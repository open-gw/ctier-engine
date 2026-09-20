"""Levels 1 and 2 emit a schema-valid decision without a custody service."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ctier.compose import compose
from ctier.generate import generate
from ctier.ledger.records import SCHEMA_DECISION, validate_record
from ctier.ledger.sink import log_decision_record
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW

TARGETS = ("kong", "apisix", "apigee")
HANDLER = (
    Path(__file__).resolve().parents[2]
    / "targets" / "kong" / "plugin" / "handler.lua"
)
REQUIRED = (
    "ctierSchema",
    "id",
    "timestamp",
    "operationAnchor",
    "agentId",
    "correlationScope",
    "appliedTier",
    "escalationReason",
    "disposition",
    "idempotencyKey",
    "deploymentDigest",
)
DIGEST = "sha256:" + "ab" * 32


def _files(target: str, *, observe: bool = False, custody=None):
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    return generate(qualified, target=target, observe=observe, custody=custody)


def _sample() -> dict:
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
        timestamp="2026-09-16T12:00:00Z",
    )
    validate_record(rec)
    return rec


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("observe", [False, True])
def test_level_1_and_2_emit_a_schema_shaped_decision(target, observe):
    files = _files(target, observe=observe)
    blob = "\n".join(files.values())
    if target == "kong":
        text = HANDLER.read_text(encoding="utf-8")
        assert "decision-record/0.2.0" in text
        assert "kong.log.notice" in text
        for key in REQUIRED:
            assert key in text
        deck = yaml.safe_load(files["kong.yaml"])
        if observe:
            assert any(
                (p.get("config") or {}).get("observe") is True
                for p in deck["plugins"]
                if p.get("name") == "ctier"
            )
        else:
            assert "observe: true" not in files["kong.yaml"]
    elif target == "apisix":
        getb = next(
            r for r in yaml.safe_load(files["apisix.yaml"])["routes"]
            if r["name"] == "getBalance"
        )
        post = "\n".join(getb["plugins"]["serverless-post-function"]["functions"])
        assert "ngx.log" in post
        assert "decision-record/0.2.0" in post
        assert "request_uri" not in post
        assert "io.open" not in post
        for key in REQUIRED:
            assert key in post
        if observe:
            t4 = next(
                r for r in yaml.safe_load(files["apisix.yaml"])["routes"]
                if r["name"] == "initiatePayment"
            )
            assert "fault-injection" not in t4["plugins"]
    else:
        js = files["apiproxy/resources/jsc/set-upstream-provenance.js"]
        assert "print('[ctier-decision] '" in js or 'print("[ctier-decision] "' in js
        assert "ctier.record.json" in js
        assert "decision-record/0.2.0" in js
        assert "io.open" not in js
        for key in REQUIRED:
            assert key in js
        proxy = files["apiproxy/proxies/default.xml"]
        if observe:
            assert "RF-Tier4" not in proxy
            assert "RF-Provisioning" not in proxy
        else:
            assert "RF-Tier4" in proxy
    _sample()
    assert SCHEMA_DECISION == "decision-record/0.2.0"


def test_apigee_records_url_compiles_a_retrievable_hop():
    """Trace print alone is not kit_records. A records URL adds the POST."""
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    bare = generate(qualified, target="apigee")
    assert "apiproxy/policies/SC-RecordDecision.xml" not in bare
    wired = generate(
        qualified,
        target="apigee",
        records={"url": "http://records:8090"},
    )
    sc = wired["apiproxy/policies/SC-RecordDecision.xml"]
    assert "http://records:8090" in sc
    assert "/v1/ledger" in sc
    assert "continueOnError=\"true\"" in sc
    assert "JS-RecordRefuse" in wired["apiproxy/proxies/default.xml"]
    assert "SC-RecordDecision" in wired["apiproxy/targets/default.xml"]
    refuse = wired["apiproxy/resources/jsc/record-refuse.js"]
    assert "refuse-and-suspend" in refuse
    assert "undeclared-operation" in refuse
    # Kong ignores records=; still gateway-log only at L2.
    kong = generate(qualified, target="kong", records={"url": "http://records:8090"})
    assert "records" not in kong["kong.yaml"]


def test_level_3_still_posts_the_ledger_and_logs_as_backstop():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    kong = generate(qualified, target="kong", custody={"url": "http://custody:8080"})
    assert "custody_url" in kong["kong.yaml"]
    text = HANDLER.read_text(encoding="utf-8")
    assert 'post_json(conf, "/v1/ledger"' in text
    assert "emit_sink(\"[ctier-decision]" in text
    apisix = generate(qualified, target="apisix", custody={"url": "http://custody:8080"})
    getb = next(
        r for r in yaml.safe_load(apisix["apisix.yaml"])["routes"]
        if r["name"] == "getBalance"
    )
    post = "\n".join(getb["plugins"]["serverless-post-function"]["functions"])
    assert "/v1/ledger" in post
    assert "request_uri" in post
    assert "[ctier-decision]" in post
    assert post.index("ctier_emit_sink") < post.index("/v1/ledger")


def test_level_1_kong_does_not_refuse_tier_4():
    files = _files("kong", observe=True)
    deck = yaml.safe_load(files["kong.yaml"])
    pay = next(
        r for r in deck["services"][0]["routes"] if r["name"] == "initiatePayment"
    )
    conf = next(p["config"] for p in pay["plugins"] if p["name"] == "ctier")
    assert conf["tier"] == 4
    assert conf["observe"] is True


def test_observe_and_custody_cannot_be_the_same_generate():
    from ctier.errors import GenerateError
    with pytest.raises(GenerateError, match="Level 1 has no custody"):
        generate(
            {"openapi": "3.1.0", "info": {"title": "t", "version": "1"}, "paths": {}},
            target="kong",
            observe=True,
            custody={"url": "http://custody:8080"},
        )


def test_record_decision_does_not_open_a_file():
    """append_fallback is the existing JSONL path for Attempts. Decisions at
    Levels 1–2 use kong.log.notice. That is the pipeline, not a new write."""
    text = HANDLER.read_text(encoding="utf-8")
    start = text.index("local function record_decision")
    end = text.index("local function record_attempt")
    chunk = text[start:end]
    assert "io.open" not in chunk
    assert "emit_sink(\"[ctier-decision]" in chunk
    emit = text[text.index("local function emit_sink"):text.index("local function decision_evidence")]
    assert "kong.log.notice" in emit
    assert "[ctier-decision]" in chunk
    assert text.count("io.open") == 1
    assert "local function append_fallback" in text


def test_kong_allocates_sequence_before_emit():
    text = HANDLER.read_text(encoding="utf-8")
    assert text.index("local function allocate_sequence") < text.index("local function emit_sink")
    emit = text[text.index("local function emit_sink"):text.index("local function decision_evidence")]
    assert emit.index("allocate_sequence()") < emit.index("kong.log.notice")
    assert "epoch=" in emit
    assert "seq=" in emit
    assert "ngx.shared" not in emit


def test_apisix_allocates_sequence_before_emit():
    files = _files("apisix")
    getb = next(
        r for r in yaml.safe_load(files["apisix.yaml"])["routes"]
        if r["name"] == "getBalance"
    )
    post = "\n".join(getb["plugins"]["serverless-post-function"]["functions"])
    assert post.index("ctier_allocate_sequence") < post.index("ctier_emit_sink")
    helpers = post.split("return function(conf, ctx)", 1)[0]
    emit = helpers[helpers.index("local function ctier_emit_sink"):]
    assert emit.index("ctier_allocate_sequence()") < emit.index("ngx.log")
    assert "epoch=" in emit
    assert "seq=" in emit
    assert "ngx.shared.ctier_seq" in helpers
    assert "request_uri" not in helpers


def test_sink_line_carries_epoch_and_seq_outside_the_schema():
    from ctier.boundary.records import parse_prefixed_line
    from ctier.boundary.runner import envelope_stripped

    rec = _sample()
    line = f'[ctier-decision] epoch=1.25-7 seq=3 {json.dumps(rec)}'
    parsed = parse_prefixed_line(line)
    assert parsed is not None
    assert parsed["sinkEpoch"] == "1.25-7"
    assert parsed["sinkSeq"] == 3
    validate_record(envelope_stripped(parsed))


def test_attempt_log_sink_is_schema_valid_and_undetermined():
    from ctier.ledger.sink import ATTEMPT_LOG_PREFIX, log_attempt_record

    rec = log_attempt_record(
        operation_anchor="updateCommunicationPreferences",
        declared_tier=3,
        deployment_digest=DIGEST,
        reason="custody-unavailable",
        agent_id="agent-a",
        correlation_scope="task-1",
        record_id="att-1",
        timestamp="2026-09-16T12:00:00Z",
    )
    validate_record(rec)
    assert rec["appliedTier"] is None
    assert rec["ctierSchema"] == "attempt-record/0.3.0"
    assert ATTEMPT_LOG_PREFIX == "[ctier-attempt] "


def test_apisix_withhold_unavailable_logs_an_attempt_without_opening_a_file():
    files = _files("apisix", custody={"url": "http://custody:8080", "timeout_ms": 200})
    comm = next(
        r for r in yaml.safe_load(files["apisix.yaml"])["routes"]
        if r["name"] == "updateCommunicationPreferences"
    )
    post = "\n".join(comm["plugins"]["serverless-post-function"]["functions"])
    assert "[ctier-attempt]" in post
    assert "attempt-record/0.3.0" in post
    assert "appliedTier = cjson.null" in post
    assert "io.open" not in post
    assert "ngx.log" in post


def test_kong_attempt_also_uses_the_log_sink():
    text = HANDLER.read_text(encoding="utf-8")
    start = text.index("local function record_attempt")
    chunk = text[start:]
    assert "[ctier-attempt]" in chunk
    assert "attempt-record/0.3.0" in chunk
    assert "appliedTier = cjson.null" in chunk
    assert "emit_sink(\"[ctier-attempt]" in chunk
    assert "type = \"attempt\"" not in chunk.split("local function withhold")[0]


def test_kong_unassigned_omits_declared_tier():
    text = HANDLER.read_text(encoding="utf-8")
    start = text.index("local function record_attempt")
    chunk = text[start:]
    assert "record_attempt(conf, nil, \"unassigned\")" in chunk
    emit = text[text.index("local function emit_sink"):text.index("local function decision_evidence")]
    assert "epoch=" in emit
    assert "seq=" in emit
    assert "declaredTier" not in emit


def test_attempt_omits_declared_tier_when_none_was_declared():
    from ctier.ledger.sink import log_attempt_record

    rec = log_attempt_record(
        operation_anchor="GET /estate/unknown",
        deployment_digest=DIGEST,
        reason="unassigned",
        record_id="att-none",
        timestamp="2026-09-16T12:00:00Z",
    )
    validate_record(rec)
    assert "declaredTier" not in rec
    assert rec["ctierSchema"] == "attempt-record/0.3.0"


def test_attempt_with_declared_tier_four_is_still_schema_valid():
    from ctier.ledger.sink import log_attempt_record

    rec = log_attempt_record(
        operation_anchor="GET /estate/unknown",
        declared_tier=4,
        deployment_digest=DIGEST,
        reason="unassigned",
        record_id="att-four",
        timestamp="2026-09-16T12:00:00Z",
    )
    validate_record(rec)
    assert rec["declaredTier"] == 4
    assert rec["ctierSchema"] == "attempt-record/0.3.0"


