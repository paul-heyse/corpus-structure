"""Stored native fields remain readable when their analytical implementation is unavailable."""

import json
from dataclasses import replace
from unittest.mock import MagicMock

import psycopg
import pytest
from sqlalchemy import Connection

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic import analysis_contracts, releases, source_views
from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.operations import BoundReader, OperationConflict
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import PreparationError, RegistryRow


@pytest.fixture
def retained_release(monkeypatch):
    inputs = trusted_execution_inputs()
    model = compile_execution_model(inputs)
    base = prepare_release(inputs.schema)
    prepared = replace(
        base,
        execution_model_id=model.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", model.model_id, model.content),
        ),
    )
    # Preserve an admitted archive while independently making its runtime implementation differ.
    monkeypatch.setattr(analysis_contracts, "_semantic_implementation_digests", lambda: ())
    return prepared


def test_retained_reader_preserves_pins_before_text_preparation_gate(retained_release):
    conn = MagicMock(spec=Connection)
    reader = BoundReader(conn, 17, retained_release, analysis=False)
    assert reader.prepared is retained_release
    # Native pins remain readable; the actual text preparation boundary checks its bytes.
    with pytest.raises(PreparationError, match="admitted semantic determinant bytes"):
        analysis_contracts.prepare_text_policy(retained_release)
    conn.execute.assert_not_called()


def test_retained_view_hydrates_pins_but_refuses_layout_and_outside_run(
    retained_release, monkeypatch
):
    conn = MagicMock(spec=Connection)
    driver = MagicMock(spec=psycopg.Connection)
    driver.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
    conn.connection.driver_connection = driver
    item = {"self_ref": "#/texts/0", "label": "formula", "orig": "x", "text": "x"}
    row = dict(
        id=31,
        key="native-section",
        document_id=5,
        native_task_id=23,
        native_product_key="organized",
        native_content_digest="a" * 64,
        native_build_id="current-published-native",
        native_revision_id="current-published-native",
        section_pointer="#/groups/0",
        membership="direct",
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        analysis_eligible=True,
        release_id=retained_release.release_id,
        projection=dict(
            text="x",
            pieces=[dict(kind="native_text", item_ref="#/texts/0", start=0, end=1)],
            items=["#/texts/0"],
            ancestors=[],
            health={"formula_outcomes": [{"pointer": "#/texts/0", "outcome": "succeeded"}]},
        ),
    )

    def execute(statement, *args):
        result = MagicMock()
        result.__enter__.return_value = result
        sql = str(statement)
        if "to_regclass" in sql or "to_regprocedure" in sql:
            result.scalar_one.return_value = True
        elif "ops.read_pdf_published_revision" in sql:
            assert args == ()
            assert statement.compile().params == {
                "task_id": 23,
                "product_key": "organized",
                "logical_digest": "a" * 64,
            }
            # Independent ordered native result; the generated materializer must preserve this pin.
            result.one_or_none.return_value = (
                "current-published-native",
                23,
                "organized",
                "a" * 64,
                retained_release.release_id,
                "d" * 64,
                "e" * 64,
                "f" * 64,
                "0" * 64,
                "native",
            )
        elif "ops.read_pdf_published_items" in sql:
            assert args == ()
            assert statement.compile().params == {
                "task_id": 23,
                "product_key": "organized",
                "content_digest": "a" * 64,
                "pointers": ("#/texts/0",),
            }
            result.__iter__.return_value = iter(
                (
                    (
                        "current-published-native",
                        "current-published-native",
                        "#/texts/0",
                        1,
                        "formula",
                        "#/groups/0",
                        "#/groups/0",
                        "body",
                        "x",
                        json.dumps(item),
                    ),
                )
            )
        else:
            assert "kb.source_view" in sql
            result.mappings.return_value.one.return_value = row
        return result

    conn.execute.side_effect = execute
    monkeypatch.setattr(releases, "open_release", lambda *args: retained_release)

    def native_identity(conn, task, key, digest, *, cancellation=None):
        assert (task, key, digest) == (23, "organized", "a" * 64)
        assert cancellation is None
        return {"kind": "native"}

    monkeypatch.setattr(
        "corpus_structure.semantic.pdf_storage._pdf_product_identity", native_identity
    )
    with pytest.raises(PreparationError, match="admitted semantic determinant bytes"):
        source_views.load_source_view(conn, 31)

    retained = source_views.load_source_view(conn, 31, analysis=False)
    assert retained.text == "x"
    assert retained.items == (item,)
    assert retained.integrated_context is None
    assert retained.ref.native_product.content_digest == "a" * 64
    assert retained.ref.projection_digest == "b" * 64
    with pytest.raises(ValueError, match="cannot prepare analytical layout"):
        retained.layout_for(SentenceConfig())
    with pytest.raises(ValueError, match="cannot prepare analytical layout"):
        _ = retained.layout

    def selected_views(selected_conn, run_id, *, read_budget=None, source_view_id=None):
        assert selected_conn is conn and run_id == 17
        assert read_budget is None
        return tuple(
            ref for ref in (retained.ref,) if source_view_id is None or ref.id == source_view_id
        )

    monkeypatch.setattr(source_views, "selected_source_views", selected_views)
    reader = BoundReader(conn, 17, retained_release, analysis=False)
    assert reader.source_view(31).items == (item,)
    with pytest.raises(OperationConflict, match="outside bound run"):
        reader.source_view(32)
