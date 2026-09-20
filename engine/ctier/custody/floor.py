# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Scope floor from the decision ledger.

Accumulation is a heuristic escalation, not an authorisation boundary. It
can only raise a tier above the floor already compiled into the
configuration. When the accumulated floor is unavailable, that compile-time
floor still governs: nothing is permitted that a human did not already
declare as sufficient. An unavailable floor is therefore no escalation,
not maximum escalation.

Attempts are not replayed: a refused operation caused no consequence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from ..classifier import Accumulator, GovernanceConfig, TIER_WEIGHT, escalate
from ..models import Tier

# The published floor when a scope is past the threshold. T1 decomposition
# becomes T2. Higher compiled tiers are unchanged by max().
PUBLISHED_FLOOR = int(escalate(Tier.LOW))


def _epoch(timestamp: str) -> float:
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    ).timestamp()


def decision_weight(record: dict[str, Any], weights: dict[Tier, int] | None = None) -> int:
    """Weight from the declared (compile-time) tier, not the applied tier.

    Weighting by applied tier after a floor raise would feed the floor back
    into itself: a T1 raised to T2 would weigh 3, and the floor would never
    recede. Declared is what the human set as sufficient for this operation.
    """
    table = weights or TIER_WEIGHT
    declared = record.get("declaredTier")
    applied = record.get("appliedTier")
    base = declared if isinstance(declared, int) else applied
    if base is None:
        return 0
    return int(table[Tier(int(base))])


def floors_from_decisions(
    decisions: list[dict[str, Any]],
    *,
    now: Optional[float] = None,
    config: Optional[GovernanceConfig] = None,
) -> dict[str, Any]:
    """Reuse Accumulator. One implementation of the weighting."""
    cfg = config or GovernanceConfig()
    clock = now if now is not None else datetime.now(timezone.utc).timestamp()
    acc = Accumulator(cfg.decay_seconds)
    scopes: list[str] = []
    seen: set[str] = set()
    for record in decisions:
        if record.get("type") not in (None, "decision"):
            continue
        if record.get("appliedTier") is None:
            continue
        scope = record.get("correlationScope")
        if not scope:
            continue
        ts = record.get("timestamp")
        when = _epoch(ts) if ts else clock
        acc.add(str(scope), decision_weight(record, cfg.weights), now=when)
        if scope not in seen:
            seen.add(scope)
            scopes.append(str(scope))
    floors = []
    for scope in scopes:
        total = acc.current(scope, clock)
        if total > cfg.escalate_above:
            floors.append({
                "correlationScope": scope,
                "floor": PUBLISHED_FLOOR,
                "accumulated": total,
            })
    floors.sort(key=lambda row: row["correlationScope"])
    return {
        "escalateAbove": cfg.escalate_above,
        "decaySeconds": cfg.decay_seconds,
        "floors": floors,
    }


def floors_from_ledger(ledger, *, now: Optional[float] = None, config: Optional[GovernanceConfig] = None) -> dict[str, Any]:
    return floors_from_decisions(
        ledger.list_records(record_type="decision"),
        now=now,
        config=config,
    )
