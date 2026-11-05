"""Actual ordinary capture; consumes retained data without a model operation."""

import json
from pathlib import Path

from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parent
selection = ReviewSelection(selections=(ContributionRequest(
    run_id=45, include_interpretation=True, include_assessment=True,
    include_publication=True, include_support=True,
),))
(ROOT / "selection_001.json").write_text(selection.model_dump_json(indent=2) + "\n")
manifest = export_review_bundle(selection, ROOT / "raw" / "ordinary_run45_001", Settings())
print(json.dumps({"outcome": "passed", "format": manifest["format"],
                  "selection_digest": manifest["selection_digest"],
                  "relations": {name: spec["rows"] for name, spec in manifest["relations"].items()}},
                 sort_keys=True))
