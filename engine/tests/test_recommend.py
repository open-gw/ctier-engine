"""recommend: structural evaluation, purity, apply, null backend."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import yaml

from ctier.backend import NullBackend, OperationView
from ctier.canonical import canonical_json
from ctier.compose import compose
from ctier.errors import ComposeError, RecommendError
from ctier.recommend import APPLY_HELP, apply_recommendations, recommend
from ctier.validate import validate_named_schema

NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)


class _Silent:
    def propose(self, view: OperationView):
        return None

    def source(self) -> str:
        return "silent"

    def version(self) -> str:
        return "0"


def _doc(*ops: tuple[str, str, dict]) -> bytes:
    paths: dict = {}
    for path, method, op in ops:
        paths.setdefault(path, {})[method] = op
    return yaml.safe_dump(
        {"openapi": "3.1.0", "info": {"title": "t", "version": "1"}, "paths": paths},
        sort_keys=False,
    ).encode("utf-8")


def _rules(*rules: dict) -> dict:
    return {"ctierSchema": "classification-rules/0.1.0", "rules": list(rules)}


def test_unrecognised_predicate_fails_before_recommend():
    with pytest.raises(RecommendError) as exc:
        recommend(
            _doc(("/x", "get", {"operationId": "x"})),
            _rules({
                "id": "bad",
                "when": {"unknownPred": True},
                "propose": {"tier": 4},
                "rationale": "x",
                "confidence": "low",
            }),
            _Silent(),
            NOW,
        )
    assert exc.value.rule == "unrecognised-predicate"


def test_first_match_wins():
    rec = recommend(
        _doc(("/x", "get", {"operationId": "x"})),
        _rules(
            {
                "id": "first",
                "when": {"method": ["get"]},
                "propose": {"criteria": {"reversibility": "not-applicable"}},
                "rationale": "first rule",
                "confidence": "high",
            },
            {
                "id": "second",
                "when": {"method": ["get"]},
                "propose": {"tier": 4},
                "rationale": "should not fire",
                "confidence": "low",
            },
        ),
        _Silent(),
        NOW,
    )
    assert rec["actions"][0]["x-ctier-provenance"]["source"] == "first"
    assert rec["actions"][0]["update"]["x-ctier-criteria"] == {
        "reversibility": "not-applicable"
    }


def test_identical_inputs_and_now_are_byte_identical():
    desc = _doc(("/x", "get", {"operationId": "x"}))
    rules = _rules({
        "id": "get",
        "when": {"method": ["get"]},
        "propose": {"criteria": {"idempotency": "inherently-safe"}},
        "rationale": "read",
        "confidence": "high",
    })
    a = recommend(desc, rules, _Silent(), NOW)
    b = recommend(desc, rules, _Silent(), NOW)
    assert canonical_json(a) == canonical_json(b)
    assert a["actions"][0]["update"]["x-ctier-recommended-at"] == "2026-09-06T14:00:00Z"


def test_null_backend_contributes_nothing():
    rec = recommend(
        _doc(("/x", "post", {"operationId": "x"})),
        _rules({
            "id": "gets-only",
            "when": {"method": ["get"]},
            "propose": {"tier": 1},
            "rationale": "reads",
            "confidence": "high",
        }),
        NullBackend(),
        NOW,
    )
    assert rec["actions"] == []
    assert "x-ctier-divergence" not in rec


def test_apply_help_states_partial_is_intended():
    assert "incomplete" in APPLY_HELP
    assert "1.1.4" in APPLY_HELP


def test_apply_complete_proposal():
    desc = _doc(("/x", "get", {"operationId": "x"}))
    rec = recommend(
        desc,
        _rules({
            "id": "complete",
            "when": {"method": ["get"]},
            "propose": {
                "criteria": {
                    "reversibility": "not-applicable",
                    "blast-radius": "single-record",
                    "data-sensitivity": "public",
                    "compliance-trigger": "none",
                    "idempotency": "inherently-safe",
                }
            },
            "rationale": "complete judgement for the apply path",
            "confidence": "high",
        }),
        NullBackend(),
        NOW,
    )
    applied, report = apply_recommendations(desc, rec, NOW)
    assert report["incomplete"] == []
    op = applied["paths"]["/x"]["get"]
    assert op["x-ctier-status"] == "recommended"
    assert op["x-ctier-recommended-at"] == "2026-09-06T14:00:00Z"
    compose(yaml.safe_dump(applied).encode("utf-8"), [], NOW)


def test_apply_partial_reports_incomplete_and_compose_rejects():
    desc = _doc(("/x", "get", {"operationId": "x"}))
    rec = recommend(
        desc,
        _rules({
            "id": "partial",
            "when": {"method": ["get"]},
            "propose": {"criteria": {"reversibility": "not-applicable"}},
            "rationale": "only what the description shows",
            "confidence": "high",
        }),
        NullBackend(),
        NOW,
    )
    applied, report = apply_recommendations(desc, rec, NOW)
    missing = report["incomplete"][0]["missing"]
    assert "data-sensitivity" in missing
    assert "compliance-trigger" in missing
    assert applied["paths"]["/x"]["get"]["x-ctier-status"] == "recommended"
    with pytest.raises(ComposeError, match="blast-radius|data-sensitivity|compliance-trigger") as exc:
        compose(yaml.safe_dump(applied).encode("utf-8"), [], NOW)
    assert exc.value.rule == "schema"
    assert "criteriaProposal" not in str(exc.value)


def test_apply_skips_declared():
    desc = _doc((
        "/x",
        "get",
        {"operationId": "x", "x-ctier-tier": 1, "x-ctier-status": "declared"},
    ))
    rec = recommend(
        desc,
        _rules({
            "id": "get",
            "when": {"method": ["get"]},
            "propose": {"tier": 4},
            "rationale": "compare",
            "confidence": "low",
        }),
        NullBackend(),
        NOW,
    )
    applied, report = apply_recommendations(desc, rec, NOW)
    assert report["skippedDeclared"]
    assert applied["paths"]["/x"]["get"]["x-ctier-status"] == "declared"
    finding = rec["x-ctier-divergence"]["confirmedBelowFloor"][0]
    assert finding["declaredTier"] == 1
    assert finding["structuralFloor"] == 4


def test_recommendation_set_is_schema_valid():
    rec = recommend(
        _doc(("/x", "get", {"operationId": "x"})),
        _rules({
            "id": "get",
            "when": {"method": ["get"]},
            "propose": {"criteria": {"reversibility": "not-applicable"}},
            "rationale": "read",
            "confidence": "high",
        }),
        NullBackend(),
        NOW,
    )
    validate_named_schema("recommendation-set-0.1.0.json", rec)
