# Identifier pass (mechanised)

Audit task 89. Mechanises the check finding 43 said could be
built, against the public specification repo.

| Artefact | Role |
|---|---|
| `identifier_pass.py` | Script: `COMMIT` → inventory + totals |
| `COUNTING-RULE.md` | Honest counting rule (not fitted to 195) |
| `derived/` | Inventories recorded at the 1.16.0 sweep commit and at tip |

## Run

```bash
# from anywhere; default repo is the sibling `ctier` checkout
python3 identifier_pass.py 0a997321234e5f6f6184b7449a241c3d30a19520 \
  --repo /path/to/ctier \
  --json derived/out.json \
  --md derived/out.md
```

`CTIER_REPO` may replace `--repo`.

## What validation.md says (unedited)

> Of **195** identifiers across **33** classes, **22** had no
> requirement sentence and **3** were stated under a different
> name.

The script's totals at the same commit are recorded under
`derived/` and do **not** match those four figures. See
`derived/HEADLINES.md` and the private finding for task 89.

Replication procedures for human re-runs live elsewhere
(`engine/docs/audit/replication/` when present) — not in this
directory.
