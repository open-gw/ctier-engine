# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""record-source/0.1.0-draft — list records written by a running deployment.

The contract is one GET. Custody's ledger and the gateway log both
satisfy it; a runner must not require either specifically.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

DECISION_MARKER = "[ctier-decision] "
ATTEMPT_MARKER = "[ctier-attempt] "
MARKERS = (DECISION_MARKER, ATTEMPT_MARKER)
SINK_SEQ = re.compile(r"epoch=(\S+) seq=(\d+)")
SINK_ENVELOPE = ("sinkEpoch", "sinkSeq")


def parse_sink_meta(line: str) -> tuple[str | None, int | None]:
    match = SINK_SEQ.search(line)
    if not match:
        return None, None
    return match.group(1), int(match.group(2))


def parse_prefixed_line(line: str) -> dict[str, Any] | None:
    for marker in MARKERS:
        if marker not in line:
            continue
        payload = line.split(marker, 1)[1].strip()
        start = payload.find("{")
        end = payload.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            rec = json.loads(payload[start:end + 1])
        except json.JSONDecodeError:
            return None
        if not (isinstance(rec, dict) and rec.get("ctierSchema")):
            return None
        epoch, seq = parse_sink_meta(line)
        if epoch is not None and seq is not None:
            rec["sinkEpoch"] = epoch
            rec["sinkSeq"] = seq
        return rec
    return None


def detect_gaps(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A reader holding only the sink's contents.

    Per emitter (epoch). Missing integers between that epoch's min and
    max are gaps. A new epoch is a restart, not a hole. Ordering
    across emitters is not claimed.
    """
    groups: dict[str, set[int]] = {}
    for rec in records:
        epoch = rec.get("sinkEpoch")
        seq = rec.get("sinkSeq")
        if epoch is None or seq is None:
            continue
        groups.setdefault(str(epoch), set()).add(int(seq))
    gaps: list[dict[str, Any]] = []
    for epoch, seen in groups.items():
        lo, hi = min(seen), max(seen)
        for n in range(lo, hi + 1):
            if n not in seen:
                gaps.append({"sinkEpoch": epoch, "sinkSeq": n})
    return gaps


def records_from_log(text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    index: dict[str, int] = {}
    for line in text.splitlines():
        rec = parse_prefixed_line(line)
        if rec is None:
            continue
        rid = str(rec.get("id") or "")
        if rid and rid in index:
            prev = found[index[rid]]
            if rec.get("sinkSeq") is not None and prev.get("sinkSeq") is None:
                found[index[rid]] = rec
            continue
        if rid:
            index[rid] = len(found)
        found.append(rec)
    return found


def records_from_ledger_body(payload: dict[str, Any] | list) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    else:
        rows = payload.get("records") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def merge_records(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for rec in group:
            rid = str(rec.get("id") or "")
            if rid and rid in seen:
                continue
            if rid:
                seen.add(rid)
            merged.append(rec)
    return merged


def fetch_records(record_base: str, *, after: str | None = None, timeout: float = 5.0) -> list[dict[str, Any]]:
    """GET {recordBase}/records as specified. after is optional."""
    url = record_base.rstrip("/") + "/records"
    if after:
        url = url + "?after=" + after
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except URLError:
        return []
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    return records_from_ledger_body(payload)
