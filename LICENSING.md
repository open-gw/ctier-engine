# Licensing

**This document records the project's reasoning about third-party licences. It
is not legal advice. It is written by the maintainer, not by counsel, and where
a question is genuinely unresolved it says so rather than asserting an answer.**

Downstream consumers with specific compliance obligations should form their own
view and are encouraged to open an issue if they believe anything here is wrong.

---

## 1. Project licence

ctier-engine source code is licensed under the Apache License, Version 2.0.
That choice is ratified: `LICENSE`, `NOTICE`, `engine/pyproject.toml`
(`license = Apache-2.0`), and SPDX headers on package sources agree.

Contributions are accepted inbound under the same terms. See `CONTRIBUTING.md`.

The published specification at `github.com/open-gw/ctier` is licensed CC BY 4.0
and grants no patent licence. The vendored pin under `engine/ctier/spec/`
carries the attribution that licence requires. Subject matter described in both
repositories is the subject of US provisional patent application 64/137,066,
filed 19 August 2026. The Apache License section 3 patent grant applies to this
Work and to contributions combined with this Work. It does not license that
application, or any patent, in the abstract.

## 2. What is distributed

This repository currently publishes source. There is no shaded or bundled
artifact. Installing the package with pip pulls dependencies from PyPI under
their own licences. "This project is licensed under Apache 2.0" is a statement
about this project's source. It is not a statement about those dependencies.

## 3. Dependency inventory

### Runtime

| Dependency | Licence | Source of determination |
|---|---|---|
| pydantic | MIT | artifact metadata |
| PyYAML | MIT | artifact metadata |

### Optional (`serve` extra)

| Dependency | Licence | Source of determination |
|---|---|---|
| fastapi | MIT | artifact metadata |
| uvicorn | BSD-3-Clause | artifact metadata |
| httpx | BSD-3-Clause | artifact metadata |

### Development (`dev` extra)

| Dependency | Licence | Source of determination |
|---|---|---|
| pytest | MIT | artifact metadata |

## 4. Adding a dependency

State the licence in the pull request and add a row here. A dependency whose
licence does not clearly permit redistribution with an Apache-2.0 work must
not be added to the default install.
