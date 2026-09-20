# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""conformance-kit/1.1 — observable outcomes against a running target."""

from .runner import (
    KIT_VERSION,
    REPORT_ID,
    SCHEMA_ID,
    SKIP_COVERED_AT_GENERATION,
    SKIP_NOT_APPLICABLE_AT_LEVEL,
    SKIP_REASONS,
    SKIP_REQUIRES_CAPABILITY,
    Observation,
    Target,
    dump_report,
    load_cases,
    run_kit,
)

__all__ = [
    "KIT_VERSION",
    "REPORT_ID",
    "SCHEMA_ID",
    "SKIP_COVERED_AT_GENERATION",
    "SKIP_NOT_APPLICABLE_AT_LEVEL",
    "SKIP_REASONS",
    "SKIP_REQUIRES_CAPABILITY",
    "Observation",
    "Target",
    "dump_report",
    "load_cases",
    "run_kit",
]
