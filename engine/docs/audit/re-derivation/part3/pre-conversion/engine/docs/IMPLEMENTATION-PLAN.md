# ctier — implementation plan and Cursor task breakdown

Replaces the original ten-day plan, which assumed a policy service in the request
path. Sequenced against the adoption ladder rather than against components, so
each milestone demonstrates on its own.

**The fixed point:** WeAreDevelopers, Berlin, July 2027 — *"Beyond Scopes:
Enforcing Consequence at the API Gateway"* — commits to a live demo. That is the
real deadline.

---

## Done

| | |
|---|---|
| Specification | `open-gw/ctier`, CC BY 4.0, DOI 10.5281/zenodo.22020288 |
| Provisional | US 64/137,066, filed 19 Aug 2026 |
| Conference | APIdays India, Aug 2026 — delivered |
| Domain model + classifier | `ctier/models.py`, `ctier/classifier.py` |
| Conformance tests | 34 passing, organised by criterion |
| Task 01 | four classifier corrections, `x-ctier` rename, C3/C13/PRD updates, `DECISIONS.md` committed |
| Architecture | eight ADRs reviewed and decided, 5 Sept 2026 |

---

## The task sequence

Each task is independently green and independently reviewable. Tasks are written
one at a time, against the repo as it stands after the previous one lands — not
batched up front, because each one's shape depends on what the last one produced.

| Task | Milestone | Delivers | Depends on |
|---|---|---|---|
| **02** | — | Land the document set: ADRs split, PRD amended, solution design, plan | 01 |
| **03** | M1 | `ctier` core library + composer: inline and overlay declaration, composition digest, single-target validator | 02 |
| **04** | M1 | Recommender: structural rules, pluggable semantic backend, provenance records | 03 |
| **05** | M1 | Coverage report + CLI, warn/fail by level | 03, 04 |
| **06** | M2 | Apigee generator — bundle mode | 05 |
| **07** | M2 | Apigee generator — fragment mode, AS configuration | 06 |
| **08** | M2 | Conformance harness: fixture corpus, differential runner | 06 |
| **09** | M3 | Custody: context store, pending and decisions endpoints | 05 |
| **10** | M3 | Tier 3 end to end: 202 contract, execute-from-persisted-context, expiry | 09 |
| **11** | M3 | Three record types; custody-unavailable path | 09, 10 |
| **12** | M4 | Scope floor, out of band; tier migration proposals | 11 |
| **13** | M5 | Kong target + thin adapter plugin | 08 |
| **14** | M6 | `docker compose` demo, scripted walkthrough, v1.0.0 | all |

Tasks 03–05 are the wedge and stand alone: they produce Level 0 with nothing
deployed. If everything after them slipped, that alone would be worth having.

---

## M1 — Level 0: classify, with nothing deployed

*Tasks 03, 04, 05.*

The library, not the CLI, is the product — every surface is a thin shell over a
stable API (ADR-004), because the Spectral ruleset and the Backstage plugin come
later and cannot be retrofitted onto logic buried in a command.

- **Composer** — inline `x-ctier-*` as the default path; description plus N
  overlays as the alternative. Composition digest over all inputs. Single-target
  validator on overlay actions assigning Tiers 1–3.
- **Recommender** — structural signals first because they are reproducible;
  pluggable semantic backend, including local. Runs once at design time producing
  an artefact, never inside the build. Records input text and digest, rule or
  model version, confidence.
- **Coverage** — declared / recommended / absent, ordered by recommended tier.
  Warns at Level 1, fails from Level 2.
- RFC 9535 JSONPath dependency chosen deliberately — `jsonpath-ng` predates the
  RFC and is not compliant.

**Demonstrable:** run it over a real public OpenAPI document and show the
distribution. No gateway, no runtime, no deployment.

---

## M2 — Levels 1 and 2: compile and enforce, no new runtime

*Tasks 06, 07, 08.*

- Apigee target: header strip (closed set, C11), default Tier 4 before any
  conditional match, per-operation flow, fault rules per disposition.
- **Bundle mode first** — a complete deployable proxy, because that is what makes
  evaluation and the demo work. Fragment mode second, for an existing estate.
- Authorisation-server configuration for exclusion and suspension (ADR-003).
- Observe mode: classify and emit a decision record, enforce nothing.
- Conformance harness: the same fixture corpus against the compiled Apigee policy
  and the reference classifier, identical decisions required.

**Demonstrable:** Tiers 1, 2 and 4 enforced end to end against a real gateway
with no ctier runtime component deployed. This is the claim most people will not
believe until they see it.

**Measure here, under controlled conditions, recorded as measured — never
estimated:** classification latency at the enforcement point for Tier 1 and
Tier 2; duplicate-execution counts with and without the derived idempotency key
under ordinary agent retry behaviour.

---

## M3 — Level 3: custody and Tier 3

*Tasks 09, 10, 11.*

- Context store; `POST /v1/pending`, `POST /v1/decisions/{correlationId}`,
  `GET /v1/pending`.
- The `202 PendingAuthorization` contract — no `Retry-After`, `retryable: false`,
  `agentAction`, `userMessage`, authority class.
- Execute from persisted context on approval, byte-identical (C6).
- Expiry as a distinct disposition from rejection (C8).
- Custody-unavailable path: `503` retryable, agent not suspended, refusal
  recorded (ADR-005).
- Three record types — decisions, attempts, outcomes.

**Measure:** gateway connection and worker occupancy under withheld operations
versus a synchronous approval baseline; payload divergence when an agent re-plans
between refusal and resubmission.

---

## M4 — Level 4: accumulation and the cycle

*Task 12.*

- Scope floor maintained out of band by custody, read locally by the enforcement
  point (ADR-006).
- Tier migration proposals from ledger evidence — the edge that makes the three
  phases a cycle.
- Runtime escalation exercised against a live gateway rather than in unit tests.

---

## M5 — Second target, to prove the claim

*Task 13.* Kong, including the thin adapter plugin — chosen over APIM because it
tests the hard part: plugin-based, no native branching, and the conformance
fixtures are the only thing keeping it honest.

At this point gateway-agnosticism stops being a claim and becomes a passing test
suite. That matters more for the standards story than a third target would.

---

## M6 — Demo and release

*Task 14.*

- `docker compose up` — gateway, custody, mock backend.
- Scripted demo covering all four tiers, a decomposition sequence, and the ledger
  showing which decisions escalated and why.
- Kill custody on stage: the ledger keeps filling with attempt rows rather than
  going dark.
- Tag v1.0.0.

---

## Running alongside

**Measurements, as they arise.** Recorded as measured, under stated conditions,
in [`measurements.md`](measurements.md). An unsupported empirical figure is
worse than no figure.

**Clean-room discipline.** Independent work, personal machine, personal accounts,
personal time. A short dated build log in the repo.

---

## Sequencing

| When | What |
|---|---|
| Now | Task 02 lands the documents |
| Before the engine is forked | The licence question (DECISIONS.md Q5). No `LICENSE` file beats the wrong one — you can add, you cannot retract |
| July 2027 | Berlin. Live demo. Nothing new gets designed in this month |

---

## Deliberately not in this plan

APIM, APISIX and Envoy targets; MCP, AsyncAPI and GraphQL surfaces; the Spectral,
Backstage, Postman and Specmatic distribution surfaces; a reviewer UI; scoped
credential minting; a durable store beyond SQLite. All post-v1, all recorded in
the solution design so their absence is a decision rather than an omission.
