"""Live Tier 3 release: approve executes from persisted context. Agent asked once."""
from __future__ import annotations

import json

import pytest

from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.rig import CUSTODY, SERVICE_TOKEN, http, point_at_echo

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
CUSTODY_CFG = {"url": "http://custody:8080", "timeout_ms": 200}
AGENT_TOKEN = "agent-secret-live-10"


def test_tier3_approve_executes_from_persisted_context(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="kong", custody=CUSTODY_CFG)
    kong_stack.load_generated(files)

    status, raw, hdrs = kong_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-live-10", "X-Task-Id": "task-10"}),
    )
    body = json.loads(raw.decode("utf-8"))
    assert status == 202, body
    assert body["retryable"] is False
    correlation_id = body["correlationId"]
    assert hdrs.get("x-ctier-correlation-id") == correlation_id

    queue_status, queue_raw, _ = http("GET", CUSTODY + "/v1/pending")
    assert queue_status == 200
    pending = json.loads(queue_raw.decode("utf-8"))["pending"]
    match = [p for p in pending if p["correlationId"] == correlation_id]
    assert match, pending
    assert match[0]["agentId"] == "agent-live-10"

    # The agent asked once. Nothing below calls it back.
    dec_status, dec_raw, _ = http(
        "POST",
        f"{CUSTODY}/v1/decisions/{correlation_id}",
        headers={
            "Content-Type": "application/json",
            "X-Approver-Id": "analyst-live",
        },
        body=json.dumps({"decision": "approve"}).encode("utf-8"),
    )
    decision = json.loads(dec_raw.decode("utf-8"))
    assert dec_status == 200, decision
    assert decision["status"] == "executed"
    assert decision["approver"] == "analyst-live"
    assert decision["decision"] == "approve"
    echo = json.loads(decision["outcome"]["body"])
    headers = echo["headers"]
    assert AGENT_TOKEN not in json.dumps(echo)
    assert "x-ctier-agent" not in headers
    assert "x-ctier-approver" not in headers
    assert headers["x-ctier-correlation-id"] == correlation_id
    assert headers.get("idempotency-key")

    log = kong_stack.harness_requests()
    attributed = [
        row for row in log
        if row.get("headers", {}).get("x-ctier-correlation-id") == correlation_id
    ]
    assert len(attributed) == 1, attributed
    assert attributed[0]["method"] == "PUT"
    assert AGENT_TOKEN not in json.dumps(attributed)
    assert attributed[0]["headers"]["authorization"] == f"Bearer {SERVICE_TOKEN}"
