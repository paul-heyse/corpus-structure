"""Support origin is admission policy; only declared exact origin identity salts values."""

from dataclasses import replace

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

from .test_data_operation_compilation import contract, declarations, identity, resolved_binding


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
    member = replace(role.members[0], support_episodes=(), support_references=(
        OriginalSourceSupportReference(admission_id=admission, source_reference=reference),
    ))
    return replace(resolved, roles=(replace(role, members=(member,)),))


def test_allowed_origin_changes_eligibility_without_changing_recipe_or_same_value_request():
    computational = governed()
    mixed = governed(origins=["computation", "original-source"])
    assert identity(computational) == identity(mixed)
    assert identity(computational, domain="eligibility") != identity(mixed, domain="eligibility")
    assert identity(computational, domain="definition") != identity(mixed, domain="definition")
    computed, old_admission = project_operation_binding(
        computational, resolved_binding(computational),
    )
    source_value, original_admission = project_operation_binding(mixed, original_binding(mixed))
    assert computed.identity == source_value.identity
    assert old_admission.identity != original_admission.identity
    assert original_binding(mixed).roles[0].members[0].support_episodes == ()


def test_repeated_original_admission_receipts_do_not_create_new_semantic_votes():
    model = governed(origins=["original-source"])
    first, first_admission = project_operation_binding(model, original_binding(model))
    second, second_admission = project_operation_binding(
        model, original_binding(model, admission="admission:another-read"),
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
        read_support_references([{
            "kind": "computation", "derivation_id": "admission:one",
            "admission_id": "admission:one",
        }])
