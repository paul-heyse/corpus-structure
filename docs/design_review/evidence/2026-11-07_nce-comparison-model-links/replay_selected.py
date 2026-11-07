"""Run the selected NCE-03 through NCE-06 arms on authenticated retained development cuts."""

import argparse
import json
import sys
from pathlib import Path

import yaml

from corpus_structure.methods.gliner import GlinerProfile
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)
from corpus_structure.settings import Settings

SOURCE_EVIDENCE = Path(__file__).resolve().parent.parent / "2026-11-07_nce-source-linguistics"
sys.path.insert(0, str(SOURCE_EVIDENCE))
from replay import benefit_inputs, prepared_release, retain, run_method  # noqa: E402, I001
from journey_support import PARENT as PARENT  # noqa: E402
from journey_support import completed_metadata as completed_metadata  # noqa: E402
from journey_support import task_custody as task_custody  # noqa: E402


def gliner_profile():
    """Load the declared repository profile, including immutable artifact hashes."""
    methods = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_bytes())
    baseline = methods["configs"]["extract.m1_candidates"]["default"]
    profile = GlinerProfile(
        snapshot=Path(baseline["snapshot"]),
        checkpoint=baseline["checkpoint"],
        revision=baseline["revision"],
        artifact_hashes=tuple(tuple(item) for item in baseline["artifact_hashes"]),
        threads=baseline["threads"],
    )
    return profile, methods


def definition_request(settings, arm, output):
    from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod

    with open_runtime_engine(settings, "nce-definition-selection", purpose="read") as engine:
        inputs, cases = benefit_inputs(engine)
    retain(output / "source-judgments.json", cases)
    profile, methods = gliner_profile()
    named_rules = methods["configs"]["extract.m1_candidates"]["witnessed"]["annotation_rules"]
    description, overlap = {
        "bare": ("bare", None),
        "described": ("described", None),
        "flat": ("bare", "flat"),
        "nested": ("bare", "nested"),
        "allow": ("bare", "allow"),
    }[arm]
    config = {
        "target_ids": tuple(passage.passage_id for passage in inputs.passages),
        "profile": profile,
        "description_arm": description,
        "evaluation_overlap": overlap,
        "threshold": 0.5,
        "annotation_rules": named_rules,
    }
    return DefinitionComponentsMethod(), inputs, config, "definition_components"


def comparison_request(selection):
    from corpus_structure.methods.structural_products import StructuralComparisonMethod

    inputs = StructuralInput.model_validate(selection["inputs"])
    config = {
        key: selection[key] for key in ("left_id", "right_id", "left_reading", "right_reading")
    }
    return StructuralComparisonMethod(), inputs, config, "qualified_comparison"


def classification_request(selection, arm):
    from corpus_structure.methods.clause_classification import ClauseClassificationMethod

    inputs = StructuralInput.model_validate(selection["inputs"])
    profile, _ = gliner_profile()
    config = {"focuses": selection["focuses"], "profile": profile, "context_policy": arm}
    return ClauseClassificationMethod(), inputs, config, "clause_classification"


def execute(settings, prepared, output, request, label):
    method, inputs, config, kind = request
    output.mkdir(parents=True, exist_ok=True)
    try:
        run = run_method(
            settings,
            prepared,
            method,
            {
                **config,
                "inputs": inputs.model_dump(mode="json"),
                "structural_input_digest": inputs.identity,
            },
            inputs,
            output / "native",
            label,
            output.name,
        )
    finally:
        close = getattr(method, "close", None)
        if close is not None:
            close()
    selection = StructuralExportRequest(run_id=run["run_id"], cut_id=run["cut_id"], kind=kind)
    with (
        open_runtime_engine(settings, "nce-joined-replay-reader", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        page = read_structural_export_page(conn, selection)
    if len(page.reports) != 1:
        raise ValueError("expected one exact retained report")
    retain(output / "product.json", page.reports[0].model_dump(mode="json"))
    retain(
        output / "selection.json",
        ReviewSelection(structural_selections=(selection,)).model_dump(
            mode="json", exclude_none=True
        ),
    )
    print(json.dumps({"run": run, "product": page.reports[0].product_id}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release", required=True)
    subparsers = parser.add_subparsers(dest="package", required=True)
    definitions = subparsers.add_parser("definitions")
    definitions.add_argument("arm", choices=("bare", "described", "flat", "nested", "allow"))
    comparison = subparsers.add_parser("comparison")
    comparison.add_argument("selection", type=Path)
    classification = subparsers.add_parser("classification")
    classification.add_argument("selection", type=Path)
    classification.add_argument("arm", choices=("exact_focus", "adjacent_sentences"))
    suite = subparsers.add_parser("suite")
    suite.add_argument("selection", type=Path)
    args = parser.parse_args()

    output = args.destination
    output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, output, args.release)
    if args.package == "suite":
        selection = args.selection
        execute(
            settings,
            prepared,
            output / "comparison",
            comparison_request(json.loads((selection / "comparison-selection.json").read_bytes())),
            "comparison",
        )
        for arm in ("bare", "described", "flat", "nested", "allow"):
            label = "definition-" + arm
            destination = output / label
            execute(
                settings,
                prepared,
                destination,
                definition_request(settings, arm, destination),
                label,
            )
        focuses = json.loads((selection / "classification-selection.json").read_bytes())
        for arm in ("exact_focus", "adjacent_sentences"):
            label = "clause-" + arm
            execute(settings, prepared, output / label, classification_request(focuses, arm), label)
        return

    if args.package == "definitions":
        request = definition_request(settings, args.arm, output)
    elif args.package == "comparison":
        request = comparison_request(json.loads(args.selection.read_bytes()))
    else:
        request = classification_request(json.loads(args.selection.read_bytes()), args.arm)
    execute(settings, prepared, output, request, args.package + "-" + getattr(args, "arm", "fixed"))


if __name__ == "__main__":
    main()
