# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Domain model for consequence-tiered governance.

Vocabulary follows the published specification at github.com/open-gw/ctier.
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Optional

from pydantic import BaseModel, Field


class Tier(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# Sentinel for operations agents are deliberately kept out of entirely.
# Not a tier: enforcement is the absence of the scope grant. Declaring it lets
# the engine distinguish a decision that was made from one that was missed, and
# gives it something to assert against when a token reaches the operation anyway.
EXCLUDED = "excluded"


class Reversibility(str, Enum):
    """Three meaningful states, not two.

    The middle one decides most Tier 2 / Tier 3 boundaries: a price can be put
    back, but the orders placed at the wrong price were still placed.
    """
    NOT_APPLICABLE = "not-applicable"          # read-only; nothing to undo
    RESTORES_EFFECT = "undo-restores-effect"   # nothing persists from the interval
    RESTORES_RECORD = "undo-restores-record-only"
    NONE = "none"


class BlastRadius(str, Enum):
    SINGLE_RECORD = "single-record"
    SINGLE_CUSTOMER = "single-customer"
    POPULATION = "population"
    SYSTEM_WIDE = "system-wide"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    REGULATED = "regulated"


class ComplianceTrigger(str, Enum):
    NONE = "none"
    ADJACENT = "adjacent"
    DIRECT = "direct"


class Idempotency(str, Enum):
    INHERENTLY_SAFE = "inherently-safe"
    SAFE = "safe"
    KEY_REQUIRED = "key-required"
    UNSAFE = "unsafe"


class Criteria(BaseModel):
    reversibility: Reversibility = Reversibility.NONE
    blast_radius: BlastRadius = Field(BlastRadius.SINGLE_RECORD, alias="blast-radius")
    data_sensitivity: Sensitivity = Field(Sensitivity.REGULATED, alias="data-sensitivity")
    compliance_trigger: ComplianceTrigger = Field(ComplianceTrigger.NONE, alias="compliance-trigger")
    idempotency: Idempotency = Idempotency.UNSAFE

    model_config = {"populate_by_name": True}


class EscalationReason(str, Enum):
    NONE = "none"
    SESSION_ACCUMULATION = "session-accumulation"
    DELEGATION_EXPANSION = "delegation-authority-expansion"
    PAYLOAD_EXCEEDS_BOUNDS = "payload-exceeds-declared-bounds"
    COMPUTED_EXCEEDS_DECLARED = "computed-tier-exceeds-declared"
    UNDECLARED = "undeclared-operation"


class Disposition(str, Enum):
    """What the enforcement point should do with the operation."""
    EXECUTE = "execute"                 # tier 1, 2
    WITHHOLD = "withhold"               # tier 3 — persist, emit, return 202
    REFUSE_AND_SUSPEND = "refuse"       # tier 4 — return 423
    REFUSE_PROVISIONING = "refuse-provisioning"  # excluded operation reached by a live token


class Operation(BaseModel):
    """A declared operation resolved from an interface description document."""
    operation_id: Optional[str] = None
    method: str
    path_template: str
    declared_tier: Optional[Tier] = None
    excluded: bool = False
    criteria: Optional[Criteria] = None
    rationale: Optional[str] = None
    # per-operation accumulation override
    contributes_weight: Optional[int] = None
    escalate_if_repeated: bool = False
    escalate_to: Optional[Tier] = None
    # declared bounds the request must stay within to keep the declared tier
    max_result_bound: Optional[int] = None
    bound_parameter: Optional[str] = None

    def anchor(self) -> str:
        """Stable identifier for idempotency derivation.

        The declared operationId is preferred because it survives restructuring
        of the path; method + template is the fallback where none is declared.
        """
        return self.operation_id or f"{self.method.upper()} {self.path_template}"


class DelegationHop(BaseModel):
    agent_id: str
    scopes: list[str] = []
    blast_radius: BlastRadius = BlastRadius.SINGLE_RECORD
    data_sensitivity: Sensitivity = Sensitivity.PUBLIC


class Request(BaseModel):
    """An intercepted operation awaiting classification."""
    method: str
    path: str
    query: dict[str, str] = {}
    headers: dict[str, str] = {}
    body: Optional[str] = None
    agent_id: str
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    delegation_chain: list[DelegationHop] = []

    def correlation_scope(self) -> str:
        return self.task_id or self.session_id or self.agent_id


class Decision(BaseModel):
    """A governance decision. The record is evidence that it was made (C10)."""
    correlation_id: str
    operation_anchor: str
    declared_tier: Optional[Tier]
    applied_tier: Tier
    escalation_reason: EscalationReason = EscalationReason.NONE
    disposition: Disposition
    criteria: Optional[Criteria] = None
    agent_id: str
    delegation_chain: list[str] = []
    correlation_scope: str
    idempotency_key: str
    accumulated_weight: int = 0
    timestamp: str
    notes: Optional[str] = None

    @property
    def escalated(self) -> bool:
        return self.escalation_reason is not EscalationReason.NONE
