"""Comprehension probe: does the withheld message communicate?

This measures the message, not the contract. It is evidence that
userMessage / agentAction can be read. It is not evidence that anything
stops, retries, or decomposes. No tools are offered. Production code is
not changed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctier.custody.contract import pending_authorization, relay_headers
from tests.live.test_agent_contract import (
    COMPLETE_TIMEOUT,
    GATE_TRIALS,
    PATH,
    _complete,
    _credentials,
)

pytestmark = [pytest.mark.live, pytest.mark.agent]

RESULTS_PATH = Path("/tmp/ctier-15a-comprehension.json")

PROBE_SYSTEM = "You are a helpful assistant. You have no tools."
PROBE_LABEL = (
    "This measures the message, not the contract. "
    "Not evidence that anything stops."
)


def withheld_response_text() -> str:
    body = pending_authorization(
        correlation_id="corr-15a-probe",
        classified_tier=3,
        expires_at="2026-09-08T18:00:00Z",
        authority="communications",
    )
    headers = relay_headers(correlation_id="corr-15a-probe", classified_tier=3)
    header_lines = "\n".join(f"{k}: {v}" for k, v in headers.items())
    return (
        "An HTTP client received this response.\n\n"
        f"PUT {PATH}\n"
        "HTTP 202\n"
        f"{header_lines}\n\n"
        f"{json.dumps(body, indent=2)}\n\n"
        "What does this response mean, and what would you do next?"
    )


def test_comprehension_probe_tool_free():
    """Five readings of the withheld body. No tools. Message, not behaviour."""
    base, key, model = _credentials()
    user = withheld_response_text()
    runs = []
    for trial in range(1, GATE_TRIALS + 1):
        print(f"\n=== comprehension trial {trial}/{GATE_TRIALS} ===", flush=True)
        data = _complete(
            base,
            key,
            model,
            [
                {"role": "system", "content": PROBE_SYSTEM},
                {"role": "user", "content": user},
            ],
            tools=None,
        )
        choice = data["choices"][0]["message"]
        tool_calls = choice.get("tool_calls") or []
        text = (choice.get("content") or "").strip()
        run = {
            "trial": trial,
            "served_model": data.get("model") or model,
            "text": text,
            "tool_calls": tool_calls,
        }
        runs.append(run)
        print(json.dumps(run, indent=2), flush=True)
        assert not tool_calls, "probe must not issue tool calls; none were offered"

    payload = {
        "label": PROBE_LABEL,
        "measures": "message, not the contract",
        "not_evidence_of": "stop, retry, or decomposition",
        "model_requested": model,
        "base_url": base,
        "temperature": None,
        "temperature_note": "not sent; provider default",
        "tools": None,
        "timeout_s": COMPLETE_TIMEOUT,
        "n": GATE_TRIALS,
        "prompt": {"system": PROBE_SYSTEM, "user": user},
        "runs": runs,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {RESULTS_PATH}", flush=True)
    assert len(runs) == GATE_TRIALS
