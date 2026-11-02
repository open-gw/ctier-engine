# Second-analyst pack

Blind coverage pass for a second reader. The inventory is
fixed; the job is to apply the two coverage rules (and to
record reader judgment when those rules run out).

**Do not open [`SEALED-KEY/`](SEALED-KEY/) until the run is
complete** (every recording-sheet row filled, timing form
stopped). Opening it early ends blindness.

This pack deliberately does **not** contain prior audit
outcomes. A coding agent with this repository's history is the
opposite of blind.

---

## Contents

| Path | Role |
|---|---|
| [`BRIEF.md`](BRIEF.md) | One-page brief |
| [`coverage-rules.md`](coverage-rules.md) | Two rules + reader-judgment pattern |
| [`identifier-inventory.md`](identifier-inventory.md) | Identifier + class only |
| [`recording-sheet.md`](recording-sheet.md) | Covered / rule / sentence / notes |
| [`timing-form.md`](timing-form.md) | Clock, files read, questions asked |
| [`corpus/`](corpus/) | Vendored normative tree at the pin |
| [`corpus/PIN.txt`](corpus/PIN.txt) | Exact commit the tree was exported from |
| [`SEALED-KEY/`](SEALED-KEY/) | **Do not open before the run completes** |

---

## How to run

1. Read [`BRIEF.md`](BRIEF.md) and [`coverage-rules.md`](coverage-rules.md).
2. Confirm the corpus pin in [`corpus/PIN.txt`](corpus/PIN.txt).
   Work only under [`corpus/`](corpus/) — do not replace it with
   tip of any repository.
3. Copy or fill [`timing-form.md`](timing-form.md); start the
   clock when the first corpus file opens for judgment.
4. For each row of [`identifier-inventory.md`](identifier-inventory.md),
   fill the matching row on [`recording-sheet.md`](recording-sheet.md).
5. Stop the clock when every Covered? cell has a value.
6. Only then may a facilitator open [`SEALED-KEY/`](SEALED-KEY/).

---

## Withheld from this pack (contamination fence)

The following are **not** inputs and are not shipped here as
answer sources:

- Any count, total, percentage, or headline figure from an
  existing audit of this corpus (or of tip).
- Strict / lenient **results** (the coverage **rules** are
  included; prior yes/no columns and gap tallies are not).
- Tip or later `spec/validation.md` identifier-accounting
  prose (the vendored pin tree is the corpus; do not fetch tip
  to "check the maturity note").
- Finding 43 and its inventory tables.
- Findings 87–93 (and any private findings tree).
- The task-89 identifier-pass script, its counting rule, and
  its derived inventories / outputs.
- The response-identifier "half-miss" narrative and any other
  prior-sweep war stories about which classes were under-asked.

If you need a file that is not listed under Contents, stop and
mark the row undecidable rather than expanding the corpus from
memory or from tip.

**Do not browse sibling directories** under `engine/docs/audit/`
(or any findings tree). This pack is self-contained under
`second-analyst/`. Sibling audit material is out of scope and
would contaminate the run.
