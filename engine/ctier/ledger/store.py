# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Append-only ledger. Three tables. No UPDATE, no DELETE, no REPLACE.

Pending custody context is a different store: it mutates, because a withheld
operation is a live object. A ledger record is evidence of something that
already happened. Conflating them is the C8 error again.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Optional

from .records import (
    attempt_from_ingress,
    validate_record,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger_decision (
  id TEXT PRIMARY KEY,
  recorded_at TEXT NOT NULL,
  correlation_scope TEXT,
  correlation_id TEXT,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger_attempt (
  id TEXT PRIMARY KEY,
  recorded_at TEXT NOT NULL,
  correlation_scope TEXT,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger_outcome (
  id TEXT PRIMARY KEY,
  recorded_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  payload TEXT NOT NULL
);
"""

_TABLE = {
    "decision": "ledger_decision",
    "attempt": "ledger_attempt",
    "outcome": "ledger_outcome",
}


class Ledger:
    def __init__(
        self,
        conn: Optional[sqlite3.Connection] = None,
        lock: Optional[threading.Lock] = None,
        path: str = ":memory:",
    ):
        self.path = path
        self._owned_conn = conn is None
        if conn is None:
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
        self._conn = conn
        self._lock = lock or threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        if self._owned_conn:
            self._conn.close()

    def append_decision(self, record: dict[str, Any]) -> dict[str, Any]:
        validate_record(record)
        self._insert(
            "ledger_decision",
            record,
            extra={
                "correlation_scope": record.get("correlationScope"),
                "correlation_id": record.get("correlationId"),
            },
        )
        return record

    def append_attempt(
        self,
        record: dict[str, Any],
        *,
        ignore_duplicate: bool = False,
    ) -> dict[str, Any]:
        validate_record(record)
        self._insert(
            "ledger_attempt",
            record,
            extra={"correlation_scope": record.get("correlationScope")},
            ignore_duplicate=ignore_duplicate,
        )
        return record

    def append_outcome(self, record: dict[str, Any]) -> dict[str, Any]:
        validate_record(record)
        self._insert(
            "ledger_outcome",
            record,
            extra={"correlation_id": record["correlationId"]},
        )
        return record

    def _insert(
        self,
        table: str,
        record: dict[str, Any],
        extra: dict[str, Any],
        *,
        ignore_duplicate: bool = False,
    ) -> None:
        columns = ["id", "recorded_at", "payload", *extra]
        values = [
            record["id"],
            record["timestamp"],
            json.dumps(record, sort_keys=True, separators=(",", ":")),
            *extra.values(),
        ]
        placeholders = ", ".join("?" for _ in columns)
        verb = "INSERT OR IGNORE" if ignore_duplicate else "INSERT"
        with self._lock:
            self._conn.execute(
                f"{verb} INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
            self._conn.commit()

    def list_records(
        self,
        *,
        record_type: Optional[str] = None,
        correlation_scope: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        kinds = ("decision", "attempt", "outcome")
        if record_type is not None:
            if record_type not in _TABLE:
                raise ValueError(f"unknown ledger type {record_type!r}")
            kinds = (record_type,)

        by_kind: dict[str, list[dict[str, Any]]] = {k: [] for k in ("decision", "attempt", "outcome")}
        with self._lock:
            for kind in ("decision", "attempt", "outcome"):
                cur = self._conn.execute(
                    f"SELECT payload FROM {_TABLE[kind]} ORDER BY recorded_at ASC, id ASC"
                )
                by_kind[kind] = [json.loads(row[0]) for row in cur.fetchall()]

        decisions = by_kind["decision"]
        attempts = by_kind["attempt"]
        outcomes = by_kind["outcome"]
        if correlation_scope is not None:
            decisions = [
                d for d in decisions if d.get("correlationScope") == correlation_scope
            ]
            attempts = [
                a for a in attempts if a.get("correlationScope") == correlation_scope
            ]
            ids = {d.get("correlationId") for d in decisions if d.get("correlationId")}
            outcomes = [o for o in outcomes if o.get("correlationId") in ids]

        out: list[dict[str, Any]] = []
        if "decision" in kinds:
            out.extend({"type": "decision", **row} for row in decisions)
        if "attempt" in kinds:
            out.extend({"type": "attempt", **row} for row in attempts)
        if "outcome" in kinds:
            out.extend({"type": "outcome", **row} for row in outcomes)
        out.sort(key=lambda row: (row.get("timestamp") or "", row.get("id") or ""))
        return out

    def ingest_fallback(self, path: str) -> int:
        """Read Attempt lines written while this process was down. Best-effort.

        The enforcement point appends JSON lines when POST /v1/pending cannot
        reach us. We rename the file, ingest, and leave a fresh path for the
        next outage. If the sink that holds the file is down too, this window
        has no record; ADR-005 says so.
        """
        if not path or not os.path.isfile(path):
            return 0
        ingest_path = path + ".ingesting"
        try:
            os.rename(path, ingest_path)
        except FileNotFoundError:
            return 0
        except OSError:
            ingest_path = path
        n = 0
        try:
            with open(ingest_path, encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError:
            return 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            try:
                record = attempt_from_ingress(payload)
                self.append_attempt(record, ignore_duplicate=True)
            except Exception:
                continue
            n += 1
        if ingest_path != path:
            try:
                os.remove(ingest_path)
            except OSError:
                pass
        return n


def prepare_fallback(path: str) -> None:
    """Create a world-writable fallback file so Kong can append during an outage."""
    if not path:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
        try:
            os.chmod(directory, 0o777)
        except OSError:
            pass
    if not os.path.exists(path):
        with open(path, "a", encoding="utf-8"):
            pass
        try:
            os.chmod(path, 0o666)
        except OSError:
            pass


# Re-export constructors so callers import from one place.
__all__ = [
    "Ledger",
    "attempt_record",
    "decision_record",
    "outcome_record",
]
