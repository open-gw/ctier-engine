# Identifier-pass counting rule

This is the rule the mechanised script implements.
It is an honest reading of finding 43's "whether this check
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
  or prose (finding 43 excluded example-only names from the
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
the rule does not special-case them away. Finding 43 did not
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
| header `name` / headers.md heading | Header |
| `X-*` alias called out as alias in headers.md | Header alias |
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

## Requirement sentence

**Yes** if and only if, in prose markdown from the corpus
(fenced code blocks removed), some paragraph or table row
contains both:

- the identifier as a whole-token match (word-boundary /
  backtick / bold aware), and
- a normative keyword: `MUST`, `MUST NOT`, `SHALL`,
  `SHALL NOT`, or `REQUIRED` (RFC 2119 style, uppercase)

**No** when the identifier appears only in JSON Schema,
YAML components, or non-normative prose (no keyword).

Schema-only is never a requirement sentence (finding 43).

This is a mechanical proxy for "is this sentence a
requirement". Finding 43 said a reader is still needed;
disagreement with the human column is expected and recorded.

## "Stated under a different name"

Mechanical proxy for validation.md's fourth figure:

- has a requirement sentence (**Yes** above), and
- has **no** heading / bold title whose visible text starts
  with the identifier (or `` `identifier` `` / **`identifier`**)

Finding 43's three (C2, C13, `refuse-provisioning`) were a
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
- It does not recount engine restatements (finding 46) —
  that remains a document recount
- It does not close the response-identifier set (1.24.0) —
  that remains a hand intersect of finding 43 vs README
