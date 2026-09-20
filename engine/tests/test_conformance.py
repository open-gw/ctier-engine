"""Runner, ReferenceAdapter, and a stub that is known to disagree."""
from __future__ import annotations

from pathlib import Path

import yaml

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.conformance.adapter import Adapter, ObservedDecision, ReferenceAdapter
from ctier.conformance.kong import KongAdapter, identity_headers
from ctier.conformance.runner import (
    CorpusExpectationError,
    case_steps,
    dump_report,
    expect_matches,
    expected_decision,
    run_corpus,
)
from ctier.corpus import build_corpus, load_extras
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import GOLDEN_ROOT, NOW

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
SIBLING = GOLDEN_ROOT / "generate" / "sibling-paths" / "in" / "description.yaml"
REPORT_GOLDEN = GOLDEN_ROOT / "conformance" / "reference" / "expect" / "report.yaml"


class AlwaysExecute(Adapter):
    """Deliberately wrong. A harness that cannot fail is not known to work."""

    name = "stub-always-execute"

    def run(self, case: dict) -> ObservedDecision:
        return ObservedDecision(
            applied_tier=1,
            disposition="execute",
            evidence={"status": 200, "note": "stub ignores the spec"},
        )


def _reference_corpus():
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    return qualified, build_corpus(qualified, extras)


def test_reference_path_cannot_honour_injected_tier_on_declared_4():
    """C11: nothing in resolve + classify reads request headers."""
    import inspect

    from ctier.classifier import Classifier
    from ctier.conformance.resolve import operation_from_openapi, resolve_operation

    qualified, _ = compose(REFERENCE, [], NOW)
    adapter = ReferenceAdapter(qualified)
    plain = {
        "id": "exp-declared-t4",
        "request": {
            "method": "PUT",
            "path": "/config/feature-flags",
            "query": {},
            "headers": {},
            "body": None,
        },
        "agent": {"id": "agent-a", "taskId": "task-1"},
        "expect": {"appliedTier": 4, "disposition": "refuse-and-suspend"},
    }
    injected = {
        **plain,
        "request": {**plain["request"], "headers": {"x-ctier-tier": "1"}},
    }
    a = adapter.run(plain)
    b = adapter.run(injected)
    assert a.applied_tier == 4 and a.disposition == "refuse-and-suspend"
    assert (b.applied_tier, b.disposition) == (a.applied_tier, a.disposition)
    op = resolve_operation(qualified, injected["request"])
    assert op is not None and int(op.declared_tier) == 4
    assert "headers" not in inspect.getsource(Classifier.classify)
    assert "headers" not in inspect.getsource(resolve_operation)
    assert "headers" not in inspect.getsource(operation_from_openapi)


def test_every_handwritten_case_passes_reference_adapter():
    qualified, _ = compose(REFERENCE, [], NOW)
    adapter = ReferenceAdapter(qualified, deployment="level-2")
    for case in load_extras(HANDWRITTEN_DIR / "reference.yaml"):
        observed = adapter.run(case)
        tier, disposition = expected_decision(case, "level-2")
        assert observed.applied_tier == tier, case["id"]
        assert observed.disposition == disposition, case["id"]


def test_sibling_handwritten_cases_pass_reference_adapter():
    qualified, _ = compose(SIBLING, [], NOW)
    adapter = ReferenceAdapter(qualified)
    for case in load_extras(HANDWRITTEN_DIR / "sibling-paths.yaml"):
        observed = adapter.run(case)
        assert observed.applied_tier == case["expect"]["appliedTier"], case["id"]
        assert observed.disposition == case["expect"]["disposition"], case["id"]


def test_runner_agrees_with_one_adapter():
    qualified, corpus = _reference_corpus()
    report = run_corpus(corpus, [ReferenceAdapter(qualified, deployment="level-2")])
    assert corpus["deployment"] == "level-2"
    assert report["deployment"] == "level-2"
    assert report["adapters"] == ["reference"]
    assert report["agree"] is True
    assert all(row["agree"] is True for row in report["cases"])
    actual = dump_report(report)
    expected = REPORT_GOLDEN.read_text(encoding="utf-8")
    if actual != expected:
        raise AssertionError(
            "reference report golden mismatch; rewrite "
            f"{REPORT_GOLDEN.relative_to(Path(__file__).parent.parent)} if the runner changed"
        )


def test_reference_adapter_projects_tier3_by_deployment():
    qualified, _ = compose(REFERENCE, [], NOW)
    case = next(
        c for c in load_extras(HANDWRITTEN_DIR / "reference.yaml")
        if c["id"] == "bounds-exceeds-listTransactions"
    )
    level2 = ReferenceAdapter(qualified, deployment="level-2").run(case)
    level3 = ReferenceAdapter(qualified, deployment="level-3").run(case)
    assert level2.applied_tier == 3
    assert level3.applied_tier == 3
    assert level2.disposition == "refuse-provisioning"
    assert level3.disposition == "withhold"


def test_missing_disposition_for_declared_level_is_corpus_error():
    qualified, _ = compose(REFERENCE, [], NOW)
    corpus = build_corpus(qualified)
    corpus["deployment"] = "level-2"
    corpus["cases"] = [
        {
            "id": "gap-level-2",
            "request": {
                "method": "GET",
                "path": "/accounts/accountId/balance",
                "query": {},
                "headers": {},
                "body": None,
            },
            "agent": {"id": "agent-a", "taskId": "task-1"},
            "expect": {
                "appliedTier": 3,
                "dispositionByLevel": {"level-3": "withhold"},
            },
        }
    ]
    try:
        run_corpus(corpus, [ReferenceAdapter(qualified, deployment="level-2")])
    except CorpusExpectationError as exc:
        assert "gap-level-2" in str(exc)
        assert "level-2" in str(exc)
    else:
        raise AssertionError("missing dispositionByLevel entry must fail, not skip")


def test_kong_403_applied_tier_comes_from_the_spec():
    """403 does not classify. Exclusion and T3-without-custody share the status."""
    qualified, _ = compose(REFERENCE, [], NOW)

    def always_403(_method, _url, _headers, _data):
        return 403, b"{}", {}

    adapter = KongAdapter(
        "http://kong.example", request_fn=always_403, qualified_spec=qualified,
    )
    t3 = adapter.run({
        "request": {
            "method": "GET",
            "path": "/accounts/12345/transactions",
            "query": {"limit": "101"},
            "headers": {},
            "body": None,
        },
    })
    assert (t3.applied_tier, t3.disposition) == (3, "refuse-provisioning")
    excluded = adapter.run({
        "request": {
            "method": "POST",
            "path": "/accounts/12345/closure",
            "query": {},
            "headers": {},
            "body": None,
        },
    })
    assert (excluded.applied_tier, excluded.disposition) == (4, "refuse-provisioning")


def test_case_steps_expands_a_sequence_and_leaves_singles():
    single = {
        "id": "one",
        "request": {"method": "GET", "path": "/x"},
        "agent": {"id": "agent-a", "taskId": "t"},
        "expect": {"appliedTier": 1, "disposition": "execute"},
    }
    assert case_steps(single) == [single]
    seq = {
        "id": "decomposition-escalates",
        "scope": "task-decomp-1",
        "agent": {"id": "agent-a"},
        "sequence": [
            {"request": {"method": "GET", "path": "/a"}, "expect": {"appliedTier": 1, "disposition": "execute"}},
            {"request": {"method": "GET", "path": "/a"}, "expect": {"appliedTierAtLeast": 2}},
        ],
    }
    steps = case_steps(seq)
    assert [s["id"] for s in steps] == [
        "decomposition-escalates#0",
        "decomposition-escalates#1",
    ]
    assert steps[0]["scope"] == "task-decomp-1"
    assert steps[0]["agent"]["taskId"] == "task-decomp-1"
    assert steps[1]["expect"]["appliedTierAtLeast"] == 2


def test_applied_tier_at_least_matches_a_bound_not_an_index():
    observed = ObservedDecision(2, "execute", {})
    assert expect_matches(
        observed, {"appliedTierAtLeast": 2}, "level-3", "decomp"
    )
    assert expect_matches(
        ObservedDecision(3, "withhold", {}),
        {"appliedTierAtLeast": 2},
        "level-3",
        "decomp",
    )
    assert not expect_matches(
        ObservedDecision(1, "execute", {}),
        {"appliedTierAtLeast": 2},
        "level-3",
        "decomp",
    )


def test_kong_adapter_sends_scope_from_case_id_not_a_shared_task():
    seen = {}

    def fake(_method, _url, headers, _data):
        seen.update(headers)
        return 200, b'{"headers": {"x-ctier-tier": "1"}}', {}

    adapter = KongAdapter("http://kong.example", request_fn=fake)
    adapter.run({
        "id": "generated-getBalance",
        "request": {
            "method": "GET",
            "path": "/ok",
            "query": {},
            "headers": {},
            "body": None,
        },
        "agent": {"id": "agent-a", "taskId": "task-1"},
    })
    assert seen["X-Agent-Id"] == "agent-a"
    assert seen["X-Task-Id"] == "generated-getBalance"
    headers = identity_headers(
        {"id": "c1", "scope": "task-decomp-1", "agent": {"id": "agent-a"}},
        {"X-Task-Id": "already-set"},
    )
    assert headers["X-Task-Id"] == "already-set"


def test_runner_reports_disagreement_with_stub_and_keeps_evidence():
    raw = yaml.safe_dump(
        {
            "openapi": "3.1.0",
            "info": {"title": "harness", "version": "1"},
            "paths": {
                "/ping": {
                    "get": {
                        "operationId": "ping",
                        "x-ctier-tier": 1,
                        "x-ctier-status": "declared",
                        "responses": {"200": {"description": "ok"}},
                    }
                },
                "/gap": {
                    "post": {
                        "operationId": "gap",
                        "responses": {"200": {"description": "ok"}},
                    }
                },
            },
        },
        sort_keys=False,
    ).encode("utf-8")
    qualified, _ = compose(raw, [], NOW)
    corpus = build_corpus(qualified)
    report = run_corpus(corpus, [ReferenceAdapter(qualified), AlwaysExecute()])
    assert report["agree"] is False
    by_id = {row["id"]: row for row in report["cases"]}
    ping = by_id["generated-ping"]
    gap = by_id["generated-gap"]
    assert ping["agree"] is True
    assert gap["agree"] is False
    assert gap["expect"] == {"appliedTier": 4, "disposition": "refuse-and-suspend"}
    assert gap["observed"]["reference"]["appliedTier"] == 4
    assert gap["observed"]["reference"]["disposition"] == "refuse-and-suspend"
    stub = gap["observed"]["stub-always-execute"]
    assert stub["appliedTier"] == 1
    assert stub["disposition"] == "execute"
    assert stub["evidence"]["status"] == 200
    assert "stub ignores the spec" in stub["evidence"]["note"]
    dumped = dump_report(report)
    assert "generated-gap" in dumped
    assert "stub ignores the spec" in dumped
    assert "refuse-and-suspend" in dumped


def test_kong_projection_maps_status_to_decision():
    from ctier.conformance.kong import decision_from_response

    t4 = decision_from_response(423, b"{}")
    assert (t4.applied_tier, t4.disposition) == (4, "refuse-and-suspend")
    assert t4.evidence["backendReached"] is False
    prov = decision_from_response(403, b"{}")
    assert (prov.applied_tier, prov.disposition) == (4, "refuse-provisioning")
    withheld = decision_from_response(202, b"{}")
    assert (withheld.applied_tier, withheld.disposition) == (3, "withhold")
    echo = b'{"headers": {"x-ctier-tier": "1", "x-ctier-operation": "getBalance"}}'
    exe = decision_from_response(200, echo)
    assert (exe.applied_tier, exe.disposition) == (1, "execute")
    assert exe.evidence["backendReached"] is True
    assert exe.evidence["echo"]["x-ctier-operation"] == "getBalance"


def test_kong_adapter_uses_the_projection_without_a_network():
    from ctier.conformance.kong import KongAdapter

    def fake(_method, url, _headers, _data):
        if url.endswith("/locked"):
            return 423, b"{}", {}
        return 200, b'{"headers": {"x-ctier-tier": "2"}}', {}

    adapter = KongAdapter("http://kong.example", request_fn=fake)
    refused = adapter.run({
        "request": {"method": "GET", "path": "/locked", "query": {}, "headers": {}, "body": None},
    })
    assert (refused.applied_tier, refused.disposition) == (4, "refuse-and-suspend")
    executed = adapter.run({
        "request": {
            "method": "GET",
            "path": "/ok",
            "query": {"limit": "1"},
            "headers": {},
            "body": None,
        },
    })
    assert (executed.applied_tier, executed.disposition) == (2, "execute")
