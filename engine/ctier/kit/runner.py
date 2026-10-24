# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Run conformance-kit/1.1 against a URL, or any Target.

The runner does not know a repository layout. It sends requests
and reads what the operator pointed it at.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

DIR = Path(__file__).resolve().parent
CASES_PATH = DIR / "cases.yaml"
VERSION_PATH = DIR / "VERSION"
KIT_VERSION = VERSION_PATH.read_text(encoding="utf-8").strip()
SCHEMA_ID = f"conformance-kit/{KIT_VERSION}"
REPORT_ID = f"conformance-kit-report/{KIT_VERSION}"
CREDENTIAL_KEYS = frozenset({
    "authorization", "proxy-authorization", "cookie", "set-cookie",
    "access_token", "accessToken", "bearer",
})

# Every skip carries one of these. A reader must not treat skip as pass.
SKIP_NOT_APPLICABLE_AT_LEVEL = "not applicable at this level"
SKIP_REQUIRES_CAPABILITY = "requires a capability this target lacks"
SKIP_COVERED_AT_GENERATION = "covered at generation rather than runtime"
SKIP_REASONS = frozenset({
    SKIP_NOT_APPLICABLE_AT_LEVEL,
    SKIP_REQUIRES_CAPABILITY,
    SKIP_COVERED_AT_GENERATION,
})


@dataclass
class Observation:
    status: int
    headers: dict[str, str]
    body: dict[str, Any]
    raw: bytes = b""


@dataclass
class Target:
    """What the runner can do. Missing callables are missing capabilities."""

    send: Callable[..., Observation]
    token: str = ""
    records: Callable[[], list[dict[str, Any]]] | None = None
    observer_log: Callable[[], list[dict[str, Any]]] | None = None
    pending: Callable[[], list[dict[str, Any]]] | None = None
    approve: Callable[[str], dict[str, Any]] | None = None

    def capabilities(self) -> set[str]:
        out: set[str] = set()
        if self.records is not None:
            out.add("records")
        if self.observer_log is not None:
            out.add("observer")
        if self.pending is not None:
            out.add("pending")
        if self.approve is not None:
            out.add("approve")
        return out


def load_cases(path: Path | None = None) -> dict[str, Any]:
    doc = yaml.safe_load((path or CASES_PATH).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("ctierSchema") != SCHEMA_ID:
        raise ValueError(f"cases must declare {SCHEMA_ID}")
    if str(doc.get("version")) != KIT_VERSION:
        raise ValueError(f"cases version must be {KIT_VERSION}")
    return doc


def dump_report(report: dict[str, Any]) -> str:
    return yaml.safe_dump(
        report,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )


def _json_body(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _lower(headers: dict[str, str] | None) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (headers or {}).items()}


def _http(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 20.0,
) -> Observation:
    req = Request(url, data=body, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, str(value))
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return Observation(resp.status, _lower(dict(resp.headers)), _json_body(raw), raw)
    except HTTPError as exc:
        raw = exc.read()
        return Observation(exc.code, _lower(dict(exc.headers)), _json_body(raw), raw)


def http_target(
    url: str,
    token: str,
    *,
    records_url: str | None = None,
    observer_url: str | None = None,
    custody_url: str | None = None,
    approver: str = "kit-approver",
) -> Target:
    base = url.rstrip("/")

    def send(
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        query: dict[str, str] | None = None,
    ) -> Observation:
        target = base + path
        if query:
            target = target + "?" + urlencode(query)
        data = None if body is None else body.encode("utf-8")
        hdrs = dict(headers or {})
        if data is not None and not any(k.lower() == "content-type" for k in hdrs):
            hdrs["Content-Type"] = "application/json"
        return _http(method, target, hdrs, data)

    rec = None
    if records_url:
        def rec() -> list[dict[str, Any]]:
            got = _http("GET", records_url)
            payload = got.body
            rows = payload.get("records")
            return list(rows) if isinstance(rows, list) else []

    obs = None
    if observer_url:
        def obs() -> list[dict[str, Any]]:
            got = _http("GET", observer_url)
            if isinstance(got.body, dict) and isinstance(got.body.get("requests"), list):
                return list(got.body["requests"])
            try:
                rows = json.loads(got.raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return []
            return rows if isinstance(rows, list) else []

    pend = None
    appr = None
    if custody_url:
        custody = custody_url.rstrip("/")

        def pend() -> list[dict[str, Any]]:
            got = _http("GET", custody + "/v1/pending")
            rows = got.body.get("pending")
            return list(rows) if isinstance(rows, list) else []

        def appr(correlation_id: str) -> dict[str, Any]:
            got = _http(
                "POST",
                f"{custody}/v1/decisions/{correlation_id}",
                headers={
                    "Content-Type": "application/json",
                    "X-Approver-Id": approver,
                },
                body=json.dumps({"decision": "approve"}).encode("utf-8"),
            )
            return got.body

    return Target(
        send=send,
        token=token,
        records=rec,
        observer_log=obs,
        pending=pend,
        approve=appr,
    )


def _ids(records: list[dict[str, Any]]) -> set[str]:
    return {str(r.get("id") or r.get("correlationId") or "") for r in records}


def _new_records(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = _ids(before)
    out = []
    for row in after:
        key = str(row.get("id") or row.get("correlationId") or "")
        if key and key in seen:
            continue
        if row in before:
            continue
        out.append(row)
    if out:
        return out
    return after[len(before):]


def _is_decision(row: dict[str, Any]) -> bool:
    schema = str(row.get("ctierSchema") or "")
    return schema.startswith("decision-record/")


def _is_attempt(row: dict[str, Any]) -> bool:
    schema = str(row.get("ctierSchema") or "")
    return schema.startswith("attempt-record/")


def _schema_of(row: dict[str, Any], kind: str) -> bool:
    if kind == "decision":
        return _is_decision(row)
    if kind == "attempt":
        return _is_attempt(row)
    return str(row.get("ctierSchema") or "").startswith(f"{kind}-record/")


def _observer_headers(entry: dict[str, Any] | None) -> dict[str, str]:
    if not entry:
        return {}
    return _lower(entry.get("headers") or {})


def _contains_secret(obj: Any, secret: str) -> bool:
    if not secret:
        return False
    return secret in json.dumps(obj, default=str)


def _inconclusive_reason(case: dict[str, Any], obs: Observation) -> str | None:
    """When the target's answer does not distinguish conformance.

    The case ran. What came back is consistent with both a pass and
    with something the kit cannot see (for C12: a path that was
    never routed, versus a routed path with no assignment).
    """
    rule = case.get("inconclusiveWhen") or {}
    if not rule:
        return None
    if "status" in rule and obs.status != rule["status"]:
        return None
    return (
        rule.get("reason")
        or "target response does not distinguish conformance from what the kit cannot see"
    )


def _evaluate(case: dict[str, Any], obs: Observation, target: Target,
              before_records: list[dict[str, Any]] | None,
              before_observer: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    expect = case.get("expect") or {}
    caps = target.capabilities()

    def fail(field: str, expected: Any, observed: Any) -> None:
        failures.append({"field": field, "expected": expected, "observed": observed})

    status = obs.status
    if "status" in expect and status != expect["status"]:
        fail("status", expect["status"], status)
    if "statusNot" in expect and status in expect["statusNot"]:
        fail("statusNot", expect["statusNot"], status)
    if "statusIn" in expect and status not in expect["statusIn"]:
        fail("statusIn", expect["statusIn"], status)

    body = obs.body
    for key, wanted in (expect.get("body") or {}).items():
        if body.get(key) != wanted:
            fail(f"body.{key}", wanted, body.get(key))
    for key in expect.get("bodyAbsent") or []:
        if key in body:
            fail(f"bodyAbsent.{key}", "absent", body.get(key))
    for key in expect.get("headerAbsent") or []:
        if key.lower() in obs.headers:
            fail(f"header.{key}", "absent", obs.headers.get(key.lower()))

    if expect.get("higherClass"):
        if status == 202:
            if body.get("status") != "pending_authorization":
                fail("higherClass", "pending_authorization", body.get("status"))
        elif status == 403:
            if body.get("status") != "provisioning_defect":
                fail("higherClass", "provisioning_defect", body.get("status"))
        else:
            fail("higherClass", [202, 403], status)

    if expect.get("pairing"):
        action = body.get("agentAction")
        header = obs.headers.get("x-agent-action")
        named = status == 202 or (
            status == 423 and action == "halt_and_hand_off"
        )
        if named:
            if header != action:
                fail("pairing", action, header)
        elif header is not None and header != action:
            fail("pairing", action, header)

    record_exp = expect.get("record")
    if record_exp:
        if "records" not in caps:
            if "records" in (case.get("requires") or []):
                pass
        else:
            after = target.records() if target.records else []
            written = _new_records(before_records or [], after)
            if "present" in record_exp:
                kind = record_exp["present"]
                found = [r for r in written if _schema_of(r, kind)]
                if not found:
                    fail("record.present", kind, [r.get("ctierSchema") for r in written] or "none")
                elif kind == "attempt":
                    fields = record_exp.get("attempt") or {}
                    row = found[-1]
                    if "appliedTier" in fields:
                        wanted = fields["appliedTier"]
                        got = row.get("appliedTier")
                        if wanted is None and got is not None:
                            fail("record.attempt.appliedTier", None, got)
                        elif wanted is not None and got != wanted:
                            fail("record.attempt.appliedTier", wanted, got)
                    if "reason" in fields and row.get("reason") != fields["reason"]:
                        fail("record.attempt.reason", fields["reason"], row.get("reason"))
            if record_exp.get("absent"):
                kind = record_exp["absent"]
                found = [r for r in written if _schema_of(r, kind)]
                if found:
                    fail("record.absent", f"no {kind}", found[0].get("ctierSchema"))

    observer_exp = expect.get("observer")
    if observer_exp and "observer" in caps and target.observer_log:
        after = target.observer_log()
        new = after[len(before_observer or []):]
        last = new[-1] if new else None
        hdrs = _observer_headers(last)
        if observer_exp.get("unreached"):
            path = case["send"]["path"]
            method = case["send"]["method"]
            hit = [
                e for e in new
                if str(e.get("method") or "").upper() == method
                and str(e.get("path") or "").startswith(path)
            ]
            if hit:
                fail("observer.unreached", "no backend hit", hit[-1].get("path"))
        for name in observer_exp.get("absent") or []:
            if name.lower() in hdrs:
                fail(f"observer.absent.{name}", "absent", hdrs.get(name.lower()))
        for name in observer_exp.get("present") or []:
            if not hdrs.get(name.lower()):
                fail(f"observer.present.{name}", "present", hdrs.get(name.lower()))
        for name, forbidden in (observer_exp.get("notEquals") or {}).items():
            if hdrs.get(name.lower()) == str(forbidden):
                fail(f"observer.notEquals.{name}", f"not {forbidden}", hdrs.get(name.lower()))

    pending_exp = expect.get("pending")
    if pending_exp and "pending" in caps and target.pending:
        queue = target.pending()
        cid = body.get("correlationId")
        if pending_exp.get("correlationAbsent"):
            # The named handover carries no correlation identifier.
            # Checking the pending list only when one came back passes
            # without observing that absence.
            if cid:
                fail("pending.correlationAbsent", "no correlation identifier", cid)
        if pending_exp.get("noCredential"):
            match = [p for p in queue if cid and p.get("correlationId") == cid] or queue[-1:]
            item = match[-1] if match else {}
            blob = _lower({k: str(v) for k, v in item.items() if v is not None})
            cred = [k for k in blob if k.lower() in CREDENTIAL_KEYS]
            headers = item.get("headers") or {}
            if isinstance(headers, dict):
                cred.extend(k for k in headers if str(k).lower() in CREDENTIAL_KEYS)
            if cred:
                fail("pending.noCredential", "no credential", cred)
            if _contains_secret(item, target.token):
                fail("pending.noCredential", "no bearer material", "token present")

    then = case.get("then")
    if then and then.get("approve"):
        if "approve" not in caps or target.approve is None:
            fail("then.approve", "approve capability", "absent")
            return failures
        cid = body.get("correlationId")
        if not cid:
            fail("then.approve", "correlationId", None)
            return failures
        target.approve(str(cid))
        obs_exp = then.get("observer") or {}
        if obs_exp and "observer" in caps and target.observer_log:
            after = target.observer_log()
            new = after[len(before_observer or []):]
            method = str(obs_exp.get("method") or "").upper()
            needle = str(obs_exp.get("pathContains") or "")
            hits = [
                e for e in new
                if (not method or str(e.get("method") or "").upper() == method)
                and (not needle or needle in str(e.get("path") or ""))
            ]
            count = obs_exp.get("count")
            if count is not None and len(hits) != count:
                fail("then.observer.count", count, len(hits))
            if not hits:
                fail("then.observer", "execute hop", "none")
            else:
                hop = hits[-1]
                hop_hdrs = _observer_headers(hop)
                if obs_exp.get("authorizationNotAgent") and target.token:
                    auth = hop_hdrs.get("authorization") or ""
                    if target.token in auth:
                        fail("then.observer.authorization", "not the caller", "caller token")
    return failures


def run_kit(
    doc: dict[str, Any],
    target: Target,
    *,
    level: str,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    caps = target.capabilities()
    rows: list[dict[str, Any]] = []
    n = 0
    for case in doc.get("cases") or []:
        n += 1
        cid = case["id"]
        klass = case.get("class")
        if klass == "generation":
            rows.append({
                "id": cid,
                "criterion": case.get("criterion"),
                "result": "skipped",
                "reason": SKIP_COVERED_AT_GENERATION,
            })
            continue
        need_level = str(case.get("level") or "any")
        if need_level not in ("any", str(level)):
            rows.append({
                "id": cid,
                "criterion": case.get("criterion"),
                "result": "skipped",
                "reason": SKIP_NOT_APPLICABLE_AT_LEVEL,
            })
            continue
        missing = [c for c in (case.get("requires") or []) if c not in caps]
        if missing:
            rows.append({
                "id": cid,
                "criterion": case.get("criterion"),
                "result": "skipped",
                "reason": SKIP_REQUIRES_CAPABILITY,
            })
            continue
        send = case.get("send") or {}
        before_records = target.records() if target.records else None
        before_observer = target.observer_log() if target.observer_log else None
        hdrs = {
            "Authorization": f"Bearer {target.token}",
            "X-Agent-Id": "kit-agent",
            "X-Task-Id": f"kit-{cid}-{n}",
        }
        hdrs.update(extra_headers or {})
        hdrs.update(send.get("headers") or {})
        obs = target.send(
            send.get("method") or "GET",
            send.get("path") or "/",
            headers=hdrs,
            body=send.get("body"),
            query=send.get("query"),
        )
        ambiguous = _inconclusive_reason(case, obs)
        if ambiguous:
            rows.append({
                "id": cid,
                "criterion": case.get("criterion"),
                "result": "inconclusive",
                "reason": ambiguous,
                "observed": {
                    "status": obs.status,
                    "body": {
                        k: obs.body.get(k)
                        for k in ("status", "agentAction", "correlationId", "retryable")
                        if k in obs.body
                    },
                },
            })
            continue
        failures = _evaluate(case, obs, target, before_records, before_observer)
        row: dict[str, Any] = {
            "id": cid,
            "criterion": case.get("criterion"),
            "result": "failed" if failures else "passed",
        }
        if failures:
            row["observed"] = {
                "status": obs.status,
                "body": {k: obs.body.get(k) for k in ("status", "agentAction", "correlationId", "retryable") if k in obs.body},
                "failures": failures,
            }
        rows.append(row)

    passed = sum(1 for r in rows if r["result"] == "passed")
    failed = sum(1 for r in rows if r["result"] == "failed")
    skipped = sum(1 for r in rows if r["result"] == "skipped")
    inconclusive = sum(1 for r in rows if r["result"] == "inconclusive")
    return {
        "ctierSchema": REPORT_ID,
        "version": KIT_VERSION,
        "level": str(level),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "inconclusive": inconclusive,
        "ran": passed + failed + inconclusive,
        "cases": rows,
    }


def parse_args(argv: list[str] | None = None):
    import argparse
    import os

    parser = argparse.ArgumentParser(
        prog="python -m ctier.kit",
        description="Run conformance-kit/1.1 against a running gateway.",
    )
    parser.add_argument("--url", default=os.environ.get("GATEWAY_URL"), help="Gateway base URL")
    parser.add_argument("--token", default=os.environ.get("GATEWAY_TOKEN"), help="Bearer token")
    parser.add_argument("--records", default=os.environ.get("KIT_RECORDS"), help="GET URL that returns {records: [...]}")
    parser.add_argument("--observer", default=os.environ.get("KIT_OBSERVER"), help="GET URL of the backend request log")
    parser.add_argument("--custody", default=os.environ.get("KIT_CUSTODY"), help="Approval service base URL")
    parser.add_argument("--level", default=os.environ.get("KIT_LEVEL", "3"), help="Deployment level: 2 or 3")
    parser.add_argument("--out", default=os.environ.get("KIT_OUT", "kit-result.yaml"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.url or not args.token:
        raise SystemExit("set --url and --token (or GATEWAY_URL and GATEWAY_TOKEN)")
    target = http_target(
        args.url,
        args.token,
        records_url=args.records,
        observer_url=args.observer,
        custody_url=args.custody,
    )
    report = run_kit(load_cases(), target, level=str(args.level))
    text = dump_report(report)
    Path(args.out).write_text(text, encoding="utf-8")
    return 1 if report["failed"] else 0
