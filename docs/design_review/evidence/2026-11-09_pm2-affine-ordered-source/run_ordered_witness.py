"""Prepare or run the exact non-Chandra affine producer without re-recognition."""

import argparse
import json
from pathlib import Path

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.methods.scoped_relations import (
    ScopedRelationsOrderedConfig,
    ScopedRelationsWithOrderedWitness,
)
from corpus_structure.methods.witnessed_source_links import (
    ORDERED_VERSION,
    QUESTION,
    ordered_witness_selection,
)
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ADOPTION = HERE.parent / "2026-11-09_pm2-adoption/raw"
WORKSPACE = Path("build/pm2-affine-ordered-witness")
WIDER_START = 61001


def physical(source):
    return (
        source.project_id,
        source.source_view_id,
        source.native_task_id,
        source.native_product_key,
        source.native_content_digest,
        source.projection_digest,
        source.recipe_digest,
        source.coordinate_version,
    )


def prepare(settings, release, rebound_run=None):
    frozen = StructuralInput.model_validate_json((ADOPTION / "query-inputs.json").read_bytes())
    (query,) = [p for p in frozen.passages if p.passage_id == "affine"]
    (source,) = [s for s in frozen.sources if s.identity == query.source_ref]
    with open_runtime_engine(settings, "pm2-ordered-witness-prepare", purpose="read") as engine:
        actual = prepare_structural_sources(
            engine,
            tuple(
                StructuralPassageSelection(
                    run_id=rebound_run or source.run_id,
                    source_view_id=source.source_view_id,
                    passage_id=passage_id,
                    start=start,
                    end=query.end,
                    scope=query.scope,
                    effective_version=query.effective_version,
                )
                for passage_id, start in (
                    (query.passage_id, query.start),
                    ("affine-witness-source", WIDER_START),
                )
            ),
            read_budget=PublishedReadBudget(max_rows=100_000, max_bytes=256 * 1024 * 1024),
        )
        (selected,) = actual.sources
        with read_snapshot(engine) as conn:
            conn.execute(
                select(
                    func.ops.validate_structural_source(
                        cast(selected.model_dump(mode="json"), JSONB)
                    )
                )
            ).scalar_one()
    rebound_query = query.model_copy(update={"source_ref": selected.identity})
    if physical(selected) != physical(source) or actual.passages[0] != rebound_query:
        raise ValueError("the affine query differs from the frozen original source cut")
    if rebound_run is not None and selected.release_id != release:
        raise ValueError("rebound source is not completed under the producer release")
    (view,) = [
        row
        for row in json.loads((ADOPTION / "m1-cut-517-views.json").read_bytes())
        if row["id"] == source.source_view_id
    ]
    inputs = StructuralInput.model_validate(
        frozen.model_dump(mode="python")
        | {
            "sources": (selected,),
            "passages": (rebound_query,),
            "exclusions": (),
            "dependencies": tuple(
                selected.identity if d == source.identity else d for d in frozen.dependencies
            ),
        }
    )
    configuration = ScopedRelationsOrderedConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        interpretation_mode="feasibility",
        ordered_formula_witness=actual.passages[1],
    )
    return {
        "project": source.project_id,
        "release": release,
        "realization": "source:pm2-affine-ordered-witness:" + release,
        "source_key": view["key"],
        "configuration": configuration.model_dump(mode="json"),
    }


def run(settings, request, *, rebind=False):
    cfg = ScopedRelationsOrderedConfig.model_validate(request["configuration"])
    if cfg.ordered_formula_witness is None or cfg.inputs is None:
        raise ValueError("run requires an explicit exact ordered source witness")
    (source,) = cfg.inputs.sources
    if source.project_id != request["project"]:
        raise ValueError("producer run and original source require the same project")
    if rebind:
        method = M1Annotations()
        params = {"source_projection_digest": source.projection_digest}
        stage = Stage.EXTRACT
    else:
        method = ScopedRelationsWithOrderedWitness()
        params = cfg.model_dump(mode="json")
        stage = Stage.SCOPE
    registry = MethodRegistry(
        (method,),
        MethodsFile(configs={method.name: {"affine": params}}),
    )
    with open_runtime_engine(settings, "pm2-ordered-witness-run", purpose="write") as engine:
        if rebind:
            with engine.begin() as conn:
                prepared = open_release(conn, request["release"])
                initialize_source_project(
                    conn,
                    project_id=ProjectId(request["project"]),
                    release_id=ReleaseId(request["release"]),
                    realization_id=RealizationId(request["realization"]),
                    projection_context=prepared,
                )
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, request["release"])
            realization = table("data.realization")
            revision = conn.execute(
                select(realization.c.data_revision).where(
                    realization.c.realization_id == request["realization"],
                    realization.c.release_id == request["release"],
                    realization.c.project_id == request["project"],
                )
            ).scalar_one()
        report = run_source_methods(
            engine,
            project_id=request["project"],
            prepared=prepared,
            binding=OperationBinding(
                request["release"], request["realization"], revision, canonical_bytes(request)
            ),
            registry=registry,
            graph=Graph(((stage, (Step(method.name + "/affine"),)),), policy_propose=False),
            method_settings=MethodSettings(
                data_dir=WORKSPACE, model_cache=Path.home() / ".cache/docling/models"
            ),
            selected_sources=cfg.inputs.sources,
            fresh=(method.name,),
            kind="slice",
        )
    return report.model_dump(mode="json")


def selection(run_id, task_id, request, max_bytes):
    cfg = ScopedRelationsOrderedConfig.model_validate(request["configuration"])
    if cfg.inputs is None or cfg.ordered_formula_witness is None:
        raise ValueError("selection requires the original ordered source input")
    (source,) = cfg.inputs.sources
    (query,) = cfg.inputs.passages
    pin = {
        "source": request["source_key"],
        "source_view_id": source.source_view_id,
        "native_product_task_id": source.native_task_id,
        "product_key": source.native_product_key,
        "product_digest": source.native_content_digest,
        "projection_digest": source.projection_digest,
        "recipe_digest": source.recipe_digest,
    }
    scope = ordered_witness_selection(query, cfg.ordered_formula_witness)
    selection = ReviewSelection(
        selections=(
            ContributionRequest(
                run_id=run_id,
                source_view_id=source.source_view_id,
                method=ScopedRelationsWithOrderedWitness.name,
                operation_key=operation_identity(QUESTION, ORDERED_VERSION, pin, scope),
                selected_task_id=task_id,
                include_details=True,
                limit=1000,
                page_bytes=32_000_000,
                max_bytes=128_000_000,
            ),
        ),
        max_bytes=max_bytes,
    )
    return selection.model_dump(mode="json", exclude_none=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    stages = cli.add_subparsers(dest="stage", required=True)
    preparation = stages.add_parser("prepare")
    preparation.add_argument("--release", required=True)
    preparation.add_argument("--source-run", type=int)
    for name in ("rebind", "run"):
        attempt = stages.add_parser(name)
        attempt.add_argument("request", type=Path)
    review = stages.add_parser("selection")
    review.add_argument("request", type=Path)
    review.add_argument("run_id", type=int)
    review.add_argument("task_id", type=int)
    review.add_argument("--max-bytes", type=int, default=536_870_912)
    args = cli.parse_args()
    if args.stage == "prepare":
        result = prepare(Settings(), args.release, args.source_run)
    else:
        request = json.loads(args.request.read_bytes())
        result = (
            run(Settings(), request, rebind=args.stage == "rebind")
            if args.stage in {"rebind", "run"}
            else selection(args.run_id, args.task_id, request, args.max_bytes)
        )
    print(canonical_bytes(result).decode())


if __name__ == "__main__":
    main()
