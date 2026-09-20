# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""compose: description + overlays + now -> qualified spec, composition manifest.

Pure. now is an argument. No ambient clock.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence, Union

import yaml
from jsonpath_rfc9535 import find

from .canonical import canonical_json, sha256_hex
from .classifier import compute_tier
from .errors import ComposeError
from .overlay import apply_overlay
from .spec_loader import spec_version
from .validate import (
    iter_operations,
    validate_openapi_extensions,
    validate_overlay_schema,
    validate_semantics,
    validate_single_target,
)

Source = Union[Path, bytes, tuple[bytes, str]]


def _as_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _load(source: Source) -> tuple[bytes, dict, str]:
    if isinstance(source, Path):
        raw = source.read_bytes()
        path = source.name
    elif isinstance(source, tuple):
        raw, path = source
    else:
        raw = source
        path = "input"
    text = raw.decode("utf-8")
    if path.endswith(".json") or text.lstrip().startswith(("{", "[")):
        document = json.loads(text)
    else:
        document = yaml.safe_load(text)
    if not isinstance(document, dict):
        raise ComposeError("schema", f"{path} is not a mapping")
    return raw, document, path


def _status_of(op: dict) -> str:
    if op.get("x-ctier-exclude") is True:
        return "declared"
    status = op.get("x-ctier-status")
    if status == "recommended":
        return "recommended"
    if status == "declared" or "x-ctier-tier" in op or "x-ctier-criteria" in op:
        return "declared"
    return "absent"


def _coverage(doc: dict) -> dict[str, int]:
    counts = {"declared": 0, "recommended": 0, "absent": 0}
    for _p, _m, op, _pp in iter_operations(doc):
        counts[_status_of(op)] += 1
    return counts


def _expire_recommendations(doc: dict, now: datetime, reports: list[dict]) -> None:
    defaults = doc.get("x-ctier-defaults") or {}
    if "recommendationTtlDays" not in defaults:
        return
    ttl = int(defaults["recommendationTtlDays"])
    now_utc = _as_utc(now)
    for _p, _m, op, _pp in iter_operations(doc):
        if op.get("x-ctier-status") != "recommended":
            continue
        raw = op.get("x-ctier-recommended-at")
        if not isinstance(raw, str):
            continue
        stamped = _parse_stamp(raw)
        age = (now_utc - _as_utc(stamped)).total_seconds()
        if age > ttl * 86400:
            reports.append({
                "operationId": op.get("operationId"),
                "expiredRecommendation": True,
            })
            for key in (
                "x-ctier-status",
                "x-ctier-tier",
                "x-ctier-criteria",
                "x-ctier-rationale",
                "x-ctier-recommended-at",
            ):
                op.pop(key, None)


def _stamp_recommendation(op: dict, timestamp: str | None) -> None:
    """Carry the recommendation-set date. Never mint compose's now."""
    if op.get("x-ctier-status") != "recommended":
        return
    if "x-ctier-recommended-at" in op:
        return
    if timestamp:
        op["x-ctier-recommended-at"] = timestamp


def _parse_stamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def compose(
    description: Source,
    overlays: Sequence[Source] | None,
    now: datetime,
    *,
    strict: bool = False,
    compute: Callable = compute_tier,
) -> tuple[dict, dict]:
    """Apply overlays in order. Schema validate, then semantic validate, then models.

    Returns (qualified_spec, composition_manifest).
    """
    if overlays is None:
        overlays = []
    desc_raw, desc_doc, desc_path = _load(description)
    validate_openapi_extensions(desc_doc)

    overlay_loaded: list[tuple[bytes, dict, str]] = []
    for source in overlays:
        raw, doc, path = _load(source)
        validate_overlay_schema(doc)
        overlay_loaded.append((raw, doc, path))

    qualified = desc_doc
    zero_matches: list[dict] = []
    for _raw, overlay, _path in overlay_loaded:
        for action in overlay.get("actions") or []:
            target = action.get("target") or ""
            nodes = list(find(target, qualified)) if target else []
            update = action.get("update") if isinstance(action.get("update"), dict) else {}
            if update:
                validate_single_target(update, len(nodes), compute=compute)
        qualified, zero = apply_overlay(qualified, overlay)
        zero_matches.extend(zero)
        for action in overlay.get("actions") or []:
            update = action.get("update") if isinstance(action.get("update"), dict) else {}
            if update.get("x-ctier-status") != "recommended":
                continue
            ts = (action.get("x-ctier-provenance") or {}).get("timestamp")
            if not isinstance(ts, str) or not action.get("target"):
                continue
            for node in find(action["target"], qualified):
                if isinstance(node.value, dict):
                    _stamp_recommendation(node.value, ts)

    if zero_matches and strict:
        first = zero_matches[0]
        raise ComposeError(
            "zero-match",
            f"overlay action {first['index']} target {first['target']!r} matched nothing",
        )

    validate_openapi_extensions(qualified)
    validate_semantics(qualified, compute=compute)

    expiry_reports: list[dict] = []
    _expire_recommendations(qualified, now, expiry_reports)

    if expiry_reports:
        validate_semantics(qualified, compute=compute)

    digest = sha256_hex(canonical_json(qualified))
    inputs = [{
        "role": "description",
        "path": desc_path,
        "digest": sha256_hex(desc_raw),
    }]
    for order, (raw, _doc, path) in enumerate(overlay_loaded):
        inputs.append({
            "role": "overlay",
            "path": path,
            "digest": sha256_hex(raw),
            "order": order,
        })
    composed_at = _as_utc(now).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest: dict[str, Any] = {
        "ctierSchema": "composition-manifest/0.1.0",
        "composedAt": composed_at,
        "compositionDigest": digest,
        "inputs": inputs,
        "operations": len(iter_operations(qualified)),
        "coverage": _coverage(qualified),
        "specVersion": spec_version(),
    }
    if zero_matches:
        manifest["zeroMatchActions"] = zero_matches
    if expiry_reports:
        manifest["expiredRecommendations"] = expiry_reports
    return qualified, manifest
