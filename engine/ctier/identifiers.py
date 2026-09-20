# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Closed response-identifier sets. Spec 1.24.0.

An implementation MUST NOT emit a `status` or `agentAction` this
specification does not list. When it needs a condition the set does
not cover, it proposes. It does not mint.

These are the tokens a client can observe. They are not ledger
dispositions. Propose a new token; do not add one here because a
path needed a string.
"""
from __future__ import annotations

import json

# --- status -----------------------------------------------------------------

STATUS_PENDING_AUTHORIZATION = "pending_authorization"
STATUS_AGENT_SUSPENDED = "agent_suspended"
STATUS_CUSTODY_UNAVAILABLE = "custody_unavailable"
STATUS_UNASSIGNED = "unassigned"
STATUS_UNAUTHORIZED = "unauthorized"
STATUS_PROVISIONING_DEFECT = "provisioning_defect"

STATUSES = frozenset({
    STATUS_PENDING_AUTHORIZATION,
    STATUS_AGENT_SUSPENDED,
    STATUS_CUSTODY_UNAVAILABLE,
    STATUS_UNASSIGNED,
    STATUS_UNAUTHORIZED,
    STATUS_PROVISIONING_DEFECT,
})

# --- agentAction ------------------------------------------------------------

ACTION_CONTINUE = "continue_task_without_this_step"
ACTION_HALT_AND_HAND_OFF = "halt_and_hand_off"
ACTION_RETRY_LATER = "retry_later"
ACTION_HALT = "halt"

AGENT_ACTIONS = frozenset({
    ACTION_CONTINUE,
    ACTION_HALT_AND_HAND_OFF,
    ACTION_RETRY_LATER,
    ACTION_HALT,
})

HEADER_AGENT_ACTION = "X-Agent-Action"


def dumps(obj: dict) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)


def required_instruction_headers(http_status: int, agent_action: str) -> dict[str, str]:
    """C5's 202 and C9's 423 named mechanisms MUST emit the body instruction.

    Spec 1.24.0: the identifier is body `agentAction`, mirrored on
    `X-Agent-Action` when that header is emitted. headers.md: an
    implementation that satisfies C5 by the `202` mechanism MUST emit
    it on 202; one that satisfies C9 by the `423` mechanism MUST emit
    it on 423. This engine uses those mechanisms. Other dispositions
    may omit the header; when they emit it, the value is still this
    one.
    """
    if not isinstance(agent_action, str):
        return {}
    action = agent_action.strip()
    if action == "":
        return {}
    if http_status == 202:
        return {HEADER_AGENT_ACTION: action}
    if http_status == 423 and action == ACTION_HALT_AND_HAND_OFF:
        return {HEADER_AGENT_ACTION: action}
    return {}


def required_instruction_headers_for(http_status: int, body: str) -> dict[str, str]:
    try:
        obj = json.loads(body)
    except (TypeError, ValueError):
        return {}
    if not isinstance(obj, dict):
        return {}
    action = obj.get("agentAction")
    if not isinstance(action, str):
        return {}
    return required_instruction_headers(http_status, action)


# --- bodies the enforcement point constructs --------------------------------
#
# pending_authorization is built by custody, not here.

AGENT_SUSPENDED_BODY = dumps({
    "status": STATUS_AGENT_SUSPENDED,
    "humanTakeoverRequired": True,
    "autoResume": False,
    "agentAction": ACTION_HALT_AND_HAND_OFF,
})

UNASSIGNED_BODY = dumps({
    "status": STATUS_UNASSIGNED,
    "retryable": False,
    "autoResume": False,
    "agentAction": ACTION_HALT,
})

# A classified operation this deployment cannot enact. Emitted on 403
# when Tier 3 is reached at Level 2 (no custody, so no withhold), and
# when an excluded operation is reached by a live token. Not C12's
# English "provisioning defect" (that miss is `unassigned`). Not a
# withhold. Not a Tier 4 handover. Composed-but-unassigned without
# custody is still C2's Tier 4, not this token.
PROVISIONING_DEFECT_BODY = dumps({
    "status": STATUS_PROVISIONING_DEFECT,
    "retryable": False,
    "autoResume": False,
    "agentAction": ACTION_CONTINUE,
})

CUSTODY_UNAVAILABLE_BODY = dumps({
    "status": STATUS_CUSTODY_UNAVAILABLE,
    "retryable": True,
    "agentAction": ACTION_RETRY_LATER,
})

UNAUTHORIZED_BODY = dumps({
    "status": STATUS_UNAUTHORIZED,
    "agentAction": ACTION_HALT,
})
