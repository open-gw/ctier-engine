"""A1's drawing code stays at or above 8 pt.

The check reads the FIG A1 section of make_diagrams.py. A2–A6 are
outside that section and are not scanned.
"""
from __future__ import annotations

import re
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
SCRIPT = ENGINE / "docs" / "make_diagrams.py"
START = "# ============================================================ FIG A1\n"
END = "# ============================================================ FIG A2\n"

# fontsize= and the helper keywords A1 must not inherit from box() / arrow().
_SIZE = re.compile(
    r"(?:fontsize|(?<![\w])fs|(?<![\w])sfs)\s*=\s*([0-9]+(?:\.[0-9]+)?)"
)


def test_a1_drawing_code_font_size_is_at_least_8pt():
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index(START)
    end = text.index(END, start)
    section = text[start:end]
    assert "def build_a1(" in section
    sizes = [float(value) for value in _SIZE.findall(section)]
    assert sizes, "A1 drawing code sets no font size"
    below = [size for size in sizes if size < 8]
    assert not below, below
    assert min(sizes) >= 8
