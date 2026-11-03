# Procedure B — identifier pass

Hostile-literal instructions. Do what the steps say. Do not
tune the inventory to match a remembered headline number.
Do not edit the candidate.

This procedure corresponds to the sweep that produced the
recorded hand inventory (and the later correction that its
counts are a floor). Those numbers are history, not targets
for this run.

A mechanised helper for this pass lives at
[`../scripts/`](../scripts/). The helper does not replace the
human obligation columns below. If the helper is unavailable,
run this procedure by hand exactly as written.

---

## Document

Run against the **candidate's normative specification
corpus**: every prose file the candidate marks normative,
every schema / IDL / example the normative prose cites as
normative or as the home of a named token, and any external
document the candidate normatively incorporates by explicit
pointer.

Exclude: blog posts, non-normative guides the candidate does
not point at, implementation repositories, and findings
history.

---

## Question (one sentence)

For every stable name the corpus treats as part of its
vocabulary, does a requirement sentence (or, where the class
owes a definition instead, a definition) exist under that
name?

---

## Steps

1. **Freeze the corpus.** Commit / tag / URL + retrieval date.
   List every file path. Do not add files after the inventory
   starts except when a normative pointer forces it; log each
   addition.

2. **Harvest identifiers.** Walk, in this order:
   1. every heading that introduces a named obligation,
      profile, level, field, status, or rule;
   2. every RFC 2119 / BCP 14 keyed sentence (`MUST`,
      `MUST NOT`, `SHALL`, …) and the nearest name it binds;
   3. every schema `enum`, `const`, `$id`, and required
      property name;
   4. every named header, media type, error code, or wire
      token in normative examples the prose treats as
      canonical.

   Write one row per distinct identifier string (case-
   sensitive as the corpus writes it). Do not merge
   `FooBar` and `foo_bar` because they "mean the same."

3. **Assign a class.** Give each identifier a short class
   name (examples of shape only: `criterion`, `header`,
   `response-identifier`, `schema-enum`). Classes are an
   inventory convenience. When two names play the same role,
   use the same class string. When unsure, invent a new class
   string rather than forcing a fit — and record the doubt.

4. **Per class, state what the class owes** before filling
   the requirement column:
   - Classes that mint implementation obligations (criteria,
     headers that constrain behaviour, validation rules)
     **owe a requirement sentence**.
   - Classes that name client-observable tokens (response
     `status` values, agent-action tokens, wire enums meant
     for callers) **owe a definition** (meaning, when
     emitted, what a caller may conclude). A requirement may
     also attach; the baseline is the definition.
   - Classes that are pure schema spelling with no prose
     role still get a row; mark what they owe as `definition`
     unless the prose clearly elevates them.

   Do **not** apply the criterion test ("is there a MUST
   beside this name?") to a class that owes a definition.
   That mistake is how a prior identifier pass named a
   response-identifier class and still missed half its
   members.

   When filling the requirement column for a class that owes
   a requirement sentence, credit a member under either of
   the following — not only under same-paragraph co-occurrence
   of the member token with `MUST` / `SHALL` / `REQUIRED`:

   **Class-coverage rule.** A requirement stated about a
   class covers a member identifier when (a) the requirement
   names the class by its own name or by a pattern the
   member matches, (b) the obligation is satisfiable per
   member, and (c) nothing in the requirement or its scope
   excludes that member. Examples of shape only: a sentence
   that all five `x-ctier-criteria` fields are required
   covers each criteria dimension and each closed enum
   value of those fields; a document-type / record-version
   class that the corpus validates as named formats covers
   each version string in that class; a profile / tier /
   deployment-level / generator-mode / corpus-dimension
   class covers each named member the class enumerates.

   **Titled-section / list-label body.** If the identifier
   *is* the section title or the numbered list label of an
   obligation (`### Bound comparison`, `Requirement 3`, …),
   a requirement sentence in that section or list-item body
   covers the identifier even when the body does not repeat
   the title token. The class-coverage rule above does not
   reach these cases; state this second rule explicitly or
   you will mark titled validation rules and numbered
   deployment requirements as missing whenever the MUST sits
   only in the body.

   A wire token that is merely *discussed* under a named
   criterion (for example a header mentioned parenthetically
   as how `C6` is satisfied) without being a class member
   under the first rule and without being the section title
   under the second is **outside both rules**. Leave it to
   reader judgment and record the doubt; do not silently
   extend class-coverage to "anything near a criterion."

5. **Fill columns for each row:**
   - `requirement-or-definition-found`: `yes` / `no`
   - `titled-under-own-name`: `yes` / `no` (a table cell or
     parenthetical letter counts as titled only if the
     section heading or an explicit `ID —` title carries the
     name; a mention inside another criterion's body is not
     "titled under its own name")
   - `where-introduced`: file + section heading
   - `notes`: at most one line

6. **List every `no` in the found column** as a numbered
   follow-up proposal ("state …" / "define …"). Do not draft
   the missing sentence during the run.

7. **Optionally cross-check** with
   [`../scripts/`](../scripts/) if present: run the script on
   the same frozen commit, attach its inventory as an annex,
   and record disagreements on the timing form. Disagreement
   is a finding; do not edit either inventory to force a match
   during the run.

---

## Counting rule

- **I** = number of identifier rows.
- **K** = number of distinct class strings.
- **Missing** = rows with `requirement-or-definition-found =
  no` under the obligation that class owes (requirement for
  requirement-classes; definition for definition-classes).
- **Retitled** = rows that had a sentence/definition but
  `titled-under-own-name = no` at harvest (even if you would
  later attach a title — count the pre-attach state).
- Report **I / K / Missing** and, separately, **Retitled**.
- These numbers count **the identifiers and classes this
  sweep used**. They are a **floor** for a reader-complete
  inventory. A later reader who names another class, or who
  finds wire tokens only an implementation emits, raises
  both **I** and **K**. Never treat the first total as
  complete because it felt exhaustive.

---

## Output shape

Inventory tables grouped by class, then the totals, then the
numbered missing list.

| Identifier | Class | Where introduced | Found? | Titled? |
|---|---|---|---|---|
| R1 | criterion | `spec.md` §Criteria | yes | yes |
| `widget_fail` | response-identifier | example only | no | no |

```
I=2 K=2 Missing=1 Retitled=0
```

Missing:

1. Proposed follow-up — define `widget_fail`

### Worked fragment (synthetic; not a candidate result)

Schema enum contains `retry_later`. Prose headers list the
string once with no meaning, when-emitted, or caller
conclusion. Class `response-identifier` owes a **definition**.
Found = `no`. That is a miss even though a `MUST` elsewhere
mentions a different token in the same class.

---

## Known blind spots

- **Counts are floors.** Full stop. A later pass that asks a
  better per-class question will find members this pass did
  not.
- **Wrong question per class.** Applying "has a requirement
  sentence?" to response-identifiers (or any definition-
  owing class) systematically misses members that need a
  definition but carry no MUST. A prior run missed **half**
  of one response-identifier class that way; treat that as a
  structural blind spot of the question, not as bad luck.
- **Schema-only and example-only tokens.** Easy to skip if
  you only grep headings. Step 2 parts 3–4 are mandatory.
- **"Titled" vs "mentioned".** A name inside another
  obligation's field list can look "specified" while still
  failing titled-under-own-name and even failing a definition
  of its own.
- **Mechanisation does not cure obligation mistakes.** A
  script that joins schema tokens to MUST headings will still
  miss definition-owing classes if the join encodes the
  criterion question. Read the counting-rule note beside the
  script before treating its totals as Procedure B complete.
- **Implementation wire tokens outside the corpus** are out
  of scope for this procedure. Finding them requires a
  different question (observe what implementations emit). Do
  not pretend a prose-only pass closed the wire set.
