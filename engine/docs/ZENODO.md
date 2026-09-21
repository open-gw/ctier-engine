# What is deposited, and what depositing 1.25.0 would mean

Checked 21 September 2026 against Zenodo record
[`22020288`](https://zenodo.org/records/22020288)
(`https://doi.org/10.5281/zenodo.22020288`). **Nothing was deposited
in this task.**

## What the DOI resolves to today

| Field | Value |
|---|---|
| Version DOI | `10.5281/zenodo.22020288` |
| Concept DOI | `10.5281/zenodo.22020287` |
| Deposited version string | **`v0.1.2`** |
| Title | ctier: Consequence-Tiered API Governance — Specification and Reference Example |
| Resource type | Software |
| Publication date | 2026-08-20 |
| Related identifiers | none recorded on the record |

That is the document a citation of `10.5281/zenodo.22020288` lands on.
It is not specification **1.25.0**. The living specification in
`open-gw/ctier` is at **1.25.0** (C14, C15, C16, admission rule,
governed-set definition, declines list, and later drafting since
`v0.1.2`).

This engine's README and `CITATION.cff` already point readers at the
DOI. A reader who follows that link does not get the text this
repository's `docs/SPEC.md` clause table was snapshotted against.

## What depositing 1.25.0 would involve

Zenodo versioning under one concept DOI:

1. Create a **new version** of the existing deposit (same concept
   `22020287`), upload the 1.25.0 specification artefacts the author
   chooses to publish, and set the version metadata to identify
   1.25.0.
2. Zenodo mints a **new version DOI**. The existing version DOI
   `10.5281/zenodo.22020288` **keeps resolving to `v0.1.2` forever**.
3. The **concept DOI** `10.5281/zenodo.22020287` continues to resolve
   to the latest version in the family.
4. Citations that hard-code `…/zenodo.22020288` stay on `v0.1.2`
   unless updated to the new version DOI or to the concept DOI.

That permanent split is why this task does not deposit. Choosing the
version string, the uploaded files, and whether engine citations move
to the concept DOI or a new version DOI is the author's decision with
a permanent record attached.

## Not done here

- No Zenodo upload, draft, or publish.
- No change to the deposited `v0.1.2` bytes.
- No rewrite of this engine's citation target beyond recording the
  facts above.
