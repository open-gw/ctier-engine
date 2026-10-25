# Known issues

`generate` does not re-validate. A partially declared criteria object is
completed from defaults, then `max(declared, computed)` runs. `compose`
rejects a half-written object.
