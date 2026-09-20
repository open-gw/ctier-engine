"""16c live: APISIX outside-slot estate; Kong strip at 10000."""
from __future__ import annotations

import yaml
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
from tests.live.test_boundary_precedence import _precedence
from tests.test_fragment import load_fixture

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
CAPS = {"observer", "probe", "recordSource"}
ESTATE_OUTSIDE = "existing/apisix-outside-slot.yaml"
ESTATE_KONG = "existing/kong.yaml"


def test_e1_apisix_outside_slot_falsifies_general_c11(apisix_stack):
    """Reader is serverless-post-function on a global rule, priority 30000."""
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified,
        target="apisix",
        mode="fragment",
        existing=load_fixture("apisix", variant="outside-slot"),
        custody={"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    doc = yaml.safe_load(files["apisix.yaml"])
    assert doc.get("global_rules")
    apisix_stack.load_generated(files)
    report = run_suite(
        load_suite(),
        _fixture(
            apisix_stack, APISIX_CUSTODY,
            target="apisix", mode="fragment", estate=ESTATE_OUTSIDE, capabilities=CAPS,
        ),
    )
    assert report["estate"] == ESTATE_OUTSIDE
    assert _precedence(report) == "failed", dump_report(report)


def _kong_with_mid_probe(files: dict[str, str]) -> dict[str, str]:
    deck = yaml.safe_load(files["kong.yaml"])
    plugins = list(deck.get("plugins") or [])
    plugins.append({"name": "ctier-estate-probe", "config": {}})
    deck["plugins"] = plugins
    out = dict(files)
    out["kong.yaml"] = yaml.safe_dump(deck, sort_keys=False, allow_unicode=True, width=1000)
    return out


def test_e2_kong_strip_above_estate_readers_below_10000(kong_stack):
    """ctier PRIORITY 10000 > cors 2000 / jwt 1005 / transformer 801 / probe 1500."""
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified,
        target="kong",
        mode="fragment",
        existing=load_fixture("kong"),
        custody={"url": CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    files = _kong_with_mid_probe(files)
    kong_stack.load_generated(files)
    report = run_suite(
        load_suite(),
        _fixture(
            kong_stack, CUSTODY,
            target="kong", mode="fragment", estate=ESTATE_KONG, capabilities=CAPS,
        ),
    )
    assert report["estate"] == ESTATE_KONG
    assert _precedence(report) == "passed", dump_report(report)


def test_e2_kong_strip_is_still_below_pre_function(kong_stack):
    """No fixed number is above pre-function (1e6)."""
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified,
        target="kong",
        mode="fragment",
        existing=load_fixture("kong"),
        custody={"url": CUSTODY_INTERNAL, "timeout_ms": 200},
    )
    files = attach_probe(files, "kong", position="before")
    kong_stack.load_generated(files)
    report = run_suite(
        load_suite(),
        _fixture(
            kong_stack, CUSTODY,
            target="kong", mode="fragment", estate=ESTATE_KONG, capabilities=CAPS,
        ),
    )
    assert report["estate"] == ESTATE_KONG
    assert _precedence(report) == "failed", dump_report(report)
