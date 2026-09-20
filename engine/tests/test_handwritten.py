"""Hand-written extras merge into a generated corpus without reordering it."""
from __future__ import annotations

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.corpus import build_corpus, dump_corpus, load_extras
from ctier.spec_loader import SPEC_DIR
from ctier.validate import iter_operations
from tests.golden_util import GOLDEN_ROOT, NOW
from tests.test_corpus import _validate

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
SIBLING = GOLDEN_ROOT / "generate" / "sibling-paths" / "in" / "description.yaml"


def test_handwritten_extras_append_deterministically():
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    assert [c["id"] for c in extras] == [
        "bounds-exceeds-listTransactions",
        "bounds-decimal-listTransactions",
        "bounds-scientific-listTransactions",
        "bounds-at-max-listTransactions",
        "bounds-non-numeric-listTransactions",
        "bounds-absent-listTransactions",
        "undeclared-exportStatements",
        "excluded-closeAccount",
        "c11-injected-tier-ignored",
    ]
    a = dump_corpus(build_corpus(qualified, extras))
    b = dump_corpus(build_corpus(qualified, extras))
    assert a == b
    corpus = build_corpus(qualified, extras)
    _validate(corpus)
    assert corpus["deployment"] == "level-2"
    n_ops = len(iter_operations(qualified))
    assert [c["id"] for c in corpus["cases"][:n_ops]] == [
        c["id"] for c in build_corpus(qualified)["cases"]
    ]
    assert [c["id"] for c in corpus["cases"][n_ops:]] == [c["id"] for c in extras]
    c11 = corpus["cases"][-1]
    assert "placeholder" not in c11
    assert c11["id"] == "c11-injected-tier-ignored"
    assert c11["request"]["path"] == "/config/feature-flags"
    assert c11["request"]["headers"]["x-ctier-tier"] == "1"
    assert c11["expect"] == {"appliedTier": 4, "disposition": "refuse-and-suspend"}
    exceeds = next(c for c in extras if c["id"] == "bounds-exceeds-listTransactions")
    assert exceeds["expect"] == {
        "appliedTier": 3,
        "dispositionByLevel": {
            "level-2": "refuse-provisioning",
            "level-3": "withhold",
        },
    }


def test_sibling_collision_extras_bind_to_the_sibling_composition():
    qualified, _ = compose(SIBLING, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "sibling-paths.yaml")
    corpus = build_corpus(qualified, extras)
    _validate(corpus)
    ids = [c["id"] for c in corpus["cases"]]
    assert ids[:2] == ["generated-cancelOrder", "generated-getOrderSummary"]
    assert ids[2:] == [
        "sibling-literal-getOrderSummary",
        "sibling-template-cancelOrder",
    ]
    by_id = {c["id"]: c for c in corpus["cases"]}
    assert by_id["sibling-literal-getOrderSummary"]["expect"]["appliedTier"] == 1
    assert by_id["sibling-template-cancelOrder"]["expect"]["appliedTier"] == 4
