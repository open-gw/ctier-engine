"""Run conformance-kit/1.1 against the live stacks. Failures are the result."""
from __future__ import annotations

import json

import pytest

from ctier.compose import compose
from ctier.generate import generate
from ctier.kit import Target, dump_report, load_cases, run_kit
from ctier.kit.runner import Observation, _json_body, _lower
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
KONG_CUSTODY = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}
APISIX_CUSTODY_CFG = {"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200}


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


def _fetch_records(stack, gw: str, custody_base: str):
    from ctier.boundary.records import merge_records, records_from_ledger_body, records_from_log

    def fetch() -> list[dict]:
        log = records_from_log(_logs(stack, gw))
        extra = ""
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


def _observer(stack):
    def log() -> list[dict]:
        if hasattr(stack, "harness_requests"):
            return stack.harness_requests()
        return stack.echo_log()

    return log


def _pending(custody_base: str):
    def fetch() -> list[dict]:
        status, raw, _ = http("GET", custody_base + "/v1/pending")
        if status != 200:
            return []
        try:
            return json.loads(raw.decode("utf-8")).get("pending") or []
        except ValueError:
            return []

    return fetch


def _approve(custody_base: str):
    def approve(correlation_id: str) -> dict:
        status, raw, _ = http(
            "POST",
            f"{custody_base}/v1/decisions/{correlation_id}",
            headers={
                "Content-Type": "application/json",
                "X-Approver-Id": "kit-approver",
            },
            body=json.dumps({"decision": "approve"}).encode("utf-8"),
        )
        try:
            return json.loads(raw.decode("utf-8")) if raw else {"status": status}
        except ValueError:
            return {"status": status}

    return approve


def _target(stack, *, gw: str, custody_base: str) -> Target:
    token = stack.token() if hasattr(stack, "token") else stack.auth_headers()["Authorization"].split(" ", 1)[1]

    def send(method, path, headers=None, body=None, query=None):
        hdrs = dict(headers or {})
        if body is not None and not any(k.lower() == "content-type" for k in hdrs):
            hdrs["Content-Type"] = "application/json"
        # stack.request already can take a token via Authorization we pass
        status, raw, rhdrs = stack.request(method, path, query=query, headers=hdrs, body=body)
        return Observation(status, _lower(rhdrs), _json_body(raw), raw)

    return Target(
        send=send,
        token=token,
        records=_fetch_records(stack, gw, custody_base),
        observer_log=_observer(stack),
        pending=_pending(custody_base),
        approve=_approve(custody_base),
    )


def _load(stack, target: str, *, custody: dict | None) -> None:
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target=target, custody=custody)
    stack.load_generated(files)


def _run(stack, *, target: str, gw: str, custody_base: str, custody: dict | None, level: str) -> dict:
    _load(stack, target, custody=custody)
    report = run_kit(load_cases(), _target(stack, gw=gw, custody_base=custody_base), level=level)
    return report


def test_kong_kit_level_3(kong_stack):
    report = _run(
        kong_stack,
        target="kong",
        gw="kong",
        custody_base=CUSTODY,
        custody=KONG_CUSTODY,
        level="3",
    )
    print(dump_report(report))
    assert report["ctierSchema"].startswith("conformance-kit-report/")
    assert report["passed"] + report["failed"] + report["skipped"] + report.get("inconclusive", 0) == len(report["cases"])


def test_kong_kit_level_2(kong_stack):
    report = _run(
        kong_stack,
        target="kong",
        gw="kong",
        custody_base=CUSTODY,
        custody=None,
        level="2",
    )
    print(dump_report(report))
    assert report["passed"] + report["failed"] + report["skipped"] + report.get("inconclusive", 0) == len(report["cases"])


def test_apisix_kit_level_3(apisix_stack):
    report = _run(
        apisix_stack,
        target="apisix",
        gw="apisix",
        custody_base=APISIX_CUSTODY,
        custody=APISIX_CUSTODY_CFG,
        level="3",
    )
    print(dump_report(report))
    assert report["passed"] + report["failed"] + report["skipped"] + report.get("inconclusive", 0) == len(report["cases"])


def test_apisix_kit_level_2(apisix_stack):
    report = _run(
        apisix_stack,
        target="apisix",
        gw="apisix",
        custody_base=APISIX_CUSTODY,
        custody=None,
        level="2",
    )
    print(dump_report(report))
    assert report["passed"] + report["failed"] + report["skipped"] + report.get("inconclusive", 0) == len(report["cases"])
