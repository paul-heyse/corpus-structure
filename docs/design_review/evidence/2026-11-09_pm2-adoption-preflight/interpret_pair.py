"""Bind both matched native candidate lists to the identical released d1 question."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.orchestrate.pm2_stage import InterpretationRunRequest
from corpus_structure.semantic.contextual_storage import (
    RetainedCandidateListRef,
    read_interpretation_candidates,
)
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_bytes())


def request(run_ids):
    cases = load(HERE / "raw/focal-cases.json")
    parser = load(HERE / "raw/dipo-request.json")
    profile = load(HERE.parent / "2026-11-09_pm2-interpretation-pair/raw/revised-request.json")[
        "scopes"
    ][0]["profile"]
    parser_scopes = {tuple(s["extent"]): s["source"] for s in parser["scopes"]}
    run, task = map(table, ("ops.run", "ops.task"))
    scopes = []
    bindings = {}
    with (
        open_runtime_engine(Settings(), "pm2-competitive-d1-input", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        for run_id in run_ids:
            selected = bind_completed_result(conn, run_id)
            page = read_source_contributions(
                conn,
                prepared=selected.prepared,
                run_id=run_id,
                cut_id=selected.completed_cut_id,
                source_view_id=391,
                method="retrieve.contextual",
                operation_version="11",
                include_details=True,
                limit=1000,
            )
            (operation,) = [row for row in page.operations if row.get("contextual_enrichment")]
            lists = {
                row["occurrence_id"]: row
                for row in operation["contextual_enrichment"]["candidate_lists"]
            }
            carriers = {
                row["occurrence_id"]: row
                for row in page.contributions
                if row["semantic_type"] == "contextual.located_mention"
            }
            for name, case in cases.items():
                occurrence = case["occurrence_id"]
                carrier, retained = carriers[occurrence], lists[occurrence]
                runtime = conn.scalar(
                    select(run.c.runtime_id)
                    .join(task, task.c.run_id == run.c.id)
                    .where(task.c.id == carrier["origin_task_id"])
                )
                reference = RetainedCandidateListRef.model_validate(
                    dict(
                        carrier=dict(
                            contribution_id=carrier["contribution_id"],
                            project_id=parser["project"],
                            release_id=selected.prepared.release_id,
                            run_id=run_id,
                            cut_id=selected.completed_cut_id,
                            result_revision=selected.binding.data_revision,
                            selected_task_id=carrier["selected_task_id"],
                            origin_task_id=carrier["origin_task_id"],
                            runtime_fingerprint=runtime,
                        ),
                        operation_key=operation["operation_key"],
                        list_id=retained["list_id"],
                    )
                )
                resolved = read_interpretation_candidates(
                    conn,
                    reference,
                    source_pin=carrier["pin"],
                    project_id=parser["project"],
                    release_id=parser["release"],
                )
                if not 1 <= len(resolved.targets) <= 12:
                    raise ValueError(
                        "candidate list cannot be submitted to the bounded interpreter"
                    )
                extent = tuple(case["extent"])
                scopes.append(
                    dict(
                        source=parser_scopes[extent],
                        extent=extent,
                        profile=profile,
                        family="contextual_link_assessment_v1",
                        version="2",
                        questions=["concept_link"],
                        retrieval=reference,
                    )
                )
                bindings[f"{run_id}:{retained['list_id']}"] = dict(
                    case=name,
                    run_id=run_id,
                    ranks=[
                        dict(target_id=entry.target_id, rank=entry.rank)
                        for entry in resolved.targets
                    ],
                )
    return dict(
        request=InterpretationRunRequest.model_validate(dict(parser, scopes=scopes)).model_dump(
            mode="json"
        ),
        bindings=bindings,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("literal", type=int)
    cli.add_argument("enriched", type=int)
    args = cli.parse_args()
    print(canonical_bytes(request((args.literal, args.enriched))).decode())
