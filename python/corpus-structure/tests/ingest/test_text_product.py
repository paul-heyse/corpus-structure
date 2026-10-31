from __future__ import annotations

import json
from itertools import pairwise

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
    result = text_product_payload(
        canonical,
        root=ROOT,
        math_ranges=[(a, b, r"\(", r"\)")],
        macro_sources=[MacroSource("page-definitions", definitions, read)],
        fallback_macros={r"\f": MacroDef(nargs=2, default="F", body="#1+#2")},
        fallback_source_ref="release:math.macros",
    )
    reps = {r["representation_id"]: r for r in result["representations"]}
    assert definitions.encode() in text_product_artifacts(result)
    assert reps["canonical"]["text_content"] == canonical
    assert reps["parse:0"]["text_content"] == r"\f{x}"
    assert reps["expanded:0"]["text_content"] == r"\(D+x+x\)"
    rows = [r for r in result["components"] if r["representation_id"] == "canonical"]
    assert [(r["category"], r["start_offset"], r["end_offset"]) for r in rows][:2] == [
        ("text", 0, 8),
        ("whitespace", 8, 9),
    ]
    assert rows[0]["start_offset"] == 0 and rows[-1]["end_offset"] == len(canonical)
    assert all(left["end_offset"] == right["start_offset"] for left, right in pairwise(rows))
    assert {d["name"] for d in result["dependencies"]} >= {
        "source",
        "page-definitions",
        "release:math.macros",
    }
    assert json.loads(reps["release:math.macros"]["text_content"])[r"\f"]["default"] == "F"
    binds = [r for r in result["relationships"] if r["kind"] == "binds"]
    assert len(binds) == 1
    definition = next(
        e
        for e in result["endpoints"]
        if e["relationship_id"] == binds[0]["relationship_id"] and e["role"] == "definition"
    )
    definition_node = next(n for n in result["nodes"] if n["node_id"] == definition["node_id"])
    assert definition_node["representation_id"] == "page-definitions"
    root_endpoints = [e for e in result["mapping_endpoints"] if e.get("target_task_id") is not None]
    assert all(
        e["dependency_name"] == "source"
        and e["target_task_id"] == 7
        and e["target_content_digest"] == "a" * 64
        for e in root_endpoints
    )


def test_fallback_requires_named_custody() -> None:
    with pytest.raises(ValueError, match="explicit dependency source reference"):
        text_product_payload("x", root=ROOT, fallback_macros={r"\x": MacroDef(body="x")})


def test_structured_fallback_does_not_reparse_or_repair_its_body() -> None:
    result = text_product_payload(
        r"\f",
        root=ROOT,
        math_ranges=[(0, 2, None, None)],
        fallback_macros={r"\f": MacroDef(body="{")},
        fallback_source_ref="release:math.macros",
    )
    reps = {r["representation_id"]: r for r in result["representations"]}
    assert reps["expanded:0"]["text_content"] == "{"
    event = next(n for n in result["nodes"] if n["kind"] == "macro_definition")
    assert json.loads(event["value"])["body"] == "{"


def test_unrequested_expansion_retains_macro_spec_and_explicit_unknown_structure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("structure-only adapter expanded a macro")

    monkeypatch.setattr("corpus_structure.core.text_structure.expand", forbidden)
    result = text_product_payload(
        r"\f{x}",
        root=ROOT,
        math_ranges=[(0, 5, None, None)],
        fallback_macros={r"\f": MacroDef(nargs=1, body="#1+#1")},
        fallback_source_ref="release:math.macros",
        structure=True,
        expand_macros=False,
    )
    assert not any(r["kind"] == "expanded" for r in result["representations"])
    definition = next(
        n for n in result["nodes"] if n["kind"] == "macro_definition" and n["name"] == r"\f"
    )
    assert json.loads(definition["value"]) == {"nargs": 1, "default": None, "body": "#1+#1"}
    view = next(n for n in result["nodes"] if n["kind"] == "parse_view")
    assert (view["start_offset"], view["end_offset"]) == (0, 5)
    assert json.loads(view["value"]) == {
        "structure_outcome": "invalid",
        "issues": ["unknown-command"],
    }
    assert not any(n["kind"] == "macro" for n in result["nodes"])


def test_canonical_prose_runs_avoid_character_rows_and_preserve_exact_math_tokens():
    prefix = "Descriptive prose. " * 80
    math = r"\( x_{1} % $z \)"
    canonical = prefix + math + " Tail paragraph."
    start, end = len(prefix), len(prefix) + len(math)
    value = text_product_payload(
        canonical,
        root=ROOT,
        math_ranges=[(start, end, r"\(", r"\)")],
        structure=False,
        expand_macros=False,
    )
    rows = [r for r in value["components"] if r["representation_id"] == "canonical"]
    assert len(rows) == 4 * 80 + 14 + 4
    assert len(rows) < len(canonical) // 4
    assert [(r["category"], canonical[r["start_offset"] : r["end_offset"]]) for r in rows[:4]] == [
        ("text", "Descriptive"),
        ("whitespace", " "),
        ("text", "prose."),
        ("whitespace", " "),
    ]
    mathematical = [
        (r["category"], r["start_offset"] - start, r["end_offset"] - start)
        for r in rows
        if start <= r["start_offset"] < end
    ]
    assert mathematical == [
        ("control_symbol", 0, 2),
        ("whitespace", 2, 3),
        ("character", 3, 4),
        ("character", 4, 5),
        ("group_open", 5, 6),
        ("character", 6, 7),
        ("group_close", 7, 8),
        ("whitespace", 8, 9),
        ("character", 9, 10),
        ("whitespace", 10, 11),
        ("character", 11, 12),
        ("character", 12, 13),
        ("whitespace", 13, 14),
        ("control_symbol", 14, 16),
    ]
    assert rows[0]["start_offset"] == 0 and rows[-1]["end_offset"] == len(canonical)
    assert all(a["end_offset"] == b["start_offset"] for a, b in pairwise(rows))


def test_canonical_partition_preserves_supplied_nonmath_categories_and_boundaries():
    from corpus_structure.core.text_structure import TextComponent

    canonical = "before [raw] ?? after"
    value = text_product_payload(
        canonical,
        root=ROOT,
        canonical_regions=[
            TextComponent("text", 0, 3),
            TextComponent("markup", 7, 12),
            TextComponent("unknown", 13, 15),
        ],
        structure=False,
        expand_macros=False,
    )
    rows = [r for r in value["components"] if r["representation_id"] == "canonical"]
    canonical_rep = next(
        r for r in value["representations"] if r["representation_id"] == "canonical"
    )
    assert (
        canonical_rep["partition_state"] == "complete"
        and canonical_rep["recognition_state"] == "partial"
    )
    assert [(r["category"], r["start_offset"], r["end_offset"]) for r in rows] == [
        ("text", 0, 3),
        ("text", 3, 6),
        ("whitespace", 6, 7),
        ("markup", 7, 12),
        ("whitespace", 12, 13),
        ("unknown", 13, 15),
        ("whitespace", 15, 16),
        ("text", 16, 21),
    ]


def test_macro_event_policy_is_typed_and_request_consumer_ignores_value_json():
    from corpus_structure.semantic.parsing_products import prepare_layered_product
    from corpus_structure.semantic.parsing_requests import _page_sources

    definitions = r"\newcommand{\f}{xy}"
    value = text_product_payload(
        "x",
        root=ROOT,
        macro_sources=[
            MacroSource("defs", definitions, read_macros(definitions, source_ref="defs"))
        ],
    )
    event = next(n for n in value["nodes"] if n["kind"] == "macro_event")
    assert event["macro_event"] == dict(
        status="accepted",
        selected=True,
        command=r"\newcommand",
        name_ranges=[dict(start_offset=12, end_offset=14)],
        body_ranges=[dict(start_offset=16, end_offset=17), dict(start_offset=17, end_offset=18)],
        default_ranges=[],
        count_ranges=[],
    )
    event["value"] = '{"status":"ignored"}'  # Explanatory text cannot change effective policy.
    checked = prepare_layered_product(value).values()
    assert _page_sources(checked)[0].read.events[0].status == "accepted"
    event["macro_event"].update(status="ignored", selected=False)
    event["value"] = '{"status":"accepted"}'
    assert (
        _page_sources(prepare_layered_product(value).values())[0].read.events[0].status == "ignored"
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda n: n.pop("macro_event"),
        lambda n: n["macro_event"].update(status="invented"),
        lambda n: n["macro_event"].update(selected="true"),
        lambda n: n["macro_event"].update(status="ignored", selected=True),
        lambda n: n["macro_event"]["body_ranges"][0].update(end_offset=n["end_offset"] + 1),
        lambda n: n["macro_event"]["body_ranges"].reverse(),
        lambda n: n["macro_event"]["body_ranges"][0].update(end_offset=16),
    ],
)
def test_macro_event_metadata_rejects_invalid_policy_or_parent_ranges(change):
    from corpus_structure.semantic.parsing_products import prepare_layered_product

    definitions = r"\newcommand{\f}{xy}"
    value = text_product_payload(
        "x",
        root=ROOT,
        macro_sources=[
            MacroSource("defs", definitions, read_macros(definitions, source_ref="defs"))
        ],
    )
    event = next(n for n in value["nodes"] if n["kind"] == "macro_event")
    change(event)
    with pytest.raises(ValueError):
        prepare_layered_product(value)
