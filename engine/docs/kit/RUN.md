# Running this against your gateway

You have a running gateway and a token
that can call it. You do not need this
repository's layout, Docker Compose, or
anyone's plugin source.

This is `conformance-kit/1.1`. Send back
the result file. A result means
something only against that version.

## What to set

Required:

| Name | What it is |
|---|---|
| `GATEWAY_URL` | Base URL of the gateway, no path. Example: `https://gw.example.com` |
| `GATEWAY_TOKEN` | A bearer token the gateway will accept |

Optional. Omit a row you do not have.
Those checks are skipped. A skip is not
a pass. Every skip names one reason
from a fixed set (below).

| Name | What it is |
|---|---|
| `KIT_RECORDS` | HTTP GET that returns `{ "records": [ … ] }` — the decisions written so far |
| `KIT_OBSERVER` | HTTP GET of the last requests the backend received, as a JSON array |
| `KIT_CUSTODY` | Base URL of the service that lists waiting items (`GET /v1/pending`) and accepts a decision (`POST /v1/decisions/{id}`) |
| `KIT_LEVEL` | `3` if that service is in front of the gateway, else `2`. Default `3` |
| `KIT_OUT` | Where to write the result. Default `kit-result.yaml` |

The runner will call, among others:

- `GET /accounts/12345/balance`
- `GET /accounts/12345/transactions?limit=101`
- `PUT /customers/12345/preferences/communication`
- `POST /payments`
- `POST /accounts/12345/statements/export`
- `PUT /config/feature-flags`
- `GET /estate/unknown`

If those paths are not on your gateway,
say so when you send the file back.

### C12 — provision a routed path

`GET /estate/unknown` must hit a path
that is **routed at the enforcement
point** and **absent from the
composition** (no assignment). That is
what C12 measures.

The kit cannot add routes on your
gateway. If the path is not routed, a
proxy often answers bare `404` with an
empty body. That is not a C12 miss —
nothing reached the governed set — and
the kit will report **inconclusive**,
not failed. Provision the route (or
point the case at one you already have)
before reading the row as a fail.

## What to run

```
pip install -e .
python -m ctier.kit --url "$GATEWAY_URL" --token "$GATEWAY_TOKEN" --out kit-result.yaml
```

Add `--records`, `--observer`, `--custody`,
and `--level` when you have them. Same
as the table above.

One command. It writes `kit-result.yaml`
(or `KIT_OUT`). Exit status is `1` if
any row failed.

## What to send back

`kit-result.yaml`.

Each row is `passed`, `failed`,
`skipped`, or `inconclusive`. A failed
row includes what came back: the
status, and the field that did not
match. Do not edit the file. Do not
send a summary instead of the file.

The report counts how many cases
**ran** (`passed` + `failed` +
`inconclusive`). Skips are not runs.

`inconclusive` means the case ran and
the answer does not distinguish
conformance from something the kit
cannot see. It is not a fail.

### What a skip means

A skip is not a pass. Every skipped row
carries exactly one reason from this
set:

| Reason | Meaning |
|---|---|
| `not applicable at this level` | The case belongs to another deployment level than this run. |
| `requires a capability this target lacks` | The runner was not given a records URL, observer URL, or approval surface the case needs. |
| `covered at generation rather than runtime` | The obligation is checked when compiling, not by a request to a running gateway. |

If you could not set a variable, say
which one and send the file anyway.
