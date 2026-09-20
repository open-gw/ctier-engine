-- Harness probe at a Kong priority between cors (2000) and a raised ctier.
-- Not a product plugin. Live E2 only.
local Probe = {
  PRIORITY = 1500,
  VERSION = "0.1.0",
}

local watch = {
  ["x-correlation-id"] = true,
  ["x-idempotency-key"] = true,
}
local emit = {
  ["x-ctier-deployment"] = true,
  ["x-ctier-correlation-id"] = true,
  ["x-ctier-tier"] = true,
  ["x-ctier-operation"] = true,
  ["x-ctier-composition"] = true,
}

function Probe:access(_conf)
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
end

return Probe
