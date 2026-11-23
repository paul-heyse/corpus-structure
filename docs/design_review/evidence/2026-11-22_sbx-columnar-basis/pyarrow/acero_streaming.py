"""Probe D: one Acero plan over a lazily supplied Python source of nested partition-like rows.

Plan: record_batch_reader_source(generator) -> filter -> project (nested list/struct kernels)
-> hashjoin "left anti" against a second source -> aggregate (grouped), consumed via
Declaration.to_reader(). Side-effect counters record how many source batches the plan pulled
when the consumer has read only one output batch, which thread ran the generator, output order,
and error propagation. Synthetic data only; no timing claims.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/pyarrow/acero_streaming.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time

import pyarrow as pa
import pyarrow.acero as ac
import pyarrow.compute as pc

TOKEN = pa.struct([("text", pa.string()), ("start", pa.int32()), ("stop", pa.int32())])
SCHEMA = pa.schema(
    [
        pa.field("block", pa.string(), nullable=False),
        pa.field("ordinal", pa.int64(), nullable=False),
        pa.field("tokens", pa.list_(TOKEN)),
    ]
)
BATCHES = 400
ROWS = 64


class Source:
    """Generator-backed reader with side-effect counters."""

    def __init__(self, batches: int = BATCHES, fail_at: int | None = None) -> None:
        self.batches = batches
        self.fail_at = fail_at
        self.pulled = 0
        self.threads: set[str] = set()

    def _gen(self):
        for b in range(self.batches):
            if self.fail_at is not None and b == self.fail_at:
                raise ValueError("source failure at batch %d" % b)
            self.pulled += 1
            self.threads.add((threading.current_thread() is threading.main_thread(), threading.get_native_id()))
            base = b * ROWS
            block = [f"blk{(base + i) // 16:05d}" for i in range(ROWS)]
            ordinal = [base + i for i in range(ROWS)]
            tokens = [
                [{"text": f"w{j}", "start": j * 2, "stop": j * 2 + 1} for j in range((base + i) % 4)]
                for i in range(ROWS)
            ]
            yield pa.RecordBatch.from_arrays(
                [pa.array(block), pa.array(ordinal, pa.int64()), pa.array(tokens, pa.list_(TOKEN))],
                schema=SCHEMA,
            )

    def reader(self) -> pa.RecordBatchReader:
        return pa.RecordBatchReader.from_batches(SCHEMA, self._gen())


def excluded_reader() -> tuple[pa.RecordBatchReader, dict]:
    state = {"pulled": 0}
    schema = pa.schema([("block", pa.string()), ("ordinal", pa.int64())])

    def gen():
        for b in range(10):
            state["pulled"] += 1
            yield pa.RecordBatch.from_arrays(
                [pa.array([f"blk{(b * 640 + k) // 16:05d}" for k in range(0, 640, 7)]),
                 pa.array([b * 640 + k for k in range(0, 640, 7)], pa.int64())],
                schema=schema,
            )

    return pa.RecordBatchReader.from_batches(schema, gen()), state


def streaming_chain(src: pa.RecordBatchReader, right: pa.RecordBatchReader | None) -> ac.Declaration:
    source = ac.Declaration("record_batch_reader_source", ac.RecordBatchReaderSourceNodeOptions(src))
    n_tokens = pc.list_value_length(pc.field("tokens"))
    first_text = pc.struct_field(pc.list_element(pc.field("tokens"), 0), "text")
    nodes = [
        source,
        ac.Declaration("filter", ac.FilterNodeOptions(n_tokens > 0)),
        ac.Declaration(
            "project",
            ac.ProjectNodeOptions(
                [pc.field("block"), pc.field("ordinal"), n_tokens, first_text],
                names=["block", "ordinal", "n_tokens", "first_text"],
            ),
        ),
    ]
    chain = ac.Declaration.from_sequence(nodes)
    if right is None:
        return chain
    right_src = ac.Declaration("record_batch_reader_source", ac.RecordBatchReaderSourceNodeOptions(right))
    return ac.Declaration(
        "hashjoin",
        ac.HashJoinNodeOptions("left anti", left_keys=["block", "ordinal"], right_keys=["block", "ordinal"]),
        inputs=[chain, right_src],
    )


def with_aggregate(decl: ac.Declaration) -> ac.Declaration:
    return ac.Declaration(
        "aggregate",
        ac.AggregateNodeOptions(
            [
                ("ordinal", "hash_count", None, "rows"),
                ("n_tokens", "hash_sum", None, "tokens"),
                ("ordinal", "hash_list", None, "ordinals"),
                ("first_text", "hash_distinct", None, "first_texts"),
            ],
            keys=["block"],
        ),
        inputs=[decl],
    )


def monotonic(values: list[int]) -> bool:
    return all(a < b for a, b in zip(values, values[1:]))


out: dict[str, object] = {"python": sys.version.split()[0], "pyarrow": pa.__version__,
                          "cpu_count": pa.cpu_count(), "io_thread_count": pa.io_thread_count(),
                          "source_batches": BATCHES, "rows_per_batch": ROWS}

# 1. filter+project only: pulled count after first output batch, then after a pause
for use_threads in (True, False):
    src = Source()
    base_alloc = pa.total_allocated_bytes()
    reader = streaming_chain(src.reader(), None).to_reader(use_threads=use_threads)
    first = reader.read_next_batch()
    pulled_at_first = src.pulled
    time.sleep(0.5)
    pulled_after_pause = src.pulled
    alloc_after_pause = pa.total_allocated_bytes() - base_alloc
    rest = reader.read_all()
    ordinals = first.column("ordinal").to_pylist() + rest.column("ordinal").to_pylist()
    out[f"chain_use_threads_{use_threads}"] = {
        "pulled_at_first_output": pulled_at_first,
        "pulled_after_0.5s_without_consuming": pulled_after_pause,
        "arrow_bytes_held_after_pause": alloc_after_pause,
        "pulled_total": src.pulled,
        "generator_native_threads": len({t[1] for t in src.threads}),
        "generator_ran_on_main_thread": any(t[0] for t in src.threads),
        "output_rows": len(ordinals),
        "output_ordinal_strictly_increasing": monotonic(ordinals),
    }

# 2. early close: does closing the reader stop the source?
src = Source(batches=4000)
reader = streaming_chain(src.reader(), None).to_reader(use_threads=True)
reader.read_next_batch()
reader.close()
pulled_at_close = src.pulled
time.sleep(0.3)
out["chain_early_close"] = {"source_batches": 4000, "pulled_at_close": pulled_at_close,
                            "pulled_after_close_pause": src.pulled}

# 3. with hash anti join: build side fully consumed before probe output; order
for use_threads in (True, False):
    src = Source()
    right, rstate = excluded_reader()
    reader = streaming_chain(src.reader(), right).to_reader(use_threads=use_threads)
    first = reader.read_next_batch()
    pulled_at_first = src.pulled
    right_at_first = rstate["pulled"]
    rest = reader.read_all()
    ordinals = first.column("ordinal").to_pylist() + rest.column("ordinal").to_pylist()
    # right side covers ordinals < 6400 at every 7th position within each 640-row stride
    expected = [o for o in range(BATCHES * ROWS) if o % 4 != 0 and not (o < 6400 and o % 640 % 7 == 0)]
    out[f"anti_join_use_threads_{use_threads}"] = {
        "probe_pulled_at_first_output": pulled_at_first,
        "build_pulled_at_first_output": right_at_first,
        "output_rows": len(ordinals),
        "expected_rows": len(expected),
        "same_set_as_expected": sorted(ordinals) == expected,
        "output_ordinal_strictly_increasing": monotonic(ordinals),
    }

# 3b. join output batching: how much probe input precedes the first joined batch
join_batching = {}
for join_type in ("left anti", "inner"):
    for n in (400, 4000):
        src = Source(batches=n)
        right, _ = excluded_reader()
        reader = ac.Declaration(
            "hashjoin",
            ac.HashJoinNodeOptions(join_type, left_keys=["block", "ordinal"], right_keys=["block", "ordinal"]),
            inputs=[streaming_chain(src.reader(), None),
                    ac.Declaration("record_batch_reader_source", ac.RecordBatchReaderSourceNodeOptions(right))],
        ).to_reader(use_threads=False)
        first = reader.read_next_batch()
        join_batching[f"{join_type}/{n}"] = {"probe_pulled_at_first_output": src.pulled,
                                              "first_batch_rows": first.num_rows}
        reader.close()
out["join_output_batching_use_threads_False"] = join_batching

# 4. full plan with grouped aggregate (pipeline breaker) streamed out
for use_threads in (True, False):
    src = Source()
    right, _ = excluded_reader()
    reader = with_aggregate(streaming_chain(src.reader(), right)).to_reader(use_threads=use_threads)
    first = reader.read_next_batch()
    pulled_at_first = src.pulled
    table = pa.Table.from_batches([first]).combine_chunks()
    rest = reader.read_all()
    full = pa.concat_tables([pa.Table.from_batches([first]), rest]) if rest.num_rows else table
    blocks = full.column("block").to_pylist()
    lists = full.column("ordinals").to_pylist()
    out[f"aggregate_use_threads_{use_threads}"] = {
        "probe_pulled_at_first_output": pulled_at_first,
        "groups": full.num_rows,
        "groups_in_key_order": blocks == sorted(blocks),
        "hash_list_members_in_input_order": all(monotonic(x) for x in lists),
        "output_schema": str(full.schema).splitlines(),
    }

# 5. error raised by the Python source propagates to the consumer
src = Source(fail_at=50)
try:
    streaming_chain(src.reader(), None).to_reader(use_threads=True).read_all()
    out["source_error"] = "no error surfaced"
except Exception as exc:  # noqa: BLE001 - recording the surfaced type
    out["source_error"] = f"{type(exc).__name__}: {exc}"

# 6. Table.group_by ordering: use_threads=False keeps first-seen key order and member order
tbl = pa.table({"k": ["b", "a", "b", "c", "a"], "v": [1, 2, 3, 4, 5]})
g = tbl.group_by("k", use_threads=False).aggregate([("v", "list"), ("v", "first")])
out["table_group_by_use_threads_false"] = g.to_pydict()

# 7. factories not wrapped by Python node options (fetch, union, write, sink variants)
probe = (
    "import pyarrow as pa, pyarrow.acero as ac\n"
    "t = pa.table({'x':[1,2]})\n"
    "a = ac.Declaration('table_source', ac.TableSourceNodeOptions(t))\n"
    "try:\n"
    "    print(ac.Declaration('union', ac.ExecNodeOptions(), inputs=[a, a]).to_table())\n"
    "except Exception as e:\n"
    "    print('union:', type(e).__name__, e)\n"
)
proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=60)
out["union_via_base_options"] = {"returncode": proc.returncode,
                                 "stdout": proc.stdout.strip()[-300:], "stderr": proc.stderr.strip()[-300:]}
out["python_node_options"] = sorted(n for n in dir(ac) if n.endswith("NodeOptions"))

json.dump(out, sys.stdout, indent=2, default=str)
print()
