"""C13 witness. Generate against one composition, present another.

Does not apply — decided before the assertions below.

Both engines, both modes: generate refuses to emit. Rule `c13`.
The assignment computed from A is not written against B. The
mismatch never reaches the gateway. A request after the refuse
still executes under A's loaded assignment.

Not an enforcement-point refuse. The EP has only the compiled
assignment. A request does not carry a composition. Same
operations would be enacted if A's deck were loaded under B's
name. That is why the refuse is at generate.

Fragment and bundle do not differ on this case. They did before
the check: fragment already refused (`replace`, same route
names); bundle ignored `existing` and emitted B. The C13 check
makes the refuse the digest, on both modes, before replace or
replace-the-estate.

This witness shows this mismatch caught. It does not show every
mismatch. It says nothing about a composition that changes after
generation — that is the drift 38 and 41 measured.
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

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"
T1_PATH = "/accounts/12345/balance"


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
    assert _operations(first) == _operations(other)
    other_digest = sha256_hex(canonical_json(other))
    assert manifest["compositionDigest"] != other_digest
    return first, other


def _still_a(stack, produced: dict[str, str]) -> None:
    status, raw, _ = stack.request(
        "GET",
        T1_PATH,
        headers=stack.auth_headers(**{"X-Agent-Id": "agent-c13", "X-Task-Id": "task-c13"}),
    )
    assert status == 200, raw
    bound = json.loads(produced["ctier-generate.json"])["deploymentDigest"]
    artefact = produced.get("kong.yaml") or produced.get("apisix.yaml") or ""
    assert bound in artefact


def _witness(stack, *, target: str, mode: str, existing=None) -> None:
    first, other = _pair()
    produced = generate(first, target=target, mode=mode, existing=existing)
    stack.load_generated(produced)
    _still_a(stack, produced)
    with pytest.raises(GenerateError) as exc:
        generate(other, target=target, mode=mode, existing=produced)
    assert exc.value.rule == "c13", exc.value
    assert "does not apply" in str(exc.value)
    _still_a(stack, produced)


def test_kong_fragment_assignment_does_not_apply_to_another_composition(kong_stack):
    _witness(kong_stack, target="kong", mode="fragment", existing=load_fixture("kong"))


def test_kong_bundle_assignment_does_not_apply_to_another_composition(kong_stack):
    _witness(kong_stack, target="kong", mode="bundle")


def test_apisix_fragment_assignment_does_not_apply_to_another_composition(apisix_stack):
    _witness(apisix_stack, target="apisix", mode="fragment", existing=load_fixture("apisix"))


def test_apisix_bundle_assignment_does_not_apply_to_another_composition(apisix_stack):
    _witness(apisix_stack, target="apisix", mode="bundle")
