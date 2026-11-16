"""Named physical row shapes evolve without treating attnum as a wire contract."""

from sqlalchemy import BigInteger, Column, Identity, Integer, MetaData, Table, Text, text

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_admission import _admission_descriptor, native_admission_sql
from corpus_structure.semantic.native_authoring import _declared_physical_catalog
from corpus_structure.semantic.native_products import relation_descriptor


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




def test_current_descriptor_freezes_declared_visual_geometry_and_indexes(semantic_bare_engine):
    from corpus_structure.semantic.native_products import admission_kernel
    from corpus_structure.semantic.target_installation import (
        capture_target_installation,
        target_admission_descriptor,
    )

    capture = capture_target_installation(metadata)
    with semantic_bare_engine.begin() as conn:
        catalog = _declared_physical_catalog(conn, metadata)
        assert conn.scalar(text("SELECT to_regclass('pg_temp.semantic_candidate_catalog')")) is None
    current = _admission_descriptor(
        native_admission_sql(admission_kernel(), capture.authoring_inputs,
                             base_descriptor=target_admission_descriptor(capture, ()),
                             target_metadata=metadata, physical_catalog=catalog)
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
