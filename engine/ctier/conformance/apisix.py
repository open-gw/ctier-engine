# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""APISIX adapter. Same observation projection as Kong; does not classify."""
from __future__ import annotations

from .kong import KongAdapter


class ApisixAdapter(KongAdapter):
    name = "apisix"
