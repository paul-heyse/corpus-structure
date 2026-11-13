"""Real target consumers accept the exact binding without reading or reselecting."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_consumers import BoundConsumerSelection
from corpus_structure.semantic.data_operation_model import BoundRoleMember, ResolvedRoleBinding


def retained(operation):
    member = BoundRoleMember("product:one", "kind:view", "view:original", "source:one", b"{}", b"{}", ("episode:one",), b"{}", member="view:member")
    return BindingResult(operation, "document:consumer", (ResolvedRoleBinding("views", "present", (member,)),), "ready", (), b"{}", b"{}", "data-operation-model-v2", "definition:one", "eligibility:one", (b"{}",))


def test_real_consumer_selection_handoff_preserves_exact_original_roles():
    from corpus_structure.methods.contextual_candidates import ContextualCandidates
    from corpus_structure.methods.m1_source import M1Candidates
    from corpus_structure.methods.native_evidence import NativeEvidenceMethod
    from corpus_structure.methods.structural_products import StructuralComparisonMethod

    for consumer in (NativeEvidenceMethod(), M1Candidates(), StructuralComparisonMethod(), ContextualCandidates()):
        binding = retained(consumer.__selection_operation__["id"])
        selected = consumer.select_bound(binding)
        assert selected.binding is binding
        assert selected.role("views").members[0].subject == "view:original"
        assert selected.subject == "document:consumer"
        with pytest.raises(ValueError, match="another operation"):
            consumer.select_bound(replace(binding, operation="unrelated"))
        with pytest.raises(ValueError, match="sufficient"):
            consumer.select_bound(replace(binding, status="awaiting-population"))


def test_consumer_handoff_refuses_ambiguous_or_undeclared_role():
    binding = retained("selected")
    with pytest.raises(ValueError, match="ambiguous"):
        BoundConsumerSelection(replace(binding, roles=binding.roles + binding.roles))
    with pytest.raises(ValueError, match="does not declare"):
        BoundConsumerSelection(binding).role("missing")
