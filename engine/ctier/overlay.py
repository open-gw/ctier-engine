# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Overlay 1.1.0 application. RFC 9535 JSONPath via jsonpath-rfc9535."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from jsonpath_rfc9535 import find

from .errors import ComposeError


def _walk(doc: Any, location: tuple) -> tuple[Any, Any]:
    parent = doc
    for key in location[:-1]:
        parent = parent[key]
    return parent, location[-1]


def merge(target: Any, update: Any) -> Any:
    if isinstance(target, dict) and isinstance(update, dict):
        out = dict(target)
        for key, value in update.items():
            if key not in out:
                out[key] = deepcopy(value)
            elif isinstance(out[key], dict) and isinstance(value, dict):
                out[key] = merge(out[key], value)
            elif isinstance(out[key], list) and isinstance(value, list):
                out[key] = list(out[key]) + list(value)
            elif type(out[key]) is type(value) or (
                isinstance(out[key], (str, int, float, bool, type(None)))
                and isinstance(value, (str, int, float, bool, type(None)))
            ):
                out[key] = deepcopy(value)
            else:
                raise ComposeError(
                    "overlay-merge",
                    f"incompatible merge at {key!r}: {type(out[key]).__name__} vs {type(value).__name__}",
                )
        return out
    if isinstance(target, list) and isinstance(update, list):
        return list(target) + list(update)
    return deepcopy(update)


def apply_overlay(document: dict, overlay: dict) -> tuple[dict, list[dict]]:
    """Apply overlay actions in order. Returns (document, zero-match reports)."""
    current = deepcopy(document)
    zero: list[dict] = []
    actions = overlay.get("actions") or []
    for index, action in enumerate(actions):
        target = action.get("target")
        if not target:
            raise ComposeError("schema", f"overlay action {index} has no target")
        nodes = list(find(target, current))
        if not nodes:
            zero.append({"index": index, "target": target, "matches": 0})
            continue
        if action.get("remove") is True:
            for node in nodes:
                parent, key = _walk(current, node.location)
                if isinstance(parent, dict):
                    parent.pop(key, None)
                elif isinstance(parent, list) and isinstance(key, int):
                    parent.pop(key)
            continue
        if action.get("copy"):
            kinds = {_kind(node.value) for node in nodes}
            if len(kinds) > 1:
                raise ComposeError(
                    "overlay-target",
                    f"action {index} selected mixed node types: {sorted(kinds)}",
                )
            sources = list(find(action["copy"], current))
            if len(sources) != 1:
                raise ComposeError(
                    "overlay-copy",
                    f"copy must select one node, selected {len(sources)}",
                )
            value = deepcopy(sources[0].value)
            for node in nodes:
                parent, key = _walk(current, node.location)
                parent[key] = merge(parent[key], value) if isinstance(parent[key], dict) else deepcopy(value)
            continue
        if "update" in action:
            update = action["update"]
            kinds = {_kind(node.value) for node in nodes}
            if len(kinds) > 1:
                raise ComposeError(
                    "overlay-target",
                    f"action {index} selected mixed node types: {sorted(kinds)}",
                )
            for node in nodes:
                parent, key = _walk(current, node.location)
                parent[key] = _apply_update(parent[key], update)
    return current, zero


def _kind(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "primitive"


def _apply_update(target: Any, update: Any) -> Any:
    if isinstance(target, list):
        if isinstance(update, list):
            return list(target) + list(update)
        return list(target) + [deepcopy(update)]
    return merge(target, update)
