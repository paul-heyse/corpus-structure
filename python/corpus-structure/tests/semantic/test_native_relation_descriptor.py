"""Named physical row shapes evolve without treating attnum as a wire contract."""

from pathlib import Path

from sqlalchemy import BigInteger, Column, Identity, Integer, MetaData, Table, Text, text

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
