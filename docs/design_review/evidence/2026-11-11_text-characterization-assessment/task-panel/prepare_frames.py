"""Version the assessment wire over the already frozen source-only opportunities.

No source selection, prediction read, expected answer or reference-pass translation occurs here.
"""

import json
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import decode_frame
from corpus_structure.semantic.identity import canonical_bytes


ROOT = Path(__file__).resolve().parent


def main():
    sample = json.loads((ROOT.parent / "panel/sample.json").read_bytes())
    for value in sample["frames"].values():
        frame = value["evaluation_frame"]
        frame["guideline_version"] = "characterization-reference-2"
        frame["rubric_version"] = "chapter-facet-task-semantics-1"
        frame["operation_version"] = "text-characterization-panel-2"
        frame["exposure_history"].append("same-frozen-source-opportunities-task-wire-refinement")
        decode_frame(value)
    sample["sampling"]["cohort"] = "tc10-chapter-and-nine-facet-task-panel-2"
    sample["sampling"]["provenance"].update(
        original_source_opportunity_set=40,
        transition="same source/questions; explicit independent semantic-task comparison",
        original_reference_passes="preserved; no automatic answer translation",
    )
    (ROOT / "sample.json").write_bytes(canonical_bytes(sample) + b"\n")
    print(json.dumps({"frames": len(sample["frames"]), "source_opportunity_set": 40}))


if __name__ == "__main__":
    main()
