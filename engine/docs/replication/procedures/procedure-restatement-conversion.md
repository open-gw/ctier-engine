# Procedure C — restatement conversion

Hostile-literal instructions. Do what the steps say. Do not
edit the candidate normative document in this procedure.
Edits, if any, land only in the companion corpus you named
up front — and only after the count-before-edit table is
frozen.

This procedure corresponds to the sweep that produced the
recorded restatement totals. The headline counts from that
run are history, not targets.

---

## Document

Run against a **companion corpus**: living documents that
claim to describe, implement, or productise the candidate
normative specification (product requirements, solution
design, portability notes, root README claim lists, decision
logs that still state current law).

Name the companion corpus before you start (repository,
paths, commit). Name the normative candidate and its pin
(version or commit) separately.

If you have only the normative candidate and no companion
documents, **this procedure does not run**. Record
`companion corpus: none` on the timing form and stop. Do not
substitute the candidate's own informative sections as if
they were a second product voice.

---

## Question (one sentence)

Which sentences in the companion corpus restate a normative
obligation (or invent one the candidate does not state), and
can each be replaced by a citation to the candidate plus a
sentence about what *this* implementation does?

---

## Steps

1. **Freeze both pins.** Normative candidate version/commit;
   companion corpus commit; file list considered "living law"
   (exclude archived findings, never-edit-in-place ADRs unless
   you explicitly include them as non-editable finds, and
   generated diagrams).

2. **Define a restatement.** A sentence in the companion
   corpus is a restatement if **either**:
   - it asserts what a named criterion / requirement /
     profile of the candidate requires, in words that would
     become wrong if the candidate changed and nobody updated
     the companion; **or**
   - it asserts an obligation under a candidate identifier
     (or under a title that stands in for one) that the
     candidate pin does **not** state.

   A correct paraphrase still counts. Accuracy is not a
   defence. The test is drift risk, not current truth.

3. **Walk every living file.** For each restatement, record:
   - file + section
   - identifier claimed (or `untitled`)
   - quoted sentence (one sentence; truncate with `…` only
     after 240 characters)
   - `kind`: `echo` (candidate states something in this
     area) or `invented` (candidate pin states nothing for
     this claim, or states a different subject)

4. **Freeze the count-before-edit table.** Totals by file and
   the global total. Do not begin edits until this table
   exists in the run record.

5. **Convert, do not sync.** For each `echo` row you choose
   to touch: replace the requirement paraphrase with
   **reference** (identifier + pin) plus **what this
   implementation does**. Do not paste a pinned quotation
   corpus that becomes a second copy of the candidate.
   Leave historical ADRs and findings history unedited unless
   your pre-declared corpus included them as editable.

6. **Handle `invented` rows separately.** An invented row is
   not fixed by citing the candidate — there is nothing to
   cite. Either delete the claim, demote it to "this engine's
   mechanism," or open a follow-up on the candidate side.
   Count invented rows; do not silently reclassify them as
   echoes because the prose sounded official.

7. **Add a guard if you control the companion tests.** A
   cheap automated check that fails when a known-stale
   requirement sentence returns is in scope; behaviour
   changes in product code are not.

8. **Count after edit** only for rows you converted or
   removed. Do not claim the candidate was audited by this
   procedure.

---

## Counting rule

- **R** = restatements found in step 3 before edit (echo +
  invented).
- **E** = subset with `kind = echo`.
- **Invented** = subset with `kind = invented`.
- **Left untouched** = restatements found but excluded by the
  pre-declared non-editable set (ADRs, plans, findings) —
  report separately; they are not a reduction of **R**.
- **R = E + Invented.** If your arithmetic disagrees, your
  labels do.
- Counts are **floors**. A greppable idiom (`C12 —`, "MUST")
  under-counts paraphrases that avoid the identifier.
  Hostile readers must still read paragraphs that narrate
  obligations in prose.

---

## Output shape

### Count before edit

| Document | Restatements | Echo | Invented |
|---|---:|---:|---:|
| `PRD.md` | 2 | 1 | 1 |
| `README.md` | 1 | 1 | 0 |
| **Total** | **3** | **2** | **1** |

Left untouched (non-editable set): *n* (list files).

### Worked fragment (synthetic; not a candidate result)

Companion PRD: "`R1` — no operation reaches its target before
a decision is recorded."

Candidate pin states `R1` as "no governed operation reaches
its target unclassified" or states nothing under `R1`.

- If the candidate lacks `R1`: `kind = invented`.
- If the candidate states the unclassified property:
  `kind = echo` (and still a restatement — the PRD will drift
  when the candidate changes).
- Conversion for an echo: "`R1` (candidate *vX*): this engine
  classifies at generate time; it does not claim the
  criterion body here."

---

## Known blind spots

- **Counts are floors.** Paraphrase without identifiers is
  the main miss mode. Grep is an aid, not the pass.
- **Invented looks like echo** when a companion document has
  been treated as normative for months. Step 3's check
  against the **candidate pin** is mandatory; skipping it
  converts fiction into citations.
- **Wrong pin.** Citing a candidate version that does not
  contain the identifier reproduces the defect this
  procedure exists to remove. Record the pin on every
  converted sentence's nearby reference file.
- **Quotation corpora.** Pasting candidate text into the
  companion "so it cannot drift" creates a second normative
  surface. Forbidden by step 5.
- **This procedure does not classify mechanism vs property**
  (Procedure A) and does not inventory identifiers
  (Procedure B). Running it first on a companion that copied
  unstated letters will convert noise into tidy citations of
  nothing — unless `invented` is applied honestly.
- **Companion scope games.** Quietly widening "living law" mid-
  pass to chase a preferred total invalidates **R**. Freeze
  the file list in step 1.
