# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""cover: qualified spec + optional recommendations + now -> coverage report.

Pure. now is an argument. Ordering is the product: findings first, then
absent, recommended by floor descending, declared.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Union

from .canonical import canonical_json, sha256_hex
from .compose import Source, _as_utc, _load, _parse_stamp, _status_of
from .floor import (
    classify_divergence,
    divergence_record,
    floor_from_update,
    structural_floor,
)
from .recommend import jsonpath_target
from .validate import iter_operations, validate_named_schema

FAIL_ON = frozenset({"none", "absent", "recommended"})
WARN_FRACTION = 0.20
Document = Union[Source, dict]


def _as_document(source: Document) -> dict:
    if isinstance(source, dict):
        return source
    _raw, doc, _path = _load(source)
    return doc


def _index_recommendations(recommendations: Document | None) -> dict[str, dict]:
    by_target: dict[str, dict] = {}
    if not recommendations:
        return by_target
    recs = _as_document(recommendations)
    for action in recs.get("actions") or []:
        target = action.get("target")
        if target:
            by_target[target] = action
    return by_target


def _declared_tier(op: dict, status: str) -> int | None:
    if status != "declared":
        return None
    if "x-ctier-tier" in op:
        return int(op["x-ctier-tier"])
    if isinstance(op.get("x-ctier-criteria"), dict):
        return structural_floor({"criteria": op["x-ctier-criteria"]})
    return None


def _remaining_ttl(
    op: dict, now: datetime, ttl_days: int | None
) -> tuple[int | None, bool]:
    if ttl_days is None:
        return None, False
    raw = op.get("x-ctier-recommended-at")
    if not isinstance(raw, str):
        return None, False
    age = (_as_utc(now) - _as_utc(_parse_stamp(raw))).total_seconds()
    remaining = ttl_days * 86400 - age
    remaining_days = int(remaining // 86400)
    warn = remaining <= ttl_days * 86400 * WARN_FRACTION
    return remaining_days, warn


def cover(
    qualified_spec: Document,
    recommendations: Document | None,
    now: datetime,
) -> dict:
    doc = _as_document(qualified_spec)
    recs = _index_recommendations(recommendations)
    defaults = doc.get("x-ctier-defaults") or {}
    ttl = defaults.get("recommendationTtlDays")
    ttl_days = int(ttl) if ttl is not None else None

    below_floor: list[dict] = []
    understates: list[dict] = []
    warnings: list[dict] = []
    rows: list[dict] = []
    totals = {"declared": 0, "recommended": 0, "absent": 0}

    for path, method, op, _pp in iter_operations(doc):
        status = _status_of(op)
        totals[status] += 1
        action = recs.get(jsonpath_target(path, method))
        update = (action or {}).get("update") if action else None
        floor = floor_from_update(update)
        if floor is None and status == "recommended":
            floor = floor_from_update(op)
        declared = _declared_tier(op, status)

        row: dict[str, Any] = {
            "operationId": op.get("operationId"),
            "method": method,
            "path": path,
            "status": status,
        }
        if declared is not None:
            row["declaredTier"] = declared
        if floor is not None:
            row["structuralFloor"] = floor
            row["recommendedTier"] = floor
        if op.get("x-ctier-recommended-at"):
            row["recommendedAt"] = op["x-ctier-recommended-at"]
            remaining, warn = _remaining_ttl(op, now, ttl_days)
            if remaining is not None:
                row["ttlRemainingDays"] = remaining
                if warn and status == "recommended":
                    warnings.append({
                        "operationId": op.get("operationId"),
                        "method": method,
                        "path": path,
                        "ttlRemainingDays": remaining,
                    })
        if declared is not None and floor is not None:
            kind = classify_divergence(declared, floor)
            record = divergence_record(
                operation_id=op.get("operationId"),
                method=method,
                path=path,
                confirmed=declared,
                floor=floor,
            )
            if kind == "below-floor":
                below_floor.append(record)
                row["divergence"] = "below-floor"
            elif kind == "understates":
                understates.append(record)
                row["divergence"] = "understates"
        rows.append(row)

    def _sort_key(row: dict) -> tuple:
        status = row["status"]
        group = {"absent": 0, "recommended": 1, "declared": 2}[status]
        floor = row.get("structuralFloor")
        floor_key = -(floor if floor is not None else 0)
        return (group, floor_key, row["path"], row["method"])

    rows.sort(key=_sort_key)
    report: dict[str, Any] = {
        "ctierSchema": "coverage-report/0.1.0",
        "compositionDigest": sha256_hex(canonical_json(doc)),
        "totals": totals,
        "findings": {
            "confirmedBelowFloor": below_floor,
            "descriptionUnderstates": understates,
        },
        "operations": rows,
    }
    if warnings:
        report["expiryWarnings"] = warnings
    validate_named_schema("coverage-report-0.1.0.json", report)
    return report


def dump_coverage_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def evaluate_gate(report: dict, fail_on: str) -> int:
    """0 clean or not tripped, 1 gate tripped. Caller maps usage errors to 2."""
    if fail_on not in FAIL_ON:
        raise ValueError(f"fail-on must be one of {sorted(FAIL_ON)}")
    totals = report.get("totals") or {}
    if fail_on == "none":
        return 0
    if fail_on == "absent" and int(totals.get("absent") or 0) > 0:
        return 1
    if fail_on == "recommended" and (
        int(totals.get("recommended") or 0) > 0 or int(totals.get("absent") or 0) > 0
    ):
        return 1
    return 0


def render_coverage_text(report: dict) -> str:
    totals = report.get("totals") or {}
    ops = report.get("operations") or []
    n = len(ops)
    lines = [
        f"{n} operations · {totals.get('declared', 0)} declared · "
        f"{totals.get('recommended', 0)} recommended · "
        f"{totals.get('absent', 0)} unclassified",
        "",
    ]
    findings = report.get("findings") or {}
    below = findings.get("confirmedBelowFloor") or []
    under = findings.get("descriptionUnderstates") or []
    if below:
        lines.append("CONFIRMED BELOW STRUCTURAL FLOOR — review these first")
        for item in below:
            lines.append(
                f"  {item['method'].upper():6} {item['path']:40} "
                f"tier {item['declaredTier']}, floor {item['structuralFloor']}"
            )
        lines.append("")
    if under:
        lines.append("DESCRIPTION UNDERSTATES CONSEQUENCE")
        for item in under:
            lines.append(
                f"  {item['method'].upper():6} {item['path']:40} "
                f"tier {item['declaredTier']}, floor {item['structuralFloor']}"
            )
        lines.append("")
    absent = [r for r in ops if r["status"] == "absent"]
    if absent:
        lines.append("UNCLASSIFIED — tier 4 until declared")
        for row in absent:
            oid = row.get("operationId") or ""
            lines.append(f"  {row['method'].upper():6} {row['path']:40} {oid}")
        lines.append("")
    recommended = [r for r in ops if r["status"] == "recommended"]
    if recommended:
        lines.append("RECOMMENDED — awaiting review")
        for row in recommended:
            floor = row.get("structuralFloor")
            extra = f"floor {floor}" if floor is not None else ""
            oid = row.get("operationId") or ""
            lines.append(f"  {row['method'].upper():6} {row['path']:40} {oid} {extra}".rstrip())
        lines.append("")
    if report.get("expiryWarnings"):
        lines.append("EXPIRY WARNINGS")
        for w in report["expiryWarnings"]:
            lines.append(
                f"  {w['method'].upper():6} {w['path']:40} "
                f"{w.get('ttlRemainingDays')} days remaining"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
