"""One selected native read owner for structural reports and their source custody."""

from contextlib import contextmanager
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.selected_contribution_input import SelectedContributionScope
from corpus_structure.semantic.selected_structural_projection import (
    STRUCTURAL_QUERY_ROOTS,
)
from corpus_structure.semantic.selected_support import SelectedOutputRoot

from .contribution_facets import ContributionFacetsRequest
from .selected_contributions import selected_contribution_scope


@dataclass(frozen=True)
class StructuralScope(SelectedContributionScope):
    implementation: str


SelectedStructuralRoot = SelectedOutputRoot


class StructuralReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    read_id: str | None = None
    expected_cut: str | None = None
    implementation: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    max_bytes: int = Field(default=1_000_000, strict=True, ge=1024, le=67_108_864)
    max_graph_bytes: int = Field(default=8_388_608, strict=True, ge=1024, le=67_108_864)
    max_graph_records: int = Field(default=100_000, strict=True, ge=1, le=1_000_000)
    max_support_edges: int = Field(default=100_000, strict=True, ge=1, le=1_000_000)

    @model_validator(mode="after")
    def pinned_read(self):
        if (self.read_id is None) != (self.expected_cut is None):
            raise ValueError("structural read requires both read_id and expected_cut")
        return self


@contextmanager
def structural_scope(connection, request, *, roots, source_products=()):
    """Acquire native roots, or consume an explicitly authenticated detached selection."""
    from corpus_structure.semantic.serving_identity import installed_read_implementation

    products = sorted({root.product_id for root in roots} | set(source_products))
    acquired = ContributionFacetsRequest(
        demand_id=request.demand_id,
        project_id=request.project_id,
        read_id=request.read_id,
        expected_cut=request.expected_cut,
        max_bytes=request.max_bytes,
        max_graph_bytes=request.max_graph_bytes,
        max_graph_records=request.max_graph_records,
        max_support_edges=request.max_support_edges,
    )
    with installed_read_implementation(
        type(request),
        entry="corpus_structure.semantic.selected_structural_projection",
        profile="selected-structural-read-v1",
        callables=STRUCTURAL_QUERY_ROOTS,
    ) as implementation:
        if request.implementation is not None and request.implementation != implementation:
            raise ValueError("structural resource differs from its installed read implementation")
        if isinstance(connection, StructuralScope):
            scope = connection
            pins = scope.cut.record
            if (
                pins["demand_id"] != request.demand_id
                or pins["project_id"] != request.project_id
                or scope.scope != {"product_ids": products}
                or (
                    request.read_id is not None
                    and (
                        request.read_id != pins["read_id"]
                        or request.expected_cut != scope.cut.identity
                    )
                )
                or scope.implementation != implementation
            ):
                raise ValueError(
                    "detached structural request differs from its authenticated read scope"
                )
            if (
                scope.index.retained_bytes > request.max_graph_bytes
                or scope.index.retained_records > request.max_graph_records
            ):
                raise ValueError("detached structural closure exceeds its examined bound")
            yield scope
            return
        with selected_contribution_scope(connection, acquired, product_ids=products) as scope:
            yield StructuralScope(
                scope.cut,
                scope.index,
                scope.prepared,
                scope.model,
                scope.scope,
                scope.max_support_edges,
                implementation,
                decimal_fixed_point_digits=scope.decimal_fixed_point_digits,
            )


def bounded_result(request, result):
    from corpus_structure.semantic.serving_code import serving_report

    result = serving_report(result)
    if len(json_bytes(result)) > request.max_bytes:
        raise ValueError("structural response exceeds max_bytes; narrow the page")
    return result
