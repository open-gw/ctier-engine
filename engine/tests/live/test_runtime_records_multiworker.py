"""Gap detection with more than one nginx worker (session stacks, reconfigure)."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from ctier.boundary import BoundaryFixture, Observation, dump_report, load_suite, run_suite
from ctier.boundary.records import detect_gaps, merge_records, records_from_ledger_body, records_from_log
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.rig import CUSTODY, http

pytestmark = pytest.mark.live


def _case(cid: str) -> dict:
    return next(c for c in load_suite()["cases"] if c["id"] == cid)


def _logs(stack, service: str) -> str:
    proc = stack._compose("logs", "--no-color", "--tail", "800", service, check=False)
    text = (proc.stdout or "") + (proc.stderr or "")
    paths = {
        "kong": "cat /usr/local/kong/logs/error.log 2>/dev/null || true",
        "apisix": "cat /usr/local/apisix/logs/error.log 2>/dev/null || true",
    }
    if service in paths:
        inner = stack.exec(service, "sh", "-c", paths[service], check=False)
        text += inner.stdout or ""
        text += inner.stderr or ""
    return text


def _fetch(stack, gw: str, custody_base: str):
    def fetch() -> list[dict]:
        log = records_from_log(_logs(stack, gw))
        if gw == "apisix":
            extra = _logs(stack, "apisix-dp") + _logs(stack, "etcd")
            log = merge_records(log, records_from_log(extra))
        ledger: list[dict] = []
        try:
            status, raw, _ = http("GET", custody_base + "/v1/ledger")
        except Exception:
            status, raw = 0, b""
        if status == 200:
            try:
                ledger = records_from_ledger_body(json.loads(raw.decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
                ledger = []
        return merge_records(log, ledger)

    return fetch


def _fixture(stack, custody_base: str, gw: str, *, target: str, deployment: str,
             capabilities: set[str]):
    def send(method: str, path: str, headers: dict[str, str], body: str | None = None) -> Observation:
        hdrs_in = dict(headers)
        if body is not None and not any(k.lower() == "content-type" for k in hdrs_in):
            hdrs_in["Content-Type"] = "application/json"
        status, raw, hdrs = stack.request(
            method, path,
            headers=stack.auth_headers(**hdrs_in),
            body=body,
        )
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            payload = {}
        observer: dict[str, str] = {}
        if isinstance(payload, dict) and isinstance(payload.get("headers"), dict):
            observer = {str(k).lower(): str(v) for k, v in payload["headers"].items()}
        response = {str(k).lower(): str(v) for k, v in (hdrs or {}).items()}
        return Observation(
            status=status,
            response_headers=response,
            observer_headers=observer,
            body=payload if isinstance(payload, dict) else {},
        )

    return BoundaryFixture(
        capabilities=capabilities,
        send=send,
        fetch_records=_fetch(stack, gw, custody_base),
        set_custody_available=lambda _up: None,
        approve=lambda _obs: None,
        target=target,
        mode="bundle",
        estate="bundle",
        deployment=deployment,
    )


def _load(stack, target: str) -> None:
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    files = generate(qualified, target=target)
    stack.load_generated(files)


def _warm_workers(stack, *, path: str = "/accounts/12345/balance", n: int = 32) -> None:
    def one(i: int) -> None:
        stack.request(
            "GET",
            path,
            headers=stack.auth_headers(**{"X-Task-Id": f"runtime-gap-70-warm-{i}"}),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, range(n)))


def _assert_multi_worker_gap(stack, *, target: str, gw: str, custody_base: str) -> None:
    _load(stack, target)
    _warm_workers(stack)
    written = _fetch(stack, gw, custody_base)()
    epochs = {
        str(rec["sinkEpoch"])
        for rec in written
        if rec.get("sinkEpoch") is not None
    }
    assert len(epochs) >= 2, (
        f"{target}: expected at least two sink epochs under two workers, got {sorted(epochs)}"
    )
    assert detect_gaps(written) == [], (
        f"{target}: interleave of epochs must not look like a gap: {detect_gaps(written)}"
    )
    cid = "induced-gap-is-detected"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            stack, custody_base, gw,
            target=target, deployment="level-2",
            capabilities={"recordSource"},
        ),
    )
    by_id = {c["id"]: c for c in report["cases"]}
    assert by_id[cid]["result"] == "passed", dump_report(report)
    assert report["failed"] == 0, dump_report(report)


def test_kong_induced_gap_with_two_workers(kong_stack):
    try:
        kong_stack.reconfigure_workers(2)
        _assert_multi_worker_gap(
            kong_stack, target="kong", gw="kong", custody_base=CUSTODY,
        )
    finally:
        kong_stack.reconfigure_workers(1)


def test_apisix_induced_gap_with_two_workers(apisix_stack):
    try:
        apisix_stack.reconfigure_workers(2)
        _assert_multi_worker_gap(
            apisix_stack, target="apisix", gw="apisix", custody_base=APISIX_CUSTODY,
        )
    finally:
        apisix_stack.reconfigure_workers(1)
