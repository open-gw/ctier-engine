# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Evaluate classification-rules/0.1.0. First-match, closed predicates."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ..errors import RecommendError
from ..validate import iter_operations

DEFAULT_RULES = Path(__file__).resolve().parent / "default.yaml"

PREDICATES = frozenset({
    "method",
    "pathEndsWithParameter",
    "responseIsCollection",
    "hasRequestBody",
    "securitySchemes",
    "tagIn",
    "operationIdMatches",
    "hasDeclaredReversal",
    "pathSegmentCount",
    "pathParameterCount",
})

_PARAM_SEGMENT = re.compile(r"^\{[^}/]+\}$")
_SUCCESS = frozenset({"200", "201", "202", "203", "206", "default"})


def load_rules(source: Path | bytes | dict) -> dict:
    if isinstance(source, dict):
        document = source
    elif isinstance(source, Path):
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
    else:
        document = yaml.safe_load(source.decode("utf-8"))
    if not isinstance(document, dict):
        raise RecommendError("schema", "classification rules must be a mapping")
    if document.get("ctierSchema") != "classification-rules/0.1.0":
        raise RecommendError("schema", "ctierSchema must be classification-rules/0.1.0")
    rules = document.get("rules")
    if not isinstance(rules, list) or not rules:
        raise RecommendError("schema", "rules must be a non-empty array")
    for rule in rules:
        _validate_rule(rule)
    return document


def _validate_rule(rule: dict) -> None:
    if not isinstance(rule, dict):
        raise RecommendError("schema", "rule must be an object")
    rid = rule.get("id")
    if not rid:
        raise RecommendError("schema", "rule id is required")
    when = rule.get("when")
    if not isinstance(when, dict) or not when:
        raise RecommendError("schema", f"{rid}: when must be a non-empty object")
    unknown = sorted(set(when) - PREDICATES)
    if unknown:
        raise RecommendError(
            "unrecognised-predicate",
            f"{rid}: unrecognised predicate {unknown[0]}",
        )
    propose = rule.get("propose")
    if not isinstance(propose, dict):
        raise RecommendError("schema", f"{rid}: propose is required")
    has_tier = "tier" in propose
    has_criteria = "criteria" in propose
    if has_tier == has_criteria:
        raise RecommendError("schema", f"{rid}: propose must contain tier or criteria, never both")
    if has_criteria and (not isinstance(propose["criteria"], dict) or not propose["criteria"]):
        raise RecommendError("schema", f"{rid}: propose.criteria must have at least one field")
    if not rule.get("rationale"):
        raise RecommendError("schema", f"{rid}: rationale is required")
    if rule.get("confidence") not in {"high", "medium", "low"}:
        raise RecommendError("schema", f"{rid}: confidence must be high, medium, or low")


def reversed_by(doc: dict) -> set[str]:
    named = set()
    for _p, _m, op, _pp in iter_operations(doc):
        target = op.get("x-ctier-reverses")
        if isinstance(target, str) and target:
            named.add(target)
    return named


def path_segments(path: str) -> list[str]:
    return [s for s in path.strip("/").split("/") if s]


def path_parameter_count(path: str) -> int:
    return sum(1 for s in path_segments(path) if _PARAM_SEGMENT.match(s))


def path_ends_with_parameter(path: str) -> bool:
    segs = path_segments(path)
    return bool(segs) and bool(_PARAM_SEGMENT.match(segs[-1]))


def response_is_collection(op: dict, doc: dict | None = None) -> bool:
    responses = op.get("responses") or {}
    if not isinstance(responses, dict):
        return False
    for code, response in responses.items():
        if str(code) not in _SUCCESS or not isinstance(response, dict):
            continue
        if _schema_is_array(_response_schema(response), doc):
            return True
    return False


def _response_schema(response: dict) -> dict | None:
    content = response.get("content")
    if not isinstance(content, dict):
        return None
    for body in content.values():
        if isinstance(body, dict) and isinstance(body.get("schema"), dict):
            return body["schema"]
    return None


def _pointer_get(doc: dict, pointer: str) -> Any:
    """Resolve a JSON Pointer under ``doc``. ``pointer`` is the path after ``#``."""
    if not pointer.startswith("/"):
        return None
    node: Any = doc
    for raw in pointer[1:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _resolve_local_schema(
    schema: dict | None,
    doc: dict | None,
    seen: frozenset[str] | None = None,
) -> dict | None:
    """Follow local ``#/…`` refs before shape checks. Cycles and misses stay unresolved."""
    if not schema:
        return None
    ref = schema.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/") or doc is None:
        return schema
    if seen is None:
        seen = frozenset()
    if ref in seen:
        return None
    target = _pointer_get(doc, ref[1:])
    if not isinstance(target, dict):
        return schema
    return _resolve_local_schema(target, doc, seen | {ref})


def _schema_is_array(schema: dict | None, doc: dict | None = None) -> bool:
    resolved = _resolve_local_schema(schema, doc)
    if not resolved:
        return False
    if resolved.get("type") == "array":
        return True
    if "items" in resolved and resolved.get("type") is None:
        return True
    return False


def security_scheme_names(doc: dict, op: dict) -> set[str]:
    names = set()
    for block in (doc.get("security"), op.get("security")):
        if not isinstance(block, list):
            continue
        for req in block:
            if isinstance(req, dict):
                names.update(req)
    return names


def count_matches(expected: Any, actual: int) -> bool:
    if isinstance(expected, int):
        return actual == expected
    if isinstance(expected, dict):
        if "min" in expected and actual < int(expected["min"]):
            return False
        if "max" in expected and actual > int(expected["max"]):
            return False
        return True
    return False


def rule_matches(
    rule: dict,
    *,
    path: str,
    method: str,
    op: dict,
    doc: dict,
    reversed_ids: set[str],
) -> bool:
    when = rule["when"]
    unknown = sorted(set(when) - PREDICATES)
    if unknown:
        raise RecommendError(
            "unrecognised-predicate",
            f"{rule.get('id')}: unrecognised predicate {unknown[0]}",
        )
    if "method" in when:
        allowed = {m.lower() for m in when["method"]}
        if method not in allowed:
            return False
    if "pathEndsWithParameter" in when:
        if path_ends_with_parameter(path) is not bool(when["pathEndsWithParameter"]):
            return False
    if "responseIsCollection" in when:
        if response_is_collection(op, doc) is not bool(when["responseIsCollection"]):
            return False
    if "hasRequestBody" in when:
        if bool(op.get("requestBody")) is not bool(when["hasRequestBody"]):
            return False
    if "securitySchemes" in when:
        have = security_scheme_names(doc, op)
        want = set(when["securitySchemes"])
        if not want.issubset(have):
            return False
    if "tagIn" in when:
        tags = set(op.get("tags") or [])
        if not tags.intersection(when["tagIn"]):
            return False
    if "operationIdMatches" in when:
        if op.get("operationId") not in when["operationIdMatches"]:
            return False
    if "hasDeclaredReversal" in when:
        oid = op.get("operationId")
        named = bool(oid and oid in reversed_ids)
        if named is not bool(when["hasDeclaredReversal"]):
            return False
    if "pathSegmentCount" in when:
        if not count_matches(when["pathSegmentCount"], len(path_segments(path))):
            return False
    if "pathParameterCount" in when:
        if not count_matches(when["pathParameterCount"], path_parameter_count(path)):
            return False
    return True


def first_match(rules: list[dict], **ctx) -> dict | None:
    for rule in rules:
        if rule_matches(rule, **ctx):
            return rule
    return None
