## ADR-0011 — Accumulated consequence is a heuristic, not a boundary

**Status:** accepted as drafted · **supersedes ADR-006**

**Context.** ADR-006 said the enforcement point reads the scope floor locally
and fails closed if it cannot. Taken literally, an enforcement point with no
floor treats everything as Tier 4. That is a constant function. Task 12a
built the floor and found the property that is actually true.

ADR-006's other half stands: accumulation is an out-of-band scope floor,
read from gateway-local state, one request (plus one poll interval) late.
This ADR corrects only the unavailable-floor case.

**Decision.**

> An unavailable scope floor produces **no escalation**, not maximum
> escalation. Accumulation can only raise a tier above the floor already
> compiled into the configuration; when it is absent, that compiled floor
> governs — and it is what a human declared sufficient for this operation.
> Its absence permits nothing that was not already permitted.
>
> This is not fail-open. The additional protection against decomposition is
> absent; the declared protection is not.

**Consequences.** An adversary who can make custody unreachable — or who
can starve the poller so published floors expire — removes the
decomposition defence while leaving every declared tier intact. That is a
real reduction in protection and it is named rather than argued away. The
mitigation is that decomposition below the declared tiers was never
permitted in the first place: ten Tier 1 reads are still ten Tier 1 reads.
What is missing is the heuristic that would have raised the tenth.

Kong encodes this as a dictionary miss: no key, no shared dict, failed
poll. Logged; the request continues at the compiled floor. Dictionary TTL
is two poll intervals so a dead poller expires floors, which is again no
escalation.

ADR-006 is left as written. The record of the correction is this file.
