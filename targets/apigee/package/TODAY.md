# What would actually run today

Date: 20 September 2026. Package as
shipped after 64/65. **No gap closed
yet.** Counts are from
`conformance-kit/1.1` (`cases.yaml`)
and `run_kit` skip rules — not from a
live Apigee organisation in this
repository (there is none).

Assumptions for the baseline column:

- `kit_level: "2"` (example default)
- `kit_records`, `kit_observer`,
  `kit_custody` empty
- Proxy deployed; bearer token has
  the scopes in
  `generated/authorization.yaml`
- `/estate/unknown` **not** provisioned
  as routed-but-ungoverned → C12 is
  inconclusive on bare `404`

If the proxy or token is missing, the
run never writes a result file. That
is outside these counts.

---

## Baseline (stock package, Level 2)

18 cases in kit/1.1.

| Outcome | Count | What |
|---|---:|---|
| Would **run** (pass or fail) | 6 | Status / body / pairing only |
| **Inconclusive** | 1 | C12 on bare `404` |
| **Skipped** | 11 | Level, generation, or missing capability |
| **Pass** | unknown | No Apigee org / runtime here to measure |
| **Fail** | unknown | Same |

**Ran** = 7 (6 + 1 inconclusive).
Skips are not runs.

### The six that would run

| Case | Why it can run without optional URLs |
|---|---|
| `c1-classified-refuse-does-not-execute` | Status `423`. Observer soft-check only if present. |
| `c2-undeclared-is-highest-class-refuse` | Status + body + pairing. |
| `c3-bound-crossing-is-the-higher-class` | Higher-class disposition (`403` at L2). |
| `c4-w2-level-2-class-3-is-a-decision` | Level-2 witness: `403` provisioning. |
| `c9-highest-class-names-no-resume` | Status + body + pairing. |
| `c11-inbound-tier-is-not-honoured` | Status `423`. |

### The one inconclusive

| Case | Why |
|---|---|
| `c12-unassigned-is-refused-undetermined` | Bare `404` → inconclusive (PROVISION §5). |

### The eleven skipped

| Case | Reason |
|---|---|
| `c4-w1-withhold-has-no-poll-url` | not applicable at this level |
| `c5-withheld-caller-is-released` | not applicable at this level |
| `c6-execute-is-the-approved-bytes` | not applicable at this level |
| `c7-caller-does-not-choose-the-identifier` | not applicable at this level |
| `c14-w1-pending-publishes-no-credential` | not applicable at this level |
| `c13-assignment-does-not-apply-to-another-composition` | covered at generation rather than runtime |
| `c4-w3-highest-class-holds-nothing` | requires pending (`kit_custody`) |
| `c10-execute-has-a-decision` | requires records |
| `c10-highest-class-has-a-decision` | requires records |
| `c10-undeclared-has-a-decision` | requires records |
| `c16-unknown-prefix-name-is-absent` | requires observer |

Matches `RESULT.md` (± wording):
**11 skipped** at Level 2 with empty
optional URLs.

---

## Per-gap unlock counts

From the baseline above: how many
**skipped → would run** if that gap
alone were closed (Level 2, other
optional URLs still empty). Unlock
means the case stops skipping for
capability; it does not promise pass.

| Gap (from 64) | Cases unlocked | Which | Close? |
|---|---:|---|---|
| No standalone runner | **0** | Install friction only | No |
| No Apigee deploy script | **0** | Enables any HTTP run; no skip→run | No |
| No OAuth/JWT product wiring | **0** | May turn 401/403 **fails** into runs that can pass; does not clear capability skips | No |
| Trace ≠ retrievable kit records | **3** | C10 × 3 | **Yes** — Part 2 |
| No backend observer | **1** | C16 (C1 gains a soft assert if observer present; already runs) | **Yes** — Part 2 |
| Custody host is placeholder | **1** at L2 | C4-w3 only. L3 withhold/C6/C7/C14 need a **real** approval service the tester supplies — no mock custody stand-in | Skip / declare; do not stub |
| No local Apigee runtime | **0** | Nothing to unlock in-kit; validation stays artefact + org | Declare absent |

### Combined (the two that gate)

Closing **observer + records** together
unlocks **4** cases at Level 2
(C10×3 + C16). Baseline ran 7 →
would run **11** (plus the same C12
inconclusive unless §5 is done).

Four unlocks is the threshold the task
named. Honest reading: that is still
a thin Apigee column next to Kong /
APISIX Level-2 matrices (~12 ran with
records+observer on a local rig). The
two gaps are still worth closing —
without them the kit is a status-code
checker and C10 is permanently dark.
Closing them does not invent a local
Apigee runtime or a custody mock.

### What closing cannot buy

- **L3 rows** without a real custody
  host the tester replaces and points
  `kit_custody` at.
- **C13** on a URL run (generation).
- **Local pass/fail proof** of the
  proxy itself — none in this repo.
- **C12 pass** without a routed-but-
  ungoverned path (operator).

---

## Local first (before building)

| Stand-up | Possible here? |
|---|---|
| Apigee Edge / hybrid emulator | **No** |
| Minimal Apigee proxy against a stub | **No** — no Apigee runtime |
| Echo backend (observer contract) | **Yes** — same shape as Kong `echo.py` |
| HTTP records collector (`{records:[]}`) | **Yes** — stdlib service; not custody |
| Kit against a real Apigee org | Only if the tester has one |

Anything built for records/observer
can be unit-validated locally. The
proxy path stays blind until an org
run.

---

## Decision this table makes

1. Close **backend observer** (unlocks
   C16; enables C1 soft assert).
2. Close **retrievable records**
   (unlocks C10×3) — Trace stays Trace;
   package must emit to a GET surface
   the kit can read, or C10 stays a
   permanent Apigee skip on the
   observability map.
3. Do **not** close runner, deploy,
   OAuth, local runtime for unlock
   math (0 cases).
4. Do **not** ship a mock custody the
   kit talks to; L3 stays
   tester-supplied or skipped.

Build starts after this file is
committed.
