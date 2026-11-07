"""Run current scoped nominations and the artifact pilot through native custody."""

import argparse
import json
import sys
from pathlib import Path

from corpus_structure.methods.artifact_identity import ArtifactIdentityMethod
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import StructuralExportRequest
from corpus_structure.settings import Settings

from run_pilot import artifact_nomination_refs, evaluate

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parents[1] / "2026-11-06_wce-gs120"
sys.path.insert(0, str(PREVIOUS / "current-structural-journey"))
from journey_support import PARENT, admit_current, inspect_scoped, retain, run_method  # noqa: E402
from run_journey import inspect_artifact, portable, prepared_release, source_inputs  # noqa: E402


def run(output, release):
    settings = Settings()
    inputs, coverage = source_inputs(
        PREVIOUS / "source-recovery/attempt001/source-packets/source-packet.json"
    )
    prepared = (
        prepared_release(settings, output, release) if release else admit_current(settings, output)
    )
    retain(output / "source-coverage.json", coverage)
    work = [
        dict(
            native_content_digest=digest,
            source_work=PARENT,
            provenance="Retained native-parent map and authenticated GS120 parent",
        )
        for digest in sorted({source.native_content_digest for source in inputs.sources})
    ]
    scoped_root = output / "scoped"
    scoped = run_method(
        settings,
        prepared,
        ScopedRelationsMethod(),
        dict(
            inputs=inputs.model_dump(mode="json"),
            structural_input_digest=inputs.identity,
            work_bindings=work,
            interpretation_mode="independent",
        ),
        inputs,
        scoped_root,
        "repair-scoped",
        output.name,
    )
    _, requests = inspect_scoped(settings, scoped, inputs, scoped_root)
    scoped_bundle = output / "review-scoped"
    portable(ReviewSelection(selections=tuple(requests), max_bytes=512_000_000), scoped_bundle, settings)
    refs = artifact_nomination_refs(scoped_root, scoped_bundle)
    bound = inputs.model_copy(
        update={"dependencies": (*inputs.dependencies, *(ref.contribution_id for ref in refs))}
    )
    artifact_root = output / "artifact"
    policy = json.loads((PREVIOUS / "current-structural-journey/artifact-policy.json").read_bytes())
    artifact = run_method(
        settings,
        prepared,
        ArtifactIdentityMethod(),
        dict(
            inputs=bound.model_dump(mode="json"),
            structural_input_digest=bound.identity,
            work_bindings=work,
            policy=policy,
            external_nomination_refs=[ref.model_dump(mode="json") for ref in refs],
        ),
        bound,
        artifact_root,
        "repair-artifact",
        output.name,
    )
    request, summary = inspect_artifact(settings, artifact, artifact_root)
    portable(
        ReviewSelection(
            selections=tuple(requests), structural_selections=(request,), max_bytes=512_000_000
        ),
        output / "review-artifact",
        settings,
    )
    result = evaluate(
        HERE.parent / "source-references/source-reference.json",
        artifact_root / "file-page.json",
        artifact_root / "configuration.json",
    )
    retain(output / "pilot-result.json", result)
    summary = {
        **summary,
        "scoped": scoped,
        "artifact": artifact,
        "external_nominations": len(refs),
        "independent_judgments": result["independent_judgments"],
        "captured_judgments": result["captured_judgments"],
    }
    retain(output / "result.json", summary)
    return summary


def verify_retained(output, retained):
    scoped_selection = ReviewSelection.model_validate(
        json.loads((retained / "review-scoped/manifest.json").read_bytes())["selection"]
    )
    artifact = json.loads((retained / "artifact/completed.json").read_bytes())
    request = StructuralExportRequest(
        run_id=artifact["run_id"], cut_id=artifact["cut_id"], kind="artifact_identity",
        max_bytes=128_000_000,
    )
    portable(
        ReviewSelection(
            selections=scoped_selection.selections,
            structural_selections=(request,),
            max_bytes=512_000_000,
        ),
        output / "review-artifact",
        Settings(),
    )
    result = evaluate(
        HERE.parent / "source-references/source-reference.json",
        retained / "artifact/file-page.json",
        retained / "artifact/configuration.json",
    )
    retain(output / "pilot-result.json", result)
    retain(output / "result.json", {
        "outcome": "passed", "artifact": artifact, "retained_attempt": retained.name,
        "independent_judgments": result["independent_judgments"],
        "captured_judgments": result["captured_judgments"],
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release")
    parser.add_argument("--retained-attempt", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.destination.mkdir(exist_ok=args.resume)
    try:
        result = (
            verify_retained(args.destination, args.retained_attempt)
            if args.retained_attempt
            else run(args.destination, args.release)
        )
        print(json.dumps(result))
    except BaseException as exc:
        number = len(list(args.destination.glob("failure-*.json"))) + 1
        retain(args.destination / f"failure-{number:03}.json", {
            "type": type(exc).__name__, "message": str(exc),
        })
        raise


if __name__ == "__main__":
    main()
