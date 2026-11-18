"""Detached-column contracts with controlled Docs; no learned-provider success claim."""

import copy
import json

import pytest
import spacy

from corpus_structure.ingest import annotations
from corpus_structure.semantic.canonical_sentences import (
    canonical_packet_values,
    canonical_projection_spec,
)
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.declared_record_sources import (
    DeclaredNativeFrameSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_products import (
    _blocks,
    source_annotation_rows,
    validate_source_annotations,
)
from corpus_structure.semantic.source_products import FrozenNativeSource
from semantic.source_annotations_test_support import (
    acquired as acquired,
)
from semantic.source_annotations_test_support import (
    detached as detached,
)


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
