"""Pure C13: different composition, same operations.

Does not apply is decided here, before any live assertion. Both
engines. Both modes.

Fragment and bundle both refuse at generate. The assignment
computed from composition A is not emitted against composition B.
The mismatch never reaches a gateway. The enforcement point is
not asked. An estate fixture with no generate stamp is not this
check; fragment merge into that fixture still proceeds.

The other two mismatch shapes are not cases. Same composition,
one operation changed: the digest moves because an assignment
moved, so the refuse would not isolate C13. Forged digest: this
engine stamps what it computed; it does not re-hash the running
deck against a presented document.
"""
from __future__ import annotations

import copy
import json

import pytest

from ctier.canonical import canonical_json, sha256_hex
from ctier.compose import compose
from ctier.errors import GenerateError
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from ctier.validate import iter_operations
from tests.golden_util import NOW
from tests.test_fragment import load_fixture

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
TARGETS = ("kong", "apisix")
MODES = ("fragment", "bundle")


def _operations(doc: dict) -> list[tuple[str, str, str | None, object]]:
    rows = []
    for path, method, op, _params in iter_operations(doc):
        rows.append((
            method,
            path,
            op.get("operationId"),
            op.get("x-ctier-tier"),
        ))
    return sorted(rows)


def _pair():
    first, manifest = compose(REFERENCE, [], NOW)
    other = copy.deepcopy(first)
    info = dict(other.get("info") or {})
    info["description"] = (info.get("description") or "") + "\n# other-composition"
    other["info"] = info
    return first, manifest, other


def test_the_pair_is_the_pure_c13_case():
    first, manifest, other = _pair()
    assert _operations(first) == _operations(other)
    other_digest = sha256_hex(canonical_json(other))
    assert manifest["compositionDigest"] != other_digest
    assert manifest["compositionDigest"] == sha256_hex(canonical_json(first))


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("mode", MODES)
def test_assignment_does_not_apply_to_another_composition(target, mode):
    first, _manifest, other = _pair()
    produced = generate(first, target=target, mode=mode)
    bound = json.loads(produced["ctier-generate.json"])["deploymentDigest"]
    with pytest.raises(GenerateError) as exc:
        generate(other, target=target, mode=mode, existing=produced)
    assert exc.value.rule == "c13"
    assert "does not apply" in str(exc.value)
    assert json.loads(produced["ctier-generate.json"])["deploymentDigest"] == bound


@pytest.mark.parametrize("target", TARGETS)
def test_fragment_into_an_unstamped_estate_still_emits(target):
    first, _manifest, _other = _pair()
    files = generate(
        first, target=target, mode="fragment", existing=load_fixture(target),
    )
    assert "ctier-generate.json" in files


@pytest.mark.parametrize("target", TARGETS)
def test_same_composition_is_not_this_refuse(target):
    first, _manifest, _other = _pair()
    produced = generate(first, target=target, mode="bundle")
    again = generate(first, target=target, mode="bundle", existing=produced)
    assert (
        json.loads(again["ctier-generate.json"])["deploymentDigest"]
        == json.loads(produced["ctier-generate.json"])["deploymentDigest"]
    )
