#!/usr/bin/env python3
"""Mechanised identifier pass (audit tasks 89 / 92).

Reads the specification at a given git commit and derives an
identifier inventory under the counting rule in COUNTING-RULE.md
beside this script.

Reports a **strict** / **lenient** pair for the requirement-
sentence column (task 92). Strict is the task-89 whole-token +
RFC 2119 rule. Lenient adds class-coverage, titled-section body,
and requirement-like prose — see COUNTING-RULE.md.

Usage:
  identifier_pass.py COMMIT [--repo PATH] [--json OUT] [--md OUT]

Environment:
  CTIER_REPO  default path to the public ctier specification repo
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

NORMATIVE = re.compile(r"\b(MUST(?:\s+NOT)?|SHALL(?:\s+NOT)?|REQUIRED)\b")
# Ordinary-English obligation cues used by the lenient prose rule
# (bucket B). Does not include uppercase RFC 2119 — those are strict.
PROSE_OBLIGATION = re.compile(
    r"(?i)\b("
    r"must(?:\s+not)?"
    r"|shall(?:\s+not)?"
    r"|required"
    r"|must never"
    r"|is a contradiction"
    r"|contains only"
    r"|equals the expected"
    r"|is ordered"
    r"|not a ctier emit"
    r"|validator-enforced"
    r"|fail-closed"
    r")\b"
)
EXCLUDED_BOLD = re.compile(r"(?i)\bExcluded\b")
FENCE = re.compile(r"```.*?```", re.S)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BOLD_LEAD = re.compile(r"^\*\*([^*]+)\*\*")
BACKTICK = re.compile(r"`([^`]+)`")
CRITERION = re.compile(r"\bC(\d+)\b")
LEVEL = re.compile(r"\bLevel\s+(\d+)\b", re.I)
LEVEL_SLUG = re.compile(r"\blevel-(\d+)\b", re.I)
TIER = re.compile(r"\bTier\s+(\d+)\b", re.I)
REQUIREMENT = re.compile(r"\bRequirement\s+(\d+)\b", re.I)
X_CTIER_KEY = re.compile(r"\bx-ctier-[A-Za-z0-9_-]+\b")
NAMESPACE = re.compile(r"`(x-ctier-\*|x-consequence-\*)`")

RULE_STRICT = "strict-rfc2119"
RULE_CLASS = "class-coverage"
RULE_TITLE = "titled-section-body"
RULE_PROSE = "requirement-like-prose"

# Hand inventory concepts (finding 43). Harvested when present in prose.
CONCEPTS = {
    "governed set",
    "granted scope",
    "undeclared default",
    "join key",
    "scope floor",
    "structural floor",
    "deploy-time bound",
    "persist-and-execute",
    "namespace strip",
    "integrity-protection",
    "refuse-to-emit",
    "undetermined",
}

# Nested fields under x-ctier-* objects (finding 43 Extension subfield).
EXTENSION_SUBFIELDS = {
    "undeclaredTier",
    "escalateAbove",
    "decaySeconds",
    "recommendationTtlDays",
    "parameter",
    "max",
    "authority",
}

HEADER_ALIASES = {
    "X-Correlation-Id",
    "X-Ctier-Tier",
    "X-Idempotency-Key",
}

# Schema field names treated as first-class vocabulary (COUNTING-RULE.md).
VOCAB_FIELDS = {
    "escalationReason",
    "disposition",
    "result",
    "profile",
    "deployment",
    "sequence",
    "appliedTierAtLeast",
    "placeholder",
    "operationAnchor",
    "correlationScope",
    "agentId",
    "idempotencyKey",
    "compositionDigest",
    "deploymentDigest",
    "ctierSchema",
}

CRITERIA_DIMS = {
    "reversibility",
    "blast-radius",
    "blastRadius",
    "data-sensitivity",
    "dataSensitivity",
    "compliance-trigger",
    "complianceTrigger",
    "idempotency",
}


@dataclass
class Row:
    identifier: str
    class_name: str
    requirement_sentence: bool  # strict (back-compat)
    titled_under_own_name: bool
    sources: list[str] = field(default_factory=list)
    notes: str = ""
    requirement_sentence_strict: bool = False
    requirement_sentence_lenient: bool = False
    lenient_rules: list[str] = field(default_factory=list)


def run_git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def list_corpus_paths(repo: Path, commit: str) -> list[str]:
    names = run_git(repo, "ls-tree", "-r", "--name-only", commit).decode().splitlines()
    out: list[str] = []
    for n in names:
        if n.startswith("spec/") and (
            n.endswith(".md")
            or n.endswith(".json")
            or n.endswith(".yaml")
            or n.endswith(".yml")
        ):
            # examples: do not invent identifiers from examples alone
            if "/examples/" in n and not n.endswith("README.md"):
                continue
            out.append(n)
        elif re.match(r"docs/adr/0009", n):
            out.append(n)
    return out


def load_text(repo: Path, commit: str, path: str) -> str:
    return run_git(repo, "show", f"{commit}:{path}").decode("utf-8", "replace")


def strip_fences(text: str) -> str:
    return FENCE.sub("", text)


def paragraphs(text: str) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            if buf:
                chunks.append("\n".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        chunks.append("\n".join(buf))
    return chunks


def token_in_text(ident: str, text: str) -> bool:
    """Whole-token / backtick / bold-aware presence check."""
    if f"`{ident}`" in text:
        return True
    if f"**{ident}**" in text:
        return True
    # criteria / Level / Tier / Requirement already word-shaped
    if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(ident)}(?![A-Za-z0-9_-])", text):
        return True
    return False


def walk_json(
    node: Any,
    path: str,
    enums: list[tuple[str, list[str]]],
    consts: list[tuple[str, str]],
    defs_keys: list[str],
    props: list[tuple[str, str]],
) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("enum"), list):
            vals = [v for v in node["enum"] if isinstance(v, str)]
            if vals:
                enums.append((path, vals))
        if isinstance(node.get("const"), str):
            consts.append((path, node["const"]))
        if isinstance(node.get("$defs"), dict):
            for k in node["$defs"]:
                defs_keys.append(k)
                walk_json(node["$defs"][k], f"{path}/$defs/{k}", enums, consts, defs_keys, props)
        props_node = node.get("properties")
        if isinstance(props_node, dict):
            for k, v in props_node.items():
                props.append((path, k))
                walk_json(v, f"{path}.{k}", enums, consts, defs_keys, props)
        for k, v in node.items():
            if k in ("enum", "const", "$defs", "properties"):
                continue
            walk_json(v, f"{path}.{k}", enums, consts, defs_keys, props)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_json(v, f"{path}[{i}]", enums, consts, defs_keys, props)


def classify(ident: str, sources: list[str]) -> str:
    src = " ".join(sources)
    if re.fullmatch(r"C\d+", ident):
        return "Criterion"
    if re.fullmatch(r"Level \d+", ident, re.I) or re.fullmatch(r"level-\d+", ident, re.I):
        return "Deployment level"
    if re.fullmatch(r"Tier \d+", ident, re.I):
        return "Tier"
    if re.fullmatch(r"Requirement \d+", ident, re.I):
        return "Deployment requirement"
    if ident in {
        "execute",
        "withhold",
        "refuse-and-suspend",
        "refuse-provisioning",
    }:
        return "Disposition"
    if ident in {
        "none",
        "session-accumulation",
        "delegation-authority-expansion",
        "payload-exceeds-declared-bounds",
        "computed-tier-exceeds-declared",
        "undeclared-operation",
    } and "escalationReason" in src:
        return "Escalation reason"
    if ident in {"executed", "failed"} and ("result" in src or "outcome" in src):
        return "Outcome result"
    if ident in {"bundle", "fragments"}:
        return "Generator mode"
    if ident in {"description", "overlay"} and "role" in src:
        return "Composition role"
    if ident in {"declared", "recommended", "absent"}:
        return "Coverage status"
    if ident in {"high", "medium", "low"}:
        return "Confidence"
    if ident in {"standard", "constrained"}:
        return "Profile"
    if ident in {"method"} or ident.startswith("path") or ident in {
        "responseIsCollection",
        "hasRequestBody",
        "securitySchemes",
        "tagIn",
        "operationIdMatches",
        "hasDeclaredReversal",
        "pathSegmentCount",
        "pathParameterCount",
        "pathEndsWithParameter",
    }:
        if "when" in src or "validation" in src or "predicate" in src:
            return "when-predicate"
    if ident in VOCAB_FIELDS:
        if ident in {"compositionDigest", "deploymentDigest"}:
            return "Digest"
        if ident == "ctierSchema":
            return "Document key"
        if ident in {
            "operationAnchor",
            "correlationScope",
            "agentId",
            "idempotencyKey",
        }:
            return "Ledger field"
        if ident in {
            "profile",
            "deployment",
            "sequence",
            "appliedTierAtLeast",
            "placeholder",
        }:
            return "Corpus field"
        if ident in {"disposition", "escalationReason", "result"}:
            return "Ledger field"
    if ident.startswith("x-ctier-") and "header" in src.lower():
        return "Header"
    if ident.startswith("x-ctier-"):
        return "Extension field"
    if ident in {"x-ctier-*", "x-consequence-*"}:
        return "Namespace"
    if re.fullmatch(r"(decision|attempt|outcome)-record/\d+\.\d+\.\d+", ident):
        return "Record version"
    if ident in {"Decision", "Attempt", "Outcome"}:
        return "Record type"
    if "/" in ident and re.search(r"/\d+\.\d+\.\d+$", ident):
        return "Document type"
    if ident in {"sha256:", "sha256: digest form"}:
        return "Document key"
    dim_norm = ident.replace("blastRadius", "blast-radius").replace(
        "dataSensitivity", "data-sensitivity"
    ).replace("complianceTrigger", "compliance-trigger")
    if dim_norm in {
        "reversibility",
        "blast-radius",
        "data-sensitivity",
        "compliance-trigger",
        "idempotency",
    } or ident in CRITERIA_DIMS:
        return "Criteria dimension"
    if ident in {
        "not-applicable",
        "undo-restores-effect",
        "undo-restores-record-only",
        "single-record",
        "single-customer",
        "population",
        "system-wide",
        "public",
        "internal",
        "personal",
        "regulated",
        "adjacent",
        "direct",
        "inherently-safe",
        "safe",
        "key-required",
        "unsafe",
    }:
        return "Criteria value"
    if ident in {"none"} and "compliance" in src:
        return "Criteria value"
    if ident in {"criteria", "criteriaProposal"} or ident.startswith("$defs/"):
        return "Schema shape"
    if ident in CONCEPTS or "concept:" in src:
        return "Concept"
    if ident in EXTENSION_SUBFIELDS or "extension-subfield" in src:
        return "Extension subfield"
    if ident in HEADER_ALIASES or "header-alias" in src.lower():
        return "Header alias"
    if ident.startswith("X-") or ident in {
        "Idempotency-Key",
        "Retry-After",
        "Authorization",
    }:
        if "alias" in src.lower():
            return "Header alias"
        return "Header"
    if "validation.md" in src and "heading:" in src:
        return "Validation rule"
    if ident in {
        "continue_task_without_this_step",
        "halt_and_hand_off",
        "retry_later",
        "halt",
    }:
        return "agentAction"
    if ident in {
        "AgentSuspended",
        "PendingAuthorization",
        "agent_suspended",
        "pending_authorization",
        "custody_unavailable",
        "unassigned",
        "unauthorized",
        "provisioning_defect",
        "incidentId",
        "autoResume",
        "202",
        "423",
        "403",
        "503",
        "401",
    }:
        return "Response identifier"
    if ident in {"Derived", "Configured", "Observed"}:
        return "Measurement kind"
    if "0009" in src:
        return "Document type"
    return "Unclassified"


def extract_from_schema(path: str, text: str, bag: dict[str, dict]) -> None:
    data = json.loads(text)
    enums: list[tuple[str, list[str]]] = []
    consts: list[tuple[str, str]] = []
    defs_keys: list[str] = []
    props: list[tuple[str, str]] = []
    walk_json(data, "$", enums, consts, defs_keys, props)

    def add(ident: str, source: str, force_class: str | None = None) -> None:
        e = bag.setdefault(
            ident,
            {"sources": [], "force_class": None, "schema_only_hint": True},
        )
        if source not in e["sources"]:
            e["sources"].append(source)
        if force_class:
            e["force_class"] = force_class

    for jpath, vals in enums:
        for v in vals:
            # annotate escalationReason / disposition path for classify()
            add(v, f"{path}:{jpath}")
    for jpath, val in consts:
        add(val, f"{path}:{jpath}")
        if re.fullmatch(r"(decision|attempt|outcome)-record/\d+\.\d+\.\d+", val):
            stem = val.split("/")[0].replace("-record", "").title()
            # Decision / Attempt / Outcome record types
            pretty = {
                "Decision": "Decision",
                "Attempt": "Attempt",
                "Outcome": "Outcome",
            }.get(stem, stem)
            if val.startswith("decision"):
                pretty = "Decision"
            elif val.startswith("attempt"):
                pretty = "Attempt"
            elif val.startswith("outcome"):
                pretty = "Outcome"
            add(pretty, f"{path}:{jpath}:record-type")
    for k in defs_keys:
        add(k, f"{path}:$defs/{k}")
        if k in {"criteria", "criteriaProposal"}:
            add(f"$defs/{k}", f"{path}:$defs/{k}:shape")
    for jpath, name in props:
        if name.startswith("x-ctier-") or name in VOCAB_FIELDS:
            add(name, f"{path}:{jpath}.properties.{name}")
        # nested fields under x-ctier-* objects (Extension subfield)
        if name in EXTENSION_SUBFIELDS and "x-ctier-" in jpath:
            add(name, f"{path}:{jpath}.properties.{name}:extension-subfield")
        # criteria dimension names as used in extensions
        if name in CRITERIA_DIMS:
            slug = {
                "blastRadius": "blast-radius",
                "dataSensitivity": "data-sensitivity",
                "complianceTrigger": "compliance-trigger",
            }.get(name, name)
            add(slug, f"{path}:{jpath}.properties.{name}:dim")


def extract_headings_and_prose(path: str, text: str, bag: dict[str, dict], titles: set[str]) -> None:
    raw = text
    body = strip_fences(raw)

    def add(ident: str, source: str) -> None:
        e = bag.setdefault(ident, {"sources": [], "force_class": None})
        if source not in e["sources"]:
            e["sources"].append(source)

    for line in body.splitlines():
        m = HEADING.match(line)
        if m:
            level, title = m.group(1), m.group(2).strip()
            if title.lower().startswith("ctier specification"):
                continue
            titles.add(title)
            # backtick tokens in heading
            for bt in BACKTICK.findall(title):
                add(bt, f"{path}:heading-backtick:{title}")
                titles.add(bt)
            # criterion lead
            for cm in CRITERION.finditer(title):
                add(f"C{cm.group(1)}", f"{path}:heading:{title}")
                titles.add(f"C{cm.group(1)}")
            for lm in LEVEL.finditer(title):
                add(f"Level {lm.group(1)}", f"{path}:heading:{title}")
                titles.add(f"Level {lm.group(1)}")
            for tm in TIER.finditer(title):
                add(f"Tier {tm.group(1)}", f"{path}:heading:{title}")
                titles.add(f"Tier {tm.group(1)}")
            for rm in REQUIREMENT.finditer(title):
                add(f"Requirement {rm.group(1)}", f"{path}:heading:{title}")
                titles.add(f"Requirement {rm.group(1)}")
            # validation rule / conceptual ### titles (short, not questions)
            if path.endswith("validation.md") and level == "###":
                if not title.endswith("?") and len(title) < 80:
                    add(title, f"{path}:heading:{title}")
            if path.endswith("headers.md") and level in ("###", "##"):
                # header sections titled with the header name
                pass
            # ADR catalogue style plain titles
            if "0009" in path and level.startswith("###"):
                add(title, f"{path}:heading:{title}")

        bm = BOLD_LEAD.match(line.strip())
        if bm:
            lead = bm.group(1)
            for cm in CRITERION.finditer(lead):
                ident = f"C{cm.group(1)}"
                add(ident, f"{path}:bold:{lead}")
                titles.add(ident)
            # `name` — definition leads
            for bt in BACKTICK.findall(lead):
                add(bt, f"{path}:bold-backtick:{lead}")
                titles.add(bt)

    # closed when-predicate keys in validation.md
    if path.endswith("validation.md"):
        if "pathEndsWithParameter" in body:
            keys = [
                "method",
                "pathEndsWithParameter",
                "responseIsCollection",
                "hasRequestBody",
                "securitySchemes",
                "tagIn",
                "operationIdMatches",
                "hasDeclaredReversal",
                "pathSegmentCount",
                "pathParameterCount",
            ]
            for k in keys:
                if k in body:
                    add(k, f"{path}:when-predicate-closed-list")

    # namespaces
    for ns in NAMESPACE.findall(body):
        add(ns, f"{path}:namespace")

    # x-ctier keys mentioned in prose
    for m in X_CTIER_KEY.finditer(body):
        add(m.group(0), f"{path}:prose-x-ctier")

    # Level / Tier / Requirement mentions that define vocabulary
    if path.endswith("README.md") or path.endswith("conformance.md"):
        for lm in LEVEL.finditer(body):
            add(f"Level {lm.group(1)}", f"{path}:prose-level")
        for lm in LEVEL_SLUG.finditer(body):
            add(f"level-{lm.group(1)}", f"{path}:prose-level-slug")
        for tm in TIER.finditer(body):
            add(f"Tier {tm.group(1)}", f"{path}:prose-tier")
        for rm in REQUIREMENT.finditer(body):
            add(f"Requirement {rm.group(1)}", f"{path}:prose-requirement")
        for cm in CRITERION.finditer(body):
            add(f"C{cm.group(1)}", f"{path}:prose-criterion")

    # measurement kinds if named
    for mk in ("Derived", "Configured", "Observed"):
        if re.search(rf"\b{mk}\b", body) and (
            "measurement" in body.lower() or "Derived bound" in body
        ):
            add(mk, f"{path}:measurement-kind")

    # response / agentAction tokens commonly listed
    for tok in (
        "continue_task_without_this_step",
        "halt_and_hand_off",
        "retry_later",
        "halt",
        "AgentSuspended",
        "PendingAuthorization",
        "agent_suspended",
        "pending_authorization",
        "custody_unavailable",
        "unassigned",
        "unauthorized",
        "provisioning_defect",
        "incidentId",
        "autoResume",
    ):
        if token_in_text(tok, body):
            add(tok, f"{path}:named-token")

    # status codes that finding 43 treated as response identifiers when titled
    if path.endswith("README.md") or path.endswith("headers.md") or path.endswith(
        "validation.md"
    ):
        for code in ("202", "423", "403", "503", "401"):
            # only if appearing as a response status discussion near C5/C9/etc.
            if re.search(rf"`{code}`|\b{code}\b", body):
                # avoid sucking every year/number: require nearby agent/response words
                pass

    # Concepts named in finding 43's Concept class
    for concept in CONCEPTS:
        if token_in_text(concept, body) or concept in body:
            add(concept, f"{path}:concept:{concept}")

    # Header aliases called out in headers.md
    if path.endswith("headers.md"):
        for alias in HEADER_ALIASES:
            if token_in_text(alias, body) or alias in body:
                add(alias, f"{path}:header-alias:{alias}")

    # Extension subfields tabulated in extensions.md
    if path.endswith("extensions.md"):
        for sub in EXTENSION_SUBFIELDS:
            if token_in_text(sub, body) or f"`{sub}`" in body:
                add(sub, f"{path}:extension-subfield:{sub}")


def extract_yaml(path: str, text: str, bag: dict[str, dict]) -> None:
    def add(ident: str, source: str) -> None:
        e = bag.setdefault(ident, {"sources": [], "force_class": None})
        if source not in e["sources"]:
            e["sources"].append(source)

    # header names: lines like `- name: X-Foo` or `name: x-ctier-...`
    for m in re.finditer(r"^\s*-?\s*name:\s*([A-Za-z0-9_*+-]+)\s*$", text, re.M):
        add(m.group(1), f"{path}:yaml-name")
    for m in X_CTIER_KEY.finditer(text):
        add(m.group(0), f"{path}:yaml-x-ctier")
    # enum-like lists under status / agentAction in examples embedded in yaml
    for tok in (
        "execute",
        "withhold",
        "refuse-and-suspend",
        "refuse-provisioning",
        "agent_suspended",
        "pending_authorization",
        "continue_task_without_this_step",
        "halt_and_hand_off",
        "retry_later",
        "X-Delegation-Chain",
        "X-Incident-Id",
        "X-Agent-Id",
        "Authorization",
        "Retry-After",
        "Idempotency-Key",
    ):
        if tok in text:
            add(tok, f"{path}:yaml-token")


def build_prose_index(files: dict[str, str]) -> list[str]:
    paras: list[str] = []
    for path, text in files.items():
        if not (path.endswith(".md")):
            continue
        for p in paragraphs(strip_fences(text)):
            paras.append(p)
    return paras


def has_requirement(ident: str, paras: Iterable[str]) -> bool:
    """Strict: whole-token + uppercase MUST/SHALL/REQUIRED same paragraph."""
    for p in paras:
        if not NORMATIVE.search(p):
            continue
        if token_in_text(ident, p):
            return True
    return False


def has_requirement_like_prose(ident: str, paras: Iterable[str]) -> bool:
    """Lenient rule from bucket B: obligation-like prose without RFC 2119.

    A paragraph that whole-token-matches the identifier and either:
    - uses ordinary-English obligation cues (lowercase must/shall/required,
      contradiction, closed-set, ordering, equality, validator-enforced, …)
      while lacking uppercase MUST/SHALL/REQUIRED, or
    - is a bold Excluded / definitional record lead naming the identifier.
    """
    for p in paras:
        if not token_in_text(ident, p) and not (
            ident in p and (f"**{ident}**" in p or f"`{ident}`" in p)
        ):
            # multi-word concepts / plain presence for short tokens already
            # handled by token_in_text; allow bold-lead record types
            if not (p.lstrip().startswith(f"**{ident}**") or f"**{ident}**" in p[:80]):
                continue
        present = (
            token_in_text(ident, p)
            or f"**{ident}**" in p
            or f"`{ident}`" in p
            or ident in p
        )
        if not present:
            continue
        if NORMATIVE.search(p):
            # uppercase RFC 2119 belongs to strict, not this rule
            continue
        if PROSE_OBLIGATION.search(p):
            return True
        if EXCLUDED_BOLD.search(p) and token_in_text(ident, p):
            return True
        # definitional ledger-record lead: **Attempt** — …
        if re.match(rf"^\*\*{re.escape(ident)}\*\*\s*[—-]", p.lstrip()):
            return True
    return False


def titled_own_name(ident: str, titles: set[str]) -> bool:
    for t in titles:
        # title starts with the identifier or `ident` / **ident**
        if t == ident or t.startswith(ident + " ") or t.startswith(ident + "—") or t.startswith(
            ident + " -"
        ):
            return True
        if t.startswith(f"`{ident}`") or t.startswith(f"**{ident}**"):
            return True
        if t.startswith(f"**`{ident}`**"):
            return True
        # C7 — ...
        if re.match(rf"^{re.escape(ident)}\s*[—-]", t):
            return True
    return False


def _section_bodies(files: dict[str, str]) -> dict[str, str]:
    """Map heading title -> body text until the next same-or-higher heading."""
    out: dict[str, str] = {}
    for path, text in files.items():
        if not path.endswith(".md"):
            continue
        body = strip_fences(text)
        lines = body.splitlines()
        headings: list[tuple[int, int, str]] = []
        for i, line in enumerate(lines):
            m = HEADING.match(line)
            if m:
                headings.append((i, len(m.group(1)), m.group(2).strip()))
        for j, (idx, level, title) in enumerate(headings):
            end = len(lines)
            for k in range(j + 1, len(headings)):
                if headings[k][1] <= level:
                    end = headings[k][0]
                    break
            chunk = "\n".join(lines[idx + 1 : end])
            out[title] = chunk
            for bt in BACKTICK.findall(title):
                out.setdefault(bt, chunk)
    return out


def _numbered_requirement_bodies(files: dict[str, str]) -> dict[str, str]:
    """Map 'Requirement N' -> item body under deployment-requirement lists."""
    out: dict[str, str] = {}
    for path, text in files.items():
        if not path.endswith(".md"):
            continue
        body = strip_fences(text)
        # Patterns: "2. **…**" or "### Requirement 2" already handled as headings.
        for m in re.finditer(
            r"(?m)^(?:#{1,6}\s*)?(?:Requirement\s+)?(\d+)\.\s+\*\*([^*]+)\*\*(.*?)(?=^(?:#{1,6}\s|(?:Requirement\s+)?\d+\.\s+\*\*|\Z))",
            body,
            re.S,
        ):
            num, title_bit, rest = m.group(1), m.group(2), m.group(3)
            key = f"Requirement {num}"
            out[key] = f"{title_bit}\n{rest}"
    return out


def class_coverage_credits(
    class_of: dict[str, str],
    paras: list[str],
    files: dict[str, str],
) -> set[str]:
    """Identifiers credited by the class-coverage rule (bucket A, rule 1).

    Rule: a requirement stated about a class covers a member when the
    requirement names the class by its own name or by a pattern the member
    matches, the obligation is satisfiable per member, and nothing in the
    requirement or its scope excludes that member.
    """
    credited: set[str] = set()
    joined = "\n".join(paras)
    prose = "\n".join(v for k, v in files.items() if k.endswith(".md"))

    def members(*classes: str) -> list[str]:
        return [i for i, c in class_of.items() if c in classes]

    # Criteria shape completeness — covers dimensions, values, $defs shapes.
    criteria_cover = False
    for p in paras:
        if "x-ctier-criteria" in p or "$defs/criteria" in p:
            if re.search(r"(?i)\ball five\b", p) or re.search(
                r"(?i)\bfields are required\b", p
            ):
                criteria_cover = True
                break
            if NORMATIVE.search(p) and re.search(r"(?i)\bcriteria\b", p):
                criteria_cover = True
                break
    if criteria_cover:
        for ident in members("Criteria value", "Criteria dimension", "Schema shape"):
            credited.add(ident)

    # Document-type / record-version class — named ctier-authored formats
    # validated as a class (schemas README + validation document-type talk).
    doc_class = False
    for p in paras:
        if re.search(r"(?i)document type|ctier-authored|schemas/", p) and (
            NORMATIVE.search(p) or PROSE_OBLIGATION.search(p) or "validat" in p.lower()
        ):
            doc_class = True
            break
    if "schemas/README.md" in files or any("schemas/README" in p for p in files):
        # schemas README existing + any validation language about named formats
        for p in paras:
            if "validat" in p.lower() and (
                "schema" in p.lower() or "document" in p.lower()
            ):
                doc_class = True
                break
    if doc_class:
        for ident in members("Document type", "Record version"):
            credited.add(ident)

    # Deployment-level class — ladder / Level N rungs bound by C-criteria.
    level_cover = False
    for p in paras:
        if re.search(r"(?i)\bLevel\s+\d+\b|\blevel-\d+\b", p) and (
            NORMATIVE.search(p)
            or re.search(r"(?i)enforc|conformance|adoption|ladder|deployment level", p)
        ):
            level_cover = True
            break
    if level_cover:
        for ident in members("Deployment level"):
            credited.add(ident)

    # Tier class — Who-executes / classification targets.
    tier_cover = False
    for p in paras:
        if re.search(r"(?i)\bTier\s+[1-4]\b", p) and (
            NORMATIVE.search(p) or re.search(r"(?i)who executes|classification", p)
        ):
            tier_cover = True
            break
    if tier_cover:
        for ident in members("Tier"):
            credited.add(ident)

    # Profile class — standard/constrained bounds.
    profile_cover = False
    for p in paras:
        if re.search(r"(?i)\bprofile\b|\bstandard\b|\bconstrained\b", p) and (
            NORMATIVE.search(p) or PROSE_OBLIGATION.search(p)
        ):
            profile_cover = True
            break
    if profile_cover:
        for ident in members("Profile"):
            credited.add(ident)

    # Generator mode class — bundle/fragments.
    gen_cover = False
    for p in paras:
        if ("bundle" in p or "fragments" in p) and (
            NORMATIVE.search(p) or PROSE_OBLIGATION.search(p)
        ):
            gen_cover = True
            break
    if gen_cover:
        for ident in members("Generator mode"):
            credited.add(ident)

    # Corpus-field class — only the dimensions the corpus table treats as
    # class members (not every Corpus field, e.g. not `placeholder`).
    corpus_dimension_members = {
        "profile",
        "deployment",
        "sequence",
        "appliedTierAtLeast",
    }
    corpus_cover = False
    for p in paras:
        if re.search(r"(?i)\b(profile|deployment|sequence|appliedTierAtLeast)\b", p) and (
            NORMATIVE.search(p)
            or PROSE_OBLIGATION.search(p)
            or re.search(r"(?i)corpus|dimension|bounded imprecision", p)
        ):
            corpus_cover = True
            break
    if corpus_cover:
        for ident in members("Corpus field"):
            if ident in corpus_dimension_members:
                credited.add(ident)

    # Deployment-requirement class: numbered items under the deployment
    # requirements list. Sibling items with MUST cover the class of labels
    # (forces Requirement 4, whose body has no uppercase MUST).
    dep_req = members("Deployment requirement")
    if any(
        NORMATIVE.search(_numbered_requirement_bodies(files).get(i, ""))
        for i in dep_req
    ):
        for ident in dep_req:
            credited.add(ident)

    # Header class is NOT wholesale-covered by one header's MUST (would
    # over-credit X-Delegation-Chain etc.). Authorization needs
    # criterion-linkage — not this rule.
    _ = (joined, prose)  # retained for future narrowing; silence lint
    return credited


def titled_section_body_credits(
    class_of: dict[str, str],
    files: dict[str, str],
) -> set[str]:
    """Identifiers credited when a titled section / list-label body has MUST.

    Forced by bucket A cases whose identifier is the section title or
    'Requirement N' label while the MUST sits in the body without repeating
    the title token.
    """
    credited: set[str] = set()
    bodies = _section_bodies(files)
    req_bodies = _numbered_requirement_bodies(files)

    for ident, klass in class_of.items():
        if klass not in {"Validation rule", "Deployment requirement"}:
            continue
        body = bodies.get(ident) or req_bodies.get(ident)
        if not body:
            continue
        if NORMATIVE.search(body):
            credited.add(ident)
    return credited


def requirement_like_credits(
    class_of: dict[str, str],
    paras: list[str],
    files: dict[str, str],
) -> set[str]:
    """Identifiers credited by requirement-like prose (bucket B rule)."""
    credited: set[str] = set()
    for ident in class_of:
        if has_requirement_like_prose(ident, paras):
            credited.add(ident)

    bodies = _section_bodies(files)
    # Titled validation-rule / extension-field sections whose body states
    # an obligation in ordinary English (lowercase must, Required table,
    # fail-closed, …) without uppercase MUST — and without repeating the
    # title token inside the body paragraphs the strict scanner walks.
    for ident, klass in class_of.items():
        body = bodies.get(ident)
        if not body:
            continue
        if klass == "Validation rule" and (
            PROSE_OBLIGATION.search(body)
            or re.search(r"(?m)^\s*\*\*[^*]{8,}\*\*", body)
            or re.search(
                r"(?i)\bno\b.{0,40}\bexists\b|\bctier does not\b|\bdoes not guess\b",
                body,
            )
        ):
            credited.add(ident)
        if klass in {"Extension field", "Extension subfield"}:
            # Field-section contract under extensions.md (type / optional /
            # Required table / descriptive norms), as bucket B credited.
            if (
                PROSE_OBLIGATION.search(body)
                or re.search(r"(?i)\boptional\b|\brequired\b|\bobject\b|\binteger\b|\bstring\b|\bboolean\b", body)
            ):
                credited.add(ident)
        if klass in {"Header", "Header alias", "Document key"} and PROSE_OBLIGATION.search(
            body
        ):
            credited.add(ident)
    return credited


def inventory_for_commit(repo: Path, commit: str) -> dict[str, Any]:
    paths = list_corpus_paths(repo, commit)
    files: dict[str, str] = {}
    for p in paths:
        try:
            files[p] = load_text(repo, commit, p)
        except subprocess.CalledProcessError:
            continue

    bag: dict[str, dict] = {}
    titles: set[str] = set()

    for path, text in files.items():
        if path.endswith(".json") and "/schemas/" in path:
            try:
                extract_from_schema(path, text, bag)
            except json.JSONDecodeError as e:
                bag.setdefault(f"__error_{path}", {"sources": [str(e)], "force_class": None})
        elif path.endswith((".yaml", ".yml")):
            extract_yaml(path, text, bag)
        elif path.endswith(".md"):
            extract_headings_and_prose(path, text, bag, titles)

    # drop internal error keys
    bag = {k: v for k, v in bag.items() if not k.startswith("__error_")}

    paras = build_prose_index(files)
    class_of: dict[str, str] = {}
    for ident, meta in bag.items():
        class_of[ident] = meta.get("force_class") or classify(ident, meta["sources"])

    class_hits = class_coverage_credits(class_of, paras, files)
    title_hits = titled_section_body_credits(class_of, files)
    prose_hits = requirement_like_credits(class_of, paras, files)

    rows: list[Row] = []
    for ident, meta in sorted(bag.items(), key=lambda kv: kv[0].lower()):
        sources = meta["sources"]
        klass = class_of[ident]
        strict = has_requirement(ident, paras)
        rules: list[str] = []
        if strict:
            rules.append(RULE_STRICT)
        if ident in class_hits:
            rules.append(RULE_CLASS)
        if ident in title_hits:
            rules.append(RULE_TITLE)
        if ident in prose_hits:
            rules.append(RULE_PROSE)
        # de-dup preserve order
        seen: set[str] = set()
        ordered_rules: list[str] = []
        for r in rules:
            if r not in seen:
                seen.add(r)
                ordered_rules.append(r)
        lenient = bool(ordered_rules)
        titled = titled_own_name(ident, titles)
        rows.append(
            Row(
                identifier=ident,
                class_name=klass,
                requirement_sentence=strict,
                titled_under_own_name=titled,
                sources=sources,
                requirement_sentence_strict=strict,
                requirement_sentence_lenient=lenient,
                lenient_rules=ordered_rules,
            )
        )

    by_class = Counter(r.class_name for r in rows)
    no_req_strict = [r for r in rows if not r.requirement_sentence_strict]
    no_req_lenient = [r for r in rows if not r.requirement_sentence_lenient]
    # difference: strict-no but lenient-yes, itemised by which non-strict rule
    # closed it. Primary = first of class-coverage, titled-section-body,
    # requirement-like-prose that fires (stable priority). Also list every
    # rule that fires (overlaps allowed; sums may exceed the gap).
    rule_priority = (RULE_CLASS, RULE_TITLE, RULE_PROSE)
    closed_primary: dict[str, list[str]] = defaultdict(list)
    closed_all: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r.requirement_sentence_strict or not r.requirement_sentence_lenient:
            continue
        non_strict = [x for x in r.lenient_rules if x != RULE_STRICT]
        for rule in non_strict:
            closed_all[rule].append(r.identifier)
        for rule in rule_priority:
            if rule in non_strict:
                closed_primary[rule].append(r.identifier)
                break
    # different name proxy: has strict requirement, not titled under own name
    diff_name = [r for r in rows if r.requirement_sentence_strict and not r.titled_under_own_name]

    full = run_git(repo, "rev-parse", commit).decode().strip()
    closed_counts = {k: len(v) for k, v in sorted(closed_primary.items())}
    closed_all_counts = {k: len(v) for k, v in sorted(closed_all.items())}
    summary = {
        "commit": full,
        "commit_arg": commit,
        "corpus_files": sorted(files.keys()),
        "identifiers": len(rows),
        "classes": len(by_class),
        "no_requirement_sentence": len(no_req_strict),  # strict; back-compat
        "no_requirement_sentence_strict": len(no_req_strict),
        "no_requirement_sentence_lenient": len(no_req_lenient),
        "strict_lenient_gap": len(no_req_strict) - len(no_req_lenient),
        "lenient_closes_by_rule_counts": closed_counts,
        "lenient_closes_by_rule_counts_all_firing": closed_all_counts,
        "stated_under_different_name_proxy": len(diff_name),
        "per_class": dict(sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0]))),
        "validation_md_recorded": {
            "identifiers": 195,
            "classes": 33,
            "no_requirement_sentence": 22,
            "stated_under_different_name": 3,
        },
        "agree_with_validation_md": {
            "identifiers": len(rows) == 195,
            "classes": len(by_class) == 33,
            "no_requirement_sentence": len(no_req_strict) == 22,
            "no_requirement_sentence_lenient": len(no_req_lenient) == 22,
            "stated_under_different_name": len(diff_name) == 3,
        },
    }
    return {
        "summary": summary,
        "rows": [asdict(r) for r in rows],
        "no_requirement_sentence": [r.identifier for r in no_req_strict],
        "no_requirement_sentence_strict": [r.identifier for r in no_req_strict],
        "no_requirement_sentence_lenient": [r.identifier for r in no_req_lenient],
        "lenient_closes_by_rule": {k: v for k, v in sorted(closed_primary.items())},
        "lenient_closes_by_rule_all_firing": {
            k: v for k, v in sorted(closed_all.items())
        },
        "stated_under_different_name_proxy": [r.identifier for r in diff_name],
    }


def render_md(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        f"# Identifier pass — derived at `{s['commit'][:12]}`",
        "",
        "Counting rule: `COUNTING-RULE.md` beside `identifier_pass.py`.",
        "",
        "## Totals vs validation.md",
        "",
        "| Total | Derived | Recorded (validation.md 1.16.0) | Agree? |",
        "|---|---:|---:|---|",
        f"| Identifiers | {s['identifiers']} | {s['validation_md_recorded']['identifiers']} | "
        f"{'yes' if s['agree_with_validation_md']['identifiers'] else 'no'} |",
        f"| Classes | {s['classes']} | {s['validation_md_recorded']['classes']} | "
        f"{'yes' if s['agree_with_validation_md']['classes'] else 'no'} |",
        f"| No requirement sentence (strict) | {s['no_requirement_sentence_strict']} | "
        f"{s['validation_md_recorded']['no_requirement_sentence']} | "
        f"{'yes' if s['agree_with_validation_md']['no_requirement_sentence'] else 'no'} |",
        f"| No requirement sentence (lenient) | {s['no_requirement_sentence_lenient']} | "
        f"{s['validation_md_recorded']['no_requirement_sentence']} | "
        f"{'yes' if s['agree_with_validation_md'].get('no_requirement_sentence_lenient') else 'no'} |",
        f"| Stated under a different name (proxy) | {s['stated_under_different_name_proxy']} | "
        f"{s['validation_md_recorded']['stated_under_different_name']} | "
        f"{'yes' if s['agree_with_validation_md']['stated_under_different_name'] else 'no'} |",
        "",
        f"Strict→lenient gap: **{s['strict_lenient_gap']}** "
        f"(itemised under `lenient_closes_by_rule`).",
        "",
        "### Lenient closes by rule (strict=no → lenient=yes)",
        "",
        "| Rule | Count |",
        "|---|---:|",
    ]
    for k, v in s.get("lenient_closes_by_rule_counts", {}).items():
        lines.append(f"| `{k}` | {v} |")
    if not s.get("lenient_closes_by_rule_counts"):
        lines.append("| *(none)* | 0 |")
    lines += [
        "",
        "## Per class",
        "",
        "| Class | Count |",
        "|---|---:|",
    ]
    for k, v in s["per_class"].items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "## Inventory",
        "",
        "| Identifier | Class | Strict? | Lenient? | Rules | Titled? |",
        "|---|---|---|---|---|---|",
    ]
    for r in result["rows"]:
        rules = ",".join(r.get("lenient_rules") or []) or "—"
        lines.append(
            f"| `{r['identifier']}` | {r['class_name']} | "
            f"{'yes' if r.get('requirement_sentence_strict', r['requirement_sentence']) else 'no'} | "
            f"{'yes' if r.get('requirement_sentence_lenient', r['requirement_sentence']) else 'no'} | "
            f"{rules} | "
            f"{'yes' if r['titled_under_own_name'] else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("commit", help="git commit-ish in the specification repo")
    ap.add_argument(
        "--repo",
        default=os.environ.get("CTIER_REPO", ""),
        help="path to public ctier repo (or set CTIER_REPO)",
    )
    ap.add_argument("--json", dest="json_out", help="write full JSON result")
    ap.add_argument("--md", dest="md_out", help="write markdown inventory")
    args = ap.parse_args(argv)

    repo = Path(args.repo) if args.repo else Path(
        "/Users/rinudhanaraj/m3pro/workspace/open-gw/ctier"
    )
    # Prefer sibling of ctier-engine when default empty
    if not args.repo:
        here = Path(__file__).resolve()
        # .../ctier-engine/engine/docs/audit/identifier-pass/identifier_pass.py
        sibling = here.parents[4].parent / "ctier"
        if sibling.is_dir():
            repo = sibling
        elif (here.parents[5] / "ctier").is_dir():
            repo = here.parents[5] / "ctier"

    if not (repo / ".git").exists() and not (repo / "spec").exists():
        print(f"error: not a ctier repo: {repo}", file=sys.stderr)
        return 2

    result = inventory_for_commit(repo, args.commit)
    summary = result["summary"]
    print(
        json.dumps(
            {
                "commit": summary["commit"],
                "identifiers": summary["identifiers"],
                "classes": summary["classes"],
                "no_requirement_sentence_strict": summary[
                    "no_requirement_sentence_strict"
                ],
                "no_requirement_sentence_lenient": summary[
                    "no_requirement_sentence_lenient"
                ],
                "strict_lenient_gap": summary["strict_lenient_gap"],
                "lenient_closes_by_rule_counts": summary[
                    "lenient_closes_by_rule_counts"
                ],
                "no_requirement_sentence": summary["no_requirement_sentence"],
                "stated_under_different_name_proxy": summary[
                    "stated_under_different_name_proxy"
                ],
                "agree_with_validation_md": summary["agree_with_validation_md"],
                "per_class": summary["per_class"],
            },
            indent=2,
        )
    )
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n")
    if args.md_out:
        Path(args.md_out).write_text(render_md(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
