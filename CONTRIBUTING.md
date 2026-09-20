# Contributing

This repository exists so people can run the conformance kit against a
gateway. Contributions that help that are welcome. Spec changes are not
merged here.

## Offline suite

Python 3.11+. From `engine/`:

```bash
pip install -e ".[dev]"
python -m pytest -q
```

That suite is socket-blocked and needs no Docker. A connect attempt fails
the test. CI runs the same command on every push.

## Live suite

`pytest --live -q` needs a local Kong or APISIX rig (Docker compose under
`targets/`). It is not run in CI. Do not invent a substitute.

`make demo` walks both live stacks; it resets volumes and is destructive.

## Spec changes

The specification lives in [open-gw/ctier](https://github.com/open-gw/ctier).
Engine pull requests do not change it. Matter for the specification goes
through that repository's admission rule — not through a PR to this tree.

## Pull requests

One concern per PR. Say what was wrong and what it caused.

If your change touches C11, C2, or C3, say so. Do not report security
vulnerabilities in a public PR — see [SECURITY.md](SECURITY.md).

A [code of conduct](CODE_OF_CONDUCT.md) is present; it is optional reading
for kit runners.
