"""Read one existing producer through the owned retained port; never execute a task."""
import argparse
import json

from sqlalchemy import select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=int, required=True)
    parser.add_argument("--port", choices=("retained", "normal"), default="retained")
    args = parser.parse_args()
    with open_runtime_engine(Settings(), "pce-retained-budget-read", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            tasks = table("ops.task")
            task = conn.execute(select(tasks.c.run_id, tasks.c.unit_id, tasks.c.release_id)
                .where(tasks.c.id == args.task)).mappings().one()
            prepared = open_release(conn, task["release_id"])
            reader = BoundReader(conn, task["run_id"], prepared)
            if args.port == "normal":
                result = reader.source_result(task["unit_id"], "extract.m1_candidates")
                if result is None:
                    raise RuntimeError("selected upstream producer has no owned source result")
                print(json.dumps(dict(outcome="passed", task_id=args.task, run_id=task["run_id"],
                    release_id=task["release_id"], port="normal", decoded_result_bytes=len(canonical_bytes(result)),
                    scope="read-only existing sealed producer through ordinary64MiB upstream port; no source/model/run execution")))
                raise SystemExit(0)
            retained = reader.retained_source_result(task["unit_id"], args.task, "extract.m1_candidates")
            print(json.dumps(dict(outcome="passed", task_id=retained.task_id,
                selected_task_id=retained.selected_task_id, run_id=retained.run_id,
                release_id=retained.release_id, body_digest=retained.body_digest,
                decoded_result_bytes=len(canonical_bytes(retained.result)),
                source_bindings=retained.source_bindings,
                scope="read-only existing sealed producer through ordinary64MiB retained port; no source/model/run execution")))
