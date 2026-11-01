# Part 2 — twenty-two extra identifiers (217 vs 195)

Net **+22** is asymmetric, not a clean list of twenty-two
additions:

- Script-only (in script, not in finding 43): **62**
- Finding-43-only (in finding 43, not in script): **40**
- Net: 62 − 40 = **22**

Pairing uses normalised spelling plus explicit maps for
qualified finding-43 rows (`Authorization` (custody), ledger
`agentId`, input-role `description`/`overlay`, escalation
`none`, extension `x-ctier-tier`).

## Verdict

The surplus is **rule artefacts** (HTTP methods, camelCase
dimension twins, bare `$defs` keys, vocab field stems, ADR
and validation headings, generic schema tokens). It is not a
list of twenty-two real identifiers the hand pass missed.
The hand pass also carries 40 identifiers the script never
minted (concepts, extension subfields, header aliases, status
codes, `Requirement 1`, old record versions, …); those offset
the artefact pile down to net +22.

## Script-only — one line each

- `1.1.0` — Rule artefact — overlay/version const fragment.
- `4.1 Rules become data, not code` — Rule artefact — ADR-0009 / validation.md heading harvested as an identifier.
- `4.2 Recommendations are an overlay` — Rule artefact — ADR-0009 / validation.md heading harvested as an identifier.
- `4.3 The schemas live in the specification repository, not the engine` — Rule artefact — ADR-0009 / validation.md heading harvested as an identifier.
- `C13 — Digest discipline` — Rule artefact — full heading string; finding 43 inventoried the letter separately.
- `C2 — Fail-closed` — Rule artefact — full heading string; finding 43 inventoried the letter separately.
- `C3 — Unidirectionality` — Rule artefact — full heading string; finding 43 inventoried the letter separately.
- `Criteria` — Rule artefact — ADR-0009 / validation.md heading harvested as an identifier.
- `Ledger records` — Rule artefact — ADR-0009 / validation.md heading harvested as an identifier.
- `On the maturity of these criteria` — Rule artefact — ADR-0009 / validation.md heading harvested as an identifier.
- `The transformations, as document-in / document-out` — Rule artefact — ADR-0009 / validation.md heading harvested as an identifier.
- `accountId` — Rule artefact — example/schema property token, not a finding-43 vocabulary row.
- `action` — Rule artefact — script-only token; not in finding 43's 195.
- `agent` — Rule artefact — script-only token; not in finding 43's 195.
- `artefact` — Rule artefact — script-only token; not in finding 43's 195.
- `authorizationId` — Rule artefact — example/schema property token, not a finding-43 vocabulary row.
- `blastRadius` — Rule artefact — camelCase schema twin of a kebab dimension already in finding 43.
- `bounds` — Rule artefact — script-only token; not in finding 43's 195.
- `case` — Rule artefact — script-only token; not in finding 43's 195.
- `complianceTrigger` — Rule artefact — camelCase schema twin of a kebab dimension already in finding 43.
- `countMatch` — Rule artefact — script-only token; not in finding 43's 195.
- `criteria` — Rule artefact — bare $defs key alongside the shape id finding 43 preferred.
- `criteriaFields` — Rule artefact — script-only token; not in finding 43's 195.
- `criteriaProposal` — Rule artefact — bare $defs key alongside the shape id finding 43 preferred.
- `ctierSchemaId` — Rule artefact — example/schema property token, not a finding-43 vocabulary row.
- `customerId` — Rule artefact — example/schema property token, not a finding-43 vocabulary row.
- `dataSensitivity` — Rule artefact — camelCase schema twin of a kebab dimension already in finding 43.
- `defaults` — Rule artefact — script-only token; not in finding 43's 195.
- `delete` — Rule artefact — HTTP method enum member; finding 43 did not inventory verbs.
- `digest` — Rule artefact — script-only token; not in finding 43's 195.
- `disposition` — Rule artefact — vocab field name; finding 43 inventoried members/uses more than the key.
- `escalationReason` — Rule artefact — vocab field name; finding 43 inventoried members/uses more than the key.
- `exclude` — Rule artefact — script-only token; not in finding 43's 195.
- `expect` — Rule artefact — script-only token; not in finding 43's 195.
- `get` — Rule artefact — HTTP method enum member; finding 43 did not inventory verbs.
- `halt` — Borderline — real response/agentAction token; finding 43 response set at attach did not list it.
- `handoff` — Rule artefact — script-only token; not in finding 43's 195.
- `head` — Rule artefact — HTTP method enum member; finding 43 did not inventory verbs.
- `input` — Rule artefact — script-only token; not in finding 43's 195.
- `operation` — Rule artefact — script-only token; not in finding 43's 195.
- `options` — Rule artefact — HTTP method enum member; finding 43 did not inventory verbs.
- `patch` — Rule artefact — HTTP method enum member; finding 43 did not inventory verbs.
- `paymentId` — Rule artefact — example/schema property token, not a finding-43 vocabulary row.
- `post` — Rule artefact — HTTP method enum member; finding 43 did not inventory verbs.
- `propose` — Rule artefact — script-only token; not in finding 43's 195.
- `provenance` — Rule artefact — script-only token; not in finding 43's 195.
- `put` — Rule artefact — HTTP method enum member; finding 43 did not inventory verbs.
- `rationale` — Rule artefact — script-only token; not in finding 43's 195.
- `recommendedAt` — Rule artefact — script-only token; not in finding 43's 195.
- `request` — Rule artefact — script-only token; not in finding 43's 195.
- `result` — Rule artefact — vocab field name; finding 43 inventoried members/uses more than the key.
- `reverses` — Rule artefact — script-only token; not in finding 43's 195.
- `rule` — Rule artefact — script-only token; not in finding 43's 195.
- `searchId` — Rule artefact — example/schema property token, not a finding-43 vocabulary row.
- `status` — Rule artefact — script-only token; not in finding 43's 195.
- `step` — Rule artefact — script-only token; not in finding 43's 195.
- `tier` — Rule artefact — script-only token; not in finding 43's 195.
- `trace` — Rule artefact — script-only token; not in finding 43's 195.
- `unassigned` — Borderline — real response/agentAction token; finding 43 response set at attach did not list it.
- `update` — Rule artefact — script-only token; not in finding 43's 195.
- `weight` — Rule artefact — script-only token; not in finding 43's 195.
- `when` — Rule artefact — script-only token; not in finding 43's 195.

## Finding-43-only (script missed; offset the surplus)

- ``decision-record/0.1.0`` (Record version) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``attempt-record/0.1.0`` (Record version) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `qualified spec` (Document type) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `Overlay 1.1.0` (Document type) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `Interface description` (Document type) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `Governance overlay` (Document type) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``undeclaredTier`` (Extension subfield) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``escalateAbove`` (Extension subfield) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``decaySeconds`` (Extension subfield) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``recommendationTtlDays`` (Extension subfield) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``parameter`` (Extension subfield) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``max`` (Extension subfield) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``authority`` (Extension subfield) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``x-ctier-tier` (header)` (Header) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``X-Agent-Action`` (Header) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``X-Correlation-Id`` (Header alias) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``X-Ctier-Tier`` (Header alias) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``X-Idempotency-Key`` (Header alias) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``none` (reversibility)` (Criteria value) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``none` (compliance)` (Criteria value) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `Configured` (Measurement kind) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `Observed` (Measurement kind) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `Requirement 1` (Deployment requirement) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `governed set` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `granted scope` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `undeclared default` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `join key` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `scope floor` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `structural floor` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `deploy-time bound` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `persist-and-execute` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `namespace strip` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `integrity-protection` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `refuse-to-emit` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- `undetermined` (Concept) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``sha256:` digest form` (Document key) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``PendingAuthorization`` (Response identifier) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``202`` (Response identifier) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``423`` (Response identifier) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
- ``503`` (Response identifier) — real hand-inventory row absent from the script harvest (miss, not a Part-2 extra).
