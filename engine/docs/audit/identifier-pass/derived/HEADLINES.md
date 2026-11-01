# Headline counts — re-derived (task 89)

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

| Count | Recorded (`validation.md`) | Script @ 1.16.0 sweep (`0a99732`) | Script @ tip (`66c509f`) | Hand recount of finding 43 tables | Agree? |
|---|---:|---:|---:|---:|---|
| Identifiers | 195 | 217 | 230 | 195 | **script no**; hand yes |
| Classes | 33 | 31 | 31 | 33 | **script no**; hand yes |
| No requirement sentence | 22 | 136 | 128 | 22 | **script no**; hand yes |
| Stated under a different name | 3 | 62 (proxy) | 65 (proxy) | 3 (C2, C13, `refuse-provisioning`) | **script no**; hand yes |

Reason script disagrees: the counting rule in
`../COUNTING-RULE.md` is the mechanised join finding 43
described (schema enums/consts/`$defs`/vocab fields + prose
titles + YAML names, MUST-proximity for requirement). It is
not the human-curated inventory. HTTP-method enum members and
other schema tokens inflate the identifier count; MUST-proximity
under-counts human "yes" rows and the different-name proxy is
far looser than the reader judgment of three. Disagreement is
left standing.

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

## Sweep vs tip (script only)

| | 1.16.0 sweep `0a99732` | tip `66c509f` |
|---|---:|---:|
| Identifiers | 217 | 230 |
| Classes | 31 | 31 |
| No requirement sentence | 136 | 128 |
| Different-name proxy | 62 | 65 |

Tip growth includes C14–C16, later response tokens, and further
validation-rule headings — expected after 1.16.0. The human
195/33/22 floor remains the finding-43 table, unchanged.
