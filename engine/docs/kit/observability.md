# Observability map — C1–C16

Four classes. Every lettered criterion
is in exactly one, except C15, which
is split on purpose.

| Class | Meaning |
|---|---|
| Runtime | A request or published follow-up shows the obligation held or failed. |
| Generation | Observable when compiling, not at a running target URL. |
| Out of scope for a target | Authorisation-server or operator condition. The enforcement point cannot make it unavoidable. |
| Not observable | Negative or internal. The kit can falsify. It cannot verify. |

Not-observable is the class that
matters. Passing a witness does not
establish the criterion. Taxonomy 33,
as 54 and 56 wrote for C4.

Requirements 1–6 are not criteria.
They are out of scope for a target.

---

## Map

| Criterion | Class | Cases | Notes |
|---|---|---|---|
| C1 | Runtime | 1 | A classified refuse does not execute. |
| C2 | Runtime | 1 | An undeclared operation in the composition is the highest-class refuse. |
| C3 | Runtime | 1 | A request that crosses a declared bound is treated as the higher class, not the lower. |
| C4 | Not observable | 3 witnesses | Below. |
| C5 | Runtime | 1 | Withheld response is terminal, does not invite retry, does not leave the caller engaged. |
| C6 | Runtime | 1 | Needs an approval surface and a backend observer. |
| C7 | Runtime | 1 | The identifier a honouring backend would use is not the caller's choice. Needs a backend observer. **Not satisfiable below Level 3** (no custody → nowhere to store a derived key). The adoption ladder says Level 2 does not satisfy C7. The case is Level 3 only; at Level 2 it skips as not applicable. |
| C8 | Out of scope | 0 | Rejection is an authorisation-server effect. Expiry is a timed store event, not a request this runner sends. |
| C9 | Runtime | 1 | Highest-class refuse names no resume handle. |
| C10 | Runtime | 3 | A decision record on an ordinary execute, on a classified highest-class refuse, and on the composed-undeclared (C2) path. **Apigee:** Trace `print()` is not retrievable. The stock package compiles a fail-open `SC-RecordDecision` POST to a collector URL and ships `package/collector/`; empty `kit_records` → skip (`requires a capability this target lacks`), not a pass. |
| C11 | Runtime | 1 | An inbound tier does not select a lower class. |
| C12 | Runtime | 1 | A path **routed** at the enforcement point with no assignment is refused undetermined, not classified as the highest class. A bare unrouted `404` is inconclusive. |
| C13 | Generation | 1 | Generate against one composition, present another. Not a URL case. |
| C14 | Not observable | 1 witness | Below. |
| C15 (AS) | Out of scope | 0 | Compiled-absence at the authorisation server. |
| C15 (EP) | Not observable | 0 | Below. No published witness. |
| C16 | Runtime | 1 | An unknown name under the reserved prefix is absent at the backend. Needs a backend observer. **Apigee:** package ships `package/observer/`; empty `kit_observer` → skip. |

Runtime cases: 13.
Generation cases: 1.
Not-observable witnesses: 4 (C4 × 3, C14 × 1).
Out of scope, no case: C8, C15 AS.
Not observable, no witness: C15 EP.

### C7 below Level 3

C7 is not satisfiable where there is no
custody. Level 2 strips inbound keys
and has nowhere to store a derived one.
The adoption ladder already says Level
2 does not satisfy C7. The kit case is
Level 3 only. An L2 matrix that painted
that row red was measuring a rung the
ladder does not claim.

---

## Not observable — witnesses and the caveat

Passing does not establish the
criterion. The suite cannot verify a
negative property. It can falsify it.
It can witness a consequence that
would be present if the criterion
were violated.

### C4

| Witness | What would falsify |
|---|---|
| A withhold has no poll URL | A withhold that offered one, or invited the caller to stay engaged. |
| Level 2, class-3, is a decision, not a wait | `202`, `503`, or pending. |
| A highest-class refuse completes; nothing holding | That identifier sitting in a pending queue. |

### C14

| Witness | What would falsify |
|---|---|
| A published pending item carries no credential | `Authorization`, `Proxy-Authorization`, a cookie, or the caller's bearer material in the published object. |

The witness looks at what the store
**publishes**. It does not open the
store. A credential kept off that
surface and on disk would not be
seen. That is why this is a witness,
not a verification.

### C15, enforcement-point half

No published surface shows the
absence of a gateway-local denylist,
or that the enforcement point did not
ask a policy service whether a caller
is suspended. A witness would read
the enforcement point's own memory.
The kit does not. There is no
witness. The criterion stays not
observable. This is not a new letter.

---

## What the kit does not cover

suspension as a mechanism — covered,
by C2 and C9
(`c2-undeclared-is-highest-class-refuse`,
`c9-highest-class-names-no-resume`),
which require agent_suspended on a
Tier 4 refuse

withheld-then-approved — covered in
the live suite, not in the kit

withheld-then-rejected-then-suspended
— not covered anywhere
