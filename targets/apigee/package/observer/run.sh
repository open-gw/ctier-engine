#!/bin/sh
# Backend observer for kit_observer. Usage: ./run.sh [port]
set -eu
HERE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
export PORT="${1:-8080}"
cd "$HERE"
echo "observer listening on 0.0.0.0:${PORT}"
echo "kit_observer → http://<reachable-host>:${PORT}/_harness/requests"
exec python3 echo.py
