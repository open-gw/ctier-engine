"""The suite is offline. A connect attempt is a test failure.

The live Kong and APISIX suites are opt-in (`pytest --live`) and are the only exception.
"""
from __future__ import annotations

import socket

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run the opt-in Kong/APISIX live suite (needs docker)",
    )
    parser.addoption(
        "--agent",
        action="store_true",
        default=False,
        help="run the opt-in agent-contract loop (needs --live and a model)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: opt-in Kong/APISIX live suite; skipped unless --live",
    )
    config.addinivalue_line(
        "markers",
        "agent: opt-in agent-contract loop; skipped unless --live --agent",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(
            reason="opt-in live Kong/APISIX suite; invoke with pytest --live"
        )
        for item in items:
            if item.get_closest_marker("live"):
                item.add_marker(skip_live)
    if not config.getoption("--agent"):
        skip_agent = pytest.mark.skip(
            reason="opt-in agent-contract loop; invoke with pytest --live --agent"
        )
        for item in items:
            if item.get_closest_marker("agent"):
                item.add_marker(skip_agent)


@pytest.fixture(autouse=True)
def no_network(monkeypatch, request):
    live = request.node.get_closest_marker("live") and request.config.getoption(
        "--live"
    )
    if live:
        return

    def blocked(*_args, **_kwargs):
        raise RuntimeError("network calls are forbidden in the ctier-engine test suite")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
