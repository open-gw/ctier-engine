"""Living engine docs cite criteria. They do not restate them.

Reference is the choice in every living document: identifier plus what
this engine does. Pinned quotation was not used. The version pin is
engine/docs/SPEC.md; a second copy of the version, or a return of the
known-stale requirement sentences, fails here.
"""
from __future__ import annotations

from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parent
SPEC = ENGINE / "docs" / "SPEC.md"
BASE = "1.15.0"

LIVING = (
    SPEC,
    ENGINE / "docs" / "PRD.md",
    ENGINE / "docs" / "SOLUTION-DESIGN.md",
    ENGINE / "docs" / "DECISIONS.md",
    ENGINE / "docs" / "portability.md",
    ENGINE / "README.md",
    REPO / "README.md",
)

# Sentences that stated a requirement. A correct restatement is still
# a defect; these are the ones this task removed and must not return.
STALE = (
    "The human is never in the request path",
    "before a decision is recorded",
    "Classification precedes routing",
    "Undeclared fails closed",
    "Idempotency keys are derived, not generated",
    "Decisions are recorded before they are acted on",
    "recorded before it is acted upon",
    "Tier 4 has no resume path",
    "Tier 4, no resume path",
    "An injected tier is trusted only from inside the trust boundary",
    "an injected tier is trusted only from inside the boundary",
    "Tier assignment is bound to the deployed interface revision",
    "Tier assignment is bound to the composed interface description",
    "lag behind the deployed interface",
    "No version skew",
    "C12 is scoped to the governed set",
    "What ctier requires of the deployment",
    "without a human ever occupying that path",
    "reachable within a granted scope",
)

# Diagrams are not living law, but they carried declined phrasing.
FIGURES = ENGINE / "docs" / "make_diagrams.py"


def test_conformance_is_stated_by_clause():
    pin = SPEC.read_text(encoding="utf-8")
    assert f"This engine implements specification **{BASE}**." not in pin
    assert f"Base: specification **{BASE}**." in pin
    assert "The claim is the clause list" in pin
    assert "snapshot relative to specification **1.25.0**" in pin
    assert "stale when a new criterion is minted" in pin
    assert "does not claim any later release as a whole" in pin
    assert "| C16 |" in pin
    assert "namespace-unlisted" in pin
    assert "namespace-unknown-audit" in pin
    assert "attempt-record/0.3.0" in pin
    assert "decision-record/0.2.0" in pin
    assert "outcome-record/0.1.0" in pin
    assert "C14" in pin and "**Not implemented.**" in pin
    assert "C15" in pin and "**Partial.**" in pin
    assert "Authorisation-server half" in pin
    assert "`governed-set` is **met.**" in pin
    assert "Kong global instance" in pin
    assert "ctier-generate.json" in pin
    assert "**Built, not titled.**" not in pin
    assert "**Not claimed.**" not in pin
    assert "Requirement 6" in pin
    assert "This engine implements specification **1.21.0**." not in pin
    assert "This engine implements specification **1.22.0**." not in pin
    assert "This engine implements specification **1.25.0**." not in pin
    assert "derived, not generated" not in pin
    assert "recorded before" not in pin
    assert "granted scope" not in pin
    assert "bound to the deployed interface" not in pin
    assert "never past 4" not in pin
    for path in LIVING:
        if path == SPEC:
            continue
        body = path.read_text(encoding="utf-8")
        assert BASE not in body, (
            f"{path.relative_to(REPO)} restates the base; citations resolve through SPEC.md"
        )


def test_living_docs_do_not_restate_known_requirement_sentences():
    for path in LIVING:
        body = path.read_text(encoding="utf-8")
        for phrase in STALE:
            assert phrase not in body, (
                f"{path.relative_to(REPO)} restates {phrase!r}"
            )


def test_figures_do_not_carry_declined_requirement_phrasing():
    body = FIGURES.read_text(encoding="utf-8")
    for phrase in STALE:
        assert phrase not in body, (
            f"make_diagrams.py restates {phrase!r}"
        )
