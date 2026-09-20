# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""build_corpus: qualified spec -> classification-agreement corpus.

Pure. Deterministic. One generated case per operation; extras appended.
"""
from __future__ import annotations

from typing import Any, Union

import yaml

from .canonical import canonical_json, sha256_hex
from .classifier import compute_tier
from .compose import Source, _load
from .generate import _is_template, _openapi_segments
from .models import Criteria
from .validate import iter_operations

SCHEMA = "conformance-corpus/0.3.0"
DEPLOYMENTS = ("level-2", "level-3")

_TIER3_BY_LEVEL = {
    "level-2": "refuse-provisioning",
    "level-3": "withhold",
}

Document = Union[Source, dict]


def _document(source: Document) -> dict:
    if isinstance(source, dict):
        return source
    _raw, doc, _path = _load(source)
    return doc


def instantiate_path(template: str) -> str:
    """Satisfy an OpenAPI template with a stable, name-derived segment."""
    parts = []
    for seg in _openapi_segments(template):
        if _is_template(s := seg):
            parts.append(s[1:-1] or "id")
        else:
            parts.append(s)
    return "/" + "/".join(parts) if parts else "/"


def path_matches(template: str, actual: str) -> bool:
    ts = _openapi_segments(template)
    actuals = _openapi_segments(actual)
    if len(ts) != len(actuals):
        return False
    for t, a in zip(ts, actuals):
        if _is_template(t):
            continue
        if t != a:
            return False
    return True


def _expect_for_operation(op: dict) -> dict[str, Any]:
    if op.get("x-ctier-exclude") is True:
        return {"appliedTier": 4, "disposition": "refuse-provisioning"}
    declared = int(op["x-ctier-tier"]) if "x-ctier-tier" in op else None
    computed = None
    if isinstance(op.get("x-ctier-criteria"), dict):
        computed = int(compute_tier(Criteria.model_validate(op["x-ctier-criteria"])))
    if declared is None and computed is None:
        return {"appliedTier": 4, "disposition": "refuse-and-suspend"}
    if declared is None:
        tier = computed
    elif computed is None:
        tier = declared
    else:
        tier = max(declared, computed)
    if tier == 3:
        return {"appliedTier": 3, "dispositionByLevel": dict(_TIER3_BY_LEVEL)}
    if tier in (1, 2):
        return {"appliedTier": tier, "disposition": "execute"}
    return {"appliedTier": 4, "disposition": "refuse-and-suspend"}


def _generated_case(path: str, method: str, op: dict) -> dict:
    oid = op.get("operationId") or f"{method}-{path}"
    return {
        "id": f"generated-{oid}",
        "request": {
            "method": method.upper(),
            "path": instantiate_path(path),
            "query": {},
            "headers": {},
            "body": None,
        },
        "agent": {"id": "agent-a", "taskId": f"task-{oid}"},
        "expect": _expect_for_operation(op),
    }


def build_corpus(
    qualified_spec: Document,
    extras: list[dict] | None = None,
    *,
    deployment: str = "level-2",
) -> dict:
    if deployment not in DEPLOYMENTS:
        raise ValueError(f"unsupported deployment {deployment!r}")
    doc = _document(qualified_spec)
    cases = [
        _generated_case(path, method, op)
        for path, method, op, _pp in iter_operations(doc)
    ]
    if extras:
        cases.extend(extras)
    return {
        "ctierSchema": SCHEMA,
        "profile": "standard",
        "deployment": deployment,
        "composition": sha256_hex(canonical_json(doc)),
        "cases": cases,
    }


def load_extras(source: Document) -> list[dict]:
    if isinstance(source, dict):
        payload = source
    else:
        _raw, payload, _path = _load(source)
    cases = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("hand-written extras must be a list of cases")
    return cases


def dump_corpus(corpus: dict) -> str:
    return yaml.safe_dump(
        corpus,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
