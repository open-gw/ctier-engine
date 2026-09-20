"""Three Kong assumptions, each with a specific falsification."""
from __future__ import annotations

import pytest
import yaml

from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import GOLDEN_ROOT, NOW
from tests.live.rig import point_at_echo
from tests.test_generate import _declared, _spec

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"


def _load(kong_stack, qualified) -> None:
    files = generate(qualified, target="kong")
    kong_stack.load_generated(files)


def test_e1_route_per_operation_resolves_the_operation(kong_stack):
    """Request an operation's path; the echo carries that operation's tier."""
    qualified, _ = compose(REFERENCE, [], NOW)
    _load(kong_stack, qualified)
    status, payload = kong_stack.echo_json(
        "GET", "/accounts/12345/balance", headers=kong_stack.auth_headers(),
    )
    assert status == 200, payload
    headers = payload["headers"]
    assert headers.get("x-ctier-tier") == "1"
    assert headers.get("x-ctier-operation") == "getBalance"


def test_e2_kong_resolves_path_specificity_itself(kong_stack):
    """Literal /orders/summary is not captured by /orders/{orderId}.

    06's sibling pair differs by method, which would let Kong's method match
    mask specificity. This experiment uses GET on both.
    """
    raw = _spec({
        "/orders/summary": {"get": _declared(1, "getOrderSummary")},
        "/orders/{orderId}": {"get": _declared(4, "getOrder")},
    }, title="specificity")
    qualified, _ = compose(raw, [], NOW)
    files = generate(qualified, target="kong")
    deck = yaml.safe_load(files["kong.yaml"])
    by_name = {r["name"]: r for r in deck["services"][0]["routes"]}
    assert by_name["getOrderSummary"]["regex_priority"] > by_name["getOrder"]["regex_priority"]
    _load(kong_stack, qualified)
    literal, payload = kong_stack.echo_json(
        "GET", "/orders/summary", headers=kong_stack.auth_headers(),
    )
    assert literal == 200, payload
    assert payload["headers"].get("x-ctier-tier") == "1"
    assert payload["headers"].get("x-ctier-operation") == "getOrderSummary"
    templated, _raw, _hdrs = kong_stack.request(
        "GET", "/orders/abc", headers=kong_stack.auth_headers(),
    )
    assert templated == 423


def test_e3_fail_closed_arises_from_plugin_precedence(kong_stack):
    """A route with no ctier instance inherits global T4. Design-critical."""
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target="kong")
    deck = yaml.safe_load(files["kong.yaml"])
    export = next(r for r in deck["services"][0]["routes"] if r["name"] == "exportStatements")
    assert "plugins" not in export, "fixture must leave the undeclared route without ctier"
    _load(kong_stack, qualified)
    status, raw, _ = kong_stack.request("POST", "/accounts/12345/statements/export")
    assert status == 423, (
        "E3 failed: undeclared operation did not inherit global T4. "
        f"status={status} body={raw!r}. Design failure — do not patch the plugin."
    )
