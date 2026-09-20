"""16c: same-slot bracketing is not general. No sockets."""
from __future__ import annotations

import yaml

from ctier.compose import compose
from ctier.fragment import CTIER_KONG_PRIORITY
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_fragment import load_fixture

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"


def test_outside_slot_fixture_is_not_serverless_pre_function():
    existing = load_fixture("apisix", variant="outside-slot")
    doc = yaml.safe_load(existing["apisix.yaml"])
    assert "global_rules" in doc
    glob = doc["global_rules"][0]["plugins"]
    assert "serverless-post-function" in glob
    assert "serverless-pre-function" not in glob
    catch = next(r for r in doc["routes"] if r["name"] == "estate-catchall")
    assert "serverless-pre-function" not in (catch.get("plugins") or {})
    pri = glob["serverless-post-function"]["_meta"]["priority"]
    assert pri > 21000


def test_outside_slot_survives_fragment_merge():
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(
        qualified,
        target="apisix",
        mode="fragment",
        existing=load_fixture("apisix", variant="outside-slot"),
    )
    doc = yaml.safe_load(files["apisix.yaml"])
    assert doc.get("global_rules")
    blob = yaml.safe_dump(doc)
    assert "estate-outside-slot" in blob
    assert "serverless-post-function" in blob
    getb = next(r for r in doc["routes"] if r["name"] == "getBalance")
    pre = getb["plugins"]["serverless-pre-function"]
    joined = "\n".join(pre.get("functions") or [])
    assert "x-boundary-probe" not in joined


def test_kong_strip_priority_is_above_cors_and_below_pre_function():
    assert CTIER_KONG_PRIORITY == 10000
    assert CTIER_KONG_PRIORITY > 2000
    assert CTIER_KONG_PRIORITY < 1_000_000
