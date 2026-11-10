"""Exact retained structural contract delivery for independent authoring preflight."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from .identity import canonical_bytes

DIALECT = "https://json-schema.org/draft/2020-12/schema"


def export_interpretation_contract(prepared, destination: Path) -> dict:
    name = "TerminologyInterpretationV1"
    artifact = next((a for a in prepared.artifacts if a.kind == "json_schema/" + name), None)
    if artifact is None:
        raise ValueError("retained terminology interpretation contract unavailable")
    schema = json.loads(artifact.content)
    if schema.get("$schema", DIALECT) != DIALECT:
        raise ValueError("unsupported retained contract dialect")

    # Current generated contracts own a closed local $defs resource. Do not flatten,
    # regenerate or silently fetch an external document.
    def refs(node):
        if isinstance(node, dict):
            if "$ref" in node and not node["$ref"].startswith("#"):
                raise ValueError("contract resource closure is not local")
            if "$dynamicRef" in node:
                raise ValueError("dynamic references are outside portable profile")
            for value in node.values():
                refs(value)
        elif isinstance(node, list):
            for value in node:
                refs(value)

    refs(schema)
    manifest = dict(
        version=1,
        contract=name,
        mode="validation",
        dialect=DIALECT,
        entry="schema.json",
        schema_digest=artifact.digest,
        release_id=prepared.release_id,
        release_manifest_digest=sha256(prepared.manifest).hexdigest(),
        source_provenance=json.loads(prepared.manifest).get("sources", {}),
        limitations=[
            "structural_preflight_only",
            "source_reference_resolution_unassessed",
            "scientific_support_unassessed",
            "native_admission_unassessed",
        ],
    )
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "schema.json").write_bytes(artifact.content)
    content = canonical_bytes(manifest)
    (destination / "manifest.json").write_bytes(content)
    return dict(
        destination=str(destination), manifest_digest=sha256(content).hexdigest(), **manifest
    )
