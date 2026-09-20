# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Fragment mode: inspect existing configuration, report, merge.

Bundle owns the path. Fragment never silently assumes it does.
"""
from __future__ import annotations

import json
import re
from typing import Any

import yaml

from .errors import GenerateError

# 1.5.0 contract names that must not be agent-supplied on the wire.
CONTRACT_HEADERS = (
    "x-ctier-",
    "x-correlation-id",
    "x-ctier-tier",
    "idempotency-key",
    "x-idempotency-key",
)

# Kong plugin PRIORITY constants. Instance config cannot override them.
# Higher runs first. ctier is 10000 in handler.lua (above cors 2000).
KONG_PRIORITY = {
    "pre-function": 1_000_000,
    "cors": 2000,
    "jwt": 1005,
    "rate-limiting": 901,
    "request-transformer": 801,
    "ctier": 10000,
    "file-log": 9,
    "post-function": -1000,
}

CTIER_KONG_PRIORITY = 10000


def _blob(obj: Any) -> str:
    return json.dumps(obj, default=str).lower()


def _mentions_contract(text: str) -> list[str]:
    lower = text.lower()
    hits = []
    if "x-ctier-" in lower:
        hits.append("x-ctier-*")
    for name in ("x-correlation-id", "idempotency-key", "x-idempotency-key"):
        if name in lower:
            hits.append(name)
    return hits


def _dump(obj: Any) -> str:
    return yaml.safe_dump(
        obj, sort_keys=False, default_flow_style=False, allow_unicode=True, width=1000,
    )


def inspect(target: str, existing: dict[str, str]) -> dict[str, Any]:
    """Walk existing files. Return a conflict report document (as a dict).

    The report is an artefact, same class as kong.yaml. Header-order
    findings that break C11 set wouldRefuse. Name collisions are not
    inspected here — they are derived from the generated artefacts in
    replacement_findings.
    """
    findings: list[dict[str, Any]] = []
    if target == "kong":
        findings.extend(_inspect_kong(existing.get("kong.yaml") or existing.get("kong-existing.yaml") or ""))
    elif target == "apisix":
        findings.extend(_inspect_apisix(existing.get("apisix.yaml") or ""))
    else:
        findings.extend(_inspect_apigee(existing))
    refuse = [f for f in findings if f.get("breaks_c11")]
    return _finish_report({
        "ctierSchema": "conflict-report/0.1.0",
        "target": target,
        "wouldRefuse": bool(refuse),
        "findings": findings,
        "unguaranteed": [
            "Strip precedence against a plugin whose priority is higher than ctier's, or against an Apigee PreProxy FlowHook not present in the artefact.",
            "A later writer of 1.5.0 headers after the strip has run.",
        ],
    })


def _inspect_kong(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not text.strip():
        out.append({
            "kind": "no-existing",
            "severity": "info",
            "breaks_c11": False,
            "detail": "No existing Kong configuration was provided.",
        })
        return out
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return [{
            "kind": "unparseable",
            "severity": "error",
            "breaks_c11": True,
            "detail": f"Kong YAML could not be parsed; ordering cannot be determined ({exc}).",
        }]
    plugins = list(doc.get("plugins") or [])
    for svc in doc.get("services") or []:
        plugins.extend(svc.get("plugins") or [])
        for route in svc.get("routes") or []:
            plugins.extend(route.get("plugins") or [])
    for plugin in plugins:
        name = str(plugin.get("name") or "")
        conf = plugin.get("config") or {}
        blob = _blob(plugin)
        hits = _mentions_contract(blob)
        pri = KONG_PRIORITY.get(name)
        if pri is None and hits:
            out.append({
                "kind": "order-unknown",
                "severity": "error",
                "breaks_c11": True,
                "component": name,
                "headers": hits,
                "detail": (
                    f"Plugin {name!r} mentions 1.5.0 headers and has no known "
                    "PRIORITY constant, so strip order cannot be determined."
                ),
            })
            continue
        if hits:
            writer = "set_header" in blob or (
                "headers" in blob
                and bool(re.search(r"\b(add|replace|append|set)\b", blob))
            )
            if writer and pri is not None and pri < CTIER_KONG_PRIORITY:
                out.append({
                    "kind": "header-writer-after-strip",
                    "severity": "error",
                    "breaks_c11": True,
                    "component": name,
                    "priority": pri,
                    "headers": hits,
                    "detail": (
                        f"{name} (priority {pri}) writes a 1.5.0 header and "
                        f"runs after ctier ({CTIER_KONG_PRIORITY}); the strip cannot catch it."
                    ),
                })
            elif pri is not None and pri > CTIER_KONG_PRIORITY:
                out.append({
                    "kind": "header-component-before-strip",
                    "severity": "warn",
                    "breaks_c11": False,
                    "component": name,
                    "priority": pri,
                    "headers": hits,
                    "detail": (
                        f"{name} (priority {pri}) runs before ctier strip "
                        f"({CTIER_KONG_PRIORITY}). It can read agent-supplied "
                        "1.5.0 headers. Fragment mode is not C11-conformant "
                        "against this configuration without an operator pinning "
                        "the strip first."
                    ),
                })
            else:
                out.append({
                    "kind": "header-component",
                    "severity": "warn",
                    "breaks_c11": False,
                    "component": name,
                    "priority": pri,
                    "headers": hits,
                    "config_keys": sorted(conf) if isinstance(conf, dict) else [],
                    "detail": f"{name} mentions 1.5.0 contract names.",
                })
        elif pri is None:
            out.append({
                "kind": "order-unknown",
                "severity": "warn",
                "breaks_c11": False,
                "component": name,
                "detail": f"Plugin {name!r} has no known PRIORITY; order relative to ctier is undetermined.",
            })
    return out


def _inspect_apisix(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not text.strip():
        out.append({
            "kind": "no-existing",
            "severity": "info",
            "breaks_c11": False,
            "detail": "No existing APISIX configuration was provided.",
        })
        return out
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return [{
            "kind": "unparseable",
            "severity": "error",
            "breaks_c11": True,
            "detail": f"APISIX YAML could not be parsed ({exc}).",
        }]
    for route in doc.get("routes") or []:
        rname = str(route.get("name") or route.get("id") or "")
        plugins = route.get("plugins") or {}
        if "serverless-pre-function" in plugins or "serverless-post-function" in plugins:
            joined = _blob(plugins)
            hits = _mentions_contract(joined)
            pre = plugins.get("serverless-pre-function") or {}
            phase = pre.get("phase")
            pri = (pre.get("_meta") or {}).get("priority")
            if hits and pri is None:
                out.append({
                    "kind": "order-unknown",
                    "severity": "error",
                    "breaks_c11": True,
                    "component": f"{rname}/serverless",
                    "headers": hits,
                    "detail": "Serverless Lua mentions 1.5.0 headers and has no _meta.priority.",
                })
            elif hits:
                out.append({
                    "kind": "header-component",
                    "severity": "warn",
                    "breaks_c11": False,
                    "component": f"{rname}/serverless",
                    "phase": phase,
                    "priority": pri,
                    "headers": hits,
                    "detail": "Existing Lua mentions 1.5.0 headers. Strip precedence is not guaranteed against arbitrary phase/priority.",
                })
        rewrite = plugins.get("proxy-rewrite") or {}
        headers = ((rewrite.get("headers") or {}).get("set") or {})
        header_blob = _blob(headers) + _blob((rewrite.get("headers") or {}).get("add") or {})
        hits = _mentions_contract(header_blob)
        if hits:
            out.append({
                "kind": "header-writer",
                "severity": "warn",
                "breaks_c11": False,
                "component": f"{rname}/proxy-rewrite",
                "headers": hits,
                "detail": "proxy-rewrite sets or adds a 1.5.0 name. A2 and phase order decide whether strip sees it.",
            })
        cors = plugins.get("cors") or {}
        if _mentions_contract(_blob(cors)):
            out.append({
                "kind": "header-component",
                "severity": "warn",
                "breaks_c11": False,
                "component": f"{rname}/cors",
                "headers": _mentions_contract(_blob(cors)),
                "detail": "CORS configuration names a 1.5.0 header (allow-list, not necessarily a request read).",
            })
    return out


def _inspect_apigee(files: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not files:
        return [{
            "kind": "no-existing",
            "severity": "info",
            "breaks_c11": False,
            "detail": "No existing Apigee configuration was provided.",
        }]
    for path, text in files.items():
        hits = _mentions_contract(text)
        if hits:
            out.append({
                "kind": "header-component",
                "severity": "warn",
                "breaks_c11": False,
                "component": path,
                "headers": hits,
                "detail": "Existing artefact mentions 1.5.0 headers.",
            })
    proxy = files.get("apiproxy/proxies/default.xml") or ""
    if proxy and "PreFlow" in proxy:
        out.append({
            "kind": "flowhook-unseen",
            "severity": "warn",
            "breaks_c11": False,
            "component": "PreProxy FlowHook",
            "detail": (
                "This artefact is the ProxyEndpoint. A PreProxy FlowHook, if "
                "attached on the organisation, runs before any step we prepend. "
                "Ordering cannot be determined from the files provided. "
                "Fragment mode is not C11-conformant against that hook."
            ),
        })
    return out


def report_yaml(report: dict[str, Any]) -> str:
    return _dump(report)


def apply_or_refuse(target: str, existing: dict[str, str], produced: dict[str, str]) -> dict[str, str]:
    """Merge produced artefacts into existing. Refuse C11 breaks and any replace.

    A before-strip reader that does not replace anything still warns and
    proceeds. That is a standing choice, named on the report as
    warnedAndProceeded — not the default for replacement, and not silence.
    Requirement 3 and the boundary suite own that gap. A later writer of
    a 1.5.0 header still refuses (breaks_c11) without needing to replace.
    """
    report = inspect(target, existing)
    replacements = replacement_findings(target, existing, produced)
    report["findings"] = list(report.get("findings") or []) + replacements
    report["wouldRefuse"] = any(
        f.get("breaks_c11") or f.get("kind") == "replace"
        for f in report["findings"]
    )
    report = _finish_report(report)
    report_text = report_yaml(report)
    files = dict(produced)
    files["ctier-conflict-report.yaml"] = report_text
    if replacements:
        raise GenerateError(
            "replace",
            _replace_message(replacements),
            files={"ctier-conflict-report.yaml": report_text},
        )
    if any(f.get("breaks_c11") for f in report["findings"]):
        raise GenerateError(
            "c11",
            "existing configuration conflicts with C11; refusing to emit fragments",
            files=files,
        )
    if not existing:
        return dict(sorted(files.items()))
    if target == "kong":
        files["kong.yaml"] = merge_kong(
            existing.get("kong.yaml") or "",
            produced.get("kong.yaml") or "",
        )
    elif target == "apisix":
        files["apisix.yaml"] = merge_apisix(
            existing.get("apisix.yaml") or "",
            produced.get("apisix.yaml") or "",
        )
    else:
        files.update(merge_apigee(existing, produced))
    return dict(sorted(files.items()))


def merge_kong(existing_text: str, fragment_text: str) -> str:
    estate = yaml.safe_load(existing_text) or {}
    frag = yaml.safe_load(fragment_text) or {}
    if not estate:
        return fragment_text
    services = list(estate.get("services") or [])
    if not services:
        estate["services"] = frag.get("services") or []
        estate["plugins"] = list(estate.get("plugins") or []) + list(frag.get("plugins") or [])
        if frag.get("consumers") and not estate.get("consumers"):
            estate["consumers"] = frag["consumers"]
        return _dump(estate)
    host = services[0]
    catchall_plugins = _kong_catchall_plugins(host)
    existing_names = {r.get("name") for r in host.get("routes") or []}
    extra = []
    for route in (frag.get("services") or [{}])[0].get("routes") or []:
        if route.get("name") in existing_names and route.get("name") != "estate-catchall":
            continue
        extra.append(_with_copied_plugins(route, catchall_plugins))
    host["routes"] = [
        r for r in (host.get("routes") or []) if r.get("name") != "estate-catchall"
    ]
    host["routes"].extend(extra)
    if frag.get("url"):
        host["url"] = frag["url"]
    frag_svc = (frag.get("services") or [{}])[0]
    if frag_svc.get("url"):
        host["url"] = frag_svc["url"]
    estate.setdefault("plugins", [])
    have = {(p.get("name"), json.dumps(p.get("config") or {}, sort_keys=True)) for p in estate["plugins"]}
    for plugin in frag.get("plugins") or []:
        key = (plugin.get("name"), json.dumps(plugin.get("config") or {}, sort_keys=True))
        if key not in have:
            estate["plugins"].append(plugin)
            have.add(key)
    if frag.get("consumers") and not estate.get("consumers"):
        estate["consumers"] = frag["consumers"]
    estate["_format_version"] = estate.get("_format_version") or frag.get("_format_version") or "3.0"
    return _dump(estate)


def merge_apisix(existing_text: str, fragment_text: str) -> str:
    estate = yaml.safe_load(existing_text) or {}
    frag = yaml.safe_load(fragment_text) or {}
    if not estate:
        return fragment_text
    estate_routes = list(estate.get("routes") or [])
    templates = []
    for route in estate_routes:
        if route.get("name") == "estate-catchall" or route.get("id") == "estate-catchall":
            templates = _estate_plugin_copy(route.get("plugins") or {})
            break
    by_id = {str(r.get("id") or r.get("name")): r for r in estate_routes}
    merged = [r for r in estate_routes if str(r.get("id") or r.get("name")) != "estate-catchall"]
    by_id = {str(r.get("id") or r.get("name")): r for r in merged}
    for route in frag.get("routes") or []:
        rid = str(route.get("id") or route.get("name"))
        if rid in by_id:
            continue
        plugins = dict(route.get("plugins") or {})
        for name, conf in templates:
            plugins[name] = _occupy_plugin_slot(name, conf, plugins.get(name))
        route = dict(route)
        route["plugins"] = plugins
        merged.append(route)
        by_id[rid] = route
    estate["routes"] = merged
    if frag.get("consumers") and not estate.get("consumers"):
        estate["consumers"] = frag["consumers"]
    text = _dump(estate)
    if not text.rstrip().endswith("#END"):
        text = text.rstrip() + "\n\n#END\n"
    return text


def _estate_plugin_copy(plugins: dict) -> list[tuple[str, Any]]:
    return list((plugins or {}).items())


def merge_apigee(existing: dict[str, str], produced: dict[str, str]) -> dict[str, str]:
    """Prepend ctier PreFlow strip steps; copy new policies. Never overwrite."""
    out = dict(existing)
    estate_proxy = existing.get("apiproxy/proxies/default.xml") or ""
    frag_proxy = produced.get("apiproxy/proxies/default.xml") or ""
    if estate_proxy and frag_proxy:
        out["apiproxy/proxies/default.xml"] = _prepend_apigee_preflow(estate_proxy, frag_proxy)
    elif frag_proxy:
        out["apiproxy/proxies/default.xml"] = frag_proxy
    for path, text in produced.items():
        if path.startswith("apiproxy/policies/") or path.startswith("apiproxy/resources/"):
            if path not in out:
                out[path] = text
            elif out[path].strip() != text.strip():
                raise GenerateError(
                    "replace",
                    f"refusing to replace existing {path}",
                    files={},
                )
        if path in ("apiproxy/targets/default.xml",) and path not in existing:
            out[path] = text
        if path.endswith("ctier-generate.json"):
            out[path] = text
    return out


def _prepend_apigee_preflow(estate: str, fragment: str) -> str:
    """Insert fragment PreFlow Request steps ahead of estate PreFlow Request steps."""
    frag_steps = _preflow_request_steps(fragment)
    if "<PreFlow>" not in estate:
        return fragment
    if not frag_steps.strip():
        return estate
    marker = "<PreFlow>\n    <Request>\n"
    alt = "<PreFlow>\n        <Request>\n"
    for needle in (marker, alt, "<Request>\n"):
        idx = estate.find(needle)
        if idx >= 0:
            insert_at = idx + len(needle)
            return estate[:insert_at] + frag_steps + estate[insert_at:]
    return estate


def _preflow_request_steps(proxy_xml: str) -> str:
    start = proxy_xml.find("<PreFlow>")
    if start < 0:
        return ""
    req = proxy_xml.find("<Request>", start)
    end = proxy_xml.find("</Request>", req)
    if req < 0 or end < 0:
        return ""
    inner = proxy_xml[req + len("<Request>"):end]
    return inner


def _config_key(conf: Any) -> str:
    return json.dumps(conf or {}, sort_keys=True, default=str)


def _combinable(estate_conf: Any, produced_conf: Any) -> bool:
    """Same plugin slot, both are function lists: concatenate, don't replace."""
    if not isinstance(estate_conf, dict) or not isinstance(produced_conf, dict):
        return False
    return (
        isinstance(estate_conf.get("functions"), list)
        and isinstance(produced_conf.get("functions"), list)
        and estate_conf.get("phase") == produced_conf.get("phase")
    )


def _finish_report(report: dict[str, Any]) -> dict[str, Any]:
    report["warnedAndProceeded"] = [
        f for f in (report.get("findings") or [])
        if f.get("severity") == "warn" and not f.get("breaks_c11")
    ]
    return report


def _combine_functions(estate_conf: dict, produced_conf: dict) -> dict:
    """Keep estate Lua; run ctier's strip first, then again after.

    Reordering a stranger's functions is an intrusion. The plugin that
    breaks because a strip ran ahead of it is one that was reading
    reserved headers — the thing being prevented. Strip-first is C11
    in this slot. Repeating the strip after estate functions is the
    same property for writers in the only slot APISIX gives us: an
    estate setter of x-ctier-* must not reach the backend either.
    """
    out = json.loads(json.dumps(produced_conf))
    strip = list(produced_conf.get("functions") or [])
    estate = list(estate_conf.get("functions") or [])
    out["functions"] = strip + estate + strip
    estate_pri = (estate_conf.get("_meta") or {}).get("priority")
    produced_pri = (out.get("_meta") or {}).get("priority")
    pri_vals = [p for p in (estate_pri, produced_pri) if p is not None]
    if pri_vals:
        out.setdefault("_meta", {})
        out["_meta"]["priority"] = max(int(p) for p in pri_vals)
    return out


def _occupy_plugin_slot(name: str, estate_conf: Any, produced_conf: Any) -> Any:
    if produced_conf is None:
        return estate_conf
    if _config_key(estate_conf) == _config_key(produced_conf):
        return produced_conf
    if _combinable(estate_conf, produced_conf):
        return _combine_functions(estate_conf, produced_conf)
    raise GenerateError(
        "replace",
        f"refusing to replace existing {name}; merge leaked a collision",
        files={},
    )


def _kong_catchall_plugins(host: dict) -> list[dict]:
    for route in host.get("routes") or []:
        if route.get("name") == "estate-catchall":
            return list(route.get("plugins") or [])
    return []


def _with_copied_plugins(route: dict, catchall_plugins: list[dict]) -> dict:
    route = dict(route)
    plugins = list(route.get("plugins") or [])
    have = {p.get("name") for p in plugins}
    for plugin in catchall_plugins:
        name = plugin.get("name")
        if name in have:
            existing = next(p for p in plugins if p.get("name") == name)
            if _config_key(existing.get("config")) != _config_key(plugin.get("config")):
                raise GenerateError(
                    "replace",
                    f"refusing to replace existing {name} on route {route.get('name')}",
                    files={},
                )
            continue
        plugins.append(plugin)
        have.add(name)
    if plugins:
        route["plugins"] = plugins
    return route


def _summarise(conf: Any) -> str:
    text = _config_key(conf)
    if len(text) > 240:
        return text[:240] + "…"
    return text


def _replace_finding(component: str, would_write: str) -> dict[str, Any]:
    return {
        "kind": "replace",
        "severity": "error",
        "breaks_c11": False,
        "component": component,
        "wouldWrite": would_write,
        "detail": (
            f"Existing {component} would be replaced by ctier's emission. "
            "Refusing. Rename or remove the existing component; there is no override."
        ),
    }


def _replace_message(findings: list[dict[str, Any]]) -> str:
    parts = []
    for f in findings:
        parts.append(
            f"{f.get('component')}: ctier would have written {f.get('wouldWrite')}"
        )
    return "refusing to replace configuration ctier did not write; " + "; ".join(parts)


def _kong_plugin_names(plugins: list | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for plugin in plugins or []:
        name = str(plugin.get("name") or "")
        if name:
            out[name] = plugin.get("config")
    return out


def replacement_findings(
    target: str, existing: dict[str, str], produced: dict[str, str]
) -> list[dict[str, Any]]:
    """Collisions derived from this generate() output against `existing`.

    Not a maintained list of reserved names. Combinable function-list
    plugins are not replacements.
    """
    if target == "kong":
        return _replace_kong(existing.get("kong.yaml") or "", produced.get("kong.yaml") or "")
    if target == "apisix":
        return _replace_apisix(
            existing.get("apisix.yaml") or "", produced.get("apisix.yaml") or ""
        )
    return _replace_apigee(existing, produced)


def _replace_kong(existing_text: str, produced_text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not existing_text.strip() or not produced_text.strip():
        return out
    estate = yaml.safe_load(existing_text) or {}
    frag = yaml.safe_load(produced_text) or {}
    host = (estate.get("services") or [{}])[0]
    catchall = _kong_plugin_names(_kong_catchall_plugins(host))
    estate_global = _kong_plugin_names(estate.get("plugins"))
    frag_global = _kong_plugin_names(frag.get("plugins"))
    for name, conf in frag_global.items():
        if name not in estate_global:
            continue
        if _config_key(estate_global[name]) == _config_key(conf):
            continue
        out.append(_replace_finding(f"plugins/{name}", _summarise(conf)))
    estate_routes = {
        r.get("name"): r
        for r in (host.get("routes") or [])
        if r.get("name") != "estate-catchall"
    }
    for route in (frag.get("services") or [{}])[0].get("routes") or []:
        rname = route.get("name")
        if rname in estate_routes:
            out.append(_replace_finding(f"route/{rname}", "ctier route of this name"))
            continue
        produced_names = _kong_plugin_names(route.get("plugins"))
        for name, conf in produced_names.items():
            if name not in catchall:
                continue
            if _config_key(catchall[name]) == _config_key(conf):
                continue
            out.append(_replace_finding(f"{rname}/{name}", _summarise(conf)))
    return out


def _replace_apisix(existing_text: str, produced_text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not existing_text.strip() or not produced_text.strip():
        return out
    estate = yaml.safe_load(existing_text) or {}
    frag = yaml.safe_load(produced_text) or {}
    templates: dict[str, Any] = {}
    for route in estate.get("routes") or []:
        if route.get("name") == "estate-catchall" or route.get("id") == "estate-catchall":
            templates = dict(route.get("plugins") or {})
            break
    estate_ids = {
        str(r.get("id") or r.get("name"))
        for r in (estate.get("routes") or [])
        if str(r.get("id") or r.get("name")) != "estate-catchall"
    }
    for route in frag.get("routes") or []:
        rid = str(route.get("id") or route.get("name"))
        if rid in estate_ids:
            out.append(_replace_finding(f"route/{rid}", "ctier route of this id"))
            continue
        plugins = dict(route.get("plugins") or {})
        for name, estate_conf in templates.items():
            produced_conf = plugins.get(name)
            if produced_conf is None:
                continue
            if _config_key(estate_conf) == _config_key(produced_conf):
                continue
            if _combinable(estate_conf, produced_conf):
                continue
            out.append(_replace_finding(f"{rid}/{name}", _summarise(produced_conf)))
    return out


def _replace_apigee(
    existing: dict[str, str], produced: dict[str, str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    existing_names: dict[str, str] = {}
    for path, text in existing.items():
        if "/policies/" in path.replace("\\", "/") and path.endswith(".xml"):
            m = re.search(r'name="([^"]+)"', text)
            if m:
                existing_names[m.group(1)] = path
    for path, text in produced.items():
        if not (
            path.startswith("apiproxy/policies/") or path.startswith("apiproxy/resources/")
        ):
            continue
        if path in existing and existing[path].strip() != text.strip():
            out.append(_replace_finding(path, _summarise({"path": path})))
            continue
        if path.endswith(".xml"):
            m = re.search(r'name="([^"]+)"', text)
            if m and m.group(1) in existing_names and existing_names[m.group(1)] != path:
                out.append(_replace_finding(m.group(1), path))
    return out

