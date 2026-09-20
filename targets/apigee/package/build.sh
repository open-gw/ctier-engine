#!/bin/sh
# Generate the Apigee bundle from the same compose the live demo uses.
set -eu
HERE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "$HERE/../../.." && pwd)"
cd "$ROOT/engine"
if [ -x .venv/bin/python ]; then
  PY=".venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
export PYTHONPATH="${ROOT}/engine${PYTHONPATH:+:$PYTHONPATH}"
export CTIER_APIGEE_OUT="$HERE/generated"
exec "$PY" -c '
from datetime import datetime, timezone
from pathlib import Path
import os
from ctier.compose import compose
from ctier.generate import DEFAULT_CUSTODY_TIMEOUT_MS, DEFAULT_RECORDS_URL, generate
from ctier.spec_loader import SPEC_DIR

NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)
dest = Path(os.environ["CTIER_APIGEE_OUT"])
qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
files = generate(
    qualified,
    target="apigee",
    custody={"url": "https://custody.example.invalid", "timeout_ms": DEFAULT_CUSTODY_TIMEOUT_MS},
    records={"url": DEFAULT_RECORDS_URL, "timeout_ms": DEFAULT_CUSTODY_TIMEOUT_MS},
)
for rel, text in files.items():
    path = dest / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
print(f"wrote {len(files)} files to {dest}")
'
