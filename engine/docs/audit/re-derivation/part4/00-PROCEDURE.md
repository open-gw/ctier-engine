# Part 4 — Criteria partition procedure

**Written:** 2026-11-03T00:48:00Z — before opening recorded
partition headlines for the Part 4 diff (finding 42 /
maturity-note glosses that already state the arithmetic).

---

## Goal

At the **criteria-audit sweep window**, re-derive:

- **N = twelve** named criteria covered (C1–C12)
- partition: **9 stated** + **2 never stated (C1, C4)** +
  **1 under another name (C3)**
- of the nine stated: **7** mechanism-where-property
  (verdict `mechanism` or `mixed` under Procedure A)

Confirm arithmetic closes: 9+2+1 = 12; 7 ≤ 9.

If the partition does **not** close to twelve, that fact
leads the report.

---

## Freeze

1. Sweep window from task / finding history (commits, not
   totals): opened ~1.8.0, closed ~1.15.0
   (`b074475b…` … `bde94022…` per prior pin tables — verify
   by `git log` / version headers, not by reading answer
   arithmetic).
2. Corpus: candidate normative criteria set only
   (`spec/README.md`, `spec/validation.md`, and any file the
   criteria section cites). **Do not** classify from engine
   PRD letters.
3. Note: tip / later maturity prose may say "C1, C3 and C4
   never stated" while still carrying a titled C3 section —
   derive C3's status from whether a **requirement sentence
   under the C3 identifier** existed in-window vs a body
   living under another title.

---

## Steps

1. List every named criterion identifier C1–C12 (and C13+
   only if the in-window corpus presents it as a member of
   the same twelve — the audit's twelve is C1–C12).
2. For each ID, copy the requirement sentence under that
   identifier at audit-close (or mark ABSENT).
3. Classify presence:
   - **stated** — requirement sentence under its own ID
   - **never stated** — no requirement sentence for that ID
     in the candidate corpus
   - **under another name** — obligation body exists in the
     corpus but not under the C-letter title (titled
     elsewhere / untitled)
4. For each **stated** row, apply Procedure A mechanism vs
   property tests (or reuse only in-window classification
   tables that record verdicts without trusting later
   summary arithmetic — prefer re-reading the requirement
   sentences).
5. Sum: stated + never stated + under-another-name =?
   twelve. Mechanisms-or-mixed among stated =?
6. Write `01-DERIVED-PARTITION.md`.
7. Only then open recorded partition figures and write
   `02-DIFF.md`.

---

## Outputs

| File | When |
|---|---|
| `00-PROCEDURE.md` | this file |
| `01-DERIVED-PARTITION.md` | after derivation |
| `02-DIFF.md` | after opening recorded figures |
