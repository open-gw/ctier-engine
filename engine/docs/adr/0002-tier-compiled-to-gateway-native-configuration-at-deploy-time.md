## ADR-002 — The tier is compiled to gateway-native configuration at deploy time

**Status:** accepted with amendment · supersedes the ServiceCallout-per-request
design

**Context.** The original design put a policy service in the request path,
invoked per request. That adds a network hop to every Tier 1 read, makes the
service a hard dependency of the API, and invents a failure mode the gateway does
not otherwise have. It also sat oddly beside the compile-time binding argument:
if the tier already travels with the proxy revision, why is its evaluation
remote?

**Decision, as amended.** The architecture stands: the generator compiles each
operation into configuration the gateway already understands — a conditional flow
setting a variable, a comparison for the bounds predicate, a cache read for the
scope floor, a fault rule per disposition. No classifier runs at request time.
The mechanism follows each gateway's own idiom: declarative policy on Apigee and
Azure APIM, a thin data-driven plugin on Kong and APISIX, an `ext_authz` filter
on Envoy — where the callout this ADR supersedes is the platform's native answer.

Two amendments:

**Output mode is the adopter's choice.** The generator emits either a **complete
policy bundle** — for evaluation, greenfield proxies and the demo, where
`docker compose up` should simply work — or **mergeable fragments and plugin
configuration** for an existing proxy and an existing promotion pipeline. Neither
is the "real" mode. Supporting only fragments would make evaluation harder, which
contradicts the point.

**Targets are demand-driven.** Apigee first because it is the reference; a second
target to prove the claim. Everything beyond that is added when adoption asks for
it, not committed up front.

> **As amended by RD:** *"The arch remains the same. The gateway-specific
> artefacts can be added to support based on adoption; also there should be an
> option to generate the full policy bundle or plugins. This layer should be more
> plug and play, allowing for adoption rather than adding more red tape."*

**Consequences.** Gateway-agnosticism means one definition, one conformance
suite, compiled targets — not one runtime artefact everywhere. That is a weaker
claim and must be worded as one. The risk it creates is several implementations
that silently disagree, and it is answered by testing rather than architecture:
the reference classifier becomes the **conformance oracle**, and every target
runs the same fixture corpus and must decide identically.

The "no red tape" steer has one concrete consequence worth recording, because it
resolves a tension the drafts carried: **the coverage gate warns at Level 1
(observe) and fails the build only from Level 2 (enforce) upward.** A gate that
blocks a pipeline before anything is being enforced is friction with no safety
value.

Anything not expressible as native configuration must move to design time or to
custody. That constraint is what buys the portability, and it will occasionally
hurt.
