local typedefs = require "kong.db.schema.typedefs"

return {
  name = "ctier",
  fields = {
    { protocols = typedefs.protocols_http },
    { config = {
        type = "record",
        fields = {
          { tier = { type = "integer", required = true, one_of = { 1, 2, 3, 4 } } },
          { deployment = { type = "string", required = true } },
          { operation = { type = "string" } },
          { excluded = { type = "boolean", default = false } },
          { bound_parameter = { type = "string" } },
          { bound_max = { type = "integer" } },
          { handoff_authority = { type = "string" } },
          -- Nested custody records are omitted-as-empty and then fail required url.
          { custody_url = { type = "string" } },
          { custody_timeout_ms = { type = "integer", default = 200, gt = 0 } },
          -- JSONL the plugin appends when persist cannot reach custody.
          { ledger_fallback = { type = "string" } },
          -- Out-of-band floor poll. Explicit: an inherited default is not a decision.
          { floor_poll_ms = { type = "integer", default = 1000, gt = 0 } },
          -- Operation scope the token must carry. Absent on excluded
          -- operations: those keep the provisioning refusal as detection.
          { required_scope = { type = "string" } },
          -- Level 1: classify and emit a decision record, enforce nothing.
          { observe = { type = "boolean", default = false } },
          -- Operations present in the composed description. The same
          -- governed-set 40 requires an implementation to publish. A
          -- match with no route-level instance is C2's undeclared
          -- default. A miss is an undetermined refusal, not Tier 4.
          { ["governed-set"] = { type = "array", elements = { type = "string" }, default = {} } },
        },
      },
    },
  },
}
