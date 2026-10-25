# What to provision first

Do these before `./run.sh`. Each row
says what to create, why, and what the
result file will show if you skip.

A skip in the result file is not a
failure. An **inconclusive** row is
not a failure either. A **failed** row
is a mismatch on a check that ran.
If you skip a provision step and later
read a red row as "Kong is wrong",
you will misread the file — match the
row below first.

## Terms used on this page

- **Composition** — the list of
  operations and their assigned
  consequence classes that was compiled
  into this deck (see
  `generated/ctier-generate.json`).
- **Governed set** — the operations that
  list assigns. A path outside that list
  is ungoverned.
- **Approval service (custody)** — the
  optional service that holds a
  class-3 request for a human decision
  (`GET /v1/pending`,
  `POST /v1/decisions/{id}`).

## Checklist

### 1. Install the runner

**Create:** a Python environment with
this repository's `engine/` installed
(`pip install -e ".[dev,serve]"` from
`engine/`).

**Why:** `./run.sh` imports
`ctier.kit`. The package directory does
not ship a standalone binary.

**If you skip:** `./run.sh` fails
immediately (import / command error).
No result file. That is not a
conformance failure.

### 2. Generate or refresh the bundle

**Create:** `generated/` via
`./build.sh` from this directory.

**Why:** the deck Kong loads must
match the checklist paths and the
scopes in `generated/authorization.yaml`.

**If you skip:** you may load an empty
or stale `kong.yaml`. Deploy errors are
yours to fix; they are not rows in the
result file.

### 3. Start Kong (local rig) or load the deck

**Create:** a running Kong that has
loaded `generated/kong.yaml` and the
`ctier` plugin.

**Local path (this repository):** from
the repo root, use the live compose
under `targets/kong/live/` the same way
the project's live tests do — bind
`CTIER_KONG_YAML` to
`generated/kong.yaml` (absolute path),
import the generated Keycloak realm,
bring the stack up. Gateway:
`http://127.0.0.1:18000`. Custody:
`http://127.0.0.1:18200`. Keycloak:
`http://127.0.0.1:18400`.

The committed `engine/ctier/authz/keycloak-rsa.json`
and `public.pem` are a test key generated
for this repository, used by nothing
outside this lab, and must not be reused.
`generate()` reads them, and Keycloak boots
from that realm. A visitor does not
generate a key. The golden files stay on
the placeholder. The comparison does not
use the key's value, so the two golden
tests stay green.

**Why:** unlike Apigee, a local Kong
runtime ships here. You still have to
start it.

**If you skip:** `gateway_url` will not
answer. The run fails at HTTP. That is
not a checklist failure against
Kong-as-product; it is "nothing was
running".

### 4. Issue a bearer token

**Create:** a token carrying the
operation scopes from
`generated/authorization.yaml`. Put it
in `gateway_token`.

**Local path:** the live Keycloak realm
in `generated/keycloak-realm.json`
matches the deck. Mint a token the same
way the live tests do (client
credentials / password grant against
the realm), or copy the method from
`engine/tests/live/rig.py`.

**If you skip:** most calls return
401/403 before compiled policy runs.
Those rows **fail**. Still send the
file.

### 5. Routed but ungoverned path (C12)

**Create:** a route on this Kong for

`GET /estate/unknown`

The path must be **routed** at the
enforcement point and **absent from the
composition** (no assignment in the
compiled list). Do not add it to the
composition and regenerate. Add only
the route (fragment merge or a
post-generation edit), so the global
`ctier` plugin still sees it and the
name is not in `governed-set`.

**Why:** stock Kong without that route
answers bare `404`. The checklist
measures a routed unassigned path.

**If you skip:** the result file will
show **inconclusive** for
`c12-unassigned-is-refused-undetermined`,
not **failed**.

### 6. Approval service (only for level 3)

**Create:** custody on the compose
network (already in
`targets/kong/live/`), regenerate with
custody URL `http://custody:8080`, set
`kit_custody: http://127.0.0.1:18200`
and `kit_level: "3"`.

**If you skip:** keep `kit_level: "2"`
and leave `kit_custody` empty.
Level-3-only rows are **skipped** with
`not applicable at this level`.

### 7. Records URL (optional)

**Create:** an HTTP GET that returns
`{ "records": [ … ] }`. Point
`kit_records` at it.

**Local path:** compose custody
`http://127.0.0.1:18200/v1/ledger`
when the deck was generated with
custody (decisions POST there). The
claimed C10 sink remains the gateway
error log; the ledger is a permitted
collector. Level 2 without custody
POST may leave the ledger empty — then
leave `kit_records` empty and accept
C10 skips, or build a log collector.

**If you skip:** leave `kit_records`
empty. Rows that need records are
**skipped** with
`requires a capability this target lacks`.

### 8. Backend observer (optional)

**Create:** an HTTP GET of recent
backend requests as a JSON array (or
`{ "requests": [ … ] }`). Point
`kit_observer` at it.

**Local path:** the echo service has
`/_harness/requests` on the upstream
network only. Publish it, proxy it, or
leave `kit_observer` empty.

**If you skip:** leave `kit_observer`
empty. Observer rows are **skipped**
with
`requires a capability this target lacks`.

## Order

1 → 2 → 3 → 4 → 5, then optional 6–8,
then `RUN.md`.

If you only do 1–4 and run, you still
get a result file. Read every
inconclusive and skip reason before
treating a row as a product defect.
