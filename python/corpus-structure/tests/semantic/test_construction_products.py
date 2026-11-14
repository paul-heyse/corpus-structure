"""Independent ordinary source-native construction expectations."""

from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import (
    ConstructionOptions,
    PreparedConstructionProfile,
    construction_product_inputs,
    validate_construction_product,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from semantic.formal_products_support import selected


@pytest.fixture(scope="module")
def profiles():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = construction_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(), python_sources=formal_operation_sources()
        ),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    return prepare_formal_evidence(
        prepared, model, grammar=grammar_identity()
    ), PreparedConstructionProfile(prepared, model)


def test_target_grammar_preserves_operators_binders_choices_and_witnesses(profiles, monkeypatch):
    formal, construction = profiles
    source = selected(formal, "Not every trial succeeds.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    from corpus_structure.semantic.constructions import forest

    monkeypatch.setattr(
        forest, "classify", lambda *_: pytest.fail("inference reclassified primary text")
    )
    product = construction.run(source, (primary,), subject_context=_publication_context(source))
    values = product.inventory()
    assert any(row["kind"] == "binder" for row in values["terms"])
    assert any(row["value"] == "negation" for row in values["terms"])
    assert values["roles"]
    assert all(row["basis"]["kind"] == "released_construction" for row in values["roles"])
    assert (
        product.value.outcome == "partial"
    )  # richer native reading families are explicitly unavailable
    assert b"task_id" not in product.content and b"release_id" not in product.content
    assert all(
        "source_view_id" not in extent for row in values["occurrences"] for extent in row["extents"]
    )
    assert b"ordinary" in next(
        kind.facts for kind in construction.model.kinds if kind.name == "DdoConstructionProduct"
    )


def test_limits_and_custody_do_not_salt_successful_constructed_meaning(profiles):
    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    left = construction.run(
        source,
        (primary,),
        ConstructionOptions(parse_seconds=2),
        subject_context=_publication_context(source),
    )
    right = construction.run(
        source,
        (primary,),
        ConstructionOptions(parse_seconds=3, max_region_chars=5000),
        subject_context=_publication_context(source),
    )
    assert left.content == right.content
    assert left.semantic_id == right.semantic_id
    assert left.reference.values() == {"product_id": left.semantic_id}


def test_target_nominal_member_and_original_occurrence_cannot_be_relabelled(profiles):
    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    product = construction.run(source, (primary,), subject_context=_publication_context(source))
    body = product.value.model_dump(mode="json", exclude_unset=True)
    occurrence = next(
        packet for packet in body["members"] if packet["body"]["record_type"] == "occurrence"
    )
    occurrence["body"]["extents"][0]["text"] = "forged"
    with pytest.raises(ValueError, match=r"original source identity|positioned source"):
        validate_construction_product(
            construction.prepared, construction.model, body, source, (primary,)
        )
    body = product.value.model_dump(mode="json", exclude_unset=True)
    body["members"][0]["kind_contract"] = "another-nominal-kind"
    with pytest.raises(ValueError, match="nominal meaning"):
        validate_construction_product(
            construction.prepared, construction.model, body, source, (primary,)
        )


def test_contextual_evaluation_consumes_real_products_and_retains_governed_premises(profiles):
    from corpus_structure.semantic.construction_products import PreparedContextualProfile

    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    symbolic = construction.run(source, (primary,), subject_context=_publication_context(source))
    meaning = PreparedContextualProfile(construction.prepared, construction.model).run(
        source, (symbolic,), (primary,), subject_context=_publication_context(source)
    )
    inventory = meaning.inventory()
    assert inventory["terms"]
    assert meaning.value.model_dump(mode="python")["environment"] is not None
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
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    product = construction.run(source, (primary,), subject_context=_publication_context(source))
    body = product.value.model_dump(mode="json", exclude_unset=True)
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
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    symbolic = construction.run(source, (primary,), subject_context=_publication_context(source))
    view = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        (primary, symbolic),
        active=(DataProductReference(symbolic.semantic_id),),
        subject_context=_publication_context((source,)[0], document=True),
    )
    readings = EnrichedDocumentReadings(view, (primary, symbolic))
    assert readings.source().content == source.content
    member_id = next(
        packet["member_id"]
        for packet in symbolic.value.model_dump(mode="json", exclude_unset=True)["members"]
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
            subject_context=_publication_context((source,)[0], document=True),
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
        subject_context=_publication_context((source,)[0], document=True),
    )
    assert base.value.model_dump(mode="python")["outcome"] == "complete"
    full = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        (),
        profile="full_characterization",
        subject_context=_publication_context((source,)[0], document=True),
    )
    full_value = full.value.model_dump(mode="python")
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
    changed = selected(formal, "Every trial succeeds.").value
    changed["source"]["section_pointer"] = "#/groups/1"
    right = FrozenNativeSource.acquire(construction.prepared, changed)
    products = tuple(
        formal.run(source, FormalEvidenceOptions(), subject_context=_publication_context(source))
        for source in (left, right)
    )
    view = compose_enriched_document(
        construction.prepared,
        construction.model,
        (left, right),
        products,
        active=tuple(DataProductReference(product.semantic_id) for product in products),
        subject_context=_publication_context((left, right)[0], document=True),
    )
    readings = EnrichedDocumentReadings(view, products)
    view_value = view.value.model_dump(mode="python")
    assert view_value["original_document"] == left.value["source"]["document"]
    assert len(view_value["sources"]) == 2
    assert readings.source(right.value["source"]).content == right.content
    with pytest.raises(ValueError, match="explicit source coordinate"):
        readings.source()
    assert {row["source"]["projection"] for row in view_value["coverage"]} == {
        left.value["source"]["projection"],
        right.value["source"]["projection"],
    }


def test_retained_working_doc_uses_native_lexeme_values_without_source_getters(profiles):
    from spacy.attrs import IS_ALPHA, IS_PUNCT, IS_QUOTE, IS_SPACE, LIKE_NUM, LOWER
    from spacy.tokens import Doc
    from spacy.vocab import Vocab

    from corpus_structure.semantic.construction_products import CharacterizationSnapshot
    from corpus_structure.semantic.constructions.matching import (
        retained_native_documents,
        retained_native_vocab,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    formal, _ = profiles
    source = selected(formal, "Alpha.")
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
    identifiers = ("a" * 64, "b" * 64)
    tokens = [
        dict(
            record_type="token",
            local_id=identifiers[token.i],
            block_id="#/texts/0",
            ordinal=token.i,
            start=token.idx,
            end=token.idx + len(token),
            lemma=token.lemma_,
            pos=token.pos_,
            tag=token.tag_,
            morphology=[],
            dependency=token.dep_,
            head_ref=identifiers[token.head.i],
            sent_start=bool(token.is_sent_start),
            lower=token.lower_,
            is_alpha=token.is_alpha,
            is_space=token.is_space,
            is_punct=token.is_punct,
            is_quote=token.is_quote,
            like_num=token.like_num,
        )
        for token in original
    ]
    native = CharacterizationSnapshot(
        "product:controlled",
        canonical_bytes(
            dict(
                members=[dict(body=token) for token in tokens],
                annotation_columns=[dict(block_id="#/texts/0", start=0, end=6)],
            )
        ),
    )
    vocab = retained_native_vocab(source, native)
    _, doc, _, start, end = next(retained_native_documents(source, native, vocab))
    assert (start, end, doc.text) == (0, 6, "Alpha.")
    assert doc[0].lower_ == "retained" and doc[0].is_alpha is False
    assert (doc[1].dep_, doc[1].head.i) == ("punct", 0)


def _publication_context(source, *, document=False):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import source_subject

    value = source.value
    return SubjectContext(
        "family-test",
        value["source"]["document"] if document else source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}),
    )


def test_compact_family_members_preserve_parent_identity_and_complete_source_context(profiles):
    import json
    from dataclasses import replace

    from corpus_structure.semantic.characterization_manifests import manifest_contract
    from corpus_structure.semantic.construction_products import PreparedContextualProfile
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.enriched_document_products import (
        RetainedCharacterizationProduct,
        compose_enriched_document,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    context = _publication_context(source)
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
            replace(
                wrapper, selected_product=product.semantic_id, selected_member=manifest["member_id"]
            )
        )
    view = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        tuple(retained),
        active=tuple(DataProductReference(product.semantic_id) for product in retained),
        profile="selected_layers",
        subject_context=_publication_context(source, document=True),
    )
    assert json.loads(view.content)["products"] == [
        {"product_id": product.semantic_id} for product in (primary, symbolic, contextual)
    ]


@pytest.mark.gpu
def test_target_named_rules_reuse_actual_native_units_and_reject_foreign_block(profiles, monkeypatch):
    import json
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.methods.annotation_rules import AnnotationRule
    from corpus_structure.methods.native_host import NativeHostGroup
    from corpus_structure.semantic.sentence_products import prepare_sentence_profile
    from corpus_structure.settings import NemotronSettings
    from semantic.test_sentence_products import _controlled_source_pin

    formal, construction = profiles
    source = selected(formal, "Mean is finite.")
    context = _publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    sentence_profile = prepare_sentence_profile(construction.prepared, construction.model)
    with NativeHostGroup(CharacterizationExecutionPolicy(), NemotronSettings().endpoint) as host:
        annotations = sentence_profile.run(source, host=host, subject_context=context, source_pin=_controlled_source_pin(source))
    monkeypatch.setattr("corpus_structure.semantic.sentence_products.pipeline", lambda *_: pytest.fail("construction repeated native inference"))
    rule = AnnotationRule(rule="copula", variant="is", mechanism="token", pattern=[{"LOWER": "is"}], bindings={"cue": {"node": "match"}})
    from corpus_structure.semantic.constructions.math_scope import Binders, retained_math_scope_products
    binders = Binders(sentence_initial=("mean",))
    product = construction.run(source, (primary,), ConstructionOptions(annotation_rules=(rule,), math_scope_binders=binders), sentences=annotations, subject_context=context)
    inventory = product.inventory()
    from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_VOCABULARY
    assert any(row.get("vocabulary") == PRIMARY_RULE_VOCABULARY and row["kind"] == "predicate" for row in inventory["terms"])
    scope = retained_math_scope_products((product,), source, binders=binders)
    assert scope.complete and scope.sentences == ((0, len(source.value["text"])),)
    assert scope.flags(0) == {"initial"}
    assert not retained_math_scope_products((product,), source, binders=Binders(sentence_initial=("suppose",))).complete
    bindings = [row for row in inventory["annotations"] if row["kind"] == "construction.named_binding"]
    assert len(bindings) == 1
    match = bindings[0]["named_match"]
    assert match["rule"] == "copula" and match["status"] == "matched"
    assert match["native_container"] == {"product_id": annotations.semantic_id, "block_id": "#/texts/0"}
    native_members = {row["member_id"]: row["body"] for row in json.loads(annotations.content)["members"]}
    (ref,) = match["nodes"]
    assert ref["product_id"] == annotations.semantic_id
    token = native_members[ref["member_id"]]
    assert source.value["text"][token["start"]:token["end"]] == "is"
    assert any(row["family"] == "construction.named_rules" and row["outcome"] == "complete" for row in inventory["coverage"])
    forged = json.loads(product.content)
    for packet in forged["members"]:
        if packet["body"].get("kind") == "construction.named_binding":
            packet["body"]["named_match"]["native_container"]["block_id"] = "#/texts/foreign"
    with pytest.raises(ValueError, match="exact original native block"):
        validate_construction_product(construction.prepared, construction.model, forged, source, (primary, annotations), subject_context=context)


def test_statistics_named_rule_configuration_belongs_to_construction_profile():
    from corpus_structure.semantic.construction_products import load_construction_options

    options = load_construction_options(Path(__file__).resolve().parents[4] / "domains/statistics")
    assert len(options.annotation_rules) == 15
    assert {("defining", "active_as"), ("naming", "passive_called_term"), ("condition_exception", "marked_clause")} <= {(rule.rule, rule.variant) for rule in options.annotation_rules}


def test_target_math_scope_keeps_unavailable_native_coverage_open(profiles):
    from corpus_structure.semantic.constructions.math_scope import Binders, retained_math_scope_products

    formal, construction = profiles
    source = selected(formal, "Suppose x is finite.")
    context = _publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    binders = Binders(sentence_initial=("suppose",))
    product = construction.run(source, (primary,), ConstructionOptions(math_scope_binders=binders), subject_context=context)
    readings = retained_math_scope_products((product,), source, binders=binders)
    assert not readings.complete and readings.sentences == () and readings.cues == ()
    coverage = [row for row in product.inventory()["coverage"] if row["family"] == "construction.math_scope"]
    assert coverage and coverage[0]["outcome"] == "unknown"
