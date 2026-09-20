# What to provision first

Do these before `./run.sh`. Each row
says what to create, why, and what the
result file will show if you skip.

A skip in the result file is not a
failure. An **inconclusive** row is
not a failure either. A **failed** row
is a mismatch on a check that ran.
If you skip a provision step and later
read a red row as "Apigee is wrong",
you will misread the file — match the
row below first.

## Terms used on this page

- **Composition** — the list of
  operations and their assigned
  consequence classes that was compiled
  into this proxy (see
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
`./build.sh` from this directory (or
use the bundle `make demo` already
wrote).

**Why:** the proxy you import must
match the checklist paths and the
scopes in `generated/authorization.yaml`.

**If you skip:** you may import an
empty or stale tree. Deploy errors are
yours to fix; they are not rows in the
result file.

### 3. Import and deploy the proxy

**Create:** zip `generated/apiproxy`,
import it into **your** organisation
and environment, deploy it. Point the
target endpoint at a backend you
control that can echo method, path,
and headers.

**Why:** there is no local Apigee
runtime in this repository.

**If you skip:** `gateway_url` will not
answer. The run fails at HTTP. That is
not a checklist failure against
Apigee-as-product; it is "nothing was
deployed".

### 4. Issue a bearer token

**Create:** an OAuth product / JWT
setup that issues tokens carrying the
operation scopes from
`generated/authorization.yaml`. Put the
token in `gateway_token`.

**Why:** the package does not configure
your Apigee product.

**If you skip:** most calls return
401/403 from Apigee before the compiled
policies run. Those rows **fail**. That
is an environment setup miss, not proof
the compiled classes are wrong — still
send the file; do not re-interpret it
yourself.

### 5. Routed but ungoverned path (C12)

**Create:** a route on this proxy (or
on a shared flow in front of it that
still hits these policies) for

`GET /estate/unknown`

The path must be **routed** at the
enforcement point and **absent from the
composition** (no assignment in the
compiled list). Do not add it to the
composition and regenerate. Add only
the route.

**Why:** the checklist measures whether
an unassigned but reachable path is
refused as undetermined. The runner
cannot add routes on your gateway.

**If you skip:** many Apigee setups
answer bare `404` with an empty body.
The result file will show
**inconclusive** for
`c12-unassigned-is-refused-undetermined`,
not **failed**. Inconclusive means the
runner cannot tell "never routed" from
"routed and wrongly handled". Tell that
apart from a failure before you worry.

### 6. Approval service (only for level 3)

**Create:** a service that implements
`POST /v1/pending` behaviour as in
`engine/ctier/custody`, replace
`custody.example.invalid` in the
deployed policies, and set
`kit_custody` plus `kit_level: "3"`.

**Why:** class-3 withhold (HTTP 202)
needs a live approval path.

**If you skip:** keep `kit_level: "2"`
and leave `kit_custody` empty. Level-3
only rows are **skipped** with
`not applicable at this level`. If you
leave `kit_level: "3"` with the
placeholder host, withhold rows will
**fail** (you asked for level 3 without
the service).

### 7. Records URL (optional)

**Create:** run the collector this
package ships, replace
`https://records.example.invalid` in
the generated `SC-RecordDecision`
policy with a URL the Message Processor
can reach, and point `kit_records` at
the same host's GET.

```
./collector/run.sh
```

That listens on `:8090` and serves
`GET /v1/ledger` → `{ "records": [ … ] }`.
The generated proxy POSTs decisions
here on execute and refuse paths
(fail-open if unreachable). Trace
`print()` remains debug-only. Details:
`collector/README.md`.

**Why:** Apigee Trace is not
`kit_records`. Without a reachable
collector, C10 cannot run.

**If you skip:** leave `kit_records`
empty. Rows that need records are
**skipped** with
`requires a capability this target lacks`.
That is expected until the collector
is wired. It is not a pass and not a
fail.

### 8. Backend observer (optional)

**Create:** run the observer this
package ships, then point the proxy
**target endpoint** at it and
`kit_observer` at its log URL.

```
./observer/run.sh
```

That listens on `:8080` and exposes
`GET /_harness/requests` (JSON array of
`method` / `path` / `headers`). Same
contract as the Kong/APISIX live echo.
It is a real upstream log, not a mock
gateway and not custody. Details:
`observer/README.md`.

**Why:** without a reachable observer
URL, C16 (and soft C1) cannot run.
The package now ships the process; you
still have to place it where Apigee
and `./run.sh` can reach it.

**If you skip:** leave `kit_observer`
empty. Rows that need the observer are
**skipped** with
`requires a capability this target lacks`.

## Order

1 → 2 → 3 → 4 → 5, then optional 6–8,
then `RUN.md`.

If you only do 1–4 and run, you still
get a result file. Read every
inconclusive and skip reason before
treating a row as a product defect.
