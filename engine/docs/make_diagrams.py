from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
from matplotlib.backends.backend_pdf import PdfPages

NAVY='#1E3A5F'; SLATE='#1E293B'; MUTED='#64748B'; RULE='#CBD5E1'
G,Y,O,R = '#16A34A','#D97706','#EA580C','#DC2626'
BLUE='#2563EB'; CARD='#F8FAFC'; AMBER='#B45309'

_OUT = Path(__file__).resolve().parent / 'architecture-diagrams.pdf'
pdf = PdfPages(str(_OUT))

def newfig(title, sub):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis('off')
    ax.text(50, 96, title, ha='center', fontsize=14, fontweight='bold', color=NAVY)
    ax.text(50, 92.3, sub, ha='center', fontsize=9, color=MUTED)
    return fig, ax

def box(ax,x,y,w,h,label,sub=None,fill=CARD,edge=RULE,lw=1.2,fs=9,tc=NAVY,sfs=7.4):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.3,rounding_size=1.0',
                                facecolor=fill, edgecolor=edge, linewidth=lw))
    if sub:
        ax.text(x+w/2, y+h*0.62, label, ha='center', va='center', fontsize=fs,
                fontweight='bold', color=tc)
        for i,l in enumerate(sub.split('\n')):
            ax.text(x+w/2, y+h*0.40-i*2.5, l, ha='center', va='center', fontsize=sfs, color=SLATE)
    else:
        ax.text(x+w/2, y+h/2, label, ha='center', va='center', fontsize=fs,
                fontweight='bold', color=tc)

def arrow(ax,x1,y1,x2,y2,label=None,color=BLUE,style='->',ls='-',fs=7):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2), arrowstyle=style, color=color,
                                 linewidth=1.3, linestyle=ls, mutation_scale=13,
                                 shrinkA=2, shrinkB=2))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2+1.6, label, ha='center', fontsize=fs,
                color=color, style='italic')

# ============================================================ FIG A1
# Page is 180 mm by 4.5 in. Every fontsize literal in this section is >= 8.
# Fig 2, below, is the §5.1 comparison. Panel (b) is this same drawing
# with the classification properties and the emission modes omitted.
_A1_WIDTH_PT = 510.24
_A1_HEIGHT_PT = 324.0
_INK = '#1A1A1A'
# Fig 2 is two stacked panels of 110 mm, a 7 mm gap, and a caption.
# 697.32 pt = 697.32 / 72 * 25.4 mm.
_FIG2_HEIGHT_PT = 697.32
_FIG2_HEIGHT_MM = 697.32 * 25.4 / 72.0
_FIG2_B_BASE = 15.0
_FIG2_PANEL_SPAN = 110.0
_FIG2_PANEL_GAP = 7.0
_FIG2_A_BASE = _FIG2_B_BASE + _FIG2_PANEL_SPAN + _FIG2_PANEL_GAP

_A1_GEOM = {
    'design': (4.0, 84.0, 172.0, 26.5),
    'deploy': (4.0, 32.0, 172.0, 44.0),
    'run': (4.0, 3.2, 172.0, 16.6),
    'tag_x': 6.0,
    'tag_design_y': 103.6,
    'tag_deploy_y': 68.8,
    'tag_run_y': 12.6,
    'cx': 90,
    'title_y': 98.2,
    'declared_y': 93.0,
    'properties_y': 87.6,
    'bundle': (8.0, 46.2, 78.0, 20.4),
    'fragments': (94.0, 46.2, 78.0, 20.4),
    'square': (11.2, 60.2, 2.3, 2.3),
    'diamond': (97.6, 60.15, 2.2, 2.2),
    'bundle_cx': 47,
    'frag_cx': 133,
    'mode_title_y': 61.2,
    'mode_sub_y': 55.4,
    'rule_x0': 12,
    'rule_x1': 168,
    'rule_y': 42.6,
    'resolution_y': 37.6,
    'gen_x1': 47,
    'gen_x2': 133,
    'gen_y1': 83.6,
    'gen_y2': 66.8,
    'cfg_x': 70,
    'cfg_y1': 31.6,
    'cfg_y2': 15.6,
    'cfg_label_x': 76,
    'cfg_label_y1': 27.2,
    'cfg_label_y2': 22.8,
}


def _comparison_geom(base):
    """Band skeleton shared by fig 2 panels (a) and (b). Y grows upward."""
    run_y = base
    deploy_y = base + 52.0
    design_y = base + 88.0
    run_h, deploy_h, design_h = 42.0, 32.0, 22.0
    return {
        'design': (4.0, design_y, 172.0, design_h),
        'deploy': (4.0, deploy_y, 172.0, deploy_h),
        'run': (4.0, run_y, 172.0, run_h),
        'tag_x': 6.0,
        'tag_design_y': design_y + design_h - 6.9,
        'tag_deploy_y': deploy_y + deploy_h - 6.9,
        'tag_run_y': run_y + run_h - 6.9,
        'cx': 90,
        'title_y': design_y + design_h - 6.9 - 6.2,
        'declared_y': design_y + design_h - 6.9 - 11.4,
        'rule_x0': 12,
        'rule_x1': 168,
        'rule_y': deploy_y + 9.2,
        'resolution_y': deploy_y + 4.2,
        'gen_x1': 47,
        'gen_x2': 133,
        'gen_y1': design_y - 0.4,
        'gen_y2': deploy_y + deploy_h - 10.5,
        'cfg_x': 70,
        'cfg_y1': deploy_y - 0.4,
        'cfg_y2': run_y + 18.0,
        'cfg_label_x': 76,
        'cfg_label_y1': deploy_y - 2.8,
        'cfg_label_y2': deploy_y - 6.8,
        'pass_y1': deploy_y + deploy_h - 6.9 - 4.2,
        'pass_y2': deploy_y + deploy_h - 6.9 - 8.6,
        'run_rule_y': run_y + 9.2,
        'run_resolution_y': run_y + 4.2,
        'phrase_y': run_y + 14.6,
        'box_y': run_y + 19.5,
        'box_h': 11.5,
        'round_y_hi': run_y + 28.6,
        'round_y_lo': run_y + 21.6,
        'round_label_y': run_y + 25.1,
        'box_x_l': 10.0,
        'box_x_r': 118.0,
        'box_w': 52.0,
    }


def _band(ax, rect, face, lw):
    ax.add_patch(Rectangle(rect[:2], rect[2], rect[3], facecolor=face,
                           edgecolor=_INK, linewidth=lw, zorder=1))


def _tag(ax, x, y, words):
    ax.add_patch(Rectangle((x, y), 32.0, 5.6, facecolor=_INK, edgecolor=_INK,
                           linewidth=0.6, zorder=3))
    ax.text(x + 16.0, y + 2.8, words, ha='center', va='center', fontsize=8,
            fontweight='bold', color='white', zorder=4)


def _shaft(ax, x1, y1, x2, y2, weight):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>',
                                 mutation_scale=11, linewidth=weight, color=_INK,
                                 shrinkA=0, shrinkB=0, clip_on=False, zorder=5))


def _draw_resolution(ax, x0, x1, y_line, y_text):
    """The block that moves. Same rule, same words, same weight, wherever it sits."""
    ax.plot([x0, x1], [y_line, y_line], color=_INK, linewidth=0.6,
            solid_capstyle='butt', zorder=2)
    ax.text((x0 + x1) / 2.0, y_text, 'resolution    max(declared, computed)',
            ha='center', va='center', fontsize=8, fontweight='bold', color=_INK,
            zorder=4)


def _draw_bands_and_tags(ax, g):
    # Run time is the heavy frame. Design is the light one. Deploy sits between.
    _band(ax, g['design'], '#F7F7F7', 0.8)
    _band(ax, g['deploy'], 'white', 1.15)
    _band(ax, g['run'], '#F3F3F3', 2.0)
    _tag(ax, g['tag_x'], g['tag_design_y'], 'DESIGN TIME')
    _tag(ax, g['tag_x'], g['tag_deploy_y'], 'DEPLOY TIME')
    _tag(ax, g['tag_x'], g['tag_run_y'], 'RUN TIME')


def _draw_design_heading(ax, g, properties):
    ax.text(g['cx'], g['title_y'], 'Composed interface description',
            ha='center', va='center', fontsize=9, fontweight='bold', color=_INK,
            zorder=4)
    ax.text(g['cx'], g['declared_y'], 'declared tiers',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    if properties:
        ax.text(g['cx'], g['properties_y'],
                'reversibility    blast radius    data sensitivity    compliance trigger',
                ha='center', va='center', fontsize=8, color=_INK, zorder=4)


def _draw_emission_modes(ax, g):
    bundle, fragments = g['bundle'], g['fragments']
    ax.add_patch(Rectangle(bundle[:2], bundle[2], bundle[3], facecolor='white',
                           edgecolor=_INK, linewidth=1.7, linestyle='solid', zorder=2))
    ax.add_patch(Rectangle(fragments[:2], fragments[2], fragments[3], facecolor='white',
                           edgecolor=_INK, linewidth=1.15, linestyle=(0, (2.4, 1.3)),
                           zorder=2))
    # Shape channel: filled square on the bundle, open diamond on the fragments.
    sx, sy, sw, sh = g['square']
    ax.add_patch(Rectangle((sx, sy), sw, sh, facecolor=_INK, edgecolor=_INK,
                           linewidth=0.4, zorder=3))
    dx, dy, dw, dh = g['diamond']
    ax.add_patch(Rectangle((dx, dy), dw, dh, angle=45, rotation_point='center',
                           facecolor='none', edgecolor=_INK, linewidth=1.0, zorder=3))
    ax.text(g['bundle_cx'], g['mode_title_y'], 'Complete policy bundle',
            ha='center', va='center', fontsize=8, fontweight='bold', color=_INK, zorder=4)
    ax.text(g['bundle_cx'], g['mode_sub_y'], 'generator owns the gateway configuration',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    ax.text(g['frag_cx'], g['mode_title_y'], 'Mergeable fragments',
            ha='center', va='center', fontsize=8, fontweight='bold', color=_INK, zorder=4)
    ax.text(g['frag_cx'], g['mode_sub_y'], 'existing estate the generator must not replace',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)


def _draw_generator_arrows(ax, g):
    # They stop in deploy time. On Figure 1 that is the top of each emission box.
    _shaft(ax, g['gen_x1'], g['gen_y1'], g['gen_x1'], g['gen_y2'], 0.9)
    _shaft(ax, g['gen_x2'], g['gen_y1'], g['gen_x2'], g['gen_y2'], 0.9)


def _draw_config_arrow(ax, g):
    # The only arrow that enters run time on the implemented architecture.
    _shaft(ax, g['cfg_x'], g['cfg_y1'], g['cfg_x'], g['cfg_y2'], 1.9)
    ax.text(g['cfg_label_x'], g['cfg_label_y1'], 'configuration',
            ha='left', va='center', fontsize=8, color=_INK, zorder=4)
    ax.text(g['cfg_label_x'], g['cfg_label_y2'], 'at deploy',
            ha='left', va='center', fontsize=8, fontweight='bold', color=_INK, zorder=4)


def draw_implemented_architecture(ax, g, *, properties, emission_modes):
    """Figure 1. properties and emission_modes are the only omissions fig 2 makes."""
    _draw_bands_and_tags(ax, g)
    _draw_design_heading(ax, g, properties)
    if emission_modes:
        _draw_emission_modes(ax, g)
    _draw_resolution(ax, g['rule_x0'], g['rule_x1'], g['rule_y'], g['resolution_y'])
    # Generator arrows are not the emission boxes. They still stop in deploy time.
    _draw_generator_arrows(ax, g)
    _draw_config_arrow(ax, g)


def draw_specified_request_path(ax, g):
    """Panel (a). Classification is a run-time round trip. Deploy does not resolve."""
    _draw_bands_and_tags(ax, g)
    _draw_design_heading(ax, g, properties=False)
    ax.text(g['cx'], g['pass_y1'], 'generator passes declarations through',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    ax.text(g['cx'], g['pass_y2'], 'it does not resolve',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    box_y, box_h, box_w = g['box_y'], g['box_h'], g['box_w']
    left, right = g['box_x_l'], g['box_x_r']
    for x, label in ((left, 'Gateway'), (right, 'Consequence Engine')):
        ax.add_patch(Rectangle((x, box_y), box_w, box_h, facecolor='white',
                               edgecolor=_INK, linewidth=1.4, linestyle='solid', zorder=2))
        ax.text(x + box_w / 2.0, box_y + box_h / 2.0, label,
                ha='center', va='center', fontsize=8, fontweight='bold', color=_INK,
                zorder=4)
    # Out to the engine, back with a disposition, before the request is forwarded.
    _shaft(ax, left + box_w + 1.5, g['round_y_hi'], right - 1.5, g['round_y_hi'], 1.6)
    _shaft(ax, right - 1.5, g['round_y_lo'], left + box_w + 1.5, g['round_y_lo'], 1.6)
    ax.text(g['cx'], g['round_label_y'], 'disposition',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    ax.text(g['cx'], g['phrase_y'], 'before the request is forwarded',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    _draw_resolution(ax, g['rule_x0'], g['rule_x1'], g['run_rule_y'], g['run_resolution_y'])


def _panel_label(ax, g, words):
    design = g['design']
    ax.text(design[0] + design[2] - 2.2, design[1] + design[3] - 3.4, words,
            ha='right', va='center', fontsize=9, fontweight='bold', color=_INK, zorder=4)


def _blank_figure(width_pt, height_pt, height_mm):
    fig, ax = plt.subplots(figsize=(width_pt / 72.0, height_pt / 72.0))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, 180)
    ax.set_ylim(0, height_mm)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    return fig, ax


def _assert_fonts(ax):
    sizes = [t.get_fontsize() for t in ax.texts]
    assert sizes and min(sizes) >= 8, sizes


def _arrow_ends(patch):
    (x1, y1), (x2, y2) = patch._posA_posB
    return x1, y1, x2, y2


def _inside(rect, x, y):
    return rect[0] < x < rect[0] + rect[2] and rect[1] < y < rect[1] + rect[3]


def _count_crossing(arrows, rect):
    entering = leaving = 0
    for patch in arrows:
        x1, y1, x2, y2 = _arrow_ends(patch)
        head_in, tail_in = _inside(rect, x2, y2), _inside(rect, x1, y1)
        if head_in and not tail_in:
            entering += 1
        if tail_in and not head_in:
            leaving += 1
    return entering, leaving


def build_a1():
    fig, ax = _blank_figure(_A1_WIDTH_PT, _A1_HEIGHT_PT, 114.3)
    draw_implemented_architecture(ax, _A1_GEOM, properties=True, emission_modes=True)
    _assert_fonts(ax)
    run = _A1_GEOM['run']
    arrows = [p for p in ax.patches if isinstance(p, FancyArrowPatch)]
    assert len(arrows) == 3, len(arrows)
    entering, leaving = _count_crossing(arrows, run)
    assert entering == 1 and leaving == 0, (entering, leaving)
    return fig


def _pdf_pages(dest):
    # No author, no path. Library names are omitted too; the page stands alone.
    return PdfPages(str(dest), metadata={
        'Creator': None,
        'Producer': None,
        'Title': None,
        'Author': None,
        'Subject': None,
        'Keywords': None,
    })


def write_a1_pdf(dest):
    fig = build_a1()
    # 510.24 pt is 180 mm. figsize is that width over 72, not a tight crop.
    fig.set_size_inches(_A1_WIDTH_PT / 72.0, _A1_HEIGHT_PT / 72.0)
    dest = Path(dest)
    out = _pdf_pages(dest)
    out.savefig(fig, bbox_inches=None)
    out.close()
    plt.close(fig)
    raw = dest.read_bytes()
    assert raw.count(b'/MediaBox') == 1
    assert b'/MediaBox [ 0 0 510.24 324 ]' in raw


def build_fig2():
    fig, ax = _blank_figure(_A1_WIDTH_PT, _FIG2_HEIGHT_PT, _FIG2_HEIGHT_MM)
    specified = _comparison_geom(_FIG2_A_BASE)
    built = _comparison_geom(_FIG2_B_BASE)
    draw_specified_request_path(ax, specified)
    # Panel (b) is Figure 1 from the same function. Two flags are the whole reduction.
    draw_implemented_architecture(ax, built, properties=False, emission_modes=False)
    _panel_label(ax, specified, '(a)')
    _panel_label(ax, built, '(b)')
    ax.text(90, 9.4, 'Panel (b) reproduces Figure 1 without the classification properties',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    ax.text(90, 5.2, 'and the emission modes, which are unchanged by the revision.',
            ha='center', va='center', fontsize=8, color=_INK, zorder=4)
    _assert_fonts(ax)
    arrows = [p for p in ax.patches if isinstance(p, FancyArrowPatch)]
    # (a) round trip is two arrows inside run time. (b) keeps the two generator
    # arrows and the one arrow into run time. Nothing leaves run time.
    assert len(arrows) == 5, len(arrows)
    a_enter, a_leave = _count_crossing(arrows, specified['run'])
    b_enter, b_leave = _count_crossing(arrows, built['run'])
    assert a_enter == 0 and a_leave == 0, (a_enter, a_leave)
    assert b_enter == 1 and b_leave == 0, (b_enter, b_leave)
    inside_a = []
    for patch in arrows:
        x1, y1, x2, y2 = _arrow_ends(patch)
        if _inside(specified['run'], x1, y1) and _inside(specified['run'], x2, y2):
            inside_a.append((x1, x2, y1, y2))
    assert len(inside_a) == 2, inside_a
    directions = {x2 > x1 for x1, x2, y1, y2 in inside_a}
    assert directions == {True, False}, inside_a
    blob = '\n'.join(t.get_text() for t in ax.texts)
    assert blob.count('resolution    max(declared, computed)') == 2
    assert 'reversibility' not in blob
    assert 'Complete policy bundle' not in blob
    assert 'Mergeable fragments' not in blob
    assert '(a)' in blob and '(b)' in blob
    assert 'disposition' in blob
    assert 'configuration' in blob and 'at deploy' in blob
    assert 'Panel (b) reproduces Figure 1' in blob
    resolution_ys = [t.get_position()[1] for t in ax.texts
                     if t.get_text() == 'resolution    max(declared, computed)']
    assert len(resolution_ys) == 2
    a_run, b_deploy = specified['run'], built['deploy']
    assert any(_inside(a_run, 90, y) for y in resolution_ys)
    assert any(_inside(b_deploy, 90, y) for y in resolution_ys)
    assert not any(_inside(specified['deploy'], 90, y) for y in resolution_ys)
    return fig


def write_fig2_pdf(dest):
    fig = build_fig2()
    fig.set_size_inches(_A1_WIDTH_PT / 72.0, _FIG2_HEIGHT_PT / 72.0)
    dest = Path(dest)
    out = _pdf_pages(dest)
    out.savefig(fig, bbox_inches=None)
    out.close()
    plt.close(fig)
    raw = dest.read_bytes()
    assert raw.count(b'/MediaBox') == 1
    assert b'/MediaBox [ 0 0 510.24 697.32 ]' in raw
    return raw

fig = build_a1()
pdf.savefig(fig, bbox_inches=None)
plt.close(fig)

fig = build_fig2()
pdf.savefig(fig, bbox_inches=None)
plt.close(fig)

# ============================================================ FIG A2
fig, ax = newfig('FIG. A2  —  Apigee policy execution order',
                 'How the declared tier is injected, and why unclassified operations fail closed')

lanes = [('ProxyEndpoint PreFlow', 72, '#EFF6FF', BLUE),
         ('Conditional flow  (router-matched)', 52, '#FFFBEB', AMBER),
         ('After the flow', 32, '#F5F3FF', '#7C3AED'),
         ('TargetEndpoint', 14, '#F0FDF4', G)]
for label,y,fill,edge in lanes:
    ax.add_patch(Rectangle((4,y),18,14, facecolor=edge, edgecolor='none'))
    for i,l in enumerate(label.split('  ')):
        ax.text(13,y+8-i*3.4,l,ha='center',va='center',fontsize=7.6,
                fontweight='bold',color='white')
    ax.add_patch(Rectangle((22,y),74,14, facecolor=fill, edgecolor=RULE, linewidth=0.8))

box(ax,24,74,20,10,'1  SC-Strip','remove inbound\nx-ctier-* headers',fill='white',edge=R,sfs=7)
box(ax,47,74,20,10,'2  AM-Default','ctier.tier = 4\nctier.declared = false',fill='white',edge=NAVY,sfs=7)
ax.text(70,79,'unconditional — runs for every request',fontsize=7.6,style='italic',color=MUTED)

box(ax,24,54,30,10,'3  AM-Tier-<operationId>',
    'ctier.tier = <declared>   ctier.declared = true\nctier.operationId = <operationId>',
    fill='white',edge=AMBER,sfs=7)
ax.text(57,59,'executes ONLY where an operation was declared.',fontsize=7.8,color=AMBER,fontweight='bold')
ax.text(57,56,'No declaration → no override → the Tier 4 default stands.',fontsize=7.6,style='italic',color=MUTED)

box(ax,24,34,20,10,'4  SC-Engine','POST /v1/authorize\nreturns disposition',fill='white',edge='#7C3AED',sfs=7)
box(ax,47,34,15,10,'5  RF-Withhold','202 · non-retryable',fill='white',edge=O,sfs=6.6)
box(ax,64,34,15,10,'6  RF-Suspend','423 · no resume',fill='white',edge=R,sfs=6.6)
box(ax,81,34,14,10,'7  RF-Provision','403 · defect',fill='white',edge=MUTED,sfs=6.6)

box(ax,24,16,30,10,'8  Route to target',
    'reached only when disposition = execute',fill='white',edge=G,sfs=7)

arrow(ax,44,79,47,79,None)
arrow(ax,34,74,34,64,None)
arrow(ax,39,54,39,44,None)
arrow(ax,44,39,47,39,None)
arrow(ax,34,34,34,26,None)

ax.text(50,7.5,'Apigee has no native ext_authz equivalent; ServiceCallout executes in the request path and populates '
               'flow variables that\nsubsequent conditional policies branch on. On callout timeout the proxy fails closed.',
        ha='center',fontsize=8,style='italic',color=MUTED)
pdf.savefig(fig,bbox_inches='tight'); plt.close(fig)

# ============================================================ FIG A3
fig, ax = newfig('FIG. A3  —  Trust boundary',
                 'A tier asserted by the caller is never honoured')

ax.plot([50,50],[18,80], color=R, linewidth=2, linestyle='--')
ax.text(27,82,'UNTRUSTED',ha='center',fontsize=11,fontweight='bold',color=R)
ax.text(75,82,'TRUSTED',ha='center',fontsize=11,fontweight='bold',color=G)

box(ax,6,58,30,14,'Autonomous agent',
    'may assert anything\nin headers and body',fill='#FEF2F2',edge=R)
box(ax,58,58,34,14,'Gateway',
    'strips inbound x-ctier-*\nsets ctier.* from proxy config',fill='#F0FDF4',edge=G)
box(ax,58,34,34,14,'Consequence Engine',
    'trusts proxy-set values only\nescalates on shared state',fill='#F0FDF4',edge=G)

arrow(ax,36,65,58,65,'request',color=R)
arrow(ax,75,58,75,48,'declared tier + context')

ax.add_patch(FancyBboxPatch((6,30),44,18,boxstyle='round,pad=0.4,rounding_size=1.0',
                            facecolor='#FEF2F2',edgecolor=R,linewidth=1.2))
ax.text(28,44.5,'The attack this closes',ha='center',fontsize=9.5,fontweight='bold',color=R)
ax.text(28,40.5,'Without the strip, an agent sends',ha='center',fontsize=8,color=SLATE)
ax.text(28,37.5,'x-ctier-tier: 1',ha='center',fontsize=9,fontweight='bold',color=R,family='monospace')
ax.text(28,34,'and governs itself. The model collapses.',ha='center',fontsize=8,color=SLATE)

ax.add_patch(FancyBboxPatch((6,8),86,15,boxstyle='round,pad=0.4,rounding_size=1.0',
                            facecolor=CARD,edgecolor=NAVY,linewidth=1.2))
ax.text(50,19,'C11 — the agent does not choose its tier',
        ha='center',fontsize=9.5,fontweight='bold',color=NAVY)
ax.text(50,14.5,'This engine strips inbound x-ctier-* at the edge before setting its own. Classification does not',
        ha='center',fontsize=8,color=SLATE)
ax.text(50,11.5,'read an inbound tier. Bundle mode owns that order; fragment mode is bounded per target.',
        ha='center',fontsize=8,color=SLATE)
pdf.savefig(fig,bbox_inches='tight'); plt.close(fig)

# ============================================================ FIG A4
fig, ax = newfig('FIG. A4  —  Tier 3, out-of-band approval',
                 'No component blocks on human input')

actors = [('Agent',10),('Gateway',30),('Engine',50),('Orchestration',70),('Human',90)]
for name,x in actors:
    ax.add_patch(Rectangle((x-8,82),16,5,facecolor=NAVY,edgecolor='none'))
    ax.text(x,84.5,name,ha='center',va='center',fontsize=8.5,fontweight='bold',color='white')
    ax.plot([x,x],[20,82],color=RULE,linewidth=1)

def step(y,x1,x2,label,color=BLUE,ls='-'):
    arrow(ax,x1,y,x2,y,None,color=color,ls=ls)
    ax.text((x1+x2)/2,y+1.6,label,ha='center',fontsize=7.2,color=color,style='italic')

step(76,10,30,'PUT /customers/{id}/profile')
step(71,30,50,'authorize (tier 3 declared)')
ax.text(51,67.5,'persist execution context + derived idempotency key',fontsize=7.2,color=MUTED,style='italic',ha='left')
step(63,50,70,'approval event')
step(57,70,90,'notify in existing tooling')
step(52,50,30,'disposition: withhold',color=O)
step(47,30,10,'202  non-retryable  X-Agent-Action',color=O)

ax.add_patch(Rectangle((6,33),88,10,facecolor='#F0FDF4',edgecolor=G,linewidth=1))
ax.text(50,40,'connection released — no gateway worker, connection-pool slot or client timeout consumed',
        ha='center',fontsize=8.4,fontweight='bold',color=G)
ax.text(50,36,'the agent continues with the rest of the task while the human decides on human timescales',
        ha='center',fontsize=7.8,color=SLATE)

step(29,90,70,'approve',color=G)
step(25,70,50,'decision',color=G)
ax.text(50,21.5,'execute FROM PERSISTED CONTEXT — the agent does not resubmit',
        fontsize=7.6,fontweight='bold',color=G,style='italic',ha='center')

ax.text(50,13,'The operation executed is byte-identical to the operation described in the event the reviewer decided upon.',
        ha='center',fontsize=8.4,fontweight='bold',color=NAVY)
ax.text(50,9.5,'An agent employing a planning model may reach a different formulation between the withholding and the release;\n'
               'resubmission would mean one payload was approved and another executed.',
        ha='center',fontsize=7.8,color=MUTED)
pdf.savefig(fig,bbox_inches='tight'); plt.close(fig)

# ============================================================ FIG A5
fig, ax = newfig('FIG. A5  —  Tier 4, no execute under the agent',
                 'C9 — the agent is removed from the path; a human performs the action')

actors = [('Agent',12),('Gateway',35),('Engine',58),('Human — own tooling',85)]
for name,x in actors:
    w = 26 if 'own' in name else 16
    ax.add_patch(Rectangle((x-w/2,82),w,5,facecolor=R if 'Human' not in name else NAVY,edgecolor='none'))
    ax.text(x,84.5,name,ha='center',va='center',fontsize=8.5,fontweight='bold',color='white')
    ax.plot([x,x],[24,82],color=RULE,linewidth=1)

def step2(y,x1,x2,label,color=R):
    arrow(ax,x1,y,x2,y,None,color=color)
    ax.text((x1+x2)/2,y+1.6,label,ha='center',fontsize=7.2,color=color,style='italic')

step2(76,12,35,'POST /payments')
step2(71,35,58,'authorize (tier 4 declared)')
ax.text(58,67,'incident written at ATTEMPT, not at decision',fontsize=7.4,fontweight='bold',color=R,style='italic',ha='left')
ax.text(58,64,'agent suspended for the operation class; permissions revoked; context frozen',
        fontsize=7.2,color=MUTED,style='italic',ha='left')
step2(58,58,85,'incident + reasoning trace + delegation chain')
step2(53,58,35,'disposition: refuse')
step2(48,35,12,'423  autoResume: false')

ax.add_patch(Rectangle((6,33),88,11,facecolor='#FEF2F2',edgecolor=R,linewidth=1))
ax.text(50,40.5,'nothing is pending — there is no correlation identifier and nothing to poll for',
        ha='center',fontsize=8.4,fontweight='bold',color=R)
ax.text(50,36.5,'the agent must not seek an alternative route to the same outcome; that attempt is itself a recorded incident',
        ha='center',fontsize=7.6,color=SLATE)

ax.add_patch(FancyBboxPatch((50,24),44,7,boxstyle='round,pad=0.3,rounding_size=0.8',
                            facecolor='#F0FDF4',edgecolor=G,linewidth=1.2))
ax.text(72,27.5,'the human performs it under their own credential',
        ha='center',fontsize=8,fontweight='bold',color=G)

ax.text(50,17,'No state transition exists by which a Tier 4 operation enters an executing state under the agent\'s identity.',
        ha='center',fontsize=8.8,fontweight='bold',color=NAVY)
ax.text(50,13,'An agent repeatedly attempting a Tier 4 operation is a recorded signal even though nothing executed.',
        ha='center',fontsize=8,style='italic',color=MUTED)
pdf.savefig(fig,bbox_inches='tight'); plt.close(fig)

# ============================================================ FIG A6
fig, ax = newfig('FIG. A6  —  Deployment topology',
                 'The engine is stateless; the generator runs in CI and produces a versioned artifact')

box(ax,26,80,48,10,'CI / CD pipeline',
    'openapi.yaml  →  generator  →  proxy bundle (versioned)',fill='#EFF6FF',edge=BLUE,fs=10)
arrow(ax,50,80,50,72,'deploy')

box(ax,4,58,20,12,'Agent',None,fill=CARD,edge=MUTED)
box(ax,30,58,40,12,'Gateway  (Apigee)',
    'strips client tier · defaults to 4 · injects declared tier',fill='#FFFBEB',edge=AMBER,fs=10)
box(ax,76,58,20,12,'Backend',None,fill=CARD,edge=MUTED)
arrow(ax,24,64,30,64)
arrow(ax,70,64,76,64,'execute only',color=G)

arrow(ax,50,58,50,48,'authorize')
box(ax,30,36,40,12,'Consequence Engine',
    'stateless · escalate · decide · record',fill='#F0FDF4',edge=G,fs=10)

box(ax,8,16,26,12,'Context store',
    'withheld operations\nderived idempotency keys',fill=CARD,edge=RULE)
box(ax,38,16,24,12,'Ledger',
    'append-only\ndeclared vs applied',fill=CARD,edge=RULE)
box(ax,66,16,28,12,'Orchestration',
    'approval events →\nreviewer\'s own tooling',fill=CARD,edge=RULE)

arrow(ax,42,36,26,28); arrow(ax,50,36,50,28); arrow(ax,58,36,74,28)

ax.text(50,9,'All vendor-specific work is in the generator. Swapping Apigee for Envoy, Kong or APIM changes the generator target only —\n'
             'the engine, the contracts and the conformance requirements are unchanged.',
        ha='center',fontsize=8.4,style='italic',color=MUTED)
pdf.savefig(fig,bbox_inches='tight'); plt.close(fig)

pdf.close()
print('7 diagram sheets written')
