"""Schema validation runs before Criteria / compute_tier."""
from __future__ import annotations

import pytest

from ctier.classifier import compute_tier
from ctier.errors import ComposeError
from ctier.validate import (
    validate_named_schema,
    validate_openapi_extensions,
    validate_operation_extensions,
    validate_operation_semantics,
    validate_semantics,
)


def test_partial_criteria_fails_naming_the_field_and_never_reaches_compute_tier():
    called = {"n": 0}

    def wrapped(criteria):
        called["n"] += 1
        return compute_tier(criteria)

    op = {
        "operationId": "getBalance",
        "x-ctier-criteria": {
            "reversibility": "not-applicable",
            "blast-radius": "single-record",
            "data-sensitivity": "internal",
            "idempotency": "inherently-safe",
        },
    }
    with pytest.raises(ComposeError, match="compliance-trigger") as exc:
        validate_operation_extensions(op)
        validate_operation_semantics(op, compute=wrapped)
    assert exc.value.rule == "schema"
    assert called["n"] == 0


def test_complete_criteria_on_openapi_passes_schema():
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            "/x": {
                "get": {
                    "operationId": "x",
                    "x-ctier-tier": 1,
                    "x-ctier-criteria": {
                        "reversibility": "not-applicable",
                        "blast-radius": "single-record",
                        "data-sensitivity": "internal",
                        "compliance-trigger": "none",
                        "idempotency": "inherently-safe",
                    },
                }
            }
        },
    }
    validate_openapi_extensions(doc)
    validate_semantics(doc)


def test_classification_rules_schema_rejects_incomplete_criteria():
    rules = {
        "ctierSchema": "classification-rules/0.1.0",
        "rules": [
            {
                "id": "incomplete-criteria",
                "when": {"method": ["get"]},
                "propose": {
                    "criteria": {
                        "reversibility": "not-applicable",
                        "blast-radius": "single-record",
                        "data-sensitivity": "internal",
                        "idempotency": "inherently-safe",
                    }
                },
                "rationale": "missing field",
                "confidence": "high",
            }
        ],
    }
    with pytest.raises(ComposeError, match="compliance-trigger"):
        validate_named_schema("classification-rules-0.1.0.json", rules)
