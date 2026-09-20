"""Vendored schemas and examples must match SHA256SUMS. Syncing is a deliberate bump."""
from __future__ import annotations

import hashlib

from ctier.spec_loader import SPEC_DIR, spec_version


def _manifest() -> dict[str, str]:
    sums = {}
    for line in (SPEC_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split()
        sums[name] = digest
    return sums


def _corpus_files() -> list[str]:
    files = []
    for path in SPEC_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(SPEC_DIR).as_posix()
        if rel in {"VERSION", "SHA256SUMS", "README.md"}:
            continue
        if rel.startswith("schemas/") or rel.startswith("examples/") or rel == "consequence-tiered-api.yaml":
            files.append(rel)
    return sorted(files)


def test_targeted_spec_version():
    assert spec_version() == "1.4.0"


def test_vendored_corpus_digests_match_manifest():
    sums = _manifest()
    files = _corpus_files()
    assert files == sorted(sums), (
        "SHA256SUMS and ctier/spec corpus have different files: "
        f"missing={sorted(set(files) - set(sums))} extra={sorted(set(sums) - set(files))}"
    )
    for name, expected in sums.items():
        actual = hashlib.sha256((SPEC_DIR / name).read_bytes()).hexdigest()
        assert actual == expected, f"{name} drifted; bump VERSION and SHA256SUMS deliberately"
