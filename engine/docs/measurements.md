# Measurements

Every figure this project states, classified as exactly one of:

| Kind | Meaning | Reproducible by |
|---|---|---|
| **Configured** | a value someone chose | reading the configuration |
| **Derived** | follows arithmetically from configured values | the same arithmetic |
| **Observed** | a sample from a run | re-running under the same conditions, approximately |
| **Observed witnesses of a property that cannot be exhaustively observed** | a run that can falsify a negative property, or witness a consequence that would be present if it were violated | the same cases; they do not verify the property |

Configured and Derived are environment-independent. Observed is not.
That distinction is the point of this file. Most of the claims that
matter are Configured or Derived: they do not depend on the machine.

An Observed figure never stands in for a bound.

Mechanisms stay in findings and ADRs. This file is the register of
numbers. Quote from here; do not restate an Observed sample as if it
were typical or as if it were the bound.

---

## Configured

| What | Value | Where it is chosen |
|---|---|---|
| Custody hop timeout | **200 ms** | `DEFAULT_CUSTODY_TIMEOUT_MS`; Kong `custody_timeout_ms`; APISIX Lua `set_timeout` |
| Floor poll interval | **1000 ms** | `DEFAULT_FLOOR_POLL_MS`; Kong `floor_poll_ms`; APISIX compiled into the poller Lua. **Kong and APISIX use the same value.** |
| Access-token lifetime | **30 s** | `ACCESS_TOKEN_LIFESPAN` → realm `accessTokenLifespan` |
| Kong plugin `PRIORITY` | **10000** | `targets/kong/plugin/handler.lua`. Raised from 800 in 16c so the strip runs before cors/jwt/request-transformer. 800 is history, not a second current value. |
| APISIX strip `_meta.priority` | **21000** | `generate._APISIX_PRI_STRIP` |
| Shared-dict size | **1m** | Kong compose `KONG_NGINX_HTTP_LUA_SHARED_DICT`; APISIX `lua_shared_dict ctier_floors 1m` |
| Live Kong workers | **1** | `KONG_NGINX_WORKER_PROCESSES` in `targets/kong/live/compose.yaml`. Not production-shaped. |
| Live APISIX workers | **1** | `nginx_config.worker_processes` in `targets/apisix/live/config.yaml`. Not production-shaped. |
| Accumulation threshold | **9** | `GovernanceConfig.escalate_above` |
| T1 weight | **1** | `TIER_WEIGHT[LOW]` |
| Decay window (production default) | **1800 s** | `GovernanceConfig.decay_seconds` |
| Decay window (live compose) | **5 s** | `CTIER_DECAY_SECONDS` on both Kong and APISIX custody. A fixture so a gap is testable, not a production recommendation. |
| Pending review period | **86400 s** | `DEFAULT_REVIEW_PERIOD_SECONDS` |
| Custody-unavailable `Retry-After` | **5 s** | generated Lua / Kong plugin on 503 |
| Apigee JavaScript `timeLimit` | **200 ms** | AssignMessage JS policies. **Not** the custody hop timeout; same numeral, different setting. |
| Migration raise min sample | **10** | `MigrationConfig.raise_min_sample` |
| Migration lower min sample | **50** | `MigrationConfig.lower_min_sample` |
| Migration raise window | **14 days** (1209600 s) | `MigrationConfig.raise_window_seconds` |
| Migration lower window | **90 days** | `MigrationConfig.lower_window_seconds` |

---

## Derived

| What | Value | From |
|---|---|---|
| Accumulation visibility **bound** | threshold-crossing **plus one poll interval (1000 ms)** | configured `floor_poll_ms`. Same bound on Kong and APISIX because the intervals match. |
| Dictionary TTL | **two poll intervals (2000 ms)** | `2 × floor_poll_ms`. A dead poller expires floors, which is no escalation. |
| T1 requests to cross the threshold | **10** | `escalate_above // T1_weight + 1` |
| Published floor | **2** | `escalate(Tier.LOW)` — T1 decomposition becomes T2 |
| Suspension delay | remaining lifetime of an already-issued token | configured token lifetime. In this rig the bound is **30 s**. An hour-long token is an hour-long window. |

The spec's evidence section (`spec/conformance.md`) quotes the
visibility bound as “the measured window” with `(1000 ms)` inline.
That figure is **Derived**, not Observed. Filed for the spec author.

---

## Observed

Every Observed row states hardware, architecture, container runtime,
concurrency, sample count, and date.

| What | Value | Conditions | Source |
|---|---|---|---|
| Escalation visible after crossing (APISIX) | **216 ms** | **Observed.** Single sample; APISIX 3.13.0 standalone; 1000 ms poll interval; Apple M3 Pro (arm64); Docker; concurrency 1 (sequential live client); 18 September 2026. **The bound is one poll interval**; this sample says the mechanism works, not how fast it is. A later run at 900 ms would still be inside the bound. | [`findings/32.md`](findings/32.md) |

Kong's accumulation (12a) recorded the Derived bound and did not
take an Observed visibility sample. There is no Kong counterpart to
the 216 ms row, and inventing one from the bound would be the error
this file exists to prevent.

`induced-gap-is-detected` (50) passed on both engines. That result
is **Observed under a configuration that is not production-shaped**:
the live rig pins one worker. A production node interleaves
emitters. The mechanism groups by epoch; that interleave has not
been run. It is not a plain Observed. See
[`findings/50a.md`](findings/50a.md).

C4 witnesses (54) are **Observed witnesses of a property that cannot
be exhaustively observed.** Taxonomy 33. The suite cannot verify C4.
It can falsify it. It can witness consequences that would be present
if C4 were violated. Three cases on both live engines: a withhold
has no `pollUrl`; Level 2 Tier 3 is an immediate
`provisioning_defect` decision, not a wait; Tier 4 `423` completes
with nothing holding for an approver. Passing those cases does not
establish C4.

C13 (55) is **Observed.** Four cells on Kong and APISIX, fragment
and bundle: generate against one composition, present another with
the same operations, generate refuses. Passing shows that mismatch
caught. It does not show every mismatch. It says nothing about a
composition that changes after generation.

---

## Outstanding (not measured)

Both need a controlled rig. A development laptop cannot produce an
honest Observed number for either. They are named here rather than
filled in.

| What | Why it is absent |
|---|---|
| Classification latency at the enforcement point (Tier 1 / Tier 2) | Plan M2. Needs a load generation setup and a quiet path; this laptop's Docker compose is not that rig. |
| Connection and worker occupancy under withheld operations versus a synchronous approval baseline | Plan M3. Needs a concurrency harness and occupancy metrics the live suite does not collect. |

Duplicate-execution counts under agent retry (also M2) remain unmeasured
for the same reason; C7 at Level 2 is declined in the spec, so that
figure is not a ladder claim.

---

## What this file is not

Pytest pass counts, corpus 24/24 agreement, and Keycloak 26.3.3 are
run records and pin versions. They live in findings and
`spec/conformance.md`. They are not timings or bounds.

The live decay of 5 s is Configured (a fixture). Findings that quote
it must not be read as production decay.
