from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.backends.backend_pdf import PdfPages

plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})

_OUT = Path(__file__).resolve().parent / "architecture-diagrams.pdf"
# 180 mm. The draft's 7.0866 in rounds to 510.2352 pt; the MediaBox is 510.24.
_PAGE_W_IN = 510.24 / 72.0
_A1_H_IN = 7.50

BAND = "#f4f4f4"
TAG = "#e6e6e6"


def _pdf_pages(dest):
    # No author, no path. Library names are omitted too; the page stands alone.
    return PdfPages(str(dest), metadata={
        "Creator": None,
        "Producer": None,
        "Title": None,
        "Author": None,
        "Subject": None,
        "Keywords": None,
    })


# ============================================================ FIG A1
# Both sheets. Every fontsize literal from here to the end of the script
# is >= 8. Fig 2 is the comparison; both of its panels are panel().


def chip(ax, x, y, w, h, label, fs=8):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="black", edgecolor="none", zorder=6))
    ax.text(x + w / 2, y + h / 2, label, color="white", ha="center", va="center",
            fontsize=fs, fontweight="bold", zorder=7)


def _band_rect(ax, y, h, heavy):
    ax.add_patch(Rectangle((2, y), 96, h, facecolor=BAND, edgecolor="black",
                           linewidth=1.9 if heavy else 0.9, zorder=1))


def band_a1(ax, y, h, label, heavy=False):
    # A1 chips are 23 by 3.8. Fig 2's are 22 by 3.6, so they do not share a call.
    _band_rect(ax, y, h, heavy)
    chip(ax, 2, y + h - 3.8, 23, 3.8, label)


def band_fig2(ax, y, h, label, heavy=False, right=None):
    _band_rect(ax, y, h, heavy)
    chip(ax, 2, y + h - 3.6, 22, 3.6, label)
    if right:
        chip(ax, 98 - 37, y + h - 3.6, 37, 3.6, right)


def _box(ax, x, y, w, h, title=None, sub=None, dashed=False, heavy=False, fs=8.5,
         fill="white", lift=1.7, drop=3.4):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor="black",
                           linewidth=1.9 if heavy else 1.0,
                           linestyle=(0, (3, 2)) if dashed else "solid", zorder=5))
    if title:
        ty = y + h / 2 + (lift if sub else 0)
        ax.text(x + w / 2, ty, title, ha="center", va="center", fontsize=fs,
                fontweight="bold", zorder=6)
        if sub:
            ax.text(x + w / 2, ty - drop, sub, ha="center", va="center",
                    fontsize=8, zorder=6)


def box_a1(ax, x, y, w, h, title=None, sub=None, dashed=False, heavy=False,
           fs=8.5, fill="white"):
    # Title sits 1.7 above centre and the subtitle 3.4 below that. Fig 2 is 1.6 / 3.3.
    _box(ax, x, y, w, h, title, sub, dashed, heavy, fs, fill, lift=1.7, drop=3.4)


def box_fig2(ax, x, y, w, h, title=None, sub=None, heavy=False, fs=8.5):
    _box(ax, x, y, w, h, title, sub, False, heavy, fs, "white", lift=1.6, drop=3.3)


def tag(ax, x, y, w, h, label):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.5",
                                facecolor=TAG, edgecolor="black", linewidth=0.8, zorder=5))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=8, zorder=6)


def vline(ax, x, y1, y2, lw=1.2):
    ax.add_line(Line2D([x, x], [y1, y2], color="black", linewidth=lw, zorder=7))


def hline(ax, y, x1, x2, lw=1.2):
    ax.add_line(Line2D([x1, x2], [y, y], color="black", linewidth=lw, zorder=7))


def varrow(ax, x, y1, y2, lw=1.2, dashed=False):
    ax.annotate("", xy=(x, y2), xytext=(x, y1), zorder=8, arrowprops=dict(
        arrowstyle="-|>", color="black", linewidth=lw, mutation_scale=11,
        shrinkA=0, shrinkB=0, linestyle=(0, (3, 2)) if dashed else "solid"))


def harrow(ax, y, x1, x2, lw=1.2):
    ax.annotate("", xy=(x2, y), xytext=(x1, y), zorder=8, arrowprops=dict(
        arrowstyle="-|>", color="black", linewidth=lw, mutation_scale=11,
        shrinkA=0, shrinkB=0))


def _assert_fonts(ax):
    sizes = [t.get_fontsize() for t in ax.texts]
    assert sizes and min(sizes) >= 8, sizes


def newfig(height_in, ylim):
    fig = plt.figure(figsize=(_PAGE_W_IN, height_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, ylim)
    ax.axis("off")
    return fig, ax


def draw_a1(ax):
    # DESIGN TIME
    band_a1(ax, 73, 37, "DESIGN TIME")
    box_a1(ax, 6, 98, 39, 7, "Base interface description", fs=8.5)
    box_a1(ax, 53, 98, 41, 7, "ctier OpenAPI overlay", fs=8.5)
    varrow(ax, 25, 98, 95.4)
    varrow(ax, 73, 98, 95.4)

    box_a1(ax, 5, 75, 90, 20)
    ax.text(50, 91.8, "Composed interface description", ha="center", fontsize=8.5,
            fontweight="bold", zorder=6)
    box_a1(ax, 8, 76.5, 50, 13.5)
    ax.text(33, 87.4, "operation governance attributes", ha="center", fontsize=8, zorder=6)
    tag(ax, 10, 82.2, 22, 4.4, "reversibility")
    tag(ax, 34, 82.2, 22, 4.4, "blast radius")
    tag(ax, 10, 77.4, 22, 4.4, "data sensitivity")
    tag(ax, 34, 77.4, 22, 4.4, "compliance trigger")
    box_a1(ax, 62, 79.5, 30, 7.5, "Declared tier", "per operation", fs=8.5)

    varrow(ax, 33, 75, 63.4)
    ax.text(34.6, 69.4, "computed", ha="left", fontsize=8, zorder=8)
    varrow(ax, 77, 75, 63.4)
    ax.text(78.6, 69.4, "declared", ha="left", fontsize=8, zorder=8)

    # DEPLOYMENT TIME
    band_a1(ax, 28, 40, "DEPLOYMENT TIME")
    box_a1(ax, 18, 52, 64, 11, "Configuration generator",
           "resolved tier  =  max(declared, computed)")
    box_a1(ax, 8, 38, 40, 10, "Complete policy bundle", "generator owns the configuration")
    box_a1(ax, 52, 38, 40, 10, "Mergeable fragments",
           "existing configuration preserved", dashed=True)
    varrow(ax, 28, 52, 48.4)
    varrow(ax, 72, 52, 48.4)
    box_a1(ax, 29, 29, 42, 6.5, "Gateway-native compiled configuration", fs=8.5)
    vline(ax, 28, 38, 36.4)
    vline(ax, 72, 38, 36.4)
    hline(ax, 36.4, 28, 72)
    varrow(ax, 50, 36.4, 35.4)

    # RUN TIME
    band_a1(ax, 2, 23, "RUN TIME", heavy=True)
    box_a1(ax, 5, 11, 18, 7, "AI agent")
    box_a1(ax, 27, 7.5, 49, 15.5, heavy=True)
    chip(ax, 27, 19.2, 23, 3.8, "API GATEWAY")
    box_a1(ax, 30, 11, 25, 7, "Platform policies", "authn · rate limits", fs=8)
    box_a1(ax, 58, 11, 16, 7, "ctier policy", "compiled tier", fs=8, heavy=True)
    box_a1(ax, 82, 11, 15, 7, "Upstream API", fs=8)
    box_a1(ax, 58, 3.6, 16, 3.4, "Request refused", fs=8)
    harrow(ax, 14.5, 23, 26.6)
    harrow(ax, 14.5, 55, 57.6)
    harrow(ax, 14.5, 76, 81.6)
    varrow(ax, 66, 11, 7.4, dashed=True)

    varrow(ax, 66, 29, 18.4, lw=1.8)
    ax.text(64.2, 26.0, "configuration  at deploy", ha="right", fontsize=8,
            fontweight="bold", zorder=8)


def build_a1():
    fig, ax = newfig(_A1_H_IN, 112)
    draw_a1(ax)
    _assert_fonts(ax)
    return fig


PH = 65
GAP = 6
TOT = PH * 2 + GAP
_FIG2_H_IN = TOT * 4.30 / 72.0


def panel(ax, b, variant):
    band_fig2(
        ax, b + 51, 14, "DESIGN TIME",
        right="(a)  AS DESIGNED \u2014 NEVER BUILT" if variant == "a"
        else "(b)  AS BUILT",
    )
    box_fig2(ax, 14, b + 53, 72, 7.5, "Composed interface description",
             "governance attributes  \u00b7  declared tier")

    band_fig2(ax, b + 28, 19, "DEPLOYMENT TIME")
    varrow(ax, 50, b + 51, b + 44.4)
    if variant == "a":
        box_fig2(ax, 18, b + 35, 64, 9, "Configuration generator",
                 "declarations forwarded  \u2014  the engine resolves, per request")
        ax.text(50, b + 31.2, "no resolution at deployment time",
                ha="center", fontsize=8, style="italic", zorder=6)
    else:
        box_fig2(ax, 18, b + 36, 64, 8.5, "Configuration generator",
                 "resolved tier  =  max(declared, computed)")
        box_fig2(ax, 29, b + 29, 42, 5.5, "Gateway-native compiled configuration", fs=8)
        varrow(ax, 50, b + 36, b + 34.9)

    band_fig2(ax, b, 24, "RUN TIME", heavy=True)
    box_fig2(ax, 24, b + 2.5, 48, 11, heavy=True)
    chip(ax, 24, b + 9.9, 21, 3.6, "API GATEWAY")
    box_fig2(ax, 4, b + 4.25, 17, 4.5, "AI agent", fs=8)
    box_fig2(ax, 79, b + 4.25, 17, 4.5, "Upstream API", fs=8)
    harrow(ax, b + 6.5, 21, 23.6)
    harrow(ax, b + 6.5, 72, 78.6)

    if variant == "a":
        box_fig2(ax, 27, b + 4, 24, 5, "Platform policies", "authn \u00b7 rate limits", fs=8)
        box_fig2(ax, 45, b + 16, 32, 6, "Consequence Engine",
                 "resolves the tier on every request", fs=8, heavy=True)
        varrow(ax, 61, b + 28, b + 22.2)
        ax.text(59.2, b + 25.8, "declarations", ha="right", fontsize=8, zorder=8)
        varrow(ax, 53, b + 16, b + 13.7)
        varrow(ax, 63, b + 13.7, b + 16)
        ax.text(66.5, b + 14.6, "per request", ha="left", fontsize=8, style="italic", zorder=8)
    else:
        box_fig2(ax, 27, b + 4, 24, 5, "Platform policies", "authn \u00b7 rate limits", fs=8)
        box_fig2(ax, 53, b + 4, 16, 5, "ctier policy", "compiled tier", fs=8, heavy=True)
        harrow(ax, b + 6.5, 51, 52.6)
        varrow(ax, 61, b + 29, b + 9.7, lw=1.7)
        ax.text(59.2, b + 25.8, "configuration  at deploy", ha="right", fontsize=8,
                fontweight="bold", zorder=8)


def build_fig2():
    fig, ax = newfig(_FIG2_H_IN, TOT)
    panel(ax, PH + GAP, "a")
    panel(ax, 0, "b")
    _assert_fonts(ax)
    return fig


def _save_one(fig, dest, width_in, height_in, mediabox):
    fig.set_size_inches(width_in, height_in)
    dest = Path(dest)
    out = _pdf_pages(dest)
    out.savefig(fig, bbox_inches=None)
    out.close()
    plt.close(fig)
    raw = dest.read_bytes()
    assert raw.count(b"/MediaBox") == 1
    assert mediabox in raw
    return raw


def write_a1_pdf(dest):
    fig = build_a1()
    return _save_one(fig, dest, _PAGE_W_IN, _A1_H_IN, b"/MediaBox [ 0 0 510.24 540 ]")


def write_fig2_pdf(dest):
    fig = build_fig2()
    return _save_one(
        fig, dest, _PAGE_W_IN, _FIG2_H_IN, b"/MediaBox [ 0 0 510.24 584.8 ]")


def write_architecture_pdf(dest=_OUT):
    a1 = build_a1()
    fig2 = build_fig2()
    a1.set_size_inches(_PAGE_W_IN, _A1_H_IN)
    fig2.set_size_inches(_PAGE_W_IN, _FIG2_H_IN)
    dest = Path(dest)
    out = _pdf_pages(dest)
    out.savefig(a1, bbox_inches=None)
    out.savefig(fig2, bbox_inches=None)
    out.close()
    plt.close(a1)
    plt.close(fig2)
    raw = dest.read_bytes()
    assert raw.count(b"/MediaBox") == 2
    assert b"/MediaBox [ 0 0 510.24 540 ]" in raw
    assert b"/MediaBox [ 0 0 510.24 584.8 ]" in raw
    return raw


write_architecture_pdf()
print("2 diagram sheets written")
