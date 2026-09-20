"""Live runtime-suite/0.3.0-draft. Kong and APISIX; Apigee excluded."""
from __future__ import annotations

import json

import pytest

from ctier.boundary import BoundaryFixture, Observation, dump_report, load_suite, run_suite
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.live.apisix_rig import CUSTODY as APISIX_CUSTODY
from tests.live.apisix_rig import CUSTODY_INTERNAL as APISIX_CUSTODY_INTERNAL
from tests.live.rig import CUSTODY, CUSTODY_INTERNAL, http
from tests.test_fragment import load_fixture

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"


def _echo_headers(payload: dict) -> dict[str, str]:
    raw = payload.get("headers") or {}
    return {str(k).lower(): str(v) for k, v in raw.items()}


def _decision_for(custody_base: str):
    def lookup(cid: str) -> dict | None:
        status, raw, _ = http("GET", custody_base + "/v1/ledger?type=decision")
        if status != 200:
            return None
        records = json.loads(raw.decode("utf-8")).get("records") or []
        match = [r for r in records if r.get("correlationId") == cid]
        return match[-1] if match else None

    return lookup


def _fixture(stack, custody_base: str, *, target: str, mode: str, capabilities: set[str],
             estate: str = ""):
    def send(method: str, path: str, headers: dict[str, str], body: str | None = None) -> Observation:
        kwargs = {"headers": stack.auth_headers(**headers)}
        if body is not None:
            kwargs["body"] = body
        status, payload = stack.echo_json(method, path, **kwargs)
        body = payload if isinstance(payload, dict) else {}
        return Observation(
            status=status,
            response_headers={},
            observer_headers=_echo_headers(payload),
            body=body,
        )

    return BoundaryFixture(
        capabilities=capabilities,
        send=send,
        decision_for=_decision_for(custody_base) if "recordSource" in capabilities else None,
        target=target,
        mode=mode,
        estate=estate,
    )


def _load(stack, target: str, mode: str, *, custody_internal: str, variant: str | None = None):
    qualified, _ = compose(REFERENCE, [], NOW)
    existing = load_fixture(target, variant=variant) if mode == "fragment" else None
    files = generate(
        qualified,
        target=target,
        mode=mode,
        existing=existing,
        custody={"url": custody_internal, "timeout_ms": 200},
    )
    stack.load_generated(files)
    return files


def _assert_header_contract(report: dict) -> None:
    by_id = {c["id"]: c for c in report["cases"]}
    assert by_id["strip-precedence"]["result"] == "skipped"
    assert by_id["strip-precedence"]["skipReason"].startswith("missing-capability:probe")
    header = [
        c for c in report["cases"]
        if c["id"] != "strip-precedence" and not str(c.get("skipReason") or "").startswith("when.")
        and "missing-capability:" not in str(c.get("skipReason") or "")
    ]
    failed = [c["id"] for c in header if c["result"] != "passed"]
    assert not failed, dump_report(report)
    assert report["failed"] == 0
    assert report.get("estate")
    assert by_id["forged-tier-not-surviving"]["result"] == "passed"


def test_kong_bundle_header_contract(kong_stack):
    _load(kong_stack, "kong", "bundle", custody_internal=CUSTODY_INTERNAL)
    report = run_suite(
        load_suite(),
        _fixture(
            kong_stack, CUSTODY,
            target="kong", mode="bundle", estate="bundle",
            capabilities={"observer", "recordSource"},
        ),
    )
    _assert_header_contract(report)
    assert report["estate"] == "bundle"


def test_kong_fragment_header_contract(kong_stack):
    """16c high-priority plugin (PRIORITY 10000) against existing/kong.yaml."""
    _load(kong_stack, "kong", "fragment", custody_internal=CUSTODY_INTERNAL)
    report = run_suite(
        load_suite(),
        _fixture(
            kong_stack, CUSTODY,
            target="kong", mode="fragment", estate="existing/kong.yaml",
            capabilities={"observer", "recordSource"},
        ),
    )
    _assert_header_contract(report)
    assert report["estate"] == "existing/kong.yaml"


def test_apisix_bundle_header_contract(apisix_stack):
    _load(apisix_stack, "apisix", "bundle", custody_internal=APISIX_CUSTODY_INTERNAL)
    report = run_suite(
        load_suite(),
        _fixture(
            apisix_stack, APISIX_CUSTODY,
            target="apisix", mode="bundle", estate="bundle",
            capabilities={"observer", "recordSource"},
        ),
    )
    _assert_header_contract(report)
    assert report["estate"] == "bundle"


def test_apisix_fragment_header_contract(apisix_stack):
    _load(apisix_stack, "apisix", "fragment", custody_internal=APISIX_CUSTODY_INTERNAL)
    report = run_suite(
        load_suite(),
        _fixture(
            apisix_stack, APISIX_CUSTODY,
            target="apisix", mode="fragment", estate="existing/apisix.yaml",
            capabilities={"observer", "recordSource"},
        ),
    )
    _assert_header_contract(report)
    assert report["estate"] == "existing/apisix.yaml"


def test_apisix_fragment_outside_slot_header_contract(apisix_stack):
    _load(
        apisix_stack, "apisix", "fragment",
        custody_internal=APISIX_CUSTODY_INTERNAL, variant="outside-slot",
    )
    report = run_suite(
        load_suite(),
        _fixture(
            apisix_stack, APISIX_CUSTODY,
            target="apisix", mode="fragment",
            estate="existing/apisix-outside-slot.yaml",
            capabilities={"observer", "recordSource"},
        ),
    )
    _assert_header_contract(report)
    assert report["estate"] == "existing/apisix-outside-slot.yaml"
