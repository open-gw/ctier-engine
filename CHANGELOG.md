# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Open-source community files aligned with `open-gw/gateway-db-mcp`: `NOTICE`,
  `CITATION.cff`, `LICENSING.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, `CHANGELOG.md`, Dependabot, and `CODEOWNERS`

## [0.3.0] — 2026-09-17

### Removed

- Compatibility shims dated engine 0.3.0 or earlier: `ledger-*` schema
  heads, ingress `composition` / `compositionDigest`, Kong plugin
  `composition`, dual-emitted `x-ctier-composition`, and downstream
  `X-Correlation-Id` on 202.

## [0.1.0] — 2026-09-05

### Added

- Classification core (`engine/ctier`): four tiers, five criteria, unidirectional
  escalation, derived idempotency keys
- Population-scale reads distinguished from writes; disclosure of personal or
  regulated data at that scale is Tier 3
- `escalate_to` cannot lower a tier already raised by a prior stage
- A declared `contributes_weight` of zero is honoured
- Criteria without an explicit tier resolve through `compute_tier`
- Architecture decision records 0001–0008
- Solution design, implementation plan, and PRD C1–C13

[Unreleased]: https://github.com/open-gw/ctier-engine/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/open-gw/ctier-engine/compare/v0.1.0...v0.3.0
[0.1.0]: https://github.com/open-gw/ctier-engine/releases/tag/v0.1.0
