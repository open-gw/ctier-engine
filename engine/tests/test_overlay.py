"""Overlay 1.1.0 merge, including array concatenation."""
from __future__ import annotations

import pytest

from ctier.errors import ComposeError
from ctier.overlay import apply_overlay, merge


def test_array_concatenation():
    target = {"tags": ["a"], "x-ctier-tier": 1}
    assert merge(target, {"tags": ["b"]})["tags"] == ["a", "b"]


def test_object_merge_and_primitive_replace():
    out = merge({"a": 1, "b": {"c": 2}}, {"a": 9, "b": {"d": 3}})
    assert out == {"a": 9, "b": {"c": 2, "d": 3}}


def test_apply_update_and_zero_match():
    doc = {"paths": {"/x": {"get": {"operationId": "x", "x-ctier-tier": 1}}}}
    overlay = {
        "overlay": "1.1.0",
        "info": {"title": "t", "version": "1"},
        "actions": [
            {
                "target": "$.paths['/x'].get",
                "update": {"x-ctier-tier": 2},
            },
            {
                "target": "$.paths['/missing'].get",
                "update": {"x-ctier-tier": 4},
            },
        ],
    }
    result, zero = apply_overlay(doc, overlay)
    assert result["paths"]["/x"]["get"]["x-ctier-tier"] == 2
    assert zero == [{"index": 1, "target": "$.paths['/missing'].get", "matches": 0}]


def test_remove():
    doc = {"paths": {"/x": {"get": {"operationId": "x", "deprecated": True}}}}
    overlay = {
        "actions": [
            {"target": "$.paths['/x'].get.deprecated", "remove": True},
        ]
    }
    result, zero = apply_overlay(doc, overlay)
    assert "deprecated" not in result["paths"]["/x"]["get"]
    assert zero == []


def test_incompatible_merge_errors():
    with pytest.raises(ComposeError, match="incompatible"):
        merge({"a": [1]}, {"a": {"x": 1}})


def test_update_appends_object_to_array_target():
    doc = {"paths": {"/x": {"get": {"parameters": [{"name": "id", "in": "path"}]}}}}
    overlay = {
        "actions": [
            {
                "target": "$.paths['/x'].get.parameters",
                "update": {"name": "limit", "in": "query"},
            }
        ]
    }
    result, zero = apply_overlay(doc, overlay)
    assert zero == []
    assert result["paths"]["/x"]["get"]["parameters"] == [
        {"name": "id", "in": "path"},
        {"name": "limit", "in": "query"},
    ]
