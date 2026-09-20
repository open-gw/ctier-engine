# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Rebuild the withheld request and execute it as the policy service.

Byte-identity (C6, spec 1.1.7) covers method, request target, query and body.
It does not extend to the credential. The agent is not involved and is not asked.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .store import CREDENTIAL_HEADERS


# Names custody used to put on the execute request. Removed for cause in
# 14a, not deprecated. Task 17 Check 1: custody calls CTIER_BACKEND_URL
# directly, so these never met C11's strip set. A dual-emit window would
# have kept a forgery path open and called it courtesy.
HEADER_AGENT = "x-ctier-agent"
HEADER_APPROVER = "x-ctier-approver"
HEADER_CORRELATION = "x-ctier-correlation-id"
HEADER_IDEMPOTENCY = "Idempotency-Key"


@dataclass
class OutboundRequest:
    method: str
    path: str
    query: dict[str, str]
    body: Optional[str]
    headers: dict[str, str]


@dataclass
class ExecuteResult:
    status_code: Optional[int]
    body: str
    headers: dict[str, str] = field(default_factory=dict)
    reached: bool = True


class Executor(Protocol):
    def execute(self, request: OutboundRequest) -> ExecuteResult:
        ...


def build_outbound(
    row: dict[str, Any],
    *,
    approver: str,
    service_token: str = "",
) -> OutboundRequest:
    """Method, target, query, body from the store. Service identity, not the agent's."""
    stored = {}
    parsed = json.loads(row.get("headers_json") or "{}")
    for key, value in parsed.items():
        if str(key).lower() in CREDENTIAL_HEADERS:
            continue
        stored[str(key)] = str(value)

    headers = dict(stored)
    # Agent and approver live on the decision record. The request carries
    # the correlation id so a backend can join them. Identity in a header
    # is either authenticated or it is a suggestion; authenticating it
    # would put a token on this path, which is the hole provenance-not-
    # authorisation exists to prevent. `approver` is recorded on the row,
    # not on the wire.
    _ = approver
    drop = {HEADER_AGENT, HEADER_APPROVER, "idempotency-key", "x-idempotency-key"}
    headers = {
        key: value
        for key, value in headers.items()
        if str(key).lower() not in drop
    }
    headers[HEADER_CORRELATION] = str(row["correlation_id"])
    headers[HEADER_IDEMPOTENCY] = str(row["idempotency_key"])
    if service_token:
        headers["Authorization"] = f"Bearer {service_token}"
    else:
        headers.pop("Authorization", None)
        headers.pop("authorization", None)

    query = parsed_query(row)
    return OutboundRequest(
        method=str(row["method"]).upper(),
        path=str(row["path"]),
        query=query,
        body=row.get("body"),
        headers=headers,
    )


def parsed_query(row: dict[str, Any]) -> dict[str, str]:
    return {str(k): str(v) for k, v in json.loads(row.get("query_json") or "{}").items()}


@dataclass
class RecordingExecutor:
    """Offline stand-in. Never opens a socket."""

    calls: list[OutboundRequest] = field(default_factory=list)
    results: list[ExecuteResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.results:
            self.results = [ExecuteResult(status_code=200, body='{"ok":true}', reached=True)]

    def execute(self, request: OutboundRequest) -> ExecuteResult:
        self.calls.append(request)
        if not self.results:
            raise AssertionError("unexpected execute")
        return self.results.pop(0)


class HttpExecutor:
    """POST the rebuilt request at the backend. Used by the serve process."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def execute(self, request: OutboundRequest) -> ExecuteResult:
        url = self.base_url + request.path
        if request.query:
            url = url + "?" + urlencode(request.query)
        data = None if request.body is None else request.body.encode("utf-8")
        req = Request(url, data=data, method=request.method.upper())
        for key, value in request.headers.items():
            req.add_header(key, value)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                return ExecuteResult(
                    status_code=resp.status,
                    body=raw.decode("utf-8", "replace"),
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    reached=True,
                )
        except HTTPError as exc:
            raw = exc.read()
            return ExecuteResult(
                status_code=exc.code,
                body=raw.decode("utf-8", "replace"),
                headers={k.lower(): v for k, v in exc.headers.items()},
                reached=True,
            )
        except URLError as exc:
            return ExecuteResult(
                status_code=None,
                body=str(getattr(exc, "reason", exc)),
                headers={},
                reached=False,
            )
