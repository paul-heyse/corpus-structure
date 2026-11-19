"""Process-local compilation of immutable native schema declarations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from corpus_structure.caches import declare


@dataclass(frozen=True)
class CompiledGlinerPack:
    schema: Any
    retained_bytes: int


@declare("runtime.gliner-pack", "runtime_bytes", weight=lambda value: value.retained_bytes)
def compiled_gliner_pack(pack, runtime_basis: str) -> CompiledGlinerPack:
    schema = pack.compile()
    built = schema.build()
    footprint = len(pack.declaration_json.encode()) + len(json.dumps(built).encode())
    return CompiledGlinerPack(schema, max(1, footprint))
