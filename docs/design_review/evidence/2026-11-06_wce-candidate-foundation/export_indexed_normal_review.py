"""Export complete normal candidate/source closure with protected-grade pointers."""

import json
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, verify_review_bundle
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
source = json.loads((HERE / "normal-native-references003/result.json").read_bytes())
source_grade = json.loads((HERE / "normal-native-assessment002/result.json").read_bytes())
output_grade = json.loads((HERE / "normal-native-output001/result.json").read_bytes())
selection = ReviewSelection(selections=(ContributionRequest(run_id=113, method="extract.wce_named_candidates", max_bytes=128_000_000, page_bytes=32_000_000),))
index = {
    "source_reference_set_id": source["set_id"], "source_pass_ids": source["pass_ids"],
    "source_evaluation_id": source_grade["source_evaluation_id"],
    "output_reference_set_id": output_grade["set_id"], "output_pass_ids": output_grade["pass_ids"],
    "output_evaluation_id": output_grade["evaluation_id"], "output_population": 23,
    "partition": "feature_fit", "origin_group": "grinstead-snell", "ordinary_reader_private_grades": "excluded",
    "assessment_scope": "native identifiers only; exact independently authored operator artifacts are retained separately alongside the bundle",
    "stronger_claims": "no attachment/applicability/scientific/native-pointer-independent or public-policy activation",
}
destination = HERE / "candidates009/portable-review-indexed"
manifest = export_review_bundle(selection, destination, Settings(), extra_relations={"external_assessment_refs": (index,)})
verification = verify_review_bundle(destination)
with (HERE / "candidates009/portable-review-indexed-receipt.json").open("xb") as stream:
    stream.write(canonical_bytes({"outcome": "passed", "manifest": manifest, "verification": verification,
        "assessment_index": index, "protected_evaluator_capture": False, "labels_copied_to_ordinary_reader": False}) + b"\n")
print(json.dumps({"outcome": "passed", "source_evaluation_id": index["source_evaluation_id"], "output_evaluation_id": index["output_evaluation_id"], "private_grades": "excluded"}))
