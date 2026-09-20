# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Structural floor: minimum tier the description supports.

Unknown criteria are filled with the lowest-consequence value. A ceiling is
not computed — an unknown compliance-trigger could be `direct` and would
force Tier 4 on every operation.
"""
from __future__ import annotations

from typing import Any

from .classifier import compute_tier
from .models import Criteria

LOWEST_CONSEQUENCE = {
    "reversibility": "not-applicable",
    "blast-radius": "single-record",
    "data-sensitivity": "public",
    "compliance-trigger": "none",
    "idempotency": "inherently-safe",
}

UNDERSTATES_GAP = 2


def structural_floor(propose: dict | None) -> int | None:
    """Floor from a proposal: an explicit tier, or compute after filling lowest."""
    if not propose:
        return None
    if "tier" in propose:
        return int(propose["tier"])
    criteria = propose.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        return None
    filled = {**LOWEST_CONSEQUENCE, **criteria}
    return int(compute_tier(Criteria.model_validate(filled)))


def floor_from_update(update: dict | None) -> int | None:
    if not update:
        return None
    propose: dict[str, Any] = {}
    if "x-ctier-tier" in update:
        propose["tier"] = update["x-ctier-tier"]
    if "x-ctier-criteria" in update:
        propose["criteria"] = update["x-ctier-criteria"]
    return structural_floor(propose)


def classify_divergence(confirmed: int, floor: int) -> str | None:
    if confirmed < floor:
        return "below-floor"
    if confirmed >= floor + UNDERSTATES_GAP:
        return "understates"
    return None


def divergence_record(
    *,
    operation_id: str | None,
    method: str,
    path: str,
    confirmed: int,
    floor: int,
) -> dict:
    return {
        "operationId": operation_id,
        "method": method,
        "path": path,
        "declaredTier": confirmed,
        "structuralFloor": floor,
    }
