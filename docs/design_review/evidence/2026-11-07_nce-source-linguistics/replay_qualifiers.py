"""Run a bounded native predicate discovery pass on four additional frozen opportunities."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from replay import BASELINE, prepared_release, retain, run_method

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

CASES = {
    "789223b6033f": "event-f",
    "c0778b4324c6": "positive-variance",
    "dd40f6c3f444": "normal-parameters",
    "66139740c4ca": "zero-wait",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, args.destination, args.release)
    source = BASELINE / "assessment/benefit-account/current35.json"
    cases = [c for c in json.loads(source.read_bytes())
             if any(c["component_id"].startswith(key) for key in CASES)]
    assert len(cases) == len(CASES)
    selections = []
    with open_runtime_engine(settings, "nce-qualifier-probe", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            for case in cases:
                pin = case["source_pin"]["source"]
                view = load_source_view(conn, pin["source_view_id"], analysis=False)
                pieces = tuple(p for p in view.pieces if p["kind"] == "native_text")
                original = case["observed"]
                assert all(
                    view.text[original[name]["start"]:original[name]["end"]] == original[name]["text"]
                    for name in ("term", "content")
                )
                affected = [
                    i for i, piece in enumerate(pieces)
                    if any(piece["start"] < original[name]["end"]
                           and original[name]["start"] < piece["end"] for name in ("term", "content"))
                ]
                # Include two preceding and following native pieces for local qualifier context.
                selections.append(StructuralPassageSelection(
                    run_id=pin["run_id"], source_view_id=view.ref.id,
                    passage_id=CASES[case["component_id"][:12]],
                    start=pieces[max(0, min(affected) - 2)]["start"],
                    end=pieces[min(len(pieces) - 1, max(affected) + 2)]["end"],
                    scope=original["scope"],
                ))
        bounded = prepare_structural_sources(engine, selections)
    inputs = StructuralInput(
        question="Locate existing host and qualifier evidence for four frozen opportunities",
        scope="selected exact original GS120 passages and adjacent local context",
        inventory_id="nce-additional-qualifiers-1",
        policy_id="source-grounded-private-proposals-2",
        sources=bounded.sources,
        passages=bounded.passages,
        dependencies=("benefit-account:" + sha256(source.read_bytes()).hexdigest(),),
    )
    retain(args.destination / "frozen-inputs.json", [
        dict(passage=selection.passage_id, case=case["component_id"],
             expectation=case["condition_scope_detail"])
        for selection, case in zip(selections, cases, strict=True)
    ])
    run_method(
        settings, prepared, ScopedRelationsMethod(),
        dict(inputs=inputs.model_dump(mode="json"), structural_input_digest=inputs.identity,
             interpretation_mode="independent"),
        inputs, args.destination / "scoped", "nce-additional-qualifiers", args.destination.name,
    )


if __name__ == "__main__":
    main()
