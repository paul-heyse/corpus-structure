"""Verify exact original standard-normal and recovered Table 6.1 endpoints."""

import argparse
from hashlib import sha256
from pathlib import Path

from replay_selected import PARENT, prepared_release, retain, run_method

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.settings import Settings

REFERENCE = (
    Path(__file__).resolve().parent.parent
    / "2026-11-06_wce-completion-repair"
    / "source-references/source-reference.json"
)
NORMAL = (143, 117, "normal-recap", "#/texts/20", "#/texts/30")
DICE = (209, 159, "dice-program", "#/texts/30", "#/texts/37")


def select_passages(engine):
    with read_snapshot(engine) as conn:
        selections = []
        for run_id, view_id, name, first, last in (NORMAL, DICE):
            view = load_source_view(conn, view_id, analysis=False)
            (start,) = tuple(
                p["start"]
                for p in view.pieces
                if p.get("item_ref") == first and p["kind"] == "native_text"
            )
            (end,) = tuple(
                p["end"]
                for p in view.pieces
                if p.get("item_ref") == last and p["kind"] == "native_text"
            )
            selections.append(
                StructuralPassageSelection(
                    run_id=run_id,
                    source_view_id=view_id,
                    passage_id=name,
                    start=start,
                    end=end,
                    scope="grinstead-snell-physical191-310",
                )
            )
    return prepare_structural_sources(engine, tuple(selections))


def assert_edge(page, kind, anchors):
    rows = {
        item["row"]["contribution_id"]: item["row"]
        for item in page.items
        if item["population"] == "contribution"
    }
    matches = []
    for row in rows.values():
        if row.get("kind") != "relation" or not row["item_key"].startswith(kind + ":"):
            continue
        if not all(endpoint["contribution_id"] in rows for endpoint in row["endpoints"]):
            continue
        endpoints = [rows[endpoint["contribution_id"]] for endpoint in row["endpoints"]]
        if len(endpoints) != len(anchors):
            continue
        if all(
            any(
                anchor["pointer"] == pointer
                and anchor["source_piece"] == text
                and (start is None or (anchor["start"], anchor["end"]) == (start, end))
                for anchor in endpoint["anchors"]
            )
            for endpoint, (pointer, text, start, end) in zip(endpoints, anchors, strict=True)
        ):
            matches.append(row)
    (match,) = matches
    return match["contribution_id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    output = args.destination
    output.mkdir(parents=True, exist_ok=True)

    settings = Settings()
    prepared = prepared_release(settings, output, args.release)
    with open_runtime_engine(settings, "nce-links-prepare", purpose="read") as engine:
        selected = select_passages(engine)
    inputs = StructuralInput(
        question="Resolve the standard-normal recap and Table 6.1 procedure reference",
        scope="selected GS120 original and caption-recovered views",
        inventory_id="nce06-fixed-endpoint-controls-1",
        policy_id="source-grounded-private-proposals-2",
        sources=selected.sources,
        passages=selected.passages,
        dependencies=("source-reference:" + sha256(REFERENCE.read_bytes()).hexdigest(),),
    )
    run = run_method(
        settings,
        prepared,
        ScopedRelationsMethod(),
        {
            "inputs": inputs.model_dump(mode="json"),
            "structural_input_digest": inputs.identity,
            "work_bindings": [
                {
                    "native_content_digest": digest,
                    "source_work": PARENT,
                    "provenance": "Original GS120 source reference and native product pins",
                }
                for digest in sorted({ref.native_content_digest for ref in inputs.sources})
            ],
        },
        inputs,
        output / "native",
        "nce06-fixed-endpoints",
        output.name,
    )
    requests = tuple(
        ContributionRequest(
            run_id=run["run_id"],
            source_view_id=view_id,
            method=ScopedRelationsMethod.name,
            include_details=True,
            include_interpretation=True,
            limit=1000,
            page_bytes=16_000_000,
            max_bytes=64_000_000,
        )
        for _, view_id, *_ in (NORMAL, DICE)
    )
    with (
        open_runtime_engine(settings, "nce-links-assess", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        normal, dice = (serve_contributions(conn, request) for request in requests)
    if not normal.population_paging_complete or not dice.population_paging_complete:
        raise ValueError("link assessment is incomplete")
    z = assert_edge(
        normal,
        "declares",
        (
            ("#/texts/30", "Z", 242, 243),
            ("#/texts/21", "standard normal random variable", 130, 161),
        ),
    )
    table = assert_edge(
        dice,
        "artifact_reference_target",
        (
            ("#/texts/30", "Table 6.1", None, None),
            ("#/texts/37", "Table 6.1", None, None),
        ),
    )
    rows = [item["row"] for item in normal.items if item["population"] == "contribution"]
    (external,) = [
        row
        for row in rows
        if row["kind"] == "occurrence"
        and source_python(row["value"]).get("resolution") == "external_target_unavailable"
        and any(
            anchor["pointer"] == "#/texts/20" and anchor["source_piece"] == "Box and Muller.9"
            for anchor in row["anchors"]
        )
    ]
    if any(
        endpoint["contribution_id"] == external["contribution_id"]
        for row in rows
        for endpoint in row.get("endpoints", ())
    ):
        raise ValueError("unresolved external citation unexpectedly has a selected edge")
    retain(
        output / "result.json",
        {
            "run": run,
            "standard_normal": z,
            "table_6_1": table,
            "unresolved_external": external["contribution_id"],
        },
    )
    retain(
        output / "selection.json",
        ReviewSelection(selections=requests, max_bytes=256_000_000).model_dump(
            mode="json", exclude_none=True
        ),
    )


if __name__ == "__main__":
    main()
