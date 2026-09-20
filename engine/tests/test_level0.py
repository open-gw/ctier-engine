"""Level 0 end to end through the library. Never imports the CLI."""
from __future__ import annotations

import difflib

from ctier.backend import NullBackend
from ctier.compose import compose
from ctier.cover import cover, dump_coverage_json
from ctier.recommend import recommend
from ctier.rules import DEFAULT_RULES
from ctier.spec_loader import SPEC_DIR
from ctier.validate import validate_named_schema
from tests.golden_util import GOLDEN_ROOT, NOW

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
GOLDEN = GOLDEN_ROOT / "level0-reference" / "expect" / "coverage-report.json"


def test_level0_library_only_matches_golden():
    assert "ctier.cli" not in globals()
    qualified, _manifest = compose(REFERENCE, [], NOW)
    recs = recommend(REFERENCE, DEFAULT_RULES, NullBackend(), NOW)
    report = cover(qualified, recs, NOW)
    validate_named_schema("coverage-report-0.1.0.json", report)
    actual = dump_coverage_json(report)
    expected = GOLDEN.read_text(encoding="utf-8")
    if actual != expected:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile="expect/coverage-report.json",
                tofile="actual/coverage-report.json",
            )
        )
        raise AssertionError(f"coverage-report.json mismatch\n{diff}")
