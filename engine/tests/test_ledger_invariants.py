"""C10 properties asserted as tests: no credential material, append-only.

If either fails against the natural implementation, that is a finding about
C10 — not something to patch around in the test.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ctier.custody.execute import ExecuteResult, RecordingExecutor
from ctier.custody.service import PersistIn, decide, persist
from ctier.custody.store import Store
from ctier.ledger.records import (
    attempt_record,
    credential_hits,
    decision_record,
)
from ctier.ledger import store as ledger_store

NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)
SECRET = "super-secret-bearer-token-11"
DIGEST = "sha256:" + "ab" * 32
TS = "2026-09-07T12:00:00Z"
KEY = "k" * 64


def _payload(**overrides) -> PersistIn:
    data = {
        "method": "PUT",
        "path": "/customers/customerId/preferences/communication",
        "query": {},
        "body": None,
        "headers": {
            "Authorization": f"Bearer {SECRET}",
            "X-Agent-Id": "agent-a",
        },
        "operationAnchor": "updateCommunicationPreferences",
        "agentId": "agent-a",
        "taskId": "task-1",
        "correlationScope": "task-1",
        "declaredTier": 3,
        "appliedTier": 3,
        "deploymentDigest": DIGEST,
        "authority": "communications",
        "credentialExp": int(NOW.timestamp()) + 3600,
    }
    data.update(overrides)
    return PersistIn.model_validate(data)


def _scan(records: list[dict], secret: str = SECRET) -> None:
    for record in records:
        hits = credential_hits(record, secret)
        assert hits == [], f"{record.get('ctierSchema')} {record.get('id')}: {hits}"
        blob = json.dumps(record, default=str)
        assert secret not in blob


def test_records_of_every_type_carry_no_credential_substring_or_field():
    """Drive Authorization through every disposition; scan what was written."""
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    executor = RecordingExecutor(results=[
        ExecuteResult(status_code=200, body='{"ok":true}', reached=True),
    ])
    decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )

    store.ledger.append_decision(decision_record(
        operation_anchor="getBalance",
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=1,
        escalation_reason="none",
        disposition="execute",
        idempotency_key=KEY,
        deployment_digest=DIGEST,
        declared_tier=1,
        record_id="dec-t1",
        timestamp=TS,
    ))
    store.ledger.append_decision(decision_record(
        operation_anchor="initiatePayment",
        agent_id="agent-a",
        correlation_scope="task-4",
        applied_tier=4,
        escalation_reason="none",
        disposition="refuse-and-suspend",
        idempotency_key=KEY,
        deployment_digest=DIGEST,
        declared_tier=4,
        record_id="dec-t4",
        timestamp=TS,
    ))
    store.ledger.append_decision(decision_record(
        operation_anchor="closeAccount",
        agent_id="agent-a",
        correlation_scope="task-x",
        applied_tier=4,
        escalation_reason="none",
        disposition="refuse-provisioning",
        idempotency_key=KEY,
        deployment_digest=DIGEST,
        declared_tier=4,
        record_id="dec-ex",
        timestamp=TS,
    ))
    store.ledger.append_attempt(attempt_record(
        operation_anchor="updateCustomerProfile",
        declared_tier=3,
        deployment_digest=DIGEST,
        reason="custody-unavailable",
        agent_id="agent-a",
        correlation_scope="task-1",
        record_id="att-1",
        timestamp=TS,
    ))

    records = store.ledger.list_records()
    types = {r["type"] for r in records}
    assert types == {"decision", "attempt", "outcome"}
    _scan(records)
    _scan([r for r in records if r["type"] == "decision"])
    _scan([r for r in records if r["type"] == "attempt"])
    _scan([r for r in records if r["type"] == "outcome"])


def test_written_records_are_never_updated_in_place():
    source = Path(ledger_store.__file__).read_text(encoding="utf-8")
    assert "UPDATE " not in source
    assert "DELETE FROM" not in source
    assert "REPLACE INTO" not in source
    assert not hasattr(ledger_store.Ledger, "update")
    assert not hasattr(ledger_store.Ledger, "save")
    assert not hasattr(ledger_store.Ledger, "update_if_status")

    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    first = store.ledger.list_records(record_type="decision")
    assert len(first) == 1
    decision_id = first[0]["id"]
    payload_before = json.dumps(first[0], sort_keys=True)

    executor = RecordingExecutor(results=[
        ExecuteResult(status_code=200, body='{"ok":true}', reached=True),
    ])
    decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    after = store.ledger.list_records()
    decisions = [r for r in after if r["type"] == "decision"]
    outcomes = [r for r in after if r["type"] == "outcome"]
    assert len(decisions) == 1
    assert decisions[0]["id"] == decision_id
    assert json.dumps(decisions[0], sort_keys=True) == payload_before
    assert len(outcomes) == 1
    assert outcomes[0]["correlationId"] == "corr-1"
    # Progress is a sequence. The pending row may mutate; the ledger must not.
    assert store.get("corr-1")["status"] == "executed"
