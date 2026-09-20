# Security Policy

This repository is a governance and enforcement reference. Someone will
eventually find a vulnerability. Report it privately — not as a public
issue.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use one of:

- Email: **security@open-gw.io**
- A private [GitHub Security Advisory](https://github.com/open-gw/ctier-engine/security/advisories/new)

Include what you found, how to reproduce it, affected versions or commits,
and impact. A suggested fix is welcome but not required.

### What to expect

| Step | Timeline |
|---|---|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 7 days |
| Fix or mitigation | Within 30 days for critical issues |
| Public disclosure | After a fix is released |

Credit in release notes is the default unless you ask to stay anonymous.

## In scope

- Honouring a caller-supplied `x-ctier-*` header as a declared tier (C11)
- An escalation stage producing a tier lower than the tier entering it (C3)
- Classification of an undeclared operation as anything other than the
  undeclared default (C2)
- A derived idempotency key colliding across different subjects (C7)
- Custody or ledger paths that execute without the recorded authorisation
- Record sinks that claim durability they do not have

## Out of scope

- Security of a gateway you deploy the generated config into
- Security of the authorisation server that enforces exclusion, suspension,
  and delegation
- Operator failure to strip inbound `x-ctier-*` headers at the edge
- Credentials in a local compose rig that never left `localhost`
