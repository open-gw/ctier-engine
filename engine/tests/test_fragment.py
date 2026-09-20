"""Fragment mode: merge into a cluttered existing proxy. No sockets."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ctier.compose import compose
from ctier.errors import GenerateError
from ctier.fragment import inspect, merge_kong
from ctier.generate import MODES, generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "existing"
TARGETS = ("apigee", "kong", "apisix")


def load_fixture(target: str, *, variant: str | None = None) -> dict[str, str]:
    if target == "kong":
        return {"kong.yaml": (FIXTURE / "kong.yaml").read_text(encoding="utf-8")}
    if target == "apisix":
        name = "apisix-outside-slot.yaml" if variant == "outside-slot" else "apisix.yaml"
        return {"apisix.yaml": (FIXTURE / name).read_text(encoding="utf-8")}
    root = FIXTURE / "apigee"
    files = {}
    for path in root.rglob("*"):
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return files


def test_fragment_is_a_generate_mode():
    assert "fragment" in MODES
    assert "bundle" in MODES


@pytest.mark.parametrize("target", TARGETS)
def test_fixture_is_cluttered_and_reads_or_rewrites_headers(target):
    existing = load_fixture(target)
    blob = "\n".join(existing.values()).lower()
    assert "rate" in blob or "limit" in blob or "spikearrest" in blob
    assert "cors" in blob
    assert "log" in blob
    assert "x-ctier-" in blob or "x-correlation-id" in blob
    assert "estate" in blob


@pytest.mark.parametrize("target", TARGETS)
def test_fragment_merges_into_fixture_and_keeps_estate(target):
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture(target)
    files = generate(qualified, target=target, mode="fragment", existing=existing)
    assert "ctier-conflict-report.yaml" in files
    report = yaml.safe_load(files["ctier-conflict-report.yaml"])
    assert report["wouldRefuse"] is False
    assert report["findings"]
    if target == "kong":
        deck = yaml.safe_load(files["kong.yaml"])
        plugin_names = {p["name"] for p in (deck.get("plugins") or [])}
        assert "cors" in plugin_names
        assert "request-transformer" in plugin_names
        assert "ctier" in plugin_names
        routes = deck["services"][0]["routes"]
        names = {r["name"] for r in routes}
        assert "estate-catchall" not in names
        assert "getBalance" in names or any("balance" in n.lower() for n in names)
        assert any(
            p.get("name") == "ctier"
            for r in routes
            for p in (r.get("plugins") or [])
        )
        assert any(
            p.get("name") == "rate-limiting"
            for r in routes
            for p in (r.get("plugins") or [])
        )
    elif target == "apisix":
        doc = yaml.safe_load(files["apisix.yaml"])
        names = {r.get("name") for r in doc["routes"]}
        assert "estate-catchall" not in names
        assert "getBalance" in names
        getb = next(r for r in doc["routes"] if r["name"] == "getBalance")
        assert "jwt-auth" in getb["plugins"]
        assert "cors" in getb["plugins"] or "limit-count" in getb["plugins"]
        pre = getb["plugins"]["serverless-pre-function"]
        fns = pre.get("functions") or []
        joined = "\n".join(fns)
        assert "X-Estate-Seen" in joined or "x-estate-seen" in joined.lower()
        assert "x-ctier-forged" in joined
        assert "clear_header" in fns[0]
        estate_i = next(i for i, f in enumerate(fns) if "X-Estate-Seen" in f)
        assert estate_i > 0
        assert any("clear_header" in f for f in fns[estate_i + 1 :])
    else:
        proxy = files["apiproxy/proxies/default.xml"]
        assert "JS-StripCtierNamespace" in proxy
        assert "SA-RateLimit" in proxy
        assert proxy.index("JS-StripCtierNamespace") < proxy.index("SA-RateLimit")
        assert "JS-ReadEstateHeaders" in proxy
        assert "apiproxy/policies/JS-StripCtierNamespace.xml" in files
        assert "apiproxy/policies/SA-RateLimit.xml" in files


@pytest.mark.parametrize("target", TARGETS)
def test_conflict_report_from_fixture(target):
    existing = load_fixture(target)
    report = inspect(target, existing)
    kinds = {f["kind"] for f in report["findings"]}
    assert report["wouldRefuse"] is False
    assert kinds
    blob = yaml.safe_dump(report).lower()
    assert "x-correlation-id" in blob or "x-ctier-" in blob
    if target != "apigee":
        assert report.get("warnedAndProceeded")


@pytest.mark.parametrize("target", ("kong", "apisix", "apigee"))
def test_replace_collision_refuses_and_writes_nothing(target):
    qualified, _ = compose(REFERENCE, [], NOW)
    if target == "kong":
        existing = {
            "kong.yaml": yaml.safe_dump({
                "_format_version": "3.0",
                "plugins": [{"name": "ctier", "config": {"tier": 1}}],
                "services": [{"name": "x", "url": "http://echo:8080", "routes": []}],
            })
        }
    elif target == "apisix":
        existing = {
            "apisix.yaml": yaml.safe_dump({
                "routes": [{
                    "id": "estate-catchall",
                    "name": "estate-catchall",
                    "uris": ["/*"],
                    "plugins": {
                        "jwt-auth": {"key": "not-ctier", "algorithm": "HS256"},
                    },
                    "upstream": {"type": "roundrobin", "nodes": {"echo:8080": 1}},
                }],
            })
        }
    else:
        existing = {
            "apiproxy/proxies/default.xml": (
                "<ProxyEndpoint name=\"default\"><PreFlow><Request>"
                "</Request></PreFlow></ProxyEndpoint>"
            ),
            "apiproxy/policies/JS-StripCtierNamespace.xml": (
                '<Javascript name="JS-StripCtierNamespace">'
                "<ResourceURL>jsc/stranger.js</ResourceURL></Javascript>"
            ),
        }
    with pytest.raises(GenerateError) as exc:
        generate(qualified, target=target, mode="fragment", existing=existing)
    assert exc.value.rule == "replace"
    assert "ctier-conflict-report.yaml" in exc.value.files
    assert list(exc.value.files) == ["ctier-conflict-report.yaml"]
    report = yaml.safe_load(exc.value.files["ctier-conflict-report.yaml"])
    assert any(f.get("kind") == "replace" for f in report["findings"])
    assert report["wouldRefuse"] is True


def test_c11_without_replace_still_refuses_a_later_writer():
    """Replacement is not the only refuse. Writer-after-strip is C11."""
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = {
        "kong.yaml": yaml.safe_dump({
            "_format_version": "3.0",
            "plugins": [{
                "name": "post-function",
                "config": {
                    "access": [
                        'kong.service.request.set_header("x-ctier-forged", "late")',
                    ],
                },
            }],
            "services": [{"name": "x", "url": "http://echo:8080", "routes": []}],
        })
    }
    with pytest.raises(GenerateError) as exc:
        generate(qualified, target="kong", mode="fragment", existing=existing)
    assert exc.value.rule == "c11"


def test_before_strip_reader_warns_and_proceeds():
    """Deliberate: requirement 3 + boundary suite, not refuse-by-default."""
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = {
        "kong.yaml": yaml.safe_dump({
            "_format_version": "3.0",
            "plugins": [{
                "name": "pre-function",
                "config": {
                    "access": [
                        'kong.log.debug(kong.request.get_header("x-ctier-tier"))',
                    ],
                },
            }],
            "services": [{"name": "x", "url": "http://echo:8080", "routes": []}],
        })
    }
    files = generate(qualified, target="kong", mode="fragment", existing=existing)
    report = yaml.safe_load(files["ctier-conflict-report.yaml"])
    assert report["wouldRefuse"] is False
    assert report["warnedAndProceeded"]
    assert any(
        f.get("kind") == "header-component-before-strip"
        for f in report["warnedAndProceeded"]
    )


def test_merge_keeps_request_transformer():
    existing = (FIXTURE / "kong.yaml").read_text(encoding="utf-8")
    frag = yaml.safe_dump({
        "_format_version": "3.0",
        "plugins": [{"name": "ctier", "config": {"tier": 4}}],
        "services": [{
            "name": "api",
            "url": "http://echo:8080",
            "routes": [{"name": "getBalance", "paths": ["/accounts/x/balance"], "methods": ["GET"]}],
        }],
    })
    merged = yaml.safe_load(merge_kong(existing, frag))
    names = {p["name"] for p in merged["plugins"]}
    assert "request-transformer" in names
    assert "ctier" in names
    routes = merged["services"][0]["routes"]
    assert any(
        p.get("name") == "rate-limiting"
        for r in routes
        for p in (r.get("plugins") or [])
    )


def test_estate_rewrite_lua_survives_apisix_fragment():
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="apisix", mode="fragment", existing=load_fixture("apisix"))
    doc = yaml.safe_load(files["apisix.yaml"])
    getb = next(r for r in doc["routes"] if r["name"] == "getBalance")
    joined = "\n".join(getb["plugins"]["serverless-pre-function"]["functions"])
    assert "x-ctier-forged" in joined
    assert "X-Estate-Seen" in joined
    assert "x-boundary-probe" in joined
    fns = getb["plugins"]["serverless-pre-function"]["functions"]
    assert "clear_header" in fns[0]
    estate_i = next(i for i, f in enumerate(fns) if "X-Estate-Seen" in f)
    assert any("clear_header" in f for f in fns[estate_i + 1 :])


def test_proxy_rewrite_collision_refuses_on_apisix():
    """Collision is whatever generate() emits, not a reserved-name list."""
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = {
        "apisix.yaml": yaml.safe_dump({
            "routes": [{
                "id": "estate-catchall",
                "name": "estate-catchall",
                "uris": ["/*"],
                "plugins": {
                    "proxy-rewrite": {"headers": {"set": {"X-Estate": "1"}}},
                },
                "upstream": {"type": "roundrobin", "nodes": {"echo:8080": 1}},
            }],
        })
    }
    with pytest.raises(GenerateError) as exc:
        generate(qualified, target="apisix", mode="fragment", existing=existing)
    assert exc.value.rule == "replace"
    blob = exc.value.files["ctier-conflict-report.yaml"]
    assert "proxy-rewrite" in blob
    assert list(exc.value.files) == ["ctier-conflict-report.yaml"]
