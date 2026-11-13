"""Independent source-builder vectors; custody belongs to the native authenticated read."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pglast
import pytest
from pglast import ast
from pglast.stream import RawStream
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_source_native import (
    source_native_sources,
    source_native_sql,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.source_products import FrozenNativeSource, source_product_inputs

from .native_record_fixtures import private_source as private_source
from .native_record_fixtures import private_source_options as private_source_options


@pytest.fixture(scope="module")
def source_prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        source_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


@pytest.fixture
def source_builder_connection(semantic_db_engine):
    parsed = prepare_sql(source_native_sql(), source="original-source-helper-test")
    with semantic_db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            # Install only the pure builder; no source admission or persistent effect.
            connection.exec_driver_sql(parsed.excerpt(0), execution_options={"no_parameters": True})
            yield connection
        finally:
            transaction.rollback()


def inputs() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    text_ = "A valve opens."
    atom = dict(
        self_ref="#/texts/0",
        label="text",
        text=text_,
        orig=text_,
        prov=[dict(page_no=1, bbox={"l": 1.5})],
        parent={"$ref": "#/groups/0"},
        ignored_native_payload={"score": 0.25},
    )
    projection = dict(
        text=text_,
        pieces=[
            dict(
                kind="native_text",
                start=0,
                end=len(text_),
                item_ref="#/texts/0",
                source_field="text",
            )
        ],
        items=["#/texts/0"],
        ancestors=[],
        health={"formula_outcomes": [], "diagnostic_ref": {"task_id": 1}},
    )
    selectors = [dict(projection="b" * 64, native_pointer="#/texts/0", start=0, end=len(text_))]
    return atom, projection, selectors


def build(connection, projection, atoms, selectors):
    return connection.execute(
        text(
            "SELECT ops.ddo_native_source_body('document:semantic','#/groups/0','descendants',"
            "CAST(:projection AS jsonb),:digest,CAST(:items AS jsonb),"
            "CAST(:selectors AS jsonb))"
        ),
        dict(
            projection=json.dumps(projection),
            digest="b" * 64,
            items=json.dumps(atoms),
            selectors=json.dumps(selectors),
        ),
    ).scalar_one()


def test_native_source_helper_capture_and_compilation():
    assert {source.name for source in source_native_sources()} == {
        "native/data-operation-source-admission.sql",
        "native/data-operation-source-native.py",
    }
    parsed = prepare_sql(source_native_sql(), source="source")
    assert len(parsed.statements) == 3
    for index, raw in enumerate(parsed.statements):
        assert isinstance(raw.stmt, ast.CreateFunctionStmt)
        if index == 0:
            pglast.parse_plpgsql(parsed.excerpt(index))


def test_native_source_builder_matches_source_owner_without_legacy_diagnostic_salts(
    source_prepared, source_builder_connection
):
    atom, projection, selectors = inputs()
    view = SimpleNamespace(
        ref=SimpleNamespace(
            section_pointer="#/groups/0", membership="descendants", projection_digest="b" * 64
        ),
        text=projection["text"],
        pieces=projection["pieces"],
        items=[atom],
        health=projection["health"],
        ancestors=[],
    )
    expected = FrozenNativeSource.from_source_view(
        source_prepared, view, document="document:semantic", selectors=selectors
    )
    actual = build(source_builder_connection, projection, [atom], selectors)
    assert canonical_bytes(actual) == expected.content
    assert (
        b"bbox" not in expected.content
        and b"score" not in expected.content
        and b"task_id" not in expected.content
    )
    typed = source_builder_connection.execute(
        text("SELECT data.ddo_normalize(data.record_json_meaning(CAST(:body AS jsonb)))"),
        {"body": json.dumps(actual)},
    ).scalar_one()
    assert typed == semantic_value(actual)


@pytest.mark.parametrize("case", ["projection", "pointer", "bounds", "fractional", "gap"])
def test_native_source_builder_refuses_non_original_coordinates(source_builder_connection, case):
    atom, projection, selectors = inputs()
    if case == "projection":
        selectors[0]["projection"] = "c" * 64
    elif case == "pointer":
        selectors[0]["native_pointer"] = "#/missing"
    elif case == "bounds":
        selectors[0]["end"] = len(projection["text"]) + 1
    elif case == "fractional":
        selectors[0]["start"] = 1.5
    else:
        projection["pieces"][0]["start"] = 1
    with pytest.raises(DBAPIError, match="original source"):
        build(source_builder_connection, projection, [atom], selectors)


def test_authenticated_original_source_read_matches_original_published_custody(
    private_source, source_prepared, semantic_db_engine
):
    from corpus_structure.semantic.source_admission import acquire_original_source_selection

    from .original_source_fixture import completed_original_source_reference

    reference, selectors = completed_original_source_reference(private_source)
    with semantic_db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            for statement in prepare_sql(
                source_native_sql(), source="original-source-read"
            ).statements:
                connection.exec_driver_sql(
                    RawStream()(statement), execution_options={"no_parameters": True}
                )
            acquired = acquire_original_source_selection(
                connection, source_prepared, reference, selectors
            )
            actual = connection.execute(
                text(
                    "SELECT ops.ddo_original_source_view("
                    "CAST(:reference AS jsonb),CAST(:selectors AS jsonb))"
                ),
                dict(reference=reference.model_dump_json(), selectors=json.dumps(selectors)),
            ).scalar_one()
            assert canonical_bytes(actual["body"]) == acquired.source.content
            assert actual["subject"] == acquired.root.subject
            assert actual["original_source"] == acquired.root.original_source
            assert actual["analyzed_scope"] == json.loads(acquired.root.analyzed_scope)
            assert actual["meaning_body"] == semantic_value(acquired.source.value)
            assert actual["original_source"] == acquired.source.value["source"]["document"]
            assert actual["original_source"] != acquired.original_content_hash
            frozen_selection = acquired.selection().record()
            assert frozen_selection == {
                "reference": reference.model_dump(mode="json"),
                "selectors": selectors,
            }
        finally:
            transaction.rollback()


def test_native_source_retains_ordered_ancestry_links_and_typed_table_context(
    source_prepared, source_builder_connection
):
    atom, projection, selectors = inputs()
    atom.update(
        content_layer="body",
        children=[],
        captions=[{"$ref": "#/texts/caption"}],
        footnotes=[],
        references=[],
        marker="1.",
        enumerated=True,
    )
    atom["data"] = dict(
        num_rows=1,
        num_cols=1,
        orientation="horizontal",
        table_cells=[
            dict(
                text="A valve opens.",
                row_span=1,
                col_span=1,
                start_row_offset_idx=0,
                end_row_offset_idx=1,
                start_col_offset_idx=0,
                end_col_offset_idx=1,
                column_header=False,
                row_header=True,
                row_section=False,
                fillable=False,
                ref={"$ref": "#/texts/cell"},
                bbox={"l": 1.5},
            )
        ],
    )
    # Native Docling fields are plain integers; retain invalid grid values as
    # original facts for later geometry assessment rather than coercing/refusing them.
    atom["data"]["table_cells"][0]["row_span"] = -1
    ancestor: dict[str, Any] = dict(
        self_ref="#/groups/0",
        label="section",
        name="Actual section",
        level=1,
        content_layer="body",
        children=[{"$ref": "#/texts/0"}],
    )
    selectors[0]["native_pointer"] = "#/groups/0"
    projection["ancestors"] = [ancestor["self_ref"]]
    view = SimpleNamespace(
        ref=SimpleNamespace(
            section_pointer="#/groups/0", membership="descendants", projection_digest="b" * 64
        ),
        text=projection["text"],
        pieces=projection["pieces"],
        items=[atom],
        ancestors=[ancestor],
        health=projection["health"],
    )
    expected = FrozenNativeSource.from_source_view(
        source_prepared, view, document="document:semantic", selectors=selectors
    )
    actual = build(source_builder_connection, projection, [ancestor, atom], selectors)
    assert canonical_bytes(actual) == expected.content
    assert actual["ancestors"][0]["children"] == ["#/texts/0"]
    assert actual["items"][0]["data"]["table_cells"][0]["row_header"] is True
    assert actual["items"][0]["data"]["table_cells"][0]["row_span"] == -1
    assert "bbox" not in actual["items"][0]["data"]["table_cells"][0]
    native = {item["self_ref"]: item for item in expected.native_items()}
    assert native["#/groups/0"]["children"] == [{"$ref": "#/texts/0"}]
    assert native["#/texts/0"]["data"]["table_cells"][0]["ref"] == {"$ref": "#/texts/cell"}
    index = expected.selector_index()
    assert index.matches({"native_pointer": "#/groups/0"}, "#/texts/0") is True
    assert index.matches({"native_pointer": "#/different"}, "#/texts/0") is False
    ancestor["parent"] = {"$ref": "#/unretained"}
    unresolved = FrozenNativeSource.from_source_view(
        source_prepared, view, document="document:semantic", selectors=selectors
    )
    assert (
        unresolved.selector_index().matches({"native_pointer": "#/different"}, "#/texts/0") is None
    )
    ancestor.pop("parent")
    before = actual["source"]["projection"]
    ancestor["name"] = "Different original section"
    changed = build(source_builder_connection, projection, [atom, ancestor], selectors)
    assert changed["source"]["projection"] != before


def test_computed_projection_uses_same_language_value_without_legacy_source_identity(
    source_prepared,
):
    atom, projection, selectors = inputs()
    native = FrozenNativeSource.from_projection(
        source_prepared,
        document="document:semantic",
        section_pointer="#/groups/0",
        membership="descendants",
        text=projection["text"],
        pieces=projection["pieces"],
        items=[atom],
        ancestors=[],
        recognition=[],
    )
    selectors = [
        {**selector, "projection": native.value["source"]["projection"]} for selector in selectors
    ]
    native = FrozenNativeSource.from_projection(
        source_prepared,
        document="document:semantic",
        section_pointer="#/groups/0",
        membership="descendants",
        text=projection["text"],
        pieces=projection["pieces"],
        items=[atom],
        ancestors=[],
        recognition=[],
        selectors=selectors,
    )
    view = SimpleNamespace(
        ref=SimpleNamespace(
            section_pointer="#/groups/0", membership="descendants", projection_digest="b" * 64
        ),
        text=projection["text"],
        pieces=projection["pieces"],
        items=[atom],
        ancestors=[],
        health=projection["health"],
    )
    original = FrozenNativeSource.from_source_view(
        source_prepared,
        view,
        document="document:semantic",
        selectors=[{**selector, "projection": "b" * 64} for selector in selectors],
    )
    assert native.content == original.content
    assert native.value["source"]["document"] == "document:semantic"
    assert native.value["items"][0]["prov"] == [{"page_no": 1}]
    assert b"task_id" not in native.content and b"bbox" not in native.content
