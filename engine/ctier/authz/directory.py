# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Revoke and restore operation scopes on an authorisation-server client.

NullDirectory is the offline default. KeycloakDirectory talks to the Admin
API and is constructed only when the live rig sets CTIER_KEYCLOAK_URL.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional
from urllib.request import Request


class NullDirectory:
    """No authorisation server. Revocation is a no-op. Offline tests use this."""

    def __init__(self) -> None:
        self.revoked: list[tuple[str, str]] = []

    def revoke(self, client_id: str, operation: str) -> None:
        self.revoked.append((client_id, operation))

    def restore(self, client_id: str, operations: list[str]) -> None:
        return


class KeycloakDirectory:
    def __init__(
        self,
        base_url: str,
        realm: str,
        *,
        admin_user: str,
        admin_password: str,
        token_realm: str = "master",
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.token_realm = token_realm
        self.timeout = timeout

    def revoke(self, client_id: str, operation: str) -> None:
        from . import scope_name

        wanted = scope_name(operation)
        token = self._admin_token()
        client_uuid = self._client_uuid(token, client_id)
        if client_uuid is None:
            return
        assigned = {
            **self._default_scope_ids(token, client_uuid),
            **self._optional_scope_ids(token, client_uuid),
        }
        for scope_id, name in list(assigned.items()):
            if name == wanted:
                self._delete_scope_assignment(token, client_uuid, scope_id)
        # Keep identity so new tokens still match the Kong JWT credential.

    def restore(self, client_id: str, operations: list[str]) -> None:
        from . import IDENTITY_SCOPE, scope_name

        names = [scope_name(op) for op in operations]
        self.grant_named(client_id, names)

    def grant_named(self, client_id: str, scope_names: list[str]) -> None:
        from . import IDENTITY_SCOPE

        token = self._admin_token()
        client_uuid = self._client_uuid(token, client_id)
        if client_uuid is None:
            return
        catalog = self._scope_names(token)
        have_default = set(self._default_scope_ids(token, client_uuid).values())
        have_optional = set(self._optional_scope_ids(token, client_uuid).values())
        if IDENTITY_SCOPE not in have_default:
            scope_id = catalog.get(IDENTITY_SCOPE)
            if scope_id:
                self._add_default_scope(token, client_uuid, scope_id)
        for name in scope_names:
            if name == IDENTITY_SCOPE or name in have_optional or name in have_default:
                continue
            scope_id = catalog.get(name)
            if scope_id:
                self._add_optional_scope(token, client_uuid, scope_id)

    def assigned_optional_scopes(self, client_id: str) -> list[str]:
        """Operation scopes currently optional on the client. Used by the rig."""
        token = self._admin_token()
        client_uuid = self._client_uuid(token, client_id)
        if client_uuid is None:
            return []
        return list(self._optional_scope_ids(token, client_uuid).values())

    def make_operation_scopes_optional(self, client_id: str) -> None:
        """Default scopes are always minted. Exchange cannot drop them.

        Move `operation-*` to optional so a `scope=` parameter can select a
        subset. Identity stays default so `cid` still lands on every token.
        """
        from . import IDENTITY_SCOPE, SCOPE_PREFIX

        token = self._admin_token()
        client_uuid = self._client_uuid(token, client_id)
        if client_uuid is None:
            raise RuntimeError(f"unknown client {client_id!r}")
        current = self._default_scope_ids(token, client_uuid)
        for scope_id, name in list(current.items()):
            if name == IDENTITY_SCOPE or not name.startswith(SCOPE_PREFIX):
                continue
            self._delete_default_scope(token, client_uuid, scope_id)
            self._json(
                token,
                "PUT",
                f"/admin/realms/{self.realm}/clients/{client_uuid}"
                f"/optional-client-scopes/{scope_id}",
            )

    def enable_standard_exchange(self, client_id: str) -> None:
        """Turn on RFC 8693 exchange for a confidential client (importable attribute)."""
        token = self._admin_token()
        client_uuid = self._client_uuid(token, client_id)
        if client_uuid is None:
            raise RuntimeError(f"unknown client {client_id!r}")
        client = self._json(
            token, "GET", f"/admin/realms/{self.realm}/clients/{client_uuid}",
        )
        attrs = dict(client.get("attributes") or {})
        attrs["standard.token.exchange.enabled"] = "true"
        client["attributes"] = attrs
        self._json(
            token, "PUT", f"/admin/realms/{self.realm}/clients/{client_uuid}", client,
        )

    def set_downscope_enforcer(self, *, enabled: bool) -> None:
        """Install or remove the importable client-policy executor.

        Without this executor Keycloak documents that exchange may *add*
        scopes the subject token does not carry.
        """
        token = self._admin_token()
        profile = {
            "name": "ctier-downscope",
            "description": "token exchange may only reduce scopes",
            "executors": [
                {
                    "executor": "downscope-assertion-grant-enforcer",
                    "configuration": {},
                }
            ],
        }
        policy = {
            "name": "ctier-exchange-downscope",
            "enabled": enabled,
            "conditions": [
                {
                    "condition": "client-access-type",
                    "configuration": {"type": ["confidential"]},
                }
            ],
            "profiles": ["ctier-downscope"],
        }
        current_profiles = self._json(
            token,
            "GET",
            f"/admin/realms/{self.realm}/client-policies/profiles?include-global-profiles=false",
        ) or {"profiles": []}
        others = [
            p for p in (current_profiles.get("profiles") or [])
            if p.get("name") != "ctier-downscope"
        ]
        self._json(
            token,
            "PUT",
            f"/admin/realms/{self.realm}/client-policies/profiles",
            {"profiles": [*others, profile]},
        )
        current_policies = self._json(
            token,
            "GET",
            f"/admin/realms/{self.realm}/client-policies/policies",
        ) or {"policies": []}
        others_p = [
            p for p in (current_policies.get("policies") or [])
            if p.get("name") != "ctier-exchange-downscope"
        ]
        self._json(
            token,
            "PUT",
            f"/admin/realms/{self.realm}/client-policies/policies",
            {"policies": [*others_p, policy] if enabled else others_p},
        )

    def ensure_granted(self, document: dict) -> None:
        """Create any missing scopes and grant the document's client sets.

        Used when a live test compiles a spec other than the imported realm.
        """
        token = self._admin_token()
        catalog = self._scope_names(token)
        for item in document.get("scopes") or []:
            name = str(item["name"])
            if name not in catalog:
                self._create_scope(token, name)
        for client in document.get("clients") or []:
            self.grant_named(str(client["id"]), list(client.get("scopes") or []))

    def _create_scope(self, token: str, name: str) -> None:
        self._json(
            token,
            "POST",
            f"/admin/realms/{self.realm}/client-scopes",
            {
                "name": name,
                "protocol": "openid-connect",
                "attributes": {
                    "include.in.token.scope": "true",
                    "display.on.consent.screen": "false",
                },
            },
        )

    def _admin_token(self) -> str:
        url = (
            f"{self.base_url}/realms/{self.token_realm}"
            "/protocol/openid-connect/token"
        )
        body = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_user,
            "password": self.admin_password,
        }).encode("utf-8")
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return str(payload["access_token"])

    def _json(self, token: str, method: str, path: str, body: Any = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            if exc.code == 404:
                return None
            if exc.code >= 400:
                raise RuntimeError(f"{method} {path} -> {exc.code} {raw!r}") from exc
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))

    def _client_uuid(self, token: str, client_id: str) -> Optional[str]:
        rows = self._json(
            token,
            "GET",
            f"/admin/realms/{self.realm}/clients?clientId={urllib.parse.quote(client_id)}",
        )
        if not rows:
            return None
        return str(rows[0]["id"])

    def _scope_names(self, token: str) -> dict[str, str]:
        rows = self._json(token, "GET", f"/admin/realms/{self.realm}/client-scopes") or []
        return {str(r["name"]): str(r["id"]) for r in rows}

    def _default_scope_ids(self, token: str, client_uuid: str) -> dict[str, str]:
        rows = self._json(
            token,
            "GET",
            f"/admin/realms/{self.realm}/clients/{client_uuid}/default-client-scopes",
        ) or []
        return {str(r["id"]): str(r["name"]) for r in rows}

    def _optional_scope_ids(self, token: str, client_uuid: str) -> dict[str, str]:
        rows = self._json(
            token,
            "GET",
            f"/admin/realms/{self.realm}/clients/{client_uuid}/optional-client-scopes",
        ) or []
        return {str(r["id"]): str(r["name"]) for r in rows}

    def _delete_scope_assignment(self, token: str, client_uuid: str, scope_id: str) -> None:
        self._json(
            token,
            "DELETE",
            f"/admin/realms/{self.realm}/clients/{client_uuid}/default-client-scopes/{scope_id}",
        )
        self._json(
            token,
            "DELETE",
            f"/admin/realms/{self.realm}/clients/{client_uuid}/optional-client-scopes/{scope_id}",
        )

    def _delete_default_scope(self, token: str, client_uuid: str, scope_id: str) -> None:
        self._delete_scope_assignment(token, client_uuid, scope_id)

    def _add_default_scope(self, token: str, client_uuid: str, scope_id: str) -> None:
        self._json(
            token,
            "PUT",
            f"/admin/realms/{self.realm}/clients/{client_uuid}/default-client-scopes/{scope_id}",
        )

    def _add_optional_scope(self, token: str, client_uuid: str, scope_id: str) -> None:
        self._json(
            token,
            "PUT",
            f"/admin/realms/{self.realm}/clients/{client_uuid}/optional-client-scopes/{scope_id}",
        )


def directory_from_env():
    url = os.environ.get("CTIER_KEYCLOAK_URL") or ""
    if not url:
        return NullDirectory()
    return KeycloakDirectory(
        url,
        os.environ.get("CTIER_KEYCLOAK_REALM") or "ctier",
        admin_user=os.environ.get("CTIER_KEYCLOAK_ADMIN_USER") or "local-dev-admin",
        admin_password=os.environ.get("CTIER_KEYCLOAK_ADMIN_PASSWORD") or "local-dev-admin-password",
    )
