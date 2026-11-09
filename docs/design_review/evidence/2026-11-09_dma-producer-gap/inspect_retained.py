"""Trace the exact predecessor candidate origins without running producers or reading grades."""

import json
from collections import Counter

from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

CASES = ((407, 517, 381, 1988), (407, 517, 382, 1989), (437, 537, 409, 2141))
PROJECT = "nce-grinstead-snell-full-book"


def inspect(conn, run_id, cut_id, view_id, task_id):
    task, cut, member = map(table, ("ops.task", "ops.input_cut", "ops.cut_task"))
    run = table("ops.run")
    release = conn.execute(
        select(run.c.release_id)
        .join(cut, cut.c.run_id == run.c.id)
        .join(member, member.c.cut_id == cut.c.id)
        .join(task, task.c.id == member.c.task_id)
        .where(
            run.c.id == run_id,
            run.c.project_id == PROJECT,
            cut.c.id == cut_id,
            cut.c.release_id == run.c.release_id,
            task.c.id == task_id,
            task.c.run_id == run.c.id,
            task.c.unit_type == "source_view",
            task.c.unit_id == view_id,
        )
    ).scalar_one()
    reader = BoundReader(
        conn,
        run_id,
        open_release(conn, release),
        cut_id=cut_id,
        analysis=False,
        read_budget=PublishedReadBudget(max_rows=200_000, max_bytes=128 * 1024**2),
    )
    source = reader.source_view(view_id)
    body = reader.source_result(view_id, "extract.m1_candidates")
    if body is None:
        raise ValueError("selected producer report unavailable")
    detail = body["parse_detail"]
    record_roles = []
    for item in body.get("records") or ():
        record_roles.append(
            {
                "family": item.get("family"),
                "standing": item.get("standing"),
                "fields": item.get("fields"),
            }
        )
    traces = []
    for item in detail["reports"]:
        if item.get("context") is None:
            continue
        context = detail["contexts"][item["context"]]
        native = item.get("report") or {}
        groups = json.loads(native.get("raw_json", "{}")).get(item["family"], ())
        trace = {
            "family": item["family"],
            "region": context["region"],
            "extent": [context["start"], context["end"]],
            "groups": len(groups),
            "source_literal": source.text[context["start"] : context["end"]],
            "diagnostics": [
                {key: row[key] for key in ("role", "code", "message") if key in row}
                for row in (*item.get("diagnostics", ()), *item.get("association_diagnostics", ()))
            ],
        }
        if item.get("operation"):
            trace["operation"] = item["operation"]
        if item.get("outcome"):
            trace["outcome"] = item["outcome"]
        if groups:
            trace["raw_roles"] = groups
        traces.append(trace)
    return {
        "run_id": run_id,
        "cut_id": cut_id,
        "source_view_id": view_id,
        "task_id": task_id,
        "source": detail["source_pin"],
        "policy": detail["policy"],
        "records": record_roles,
        "policy_events": detail["record_policy_events"],
        "interpretations": detail.get("record_interpretation", ()),
        "contribution_kinds": dict(
            Counter(
                row.get("semantic_type", row.get("kind")) for row in body.get("contributions") or ()
            )
        ),
        "traces": traces,
    }


def main():
    with (
        open_runtime_engine(Settings(), "dma-producer-gap", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        print(json.dumps([inspect(conn, *case) for case in CASES], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
