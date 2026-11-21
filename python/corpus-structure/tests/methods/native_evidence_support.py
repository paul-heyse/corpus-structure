"""Literal native columns projected into current nominal source and HanLP products."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest
from annotation_support import ControlledPipeline, selected_item

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
from corpus_structure.ingest.sentences import Block
from corpus_structure.semantic.canonical_sentences import (
    CanonicalProduct,
    canonical_partition_values,
    canonical_projection_spec,
)
from corpus_structure.semantic.characterization_manifests import manifest_contract
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import construction_product_inputs
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.formal_products import formal_operation_sources
from corpus_structure.semantic.hanlp_products import (
    canonical_hanlp_rows,
    detach_hanlp_sentence,
    hanlp_product_inputs,
    partition_hanlp_product,
)
from corpus_structure.semantic.learned_primary import learned_primary_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.sentence_partitions import partition_source_annotations
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from methods.navigation_fixture import SourcePrimaryProducts, source_primary_products


@lru_cache(maxsize=1)
def profiles():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = learned_primary_inputs(
        hanlp_product_inputs(
            construction_product_inputs(
                SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
            )
        )
    )
    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(), python_sources=formal_operation_sources()
        ),
        PreparationProfile(version="semantic-2"),
    )
    return prepared, bound_data_operation_model(prepared)


@dataclass(frozen=True)
class NativeCase:
    controlled: ControlledPipeline
    request: AnnotationInput
    primary: SourcePrimaryProducts
    profile: AnnotationProfile

    @property
    def words(self):
        native = self.primary.native
        if native is None:
            raise AssertionError("controlled native fixture requires its supplied annotations")
        return [
            row
            for row in native.inventory("token")
            if self.primary.source.value["text"][row["start"] : row["end"]].strip()
        ]


@pytest.fixture
def native_source(monkeypatch):
    controlled = ControlledPipeline()
    monkeypatch.setattr(annotations, "pipeline", lambda _: controlled)
    text = "X X é x+y [3]."
    request, _source, frame, _context = selected_item(
        controlled,
        text,
        start=0,
        block_id="#/texts/1",
        block=Block(text, ((6, 9),), (), ((10, 13),)),
    )
    profile = AnnotationProfile(execution_profile=controlled.selection().native.fingerprint)
    (product,) = annotate([request], profile)
    primary = source_primary_products(frame, (product,), profile=profile)
    return NativeCase(controlled, request, primary, profile)


def canonical_product(case):
    prepared, model = profiles()
    kind = prepared.index.definitions["DdoCanonicalSentences"].iri
    native = case.primary.native
    assert native is not None
    if native.partitions is None:
        header, packets = partition_source_annotations(json.loads(native.content))
    else:
        header, packets = (
            json.loads(native.content),
            [json.loads(piece) for piece in native.partitions],
        )
    value = canonical_partition_values(
        {"header": header, "partitions": packets}, canonical_projection_spec(model, kind)
    )
    return CanonicalProduct.from_projection(
        value, prepared, model, kind, subject_context=case.primary.context
    )


def retained_hanlp(case, heads, preparation):
    """Run the Native HanLP result detacher against controlled head values."""
    prepared, model = profiles()
    canonical = canonical_product(case)
    rows = canonical_hanlp_rows(case.primary.source, canonical)
    ((sentence, tokens),) = rows
    units, alignment, coverage = detach_hanlp_sentence(
        sentence, tokens, canonical, heads, preparation, "unadmitted:literal-token-vocabulary"
    )
    product = partition_hanlp_product(
        case.primary.source,
        rows,
        units,
        (alignment,),
        coverage,
        kind_contract=manifest_contract(prepared, model, "DdoHanlpManifest"),
    )
    return product, canonical
