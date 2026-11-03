# Architecture decision records

An ADR is superseded by a later ADR, never edited in place.

| | Decision | Status |
|---|---|---|
| 001 | Consequence declared in an interface description, optionally composed | **accepted, amended** |
| 002 | Tier compiled to gateway-native configuration at deploy time | **accepted, amended** |
| 003 | Authorisation decisions belong at the authorisation layer | **accepted; delegation item superseded by 012** |
| 004 | Two components, thin adapters, and distribution into existing tooling | **accepted, amended** |
| 005 | Custody unavailable fails closed, and the refusal is recorded | accepted |
| 006 | Accumulation is an out-of-band scope floor | **superseded by 011** |
| 007 | Routing to a human is the consuming application's concern | accepted |
| 008 | Classification is recommended, never decided | accepted |
| 009 | The contract is the documents, not the code | **proposed** |
| 011 | Accumulated consequence is a heuristic, not a boundary | accepted |
| 012 | Delegation is bounded by compiled client entitlement | accepted |
