"""13c E4: reduction by client entitlement, not subject-token lineage."""
from __future__ import annotations

import base64
import json

import pytest

from ctier.authz import AGENT_CLIENT, AGENT_SUB_CLIENT, scope_name
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.rig import CUSTODY_INTERNAL

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
BALANCE = scope_name("getBalance")
PAYMENT = scope_name("initiatePayment")
SUB_CLIENT = AGENT_SUB_CLIENT
CUSTODY_CFG = {"url": CUSTODY_INTERNAL, "timeout_ms": 200}


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _scopes(token: str) -> set[str]:
    raw = _claims(token).get("scope") or ""
    return {s for s in str(raw).split() if s}


@pytest.fixture
def entitlement_ready(kong_stack):
    import yaml

    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="kong", custody=CUSTODY_CFG)
    doc = yaml.safe_load(files["authorization.yaml"])
    ids = [c["id"] for c in doc["clients"]]
    assert SUB_CLIENT in ids, "generate() must emit the sub-agent that made E4 hold"
    kong_stack.load_generated(files)
    yield


def test_e4_reduction_by_client_entitlement(kong_stack, entitlement_ready):
    """A client never entitled to a scope cannot obtain it by exchange."""
    parent = kong_stack.fresh_token(scopes=f"{BALANCE} {PAYMENT}")
    assert BALANCE in _scopes(parent)
    assert PAYMENT in _scopes(parent)
    parent_claims = _claims(parent)
    print(f"\n13c E4 parent aud={parent_claims.get('aud')!r} azp={parent_claims.get('azp')!r}")

    # (a) Exchange parent token into agent-sub-balance.
    a_status, a_body = kong_stack.exchange(parent, scopes=BALANCE, client_id=SUB_CLIENT)
    print(f"\n13c E4 (a) exchange into {SUB_CLIENT}: status={a_status} body_keys={list(a_body)}")
    assert a_status == 200, (
        f"expressibility or mechanism failed at (a): status={a_status} body={a_body}"
    )
    token_a = a_body["access_token"]
    have_a = _scopes(token_a)
    claims_a = _claims(token_a)
    print(
        f"\n13c E4 (a) scopes={sorted(have_a)} aud={claims_a.get('aud')!r} "
        f"azp={claims_a.get('azp')!r} act={claims_a.get('act')!r} "
        f"keys={sorted(claims_a)}"
    )
    assert BALANCE in have_a, have_a
    assert PAYMENT not in have_a, have_a
    chain_keys = {
        k: claims_a.get(k)
        for k in ("act", "azp", "sub", "sid", "session_state", "typ")
        if k in claims_a
    }
    print(f"\n13c E4 claims dump (exchanged): {json.dumps(chain_keys, default=str)}")
    print(f"\n13c E4 act present: {'act' in claims_a}")

    # (b) Same exchange, explicitly requesting initiatePayment.
    b_status, b_body = kong_stack.exchange(
        parent, scopes=PAYMENT, client_id=SUB_CLIENT,
    )
    b_scopes = _scopes(b_body["access_token"]) if b_status == 200 else set()
    print(
        f"\n13c E4 (b) request {PAYMENT}: status={b_status} "
        f"scopes={sorted(b_scopes)} error={b_body.get('error')} "
        f"desc={b_body.get('error_description')}"
    )
    if b_status == 200:
        assert PAYMENT not in b_scopes, (
            f"(b) issued {PAYMENT} to an unentitled client: {sorted(b_scopes)}"
        )
        b_outcome = "issued-without"
    else:
        b_outcome = "refused"
    print(f"\n13c E4 (b) outcome={b_outcome}")

    # (c) Re-exchange the token from (a), requesting initiatePayment.
    c_status, c_body = kong_stack.exchange(
        token_a, scopes=PAYMENT, client_id=SUB_CLIENT,
    )
    c_scopes = _scopes(c_body["access_token"]) if c_status == 200 else set()
    print(
        f"\n13c E4 (c) re-exchange request {PAYMENT}: status={c_status} "
        f"scopes={sorted(c_scopes)} error={c_body.get('error')} "
        f"desc={c_body.get('error_description')}"
    )
    if c_status == 200:
        assert PAYMENT not in c_scopes, (
            f"(c) re-exchange restored {PAYMENT}: {sorted(c_scopes)}"
        )
        c_outcome = "issued-without"
    else:
        c_outcome = "refused"
    print(f"\n13c E4 (c) outcome={c_outcome}")

    # Audience check: Kong must accept the exchanged token on the held op,
    # otherwise the 401 in (d) is measuring jwt/aud, not missing scope.
    headers = {
        "Authorization": f"Bearer {token_a}",
        "X-Agent-Id": SUB_CLIENT,
        "X-Task-Id": "task-entitlement-1",
    }
    ok, raw_ok, _ = kong_stack.request(
        "GET", "/accounts/12345/balance", headers=headers,
    )
    print(f"\n13c E4 audience/cid on exchanged token: GET balance -> {ok}")
    assert ok == 200, (
        f"Kong rejected the exchanged token (aud/cid?), so (d) would be the "
        f"wrong 401. status={ok} body={raw_ok!r} aud={claims_a.get('aud')!r} "
        f"cid={claims_a.get('cid')!r}"
    )

    # (d) initiatePayment at Kong with the token from (a).
    denied, raw_denied, _ = kong_stack.request(
        "POST", "/payments", headers=headers, body="{}",
    )
    print(f"\n13c E4 (d) POST /payments -> {denied}")
    assert denied == 401, raw_denied

    # (e) Control: the parent client exchanges for initiatePayment and succeeds.
    e_status, e_body = kong_stack.exchange(
        parent, scopes=PAYMENT, client_id=AGENT_CLIENT,
    )
    e_scopes = _scopes(e_body["access_token"]) if e_status == 200 else set()
    print(
        f"\n13c E4 (e) parent exchange {PAYMENT}: status={e_status} "
        f"scopes={sorted(e_scopes)}"
    )
    assert e_status == 200, e_body
    assert PAYMENT in e_scopes, e_scopes
