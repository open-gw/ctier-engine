"""Superseded names are rejected. Withdrawn names are not emitted."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ctier.compose import compose
from ctier.custody.contract import relay_headers
from ctier.generate import generate
from ctier.ledger.compat import (
    DIGEST_FIELD_REMOVED_IN,
    HEADER_REMOVED_IN,
    LEGACY_DIGEST_FIELDS,
    PLUGIN_CONFIG_REMOVED_IN,
    REMOVED_IN,
    REMOVED_SCHEMA_HEADS,
    resolve_deployment_digest,
    resolve_record_kind,
)
from ctier.ledger.records import attempt_from_ingress, decision_from_ingress
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_custody import _payload

DIGEST = "sha256:" + "ab" * 32
REPO = Path(__file__).resolve().parents[2]
HANDLER = REPO / "targets" / "kong" / "plugin" / "handler.lua"
SCHEMA_LUA = REPO / "targets" / "kong" / "plugin" / "schema.lua"
TARGETS = ("kong", "apisix", "apigee")

# Names that still appear because they are stripped or scanned, not emitted.
# Edit this list deliberately; a new mention of a withdrawn name that is not
# on it is a shim coming back.
EMIT_EXCEPTIONS = (
    "generate.CTIER_HEADERS",  # inbound strip documentation
    "generate.STRIP_ALIASES",  # inbound strip aliases
    "SC-StripCtierHeaders.xml",  # inbound alias strip
    "apisix.yaml strip walk",  # inbound prefix + alias clear
    "handler.lua ALIAS",  # inbound prefix + alias clear
    "boundary.probe",  # reserved-name reader scan
    "estate-probe",  # same
    "boundary.suite inbound forge",
)


def test_legacy_schema_heads_are_rejected():
    for head in REMOVED_SCHEMA_HEADS:
        with pytest.raises(ValueError, match=REMOVED_IN):
            resolve_record_kind(f"{head}/0.1.0")
    assert resolve_record_kind("decision-record/0.2.0") == "decision"


def test_legacy_digest_fields_are_rejected():
    for old in LEGACY_DIGEST_FIELDS:
        with pytest.raises(ValueError, match=DIGEST_FIELD_REMOVED_IN):
            resolve_deployment_digest({old: DIGEST})
    assert resolve_deployment_digest({"deploymentDigest": DIGEST}) == DIGEST


def test_ingress_rejects_composition_fields():
    base = {
        "operationAnchor": "getBalance",
        "agentId": "agent-a",
        "appliedTier": 1,
        "disposition": "execute",
        "method": "GET",
        "path": "/accounts/1/balance",
    }
    with pytest.raises(ValueError, match="deploymentDigest"):
        decision_from_ingress({**base, "composition": DIGEST})
    with pytest.raises(ValueError, match="deploymentDigest"):
        attempt_from_ingress({
            "operationAnchor": "updateCustomerProfile",
            "declaredTier": 3,
            "compositionDigest": DIGEST,
            "reason": "custody-unavailable",
        })
    decision = decision_from_ingress({**base, "deploymentDigest": DIGEST})
    assert decision["deploymentDigest"] == DIGEST


def test_persist_rejects_composition():
    with pytest.raises(ValidationError, match="composition"):
        _payload(composition=DIGEST)
    with pytest.raises(ValidationError, match="compositionDigest"):
        _payload(compositionDigest=DIGEST)


def test_plugin_schema_rejects_composition_key():
    text = SCHEMA_LUA.read_text(encoding="utf-8")
    assert "composition" not in text
    assert PLUGIN_CONFIG_REMOVED_IN == "0.3.0"


def test_nothing_emits_withdrawn_names():
    """13h's naming guard, extended: withdrawn names are not emitted.

    EMIT_EXCEPTIONS is the only place they may still be written, and every
    entry is a strip or a scanner — not an upstream or 202 write.
    """
    assert EMIT_EXCEPTIONS == (
        "generate.CTIER_HEADERS",
        "generate.STRIP_ALIASES",
        "SC-StripCtierHeaders.xml",
        "apisix.yaml strip walk",
        "handler.lua ALIAS",
        "boundary.probe",
        "estate-probe",
        "boundary.suite inbound forge",
    )
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    handler = HANDLER.read_text(encoding="utf-8")
    assert 'set_header("x-ctier-composition"' not in handler
    assert 'set_header("x-ctier-deployment"' in handler
    assert 'relay["X-Correlation-Id"]' not in handler
    assert HEADER_REMOVED_IN == "0.3.0"
    headers = relay_headers(correlation_id="c1", classified_tier=3)
    assert "X-Correlation-Id" not in headers
    assert "x-correlation-id" not in {k.lower() for k in headers}
    for name in TARGETS:
        files = generate(qualified, target=name, custody={"url": "http://custody:8080"})
        for path, text in files.items():
            assert "x-ctier-composition" not in text.lower(), (
                f"{name}:{path} still names x-ctier-composition"
            )
            if path.endswith("SC-StripCtierHeaders.xml"):
                assert "X-Correlation-Id" in text
                continue
            assert 'ngx.header["X-Correlation-Id"]' not in text, path
            if "RF-Withhold" in path:
                assert "X-Correlation-Id" not in text
                assert "x-ctier-correlation-id" in text


def test_202_carries_only_the_join_key():
    headers = relay_headers(correlation_id="corr-window", classified_tier=3)
    assert headers["x-ctier-correlation-id"] == "corr-window"
    assert "X-Correlation-Id" not in headers
