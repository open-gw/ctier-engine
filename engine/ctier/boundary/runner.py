# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Load and run runtime-suite/0.3.0-draft."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import jsonschema
import yaml

from ctier.identifiers import HEADER_AGENT_ACTION, required_instruction_headers
from ctier.ledger.records import validate_record

from .records import detect_gaps

DIR = Path(__file__).resolve().parent
SUITE_PATH = DIR / "suite.yaml"
SCHEMA_PATH = DIR / "suite.schema.json"
SCHEMA_ID = "runtime-suite/0.3.0-draft"
REPORT_ID = "runtime-report/0.1.0-draft"
CAPABILITIES = frozenset({
    "observer", "probe", "recordSource", "execute", "custodyControl",
})
DECISION_POINTERS = {
    "decision.correlationId": "correlationId",
    "decision.idempotencyKey": "idempotencyKey",
}
RECORD_SCHEMAS = {
    "attempt": "attempt-record/0.3.0",
    "decision": "decision-record/0.2.0",
    "outcome": "outcome-record/0.1.0",
}


@dataclass
class Observation:
    status: int
    response_headers: dict[str, str]
    observer_headers: dict[str, str]
    body: dict[str, Any] = field(default_factory=dict)


@dataclass
class BoundaryFixture:
    capabilities: set[str]
    send: Callable[..., Observation]
    decision_for: Callable[[str], dict[str, Any] | None] | None = None
    target: str = ""
    mode: str = ""
    estate: str = ""
    deployment: str = ""
    fetch_records: Callable[[], list[dict[str, Any]]] | None = None
    set_custody_available: Callable[[bool], None] | None = None
    approve: Callable[[Observation], None] | None = None


@dataclass
class CaseResult:
    id: str
    result: str
    skipReason: str | None = None
    failures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"id": self.id, "result": self.result}
        if self.skipReason:
            out["skipReason"] = self.skipReason
        if self.failures:
            out["failures"] = self.failures
        return out


def load_suite(path: Path | None = None) -> dict[str, Any]:
    text = (path or SUITE_PATH).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(doc)
    return doc


def _lower(headers: dict[str, str] | None) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (headers or {}).items()}


def _requires(case: dict[str, Any]) -> set[str]:
    needed = set(case.get("requires") or [])
    expect = case.get("expect") or {}
    equals = expect.get("equals") or {}
    for pointer in equals.values():
        if str(pointer).startswith("decision."):
            needed.add("recordSource")
    if expect.get("recorded") or expect.get("unrecorded") or expect.get("induceGap"):
        needed.add("recordSource")
    then = case.get("then") or {}
    if then.get("approve"):
        needed.add("execute")
    if then.get("expect"):
        needed.add("recordSource")
    when = case.get("when") or {}
    if when.get("custody") == "unavailable":
        needed.add("custodyControl")
    return needed


def _when_skip(case: dict[str, Any], fixture: BoundaryFixture) -> str | None:
    when = case.get("when") or {}
    wanted = when.get("deployment")
    if wanted and wanted != fixture.deployment:
        return f"when.deployment:{wanted}"
    return None


def _needs_join_key(case: dict[str, Any]) -> bool:
    equals = (case.get("expect") or {}).get("equals") or {}
    return any(str(p).startswith("decision.") for p in equals.values())


def _resolve_pointer(
    pointer: str,
    obs: Observation,
    record: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    if pointer in DECISION_POINTERS:
        if record is None:
            return None, f"no decision record for {pointer}"
        value = record.get(DECISION_POINTERS[pointer])
        if value is None or str(value) == "":
            return None, f"{pointer} empty on decision record"
        return str(value), None
    if pointer.startswith("response."):
        name = pointer[len("response."):].lower()
        value = obs.response_headers.get(name)
        if not value:
            return None, f"{pointer} missing on client response"
        return value, None
    if pointer.startswith("observer."):
        name = pointer[len("observer."):].lower()
        value = obs.observer_headers.get(name)
        if not value:
            return None, f"{pointer} missing at observer"
        return value, None
    return None, f"unknown equals pointer {pointer}"


def envelope_stripped(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out.pop("type", None)
    out.pop("sinkEpoch", None)
    out.pop("sinkSeq", None)
    return out


def record_kind(record: dict[str, Any]) -> str | None:
    schema = record.get("ctierSchema")
    for kind, sid in RECORD_SCHEMAS.items():
        if schema == sid:
            return kind
    typed = record.get("type")
    if typed in RECORD_SCHEMAS:
        return str(typed)
    return None


def _field_mismatch(observed: dict[str, Any], want: dict[str, Any]) -> str | None:
    for key, expected in want.items():
        if key in {"type", "absent"}:
            continue
        got = observed.get(key)
        if got != expected:
            return f"{key}: observed {got!r} != expected {expected!r}"
    for key in want.get("absent") or []:
        if key in observed:
            return f"{key}: present {observed[key]!r} (expected absent)"
    return None


def match_recorded(want: dict[str, Any], written: list[dict[str, Any]]) -> str | None:
    """Presence: None if a schema-valid record matches. Else a failure string."""
    kind = str(want.get("type") or "")
    same_kind = [r for r in written if record_kind(r) == kind]
    if not same_kind:
        return f"recorded {kind}: none written"
    invalid: list[str] = []
    value_miss: list[str] = []
    for raw in same_kind:
        body = envelope_stripped(raw)
        try:
            validate_record(body)
        except (jsonschema.ValidationError, KeyError, ValueError) as exc:
            invalid.append(str(exc).split("\n", 1)[0])
            continue
        miss = _field_mismatch(body, want)
        if miss is None:
            return None
        value_miss.append(miss)
    if invalid and not value_miss:
        return f"recorded {kind}: schema-invalid: {invalid[0]}"
    if value_miss:
        return f"recorded {kind}: {value_miss[0]}"
    return f"recorded {kind}: schema-invalid: {invalid[0]}"


def match_unrecorded(want: dict[str, Any], written: list[dict[str, Any]]) -> str | None:
    kind = str(want.get("type") or "")
    same_kind = [r for r in written if record_kind(r) == kind]
    if same_kind:
        return f"unrecorded {kind}: observed {len(same_kind)}"
    return None


def _response_header(obs: Observation, name: str) -> str | None:
    key = name.lower()
    for raw_name, raw_value in (obs.response_headers or {}).items():
        if str(raw_name).lower() == key:
            value = str(raw_value).strip()
            return value or None
    return None


def evaluate_instruction_pairing(obs: Observation) -> list[str]:
    """Header and body are one fact. Assert the pairing, not presence apart.

    Spec 1.24.0: body agentAction is the identifier, mirrored on
    X-Agent-Action when that header is emitted. C5's named 202
    mechanism and C9's named 423 mechanism require the header.
    Absence on other dispositions is not a defect; a conflicting
    pair is.
    """
    body = obs.body or {}
    if not isinstance(body, dict):
        return []
    action = body.get("agentAction")
    if not isinstance(action, str) or action.strip() == "":
        return []
    action = action.strip()
    header = _response_header(obs, HEADER_AGENT_ACTION)
    failures: list[str] = []
    if header is not None and header != action:
        failures.append(
            f"agree {HEADER_AGENT_ACTION}: header {header!r} != body agentAction {action!r}"
        )
    required = required_instruction_headers(obs.status, action)
    if required and header is None:
        failures.append(
            f"agree {HEADER_AGENT_ACTION}: {obs.status} body carries "
            f"agentAction {action!r} without the header"
        )
    return failures


def _evaluate_headers(case: dict[str, Any], obs: Observation, record: dict[str, Any] | None) -> list[str]:
    expect = case.get("expect") or {}
    headers = obs.observer_headers
    failures: list[str] = []
    for name in expect.get("absent") or []:
        key = name.lower()
        if key in headers and str(headers[key]).strip() != "":
            failures.append(f"absent {name}: observed {headers[key]!r}")
    for name in expect.get("present") or []:
        key = name.lower()
        if key not in headers or str(headers[key]).strip() == "":
            failures.append(f"present {name}: missing at observer")
    for name, pointer in (expect.get("equals") or {}).items():
        key = name.lower()
        left = headers.get(key)
        if not left or str(left).strip() == "":
            failures.append(f"equals {name}: missing at observer")
            continue
        right, err = _resolve_pointer(str(pointer), obs, record)
        if err:
            failures.append(f"equals {name}: {err}")
            continue
        if str(left) != str(right):
            failures.append(f"equals {name}: observer {left!r} != {pointer} {right!r}")
    for name, forbidden in (expect.get("notEquals") or {}).items():
        key = name.lower()
        left = headers.get(key)
        if left is not None and str(left) == str(forbidden):
            failures.append(f"notEquals {name}: observed {left!r}")
    return failures


def induce_and_detect_gap(written: list[dict[str, Any]]) -> str | None:
    """Drop one sequenced record. A reader of the remainder must see a hole.

    Not 'sequence field present'. The test removes a line from the sink
    contents after allocation-and-emit; detect_gaps is the reader.
    """
    sequenced = [
        rec for rec in written
        if rec.get("sinkEpoch") is not None and rec.get("sinkSeq") is not None
    ]
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in sequenced:
        groups.setdefault(str(rec["sinkEpoch"]), []).append(rec)
    target = None
    for recs in groups.values():
        if len(recs) >= 3:
            target = sorted(recs, key=lambda rec: int(rec["sinkSeq"]))
            break
    if target is None:
        return "induceGap: no emitter produced three sequenced records"
    dropped = target[len(target) // 2]
    remaining = [rec for rec in sequenced if str(rec.get("id")) != str(dropped.get("id"))]
    if detect_gaps(remaining):
        return None
    return "induceGap: reader reported no gap after dropping a record"


def _evaluate_records(expect: dict[str, Any], written: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for want in expect.get("recorded") or []:
        err = match_recorded(want, written)
        if err:
            failures.append(err)
    for want in expect.get("unrecorded") or []:
        err = match_unrecorded(want, written)
        if err:
            failures.append(err)
    if expect.get("induceGap"):
        err = induce_and_detect_gap(written)
        if err:
            failures.append(err)
    return failures


def _evaluate(case: dict[str, Any], obs: Observation, record: dict[str, Any] | None,
              written: list[dict[str, Any]]) -> list[str]:
    expect = case.get("expect") or {}
    expected_status = expect.get("status")
    if expected_status is None:
        return ["status: not declared"]
    if obs.status != int(expected_status):
        return [f"status: observed {obs.status} != expected {expected_status}"]
    failures = _evaluate_headers(case, obs, record)
    failures.extend(evaluate_instruction_pairing(obs))
    failures.extend(_evaluate_records(expect, written))
    return failures


def run_suite(suite: dict[str, Any], fixture: BoundaryFixture) -> dict[str, Any]:
    results: list[CaseResult] = []
    have = set(fixture.capabilities)
    for case in suite["cases"]:
        cid = case["id"]
        needed = _requires(case)
        missing = sorted(needed - have)
        if missing:
            results.append(CaseResult(
                id=cid,
                result="skipped",
                skipReason="missing-capability:" + ",".join(missing),
            ))
            continue
        skip_when = _when_skip(case, fixture)
        if skip_when:
            results.append(CaseResult(id=cid, result="skipped", skipReason=skip_when))
            continue
        expect = case.get("expect") or {}
        needs_sink = bool(
            expect.get("recorded") or expect.get("unrecorded")
            or expect.get("induceGap")
            or ((case.get("then") or {}).get("expect"))
        )
        seen_ids: set[str] = set()
        if needs_sink:
            if fixture.fetch_records is None:
                results.append(CaseResult(
                    id=cid, result="failed",
                    failures=["recordSource: no fetch_records"],
                ))
                continue
            seen_ids = {
                str(r.get("id")) for r in fixture.fetch_records() if r.get("id")
            }
        send = case.get("send") or {}
        headers = dict(send.get("headers") or {})
        repeat = int(send.get("repeat") or 1)
        when = case.get("when") or {}
        custody_down = when.get("custody") == "unavailable"
        if custody_down:
            if fixture.set_custody_available is None:
                results.append(CaseResult(
                    id=cid, result="failed",
                    failures=["custodyControl: no set_custody_available"],
                ))
                continue
            fixture.set_custody_available(False)
        try:
            obs = None
            for _ in range(repeat):
                obs = fixture.send(
                    str(send["method"]),
                    str(send["path"]),
                    headers,
                    body=send.get("body"),
                )
        finally:
            if custody_down and fixture.set_custody_available is not None:
                fixture.set_custody_available(True)
        assert obs is not None
        written: list[dict[str, Any]] = []
        if needs_sink and fixture.fetch_records is not None:
            written = [
                r for r in fixture.fetch_records()
                if r.get("id") and str(r.get("id")) not in seen_ids
            ]
        record = None
        if _needs_join_key(case):
            join = obs.observer_headers.get("x-ctier-correlation-id")
            if not join or fixture.decision_for is None:
                results.append(CaseResult(
                    id=cid,
                    result="failed",
                    failures=["recordSource: no join key at observer"],
                ))
                continue
            record = fixture.decision_for(join)
            if record is None:
                results.append(CaseResult(
                    id=cid,
                    result="failed",
                    failures=[f"recordSource: no decision for {join}"],
                ))
                continue
        failures = _evaluate(case, obs, record, written)
        then = case.get("then") or {}
        if then.get("approve") and not failures:
            if fixture.approve is None:
                failures.append("execute: no approve hook")
            else:
                fixture.approve(obs)
                if needs_sink and fixture.fetch_records is not None:
                    written = [
                        r for r in fixture.fetch_records()
                        if r.get("id") and str(r.get("id")) not in seen_ids
                    ]
                failures.extend(_evaluate_records(then.get("expect") or {}, written))
        if failures:
            results.append(CaseResult(id=cid, result="failed", failures=failures))
        else:
            results.append(CaseResult(id=cid, result="passed"))
    passed = sum(1 for r in results if r.result == "passed")
    failed = sum(1 for r in results if r.result == "failed")
    skipped = sum(1 for r in results if r.result == "skipped")
    return {
        "ctierSchema": REPORT_ID,
        "target": fixture.target,
        "mode": fixture.mode,
        "estate": fixture.estate,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "cases": [r.as_dict() for r in results],
    }


def dump_report(report: dict[str, Any]) -> str:
    return yaml.safe_dump(report, sort_keys=False, allow_unicode=True)
