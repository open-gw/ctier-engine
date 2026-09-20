# What a run of this package would establish

Do not report “the proxy deployed”. Report whether these claims held.

## Classification (differential)

Run `python harness.py --deployment level-3` first. That is the reference
oracle against the handwritten corpus plus generated cases. Then:

```
python harness.py --deployment level-3 --proxy https://YOUR-HOST --token TOKEN
```

The harness posts each case and compares observed `(appliedTier, disposition)`
to the reference. **Agreement** is the claim.

A miss on `bounds-exceeds-listTransactions` (limit=101 → applied 3) means the
Apigee Condition did not escalate. A miss on `c11-injected-tier-ignored`
means an inbound `x-ctier-tier: 1` selected the operation’s tier — the strip
did not hold.

## Strip (C11)

Forge `x-ctier-tier: 1` on `PUT /config/feature-flags` (declared 4). Expect
refuse-and-suspend at Level 3 (423 or the compiled RaiseFault), not execute
as Tier 1. The echo backend, if you have one, must not see the forged inbound
header.

## Withhold

With custody pointed at a real implementation (replace
`custody.example.invalid`):

- `PUT /customers/{id}/preferences/communication` returns **202**, not 200.
- The pending body identifies the same method and path.
- `POST /v1/decisions/{correlationId}` with `approve` executes **once** from
  persisted context. A second agent retry must not produce a second backend
  call.

Without custody, that operation is refuse-provisioning (403). Do not call
that a withhold success.

## What this run cannot establish

- Durability of `print()` Decision lines (Trace only).
- Precedence against a PreProxy FlowHook you did not declare in the artefact.
- Live Kong/APISIX parity — those are already run in-tree. This package is
  the Apigee column.
