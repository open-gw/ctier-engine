# ctier-engine

Reference implementation of consequence-tiered API governance for autonomous
agents.

**AGA** — Autonomous Governance Architecture — is the framework. **ctier** is
the specification and this implementation of it. Public writing uses AGA for
the idea and ctier for the artefact.

Specification: [open-gw/ctier](https://github.com/open-gw/ctier) ·
[doi.org/10.5281/zenodo.22020288](https://doi.org/10.5281/zenodo.22020288).
The release this engine implements is named in
[`engine/docs/SPEC.md`](engine/docs/SPEC.md).

Kong and APISIX live at every ladder rung. Apigee is generated, not run here.

## Try it

```bash
cd engine && pip install -e ".[dev,serve]" && cd ..
make demo   # needs Docker; warns, then resets volumes, then ten beats on Kong and APISIX
```

That is one command. It prints a warning naming the ledger, pending reviews,
and revocations it is about to destroy, then resets both compose projects
(including volumes) so a second run matches the first, then walks ten beats
on Kong and the same ten on APISIX. You do not need to know pytest.

`python -m pytest -q` (from `engine/`) is the offline suite. `pytest --live -q`
is the author-run live suite, not the demonstration.

## Adoption ladder

Each rung is independently useful.

| Level | Deployed | Gives |
|---|---|---|
| 0 · Classify | nothing | a review queue in risk order, and a number: what share of the estate is unclassified |
| 1 · Observe | proxy config | classify and emit a decision record, enforcing nothing; coverage warns |
| 2 · Enforce 1/2/4 | proxy config + AS flags | first level with teeth, still no new runtime; coverage fails the build |
| 3 · Withhold | custody | Tier 3 end to end |
| 4 · Accumulate | scope floor | decomposition defence, and the cycle back to design |

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
- **Fragment mode's C11 guarantee is bounded per target.** Bundle mode owns the
  path. Fragment mode is not C11-conformant against arbitrary existing
  configuration (requirement 3).
- **Level 2 does not satisfy C7.** There is no derived idempotency key at
  observe-or-enforce-without-custody. C7 holds where custody persists context
  and execute reuses it.
- **Three deployment requirements ctier does not enforce:** (1) the backend
  accepts requests only from the enforcement point and from custody; (2)
  custody's execute path bypasses the enforcement point by design; (3) in
  fragment mode the operator must place the strip before any reader of a 1.5.0
  header, and no later writer. See `engine/docs/portability.md`.

ctier also does not guarantee durability of `[ctier-decision]` gateway-log
lines (requirement 4). An operator without a collector has not recorded them.

## Documentation

| | |
|---|---|
| Specification this engine implements | [`engine/docs/SPEC.md`](engine/docs/SPEC.md) |
| Requirements | [`engine/docs/PRD.md`](engine/docs/PRD.md) |
| Solution design | [`engine/docs/SOLUTION-DESIGN.md`](engine/docs/SOLUTION-DESIGN.md) |
| Decisions | [`engine/docs/adr/`](engine/docs/adr/) |
| Still open | [`engine/docs/DECISIONS.md`](engine/docs/DECISIONS.md) |
| Implementation plan | [`engine/docs/IMPLEMENTATION-PLAN.md`](engine/docs/IMPLEMENTATION-PLAN.md) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The code of conduct is in
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security reports go through
[SECURITY.md](SECURITY.md).

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

[Apache 2.0](LICENSE) — see [NOTICE](NOTICE) and [LICENSING.md](LICENSING.md).
The specification is [CC BY 4.0](https://github.com/open-gw/ctier) and grants
no patent licence. Subject matter described in both repositories is the
subject of US provisional patent application 64/137,066.
