# Part 4 — Derived criteria partition (this run)

**Written:** 2026-11-03T00:55:00Z — after `00-PROCEDURE.md`,
before opening recorded partition headlines for diff.

**Sweep window (verified):**

| Bound | Commit | Role |
|---|---|---|
| Open | `b074475b4fedd35c527c4d8ba089053e5fbe8d04` | findings for 25 |
| Close | `bde94022e16493b28f595c693c7ac66d49835682` | findings for 42 |
| C3 titled | `121bb8b5…` | `spec: C3 is titled` |
| C1/C4 stated | `463bf5ba…` | `spec: C1 and C4 are stated` |
| Accounting note | `974a2700…` | `spec: correct the criteria accounting` |

Corpus: `spec/README.md` + `spec/validation.md` only.

---

## Step 2–3 — presence at the pre-title / pre-C1·C4 state

Examined parent of `121bb8b` (`5df2bffe…`), still inside the
window, before C3 received its letter and before C1/C4 letters
landed:

| ID | Presence (this run) | Evidence |
|---|---|---|
| C1 | **never stated** | no `**C1 —` / requirement under C1 in candidate |
| C2 | **stated** | fail-closed obligation present in validation prose ("Fail-closed is C2…") / README references; lettered title arrives later at attach `0a99732` but the obligation was already in-corpus |
| C3 | **under another name** | validation `### Unidirectionality` body (`x-ctier-escalate-to` may never resolve below…) **without** a C3 title; commit `121bb8b` only attaches the name |
| C4 | **never stated** | no C4 requirement under that ID |
| C5–C12 | **stated** | `**C5`–`**C12` requirement blocks in README at this freeze |

**Named set covered by the audit:** C1–C12 → **N = 12**.

### Partition (this run)

| Bucket | Members | Count |
|---|---|---:|
| Stated | C2, C5, C6, C7, C8, C9, C10, C11, C12 | **9** |
| Never stated | C1, C4 | **2** |
| Under another name | C3 | **1** |
| **Sum** | | **12** |

Arithmetic: 9 + 2 + 1 = **12**. **Closes.**

Note on later glosses: maturity prose at `974a270` / pin
`0a99732` says "three were never stated: C1, C3 and C4" in
one breath, then immediately "C3's requirement existed
unattached to its name, C1 and C4 not at all." The precise
partition above is that gloss — C3 is not a third *absent*
letter; it is the under-another-name cell.

---

## Step 4 — seven of nine mechanism-where-property

Applied Procedure A tests to the **stated** nine, using the
requirement sentences as the audit met them (including
pre-1.13.0 mechanism prescriptions that maturity says were
later restated as properties):

| ID | Verdict (this run) | Brief ground |
|---|---|---|
| C2 | `property` | fail-closed outcome; no replaceable artefact as the obligation |
| C5 | `mixed` / mechanism pressure | property + named status/`agentAction` prescription |
| C6 | `mixed` | approved-bytes property + persist/store prescription |
| C7 | `mechanism` (historical letter) | derived-key / persist prescription as the obligation |
| C8 | `property` | expiry vs rejection outcomes; no replaceable wire artefact as the letter |
| C9 | `mixed` | identity prohibition + named 423/`AgentSuspended` prescription |
| C10 | `mechanism` / mixed | record-before-act / binding prescription |
| C11 | `mixed` | honour-rule property + strip/MAC prescription |
| C12 | `mechanism` / mixed | coverage property later; generator/refuse-to-emit prescription in the audited letter |

**Mechanism-where-property (mechanism ∪ mixed):**
C5, C6, C7, C9, C10, C11, C12 → **7**.

**Already property among the nine:** C2, C8 → **2**.

Check: 7 + 2 = 9. **Closes.**

---

## Summary (this run)

```
N=12
stated=9
never_stated=2   (C1, C4)
under_another_name=1   (C3)
mechanism_where_property=7
```

Partition leads with **closes to twelve**.

---

## Next

`02-DIFF.md` after opening recorded partition figures.
