# Headline counts — re-derived (tasks 89 / 92)

`validation.md` was not edited. Figures below are what it
states, what the mechanised script derives, and what a hand
recount of the original artefacts produces.

Pinned commits:

| Event | Spec version | Commit |
|---|---|---|
| Criteria audit opens | 1.8.0 | `b074475b4fedd35c527c4d8ba089053e5fbe8d04` (task 25) |
| Criteria audit closes | 1.15.0 | `bde94022e16493b28f595c693c7ac66d49835682` (task 42 findings) |
| Identifier pass (spec attach) | 1.16.0 | `0a997321234e5f6f6184b7449a241c3d30a19520` |
| Identifier pass (finding 43) | 1.16.0 | `86f3565f90995c5c52abbf603cea6588d07fe1f3` |
| Spec tip read for this derivation | 1.25.0 tree | `66c509f3625fced9f30f029f458b186547b06d47` |

## Part A — validation.md 1.16.0 quartet

Task 89 baseline (strict-only harvest, before task 92's three
class additions) is kept for comparison. Task 92 adds Concept /
Extension subfield / Header alias and reports a strict/lenient
pair. Neither rule is tuned toward 22.

| Count | Recorded (`validation.md`) | Script @ sweep (task 89) | Script @ sweep (task 92) | Script @ tip (task 92) | Hand (finding 43) |
|---|---:|---:|---:|---:|---:|
| Identifiers | 195 | 217 | **239** | **252** | 195 |
| Classes | 33 | 31 | **34** | **34** | 33 |
| No requirement (strict) | 22 | 136 | **145** | **137** | 22 |
| No requirement (lenient) | 22 | — | **46** | **41** | 22 |
| Stated under a different name | 3 | 62 (proxy) | 75 (proxy) | 78 (proxy) | 3 |

Agree with validation.md on the quartet: **no** (script);
hand recount of finding 43 tables still **yes** at 195/33/22/3.

### Strict → lenient gap (itemised by primary rule)

Priority: class-coverage → titled-section-body →
requirement-like-prose. Primary counts sum to the gap.

| Pin | Strict no-req | Lenient no-req | Gap | class-coverage | titled-section-body | requirement-like-prose |
|---|---:|---:|---:|---:|---:|---:|
| Sweep `0a99732` | 145 | 46 | **99** | 46 | 6 | 47 |
| Tip `66c509f` | 137 | 41 | **96** | 45 | 8 | 43 |

Lenient does **not** reproduce 22. Residual at sweep (46):
the 16 agreed hand/script `no` rows, 28 of the task-91
script-only no-req identifiers, and 2 newly harvested
concepts (`deploy-time bound`, `structural floor`). Not
tuned further.

Strict moved 136 → 145 at sweep because Part 3 added 22
identifier rows (12 Concept + 7 Extension subfield + 3
Header alias); 13 of those already have a strict MUST hit.

Finding 43's inventory tables are identical at sweep commit
and at tip (findings not rewritten): **195 / 33 / 22**.

## Part B — Response-identifier class (1.24.0 closed set)

Recorded (abstract / finding 87 pin): members **10** / found in
43 **5** / missed **5**.

Closed set at tip `spec/README.md` Response identifiers
(`status` × 6 + `agentAction` × 4):

`pending_authorization`, `agent_suspended`,
`custody_unavailable`, `unassigned`, `unauthorized`,
`provisioning_defect`, `continue_task_without_this_step`,
`halt_and_hand_off`, `retry_later`, `halt`.

| | Derived | Recorded | Agree? |
|---|---:|---:|---|
| Members | 10 | 10 | yes |
| Found in finding 43 | 5 | 5 | yes |
| Missed | 5 | 5 | yes |

Found: `pending_authorization`, `agent_suspended`,
`continue_task_without_this_step`, `halt_and_hand_off`,
`retry_later`.

Missed: `custody_unavailable`, `unassigned`, `unauthorized`,
`provisioning_defect`, `halt`.

(Script at tip classifies 10 as Response identifier and 4 as
agentAction — a related split, not this closed-set intersect.)

## Part C — Restatements / inventing requirements (finding 46)

| | Derived | Recorded | Agree? |
|---|---:|---:|---|
| Restatements converted | 74 (= 15+24+4+10+21) | 74 | yes |
| Engine-invented requirements | 8 (bullets under that heading) | 8 | yes |

Source: `engine/docs/findings/46.md` Part 1 table and
"Engine-invented requirements" list. Living documents were
converted afterward; this is a recount of the recorded
artefact, not a re-scan that expects 74 still present.

## Part D — three classes (task 92)

Harvested at sweep: **Concept** (12), **Extension subfield**
(7), **Header alias** (3). Script class cardinality is **34**
(= finding 43's 33 labels + **Unclassified**). Unclassified
does **not** empty (43 rows at sweep: HTTP methods, camelCase
stems, rule-artefact headings, …).

## Sweep vs tip (task 92 script)

| | 1.16.0 sweep `0a99732` | tip `66c509f` |
|---|---:|---:|
| Identifiers | 239 | 252 |
| Classes | 34 | 34 |
| No requirement (strict) | 145 | 137 |
| No requirement (lenient) | 46 | 41 |
| Different-name proxy | 75 | 78 |

Tip growth includes C14–C16, later response tokens, and further
validation-rule headings — expected after 1.16.0. The human
195/33/22 floor remains the finding-43 table, unchanged.
