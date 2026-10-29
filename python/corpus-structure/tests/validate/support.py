"""Batches for the `validate` tests (P0-S-2), loaded by file path (`--import-mode=importlib`).

The independent controls are external batches (coordinator decision 24):
- `fixtures/s0`: the v1 reference as authored batches with their frames;
- their stored form on production renditions of the vendored pages, through A0's parse (the
  production quote cascade), so the stored checks see real spans and canonical text;
- the spike's stored v1 reference, with its names prefixed (S1's test helpers).
The worked examples have no rendition, so `spanless_stored` gives them a stored form whose spans
are placeholders: the rules read no span.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

from corpus_structure.core.batch import CORE_QUALIFIERS, AuthoredBatch, CitationFrame
from corpus_structure.schema.compile import CompiledSchema

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent
REPO = TESTS.parents[2]
S0 = REPO / "fixtures/s0"
S0_UNITS = (
    "T1-leadin",
    "T1-dfn1",
    "T2",
    "T3",
    "T4",
    "U5",
    "U6",
    "U7",
    "U8",
    "U9",
    "U10",
    "U11",
    "U12",
)


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


@cache
def packs_helpers() -> ModuleType:
    return _load("validate_packs_helpers", TESTS / "schema/test_packs.py")


@cache
def llm_env() -> ModuleType:
    return _load("validate_llm_env", TESTS / "llm/conftest.py")


def s0(name: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    """An s0 fixture's authored batch, frame and page."""
    raw = json.loads((S0 / f"{name}.json").read_text(encoding="utf-8"))
    return raw["batch"], raw["frame"], raw["provenance"]["rendition"]["page"]


@cache
def _stored_s0(name: str) -> tuple[str, str]:
    from corpus_structure.methods.llm.parse import parse
    from corpus_structure.schema.lookup import name_map
    from corpus_structure.schema.pack import DOMAINS, load_pack

    env = llm_env()
    batch, frame, page = s0(name)
    view = env.page_view(page)
    names = dict(name_map([load_pack(DOMAINS / "statistics")]).to_prefixed)
    result = parse(
        view, AuthoredBatch.model_validate(batch), CitationFrame.model_validate(frame), names
    )
    stored = result.stored.model_dump(mode="json", by_alias=True)
    return json.dumps(stored), view.content.canonical_text


def stored_s0(name: str) -> tuple[dict[str, Any], str]:
    """The fixture's stored form on its production rendition (A0's parse) and the canonical text."""
    text, canonical = _stored_s0(name)
    return json.loads(text), canonical


def stored_v1(unit: str, compiled: CompiledSchema) -> dict[str, Any]:
    """The spike's stored v1 reference batch, names prefixed (X2-01)."""
    helpers = packs_helpers()
    raw = json.loads((helpers.S0R2 / "reference_v1" / f"{unit}.json").read_text(encoding="utf-8"))
    return helpers.prefixed_names(raw, compiled)


V1_UNITS: tuple[str, ...] = (
    "T1",
    "T2",
    "T3",
    "T4",
    "U5",
    "U6",
    "U7",
    "U8",
    "U9",
    "U10",
    "U11",
    "U12",
)


def spanless_stored(batch: dict[str, Any], compiled: CompiledSchema) -> dict[str, Any]:
    """A stored form of an authored batch with placeholder spans and segments (for batches with no
    rendition): names prefixed through the name map, every anchored text at [0, 1)."""
    names = compiled.names.to_prefixed
    b = copy.deepcopy(batch)
    span = {"start": 0, "end": 1}

    def anchored(node: Any) -> Any:
        if isinstance(node, dict):
            out = {k: anchored(v) for k, v in node.items() if k not in ("sentence", "quote")}
            if node.get("t") == "phrase" or node.get("op") in ("phrase", "unsupported"):
                out |= span
            if node.get("t") == "enum":
                out["enum"] = names[node["enum"]]
            return out
        if isinstance(node, list):
            return [anchored(v) for v in node]
        return node

    for e in b.get("entities", []):
        e["type"] = names[e["type"]]
        e["identity"] = {names[k]: v for k, v in e.get("identity", {}).items()}
        if e["scope"] == "local":
            e["scope_segment"] = "seg:x"
    for s in b.get("statements", []):
        if s.get("anchor") == "outside":
            s["descriptor"] = span | (
                {"target": s["descriptor"]["target"]} if "target" in s["descriptor"] else {}
            )
        else:
            s["anchor"] = ["seg:x"]
            kinds = {
                m.text: m.stored for m in compiled.lookup.version_sets["StatementKind"].members
            }
            s["kind"] = kinds[s["kind"]]
    modalities = {m.text: m.stored for m in compiled.lookup.version_sets["ClaimModality"].members}
    for c in b.get("claims", []):
        c["predicate"] = names[c["predicate"]]
        quals = {}
        for k, v in c.get("qualifiers", {}).items():
            if k in CORE_QUALIFIERS:
                if k == "modality":
                    v = modalities[v]
                if k == "scope":
                    v = {"extent": v, "segment": "seg:x"}
                quals[f"core:{k}"] = anchored(v)
            else:
                quals[names[k]] = anchored(v)
        c["qualifiers"] = quals
        c["object"] = anchored(c["object"])
        c["evidence"] = [{"role": ev["role"], **span} for ev in c.get("evidence", [])]
    b["unsupported"] = [
        {"local_ref": u["local_ref"], "reason": u["reason"], **span}
        for u in b.get("unsupported", [])
    ]
    b["rendition"] = "ren:" + "0" * 32
    return b
