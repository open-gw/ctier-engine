# Coverage rules (for this pack)

Apply these rules when filling the recording sheet. They are
the two coverage rules from Procedure B's per-class obligation
step, copied here so this pack stands alone. A third pattern is
named only as **reader judgment** — record when you use it; do
not silently fold it into either rule below.

Before judging a row, recall what the class owes (requirement
sentence vs definition). Do **not** apply a "is there a MUST
beside this name?" test to a class that owes a definition.

---

## Rule 1 — Class-coverage (verbatim)

> A requirement stated about a class covers a member
> identifier when (a) the requirement names the class by its
> own name or by a pattern the member matches, (b) the
> obligation is satisfiable per member, and (c) nothing in the
> requirement or its scope excludes that member.

### Shape examples (not results)

- A sentence that all five `x-ctier-criteria` fields are
  required covers each criteria dimension and each closed enum
  value of those fields.
- A document-type / record-version class that the corpus
  validates as named formats covers each version string in that
  class.
- A profile / tier / deployment-level / generator-mode /
  corpus-dimension class covers each named member the class
  enumerates.

### Worked fragment (synthetic)

Corpus states: "Where `x-ctier-criteria` appears, all five
fields are required." Identifier `blastRadius` is a member of
the criteria-dimension class those fields constitute.

- Class-coverage: **fires** — the requirement names the class
  pattern; the obligation is satisfiable per member; nothing
  excludes `blastRadius`.
- Record: Covered `yes`, rule `class-coverage`, quote the
  class-level sentence.

### Boundary (do not over-extend)

Class-coverage is **not** "any token discussed near a
requirement." A header that appears only parenthetically under
an unrelated criterion, without being a class member under this
rule, is outside Rule 1.

---

## Rule 2 — Titled-section / list-label body (verbatim)

> If the identifier *is* the section title or the numbered list
> label of an obligation (`### Bound comparison`,
> `Requirement 3`, …), a requirement sentence in that section or
> list-item body covers the identifier even when the body does
> not repeat the title token. The class-coverage rule above does
> not reach these cases; state this second rule explicitly or
> you will mark titled validation rules and numbered deployment
> requirements as missing whenever the MUST sits only in the
> body.

### Worked fragment (synthetic)

Heading: `### Bound comparison`. Body (no repeat of the title
token): "An implementation MUST interpret a bound parameter's
value as a decimal number."

- Class-coverage: does **not** fire (the identifier is the
  title, not a class-member under a class-named requirement).
- Titled-section body: **fires**.
- Record: Covered `yes`, rule `titled-section-body`, quote the
  body sentence.

---

## Pattern 3 — Criterion-linkage (reader judgment only)

A wire token that is merely *discussed* under a named criterion
(for example a header mentioned parenthetically as how a named
criterion is satisfied) without being a class member under
Rule 1 and without being the section title under Rule 2 is
**outside both rules**.

**Do not silently extend class-coverage to "anything near a
criterion."**

If you credit coverage anyway, you are exercising **reader
judgment**, not Rule 1 or Rule 2. On the recording sheet:

- put `reader-judgment` under Which rule, and
- explain the link in Notes (which criterion, why the token is
  covered, what alternative reading you rejected).

If you are unwilling to defend that judgment, mark Covered
`undecidable` (or `no`) and say so in Notes.

### Worked fragment (synthetic; judgment, not a rule fire)

Criterion `C6` body discusses header `Authorization` as how
the criterion is satisfied, but `Authorization` is not a
class-covered member under Rule 1 and is not the section title
under Rule 2.

- Rules 1 and 2: **do not fire**.
- Any `yes` is reader judgment; record it as such.

---

## What these rules are not

- They are not a harvest procedure. The inventory is given.
- They are not a licence to invent a third mechanical rule
  mid-run.
- They do not tell you the answer for any row in advance.

---

## Reach of the two rules (43 of 44)

Against the script-vs-hand disagreement set used when the
two rules were stated, **class-coverage + titled-section /
list-label body together reach 43 of 44** cases that had been
filed as "covered by a class or title-body reading."

The **holdout** is the criterion-linkage pattern above
(`Authorization` discussed under a named criterion without
class membership under Rule 1 and without being the section
title under Rule 2). That case is **not** folded into either
rule. Adopting it as a third mechanical rule was considered
and **not adopted** — it would push the obligation step toward
not being stateable for a stranger. Record it as reader
judgment when it arises.

The figure **43 of 44** is therefore a statement about the
reach of the two written rules on that disagreement set, not
a target for a stranger to match mid-run, and not a licence
to invent Rule 3.
