"""13a on APISIX after A5: exclusion and suspension at the stock plugin."""
from __future__ import annotations

import base64
import json
import time

import pytest

from ctier.authz import ACCESS_TOKEN_LIFESPAN, scope_name
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY, CUSTODY_INTERNAL
from tests.live.rig import http

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
CUSTODY_CFG = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}
MISSING_SCOPE = {401, 403}


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _restore(apisix_stack) -> dict[str, str]:
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="apisix", custody=CUSTODY_CFG)
    apisix_stack.load_generated(files)
    return files


@pytest.fixture
def restored(apisix_stack):
    files = _restore(apisix_stack)
    yield files
    _restore(apisix_stack)


def test_access_token_lifetime_is_the_compiled_lifespan(apisix_stack, restored):
    token = apisix_stack.fresh_token()
    claims = _claims(token)
    lifetime = int(claims["exp"]) - int(claims["iat"])
    print(f"\n13a APISIX measured access-token lifetime: {lifetime}s")
    assert lifetime == ACCESS_TOKEN_LIFESPAN


def test_excluded_closeAccount_is_provisioning_not_missing_scope(apisix_stack, restored):
    """13a exclusion: over-grant detection is 403, not a required_scopes miss."""
    token = apisix_stack.fresh_token()
    claims = _claims(token)
    raw_scope = claims.get("scope") or ""
    assert scope_name("closeAccount") not in str(raw_scope).split()
    status, raw, _ = apisix_stack.request(
        "POST",
        "/accounts/12345/closure",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-exclude-1",
        },
        body="{}",
    )
    print(f"\n13a APISIX excluded closeAccount: {status} {raw[:200]!r}")
    assert status == 403, raw
    body = json.loads(raw.decode("utf-8"))
    assert "required scopes" not in str(body).lower()


def test_tier4_suspends_and_the_next_token_is_refused(apisix_stack, restored):
    issued = apisix_stack.fresh_token()
    claims = _claims(issued)
    remaining = int(claims["exp"]) - int(time.time())
    status, raw, _ = apisix_stack.request(
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
    still, still_raw, _ = apisix_stack.request(
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
        f"\n13a APISIX suspension delay bound: {remaining}s remaining "
        f"(lifetime {int(claims['exp']) - int(claims['iat'])}s)"
    )
    status2, raw2, _ = apisix_stack.request(
        "POST",
        "/payments",
        headers={
            "Authorization": f"Bearer {apisix_stack.fresh_token()}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-suspend-1",
        },
        body="{}",
    )
    print(f"\n13a APISIX next token after T4: {status2} {raw2[:200]!r}")
    # Stock T4 writes a decision to the gateway-log sink only. It does not
    # POST the ledger, so the directory is not told to revoke. C8 reject
    # does, and that case holds. A5's plugin is not this hop.
    assert status2 == 423, raw2


def test_rejected_tier3_suspends_and_the_next_token_is_refused(apisix_stack, restored):
    status, raw, _ = apisix_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers=apisix_stack.auth_headers(
            **{"X-Agent-Id": "agent-a", "X-Task-Id": "task-reject-1"}
        ),
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
    status2, raw2, _ = apisix_stack.request(
        "PUT",
        "/customers/12345/preferences/communication",
        headers={
            "Authorization": f"Bearer {apisix_stack.fresh_token()}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-reject-1",
        },
    )
    print(f"\n13a APISIX next token after C8 reject: {status2} {raw2[:200]!r}")
    assert status2 in MISSING_SCOPE, raw2


def test_expired_tier3_does_not_suspend(apisix_stack, restored):
    first = apisix_stack.fresh_token()
    claims = _claims(first)
    remaining = int(claims["exp"]) - int(time.time())
    status, raw, _ = apisix_stack.request(
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
    status2, raw2, _ = apisix_stack.request(
        "GET",
        "/accounts/12345/balance",
        headers={
            "Authorization": f"Bearer {apisix_stack.fresh_token()}",
            "X-Agent-Id": "agent-a",
            "X-Task-Id": "task-expire-1",
        },
    )
    assert status2 == 200, raw2
    echo = json.loads(raw2.decode("utf-8"))
    assert echo["headers"].get("x-ctier-tier") == "1"
