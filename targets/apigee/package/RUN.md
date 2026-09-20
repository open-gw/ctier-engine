# What you run

One command. One configuration file.
One result file. That is the whole run.

This package exercises
**conformance-kit/1.1** — a fixed checklist
of HTTP checks against a running proxy.
A result means something only against
that version. You do not need the
specification, Docker Compose, or this
repository's Kong/APISIX stacks.

## Before this page

1. Read `COVER.md` (what this is, what
   we do with your result, what Apigee
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
| `gateway_url` | yes | Base URL of the deployed proxy, no path. Example: `https://myorg-eval.apigee.net` |
| `gateway_token` | yes | Bearer token the proxy will accept |
| `apigee_org` | yes (for your reply) | Apigee organisation name. Example: `myorg` |
| `apigee_environment` | yes (for your reply) | Environment the proxy is deployed to. Example: `eval` |
| `apigee_proxy_name` | yes (for your reply) | Proxy name after import |
| `kit_records` | no | GET URL returning `{ "records": [ … ] }` |
| `kit_observer` | no | GET URL of the backend request log |
| `kit_custody` | no | Base URL of the approval service (`GET /v1/pending`, `POST /v1/decisions/{id}`) |
| `kit_level` | no | `"3"` if that approval service is in front of the gateway; `"2"` if not. Example default for a first Apigee run: `"2"` |
| `kit_out` | no | Result path. Default `kit-result.yaml` |

`apigee_org`, `apigee_environment`, and
`apigee_proxy_name` are not sent to the
proxy. They stay in one place so your
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

If those paths are not on your proxy,
say so when you send the file back.

## What this package does not include

Do not invent substitutes. If a step
needs one of these, stop and report
the gap — or omit the matching optional
URL and accept the skip.

| Missing from this package | Effect if you proceed without it |
|---|---|
| A standalone installer of the runner | You need this repository's `engine/` installed (`cd ../../../engine && pip install -e ".[dev,serve]"` from this directory, or the same from the repo root's `engine/`). There is no wheel inside `package/`. |
| An Apigee deploy script | Zip `generated/apiproxy` and import it yourself. This directory does not call the Management API. |
| OAuth / JWT product wiring | ctier does not configure your Apigee product. You must issue a token with the scopes in `generated/authorization.yaml`. |
| A retrievable decision-record URL | Ship `collector/` (`GET/POST /v1/ledger`). Generated proxy POSTs there (`SC-RecordDecision`); replace `records.example.invalid` and set `kit_records`. Trace `print()` is still not this URL. |
| A backend observer endpoint | Ship `observer/` (echo + `GET /_harness/requests`). Point the proxy target at it and set `kit_observer`. Leave empty to accept the C16 skip. |
| A real approval (custody) service | The bundle is compiled with `https://custody.example.invalid`. Leave `kit_custody` empty and keep `kit_level: "2"` unless you replace that host and point `kit_custody` at a live service. |
| A local Apigee runtime | There is none in this repository. Classification against Apigee is artefact-only until you run on an organisation you control. |

The older `harness.py` path compares a
reference classifier to your proxy. It
is not this run. This run is
`./run.sh kit.conf` only.
