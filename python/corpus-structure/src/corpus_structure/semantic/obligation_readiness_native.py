"""Exact scalar readiness from one native admitted-row read."""

from sqlalchemy import Text, and_, case, cast, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by

from .data_operation_projections import _items, binding_columns
from .native_program import NativeRoutine, Parameter, core_variable, pg_type


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
