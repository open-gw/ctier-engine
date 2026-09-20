"""Live Tier 3 withhold: persist, 202 contract, fail-closed, corpus at level-3."""
from __future__ import annotations

import json

import pytest

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.conformance.adapter import ReferenceAdapter
from ctier.conformance.kong import KongAdapter
from ctier.conformance.runner import dump_report, run_corpus
from ctier.corpus import build_corpus, load_extras
from ctier.custody.contract import AGENT_ACTION
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, PROXY, http, point_at_echo

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
CUSTODY_CFG = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}


def _load_level3(kong_stack, qualified) -> None:
    files = generate(qualified, target="kong", custody=CUSTODY_CFG)
    kong_stack.load_generated(files)


def test_tier3_withhold_returns_202_and_appears_in_the_queue(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load_level3(kong_stack, qualified)
    status, raw, hdrs = kong_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-live-09", "X-Task-Id": "task-09"}),
    )
    body = json.loads(raw.decode("utf-8"))
    assert status == 202, body
    assert "retry-after" not in {k.lower() for k in hdrs}
    assert body["status"] == "pending_authorization"
    assert body["retryable"] is False
    assert body["agentAction"] == AGENT_ACTION
    assert body["classifiedTier"] == 3
    assert "pollUrl" not in body
    assert hdrs.get("x-agent-action") == AGENT_ACTION
    assert hdrs.get("x-ctier-correlation-id") == body["correlationId"]
    assert "method" not in body  # not the echo
    queue_status, queue_raw, _ = http("GET", CUSTODY + "/v1/pending")
    assert queue_status == 200
    pending = json.loads(queue_raw.decode("utf-8"))["pending"]
    match = [p for p in pending if p["correlationId"] == body["correlationId"]]
    assert match, pending
    assert match[0]["operationAnchor"] == "updateCommunicationPreferences"
    assert match[0]["agentId"] == "agent-live-09"
    assert match[0]["appliedTier"] == 3


def test_custody_unavailable_is_503_retryable_not_suspension(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    _load_level3(kong_stack, qualified)
    try:
        kong_stack.stop_service("custody")
        status, raw, hdrs = kong_stack.request(
            "PUT",
            "/customers/12345/profile",
            headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-live-09"}),
        )
        body = json.loads(raw.decode("utf-8"))
        assert status == 503, body
        assert hdrs.get("retry-after") == "5"
        assert body.get("retryable") is True
        assert body.get("status") == "custody_unavailable"
        assert "halt_and_hand_off" not in json.dumps(body)
        assert status != 423
        assert status != 403
    finally:
        kong_stack.start_service("custody")


def test_differential_corpus_at_level_3(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment="level-3")
    _load_level3(kong_stack, qualified)

    def request_fn(method, url, headers, data):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return kong_stack.request(
            method, parsed.path, query=query or None, headers=headers,
            body=None if data is None else data.decode("utf-8"),
        )

    report = run_corpus(
        corpus,
        [
            ReferenceAdapter(qualified, deployment="level-3"),
            KongAdapter(
                PROXY,
                request_fn=request_fn,
                qualified_spec=qualified,
                token=kong_stack.token(),
                token_fn=kong_stack.token,
            ),
        ],
    )
    dumped = dump_report(report)
    n = len(report["cases"])
    disagree = [c for c in report["cases"] if not c["agree"]]
    t3 = [
        c for c in report["cases"]
        if c["expect"]["appliedTier"] == 3
    ]
    assert t3
    for row in t3:
        assert row["expect"]["disposition"] == "withhold", row["id"]
        assert row["agree"] is True, row
        assert row["observed"]["kong"]["disposition"] == "withhold"
        assert row["observed"]["kong"]["appliedTier"] == 3
        assert row["observed"]["kong"]["evidence"].get("backendReached") is False

    assert report["deployment"] == "level-3"
    assert n == 24
    assert report["agree"] is True, (
        f"expected 24/24 at level-3; disagree={[c['id'] for c in disagree]}\n{dumped}"
    )
    print(
        f"\n09 differential: cases={n} agree={n} disagree=0 deployment=level-3\n"
    )
    print(dumped)
