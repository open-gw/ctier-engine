"""Coverage report: floor, two findings, expiry warnings, gate."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import yaml

from ctier.cover import cover, dump_coverage_json, evaluate_gate, render_coverage_text
from ctier.validate import validate_named_schema

NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)


def _spec(ops: dict, defaults: dict | None = None) -> bytes:
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "c", "version": "1"},
        "paths": ops,
    }
    if defaults:
        doc["x-ctier-defaults"] = defaults
    return yaml.safe_dump(doc, sort_keys=False).encode("utf-8")


def test_cover_validates_against_schema():
    raw = _spec({
        "/x": {"get": {"operationId": "x", "x-ctier-tier": 1, "x-ctier-status": "declared"}},
        "/y": {"post": {"operationId": "y"}},
    })
    report = cover(raw, None, NOW)
    validate_named_schema("coverage-report-0.1.0.json", report)
    assert report["totals"] == {"declared": 1, "recommended": 0, "absent": 1}
    assert report["operations"][0]["status"] == "absent"
    assert report["operations"][1]["status"] == "declared"


def test_findings_are_separate_and_above_the_queue():
    raw = _spec({
        "/low": {
            "put": {
                "operationId": "overrideDown",
                "x-ctier-tier": 2,
                "x-ctier-status": "declared",
            }
        },
        "/high": {
            "post": {
                "operationId": "understated",
                "x-ctier-tier": 4,
                "x-ctier-status": "declared",
            }
        },
    })
    recs = {
        "ctierSchema": "recommendation-set/0.1.0",
        "overlay": "1.1.0",
        "info": {"title": "r", "version": "1"},
        "actions": [
            {
                "target": "$.paths['/low'].put",
                "update": {"x-ctier-criteria": {"reversibility": "undo-restores-record-only"}},
            },
            {
                "target": "$.paths['/high'].post",
                "update": {
                    "x-ctier-criteria": {
                        "reversibility": "not-applicable",
                        "blast-radius": "single-record",
                    }
                },
            },
        ],
    }
    report = cover(raw, recs, NOW)
    below = report["findings"]["confirmedBelowFloor"]
    under = report["findings"]["descriptionUnderstates"]
    assert below[0]["operationId"] == "overrideDown"
    assert below[0]["declaredTier"] == 2
    assert below[0]["structuralFloor"] == 3
    assert under[0]["operationId"] == "understated"
    assert under[0]["declaredTier"] == 4
    assert under[0]["structuralFloor"] == 1
    text = render_coverage_text(report)
    assert text.index("CONFIRMED BELOW STRUCTURAL FLOOR") < text.index("DESCRIPTION UNDERSTATES")


def test_expiry_warning_within_twenty_percent():
    raw = _spec(
        {
            "/x": {
                "get": {
                    "operationId": "x",
                    "x-ctier-status": "recommended",
                    "x-ctier-recommended-at": "2026-08-20T14:00:00Z",
                    "x-ctier-tier": 1,
                    "x-ctier-criteria": {
                        "reversibility": "not-applicable",
                        "blast-radius": "single-record",
                        "data-sensitivity": "public",
                        "compliance-trigger": "none",
                        "idempotency": "inherently-safe",
                    },
                }
            }
        },
        defaults={"recommendationTtlDays": 20},
    )
    report = cover(raw, None, NOW)
    assert report["expiryWarnings"][0]["operationId"] == "x"
    assert report["operations"][0]["ttlRemainingDays"] == 3


def test_gate_exit_codes():
    raw = _spec({
        "/a": {"get": {"operationId": "a"}},
        "/b": {
            "get": {
                "operationId": "b",
                "x-ctier-status": "recommended",
                "x-ctier-recommended-at": "2026-09-01T00:00:00Z",
                "x-ctier-tier": 1,
                "x-ctier-criteria": {
                    "reversibility": "not-applicable",
                    "blast-radius": "single-record",
                    "data-sensitivity": "public",
                    "compliance-trigger": "none",
                    "idempotency": "inherently-safe",
                },
            }
        },
    })
    report = cover(raw, None, NOW)
    assert evaluate_gate(report, "none") == 0
    assert evaluate_gate(report, "absent") == 1
    assert evaluate_gate(report, "recommended") == 1
    declared_only = cover(
        _spec({"/x": {"get": {"operationId": "x", "x-ctier-tier": 1, "x-ctier-status": "declared"}}}),
        None,
        NOW,
    )
    assert evaluate_gate(declared_only, "absent") == 0
    assert evaluate_gate(declared_only, "recommended") == 0


def test_gate_recommended_without_absent():
    raw = _spec({
        "/b": {
            "get": {
                "operationId": "b",
                "x-ctier-status": "recommended",
                "x-ctier-recommended-at": "2026-09-01T00:00:00Z",
                "x-ctier-tier": 1,
                "x-ctier-criteria": {
                    "reversibility": "not-applicable",
                    "blast-radius": "single-record",
                    "data-sensitivity": "public",
                    "compliance-trigger": "none",
                    "idempotency": "inherently-safe",
                },
            }
        },
    })
    report = cover(raw, None, NOW)
    assert report["totals"]["absent"] == 0
    assert evaluate_gate(report, "absent") == 0
    assert evaluate_gate(report, "recommended") == 1
    assert evaluate_gate(report, "none") == 0


def test_operations_ordered_absent_then_recommended_floor_then_declared():
    raw = _spec({
        "/declared": {
            "get": {
                "operationId": "d",
                "x-ctier-tier": 1,
                "x-ctier-status": "declared",
            }
        },
        "/absent": {"post": {"operationId": "a"}},
        "/rec-low": {
            "get": {
                "operationId": "rl",
                "x-ctier-status": "recommended",
                "x-ctier-recommended-at": "2026-09-01T00:00:00Z",
                "x-ctier-tier": 1,
                "x-ctier-criteria": {
                    "reversibility": "not-applicable",
                    "blast-radius": "single-record",
                    "data-sensitivity": "public",
                    "compliance-trigger": "none",
                    "idempotency": "inherently-safe",
                },
            }
        },
        "/rec-high": {
            "put": {
                "operationId": "rh",
                "x-ctier-status": "recommended",
                "x-ctier-recommended-at": "2026-09-01T00:00:00Z",
                "x-ctier-tier": 3,
                "x-ctier-criteria": {
                    "reversibility": "undo-restores-record-only",
                    "blast-radius": "single-record",
                    "data-sensitivity": "public",
                    "compliance-trigger": "none",
                    "idempotency": "safe",
                },
            }
        },
    })
    report = cover(raw, None, NOW)
    statuses = [row["status"] for row in report["operations"]]
    assert statuses == ["absent", "recommended", "recommended", "declared"]
    recs = [row for row in report["operations"] if row["status"] == "recommended"]
    assert recs[0]["operationId"] == "rh"
    assert recs[1]["operationId"] == "rl"
    validate_named_schema("coverage-report-0.1.0.json", json.loads(dump_coverage_json(report)))
