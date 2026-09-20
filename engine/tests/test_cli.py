"""CLI is a thin shell: parse, call the library, render. Exit codes 0, 1, 2."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from ctier.cli import main
from ctier.compose import compose
from ctier.cover import cover, dump_coverage_json
from ctier.recommend import recommend
from ctier.backend import NullBackend
from ctier.rules import DEFAULT_RULES

NOW = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)


def _write_spec(path: Path, ops: dict) -> Path:
    path.write_text(
        yaml.safe_dump(
            {"openapi": "3.1.0", "info": {"title": "c", "version": "1"}, "paths": ops},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_migrate_has_no_apply_flag():
    from ctier.cli import _parser

    parser = _parser()
    args = parser.parse_args(["migrate", "ledger.sqlite"])
    assert not hasattr(args, "apply")
    migrate = parser._subparsers._group_actions[0].choices["migrate"]
    assert "--apply" not in migrate.format_help()


def test_migrate_cli_matches_library(tmp_path: Path, capsys):
    from ctier.ledger.records import decision_record
    from ctier.ledger.store import Ledger
    from ctier.migrate import dump_proposals, propose_migrations

    digest = "sha256:" + "ab" * 32
    path = tmp_path / "ledger.sqlite"
    ledger = Ledger(path=str(path))
    ledger.append_decision(decision_record(
        operation_anchor="getBalance",
        agent_id="agent-a",
        correlation_scope="task-1",
        applied_tier=1,
        escalation_reason="none",
        disposition="execute",
        idempotency_key="k" * 64,
        deployment_digest=digest,
        declared_tier=1,
        record_id="d1",
        timestamp="2026-09-07T12:00:00Z",
    ))
    ledger.close()
    expected = dump_proposals(propose_migrations(Ledger(path=str(path)), now=NOW))
    assert main(["migrate", str(path)], now=NOW) == 0
    assert capsys.readouterr().out == expected


def test_fail_on_defaults_to_none():
    from ctier.cli import _parser

    args = _parser().parse_args(["cover", "qualified.yaml"])
    assert args.fail_on == "none"


def test_exit_0_when_gate_not_tripped(tmp_path: Path, capsys):
    spec = _write_spec(
        tmp_path / "q.yaml",
        {"/x": {"get": {"operationId": "x", "x-ctier-tier": 1, "x-ctier-status": "declared"}}},
    )
    assert main(["cover", str(spec), "--fail-on", "absent", "--format", "json"], now=NOW) == 0
    capsys.readouterr()


def test_exit_1_when_gate_trips(tmp_path: Path, capsys):
    spec = _write_spec(tmp_path / "q.yaml", {"/x": {"post": {"operationId": "x"}}})
    assert main(["cover", str(spec), "--fail-on", "absent", "--format", "json"], now=NOW) == 1
    capsys.readouterr()


def test_exit_2_on_usage_or_input_error(capsys):
    assert main(["cover"], now=NOW) == 2
    assert main(["cover", "/no/such/qualified.yaml"], now=NOW) == 2
    capsys.readouterr()


def test_library_cover_matches_cli_stdout(tmp_path: Path, capsys):
    spec = _write_spec(
        tmp_path / "q.yaml",
        {
            "/x": {"get": {"operationId": "x", "x-ctier-tier": 1, "x-ctier-status": "declared"}},
            "/y": {"post": {"operationId": "y"}},
        },
    )
    report = cover(spec, None, NOW)
    assert main(["cover", str(spec), "--format", "json"], now=NOW) == 0
    assert capsys.readouterr().out == dump_coverage_json(report)


def test_level0_cli_matches_library(tmp_path: Path, capsys):
    from ctier.spec_loader import SPEC_DIR

    description = SPEC_DIR / "consequence-tiered-api.yaml"
    qualified, _manifest = compose(description, [], NOW)
    recs = recommend(description, DEFAULT_RULES, NullBackend(), NOW)
    expected = dump_coverage_json(cover(qualified, recs, NOW))

    out = tmp_path / "out"
    rec_path = tmp_path / "recs.yaml"
    assert main(["compose", str(description), "--out", str(out)], now=NOW) == 0
    assert main(["recommend", str(description), "--out", str(rec_path)], now=NOW) == 0
    assert main(
        [
            "cover",
            str(out / "qualified.yaml"),
            "--recommendations",
            str(rec_path),
            "--format",
            "json",
        ],
        now=NOW,
    ) == 0
    assert capsys.readouterr().out == expected
