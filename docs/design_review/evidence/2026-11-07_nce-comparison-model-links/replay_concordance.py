"""Attach a completed clause observation to a later exact scoped interpretation."""

import argparse
import json
from pathlib import Path

from prepare import FOCUSES, prepare_classification
from replay_selected import (
    classification_request,
    execute,
    prepared_release,
    retain,
    run_method,
    task_custody,
)

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import (
    RetainedStructuralRef,
    StructuralProductReport,
)
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)
from corpus_structure.settings import Settings


def refresh_focuses(settings, prepared, destination, previous):
    """Use the current deterministic producer for a compatible focus-custody control."""
    product = StructuralProductReport.model_validate_json((previous / "product.json").read_bytes())
    sources = tuple(source for source in product.inputs.sources if source.source_view_id == 147)
    passages = tuple(p for p in product.inputs.passages if p.source_ref == sources[0].identity)
    inputs = product.inputs.model_copy(
        update={
            "sources": sources,
            "passages": passages,
            "dependencies": tuple(
                dep
                for dep in product.inputs.dependencies
                if not dep.startswith("source-contribution:")
            ),
        }
    )
    native = destination / "current-scope"
    run = run_method(
        settings,
        prepared,
        ScopedRelationsMethod(),
        {"inputs": inputs.model_dump(mode="json"), "structural_input_digest": inputs.identity},
        inputs,
        native,
        "nce-current-concordance-focus",
        destination.name,
    )
    selection = destination / "current-focuses.json"
    with (
        open_runtime_engine(settings, "nce-current-focuses", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepare_classification(
            conn,
            native / "configuration.json",
            selection,
            run_id=run["run_id"],
            selected=tuple(item for item in FOCUSES if item[0] == 147),
        )
    arm = destination / "current-classifier"
    execute(
        settings,
        prepared,
        arm,
        classification_request(json.loads(selection.read_bytes()), "exact_focus"),
        "nce-current-concordance-classifier",
    )
    return arm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("clause_arm", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)

    settings = Settings()
    prepared = prepared_release(settings, args.destination, args.release)
    clause_arm = (
        refresh_focuses(settings, prepared, args.destination, args.clause_arm)
        if args.refresh
        else args.clause_arm
    )
    original = json.loads((clause_arm / "native/completed.json").read_bytes())
    report = StructuralProductReport.model_validate_json((clause_arm / "product.json").read_bytes())
    selection = StructuralExportRequest(
        run_id=original["run_id"], cut_id=original["cut_id"], kind="clause_classification"
    )
    with (
        open_runtime_engine(settings, "nce-concordance-ref", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        page = read_structural_export_page(conn, selection)
        (task_id,) = page.task_ids
        custody = task_custody(conn, original)[task_id]
    ref = RetainedStructuralRef(
        product_id=report.product_id,
        project_id=original["project_id"],
        run_id=original["run_id"],
        cut_id=original["cut_id"],
        release_id=original["release_id"],
        result_revision=original["result_revision"],
        **custody,
    )
    inputs = report.inputs.model_copy(
        update={"dependencies": (*report.inputs.dependencies, report.product_id)}
    )
    run = run_method(
        settings,
        prepared,
        ScopedRelationsMethod(),
        {
            "inputs": inputs.model_dump(mode="json"),
            "structural_input_digest": inputs.identity,
            "classification_refs": [ref.model_dump(mode="json")],
        },
        inputs,
        args.destination / "native",
        "nce-model-concordance",
        args.destination.name,
    )
    requests = tuple(
        ContributionRequest(
            run_id=run["run_id"],
            source_view_id=source.source_view_id,
            method=ScopedRelationsMethod.name,
            include_details=True,
            limit=1000,
            page_bytes=16_000_000,
            max_bytes=64_000_000,
        )
        for source in inputs.sources
    )
    retain(
        args.destination / "selection.json",
        ReviewSelection(
            selections=requests,
            structural_selections=(selection,),
            max_bytes=256_000_000,
        ).model_dump(mode="json", exclude_none=True),
    )


if __name__ == "__main__":
    main()
