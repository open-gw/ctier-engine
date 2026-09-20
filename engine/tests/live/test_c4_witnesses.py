"""C4 witnesses. The suite cannot verify a negative property.

These cases can falsify C4, and they can witness consequences that
would be present if C4 were violated. They do not establish C4.
"""
from __future__ import annotations

import json

import pytest

from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
T3_PATH = "/customers/12345/preferences/communication"
T4_PATH = "/payments"
KONG_CUSTODY = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}
APISIX_CUSTODY_CFG = {"url": APISIX_CUSTODY_INTERNAL, "timeout_ms": 200}


def _body(raw: bytes) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def _pending(custody_base: str) -> list[dict]:
    status, raw, _ = http("GET", custody_base + "/v1/pending")
    assert status == 200, raw
    return json.loads(raw.decode("utf-8")).get("pending") or []


def _load(stack, *, target: str, custody: dict | None) -> None:
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target=target, custody=custody)
    stack.load_generated(files)


def _assert_withhold_has_no_pollurl(status: int, raw: bytes, hdrs: dict[str, str]) -> dict:
    body = _body(raw)
    assert status == 202, body
    assert "pollUrl" not in body
    assert not any(k.lower() == "pollurl" for k in hdrs)
    assert body.get("status") == "pending_authorization"
    return body


def _assert_l2_t3_is_refuse_not_wait(status: int, raw: bytes, hdrs: dict[str, str]) -> dict:
    body = _body(raw)
    # The decision, not only the status: an unavailable durable path
    # completed as refuse-provisioning. It did not become a wait.
    assert status == 403, body
    assert body.get("status") == "provisioning_defect", body
    assert body.get("retryable") is False
    assert body.get("agentAction") == "continue_task_without_this_step"
    assert "pollUrl" not in body
    assert body.get("status") != "pending_authorization"
    assert body.get("status") != "custody_unavailable"
    assert status != 202
    assert status != 503
    assert "retry-after" not in {k.lower() for k in hdrs}
    return body


def _assert_t4_completes_nothing_holding(
    status: int, raw: bytes, custody_base: str,
) -> dict:
    body = _body(raw)
    assert status == 423, body
    assert body.get("agentAction") == "halt_and_hand_off"
    assert body.get("status") == "agent_suspended"
    assert "pollUrl" not in body
    cid = body.get("correlationId")
    pending = _pending(custody_base)
    if cid:
        held = [p for p in pending if p.get("correlationId") == cid]
        assert not held, held
    return body


def test_kong_withhold_has_no_pollurl(kong_stack):
    _load(kong_stack, target="kong", custody=KONG_CUSTODY)
    status, raw, hdrs = kong_stack.request(
        "PUT",
        T3_PATH,
        headers=kong_stack.auth_headers(
            **{"X-Agent-Id": "agent-c4-k1", "X-Task-Id": "task-c4-k1"},
        ),
    )
    _assert_withhold_has_no_pollurl(status, raw, hdrs)


def test_apisix_withhold_has_no_pollurl(apisix_stack):
    _load(apisix_stack, target="apisix", custody=APISIX_CUSTODY_CFG)
    status, raw, hdrs = apisix_stack.request(
        "PUT",
        T3_PATH,
        headers=apisix_stack.auth_headers(
            **{"X-Agent-Id": "agent-c4-a1", "X-Task-Id": "task-c4-a1"},
        ),
    )
    _assert_withhold_has_no_pollurl(status, raw, hdrs)


def test_kong_l2_t3_unavailable_durable_path_is_refuse_not_wait(kong_stack):
    _load(kong_stack, target="kong", custody=None)
    try:
        kong_stack.stop_service("custody")
        status, raw, hdrs = kong_stack.request(
            "PUT",
            T3_PATH,
            headers=kong_stack.auth_headers(
                **{"X-Agent-Id": "agent-c4-k2", "X-Task-Id": "task-c4-k2"},
            ),
        )
        _assert_l2_t3_is_refuse_not_wait(status, raw, hdrs)
    finally:
        kong_stack.start_service("custody")


def test_apisix_l2_t3_unavailable_durable_path_is_refuse_not_wait(apisix_stack):
    _load(apisix_stack, target="apisix", custody=None)
    try:
        apisix_stack.stop_service("custody")
        status, raw, hdrs = apisix_stack.request(
            "PUT",
            T3_PATH,
            headers=apisix_stack.auth_headers(
                **{"X-Agent-Id": "agent-c4-a2", "X-Task-Id": "task-c4-a2"},
            ),
        )
        _assert_l2_t3_is_refuse_not_wait(status, raw, hdrs)
    finally:
        apisix_stack.start_service("custody")


def test_kong_t4_completes_nothing_holding_for_approver(kong_stack):
    _load(kong_stack, target="kong", custody=KONG_CUSTODY)
    status, raw, _ = kong_stack.request(
        "POST",
        T4_PATH,
        headers=kong_stack.auth_headers(
            **{"X-Agent-Id": "agent-c4-k3", "X-Task-Id": "task-c4-k3"},
        ),
        body="{}",
    )
    _assert_t4_completes_nothing_holding(status, raw, CUSTODY)


def test_apisix_t4_completes_nothing_holding_for_approver(apisix_stack):
    _load(apisix_stack, target="apisix", custody=APISIX_CUSTODY_CFG)
    status, raw, _ = apisix_stack.request(
        "POST",
        T4_PATH,
        headers=apisix_stack.auth_headers(
            **{"X-Agent-Id": "agent-c4-a3", "X-Task-Id": "task-c4-a3"},
        ),
        body="{}",
    )
    _assert_t4_completes_nothing_holding(status, raw, APISIX_CUSTODY)
