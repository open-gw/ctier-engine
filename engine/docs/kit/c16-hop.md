# C16 on the forged hop

`c16-unknown-prefix-name-is-absent`.
`GET /accounts/12345/balance` with
`x-ctier-unknown-audit: forged`.
Expect status 200. The name is absent
on the hop the echo received.

Each quote is that balance request,
taken from a raw socket on the echo
container's network namespace. Not
the kit runner. The same window also
held a `GET /` healthcheck. The
quoted request is the one whose path
is `/accounts/12345/balance` and
whose `X-Task-Id` is the label below.
`x-ctier-unknown-audit` is not on it.
Credential headers are omitted.

## Kong Level 3

Status 200. One balance request,
three healthchecks, in the window.

```
GET /accounts/12345/balance HTTP/1.1
X-Task-Id: c16-kong-level-3
x-ctier-operation: getBalance
x-ctier-tier: 1
x-ctier-correlation-id: 1792900626.689-1406-869134346
```

## Kong Level 2

Status 200. One balance request,
two healthchecks, in the window.

```
GET /accounts/12345/balance HTTP/1.1
X-Task-Id: c16-kong-level-2
x-ctier-operation: getBalance
x-ctier-tier: 1
x-ctier-correlation-id: 1792900648.584-1406-652340690
```

## APISIX Level 3

Status 200. One balance request,
two healthchecks, in the window.

```
GET /accounts/12345/balance HTTP/1.1
X-Task-Id: c16-apisix-level-3
X-Ctier-Operation: getBalance
X-Ctier-Tier: 1
x-ctier-correlation-id: 1792900708.147-33-945691970
```

## APISIX Level 2

Status 200. One balance request,
two healthchecks, in the window.

```
GET /accounts/12345/balance HTTP/1.1
X-Task-Id: c16-apisix-level-2
X-Ctier-Operation: getBalance
X-Ctier-Tier: 1
x-ctier-correlation-id: 1792900730.54-32-212193742
```
