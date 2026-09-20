# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""recommend: description + rules + backend + now -> recommendation set.

Pure. now is an argument. The backend is the one impure dependency, and it is
passed in.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import sha256_hex
from .compose import Source, _load
from .errors import RecommendError
from .backend import BackendProposal, OperationView, RecommendationBackend
from .floor import classify_divergence, divergence_record, structural_floor
from .rules import first_match, load_rules, reversed_by
from .validate import iter_operations

APPLY_HELP = (
    "recommend --apply writes each proposal into the description as "
    "x-ctier-status: recommended and x-ctier-recommended-at. A partial "
    "criteria proposal is applied and the document is reported incomplete, "
    "naming the fields a human still has to supply. That invalidity is "
    "intended (spec 1.1.4): completeness is required at declaration, not "
    "at proposal. Declared operations are left untouched."
)

_FORBIDDEN_DEFAULT = frozenset({"data-sensitivity", "compliance-trigger"})
_CRITERIA_FIELDS = (
    "reversibility",
    "blast-radius",
    "data-sensitivity",
    "compliance-trigger",
    "idempotency",
)


def _as_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _stamp(now: datetime) -> str:
    return _as_utc(now).strftime("%Y-%m-%dT%H:%M:%SZ")


def jsonpath_target(path: str, method: str) -> str:
    escaped = path.replace("\\", "\\\\").replace("'", "\\'")
    return f"$.paths['{escaped}'].{method}"


def input_text(path: str, method: str, op: dict) -> str:
    parts = [f"{method.upper()} {path}"]
    if op.get("operationId"):
        parts.append(str(op["operationId"]))
    if op.get("summary"):
        parts.append(str(op["summary"]))
    if op.get("description"):
        parts.append(str(op["description"]))
    return "\n".join(parts)


def _property_names(op: dict) -> tuple[str, ...]:
    names: list[str] = []
    body = op.get("requestBody")
    if isinstance(body, dict):
        content = body.get("content") or {}
        for media in content.values() if isinstance(content, dict) else []:
            schema = (media or {}).get("schema") if isinstance(media, dict) else None
            props = (schema or {}).get("properties") if isinstance(schema, dict) else None
            if isinstance(props, dict):
                names.extend(props)
    return tuple(names)


def _view(path: str, method: str, op: dict) -> OperationView:
    return OperationView(
        operation_id=op.get("operationId"),
        method=method,
        path=path,
        summary=op.get("summary"),
        description=op.get("description"),
        tags=tuple(op.get("tags") or []),
        property_names=_property_names(op),
    )


def recommend(
    description: Source,
    rules: Path | bytes | dict,
    backend: RecommendationBackend,
    now: datetime,
) -> dict:
    """First-match structural rules, then the backend. Returns a recommendation set."""
    _raw, doc, _path = _load(description)
    rule_doc = load_rules(rules)
    reversed_ids = reversed_by(doc)
    stamp = _stamp(now)
    actions: list[dict] = []
    below_floor: list[dict] = []
    understates: list[dict] = []
    for path, method, op, _params in iter_operations(doc):
        matched = first_match(
            rule_doc["rules"],
            path=path,
            method=method,
            op=op,
            doc=doc,
            reversed_ids=reversed_ids,
        )
        source = None
        version = "0.1.0"
        confidence = None
        rationale = None
        propose: dict | None = None
        if matched:
            propose = dict(matched["propose"])
            source = matched["id"]
            confidence = matched["confidence"]
            rationale = matched["rationale"]
        else:
            proposal = backend.propose(_view(path, method, op))
            if proposal is None:
                continue
            source = backend.source()
            version = backend.version()
            confidence = proposal.confidence
            rationale = proposal.rationale
            propose = {}
            if proposal.tier is not None:
                propose["tier"] = proposal.tier
            if proposal.criteria:
                propose["criteria"] = dict(proposal.criteria)
        if not propose:
            continue
        text = input_text(path, method, op)
        update: dict[str, Any] = {
            "x-ctier-status": "recommended",
            "x-ctier-recommended-at": stamp,
        }
        if "tier" in propose:
            update["x-ctier-tier"] = int(propose["tier"])
        if "criteria" in propose:
            update["x-ctier-criteria"] = dict(propose["criteria"])
        if rationale:
            update["x-ctier-rationale"] = rationale
        actions.append({
            "target": jsonpath_target(path, method),
            "description": rationale,
            "update": update,
            "x-ctier-provenance": {
                "inputText": text,
                "inputDigest": sha256_hex(text.encode("utf-8")),
                "source": source,
                "version": version,
                "confidence": confidence,
                "timestamp": stamp,
            },
        })
        confirmed = _confirmed_tier(op)
        floor = structural_floor(propose)
        if confirmed is not None and floor is not None:
            kind = classify_divergence(confirmed, floor)
            record = divergence_record(
                operation_id=op.get("operationId"),
                method=method,
                path=path,
                confirmed=confirmed,
                floor=floor,
            )
            if kind == "below-floor":
                below_floor.append(record)
            elif kind == "understates":
                understates.append(record)
    result = {
        "ctierSchema": "recommendation-set/0.1.0",
        "overlay": "1.1.0",
        "info": {
            "title": "ctier recommendations",
            "version": "0.1.0",
        },
        "actions": actions,
    }
    if below_floor or understates:
        result["x-ctier-divergence"] = {
            "confirmedBelowFloor": below_floor,
            "descriptionUnderstates": understates,
        }
    return result


def _criteria_complete(block: dict) -> bool:
    return all(field in block for field in _CRITERIA_FIELDS)


def _confirmed_tier(op: dict) -> int | None:
    if op.get("x-ctier-status") != "declared" and "x-ctier-tier" not in op:
        if "x-ctier-criteria" not in op:
            return None
    if "x-ctier-tier" in op:
        return int(op["x-ctier-tier"])
    block = op.get("x-ctier-criteria")
    if isinstance(block, dict) and _criteria_complete(block):
        from .classifier import compute_tier
        from .models import Criteria
        return int(compute_tier(Criteria.model_validate(block)))
    return None


def apply_recommendations(
    description: Source,
    recommendation_set: dict,
    now: datetime,
) -> tuple[dict, dict]:
    """Write proposals inline. Partial criteria are applied and reported incomplete.

    See APPLY_HELP.
    """
    from .overlay import apply_overlay

    _raw, doc, _path = _load(description)
    report = {"applied": [], "skippedDeclared": [], "incomplete": []}
    overlay = {
        "actions": [],
    }
    for action in recommendation_set.get("actions") or []:
        target = action.get("target")
        update = dict(action.get("update") or {})
        # Resolve the current node to see if it is already declared.
        from jsonpath_rfc9535 import find
        nodes = list(find(target, doc)) if target else []
        declared = False
        for node in nodes:
            if isinstance(node.value, dict) and node.value.get("x-ctier-status") == "declared":
                declared = True
        if declared:
            report["skippedDeclared"].append(target)
            continue
        update["x-ctier-status"] = "recommended"
        update["x-ctier-recommended-at"] = update.get("x-ctier-recommended-at") or _stamp(now)
        overlay["actions"].append({**action, "update": update})
        missing = []
        criteria = update.get("x-ctier-criteria") or {}
        if criteria:
            missing = [f for f in _CRITERIA_FIELDS if f not in criteria]
        oid = None
        if nodes and isinstance(nodes[0].value, dict):
            oid = nodes[0].value.get("operationId")
        report["applied"].append(target)
        if missing:
            report["incomplete"].append({
                "target": target,
                "operationId": oid,
                "missing": missing,
            })
    if overlay["actions"]:
        doc, _zero = apply_overlay(doc, overlay)
    return doc, report
