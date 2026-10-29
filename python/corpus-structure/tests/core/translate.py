"""T2 (stored batch -> keyed candidate set) applied mechanically from its declaration, for tests.

S2 owns the real adapter (`validate`); this applies `core/translations.py`'s T2 declaration slot by
slot (each declared image of each source slot, an `outside` item into `references`), so tests can
carry real stored batches into candidate sets and check that the declaration loses nothing.
Loaded by file path (the tests run under `--import-mode=importlib`).
"""

from __future__ import annotations

from typing import Any

from corpus_structure.core import translations as T
from corpus_structure.core.batch import StoredBatch, StoredOutside
from corpus_structure.core.candidates import KeyedCandidateSet


def candidate_set(batch: StoredBatch) -> KeyedCandidateSet:
    maps = {m.source: m for m in T.T2.classes}

    def apply(source: str, item: Any) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for slot, image in maps[source].slots.items():
            if isinstance(image, T.Omitted) or not hasattr(item, slot):
                continue
            out[image if isinstance(image, str) else image[0]] = getattr(item, slot)
        return out

    statements, references = [], []
    for st in batch.statements:
        if isinstance(st, StoredOutside):
            references.append(apply("OutsideItem", st))
        else:
            statements.append(apply("StatementItem", st))
    return KeyedCandidateSet.model_validate({
        "rendition": batch.rendition,
        "entities": [apply("EntityItem", e) for e in batch.entities],
        "statements": statements, "references": references,
        "claims": [apply("ClaimItem", c) for c in batch.claims],
        "alternatives": [apply("AlternativeItem", a) for a in batch.alternatives],
        "unsupported": [apply("UnsupportedItem", u) for u in batch.unsupported],
    })  # fmt: skip
