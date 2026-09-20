"""The deployment digest must not be emitted under a composition-named surface.

Two named exceptions, both C13 of the composed API, not the deployment
digest. Edit this list deliberately; pattern-matching around them is
how the rename stopped at the schema boundary.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import yaml

from ctier.compose import compose
from ctier.corpus import build_corpus
from ctier.cover import cover
from ctier.custody.service import persist
from ctier.custody.store import Store
from ctier.generate import generate
from ctier.spec_loader import SPEC_DIR
from tests.golden_util import NOW
from tests.test_custody import _payload

# Exactly two. Compose-time compositionDigest (manifest and coverage
# report share it). Corpus document field composition (C13 of the API
# the cases classify; the conformance report copies it).
NAMED_EXCEPTIONS = (
    "compose-manifest.compositionDigest",
    "conformance-corpus.composition",
)


def _hits(obj, digest: str, path: str = "") -> list[str]:
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = f"{path}.{key}" if path else str(key)
            if "composition" in str(key).lower() and value == digest:
                found.append(here)
            found.extend(_hits(value, digest, here))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            found.extend(_hits(value, digest, f"{path}[{i}]"))
    return found


def _xml_hits(text: str, digest: str) -> list[str]:
    found = []
    root = ET.fromstring(text)
    for assign in root.iter():
        if assign.tag.split("}")[-1] != "AssignVariable":
            continue
        name = value = None
        for child in assign:
            tag = child.tag.split("}")[-1]
            if tag == "Name":
                name = (child.text or "").strip()
            elif tag == "Value":
                value = (child.text or "").strip()
        if name and "composition" in name.lower() and value == digest:
            found.append(name)
    return found


def test_no_surface_names_the_deployment_digest_composition():
    assert NAMED_EXCEPTIONS == (
        "compose-manifest.compositionDigest",
        "conformance-corpus.composition",
    )
    qualified, manifest = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
    coverage = cover(qualified, None, NOW)
    corpus = build_corpus(qualified)
    apigee = generate(qualified)
    kong = generate(qualified, target="kong")
    apisix = generate(qualified, target="apisix")
    digest = json.loads(apigee["ctier-generate.json"])["deploymentDigest"]
    assert json.loads(kong["ctier-generate.json"])["deploymentDigest"] == digest
    assert json.loads(apisix["ctier-generate.json"])["deploymentDigest"] == digest

    # The two exceptions exist, and they are the other object.
    assert "compose-manifest.compositionDigest" in NAMED_EXCEPTIONS
    assert manifest["compositionDigest"] != digest
    assert coverage["compositionDigest"] == manifest["compositionDigest"]
    assert "conformance-corpus.composition" in NAMED_EXCEPTIONS
    assert corpus["composition"] != digest
    assert corpus["composition"] == manifest["compositionDigest"]

    illegal = []
    illegal.extend(_hits(json.loads(apigee["ctier-generate.json"]), digest, "apigee-meta"))
    illegal.extend(_hits(json.loads(kong["ctier-generate.json"]), digest, "kong-meta"))
    illegal.extend(_hits(json.loads(apisix["ctier-generate.json"]), digest, "apisix-meta"))
    illegal.extend(_hits(yaml.safe_load(kong["kong.yaml"]), digest, "kong.yaml"))
    illegal.extend(_hits(yaml.safe_load(apisix["apisix.yaml"]), digest, "apisix.yaml"))
    for path, text in apigee.items():
        if path.endswith(".xml"):
            illegal.extend(
                f"{path}:{name}" for name in _xml_hits(text, digest)
            )
        if "composition" in path.lower() and digest in text:
            illegal.append(path)
    store = Store()
    persist(
        store,
        _payload(deploymentDigest=digest),
        now=NOW,
        new_id=lambda: "corr-1",
    )
    row = store.get("corr-1")
    columns = {
        col[1]
        for col in store._conn.execute("PRAGMA table_info(pending)").fetchall()
    }
    illegal.extend(
        f"pending.{name}" for name in columns if "composition" in name.lower()
    )
    illegal.extend(_hits(dict(row), digest, "pending-row"))
    from ctier.custody.service import review_queue

    illegal.extend(_hits(review_queue(store, now=NOW), digest, "review-queue"))
    store.close()
    assert not illegal, (
        "deployment digest emitted under a composition-named surface: "
        f"{illegal}. NAMED_EXCEPTIONS is {list(NAMED_EXCEPTIONS)}"
    )
