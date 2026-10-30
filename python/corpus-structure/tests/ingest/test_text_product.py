from __future__ import annotations

import json

import pytest

from corpus_structure.core.evidence import MacroDef
from corpus_structure.ingest.macros import MacroSource, read_macros
from corpus_structure.ingest.text_product import text_product_artifacts, text_product_payload

ROOT = dict(task_id=7, product_key="source", content_digest="a" * 64)


def test_portable_product_keeps_complete_source_and_definition_dependencies() -> None:
    definitions = r"\newcommand{\f}[2][D]{#1+#2+#2}"
    read = read_macros(definitions, source_ref="page-definitions")
    canonical = r"Heading. \(\f{x}\)  Tail."
    a, b = canonical.index(r"\("), canonical.index(r"\)") + 2
    result = text_product_payload(canonical, root=ROOT, math_ranges=[(a, b, r"\(", r"\)")],
        macro_sources=[MacroSource("page-definitions", definitions, read)],
        fallback_macros={r"\f": MacroDef(nargs=2, default="F", body="#1+#2")},
        fallback_source_ref="release:math.macros")
    reps = {r["representation_id"]: r for r in result["representations"]}
    assert definitions.encode() in text_product_artifacts(result)
    assert reps["canonical"]["text_content"] == canonical
    assert reps["parse:0"]["text_content"] == r"\f{x}"
    assert reps["expanded:0"]["text_content"] == r"\(D+x+x\)"
    rows = [r for r in result["components"] if r["representation_id"] == "canonical"]
    assert [(r["start_offset"], r["end_offset"]) for r in rows][:2] == [(0, 1), (1, 2)]
    assert rows[0]["start_offset"] == 0 and rows[-1]["end_offset"] == len(canonical)
    assert all(left["end_offset"] == right["start_offset"] for left, right in zip(rows, rows[1:]))
    assert {d["name"] for d in result["dependencies"]} >= {"source", "page-definitions", "release:math.macros"}
    assert json.loads(reps["release:math.macros"]["text_content"])[r"\f"]["default"] == "F"
    binds = [r for r in result["relationships"] if r["kind"] == "binds"]
    assert len(binds) == 1
    definition = next(e for e in result["endpoints"] if e["relationship_id"] == binds[0]["relationship_id"] and e["role"] == "definition")
    definition_node = next(n for n in result["nodes"] if n["node_id"] == definition["node_id"])
    assert definition_node["representation_id"] == "page-definitions"
    root_endpoints = [e for e in result["mapping_endpoints"] if e.get("target_task_id") is not None]
    assert all(e["dependency_name"] == "source" and e["target_task_id"] == 7 and e["target_content_digest"] == "a" * 64 for e in root_endpoints)


def test_fallback_requires_named_custody() -> None:
    with pytest.raises(ValueError, match="explicit dependency source reference"):
        text_product_payload("x", root=ROOT, fallback_macros={r"\x": MacroDef(body="x")})


def test_structured_fallback_does_not_reparse_or_repair_its_body() -> None:
    result = text_product_payload(r"\f", root=ROOT, math_ranges=[(0, 2, None, None)],
        fallback_macros={r"\f": MacroDef(body="{")}, fallback_source_ref="release:math.macros")
    reps = {r["representation_id"]: r for r in result["representations"]}
    assert reps["expanded:0"]["text_content"] == "{"
    event = next(n for n in result["nodes"] if n["kind"] == "macro_definition")
    assert json.loads(event["value"])["body"] == "{"


def test_expansion_demand_can_be_disabled_without_losing_declared_structure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("structure-only adapter expanded a macro")
    monkeypatch.setattr("corpus_structure.core.text_structure.expand", forbidden)
    result = text_product_payload(r"\f{x}", root=ROOT, math_ranges=[(0, 5, None, None)],
        fallback_macros={r"\f": MacroDef(nargs=1, body="#1+#1")},
        fallback_source_ref="release:math.macros", structure=True, expand_macros=False)
    assert not any(r["kind"] == "expanded" for r in result["representations"])
    macro = next(n for n in result["nodes"] if n["kind"] == "macro" and n["name"] == "f")
    assert (macro["start_offset"], macro["end_offset"]) == (0, 5)
