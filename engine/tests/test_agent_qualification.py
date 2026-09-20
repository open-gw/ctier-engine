"""Qualification gate scoring. No model, no network.

Thresholds are the committed floor. A failed gate cannot emit arm tables.
"""
from __future__ import annotations

import pytest

from tests.live.test_agent_contract import (
    GATE_TRIALS,
    MAX_TURNS,
    Q1_PASS_MIN,
    Q2_PASS_MIN,
    Q3_PASS_MIN,
    Q4_MARGIN_FRACTION,
    QualificationError,
    assert_qualified,
    evaluate_gate,
    q1_trial_pass,
    q2_trial_pass,
    q3_trial_pass,
    q4_packed_turns,
    select_num_ctx,
)


def test_thresholds_are_the_committed_floor():
    assert GATE_TRIALS == 5
    assert Q1_PASS_MIN == 5
    assert Q2_PASS_MIN == 5
    assert Q3_PASS_MIN == 4
    assert Q4_MARGIN_FRACTION == 0.25
    assert q4_packed_turns() == 10
    assert MAX_TURNS == 8


def test_gate_passes_only_when_every_check_clears():
    ok = evaluate_gate(q1_passes=5, q2_passes=5, q3_retries=4, q4_ok=True)
    assert ok["passed"] is True
    assert ok["failing"] == []


def test_gate_fails_named_checks_and_blocks_arms():
    gate = evaluate_gate(q1_passes=5, q2_passes=5, q3_retries=0, q4_ok=True)
    assert gate["passed"] is False
    assert gate["failing"] == ["Q3"]
    with pytest.raises(QualificationError, match="instrument not qualified: Q3"):
        assert_qualified(gate)


def test_each_check_can_fail_the_gate_alone():
    cases = [
        dict(q1_passes=4, q2_passes=5, q3_retries=5, q4_ok=True, fail="Q1"),
        dict(q1_passes=5, q2_passes=4, q3_retries=5, q4_ok=True, fail="Q2"),
        dict(q1_passes=5, q2_passes=5, q3_retries=3, q4_ok=True, fail="Q3"),
        dict(q1_passes=5, q2_passes=5, q3_retries=5, q4_ok=False, fail="Q4"),
    ]
    for row in cases:
        fail = row.pop("fail")
        gate = evaluate_gate(**row)
        assert gate["failing"] == [fail], fail
        with pytest.raises(QualificationError, match=fail):
            assert_qualified(gate)


def test_missing_gate_cannot_produce_arm_tables():
    with pytest.raises(QualificationError, match="gate-not-run"):
        assert_qualified(None)


def test_q1_requires_a_structured_get_not_prose():
    assert q1_trial_pass([]) is False
    assert q1_trial_pass([{"method": "PUT", "path": "/health"}]) is False
    assert q1_trial_pass([{"method": "GET", "path": "/health"}]) is True


def test_q2_requires_the_second_call_after_the_first():
    assert q2_trial_pass([
        {"method": "GET", "path": "/session", "turn": 1},
        {"method": "GET", "path": "/whoami", "turn": 1},
    ]) is False
    assert q2_trial_pass([
        {"method": "GET", "path": "/session", "turn": 1},
        {"method": "GET", "path": "/whoami", "turn": 2},
    ]) is True
    assert q2_trial_pass([{"method": "GET", "path": "/whoami", "turn": 1}]) is False


def test_q3_requires_a_wire_retry():
    assert q3_trial_pass({"retried": False, "withheld_attempts": 1}) is False
    assert q3_trial_pass({"retried": True, "withheld_attempts": 2}) is True


def test_architecture_context_length_is_not_num_ctx():
    num_ctx, source = select_num_ctx(
        ps_context=None,
        modelfile_num_ctx=None,
        architecture_context_length=131072,
    )
    assert num_ctx is None
    assert source is None
    num_ctx, source = select_num_ctx(
        ps_context=None,
        modelfile_num_ctx=4096,
        architecture_context_length=131072,
    )
    assert num_ctx == 4096
    assert source == "api/show parameters num_ctx"
    num_ctx, source = select_num_ctx(
        ps_context=2048,
        modelfile_num_ctx=4096,
        architecture_context_length=131072,
    )
    assert num_ctx == 2048
    assert source == "api/ps"
