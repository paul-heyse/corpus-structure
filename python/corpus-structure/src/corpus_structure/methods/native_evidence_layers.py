"""Shared source selectors, native family declarations and retained column readers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from corpus_structure.ingest.annotations import AnnotationProduct
from corpus_structure.semantic.identity import canonical_bytes


SPACY_FAMILIES = (
    "spacy.tokens",
    "spacy.sentences",
    "spacy.lemma",
    "spacy.pos",
    "spacy.tag",
    "spacy.morphology",
    "spacy.dependency",
)
HANLP_FAMILIES = (
    "hanlp.tokens",
    "hanlp.lemma",
    "hanlp.pos",
    "hanlp.dependency",
    "hanlp.constituency",
    "hanlp.srl",
)
SPACY_COLUMNS = dict(
    zip(("SENT_START", "LEMMA", "POS", "TAG", "MORPH", "DEP"), SPACY_FAMILIES[1:], strict=True)
)
HANLP_SCHEMES = {
    "lemma": "hanlp-lemma-native-1",
    "pos": "hanlp-ptb-pos-native-1",
    "dependency": "hanlp-universal-dependencies-1",
    "constituency": "hanlp-ptb-constituency-1",
    "srl": "hanlp-propbank-srl-native-1",
}


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def source_identity(view):
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    return view.source_key if isinstance(view, DeclaredNativeFrameSource) else view.ref.id


def source_projection(view):
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    return (
        view.projection_digest
        if isinstance(view, DeclaredNativeFrameSource)
        else view.ref.projection_digest
    )


def source_selector(view: Any, start: int, end: int, pointer: str | None = None) -> dict[str, Any]:
    row = dict(projection=source_projection(view), start=start, end=end)
    if pointer is not None:
        row["native_pointer"] = pointer
    return row


def has_selected_native_text(view: Any, selectors: Sequence[Mapping[str, Any]]) -> bool:
    """Whether selected projected native characters contain language input.

    Item-only formula recognition has independent eligibility in the formal owner.
    Empty projections and synthetic separators do not become provider requests.
    """
    items = {item["self_ref"]: item for item in getattr(view, "items", ())}
    for piece in view.pieces:
        if piece["kind"] != "native_text":
            continue
        for selector in selectors:
            if selector["projection"] != source_projection(view):
                continue
            pointer = selector.get("native_pointer")
            current, seen = piece.get("item_ref"), set()
            while pointer and current and current != pointer and current not in seen:
                seen.add(current)
                current = (items.get(current, {}).get("parent") or {}).get("$ref")
            if pointer and current != pointer:
                continue
            start = max(piece["start"], selector.get("start", 0))
            end = min(piece["end"], selector.get("end", len(view.text)))
            if start < end and view.text[start:end].strip():
                return True
    return False








