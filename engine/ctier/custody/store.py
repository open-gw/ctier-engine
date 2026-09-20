# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""SQLite store for pending withheld operations.

SQLite is v1-only. A durable store is post-v1 (solution design). Do not treat
this file as a commitment to SQLite beyond that.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Optional

from ..ledger.store import Ledger

# Rows written before the deployment digest carry a composition digest in
# `digest`. The two are incomparable; `digest_schema` is the marker.
DIGEST_SCHEMA_COMPOSITION = "composition"
DIGEST_SCHEMA_DEPLOYMENT = "deploymentDigest"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pending (
  correlation_id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  query_json TEXT NOT NULL,
  body TEXT,
  headers_json TEXT NOT NULL,
  operation_anchor TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  task_id TEXT,
  correlation_scope TEXT NOT NULL,
  declared_tier INTEGER,
  applied_tier INTEGER NOT NULL,
  digest TEXT NOT NULL,
  digest_schema TEXT NOT NULL,
  authority TEXT,
  credential_exp INTEGER,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  approver_id TEXT,
  decided_at TEXT,
  decision TEXT,
  outcome_status INTEGER,
  outcome_body TEXT,
  executed_at TEXT,
  failure_reason TEXT
);
"""

# Added after withhold-only. Existing sqlite files (live compose volumes)
# get them via ALTER rather than a wipe.
_DECISION_COLUMNS = (
    ("approver_id", "TEXT"),
    ("decided_at", "TEXT"),
    ("decision", "TEXT"),
    ("outcome_status", "INTEGER"),
    ("outcome_body", "TEXT"),
    ("executed_at", "TEXT"),
    ("failure_reason", "TEXT"),
)

# Nothing that authenticates. Not names that merely sound sensitive — these
# are the headers that *are* a credential or a session.
CREDENTIAL_HEADERS = frozenset({
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
})


def strip_credentials(headers: dict[str, str] | None) -> dict[str, str]:
    """Drop credential headers. Does not parse or hash them."""
    out = {}
    for key, value in (headers or {}).items():
        if str(key).lower() in CREDENTIAL_HEADERS:
            continue
        out[str(key)] = str(value)
    return out


def row_contains_credential(row: dict[str, Any], secret: str) -> bool:
    """True if any stored field carries the credential material."""
    blob = json.dumps(row, default=str)
    return secret in blob


class Store:
    def __init__(self, path: str = ":memory:"):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._ensure_decision_columns()
        self.digest_backfill_count = self._migrate_digest_column()
        self._conn.commit()
        self.ledger = Ledger(self._conn, self._lock, path=path)

    def _column_names(self) -> set[str]:
        return {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(pending)").fetchall()
        }

    def _ensure_decision_columns(self) -> None:
        have = self._column_names()
        for name, typ in _DECISION_COLUMNS:
            if name not in have:
                self._conn.execute(f"ALTER TABLE pending ADD COLUMN {name} {typ}")

    def _migrate_digest_column(self) -> int:
        """Backfill every existing row as the old digest. Do not convert values.

        Every row already in the store was written before this change, so all
        of them carry a composition digest by construction. Inspecting the
        hex cannot tell the two objects apart.
        """
        have = self._column_names()
        if "digest" in have and "digest_schema" in have:
            return 0
        if "composition" not in have:
            return 0
        n = int(self._conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0])
        self._conn.execute("ALTER TABLE pending RENAME TO pending_pre_digest")
        self._conn.executescript(SCHEMA)
        self._conn.execute(
            """
            INSERT INTO pending (
              correlation_id, idempotency_key, status, method, path,
              query_json, body, headers_json, operation_anchor,
              agent_id, task_id, correlation_scope, declared_tier,
              applied_tier, digest, digest_schema, authority, credential_exp,
              expires_at, created_at,
              approver_id, decided_at, decision,
              outcome_status, outcome_body, executed_at, failure_reason
            )
            SELECT
              correlation_id, idempotency_key, status, method, path,
              query_json, body, headers_json, operation_anchor,
              agent_id, task_id, correlation_scope, declared_tier,
              applied_tier, composition, ?, authority, credential_exp,
              expires_at, created_at,
              approver_id, decided_at, decision,
              outcome_status, outcome_body, executed_at, failure_reason
            FROM pending_pre_digest
            """,
            (DIGEST_SCHEMA_COMPOSITION,),
        )
        self._conn.execute("DROP TABLE pending_pre_digest")
        return n

    def close(self) -> None:
        self._conn.close()

    def get_by_idempotency(self, key: str) -> Optional[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM pending WHERE idempotency_key = ?",
                (key,),
            )
            found = cur.fetchone()
        return dict(found) if found else None

    def get(self, correlation_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM pending WHERE correlation_id = ?",
                (correlation_id,),
            )
            found = cur.fetchone()
        return dict(found) if found else None

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        cols = (
            "correlation_id", "idempotency_key", "status", "method", "path",
            "query_json", "body", "headers_json", "operation_anchor",
            "agent_id", "task_id", "correlation_scope", "declared_tier",
            "applied_tier", "digest", "digest_schema", "authority",
            "credential_exp",
            "expires_at", "created_at",
            "approver_id", "decided_at", "decision",
            "outcome_status", "outcome_body", "executed_at", "failure_reason",
        )
        values = tuple(row.get(c) for c in cols)
        placeholders = ", ".join("?" for _ in cols)
        with self._lock:
            self._conn.execute(
                f"INSERT INTO pending ({', '.join(cols)}) VALUES ({placeholders})",
                values,
            )
            self._conn.commit()
        return row

    def list_pending(self) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM pending WHERE status = 'pending' "
                "ORDER BY created_at ASC, correlation_id ASC"
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM pending")
            n = cur.fetchone()[0]
        return int(n)

    def update_if_status(
        self,
        correlation_id: str,
        expected_status: str,
        fields: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Claim a row only if it is still in expected_status. None if not."""
        if not fields:
            raise ValueError("fields required")
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values()) + [correlation_id, expected_status]
        with self._lock:
            cur = self._conn.execute(
                f"UPDATE pending SET {assignments} "
                "WHERE correlation_id = ? AND status = ?",
                values,
            )
            self._conn.commit()
            if cur.rowcount != 1:
                return None
            found = self._conn.execute(
                "SELECT * FROM pending WHERE correlation_id = ?",
                (correlation_id,),
            ).fetchone()
        return dict(found) if found else None

    def save(self, correlation_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values()) + [correlation_id]
        with self._lock:
            self._conn.execute(
                f"UPDATE pending SET {assignments} WHERE correlation_id = ?",
                values,
            )
            self._conn.commit()
            found = self._conn.execute(
                "SELECT * FROM pending WHERE correlation_id = ?",
                (correlation_id,),
            ).fetchone()
        if found is None:
            raise KeyError(correlation_id)
        return dict(found)
