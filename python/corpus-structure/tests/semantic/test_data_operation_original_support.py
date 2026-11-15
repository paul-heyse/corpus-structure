"""Support origin is admission policy; only declared exact origin identity salts values."""

from dataclasses import replace
from decimal import Decimal

import pytest

from corpus_structure.semantic.data_operation_compilation import (
    compile_data_operations,
    project_operation_binding,
)
from corpus_structure.semantic.data_operation_support import (
    OriginalSourceSupportReference,
    read_support_references,
)
from corpus_structure.semantic.types import PreparationError
from semantic.data_operation_declaration_support import (
    contract,
    declarations,
    identity,
    resolved_binding,
)


def governed(*, origins=None, exact=False):
    value = contract()
    support = value["roles"][0]["support"]
    support["provenance"] = "exact" if exact else "value_substitution"
    support["identity_requirements"] = ["original-source"] if exact else []
    if origins is not None:
        support["origins"] = origins
    return compile_data_operations(declarations=declarations(value))


def original_binding(model, *, admission="admission:one", reference="a" * 64):
    resolved = resolved_binding(model)
    role = resolved.roles[0]
    member = replace(
        role.members[0],
        support_episodes=(),
        support_references=(
            OriginalSourceSupportReference(admission_id=admission, source_reference=reference),
        ),
    )
    return replace(resolved, roles=(replace(role, members=(member,)),))


def test_allowed_origin_changes_eligibility_without_changing_recipe_or_same_value_request():
    computational = governed()
    mixed = governed(origins=["computation", "original-source"])
    assert identity(computational) == identity(mixed)
    assert identity(computational, domain="eligibility") != identity(mixed, domain="eligibility")
    assert identity(computational, domain="definition") != identity(mixed, domain="definition")
    computed, old_admission = project_operation_binding(
        computational,
        resolved_binding(computational),
    )
    source_value, original_admission = project_operation_binding(mixed, original_binding(mixed))
    assert computed.identity == source_value.identity
    assert old_admission.identity != original_admission.identity
    assert original_binding(mixed).roles[0].members[0].support_episodes == ()


def test_repeated_original_admission_receipts_do_not_create_new_semantic_votes():
    model = governed(origins=["original-source"])
    first, first_admission = project_operation_binding(model, original_binding(model))
    second, second_admission = project_operation_binding(
        model,
        original_binding(model, admission="admission:another-read"),
    )
    assert first.identity == second.identity
    assert first_admission.identity != second_admission.identity


def test_exact_original_fact_requires_stable_original_identity_and_never_fake_episode():
    model = governed(origins=["original-source"], exact=True)
    first, _ = project_operation_binding(model, original_binding(model))
    second, _ = project_operation_binding(model, original_binding(model, reference="b" * 64))
    assert first.identity != second.identity
    with pytest.raises(ValueError, match="computational support projection"):
        replace(original_binding(model).roles[0].members[0], support_episodes=("admission:one",))
    value = contract()
    value["roles"][0]["support"]["origins"] = ["original-source"]
    with pytest.raises(PreparationError, match="original-source identity"):
        compile_data_operations(declarations=declarations(value))


def test_original_support_cannot_enter_undeclared_computational_origin():
    model = governed()
    with pytest.raises(PreparationError, match="origin"):
        project_operation_binding(model, original_binding(model))
    with pytest.raises(ValueError):
        read_support_references(
            [
                {
                    "kind": "computation",
                    "derivation_id": "admission:one",
                    "admission_id": "admission:one",
                }
            ]
        )


def test_original_origin_and_historical_default_survive_owned_archive_roundtrip():
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    for model in (governed(), governed(origins=["original-source"])):
        restored = read_effective_data_operations(model.content)
        assert restored.content == model.content
        assert restored.operations[0].roles[0].support == model.operations[0].roles[0].support


@pytest.mark.parametrize(
    "scope",
    [None, False, 0, {"fraction": Decimal("0.123456789012345678901"), "nested": [True, None]}],
)
def test_authored_scope_preserves_exact_fraction_null_and_boolean_distinctions(scope):
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_support import (
        AuthoredFactRef,
        authored_fact_selection,
        read_original_source_reference,
    )

    selected = authored_fact_selection(
        "fact",
        {"value": 7},
        kind_contract="kind:A",
        context=SubjectContext("project:A", "subject:A", "source:A", json_bytes(scope), subject_definition="document"),
        author="operator",
        selection_id="selection:A",
    )
    acquired = read_original_source_reference(selected.reference)
    assert isinstance(acquired, AuthoredFactRef)
    assert semantic_value(selected.record()["reference"]["analyzed_scope"]) == semantic_value(scope)
    assert semantic_value(acquired.analyzed_scope) == semantic_value(scope)
    assert json_bytes(selected.record()["reference"]) == selected.reference
    assert json_loads(selected.reference)["meaning_body"] == semantic_value({"value": 7})


def test_authored_project_source_is_required_explicit_null_and_checked_at_freeze():
    from pydantic import ValidationError
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_support import AuthoredFactRef, authored_fact_selection

    project = contract()
    project.update(id="project-operation", subject="knowledge-universe", subject_definition={"id": "knowledge-universe", "identifier_kind": "string", "scope": "project"})
    source = contract()
    source.update(id="source-operation", subject="original", subject_definition={"id": "original", "identifier_kind": "string", "scope": "original-source"})
    model = compile_data_operations(declarations=declarations(project, source))
    context = SubjectContext("project:A", "knowledge:A", None, b"null", subject_definition="knowledge-universe")
    selection = authored_fact_selection("known", 7, kind_contract="kind:integer", context=context, author="operator", selection_id="explicit-empty-universe")
    reference = selection.record()["reference"]
    assert "original_source" in reference and reference["original_source"] is None
    AuthoredFactRef.model_validate(reference)
    missing = dict(reference)
    del missing["original_source"]
    with pytest.raises(ValidationError):
        AuthoredFactRef.model_validate(missing)
    intent = freeze_demand(model, roots=(RootSubject(context.subject, None, b"null"),), targets=("project-operation",), inference="explicit", execution_profile="test", original_sources=(selection,))
    assert intent.record["original_sources"]["known"]["reference"] == reference
    forged = authored_fact_selection("known", 7, kind_contract="kind:integer", context=replace(context, subject_definition="original"), author="operator", selection_id="source-without-source")
    with pytest.raises(ValueError, match="project"):
        freeze_demand(model, roots=(RootSubject(context.subject, None, b"null"),), targets=("project-operation",), inference="explicit", execution_profile="test", original_sources=(forged,))
