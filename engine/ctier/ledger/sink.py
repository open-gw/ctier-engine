# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Where evidence goes. Custody is one sink, not the definition of one."""
from __future__ import annotations

from dataclasses import dataclass

from .records import SCHEMA_ATTEMPT, SCHEMA_DECISION, attempt_record, decision_record, validate_record

LOG_PREFIX = "[ctier-decision] "
ATTEMPT_LOG_PREFIX = "[ctier-attempt] "


@dataclass(frozen=True)
class Sink:
    """A place a decision record may be written."""

    name: str
    needs_runtime: bool
    durable: str  # "yes" | "operator" | "no"


CUSTODY = Sink("custody", needs_runtime=True, durable="yes")
GATEWAY_LOG = Sink("gateway-log", needs_runtime=False, durable="operator")

SINKS = (CUSTODY, GATEWAY_LOG)


def log_decision_record(
    *,
    operation_anchor: str,
    agent_id: str,
    correlation_scope: str,
    applied_tier: int,
    escalation_reason: str,
    disposition: str,
    deployment_digest: str,
    declared_tier: int | None = None,
    correlation_id: str,
    record_id: str | None = None,
    timestamp: str | None = None,
) -> dict:
    """A schema-valid Decision for a sink that is not custody.

    idempotencyKey is occupied by the correlation id so the record
    validates. It is not a C7 derived key and MUST NOT be forwarded
    as Idempotency-Key. C7 at this level is unmet by choice.
    """
    rid = record_id or correlation_id
    record = decision_record(
        operation_anchor=operation_anchor,
        agent_id=agent_id,
        correlation_scope=correlation_scope,
        applied_tier=applied_tier,
        escalation_reason=escalation_reason,
        disposition=disposition,
        idempotency_key=correlation_id,
        deployment_digest=deployment_digest,
        declared_tier=declared_tier,
        correlation_id=correlation_id,
        record_id=rid,
        timestamp=timestamp,
    )
    validate_record(record)
    assert record["ctierSchema"] == SCHEMA_DECISION
    return record


def log_attempt_record(
    *,
    operation_anchor: str,
    deployment_digest: str,
    reason: str,
    declared_tier: int | None = None,
    agent_id: str | None = None,
    correlation_scope: str | None = None,
    record_id: str | None = None,
    timestamp: str | None = None,
) -> dict:
    """A schema-valid Attempt for the gateway-log sink. appliedTier is null.

    declaredTier is present when a declaration was made and omitted
    when none was. Do not write 4 to mean unknown.
    """
    record = attempt_record(
        operation_anchor=operation_anchor,
        declared_tier=declared_tier,
        deployment_digest=deployment_digest,
        reason=reason,
        agent_id=agent_id,
        correlation_scope=correlation_scope,
        record_id=record_id,
        timestamp=timestamp,
    )
    validate_record(record)
    assert record["ctierSchema"] == SCHEMA_ATTEMPT
    assert record["appliedTier"] is None
    return record
