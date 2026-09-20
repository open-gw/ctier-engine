# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Run a corpus against N adapters. Agreement is the product."""
from __future__ import annotations

from typing import Sequence

import yaml

from .adapter import Adapter, ObservedDecision

REPORT_SCHEMA = "conformance-report/0.1.0-draft"


class CorpusExpectationError(ValueError):
    """A case cannot be evaluated at the declared deployment. Not a skip."""


def case_steps(case: dict) -> list[dict]:
    """Expand a case to runnable steps. A single-request case is a sequence of one."""
    if "sequence" not in case:
        return [case]
    agent = dict(case.get("agent") or {"id": "agent-a"})
    if "taskId" not in agent and case.get("scope"):
        agent["taskId"] = case["scope"]
    steps = []
    for i, step in enumerate(case["sequence"]):
        steps.append({
            "id": f"{case['id']}#{i}",
            "scope": case.get("scope"),
            "profile": case.get("profile"),
            "placeholder": case.get("placeholder"),
            "agent": step.get("agent") or agent,
            "request": step["request"],
            "expect": step["expect"],
            "refreshToken": bool(step.get("refreshToken")),
        })
    return steps


def expected_decision(case: dict, deployment: str) -> tuple:
    """Return (appliedTier, disposition) for this case at this deployment.

    appliedTier is always the classification claim. disposition is taken from
    expect.disposition, or from expect.dispositionByLevel[deployment]. A mapping
    with no entry for the run's level is a corpus error, not a skip.
    """
    case_id = case.get("id", "<unknown>")
    expect = case["expect"]
    tier = expect.get("appliedTier")
    by_level = expect.get("dispositionByLevel")
    if by_level is not None:
        if deployment not in by_level:
            raise CorpusExpectationError(
                f"corpus error: case {case_id!r} has no disposition for "
                f"deployment {deployment!r}"
            )
        return (tier, by_level[deployment])
    if "disposition" not in expect:
        raise CorpusExpectationError(
            f"corpus error: case {case_id!r} has neither disposition nor "
            f"dispositionByLevel"
        )
    return (tier, expect["disposition"])


def expect_matches(
    observed: ObservedDecision,
    expect: dict,
    deployment: str,
    case_id: str,
) -> bool:
    """True when observation satisfies expect, including appliedTierAtLeast."""
    if "appliedTierAtLeast" in expect:
        least = expect["appliedTierAtLeast"]
        if observed.applied_tier is None or observed.applied_tier < least:
            return False
        if "disposition" in expect or "dispositionByLevel" in expect:
            proxy = {
                "id": case_id,
                "expect": {
                    "appliedTier": expect.get("appliedTier", least),
                    **{k: expect[k] for k in ("disposition", "dispositionByLevel") if k in expect},
                },
            }
            _tier, disposition = expected_decision(proxy, deployment)
            return observed.disposition == disposition
        return True
    return _tuple(observed) == expected_decision(
        {"id": case_id, "expect": expect}, deployment
    )


def _tuple(observed: ObservedDecision) -> tuple:
    return (observed.applied_tier, observed.disposition)


def _run_step(
    step: dict,
    adapters: Sequence[Adapter],
    deployment: str,
) -> tuple[dict, bool]:
    observed: dict[str, dict] = {}
    results: list[ObservedDecision] = []
    for adapter in adapters:
        result = adapter.run(step)
        observed[adapter.name] = result.to_dict()
        results.append(result)
    matches = all(
        expect_matches(r, step["expect"], deployment, step["id"]) for r in results
    )
    if "appliedTierAtLeast" in step["expect"]:
        agree = matches
        expect_out = dict(step["expect"])
    else:
        adapters_match = len({_tuple(r) for r in results}) == 1
        agree = adapters_match and matches
        tier, disposition = expected_decision(step, deployment)
        expect_out = {"appliedTier": tier, "disposition": disposition}
    return {
        "expect": expect_out,
        "observed": observed,
        "agree": agree,
    }, agree


def run_corpus(corpus: dict, adapters: Sequence[Adapter]) -> dict:
    if not adapters:
        raise ValueError("run_corpus requires at least one adapter")
    if "deployment" not in corpus:
        raise CorpusExpectationError("corpus error: missing deployment")
    deployment = corpus["deployment"]
    rows = []
    all_agree = True
    for case in corpus["cases"]:
        steps = case_steps(case)
        if "sequence" in case:
            step_rows = []
            case_agree = True
            for step in steps:
                row, agree = _run_step(step, adapters, deployment)
                step_rows.append(row)
                case_agree = case_agree and agree
            all_agree = all_agree and case_agree
            rows.append({
                "id": case["id"],
                "agree": case_agree,
                "steps": step_rows,
            })
            continue
        step = steps[0]
        observed: dict[str, dict] = {}
        tuples = []
        for adapter in adapters:
            result = adapter.run(step)
            observed[adapter.name] = result.to_dict()
            tuples.append(_tuple(result))
        expect_tuple = expected_decision(step, deployment)
        adapters_match = len(set(tuples)) == 1
        matches_expect = all(t == expect_tuple for t in tuples)
        agree = adapters_match and matches_expect
        all_agree = all_agree and agree
        rows.append({
            "id": case["id"],
            "expect": {
                "appliedTier": expect_tuple[0],
                "disposition": expect_tuple[1],
            },
            "observed": observed,
            "agree": agree,
        })
    return {
        "ctierSchema": REPORT_SCHEMA,
        "composition": corpus["composition"],
        "deployment": deployment,
        "adapters": [a.name for a in adapters],
        "agree": all_agree,
        "cases": rows,
    }


def dump_report(report: dict) -> str:
    return yaml.safe_dump(
        report,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
