# Conformance case list

`conformance-kit/1.1`. Cases change only with a
version bump. A target's result is meaningful
only against this version.

One row per observable obligation. Target-agnostic:
no row names how a target implements the outcome.
If a row cannot be written without naming a
target's mechanism, it is an implementation test
and does not belong here.

Generation rows are not sent to a URL.
Not-observable rows are witnesses: they falsify,
they do not verify. See
[`observability.md`](observability.md).

A target may differ only as
[`divergence.md`](divergence.md) enumerates.

| id | Criterion | Request / action | Observable outcome | May a target differ |
|---|---|---|---|---|
| `c1-classified-refuse-does-not-execute` | C1 | `POST /payments` with an entitled token | Status `423`. Not `200`. If a backend observer is present, that backend did not receive this request. | No |
| `c2-undeclared-is-highest-class-refuse` | C2 | `POST /accounts/12345/statements/export` | Status `423`. Body `status` `agent_suspended`, `agentAction` `halt_and_hand_off`. Header and body agree when both name the instruction. | No |
| `c3-bound-crossing-is-the-higher-class` | C3 | `GET /accounts/12345/transactions?limit=101` | Not `200`. The higher class: `202` where a persist path exists, or `403` `provisioning_defect` where it does not. Not the highest-class refuse. | Disposition `202` vs `403` by whether persist is deployed. That is the level, not the target. |
| `c4-w1-withhold-has-no-poll-url` | C4 witness | `PUT /customers/12345/preferences/communication` where persist is deployed | Status `202`. No `pollUrl` in the body. No poll URL header. Does not establish C4. | No |
| `c4-w2-level-2-class-3-is-a-decision` | C4 witness | Same path, no persist path | Status `403`, body `status` `provisioning_defect`. Not `202`, not `503`, not pending. Does not establish C4. | No |
| `c4-w3-highest-class-holds-nothing` | C4 witness | `POST /payments`, then read the published pending list | Status `423`, `halt_and_hand_off`. That `correlationId`, if any, is not in the pending list. Does not establish C4. | No |
| `c5-withheld-caller-is-released` | C5 | `PUT /customers/12345/preferences/communication` where persist is deployed | Status `202`. Body `status` `pending_authorization`, `retryable` false, `agentAction` `continue_task_without_this_step`. No `Retry-After`. No `pollUrl`. Header and body agree. | No |
| `c6-execute-is-the-approved-bytes` | C6 | Withhold as C5, then approve that item | The backend receives one request whose method and path are the withheld operation. The `Authorization` on that hop is not the caller's. | No |
| `c7-caller-does-not-choose-the-identifier` | C7 | `GET /accounts/12345/balance` with `Idempotency-Key: agent-chosen` (Level 3) | At the backend the identifier is present and is not `agent-chosen`. | No at Level 3. **Not applicable at Level 2** — no custody, nowhere to store a derived key; the adoption ladder says Level 2 does not satisfy C7. The row skips, it does not fail. |
| `c9-highest-class-names-no-resume` | C9 | `POST /payments` | Status `423`. Body `status` `agent_suspended`, `agentAction` `halt_and_hand_off`, `autoResume` false when present. No `correlationId`. No `pollUrl`. Header and body agree when the named `423` mechanism is used. | No |
| `c10-execute-has-a-decision` | C10 | `GET /accounts/12345/balance` | A decision record was written for this request. | Sink transport may differ (see divergence). Absence of a record is a failure. |
| `c10-highest-class-has-a-decision` | C10 | `POST /payments` | A decision record was written for this request. | Same. Absence is a failure. |
| `c10-undeclared-has-a-decision` | C10 | `POST /accounts/12345/statements/export` | A decision record was written for this composed-but-undeclared refuse. | Same. Absence is a failure. The undeclared default is a decision; C2 alone does not check the sink. |
| `c11-inbound-tier-is-not-honoured` | C11 | `PUT /config/feature-flags` with `x-ctier-tier: 1` | Status `423`. Not `200`. | No |
| `c12-unassigned-is-refused-undetermined` | C12 | `GET /estate/unknown` on a path **routed at the enforcement point** and absent from the composition | Status `423`. Body `status` `unassigned`, `agentAction` `halt`. If records are available: an attempt with applied tier undetermined, and no decision. | A later, more specific route that claims this path may escape. That bound is listed under divergence. Against a routed path no later route claimed, no. A bare `404` (path never routed) is **inconclusive**, not a fail — the kit cannot tell that from a C12 miss. |
| `c13-assignment-does-not-apply-to-another-composition` | C13 | Generate against composition A; present composition B with the same operations | Generate refuses. The running target is unchanged. | Not a URL case. |
| `c14-w1-pending-publishes-no-credential` | C14 witness | After C5, read the published pending item | No `Authorization`, `Proxy-Authorization`, cookie, or bearer material. Does not establish C14. | No |
| `c16-unknown-prefix-name-is-absent` | C16 | `GET /accounts/12345/balance` with `x-ctier-unknown-audit: forged` | Status `200`. That name is absent at the backend. | No |

C8 has no row. C15 has no row.
