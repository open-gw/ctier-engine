"""Precedence: bundle passes; Kong fragment fails; APISIX fragment passes (strip-first)."""
from __future__ import annotations

import pytest

from ctier.boundary import dump_report, load_suite, run_suite
from ctier.boundary.probe import attach_probe
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL
from tests.live.test_boundary import _fixture
from tests.test_fragment import load_fixture

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
CAPS = {"observer", "probe", "recordSource"}


def _load_with_probe(stack, target: str, mode: str, *, custody_internal: str, position: str):
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture(target) if mode == "fragment" else None
    files = generate(
        qualified,
        target=target,
        mode=mode,
        existing=existing,
        custody={"url": custody_internal, "timeout_ms": 200},
    )
    files = attach_probe(files, target, position=position)
    stack.load_generated(files)


def _precedence(report: dict) -> str:
    assert report.get("estate"), dump_report(report)
    by_id = {c["id"]: c for c in report["cases"]}
    row = by_id["strip-precedence"]
    assert row["result"] != "skipped", dump_report(report)
    others = [
        c for c in report["cases"]
        if c["id"] != "strip-precedence" and c["result"] != "skipped"
    ]
    failed = [c["id"] for c in others if c["result"] != "passed"]
    assert not failed, dump_report(report)
    return row["result"]


def test_kong_bundle_passes_precedence(kong_stack):
    _load_with_probe(
        kong_stack, "kong", "bundle",
        custody_internal=CUSTODY_INTERNAL, position="after",
    )
    report = run_suite(
        load_suite(),
        _fixture(kong_stack, CUSTODY, target="kong", mode="bundle", estate="bundle", capabilities=CAPS),
    )
    assert _precedence(report) == "passed", dump_report(report)
    assert report["estate"] == "bundle"


def test_kong_fragment_fails_precedence(kong_stack):
    _load_with_probe(
        kong_stack, "kong", "fragment",
        custody_internal=CUSTODY_INTERNAL, position="before",
    )
    report = run_suite(
        load_suite(),
        _fixture(kong_stack, CUSTODY, target="kong", mode="fragment", estate="existing/kong.yaml", capabilities=CAPS),
    )
    assert _precedence(report) == "failed", dump_report(report)
    assert report["estate"] == "existing/kong.yaml"


def test_apisix_bundle_passes_precedence(apisix_stack):
    _load_with_probe(
        apisix_stack, "apisix", "bundle",
        custody_internal=APISIX_CUSTODY_INTERNAL, position="after",
    )
    report = run_suite(
        load_suite(),
        _fixture(
            apisix_stack, APISIX_CUSTODY,
            target="apisix", mode="bundle", estate="bundle", capabilities=CAPS,
        ),
    )
    assert _precedence(report) == "passed", dump_report(report)
    assert report["estate"] == "bundle"


def test_apisix_fragment_passes_precedence_with_estate_intact(apisix_stack):
    """Estate Lua survived; strip runs first in the combined slot. C11 in this slot."""
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified,
        target="apisix",
        mode="fragment",
        existing=load_fixture("apisix"),
        custody={"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    apisix_stack.load_generated(files)
    report = run_suite(
        load_suite(),
        _fixture(
            apisix_stack, APISIX_CUSTODY,
            target="apisix", mode="fragment", estate="existing/apisix.yaml", capabilities=CAPS,
        ),
    )
    assert _precedence(report) == "passed", dump_report(report)
    assert report["estate"] == "existing/apisix.yaml"


def test_apisix_fragment_outside_slot_fails_precedence(apisix_stack):
    """16c: serverless-post-function on a global rule, priority 30000."""
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified,
        target="apisix",
        mode="fragment",
        existing=load_fixture("apisix", variant="outside-slot"),
        custody={"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    apisix_stack.load_generated(files)
    report = run_suite(
        load_suite(),
        _fixture(
            apisix_stack, APISIX_CUSTODY,
            target="apisix", mode="fragment",
            estate="existing/apisix-outside-slot.yaml", capabilities=CAPS,
        ),
    )
    assert _precedence(report) == "failed", dump_report(report)
    assert report["estate"] == "existing/apisix-outside-slot.yaml"


def test_apigee_live_boundary_is_excluded():
    pytest.skip("Apigee has no local runtime; precedence untestable live")
