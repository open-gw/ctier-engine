## ADR-003 — Authorisation decisions belong at the authorisation layer

**Status:** accepted as drafted

**Context.** Three things kept dragging shared mutable state and scripting into
the request path: exclusion, agent suspension, and delegation-chain integrity.
Each requires either a stateful lookup on every request, or a scripted policy
parsing a structure no gateway parses natively.

**Decision.** All three move to the authorisation layer, where the model already
places exclusion.

| | Enforced by | Was |
|---|---|---|
| Exclusion | scope never granted | already the position |
| Suspension | credential flagged | custody lookup per request |
| Delegation expansion | token exchange refused at the AS | scripted policy at the gateway |

**Consequences.** What remains at the enforcement point is: resolve the floor,
compare a number, read a floor, pick a disposition. All native, everywhere.

The cost is an adoption dependency that will otherwise be discovered late — this
puts the IAM team on the critical path for an API governance rollout. It also
assumes an authorisation server performing token exchange with scope reduction.
Where none exists, the enforcement point must check the chain itself and a
scripted policy returns. That is a stated **deployment profile**, not a footnote.
