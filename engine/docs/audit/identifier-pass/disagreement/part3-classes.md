# Part 3 — two lost classes (31 vs 33)

Finding 43 uses **33** class labels. The script assigns **31**.

## Labels only in finding 43

| Class | Judgment |
|---|---|
| Concept | **Miss** — twelve concept identifiers (`governed set`, `granted scope`, …) are absent from the script inventory entirely, not merged under another label. |
| Extension subfield | **Miss** — seven nested fields (`undeclaredTier`, `escalateAbove`, …) are not harvested; script `Extension field` count is the parent `x-ctier-*` keys only. |
| Header alias | **Miss** — `X-Correlation-Id`, `X-Ctier-Tier`, `X-Idempotency-Key` never appear as script identifiers (aliases not collected). |

## Labels only in the script

| Class | Judgment |
|---|---|
| Unclassified | Catch-all for rule-artefact tokens (HTTP methods, generic stems, …). |

## Cardinality

33 − 3 (Concept, Extension subfield, Header alias) + 1
(Unclassified) = **31**.

The headline "two missing" is the **net** cardinality gap.
Naming the two that most cleanly explain a 33→31 merge story
without the catch-all: if **Extension subfield** and
**Header alias** were folded into Extension field / Header,
cardinality would drop by two — but **Concept** would still
be missing and **Unclassified** would still be extra, so label
sets would not match. None of the three hand-only labels is a
record oversplit of a script label that already contains those
rows; the rows themselves are missing.

**Short answer:** the two-count gap is three misses (Concept,
Extension subfield, Header alias) minus one catch-all
(Unclassified). Not record oversplit.

## Follow-up (task 92)

The script now harvests all three hand-only labels. At the
1.16.0 sweep pin that yields **34** classes (33 + Unclassified).
Unclassified remains populated (rule artefacts). See
`../derived/HEADLINES.md` Part D and private finding 92.
