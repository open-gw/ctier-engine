# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""generate: qualified spec + target + mode -> directory of files.

Pure. No clock, no network, no state. Byte-identical for identical input.
"""
from __future__ import annotations

import json
import re
from typing import Union
from urllib.parse import urlparse

import yaml

from .authz import (
    AGENT_CLIENT,
    AGENT_SECRET,
    JWT_CLAIM,
    JWT_CLAIM_VALUE,
    authorization_document,
    authorization_files,
    jwt_plugin,
    kong_consumers,
    public_pem,
    scope_name,
)
from .identifiers import (
    ACTION_CONTINUE,
    AGENT_SUSPENDED_BODY,
    CUSTODY_UNAVAILABLE_BODY,
    HEADER_AGENT_ACTION,
    PROVISIONING_DEFECT_BODY,
    UNASSIGNED_BODY,
    required_instruction_headers_for,
)
from .canonical import canonical_json, sha256_hex
from .classifier import compute_tier, escalate
from .compose import Source, _load
from .errors import GenerateError
from .fragment import apply_or_refuse
from .models import Criteria, Tier
from .validate import iter_operations, validate_openapi_extensions

GENERATOR_VERSION = "0.3.0"
TARGETS = frozenset({"apigee", "kong", "apisix"})
MODES = frozenset({"bundle", "fragment"})
# Explicit millisecond bounds, not library defaults. Persist/ledger hops are
# 200 ms; the floor poller interval is 1000 ms. The published floor is stale
# by up to one interval, which compounds with the one-request-late property.
DEFAULT_CUSTODY_TIMEOUT_MS = 200
DEFAULT_FLOOR_POLL_MS = 1000
# Apigee has no gateway-log sink the kit can GET. When a records URL is
# compiled, refuse and execute paths POST /v1/ledger (fail-open). Trace
# print() remains; it is not kit_records.
DEFAULT_RECORDS_TIMEOUT_MS = 200
DEFAULT_RECORDS_URL = "https://records.example.invalid"

# Closed set kept as documentation of names the generator itself
# understands. 1.5.0 strips the whole `x-ctier-*` namespace on
# ingress, not this list. Apigee has no wildcard; that is a JS
# prefix walk. Kong already prefix-scans. APISIX Lua does the same.
CTIER_HEADERS = (
    "x-ctier-tier",
    "x-ctier-criteria",
    "x-ctier-exclude",
    "x-ctier-bounds",
    "x-ctier-handoff",
    "x-ctier-status",
    "x-ctier-recommended-at",
    "x-ctier-rationale",
    "x-ctier-weight",
    "x-ctier-escalate-to",
    "x-ctier-reverses",
    "x-ctier-defaults",
    "x-ctier-declared",
    "x-ctier-composition",
    "x-ctier-deployment",
    "x-ctier-operation",
)

# Outside the namespace. A prefix strip does not catch them.
STRIP_ALIASES = (
    "X-Correlation-Id",
    "Idempotency-Key",
    "X-Idempotency-Key",
)

HEADER_CORRELATION = "x-ctier-correlation-id"
HEADER_IDEMPOTENCY = "Idempotency-Key"

_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _normalise_custody(custody: dict | None) -> dict | None:
    """Select level-3 when a custody block is present; level-2 when it is not."""
    if custody is None:
        return None
    if not isinstance(custody, dict) or not custody.get("url"):
        raise GenerateError("custody", "custody.url is required")
    timeout = int(custody.get("timeout_ms", DEFAULT_CUSTODY_TIMEOUT_MS))
    if timeout <= 0:
        raise GenerateError("custody", "timeout_ms must be a positive millisecond bound")
    poll = int(custody.get("floor_poll_ms", DEFAULT_FLOOR_POLL_MS))
    if poll <= 0:
        raise GenerateError("custody", "floor_poll_ms must be a positive millisecond bound")
    out = {"url": str(custody["url"]), "timeout_ms": timeout, "floor_poll_ms": poll}
    fallback = custody.get("ledger_fallback")
    if fallback:
        out["ledger_fallback"] = str(fallback)
    return out


def _normalise_records(records: dict | None) -> dict | None:
    """Optional retrievable sink for Apigee. Kong/APISIX ignore this."""
    if records is None:
        return None
    if not isinstance(records, dict) or not records.get("url"):
        raise GenerateError("records", "records.url is required")
    timeout = int(records.get("timeout_ms", DEFAULT_RECORDS_TIMEOUT_MS))
    if timeout <= 0:
        raise GenerateError("records", "timeout_ms must be a positive millisecond bound")
    return {"url": str(records["url"]), "timeout_ms": timeout}


def _handoff_authority(op: dict) -> str | None:
    raw = op.get("x-ctier-handoff")
    if isinstance(raw, dict) and raw.get("authority"):
        return str(raw["authority"])
    return None


def _document(source: Union[Source, dict]) -> dict:
    if isinstance(source, dict):
        return source
    _raw, doc, _path = _load(source)
    return doc


def _proxy_name(doc: dict) -> str:
    title = ((doc.get("info") or {}).get("title") or "ctier").strip()
    slug = _NAME.sub("-", title).strip("-._").lower()
    return slug or "ctier"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _xml_decl() -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def _policy_strip() -> str:
    """Aliases outside `x-ctier-*`. The namespace itself is JS-StripCtierNamespace."""
    headers = "\n".join(
        f'        <Header name="{name}"/>' for name in STRIP_ALIASES
    )
    return (
        _xml_decl()
        + "<AssignMessage name=\"SC-StripCtierHeaders\">\n"
        "  <!-- 1.5.0: aliases a prefix strip misses. The namespace is\n"
        "       stripped by JS-StripCtierNamespace, not this closed list. -->\n"
        "  <DisplayName>SC-StripCtierHeaders</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <Remove>\n"
        "    <Headers>\n"
        f"{headers}\n"
        "    </Headers>\n"
        "  </Remove>\n"
        "</AssignMessage>\n"
    )


def _policy_js_strip() -> str:
    return (
        _xml_decl()
        + "<Javascript name=\"JS-StripCtierNamespace\" timeLimit=\"200\">\n"
        "  <DisplayName>JS-StripCtierNamespace</DisplayName>\n"
        "  <ResourceURL>jsc://strip-ctier-namespace.js</ResourceURL>\n"
        "</Javascript>\n"
    )


def _js_strip_namespace() -> str:
    return (
        "/* 1.5.0: no agent-supplied x-ctier-* header reaches the backend. */\n"
        "var names = (context.getVariable('request.headers.names') || '') + '';\n"
        "names = names.replace(/\\[|\\]/g, '');\n"
        "var parts = names.split(',');\n"
        "for (var i = 0; i < parts.length; i++) {\n"
        "  var n = parts[i].replace(/^\\s+|\\s+$/g, '');\n"
        "  if (!n) continue;\n"
        "  var lower = n.toLowerCase();\n"
        "  if (lower.indexOf('x-ctier-') === 0) {\n"
        "    context.removeVariable('request.header.' + n);\n"
        "  }\n"
        "}\n"
    )


def _policy_js_provenance() -> str:
    return (
        _xml_decl()
        + "<Javascript name=\"JS-SetUpstreamProvenance\" timeLimit=\"200\">\n"
        "  <DisplayName>JS-SetUpstreamProvenance</DisplayName>\n"
        "  <ResourceURL>jsc://set-upstream-provenance.js</ResourceURL>\n"
        "</Javascript>\n"
    )


def _js_set_upstream_provenance() -> str:
    return (
        "/* Mint the join key on the forwarding path. */\n"
        "var cid = context.getVariable('messageid') || ('apigee-' + Date.now());\n"
        "function _ctierIso(d) {\n"
        "  function p(n) { return n < 10 ? '0' + n : String(n); }\n"
        "  return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate())\n"
        "    + 'T' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ':' + p(d.getUTCSeconds()) + 'Z';\n"
        "}\n"
        "var agent = context.getVariable('request.header.x-agent-id') || 'unknown';\n"
        "var task = context.getVariable('request.header.x-task-id');\n"
        "var rec = {\n"
        "  ctierSchema: 'decision-record/0.2.0',\n"
        "  type: 'decision',\n"
        "  id: String(cid),\n"
        "  timestamp: _ctierIso(new Date()),\n"
        "  operationAnchor: context.getVariable('ctier.operation') || 'undeclared',\n"
        "  agentId: agent,\n"
        "  correlationScope: task || agent,\n"
        "  correlationId: String(cid),\n"
        "  declaredTier: parseInt(context.getVariable('ctier.tier'), 10) || 4,\n"
        "  appliedTier: parseInt(context.getVariable('ctier.tier'), 10) || 4,\n"
        "  escalationReason: 'none',\n"
        "  disposition: 'execute',\n"
        "  idempotencyKey: String(cid),\n"
        "  deploymentDigest: context.getVariable('ctier.deployment')\n"
        "};\n"
        "var blob = JSON.stringify(rec);\n"
        "print('[ctier-decision] ' + blob);\n"
        "context.setVariable('ctier.record.json', blob);\n"
        "context.setVariable('request.header.x-ctier-correlation-id', cid);\n"
    )


def _policy_js_record_refuse() -> str:
    return (
        _xml_decl()
        + "<Javascript name=\"JS-RecordRefuse\" timeLimit=\"200\">\n"
        "  <DisplayName>JS-RecordRefuse</DisplayName>\n"
        "  <ResourceURL>jsc://record-refuse.js</ResourceURL>\n"
        "</Javascript>\n"
    )


def _js_record_refuse() -> str:
    """Build a decision-record for PostFlow refuses before RaiseFault."""
    return (
        "/* Decision on a refuse path. Trace print is not kit_records. */\n"
        "var cid = context.getVariable('messageid') || ('apigee-' + Date.now());\n"
        "function _ctierIso(d) {\n"
        "  function p(n) { return n < 10 ? '0' + n : String(n); }\n"
        "  return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate())\n"
        "    + 'T' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ':' + p(d.getUTCSeconds()) + 'Z';\n"
        "}\n"
        "var agent = context.getVariable('request.header.x-agent-id') || 'unknown';\n"
        "var task = context.getVariable('request.header.x-task-id');\n"
        "var tier = parseInt(context.getVariable('ctier.tier'), 10) || 4;\n"
        "var excluded = context.getVariable('ctier.excluded') === 'true';\n"
        "var declared = context.getVariable('ctier.declared') === 'true';\n"
        "var op = context.getVariable('ctier.operation') || 'undeclared';\n"
        "var disposition;\n"
        "var reason;\n"
        "var applied = tier;\n"
        "if (excluded || tier === 3) {\n"
        "  disposition = 'refuse-provisioning';\n"
        "  reason = excluded ? 'excluded' : 'class-3-without-persist';\n"
        "} else {\n"
        "  disposition = 'refuse-and-suspend';\n"
        "  applied = 4;\n"
        "  reason = declared ? 'classified-refuse' : 'undeclared-operation';\n"
        "}\n"
        "var rec = {\n"
        "  ctierSchema: 'decision-record/0.2.0',\n"
        "  type: 'decision',\n"
        "  id: String(cid),\n"
        "  timestamp: _ctierIso(new Date()),\n"
        "  operationAnchor: op,\n"
        "  agentId: agent,\n"
        "  correlationScope: task || agent,\n"
        "  correlationId: String(cid),\n"
        "  declaredTier: declared ? tier : 4,\n"
        "  appliedTier: applied,\n"
        "  escalationReason: reason,\n"
        "  disposition: disposition,\n"
        "  idempotencyKey: String(cid),\n"
        "  deploymentDigest: context.getVariable('ctier.deployment')\n"
        "};\n"
        "var blob = JSON.stringify(rec);\n"
        "print('[ctier-decision] ' + blob);\n"
        "context.setVariable('ctier.record.json', blob);\n"
    )


def _policy_sc_record_decision(records: dict) -> str:
    url = _escape(records["url"].rstrip("/"))
    timeout = int(records["timeout_ms"])
    return (
        _xml_decl()
        + "<ServiceCallout name=\"SC-RecordDecision\" continueOnError=\"true\">\n"
        "  <DisplayName>SC-RecordDecision</DisplayName>\n"
        "  <Request clearPayload=\"true\">\n"
        "    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "    <Set>\n"
        "      <Verb>POST</Verb>\n"
        "      <Path>/v1/ledger</Path>\n"
        "      <Headers>\n"
        "        <Header name=\"Content-Type\">application/json</Header>\n"
        "      </Headers>\n"
        "      <Payload contentType=\"application/json\">{ctier.record.json}</Payload>\n"
        "    </Set>\n"
        "  </Request>\n"
        "  <Response>ctierRecord</Response>\n"
        "  <HTTPTargetConnection>\n"
        f"    <URL>{url}</URL>\n"
        "    <Properties>\n"
        f"      <Property name=\"io.timeout.millis\">{timeout}</Property>\n"
        "      <Property name=\"success.codes\">1xx,2xx,3xx,4xx,5xx</Property>\n"
        "    </Properties>\n"
        "  </HTTPTargetConnection>\n"
        "</ServiceCallout>\n"
    )


def _policy_default_tier() -> str:
    return (
        _xml_decl()
        + "<AssignMessage name=\"AM-DefaultTier\">\n"
        "  <DisplayName>AM-DefaultTier</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.tier</Name>\n"
        "    <Value>4</Value>\n"
        "  </AssignVariable>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.declared</Name>\n"
        "    <Value>false</Value>\n"
        "  </AssignVariable>\n"
        "</AssignMessage>\n"
    )


def _policy_deployment(digest: str) -> str:
    return (
        _xml_decl()
        + "<AssignMessage name=\"AM-Deployment\">\n"
        "  <DisplayName>AM-Deployment</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.deployment</Name>\n"
        f"    <Value>{_escape(digest)}</Value>\n"
        "  </AssignVariable>\n"
        "</AssignMessage>\n"
    )


def _policy_rf_tier4() -> str:
    payload = AGENT_SUSPENDED_BODY
    instruction = required_instruction_headers_for(423, payload)
    header_lines = "".join(
        f"        <Header name=\"{name}\">{value}</Header>\n"
        for name, value in instruction.items()
    )
    return (
        _xml_decl()
        + "<RaiseFault name=\"RF-Tier4\">\n"
        "  <DisplayName>RF-Tier4</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <FaultResponse>\n"
        "    <Set>\n"
        "      <StatusCode>423</StatusCode>\n"
        "      <ReasonPhrase>Locked</ReasonPhrase>\n"
        "      <Headers>\n"
        "        <Header name=\"X-Ctier-Tier\">{ctier.tier}</Header>\n"
        f"{header_lines}"
        "        <Header name=\"Cache-Control\">no-store</Header>\n"
        "      </Headers>\n"
        f"      <Payload contentType=\"application/json\">{payload}</Payload>\n"
        "    </Set>\n"
        "  </FaultResponse>\n"
        "</RaiseFault>\n"
    )


def _policy_rf_provisioning() -> str:
    payload = PROVISIONING_DEFECT_BODY
    return (
        _xml_decl()
        + "<RaiseFault name=\"RF-Provisioning\">\n"
        "  <DisplayName>RF-Provisioning</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <FaultResponse>\n"
        "    <Set>\n"
        "      <StatusCode>403</StatusCode>\n"
        "      <ReasonPhrase>Forbidden</ReasonPhrase>\n"
        "      <Headers>\n"
        f"        <Header name=\"{HEADER_AGENT_ACTION}\">{ACTION_CONTINUE}</Header>\n"
        "        <Header name=\"Cache-Control\">no-store</Header>\n"
        "      </Headers>\n"
        f"      <Payload contentType=\"application/json\">{payload}</Payload>\n"
        "    </Set>\n"
        "  </FaultResponse>\n"
        "</RaiseFault>\n"
    )


def _policy_rf_withhold() -> str:
    """Relay the body custody returned. The generator does not construct it."""
    return (
        _xml_decl()
        + "<RaiseFault name=\"RF-Withhold\">\n"
        "  <DisplayName>RF-Withhold</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <FaultResponse>\n"
        "    <Set>\n"
        "      <StatusCode>202</StatusCode>\n"
        "      <ReasonPhrase>Accepted</ReasonPhrase>\n"
        "      <Headers>\n"
        "        <Header name=\"Content-Type\">application/json</Header>\n"
        "        <Header name=\"Cache-Control\">no-store</Header>\n"
        f"        <Header name=\"{HEADER_AGENT_ACTION}\">{{custodyPending.header.{HEADER_AGENT_ACTION}}}</Header>\n"
        "        <Header name=\"x-ctier-correlation-id\">{custodyPending.header.x-ctier-correlation-id}</Header>\n"
        "        <Header name=\"X-Ctier-Tier\">{custodyPending.header.X-Ctier-Tier}</Header>\n"
        "      </Headers>\n"
        "      <Payload contentType=\"application/json\">{custodyPending.content}</Payload>\n"
        "    </Set>\n"
        "  </FaultResponse>\n"
        "</RaiseFault>\n"
    )


def _policy_rf_custody_unavailable() -> str:
    payload = CUSTODY_UNAVAILABLE_BODY
    return (
        _xml_decl()
        + "<RaiseFault name=\"RF-CustodyUnavailable\">\n"
        "  <DisplayName>RF-CustodyUnavailable</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <FaultResponse>\n"
        "    <Set>\n"
        "      <StatusCode>503</StatusCode>\n"
        "      <ReasonPhrase>Service Unavailable</ReasonPhrase>\n"
        "      <Headers>\n"
        "        <Header name=\"Retry-After\">5</Header>\n"
        "        <Header name=\"Cache-Control\">no-store</Header>\n"
        "      </Headers>\n"
        f"      <Payload contentType=\"application/json\">{payload}</Payload>\n"
        "    </Set>\n"
        "  </FaultResponse>\n"
        "</RaiseFault>\n"
    )


def _policy_sc_custody_pending(custody: dict) -> str:
    url = _escape(custody["url"].rstrip("/"))
    timeout = int(custody["timeout_ms"])
    return (
        _xml_decl()
        + "<ServiceCallout name=\"SC-CustodyPending\">\n"
        "  <DisplayName>SC-CustodyPending</DisplayName>\n"
        "  <Request>\n"
        "    <Set>\n"
        "      <Verb>POST</Verb>\n"
        "      <Path>/v1/pending</Path>\n"
        "      <Headers>\n"
        "        <Header name=\"Content-Type\">application/json</Header>\n"
        "      </Headers>\n"
        "      <Payload contentType=\"application/json\">{\n"
        "  \"method\": \"{request.verb}\",\n"
        "  \"path\": \"{proxy.pathsuffix}\",\n"
        "  \"operationAnchor\": \"{ctier.operation}\",\n"
        "  \"agentId\": \"{request.header.X-Agent-Id}\",\n"
        "  \"declaredTier\": {ctier.tier},\n"
        "  \"appliedTier\": {ctier.tier},\n"
        "  \"deploymentDigest\": \"{ctier.deployment}\"\n"
        "}</Payload>\n"
        "    </Set>\n"
        "  </Request>\n"
        "  <Response>custodyPending</Response>\n"
        "  <HTTPTargetConnection>\n"
        f"    <URL>{url}</URL>\n"
        "    <Properties>\n"
        f"      <Property name=\"io.timeout.millis\">{timeout}</Property>\n"
        "    </Properties>\n"
        "  </HTTPTargetConnection>\n"
        "</ServiceCallout>\n"
    )


def _postflow_xml(
    custody: dict | None = None,
    *,
    observe: bool = False,
    records: dict | None = None,
) -> str:
    if observe:
        return (
            "  <PostFlow>\n"
            "    <Request/>\n"
            "  </PostFlow>\n"
        )
    record_steps = ""
    if records is not None:
        record_steps = (
            "      <Step>\n"
            "        <Name>JS-RecordRefuse</Name>\n"
            "        <Condition>(ctier.excluded = \"true\") or (ctier.tier = \"3\") "
            "or (ctier.tier = \"4\")</Condition>\n"
            "      </Step>\n"
            "      <Step>\n"
            "        <Name>SC-RecordDecision</Name>\n"
            "        <Condition>(ctier.excluded = \"true\") or (ctier.tier = \"3\") "
            "or (ctier.tier = \"4\")</Condition>\n"
            "      </Step>\n"
        )
    if custody is None:
        t3 = (
            "      <Step>\n"
            "        <Name>RF-Provisioning</Name>\n"
            "        <Condition>(ctier.excluded = \"true\") or (ctier.tier = \"3\")</Condition>\n"
            "      </Step>\n"
        )
    else:
        t3 = (
            "      <Step>\n"
            "        <Name>RF-Provisioning</Name>\n"
            "        <Condition>ctier.excluded = \"true\"</Condition>\n"
            "      </Step>\n"
            "      <Step>\n"
            "        <Name>SC-CustodyPending</Name>\n"
            "        <Condition>ctier.tier = \"3\"</Condition>\n"
            "      </Step>\n"
            "      <Step>\n"
            "        <Name>RF-CustodyUnavailable</Name>\n"
            "        <Condition>(ctier.tier = \"3\") and (custodyPending.status.code != 202)</Condition>\n"
            "      </Step>\n"
            "      <Step>\n"
            "        <Name>RF-Withhold</Name>\n"
            "        <Condition>ctier.tier = \"3\"</Condition>\n"
            "      </Step>\n"
        )
    return (
        "  <PostFlow>\n"
        "    <Request>\n"
        f"{record_steps}"
        f"{t3}"
        "      <Step>\n"
        "        <Name>RF-Tier4</Name>\n"
        "        <Condition>ctier.tier = \"4\"</Condition>\n"
        "      </Step>\n"
        "    </Request>\n"
        "  </PostFlow>\n"
    )


def _target_xml(doc: dict, *, records: dict | None = None) -> str:
    servers = doc.get("servers") or []
    url = "https://example.invalid"
    if servers and isinstance(servers[0], dict) and servers[0].get("url"):
        url = str(servers[0]["url"])
    record_step = ""
    if records is not None:
        record_step = (
            "      <Step>\n"
            "        <Name>SC-RecordDecision</Name>\n"
            "      </Step>\n"
        )
    return (
        _xml_decl()
        + "<TargetEndpoint name=\"default\">\n"
        "  <PreFlow>\n"
        "    <Request>\n"
        "      <Step>\n"
        "        <Name>JS-SetUpstreamProvenance</Name>\n"
        "      </Step>\n"
        f"{record_step}"
        "    </Request>\n"
        "  </PreFlow>\n"
        "  <HTTPTargetConnection>\n"
        f"    <URL>{_escape(url)}</URL>\n"
        "  </HTTPTargetConnection>\n"
        "</TargetEndpoint>\n"
    )


def _proxy_root_xml(name: str) -> str:
    return (
        _xml_decl()
        + f"<APIProxy name=\"{_escape(name)}\">\n"
        f"  <DisplayName>{_escape(name)}</DisplayName>\n"
        "</APIProxy>\n"
    )


def _openapi_segments(path: str) -> list[str]:
    return [s for s in path.split("/") if s]


def _is_template(segment: str) -> bool:
    return segment.startswith("{") and segment.endswith("}")


def matches_path(path: str) -> str:
    """OpenAPI template -> Apigee MatchesPath. * matches one segment."""
    parts = ["*" if _is_template(s) else s for s in _openapi_segments(path)]
    return "/" + "/".join(parts) if parts else "/"


def flow_sort_key(path: str, method: str, operation_id: str) -> tuple:
    """Literal segments before templated, left to right; longer prefix first."""
    segs = _openapi_segments(path)
    coded = tuple((1 if _is_template(s) else 0, s) for s in segs)
    pad = ((2, ""),) * (32 - len(segs))
    return (coded + pad, -len(segs), method, operation_id)


def _policy_name(prefix: str, operation_id: str) -> str:
    slug = _NAME.sub("-", operation_id).strip("-._") or "operation"
    return f"{prefix}-{slug}"


def _resolved_tier(op: dict) -> int | None:
    """Compile the decision, not the declaration.

    Classifier stage 2: the higher of declared and computed, when both exist.
    """
    if op.get("x-ctier-exclude") is True:
        return None
    declared = int(op["x-ctier-tier"]) if "x-ctier-tier" in op else None
    computed = None
    if isinstance(op.get("x-ctier-criteria"), dict):
        computed = int(compute_tier(Criteria.model_validate(op["x-ctier-criteria"])))
    if declared is None:
        return computed
    if computed is None:
        return declared
    return max(declared, computed)


def _operation_bounds(op: dict) -> tuple[str | None, int | None]:
    """Both fields or neither. Matches exceeds_declared_bounds."""
    raw = op.get("x-ctier-bounds")
    if not isinstance(raw, dict):
        return None, None
    parameter = raw.get("parameter")
    maximum = raw.get("max")
    if not parameter or maximum is None:
        return None, None
    return str(parameter), int(maximum)


def _escalated_tier(tier: int) -> int:
    return int(escalate(Tier(tier)))


def _classified_operations(doc: dict) -> list[dict]:
    rows = []
    for path, method, op, _pp in iter_operations(doc):
        excluded = op.get("x-ctier-exclude") is True
        parameter, maximum = _operation_bounds(op)
        tier = _resolved_tier(op)
        if not excluded and tier is None:
            continue
        oid = op.get("operationId") or f"{method}-{path}"
        rows.append({
            "path": path,
            "method": method,
            "operationId": oid,
            "tier": tier,
            "excluded": excluded,
            "bound_parameter": parameter,
            "bound_max": maximum,
            "handoff_authority": _handoff_authority(op),
        })
    rows.sort(key=lambda r: flow_sort_key(r["path"], r["method"], r["operationId"]))
    return rows


def _all_operations(doc: dict) -> list[dict]:
    """Every operation, classified or not. Stable order: path, method, id."""
    rows = []
    for path, method, op, _pp in iter_operations(doc):
        excluded = op.get("x-ctier-exclude") is True
        tier = _resolved_tier(op)
        oid = op.get("operationId") or f"{method}-{path}"
        parameter, maximum = _operation_bounds(op)
        rows.append({
            "path": path,
            "method": method,
            "operationId": oid,
            "tier": tier,
            "excluded": excluded,
            "classified": excluded or tier is not None,
            "bound_parameter": parameter,
            "bound_max": maximum,
            "handoff_authority": _handoff_authority(op),
        })
    rows.sort(key=lambda r: (r["path"], r["method"], r["operationId"]))
    return rows


_CAPTURE = re.compile(r"[^A-Za-z0-9_]")


def kong_path(template: str) -> str:
    """OpenAPI template -> Kong 3 regex path, one segment per parameter."""
    parts = []
    for seg in _openapi_segments(template):
        if _is_template(seg):
            name = _CAPTURE.sub("_", seg[1:-1]) or "id"
            if name[0].isdigit():
                name = "p_" + name
            parts.append(f"(?<{name}>[^/]+)")
        else:
            parts.append(re.escape(seg))
    return "~/" + "/".join(parts) + "$"


def kong_regex_priority(template: str) -> int:
    """Literal segments raise priority. Kong considers regex routes before
    prefix routes; same-priority regex order is undefined, so the generator
    sets this from the path rather than sorting document order."""
    return sum(0 if _is_template(s) else 1 for s in _openapi_segments(template))


def _target_url(doc: dict) -> str:
    servers = doc.get("servers") or []
    if servers and isinstance(servers[0], dict) and servers[0].get("url"):
        return str(servers[0]["url"])
    return "https://example.invalid"


def _canonical_tiers(doc: dict) -> list[dict]:
    """Tier declarations as the generator sees them. Sorted; no file paths."""
    rows = []
    for row in _all_operations(doc):
        rows.append({
            "excluded": bool(row["excluded"]),
            "method": row["method"],
            "operationId": row["operationId"],
            "path": row["path"],
            "tier": row["tier"],
        })
    return rows


def _canonical_identities(doc: dict, agents=None) -> list[dict]:
    """Declared agent identities and entitlements. Sorted by id; scopes sorted."""
    auth = authorization_document(_all_operations(doc), agents=agents)
    out = []
    for client in auth["clients"]:
        item = {
            "id": client["id"],
            "scopes": sorted(client["scopes"]),
        }
        if client.get("parent"):
            item["parent"] = client["parent"]
        out.append(item)
    out.sort(key=lambda item: item["id"])
    return out


def deployment_input(doc: dict, agents=None) -> dict:
    """Canonical inputs the generator consumed. Keys sorted at serialisation."""
    return {
        "agents": _canonical_identities(doc, agents),
        "composed": doc,
        "tiers": _canonical_tiers(doc),
    }


def deployment_digest(doc: dict, agents=None) -> str:
    """Digest over composed description, tier declarations, and agent identities.

    Regenerating from identical inputs produces an identical digest. A change
    to any input changes it. Declaration order and file names are not inputs.
    """
    return sha256_hex(canonical_json(deployment_input(doc, agents)))


def _route_slug(operation_id: str) -> str:
    return _NAME.sub("-", operation_id).strip("-._") or "operation"


def _governed_manifest(doc: dict) -> list[dict]:
    """The operations this generation covers. Discoverable without the deck."""
    rows = []
    for row in _all_operations(doc):
        if row["classified"]:
            assignment: int | str = 4 if row["excluded"] else int(row["tier"])
        else:
            assignment = "undeclared"
        rows.append({
            "assignment": assignment,
            "method": row["method"].upper(),
            "operation": row["operationId"],
            "path": row["path"],
        })
    return rows


def _governed_route_names(doc: dict) -> list[str]:
    return [_route_slug(row["operationId"]) for row in _all_operations(doc)]


def _bound_digest(existing: dict[str, str] | None) -> tuple[str, str] | None:
    """Digest a prior generate stamped, if the artefact carries one."""
    if not existing:
        return None
    raw = existing.get("ctier-generate.json")
    if not raw:
        return None
    try:
        meta = json.loads(raw)
    except ValueError:
        return None
    composition = meta.get("compositionDigest")
    if isinstance(composition, str) and composition:
        return ("composition", composition)
    deployment = meta.get("deploymentDigest")
    if isinstance(deployment, str) and deployment:
        return ("deployment", deployment)
    return None


def _refuse_foreign_assignment(doc: dict, agents, existing: dict[str, str] | None) -> None:
    """An assignment computed from one composition does not apply to another.

    Detected at generate. The mismatch is not emitted. The enforcement
    point never sees it. Bundle and fragment both refuse when `existing`
    carries a prior generate stamp that does not match the presented
    document. An estate fixture with no stamp is not this check.
    """
    bound = _bound_digest(existing)
    if bound is None:
        return
    kind, digest = bound
    presented = (
        sha256_hex(canonical_json(doc))
        if kind == "composition"
        else deployment_digest(doc, agents)
    )
    if digest != presented:
        raise GenerateError(
            "c13",
            "assignment does not apply to a different composition",
        )


def _generate_meta(
    digest: str, target: str, mode: str, governed: list[dict] | None = None,
) -> str:
    payload: dict = {
        "deploymentDigest": digest,
        "generator": {
            "mode": mode,
            "target": target,
            "version": GENERATOR_VERSION,
        },
    }
    if governed is not None:
        payload["governed-set"] = governed
    return json.dumps(payload, indent=2) + "\n"


def _kong_plugin_config(
    row: dict, digest: str, custody: dict | None = None, *, observe: bool = False,
) -> dict:
    conf: dict = {
        "tier": 4 if row["excluded"] else int(row["tier"]),
        "deployment": digest,
        "operation": row["operationId"],
        "excluded": bool(row["excluded"]),
    }
    if not row.get("excluded"):
        conf["required_scope"] = scope_name(row["operationId"])
    if row.get("bound_parameter") is not None and row.get("bound_max") is not None:
        conf["bound_parameter"] = str(row["bound_parameter"])
        conf["bound_max"] = int(row["bound_max"])
    if custody is not None and row.get("handoff_authority"):
        conf["handoff_authority"] = str(row["handoff_authority"])
    if custody is not None:
        conf["custody_url"] = custody["url"]
        conf["custody_timeout_ms"] = int(custody["timeout_ms"])
        conf["floor_poll_ms"] = int(custody["floor_poll_ms"])
        if custody.get("ledger_fallback"):
            conf["ledger_fallback"] = custody["ledger_fallback"]
    if observe:
        conf["observe"] = True
    return conf


def _generate_kong(
    doc: dict, digest: str, mode: str, custody: dict | None = None,
    *,
    agents=None,
    observe: bool = False,
) -> dict[str, str]:
    routes = []
    for row in _all_operations(doc):
        route: dict = {
            "name": _route_slug(row["operationId"]),
            "methods": [row["method"].upper()],
            "paths": [kong_path(row["path"])],
            "strip_path": False,
            "regex_priority": kong_regex_priority(row["path"]),
        }
        if row["classified"]:
            ctier_conf = _kong_plugin_config(row, digest, custody, observe=observe)
            plugins = [jwt_plugin(), {"name": "ctier", "config": ctier_conf}]
            route["plugins"] = plugins
        routes.append(route)
    global_conf: dict = {
        "tier": 4,
        "deployment": digest,
        "excluded": False,
        "governed-set": _governed_route_names(doc),
    }
    if custody is not None:
        global_conf["custody_url"] = custody["url"]
        global_conf["custody_timeout_ms"] = int(custody["timeout_ms"])
        global_conf["floor_poll_ms"] = int(custody["floor_poll_ms"])
        if custody.get("ledger_fallback"):
            global_conf["ledger_fallback"] = custody["ledger_fallback"]
    if observe:
        global_conf["observe"] = True
    deck = {
        "_format_version": "3.0",
        "consumers": kong_consumers(),
        "services": [{
            "name": _proxy_name(doc),
            "url": _target_url(doc),
            "routes": routes,
        }],
        "plugins": [{
            "name": "ctier",
            "config": global_conf,
        }],
    }
    text = yaml.safe_dump(
        deck,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
    files = {
        "kong.yaml": text,
        "ctier-generate.json": _generate_meta(
            digest, "kong", mode, _governed_manifest(doc),
        ),
    }
    files.update(authorization_files(_all_operations(doc), agents=agents))
    return files


# APISIX plugin run order: higher _meta.priority runs first.
_APISIX_PRI_JWT = 20000
_APISIX_PRI_SCOPE = 15000
_APISIX_PRI_REWRITE = 10000
_APISIX_PRI_BOUNDS = 8000
_APISIX_PRI_ABORT = 7000
_APISIX_PRI_CATCHALL = 1

_T4_BODY = AGENT_SUSPENDED_BODY
_UNASSIGNED_BODY = UNASSIGNED_BODY
_PROV_BODY = PROVISIONING_DEFECT_BODY
_UNAVAILABLE_BODY = CUSTODY_UNAVAILABLE_BODY

# Set these; never also list them in proxy-rewrite remove (A2 same-name).
_APISIX_SET_HEADERS = (
    "x-ctier-tier",
    "x-ctier-deployment",
    "x-ctier-operation",
)
_APISIX_PRI_STRIP = 21000


def apisix_path(template: str) -> str:
    """OpenAPI template -> APISIX uri. * matches one segment."""
    parts = ["*" if _is_template(s) else s for s in _openapi_segments(template)]
    return "/" + "/".join(parts) if parts else "/*"


def apisix_priority(template: str) -> int:
    """Literal segments raise priority so a literal sibling wins a template."""
    return 10 + sum(0 if _is_template(s) else 1 for s in _openapi_segments(template))


def _apisix_upstream(doc: dict) -> dict:
    parsed = urlparse(_target_url(doc))
    host = parsed.hostname or "example.invalid"
    scheme = parsed.scheme or "https"
    port = parsed.port or (443 if scheme == "https" else 80)
    return {
        "type": "roundrobin",
        "scheme": scheme,
        "nodes": {f"{host}:{port}": 1},
    }


def _apisix_remove_headers() -> list[str]:
    """Aliases only. The namespace is stripped in Lua; A2 forbids remove+set."""
    return list(STRIP_ALIASES)


def _lua_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _lua_seq_helpers() -> str:
    """Per-worker sequence. Allocate before emit. Restart gets a new epoch.

    serverless-post-function loadstrings per route; package.loaded is
    not a reliable emitter. ngx.shared.ctier_seq is node config, same
    class as ctier_floors. Local incr, no network.
    """
    return (
        "local function ctier_allocate_sequence()\n"
        "  local dict = ngx.shared.ctier_seq\n"
        "  local pid = tostring(ngx.worker.pid())\n"
        "  if dict then\n"
        "    local epoch = dict:get(\"epoch:\" .. pid)\n"
        "    if not epoch then\n"
        "      epoch = string.format(\"%s-%s\", tostring(ngx.now()), pid)\n"
        "      dict:set(\"epoch:\" .. pid, epoch)\n"
        "    end\n"
        "    local n = dict:incr(\"n:\" .. pid, 1, 0)\n"
        "    return epoch, n\n"
        "  end\n"
        "  local M = package.loaded.ctier_record_seq\n"
        "  if not M then\n"
        "    M = {\n"
        "      epoch = string.format(\"%s-%s\", tostring(ngx.now()), pid),\n"
        "      n = 0,\n"
        "    }\n"
        "    package.loaded.ctier_record_seq = M\n"
        "  end\n"
        "  M.n = M.n + 1\n"
        "  return M.epoch, M.n\n"
        "end\n"
        "local function ctier_emit_sink(marker, rec, cjson)\n"
        "  local epoch, seq = ctier_allocate_sequence()\n"
        "  ngx.log(ngx.NOTICE, marker .. \"epoch=\" .. epoch .. \" seq=\" "
        ".. tostring(seq) .. \" \" .. (cjson.encode(rec) or \"\"))\n"
        "end\n"
    )


def _lua_exit(status: int, body: str, headers: dict[str, str] | None = None) -> str:
    extra = ""
    for key, value in (headers or {}).items():
        extra += f'  ngx.header["{_lua_quote(key)}"] = "{_lua_quote(value)}"\n'
    return (
        f"  ngx.status = {int(status)}\n"
        '  ngx.header["Content-Type"] = "application/json"\n'
        '  ngx.header["Cache-Control"] = "no-store"\n'
        f"{extra}"
        f'  ngx.say("{_lua_quote(body)}")\n'
        f"  return ngx.exit({int(status)})\n"
    )


def _lua_emit_decision_then_exit(
    row: dict,
    digest: str,
    *,
    status: int,
    body: str,
    disposition: str,
    declared: int,
    applied: int,
    reason: str = "none",
) -> str:
    """Fragment: sink line then refuse. Caller must have seq helpers in scope.

    No ledger POST. The gateway-log line is the claimed sink; a POST would
    also revoke on refuse-and-suspend, which stock T4 does not do here.
    """
    oid = _lua_quote(row["operationId"])
    digest_q = _lua_quote(digest)
    headers = required_instruction_headers_for(status, body)
    return (
        "  local cjson = require(\"cjson.safe\")\n"
        "  local agent = ngx.var.http_x_agent_id or \"unknown\"\n"
        "  local task = ngx.var.http_x_task_id\n"
        "  local cid = tostring(ngx.now()) .. \"-\" .. tostring(ngx.worker.pid()) "
        ".. \"-\" .. tostring(math.random(1, 1000000000))\n"
        "  local rec = {\n"
        "    ctierSchema = \"decision-record/0.2.0\",\n"
        "    id = cid,\n"
        "    timestamp = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"),\n"
        f"    operationAnchor = \"{oid}\",\n"
        "    agentId = agent,\n"
        "    correlationScope = task or agent,\n"
        "    correlationId = cid,\n"
        f"    declaredTier = {int(declared)},\n"
        f"    appliedTier = {int(applied)},\n"
        f"    escalationReason = \"{_lua_quote(reason)}\",\n"
        f"    disposition = \"{_lua_quote(disposition)}\",\n"
        "    idempotencyKey = cid,\n"
        f"    deploymentDigest = \"{digest_q}\",\n"
        "  }\n"
        "  ctier_emit_sink(\"[ctier-decision] \", rec, cjson)\n"
        + _lua_exit(status, body, headers)
    )


def _lua_refuse_decision(
    row: dict,
    digest: str,
    *,
    status: int,
    body: str,
    disposition: str,
    declared: int,
    applied: int,
    reason: str = "none",
) -> str:
    """Compiled abort: record the decision, then refuse. Same sink as execute."""
    return (
        _lua_seq_helpers()
        + "return function(conf, ctx)\n"
        + _lua_emit_decision_then_exit(
            row,
            digest,
            status=status,
            body=body,
            disposition=disposition,
            declared=declared,
            applied=applied,
            reason=reason,
        )
        + "end\n"
    )


def _abort_disposition(status: int) -> str:
    if status == 423:
        return "refuse-and-suspend"
    return "refuse-provisioning"


def _lua_catchall(doc: dict, digest: str) -> str:
    """Refuse a miss. C2 stays for composed-but-unassigned paths.

    Priority stays 1. A later route at a higher priority outranks this;
    that is the drift property, not a number to beat.

    The undeclared default is a decision. Emit before exit — same sink
    and epoch/seq allocation as compiled abort (63). Kong already records
    this path via the global plugin; silence here was a divergence.
    """
    c2_rows = [
        (row["method"].upper(), apisix_path(row["path"]), row["operationId"])
        for row in _all_operations(doc)
        if not row["classified"]
    ]
    pairs = ",\n".join(
        f'    {{method = "{_lua_quote(method)}", uri = "{_lua_quote(uri)}", '
        f'operation = "{_lua_quote(oid)}"}}'
        for method, uri, oid in c2_rows
    )
    digest_q = _lua_quote(digest)
    t4_headers = required_instruction_headers_for(423, _T4_BODY)
    return (
        _lua_seq_helpers()
        + "return function(conf, ctx)\n"
        "  local cjson = require(\"cjson.safe\")\n"
        "  local method = ngx.req.get_method()\n"
        "  local uri = ngx.var.uri\n"
        "  local c2 = {\n"
        f"{pairs}\n"
        "  }\n"
        "  local function match_uri(pattern, got)\n"
        "    local escaped = pattern:gsub(\"[%(%)%.%%%+%-%*%?%[%]%^%$]\", \"%%%1\")\n"
        "    escaped = escaped:gsub(\"%%%*\", \"[^/]+\")\n"
        "    return string.match(got, \"^\" .. escaped .. \"$\") ~= nil\n"
        "  end\n"
        "  for i = 1, #c2 do\n"
        "    if c2[i].method == method and match_uri(c2[i].uri, uri) then\n"
        "      local agent = ngx.var.http_x_agent_id or \"unknown\"\n"
        "      local task = ngx.var.http_x_task_id\n"
        "      local cid = tostring(ngx.now()) .. \"-\" .. tostring(ngx.worker.pid()) "
        ".. \"-\" .. tostring(math.random(1, 1000000000))\n"
        "      local rec = {\n"
        "        ctierSchema = \"decision-record/0.2.0\",\n"
        "        id = cid,\n"
        "        timestamp = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"),\n"
        "        operationAnchor = c2[i].operation,\n"
        "        agentId = agent,\n"
        "        correlationScope = task or agent,\n"
        "        correlationId = cid,\n"
        "        declaredTier = 4,\n"
        "        appliedTier = 4,\n"
        "        escalationReason = \"undeclared-operation\",\n"
        "        disposition = \"refuse-and-suspend\",\n"
        "        idempotencyKey = cid,\n"
        f"        deploymentDigest = \"{digest_q}\",\n"
        "      }\n"
        "      ctier_emit_sink(\"[ctier-decision] \", rec, cjson)\n"
        + _lua_exit(423, _T4_BODY, t4_headers)
        + "    end\n"
        "  end\n"
        "  local agent = ngx.var.http_x_agent_id or \"unknown\"\n"
        "  local task = ngx.var.http_x_task_id\n"
        "  -- No declaredTier: no declaration was made. Do not write 4.\n"
        "  -- epoch/seq stay on the sink line, not in this object.\n"
        "  local rec = {\n"
        "    ctierSchema = \"attempt-record/0.3.0\",\n"
        "    id = tostring(ngx.now()) .. \"-\" .. tostring(ngx.worker.pid()) "
        ".. \"-\" .. tostring(math.random(1, 1000000000)),\n"
        "    timestamp = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"),\n"
        "    operationAnchor = method .. \" \" .. uri,\n"
        "    agentId = agent,\n"
        "    correlationScope = task or agent,\n"
        "    appliedTier = cjson.null,\n"
        f"    deploymentDigest = \"{digest_q}\",\n"
        "    reason = \"unassigned\",\n"
        "  }\n"
        "  ctier_emit_sink(\"[ctier-attempt] \", rec, cjson)\n"
        + _lua_exit(423, _UNASSIGNED_BODY)
        + "end\n"
    )


def _lua_withhold(row: dict, digest: str, custody: dict, applied: int, reason: str) -> str:
    url = custody["url"].rstrip("/") + "/v1/pending"
    timeout = int(custody["timeout_ms"])
    authority = row.get("handoff_authority") or ""
    return (
        "  local http = require(\"resty.http\")\n"
        "  local cjson = require(\"cjson.safe\")\n"
        "  local httpc = http.new()\n"
        f"  httpc:set_timeout({timeout})\n"
        "  local args = ngx.req.get_uri_args() or {}\n"
        "  local query = {}\n"
        "  for k, v in pairs(args) do\n"
        "    if type(v) == \"table\" then query[k] = tostring(v[1]) else query[k] = tostring(v) end\n"
        "  end\n"
        "  ngx.req.read_body()\n"
        "  local agent = ngx.var.http_x_agent_id or \"unknown\"\n"
        "  local task = ngx.var.http_x_task_id\n"
        "  local payload = {\n"
        "    method = ngx.req.get_method(),\n"
        "    path = ngx.var.uri,\n"
        "    query = query,\n"
        "    body = ngx.req.get_body_data(),\n"
        f"    operationAnchor = \"{_lua_quote(row['operationId'])}\",\n"
        "    agentId = agent,\n"
        "    taskId = task,\n"
        "    correlationScope = task or agent,\n"
        f"    declaredTier = {int(row['tier'])},\n"
        f"    appliedTier = {int(applied)},\n"
        f"    deploymentDigest = \"{_lua_quote(digest)}\",\n"
        f"    escalationReason = \"{_lua_quote(reason)}\",\n"
        + (f"    authority = \"{_lua_quote(str(authority))}\",\n" if authority else "")
        + "  }\n"
        f"  local res, err = httpc:request_uri(\"{_lua_quote(url)}\", {{\n"
        "    method = \"POST\",\n"
        "    body = cjson.encode(payload),\n"
        "    headers = { [\"Content-Type\"] = \"application/json\", [\"Accept\"] = \"application/json\" },\n"
        "  })\n"
        "  if not res or res.status ~= 202 or not res.body then\n"
        "    local rec = {\n"
        "      ctierSchema = \"attempt-record/0.3.0\",\n"
        "      id = tostring(ngx.now()) .. \"-\" .. tostring(ngx.worker.pid()) "
        ".. \"-\" .. tostring(math.random(1, 1000000000)),\n"
        "      timestamp = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"),\n"
        f"      operationAnchor = \"{_lua_quote(row['operationId'])}\",\n"
        "      agentId = agent,\n"
        "      correlationScope = task or agent,\n"
        f"      declaredTier = {int(row['tier'])},\n"
        "      appliedTier = cjson.null,\n"
        f"      deploymentDigest = \"{_lua_quote(digest)}\",\n"
        "      reason = \"custody-unavailable\",\n"
        "    }\n"
        "    ctier_emit_sink(\"[ctier-attempt] \", rec, cjson)\n"
        + _lua_exit(503, _UNAVAILABLE_BODY, {"Retry-After": "5"})
        + "  end\n"
        "  ngx.status = 202\n"
        "  ngx.header[\"Content-Type\"] = \"application/json\"\n"
        "  ngx.header[\"Cache-Control\"] = \"no-store\"\n"
        f"  local ha = res.headers[\"{HEADER_AGENT_ACTION}\"] or res.headers[\"x-agent-action\"]\n"
        "  local hc = res.headers[\"x-ctier-correlation-id\"] or res.headers[\"X-Ctier-Correlation-Id\"]\n"
        f"  if ha then ngx.header[\"{HEADER_AGENT_ACTION}\"] = ha end\n"
        "  if hc then\n"
        "    ngx.header[\"x-ctier-correlation-id\"] = hc\n"
        "  end\n"
        "  ngx.say(res.body)\n"
        "  return ngx.exit(202)\n"
    )


def _outcome(
    tier: int, excluded: bool, custody: dict | None, *, observe: bool = False,
) -> tuple[str, int, str | None]:
    """Compiled disposition. Target code only enacts this."""
    if observe:
        return "execute", 200, None
    if excluded:
        return "abort", 403, _PROV_BODY
    if tier >= 4:
        return "abort", 423, _T4_BODY
    if tier == 3:
        if custody is not None:
            return "withhold", 202, None
        return "abort", 403, _PROV_BODY
    return "execute", 200, None


def _lua_bounds(row: dict, digest: str, custody: dict | None, *, observe: bool = False) -> str:
    """tonumber the compiled query parameter. Consequence is already compiled."""
    parameter = str(row["bound_parameter"])
    maximum = int(row["bound_max"])
    declared = int(row["tier"])
    escalated = _escalated_tier(declared)
    kind, status, body = _outcome(escalated, False, custody, observe=observe)
    reason = "payload-exceeds-declared-bounds"
    block = (
        _lua_seq_helpers()
        + "return function(conf, ctx)\n"
        f'  local raw = ngx.var["arg_{_lua_quote(parameter)}"]\n'
        "  if raw == nil or raw == \"\" then return end\n"
        "  local n = tonumber(raw)\n"
        f"  if not n or n <= {maximum} then return end\n"
    )
    if kind == "abort":
        payload = body or _PROV_BODY
        block += _lua_emit_decision_then_exit(
            row,
            digest,
            status=status,
            body=payload,
            disposition=_abort_disposition(status),
            declared=declared,
            applied=escalated,
            reason=reason,
        )
    elif kind == "withhold":
        block += _lua_withhold(row, digest, custody, escalated, reason)
    else:
        block += f'  ngx.req.set_header("x-ctier-tier", "{escalated}")\n'
    block += "end\n"
    return block


def _lua_withhold_fn(row: dict, digest: str, custody: dict) -> str:
    reason = "none"
    return (
        _lua_floor_helpers(custody)
        + _lua_seq_helpers()
        + "return function(conf, ctx)\n"
        "  ctier_start_floor_poller()\n"
        + _lua_withhold(row, digest, custody, int(row["tier"]), reason)
        + "end\n"
    )


def _lua_floor_helpers(custody: dict) -> str:
    """Out of band: timer writes ngx.shared.ctier_floors. Request path only reads.

    APISIX has no worker-init plugin. One timer per worker is claimed with
    a pid-keyed add in the same dict; floor keys are never that prefix.
    Interval and TTL are compiled numbers, not library defaults.
    """
    url = _lua_quote(custody["url"].rstrip("/") + "/v1/floors")
    timeout = int(custody["timeout_ms"])
    interval_ms = int(custody["floor_poll_ms"])
    interval = interval_ms / 1000.0
    ttl = (2 * interval_ms) / 1000.0
    return (
        "local function ctier_refresh_floors(url, timeout_ms, ttl)\n"
        "  local http = require(\"resty.http\")\n"
        "  local cjson = require(\"cjson.safe\")\n"
        "  local httpc = http.new()\n"
        "  httpc:set_timeout(timeout_ms)\n"
        "  local res, err = httpc:request_uri(url, {\n"
        "    method = \"GET\",\n"
        "    headers = { [\"Accept\"] = \"application/json\" },\n"
        "  })\n"
        "  if not res or res.status ~= 200 or not res.body then\n"
        "    ngx.log(ngx.ERR, \"ctier floor poll failed: \", err or (res and res.status) or \"no response\")\n"
        "    return\n"
        "  end\n"
        "  local body = cjson.decode(res.body)\n"
        "  if type(body) ~= \"table\" or type(body.floors) ~= \"table\" then\n"
        "    return\n"
        "  end\n"
        "  local dict = ngx.shared.ctier_floors\n"
        "  if not dict then\n"
        "    ngx.log(ngx.ERR, \"ctier_floors shared dict is not configured; accumulation will not escalate\")\n"
        "    return\n"
        "  end\n"
        "  local seen = {}\n"
        "  for _, row in ipairs(body.floors) do\n"
        "    if type(row) == \"table\" and type(row.correlationScope) == \"string\" and row.floor then\n"
        "      dict:set(row.correlationScope, tonumber(row.floor), ttl)\n"
        "      seen[row.correlationScope] = true\n"
        "    end\n"
        "  end\n"
        "  local keys = dict:get_keys(0)\n"
        "  for i = 1, #keys do\n"
        "    local k = keys[i]\n"
        "    if string.sub(k, 1, 13) ~= \"ctier:poller:\" and not seen[k] then\n"
        "      dict:delete(k)\n"
        "    end\n"
        "  end\n"
        "end\n"
        "local function ctier_start_floor_poller()\n"
        "  local dict = ngx.shared.ctier_floors\n"
        "  if not dict then\n"
        "    return\n"
        "  end\n"
        "  local flag = \"ctier:poller:\" .. tostring(ngx.worker.pid())\n"
        "  local ok, err = dict:add(flag, 1)\n"
        "  if not ok then\n"
        "    return\n"
        "  end\n"
        f"  local url = \"{url}\"\n"
        f"  local timeout_ms = {timeout}\n"
        f"  local interval_ms = {interval_ms}\n"
        f"  local ttl = {ttl}\n"
        "  ngx.log(ngx.NOTICE, \"ctier floor poller interval_ms=\", interval_ms)\n"
        "  local function tick(premature)\n"
        "    if premature then return end\n"
        "    ctier_refresh_floors(url, timeout_ms, ttl)\n"
        "  end\n"
        "  ok, err = ngx.timer.at(0, tick)\n"
        "  if not ok then\n"
        "    ngx.log(ngx.ERR, \"ctier floor poller at(0): \", err)\n"
        "  end\n"
        f"  ok, err = ngx.timer.every({interval}, tick)\n"
        "  if not ok then\n"
        "    ngx.log(ngx.ERR, \"ctier floor poller every: \", err)\n"
        "    dict:delete(flag)\n"
        "  end\n"
        "end\n"
        "local function ctier_apply_scope_floor(tier)\n"
        "  ctier_start_floor_poller()\n"
        "  local dict = ngx.shared.ctier_floors\n"
        "  if not dict then\n"
        "    ngx.log(ngx.NOTICE, \"ctier no floor dictionary; no accumulation escalation\")\n"
        "    return tier\n"
        "  end\n"
        "  local task = ngx.var.http_x_task_id\n"
        "  local agent = ngx.var.http_x_agent_id or \"unknown\"\n"
        "  local scope = task or agent\n"
        "  local raw = dict:get(scope)\n"
        "  if raw == nil then\n"
        "    ngx.log(ngx.DEBUG, \"ctier no published floor for \", scope, \"; no escalation\")\n"
        "    return tier\n"
        "  end\n"
        "  local floor = tonumber(raw, 10)\n"
        "  if floor and floor > tier then\n"
        "    return floor\n"
        "  end\n"
        "  return tier\n"
        "end\n"
    )


def _apisix_jwt() -> dict:
    return {
        "_meta": {"priority": _APISIX_PRI_JWT},
        "key_claim_name": JWT_CLAIM,
    }


def _apisix_oidc(required: str | None) -> dict:
    """Local JWT + required_scopes. Discovery is a tripwire, not a hop.

    valid_issuers skips get_discovery_doc (A5). The URL is required by the
    plugin schema and is never fetched when this list is set. Issuers are
    the realm identities the live rigs mint and import; not a new input.
    """
    conf: dict = {
        "_meta": {"priority": _APISIX_PRI_SCOPE},
        "client_id": AGENT_CLIENT,
        "client_secret": AGENT_SECRET,
        "discovery": "http://127.0.0.1:1/.well-known/openid-configuration",
        "bearer_only": True,
        "ssl_verify": False,
        "public_key": public_pem().strip(),
        "claim_validator": {
            "issuer": {
                "valid_issuers": [
                    "ctier",
                    "http://keycloak:8080/realms/ctier",
                    "http://127.0.0.1:18400/realms/ctier",
                    "http://127.0.0.1:19400/realms/ctier",
                ]
            }
        },
        "set_userinfo_header": False,
        "set_id_token_header": False,
    }
    if required:
        conf["required_scopes"] = [required]
    return conf


def _lua_strip_namespace() -> str:
    return (
        "return function(conf, ctx)\n"
        "  local h = ngx.req.get_headers()\n"
        "  for k, _ in pairs(h) do\n"
        "    local lk = string.lower(k)\n"
        "    if string.sub(lk, 1, 8) == \"x-ctier-\" or lk == \"x-correlation-id\""
        " or lk == \"idempotency-key\" or lk == \"x-idempotency-key\" then\n"
        "      ngx.req.clear_header(k)\n"
        "    end\n"
        "  end\n"
        "end\n"
    )


def _lua_forward_provenance(row: dict, digest: str, custody: dict | None) -> str:
    """Join key, and ledger idempotency when custody answers."""
    oid = _lua_quote(row["operationId"])
    digest_q = _lua_quote(digest)
    tier = 4 if row.get("excluded") else int(row["tier"])
    floor_prefix = _lua_floor_helpers(custody) if custody else ""
    apply_block = ""
    if custody:
        apply_block = (
            f"  local declared = {tier}\n"
            "  local applied = ctier_apply_scope_floor(declared)\n"
            "  local reason = \"none\"\n"
            "  if applied > declared then reason = \"session-accumulation\" end\n"
            "  if applied >= 4 then\n"
            "    local rec = {\n"
            "      ctierSchema = \"decision-record/0.2.0\",\n"
            "      id = cid,\n"
            "      timestamp = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"),\n"
            f"      operationAnchor = \"{oid}\",\n"
            "      agentId = agent,\n"
            "      correlationScope = task or agent,\n"
            "      correlationId = cid,\n"
            "      declaredTier = declared,\n"
            "      appliedTier = applied,\n"
            "      escalationReason = reason,\n"
            "      disposition = \"refuse-and-suspend\",\n"
            "      idempotencyKey = cid,\n"
            f"      deploymentDigest = \"{digest_q}\",\n"
            "    }\n"
            "    ctier_emit_sink(\"[ctier-decision] \", rec, cjson)\n"
            + _lua_exit(423, _T4_BODY, required_instruction_headers_for(423, _T4_BODY))
            + "  end\n"
            "  ngx.req.set_header(\"x-ctier-tier\", tostring(applied))\n"
        )
    custody_block = ""
    if custody:
        url = _lua_quote(custody["url"].rstrip("/") + "/v1/ledger")
        timeout = int(custody["timeout_ms"])
        custody_block = (
            "  local http = require(\"resty.http\")\n"
            "  local httpc = http.new()\n"
            f"  httpc:set_timeout({timeout})\n"
            "  local payload = {\n"
            "    type = \"decision\",\n"
            "    method = ngx.req.get_method(),\n"
            "    path = ngx.var.uri,\n"
            "    query = query,\n"
            "    body = ngx.req.get_body_data(),\n"
            f"    operationAnchor = \"{oid}\",\n"
            "    agentId = agent,\n"
            "    taskId = task,\n"
            "    correlationScope = task or agent,\n"
            "    correlationId = cid,\n"
            "    declaredTier = declared,\n"
            "    appliedTier = applied,\n"
            "    disposition = \"execute\",\n"
            "    escalationReason = reason,\n"
            f"    deploymentDigest = \"{digest_q}\",\n"
            "  }\n"
            f"  local res = httpc:request_uri(\"{url}\", {{\n"
            "    method = \"POST\",\n"
            "    body = cjson.encode(payload),\n"
            "    headers = { [\"Content-Type\"] = \"application/json\" },\n"
            "  })\n"
            "  if res and res.body then\n"
            "    local rec = cjson.decode(res.body)\n"
            "    if type(rec) == \"table\" then\n"
            "      if rec.correlationId then cid = rec.correlationId end\n"
            "      if rec.idempotencyKey then key = rec.idempotencyKey end\n"
            "    end\n"
            "  end\n"
        )
    if not apply_block:
        apply_block = (
            f"  local declared = {tier}\n"
            f"  local applied = {tier}\n"
            "  local reason = \"none\"\n"
        )
    log_block = (
        "  local rec = {\n"
        "    ctierSchema = \"decision-record/0.2.0\",\n"
        "    id = cid,\n"
        "    timestamp = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"),\n"
        f"    operationAnchor = \"{oid}\",\n"
        "    agentId = agent,\n"
        "    correlationScope = task or agent,\n"
        "    correlationId = cid,\n"
        "    declaredTier = declared,\n"
        "    appliedTier = applied,\n"
        "    escalationReason = reason,\n"
        "    disposition = \"execute\",\n"
        "    idempotencyKey = cid,\n"
        f"    deploymentDigest = \"{digest_q}\",\n"
        "  }\n"
        "  ctier_emit_sink(\"[ctier-decision] \", rec, cjson)\n"
    )
    return (
        floor_prefix
        + _lua_seq_helpers()
        + "return function(conf, ctx)\n"
        "  local cjson = require(\"cjson.safe\")\n"
        "  ngx.req.read_body()\n"
        "  local agent = ngx.var.http_x_agent_id or \"unknown\"\n"
        "  local task = ngx.var.http_x_task_id\n"
        "  local args = ngx.req.get_uri_args() or {}\n"
        "  local query = {}\n"
        "  for k, v in pairs(args) do\n"
        "    if type(v) == \"table\" then query[k] = tostring(v[1]) else query[k] = tostring(v) end\n"
        "  end\n"
        "  local cid = tostring(ngx.now()) .. \"-\" .. tostring(ngx.worker.pid()) "
        ".. \"-\" .. tostring(math.random(1, 1000000000))\n"
        "  local key\n"
        + apply_block
        + log_block
        + custody_block
        + "  ngx.req.set_header(\"x-ctier-correlation-id\", cid)\n"
        "  if key and key ~= \"\" then ngx.req.set_header(\"Idempotency-Key\", key) end\n"
        "end\n"
    )


def _apisix_rewrite(row: dict, digest: str) -> dict:
    headers = {
        "remove": list(_apisix_remove_headers()),
        "set": {
            "X-Ctier-Tier": str(4 if row["excluded"] else int(row["tier"])),
            "X-Ctier-Deployment": digest,
            "X-Ctier-Operation": row["operationId"],
        },
    }
    return {
        "_meta": {"priority": _APISIX_PRI_REWRITE},
        "headers": headers,
    }


def _apisix_plugins(
    row: dict, digest: str, custody: dict | None, *, observe: bool = False,
) -> dict:
    """Express one compiled row. No classification happens here."""
    plugins: dict = {"jwt-auth": _apisix_jwt()}
    # Strip in rewrite, before proxy-rewrite. Access-phase strip runs
    # after rewrite and would drop the headers this target just set.
    plugins["serverless-pre-function"] = {
        "_meta": {"priority": _APISIX_PRI_STRIP},
        "phase": "rewrite",
        "functions": [_lua_strip_namespace()],
    }
    declared = 4 if row["excluded"] else int(row["tier"])
    kind, status, body = _outcome(
        declared,
        bool(row["excluded"]),
        custody,
        observe=observe,
    )
    plugins["proxy-rewrite"] = _apisix_rewrite(row, digest)
    plugins["openid-connect"] = _apisix_oidc(
        None if (observe or row.get("excluded")) else scope_name(row["operationId"])
    )
    post_fns: list[str] = []
    post_pri = _APISIX_PRI_SCOPE
    if _has_bounds(row):
        post_fns.append(_lua_bounds(row, digest, custody, observe=observe))
        post_pri = min(post_pri, _APISIX_PRI_BOUNDS)
    if kind == "abort":
        # Was fault-injection: status and body, no sink line. Recording was
        # attached to the execute/withhold paths, not to the decision.
        payload = body or _PROV_BODY
        post_fns.append(_lua_refuse_decision(
            row,
            digest,
            status=status,
            body=payload,
            disposition=_abort_disposition(status),
            declared=declared,
            applied=declared,
        ))
        post_pri = min(post_pri, _APISIX_PRI_ABORT)
    elif kind == "withhold":
        post_fns.append(_lua_withhold_fn(row, digest, custody))
    elif kind == "execute":
        post_fns.append(_lua_forward_provenance(row, digest, custody))
    if post_fns:
        plugins["serverless-post-function"] = {
            "_meta": {"priority": post_pri},
            "phase": "access",
            "functions": post_fns,
        }
    return plugins


def _apisix_route(
    row: dict, digest: str, custody: dict | None, upstream: dict, *, observe: bool = False,
) -> dict:
    slug = _route_slug(row["operationId"])
    return {
        "id": slug,
        "name": slug,
        "uris": [apisix_path(row["path"])],
        "methods": [row["method"].upper()],
        "priority": apisix_priority(row["path"]),
        "plugins": _apisix_plugins(row, digest, custody, observe=observe),
        "upstream": dict(upstream),
    }


def _generate_apisix(
    doc: dict, digest: str, mode: str, custody: dict | None = None,
    *,
    agents=None,
    observe: bool = False,
) -> dict[str, str]:
    """Same compiled rows as Kong/Apigee. mode is accepted, not packed.

    Fragment mode will consume these rows too. This function must not grow a
    bundle-only wrapper around them.
    """
    # Packing is the files dict. Fragment mode merges after generate().
    upstream = _apisix_upstream(doc)
    routes = [
        _apisix_route(row, digest, custody, upstream, observe=observe)
        for row in _all_operations(doc)
        if row["classified"]
    ]
    routes.append({
        "id": "undeclared",
        "name": "undeclared",
        "uris": ["/*"],
        "priority": _APISIX_PRI_CATCHALL,
        "plugins": {} if observe else {
            "serverless-post-function": {
                "_meta": {"priority": _APISIX_PRI_CATCHALL},
                "phase": "access",
                "functions": [_lua_catchall(doc, digest)],
            },
        },
        "upstream": dict(upstream),
    })
    deck = {
        "consumers": [{
            "username": "ctier-agents",
            "plugins": {
                "jwt-auth": {
                    "key": JWT_CLAIM_VALUE,
                    "algorithm": "RS256",
                    "public_key": public_pem().strip(),
                },
            },
        }],
        "routes": routes,
    }
    text = yaml.safe_dump(
        deck,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
    if not text.rstrip().endswith("#END"):
        text = text.rstrip() + "\n\n#END\n"
    files = {
        "apisix.yaml": text,
        "ctier-generate.json": _generate_meta(
            digest, "apisix", mode, _governed_manifest(doc),
        ),
    }
    files.update(authorization_files(_all_operations(doc), agents=agents))
    return files


def _policy_tier(operation_id: str, tier: int, *, name_suffix: str = "") -> str:
    name = _policy_name("AM-Tier", operation_id + name_suffix)
    return (
        _xml_decl()
        + f"<AssignMessage name=\"{_escape(name)}\">\n"
        f"  <DisplayName>{_escape(name)}</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.tier</Name>\n"
        f"    <Value>{tier}</Value>\n"
        "  </AssignVariable>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.declared</Name>\n"
        "    <Value>true</Value>\n"
        "  </AssignVariable>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.operation</Name>\n"
        f"    <Value>{_escape(operation_id)}</Value>\n"
        "  </AssignVariable>\n"
        "</AssignMessage>\n"
    )


def _policy_exclude(operation_id: str) -> str:
    name = _policy_name("AM-Exclude", operation_id)
    return (
        _xml_decl()
        + f"<AssignMessage name=\"{_escape(name)}\">\n"
        f"  <DisplayName>{_escape(name)}</DisplayName>\n"
        "  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.excluded</Name>\n"
        "    <Value>true</Value>\n"
        "  </AssignVariable>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.declared</Name>\n"
        "    <Value>true</Value>\n"
        "  </AssignVariable>\n"
        "  <AssignVariable>\n"
        "    <Name>ctier.operation</Name>\n"
        f"    <Value>{_escape(operation_id)}</Value>\n"
        "  </AssignVariable>\n"
        "</AssignMessage>\n"
    )


def _has_bounds(row: dict) -> bool:
    return (
        not row["excluded"]
        and bool(row.get("bound_parameter"))
        and row.get("bound_max") is not None
    )


def _bounds_condition(parameter: str, maximum: int) -> str:
    return f"request.queryparam.{parameter} > {maximum}"


def _flow_xml(row: dict) -> str:
    oid = row["operationId"]
    policy = _policy_name("AM-Exclude" if row["excluded"] else "AM-Tier", oid)
    pattern = _escape(matches_path(row["path"]))
    verb = row["method"].upper()
    steps = (
        "        <Step>\n"
        f"          <Name>{_escape(policy)}</Name>\n"
        "        </Step>\n"
    )
    if _has_bounds(row):
        bounds_policy = _policy_name("AM-Tier", oid + "-bounds")
        condition = _escape(_bounds_condition(row["bound_parameter"], int(row["bound_max"])))
        steps += (
            "        <Step>\n"
            f"          <Name>{_escape(bounds_policy)}</Name>\n"
            f"          <Condition>{condition}</Condition>\n"
            "        </Step>\n"
        )
    return (
        f"    <Flow name=\"{_escape(oid)}\">\n"
        f"      <Condition>(proxy.pathsuffix MatchesPath \"{pattern}\") "
        f"and (request.verb = \"{verb}\")</Condition>\n"
        "      <Request>\n"
        f"{steps}"
        "      </Request>\n"
        "    </Flow>\n"
    )


def _proxy_endpoint_xml(flows: str, postflow: str) -> str:
    return (
        _xml_decl()
        + "<ProxyEndpoint name=\"default\">\n"
        "  <PreFlow>\n"
        "    <Request>\n"
        "      <Step>\n"
        "        <Name>JS-StripCtierNamespace</Name>\n"
        "      </Step>\n"
        "      <Step>\n"
        "        <Name>SC-StripCtierHeaders</Name>\n"
        "      </Step>\n"
        "      <Step>\n"
        "        <Name>AM-DefaultTier</Name>\n"
        "      </Step>\n"
        "      <Step>\n"
        "        <Name>AM-Deployment</Name>\n"
        "      </Step>\n"
        "    </Request>\n"
        "  </PreFlow>\n"
        "  <Flows>\n"
        f"{flows}"
        "  </Flows>\n"
        f"{postflow}"
        "  <HTTPProxyConnection>\n"
        "    <BasePath>/</BasePath>\n"
        "    <VirtualHost>default</VirtualHost>\n"
        "  </HTTPProxyConnection>\n"
        "  <RouteRule name=\"default\">\n"
        "    <TargetEndpoint>default</TargetEndpoint>\n"
        "  </RouteRule>\n"
        "</ProxyEndpoint>\n"
    )


def generate(
    qualified_spec: Union[Source, dict],
    target: str = "apigee",
    mode: str = "bundle",
    custody: dict | None = None,
    agents=None,
    existing: dict[str, str] | None = None,
    observe: bool = False,
    records: dict | None = None,
) -> dict[str, str]:
    """Compile a qualified spec to gateway artefacts. Returns path -> text.

    custody absent: Level 2. Tier 3 compiles as a provisioning refusal.
    custody present: Level 3. Tier 3 compiles the withhold path.
    observe True: Level 1. Classify and emit a decision record; enforce nothing.
    records: Apigee-only optional POST /v1/ledger sink the kit can GET.
    mode=fragment: same compiled rows, merged into `existing` when given.
    """
    if target not in TARGETS:
        raise GenerateError("target", f"unsupported target {target!r}")
    if mode not in MODES:
        raise GenerateError("mode", f"unsupported mode {mode!r}")
    if observe and custody is not None:
        raise GenerateError("observe", "Level 1 has no custody")
    cfg = _normalise_custody(custody)
    rec = _normalise_records(records)
    if rec is not None and target != "apigee":
        # Kong/APISIX already emit to the gateway log; records URL is unused.
        rec = None
    doc = _document(qualified_spec)
    # Same schema check compose runs, on this document, before a tier is resolved.
    validate_openapi_extensions(doc)
    digest = deployment_digest(doc, agents)
    _refuse_foreign_assignment(doc, agents, existing)
    if target == "kong":
        files = dict(sorted(_generate_kong(
            doc, digest, mode, cfg, agents=agents, observe=observe,
        ).items()))
        if mode == "fragment":
            return apply_or_refuse(target, existing or {}, files)
        return files
    if target == "apisix":
        files = dict(sorted(_generate_apisix(
            doc, digest, mode, cfg, agents=agents, observe=observe,
        ).items()))
        if mode == "fragment":
            return apply_or_refuse(target, existing or {}, files)
        return files
    name = _proxy_name(doc)
    classified = _classified_operations(doc)
    flows = "".join(_flow_xml(row) for row in classified)
    files = {
        f"apiproxy/{name}.xml": _proxy_root_xml(name),
        "apiproxy/proxies/default.xml": _proxy_endpoint_xml(
            flows, _postflow_xml(cfg, observe=observe, records=rec),
        ),
        "apiproxy/targets/default.xml": _target_xml(doc, records=rec),
        "apiproxy/policies/JS-StripCtierNamespace.xml": _policy_js_strip(),
        "apiproxy/resources/jsc/strip-ctier-namespace.js": _js_strip_namespace(),
        "apiproxy/policies/SC-StripCtierHeaders.xml": _policy_strip(),
        "apiproxy/policies/AM-DefaultTier.xml": _policy_default_tier(),
        "apiproxy/policies/JS-SetUpstreamProvenance.xml": _policy_js_provenance(),
        "apiproxy/resources/jsc/set-upstream-provenance.js": _js_set_upstream_provenance(),
        "apiproxy/policies/AM-Deployment.xml": _policy_deployment(digest),
        "apiproxy/policies/RF-Tier4.xml": _policy_rf_tier4(),
        "apiproxy/policies/RF-Provisioning.xml": _policy_rf_provisioning(),
        "ctier-generate.json": _generate_meta(digest, target, mode),
    }
    files.update(authorization_files(_all_operations(doc), agents=agents))
    if cfg is not None:
        files["apiproxy/policies/SC-CustodyPending.xml"] = _policy_sc_custody_pending(cfg)
        files["apiproxy/policies/RF-Withhold.xml"] = _policy_rf_withhold()
        files["apiproxy/policies/RF-CustodyUnavailable.xml"] = _policy_rf_custody_unavailable()
    if rec is not None:
        files["apiproxy/policies/SC-RecordDecision.xml"] = _policy_sc_record_decision(rec)
        if not observe:
            files["apiproxy/policies/JS-RecordRefuse.xml"] = _policy_js_record_refuse()
            files["apiproxy/resources/jsc/record-refuse.js"] = _js_record_refuse()
    for row in classified:
        oid = row["operationId"]
        if row["excluded"]:
            files[f"apiproxy/policies/{_policy_name('AM-Exclude', oid)}.xml"] = (
                _policy_exclude(oid)
            )
        else:
            files[f"apiproxy/policies/{_policy_name('AM-Tier', oid)}.xml"] = (
                _policy_tier(oid, row["tier"])
            )
            if _has_bounds(row):
                files[f"apiproxy/policies/{_policy_name('AM-Tier', oid + '-bounds')}.xml"] = (
                    _policy_tier(oid, _escalated_tier(row["tier"]), name_suffix="-bounds")
                )
    packed = dict(sorted(files.items()))
    if mode == "fragment":
        return apply_or_refuse(target, existing or {}, packed)
    return packed
