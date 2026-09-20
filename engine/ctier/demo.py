# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""End-to-end demo walker. Invoked by `make demo` / `./demo.sh`. Not pytest."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ctier.authz import ACCESS_TOKEN_LIFESPAN, AGENT_SUB_CLIENT, scope_name
from ctier.compose import compose
from ctier.cover import cover
from ctier.generate import (
    DEFAULT_CUSTODY_TIMEOUT_MS,
    DEFAULT_FLOOR_POLL_MS,
    DEFAULT_RECORDS_URL,
    generate,
)
from ctier.ledger.records import decision_record
from ctier.migrate import MigrationConfig, propose_migrations
from ctier.spec_loader import SPEC_DIR

REPO = Path(__file__).resolve().parents[2]
REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)
KONG_COMPOSE = REPO / "targets" / "kong" / "live" / "compose.yaml"
APISIX_COMPOSE = REPO / "targets" / "apisix" / "live" / "compose.yaml"
MARKER = "[ctier-decision] "
ATTEMPT_MARKER = "[ctier-attempt] "
BALANCE = "/accounts/12345/balance"
DISPLAY = "/customers/12345/preferences/display"
COMMUNICATION = "/customers/12345/preferences/communication"
PAYMENTS = "/payments"
CLOSURE = "/accounts/12345/closure"
CROSSING = 10  # Derived: escalate_above // T1_weight + 1
FLOOR_POLL_MS = DEFAULT_FLOOR_POLL_MS
SEED_COUNT = 10  # Configured: MigrationConfig.raise_min_sample
RAISE_WINDOW_SECONDS = 14 * 86400  # Configured: MigrationConfig.raise_window_seconds

# Printed figures that must appear in measurements.md (name, value, kind).
FIGURES: tuple[tuple[str, str, str], ...] = (
    ("floor poll interval", "1000 ms", "Configured"),
    ("accumulation visibility bound", "one poll interval (1000 ms)", "Derived"),
    ("T1 requests to cross the threshold", "10", "Derived"),
    ("published floor", "2", "Derived"),
    ("access-token lifetime", "30 s", "Configured"),
    ("custody hop timeout", "200 ms", "Configured"),
    ("live decay window", "5 s", "Configured"),
    ("migration raise min sample", "10", "Configured"),
    ("migration raise window", "14 days", "Configured"),
)


def out(text: str = "") -> None:
    print(text, flush=True)


def beat_header(n: int, title: str, doing: str, expect: str) -> None:
    out()
    out(f"── Beat {n}: {title}")
    out(f"   Doing:    {doing}")
    out(f"   Expects:  {expect}")


def evidence(text: str) -> None:
    out(f"   Evidence: {text}")


def figure(name: str, value: str, kind: str) -> str:
    return f"{value} [{kind} — measurements.md: {name}]"


def jwt_claims(token: str) -> dict:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    import base64

    return json.loads(base64.urlsafe_b64decode(padded))


def scopes_of(token: str) -> set[str]:
    raw = jwt_claims(token).get("scope") or ""
    return {s for s in str(raw).split() if s}


def applied_tier(raw: bytes) -> int | None:
    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except ValueError:
        return None
    headers = payload.get("headers") or {}
    value = headers.get("x-ctier-tier")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_decision_logs(text: str) -> list[dict]:
    found = []
    for line in text.splitlines():
        if MARKER not in line:
            continue
        payload = line.split(MARKER, 1)[1].strip()
        start = payload.find("{")
        end = payload.rfind("}")
        if start < 0 or end <= start:
            continue
        try:
            rec = json.loads(payload[start:end + 1])
        except json.JSONDecodeError:
            continue
        if rec.get("ctierSchema") == "decision-record/0.2.0":
            found.append(rec)
    return found


def parse_attempt_logs(text: str) -> list[dict]:
    found = []
    for line in text.splitlines():
        if ATTEMPT_MARKER not in line:
            continue
        payload = line.split(ATTEMPT_MARKER, 1)[1].strip()
        start = payload.find("{")
        end = payload.rfind("}")
        if start < 0 or end <= start:
            continue
        try:
            rec = json.loads(payload[start:end + 1])
        except json.JSONDecodeError:
            continue
        if rec.get("ctierSchema") == "attempt-record/0.3.0":
            found.append(rec)
    return found


def gateway_logs(stack, service: str) -> str:
    proc = stack._compose("logs", "--no-color", "--tail", "800", service, check=False)
    text = (proc.stdout or "") + (proc.stderr or "")
    paths = {
        "kong": "cat /usr/local/kong/logs/error.log 2>/dev/null || true",
        "apisix": "cat /usr/local/apisix/logs/error.log 2>/dev/null || true",
    }
    if service in paths:
        inner = stack.exec(service, "sh", "-c", paths[service], check=False)
        text += inner.stdout or ""
        text += inner.stderr or ""
    return text


def compose_down(project: str, compose_file: Path) -> None:
    subprocess.run(
        [
            "docker", "compose", "-p", project, "-f", str(compose_file),
            "down", "-v", "--remove-orphans",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def reset_rigs() -> None:
    out("WARNING: about to wipe a previous run. Copy first if you meant to inspect it.")
    out("  ledger rows — GET http://127.0.0.1:18200/v1/ledger (Kong) and :19200 (APISIX)")
    out("  pending reviews — GET http://127.0.0.1:18200/v1/pending and :19200/v1/pending")
    out("  revocations — Keycloak grants in each compose project (re-imported on next start)")
    out("RESET: tearing down Kong and APISIX compose projects, including volumes.")
    compose_down("ctier-kong-live", KONG_COMPOSE)
    compose_down("ctier-apisix-live", APISIX_COMPOSE)


class EngineRun:
    def __init__(self, name: str, target: str, stack, custody_url: str, gw_service: str,
                 custody_internal: str):
        self.name = name
        self.target = target
        self.stack = stack
        self.custody = custody_url
        self.gw_service = gw_service
        self.custody_internal = custody_internal
        self.outcomes: dict[str, Any] = {}

    def custody_cfg(self) -> dict:
        cfg = {
            "url": self.custody_internal,
            "timeout_ms": DEFAULT_CUSTODY_TIMEOUT_MS,
            "floor_poll_ms": FLOOR_POLL_MS,
        }
        if self.target == "kong":
            cfg["ledger_fallback"] = "/var/ctier/ledger/attempts.jsonl"
        return cfg

    def load(self, qualified, *, observe: bool = False, custody: bool = False) -> dict[str, str]:
        files = generate(
            qualified,
            target=self.target,
            observe=observe,
            custody=self.custody_cfg() if custody else None,
        )
        self.stack.load_generated(files)
        if custody:
            from tests.live.rig import wait_url

            wait_url(self.custody + "/health", timeout=60.0)
            time.sleep(0.4)
        return files

    def call(self, method: str, path: str, *, scope: str, body: str | None = None,
             token: str | None = None, query: dict | None = None):
        if token is None:
            headers = self.stack.auth_headers(**{"X-Agent-Id": "agent-a", "X-Task-Id": scope})
        else:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Agent-Id": "agent-a",
                "X-Task-Id": scope,
            }
        return self.stack.request(method, path, query=query, headers=headers, body=body)

    def http_custody(self, method: str, path: str, **kwargs):
        from tests.live.rig import http

        return http(method, self.custody + path, **kwargs)


def wait_floor(engine: EngineRun, scope: str) -> int:
    deadline = time.monotonic() + (FLOOR_POLL_MS / 1000.0) + 0.5
    last = 1
    while time.monotonic() < deadline:
        status, raw, _ = engine.call("GET", BALANCE, scope=scope)
        if status != 200:
            raise RuntimeError(f"{engine.name} T1 after crossing returned {status}")
        last = applied_tier(raw) or last
        if last >= 2:
            return last
        time.sleep(0.15)
    raise RuntimeError(
        f"{engine.name} still at applied tier {last} after the Derived bound "
        f"(threshold-crossing + one poll interval)"
    )


def withhold_put(engine: EngineRun, scope: str, token: str | None = None):
    last: tuple = (None, b"", {})
    for _ in range(5):
        status, raw, hdrs = engine.call("PUT", COMMUNICATION, scope=scope, token=token)
        last = (status, raw, hdrs)
        if status == 202:
            return status, raw, hdrs, json.loads(raw.decode("utf-8"))
        if status == 503:
            time.sleep(0.5)
            continue
        break
    status, raw, _hdrs = last
    raise RuntimeError(f"withhold: {status} {raw[:200]!r}")


def beat_1_classify(qualified, manifest) -> dict[str, Any]:
    beat_header(
        1,
        "Level 0 — classify, nothing deployed",
        "Compose the public consequence-tiered-api.yaml and run cover.",
        "A coverage distribution. No proxy is started for this beat.",
    )
    report = cover(qualified, None, NOW)
    totals = report["totals"]
    out(f"   compositionDigest: {manifest['compositionDigest']}")
    evidence(
        f"coverage totals declared={totals.get('declared')} "
        f"recommended={totals.get('recommended')} absent={totals.get('absent')} "
        f"(n={len(report['operations'])} operations)"
    )
    by_tier: dict[int, int] = {}
    for row in report["operations"]:
        if row.get("declaredTier") is not None:
            t = int(row["declaredTier"])
            by_tier[t] = by_tier.get(t, 0) + 1
    evidence(f"declared-tier distribution: {dict(sorted(by_tier.items()))}")
    return {"totals": totals, "digest": manifest["compositionDigest"]}


def beat_2_observe(engine: EngineRun, qualified) -> None:
    beat_header(
        2,
        "Level 1 — observe",
        f"Generate {engine.name} with observe=True (no custody). GET a Tier 1.",
        "200, and a schema-shaped Decision in the gateway log. Nothing is refused.",
    )
    engine.load(qualified, observe=True)
    status, raw, _ = engine.call("GET", BALANCE, scope=f"demo-{engine.name}-l1")
    if status != 200:
        raise RuntimeError(f"L1 GET balance: {status} {raw[:200]!r}")
    records = []
    for _ in range(20):
        records = parse_decision_logs(gateway_logs(engine.stack, engine.gw_service))
        if records:
            break
        time.sleep(0.25)
    if not records:
        raise RuntimeError(f"no {MARKER} line in {engine.name} logs")
    rec = records[-1]
    evidence(f"HTTP {status}; log Decision appliedTier={rec.get('appliedTier')} "
             f"disposition={rec.get('disposition')}")
    engine.outcomes["l1_status"] = status
    engine.outcomes["l1_disposition"] = rec.get("disposition")


def beat_3_level2(engine: EngineRun, qualified) -> None:
    beat_header(
        3,
        "Tiers 1, 2 and 4 — Level 2, no custody process",
        f"Generate {engine.name} without custody_url. Hit T1, T2, T4.",
        "T1 and T2 execute. T4 suspends (423). Tier 3 is a provisioning refusal, not a withhold.",
    )
    engine.load(qualified, observe=False, custody=False)
    s1, r1, _ = engine.call("GET", BALANCE, scope=f"demo-{engine.name}-l2-t1")
    t1 = applied_tier(r1)
    s2, r2, _ = engine.call("PUT", DISPLAY, scope=f"demo-{engine.name}-l2-t2", body="{}")
    t2 = applied_tier(r2)
    s4, _, _ = engine.call("POST", PAYMENTS, scope=f"demo-{engine.name}-l2-t4", body="{}")
    s3, raw3, _ = engine.call("PUT", COMMUNICATION, scope=f"demo-{engine.name}-l2-t3")
    if s1 != 200 or t1 != 1:
        raise RuntimeError(f"L2 T1: {s1} tier={t1}")
    if s2 != 200 or t2 != 2:
        raise RuntimeError(f"L2 T2: {s2} tier={t2} {r2[:200]!r}")
    if s4 != 423:
        raise RuntimeError(f"L2 T4: {s4}")
    if s3 != 403:
        raise RuntimeError(f"L2 T3 without custody should 403, got {s3} {raw3[:200]!r}")
    evidence(
        f"T1 HTTP {s1} appliedTier={t1}; T2 HTTP {s2} appliedTier={t2}; "
        f"T4 HTTP {s4}; T3 HTTP {s3} (refuse-provisioning — no withhold hop)"
    )
    evidence("Level 2 does not satisfy C7: no derived Idempotency-Key is persisted.")
    engine.outcomes["l2"] = (s1, t1, s2, t2, s4, s3)


def beat_4_withhold(engine: EngineRun, qualified) -> None:
    beat_header(
        4,
        "Tier 3 — withhold, approve, execute from persisted context",
        "PUT communication preferences. Approve. Custody executes; the agent is not called back.",
        "202 pending; approve returns executed; echo path matches the withheld request.",
    )
    engine.load(qualified, custody=True)
    status, raw, hdrs, body = withhold_put(engine, f"demo-{engine.name}-t3")
    cid = body["correlationId"]
    qs, qraw, _ = engine.http_custody("GET", "/v1/pending")
    pending = json.loads(qraw.decode("utf-8")).get("pending") or []
    match = [p for p in pending if p.get("correlationId") == cid]
    if not match:
        raise RuntimeError(f"pending missing {cid}: {pending}")
    ds, draw, _ = engine.http_custody(
        "POST",
        f"/v1/decisions/{cid}",
        headers={"Content-Type": "application/json", "X-Approver-Id": "demo-analyst"},
        body=json.dumps({"decision": "approve"}).encode("utf-8"),
    )
    decision = json.loads(draw.decode("utf-8"))
    if ds != 200 or decision.get("status") != "executed":
        raise RuntimeError(f"approve: {ds} {decision}")
    echo = json.loads(decision["outcome"]["body"]) if decision.get("outcome") else {}
    evidence(
        f"HTTP {status} correlationId={cid}; pending path={match[0].get('path')}; "
        f"executed status={decision.get('status')} echo.method={echo.get('method')} "
        f"echo.path={echo.get('path')}"
    )
    engine.outcomes["t3"] = (status, decision.get("status"), echo.get("method"), echo.get("path"))


def beat_5_expiry_vs_reject(engine: EngineRun, qualified) -> None:
    beat_header(
        5,
        "Expiry versus rejection",
        "Withhold and wait out the token (T1 still executes). Then withhold and reject (next token 401).",
        "An unrejected withhold does not suspend. A reject does. Same operation, two outcomes.",
    )
    engine.load(qualified, custody=True)
    first = engine.stack.fresh_token()
    claims = jwt_claims(first)
    remaining = int(claims["exp"]) - int(time.time())
    s_hold, raw_hold, _, _body_hold = withhold_put(
        engine, f"demo-{engine.name}-expire", token=first,
    )
    wait = max(remaining + 1, 1)
    out(f"   Waiting {wait}s — access-token lifetime "
        f"{figure('access-token lifetime', '30 s', 'Configured')} "
        f"(remaining on this token {remaining}s).")
    time.sleep(wait)
    s_t1, raw_t1, _ = engine.call(
        "GET", BALANCE, scope=f"demo-{engine.name}-expire",
        token=engine.stack.fresh_token(),
    )
    if s_t1 != 200 or applied_tier(raw_t1) != 1:
        raise RuntimeError(f"after expiry expected T1 200, got {s_t1} tier={applied_tier(raw_t1)}")
    status, raw, _, body = withhold_put(engine, f"demo-{engine.name}-reject")
    engine.http_custody(
        "POST",
        f"/v1/decisions/{body['correlationId']}",
        headers={"Content-Type": "application/json", "X-Approver-Id": "demo-analyst"},
        body=json.dumps({"decision": "reject"}).encode("utf-8"),
    )
    s_rej, raw_rej, _ = engine.call(
        "PUT", COMMUNICATION, scope=f"demo-{engine.name}-reject-next",
        token=engine.stack.fresh_token(),
    )
    if s_rej not in {401, 403}:
        raise RuntimeError(f"after reject expected 401 or 403, got {s_rej} {raw_rej[:200]!r}")
    evidence(
        f"unrejected withhold → T1 HTTP {s_t1} appliedTier=1; reject → next token HTTP {s_rej}"
    )
    if s_rej == 403:
        evidence(
            "APISIX stock openid-connect answers missing scope with 403; "
            "Kong's Lua plugin answers 401. Same compiled absence, different plugin."
        )
    engine.outcomes["expiry"] = (s_t1, s_rej in {401, 403})


def beat_6_decomposition(engine: EngineRun, qualified) -> None:
    beat_header(
        6,
        "Decomposition — sequence crossing the threshold",
        f"Issue {CROSSING} Tier-1 requests on one task, then wait the visibility bound.",
        "Applied tier becomes the published floor. Escalation is not a refusal.",
    )
    engine.load(qualified, custody=True)
    scope = f"demo-{engine.name}-decomp"
    last = 1
    for _ in range(CROSSING):
        status, raw, _ = engine.call("GET", BALANCE, scope=scope)
        if status != 200:
            raise RuntimeError(f"decomp T1 {status}")
        last = applied_tier(raw) or last
    out(
        "   Bound: threshold-crossing plus "
        f"{figure('accumulation visibility bound', 'one poll interval (1000 ms)', 'Derived')}. "
        "Not the 216 ms Observed sample."
    )
    out(
        f"   Crossing count: {figure('T1 requests to cross the threshold', '10', 'Derived')}; "
        f"published floor {figure('published floor', '2', 'Derived')}."
    )
    floor = wait_floor(engine, scope)
    evidence(f"after {CROSSING} T1s, appliedTier={floor} (was {last} at the crossing request)")
    engine.outcomes["decomp"] = floor


def beat_7_exclusion_suspension(engine: EngineRun, qualified) -> None:
    if engine.target == "kong":
        doing = (
            "POST closeAccount (never granted). POST /payments (T4). Fresh token."
        )
        expects = (
            "Exclusion 403. T4 423 then the next token is 401 — Kong T4 POSTs a "
            "Decision and the directory revokes. Same compiled absence: the scope is gone."
        )
    else:
        doing = (
            "POST closeAccount (never granted). POST /payments (T4). Fresh token — "
            "this engine's T4 will not revoke."
        )
        expects = (
            "Exclusion 403. T4 423 and the next token is still 423. On APISIX the "
            "grant is removed by C8 reject (beat 5), not by T4. Same compiled absence, "
            "different trigger."
        )
    beat_header(
        7,
        "Exclusion and suspension — the same compiled absence",
        doing,
        expects,
    )
    engine.load(qualified, custody=True)
    s_ex, raw_ex, _ = engine.call(
        "POST", CLOSURE, scope=f"demo-{engine.name}-ex",
        token=engine.stack.fresh_token(), body="{}",
    )
    if s_ex != 403:
        raise RuntimeError(f"exclusion: {s_ex} {raw_ex[:200]!r}")
    s4, _, _ = engine.call(
        "POST", PAYMENTS, scope=f"demo-{engine.name}-sus",
        token=engine.stack.fresh_token(), body="{}",
    )
    if s4 != 423:
        raise RuntimeError(f"T4: {s4}")
    s_next, raw_next, _ = engine.call(
        "POST", PAYMENTS, scope=f"demo-{engine.name}-sus-next",
        token=engine.stack.fresh_token(), body="{}",
    )
    evidence(f"closeAccount HTTP {s_ex}; T4 HTTP {s4}; next token HTTP {s_next}")
    if engine.target == "kong":
        if s_next != 401:
            raise RuntimeError(f"Kong after T4 expected 401, got {s_next} {raw_next[:200]!r}")
        evidence("Kong T4 POSTs a Decision and the directory revokes; the next token is 401.")
    else:
        if s_next != 423:
            evidence(
                f"APISIX after T4 HTTP {s_next} (stock T4 is fault-injection; "
                "it does not revoke — findings 13a / live test)."
            )
        else:
            evidence(
                "APISIX T4 is stock fault-injection 423. It does not POST a Decision, "
                "so the directory is not told to revoke. The next token is still 423. "
                "C8 reject (beat 5) is the APISIX revoke path."
            )
    engine.outcomes["absence"] = (s_ex, s4)


def beat_8_delegation(engine: EngineRun, qualified) -> None:
    beat_header(
        8,
        "Delegation — a sub-agent that cannot widen its scope",
        f"Exchange a parent token into {AGENT_SUB_CLIENT}. Ask for initiatePayment.",
        "Balance is obtainable. Payment is not. Entitlement, not subject-token lineage.",
    )
    engine.load(qualified, custody=True)
    balance = scope_name("getBalance")
    payment = scope_name("initiatePayment")
    parent = engine.stack.fresh_token(scopes=f"{balance} {payment}")
    a_status, a_body = engine.stack.exchange(parent, scopes=balance, client_id=AGENT_SUB_CLIENT)
    if a_status != 200:
        raise RuntimeError(f"exchange balance: {a_status} {a_body}")
    have = scopes_of(a_body["access_token"])
    b_status, b_body = engine.stack.exchange(parent, scopes=payment, client_id=AGENT_SUB_CLIENT)
    b_scopes = scopes_of(b_body["access_token"]) if b_status == 200 else set()
    claims = jwt_claims(a_body["access_token"])
    if payment in have or (b_status == 200 and payment in b_scopes):
        raise RuntimeError("sub-agent obtained initiatePayment")
    if balance not in have:
        raise RuntimeError(f"sub-agent missing balance: {have}")
    evidence(
        f"exchange balance HTTP {a_status} scopes={sorted(have)} azp={claims.get('azp')!r}; "
        f"exchange payment HTTP {b_status} scopes={sorted(b_scopes) if b_status == 200 else []} "
        f"error={b_body.get('error')}"
    )
    engine.outcomes["delegation"] = (
        a_status == 200 and balance in have,
        payment not in have,
        b_status != 200 or payment not in b_scopes,
    )


def beat_9_custody_killed(engine: EngineRun, qualified) -> None:
    if engine.target == "kong":
        expects = (
            "503 twice. An Attempt on the gateway log with appliedTier undetermined "
            "(null), and the same object on JSONL so custody can ingest when it returns."
        )
    else:
        expects = (
            "503 twice. An Attempt on the gateway log with appliedTier undetermined "
            "(null). No JSONL file — 29's log sink, no blocking I/O. Same record, different transport."
        )
    beat_header(
        9,
        "Custody killed — a refusal to decide is a decision",
        "Stop custody. PUT a Tier 3 twice.",
        expects,
    )
    engine.load(qualified, custody=True)
    engine.stack.stop_service("custody")
    try:
        statuses = []
        for i in range(2):
            status, raw, hdrs = engine.call(
                "PUT", COMMUNICATION, scope=f"demo-{engine.name}-killed-{i}",
            )
            statuses.append(status)
            if status != 503:
                raise RuntimeError(f"expected 503, got {status} {raw[:200]!r}")
            if hdrs.get("retry-after") != "5":
                out(f"   note: Retry-After={hdrs.get('retry-after')!r} "
                    f"(Configured custody-unavailable Retry-After is 5 s)")
        attempts = []
        for _ in range(20):
            attempts = parse_attempt_logs(gateway_logs(engine.stack, engine.gw_service))
            if attempts:
                break
            time.sleep(0.25)
    finally:
        engine.stack.start_service("custody")
    if not attempts:
        raise RuntimeError(f"{engine.name} emitted no [ctier-attempt] line — C10 failure")
    rec = attempts[-1]
    if rec.get("appliedTier") is not None:
        raise RuntimeError(f"appliedTier must be undetermined (null), got {rec.get('appliedTier')!r}")
    if rec.get("reason") != "custody-unavailable":
        raise RuntimeError(f"reason {rec.get('reason')!r}")
    evidence(
        f"HTTP {statuses} twice. Log Attempt appliedTier={rec.get('appliedTier')!r} "
        f"(undetermined) declaredTier={rec.get('declaredTier')} reason={rec.get('reason')}"
    )
    if engine.target == "kong":
        ls, lraw, _ = engine.http_custody("GET", "/v1/ledger?type=attempt")
        rows = json.loads(lraw.decode("utf-8")).get("records") or [] if ls == 200 else []
        ingested = [r for r in rows if r.get("reason") == "custody-unavailable"]
        evidence(
            f"Kong also appended JSONL; after ingest, ledger attempts={len(ingested)}. "
            "Transport extra, not a second kind of record."
        )
    else:
        evidence(
            "APISIX records only on the gateway log (no JSONL, no hop). "
            "C10 holds by 29's sink."
        )
    evidence(
        f"custody hop timeout {figure('custody hop timeout', '200 ms', 'Configured')} "
        "is the fail-closed bound, not a measurement of how long the 503 took."
    )
    engine.outcomes["killed"] = (
        tuple(statuses),
        rec.get("appliedTier") is None,
        rec.get("reason"),
        rec.get("declaredTier"),
    )


def beat_10_seed_and_migrate(engine: EngineRun, qualified, digest: str) -> None:
    beat_header(
        10,
        "Migration proposals — the cycle closing",
        "Seed Decision records through POST /v1/ledger, then propose_migrations.",
        "A raise signal from genuine Decision objects. The clock is compressed; the records are not invented in SQL.",
    )
    engine.load(qualified, custody=True)
    out(
        f"   Seeding {SEED_COUNT} Decision records through POST /v1/ledger — "
        "the same hop the enforcement point uses when it records. "
        f"The timestamps are now, inside the Configured raise window of "
        f"{figure('migration raise window', '14 days', 'Configured')}. "
        "That is synthetic about the calendar and honest about the objects: "
        "schema-valid Decisions with escalationReason=payload-exceeds-declared-bounds, "
        "not rows inserted into sqlite."
    )
    out(
        f"   Count {SEED_COUNT} is "
        f"{figure('migration raise min sample', '10', 'Configured')} "
        "(MigrationConfig.raise_min_sample)."
    )
    from tests.live.rig import http

    deployment = json.loads(generate(qualified, target=engine.target)["ctier-generate.json"])
    dep = deployment["deploymentDigest"]
    created = 0
    for i in range(SEED_COUNT):
        rec = decision_record(
            operation_anchor="listTransactions",
            agent_id="agent-demo-seed",
            correlation_scope=f"demo-seed-{engine.name}",
            applied_tier=3,
            escalation_reason="payload-exceeds-declared-bounds",
            disposition="withhold",
            idempotency_key=hashlib.sha256(
                f"demo-seed-{engine.name}-{i}".encode()
            ).hexdigest(),
            deployment_digest=dep,
            declared_tier=1,
            correlation_id=f"demo-seed-{engine.name}-{i}",
        )
        rec["type"] = "decision"
        status, raw, _ = http(
            "POST",
            engine.custody + "/v1/ledger",
            headers={"Content-Type": "application/json"},
            body=json.dumps(rec).encode("utf-8"),
        )
        if status not in {200, 201}:
            raise RuntimeError(f"seed POST: {status} {raw[:300]!r}")
        created += 1
    ls, lraw, _ = engine.http_custody("GET", "/v1/ledger?type=decision")
    rows = json.loads(lraw.decode("utf-8")).get("records") or []
    proposals = propose_migrations(rows, config=MigrationConfig())
    signals = [p.get("signal") for p in proposals.get("proposals") or []]
    if "tier2-bounds-escalated" not in signals:
        raise RuntimeError(f"expected tier2-bounds-escalated, got {proposals}")
    evidence(
        f"POSTed {created} Decisions; propose_migrations signals={signals} "
        f"n_proposals={len(proposals.get('proposals') or [])}"
    )
    engine.outcomes["migrate"] = signals


def run_engine(name: str, qualified, composition_digest: str) -> dict[str, Any]:
    from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
    from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_INTERNAL
    from tests.live.apisix_rig import ApisixStack
    from tests.live.rig import CUSTODY as KONG_CUSTODY
    from tests.live.rig import CUSTODY_INTERNAL as KONG_INTERNAL
    from tests.live.rig import KongStack

    work = Path(tempfile.mkdtemp(prefix=f"ctier-demo-{name}-"))
    if name == "kong":
        stack = KongStack(work)
        engine = EngineRun("kong", "kong", stack, KONG_CUSTODY, "kong", KONG_INTERNAL)
    else:
        stack = ApisixStack(work)
        engine = EngineRun("apisix", "apisix", stack, APISIX_CUSTODY, "apisix", APISIX_INTERNAL)
    out()
    out(f"════ {name.upper()} ════")
    stack.start()
    try:
        files = generate(qualified, target=engine.target)
        meta = json.loads(files["ctier-generate.json"])
        out(f"   compositionDigest (compose-time): {composition_digest}")
        out(f"   deploymentDigest ({name} generate): {meta['deploymentDigest']}")
        engine.outcomes["compositionDigest"] = composition_digest
        engine.outcomes["deploymentDigest"] = meta["deploymentDigest"]
        beat_2_observe(engine, qualified)
        beat_3_level2(engine, qualified)
        beat_4_withhold(engine, qualified)
        beat_5_expiry_vs_reject(engine, qualified)
        beat_6_decomposition(engine, qualified)
        beat_7_exclusion_suspension(engine, qualified)
        beat_8_delegation(engine, qualified)
        beat_9_custody_killed(engine, qualified)
        beat_10_seed_and_migrate(engine, qualified, composition_digest)
    finally:
        out(f"   stopping {name} (volumes included)")
        stack.stop()
    return engine.outcomes


def compare(kong: dict, apisix: dict) -> None:
    out()
    out("════ SAMENESS ════")
    kd, ad = kong.get("compositionDigest"), apisix.get("compositionDigest")
    out(f"   compositionDigest Kong={kd}")
    out(f"   compositionDigest APISIX={ad}")
    if kd != ad:
        raise RuntimeError("compositionDigest diverged")
    out("   Same composed description drove both generates.")
    keys = (
        "l1_status", "l1_disposition", "l2", "t3", "expiry", "decomp",
        "absence", "delegation", "killed", "migrate",
    )
    diffs = []
    for key in keys:
        if kong.get(key) != apisix.get(key):
            diffs.append((key, kong.get(key), apisix.get(key)))
    if diffs:
        for key, a, b in diffs:
            out(f"   differ on {key}: Kong={a!r} APISIX={b!r}")
        raise RuntimeError("beat outcomes diverged")
    out("   Beat outcomes matched: L1 record, L2 statuses, T3 execute, expiry vs reject,")
    out("   decomposition floor, exclusion/suspension, delegation, custody-killed, migration signal.")
    out()
    out("Where they genuinely differ (not hidden):")
    out("   • APISIX enforces required scopes with the stock openid-connect plugin;")
    out("     Kong checks required_scope in the ctier Lua plugin.")
    out("   • Level 4: Kong starts the floor poller from the plugin worker module;")
    out("     APISIX starts it lazily from generated serverless-post-function Lua")
    out("     with a pid-keyed shared-dict claim. Same property, different hook.")
    out("   • After a revoked scope, APISIX's stock openid-connect returns 403;")
    out("     Kong's Lua plugin returns 401. Same absence, different status.")
    out("   • APISIX T4 does not revoke: stock fault-injection never POSTs a Decision.")
    out("     Kong T4 does. APISIX revoke is C8 reject (beat 5), not T4.")
    out("   • Custody-unavailable Attempts: both write the same schema-valid record")
    out("     (appliedTier null) to the gateway log. Kong also appends JSONL for ingest.")


def write_apigee_bundle(qualified) -> None:
    dest = REPO / "targets" / "apigee" / "package" / "generated"
    dest.mkdir(parents=True, exist_ok=True)
    files = generate(qualified, target="apigee", custody={
        "url": "https://custody.example.invalid",
        "timeout_ms": DEFAULT_CUSTODY_TIMEOUT_MS,
    }, records={
        "url": DEFAULT_RECORDS_URL,
        "timeout_ms": DEFAULT_CUSTODY_TIMEOUT_MS,
    })
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    out(f"   Apigee bundle written to {dest} ({len(files)} files), same compose as the live runs.")


def main() -> int:
    if shutil_missing():
        out("docker is required")
        return 1
    reset_rigs()
    qualified, manifest = compose(REFERENCE, [], NOW)
    out()
    out("ctier-engine demo — ten beats, Kong then APISIX, one composed description.")
    out(f"Input: {REFERENCE}")
    beat_1_classify(qualified, manifest)
    write_apigee_bundle(qualified)
    kong = run_engine("kong", qualified, manifest["compositionDigest"])
    apisix = run_engine("apisix", qualified, manifest["compositionDigest"])
    compare(kong, apisix)
    out()
    out("Done. Re-run `make demo` without a manual teardown; RESET runs first.")
    return 0


def shutil_missing() -> bool:
    import shutil

    return shutil.which("docker") is None


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
