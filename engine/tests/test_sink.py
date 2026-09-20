"""A record sink is not custody. No gateway, no network."""
from __future__ import annotations

from ctier.ledger.records import SCHEMA_DECISION, validate_record
from ctier.ledger.sink import CUSTODY, GATEWAY_LOG, SINKS, log_decision_record

DIGEST = "sha256:" + "ab" * 32


def test_two_sinks_and_custody_is_not_the_only_one():
    assert CUSTODY.needs_runtime is True
    assert CUSTODY.durable == "yes"
    assert GATEWAY_LOG.needs_runtime is False
    assert GATEWAY_LOG.durable == "operator"
    assert SINKS == (CUSTODY, GATEWAY_LOG)


def test_log_sink_record_validates_as_decision_0_2_0():
    rec = log_decision_record(
        operation_anchor="getBalance",
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=1,
        escalation_reason="none",
        disposition="execute",
        deployment_digest=DIGEST,
        declared_tier=1,
        correlation_id="cid-1",
        record_id="cid-1",
        timestamp="2026-09-16T12:00:00Z",
    )
    assert rec["ctierSchema"] == SCHEMA_DECISION
    validate_record(rec)
