# Kong and APISIX against conformance-kit/1.1

After 65: APISIX catchall C2 records a
decision. Kit adds
`c10-undeclared-has-a-decision`. Kong
unchanged on that path (already
recorded via the global plugin).

Date: 20 September 2026. Live stacks,
bundle, reference description.

A result is meaningful only against
`conformance-kit/1.1`.

A clean matrix is a claim about the
cases in the kit, and the kit is not
the specification. The reason that
caveat exists is this instance: C10
passed on classified paths while the
composed-undeclared path stayed silent
until the kit named it.

---

## Fail-before-fix (APISIX)

Against unfixed generate, kit/1.1 case
`c10-undeclared-has-a-decision` alone:

- status `423`, body highest-class
- `record.present: decision` → **failed**
  (`observed: none`)

After the catchall emit: **passed**.

---

## Kong

### Level 3

15 passed, 0 failed, 2 skipped, 1
inconclusive. **16 ran.**

| Inconclusive | Observed |
|---|---|
| `c12-unassigned-is-refused-undetermined` | status `404`, empty body — path never routed |

Skipped: `c4-w2` (level), `c13`
(generation).

### Level 2

11 passed, 0 failed, 6 skipped, 1
inconclusive. **12 ran.**

---

## APISIX

### Level 3

16 passed, 0 failed, 2 skipped, 0
inconclusive. **16 ran.**

`c10-undeclared-has-a-decision`
passed. `c12` passed (catchall routes
`/estate/unknown`).

### Level 2

12 passed, 0 failed, 6 skipped, 0
inconclusive. **12 ran.**

APISIX: **0** failing rows. The
composed-undeclared C10 silence from
63 is gone at both levels.
