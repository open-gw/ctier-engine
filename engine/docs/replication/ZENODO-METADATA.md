# Zenodo metadata draft — replication package

**Prepare only. Do not create a deposit. Do not mint a DOI.**

Verified against Zenodo API on package build (2026-11-02):

| Concept DOI (current) | Latest version DOI | Version string | Role |
|---|---|---|---|
| [`10.5281/zenodo.23831726`](https://doi.org/10.5281/zenodo.23831726) | `10.5281/zenodo.23831727` | v1.25.0 | ctier specification |
| [`10.5281/zenodo.23649937`](https://doi.org/10.5281/zenodo.23649937) | `10.5281/zenodo.23866301` | v1.3.0 | ctier-engine |

(Earlier archive `10.5281/zenodo.22020288` remains a historical
spec deposit under a different concept; citations for the
living line should use the concept DOI above.)

---

## Suggested upload metadata

**Title.**  
Replication package for the ctier audit case study (procedures, pin corpus, mechanised identifier pass, re-derived headline counts)

**Resource type.** Dataset (or Software + Dataset if Zenodo
forces a single type — prefer Dataset with related software
identifiers).

**Description.**

> Replication materials for the desk sweeps behind the ctier /
> ctier-engine audit case study: vendored specification corpus
> at commit `0a997321234e5f6f6184b7449a241c3d30a19520`
> (specification 1.16.0), Procedures A/B/restatement-conversion,
> two coverage rules (a third criterion-linkage pattern stated
> but not adopted), identifier inventory with classes,
> mechanised identifier-pass script with recorded outputs, and
> an ordered re-derivation of headline counts. Ships re-derived
> figures (strict/lenient 145/46, gap 46+6+47, restatements
> 74/8, criteria 12 = 9+2+1 with seven-of-nine) and records
> which figures are not re-derivable (hand 195/33, human 22,
> agreed 16, residual partition 16+28+2). Procedure A is not
> uniquely runnable by a stranger (protected-outcome span
> selection; Test 1 “plausible implementation”). Does not
> include sealed second-analyst answer keys or author findings
> files.

**Creators / affiliation** (as on the paper deposits and
`CITATION.cff`):

| Name | Affiliation | ORCID |
|---|---|---|
| Dhanaraj, Rinu | Independent Researcher, Alpharetta, GA, USA | `0009-0007-9082-8846` |

(Spec concept record currently carries the ORCID without an
affiliation string; engine concept record carries the
affiliation above. Prefer the affiliation form for this
upload.)

**Licences (split by artefact family):**

| Artefact family | Licence |
|---|---|
| Vendored specification corpus (`corpus/spec/`, ADR-0009) | **CC BY 4.0** |
| Engine procedures, scripts, inventories, re-derivation prose in this package | **Apache 2.0** (same as `open-gw/ctier-engine`) |

State both licences in the Zenodo description / notes if the
deposit UI allows only one primary licence — primary suggestion:
CC BY 4.0 for the deposit as a whole when the corpus dominates,
with Apache 2.0 noted for engine-authored files; or the reverse
if the upload is filed under the engine concept. Author choice
at deposit time.

**Related identifiers (draft):**

| Identifier | Relation | Note |
|---|---|---|
| `10.5281/zenodo.23831726` | isSupplementTo / cites | Spec concept DOI |
| `10.5281/zenodo.23649937` | isSupplementTo / isCompiledBy | Engine concept DOI |
| `https://github.com/open-gw/ctier-engine` | isSupplementTo | Source repository |
| `https://github.com/open-gw/ctier/tree/0a997321234e5f6f6184b7449a241c3d30a19520` | references | Corpus pin |

**Keywords.** api-governance; ai-agents; replication-package;
openapi; consequence-tier; audit-methods

**Version string (suggestion).** `replication-1` or date-stamp
`2026-11-02` — author chooses at deposit.

**Files to upload (suggestion).** A zip of
`engine/docs/replication/` from `open-gw/ctier-engine` at the
commit that lands this package — excluding nothing already in
the fence (no findings, no sealed key, no `NEW-MATTER.md`).

---

## Explicitly not done in this task

- No Zenodo draft created in the web UI or API.
- No DOI minted.
- No upload performed.
