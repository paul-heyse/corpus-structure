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

from .test_releases import source_bundle


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
    assert len(tables) == 20
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
    assert "FULL JOIN" in sql
    assert "sem.require_archive_bytes(p_release_id)" in sql
    assert "sem.require_execution_projection(p_release_id)" in sql
