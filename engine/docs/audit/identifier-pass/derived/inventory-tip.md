# Identifier pass — derived at `66c509f3625f`

Counting rule: `COUNTING-RULE.md` beside `identifier_pass.py`.

## Totals vs validation.md

| Total | Derived | Recorded (validation.md 1.16.0) | Agree? |
|---|---:|---:|---|
| Identifiers | 252 | 195 | no |
| Classes | 34 | 33 | no |
| No requirement sentence (strict) | 137 | 22 | no |
| No requirement sentence (lenient) | 41 | 22 | no |
| Stated under a different name (proxy) | 78 | 3 | no |

Strict→lenient gap: **96** (itemised under `lenient_closes_by_rule`).

### Lenient closes by rule (strict=no → lenient=yes)

| Rule | Count |
|---|---:|
| `class-coverage` | 45 |
| `requirement-like-prose` | 43 |
| `titled-section-body` | 8 |

## Per class

| Class | Count |
|---|---:|
| Unclassified | 44 |
| Validation rule | 19 |
| Criteria value | 17 |
| Criterion | 16 |
| Concept | 12 |
| Extension field | 12 |
| Header | 12 |
| Response identifier | 10 |
| when-predicate | 10 |
| Document type | 9 |
| Criteria dimension | 8 |
| Deployment level | 7 |
| Extension subfield | 7 |
| Ledger field | 7 |
| Escalation reason | 6 |
| Corpus field | 5 |
| Deployment requirement | 5 |
| Disposition | 4 |
| Schema shape | 4 |
| Tier | 4 |
| agentAction | 4 |
| Confidence | 3 |
| Coverage status | 3 |
| Header alias | 3 |
| Measurement kind | 3 |
| Record type | 3 |
| Record version | 3 |
| Composition role | 2 |
| Digest | 2 |
| Generator mode | 2 |
| Outcome result | 2 |
| Profile | 2 |
| Document key | 1 |
| Namespace | 1 |

## Inventory

| Identifier | Class | Strict? | Lenient? | Rules | Titled? |
|---|---|---|---|---|---|
| `$defs/criteria` | Schema shape | no | yes | class-coverage,requirement-like-prose | no |
| `$defs/criteriaProposal` | Schema shape | no | yes | class-coverage,requirement-like-prose | no |
| `1.1.0` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `4.1 Rules become data, not code` | Document type | no | yes | class-coverage | yes |
| `4.2 Recommendations are an overlay` | Document type | no | yes | class-coverage | yes |
| `4.3 The schemas live in the specification repository, not the engine` | Document type | no | yes | class-coverage | yes |
| `403` | Response identifier | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `absent` | Coverage status | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `accountId` | Unclassified | no | no | — | no |
| `action` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `Additive evolution` | Validation rule | yes | yes | strict-rfc2119,titled-section-body,requirement-like-prose | yes |
| `adjacent` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `agent` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `agent_suspended` | Response identifier | no | no | — | yes |
| `agentAction` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `agentId` | Ledger field | no | no | — | no |
| `AgentSuspended` | Response identifier | yes | yes | strict-rfc2119 | no |
| `appliedTierAtLeast` | Corpus field | no | yes | class-coverage | no |
| `artefact` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `Attempt` | Record type | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `attempt-record/0.3.0` | Record version | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `authority` | Extension subfield | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `Authorization` | Header | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `authorizationId` | Unclassified | no | no | — | no |
| `autoResume` | Response identifier | yes | yes | strict-rfc2119 | no |
| `blast-radius` | Criteria dimension | no | yes | class-coverage,requirement-like-prose | no |
| `blastRadius` | Criteria dimension | no | yes | class-coverage | no |
| `Bound comparison` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `bounds` | Unclassified | no | no | — | no |
| `Bounds coherence` | Validation rule | no | yes | requirement-like-prose | yes |
| `bundle` | Generator mode | yes | yes | strict-rfc2119,class-coverage | no |
| `C1` | Criterion | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `C10` | Criterion | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `C11` | Criterion | yes | yes | strict-rfc2119 | yes |
| `C12` | Criterion | yes | yes | strict-rfc2119 | yes |
| `C13` | Criterion | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `C13 — Digest discipline` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `C14` | Criterion | yes | yes | strict-rfc2119 | yes |
| `C14 — No credential persistence` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `C15` | Criterion | yes | yes | strict-rfc2119 | yes |
| `C15 — Agent suspension is an authorisation concern` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `C16` | Criterion | yes | yes | strict-rfc2119 | yes |
| `C16 — The namespace is stripped on ingress` | Validation rule | no | yes | requirement-like-prose | yes |
| `C2` | Criterion | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `C2 — Fail-closed` | Validation rule | no | yes | requirement-like-prose | yes |
| `C3` | Criterion | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `C3 — Unidirectionality` | Validation rule | no | no | — | yes |
| `C4` | Criterion | yes | yes | strict-rfc2119 | yes |
| `C5` | Criterion | yes | yes | strict-rfc2119 | no |
| `C6` | Criterion | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `C7` | Criterion | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `C8` | Criterion | yes | yes | strict-rfc2119 | yes |
| `C9` | Criterion | yes | yes | strict-rfc2119 | no |
| `case` | Unclassified | no | no | — | no |
| `classification-rules/0.1.0` | Document type | no | yes | class-coverage | no |
| `compliance-trigger` | Criteria dimension | no | yes | class-coverage,requirement-like-prose | no |
| `complianceTrigger` | Criteria dimension | no | yes | class-coverage | no |
| `composition-manifest/0.1.0` | Document type | no | yes | class-coverage | no |
| `compositionDigest` | Digest | yes | yes | strict-rfc2119 | no |
| `computed-tier-exceeds-declared` | Escalation reason | no | no | — | no |
| `Configured` | Measurement kind | no | no | — | no |
| `conformance-corpus/0.3.0` | Document type | yes | yes | strict-rfc2119,class-coverage | no |
| `constrained` | Profile | no | yes | class-coverage | no |
| `continue_task_without_this_step` | agentAction | yes | yes | strict-rfc2119 | yes |
| `correlationScope` | Ledger field | no | no | — | no |
| `countMatch` | Unclassified | no | no | — | no |
| `Coverage sort` | Validation rule | no | yes | requirement-like-prose | yes |
| `coverage-report/0.1.0` | Document type | no | yes | class-coverage | no |
| `criteria` | Schema shape | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `Criteria` | Unclassified | no | yes | requirement-like-prose | yes |
| `criteriaFields` | Unclassified | no | no | — | no |
| `criteriaProposal` | Schema shape | no | yes | class-coverage,requirement-like-prose | no |
| `ctierSchema` | Document key | no | yes | requirement-like-prose | no |
| `ctierSchemaId` | Unclassified | no | no | — | no |
| `custody_unavailable` | Response identifier | yes | yes | strict-rfc2119 | yes |
| `customerId` | Unclassified | no | no | — | no |
| `data-sensitivity` | Criteria dimension | no | yes | class-coverage,requirement-like-prose | no |
| `dataSensitivity` | Criteria dimension | no | yes | class-coverage | no |
| `decaySeconds` | Extension subfield | no | yes | requirement-like-prose | no |
| `Decision` | Record type | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `decision-record/0.2.0` | Record version | no | yes | class-coverage,requirement-like-prose | no |
| `declared` | Coverage status | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `defaults` | Unclassified | no | yes | requirement-like-prose | no |
| `delegation-authority-expansion` | Escalation reason | no | no | — | no |
| `delete` | Unclassified | no | no | — | no |
| `deploy-time bound` | Concept | no | no | — | no |
| `deployment` | Corpus field | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `deploymentDigest` | Digest | yes | yes | strict-rfc2119 | no |
| `Derived` | Measurement kind | yes | yes | strict-rfc2119 | no |
| `description` | Composition role | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `digest` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `direct` | Criteria value | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `disposition` | Ledger field | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `Engine `Criteria` defaults are not the contract` | Validation rule | no | yes | requirement-like-prose | yes |
| `escalateAbove` | Extension subfield | no | yes | requirement-like-prose | no |
| `escalationReason` | Ledger field | no | no | — | no |
| `exclude` | Unclassified | no | no | — | no |
| `Exclusion exclusivity` | Validation rule | no | yes | requirement-like-prose | yes |
| `execute` | Disposition | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `executed` | Outcome result | yes | yes | strict-rfc2119 | no |
| `expect` | Unclassified | no | no | — | no |
| `failed` | Outcome result | no | no | — | no |
| `fragments` | Generator mode | no | yes | class-coverage | no |
| `get` | Unclassified | yes | yes | strict-rfc2119 | no |
| `governed set` | Concept | yes | yes | strict-rfc2119 | no |
| `granted scope` | Concept | no | yes | requirement-like-prose | no |
| `halt` | agentAction | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `halt_and_hand_off` | agentAction | yes | yes | strict-rfc2119 | yes |
| `handoff` | Unclassified | no | no | — | no |
| `hasDeclaredReversal` | when-predicate | no | yes | requirement-like-prose | no |
| `hasRequestBody` | when-predicate | no | yes | requirement-like-prose | no |
| `head` | Unclassified | no | no | — | no |
| `high` | Confidence | no | yes | requirement-like-prose | no |
| `idempotency` | Criteria dimension | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `Idempotency-Key` | Header | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `idempotencyKey` | Ledger field | no | no | — | no |
| `incidentId` | Response identifier | yes | yes | strict-rfc2119 | no |
| `inherently-safe` | Criteria value | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `input` | Unclassified | yes | yes | strict-rfc2119 | no |
| `integrity-protection` | Concept | yes | yes | strict-rfc2119 | no |
| `internal` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `join key` | Concept | yes | yes | strict-rfc2119 | no |
| `key-required` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `Ledger records` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `Level 0` | Deployment level | no | yes | class-coverage | no |
| `Level 1` | Deployment level | no | yes | class-coverage | no |
| `Level 2` | Deployment level | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `Level 3` | Deployment level | yes | yes | strict-rfc2119,class-coverage | no |
| `Level 4` | Deployment level | yes | yes | strict-rfc2119,class-coverage | no |
| `level-2` | Deployment level | no | yes | class-coverage | no |
| `level-3` | Deployment level | no | yes | class-coverage | no |
| `low` | Confidence | no | yes | requirement-like-prose | no |
| `max` | Extension subfield | no | yes | requirement-like-prose | no |
| `medium` | Confidence | no | yes | requirement-like-prose | no |
| `method` | when-predicate | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `namespace strip` | Concept | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `No agent-facing URL` | Validation rule | no | yes | requirement-like-prose | yes |
| `none` | Escalation reason | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `not-applicable` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `Observed` | Measurement kind | yes | yes | strict-rfc2119 | no |
| `On the maturity of these criteria` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `operation` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `operationAnchor` | Ledger field | no | no | — | no |
| `operationIdMatches` | when-predicate | no | yes | requirement-like-prose | no |
| `options` | Unclassified | no | no | — | no |
| `Outcome` | Record type | no | yes | requirement-like-prose | no |
| `outcome-record/0.1.0` | Record version | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `overlay` | Composition role | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `Pagination is refused as a predicate` | Validation rule | no | yes | requirement-like-prose | yes |
| `parameter` | Extension subfield | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `patch` | Unclassified | no | no | — | no |
| `pathEndsWithParameter` | when-predicate | no | yes | requirement-like-prose | no |
| `pathParameterCount` | when-predicate | no | yes | requirement-like-prose | no |
| `pathSegmentCount` | when-predicate | no | yes | requirement-like-prose | no |
| `payload-exceeds-declared-bounds` | Escalation reason | no | no | — | no |
| `paymentId` | Unclassified | no | no | — | no |
| `pending_authorization` | Response identifier | no | yes | requirement-like-prose | yes |
| `persist-and-execute` | Concept | yes | yes | strict-rfc2119 | no |
| `personal` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `placeholder` | Corpus field | no | no | — | no |
| `population` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `post` | Unclassified | no | no | — | no |
| `profile` | Corpus field | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `propose` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `provenance` | Unclassified | yes | yes | strict-rfc2119 | no |
| `provisioning_defect` | Response identifier | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `public` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `put` | Unclassified | yes | yes | strict-rfc2119 | no |
| `rationale` | Unclassified | no | no | — | no |
| `recommendation-set/0.1.0` | Document type | no | yes | class-coverage | no |
| `recommendationTtlDays` | Extension subfield | no | yes | requirement-like-prose | no |
| `recommended` | Coverage status | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `recommendedAt` | Unclassified | no | no | — | no |
| `refuse-and-suspend` | Disposition | no | no | — | no |
| `refuse-provisioning` | Disposition | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `refuse-to-emit` | Concept | yes | yes | strict-rfc2119 | no |
| `regulated` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `request` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `Requirement 2` | Deployment requirement | no | yes | class-coverage,titled-section-body | no |
| `Requirement 3` | Deployment requirement | yes | yes | strict-rfc2119,class-coverage,titled-section-body,requirement-like-prose | no |
| `Requirement 4` | Deployment requirement | no | yes | class-coverage,requirement-like-prose | no |
| `Requirement 5` | Deployment requirement | no | yes | class-coverage,titled-section-body | no |
| `Requirement 6` | Deployment requirement | no | yes | class-coverage,requirement-like-prose | no |
| `responseIsCollection` | when-predicate | no | yes | requirement-like-prose | no |
| `result` | Ledger field | no | no | — | no |
| `Retry-After` | Header | yes | yes | strict-rfc2119 | no |
| `retry_later` | agentAction | yes | yes | strict-rfc2119 | yes |
| `reverses` | Unclassified | no | no | — | no |
| `reversibility` | Criteria dimension | no | yes | class-coverage,requirement-like-prose | no |
| `rule` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `safe` | Criteria value | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `scope floor` | Concept | no | yes | requirement-like-prose | no |
| `searchId` | Unclassified | no | no | — | no |
| `securitySchemes` | when-predicate | no | yes | requirement-like-prose | no |
| `Self-reversal` | Validation rule | no | yes | requirement-like-prose | yes |
| `sequence` | Corpus field | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `session-accumulation` | Escalation reason | no | no | — | no |
| `single-customer` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `single-record` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `Single-target rule` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `standard` | Profile | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | yes |
| `status` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `step` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `structural floor` | Concept | no | no | — | no |
| `system-wide` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `tagIn` | when-predicate | no | yes | requirement-like-prose | no |
| `The transformations, as document-in / document-out` | Document type | no | yes | class-coverage | yes |
| `tier` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `Tier 1` | Tier | no | yes | class-coverage | no |
| `Tier 2` | Tier | yes | yes | strict-rfc2119,class-coverage | yes |
| `Tier 2 requires a verified compensating action` | Validation rule | no | yes | titled-section-body,requirement-like-prose | yes |
| `Tier 3` | Tier | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `Tier 4` | Tier | yes | yes | strict-rfc2119,class-coverage,requirement-like-prose | no |
| `trace` | Unclassified | no | no | — | no |
| `unassigned` | Response identifier | yes | yes | strict-rfc2119 | yes |
| `unauthorized` | Response identifier | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `undeclared default` | Concept | yes | yes | strict-rfc2119 | no |
| `undeclared-operation` | Escalation reason | no | no | — | no |
| `undeclaredTier` | Extension subfield | no | yes | requirement-like-prose | no |
| `undetermined` | Concept | yes | yes | strict-rfc2119 | no |
| `undo-restores-effect` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `undo-restores-record-only` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `unsafe` | Criteria value | no | yes | class-coverage,requirement-like-prose | no |
| `update` | Unclassified | yes | yes | strict-rfc2119 | no |
| `weight` | Unclassified | no | yes | requirement-like-prose | no |
| `when` | Unclassified | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `withhold` | Disposition | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `X-Agent-Id` | Header | no | yes | requirement-like-prose | no |
| `x-consequence-*` | Namespace | yes | yes | strict-rfc2119 | no |
| `X-Correlation-Id` | Header alias | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `x-ctier-*` | Header | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `x-ctier-bounds` | Extension field | no | yes | requirement-like-prose | yes |
| `x-ctier-composition` | Header | yes | yes | strict-rfc2119 | no |
| `x-ctier-correlation-id` | Header | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `x-ctier-criteria` | Extension field | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `x-ctier-defaults` | Extension field | no | yes | requirement-like-prose | yes |
| `x-ctier-deployment` | Header | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `x-ctier-escalate-to` | Extension field | no | yes | requirement-like-prose | yes |
| `x-ctier-exclude` | Extension field | no | yes | requirement-like-prose | yes |
| `x-ctier-handoff` | Extension field | no | yes | requirement-like-prose | yes |
| `x-ctier-operation` | Header | yes | yes | strict-rfc2119 | no |
| `x-ctier-provenance` | Extension field | no | yes | requirement-like-prose | no |
| `x-ctier-rationale` | Extension field | no | yes | requirement-like-prose | yes |
| `x-ctier-recommended-at` | Extension field | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `x-ctier-reverses` | Extension field | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `x-ctier-status` | Extension field | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `x-ctier-tier` | Header | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `X-Ctier-Tier` | Header alias | yes | yes | strict-rfc2119,requirement-like-prose | no |
| `x-ctier-weight` | Extension field | no | yes | requirement-like-prose | yes |
| `X-Delegation-Chain` | Header | yes | yes | strict-rfc2119,requirement-like-prose | yes |
| `X-Idempotency-Key` | Header alias | yes | yes | strict-rfc2119 | no |
| `X-Incident-Id` | Header | yes | yes | strict-rfc2119,requirement-like-prose | yes |
