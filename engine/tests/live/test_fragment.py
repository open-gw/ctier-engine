"""Fragment mode on a populated gateway. Kong and APISIX live; Apigee artefact-only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.conformance.adapter import ReferenceAdapter
from ctier.conformance.apisix import ApisixAdapter
from ctier.conformance.kong import KongAdapter
from ctier.conformance.runner import dump_report, run_corpus
from ctier.corpus import build_corpus, load_extras
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.apisix_rig import PROXY as APISIX_PROXY
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, PROXY
from tests.test_fragment import load_fixture

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "existing"


def _echo_headers(payload: dict) -> dict[str, str]:
    raw = payload.get("headers") or {}
    return {str(k).lower(): str(v) for k, v in raw.items()}


def _ledger_by_correlation(custody_base: str, cid: str) -> dict:
    from tests.live.rig import http

    status, raw, _ = http("GET", custody_base + "/v1/ledger?type=decision")
    assert status == 200, raw
    records = json.loads(raw.decode("utf-8")).get("records") or []
    match = [r for r in records if r.get("correlationId") == cid]
    assert match, records
    return match[-1]


def _fragment_kong(kong_stack, *, custody=None):
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture("kong")
    cfg = None
    if custody:
        cfg = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}
    files = generate(qualified, target="kong", mode="fragment", existing=existing, custody=cfg)
    kong_stack.load_generated(files)
    return kong_stack, files


def _fragment_apisix(apisix_stack, *, custody=False):
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture("apisix")
    cfg = None
    if custody:
        cfg = {"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200}
    files = generate(qualified, target="apisix", mode="fragment", existing=existing, custody=cfg)
    apisix_stack.load_generated(files)
    return apisix_stack, files


def test_fixtures_exist_on_disk():
    assert (FIXTURE / "kong.yaml").is_file()
    assert (FIXTURE / "apisix.yaml").is_file()
    assert (FIXTURE / "apigee" / "apiproxy" / "proxies" / "default.xml").is_file()


def test_kong_fragment_corpus_matches_bundle_level2(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-2")
    _fragment_kong(kong_stack)

    def request_fn(method, url, headers, data):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return kong_stack.request(
            method, parsed.path, query=query or None, headers=headers,
            body=None if data is None else data.decode("utf-8"),
        )

    report = run_corpus(
        corpus,
        [
            ReferenceAdapter(qualified, deployment="level-2"),
            KongAdapter(
                PROXY,
                request_fn=request_fn,
                qualified_spec=qualified,
                token=kong_stack.token(),
                token_fn=kong_stack.token,
            ),
        ],
    )
    dumped = dump_report(report)
    disagree = [c for c in report["cases"] if not c["agree"]]
    assert report["agree"] is True, (
        f"fragment != bundle/reference; disagree={[c['id'] for c in disagree]}\n{dumped}"
    )


def test_kong_fragment_corpus_level3(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-3")
    _fragment_kong(kong_stack, custody=True)

    def request_fn(method, url, headers, data):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return kong_stack.request(
            method, parsed.path, query=query or None, headers=headers,
            body=None if data is None else data.decode("utf-8"),
        )

    report = run_corpus(
        corpus,
        [
            ReferenceAdapter(qualified, deployment="level-3"),
            KongAdapter(
                PROXY,
                request_fn=request_fn,
                qualified_spec=qualified,
                token=kong_stack.token(),
                token_fn=kong_stack.token,
            ),
        ],
    )
    dumped = dump_report(report)
    disagree = [c for c in report["cases"] if not c["agree"]]
    assert report["agree"] is True, (
        f"fragment level-3 disagree={[c['id'] for c in disagree]}\n{dumped}"
    )


def test_kong_fragment_forged_header_does_not_reach_backend(kong_stack):
    _fragment_kong(kong_stack)
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=kong_stack.auth_headers(**{
            "x-ctier-unknown-audit": "agent",
            "X-Correlation-Id": "agent-correlation",
        }),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    assert "x-ctier-unknown-audit" not in headers
    assert headers.get("x-ctier-forged") != "estate"
    assert "x-ctier-forged" not in headers
    assert headers.get("x-correlation-id") != "agent-correlation"
    assert headers.get("x-estate-seen") == "1"


def test_kong_fragment_join_key_equals_record(kong_stack):
    _fragment_kong(kong_stack, custody=True)
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=kong_stack.auth_headers(),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    cid = headers.get("x-ctier-correlation-id")
    assert cid
    record = _ledger_by_correlation(CUSTODY, cid)
    assert record["correlationId"] == cid


def test_apisix_fragment_corpus_level2(apisix_stack):
    """Re-run of the 16 differential against the intact estate rewrite Lua."""
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-2")
    _fragment_apisix(apisix_stack)
    from tests.live.test_apisix_corpus import _request_fn

    report = run_corpus(
        corpus,
        [
            ReferenceAdapter(qualified, deployment="level-2"),
            ApisixAdapter(
                APISIX_PROXY,
                request_fn=_request_fn(apisix_stack),
                qualified_spec=qualified,
                token=apisix_stack.token(),
                token_fn=apisix_stack.token,
            ),
        ],
    )
    dumped = dump_report(report)
    disagree = [c for c in report["cases"] if not c["agree"]]
    assert report["agree"] is True, (
        f"fragment apisix disagree={[c['id'] for c in disagree]}\n{dumped}"
    )


def test_apisix_fragment_corpus_level3(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-3")
    _fragment_apisix(apisix_stack, custody=True)
    from tests.live.test_apisix_corpus import _request_fn

    report = run_corpus(
        corpus,
        [
            ReferenceAdapter(qualified, deployment="level-3"),
            ApisixAdapter(
                APISIX_PROXY,
                request_fn=_request_fn(apisix_stack),
                qualified_spec=qualified,
                token=apisix_stack.token(),
                token_fn=apisix_stack.token,
            ),
        ],
    )
    dumped = dump_report(report)
    disagree = [c for c in report["cases"] if not c["agree"]]
    assert report["agree"] is True, (
        f"fragment apisix L3 disagree={[c['id'] for c in disagree]}\n{dumped}"
    )


def test_apisix_fragment_forged_header_does_not_reach_backend(apisix_stack):
    _fragment_apisix(apisix_stack)
    status, payload = apisix_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=apisix_stack.auth_headers(**{
            "x-ctier-unknown-audit": "agent",
            "X-Correlation-Id": "agent-correlation",
        }),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    assert "x-ctier-unknown-audit" not in headers
    assert "x-ctier-forged" not in headers
    assert headers.get("x-correlation-id") != "agent-correlation"
    assert headers.get("x-estate-seen") == "1"


def test_apisix_fragment_join_key_equals_record(apisix_stack):
    _fragment_apisix(apisix_stack, custody=True)
    status, payload = apisix_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=apisix_stack.auth_headers(),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    cid = headers.get("x-ctier-correlation-id")
    assert cid
    record = _ledger_by_correlation(APISIX_CUSTODY, cid)
    assert record["correlationId"] == cid


def test_apisix_fragment_estate_rewrite_still_on_the_route(apisix_stack):
    _stack, files = _fragment_apisix(apisix_stack)
    doc = yaml.safe_load(files["apisix.yaml"])
    getb = next(r for r in doc["routes"] if r["name"] == "getBalance")
    joined = "\n".join(getb["plugins"]["serverless-pre-function"]["functions"])
    assert "x-ctier-forged" in joined
    assert "X-Estate-Seen" in joined
    status, payload = apisix_stack.echo_json(
        "GET", "/accounts/12345/balance",
        headers=apisix_stack.auth_headers(),
    )
    assert status == 200, payload
    headers = _echo_headers(payload)
    assert headers.get("x-estate-seen") == "1"
    assert "x-ctier-forged" not in headers
