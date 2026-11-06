"""Read-only immutable native run capture, retaining one exact raw envelope per task.

A live capture is an explicit partial checkpoint, never completed-run qualification.
All writes stay in the assigned assessment evidence directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, UTC
import json
from pathlib import Path

from normalize_sources import BASE, HERE, canonical, retain


def capture(run_id: int, output: Path, *, allow_live: bool = False):
    from sqlalchemy import text
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings

    output.mkdir(exist_ok=False)
    with open_runtime_engine(Settings(), "gs120-assessment-capture", purpose="read") as engine:
        with engine.connect() as conn:
            run = dict(conn.execute(text("SELECT id,project_id,release_id,runtime_id,status,sealed,code_commit FROM ops.run WHERE id=:r"), {"r": run_id}).mappings().one())
            complete = run["sealed"] and run["status"] == "finished"
            if not complete and not allow_live:
                raise ValueError("run is not sealed and finished; --allow-live is required for a partial checkpoint")
            completed = conn.execute(text("SELECT cut_id,batch_id,output_realization_id FROM ops.completed_result WHERE run_id=:r"), {"r": run_id}).mappings().one_or_none()
            tasks = [dict(row) for row in conn.execute(text("""
SELECT t.id selected_task_id,COALESCE(t.reused_task_id,t.id) origin_task_id,
       t.unit_type,t.unit_id,t.status,m.name method,m.version operation_version,
       t.error IS NOT NULL has_task_error, r.task_id IS NOT NULL has_task_result
FROM ops.task t JOIN ops.method_config cfg ON cfg.id=t.method_config_id
JOIN ops.method m ON m.id=cfg.method_id
LEFT JOIN ops.task_result r ON r.task_id=COALESCE(t.reused_task_id,t.id)
WHERE t.run_id=:r ORDER BY t.id
"""), {"r": run_id}).mappings()]
        for row in tasks:
            if not row["has_task_result"]:
                continue
            with engine.connect() as conn:
                body = conn.execute(text("SELECT body FROM ops.task_result WHERE task_id=:t"), {"t": row["origin_task_id"]}).scalar_one()
            raw_path = output / ("task-" + str(row["selected_task_id"]) + ".json")
            retain(raw_path, {**row, "body": body})
            row["raw_file"] = raw_path.name
            from hashlib import sha256
            row["raw_sha256"] = sha256(raw_path.read_bytes()).hexdigest()
            row["raw_bytes"] = raw_path.stat().st_size
    manifest = {"protocol": "gs120-native-output-capture-1", "captured_at": datetime.now(UTC).isoformat(),
                "run": run, "completed_result": dict(completed) if completed is not None else None,
                "capture_scope": "completed_sealed_run" if complete else "partial_live_checkpoint",
                "metadata_membership_frozen_before_body_reads": True,
                "task_results_are_immutable": True, "tasks": tasks,
                "writes": "assessment evidence files only; database read-only purpose",
                "semantic_quality": "unassessed"}
    retain(output / "manifest.json", manifest)
    print(json.dumps({"outcome": "passed", "scope": manifest["capture_scope"],
                      "run_id": run_id, "tasks": len(tasks),
                      "raw_envelopes": sum(row["has_task_result"] for row in tasks)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", type=int)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()
    output = (HERE / args.out).resolve()
    if HERE not in output.parents:
        raise ValueError("capture output must stay within the assessment assignment")
    capture(args.run_id, output, allow_live=args.allow_live)


if __name__ == "__main__":
    main()
