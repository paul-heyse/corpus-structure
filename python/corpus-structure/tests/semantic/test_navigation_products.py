"""Independent original-coordinate navigation expectations for declared products."""

import pytest

from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.constructions.layers import ConstructionLayer, ConstructionSource
from corpus_structure.semantic.constructions.navigation import (
    FAMILY,
    NativeNavigationIndex,
    populate_navigation_products,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import original_document_subject
from corpus_structure.semantic.source_products import FrozenNativeSource, native_projection_identity


def source(text="Table 2.1 (aliases: none).", label="caption"):
    coordinate = {
        "document": "book",
        "document_subject": original_document_subject("book"),
        "section_pointer": "#/groups/0",
        "membership": "direct",
    }
    value = {
        "source": coordinate,
        "text": text,
        "pieces": [
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 0,
                "end": len(text),
            }
        ],
        "items": [{"self_ref": "#/texts/0", "label": label, "text": text, "content_layer": "body"}],
        "ancestors": [],
    }
    projection = native_projection_identity(text, value["pieces"], value["items"])
    coordinate["projection"] = projection
    value["selectors"] = [{"projection": projection}]
    return FrozenNativeSource._accept_retained_projection(canonical_bytes(value))


def product(selected):
    layer = ConstructionLayer(
        selected.value["source"],
        {"selectors": selected.value["selectors"]},
        {"key": "text.constructions/source-native"},
        families=(FAMILY,),
    )
    populate_navigation_products(layer, ConstructionSource.from_native(selected), selected, None)
    facts = layer.facts()
    return CharacterizationSnapshot(
        "product:navigation",
        canonical_bytes(
            {
                "source": selected.value["source"],
                "selectors": selected.value["selectors"],
                "coverage": facts["coverage"],
                "members": [
                    {"body": {"record_type": tag, **row}}
                    for name, tag in (("annotations", "annotation"), ("occurrences", "occurrence"))
                    for row in facts[name]
                ],
            }
        ),
    )


def test_literal_navigation_keeps_known_empty_aliases_and_original_semantic_addresses():
    selected = source()
    retained = product(selected)
    index = NativeNavigationIndex((retained,), selected).require()
    (mention,) = index.select("artifact_mention", "#/texts/0")
    assert mention.text("subject") == "Table 2.1"
    assert mention.text("designator") == "2.1"
    assert mention.payload["alias_state"] == "known_empty"
    assert mention.text("alias_absence") == "aliases: none"
    assert mention.reference.values()["product_id"] == "product:navigation"
    assert "task_id" not in mention.reference.values()
    assert all("source_view_id" not in extent for extent in mention.fragments("subject"))


def test_unobserved_aliases_stay_unknown_and_missing_native_language_coverage_is_not_empty():
    selected = source("Table 2.1.")
    (mention,) = (
        NativeNavigationIndex((product(selected),), selected).require().select("artifact_mention")
    )
    assert mention.payload["alias_state"] == "unknown"
    language = source("A random variable has an expected value.", label="text")
    index = NativeNavigationIndex((product(language),), language)
    assert not index.complete
    with pytest.raises(ValueError, match="missing or incomplete"):
        index.require()
    with pytest.raises(ValueError, match="missing or incomplete"):
        NativeNavigationIndex((), selected).require()


def test_navigation_refuses_changed_source_scope_and_literal_evidence():
    import json

    selected = source()
    retained = product(selected)
    body = json.loads(retained.content)
    body["selectors"] = [
        {"projection": selected.value["source"]["projection"], "start": 0, "end": 3}
    ]
    with pytest.raises(ValueError, match="analyzed scope"):
        NativeNavigationIndex(
            (CharacterizationSnapshot(retained.product_id, canonical_bytes(body)),), selected
        )
    body = json.loads(retained.content)
    occurrence = next(
        packet["body"]
        for packet in body["members"]
        if packet["body"]["record_type"] == "occurrence"
    )
    occurrence["extents"][0]["text"] = "forged spelling"
    with pytest.raises(ValueError, match="literal original"):
        NativeNavigationIndex(
            (CharacterizationSnapshot(retained.product_id, canonical_bytes(body)),), selected
        )


def artifact_case(text="Table 2.1 (aliases: none)."):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredNativeFrameSource,
        DeclaredRecordSource,
    )
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.source_products import source_subject
    from corpus_structure.semantic.structural_products import (
        DeclaredStructuralInput,
        StructuralPassage,
    )

    selected = source(text)
    context = SubjectContext(
        "p",
        source_subject(selected.value["source"]),
        "book",
        canonical_bytes(
            {"source": selected.value["source"], "selectors": selected.value["selectors"]}
        ),
        subject_definition="original-source-view",
    )
    pin = DeclaredRecordSource(
        "book",
        selected.value["source"]["projection"],
        "#/groups/0",
        "direct",
        context,
        "product:source",
        None,
        "kind:source",
    ).pin()
    frame = DeclaredNativeFrameSource.from_source(selected, canonical_bytes(pin).decode())
    original = DeclaredStructuralSource.model_validate(pin)
    passage = StructuralPassage(
        passage_id="caption",
        source_ref=original.identity,
        start=0,
        end=len(text),
        text=text,
        scope="local",
    )
    inputs = DeclaredStructuralInput(
        question="Read exact artifact",
        scope="local",
        inventory_id="explicit",
        policy_id="artifact-identity-5",
        sources=(original,),
        passages=(passage,),
        dependencies=("product:navigation",),
    )
    navigation = NativeNavigationIndex((product(selected),), selected).require()
    return selected, frame, original, inputs, navigation


def test_native_artifact_discovery_keeps_known_absence_and_actual_semantic_witnesses():
    from corpus_structure.semantic.artifact_products import native_artifact_records

    selected, frame, original, inputs, navigation = artifact_case()
    (record,) = native_artifact_records(
        frame, selected, inputs, original.identity, "work:book", navigation
    )
    assert record.artifact.controlled_code == "2.1" and record.artifact.artifact_kind == "table"
    assert record.artifact.alias_state == "known_empty" and record.artifact.aliases == ()
    assert record.artifact.alias_absence is not None
    assert record.artifact.alias_absence.text == "aliases: none"
    assert record.citations[0].text == "Table 2.1"
    assert record.primary_node is not None
    assert record.primary_node.product_id == "product:navigation"
    assert record.primary_node == record.artifact.primary_node
    assert b"task_id" not in canonical_bytes(record.model_dump(mode="json"))
    assert b"source_view_id" not in canonical_bytes(record.source_contribution)


def test_native_artifact_discovery_retains_unknown_aliases_and_requires_complete_navigation():
    from corpus_structure.semantic.artifact_products import native_artifact_records

    selected, frame, original, inputs, navigation = artifact_case("Table 2.1.")
    (record,) = native_artifact_records(
        frame, selected, inputs, original.identity, "work:book", navigation
    )
    assert record.artifact.alias_state == "unknown" and record.artifact.alias_absence is None
    with pytest.raises(ValueError, match="missing or incomplete"):
        native_artifact_records(
            frame,
            selected,
            inputs,
            original.identity,
            "work:book",
            NativeNavigationIndex((), selected),
        )
