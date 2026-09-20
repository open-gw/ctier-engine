"""1.5.0 header contract, all three generated targets. No sockets."""
from __future__ import annotations

import pytest
import yaml

from ctier.compose import compose
from ctier.custody.contract import relay_headers
from ctier.generate import STRIP_ALIASES, generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
TARGETS = ("apigee", "kong", "apisix")
FORGED_NS = "x-ctier-unknown-audit"
ALIASES = ("X-Correlation-Id", "X-Ctier-Tier", "Idempotency-Key", "X-Idempotency-Key")


def _kong_handler() -> str:
    from pathlib import Path
    return (
        Path(__file__).resolve().parents[2]
        / "targets" / "kong" / "plugin" / "handler.lua"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize("target", TARGETS)
def test_generated_artefacts_strip_namespace_and_aliases(target):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target=target)
    # Kong generate emits plugin config, not handler.lua. The prefix
    # walk lives in the plugin; a blob scan of kong.yaml would miss
    # X-Correlation-Id the same way the prefix itself does.
    if target == "kong":
        lower = _kong_handler().lower()
        assert 'prefix = "x-ctier-"' in lower
        assert "x-correlation-id" in lower
        assert "idempotency-key" in lower
        assert "x-idempotency-key" in lower
        return
    blob = "\n".join(files.values()).lower()
    assert "x-ctier-" in blob
    if target == "apigee":
        js = files["apiproxy/resources/jsc/strip-ctier-namespace.js"]
        assert "x-ctier-" in js
        strip = files["apiproxy/policies/SC-StripCtierHeaders.xml"].lower()
        for name in STRIP_ALIASES:
            assert name.lower() in strip
        return
    yaml_text = files["apisix.yaml"].lower()
    assert "x-ctier-" in yaml_text
    assert "x-correlation-id" in yaml_text
    assert "idempotency-key" in yaml_text
    assert "x-idempotency-key" in yaml_text


@pytest.mark.parametrize("target", TARGETS)
def test_generated_artefacts_emit_the_join_key(target):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target=target, custody={"url": "http://custody:8080"})
    if target == "kong":
        assert 'set_header("x-ctier-correlation-id"' in _kong_handler()
        return
    blob = "\n".join(files.values())
    assert "x-ctier-correlation-id" in blob.lower()


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("custody", [None, {"url": "http://custody:8080"}])
def test_no_target_emits_a_derived_idempotency_key_on_the_forwarded_path(target, custody):
    """Kong and APISIX may copy a stored ledger key. Nobody HMACs on the hop."""
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target=target, custody=custody)
    blob = "\n".join(files.values())
    assert "crypto.hmac" not in blob
    assert "ngx.hmac" not in blob
    if target == "apigee":
        js = files["apiproxy/resources/jsc/set-upstream-provenance.js"]
        assert "Idempotency-Key" not in js
        assert "hmac" not in js.lower()
        assert "x-ctier-correlation-id" in js.lower()
        return
    if target == "kong":
        handler = _kong_handler()
        assert "ngx.hmac" not in handler
        assert "crypto.hmac" not in handler
        assert 'set_header("Idempotency-Key", rec.idempotencyKey)' in handler
        return
    lua = []
    for route in yaml.safe_load(files["apisix.yaml"]).get("routes", []):
        fns = (
            route.get("plugins", {})
            .get("serverless-post-function", {})
            .get("functions")
            or []
        )
        lua.extend(fns)
    joined = "\n".join(lua)
    assert "ngx.hmac" not in joined
    if custody is not None:
        assert "if rec.idempotencyKey then key = rec.idempotencyKey end" in joined
    assert 'ngx.req.set_header("Idempotency-Key", key)' in joined


def test_202_carries_the_join_key_only():
    headers = relay_headers(correlation_id="corr-window", classified_tier=3)
    assert headers["x-ctier-correlation-id"] == "corr-window"
    assert "X-Correlation-Id" not in headers
