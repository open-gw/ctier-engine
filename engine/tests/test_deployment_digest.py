"""deploymentDigest: canonical over description, tiers, and agent identities."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from ctier.authz import AGENT_CLIENT
from ctier.compose import compose
from ctier.generate import deployment_digest, generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_generate import _declared, _spec


def _digest(files: dict[str, str]) -> str:
    return json.loads(files["ctier-generate.json"])["deploymentDigest"]


def _agents(*order: str) -> list[dict]:
    by_id = {
        AGENT_CLIENT: {"id": AGENT_CLIENT},
        "agent-sub-balance": {
            "id": "agent-sub-balance",
            "parent": AGENT_CLIENT,
            "operations": ["ok"],
        },
        "agent-other": {
            "id": "agent-other",
            "parent": AGENT_CLIENT,
            "operations": ["ok"],
        },
    }
    return [by_id[name] for name in order]


def _qualified(tmp_path: Path | None = None, name: str = "api.yaml"):
    raw = _spec({"/ok": {"get": _declared(1, "ok")}})
    if tmp_path is None:
        return compose(raw, [], NOW)[0]
    path = tmp_path / name
    path.write_bytes(raw)
    return compose(path, [], NOW)[0]


def test_identical_inputs_produce_identical_digests():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    a = generate(qualified, target="kong")
    b = generate(qualified, target="kong")
    assert _digest(a) == _digest(b)
    assert _digest(a) == deployment_digest(qualified)


def test_reordering_agent_declarations_does_not_change_the_digest():
    qualified = _qualified()
    a = generate(qualified, target="kong", agents=_agents(AGENT_CLIENT, "agent-sub-balance", "agent-other"))
    b = generate(qualified, target="kong", agents=_agents("agent-other", AGENT_CLIENT, "agent-sub-balance"))
    assert _digest(a) == _digest(b)
    ids_a = [c["id"] for c in yaml.safe_load(a["authorization.yaml"])["clients"]]
    ids_b = [c["id"] for c in yaml.safe_load(b["authorization.yaml"])["clients"]]
    assert ids_a != ids_b


def test_changing_one_entitlement_changes_the_digest():
    qualified = _qualified()
    base = [
        {"id": AGENT_CLIENT},
        {"id": "agent-sub-balance", "parent": AGENT_CLIENT, "operations": ["ok"]},
    ]
    changed = [
        {"id": AGENT_CLIENT},
        {"id": "agent-sub-balance", "parent": AGENT_CLIENT, "operations": []},
    ]
    a = generate(qualified, target="kong", agents=base)
    b = generate(qualified, target="kong", agents=changed)
    assert _digest(a) != _digest(b)


def test_changing_a_tier_declaration_changes_the_digest():
    qualified = _qualified()
    other = copy.deepcopy(qualified)
    other["paths"]["/ok"]["get"]["x-ctier-tier"] = 2
    a = generate(qualified, target="kong")
    b = generate(other, target="kong")
    assert _digest(a) != _digest(b)


def test_renaming_a_file_without_changing_content_does_not_change_the_digest(tmp_path: Path):
    a = generate(_qualified(tmp_path, "first.yaml"), target="kong")
    b = generate(_qualified(tmp_path, "second.yaml"), target="kong")
    assert _digest(a) == _digest(b)


def test_different_agent_topologies_produce_different_digests():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    a = generate(qualified, target="kong")
    b = generate(
        qualified,
        target="kong",
        agents=[
            {"id": AGENT_CLIENT},
            {
                "id": "agent-other",
                "parent": AGENT_CLIENT,
                "operations": ["getBalance"],
            },
        ],
    )
    assert _digest(a) != _digest(b)
