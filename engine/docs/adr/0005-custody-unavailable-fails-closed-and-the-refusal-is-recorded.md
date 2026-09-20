## ADR-005 — Custody unavailable fails closed, and the refusal is recorded

**Status:** accepted as drafted · amends **C10**

**Context.** With custody off the request path, the only synchronous dependency
is the Tier 3 persist — you cannot return `202 PendingAuthorization` having
failed to persist the thing you claim is pending.

**Decision.** Fail closed: nothing executes without a decision. But fail closed to
Tier 4's *refusal*, not Tier 4's *disposition* — `503`, retryable with
`Retry-After`, agent **not** suspended.

The reasoning is C8's, one level up. Rejection is evidence about the agent and
pauses it; expiry is evidence about reviewer availability and refuses only the
operation. An outage is evidence about the infrastructure. Applying Tier 4
literally would suspend every agent that touched the gateway during a five-second
restart, with no resume path by C9 — a worse outage than the one that caused it.

The enforcement point records the refusal itself, carrying the operation, the
declared tier (which it already holds), the composition digest and the reason,
marking the applied tier undetermined.

**C10 restated rather than carved out:**

> Decisions are recorded before they are acted on, including declared tier,
> applied tier and escalation reason. Where the policy service is unavailable and
> the enforcement point refuses without classifying, the refusal MUST itself be
> recorded, carrying the declared tier, the composition digest and the reason,
> and marking the applied tier as undetermined. **A refusal to decide is a
> decision.**

**Consequences.** A carve-out would have made C10 untestable — a second
implementation could satisfy it by recording nothing and asserting the service was
always down. Attempt records are a distinct type, not `Decision` objects with
nulls, and they are **not** replayed into accumulation: a refused operation caused
no consequence, and feeding attempts in would conflate "tried" with "did".
Best-effort by nature — if the log sink is also down, that window has no record,
and the PRD says so rather than implying a guarantee.
