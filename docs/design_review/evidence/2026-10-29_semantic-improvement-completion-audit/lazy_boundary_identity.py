"""Pure SP-I04 check: do overlapping lazy closures preserve validated model identity?"""

from __future__ import annotations

import importlib.metadata
import json
import sys

from pydantic import ValidationError

from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import _products
from corpus_structure.semantic.types import PreparationProfile, SourceArtifact, SourceBundle

SOURCE = b"""id: https://example.org/lazy
name: lazy
types:
  string: {base: str, uri: xsd:string}
classes:
  C:
    attributes:
      id: {identifier: true}
  B:
    attributes:
      id: {identifier: true}
      c: {range: C, inlined: true, required: true}
  A:
    attributes:
      id: {identifier: true}
      b: {range: B, inlined: true, required: true}
"""


def check() -> dict[str, object]:
    bundle = SourceBundle("lazy", (SourceArtifact("lazy", SOURCE),))
    prepared = prepare_release(bundle)
    opened = reconstruct_release(
        _products(prepared), prepared.manifest, bundle, PreparationProfile(), prepared.artifacts
    )
    value = opened.validate_python("B", {"id": "b", "c": {"id": "c"}})
    previous_b, previous_c = type(value), type(value.c)
    opened.adapter("A")
    adapter = opened.property_adapter("B", "c")
    raw = value.c.model_dump()
    adapter.validate_python(raw, strict=True)
    errors = []
    try:
        adapter.validate_python(value.c, strict=True)
    except ValidationError as error:
        errors = [entry["type"] for entry in error.errors()]
    return {
        "python": sys.version,
        "pydantic": importlib.metadata.version("pydantic"),
        "release_id": prepared.release_id,
        "B_identity_stable": opened._boundary_models["B"] is previous_b,
        "C_identity_stable": opened._boundary_models["C"] is previous_c,
        "same_value_dict_accepted": True,
        "validated_same_release_instance_accepted": not errors,
        "validation_error_types": errors,
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
