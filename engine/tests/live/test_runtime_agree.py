"""Runtime suite: header and body agree on the agent instruction.

The pairing is one assertion. Presence of each field separately
would have passed while they disagreed.
"""
from __future__ import annotations

import json

import pytest

from ctier.boundary import BoundaryFixture, Observation, dump_report, load_suite, run_suite
from ctier.compose import compose
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW

pytestmark = pytest.mark.live

REFERENCE = SPEC_DIR / "consequence-tiered-api.yaml"


def _case(cid: str) -> dict:
    return next(c for c in load_suite()["cases"] if c["id"] == cid)


def _observation(status: int, raw: bytes, hdrs: dict[str, str]) -> Observation:
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        payload = {}
    body = payload if isinstance(payload, dict) else {}
    response = {str(k).lower(): str(v) for k, v in (hdrs or {}).items()}
    return Observation(
        status=status,
        response_headers=response,
        observer_headers={},
        body=body,
    )


def _fixture(stack, *, target: str, deployment: str) -> BoundaryFixture:
    def send(method: str, path: str, headers: dict[str, str], body: str | None = None) -> Observation:
        hdrs_in = dict(headers)
        if body is not None and not any(k.lower() == "content-type" for k in hdrs_in):
            hdrs_in["Content-Type"] = "application/json"
        status, raw, hdrs = stack.request(
            method, path,
            headers=stack.auth_headers(**hdrs_in),
            body=body,
        )
        return _observation(status, raw, hdrs)

    return BoundaryFixture(
        capabilities=set(),
        send=send,
        target=target,
        mode="bundle",
        estate="bundle",
        deployment=deployment,
    )


def _load(stack, target: str, *, custody=None) -> None:
    qualified, _ = compose(REFERENCE, [], NOW)
    files = generate(qualified, target=target, custody=custody)
    stack.load_generated(files)


def _assert_passed(report: dict, cid: str) -> None:
    by_id = {c["id"]: c for c in report["cases"]}
    assert by_id[cid]["result"] == "passed", dump_report(report)
    assert report["failed"] == 0, dump_report(report)


def _run(stack, *, target: str, deployment: str, cid: str, custody=None) -> None:
    _load(stack, target, custody=custody)
    report = run_suite(
        {"ctierSchema": load_suite()["ctierSchema"], "cases": [_case(cid)]},
        _fixture(stack, target=target, deployment=deployment),
    )
    _assert_passed(report, cid)


def test_kong_tier_4_header_and_body_agree(kong_stack):
    _run(kong_stack, target="kong", deployment="level-2", cid="tier-4-instruction-agrees")


def test_apisix_tier_4_header_and_body_agree(apisix_stack):
    _run(apisix_stack, target="apisix", deployment="level-2", cid="tier-4-instruction-agrees")


def test_kong_provisioning_header_and_body_agree(kong_stack):
    _run(kong_stack, target="kong", deployment="level-2", cid="provisioning-instruction-agrees")


def test_apisix_provisioning_header_and_body_agree(apisix_stack):
    _run(apisix_stack, target="apisix", deployment="level-2", cid="provisioning-instruction-agrees")
