"""Shared dump and compose helpers for golden-file tests."""
from __future__ import annotations

import json
import re
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


_PEM_RE = re.compile(
    r"-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----",
    re.DOTALL,
)
_JSON_MATERIAL_RE = re.compile(
    r'("(?:privateKey|certificate)"\s*:\s*(?:\[\s*)?")(?:[^"\\]|\\.)*(")',
)


def normalise_signing_material(text: str) -> str:
    """The golden does not depend on the realm key's value.

    ``privateKey``, ``certificate``, and a public-key PEM are replaced
    with a fixed marker. The committed golden stays on the placeholder.
    A local key does not fail the comparison, and it is not written
    into the golden.
    """
    text = _PEM_RE.sub(
        "-----BEGIN PUBLIC KEY-----\nNORMALISED\n-----END PUBLIC KEY-----",
        text,
    )
    return _JSON_MATERIAL_RE.sub(r"\1NORMALISED\2", text)


def case_inputs(case_dir: Path) -> tuple[Path, list[Path]]:
    description = case_dir / "in" / "description.yaml"
    overlays = sorted((case_dir / "in").glob("overlay-*.yaml"))
    return description, overlays


def run_case(case_dir: Path, **kwargs):
    description, overlays = case_inputs(case_dir)
    return compose(description, overlays, NOW, **kwargs)
