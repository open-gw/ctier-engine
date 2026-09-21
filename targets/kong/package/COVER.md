# Covering note — read this first

Source:
https://github.com/open-gw/ctier-engine
(`targets/kong/package/`).

You know Kong. You do not know ctier.
You will not read the specification.
You cannot ask the same day. Stop at
the first instruction that does not
work and send what you have.

## What this is

A half-hour check that a running Kong
proxy answers
**conformance-kit/1.1** — a fixed
checklist of HTTP cases. One
configuration file (`kit.conf`). One
command (`./run.sh kit.conf`). One
result file (`kit-result.yaml`).

ctier is a way to compile consequence
classes onto gateway operations. This
package is the Kong column of that
work: the same four documents as the
Apigee handoff, pointed at the local
Kong rig in this repository (or any
Kong that loads the generated deck).

## Why half an hour matters

Two engines in this repository already
agree because the same people wrote
both. That agreement does not transfer
to a stranger's run. Until someone who
was not in the room runs the checklist
from these pages alone, the Kong
column for an external reader is still
author-run. Your run is that check.

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
- Use the outcome next to the APISIX
  and Apigee columns.
- Fix our docs or packaging when you
  stop at an instruction that does not
  work.

## What we will not do

Answer these before you start:

| Question | Answer |
|---|---|
| Will you publish my hostnames? | **No**, not without asking you first in a separate message. |
| Will you publish my raw result file? | **No.** We may quote anonymised row counts and case ids. |
| Will tokens be stored? | **Do not send tokens.** If a token appears in a paste, we discard it. |
| Will "Kong failed X" name my machine? | Public statements will say **Kong** (the product), not your hostname — unless you agree otherwise in writing. |
| Is a clean file a public claim you implement the whole specification? | **No.** It is a claim about the cases in conformance-kit/1.1. The checklist is not the specification. |

## Known differences — before you run

Kong here has a local compose stack.
That is target-specific
**provisioning**, not a second
checklist. The cases and vocabulary
are the same as Apigee's package.

### Expected skips (stock package, empty optionals)

With `kit.conf.example` defaults
(`kit_level: "2"`, optional URLs empty):

- About **11 skipped** rows (see
  `RESULT.md`). Records, observer, and
  approval checks cannot run until you
  point the optional URLs at the live
  rig (or equivalents you control).
- **C13** always skips on a URL run
  (`covered at generation rather than runtime`).

### Expected inconclusive

- **C12** (`GET /estate/unknown`) is
  **inconclusive** on bare `404` if you
  did not provision a routed-but-
  ungoverned path (`PROVISION.md` §5).
  Inconclusive ≠ failed. Stock Kong
  without that route answers `404`.

### Expected fails if you aim too high

- `kit_level: "3"` without a live
  approval service: withhold rows
  **fail**. Use level 2, or set
  `kit_custody` to the compose custody
  URL after generation with custody.
- No bearer scopes: many rows **fail**
  with 401/403 before compiled policy
  runs. Still send the file.

### Kong can satisfy more than Apigee from this artefact

| Obligation | Why |
|---|---|
| Retrievable decision records (C10) | Compose custody exposes `GET /v1/ledger` → `{ "records": [ … ] }`. Point `kit_records` there when decisions are posted. The claimed sink is still the gateway error log; ledger is a permitted collector in front of it. |
| Backend observer (C6, C7, C16) | Compose echo exposes `/_harness/requests` on the upstream network. Publish or proxy it, or leave `kit_observer` empty and accept skips. |
| Local runtime | `targets/kong/live/` is in this repository. |

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
