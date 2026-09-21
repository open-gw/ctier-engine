# Portability of enforcement

ADR-002 says the enforcement mechanism follows each gateway's own idiom. This
table is that claim in a form that can be checked. APISIX 3.13.0 standalone
is the third column, generated from the same compiled rows as Kong and Apigee.

The Kong column is **Kong OSS 3.9.3 as in this rig**, not Kong the product
family. Kong cells that rest on an unverified platform behaviour are
assumptions, not findings. See [`targets/kong/ASSUMPTIONS.md`](../../targets/kong/ASSUMPTIONS.md).
08c ran the three experiments against this OSS; all three held. That is
evidence for this Kong, not verification of every Kong, not of Enterprise,
and not of Apigee.

The generator compiles the **decision**, not the declaration. `x-ctier-tier`
and `x-ctier-criteria` are inputs to a resolution the classifier performs; the
enforcement point receives the result. Anything the generator can resolve at
deploy time must not be left for the enforcement point to recompute, because
every recomputation is a place two targets can silently disagree.

| What the enforcement point must do | Apigee | Kong OSS | APISIX 3.13.0 standalone |
|---|---|---|---|
| Operation resolution | **Deploy time.** Generator emits one conditional flow per classified operation; first matching flow wins. | **Deploy time / request time.** Generator emits one route per OpenAPI operation (method + path). 08c E1: Kong's router selected it. | **Deploy time.** One route per classified operation (method + `uri`). 17 live: `GET /accounts/12345/balance` echoed the compiled tier and operation. |
| Path specificity | **Deploy time.** Generator sorts literal paths ahead of templated siblings (`flow_sort_key`) because Apigee is first-match by document order. | **Deploy time, with a request-time remainder.** Generator sets `regex_priority` to the count of literal segments. 08c E2: the literal received its own tier with that hint in place. Unaided preference at equal priority was not tested. | **Deploy time.** `priority = 10 +` literal segment count. Untested as a dedicated 08c-style pair; the corpus includes both shapes and agreed. |
| Default tier when undeclared | **Deploy time.** `AM-DefaultTier` sets 4; classified flows override. | **Deploy time / request time.** Global `ctier` instance `tier = 4` applies the undeclared default only when the matched route is in the `governed-set` (08c E3: `exportStatements`). A matched route absent from that set is refused and recorded undetermined — not Tier 4. | **Deploy time.** Catch-all `/*` at priority 1. A composed-but-unassigned path gets the undeclared default (423, Decision on the sink). A path the composition does not contain is refused and recorded undetermined. A more specific added route wins over `/*`. Unclassified operations are not given their own route. |
| Inbound header removal | **Request time.** JS prefix-walks `x-ctier-*`; AssignMessage removes aliases a prefix misses (`X-Correlation-Id`, `Idempotency-Key`, `X-Idempotency-Key`). | **Request time.** Lua prefix-scans `x-ctier-*` and the same aliases. | **Request time.** Lua prefix-scans the namespace and aliases. `proxy-rewrite` remove is aliases only (A2: cannot remove-and-set the names it writes). |
| Tier propagation upstream | **Deploy time / request time.** Per-operation `AssignMessage` writes `ctier.tier`. Target PreFlow JS sets `x-ctier-correlation-id`. It does not set `Idempotency-Key`. | **Request time.** After strip, the plugin sets `x-ctier-tier`, `x-ctier-deployment`, `x-ctier-correlation-id`. `Idempotency-Key` is set from the ledger only when custody is compiled. | **Deploy time / request time.** `proxy-rewrite` sets `x-ctier-tier`, `x-ctier-deployment`, `x-ctier-operation`. Lua posts the decision when custody is configured, sets the join key, and copies `idempotencyKey` from the ledger 201 when present. |
| Bounds escalation | **Request time comparison, deploy-time value.** Nested `Condition` on `request.queryparam.<parameter>` inside the operation flow. The unexceeded path keeps the compiled floor; the exceeded path assigns the escalated integer, already resolved by the generator (C3). | **Request time comparison, deploy-time value.** Lua compares a configured query parameter to a configured maximum. The consequence of that comparison is known at generate time (C3); Kong still applies it in `escalate` rather than emitting the integer. | **Request time comparison, deploy-time value.** Lua `tonumber` of the compiled query parameter. The consequence (abort, withhold, or overwrite the tier header) is compiled. Platform `vars` were not used: the corpus needs `101.0` and `1.01e2`. |
| Execute (tiers 1, 2) | **Deploy time.** No fault rule; request continues. | **Request time.** Plugin does not exit; request continues. | **Deploy time.** No abort plugin; request continues. |
| Withhold (tier 3) | **Deploy time.** PostFlow `RF-Provisioning` (403) when `ctier.tier = 3` — Level 2 without custody, not 202. | **Request time.** Plugin exits 403 when the (possibly escalated) tier is 3 and `custody` is false. Same Level 2 posture. | **Deploy time at L2; request time at L3.** Serverless records `refuse-provisioning` then exits 403 without custody. With custody, serverless POST `/v1/pending` (same hop Kong makes in Lua). |
| Refuse-and-suspend (tier 4) | **Deploy time.** PostFlow `RF-Tier4` (423) when `ctier.tier = 4`. | **Request time.** Plugin exits 423 when the (possibly escalated) tier is ≥ 4. | **Request time.** Serverless records `refuse-and-suspend` on the gateway-log sink, then exits 423. No ledger POST. |
| Refuse-provisioning (excluded) | **Deploy time.** Exclude flow sets `ctier.excluded`; PostFlow `RF-Provisioning` (403). | **Request time.** Route-level instance has `excluded: true`; plugin exits 403. A route-level instance is required so the global T4 does not 423 instead. | **Request time.** Serverless records `refuse-provisioning` then exits 403. No `required_scope` on the excluded route, same as Kong. |
| Accumulated consequence (scope floor) | Not built. | **Out of band, then a local read.** A timer polls custody `GET /v1/floors` every **1000 ms** (`floor_poll_ms`, same class of explicit bound as the **200 ms** `custody_timeout_ms`). The request path looks up `ngx.shared.ctier_floors`. No per-request hop. A missing entry is no escalation. | **Out of band, then a local read.** Same property as Kong: `ngx.timer.every` polls `GET /v1/floors` every **1000 ms** (`floor_poll_ms`, compiled into the Lua). The request path looks up `ngx.shared.ctier_floors` (A4). No per-request hop. A missing entry is no escalation. Remaining: the dict is node config (`lua_shared_dict ctier_floors 1m` in `config.yaml`), not generated; the poller starts lazily per worker (no plugin `init`), claimed with a pid-keyed `dict:add`. |
| Token scope vs operation | **Deploy time grant.** Generator emits client scopes; excluded operations are omitted from the grant. | **Deploy time grant, request-time claim.** Same grant. Bundled `jwt` verifies signature and `exp`; `ctier` reads `scope` on that bearer. Missing required scope is 401 (`refuse-unauthorized`). No introspection. Kong Enterprise ships OIDC / `scopes_required` — **not measured**; this cell is OSS. | **Deploy time grant, request-time claim.** A3: stock `jwt-auth` still does not check `scope`. A5: stock `openid-connect` `required_scopes` with `public_key` does, locally. Missing scope is **403**. No introspection, no UMA ticket. `authz-keycloak` was measured and posts `uma-ticket` on the request path — not accepted. |

`deploy time` means the generator resolved it into configuration. `request time`
means code (Lua) or a platform evaluator still chooses after the request is
seen. Apigee PostFlow conditions are evaluated per request but the *mapping*
from tier to fault is compiled; Kong must compute that mapping in Lua because
it cannot branch declaratively, and because bounds can change the tier after
the instance was configured.

## Two cells that are not merely mechanical

**Path specificity.** Apigee is first-match by document order, so the generator
sorts literal paths ahead of templated siblings. Kong is *not* sorted that way.
08b hedged with `regex_priority` from literal segment count. 08c E2: the
literal received its own tier with that hint. Same-priority unaided preference
is still untested.

**Header removal.** 1.5.0 strips the whole `x-ctier-*` namespace on
ingress, plus aliases a prefix misses (`X-Correlation-Id`, and the
idempotency names that are not in the namespace at all). Apigee has
no wildcard, so a JS policy walks request header names and drops
the prefix; AssignMessage drops the aliases. Kong and APISIX Lua
do the same walk. `X-Ctier-Tier` is an alias the spec names and a
prefix already catches. `X-Correlation-Id` is the one a prefix
target can still miss.

**Fragment mode (C11).** On any of the three targets, this engine does
not guarantee strip-before-read against arbitrary existing
configuration. See what this engine does not make unavoidable.
Bundle mode gets the ordering for free because it owns the path.

**Bounds** is the other non-mechanical split. Both targets compare the request
to `x-ctier-bounds` at request time — Apigee with a declarative condition,
Kong with a Lua comparison — because the predicate depends on the request.
The escalated *value* does not: the generator knows the resolved floor and
the C3 consequence, so it knows the integer to assign. Apigee emits that integer in `AssignMessage`.
Kong still adds one in `escalate`. Pushing the consequence to deploy time is
what keeps the targets aligned; leaving the comparison at request time is
what makes the predicate true.

## Kong plugin request-time branches

Every `if` in `targets/kong/plugin/handler.lua`. Column three: could this have
been resolved from the qualified spec at generate time and baked into the
plugin instance config? If yes, it belongs in the generator.

| Branch | What it decides | Could the generator have decided it? | If yes, why is it here |
|---|---|---|---|
| `name` is a string and starts with `x-ctier-` | Whether this inbound header is stripped | No. The attacker chooses the names. The spec does not list them. | — |
| `not bound_parameter or not bound_max` | Skip the bounds comparison when the instance has none | Yes, in the weak sense that the generator already omits the fields. | Same handler serves the global instance (no bounds) and route instances (sometimes bounds). Absence of config is the skip; not a governance decision. |
| query value is a table | Which value to read when Kong returns a multi-value arg | No. Request shape. | — |
| query value is nil | Bound not present on this request | No. Request. | — |
| `tonumber(raw) and n > bound_max` | Whether the request exceeds the declared bound | No. Needs the request. | — |
| `tier < 4` in `escalate` | Ceiling: do not raise past 4 | The constant 4 is known. The *input* tier is not, after bounds. | Part of the bounds arithmetic. |
| `conf.excluded` | 403 provisioning vs continue into tier logic | **Yes.** Exclusion is in the spec. Already baked as `excluded: true`. | Stays. A route-level `ctier` instance is required to *override* the global T4 (otherwise Kong 423s). That instance must itself 403. Moving the refuse to `request-termination` would not suppress the global `ctier` plugin (different plugin names both run). Enactment of a generate-time flag, same shape as Apigee's PostFlow condition on `ctier.excluded`. |
| `has_required_scope(conf.required_scope)` | 401 vs continue | **No.** The required *name* is compiled. Whether this token carries it is not. | Legitimate third branch: it depends on the token. Reads the bearer Kong's `jwt` plugin already accepted. Not a call to the issuer. Absent `required_scope` (excluded routes) is skip, so a token that reached an excluded operation is still 403 provisioning. |
| `tier >= 4` | 423 vs continue | No, once bounds can raise the configured tier. Without bounds, yes. | Disposition implied by the (possibly escalated) tier. Kong cannot branch declaratively. |
| `tier == 3 and not conf.custody` | 403 vs continue, for Tier 3 | `custody` is generate-time (never emitted; default false). The *tier* may have been raised by bounds from 2, so the T3 case is not always known at generate time. | Disposition implied by the (possibly escalated) tier, plus a generate-time custody flag. If `custody` were true today, this branch would fall through and **proxy** Tier 3 — withhold (202) is not implemented. Finding; stays until custody exists. |
| `not conf.operation and not in_governed` | Undetermined refusal vs undeclared default on the global instance | **Yes.** The `governed-set` is compiled. Whether this request matched a name on it is not — the router chooses the route. | The undeclared default stays for a composed route with no instance (C2). A miss is an Attempt, not Tier 4. |
| `conf.operation` | Whether to set `x-ctier-operation` upstream | Yes. Generator always sets it on route instances and omits it on the global instance. | Optional config field, not a governance decision. |
| `ngx.shared.ctier_floors` missing or no key for the scope | Whether to raise the compiled tier | No. The floor is runtime state. | Absence is no escalation, not Tier 4. Logged; the request continues at the compiled floor. |
| published floor `> tier` | Raise to the floor | No. | Heuristic escalation. Can only raise. |

Three branches are the legitimate request-time core: **bounds comparison**,
**disposition implied by the (possibly escalated) tier**, and **whether this
token carries the compiled required scope**. `excluded` is still the
suspicious one: the generator already decided it; Lua enacts it because the
same plugin must override global T4. It was not moved.

The scope-floor read is a further request-time branch, added in 12a. The
*value* is computed in custody from the ledger; the enforcement point only
compares it to the compiled floor. The network cost sits on `ngx.timer.every`,
not on the request.

## OSS versus Enterprise

Three request-time Lua branches are now in the plugin: bounds, disposition,
and required scope. The honest axis is **which capabilities you pay for**,
not which vendor you chose. Apigee remains the other column because it is
the reference target; it is not the explanation for why Kong OSS is in Lua.

| Capability | Kong OSS (this rig) | Kong Enterprise | Apigee |
|---|---|---|---|
| Bounds vs compiled max | Lua | Lua (no product plugin either; **unmeasured**) | `Condition` |
| Disposition from (possibly escalated) tier | Lua | Lua (**unmeasured**) | PostFlow fault |
| Token scope vs operation | Lua on the accepted bearer | OIDC / `scopes_required` (**unmeasured**) | deploy-time grant |

**"Kong needs custom Lua" and "Kong OSS needs custom Lua" are different
statements.** This matrix does not treat Enterprise as measured. Do not
read the OSS cell as a finding about Kong Gateway as a whole.

## Paid capability, three engines

The axis this table exists for is **which capabilities you pay for**, not
which vendor you chose. Two data points could have been coincidence. A
third is enough to split the claim.

| Capability | Kong OSS (this rig) | Kong Enterprise | APISIX 3.13.0 OSS | Apigee |
|---|---|---|---|---|
| Bounds vs compiled max | Lua | Lua (no product plugin either; **unmeasured**) | Lua `tonumber` (stock `vars` not used) | `Condition` |
| Disposition from (possibly escalated) tier | Lua | Lua (**unmeasured**) | Serverless records then refuses when the tier is known at generate time | PostFlow fault |
| Token scope vs operation | Lua on the accepted bearer | OIDC / `scopes_required` (**unmeasured**) | A5: stock `openid-connect` `required_scopes` (local JWT). `jwt-auth` still does not. Missing scope is 403 | deploy-time grant |
| Inbound `x-ctier-*` strip | Lua prefix scan + aliases | **unmeasured** | Lua prefix scan + aliases (A2: set names are not also removed) | JS prefix walk + alias AssignMessage |

**Token scope versus operation is missing from Kong OSS's JWT plugin and
from APISIX `jwt-auth`.** It is not missing from APISIX as a gateway:
`openid-connect` `required_scopes` with a configured public key checks
the compiled operation scope on the accepted bearer without calling
the issuer (A5). That is the second time this APISIX's plugin model
does in configuration what Kong OSS does in Lua — after bracketing
(A2 `_meta.priority`). The interesting variable is how much of a
gateway's behaviour is expressed as configuration rather than as
code, not open-source versus commercial and not one vendor versus
another.

Whether Kong Enterprise `scopes_required` closes the OSS JWT gap
remains unmeasured and must stay visibly so. APISIX `authz-keycloak`
closes nothing we can accept: it posts a UMA ticket on the request
path.

**Strip and static refuse are not behind a paywall.** APISIX does with
stock plugins what Kong OSS does in the `ctier` plugin: remove a closed
header set, abort 403/423. "This framework needs paid plugins" is false
as a general claim. "OSS JWT plugins do not check an operation scope"
is true twice; "this APISIX cannot check an operation scope without Lua"
is false.

Keycloak's downscope enforcer in 26.5 is a third-product, later-release
point on the same axis. It was not re-measured here. The APISIX column
does not make that cell measured either.

## Corpus implications (blocks 08c)

One `(appliedTier, disposition)` per case. Forking `expect` by target is a
format change. It is only warranted where a gateway **cannot express** what
the other can, so they must disagree on that pair.

**Empty set.** No current case needs per-target expectations.

| Split | Platform cannot, or just different? | Changes `expect`? |
|---|---|---|
| Path specificity | Same hazard, different mechanism (sort vs `regex_priority`). | No. |
| Default undeclared tier | Same property, different mechanism (PreFlow vs plugin precedence). | No. |
| Header removal | Apigee **cannot** prefix-strip; Kong Lua can. This engine sends `x-ctier-tier` after strip (C11), which is in Apigee's closed set. Classification agrees. Echo of an *unknown* `x-ctier-*` is not what `expect` holds. | No for this corpus. |
| Bounds escalation | Both compare a query parameter at request time (Apigee `Condition`, Kong Lua). The escalated integer is resolved at generate time on Apigee; Kong still computes +1 in the plugin. Same property, different mechanism. | No. One expect (the classifier). |
| T3 withhold vs 403 | Both Level 2 targets refuse as provisioning. Classifier `withhold` is already out of scope against those proxies. | No. Already excluded, not forked. |

08c writes against the format 08a established.

## Escalation window (12a)

ADR-006 accepted that the request crossing the accumulation threshold
executes at the compiled tier, and only subsequent requests in that scope
are governed. That is still true.

With an out-of-band poller the true window is larger:
**threshold-crossing plus one poll interval**. That bound is
**Derived** from configured `floor_poll_ms` (1000 ms on both Kong
and APISIX). Classified in [`measurements.md`](measurements.md).
The Decision that crosses the threshold is written during `access`;
the floor is visible to the enforcement point only after the next
successful timer tick. A defence with a known, bounded gap is honest.
`appliedTierAtLeast` in corpus 0.3.0-draft asserts the bound rather
than encoding the interval into an exact request index.

`floor_poll_ms` and `custody_timeout_ms` are Configured (1000 ms and
200 ms). Neither is inherited from an HTTP library. The dictionary
TTL is Derived (two intervals). An Observed 216 ms sample on APISIX
is in the measurements file with its bound beside it; it is not the
bound.

The poller start differs. Kong's plugin module starts `ngx.timer.every`
once per worker from `access`. APISIX has no equivalent init: generate
emits the timer inside `serverless-post-function`, and a pid-keyed
`ngx.shared.ctier_floors:add` makes it one timer per worker even though
every classified route carries a copy of the chunk. The shared dict
itself is node config on APISIX (`lua_shared_dict` in `config.yaml`),
compose env on Kong. An operator who omits the dict gets no escalation,
logged, not a refuse.

## Suspension window (13a)

Exclusion and suspension are the same compiled fact: the operation scope
is absent from the agent client. Exclusion never grants it. Suspension
removes it. The enforcement point does not ask the authorisation server
whether the agent is paused; it reads `scope` on the bearer Kong already
accepted.

The delay is therefore **the remaining lifetime of a token that still
carries the scope**. New tokens omit it and are 401. Live, `exp - iat`
on a token the rig obtained matches the compiled 30 s
`accessTokenLifespan` (**Configured**; [`measurements.md`](measurements.md)).
An organisation choosing an hour-long token has chosen an hour-long
suspension delay. Closing the window with token introspection on the
request path is forbidden.

## Delegation by client entitlement (13c)

Keycloak 26.3.3 does not refuse an expanded re-exchange against the
subject token's lineage (13b E2). It does bound a token against the
**requesting client's entitlement**. A compiled client that was never
granted `operation-initiatePayment` cannot obtain it by exchange or
re-exchange (13c E4). The generator emits one confidential client per
declared agent identity, each with its own optional-scope set, plus the
importable exchange switch and an audience mapper so a parent token
lists the sub-client in `aud`.

That is a narrower claim than RFC 8693. Delegation is bounded to
identities declared at deploy time. An agent cannot mint an arbitrary
sub-agent at runtime with an arbitrary narrower scope; it can only
exchange into a client someone compiled. Kong still reads `scope` on
the bearer it already accepted. No introspection.

A sub-agent identity may have one parent. Two parents are rejected at
generation, with both named. "B acting for A1" and "B acting for A2"
are not the same authority. They may warrant different scope sets, and
collapsing them into one client hides that. The duplication is not a
workaround for a limitation; it is the more accurate model, and the
ambiguity disappears by construction rather than being detected at
read time.

## Reconstructing the chain from a record (13g)

A Decision or Attempt carries `deploymentDigest`. That digest is taken
over the canonical serialisation of the composed interface description,
the tier declarations, and the declared agent identities with their
entitlements. Regenerating from those inputs produces the same digest;
the generated deployment is the one that matches. The declared topology
is in that deployment — each identity, its parent, its entitlements —
and the chain is the path from the record's `agentId` through those
parent links.

This recovers the **declared** topology, and it is unambiguous only
because a sub-agent identity may be declared under at most one parent,
enforced at generation since 13e. The digest is not what makes it
unambiguous — the constraint is. No new record field. No mapper.

## Compatibility shims and their removal versions

None. Engine **0.3.0** removed every shim whose stated removal version
was 0.3.0 or earlier, including `ledger-*` schema heads (dated 0.2.0;
0.2.0 was never a published engine release). This table is empty
because a row that has already been removed is not a commitment.

**Record schema versions** and engine versions are not the same
milestone. Decision stays `0.2.0`. Attempt is `0.3.0`:
`declaredTier` is present when a declaration was made and omitted
when none was. Outcome stays `0.1.0`. Those are specification
format versions.

These two surfaces keep a composition-named field because they are
not the deployment digest:

| Surface | Keeps | Because |
|---|---|---|
| compose manifest, coverage report | `compositionDigest` | compose-time; compose cannot see agent identities |
| conformance corpus document field | `composition` | digest of the API the cases classify (C13), not a ledger field |

## Custody execute is a second ingress path

Custody calls `CTIER_BACKEND_URL + path` directly. It does not
re-enter Kong, Apigee, or APISIX. Task 17 Check 1 measured that.
The backend therefore has **two callers with different properties**:

- Requests through the enforcement point, where the compiled decision
  applies and this engine strips inbound `x-ctier-*` headers (C11).
- Requests from custody, where none of that runs. The decision was
  already made; that is why this path exists.

The headline claim that the gateway is the chokepoint has this
standing exception. A deployment must restrict who may call the
backend — by network policy or mutual authentication — because
ctier does not enforce anything on custody's path.

The live rig isolates echo on an internal network and does not
publish it to the host (14a.1). That is a property of this compose
file, not of a deployment that generates from the same artefact.

The specification's threat model needs the same exception written
down. That is a spec change (with 14b's `spec/headers.md` and 1.5.0),
not this file's.

## What this engine does not make unavoidable

The specification this engine implements ([`SPEC.md`](SPEC.md))
names deployment conditions. This engine cannot make them hold.
What this engine and this rig do:

1. **Backend callers.** The live rig isolates echo on an internal
   network and does not publish it to the host (14a.1). That is a
   property of this compose file.
2. **Custody execute.** Custody calls the backend directly (14a).
   This engine does not sit on that path.
3. **Fragment strip order (C11).** Kong plugin PRIORITY is a
   constant on the plugin (ctier is 800), not a field in the deck.
   CORS (2000), jwt (1005) and request-transformer (801) all run
   *before* that strip. APISIX `_meta.priority` is per plugin
   instance but an existing rewrite-phase function can still sit
   above it. Apigee PreProxy FlowHook runs before any ProxyEndpoint
   PreFlow step we prepend, and is not in the artefact we inspect.
   Bundle mode owns the path. No runtime check is added to
   compensate. The conflict report names what was found; a collision
   that writes a reserved header after the strip, or a reader
   before it, refuses to emit.
4. **Error-log level (C10).** The claimed sink is written at
   NOTICE: `kong.log.notice` on Kong, `ngx.log(ngx.NOTICE)` on
   APISIX. nginx `error_log ... warn;` is an ordinary production
   setting. NOTICE is below it. That deployment loses every
   record, and C10 with it. Sequencing detects a missing record
   inside a sink; it does not detect a sink that was never
   written. This engine does not check the configured level at
   startup. The live APISIX node pins `error_log_level: notice`.
   Kong compose does not set a level. An operator who has not
   kept notice (or more verbose) on the error log has not
   recorded.
5. **C13 witness.** The live cases generate against one
   composition and present another with the same operations.
   Generate refuses. That mismatch is caught. The witness
   does not show every mismatch. Same composition, one
   operation changed, is a different shape: the digest moves
   because an assignment moved. A forged digest on a running
   deck is a different shape: this engine stamps what it
   computed and does not re-hash the deck. The witness says
   nothing about a composition that changes after generation.
   That is the drift 38 and 41 measured.

## Record paths this engine claims

C10. This engine claims one sink: the `[ctier-decision]` and
`[ctier-attempt]` lines it writes with `kong.log.notice` and
`ngx.log(ngx.NOTICE)`. Those lines land in the gateway error log
only when that log accepts NOTICE.
Levels 1 and 2 write Decisions there. Attempts write there at
every level. When `POST /v1/ledger` fails open, this line is the
backstop — including at Level 3.

A path a record leaves the enforcement point is not a sink unless
this engine claims it.

| Path | Claim |
|---|---|
| `[ctier-decision]` / `[ctier-attempt]` via `kong.log.notice` / `ngx.log(ngx.NOTICE)` | **C10 sink.** The gateway-log sink. Error log, not nginx `access.log`. |
| nginx / Kong / APISIX `access.log` | **Not a sink.** This engine does not write a decision record there. A request line is not a Decision. |
| `POST /v1/ledger` | **Not claimed.** Fails open. A missed write does not unmake the disposition. The error-log line is what this engine claims when the POST fails. |
| `kong.log.err` / `ngx.log(ngx.ERR)` (`ctier ledger decision failed`, custody persist failed, floor poller) | **Diagnostic.** Not a Decision or an Attempt. |
| Kong JSONL `ledger_fallback` | Custody ingest for Attempts. Not a third C10 sink. |
| Apigee `print()` | **Not a sink.** Trace/Debug only (29). |

`[ctier-decision]` in the error log is the gateway-log sink, not a
diagnostic. Other error-log lines are diagnostics. The two share a
file. They do not share a claim.

**What an emitter is.** The sequence is per emitter, not global.
An emitter is one worker process. Emitter identity includes the
worker: `epoch=` is `{ngx.now()}-{pid}`, minted on first allocate
in that worker. A new epoch after a restart is not a hole.

- **Kong.** Worker-local upvalue `seq_state` in the plugin
  module. The counter is not in shared memory.
- **APISIX.** `ngx.shared.ctier_seq` (node config, same class as
  `ctier_floors`). Keys are `epoch:{pid}` and `n:{pid}`. The
  store is shared; the sequence is still per worker.
  serverless-post-function loadstrings per route;
  `package.loaded` is not an emitter.

Two workers do not share a counter and do not reuse an epoch.
`(epoch, seq)` is not predicted to collide. A reader holding only
the claimed sink's contents can see that a record is missing on
one emitter: missing integers between that epoch's min and max.

**Default live pin is one worker.** Compose defaults
`KONG_NGINX_WORKER_PROCESSES` / APISIX `worker_processes` to 1.
The rig can raise that (`CTIER_KONG_WORKERS` /
`CTIER_APISIX_CONFIG` with substituted `worker_processes`).
`detect_gaps` groups by epoch, so interleave is not a hole by
design. Workers do not contend on one counter. Collision is not
the property under test.

**Multi-worker (70).** Both engines ran the induced-gap case with
two workers. Concurrent requests produced at least two
`sinkEpoch` values in one sink file; `detect_gaps` reported no
false hole from that interleave; dropping a middle seq on one
epoch still detected the gap. 50a's reasoning held. The default
suite still pins one worker; the two-worker cases are
`test_*_induced_gap_with_two_workers`. See
[`findings/50a.md`](findings/50a.md) and [`findings/70.md`](findings/70.md).

**What it does not detect.** Wholesale delete or truncate of the
sink. An emitter that never started — a worker that wrote nothing
leaves no epoch to audit. Ordering across emitters. The operator
must not treat the sequence as a global log or as a bound on those
three.

## Profile this engine implements

This engine implements `standard`. It does not implement
`constrained`. Compiled client entitlement is the bound. The
enforcement point does not check a delegation chain and does not
consult custody for suspension.

## The catchall does not catch a later add

C12. This engine's `governed-set` is the operations in the
composition generate consumed. A route added after generation
cannot be closed from inside the configuration. 41 narrows the
gap that 38 measured. It does not close it.

**What it catches.** Kong's global `ctier` instance runs on a
matched route. If that route's name is in the governed set and
has no route-level instance, the undeclared default applies
(tier 4). If the name is not in the set, the request is refused
and recorded undetermined. APISIX's `undeclared` route is `/*`
at priority 1. A composed-but-unassigned path that reaches it
gets the undeclared default and records
a decision (same sink as classified
Tier 4). A path the composition does not
contain is refused and recorded undetermined.

**What outranks it.** Kong: a route-level `ctier` instance
overrides the global plugin; a path that matches no route is
404 and is not recorded. APISIX: a more specific URI wins over
`/*`, including an add at a lower priority than the catchall.
38's priority 100 was sufficient, not necessary. Raising the
catchall's priority is not the fix: there is no number above
specificity, the same shape 16c found for Kong's strip. On
both engines a route added after generation can still escape.
An operator who has not kept the running estate inside the
`governed-set` has not covered those paths.

## Identity headers were removed for cause

Custody used to send `x-ctier-approver` and `x-ctier-agent` on the
execute request. 13h's dual-emit window does **not** apply: that was
a rename, and the risk of breaking a reader outweighed the overlap.
These two were a forgery path. A compatibility window would have
kept the hole open and called it courtesy. They are gone.

Task 17 already established that the execute request never meets
this engine's strip set (C11), so specify-and-strip was never
available.

A backend recovers agent and approver as: correlation id on the
execute request (`x-ctier-correlation-id`) → decision record.

## Level 2 and C7

Level 2 is generate-without-custody: enforce 1/2/4, refuse Tier 3 as
provisioning. It is the rung that sells "no new runtime."

**What it defends.** Inbound `Idempotency-Key` and `X-Idempotency-Key`
are stripped on Kong, APISIX, and Apigee. An agent cannot choose the
key the backend would honour.

**What it does not.** It does not emit a derived HMAC. This engine
derives that key from request content and stores it with persisted
context; it does not re-derive at execution time. Level 2 has no
persist, so there is nowhere to store it. Kong and APISIX copy
`idempotencyKey` from the ledger 201 when custody is present (Level
3) and otherwise set nothing. Custody's own execute always emits the
stored key.

A Lua HMAC on the gateway 500'd every Level-2 execute. Hashing the
request at forward time is request-time compute the compiled
architecture is built to avoid, even if the 500 were fixed. A
per-request `ngx.md5` of a minted id is not this engine's derived
key either: it would look like a key while guaranteeing the backend
never deduplicates.

A backend that honours `Idempotency-Key` therefore sees a
**ctier-derived HMAC at Level 3**, and **no key at Level 2**. The
agent's value is gone in both cases. This engine emits the stored
key only where custody exists (C7). Whether the specification's
MUST should be scoped that way, or Level 2 needs another mechanism,
is not decided here.

No target provides the derived key on the forwarded path, for the
reason 22 established: the material includes the body, and two
languages already disagree on the edges. Apigee used to HMAC
anchor and path only, collapsing every body onto one key. That is
gone. Kong and APISIX never derived on the hop. The three targets
now match: strip the agent's key; emit a stored key only from
custody (Kong/APISIX copy the ledger 201; custody execute emits
it). Removing Apigee's header was alignment, not dropping a
protection.
