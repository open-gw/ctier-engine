-- ctier: data-driven enforcement. Does not classify, does not parse paths.
-- Network calls on the request path: POST /v1/pending for Tier 3 persist,
-- and POST /v1/ledger for evidence of a decision already compiled into this
-- configuration. GET /v1/floors runs on a timer, never on a request.
-- Never GET custody to ask whether an agent is suspended.
local CtierHandler = {
  PRIORITY = 10000,
  VERSION = "0.5.0",
}

local cjson = require "cjson.safe"

local PREFIX = "x-ctier-"
local ALIAS = {
  ["x-correlation-id"] = true,
  ["idempotency-key"] = true,
  ["x-idempotency-key"] = true,
}

local T4_BODY = '{"status":"agent_suspended","humanTakeoverRequired":true,'
  .. '"autoResume":false,"agentAction":"halt_and_hand_off"}'
local UNASSIGNED_BODY = '{"status":"unassigned","retryable":false,'
  .. '"autoResume":false,"agentAction":"halt"}'
local PROV_BODY = '{"status":"provisioning_defect","retryable":false,'
  .. '"autoResume":false,"agentAction":"continue_task_without_this_step"}'
-- ADR-005: unavailability is evidence about infrastructure, not the agent.
local UNAVAILABLE_BODY = '{"status":"custody_unavailable","retryable":true,'
  .. '"agentAction":"retry_later"}'
local UNAUTH_BODY = '{"status":"unauthorized","agentAction":"halt"}'

-- Prefer config.deployment. The composition key is gone.
local function deployment_digest(conf)
  if type(conf.deployment) == "string" and conf.deployment ~= "" then
    return conf.deployment
  end
  return ""
end

local function strip_inbound()
  local headers = kong.request.get_headers()
  for name, _ in pairs(headers) do
    if type(name) == "string" then
      local lower = string.lower(name)
      if string.sub(lower, 1, 8) == PREFIX or ALIAS[lower] then
        kong.service.request.clear_header(name)
      end
    end
  end
end

local function escalate(tier)
  if tier < 4 then
    return tier + 1
  end
  return 4
end

-- The only arithmetic: configured query parameter versus configured maximum.
local function apply_bounds(conf, tier)
  if not conf.bound_parameter or not conf.bound_max then
    return tier
  end
  local args = kong.request.get_query()
  local raw = args[conf.bound_parameter]
  if type(raw) == "table" then
    raw = raw[1]
  end
  if raw == nil then
    return tier
  end
  local n = tonumber(raw, 10)
  if n and n > conf.bound_max then
    return escalate(tier)
  end
  return tier
end

local function refuse_tier4()
  return kong.response.exit(423, T4_BODY, {
    ["Content-Type"] = "application/json",
    ["X-Agent-Action"] = "halt_and_hand_off",
    ["Cache-Control"] = "no-store",
  })
end

local function refuse_unassigned()
  -- Not Tier 4. No halt_and_hand_off: this is a miss, not a suspension.
  return kong.response.exit(423, UNASSIGNED_BODY, {
    ["Content-Type"] = "application/json",
    ["Cache-Control"] = "no-store",
  })
end

local function in_governed(conf)
  -- Route name is the generated operation identity. A fragment extra or
  -- a post-generation add is not on this list.
  local route = kong.router.get_route()
  local name = route and route.name
  if type(name) ~= "string" or name == "" then
    return false
  end
  local set = conf["governed-set"]
  if type(set) ~= "table" then
    return false
  end
  for i = 1, #set do
    if set[i] == name then
      return true
    end
  end
  return false
end

local function refuse_unauthorized()
  return kong.response.exit(401, UNAUTH_BODY, {
    ["Content-Type"] = "application/json",
    ["Cache-Control"] = "no-store",
  })
end

local function bearer_payload()
  local auth = kong.request.get_header("Authorization")
  if type(auth) ~= "string" then
    return nil
  end
  local token = auth:match("^[Bb]earer%s+(%S+)$")
  if not token then
    return nil
  end
  local payload_b64 = token:match("^[^%.]+%.([^%.]+)%.")
  if not payload_b64 then
    return nil
  end
  local padded = payload_b64:gsub("-", "+"):gsub("_", "/")
  local mod = #padded % 4
  if mod > 0 then
    padded = padded .. string.rep("=", 4 - mod)
  end
  local decoded = ngx.decode_base64(padded)
  if not decoded then
    return nil
  end
  local obj = cjson.decode(decoded)
  if type(obj) ~= "table" then
    return nil
  end
  return obj
end

local function has_required_scope(required)
  -- Reads the bearer payload. Signature already verified by the jwt plugin.
  -- The claim is on the token Kong accepted; Kong does not call the issuer.
  if type(required) ~= "string" or required == "" then
    return true
  end
  local obj = bearer_payload()
  if not obj then
    return false
  end
  local raw = obj.scope
  if type(raw) ~= "string" then
    return false
  end
  for s in string.gmatch(raw, "%S+") do
    if s == required then
      return true
    end
  end
  return false
end

local function refuse_provisioning()
  return kong.response.exit(403, PROV_BODY, {
    ["Content-Type"] = "application/json",
    ["X-Agent-Action"] = "continue_task_without_this_step",
    ["Cache-Control"] = "no-store",
  })
end

local function custody_unavailable()
  -- Explicit Retry-After. Not a library default. Not Tier 4. Not provisioning.
  return kong.response.exit(503, UNAVAILABLE_BODY, {
    ["Content-Type"] = "application/json",
    ["Retry-After"] = "5",
    ["Cache-Control"] = "no-store",
  })
end

local function query_map()
  local args = kong.request.get_query() or {}
  local out = {}
  for k, v in pairs(args) do
    if type(v) == "table" then
      out[k] = tostring(v[1])
    else
      out[k] = tostring(v)
    end
  end
  return out
end

local function credential_exp()
  -- Pass the exp claim as a value. Never the token.
  local obj = bearer_payload()
  if type(obj) ~= "table" or type(obj.exp) ~= "number" then
    return nil
  end
  return obj.exp
end

local function header(res_headers, name)
  if type(res_headers) ~= "table" then
    return nil
  end
  return res_headers[name] or res_headers[string.lower(name)]
end

local function now_iso()
  return os.date("!%Y-%m-%dT%H:%M:%SZ")
end

local function new_id()
  return string.format("%s-%d-%d", ngx.now(), ngx.worker.pid(), math.random(1, 1000000000))
end

local function agent_and_scope()
  local agent = kong.request.get_header("X-Agent-Id") or "unknown"
  local task = kong.request.get_header("X-Task-Id")
  return agent, task, task or agent
end

local function operation_anchor(conf)
  return conf.operation or (kong.request.get_method() .. " " .. kong.request.get_path())
end

local function escalation_reason(conf, declared, applied)
  if not conf.operation then
    return "undeclared-operation"
  end
  if applied > declared then
    if conf.bound_parameter then
      return "payload-exceeds-declared-bounds"
    end
    return "computed-tier-exceeds-declared"
  end
  return "none"
end

-- A only, bounded by custody_timeout_ms. Hostname connect through
-- resty.http waits on AAAA/UDP past that bound when compose-stop
-- removes the name; /status still answers because the wait yields.
local function ipv4(host, timeout)
  if host:match("^%d+%.%d+%.%d+%.%d+$") then
    return host
  end
  -- Cluster DNS. A only, bounded by the persist timeout.
  local ok, resolver = pcall(require, "resty.dns.resolver")
  if not ok then
    return nil, "dns resolver"
  end
  local r, err = resolver:new({
    nameservers = { "127.0.0.11" },
    retrans = 1,
    timeout = timeout,
  })
  if not r then
    return nil, err
  end
  local answers, err = r:query(host, { qtype = r.TYPE_A })
  if not answers then
    return nil, err
  end
  if answers.errcode then
    return nil, answers.errstr or "dns error"
  end
  for i = 1, #answers do
    if answers[i].address then
      return answers[i].address
    end
  end
  return nil, "no A record"
end

local function custody_url(url, timeout)
  local scheme, host, port, rest = url:match("^(https?)://([^:/]+):?(%d*)(.*)$")
  if not scheme then
    return nil, nil, "bad custody url"
  end
  local ip, err = ipv4(host, timeout)
  if not ip then
    return nil, nil, err
  end
  if port == "" then
    port = (scheme == "https") and "443" or "80"
  end
  return scheme .. "://" .. ip .. ":" .. port .. rest, host
end

local function post_json(conf, path, payload)
  local http = require "resty.http"
  local httpc = http.new()
  local timeout = conf.custody_timeout_ms
  if type(timeout) ~= "number" or timeout <= 0 then
    timeout = 200
  end
  httpc:set_timeouts(timeout, timeout, timeout)
  local url, host, err = custody_url(conf.custody_url:gsub("/$", "") .. path, timeout)
  if not url then
    return nil, err
  end
  return httpc:request_uri(url, {
    method = "POST",
    body = cjson.encode(payload),
    headers = {
      ["Content-Type"] = "application/json",
      ["Accept"] = "application/json",
      ["Host"] = host,
    },
    keepalive = false,
  })
end

-- Out-of-band. The request path only reads ngx.shared.ctier_floors.
local poller_started = false

local function floor_poll_ms(conf)
  local ms = conf.floor_poll_ms
  if type(ms) ~= "number" or ms <= 0 then
    return 1000
  end
  return ms
end

local function refresh_floors(url, timeout_ms, ttl)
  local http = require "resty.http"
  local httpc = http.new()
  httpc:set_timeouts(timeout_ms, timeout_ms, timeout_ms)
  local resolved, host, err = custody_url(url, timeout_ms)
  if not resolved then
    kong.log.err("ctier floor poll failed: ", err or "dns")
    return
  end
  local res, err = httpc:request_uri(resolved, {
    method = "GET",
    headers = { ["Accept"] = "application/json", ["Host"] = host },
    keepalive = false,
  })
  if not res or res.status ~= 200 or not res.body then
    kong.log.err("ctier floor poll failed: ", err or (res and res.status) or "no response")
    return
  end
  local body = cjson.decode(res.body)
  if type(body) ~= "table" or type(body.floors) ~= "table" then
    return
  end
  local dict = ngx.shared.ctier_floors
  if not dict then
    kong.log.err("ctier_floors shared dict is not configured; accumulation will not escalate")
    return
  end
  local seen = {}
  for _, row in ipairs(body.floors) do
    if type(row) == "table" and type(row.correlationScope) == "string" and row.floor then
      dict:set(row.correlationScope, tonumber(row.floor), ttl)
      seen[row.correlationScope] = true
    end
  end
  local keys = dict:get_keys(0)
  for i = 1, #keys do
    if not seen[keys[i]] then
      dict:delete(keys[i])
    end
  end
end

local function start_floor_poller(conf)
  if poller_started then
    return
  end
  if type(conf.custody_url) ~= "string" or conf.custody_url == "" then
    return
  end
  poller_started = true
  local url = conf.custody_url:gsub("/$", "") .. "/v1/floors"
  local timeout = conf.custody_timeout_ms
  if type(timeout) ~= "number" or timeout <= 0 then
    timeout = 200
  end
  local interval_ms = floor_poll_ms(conf)
  local interval = interval_ms / 1000
  -- TTL of two intervals: a dead poller expires floors, which is no
  -- escalation (not maximum escalation).
  local ttl = (2 * interval_ms) / 1000
  kong.log.notice("ctier floor poller interval_ms=", interval_ms)
  local function tick(premature)
    if premature then
      return
    end
    refresh_floors(url, timeout, ttl)
  end
  local ok, err = ngx.timer.at(0, tick)
  if not ok then
    kong.log.err("ctier floor poller at(0): ", err)
  end
  ok, err = ngx.timer.every(interval, tick)
  if not ok then
    kong.log.err("ctier floor poller every: ", err)
    poller_started = false
  end
end

-- No dictionary entry, missing dict, or failed poll: no escalation.
-- Accumulation can only raise a compiled floor; its absence permits
-- nothing that the declared tier did not already allow.
local function apply_scope_floor(conf, tier)
  start_floor_poller(conf)
  local dict = ngx.shared.ctier_floors
  if not dict then
    kong.log.notice("ctier no floor dictionary; no accumulation escalation")
    return tier
  end
  local _, _, scope = agent_and_scope()
  local raw = dict:get(scope)
  if raw == nil then
    kong.log.debug("ctier no published floor for ", scope, "; no escalation")
    return tier
  end
  local floor = tonumber(raw, 10)
  if floor and floor > tier then
    return floor
  end
  return tier
end

local function append_fallback(conf, record)
  local path = conf.ledger_fallback
  if type(path) ~= "string" or path == "" then
    return
  end
  local fh, err = io.open(path, "a")
  if not fh then
    kong.log.err("ctier ledger fallback open failed: ", err)
    return
  end
  fh:write(cjson.encode(record) .. "\n")
  fh:close()
end

-- Per-worker emitter. A shared-memory counter would mix workers and
-- reset on restart without an epoch — that reset would look like a
-- hole. Allocating a number is not recording; the write may still fail.
local seq_state

local function allocate_sequence()
  if not seq_state then
    seq_state = {
      epoch = string.format("%s-%s", tostring(ngx.now()), tostring(ngx.worker.pid())),
      n = 0,
    }
  end
  seq_state.n = seq_state.n + 1
  return seq_state.epoch, seq_state.n
end

local function emit_sink(marker, record)
  local epoch, seq = allocate_sequence()
  kong.log.notice(marker, "epoch=", epoch, " seq=", seq, " ", cjson.encode(record))
end

-- Evidence of a decision already made at compile time. Fail-open: a missed
-- write does not unmake the disposition. The error-log line is the claimed
-- C10 sink. Ledger POST is not claimed.
local function decision_evidence(conf, declared, applied, disposition, reason, correlation_id)
  local agent, task, scope = agent_and_scope()
  local cid = correlation_id or new_id()
  local declared_tier = declared
  if not conf.operation then
    declared_tier = cjson.null
  end
  return {
    ctierSchema = "decision-record/0.2.0",
    id = cid,
    timestamp = now_iso(),
    operationAnchor = operation_anchor(conf),
    agentId = agent,
    correlationScope = scope,
    correlationId = cid,
    declaredTier = declared_tier,
    appliedTier = applied,
    escalationReason = reason or escalation_reason(conf, declared, applied),
    disposition = disposition,
    -- Occupies the schema field. Not a C7 key. Do not forward it.
    idempotencyKey = cid,
    deploymentDigest = deployment_digest(conf),
  }
end

local function record_decision(conf, declared, applied, disposition, reason, correlation_id)
  local record = decision_evidence(conf, declared, applied, disposition, reason, correlation_id)
  emit_sink("[ctier-decision] ", record)
  if type(conf.custody_url) ~= "string" or conf.custody_url == "" then
    return record
  end
  local agent, task, scope = agent_and_scope()
  local payload = {
    type = "decision",
    operationAnchor = operation_anchor(conf),
    agentId = agent,
    taskId = task,
    correlationScope = scope,
    correlationId = record.correlationId,
    declaredTier = record.declaredTier,
    appliedTier = applied,
    escalationReason = reason or escalation_reason(conf, declared, applied),
    disposition = disposition,
    deploymentDigest = deployment_digest(conf),
    method = kong.request.get_method(),
    path = kong.request.get_path(),
    query = query_map(),
    body = kong.request.get_raw_body(),
  }
  -- Authorization is deliberately absent. Fail-open: the log line is the claim.
  local res, err = post_json(conf, "/v1/ledger", payload)
  if not res or (res.status ~= 201 and res.status ~= 200) then
    kong.log.err("ctier ledger decision failed: ", err or (res and res.status) or "no response")
    return record
  end
  if res.body then
    local obj = cjson.decode(res.body)
    if type(obj) == "table" then
      return obj
    end
  end
  return record
end

local function record_attempt(conf, declared, reason)
  local agent, task, scope = agent_and_scope()
  -- Sequence stays on the sink line (epoch=/seq=). Not in this object.
  local record = {
    ctierSchema = "attempt-record/0.3.0",
    id = new_id(),
    timestamp = now_iso(),
    operationAnchor = operation_anchor(conf),
    agentId = agent,
    correlationScope = scope,
    appliedTier = cjson.null,
    deploymentDigest = deployment_digest(conf),
    reason = reason,
  }
  -- Present = a declaration was made. Omit when none was.
  -- Do not write 4 to mean unknown.
  if declared ~= nil then
    record.declaredTier = declared
  end
  -- Same object Kong writes to JSONL. The log line is the claimed sink.
  emit_sink("[ctier-attempt] ", record)
  append_fallback(conf, record)
end

local function withhold(conf, declared, applied)
  local agent, task, scope = agent_and_scope()
  local payload = {
    method = kong.request.get_method(),
    path = kong.request.get_path(),
    query = query_map(),
    body = kong.request.get_raw_body(),
    operationAnchor = operation_anchor(conf),
    agentId = agent,
    taskId = task,
    correlationScope = scope,
    declaredTier = declared,
    appliedTier = applied,
    deploymentDigest = deployment_digest(conf),
    authority = conf.handoff_authority,
    credentialExp = credential_exp(),
    escalationReason = escalation_reason(conf, declared, applied),
  }
  -- Authorization is deliberately absent. Do not copy inbound headers.
  local res, err = post_json(conf, "/v1/pending", payload)
  if not res or res.status ~= 202 or not res.body then
    kong.log.err("ctier custody persist failed: ", err or (res and res.status) or "no response")
    record_attempt(conf, declared, "custody-unavailable")
    return custody_unavailable()
  end
  local relay = {
    ["Content-Type"] = "application/json",
    ["Cache-Control"] = header(res.headers, "Cache-Control") or "no-store",
  }
  for _, name in ipairs({ "X-Agent-Action", "x-ctier-correlation-id", "X-Ctier-Tier" }) do
    local value = header(res.headers, name)
    if value then
      relay[name] = value
    end
  end
  local join = header(res.headers, "x-ctier-correlation-id")
  if join then
    relay["x-ctier-correlation-id"] = join
  end
  -- Never emit Retry-After on a withhold, even if a hop added one.
  return kong.response.exit(202, res.body, relay)
end

function CtierHandler:access(conf)
  strip_inbound()
  start_floor_poller(conf)
  -- Global instance only. A route-level instance is a compiled decision
  -- (conf.operation set). C2's undeclared default is a governed route
  -- with no instance. A path not in the composition is neither.
  if not conf.operation and not in_governed(conf) then
    record_attempt(conf, nil, "unassigned")
    return refuse_unassigned()
  end
  if conf.observe then
    local cid = new_id()
    local rec = record_decision(conf, conf.tier, conf.tier, "execute", "none", cid)
    kong.service.request.set_header("x-ctier-correlation-id", (rec and rec.correlationId) or cid)
    kong.service.request.set_header("x-ctier-tier", tostring(conf.tier))
    local digest = deployment_digest(conf)
    kong.service.request.set_header("x-ctier-deployment", digest)
    if conf.operation then
      kong.service.request.set_header("x-ctier-operation", conf.operation)
    end
    return
  end
  if not has_required_scope(conf.required_scope) then
    return refuse_unauthorized()
  end
  if conf.excluded then
    record_decision(conf, conf.tier, conf.tier, "refuse-provisioning")
    return refuse_provisioning()
  end
  local declared = conf.tier
  local after_bounds = apply_bounds(conf, conf.tier)
  local tier = apply_scope_floor(conf, after_bounds)
  local reason
  if tier > after_bounds then
    reason = "session-accumulation"
  else
    reason = escalation_reason(conf, declared, tier)
  end
  if tier >= 4 then
    record_decision(conf, declared, tier, "refuse-and-suspend", reason)
    return refuse_tier4()
  end
  if tier == 3 then
    if not conf.custody_url then
      record_decision(conf, declared, tier, "refuse-provisioning", reason)
      return refuse_provisioning()
    end
    return withhold(conf, declared, tier)
  end
  local cid = new_id()
  local rec = record_decision(conf, declared, tier, "execute", reason, cid)
  kong.service.request.set_header("x-ctier-correlation-id", (rec and rec.correlationId) or cid)
  -- C7 HMAC lives on the ledger row. Level 2 has no custody, so no
  -- stored key. A log-sink record occupies idempotencyKey for the
  -- schema only; do not forward it.
  if rec and rec.idempotencyKey
      and type(conf.custody_url) == "string" and conf.custody_url ~= "" then
    kong.service.request.set_header("Idempotency-Key", rec.idempotencyKey)
  end
  kong.service.request.set_header("x-ctier-tier", tostring(tier))
  local digest = deployment_digest(conf)
  kong.service.request.set_header("x-ctier-deployment", digest)
  if conf.operation then
    kong.service.request.set_header("x-ctier-operation", conf.operation)
  end
end

return CtierHandler
