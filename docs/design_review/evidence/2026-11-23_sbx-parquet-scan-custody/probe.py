"""Compare path-based lazy Parquet scans with a held, verified input."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


def write(path, labels, witnesses):
    pq.write_table(
        pa.table({"address": [1, 2], "label": labels, "witness": witnesses}),
        path,
        row_group_size=1,
    )


def observe():
    with TemporaryDirectory(prefix="sbx-parquet-custody-") as directory:
        path = Path(directory) / "population.parquet"
        replacement = Path(directory) / "replacement.parquet"
        write(path, ["original", "untouched"], ["sealed", "other"])
        write(replacement, ["replacement", "untouched"], ["changed", "other"])
        with (
            duckdb.connect(config={"threads": 1}) as connection,
            pa.OSFile(str(path), "rb") as held,
        ):
            sealed_digest = hashlib.sha256(held.read()).hexdigest()
            held.seek(0)
            held_file = pq.ParquetFile(held)
            query = connection.from_parquet(str(path)).filter("address = 1").project("label")
            replacement.replace(path)
            rebound_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lazy_rows = query.fetchall()
            held_row = held_file.read_row_group(0, columns=["label"]).column("label")[0].as_py()
            held_witness = (
                held_file.read_row_group(0, columns=["witness"]).column("witness")[0].as_py()
            )

    assert rebound_digest != sealed_digest
    assert held_row == "original"
    assert held_witness == "sealed"
    assert lazy_rows in ([("original",)], [("replacement",)])
    return {
        "duckdb": duckdb.__version__,
        "pyarrow": pa.__version__,
        "replacement_digest_differs": rebound_digest != sealed_digest,
        "lazy_duckdb_projected_rows": lazy_rows,
        "held_arrow_projected_row": held_row,
        "held_arrow_omitted_witness": held_witness,
    }


if __name__ == "__main__":
    print(json.dumps(observe(), indent=2))
