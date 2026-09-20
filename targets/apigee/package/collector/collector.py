#!/usr/bin/env python3
"""Retrievable decision-record sink for Apigee kit runs.

Accepts POST /v1/ledger and serves GET /v1/ledger → { "records": [ … ] }.
This is not custody: no pending queue, no approve, no execute-from-store.
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8090"))
_LOCK = threading.Lock()
_RECORDS: list[dict] = []


def _is_decision(row: dict) -> bool:
    schema = str(row.get("ctierSchema") or "")
    if schema.startswith("decision-record/"):
        return True
    return str(row.get("type") or "") == "decision"


def _normalise(payload: dict) -> dict:
    """Accept either a full decision-record or a Kong-style ledger ingress."""
    if _is_decision(payload) and payload.get("ctierSchema"):
        return dict(payload)
    # Ingress shape (type + fields). Stamp the schema the kit looks for.
    out = dict(payload)
    out.setdefault("ctierSchema", "decision-record/0.2.0")
    out.setdefault("type", "decision")
    if "id" not in out and out.get("correlationId"):
        out["id"] = out["correlationId"]
    return out


class Collector(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/v1/ledger":
            with _LOCK:
                body = json.dumps({"records": list(_RECORDS)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/health", "/"):
            body = b'{"ok":true}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/v1/ledger":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400, "json required")
            return
        if not isinstance(payload, dict):
            self.send_error(400, "json object required")
            return
        kind = payload.get("type")
        schema = str(payload.get("ctierSchema") or "")
        if kind not in (None, "decision") and not schema.startswith("decision-record/"):
            if kind == "attempt":
                # Accept attempts for C12 soft checks; store as-is.
                row = dict(payload)
                row.setdefault("ctierSchema", "attempt-record/0.2.0")
                with _LOCK:
                    _RECORDS.append(row)
                body = json.dumps({"ok": True}).encode("utf-8")
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(400, "type must be decision or attempt")
            return
        row = _normalise(payload)
        with _LOCK:
            _RECORDS.append(row)
        body = json.dumps({"ok": True, "id": row.get("id")}).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    print(f"records collector on {HOST}:{PORT}", flush=True)
    print(f"kit_records → http://<reachable-host>:{PORT}/v1/ledger", flush=True)
    HTTPServer((HOST, PORT), Collector).serve_forever()
