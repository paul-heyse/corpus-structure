"""Actual acquired family kernels on the shared managed CPU process owner."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization_ports import (
    construction_operation_sources,
    contextual_operation_sources,
    resolve_construction_port,
    resolve_contextual_port,
)
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import construction_product_inputs
from corpus_structure.semantic.contextual_operations import contextual_operation_declarations
from corpus_structure.semantic.data_operation_admission import (
    PreparedCapabilityIdentity,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_ports import PythonRoleValue, python_port_identity
from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from semantic.formal_products_support import selected


@pytest.fixture(scope="module")
def acquired(tmp_path_factory):
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

    configuration = SentenceConfig(exclude=("ner",))
    selection = NativeSelection(
        NativeProfile(
            "spacy",
            {"controlled": "unadmitted-schema"},
            {},
            configuration.model_dump(mode="json"),
            "float32",
            "cupy",
            4,
            1,
        ),
        tmp_path_factory.mktemp("controlled-sentence-custody"),
    )
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = construction_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    collections = (
        formal_operation_sources(),
        construction_operation_sources(
            sentence_configuration=configuration, sentence_selection=selection
        ),
        contextual_operation_sources(include_dependencies=False),
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources

    sources = combine_primary_sources(*collections)
    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(),
            declarations=(
                contextual_operation_declarations(),
                structural_operation_declarations(),
            ),
            python_sources=sources,
        ),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    formal = prepare_formal_evidence(prepared, model, grammar=grammar_identity())
    return bundle, sources, prepared, model, formal


def admitted(acquired, operation, factory):
    bundle, sources, prepared, model, _ = acquired
    selected_op = model.operation(operation)
    base = python_port_identity(model, sources, operation, schema=bundle, prepared=prepared)
    boundaries = (
        *selected_op.assets,
        *(
            boundary
            for implementation in model.implementation_slices
            if implementation.root == selected_op.implementation_root
            for boundary in implementation.boundaries
        ),
    )
    identity = PreparedCapabilityIdentity(
        **asdict(base),
        runtime="controlled:family-source-custody",
        assets=canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )

    def authorize(actual):
        if actual != identity:
            raise ValueError("not the exact controlled acquired execution identity")

    return factory(
        prepared,
        model,
        operation,
        identity=identity,
        authorize=authorize,
        custody=sources.boundary_contracts,
        sources=sources,
    )


def values(port, **provided):
    contracts = {
        (identity.owner, identity.domain): identity.key for identity in port.model.identities
    }
    return tuple(
        PythonRoleValue(role.name, contracts[role.kind, "kind"], provided[role.name])
        for role in port.operation.roles
        if role.direction == "input" and role.name in provided
    )


@pytest.mark.parametrize(
    "text,heads,deps,pos,term,content",
    [
        (
            "We define variance as spread.",
            (1, 1, 1, 4, 1, 1),
            ("nsubj", "ROOT", "dobj", "mark", "advcl", "punct"),
            ("PRON", "VERB", "NOUN", "SCONJ", "NOUN", "PUNCT"),
            "variance",
            "spread",
        ),
        (
            "We define mass as inertia.",
            (1, 1, 1, 2, 3, 1),
            ("nsubj", "ROOT", "dobj", "prep", "pobj", "punct"),
            ("PRON", "VERB", "NOUN", "ADP", "NOUN", "PUNCT"),
            "mass",
            "inertia",
        ),
    ],
)
def test_named_attachment_variants_survive_the_actual_retained_producer_roundtrip(
    acquired, text, heads, deps, pos, term, content
):
    """Authored columns exercise current producers/readers, without provider standing."""
    import spacy
    from spacy.tokens import Doc

    from corpus_structure.ingest.sentences import SentenceConfig, prepare_layout
    from corpus_structure.methods.definition_applicability import (
        components_from_named_matches,
        definition_scopes,
    )
    from corpus_structure.methods.predicate_frames import predicate_frames, prepare_predicate_readings
    from corpus_structure.semantic.construction_products import (
        CharacterizationSnapshot,
        PreparedConstructionProfile,
        load_construction_options,
    )
    from corpus_structure.semantic.constructions.declared_named import DeclaredNamedRules
    from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource, DeclaredSourcePin
    from corpus_structure.semantic.sentence_products import (
        _blocks,
        _detach_annotation_block,
        retained_source_annotation_products,
        source_annotation_packets,
        spacy_family_coverage,
        validate_source_annotations,
    )
    from corpus_structure.semantic.structural_products import StructuralPassage

    _, _, prepared, model, formal = acquired
    source = selected(formal, text)
    context = _publication_context(source)
    coordinate = source.value["source"]
    pin = DeclaredRecordSource(
        coordinate["document"], coordinate["projection"], coordinate["section_pointer"],
        coordinate["membership"], context, "unadmitted:source", None, "unadmitted:source-kind",
    )
    configuration = SentenceConfig(exclude=("ner",))
    nlp = spacy.blank("en")
    tokenized = nlp.make_doc(text)
    doc = Doc(
        nlp.vocab, words=[token.text for token in tokenized],
        spaces=[bool(token.whitespace_) for token in tokenized],
        heads=heads, deps=deps, pos=pos,
        lemmas=[token.text.lower() for token in tokenized],
        tags=["PRP", "VBP", "NN", "IN", "NN", "."],
        morphs=["Case=Nom|Number=Plur|Person=1|PronType=Prs", "Tense=Pres|VerbForm=Fin",
                "Number=Sing", "", "Number=Sing", "PunctType=Peri"],
    )
    (block,), coverage = _blocks(source)
    detached = _detach_annotation_block(
        source.value, block, prepare_layout(nlp, block.block, start=block.start), doc,
        DeclaredSourcePin(canonical_bytes(pin.pin()).decode()), configuration,
        "unadmitted:authored-parse-columns",
    )
    columns = dict(block_id=block.block_id, start=block.start, end=block.end, attributes={
        row["attribute"]: row["status"] for row in detached["annotation"]["availability"]
    })
    annotations = dict(
        source=coordinate, selectors=source.value["selectors"], outcome="complete",
        blocks=[detached], block_coverage=coverage,
        coverage=spacy_family_coverage(source.value, coverage, [columns]),
        configuration=configuration.model_dump(mode="json"),
        execution_profile="unadmitted:authored-parse-columns",
    )
    annotations["members"] = source_annotation_packets(prepared, model, annotations)
    native = validate_source_annotations(prepared, model, annotations, source, subject_context=context)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    options = load_construction_options(Path(__file__).resolve().parents[4] / "domains/statistics")
    construction = PreparedConstructionProfile(prepared, model).run(
        source, (primary,), options, sentences=native, subject_context=context,
    )
    snapshot = CharacterizationSnapshot(construction.semantic_id, construction.content)
    native_snapshot = CharacterizationSnapshot(native.semantic_id, native.content)
    (restored,) = retained_source_annotation_products(source, native_snapshot)
    result, refs, nominations, rule_ids = DeclaredNamedRules((snapshot,), native_snapshot).decode(restored)
    frames = predicate_frames(text, (restored,), primary_products=prepare_predicate_readings((snapshot,)))
    scopes = definition_scopes(result.matches, frames, content_role="defining_content")
    components = components_from_named_matches(
        StructuralPassage(passage_id="literal", source_ref="source", start=0, end=len(text),
                          text=text, scope="literal"),
        result.matches, scopes=scopes, term_role="defined_term", content_role="defining_content",
    )
    assert [(row.term.text, row.content.text) for row in components] == [(term, content)], (
        result.availability,
        len(result.matches),
        frames.issues,
        [(match.variant, scope.disposition) for match, scope in scopes.items()],
    )
    assert refs and all(reference.product_id == construction.semantic_id for reference in refs.values())
    policy = json.loads(
        (Path(__file__).parents[2] / "src/corpus_structure/methods/model_observation.json").read_bytes()
    )["definition_witness"]
    for match in result.matches:
        assert rule_ids[match.rule, match.variant] == "named-rule:" + policy["rules"][
            f"{match.rule}/{match.variant}"
        ]
        assert scopes[match].primary_scope
        # Active defining constructions do not nominate a passive demonstrative.
        assert nominations.get(match, {}).get("defining_content") is None


def test_acquired_construction_kernel_runs_real_parser_in_child_and_preserves_typed_packets(
    acquired,
    monkeypatch,
):
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.semantic.sentence_products import (
        _blocks,
        _detach_annotation_block,
        source_annotation_packets,
        spacy_family_coverage,
        validate_source_annotations,
    )

    _, _, prepared, model, formal = acquired
    source = selected(formal, "Not every trial succeeds.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    port = admitted(acquired, "text.constructions/source-native", resolve_construction_port)
    from corpus_structure.semantic.data_operation_ports import PortRefusal

    with pytest.raises(PortRefusal, match="omits a required typed role"):
        port.invoke_python(values(port, source=source.value, formal=(primary,)))
    # Controlled lexical/sentence columns let the real grammar consume original
    # token positions. Missing learned columns remain partial, without provider authority.
    import spacy

    from corpus_structure.ingest import annotations as annotation_owner
    from corpus_structure.ingest.sentences import make_doc, prepare_layout
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredRecordSource,
        DeclaredSourcePin,
    )

    nlp = spacy.blank("en")
    monkeypatch.setattr(annotation_owner, "pipeline", lambda *_: nlp)
    configuration = SentenceConfig(exclude=("ner",))
    coordinate = source.value["source"]
    pin = DeclaredRecordSource(
        coordinate["document"],
        coordinate["projection"],
        coordinate["section_pointer"],
        coordinate["membership"],
        _publication_context(source),
        "unadmitted:source",
        None,
        "unadmitted:source-kind",
    )
    (block,), coverage = _blocks(source)
    layout = prepare_layout(nlp, block.block, start=block.start)
    doc = make_doc(nlp, block.block, layout, start=block.start)
    for index, token in enumerate(doc):
        token.is_sent_start = index == 0
    detached = _detach_annotation_block(
        source.value,
        block,
        layout,
        doc,
        DeclaredSourcePin(canonical_bytes(pin.pin()).decode()),
        configuration,
        "unadmitted:controlled-lexical-columns",
    )
    columns = dict(
        block_id=block.block_id,
        start=block.start,
        end=block.end,
        attributes={
            row["attribute"]: row["status"] for row in detached["annotation"]["availability"]
        },
    )
    annotations = dict(
        source=source.value["source"],
        selectors=source.value["selectors"],
        outcome="partial",
        blocks=[detached],
        block_coverage=coverage,
        coverage=spacy_family_coverage(source.value, coverage, [columns]),
        configuration=configuration.model_dump(mode="json"),
        execution_profile="unadmitted:controlled-lexical-columns",
    )
    annotations["members"] = source_annotation_packets(prepared, model, annotations)
    native = validate_source_annotations(
        prepared, model, annotations, source, subject_context=_publication_context(source)
    )
    inputs = values(port, source=source.value, formal=(primary,), sentences=native)
    expected = port.invoke_python(inputs)
    cpu = CPUExecutionScope(
        prepared,
        CharacterizationExecutionPolicy(
            workers=1, max_submissions=1, max_packet_bytes=8 * 1024**2, max_reply_bytes=8 * 1024**2
        ),
        retain_schema=False,
    )
    try:
        actual = drive_prepared_work(
            port.plan_python(inputs, execution_owner=SimpleNamespace(cpu=cpu, reservation=None)),
            lambda: None,
        )
        assert actual.outputs[0].content == expected.outputs[0].content
        body = decode_semantic_value(json.loads(actual.outputs[0].meaning))
        assert body["outcome"] == "partial"
        assert any(packet["body"].get("kind") == "binder" for packet in body["members"])
        receipt = json.loads(actual.cpu_execution_evidence)
        assert receipt["pid"] != os.getpid() and receipt["main_thread"] is True
        assert receipt["native_thread_limit"] == 1
        assert len(actual.outputs[0].members) == len(body["members"])
        assert cpu._capsule_bytes == 0
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_actual_contextual_kernel_uses_same_retained_symbols_and_no_schema_capsule(acquired):
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.construction_products import PreparedConstructionProfile
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope

    _, _, prepared, model, formal = acquired
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    symbolic = PreparedConstructionProfile(prepared, model).run(
        source, (primary,), subject_context=_publication_context(source)
    )
    port = admitted(acquired, "text.contextual_evaluation/source-native", resolve_contextual_port)
    inputs = values(port, source=source.value, formal=(primary,), constructions=(symbolic,))
    expected = port.invoke_python(inputs)
    cpu = CPUExecutionScope(
        prepared,
        CharacterizationExecutionPolicy(
            workers=1, max_submissions=1, max_packet_bytes=8 * 1024**2, max_reply_bytes=8 * 1024**2
        ),
        retain_schema=False,
    )
    try:
        actual = drive_prepared_work(
            port.plan_python(inputs, execution_owner=SimpleNamespace(cpu=cpu, reservation=None)),
            lambda: None,
        )
        assert actual.outputs[0].content == expected.outputs[0].content
        assert json.loads(actual.cpu_execution_evidence)["pid"] != os.getpid()
        assert cpu._capsule_bytes == 0
    finally:
        cpu.close()


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
        subject_definition="original-source-view",
    )


def test_retained_family_ingress_uses_selected_member_context_and_checks_native_id(acquired):
    from dataclasses import replace
    from types import SimpleNamespace

    from corpus_structure.semantic.data_operation_ports import PortRefusal

    _, _, _, _, formal = acquired
    source = selected(formal, "All samples are finite.")
    context = _publication_context(source)
    original = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    port = admitted(acquired, "text.constructions/source-native", resolve_construction_port)
    member = SimpleNamespace(
        product=original.semantic_id,
        subject=context.subject,
        subject_definition=context.subject_definition,
        original_source=context.original_source,
        analyzed_scope=context.analyzed_scope,
        member=None,
        multiplicity=1,
    )
    binding = SimpleNamespace(
        subject_context=context, roles=(SimpleNamespace(role="formal", members=(member,)),)
    )
    unbound = replace(original, subject_context=None)
    restored = port._selected_product(unbound, binding, "formal", 0)
    assert restored.content == original.content
    assert restored.subject_context == context
    assert restored.semantic_id == member.product
    other_project = SimpleNamespace(
        subject_context=replace(context, project_id="another-project"), roles=binding.roles
    )
    with pytest.raises(PortRefusal, match="selected native product identity"):
        port._selected_product(unbound, other_project, "formal", 0)
