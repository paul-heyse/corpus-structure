"""Collect managed Chandra shadow groups from a frozen source and selection list."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from os import link
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic

from corpus_structure.ingest.pdf_chandra import ChandraRuntime, chandra_parser_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import (
    _CROP_POLICY,
    _RENDER_POLICY,
    MAX_VISUAL_GROUP,
    VisualGroupResult,
    VisualSelection,
    request_visual_group,
)
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings


def _retain(path: Path, content: bytes) -> bytes:
    """Publish the complete immutable file before allowing a second process to read it."""
    if path.exists():
        return path.read_bytes()
    with NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
            handle.flush()
            try:
                link(temporary, path)
            except FileExistsError:
                pass
        finally:
            temporary.unlink()
    return path.read_bytes()


def _custody(body: VisualGroupResult):
    return body.model_dump(mode="json", exclude={"members": {"__all__": {"attempt_receipt"}}})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    artifacts = Path(manifest["artifacts"])
    if "recipe" in manifest and manifest["recipe"] != {
        "execution": "serial_inside_managed_group",
        "runtime": ChandraRuntime(artifacts).identity(),
        "parser": chandra_parser_identity(),
        "render_policy": _RENDER_POLICY,
        "crop_policy": _CROP_POLICY,
    }:
        raise ValueError("installed visual recipe differs from the frozen campaign")
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
    if _retain(bound, manifest_bytes) != manifest_bytes:
        raise ValueError("shadow manifest differs from the retained campaign")
    manifest_digest = sha256(manifest_bytes).hexdigest()

    failed = 0
    settings = Settings()
    # Keep the writer engine so immutable archive decoding is reused across groups.
    # Each call uses the same managed effect as ci source visual-group.
    with open_runtime_engine(settings, "ci-visual-shadow-evidence", purpose="write") as engine:
        for first in range(0, len(selections), MAX_VISUAL_GROUP):
            group = selections[first : first + MAX_VISUAL_GROUP]
            stem = root / f"group-{first // MAX_VISUAL_GROUP + 1:04d}"
            receipt = stem.with_suffix(".result.json")
            key = sha256(
                canonical_bytes({"manifest": manifest_digest, "first_selection": first})
            ).hexdigest()
            run_id = None
            if receipt.exists():
                retained = json.loads(receipt.read_bytes())
                if retained.get("campaign_group") != key:
                    raise ValueError(f"group result belongs to another or a legacy campaign: {receipt}")
                run_id = VisualGroupResult.model_validate(retained).run_id
            elif stem.with_suffix(".pending.json").exists():
                raise ValueError(f"legacy pending group requires managed run recovery: {stem}")
            started = monotonic()
            result = request_visual_group(
                engine,
                selections=group,
                semantic_release=manifest["semantic_release"],
                realization=manifest["realization"],
                receipts=settings.nemotron.receipts,
                artifacts=artifacts,
                nemotron_endpoint=settings.nemotron.endpoint,
                resume_run_id=run_id,
                campaign_group=key,
            )
            body = result.model_dump(mode="json")
            body["campaign_group"] = key
            body["elapsed_seconds"] = round(monotonic() - started, 3)
            retained = json.loads(_retain(receipt, canonical_bytes(body)))
            if retained.get("campaign_group") != key or _custody(
                VisualGroupResult.model_validate(retained)
            ) != _custody(result):
                raise ValueError(f"group result differs from retained managed custody: {receipt}")
            failed += sum(member.status != "source_ready" for member in result.members)
            print(
                f"{first + len(group)}/{len(selections)} managed selections. "
                f"Run {result.run_id}. Failed members: {failed}.",
                flush=True,
            )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
