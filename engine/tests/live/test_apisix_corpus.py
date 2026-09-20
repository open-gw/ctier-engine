"""Differential corpus: ReferenceAdapter vs ApisixAdapter on a live proxy."""
from __future__ import annotations

import pytest

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.conformance.adapter import ReferenceAdapter
from ctier.conformance.apisix import ApisixAdapter
from ctier.conformance.runner import dump_report, run_corpus
from ctier.corpus import build_corpus, load_extras
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY_INTERNAL, PROXY

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
CUSTODY_CFG = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}


def _request_fn(apisix_stack):
    def request_fn(method, url, headers, data):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return apisix_stack.request(
            method, parsed.path, query=query or None, headers=headers,
            body=None if data is None else data.decode("utf-8"),
        )
    return request_fn


def test_generated_getBalance_executes_on_apisix(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="apisix")
    apisix_stack.load_generated(files)
    status, payload = apisix_stack.echo_json(
        "GET",
        "/accounts/12345/balance",
        headers=apisix_stack.auth_headers(),
    )
    assert status == 200, payload
    headers = payload.get("headers") or {}
    assert headers.get("x-ctier-tier") == "1", headers
    assert headers.get("x-ctier-operation") == "getBalance", headers
    assert "x-ctier-deployment" in headers, headers
    assert "x-ctier-criteria" not in headers, headers


def test_differential_corpus_reference_vs_apisix_level2(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-2")
    files = generate(qualified, target="apisix")
    apisix_stack.load_generated(files)

    report = run_corpus(
        corpus,
        [
            ReferenceAdapter(qualified, deployment="level-2"),
            ApisixAdapter(
                PROXY,
                request_fn=_request_fn(apisix_stack),
                qualified_spec=qualified,
                token=apisix_stack.token(),
                token_fn=apisix_stack.token,
            ),
        ],
    )
    dumped = dump_report(report)
    n = len(report["cases"])
    disagree = [c for c in report["cases"] if not c["agree"]]

    c11 = next(c for c in report["cases"] if c["id"] == "c11-injected-tier-ignored")
    assert c11["agree"] is True
    observed = c11["observed"]["apisix"]
    assert observed["disposition"] == "refuse-and-suspend"
    assert observed["appliedTier"] == 4
    assert observed["evidence"].get("backendReached") is False

    assert report["adapters"] == ["reference", "apisix"]
    assert report["deployment"] == "level-2"
    assert n == 24
    assert report["agree"] is True, (
        f"expected 24/24 at level-2; disagree={[c['id'] for c in disagree]}\n{dumped}"
    )


def test_differential_corpus_reference_vs_apisix_level3(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-3")
    files = generate(qualified, target="apisix", custody=CUSTODY_CFG)
    apisix_stack.load_generated(files)

    report = run_corpus(
        corpus,
        [
            ReferenceAdapter(qualified, deployment="level-3"),
            ApisixAdapter(
                PROXY,
                request_fn=_request_fn(apisix_stack),
                qualified_spec=qualified,
                token=apisix_stack.token(),
                token_fn=apisix_stack.token,
            ),
        ],
    )
    dumped = dump_report(report)
    n = len(report["cases"])
    disagree = [c for c in report["cases"] if not c["agree"]]
    t3 = [c for c in report["cases"] if c["expect"]["appliedTier"] == 3]
    assert t3
    for row in t3:
        assert row["expect"]["disposition"] == "withhold", row["id"]
        assert row["agree"] is True, row
        assert row["observed"]["apisix"]["disposition"] == "withhold"
        assert row["observed"]["apisix"]["appliedTier"] == 3
        assert row["observed"]["apisix"]["evidence"].get("backendReached") is False

    assert report["deployment"] == "level-3"
    assert n == 24
    assert report["agree"] is True, (
        f"expected 24/24 at level-3; disagree={[c['id'] for c in disagree]}\n{dumped}"
    )
