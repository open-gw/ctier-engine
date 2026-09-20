"""APISIX generation: same compiled decision as Kong, declarative where it can."""
from __future__ import annotations

import json

import yaml

from ctier.compose import compose
from ctier.errors import GenerateError
from ctier.generate import (
    TARGETS,
    _APISIX_SET_HEADERS,
    apisix_path,
    apisix_priority,
    generate,
)
from ctier.spec_loader import SPEC_DIR
from ctier.validate import iter_operations
from tests.golden_util import NOW
from tests.test_generate import _declared, _spec


def _routes(files: dict[str, str]) -> list[dict]:
    assert files["apisix.yaml"].rstrip().endswith("#END")
    return yaml.safe_load(files["apisix.yaml"])["routes"]


def _by_name(files: dict[str, str]) -> dict[str, dict]:
    return {r["name"]: r for r in _routes(files)}


def _structural(files: dict[str, str]) -> None:
    assert "apisix.yaml" in files
    assert "ctier-generate.json" in files
    assert "authorization.yaml" in files
    doc = yaml.safe_load(files["apisix.yaml"])
    consumers = doc.get("consumers") or []
    assert len(consumers) == 1
    jwt = consumers[0]["plugins"]["jwt-auth"]
    assert jwt["algorithm"] == "RS256"
    assert jwt["key"] == "ctier"
    assert "BEGIN PUBLIC KEY" in jwt["public_key"]
    names = {r["name"] for r in doc["routes"]}
    assert "undeclared" in names
    catch = next(r for r in doc["routes"] if r["name"] == "undeclared")
    assert catch["priority"] == 1
    assert "fault-injection" not in (catch.get("plugins") or {})
    post = catch["plugins"]["serverless-post-function"]
    assert post["phase"] == "access"
    joined = "\n".join(post.get("functions") or [])
    assert "[ctier-decision]" in joined
    assert "undeclared-operation" in joined
    assert "refuse-and-suspend" in joined
    assert "[ctier-attempt]" in joined
    assert "attempt-record/0.3.0" in joined
    assert "appliedTier = cjson.null" in joined
    assert "reason = \"unassigned\"" in joined
    # Unassigned Attempt still omits declaredTier; C2 Decision writes 4.
    attempt_chunk = joined[joined.find("attempt-record/0.3.0"):]
    assert "declaredTier" not in attempt_chunk
    assert "423" in joined
    for route in doc["routes"]:
        if route["name"] == "undeclared":
            continue
        plugins = route["plugins"]
        extras = set(plugins) - {
            "jwt-auth",
            "openid-connect",
            "proxy-rewrite",
            "serverless-pre-function",
            "serverless-post-function",
        }
        assert not extras, f"route {route['name']} unknown plugins {extras}"
        assert "fault-injection" not in plugins
        rewrite = plugins.get("proxy-rewrite")
        if rewrite:
            remove = {n.lower() for n in rewrite["headers"]["remove"]}
            set_names = {n.lower() for n in rewrite["headers"]["set"]}
            assert not (remove & set_names), "A2: same-name remove drops the set"
            assert set_names <= {n.lower() for n in _APISIX_SET_HEADERS}
            for name in ("x-correlation-id", "idempotency-key", "x-idempotency-key"):
                assert name in remove
            pre = plugins.get("serverless-pre-function") or {}
            joined = "\n".join(pre.get("functions") or [])
            assert "x-ctier-" in joined
            assert "x-correlation-id" in joined
            assert pre.get("phase") == "rewrite"


def test_apisix_is_a_generate_target():
    assert "apisix" in TARGETS
    try:
        generate({"openapi": "3.1.0", "info": {"title": "t", "version": "1"}, "paths": {}}, target="nope")
    except GenerateError as exc:
        assert "unsupported target" in str(exc)
    else:
        raise AssertionError("expected GenerateError")


def test_apisix_path_and_literal_priority():
    assert apisix_path("/accounts/{accountId}/balance") == "/accounts/*/balance"
    assert apisix_path("/orders/summary") == "/orders/summary"
    assert apisix_priority("/orders/summary") > apisix_priority("/orders/{orderId}")


def test_apisix_undeclared_is_catchall_not_a_classified_route():
    raw = _spec({
        "/ping": {"get": _declared(1, "ping")},
        "/gap": {"post": {"operationId": "gap", "responses": {"200": {"description": "x"}}}},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="apisix")
    by_name = _by_name(files)
    assert "ping" in by_name
    assert "gap" not in by_name
    assert "undeclared" in by_name
    catch = "\n".join(by_name["undeclared"]["plugins"]["serverless-post-function"]["functions"])
    assert 'uri = "/gap"' in catch
    assert "halt_and_hand_off" in catch
    published = json.loads(files["ctier-generate.json"])["governed-set"]
    assert {row["operation"] for row in published} == {"ping", "gap"}
    assert next(row for row in published if row["operation"] == "gap")["assignment"] == (
        "undeclared"
    )
    _structural(files)


def test_apisix_generate_is_byte_identical_twice():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    a = generate(qualified, target="apisix")
    b = generate(qualified, target="apisix")
    assert a == b
    _structural(a)
    classified = [op for _p, _m, op, _pp in iter_operations(qualified) if "x-ctier-tier" in op or op.get("x-ctier-exclude") is True]
    routes = [r for r in _routes(a) if r["name"] != "undeclared"]
    assert len(routes) == len(classified)


def test_apisix_same_compiled_tier_as_kong():
    raw = _spec({
        "/records/{id}": {
            "get": _declared(1, "getRecord", {
                "x-ctier-criteria": {
                    "reversibility": "undo-restores-record-only",
                    "blast-radius": "single-record",
                    "data-sensitivity": "internal",
                    "compliance-trigger": "none",
                    "idempotency": "inherently-safe",
                },
            }),
        },
    })
    qualified, _ = compose(raw, [], NOW)
    kong = generate(qualified, target="kong")
    apisix = generate(qualified, target="apisix")
    deck = yaml.safe_load(kong["kong.yaml"])
    route = next(r for r in deck["services"][0]["routes"] if r["name"] == "getRecord")
    ctier = next(p for p in route["plugins"] if p["name"] == "ctier")
    assert ctier["config"]["tier"] == 3
    rewrite = _by_name(apisix)["getRecord"]["plugins"]["proxy-rewrite"]
    assert rewrite["headers"]["set"]["X-Ctier-Tier"] == "3"
    assert "arg_" not in yaml.safe_dump(_by_name(apisix)["getRecord"])
    _structural(apisix)


def test_apisix_floor_poller_is_out_of_band():
    raw = _spec({"/x": {"get": _declared(1, "getX")}})
    qualified, _ = compose(raw, [], NOW)
    without = generate(qualified, target="apisix")
    with_c = generate(
        qualified,
        target="apisix",
        custody={"url": "http://custody:8080", "timeout_ms": 200, "floor_poll_ms": 1000},
    )
    l2 = "".join(_by_name(without)["getX"]["plugins"]["serverless-post-function"]["functions"])
    assert "/v1/floors" not in l2
    assert "ngx.timer.every" not in l2
    post = "".join(_by_name(with_c)["getX"]["plugins"]["serverless-post-function"]["functions"])
    assert "/v1/floors" in post
    assert "ngx.timer.every" in post
    assert "ngx.timer.at" in post
    assert "interval_ms=" in post
    assert "ngx.shared.ctier_floors" in post
    handler = post.split("return function(conf, ctx)", 1)[1]
    assert "/v1/floors" not in handler
    assert "/v1/ledger" in handler
    assert 'ngx.header["X-Agent-Action"] = "halt_and_hand_off"' in post
    _structural(with_c)


def test_apisix_custody_selects_level_3():
    raw = _spec({"/x": {"put": _declared(3, "updateX")}})
    qualified, _ = compose(raw, [], NOW)
    without = generate(qualified, target="apisix")
    with_c = generate(
        qualified,
        target="apisix",
        custody={"url": "http://custody:8080", "timeout_ms": 200},
    )
    l2 = _by_name(without)["updateX"]["plugins"]
    l3 = _by_name(with_c)["updateX"]["plugins"]
    assert "fault-injection" not in l2
    post_l2 = "".join(l2["serverless-post-function"]["functions"])
    assert "403" in post_l2
    assert "refuse-provisioning" in post_l2
    assert "[ctier-decision]" in post_l2
    assert "fault-injection" not in l3
    post = "".join(l3["serverless-post-function"]["functions"])
    assert "/v1/pending" in post
    assert "http://custody:8080" in post
    assert "200" in post
    assert "[ctier-attempt]" in post
    assert "appliedTier = cjson.null" in post
    assert "io.open" not in post
    _structural(without)
    _structural(with_c)


def test_apisix_tier4_records_a_decision():
    """Compiled Tier 4 is a decision. fault-injection alone was silent."""
    raw = _spec({"/payments": {"post": _declared(4, "createPayment")}})
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="apisix")
    plugins = _by_name(files)["createPayment"]["plugins"]
    assert "fault-injection" not in plugins
    post = "".join(plugins["serverless-post-function"]["functions"])
    assert "[ctier-decision]" in post
    assert "refuse-and-suspend" in post
    assert "ctier_emit_sink" in post
    assert "ctier_allocate_sequence" in post
    assert "epoch=" in post
    assert "423" in post
    assert "/v1/ledger" not in post
    _structural(files)


def test_apisix_catchall_c2_records_a_decision():
    """Composed-but-undeclared is a decision. Silent 423 failed C10 on that path."""
    raw = _spec({
        "/ping": {"get": _declared(1, "ping")},
        "/gap": {"post": {"operationId": "gap", "responses": {"200": {"description": "x"}}}},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="apisix")
    catch = "\n".join(_by_name(files)["undeclared"]["plugins"]["serverless-post-function"]["functions"])
    assert "[ctier-decision]" in catch
    assert "undeclared-operation" in catch
    assert "refuse-and-suspend" in catch
    assert "ctier_emit_sink" in catch
    assert "ctier_allocate_sequence" in catch
    assert 'operation = "gap"' in catch
    # Decision sits on the C2 match; Attempt stays on the unassigned fall-through.
    decision_at = catch.find("[ctier-decision]")
    attempt_at = catch.find("[ctier-attempt]")
    assert 0 <= decision_at < attempt_at
    _structural(files)


def test_apisix_custom_lua_is_not_classification():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    text = generate(qualified, target="apisix")["apisix.yaml"]
    assert "x-ctier-criteria" not in text.lower() or "remove" in text
    assert "compute_tier" not in text
    assert "blast-radius" not in text
    assert "operation-getBalance" in text
    assert "openid-connect" in text
    assert "required_scopes" in text
    assert "tonumber" in text
    getb = _by_name(generate(qualified, target="apisix"))["getBalance"]["plugins"]
    assert getb["openid-connect"]["required_scopes"] == ["operation-getBalance"]
    close = _by_name(generate(qualified, target="apisix"))["closeAccount"]["plugins"]
    assert "required_scopes" not in close["openid-connect"]


def test_apisix_digest_matches_kong():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    kong = generate(qualified, target="kong")
    apisix = generate(qualified, target="apisix")
    assert kong["ctier-generate.json"] != apisix["ctier-generate.json"]
    kmeta = json.loads(kong["ctier-generate.json"])
    ameta = json.loads(apisix["ctier-generate.json"])
    assert kmeta["deploymentDigest"] == ameta["deploymentDigest"]
    assert ameta["generator"]["target"] == "apisix"
    assert kmeta["governed-set"] == ameta["governed-set"]
    catch = "\n".join(_by_name(apisix)["undeclared"]["plugins"]["serverless-post-function"]["functions"])
    assert 'uri = "/accounts/*/statements/export"' in catch
    _structural(apisix)
