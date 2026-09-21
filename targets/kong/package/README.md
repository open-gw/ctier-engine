# Kong package — verify on the local rig (or any Kong that loads the deck)

This directory is for someone who can run Kong. A local compose stack
lives under `targets/kong/live/`. The checklist is the same
**conformance-kit/1.1** as Apigee's package; only provisioning is
Kong-shaped. Get the package from
[open-gw/ctier-engine](https://github.com/open-gw/ctier-engine)
(`targets/kong/package/`).

## Start here (external run)

If you were sent this package to run the
checklist, read in order:

1. `COVER.md` — what this is, privacy, known differences
2. `PROVISION.md` — what to create first
3. `RUN.md` — one config, one command
4. `RESULT.md` — how to read the file (do not diagnose)

`kit.conf.example` → `kit.conf`, then
`./run.sh kit.conf`.

## Layout

| Path | What |
|---|---|
| `COVER.md` | Covering note for a Kong practitioner |
| `PROVISION.md` | What to create before the run |
| `RUN.md` / `kit.conf.example` / `run.sh` | One command, one config, one result file |
| `RESULT.md` | How to read `kit-result.yaml` |
| `generated/` | Bundle from the same composed `consequence-tiered-api.yaml` the live demo uses (`datetime` fixed at compose `NOW`). Written by `./build.sh`. |
| `build.sh` | Regenerates `generated/` from the engine. |

## Deploy (local)

1. Install the engine (`cd engine && pip install -e ".[dev,serve]"`).
2. `./build.sh` from this directory.
3. Start `targets/kong/live/` with `CTIER_KONG_YAML` pointing at
   `generated/kong.yaml` and the Keycloak realm at
   `generated/keycloak-realm.json`.
4. Mint a token with the generated scopes; put it in `kit.conf`.
5. Optional: set `kit_records`, `kit_observer`, `kit_custody` as
   `PROVISION.md` describes.

## Same handoff as Apigee

COVER → PROVISION → RUN → RESULT. Same
vocabulary, same kit version, same
outcomes. Target-specific steps live
only in PROVISION and the example
config field names.
