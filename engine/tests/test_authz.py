"""Authorisation configuration: exclusion is a scope never granted."""
from __future__ import annotations

import pytest

from ctier.authz import (
    ACCESS_TOKEN_LIFESPAN,
    AGENT_CLIENT,
    AGENT_SUB_CLIENT,
    EXCHANGE_ATTRIBUTE,
    IDENTITY_SCOPE,
    scope_name,
)
from ctier.compose import compose
from ctier.custody.service import decide, persist
from ctier.custody.store import Store
from ctier.errors import GenerateError
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_custody import _payload
from tests.test_generate import _declared, _spec
from ctier.authz.directory import NullDirectory


def test_excluded_operation_scope_is_absent_from_the_agent_client():
    raw = _spec({
        "/ok": {"get": _declared(1, "okOp")},
        "/no": {"post": {
            "operationId": "noOp",
            "x-ctier-exclude": True,
            "x-ctier-status": "declared",
            "responses": {"200": {"description": "ok"}},
        }},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="kong")
    assert "authorization.yaml" in files
    assert "keycloak-realm.json" in files
    import yaml
    doc = yaml.safe_load(files["authorization.yaml"])
    granted = set(doc["clients"][0]["scopes"])
    assert scope_name("okOp") in granted
    assert scope_name("noOp") not in granted
    assert "noOp" in {s["operation"] for s in doc["scopes"] if s["excluded"]}
    deck = yaml.safe_load(files["kong.yaml"])
    by_name = {r["name"]: r for r in deck["services"][0]["routes"]}
    ok = next(p for p in by_name["okOp"]["plugins"] if p["name"] == "ctier")
    no = next(p for p in by_name["noOp"]["plugins"] if p["name"] == "ctier")
    assert ok["config"]["required_scope"] == scope_name("okOp")
    assert "required_scope" not in no["config"]
    assert no["config"]["excluded"] is True
    jwt = [p for p in by_name["okOp"]["plugins"] if p["name"] == "jwt"]
    assert jwt


def test_reject_revokes_the_operation_scope_and_expiry_does_not():
    store = Store()
    directory = NullDirectory()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-rej-scope")
    decide(store, "corr-rej-scope", "reject", "analyst-1", now=NOW, directory=directory)
    assert directory.revoked == [("agent-a", "updateCommunicationPreferences")]

    store2 = Store()
    silent = NullDirectory()
    persist(
        store2,
        _payload(),
        now=NOW,
        new_id=lambda: "corr-exp-scope",
        review_period_seconds=1,
    )
    from datetime import timedelta
    from ctier.custody.service import review_queue
    later = NOW + timedelta(seconds=5)
    review_queue(store2, now=later)
    assert silent.revoked == []
    assert store2.get("corr-exp-scope")["status"] == "expired"


def test_reference_authorization_omits_closeAccount():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    files = generate(qualified, target="kong")
    import yaml
    doc = yaml.safe_load(files["authorization.yaml"])
    granted = set(doc["clients"][0]["scopes"])
    assert scope_name("getBalance") in granted
    assert scope_name("initiatePayment") in granted
    assert scope_name("closeAccount") not in granted
    assert doc["clients"][0]["id"] == AGENT_CLIENT
    assert doc["clients"][1]["id"] == AGENT_SUB_CLIENT
    assert doc["clients"][1]["parent"] == AGENT_CLIENT
    assert doc["clients"][1]["scopes"] == [scope_name("getBalance")]
    import json
    realm = json.loads(files["keycloak-realm.json"])
    client = realm["clients"][0]
    assert client["serviceAccountsEnabled"] is True
    assert realm["accessTokenLifespan"] == ACCESS_TOKEN_LIFESPAN
    assert client["defaultClientScopes"] == [
        IDENTITY_SCOPE, f"audience-{AGENT_SUB_CLIENT}",
    ]
    for name in granted:
        assert name in client["optionalClientScopes"]
        assert name not in client["defaultClientScopes"]
    assert scope_name("closeAccount") not in client["optionalClientScopes"]
    sub = realm["clients"][1]
    assert sub["clientId"] == AGENT_SUB_CLIENT
    assert sub["optionalClientScopes"] == [scope_name("getBalance")]
    assert sub["defaultClientScopes"] == [IDENTITY_SCOPE]
    assert client["attributes"][EXCHANGE_ATTRIBUTE] == "true"
    assert sub["attributes"][EXCHANGE_ATTRIBUTE] == "true"
    assert any(s["name"] == f"audience-{AGENT_SUB_CLIENT}" for s in realm["clientScopes"])


def test_operation_scopes_are_optional_never_default():
    """E1: a default operation scope cannot be reduced. generate() must not emit one."""
    raw = _spec({
        "/ok": {"get": _declared(1, "okOp")},
        "/no": {"post": {
            "operationId": "noOp",
            "x-ctier-exclude": True,
            "x-ctier-status": "declared",
            "responses": {"200": {"description": "ok"}},
        }},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="kong")
    import json
    realm = json.loads(files["keycloak-realm.json"])
    client = realm["clients"][0]
    assert client["defaultClientScopes"] == [IDENTITY_SCOPE]
    assert scope_name("okOp") in client["optionalClientScopes"]
    assert scope_name("okOp") not in client["defaultClientScopes"]
    assert scope_name("noOp") not in client["optionalClientScopes"]
    assert scope_name("noOp") not in client["defaultClientScopes"]


def test_shared_sub_agent_is_rejected_with_both_parents():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    with pytest.raises(GenerateError) as exc:
        generate(
            qualified,
            target="kong",
            agents=[
                {"id": "agent-a1"},
                {"id": "agent-a2"},
                {
                    "id": "agent-shared",
                    "parent": "agent-a1",
                    "operations": ["getBalance"],
                },
                {
                    "id": "agent-shared",
                    "parent": "agent-a2",
                    "operations": ["getBalance"],
                },
            ],
        )
    assert exc.value.rule == "shared-sub-agent"
    message = str(exc.value)
    assert "agent-shared" in message
    assert "agent-a1" in message
    assert "agent-a2" in message
    assert "distinct identities" in message


def test_depth_two_tree_generates():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    files = generate(qualified, target="kong")
    import yaml
    doc = yaml.safe_load(files["authorization.yaml"])
    assert [c["id"] for c in doc["clients"]] == [AGENT_CLIENT, AGENT_SUB_CLIENT]
    assert doc["clients"][1]["parent"] == AGENT_CLIENT


def test_distinct_identities_with_the_same_scope_set_generate():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    files = generate(
        qualified,
        target="kong",
        agents=[
            {"id": AGENT_CLIENT},
            {
                "id": "agent-sub-balance",
                "parent": AGENT_CLIENT,
                "operations": ["getBalance"],
            },
            {
                "id": "agent-sub-ledger",
                "parent": AGENT_CLIENT,
                "operations": ["getBalance"],
            },
        ],
    )
    import yaml
    doc = yaml.safe_load(files["authorization.yaml"])
    ids = [c["id"] for c in doc["clients"]]
    assert ids == [AGENT_CLIENT, "agent-sub-balance", "agent-sub-ledger"]
    assert doc["clients"][1]["scopes"] == doc["clients"][2]["scopes"]

