## ADR-0012 — Delegation is bounded by compiled client entitlement

**Status:** accepted as drafted · **supersedes ADR-003's delegation item only**

**Context.** ADR-003 moved delegation-chain integrity to the authorisation
layer on the assumption that the authorisation server would enforce
scope reduction against the subject token. Keycloak 26.3.3 does not
(13b). An exchanged token is bounded by the requesting client's
entitlement instead (13c). Exclusion and suspension already were
that same absence. Delegation is the third trigger.

ADR-003's exclusion and suspension items stand. This ADR corrects
only the delegation item.

**Decision.**

> An agent exchanges its token into a client that was compiled with a
> narrower entitlement. The excluded scope cannot be obtained because
> it was never granted to that client — not because an exchange was
> refused on lineage. Enforcement is the absence of the grant.
>
> This is the same mechanism as exclusion and suspension under a
> third trigger: a scope never granted, a scope removed, an identity
> never entitled.

**Consequences.**

- **Delegation is bounded to deploy-time identities.** No runtime
  minting of a sub-agent with an arbitrary narrower scope. Narrower
  than RFC 8693 and deliberately so.
- **The exchanged token carries no `act` and no parent reference.**
  Enforcement does not need one. The record would: a decision names
  the actor and the composition digest. The digest is taken over the
  qualified API description and does not cover the declared agent
  identities, so digest plus client id does not reconstruct the
  chain. That is a finding of 13e, not a decision to enlarge the
  digest here.
- **The authorisation server is now load-bearing for a correctness
  property**, where ADR-003 had assumed it would be load-bearing for
  a different one. The dependency did not go away, it moved.

A sub-agent identity declared under more than one parent is rejected
at generation. "B acting for A1" and "B acting for A2" are not the
same authority. The duplication is the more accurate model; the
ambiguity disappears by construction.

ADR-003 is left as written. The record of the correction is this file.
