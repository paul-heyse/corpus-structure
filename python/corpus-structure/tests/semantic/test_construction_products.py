"""Independent ordinary source-native construction expectations."""

from pathlib import Path

import pytest

from corpus_structure.semantic.construction_products import (
    ConstructionOptions,
    validate_construction_product,
)
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_source_view import thaw_native
from semantic.construction_products_test_support import (
    profiles as profiles,
)
from semantic.construction_products_test_support import (
    publication_context as publication_context,
)
from semantic.formal_products_support import selected


def test_target_grammar_preserves_operators_binders_choices_and_witnesses(profiles, monkeypatch):
    formal, construction = profiles
    source = selected(formal, "Not every trial succeeds.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=publication_context(source)
    )
    from corpus_structure.semantic.constructions import forest

    monkeypatch.setattr(
        forest, "classify", lambda *_: pytest.fail("inference reclassified primary text")
    )
    product = construction.run(source, (primary,), subject_context=publication_context(source))
    values = product.inventory()
    assert any(row["kind"] == "binder" for row in values["terms"])
    assert any(row["value"] == "negation" for row in values["terms"])
    assert values["roles"]
    assert all(row["basis"]["kind"] == "released_construction" for row in values["roles"])
    assert (
        product.value["outcome"] == "partial"
    )  # richer native reading families are explicitly unavailable
    assert b"task_id" not in product.content and b"release_id" not in product.content
    assert all(
        "source_view_id" not in extent for row in values["occurrences"] for extent in row["extents"]
    )
    assert b"ordinary" in next(
        kind.facts for kind in construction.model.kinds if kind.name == "DdoConstructionProduct"
    )


def test_limits_and_custody_do_not_salt_successful_constructed_meaning(profiles):
    from corpus_structure.semantic.construction_products import ConstructionProduct

    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=publication_context(source)
    )
    left = construction.run(
        source,
        (primary,),
        ConstructionOptions(parse_seconds=2),
        subject_context=publication_context(source),
    )
    right = construction.run(
        source,
        (primary,),
        ConstructionOptions(parse_seconds=3, max_region_chars=5000),
        subject_context=publication_context(source),
    )
    assert left.content == right.content
    assert left.semantic_id == right.semantic_id
    assert left.reference.values() == {"product_id": left.semantic_id}
    assert left.with_context(left.subject_context).value is left.value
    assert left.inventory() is left.inventory()
    with pytest.raises(TypeError, match="validated production"):
        ConstructionProduct(left.content, left.prepared, left.model, left.subject_context)


def test_target_nominal_member_and_original_occurrence_cannot_be_relabelled(profiles):
    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=publication_context(source)
    )
    product = construction.run(source, (primary,), subject_context=publication_context(source))
    body = thaw_native(product.value)
    occurrence = next(
        packet for packet in body["members"] if packet["body"]["record_type"] == "occurrence"
    )
    occurrence["body"]["extents"][0]["text"] = "forged"
    with pytest.raises(ValueError, match=r"original source identity|positioned source"):
        validate_construction_product(
            construction.prepared, construction.model, body, source, (primary,)
        )
    body = thaw_native(product.value)
    body["members"][0]["kind_contract"] = "another-nominal-kind"
    with pytest.raises(ValueError, match="nominal meaning"):
        validate_construction_product(
            construction.prepared, construction.model, body, source, (primary,)
        )


def test_constructed_separator_and_epsilon_extents_preserve_projection_authority(profiles):
    from copy import deepcopy

    from corpus_structure.semantic.characterization import occurrence_id
    from corpus_structure.semantic.construction_products import (
        interpreted_member_contracts,
        interpreted_product_value,
    )
    from corpus_structure.semantic.constructions.layers import ConstructionLayer, ConstructionSource

    formal, construction = profiles
    source = selected(
        formal,
        "First\nSecond",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=5),
            dict(kind="synthetic_separator", start=5, end=6),
            dict(kind="native_text", item_ref="#/texts/1", source_field="text", start=6, end=12),
        ],
        items=[
            dict(self_ref="#/texts/0", label="text", text="First", orig="First"),
            dict(self_ref="#/texts/1", label="text", text="Second", orig="Second"),
        ],
        selectors=[dict(projection="pending", start=0, end=12)],
    )
    value = source.value
    layer = ConstructionLayer(
        value["source"], value, {"key": "controlled"}, families=("construction.predication",)
    )
    layer.record(
        "construction.predication", value["selectors"][0], "unknown", "only occurrences authored"
    )
    view = ConstructionSource.from_native(source)
    full = layer.occurrence(view, 0, 12)
    anchors = [layer.occurrence(view, boundary, boundary) for boundary in (0, 5, 6, 12)]
    extents = layer.occurrences[full]["extents"]
    assert [
        (row["start"], row["end"], row["native_pointer"], row["synthetic"]) for row in extents
    ] == [
        (0, 5, "#/texts/0", False),
        (5, 6, "#/texts/0", True),
        (6, 12, "#/texts/1", False),
    ]
    assert source.view.containing_piece("#/texts/0", 5, 6) is None
    body = interpreted_product_value(
        source,
        layer.facts(),
        interpreted_member_contracts(construction.prepared, construction.model),
        (),
    )
    body["annotation_support"] = []
    body["formal_support"] = []
    checked = validate_construction_product(
        construction.prepared,
        construction.model,
        body,
        source,
        (),
        subject_context=publication_context(source),
    )
    assert len(checked.inventory()["occurrences"]) == 5
    for occurrence_id_to_forge, index, change in (
        (full, 1, {"synthetic": False}),
        (full, 1, {"native_pointer": "#/texts/1"}),
        (full, 0, {"synthetic": True}),
        (anchors[1], 0, {"synthetic": False}),
        (anchors[2], 0, {"native_pointer": "#/texts/0"}),
    ):
        forged = deepcopy(body)
        occurrence = next(
            packet for packet in forged["members"] if packet["member_id"] == occurrence_id_to_forge
        )
        occurrence["body"]["extents"][index].update(change)
        key = occurrence_id(value["source"], occurrence["body"]["extents"])
        occurrence["member_id"] = occurrence["body"]["local_id"] = key
        with pytest.raises(ValueError, match="original positioned source"):
            validate_construction_product(
                construction.prepared,
                construction.model,
                forged,
                source,
                (),
                subject_context=publication_context(source),
            )


def test_contextual_evaluation_consumes_real_products_and_retains_governed_premises(profiles):
    from corpus_structure.semantic.construction_products import PreparedContextualProfile

    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=publication_context(source)
    )
    symbolic = construction.run(source, (primary,), subject_context=publication_context(source))
    meaning = PreparedContextualProfile(construction.prepared, construction.model).run(
        source, (symbolic,), (primary,), subject_context=publication_context(source)
    )
    inventory = meaning.inventory()
    assert inventory["terms"]
    assert meaning.value["environment"] is not None
    assert b"task_id" not in meaning.content and b"source_view_id" not in meaning.content
    refs = [ref for row in inventory["terms"] for ref in row.get("external_premises", ())]
    assert refs and all(set(ref) == {"product_id", "member_id"} for ref in refs)
    assert {ref["product_id"] for ref in refs} <= {primary.semantic_id, symbolic.semantic_id}
    assert meaning.semantic_id not in {primary.semantic_id, symbolic.semantic_id}
    assert any(row["kind"] == "binder" for row in inventory["terms"])


def test_construction_choice_members_are_real_flattened_addresses(profiles):
    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=publication_context(source)
    )
    product = construction.run(source, (primary,), subject_context=publication_context(source))
    body = thaw_native(product.value)
    groups = [
        packet["body"] for packet in body["members"] if packet["body"]["record_type"] == "choice"
    ]
    alternatives = {
        packet["member_id"]: packet["body"]
        for packet in body["members"]
        if packet["body"]["record_type"] == "choice_member"
    }
    assert groups and alternatives
    assert alternatives == {
        member["local_id"]: dict(record_type="choice_member", group_id=group["local_id"], **member)
        for group in groups
        for member in group["members"]
    }


def test_combined_document_preserves_source_and_exact_cross_layer_member_addresses(profiles):
    from corpus_structure.semantic.data_product_reference import (
        DataProductMemberReference,
        DataProductReference,
    )
    from corpus_structure.semantic.enriched_document_products import (
        EnrichedDocumentReadings,
        compose_enriched_document,
    )

    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=publication_context(source)
    )
    symbolic = construction.run(source, (primary,), subject_context=publication_context(source))
    view = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        (primary, symbolic),
        active=(DataProductReference(symbolic.semantic_id),),
        subject_context=publication_context((source,)[0], document=True),
    )
    readings = EnrichedDocumentReadings(view, (primary, symbolic))
    assert readings.source().content == source.content
    member_id = next(
        packet["member_id"]
        for packet in symbolic.value["members"]
        if packet["body"]["record_type"] == "choice_member"
    )
    reference = DataProductMemberReference(DataProductReference(symbolic.semantic_id), member_id)
    packet = readings.member(reference, active_only=True)
    assert packet["body"]["group_id"]
    assert packet["member_id"] == member_id
    packet["body"]["group_id"] = "caller mutation"
    assert readings.member(reference)["body"]["group_id"] != "caller mutation"
    with pytest.raises(ValueError, match="missing an exact selected dependency"):
        compose_enriched_document(
            construction.prepared,
            construction.model,
            (source,),
            (symbolic,),
            active=(symbolic.reference,),
            subject_context=publication_context((source,)[0], document=True),
        )
    with pytest.raises(ValueError, match="actual retained canonical packet"):
        readings.member(DataProductMemberReference(symbolic.reference, "not-a-member"))


def test_source_only_and_full_combined_views_preserve_distinct_coverage_claims(profiles):
    from corpus_structure.semantic.enriched_document_products import compose_enriched_document

    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    base = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        (),
        profile="source_only",
        subject_context=publication_context((source,)[0], document=True),
    )
    assert base.value["outcome"] == "complete"
    full = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        (),
        profile="full_characterization",
        subject_context=publication_context((source,)[0], document=True),
    )
    full_value = full.value
    assert full_value["outcome"] == "partial"
    assert full_value["coverage"] and all(
        row["outcome"] == "unknown" for row in full_value["coverage"]
    )


def test_multi_source_view_keeps_each_projection_local_coordinate(profiles):
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.enriched_document_products import (
        EnrichedDocumentReadings,
        compose_enriched_document,
    )
    from corpus_structure.semantic.source_products import FrozenNativeSource

    formal, construction = profiles
    left = selected(formal, "All samples are finite.")
    changed = thaw_native(selected(formal, "Every trial succeeds.").value)
    changed["source"]["section_pointer"] = "#/groups/1"
    right = FrozenNativeSource.acquire(construction.prepared, changed)
    products = tuple(
        formal.run(source, FormalEvidenceOptions(), subject_context=publication_context(source))
        for source in (left, right)
    )
    view = compose_enriched_document(
        construction.prepared,
        construction.model,
        (left, right),
        products,
        active=tuple(DataProductReference(product.semantic_id) for product in products),
        subject_context=publication_context((left, right)[0], document=True),
    )
    readings = EnrichedDocumentReadings(view, products)
    view_value = view.value
    assert view_value["original_document"] == left.value["source"]["document"]
    assert len(view_value["sources"]) == 2
    assert readings.source(right.value["source"]).content == right.content
    with pytest.raises(ValueError, match="explicit source coordinate"):
        readings.source()
    assert {row["source"]["projection"] for row in view_value["coverage"]} == {
        left.value["source"]["projection"],
        right.value["source"]["projection"],
    }


def test_captured_composition_canonicalizes_sets_without_reordering_explicit_sequences(profiles):
    from types import SimpleNamespace
    from typing import cast

    from corpus_structure.methods.captured_document_composition import ComposeCapturedDocumentFamily
    from corpus_structure.semantic.characterization_ports import execute_view_profile
    from corpus_structure.semantic.source_products import FrozenNativeSource

    formal, construction = profiles
    left = selected(formal, "All samples are finite.")
    changed = thaw_native(selected(formal, "Every trial succeeds.").value)
    changed["source"]["section_pointer"] = "#/groups/1"
    right = FrozenNativeSource.acquire(construction.prepared, changed)
    products = tuple(
        formal.run(source, FormalEvidenceOptions(), subject_context=publication_context(source))
        for source in (left, right)
    )
    receiver = cast(ComposeCapturedDocumentFamily, SimpleNamespace(profile=construction))
    first = ComposeCapturedDocumentFamily.run(
        receiver, (left, right), (), (), (), products, (), (), (), "selected_layers"
    )
    second = ComposeCapturedDocumentFamily.run(
        receiver, (right, left), (), (), (), products[::-1], (), (), (), "selected_layers"
    )
    assert first is not None and second is not None
    assert first.content == second.content
    value = first.value
    assert {row["source"]["projection"] for row in value["sources"]} == {
        left.value["source"]["projection"],
        right.value["source"]["projection"],
    }
    assert {row["product_id"] for row in value["products"]} == {
        product.semantic_id for product in products
    }
    explicit = execute_view_profile(receiver, (right, left), products[::-1], (), "selected_layers")
    assert canonical_bytes(explicit.value["sources"]) == canonical_bytes([right.value, left.value])


def test_retained_working_doc_uses_native_lexeme_values_without_source_getters(monkeypatch):
    from spacy.attrs import IS_ALPHA, IS_PUNCT, IS_QUOTE, IS_SPACE, LIKE_NUM, LOWER
    from spacy.tokens import Doc
    from spacy.vocab import Vocab

    from corpus_structure.semantic.constructions.matching import (
        retained_native_documents,
        retained_native_vocab,
    )

    original = Doc(
        Vocab(
            lex_attr_getters={
                LOWER: lambda text: "retained" if text == "Alpha" else text,
                IS_ALPHA: lambda text: False,
                IS_SPACE: lambda text: False,
                IS_PUNCT: lambda text: text == ".",
                IS_QUOTE: lambda text: False,
                LIKE_NUM: lambda text: False,
            }
        ),
        words=["Alpha", "."],
        spaces=[False, False],
        lemmas=["alpha", "."],
        pos=["NOUN", "PUNCT"],
        tags=["NN", "."],
        heads=[0, 0],
        deps=["ROOT", "punct"],
    )
    import json

    from annotation_support import ControlledPipeline, selected_item
    from methods.declared_primary_fixture import retained_source_annotations

    from corpus_structure.ingest import annotations as annotation_owner
    from corpus_structure.ingest.annotations import AnnotationProfile, annotate
    from corpus_structure.semantic.sentence_products import source_annotation_blocks
    from semantic.source_annotations_test_support import partition_controlled_annotations

    controlled = ControlledPipeline()
    request, source, frame, context = selected_item(
        controlled, "Alpha.", start=0, block_id="#/texts/1"
    )
    monkeypatch.setattr(annotation_owner, "pipeline", lambda _: controlled)
    annotation_profile = AnnotationProfile(
        execution_profile=controlled.selection().native.fingerprint
    )
    (annotation,) = annotate(
        (request,), annotation_profile, processed_docs=(original,), require_complete=False
    )
    native = retained_source_annotations(source, frame, context, (annotation,), annotation_profile)
    value = json.loads(native.content)
    value["blocks"] = thaw_native(source_annotation_blocks(native))
    value["blocks"][0]["lexemes"] = [
        dict(
            lower=token.lower_,
            is_alpha=token.is_alpha,
            is_space=token.is_space,
            is_punct=token.is_punct,
            is_quote=token.is_quote,
            like_num=token.like_num,
            sent_start=token.is_sent_start,
        )
        for token in original
    ]
    native = partition_controlled_annotations(
        native.prepared,
        native.model,
        value,
        source,
        configuration=annotation_profile.configuration,
        subject_context=context,
    )
    assert len(native.inventory("token")) == 2
    vocab = retained_native_vocab(source, native)
    _, doc, _, start, end = next(retained_native_documents(source, native, vocab))
    assert (start, end, doc.text) == (0, 6, "Alpha.")
    assert doc[0].lower_ == "retained" and doc[0].is_alpha is False
    assert (doc[1].dep_, doc[1].head.i) == ("punct", 0)


def test_compact_family_members_preserve_parent_identity_and_complete_source_context(profiles):
    import json

    from corpus_structure.semantic.characterization_manifests import manifest_contract
    from corpus_structure.semantic.construction_products import PreparedContextualProfile
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.enriched_document_products import (
        RetainedCharacterizationProduct,
        compose_enriched_document,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    context = publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    symbolic = construction.run(source, (primary,), subject_context=context)
    contextual = PreparedContextualProfile(construction.prepared, construction.model).run(
        source, (symbolic,), (primary,), subject_context=context
    )
    retained = []
    for product, name in (
        (primary, "DdoFormalManifest"),
        (symbolic, "DdoConstructionManifest"),
        (contextual, "DdoContextualManifest"),
    ):
        value = json.loads(product.content)
        manifests = [
            packet for packet in value["members"] if packet["body"]["record_type"] == "manifest"
        ]
        assert len(manifests) == 1
        manifest = manifests[0]
        assert manifest["kind_contract"] == manifest_contract(
            construction.prepared, construction.model, name
        )
        assert manifest["context"]["subject"] == context.subject
        assert manifest["body"]["source"] == source.value["source"]
        assert "members" not in manifest["body"] and "lexicon" not in manifest["body"]
        wrapper = RetainedCharacterizationProduct.acquire(
            construction.prepared,
            construction.model,
            construction.prepared.index.definitions[name].iri,
            canonical_bytes(manifest["body"]),
            subject_context=context,
        )
        retained.append(
            wrapper.with_context(
                context,
                member=BoundRoleMember(
                    product=product.semantic_id,
                    kind_contract=manifest["kind_contract"],
                    subject=context.subject,
                    original_source=context.original_source,
                    analyzed_scope=context.analyzed_scope,
                    coverage=b"[]",
                    subject_definition=context.subject_definition,
                    support_episodes=(),
                    support_evidence=b"[]",
                    support_references=(),
                    member=manifest["member_id"],
                ),
            )
        )
        assert retained[-1].value is wrapper.value
    view = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        tuple(retained),
        active=tuple(DataProductReference(product.semantic_id) for product in retained),
        profile="selected_layers",
        subject_context=publication_context(source, document=True),
    )
    assert json.loads(view.content)["products"] == [
        {"product_id": product.semantic_id} for product in (primary, symbolic, contextual)
    ]


@pytest.mark.gpu
def test_target_named_rules_reuse_actual_native_units_and_reject_foreign_block(
    profiles, monkeypatch
):
    import json

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.methods.annotation_rules import AnnotationRule
    from corpus_structure.methods.native_host import NativeHostGroup
    from corpus_structure.semantic.sentence_products import prepare_sentence_profile
    from corpus_structure.settings import NemotronSettings
    from semantic.sentence_products_test_support import controlled_source_pin

    formal, construction = profiles
    source = selected(formal, "Mean is finite.")
    context = publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    sentence_profile = prepare_sentence_profile(construction.prepared, construction.model)
    with NativeHostGroup(CharacterizationExecutionPolicy(), NemotronSettings().endpoint) as host:
        annotations = sentence_profile.run(
            source, host=host, subject_context=context, source_pin=controlled_source_pin(source)
        )
    monkeypatch.setattr(
        "corpus_structure.semantic.sentence_products.pipeline",
        lambda *_: pytest.fail("construction repeated native inference"),
    )
    rule = AnnotationRule(
        rule="copula",
        variant="is",
        mechanism="token",
        pattern=[{"LOWER": "is"}],
        bindings={"cue": {"node": "match"}},
    )
    from corpus_structure.semantic.constructions.math_scope import (
        Binders,
        retained_math_scope_products,
    )

    binders = Binders(sentence_initial=("mean",))
    product = construction.run(
        source,
        (primary,),
        ConstructionOptions(annotation_rules=(rule,), math_scope_binders=binders),
        sentences=annotations,
        subject_context=context,
    )
    inventory = product.inventory()
    from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_VOCABULARY

    assert any(
        row.get("vocabulary") == PRIMARY_RULE_VOCABULARY and row["kind"] == "predicate"
        for row in inventory["terms"]
    )
    scope = retained_math_scope_products((product,), source, binders=binders)
    assert scope.complete and scope.sentences == ((0, len(source.value["text"])),)
    assert scope.flags(0) == {"initial"}
    from corpus_structure.methods.predicate_contributions import declared_predicate_evidence
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.sentence_products import (
        retained_source_annotation_products,
        source_annotation_rows,
    )
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        PreparedNativeSources,
        source_slice,
    )

    rows = source_annotation_rows(annotations)
    frame = DeclaredNativeFrameSource.from_source(source, rows[0]["source"]["content"])
    native_context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, 0, len(frame.text)),),
        "predicate target test",
        "retained-primary",
        "complete original",
        version=2,
        preparation=PreparedNativeSources((frame,)),
    )
    evidence = declared_predicate_evidence(
        frame,
        native_context,
        retained_source_annotation_products(source, annotations),
        dependency="native-product:" + annotations.semantic_id,
        primary_products=(product,),
        formal_products=(primary,),
    )
    assert evidence.inspection_complete
    assert any(
        row["semantic_type"] == "structural.predicate_frame" for row in evidence.contributions
    )
    assert all(
        "product_id" in row["component"]["primary_node"]
        for row in evidence.contributions
        if row.get("component", {}).get("primary_node")
    )
    assert not retained_math_scope_products(
        (product,), source, binders=Binders(sentence_initial=("suppose",))
    ).complete
    bindings = [
        row for row in inventory["annotations"] if row["kind"] == "construction.named_binding"
    ]
    assert len(bindings) == 1
    match = bindings[0]["named_match"]
    assert match["rule"] == "copula" and match["status"] == "matched"
    assert match["block_id"] == "#/texts/0"
    from corpus_structure.semantic.construction_products import annotation_support_index
    from corpus_structure.semantic.sentence_partitions import blocks_from_packets

    support = annotation_support_index(json.loads(product.content))
    ((position, reference),) = support[bindings[0]["local_id"], "named_node", None]
    assert position == 0 and reference.partition_key == match["block_id"]
    assert reference.role == "sentences"
    assert annotations.partitions is not None
    blocks = blocks_from_packets(tuple(json.loads(packet) for packet in annotations.partitions))
    (block,) = (block for block in blocks if block.key == reference.partition_key)
    (token,) = (
        row for row in block.rows if (row["record_type"], row["ordinal"]) == reference.item_key
    )
    assert source.value["text"][block.start + token["start"] : block.start + token["end"]] == "is"
    assert any(
        row["family"] == "construction.named_rules" and row["outcome"] == "complete"
        for row in json.loads(product.content)["coverage"]
    )
    from corpus_structure.semantic.data_operation_values import (
        decode_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.enriched_document_products import RetainedCharacterizationProduct

    retained = RetainedCharacterizationProduct.acquire(
        construction.prepared,
        construction.model,
        construction.prepared.index.definitions["DdoSourceAnnotations"].iri,
        annotations.content,
        partitions=annotations.partitions,
        subject_context=context,
    )
    assert retained.partition_blocks == annotations.partition_blocks
    rebound = retained.with_context(context)
    assert rebound.partition_blocks is retained.partition_blocks
    altered = json.loads(annotations.partitions[0])
    rows = decode_semantic_value(altered["body"])
    rows[0]["ordinal"] += 1
    altered["body"] = semantic_value(rows)
    with pytest.raises(ValueError, match="partition digest differs"):
        RetainedCharacterizationProduct.acquire(
            construction.prepared,
            construction.model,
            retained.kind,
            annotations.content,
            partitions=(canonical_bytes(altered), *annotations.partitions[1:]),
            subject_context=context,
        )
    monkeypatch.setattr(
        "corpus_structure.semantic.sentence_partitions.acquire_sentence_partitions",
        lambda *_: pytest.fail("construction decoded already admitted annotation blocks"),
    )
    for original_annotations in (annotations, rebound):
        restored = validate_construction_product(
            construction.prepared,
            construction.model,
            json.loads(product.content),
            source,
            (primary, original_annotations),
            subject_context=context,
        )
        assert restored.content == product.content
    forged = json.loads(product.content)
    for packet in forged["members"]:
        if packet["body"].get("kind") == "construction.named_binding":
            packet["body"]["named_match"]["block_id"] = "#/texts/foreign"
    with pytest.raises(ValueError, match="exact original native block"):
        validate_construction_product(
            construction.prepared,
            construction.model,
            forged,
            source,
            (primary, annotations),
            subject_context=context,
        )

    from corpus_structure.semantic.construction_products import acquired_construction_product
    from corpus_structure.semantic.data_operation_model import BoundRoleMember

    product_kind = construction.prepared.index.definitions[product.kind_name].iri
    member = BoundRoleMember(
        product=product.semantic_id,
        kind_contract=next(
            row.key
            for row in construction.model.identities
            if row.owner == product_kind and row.domain == "kind"
        ),
        subject=context.subject,
        subject_definition=context.subject_definition,
        original_source=context.original_source,
        analyzed_scope=context.analyzed_scope,
        coverage=b"{}",
        support_episodes=(),
        support_evidence=b"{}",
        support_references=(),
    )

    def repeated(*_args, **_kwargs):
        pytest.fail("already established annotation support was validated again")

    monkeypatch.setattr(
        "corpus_structure.semantic.construction_products.verify_interpreted_annotation_support",
        repeated,
    )
    assert (
        acquired_construction_product(
            construction.prepared,
            construction.model,
            product.value,
            source,
            (primary, rebound),
            subject_context=context,
            member=member,
        ).content
        == product.content
    )
    with pytest.raises(ValueError, match="exact retained dependency closure"):
        acquired_construction_product(
            construction.prepared,
            construction.model,
            product.value,
            source,
            (primary,),
            subject_context=context,
            member=member,
        )


def test_statistics_named_rule_configuration_belongs_to_construction_profile():
    from corpus_structure.semantic.construction_products import load_construction_options

    options = load_construction_options(Path(__file__).resolve().parents[4] / "domains/statistics")
    assert {(rule.rule, rule.variant) for rule in options.annotation_rules} == {
        ("defining", "active_as"),
        ("defining", "active_as_term_attachment"),
        ("defining", "active_as_marked_nominal"),
        ("defining", "passive_as"),
        ("defining", "active_to_be"),
        ("defining", "passive_to_be"),
        ("naming", "active_called_term"),
        ("naming", "passive_called_term"),
        ("defining", "passive_following_display"),
        ("defining", "active_following_display"),
        ("explanation", "given_following_display"),
        ("definition_context", "numbered_label"),
        ("definition_context", "labelled_copula_display"),
        ("defining", "nominal_follows"),
        ("defining", "constructive_copula"),
        ("symbol_declaration", "denotes"),
        ("condition_exception", "marked_clause"),
    }
    added = {
        rule.variant: rule
        for rule in options.annotation_rules
        if rule.variant in {"active_as_term_attachment", "active_as_marked_nominal"}
    }
    for rule in added.values():
        assert set(rule.bindings) == {"defining_cue", "defined_term", "defining_content"}
        assert rule.bindings["defined_term"].node == "term"
        assert rule.bindings["defining_content"].node == "content"
    assert added["active_as_marked_nominal"].bindings["defining_content"].exclude_nodes == ("as",)


def test_target_math_scope_keeps_unavailable_native_coverage_open(profiles):
    from corpus_structure.semantic.constructions.math_scope import (
        Binders,
        retained_math_scope_products,
    )

    formal, construction = profiles
    source = selected(formal, "Suppose x is finite.")
    context = publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    binders = Binders(sentence_initial=("suppose",))
    product = construction.run(
        source, (primary,), ConstructionOptions(math_scope_binders=binders), subject_context=context
    )
    readings = retained_math_scope_products((product,), source, binders=binders)
    assert not readings.complete and readings.sentences == () and readings.cues == ()
    import json

    coverage = [
        row
        for row in json.loads(product.content)["coverage"]
        if row["family"] == "construction.math_scope"
    ]
    assert coverage and coverage[0]["outcome"] == "unknown"


def test_target_source_owned_atoms_preserve_exact_inline_formula_extent(profiles):
    formal, construction = profiles
    text = "A uses x + y."
    source = selected(
        formal,
        text,
        pieces=[
            dict(start=0, end=7, kind="native_text", item_ref="#/texts/0", source_field="text"),
            dict(start=7, end=12, kind="native_text", item_ref="#/texts/1", source_field="text"),
            dict(start=12, end=13, kind="native_text", item_ref="#/texts/0", source_field="text"),
        ],
        items=[
            dict(
                self_ref="#/texts/0",
                label="paragraph",
                text=text,
                orig=text,
                prov=[dict(page_no=1)],
            ),
            dict(
                self_ref="#/texts/1",
                label="formula",
                parent="#/texts/0",
                text="x + y",
                orig="x + y",
                prov=[dict(page_no=1)],
            ),
        ],
    )
    context = publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    independent = formal.run(
        source, FormalEvidenceOptions(math_start="relation"), subject_context=context
    )
    assert primary.semantic_id != independent.semantic_id
    product = construction.run(source, (primary, independent), subject_context=context)
    reordered = construction.run(source, (independent, primary), subject_context=context)
    assert product.content == reordered.content
    inventory = product.inventory()
    atoms = [
        row
        for row in inventory["annotations"]
        if row["kind"] == "grammar.terminal" and row.get("native_label") == "ATOM"
    ]
    assert atoms
    edges = atoms[0]["external_premises"]
    assert {edge["product_id"] for edge in edges} == {primary.semantic_id, independent.semantic_id}
    (retained_atom,) = {edge["member_id"] for edge in edges}
    assert [row["target"]["occurrence"] for row in product.value["formal_support"]] == ["0", "1"]
    assert all(
        row["target"]["member_id"] == retained_atom for row in product.value["formal_support"]
    )
    assert not any(
        packet["body"].get("external_premises")
        for packet in product.value["members"]
        if packet["member_id"] == atoms[0]["local_id"]
    )
    by_id = {row["local_id"]: row for row in inventory["occurrences"]}
    assert any(
        [
            (extent["start"], extent["end"], extent["text"])
            for extent in by_id[row["occurrences"][0]]["extents"]
        ]
        == [(7, 12, "x + y")]
        for row in atoms
    )


def test_target_lexical_formal_root_keeps_paragraph_quantifier_and_predicate(profiles):
    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    context = publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    product = construction.run(source, (primary,), subject_context=context)
    inventory = product.inventory()
    assert {row["kind"] for row in inventory["terms"]} >= {"binder", "predicate"}
    assert not any(row.get("native_label") == "ATOM" for row in inventory["annotations"])
