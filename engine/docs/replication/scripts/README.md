# Scripts and recorded outputs

Mechanised identifier harvest used for the strict / lenient
figures in this package. The counting rule is
[`COUNTING-RULE.md`](COUNTING-RULE.md). The script is
[`identifier_pass.py`](identifier_pass.py).

This is an annex to Procedure B. It does **not** rewrite the
human obligation columns in
[`../procedures/procedure-identifier-pass.md`](../procedures/procedure-identifier-pass.md).

## Invocation (pin)

```bash
# from engine/docs/replication/
python3 scripts/identifier_pass.py \
  0a997321234e5f6f6184b7449a241c3d30a19520 \
  --repo /path/to/open-gw/ctier \
  --json scripts/recorded-outputs/inventory-1.16.0-sweep.json \
  --md  scripts/recorded-outputs/inventory-1.16.0-sweep.md
```

`CTIER_REPO` may replace `--repo`. If neither is set, the
script looks for a sibling `ctier` checkout next to this
engine repository. There is **no** hardcoded personal path.

## Invocation (tip, for comparison only)

```bash
python3 scripts/identifier_pass.py \
  66c509f3625fced9f30f029f458b186547b06d47 \
  --repo /path/to/open-gw/ctier \
  --json scripts/recorded-outputs/inventory-tip.json \
  --md  scripts/recorded-outputs/inventory-tip.md
```

Tip figures are not the case-study pin. The paper's living tip
is specification 1.25.0; the pin remains 1.16.0 /
`0a99732…`.

## Recorded outputs in this package

| File | What it records |
|---|---|
| `recorded-outputs/inventory-1.16.0-sweep.json` | Full JSON inventory at the pin |
| `recorded-outputs/inventory-1.16.0-sweep.md` | Markdown inventory at the pin |
| `recorded-outputs/inventory-tip.json` | Tip comparison inventory |
| `recorded-outputs/inventory-tip.md` | Tip comparison markdown |
| `recorded-outputs/HEADLINES.md` | Headline table (script vs recorded) |
| `recorded-outputs/re-derivation-part1-script-inventory.json` | Re-derivation Part 1 annex (same pin) |
| `recorded-outputs/re-derivation-part1-script-inventory.md` | Same, markdown |
| `recorded-outputs/re-derivation-part1-script-run.log` | Captured run log / summary |

## Expected summary at the pin (recorded)

| Field | Value |
|---|---:|
| Identifiers | 239 |
| Classes | 34 |
| Strict no-requirement | 145 |
| Lenient no-requirement | 46 |
| Gap | 99 |
| Gap primary: class-coverage | 46 |
| Gap primary: titled-section-body | 6 |
| Gap primary: requirement-like-prose | 47 |

A stranger who re-runs the invocation above against a public
`ctier` checkout at the pin should match these totals. Row
order in markdown may differ; the counts must not.
