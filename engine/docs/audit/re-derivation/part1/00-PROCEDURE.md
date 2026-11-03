# Part 1 — Inventory extraction procedure

**Written:** 2026-11-03T00:27:41Z (procedure before any
derived inventory or any opening of finding 43 /
`validation.md` identifier totals).

**Pin:** ctier `0a997321234e5f6f6184b7449a241c3d30a19520`.

**Discipline:** This file must exist and be complete before
`01-DERIVED-INVENTORY.*` is written. Recorded headline
figures (195 / 33) are opened only in `02-DIFF.md` after
derivation.

---

## Goal

Re-derive the **hand** identifier inventory boundary used by
finding 43 / the 1.16.0 attach accounting: distinct identifier
rows and distinct class strings. Task 89's mechanised totals
are a **different** procedure and are **not** the comparison
target for this part.

---

## Written sources for the harvest rule (rules only)

1. Procedure B harvest steps
   (`engine/docs/audit/replication/procedure-identifier-pass.md`
   §§Document, Steps 1–3): walk headings, RFC 2119 sentences,
   schema `enum` / `const` / `$id` / required properties, and
   named wire tokens in normative examples the prose treats as
   canonical. Assign a short class per row.
2. Identifier-pass counting rule
   (`engine/docs/audit/identifier-pass/COUNTING-RULE.md`) —
   corpus freeze and what the **mechanised** helper harvests.
   Notes that are useful as *boundary hints* without being a
   complete hand recipe:
   - Corpus: `spec/**/*.md`, `spec/schemas/*.json`,
     `spec/consequence-tiered-api.yaml`, `docs/adr/0009*`.
   - Examples do **not** mint identifiers alone.
   - HTTP method verbs that appear only as `when.method`
     enum members were **not** inventoried by finding 43
     (script keeps them; that delta is reported, not fitted).
   - Hand class cardinality was a 33-label catalogue; the
     script's labels are allowed to differ.

---

## What is **not** written down (honest limit)

Procedure B describes *how to walk* a corpus. It does **not**
publish a closed inclusion/exclusion list that yields the
exact finding-43 row set, nor a frozen 33-string class
catalogue, nor the reader decisions that kept a few
example-only tokens while dropping other schema stems.

COUNTING-RULE.md is explicitly "not a reverse-engineer of"
the hand headline and implements a **looser** harvest.

Therefore:

- If an independent run against the pin can only instantiate
  the **written** mechanised rule (or that rule plus the one
  documented HTTP-method exclusion), that run is **not** a
  re-derivation of the hand boundary.
- Reconstructing the hand set by subtracting a published
  script-vs-hand disagreement list would be reconstructing
  from the recorded answer — **forbidden** under this task.
- Recounting finding 43's finished tables would verify
  arithmetic on the answer artefact, not extract from the pin.

**Failure mode to record if it applies:** hand inventory
boundary **not re-derivable** — the inclusion/exclusion and
class-catalogue decisions that produced the hand table were
never written as a counting rule; only the finished table
exists.

---

## Steps to run (in order)

1. Freeze corpus at pin `0a99732` (full SHA above). List
   every path under the COUNTING-RULE corpus set.
2. Run the public mechanised helper
   `engine/docs/audit/identifier-pass/identifier_pass.py`
   against that pin. Save the helper's inventory and
   `I` / `K` as **written-rule** annex totals (expected to
   differ from the hand boundary).
3. Optionally apply only exclusions that are **explicitly**
   written in COUNTING-RULE / Procedure B (HTTP `when.method`
   verbs). Do **not** apply unpublished reader filters.
4. Attempt a Procedure B hand walk only to the extent the
   written steps close a set. If they do not close to a
   determinate hand inventory without reader memory of
   finding 43, stop and record **not re-derivable** with the
   missing piece named.
5. Write `01-DERIVED-INVENTORY.md` with **this run's**
   counts, class set (if any), and the not-re-derivable
   statement if applicable. Do **not** cite 195 / 33 yet.
6. Only then open recorded hand totals and write `02-DIFF.md`.

---

## Outputs

| File | When |
|---|---|
| `00-PROCEDURE.md` | this file (before run) |
| `01-DERIVED-INVENTORY.md` (+ JSON if useful) | after run, before opening recorded figures |
| `02-DIFF.md` | after opening recorded 195 / 33 |
