"""Run the current native organization method from one verified protected native pin.

The graph contains only ingest.pdf. It cannot run Standard conversion when the explicit
native input is valid, and it does not contain enrichment, recognition or knowledge methods.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate.commands import start_bound_run
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import selected_source_views
from corpus_structure.settings import Settings


def retain(path: Path, value) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--post-read", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads((args.recovery / "task.json").read_bytes())
    pin = ProductReference(**json.loads((args.recovery / "native.pin.json").read_bytes()))
    read_receipt = json.loads(args.post_read.read_bytes())
    if read_receipt["status"] != "passed" or read_receipt["reference"] != pin.values():
        raise ValueError("the exact native input has no successful post-termination read")
    settings = Settings()
    with open_runtime_engine(settings, "um-current-native-organize", purpose="write") as engine:
        with engine.connect() as conn:
            target = conn.execute(text(
                "SELECT current_database(), (SELECT oid FROM pg_database "
                "WHERE datname=current_database()), "
                "(SELECT version_num FROM public.semantic_alembic_version)"
            )).one()
            if tuple(target) != ("corpus_pdf_20261102", 16934542, args.head):
                raise ValueError("current organization target ownership/head differs")
            reader = published_record_reader(conn, pin)
            if reader is None or reader.revision["kind"] != "native":
                raise ValueError("current organization requires an immutable native input")
        args.output.mkdir(parents=True, exist_ok=False)
        try:
            report = start_bound_run(
                engine, release_id=source["release_id"],
                realization_id=f"source:pdf-docling-adoption:{source['release_id']}",
                project_id="pdf-docling-adoption", domain="statistics",
                method_settings=MethodSettings(
                    data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache,
                ),
                graph=Graph(((Stage.INGEST, (Step("ingest.pdf/default"),)),)),
                scope="pdf-qualification", native_product=pin,
            )
            retain(args.output / "source-report.json", report.model_dump(mode="json"))
            with engine.connect() as conn:
                views = selected_source_views(conn, report.run_id)
                pins = {view.native_product for view in views}
                if len(pins) != 1 or sum(view.analysis_eligible for view in views) != 5:
                    raise ValueError("current organization did not prepare five intact sections")
                organized = pins.pop()
                if organized.product_key != "organized" or organized == pin:
                    raise ValueError("current organization did not publish a new organized product")
                reader = published_record_reader(conn, organized)
                if reader is None:
                    raise ValueError("current organized product is unavailable")
                tasks = table("ops.task")
                statuses = conn.execute(select(tasks.c.id, tasks.c.status).where(
                    tasks.c.run_id == report.run_id,
                )).all()
                retain(args.output / "organized.pin.json", organized.values())
                retain(args.output / "readiness.json", {
                    "status": "passed", "run_id": report.run_id,
                    "input_native_pin": pin.values(), "organized_pin": organized.values(),
                    "analysis_sections": 5, "selected_views": len(views),
                    "task_statuses": [list(row) for row in statuses],
                    "conversion": "not_run", "recognition": "not_run",
                    "knowledge": "not_run", "selection": "unchanged",
                })
        except BaseException as error:
            retain(args.output / "failure.json", {
                "status": "failed", "error_type": type(error).__name__, "message": str(error),
            })
            raise


if __name__ == "__main__":
    main()
