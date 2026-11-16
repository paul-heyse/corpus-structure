"""Current selected nominal characterization and definition products."""

from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.characterization_store import (
    FamilyOutcomeSummary,
    HistoricalProviderSummary,
)
from corpus_structure.semantic.data_operation_json import DdoJsonValue
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_definition_projection import DefinitionVariant
from corpus_structure.serve.demand_journey import DemandQueryRequest


class DemandCharacterizationRequest(DemandQueryRequest):
    inventory: Literal[
        "summary", "occurrences", "annotations", "terms", "memberships", "choices", "coverage"
    ] = "summary"


class SelectedCharacterizationSummary(BaseModel):
    """Current selected envelope metadata, with no analytical member payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["selected-characterization-summary-1"] = "selected-characterization-summary-1"
    source: dict[str, DdoJsonValue] | None = None
    original_document: str | None = None
    profile: str | None = None
    execution_profile: str | None = None
    outcome: str | None = None
    member_counts: dict[str, int] | None = None
    dependency_count: int | None = None
    active_count: int | None = None
    coverage: tuple[FamilyOutcomeSummary, ...] | None = Field(default=None, max_length=64)
    coverage_omitted: int = Field(default=0, ge=0)
    providers: tuple[HistoricalProviderSummary, ...] | None = Field(default=None, max_length=16)
    providers_omitted: int = Field(default=0, ge=0)


def _characterization_summary(body, *, native_annotation=False):
    """Project only declared header metadata from the bounded authenticated value.

    Missing provider/coverage/member fields remain unknown. Retained provider
    attributes describe their original record, never a new execution assertion.
    """
    values = {
        name: body[name]
        for name in ("source", "original_document", "profile", "execution_profile", "outcome")
        if name in body
    }
    if "members" in body:
        values["member_counts"] = dict(
            Counter(packet["body"]["record_type"] for packet in body["members"])
        )
    for field, output in (("dependencies", "dependency_count"), ("active", "active_count")):
        if field in body:
            values[output] = len(body[field])
    if "coverage" in body:
        values["coverage"] = [
            {name: row[name] for name in ("family", "outcome", "availability")}
            for row in body["coverage"][:64]
        ]
        values["coverage_omitted"] = max(0, len(body["coverage"]) - 64)
    if native_annotation:
        providers = {}
        for block in body["blocks"]:
            annotation = block["annotation"]
            # These are the actual declared spaCy annotation header fields;
            # arbitrary labels or generic model strings cannot create a provider.
            if "spacy_version" not in annotation:
                continue
            availability = annotation["availability"]
            provider = HistoricalProviderSummary(
                provider="spacy",
                profile=annotation["profile_recipe"],
                model=annotation["model"],
                model_version=annotation["model_version"],
                runtime_version=annotation["spacy_version"],
                configuration_digest=annotation["pipeline_config_digest"],
                availability=availability[:32],
                availability_omitted=max(0, len(availability) - 32),
            )
            providers[canonical_bytes(provider.model_dump(mode="json"))] = provider
        ordered = [providers[key] for key in sorted(providers)]
        values.update(providers=ordered[:16], providers_omitted=max(0, len(ordered) - 16))
    return SelectedCharacterizationSummary.model_validate(values).model_dump(mode="python")


def inspect_demand_characterization(
    connection, request: DemandCharacterizationRequest
) -> dict[str, Any]:
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
    result = read_demand_contributions(connection, DemandQueryRequest.model_validate(selected))
    if request.inventory != "summary":
        return result
    # A generic selected-result resource would replay the complete parent body.
    # Summary continuations use this same projection; do not advertise that other
    # representation as a metadata-only resource.
    summaries = []
    if result["items"]:
        from corpus_structure.semantic.releases import open_release
        from corpus_structure.serve.source_catalog import _kind_contracts

        prepared = open_release(connection, result["cut"]["release_id"])
        kinds = {
            **_kind_contracts(prepared, "DdoCharacterizationEnvelope"),
            **_kind_contracts(prepared, "DdoEnrichedDocumentView"),
        }
        for row in result["items"]:
            nominal = kinds.get(row["kind_contract"])
            if nominal is None:
                continue
            body = prepared.validate_python(nominal, row["body"]).model_dump(
                mode="python", exclude_unset=True
            )
            summaries.append(
                {
                    **{key: value for key, value in row.items() if key != "body"},
                    "summary": _characterization_summary(
                        body, native_annotation=nominal == "DdoSourceAnnotations"
                    ),
                }
            )
    return {
        **{key: value for key, value in result.items() if key != "resource_handle"},
        "projection": "characterization-summary-1",
        "items": summaries,
        "knowledge": "observed" if summaries else "unknown",
    }


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
