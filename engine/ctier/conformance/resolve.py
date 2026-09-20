# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Resolve a corpus request to an OpenAPI operation, then to Operation."""
from __future__ import annotations

from typing import Optional

from ..corpus import _document, path_matches
from ..generate import flow_sort_key
from ..models import Criteria, Operation, Request, Tier
from ..validate import iter_operations


def operation_from_openapi(path: str, method: str, op: dict) -> Operation:
    bounds = op.get("x-ctier-bounds") if isinstance(op.get("x-ctier-bounds"), dict) else {}
    declared = None
    if "x-ctier-tier" in op:
        declared = Tier(int(op["x-ctier-tier"]))
    criteria = None
    if isinstance(op.get("x-ctier-criteria"), dict):
        criteria = Criteria.model_validate(op["x-ctier-criteria"])
    escalate_to = None
    if "x-ctier-escalate-to" in op:
        escalate_to = Tier(int(op["x-ctier-escalate-to"]))
    weight = op.get("x-ctier-weight")
    return Operation(
        operation_id=op.get("operationId"),
        method=method,
        path_template=path,
        declared_tier=declared,
        excluded=op.get("x-ctier-exclude") is True,
        criteria=criteria,
        rationale=op.get("x-ctier-rationale"),
        contributes_weight=int(weight) if weight is not None else None,
        escalate_to=escalate_to,
        max_result_bound=int(bounds["max"]) if "max" in bounds else None,
        bound_parameter=bounds.get("parameter"),
    )


def resolve_operation(qualified_spec, request: dict) -> Optional[Operation]:
    """Most specific matching operation. Unmatched paths return None (C2)."""
    doc = _document(qualified_spec)
    method = str(request["method"]).lower()
    path = request["path"]
    candidates = []
    for tmpl, m, op, _params in iter_operations(doc):
        if m != method or not path_matches(tmpl, path):
            continue
        oid = op.get("operationId") or ""
        candidates.append((flow_sort_key(tmpl, m, oid), tmpl, op))
    if not candidates:
        return None
    candidates.sort()
    _key, tmpl, op = candidates[0]
    return operation_from_openapi(tmpl, method, op)


def _string_map(values) -> dict[str, str]:
    if not values:
        return {}
    return {str(k): "" if v is None else str(v) for k, v in values.items()}


def request_from_case(case: dict) -> Request:
    req = case["request"]
    agent = case.get("agent") or {}
    body = req.get("body")
    return Request(
        method=str(req["method"]),
        path=req["path"],
        query=_string_map(req.get("query")),
        headers=_string_map(req.get("headers")),
        body=None if body is None else str(body),
        agent_id=agent.get("id") or "agent-a",
        task_id=case.get("scope") or agent.get("taskId"),
    )
