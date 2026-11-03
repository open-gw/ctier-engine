# Procedure A — criteria audit (mechanism or property?)

Hostile-literal instructions. Do what the steps say. Do not
import prior knowledge of what any earlier sweep found on any
other document. Do not edit the candidate. Do not "fix" anything
during the run; record only.

This procedure corresponds to the sweep recorded as tasks
25–42 in the original work (classification, restatement
pressure, scope questions). Those task numbers are history,
not inputs.

---

## Document

Run against the **candidate's named normative criteria /
conformance-requirements set**: the sections the candidate
itself treats as the list of numbered or lettered obligations
an implementation must meet (for example a "Criteria",
"Conformance", or "Requirements" chapter that assigns stable
identifiers such as `C1`, `REQ-3`, or `§4.2`).

Include only files the candidate's own text marks as
normative for those obligations (including a schema or
appendix the criteria section cites by name).

**Do not** invent a criterion from a product README, a blog,
or an implementation PRD unless the candidate text itself
normatively points at that file as the location of the
criterion. If you are tempted to pull a sibling repository
into the corpus because "that is where the titles live,"
stop: record the temptation on the timing form and stay
inside the candidate's normative set.

---

## Question (one sentence)

For each named criterion, does its requirement sentence state
a property an implementation must achieve, or does it name a
mechanism (artefact, store, status code, constructor, plugin
order) that could be replaced without changing the intended
outcome?

---

## Steps

1. **Freeze the corpus.** Record commit / tag / URL + retrieval
   date of every file you will read. Do not change the set mid-
   pass unless a criterion body cites a further normative file
   by name; if it does, add that file, note the addition, and
   continue.

2. **List every criterion identifier** the corpus presents as a
   member of the criteria set (heading of the form
   `C12 — …`, `Requirement 3`, numbered conformance clause with
   a stable letter/number). One row per identifier. If a
   requirement sentence exists under a descriptive title but
   carries no letter, still list it — mark `identifier:
   untitled` and quote the title. Do not skip untitled
   requirements because they lack a letter.

3. **For each row, copy the requirement sentence(s)** that the
   corpus presents as that criterion's obligation. If the
   identifier appears only in a list or table and the body is
   elsewhere, copy the body. If no body exists in the corpus,
   write `requirement sentence: ABSENT` and stop the
   classification for that row (verdict `unstated`). Do not
   supply a sentence from memory or from a non-corpus file.

4. **Ask, of the copied sentence: mechanism, property, or
   mixed?** Before any test, record the protected-outcome
   field for the row. Then apply the tests in order; record
   which fired.

   **Protected-outcome field (required before Test 1).**
   Quote a contiguous verbatim span from the corpus that
   states the outcome the criterion is meant to protect, in
   the candidate's own words, **or** write exactly
   `UNSTATED`. Record the location (file path + heading or
   nearby anchor the corpus uses). Do not paraphrase. Do not
   invent an outcome the corpus does not state.

   What qualifies as a **span:**
   - Contiguous characters copied from one place in the
     corpus (one sentence, or adjacent sentences under the
     same criterion heading / titled block).
   - May be the requirement sentence itself when that
     sentence already states an outcome rather than only an
     artefact.
   - May be a purpose clause, title, or surrounding prose
     under the same criterion that names what the
     prescription is for — still contiguous and verbatim.
   - Prefer the shortest span that states an outcome without
     naming only the replaceable artefact.

   What **`UNSTATED`** means:
   - No contiguous span in the corpus states a protected
     outcome in the candidate's own words for this row.
   - When the field is `UNSTATED`, **skip Test 1** for that
     row. Tests 2 and 3 may still run against the copied
     requirement sentence. Do not supply an outcome from
     memory so that Test 1 can run.

   Worked negative: if the only span you can quote restates
   the named artefact or location (status code, store name,
   plugin order, constructor) and adds no separable outcome,
   that is not a protected-outcome span — write `UNSTATED`
   (or keep searching for a purpose/outcome clause). Test 1
   does not fire on an artefact-only restatement; you have
   not found an intent/letter split.

   - **Test 1 (letter vs intent):** Using only the recorded
     protected-outcome span (skip this test when the field is
     `UNSTATED`): is there a plausible implementation that
     achieves that quoted outcome, yet fails the letter of
     the requirement sentence because the sentence names a
     particular artefact or location? If yes → mechanism
     pressure.
   - **Test 2 (replaceable prescription):** Can the named
     status, field list, store, constructor, or strip/MAC
     pair be replaced by another concrete means without
     changing the protected outcome (the quoted span when
     present; otherwise the outcome only as the requirement
     sentence itself states it)? If yes → the prescription
     is mechanism; the outcome may still be a property
     (verdict **mixed** if both an outcome sentence and a
     replaceable prescription are present).
   - **Test 3 (unsatisfiable letter):** Without the named
     artefact, is the letter unsatisfiable even when the
     protected outcome could still hold some other way? If
     yes → mechanism (or mixed).

   Verdict vocabulary (use exactly these words):

   - `property` — outcome only; no replaceable artefact named
     as the obligation.
   - `mechanism` — obligation is an artefact/location; tests
     1 or 3 fire and no separable outcome sentence remains.
   - `mixed` — outcome sentence plus replaceable prescription.
   - `unstated` — identifier or title with no requirement
     sentence in the corpus.

5. **Ask the scope question once per row that is not
   `unstated`:** "And within what scope does this obligation
   apply?" Record the bound the text states, or `unbounded`
   if none. Do not invent a bound from architecture diagrams.

6. **Do not restate.** This procedure classifies. Rewording
   the candidate is outside the run. Rank urgency only as a
   note: which `mechanism` / `mixed` rows would make a
   conformant implementation look non-conformant if left as
   letter. Ranking is not a count input.

7. **Close the table.** Every identifier from step 2 has a
   verdict. Counts below.

---

## Counting rule

- **N** = number of rows in the step-2 list (identifiers +
  untitled requirements found in the corpus).
- **Mechanisms** = rows with verdict `mechanism`.
- **Mixed** = rows with verdict `mixed`.
- **Properties** = rows with verdict `property`.
- **Unstated** = rows with verdict `unstated`.
- A row is exactly one of the four. Sum must equal **N**.
- Counts are **floors**: a later reader who notices a further
  untitled requirement, or who splits one mixed row into two
  obligations the corpus actually states separately, raises
  **N**. Do not treat the first pass as complete because the
  section heading said "twelve."

---

## Output shape

One markdown table, then the four counts.

| ID | Verdict | Protected-outcome span (verbatim + location) or `UNSTATED` | Tests that fired | Scope |
|---|---|---|---|---|
| R1 | mechanism | "…" (`path` §heading) | 1, 3 | governed operations only |
| R2 | property | "…" (`path` §heading) | — | unbounded |
| R3 | mixed | "…" (`path` §heading) | 2 | … |
| R4 | unstated | — | — | — |

```
N=4 mechanisms=1 mixed=1 properties=1 unstated=1
```

### Worked fragment — span present (synthetic; not a candidate result)

Corpus for `R7`, requirement sentence: "On refusal the
enforcement point MUST return status 451 and write a row to
the custody ledger before responding."

Surrounding prose under the same heading: "A refused agent
must be released onto the rest of its task; the refusal must
be evidenced."

- Protected-outcome span (verbatim + location):
  `"A refused agent must be released onto the rest of its
  task; the refusal must be evidenced."`
  (`candidate.md` §R7)
- Test 1: skip only if `UNSTATED`; here a span is recorded.
  A plausible impl could release-and-evidence with another
  non-retryable status / different durable sink and fail the
  letter's `451` + custody-ledger prescription → Test 1 may
  fire.
- Test 2 fires on the same replaceable prescription.
- Verdict: `mixed`.
- Scope: as stated in the criterion body, or `unbounded`.

### Worked fragment — `UNSTATED` (synthetic; not a candidate result)

Corpus for `R8`, sole sentence under the heading: "The
gateway MUST load `plugins/ctier-filter.so` before any other
filter."

No purpose clause, no title outcome, no adjacent prose that
states what loading that artefact protects.

- Protected-outcome field: `UNSTATED`
- Test 1: **skipped** (field is `UNSTATED`).
- Test 2 / Test 3: may still fire on the named artefact.
- Do not invent "filter order protects classification" so
  Test 1 can run.

---

## Known blind spots

- **Counts are floors.** Untitled requirements and obligations
  living only under descriptive headings are easy to miss;
  missing them under-counts **N** and especially **unstated**.
- **Wrong corpus looks like method success.** Classifying a
  sentence that lives only in a sibling product document
  produces a clean table about text the candidate never
  stated. The original criteria audit hit this shape: a
  letter was classified from an implementation PRD while the
  normative specification still lacked the sentence. If the
  identifier is cited in the candidate but the body is only
  outside it, the correct verdict is `unstated` in the
  candidate corpus — not a classification of the external
  sentence.
- **Protected-outcome span selection remains reader-
  dependent.** Requiring a quoted span (or `UNSTATED`) before
  Test 1 makes disagreement about a cited sentence rather
  than an unspoken intent. Two hostile readers can still
  pick different surrounding sentences as the outcome, or
  disagree on Test 1's "plausible implementation" once a
  span is fixed. Record the alternative you considered; do
  not smooth disagreement away.
- **This pass does not detect "named everywhere, required
  nowhere" across non-criteria identifiers.** That is
  Procedure B. Do not expand the row list into every schema
  enum because you anticipate Procedure B.
- **Restatement pressure is not conversion.** Ranking a row
  "urgent to restate" is not Procedure C and must not edit
  companion documents during this run.
