"""Golden recommendation sets: documents in, documents out, printed diff."""
from __future__ import annotations

import difflib
from pathlib import Path

import yaml

from ctier.backend import NullBackend
from ctier.recommend import recommend
from ctier.rules import DEFAULT_RULES
from tests.golden_util import GOLDEN_ROOT, NOW, dump_qualified


def _assert_text(expected: str, actual: str, label: str) -> None:
    if expected == actual:
        return
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=f"expect/{label}",
            tofile=f"actual/{label}",
        )
    )
    raise AssertionError(f"{label} mismatch\n{diff}")


def test_golden_recommend_get_single():
    case = GOLDEN_ROOT / "recommend-get-single"
    rec = recommend(case / "in" / "description.yaml", DEFAULT_RULES, NullBackend(), NOW)
    _assert_text(
        (case / "expect" / "recommendation-set.yaml").read_text(encoding="utf-8"),
        dump_qualified(rec),
        "recommendation-set.yaml",
    )


def test_golden_recommend_first_match():
    case = GOLDEN_ROOT / "recommend-first-match"
    rec = recommend(
        case / "in" / "description.yaml",
        case / "in" / "rules.yaml",
        NullBackend(),
        NOW,
    )
    _assert_text(
        (case / "expect" / "recommendation-set.yaml").read_text(encoding="utf-8"),
        dump_qualified(rec),
        "recommendation-set.yaml",
    )
