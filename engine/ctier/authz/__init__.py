# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Authorisation-server configuration: scopes, exclusion, agent clients.

Exclusion is a scope never granted. Suspension is the same act at runtime:
remove that scope from the client. Operation scopes are optional on the
client — default scopes are re-attached on every grant, so a default
operation scope cannot be reduced. The generator emits both the portable
document and a Keycloak realm that imports it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

from ctier.errors import GenerateError

DIR = Path(__file__).resolve().parent
REALM = "ctier"
SCOPE_PREFIX = "operation-"
ACCESS_TOKEN_LIFESPAN = 30
JWT_CLAIM = "cid"
JWT_CLAIM_VALUE = "ctier"
AGENT_CLIENT = "agent-a"
AGENT_SECRET = "local-dev-agent-secret"
AGENT_SUB_CLIENT = "agent-sub-balance"
IDENTITY_SCOPE = "ctier-identity"
EXCHANGE_ATTRIBUTE = "standard.token.exchange.enabled"


def scope_name(operation_id: str) -> str:
    return SCOPE_PREFIX + operation_id


def public_pem() -> str:
    return (DIR / "public.pem").read_text(encoding="utf-8")


def _rsa_material() -> dict[str, str]:
    return json.loads((DIR / "keycloak-rsa.json").read_text(encoding="utf-8"))


def _default_agents(granted: list[str]) -> list[dict[str, Any]]:
    decls: list[dict[str, Any]] = [{"id": AGENT_CLIENT, "scopes": list(granted)}]
    balance = scope_name("getBalance")
    if balance in granted:
        decls.append({
            "id": AGENT_SUB_CLIENT,
            "parent": AGENT_CLIENT,
            "scopes": [balance],
        })
    return decls


def _normalise_agents(
    agents: Sequence[Any] | None, granted: list[str],
) -> list[dict[str, Any]]:
    if agents is None:
        return _default_agents(granted)
    decls: list[dict[str, Any]] = []
    strings_only = True
    for item in agents:
        if isinstance(item, str):
            decls.append({"id": item, "scopes": list(granted)})
            continue
        strings_only = False
        entry = {"id": str(item["id"])}
        if item.get("parent"):
            entry["parent"] = str(item["parent"])
        if "scopes" in item:
            entry["scopes"] = list(item["scopes"])
        elif "operations" in item:
            entry["scopes"] = [scope_name(op) for op in item["operations"]]
        else:
            entry["scopes"] = list(granted)
        decls.append(entry)
    if strings_only:
        balance = scope_name("getBalance")
        if balance in granted and all(d["id"] != AGENT_SUB_CLIENT for d in decls):
            decls.append({
                "id": AGENT_SUB_CLIENT,
                "parent": decls[0]["id"] if decls else AGENT_CLIENT,
                "scopes": [balance],
            })
    return decls


def _reject_shared_sub_agents(decls: list[dict[str, Any]]) -> None:
    parents: dict[str, list[str]] = {}
    for item in decls:
        parent = item.get("parent")
        if not parent:
            continue
        parents.setdefault(item["id"], []).append(parent)
    for child, named in parents.items():
        unique = list(dict.fromkeys(named))
        if len(unique) < 2:
            continue
        a, b = unique[0], unique[1]
        raise GenerateError(
            "shared-sub-agent",
            f"agent identity {child!r} is declared under both {a!r} and {b!r}. "
            f"{child!r} acting for {a!r} and {child!r} acting for {b!r} are not "
            "the same authority; they may warrant different scope sets. "
            "Compile them as distinct identities.",
        )


def authorization_document(
    rows: Iterable[dict[str, Any]],
    *,
    agents: Sequence[Any] | None = None,
) -> dict[str, Any]:
    classified = [r for r in rows if r.get("classified")]
    scopes = []
    granted: list[str] = []
    excluded: list[str] = []
    for row in classified:
        oid = str(row["operationId"])
        name = scope_name(oid)
        item = {
            "name": name,
            "operation": oid,
            "excluded": bool(row.get("excluded")),
        }
        scopes.append(item)
        if row.get("excluded"):
            excluded.append(name)
        else:
            granted.append(name)
    decls = _normalise_agents(agents, granted)
    _reject_shared_sub_agents(decls)
    clients = []
    for decl in decls:
        client: dict[str, Any] = {"id": decl["id"]}
        if decl.get("parent"):
            client["parent"] = decl["parent"]
        client["scopes"] = list(decl["scopes"])
        clients.append(client)
    return {
        "realm": REALM,
        "accessTokenLifespan": ACCESS_TOKEN_LIFESPAN,
        "jwt": {
            "claim": JWT_CLAIM,
            "claimValue": JWT_CLAIM_VALUE,
        },
        "scopes": scopes,
        "excluded": excluded,
        "clients": clients,
    }


def _client_scope(name: str, *, identity: bool = False) -> dict[str, Any]:
    mappers = []
    if identity:
        mappers.append({
            "name": JWT_CLAIM,
            "protocol": "openid-connect",
            "protocolMapper": "oidc-hardcoded-claim-mapper",
            "consentRequired": False,
            "config": {
                "claim.name": JWT_CLAIM,
                "claim.value": JWT_CLAIM_VALUE,
                "jsonType.label": "String",
                "id.token.claim": "false",
                "access.token.claim": "true",
                "userinfo.token.claim": "false",
            },
        })
    return {
        "name": name,
        "protocol": "openid-connect",
        "attributes": {
            "include.in.token.scope": "false" if identity else "true",
            "display.on.consent.screen": "false",
        },
        "protocolMappers": mappers,
    }


def _audience_scope(audience_client_id: str) -> dict[str, Any]:
    """Mapper so a parent's token lists the sub-client in `aud`.

    Standard token exchange requires that, unless the requester is
    exchanging its own token.
    """
    return {
        "name": f"audience-{audience_client_id}",
        "protocol": "openid-connect",
        "attributes": {
            "include.in.token.scope": "false",
            "display.on.consent.screen": "false",
        },
        "protocolMappers": [{
            "name": f"aud-{audience_client_id}",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-audience-mapper",
            "consentRequired": False,
            "config": {
                "included.client.audience": audience_client_id,
                "id.token.claim": "false",
                "access.token.claim": "true",
            },
        }],
    }


def _confidential_client(
    client_id: str,
    secret: str,
    optional_scopes: list[str],
    *,
    default_scopes: list[str] | None = None,
    service_account: bool = False,
    attributes: dict[str, str] | None = None,
) -> dict[str, Any]:
    # Operation scopes are optional. Default scopes are re-attached on every
    # grant, including token exchange, so a default operation scope cannot
    # be reduced by a `scope=` parameter or by a narrower client.
    body: dict[str, Any] = {
        "clientId": client_id,
        "name": client_id,
        "enabled": True,
        "secret": secret,
        "clientAuthenticatorType": "client-secret",
        "publicClient": False,
        "protocol": "openid-connect",
        "standardFlowEnabled": False,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": service_account,
        "fullScopeAllowed": False,
        "defaultClientScopes": list(default_scopes if default_scopes is not None else [IDENTITY_SCOPE]),
        "optionalClientScopes": list(optional_scopes),
    }
    if attributes:
        body["attributes"] = attributes
    return body


def keycloak_realm(document: dict[str, Any]) -> dict[str, Any]:
    rsa = _rsa_material()
    children_of: dict[str, list[str]] = {}
    for c in document["clients"]:
        parent = c.get("parent")
        if parent:
            children_of.setdefault(str(parent), []).append(str(c["id"]))
    client_scopes = [_client_scope(IDENTITY_SCOPE, identity=True)]
    for item in document["scopes"]:
        client_scopes.append(_client_scope(item["name"]))
    seen_audience = set()
    for child_ids in children_of.values():
        for child_id in child_ids:
            if child_id in seen_audience:
                continue
            seen_audience.add(child_id)
            client_scopes.append(_audience_scope(child_id))
    clients = []
    for c in document["clients"]:
        defaults = [IDENTITY_SCOPE]
        for child_id in children_of.get(c["id"], []):
            defaults.append(f"audience-{child_id}")
        clients.append(
            _confidential_client(
                c["id"],
                AGENT_SECRET,
                list(c["scopes"]),
                default_scopes=defaults,
                service_account=True,
                attributes={EXCHANGE_ATTRIBUTE: "true"},
            )
        )
    return {
        "id": REALM,
        "realm": REALM,
        "enabled": True,
        "sslRequired": "none",
        "accessTokenLifespan": int(document["accessTokenLifespan"]),
        "accessTokenLifespanForImplicitFlow": int(document["accessTokenLifespan"]),
        "ssoSessionIdleTimeout": 300,
        "ssoSessionMaxLifespan": 300,
        "clients": clients,
        "clientScopes": client_scopes,
        "defaultDefaultClientScopes": [IDENTITY_SCOPE],
        "defaultOptionalClientScopes": [],
        "components": {
            "org.keycloak.keys.KeyProvider": [
                {
                    "name": "rsa",
                    "providerId": "rsa",
                    "config": {
                        "priority": ["100"],
                        "enabled": ["true"],
                        "active": ["true"],
                        "algorithm": ["RS256"],
                        "kid": ["ctier-realm"],
                        "privateKey": [rsa["privateKey"]],
                        "certificate": [rsa["certificate"]],
                    },
                }
            ]
        },
    }


def dump_authorization(document: dict[str, Any]) -> str:
    return yaml.safe_dump(
        document,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )


def authorization_files(
    rows: Iterable[dict[str, Any]],
    *,
    agents: Sequence[Any] | None = None,
) -> dict[str, str]:
    document = authorization_document(rows, agents=agents)
    realm = keycloak_realm(document)
    return {
        "authorization.yaml": dump_authorization(document),
        "keycloak-realm.json": json.dumps(realm, indent=2) + "\n",
    }


def kong_consumers() -> list[dict[str, Any]]:
    return [{
        "username": "ctier-agents",
        "jwt_secrets": [{
            "algorithm": "RS256",
            "key": JWT_CLAIM_VALUE,
            "secret": "unused-rs256",
            "rsa_public_key": public_pem(),
        }],
    }]


def jwt_plugin() -> dict[str, Any]:
    return {
        "name": "jwt",
        "config": {
            "key_claim_name": JWT_CLAIM,
            "claims_to_verify": ["exp"],
            "header_names": ["authorization"],
        },
    }
