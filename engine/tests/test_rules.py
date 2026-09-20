"""Closed-predicate evaluation: first-match, fail on unrecognised keys."""
from __future__ import annotations

import pytest

from ctier.errors import RecommendError
from ctier.rules import first_match, load_rules, rule_matches, reversed_by


def _rule(**when):
    return {
        "id": "r",
        "when": when,
        "propose": {"tier": 1},
        "rationale": "test",
        "confidence": "high",
    }


def test_unrecognised_predicate_fails_loudly():
    with pytest.raises(RecommendError, match="pagination") as exc:
        load_rules({
            "ctierSchema": "classification-rules/0.1.0",
            "rules": [_rule(pagination=True, method=["get"])],
        })
    assert exc.value.rule == "unrecognised-predicate"


def test_first_match_by_document_order():
    rules = [
        _rule(method=["get"]),
        {**_rule(method=["get"]), "id": "second", "propose": {"tier": 4}},
    ]
    matched = first_match(
        rules,
        path="/x",
        method="get",
        op={"operationId": "x"},
        doc={"paths": {}},
        reversed_ids=set(),
    )
    assert matched["id"] == "r"


def test_path_and_collection_predicates():
    rule = _rule(
        method=["get"],
        pathEndsWithParameter=True,
        responseIsCollection=False,
    )
    op = {
        "operationId": "getOne",
        "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}},
    }
    assert rule_matches(
        rule, path="/items/{id}", method="get", op=op, doc={}, reversed_ids=set()
    )
    assert not rule_matches(
        rule, path="/items", method="get", op=op, doc={}, reversed_ids=set()
    )
    collection = {
        "responses": {"200": {"content": {"application/json": {"schema": {"type": "array"}}}}},
    }
    assert not rule_matches(
        rule, path="/items/{id}", method="get", op=collection, doc={}, reversed_ids=set()
    )


def test_has_declared_reversal():
    rule = _rule(hasDeclaredReversal=True)
    assert rule_matches(
        rule, path="/x", method="put", op={"operationId": "a"}, doc={}, reversed_ids={"a"}
    )
    assert not rule_matches(
        rule, path="/x", method="put", op={"operationId": "a"}, doc={}, reversed_ids=set()
    )


def test_path_counts():
    rule = _rule(pathSegmentCount={"min": 3}, pathParameterCount=2)
    assert rule_matches(
        rule,
        path="/a/{b}/c/{d}",
        method="get",
        op={},
        doc={},
        reversed_ids=set(),
    )
    assert not rule_matches(
        rule,
        path="/a/{b}",
        method="get",
        op={},
        doc={},
        reversed_ids=set(),
    )


def test_reversed_by_collects_targets():
    doc = {
        "paths": {
            "/x": {"put": {"operationId": "restore", "x-ctier-reverses": "update"}},
        }
    }
    assert reversed_by(doc) == {"update"}
