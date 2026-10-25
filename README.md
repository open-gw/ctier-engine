[![test](https://github.com/open-gw/ctier-engine/actions/workflows/test.yml/badge.svg)](https://github.com/open-gw/ctier-engine/actions/workflows/test.yml)

# ctier-engine

This engine was developed in a private repository and is published here as a
single tree. The development record is in
[`engine/docs/findings/`](engine/docs/findings/), dated and sequential.
Commit hashes cited in findings refer to that private development repository.

This repository is a reference implementation of consequence-tiered API
governance: each operation is assigned a consequence class at design time, and
a gateway enforces that class before the call reaches the backend. It ships
generators for Kong, Apache APISIX, and Apigee, plus a conformance kit you can
point at a running URL.

Specification: [open-gw/ctier](https://github.com/open-gw/ctier) ·
[doi.org/10.5281/zenodo.22020288](https://doi.org/10.5281/zenodo.22020288).
The release this engine implements is named in
[`engine/docs/SPEC.md`](engine/docs/SPEC.md).

## What is verified, and how

Kong and APISIX are clean against **conformance-kit/1.1** at both Level 2 and
Level 3: zero failed rows, skips carry stated reasons, matrices in
[`engine/docs/kit/matrices.md`](engine/docs/kit/matrices.md).

## What is not

- **Apigee** cases in this repository are *would-run* predictions. There is no
  organisation result file. Generated artefacts exist; they have not been
  executed against an Apigee org here.
- **C12** is inconclusive on a bare unrouted `404`. Without provisioning a
  path that is routed at the enforcement point and absent from the
  composition, the kit cannot tell an unrouted miss from a C12 miss.
- **Five criteria are not observable at a running URL** (C4, C8, C13, C14,
  C15). Witnesses can falsify; they do not verify. See
  [`engine/docs/kit/observability.md`](engine/docs/kit/observability.md).

A clean matrix is a claim about the cases in the kit. It is not a claim about
the specification.

## Known issues

`generate` does not re-validate. A partially declared criteria object is
completed from defaults, then `max(declared, computed)` runs. `compose`
rejects a half-written object.

The same paragraph is [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md).

## Try it

```bash
cd engine && pip install -e ".[dev,serve]" && cd ..
make demo   # needs Docker; warns, then resets volumes, then ten beats on Kong and APISIX
```

That is one command. It prints a warning naming the ledger, pending reviews,
and revocations it is about to destroy, then resets both compose projects
(including volumes) so a second run matches the first, then walks ten beats
on Kong and the same ten on APISIX. You do not need to know pytest.

`python -m pytest -q` (from `engine/`) is the offline suite — socket-blocked,
no Docker. CI runs it on every push. `pytest --live -q` needs a local Kong or
APISIX rig and is not run in CI.

## Adoption ladder

Levels 0–4 are in the specification this engine implements
([`engine/docs/SPEC.md`](engine/docs/SPEC.md)). What this engine deploys:

| Level | This engine |
|---|---|
| 0 · Classify | Coverage report and review queue; nothing compiled into a gateway |
| 1 · Observe | Proxy config that classifies and emits a decision record; coverage warns |
| 2 · Enforce 1/2/4 | Proxy config and AS flags; no custody; coverage fails the build |
| 3 · Withhold | Custody; persist, approve, execute |
| 4 · Accumulate | Scope floor on Kong and APISIX |

Level 4 on the two live gateways is the same property with two encodings:
Kong's plugin module starts the poller; APISIX starts it lazily from
generated Lua. Both read `ngx.shared.ctier_floors` on the request path.
Apigee has no live runtime here. The dict size is Configured (1m);
memory-pressure behaviour of `lua_shared_dict` has never been Observed.

## What the demo does not claim

In the 16d exclusion form: a reader who finishes impressed and then discovers
one of these has been misled by omission.

- **Apigee is unverified.** The bundle in `targets/apigee/package/generated/`
  is generated from the same compile as the live targets. It has not been
  executed against an organisation in this repository. `print()` in that
  JavaScript is Trace, not a log sink. Precedence against a PreProxy FlowHook
  is untestable from the artefact.
- **Observed figures are samples on one machine; bounds are Derived.** Beat 6
  states the visibility bound as threshold-crossing plus one poll interval
  (1000 ms, Derived). It does not treat the 216 ms Observed sample as the bound.
  See [`engine/docs/measurements.md`](engine/docs/measurements.md).
- **Fragment mode (C11).** Bundle mode owns the path and strips inbound
  `x-ctier-*` first. Fragment mode does not guarantee that order against
  arbitrary existing configuration. See `engine/docs/portability.md`.
- **Level 2 (C7).** This engine strips inbound idempotency keys and emits
  none. Derived keys are emitted when custody persists context (Level 3).
- **What this engine does not make unavoidable.** The live rig isolates
  echo on an internal network. Custody calls the backend directly.
  Fragment emit does not pin strip-before-read against arbitrary existing
  configuration. The C10 sink is NOTICE on the error log; `error_log
  ... warn` drops every record. See `engine/docs/portability.md`.

ctier also does not guarantee durability of `[ctier-decision]` gateway-log
lines (requirement 4). An operator without a collector has not recorded them.
Those lines are the claimed C10 sink. They land in the gateway error log
at NOTICE. An `error_log` of warn or above discards them. nginx
`access.log` is not that sink. Other error-log lines (ledger-POST
failures, the floor poller) are diagnostics; see
`engine/docs/portability.md`.

This engine implements the `standard` profile. It does not implement
`constrained`.

## Documentation

| | |
|---|---|
| Specification this engine implements | [`engine/docs/SPEC.md`](engine/docs/SPEC.md) |
| Requirements | [`engine/docs/PRD.md`](engine/docs/PRD.md) |
| Solution design | [`engine/docs/SOLUTION-DESIGN.md`](engine/docs/SOLUTION-DESIGN.md) |
| Decisions | [`engine/docs/adr/`](engine/docs/adr/) |
| Still open | [`engine/docs/DECISIONS.md`](engine/docs/DECISIONS.md) |
| Kit matrices | [`engine/docs/kit/matrices.md`](engine/docs/kit/matrices.md) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports go through
[SECURITY.md](SECURITY.md). A [code of conduct](CODE_OF_CONDUCT.md) is
optional.

## Citing this work

If you use ctier-engine or the model, please cite the archived specification:

```bibtex
@software{dhanaraj2026ctier,
  author    = {Dhanaraj, Rinu},
  title     = {{ctier}: Consequence-Tiered {API} Governance for Autonomous {AI} Agents},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22020288},
  url       = {https://doi.org/10.5281/zenodo.22020288}
}
```

See `CITATION.cff`. The preferred citation is the specification, not this
repository.

## License

Engine source is licensed under the Apache License, Version 2.0. See
`LICENSE`, `NOTICE`, and `LICENSING.md`. Package metadata in
`engine/pyproject.toml` and SPDX headers on `engine/ctier/` sources state the
same licence.

The published specification (including the copy under `engine/ctier/spec/`) is
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and grants no patent
licence. Subject matter described in both repositories is the subject of US
provisional patent application 64/137,066.
