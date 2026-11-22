"""Exact scalar readiness from one native admitted-row read."""

from sqlalchemy import BigInteger, Text, and_, case, cast, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, insert
from sqlalchemy.types import NullType

from .data_operation_projections import _items, binding_columns
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
    Return,
    SelectInto,
    Sql,
    core_relation_row,
    core_variable,
    pg_type,
)
from .publication_delivery_native import _superseded


def obligation_readiness(model):
    """Cover independent required scalar scans with direct computation origins.

    Frozen obligations, immutable source admissions and fulfilled native uses own
    the durable origins. This read adds no shadow wait receipt: it asks the same
    admitted-row owner used by binding for all arms at one acquired boundary.
    """
    obligations = model.tables["ops.data_obligation"]
    demands = model.tables["ops.data_demand"]
    reads = model.tables["ops.data_demand_read"]
    definitions = model.tables["sem.data_operation_definition"]
    kinds = model.tables["sem.data_kind_contract"]
    obligation = core_variable("p_obligation", Text())
    read = core_variable("p_read", Text())
    expression = definitions.c.binding_expression
    roles = _items(definitions.c.input_roles, "readiness_role")
    role = roles.c.value
    selected = _items(demands.c.selection["operations"], "readiness_operation")

    def json(value):
        return cast(literal(value), JSONB())

    def empty(value, default="[]"):
        return func.coalesce(func.nullif(value, json("null")), json(default)) == json(default)

    ordinary_role = and_(
        role["minimum"].astext == "1",
        role["maximum"].astext == "1",
        role["presence"].astext == "required",
        role["collection"].astext == "scalar",
        role["support"]["origins"].in_(
            (json('["original-source"]'), json('["computation"]'))
        ),
        role["support"]["source"].astext == "same-original",
        role["support"]["source_set"].astext.is_(None),
        *(empty(role["support"][field]) for field in ("authorization", "closure")),
        role["support"]["identity_requirements"].in_(
            (json("[]"), json('["episode"]'))
        ),
        empty(role["alternatives"]),
        role["selected"].astext.is_(None),
        role["subject_field"].astext.is_(None),
        func.coalesce(role["subject_target"].astext, "subject") == "subject",
        empty(role["required_rules"]),
        kinds.c.universe.in_(("ordinary", "source")),
    )
    invalid_role = exists(
        select(1)
        .select_from(roles.outerjoin(kinds, kinds.c.kind_contract == role["kind_contract"].astext))
        .where(ordinary_role.is_not(True))
        .correlate(definitions)
    )
    # The generic binding reader also permits a transitive producer closure.
    # Restrict this cutover to the finite direct shape until that responsibility
    # receives a native readiness interpretation of its own.
    nested_dependency = exists(
        select(1)
        .select_from(selected)
        .where(
            definitions.c.dependencies["required"].bool_op("?")(
                selected.c.value["operation"].astext
            ),
            ~empty(selected.c.value["dependencies"]),
        )
        .correlate(definitions, demands)
    )
    exact_selection = exists(
        select(1)
        .select_from(selected)
        .where(
            selected.c.value["operation"].astext == definitions.c.operation_id,
            selected.c.value["dependencies"].bool_op("@>")(definitions.c.dependencies["required"]),
            selected.c.value["dependencies"].bool_op("<@")(definitions.c.dependencies["required"]),
        )
        .correlate(definitions, demands)
    )
    other_fields = func.jsonb_strip_nulls(expression)
    for field in ("operator", "roles", "impact", "fields", "children", "operands"):
        other_fields = other_fields.op("-")(field)
    role_names = (
        select(func.jsonb_agg(aggregate_order_by(role["name"], role["name"].astext)))
        .select_from(roles)
        .correlate(definitions)
        .scalar_subquery()
    )
    transitions = _items(definitions.c.support_contract["transitions"], "readiness_transition")
    effectful_transition = exists(
        select(1).select_from(transitions)
        .where(~empty(transitions.c.value["effects"]))
        .correlate(definitions)
    )
    no_input_premises = and_(
        func.jsonb_array_length(definitions.c.input_roles) == 0,
        empty(definitions.c.dependencies["required"]),
        empty(definitions.c.support_contract["effects"]),
        ~effectful_transition,
        definitions.c.command_class.is_(None),
    )
    computation_role = exists(
        select(1).select_from(roles)
        .where(role["support"]["origins"] == json('["computation"]'))
        .correlate(definitions)
    )
    covered = and_(
        ~reads.c.public_disclosure,
        func.ops.ddo_demand_active(demands.c.id),
        or_(func.jsonb_array_length(definitions.c.input_roles) > 0, no_input_premises),
        or_(~computation_role, func.jsonb_array_length(definitions.c.dependencies["required"]) > 0),
        ~invalid_role,
        empty(definitions.c.dependencies["potential"]),
        ~nested_dependency,
        exact_selection,
        empty(demands.c.selection["discovery"]),
        empty(demands.c.selection["source_sets"], "{}"),
        expression["operator"].astext.in_(("scan", "all")),
        func.coalesce(expression["roles"], json("[]")).in_((json("[]"), role_names)),
        *(empty(expression[field]) for field in ("fields", "children", "operands")),
        other_fields == json("{}"),
    )
    admitted = (
        func.ops.ddo_binding_rows(
            demands.c.id,
            definitions.c.operation_id,
            reads.c.trust_snapshot,
            reads.c.id,
            obligations.c.subject,
            func.coalesce(func.to_jsonb(obligations.c.original_source), json("null")),
            obligations.c.analyzed_scope,
            literal(False),
            cast(literal(None), JSONB()),
        )
        .table_valued(*binding_columns())
        .render_derived(name="admitted_readiness_rows")
    )
    rows = (
        select(admitted)
        .select_from(admitted)
        .correlate(demands, definitions, reads, obligations)
        .cte("readiness_candidates")
        .prefix_with("MATERIALIZED")
    )
    references = _items(rows.c.support_references, "readiness_support")
    support = (
        select(
            func.jsonb_agg(
                references.c.value.op("||")(
                    func.jsonb_build_object("role", role["name"], "position", rows.c.position)
                )
            )
        )
        .select_from(references)
        .correlate(rows, roles)
        .scalar_subquery()
    )
    identity = func.jsonb_build_object(
        "input",
        func.jsonb_build_object(
            "role", role["name"],
            "position", rows.c.position,
            "multiplicity", rows.c.multiplicity,
            "product_id", rows.c.product,
            "member_id", rows.c.member,
            "producer_output", rows.c.support_evidence["producer_output"],
            "support_derivation_ids", rows.c.support_episodes,
        ),
        "support", support,
    )
    count = func.count()
    scalar = and_(count == 1, func.bool_and(rows.c.multiplicity == 1))
    per_role = (
        select(
            func.jsonb_build_object(
                "input_role", role["name"],
                "state", case(
                    (count == 0, "missing"),
                    (count > 1, "ambiguous"),
                    (scalar, "ready"),
                    else_="invalid",
                ),
                "identity", case(
                    (scalar, func.jsonb_agg(identity, type_=JSONB())[0]),
                    else_=cast(literal(None), JSONB()),
                ),
            ).label("value"),
            scalar.label("ready"),
        )
        .select_from(rows)
        .where(
            role["accepted_kind_contracts"].bool_op("?")(rows.c.kind_contract),
            role["support"]["origins"].bool_op("?")(
                rows.c.support_references[0]["kind"].astext
            ),
        )
        .correlate(roles)
        .lateral("role_readiness")
    )
    state = (
        select(
            func.jsonb_build_object(
                "ready", func.coalesce(func.bool_and(per_role.c.ready), literal(True)),
                "roles", func.coalesce(
                    func.jsonb_agg(aggregate_order_by(per_role.c.value, role["name"].astext)),
                    json("[]"),
                ),
            )
        )
        .select_from(roles.join(per_role, literal(True)))
        .add_cte(rows, nest_here=True)
        .correlate(demands, definitions, reads, obligations)
        .scalar_subquery()
    )
    return NativeRoutine(
        "ops", "ddo_obligation_readiness",
        parameters=(Parameter("p_obligation", pg_type("text")), Parameter("p_read", pg_type("text"))),
        returns=pg_type("jsonb"),
        body=select(case((covered, state), else_=cast(literal(None), JSONB())))
        .select_from(
            obligations.join(demands, demands.c.id == obligations.c.demand_id)
            .join(reads, reads.c.demand_id == demands.c.id)
            .join(definitions, and_(
                definitions.c.release_id == demands.c.release_id,
                definitions.c.operation_id == obligations.c.operation_id,
            ))
        )
        .where(obligations.c.id == obligation, reads.c.id == read),
        security_definer=True,
        volatility="volatile",
        search_path=("pg_catalog", "pg_temp"),
    )


def _binding_matches_readiness(ready, binding):
    """Match the actual authored input/support incidence, independent of array order."""
    role = _items(ready["roles"], "cut_role")
    reference = _items(role.c.value["identity"]["support"], "cut_support")
    empty = cast(literal("[]"), JSONB())
    inputs = select(func.coalesce(func.jsonb_agg(role.c.value["identity"]["input"]), empty)).scalar_subquery()
    support = (
        select(func.coalesce(func.jsonb_agg(reference.c.value), empty))
        .select_from(role.join(reference, literal(True)))
        .scalar_subquery()
    )
    return and_(
        func.jsonb_array_length(binding["inputs"]) == func.jsonb_array_length(inputs),
        binding["inputs"].bool_op("@>")(inputs),
        binding["inputs"].bool_op("<@")(inputs),
        func.jsonb_array_length(binding["support"]) == func.jsonb_array_length(support),
        binding["support"].bool_op("@>")(support),
        binding["support"].bool_op("<@")(support),
    )


def record_obligation_cut(model):
    """Retain one real attachment's checked arms under the current named fence."""
    reads = model.tables["ops.data_demand_read"]
    uses = model.tables["ops.demand_use"]
    demands = model.tables["ops.data_demand"]
    history = model.tables["ops.data_demand_selection"]
    cuts = model.tables["ops.data_obligation_cut"]
    use_id = core_variable("p_use", Text())
    read_id = core_variable("p_read", Text())
    ready = core_variable("ready", JSONB())
    total = core_variable("total", BigInteger())
    inserted = core_variable("inserted", BigInteger())

    def row(owner, table, field):
        return core_variable(owner, table.c[field].type, field)

    def attached(field):
        return row("attached", uses, field)

    def boundary(field):
        return row("boundary", reads, field)

    def scope(field):
        return row("scope", history, field)

    project = row("demand", demands, "project_id")
    current_scope = and_(
        history.c.project_id == scope("project_id"),
        history.c.name == scope("name"),
        history.c.generation == scope("generation"),
        history.c.demand_id == attached("demand_id"),
        ~_superseded(history),
    )
    write = (
        insert(cuts)
        .from_select(
            ("project_id", "name", "selection_generation", "obligation_id", "attachment_use_id", "read_id", "roles", "created_at", "created_xid"),
            select(
                history.c.project_id, history.c.name, history.c.generation,
                attached("obligation_id"), attached("id"), boundary("id"), ready["roles"],
                func.clock_timestamp(), cast(func.pg_current_xact_id(), Text()),
            ).where(current_scope, func.ops.ddo_demand_active(attached("demand_id"))),
        )
        .on_conflict_do_nothing()
    )
    return NativeRoutine(
        "ops", "ddo_record_obligation_cut",
        parameters=(Parameter("p_use", pg_type("text")), Parameter("p_read", pg_type("text"))),
        returns=pg_type("bigint"),
        body=Block(
            (
                SelectInto(select(core_relation_row(uses)).where(uses.c.id == use_id), ("attached",), strict=True),
                SelectInto(select(core_relation_row(reads)).where(
                    reads.c.id == read_id, reads.c.demand_id == attached("demand_id"),
                    attached("selection")["read_id"].astext == reads.c.id,
                ), ("boundary",), strict=True),
                SelectInto(select(core_relation_row(demands)).where(demands.c.id == attached("demand_id")), ("demand",), strict=True),
                If(or_(
                    boundary("public_disclosure"),
                    func.current_setting("transaction_isolation").not_in(("read committed", "read uncommitted")),
                ), (Return(literal(0)),)),
                Perform(func.ops.ddo_require_read_current(core_variable("boundary", NullType()), project)),
                Assign("ready", func.ops.ddo_obligation_readiness(attached("obligation_id"), read_id)),
                If(func.coalesce(and_(
                    ready.is_not(None), ready["ready"].astext == "true",
                    _binding_matches_readiness(ready, attached("selection")),
                ), False).is_not(True), (Return(literal(0)),)),
                ForQuery(("scope",), select(core_relation_row(history)).where(
                    history.c.project_id == project, history.c.demand_id == attached("demand_id"),
                    ~_superseded(history),
                ).order_by(history.c.project_id, history.c.name), (
                    Perform(func.pg_advisory_xact_lock(func.hashtextextended(cast(
                        func.jsonb_build_array("ops.data_demand_selection", scope("project_id"), scope("name")), Text()
                    ), 0))),
                    Sql(write),
                    GetRowCount("inserted"),
                    Assign("total", total + inserted),
                )),
                Return(total),
            ),
            (
                Local("attached", uses), Local("boundary", reads), Local("demand", demands),
                Local("scope", history), Local("ready", pg_type("jsonb")),
                Local("inserted", pg_type("bigint")), Local("total", pg_type("bigint"), literal(0)),
            ),
        ),
        security_definer=True,
        volatility="volatile",
        search_path=("pg_catalog", "pg_temp"),
    )


def obligation_settlement(model):
    """Observe only this obligation's certified scalar binding cut at a pinned read.

    The cut records actual attachment and its arms. A later real fulfilled use
    supplies completion; a local queue and an input-ready flag supply neither.
    """
    reads = model.tables["ops.data_demand_read"]
    demands = model.tables["ops.data_demand"]
    obligations = model.tables["ops.data_obligation"]
    history = model.tables["ops.data_demand_selection"]
    uses = model.tables["ops.demand_use"]
    cuts = model.tables["ops.data_obligation_cut"]
    attached = uses.alias("cut_attachment")
    obligation = core_variable("p_obligation", Text())
    read_id = core_variable("p_read", Text())
    ready = core_variable("p_ready", JSONB())
    boundary = reads.table_valued()

    def visible(table):
        return func.ops.ddo_read_visible(table.c.created_at, table.c.created_xid, boundary)

    current = (
        select(uses)
        .where(uses.c.obligation_id == obligation, visible(uses))
        .order_by(uses.c.created_at.desc(), uses.c.id.desc()).limit(1)
        .correlate(reads).lateral("cut_current_use")
    )
    retained = (
        select(cuts)
        .select_from(cuts.join(attached, attached.c.id == cuts.c.attachment_use_id))
        .where(
            cuts.c.project_id == history.c.project_id, cuts.c.name == history.c.name,
            cuts.c.selection_generation == history.c.generation, cuts.c.obligation_id == obligation,
            cuts.c.roles == ready["roles"], ready["ready"].astext == "true", visible(cuts),
            attached.c.request_id == current.c.request_id, attached.c.generation == current.c.generation,
            _binding_matches_readiness(ready, current.c.selection),
        )
        .order_by(cuts.c.created_at.desc(), cuts.c.attachment_use_id.desc()).limit(1)
        .correlate(history, current, reads).lateral("matching_binding_cut")
    )
    settled = case((and_(
        retained.c.attachment_use_id.is_not(None), current.c.fate == "fulfilled",
    ), func.ops.ddo_node_valid("use", current.c.id, boundary)), else_=False)
    state = (
        select(func.coalesce(func.jsonb_agg(aggregate_order_by(func.jsonb_build_object(
            "selection_name", history.c.name, "selection_generation", history.c.generation,
            "state", case((settled, "settled"), else_="pending"),
            "binding_read_id", retained.c.read_id,
            "attachment_use_id", retained.c.attachment_use_id,
            "successor_use_id", case((settled, current.c.id), else_=None),
        ), history.c.name)), cast(literal("[]"), JSONB())))
        .select_from(history.outerjoin(current, literal(True)).outerjoin(retained, literal(True)))
        .where(
            history.c.project_id == demands.c.project_id, history.c.demand_id == demands.c.id,
            ~_superseded(history), visible(history), func.ops.ddo_demand_active(demands.c.id),
        )
        .correlate(demands, reads).scalar_subquery()
    )
    return NativeRoutine(
        "ops", "ddo_obligation_settlement",
        parameters=(Parameter("p_obligation", pg_type("text")), Parameter("p_read", pg_type("text")), Parameter("p_ready", pg_type("jsonb"))),
        returns=pg_type("jsonb"),
        body=select(case((and_(~reads.c.public_disclosure, ready.is_not(None)), state), else_=cast(literal(None), JSONB())))
        .select_from(obligations.join(demands, demands.c.id == obligations.c.demand_id).join(reads, reads.c.demand_id == demands.c.id))
        .where(obligations.c.id == obligation, reads.c.id == read_id),
        security_definer=True,
        volatility="volatile",
        search_path=("pg_catalog", "pg_temp"),
    )
