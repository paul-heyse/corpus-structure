"""Compare a consuming role's requirements with explicitly observed producer facts."""

from dataclasses import dataclass
from typing import Literal

from .data_operation_model import ProducerRequirement
from .selected_support import ProducerOutputOccurrence


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
        checks.append(("output_role", None if output is None else output.role == required.output_role))
    if required.requires_cpu:
        checks.append(("cpu_receipt", cpu_receipt))
    if required.required_effect is not None:
        checks.append(("admitted_effect", None if admitted_effects is None else required.required_effect in admitted_effects))
    if required.required_family == "undetermined":
        checks.append(("required_family", None))
    elif required.required_family != "none":
        checks.append(("validity_family", None if validity_families is None else required.required_family in validity_families))
    return ProducerRequirementComparison(
        required, output, publication_receipt, cpu_receipt, admitted_effects, validity_families,
        tuple(name for name, outcome in checks if outcome is False),
        tuple(name for name, outcome in checks if outcome is None),
    )
