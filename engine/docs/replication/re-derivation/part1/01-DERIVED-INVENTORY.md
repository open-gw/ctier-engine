# Part 1 — Derived inventory (this run)

**Written:** 2026-11-03T00:30:00Z — after `00-PROCEDURE.md`,
before opening the recorded hand inventory / tip `validation.md` identifier
totals for the Part 1 diff.

**Pin:** `0a997321234e5f6f6184b7449a241c3d30a19520`.

**Corpus files frozen** (script listing at pin):

- `docs/adr/0009-the-contract-is-the-documents.md`
- `spec/README.md`, `spec/conformance.md`, `spec/extensions.md`,
  `spec/headers.md`, `spec/validation.md`, `spec/examples/README.md`,
  `spec/schemas/README.md`
- `spec/consequence-tiered-api.yaml`
- nine JSON schemas under `spec/schemas/`

---

## Verdict on the hand boundary

**Not re-derivable from the pin + written procedures alone.**

Missing piece: the **closed inclusion/exclusion and 33-label
class catalogue** that produced the recorded hand table was
never published as a counting rule. Procedure B gives walk
steps; `COUNTING-RULE.md` publishes a **different**, looser
mechanised harvest. Reconstructing the hand set from a
script-vs-hand disagreement list would be reconstructing from
the recorded answer — not done.

---

## What this run *did* derive (written-rule annex)

Command:

```bash
python3 identifier_pass.py 0a997321234e5f6f6184b7449a241c3d30a19520 \
  --repo <ctier> \
  --json part1/01-script-inventory.json \
  --md part1/01-script-inventory.md
```

| Quantity | This run |
|---|---:|
| Identifiers (I) | **239** |
| Classes (K) | **34** |

Per-class cardinalities (this run): see
`01-script-inventory.json` → `summary.per_class`
(Unclassified 43, Criteria value 17, Validation rule 17, …).

### Optional written exclusion only

COUNTING-RULE notes that the recorded hand inventory did not inventory HTTP
method verbs that appear only as `when.method` enum members.
Applying **only** that documented exclusion to this run's
rows removes: `delete`, `get`, `head`, `options`, `patch`,
`post`, `put`, `trace` (8).

| Quantity | After HTTP-verb exclusion |
|---|---:|
| Identifiers | **231** |
| Classes | **34** |

Still not a hand inventory. No further unpublished filters
applied.

---

## Class set (this run, 34 labels)

Unclassified, Criteria value, Validation rule, Criterion,
Concept, Extension field, Header, when-predicate, Document
type, Criteria dimension, Deployment level, Extension
subfield, Ledger field, Response identifier, Escalation
reason, Corpus field, Disposition, Schema shape, Tier,
agentAction, Confidence, Coverage status, Deployment
requirement, Header alias, Record type, Record version,
Composition role, Digest, Generator mode, Outcome result,
Profile, Document key, Measurement kind, Namespace.

---

## Next

`02-DIFF.md` opens the recorded hand figures and set-diffs
only after this file.
