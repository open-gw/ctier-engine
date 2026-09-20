# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Classification: resolve, then escalate.

The five criteria are evaluated by a human at design time and recorded in the
interface description document. At runtime this module RESOLVES the recorded
tier -- a lookup, not an evaluation -- and then applies adjustments derived from
information the specification could not have known.

Adjustment is unidirectional. The declared tier is a floor.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from .models import (
    EXCLUDED,
    BlastRadius,
    ComplianceTrigger,
    Criteria,
    Decision,
    Disposition,
    EscalationReason,
    Idempotency,
    Operation,
    Request,
    Reversibility,
    Sensitivity,
    Tier,
)

# Ordinal comparisons for the delegation check.
_RADIUS_ORDER = {b: i for i, b in enumerate(
    [BlastRadius.SINGLE_RECORD, BlastRadius.SINGLE_CUSTOMER,
     BlastRadius.POPULATION, BlastRadius.SYSTEM_WIDE])}
_SENSITIVITY_ORDER = {s: i for i, s in enumerate(
    [Sensitivity.PUBLIC, Sensitivity.INTERNAL,
     Sensitivity.PERSONAL, Sensitivity.REGULATED])}

TIER_WEIGHT = {Tier.LOW: 1, Tier.MEDIUM: 3, Tier.HIGH: 9, Tier.CRITICAL: 10_000}

DISPOSITION_FOR_TIER = {
    Tier.LOW: Disposition.EXECUTE,
    Tier.MEDIUM: Disposition.EXECUTE,
    Tier.HIGH: Disposition.WITHHOLD,
    Tier.CRITICAL: Disposition.REFUSE_AND_SUSPEND,
}


@dataclass
class GovernanceConfig:
    """Document-level defaults, read from x-ctier-defaults."""
    undeclared_operation_tier: Tier = Tier.CRITICAL
    escalate_above: int = 9
    decay_seconds: int = 1800
    require_scope_reduction: bool = True
    hmac_key: bytes = b"ctier-dev-key-replace-in-production"
    weights: dict[Tier, int] = field(default_factory=lambda: dict(TIER_WEIGHT))


def escalate(tier: Tier) -> Tier:
    """Raise a tier by one. Never lowers; Tier 4 is the ceiling."""
    return Tier(min(int(tier) + 1, int(Tier.CRITICAL)))


def compute_tier(c: Criteria) -> Tier:
    """First-match rules over the five criteria.

    Used where no tier has been declared, and as the comparison value where one
    has -- the higher of declared and computed is applied, never the lesser.
    """
    if c.reversibility is Reversibility.NONE:
        return Tier.CRITICAL
    if c.compliance_trigger is ComplianceTrigger.DIRECT:
        return Tier.CRITICAL
    # Population-scale WRITE. The population affected while the state stood is
    # unbounded, so the undo cannot restore the effect whatever the data was.
    # This is why blast radius outranks data sensitivity: not a precedence
    # preference, a collapse of reversibility.
    if (c.blast_radius in (BlastRadius.POPULATION, BlastRadius.SYSTEM_WIDE)
            and c.reversibility is not Reversibility.NOT_APPLICABLE):
        return Tier.CRITICAL
    # Population-scale READ. Reversibility does not describe disclosure -- you
    # cannot un-disclose -- so scale still carries consequence, but it is a delay
    # rather than a handover. A read that also trips a compliance obligation has
    # already returned Tier 4 from the DIRECT clause above.
    if (c.blast_radius in (BlastRadius.POPULATION, BlastRadius.SYSTEM_WIDE)
            and c.data_sensitivity in (Sensitivity.PERSONAL, Sensitivity.REGULATED)):
        return Tier.HIGH
    if c.reversibility is Reversibility.RESTORES_RECORD:
        return Tier.HIGH
    if c.data_sensitivity is Sensitivity.REGULATED:
        return Tier.HIGH
    if c.reversibility is Reversibility.RESTORES_EFFECT:
        return Tier.MEDIUM
    if c.reversibility is Reversibility.NOT_APPLICABLE and c.data_sensitivity in (
            Sensitivity.PUBLIC, Sensitivity.INTERNAL):
        return Tier.LOW
    return Tier.MEDIUM


def derive_idempotency_key(op: Operation, req: Request, key: bytes) -> str:
    """Derived, not generated.

    Anchored on the declared operationId so the key survives restructuring of
    the path; combined with the request specifics so two invocations of the same
    operation upon different subjects derive distinct keys.
    """
    body_canonical = ""
    if req.body:
        try:
            body_canonical = json.dumps(json.loads(req.body), sort_keys=True, separators=(",", ":"))
        except (ValueError, TypeError):
            body_canonical = req.body
    material = "\x1f".join([
        op.anchor(),
        req.path,
        json.dumps(dict(sorted(req.query.items())), separators=(",", ":")),
        body_canonical,
        req.agent_id,
        req.task_id or "",
    ])
    return hmac.new(key, material.encode(), hashlib.sha256).hexdigest()


def check_delegation(req: Request) -> bool:
    """True when any hop confers authority exceeding its parent.

    Evaluated before the operation itself, so an otherwise low-consequence
    operation conveyed by an expanded chain is governed by the expansion.
    """
    for parent, child in zip(req.delegation_chain, req.delegation_chain[1:]):
        if not set(child.scopes).issubset(set(parent.scopes)):
            return True
        if _RADIUS_ORDER[child.blast_radius] > _RADIUS_ORDER[parent.blast_radius]:
            return True
        if _SENSITIVITY_ORDER[child.data_sensitivity] > _SENSITIVITY_ORDER[parent.data_sensitivity]:
            return True
    return False


def exceeds_declared_bounds(op: Operation, req: Request) -> bool:
    """A declared tier assumes a bounded request. This checks the assumption.

    Spec 1.1.6: the parameter's value is a decimal number. Parsing it as an
    integer is fail-open — `int("101.0")` does not escalate a request that
    exceeds the bound.
    """
    if op.max_result_bound is None or not op.bound_parameter:
        return False
    raw = req.query.get(op.bound_parameter)
    if raw is None:
        return False
    try:
        n = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return False
    if not n.is_finite():
        return False
    return n > op.max_result_bound


class Accumulator:
    """Consequence accumulated across a correlation scope, with decay.

    Without decay the accumulated value of a long-running session increases
    monotonically until a well-behaved agent is treated as hostile.
    """

    def __init__(self, decay_seconds: int = 1800):
        self.decay_seconds = decay_seconds
        self._entries: dict[str, list[tuple[float, int]]] = {}

    def current(self, scope: str, now: Optional[float] = None) -> int:
        now = now if now is not None else time.time()
        entries = self._entries.get(scope, [])
        live = [(t, w) for t, w in entries if now - t < self.decay_seconds]
        self._entries[scope] = live
        return sum(w for _, w in live)

    def add(self, scope: str, weight: int, now: Optional[float] = None) -> None:
        now = now if now is not None else time.time()
        self._entries.setdefault(scope, []).append((now, weight))

    def reset(self, scope: str) -> None:
        self._entries.pop(scope, None)


class Classifier:
    def __init__(self, config: Optional[GovernanceConfig] = None,
                 accumulator: Optional[Accumulator] = None):
        self.config = config or GovernanceConfig()
        self.accumulator = accumulator or Accumulator(self.config.decay_seconds)

    def classify(self, op: Optional[Operation], req: Request,
                 now: Optional[float] = None) -> Decision:
        now = now if now is not None else time.time()
        scope = req.correlation_scope()
        reason = EscalationReason.NONE

        # ---- stage 0: exclusion -------------------------------------------
        # Not a tier. A live token reaching an excluded operation means a scope
        # was over-granted: a provisioning defect, surfaced rather than absorbed.
        if op is not None and op.excluded:
            return self._record(op, req, None, Tier.CRITICAL,
                                EscalationReason.NONE,
                                Disposition.REFUSE_PROVISIONING, scope, 0, now,
                                notes="excluded operation reached by a live credential")

        # ---- stage 1: delegation chain integrity --------------------------
        if check_delegation(req):
            anchor_op = op or Operation(method=req.method, path_template=req.path)
            return self._record(anchor_op, req, op.declared_tier if op else None,
                                Tier.CRITICAL, EscalationReason.DELEGATION_EXPANSION,
                                Disposition.REFUSE_AND_SUSPEND, scope, 0, now,
                                notes="authority expansion across delegation chain")

        # ---- stage 2: resolve, do not re-evaluate -------------------------
        if op is None:
            # No declaration in the composition. Fail closed (undeclared default).
            anchor_op = Operation(method=req.method, path_template=req.path)
            return self._record(anchor_op, req, None, self.config.undeclared_operation_tier,
                                EscalationReason.UNDECLARED,
                                DISPOSITION_FOR_TIER[self.config.undeclared_operation_tier],
                                scope, 0, now, notes="no x-ctier-* declaration")

        declared = op.declared_tier
        if declared is not None:
            tier = declared
        elif op.criteria is not None:
            tier = compute_tier(op.criteria)
        else:
            tier = self.config.undeclared_operation_tier
            reason = EscalationReason.UNDECLARED

        if declared is not None and op.criteria is not None:
            computed = compute_tier(op.criteria)
            if computed > tier:
                tier = computed
                reason = EscalationReason.COMPUTED_EXCEEDS_DECLARED

        # ---- stage 2b: request content exceeding declared bounds ----------
        if exceeds_declared_bounds(op, req):
            tier = escalate(tier)
            reason = EscalationReason.PAYLOAD_EXCEEDS_BOUNDS

        # ---- stage 3: accumulated consequence -----------------------------
        weight = (op.contributes_weight if op.contributes_weight is not None
                  else self.config.weights[tier])
        accumulated = self.accumulator.current(scope, now)
        if accumulated + weight > self.config.escalate_above and tier < Tier.CRITICAL:
            proposed = op.escalate_to or escalate(tier)
            if proposed > tier:
                tier = proposed
                reason = EscalationReason.SESSION_ACCUMULATION
        self.accumulator.add(scope, weight, now)

        # invariant C3: never below the declared tier
        if declared is not None and tier < declared:
            tier = declared

        return self._record(op, req, declared, tier, reason,
                            DISPOSITION_FOR_TIER[tier], scope,
                            accumulated + weight, now)

    def _record(self, op, req, declared, tier, reason, disposition, scope,
                accumulated, now, notes=None) -> Decision:
        return Decision(
            correlation_id=str(uuid.uuid4()),
            operation_anchor=op.anchor(),
            declared_tier=declared,
            applied_tier=tier,
            escalation_reason=reason,
            disposition=disposition,
            criteria=op.criteria,
            agent_id=req.agent_id,
            delegation_chain=[h.agent_id for h in req.delegation_chain],
            correlation_scope=scope,
            idempotency_key=derive_idempotency_key(op, req, self.config.hmac_key),
            accumulated_weight=accumulated,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            notes=notes,
        )
