"""runtime-suite/0.3.0-draft: format, skips, observer-shaped fixtures. No sockets."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from ctier.boundary import SCHEMA_ID, SUITE_PATH, BoundaryFixture, Observation, load_suite, run_suite
from ctier.boundary.probe import attach_probe
from ctier.boundary.runner import SCHEMA_PATH
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_fragment import load_fixture

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
FINDINGS = Path(__file__).resolve().parents[1] / "docs" / "findings" / "19.md"


def _obs(headers: dict[str, str], *, status: int = 200) -> Observation:
    return Observation(status=status, response_headers={}, observer_headers=headers)


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_suite_loads_and_declares_the_draft_id():
    suite = load_suite()
    assert suite["ctierSchema"] == SCHEMA_ID
    assert SCHEMA_ID == "runtime-suite/0.3.0-draft"
    ids = [c["id"] for c in suite["cases"]]
    assert 11 <= len(ids) <= 20
    assert "strip-precedence" in ids
    assert "forged-tier-not-surviving" in ids
    unknown = next(c for c in suite["cases"] if c["id"] == "unknown-path-refused-undetermined")
    gap = next(c for c in suite["cases"] if c["id"] == "induced-gap-is-detected")
    assert gap["expect"]["induceGap"] is True
    assert gap["send"]["repeat"] == 8
    assert unknown["expect"]["status"] == 423
    assert unknown["expect"]["recorded"] == [
        {
            "type": "attempt",
            "appliedTier": None,
            "reason": "unassigned",
            "absent": ["declaredTier"],
        },
    ]
    assert unknown["expect"]["unrecorded"] == [{"type": "decision"}]
    assert SUITE_PATH.is_file()
    blob = yaml.safe_dump(suite)
    for forbidden in ("applied_tier", "disposition", "withhold", "refuse-and-suspend"):
        assert forbidden not in blob
    for case in suite["cases"]:
        assert "status" in case["expect"]
    derived = next(c for c in suite["cases"] if c["id"] == "derived-idempotency-present")
    assert derived["expect"]["notEquals"]["idempotency-key"] == "agent-idempotency"
    assert "tier-4-instruction-agrees" in ids
    assert "provisioning-instruction-agrees" in ids


def test_expect_requires_status():
    suite = load_suite()
    case = dict(suite["cases"][0])
    expect = dict(case["expect"])
    expect.pop("status")
    case["expect"] = expect
    doc = {"ctierSchema": SCHEMA_ID, "cases": [case]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(_schema()).validate(doc)


def test_missing_capability_is_skipped_not_passed():
    suite = load_suite()

    def send(_m, _p, _h, body=None):
        raise AssertionError("skipped cases must not send")

    report = run_suite(
        suite,
        BoundaryFixture(capabilities=set(), send=send, target="stub", mode="bundle", estate="stub"),
    )
    assert report["passed"] == 0
    assert report["failed"] == 0
    assert report["skipped"] == len(suite["cases"])
    for row in report["cases"]:
        assert row["result"] == "skipped"
        reason = row["skipReason"]
        assert reason.startswith("missing-capability:") or reason.startswith("when.deployment:")


def test_skip_counts_do_not_blur_with_pass():
    suite = load_suite()

    def send(_m, _p, _h, body=None):
        return _obs({
            "x-ctier-correlation-id": "cid-1",
            "idempotency-key": "hmac-1",
        })

    report = run_suite(
        suite,
        BoundaryFixture(
            capabilities={"observer", "recordSource"},
            send=send,
            decision_for=lambda cid: {
                "correlationId": cid,
                "idempotencyKey": "hmac-1",
            },
            target="stub",
            mode="bundle",
            estate="stub",
        ),
    )
    by_id = {c["id"]: c for c in report["cases"]}
    assert by_id["strip-precedence"]["result"] == "skipped"
    assert by_id["join-key-equals-decision"]["result"] == "passed"
    assert by_id["forged-tier-not-surviving"]["result"] == "passed"
    assert by_id["derived-idempotency-present"]["result"] == "passed"
    assert by_id["custody-unavailable-records-attempt"]["result"] == "skipped"
    assert report["skipped"] >= 1
    assert report["passed"] + report["failed"] + report["skipped"] == len(suite["cases"])
    assert report["skipped"] >= 1
    assert report["passed"] == len(suite["cases"]) - report["skipped"] - report["failed"]
    assert "estate" in report


def test_absent_present_equals_against_a_fake_observer():
    suite = load_suite()
    sent = []

    def send(method, path, headers, body=None):
        sent.append((method, path, headers))
        out = {
            "x-ctier-correlation-id": "cid-1",
            "idempotency-key": "hmac-1",
        }
        return _obs(out)

    report = run_suite(
        suite,
        BoundaryFixture(
            capabilities={"observer", "probe", "recordSource"},
            send=send,
            decision_for=lambda cid: {"correlationId": cid, "idempotencyKey": "hmac-1"},
            target="stub",
            mode="bundle",
            estate="stub",
        ),
    )
    assert report["failed"] == 0, report
    by_id = {c["id"]: c for c in report["cases"]}
    assert by_id["strip-precedence"]["result"] == "passed"
    assert report["passed"] + report["failed"] + report["skipped"] == len(suite["cases"])
    header = [c for c in suite["cases"] if not c.get("when")]
    assert report["passed"] == len(header)
    assert sent


def test_equals_fails_when_record_disagrees():
    suite = {"ctierSchema": SCHEMA_ID, "cases": [c for c in load_suite()["cases"] if c["id"] == "join-key-equals-decision"]}

    def send(_m, _p, _h, body=None):
        return _obs({"x-ctier-correlation-id": "cid-1"})

    report = run_suite(
        suite,
        BoundaryFixture(
            capabilities={"observer", "recordSource"},
            send=send,
            decision_for=lambda _cid: {"correlationId": "other"},
        ),
    )
    assert report["passed"] == 0
    assert report["failed"] == 1
    assert report["skipped"] == 0


def test_not_equals_fails_when_the_forged_value_survives():
    suite = {
        "ctierSchema": SCHEMA_ID,
        "cases": [{
            "id": "forged-tier",
            "requires": ["observer"],
            "send": {"method": "GET", "path": "/accounts/12345/balance", "headers": {"x-ctier-tier": "9"}},
            "expect": {"status": 200, "notEquals": {"x-ctier-tier": "9"}},
        }],
    }

    def send(_m, _p, _h, body=None):
        return _obs({"x-ctier-tier": "9"})

    report = run_suite(suite, BoundaryFixture(capabilities={"observer"}, send=send))
    assert report["failed"] == 1
    assert report["passed"] == 0
    assert "notEquals" in report["cases"][0]["failures"][0]


def test_not_equals_passes_when_the_name_is_re_emitted_differently():
    suite = {
        "ctierSchema": SCHEMA_ID,
        "cases": [{
            "id": "forged-tier",
            "requires": ["observer"],
            "send": {"method": "GET", "path": "/accounts/12345/balance", "headers": {"x-ctier-tier": "9"}},
            "expect": {"status": 200, "notEquals": {"x-ctier-tier": "9"}},
        }],
    }

    def send(_m, _p, _h, body=None):
        return _obs({"x-ctier-tier": "2"})

    report = run_suite(suite, BoundaryFixture(capabilities={"observer"}, send=send))
    assert report["passed"] == 1
    assert report["failed"] == 0


def test_not_equals_passes_when_the_name_is_absent():
    suite = {
        "ctierSchema": SCHEMA_ID,
        "cases": [{
            "id": "forged-tier",
            "requires": ["observer"],
            "send": {"method": "GET", "path": "/accounts/12345/balance", "headers": {"x-ctier-tier": "9"}},
            "expect": {"status": 200, "notEquals": {"x-ctier-tier": "9"}},
        }],
    }

    def send(_m, _p, _h, body=None):
        return _obs({})

    report = run_suite(suite, BoundaryFixture(capabilities={"observer"}, send=send))
    assert report["passed"] == 1


def test_refused_request_does_not_pass_absent_vacuously():
    suite = {
        "ctierSchema": SCHEMA_ID,
        "cases": [{
            "id": "ns",
            "requires": ["observer"],
            "send": {"method": "GET", "path": "/x", "headers": {"x-ctier-foo": "forged"}},
            "expect": {"status": 200, "absent": ["x-ctier-foo"]},
        }],
    }

    def send(_m, _p, _h, body=None):
        return _obs({}, status=401)

    report = run_suite(suite, BoundaryFixture(capabilities={"observer"}, send=send))
    assert report["failed"] == 1
    assert report["passed"] == 0
    assert report["cases"][0]["failures"][0].startswith("status:")


def test_kong_and_apisix_probe_injection_is_declarative():
    qualified, _ = compose(REFERENCE, [], NOW)
    for target in ("kong", "apisix"):
        files = generate(qualified, target=target)
        before = attach_probe(files, target, position="before")
        after = attach_probe(files, target, position="after")
        key = "kong.yaml" if target == "kong" else "apisix.yaml"
        assert "x-boundary-probe" in before[key]
        assert "x-boundary-probe" in after[key]
        if target == "kong":
            assert "pre-function" in before[key]
            assert "post-function" in after[key]
        else:
            assert "30000" in before[key]


def test_fragment_files_still_merge_with_a_probe_attached():
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture("kong")
    files = generate(qualified, target="kong", mode="fragment", existing=existing)
    probed = attach_probe(files, "kong", position="before")
    deck = yaml.safe_load(probed["kong.yaml"])
    names = {p["name"] for p in deck["plugins"]}
    assert "pre-function" in names
    assert "cors" in names
    assert "ctier" in names


def test_draft_documents_not_equals_and_rejects_equals_compiled_tier():
    readme = (Path(__file__).resolve().parents[1] / "ctier" / "boundary" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "notEquals" in readme
    assert "classification corpus" in readme.lower()
    assert "equals-the-compiled-tier" in readme or "compiled tier" in readme
    assert "how a case is evaluated" in readme
    assert "internal state" in readme
    assert "pairing" in readme
    schema = _schema()
    kinds = set(schema["$defs"]["expect"]["properties"])
    assert "recorded" in kinds
    assert "unrecorded" in kinds
    assert "status" in schema["$defs"]["expect"]["required"]


def test_draft_specifies_the_result_record_and_its_estate():
    readme = (Path(__file__).resolve().parents[1] / "ctier" / "boundary" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "## Report — `runtime-report/0.1.0-draft`" in readme
    assert "A precedence result is only meaningful against a named estate." in readme
    for field in ("ctierSchema", "target", "mode", "estate", "passed", "failed", "skipped", "cases"):
        assert f"`{field}`" in readme
    report = run_suite(
        {"ctierSchema": SCHEMA_ID, "cases": [{
            "id": "ns",
            "requires": ["observer"],
            "send": {"method": "GET", "path": "/x"},
            "expect": {"status": 200, "absent": ["x-ctier-foo"]},
        }]},
        BoundaryFixture(
            capabilities={"observer"},
            send=lambda _m, _p, _h, body=None: _obs({}),
            target="kong",
            mode="fragment",
            estate="existing/kong.yaml",
        ),
    )
    assert report["ctierSchema"] == "runtime-report/0.1.0-draft"
    assert report["estate"] == "existing/kong.yaml"
    assert report["target"] == "kong"
    assert report["mode"] == "fragment"


def test_apigee_exclusion_is_recorded_when_findings_exist():


    readme = (Path(__file__).resolve().parents[1] / "ctier" / "boundary" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "Apigee" in readme
    assert "no local runtime" in readme.lower()
    if FINDINGS.is_file():
        text = FINDINGS.read_text(encoding="utf-8")
        assert "Apigee" in text
        assert "excluded" in text.lower()


DIGEST = "sha256:" + ("ab" * 32)


def _attempt(**kwargs):
    from ctier.ledger.sink import log_attempt_record

    rec = log_attempt_record(
        operation_anchor="updateCommunicationPreferences",
        declared_tier=3,
        deployment_digest=DIGEST,
        reason="custody-unavailable",
        agent_id="agent-a",
        correlation_scope="task-1",
        record_id=kwargs.get("record_id", "att-1"),
        timestamp="2026-09-16T12:00:00Z",
    )
    rec.update({k: v for k, v in kwargs.items() if k != "record_id"})
    return rec


def test_recorded_presence_and_absence():
    from ctier.boundary.runner import match_recorded, match_unrecorded

    rec = _attempt()
    want = {"type": "attempt", "appliedTier": None, "reason": "custody-unavailable"}
    assert match_recorded(want, [rec]) is None
    assert match_unrecorded({"type": "outcome"}, [rec]) is None
    assert match_unrecorded({"type": "attempt"}, [rec]).startswith("unrecorded attempt:")
    assert match_recorded({"type": "attempt"}, []).startswith("recorded attempt: none written")


def test_unassigned_refusal_with_declared_tier_four_fails_even_when_schema_valid():
    """A 0.3.0 Attempt that still writes 4 is valid. It is not an unassigned miss."""
    from ctier.boundary.runner import match_recorded
    from ctier.ledger.records import validate_record

    rec = _attempt(reason="unassigned")
    rec["declaredTier"] = 4
    validate_record(rec)
    err = match_recorded(
        {
            "type": "attempt",
            "appliedTier": None,
            "reason": "unassigned",
            "absent": ["declaredTier"],
        },
        [rec],
    )
    assert err is not None
    assert "declaredTier: present 4" in err

    omitted = _attempt(reason="unassigned")
    omitted.pop("declaredTier", None)
    validate_record(omitted)
    assert match_recorded(
        {
            "type": "attempt",
            "appliedTier": None,
            "reason": "unassigned",
            "absent": ["declaredTier"],
        },
        [omitted],
    ) is None


def test_recorded_distinguishes_schema_invalid_from_wrong_value():
    from ctier.boundary.runner import match_recorded

    rec = _attempt()
    rec["appliedTier"] = 4
    err = match_recorded(
        {"type": "attempt", "appliedTier": None, "reason": "custody-unavailable"},
        [rec],
    )
    assert err is not None
    assert "schema-invalid" in err

    rec2 = _attempt(record_id="att-2")
    rec2["reason"] = "other"
    err2 = match_recorded(
        {"type": "attempt", "appliedTier": None, "reason": "custody-unavailable"},
        [rec2],
    )
    assert err2 is not None
    assert "schema-invalid" not in err2
    assert "reason:" in err2


def test_recorded_case_runs_against_a_sink_fixture():
    rec = _attempt()
    calls = {"n": 0}

    def send(_m, _p, _h, body=None):
        return _obs({}, status=503)

    def fetch():
        calls["n"] += 1
        return [] if calls["n"] == 1 else [rec]

    report = run_suite(
        {
            "ctierSchema": SCHEMA_ID,
            "cases": [{
                "id": "down",
                "requires": ["recordSource", "custodyControl"],
                "when": {"deployment": "level-3", "custody": "unavailable"},
                "send": {
                    "method": "PUT",
                    "path": "/customers/12345/preferences/communication",
                    "repeat": 2,
                },
                "expect": {
                    "status": 503,
                    "recorded": [{
                        "type": "attempt",
                        "appliedTier": None,
                        "reason": "custody-unavailable",
                    }],
                    "unrecorded": [{"type": "outcome"}],
                },
            }],
        },
        BoundaryFixture(
            capabilities={"recordSource", "custodyControl"},
            send=send,
            deployment="level-3",
            fetch_records=fetch,
            set_custody_available=lambda _up: None,
        ),
    )
    assert report["passed"] == 1, report


def test_record_source_contract_is_specified_and_log_parse_is_the_same_array():
    from ctier.boundary.records import records_from_log, records_from_ledger_body

    readme = (Path(__file__).resolve().parents[1] / "ctier" / "boundary" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "record-source/0.1.0-draft" in readme
    assert "GET {recordBase}/records" in readme
    assert "Not a query language" in readme
    rec = _attempt()
    line = f'2026/09/18 notice: [ctier-attempt] {json.dumps(rec)}'
    parsed = records_from_log(line)
    assert parsed == [rec]
    wrapped = records_from_ledger_body({"records": [dict(rec, type="attempt")]})
    assert wrapped[0]["id"] == rec["id"]


def test_instruction_pairing_fails_when_header_and_body_disagree():
    from ctier.boundary.runner import evaluate_instruction_pairing

    obs = Observation(
        status=423,
        response_headers={"x-agent-action": "halt"},
        observer_headers={},
        body={"status": "agent_suspended", "agentAction": "halt_and_hand_off"},
    )
    err = evaluate_instruction_pairing(obs)
    assert err
    assert "agree X-Agent-Action" in err[0]
    assert "halt" in err[0]
    assert "halt_and_hand_off" in err[0]


def test_instruction_pairing_passes_when_they_match():
    from ctier.boundary.runner import evaluate_instruction_pairing

    obs = Observation(
        status=423,
        response_headers={"X-Agent-Action": "halt_and_hand_off"},
        observer_headers={},
        body={"agentAction": "halt_and_hand_off"},
    )
    assert evaluate_instruction_pairing(obs) == []


def test_instruction_pairing_does_not_treat_absence_as_a_conflict():
    from ctier.boundary.runner import evaluate_instruction_pairing

    obs = Observation(
        status=423,
        response_headers={},
        observer_headers={},
        body={"agentAction": "halt"},
    )
    assert evaluate_instruction_pairing(obs) == []


def test_instruction_pairing_requires_the_202_mirror():
    from ctier.boundary.runner import evaluate_instruction_pairing

    missing = Observation(
        status=202,
        response_headers={},
        observer_headers={},
        body={"agentAction": "continue_task_without_this_step"},
    )
    err = evaluate_instruction_pairing(missing)
    assert err
    assert "202" in err[0]
    matched = Observation(
        status=202,
        response_headers={"x-agent-action": "continue_task_without_this_step"},
        observer_headers={},
        body={"agentAction": "continue_task_without_this_step"},
    )
    assert evaluate_instruction_pairing(matched) == []


def test_instruction_pairing_requires_the_c9_mirror():
    from ctier.boundary.runner import evaluate_instruction_pairing

    missing = Observation(
        status=423,
        response_headers={},
        observer_headers={},
        body={"agentAction": "halt_and_hand_off"},
    )
    err = evaluate_instruction_pairing(missing)
    assert err
    assert "423" in err[0]
    matched = Observation(
        status=423,
        response_headers={"x-agent-action": "halt_and_hand_off"},
        observer_headers={},
        body={"agentAction": "halt_and_hand_off"},
    )
    assert evaluate_instruction_pairing(matched) == []


def test_suite_runs_pairing_against_a_conflicting_observation():
    def send(_m, _p, _h, body=None):
        return Observation(
            status=423,
            response_headers={"x-agent-action": "halt"},
            observer_headers={},
            body={"agentAction": "halt_and_hand_off"},
        )

    report = run_suite(
        {
            "ctierSchema": SCHEMA_ID,
            "cases": [{
                "id": "tier-4-instruction-agrees",
                "send": {"method": "POST", "path": "/payments", "body": "{}"},
                "expect": {"status": 423},
            }],
        },
        BoundaryFixture(capabilities=set(), send=send, deployment="level-2"),
    )
    assert report["failed"] == 1
    assert report["passed"] == 0
    assert "agree" in report["cases"][0]["failures"][0]


