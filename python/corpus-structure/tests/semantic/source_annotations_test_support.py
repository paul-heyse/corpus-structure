"""Shared authored scenarios and fixtures for source annotations test support."""

from pathlib import Path

import pytest
import spacy

from corpus_structure.ingest import annotations
from corpus_structure.ingest.sentences import SentenceConfig, make_doc, prepare_layout
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.declared_record_sources import (
    DeclaredRecordSource,
    DeclaredSourcePin,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.sentence_products import (
    _blocks,
    _detach_annotation_block,
    sentence_operation_sources,
    sentence_product_inputs,
    source_annotation_packets,
    spacy_family_coverage,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def partition_controlled_annotations(
    prepared, model, value, source, *, configuration=None, subject_context=None
):
    from corpus_structure.semantic.characterization_manifests import manifest_contract
    from corpus_structure.semantic.data_operation_partitions import partition_header
    from corpus_structure.semantic.sentence_partitions import partition_source_annotations
    from corpus_structure.semantic.sentence_products import (
        annotation_manifest,
        validate_source_annotations,
    )

    manifest = annotation_manifest(
        value, kind_contract=manifest_contract(prepared, model, "DdoSourceAnnotationManifest")
    )
    header, rows = partition_source_annotations({**value, "members": [manifest]})
    return validate_source_annotations(
        prepared,
        model,
        {**header, "rows": partition_header(rows)},
        source,
        configuration=configuration,
        subject_context=subject_context,
        partitions=tuple(canonical_bytes(row) for row in rows),
    )


@pytest.fixture(scope="module")
def acquired(tmp_path_factory):
    directory = tmp_path_factory.mktemp("controlled-annotations")
    configuration = SentenceConfig(exclude=("ner",))
    selection = NativeSelection(
        NativeProfile(
            "spacy",
            {"controlled": "runtime"},
            {"files": {}},
            configuration.model_dump(mode="json"),
            "float32",
            "cupy",
            4,
            1,
        ),
        directory,
    )
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = sentence_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(bundle)
    model = compile_data_operations(
        schema=bundle,
        python_sources=sentence_operation_sources(configuration, selection=selection),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return prepared, model, configuration, selection


@pytest.fixture
def detached(acquired, monkeypatch, request):
    prepared, model, configuration, selection = acquired
    nlp = spacy.blank("en")
    monkeypatch.setattr(annotations, "pipeline", lambda _configuration: nlp)
    parameter = getattr(request, "param", "A valve opens.")
    text = parameter["text"] if isinstance(parameter, dict) else parameter
    source = FrozenNativeSource.from_projection(
        prepared,
        document="document:one",
        section_pointer="#/body",
        membership="descendants",
        text=text,
        pieces=[
            dict(
                kind="native_text",
                start=0,
                end=len(text),
                item_ref="#/texts/0",
                source_field="text",
            )
        ],
        items=[dict(self_ref="#/texts/0", label="text", text=text, orig=text)],
    )
    scope = canonical_bytes(
        dict(source=source.value["source"], selectors=source.value["selectors"])
    )
    member = BoundRoleMember(
        "controlled-original-product",
        "controlled-source-kind",
        source_subject(source.value["source"]),
        "document:one",
        scope,
        b"{}",
        (),
        b"{}",
        member="controlled-original-member",
        subject_definition="original-source-view",
        support_references=(),
    )
    address = DeclaredRecordSource.from_bound(source, member, project="controlled-project")
    pin = DeclaredSourcePin(canonical_bytes(address.pin()).decode())
    (block,), coverage = _blocks(source)
    layout = prepare_layout(nlp, block.block, start=block.start)
    doc = make_doc(nlp, block.block, layout, start=block.start)
    for index, token in enumerate(doc):
        token.is_sent_start = index == 0
    if hasattr(request, "param"):
        # Controlled native columns, with no model or linguistic accuracy claim.
        from spacy.tokens import MorphAnalysis

        for token in doc:
            token.lemma_ = f"lemma:{token.i}"
            token.pos_ = "VERB"
            token.tag_ = "VB"
            token.morph = MorphAnalysis(doc.vocab, "VerbForm=Fin")
            token.dep_ = "ROOT" if token.i == 0 else "dep"
            token.head = doc[0]
        if isinstance(parameter, dict):
            for token, columns in zip(doc, parameter["columns"], strict=True):
                token.lemma_, token.pos_, token.tag_, token.dep_, head = columns
                token.head = doc[head]
    detached = _detach_annotation_block(
        source.value, block, layout, doc, pin, configuration, selection.native.fingerprint
    )
    availability = dict(
        block_id=block.block_id,
        start=block.start,
        end=block.end,
        attributes={
            row["attribute"]: row["status"] for row in detached["annotation"]["availability"]
        },
    )
    value = dict(
        source=source.value["source"],
        selectors=source.value["selectors"],
        configuration=configuration.model_dump(mode="json"),
        execution_profile=selection.native.fingerprint,
        block_coverage=coverage,
        coverage=spacy_family_coverage(source.value, coverage, [availability]),
        blocks=[detached],
    )
    value["outcome"] = (
        "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in value["coverage"])
        else "partial"
    )
    value["members"] = source_annotation_packets(prepared, model, value)
    return source, value
