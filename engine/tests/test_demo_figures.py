"""Every figure the demo prints is classified in measurements.md."""
from __future__ import annotations

from pathlib import Path

from ctier.demo import FIGURES

MEASUREMENTS = Path(__file__).resolve().parents[1] / "docs" / "measurements.md"


def test_demo_figures_are_in_measurements_with_their_kind():
    text = MEASUREMENTS.read_text(encoding="utf-8")
    configured, rest = text.split("## Derived", 1)
    derived, observed = rest.split("## Observed", 1)
    sections = {"Configured": configured, "Derived": derived, "Observed": observed}
    for name, value, kind in FIGURES:
        blob = sections[kind]
        words = [w for w in name.replace("—", " ").split() if len(w) > 3]
        assert any(w.lower() in blob.lower() for w in words), (name, kind)
        if "1000 ms" in value:
            assert "1000 ms" in blob
        if value == "10" or name.endswith("min sample"):
            assert "**10**" in blob
        if value == "2":
            assert "**2**" in blob
        if "30 s" in value:
            assert "**30 s**" in blob
        if "200 ms" in value:
            assert "**200 ms**" in blob
        if "5 s" in value:
            assert "**5 s**" in blob
        if "14 days" in value:
            assert "**14 days**" in blob


def test_demo_names_the_derived_bound_and_refuses_the_observed_sample_as_the_bound():
    demo = (Path(__file__).resolve().parents[1] / "ctier" / "demo.py").read_text(
        encoding="utf-8"
    )
    assert "one poll interval" in demo
    assert "Not the 216 ms Observed sample" in demo
