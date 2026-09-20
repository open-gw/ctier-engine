# How a gateway's decision will be observed

Task 08b implements this. It is specified here because it constrains what 08b
may do, and the constraint is the point.

## The gateway under test is not modified

No debug build, no conformance profile, no policy that echoes the tier back to
the caller. What is tested must be exactly what would be deployed, or the
harness proves something about an artefact nobody ships.

The tier is observed instead through a **mock backend that echoes the
`x-ctier-*` headers it received.** The proxy already forwards those to its
target; the echo lives in harness infrastructure.

## Projection

| Observation | Decision |
|---|---|
| target reached, echo carries the tier | `execute`, tier from the echo |
| `423` | `refuse-and-suspend`, tier 4 |
| `401` | `refuse-unauthorized` — token missing the operation's scope |
| `403` provisioning refusal | `refuse-provisioning` |
| `202` | `withhold`, tier 3 |

Executing tiers reveal their exact tier through the echo; refusing tiers reveal
their disposition through the status. Between them every disagreement that
matters is visible — including the quiet one where two implementations both
execute but disagree about which tier they executed at.

A compiled proxy without custody refuses Tier 3 as a provisioning defect
(task 06). That is the expected disposition at `deployment: level-2`, not a
classification disagreement and not out of scope. `403` does not encode the
tier: exclusion and Tier 3 without custody share the status. `appliedTier` on
that observation is filled from the spec so the comparison stays
classification versus disposition, not a fake T4. Level 3 (`202` / `withhold`)
is exercised when custody exists.

## Production must not echo

Echoing `x-ctier-*` back to a caller is something a production deployment must
not do. It hands an agent the governance metadata it would need to reason about
how to avoid a tier. The mock backend does it because it is a test fixture and
its responses reach nobody.

## C11

Confirmed against the reference path *and* against Kong. `ReferenceAdapter`
given `x-ctier-tier: 1` against a declared Tier 4 operation
(`PUT /config/feature-flags`) still refuses at Tier 4. Resolve does not read
request headers; `Classifier.classify` does not mention headers; C3 would
restore a declared floor anyway. That path cannot fail the case.

The inbound header is stripped in the proxy. The hand-written case is no
longer a placeholder: `KongAdapter` is the first adapter that can fail it.
A pass means the injected tier did not execute. A fail is urgent — C11 is
the attack that collapses the model.
