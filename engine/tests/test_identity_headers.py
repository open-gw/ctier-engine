"""x-ctier-approver and x-ctier-agent are not emitted by any surface.

The 13h naming guard's exception list is for composition-named fields.
These two names are not exceptions to that list. They must not appear
on any generated artefact or on custody's execute request.
"""
from __future__ import annotations

from pathlib import Path

from ctier.compose import compose
from ctier.custody.execute import (
    HEADER_AGENT,
    HEADER_APPROVER,
    HEADER_CORRELATION,
    RecordingExecutor,
)
from ctier.custody.service import decide, persist
from ctier.custody.store import Store
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_custody import _payload

REPO = Path(__file__).resolve().parents[2]
FORBIDDEN = (HEADER_AGENT, HEADER_APPROVER)


def _mentions(text: str) -> list[str]:
    lower = text.lower()
    return [name for name in FORBIDDEN if name in lower]


def test_no_surface_emits_approver_or_agent_headers():
    qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    hits = []
    for target in ("apigee", "kong", "apisix"):
        files = generate(qualified, target=target)
        for path, text in files.items():
            found = _mentions(text)
            if found:
                hits.append(f"generate/{target}/{path}:{found}")

    handler = (REPO / "targets" / "kong" / "plugin" / "handler.lua").read_text(
        encoding="utf-8"
    )
    if _mentions(handler):
        hits.append("handler.lua")

    store = Store()
    persist(store, _payload(), now=NOW, new_id=lambda: "corr-1")
    executor = RecordingExecutor()
    decide(
        store, "corr-1", "approve", "analyst-1",
        now=NOW, executor=executor, service_token="custody-service",
    )
    assert len(executor.calls) == 1
    sent = executor.calls[0]
    lower = {k.lower(): v for k, v in sent.headers.items()}
    for name in FORBIDDEN:
        if name in lower:
            hits.append(f"execute-request:{name}")
    assert sent.headers[HEADER_CORRELATION] == "corr-1"
    store.close()
    assert not hits, (
        "identity headers emitted: "
        f"{hits}. These names have no exception list."
    )
