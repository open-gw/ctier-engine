# What you run

One command. One configuration file.
One result file. That is the whole run.

This package exercises
**conformance-kit/1.1** — a fixed checklist
of HTTP checks against a running proxy.
A result means something only against
that version. You do not need the
specification. You do need Kong running
with the generated deck (see
`PROVISION.md`).

## Before this page

1. Read `COVER.md` (what this is, what
   we do with your result, what Kong
   is expected to skip or fail).
2. Follow `PROVISION.md` (what to create
   first). Skipping a step has a named
   consequence; it is not the same as a
   failed check.

## The configuration file

Copy the example and fill it in:

```
cp kit.conf.example kit.conf
```

Every value is named in that file, with
an example. Do not assemble flags.

| Name | Required? | What it is |
|---|---|---|
| `gateway_url` | yes | Base URL of the Kong proxy, no path. Local example: `http://127.0.0.1:18000` |
| `gateway_token` | yes | Bearer token Kong will accept |
| `kong_deployment` | yes (for your reply) | How you loaded the deck. Example: `local-compose` or `deck-sync-staging` |
| `kit_records` | no | GET URL returning `{ "records": [ … ] }` |
| `kit_observer` | no | GET URL of the backend request log |
| `kit_custody` | no | Base URL of the approval service |
| `kit_level` | no | `"3"` if that approval service is in front of the gateway; `"2"` if not. Example default: `"2"` |
| `kit_out` | no | Result path. Default `kit-result.yaml` |

`kong_deployment` is not sent to the
proxy. It stays in one place so your
reply matches what you ran.

## The command

From this directory, with the engine
installed (see gaps below):

```
./run.sh kit.conf
```

That writes the file named in
`kit_out` (default `kit-result.yaml`
next to the config). Exit status is
`1` if any row **failed**. Skips and
inconclusives are not failures.

Then open `RESULT.md`. Do not diagnose
failures yourself — send the file.

## Paths the checklist will call

Among others:

- `GET /accounts/12345/balance`
- `GET /accounts/12345/transactions?limit=101`
- `PUT /customers/12345/preferences/communication`
- `POST /payments`
- `POST /accounts/12345/statements/export`
- `PUT /config/feature-flags`
- `GET /estate/unknown`

## Package gaps (not papered over)

1. **No standalone runner** — needs
   `engine/` `pip install -e`.
2. **No one-click compose up from this
   directory** — you start
   `targets/kong/live/` (or your own
   Kong) yourself.
3. **No automatic token mint** — you
   put a bearer in `kit.conf`.
4. **Records URL is optional** — Level 2
   without a collector skips C10.
5. **Observer URL is optional** — echo's
   harness is not published by default.
6. **C12 needs an extra route** — stock
   generate does not add
   `/estate/unknown`.

## After the run

Open `RESULT.md`. Send
`kit-result.yaml`. Stop.
