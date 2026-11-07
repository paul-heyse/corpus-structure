"""Compare the native naming proposal with the exact frozen level-set case."""

import argparse
import json
from pathlib import Path

import yaml
from replay import benefit_inputs, prepared_release, retain, run_method

from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)
from corpus_structure.settings import Settings

CASE = "822bb6359ada0a728f424b525b3f030af958a66907511155283f216f21de7613"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, args.destination, args.release)
    with open_runtime_engine(settings, "nce-antecedent-inputs", purpose="read") as engine:
        inputs, cases = benefit_inputs(engine)
    (case,) = [case for case in cases if case["component_id"] == CASE]
    expected = case["corrected_alternatives"][0]
    rules = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_bytes())
    result = run_method(
        settings, prepared, DefinitionComponentsMethod(),
        dict(
            inputs=inputs.model_dump(mode="json"),
            structural_input_digest=inputs.identity,
            use_model=False,
            target_ids=[passage.passage_id for passage in inputs.passages],
            annotation_rules=rules["configs"]["extract.m1_candidates"]["witnessed"]["annotation_rules"],
        ),
        inputs, args.destination / "definition", "nce-definition-antecedent", args.destination.name,
    )
    request = StructuralExportRequest(
        run_id=result["run_id"], cut_id=result["cut_id"], kind="definition_components",
    )
    with open_runtime_engine(settings, "nce-antecedent-result", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            page = read_structural_export_page(conn, request)
    product = page.reports[0].definition_components
    assert product is not None
    (component,) = [
        component for component in product.components
        if component.term.passage_id == "benefit:147"
    ]
    for role in ("term", "content"):
        actual = getattr(component, role)
        assert (actual.start, actual.end, actual.text) == tuple(
            expected[role][key] for key in ("start", "end", "text")
        )
    assert component.interpretation == expected["interpretation"]
    assert (component.content.end, component.term.start) == (295, 325)
    retain(args.destination / "antecedent.json", dict(
        case=CASE, run_id=result["run_id"], cut_id=result["cut_id"], source=case["source_pin"]["source"],
        component=component.model_dump(mode="json"),
    ))
    retain(
        args.destination / "selection.json",
        ReviewSelection(structural_selections=(request,)).model_dump(mode="json", exclude_none=True),
    )


if __name__ == "__main__":
    main()
