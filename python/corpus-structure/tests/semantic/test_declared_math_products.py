"""Current math producer/consumer semantics without legacy execution admission."""

from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.methods.math.declared import DeclaredMathNormalization, DeclaredMathOccurrences
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_model import BoundRoleMember, ResolvedRoleBinding, SubjectContext
from corpus_structure.semantic.declared_math_products import (
    DeclaredMathOptions, DeclaredMathProduct, PreparedMathInputs,
    acquire_analysis_context_profile, math_operation_declarations, math_operation_sources,
)
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions, formal_operation_sources, formal_product_inputs, prepare_formal_evidence,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.source_products import source_subject
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from semantic.formal_products_support import selected


@pytest.fixture(scope="module")
def math_profile():
    from corpus_structure.semantic.formal_evidence import grammar_identity

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    captured = combine_primary_sources(formal_operation_sources(), math_operation_sources())
    dependencies = data_operation_dependencies(ResolvedDependencies(),
        (math_operation_declarations(),), captured)
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    model = bound_data_operation_model(prepared)
    return prepare_formal_evidence(prepared, model, grammar=grammar_identity())


def _inputs(profile):
    source = selected(profile, "  2+1", pieces=[
        dict(kind="synthetic_separator", start=0, end=2),
        dict(kind="native_text", start=2, end=5, item_ref="#/texts/0", source_field="text"),
    ], items=[dict(self_ref="#/texts/0", label="formula", text="2+1", orig="2+1")],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
        selectors=[dict(projection="b"*64, native_pointer="#/texts/0", start=2, end=5)])
    context = SubjectContext("outside-statistics", source_subject(source.value["source"]),
        source.value["source"]["document"], canonical_bytes({"selectors":source.value["selectors"]}))
    formal = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    source_member = BoundRoleMember("product:source", "kind:source", context.subject, context.original_source,
        context.analyzed_scope, b"{}", (), b"{}", member="selected")
    formal_member = replace(source_member, product=formal.semantic_id, member=None, kind_contract="kind:formal")
    return source, formal, source_member, formal_member


def _role(name, members):
    return ResolvedRoleBinding(name, "set" if name == "inherited" else "scalar", tuple(members))


def test_math_profiles_compile_without_a_legacy_execution_binding(math_profile):
    prepared = math_profile.prepared
    assert prepared.execution_model_id is None
    model = bound_data_operation_model(prepared)
    assert {"extract.math/declared", "normalize.formula/declared"} <= {op.semantic_id for op in model.operations}
    assert model.operation("normalize.formula/declared").roles[1].kind == "urn:corpus:math:DeclaredMathProduct"


def test_occurrence_and_normalization_consume_exact_retained_syntax(math_profile, monkeypatch):
    from corpus_structure.methods.math import grammar

    source, formal, source_member, formal_member = _inputs(math_profile)
    roles = (_role("source", (source_member,)), _role("formal", (formal_member,)), _role("inherited", ()), _role("ancestor_sources", ()))
    profile = PreparedMathInputs(math_profile.prepared, roles, "outside-statistics", DeclaredMathOptions(),
        acquire_analysis_context_profile(), lambda: None)
    def refuse_parse(*args, **kwargs):
        pytest.fail("a mathematical consumer reparsed retained primary syntax")
    monkeypatch.setattr(grammar, "syntax", refuse_parse)
    monkeypatch.setattr(grammar, "syntax_forest", refuse_parse)
    actual = DeclaredMathOccurrences(profile).run(source.value, formal.value.model_dump(mode="json", exclude_unset=True))
    product = DeclaredMathProduct.model_validate(actual)
    assert product.phase == "occurrences" and product.outcome == "complete"
    assert product.source.source_product == "product:source"
    assert product.items[0]["pointer"] == "#/texts/0"
    assert product.items[0]["recognized_latex"] == "2+1"
    assert product.items[0]["primary_input"]["product_id"] == formal.semantic_id
    occurrence_member = replace(formal_member, product="product:occurrences", kind_contract="kind:math")
    normalizer = replace(profile, roles=(_role("source", (source_member,)), _role("occurrences", (occurrence_member,))))
    result = DeclaredMathProduct.model_validate(DeclaredMathNormalization(normalizer).run(source.value, actual))
    assert result.phase == "symbolic"
    assert result.occurrence_input.product_id == "product:occurrences"
    assert result.items[0]["symbolic"] == {"format":"sympy-srepr-1", "expression":"Integer(3)"}
    changed = {**actual, "source":{**actual["source"], "membership":"direct"}}
    with pytest.raises(ValueError, match="exact selected source"):
        DeclaredMathNormalization(normalizer).run(source.value, changed)
    changed = {**actual, "items":[{**actual["items"][0], "occurrence_basis":"wrong"}]}
    with pytest.raises(ValueError, match="normalization context"):
        DeclaredMathNormalization(normalizer).run(source.value, changed)
