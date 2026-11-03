# Consequence Engine — Product Requirements, v1

Reference implementation of the consequence-tiered governance model
(`github.com/open-gw/ctier`, doi.org/10.5281/zenodo.22020288).

---

## 1. What this is

A design-time library and generator that classify an agent-initiated API operation by the
consequence of executing it incorrectly, and compile that classification into the
enforcement point's own native configuration ([ADR-002](adr/0002-tier-compiled-to-gateway-native-configuration-at-deploy-time.md)).
No classification logic runs at request time.

It is **not** a gateway. The generator emits a complete policy bundle or mergeable
fragments for whatever gateway is already in place.

## 2. What v1 must prove

The claim on which the whole model rests is that consequence-based governance can be enforced
at the gateway, in the request path, without a human ever occupying that path. v1 exists to
demonstrate exactly that, end to end, with one gateway.

**In scope for v1**

- A design-time generator that reads the interface description and emits the enforcement
  point's native configuration, in bundle or fragment output mode, with Tier 4 as the
  structural default ([ADR-002](adr/0002-tier-compiled-to-gateway-native-configuration-at-deploy-time.md))
- Runtime escalation on request content exceeding declared bounds, and on accumulated
  consequence read as a scope floor — never de-escalation. Exclusion, suspension and
  delegation-chain integrity are enforced at the authorisation layer
  ([ADR-003](adr/0003-authorisation-decisions-belong-at-the-authorisation-layer.md))
- Tier 1 and 2: permit, with the tier's logging and state-capture obligations
- Tier 3: withhold, persist execution context, emit an approval event, return a non-retryable
  202; resume from persisted context on approval
- Tier 4: refuse, suspend the agent for the operation class, return 423
- One reference generator target (Apigee). A second target is demand-driven
- Append-only decision log

**Out of scope for v1**

- Generator targets beyond the reference and one second target
- Durable store beyond SQLite; no clustering
- A reviewer UI. The consuming application is the approval surface
- Learned classification as authority. The recommender is triage
- Credential minting. v1 replays the caller's credential; scoped minting is v2

## 2a. Where design time meets runtime

An OpenAPI document is design-time data. A gateway is a runtime component. The binding between
them is the part most easily got wrong, and the architecture places it deliberately.

**Tier assignment is compiled into the gateway at deploy time, not resolved at request time.**

Two declaration modes, both first-class
([ADR-001](adr/0001-consequence-declared-in-an-interface-description.md)). Inline `x-ctier-*`
in the OpenAPI document is the default and the fast path: one artefact, one review, one
team. Description plus N governance overlays (Overlay 1.1.0, RFC 9535 JSONPath), applied in
order, is the alternative where governance and interface ownership genuinely differ.

A generator reads the declared description and emits the enforcement point's native
configuration, as a complete bundle or as mergeable fragments
([ADR-002](adr/0002-tier-compiled-to-gateway-native-configuration-at-deploy-time.md)).
No classification logic runs at request time. The gateway's own router — which already
resolves which operation a request matched — performs the resolution.

Three properties follow, and each removes a class of failure rather than mitigating it.

**No second router.** An engine that matched method and path against path templates itself would
be a second routing implementation capable of disagreeing with the gateway's. The disagreement
would be silent and would appear only in edge cases. Compiling the assignment into the gateway
removes the possibility rather than reducing its likelihood.

**No version skew.** The tier travels with the gateway revision. There is no separately loaded
specification that can lag behind the deployed interface, and therefore no window in which a
live route exists that the governance layer has not heard of.

**Fail-closed is structural.** A default policy in the request pre-flow sets the tier to 4;
per-operation policies override it within their conditional flow. An operation nobody classified
receives no override and inherits 4 — not because a rule enforces it, but because the absence of
a policy produces it. The safe default is the default.

An overlay action whose `update` assigns a tier of 1, 2 or 3 MUST select exactly one
operation. An action MAY select many operations only when it assigns Tier 4. The rule is
scoped to overlays. Inline declaration is per-operation by construction, so it does not
apply there. Split ownership makes adding an operation a two-team change; the overlay lags;
fail-closed suspends agents; and the fix everyone reaches for is a blanket assignment across
a path prefix, which destroys the model in one line. Raising many operations to the safe
floor at once is never the dangerous direction. Lowering many at once always is.

The coverage report warns at Level 1 and fails the build from Level 2 upward. A gate that
blocks a pipeline before anything is being enforced is friction with no safety value.

**What remains at the enforcement point.** Resolve the declared floor, compare request
content against declared bounds, read the scope floor, pick a disposition. All of that is
native configuration
([ADR-002](adr/0002-tier-compiled-to-gateway-native-configuration-at-deploy-time.md)).

**Exclusion, suspension and delegation** are enforced at the authorisation layer, not the
enforcement point
([ADR-003](adr/0003-authorisation-decisions-belong-at-the-authorisation-layer.md)).
Where no authorisation server performs token exchange with scope reduction, the enforcement
point checks the chain itself and a scripted policy is required. That is a stated
constrained deployment profile.

**Per-gateway work sits in the generator.** Apigee bundles, Kong declarative configuration
and APIM policy documents differ substantially. All of that difference is design-time.
Gateway-agnosticism means one definition, one conformance suite and compiled targets — not
one runtime artefact.

## 2b. The five criteria

Reversibility is the axis the tiers are defined on. The other four criteria — blast radius,
data sensitivity, compliance trigger, idempotency — are escalators on that axis.

A population-scale write collapses reversibility to `undo-restores-record-only` by
construction: the population affected while the state stood is unbounded, so the undo cannot
restore the effect whatever the data was. That is why blast radius outranks data sensitivity.
It is not a precedence preference.

Reversibility does not describe disclosure. You cannot un-disclose. A population-scale read of
personal or regulated data is therefore Tier 3: a delay, not a handover.

A partially filled `x-ctier-criteria` object classifies high. The field defaults are
`reversibility=none`, `data_sensitivity=regulated` and `idempotency=unsafe`. That is
deliberate.

## 3. Conformance

An implementation is conformant if it satisfies all of the following. These are the
requirements a second implementation would have to meet, and they are the point of writing a
PRD before code.

**C1 — Classification precedes routing.** No governed operation reaches its target before a
decision is recorded.

**C2 — Undeclared fails closed.** An operation reachable within a granted scope but carrying no
`x-ctier-*` declaration is treated as Tier 4.

**C3 — Escalation is unidirectional.** No runtime input may produce a tier lower than the
declared tier, and no escalation stage may produce a tier lower than the tier entering that
stage.

**C4 — The human is never in the request path.** No decision path blocks on human input. The
enforcement point must not hold a connection open pending a human decision.

**C5 — The withheld response is terminal and non-retryable.** Status outside conventionally
retried classes, no `Retry-After`, explicit `retryable: false` and an `agentAction` directive.

**C6 — Execution is from persisted context.** On approval, the operation executed is
byte-identical to the operation described in the approval event. The agent does not resubmit.

**C7 — Idempotency keys are derived, not generated.** Derived from the declared `operationId`
(or method + path template) plus a canonical serialisation of the request specifics, so a
resubmission resolves to the pending context rather than creating a second one.

**C8 — Expiry and rejection differ.** Rejection pauses the agent for the operation class.
Expiry refuses the single operation and leaves the agent working.

**C9 — Tier 4 has no resume path.** No state transition exists by which a Tier 4 operation
executes under the agent's identity.

**C10 — Decisions are recorded before they are acted on**, including declared tier, applied
tier and escalation reason.

**C11 — An injected tier is trusted only from inside the trust boundary.** A tier arriving as an
inbound client header MUST NOT be honoured. The enforcement point MUST strip any client-supplied
tier at the edge before setting its own, or the value MUST be integrity-protected such that the
engine can distinguish a gateway-set value from a caller-set one. Without this, an agent
declares itself Tier 1 and the model collapses.

**C12 — Tier assignment is bound to the deployed interface revision.** The declared tier MUST
travel with the gateway configuration rather than being resolved from a separately loaded
document at request time, so that a deployed operation cannot exist without its governance
assignment. Where a fallback resolution path is used, an operation matching no loaded
specification MUST be treated as undeclared.

**C13 — Tier assignment is bound to the composed interface description.** Where
the declaration is assembled from a description plus one or more governance
overlays, the assignment is bound to the digest of the composition, and every
input artefact and its digest MUST be recorded in the emitted gateway
configuration and in each decision record. C12's binding is to the
composition, not to either input alone.

## 4. Interfaces

The generator emits the enforcement point's native configuration. There is no per-request
classification endpoint.

**Custody** — `POST /v1/pending` persists a withheld operation. `POST
/v1/decisions/{correlationId}` accepts approve or reject and executes from persisted context
on approval. `GET /v1/pending` is the queue for the application's approval surface.
`GET /v1/ledger` returns decisions, attempts and outcomes.

## 5. Non-functional

- Tier 1 and 2 classification: single-digit milliseconds at the enforcement point. Tier 3 and 4
  do not consume the routing budget, since nothing is routed.
- No classification service sits in the request path. Custody is the only new runtime
  component, and only Level 3 requires it.
- Ledger is append-only. No update or delete path exists in code.

## 6. Milestones

Sequenced against the adoption ladder in
[`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md). The original ten-day cut assumed
classification in the request path and is withdrawn.

## 7. Definition of done for v1

A `docker compose up` brings up a generator-configured gateway, custody and a mock backend.
A scripted demo drives an agent through a Tier 1 read, a Tier 2 write, a Tier 3 withhold
with out-of-band approval and resume, a Tier 4 refusal, and a decomposition sequence that
escalates on accumulated consequence — with the ledger showing every decision and which were
escalated.

## 8. Known limits

These are stated decisions, not discoveries to be made later.

- Accumulation escalation is one request late by construction ([ADR-006](adr/0006-accumulation-is-an-out-of-band-scope-floor.md)).
- Attempt recording is best-effort; if the log sink is down with custody, that window has no
  record ([ADR-005](adr/0005-custody-unavailable-fails-closed-and-the-refusal-is-recorded.md)).
- The constrained profile reintroduces scripting at the enforcement point
  ([ADR-003](adr/0003-authorisation-decisions-belong-at-the-authorisation-layer.md)).
- Conditional-flow-per-operation has a practical ceiling on bundle size. Measure it and state
  it; the alternative breaks the property the architecture rests on.
- The recommender must never be the authority, and its backend must be pluggable or
  regulated deployments cannot use it
  ([ADR-008](adr/0008-classification-is-recommended-never-decided.md)).
- With overlays optional, separated ownership is a mechanism most deployments will not
  exercise — it needs demonstrating deliberately
  ([ADR-001](adr/0001-consequence-declared-in-an-interface-description.md)).
