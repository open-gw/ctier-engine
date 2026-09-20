"""Session-scoped live stacks. Live tests only."""
from __future__ import annotations

import shutil

import pytest


@pytest.fixture(scope="session")
def kong_stack(tmp_path_factory):
    if shutil.which("docker") is None:
        pytest.skip("live Kong suite needs docker")
    from tests.live.rig import KongStack

    stack = KongStack(tmp_path_factory.mktemp("kong-live"))
    try:
        stack.start()
        yield stack
    finally:
        stack.stop()


@pytest.fixture(scope="session")
def apisix_stack(tmp_path_factory):
    if shutil.which("docker") is None:
        pytest.skip("live APISIX suite needs docker")
    from tests.live.apisix_rig import ApisixStack

    stack = ApisixStack(tmp_path_factory.mktemp("apisix-live"))
    try:
        stack.start()
        yield stack
    finally:
        stack.stop()
