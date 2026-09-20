# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Install a boundary probe into generated proxy files.

The probe records agent-reserved inbound names as x-boundary-probe.
position=before sits ahead of the strip (fragment). position=after
sits behind it (bundle).
"""
from __future__ import annotations

import yaml

KONG_LUA = """
local watch = {["x-correlation-id"]=true, ["x-idempotency-key"]=true}
local emit = {
  ["x-ctier-deployment"]=true,
  ["x-ctier-correlation-id"]=true,
  ["x-ctier-tier"]=true,
  ["x-ctier-operation"]=true,
  ["x-ctier-composition"]=true,
}
local seen = {}
local h = kong.request.get_headers()
for name, _ in pairs(h) do
  local l = string.lower(name)
  if watch[l] or (string.sub(l, 1, 8) == "x-ctier-" and not emit[l]) then
    table.insert(seen, l)
  end
end
if #seen > 0 then
  kong.service.request.set_header("x-boundary-probe", table.concat(seen, ","))
end
""".strip()

APISIX_LUA = """
return function(conf, ctx)
  local watch = {["x-correlation-id"]=true, ["x-idempotency-key"]=true}
  local emit = {
    ["x-ctier-deployment"]=true,
    ["x-ctier-correlation-id"]=true,
    ["x-ctier-tier"]=true,
    ["x-ctier-operation"]=true,
    ["x-ctier-composition"]=true,
  }
  local seen = {}
  local h = ngx.req.get_headers()
  for name, _ in pairs(h) do
    local l = string.lower(name)
    if watch[l] or (string.sub(l, 1, 8) == "x-ctier-" and not emit[l]) then
      table.insert(seen, l)
    end
  end
  if #seen > 0 then
    ngx.req.set_header("x-boundary-probe", table.concat(seen, ","))
  end
end
""".strip()


def attach_probe(files: dict[str, str], target: str, *, position: str) -> dict[str, str]:
    if position not in ("before", "after"):
        raise ValueError(f"position must be before|after, not {position!r}")
    out = dict(files)
    if target == "kong":
        out["kong.yaml"] = _kong(out["kong.yaml"], position)
    elif target == "apisix":
        out["apisix.yaml"] = _apisix(out["apisix.yaml"], position)
    else:
        raise ValueError(f"no live probe injector for {target}")
    return out


def _kong(text: str, position: str) -> str:
    doc = yaml.safe_load(text) or {}
    name = "pre-function" if position == "before" else "post-function"
    plugin = {"name": name, "config": {"access": [KONG_LUA]}}
    plugins = list(doc.get("plugins") or [])
    plugins.append(plugin)
    doc["plugins"] = plugins
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000)


def _apisix(text: str, position: str) -> str:
    doc = yaml.safe_load(text) or {}
    for route in doc.get("routes") or []:
        plugins = dict(route.get("plugins") or {})
        pre = plugins.get("serverless-pre-function")
        if not isinstance(pre, dict):
            continue
        fns = list(pre.get("functions") or [])
        if position == "before":
            fns = [APISIX_LUA] + fns
            meta = dict(pre.get("_meta") or {})
            meta["priority"] = max(int(meta.get("priority") or 21000), 30000)
            pre["_meta"] = meta
        else:
            fns = fns + [APISIX_LUA]
        pre["functions"] = fns
        plugins["serverless-pre-function"] = pre
        route["plugins"] = plugins
    dumped = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000)
    if not dumped.rstrip().endswith("#END"):
        dumped = dumped.rstrip() + "\n\n#END\n"
    return dumped
