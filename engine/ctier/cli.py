# Copyright 2026 Rinu Dhanaraj
# SPDX-License-Identifier: Apache-2.0
"""Thin shells: parse arguments, call one library function, render the result."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .backend import NullBackend
from .compose import compose
from .cover import dump_coverage_json, evaluate_gate, cover, render_coverage_text
from .errors import ComposeError, RecommendError
from .ledger.store import Ledger
from .migrate import dump_proposals, propose_migrations
from .recommend import apply_recommendations, recommend
from .rules import DEFAULT_RULES


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ctier")
    sub = parser.add_subparsers(dest="command", required=True)

    compose_p = sub.add_parser("compose", help="compose a description with overlays")
    compose_p.add_argument("description")
    compose_p.add_argument("--overlay", action="append", default=[], dest="overlays")
    compose_p.add_argument("--out")
    compose_p.add_argument("--strict", action="store_true")

    recommend_p = sub.add_parser("recommend", help="propose classifications")
    recommend_p.add_argument("description")
    recommend_p.add_argument("--rules")
    recommend_p.add_argument("--apply", action="store_true")
    recommend_p.add_argument("--out")

    cover_p = sub.add_parser("cover", help="coverage report and optional gate")
    cover_p.add_argument("qualified")
    cover_p.add_argument("--recommendations")
    cover_p.add_argument(
        "--fail-on",
        choices=sorted(("none", "absent", "recommended")),
        default="none",
    )
    cover_p.add_argument("--format", choices=("json", "text"), default="text")

    migrate_p = sub.add_parser(
        "migrate",
        help="propose tier migrations from a ledger; never applies them",
    )
    migrate_p.add_argument("ledger")
    migrate_p.add_argument("--out")
    return parser


def _dump_yaml(document: dict) -> str:
    return yaml.safe_dump(
        document,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )


def _write(path: str | None, text: str) -> None:
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _run_compose(args: argparse.Namespace, now: datetime) -> int:
    qualified, manifest = compose(
        Path(args.description),
        [Path(p) for p in args.overlays],
        now,
        strict=args.strict,
    )
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "qualified.yaml").write_text(_dump_yaml(qualified), encoding="utf-8")
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        sys.stdout.write(_dump_yaml(qualified))
    return 0


def _run_recommend(args: argparse.Namespace, now: datetime) -> int:
    rules = Path(args.rules) if args.rules else DEFAULT_RULES
    recs = recommend(Path(args.description), rules, NullBackend(), now)
    if args.apply:
        doc, report = apply_recommendations(Path(args.description), recs, now)
        _write(args.out, _dump_yaml(doc))
        sys.stderr.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return 0
    _write(args.out, _dump_yaml(recs))
    return 0


def _run_cover(args: argparse.Namespace, now: datetime) -> int:
    recs = Path(args.recommendations) if args.recommendations else None
    report = cover(Path(args.qualified), recs, now)
    rendered = (
        dump_coverage_json(report)
        if args.format == "json"
        else render_coverage_text(report)
    )
    sys.stdout.write(rendered)
    return evaluate_gate(report, args.fail_on)


def _run_migrate(args: argparse.Namespace, now: datetime) -> int:
    ledger = Ledger(path=args.ledger)
    try:
        document = propose_migrations(ledger, now=now)
    finally:
        ledger.close()
    _write(args.out, dump_proposals(document))
    return 0


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return 0
        return 2
    clock = now if now is not None else datetime.now(timezone.utc)
    try:
        if args.command == "compose":
            return _run_compose(args, clock)
        if args.command == "recommend":
            return _run_recommend(args, clock)
        if args.command == "cover":
            return _run_cover(args, clock)
        if args.command == "migrate":
            return _run_migrate(args, clock)
    except (ComposeError, RecommendError, OSError, ValueError, yaml.YAMLError) as exc:
        print(exc, file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
