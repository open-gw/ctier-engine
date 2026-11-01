# Identifier-pass disagreement classification (task 91)

Classifies the gap between the mechanised identifier pass
(task 89, public commit `480e156`, counting rule frozen) and
finding 43 / `validation.md` at the 1.16.0 sweep.

**Does not** edit `COUNTING-RULE.md`, `identifier_pass.py`,
`validation.md`, finding 43, or the specification. Disagreement
is left standing.

| Source | Identifiers | Classes | No requirement | Different name |
|---|---:|---:|---:|---:|
| validation.md / finding 43 | 195 | 33 | 22 | 3 |
| Script @ `0a99732` | 217 | 31 | 136 | 62 (proxy) |

Pinned:

- Spec attach (1.16.0): `0a997321234e5f6f6184b7449a241c3d30a19520`
- Finding 43: `86f3565f90995c5c52abbf603cea6588d07fe1f3` (`ctier` `docs/findings/43.md`)
- Task 89 script: `480e156f77746739e7cad0c1a8d7814223433efb`

## Lead

**Bucket C has 0 members.** Every script-no / hand-yes
identifier was re-checked with the script's own
MUST-proximity rule against the 1.16.0 corpus; none have a
same-paragraph whole-token co-occurrence of the identifier
with `MUST` / `MUST NOT` / `SHALL` / `SHALL NOT` / `REQUIRED`
that the script missed.

The disagreement is therefore **not** "fix the script, hand
count stands." It is **mostly A/B**: the hand pass credited
requirements by titled-section / class-level indirection and
by requirement-like prose without RFC 2119 keywords. The
result is about how the specification is read, not about a
defect list in `identifier_pass.py`.

| Bucket | Count (of 76 script=no ∩ hand=yes) |
|---|---:|
| A — class/title indirection | 44 |
| B — prose without RFC 2119 | 32 |
| C — script defect | **0** |
| D — hand credited in error | 0 |
| Ambiguous | 0 |

Full C list: *(empty)*.

## Files

| Path | Contents |
|---|---|
| `part1-no-requirement.md` | Set-diff arithmetic; A–D classification with quotes |
| `part1-inventory.json` | Machine-readable Part 1 |
| `part2-extra-identifiers.md` | 217 vs 195 (asymmetric 62 vs 40, net +22) |
| `part3-classes.md` | 31 vs 33 |
| `part4-fourth-figure.md` | 62 vs 3; task 88 pending |

Task 90 owns `engine/docs/audit/replication/`. Untouched.
