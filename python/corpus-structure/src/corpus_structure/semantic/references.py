"""Exact input-snapshot class references for source packets and domain operations."""

from sqlalchemy import select

from .metadata import table
from .query import SnapshotBinding


def read_reference_classes(
    connection, binding: SnapshotBinding, entity_ids: tuple[str, ...], *, read_budget=None
) -> dict[str, tuple[str, ...]]:
    """Resolve explicit packet referents in the exact admitted input snapshot."""
    from .query import StaleSnapshot, WrongRelease

    realization = table("data.realization")
    row = connection.execute(
        select(realization.c.release_id, realization.c.data_revision).where(
            realization.c.realization_id == binding.realization_id
        )
    ).one()
    if row.release_id != binding.release_id:
        raise WrongRelease("reference snapshot release differs from bound operation")
    if row.data_revision != binding.data_revision:
        raise StaleSnapshot("reference snapshot revision differs from bound operation")
    if not entity_ids:
        return {}
    membership = table("data.membership")
    result = {identity: [] for identity in entity_ids}
    query = select(membership.c.entity_id, membership.c.class_id).where(
        membership.c.release_id == binding.release_id,
        membership.c.realization_id == binding.realization_id,
        membership.c.entity_id.in_(entity_ids),
    )
    if read_budget is not None:
        read_budget.preflight(connection, query)
    for entity, cls in connection.execute(query):
        if read_budget is not None:
            read_budget.value((entity, cls))
        result[entity].append(cls)
    if any(not classes for classes in result.values()):
        raise ValueError("packet reference has no admitted input class membership")
    return {identity: tuple(sorted(set(classes))) for identity, classes in result.items()}
