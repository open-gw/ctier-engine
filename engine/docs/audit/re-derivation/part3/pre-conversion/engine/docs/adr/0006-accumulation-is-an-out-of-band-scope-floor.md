## ADR-006 — Accumulation is an out-of-band scope floor

**Status:** superseded by [ADR-0011](0011-accumulated-consequence-is-a-heuristic-not-a-boundary.md)

**Context.** Accumulated consequence across a correlation scope needs weighted,
decaying, shared mutable state. It is the one classification stage that cannot be
a pure function, and the substrates differ genuinely across gateways with
different consistency properties. That is divergent *behaviour*, not divergent
syntax, and no amount of compilation fixes it.

**Decision.** Custody maintains a per-scope floor out of band, watching decision
records. The enforcement point reads that floor locally, alongside the
operation's compile-time floor, and fails closed if it cannot.

**Consequences.** Two floors, both read locally, neither requiring a hop. The
request that crosses the threshold executes at the lower tier; only subsequent
ones are governed. For a heuristic detecting a *sequence* that is an acceptable
and bounded loss — but it is stated in the PRD, not left to be discovered.
