# Identifier-pass counting rule

This is the rule the mechanised script implements.
It is an honest reading of the recorded hand inventory's "whether this check
could be mechanised" note — not a reverse-engineer of the
195 / 33 / 22 / 3 headline. If the totals disagree with
`spec/validation.md`, that disagreement is a finding.

## Corpus (at the commit under test)

Read only:

- `spec/**/*.md` (README, validation, conformance, extensions,
  headers, schemas/README, examples README — whatever exists)
- `spec/schemas/*.json`
- `spec/consequence-tiered-api.yaml`
- `spec/examples/**` is **not** scanned for new identifiers;
  example-only tokens surface only if also present in schemas
  or prose (the recorded hand inventory excluded example-only names from the
  "where introduced" column when they had no other home, but
  still listed a few that lived only in the example — those
  require a reader; this script does not invent them from
  examples alone)
- `docs/adr/0009*` because the specification points at it

Not in corpus: `docs/classification-guide.md`,
`runtime-suite`, `record-source`, engine trees, findings.

## What counts as an identifier

Union of the following, de-duplicated by normalised name
(case-sensitive spelling as first seen; aliases that differ
only by punctuation are kept distinct when the corpus spells
them differently — e.g. `Level 2` vs `level-2`):

1. **Schema vocabulary**
   - every string member of every `enum`
   - every string `const` (document / record version ids,
     overlay version, status literals)
   - every `$defs` key
   - every property name under `properties` that starts with
     `x-ctier-`, plus the well-known ledger / corpus field
     names that schemas introduce as first-class keys:
     `escalationReason`, `disposition`, `result`, `profile`,
     `deployment`, `sequence`, `appliedTierAtLeast`,
     `placeholder`, `operationAnchor`, `correlationScope`,
     `agentId`, `idempotencyKey`, `compositionDigest`,
     `deploymentDigest`, `ctierSchema`
   - every `$id` basename turned into the document-type form
     used in prose (e.g. `decision-record/0.2.0` from the
     matching `const`, already covered)

2. **Prose-titled names** in `spec/*.md` and ADR-0009
   - headings / bold lead-ins matching `C` + digits (criteria)
   - `Level` + digit, `Tier` + digit, `Requirement` + digit
   - markdown `###` / `##` titles that are not structural
     (`# ctier specification…` excluded)
   - backtick-wrapped tokens inside those headings
   - closed when-predicate key lists stated in
     `validation.md` (the script recognises the
     `pathEndsWithParameter` family by reading the paragraph
     that names the closed keys)

3. **OpenAPI / YAML vocabulary** in
   `consequence-tiered-api.yaml`
   - header parameter `name` values
   - extension keys matching `x-ctier-*`
   - schema `status` / `agentAction` enumerations if present

HTTP method verbs that appear only as
`when.method` enum members (`get`, `put`, …) are **kept** —
the rule does not special-case them away. The recorded hand inventory did not
inventory them; that delta is reported, not fitted.

## Class

Assigned by the first matching heuristic, in order:

| Pattern / source | Class |
|---|---|
| `C` + digits | Criterion |
| `Level N` / `level-N` | Deployment level |
| `Tier N` | Tier |
| `Requirement N` | Deployment requirement |
| disposition enum members | Disposition |
| escalationReason enum | Escalation reason |
| outcome `result` enum | Outcome result |
| criteria dimension enums / `$defs` criteria dims | Criteria value / Criteria dimension / Schema shape |
| `x-ctier-*` property in extensions schema or extensions.md | Extension field |
| nested fields under `x-ctier-*` objects (`undeclaredTier`, `authority`, …) | Extension subfield |
| header `name` / headers.md heading | Header |
| `X-*` alias called out as alias in headers.md | Header alias |
| named concepts harvested from prose (`governed set`, …) | Concept |
| generator mode enum | Generator mode |
| input role enum | Composition role |
| coverage / x-ctier-status enum | Coverage status |
| confidence enum | Confidence |
| profile / deployment corpus enums | Profile / Corpus field / Deployment level |
| record `const` `*-record/N` | Record version (and Record type from the stem) |
| document `const` / `$id` document forms | Document type |
| when-predicate closed keys | when-predicate |
| validation.md `###` rule titles | Validation rule |
| digest / `sha256:` form | Digest / Document key |
| namespace prefixes `x-ctier-*` / `x-consequence-*` | Namespace |
| ADR-0009 catalogue rows | Document type |
| otherwise | Unclassified |

Class cardinality is the number of distinct class labels
actually assigned. The human sweep used 33 labels; this
script's label set is allowed to differ.

## Requirement sentence (strict / lenient pair)

The script reports **two** answers for every row. Do not
collapse them. Do not retune either rule toward the recorded
22.

### Strict (the strict harvest; unchanged)

**Yes** if and only if, in prose markdown from the corpus
(fenced code blocks removed), some paragraph or table row
contains both:

- the identifier as a whole-token match (word-boundary /
  backtick / bold aware), and
- a normative keyword: `MUST`, `MUST NOT`, `SHALL`,
  `SHALL NOT`, or `REQUIRED` (RFC 2119 style, uppercase)

**No** when the identifier appears only in JSON Schema,
YAML components, or non-normative prose (no keyword).

Schema-only is never a strict requirement sentence
(the recorded hand inventory).

### Lenient (the lenient-rule pass)

**Yes** if strict is Yes, **or** any of the following fires:

1. **Class-coverage.** A requirement stated about a class
   covers a member identifier when the requirement names the
   class by its own name or by a pattern the member matches,
   its obligation is satisfiable per member, and nothing in
   the requirement or its scope excludes that member.
2. **Titled-section body.** An identifier that is a section
   title or a numbered list label (`Requirement N`) is
   covered when that section/item body contains uppercase
   `MUST` / `SHALL` / `REQUIRED`, even if the body does not
   repeat the title token. (Forced by titled validation-rule
   and deployment-requirement cases in the hand/script
   disagreement; the class-coverage formulation alone does
   not reach them.)
3. **Requirement-like prose.** A paragraph or titled field /
   validation-rule section that names the identifier states
   an obligation, prohibition, contradiction, closed
   membership, ordering, equality, or field-contract norm in
   ordinary English (including lowercase must/shall/required,
   bold normative leads, `Required` tables) without uppercase
   RFC 2119 keywords.

Lenient closes are itemised by **primary** rule in priority
order (class-coverage → titled-section-body →
requirement-like-prose). Overlaps are also recorded; their
counts may sum above the strict→lenient gap.

The back-compat field `no_requirement_sentence` equals the
**strict** count.

This is still a mechanical proxy. The recorded hand inventory said a reader
is still needed; disagreement with the human column is
expected and recorded. Lenient is **not** tuned to reproduce
the recorded 22.

## "Stated under a different name"

Mechanical proxy for validation.md's fourth figure:

- has a requirement sentence (**Yes** above), and
- has **no** heading / bold title whose visible text starts
  with the identifier (or `` `identifier` `` / **`identifier`**)

The recorded hand inventory's three (C2, C13, `refuse-provisioning`) were a
reader judgment after the fact; the proxy will not match
exactly.

## Totals shape (same as validation.md 1.16.0)

| Total | Meaning |
|---|---|
| identifiers | distinct inventory rows |
| classes | distinct class labels |
| no requirement sentence | rows with requirement = No |
| stated under a different name | proxy above |

## What this script does not do

- It does not edit the specification or `validation.md`
- It does not tune thresholds to force 195 / 33 / 22 / 3
- It does not recount engine restatements (the recorded restatement totals) —
  that remains a document recount
- It does not close the response-identifier set (1.24.0) —
  that remains a hand intersect of the recorded hand inventory vs README
