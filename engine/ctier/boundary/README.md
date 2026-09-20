# runtime-suite/0.3.0-draft

Live-only. Observed behaviour of a running deployment. Not promoted
into the specification.

The split with `conformance-corpus` is **how a case is evaluated**,
not where the bytes go:

| Artefact | Evaluated by |
|---|---|
| `conformance-corpus` | comparing documents, offline, without deploying anything |
| this suite | observing a running deployment |

Headers arriving at a backend and records arriving at a sink are both
the second kind. `recordSource` is a fixture capability under that
division, not a special case bolted onto a header suite.

This draft used to be named `boundary-suite`. There is no compatibility
shim for that name. It was a draft with no external consumers; a shim
would have been a row in a deprecation table that is empty on purpose.

A format used by one implementation is a serialisation; a format used
by two is an interface, and only the second has been tested as one.
This draft has been read by its author. It is a serialisation until a
second implementation is held to it. The format reaches a version
without `-draft` when an implementation other than the reference one
has been held to it.

The classification corpus establishes that two implementations agree
on a decision. This one establishes that they behave the same when
observed at runtime. Neither establishes that either is *correct* —
both could agree and both be wrong.

**Classification correctness belongs to the corpus.** This suite never
asserts which tier is right.

**Nothing visible only by reading the implementation's own memory.**
If an assertion needs custody's internal state rather than something
custody publishes, it is out of scope.

`ctierSchema`: `runtime-suite/0.3.0-draft`.

---

## What a case is

A request to send, a declared HTTP status, and expectations about
headers that arrived at the backend, records that arrived at a
sink, or `equals` against a decision record. Header kinds:

| Kind | Meaning |
|---|---|
| `absent` | the named header did not reach the backend |
| `present` | it did, non-empty |
| `equals` | its backend-observed value matches another observation |
| `notEquals` | its backend-observed value is not this literal |

Record kinds, gated on `recordSource`:

| Kind | Meaning |
|---|---|
| `recorded` | a schema-valid record of this type was written during the case, matching any listed fields |
| `unrecorded` | no record of this type was written during the case |

A record is matched against its JSON Schema, not by string
comparison. A payload that does not validate is reported as
`schema-invalid`. A payload that validates but disagrees on a
listed field is a different failure. An Observed sample is not
this mechanism.

`unrecorded` exists because a missing record was the defect this
suite is here to catch. Presence-only would have passed 35.

When an agent-facing body carries `agentAction`, the runner
asserts the pairing with `X-Agent-Action` on the client
response: the two fields describe one instruction. A conflict
fails. Checking that each exists would have passed while they
disagreed. C5's named `202` mechanism and C9's named `423`
mechanism also require the header as the mirror. Absence of
the header on other dispositions is not asserted as a defect.

Do not add an assertion that reads custody's in-memory tables. The
sink is what custody (or the gateway log) *publishes*.

`expect.status` is required. Header assertions run only when the
observed status matches. A refused request that never reached the
backend would otherwise pass `absent` vacuously. Declaring status
is not asserting a disposition — only the HTTP status the fixture
returned.

`requires` names fixture capabilities. A runner that lacks one
**skips** the case and reports the skip. A skip is not a pass. Counts
must not let those blur.

```yaml
ctierSchema: runtime-suite/0.3.0-draft
cases:
  - id: namespace-stripped
    requires: [observer]
    send:
      method: GET
      path: /accounts/12345/balance
      headers:
        x-ctier-unknown-audit: forged-by-the-agent
    expect:
      status: 200
      absent: [x-ctier-unknown-audit]
  - id: forged-tier-not-surviving
    requires: [observer]
    send:
      method: GET
      path: /accounts/12345/balance
      headers:
        x-ctier-tier: "9"
    expect:
      status: 200
      notEquals:
        x-ctier-tier: "9"
```

Header names in `expect` are compared case-insensitively after
lowercasing.

`equals` values are pointers, not literals. `notEquals` values **are**
literals — the forged value that must not survive:

| Pointer | Observation |
|---|---|
| `decision.correlationId` | that field on the matching decision record |
| `decision.idempotencyKey` | the same record |
| `response.<name>` | the header on the **client-observed** HTTP response |
| `observer.<name>` | another header from the same backend snapshot |

A pointer that starts with `decision.` implies `recordSource` even if
`requires` omitted it.

Names the enforcement point itself sets (`x-ctier-deployment`,
`x-ctier-tier`, `x-ctier-operation`, `x-ctier-correlation-id`) are **not** valid `absent`
targets for an injected client header of the same name: the gateway
strips the agent's value and writes its own. The namespace property
for those names is the unknown-name cases plus the aliases that sit
outside the prefix. For a name that is re-emitted, `notEquals` is
the assertion that the agent's value did not survive.

`X-Ctier-Tier` is the same header as `x-ctier-tier` after
normalization. `absent` is wrong for it: the header **is** at the
backend after the enforcement point writes its own. `present`
passes on a forged `9` that survived. `notEquals: {x-ctier-tier: "9"}`
says the forged value did not survive, and does not say what the
surviving value is.

Do not add an `equals`-the-compiled-tier kind. The classification
corpus already owns that claim. This suite's job at the wire is that
the agent's `9` is gone; the corpus's job is that the operation is
the compiled tier. Two normative artefacts; one claim each.

`Idempotency-Key` is the same occupation: inbound it is stripped;
on execute with custody the enforcement point writes the derived
key under that name. `absent` of the name would fail a conforming
Level-3 fixture. `notEquals` against the agent's value says the
forge did not survive; the equals case still says the surviving
value is the ledger's. `X-Idempotency-Key` is not re-emitted and
stays a valid `absent`.

---

## Capabilities

| Name | The fixture provides |
|---|---|
| `observer` | the last-N backend header log, this document's contract |
| `probe` | a component at a declared position in the chain that records reserved inbound names it saw, as `x-boundary-probe` on the forwarded request |
| `recordSource` | a way to list records written during a case (see Record source) |

`x-boundary-probe` is **outside** the `x-ctier-*` namespace so the
strip will not remove it. The probe watches agent-reserved names
only: `x-correlation-id`, `x-idempotency-key`,
and any `x-ctier-*` name that is not in the emit set
(`deployment`, `correlation-id`, `tier`, `operation`,
`composition`). It does not watch `Idempotency-Key`: that name is
re-emitted on execute with the derived value, so an after-strip
probe would always see it. It sets `x-boundary-probe` to a
comma-separated list of watched names if it saw any; it sets
nothing if it saw none.

A precedence case asserts `absent: [x-boundary-probe]`. In bundle
mode the probe sits **after** the strip (the path owner has already
run). In Kong fragment mode it sits **before** the strip (the estate);
that failure is a required result. On APISIX, fragment merge concatenates
function-list plugins with ctier's strip first, so the same case is
expected to **pass** — requirement 3 does not apply to that slot.
The suite itself only passes or fails; the engine's own test asserts
the per-target shape.

---

## Observer contract — `boundary-observer/0.1.0-draft`

Versioned with the case format. A second implementation stands this
up in an afternoon. Transport-plain HTTP. No auth beyond whatever
the fixture already uses for its backend.

### Fetch the last N requests the backend received

```
GET /_harness/requests
```

**Response:** `200`, `Content-Type: application/json`, a JSON array.
Index `0` is the oldest entry still retained. The last element is
the most recent request. A draft implementation MAY cap the log;
the runner reads from the end.

Each element:

```json
{
  "method": "GET",
  "path": "/accounts/12345/balance",
  "headers": {
    "host": "echo:8080",
    "x-ctier-correlation-id": "…"
  }
}
```

| Field | Rule |
|---|---|
| `method` | HTTP method, uppercase |
| `path` | request target as the backend saw it, including query if present |
| `headers` | object. Keys **lowercase**. Values strings. Combine duplicates with `, ` if the server coalesced them; do not invent a structured multi-value type |

No other fields are required. Extra fields are ignored.

`GET /_harness/requests?limit=1` is a MAY: return only the newest
`limit` entries. Runners that do not send `limit` must still work.

The path is fixed. Do not hide it behind a different prefix without
forking this draft.

### Convenience: the same request's echo body

A fixture backend MAY also respond to the operation under test with
`200` and `{"method","path","headers"}` for **that** request. The
reference runner uses that body as the observer snapshot of the
request it just sent, so it does not need a second hop. That is the
same data as the last array element after the request. A second
implementation that only implements `GET /_harness/requests` is
conformant; the runner then GETs the log after each send.

### What this is not

Not a packet capture. Not a span. Not access to gateway locals.
Not a requirement to publish the backend on the host network — the
reference echo is unpublished; the harness reads the log from inside
the backend's network.

---

## Record source — `record-source/0.1.0-draft`

Not part of the observer. Headers at a backend and records at a sink
are both observed runtime behaviour; this is the second.

Two transports already exist in the reference: custody's ledger
endpoint, and the gateway error log. This engine **claims** the
`[ctier-decision]` / `[ctier-attempt]` error-log lines as the C10
sink. They are written at NOTICE. An `error_log` of warn or above
discards them; sequencing cannot see a sink that was never written.
The sequence is per worker (`epoch=` carries the pid). Kong keeps
the counter in a worker-local upvalue. APISIX increments
`ngx.shared.ctier_seq` under a pid key. The live suite pins one
worker; `induced-gap-is-detected` is **Observed under a
configuration that is not production-shaped**, not a plain
Observed. Ledger POST fails open and is not claimed; the error-log line
is the backstop. Other error-log lines are diagnostics. nginx
`access.log` is not written and is not claimed. The contract is what
a conforming implementation **exposes**, in one shape, so a runner
can ask which records were written during a case. It must be
satisfiable by either transport. Anything clever is something a
second implementation has to rebuild.

### Fetch records written so far

```
GET {recordBase}/records
```

**Response:** `200`, `Content-Type: application/json`.

```json
{
  "records": [
    { "ctierSchema": "decision-record/0.2.0", "id": "…", "…": "…" }
  ]
}
```

| Field | Rule |
|---|---|
| `records` | array. Index `0` is the oldest entry still retained. Each element is one Decision, Attempt, or Outcome object |

No other wrapper fields are required. Extra wrapper fields are
ignored.

Each element is matched against the JSON Schema named by its
`ctierSchema`. A runner MUST NOT compare records as strings. A
`type` field, if present, is envelope and is stripped before
schema validation; it is not part of the three record schemas.

`GET {recordBase}/records?after={id}` is a MAY. Return only records
whose `id` is newer than that value, or ignore the query and return
the full list. Runners that do not send `after` must still work;
they isolate a case by listing `id`s before the send and diffing
afterwards.

The path is `{recordBase}/records`. Do not hide it behind a
different prefix without forking this draft. Custody's
`GET /v1/ledger` is one implementation of the same array, not a
second contract: an adapter may concatenate its typed queries into
`records`. The gateway log is another implementation: parse
`[ctier-decision]` and `[ctier-attempt]` lines into the same
objects. Outcomes, in the reference, are published by custody.

Join-key `equals` still matches `correlationId` on a Decision from
this list (or an equivalent lookup) to the **backend-observed**
`x-ctier-correlation-id`. Ordinary `200` responses do not return
that header to the client. Extending the `200` would be a change
to `spec/headers.md`, not to this draft.

An implementation without a record source skips cases that
`requires: [recordSource]` and reports them skipped.

### What this is not

Not a query language. Not a subscription. Not access to custody's
SQLite file or in-process maps. If the runner would have to read
memory the implementation does not publish, the assertion is out of
scope.

---

## Probe, per target (cheapest)

| Target | Before the strip (fragment) | After the strip (bundle) |
|---|---|---|
| Kong | bundled `pre-function` (priority 1e6, always first) | bundled `post-function` (priority −1000, always last in access) |
| APISIX | first function of `serverless-pre-function` in rewrite, priority raised above strip | last function of the same plugin, after the strip function |
| Apigee | JS Callout in PreFlow (or a PreProxy FlowHook, which the artefact cannot see) | JS Callout on the TargetEndpoint after strip |

Apigee has no local runtime in this repository. Precedence is
untestable live there. That is a recorded exclusion, not a skip of
the case format.

---

## Report — `runtime-report/0.1.0-draft`

The result record of one suite run. A run is identified by `target`,
`mode`, and `estate`. `estate` is a field of this record, not an
implementation detail of the reference runner.

A precedence result is only meaningful against a named estate. The
same `strip-precedence` case can pass against `existing/apisix.yaml`
and fail against `existing/apisix-outside-slot.yaml`. Without
`estate` those are not two results; they are one number that cannot
be reproduced.

```yaml
ctierSchema: runtime-report/0.1.0-draft
target: kong
mode: fragment
estate: existing/kong.yaml
passed: 9
failed: 1
skipped: 0
cases:
  - id: strip-precedence
    result: failed
```

| Field | Required | Rule |
|---|---|---|
| `ctierSchema` | yes | `runtime-report/0.1.0-draft` |
| `target` | yes | the enforcement point under test |
| `mode` | yes | `bundle` or `fragment` |
| `estate` | yes | fixture path of the existing configuration the run was merged into, or `bundle` when there was none. Non-empty. |
| `passed` | yes | count of cases with `result: passed` |
| `failed` | yes | count of cases with `result: failed` |
| `skipped` | yes | count of cases with `result: skipped` |
| `cases` | yes | one row per suite case, in suite order |

Each element of `cases`:

| Field | Required | Rule |
|---|---|---|
| `id` | yes | the case id |
| `result` | yes | `passed`, `failed`, or `skipped` |
| `skipReason` | when skipped | why the runner did not send |
| `failures` | when failed | the assertion messages |

The case row does not repeat `estate`. The run is the unit; every
case in it was evaluated against that estate.

`passed` + `failed` + `skipped` equals the length of `cases`. Never
count a skip as a pass.
