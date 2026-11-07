"""Freeze exact comparison sides and model focuses from completed NCE-02 cuts."""

import argparse
import json
from pathlib import Path

from replay_selected import SOURCE_EVIDENCE, completed_metadata, retain, task_custody

from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings

# Coordinates and expected readings refer to the original selected passage.
FOCUSES = (
    (122, "benefit:122", (1724, 1773), "explanation"),
    (135, "benefit:135", (4354, 4403), "reported_reference"),
    (147, "benefit:147", (296, 350), "definition"),
    (147, "benefit:147", (470, 474), "prescribed_action"),
)


def exact_reference(run, custody, row):
    return RetainedContributionRef(
        contribution_id=row["contribution_id"],
        project_id=run["project_id"],
        run_id=run["run_id"],
        cut_id=run["cut_id"],
        release_id=run["release_id"],
        result_revision=run["result_revision"],
        **custody[row["selected_task_id"]],
    ).model_dump(mode="json")


def composites(conn, run_id, view):
    page = serve_contributions(
        conn,
        ContributionRequest(
            run_id=run_id,
            source_view_id=view,
            method="structure.scoped_relations",
            kind="composite",
            include_details=True,
            limit=500,
            page_bytes=16_000_000,
            max_bytes=64_000_000,
        ),
    )
    if not page.population_paging_complete:
        raise ValueError("selected source page exceeds the declared evidence bound")
    return tuple(item["row"] for item in page.items if item["population"] == "contribution")


def subset(source, passages, refs, question, inventory_id):
    config = json.loads(source.read_bytes())["config"]
    original = StructuralInput.model_validate(config["inputs"])
    selected = tuple(p for p in original.passages if p.passage_id in passages)
    if {p.passage_id for p in selected} != set(passages):
        raise ValueError("retained configuration lacks one of the named passages")
    source_ids = {p.source_ref for p in selected}
    return StructuralInput(
        question=question,
        scope=original.scope,
        inventory_id=inventory_id,
        policy_id=original.policy_id,
        sources=tuple(ref for ref in original.sources if ref.identity in source_ids),
        passages=selected,
        dependencies=(*original.dependencies, *refs),
    ).model_dump(mode="json")


def prepare_comparison(conn, configuration, destination):
    run = completed_metadata(conn, 224)
    custody = task_custody(conn, run)
    frozen = json.loads((SOURCE_EVIDENCE / "qualifier-scope.json").read_bytes())["cases"]
    references, passages = [], []
    for view in (131, 146):
        (case,) = frozen[str(view)]
        (reading,) = tuple(
            row
            for row in composites(conn, 224, view)
            if row.get("component", {}).get("kind") == "predicate_reading"
            and row["component"]["frame"] == case["host"]
        )
        references.append(exact_reference(run, custody, reading))
        passages.append(reading["component"]["scope"])
    inputs = subset(
        configuration,
        passages,
        tuple(ref["contribution_id"] for ref in references),
        "Compare the Event F and correlation definitions with their original premises",
        "nce03-event-correlation-1",
    )
    retain(
        destination,
        {
            "inputs": inputs,
            "left_id": passages[0],
            "right_id": passages[1],
            "left_reading": references[0],
            "right_reading": references[1],
        },
    )


def prepare_classification(conn, configuration, destination, *, run_id=217, selected=FOCUSES):
    run = completed_metadata(conn, run_id)
    custody = task_custody(conn, run)
    populations = {
        view: composites(conn, run_id, view) for view in sorted({f[0] for f in selected})
    }
    focuses = []
    for view, passage, (start, end), _ in selected:
        (frame,) = tuple(
            row
            for row in populations[view]
            if row.get("component", {}).get("kind") == "predicate_frame"
            and row["component"]["scope"] == passage
            and row["component"].get("focus_state") == "exact"
            and any(
                member["role"] == "focus" and member["extents"] == [{"start": start, "end": end}]
                for member in row["component"]["frame_members"]
            )
        )
        focuses.append({"passage_id": passage, "frame": exact_reference(run, custody, frame)})
    inputs = subset(
        configuration,
        {entry["passage_id"] for entry in focuses},
        tuple(entry["frame"]["contribution_id"] for entry in focuses),
        "Compare exact clause focus and bounded neighboring context",
        "nce04-clause-focus-1",
    )
    retain(destination, {"inputs": inputs, "focuses": focuses, "judgments": selected})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("nce02_configuration", type=Path)
    parser.add_argument("initial_scope_configuration", type=Path)
    args = parser.parse_args()
    with (
        open_runtime_engine(Settings(), "nce-compare-model-freeze", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepare_comparison(
            conn, args.nce02_configuration, args.destination / "comparison-selection.json"
        )
        prepare_classification(
            conn,
            args.initial_scope_configuration,
            args.destination / "classification-selection.json",
        )


if __name__ == "__main__":
    main()
