"""Retain one anchored book-demand task/dependency snapshot without changing execution.

This evidence-only read preserves existing facts for later resource correlation.
It does not infer readiness or reconstruct unrecorded attempt/provider transitions.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.orchestrate.characterization_recovery import resolve_characterization_anchor
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PROJECT = "nce-grinstead-snell-full-book"
TASK_FIELDS = (
    "id", "run_id", "release_id", "stage", "unit_type", "unit_id", "unit_key",
    "method_config_id", "input_hash", "packet_hash", "reused_task_id", "status",
    "attempt", "result_digest", "created_at", "started_at", "finished_at",
)
RUN_FIELDS = (
    "id", "project_id", "release_id", "runtime_id", "input_realization_id",
    "input_revision", "dependency_digest", "kind", "phase", "status",
    "code_commit", "result_realization_id", "sealed",
)


def bounded(conn, statement, maximum):
    rows = [dict(row) for row in conn.execute(statement.limit(maximum + 1)).mappings()]
    if len(rows) > maximum:
        raise ValueError("explicit row bound exceeded; no truncated graph is published")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-rows", type=int, default=100000)
    args = parser.parse_args()
    if args.anchor <= 0:
        parser.error("select an exact positive characterization anchor")
    if not 1 <= args.max_rows <= 100000:
        parser.error("row bound must be between1 and100000")
    if args.output.exists():
        parser.error("output already exists; preserve the earlier snapshot")
    runs, tasks, edges = map(table, ("ops.run", "ops.task", "ops.task_dependency"))
    configs, methods = map(table, ("ops.method_config", "ops.method"))
    with open_runtime_engine(Settings(), "bep-tc-book-graph-snapshot", purpose="read") as engine, read_snapshot(engine) as conn:
        snapshot_at = conn.exec_driver_sql("SELECT transaction_timestamp()").scalar_one()
        anchor, _demand = resolve_characterization_anchor(conn, args.anchor)
        if anchor != args.anchor:
            raise ValueError("select the actual demand anchor, not an implicitly resolved child")
        # Same authoritative anchor selection as the production recovery owner.
        run_rows = bounded(conn, select(
            *(runs.c[name] for name in RUN_FIELDS),
            runs.c.options["characterization_region"].as_integer().label("characterization_region"),
            runs.c.options["characterization_stage"].label("characterization_stage"),
        ).where((runs.c.id == anchor) | (runs.c.options["characterization_anchor"].as_integer() == anchor)).order_by(runs.c.id), 10000)
        if not run_rows or any(row["project_id"] != PROJECT for row in run_rows):
            raise ValueError("selected demand is absent or belongs to another project")
        selected_runs = [row["id"] for row in run_rows]
        selected_tasks = select(tasks.c.id).where(tasks.c.run_id.in_(selected_runs))
        task_rows = bounded(conn, select(*(tasks.c[name] for name in TASK_FIELDS)).where(tasks.c.run_id.in_(selected_runs)).order_by(tasks.c.id), args.max_rows)
        edge_rows = bounded(conn, select(edges).where(edges.c.task_id.in_(selected_tasks)).order_by(edges.c.task_id, edges.c.dependency_task_id), args.max_rows)
        owned_ids = {row["id"] for row in task_rows}
        external_ids = ({row["dependency_task_id"] for row in edge_rows} | {row["reused_task_id"] for row in task_rows if row["reused_task_id"] is not None}) - owned_ids
        endpoints = bounded(conn, select(*(tasks.c[name] for name in TASK_FIELDS)).where(tasks.c.id.in_(external_ids)).order_by(tasks.c.id), args.max_rows)
        if {row["id"] for row in endpoints} != external_ids:
            raise ValueError("a referenced dependency/reuse endpoint is unavailable")
        config_ids = {row["method_config_id"] for row in (*task_rows, *endpoints)}
        config_rows = bounded(conn, select(configs.c.id, configs.c.config_hash, methods.c.name.label("method"), methods.c.version).join(methods, methods.c.id == configs.c.method_id).where(configs.c.id.in_(config_ids)).order_by(configs.c.id), args.max_rows)
    report = dict(
        version="bep-tc-existing-task-graph-snapshot-1", project=PROJECT,
        snapshot_at=snapshot_at, acquired_at=datetime.now(timezone.utc),
        helper_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        selection=dict(anchor_run_id=anchor, run_ids=selected_runs, maximum_runs=10000, maximum_rows_per_collection=args.max_rows),
        runs=run_rows, tasks=task_rows, dependencies=edge_rows,
        external_endpoint_tasks=endpoints, configurations=config_rows,
        completeness="All registered runs of the exact demand anchor, their tasks and outgoing registered dependency edges at this snapshot; direct external dependency/reuse endpoints only.",
        limits=[
            "No transitive closure or complete scheduler readiness claim.",
            "Dependencies may not yet be registered; missing edges are not proof of independence.",
            "Task timestamps/current attempt are persisted state, not a complete attempt history or provider/queue/transfer timeline.",
            "Cross-process timestamps alone do not establish causal order or attribute host-wide resource use.",
        ],
    )
    payload = (json.dumps(report, default=lambda value: value.isoformat(), sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(payload) > 64 * 1024**2:
        raise ValueError("snapshot exceeds64MiB; no partial report is published")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(payload)
    print(json.dumps(dict(output=str(args.output), run_ids=selected_runs, tasks=len(task_rows), dependencies=len(edge_rows), bytes=len(payload), sha256=sha256(payload).hexdigest())))


if __name__ == "__main__":
    main()
