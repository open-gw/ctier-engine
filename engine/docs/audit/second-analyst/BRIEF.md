# One-page brief — second analyst

## What the specification is

**ctier** is a consequence-tiering contract for HTTP APIs: an
OpenAPI-borne description carries governance declarations
(`x-ctier-*` extensions, criteria, overlays, ledger record
formats). The normative surface is a set of versioned documents
and the transformations between them — not a particular engine
binary. The corpus for this pack is frozen under `corpus/` at
the pin in `corpus/PIN.txt` (specification tree plus ADR-0009,
which the specification treats as part of the contract story).

You will meet RFC 2119 / BCP 14 keywords (`MUST`, `SHALL`,
`REQUIRED`, …), OpenAPI 3.x shapes, JSON Schema, and ordinary
conformance prose that states obligations without always
repeating an identifier token in the same sentence.

## What the task is

For **each** row in [`identifier-inventory.md`](identifier-inventory.md),
decide whether a requirement sentence (or, where the class owes
a definition instead, a definition) covers that identifier
under the rules in [`coverage-rules.md`](coverage-rules.md).

Record every decision on [`recording-sheet.md`](recording-sheet.md).
Fill [`timing-form.md`](timing-form.md) during the run, not
after from memory.

Do **not** re-harvest identifiers. Do **not** edit the corpus.
Do **not** open [`SEALED-KEY/`](SEALED-KEY/).

## What to do when the rules run out

1. Re-read Rule 1 and Rule 2. Check whether the class owes a
   **definition** rather than a requirement sentence.
2. If the token is only discussed under a named criterion,
   that is **reader judgment** (Pattern 3) — not a silent
   extension of class-coverage. Mark `reader-judgment` or
   `undecidable` and explain in Notes.
3. If two readings fight, pick one, record the other in Notes,
   and move on. Do not stall the sheet waiting for an author.
4. If you must ask a person or a tool with prior knowledge of
   this corpus's audit history, write the question on the
   timing form. Prefer finishing undecided rows as
   `undecidable` over seeking the "right" prior answer.

## Out of scope

Anything listed as withheld in [`README.md`](README.md). Prior
audit outcomes are not inputs.
