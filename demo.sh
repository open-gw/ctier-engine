#!/bin/sh
# One entry point. Resets both live stacks, then walks ten beats on Kong
# and APISIX. Re-run without tearing anything down first.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
cd "$ROOT/engine"
if [ -x .venv/bin/python ]; then
  PY=".venv/bin/python"
elif [ -x .venv/bin/python3 ]; then
  PY=".venv/bin/python3"
else
  PY="${PYTHON:-python3}"
fi
export PYTHONPATH="${ROOT}/engine${PYTHONPATH:+:$PYTHONPATH}"
exec "$PY" -m ctier.demo "$@"
