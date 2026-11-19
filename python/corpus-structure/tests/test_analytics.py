"""Independent resource, expression, multiplicity and time-zone contracts."""

from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from duckdb import col

from corpus_structure.analytics import connection
from corpus_structure.settings import AnalyticsSettings


def test_invocation_uses_settings_and_releases_private_spill(tmp_path):
    settings = AnalyticsSettings(threads=2, memory_limit="128MB", scratch_path=tmp_path)
    with connection(settings) as db:
        actual = db.native.execute(
            "SELECT current_setting('threads'), current_setting('memory_limit'), "
            "current_setting('temp_directory'), current_setting('TimeZone')"
        ).fetchall()[0]
        assert actual[0] == 2 and actual[1] == "122.0 MiB" and actual[3] == "UTC"
        scratch = Path(actual[2])
        assert scratch.is_absolute() and scratch.parent == tmp_path
        assert scratch.is_dir() and scratch.stat().st_mode & 0o077 == 0
        value = datetime(2026, 11, 19, 12, 34, tzinfo=UTC)
        table = pa.table({"time": pa.array([value], type=pa.timestamp("us", tz="Asia/Tokyo"))})
        result = db.from_arrow(table).to_arrow_table()
        assert result.schema.field("time").type.tz == "UTC"
        assert result.column("time")[0].as_py() == value
    assert not scratch.exists()


@pytest.mark.parametrize("operation", ("filter", "select", "sort", "aggregate", "join"))
def test_expression_entries_refuse_sql_text(tmp_path, operation):
    with connection(AnalyticsSettings(scratch_path=tmp_path)) as db:
        relation = db.from_arrow(pa.table({"id": [1]}))
        with pytest.raises(TypeError, match="expression"):
            if operation == "join":
                relation.join(relation, "id=id")
            else:
                getattr(relation, operation)("id")


def test_bag_and_set_operations_preserve_their_declared_multiplicity(tmp_path):
    with connection(AnalyticsSettings(scratch_path=tmp_path)) as db:
        left = db.from_arrow(pa.table({"id": [1, 1, 2]}))
        right = db.from_arrow(pa.table({"id": [1]}))
        assert left.union_all(right).sort(col("id")).fetchall() == [(1,), (1,), (1,), (2,)]
        assert left.union(right).sort(col("id")).fetchall() == [(1,), (2,)]
        assert left.except_all(right).sort(col("id")).fetchall() == [(1,), (2,)]
        assert left.except_(right).sort(col("id")).fetchall() == [(2,)]
        assert left.intersect_all(left).sort(col("id")).fetchall() == [(1,), (1,), (2,)]
        assert left.intersect(left).sort(col("id")).fetchall() == [(1,), (2,)]
        with pytest.raises(TypeError, match="columns or types"):
            left.union_all(db.from_arrow(pa.table({"id": ["1"]})))


def test_bad_scratch_refuses_before_connection(tmp_path):
    unavailable = tmp_path / "file"
    unavailable.write_bytes(b"occupied")
    with (
        pytest.raises(OSError, match=str(unavailable)),
        connection(AnalyticsSettings(scratch_path=unavailable)),
    ):
        pytest.fail("unavailable scratch was admitted")


def test_export_capture_honors_batch_size_and_resident_bound():
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.serve.companion_export import _capture_batches

    table = pa.table({"id": [1, 2, 3]})
    for mode in ("resident", "spooled"):
        settings = AnalyticsSettings(capture_mode=mode, batch_size=2)
        batches = list(_capture_batches(iter(table.to_batches()), settings))
        assert [batch.num_rows for batch in batches] == [2, 1]
        assert pa.Table.from_batches(batches).to_pylist() == [{"id": 1}, {"id": 2}, {"id": 3}]
    with pytest.raises(SemanticRefusal, match="resident capture exceeds"):
        list(
            _capture_batches(
                iter(table.to_batches()),
                AnalyticsSettings(capture_mode="resident", resident_limit_bytes=1),
            )
        )
