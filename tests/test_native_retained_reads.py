"""Stored native fields remain readable when their analytical implementation is unavailable."""

from dataclasses import replace
from unittest.mock import MagicMock

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
    monkeypatch.setattr(analysis_contracts, "_runtime_implementation_digests", lambda: ())
    return prepared


def test_retained_reader_skips_analysis_admission_but_cannot_prepare_inputs(retained_release):
    conn = MagicMock(spec=Connection)
    with pytest.raises(PreparationError, match="admitted implementation bytes"):
        BoundReader(conn, 17, retained_release)

    reader = BoundReader(conn, 17, retained_release, analysis=False)
    assert reader.prepared is retained_release
    with pytest.raises(OperationConflict, match="cannot prepare analytical inputs"):
        reader.content(1)
    conn.execute.assert_not_called()


def test_retained_view_hydrates_pins_but_refuses_layout_and_outside_run(
    retained_release, monkeypatch
):
    conn = MagicMock(spec=Connection)
    item = {"self_ref": "#/texts/0", "label": "formula", "orig": "x", "text": "x"}
    row = dict(
        id=31,
        key="native-section",
        document_id=5,
        native_task_id=23,
        native_product_key="organized",
        native_content_digest="a" * 64,
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
        if "unnest" in str(statement):
            result.mappings.return_value = [dict(pointer="#/texts/0", item=item)]
        else:
            result.mappings.return_value.one.return_value = row
        return result

    conn.execute.side_effect = execute
    monkeypatch.setattr(releases, "open_release", lambda *args: retained_release)
    with pytest.raises(PreparationError, match="admitted implementation bytes"):
        source_views.load_source_view(conn, 31)

    retained = source_views.load_source_view(conn, 31, analysis=False)
    assert retained.text == "x"
    assert retained.items == (item,)
    assert retained.ref.native_product.content_digest == "a" * 64
    assert retained.ref.projection_digest == "b" * 64
    with pytest.raises(ValueError, match="cannot prepare analytical layout"):
        retained.layout_for(SentenceConfig())
    with pytest.raises(ValueError, match="cannot prepare analytical layout"):
        _ = retained.layout

    monkeypatch.setattr(source_views, "selected_source_views", lambda *args: (retained.ref,))
    reader = BoundReader(conn, 17, retained_release, analysis=False)
    assert reader.source_view(31).items == (item,)
    with pytest.raises(OperationConflict, match="outside bound run"):
        reader.source_view(32)
