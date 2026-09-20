# Backend observer for Apigee kit runs

This is the same echo contract Kong and
APISIX live stacks use. It is a real
upstream that logs every hop, not a
stand-in for Apigee and not custody.

## What the kit needs

`kit_observer` must be an HTTP GET that
returns a JSON array of recent backend
requests (or `{ "requests": [ … ] }`).
Each entry has `method`, `path`, and
`headers`.

This process exposes:

```
GET /_harness/requests
```

Every other method/path is logged and
echoed.

## Run it

```
python3 echo.py
```

Listens on `0.0.0.0:8080`.

## Wire Apigee

1. Point the proxy **target endpoint**
   at this host (reachable from the
   Message Processor), e.g.
   `http://observer.example:8080`.
2. Publish `GET /_harness/requests` so
   the machine running `./run.sh` can
   reach it (tunnel, load balancer, or
   a host the runner shares).
3. Set in `kit.conf`:

```
kit_observer: http://<reachable-host>:8080/_harness/requests
```

## What this unlocks

At Level 2: `c16-unknown-prefix-name-is-absent`.
C1 gains the soft "backend unreached"
assert when the observer is present.

At Level 3 (with real custody, not this
process): C6 and C7 also need the
observer.

## What this is not

- Not an Apigee emulator.
- Not a custody / approval service.
- Not a decision-record collector.
