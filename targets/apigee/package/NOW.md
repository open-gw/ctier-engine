# What would run now

Date: 20 September 2026. After the two
gaps Part 1 said were worth closing
(observer + retrievable records).
Still **no live Apigee organisation**
in this repository — pass/fail of the
proxy itself remains unmeasured here.
Counts are kit skip-rule projections
plus local validation of the new
sidecars.

Compare to `TODAY.md` (Part 1).

---

## After (Level 2, optional URLs wired)

Assumptions:

- `kit_level: "2"`
- `kit_observer` → shipped `observer/`
- `kit_records` → shipped `collector/`
- `kit_custody` empty
- Proxy + token + collector URL
  replaced in `SC-RecordDecision`
- C12 still without routed-but-
  ungoverned → inconclusive

| Outcome | Part 1 | Now | Δ |
|---|---:|---:|---:|
| Would run (pass or fail) | 6 | **10** | +4 |
| Inconclusive | 1 | 1 | 0 |
| Skipped | 11 | **7** | −4 |
| Pass / fail on Apigee | unknown | unknown | — |

**Ran** = 11 (was 7). The four new
runs are exactly the unlocks Part 1
named: C10 × 3 + C16.

### Still skipped (7)

| Case | Reason |
|---|---|
| `c4-w1`, `c5`, `c6`, `c7`, `c14-w1` | not applicable at this level |
| `c13` | covered at generation |
| `c4-w3` | requires pending (real custody; no mock) |

### Gaps not closed (unlock 0)

Standalone runner, deploy script,
OAuth wiring, local Apigee runtime —
unchanged. Custody placeholder —
tester supplies a real host for L3, or
skips.

---

## Local validation established

| What | Result |
|---|---|
| Apigee Edge / hybrid emulator | **Still absent** |
| `observer/echo.py` contract | Smoke: log + `GET /_harness/requests` |
| `collector/` ledger GET/POST | Smoke: decision round-trip |
| Generate emits `SC-RecordDecision` + refuse JS | Unit test + regenerated `generated/` |
| Kit against a running Apigee proxy | **Not run** (no org / runtime) |

Remaining gaps are closed **blind** on
the proxy path: artefact + sidecar
proof only.

---

## Did the running count barely move?

Baseline ran **7**. Now **11** when the
tester wires both sidecars. That is
+4 cases — material for C10/C16, still
thin next to Kong/APISIX Level-2 live
matrices (~12 ran on a local rig with
full records+observer). Without an
org run, **pass** stays unknown. The
honest Apigee claim is: status-shaped
cases plus C10/C16 **can** be measured
when provisioned; they are not proved
here.
