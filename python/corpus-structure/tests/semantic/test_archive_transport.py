"""Independent binary archive transport and trusted model coverage expectations."""

from decimal import Decimal
from typing import Any

import pyarrow as pa
import pytest

from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
from corpus_structure.semantic.archive_native import archive_native_sql
from corpus_structure.semantic.archive_transport import (
    archive_batch,
    archive_tables,
    archive_write_profile,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.releases import _projection_rows
from semantic.releases_support import source_bundle


def test_archive_bytea_stays_binary_and_json_fields_lower_owned_tuples_without_mutation():
    relation = table("sem.input")
    profile = archive_write_profile(relation, "release:binary")
    rows = [
        {
            "release_id": "release:binary",
            "input_kind": "source",
            "input_name": "a",
            "content": memoryview(b"\x00\xff"),
            "content_digest": "digest",
        }
    ]
    batch = archive_batch(relation, profile, rows)
    assert batch.column("content").to_pylist() == [b"\x00\xff"]
    assert pa.types.is_binary(batch.schema.field("content").type)
    assert profile.new_encoder().schema().columns[-2].data_type.ddl() == "BYTEA"
    assert isinstance(rows[0]["content"], memoryview)

    relation = table("sem.property_applicability")
    profile = archive_write_profile(relation, "release:binary")
    row: dict[str, Any] = {column.name: None for column in relation.columns}
    row.update(
        release_id="release:binary",
        class_id="class",
        property_id="property",
        constraints={"patterns": ("^a", "z$"), "nested": ({"choices": ()},)},
    )
    batch = archive_batch(relation, profile, [row])
    assert batch.column("constraints").to_pylist() == [
        '{"patterns":["^a","z$"],"nested":[{"choices":[]}]}'
    ]
    assert row["constraints"] == {"patterns": ("^a", "z$"), "nested": ({"choices": ()},)}


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf"), Decimal("1.00"), object()]
)
def test_archive_json_refuses_nonfinite_and_unowned_serializers(value):
    relation = table("sem.property_applicability")
    profile = archive_write_profile(relation, "release:binary")
    row: dict[str, Any] = {column.name: None for column in relation.columns}
    row["constraints"] = {"minimum": value}
    with pytest.raises((ValueError, TypeError)):
        archive_batch(relation, profile, [row])


def test_every_declared_projection_has_exact_typed_columns_and_binary_encoder():
    prepared = prepare_release(source_bundle(), ResolvedDependencies(), PreparationProfile())
    projections = _projection_rows(prepared)
    tables = archive_tables()
    assert {relation.fullname for relation in tables} == {
        "sem.release", "sem.artifact", "sem.class_definition", "sem.input",
        "sem.metric_definition", "sem.property_definition", "sem.registry_row",
        "sem.scientific_decision_rule", "sem.vocabulary_member", "sem.class_hierarchy",
        "sem.conditional_rule", "sem.identity_slot", "sem.property_applicability",
        "sem.conditional_atom", "sem.operation_property_role",
    }
    assert tables[0].fullname == "sem.release"
    assert "runtime_binding" not in {relation.name for relation in tables}
    assert set(projections) == {t.name for t in tables if t.info["archive_role"] == "projection"}
    for relation in tables:
        profile = archive_write_profile(relation, prepared.release_id)
        profile.new_encoder()
        if relation.name in projections:
            batch = archive_batch(relation, profile, projections[relation.name])
            assert batch.num_rows == len(projections[relation.name])


def test_native_archive_has_one_typed_transport_and_parses():
    sql = archive_native_sql()
    assert len(prepare_sql(sql, source="archive").statements) == 3
    assert "jsonb_agg" not in sql
    assert "jsonb_populate_recordset" not in sql
    from pglast import parse_plpgsql

    programs = parse_plpgsql(sql)
    assert len(programs) == 3
    assert "FULL OUTER JOIN" in sql
    assert "sem.require_archive_bytes(p_release_id)" in sql
    assert "sem.require_execution_projection(p_release_id)" in sql


def test_archive_chunks_share_schema_and_preserve_rows_without_eager_consumption():
    from corpus_structure.semantic.archive_transport import archive_batches

    relation = table("sem.input")
    profile = archive_write_profile(relation, "release:chunks")
    consumed = []

    def rows():
        for index in range(5):
            consumed.append(index)
            yield {
                "release_id": "release:chunks",
                "input_kind": "source",
                "input_name": str(index),
                "content": bytes([index]),
                "content_digest": "digest",
            }

    batches = archive_batches(relation, profile, rows(), batch_size=2)
    first = next(batches)
    assert consumed == [0, 1]
    rest = list(batches)
    assert [batch.num_rows for batch in [first, *rest]] == [2, 2, 1]
    assert all(batch.schema.equals(profile.schema) for batch in rest)
    assert pa.Table.from_batches([first, *rest]).column("content").to_pylist() == [
        bytes([index]) for index in range(5)
    ]
    assert list(archive_batches(relation, profile, ())) == []



def test_archive_native_consumes_exact_supplied_model_for_columns_keys_and_scratch(monkeypatch):
    from pglast import parse_plpgsql
    from pglast.visitors import Visitor
    from sqlalchemy import Column, MetaData, Text

    from corpus_structure.semantic import archive_transport
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_products import function_bodies

    target = MetaData()
    for relation in (*archive_tables(), metadata.tables["sem.release_finalization"]):
        relation.to_metadata(target)
    target.tables["sem.input"].append_column(Column("quoted payload", Text()))
    monkeypatch.setattr(archive_transport, "metadata", MetaData())
    sql = archive_native_sql(target_metadata=target)
    assert len(parse_plpgsql(sql)) == 3
    body = function_bodies(sql)["sem.publish_release_archive"]
    assert '"quoted payload"' in body
    inserts = []

    class ArchiveInserts(Visitor):
        def visit_InsertStmt(self, ancestors, node):
            if node.relation.schemaname == "sem" and node.relation.relname == "input":
                inserts.append(node)

    # The header remains first according to captured foreign-key dependency
    # ordering, and scratch creation uses the exact model-owned source relation.
    prepare = function_bodies(sql)["sem.prepare_release_archive"]
    assert prepare.index("CREATE TEMPORARY TABLE cs_archive_release") < prepare.index("CREATE TEMPORARY TABLE cs_archive_input")
    assert "LIKE sem.input INCLUDING CONSTRAINTS" in prepare
    assert "ON COMMIT DROP" in prepare
    assert "TO corpus_sem_admitter" in prepare
    assert "FROM PUBLIC" in prepare
    query = body[body.index("INSERT INTO sem.input"):].split(";", 1)[0]
    ArchiveInserts()(prepare_sql(query, source="captured archive insert").statements)
    (insertion,) = inserts
    assert tuple(item.name for item in insertion.cols) == tuple(target.tables["sem.input"].c.keys())
