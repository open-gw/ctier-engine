"""Live runtime-suite record cases. Kong and APISIX; custody-down first."""
from __future__ import annotations

import json

import pytest

from ctier.boundary import BoundaryFixture, Observation, dump_report, load_suite, run_suite
from ctier.boundary.records import merge_records, records_from_ledger_body, records_from_log
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
APPROVER = "analyst-runtime-37"
KONG_CUSTODY = {
    "url": CUSTODY_INTERNAL,
    "timeout_ms": 200,
    "ledger_fallback": "/var/ctier/ledger/attempts.jsonl",
}
APISIX_CUSTODY_CFG = {"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200}


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


def _fixture(stack, custody_base: str, gw: str, *, target: str, deployment: str,
             capabilities: set[str], estate: str = "bundle"):
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

    def set_custody_available(up: bool) -> None:
        if up:
            stack.start_service("custody")
        else:
            stack.stop_service("custody")

    def approve(obs: Observation) -> None:
        cid = obs.response_headers.get("x-ctier-correlation-id")
        if not cid:
            raise AssertionError("approve: no correlation id on the 202")
        status, raw, _ = http(
            "POST",
            f"{custody_base}/v1/decisions/{cid}",
            headers={
                "Content-Type": "application/json",
                "X-Approver-Id": APPROVER,
            },
            body=json.dumps({"decision": "approve"}).encode("utf-8"),
        )
        if status != 200:
            raise AssertionError(f"approve: {status} {raw!r}")

    return BoundaryFixture(
        capabilities=capabilities,
        send=send,
        fetch_records=_fetch(stack, gw, custody_base),
        set_custody_available=set_custody_available,
        approve=approve,
        target=target,
        mode="bundle",
        estate=estate,
        deployment=deployment,
    )


def _load(stack, target: str, *, observe: bool = False, custody=None):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target=target, observe=observe, custody=custody)
    stack.load_generated(files)


def _assert_passed(report: dict, cid: str) -> None:
    by_id = {c["id"]: c for c in report["cases"]}
    assert by_id[cid]["result"] == "passed", dump_report(report)
    assert report["failed"] == 0, dump_report(report)


def test_kong_custody_unavailable_records_an_attempt(kong_stack):
    _load(kong_stack, "kong", custody=KONG_CUSTODY)
    cid = "custody-unavailable-records-attempt"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            kong_stack, CUSTODY, "kong",
            target="kong", deployment="level-3",
            capabilities={"recordSource", "custodyControl"},
        ),
    )
    _assert_passed(report, cid)


def test_apisix_custody_unavailable_records_an_attempt(apisix_stack):
    _load(apisix_stack, "apisix", custody=APISIX_CUSTODY_CFG)
    cid = "custody-unavailable-records-attempt"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            apisix_stack, APISIX_CUSTODY, "apisix",
            target="apisix", deployment="level-3",
            capabilities={"recordSource", "custodyControl"},
        ),
    )
    _assert_passed(report, cid)


def test_kong_level_1_observe_records_a_decision(kong_stack):
    _load(kong_stack, "kong", observe=True)
    cid = "level-1-observe-records-decision"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            kong_stack, CUSTODY, "kong",
            target="kong", deployment="level-1",
            capabilities={"recordSource"},
        ),
    )
    _assert_passed(report, cid)


def test_apisix_level_1_observe_records_a_decision(apisix_stack):
    _load(apisix_stack, "apisix", observe=True)
    cid = "level-1-observe-records-decision"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            apisix_stack, APISIX_CUSTODY, "apisix",
            target="apisix", deployment="level-1",
            capabilities={"recordSource"},
        ),
    )
    _assert_passed(report, cid)


def test_kong_level_2_execute_records_a_decision(kong_stack):
    _load(kong_stack, "kong")
    cid = "level-2-execute-records-decision"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            kong_stack, CUSTODY, "kong",
            target="kong", deployment="level-2",
            capabilities={"recordSource"},
        ),
    )
    _assert_passed(report, cid)


def test_kong_induced_gap_is_detected(kong_stack):
    _load(kong_stack, "kong")
    cid = "induced-gap-is-detected"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            kong_stack, CUSTODY, "kong",
            target="kong", deployment="level-2",
            capabilities={"recordSource"},
        ),
    )
    _assert_passed(report, cid)


def test_apisix_induced_gap_is_detected(apisix_stack):
    _load(apisix_stack, "apisix")
    cid = "induced-gap-is-detected"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            apisix_stack, APISIX_CUSTODY, "apisix",
            target="apisix", deployment="level-2",
            capabilities={"recordSource"},
        ),
    )
    _assert_passed(report, cid)


def test_apisix_level_2_execute_records_a_decision(apisix_stack):
    _load(apisix_stack, "apisix")
    cid = "level-2-execute-records-decision"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            apisix_stack, APISIX_CUSTODY, "apisix",
            target="apisix", deployment="level-2",
            capabilities={"recordSource"},
        ),
    )
    _assert_passed(report, cid)


def test_kong_withheld_then_approved_records_outcome(kong_stack):
    _load(kong_stack, "kong", custody=KONG_CUSTODY)
    cid = "withheld-then-approved"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            kong_stack, CUSTODY, "kong",
            target="kong", deployment="level-3",
            capabilities={"recordSource", "execute"},
        ),
    )
    _assert_passed(report, cid)


def test_apisix_withheld_then_approved_records_outcome(apisix_stack):
    _load(apisix_stack, "apisix", custody=APISIX_CUSTODY_CFG)
    cid = "withheld-then-approved"
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(
            apisix_stack, APISIX_CUSTODY, "apisix",
            target="apisix", deployment="level-3",
            capabilities={"recordSource", "execute"},
        ),
    )
    _assert_passed(report, cid)
