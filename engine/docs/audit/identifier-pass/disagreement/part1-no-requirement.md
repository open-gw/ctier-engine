# Part 1 — no-requirement disagreement

## Inventories

Finding 43's twenty-two (from `docs/findings/43.md`
"Identifiers with no requirement sentence", matching the
inventory tables' `no` rows):

1. ``execute``
2. ``refuse-and-suspend``
3. ``X-Delegation-Chain``
4. ``X-Incident-Id``
5. ``retry_later``
6. `Configured`
7. `Observed`
8. ``placeholder``
9. ``none` (escalationReason)`
10. ``session-accumulation``
11. ``delegation-authority-expansion``
12. ``payload-exceeds-declared-bounds``
13. ``computed-tier-exceeds-declared``
14. ``undeclared-operation``
15. ``operationAnchor``
16. ``correlationScope``
17. ``agentId` (record)`
18. ``idempotencyKey` (record)`
19. ``agent_suspended``
20. ``pending_authorization``
21. ``executed``
22. ``failed``

Script no-requirement count: **136**
(`derived/inventory-1.16.0-sweep.json`).

## Set arithmetic

| Set | Size |
|---|---:|
| Script ∩ hand agreed **no** | 16 |
| Script **no**, hand **yes** (classify below) | 76 |
| Script **no**, not in finding 43 inventory | 44 |
| Sum | 136 |

The headline gap 136 − 22 = 114 is not itself a set: six of
the record's twenty-two are outside the script's 136 (four
the script marks **yes** — `execute`, `retry_later`, `none`,
`executed` — and two the script never minted —
`Configured`, `Observed`). So
136 − 16 agreed = **120** identifiers in script-no that are
not in the record's twenty-two (76 hand-yes + 44 script-only).

Hand-no / script-yes (inverse disagreements; not Part 1
buckets): `execute`, `retry_later`, `none` (escalationReason),
`executed`. Hand-no / script-missing: `Configured`, `Observed`.

Agreed no (16): `X-Delegation-Chain`, `X-Incident-Id`, `agentId`, `agent_suspended`, `computed-tier-exceeds-declared`, `correlationScope`, `delegation-authority-expansion`, `failed`, `idempotencyKey`, `operationAnchor`, `payload-exceeds-declared-bounds`, `pending_authorization`, `placeholder`, `refuse-and-suspend`, `session-accumulation`, `undeclared-operation`.

## Bucket counts (76)

| Bucket | Count |
|---|---:|
| A | 44 |
| B | 32 |
| C | **0** |
| D | 0 |
| Ambiguous | 0 |

## C — script defect (complete list)

**None.** Re-scan of the 1.16.0 prose corpus with the script's
whole-token + RFC 2119 same-paragraph rule found no hit the
script marked `requirement_sentence: false`.

## A — class-level / titled-section indirection (44)

### `$defs/criteria`
- Finding 43: ``$defs/criteria`` (Schema shape)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`).
- Note: Class/shape-level completeness requirement covers the dimension or shape name.

### `$defs/criteriaProposal`
- Finding 43: ``$defs/criteriaProposal`` (Schema shape)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`).
- Note: Class/shape-level completeness requirement covers the dimension or shape name.

### `adjacent`
- Finding 43: ``adjacent`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `Agent suspension is an authorisation concern`
- Finding 43: `Agent suspension is an authorisation concern` (Validation rule)
- Quote: An implementation without it may record a rejection but cannot produce its effect, and MUST NOT simulate the effect by consulting the policy service on every request
- Note: Titled section; MUST is in the body paragraph, which does not repeat the title token — script requires same-paragraph co-occurrence.

### `appliedTierAtLeast`
- Finding 43: ``appliedTierAtLeast`` (Corpus field)
- Quote: An escalating case asserts `appliedTierAtLeast` rather than an exact tier…
- Note: Corpus-field class under conformance bounded imprecision.

### `attempt-record/0.2.0`
- Finding 43: ``attempt-record/0.2.0`` (Record version)
- Quote: Ledger / schema document-type version for Attempt records; covered by the record-version class the sweep treated as required alongside Decision/Attempt/Outcome.
- Note: Version id rarely sits in a MUST sentence; hand credited via record class.

### `Authorization`
- Finding 43: ``Authorization` (custody)` (Header)
- Quote: `Authorization` on custody's execute request is the policy service authenticating as itself (C6: the agent is not the client).
- Note: Covered by C6; the header token is not in C6's MUST paragraph.

### `blast-radius`
- Finding 43: ``blast-radius`` (Criteria dimension)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`).
- Note: Class/shape-level completeness requirement covers the dimension or shape name.

### `Bound comparison`
- Finding 43: `Bound comparison` (Validation rule)
- Quote: An implementation MUST interpret a bound parameter's value as a decimal number.
- Note: Titled section; MUST is in the body paragraph, which does not repeat the title token — script requires same-paragraph co-occurrence.

### `classification-rules/0.1.0`
- Finding 43: ``classification-rules/0.1.0`` (Document type)
- Quote: Document types listed in schemas/README and validated as named ctier-authored formats; hand treated the document-type class as carrying schema/validation requirements.
- Note: Class-level; script finds no MUST co-occurrence with the version string.

### `compliance-trigger`
- Finding 43: ``compliance-trigger`` (Criteria dimension)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`).
- Note: Class/shape-level completeness requirement covers the dimension or shape name.

### `composition-manifest/0.1.0`
- Finding 43: ``composition-manifest/0.1.0`` (Document type)
- Quote: Document types listed in schemas/README and validated as named ctier-authored formats; hand treated the document-type class as carrying schema/validation requirements.
- Note: Class-level; script finds no MUST co-occurrence with the version string.

### `constrained`
- Finding 43: ``constrained`` (Profile)
- Quote: `profile` | `standard` bounds…; `constrained` does not assume that, and puts the check at the enforcement point
- Note: Profile class; standard co-occurs with MUST in a large Naming paragraph, constrained does not.

### `coverage-report/0.1.0`
- Finding 43: ``coverage-report/0.1.0`` (Document type)
- Quote: Document types listed in schemas/README and validated as named ctier-authored formats; hand treated the document-type class as carrying schema/validation requirements.
- Note: Class-level; script finds no MUST co-occurrence with the version string.

### `data-sensitivity`
- Finding 43: ``data-sensitivity`` (Criteria dimension)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`).
- Note: Class/shape-level completeness requirement covers the dimension or shape name.

### `decision-record/0.2.0`
- Finding 43: ``decision-record/0.2.0`` (Record version)
- Quote: Ledger / schema document-type version for Decision records; same class-level credit as other record versions.
- Note: Class-level indirection.

### `fragments`
- Finding 43: ``fragments`` (Generator mode)
- Quote: Generator mode beside `bundle` on composition-manifest; hand credited the mode class (bundle has MUST-proximity elsewhere in headers.md).
- Note: Class-level indirection to generator-mode requirements.

### `internal`
- Finding 43: ``internal`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `key-required`
- Finding 43: ``key-required`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `Level 0`
- Finding 43: `Level 0` (Deployment level)
- Quote: Adoption-ladder / conformance deployment-level class: levels are the named rungs the deployment requirements and C-criteria bind to (e.g. Level 2 enforces Tiers 1, 2 and 4…).
- Note: Hand credits the level as required by the ladder contract; no same-paragraph MUST+token for Level 0/1 / level-2/3 at sweep.

### `Level 1`
- Finding 43: `Level 1` (Deployment level)
- Quote: Adoption-ladder / conformance deployment-level class: levels are the named rungs the deployment requirements and C-criteria bind to (e.g. Level 2 enforces Tiers 1, 2 and 4…).
- Note: Hand credits the level as required by the ladder contract; no same-paragraph MUST+token for Level 0/1 / level-2/3 at sweep.

### `level-2`
- Finding 43: ``level-2`` (Deployment level)
- Quote: Adoption-ladder / conformance deployment-level class: levels are the named rungs the deployment requirements and C-criteria bind to (e.g. Level 2 enforces Tiers 1, 2 and 4…).
- Note: Hand credits the level as required by the ladder contract; no same-paragraph MUST+token for Level 0/1 / level-2/3 at sweep.

### `level-3`
- Finding 43: ``level-3`` (Deployment level)
- Quote: Adoption-ladder / conformance deployment-level class: levels are the named rungs the deployment requirements and C-criteria bind to (e.g. Level 2 enforces Tiers 1, 2 and 4…).
- Note: Hand credits the level as required by the ladder contract; no same-paragraph MUST+token for Level 0/1 / level-2/3 at sweep.

### `No credential persistence`
- Finding 43: `No credential persistence` (Validation rule)
- Quote: A policy service MUST NOT persist any credential belonging to the agent.
- Note: Titled section; MUST is in the body paragraph, which does not repeat the title token — script requires same-paragraph co-occurrence.

### `not-applicable`
- Finding 43: ``not-applicable`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `personal`
- Finding 43: ``personal`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `population`
- Finding 43: ``population`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `public`
- Finding 43: ``public`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `recommendation-set/0.1.0`
- Finding 43: ``recommendation-set/0.1.0`` (Document type)
- Quote: Document types listed in schemas/README and validated as named ctier-authored formats; hand treated the document-type class as carrying schema/validation requirements.
- Note: Class-level; script finds no MUST co-occurrence with the version string.

### `regulated`
- Finding 43: ``regulated`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `Requirement 2`
- Finding 43: `Requirement 2` (Deployment requirement)
- Quote: 2. **Custody's execute path bypasses the enforcement point by design.** … The backend MUST treat custody as a trusted caller…
- Note: Identifier "Requirement N" is the list label; MUST appears in the item body without the words "Requirement N" (except elsewhere with lowercase must for Requirement 3).

### `Requirement 3`
- Finding 43: `Requirement 3` (Deployment requirement)
- Quote: 3. **A deployment MUST ensure the ctier ingress strip precedes any component that reads a reserved header.**
- Note: Identifier "Requirement N" is the list label; MUST appears in the item body without the words "Requirement N" (except elsewhere with lowercase must for Requirement 3).

### `Requirement 4`
- Finding 43: `Requirement 4` (Deployment requirement)
- Quote: Numbered deployment-requirement item under "What ctier requires of the deployment" (item 4 in the same list).
- Note: Identifier "Requirement N" is the list label; MUST appears in the item body without the words "Requirement N" (except elsewhere with lowercase must for Requirement 3).

### `reversibility`
- Finding 43: ``reversibility`` (Criteria dimension)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`).
- Note: Class/shape-level completeness requirement covers the dimension or shape name.

### `sequence`
- Finding 43: ``sequence`` (Corpus field)
- Quote: Conformance corpus dimensions table (`profile` / `deployment` / `sequence`); sequence is a required dimension of the corpus class.
- Note: Class-level corpus field.

### `single-customer`
- Finding 43: ``single-customer`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `single-record`
- Finding 43: ``single-record`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `Single-target rule`
- Finding 43: `Single-target rule` (Validation rule)
- Quote: An overlay action whose `update` sets any `x-ctier-*` field that resolves to a tier below 4 — whether by declaring `x-ctier-tier` or by supplying `x-ctier-criteria` that compute one — MUST select exactly one operation.
- Note: Titled section; MUST is in the body paragraph, which does not repeat the title token — script requires same-paragraph co-occurrence.

### `system-wide`
- Finding 43: ``system-wide`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `Tier 1`
- Finding 43: `Tier 1` (Tier)
- Quote: Tier table under "Who executes" in extensions.md (Tier 1–4); tiers are the classification targets C-criteria and overlay rules bind to.
- Note: Class-level; Tier 2–4 happen to co-occur with MUST elsewhere, Tier 1 does not.

### `Tier 2 requires a verified compensating action`
- Finding 43: `Tier 2 requires a verified compensating action` (Validation rule)
- Quote: An operation declaring `x-ctier-tier: 2`, or criteria resolving to Tier 2, MUST be named by an `x-ctier-reverses` field in the same composed description.
- Note: Titled section; MUST is in the body paragraph, which does not repeat the title token — script requires same-paragraph co-occurrence.

### `undo-restores-effect`
- Finding 43: ``undo-restores-effect`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `undo-restores-record-only`
- Finding 43: ``undo-restores-record-only`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.

### `unsafe`
- Finding 43: ``unsafe`` (Criteria value)
- Quote: Where `x-ctier-criteria` appears on a description or qualified spec, all five fields are required (`$defs/criteria`). Enum members are the closed value set of those required fields.
- Note: Class-level indirection via required criteria fields; individual values are not named in a MUST sentence.


## B — prose without RFC 2119 keyword (32)

### `403`
- Finding 43: ``403`` (Response identifier)
- Quote: Excluded — `403`.** Refused at credential validation, before consequence evaluation.
- Note: Bold excluded-status prose without MUST/SHALL/REQUIRED.

### `Attempt`
- Finding 43: `Attempt` (Record type)
- Quote: **Attempt** — the enforcement point refused without classifying…
- Note: Ledger-records definitional prose; no MUST beside the name.

### `Bounds coherence`
- Finding 43: `Bounds coherence` (Validation rule)
- Quote: `x-ctier-bounds.parameter` must name a parameter that exists on the operation.
- Note: Requirement-like section prose without uppercase MUST/SHALL/REQUIRED.

### `Coverage sort`
- Finding 43: `Coverage sort` (Validation rule)
- Quote: `coverage-report` `operations` is ordered by recommended tier descending, `absent` last.
- Note: Requirement-like section prose without uppercase MUST/SHALL/REQUIRED.

### `ctierSchema`
- Finding 43: ``ctierSchema`` (Document key)
- Quote: - `ctierSchema` equals the expected `<name>/<version>` string.
- Note: Schema-checked list item without RFC 2119 keyword.

### `Engine `Criteria` defaults are not the contract`
- Finding 43: `Engine `Criteria` defaults are not the contract` (Validation rule)
- Quote: Those defaults are **not** the document contract and must never be relied upon by a document.
- Note: Requirement-like section prose without uppercase MUST/SHALL/REQUIRED.

### `Exclusion exclusivity`
- Finding 43: `Exclusion exclusivity` (Validation rule)
- Quote: `x-ctier-exclude: true` with a declared `x-ctier-tier` is a contradiction.
- Note: Requirement-like section prose without uppercase MUST/SHALL/REQUIRED.

### `hasDeclaredReversal`
- Finding 43: ``hasDeclaredReversal`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `hasRequestBody`
- Finding 43: ``hasRequestBody`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `high`
- Finding 43: ``high`` (Confidence)
- Quote: Enumerations: … rule `confidence` `high` | `medium` | `low`.
- Note: Named in schema-checked enumerations prose without RFC 2119.

### `low`
- Finding 43: ``low`` (Confidence)
- Quote: Enumerations: … rule `confidence` `high` | `medium` | `low`.
- Note: Named in schema-checked enumerations prose without RFC 2119.

### `medium`
- Finding 43: ``medium`` (Confidence)
- Quote: Enumerations: … rule `confidence` `high` | `medium` | `low`.
- Note: Named in schema-checked enumerations prose without RFC 2119.

### `No agent-facing URL`
- Finding 43: `No agent-facing URL` (Validation rule)
- Quote: **No response emitted to an agent carries a URL.**
- Note: Requirement-like section prose without uppercase MUST/SHALL/REQUIRED.

### `operationIdMatches`
- Finding 43: ``operationIdMatches`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `Outcome`
- Finding 43: `Outcome` (Record type)
- Quote: **Outcome** — what happened when an approved Tier 3 executed… / An outcome is the only record that proves C6 held.
- Note: Definitional prose without RFC 2119 beside the name.

### `Pagination is refused as a predicate`
- Finding 43: `Pagination is refused as a predicate` (Validation rule)
- Quote: No pagination predicate exists. If a recommender wants that signal, it uses `x-ctier-bounds` being present or absent.
- Note: Requirement-like section prose without uppercase MUST/SHALL/REQUIRED.

### `pathEndsWithParameter`
- Finding 43: ``pathEndsWithParameter`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `pathParameterCount`
- Finding 43: ``pathParameterCount`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `pathSegmentCount`
- Finding 43: ``pathSegmentCount`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `responseIsCollection`
- Finding 43: ``responseIsCollection`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `securitySchemes`
- Finding 43: ``securitySchemes`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `Self-reversal`
- Finding 43: `Self-reversal` (Validation rule)
- Quote: An operation MAY name itself in `x-ctier-reverses`… An operation that is `key-required` or `unsafe` cannot reverse itself
- Note: Requirement-like section prose without uppercase MUST/SHALL/REQUIRED.

### `tagIn`
- Finding 43: ``tagIn`` (when-predicate)
- Quote: `when` contains only the closed predicate keys: `method`, `pathEndsWithParameter`, `responseIsCollection`, `hasRequestBody`, `securitySchemes`, `tagIn`, `operationIdMatches`, `hasDeclaredReversal`, `pathSegmentCount`, `pathParameterCount`.
- Note: Named in the closed-set prose; no RFC 2119 keyword in that bullet.

### `X-Agent-Id`
- Finding 43: ``X-Agent-Id`` (Header)
- Quote: Pass-through of the agent's inbound headers (including `X-Agent-Id`) is not a ctier emit.
- Note: Descriptive wire note without RFC 2119; hand still marked requirement=yes.

### `x-ctier-bounds`
- Finding 43: ``x-ctier-bounds`` (Extension field)
- Quote: `parameter` must name a parameter that exists on the operation. That check is validator-enforced; see `validation.md`.
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.

### `x-ctier-defaults`
- Finding 43: ``x-ctier-defaults`` (Extension field)
- Quote: Object. Optional. Fail-closed values apply when a field is omitted.
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.

### `x-ctier-escalate-to`
- Finding 43: ``x-ctier-escalate-to`` (Extension field)
- Quote: Integer 1–4. Optional. Per-operation accumulation target. May never resolve below the tier already reached. That check is validator-enforced; see `validation.md` (C3).
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.

### `x-ctier-exclude`
- Finding 43: ``x-ctier-exclude`` (Extension field)
- Quote: Exclusion exclusivity / exclude semantics in extensions + validation (contradiction with declared tier).
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.

### `x-ctier-handoff`
- Finding 43: ``x-ctier-handoff`` (Extension field)
- Quote: Object. Optional. The authority class… The class is declared; the person is resolved by the consuming application.
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.

### `x-ctier-provenance`
- Finding 43: ``x-ctier-provenance`` (Extension field)
- Quote: Provenance field on recommendation-set / validation discussion of overlay provenance.
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.

### `x-ctier-rationale`
- Finding 43: ``x-ctier-rationale`` (Extension field)
- Quote: String. Optional. Why this tier. What survives an audit.
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.

### `x-ctier-weight`
- Finding 43: ``x-ctier-weight`` (Extension field)
- Quote: Integer ≥ 0. Optional. Contribution to accumulated consequence. **Zero is meaningful**
- Note: Field section under extensions.md; body uses lowercase must / table "Required" / descriptive norms, not uppercase MUST co-occurring with the field token in one paragraph.


## D — genuinely unstated (hand erred)

None among the 76. (Coverage-sort and similar are filed under
B as requirement-like prose, not as hand error.)

## Script-only contributors to the 136 (44)

These inflate the script's no-requirement total without a
finding-43 requirement column to disagree with. Judged under
Part 2 (rule artefacts). List:

- `4.1 Rules become data, not code`
- `4.2 Recommendations are an overlay`
- `4.3 The schemas live in the specification repository, not the engine`
- `C13 — Digest discipline`
- `C2 — Fail-closed`
- `C3 — Unidirectionality`
- `Criteria`
- `Ledger records`
- `On the maturity of these criteria`
- `The transformations, as document-in / document-out`
- `accountId`
- `artefact`
- `authorizationId`
- `blastRadius`
- `bounds`
- `case`
- `complianceTrigger`
- `countMatch`
- `criteriaFields`
- `criteriaProposal`
- `ctierSchemaId`
- `customerId`
- `dataSensitivity`
- `defaults`
- `delete`
- `disposition`
- `escalationReason`
- `exclude`
- `expect`
- `get`
- `handoff`
- `head`
- `options`
- `patch`
- `paymentId`
- `post`
- `put`
- `rationale`
- `recommendedAt`
- `result`
- `reverses`
- `searchId`
- `trace`
- `weight`
