# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Kong adapter. Observes a running proxy; does not classify."""
from __future__ import annotations

import json
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .adapter import Adapter, ObservedDecision, classified_applied_tier


def identity_headers(case: dict, headers: dict | None = None) -> dict[str, str]:
    """Agent and correlation scope for the enforcement point.

    Prefer case.scope, then case.id. Sharing a default taskId across
    single-request cases would make accumulation look global.
    """
    out = {str(k): str(v) for k, v in (headers or {}).items()}
    lower = {k.lower() for k in out}
    agent = case.get("agent") or {}
    if "x-agent-id" not in lower and agent.get("id"):
        out["X-Agent-Id"] = str(agent["id"])
    if "x-task-id" not in lower:
        scope = case.get("scope") or case.get("id") or agent.get("taskId")
        if scope:
            out["X-Task-Id"] = str(scope)
    return out


def decision_from_response(
    status: int,
    body: bytes,
    response_headers: Optional[dict] = None,
) -> ObservedDecision:
    """08a's observation projection. The proxy is not modified."""
    evidence: dict = {"status": status}
    if response_headers:
        evidence["responseHeaders"] = dict(response_headers)
    if status == 423:
        evidence["backendReached"] = False
        return ObservedDecision(4, "refuse-and-suspend", evidence)
    if status == 401:
        evidence["backendReached"] = False
        return ObservedDecision(None, "refuse-unauthorized", evidence)
    if status == 403:
        evidence["backendReached"] = False
        return ObservedDecision(4, "refuse-provisioning", evidence)
    if status == 202:
        evidence["backendReached"] = False
        return ObservedDecision(3, "withhold", evidence)
    if 200 <= status < 300:
        evidence["backendReached"] = True
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (ValueError, UnicodeError):
            return ObservedDecision(
                None, "execute", {**evidence, "note": "unparseable echo body"}
            )
        echo_headers = payload.get("headers") if isinstance(payload, dict) else {}
        if not isinstance(echo_headers, dict):
            echo_headers = {}
        evidence["echo"] = echo_headers
        raw = echo_headers.get("x-ctier-tier")
        try:
            tier = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            tier = None
        leaked = [
            k for k in echo_headers
            if k.lower().startswith("x-ctier-") and k.lower() not in {
                "x-ctier-tier", "x-ctier-deployment",
                "x-ctier-operation", "x-ctier-correlation-id",
            }
        ]
        if leaked:
            evidence["leakedInbound"] = leaked
        return ObservedDecision(tier, "execute", evidence)
    return ObservedDecision(None, f"unexpected-{status}", evidence)


class KongAdapter(Adapter):
    name = "kong"

    def __init__(self, base_url: str, request_fn=None, qualified_spec=None, token=None, token_fn=None):
        self.base_url = base_url.rstrip("/")
        self._request_fn = request_fn
        self.qualified_spec = qualified_spec
        self.token = token
        self.token_fn = token_fn

    def run(self, case: dict) -> ObservedDecision:
        req = case["request"]
        url = self.base_url + req["path"]
        query = req.get("query") or {}
        if query:
            url = url + "?" + urlencode(query)
        headers = identity_headers(case, req.get("headers") or {})
        if case.get("refreshToken") and self.token_fn is not None:
            self.token = self.token_fn()
        if self.token:
            lower = {k.lower() for k in headers}
            if "authorization" not in lower:
                headers["Authorization"] = f"Bearer {self.token}"
        body = req.get("body")
        data = None if body is None else str(body).encode("utf-8")
        if self._request_fn is not None:
            status, raw, resp_headers = self._request_fn(
                req["method"], url, headers, data
            )
        else:
            status, raw, resp_headers = self._http(req["method"], url, headers, data)
        observed = decision_from_response(status, raw, resp_headers)
        # 403 is a disposition, not a classification. Exclusion and Tier 3
        # without custody share the status. appliedTier is filled from the
        # spec so the comparison is what the proxy did, not a fake T4.
        if (
            observed.disposition == "refuse-provisioning"
            and self.qualified_spec is not None
        ):
            observed.applied_tier = classified_applied_tier(
                self.qualified_spec, case
            )
        return observed

    def _http(self, method, url, headers, data) -> tuple[int, bytes, dict]:
        request = Request(url, data=data, method=str(method).upper())
        for key, value in headers.items():
            request.add_header(key, value)
        try:
            with urlopen(request, timeout=10) as resp:
                return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
        except HTTPError as exc:
            return exc.code, exc.read(), {k.lower(): v for k, v in exc.headers.items()}
        except URLError as exc:
            return 0, str(exc.reason).encode(), {}
