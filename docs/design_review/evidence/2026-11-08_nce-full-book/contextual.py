"""Replay scoped book citations against the complete selected heading inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from enrich import SCOPE, journey, structural_inputs
from intake import PROJECT
from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import ContextualCandidatesWithNeighborhood
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import installed_runtime_id
from corpus_structure.settings import Settings


def cue_inputs(conn, scoped):
    rows = (
        conn.execute(
            text("""
        SELECT t.unit_id, ct.origin_task_id, m.version, cfg.params, job.release_id,
               job.runtime_id, job.input_realization_id, job.input_revision, job.dependencies
        FROM ops.cut_task ct JOIN ops.task t ON t.id=ct.task_id
        JOIN ops.run job ON job.id=t.run_id
        JOIN ops.method_config cfg ON cfg.id=t.method_config_id
        JOIN ops.method m ON m.id=cfg.method_id
        JOIN ops.task_result r ON r.task_id=ct.origin_task_id
        WHERE ct.cut_id=ANY(:cuts) AND m.name='structure.scoped_relations'
          AND jsonb_path_exists(r.body,
            '$.contributions[*].value.fields[*] ? (
                @.name == "role" && @.value.text == "named_link_subject")')
        ORDER BY t.unit_id
    """),
            {"cuts": [run["cut_id"] for run in scoped]},
        )
        .mappings()
        .all()
    )
    selected = {row["unit_id"]: row for row in rows}
    if len(selected) != len(rows):
        raise ValueError("one exact completed scoped origin is required for each cue view")
    return selected


def run_case(settings, prepared, headings, source, upstream, output, *, repaired):
    scoped, contextual = ScopedRelationsMethod(), ContextualCandidatesWithNeighborhood()
    if repaired:
        from corpus_structure.methods.contextual_candidates import (
            ContextualCandidatesWithNamedBindings,
        )
        from corpus_structure.methods.scoped_relations import ScopedRelationsWithRoleClosure

        scoped = ScopedRelationsWithRoleClosure()
        contextual = ContextualCandidatesWithNamedBindings()
    if upstream["version"] != scoped.version:
        raise ValueError("selected scoped task belongs to a different producer version")
    configs = {
        scoped.name: {"current": upstream["params"]},
        contextual.name: {
            "book": dict(
                profile="e5",
                source_dependency_method=scoped.name,
                semantic_types=["structural.located_participant"],
                section_sources=[ref.model_dump(mode="json") for ref in headings],
                source_product_digest=source.native_content_digest,
                source_projection_digest=source.projection_digest,
                scope=SCOPE,
            )
        },
    }
    registry = MethodRegistry((scoped, contextual), MethodsFile(configs=configs))
    output.mkdir(parents=True, exist_ok=True)
    journey.retain(output / "configuration.json", configs)
    completed = output / "completed.json"
    if completed.exists():
        return json.loads(completed.read_bytes())
    ready = output / "source-ready.json"
    if ready.exists():
        run_id = json.loads(ready.read_bytes())["run_id"]
        return journey.finish_source_stage(settings, run_id, output)

    with open_runtime_engine(settings, "nce-full-book-contextual", purpose="write") as engine:
        result = run_source_methods(
            engine,
            project_id=PROJECT,
            prepared=prepared,
            binding=OperationBinding(
                prepared.release_id,
                upstream["input_realization_id"],
                upstream["input_revision"],
                bytes(upstream["dependencies"]),
            ),
            registry=registry,
            graph=Graph(
                (
                    (
                        Stage.SCOPE,
                        (
                            Step(scoped.name + "/current"),
                            Step(contextual.name + "/book", upstream=(scoped.name,)),
                        ),
                    ),
                ),
                policy_propose=False,
            ),
            method_settings=MethodSettings(
                data_dir=output / "data", model_cache=Path.home() / ".cache/docling/models"
            ),
            guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(),
            policy_source=None,
            kind="full",
            selected_sources=(source,),
        )
        with read_snapshot(engine) as conn:
            reused = conn.execute(
                text("""
                SELECT t.status, t.reused_task_id
                FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id
                JOIN ops.method m ON m.id=c.method_id
                WHERE t.run_id=:run AND t.unit_id=:view AND m.name=:method
                """),
                dict(run=result.run_id, view=source.source_view_id, method=scoped.name),
            ).one()
        if (reused.status, reused.reused_task_id) != ("reused", upstream["origin_task_id"]):
            raise ValueError("contextual producer did not reuse its exact scoped predecessor")
    journey.retain(ready, result.model_dump(mode="json"))
    if result.status != "source_ready":
        raise ValueError("book citation task did not reach source readiness")
    return journey.finish_source_stage(settings, result.run_id, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--repaired", action="store_true")
    args = parser.parse_args()
    inventory = json.loads((args.output / "source-inventory.json").read_bytes())
    scoped = json.loads((args.output / "scoped-summary.json").read_bytes())
    source_run = inventory["run"]["run_id"]
    views = [v for v in inventory["views"] if v["analysis_eligible"] and v["chars"]]
    settings = Settings()
    with open_runtime_engine(
        settings, "nce-full-book-contextual-inventory", purpose="read"
    ) as reader:
        with read_snapshot(reader) as conn:
            prepared = open_release(conn, args.release)
            candidates = cue_inputs(conn, scoped)
        runtime = installed_runtime_id(prepared)
        if any(
            (row["release_id"], row["runtime_id"]) != (prepared.release_id, runtime)
            for row in candidates.values()
        ):
            raise ValueError("scoped cue inputs differ from the installed release/runtime")
        atlas = structural_inputs(reader, source_run, views, "heading-atlas")
        if len(atlas.sources) > 256:
            raise ValueError("complete heading inventory exceeds the contextual source bound")
        results = [
            run_case(
                settings,
                prepared,
                atlas.sources,
                source,
                candidates[source.source_view_id],
                args.output / f"contextual-{source.source_view_id}",
                repaired=args.repaired,
            )
            | {"source_view_id": source.source_view_id}
            for source in atlas.sources
            if source.source_view_id in candidates
        ]
    journey.retain(
        args.output / "contextual-summary.json",
        dict(
            eligible_cue_views=sorted(candidates),
            heading_sources=len(atlas.sources),
            results=results,
        ),
    )


if __name__ == "__main__":
    main()
