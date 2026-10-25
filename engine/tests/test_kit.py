"""conformance-kit/1.1. Offline. A connect is a failure."""
from __future__ import annotations

from pathlib import Path

from ctier.kit import (
    KIT_VERSION,
    SCHEMA_ID,
    SKIP_COVERED_AT_GENERATION,
    SKIP_NOT_APPLICABLE_AT_LEVEL,
    SKIP_REASONS,
    SKIP_REQUIRES_CAPABILITY,
    Observation,
    Target,
    load_cases,
    run_kit,
)
from ctier.kit.runner import dump_report

ENGINE = Path(__file__).resolve().parents[1]
CASES_MD = ENGINE / "docs" / "kit" / "cases.md"
OBS_MD = ENGINE / "docs" / "kit" / "observability.md"
CASES_YAML = ENGINE / "ctier" / "kit" / "cases.yaml"

MECHANISM = (
    "kong", "apisix", "plugin", "priority",
    "fault-injection", "global_rules", "pre-function", "lua",
)

CRITERIA = tuple(f"C{i}" for i in range(1, 17))


def _obs(status: int, body: dict | None = None, headers: dict | None = None) -> Observation:
    return Observation(status, {k.lower(): v for k, v in (headers or {}).items()}, body or {})


def test_kit_version_is_frozen_at_1_1():
    assert KIT_VERSION == "1.1"
    assert SCHEMA_ID == "conformance-kit/1.1"
    doc = load_cases()
    assert doc["ctierSchema"] == SCHEMA_ID
    assert str(doc["version"]) == "1.1"
    assert "version bump" in doc["change"]
    assert any(c["id"] == "c10-undeclared-has-a-decision" for c in doc["cases"])


def test_every_criterion_is_classified():
    text = OBS_MD.read_text(encoding="utf-8")
    for letter in CRITERIA:
        assert f"| {letter} |" in text or f"| {letter} (" in text, letter
    assert "| C15 (AS) |" in text
    assert "| C15 (EP) |" in text
    assert "falsify" in text
    assert "Does not establish" in CASES_MD.read_text(encoding="utf-8") or "does not establish" in CASES_MD.read_text(encoding="utf-8")


def test_cases_are_target_agnostic():
    blob = CASES_YAML.read_text(encoding="utf-8").lower()
    for word in MECHANISM:
        assert word not in blob, word
    # the human list may mention a later route as divergence, not a mechanism
    yaml_ids = [c["id"] for c in load_cases()["cases"]]
    md = CASES_MD.read_text(encoding="utf-8")
    for cid in yaml_ids:
        assert cid in md


def test_witnesses_falsify_not_verify():
    for case in load_cases()["cases"]:
        if case.get("class") == "witness":
            assert case.get("caveat") == "falsify-not-verify", case["id"]


def test_generation_is_skipped_against_a_url_target():
    sent: list[str] = []

    def send(method, path, **_k):
        sent.append(path)
        return _obs(200)

    report = run_kit(load_cases(), Target(send=send, token="t"), level="3")
    row = next(c for c in report["cases"] if c["id"].startswith("c13-"))
    assert row["result"] == "skipped"
    assert row["reason"] == SKIP_COVERED_AT_GENERATION
    assert all("composition" not in p for p in sent)


def test_missing_capability_skips_and_is_not_a_pass():
    def send(*_a, **_k):
        return _obs(200)

    report = run_kit(load_cases(), Target(send=send, token="t"), level="3")
    c16 = next(c for c in report["cases"] if c["id"].startswith("c16-"))
    assert c16["result"] == "skipped"
    assert c16["reason"] == SKIP_REQUIRES_CAPABILITY
    assert report["skipped"] >= 1


def test_failure_records_the_observed_value():
    def send(*_a, **_k):
        return _obs(200, {"status": "ok"})

    cases = {
        "ctierSchema": SCHEMA_ID,
        "version": KIT_VERSION,
        "cases": [{
            "id": "c9-highest-class-names-no-resume",
            "criterion": "C9",
            "class": "runtime",
            "level": "any",
            "send": {"method": "POST", "path": "/payments", "body": "{}"},
            "expect": {"status": 423},
        }],
    }
    report = run_kit(cases, Target(send=send, token="t"), level="3")
    row = report["cases"][0]
    assert row["result"] == "failed"
    assert row["observed"]["status"] == 200
    assert row["observed"]["failures"][0]["expected"] == 423
    assert "failed" in dump_report(report)


def test_a_matching_observation_passes():
    def send(*_a, **_k):
        return _obs(
            423,
            {"status": "agent_suspended", "agentAction": "halt_and_hand_off"},
            {"X-Agent-Action": "halt_and_hand_off"},
        )

    cases = {
        "ctierSchema": SCHEMA_ID,
        "version": KIT_VERSION,
        "cases": [next(c for c in load_cases()["cases"] if c["id"].startswith("c9-"))],
    }
    report = run_kit(cases, Target(send=send, token="t"), level="3")
    assert report["failed"] == 0
    assert report["cases"][0]["result"] == "passed"


def test_c12_bare_404_is_inconclusive_not_fail():
    """Path never routed is not a C12 miss. Kit cannot tell them apart."""

    def send(*_a, **_k):
        return _obs(404)

    cases = {
        "ctierSchema": SCHEMA_ID,
        "version": KIT_VERSION,
        "cases": [next(c for c in load_cases()["cases"] if c["id"].startswith("c12-"))],
    }
    report = run_kit(cases, Target(send=send, token="t"), level="3")
    row = report["cases"][0]
    assert row["result"] == "inconclusive"
    assert report["failed"] == 0
    assert report["inconclusive"] == 1
    assert report["ran"] == 1


def test_c12_wrong_refuse_still_fails():
    def send(*_a, **_k):
        return _obs(
            423,
            {"status": "agent_suspended", "agentAction": "halt_and_hand_off"},
        )

    cases = {
        "ctierSchema": SCHEMA_ID,
        "version": KIT_VERSION,
        "cases": [next(c for c in load_cases()["cases"] if c["id"].startswith("c12-"))],
    }
    report = run_kit(cases, Target(send=send, token="t"), level="3")
    assert report["cases"][0]["result"] == "failed"
    assert report["failed"] == 1


def test_c12_case_declares_provision_and_inconclusive_when():
    case = next(c for c in load_cases()["cases"] if c["id"].startswith("c12-"))
    assert case.get("provision") == "routed-but-ungoverned"
    assert (case.get("inconclusiveWhen") or {}).get("status") == 404


def test_level_2_skips_level_3_only_rows():
    def send(*_a, **_k):
        return _obs(403, {"status": "provisioning_defect"})

    report = run_kit(load_cases(), Target(send=send, token="t"), level="2")
    c5 = next(c for c in report["cases"] if c["id"].startswith("c5-"))
    assert c5["result"] == "skipped"
    assert c5["reason"] == SKIP_NOT_APPLICABLE_AT_LEVEL


def test_c7_reads_the_balance_hop_not_a_later_healthcheck():
    log: list[dict] = []

    def send(*_a, **_k):
        log.append({
            "method": "GET",
            "path": "/accounts/12345/balance",
            "headers": {"idempotency-key": "minted-not-agent"},
        })
        log.append({"method": "GET", "path": "/", "headers": {}})
        return _obs(200)

    case = next(c for c in load_cases()["cases"] if c["id"].startswith("c7-"))
    report = run_kit(
        {"ctierSchema": SCHEMA_ID, "version": KIT_VERSION, "cases": [case]},
        Target(send=send, token="t", observer_log=lambda: list(log)),
        level="3",
    )
    assert report["cases"][0]["result"] == "passed"


def test_c7_still_fails_when_the_balance_hop_has_no_identifier():
    log: list[dict] = []

    def send(*_a, **_k):
        log.append({
            "method": "GET",
            "path": "/accounts/12345/balance",
            "headers": {},
        })
        log.append({
            "method": "GET",
            "path": "/",
            "headers": {"idempotency-key": "somewhere-else"},
        })
        return _obs(200)

    case = next(c for c in load_cases()["cases"] if c["id"].startswith("c7-"))
    report = run_kit(
        {"ctierSchema": SCHEMA_ID, "version": KIT_VERSION, "cases": [case]},
        Target(send=send, token="t", observer_log=lambda: list(log)),
        level="3",
    )
    row = report["cases"][0]
    assert row["result"] == "failed"
    assert row["observed"]["failures"][0]["field"] == "observer.present.idempotency-key"


def test_c16_does_not_pass_on_a_later_healthcheck():
    log: list[dict] = []

    def send(*_a, **_k):
        log.append({
            "method": "GET",
            "path": "/accounts/12345/balance",
            "headers": {"x-ctier-unknown-audit": "forged"},
        })
        log.append({"method": "GET", "path": "/", "headers": {}})
        return _obs(200)

    case = next(c for c in load_cases()["cases"] if c["id"].startswith("c16-"))
    report = run_kit(
        {"ctierSchema": SCHEMA_ID, "version": KIT_VERSION, "cases": [case]},
        Target(send=send, token="t", observer_log=lambda: list(log)),
        level="3",
    )
    row = report["cases"][0]
    assert row["result"] == "failed"
    assert row["observed"]["failures"][0]["field"] == "observer.absent.x-ctier-unknown-audit"


def test_c16_passes_when_the_balance_hop_lacks_the_forged_header():
    log: list[dict] = []

    def send(*_a, **_k):
        log.append({
            "method": "GET",
            "path": "/accounts/12345/balance",
            "headers": {"idempotency-key": "minted"},
        })
        log.append({"method": "GET", "path": "/", "headers": {}})
        return _obs(200)

    case = next(c for c in load_cases()["cases"] if c["id"].startswith("c16-"))
    report = run_kit(
        {"ctierSchema": SCHEMA_ID, "version": KIT_VERSION, "cases": [case]},
        Target(send=send, token="t", observer_log=lambda: list(log)),
        level="3",
    )
    assert report["cases"][0]["result"] == "passed"


def test_c16_does_not_pass_when_the_only_new_line_is_a_healthcheck():
    log: list[dict] = []

    def send(*_a, **_k):
        log.append({"method": "GET", "path": "/", "headers": {}})
        return _obs(200)

    case = next(c for c in load_cases()["cases"] if c["id"].startswith("c16-"))
    report = run_kit(
        {"ctierSchema": SCHEMA_ID, "version": KIT_VERSION, "cases": [case]},
        Target(send=send, token="t", observer_log=lambda: list(log)),
        level="3",
    )
    row = report["cases"][0]
    assert row["result"] == "failed"
    assert row["observed"]["failures"][0]["field"] == "observer.hop"


def test_c7_not_equals_does_not_pass_on_a_healthcheck_alone():
    log: list[dict] = []

    def send(*_a, **_k):
        log.append({"method": "GET", "path": "/", "headers": {}})
        return _obs(200)

    case = next(c for c in load_cases()["cases"] if c["id"].startswith("c7-"))
    report = run_kit(
        {"ctierSchema": SCHEMA_ID, "version": KIT_VERSION, "cases": [case]},
        Target(send=send, token="t", observer_log=lambda: list(log)),
        level="3",
    )
    row = report["cases"][0]
    assert row["result"] == "failed"
    assert row["observed"]["failures"][0]["field"] == "observer.hop"


def _one(case_id: str) -> dict:
    case = next(c for c in load_cases()["cases"] if c["id"] == case_id)
    return {"ctierSchema": SCHEMA_ID, "version": KIT_VERSION, "cases": [case]}


def test_c10_ignores_a_decision_from_another_request():
    case_id = "c10-execute-has-a-decision"
    rows: list[dict] = []

    def send(*_a, **_k):
        rows.append({
            "ctierSchema": "decision-record/0.2.0",
            "id": "other",
            "correlationScope": "kit-someone-else",
        })
        return _obs(200)

    report = run_kit(
        _one(case_id),
        Target(send=send, token="t", records=lambda: list(rows)),
        level="3",
    )
    row = report["cases"][0]
    assert row["result"] == "failed"
    assert row["observed"]["failures"][0]["field"] == "record.present"


def test_c10_passes_on_the_decision_for_this_task():
    case_id = "c10-execute-has-a-decision"
    rows: list[dict] = []

    def send(*_a, **_k):
        rows.append({
            "ctierSchema": "decision-record/0.2.0",
            "id": "other",
            "correlationScope": "kit-someone-else",
        })
        rows.append({
            "ctierSchema": "decision-record/0.2.0",
            "id": "this",
            "correlationScope": f"kit-{case_id}-1",
        })
        return _obs(200)

    report = run_kit(
        _one(case_id),
        Target(send=send, token="t", records=lambda: list(rows)),
        level="3",
    )
    assert report["cases"][0]["result"] == "passed"


def test_c12_scores_this_attempt_not_a_later_row():
    case_id = "c12-unassigned-is-refused-undetermined"
    rows: list[dict] = []

    def send(*_a, **_k):
        rows.append({
            "ctierSchema": "attempt-record/0.3.0",
            "id": "this-attempt",
            "correlationScope": f"kit-{case_id}-1",
            "appliedTier": None,
            "reason": "unassigned",
        })
        rows.append({
            "ctierSchema": "attempt-record/0.3.0",
            "id": "later-attempt",
            "correlationScope": "kit-someone-else",
            "appliedTier": 4,
            "reason": "custody-unavailable",
        })
        rows.append({
            "ctierSchema": "decision-record/0.2.0",
            "id": "other-decision",
            "correlationScope": "kit-someone-else",
        })
        return _obs(423, {"status": "unassigned", "agentAction": "halt"})

    report = run_kit(
        _one(case_id),
        Target(send=send, token="t", records=lambda: list(rows)),
        level="3",
    )
    assert report["cases"][0]["result"] == "passed", report["cases"][0]


def test_c14_does_not_score_the_last_pending_row():
    case_id = "c14-w1-pending-publishes-no-credential"

    def send(*_a, **_k):
        return _obs(202, {"correlationId": "this-request"})

    def pending():
        return [{
            "correlationId": "older",
            "method": "PUT",
            "path": "/customers/12345/preferences/communication",
        }]

    report = run_kit(
        _one(case_id),
        Target(send=send, token="caller-token", pending=pending),
        level="3",
    )
    row = report["cases"][0]
    assert row["result"] == "failed"
    assert row["observed"]["failures"][0]["field"] == "pending.noCredential"


def test_c14_scores_the_pending_row_for_this_correlation_identifier():
    case_id = "c14-w1-pending-publishes-no-credential"

    def send(*_a, **_k):
        return _obs(202, {"correlationId": "this-request"})

    def pending():
        return [
            {"correlationId": "older", "authorization": "Bearer caller-token"},
            {
                "correlationId": "this-request",
                "method": "PUT",
                "path": "/customers/12345/preferences/communication",
            },
        ]

    report = run_kit(
        _one(case_id),
        Target(send=send, token="caller-token", pending=pending),
        level="3",
    )
    assert report["cases"][0]["result"] == "passed"


def test_c7_at_level_2_is_not_applicable():
    def send(*_a, **_k):
        return _obs(200)

    report = run_kit(
        load_cases(),
        Target(send=send, token="t", observer_log=lambda: []),
        level="2",
    )
    c7 = next(c for c in report["cases"] if c["id"].startswith("c7-"))
    assert c7["result"] == "skipped"
    assert c7["reason"] == SKIP_NOT_APPLICABLE_AT_LEVEL
    assert load_cases()["cases"][
        next(i for i, c in enumerate(load_cases()["cases"]) if c["id"].startswith("c7-"))
    ]["level"] == "3"


def test_every_skip_reason_is_from_the_fixed_set():
    def send(*_a, **_k):
        return _obs(200)

    for level in ("2", "3"):
        report = run_kit(load_cases(), Target(send=send, token="t"), level=level)
        for row in report["cases"]:
            if row["result"] == "skipped":
                assert row["reason"] in SKIP_REASONS, row
        assert "ran" in report
        assert report["ran"] == report["passed"] + report["failed"] + report["inconclusive"]
