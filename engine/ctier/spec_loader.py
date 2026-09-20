# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Locate vendored ctier schemas and the targeted specification version."""
from __future__ import annotations

from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent / "spec"
SCHEMA_DIR = SPEC_DIR / "schemas"
EXAMPLES_DIR = SPEC_DIR / "examples"


def spec_version() -> str:
    return (SPEC_DIR / "VERSION").read_text(encoding="utf-8").strip()


def schema_path(name: str) -> Path:
    return SCHEMA_DIR / name
