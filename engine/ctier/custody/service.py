# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Persist a withheld operation. Derive the idempotency key; do not store credentials.

Custody holds withheld operations and records the human decision against
them. v1 authenticates the approver as the `X-Approver-Id` header and
records that value so the named-approver claim is testable. Production
deployments bind this endpoint to their own identity provider and record
the identity that provider asserts. Do not treat `X-Approver-Id` as the
intended production mechanism.

Custody executes (task 10) under its own service identity, with the original
agent and the approver recorded as attribution. The backend will see custody;
the ledger will see who asked and who authorised.

Tier 3 executes under the system's identity, with the agent and the approver
recorded. Tier 4 executes under the human's own credential. In Tier 3 a named
person authorised an action; in Tier 4 a named person performed one. The
record says different things and it should.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field, model_validator

from ..classifier import GovernanceConfig, derive_idempotency_key
from ..models import Operation, Request
from .contract import pending_authorization, relay_headers
from .execute import Executor, build_outbound
from .store import DIGEST_SCHEMA_DEPLOYMENT, Store, strip_credentials
from ..ledger.records import decision_record, outcome_record

DEFAULT_REVIEW_PERIOD_SECONDS = 86400


class PersistIn(BaseModel):
    """What the enforcement point sends. Never a credential."""

    method: str
    path: str
    query: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    headers: dict[str, str] = Field(default_factory=dict)
    operation_anchor: str = Field(alias="operationAnchor")
    agent_id: str = Field(alias="agentId")
    task_id: Optional[str] = Field(default=None, alias="taskId")
    correlation_scope: Optional[str] = Field(default=None, alias="correlationScope")
    declared_tier: Optional[int] = Field(default=None, alias="declaredTier")
    applied_tier: int = Field(alias="appliedTier")
    deployment_digest: str = Field(alias="deploymentDigest")
    authority: Optional[str] = None
    credential_exp: Optional[int] = Field(default=None, alias="credentialExp")
    escalation_reason: Optional[str] = Field(default=None, alias="escalationReason")

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _no_legacy_digest(cls, data):
        if isinstance(data, dict):
            for old in ("composition", "compositionDigest"):
                if data.get(old):
                    raise ValueError(
                        f"{old!r} was removed in ctier-engine 0.3.0; "
                        "write 'deploymentDigest'"
                    )
        return data


@dataclass
class PersistOut:
    correlation_id: str
    created: bool
    body: dict[str, Any]
    headers: dict[str, str]
    row: dict[str, Any]


class DecisionError(Exception):
    """A decisions-endpoint failure with an HTTP status."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class DecisionOut:
    correlation_id: str
    decision: str
    approver: str
    status: str
    decided_at: str
    operation_class: str
    created: bool
    row: dict[str, Any]

    def body(self) -> dict[str, Any]:
        payload = {
            "correlationId": self.correlation_id,
            "decision": self.decision,
            "approver": self.approver,
            "status": self.status,
            "decidedAt": self.decided_at,
            "operationClass": self.operation_class,
        }
        if self.row.get("outcome_status") is not None or self.row.get("outcome_body"):
            payload["outcome"] = {
                "statusCode": self.row.get("outcome_status"),
                "body": self.row.get("outcome_body"),
                "reached": self.row.get("failure_reason") != "unreachable",
            }
        return payload


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def derive_deadline(
    now: datetime,
    credential_exp: Optional[int],
    review_period_seconds: int = DEFAULT_REVIEW_PERIOD_SECONDS,
) -> datetime:
    """min(credential remaining lifetime, configured review period).

    Uses the exp claim as a value, not the credential. Do not recompute later
    from a token that was never kept.
    """
    cap = timedelta(seconds=int(review_period_seconds))
    remaining = cap
    if credential_exp is not None:
        exp_at = datetime.fromtimestamp(int(credential_exp), tz=timezone.utc)
        remaining = exp_at - now.astimezone(timezone.utc)
        if remaining < timedelta(0):
            remaining = timedelta(0)
    if remaining > cap:
        remaining = cap
    return now.astimezone(timezone.utc) + remaining


def _key(payload: PersistIn, hmac_key: bytes) -> str:
    op = Operation(
        operation_id=payload.operation_anchor,
        method=payload.method,
        path_template=payload.path,
    )
    req = Request(
        method=payload.method,
        path=payload.path,
        query=dict(payload.query),
        body=payload.body,
        agent_id=payload.agent_id,
        task_id=payload.task_id,
    )
    return derive_idempotency_key(op, req, hmac_key)


def _infer_escalation(payload: PersistIn) -> str:
    if payload.escalation_reason:
        return payload.escalation_reason
    declared = payload.declared_tier
    applied = int(payload.applied_tier)
    if declared is None:
        return "undeclared-operation"
    if applied > declared:
        return "payload-exceeds-declared-bounds"
    return "none"


def _append_withhold_decision(store: Store, row: dict[str, Any], payload: PersistIn) -> None:
    """Evidence of a withhold. Must not unmake the persist if the write fails."""
    ledger = getattr(store, "ledger", None)
    if ledger is None:
        return
    try:
        ledger.append_decision(decision_record(
            operation_anchor=row["operation_anchor"],
            agent_id=row["agent_id"],
            correlation_scope=row["correlation_scope"],
            applied_tier=int(row["applied_tier"]),
            escalation_reason=_infer_escalation(payload),
            disposition="withhold",
            idempotency_key=row["idempotency_key"],
            deployment_digest=row["digest"],
            declared_tier=row.get("declared_tier"),
            correlation_id=row["correlation_id"],
            timestamp=row["created_at"],
        ))
    except Exception:
        return


def _append_outcome(store: Store, row: dict[str, Any]) -> None:
    ledger = getattr(store, "ledger", None)
    if ledger is None:
        return
    failed = row.get("status") == "failed"
    try:
        ledger.append_outcome(outcome_record(
            correlation_id=row["correlation_id"],
            approver=row.get("approver_id") or "",
            executed_at=row.get("executed_at") or row.get("decided_at") or "",
            failed=failed,
            result="failed" if failed else "executed",
            status_code=row.get("outcome_status"),
            timestamp=row.get("executed_at") or row.get("decided_at"),
        ))
    except Exception:
        return


def persist(
    store: Store,
    payload: PersistIn,
    *,
    now: Optional[datetime] = None,
    hmac_key: Optional[bytes] = None,
    review_period_seconds: int = DEFAULT_REVIEW_PERIOD_SECONDS,
    new_id: Optional[Callable[[], str]] = None,
) -> PersistOut:
    clock = now or datetime.now(timezone.utc)
    key_bytes = hmac_key if hmac_key is not None else GovernanceConfig().hmac_key
    derived = _key(payload, key_bytes)
    existing = store.get_by_idempotency(derived)
    if existing is not None:
        body = pending_authorization(
            correlation_id=existing["correlation_id"],
            classified_tier=int(existing["applied_tier"]),
            expires_at=existing["expires_at"],
            authority=existing.get("authority"),
        )
        headers = relay_headers(
            correlation_id=existing["correlation_id"],
            classified_tier=int(existing["applied_tier"]),
        )
        return PersistOut(
            correlation_id=existing["correlation_id"],
            created=False,
            body=body,
            headers=headers,
            row=existing,
        )

    headers_kept = strip_credentials(payload.headers)
    expires_at = derive_deadline(clock, payload.credential_exp, review_period_seconds)
    correlation_id = (new_id or (lambda: str(uuid.uuid4())))()
    scope = payload.correlation_scope or payload.task_id or payload.agent_id
    row = {
        "correlation_id": correlation_id,
        "idempotency_key": derived,
        "status": "pending",
        "method": payload.method.upper(),
        "path": payload.path,
        "query_json": json.dumps(dict(payload.query), sort_keys=True, separators=(",", ":")),
        "body": payload.body,
        "headers_json": json.dumps(headers_kept, sort_keys=True, separators=(",", ":")),
        "operation_anchor": payload.operation_anchor,
        "agent_id": payload.agent_id,
        "task_id": payload.task_id,
        "correlation_scope": scope,
        "declared_tier": payload.declared_tier,
        "applied_tier": int(payload.applied_tier),
        "digest": payload.deployment_digest,
        "digest_schema": DIGEST_SCHEMA_DEPLOYMENT,
        "authority": payload.authority,
        "credential_exp": payload.credential_exp,
        "expires_at": _iso(expires_at),
        "created_at": _iso(clock),
    }
    stored = store.insert(row)
    _append_withhold_decision(store, row, payload)
    body = pending_authorization(
        correlation_id=correlation_id,
        classified_tier=int(payload.applied_tier),
        expires_at=row["expires_at"],
        authority=payload.authority,
    )
    headers = relay_headers(
        correlation_id=correlation_id,
        classified_tier=int(payload.applied_tier),
    )
    return PersistOut(
        correlation_id=correlation_id,
        created=True,
        body=body,
        headers=headers,
        row=stored,
    )


def review_queue(store: Store, *, now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """Queue surface. No credential fields exist to redact.

    Expiry is evaluated lazily on read. No sweeper.
    """
    clock = now or datetime.now(timezone.utc)
    out = []
    for row in store.list_pending():
        row = materialize_expiry(store, row, clock)
        if row is None or row["status"] != "pending":
            continue
        out.append({
            "correlationId": row["correlation_id"],
            "method": row["method"],
            "path": row["path"],
            "query": json.loads(row["query_json"]),
            "body": row["body"],
            "operationAnchor": row["operation_anchor"],
            "agentId": row["agent_id"],
            "taskId": row["task_id"],
            "correlationScope": row["correlation_scope"],
            "declaredTier": row["declared_tier"],
            "appliedTier": row["applied_tier"],
            "deployment": row["digest"],
            "digestSchema": row["digest_schema"],
            "authority": row["authority"],
            "expiresAt": row["expires_at"],
            "createdAt": row["created_at"],
        })
    return out


def parse_expiry(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def materialize_expiry(store: Store, row: dict[str, Any], now: datetime) -> dict[str, Any]:
    """If pending and now is past expiresAt, the row is expired. No sweeper."""
    if row.get("status") != "pending":
        return row
    deadline = parse_expiry(row["expires_at"])
    if now.astimezone(timezone.utc) < deadline:
        return row
    updated = store.update_if_status(
        row["correlation_id"],
        "pending",
        {"status": "expired"},
    )
    return updated if updated is not None else store.get(row["correlation_id"]) or row


def _decision_out(row: dict[str, Any], *, created: bool) -> DecisionOut:
    return DecisionOut(
        correlation_id=row["correlation_id"],
        decision=row["decision"] or "",
        approver=row["approver_id"] or "",
        status=row["status"],
        decided_at=row["decided_at"] or "",
        operation_class=row["operation_anchor"],
        created=created,
        row=row,
    )


def decide(
    store: Store,
    correlation_id: str,
    decision: str,
    approver: str,
    *,
    now: Optional[datetime] = None,
    executor: Optional[Executor] = None,
    service_token: str = "",
    directory=None,
) -> DecisionOut:
    """Record a named approver's decision. On approval, execute from persisted context.

    The agent is not involved. Approving twice is answered from the terminal
    state and does not execute again.
    """
    if not (approver or "").strip():
        raise DecisionError(401, "approver required")
    who = approver.strip()
    verb = (decision or "").strip().lower()
    if verb in {"approve", "approved"}:
        verb = "approve"
    elif verb in {"reject", "rejected"}:
        verb = "reject"
    else:
        raise DecisionError(400, "decision must be approve or reject")

    clock = now or datetime.now(timezone.utc)
    row = store.get(correlation_id)
    if row is None:
        raise DecisionError(404, "unknown correlation id")
    row = materialize_expiry(store, row, clock)

    if row["status"] != "pending":
        return _decision_out(row, created=False)

    if verb == "reject":
        claimed = store.update_if_status(
            correlation_id,
            "pending",
            {
                "status": "rejected",
                "decision": "reject",
                "approver_id": who,
                "decided_at": _iso(clock),
            },
        )
        if claimed is None:
            current = store.get(correlation_id)
            if current is None:
                raise DecisionError(404, "unknown correlation id")
            return _decision_out(current, created=False)
        if directory is not None:
            directory.revoke(
                str(claimed.get("agent_id") or ""),
                str(claimed.get("operation_anchor") or ""),
            )
        return _decision_out(claimed, created=True)

    claimed = store.update_if_status(
        correlation_id,
        "pending",
        {
            "status": "executing",
            "decision": "approve",
            "approver_id": who,
            "decided_at": _iso(clock),
        },
    )
    if claimed is None:
        current = store.get(correlation_id)
        if current is None:
            raise DecisionError(404, "unknown correlation id")
        return _decision_out(current, created=False)

    if executor is None:
        finished = store.save(correlation_id, {"status": "approved"})
        return _decision_out(finished, created=True)

    outbound = build_outbound(claimed, approver=who, service_token=service_token)
    result = executor.execute(outbound)
    # One attempt. A silent retry is how an approved operation that did not
    # execute stops being visible. The approval remains; re-attempt is a
    # person's decision.
    if not result.reached:
        terminal = "failed"
        reason = "unreachable"
    elif result.status_code is None or int(result.status_code) >= 400:
        terminal = "failed"
        reason = f"http:{result.status_code}"
    else:
        terminal = "executed"
        reason = None
    finished = store.save(
        correlation_id,
        {
            "status": terminal,
            "outcome_status": result.status_code,
            "outcome_body": result.body,
            "executed_at": _iso(clock),
            "failure_reason": reason,
        },
    )
    _append_outcome(store, finished)
    return _decision_out(finished, created=True)
