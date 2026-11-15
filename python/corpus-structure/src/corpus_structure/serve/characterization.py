"""Current selected nominal characterization and definition products."""

from typing import Literal

from pydantic import Field

from corpus_structure.semantic.native_definition_projection import DefinitionVariant
from corpus_structure.serve.demand_journey import DemandQueryRequest


class DemandCharacterizationRequest(DemandQueryRequest):
    inventory: Literal[
        "summary", "occurrences", "annotations", "terms", "memberships", "choices", "coverage"
    ] = "summary"


def inspect_demand_characterization(connection, request: DemandCharacterizationRequest):
    """Read actual nominal primary members and explicit population/coverage standing."""
    from corpus_structure.semantic.contribution_queries import read_demand_contributions

    selected = request.model_dump(mode="python", exclude={"inventory"}, exclude_unset=True)
    selected["view"] = "coverage" if request.inventory == "coverage" else "members"
    selected["containers_only"] = request.inventory == "summary"
    selected["record_type"] = (
        None
        if request.inventory in {"summary", "coverage"}
        else {
            "occurrences": "occurrence",
            "annotations": "annotation",
            "terms": "term",
            "memberships": "membership",
            "choices": "choice",
        }[request.inventory]
    )
    return read_demand_contributions(connection, DemandQueryRequest.model_validate(selected))


class DemandDefinitionRequest(DemandQueryRequest):
    product_id: str = Field(min_length=1)
    variant: DefinitionVariant


def inspect_demand_definition(connection, request: DemandDefinitionRequest):
    """Inspect genuine selected definition products; no knowledge admission follows."""
    from corpus_structure.semantic.contribution_queries import read_demand_contributions
    from corpus_structure.semantic.releases import open_release

    selected = request.model_dump(mode="python", exclude={"variant"}, exclude_unset=True)
    selected.update(view="members", containers_only=True)
    result = read_demand_contributions(connection, DemandQueryRequest.model_validate(selected))
    release = open_release(connection, result["cut"]["release_id"])
    from corpus_structure.semantic.native_definition_projection import (
        read_native_definition_projection,
    )

    projection = read_native_definition_projection(release)
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.native_definition_projection import definition_variant_contract

    contract = definition_variant_contract(
        bound_data_operation_model(release), projection, request.variant
    )
    contracts = set() if contract is None else {contract}
    if not contracts:
        return dict(
            result,
            availability="unavailable",
            reason="selected release does not declare this definition product",
            items=[],
        )
    if any(row["kind_contract"] not in contracts for row in result["items"]):
        raise ValueError("selected definition product has another nominal kind")
    return dict(result, standing="private_selected_definition_product", variant=request.variant)
