# Part 2 — Coverage counts procedure

**Written:** 2026-11-03T00:31:00Z — after Part 1 derived
inventory; **before** opening
`engine/docs/audit/second-analyst/SEALED-KEY/` totals or
`identifier-pass/derived/` headline totals for this part's
diff.

---

## Goal

Re-derive, under Procedure B / COUNTING-RULE coverage rules:

- strict no-requirement count
- lenient no-requirement count
- strict→lenient gap primary-rule composition
  (class-coverage / titled-section-body / requirement-like-prose)
- agreed hand∩script `no` (if re-derivable)
- lenient residual composition (if re-derivable)

**Human 22:** explicitly **not re-derivable** — do not attempt
(reader judgment column of finding 43; not a written rule).

---

## Rules to apply (may read; totals forbidden until after)

1. Procedure B step 4 class-coverage + titled-section body
   (`procedure-identifier-pass.md`, `coverage-rules.md`).
2. COUNTING-RULE strict / lenient pair
   (`COUNTING-RULE.md`):
   - **Strict:** whole-token co-occurrence with uppercase
     `MUST` / `MUST NOT` / `SHALL` / `SHALL NOT` / `REQUIRED`
     in non-fenced prose.
   - **Lenient:** strict **or** class-coverage **or**
     titled-section body **or** requirement-like prose.
3. Task 92 script `identifier_pass.py` may be used to *apply*
   these rules mechanically on the frozen pin inventory.

Inventory input for this run: the Part 1 written-rule
inventory at pin `0a99732` (script harvest). The hand 195-row
set was **not** independently re-derived in Part 1; coverage
figures from the written rule therefore attach to the **239**
identifier written-rule inventory, not to a reconstructed
hand table.

---

## Steps

1. Confirm Part 1 `01-DERIVED-INVENTORY.md` exists.
2. Using the Part 1 script JSON at the pin, compute:
   - `S` = rows with `requirement_sentence_strict = false`
   - `L` = rows with `requirement_sentence_lenient = false`
   - gap = `S − L`
   - primary-rule close counts among rows strict-no and
     lenient-yes (class-coverage, titled-section-body,
     requirement-like-prose), summing to the gap.
3. **Agreed 16:** requires the hand `no`-requirement set
   intersected with script strict `no`. The hand `no` set is
   the human-22 column — declared not re-derivable. Record
   agreed-16 as **not re-derivable** unless an independent
   hand column exists without opening sealed totals.
4. **Lenient residual composition** (recorded shape
   agreed + script-only + new): likewise needs the hand
   column and task-91 bucket membership. If those are only
   available as prior sealed/narrative answers, mark
   composition **not re-derivable** beyond `L` itself.
5. Write `01-DERIVED-COVERAGE.md` with this run's numbers.
6. Only then open sealed / recorded coverage figures and
   write `02-DIFF.md`.

---

## Outputs

| File | When |
|---|---|
| `00-PROCEDURE.md` | this file |
| `01-DERIVED-COVERAGE.md` | after run, before sealed open |
| `02-DIFF.md` | after sealed / recorded open |
