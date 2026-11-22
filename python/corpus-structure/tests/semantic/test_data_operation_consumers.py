"""Real target consumers accept the exact binding without reading or reselecting."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_consumers import BoundConsumerSelection
from corpus_structure.semantic.data_operation_model import BoundRoleMember, ResolvedRoleBinding
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.data_operation_version import MODEL_VERSION


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
        replicate=None,
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


@pytest.mark.parametrize(
    "presence,minimum,count,accepted",
    [
        ("optional", 0, 0, True),
        ("optional", 0, 1, True),
        ("optional", 0, 2, False),
        ("required", 1, 0, False),
        ("required", 1, 1, True),
        ("required", 1, 2, False),
    ],
)
def test_executor_scalar_handoff_preserves_optional_omission_and_exact_cardinality(
    monkeypatch, presence, minimum, count, accepted
):
    from types import SimpleNamespace
    from typing import cast

    from corpus_structure.semantic.data_operation_consumers import (
        HydratedConsumerSelection,
        SelectedConsumerValue,
    )
    from corpus_structure.semantic.data_operation_demands import ReadyDataRequest
    from corpus_structure.semantic.data_operation_ports import PortRefusal

    binding = retained("selected")
    member = binding.roles[0].members[0]
    role = replace(binding.roles[0], members=(member,) * count)
    binding = replace(binding, roles=(role,))
    selected = HydratedConsumerSelection(
        BoundConsumerSelection(binding),
        (("views", tuple(SelectedConsumerValue.acquire(member, b'{"value":7}', b'["mapping",[["value",["integer","7"]]]]') for _ in range(count))),),
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.data_operation_consumers.hydrate_consumer_selection",
        lambda *args, **kwargs: selected,
    )
    operation = SimpleNamespace(
        consumer_selection=None,
        roles=(
            SimpleNamespace(
                name="views", kind="view", collection="scalar", minimum=minimum, presence=presence
            ),
        ),
    )
    # SQL hydration is replaced above: these controlled stand-ins supply only
    # this handoff's inputs, with no native/provider execution claim.
    from orchestrate.executor_support import ControlledNativeIO, executor_case

    executor = executor_case(
        native_io=ControlledNativeIO(hydrate=lambda *args, **options: selected)
    )
    executor.model = SimpleNamespace(
        operation=lambda _: operation,
        identities=(SimpleNamespace(owner="view", domain="kind", key="kind:view"),),
    )
    executor.demand = "demand"
    context = SimpleNamespace(model=executor.model, consumer_selectors={})
    ready = cast(
        ReadyDataRequest,
        SimpleNamespace(
            resolved=SimpleNamespace(trust_evidence=b'{"read_id":"read","trust":{}}'),
            binding_result=binding,
            operation="selected",
        ),
    )
    if not accepted:
        with pytest.raises(PortRefusal, match="scalar input requires one admitted member"):
            executor._hydrate(ready, context=context)
    else:
        values = executor._hydrate(ready, context=context)
        assert [item.value for item in values] == ([] if count == 0 else [{"value": 7}])
        from corpus_structure.semantic.data_operation_ports import HydratedRoleValue

        assert all(isinstance(item, HydratedRoleValue) for item in values)
        assert binding.roles[0].state == "present"
