## ADR-001 — Consequence is declared in an interface description, optionally composed

**Status:** accepted with amendment · supersedes the inline-only assumption in
`docs/PRD.md`

**Context.** Tiers were to be declared inline in the OpenAPI document. In an
organisation where the interface is owned by the API team and the consequence
judgement by governance and risk, inline declaration forces the governance
decision through the API team's pull request, reviewed by people whose job it is
not. But that separation is a property of large organisations, not of the model.

**Decision, as amended.** Two declaration modes, both first-class and both
documented:

- **Inline.** `x-ctier-*` in the OpenAPI document. One artefact, one review, one
  team. This is the default and the fast path.
- **Composed.** A description plus N governance overlays (Overlay 1.1.0, RFC 9535
  JSONPath), applied in order, with tiers read from the composition. For
  organisations where governance and interface ownership genuinely differ.

The generator accepts both; a team chooses by its own shape, not by ours.

The single-target rule applies to overlays only: an overlay action whose `update`
assigns Tier 1, 2 or 3 MUST select exactly one operation, and MAY select many
only when assigning Tier 4. Inline declaration is per-operation by construction,
so the rule is vacuous there and no conflict arises.

> **As amended by RD:** *"Teams can use overlays as optional, or ctier can be
> defined directly in the OpenAPI spec, allowing leaner teams to move fast."*
> The original drafted composition as the architecture and inline as its
> degenerate case. That inverted the common path.

**Consequences.** The composition digest (C13) covers both modes — inline is
simply one input artefact rather than several. Documentation, examples and the
reference spec must show the inline path first, because it is what most adopters
will use.

Worth stating honestly: with overlays optional, the separated-ownership mechanism
becomes a feature most deployments will not exercise. It will not be proven in
the field as quickly as the rest, and the demo should show it deliberately
rather than incidentally.
