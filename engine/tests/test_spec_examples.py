"""Cross-repo conformance: spec/examples/ is the shared validator corpus."""
from __future__ import annotations

import json

import pytest
import yaml

from ctier.compose import compose
from ctier.errors import ComposeError
from ctier.spec_loader import EXAMPLES_DIR, SPEC_DIR
from ctier.validate import validate_named_schema, validate_overlay_schema
from tests.golden_util import NOW

EXAMPLES = EXAMPLES_DIR
REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"

SCHEMA_FILES = {
    "classification-rules.valid.yaml": "classification-rules-0.1.0.json",
    "composition-manifest.valid.json": "composition-manifest-0.1.0.json",
    "recommendation-set.valid.yaml": "recommendation-set-0.1.0.json",
    "recommendation-partial.valid.yaml": "recommendation-set-0.1.0.json",
    "coverage-report.valid.json": "coverage-report-0.1.0.json",
}

COMPOSE_VALID = (
    "reversal.valid.yaml",
    "self-reversal.valid.yaml",
    "recommended.valid.yaml",
)

# Annotated reason -> ComposeError.rule. A mismatch is a specification bug.
INVALID = {
    "single-target.overlay.yaml": "single-target",
    "unidirectionality.operation.yaml": "unidirectionality",
    "bounds-coherence.operation.yaml": "bounds-coherence",
    "exclusion-exclusivity.operation.yaml": "exclusion-exclusivity",
    "criteria-incomplete.yaml": "schema",
    "criteria-proposal-empty.yaml": "schema",
    "recommended-missing-date.operation.yaml": "schema",
    "declared-with-recommended-at.operation.yaml": "schema",
    "tier2-unverified.yaml": "tier2-reversal",
    "reverses-dangling.yaml": "dangling-reverses",
    "self-reversal-unsafe.yaml": "self-reversal",
}

OPERATION_FRAGMENTS = {
    "unidirectionality.operation.yaml",
    "bounds-coherence.operation.yaml",
    "exclusion-exclusivity.operation.yaml",
    "recommended-missing-date.operation.yaml",
    "declared-with-recommended-at.operation.yaml",
}


def _load(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _wrap_operation(op: dict) -> bytes:
    wrapped = {
        "openapi": "3.1.0",
        "info": {"title": "fragment", "version": "0"},
        "paths": {"/x": {"get": op}},
    }
    return yaml.safe_dump(wrapped, sort_keys=False).encode("utf-8")


@pytest.mark.parametrize("name", COMPOSE_VALID)
def test_valid_openapi_example_composes(name: str):
    compose(EXAMPLES / name, [], NOW)


def test_recommendation_set_composes_against_the_reference_spec():
    compose(REFERENCE, [EXAMPLES / "recommendation-set.valid.yaml"], NOW)


@pytest.mark.parametrize("name,schema", list(SCHEMA_FILES.items()))
def test_valid_document_passes_schema(name: str, schema: str):
    validate_named_schema(schema, _load(EXAMPLES / name))


def test_criteria_incomplete_is_a_schema_error_naming_the_field():
    with pytest.raises(ComposeError, match="compliance-trigger") as exc:
        validate_named_schema(
            "classification-rules-0.1.0.json",
            _load(EXAMPLES / "invalid" / "criteria-incomplete.yaml"),
        )
    assert exc.value.rule == "schema"
    assert "criteriaProposal" not in str(exc.value)


def test_partial_inline_criteria_names_the_field_not_criteria_proposal():
    from ctier.validate import validate_operation_extensions

    op = {
        "operationId": "getBalance",
        "x-ctier-status": "declared",
        "x-ctier-criteria": {
            "reversibility": "not-applicable",
            "blast-radius": "single-record",
            "data-sensitivity": "internal",
            "idempotency": "inherently-safe",
        },
    }
    with pytest.raises(ComposeError, match="compliance-trigger") as exc:
        validate_operation_extensions(op)
    assert exc.value.rule == "schema"
    assert "criteriaProposal" not in str(exc.value)


def test_empty_criteria_proposal_is_a_schema_error():
    with pytest.raises(ComposeError) as exc:
        validate_named_schema(
            "recommendation-set-0.1.0.json",
            _load(EXAMPLES / "invalid" / "criteria-proposal-empty.yaml"),
        )
    assert exc.value.rule == "schema"


def test_single_target_overlay_rejected_against_reference_spec():
    overlay = EXAMPLES / "invalid" / "single-target.overlay.yaml"
    validate_overlay_schema(_load(overlay))
    with pytest.raises(ComposeError) as exc:
        compose(REFERENCE, [overlay], NOW)
    assert exc.value.rule == "single-target"


@pytest.mark.parametrize("name", sorted(OPERATION_FRAGMENTS))
def test_invalid_operation_fragment(name: str):
    expected = INVALID[name]
    with pytest.raises(ComposeError) as exc:
        compose(_wrap_operation(_load(EXAMPLES / "invalid" / name)), [], NOW)
    assert exc.value.rule == expected, (
        f"{name} rejected as {exc.value.rule!r}, annotated {expected!r}: {exc.value}"
    )


@pytest.mark.parametrize(
    "name",
    ["tier2-unverified.yaml", "reverses-dangling.yaml", "self-reversal-unsafe.yaml"],
)
def test_invalid_openapi_example(name: str):
    expected = INVALID[name]
    with pytest.raises(ComposeError) as exc:
        compose(EXAMPLES / "invalid" / name, [], NOW)
    assert exc.value.rule == expected, (
        f"{name} rejected as {exc.value.rule!r}, annotated {expected!r}: {exc.value}"
    )
