# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Ledger name mapping. Superseded names are rejected, not aliased."""
from __future__ import annotations

from typing import Any

CURRENT_SCHEMA_HEADS = {
    "decision-record": "decision",
    "attempt-record": "attempt",
    "outcome-record": "outcome",
}
REMOVED_SCHEMA_HEADS = {
    "ledger-decision": "decision",
    "ledger-attempt": "attempt",
    "ledger-outcome": "outcome",
}
REMOVED_IN = "0.2.0"
DIGEST_FIELD_REMOVED_IN = "0.3.0"
PLUGIN_CONFIG_REMOVED_IN = "0.3.0"
HEADER_REMOVED_IN = "0.3.0"
LEGACY_DIGEST_FIELDS = ("composition", "compositionDigest")


def resolve_record_kind(schema_or_type: str) -> str:
    """Map a `type` or current `ctierSchema` head to decision/attempt/outcome."""
    head = str(schema_or_type or "").split("/", 1)[0]
    if head in {"decision", "attempt", "outcome"}:
        return head
    if head in REMOVED_SCHEMA_HEADS:
        raise ValueError(
            f"{head!r} was removed in ctier-engine {REMOVED_IN}; "
            f"write {next(k for k, v in CURRENT_SCHEMA_HEADS.items() if v == REMOVED_SCHEMA_HEADS[head])!r}"
        )
    return CURRENT_SCHEMA_HEADS.get(head, "")


def resolve_deployment_digest(payload: dict[str, Any]) -> str:
    """Require `deploymentDigest`. Old field names are an error."""
    for old in LEGACY_DIGEST_FIELDS:
        if payload.get(old):
            raise ValueError(
                f"{old!r} was removed in ctier-engine {DIGEST_FIELD_REMOVED_IN}; "
                "write 'deploymentDigest'"
            )
    current = payload.get("deploymentDigest")
    if current:
        return str(current)
    raise ValueError("deploymentDigest is required")
