"""Apigee bundle generation: order, fail-closed, determinism, structure."""
from __future__ import annotations

import difflib
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.conformance.adapter import ReferenceAdapter
from ctier.corpus import load_extras
from ctier.generate import flow_sort_key, generate, matches_path
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import GOLDEN_ROOT, NOW, normalise_signing_material

GENERATE_ROOT = GOLDEN_ROOT / "generate"


def _spec(ops: dict, title: str = "t") -> bytes:
    return yaml.safe_dump(
        {
            "openapi": "3.1.0",
            "info": {"title": title, "version": "1"},
            "servers": [{"url": "https://example.invalid/v1"}],
            "paths": ops,
        },
        sort_keys=False,
    ).encode("utf-8")


def _declared(tier: int, oid: str, extra: dict | None = None) -> dict:
    op = {
        "operationId": oid,
        "x-ctier-tier": tier,
        "x-ctier-status": "declared",
        "responses": {"200": {"description": "ok"}},
    }
    if extra:
        op.update(extra)
    return op


def _query(name: str) -> list[dict]:
    return [{"name": name, "in": "query", "schema": {"type": "integer"}}]


def _write_bundle(dest: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _assert_bundle(expect_dir: Path, files: dict[str, str]) -> None:
    expected = sorted(p.relative_to(expect_dir).as_posix() for p in expect_dir.rglob("*") if p.is_file())
    actual = sorted(files)
    if expected != actual:
        raise AssertionError(f"bundle files differ\nexpect={expected}\nactual={actual}")
    for rel in actual:
        want = normalise_signing_material((expect_dir / rel).read_text(encoding="utf-8"))
        got = normalise_signing_material(files[rel])
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


def _policy_names_from_xml(text: str) -> set[str]:
    root = ET.fromstring(text)
    return {
        el.text.strip()
        for el in root.iter()
        if el.tag.split("}")[-1] == "Name" and el.text
    }


def _structural(files: dict[str, str]) -> None:
    policy_files = {
        Path(p).stem
        for p in files
        if p.startswith("apiproxy/policies/") and p.endswith(".xml")
    }
    referenced: set[str] = set()
    for path, text in files.items():
        if not path.endswith(".xml"):
            continue
        ET.fromstring(text)
        if path.startswith("apiproxy/policies/"):
            continue
        referenced |= _policy_names_from_xml(text)
    referenced -= {"default"}
    assert policy_files == referenced, (
        f"policy file/reference mismatch missing={sorted(referenced - policy_files)} "
        f"orphan={sorted(policy_files - referenced)}"
    )


def test_matches_path_and_specificity():
    assert matches_path("/orders/{orderId}") == "/orders/*"
    assert matches_path("/orders/summary") == "/orders/summary"
    assert matches_path("/payments/{id}/authorizations/{aid}") == "/payments/*/authorizations/*"
    literal = flow_sort_key("/orders/summary", "get", "getOrderSummary")
    templated = flow_sort_key("/orders/{orderId}", "delete", "cancelOrder")
    longer = flow_sort_key("/orders/{orderId}/items", "get", "listItems")
    shorter = flow_sort_key("/orders/{orderId}", "get", "getOrder")
    assert literal < templated
    assert longer < shorter


def test_literal_sibling_flow_precedes_template():
    raw = _spec({
        "/orders/{orderId}": {"delete": _declared(4, "cancelOrder")},
        "/orders/summary": {"get": _declared(1, "getOrderSummary")},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    proxy = files["apiproxy/proxies/default.xml"]
    assert proxy.index('name="getOrderSummary"') < proxy.index('name="cancelOrder"')
    assert 'MatchesPath "/orders/summary"' in proxy
    assert 'MatchesPath "/orders/*"' in proxy
    _structural(files)


def test_undeclared_has_no_override_policy():
    raw = _spec({
        "/ping": {"get": _declared(1, "ping")},
        "/gap": {"post": {"operationId": "gap", "responses": {"200": {"description": "x"}}}},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    assert "apiproxy/policies/AM-Tier-ping.xml" in files
    assert "apiproxy/policies/AM-Tier-gap.xml" not in files
    assert "gap" not in files["apiproxy/proxies/default.xml"]
    assert "<Value>4</Value>" in files["apiproxy/policies/AM-DefaultTier.xml"]
    _structural(files)


def test_tier3_without_custody_is_provisioning_not_suspend():
    raw = _spec({"/x": {"put": _declared(3, "updateX")}})
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    prov = files["apiproxy/policies/RF-Provisioning.xml"]
    tier4 = files["apiproxy/policies/RF-Tier4.xml"]
    proxy = files["apiproxy/proxies/default.xml"]
    assert "<StatusCode>403</StatusCode>" in prov
    assert "halt_and_hand_off" not in prov
    assert "<StatusCode>423</StatusCode>" in tier4
    assert "halt_and_hand_off" in tier4
    assert 'ctier.tier = "3"' in proxy
    assert "RF-Provisioning" in proxy
    _structural(files)


def test_tier3_with_custody_compiles_the_withhold_path():
    raw = _spec({"/x": {"put": _declared(3, "updateX")}})
    qualified, _ = compose(raw, [], NOW)
    files = generate(
        qualified,
        custody={"url": "http://custody.example:8080", "timeout_ms": 200},
    )
    proxy = files["apiproxy/proxies/default.xml"]
    callout = files["apiproxy/policies/SC-CustodyPending.xml"]
    assert "RF-Withhold" in proxy
    assert "SC-CustodyPending" in proxy
    assert "RF-CustodyUnavailable" in proxy
    assert 'ctier.excluded = "true"' in proxy
    assert '(ctier.excluded = "true") or (ctier.tier = "3")' not in proxy
    assert "http://custody.example:8080" in callout
    assert "io.timeout.millis" in callout
    assert ">200<" in callout
    assert "Authorization" not in callout
    withhold = files["apiproxy/policies/RF-Withhold.xml"]
    assert "<StatusCode>202</StatusCode>" in withhold
    assert "Retry-After" not in withhold
    assert "{custodyPending.content}" in withhold
    unavailable = files["apiproxy/policies/RF-CustodyUnavailable.xml"]
    assert "<StatusCode>503</StatusCode>" in unavailable
    assert "Retry-After" in unavailable
    assert "halt_and_hand_off" not in unavailable
    _structural(files)


def test_excluded_uses_provisioning_policy():
    raw = _spec({
        "/secret": {
            "post": {
                "operationId": "secret",
                "x-ctier-exclude": True,
                "responses": {"403": {"description": "no"}},
            }
        }
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    assert "apiproxy/policies/AM-Exclude-secret.xml" in files
    assert "apiproxy/policies/AM-Tier-secret.xml" not in files
    assert 'ctier.excluded = "true"' in files["apiproxy/proxies/default.xml"]
    _structural(files)


def test_generate_is_byte_identical_twice():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    a = generate(qualified)
    b = generate(qualified)
    assert a == b
    _structural(a)


def _tier_value(text: str) -> str:
    root = ET.fromstring(text)
    for assign in root.iter():
        if assign.tag.split("}")[-1] != "AssignVariable":
            continue
        name = value = None
        for child in assign:
            tag = child.tag.split("}")[-1]
            if tag == "Name":
                name = (child.text or "").strip()
            elif tag == "Value":
                value = (child.text or "").strip()
        if name == "ctier.tier":
            return value
    raise AssertionError("ctier.tier not assigned")


def test_bounds_nested_condition_and_both_tier_assignments():
    raw = _spec({
        "/items": {
            "get": _declared(1, "listItems", {
                "x-ctier-bounds": {"parameter": "limit", "max": 50},
                "parameters": _query("limit"),
            }),
        },
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    proxy = files["apiproxy/proxies/default.xml"]
    floor = files["apiproxy/policies/AM-Tier-listItems.xml"]
    raised = files["apiproxy/policies/AM-Tier-listItems-bounds.xml"]
    assert 'name="listItems"' in proxy
    assert "<Name>AM-Tier-listItems</Name>" in proxy
    assert "<Name>AM-Tier-listItems-bounds</Name>" in proxy
    assert "request.queryparam.limit &gt; 50" in proxy
    assert proxy.index("AM-Tier-listItems") < proxy.index("AM-Tier-listItems-bounds")
    assert _tier_value(floor) == "1"
    assert _tier_value(raised) == "2"
    assert "listItems" in raised
    _structural(files)


def test_no_bounds_emits_no_bounds_condition():
    raw = _spec({"/ping": {"get": _declared(1, "ping")}})
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    proxy = files["apiproxy/proxies/default.xml"]
    assert "queryparam" not in proxy
    assert "-bounds" not in proxy
    assert not any(p.endswith("-bounds.xml") for p in files)
    _structural(files)


def test_partial_bounds_are_absent_not_a_disabled_branch():
    # Schema forbids a one-sided bounds object; the generator still matches
    # exceeds_declared_bounds (both fields, or no comparison).
    files = generate({
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            "/a": {"get": _declared(1, "onlyParam", {"x-ctier-bounds": {"parameter": "limit"}})},
            "/b": {"get": _declared(1, "onlyMax", {"x-ctier-bounds": {"max": 10}})},
        },
    })
    proxy = files["apiproxy/proxies/default.xml"]
    assert "queryparam" not in proxy
    assert "-bounds" not in proxy
    _structural(files)


def test_escalation_raises_one_tier_and_never_lowers():
    raw = _spec({
        "/t3": {
            "put": _declared(3, "updateT3", {
                "x-ctier-bounds": {"parameter": "n", "max": 1},
                "parameters": _query("n"),
            }),
        },
        "/t4": {
            "put": _declared(4, "updateT4", {
                "x-ctier-bounds": {"parameter": "n", "max": 1},
                "parameters": _query("n"),
            }),
        },
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    assert _tier_value(files["apiproxy/policies/AM-Tier-updateT3.xml"]) == "3"
    assert _tier_value(files["apiproxy/policies/AM-Tier-updateT3-bounds.xml"]) == "4"
    assert _tier_value(files["apiproxy/policies/AM-Tier-updateT4.xml"]) == "4"
    assert _tier_value(files["apiproxy/policies/AM-Tier-updateT4-bounds.xml"]) == "4"
    _structural(files)


def test_excluded_operation_does_not_emit_bounds():
    raw = _spec({
        "/secret": {
            "post": {
                "operationId": "secret",
                "x-ctier-exclude": True,
                "x-ctier-bounds": {"parameter": "limit", "max": 10},
                "parameters": _query("limit"),
                "responses": {"403": {"description": "no"}},
            }
        }
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified)
    proxy = files["apiproxy/proxies/default.xml"]
    assert "AM-Exclude-secret" in proxy
    assert "queryparam" not in proxy
    assert "AM-Tier-secret-bounds" not in files
    _structural(files)


def test_bounds_corpus_case_apigee_matches_classifier():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    files = generate(qualified)
    case = next(
        c for c in load_extras(HANDWRITTEN_DIR / "reference.yaml")
        if c["id"] == "bounds-exceeds-listTransactions"
    )
    observed = ReferenceAdapter(qualified).run(case)
    proxy = files["apiproxy/proxies/default.xml"]
    floor = files["apiproxy/policies/AM-Tier-listTransactions.xml"]
    raised = files["apiproxy/policies/AM-Tier-listTransactions-bounds.xml"]
    assert observed.applied_tier == 3
    assert observed.disposition == "refuse-provisioning"
    assert _tier_value(floor) == "2"
    assert _tier_value(raised) == str(observed.applied_tier)
    assert "request.queryparam.limit &gt; 100" in proxy
    start = proxy.index('<Flow name="listTransactions">')
    end = proxy.index("</Flow>", start)
    flow = proxy[start:end]
    assert "<Name>AM-Tier-listTransactions</Name>" in flow
    assert "<Name>AM-Tier-listTransactions-bounds</Name>" in flow
    assert "<Condition>" in flow
    _structural(files)


def test_unbounded_compiles_max_of_declared_and_computed():
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
    apigee = generate(qualified)
    kong = generate(qualified, target="kong")
    assert _tier_value(apigee["apiproxy/policies/AM-Tier-getRecord.xml"]) == "3"
    assert "AM-Tier-getRecord-bounds.xml" not in apigee
    assert "queryparam" not in apigee["apiproxy/proxies/default.xml"]
    deck = yaml.safe_load(kong["kong.yaml"])
    route = next(r for r in deck["services"][0]["routes"] if r["name"] == "getRecord")
    ctier = next(p for p in route["plugins"] if p["name"] == "ctier")
    assert ctier["config"]["tier"] == 3
    assert "bound_parameter" not in ctier["config"]
    _structural(apigee)


def test_golden_comparison_ignores_the_realm_key():
    placeholder = (
        '"privateKey": ["placeholder-private"]\n'
        '"certificate": ["placeholder-cert"]\n'
        "-----BEGIN PUBLIC KEY-----\nPLACEHOLDER\n-----END PUBLIC KEY-----\n"
        "route: balance\n"
    )
    local = (
        '"privateKey": ["local-private"]\n'
        '"certificate": ["local-cert"]\n'
        "-----BEGIN PUBLIC KEY-----\nLOCAL\n-----END PUBLIC KEY-----\n"
        "route: balance\n"
    )
    other = local.replace("route: balance", "route: other")
    assert normalise_signing_material(placeholder) == normalise_signing_material(local)
    assert "placeholder-private" not in normalise_signing_material(placeholder)
    assert "local-private" not in normalise_signing_material(local)
    assert normalise_signing_material(placeholder) != normalise_signing_material(other)


def test_golden_generate_cases():
    for case in sorted(p for p in GENERATE_ROOT.iterdir() if p.is_dir()):
        if (case / "in" / "description.yaml").exists():
            qualified, _ = compose(case / "in" / "description.yaml", [], NOW)
        else:
            qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
        files = generate(qualified)
        _assert_bundle(case / "expect", files)
        _structural(files)
