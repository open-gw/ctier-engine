# C14 on its own hop

`c14-w1-pending-publishes-no-credential`
is Level 3 only. Level 2 has no
row. None was invented.

The case reads the published
pending list. `noCredential` is
the check. Captured from
custody, not from a kit
pass/fail. `idempotencyKey` on
the ledger decision is present;
the value is withheld.

## The runner

`engine/ctier/kit/runner.py`,
after the task-75 hop fix. A
missing correlation identifier,
or no pending row carrying it,
fails. There is no `queue[-1]`
fallback.

```
match = [
    p for p in queue
    if cid and str(p.get("correlationId") or "") == str(cid)
]
if not match:
    fail("pending.noCredential", "the pending row for this request", "none")
else:
    item = match[-1]
```

`match[-1]` is the last row
whose correlation identifier is
this response's. A neighbour is
not in `match`. The fallback
cannot be reached.

## Kong Level 3

`PUT /customers/12345/preferences/communication`.
Status 202. `X-Task-Id`
`c14-kong-level-3`. Own
correlation identifier
`a9ad0527-892b-4c0c-8f06-becaa78c2f73`.

Published pending row. Keys
present are the ones below.
`Authorization`,
`Proxy-Authorization`, cookie,
`set-cookie`, `access_token`,
bearer, `credential`, and
`credentialExp` are not among
them. No `headers` object.

```
{
  "agentId": "agent-c14-kong",
  "appliedTier": 3,
  "authority": "communications",
  "body": "",
  "correlationId": "a9ad0527-892b-4c0c-8f06-becaa78c2f73",
  "correlationScope": "c14-kong-level-3",
  "createdAt": "2026-10-25T15:05:31Z",
  "declaredTier": 3,
  "deployment": "sha256:cbbddcc056749e21fa111ce65cc7730b6236cee3fd3b967b511010e88dbfeec8",
  "digestSchema": "deploymentDigest",
  "expiresAt": "2026-10-25T15:06:01Z",
  "method": "PUT",
  "operationAnchor": "updateCommunicationPreferences",
  "path": "/customers/12345/preferences/communication",
  "query": {},
  "taskId": "c14-kong-level-3"
}
```

Ledger decision for that same
correlation identifier.
Disposition `withhold`.
`idempotencyKey` withheld.

```
{
  "agentId": "agent-c14-kong",
  "appliedTier": 3,
  "correlationId": "a9ad0527-892b-4c0c-8f06-becaa78c2f73",
  "correlationScope": "c14-kong-level-3",
  "ctierSchema": "decision-record/0.2.0",
  "declaredTier": 3,
  "deploymentDigest": "sha256:cbbddcc056749e21fa111ce65cc7730b6236cee3fd3b967b511010e88dbfeec8",
  "disposition": "withhold",
  "escalationReason": "none",
  "id": "b0af9398-6eda-48af-9905-7178e0d44ebd",
  "idempotencyKey": "[withheld]",
  "operationAnchor": "updateCommunicationPreferences",
  "timestamp": "2026-10-25T15:05:31Z",
  "type": "decision"
}
```

## APISIX Level 3

Same request. Status 202.
`X-Task-Id` `c14-apisix-level-3`.
Own correlation identifier
`f3c6383e-fd84-46b4-acde-97d96c40eeb0`.

Published pending row. The same
credential names are absent. No
`headers` object.

```
{
  "agentId": "agent-c14-apisix",
  "appliedTier": 3,
  "authority": "communications",
  "body": null,
  "correlationId": "f3c6383e-fd84-46b4-acde-97d96c40eeb0",
  "correlationScope": "c14-apisix-level-3",
  "createdAt": "2026-10-25T15:05:39Z",
  "declaredTier": 3,
  "deployment": "sha256:cbbddcc056749e21fa111ce65cc7730b6236cee3fd3b967b511010e88dbfeec8",
  "digestSchema": "deploymentDigest",
  "expiresAt": "2026-10-26T15:05:39Z",
  "method": "PUT",
  "operationAnchor": "updateCommunicationPreferences",
  "path": "/customers/12345/preferences/communication",
  "query": {},
  "taskId": "c14-apisix-level-3"
}
```

Ledger decision for that same
correlation identifier.
`idempotencyKey` withheld.

```
{
  "agentId": "agent-c14-apisix",
  "appliedTier": 3,
  "correlationId": "f3c6383e-fd84-46b4-acde-97d96c40eeb0",
  "correlationScope": "c14-apisix-level-3",
  "ctierSchema": "decision-record/0.2.0",
  "declaredTier": 3,
  "deploymentDigest": "sha256:cbbddcc056749e21fa111ce65cc7730b6236cee3fd3b967b511010e88dbfeec8",
  "disposition": "withhold",
  "escalationReason": "none",
  "id": "1d64f98d-42c2-4575-9bcb-ffa06aa11590",
  "idempotencyKey": "[withheld]",
  "operationAnchor": "updateCommunicationPreferences",
  "timestamp": "2026-10-25T15:05:39Z",
  "type": "decision"
}
```
