# ctier — solution design

Supersedes `docs/ARCHITECTURE.md`. Reads with `docs/adr/` for why each choice was
made and `docs/DECISIONS.md` for what is still open.

**Naming.** *AGA* — Autonomous Governance Architecture — is the framework.
*ctier* is the specification and the implementation of it. Public writing uses
AGA for the idea and ctier for the artefact.

---

## 1. The problem

Identity-based authorisation describes the **caller**. OAuth scopes, RBAC, rate
limits and audit logs all answer *who is asking*. None answers *what this will
do*. An agent can be fully authenticated, entirely within scope, and still
perform something irreversible.

This matters now because the caller is increasingly not a person operating an
application but an autonomous agent composing operations toward a goal. Scopes
are coarser than operations, and an agent's mode — observe, recommend, act — is a
property of the agent, while risk is a property of the action.

MCP's authorization specification is OAuth-based, which is the same gap on the
surface agents actually use today.

---

## 2. The model

**Five criteria**, evaluated by a human at design time: reversibility, blast
radius, data sensitivity, compliance trigger, idempotency.

**Reversibility has three states, not two**, and it is the axis the tiers are
defined on:

| State | Meaning |
|---|---|
| `undo-restores-effect` | nothing persists from the interval the operation stood |
| `undo-restores-record-only` | the record reverts; actions others took in that interval cannot be recalled — a price can be put back, the orders placed at the wrong price were still placed |
| `none` | no reversal exists |

The other four criteria are **escalators** on that axis, not peers of it. This is
why blast radius outranks data sensitivity: a population-scale *write* collapses
reversibility to `record-only` by construction, because the population affected
while the state stood is unbounded. It is a derivation, not a precedence
preference.

A population-scale *read* is separate. Reversibility does not describe
disclosure — you cannot un-disclose — so scale carries consequence for reads too,
but as a delay rather than a handover.

**Four tiers.**

| Tier | Character | Enforcement | The human's role |
|---|---|---|---|
| 1 | read-only, no compliance surface | log; logging does not gate | none |
| 2 | undo restores the effect | audit trail, before/after state, compensating action verified to exist | decides whether it *stands*, not whether it happens |
| 3 | undo restores the record only | withhold, persist, approve out of band, execute from persisted context | authorises, out of band |
| 4 | no undo exists | refuse, suspend the agent for that operation class, no auto-resume | performs it personally, under their own credential |

**Tier 3 is a delay. Tier 4 is a handover.** In Tier 3 the operation eventually
executes with a named approver against it. In Tier 4 the agent never executes it.
Tier 4 exists because approving an agent's payload launders the decision rather
than checking it, and because attribution matters — *"the clinician ordered it"*
is a stronger record than *"the agent ordered it and a clinician approved."*

**Exclusion is not a tier.** It is an authorisation decision — the scope is never
granted, refused at token validation, before any tier is considered. Both exist
because scopes are coarser than operations.

---

## 3. Three phases, which form a cycle

### Design

Two declaration modes, both first-class (ADR-001):

- **Inline** — `x-ctier-*` in the OpenAPI document. One artefact, one review, one
  team. The default and the fast path.
- **Composed** — a description plus N governance overlays (Overlay 1.1.0, RFC
  9535 JSONPath) applied in order, for organisations where governance and
  interface ownership genuinely differ.

A recommender proposes tiers; a human confirms the ones that carry consequence
(ADR-008). Classification has three states: **declared**, **recommended**,
**absent** — and absent is compiled as the undeclared default (tier 4).

Output: the qualified spec, a per-operation rationale, and a review queue ordered
by recommended tier.

### Build

The generator compiles each operation into the enforcement point's native
configuration (ADR-002), in either of two output modes:

- **Bundle** — a complete, deployable proxy. For evaluation, greenfield, and the
  demo, where the thing should simply run.
- **Fragments** — policies and flow entries to merge into an existing proxy, for
  an estate that already has templates and a promotion pipeline.

Neither is the canonical mode. It also emits authorisation-server configuration
(ADR-003), a composition manifest with digests (C13), and the conformance
fixtures proving the compiled target decides identically to the reference
classifier.

The coverage report **warns** at Level 1 and **fails the build** from Level 2
upward. A gate that blocks a pipeline before anything is being enforced is
friction with no safety value.

### Run

The enforcement point resolves the declared floor, compares request content
against declared bounds, reads the scope floor, and selects a disposition.
Custody holds withheld operations and executes them on approval. The consuming
application routes humans (ADR-007).

### The cycle

Run feeds Design. A Tier 3 approved every time for six months was misclassified —
it is a Tier 2. A Tier 2 repeatedly escalated by bounds is under-classified.
Without that edge every classification is a one-time guess nobody revisits.

---

## 4. Components

| Component | Where it runs | Contains |
|---|---|---|
| **`ctier`** | CI and design time | recommender, composer, coverage report, generator, reference classifier as conformance oracle |
| **Custody** | one service, off the request path | pending Tier 3 context, ledger, scope floor, approval endpoint |
| **Adapter** | Kong and APISIX only | thin data-driven plugin reading compiled config |

Everything else is already in the estate: the gateway, the authorisation server,
CI, the observability stack. ctier adds no system of record and replaces no tool.

**`ctier` is a library first.** Every surface — the CLI included — is a thin
shell over a stable programmatic API (ADR-004). Logic that ends up inside the CLI
cannot later be embedded in a Spectral ruleset or a Backstage plugin without
being rewritten, so this is a constraint from the first commit rather than a
refactor.

---

## 5. Resolve, then escalate

The enforcement point supplies the declared tier as a **floor**. Adjustment is
unidirectional — it may only raise.

1. **Delegation-chain integrity** — enforced at token exchange (ADR-003), so an
   expanded chain never reaches the enforcement point with a valid credential.
2. **Request content exceeding declared bounds** — a declared tier assumes a
   bounded request; this checks the assumption.
3. **Accumulated consequence across the correlation scope** — read as a scope
   floor maintained out of band (ADR-006).

---

## 6. Interfaces

**Design-time extensions**, under the registered `ctier` namespace:
`x-ctier-tier`, `x-ctier-criteria`, `x-ctier-exclude`, `x-ctier-defaults`,
`x-ctier-handoff`.

**Custody**

- `POST /v1/pending` — persist a withheld operation, returning its correlation id
- `POST /v1/decisions/{correlationId}` — approve or reject; executes from
  persisted context on approval
- `GET /v1/pending` — the queue, for the application's approval surface
- `GET /v1/ledger` — decisions, attempts and outcomes

**Agent-facing responses**

| Case | Status | Retryable | Agent state |
|---|---|---|---|
| Tier 1 · 2 | as the backend returns | — | working |
| Tier 3 | `202 PendingAuthorization` — no `Retry-After`, `retryable: false`, `agentAction`, `userMessage`, authority class | no, terminal | working |
| Tier 4 | `423 AgentSuspended` | no, terminal | suspended, no resume |
| Custody unavailable | `503` with `Retry-After` | **yes** | working |

The last row is the one place a retryable refusal is correct, for the same reason
the withheld response is not: the response should tell the agent what is true. A
withhold will never succeed on retry; an outage will.

**Two obligations on the consuming application** (ADR-007), and everything else
about routing is the developer's choice:

1. On `423`, the operation must never subsequently execute under the agent's or
   the application's credential.
2. On `202`, the application posts the decision to custody rather than re-calling
   the API.

---

## 7. Conformance criteria

Criteria C1–C13 are in the specification this engine implements
([`SPEC.md`](SPEC.md)). The table names the identifier and what this
engine does. It does not state what a criterion requires.

| | This engine |
|---|---|
| C1 | Classifies at generate time; compiles the assignment into the enforcement configuration |
| C2 | Emits the undeclared default (tier 4) for an operation in the composition with no declaration; a path outside the composition is refused undetermined |
| C3 | Resolves `x-ctier-escalate-to` to an integer that does not fall below the tier entering that stage |
| C4 | Classify, withhold, refuse, and escalate do not wait for a human |
| C5 | Withhold is `202`, no `Retry-After`, `retryable: false`, `agentAction: continue_task_without_this_step` |
| C6 | Custody persists at withhold and executes those bytes; the agent is not the execute client |
| C7 | Satisfies the duplicate-execution property by deriving a key at classify, storing it, and emitting it on execute; Level 2 strips inbound keys and emits none |
| C8 | `decide(reject)` pauses the operation class; expiry refuses the one operation |
| C9 | Tier 4 is `423` / `halt_and_hand_off`; no later execute under the agent's identity |
| C10 | The decision precedes the act; writes `[ctier-decision]` / `[ctier-attempt]` at NOTICE on the gateway error log (the claimed sink); the record is evidence and MAY be async; `error_log ... warn` drops them; ledger POST fails open and is not claimed; a custody-unavailable refuse is an Attempt, `appliedTier` undetermined |
| C11 | Bundle mode strips inbound `x-ctier-*` before setting its own; classification does not read an inbound tier |
| C12 | Assignment travels in the generated configuration; `governed-set` is on the artefact; a composed miss is refused undetermined |
| C13 | Emits `compositionDigest` and `deploymentDigest` on the artefact and on decision records. Generate refuses when `existing` carries an assignment from another composition |

---

## 8. Trust boundary

C11. Generated bundles strip inbound `x-ctier-*` before setting this
engine's own headers. Classification does not read an inbound tier.

Apigee's `AssignMessage` removes headers **by exact name** — no documented
wildcard or prefix form. So the generator enumerates a closed set. This
engine's enforcement point and custody ignore an `x-ctier-*` header they
do not know. That ignore survives a gateway misconfiguration; header
removal alone does not.

---

## 9. Deployment profiles

**Standard.** An authorisation server performing token exchange with scope
reduction, enforcing exclusion, suspension and delegation integrity. No scripting
at the enforcement point on Apigee, APIM or Envoy.

**Constrained.** No such authorisation server. The enforcement point checks the
delegation chain itself, which requires a scripted policy, and suspension is
consulted from custody. Slower, more coupled, and conformant.

This engine implements `standard`. It does not implement `constrained`.

**Adoption ladder.** Levels 0–4 are in the specification this engine
implements ([`SPEC.md`](SPEC.md)). What this engine deploys:

| Level | This engine |
|---|---|
| 0 · Classify | Coverage report and review queue; nothing compiled into a gateway |
| 1 · Observe | Proxy config that classifies and emits a decision record; coverage warns |
| 2 · Enforce 1/2/4 | Proxy config and AS flags; no custody; coverage fails the build |
| 3 · Withhold | Custody; persist, approve, execute |
| 4 · Accumulate | Scope floor on Kong and APISIX |

Level 4 is encoded on Kong and APISIX as an out-of-band poller plus a
local dictionary read. Apigee is artefact-only for this rung. The
remaining live-target difference is how the timer starts (plugin
`access` vs lazy `serverless-post-function`) and where the dict is
declared (Kong compose vs APISIX `config.yaml`), not whether
accumulation exists.

---

## 10. Targets

Apigee is the reference target. A second target follows to prove the portability
claim. Everything beyond is **demand-driven** — added when adoption asks, not
committed up front (ADR-002).

| Target | Idiom | Emitted | Adapter |
|---|---|---|---|
| Apigee | policy pipeline | AssignMessage policies + conditional flows | no |
| Azure APIM | policy expressions | inbound policy fragments | no |
| Kong | plugins per route | decK config entries | yes (Lua) |
| APISIX | plugins per route | route plugin config | yes (Lua) |
| Envoy / Istio | `ext_authz` | filter config pointing at custody | no |

Gateway-agnosticism means one definition, one conformance suite and compiled
targets — not one runtime artefact. The reference classifier is the oracle; every
target runs the same fixture corpus and must decide identically.

---

## 11. Distribution surfaces

ctier is embedded into tooling teams already run rather than asking them to adopt
another tool (ADR-004). Post-v1 and demand-driven, but the library-first
constraint in §4 exists to keep them cheap.

| Surface | Why |
|---|---|
| Spectral ruleset | Already in most enterprise OpenAPI pipelines — coverage checking runs inside linting they do today. Cheapest adoption path available |
| Backstage plugin | Where enterprise API catalogues live; tier coverage per API is the executive view of Level 0 |
| Postman | Classify a collection where API teams already work |
| Specmatic | Contract testing from OpenAPI; the conformance fixtures fit its harness |
| Bruno, VS Code | Developer-local, lower reach |

---

## 12. Observability

This engine emits three record types (`decision-record/0.2.0`,
`attempt-record/0.3.0`, `outcome-record/0.1.0`). C8 is in the
specification this engine implements.

- **Decisions** — this engine writes declared tier, applied tier,
  escalation reason, deployment digest.
- **Attempts** — this engine writes a refuse without classification,
  `appliedTier` undetermined.
- **Outcomes** — this engine writes what executed after approval.

There is no tracing integration in this implementation. Decision evidence
at Levels 1 and 2 is a schema-valid log line on the gateway. Custody, when
deployed, remains the durable ledger.

---

## 13. Out of scope

A reviewer UI, in v1 or after — the consuming application is the approval
surface. Any notification, workflow or paging mechanism. Org-structure modelling
beyond the declared authority class. Scoped credential minting (post-v1). A
durable store beyond SQLite for custody (post-v1).

---

## 14. Known limits, stated rather than discovered

- Accumulation escalation is one request late by construction (ADR-006).
- Attempt recording is best-effort; if the log sink is down with custody, that
  window has no record (ADR-005).
- The constrained profile reintroduces scripting at the enforcement point
  (ADR-003).
- Conditional-flow-per-operation has a practical ceiling on bundle size. Measure
  it and state it; the alternative breaks the property the architecture rests on.
- The recommender must never be the authority, and its backend must be pluggable
  or regulated deployments cannot use it (ADR-008).
- With overlays optional, separated ownership is a mechanism most deployments
  will not exercise — it needs demonstrating deliberately (ADR-001).
