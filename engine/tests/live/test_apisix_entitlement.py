"""13c E4 on APISIX after A5: reduction by client entitlement."""
from __future__ import annotations

import base64
import json

import pytest

from ctier.authz import AGENT_CLIENT, AGENT_SUB_CLIENT, scope_name
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY_INTERNAL

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
BALANCE = scope_name("getBalance")
PAYMENT = scope_name("initiatePayment")
SUB_CLIENT = AGENT_SUB_CLIENT
CUSTODY_CFG = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}
MISSING_SCOPE = {401, 403}


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _scopes(token: str) -> set[str]:
    raw = _claims(token).get("scope") or ""
    return {s for s in str(raw).split() if s}


@pytest.fixture
def entitlement_ready(apisix_stack):
    import yaml

    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="apisix", custody=CUSTODY_CFG)
    doc = yaml.safe_load(files["authorization.yaml"])
    ids = [c["id"] for c in doc["clients"]]
    assert SUB_CLIENT in ids, "generate() must emit the sub-agent that made E4 hold"
    apisix_stack.load_generated(files)
    yield


def test_e4_reduction_by_client_entitlement(apisix_stack, entitlement_ready):
    parent = apisix_stack.fresh_token(scopes=f"{BALANCE} {PAYMENT}")
    assert BALANCE in _scopes(parent)
    assert PAYMENT in _scopes(parent)
    parent_claims = _claims(parent)
    print(
        f"\n13c APISIX E4 parent aud={parent_claims.get('aud')!r} "
        f"azp={parent_claims.get('azp')!r} iss={parent_claims.get('iss')!r}"
    )

    a_status, a_body = apisix_stack.exchange(parent, scopes=BALANCE, client_id=SUB_CLIENT)
    print(f"\n13c APISIX E4 (a) exchange into {SUB_CLIENT}: status={a_status}")
    assert a_status == 200, a_body
    token_a = a_body["access_token"]
    have_a = _scopes(token_a)
    claims_a = _claims(token_a)
    print(
        f"\n13c APISIX E4 (a) scopes={sorted(have_a)} azp={claims_a.get('azp')!r} "
        f"iss={claims_a.get('iss')!r}"
    )
    assert BALANCE in have_a, have_a
    assert PAYMENT not in have_a, have_a

    b_status, b_body = apisix_stack.exchange(
        parent, scopes=PAYMENT, client_id=SUB_CLIENT,
    )
    print(
        f"\n13c APISIX E4 (b) request {PAYMENT}: status={b_status} "
        f"error={b_body.get('error')} desc={b_body.get('error_description')}"
    )
    assert b_status != 200

    c_status, c_body = apisix_stack.exchange(
        token_a, scopes=PAYMENT, client_id=SUB_CLIENT,
    )
    print(
        f"\n13c APISIX E4 (c) re-exchange: status={c_status} "
        f"error={c_body.get('error')}"
    )
    assert c_status != 200

    headers = {
        "Authorization": f"Bearer {token_a}",
        "X-Agent-Id": SUB_CLIENT,
        "X-Task-Id": "task-entitlement-1",
    }
    ok, raw_ok, _ = apisix_stack.request(
        "GET", "/accounts/12345/balance", headers=headers,
    )
    print(f"\n13c APISIX E4 GET balance -> {ok}")
    assert ok == 200, raw_ok

    denied, raw_denied, _ = apisix_stack.request(
        "POST", "/payments", headers=headers, body="{}",
    )
    print(f"\n13c APISIX E4 (d) POST /payments -> {denied} {raw_denied[:200]!r}")
    assert denied in MISSING_SCOPE, raw_denied

    e_status, e_body = apisix_stack.exchange(
        parent, scopes=PAYMENT, client_id=AGENT_CLIENT,
    )
    e_scopes = _scopes(e_body["access_token"]) if e_status == 200 else set()
    print(f"\n13c APISIX E4 (e) parent exchange {PAYMENT}: status={e_status}")
    assert e_status == 200, e_body
    assert PAYMENT in e_scopes, e_scopes
