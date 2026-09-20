# Local-rig signing material

This published tree ships **obviously-fake placeholders** in
`keycloak-rsa.json` and `public.pem`. They are not a Keycloak-usable
keypair. Offline `generate()` goldens match the placeholders.

Before a live rig, regenerate real material:

```bash
openssl genrsa -out /tmp/ctier-key.pem 2048
openssl rsa -in /tmp/ctier-key.pem -pubout -out public.pem
openssl req -new -x509 -key /tmp/ctier-key.pem -out /tmp/ctier-cert.pem \
  -days 3650 -subj "/CN=ctier-realm"
openssl pkcs8 -topk8 -nocrypt -in /tmp/ctier-key.pem
```

Write the PKCS#8 body and the certificate body (PEM headers stripped) into
`keycloak-rsa.json` as `privateKey` and `certificate`, then regenerate
goldens and `targets/*/live/realm.json` via `generate()`.

Local-dev compose defaults (`local-dev-admin`, `local-dev-custody-token`,
`local-dev-agent-secret`) are fixtures for localhost only — change them
before exposing any port beyond the machine.
