# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Composition and validation errors. rule names the spec constraint."""
from __future__ import annotations


class ComposeError(ValueError):
    def __init__(self, rule: str, message: str):
        self.rule = rule
        super().__init__(message)


class RecommendError(ValueError):
    def __init__(self, rule: str, message: str):
        self.rule = rule
        super().__init__(message)


class GenerateError(ValueError):
    def __init__(self, rule: str, message: str, files: dict | None = None):
        self.rule = rule
        self.files = files or {}
        super().__init__(message)
