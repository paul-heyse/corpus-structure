"""Actual acquired family kernels on the shared managed CPU process owner."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

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
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
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
            {"files": {}},
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
    archived = replace(
        sources,
        sources=tuple(
            replace(source, filename=source.logical_filename) for source in sources.sources
        ),
    )
    base = python_port_identity(model, archived, operation, schema=bundle, prepared=prepared)
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
    from corpus_structure.methods.predicate_frames import (
        predicate_frames,
        prepare_predicate_readings,
    )
    from corpus_structure.semantic.construction_products import (
        CharacterizationSnapshot,
        PreparedConstructionProfile,
        load_construction_options,
    )
    from corpus_structure.semantic.constructions.declared_named import DeclaredNamedRules
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredRecordSource,
        DeclaredSourcePin,
    )
    from corpus_structure.semantic.sentence_products import (
        _blocks,
        _detach_annotation_block,
        retained_source_annotation_products,
        spacy_family_coverage,
    )
    from corpus_structure.semantic.structural_products import StructuralPassage
    from semantic.source_annotations_test_support import partition_controlled_annotations

    _, _, prepared, model, formal = acquired
    source = selected(formal, text)
    context = _publication_context(source)
    coordinate = source.value["source"]
    pin = DeclaredRecordSource(
        coordinate["document"],
        coordinate["projection"],
        coordinate["section_pointer"],
        coordinate["membership"],
        context,
        "unadmitted:source",
        None,
        "unadmitted:source-kind",
    )
    configuration = SentenceConfig(exclude=("ner",))
    nlp = spacy.blank("en")
    tokenized = nlp.make_doc(text)
    doc = Doc(
        nlp.vocab,
        words=[token.text for token in tokenized],
        spaces=[bool(token.whitespace_) for token in tokenized],
        heads=heads,
        deps=deps,
        pos=pos,
        lemmas=[token.text.lower() for token in tokenized],
        tags=["PRP", "VBP", "NN", "IN", "NN", "."],
        morphs=[
            "Case=Nom|Number=Plur|Person=1|PronType=Prs",
            "Tense=Pres|VerbForm=Fin",
            "Number=Sing",
            "",
            "Number=Sing",
            "PunctType=Peri",
        ],
    )
    (block,), coverage = _blocks(source)
    detached = _detach_annotation_block(
        source.value,
        block,
        prepare_layout(nlp, block.block, start=block.start),
        doc,
        DeclaredSourcePin(canonical_bytes(pin.pin()).decode()),
        configuration,
        "unadmitted:authored-parse-columns",
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
        source=coordinate,
        selectors=source.value["selectors"],
        outcome="complete",
        blocks=[detached],
        block_coverage=coverage,
        coverage=spacy_family_coverage(source.value, coverage, [columns]),
        configuration=configuration.model_dump(mode="json"),
        execution_profile="unadmitted:authored-parse-columns",
    )
    native = partition_controlled_annotations(
        prepared, model, annotations, source, subject_context=context
    )
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    options = load_construction_options(Path(__file__).resolve().parents[4] / "domains/statistics")
    construction = PreparedConstructionProfile(prepared, model).run(
        source,
        (primary,),
        options,
        sentences=native,
        subject_context=context,
    )
    snapshot = CharacterizationSnapshot(construction.semantic_id, construction.content)
    native_snapshot = CharacterizationSnapshot(
        native.semantic_id, native.content, native.partitions
    )
    (restored,) = retained_source_annotation_products(source, native_snapshot)
    result, refs, nominations, rule_ids = DeclaredNamedRules((snapshot,), native_snapshot).decode(
        restored
    )
    frames = predicate_frames(
        text, (restored,), primary_products=prepare_predicate_readings((snapshot,))
    )
    scopes = definition_scopes(result.matches, frames, content_role="defining_content")
    components = components_from_named_matches(
        StructuralPassage(
            passage_id="literal",
            source_ref="source",
            start=0,
            end=len(text),
            text=text,
            scope="literal",
        ),
        result.matches,
        scopes=scopes,
        term_role="defined_term",
        content_role="defining_content",
    )
    assert [(row.term.text, row.content.text) for row in components] == [(term, content)], (
        result.availability,
        len(result.matches),
        frames.issues,
        [(match.variant, scope.disposition) for match, scope in scopes.items()],
    )
    assert refs and all(
        reference.product_id == construction.semantic_id for reference in refs.values()
    )
    policy = json.loads(
        (
            Path(__file__).parents[2] / "src/corpus_structure/methods/model_observation.json"
        ).read_bytes()
    )["definition_witness"]
    for match in result.matches:
        assert (
            rule_ids[match.rule, match.variant]
            == "named-rule:" + policy["rules"][f"{match.rule}/{match.variant}"]
        )
        assert scopes[match].primary_scope
        # Active defining constructions do not nominate a passive demonstrative.
        assert nominations.get(match, {}).get("defining_content") is None


def test_acquired_construction_kernel_runs_real_parser_in_child_and_preserves_typed_packets(
    acquired,
    monkeypatch,
):
    from dataclasses import replace

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.sentence_products import (
        _blocks,
        _detach_annotation_block,
        spacy_family_coverage,
    )
    from semantic.source_annotations_test_support import partition_controlled_annotations

    _, _, prepared, model, formal = acquired
    source = selected(formal, "Not every trial succeeds.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    port = admitted(acquired, "text.constructions/source-native", resolve_construction_port)
    from corpus_structure.semantic.data_operation_ports import PortRefusal

    sentence_role = next(role for role in port.operation.roles if role.name == "sentences")
    assert set(sentence_role.required_rules) == {
        "segment.sentences/coverage-manifest",
        "segment.sentences/exact-source-scope",
        "segment.sentences/source-layout",
        "segment.sentences/token-sentence-membership",
        "segment.sentences/native-dense-ordinal",
        "segment.sentences/native-row-span",
        "segment.sentences/native-source-order",
    }
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
    native = partition_controlled_annotations(
        prepared, model, annotations, source, subject_context=_publication_context(source)
    )
    with pytest.raises(ValueError, match="selected collection commitment"):
        replace(native, partitions=())
    inputs = values(port, source=source.value, formal=(primary,), sentences=native)
    expected = port.invoke_python(inputs)
    from corpus_structure.semantic import data_operation_prepared_products as prepared_products

    checked = port._verification.check
    checks = []
    compilations = []

    def observed_check():
        checks.append(True)
        checked()

    def observed_compile(*args, **kwargs):
        compilations.append(args[1])
        return compile(*args, **kwargs)

    monkeypatch.setattr(port._verification, "check", observed_check)
    monkeypatch.setattr(prepared_products, "compile", observed_compile, raising=False)
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
        assert checks == [True, True]
        assert compilations == []
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


def test_interpreted_body_coverage_refuses_empty_family_with_analytical_members():
    from corpus_structure.semantic.construction_products import verify_interpreted_body_coverage

    coverage = [
        {
            "family": "sample.choice",
            "outcome": "complete",
            "availability": "available",
            "eligible": [{"start": 0, "end": 6}],
            "examined": [{"start": 0, "end": 6}],
        }
    ]
    inventory = {
        "annotations": [],
        "memberships": [],
        "roles": [],
        "terms": [],
        "choices": [{"family": "sample.choice"}],
    }
    verify_interpreted_body_coverage(coverage, "complete", inventory)
    coverage[0]["outcome"] = "empty"
    with pytest.raises(ValueError, match="successful empty family contains analytical output"):
        verify_interpreted_body_coverage(coverage, "complete", inventory)


def test_navigation_proof_requires_the_declared_block_and_exact_token():
    from corpus_structure.semantic.construction_products import (
        verify_interpreted_annotation_support,
    )

    node = {
        "local_id": "navigation",
        "navigation": {
            "block": "selected",
            "annotation": "annotation:layout-a",
            "native_tokens": [{"index": 1}],
        },
    }
    selected = ("selected", ("token", 1))
    other = ("other", ("token", 1))
    slot = ("navigation", "navigation_token", None)
    items = {selected, other}
    layouts = {"selected": "layout-a", "other": "layout-b"}
    graph = {"navigation": node}
    verify_interpreted_annotation_support({slot: ((0, selected),)}, items, layouts, [node], graph)
    with pytest.raises(ValueError, match="native token layout"):
        verify_interpreted_annotation_support({slot: ((0, other),)}, items, layouts, [node], graph)
    with pytest.raises(ValueError, match="exact original native block"):
        verify_interpreted_annotation_support(
            {slot: ((0, selected),)}, items, {"selected": "layout-b"}, [node], graph
        )


def test_interpreted_completions_attest_body_coverage_and_exact_source(acquired, monkeypatch):
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic import construction_products
    from corpus_structure.semantic.characterization_ports import (
        _ConstructionInputs,
        _ContextualInputs,
    )
    from corpus_structure.semantic.construction_products import (
        PreparedConstructionProfile,
        PreparedContextualProfile,
        verify_interpreted_literal_source,
        verify_interpreted_positioned_geometry,
        verify_interpreted_source_coverage,
    )
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.data_operation_partitions import partition_header
    from corpus_structure.semantic.sentence_products import SourceAnnotations

    _, _, prepared, model, formal = acquired
    source = selected(formal, "All samples are finite.")
    context = _publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    construction = PreparedConstructionProfile(prepared, model).run(
        source, (primary,), subject_context=context
    )
    contextual = PreparedContextualProfile(prepared, model).run(
        source, (construction,), (primary,), subject_context=context
    )
    # A nominal empty row envelope isolates the completion's premise projection.
    annotation = SourceAnnotations(
        canonical_bytes(
            {
                "source": source.value["source"],
                "selectors": source.value["selectors"],
                "execution_profile": "selected",
                "configuration": SentenceConfig(exclude=("ner",)).model_dump(mode="json"),
                "outcome": "partial",
                "block_coverage": [],
                "coverage": [],
                "block_layouts": [],
                "members": [],
                "rows": partition_header(()),
            }
        ),
        prepared,
        model,
        (),
        subject_context=context,
    )

    def binding(**roles):
        return SimpleNamespace(
            subject_context=context,
            roles=tuple(
                SimpleNamespace(
                    role=name,
                    members=tuple(
                        SimpleNamespace(product=item.semantic_id, multiplicity=1) for item in items
                    ),
                )
                for name, items in roles.items()
            ),
        )

    for operation, resolver, product, required, inputs, selection in (
        (
            "text.constructions/source-native",
            resolve_construction_port,
            construction,
            "text.constructions/literal-source",
            _ConstructionInputs(source, (primary,), annotation),
            binding(formal=(primary,), sentences=(annotation,)),
        ),
        (
            "text.contextual_evaluation/source-native",
            resolve_contextual_port,
            contextual,
            "text.contextual_evaluation/literal-source",
            _ContextualInputs(source, (primary,), (construction,)),
            binding(formal=(primary,), constructions=(construction,), supporting=()),
        ),
    ):
        port = admitted(acquired, operation, resolver)
        result = port._completion(product, selection, inputs=inputs)
        proofs = {proof.rule_id: proof for proof in result.rule_attestations}
        prefix = operation.partition("/")[0]
        coverage_rule = prefix + "/body-coverage"
        selected_rule = prefix + "/selected-source-coverage"
        geometry_rule = prefix + "/positioned-source-geometry"
        topology_rule = prefix + "/inventory-topology"
        numeric_rule = prefix + "/native-numeric-scores"
        address_rule = prefix + "/canonical-occurrence-addresses"
        members_rule = prefix + "/selected-primary-members"
        attachment_rule = prefix + "/released-attachment-witnesses"
        expected = {
            required,
            coverage_rule,
            selected_rule,
            geometry_rule,
            topology_rule,
            numeric_rule,
            address_rule,
            members_rule,
            attachment_rule,
        }
        if isinstance(inputs, _ConstructionInputs):
            expected.add("text.constructions/navigation-source-fields")
            expected.add("text.constructions/selected-annotation-support")
        assert set(proofs) == expected
        assert all(proof.output_role == "result" for proof in proofs.values())
        assert all(proof.output_position == 0 for proof in proofs.values())

        changed = port._completion(
            product,
            selection,
            inputs=replace(inputs, source=selected(formal, "No sample is finite.")),
        )
        changed_proofs = {proof.rule_id: proof for proof in changed.rule_attestations}
        assert changed_proofs[coverage_rule].premise == proofs[coverage_rule].premise
        assert changed_proofs[required].premise != proofs[required].premise
        assert changed_proofs[selected_rule].premise != proofs[selected_rule].premise
        assert changed_proofs[geometry_rule].premise != proofs[geometry_rule].premise
        assert changed_proofs[topology_rule].premise == proofs[topology_rule].premise
        assert changed_proofs[numeric_rule].premise == proofs[numeric_rule].premise
        assert changed_proofs[address_rule].premise == proofs[address_rule].premise
        assert changed_proofs[members_rule].premise == proofs[members_rule].premise
        if isinstance(inputs, _ConstructionInputs):
            navigation_rule = "text.constructions/navigation-source-fields"
            assert changed_proofs[navigation_rule].premise == proofs[navigation_rule].premise

    consumer = model.operation("text.contextual_evaluation/source-native")
    (annotation_rule,) = (
        rule for rule in model.rules if rule.id == "text.constructions/selected-annotation-support"
    )
    assert json.loads(annotation_rule.parameters)["input_reads"] == {
        "sentences": ["block_layouts", "rows"]
    }
    (formal_role,) = (role for role in consumer.roles if role.name == "formal")
    assert "text.formal_evidence/canonical-occurrence-addresses" in formal_role.required_rules
    (role,) = (role for role in consumer.roles if role.name == "constructions")
    assert role.required_rules == (
        "text.constructions/body-coverage",
        "text.constructions/canonical-occurrence-addresses",
        "text.constructions/inventory-topology",
        "text.constructions/literal-source",
        "text.constructions/native-numeric-scores",
        "text.constructions/navigation-source-fields",
        "text.constructions/positioned-source-geometry",
        "text.constructions/released-attachment-witnesses",
        "text.constructions/selected-annotation-support",
        "text.constructions/selected-primary-members",
        "text.constructions/selected-source-coverage",
    )
    targets = model.operation("text.constructions/source-native").reference_targets
    reference_target = next(target for target in targets if target.input_role == "sentences")
    assert (reference_target.path, reference_target.input_role, reference_target.collection) == (
        "/annotation_support/*/target",
        "sentences",
        "rows",
    )
    formal_target = next(target for target in targets if target.input_role == "formal")
    assert formal_target.path == "/formal_support/*/target"
    assert formal_target.occurrence_position
    assert {(target.input_role, target.variant) for target in consumer.reference_targets} == {
        (role, variant)
        for role in ("formal", "constructions", "supporting")
        for variant in ("member", "product")
    }
    assert all(target.occurrence_position for target in consumer.reference_targets)
    assert all(
        role.collection == "set"
        for role in consumer.roles
        if role.name in {"formal", "constructions", "supporting"}
    )
    product = {
        "source": source.value["source"],
        "selectors": source.value["selectors"],
        "members": [
            {
                "body": {
                    "record_type": "occurrence",
                    "extents": [{"start": 0, "end": 3, "text": "All"}],
                }
            }
        ],
    }
    verify_interpreted_literal_source(product, source.value)
    with pytest.raises(ValueError, match="changes original positioned source"):
        verify_interpreted_literal_source(
            product, {**source.value, "text": "Few samples are finite."}
        )

    covered = {
        "outcome": "complete",
        "eligible": source.value["selectors"],
        "examined": source.value["selectors"],
    }
    verify_interpreted_source_coverage((covered,), source.value)
    with pytest.raises(ValueError, match="leaves eligible source scope unexamined"):
        verify_interpreted_source_coverage(({**covered, "examined": ()},), source.value)

    extent = {
        "projection": source.value["source"]["projection"],
        "native_pointer": "#/texts/0",
        "start": 0,
        "end": 3,
        "text": "All",
        "synthetic": False,
    }
    packet = {"body": {"record_type": "occurrence", "extents": [extent]}}
    verify_interpreted_positioned_geometry((packet,), source.value)
    extent["synthetic"] = True
    with pytest.raises(ValueError, match="changes original positioned source"):
        verify_interpreted_positioned_geometry((packet,), source.value)

    member = BoundRoleMember(
        product=construction.semantic_id,
        kind_contract=next(
            item.key
            for item in model.identities
            if item.owner == prepared.index.definitions[construction.kind_name].iri
            and item.domain == "kind"
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
    payload = construction.value

    def repeated(*args, **kwargs):
        pytest.fail("selected construction repeated an established source or coverage rule")

    for checker in (
        "verify_interpreted_literal_source",
        "verify_interpreted_positioned_geometry",
        "verify_interpreted_body_coverage",
        "verify_interpreted_inventory_topology",
        "verify_interpreted_source_coverage",
        "verify_inventory_native_scores",
        "verify_inventory_occurrence_ids",
        "verify_interpreted_attachment_witnesses",
        "validate_attachment_basis",
        "verify_interpreted_dependency_members",
        "verify_interpreted_annotation_support",
    ):
        monkeypatch.setattr(construction_products, checker, repeated)
    selected_product = construction_products.acquired_construction_product(
        prepared, model, payload, source, (primary,), subject_context=context, member=member
    )
    assert selected_product.semantic_id == construction.semantic_id
    with pytest.raises(ValueError, match="exact selected native product/source"):
        construction_products.acquired_construction_product(
            prepared,
            model,
            payload,
            selected(formal, "No sample is finite."),
            (primary,),
            subject_context=context,
            member=member,
        )


def test_primary_support_preserves_formal_premises_and_checks_exact_annotation_addresses():
    from corpus_structure.semantic.construction_products import (
        _stage_construction_support,
        annotation_support_index,
        verify_interpreted_annotation_support,
    )
    from corpus_structure.semantic.data_product_reference import SemanticReference

    formal = {"product_id": "formal", "member_id": "literal"}
    token = SemanticReference.item("sentences", "rows", "block", ("token", 0))
    sentence = SemanticReference.item("sentences", "rows", "block", ("sentence", 0))
    term = {"local_id": "term", "external_premises": [formal, token.values(), sentence.values()]}
    facts = {
        "occurrences": [],
        "annotations": [],
        "memberships": [],
        "roles": [],
        "choices": [],
        "terms": [term],
    }
    annotation_support, formal_support = _stage_construction_support(
        facts, (SimpleNamespace(semantic_id="formal"),)
    )
    links = {"annotation_support": annotation_support, "formal_support": formal_support}
    assert term["external_premises"] == []
    assert formal_support == [
        {
            "owner": "term",
            "use": "external_premise",
            "position": 0,
            "target": {
                "variant": "member",
                "role": "formal",
                "occurrence": "0",
                "member_id": "literal",
            },
        }
    ]
    from corpus_structure.semantic.construction_formal_references import (
        project_construction_formal_support,
    )

    projected = project_construction_formal_support(
        {**links, "members": [{"member_id": "term", "body": term}]}, (("0", "formal"),)
    )
    term = projected["members"][0]["body"]
    assert term["external_premises"] == [formal]
    assert annotation_support_index(links)["term", "external_premise", None] == (
        (1, token),
        (2, sentence),
    )

    support = {
        ("term", "external_premise", None): (
            (1, ("block", ("token", 0))),
            (2, ("block", ("sentence", 0))),
        )
    }
    addresses = {("block", ("sentence", 0)), ("block", ("token", 0))}
    verify_interpreted_annotation_support(support, addresses, {}, (), {"term": term})
    with pytest.raises(ValueError, match="exact graph/item address"):
        verify_interpreted_annotation_support(support, addresses, {}, (), {})


def test_retained_family_ingress_uses_selected_member_context_and_checks_native_id(acquired):
    from corpus_structure.semantic.data_operation_model import BoundRoleMember

    _, _, _, _, formal = acquired
    source = selected(formal, "All samples are finite.")
    context = _publication_context(source)
    original = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    port = admitted(acquired, "text.constructions/source-native", resolve_construction_port)
    formal_role = next(role for role in port.operation.roles if role.name == "formal")
    member = BoundRoleMember(
        product=original.semantic_id,
        kind_contract=next(
            item.key
            for item in port.model.identities
            if item.owner == formal_role.kind and item.domain == "kind"
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
    binding = SimpleNamespace(
        subject_context=context, roles=(SimpleNamespace(role="formal", members=(member,)),)
    )
    unbound = original.with_context(None)
    (restored,) = port._formal(source, (unbound,), binding)
    assert restored.content == original.content
    assert restored.subject_context == context
    assert restored.semantic_id == member.product
    other_project = SimpleNamespace(
        subject_context=replace(context, project_id="another-project"), roles=binding.roles
    )
    with pytest.raises(ValueError, match="exact selected native product/source"):
        port._formal(source, (unbound,), other_project)
