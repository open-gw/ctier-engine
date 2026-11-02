# SEALED KEY — DO NOT OPEN BEFORE THE RUN COMPLETES

```
################################################################
#  Facilitator material. Not for the second analyst.           #
################################################################
```

**Pin:** `0a997321234e5f6f6184b7449a241c3d30a19520` (`0a99732`),
same commit as the vendored pack corpus. Timestamps for pack
and key are the git commit that lands this directory.

Source for mechanised columns: task-92 identifier-pass script
output at that pin (`inventory-1.16.0-sweep`). Human / agreed
sets: finding 43 inventory as classified in the disagreement
work — facilitator reference only.

---

## Totals (at pin)

| Figure | Value |
|---|---:|
| Strict no-requirement | **145** |
| Lenient no-requirement | **46** |
| Human no-requirement (finding 43) | **22** |
| Agreed no (script ∩ hand) | **16** |

---

## Strict→lenient gap composition (primary rule)

Identifiers that are strict=`no` and lenient=`yes`, counted by
the primary closing rule:

| Rule | Count |
|---|---:|
| `class-coverage` | **46** |
| `titled-section-body` | **6** |
| `requirement-like-prose` | **47** |

(Gap size 145−46 = 99; primary-rule counts above are the
composition used for the sealed comparison. Overlaps where
multiple rules fire are itemised in the JSON via
`lenient_rules`.)

---

## Agreed no (16)

1. `X-Delegation-Chain`
2. `X-Incident-Id`
3. `agentId`
4. `agent_suspended`
5. `computed-tier-exceeds-declared`
6. `correlationScope`
7. `delegation-authority-expansion`
8. `failed`
9. `idempotencyKey`
10. `operationAnchor`
11. `payload-exceeds-declared-bounds`
12. `pending_authorization`
13. `placeholder`
14. `refuse-and-suspend`
15. `session-accumulation`
16. `undeclared-operation`

---

## Human no-requirement (22)

1. `execute`
2. `refuse-and-suspend`
3. `X-Delegation-Chain`
4. `X-Incident-Id`
5. `retry_later`
6. `Configured`
7. `Observed`
8. `placeholder`
9. `none` (escalationReason)
10. `session-accumulation`
11. `delegation-authority-expansion`
12. `payload-exceeds-declared-bounds`
13. `computed-tier-exceeds-declared`
14. `undeclared-operation`
15. `operationAnchor`
16. `correlationScope`
17. `agentId` (record)
18. `idempotencyKey` (record)
19. `agent_suspended`
20. `pending_authorization`
21. `executed`
22. `failed`

---

## Per-identifier lenient verdicts

See [`per-identifier-lenient.json`](per-identifier-lenient.json):
one object per inventory identifier with `strict`, `lenient`,
and `lenient_rules` at this pin.
