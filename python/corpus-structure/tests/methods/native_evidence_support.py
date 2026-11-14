"""Controlled inputs and builders shared by the native evidence consumers."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from annotation_support import ControlledPipeline, item

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import annotate
from corpus_structure.ingest.sentences import Block
from corpus_structure.methods import native_evidence as producer
from corpus_structure.methods.native_evidence import native_run
from corpus_structure.methods.native_evidence_layers import (
    HANLP_FAMILIES,
    SPACY_FAMILIES,
    NativeEvidenceBuilder,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs


@pytest.fixture(scope="module")
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


@pytest.fixture
def native_source(monkeypatch):
    controlled = ControlledPipeline()
    monkeypatch.setattr(annotations, "pipeline", lambda _: controlled)
    text = "X X é x+y [3]."
    block = Block(text, ((6, 9),), (), ((10, 13),))
    request = item(controlled, text, start=0, block=block)
    (product,) = annotate([request])
    pin = request.source
    view = SimpleNamespace(
        ref=SimpleNamespace(
            id=pin.source_view_id,
            key=pin.unit_ref,
            native_product=pin.native_product,
            projection_digest=pin.projection_digest,
            recipe_digest=pin.recipe_digest,
            section_pointer=pin.section_pointer,
            membership=pin.membership,
            document_id=17,
        ),
        text=text,
        pieces=[p.to_wire() for p in request.native_pieces],
    )
    base = pin.native_product.values()
    selector = dict(
        projection=pin.projection_digest, native_pointer="#/texts/1", start=0, end=len(text)
    )
    scope = dict(
        source_view_ids=[pin.source_view_id],
        source_views=[
            dict(
                source_view_id=pin.source_view_id,
                key=pin.unit_ref,
                base_document=base,
                section_pointer=pin.section_pointer,
                membership=pin.membership,
                projection_digest=pin.projection_digest,
                recipe_digest=pin.recipe_digest,
            )
        ],
        profile="full_native",
        selectors=[selector],
    )
    operation = dict(
        key="text.native_evidence",
        version="1",
        runtime="runtime:fixture",
        model=producer.MODEL,
        grammar="none",
        configuration="cfg:fixture",
        input="input:fixture",
        context="source-blocks-and-canonical-sentences-1",
    )
    return controlled, request, product, view, base, scope, operation


def builder_for(source, *, full=True):
    _, _, product, view, base, scope, operation = source
    families = SPACY_FAMILIES + HANLP_FAMILIES if full else SPACY_FAMILIES
    builder = NativeEvidenceBuilder(
        base, scope, operation, profile="full_native" if full else "spacy_only", families=families
    )
    _, tokens = builder.spacy(view, product, "spacy")
    return builder, [t for t in tokens if t["text"].strip()]


def metadata(builder):
    for provider in ("spacy", "hanlp"):
        if not any(f.startswith(provider + ".") for f in builder.families):
            continue
        builder.native_runs.append(
            native_run(
                provider,
                builder.profile,
                "fixture" if provider == "spacy" else "{}",
                model="fixture",
                version="1",
                runtime_version="fixture",
                layout=[],
                text=[],
            )
        )
