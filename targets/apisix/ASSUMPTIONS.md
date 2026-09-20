# APISIX assumptions — under experiment in 17

Named tests in `engine/tests/live/test_apisix_assumptions.py`. Offline,
arm64, `apache/apisix:3.13.0-debian`, standalone YAML (`config_provider:
yaml`). No Admin API. A configuration only the Admin API can set, which
the declarative file cannot express, is a failed experiment.

See also [`engine/docs/portability.md`](../../engine/docs/portability.md)
and [`engine/docs/findings/17.md`](../../engine/docs/findings/17.md).

---

## A1. APISIX runs in the compose rig, configured declaratively

**Hypothesis.** APISIX starts from a checked-in `config.yaml` +
`apisix.yaml` on arm64, with no etcd and no Admin API, and proxies a
request to the echo.

**Observed.** Holds. `GET /a1/ping` returned 200 from the echo
(`method=GET`, `path=/a1/ping`) with Admin API off and no etcd.

**Falsified if.** The process does not listen; the file provider is
ignored; a route exists only after an Admin API PUT; or the request
never reaches the echo.

**If false.** Stop. Everything below depends on a declarative data plane.

---

## A2. Per-route header strip is declarative, and plugin order is controllable

**Hypothesis.** `proxy-rewrite` can remove inbound `x-ctier-*` names and
set the compiled replacements in one route, from the YAML file. Relative
order against another plugin is controllable with `_meta.priority`.

**Observed.** Holds, with a same-name constraint. `proxy-rewrite` set
overwrote inbound `x-ctier-tier` and removed `x-ctier-criteria`.
`_meta.priority` changed which write the echo saw (`rewrite` vs
`serverless`). Remove and set of the *same* name in one plugin dropped
the set value — the generator must not list a set name in `remove`.

**Falsified if.** Strip requires a custom plugin; set-after-remove cannot
be expressed in the file; or `_meta.priority` does not change which
plugin's write survives.

**If false.** C11 needs a plugin. That is a finding about APISIX, not a
licence to write one without recording it.

---

## A3. Token scope versus operation is expressible without custom code

**Hypothesis.** A stock plugin can refuse a bearer that lacks the
compiled operation scope, without Lua and without calling the issuer.

**Observed.** Falsified. A signed HS256 token without the operation
scope was 200, same as a token that carried it. Missing or unsigned
bearer was 401/403. Stock `jwt-auth` verifies signature, not `scope`.

**Falsified if.** `jwt-auth` accepts any signed token regardless of
`scope`; the only stock alternative (`openid-connect` `required_scopes`)
calls userinfo or introspection; or the check exists only as
`serverless-pre-function`.

**If false.** Same shape as Kong OSS: signature is a product plugin,
scope is Lua on the accepted bearer. That is a finding about Kong's
"needs Lua" story, not a win for APISIX.

---

## A5. Scope-to-operation is a stock plugin, with no issuer call on the request path

**Hypothesis.** APISIX can refuse a bearer that lacks the compiled
operation scope using a stock plugin, configured declaratively, with
no custom Lua and no per-request call to the authorisation server.

**Candidates.** `jwt-auth` (A3: no `required_scopes`). `authz-keycloak`
(declarative `permissions`, but `evaluate_permissions` POSTs
`urn:ietf:params:oauth:grant-type:uma-ticket` to `token_endpoint` on
the request path — measured). `openid-connect` `required_scopes` with
`public_key` and `claim_validator.issuer.valid_issuers` (local JWT;
discovery is in the schema but `get_discovery_doc` is skipped when
issuers are set). `use_jwks` / `introspection_endpoint` (network).
`opa`, `forward-auth`, `ldap-auth`, `wolf-rbac` (another server).
`authz-casbin` (a policy file, not the JWT operation scope).

Picked `openid-connect` + `public_key` + `required_scopes` +
`valid_issuers`: the only stock plugin that both names a required
scope and has a local verification branch.

**Observed.** Holds. A signed RS256 token with `operation-getBalance`
was 200; the same signature without that scope was 403; unsigned was
401/403. Echo saw no `/.well-known/` or token-endpoint hop.
`authz-keycloak` POSTed `/uma-ticket` on the same request, so it is
not an accepted mechanism.

**Falsified if.** The missing-scope token is 200; a hop to discovery,
introspection, userinfo, or UMA ticket happens on the request path;
the plugin cannot be expressed in standalone YAML; or Admin API is
required.

**If false.** Stop. Do not write Lua. The choice between a second Lua
branch and a documented gap is the author's.

---

## A4. A shared store is readable at request time without a network call

**Hypothesis.** A `lua_shared_dict` declared in `config.yaml` exists
inside the worker and can be read on the request path without hopping
to custody.

**Observed.** Holds. `ngx.shared.ctier_floors` was writable and readable
on the request path (`x-floor-store: held`). Task 32 uses that dict:
generated Lua publishes floors from a timer and reads them on the
request path. The dict declaration remains node config.

**Falsified if.** The snippet is ignored in standalone mode; the dict is
absent; or the only way to declare it is the Admin API.

**If false.** Level 4 is not available on this target; say so plainly.
