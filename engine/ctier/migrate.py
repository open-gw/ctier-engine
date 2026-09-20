# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Tier migration proposals from ledger evidence.

Pure. Emits a document a human reads. Nothing in this module writes a
declaration, patches a spec, or applies a proposal. The act of changing
a tier remains a declaration in the interface description.

Lowering requires a strictly higher evidence bar than raising: a larger
minimum sample, a longer window, and zero contrary events. A proposal
below the minimum is not emitted at all — not emitted with low confidence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union

import yaml
from jsonschema import Draft202012Validator

from .ledger.records import iso_now

SCHEMA = "migration-proposals/0.1.0-draft"
SCHEMA_PATH = Path(__file__).resolve().parent / "migration-proposals-0.1.0-draft.json"
BOUNDS = "payload-exceeds-declared-bounds"

LedgerLike = Union[Any, Iterable[dict[str, Any]]]


@dataclass(frozen=True)
class MigrationConfig:
    """Conservative defaults. Tests pass a smaller bar; production does not."""

    raise_min_sample: int = 10
    lower_min_sample: int = 50
    raise_window_seconds: int = 14 * 86400
    lower_window_seconds: int = 90 * 86400

    def __post_init__(self) -> None:
        if self.lower_min_sample <= self.raise_min_sample:
            raise ValueError("lower_min_sample must be strictly greater than raise_min_sample")
        if self.lower_window_seconds <= self.raise_window_seconds:
            raise ValueError("lower_window_seconds must be strictly greater than raise_window_seconds")


def _validate(document: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(document)


def _records(ledger: LedgerLike) -> list[dict[str, Any]]:
    if hasattr(ledger, "list_records"):
        return list(ledger.list_records())
    return list(ledger)


def _kind(record: dict[str, Any]) -> str:
    if record.get("type") in {"decision", "attempt", "outcome"}:
        return str(record["type"])
    from .ledger.compat import resolve_record_kind

    return resolve_record_kind(str(record.get("ctierSchema") or ""))


def _epoch(timestamp: str, fallback: float) -> float:
    if not timestamp:
        return fallback
    try:
        return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        ).timestamp()
    except ValueError:
        return fallback


def _in_window(record: dict[str, Any], now: float, window: int) -> bool:
    return (now - _epoch(str(record.get("timestamp") or ""), now)) < window


def _cid(record: dict[str, Any]) -> str:
    return str(record.get("correlationId") or record.get("id") or "")


def _proposal(
    *,
    operation: str,
    current: dict[str, Any],
    proposed: dict[str, Any],
    direction: str,
    signal: str,
    sample: int,
    window: int,
    contrary: int,
    counts: dict[str, int],
    ids: list[str],
) -> dict[str, Any]:
    return {
        "operationAnchor": operation,
        "current": current,
        "proposed": proposed,
        "direction": direction,
        "signal": signal,
        "sample": sample,
        "windowSeconds": window,
        "contraryEvents": contrary,
        "counts": counts,
        "correlationIds": [i for i in ids if i],
    }


def propose_migrations(
    ledger: LedgerLike,
    config: Optional[MigrationConfig] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    cfg = config or MigrationConfig()
    clock = now or datetime.now(timezone.utc)
    instant = clock.timestamp()
    rows = _records(ledger)
    decisions = [r for r in rows if _kind(r) == "decision"]
    attempts = [r for r in rows if _kind(r) == "attempt"]
    outcomes = [r for r in rows if _kind(r) == "outcome"]

    proposals: list[dict[str, Any]] = []
    proposals.extend(_tier3_always_approved(decisions, outcomes, cfg, instant))
    proposals.extend(_tier2_bounds(decisions, cfg, instant))
    proposals.extend(_tier3_rejected(decisions, outcomes, cfg, instant))
    proposals.extend(_tier4_never_attempted(decisions, attempts, cfg, instant))
    proposals.sort(key=lambda p: (p["operationAnchor"], p["signal"]))

    document = {
        "ctierSchema": SCHEMA,
        "generatedAt": iso_now(clock),
        "config": {
            "raiseMinSample": cfg.raise_min_sample,
            "lowerMinSample": cfg.lower_min_sample,
            "raiseWindowSeconds": cfg.raise_window_seconds,
            "lowerWindowSeconds": cfg.lower_window_seconds,
        },
        "proposals": proposals,
    }
    _validate(document)
    return document


def _tier3_always_approved(
    decisions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    cfg: MigrationConfig,
    now: float,
) -> list[dict[str, Any]]:
    window = cfg.lower_window_seconds
    by_op: dict[str, list[dict[str, Any]]] = {}
    for rec in decisions:
        if rec.get("appliedTier") != 3 or rec.get("disposition") != "withhold":
            continue
        if not _in_window(rec, now, window):
            continue
        by_op.setdefault(str(rec.get("operationAnchor") or ""), []).append(rec)
    executed = {o.get("correlationId") for o in outcomes if o.get("failed") is False}
    failed = {o.get("correlationId") for o in outcomes if o.get("failed") is True}
    out = []
    for op, group in by_op.items():
        if not op:
            continue
        ids = [r.get("correlationId") for r in group]
        ok = [str(i) for i in ids if i in executed]
        contrary = sum(1 for i in ids if i in failed)
        if contrary != 0:
            continue
        if len(ok) < cfg.lower_min_sample:
            continue
        out.append(_proposal(
            operation=op,
            current={"tier": 3},
            proposed={"tier": 2},
            direction="lower",
            signal="tier3-always-approved",
            sample=len(ok),
            window=window,
            contrary=0,
            counts={"approved": len(ok), "rejected": 0, "withheld": len(group)},
            ids=ok,
        ))
    return out


def _tier2_bounds(
    decisions: list[dict[str, Any]],
    cfg: MigrationConfig,
    now: float,
) -> list[dict[str, Any]]:
    window = cfg.raise_window_seconds
    by_op: dict[str, list[dict[str, Any]]] = {}
    for rec in decisions:
        if rec.get("escalationReason") != BOUNDS:
            continue
        declared = rec.get("declaredTier")
        if declared is not None and int(declared) > 2:
            continue
        if not _in_window(rec, now, window):
            continue
        by_op.setdefault(str(rec.get("operationAnchor") or ""), []).append(rec)
    out = []
    for op, group in by_op.items():
        if not op or len(group) < cfg.raise_min_sample:
            continue
        out.append(_proposal(
            operation=op,
            current={"tier": int(group[0].get("declaredTier") or 2)},
            proposed={"tier": 3},
            direction="raise",
            signal="tier2-bounds-escalated",
            sample=len(group),
            window=window,
            contrary=0,
            counts={"boundsEscalations": len(group)},
            ids=[_cid(r) for r in group],
        ))
    return out


def _tier3_rejected(
    decisions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    cfg: MigrationConfig,
    now: float,
) -> list[dict[str, Any]]:
    """Approvers declining. C8 rejection is not a ledger type; failed
    Outcomes joined to a T3 withhold are the evidence that exists.
    """
    window = cfg.raise_window_seconds
    withhold = [
        r for r in decisions
        if r.get("appliedTier") == 3
        and r.get("disposition") == "withhold"
        and _in_window(r, now, window)
    ]
    failed = {o.get("correlationId") for o in outcomes if o.get("failed") is True}
    executed = {o.get("correlationId") for o in outcomes if o.get("failed") is False}
    by_op: dict[str, list[str]] = {}
    contrary_by_op: dict[str, int] = {}
    for rec in withhold:
        op = str(rec.get("operationAnchor") or "")
        cid = rec.get("correlationId")
        if not op or not cid:
            continue
        if cid in failed:
            by_op.setdefault(op, []).append(str(cid))
        if cid in executed:
            contrary_by_op[op] = contrary_by_op.get(op, 0) + 1
    out = []
    for op, ids in by_op.items():
        if len(ids) < cfg.raise_min_sample:
            continue
        out.append(_proposal(
            operation=op,
            current={"tier": 3},
            proposed={"tier": 4},
            direction="raise",
            signal="tier3-repeatedly-rejected",
            sample=len(ids),
            window=window,
            contrary=contrary_by_op.get(op, 0),
            counts={"rejected": len(ids), "approved": contrary_by_op.get(op, 0)},
            ids=ids,
        ))
    return out


def _tier4_never_attempted(
    decisions: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    cfg: MigrationConfig,
    now: float,
) -> list[dict[str, Any]]:
    window = cfg.raise_window_seconds
    seen: dict[str, list[dict[str, Any]]] = {}
    for rec in (*decisions, *attempts):
        declared = rec.get("declaredTier")
        applied = rec.get("appliedTier")
        if declared != 4 and applied != 4 and rec.get("disposition") != "refuse-and-suspend":
            continue
        op = str(rec.get("operationAnchor") or "")
        if op:
            seen.setdefault(op, []).append(rec)
    out = []
    for op, group in seen.items():
        historical = [r for r in group if not _in_window(r, now, window)]
        recent = [r for r in group if _in_window(r, now, window)]
        if recent or len(historical) < cfg.raise_min_sample:
            continue
        out.append(_proposal(
            operation=op,
            current={"tier": 4},
            proposed={"excluded": True},
            direction="raise",
            signal="tier4-never-attempted",
            sample=len(historical),
            window=window,
            contrary=0,
            counts={"historical": len(historical), "inWindow": 0},
            ids=[_cid(r) for r in historical],
        ))
    return out


def dump_proposals(document: dict[str, Any]) -> str:
    return yaml.safe_dump(
        document,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
