# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Adapter interface. Implementations observe a decision; they do not declare one."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..classifier import Classifier
from ..models import Disposition
from .resolve import request_from_case, resolve_operation

CORPUS_DISPOSITION = {
    Disposition.EXECUTE: "execute",
    Disposition.WITHHOLD: "withhold",
    Disposition.REFUSE_AND_SUSPEND: "refuse-and-suspend",
    Disposition.REFUSE_PROVISIONING: "refuse-provisioning",
}

DEPLOYMENTS = ("level-2", "level-3")


@dataclass
class ObservedDecision:
    applied_tier: Optional[int]
    disposition: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "appliedTier": self.applied_tier,
            "disposition": self.disposition,
            "evidence": self.evidence,
        }


class Adapter(ABC):
    name: str

    @abstractmethod
    def run(self, case: dict) -> ObservedDecision:
        ...


def classified_applied_tier(qualified_spec, case: dict) -> Optional[int]:
    """Classification only. Used when an observation (403) does not carry a tier."""
    op = resolve_operation(qualified_spec, case["request"])
    if op is None:
        return 4
    decision = Classifier().classify(op, request_from_case(case))
    return int(decision.applied_tier)


class ReferenceAdapter(Adapter):
    """Oracle for classification. Disposition is projected from the run's level.

    Classifier.classify maps Tier 3 to WITHHOLD unconditionally: Level 3 by
    construction. The classifier decides what the operation is; the deployment
    decides what happens to it. This adapter applies that projection at the
    edge. It does not change the classifier.
    """

    name = "reference"

    def __init__(self, qualified_spec, deployment: str = "level-2"):
        if deployment not in DEPLOYMENTS:
            raise ValueError(f"unsupported deployment {deployment!r}")
        self.qualified_spec = qualified_spec
        self.deployment = deployment

    def run(self, case: dict) -> ObservedDecision:
        op = resolve_operation(self.qualified_spec, case["request"])
        req = request_from_case(case)
        decision = Classifier().classify(op, req)
        evidence: dict[str, Any] = {
            "operationAnchor": decision.operation_anchor,
            "escalationReason": decision.escalation_reason.value,
            "deployment": self.deployment,
        }
        if decision.declared_tier is not None:
            evidence["declaredTier"] = int(decision.declared_tier)
        if decision.notes:
            evidence["notes"] = decision.notes
        return ObservedDecision(
            applied_tier=int(decision.applied_tier),
            disposition=self._project_disposition(decision),
            evidence=evidence,
        )

    def _project_disposition(self, decision) -> str:
        # Exclusion is applied_tier 4 + REFUSE_PROVISIONING. Projecting from
        # tier alone would collapse it onto refuse-and-suspend.
        if decision.disposition is Disposition.REFUSE_PROVISIONING:
            return "refuse-provisioning"
        tier = int(decision.applied_tier)
        if tier in (1, 2):
            return "execute"
        if tier == 3:
            if self.deployment == "level-2":
                return "refuse-provisioning"
            return "withhold"
        return "refuse-and-suspend"
