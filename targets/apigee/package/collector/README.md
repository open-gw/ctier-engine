# Retrievable decision records for Apigee

Apigee `print()` is Trace only. The kit
needs a GET that returns
`{ "records": [ … ] }`. This process is
that GET surface. It is **not** custody
(no pending, no approve).

## Run

```
./run.sh
```

Listens on `0.0.0.0:8090`.

- `POST /v1/ledger` — append a decision
  (or attempt)
- `GET /v1/ledger` — `{ "records": [ … ] }`

## Wire Apigee

1. Replace `https://records.example.invalid`
   in the generated ServiceCallout
   (`SC-RecordDecision`) with a URL the
   Message Processor can reach (this
   host).
2. Set in `kit.conf`:

```
kit_records: http://<reachable-host>:8090/v1/ledger
```

Regenerate with `./build.sh` after you
change the collector URL if you prefer
it compiled in (see `build.sh`).

## What this unlocks

C10 × 3 when the proxy actually POSTs
here on execute and refuse paths.

## What this is not

- Not Trace.
- Not a mock custody service.
- Not an Apigee emulator.
