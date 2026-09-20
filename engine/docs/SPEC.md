# Specification this engine was built against

Base: specification **1.15.0**. Citations of criteria, dispositions,
deployment levels, and record types that existed in that release
resolve there. The claim is the clause list below, not that version
number, and not any later release as a whole.

The table names the identifier and what this engine does. It does
not state what a criterion requires. The clause list is a
snapshot relative to specification **1.25.0**. It is
stale when a new criterion is minted, a record type this engine
emits gains a version, or a clause this table lists as not met
is implemented.

## Criteria this engine implements

| | This engine |
|---|---|
| C1 | Classifies at generate time; compiles the assignment into the enforcement configuration |
| C2 | Emits the undeclared default (tier 4) for an operation in the composition with no declaration; a path outside the composition is refused undetermined |
| C3 | Resolves `x-ctier-escalate-to` to an integer that does not fall below the tier entering that stage |
| C4 | Classify, withhold, refuse, and escalate do not wait for a human |
| C5 | Withhold is `202`, no `Retry-After`, `retryable: false`, `agentAction: continue_task_without_this_step` |
| C6 | Custody persists at withhold and executes those bytes; the agent is not the execute client |
| C7 | Satisfies the duplicate-execution property by deriving a key at classify, storing it, and emitting it on execute; Level 2 strips inbound keys and emits none |
| C8 | `decide(reject)` pauses the operation class; expiry refuses the one operation. That pause is not agent suspension at the authorisation server. |
| C9 | Tier 4 is `423` / `halt_and_hand_off`; no later execute under the agent's identity |
| C10 | The decision precedes the act (compile-time assignment or access-phase evaluation). Writes sequenced `[ctier-decision]` / `[ctier-attempt]` at NOTICE on the gateway error log (the claimed sink). The record is evidence and MAY be async; ledger POST fails open and is not claimed. `epoch=` and `seq=` sit on the line, outside the JSON. `error_log ... warn` drops them. A custody-unavailable refuse is an Attempt, `appliedTier` undetermined. The absence-detectable sink clause as later releases stated it is this engine's conduct on that sink. |
| C11 | Bundle mode strips inbound `x-ctier-*` before setting its own; classification does not read an inbound tier |
| C12 | Assignment travels in the generated configuration; `governed-set` is on the artefact; a composed miss is refused undetermined |
| C13 | Emits `compositionDigest` and `deploymentDigest` on the artefact and on decision records. Generate refuses when `existing` carries an assignment from another composition |
| C16 | Prefix-strips the `x-ctier-*` namespace on ingress (Kong, APISIX, Apigee JS). Runtime suite `namespace-unlisted` and `namespace-unknown-audit` require the unknown name absent at the observer. |

## Record types this engine emits

| Type | Version | This engine |
|---|---|---|
| Decision | `decision-record/0.2.0` | `declaredTier` present when a declaration was made |
| Attempt | `attempt-record/0.3.0` | `declaredTier` present when a declaration was made; omitted when none was. Do not write 4 to mean unknown. |
| Outcome | `outcome-record/0.1.0` | What executed after approval |

## The governed set

`governed-set` is **met.** One artefact, two serialisations:
`governed-set` on the Kong global instance and on
`ctier-generate.json`. The identifier names the same list.

## Named requirements this engine does not meet

These are not oversights. They are scope this engine has not taken on.

| | Standing |
|---|---|
| C14 | **Not implemented.** |
| C15 | **Partial.** Enforcement-point half: this engine does not consult the policy service to ask whether an agent is suspended, and does not keep a gateway denylist of suspended agents. Authorisation-server half: compiled-absence — the scope removed at the authorisation server — is the estate. This engine does not implement that half. Rounding either way would be a false statement about a security property. |
| Requirement 6 | **The operator's, not this engine's.** Records that leave the sink must take the sink's sequencing with them. |

## What the C13 witness establishes

The live cases generate against one composition and present
another with the same operations. Generate refuses on Kong
and on APISIX, fragment and bundle. They show that mismatch
caught. They do not show every mismatch. They say nothing
about a composition that changes after generation.

## What the C4 witnesses establish

C4 is a negative property. The suite cannot verify it. It can
falsify it. It can witness consequences that would be present
if C4 were violated. Taxonomy 33: Observed witnesses of a
property that cannot be exhaustively observed. Three witnesses
on Kong and on APISIX. They do not establish C4.

## What a Tier 4 handover carries

C9 is no resume under the agent's identity. Tier 4 is the
handover. The named `423` mechanism lists `incidentId`.
`X-Incident-Id` MAY be emitted; 48 gave it a stated trust
status. It is not the join key. C9 forbids a correlation
identifier on this disposition.

What actually correlates a handover today:

| Engine | On the wire | What correlates |
|---|---|---|
| Kong | `423`, body `agent_suspended` / `autoResume: false` / `agentAction: halt_and_hand_off`, and `X-Agent-Action`. No `incidentId`. No `X-Incident-Id`. No `correlationId`. | A decision record (`refuse-and-suspend`) whose `correlationId` the client never sees. |
| APISIX compiled T4 | `423`, the same body, and `X-Agent-Action`. | A decision record (`refuse-and-suspend`) on the gateway-log sink. No ledger POST. |
| APISIX C2 T4 | `423`, the same body, and `X-Agent-Action`. | Nothing on a record the client can see. |

C9 does not need `incidentId` on the wire. The property is
that nothing names a resume handle. An incident label is not
that handle. A named header with trust status implies it
travels; it does not. MAY is not MUST. This engine does not
emit it. The 423 goes out, and the only link — where one
exists — is in a record the client never sees.

## What this tree does not claim

This tree does not claim any later release as a whole. A version
scalar cannot name a partial implementation.
