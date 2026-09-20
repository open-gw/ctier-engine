# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Semantic recommendation backend. The only shipped implementation proposes nothing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OperationView:
    operation_id: str | None
    method: str
    path: str
    summary: str | None
    description: str | None
    tags: tuple[str, ...]
    property_names: tuple[str, ...]


@dataclass(frozen=True)
class BackendProposal:
    criteria: dict[str, str]
    confidence: str
    rationale: str
    tier: int | None = None


class RecommendationBackend(Protocol):
    """Given visible operation text, propose criteria — or nothing."""

    def propose(self, view: OperationView) -> BackendProposal | None:
        ...

    def source(self) -> str:
        ...

    def version(self) -> str:
        ...


class NullBackend:
    """Proposes nothing. Level 0 stays offline and deterministic."""

    def propose(self, view: OperationView) -> BackendProposal | None:
        return None

    def source(self) -> str:
        return "null"

    def version(self) -> str:
        return "0"
