# Kong assumptions — observed in 08c

08b forbade a running gateway. 08c ran three named experiments against Kong
3.9.3 DB-less, the `ctier` plugin as deployed, and a mock echo backend. The
proxy was not modified.

See also [`engine/docs/portability.md`](../../engine/docs/portability.md) and
[`engine/docs/findings/08c.md`](../../engine/docs/findings/08c.md).

---

## 1. Route per operation gives native operation resolution

**Hypothesis.** Kong's router matches method and path, so the generator does
not need a second router. One route per OpenAPI operation is enough; the
request is classified by which route it hit.

**Observed.** Holds. `GET /accounts/12345/balance` reached the echo with
`x-ctier-tier: 1` and `x-ctier-operation: getBalance` — the compiled values
for that operation, not the default.

**Falsified if.** A request for a declared operation is handled by the wrong
route, or by no route (404) when a route exists for that method and path; or
two operations share a route and the plugin cannot tell them apart from
config.

**If false.** The generator must encode operation matching itself (expressions
router, a catch-all plus Lua path parse, or an Apigee-style ordered list). That
puts a second router in the plugin, which this target was designed not to have.

---

## 2. Kong resolves path specificity itself

**Hypothesis.** A literal route wins over a templated sibling without the
generator sorting them. `GET /orders/summary` is not captured by
`/orders/{orderId}`.

**What was actually emitted.** All paths are `~`…`$` regex. The generator sets
`regex_priority` to the count of literal segments. That hint is still present.

**Observed.** Holds, with the hint in place. 06's sibling pair differs by
method, which would let Kong's method match mask specificity, so the
experiment used GET on both. `GET /orders/summary` echoed tier 1
(`getOrderSummary`); `GET /orders/abc` returned 423 (the templated sibling).
The generator did not sort routes the way Apigee sorts flows. Whether the
literal would win at equal `regex_priority` was not tested.

**Falsified if.** `GET /orders/summary` is served by the templated sibling's
plugin instance despite a higher `regex_priority` on the literal; or the
literal wins even when `regex_priority` is equal, showing the hint was
unnecessary.

**If false.** The same hazard Apigee solves by document order is unsolved on
Kong. Raise `regex_priority` further, emit only expressions-router predicates,
or sort as Apigee sorts. Portability still holds only if the corpus agrees.

---

## 3. Fail-closed arises from plugin precedence

**Hypothesis.** A plugin runs once per request. A route-level `ctier` instance
overrides a global `ctier` instance. A global instance configured `tier = 4`,
plus classified routes with their own instance, means a route with no instance
inherits Tier 4 **because nothing overrode it**.

**Observed.** Holds. `exportStatements` is emitted as a route with no `ctier`
plugin. `POST /accounts/12345/statements/export` returned 423. Fail-closed
arose from the absence of an override, not from a check in the plugin. Part 3
was run because this held.

**Falsified if.** Both the global and route-level `ctier` instances run on the
same request; or the global instance does not run on a route that has no
route-level `ctier`; or an undeclared operation returns 404, 200, or a tier
other than 4.

**If false.** Fail-closed does not hold on Kong. That is a **design failure**.
The generator would need rework. 08c would not proceed to the corpus.
