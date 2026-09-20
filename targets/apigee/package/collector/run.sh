#!/bin/sh
# Retrievable records sink for kit_records. Usage: ./run.sh [port]
set -eu
HERE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
export PORT="${1:-8090}"
cd "$HERE"
exec python3 collector.py
