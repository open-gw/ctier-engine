# Replication package — sweep method

This directory is the public replication package for the three
cheap desk sweeps described in the paper's method / data-
availability path: a **criteria audit** (mechanism or
property?), an **identifier pass**, and a **restatement
conversion** on companion implementation documents.

It is enough to *prepare* a blind run. It deliberately does
**not** contain results against any candidate. A coding agent
with this repository's history is the opposite of blind; do
not treat an in-repo rehearsal as the external replication.

---

## Contents

| Path | Role |
|---|---|
| [`procedure-criteria-audit.md`](procedure-criteria-audit.md) | Procedure A — criteria audit |
| [`procedure-identifier-pass.md`](procedure-identifier-pass.md) | Procedure B — identifier pass |
| [`procedure-restatement-conversion.md`](procedure-restatement-conversion.md) | Procedure C — restatement conversion |
| [`timing-form.md`](timing-form.md) | Start/stop, files read, tooling, questions asked |
| [`candidates.md`](candidates.md) | Proposed public normative targets (size/subject only) |

---

## Mechanised identifier helper (task 89)

A scripted harvest for Procedure B lives at:

[`../identifier-pass/`](../identifier-pass/)

Use it as an annex and recording aid after freezing the
candidate pin. It does **not** rewrite the human obligation
rules in Procedure B and must not be tuned mid-run to match
a remembered total. If the helper is unavailable for any
reason, run Procedure B by hand from
[`procedure-identifier-pass.md`](procedure-identifier-pass.md).

---

## Where recorded results live

| Kind | Location |
|---|---|
| This package (procedures, form, candidate list) | **Public** `ctier-engine` → `engine/docs/audit/replication/` |
| Mechanised identifier inventories (when landed) | **Public** `ctier-engine` → `engine/docs/audit/identifier-pass/` |
| Blind-run outputs (filled timing forms, tables) | Deposit as the paper's data-availability statement names; default suggestion: a `results/` tree beside this README or a Zenodo annex. Do not commit blind-run tables into this package until the external run exists. |
| Author-side task findings (preparation notes) | **Private** `ctier-engine-private` → `engine/docs/findings/90.md` (and related). Not required to execute the procedures. |

Historical sweeps that motivated these procedures (not inputs
to a blind run): public `open-gw/ctier` `docs/findings/25–42`,
`43`, `57`, `59`; engine `docs/findings/46`; accounting prose
in `spec/validation.md`.

---

## How to run (external reader)

1. Pick a candidate from [`candidates.md`](candidates.md) (or
   another public normative spec of similar bulk). Pin it.
2. Copy [`timing-form.md`](timing-form.md) once per procedure.
3. Execute A, then B, then C (C only if you declare a companion
   corpus). Do not read prior findings for that candidate.
4. File the filled forms and output tables where the paper's
   data-availability statement points.

**Do not** start from this repository's private findings and
work backwards to the counts. The procedures are the method;
the historical counts are one document's outcome.
