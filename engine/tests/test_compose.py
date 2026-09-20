"""compose purity, digest, strict zero-match."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from ctier.canonical import canonical_json, sha256_hex
from ctier.compose import compose
from ctier.errors import ComposeError

NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)


def _inline() -> bytes:
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "inline", "version": "1"},
        "paths": {
            "/ping": {
                "get": {
                    "operationId": "ping",
                    "x-ctier-tier": 1,
                    "x-ctier-status": "declared",
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
    }
    return yaml.safe_dump(doc, sort_keys=True).encode("utf-8")


def test_identical_inputs_and_now_are_byte_identical():
    raw = _inline()
    a_q, a_m = compose(raw, [], NOW)
    b_q, b_m = compose(raw, [], NOW)
    assert canonical_json(a_q) == canonical_json(b_q)
    assert canonical_json(a_m) == canonical_json(b_m)
    assert a_m["compositionDigest"] == sha256_hex(canonical_json(a_q))
    assert a_m["composedAt"] == "2026-09-06T14:00:00Z"
    assert a_m["specVersion"] == "1.4.0"


def test_digest_is_over_canonical_json_not_yaml():
    raw = _inline()
    qualified, manifest = compose(raw, [], NOW)
    assert manifest["compositionDigest"] == sha256_hex(canonical_json(qualified))
    assert manifest["inputs"][0]["digest"] == sha256_hex(raw)


def test_zero_match_warns_and_strict_fails(tmp_path: Path):
    desc = tmp_path / "openapi.yaml"
    desc.write_bytes(_inline())
    overlay = tmp_path / "miss.overlay.yaml"
    overlay.write_text(
        yaml.safe_dump({
            "overlay": "1.1.0",
            "info": {"title": "miss", "version": "1"},
            "actions": [
                {"target": "$.paths['/nope'].get", "update": {"x-ctier-tier": 4}},
            ],
        }),
        encoding="utf-8",
    )
    _q, manifest = compose(desc, [overlay], NOW)
    assert manifest["zeroMatchActions"][0]["matches"] == 0
    with pytest.raises(ComposeError, match="matched nothing") as exc:
        compose(desc, [overlay], NOW, strict=True)
    assert exc.value.rule == "zero-match"


def _recommended(ttl_days: int | None, stamped: bool) -> tuple[bytes, list[bytes]]:
    desc = {
        "openapi": "3.1.0",
        "info": {"title": "ttl", "version": "1"},
        "paths": {
            "/ping": {
                "get": {
                    "operationId": "ping",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    if ttl_days is not None:
        desc["x-ctier-defaults"] = {"recommendationTtlDays": ttl_days}
    overlay = {
        "overlay": "1.1.0",
        "info": {"title": "rec", "version": "1"},
        "actions": [
            {
                "target": "$.paths['/ping'].get",
                "update": {
                    "x-ctier-tier": 1,
                    "x-ctier-status": "recommended",
                    "x-ctier-criteria": {
                        "reversibility": "not-applicable",
                        "blast-radius": "single-record",
                        "data-sensitivity": "public",
                        "compliance-trigger": "none",
                        "idempotency": "inherently-safe",
                    },
                },
            }
        ],
    }
    if stamped:
        overlay["actions"][0]["x-ctier-provenance"] = {
            "timestamp": "2026-01-01T00:00:00Z",
        }
    return (
        yaml.safe_dump(desc, sort_keys=True).encode("utf-8"),
        [yaml.safe_dump(overlay, sort_keys=True).encode("utf-8")],
    )


def test_recommendation_expires_only_when_ttl_is_set():
    raw, overlays = _recommended(ttl_days=30, stamped=True)
    _q, manifest = compose(raw, overlays, NOW)
    assert manifest["coverage"]["absent"] == 1
    assert manifest["expiredRecommendations"][0]["operationId"] == "ping"
    leftover = _q["paths"]["/ping"]["get"]
    assert "x-ctier-tier" not in leftover
    assert "x-ctier-criteria" not in leftover
    assert "x-ctier-status" not in leftover


def test_recommendation_does_not_expire_when_ttl_unset():
    raw, overlays = _recommended(ttl_days=None, stamped=True)
    qualified, manifest = compose(raw, overlays, NOW)
    assert manifest["coverage"]["recommended"] == 1
    assert "expiredRecommendations" not in manifest
    assert qualified["paths"]["/ping"]["get"]["x-ctier-status"] == "recommended"


def test_recommended_at_is_carried_not_minted():
    raw, overlays = _recommended(ttl_days=None, stamped=True)
    later = datetime(2027, 1, 1, tzinfo=timezone.utc)
    first, _ = compose(raw, overlays, NOW)
    second, _ = compose(raw, overlays, later)
    a = first["paths"]["/ping"]["get"]["x-ctier-recommended-at"]
    b = second["paths"]["/ping"]["get"]["x-ctier-recommended-at"]
    assert a == b == "2026-01-01T00:00:00Z"


def test_recommendation_without_timestamp_is_invalid():
    raw, overlays = _recommended(ttl_days=30, stamped=False)
    with pytest.raises(ComposeError, match="x-ctier-recommended-at") as exc:
        compose(raw, overlays, NOW)
    assert exc.value.rule == "schema"


def test_compose_partial_criteria_never_reaches_compute_tier():
    called = {"n": 0}

    def wrapped(criteria):
        called["n"] += 1
        raise AssertionError("compute_tier must not run")

    doc = {
        "openapi": "3.1.0",
        "info": {"title": "partial", "version": "1"},
        "paths": {
            "/x": {
                "get": {
                    "operationId": "getBalance",
                    "x-ctier-criteria": {
                        "reversibility": "not-applicable",
                        "blast-radius": "single-record",
                        "data-sensitivity": "internal",
                        "idempotency": "inherently-safe",
                    },
                }
            }
        },
    }
    with pytest.raises(ComposeError, match="compliance-trigger") as exc:
        compose(yaml.safe_dump(doc).encode("utf-8"), [], NOW, compute=wrapped)
    assert exc.value.rule == "schema"
    assert called["n"] == 0
