# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Custody: persist withheld operations; record the human decision against them.

SQLite is deliberate and v1-only. The solution design lists a durable store as
post-v1. This is not a decision that was never revisited.

v1 records the approver from `X-Approver-Id`. Production binds the decisions
endpoint to an identity provider; that header is not the intended mechanism.
"""
from .contract import pending_authorization, relay_headers
from .service import DecisionError, DecisionOut, PersistIn, PersistOut, decide, persist, review_queue
from .store import Store

__all__ = [
    "DecisionError",
    "DecisionOut",
    "PersistIn",
    "PersistOut",
    "Store",
    "decide",
    "pending_authorization",
    "persist",
    "relay_headers",
    "review_queue",
]
