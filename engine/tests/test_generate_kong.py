"""Kong decK generation: determinism, fail-closed, structure, goldens."""
from __future__ import annotations

import difflib
import json
from pathlib import Path

import yaml

from ctier.compose import compose
from ctier.generate import generate, kong_path, kong_regex_priority
from ctier.spec_loader import SPEC_DIR
from ctier.validate import iter_operations
from tests.golden_util import GOLDEN_ROOT, NOW
from tests.test_generate import _declared, _spec

KONG_ROOT = GOLDEN_ROOT / "generate-kong"


def _ctier_conf(route: dict) -> dict:
    return next(p["config"] for p in route["plugins"] if p["name"] == "ctier")


def _assert_bundle(expect_dir: Path, files: dict[str, str]) -> None:
    expected = sorted(p.relative_to(expect_dir).as_posix() for p in expect_dir.rglob("*") if p.is_file())
    actual = sorted(files)
    if expected != actual:
        raise AssertionError(f"bundle files differ\nexpect={expected}\nactual={actual}")
    for rel in actual:
        want = (expect_dir / rel).read_text(encoding="utf-8")
        got = files[rel]
        if want != got:
            diff = "".join(
                difflib.unified_diff(
                    want.splitlines(keepends=True),
                    got.splitlines(keepends=True),
                    fromfile=f"expect/{rel}",
                    tofile=f"actual/{rel}",
                )
            )
            raise AssertionError(f"{rel} mismatch\n{diff}")


def _structural(files: dict[str, str]) -> None:
    assert "kong.yaml" in files
    doc = yaml.safe_load(files["kong.yaml"])
    globals_ = [p for p in (doc.get("plugins") or []) if p.get("name") == "ctier"]
    assert len(globals_) == 1, "global ctier default missing"
    gconf = globals_[0]["config"]
    assert gconf["tier"] == 4
    assert gconf.get("excluded") is False
    assert isinstance(gconf.get("governed-set"), list)
    services = doc.get("services") or []
    assert len(services) == 1
    route_names = [r.get("name") for r in (services[0].get("routes") or [])]
    assert set(gconf["governed-set"]) == set(route_names)
    for route in services[0].get("routes") or []:
        plugins = [p for p in (route.get("plugins") or []) if p.get("name") == "ctier"]
        extras = [p for p in (route.get("plugins") or []) if p.get("name") not in {"ctier", "jwt"}]
        assert not extras, f"route {route.get('name')} references unknown plugin"
        ctier = [p for p in (route.get("plugins") or []) if p.get("name") == "ctier"]
        if ctier:
            conf = ctier[0]["config"]
            assert conf.get("excluded") is True or conf.get("tier") in (1, 2, 3, 4)
            if conf.get("excluded"):
                assert "required_scope" not in conf
            else:
                assert conf.get("required_scope")
        # else: inherits the global Tier 4 because nothing overrode it


def test_kong_path_and_literal_priority():
    assert kong_path("/accounts/{accountId}/balance") == (
        "~/accounts/(?<accountId>[^/]+)/balance$"
    )
    assert kong_path("/orders/summary").startswith("~/orders/summary")
    assert kong_regex_priority("/orders/summary") > kong_regex_priority("/orders/{orderId}")


def test_kong_undeclared_has_route_without_plugin():
    raw = _spec({
        "/ping": {"get": _declared(1, "ping")},
        "/gap": {"post": {"operationId": "gap", "responses": {"200": {"description": "x"}}}},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="kong")
    doc = yaml.safe_load(files["kong.yaml"])
    by_name = {r["name"]: r for r in doc["services"][0]["routes"]}
    assert "plugins" in by_name["ping"]
    assert "plugins" not in by_name["gap"]
    gconf = next(p["config"] for p in doc["plugins"] if p["name"] == "ctier")
    assert "gap" in gconf["governed-set"]
    assert "ping" in gconf["governed-set"]
    published = json.loads(files["ctier-generate.json"])["governed-set"]
    assert {row["operation"] for row in published} == {"ping", "gap"}
    assert next(row for row in published if row["operation"] == "gap")["assignment"] == (
        "undeclared"
    )
    _structural(files)


def test_kong_generate_is_byte_identical_twice():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    a = generate(qualified, target="kong")
    b = generate(qualified, target="kong")
    assert a == b
    _structural(a)
    ops = iter_operations(qualified)
    routes = yaml.safe_load(a["kong.yaml"])["services"][0]["routes"]
    assert len(routes) == len(ops)


def test_kong_unbounded_compiles_max_of_declared_and_computed():
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
    files = generate(qualified, target="kong")
    deck = yaml.safe_load(files["kong.yaml"])
    route = next(r for r in deck["services"][0]["routes"] if r["name"] == "getRecord")
    assert _ctier_conf(route)["tier"] == 3
    assert "bound_parameter" not in _ctier_conf(route)
    _structural(files)


def test_kong_custody_config_selects_level_3():
    raw = _spec({"/x": {"put": _declared(3, "updateX")}})
    qualified, _ = compose(raw, [], NOW)
    without = generate(qualified, target="kong")
    with_c = generate(
        qualified,
        target="kong",
        custody={"url": "http://custody:8080", "timeout_ms": 200},
    )
    l2 = yaml.safe_load(without["kong.yaml"])
    l3 = yaml.safe_load(with_c["kong.yaml"])
    route2 = next(r for r in l2["services"][0]["routes"] if r["name"] == "updateX")
    route3 = next(r for r in l3["services"][0]["routes"] if r["name"] == "updateX")
    assert "custody_url" not in _ctier_conf(route2)
    assert _ctier_conf(route3)["custody_url"] == "http://custody:8080"
    assert _ctier_conf(route3)["custody_timeout_ms"] == 200
    assert _ctier_conf(route3)["floor_poll_ms"] == 1000
    assert l3["plugins"][0]["config"]["custody_url"] == "http://custody:8080"
    assert l3["plugins"][0]["config"]["custody_timeout_ms"] == 200
    assert l3["plugins"][0]["config"]["floor_poll_ms"] == 1000
    assert "ledger_fallback" not in route3["plugins"][0]["config"]
    with_fb = generate(
        qualified,
        target="kong",
        custody={
            "url": "http://custody:8080",
            "timeout_ms": 200,
            "ledger_fallback": "/var/ctier/ledger/attempts.jsonl",
        },
    )
    l3fb = yaml.safe_load(with_fb["kong.yaml"])
    route_fb = next(r for r in l3fb["services"][0]["routes"] if r["name"] == "updateX")
    assert _ctier_conf(route_fb)["ledger_fallback"] == (
        "/var/ctier/ledger/attempts.jsonl"
    )
    _structural(without)
    _structural(with_c)
    _structural(with_fb)


def test_golden_kong_cases():
    for case in sorted(p for p in KONG_ROOT.iterdir() if p.is_dir()):
        if (case / "in" / "description.yaml").exists():
            qualified, _ = compose(case / "in" / "description.yaml", [], NOW)
        else:
            qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
        files = generate(qualified, target="kong")
        _assert_bundle(case / "expect", files)
        _structural(files)
