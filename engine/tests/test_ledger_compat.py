"""Superseded ledger names are rejected."""
from __future__ import annotations

import pytest

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

DIGEST = "sha256:" + "ab" * 32


def test_current_heads_still_map():
    assert resolve_record_kind("decision-record/0.2.0") == "decision"
    assert resolve_record_kind("decision") == "decision"


def test_legacy_heads_are_rejected():
    for head in REMOVED_SCHEMA_HEADS:
        with pytest.raises(ValueError, match=REMOVED_IN):
            resolve_record_kind(f"{head}/0.1.0")


def test_legacy_digest_fields_are_rejected():
    for old in LEGACY_DIGEST_FIELDS:
        with pytest.raises(ValueError, match=DIGEST_FIELD_REMOVED_IN):
            resolve_deployment_digest({old: DIGEST})


def test_deployment_digest_still_maps():
    assert resolve_deployment_digest({"deploymentDigest": DIGEST}) == DIGEST


def test_ingress_rejects_old_digest_names():
    with pytest.raises(ValueError, match="deploymentDigest"):
        decision_from_ingress({
            "operationAnchor": "getBalance",
            "agentId": "agent-a",
            "appliedTier": 1,
            "disposition": "execute",
            "composition": DIGEST,
            "method": "GET",
            "path": "/accounts/1/balance",
        })
    with pytest.raises(ValueError, match="deploymentDigest"):
        attempt_from_ingress({
            "operationAnchor": "updateCustomerProfile",
            "declaredTier": 3,
            "compositionDigest": DIGEST,
            "reason": "custody-unavailable",
        })


def test_removal_versions():
    assert REMOVED_IN == "0.2.0"
    assert DIGEST_FIELD_REMOVED_IN == "0.3.0"
    assert PLUGIN_CONFIG_REMOVED_IN == DIGEST_FIELD_REMOVED_IN
    assert HEADER_REMOVED_IN == DIGEST_FIELD_REMOVED_IN
