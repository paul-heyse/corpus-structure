"""Small, independent controls for the proposed common analytical basis."""

import json
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from duckdb import col, fn

from corpus_structure.analytics import connection

CAPTION = pa.struct([("present", pa.bool_()), ("text", pa.string())])
SCHEMA = pa.schema(
    [
        ("block", pa.string()),
        ("ordinal", pa.int64()),
        ("span", pa.struct([("start", pa.int64()), ("stop", pa.int64())])),
        ("caption", CAPTION),
        ("amount", pa.decimal128(18, 3)),
        ("recorded", pa.timestamp("us", tz="UTC")),
    ]
)
VALIDATION = """
WITH ranges(block, placement, width, expected_count, closed) AS (
    VALUES ('origin', 0, 8, 2, true), ('moved', 40, 8, 2, true),
           ('bad', 0, 8, 2, true), ('empty', 0, 8, 0, true),
           ('pending', 0, 8, 2, false)
), numbered AS (
    SELECT t.*, r.width,
           row_number() OVER (PARTITION BY t.block ORDER BY ordinal, span.start) - 1 AS expected
    FROM source_rows t JOIN ranges r USING (block)
), violations AS (
    SELECT block, 'ordinal' AS reason FROM numbered WHERE ordinal <> expected
    UNION ALL
    SELECT block, 'span' FROM numbered WHERE span.start < 0 OR span.stop > width
    UNION ALL
    SELECT r.block, 'count'
    FROM ranges r LEFT JOIN numbered n USING (block)
    WHERE r.closed
    GROUP BY r.block, r.expected_count HAVING count(n.ordinal) <> r.expected_count
)
SELECT block, reason FROM violations ORDER BY block, reason
"""
PLACEMENT = """
SELECT block, ordinal, span.start + CASE WHEN block = 'moved' THEN 40 ELSE 0 END AS start_pos
FROM source_rows WHERE block IN ('origin', 'moved')
ORDER BY block, ordinal
"""
MISSING = """
WITH wanted(block, ordinal) AS (
    VALUES ('origin', 1), ('moved', 1), ('empty', 0), ('origin', 2)
)
SELECT w.block, w.ordinal FROM wanted w ANTI JOIN source_rows t USING (block, ordinal)
ORDER BY w.block, w.ordinal
"""
CONTENT = """
SELECT ordinal, caption.present, caption.text, amount, recorded
FROM source_rows WHERE block = 'origin' ORDER BY ordinal
"""


def main():
    first = datetime(2026, 11, 22, 0, 0, 0, 123456, UTC)
    amount = Decimal("100000000000000.127")

    def row(block, ordinal, start, stop, present):
        return {
            "block": block,
            "ordinal": ordinal,
            "span": {"start": start, "stop": stop},
            "caption": {"present": present, "text": None},
            "amount": amount,
            "recorded": first,
        }

    table = pa.Table.from_pylist(
        [
            row("origin", 1, 4, 8, True),
            row("moved", 0, 0, 3, False),
            row("bad", 0, 0, 3, False),
            row("origin", 0, 0, 3, False),
            row("moved", 1, 4, 8, True),
            row("bad", 0, 4, 9, True),
        ],
        schema=SCHEMA,
    )
    # Physical Arrow validation accepts this structurally valid, logically invalid population.
    table.validate(full=True)
    expected = {
        VALIDATION: [("bad", "ordinal"), ("bad", "span")],
        PLACEMENT: [("moved", 0, 40), ("moved", 1, 44), ("origin", 0, 0), ("origin", 1, 4)],
        MISSING: [("empty", 0), ("origin", 2)],
    }
    expected_content = [(0, False, None, amount, first), (1, True, None, amount, first)]

    with TemporaryDirectory() as work:
        path = Path(work) / "rows.parquet"
        pq.write_table(table, path, row_group_size=2)
        assert pq.read_table(path).equals(table, check_metadata=True)
        with connection() as analytical:
            result = analytical.from_arrow(table).filter(col("block") == "origin")
            window = fn("row_number").over(order_by=[col("ordinal")]).alias("numbered")
            assert result.select(col("ordinal"), window).sort(col("ordinal")).fetchall() == [
                (0, 1),
                (1, 2),
            ]
            native = analytical.native

            def check_answers():
                for query, answer in expected.items():
                    assert native.execute(query).fetchall() == answer
                content = native.sql(CONTENT).to_arrow_table()
                assert [
                    tuple(record.values()) for record in content.to_pylist()
                ] == expected_content

            native.register("source_rows", table)
            check_answers()
            native.unregister("source_rows")
            native.read_parquet(str(path)).create_view("source_rows")
            check_answers()
            scan = f"SELECT ordinal FROM read_parquet('{path}') WHERE block = 'origin'"
            cli = ["duckdb", "-no-agent", "-no-init", "-bail", "-json", ":memory:", "-c"]
            description = json.loads(subprocess.check_output([*cli, f"DESCRIBE {scan}"], text=True))
            assert [(row["column_name"], row["column_type"]) for row in description] == [
                ("ordinal", "BIGINT")
            ]
            plan = subprocess.check_output([*cli, f"EXPLAIN {scan}"], text=True)
            assert "Projections: ordinal" in plan and "Filters: block = 'origin'" in plan

            nanos = 1_764_000_000_123_456_789
            array = pa.array([nanos], type=pa.int64()).cast(pa.timestamp("ns", tz="UTC"))
            high_precision = pa.table({"captured_at": array})
            pq.write_table(high_precision, path)
            assert pq.read_table(path).equals(high_precision)
            native.register("high_precision", high_precision)
            [(arrow_ns,)] = native.execute(
                "SELECT epoch_ns(captured_at) FROM high_precision"
            ).fetchall()
            [(parquet_ns,)] = native.execute(
                "SELECT epoch_ns(captured_at) FROM read_parquet(?)", [str(path)]
            ).fetchall()
            assert arrow_ns == parquet_ns == nanos, (arrow_ns, parquet_ns)
            roundtrip = native.sql("SELECT captured_at FROM high_precision").to_arrow_table()
            assert roundtrip["captured_at"].cast(pa.int64()).to_pylist() == [nanos]
            timestamp_type = str(roundtrip.schema.field("captured_at").type)

            pending = native.execute("SELECT * FROM range(2)")
            assert pending.fetchone() == (0,)
            try:
                native.sql("SELECT 42").fetchall()
            except duckdb.ResourceInUseException:
                pass
            else:
                raise AssertionError("new relation unexpectedly accepted a pending result")
            assert pending.fetchall() == [(1,)]
            assert native.sql("SELECT 42").fetchall() == [(42,)]

            partial = Path(work) / "partial.parquet"
            partial.write_bytes(path.read_bytes()[:-8])
            for reader, error in (
                (pq.read_table, pa.ArrowInvalid),
                (native.read_parquet, duckdb.Error),
            ):
                try:
                    reader(str(partial))
                except error:
                    pass
                else:
                    raise AssertionError("reader unexpectedly accepted a truncated Parquet footer")

    cli = subprocess.check_output(["duckdb", "-no-agent", "--version"], text=True).strip()
    print(
        json.dumps(
            {
                "duckdb": duckdb.__version__,
                "pyarrow": pa.__version__,
                "cli": cli,
                "arrow_structure_accepted_invalid_population": True,
                "owner_expression_window": "matched",
                "independent_expectations_for_arrow_and_parquet": len(expected) + 1,
                "parquet_plan_has_projection_and_filter": True,
                "unfinished_result_blocks_reuse_until_drained": True,
                "both_readers_refused_truncated_parquet_footer": True,
                "arrow_parquet_utc_nanoseconds": nanos,
                "duckdb_utc_nanoseconds_from_arrow": arrow_ns,
                "duckdb_utc_nanoseconds_from_parquet": parquet_ns,
                "duckdb_arrow_egress_type": timestamp_type,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
