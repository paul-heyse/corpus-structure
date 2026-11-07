"""Replay the completed NCE-02 scope on original frozen source cuts."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from replay import BASELINE, prepared_release, retain, run_method
from replay_qualifiers import CASES

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

SOURCE = BASELINE / "assessment/benefit-account/current35.json"
FORMULA = BASELINE.parent / "2026-11-06_wce-completion-repair/composition/native-retained004/source-judgment.json"

# Exact source extents were inspected independently of the new producer.
CONTROLS = {
    131: ("event-f", 0, 582, (("event_compound_then", (39, 121), "condition", "defined"),)),
    146: ("positive-variance", 5389, 5885,
          (("adjacent_variance_premise", (5559, 5613), "assumption", "defined"),)),
    116: ("normal-parameters", 13822, 15165, (
        ("nominal_parameter_pair", (14593, 14616), "parameterization", "defined"),
        ("parameter_positive", (14967, 14995), "assumption", "defined"),
    )),
    145: ("zero-wait", 2473, 3190,
          (("customer_population_inclusion", (2933, 2975), "population_inclusion", "counting"),)),
    117: ("formula-z", 2469, 2717, ()),
}


def assess(page, expected):
    rows = {
        item["row"]["contribution_id"]: item["row"]
        for item in page.items if item["population"] == "contribution"
    }
    selected = []
    for variant, extent, kind, expected_predicate in expected:
        (cue,) = [
            row for row in rows.values()
            if row.get("component", {}).get("variant") == variant
            and row["component"]["kind"] == "predicate_cue"
        ]
        (link,) = [
            row for row in rows.values()
            if row.get("component", {}).get("qualifier_contribution_id") == cue["contribution_id"]
        ]
        component = link["component"]
        target = rows[component["host_contribution_id"]]["component"]
        member = next(m for m in target["frame_members"] if m["role"] == "predicate")
        predicate = rows[member["contribution"]]["anchors"][0]["source_piece"]
        anchors = cue["anchors"]
        assert tuple((a["start"], a["end"]) for a in cue["component"]["extents"]) == (extent,)
        assert predicate == expected_predicate and component["qualifier_kind"] == kind
        if kind in {"assumption", "condition"}:
            condition = source_python(component["condition"])
            assert condition["kind"] == "escape"
            assert condition["text"] == " ".join(a["source_piece"] for a in anchors)
        else:
            assert "condition" not in component and "qualification" not in component
        selected.append(dict(
            variant=variant, kind=kind, cue=cue["contribution_id"],
            source_extent=extent, text=" ".join(a["source_piece"] for a in anchors),
            host=component["host_contribution_id"], predicate=predicate,
            witness=component.get("host_witness"),
        ))
    if page.selection["source_view_id"] == 117:
        (formula,) = [
            row for row in rows.values()
            if row["kind"] == "occurrence" and any(
                a.get("pointer") == "#/texts/30" and a["start"] == 242 and a["end"] == 243
                for a in row.get("anchors", ())
            )
            and source_python(row["value"]).get("role") == "formula_symbol"
        ]
        assert source_python(formula["value"])["text"] == "Z"
        assert source_python(formula["value"])["syntax_standing"] == "syntax_only"
        selected.append(dict(variant="formula_z", occurrence=formula["contribution_id"]))
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, args.destination, args.release)
    frozen = [
        row for row in json.loads(SOURCE.read_bytes()) if row["component_id"][:12] in CASES
    ]
    pins = {row["source_pin"]["source"]["source_view_id"]: row["source_pin"]["source"]
            for row in frozen}
    pins[117] = json.loads(FORMULA.read_bytes())["source_transform"]["source"]
    with open_runtime_engine(settings, "nce02-inputs", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            selections = []
            for view_id, (name, start, end, _) in CONTROLS.items():
                pin = pins[view_id]
                view = load_source_view(conn, view_id, analysis=False)
                assert view.ref.projection_digest == pin["projection_digest"]
                selections.append(StructuralPassageSelection(
                    run_id=pin["run_id"], source_view_id=view_id, passage_id=name,
                    start=start, end=end, scope="grinstead-snell-physical191-310",
                ))
        selected = prepare_structural_sources(engine, selections)
    inputs = StructuralInput(
        question="Resolve frozen qualifier hosts and recover exact inline formula Z",
        scope="selected exact original GS120 passages and adjacent local context",
        inventory_id="nce02-qualifier-scope-1",
        policy_id="source-grounded-private-proposals-2",
        sources=selected.sources, passages=selected.passages,
        dependencies=("benefit-account:" + sha256(SOURCE.read_bytes()).hexdigest(),
                      "formula-control:" + sha256(FORMULA.read_bytes()).hexdigest()),
    )
    run = run_method(
        settings, prepared, ScopedRelationsMethod(),
        dict(inputs=inputs.model_dump(mode="json"), structural_input_digest=inputs.identity,
             interpretation_mode="independent"),
        inputs, args.destination / "scoped", "nce02-qualifier-scope", args.destination.name,
    )
    requests = tuple(ContributionRequest(
        run_id=run["run_id"], source_view_id=view_id, method=ScopedRelationsMethod.name,
        include_details=True, include_interpretation=True,
        limit=1000, page_bytes=16_000_000, max_bytes=64_000_000,
    ) for view_id in CONTROLS)
    outcomes = {}
    with open_runtime_engine(settings, "nce02-assess", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            for request in requests:
                page = serve_contributions(conn, request)
                assert page.population_paging_complete
                outcomes[request.source_view_id] = assess(page, CONTROLS[request.source_view_id][3])
    retain(args.destination / "qualifier-scope.json", dict(run=run, cases=outcomes))
    retain(args.destination / "selection.json", ReviewSelection(
        selections=requests, max_bytes=256_000_000,
    ).model_dump(mode="json", exclude_none=True))


if __name__ == "__main__":
    main()
