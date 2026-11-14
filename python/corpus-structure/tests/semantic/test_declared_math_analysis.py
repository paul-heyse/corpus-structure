"""Finite target math requests: genuine retained syntax, weak dependencies and failures."""

from types import SimpleNamespace

import pytest

from corpus_structure.semantic.analysis_contracts import acquire_analysis_context_profile
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_math_analysis import analyze_declared_math
from corpus_structure.semantic.declared_math_products import DeclaredMathOptions
from semantic.test_declared_math_products import _inputs, _role
from semantic.test_declared_math_products import math_profile as math_profile


def arguments(source, formal, demand="lexical"):
    return dict(source=source.value, formal=formal.value.model_dump(mode="json", exclude_unset=True), demand=demand, pointer="", question="", predicate="", seconds=2.0)


def test_weak_analysis_never_loads_ancestors_reparses_or_performs_symbolic_work(math_profile, monkeypatch):
    from corpus_structure.methods.math import grammar
    from corpus_structure.methods.math.prepared import PreparedMathInput

    source, formal, source_member, formal_member = _inputs(math_profile)
    def refused(*args, **kwargs):
        pytest.fail("weak analysis attempted stronger or repeated work")
    monkeypatch.setattr(grammar, "syntax", refused)
    monkeypatch.setattr(grammar, "syntax_forest", refused)
    monkeypatch.setattr(PreparedMathInput, "symbolic_value", refused)
    monkeypatch.setattr("corpus_structure.semantic.declared_math_analysis.inherited_analysis_declarations", refused)
    context = SubjectContext("outside-statistics", source_member.subject, source_member.original_source, source_member.analyzed_scope)
    result = analyze_declared_math(math_profile.prepared, (_role("source", (source_member,)), _role("formal", (formal_member,))), context, DeclaredMathOptions(), acquire_analysis_context_profile(), arguments(source, formal), check_active=lambda: None)
    assert result["source"]["source_product"] == source_member.product
    assert result["source"]["source_member"] == source_member.member
    assert result["formal_input"]["product_id"] == formal.semantic_id
    assert result["outcome"] == "complete"
    (item,) = result["items"]
    assert item["pointer"] == "#/texts/0" and item["recognized_latex"] == "2+1"
    assert item["lexical"] and "symbolic" not in item and "assessment" not in item
    assert item["context"]["declarations"] == []
    assert item["primary_input"]["product_id"] == formal.semantic_id


def test_analysis_refuses_widening_and_unqualified_scientific_questions(math_profile):
    source, formal, source_member, formal_member = _inputs(math_profile)
    roles = (_role("source", (source_member,)), _role("formal", (formal_member,)))
    context = SubjectContext("outside-statistics", source_member.subject, source_member.original_source, source_member.analyzed_scope)
    for changed in ({"pointer": "#/texts/foreign"}, {"demand": "scientific"}, {"seconds": float("nan")}, {"seconds": 0}):
        with pytest.raises(ValueError):
            analyze_declared_math(math_profile.prepared, roles, context, DeclaredMathOptions(), acquire_analysis_context_profile(), {**arguments(source, formal), **changed}, check_active=lambda: None)


def test_timeout_is_failed_even_when_a_partial_math_payload_is_available():
    from corpus_structure.methods.math.native import analysis_failure

    item = {"availability": "available", "failure": {"category": "timeout"}, "stages": {"syntax": {"work": "failed", "coverage": "partial"}}}
    for _ in range(2):
        assert analysis_failure(SimpleNamespace(items=(item,))) == "native mathematical request exceeded its budget"


def test_current_source_view_mutation_refuses_math_before_any_database_access():
    from corpus_structure.semantic.native_requests import request_source_view

    with pytest.raises(ValueError, match="NativeDemandRequest"):
        request_source_view(object(), source_run_id=1, source_view_id=2, demand="lexical", code_commit="no-legacy-execution")


def test_context_reads_exact_retained_parent_function_and_variable_with_native_order(math_profile):
    from dataclasses import replace
    import json
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_math_analysis import inherited_analysis_declarations
    from corpus_structure.semantic.declared_math_products import DeclaredMathScopeProduct
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import source_subject
    from corpus_structure.semantic.structural_products import DeclaredStructuralInputPin
    from semantic.formal_products_support import selected

    root = {"self_ref": "#/groups/0", "label": "section_header", "children": [{"$ref": "#/texts/0"}, {"$ref": "#/groups/1"}]}
    parent = selected(math_profile, "f(x)=x", items=[{"self_ref": "#/texts/0", "label": "formula", "text": "f(x)=x", "orig": "f(x)=x", "parent": {"$ref": "#/groups/0"}}], ancestors=[root])
    child = selected(math_profile, "f(x)", source={**parent.value["source"], "section_pointer": "#/groups/1"}, items=[{"self_ref": "#/texts/1", "label": "formula", "text": "f(x)", "orig": "f(x)", "parent": {"$ref": "#/groups/1"}}], pieces=[{"kind": "native_text", "start": 0, "end": 4, "item_ref": "#/texts/1", "source_field": "text"}], selectors=[{"projection": "b" * 64, "native_pointer": "#/texts/1", "start": 0, "end": 4}], ancestors=[root, {"self_ref": "#/groups/1", "label": "section_header", "parent": {"$ref": "#/groups/0"}}])
    def bind(source, product):
        return BoundRoleMember(product, "kind:source", source_subject(source.value["source"]), source.value["source"]["document"], canonical_bytes({"source": source.value["source"], "selectors": source.value["selectors"]}), b"{}", (), b"{}")
    parent_pin, child_pin = bind(parent, "parent-source"), bind(child, "child-source")
    parent_frame = DeclaredNativeFrameSource.acquire(math_profile.prepared, parent.value, parent_pin, project="p")
    child_frame = DeclaredNativeFrameSource.acquire(math_profile.prepared, child.value, child_pin, project="p")
    source = DeclaredStructuralSource.model_validate(parent_frame.pin.values())
    premise = DeclaredStructuralInputPin.from_bound(parent_pin, project="p")
    product = DeclaredMathScopeProduct(source=source, occurrence_input=premise, symbolic_input=premise, construction_input=premise, source_declarations=({"symbol": "f", "role": "function", "pointer": "#/texts/0", "scope": parent_frame.source_key + ":section:#/groups/0", "recognized_start": 0},), items=({"symbol": "x", "outcome": "resolved", "binding_pointer": "#/texts/0", "binding_start": 2, "binding_source": source.model_dump(mode="json"), "scope_pointer": "#/groups/0"},), outcome="complete")
    scope_member = replace(parent_pin, product="actual-parent-scope", kind_contract="kind:scope")
    declarations, issues = inherited_analysis_declarations(child_frame, (product.model_dump(mode="json"),), (scope_member,), (parent.value,), (parent_pin,), prepared=math_profile.prepared, project="p")
    assert {(row["symbol"], row["role"]) for row in declarations} == {("f", "function"), ("x", "variable")}
    assert all(json.loads(row["evidence"])["preparation_input"] == "actual-parent-scope" for row in declarations)
    assert all(json.loads(row["evidence"])["before_descendant"] is True for row in declarations)
    assert issues == ()
    absent, missing = inherited_analysis_declarations(child_frame, (), (), (), (), prepared=math_profile.prepared, project="p")
    assert absent == () and missing == ("unavailable ancestor mathematical context: #/groups/0",)
    partial = {**product.model_dump(mode="json"), "outcome": "partial"}
    _, incomplete = inherited_analysis_declarations(child_frame, (partial,), (scope_member,), (parent.value,), (parent_pin,), prepared=math_profile.prepared, project="p")
    assert incomplete == ("partial ancestor mathematical context: #/groups/0",)
    wrong = {**product.model_dump(mode="json"), "source": {**source.model_dump(mode="json"), "source_product": "foreign"}}
    with pytest.raises(ValueError):
        inherited_analysis_declarations(child_frame, (wrong,), (scope_member,), (parent.value,), (parent_pin,), prepared=math_profile.prepared, project="p")


def test_analysis_operations_compile_with_explicit_weak_and_contextual_dependencies():
    from pathlib import Path
    from corpus_structure.semantic import SourceArtifact, SourceBundle
    from corpus_structure.semantic.characterization_ports import characterization_operation_sources
    from corpus_structure.semantic.construction_products import construction_product_inputs
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.declared_math_analysis import math_analysis_declarations, math_analysis_operation_sources
    from corpus_structure.semantic.declared_math_products import math_operation_declarations, math_operation_sources
    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = construction_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    sources = combine_primary_sources(formal_operation_sources(), characterization_operation_sources(), math_operation_sources(), math_analysis_operation_sources())
    model = compile_data_operations(bundle, (math_operation_declarations(), math_analysis_declarations()), sources)
    weak = model.operation("analyze.math/lexical")
    strong = model.operation("analyze.math/contextual")
    assert weak.dependencies == ("text.formal_evidence/source-native",)
    assert {role.name for role in weak.roles if role.direction == "input"} == {"source", "formal"}
    assert {role.name for role in strong.roles if role.direction == "input"} == {"source", "formal", "constructions", "inherited", "ancestor_sources"}
    assert all(part.complete for part in model.implementation_slices)
