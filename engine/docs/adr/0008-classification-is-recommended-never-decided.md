## ADR-008 — Classification is recommended, never decided

**Status:** accepted as drafted

**Context.** The barrier to adoption is not technical. Someone must classify
thousands of endpoints, and that cost is human. Structural and semantic inference
from the interface description can shrink it.

**Decision.** ctier ships a recommender: structural signals first because they are
reproducible — method, path shape, response cardinality, whether a reversing
operation exists — then semantic reading of `summary` and `description`. It runs
**once at design time, producing an artefact**, never inside the build, so CI
stays deterministic and offline. Every recommendation records its input text and
digest, the rule or model version, and confidence.

Classification therefore has three states: **declared** (human confirmed),
**recommended** (awaiting review), **absent** (Tier 4).

**Consequences.** The recommender is positioned as **triage, not
classification** — it says which 200 of 4,000 endpoints need a human, in risk
order. It must never be the authority, and the model backend must be pluggable,
including local, or regulated deployments cannot use it at all.

The interesting output is not the recommendation. The recommender and the agent
read the same document, so an operation whose description understates its
consequence misleads both — and a large gap between recommended and confirmed
tier is a measurable signal that this endpoint misrepresents itself to an
autonomous consumer. That is a documentation defect and an agent-safety finding
in one number, and nothing else in the system surfaces it.
