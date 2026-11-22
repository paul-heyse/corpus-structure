"""Record pending receipt origins from the exact uses created by publication."""

from sqlalchemy import Text, cast, column, func, select
from sqlalchemy.dialects.postgresql import insert

from .native_program import NativeRoutine, Parameter, column_type, core_variable, pg_type


def record_publication_delivery(model, observe, receipt_id, project_id):
    """Use one command snapshot for newly fulfilled uses and their named heads.

    A later selection may supersede the observed generation. The row remains
    anchored to the original generation and cannot establish current coverage.
    """
    uses = model.tables["ops.demand_use"]
    selection = model.tables["ops.data_demand_selection"]
    fulfillments = model.tables["ops.data_publication_fulfillment"]
    observed = observe.returning(uses.c.id, uses.c.demand_id, uses.c.fate).cte(
        "publication_observations"
    )
    fulfilled = (
        insert(fulfillments)
        .from_select(
            ("demand_id", "receipt_id", "use_id"),
            select(observed.c.demand_id, receipt_id, observed.c.id).where(
                observed.c.fate == "fulfilled"
            ),
        )
        .returning(fulfillments.c.demand_id)
        .cte("publication_fulfillments")
    )
    scopes = (
        select(selection.c.project_id, selection.c.name, selection.c.generation)
        .select_from(fulfilled.join(selection, selection.c.demand_id == fulfilled.c.demand_id))
        .where(selection.c.project_id == project_id, ~_superseded(selection))
        .distinct()
        .subquery("publication_selection_scopes")
    )
    return _record_pending(
        model, scopes.c.project_id, scopes.c.name, scopes.c.generation, receipt_id, scopes
    )


def _superseded(selection):
    newer = selection.alias("newer_selection")
    return (
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


def _record_pending(model, project, name, generation, receipt, source):
    return (
        insert(model.tables["ops.data_publication_delivery"])
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
                project,
                name,
                generation,
                receipt,
                func.clock_timestamp(),
                cast(func.pg_current_xact_id(), Text()),
            ).select_from(source),
        )
        .on_conflict_do_nothing()
    )


def unreconciled_publication_origins(model):
    """See exact committed origins missing delivery for a current active generation.

    The two owners need not observe each other's uncommitted writes. They retain
    their own exact facts, and this query observes the join as soon as both
    commits are visible. No row establishes a settled or fresh selection.
    """
    history = model.tables["ops.data_demand_selection"]
    origins = model.tables["ops.data_publication_fulfillment"]
    pending = model.tables["ops.data_publication_delivery"]
    fields = (
        ("p_project", history.c.project_id),
        ("p_name", history.c.name),
        ("p_generation", history.c.generation),
    )
    project, name, generation = (
        core_variable(parameter, column.type) for parameter, column in fields
    )
    delivered = (
        select(1)
        .select_from(pending)
        .where(
            pending.c.project_id == history.c.project_id,
            pending.c.name == history.c.name,
            pending.c.selection_generation == history.c.generation,
            pending.c.receipt_id == origins.c.receipt_id,
        )
        .correlate(history, origins)
        .exists()
    )
    returns = pg_type("text")
    returns.setof = True
    return NativeRoutine(
        "ops",
        "ddo_unreconciled_publication_origins",
        parameters=tuple(Parameter(parameter, column_type(column)) for parameter, column in fields),
        returns=returns,
        body=select(origins.c.receipt_id)
        .select_from(history.join(origins, history.c.demand_id == origins.c.demand_id))
        .where(
            history.c.project_id == project,
            history.c.name == name,
            history.c.generation == generation,
            ~_superseded(history),
            func.ops.ddo_demand_active(history.c.demand_id),
            ~delivered,
        )
        .distinct(),
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
    )


def reconcile_publication_delivery(model, project, name, generation):
    """Materialize visible gaps while the caller owns the named generation fence."""
    origins = (
        func.ops.ddo_unreconciled_publication_origins(project, name, generation)
        .table_valued(column("receipt_id", Text()))
        .render_derived(name="unreconciled_publications")
    )
    return _record_pending(model, project, name, generation, origins.c.receipt_id, origins)
