"""Model generation, actual static consumer checks and invocation-bound preparation."""

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pytest
from sqlalchemy import Column, MetaData, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateColumn

from corpus_structure.schema.relational import render_typed_column_class
from corpus_structure.semantic import _typed_columns
from corpus_structure.semantic.analytics import compile_projection, compile_sql
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.pdf_record_model import record_arrow_schema, record_write_profile
from corpus_structure.semantic.query import SnapshotBinding
from corpus_structure.semantic.typed_generation import generated_source

from .test_analytics import prepared_inputs

REPO = Path(__file__).resolve().parents[4]


def test_generated_surface_is_current_and_attaches_existing_table():
    assert Path(_typed_columns.__file__).read_text() == generated_source()
    assert _typed_columns.data_occurrence is metadata.tables["data.occurrence"]


def test_one_modeled_field_updates_static_native_and_arrow_products():
    changed = MetaData()
    target = metadata.tables["ops.pdf_stage_native"].to_metadata(changed)
    target.append_column(Column("modeled_extra", Text, nullable=False))
    generated = render_typed_column_class("ChangedColumns", target.columns)
    assert "modeled_extra: Named[str]" in generated
    native = str(CreateColumn(target.c.modeled_extra).compile(dialect=postgresql.dialect()))
    assert "modeled_extra TEXT NOT NULL" in native
    arrow = record_arrow_schema(target.fullname, model=changed)
    assert arrow.field("modeled_extra") == pa.field(
        "modeled_extra",
        pa.string(),
        nullable=False,
        metadata={"postgresql": "text", "constraints": "{}"},
    )
    write_profile = record_write_profile(target.fullname, release_id="r", model=changed)
    assert write_profile.fields[-1].wire_type == "text"


def test_shape_reused_with_independent_invocation_values_and_changed_profile(monkeypatch):
    from corpus_structure.semantic import analytics

    prepared = replace(prepared_inputs()[2])
    original = analytics._prepare_projection_shapes
    calls = []

    def prepare(scale):
        calls.append(scale)
        return original(scale)

    monkeypatch.setattr(analytics, "_prepare_projection_shapes", prepare)
    first = compile_projection(
        prepared, SnapshotBinding(prepared.release_id, "one", 1, "capture-1")
    )
    second = compile_projection(
        prepared, SnapshotBinding(prepared.release_id, "two%_o'", 2, "capture-2")
    )
    assert calls == [12]
    assert first.projection_id == second.projection_id
    for value, projection in (("one", first), ("two%_o'", second)):
        sql = compile_sql(projection.relations[0].statement)
        assert ("'one'" if value == "one" else "'two%_o'''") in sql
        capture = projection.relations[0].schema.metadata[b"cs.capture"]
        assert capture == projection.binding.capture_id.encode()
    monkeypatch.setattr(analytics, "COMPILER_VERSION", "changed-compiler")
    third = compile_projection(prepared, replace(first.binding, capture_id="new"))
    assert calls == [12, 12]
    assert third.projection_id != first.projection_id


@pytest.mark.skipif(shutil.which("pyrefly") is None, reason="blocked: pyrefly not on PATH")
def test_actual_static_consumer_refuses_wrong_column_and_incompatible_type(tmp_path):
    source = tmp_path / "consumer.py"
    source.write_text(
        "from sqlalchemy import select\n"
        "from sqlalchemy.sql.elements import ColumnElement\n"
        "from corpus_structure.semantic._typed_columns import data_occurrence_columns\n"
        "def needs_text(value: ColumnElement[str]) -> None: pass\n"
        "def needs_integer(value: ColumnElement[int]) -> None: pass\n"
        "needs_text(data_occurrence_columns.occurrence_id)\n"
        "select(data_occurrence_columns.occurrence_id)\n"
    )
    pyrefly = shutil.which("pyrefly")
    assert pyrefly is not None
    command = [pyrefly, "check", "--config", str(REPO / "pyproject.toml"), str(source)]
    good = subprocess.run(command, capture_output=True, text=True, check=False)
    assert good.returncode == 0, good.stdout + good.stderr
    with source.open("a") as stream:
        stream.write("select(data_occurrence_columns.absent_modeled_column)\n")
        stream.write("needs_integer(data_occurrence_columns.occurrence_id)\n")
    bad = subprocess.run(command, capture_output=True, text=True, check=False)
    output = bad.stdout + bad.stderr
    assert bad.returncode != 0
    assert "absent_modeled_column" in output
    assert "needs_integer" in output


def test_two_native_invocations_reuse_preparation_and_return_independent_rows(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    from sqlalchemy import insert

    from corpus_structure.semantic import analytics
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import EntityRow, PublicationBatch, publish_batch
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import PreparationProfile

    bundle, dependencies, cached = prepared_inputs()
    prepared = replace(cached)
    pins = ("first", "second%_o'")
    with semantic_db_engine.begin() as conn:
        persist_release(
            conn, bundle, dependencies, PreparationProfile(version="semantic-2"), prepared
        )
        conn.execute(insert(table("data.project")).values(project_id="prepared-pins"))
        for realization in pins:
            conn.execute(
                insert(table("data.realization")).values(
                    realization_id=realization,
                    release_id=prepared.release_id,
                    project_id="prepared-pins",
                )
            )
    for realization in pins:
        publish_batch(
            semantic_writer_engine,
            PublicationBatch(
                prepared.release_id,
                realization,
                "batch:" + realization,
                entity=(EntityRow("entity:" + realization),),
            ),
        )
    original = analytics._prepare_projection_shapes
    prepared_scales = []

    def prepare(scale):
        prepared_scales.append(scale)
        return original(scale)

    monkeypatch.setattr(analytics, "_prepare_projection_shapes", prepare)
    for realization in pins:
        projection = compile_projection(
            prepared, SnapshotBinding(prepared.release_id, realization, 1, "capture:" + realization)
        )
        statement = next(row.statement for row in projection.relations if row.name == "entity")
        with semantic_db_engine.connect() as conn:
            assert [row["entity_id"] for row in conn.execute(statement).mappings()] == [
                "entity:" + realization
            ]
    assert prepared_scales == [12]
