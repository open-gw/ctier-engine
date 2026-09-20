"""Scope floor from the decision ledger. No network."""
from __future__ import annotations

from datetime import datetime, timezone

from ctier.classifier import Accumulator, GovernanceConfig
from ctier.custody.floor import (
    PUBLISHED_FLOOR,
    decision_weight,
    floors_from_decisions,
    floors_from_ledger,
)
from ctier.ledger.records import attempt_record, decision_record
from ctier.ledger.store import Ledger

DIGEST = "sha256:" + "ab" * 32
TS = "2026-09-07T12:00:00Z"
KEY = "k" * 64
NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()


def _decision(scope: str, *, applied: int = 1, declared: int = 1, record_id: str = "d1"):
    return decision_record(
        operation_anchor="getBalance",
        agent_id="agent-a",
        correlation_scope=scope,
        applied_tier=applied,
        escalation_reason="none",
        disposition="execute",
        idempotency_key=KEY,
        deployment_digest=DIGEST,
        declared_tier=declared,
        record_id=record_id,
        timestamp=TS,
    )


def test_accumulator_arithmetic_and_decay_are_the_classifier_semantics():
    acc = Accumulator(decay_seconds=60)
    acc.add("task-1", 1, now=1000.0)
    acc.add("task-1", 1, now=1010.0)
    assert acc.current("task-1", now=1020.0) == 2
    assert acc.current("task-1", now=1070.0) == 0


def test_ten_tier1_decisions_publish_a_floor():
    decisions = [_decision("task-1", record_id=f"d{i}") for i in range(10)]
    published = floors_from_decisions(
        decisions, now=NOW, config=GovernanceConfig(escalate_above=9),
    )
    assert published["escalateAbove"] == 9
    assert published["floors"] == [{
        "correlationScope": "task-1",
        "floor": PUBLISHED_FLOOR,
        "accumulated": 10,
    }]


def test_nine_tier1_decisions_do_not_publish_a_floor():
    decisions = [_decision("task-1", record_id=f"d{i}") for i in range(9)]
    assert floors_from_decisions(decisions, now=NOW)["floors"] == []


def test_interleaved_scopes_do_not_contaminate():
    a = [_decision("task-a", record_id=f"a{i}") for i in range(10)]
    b = [_decision("task-b", record_id=f"b{i}") for i in range(3)]
    published = floors_from_decisions(a + b, now=NOW)
    assert {row["correlationScope"] for row in published["floors"]} == {"task-a"}


def test_gap_longer_than_decay_resets_accumulation():
    first = dict(_decision("task-1", record_id="old"))
    first["timestamp"] = "2026-09-07T11:00:00Z"
    recent = [_decision("task-1", record_id=f"d{i}") for i in range(3)]
    assert floors_from_decisions([first] + recent, now=NOW)["floors"] == []


def test_weight_uses_declared_tier_not_applied_after_floor_raise():
    raised = _decision("task-1", applied=2, declared=1, record_id="r1")
    assert decision_weight(raised) == 1


def test_attempts_and_an_empty_ledger_publish_no_floor():
    assert floors_from_decisions([], now=NOW)["floors"] == []
    ledger = Ledger()
    ledger.append_attempt(attempt_record(
        operation_anchor="updateCustomerProfile",
        declared_tier=3,
        deployment_digest=DIGEST,
        reason="custody-unavailable",
        correlation_scope="task-1",
        record_id="att-1",
        timestamp=TS,
    ))
    assert floors_from_ledger(ledger, now=NOW)["floors"] == []
    ledger.close()
