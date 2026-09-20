"""Differential corpus: ReferenceAdapter vs KongAdapter on a live proxy."""
from __future__ import annotations

import pytest

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.conformance.adapter import ReferenceAdapter
from ctier.conformance.kong import KongAdapter
from ctier.conformance.runner import dump_report, run_corpus
from ctier.corpus import build_corpus, load_extras
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.rig import PROXY, point_at_echo

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"


def test_differential_corpus_reference_vs_kong(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-2")
    files = generate(qualified, target="kong")
    kong_stack.load_generated(files)

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
    n = len(report["cases"])
    disagree = [c for c in report["cases"] if not c["agree"]]

    c11 = next(c for c in report["cases"] if c["id"] == "c11-injected-tier-ignored")
    assert c11["agree"] is True
    kong_c11 = c11["observed"]["kong"]
    assert kong_c11["disposition"] == "refuse-and-suspend"
    assert kong_c11["appliedTier"] == 4
    assert kong_c11["evidence"].get("backendReached") is False

    assert report["adapters"] == ["reference", "kong"]
    assert report["deployment"] == "level-2"
    assert n == 24
    assert n == len(corpus["cases"])
    assert report["agree"] is True, (
        f"expected 24/24 at level-2; disagree={[c['id'] for c in disagree]}\n{dumped}"
    )
    print(
        f"\n08d differential: cases={n} agree={n} disagree=0 deployment=level-2\n"
    )
    print(dumped)
