# Covering note — read this first

Source:
https://github.com/open-gw/ctier-engine
(`targets/apigee/package/`).

You know Apigee. You do not know ctier.
You will not read the specification.
You cannot ask the same day. Stop at
the first instruction that does not
work and send what you have.

## What this is

A half-hour check that your deployed
Apigee proxy answers
**conformance-kit/1.1** — a fixed
checklist of HTTP cases. One
configuration file (`kit.conf`). One
command (`./run.sh kit.conf`). One
result file (`kit-result.yaml`).

ctier is a way to compile consequence
classes onto gateway operations. This
package is the Apigee column of that
work: not a product pitch, not a full
audit, not a claim that Apigee equals
Kong or APISIX.

## Why half an hour matters

Two engines in this repository already
agree because the same people wrote
both. That agreement does not transfer
to Apigee. Until someone who was not in
the room runs the checklist, the Apigee
column is artefact-only. Your run is
that check. Thirty minutes of setup and
one command beats another month of
"it should work".

## What comes back

`kit-result.yaml`. Rows are `passed`,
`failed`, `skipped`, or `inconclusive`.
Read `RESULT.md` once. Do not diagnose.

## What we will do with it

- Diff your file against what the
  checklist asks.
- Separate environment misses (token,
  route, empty optional URL) from
  checklist failures.
- Use the outcome to fill the Apigee
  column next to Kong and APISIX.
- Fix our docs or packaging when you
  stop at an instruction that does not
  work.

## What we will not do

Answer these before you start:

| Question | Answer |
|---|---|
| Will you publish my organisation name? | **No**, not without asking you first in a separate message. |
| Will you publish my environment name? | **No**, same rule. |
| Will you publish my raw result file? | **No.** We may quote anonymised row counts (passed / failed / skipped / inconclusive) and case ids. |
| Will tokens or Trace dumps be stored? | **Do not send tokens.** If a token appears in a paste, we discard it. We do not want Trace screenshots. |
| Will "Apigee failed X" name my org? | Public statements will say **Apigee** (the product), or "an Apigee eval org", not your org id — unless you agree otherwise in writing. |
| Is a clean file a public claim you implement the whole specification? | **No.** It is a claim about the cases in conformance-kit/1.1. The checklist is not the specification. |

## Known differences — before you run

Apigee is not Kong or APISIX. Some
gaps are about **Apigee as a target**,
not about your organisation. Expect
them. Do not "fix" them before sending
the file.

### Expected skips (stock package)

With `kit.conf.example` defaults
(`kit_level: "2"`, optional URLs empty):

- About **11 skipped** rows (see
  `RESULT.md`) when optional URLs stay
  empty. Records and approval checks
  cannot run until you wire a collector
  and (for L3) a live custody host.
  Observer: ship `observer/`; empty
  `kit_observer` still skips C16.
- **C13** always skips on a URL run
  (`covered at generation rather than runtime`).

That is a result about **what this
package can see on Apigee**, not about
whether you misconfigured the org.

### Expected inconclusive

- **C12** (`GET /estate/unknown`) is
  **inconclusive** on bare `404` if you
  did not provision a routed-but-
  ungoverned path (`PROVISION.md` §5).
  Inconclusive ≠ failed.

### Expected fails if you aim too high

- `kit_level: "3"` with the stock
  `custody.example.invalid` host:
  withhold rows **fail**. Use level 2,
  or replace the host and set
  `kit_custody`.
- No bearer scopes: many rows **fail**
  with 401/403 before compiled policy
  runs. Still send the file.

### Apigee cannot satisfy from this artefact alone

These are about Apigee + this package,
not your env hygiene:

| Obligation | Why |
|---|---|
| Retrievable decision records (C10 via `kit_records`) | Package ships `collector/` and generate emits `SC-RecordDecision`. Replace the placeholder host and set `kit_records`. Trace alone is still not a sink. |
| Backend observer cases (C6, C7, C16) | Package ships `observer/`; you must run it, aim the target endpoint, and set `kit_observer`. Empty URL → skip. |
| Precedence against a PreProxy FlowHook (C11 beyond the clean path) | Untestable from this artefact; fragment mode cannot claim it. |
| Local runtime parity | There is no Apigee runtime in this repository. |

If you later add a records collector and
an observer, those skips can become
runs. Until then, skips are the honest
Apigee column.

Permitted target differences for
kit/1.1 are listed in
`../../../engine/docs/kit/divergence.md`
for maintainers. You do not need that
file to run.

## Where to go next

1. `PROVISION.md` — what to create first
2. `RUN.md` — one command, one config
3. `RESULT.md` — how to read the file
4. Send `kit-result.yaml` back
