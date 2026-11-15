"""One selected native read owner for structural reports and their source custody."""

from contextlib import contextmanager
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.nonrich_contribution_facets import read_nonrich_root
from corpus_structure.semantic.observations import source_python

from .contribution_facets import ContributionFacetsRequest
from .selected_contributions import SelectedContributionScope, selected_contribution_scope

STRUCTURAL_READ_SOURCES = (
    "serve/selected_structural.py", "serve/structural_products.py",
    "serve/structural_gaps.py", "serve/source_decision_journey.py",
    "serve/selected_contributions.py", "serve/selected_math.py",
    "semantic/nonrich_contribution_facets.py", "semantic/structural_products.py",
    "semantic/declared_structural_references.py", "semantic/source_products.py",
    "semantic/contextual_operations.py", "semantic/observations.py",
)


@dataclass(frozen=True)
class StructuralScope(SelectedContributionScope):
    implementation: str


class SelectedStructuralRoot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str = Field(min_length=1)
    member_id: str | None = None
    use_id: str = Field(min_length=1)
    derivation_id: str = Field(min_length=1)


class StructuralReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    read_id: str | None = None
    expected_cut: str | None = None
    implementation: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
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
    from .rich_queries import installed_read_implementation

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
        type(request), sources=STRUCTURAL_READ_SOURCES, profile="selected-structural-read-v1"
    ) as implementation:
        if request.implementation is not None and request.implementation != implementation:
            raise ValueError("structural resource differs from its installed read implementation")
        if isinstance(connection, StructuralScope):
            scope = connection
            pins = scope.cut.record
            if (
                pins["demand_id"] != request.demand_id or pins["project_id"] != request.project_id
                or scope.scope != {"product_ids": products}
                or (request.read_id is not None and (request.read_id != pins["read_id"]
                    or request.expected_cut != scope.cut.identity))
                or scope.implementation != implementation
            ):
                raise ValueError("detached structural request differs from its authenticated read scope")
            if scope.index.retained_bytes > request.max_graph_bytes or scope.index.retained_records > request.max_graph_records:
                raise ValueError("detached structural closure exceeds its examined bound")
            yield scope
            return
        with selected_contribution_scope(connection, acquired, product_ids=products) as scope:
            yield StructuralScope(scope.cut, scope.index, scope.prepared, scope.model,
                                  scope.scope, scope.max_support_edges, implementation)


def selected_root(scope, root):
    """An exact selected output, never a body found merely in dependency closure."""
    candidates = tuple(
        selected
        for selected in scope.products(product_id=root.product_id)
        if selected.reference.member_id == root.member_id
        and selected.use_id == root.use_id
        and selected.derivation_id == root.derivation_id
    )
    if not candidates:
        return None
    first = candidates[0]
    if any(item.reference != first.reference or item.body != first.body for item in candidates):
        raise ValueError("selected structural output address has conflicting values")
    return first


def structural_report(scope, selected):
    root = read_nonrich_root(scope.model, selected)
    if root.structural is None:
        raise ValueError("selected output has no current structural report contract")
    return root.structural


def selected_contextual(scope, selected):
    """Validate the captured nominal schema before interpreting its encoded source values."""
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema

    nominal = "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalProduct"
    kind = next((kind for kind in scope.model.kinds if kind.semantic_id == nominal), None)
    contract = next(
        (identity.key for identity in scope.model.identities
         if identity.domain == "kind" and identity.owner == nominal), None
    )
    if (
        selected.nominal != nominal or selected.reference.member_id is not None
        or kind is None or not kind.complete or contract != selected.reference.kind_contract
    ):
        raise ValueError("contextual journey requires its actual captured retrieval whole")
    schema = json_loads(kind.facts).get("json_schema")
    if schema is None:
        raise ValueError("contextual retrieval has no captured nominal schema")
    validate_wire_schema(schema, json_loads(json_bytes(selected.body)))
    return {
        **selected.body,
        **{name: source_python(selected.body[name])
           for name in ("inventory", "candidate_list", "relationship_decision")},
    }


def producer(selected):
    return dict(
        reference=selected.reference.model_dump(mode="python"),
        context=selected.context.identity_record,
        nominal=selected.nominal,
        operation_id=selected.operation_id,
        use_id=selected.use_id,
        derivation_id=selected.derivation_id,
        output=selected.output,
    )


def bounded_result(request, result):
    if len(json_bytes(result)) > request.max_bytes:
        raise ValueError("structural response exceeds max_bytes; narrow the page")
    return result
