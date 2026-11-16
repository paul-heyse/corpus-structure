"""Current selected M1 qualification from controlled columns, without provider evidence."""

from dataclasses import replace
from pathlib import Path

import pytest
from annotation_support import controlled as controlled
from semantic.test_m1_declared_products import _sources, configuration, record_schemas
from semantic.test_source_annotations import detached as detached

from corpus_structure.core.vocab import ObservationOutcome
from corpus_structure.methods.assertion_qualification import AssertionQualification
from corpus_structure.methods.m1_source import M1CandidateProduct, configured_packs
from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.construction_products import PreparedConstructionProfile
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import (
    body_identity,
    contextual_product_identity,
)
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import FormalEvidenceOptions, prepare_formal_evidence
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.m1_products import PreparedM1Inputs, m1_operation_inputs
from corpus_structure.semantic.sentence_products import validate_source_annotations
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    source_slice,
)
from corpus_structure.semantic.source_products import source_subject
from corpus_structure.semantic.types import PreparationProfile
from methods.record_assembly_support import report


@pytest.fixture(scope="module")
def acquired():
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

    config = configuration().sentences
    selected = NativeSelection(
        NativeProfile(
            "spacy",
            {"controlled": "columns"},
            {},
            config.model_dump(mode="json"),
            "float32",
            "cupy",
        ),
        Path("."),
    )
    bundle = m1_operation_inputs(record_schemas())
    prepared = prepare_release(bundle, profile=PreparationProfile(version="semantic-2"))
    return prepared, compile_data_operations(bundle, python_sources=_sources()), config, selected


NEGATIVE = {
    "text": "The pumps do not drain the tanks.",
    "columns": [
        ("the", "DET", "DT", "det", 1),
        ("pump", "NOUN", "NNS", "nsubj", 4),
        ("do", "AUX", "VBP", "aux", 4),
        ("not", "PART", "RB", "neg", 4),
        ("drain", "VERB", "VB", "ROOT", 4),
        ("the", "DET", "DT", "det", 6),
        ("tank", "NOUN", "NNS", "dobj", 4),
        (".", "PUNCT", ".", "punct", 4),
    ],
}
POSSIBLE = {
    "text": "The pumps might drain the tanks.",
    "columns": [
        ("the", "DET", "DT", "det", 1),
        ("pump", "NOUN", "NNS", "nsubj", 3),
        ("might", "AUX", "MD", "aux", 3),
        ("drain", "VERB", "VB", "ROOT", 3),
        ("the", "DET", "DT", "det", 5),
        ("tank", "NOUN", "NNS", "dobj", 3),
        (".", "PUNCT", ".", "punct", 3),
    ],
}

SHARED_NEGATION = {
    "text": "The pumps do not drain and fill the tanks.",
    "columns": [
        ("the", "DET", "DT", "det", 1),
        ("pump", "NOUN", "NNS", "nsubj", 4),
        ("do", "AUX", "VBP", "aux", 4),
        ("not", "PART", "RB", "neg", 4),
        ("drain", "VERB", "VB", "ROOT", 4),
        ("and", "CCONJ", "CC", "cc", 4),
        ("fill", "VERB", "VB", "conj", 4),
        ("the", "DET", "DT", "det", 8),
        ("tank", "NOUN", "NNS", "dobj", 6),
        (".", "PUNCT", ".", "punct", 4),
    ],
}


@pytest.fixture
def selected_inputs(acquired, detached):
    prepared, model, config, _ = acquired
    source, value = detached
    context = SubjectContext(
        "controlled-project",
        source_subject(source.value["source"]),
        source.value["source"]["document"],
        canonical_bytes(dict(source=source.value["source"], selectors=source.value["selectors"])),
        subject_definition="original-source-view",
    )
    annotations = validate_source_annotations(
        prepared, model, value, source, subject_context=context, configuration=config
    )
    formal = prepare_formal_evidence(prepared, model, grammar=grammar_identity()).run(
        source, FormalEvidenceOptions(), subject_context=context
    )
    construction = PreparedConstructionProfile(prepared, model).run(
        source, (formal,), sentences=annotations, subject_context=context
    )

    def member(product, kind, *, selected_member=None):
        return BoundRoleMember(
            product,
            kind,
            context.subject,
            context.original_source,
            context.analyzed_scope,
            b"{}",
            (),
            b"{}",
            member=selected_member,
            subject_definition=context.subject_definition,
            support_references=(),
        )

    primary = member(
        "controlled-original-product",
        "controlled-source-kind",
        selected_member="controlled-original-member",
    )
    native = member(annotations.semantic_id, "controlled-native-kind")
    symbolic = member(construction.semantic_id, "controlled-construction-kind")
    population = ResolvedRoleBinding(
        "sources",
        "present",
        (primary,),
        population_witness=canonical_bytes(
            dict(
                identity="unadmitted:complete-selected-population",
                complete=True,
                members=[primary.member],
                evidence={"controlled": "pure-input"},
            )
        ),
    )
    profile = PreparedM1Inputs(
        prepared,
        model,
        configuration(),
        primary,
        native,
        symbolic,
        population,
        context.project_id,
        lambda: None,
    )
    return profile, source, value, construction, context


@pytest.mark.parametrize(
    "detached,expected",
    [
        (NEGATIVE, {"polarity": "negative", "modality": "asserted"}),
        (POSSIBLE, {"polarity": "positive", "modality": "possible"}),
        (SHARED_NEGATION, None),
    ],
    indirect=["detached"],
)
def test_current_m1_passes_selected_primary_meaning_to_exact_assertion_qualification(
    selected_inputs, monkeypatch, expected
):
    profile, source, annotations, construction, _context = selected_inputs
    inspected = []

    def inspect(**inputs):
        frame = inputs["prepared_source"].source
        products = inputs["prepared_source"].annotations
        assert products and all(not hasattr(product, "primary_layers") for product in products)
        readings = inputs["primary_products"]
        assert [product.semantic_id for product in readings] == [construction.semantic_id]
        context = NativeSourceContext(
            frame,
            (),
            (source_slice(frame, 0, len(frame.text)),),
            "controlled assertion question",
            "pure",
            "exact selected source",
            version=2,
            preparation=PreparedNativeSources((frame,)),
        )
        group = {}
        for role, literal in (
            ("subject", "The pumps"),
            ("predicate", "drain"),
            ("object", "the tanks"),
        ):
            start = frame.text.index(literal)
            group[role] = dict(start=start, end=start + len(literal), text=literal)
        pack = configured_packs(profile.prepared, profile.configuration)["assertion"]
        qualification = AssertionQualification(
            frame,
            products,
            inputs["view"].pieces,
            inputs["view"].items,
            primary_products=readings,
        ).supplement(context, pack, report(context, pack, "assertion", [group]), group)
        if expected is None:
            from corpus_structure.methods.predicate_frames import predicate_frames

            result = predicate_frames(frame.text, products, primary_products=readings)
            assert not result.issues
            assert {value.polarity for value in result.frames} == {"negative_scope_unresolved"}
            assert qualification is None
            inspected.append(True)
            yield from ()
            return M1CandidateProduct(ObservationOutcome.EMPTY)
        assert qualification is not None
        assert {field.role: field.label for field in qualification.fields} == expected
        cues = {field.role: tuple(cue.text for cue in field.cues) for field in qualification.fields}
        assert cues["polarity"] == (
            ("not",) if expected["polarity"] == "negative" else (frame.text[:-1],)
        )
        if expected["modality"] == "possible":
            assert cues["modality"] == ("might",)
        inspected.append(True)
        yield from ()
        return M1CandidateProduct(ObservationOutcome.EMPTY)

    monkeypatch.setattr("corpus_structure.semantic.m1_products.plan_candidate_replies", inspect)
    with pytest.raises(StopIteration):
        next(
            profile.run(
                source.value,
                annotations,
                construction.value.model_dump(mode="json", exclude_unset=True),
                (source.value,),
            )
        )
    assert inspected == [True]


@pytest.mark.parametrize("detached", [NEGATIVE], indirect=True)
@pytest.mark.parametrize("change", ["product", "member", "source"])
def test_current_m1_refuses_changed_or_unselected_primary_before_provider(
    selected_inputs, monkeypatch, change
):
    profile, source, annotations, construction, context = selected_inputs
    body = construction.value.model_dump(mode="json", exclude_unset=True)
    if change == "product":
        profile = replace(
            profile,
            construction_member=replace(profile.construction_member, product="unselected-product"),
        )
    elif change == "member":
        profile = replace(
            profile,
            construction_member=replace(profile.construction_member, member="not-a-whole-product"),
        )
    else:
        body["source"]["document"] = "other-original"
        kind = next(
            identity.key
            for identity in profile.model.identities
            if identity.owner
            == profile.prepared.index.definitions["DdoPrimaryConstructionProduct"].iri
            and identity.domain == "kind"
        )
        altered = contextual_product_identity(
            kind=kind, context=context, body=body_identity(body).key
        ).key
        profile = replace(
            profile, construction_member=replace(profile.construction_member, product=altered)
        )
    monkeypatch.setattr(
        "corpus_structure.semantic.m1_products.plan_candidate_replies",
        lambda **_: pytest.fail("provider plan started for changed primary"),
    )
    with pytest.raises(
        ValueError, match=r"whole construction|selected native product|exact original source"
    ):
        next(profile.run(source.value, annotations, body, (source.value,)))


def test_current_annotation_fixture_uses_declared_source_and_separate_nominal_products(
    controlled, monkeypatch
):
    from corpus_structure.ingest import sentences
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods import source_preparation
    from methods.declared_primary_fixture import source_readings

    monkeypatch.setattr(sentences, "pipeline", lambda *_: controlled)
    monkeypatch.setattr(source_preparation, "pipeline", lambda *_: controlled)
    frame, annotations, primary, native = source_readings("X X.", AnnotationProfile())
    assert len(annotations) == len(primary) == 1
    assert annotations[0].source == frame.pin
    assert not hasattr(annotations[0], "primary_layers")
    assert [token.lemma for token in annotations[0].tokens] == ["lemma:0", "lemma:1"]
    assert native.value.model_dump(mode="json", exclude_unset=True)["source"] == frame.value["source"]
    assert primary[0].value.model_dump(mode="json", exclude_unset=True)["source"] == frame.value["source"]
