# Reading your result

At most two pages. Send the file. Do
not diagnose failures.

After `./run.sh kit.conf` you have
`kit-result.yaml` (or whatever you set
in `kit_out`). That file is the result.
Do not edit it. Do not replace it with
a summary.

## The four outcomes

Every row is exactly one of:

| Result | Meaning |
|---|---|
| `passed` | The check ran and matched. |
| `failed` | The check ran and did not match. The row includes what came back (status, and the field that differed). |
| `skipped` | The check did not run. The row names exactly one reason (below). A skip is **not** a pass. |
| `inconclusive` | The check ran, but the answer does not distinguish conformance from something the checklist cannot see. An inconclusive is **not** a fail. |

The top of the file counts:

- `passed`, `failed`, `skipped`,
  `inconclusive`
- `ran` = passed + failed +
  inconclusive

Skips are not runs.

## Skips are expected

Every skipped row carries one reason:

| Reason | Meaning |
|---|---|
| `not applicable at this level` | The case belongs to the other deployment level (`kit_level` 2 vs 3). |
| `requires a capability this target lacks` | You left `kit_records`, `kit_observer`, or `kit_custody` empty and this case needs one of them. |
| `covered at generation rather than runtime` | The obligation is checked when compiling, not by a request to a running proxy. |

### How many skips to expect (level 3)

If you set `kit_level: "3"` and leave
records, observer, and custody empty:

- **1** skip — `not applicable at this level`
  (`c4-w2-level-2-class-3-is-a-decision`)
- **1** skip — `covered at generation rather than runtime`
  (`c13-assignment-does-not-apply-to-another-composition`)
- **8** skips — `requires a capability this target lacks`
  (records: three C10 rows; observer:
  C7 and C16; pending/approve:
  C4-w3, C6, C14)

**10 skipped**, and the rest ran (some
may still fail or be inconclusive if
provisioning was incomplete).

### How many skips to expect (level 2)

If you set `kit_level: "2"` and leave
the optional URLs empty (the default
in `kit.conf.example`):

- **5** skips — `not applicable at this level`
  (level-3-only rows, including
  withhold and C7)
- **1** skip — `covered at generation rather than runtime`
  (C13)
- **5** skips — `requires a capability this target lacks`
  (pending: C4-w3; records: three C10
  rows; observer: C16)

**11 skipped**. That is normal for a
first Apigee pass without a collector
or observer.

## Inconclusive you may see

`c12-unassigned-is-refused-undetermined`
with status `404` means the path was
likely never routed. That is the
provision gap in `PROVISION.md` §5,
not a failed refuse. If you did
provision the route and still see
`failed`, send the file — do not
re-run analysis yourself.

## What a clean matrix claims

A file with **0 failed** rows is a
claim about the **cases in
conformance-kit/1.1**, not a claim that
Apigee implements the whole
specification. The checklist is not
the specification. Skips leave
obligations untested. Say that when
you quote the file.

## What to send back, and to whom

Send **the result file**
(`kit-result.yaml`) to the person who
gave you this package (the ctier
engine maintainer who asked for the
Apigee column).

Also send, in the same message:

- the `apigee_org`,
  `apigee_environment`, and
  `apigee_proxy_name` from your config
  (not secrets)
- whether you regenerated with
  `./build.sh` or used an existing
  `generated/` tree
- which optional URLs you left empty

Do **not** send bearer tokens.
Do **not** send Trace screenshots
instead of the file.
Do **not** interpret or diagnose
failures. Diagnosis is ours.

If the command never wrote a file,
say what blocked you (install, deploy,
token) in plain language and stop.
