"""Vendored ledger schemas and per-type construction. No gateway, no network."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ctier.ledger.records import (
    SCHEMA_ATTEMPT,
    SCHEMA_DECISION,
    SCHEMA_OUTCOME,
    attempt_record,
    decision_from_ingress,
    decision_record,
    load_schema,
    outcome_record,
    validate_record,
)
from ctier.ledger.store import Ledger

NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)
DIGEST = "sha256:" + "ab" * 32
TS = "2026-09-07T12:00:00Z"


def _decision(**overrides):
    data = dict(
        operation_anchor="getBalance",
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=1,
        escalation_reason="none",
        disposition="execute",
        idempotency_key="k" * 64,
        deployment_digest=DIGEST,
        declared_tier=1,
        record_id="dec-1",
        timestamp=TS,
    )
    data.update(overrides)
    return decision_record(**data)


def test_three_schemas_are_distinct_and_valid():
    for name in (SCHEMA_DECISION, SCHEMA_ATTEMPT, SCHEMA_OUTCOME):
        schema = load_schema(name)
        Draft202012Validator.check_schema(schema)
    assert load_schema(SCHEMA_DECISION)["required"]
    assert "appliedTier" in load_schema(SCHEMA_DECISION)["required"]
    assert load_schema(SCHEMA_ATTEMPT)["properties"]["appliedTier"] == {"type": "null"}
    assert "correlationId" in load_schema(SCHEMA_OUTCOME)["required"]
    assert SCHEMA_DECISION != SCHEMA_ATTEMPT != SCHEMA_OUTCOME


def test_decision_construction_round_trips_the_schema():
    record = _decision(correlation_id="corr-1")
    validate_record(record)
    assert record["ctierSchema"] == SCHEMA_DECISION
    assert record["disposition"] == "execute"
    assert record["appliedTier"] == 1
    assert record["declaredTier"] == 1
    assert record["correlationId"] == "corr-1"


def test_classifier_refuse_is_written_as_refuse_and_suspend():
    record = _decision(
        applied_tier=4,
        declared_tier=4,
        disposition="refuse",
        operation_anchor="initiatePayment",
    )
    assert record["disposition"] == "refuse-and-suspend"
    with pytest.raises(ValidationError):
        broken = dict(record)
        broken["disposition"] = "refuse"
        validate_record(broken)


def test_attempt_marks_applied_tier_undetermined():
    record = attempt_record(
        operation_anchor="updateCustomerProfile",
        declared_tier=3,
        deployment_digest=DIGEST,
        reason="custody-unavailable",
        agent_id="agent-a",
        correlation_scope="task-1",
        record_id="att-1",
        timestamp=TS,
    )
    validate_record(record)
    assert record["appliedTier"] is None
    assert record["declaredTier"] == 3
    assert record["deploymentDigest"] == DIGEST
    assert record["reason"] == "custody-unavailable"
    assert record["ctierSchema"] == SCHEMA_ATTEMPT


def test_attempt_omits_declared_tier_when_none_was_declared():
    record = attempt_record(
        operation_anchor="GET /estate/unknown",
        deployment_digest=DIGEST,
        reason="unassigned",
        record_id="att-none",
        timestamp=TS,
    )
    validate_record(record)
    assert "declaredTier" not in record
    assert record["appliedTier"] is None
    assert record["reason"] == "unassigned"


def test_a_decision_with_null_applied_tier_is_not_an_attempt():
    record = _decision()
    record["appliedTier"] = None
    with pytest.raises(ValidationError):
        validate_record(record)


def test_an_attempt_with_a_determined_tier_is_not_a_decision():
    record = attempt_record(
        operation_anchor="updateCustomerProfile",
        declared_tier=3,
        deployment_digest=DIGEST,
        reason="custody-unavailable",
        record_id="att-1",
        timestamp=TS,
    )
    record["appliedTier"] = 3
    with pytest.raises(ValidationError):
        validate_record(record)


def test_outcome_construction():
    record = outcome_record(
        correlation_id="corr-1",
        approver="analyst-1",
        executed_at=TS,
        failed=False,
        status_code=200,
        record_id="out-1",
        timestamp=TS,
    )
    validate_record(record)
    assert record["result"] == "executed"
    assert record["failed"] is False
    failed = outcome_record(
        correlation_id="corr-1",
        approver="analyst-1",
        executed_at=TS,
        failed=True,
        status_code=500,
        record_id="out-2",
        timestamp=TS,
    )
    assert failed["result"] == "failed"
    assert failed["failed"] is True


def test_decision_from_ingress_derives_the_key_without_headers():
    record = decision_from_ingress({
        "type": "decision",
        "operationAnchor": "getBalance",
        "agentId": "agent-a",
        "taskId": "task-1",
        "correlationScope": "task-1",
        "declaredTier": 1,
        "appliedTier": 1,
        "escalationReason": "none",
        "disposition": "execute",
        "deploymentDigest": DIGEST,
        "method": "GET",
        "path": "/accounts/12345/balance",
        "query": {},
        "body": None,
        "Authorization": "Bearer should-not-be-read",
    }, now=NOW)
    assert "Authorization" not in record
    assert record["idempotencyKey"]
    assert len(record["idempotencyKey"]) == 64


def test_ledger_stores_three_types_separately():
    ledger = Ledger()
    ledger.append_decision(_decision())
    ledger.append_attempt(attempt_record(
        operation_anchor="updateCustomerProfile",
        declared_tier=3,
        deployment_digest=DIGEST,
        reason="custody-unavailable",
        correlation_scope="task-1",
        record_id="att-1",
        timestamp=TS,
    ))
    ledger.append_outcome(outcome_record(
        correlation_id="corr-1",
        approver="analyst-1",
        executed_at=TS,
        failed=False,
        record_id="out-1",
        timestamp=TS,
    ))
    all_rows = ledger.list_records()
    assert {r["type"] for r in all_rows} == {"decision", "attempt", "outcome"}
    assert len(ledger.list_records(record_type="decision")) == 1
    assert len(ledger.list_records(record_type="attempt")) == 1
    assert len(ledger.list_records(record_type="outcome")) == 1
    scoped = ledger.list_records(correlation_scope="task-1")
    assert {r["type"] for r in scoped} == {"attempt", "decision"}
    ledger.close()


def test_scope_filter_returns_correlated_outcome():
    ledger = Ledger()
    ledger.append_decision(_decision(correlation_id="corr-1", record_id="dec-1"))
    ledger.append_outcome(outcome_record(
        correlation_id="corr-1",
        approver="analyst-1",
        executed_at=TS,
        failed=False,
        record_id="out-1",
        timestamp=TS,
    ))
    scoped = ledger.list_records(correlation_scope="task-1")
    assert {r["type"] for r in scoped} == {"decision", "outcome"}
    empty = ledger.list_records(correlation_scope="other")
    assert empty == []
    ledger.close()


def test_ingest_fallback_reads_attempts_then_clears_the_file(tmp_path):
    path = tmp_path / "attempts.jsonl"
    line = json.dumps({
        "ctierSchema": SCHEMA_ATTEMPT,
        "id": "att-fb",
        "timestamp": TS,
        "operationAnchor": "updateCustomerProfile",
        "declaredTier": 3,
        "appliedTier": None,
        "deploymentDigest": DIGEST,
        "reason": "custody-unavailable",
        "agentId": "agent-a",
        "correlationScope": "task-1",
    })
    path.write_text(line + "\n", encoding="utf-8")
    ledger = Ledger()
    n = ledger.ingest_fallback(str(path))
    assert n == 1
    assert not path.exists()
    rows = ledger.list_records(record_type="attempt")
    assert len(rows) == 1
    assert rows[0]["appliedTier"] is None
    assert rows[0]["reason"] == "custody-unavailable"
    ledger.close()


def test_old_and_new_ledger_rows_are_distinguishable_by_ctier_schema():
    """Ledger payloads already carry ctierSchema. 0.1.0 vs 0.2.0 is the marker.

    Insert the old shape through SQL: validate_record only knows 0.2.0.
    The stored hex is left alone — there is nothing to convert it from.
    """
    old_digest = "sha256:" + "aa" * 32
    old_payload = {
        "ctierSchema": "decision-record/0.1.0",
        "type": "decision",
        "id": "old-1",
        "timestamp": TS,
        "operationAnchor": "getBalance",
        "agentId": "agent-a",
        "correlationScope": "task-1",
        "declaredTier": 1,
        "appliedTier": 1,
        "escalationReason": "none",
        "disposition": "execute",
        "idempotencyKey": "k" * 64,
        "composition": old_digest,
    }
    ledger = Ledger()
    with ledger._lock:
        ledger._conn.execute(
            "INSERT INTO ledger_decision (id, recorded_at, payload) "
            "VALUES (?, ?, ?)",
            (
                "old-1",
                TS,
                json.dumps(old_payload, sort_keys=True, separators=(",", ":")),
            ),
        )
        ledger._conn.commit()
    ledger.append_decision(_decision(record_id="new-1"))
    rows = {r["id"]: r for r in ledger.list_records(record_type="decision")}
    old = rows["old-1"]
    new = rows["new-1"]
    assert old["ctierSchema"] == "decision-record/0.1.0"
    assert new["ctierSchema"] == SCHEMA_DECISION
    assert old["ctierSchema"] != new["ctierSchema"]
    assert old["composition"] == old_digest
    assert "deploymentDigest" not in old
    assert new["deploymentDigest"] == DIGEST
    assert "composition" not in new
    ledger.close()
