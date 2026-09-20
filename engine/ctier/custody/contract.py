# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""The 202 PendingAuthorization contract. Built here, relayed by gateways.

One implementation, not one per target — the same reasoning as compiling the
decision rather than the declaration, applied to the response.
"""
from __future__ import annotations

from typing import Any, Optional

from ctier.identifiers import ACTION_CONTINUE, HEADER_AGENT_ACTION, STATUS_PENDING_AUTHORIZATION

STATUS = STATUS_PENDING_AUTHORIZATION
AGENT_ACTION = ACTION_CONTINUE
USER_MESSAGE = (
    "That's submitted and pending a quick review — you'll have confirmation shortly."
)

# C5: terminal, non-retryable. Retry-After is absent by construction.
RELAY_HEADER_NAMES = (
    "Content-Type",
    "Cache-Control",
    HEADER_AGENT_ACTION,
    "x-ctier-correlation-id",
    "X-Ctier-Tier",
)


def pending_authorization(
    *,
    correlation_id: str,
    classified_tier: int,
    expires_at: str,
    authority: Optional[str] = None,
) -> dict[str, Any]:
    """Complete body the enforcement point should emit. No pollUrl.

    C5 requires retryable false and an agentAction that means stop-and-report,
    not retry and not poll. The published const is continue_task_without_this_step:
    continue the rest of the task; do not resubmit this step. pollUrl is in the
    example schema as optional; emitting it would invite polling, so it is omitted.
    authority is the x-ctier-handoff class; C5 does not mention it, the 202 row
    of the solution design does.
    """
    body: dict[str, Any] = {
        "status": STATUS,
        "correlationId": correlation_id,
        "classifiedTier": classified_tier,
        "expiresAt": expires_at,
        "retryable": False,
        "agentAction": AGENT_ACTION,
        "userMessage": USER_MESSAGE,
    }
    if authority:
        body["authority"] = authority
    return body


def relay_headers(*, correlation_id: str, classified_tier: int) -> dict[str, str]:
    """Headers that accompany the 202. Retry-After is not among them."""
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        HEADER_AGENT_ACTION: AGENT_ACTION,
        "x-ctier-correlation-id": correlation_id,
        "X-Ctier-Tier": str(classified_tier),
    }
