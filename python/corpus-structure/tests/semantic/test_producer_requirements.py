"""Observed producer facts retain the consuming role's independent requirements."""

from dataclasses import replace
from typing import Any

import pytest

from corpus_structure.semantic.data_operation_model import ProducerRequirement
from corpus_structure.semantic.producer_requirements import compare_producer_requirement
from corpus_structure.semantic.selected_support import ProducerOutputOccurrence


def output(role="result"):
    return ProducerOutputOccurrence(role=role, position=0, multiplicity=1, member_id=None)


def test_none_family_and_public_issuer_can_satisfy_their_own_role():
    required = ProducerRequirement("authorization", False, "policy-authorization", "none")
    actual = compare_producer_requirement(
        required,
        output=output("authorization"),
        publication_receipt=True,
        admitted_effects=("policy-authorization",),
        validity_families=(),
    )
    assert actual.standing == "satisfied"
    assert actual.cpu_receipt is None
    assert actual.failed == actual.unobserved == ()
    rich = compare_producer_requirement(
        ProducerRequirement("consolidated", True, None, "rich"),
        output=output("consolidated"),
        publication_receipt=True,
        cpu_receipt=True,
        validity_families=("rich",),
    )
    assert rich.standing == "satisfied"


def test_unobserved_requirement_and_missing_receipt_are_explicit():
    required = ProducerRequirement("result", True, None, "undetermined")
    observed = compare_producer_requirement(required, output=output())
    assert observed.standing == "unobserved"
    assert observed.failed == ()
    assert observed.unobserved == ("publication_receipt", "cpu_receipt", "required_family")
    known = compare_producer_requirement(
        replace(required, required_family="none"), output=output(), publication_receipt=False
    )
    assert known.standing == "refused"
    assert known.failed == ("publication_receipt",)


@pytest.mark.parametrize(
    "damage,failed",
    [
        ("role", "output_role"),
        ("cpu", "cpu_receipt"),
        ("effect", "admitted_effect"),
        ("family", "validity_family"),
    ],
)
def test_each_wrong_producer_fact_names_its_failed_requirement(damage, failed):
    required = ProducerRequirement("result", True, "effect:actual", "rich")
    facts: dict[str, Any] = dict(
        output=output(),
        publication_receipt=True,
        cpu_receipt=True,
        admitted_effects=("effect:actual",),
        validity_families=("rich",),
    )
    if damage == "role":
        facts["output"] = output("other")
    elif damage == "cpu":
        facts["cpu_receipt"] = False
    elif damage == "effect":
        facts["admitted_effects"] = ("other",)
    else:
        facts["validity_families"] = ("other",)
    actual = compare_producer_requirement(required, **facts)
    assert actual.standing == "refused"
    assert actual.failed == (failed,)
    assert actual.unobserved == ()


def test_normal_binding_projection_refuses_wrong_selected_output_before_capture():
    from corpus_structure.semantic.data_operation_compilation import (
        compile_data_operations,
        project_operation_binding,
    )
    from corpus_structure.semantic.types import PreparationError
    from semantic.data_operation_declaration_support import contract, declarations, resolved_binding

    declaration = contract()
    declaration["roles"][0]["producer_requirement"] = {
        "output_role": "result",
        "requires_cpu": True,
        "required_effect": None,
        "required_family": "none",
    }
    model = compile_data_operations(declarations=declarations(declaration))
    binding = resolved_binding(model)
    role = binding.roles[0]
    wrong = replace(role.members[0], producer_output=output("another-output"))
    with pytest.raises(PreparationError, match=r"source.*selected producer violates output_role"):
        project_operation_binding(model, replace(binding, roles=(replace(role, members=(wrong,)),)))
    correct = replace(wrong, producer_output=output())
    request, _ = project_operation_binding(
        model, replace(binding, roles=(replace(role, members=(correct,)),))
    )
    assert request.identity.key


def test_normal_preparation_consumes_scoped_native_producer_observation():
    from corpus_structure.semantic.data_operation_compilation import (
        compile_data_operations,
        project_operation_binding,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
    from corpus_structure.semantic.types import PreparationError
    from semantic.data_operation_declaration_support import contract, declarations, resolved_binding

    declaration = contract()
    declaration["roles"][0]["producer_requirement"] = {
        "output_role": "result",
        "requires_cpu": True,
        "required_effect": None,
        "required_family": "rich",
    }
    model = compile_data_operations(declarations=declarations(declaration))
    binding = resolved_binding(model)
    role = binding.roles[0]
    observation = {
        "version": "selected-producer-contract-v1",
        "derivation_id": "episode:observed",
        "release_id": "release:producing",
        "runtime_id": "runtime:producing",
        "publication_receipt": True,
        "cpu_receipt": True,
        "admitted_effects": [],
        "validity_families": ["rich"],
    }
    member = replace(
        role.members[0],
        producer_output=output(),
        support_episodes=("episode:observed",),
        support_references=(ComputationalSupportReference(derivation_id="episode:observed"),),
        support_evidence=json_bytes({"producer_contract": observation}),
    )
    selected = replace(binding, roles=(replace(role, members=(member,)),))
    assert project_operation_binding(model, selected)[0].identity.key
    for changed, expected in (
        ({"cpu_receipt": False}, "cpu_receipt"),
        ({"validity_families": []}, "validity_family"),
        ({"derivation_id": "episode:other"}, "selected computational support"),
    ):
        wrong = replace(
            member, support_evidence=json_bytes({"producer_contract": {**observation, **changed}})
        )
        with pytest.raises(PreparationError, match=expected):
            project_operation_binding(
                model, replace(selected, roles=(replace(role, members=(wrong,)),))
            )
