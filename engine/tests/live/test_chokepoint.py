"""The agent cannot reach the mock backend without the enforcement point."""
from __future__ import annotations

import pytest

from tests.live.apisix_rig import ECHO_HOST_PORT as APISIX_ECHO_PORT
from tests.live.chokepoint import assert_backend_unreachable_from_outside
from tests.live.rig import ECHO_HOST_PORT as KONG_ECHO_PORT

pytestmark = pytest.mark.live


def test_kong_backend_unreachable_from_outside(kong_stack):
    assert_backend_unreachable_from_outside(kong_stack, KONG_ECHO_PORT)


def test_apisix_backend_unreachable_from_outside(apisix_stack):
    assert_backend_unreachable_from_outside(apisix_stack, APISIX_ECHO_PORT)
