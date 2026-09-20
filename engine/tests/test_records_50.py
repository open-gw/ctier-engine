"""A reader of the C10 sink can see that a record is missing."""
from __future__ import annotations

from ctier.boundary.records import detect_gaps, parse_prefixed_line
from ctier.boundary.runner import SCHEMA_ID, BoundaryFixture, induce_and_detect_gap, run_suite
from ctier.ledger.sink import log_decision_record

DIGEST = "sha256:" + "ab" * 32


def _rec(*, record_id: str, epoch: str, seq: int) -> dict:
    rec = log_decision_record(
        operation_anchor="getBalance",
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=1,
        escalation_reason="none",
        disposition="execute",
        deployment_digest=DIGEST,
        declared_tier=1,
        correlation_id=record_id,
        record_id=record_id,
        timestamp="2026-09-19T12:00:00Z",
    )
    rec["sinkEpoch"] = epoch
    rec["sinkSeq"] = seq
    return rec


def test_detect_gaps_finds_a_missing_seq_on_one_epoch():
    rows = [
        _rec(record_id="a", epoch="1.0-7", seq=1),
        _rec(record_id="c", epoch="1.0-7", seq=3),
    ]
    gaps = detect_gaps(rows)
    assert gaps == [{"sinkEpoch": "1.0-7", "sinkSeq": 2}]


def test_detect_gaps_does_not_treat_a_new_epoch_as_a_hole():
    rows = [
        _rec(record_id="a", epoch="1.0-7", seq=1),
        _rec(record_id="b", epoch="1.0-7", seq=2),
        _rec(record_id="c", epoch="9.0-7", seq=1),
    ]
    assert detect_gaps(rows) == []


def test_induce_drops_a_record_and_the_reader_sees_the_hole():
    rows = [
        _rec(record_id="a", epoch="1.0-7", seq=1),
        _rec(record_id="b", epoch="1.0-7", seq=2),
        _rec(record_id="c", epoch="1.0-7", seq=3),
    ]
    assert induce_and_detect_gap(rows) is None


def test_a_present_sequence_field_is_not_itself_the_property():
    rows = [_rec(record_id="a", epoch="1.0-7", seq=1)]
    assert detect_gaps(rows) == []
    err = induce_and_detect_gap(rows)
    assert err is not None
    assert "three sequenced records" in err


def test_parse_prefixed_line_feeds_the_reader():
    rec = log_decision_record(
        operation_anchor="getBalance",
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=1,
        escalation_reason="none",
        disposition="execute",
        deployment_digest=DIGEST,
        declared_tier=1,
        correlation_id="cid-1",
        record_id="cid-1",
        timestamp="2026-09-19T12:00:00Z",
    )
    import json
    line = (
        '[ctier-decision] epoch=1.0-7 seq=1 ' + json.dumps(rec) + "\n"
        + '[ctier-decision] epoch=1.0-7 seq=3 ' + json.dumps({**rec, "id": "cid-3"})
    )
    parsed = [parse_prefixed_line(row) for row in line.splitlines()]
    parsed = [row for row in parsed if row]
    assert detect_gaps(parsed) == [{"sinkEpoch": "1.0-7", "sinkSeq": 2}]


def test_suite_case_induces_a_gap_against_a_sink_fixture():
    from ctier.boundary.runner import Observation

    rows = [
        _rec(record_id="a", epoch="1.0-7", seq=1),
        _rec(record_id="b", epoch="1.0-7", seq=2),
        _rec(record_id="c", epoch="1.0-7", seq=3),
    ]
    calls = {"n": 0}

    def send(_m, _p, _h, body=None):
        return Observation(status=200, response_headers={}, observer_headers={})

    def fetch():
        calls["n"] += 1
        return [] if calls["n"] == 1 else rows

    report = run_suite(
        {
            "ctierSchema": SCHEMA_ID,
            "cases": [{
                "id": "induced-gap-is-detected",
                "requires": ["recordSource"],
                "when": {"deployment": "level-2"},
                "send": {
                    "method": "GET",
                    "path": "/accounts/12345/balance",
                    "repeat": 8,
                },
                "expect": {
                    "status": 200,
                    "recorded": [{"type": "decision"}],
                    "induceGap": True,
                },
            }],
        },
        BoundaryFixture(
            capabilities={"recordSource"},
            send=send,
            deployment="level-2",
            fetch_records=fetch,
        ),
    )
    assert report["passed"] == 1, report
