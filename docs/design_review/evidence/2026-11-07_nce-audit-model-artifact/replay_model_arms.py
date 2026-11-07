"""Run the exact pinned model arms independently of comparison regeneration."""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import anyio
from replay_role import cli

from corpus_structure.core.method import UnitView
from corpus_structure.orchestrate.source_reader import ScopedSourceReader
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import StructuralExportRequest
from corpus_structure.settings import Settings

COMPARISON_EVIDENCE = Path(__file__).resolve().parents[1] / "2026-11-07_nce-comparison-model-links"
sys.path.insert(0, str(COMPARISON_EVIDENCE))
from assess_model import evaluate_classification, evaluate_definition  # noqa: E402
from check_delivery import compare  # noqa: E402
from replay_selected import (  # noqa: E402
    classification_request,
    definition_request,
    execute,
    prepared_release,
    retain,
)

DEFINITION_ARMS = ("bare", "described", "flat", "nested", "allow")
CLAUSE_ARMS = ("exact_focus", "adjacent_sentences")


def execute_provider(settings, prepared, output, request):
    """Use authenticated source reads and the real method without publishing a run."""
    method, inputs, config, _ = request
    cfg = method.Config.model_validate(
        {
            **config,
            "inputs": inputs,
            "structural_input_digest": inputs.identity,
        }
    )
    source = inputs.sources[0]
    owner = BoundReader(None, source.run_id, prepared, source.cut_id, analysis=False)
    with open_runtime_engine(settings, "nce-audit-provider-only", purpose="read") as engine:
        reader = ScopedSourceReader(engine, owner)
        ctx = SimpleNamespace(reader=reader, check_active=lambda: None)
        try:
            (unit,) = method.select(None, cfg)
            (result,) = method.run((UnitView(unit, None),), cfg, ctx)
        finally:
            method.close()
    if result.structural_product is None or result.parse_detail is None:
        raise ValueError("pinned provider arm did not return a structural observation")
    retain(output / "product.json", result.structural_product)
    retain(output / "provider.json", result.parse_detail)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--only", nargs="+", choices=(*DEFINITION_ARMS, *CLAUSE_ARMS))
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--provider-only", action="store_true")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, args.output, args.release)
    selected_focuses = json.loads(args.classification.read_bytes())
    selected = args.only or (*DEFINITION_ARMS, *CLAUSE_ARMS)
    summaries = {"definitions": {}, "classification": {}}

    def execute_arm(arm):
        definition = arm in DEFINITION_ARMS
        package = "definitions" if definition else "classification"
        name = ("definition-" if definition else "clause-") + arm
        output = args.output / name
        request = (
            definition_request(settings, arm, output)
            if definition
            else classification_request(selected_focuses, arm)
        )
        run = root = None
        if args.provider_only:
            execute_provider(settings, prepared, output, request)
        else:
            execute(settings, prepared, output, request, name)
            run = json.loads((output / "native/completed.json").read_bytes())
            kind = request[3]
            delivered = cli(
                "structure",
                "list",
                "--run",
                str(run["run_id"]),
                "--cut",
                str(run["cut_id"]),
                "--kind",
                kind,
                "--max-bytes",
                "8000000",
            )
            (read,) = delivered["reports"]
            if read != json.loads((output / "product.json").read_bytes()):
                raise ValueError("installed CLI product differs from the exact Reader")
            anyio.run(compare, kind, json.dumps(delivered).encode())
            root = StructuralExportRequest(run_id=run["run_id"], cut_id=run["cut_id"], kind=kind)
        assessment = (
            evaluate_definition(output)
            if definition
            else evaluate_classification(output, selected_focuses)
        )
        return package, arm, {"run": run, "assessment": assessment}, root

    requests = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for package, arm, summary, root in executor.map(execute_arm, selected):
            summaries[package][arm] = summary
            if root is not None:
                requests.append(root)
    if args.provider_only:
        retain(args.output / "provider-assessment.json", summaries)
        print(json.dumps(summaries))
        return
    selection = ReviewSelection(structural_selections=tuple(requests))
    export = cli("review", "export", "--exact-closure", "-", body=selection.model_dump_json())
    cli("review", "inspect", "--result", export["invocation_id"])
    result = {
        "release_id": args.release,
        **summaries,
        "reader_cli_mcp_equal": True,
        "detached_result_id": export["invocation_id"],
        "detached_selection_digest": export["selection_digest"],
        "outcome": "passed",
    }
    retain(args.output / "result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
