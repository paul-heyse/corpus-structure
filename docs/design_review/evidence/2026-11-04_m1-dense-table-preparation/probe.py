"""Read retained run10 source21 and prepare bounded contexts without model execution."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.source_preparation import POLICY, prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    task, config, run = map(table, ("ops.task", "ops.method_config", "ops.run"))
    with (
        open_runtime_engine(Settings(), "m1-dense-preparation-probe", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        selected = conn.execute(
            select(task.c.id, task.c.unit_id, config.c.params, run.c.release_id)
            .join(config, config.c.id == task.c.method_config_id)
            .join(run, run.c.id == task.c.run_id)
            .where(task.c.id == 27, task.c.run_id == 10)
        ).mappings().one()
        budget = PublishedReadBudget(20_000, 128 * 1024**2)
        reader = BoundReader(
            conn, 10, open_release(conn, selected["release_id"]), analysis=False,
            read_budget=budget,
        )
        view = reader.source_view(selected["unit_id"])
        params = selected["params"]
        chars, pieces = params["max_context_chars"], params["max_context_pieces"]
        profile = AnnotationProfile(SentenceConfig.model_validate(params["sentences"]))
        annotations, errors, _ = consume_annotations(reader, view, profile)
        prepared = prepare_source(
            view, profile=profile, max_chars=chars, max_pieces=pieces,
            max_annotation_chars=params["max_annotation_chars"], reader=reader,
            read_budget=budget, persisted_annotations=annotations, annotation_errors=errors,
        )
        tables = []
        for node in view.items:
            if "table_cells" not in node.get("data", {}):
                continue
            cells = node["data"]["table_cells"]
            expected = {
                index for index, cell in enumerate(cells)
                if not cell.get("column_header") and not cell.get("row_header")
            }
            selections = [s for s in prepared.selections if s.region == node["self_ref"]]
            targets = Counter(
                target.cell_index for selection in selections
                for target in selection.table_targets or ()
            )
            serialized = [s.context(
                prepared.source, preparation=prepared.preparation, related=prepared.related,
                max_chars=chars, max_pieces=pieces,
            ) for s in selections]
            region = next(r for r in prepared.regions if r.pointer == node["self_ref"])
            tables.append(dict(
                pointer=node["self_ref"], native_cells=len(cells), eligible_cells=len(expected),
                contexts=len(selections), target_counts=dict(sorted(targets.items())),
                missing_targets=sorted(expected - targets.keys()),
                duplicate_targets=sorted(index for index, count in targets.items() if count != 1),
                unrelated_targets=sorted(targets.keys() - expected),
                max_serialized_chars=max((len(c.text) for c in serialized), default=0),
                max_serialized_intervals=max((len(c.intervals) for c in serialized), default=0),
                region_outcome=region.outcome, region_reason=region.reason,
            ))
        result = dict(
            run_id=10, task_id=27, source_view_id=view.ref.id, release_id=selected["release_id"],
            projection_digest=view.ref.projection_digest, policy=POLICY,
            max_context_chars=chars, max_context_pieces=pieces, tables=tables,
            scope="retained native source and annotation preparation only",
            provider_execution="not_run", knowledge_capture_accuracy="not_established",
        )
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("result.json")
    with path.open("xb") as stream:
        stream.write(canonical_bytes(result))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
