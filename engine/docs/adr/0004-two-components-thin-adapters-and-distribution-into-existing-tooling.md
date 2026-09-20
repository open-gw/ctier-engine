## ADR-004 — Two components, thin adapters, and distribution into existing tooling

**Status:** accepted with amendment

**Context.** "Engine" was doing two jobs: synchronous per-request classification,
and durable custody of withheld operations. Conflating them made the whole thing
look like a runtime service to be adopted wholesale.

**Decision, as amended.**

- **`ctier`** — a build-time **library** with a stable programmatic API, and a
  thin CLI over it: recommender, composer, coverage report, generator, and the
  reference classifier as conformance oracle. Runs in CI. Never in the request
  path.
- **Custody** — the only runtime service: pending Tier 3 context, the ledger, the
  scope floor. Off the request path except the Tier 3 persist.
- **Adapters** — a thin, data-driven plugin for Kong and APISIX. None for Apigee,
  APIM or Envoy.
- **Distribution surfaces** — ctier is embedded into the tooling teams already
  run, rather than asking them to adopt another tool.

> **As amended by RD:** *"How about extending this as a plugin to Postman /
> Specmatic / Bruno or other marketplace?"*

Candidate surfaces, in the order I would rank them by adoption per unit of
effort:

| Surface | Why |
|---|---|
| **Spectral ruleset** | The one you didn't name and the cheapest of all. Spectral is already in most enterprise OpenAPI pipelines, so coverage checking runs inside linting they do today — no new tool, no new pipeline step |
| **Backstage plugin** | Where enterprise API catalogues live. Tier coverage per API is the executive-facing view of Level 0 |
| **Postman** | Classify a collection, show tiers in the workspace where API teams already work |
| **Specmatic** | Contract testing from OpenAPI — the conformance fixtures are a natural fit for its harness |
| **Bruno**, VS Code | Developer-local surfaces; useful, lower reach |

**Consequences.** Tiers 1, 2 and 4 deploy with **no new runtime component**,
because suspension now lives on the credential (ADR-003). That is what makes the
adoption ladder possible.

The distribution amendment imposes one architectural constraint that must be
honoured from the first commit rather than retrofitted: **the core is a library
with a stable API, and every surface — CLI included — is a thin shell over it.**
Logic that ends up inside the CLI cannot be embedded in a Spectral ruleset or a
Backstage plugin later without being rewritten.
