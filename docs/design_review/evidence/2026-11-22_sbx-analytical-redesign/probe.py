"""Small installed-library controls for grouped proofs and Arrow stream reuse."""

import json
import subprocess

import duckdb
import pyarrow as pa
from pyarrow import acero, compute as pc

SCHEMA = pa.schema(
    [
        ("role", pa.string()),
        ("ordinal", pa.int32()),
        ("start", pa.int32()),
        ("stop", pa.int32()),
    ]
)


def source():
    rows = [
        ("annotation", 0, 0, 1),
        ("annotation", 1, 1, 3),
        ("report-a", 0, 1, 2),
        ("annotation", 1, 4, 2),
        ("report-b", 0, 3, 4),
        ("annotation", 2, 0, 0),
    ]
    batches = (
        pa.record_batch(list(map(list, zip(*chunk, strict=True))), schema=SCHEMA)
        for chunk in (rows[:3], rows[3:])
    )
    return pa.RecordBatchReader.from_batches(SCHEMA, batches)


def arrow_groups():
    graph = acero.Declaration.from_sequence(
        [
            acero.Declaration(
                "record_batch_reader_source",
                acero.RecordBatchReaderSourceNodeOptions(source()),
            ),
            acero.Declaration(
                "project",
                acero.ProjectNodeOptions(
                    [
                        pc.field("role"),
                        pc.field("ordinal"),
                        (pc.field("start") > pc.field("stop")).cast(pa.int64()),
                    ],
                    ["role", "ordinal", "invalid"],
                ),
            ),
            acero.Declaration(
                "aggregate",
                acero.AggregateNodeOptions(
                    [
                        ("invalid", "hash_sum", None, "inversions"),
                        ("ordinal", "hash_count", None, "multiplicity"),
                    ],
                    keys=["role", "ordinal"],
                ),
            ),
        ]
    )
    with graph.to_reader(use_threads=False) as reader:
        return sorted(
            (row["role"], row["ordinal"], row["multiplicity"], row["inversions"])
            for batch in reader
            for row in batch.to_pylist()
        )


def duckdb_groups(con):
    relation = con.from_arrow(source())
    grouped = relation.aggregate(
        "role, ordinal, count(*) AS multiplicity, "
        "count(*) FILTER (WHERE start > stop) AS inversions",
        "role, ordinal",
    ).order("role, ordinal")
    with grouped.to_arrow_reader(batch_size=2) as reader:
        return [
            (row["role"], row["ordinal"], row["multiplicity"], row["inversions"])
            for batch in reader
            for row in batch.to_pylist()
        ]


def main():
    expected = [
        ("annotation", 0, 1, 0),
        ("annotation", 1, 2, 1),
        ("annotation", 2, 1, 0),
        ("report-a", 0, 1, 0),
        ("report-b", 0, 1, 0),
    ]
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    arrow = arrow_groups()
    with duckdb.connect(
        config={
            "threads": "1",
            "memory_limit": "64MB",
            "max_temp_directory_size": "16MB",
        }
    ) as con:
        duck = duckdb_groups(con)
        single_use = con.from_arrow(source()).aggregate("count(*) AS count")
        first_count = single_use.fetchall()[0][0]
        try:
            single_use.fetchall()
        except duckdb.InvalidInputException as error:
            reader_reuse_refused = "already been consumed" in str(error)
        else:
            reader_reuse_refused = False
        stored = con.from_arrow(source()).materialize().aggregate("count(*) AS count")
        stored_counts = [stored.fetchall()[0][0], stored.fetchall()[0][0]]
    assert arrow == duck == expected, (arrow, duck)
    assert first_count == 6 and reader_reuse_refused
    assert stored_counts == [6, 6], stored_counts

    cli = ["duckdb", "-no-init", "-bail", "-no-agent", ":memory:"]
    profile = subprocess.check_output(
        [
            *cli,
            "-csv",
            "-c",
            "SET threads=1; SET memory_limit='64MB'; EXPLAIN (FORMAT JSON) SELECT i % 2 AS k, "
            "count(*) FROM range(8) t(i) GROUP BY k",
        ],
        text=True,
    )
    assert "HASH_GROUP_BY" in profile, profile
    print(
        json.dumps(
            {
                "pyarrow": pa.__version__,
                "duckdb_python": duckdb.__version__,
                "duckdb_cli": subprocess.check_output(
                    ["duckdb", "--version"], text=True
                ).strip(),
                "groups": arrow,
                "initial_reader_count": first_count,
                "second_scan_refused": reader_reuse_refused,
                "materialized_counts": stored_counts,
                "cli_group_operator": "HASH_GROUP_BY",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
