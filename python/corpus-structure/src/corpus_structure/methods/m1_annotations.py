"""Reusable source-bound linguistic columns under ordinary source-task custody."""

from dataclasses import asdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.method import Reader
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_evidence_layers import (
    SPACY_FAMILIES,
    retained_annotation_products,
)
from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_FAMILY
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourcePin

METHOD = "extract.m1_annotations"
RECIPE = "m1-owned-linguistic-product-1"


class M1AnnotationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recipe: Literal["m1-owned-linguistic-product-1"] = RECIPE
    sentences: SentenceConfig = Field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    max_annotation_chars: int = Field(default=32768, ge=1)
    source_projection_digest: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    characterization_layers: tuple[dict, ...] = ()


class LinguisticAnnotationSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    block_id: str
    profile_digest: str
    dependency_digest: str
    availability: tuple[tuple[str, str], ...]


def consume_annotations(
    reader: Reader, view, profile
) -> tuple[tuple, tuple[str, ...], dict[str, Any]]:
    """Read exact retained primary inputs; missing evidence never runs a language model."""
    from hashlib import sha256

    layers = reader.primary_characterization(
        view.ref.id, families=(*SPACY_FAMILIES, PRIMARY_RULE_FAMILY)
    )
    products = retained_annotation_products(layers, view, profile)
    pins = [pin.values() for pin in layers]
    details = dict(
        recipe=RECIPE,
        source_pin=asdict(NativeSourcePin.from_source(native_source_frame(view, ()))),
        characterization_layers=pins,
        annotation_errors=[],
    )
    result = dict(
        method="retained.primary_characterization",
        input_hash=sha256(canonical_bytes(pins)).hexdigest(),
        configuration_hash=sha256(canonical_bytes(profile.identity())).hexdigest(),
        outcome="produced" if products else "empty",
        parse_detail=details,
        primary_layers=pins,
    )
    return products, (), result
