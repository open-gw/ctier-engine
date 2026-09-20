"""Cross-language differential for the C7 derived idempotency key.

This file does not add a Lua implementation. It reconstructs the abandoned
14c Lua material join in Python, and the Apigee JS join from generate.py,
and compares both to `derive_idempotency_key`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from ctier.classifier import GovernanceConfig, derive_idempotency_key
from ctier.generate import _js_set_upstream_provenance
from ctier.models import Operation, Request

SEP = "\x1f"
KEY = GovernanceConfig().hmac_key
HANDLER = (
    Path(__file__).resolve().parents[2] / "targets" / "kong" / "plugin" / "handler.lua"
)


def op(**kw) -> Operation:
    base = dict(
        method="GET",
        path_template="/accounts/{id}/balance",
        operation_id="getBalance",
    )
    base.update(kw)
    return Operation(**base)


def req(**kw) -> Request:
    base = dict(
        method="GET",
        path="/accounts/1/balance",
        agent_id="agent-a",
        task_id="task-1",
    )
    base.update(kw)
    return Request(**base)


def python_material(operation: Operation, request: Request) -> str:
    """Exact join inside derive_idempotency_key (classifier.py)."""
    body_canonical = ""
    if request.body:
        try:
            body_canonical = json.dumps(
                json.loads(request.body), sort_keys=True, separators=(",", ":")
            )
        except (ValueError, TypeError):
            body_canonical = request.body
    return SEP.join(
        [
            operation.anchor(),
            request.path,
            json.dumps(dict(sorted(request.query.items())), separators=(",", ":")),
            body_canonical,
            request.agent_id,
            request.task_id or "",
        ]
    )


def lua_abandoned_material(operation: Operation, request: Request) -> str:
    """14c Kong fallback: sorted query, raw body, no JSON canonicalisation.

    Query object is string-concatenated, not json.encoded. Body is
    kong.request.get_raw_body(), not loads/dumps.
    """
    keys = sorted(request.query)
    qjson = "{" + ",".join(f'"{k}":"{request.query[k]}"' for k in keys) + "}"
    body = request.body or ""
    return SEP.join(
        [
            operation.anchor(),
            request.path,
            qjson,
            body,
            request.agent_id,
            request.task_id or "",
        ]
    )


def apigee_js_material(operation: Operation, request: Request) -> str:
    """Removed in 23. Kept so the 22 edges stay named as a historical miss."""
    return SEP.join(
        [
            operation.anchor(),
            request.path,
            "{}",
            "",
            request.agent_id,
            request.task_id or "",
        ]
    )


def python_key(operation: Operation, request: Request) -> str:
    return hmac.new(KEY, python_material(operation, request).encode(), hashlib.sha256).hexdigest()


def lua_would_have_keyed(operation: Operation, request: Request) -> str:
    """What Python HMAC-SHA256 hex of the Lua material would be, had ngx.hmac_sha256 existed."""
    return hmac.new(
        KEY, lua_abandoned_material(operation, request).encode(), hashlib.sha256
    ).hexdigest()


# --- Part 0: the Python function's inputs ----------------------------------


def test_python_key_is_hmac_sha256_hex_of_the_six_field_join():
    o, r = op(), req(body='{"z":1,"a":2}', query={"b": "2", "a": "1"})
    assert derive_idempotency_key(o, r, KEY) == python_key(o, r)


def test_inputs_are_anchor_path_sorted_query_json_body_agent_task():
    o, r = op(), req(body='{"name":"A"}', query={"id": "1"})
    parts = python_material(o, r).split(SEP)
    assert parts[0] == "getBalance"
    assert parts[1] == "/accounts/1/balance"
    assert parts[2] == '{"id":"1"}'
    assert parts[3] == '{"name":"A"}'
    assert parts[4] == "agent-a"
    assert parts[5] == "task-1"


def test_non_json_body_is_hashed_raw():
    o, r = op(), req(method="PUT", body="not-json")
    assert python_material(o, r).split(SEP)[3] == "not-json"
    assert derive_idempotency_key(o, r, KEY) == python_key(o, r)


def test_json_body_is_re_serialised_with_sorted_keys():
    o = op(operation_id="updateProfile", method="PUT")
    a = req(method="PUT", body='{"a":1,"b":2}')
    b = req(method="PUT", body='{"b":2,"a":1}')
    assert python_material(o, a).split(SEP)[3] == '{"a":1,"b":2}'
    assert python_material(o, a) == python_material(o, b)


def test_handler_lua_does_not_contain_a_gateway_hmac():
    text = HANDLER.read_text(encoding="utf-8")
    assert "ngx.hmac_sha256" not in text
    assert "hmac.new" not in text


def test_apigee_js_does_not_derive_an_idempotency_key():
    src = _js_set_upstream_provenance()
    assert "hmac" not in src.lower()
    assert "Idempotency-Key" not in src
    assert "x-ctier-correlation-id" in src.lower()


# --- Part 2: agreement, including the edges a happy path hides -------------


def test_empty_query_and_empty_body_all_three_materials_agree():
    o, r = op(), req()
    assert python_material(o, r) == lua_abandoned_material(o, r) == apigee_js_material(o, r)
    assert derive_idempotency_key(o, r, KEY) == lua_would_have_keyed(o, r)


def test_query_key_order_python_and_lua_agree():
    o = op()
    a = req(query={"b": "2", "a": "1"})
    b = req(query={"a": "1", "b": "2"})
    assert python_material(o, a) == python_material(o, b)
    assert lua_abandoned_material(o, a) == lua_abandoned_material(o, b)
    assert python_material(o, a) == lua_abandoned_material(o, a)
    assert apigee_js_material(o, a) != python_material(o, a)


def test_absent_versus_empty_query_value():
    o = op()
    absent = req()
    empty = req(query={"q": ""})
    assert python_material(o, absent) != python_material(o, empty)
    assert lua_abandoned_material(o, absent) != lua_abandoned_material(o, empty)
    # Python json.dumps encodes empty as ""; Lua concatenation does the same.
    assert python_material(o, empty) == lua_abandoned_material(o, empty)
    # Apigee never sees the query, so absent and empty collide.
    assert apigee_js_material(o, absent) == apigee_js_material(o, empty)


def test_query_value_that_needs_json_escaping_diverges():
    o = op()
    r = req(query={"q": 'a"b'})
    assert python_material(o, r) != lua_abandoned_material(o, r)
    assert derive_idempotency_key(o, r, KEY) != lua_would_have_keyed(o, r)


def test_json_key_order_python_stable_lua_follows_the_bytes():
    o = op(operation_id="updateProfile", method="PUT")
    a = req(method="PUT", body='{"a":1,"b":2}')
    b = req(method="PUT", body='{"b":2,"a":1}')
    assert derive_idempotency_key(o, a, KEY) == derive_idempotency_key(o, b, KEY)
    assert lua_abandoned_material(o, a) != lua_abandoned_material(o, b)
    assert lua_would_have_keyed(o, a) != lua_would_have_keyed(o, b)


def test_json_whitespace_python_canonical_lua_raw():
    o = op(operation_id="updateProfile", method="PUT")
    compact = req(method="PUT", body='{"a":1}')
    spaced = req(method="PUT", body='{ "a": 1 }')
    assert derive_idempotency_key(o, compact, KEY) == derive_idempotency_key(o, spaced, KEY)
    assert lua_abandoned_material(o, compact) != lua_abandoned_material(o, spaced)


def test_unicode_bmp_in_json_body_python_escapes_lua_keeps_utf8():
    o = op(operation_id="updateProfile", method="PUT")
    r = req(method="PUT", body='{"name":"café"}')
    py_body = python_material(o, r).split(SEP)[3]
    assert "\\u00e9" in py_body
    assert lua_abandoned_material(o, r).split(SEP)[3] == '{"name":"café"}'
    assert derive_idempotency_key(o, r, KEY) != lua_would_have_keyed(o, r)


def test_unicode_outside_bmp_in_json_body_diverges():
    o = op(operation_id="updateProfile", method="PUT")
    r = req(method="PUT", body='{"note":"𝄞"}')
    py_body = python_material(o, r).split(SEP)[3]
    assert "\\ud834\\udd1e" in py_body
    assert lua_abandoned_material(o, r).split(SEP)[3] == '{"note":"𝄞"}'
    assert derive_idempotency_key(o, r, KEY) != lua_would_have_keyed(o, r)


def test_unicode_in_query_python_escapes_lua_does_not():
    o = op()
    r = req(query={"q": "café"})
    assert "\\u00e9" in python_material(o, r).split(SEP)[2]
    assert lua_abandoned_material(o, r).split(SEP)[2] == '{"q":"café"}'
    assert python_material(o, r) != lua_abandoned_material(o, r)


def test_long_json_body_same_shape_as_short_json_body():
    o = op(operation_id="updateProfile", method="PUT")
    payload = json.dumps({"blob": "x" * 8000}, separators=(",", ":"))
    r = req(method="PUT", body=payload)
    assert derive_idempotency_key(o, r, KEY) == python_key(o, r)
    # Compact JSON with sorted keys: Lua raw matches Python here.
    assert python_material(o, r) == lua_abandoned_material(o, r)
    assert apigee_js_material(o, r) != python_material(o, r)


def test_absent_body_versus_empty_string_agree_in_python_and_lua():
    o = op()
    absent = req()
    empty = req(body="")
    assert python_material(o, absent) == python_material(o, empty)
    assert lua_abandoned_material(o, absent) == lua_abandoned_material(o, empty)


def test_apigee_agrees_on_the_happy_path_and_collides_on_every_body():
    o = op(operation_id="updateProfile", method="PUT")
    empty = req(method="PUT")
    with_body = req(method="PUT", body='{"name":"A"}')
    assert apigee_js_material(o, empty) == python_material(o, empty)
    assert apigee_js_material(o, with_body) == apigee_js_material(o, empty)
    assert python_material(o, with_body) != python_material(o, empty)
