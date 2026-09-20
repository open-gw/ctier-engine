"""Live suspension: T4 and C8 reject remove a scope; expiry does not."""
from __future__ import annotations

import base64
import json
import time

import pytest

from ctier.authz import ACCESS_TOKEN_LIFESPAN
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
CUSTODY_CFG = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _restore(kong_stack) -> dict[str, str]:
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="kong", custody=CUSTODY_CFG)
    kong_stack.load_generated(files)
    return files


@pytest.fixture
def restored(kong_stack):
    files = _restore(kong_stack)
    yield files
    _restore(kong_stack)


def test_access_token_lifetime_is_the_compiled_lifespan(kong_stack, restored):
    token = kong_stack.fresh_token()
    claims = _claims(token)
    lifetime = int(claims["exp"]) - int(claims["iat"])
    print(f"\n13a measured access-token lifetime: {lifetime}s (exp-iat)")
    assert lifetime == ACCESS_TOKEN_LIFESPAN


def test_tier4_suspends_and_the_next_token_is_refused(kong_stack, restored):
    issued = kong_stack.fresh_token()
    claims = _claims(issued)
    remaining = int(claims["exp"]) - int(time.time())
    status, raw, _ = kong_stack.request(
        "POST",
        "/payments",
        headers={
            "Authorization": f"Bearer {issued}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-suspend-1",
        },
        body="{}",
    )
    assert status == 423, raw
    # Already-issued token still carries the scope: that remainder is the delay.
    still, still_raw, _ = kong_stack.request(
        "POST",
        "/payments",
        headers={
            "Authorization": f"Bearer {issued}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-suspend-1",
        },
        body="{}",
    )
    assert still == 423, still_raw
    print(
        f"\n13a measured suspension delay bound: {remaining}s remaining on the "
        f"already-issued token (lifetime {int(claims['exp']) - int(claims['iat'])}s)"
    )
    status2, raw2, _ = kong_stack.request(
        "POST",
        "/payments",
        headers={
            "Authorization": f"Bearer {kong_stack.fresh_token()}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-suspend-1",
        },
        body="{}",
    )
    assert status2 == 401, raw2
    body = json.loads(raw2.decode("utf-8"))
    assert body.get("status") == "unauthorized"


def test_rejected_tier3_suspends_and_the_next_token_is_refused(kong_stack, restored):
    status, raw, _ = kong_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers=kong_stack.auth_headers(**{"X-Agent-Id": "agent-a", "X-Task-Id": "task-reject-1"}),
    )
    body = json.loads(raw.decode("utf-8"))
    assert status == 202, body
    dec_status, dec_raw, _ = http(
        "POST",
        f"{CUSTODY}/v1/decisions/{body['correlationId']}",
        headers={
            "Content-Type": "application/json",
            "X-Approver-Id": "analyst-13a",
        },
        body=json.dumps({"decision": "reject"}).encode("utf-8"),
    )
    assert dec_status == 200, dec_raw
    status2, raw2, _ = kong_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers={
            "Authorization": f"Bearer {kong_stack.fresh_token()}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-reject-1",
        },
    )
    assert status2 == 401, raw2


def test_expired_tier3_does_not_suspend(kong_stack, restored):
    """A withhold that is not rejected leaves the grant. Token TTL is waited,
    not estimated: the next token must still execute a classified Tier 1.
    """
    first = kong_stack.fresh_token()
    claims = _claims(first)
    remaining = int(claims["exp"]) - int(time.time())
    status, raw, _ = kong_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers={
            "Authorization": f"Bearer {first}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-expire-1",
        },
    )
    assert status == 202, raw
    if remaining > 0:
        time.sleep(remaining + 1)
    status2, raw2, _ = kong_stack.request(
        "GET",
        "/accounts/12345/balance",
        headers={
            "Authorization": f"Bearer {kong_stack.fresh_token()}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-expire-1",
        },
    )
    assert status2 == 200, raw2
    echo = json.loads(raw2.decode("utf-8"))
    assert echo["headers"].get("x-ctier-tier") == "1"
