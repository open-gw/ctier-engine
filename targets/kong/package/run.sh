#!/bin/sh
# One command against your running Kong → one result file.
# Usage: ./run.sh kit.conf
set -eu
HERE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "$HERE/../../.." && pwd)"
CONF="${1:-}"
if [ -z "$CONF" ]; then
  echo "usage: ./run.sh kit.conf" >&2
  echo "copy kit.conf.example to kit.conf and fill it in" >&2
  exit 2
fi
case "$CONF" in
  /*) ;;
  *) CONF="$PWD/$CONF" ;;
esac
if [ ! -f "$CONF" ]; then
  echo "config not found: $CONF" >&2
  exit 2
fi
cd "$ROOT/engine"
if [ -x .venv/bin/python ]; then
  PY=".venv/bin/python"
elif [ -x .venv/bin/python3 ]; then
  PY=".venv/bin/python3"
else
  PY="${PYTHON:-python3}"
fi
export PYTHONPATH="${ROOT}/engine${PYTHONPATH:+:$PYTHONPATH}"
exec "$PY" - "$CONF" <<'PY'
"""Read kit.conf and run conformance-kit/1.1 once."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from ctier.kit.runner import dump_report, http_target, load_cases, run_kit


def _str(doc: dict, key: str, default: str = "") -> str:
    val = doc.get(key, default)
    if val is None:
        return default
    return str(val).strip()


def main(conf_path: str) -> int:
    doc = yaml.safe_load(Path(conf_path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit(f"config must be a mapping: {conf_path}")

    url = _str(doc, "gateway_url")
    token = _str(doc, "gateway_token")
    if not url or not token or token == "paste-bearer-token-here":
        raise SystemExit(
            "set gateway_url and gateway_token in the config "
            "(see kit.conf.example)"
        )

    records = _str(doc, "kit_records") or None
    observer = _str(doc, "kit_observer") or None
    custody = _str(doc, "kit_custody") or None
    level = _str(doc, "kit_level", "2") or "2"
    out = _str(doc, "kit_out", "kit-result.yaml") or "kit-result.yaml"

    # Named for your reply / deploy notes. Not sent to the runner.
    if "kong_deployment" not in doc:
        raise SystemExit("config must name kong_deployment (see kit.conf.example)")

    target = http_target(
        url,
        token,
        records_url=records,
        observer_url=observer,
        custody_url=custody,
    )
    report = run_kit(load_cases(), target, level=level)
    text = dump_report(report)
    out_path = Path(out)
    if not out_path.is_absolute():
        out_path = Path(conf_path).resolve().parent / out_path
    out_path.write_text(text, encoding="utf-8")
    print(
        f"wrote {out_path} "
        f"passed={report['passed']} failed={report['failed']} "
        f"skipped={report['skipped']} "
        f"inconclusive={report['inconclusive']} "
        f"ran={report['ran']}"
    )
    return 1 if report["failed"] else 0


raise SystemExit(main(sys.argv[1]))
PY
