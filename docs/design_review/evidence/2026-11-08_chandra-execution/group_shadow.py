"""Collect managed Chandra shadow groups from a frozen source and selection list."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import monotonic

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import (
    MAX_VISUAL_GROUP,
    VisualSelection,
    request_visual_group,
)
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    source = VisualEvidencePin.model_validate(manifest["source"])
    selections = tuple(
        VisualSelection.model_validate(dict(row, source=source))
        for row in manifest["selections"]
    )
    if not selections or len({canonical_bytes(row.scope()) for row in selections}) != len(selections):
        raise ValueError("shadow selections must be finite, nonempty and unique")
    root = args.output
    root.mkdir(parents=True, exist_ok=True)
    bound = root / "manifest.json"
    if bound.exists():
        if bound.read_bytes() != manifest_bytes:
            raise ValueError("shadow manifest differs from the retained campaign")
    else:
        bound.write_bytes(manifest_bytes)

    failed = 0
    settings = Settings()
    # Keep the writer engine so immutable archive decoding is reused across groups.
    # Each call uses the same managed effect as ci source visual-group.
    with open_runtime_engine(settings, "ci-visual-shadow-evidence", purpose="write") as engine:
        for first in range(0, len(selections), MAX_VISUAL_GROUP):
            group = selections[first : first + MAX_VISUAL_GROUP]
            stem = root / f"group-{first // MAX_VISUAL_GROUP + 1:04d}"
            receipt = stem.with_suffix(".result.json")
            pending = stem.with_suffix(".pending.json")
            if not receipt.exists():
                with pending.open("xb") as output:
                    started = monotonic()
                    result = request_visual_group(
                        engine,
                        selections=group,
                        semantic_release=manifest["semantic_release"],
                        realization=manifest["realization"],
                        receipts=settings.nemotron.receipts,
                        artifacts=Path(manifest["artifacts"]),
                        nemotron_endpoint=settings.nemotron.endpoint,
                    )
                    body = result.model_dump(mode="json")
                    body["elapsed_seconds"] = round(monotonic() - started, 3)
                    output.write(canonical_bytes(body))
                pending.replace(receipt)
            result_body = json.loads(receipt.read_bytes())
            if result_body["source"] != source.model_dump(mode="json") or [
                VisualSelection.model_validate(member["selection"]).scope()
                for member in result_body["members"]
            ] != [selection.scope() for selection in group]:
                raise ValueError(f"group result does not match the frozen selection: {receipt}")
            failed += sum(member["status"] != "source_ready" for member in result_body["members"])
            print(
                f"{first + len(group)}/{len(selections)} managed selections. "
                f"Run {result_body['run_id']}. Unsettled or failed members: {failed}.",
                flush=True,
            )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
