"""Replay the named CPU M1 challenger on authenticated inputs without writes."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from inspect_retained import CASES, PROJECT
from pydantic_core import to_jsonable_python
from sqlalchemy import select

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.orchestrate.m1 import registry
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def compare(conn, run_id, cut_id, view_id, name):
    run, cut = table("ops.run"), table("ops.input_cut")
    release = conn.execute(
        select(run.c.release_id)
        .join(cut, cut.c.run_id == run.c.id)
        .where(
            run.c.id == run_id,
            run.c.project_id == PROJECT,
            cut.c.id == cut_id,
            cut.c.release_id == run.c.release_id,
        )
    ).scalar_one()
    prepared = open_release(conn, release)
    reader = BoundReader(
        conn,
        run_id,
        prepared,
        cut_id=cut_id,
        analysis=False,
        read_budget=PublishedReadBudget(max_rows=200_000, max_bytes=128 * 1024**2),
    )
    source = reader.source_view(view_id)
    chosen = registry(Path("domains/statistics")).bind_release(prepared)
    method_name = "extract.m1_candidates"
    method = chosen.method(method_name)
    cfg = chosen.resolve(method_name, name).config
    ctx = SimpleNamespace(reader=reader, check_active=lambda: None)
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, view_id, source.ref.key))
    try:
        (result,) = method.run((unit,), cfg, ctx)
    finally:
        method.close()
    detail = result.parse_detail
    reports = []
    for item in detail["reports"]:
        context = detail["contexts"][item["context"]]
        native = item.get("report") or {}
        reports.append(
            {
                "region": context["region"],
                "family": item["family"],
                "variant": item.get("variant"),
                "groups": json.loads(native.get("raw_json", "{}")).get(item["family"], []),
                "diagnostics": [
                    {key: row[key] for key in ("role", "code", "message") if key in row}
                    for row in (
                        *item.get("diagnostics", ()),
                        *item.get("association_diagnostics", ()),
                    )
                ],
            }
        )
    return to_jsonable_python(
        {
            "run": run_id,
            "cut": cut_id,
            "view": view_id,
            "release": release,
            "configuration": name,
            "policy": detail["policy"],
            "source": detail["source_pin"],
            "outcome": result.outcome,
            "records": [
                {
                    "family": row["family"],
                    "fields": row["fields"],
                    "anchors": row["anchors"],
                }
                for row in result.records or ()
            ],
            "reports": reports,
        }
    )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("view", type=int, choices=[case[2] for case in CASES])
    cli.add_argument("configuration", choices=("described", "readings", "contextual"))
    args = cli.parse_args()
    run_id, cut_id, view_id, _ = next(case for case in CASES if case[2] == args.view)
    with (
        open_runtime_engine(Settings(), "dma-candidate-readonly", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        print(json.dumps(compare(conn, run_id, cut_id, view_id, args.configuration), indent=2))


if __name__ == "__main__":
    main()
