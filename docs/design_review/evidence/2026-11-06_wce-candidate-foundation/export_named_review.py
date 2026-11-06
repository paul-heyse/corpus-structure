"""Export/verify actual named candidates with complete selected source closure."""

import argparse
import json
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, verify_review_bundle
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("candidate_directory")
parser.add_argument("--additional-dir", action="append", default=[])
args = parser.parse_args()
root = HERE / args.candidate_directory
roots = [root, *(HERE / name for name in args.additional_dir)]
results = [json.loads((directory / "result.json").read_bytes()) for directory in roots]
if any(result["outcome"] != "passed" for result in results):
    raise ValueError("review export requires completed actual candidate execution")
all_runs = [run for result in results for run in result["runs"]]
selection = ReviewSelection(selections=tuple(ContributionRequest(run_id=r["run_id"], method="extract.wce_named_candidates", max_bytes=128_000_000, page_bytes=32_000_000) for r in all_runs))
manifest = export_review_bundle(selection, root / "portable-review", Settings())
verification = verify_review_bundle(root / "portable-review")
with (root / "portable-review-receipt.json").open("xb") as stream:
    stream.write(canonical_bytes({"outcome": "passed", "manifest": manifest, "verification": verification,
        "protected_evaluator_capture": False, "scope": "actual named-candidate/read/export/source reconstruction; no independent semantic promotion"}) + b"\n")
print(json.dumps({"outcome": "passed", "runs": len(all_runs)}))
