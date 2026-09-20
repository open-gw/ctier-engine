"""Custody store, persist, 202 contract, idempotency, deadline. No network."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ctier.custody.contract import AGENT_ACTION, pending_authorization, relay_headers
from ctier.custody.execute import (
    HEADER_AGENT,
    HEADER_APPROVER,
    HEADER_CORRELATION,
    HEADER_IDEMPOTENCY,
    ExecuteResult,
    RecordingExecutor,
)
from ctier.custody.service import PersistIn, decide, derive_deadline, persist, review_queue
from ctier.custody.store import (
    DIGEST_SCHEMA_COMPOSITION,
    DIGEST_SCHEMA_DEPLOYMENT,
    Store,
    row_contains_credential,
    strip_credentials,
)

NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)
SECRET = "super-secret-bearer-token-09"


def _payload(**overrides) -> PersistIn:
    data = {
        "method": "PUT",
        "path": "/customers/customerId/preferences/communication",
        "query": {},
        "body": None,
        "headers": {"X-Agent-Id": "agent-a", "Content-Type": "application/json"},
        "operationAnchor": "updateCommunicationPreferences",
        "agentId": "agent-a",
        "taskId": "task-1",
        "declaredTier": 3,
        "appliedTier": 3,
        "deploymentDigest": "sha256:" + "ab" * 32,
        "authority": "communications",
        "credentialExp": int(NOW.timestamp()) + 3600,
    }
    data.update(overrides)
    return PersistIn.model_validate(data)


def test_strip_credentials_drops_authorization_and_keeps_the_rest():
    kept = strip_credentials({
        "Authorization": f"Bearer {SECRET}",
        "X-Agent-Id": "agent-a",
        "Content-Type": "application/json",
    })
    assert "Authorization" not in kept
    assert {k.lower() for k in kept} == {"x-agent-id", "content-type"}
    assert SECRET not in json.dumps(kept)


def test_persist_does_not_store_anything_derived_from_authorization():
    store = Store()
    payload = _payload(headers={
        "Authorization": f"Bearer {SECRET}",
        "X-Agent-Id": "agent-a",
    })
    result = persist(store, payload, now=NOW, new_id=lambda: "corr-1")
    assert result.created is True
    row = store.get("corr-1")
    assert row is not None
    assert row_contains_credential(row, SECRET) is False
    assert "authorization" not in json.loads(row["headers_json"])
    assert "Authorization" not in json.loads(row["headers_json"])
    assert SECRET not in json.dumps(dict(row), default=str)
    queued = review_queue(store, now=NOW)
    assert SECRET not in json.dumps(queued)


def test_202_body_is_terminal_and_has_no_retry_after():
    body = pending_authorization(
        correlation_id="c1",
        classified_tier=3,
        expires_at="2026-09-07T13:00:00Z",
        authority="communications",
    )
    assert body["status"] == "pending_authorization"
    assert body["retryable"] is False
    assert body["agentAction"] == AGENT_ACTION
    assert body["correlationId"] == "c1"
    assert body["classifiedTier"] == 3
    assert body["authority"] == "communications"
    assert "pollUrl" not in body
    assert "Retry-After" not in body
    headers = relay_headers(correlation_id="c1", classified_tier=3)
    assert "Retry-After" not in headers
    assert headers["X-Agent-Action"] == AGENT_ACTION
    assert headers["x-ctier-correlation-id"] == "c1"
    assert "X-Correlation-Id" not in headers
    assert headers["Cache-Control"] == "no-store"


def test_duplicate_persist_yields_one_row_and_one_correlation_id():
    store = Store()
    a = persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    b = persist(store, _payload(), now=NOW, new_id=lambda: "corr-2")
    assert a.created is True
    assert b.created is False
    assert a.correlation_id == b.correlation_id == "corr-1"
    assert store.count() == 1
    assert a.body["correlationId"] == b.body["correlationId"]


def test_deadline_is_min_of_exp_remaining_and_review_period():
    hour = 3600
    exp_in_ten_minutes = int(NOW.timestamp()) + 600
    short = derive_deadline(NOW, exp_in_ten_minutes, review_period_seconds=hour)
    assert (short - NOW).total_seconds() == 600
    exp_in_two_hours = int(NOW.timestamp()) + 2 * hour
    capped = derive_deadline(NOW, exp_in_two_hours, review_period_seconds=hour)
    assert (capped - NOW).total_seconds() == hour
    no_exp = derive_deadline(NOW, None, review_period_seconds=hour)
    assert (no_exp - NOW).total_seconds() == hour


def test_persist_records_deadline_from_passed_exp_not_from_a_token():
    store = Store()
    exp = int(NOW.timestamp()) + 600
    result = persist(
        store,
        _payload(credentialExp=exp, headers={"Authorization": f"Bearer {SECRET}"}),
        now=NOW,
        review_period_seconds=3600,
        new_id=lambda: "corr-1",
    )
    assert result.body["expiresAt"] == "2026-09-07T12:10:00Z"
    row = store.get("corr-1")
    assert row["credential_exp"] == exp
    assert row_contains_credential(row, SECRET) is False


def test_review_queue_lists_the_pending_operation():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    queue = review_queue(store, now=NOW)
    assert len(queue) == 1
    assert queue[0]["correlationId"] == "corr-1"
    assert queue[0]["operationAnchor"] == "updateCommunicationPreferences"
    assert queue[0]["appliedTier"] == 3
    assert SECRET not in json.dumps(queue)


def test_anonymous_decision_is_rejected():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    from ctier.custody.service import DecisionError
    try:
        decide(store, "corr-1", "approve", "", now=NOW)
        raise AssertionError("expected DecisionError")
    except DecisionError as exc:
        assert exc.status_code == 401
    row = store.get("corr-1")
    assert row["status"] == "pending"
    assert row["approver_id"] is None


def test_approve_records_the_named_approver():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    result = decide(store, "corr-1", "approve", "analyst-1", now=NOW)
    assert result.created is True
    assert result.approver == "analyst-1"
    assert result.decision == "approve"
    assert result.status == "approved"
    assert result.operation_class == "updateCommunicationPreferences"
    row = store.get("corr-1")
    assert row["approver_id"] == "analyst-1"
    assert row["decided_at"] == "2026-09-07T12:00:00Z"
    assert row["decision"] == "approve"


def test_reject_records_and_does_not_leave_the_row_pending():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    result = decide(store, "corr-1", "reject", "analyst-1", now=NOW)
    assert result.status == "rejected"
    assert result.decision == "reject"
    assert result.approver == "analyst-1"
    assert result.operation_class == "updateCommunicationPreferences"
    assert store.get("corr-1")["status"] == "rejected"
    assert review_queue(store, now=NOW) == []


def test_second_approval_is_answered_from_the_terminal_state():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    first = decide(store, "corr-1", "approve", "analyst-1", now=NOW)
    second = decide(store, "corr-1", "approve", "analyst-2", now=NOW)
    assert first.created is True
    assert second.created is False
    assert second.approver == "analyst-1"
    assert second.status == "approved"
    row = store.get("corr-1")
    assert row["approver_id"] == "analyst-1"


def test_approve_executes_once_under_service_identity():
    store = Store()
    persist(
        store,
        _payload(headers={
            "Authorization": f"Bearer {SECRET}",
            "X-Agent-Id": "agent-a",
            "Content-Type": "application/json",
            HEADER_AGENT: "forged-agent",
            HEADER_APPROVER: "forged-approver",
        }),
        now=NOW,
        new_id=lambda: "corr-1",
    )
    executor = RecordingExecutor()
    result = decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    assert result.status == "executed"
    assert len(executor.calls) == 1
    outbound = executor.calls[0]
    assert outbound.method == "PUT"
    assert outbound.path == "/customers/customerId/preferences/communication"
    assert outbound.headers["Authorization"] == "Bearer custody-service"
    assert SECRET not in json.dumps(outbound.headers)
    lower = {k.lower(): v for k, v in outbound.headers.items()}
    assert HEADER_AGENT not in lower
    assert HEADER_APPROVER not in lower
    assert outbound.headers[HEADER_CORRELATION] == "corr-1"
    assert HEADER_IDEMPOTENCY in outbound.headers
    assert outbound.headers[HEADER_IDEMPOTENCY]
    row = store.get("corr-1")
    assert row["idempotency_key"] == outbound.headers[HEADER_IDEMPOTENCY]
    assert row_contains_credential(row, SECRET) is False


def test_double_approval_executes_once():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    executor = RecordingExecutor()
    first = decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    second = decide(
        store, "corr-1", "approve", "analyst-2",
        now=NOW, executor=executor, service_token="custody-service",
    )
    assert first.created is True
    assert first.status == "executed"
    assert second.created is False
    assert second.status == "executed"
    assert second.approver == "analyst-1"
    assert len(executor.calls) == 1


def test_reject_does_not_execute():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    executor = RecordingExecutor()
    result = decide(
        store, "corr-1", "reject", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    assert result.status == "rejected"
    assert executor.calls == []


def test_execution_failure_is_terminal_and_not_retried():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    executor = RecordingExecutor(results=[
        ExecuteResult(status_code=500, body='{"error":"boom"}', reached=True),
        ExecuteResult(status_code=200, body='{"ok":true}', reached=True),
    ])
    first = decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    assert first.status == "failed"
    assert first.row["decision"] == "approve"
    assert first.row["approver_id"] == "analyst-1"
    assert first.row["failure_reason"] == "http:500"
    assert first.row["outcome_status"] == 500
    second = decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    assert second.created is False
    assert second.status == "failed"
    assert len(executor.calls) == 1


def test_unreachable_backend_is_terminal_failure():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    executor = RecordingExecutor(results=[
        ExecuteResult(status_code=None, body="connection refused", reached=False),
    ])
    result = decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    assert result.status == "failed"
    assert result.row["failure_reason"] == "unreachable"
    assert result.row["decision"] == "approve"
    assert len(executor.calls) == 1


LATER = datetime(2026, 9, 7, 13, 0, 0, tzinfo=timezone.utc)


def test_past_expires_at_reads_as_expired():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    assert review_queue(store, now=NOW)[0]["correlationId"] == "corr-1"
    assert review_queue(store, now=LATER) == []
    row = store.get("corr-1")
    assert row["status"] == "expired"
    executor = RecordingExecutor()
    result = decide(
        store, "corr-1", "approve", "analyst-1",
        now=LATER, executor=executor, service_token="custody-service",
    )
    assert result.status == "expired"
    assert result.created is False
    assert executor.calls == []


def test_expiry_and_rejection_are_distinguishable():
    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-exp")
    persist(
        store,
        _payload(path="/customers/other/preferences/communication", operationAnchor="updateCommunicationPreferences-b"),
        now=NOW,
        new_id=lambda: "corr-rej",
    )
    decide(store, "corr-rej", "reject", "analyst-1", now=NOW)
    review_queue(store, now=LATER)
    expired = store.get("corr-exp")
    rejected = store.get("corr-rej")
    assert expired["status"] == "expired"
    assert rejected["status"] == "rejected"
    assert expired["approver_id"] is None
    assert rejected["approver_id"] == "analyst-1"
    assert rejected["decision"] == "reject"
    assert expired["decision"] is None
    assert expired["status"] != rejected["status"]


_OLD_PENDING_SCHEMA = """
CREATE TABLE pending (
  correlation_id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  query_json TEXT NOT NULL,
  body TEXT,
  headers_json TEXT NOT NULL,
  operation_anchor TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  task_id TEXT,
  correlation_scope TEXT NOT NULL,
  declared_tier INTEGER,
  applied_tier INTEGER NOT NULL,
  composition TEXT NOT NULL,
  authority TEXT,
  credential_exp INTEGER,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  approver_id TEXT,
  decided_at TEXT,
  decision TEXT,
  outcome_status INTEGER,
  outcome_body TEXT,
  executed_at TEXT,
  failure_reason TEXT
);
"""

_OLD_DIGEST = "sha256:" + "aa" * 32


def test_pending_rows_written_before_the_deployment_digest_are_marked_composition(
    tmp_path,
):
    """Existing rows are the old object. The hex cannot tell the two apart."""
    import sqlite3

    path = tmp_path / "custody.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(_OLD_PENDING_SCHEMA)
    for i in range(2):
        conn.execute(
            """
            INSERT INTO pending (
              correlation_id, idempotency_key, status, method, path,
              query_json, headers_json, operation_anchor, agent_id,
              correlation_scope, applied_tier, composition,
              expires_at, created_at
            ) VALUES (?, ?, 'pending', 'PUT', '/x', '{}', '{}', 'op',
                      'agent-a', 'agent-a', 3, ?,
                      '2026-09-08T12:00:00Z', '2026-09-07T12:00:00Z')
            """,
            (f"old-{i}", f"key-{i}", _OLD_DIGEST),
        )
    conn.commit()
    conn.close()

    store = Store(str(path))
    assert store.digest_backfill_count == 2
    columns = {
        row[1]
        for row in store._conn.execute("PRAGMA table_info(pending)").fetchall()
    }
    assert "composition" not in columns
    assert "digest" in columns
    assert "digest_schema" in columns
    for i in range(2):
        row = store.get(f"old-{i}")
        assert row["digest"] == _OLD_DIGEST
        assert row["digest_schema"] == DIGEST_SCHEMA_COMPOSITION
    persist(store, _payload(), now=NOW, new_id=lambda: "new-1")
    fresh = store.get("new-1")
    assert fresh["digest"] == _payload().deployment_digest
    assert fresh["digest_schema"] == DIGEST_SCHEMA_DEPLOYMENT
    assert fresh["digest"] != _OLD_DIGEST
    store.close()


def test_new_pending_row_stamps_the_deployment_digest_schema():
    store = Store()
    assert store.digest_backfill_count == 0
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    row = store.get("corr-1")
    assert row["digest_schema"] == DIGEST_SCHEMA_DEPLOYMENT
    assert "composition" not in row
    queue = review_queue(store, now=NOW)
    assert queue[0]["deployment"] == row["digest"]
    assert queue[0]["digestSchema"] == DIGEST_SCHEMA_DEPLOYMENT
    assert "composition" not in queue[0]
    store.close()
