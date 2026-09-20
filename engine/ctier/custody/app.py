# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""HTTP surface for custody. FastAPI is a serve extra; the library does not import this.

v1 authenticates the approver as the `X-Approver-Id` header and records that
identity. Production deployments bind `/v1/decisions/{correlationId}` to their
own identity provider and record the identity that provider asserts. The v1
header is a stand-in so the named-approver claim is testable, not the
intended production mechanism.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from .service import DecisionError, PersistIn, decide, persist, review_queue
from .store import Store
from .execute import HttpExecutor
from ..authz.directory import directory_from_env
from ..classifier import GovernanceConfig
from ..ledger.records import attempt_from_ingress, decision_from_ingress
from ..ledger.store import prepare_fallback
from .floor import floors_from_ledger

DEFAULT_REVIEW_PERIOD = 86400


def create_app(
    store: Optional[Store] = None,
    *,
    hmac_key: Optional[bytes] = None,
    review_period_seconds: Optional[int] = None,
    executor=None,
    service_token: Optional[str] = None,
    directory=None,
) -> FastAPI:
    path = os.environ.get("CTIER_SQLITE", ":memory:")
    owned = store or Store(path)
    key = hmac_key
    if key is None and os.environ.get("CTIER_HMAC_KEY"):
        key = os.environ["CTIER_HMAC_KEY"].encode("utf-8")
    period = review_period_seconds
    if period is None:
        period = int(os.environ.get("CTIER_REVIEW_PERIOD_SECONDS", DEFAULT_REVIEW_PERIOD))
    token = service_token
    if token is None:
        token = os.environ.get("CTIER_SERVICE_TOKEN", "")
    runner = executor
    if runner is None and os.environ.get("CTIER_BACKEND_URL"):
        runner = HttpExecutor(os.environ["CTIER_BACKEND_URL"])

    fallback = os.environ.get("CTIER_LEDGER_FALLBACK") or ""
    if fallback:
        prepare_fallback(fallback)
        owned.ledger.ingest_fallback(fallback)

    decay = int(os.environ.get("CTIER_DECAY_SECONDS", str(GovernanceConfig.decay_seconds)))
    escalate_above = int(os.environ.get("CTIER_ESCALATE_ABOVE", str(GovernanceConfig.escalate_above)))
    floor_cfg = GovernanceConfig(decay_seconds=decay, escalate_above=escalate_above)

    app = FastAPI(title="ctier-custody", version="0.3.0")
    app.state.store = owned
    app.state.hmac_key = key
    app.state.review_period_seconds = period
    app.state.executor = runner
    app.state.service_token = token
    app.state.ledger_fallback = fallback
    app.state.floor_config = floor_cfg
    app.state.directory = directory if directory is not None else directory_from_env()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/pending")
    async def post_pending(request: Request):
        payload = PersistIn.model_validate(await request.json())
        result = persist(
            owned,
            payload,
            now=datetime.now(timezone.utc),
            hmac_key=key,
            review_period_seconds=period,
        )
        return JSONResponse(
            status_code=202,
            content=result.body,
            headers={
                k: v for k, v in result.headers.items() if k.lower() != "content-type"
            },
        )

    @app.get("/v1/pending")
    def get_pending():
        return {"pending": review_queue(owned, now=datetime.now(timezone.utc))}

    @app.post("/v1/decisions/{correlation_id}")
    async def post_decision(correlation_id: str, request: Request):
        approver = (request.headers.get("x-approver-id") or "").strip()
        if not approver:
            return JSONResponse(
                status_code=401,
                content={"status": "unauthenticated", "detail": "approver required"},
            )
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        try:
            result = decide(
                owned,
                correlation_id,
                str(payload.get("decision") or ""),
                approver,
                now=datetime.now(timezone.utc),
                executor=runner,
                service_token=token or "",
                directory=app.state.directory,
            )
        except DecisionError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"status": "error", "detail": exc.detail},
            )
        return JSONResponse(status_code=200, content=result.body())

    @app.get("/v1/ledger")
    def get_ledger(
        correlationScope: Optional[str] = None,
        type: Optional[str] = Query(default=None, alias="type"),
    ):
        if fallback:
            owned.ledger.ingest_fallback(fallback)
        try:
            records = owned.ledger.list_records(
                record_type=type,
                correlation_scope=correlationScope,
            )
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"detail": str(exc)})
        return {"records": records}

    @app.post("/v1/ledger")
    async def post_ledger(request: Request):
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"detail": "json required"})
        if not isinstance(payload, dict):
            return JSONResponse(status_code=400, content={"detail": "json object required"})
        kind = payload.get("type")
        try:
            if not kind and isinstance(payload.get("ctierSchema"), str):
                from ..ledger.compat import resolve_record_kind

                kind = resolve_record_kind(payload["ctierSchema"])
            if kind == "decision":
                record = decision_from_ingress(payload, hmac_key=key)
                owned.ledger.append_decision(record)
                if record.get("disposition") == "refuse-and-suspend":
                    try:
                        app.state.directory.revoke(
                            str(record.get("agentId") or ""),
                            str(record.get("operationAnchor") or ""),
                        )
                    except Exception:
                        pass
            elif kind == "attempt":
                record = attempt_from_ingress(payload)
                owned.ledger.append_attempt(record, ignore_duplicate=True)
            else:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "type must be decision or attempt"},
                )
        except Exception as exc:
            return JSONResponse(status_code=400, content={"detail": str(exc)})
        return JSONResponse(status_code=201, content=record)

    @app.get("/v1/floors")
    def get_floors():
        """Published floors for scopes past the threshold. Empty means none.

        An enforcement point that cannot reach this endpoint has no floor,
        which is no escalation — not refusal.
        """
        if fallback:
            owned.ledger.ingest_fallback(fallback)
        return floors_from_ledger(owned.ledger, config=floor_cfg)

    return app


app = create_app()
