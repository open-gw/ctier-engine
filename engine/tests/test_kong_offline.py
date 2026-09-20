"""Offline checks on Kong artefacts. No gateway, no network."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import GOLDEN_ROOT, NOW

REPO = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO / "targets" / "kong" / "plugin"
SCHEMA_LUA = PLUGIN_DIR / "schema.lua"
HANDLER_LUA = PLUGIN_DIR / "handler.lua"
KONG_ROOT = GOLDEN_ROOT / "generate-kong"

PLUGIN_FIELDS = frozenset({
    "tier",
    "deployment",
    "operation",
    "excluded",
    "bound_parameter",
    "bound_max",
    "handoff_authority",
    "custody_url",
    "custody_timeout_ms",
    "ledger_fallback",
    "floor_poll_ms",
    "required_scope",
    "observe",
    "governed-set",
})


def _schema_lua_fields() -> set[str]:
    text = SCHEMA_LUA.read_text(encoding="utf-8")
    inner = text.split("config = {", 1)[1]
    # Top-level config fields only; nested custody.url is not a plugin key.
    names = set(re.findall(r"^          \{ (\w+) = \{", inner, flags=re.M))
    names.update(re.findall(r'^          \{ \["([^"]+)"\] = \{', inner, flags=re.M))
    return names


def _plugin_configs(deck: dict) -> list[dict]:
    found = []
    for plugin in deck.get("plugins") or []:
        if plugin.get("name") == "ctier":
            found.append(plugin.get("config") or {})
    for service in deck.get("services") or []:
        for route in service.get("routes") or []:
            for plugin in route.get("plugins") or []:
                if plugin.get("name") == "ctier":
                    found.append(plugin.get("config") or {})
    return found


def _assert_config_matches_schema(conf: dict) -> None:
    extra = set(conf) - PLUGIN_FIELDS
    assert not extra, f"generator emitted keys the plugin schema does not declare: {sorted(extra)}"
    assert "tier" in conf and conf["tier"] in (1, 2, 3, 4)
    assert isinstance(conf.get("deployment"), str) and conf["deployment"]
    assert "composition" not in conf
    if "excluded" in conf:
        assert conf["excluded"] in (True, False)
    has_param = "bound_parameter" in conf
    has_max = "bound_max" in conf
    assert has_param == has_max, "bounds fields must be emitted together"
    if has_max:
        assert isinstance(conf["bound_max"], int)


def test_handler_does_not_consult_custody_except_to_persist_and_record():
    """1.1.7: the enforcement point must not ask custody whether an agent is paused."""
    text = HANDLER_LUA.read_text(encoding="utf-8")
    assert "introspect" not in text
    assert "userinfo" not in text
    assert "/v1/pending" in text
    assert "/v1/ledger" in text
    assert "/v1/floors" in text
    assert "/v1/decisions" not in text
    assert "paused" not in text.lower()
    # POST persist/ledger, GET floors on the timer — not a per-request consult.
    assert text.count("request_uri") == 2
    assert "ctier_floors" in text
    assert "ngx.timer.at" in text
    assert "ngx.timer.every" in text

    assert _schema_lua_fields() == PLUGIN_FIELDS
    assert "in_governed" in text
    assert "unassigned" in text
    assert "refuse_unassigned" in text


def test_handler_does_not_emit_withdrawn_names():
    text = HANDLER_LUA.read_text(encoding="utf-8")
    assert 'set_header("x-ctier-deployment"' in text
    assert 'set_header("x-ctier-composition"' not in text
    assert "config.composition is accepted" not in text
    assert 'relay["X-Correlation-Id"]' not in text


def test_generated_plugin_config_matches_schema_lua():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    deck = yaml.safe_load(generate(qualified, target="kong")["kong.yaml"])
    configs = _plugin_configs(deck)
    assert configs
    for conf in configs:
        _assert_config_matches_schema(conf)


def test_golden_plugin_config_matches_schema_lua():
    for case in sorted(p for p in KONG_ROOT.iterdir() if p.is_dir()):
        deck = yaml.safe_load((case / "expect" / "kong.yaml").read_text(encoding="utf-8"))
        for conf in _plugin_configs(deck):
            _assert_config_matches_schema(conf)


@pytest.mark.skipif(shutil.which("deck") is None, reason="deck not in toolchain")
def test_deck_file_validate_golden_offline():
    """decK local validate. Does not contact a gateway (see `deck file validate --help`)."""
    for case in sorted(p for p in KONG_ROOT.iterdir() if p.is_dir()):
        path = case / "expect" / "kong.yaml"
        result = subprocess.run(
            ["deck", "file", "validate", "--analytics=false", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"deck file validate failed on {path}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


@pytest.mark.skipif(shutil.which("luac") is None, reason="luac not in toolchain")
def test_luac_syntax_check_plugin():
    for path in (HANDLER_LUA, SCHEMA_LUA):
        result = subprocess.run(
            ["luac", "-p", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"luac -p {path}\n{result.stderr}"


@pytest.mark.skipif(shutil.which("luacheck") is None, reason="luacheck not in toolchain")
def test_luacheck_plugin():
    result = subprocess.run(
        ["luacheck", str(PLUGIN_DIR)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
