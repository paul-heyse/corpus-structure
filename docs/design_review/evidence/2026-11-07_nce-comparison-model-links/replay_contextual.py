"""Repeat the original affine X and unrelated red-ball contextual control."""

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from replay_selected import prepared_release, retain

from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import StructuralExportRequest
from corpus_structure.settings import Settings

COMPOSITION = (
    Path(__file__).resolve().parent.parent / "2026-11-06_wce-completion-repair/composition"
)
sys.path.insert(0, str(COMPOSITION))
from run_nonself import (  # noqa: E402
    M1_ORIGINAL_TASK,
    NAMED_PRODUCT,
    OLD_RELEASE,
    SOURCE_VIEW,
    capture_named,
    execute,
    prepare_inventory,
    read_pages,
    summarize_raw,
)


def assess(bundle):
    expected = json.loads(
        (COMPOSITION / "native-retained004/false-bridge-control.json").read_bytes()
    )
    wrong = expected["removed_false_selection"]
    anchors = [origin["anchors"] for origin in wrong["origins"]]
    reports = (
        json.loads(json.loads(line)["payload_json"])
        for line in (bundle / "reports.jsonl").read_text().splitlines()
    )
    (report,) = [
        row
        for row in reports
        if row.get("method") == "retrieve.contextual" and row.get("origin_unit_id") == SOURCE_VIEW
    ]
    ids = {
        row["occurrence_id"]
        for row in report["body"]["contributions"]
        if row["semantic_type"] == "contextual.located_mention" and row.get("anchors") in anchors
    }
    (occurrence,) = ids
    summary = summarize_raw(bundle, SOURCE_VIEW)
    (candidate,) = [r for r in summary["candidate_lists"] if r["occurrence_id"] == occurrence]
    (decision,) = [r for r in summary["relationship_decisions"] if r["occurrence_id"] == occurrence]
    if not any(r["target_id"] == wrong["target_id"] for r in candidate["candidates"]):
        raise ValueError("matched control lost the independently judged unrelated candidate")
    if decision["outcome"] != "insufficient_evidence" or decision["selected_edges"]:
        raise ValueError("the affine X occurrence has an unsupported selected edge")
    print(
        json.dumps(
            {
                "outcome": "passed",
                "occurrence": occurrence,
                "target": wrong["target_id"],
                "decision": decision["outcome"],
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release")
    parser.add_argument("--assess", action="store_true")
    args = parser.parse_args()
    output = args.destination
    if args.assess:
        assess(output)
        return
    if not args.release:
        parser.error("native execution needs an explicitly admitted release")
    output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, output, args.release)
    named, report, references = capture_named(
        settings,
        SimpleNamespace(named_run=160, named_product=NAMED_PRODUCT, release_id=OLD_RELEASE),
        output,
    )
    inventory = prepare_inventory(report, references, output)
    source = next(ref for ref in report.inputs.sources if ref.source_view_id == SOURCE_VIEW)
    run, producer, linker = execute(
        settings,
        prepared,
        report,
        source,
        inventory["target_components"],
        SimpleNamespace(upstream="retained-m1", attempt=output.name),
        output,
    )
    selections = read_pages(settings, run, (producer, linker), output)
    # The original producer and definition products are distinct predecessors of the result.
    selections.append(
        ContributionRequest(
            run_id=161,
            source_view_id=SOURCE_VIEW,
            method="extract.m1_candidates",
            max_bytes=128_000_000,
        )
    )
    retain(
        output / "selection.json",
        ReviewSelection(
            selections=tuple(selections),
            structural_selections=(
                StructuralExportRequest(
                    run_id=named["run_id"],
                    cut_id=named["cut_id"],
                    kind="definition_components",
                ),
            ),
            max_bytes=256_000_000,
        ).model_dump(mode="json", exclude_none=True),
    )
    retain(output / "scope.json", {"run": run, "method": linker, "origin_task": M1_ORIGINAL_TASK})
    print(json.dumps(run))


if __name__ == "__main__":
    main()
