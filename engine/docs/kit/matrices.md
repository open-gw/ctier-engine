# Kong and APISIX against conformance-kit/1.1

The tables are the runs. Each row is
a case from the runner's `--out` file
in `runs/`. A pass has no reason
field. A skip's reason is the string
the runner emitted, in one of two
columns. Those columns do not share
a cell.

`Not this level` is only
`not applicable at this level`.
The case does not apply at the level
of that file. An empty cell in that
column means the case is eligible
at that level.

`Not observed here` is a skip of an
eligible case. In these files the
string is
`covered at generation rather than runtime`.
`requires a capability this target lacks`
would use the same column. It is not
in these eight files.

C14 is Level 3 only. Both Level 2
files record `not applicable at this level`
on `c14-w1-pending-publishes-no-credential`.
Both Level 3 files record that case
`passed`, with both skip columns
empty.

Level 2 shows six skips. Five are
not this level:
`c4-w1-withhold-has-no-poll-url`,
`c5-withheld-caller-is-released`,
`c6-execute-is-the-approved-bytes`,
`c7-caller-does-not-choose-the-identifier`,
`c14-w1-pending-publishes-no-credential`.
One is not observed here:
`c13-assignment-does-not-apply-to-another-composition`.
The six is not six of one kind.

Level 3 shows two skips. One is not
this level:
`c4-w2-level-2-class-3-is-a-decision`.
One is the same C13 generation skip.
C14 is not among them.

Current tables are the dated files
from 24 October 2026, after the
observer fix and after kit commit
`e594696` (hop scoring). Host
`Rinus-MBP-M3.local`. The undated
files are the earlier record from
the same calendar date. They stay.
They are not deleted.

Specification 1.25.0 at
`c5c6af025a8f2baab527ebb8518dcbea13ef2058`.
Kit `conformance-kit/1.1` at
`e594696978895b3c455e385b12d1ebeb666592e6`
— the commit that produced the
post-fix runs. Generator
`fd797887d6352ffe06402780846166293980f17c`.
The generator did not change. The
observer fix is not that commit.

| Run | Current file | 24 October record | Compose | Target |
|---|---|---|---|---|
| Kong Level 3 | `runs/kong-level-3-e594696-2026-10-24.yaml` | `runs/kong-level-3-pre-e594696.yaml` | `targets/kong/live/compose.yaml` | `kong:3.9` |
| Kong Level 2 | `runs/kong-level-2-e594696-2026-10-24.yaml` | `runs/kong-level-2-pre-e594696.yaml` | `targets/kong/live/compose.yaml` | `kong:3.9` |
| APISIX Level 3 | `runs/apisix-level-3-e594696-2026-10-24.yaml` | `runs/apisix-level-3-pre-e594696.yaml` | `targets/apisix/live/compose.yaml` | `apache/apisix:3.13.0-debian` |
| APISIX Level 2 | `runs/apisix-level-2-e594696-2026-10-24.yaml` | `runs/apisix-level-2-pre-e594696.yaml` | `targets/apisix/live/compose.yaml` | `apache/apisix:3.13.0-debian` |

When these runs were taken, the committed
`keycloak-rsa.json` was a placeholder and
Keycloak would not start on it. These runs
used a local PKCS#8 keypair that is not in
the result files.

A result is meaningful only against
`conformance-kit/1.1`.

---

## Cases and criteria

Eighteen cases. Fourteen criteria
appear in them. C4 has three cases.
C10 has three cases. Every other
criterion in the kit has one case.
C8 and C15 have no case. The
specification's sixteen criteria are
not sixteen rows.

---

## Counts

September writeup, then the undated
24 October files, then the dated
files. Pass/fail/skip/inconclusive.
September APISIX rows were stored
without an inconclusive count.

| Run | September | 24 October files | Current |
|---|---|---|---|
| Kong Level 3 | 15/0/2/1 | 15/0/2/1 | 15/0/2/1 |
| Kong Level 2 | 11/0/6/1 | 11/0/6/1 | 11/0/6/1 |
| APISIX Level 3 | 16/0/2 | 15/1/2/0 | 16/0/2/0 |
| APISIX Level 2 | 12/0/6 | 12/0/6/0 | 12/0/6/0 |

The 24 October APISIX Level 3 file
is the failing record.
`c7-caller-does-not-choose-the-identifier`
failed. Status 200. The runner's
failure is
`observer.present.idempotency-key`,
expected present, observed null.
That row is repeated below. It is
not removed.

---

## Level 3, Kong and APISIX

The stored aggregates differ by one
inconclusive. That row is C12,
`c12-unassigned-is-refused-undetermined`.
Kong observed status 404. The runner's
reason is `target response does not distinguish conformance from what the kit cannot see`. APISIX passed the
same case. That difference is item 3
in `divergence.md`.

The 24 October files add a second
difference. C7 failed on APISIX
Level 3 and passed on Kong Level 3.
C7 is not on the permitted-divergence
list. The list's C7 note is the
Level 2 skip, which both targets
took. A Level 3 miss is a failure.
The dated files do not repeat that
miss. `divergence.md` was not edited
and C7 was not added to the list.

An inconclusive is not a skip. Kong's
C12 reason stays in the prose above.
It is not placed in either skip
column.

---

## Kong Level 3

Current file
`runs/kong-level-3-e594696-2026-10-24.yaml`.
The 24 October file
`runs/kong-level-3-pre-e594696.yaml` has the
same rows. 15/0/2/1.

| Criterion | Case | Outcome | Not this level | Not observed here |
|---|---|---|---|---|
| C1 | `c1-classified-refuse-does-not-execute` | passed |  |  |
| C2 | `c2-undeclared-is-highest-class-refuse` | passed |  |  |
| C3 | `c3-bound-crossing-is-the-higher-class` | passed |  |  |
| C4 | `c4-w1-withhold-has-no-poll-url` | passed |  |  |
| C4 | `c4-w2-level-2-class-3-is-a-decision` | skipped | not applicable at this level |  |
| C4 | `c4-w3-highest-class-holds-nothing` | passed |  |  |
| C5 | `c5-withheld-caller-is-released` | passed |  |  |
| C6 | `c6-execute-is-the-approved-bytes` | passed |  |  |
| C7 | `c7-caller-does-not-choose-the-identifier` | passed |  |  |
| C9 | `c9-highest-class-names-no-resume` | passed |  |  |
| C10 | `c10-execute-has-a-decision` | passed |  |  |
| C10 | `c10-highest-class-has-a-decision` | passed |  |  |
| C10 | `c10-undeclared-has-a-decision` | passed |  |  |
| C11 | `c11-inbound-tier-is-not-honoured` | passed |  |  |
| C12 | `c12-unassigned-is-refused-undetermined` | inconclusive |  |  |
| C13 | `c13-assignment-does-not-apply-to-another-composition` | skipped |  | covered at generation rather than runtime |
| C14 | `c14-w1-pending-publishes-no-credential` | passed |  |  |
| C16 | `c16-unknown-prefix-name-is-absent` | passed |  |  |

---

## Kong Level 2

Current file
`runs/kong-level-2-e594696-2026-10-24.yaml`.
The 24 October file
`runs/kong-level-2-pre-e594696.yaml` has the
same rows. 11/0/6/1.

| Criterion | Case | Outcome | Not this level | Not observed here |
|---|---|---|---|---|
| C1 | `c1-classified-refuse-does-not-execute` | passed |  |  |
| C2 | `c2-undeclared-is-highest-class-refuse` | passed |  |  |
| C3 | `c3-bound-crossing-is-the-higher-class` | passed |  |  |
| C4 | `c4-w1-withhold-has-no-poll-url` | skipped | not applicable at this level |  |
| C4 | `c4-w2-level-2-class-3-is-a-decision` | passed |  |  |
| C4 | `c4-w3-highest-class-holds-nothing` | passed |  |  |
| C5 | `c5-withheld-caller-is-released` | skipped | not applicable at this level |  |
| C6 | `c6-execute-is-the-approved-bytes` | skipped | not applicable at this level |  |
| C7 | `c7-caller-does-not-choose-the-identifier` | skipped | not applicable at this level |  |
| C9 | `c9-highest-class-names-no-resume` | passed |  |  |
| C10 | `c10-execute-has-a-decision` | passed |  |  |
| C10 | `c10-highest-class-has-a-decision` | passed |  |  |
| C10 | `c10-undeclared-has-a-decision` | passed |  |  |
| C11 | `c11-inbound-tier-is-not-honoured` | passed |  |  |
| C12 | `c12-unassigned-is-refused-undetermined` | inconclusive |  |  |
| C13 | `c13-assignment-does-not-apply-to-another-composition` | skipped |  | covered at generation rather than runtime |
| C14 | `c14-w1-pending-publishes-no-credential` | skipped | not applicable at this level |  |
| C16 | `c16-unknown-prefix-name-is-absent` | passed |  |  |

---

## APISIX Level 3

Current file
`runs/apisix-level-3-e594696-2026-10-24.yaml`.
16/0/2/0. C7 passed.

| Criterion | Case | Outcome | Not this level | Not observed here |
|---|---|---|---|---|
| C1 | `c1-classified-refuse-does-not-execute` | passed |  |  |
| C2 | `c2-undeclared-is-highest-class-refuse` | passed |  |  |
| C3 | `c3-bound-crossing-is-the-higher-class` | passed |  |  |
| C4 | `c4-w1-withhold-has-no-poll-url` | passed |  |  |
| C4 | `c4-w2-level-2-class-3-is-a-decision` | skipped | not applicable at this level |  |
| C4 | `c4-w3-highest-class-holds-nothing` | passed |  |  |
| C5 | `c5-withheld-caller-is-released` | passed |  |  |
| C6 | `c6-execute-is-the-approved-bytes` | passed |  |  |
| C7 | `c7-caller-does-not-choose-the-identifier` | passed |  |  |
| C9 | `c9-highest-class-names-no-resume` | passed |  |  |
| C10 | `c10-execute-has-a-decision` | passed |  |  |
| C10 | `c10-highest-class-has-a-decision` | passed |  |  |
| C10 | `c10-undeclared-has-a-decision` | passed |  |  |
| C11 | `c11-inbound-tier-is-not-honoured` | passed |  |  |
| C12 | `c12-unassigned-is-refused-undetermined` | passed |  |  |
| C13 | `c13-assignment-does-not-apply-to-another-composition` | skipped |  | covered at generation rather than runtime |
| C14 | `c14-w1-pending-publishes-no-credential` | passed |  |  |
| C16 | `c16-unknown-prefix-name-is-absent` | passed |  |  |

## APISIX Level 3, 24 October record

File `runs/apisix-level-3-pre-e594696.yaml`. Kept.
15/1/2/0.

| Criterion | Case | Outcome | Not this level | Not observed here |
|---|---|---|---|---|
| C1 | `c1-classified-refuse-does-not-execute` | passed |  |  |
| C2 | `c2-undeclared-is-highest-class-refuse` | passed |  |  |
| C3 | `c3-bound-crossing-is-the-higher-class` | passed |  |  |
| C4 | `c4-w1-withhold-has-no-poll-url` | passed |  |  |
| C4 | `c4-w2-level-2-class-3-is-a-decision` | skipped | not applicable at this level |  |
| C4 | `c4-w3-highest-class-holds-nothing` | passed |  |  |
| C5 | `c5-withheld-caller-is-released` | passed |  |  |
| C6 | `c6-execute-is-the-approved-bytes` | passed |  |  |
| C7 | `c7-caller-does-not-choose-the-identifier` | failed |  |  |
| C9 | `c9-highest-class-names-no-resume` | passed |  |  |
| C10 | `c10-execute-has-a-decision` | passed |  |  |
| C10 | `c10-highest-class-has-a-decision` | passed |  |  |
| C10 | `c10-undeclared-has-a-decision` | passed |  |  |
| C11 | `c11-inbound-tier-is-not-honoured` | passed |  |  |
| C12 | `c12-unassigned-is-refused-undetermined` | passed |  |  |
| C13 | `c13-assignment-does-not-apply-to-another-composition` | skipped |  | covered at generation rather than runtime |
| C14 | `c14-w1-pending-publishes-no-credential` | passed |  |  |
| C16 | `c16-unknown-prefix-name-is-absent` | passed |  |  |

The C7 outcome is `failed`. The file
has no `reason` on that case. The
failure entry is `observer.present.idempotency-key` expected `present`, observed `null`; status 200.

---

## APISIX Level 2

Current file
`runs/apisix-level-2-e594696-2026-10-24.yaml`.
The 24 October file
`runs/apisix-level-2-pre-e594696.yaml` has the
same rows. 12/0/6/0.

| Criterion | Case | Outcome | Not this level | Not observed here |
|---|---|---|---|---|
| C1 | `c1-classified-refuse-does-not-execute` | passed |  |  |
| C2 | `c2-undeclared-is-highest-class-refuse` | passed |  |  |
| C3 | `c3-bound-crossing-is-the-higher-class` | passed |  |  |
| C4 | `c4-w1-withhold-has-no-poll-url` | skipped | not applicable at this level |  |
| C4 | `c4-w2-level-2-class-3-is-a-decision` | passed |  |  |
| C4 | `c4-w3-highest-class-holds-nothing` | passed |  |  |
| C5 | `c5-withheld-caller-is-released` | skipped | not applicable at this level |  |
| C6 | `c6-execute-is-the-approved-bytes` | skipped | not applicable at this level |  |
| C7 | `c7-caller-does-not-choose-the-identifier` | skipped | not applicable at this level |  |
| C9 | `c9-highest-class-names-no-resume` | passed |  |  |
| C10 | `c10-execute-has-a-decision` | passed |  |  |
| C10 | `c10-highest-class-has-a-decision` | passed |  |  |
| C10 | `c10-undeclared-has-a-decision` | passed |  |  |
| C11 | `c11-inbound-tier-is-not-honoured` | passed |  |  |
| C12 | `c12-unassigned-is-refused-undetermined` | passed |  |  |
| C13 | `c13-assignment-does-not-apply-to-another-composition` | skipped |  | covered at generation rather than runtime |
| C14 | `c14-w1-pending-publishes-no-credential` | skipped | not applicable at this level |  |
| C16 | `c16-unknown-prefix-name-is-absent` | passed |  |  |
