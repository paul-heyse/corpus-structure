"""Read-only native rich-cell assembly on retained source and annotation products."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.record_assembly import (
    OCCURRENCE_POLICY,
    assemble_native_records,
    native_table_groups,
)
from corpus_structure.methods.source_preparation import POLICY, prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from sqlalchemy import select


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    tasks, configs, runs = map(table, ("ops.task", "ops.method_config", "ops.run"))
    with open_runtime_engine(Settings(), "m1-rich-cell-assembly-probe", purpose="read") as engine, read_snapshot(engine) as conn:
        selected = conn.execute(select(tasks.c.unit_id, configs.c.params, runs.c.release_id)
            .join(configs, configs.c.id == tasks.c.method_config_id)
            .join(runs, runs.c.id == tasks.c.run_id)
            .where(tasks.c.id == 27, tasks.c.run_id == 10)).mappings().one()
        budget = PublishedReadBudget(20_000, 128 * 1024**2)
        reader = BoundReader(conn, 10, open_release(conn, selected["release_id"]),
                             analysis=False, read_budget=budget)
        view = reader.source_view(selected["unit_id"])
        params = selected["params"]
        chars, pieces = params["max_context_chars"], params["max_context_pieces"]
        profile = AnnotationProfile(SentenceConfig.model_validate(params["sentences"]))
        annotations, errors, _ = consume_annotations(reader, view, profile)
        prepared = prepare_source(view, profile=profile, max_chars=chars, max_pieces=pieces,
            max_annotation_chars=params["max_annotation_chars"], reader=reader, read_budget=budget,
            persisted_annotations=annotations, annotation_errors=errors)
        results = []
        for selection in prepared.selections:
            if selection.families != ("table",):
                continue
            context = selection.context(prepared.source, preparation=prepared.preparation,
                related=prepared.related, max_chars=chars, max_pieces=pieces)
            if selection.table_targets is None:
                raise ValueError("new bounded table context lacks its native target binding")
            targets = selection.table_targets
            groups = native_table_groups(context, table_pointer=selection.region,
                cells=tuple(target.cell_index for target in targets),
                row_paths={target.cell_index: target.row_path for target in targets},
                header_paths={target.cell_index: target.header_path for target in targets})
            assembled = assemble_native_records(reader.prepared, context,
                contract="TableRecordFields", occurrence_roles=("table", "cell"),
                policy_version=params["record_policy_version"], occurrence_policy=OCCURRENCE_POLICY,
                groups=groups)
            rows = [record.model_dump(mode="json") for record in assembled.records]
            results.append(dict(context_digest=context.dependency_digest,
                selection=asdict(selection), records=rows, diagnostics=[asdict(d) for d in assembled.diagnostics]))
        rows = [row for result in results for row in result["records"]]
        fields = [field for row in rows for field in row["fields"]]
        summary = dict(scope="retained source + annotation read; new pure native-cell assembly only",
            run_id=10, task_id=27, release_id=selected["release_id"], source_view_id=view.ref.id,
            projection_digest=view.ref.projection_digest, preparation_policy=POLICY,
            table_contexts=len(results), targets=sum(len(result["selection"]["table_targets"]) for result in results),
            candidate_records=len(rows), unique_occurrences=len({row["record_id"] for row in rows}),
            present_header_paths=sum(field["role"] == "header_path" and field["state"] == "present" for field in fields),
            present_row_identities=sum(field["role"] == "row_identity" and field["state"] == "present" for field in fields),
            diagnostics=dict(Counter(d["code"] for result in results for d in result["diagnostics"])),
            model_execution="not_run", annotation_execution="not_run", publication="not_run", quality_claim="not_established")
        inputs = canonical_bytes(dict(source=asdict(prepared.source), source_configuration=params,
                                      annotations=[asdict(a) for a in annotations]))
        (args.out / "source-inputs.json").write_bytes(inputs)
        summary["source_inputs_sha256"] = sha256(inputs).hexdigest()
        (args.out / "result.json").write_bytes(canonical_bytes(dict(summary=summary, contexts=results)))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
