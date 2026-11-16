"""Select independently available native HanLP heads from the actual provider reply."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _native_heads(document: Mapping[str, Any], index: int, population: int) -> dict[str, Any]:
    heads = {}
    for name, family in (
        ("lem", "lemma"),
        ("pos", "pos"),
        ("dep", "dependency"),
        ("con", "constituency"),
        ("srl", "srl"),
    ):
        columns = [v for k, v in document.items() if k.split("/")[0] == name]
        if len(columns) == 1 and isinstance(columns[0], list) and len(columns[0]) == population:
            heads[family] = columns[0][index]
    return heads
