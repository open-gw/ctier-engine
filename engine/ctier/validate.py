# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Schema validation first, then semantic. Never construct Criteria before schema."""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .canonical import sha256_hex
from .classifier import compute_tier
from .errors import ComposeError
from .models import Criteria
from .spec_loader import SCHEMA_DIR

_HTTP = frozenset(
    {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
)
_CRITERIA_FIELDS = (
    "reversibility",
    "blast-radius",
    "data-sensitivity",
    "compliance-trigger",
    "idempotency",
)
_SAFE_IDEMPOTENCY = frozenset({"inherently-safe", "safe"})


def _registry() -> Registry:
    resources = []
    for path in SCHEMA_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        resources.append(
            (data["$id"], Resource.from_contents(data, default_specification=DRAFT202012))
        )
        resources.append(
            (path.name, Resource.from_contents(data, default_specification=DRAFT202012))
        )
    return Registry().with_resources(resources)


_REGISTRY = _registry()


def _extensions() -> dict:
    return json.loads((SCHEMA_DIR / "ctier-extensions-0.1.0.json").read_text(encoding="utf-8"))


def _validator_for_def(name: str) -> Draft202012Validator:
    ext = _extensions()
    schema = {"$ref": f"ctier-extensions-0.1.0.json#/$defs/{name}"}
    return Draft202012Validator(schema, registry=_REGISTRY)


def schema_validator(schema_file: str) -> Draft202012Validator:
    """Validator for a vendored schema, with $ref resolved inside SCHEMA_DIR."""
    schema = json.loads((SCHEMA_DIR / schema_file).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_REGISTRY)


def _validate_against(schema_file: str, instance: Any, rule: str = "schema") -> None:
    validator = schema_validator(schema_file)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        path = "/".join(str(p) for p in err.path)
        raise ComposeError(rule, f"{path}: {err.message}" if path else err.message)


def validate_named_schema(schema_file: str, instance: Any) -> None:
    _validate_against(schema_file, instance, rule="schema")


def _check_extension_field(name: str, value: Any) -> None:
    key = {
        "x-ctier-tier": "tier",
        "x-ctier-criteria": "criteria",
        "x-ctier-exclude": "exclude",
        "x-ctier-bounds": "bounds",
        "x-ctier-handoff": "handoff",
        "x-ctier-status": "status",
        "x-ctier-rationale": "rationale",
        "x-ctier-weight": "weight",
        "x-ctier-escalate-to": "tier",
        "x-ctier-reverses": "reverses",
        "x-ctier-defaults": "defaults",
        "x-ctier-recommended-at": "recommendedAt",
    }.get(name)
    if key is None:
        return
    validator = _validator_for_def(key)
    errors = sorted(validator.iter_errors(value), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        missing = ""
        if name == "x-ctier-criteria":
            for field in _CRITERIA_FIELDS:
                if isinstance(value, dict) and field not in value:
                    raise ComposeError(
                        "schema",
                        f"{field} is a required property",
                    )
        path = "/".join(str(p) for p in err.path)
        raise ComposeError("schema", f"{path}: {err.message}" if path else err.message)


def iter_operations(doc: dict) -> list[tuple[str, str, dict, list]]:
    found = []
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        path_params = item.get("parameters") if isinstance(item.get("parameters"), list) else []
        for method, op in item.items():
            if method.lower() not in _HTTP or not isinstance(op, dict):
                continue
            found.append((path, method.lower(), op, path_params))
    return found


def _parameter_names(op: dict, path_params: list) -> set[str]:
    names = set()
    for param in list(path_params) + list(op.get("parameters") or []):
        if isinstance(param, dict) and param.get("name"):
            names.add(param["name"])
    return names


def validate_openapi_extensions(doc: dict) -> None:
    if "x-ctier-defaults" in doc:
        _check_extension_field("x-ctier-defaults", doc["x-ctier-defaults"])
    for _path, _method, op, _params in iter_operations(doc):
        validate_operation_extensions(op)


def validate_operation_extensions(op: dict) -> None:
    for key, value in op.items():
        if key.startswith("x-ctier-"):
            _check_extension_field(key, value)
    _check_operation_object(op)


def _check_operation_object(op: dict) -> None:
    validator = _validator_for_def("operation")
    errors = sorted(validator.iter_errors(op), key=lambda e: list(e.path))
    if not errors:
        return
    err = errors[0]
    if op.get("x-ctier-status") == "recommended" and "x-ctier-recommended-at" not in op:
        raise ComposeError("schema", "x-ctier-recommended-at is a required property")
    if op.get("x-ctier-status") != "recommended" and "x-ctier-recommended-at" in op:
        raise ComposeError(
            "schema",
            "x-ctier-recommended-at is forbidden unless x-ctier-status is recommended",
        )
    path = "/".join(str(p) for p in err.path)
    raise ComposeError("schema", f"{path}: {err.message}" if path else err.message)


def validate_overlay_schema(overlay: dict) -> None:
    if overlay.get("ctierSchema") == "recommendation-set/0.1.0":
        _validate_against("recommendation-set-0.1.0.json", overlay, rule="schema")
        return
    actions = overlay.get("actions")
    if not isinstance(actions, list):
        raise ComposeError("schema", "overlay actions must be an array")
    for action in actions:
        if not isinstance(action, dict):
            raise ComposeError("schema", "overlay action must be an object")
        update = action.get("update")
        if isinstance(update, dict):
            for key, value in update.items():
                if key.startswith("x-ctier-"):
                    _check_extension_field(key, value)


def _tier_from_update(update: dict, compute: Callable) -> Optional[int]:
    if "x-ctier-tier" in update:
        return int(update["x-ctier-tier"])
    if "x-ctier-criteria" in update:
        block = update["x-ctier-criteria"]
        _check_extension_field("x-ctier-criteria", block)
        return int(compute(Criteria.model_validate(block)))
    return None


def _reached_tier(op: dict, compute: Callable) -> Optional[int]:
    if "x-ctier-tier" in op:
        return int(op["x-ctier-tier"])
    if "x-ctier-criteria" in op:
        block = op["x-ctier-criteria"]
        _check_extension_field("x-ctier-criteria", block)
        return int(compute(Criteria.model_validate(block)))
    return None


def validate_semantics(
    doc: dict,
    *,
    overlays: Optional[list[tuple[dict, list]]] = None,
    compute: Callable = compute_tier,
) -> None:
    """overlays is a list of (overlay_doc, match_counts_per_action) after apply,
    or None to check only the composed description. Single-target is checked
    separately at apply time with live match counts.
    """
    ops = iter_operations(doc)
    op_by_id = {}
    for path, method, op, path_params in ops:
        oid = op.get("operationId")
        if oid:
            op_by_id[oid] = (path, method, op, path_params)

    reverses_targets = set()
    for _p, _m, op, _pp in ops:
        target = op.get("x-ctier-reverses")
        if target:
            reverses_targets.add(target)
            if target not in op_by_id:
                raise ComposeError(
                    "dangling-reverses",
                    f"x-ctier-reverses names {target!r} which does not exist",
                )

    for path, method, op, path_params in ops:
        if op.get("x-ctier-exclude") is True and "x-ctier-tier" in op:
            raise ComposeError(
                "exclusion-exclusivity",
                f"{op.get('operationId')}: x-ctier-exclude cannot appear with x-ctier-tier",
            )
        bounds = op.get("x-ctier-bounds")
        if isinstance(bounds, dict) and "parameter" in bounds:
            names = _parameter_names(op, path_params)
            if bounds["parameter"] not in names:
                raise ComposeError(
                    "bounds-coherence",
                    f"{op.get('operationId')}: x-ctier-bounds.parameter "
                    f"{bounds['parameter']!r} is not a parameter on the operation",
                )
        reached = _reached_tier(op, compute)
        escalate_to = op.get("x-ctier-escalate-to")
        if reached is not None and escalate_to is not None and int(escalate_to) < reached:
            raise ComposeError(
                "unidirectionality",
                f"{op.get('operationId')}: x-ctier-escalate-to {escalate_to} "
                f"resolves below the tier already reached ({reached})",
            )
        reverses = op.get("x-ctier-reverses")
        oid = op.get("operationId")
        if reverses and oid and reverses == oid:
            criteria = op.get("x-ctier-criteria") or {}
            idem = criteria.get("idempotency")
            if idem not in _SAFE_IDEMPOTENCY:
                raise ComposeError(
                    "self-reversal",
                    f"{oid}: self-reversal requires idempotency inherently-safe or safe",
                )
        is_tier2 = op.get("x-ctier-tier") == 2
        if not is_tier2 and "x-ctier-criteria" in op and "x-ctier-tier" not in op:
            is_tier2 = int(compute(Criteria.model_validate(op["x-ctier-criteria"]))) == 2
        if is_tier2 and oid and oid not in reverses_targets:
            raise ComposeError(
                "tier2-reversal",
                f"{oid}: Tier 2 must be named by an x-ctier-reverses",
            )


def validate_operation_semantics(op: dict, *, compute: Callable = compute_tier) -> None:
    """Semantic checks that can run on a single operation object."""
    wrap = {
        "openapi": "3.1.0",
        "info": {"title": "fragment", "version": "0"},
        "paths": {
            "/x": {
                "parameters": op.get("parameters") or [],
                "get": {k: v for k, v in op.items() if k != "parameters"},
            }
        },
    }
    validate_semantics(wrap, compute=compute)


def validate_single_target(
    update: dict,
    match_count: int,
    *,
    compute: Callable = compute_tier,
) -> None:
    if match_count <= 1:
        return
    if not any(k.startswith("x-ctier-") for k in update):
        return
    tier = _tier_from_update(update, compute)
    if tier is None:
        return
    if tier < 4:
        raise ComposeError(
            "single-target",
            f"overlay action assigning tier {tier} selected {match_count} operations",
        )
