"""Each default rule matches in isolation; none invents sensitivity or compliance."""
from __future__ import annotations

from pathlib import Path

import yaml

from ctier.recommend import recommend
from ctier.rules import DEFAULT_RULES, first_match, load_rules, reversed_by
from tests.test_recommend import NOW, _Silent, _doc


def test_default_rules_never_propose_sensitivity_or_compliance():
    text = DEFAULT_RULES.read_text(encoding="utf-8")
    assert "data-sensitivity" not in text
    assert "compliance-trigger" not in text


def test_default_rules_load():
    doc = load_rules(DEFAULT_RULES)
    assert [r["id"] for r in doc["rules"]] == [
        "get-single-resource",
        "read-singleton-subresource",
        "get-collection",
        "put-with-declared-reversal",
        "put-without-declared-reversal",
        "patch",
        "post-create",
        "delete-with-declared-reversal",
        "delete-without-declared-reversal",
    ]


def _match(path, method, op, extra_ops=None):
    rules = load_rules(DEFAULT_RULES)["rules"]
    paths = {path: {method: op}}
    if extra_ops:
        for p, m, o in extra_ops:
            paths.setdefault(p, {})[m] = o
    doc = {"paths": paths}
    return first_match(
        rules,
        path=path,
        method=method,
        op=op,
        doc=doc,
        reversed_ids=reversed_by(doc),
    )


def test_get_single_resource():
    op = {
        "operationId": "getItem",
        "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}},
    }
    m = _match("/items/{id}", "get", op)
    assert m["id"] == "get-single-resource"


def test_read_singleton_subresource_after_ends_with_parameter():
    singleton = {
        "operationId": "getProfile",
        "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}},
    }
    assert _match("/users/{id}/profile", "get", singleton)["id"] == "read-singleton-subresource"
    assert _match("/users/{id}/profile", "head", singleton)["id"] == "read-singleton-subresource"
    ending = {
        "operationId": "getUser",
        "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}},
    }
    assert _match("/users/{id}", "get", ending)["id"] == "get-single-resource"
    ids = [r["id"] for r in load_rules(DEFAULT_RULES)["rules"]]
    assert ids.index("get-single-resource") < ids.index("read-singleton-subresource")
    assert ids.index("read-singleton-subresource") < ids.index("get-collection")


def test_get_collection():
    op = {
        "operationId": "listItems",
        "responses": {"200": {"content": {"application/json": {"schema": {"type": "array"}}}}},
    }
    m = _match("/items", "get", op)
    assert m["id"] == "get-collection"


def test_put_with_and_without_reversal():
    put = {"operationId": "replaceItem"}
    assert _match("/items/{id}", "put", put)["id"] == "put-without-declared-reversal"
    restore = {"operationId": "restoreItem", "x-ctier-reverses": "replaceItem"}
    assert _match("/items/{id}", "put", put, extra_ops=[("/items/{id}", "post", restore)])["id"] == (
        "put-with-declared-reversal"
    )


def test_patch_post_delete():
    assert _match("/items/{id}", "patch", {"operationId": "p"})["id"] == "patch"
    assert _match("/items", "post", {"operationId": "c", "requestBody": {"content": {}}})["id"] == "post-create"
    delete = {"operationId": "d"}
    assert _match("/items/{id}", "delete", delete)["id"] == "delete-without-declared-reversal"
    undo = {"operationId": "undo", "x-ctier-reverses": "d"}
    assert _match("/items/{id}", "delete", delete, extra_ops=[("/x", "post", undo)])["id"] == (
        "delete-with-declared-reversal"
    )


def test_recommend_default_rules_emits_partial_criteria():
    desc = _doc((
        "/items/{id}",
        "get",
        {
            "operationId": "getItem",
            "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}},
        },
    ))
    rec = recommend(desc, DEFAULT_RULES, _Silent(), NOW)
    criteria = rec["actions"][0]["update"]["x-ctier-criteria"]
    assert "data-sensitivity" not in criteria
    assert "compliance-trigger" not in criteria
    assert criteria["reversibility"] == "not-applicable"
