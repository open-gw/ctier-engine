# Replication package — audit case study

Public package for re-running (and checking) the desk sweeps
behind the companion paper's method / data-availability path.
It ships **re-derived** headline figures from an ordered
look-last pass against the pin below — not a one-shot claim
alone.

**Pin.** Corpus under [`corpus/`](corpus/) is frozen at
`0a997321234e5f6f6184b7449a241c3d30a19520` (spec **1.16.0**
identifier-attach). Windows and tip: [`PIN-CONTEXT.md`](PIN-CONTEXT.md).
The living tip the paper reports against is specification
**1.25.0**; the criteria-audit sweep window is **1.8.0 → 1.15.0**.

**Hard fence.** No author findings files live in this package.
No sealed answer-key contents. No private repository paths.
Do not open [`../audit/second-analyst/SEALED-KEY/`](../audit/second-analyst/SEALED-KEY/)
until a second-analyst run is complete (see
[`SECOND-ANALYST.md`](SECOND-ANALYST.md)).

---

## Procedure A is not runnable by a stranger

**State this first.** Procedure A
([`procedures/procedure-criteria-audit.md`](procedures/procedure-criteria-audit.md))
can be *followed*, but it cannot be *executed to a unique
verdict table* by a stranger with this package alone. Two
residual judgements remain:

1. **Span selection** for the protected-outcome field (which
   contiguous corpus span states the outcome the criterion is
   meant to protect, or `UNSTATED`).
2. **Test 1** — whether there is a "plausible implementation"
   that achieves that quoted outcome yet fails the letter of
   the requirement sentence.

Those steps are reader judgment. Two hostile readers can
disagree without either violating the procedure. A stranger
can still produce *a* criteria partition and a coverage-style
count under Procedures B/C and the scripts; they cannot claim
Procedure A's verdicts are uniquely determined by this text.

---

## Contents

| Path | Role |
|---|---|
| [`corpus/`](corpus/) | Vendored normative tree at the pin |
| [`PIN-CONTEXT.md`](PIN-CONTEXT.md) | Pin, tip, 1.8.0→1.15.0 window |
| [`procedures/`](procedures/) | Procedures A / B / restatement (+ timing form) |
| [`coverage-rules.md`](coverage-rules.md) | Two rules; third pattern not adopted; 43-of-44 |
| [`identifier-inventory.md`](identifier-inventory.md) | Identifier + class at the pin |
| [`scripts/`](scripts/) | Mechanised harvest + recorded outputs |
| [`re-derivation/`](re-derivation/) | Ordered re-derivation + master diff table |
| [`SECOND-ANALYST.md`](SECOND-ANALYST.md) | Pointer to the blind coverage pack |
| [`ZENODO-METADATA.md`](ZENODO-METADATA.md) | Deposit prep only (no deposit minted here) |
| [`CONTAMINATION.md`](CONTAMINATION.md) | What a stranger-read removed |

---

## Reproducible exactly

These figures re-derive from the written counting rule / script /
vendored pre-conversion tree without further reader judgment
(beyond applying the stated rules as written):

- **Strict no-requirement** — 145 (at pin)
- **Lenient no-requirement** — 46 (at pin)
- **Strict−lenient gap** — 99, primary class-coverage **46** +
  titled-section-body **6** + requirement-like-prose **47**
- **Written-rule annex inventory** — 239 identifiers / 34 classes
  (COUNTING-RULE / mechanised harvest at pin; not the hand 195/33)
- **Restatements R (editable living set)** — 74
- **Invented-requirement count** — 8
- **Criteria set size** — 12 (= 9 stated + 2 never + 1 other-name)
- **Mechanism-where-property (seven of nine)** — 7

See [`re-derivation/05-DIFF-TABLE.md`](re-derivation/05-DIFF-TABLE.md)
and [`scripts/recorded-outputs/`](scripts/recorded-outputs/).

---

## Reproducible approximately

Name the figure **and** the judgement step that keeps the
result from being unique:

- **Left (restatement non-editable floor)** — recorded 13;
  re-derived **12**. Judgement: hostile unitisation of
  non-editable companion spans (ADR / plan / observation /
  diagrams). Δ −1 on re-derivation.
- **Per-row coverage under Procedure B** — rules are written;
  borderline class membership and "what the class owes" still
  require a reader. Scripted strict/lenient above are exact;
  a hand sheet need not match every row.
- **Criteria mechanism/property verdicts (Procedure A)** — see
  the plain statement above (span selection; Test 1 plausible
  implementation).
- **Invented-requirement membership labels** — count 8 matches;
  which eight labels a reader names can differ while the count
  holds.
- **43-of-44 under the two coverage rules** — two rules reach
  43 of the 44 script-vs-hand "covered by class/title" cases;
  the holdout is criterion-linkage (`Authorization` under a
  named criterion), recorded as reader judgment and **not**
  adopted as a third rule ([`coverage-rules.md`](coverage-rules.md)).

---

## Not reproducible

- **Hand identifiers / classes (195 / 33)** — the hand harvest
  boundary and 33-class catalogue were never written as a
  counting rule; only a finished answer table exists elsewhere.
  The written-rule annex at the pin is **239 / 34**, which is
  not that hand set.
- **Human no-requirement (22)** — reader judgment; no
  mechanical path; not attempted in the re-derivation.
- **Agreed no (16)** — intersection of script `no` with the
  hand `no` column; needs the unreproducible hand column.
- **Lenient residual partition 16 + 28 + 2** — residual
  **total** 46 re-derives; the three-way split needs the hand
  column plus a prior script-only disagreement bucket that is
  not a stranger-facing counting rule in this package.

---

## How to run the mechanised parts

```bash
# from this directory; point --repo at a public open-gw/ctier checkout
python3 scripts/identifier_pass.py 0a997321234e5f6f6184b7449a241c3d30a19520 \
  --repo /path/to/ctier \
  --json /tmp/inventory.json \
  --md /tmp/inventory.md
```

Recorded outputs at the pin (and tip) live under
[`scripts/recorded-outputs/`](scripts/recorded-outputs/).
Invocations and expected summaries:
[`scripts/README.md`](scripts/README.md).

Procedure B's human obligation columns are not replaced by
the script. Procedure C needs a named companion corpus (the
re-derivation vendored its pre-conversion tree under
`re-derivation/part3/pre-conversion/`).

---

## Relation to other public packs

| Pack | Path | Relation |
|---|---|---|
| Sweep-method procedures (earlier) | [`../audit/replication/`](../audit/replication/) | Source wording for A/B/C; this package is the case-study assembly |
| Identifier-pass tooling | [`../audit/identifier-pass/`](../audit/identifier-pass/) | Upstream of `scripts/` |
| Re-derivation (ordered) | [`../audit/re-derivation/`](../audit/re-derivation/) | Upstream of `re-derivation/` |
| Second-analyst blind pack | [`../audit/second-analyst/`](../audit/second-analyst/) | Pointer only; sealed key stays sealed |
