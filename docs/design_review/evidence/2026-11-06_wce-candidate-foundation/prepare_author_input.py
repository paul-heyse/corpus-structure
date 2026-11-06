"""Produce a source-only author view without opportunity proposals or predictions."""

import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent
packet = json.loads((HERE / "raw/source-opportunities-001.json").read_bytes())
source_only = {
    "protocol": "wce-source-author-input-1",
    "scope": packet["scope"],
    "partition": packet["partition"],
    "exposure": packet["exposure"],
    "sources": packet["sources"],
    "passages": packet["passages"],
    "source_groups": packet["source_groups"],
    "questions": packet["questions"],
    "author_instruction": "Independently identify and locate source-supported term/defining/naming cues, content, conditions, symbol declarations and thresholds. Separate location from role/attachment. Preserve recognition limitations and ambiguous or unsupported readings. Do not view other authors, opportunity proposals or producer outputs.",
    "source_freeze_sha256": sha256((HERE / "raw/source-opportunities-001.json").read_bytes()).hexdigest(),
    "producer_outputs_included": False,
    "other_authors_included": False,
}
with (HERE / "raw/source-author-input-001.json").open("xb") as stream:
    stream.write(canonical_bytes(source_only) + b"\n")
print(json.dumps({"outcome": "passed", "passages": len(source_only["passages"])}))
