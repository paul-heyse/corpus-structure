"""Compare a consuming role's requirements with explicitly observed producer facts."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_json import json_bytes, native_json_loads
from .data_operation_model import BoundRoleMember, ProducerRequirement
from .reference_resolution import ProducingReferenceInput
from .selected_support import ProducerOutputOccurrence


class SelectedProducerContract(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    version: Literal["selected-producer-contract-v1"]
    derivation_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)
    publication_receipt: bool
    cpu_receipt: bool
    admitted_effects: tuple[str, ...]
    validity_families: tuple[str, ...]
    reference_inputs: tuple[ProducingReferenceInput, ...] = ()
    reference_inputs_complete: bool = False


@dataclass(frozen=True)
class ProducerRequirementComparison:
    required: ProducerRequirement
    output: ProducerOutputOccurrence | None
    publication_receipt: bool | None
    cpu_receipt: bool | None
    admitted_effects: tuple[str, ...] | None
    validity_families: tuple[str, ...] | None
    failed: tuple[str, ...]
    unobserved: tuple[str, ...]

    @property
    def standing(self) -> Literal["satisfied", "refused", "unobserved"]:
        if self.failed:
            return "refused"
        return "unobserved" if self.unobserved else "satisfied"


def compare_producer_requirement(
    required: ProducerRequirement,
    *,
    output: ProducerOutputOccurrence | None = None,
    publication_receipt: bool | None = None,
    cpu_receipt: bool | None = None,
    admitted_effects: tuple[str, ...] | None = None,
    validity_families: tuple[str, ...] | None = None,
) -> ProducerRequirementComparison:
    """Missing observations stay explicit and grant no native publication authority."""
    checks: list[tuple[str, bool | None]] = [("publication_receipt", publication_receipt)]
    if required.output_role is not None:
        checks.append(
            ("output_role", None if output is None else output.role == required.output_role)
        )
    if required.requires_cpu:
        checks.append(("cpu_receipt", cpu_receipt))
    if required.required_effect is not None:
        checks.append(
            (
                "admitted_effect",
                None if admitted_effects is None else required.required_effect in admitted_effects,
            )
        )
    if required.required_family == "undetermined":
        checks.append(("required_family", None))
    elif required.required_family != "none":
        checks.append(
            (
                "validity_family",
                None
                if validity_families is None
                else required.required_family in validity_families,
            )
        )
    return ProducerRequirementComparison(
        required,
        output,
        publication_receipt,
        cpu_receipt,
        admitted_effects,
        validity_families,
        tuple(name for name, outcome in checks if outcome is False),
        tuple(name for name, outcome in checks if outcome is None),
    )


def compare_bound_producer(required: ProducerRequirement, member: BoundRoleMember):
    """Consume observations from the same native binding as the selected output."""
    evidence = native_json_loads(member.support_evidence)
    observed = evidence.get("producer_contract")
    if observed is None:
        return compare_producer_requirement(required, output=member.producer_output)
    contract = SelectedProducerContract.model_validate_json(json_bytes(observed))
    if member.support_episodes != (contract.derivation_id,):
        raise ValueError("producer observation differs from its selected computational support")
    return compare_producer_requirement(
        required,
        output=member.producer_output,
        publication_receipt=contract.publication_receipt,
        cpu_receipt=contract.cpu_receipt,
        admitted_effects=contract.admitted_effects,
        validity_families=contract.validity_families,
    )
