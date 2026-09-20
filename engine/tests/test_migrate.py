"""Migration proposals from constructed ledger data. No network, no apply path."""
from __future__ import annotations

import hashlib
import inspect
from datetime import datetime, timezone

import pytest

from ctier import migrate as migrate_mod
from ctier.ledger.records import attempt_record, decision_record, outcome_record
from ctier.ledger.store import Ledger
from ctier.migrate import MigrationConfig, propose_migrations

NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)
TS = "2026-09-07T12:00:00Z"
OLD = "2026-06-01T12:00:00Z"
DIGEST = "sha256:" + "ab" * 32
CFG = MigrationConfig(
    raise_min_sample=5,
    lower_min_sample=10,
    raise_window_seconds=86400,
    lower_window_seconds=7 * 86400,
)


def _key(n: int) -> str:
    return hashlib.sha256(f"k{n}".encode()).hexdigest()


def _t3_withhold(n: int, *, op="updateCommunicationPreferences", ts=TS):
    return decision_record(
        operation_anchor=op,
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=3,
        escalation_reason="none",
        disposition="withhold",
        idempotency_key=_key(n),
        deployment_digest=DIGEST,
        declared_tier=3,
        correlation_id=f"corr-{n}",
        record_id=f"d{n}",
        timestamp=ts,
    )


def _outcome(n: int, *, failed: bool, ts=TS):
    return outcome_record(
        correlation_id=f"corr-{n}",
        approver="analyst-1",
        executed_at=ts,
        failed=failed,
        record_id=f"o{n}",
        timestamp=ts,
    )


def _bounds(n: int, *, op="listTransactions", ts=TS):
    return decision_record(
        operation_anchor=op,
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=3,
        escalation_reason="payload-exceeds-declared-bounds",
        disposition="withhold",
        idempotency_key=_key(1000 + n),
        deployment_digest=DIGEST,
        declared_tier=2,
        correlation_id=f"b-{n}",
        record_id=f"bd{n}",
        timestamp=ts,
    )


def _t4(n: int, *, op="initiatePayment", ts=OLD):
    return decision_record(
        operation_anchor=op,
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=4,
        escalation_reason="none",
        disposition="refuse-and-suspend",
        idempotency_key=_key(2000 + n),
        deployment_digest=DIGEST,
        declared_tier=4,
        record_id=f"t4{n}",
        timestamp=ts,
    )


def _ledger(*records) -> Ledger:
    ledger = Ledger()
    for rec in records:
        kind = rec["ctierSchema"].split("/", 1)[0]
        if kind in {"decision-record"}:
            ledger.append_decision(rec)
        elif kind in {"attempt-record"}:
            ledger.append_attempt(rec)
        else:
            ledger.append_outcome(rec)
    return ledger


def test_legacy_schema_heads_are_rejected_not_ignored():
    with pytest.raises(ValueError, match="0.2.0"):
        propose_migrations(
            [{"ctierSchema": "ledger-decision/0.1.0", "appliedTier": 1}],
            CFG,
            NOW,
        )


def test_config_bar_is_asymmetric():
    assert MigrationConfig().lower_min_sample > MigrationConfig().raise_min_sample
    assert MigrationConfig().lower_window_seconds > MigrationConfig().raise_window_seconds


def test_module_has_no_apply_path():
    src = inspect.getsource(migrate_mod)
    assert "def apply" not in src
    assert "apply_migrations" not in src
    assert "auto_apply" not in src


def test_tier3_always_approved_fires_at_the_lower_bar():
    records = []
    for i in range(10):
        records.append(_t3_withhold(i))
        records.append(_outcome(i, failed=False))
    doc = propose_migrations(_ledger(*records), CFG, NOW)
    assert [p["signal"] for p in doc["proposals"]] == ["tier3-always-approved"]
    p = doc["proposals"][0]
    assert p["direction"] == "lower"
    assert p["proposed"] == {"tier": 2}
    assert p["sample"] == 10
    assert p["contraryEvents"] == 0
    assert len(p["correlationIds"]) == 10
    assert p["counts"]["approved"] == 10


def test_tier3_always_approved_absent_below_minimum():
    records = []
    for i in range(9):
        records.append(_t3_withhold(i))
        records.append(_outcome(i, failed=False))
    doc = propose_migrations(_ledger(*records), CFG, NOW)
    assert doc["proposals"] == []


def test_one_rejection_blocks_a_lowering_proposal():
    records = []
    for i in range(10):
        records.append(_t3_withhold(i))
        records.append(_outcome(i, failed=(i == 0)))
    doc = propose_migrations(_ledger(*records), CFG, NOW)
    assert not any(p["signal"] == "tier3-always-approved" for p in doc["proposals"])


def test_identical_sample_raises_and_does_not_lower():
    """Same n: raising fires, lowering does not. The bars are not symmetric."""
    n = 5
    raising = [_bounds(i) for i in range(n)]
    lowering = []
    for i in range(n):
        lowering.append(_t3_withhold(i))
        lowering.append(_outcome(i, failed=False))
    up = propose_migrations(_ledger(*raising), CFG, NOW)
    down = propose_migrations(_ledger(*lowering), CFG, NOW)
    assert [p["signal"] for p in up["proposals"]] == ["tier2-bounds-escalated"]
    assert down["proposals"] == []


def test_bounds_absent_below_minimum():
    doc = propose_migrations(_ledger(*[_bounds(i) for i in range(4)]), CFG, NOW)
    assert doc["proposals"] == []


def test_tier3_rejected_fires_on_failed_outcomes():
    records = []
    for i in range(5):
        records.append(_t3_withhold(i))
        records.append(_outcome(i, failed=True))
    doc = propose_migrations(_ledger(*records), CFG, NOW)
    assert [p["signal"] for p in doc["proposals"]] == ["tier3-repeatedly-rejected"]
    p = doc["proposals"][0]
    assert p["direction"] == "raise"
    assert p["proposed"] == {"tier": 4}
    assert p["sample"] == 5
    assert p["correlationIds"]


def test_tier4_never_attempted_needs_historical_sample_outside_the_window():
    old = [_t4(i) for i in range(5)]
    doc = propose_migrations(_ledger(*old), CFG, NOW)
    assert [p["signal"] for p in doc["proposals"]] == ["tier4-never-attempted"]
    recent = [_t4(i, ts=TS) for i in range(5)]
    silent = propose_migrations(_ledger(*recent), CFG, NOW)
    assert silent["proposals"] == []


def test_live_scale_sample_fires_nothing_under_production_defaults():
    """What the live suite has produced is nowhere near the bar."""
    records = [
        decision_record(
            operation_anchor="getBalance",
            agent_id="agent-a",
            correlation_scope="task-12a",
            applied_tier=1,
            escalation_reason="none",
            disposition="execute",
            idempotency_key=_key(9),
            deployment_digest=DIGEST,
            declared_tier=1,
            record_id="live-t1",
            timestamp=TS,
        ),
        _t3_withhold(0),
        _outcome(0, failed=False),
        _t4(0, ts=TS),
        attempt_record(
            operation_anchor="updateCustomerProfile",
            declared_tier=3,
            deployment_digest=DIGEST,
            reason="custody-unavailable",
            record_id="att-1",
            timestamp=TS,
        ),
    ]
    doc = propose_migrations(_ledger(*records), now=NOW)
    assert doc["proposals"] == []
    assert doc["ctierSchema"] == "migration-proposals/0.1.0-draft"
