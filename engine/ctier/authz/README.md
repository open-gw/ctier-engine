# Local-rig signing material

`keycloak-rsa.json` and `public.pem` are a test key generated for this
repository, used by nothing outside this lab, and must not be reused.

`generate()` reads those two files. The local Docker rigs import the
realm that produces, and Keycloak boots from it. A visitor does not
generate a key for `make demo` or `pytest --live`. The live compose
files bind Keycloak to localhost.

The package realms and the offline goldens carry that same lab key. The
comparison normalises `privateKey`, `certificate`, and the public-key PEM,
so `test_golden_generate_cases` and `test_golden_kong_cases` do not assert
this key's bytes.

Local-dev compose defaults (`local-dev-admin`, `local-dev-custody-token`,
`local-dev-agent-secret`) are fixtures for localhost only — change them
before exposing any port beyond the machine.
