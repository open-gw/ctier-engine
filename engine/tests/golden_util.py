"""Shared dump and compose helpers for golden-file tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ctier.compose import compose
from ctier.errors import ComposeError

NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)
GOLDEN_ROOT = Path(__file__).parent / "golden"
COMPOSED_AT_MASK = "<composedAt>"


def dump_qualified(document: dict) -> str:
    return yaml.safe_dump(
        document,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )


def dump_manifest(manifest: dict) -> str:
    masked = json.loads(json.dumps(manifest))
    masked["composedAt"] = COMPOSED_AT_MASK
    return json.dumps(masked, indent=2, sort_keys=True) + "\n"


def dump_error(exc: ComposeError) -> str:
    return json.dumps({"rule": exc.rule, "message": str(exc)}, indent=2) + "\n"


def case_inputs(case_dir: Path) -> tuple[Path, list[Path]]:
    description = case_dir / "in" / "description.yaml"
    overlays = sorted((case_dir / "in").glob("overlay-*.yaml"))
    return description, overlays


def run_case(case_dir: Path, **kwargs):
    description, overlays = case_inputs(case_dir)
    return compose(description, overlays, NOW, **kwargs)
