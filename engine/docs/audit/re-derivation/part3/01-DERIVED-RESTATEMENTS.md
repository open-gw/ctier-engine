# Part 3 — Derived restatement recount (this run)

**Written:** 2026-11-03T00:45:00Z — after `00-PROCEDURE.md`,
before opening finding 46's totals / invented list.

**Companion freeze**

| Item | Value |
|---|---|
| Conversion commit | `730cac6df87c23f175f733a6e391c268e19b2cb0` (*docs: engine documents cite criteria rather than restating them*) |
| Pre-conversion parent | `0a6b9200c126edab7d92a711e824ad4686deea05` |
| Tree | `ctier-engine-private` (public `ctier-engine` squashed the pre-state away) |
| Normative pin named in tree | engine `SPEC.md` → specification **1.15.0** |
| Editable living set | root `README.md`, `engine/docs/PRD.md`, `SOLUTION-DESIGN.md`, `DECISIONS.md`, `portability.md` |
| Left / non-editable | `engine/docs/adr/**`, `IMPLEMENTATION-PLAN.md`, `observation.md`, `make_diagrams.py` |

Method: Procedure C test on the **parent** blobs; conversion
diff used only to locate which spans the conversion touched,
then each span split into sentence / table-row / criterion
units. Artefacts under `pre-conversion/`.

---

## Count before edit (this run) — editable living set

| Document | Restatements (this run) |
|---|---:|
| `README.md` (root) | **10** |
| `engine/docs/PRD.md` | **15** |
| `engine/docs/SOLUTION-DESIGN.md` | **24** |
| `engine/docs/DECISIONS.md` | **4** |
| `engine/docs/portability.md` | **21** |
| **R total** | **74** |

Arithmetic: 10+15+24+4+21 = **74**. Closes.

### README.md (10)

1. "Each rung is independently useful."
2–6. Adoption-ladder rows Levels 0–4 (five rows).
7. Fragment mode / C11 bounded per target.
8. Level 2 does not satisfy C7.
9. Three deployment requirements ctier does not enforce (1)(2)(3).
10. Durability of `[ctier-decision]` log lines (requirement 4).

### PRD.md (15)

1. v1 claim: enforce without a human ever occupying the path.
2. Conformance preamble ("satisfies all of the following…").
3–15. **C1–C13** requirement paragraphs (13).

### SOLUTION-DESIGN.md (24)

1–13. Criteria table rows C1–C13.
14. C11 attack / strip narrative.
15. Blockquote MUST ignore unknown `x-ctier-*`.
16–20. Adoption-ladder rows Levels 0–4.
21. "Three record types… C8 warns…"
22–24. Decisions / Attempts / Outcomes bullets (C6/C8/C10 surface).

### DECISIONS.md (4)

1. New conformance criterion **C13** bullet (composed digest).
2. Naming / C11 prefix paragraph tied to the criterion surface.
3. "Belongs in the PRD next to C4…" obligation pointer.
4. Ranking table row for **C13**.

(Excluded as too fragmentary to be its own restatement unit:
a mid-sentence "stability argument C7 already makes…" edit
crumb.)

### portability.md (21)

1–2. Matrix rows: default tier undeclared; bounds escalation.
3. Fragment mode not C11-conformant (early).
4. Escalated value / C3 generator knowledge.
5–7. Matrix rows: governed-set refusal vs C2; header removal /
   C11; composition field / C13.
8. "applies and C11 strips forged…"
9. Section title "What ctier requires of the deployment".
10. Section intro (three deployment conditions).
11–13. Numbered requirements 1–3.
14. Fragment mode not C11-conformant (later reprise).
15. C12 scoped to governed set.
16–17. C2 undeclared default / path-not-in-composition.
18. C11 strip-set / specify-and-strip unavailable.
19–21. C7 HMAC / Level 2 / minted id / MUST-scope open question
    (three obligation-bearing sentences in the C7 cluster).

---

## Invented (this run)

Relative to specification **1.15.0** (engine pin) / maturity
note that **C1, C3, C4** lacked a stated requirement letter in
the candidate (C3's body existed under another title — see
Part 4), the editable set asserts full letters for at least:

| # | Claim (engine docs) | Why invented / ahead |
|---|---|---|
| 1 | PRD **C1** letter | candidate maturity: C1 never stated |
| 2 | PRD **C4** letter | candidate maturity: C4 never stated |
| 3 | PRD human-never-in-path v1 claim | same C4 subject, ahead of letter |
| 4 | SD table **C1** row | same |
| 5 | SD table **C4** row | same |
| 6 | DECISIONS "next to C4" pointer | treats C4 as settled law |
| 7 | PRD/SD **C13** as composed-digest assignment letter | wording/role ahead of / beside candidate C13 digest-discipline title (reader: engine states a broader binding letter) |
| 8 | README/portability "deployment requirements" as if normative ctier obligations | candidate does not mint those three as named criteria |

**Invented = 8** (this run's reader partition of the 74).
Echo = 74 − 8 = 66 under this labelling.

---

## Left untouched (this run)

Hostile floor over non-editable paths at the same parent
(obligation-bearing C-references; counts are floors):

| Path | Units (this run) |
|---|---:|
| `adr/0001-…` | 1 |
| `adr/0005-…` | 2 |
| `adr/0007-…` | 1 |
| `adr/0009-…` | 3 (deduped table/C13 noise) |
| `IMPLEMENTATION-PLAN.md` | 3 |
| `observation.md` | 1 |
| `make_diagrams.py` | 1 |
| **Left** | **12** |

**Left = 12** on this floor. A thirteenth unit is plausible
(second ADR-0009 table row / plan line) but was not cleanly
separable without double-counting — recorded as **12 (floor;
possible 13)**.

---

## Summary (this run)

| Quantity | This run |
|---|---:|
| R (editable) | **74** |
| Invented | **8** |
| Left | **12** (floor; possibly 13) |

---

## Next

`02-DIFF.md` after opening finding 46 totals.
