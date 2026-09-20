"""Live: Levels 1 and 2 write a schema-valid decision without custody."""
from __future__ import annotations

import json

import pytest

from ctier.compose import compose
from ctier.generate import generate
from ctier.ledger.records import validate_record
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
MARKER = "[ctier-decision] "


def _echo_headers(payload: dict) -> dict[str, str]:
    raw = payload.get("headers") or {}
    return {str(k).lower(): str(v) for k, v in raw.items()}


def _parse_records(text: str) -> list[dict]:
    found = []
    for line in text.splitlines():
        if MARKER not in line:
            continue
        payload = line.split(MARKER, 1)[1].strip()
        start = payload.find("{")
        end = payload.rfind("}")
        if start < 0 or end <= start:
            continue
        try:
            rec = json.loads(payload[start:end + 1])
        except json.JSONDecodeError:
            continue
        if rec.get("ctierSchema") == "decision-record/0.2.0":
            found.append(rec)
    return found


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


def _kong_load(kong_stack, *, observe: bool = False, custody=None):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="kong", observe=observe, custody=custody)
    kong_stack.load_generated(files)


def _apisix_load(apisix_stack, *, observe: bool = False, custody=None):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="apisix", observe=observe, custody=custody)
    apisix_stack.load_generated(files)


@pytest.mark.parametrize("observe", [False, True])
def test_kong_log_sink_decision_validates(kong_stack, observe):
    _kong_load(kong_stack, observe=observe)
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=kong_stack.auth_headers(),
    )
    assert status == 200, payload
    records = _parse_records(_logs(kong_stack, "kong"))
    assert records, "expected a [ctier-decision] line in Kong logs"
    rec = records[-1]
    validate_record(rec)
    assert rec["disposition"] == "execute"
    assert rec["appliedTier"] == 1
    if observe:
        status4, payload4 = kong_stack.echo_json(
            "POST", "/payments",
            headers=kong_stack.auth_headers(),
            body="{}",
        )
        assert status4 == 200, payload4


@pytest.mark.parametrize("observe", [False, True])
def test_apisix_log_sink_decision_validates(apisix_stack, observe):
    _apisix_load(apisix_stack, observe=observe)
    status, payload = apisix_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=apisix_stack.auth_headers(),
    )
    assert status == 200, payload
    records = _parse_records(_logs(apisix_stack, "apisix"))
    if not records:
        records = _parse_records(_logs(apisix_stack, "apisix-dp") + _logs(apisix_stack, "etcd"))
    assert records, "expected a [ctier-decision] line in APISIX logs"
    rec = records[-1]
    validate_record(rec)
    assert rec["disposition"] == "execute"


def test_kong_level_3_still_writes_custody(kong_stack):
    _kong_load(kong_stack, custody={"url": CUSTODY_INTERNAL, "timeout_ms": 200})
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=kong_stack.auth_headers(),
    )
    assert status == 200, payload
    cid = _echo_headers(payload).get("x-ctier-correlation-id")
    assert cid
    code, raw, _ = http("GET", CUSTODY + "/v1/ledger?type=decision")
    assert code == 200, raw
    rows = json.loads(raw.decode("utf-8"))["records"]
    match = [r for r in rows if r.get("correlationId") == cid]
    assert match, rows
    rec = {k: v for k, v in match[-1].items() if k != "type"}
    validate_record(rec)


    rec = {k: v for k, v in match[-1].items() if k != "type"}
    validate_record(rec)


ATTEMPT_MARKER = "[ctier-attempt] "


def _parse_attempts(text: str) -> list[dict]:
    found = []
    for line in text.splitlines():
        if ATTEMPT_MARKER not in line:
            continue
        payload = line.split(ATTEMPT_MARKER, 1)[1].strip()
        start = payload.find("{")
        end = payload.rfind("}")
        if start < 0 or end <= start:
            continue
        try:
            rec = json.loads(payload[start:end + 1])
        except json.JSONDecodeError:
            continue
        if rec.get("ctierSchema") == "attempt-record/0.3.0":
            found.append(rec)
    return found


def test_kong_custody_unavailable_logs_an_attempt(kong_stack):
    from ctier.ledger.records import SCHEMA_ATTEMPT

    _kong_load(kong_stack, custody={"url": CUSTODY_INTERNAL, "timeout_ms": 200})
    try:
        kong_stack.stop_service("custody")
        status, raw, _ = kong_stack.request(
            "PUT",
            "/customers/12345/preferences/communication",
            headers=kong_stack.auth_headers(**{"X-Task-Id": "task-35-kong-attempt"}),
        )
        assert status == 503, raw
    finally:
        kong_stack.start_service("custody")
    attempts = _parse_attempts(_logs(kong_stack, "kong"))
    assert attempts, "expected a [ctier-attempt] line in Kong logs"
    rec = attempts[-1]
    validate_record(rec)
    assert rec["ctierSchema"] == SCHEMA_ATTEMPT
    assert rec["appliedTier"] is None
    assert rec["reason"] == "custody-unavailable"
    assert rec["declaredTier"] == 3


def test_apisix_custody_unavailable_logs_an_attempt(apisix_stack):
    """C10: a 503 that classifies nothing must still be recorded."""
    from ctier.ledger.records import SCHEMA_ATTEMPT

    _apisix_load(
        apisix_stack,
        custody={"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    try:
        apisix_stack.stop_service("custody")
        status, raw, _ = apisix_stack.request(
            "PUT",
            "/customers/12345/preferences/communication",
            headers=apisix_stack.auth_headers(**{"X-Task-Id": "task-35-apisix-attempt"}),
        )
        assert status == 503, raw
    finally:
        apisix_stack.start_service("custody")
    attempts = _parse_attempts(_logs(apisix_stack, "apisix"))
    if not attempts:
        attempts = _parse_attempts(
            _logs(apisix_stack, "apisix-dp") + _logs(apisix_stack, "etcd")
        )
    assert attempts, "expected a [ctier-attempt] line in APISIX logs"
    rec = attempts[-1]
    validate_record(rec)
    assert rec["ctierSchema"] == SCHEMA_ATTEMPT
    assert rec["appliedTier"] is None
    assert rec["reason"] == "custody-unavailable"
    assert rec["declaredTier"] == 3
    assert rec.get("type") is None
