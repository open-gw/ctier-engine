# Identifier pass (mechanised)

Audit tasks 89 / 92. Mechanises the check finding 43 said
could be built, against the public specification repo.

| Artefact | Role |
|---|---|
| `identifier_pass.py` | Script: `COMMIT` → inventory + strict/lenient totals |
| `COUNTING-RULE.md` | Honest counting rule (not fitted to 195 / 22) |
| `derived/` | Inventories recorded at the 1.16.0 sweep commit and at tip |
| `disagreement/` | Task 91 classification of script vs hand (A/B/C/D) |

## Run

```bash
# from anywhere; default repo is the sibling `ctier` checkout
python3 identifier_pass.py 0a997321234e5f6f6184b7449a241c3d30a19520 \
  --repo /path/to/ctier \
  --json derived/out.json \
  --md derived/out.md
```

`CTIER_REPO` may replace `--repo`.

The JSON summary reports `no_requirement_sentence_strict`,
`no_requirement_sentence_lenient`, and
`lenient_closes_by_rule_counts` (primary-rule itemisation of
the gap). `no_requirement_sentence` remains the strict count
for back-compat.

## What validation.md says (unedited)

> Of **195** identifiers across **33** classes, **22** had no
> requirement sentence and **3** were stated under a different
> name.

The script's totals at the same commit are recorded under
`derived/` and do **not** match those four figures. Lenient
is not tuned toward 22. See `derived/HEADLINES.md` and the
private findings for tasks 89 / 91 / 92.

Replication procedures for human re-runs live elsewhere
(`engine/docs/audit/replication/` when present) — not in this
directory.
