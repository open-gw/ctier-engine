"""13b: token exchange and scope reduction at Keycloak.

Find-out first. If E2 is false the rest of the task tells you nothing useful.
Re-exchange (a reduced token asking for a dropped scope) is part of E2.
"""
from __future__ import annotations

import base64
import json

import pytest

from ctier.authz import AGENT_CLIENT, scope_name
from ctier.authz.directory import KeycloakDirectory
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.rig import CUSTODY_INTERNAL, KEYCLOAK

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
BALANCE = scope_name("getBalance")
PAYMENT = scope_name("initiatePayment")
CUSTODY_CFG = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _scopes(token: str) -> set[str]:
    raw = _claims(token).get("scope") or ""
    return {s for s in str(raw).split() if s}


def _directory() -> KeycloakDirectory:
    return KeycloakDirectory(
        KEYCLOAK, "ctier", admin_user="local-dev-admin", admin_password="local-dev-admin-password",
    )


@pytest.fixture
def exchange_ready(kong_stack):
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="kong", custody=CUSTODY_CFG)
    kong_stack.load_generated(files)
    directory = _directory()
    directory.enable_standard_exchange(AGENT_CLIENT)
    yield directory


def test_e1_standard_token_exchange_is_available(kong_stack, exchange_ready):
    """A subject_token this rig mints can be exchanged for a new access token."""
    parent = kong_stack.fresh_token(scopes=f"{BALANCE} {PAYMENT}")
    assert BALANCE in _scopes(parent)
    assert PAYMENT in _scopes(parent)
    status, payload = kong_stack.exchange(parent, scopes=BALANCE)
    assert status == 200, payload
    child = payload["access_token"]
    have = _scopes(child)
    assert BALANCE in have, have
    print(f"\n13b E1 downscope scopes={sorted(have)}")
    assert PAYMENT not in have, (
        "exchange succeeded but did not reduce: default scopes were forced "
        f"back on. scopes={sorted(have)}"
    )


def test_e2_reduction_is_enforced_not_requested(kong_stack, exchange_ready):
    """Expanded re-exchange is refused only when the executor is imported.

    Without the executor the grant exists and may still add scopes. With it,
    a reduced token asking for a dropped scope must fail — that is the
    re-exchange assertion.
    """
    directory = exchange_ready
    parent = kong_stack.fresh_token(scopes=f"{BALANCE} {PAYMENT}")
    down_status, down = kong_stack.exchange(parent, scopes=BALANCE)
    assert down_status == 200, down
    reduced = down["access_token"]
    assert PAYMENT not in _scopes(reduced)

    open_status, opened = kong_stack.exchange(
        reduced, scopes=f"{BALANCE} {PAYMENT}",
    )
    opened_scopes = _scopes(opened["access_token"]) if open_status == 200 else set()
    print(
        f"\n13b E2 re-exchange without executor: status={open_status} "
        f"scopes={sorted(opened_scopes)} body_keys={list(opened)}"
    )
    executor_error = None
    try:
        directory.set_downscope_enforcer(enabled=True)
    except Exception as exc:
        executor_error = str(exc)
        print(f"\n13b E2 executor not importable: {executor_error}")
    else:
        shut_status, shut = kong_stack.exchange(
            reduced, scopes=f"{BALANCE} {PAYMENT}",
        )
        print(f"\n13b E2 re-exchange with executor: status={shut_status} body={shut}")
        assert shut_status != 200, (
            "re-exchange restored a dropped scope; the executor did not enforce "
            f"reduction. body={shut}"
        )
        return

    assert open_status == 200
    assert PAYMENT in opened_scopes
    assert executor_error and "does not have valid provider" in executor_error
    # E2 is falsified on Keycloak 26.3.3. Findings name the constrained profile.


def test_e3_reduced_token_is_what_kong_checks(kong_stack, exchange_ready):
    """A downscoped token executes the held operation and is 401 on the omitted one."""
    parent = kong_stack.fresh_token(scopes=f"{BALANCE} {PAYMENT}")
    status, payload = kong_stack.exchange(parent, scopes=BALANCE)
    if status != 200:
        pytest.skip(f"E1/E2 did not hold; no reduced token: {payload}")
    child = payload["access_token"]
    headers = {
        "Authorization": f"Bearer {child}",
        "X-Agent-Id": "agent-a",
        "X-Task-Id": "task-exchange-1",
    }
    ok, raw_ok, _ = kong_stack.request(
        "GET", "/accounts/12345/balance", headers=headers,
    )
    assert ok == 200, raw_ok
    denied, raw_denied, _ = kong_stack.request(
        "POST", "/payments", headers=headers, body="{}",
    )
    assert denied == 401, raw_denied
