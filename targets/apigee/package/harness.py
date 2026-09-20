#!/usr/bin/env python3
"""Differential harness for an Apigee deployment of the generated bundle.

Without --proxy: runs the reference oracle against the corpus.
With --proxy: compares that oracle to HTTP observations using the same
status-to-disposition projection as the Kong adapter. Supply a bearer token
your organisation will accept.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "engine"))

from ctier.compose import compose
from ctier.conformance import HANDWRITTEN_DIR
from ctier.conformance.adapter import ReferenceAdapter
from ctier.conformance.kong import KongAdapter
from ctier.conformance.runner import dump_report, run_corpus
from ctier.corpus import build_corpus, load_extras
from ctier.spec_loader import SPEC_DIR

NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", choices=("level-2", "level-3"), default="level-3")
    parser.add_argument("--proxy", help="base URL of the deployed Apigee proxy")
    parser.add_argument("--token", help="bearer token the proxy will accept")
    parser.add_argument("--out", help="write the conformance report here")
    args = parser.parse_args()

    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    extras = load_extras(HANDWRITTEN_DIR / "reference.yaml")
    corpus = build_corpus(qualified, extras, deployment=args.deployment)
    adapters = [ReferenceAdapter(qualified, deployment=args.deployment)]
    if args.proxy:
        deployed = KongAdapter(
            args.proxy,
            qualified_spec=qualified,
            token=args.token,
        )
        deployed.name = "apigee"
        adapters.append(deployed)

    report = run_corpus(corpus, adapters)
    rendered = dump_report(report)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    print(f"agree={report['agree']} adapters={report['adapters']} cases={len(report['cases'])}")
    if not report["agree"]:
        for row in report["cases"]:
            if not row.get("agree"):
                print(json.dumps(row, indent=2)[:2000])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
