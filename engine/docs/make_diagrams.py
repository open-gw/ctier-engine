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
fig, ax = newfig('FIG. A1  —  Three phases',
                 'Where design-time declaration becomes runtime enforcement')

for i,(x,t,c) in enumerate([(4,'DESIGN TIME',NAVY),(36,'DEPLOY TIME',NAVY),(68,'RUN TIME',NAVY)]):
    ax.add_patch(Rectangle((x,80),28,5, facecolor=c, edgecolor='none'))
    ax.text(x+14,82.5,t,ha='center',va='center',fontsize=10,fontweight='bold',color='white')

box(ax,4,58,28,18,'OpenAPI document',
    'x-ctier-tier declared per operation\nfive criteria evaluated\nby a human, once',fill='#EFF6FF',edge=BLUE,sfs=7)
box(ax,36,58,28,18,'Gateway configuration',
    'tier compiled into each operation flow\nTier 4 default set in\nthe request pre-flow',fill='#FFFBEB',edge=AMBER,sfs=7)
box(ax,68,58,28,18,'Request in flight',
    'gateway resolves the operation\ninjects the declared tier\nengine escalates on context',fill='#F0FDF4',edge=G,sfs=7)

arrow(ax,32,67,36,67,'generator')
arrow(ax,64,67,68,67,'deploy')

ax.text(50,53,'The declared tier is a floor. Runtime adjustment is unidirectional.',
        ha='center',fontsize=10,fontweight='bold',color=NAVY)

# consequences panel
ax.add_patch(FancyBboxPatch((4,16),92,32,boxstyle='round,pad=0.4,rounding_size=1.2',
                            facecolor='white',edgecolor=NAVY,linewidth=1.2))
ax.text(8,44.5,'Why the assignment is compiled at deploy time',fontsize=10,fontweight='bold',color=NAVY)
items = [
 ('No second router',
  ['The gateway already resolves which operation matched. An engine that re-derived it would be a second routing',
   'implementation capable of silent disagreement. The possibility is removed rather than reduced.']),
 ('One artefact',
  ['The assignment travels in the generated configuration. C12 is governed-set coverage;',
   'binding that assignment to the composition is C13. No separate governance document is loaded at request time.']),
 ('Fail-closed is structural',
  ['An unclassified operation receives no override and inherits Tier 4 — not because a rule enforces it, but because',
   'the absence of a policy produces it. The safe default is the default.']),
]
y=41.0
for bold,lines in items:
    ax.text(8,y,bold,fontsize=8.6,fontweight='bold',color=NAVY)
    y-=3.0
    for l in lines:
        ax.text(8,y,l,fontsize=8.0,color=SLATE)
        y-=2.8
    y-=0.6

ax.text(50,10,'Per-gateway difference lives entirely in the generator. The engine receives a resolved tier '
              'over one uniform interface\nand never learns which gateway called it.',
        ha='center',fontsize=8.6,style='italic',color=MUTED)
pdf.savefig(fig,bbox_inches='tight'); plt.close(fig)

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
print('6 diagram sheets written')
