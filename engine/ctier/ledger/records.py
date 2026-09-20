# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Construct the three ledger record types. Validate against the vendored schemas.

A Decision is a classification that was made. An Attempt is a refusal to
classify. An Outcome is what happened when an approved Tier 3 executed.
They are different things; a Decision with a null applied tier is not an
Attempt.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..classifier import GovernanceConfig, derive_idempotency_key
from ..models import Operation, Request
from ..spec_loader import schema_path
from ..validate import schema_validator
from .compat import resolve_deployment_digest

SCHEMA_DECISION = "decision-record/0.2.0"
SCHEMA_ATTEMPT = "attempt-record/0.3.0"
SCHEMA_OUTCOME = "outcome-record/0.1.0"

DISPOSITIONS = frozenset({
    "execute",
    "withhold",
    "refuse-and-suspend",
    "refuse-provisioning",
})

# Field names that would carry a credential or something derived from one.
# credential_exp is the exp claim taken from a bearer token: a value derived
# from a credential, even when the token itself is not kept.
CREDENTIAL_FIELD_NAMES = frozenset({
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "credential",
    "credentialexp",
    "credential_exp",
})


def _schema_file(ctier_schema: str) -> Path:
    return schema_path(ctier_schema.replace("/", "-") + ".json")


def load_schema(ctier_schema: str) -> dict[str, Any]:
    return json.loads(_schema_file(ctier_schema).read_text(encoding="utf-8"))


def validate_record(record: dict[str, Any]) -> None:
    schema_validator(_schema_file(record["ctierSchema"]).name).validate(record)


def iso_now(now: Optional[datetime] = None) -> str:
    clock = now or datetime.now(timezone.utc)
    return clock.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id() -> str:
    return str(uuid.uuid4())


def ledger_disposition(value: str) -> str:
    """Map the in-process classifier enum onto the corpus strings.

    `Disposition.REFUSE_AND_SUSPEND` is stored as `"refuse"` in the classifier.
    The ledger uses `"refuse-and-suspend"`. Do not write `"refuse"` here.
    """
    if value == "refuse":
        return "refuse-and-suspend"
    if value not in DISPOSITIONS:
        raise ValueError(f"unknown disposition {value!r}")
    return value


def derive_decision_key(
    *,
    operation_anchor: str,
    method: str,
    path: str,
    query: dict[str, str] | None,
    body: Optional[str],
    agent_id: str,
    task_id: Optional[str],
    hmac_key: Optional[bytes] = None,
) -> str:
    key_bytes = hmac_key if hmac_key is not None else GovernanceConfig().hmac_key
    op = Operation(operation_id=operation_anchor, method=method, path_template=path)
    req = Request(
        method=method,
        path=path,
        query=dict(query or {}),
        body=body,
        agent_id=agent_id,
        task_id=task_id,
    )
    return derive_idempotency_key(op, req, key_bytes)


def decision_record(
    *,
    operation_anchor: str,
    agent_id: str,
    correlation_scope: str,
    applied_tier: int,
    escalation_reason: str,
    disposition: str,
    idempotency_key: str,
    deployment_digest: str,
    declared_tier: Optional[int] = None,
    correlation_id: Optional[str] = None,
    record_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    record = {
        "ctierSchema": SCHEMA_DECISION,
        "id": record_id or new_id(),
        "timestamp": timestamp or iso_now(now),
        "operationAnchor": operation_anchor,
        "agentId": agent_id,
        "correlationScope": correlation_scope,
        "correlationId": correlation_id,
        "declaredTier": declared_tier,
        "appliedTier": int(applied_tier),
        "escalationReason": escalation_reason,
        "disposition": ledger_disposition(disposition),
        "idempotencyKey": idempotency_key,
        "deploymentDigest": deployment_digest,
    }
    validate_record(record)
    return record


def attempt_record(
    *,
    operation_anchor: str,
    deployment_digest: str,
    reason: str,
    declared_tier: Optional[int] = None,
    agent_id: Optional[str] = None,
    correlation_scope: Optional[str] = None,
    record_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    # Sequence is a sink property. epoch/seq stay on the error-log
    # line. Do not put them on this object.
    record = {
        "ctierSchema": SCHEMA_ATTEMPT,
        "id": record_id or new_id(),
        "timestamp": timestamp or iso_now(now),
        "operationAnchor": operation_anchor,
        "agentId": agent_id,
        "correlationScope": correlation_scope,
        "appliedTier": None,
        "deploymentDigest": deployment_digest,
        "reason": reason,
    }
    if declared_tier is not None:
        record["declaredTier"] = int(declared_tier)
    validate_record(record)
    return record


def outcome_record(
    *,
    correlation_id: str,
    approver: str,
    executed_at: str,
    failed: bool,
    result: Optional[str] = None,
    status_code: Optional[int] = None,
    record_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    if result is None:
        result = "failed" if failed else "executed"
    record = {
        "ctierSchema": SCHEMA_OUTCOME,
        "id": record_id or new_id(),
        "timestamp": timestamp or iso_now(now),
        "correlationId": correlation_id,
        "approver": approver,
        "executedAt": executed_at,
        "result": result,
        "failed": bool(failed),
        "statusCode": status_code,
    }
    validate_record(record)
    return record


def decision_from_ingress(
    payload: dict[str, Any],
    *,
    hmac_key: Optional[bytes] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Build a Decision from an enforcement-point POST. No inbound headers."""
    method = str(payload.get("method") or "GET")
    path = str(payload.get("path") or "/")
    agent_id = str(payload.get("agentId") or "unknown")
    task_id = payload.get("taskId")
    task_id = str(task_id) if task_id else None
    anchor = str(
        payload.get("operationAnchor")
        or f"{method.upper()} {path}"
    )
    scope = str(payload.get("correlationScope") or task_id or agent_id)
    key = payload.get("idempotencyKey")
    if not key:
        key = derive_decision_key(
            operation_anchor=anchor,
            method=method,
            path=path,
            query=payload.get("query") or {},
            body=payload.get("body"),
            agent_id=agent_id,
            task_id=task_id,
            hmac_key=hmac_key,
        )
    declared = payload.get("declaredTier")
    if declared is not None:
        declared = int(declared)
    return decision_record(
        operation_anchor=anchor,
        agent_id=agent_id,
        correlation_scope=scope,
        applied_tier=int(payload["appliedTier"]),
        escalation_reason=str(payload.get("escalationReason") or "none"),
        disposition=str(payload["disposition"]),
        idempotency_key=str(key),
        deployment_digest=resolve_deployment_digest(payload),
        declared_tier=declared,
        correlation_id=payload.get("correlationId"),
        record_id=payload.get("id"),
        timestamp=payload.get("timestamp"),
        now=now,
    )


def attempt_from_ingress(
    payload: dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    declared = payload.get("declaredTier")
    if declared is not None:
        declared = int(declared)
    return attempt_record(
        operation_anchor=str(payload["operationAnchor"]),
        declared_tier=declared,
        deployment_digest=resolve_deployment_digest(payload),
        reason=str(payload.get("reason") or "custody-unavailable"),
        agent_id=payload.get("agentId"),
        correlation_scope=payload.get("correlationScope"),
        record_id=payload.get("id"),
        timestamp=payload.get("timestamp"),
        now=now,
    )


def walk_keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            found.append(str(key))
            found.extend(walk_keys(inner))
    elif isinstance(value, list):
        for inner in value:
            found.extend(walk_keys(inner))
    return found


def credential_hits(record: dict[str, Any], secret: str) -> list[str]:
    """How a record would carry a credential, if it did.

    Asserted empty. A hit is a finding about C10, not something to patch
    around in the test.
    """
    hits: list[str] = []
    blob = json.dumps(record, default=str)
    if secret and secret in blob:
        hits.append("substring")
    for key in walk_keys(record):
        lowered = key.lower().replace("-", "")
        if key.lower() in CREDENTIAL_FIELD_NAMES or lowered in CREDENTIAL_FIELD_NAMES:
            hits.append(key)
        if "authorization" in key.lower() or key.lower() in {"cookie", "set-cookie"}:
            if key not in hits:
                hits.append(key)
    return hits
