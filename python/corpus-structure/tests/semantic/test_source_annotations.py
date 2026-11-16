"""Detached-column contracts with controlled Docs; no learned-provider success claim."""

import copy
import json
from pathlib import Path

import pytest
import spacy

from corpus_structure.ingest import annotations
from corpus_structure.ingest.sentences import SentenceConfig, make_doc, prepare_layout
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.canonical_sentences import (
    canonical_packet_values,
    canonical_projection_spec,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.declared_record_sources import (
    DeclaredNativeFrameSource,
    DeclaredRecordSource,
    DeclaredSourcePin,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_products import (
    _blocks,
    _detach_annotation_block,
    sentence_operation_sources,
    sentence_product_inputs,
    source_annotation_packets,
    source_annotation_rows,
    spacy_family_coverage,
    validate_source_annotations,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject


@pytest.fixture(scope="module")
def acquired(tmp_path_factory):
    directory = tmp_path_factory.mktemp("controlled-annotations")
    configuration = SentenceConfig(exclude=("ner",))
    selection = NativeSelection(
        NativeProfile(
            "spacy",
            {"controlled": "runtime"},
            {},
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


def test_one_annotation_population_preserves_existing_payload_and_compact_manifest(
    acquired, detached
):
    prepared, model, configuration, _selection = acquired
    source, value = detached
    product = validate_source_annotations(
        prepared, model, value, source, configuration=configuration
    )
    rows = source_annotation_rows(json.loads(product.content))
    frame = DeclaredNativeFrameSource(source.content.decode(), rows[0]["source"]["content"])
    restored = annotations.restore_annotations(
        rows,
        source=frame,
        profile=annotations.AnnotationProfile(
            configuration, execution_profile=value["execution_profile"]
        ),
        require_complete=False,
    )
    assert len(restored) == 1 and len(restored[0].tokens) == 4
    assert restored[0].block_start == 0 and restored[0].block_end == len(source.value["text"])
    assert product.value.model_dump(mode="json")["outcome"] == "partial"
    kinds = [packet["body"]["record_type"] for packet in value["members"]]
    assert {kind: kinds.count(kind) for kind in set(kinds)} == {
        "native_block": 1,
        "native_token": 4,
        "native_sentence": 1,
        "manifest": 1,
    }
    manifest = next(
        packet for packet in value["members"] if packet["body"]["record_type"] == "manifest"
    )
    assert set(manifest["body"]) == {
        "record_type",
        "source",
        "selectors",
        "coverage",
        "outcome",
        "dependencies",
    }
    assert not any(
        "tokens" in packet["body"] or "blocks" in packet["body"] for packet in value["members"]
    )
    assert "annotation_columns" not in value
    assert "DdoSentenceInventory" not in prepared.index.definitions
    from corpus_structure.semantic.data_operation_output_witnesses import validate_output_witnesses

    pin = value["blocks"][0]["annotation"]["source"]
    selected = {
        "source": [
            {
                "product": pin["source_product"],
                "member": pin.get("source_member"),
                "project_id": pin["project_id"],
                "kind_contract": pin["kind_contract"],
                "subject": pin["subject"],
                "subject_definition": pin["subject_definition"],
                "original_source": pin["original_source"],
                "analyzed_scope": {
                    "source": source.value["source"],
                    "selectors": source.value["selectors"],
                },
                "body": source.value,
            }
        ]
    }
    operation = model.operation("segment.sentences/source-native")
    validate_output_witnesses(operation, {"result": [value]}, selected)
    foreign = copy.deepcopy(value)
    foreign["blocks"][0]["annotation"]["source"]["source_product"] = "foreign-parent"
    with pytest.raises(ValueError, match="complete selected input member"):
        validate_output_witnesses(operation, {"result": [foreign]}, selected)


def test_canonical_projection_uses_annotations_without_native_label_determinants(
    acquired, detached
):
    prepared, model, _configuration, _selection = acquired
    _source, value = detached
    projection = canonical_projection_spec(
        model, prepared.index.definitions["DdoCanonicalSentences"].iri
    )
    canonical = canonical_packet_values(value, projection)
    changed = copy.deepcopy(value)
    changed["blocks"][0]["annotation"]["tokens"][0]["lemma"] = "another-native-label"
    assert canonical_packet_values(changed, projection) == canonical
    assert len(canonical["members"]) == 6
    sentence = next(
        packet["body"]
        for packet in canonical["members"]
        if packet["body"]["record_type"] == "sentence"
    )
    assert sentence["start"] == 0 and sentence["end"] == 14
    assert len(sentence["token_ids"]) == 4
    prepared.validate_json("DdoCanonicalSentences", canonical_bytes(canonical))


def test_empty_annotation_producer_emits_closed_manifest_without_invoking_provider(
    acquired, monkeypatch
):
    from corpus_structure.semantic.sentence_products import prepare_sentence_profile

    prepared, model, configuration, selection = acquired
    monkeypatch.setattr(
        "corpus_structure.semantic.sentence_products.pipeline",
        lambda *_: pytest.fail("empty original loaded a model"),
    )
    source = FrozenNativeSource.from_projection(
        prepared,
        document="document:empty",
        section_pointer="#/body",
        membership="descendants",
        text="",
        pieces=(),
        items=(),
    )
    profile = prepare_sentence_profile(prepared, model, configuration, selection=selection)
    product = profile.run(source)
    value = json.loads(product.content)
    assert value["blocks"] == [] and product.execution_receipts == ()
    assert value["outcome"] == "complete" and len(value["members"]) == 1
    assert all(row["outcome"] == "empty" for row in value["coverage"])


def test_annotation_consumer_refuses_equal_source_body_from_another_selected_carrier(
    acquired, detached
):
    from corpus_structure.semantic.learned_primary import maverick_input
    from corpus_structure.semantic.model_characterization import prepare_model_scope

    prepared, model, configuration, _ = acquired
    source, value = detached
    product = validate_source_annotations(
        prepared, model, value, source, configuration=configuration
    )
    operation = model.operation("segment.sentences/source-native")
    source_role = next(role for role in operation.roles if role.direction == "input")
    assert source_role.support.origins == ("computation",)
    assert source_role.support.provenance == "exact"
    assert source_role.support.identity_requirements == ("episode",)
    original = value["blocks"][0]["annotation"]["source"]
    foreign_member = BoundRoleMember(
        "different-discovery-carrier",
        original["kind_contract"],
        original["subject"],
        original["original_source"],
        canonical_bytes(dict(source=source.value["source"], selectors=source.value["selectors"])),
        b"{}",
        (),
        b"{}",
        member=original["source_member"],
        subject_definition="original-source-view",
        support_references=(),
    )
    foreign = DeclaredNativeFrameSource.acquire(
        prepared, source.value, foreign_member, project=original["project_id"]
    )
    (block,), _ = _blocks(source)
    mapping = prepare_model_scope(
        foreign, (block.start, block.end), (block.start, block.end)
    ).mapping
    with pytest.raises(ValueError, match="different selected source carrier"):
        maverick_input(source, product, foreign, block, mapping)


@pytest.mark.parametrize("detached", [" X  X\né x+y [3]."], indirect=True)
def test_current_native_columns_restore_whole_doc_without_pipeline_and_preserve_whitespace(
    acquired, detached, monkeypatch
):
    from corpus_structure.ingest.annotation_views import annotation_view
    from corpus_structure.semantic.sentence_products import retained_source_annotation_products

    prepared, model, configuration, _selection = acquired
    source, value = detached
    native = validate_source_annotations(
        prepared, model, value, source, configuration=configuration
    )
    monkeypatch.setattr(
        annotations, "pipeline", lambda *_: pytest.fail("retained replay invoked native model")
    )
    (product,) = retained_source_annotation_products(source, native)
    restored = annotation_view(product, source.value["text"], spacy.blank("en").vocab)
    assert restored.doc.text == " X  X\né x+y [3]."
    assert [(t.idx, t.text) for t in restored.doc if t.text == "X"] == [(1, "X"), (4, "X")]
    assert [t.dep_ for t in restored.doc] == ["ROOT", *(["dep"] * (len(restored.doc) - 1))]
    assert [t.head.i for t in restored.doc] == [0] * len(restored.doc)
    assert [t.lemma_ for t in restored.doc] == [f"lemma:{i}" for i in range(len(restored.doc))]
    assert all(t.morph.to_dict() == {"VerbForm": "Fin"} for t in restored.doc)


@pytest.mark.parametrize(
    "mutation,message",
    (
        ("foreign_head", "token coordinates"),
        ("foreign_token_extent", "token coordinates"),
        ("missing_lexeme", "actual token population"),
        ("foreign_sentence", "token/sentence membership"),
        ("changed_source_text", "text differs from its pinned source"),
        ("duplicate_block", "duplicate native blocks"),
    ),
)
def test_current_annotation_validator_refuses_invalid_retained_populations(
    acquired, detached, mutation, message
):
    prepared, model, configuration, _selection = acquired
    source, original = detached
    value = copy.deepcopy(original)
    block = value["blocks"][0]
    annotation = block["annotation"]
    token = annotation["tokens"][0]
    if mutation == "foreign_head":
        token["head"] = len(annotation["tokens"])
    elif mutation == "foreign_token_extent":
        token["end"] = annotation["block_end"] + 1
    elif mutation == "missing_lexeme":
        block["lexemes"].pop()
    elif mutation == "foreign_sentence":
        token["sentence"] = len(annotation["sentences"])
    elif mutation == "changed_source_text":
        annotation["text_digest"] = "0" * 64
    elif mutation == "duplicate_block":
        value["blocks"].append(copy.deepcopy(block))
    with pytest.raises(ValueError, match=message):
        validate_source_annotations(prepared, model, value, source, configuration=configuration)
