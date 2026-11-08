"""Publish and independently verify exact managed whole-book result partitions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from enrich import journey

from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import StructuralExportRequest

CLI = str(Path(sys.executable).with_name("ci"))
SOURCE_METHODS = {"scoped": "structure.scoped_relations", "contextual": "retrieve.contextual"}
STRUCTURAL_KINDS = {"artifact": "artifact_identity", "model": "definition_components"}


def export(run, phase, *, sources):
    if phase in STRUCTURAL_KINDS:
        selection = ReviewSelection(
            structural_selections=(
                StructuralExportRequest(
                    run_id=run["run_id"], cut_id=run["cut_id"], kind=STRUCTURAL_KINDS[phase]
                ),
            ),
            max_bytes=256_000_000,
        )
    else:
        selection = ReviewSelection(
            selections=tuple(
                ContributionRequest(
                    run_id=run["run_id"],
                    cut_id=run["cut_id"],
                    source_view_id=view,
                    method=SOURCE_METHODS[phase],
                    include_details=True,
                    include_relationships=True,
                    include_interpretation=True,
                    max_bytes=32_000_000,
                )
                for view in sources
            ),
            max_bytes=256_000_000,
        )
    managed = subprocess.run(
        [CLI, "review", "export", "-", "--exact-closure", "--json"],
        input=selection.model_dump_json(exclude_none=True),
        text=True,
        capture_output=True,
        check=False,
    )
    if managed.returncode:
        raise ValueError(managed.stdout or managed.stderr[-2500:])
    (identifier,) = re.findall(r"Review ([a-f0-9]{32}) · published", managed.stderr)
    bundle = Path("build/ci") / identifier / "bundle"
    digest = sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    verified = subprocess.run(
        [CLI, "review", "verify", str(bundle), "--manifest-sha256", digest, "--json"],
        text=True,
        capture_output=True,
        check=True,
    )
    if json.loads(verified.stdout)["verification_standing"] != "bound_manifest":
        raise ValueError("detached verification failed to bind the managed digest")
    subprocess.run([CLI, "results", "hold", identifier, "--json"], capture_output=True, check=True)
    return dict(run=run["run_id"], cut=run["cut_id"], result=identifier, manifest_sha256=digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("phase", choices=(*SOURCE_METHODS, *STRUCTURAL_KINDS))
    args = parser.parse_args()
    receipt = json.loads((args.baseline / f"{args.phase}-summary.json").read_bytes())
    records = receipt["results"] if args.phase == "contextual" else receipt
    for run in records:
        target = args.baseline / "delivery" / f"{args.phase}-{run['run_id']}.json"
        if target.exists():
            continue
        sources = run.get("source_views", ())
        if args.phase == "contextual":
            if "source_view_id" not in run:
                raise ValueError("contextual receipt must name its exact source view")
            sources = (run["source_view_id"],)
        result = export(run, args.phase, sources=sources)
        journey.retain(target, result)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
