"""Selected declared neighborhoods; reading never ranks or encodes new vectors."""

from dataclasses import asdict

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.contextual_operations import admitted_contextual_inventory
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_queries import _cursor
from corpus_structure.semantic.demand_results import selected_record_index
from corpus_structure.semantic.observations import source_python


class DemandNeighborhoodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    read_id: str | None = None
    expected_cut: str | None = None
    max_bytes: int = Field(default=1048576, strict=True, ge=1024, le=67108864)


def neighborhood_projection(product, target_id):
    """Project an authenticated product; edges retain their actual directed ranks."""
    if product["version"] != "declared-contextual-neighborhood-1":
        raise ValueError("neighborhood consumer requires its declared mutual-neighborhood product")
    inventory = admitted_contextual_inventory(product)
    neighborhood = source_python(product["neighborhood"])
    if neighborhood["inventory_id"] != inventory.inventory_id or neighborhood["policy"] != "mutual-exact-cosine-top5-2":
        raise ValueError("neighborhood differs from its retained inventory or native policy")
    groups = {group.target_id: asdict(group) for group in inventory.semantic_groups}
    group = next((group for group in groups.values() if target_id == group["target_id"] or target_id in group["member_target_ids"]), None)
    if group is None:
        raise ValueError("target is outside the exact selected neighborhood inventory")
    neighbors = []
    for edge in neighborhood["edges"]:
        if edge["left_group"] == group["target_id"]:
            neighbors.append((edge["left_rank"], dict(edge, peer=groups[edge["right_group"]])))
        elif edge["right_group"] == group["target_id"]:
            neighbors.append((edge["right_rank"], dict(edge, peer=groups[edge["left_group"]])))
    return dict(
        kind="exploratory_cosine_neighbors",
        inventory_id=inventory.inventory_id,
        source_selection=inventory.source_selection,
        profile_id=neighborhood.get("profile_id"),
        status=neighborhood["status"],
        group=group,
        neighbors=[value for _, value in sorted(neighbors, key=lambda item: item[0])],
        standing="exploratory_neighborhood",
        inference="not_run",
    )


def inspect_demand_neighborhood(connection, request: DemandNeighborhoodRequest):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.releases import open_release

    with selected_record_index(
        connection, request.demand_id, project_id=request.project_id,
        scope={"product_ids": [request.product_id]},
        read_id=request.read_id, expected_cut=request.expected_cut,
        max_bytes=request.max_bytes, max_total_bytes=request.max_bytes,
    ) as (cut, index):
        product = index.mapping("kb.data_product", ("id",)).get(request.product_id)
        if product is None:
            return dict(
                format="selected-contextual-neighborhood-v1", availability="unavailable",
                reason="requested neighborhood product is outside the selected cut closure",
                cut_id=cut.identity, cut=cut.record, inference="not_run",
            )
        release = open_release(connection, cut.record["release_id"])
        model = bound_data_operation_model(release)
        kind = "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualNeighborhoodProduct"
        contracts = {identity.key for identity in model.identities if identity.domain == "kind" and identity.owner == kind}
        if product["kind_contract"] not in contracts:
            raise ValueError("selected product is not a declared mutual-neighborhood product")
        body = release.validate_json("DdoContextualNeighborhoodProduct", json_bytes(decode_semantic_value(product["canonical_body"]))).model_dump(mode="python", exclude_unset=True)
        projection = neighborhood_projection(body, request.target_id)
        pinned = request.model_copy(update=dict(read_id=cut.record["read_id"], expected_cut=cut.identity))
        result = dict(
            format="selected-contextual-neighborhood-v1", availability="available",
            cut_id=cut.identity, cut=cut.record, product_id=request.product_id,
            **projection, resource_handle=_cursor(pinned.model_dump(mode="python")),
        )
        if len(json_bytes(result)) > request.max_bytes:
            raise ValueError("selected neighborhood response exceeds max_bytes")
        return result
