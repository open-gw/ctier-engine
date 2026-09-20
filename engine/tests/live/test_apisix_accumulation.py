"""Live APISIX accumulation: decomposition, decay, isolation, unavailable floor."""
from __future__ import annotations

import json
import time

import pytest

from ctier.compose import compose
from ctier.generate import DEFAULT_CUSTODY_TIMEOUT_MS, DEFAULT_FLOOR_POLL_MS, generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY_INTERNAL

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
FLOOR_POLL_MS = DEFAULT_FLOOR_POLL_MS
CUSTODY_TIMEOUT_MS = DEFAULT_CUSTODY_TIMEOUT_MS
LIVE_DECAY_SECONDS = 5
ESCALATE_ABOVE = 9
T1_WEIGHT = 1
CROSSING = ESCALATE_ABOVE // T1_WEIGHT + 1  # 10
BALANCE = "/accounts/12345/balance"
CUSTODY_CFG = {
    "url": CUSTODY_INTERNAL,
    "timeout_ms": CUSTODY_TIMEOUT_MS,
    "floor_poll_ms": FLOOR_POLL_MS,
}


def _load(apisix_stack, qualified) -> None:
    files = generate(qualified, target="apisix", custody=CUSTODY_CFG)
    apisix_stack.load_generated(files)


def _applied_tier(raw: bytes) -> int | None:
    payload = json.loads(raw.decode("utf-8")) if raw else {}
    headers = payload.get("headers") or {}
    value = headers.get("x-ctier-tier")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _t1(apisix_stack, scope: str, agent: str = "agent-live-32") -> tuple[int, int | None]:
    status, raw, _ = apisix_stack.request(
        "GET",
        BALANCE,
        headers=apisix_stack.auth_headers(**{"X-Agent-Id": agent, "X-Task-Id": scope}),
    )
    return status, _applied_tier(raw)


def _wait_for_floor(apisix_stack, scope: str, *, at_least: int = 2) -> tuple[int, float]:
    """Escalation is a bound: threshold-crossing plus one poll interval."""
    started = time.monotonic()
    deadline = started + (FLOOR_POLL_MS / 1000.0) + 0.5
    last = 1
    while time.monotonic() < deadline:
        status, tier = _t1(apisix_stack, scope)
        assert status == 200, "escalation must not refuse"
        last = tier if tier is not None else last
        if tier is not None and tier >= at_least:
            return tier, time.monotonic() - started
        time.sleep(0.15)
    raise AssertionError(
        f"scope {scope!r} still at {last} after bound "
        f"(threshold-crossing + {FLOOR_POLL_MS} ms)"
    )


def test_decomposition_escalates_within_the_bounded_window(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(apisix_stack, qualified)
    scope = "task-32-decomp"
    for _ in range(CROSSING):
        status, tier = _t1(apisix_stack, scope)
        assert status == 200
        assert tier == 1
    raised, waited = _wait_for_floor(apisix_stack, scope)
    assert raised >= 2, waited
    assert waited <= (FLOOR_POLL_MS / 1000.0) + 0.5


def test_under_threshold_does_not_escalate(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(apisix_stack, qualified)
    scope = "task-32-under"
    for _ in range(3):
        status, tier = _t1(apisix_stack, scope)
        assert status == 200
        assert tier == 1
    time.sleep((2 * FLOOR_POLL_MS) / 1000.0)
    status, tier = _t1(apisix_stack, scope)
    assert status == 200
    assert tier == 1


def test_interleaved_scopes_do_not_contaminate(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(apisix_stack, qualified)
    hot = "task-32-iso-hot"
    cold = "task-32-iso-cold"
    for i in range(CROSSING):
        status, tier = _t1(apisix_stack, hot)
        assert status == 200 and tier == 1
        if i < 3:
            status, tier = _t1(apisix_stack, cold)
            assert status == 200 and tier == 1
    raised, _ = _wait_for_floor(apisix_stack, hot)
    assert raised >= 2
    time.sleep((2 * FLOOR_POLL_MS) / 1000.0)
    status, tier = _t1(apisix_stack, cold)
    assert status == 200
    assert tier == 1


def test_gap_longer_than_decay_resets_accumulation(apisix_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(apisix_stack, qualified)
    scope = "task-32-decay"
    for _ in range(CROSSING):
        status, tier = _t1(apisix_stack, scope)
        assert status == 200 and tier == 1
    raised, _ = _wait_for_floor(apisix_stack, scope)
    assert raised >= 2
    time.sleep(LIVE_DECAY_SECONDS + (FLOOR_POLL_MS / 1000.0) + 0.5)
    status, tier = _t1(apisix_stack, scope)
    assert status == 200
    assert tier == 1


def test_unavailable_floor_does_not_escalate_or_refuse(apisix_stack):
    """ADR-0011: no floor is no escalation, not maximum escalation."""
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(apisix_stack, qualified)
    scope = "task-32-no-floor"
    try:
        apisix_stack.stop_service("custody")
        for _ in range(CROSSING + 2):
            status, tier = _t1(apisix_stack, scope)
            assert status == 200, status
            assert status not in (423, 503)
            assert tier == 1
        time.sleep((2 * FLOOR_POLL_MS) / 1000.0)
        status, tier = _t1(apisix_stack, scope)
        assert status == 200
        assert tier == 1
    finally:
        apisix_stack.start_service("custody")
