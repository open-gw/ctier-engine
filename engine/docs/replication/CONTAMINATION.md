# Contamination / leakage check (stranger-read)

Read as a stranger with only this directory (and public
relative pointers inside `open-gw/ctier-engine`). Removed or
rewrote the following before landing:

| Removed / rewritten | Where it was | Why |
|---|---|---|
| Absolute personal filesystem path `/Users/rinudhanaraj/…/ctier` as script default | `scripts/identifier_pass.py` | Private machine path; stranger cannot use it |
| Private repository name `ctier-engine-private` | `re-derivation/part3/01-DERIVED-RESTATEMENTS.md` | Leaks a non-public tree; pre-conversion artefacts are already vendored under `pre-conversion/` |
| Pointers that require opening sealed-key *contents* as inputs | `re-derivation/part2/02-DIFF.md` | Sealed key stays sealed; diff now cites recorded figures without instructing a stranger to open the key |
| Private / author-side finding file paths as *required inputs* (`docs/findings/43.md`, `engine/docs/findings/46.md`, private findings 87–95) | re-derivation diffs, headlines annex | Public package must not depend on findings files; recorded totals are restated in-package |
| Internal preparation task numbers as navigation (`task 89/91/92/95` as “go read that finding”) | README-facing prose, procedure helper links, re-derivation titles | Reframed as mechanised harvest / re-derivation / disagreement buckets where a stranger would otherwise chase private notes |
| Broken relative links to `../identifier-pass/` from the old audit layout | `procedures/*` | Retargeted to `../scripts/` inside this package |

**Kept (intentional, not leakage):**

- Headline **numbers** the README lists (matched / moved /
  not re-derivable) — those are the deliverable.
- Public commit SHAs and version strings (1.8.0 / 1.15.0 /
  1.16.0 / 1.25.0).
- Relative pointers to other **public** packs under
  `engine/docs/audit/` (second-analyst fence, upstream copies).
- SHA-256 digests of public recorded artefacts where the
  re-derivation logged them (integrity of look-last, not a
  private path).

**Not present in this package (fence):**

- No `findings/*.md`
- No `NEW-MATTER.md`
- No keys, tokens, or sealed-key file contents
- No private absolute paths after the scrub above
