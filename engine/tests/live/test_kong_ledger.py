"""Live ledger: Decision, Attempt, Outcome, GET /v1/ledger."""
from __future__ import annotations

import json
from urllib.parse import urlencode

import pytest

from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http, point_at_echo

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
LEDGER_CUSTODY = {
    "url": CUSTODY_INTERNAL,
    "timeout_ms": 200,
    "ledger_fallback": "/var/ctier/ledger/attempts.jsonl",
}
SECRET = "super-secret-bearer-token-11"
SERVICE_APPROVER = "analyst-live-11"


def _load(kong_stack, qualified) -> None:
    files = generate(qualified, target="kong", custody=LEDGER_CUSTODY)
    kong_stack.load_generated(files)


def _ledger(correlation_scope: str | None = None, record_type: str | None = None) -> list[dict]:
    query = {}
    if correlation_scope is not None:
        query["correlationScope"] = correlation_scope
    if record_type is not None:
        query["type"] = record_type
    url = CUSTODY + "/v1/ledger"
    if query:
        url = url + "?" + urlencode(query)
    status, raw, _ = http("GET", url)
    assert status == 200, raw
    return json.loads(raw.decode("utf-8"))["records"]


def _scan(records: list[dict]) -> None:
    blob = json.dumps(records)
    assert SECRET not in blob
    for record in records:
        keys = json.dumps(list(record.keys())).lower()
        assert "authorization" not in keys
        assert "credential" not in keys


def test_tier1_request_produces_a_decision(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(kong_stack, qualified)
    scope = "task-11-t1"
    status, raw, _ = kong_stack.request(
        "GET",
        "/accounts/12345/balance",
        headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-live-11", "X-Task-Id": scope}),
    )
    assert status == 200, raw
    records = _ledger(correlation_scope=scope, record_type="decision")
    assert records, records
    decision = records[0]
    assert decision["type"] == "decision"
    assert decision["disposition"] == "execute"
    assert decision["appliedTier"] == 1
    assert decision["declaredTier"] == 1
    assert decision["agentId"] == "agent-live-11"
    _scan(records)


def test_tier4_request_produces_refuse_and_suspend(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(kong_stack, qualified)
    scope = "task-11-t4"
    status, raw, _ = kong_stack.request(
        "POST",
        "/payments",
        headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-live-11", "X-Task-Id": scope}),
        body="{}",
    )
    assert status == 423, raw
    records = _ledger(correlation_scope=scope, record_type="decision")
    assert records, records
    decision = records[0]
    assert decision["disposition"] == "refuse-and-suspend"
    assert decision["appliedTier"] == 4
    _scan(records)


def test_withheld_then_approved_produces_decision_and_outcome(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(kong_stack, qualified)
    scope = "task-11-t3"
    status, raw, hdrs = kong_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-live-11", "X-Task-Id": scope}),
    )
    body = json.loads(raw.decode("utf-8"))
    assert status == 202, body
    correlation_id = body["correlationId"]
    assert hdrs.get("x-ctier-correlation-id") == correlation_id

    dec_status, dec_raw, _ = http(
        "POST",
        f"{CUSTODY}/v1/decisions/{correlation_id}",
        headers={
            "Content-Type": "application/json",
            "X-Approver-Id": SERVICE_APPROVER,
        },
        body=json.dumps({"decision": "approve"}).encode("utf-8"),
    )
    decision = json.loads(dec_raw.decode("utf-8"))
    assert dec_status == 200, decision
    assert decision["status"] == "executed"

    records = _ledger(correlation_scope=scope)
    types = {r["type"] for r in records}
    assert "decision" in types, records
    assert "outcome" in types, records
    decisions = [r for r in records if r["type"] == "decision"]
    outcomes = [r for r in records if r["type"] == "outcome"]
    assert decisions[0]["disposition"] == "withhold"
    assert decisions[0]["correlationId"] == correlation_id
    assert outcomes[0]["correlationId"] == correlation_id
    assert outcomes[0]["approver"] == SERVICE_APPROVER
    assert outcomes[0]["failed"] is False
    _scan(records)


def test_custody_unavailable_produces_an_attempt(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(kong_stack, qualified)
    scope = "task-11-attempt"
    try:
        kong_stack.stop_service("custody")
        status, raw, hdrs = kong_stack.request(
            "PUT",
            "/customers/12345/profile",
            headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-live-11", "X-Task-Id": scope}),
        )
        body = json.loads(raw.decode("utf-8"))
        assert status == 503, body
        assert hdrs.get("retry-after") == "5"
        assert body.get("status") == "custody_unavailable"
    finally:
        kong_stack.start_service("custody")

    records = _ledger(correlation_scope=scope, record_type="attempt")
    assert records, records
    attempt = records[0]
    assert attempt["type"] == "attempt"
    assert attempt["declaredTier"] == 3
    assert attempt["appliedTier"] is None
    assert attempt["deploymentDigest"].startswith("sha256:")
    assert attempt["reason"] == "custody-unavailable"
    _scan(records)
