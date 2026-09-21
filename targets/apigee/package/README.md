# Apigee package — verify on an organisation you control

This directory is for someone who has an Apigee organisation. There is **no
local Apigee runtime** in this repository. The bundle is generated, not run.
Get the package from
[open-gw/ctier-engine](https://github.com/open-gw/ctier-engine)
(`targets/apigee/package/`).

`print()` in the generated JavaScript is Trace (`stepExecution-stdout`). It is
not a Cloud Logging sink. Precedence against a PreProxy FlowHook is untestable
from this artefact.

## Start here (external run)

If you were sent this package to run the
checklist against your org, read in order:

1. `COVER.md` — what this is, privacy, known differences
2. `PROVISION.md` — what to create first
3. `RUN.md` — one config, one command
4. `RESULT.md` — how to read the file (do not diagnose)

`kit.conf.example` → `kit.conf`, then
`./run.sh kit.conf`.

## Layout

| Path | What |
|---|---|
| `COVER.md` | Covering note for an Apigee practitioner |
| `PROVISION.md` | What to create before the run |
| `RUN.md` / `kit.conf.example` / `run.sh` | One command, one config, one result file |
| `RESULT.md` | How to read `kit-result.yaml` |
| `generated/` | Bundle from the same composed `consequence-tiered-api.yaml` the live Kong/APISIX demo uses (`datetime` fixed at compose `NOW`). Written by `./build.sh` or `make demo`. |
| `build.sh` | Regenerates `generated/` from the engine. |
| `VERIFY.md` | Older differential claims (harness). Not the kit run. |
| `REPORT.md` | Older harness report-back template. |
| `observer/` | Backend echo for `kit_observer` (`GET /_harness/requests`). |
| `collector/` | Decision sink for `kit_records` (`GET/POST /v1/ledger`). Not custody. |
| `TODAY.md` / `NOW.md` | Kit/1.1 counts before and after gap work (task 66). |

## Deploy

1. Install the engine (`cd engine && pip install -e ".[dev,serve]"`).
2. `./build.sh` from this directory (or run `make demo` at the repo root; it writes the same bundle).
3. Zip `generated/apiproxy` as you would any Apigee API proxy and import it into **your** org and environment.
4. Point the target endpoint at the shipped observer (`./observer/run.sh`) or any backend that echoes method, path, and headers and exposes a request log the kit can GET.
5. Bind an OAuth product / JWT policy that issues tokens carrying the generated operation scopes (`authorization.yaml` in `generated/`). ctier does not configure your Apigee OAuth product for you.
6. For C10: run `./collector/run.sh`, replace `https://records.example.invalid` in `SC-RecordDecision`, set `kit_records`. Trace `print()` is not that URL.
7. If you will exercise withhold: deploy a custody that implements `POST /v1/pending` and `POST /v1/decisions/{id}` as in `engine/ctier/custody`, and set the generated `SC-CustodyPending` URL to it. The bundle in `generated/` is compiled **with** a custody URL placeholder (`https://custody.example.invalid`). Replace that host before expecting 202. Do **not** use the records collector as custody.

## Unproven, on purpose

- No local runtime — classification agreement with Apigee is artefact-only until you run this package.
- `print('[ctier-decision] …')` is Trace; the retrievable sink is `SC-RecordDecision` → collector when wired.
- C11 precedence against a PreProxy FlowHook is not in the artefact; fragment mode cannot claim it.
- The live demo never executes these policies.

For the kit run, send `kit-result.yaml`
as `RESULT.md` says. The older harness
path still uses `VERIFY.md` /
`REPORT.md`.
