"""Exercise the pinned resident classifier on the four frozen exact focuses."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from replay_selected import gliner_profile

from corpus_structure.methods.clause_classification import (
    clause_context,
    clause_labels,
    clause_pack,
)
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.semantic.structural_products import (
    ClauseFocusSelection,
    LocatedDefinitionSpan,
    StructuralInput,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    args = parser.parse_args()
    selected = json.loads(args.selection.read_bytes())
    inputs = StructuralInput.model_validate(selected["inputs"])
    passages = {p.passage_id: p for p in inputs.passages}
    requests = []
    for ref, (_, passage_id, (start, end), _) in zip(
        selected["focuses"], selected["judgments"], strict=True
    ):
        passage = passages[passage_id]
        focus = LocatedDefinitionSpan(
            passage_id=passage_id,
            start=start,
            end=end,
            text=passage.text[start - passage.start : end - passage.start],
        )
        requests.append(
            clause_context(ClauseFocusSelection.model_validate(ref), "exact_focus", focus)
        )
    profile, _ = gliner_profile()
    worker = GlinerWorker(profile)
    results = []
    try:
        pack = clause_pack(selected["focuses"][0]["frame"]["release_id"])
        for request in requests:
            (report,) = worker.extract(pack, (request,))
            function, presentation, disposition = clause_labels(report.raw)
            results.append(
                {
                    "report": asdict(report),
                    "disposition": disposition,
                    "function": [label.model_dump(mode="json") for label in function],
                    "presentation": [label.model_dump(mode="json") for label in presentation],
                }
            )
    finally:
        worker.close()
    print(
        json.dumps(
            {"checkpoint": profile.checkpoint, "revision": profile.revision, "rows": results}
        )
    )


if __name__ == "__main__":
    main()
