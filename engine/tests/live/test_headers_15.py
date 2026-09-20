"""1.5.0 on the wire. Kong and APISIX live; Apigee has no local runtime."""
from __future__ import annotations

import json

import pytest

from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
FORGED = {
    "x-ctier-criteria": "forged-criteria",
    "x-ctier-unknown-audit": "forged-unknown",
    "X-Correlation-Id": "agent-correlation",
    "X-Ctier-Tier": "9",
    "Idempotency-Key": "agent-idempotency",
    "X-Idempotency-Key": "agent-x-idempotency",
}


def _kong_load(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified, target="kong",
        custody={"url": CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    kong_stack.load_generated(files)
    return kong_stack


def _apisix_load(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified, target="apisix",
        custody={"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    apisix_stack.load_generated(files)
    return apisix_stack


def _echo_headers(payload: dict) -> dict[str, str]:
    raw = payload.get("headers") or {}
    return {str(k).lower(): str(v) for k, v in raw.items()}


def _ledger_by_correlation(custody_base: str, cid: str) -> dict:
    status, raw, _ = http("GET", custody_base + "/v1/ledger?type=decision")
    assert status == 200, raw
    records = json.loads(raw.decode("utf-8")).get("records") or []
    match = [r for r in records if r.get("correlationId") == cid]
    assert match, records
    return match[-1]


def test_kong_prefix_left_x_correlation_id_open(kong_stack):
    """Confirmed: strip_inbound was prefix-only. Alias is now explicit."""
    from pathlib import Path
    text = (
        Path(__file__).resolve().parents[3]
        / "targets" / "kong" / "plugin" / "handler.lua"
    ).read_text(encoding="utf-8")
    assert 'PREFIX = "x-ctier-"' in text
    assert "x-correlation-id" in text.lower()
    _kong_load(kong_stack)
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=kong_stack.auth_headers(**FORGED),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    assert headers.get("x-correlation-id") != "agent-correlation"
    assert "agent-correlation" not in headers.values()


def test_kong_forged_headers_do_not_reach_backend(kong_stack):
    _kong_load(kong_stack)
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=kong_stack.auth_headers(**FORGED),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    assert "x-ctier-criteria" not in headers
    assert "x-ctier-unknown-audit" not in headers
    assert headers.get("x-ctier-tier") != "9"
    assert headers.get("idempotency-key") != "agent-idempotency"
    assert headers.get("x-idempotency-key") != "agent-x-idempotency"


def test_kong_correlation_id_equals_decision_record(kong_stack):
    _kong_load(kong_stack)
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=kong_stack.auth_headers(),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    cid = headers.get("x-ctier-correlation-id")
    assert cid
    record = _ledger_by_correlation(CUSTODY, cid)
    assert record["correlationId"] == cid
    key = headers.get("idempotency-key")
    assert key
    assert record["idempotencyKey"] == key


def test_kong_202_carries_the_join_key(kong_stack):
    _kong_load(kong_stack)
    status, raw, hdrs = kong_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-a", "X-Task-Id": "task-14c"}),
    )
    assert status == 202, raw
    assert hdrs.get("x-ctier-correlation-id")
    assert not hdrs.get("x-correlation-id")


def test_apisix_forged_headers_do_not_reach_backend(apisix_stack):
    _apisix_load(apisix_stack)
    status, payload = apisix_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=apisix_stack.auth_headers(**FORGED),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    assert "x-ctier-criteria" not in headers
    assert "x-ctier-unknown-audit" not in headers
    assert headers.get("x-ctier-tier") != "9"
    assert headers.get("idempotency-key") != "agent-idempotency"
    assert headers.get("x-idempotency-key") != "agent-x-idempotency"


def test_apisix_correlation_id_equals_decision_record(apisix_stack):
    _apisix_load(apisix_stack)
    status, payload = apisix_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=apisix_stack.auth_headers(),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    cid = headers.get("x-ctier-correlation-id")
    assert cid
    record = _ledger_by_correlation(APISIX_CUSTODY, cid)
    assert record["correlationId"] == cid
    key = headers.get("idempotency-key")
    assert key
    assert record["idempotencyKey"] == key


def test_apisix_202_carries_the_join_key(apisix_stack):
    _apisix_load(apisix_stack)
    status, raw, hdrs = apisix_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers=apisix_stack.auth_headers(**{"X-Agent-Id": "agent-a", "X-Task-Id": "task-14c"}),
    )
    assert status == 202, raw
    lower = {k.lower(): v for k, v in hdrs.items()}
    assert lower.get("x-ctier-correlation-id")
    assert not lower.get("x-correlation-id")
