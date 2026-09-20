local typedefs = require "kong.db.schema.typedefs"

return {
  name = "ctier-estate-probe",
  fields = {
    { protocols = typedefs.protocols_http },
    { config = { type = "record", fields = {} } },
  },
}
