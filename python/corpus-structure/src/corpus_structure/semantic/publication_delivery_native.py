"""Record pending receipt origins from the exact uses created by publication."""

from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    Text,
    and_,
    any_,
    cast,
    column,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, insert

from .data_operation_projections import _custody_body_eligible
from .native_program import (
    Assign,
    Block,
    ForQuery,
    GetRowCount,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    PerformQuery,
    Return,
    SelectInto,
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program import literal as pg_literal


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
        parameters=(
            *(Parameter(parameter, column_type(column)) for parameter, column in fields),
            Parameter("p_limit", pg_type("int4"), pg_literal(1000)),
        ),
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
        .distinct()
        .order_by(origins.c.receipt_id)
        .limit(core_variable("p_limit", Integer())),
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
    )


def reconcile_publication_delivery(model, project, name, generation, limit=1000):
    """Materialize visible gaps while the caller owns the named generation fence."""
    origins = (
        func.ops.ddo_unreconciled_publication_origins(
            project, name, generation, cast(limit, Integer())
        )
        .table_valued(column("receipt_id", Text()))
        .render_derived(name="unreconciled_publications")
    )
    return _record_pending(model, project, name, generation, origins.c.receipt_id, origins)


def reconcile_demand_publications(model):
    """Repair committed enrollment/publication gaps through ordinary bounded resume.

    The same per-name fence as enrollment precedes the fresh statement reading
    fulfillment facts. Replays insert only missing exact origin identities.
    This is recovery evidence, never a claim that the selected scope is settled.
    """
    from .obligation_readiness_native import scheduler_authorized

    demands = model.tables["ops.data_demand"]
    history = model.tables["ops.data_demand_selection"]
    demand = core_variable("p_demand", Text())
    bound = core_variable("p_limit", Integer())
    total = core_variable("processed", BigInteger())
    project = core_variable("project", Text())
    name = core_variable("scope", Text(), "name")
    generation = core_variable("scope", BigInteger(), "generation")
    return NativeRoutine(
        "ops",
        "ddo_reconcile_demand_publications",
        parameters=(
            Parameter("p_demand", pg_type("text")),
            Parameter("p_limit", pg_type("int4"), pg_literal(1000)),
        ),
        returns=pg_type("int8"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    or_(
                        ~scheduler_authorized(),
                        bound.is_(None),
                        ~bound.between(1, 1000),
                        func.current_setting("transaction_isolation").not_in(
                            ("read committed", "read uncommitted")
                        ),
                    ),
                    (Return(literal(0)),),
                ),
                PerformQuery(
                    select(1)
                    .select_from(demands)
                    .where(demands.c.id == demand)
                    .with_for_update(read=True)
                ),
                If(~func.ops.ddo_demand_active(demand), (Return(literal(0)),)),
                SelectInto(
                    select(demands.c.project_id).where(demands.c.id == demand),
                    ("project",),
                    strict=True,
                ),
                ForQuery(
                    ("scope",),
                    select(core_relation_row(history))
                    .where(
                        history.c.project_id == project,
                        history.c.demand_id == demand,
                        ~_superseded(history),
                    )
                    .order_by(history.c.name),
                    (
                        If(
                            total < bound,
                            (
                                Perform(
                                    func.pg_advisory_xact_lock(
                                        func.hashtextextended(
                                            cast(
                                                func.jsonb_build_array(
                                                    "ops.data_demand_selection", project, name
                                                ),
                                                Text(),
                                            ),
                                            0,
                                        )
                                    )
                                ),
                                Sql(
                                    reconcile_publication_delivery(
                                        model, project, name, generation, bound - total
                                    )
                                ),
                                GetRowCount("inserted"),
                                Assign(
                                    "processed", total + core_variable("inserted", BigInteger())
                                ),
                            ),
                        ),
                    ),
                ),
                Return(total),
            ),
            (
                Local("scope", history),
                Local("project", pg_type("text")),
                Local("processed", pg_type("int8"), literal(0)),
                Local("inserted", pg_type("int8")),
            ),
        ),
    )


def settle_pending_discovery(model):
    """Close newly fulfilled, current discovery populations at the native owner."""
    demands = model.tables["ops.data_demand"]
    reads = model.tables["ops.data_demand_read"]
    obligations = model.tables["ops.data_obligation"]
    uses = model.tables["ops.demand_use"]
    populations = model.tables["ops.data_population"]
    products = model.tables["kb.data_product"]
    kinds = model.tables["sem.data_kind_contract"].alias("discovery_output_kind")
    outputs = model.tables["ops.data_derivation_output"]
    read = core_variable("p_read", reads.c.id.type)
    page = core_variable("p_page", ARRAY(Text()))
    boundary = core_variable("boundary", JSONB())
    demand_id = core_variable("boundary", reads.c.demand_id.type, "demand_id")
    universes = core_variable("boundary", reads.c.access_universes.type, "access_universes")
    project = core_variable("project", demands.c.project_id.type)
    payload = core_variable("payload", JSONB())
    processed = core_variable("processed", BigInteger())
    declarations = (
        func.jsonb_array_elements(demands.c.selection["discovery"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="discovery_declaration")
        .lateral()
    )
    selected = declarations.c.value
    name = selected["population"].astext
    later = uses.alias("later_discovery_use")
    superseded = (
        select(1)
        .select_from(later)
        .where(
            later.c.obligation_id == uses.c.obligation_id,
            or_(
                later.c.created_at > uses.c.created_at,
                and_(later.c.created_at == uses.c.created_at, later.c.id > uses.c.id),
            ),
            func.ops.ddo_read_visible(later.c.created_at, later.c.created_xid, boundary),
        )
        .correlate(uses)
        .exists()
    )
    closed = (
        select(1)
        .select_from(populations)
        .where(
            populations.c.demand_id == demand_id,
            populations.c.name == name,
            populations.c.evidence["product_id"].astext == outputs.c.product_id,
            populations.c.evidence["derivation_id"].astext == uses.c.derivation_id,
            populations.c.evidence["member_role"].astext == outputs.c.role,
            populations.c.evidence["admission_use_id"].astext == uses.c.id,
            ~populations.c.evidence.has_key("selection"),
            func.ops.ddo_read_visible(
                populations.c.created_at, populations.c.created_xid, boundary
            ),
            func.ops.ddo_node_valid("population", populations.c.id, boundary),
        )
        .correlate(declarations, uses, outputs)
        .exists()
    )
    pending = (
        select(
            func.jsonb_build_object(
                "demand_id",
                demand_id,
                "name",
                name,
                "product_id",
                outputs.c.product_id,
                "derivation_id",
                uses.c.derivation_id,
                "member_role",
                outputs.c.role,
                "admission_use_id",
                uses.c.id,
            ).label("discovery_payload")
        )
        .select_from(
            demands.join(obligations, obligations.c.demand_id == demands.c.id)
            .join(uses, uses.c.obligation_id == obligations.c.id)
            .join(declarations, selected["producer"].astext == obligations.c.operation_id)
            .join(
                outputs,
                and_(
                    outputs.c.derivation_id == uses.c.derivation_id,
                    outputs.c.role == selected["output_role"].astext,
                ),
            )
            .join(products, products.c.id == outputs.c.product_id)
            .join(kinds, kinds.c.kind_contract == products.c.kind_contract)
        )
        .where(
            demands.c.id == demand_id,
            func.ops.ddo_demand_active(demand_id),
            obligations.c.id == any_(page),
            func.ops.ddo_read_visible(
                obligations.c.created_at, obligations.c.created_xid, boundary
            ),
            uses.c.fate == "fulfilled",
            func.ops.ddo_read_visible(uses.c.created_at, uses.c.created_xid, boundary),
            ~superseded,
            ~closed,
            func.coalesce(universes.bool_op("?")(kinds.c.universe), False),
            _custody_body_eligible(model, products.c.kind_contract, products.c.canonical_body),
            func.ops.ddo_node_valid("use", uses.c.id, boundary),
        )
        .distinct()
        .order_by("discovery_payload")
    )
    return NativeRoutine(
        "ops",
        "ddo_settle_pending_discovery",
        parameters=(
            Parameter("p_read", column_type(reads.c.id)),
            Parameter("p_page", column_type(Column("page", ARRAY(Text())))),
        ),
        returns=pg_type("bigint"),
        body=Block(
            (
                SelectInto(
                    select(core_relation_row(reads)).where(reads.c.id == read),
                    ("boundary",),
                    strict=True,
                ),
                SelectInto(
                    select(demands.c.project_id).where(demands.c.id == demand_id),
                    ("project",),
                    strict=True,
                ),
                Perform(func.ops.ddo_require_read_current(boundary, project)),
                ForQuery(
                    ("payload",),
                    pending,
                    (
                        Perform(func.ops.close_data_population(payload)),
                        Assign("processed", processed + 1),
                    ),
                ),
                Return(processed),
            ),
            (
                Local("boundary", reads),
                Local("project", pg_type("text")),
                Local("payload", pg_type("jsonb")),
                Local("processed", pg_type("bigint"), literal(0)),
            ),
        ),
        search_path=("pg_catalog", "pg_temp"),
        security_definer=True,
    )
