"""Kong DB-less + mock echo come up. No ctier plugin under test yet."""
from __future__ import annotations

import pytest

from tests.live.rig import MINIMAL, STATUS, http

pytestmark = pytest.mark.live


def test_kong_status_ready(kong_stack):
    status, raw, _ = http("GET", STATUS)
    assert status == 200
    assert raw


def test_echo_is_reachable_through_kong(kong_stack):
    kong_stack.load(MINIMAL)
    status, payload = kong_stack.echo_json("GET", "/ping")
    assert status == 200
    assert payload["method"] == "GET"
    assert payload["path"].startswith("/ping")
    assert "headers" in payload
