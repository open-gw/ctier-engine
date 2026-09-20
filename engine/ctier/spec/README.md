# Vendored specification documents

These schemas, examples, and `consequence-tiered-api.yaml` are taken from the
published specification repository [open-gw/ctier](https://github.com/open-gw/ctier)
(release named in `VERSION`).

**Attribution (CC BY 4.0).** Copyright (c) 2026 Rinu Dhanaraj. Licensed under
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/legalcode).
This copy is an unchanged vendor pin of the named release for offline tests and
package data; it is not a fork of the specification. See that repository's
`LICENSE` for the full text. The CC BY licence grants no patent rights.

`VERSION` is the specification release these files were taken from. Syncing is
a manual bump: copy the schemas and examples, rewrite `SHA256SUMS`, update
`VERSION`. `tests/test_spec_vendor.py` recomputes the digests and fails on
drift of either. 1.4.0 renames the ledger digest to `deploymentDigest` and
moves decision and attempt records to `0.2.0`. Outcome stays `0.1.0`.
Writers now emit `attempt-record/0.3.0`; the 0.2.0 schema stays so a
reader can still name an old row. `VERSION` remains 1.4.0 — that pin
is the document-format floor, not a claim that every later record
type is absent.
