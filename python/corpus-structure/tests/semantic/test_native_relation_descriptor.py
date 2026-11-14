"""Named physical row shapes evolve without treating attnum as a wire contract."""

from pathlib import Path

from sqlalchemy import BigInteger, Column, Identity, Integer, MetaData, Table, Text, text

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_candidate import _declared_physical_catalog
from corpus_structure.semantic.native_products import relation_descriptor
from corpus_structure.semantic.source_view_native import _admission_descriptor, native_admission_sql


def test_named_shape_retains_type_nullability_default_identity_and_primary_key_order():
    relation = Table(
        "row",
        MetaData(),
        Column("z", Text, nullable=True),
        Column("id", BigInteger, Identity(always=True), primary_key=True),
        Column("n", Integer, nullable=False, server_default=text("42")),
        schema="test",
    )
    descriptor = relation_descriptor(relation)
    assert descriptor["columns"] == [
        dict(name="id", type="bigint", not_null=True, default=None, identity="a", generated=""),
        dict(name="n", type="integer", not_null=True, default="42", identity="", generated=""),
        dict(name="z", type="text", not_null=False, default=None, identity="", generated=""),
    ]
    assert descriptor["primary_key"] == ["id"]


def test_forward_admission_refreshes_existing_named_shapes_from_current_model():
    root = Path(__file__).resolve().parents[2]
    prior = root / "semantic_alembic/versions/semantic_um_model_20261102_admission.sql"
    frozen = _admission_descriptor(prior.read_text())
    current = _admission_descriptor(native_admission_sql("", base_admission=prior.read_text()))
    for name in ("kb.source_view", "ops.native_region_artifact"):
        before = next(row for row in frozen["tables"] if row["relation"] == name)
        after = next(row for row in current["tables"] if row["relation"] == name)
        assert {column["name"] for column in before["columns"]}.isdisjoint(
            {"native_build_id", "native_revision_id"}
        )
        fields = {column["name"]: column for column in after["columns"]}
        assert [column["name"] for column in after["columns"]] == sorted(fields)
        for column in ("native_build_id", "native_revision_id"):
            assert fields[column] == dict(
                name=column, type="text", not_null=True, default=None, identity="", generated=""
            )
        assert any(
            key["columns"]
            == ["native_build_id", "native_task_id", "native_product_key", "native_content_digest"]
            and key["remote_columns"] == ["build_id", "task_id", "product_key", "logical_digest"]
            for key in after["foreign_keys"]
        )


def test_forward_descriptor_freezes_declared_visual_geometry_and_indexes(commit_db_engine):
    root = Path(__file__).resolve().parents[2]
    prior = root / "semantic_alembic/versions/semantic_dma_05_13_final_admission.sql"
    with commit_db_engine.begin() as conn:
        catalog = _declared_physical_catalog(conn, metadata)
        assert conn.scalar(text("SELECT to_regclass('pg_temp.semantic_candidate_catalog')")) is None
    current = _admission_descriptor(
        native_admission_sql("", base_admission=prior.read_text(), physical_catalog=catalog)
    )
    locator_indexes = {
        item["definition"].split(" USING ")[1]
        for item in current["indexes"]
        if item["relation"] == "kb.pdf_visual_locator"
    }
    assert locator_indexes == {
        "btree (task_id, product_key, artifact_digest, kind, ordinal)",
        "btree (task_id, product_key, artifact_digest, parent_id, ordinal)",
        "gist (artifact_scope, source_x, source_y) "
        "WHERE ((source_x IS NOT NULL) AND (source_y IS NOT NULL))",
    }
    shapes = {shape["relation"]: shape for shape in current["tables"]}
    assert "kb.pdf_visual_cell" in shapes and "ops.pdf_visual_index" in shapes
    generated = {
        column["name"]: column
        for column in shapes["kb.pdf_visual_locator"]["columns"]
        if column["generated"]
    }
    assert set(generated) == {"artifact_scope", "source_x", "source_y"}
    assert generated["artifact_scope"]["type"] == "int8range"
    for column, coordinate in (("source_x", "left"), ("source_y", "top")):
        assert generated[column]["type"] == "numrange"
        assert coordinate + "'::text" in generated[column]["default"]
