"""Record pending receipt origins from the exact uses created by publication."""

from sqlalchemy import Text, cast, func, select
from sqlalchemy.dialects.postgresql import insert


def record_publication_delivery(model, observe, receipt_id, project_id):
    """Use one command snapshot for newly fulfilled uses and their named heads.

    A later selection may supersede the observed generation. The row remains
    anchored to the original generation and cannot establish current coverage.
    """
    uses = model.tables["ops.demand_use"]
    selection = model.tables["ops.data_demand_selection"]
    pending = model.tables["ops.data_publication_delivery"]
    observed = observe.returning(uses.c.demand_id, uses.c.fate).cte("publication_observations")
    newer = selection.alias("newer_selection")
    superseded = (
        select(1)
        .select_from(newer)
        .where(
            newer.c.project_id == selection.c.project_id,
            newer.c.name == selection.c.name,
            newer.c.generation > selection.c.generation,
        )
        .correlate(selection)
        .exists()
    )
    scopes = (
        select(selection.c.project_id, selection.c.name, selection.c.generation)
        .select_from(observed.join(selection, selection.c.demand_id == observed.c.demand_id))
        .where(observed.c.fate == "fulfilled", selection.c.project_id == project_id, ~superseded)
        .distinct()
        .subquery("publication_selection_scopes")
    )
    return (
        insert(pending)
        .from_select(
            (
                "project_id",
                "name",
                "selection_generation",
                "receipt_id",
                "created_at",
                "created_xid",
            ),
            select(
                scopes.c.project_id,
                scopes.c.name,
                scopes.c.generation,
                receipt_id,
                func.clock_timestamp(),
                cast(func.pg_current_xact_id(), Text()),
            ),
        )
        .on_conflict_do_nothing()
    )
