"""Real target consumers accept the exact binding without reading or reselecting."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_consumers import BoundConsumerSelection
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BoundRoleMember,
    ResolvedRoleBinding,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference


def retained(operation):
    member = BoundRoleMember(
        "product:one",
        "kind:view",
        "view:original",
        "source:one",
        b"{}",
        b"{}",
        ("episode:one",),
        b"{}",
        member="view:member",
        subject_definition="document",
        support_references=tuple(
            ComputationalSupportReference(derivation_id=episode) for episode in ("episode:one",)
        ),
    )
    return BindingResult(
        operation,
        "document:consumer",
        (ResolvedRoleBinding("views", "present", (member,)),),
        "ready",
        (),
        b"{}",
        b"{}",
        MODEL_VERSION,
        "definition:one",
        "eligibility:one",
        (b"{}",),
    )


def test_retained_handoff_preserves_exact_roles_and_refuses_another_operation():
    binding = retained("admitted-selection")
    selected = BoundConsumerSelection.from_binding(binding, operation="admitted-selection")
    assert selected.binding is binding
    assert selected.role("views").members[0].subject == "view:original"
    assert selected.subject == "document:consumer"
    with pytest.raises(ValueError, match="another operation"):
        BoundConsumerSelection.from_binding(binding, operation="unrelated")
    with pytest.raises(ValueError, match="sufficient"):
        BoundConsumerSelection(replace(binding, status="awaiting-population"))


def test_consumer_handoff_refuses_ambiguous_or_undeclared_role():
    binding = retained("selected")
    with pytest.raises(ValueError, match="ambiguous"):
        BoundConsumerSelection(replace(binding, roles=binding.roles + binding.roles))
    with pytest.raises(ValueError, match="does not declare"):
        BoundConsumerSelection(binding).role("missing")
