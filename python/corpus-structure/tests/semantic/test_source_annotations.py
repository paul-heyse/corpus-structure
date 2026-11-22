"""Detached-column contracts with controlled Docs; no learned-provider success claim."""

import copy
import json

import pytest
import spacy

from corpus_structure.ingest import annotations
from corpus_structure.semantic.canonical_sentences import (
    canonical_partition_values,
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
from semantic.source_annotations_test_support import partition_controlled_annotations


def test_annotation_payload_is_immutable_and_context_changes_retain_decoded_custody(
    acquired, detached, monkeypatch
):
    from dataclasses import replace
    from typing import Any, cast

    from corpus_structure.semantic import sentence_partitions
    from corpus_structure.semantic.sentence_products import source_annotation_blocks

    prepared, model, configuration, _ = acquired
    source, value = detached
    product = partition_controlled_annotations(
        prepared, model, value, source, configuration=configuration
    )
    with pytest.raises(TypeError, match="immutable receipt bytes"):
        replace(product, execution_receipts=cast(Any, [b"unadmitted"]))
    blocks = source_annotation_blocks(product)
    configured = product.configuration

    def repeated(*_args, **_kwargs):
        pytest.fail("retained annotation data was decoded or validated again")

    monkeypatch.setattr(sentence_partitions, "sentence_product_payload", repeated)
    carried = product.with_context(None)
    assert carried.value is product.value
    assert source_annotation_blocks(carried) is blocks
    assert carried.configuration is configured
    with pytest.raises(TypeError):
        carried.value["configuration"]["batch_size"] = 99


def test_one_annotation_population_preserves_existing_payload_and_compact_manifest(
    acquired, detached
):
    prepared, model, configuration, _selection = acquired
    source, value = detached
    product = partition_controlled_annotations(
        prepared, model, value, source, configuration=configuration
    )
    rows = source_annotation_rows(product)
    frame = DeclaredNativeFrameSource.from_source(source, rows[0]["source"]["content"])
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
    assert product.value["outcome"] == "partial"
    header = json.loads(product.content)
    assert len(product.inventory("sentence")) == 1
    assert len(product.inventory("token")) == 4
    assert [packet["body"]["record_type"] for packet in header["members"]] == ["manifest"]
    manifest = next(
        packet for packet in value["members"] if packet["body"]["record_type"] == "manifest"
    )
    assert set(manifest["body"]) == {
        "record_type",
        "source",
        "selectors",
        "coverage",
        "outcome",
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
    validate_output_witnesses(operation, {"result": [header]}, selected)
    foreign = copy.deepcopy(header)
    foreign["block_layouts"][0]["annotation"]["source"]["source_product"] = "foreign-parent"
    with pytest.raises(ValueError, match="complete selected input member"):
        validate_output_witnesses(operation, {"result": [foreign]}, selected)


def test_annotation_payload_shares_rows_across_distinct_placements(acquired, detached):
    from corpus_structure.semantic.data_operation_partitions import partition_header
    from corpus_structure.semantic.sentence_partitions import (
        _sentence_partition_body,
        sentence_product_payload,
    )

    prepared, model, configuration, _ = acquired
    source, value = detached
    product = partition_controlled_annotations(
        prepared, model, value, source, configuration=configuration
    )
    nominal = "DdoSourceAnnotations"
    first = sentence_product_payload(product.content, product.partitions, prepared, nominal)
    packet = json.loads(product.partitions[0])
    packet["placement"] = {key: offset + 17 for key, offset in packet["placement"].items()}
    header = json.loads(product.content)
    header["rows"] = partition_header((packet,))
    moved = canonical_bytes(header)
    relocated = sentence_product_payload(moved, (canonical_bytes(packet),), prepared, nominal)
    assert first.blocks[0].rows is relocated.blocks[0].rows
    assert first.packets[0]["body"] is relocated.packets[0]["body"]
    assert relocated.blocks[0].start == first.blocks[0].start + 17
    assert first.partitions != relocated.partitions

    # A populated cache cannot legitimize unrelated tagged rows under a valid commitment.
    packet["body"][1].reverse()
    with pytest.raises(ValueError, match="digest differs from its actual rows"):
        sentence_product_payload(moved, (canonical_bytes(packet),), prepared, nominal)

    _sentence_partition_body.cache_clear()
    reacquired = sentence_product_payload(product.content, product.partitions, prepared, nominal)
    assert reacquired.blocks[0].rows == first.blocks[0].rows
    assert reacquired.blocks[0].rows is not first.blocks[0].rows


def test_annotation_producer_refuses_missing_family_even_with_matching_manifest(acquired, detached):
    prepared, model, configuration, _ = acquired
    source, value = detached
    value["coverage"].pop()
    with pytest.raises(ValueError, match="coverage omits or repeats a declared spaCy family"):
        partition_controlled_annotations(
            prepared, model, value, source, configuration=configuration
        )


def test_canonical_projection_uses_annotations_without_native_label_determinants(
    acquired, detached
):
    prepared, model, _configuration, _selection = acquired
    _source, value = detached
    projection = canonical_projection_spec(
        model, prepared.index.definitions["DdoCanonicalSentences"].iri
    )
    from corpus_structure.semantic.data_operation_projection_values import (
        materialize_whole_input_projection,
    )
    from corpus_structure.semantic.data_product_reference import read_semantic_reference
    from corpus_structure.semantic.sentence_partitions import (
        blocks_from_packets,
        partition_source_annotations,
    )

    header, packets = partition_source_annotations(value)
    operation = model.operation("segment.sentences/canonical-projection")
    input_role = next(role for role in operation.roles if role.direction == "input")
    layout = json.loads(
        next(kind.facts for kind in model.kinds if kind.semantic_id == input_role.kind)
    )["collections"]

    def project(header, packets):
        return materialize_whole_input_projection(
            input_role.read_projection, layout, header, packets
        )

    canonical = canonical_partition_values(project(header, packets), projection)
    changed = copy.deepcopy(value)
    changed["blocks"][0]["lexemes"][0]["lemma"] = "another-native-label"
    relabeled, labeled_packets = partition_source_annotations(changed)
    assert labeled_packets[0]["partition_digest"] != packets[0]["partition_digest"]
    assert canonical_partition_values(project(relabeled, labeled_packets), projection) == canonical
    (block,) = blocks_from_packets(canonical["partitions"])
    assert [
        (row["record_type"], row["ordinal"], row["start"], row["end"]) for row in block.rows
    ] == [
        ("sentence", 0, 0, 14),
        ("token", 0, 0, 1),
        ("token", 1, 2, 7),
        ("token", 2, 8, 13),
        ("token", 3, 13, 14),
    ]
    assert all(
        read_semantic_reference(row["annotation"]).item_key == (row["record_type"], row["ordinal"])
        for row in block.rows
    )
    assert [member["body"]["record_type"] for member in canonical["header"]["members"]] == [
        "manifest"
    ]


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
    assert value["block_layouts"] == [] and product.execution_receipts == ()
    assert value["rows"]["item_count"] == 0 and product.partitions == ()
    assert value["outcome"] == "complete" and len(value["members"]) == 1
    assert all(row["outcome"] == "empty" for row in value["coverage"])


def test_annotation_consumer_refuses_equal_source_body_from_another_selected_carrier(
    acquired, detached
):
    from corpus_structure.semantic.learned_primary import maverick_input
    from corpus_structure.semantic.model_characterization import prepare_model_scope
    from corpus_structure.semantic.sentence_products import source_annotation_blocks

    prepared, model, configuration, _ = acquired
    source, value = detached
    product = partition_controlled_annotations(
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
    (annotation_block,) = source_annotation_blocks(product)
    with pytest.raises(ValueError, match="different selected source carrier"):
        maverick_input(annotation_block["annotation"], foreign, block, mapping)


@pytest.mark.parametrize("detached", [" X  X\né x+y [3]."], indirect=True)
def test_current_native_columns_restore_whole_doc_without_pipeline_and_preserve_whitespace(
    acquired, detached, monkeypatch
):
    from corpus_structure.ingest.annotation_views import annotation_view
    from corpus_structure.semantic.data_operation_partitions import partition_header
    from corpus_structure.semantic.sentence_partitions import partition_source_annotations
    from corpus_structure.semantic.sentence_products import retained_source_annotation_products

    prepared, model, configuration, _selection = acquired
    source, value = detached
    header, packets = partition_source_annotations(value)
    assert [member["body"]["record_type"] for member in header["members"]] == ["manifest"]
    header["rows"] = partition_header(packets)
    native = validate_source_annotations(
        prepared,
        model,
        header,
        source,
        configuration=configuration,
        partitions=tuple(canonical_bytes(packet) for packet in packets),
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
        ("duplicate_block", "duplicate partition key"),
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
        partition_controlled_annotations(
            prepared, model, value, source, configuration=configuration
        )
