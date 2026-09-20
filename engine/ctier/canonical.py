# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Canonical JSON for C13. Keys sorted, no insignificant whitespace, UTF-8, no newline."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(document: Any) -> bytes:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()
