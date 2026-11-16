"""Shared source selectors, native family declarations and retained column readers."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
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


def source_identity(view: DeclaredNativeFrameSource) -> str:
    return view.source_key


def source_projection(view: DeclaredNativeFrameSource) -> str:
    return view.projection_digest


def source_selector(view: DeclaredNativeFrameSource, start: int, end: int, pointer: str | None = None) -> dict[str, Any]:
    row = dict(projection=source_projection(view), start=start, end=end)
    if pointer is not None:
        row["native_pointer"] = pointer
    return row
