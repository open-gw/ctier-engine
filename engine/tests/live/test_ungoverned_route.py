"""A path absent from the composed description is refused undetermined.

38 measured the four cells. After 41 they must all assert C12's miss:
refused, an undetermined Attempt, and no Tier 4 Decision. Kong's old
pass was a Decision with appliedTier 4 — the wrong record of the
right shape. After 52 the Attempt must also omit `declaredTier`. A
schema-valid 0.3.0 that still writes 4 is the failure 41 already
found once.

Fragment: the route is in the estate under a name other than
`estate-catchall`, so merge keeps it. Bundle: generate, then add the
same route to the running gateway.

APISIX: a more specific added route wins over `/*` at any priority,
so the C12-miss probe is a path no added route claims. The add is
still performed (fragment extra / post-generation drift). A route
that claims the path escapes; that is the bound, not a number to beat.
"""
from __future__ import annotations

import json

import pytest
import yaml

from ctier.boundary import BoundaryFixture, Observation, dump_report, load_suite, run_suite
from ctier.boundary.records import merge_records, records_from_ledger_body, records_from_log
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import with_end
from tests.live.apisix_rig import point_at_echo as apisix_point_at_echo
from tests.live.rig import CUSTODY, http
from tests.live.rig import point_at_echo as kong_point_at_echo
from tests.test_fragment import load_fixture

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
UNKNOWN_PATH = "/estate/unknown"
UNKNOWN_ROUTE = "estate-unknown"
CASE_ID = "unknown-path-refused-undetermined"


def _case() -> dict:
    return next(c for c in load_suite()["cases"] if c["id"] == CASE_ID)


def _logs(stack, service: str) -> str:
    proc = stack._compose("logs", "--no-color", "--tail", "800", service, check=False)
    text = (proc.stdout or "") + (proc.stderr or "")
    paths = {
        "kong": "cat /usr/local/kong/logs/error.log 2>/dev/null || true",
        "apisix": "cat /usr/local/apisix/logs/error.log 2>/dev/null || true",
    }
    if service in paths:
        inner = stack.exec(service, "sh", "-c", paths[service], check=False)
        text += inner.stdout or ""
        text += inner.stderr or ""
    return text


def _add_kong_unknown(text: str) -> str:
    deck = yaml.safe_load(text) or {}
    services = deck.setdefault("services", [])
    if not services:
        raise AssertionError("kong yaml has no service to hang the unknown route on")
    routes = services[0].setdefault("routes", [])
    routes.append({
        "name": UNKNOWN_ROUTE,
        "paths": [UNKNOWN_PATH],
        "methods": ["GET"],
        "strip_path": False,
    })
    return yaml.safe_dump(
        deck,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )


def _add_apisix_unknown(text: str) -> str:
    # A more specific URI wins over `/*` even at priority 0. Claim a
    # different path so the catchall still receives UNKNOWN_PATH.
    doc = yaml.safe_load(text) or {}
    routes = doc.setdefault("routes", [])
    routes.append({
        "id": UNKNOWN_ROUTE,
        "name": UNKNOWN_ROUTE,
        "uris": ["/estate/drift-extra"],
        "methods": ["GET"],
        "priority": 100,
        "upstream": {
            "type": "roundrobin",
            "scheme": "http",
            "nodes": {"echo:8080": 1},
        },
    })
    dumped = yaml.safe_dump(
        doc,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
    return with_end(dumped)


def _fetch(stack, gw: str, custody_base: str):
    def fetch() -> list[dict]:
        log = records_from_log(_logs(stack, gw))
        extra = ""
        if gw == "apisix":
            extra = _logs(stack, "apisix-dp") + _logs(stack, "etcd")
            log = merge_records(log, records_from_log(extra))
        ledger: list[dict] = []
        try:
            status, raw, _ = http("GET", custody_base + "/v1/ledger")
        except Exception:
            status, raw = 0, b""
        if status == 200:
            try:
                ledger = records_from_ledger_body(json.loads(raw.decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
                ledger = []
        return merge_records(log, ledger)

    return fetch


def _fixture(stack, custody_base: str, gw: str, *, target: str, estate: str):
    def send(method: str, path: str, headers: dict[str, str], body: str | None = None) -> Observation:
        hdrs_in = dict(headers)
        if body is not None and not any(k.lower() == "content-type" for k in hdrs_in):
            hdrs_in["Content-Type"] = "application/json"
        status, raw, hdrs = stack.request(
            method, path,
            headers=stack.auth_headers(**hdrs_in),
            body=body,
        )
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            payload = {}
        observer: dict[str, str] = {}
        if isinstance(payload, dict) and isinstance(payload.get("headers"), dict):
            observer = {str(k).lower(): str(v) for k, v in payload["headers"].items()}
        response = {str(k).lower(): str(v) for k, v in (hdrs or {}).items()}
        return Observation(
            status=status,
            response_headers=response,
            observer_headers=observer,
            body=payload if isinstance(payload, dict) else {},
        )

    return BoundaryFixture(
        capabilities={"recordSource"},
        send=send,
        fetch_records=_fetch(stack, gw, custody_base),
        target=target,
        mode="bundle" if "bundle" in estate else "fragment",
        estate=estate,
        deployment="level-2",
    )


def _assert_miss(stack, gw: str, custody_base: str, *, target: str, estate: str) -> None:
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case()]},
        _fixture(stack, custody_base, gw, target=target, estate=estate),
    )
    by_id = {c["id"]: c for c in report["cases"]}
    assert by_id[CASE_ID]["result"] == "passed", dump_report(report)
    assert report["failed"] == 0, dump_report(report)


def _assert_absent_from_generated(text: str) -> None:
    assert UNKNOWN_PATH not in text
    assert UNKNOWN_ROUTE not in text


def test_kong_fragment_unknown_route(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture("kong")
    existing = {"kong.yaml": _add_kong_unknown(existing["kong.yaml"])}
    files = generate(qualified, target="kong", mode="fragment", existing=existing)
    merged = yaml.safe_load(files["kong.yaml"])
    names = [r.get("name") for r in (merged["services"][0].get("routes") or [])]
    assert UNKNOWN_ROUTE in names
    assert "estate-catchall" not in names
    kong_stack.load_generated(files)
    _assert_miss(
        kong_stack, "kong", CUSTODY,
        target="kong", estate="fragment",
    )


def test_kong_bundle_drift_unknown_route(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="kong")
    _assert_absent_from_generated(files["kong.yaml"])
    kong_stack.load_generated(files)
    drifted = _add_kong_unknown(kong_point_at_echo(files["kong.yaml"]))
    kong_stack.load(drifted, authorization=files.get("authorization.yaml"))
    _assert_miss(
        kong_stack, "kong", CUSTODY,
        target="kong", estate="bundle-drift",
    )


def test_apisix_fragment_unknown_route(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture("apisix")
    existing = {"apisix.yaml": _add_apisix_unknown(existing["apisix.yaml"])}
    files = generate(qualified, target="apisix", mode="fragment", existing=existing)
    merged = yaml.safe_load(files["apisix.yaml"])
    ids = [str(r.get("id") or r.get("name")) for r in (merged.get("routes") or [])]
    assert UNKNOWN_ROUTE in ids
    assert "estate-catchall" not in ids
    apisix_stack.load_generated(files)
    _assert_miss(
        apisix_stack, "apisix", APISIX_CUSTODY,
        target="apisix", estate="fragment",
    )


def test_apisix_bundle_drift_unknown_route(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="apisix")
    _assert_absent_from_generated(files["apisix.yaml"])
    apisix_stack.load_generated(files)
    drifted = _add_apisix_unknown(apisix_point_at_echo(files["apisix.yaml"]))
    apisix_stack.load(drifted)
    _assert_miss(
        apisix_stack, "apisix", APISIX_CUSTODY,
        target="apisix", estate="bundle-drift",
    )
