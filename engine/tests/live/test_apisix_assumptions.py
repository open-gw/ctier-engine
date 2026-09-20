"""APISIX assumptions, each with a specific falsification.

Handwritten declarative files only. generate() is not used: Part 0 runs
before a target exists. A configuration only the Admin API can set is a
failed experiment.
"""
from __future__ import annotations

import time

import pytest
import yaml

from ctier.authz import public_pem
from tests.live.apisix_rig import HS256_SECRET, MINIMAL, hs256_token, rs256_token, with_end

pytestmark = pytest.mark.live


A2_STRIP = """\
routes:
  - id: strip-then-set
    name: strip-then-set
    uris:
      - /echo
    methods:
      - GET
    plugins:
      proxy-rewrite:
        headers:
          remove:
            - x-ctier-criteria
          set:
            X-Ctier-Tier: "2"
            X-Ctier-Operation: "handwritten"
    upstream:
      type: roundrobin
      nodes:
        "echo:8080": 1

#END
"""

A2_SAME_NAME = """\
routes:
  - id: same-name
    name: same-name
    uris:
      - /same
    methods:
      - GET
    plugins:
      proxy-rewrite:
        headers:
          remove:
            - x-ctier-tier
          set:
            X-Ctier-Tier: "2"
    upstream:
      type: roundrobin
      nodes:
        "echo:8080": 1

#END
"""

A2_ORDER_REWRITE_LAST = """\
routes:
  - id: order
    name: order
    uris:
      - /order
    methods:
      - GET
    plugins:
      serverless-pre-function:
        _meta:
          priority: 2000
        phase: rewrite
        functions:
          - |
            return function(conf, ctx)
              ngx.req.set_header("X-Order", "serverless")
            end
      proxy-rewrite:
        _meta:
          priority: 1000
        headers:
          set:
            X-Order: "rewrite"
    upstream:
      type: roundrobin
      nodes:
        "echo:8080": 1

#END
"""

A2_ORDER_REWRITE_FIRST = """\
routes:
  - id: order
    name: order
    uris:
      - /order
    methods:
      - GET
    plugins:
      serverless-pre-function:
        _meta:
          priority: 1000
        phase: rewrite
        functions:
          - |
            return function(conf, ctx)
              ngx.req.set_header("X-Order", "serverless")
            end
      proxy-rewrite:
        _meta:
          priority: 2000
        headers:
          set:
            X-Order: "rewrite"
    upstream:
      type: roundrobin
      nodes:
        "echo:8080": 1

#END
"""

A3_JWT = f"""\
consumers:
  - username: a3-agent
    plugins:
      jwt-auth:
        key: a3-agent
        algorithm: HS256
        secret: {HS256_SECRET}

routes:
  - id: scoped
    name: scoped
    uris:
      - /scoped
    methods:
      - GET
    plugins:
      jwt-auth:
        key_claim_name: key
    upstream:
      type: roundrobin
      nodes:
        "echo:8080": 1

#END
"""

A4_STORE = """\
routes:
  - id: floor-store
    name: floor-store
    uris:
      - /floor
    methods:
      - GET
    plugins:
      serverless-pre-function:
        phase: rewrite
        functions:
          - |
            return function(conf, ctx)
              local dict = ngx.shared.ctier_floors
              if not dict then
                ngx.req.set_header("X-Floor-Store", "absent")
                return
              end
              dict:set("probe", "held")
              ngx.req.set_header("X-Floor-Store", dict:get("probe") or "empty")
            end
    upstream:
      type: roundrobin
      nodes:
        "echo:8080": 1

#END
"""


def test_a1_apisix_runs_declaratively_on_arm64(apisix_stack):
    """A1: standalone YAML proxies to echo. No Admin API."""
    apisix_stack.load(MINIMAL)
    status, payload = apisix_stack.echo_json("GET", "/a1/ping")
    assert status == 200, payload
    assert payload.get("method") == "GET"
    assert payload.get("path") == "/a1/ping"
    # Control plane is off. A 19000 hit that reached echo is the data plane.
    assert "headers" in payload


def test_a2_proxy_rewrite_strips_and_sets_declaratively(apisix_stack):
    """A2 part 1: set overwrites inbound; remove drops a name we do not emit.

    Same-plugin remove+set of one name is a different observation — see
    test_a2_same_name_remove_drops_the_set_value.
    """
    apisix_stack.load(A2_STRIP)
    status, payload = apisix_stack.echo_json(
        "GET",
        "/echo",
        headers={"x-ctier-tier": "1", "x-ctier-criteria": "forged"},
    )
    assert status == 200, payload
    headers = payload["headers"]
    assert headers.get("x-ctier-tier") == "2", headers
    assert headers.get("x-ctier-operation") == "handwritten", headers
    assert "x-ctier-criteria" not in headers, headers


def test_a2_same_name_remove_drops_the_set_value(apisix_stack):
    """proxy-rewrite remove of x-ctier-tier also drops a set of that name."""
    apisix_stack.load(A2_SAME_NAME)
    status, payload = apisix_stack.echo_json(
        "GET", "/same", headers={"x-ctier-tier": "1"},
    )
    assert status == 200, payload
    assert payload["headers"].get("x-ctier-tier") is None, payload["headers"]


def test_a2_plugin_priority_is_controllable(apisix_stack):
    """A2 part 2: _meta.priority changes which write the echo sees."""
    apisix_stack.load(A2_ORDER_REWRITE_LAST)
    status, payload = apisix_stack.echo_json("GET", "/order")
    assert status == 200, payload
    later = payload["headers"].get("x-order")
    apisix_stack.load(A2_ORDER_REWRITE_FIRST)
    status, payload = apisix_stack.echo_json("GET", "/order")
    assert status == 200, payload
    earlier = payload["headers"].get("x-order")
    assert later == "rewrite", later
    assert earlier == "serverless", earlier
    assert later != earlier


def test_a3_jwt_auth_does_not_check_scope(apisix_stack):
    """A3: jwt-auth accepts a signed token with or without the operation scope.

    Falsified (the interesting direction) if the missing-scope token is
    refused without custom code. Then APISIX would do declaratively what
    Kong OSS needed Lua for.
    """
    apisix_stack.load(A3_JWT)
    exp = int(time.time()) + 60
    with_scope = hs256_token({
        "key": "a3-agent",
        "exp": exp,
        "scope": "operation-getBalance",
    })
    without_scope = hs256_token({
        "key": "a3-agent",
        "exp": exp,
        "scope": "openid",
    })
    held, payload = apisix_stack.echo_json(
        "GET", "/scoped", headers={"Authorization": f"Bearer {with_scope}"},
    )
    assert held == 200, payload
    missing, raw, _ = apisix_stack.request(
        "GET", "/scoped", headers={"Authorization": f"Bearer {without_scope}"},
    )
    # Stock jwt-auth has no required_scope. A 200 here falsifies A3.
    assert missing == 200, raw
    unsigned, _raw, _ = apisix_stack.request("GET", "/scoped")
    assert unsigned in {401, 403}


def test_a4_shared_dict_exists_without_admin_api(apisix_stack):
    """A4: lua_shared_dict from config.yaml is readable on the request path.

    The probe is serverless Lua. That is the experiment, not a product
    plugin: no stock plugin reads this dict for a floor.
    """
    apisix_stack.load(A4_STORE)
    status, payload = apisix_stack.echo_json("GET", "/floor")
    assert status == 200, payload
    observed = payload["headers"].get("x-floor-store")
    assert observed == "held", (
        "A4 failed: shared dict absent or unreadable without Admin API. "
        f"x-floor-store={observed!r}. Level 4 is not available on this target."
    )


# --- A5 -----------------------------------------------------------------
#
# Candidates on apache/apisix:3.13.0-debian, this rig's plugin list:
# - jwt-auth: A3. Signature and exp. No required_scopes in the schema.
# - authz-keycloak: declarative permissions, but evaluate_permissions POSTs
#   grant_type=urn:ietf:params:oauth:grant-type:uma-ticket to token_endpoint
#   on the request path (lua: request_uri). That is the ADR-003 hop.
# - openid-connect: required_scopes on the verified token. Local if
#   public_key (or a cached JWKS) verifies; introspection_endpoint is the
#   other branch and is a per-request issuer call. Discovery is required
#   in the schema; get_discovery_doc is skipped when valid_issuers is set.
# - use_jwks without public_key: fetches JWKS (network).
# - opa / forward-auth / ldap-auth / wolf-rbac: another server on the
#   request path. Not scope-on-this-bearer.
# - authz-casbin: a local policy file, not the compiled operation scope
#   on the JWT. A different model.
#
# Picked openid-connect + public_key + required_scopes + valid_issuers:
# the only stock plugin that both names a required scope and has a local
# verification branch. authz-keycloak is recorded on the wire as the
# likely casualty of the no-issuer-call rule.

A5_SCOPE = "operation-getBalance"
A5_ISSUER = "ctier-a5"
A5_DISCOVERY = "http://echo:8080/.well-known/openid-configuration"
A5_UMA = "http://echo:8080/uma-ticket"


def _a5_oidc() -> str:
    doc = {
        "routes": [
            {
                "id": "scoped",
                "name": "scoped",
                "uris": ["/scoped"],
                "methods": ["GET"],
                "plugins": {
                    "openid-connect": {
                        "client_id": "a5",
                        "client_secret": "unused-a5-secret",
                        "discovery": A5_DISCOVERY,
                        "bearer_only": True,
                        "ssl_verify": False,
                        "public_key": public_pem().strip(),
                        "required_scopes": [A5_SCOPE],
                        "claim_validator": {
                            "issuer": {"valid_issuers": [A5_ISSUER]},
                        },
                        "set_userinfo_header": False,
                        "set_id_token_header": False,
                    }
                },
                "upstream": {
                    "type": "roundrobin",
                    "nodes": {"echo:8080": 1},
                },
            }
        ]
    }
    return with_end(yaml.safe_dump(doc, sort_keys=False))


def _a5_keycloak() -> str:
    doc = {
        "routes": [
            {
                "id": "uma",
                "name": "uma",
                "uris": ["/uma"],
                "methods": ["GET"],
                "plugins": {
                    "authz-keycloak": {
                        "client_id": "a5",
                        "token_endpoint": A5_UMA,
                        "permissions": [f"balance#{A5_SCOPE}"],
                        "ssl_verify": False,
                        "timeout": 1000,
                    }
                },
                "upstream": {
                    "type": "roundrobin",
                    "nodes": {"echo:8080": 1},
                },
            }
        ]
    }
    return with_end(yaml.safe_dump(doc, sort_keys=False))


def _a5_token(scope: str) -> str:
    return rs256_token({
        "iss": A5_ISSUER,
        "exp": int(time.time()) + 60,
        "scope": scope,
    })


def _issuer_hops(log: list[dict]) -> list[dict]:
    return [
        row for row in log
        if str(row.get("path") or "").startswith("/.well-known/")
        or str(row.get("path") or "").startswith("/uma-ticket")
    ]


def test_a5_authz_keycloak_posts_uma_ticket_on_the_request_path(apisix_stack):
    """authz-keycloak is declarative config over a per-request issuer call.

    Not the A5 candidate. Recorded so the pick is from the wire, not the
    plugin name. Falsified-for-A5 if this request is refused *without* a
    POST to token_endpoint — then we would have been wrong about the lua.
    """
    apisix_stack.load(_a5_keycloak())
    before = len(_issuer_hops(apisix_stack.echo_log()))
    token = _a5_token(A5_SCOPE)
    status, raw, _ = apisix_stack.request(
        "GET", "/uma", headers={"Authorization": f"Bearer {token}"},
    )
    hops = _issuer_hops(apisix_stack.echo_log())
    added = hops[before:]
    assert added, (
        f"authz-keycloak did not call token_endpoint; status={status} "
        f"body={raw[:200]!r} hops={hops!r}"
    )
    assert any(row.get("method") == "POST" for row in added), added


def test_a5_openid_connect_enforces_scope_without_an_issuer_call(apisix_stack):
    """A5: stock openid-connect refuses a signed token missing the scope.

    Holds if: with-scope is 200, without-scope is 401/403, unsigned is
    401/403, and echo saw no discovery/token/uma hop for those requests.
    Falsified if the missing-scope token is 200, if a hop to the discovery
    or token URL happened on the request path, or if the plugin cannot be
    expressed in standalone YAML.
    """
    apisix_stack.load(_a5_oidc())
    before = apisix_stack.echo_log()
    with_scope = _a5_token(A5_SCOPE)
    without_scope = _a5_token("openid")
    held, payload = apisix_stack.echo_json(
        "GET", "/scoped", headers={"Authorization": f"Bearer {with_scope}"},
    )
    missing, raw, _ = apisix_stack.request(
        "GET", "/scoped", headers={"Authorization": f"Bearer {without_scope}"},
    )
    unsigned, _, _ = apisix_stack.request("GET", "/scoped")
    after = apisix_stack.echo_log()
    hops = _issuer_hops(after[len(before):])
    print(
        f"\nA5 openid-connect: with={held} without={missing} unsigned={unsigned} "
        f"issuer_hops={len(hops)}"
    )
    assert not hops, (
        "A5 falsified: authorisation-server call on the request path. "
        f"hops={hops!r}"
    )
    assert held == 200, payload
    assert missing in {401, 403}, raw
    assert unsigned in {401, 403}
