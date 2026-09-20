"""Classification-agreement corpus: generation, determinism, golden."""
from __future__ import annotations

from pathlib import Path

import yaml

from ctier.compose import compose
from ctier.corpus import build_corpus, dump_corpus, instantiate_path
from ctier.spec_loader import SPEC_DIR
from ctier.validate import iter_operations, validate_named_schema
from tests.golden_util import GOLDEN_ROOT, NOW

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
GOLDEN = GOLDEN_ROOT / "conformance" / "reference" / "expect" / "corpus.yaml"


def _qualified():
    qualified, _manifest = compose(REFERENCE, [], NOW)
    return qualified


def _validate(corpus: dict) -> None:
    validate_named_schema("conformance-corpus-0.3.0.json", corpus)


def test_instantiate_path_satisfies_templates():
    assert instantiate_path("/accounts/{accountId}/balance") == "/accounts/accountId/balance"
    assert instantiate_path("/orders/summary") == "/orders/summary"
    assert instantiate_path("/") == "/"


def test_build_corpus_is_byte_identical_twice():
    qualified = _qualified()
    a = dump_corpus(build_corpus(qualified))
    b = dump_corpus(build_corpus(qualified))
    assert a == b


def test_generated_corpus_has_one_case_per_operation():
    qualified = _qualified()
    ops = iter_operations(qualified)
    corpus = build_corpus(qualified)
    _validate(corpus)
    assert corpus["profile"] == "standard"
    assert corpus["deployment"] == "level-2"
    assert corpus["ctierSchema"] == "conformance-corpus/0.3.0"
    assert len(corpus["cases"]) == len(ops)
    ids = [c["id"] for c in corpus["cases"]]
    assert ids == [f"generated-{op.get('operationId')}" for _p, _m, op, _pp in ops]
    by_id = {c["id"]: c for c in corpus["cases"]}
    export = by_id["generated-exportStatements"]
    assert export["request"]["method"] == "POST"
    assert export["request"]["path"] == "/accounts/accountId/statements/export"
    assert export["expect"] == {"appliedTier": 4, "disposition": "refuse-and-suspend"}
    close = by_id["generated-closeAccount"]
    assert close["expect"] == {"appliedTier": 4, "disposition": "refuse-provisioning"}
    balance = by_id["generated-getBalance"]
    assert balance["expect"] == {"appliedTier": 1, "disposition": "execute"}
    prefs = by_id["generated-updateCommunicationPreferences"]
    assert prefs["expect"] == {
        "appliedTier": 3,
        "dispositionByLevel": {
            "level-2": "refuse-provisioning",
            "level-3": "withhold",
        },
    }
    assert balance["agent"]["taskId"] == "task-getBalance"


def test_0_3_0_accepts_single_request_and_sequence():
    from ctier.conformance import HANDWRITTEN_DIR
    from ctier.corpus import load_extras

    qualified = _qualified()
    extras = load_extras(HANDWRITTEN_DIR / "accumulation.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-3")
    _validate(corpus)
    assert corpus["ctierSchema"] == "conformance-corpus/0.3.0"
    by_id = {c["id"]: c for c in corpus["cases"]}
    assert "request" in by_id["generated-getBalance"]
    assert "sequence" not in by_id["generated-getBalance"]
    decomp = by_id["decomposition-escalates"]
    assert decomp["scope"] == "task-decomp-1"
    assert decomp["sequence"][-1]["expect"] == {"appliedTierAtLeast": 2}
    under = by_id["under-threshold-no-escalation"]
    assert len(under["sequence"]) == 3
    assert all(s["expect"]["appliedTier"] == 1 for s in under["sequence"])
    ids = [c["id"] for c in extras]
    assert ids == [
        "decomposition-escalates",
        "under-threshold-no-escalation",
        "isolation-scope-hot",
        "isolation-scope-cold",
        "decay-resets-long-running-agent",
    ]


def test_suspension_extras_are_kong_only_sequences():
    from ctier.conformance import HANDWRITTEN_DIR
    from ctier.corpus import load_extras

    extras = load_extras(HANDWRITTEN_DIR / "suspension.yaml")
    assert [c["id"] for c in extras] == [
        "tier-4-suspends-the-agent",
        "rejected-tier-3-suspends-the-agent",
        "expired-tier-3-does-not-suspend",
    ]
    # 401 is an observation, not a classified disposition. These extras
    # are Kong-only and are not merged into the 24-case differential.
    by_id = {c["id"]: c for c in extras}
    assert by_id["tier-4-suspends-the-agent"]["sequence"][-1]["expect"] == {
        "disposition": "refuse-unauthorized",
    }
    assert by_id["rejected-tier-3-suspends-the-agent"]["sequence"][-1].get("refreshToken") is True
    assert by_id["expired-tier-3-does-not-suspend"]["sequence"][-1]["expect"] == {
        "appliedTier": 1,
        "disposition": "execute",
    }


def test_entitlement_extras_are_kong_only_sequences():
    from ctier.conformance import HANDWRITTEN_DIR
    from ctier.corpus import load_extras

    extras = load_extras(HANDWRITTEN_DIR / "entitlement.yaml")
    assert [c["id"] for c in extras] == [
        "unentitled-client-cannot-initiate-payment",
    ]
    by_id = {c["id"]: c for c in extras}
    assert by_id["unentitled-client-cannot-initiate-payment"]["agent"]["id"] == (
        "agent-sub-balance"
    )
    assert by_id["unentitled-client-cannot-initiate-payment"]["sequence"][-1]["expect"] == {
        "disposition": "refuse-unauthorized",
    }


def test_golden_reference_corpus():
    actual = dump_corpus(build_corpus(_qualified()))
    expected = GOLDEN.read_text(encoding="utf-8")
    if actual != expected:
        raise AssertionError(
            "reference corpus golden mismatch; rewrite "
            f"{GOLDEN.relative_to(Path(__file__).parent.parent)} if the generator changed"
        )
