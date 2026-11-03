# Part 2 — Diff vs recorded coverage figures

**Written:** 2026-11-03T01:01:00Z — after `01-DERIVED-COVERAGE.md`.
Opened now: recorded coverage totals (strict / lenient / gap
composition) for comparison only. Sealed second-analyst key
contents were **not** used as a package input.

| Figure | Recorded | Re-derived | Δ | Cause |
|---|---:|---:|---:|---|
| Strict no-requirement | 145 | **145** | 0 | exact match (mechanised script at pin on written-rule inventory) |
| Lenient no-requirement | 46 | **46** | 0 | exact match |
| Gap | 99 | **99** | 0 | 145−46 |
| Gap primary: class-coverage | 46 | **46** | 0 | exact match |
| Gap primary: titled-section-body | 6 | **6** | 0 | exact match |
| Gap primary: requirement-like-prose | 47 | **47** | 0 | exact match; 46+6+47=99 closes |
| Agreed no (script ∩ hand) | 16 | — | — | **not re-derivable:** needs hand `no` column (human 22) |
| Lenient residual 16+28+2 | 46 (=16+28+2) | L=46; partition — | — | **partition not re-derivable** without hand column + prior script-only disagreement bucket; residual **total** matches |
| Human 22 | 22 | — | — | **not re-derivable** (reader judgment; not attempted) |
