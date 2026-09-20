# ctier

Build-time library for consequence-tiered API governance. It is not a
gateway and it does not sit in the request path.

The classification core is what currently works. The composer, recommender,
coverage report and generator are not built yet.

```bash
pip install -e ".[dev]"
python -m pytest -q
python demo_classify.py
```

```
balance query (T1)              declared=LOW      applied=T1  execute
preference update (T2)          declared=MEDIUM   applied=T2  execute
profile update (T3)             declared=HIGH     applied=T3  withhold
payment initiation (T4)         declared=CRITICAL applied=T4  refuse
statements export (undeclared)  declared=--       applied=T4  refuse   <- undeclared-operation
account closure (excluded)      declared=--       applied=T4  refuse-provisioning

  transactions read #1          declared=LOW      applied=T1  execute
  transactions read #9          declared=LOW      applied=T1  execute
  transactions read #10         declared=LOW      applied=T2  execute  <- session-accumulation
```

Nine individually low-consequence reads pass at Tier 1. The tenth crosses the
accumulated threshold and is governed at Tier 2.

The specification this engine implements is named in
[`docs/SPEC.md`](docs/SPEC.md). What this engine does for each criterion
is in [`docs/PRD.md`](docs/PRD.md). Architecture decisions are in
[`docs/adr/`](docs/adr/). The package licence is the repository
[`LICENSE`](../LICENSE).
