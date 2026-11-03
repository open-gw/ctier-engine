## ADR-007 — Routing to a human is the consuming application's concern

**Status:** accepted as drafted · resolves DECISIONS.md Q7

**Context.** Tier 3 needs an approver; Tier 4 needs someone to perform the
operation. Declaring the *person* in the interface description would put ctier in
the business of org charts, on-call rotas and notification channels.

**Decision.** ctier's obligation ends at the response. It emits a terminal
response carrying a correlation id, a reason, an `agentAction` directive and an
**authority class** (`account-holder`, `clinician`, `operator`, `risk-approver`)
— the class declared at design time, the person resolved by the application at
runtime. What the application then does is the developer's choice: terminate,
queue, page a channel, open a ticket.

Two obligations survive, because without them the model collapses:

1. On `423`, the operation MUST never subsequently execute under the agent's or
   the application's credential.
2. On `202`, the application posts the decision to custody rather than re-calling
   the API — otherwise double execution or payload divergence (C6).

**Consequences.** `202` and `423` route different things: an *approval*, which
custody then executes, versus a *task*, which a human performs. An application
treating them alike has turned Tier 4 into Tier 3 with extra steps — the test
remains whose credential the executed request carries, not who clicked. The
ledger detects the breach: a Tier 4 operation later executing with an agent
delegation chain means C9 failed.

ctier ships no reviewer UI, in v1 or after. The application is the approval
surface.
