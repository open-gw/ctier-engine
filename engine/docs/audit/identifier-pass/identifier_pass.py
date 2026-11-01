#!/usr/bin/env python3
"""Mechanised identifier pass (audit task 89).

Reads the specification at a given git commit and derives an
identifier inventory under the counting rule in COUNTING-RULE.md
beside this script.

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
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

NORMATIVE = re.compile(r"\b(MUST(?:\s+NOT)?|SHALL(?:\s+NOT)?|REQUIRED)\b")
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
    requirement_sentence: bool
    titled_under_own_name: bool
    sources: list[str] = field(default_factory=list)
    notes: str = ""


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
    for p in paras:
        if not NORMATIVE.search(p):
            continue
        if token_in_text(ident, p):
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
    rows: list[Row] = []
    for ident, meta in sorted(bag.items(), key=lambda kv: kv[0].lower()):
        sources = meta["sources"]
        klass = meta.get("force_class") or classify(ident, sources)
        req = has_requirement(ident, paras)
        titled = titled_own_name(ident, titles)
        # also treat a dedicated ### `ident` heading captured as title set member
        rows.append(
            Row(
                identifier=ident,
                class_name=klass,
                requirement_sentence=req,
                titled_under_own_name=titled,
                sources=sources,
            )
        )

    by_class = Counter(r.class_name for r in rows)
    no_req = [r for r in rows if not r.requirement_sentence]
    # different name proxy: has requirement, not titled under own name
    diff_name = [r for r in rows if r.requirement_sentence and not r.titled_under_own_name]

    full = run_git(repo, "rev-parse", commit).decode().strip()
    summary = {
        "commit": full,
        "commit_arg": commit,
        "corpus_files": sorted(files.keys()),
        "identifiers": len(rows),
        "classes": len(by_class),
        "no_requirement_sentence": len(no_req),
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
            "no_requirement_sentence": len(no_req) == 22,
            "stated_under_different_name": len(diff_name) == 3,
        },
    }
    return {
        "summary": summary,
        "rows": [asdict(r) for r in rows],
        "no_requirement_sentence": [r.identifier for r in no_req],
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
        f"| No requirement sentence | {s['no_requirement_sentence']} | "
        f"{s['validation_md_recorded']['no_requirement_sentence']} | "
        f"{'yes' if s['agree_with_validation_md']['no_requirement_sentence'] else 'no'} |",
        f"| Stated under a different name (proxy) | {s['stated_under_different_name_proxy']} | "
        f"{s['validation_md_recorded']['stated_under_different_name']} | "
        f"{'yes' if s['agree_with_validation_md']['stated_under_different_name'] else 'no'} |",
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
        "| Identifier | Class | Requirement sentence? | Titled under own name? |",
        "|---|---|---|---|",
    ]
    for r in result["rows"]:
        lines.append(
            f"| `{r['identifier']}` | {r['class_name']} | "
            f"{'yes' if r['requirement_sentence'] else 'no'} | "
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
