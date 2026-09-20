"""Golden-file corpus: compose(in/) compared to expect/, with a printed diff."""
from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from ctier.classifier import compute_tier
from ctier.errors import ComposeError
from tests.golden_util import (
    GOLDEN_ROOT,
    dump_error,
    dump_manifest,
    dump_qualified,
    run_case,
)

SUCCESS = (
    "inline-only",
    "overlay-add-tier",
    "overlay-order-second-wins",
    "zero-match",
)
FAILURE = (
    "single-target",
    "criteria-missing-field",
    "reverses-dangling",
    "self-reversal-unsafe",
)


def _cases() -> list[Path]:
    return sorted(p for p in GOLDEN_ROOT.iterdir() if p.is_dir())


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


@pytest.mark.parametrize("name", SUCCESS)
def test_golden_success(name: str):
    case = GOLDEN_ROOT / name
    qualified, manifest = run_case(case)
    _assert_text(
        (case / "expect" / "qualified.yaml").read_text(encoding="utf-8"),
        dump_qualified(qualified),
        "qualified.yaml",
    )
    _assert_text(
        (case / "expect" / "manifest.json").read_text(encoding="utf-8"),
        dump_manifest(manifest),
        "manifest.json",
    )


@pytest.mark.parametrize("name", FAILURE)
def test_golden_failure(name: str):
    case = GOLDEN_ROOT / name
    with pytest.raises(ComposeError) as exc:
        run_case(case)
    _assert_text(
        (case / "expect" / "error.json").read_text(encoding="utf-8"),
        dump_error(exc.value),
        "error.json",
    )


def test_inline_only_composes_to_the_same_digest_twice():
    first_q, first_m = run_case(GOLDEN_ROOT / "inline-only")
    second_q, second_m = run_case(GOLDEN_ROOT / "inline-only")
    assert dump_qualified(first_q) == dump_qualified(second_q)
    assert dump_manifest(first_m) == dump_manifest(second_m)
    assert first_m["compositionDigest"] == second_m["compositionDigest"]


def test_criteria_missing_field_never_reaches_compute_tier():
    called = {"n": 0}

    def wrapped(criteria):
        called["n"] += 1
        return compute_tier(criteria)

    with pytest.raises(ComposeError, match="compliance-trigger") as exc:
        run_case(GOLDEN_ROOT / "criteria-missing-field", compute=wrapped)
    assert exc.value.rule == "schema"
    assert called["n"] == 0
