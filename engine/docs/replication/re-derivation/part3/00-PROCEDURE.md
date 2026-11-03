# Part 3 — Restatement recount procedure

**Written:** 2026-11-03T00:33:00Z — before opening finding
46's totals / invented list for the Part 3 diff.

---

## Goal

Re-derive companion-corpus restatement counts under
Procedure C:

- **R** = restatements in the editable living set (before edit)
- **Invented** = subset asserting obligations the candidate
  pin does not state
- **Left** = restatements found but excluded by the
  pre-declared non-editable set (ADRs / plan / observation /
  diagrams)

---

## Freeze (to establish before counting)

1. **Normative candidate pin:** ctier attach used by the
   original conversion era (spec 1.16.0 /
   `0a997321234e5f6f6184b7449a241c3d30a19520` unless git
   recorded history names a different pin — prefer the
   pin the conversion commit itself records, without reading
   its totals).
2. **Companion corpus:** public `ctier-engine` living docs
   that Procedure C treated as editable law:
   typically `engine/docs/PRD.md`, `SOLUTION-DESIGN.md`,
   `DECISIONS.md`, root `README.md`, `engine/docs/portability.md`.
3. **Historical state:** the companion tree **immediately
   before** the restatement-conversion commit (parent of the
   conversion). Tip living docs were converted afterward and
   must **not** be recounted as if they still held the
   pre-edit restatements.
4. **Non-editable / left set:** ADRs, plan, observation,
   `make_diagrams.py` (and any other paths the conversion
   run declared left) — count separately as **Left**, not in
   **R**.

---

## Restatement test (Procedure C step 2)

A sentence is a restatement if either:

- it asserts what a named criterion / requirement / profile
  of the candidate requires, in words that would become wrong
  if the candidate changed and nobody updated the companion;
  **or**
- it asserts an obligation under a candidate identifier (or
  title standing in for one) that the candidate pin does
  **not** state (`kind = invented`).

Accuracy is not a defence. Grep for `C\d+`, `MUST`, criterion
titles is an aid; hostile reading of obligation prose is
still required. Counts are floors.

---

## Steps

1. Locate the conversion commit(s) in `ctier-engine` history
   by message / path touch of the living docs — **without**
   opening the recorded restatement totals' count table.
2. Check out or `git show` the **parent** tree for:
   PRD, SOLUTION-DESIGN, DECISIONS, README, portability.
3. Walk each file; record every restatement row (file,
   section, identifier or `untitled`, kind echo|invented).
4. Sum **R** by file; sum **Invented**; list **Left** from
   the non-editable set at the same historical tip (or from
   a contemporaneous note that names left paths without
   relying on the recorded restatement totals' headline numbers).
5. Write `01-DERIVED-RESTATEMENTS.md`.
6. Only then open the recorded restatement totals and write `02-DIFF.md`.

---

## Failure modes

- If the pre-conversion companion blob is missing from git
  history: **not re-derivable** — name the missing commit /
  paths.
- If invented vs echo cannot be decided without the
  candidate pin body: load pin `0a99732` criteria text (not
  the recorded restatement totals).
- Do not sum the recorded restatement totals' published per-file table and call
  that a recount.

---

## Outputs

| File | When |
|---|---|
| `00-PROCEDURE.md` | this file |
| `01-DERIVED-RESTATEMENTS.md` | after recount |
| `02-DIFF.md` | after opening the recorded restatement totals |
