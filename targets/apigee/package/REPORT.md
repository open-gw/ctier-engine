# Report-back template

Copy this file, fill every field, attach the harness JSON. “It seemed to work”
cannot be compared to anything.

## Who

- Organisation name:
- Environment (eval / prod / other):
- Apigee product (X / Edge / hybrid) and version:
- Date (UTC):
- Contact:

## Artefact

- `compositionDigest` from `generated/ctier-generate.json` **wait** — that file
  carries `deploymentDigest`. Paste both:

```
deploymentDigest:
engine version (pip show ctier-engine, or git rev-parse HEAD):
```

- Did you regenerate with `./build.sh`, or use a bundle `make demo` wrote?
- Custody URL you compiled in (redact secrets; host and path are enough):

## Differential

Attach `harness-report.json` from:

```
python harness.py --deployment level-3 --proxy https://… --token … --out harness-report.json
```

- `agree`: true / false
- Cases that disagreed (id, expect, observed):
- Cases you skipped, and why (must not be “looked fine”):

## Strip

- Forged `x-ctier-tier: 1` on the declared-4 operation: HTTP status, and whether
  the backend echo still showed that header:

## Withhold (if custody was wired)

- First call status (expect 202):
- Approve executed? (yes/no, status):
- Duplicate agent retry: second backend call observed? (yes/no):

## Failures other than classification

- Deploy errors:
- JWT / product mismatch:
- Target endpoint errors:
- Anything the generated policies logged in Trace that surprised you:

## Org configuration that could explain a miss

- PreProxy FlowHooks installed on this environment:
- Shared flows on the proxy PreFlow:
- Existing AssignMessage / RaiseFault names that collided:
- JWT policy claim used for scopes (name and sample, redact the token):

## Standing of this result

Circle one:

- [ ] Differential agreed; strip held; withhold not attempted (no custody).
- [ ] Differential agreed; strip held; withhold held.
- [ ] Differential disagreed (attach the cases). This is the useful outcome.
- [ ] Could not run the harness. Say what blocked you, not that Apigee is fine.
