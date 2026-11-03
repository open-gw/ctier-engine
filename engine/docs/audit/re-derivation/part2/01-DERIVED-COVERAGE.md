# Part 2 — Derived coverage (this run)

**Written:** 2026-11-03T00:32:00Z — after `00-PROCEDURE.md`,
before opening SEALED-KEY / derived headline coverage totals.

**Source run:** Part 1 `01-script-inventory.json` at pin
`0a997321234e5f6f6184b7449a241c3d30a19520` (I=239).

---

## Strict / lenient (this run)

| Quantity | This run |
|---|---:|
| Strict no-requirement (`S`) | **145** |
| Lenient no-requirement (`L`) | **46** |
| Gap (`S − L`) | **99** |

### Gap primary-rule composition (this run)

From `summary.lenient_closes_by_rule_counts` on the same JSON
(primary rule per closed row; counts sum to the gap):

| Primary rule | Count |
|---|---:|
| class-coverage | **46** |
| titled-section-body | **6** |
| requirement-like-prose | **47** |
| **Sum** | **99** |

Arithmetic check: 46 + 6 + 47 = 99 = gap. **Closes.**

---

## Agreed hand∩script `no`

**Not re-derivable in this run.**

Reason: the intersection needs the hand requirement column
(human-22 set). Part 1 could not re-derive the hand inventory;
human 22 is explicitly out of scope. No independent agreed
count without that column.

---

## Lenient residual composition (recorded shape 16+28+2)

**`L = 46` re-derived** (above).

The partition of those 46 into agreed-hand-no / script-only /
newly harvested concepts **not re-derivable** without the hand
`no` column and the task-91 script-only bucket list as prior
answers. Not reconstructed here.

---

## Human 22

**Not re-derivable** (task instruction; reader judgment).
Not attempted.

---

## Next

`02-DIFF.md` after opening recorded / sealed coverage figures.
