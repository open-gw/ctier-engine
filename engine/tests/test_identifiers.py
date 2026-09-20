"""Closed response identifiers. Spec 1.24.0. Propose; do not mint."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from ctier.compose import compose
from ctier.generate import generate
from ctier.identifiers import (
    ACTION_CONTINUE,
    ACTION_HALT,
    ACTION_HALT_AND_HAND_OFF,
    ACTION_RETRY_LATER,
    AGENT_ACTIONS,
    AGENT_SUSPENDED_BODY,
    CUSTODY_UNAVAILABLE_BODY,
    HEADER_AGENT_ACTION,
    PROVISIONING_DEFECT_BODY,
    STATUS_AGENT_SUSPENDED,
    STATUS_CUSTODY_UNAVAILABLE,
    STATUS_PENDING_AUTHORIZATION,
    STATUS_PROVISIONING_DEFECT,
    STATUS_UNASSIGNED,
    STATUS_UNAUTHORIZED,
    STATUSES,
    UNASSIGNED_BODY,
    UNAUTHORIZED_BODY,
    required_instruction_headers,
    required_instruction_headers_for,
)
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_generate import _declared, _spec

REPO = Path(__file__).resolve().parents[2]
HANDLER_LUA = REPO / "targets" / "kong" / "plugin" / "handler.lua"


def test_closed_sets_are_the_1_24_0_list():
    assert STATUSES == {
        STATUS_PENDING_AUTHORIZATION,
        STATUS_AGENT_SUSPENDED,
        STATUS_CUSTODY_UNAVAILABLE,
        STATUS_UNASSIGNED,
        STATUS_UNAUTHORIZED,
        STATUS_PROVISIONING_DEFECT,
    }
    assert AGENT_ACTIONS == {
        ACTION_CONTINUE,
        ACTION_HALT_AND_HAND_OFF,
        ACTION_RETRY_LATER,
        ACTION_HALT,
    }


def test_bodies_carry_only_listed_identifiers():
    for raw in (
        AGENT_SUSPENDED_BODY,
        UNASSIGNED_BODY,
        PROVISIONING_DEFECT_BODY,
        CUSTODY_UNAVAILABLE_BODY,
        UNAUTHORIZED_BODY,
    ):
        body = json.loads(raw)
        assert body["status"] in STATUSES
        assert body["agentAction"] in AGENT_ACTIONS


def test_provisioning_defect_matches_specified_definition():
    """L2 cannot withhold T3; excluded reached live; not C2, not C12's miss."""
    from ctier.generate import _outcome

    l2_t3 = _outcome(3, False, None)
    assert l2_t3 == ("abort", 403, PROVISIONING_DEFECT_BODY)
    withheld = _outcome(3, False, {"url": "http://custody.example", "timeout_ms": 200})
    assert withheld[0] == "withhold"
    excluded = _outcome(1, True, None)
    assert excluded == ("abort", 403, PROVISIONING_DEFECT_BODY)
    t4 = _outcome(4, False, None)
    assert t4 == ("abort", 423, AGENT_SUSPENDED_BODY)
    body = json.loads(PROVISIONING_DEFECT_BODY)
    assert body["status"] == STATUS_PROVISIONING_DEFECT
    assert body["agentAction"] == ACTION_CONTINUE
    assert body["retryable"] is False


def test_c2_composed_unassigned_is_not_provisioning_defect():
    raw = _spec({
        "/ping": {"get": _declared(1, "ping")},
        "/gap": {"post": {"operationId": "gap", "responses": {"200": {"description": "x"}}}},
    })
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="apisix")
    catch = next(
        r for r in yaml.safe_load(files["apisix.yaml"])["routes"]
        if r["name"] == "undeclared"
    )
    joined = "\n".join(catch["plugins"]["serverless-post-function"]["functions"])
    assert ACTION_HALT_AND_HAND_OFF in joined
    assert STATUS_UNASSIGNED in joined
    assert STATUS_PROVISIONING_DEFECT not in joined


def test_named_mechanisms_require_the_mirror_header():
    assert required_instruction_headers(202, ACTION_CONTINUE) == {
        HEADER_AGENT_ACTION: ACTION_CONTINUE,
    }
    assert required_instruction_headers(423, ACTION_HALT_AND_HAND_OFF) == {
        HEADER_AGENT_ACTION: ACTION_HALT_AND_HAND_OFF,
    }
    assert required_instruction_headers(423, ACTION_HALT) == {}
    assert required_instruction_headers(403, ACTION_CONTINUE) == {}
    assert required_instruction_headers(503, ACTION_RETRY_LATER) == {}
    assert required_instruction_headers(401, ACTION_HALT) == {}
    assert required_instruction_headers_for(423, AGENT_SUSPENDED_BODY) == {
        HEADER_AGENT_ACTION: ACTION_HALT_AND_HAND_OFF,
    }
    assert required_instruction_headers_for(423, UNASSIGNED_BODY) == {}
    assert required_instruction_headers_for(403, PROVISIONING_DEFECT_BODY) == {}


def test_kong_plugin_bodies_use_the_closed_set():
    text = HANDLER_LUA.read_text(encoding="utf-8")
    compact = re.sub(r"'\s*\.\.\s*'", "", text)
    compact = compact.replace("\n", "")
    for raw in (
        AGENT_SUSPENDED_BODY,
        UNASSIGNED_BODY,
        PROVISIONING_DEFECT_BODY,
        CUSTODY_UNAVAILABLE_BODY,
        UNAUTHORIZED_BODY,
    ):
        assert raw in compact, raw
        body = json.loads(raw)
        assert body["status"] in STATUSES
        assert body["agentAction"] in AGENT_ACTIONS
    assert '["X-Agent-Action"] = "halt_and_hand_off"' in text
    assert '["X-Agent-Action"] = "continue_task_without_this_step"' in text


def test_generate_emits_bodies_from_the_definition():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    apisix = generate(qualified, target="apisix")["apisix.yaml"]
    apigee = generate(qualified)
    assert "agent_suspended" in apisix
    assert "halt_and_hand_off" in apisix
    assert AGENT_SUSPENDED_BODY in apigee["apiproxy/policies/RF-Tier4.xml"]
    assert PROVISIONING_DEFECT_BODY in apigee["apiproxy/policies/RF-Provisioning.xml"]
    t4 = next(
        r for r in yaml.safe_load(apisix)["routes"] if r["name"] == "initiatePayment"
    )
    post = "\n".join(t4["plugins"]["serverless-post-function"]["functions"])
    assert "agent_suspended" in post
    assert f'["{HEADER_AGENT_ACTION}"] = "{ACTION_HALT_AND_HAND_OFF}"' in post
    assert "refuse-and-suspend" in post
    assert "[ctier-decision]" in post
    prov = next(
        r
        for r in yaml.safe_load(apisix)["routes"]
        if r["name"] == "updateCommunicationPreferences"
    )
    prov_post = "\n".join(prov["plugins"]["serverless-post-function"]["functions"])
    assert "refuse-provisioning" in prov_post
    assert "[ctier-decision]" in prov_post
    assert "halt_and_hand_off" not in prov_post
    assert CUSTODY_UNAVAILABLE_BODY in generate(
        qualified, custody={"url": "http://custody.example:8080", "timeout_ms": 200},
    )["apiproxy/policies/RF-CustodyUnavailable.xml"]
