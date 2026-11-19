"""Actual current math/formal profiles and exact selected source-role inputs."""

from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.declared_math_products import (
    math_operation_declarations,
    math_operation_sources,
)
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.source_products import source_subject
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.formal_products_support import selected


@pytest.fixture(scope="module")
def math_profile(tmp_path_factory):
    from corpus_structure.semantic.formal_evidence import grammar_identity

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
    from corpus_structure.semantic.characterization_ports import characterization_operation_sources
    from corpus_structure.semantic.construction_products import construction_product_inputs

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
        tmp_path_factory.mktemp("math-sentence-custody"),
    )

    bundle = construction_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    captured = combine_primary_sources(
        formal_operation_sources(),
        math_operation_sources(),
        characterization_operation_sources(
            sentence_configuration=configuration, sentence_selection=selection
        ),
    )
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), (math_operation_declarations(),), captured
    )
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    model = bound_data_operation_model(prepared)
    return prepare_formal_evidence(prepared, model, grammar=grammar_identity())


def _inputs(profile, source=None):
    source = (
        source
        if source is not None
        else selected(
            profile,
            "  2+1",
            pieces=[
                dict(kind="synthetic_separator", start=0, end=2),
                dict(kind="native_text", start=2, end=5, item_ref="#/texts/0", source_field="text"),
            ],
            items=[dict(self_ref="#/texts/0", label="formula", text="2+1", orig="2+1")],
            recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
            selectors=[dict(projection="b" * 64, native_pointer="#/texts/0", start=2, end=5)],
        )
    )
    context = SubjectContext(
        "outside-statistics",
        source_subject(source.value["source"]),
        source.value["source"]["document"],
        canonical_bytes({"selectors": source.value["selectors"]}),
        subject_definition="original-source-view",
    )
    formal = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    source_member = BoundRoleMember(
        "product:source",
        "kind:source",
        context.subject,
        context.original_source,
        context.analyzed_scope,
        b"{}",
        (),
        b"{}",
        member="selected",
        subject_definition="original-source-view",
        support_references=(),
    )
    formal_member = replace(
        source_member, product=formal.semantic_id, member=None, kind_contract="kind:formal"
    )
    return source, formal, source_member, formal_member


def _role(name, members):
    return ResolvedRoleBinding(name, "present" if members else "known-absent", tuple(members))
