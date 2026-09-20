# ctier-engine — decision record for the §8 open questions

Status: proposed, pending your acceptance. Dated 5 September 2026.
Intended home: `docs/DECISIONS.md`, committed before the generator is written.

Each item states a recommendation, the reasoning, and — where relevant — what it
changes in `docs/PRD.md` or in the generator's input contract.

Verified against the current published specifications while writing this:
Overlay is at **v1.1.0** (14 Jan 2026), not 1.0.0; targets are **RFC 9535**
JSONPath and `copy` was added in 1.1.0. The Namespace Registry currently holds
eight namespaces — `fdx`, `jsonschema`, `ms`, `oai`, `oas-draft`, `oas`, `sap`,
`scalar` — and **`ctier` is free**. `x-agent-trust` is in the Extensions
Registry, registered *unnamespaced*; so is `x-sensitive-data`, which is closer
to your territory than the name suggests.

---

## Q1 — Overlays as the delivery mechanism for tier assignments

**Recommendation: adopt, but as a superset rather than a replacement. Do it now,
because it changes the generator's input contract and the generator is the next
thing written.**

The generator's signature becomes:

```
generate(description, *overlays) -> bundle
```

Zero overlays reproduces today's behaviour exactly — tiers read from inline
`x-ctier-*` in the description. One or more overlays are applied in order (RFC
9535 JSONPath targets, `update` merge), and tiers are read from the **composed**
document. Inline declaration is then just the degenerate case of composition
with an empty overlay set, so nothing in the existing PRD is contradicted; it is
generalised.

Why it is worth doing rather than merely possible:

- It matches how the ownership actually splits in an organisation large enough
  to need this. The API team owns the interface; the governance team owns what
  the interface is allowed to cost. Two owners, two review paths, two audit
  trails. Putting the tier inline forces the governance decision through the API
  team's pull request, where it is reviewed by people whose job is not that.
- Overlay `update` is an object merge, so adding `x-ctier-*` to an operation is
  a clean, non-destructive action. This is a good fit, not a workaround.
- Targeting by `operationId` works — `$.paths[*][?@.operationId == 'cancelOrder']`
  — which means an overlay survives path restructuring. That is the *same*
  stability argument this engine later used when deriving keys from
  `operationId` (this engine's mechanism for C7). The consistency is worth
  having.

**The failure mode you must design against, and it is not a small one.** Split
ownership means adding an operation becomes a two-team change. In practice the
API team ships and the governance overlay lags. Fail-closed then makes the new
operation Tier 4, agents get suspended against it, and the organisational
pressure is immediately to add a blanket action to the overlay — *"everything
under `/v2` is Tier 2"* — which destroys the model in one line while looking
like an operational fix. This is the single most likely way ctier dies in
production, and it is created by the overlay approach, not by the current one.

So the adoption comes with a guard the generator enforces:

> **An overlay action whose `update` assigns a tier of 1, 2 or 3 MUST select
> exactly one operation. An action may select many operations only when it
> assigns Tier 4.**

Raising many operations to the safe floor at once is never the dangerous
direction; lowering many at once always is. That asymmetry is enforceable in
about fifteen lines of generator code and it is what makes separated ownership
safe rather than merely tidy.

Changes:

- **PRD** — restate declaration as "declared in the composed interface
  description", and add the single-target rule above as a normative MUST.
- **Generator contract** — accepts N overlay documents; applies in order; emits
  a composition manifest.
- **Proposed criterion C13.** This record proposed a thirteenth letter. The
  specification minted it. This engine emits `compositionDigest` and
  `deploymentDigest` on the artefact and on decision records. The letter
  is not minted here. See [`SPEC.md`](SPEC.md).

---

## Q2 — The generator run against a spec from which the overlay has stripped `x-ctier-*`

**Recommendation: resolved by Q1's manifest plus a coverage gate. Fail closed at
runtime; fail *loud* at deploy. These are not in tension — one is the safety
net, the other is the CI gate.**

The generator emits, alongside the bundle, a coverage report: N operations in
the composed description, M carrying a tier, and the list of the N−M that do
not. It exits non-zero when M < N unless `--allow-unclassified` is passed
explicitly.

This means the silent-Tier-4-everywhere scenario cannot reach production without
somebody typing a flag whose name says what they are doing. The runtime property
is unchanged: an unclassified operation still inherits Tier 4 from the absence
of a policy. The deploy-time behaviour changes from "works, then nothing works"
to "refuses to ship."

Add to the PRD, close to the fail-closed statement:

> The generator's input is the authoritative source composition, never a
> published or filtered rendering of it. A rendering from which governance
> metadata has been removed produces a bundle in which every operation is Tier
> 4 — safe, but non-functional. The coverage report exists so that this is
> caught at deploy time rather than in production.

---

## Q3 — Arazzo and workflow-level consequence

**Recommendation: do not build it for v1. Record the design position now,
because the position is the valuable part and it is cheap to get wrong later.**

Two things to fix in writing before this is discussed with anyone:

**A declared workflow's tier is a floor for its steps, never a ceiling.** The
temptation with Arazzo is to say "this workflow is approved as Tier 3, therefore
its steps execute" — and that is tier laundering with a specification file
attached, which is precisely what the accumulator exists to prevent. Keep the
same unidirectionality the operation case already has: a workflow declared Tier
3 raises every step's floor to Tier 3 and can never lower a Tier 4 step. Under
that rule Arazzo is purely additive and cannot weaken the model. Under any other
rule it is a hole.

**The more interesting use is deviation, not assignment.** Runtime accumulation
detects decomposition by watching consequence pile up in a correlation scope
with no declared shape. An Arazzo workflow gives that scope a *declared* shape
— a known step set, a known order, a known beginning and end. That makes a
second, distinct signal available: the agent is executing operations outside the
declared workflow while claiming that workflow's correlation scope. That is not
accumulation and it is not delegation-chain failure; it is a third escalation
trigger.

Changes:

- **PRD** — one paragraph under future work stating the floor-not-ceiling rule,
  so that nobody implements it the other way in your absence.

---

## Q4 — `compute_tier` ordering, and a probable bug

**Recommendation: keep blast radius above data sensitivity, but re-derive the
ordering from reversibility rather than asserting it — and fix what I think is a
real hole in the read path.**

The five criteria are not peers, and treating them as a flat precedence list is
what makes the ordering feel arbitrary. Reversibility is the axis the tiers are
*defined* on: the tier table in §2 of the handover literally reads T2 = undo
restores effect, T3 = undo restores record only, T4 = no undo. The other four
criteria are escalators — they raise a tier that reversibility would otherwise
set.

That gives blast radius its real justification, which is stronger than
precedence: **a system-wide write collapses reversibility to `record-only` by
construction.** The population affected in the interval is unbounded, so you
cannot recall what they did with the state while it stood. The feature-flag case
is not "blast radius outranks sensitivity"; it is "system-wide scope means the
undo cannot restore the effect, whatever the data was." Record it that way in
the PRD and the ordering stops looking like a preference.

**Now the hole.** Consider a read: `blast_radius = system`,
`sensitivity = restricted`, no compliance trigger — a bulk export of every
customer record in a system where that data is classified restricted rather than
regulated. If the system-wide rule is conditioned on the operation being a
write, and the sensitivity rule is conditioned on the operation being a write,
this falls through to "read-only, no compliance surface" and classifies **Tier
1**. Logged, not gated. That is wrong, and it is wrong in the most quotable
possible way for anyone attacking the model.

The reason it slips through is that reversibility does not describe disclosure.
You cannot un-disclose. So the rule set needs one more clause that applies to
reads:

| # | Condition | Tier |
|---|---|---|
| 1 | `reversibility == none` | 4 |
| 2 | compliance trigger present and `reversibility != full` | 3, or 4 if blast radius is system-wide |
| 3 | `blast_radius == system` and the operation writes | 4 |
| **3b** | **`blast_radius in (segment, system)` and `sensitivity in (restricted, regulated)` — reads included** | **3** |
| 4 | `sensitivity in (restricted, regulated)` and the operation writes | 3 |
| 5 | `reversibility == record-only` | 3 |
| 6 | `reversibility == effect` | 2 |
| 7 | read-only, no compliance surface | 1 |

Two tests to add, both of which I would expect to fail today:

- system-wide read, restricted data, no compliance trigger → expect Tier 3
- segment-wide read, regulated data → expect Tier 3 (this one may already pass
  via the compliance-trigger clause, which is why the first case is the real
  one — it has no compliance surface to catch it)

I have not been able to run these, since the repo is not reachable from this
session. They are the first thing to check when it is.

---

## Q5 — Apache 2.0 on the engine while 64/137,066 is live

**Not legal advice, and this one genuinely needs counsel before the first push.
But the decision is more tractable than it looks, and one option is being
overlooked.**

What Apache 2.0 §3 actually does: each contributor grants a patent licence
covering *their contributions and the combination of those contributions with
the Work*. It is scoped to the Work. It does not license your patent in the
abstract — somebody who reads the spec and writes an independent implementation
in Go is not covered by it.

The problem is that this distinction does very little work in practice, because
a reference implementation good enough to demo at WeAreDevelopers is good enough
to fork into production, and forking is exactly the path §3 licenses. If the
commercial intent is to license the patent, Apache 2.0 on the engine undercuts
it, because the obvious adoption path is also the licensed one.

MIT is not the escape hatch it is often assumed to be. It has no express grant,
but publishing something *as a reference implementation* and inviting people to
build on it gives a defendant a serious implied-licence and estoppel argument.
Choosing MIT to preserve patent rights buys ambiguity, not protection — and
ambiguity is worse than either clear answer.

The overlooked option: **ship without a LICENSE file until counsel answers.**
You can add a licence at any time. You cannot retract one. The asymmetry is
total, and the cost of waiting is a few weeks of slightly worse adoption
signalling on a repo nobody has found yet. If the demo deadline forces the issue
before counsel is retained, Apache 2.0 with a NOTICE stating the grant's scope
explicitly is the defensible default — the NOTICE adds nothing legally that §3
does not already say, but it removes the "we assumed the whole patent was free"
conversation.

My read on your actual goals, for what it is worth: you want the model adopted
as a standard *and* you hold a patent, and those pull in opposite directions.
An unadopted patented framework is worth considerably less than an adopted one,
and the OAI registry route in Q6 is not compatible with an aggressive licensing
posture anyway. If you are going to land on Apache 2.0 eventually — and I think
you are — the value of deciding it deliberately is that the patent becomes
defensive and attributive by choice rather than by accident.

### Q5.a — The Kong plugin, as a sub-question of Q5

**Not a decision. Options only.**

Root `LICENSE` is Apache 2.0. Q5 is whether that grant is the right answer
while 64/137,066 is live. The Lua plugin in `targets/kong/plugin/` is a
further question even if Q5 is settled for the Python engine:

- It may be distributed through Kong's plugin hub, not PyPI.
- Hub conventions and the audience that copies a plugin into an existing
  Kong are not the same as `pip install ctier-engine`.
- A plugin copied on its own may or may not be "the Work" Q5 talks about.

Options, none recommended here:

1. The plugin is part of the same Work and inherits whatever Q5 decides for
   the engine, including Apache 2.0 as it stands in `LICENSE`.
2. The plugin is a separate work and gets its own licence when distributed
   through the hub, decided with counsel while the provisional is live.
3. No licence file under `targets/kong/` until that is decided (current
   state). You can add a licence; you cannot retract one.

Do not read a recommendation into this subsection. Do not add a licence
file to `targets/kong/` on the back of it.

---

## Q6 — OpenAPI Initiative registration

**Recommendation: register the `ctier` namespace now, rename the extensions to
match before the engine ships, and stop there.**

`ctier` is free in the Namespace Registry. Registration is a pull request to the
`spec.openapis.org` repository, with a lowercase identifier, prefix, description
and documentation link. Format is `x-{namespace}-`, giving `x-ctier-tier`,
`x-ctier-criteria`, `x-ctier-exclude`.

The naming win is bigger than it looks: this engine's runtime headers are
already `x-ctier-*` (C11), so registering the namespace gives you one prefix
across the design-time extension, the runtime header and the repo name. That
is the kind of coherence that makes a model easy to talk about, which is most
of what adoption is.

The cost is a spec version bump — the DOI'd spec uses `x-consequence-tier`, so
renaming means a 1.1. Do it anyway, and do it **before the engine ships**,
because the engine is what will fix the naming in people's heads. A DOI'd 1.0
with a superseded extension name is normal; an engine and a spec disagreeing is
not.

Worth reading before you submit: the `x-agent-trust` entry, which is adjacent
territory and was registered unnamespaced, and `x-sensitive-data`, which touches
one of your five criteria. Neither conflicts, but both are prior art you should
be able to distinguish on request rather than be shown.

Your IPR caution is right and I would keep it exactly as written. Registry entry
is low exposure — it records that a prefix is in use. Proposing inclusion in the
OpenAPI Specification proper is a different act with Linux Foundation licensing
and patent commitments attached, and I am not in a position to tell you what the
current OAI IPR policy text requires. Do not pursue that without counsel reading
it.

---

## Q7 — Tier 4 handoff target

**Recommendation: accept your general rule, make the target a declared property
of the operation rather than a deployment-wide setting, and add the test that
stops Tier 4 collapsing into a confirm button.**

"Hand off to whoever bears the consequence and holds the authority" is right,
and the deck's assumption of internal staff is a special case of it. Which means
the target cannot be global configuration — the same engine serves an agent
inside the bank and an agent in the customer's channel. It belongs in the
declaration:

```yaml
x-ctier-handoff:
  principal: account-holder   # or: operator, clinician, ...
  resolve-from: request.accountId
```

with the concrete human resolved from request context at suspension time. That
is a Day 8 item.

**The sharp edge.** If the handoff target can be the customer, and the agent is
in the customer's own channel, then Tier 4 looks dangerously like "the app shows
a confirm button" — which is exactly the laundering the model rejects for Tier
3. The distinction has to be stated as a test, or it will be argued at you:

> The test is whose credential the executed request carries, not who clicked.
> In Tier 4 the human authenticates and the request executes under their
> identity. A confirmation that permits the agent's credential to complete the
> call is Tier 3 with extra steps, and the ledger will show it.

That belongs next to this engine's C4 description in the PRD (what the
engine does, not what C4 requires), and it is the answer to the first hostile
question you will get about Tier 4 in Berlin.

---

## Summary of changes this record implies

| | Change | Where |
|---|---|---|
| 1 | Generator accepts description + N overlays; composition manifest | Generator contract, PRD |
| 2 | Single-target rule for tier-lowering overlay actions | PRD (normative MUST), generator |
| 3 | **C13** — proposed here; the specification minted the letter | PRD names C13 and what this engine does |
| 4 | Coverage report + non-zero exit; `--allow-unclassified` | Generator, CI |
| 5 | Rule **3b** — blast radius applies to reads on sensitive data | `classifier.py`, 2 new tests |
| 6 | Ordering re-derived from reversibility, not asserted | PRD |
| 7 | Arazzo: floor-not-ceiling, stated as future work | PRD |
| 8 | Extensions renamed to `x-ctier-*`; namespace PR | Spec 1.1, engine, generator |
| 9 | `x-ctier-handoff` declaration; credential test next to C4 | PRD, Day 8 |
| 10 | LICENSE decision deferred; no LICENSE file until counsel answers | Repo root |

Items 1–4 gate the generator. Item 5 is a live defect and should be fixed first,
since it is cheap and it is the one someone else could find.

---

Sources consulted while writing this:
[Overlay Specification v1.1.0](https://spec.openapis.org/overlay/v1.1.0.html) ·
[Namespace Registry](https://spec.openapis.org/registry/namespace/index.html) ·
[Extensions Registry](https://spec.openapis.org/registry/extension/index.html) ·
[x-agent-trust registry entry](https://spec.openapis.org/registry/extension/x-agent-trust.html) ·
[Arazzo Specification](https://www.openapis.org/arazzo-specification)
