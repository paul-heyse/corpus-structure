"""Exact scalar readiness from one native admitted-row read."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, insert
from sqlalchemy.types import NullType

from corpus_structure.schema.integrity import role_name

from .data_operation_projections import _items, _population_shortfall_candidate, binding_columns
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


def scheduler_authorized():
    """Scheduling authority is separate from a cut's public disclosure policy."""
    caller = func.coalesce(func.nullif(func.current_setting("role"), "none"), func.session_user())
    return or_(
        *(
            func.pg_has_role(caller, role_name(purpose), "MEMBER", type_=Boolean())
            for purpose in ("writer", "evaluator")
        )
    )


def _ordinary_scalar_role(role, kinds):
    def json(value):
        return cast(literal(value), JSONB())

    def empty(value, default="[]"):
        return func.coalesce(func.nullif(value, json("null")), json(default)) == json(default)

    return and_(
        role["minimum"].astext == "1",
        role["maximum"].astext == "1",
        role["presence"].astext == "required",
        role["collection"].astext == "scalar",
        role["support"]["origins"].in_(
            (json('["original-source"]'), json('["computation"]'), json('["authored"]'))
        ),
        role["support"]["source_set"].astext.is_(None),
        *(empty(role["support"][field]) for field in ("authorization", "closure")),
        role["support"]["identity_requirements"].in_(
            (json("[]"), json('["episode"]'), json('["original-source"]'))
        ),
        empty(role["alternatives"]),
        role["selected"].astext.is_(None),
        role["subject_field"].astext.is_(None),
        func.coalesce(role["subject_target"].astext, "subject") == "subject",
        empty(role["required_rules"]),
        kinds.c.universe.in_(("ordinary", "source")),
    )


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

    ordinary_role = _ordinary_scalar_role(role, kinds)
    invalid_role = exists(
        select(1)
        .select_from(roles.outerjoin(kinds, kinds.c.kind_contract == role["kind_contract"].astext))
        .where(ordinary_role.is_not(True))
        .correlate(definitions)
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
        select(1)
        .select_from(transitions)
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
    covered = and_(
        scheduler_authorized(),
        func.ops.ddo_demand_active(demands.c.id),
        or_(func.jsonb_array_length(definitions.c.input_roles) > 0, no_input_premises),
        ~invalid_role,
        empty(definitions.c.dependencies["potential"]),
        exact_selection,
        or_(
            func.jsonb_array_length(definitions.c.input_roles) == 0,
            empty(demands.c.selection["discovery"]),
        ),
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
            "role",
            role["name"],
            "position",
            rows.c.position,
            "multiplicity",
            rows.c.multiplicity,
            "product_id",
            rows.c.product,
            "member_id",
            rows.c.member,
            "producer_output",
            rows.c.support_evidence["producer_output"],
            "support_derivation_ids",
            rows.c.support_episodes,
        ),
        "support",
        support,
    )
    count = func.count()
    scalar = and_(count == 1, func.bool_and(rows.c.multiplicity == 1))
    producer = obligations.alias("readiness_producer")
    producer_definition = definitions.alias("readiness_producer_definition")
    producer_uses = model.tables["ops.demand_use"].alias("readiness_producer_use")
    episodes = model.tables["ops.data_derivation"]
    outputs = model.tables["ops.data_derivation_output"]
    products = model.tables["kb.data_product"]
    dependencies = (
        func.jsonb_array_elements_text(definitions.c.dependencies["required"])
        .table_valued(column("value", Text()))
        .render_derived(name="readiness_dependency")
    )
    declared_outputs = _items(producer_definition.c.output_roles, "readiness_declared_output")
    emits_kind = exists(
        select(1)
        .select_from(declared_outputs)
        .where(
            role["accepted_kind_contracts"].bool_op("?")(
                declared_outputs.c.value["kind_contract"].astext
            ),
        )
        .correlate(producer_definition, roles)
    )
    latest_producer = (
        select(producer_uses)
        .where(
            producer_uses.c.obligation_id == producer.c.id,
            func.ops.ddo_read_visible(
                producer_uses.c.created_at, producer_uses.c.created_xid, reads.table_valued()
            ),
        )
        .order_by(producer_uses.c.created_at.desc(), producer_uses.c.id.desc())
        .limit(1)
        .correlate(producer, reads)
        .lateral("readiness_producer_current")
    )
    has_output = exists(
        select(1)
        .select_from(outputs.join(products, products.c.id == outputs.c.product_id))
        .where(
            outputs.c.derivation_id == latest_producer.c.derivation_id,
            role["accepted_kind_contracts"].bool_op("?")(products.c.kind_contract),
        )
        .correlate(latest_producer, roles)
    )
    closed_producer = and_(
        producer.c.id.is_not(None),
        ~func.ops.ddo_obligation_wake_changed(
            producer.c.id, latest_producer.c.selection["read_id"].astext, reads.c.id
        ),
        episodes.c.request_id == latest_producer.c.request_id,
        episodes.c.generation == latest_producer.c.generation,
        or_(
            and_(
                latest_producer.c.fate == "fulfilled",
                episodes.c.outcome.in_(("success", "empty")),
                ~has_output,
                func.ops.ddo_node_valid("use", latest_producer.c.id, reads.table_valued()),
            ),
            and_(latest_producer.c.fate == "failed", episodes.c.outcome == "failed"),
        ),
    )
    complete_unavailable = and_(
        role["support"]["origins"] == json('["computation"]'),
        select(and_(func.count() > 0, func.coalesce(func.bool_and(closed_producer), False)))
        .select_from(
            dependencies.join(
                producer_definition,
                and_(
                    producer_definition.c.release_id == demands.c.release_id,
                    producer_definition.c.operation_id == dependencies.c.value,
                ),
            )
            .outerjoin(
                producer,
                and_(
                    producer.c.demand_id == demands.c.id,
                    producer.c.operation_id == dependencies.c.value,
                    producer.c.subject == obligations.c.subject,
                    producer.c.original_source.is_not_distinct_from(obligations.c.original_source),
                    producer.c.analyzed_scope == obligations.c.analyzed_scope,
                ),
            )
            .outerjoin(latest_producer, literal(True))
            .outerjoin(episodes, episodes.c.id == latest_producer.c.derivation_id)
        )
        .where(emits_kind)
        .correlate(definitions, demands, reads, obligations, roles)
        .scalar_subquery(),
    )
    per_role = (
        select(
            func.jsonb_build_object(
                "input_role",
                role["name"],
                "state",
                case(
                    (and_(count == 0, complete_unavailable), "unavailable"),
                    (count == 0, "missing"),
                    (count > 1, "ambiguous"),
                    (scalar, "ready"),
                    else_="invalid",
                ),
                "identity",
                case(
                    (scalar, func.jsonb_agg(identity, type_=JSONB())[0]),
                    else_=cast(literal(None), JSONB()),
                ),
            ).label("value"),
            scalar.label("ready"),
        )
        .select_from(rows)
        .where(
            role["accepted_kind_contracts"].bool_op("?")(rows.c.kind_contract),
            role["support"]["origins"].bool_op("?")(rows.c.support_references[0]["kind"].astext),
        )
        .correlate(roles)
        .lateral("role_readiness")
    )
    state = (
        select(
            func.jsonb_build_object(
                "ready",
                func.coalesce(func.bool_and(per_role.c.ready), literal(True)),
                "roles",
                func.coalesce(
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
        "ops",
        "ddo_obligation_readiness",
        parameters=(
            Parameter("p_obligation", pg_type("text")),
            Parameter("p_read", pg_type("text")),
        ),
        returns=pg_type("jsonb"),
        body=select(case((covered, state), else_=cast(literal(None), JSONB())))
        .select_from(
            obligations.join(demands, demands.c.id == obligations.c.demand_id)
            .join(reads, reads.c.demand_id == demands.c.id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == obligations.c.operation_id,
                ),
            )
        )
        .where(obligations.c.id == obligation, reads.c.id == read),
        security_definer=True,
        volatility="volatile",
        search_path=("pg_catalog", "pg_temp"),
    )


def population_binding_unavailable(model):
    """Certify insufficient closed selected populations at one actual read cut.

    Native selection owns predicate eligibility and population scope. Member
    projection counts every currently admitted support incidence for its keys,
    an upper bound on any further join/predicate selection. Qualified-context
    projection is decisive only when empty. Other arms require a complete
    selected witness or the same ordinary scalar readiness contract.
    """
    from .data_operation_projections import _obj, _origin_role_matches

    obligations = model.tables["ops.data_obligation"]
    demands = model.tables["ops.data_demand"]
    reads = model.tables["ops.data_demand_read"]
    definitions = model.tables["sem.data_operation_definition"]
    populations = model.tables["ops.data_population"]
    kinds = model.tables["sem.data_kind_contract"]
    obligation, read = core_variable("p_obligation", Text()), core_variable("p_read", Text())
    roles = _items(definitions.c.input_roles, "population_decision_role")
    role = roles.c.value
    selected = _items(demands.c.selection["operations"], "population_decision_operation")
    context = _obj(
        roledefs=definitions.c.input_roles,
        choices=selected.c.value["choices"],
        parameters=selected.c.value["parameters"],
        parameter_meaning=selected.c.value["parameter_meaning"],
        parameterdefs=definitions.c.parameter_definitions,
    )
    expression = definitions.c.binding_expression
    name = func.ops.ddo_binding_population_refs(expression, context, type_=JSONB())[
        role["name"].astext
    ].astext
    projection = func.coalesce(
        func.ops.ddo_binding_population_projection(expression, context, role["name"].astext),
        "member",
    )
    admitted = (
        func.ops.ddo_binding_rows(
            demands.c.id,
            definitions.c.operation_id,
            reads.c.trust_snapshot,
            reads.c.id,
            obligations.c.subject,
            func.coalesce(
                func.to_jsonb(obligations.c.original_source), cast(literal("null"), JSONB())
            ),
            obligations.c.analyzed_scope,
            False,
            cast(literal(None), JSONB()),
        )
        .table_valued(*binding_columns())
        .render_derived(name="population_decision_rows")
    )
    rows = (
        select(admitted)
        .correlate(demands, definitions, reads, obligations)
        .cte("population_decision_candidates")
        .prefix_with("MATERIALIZED")
    )
    members = _items(populations.c.members, "population_decision_member")
    matching_member = (
        select(1)
        .select_from(members)
        .where(
            members.c.value["member_id"].astext == rows.c.member,
        )
        .correlate(populations, rows)
        .exists()
    )
    upper_bound = (
        select(func.coalesce(func.sum(rows.c.multiplicity), 0))
        .select_from(rows)
        .where(
            rows.c.product == populations.c.evidence["product_id"].astext,
            role["accepted_kind_contracts"].bool_op("?")(rows.c.kind_contract),
            matching_member,
        )
        .correlate(populations, roles)
        .scalar_subquery()
    )
    candidate_for_member = (
        select(1)
        .select_from(rows)
        .where(
            rows.c.product == populations.c.evidence["product_id"].astext,
            rows.c.member == members.c.value["member_id"].astext,
            role["accepted_kind_contracts"].bool_op("?")(rows.c.kind_contract),
        )
        .correlate(populations, roles, members)
        .exists()
    )
    covered_members = (
        select(func.count())
        .select_from(members)
        .where(candidate_for_member)
        .correlate(populations, roles)
        .scalar_subquery()
    )
    no_proof_uncertainty = func.coalesce(
        role["required_rules"], cast(literal("[]"), JSONB())
    ) == cast(literal("[]"), JSONB())
    complete_arm = and_(
        populations.c.complete,
        no_proof_uncertainty,
        or_(
            func.jsonb_array_length(populations.c.members) == 0,
            and_(
                projection == "member",
                covered_members == func.jsonb_array_length(populations.c.members),
            ),
        ),
    )
    minimum = cast(role["minimum"].astext, BigInteger())
    insufficient = and_(
        minimum > 0,
        or_(
            func.jsonb_array_length(populations.c.members) == 0,
            and_(projection == "member", upper_bound < minimum),
        ),
    )
    selection = populations.c.evidence["selection"]
    scoped = (
        select(
            and_(func.count() == 1, func.bool_and(complete_arm)).label("resolved"),
            and_(func.count() == 1, func.bool_and(complete_arm), func.bool_and(insufficient)).label(
                "unavailable"
            ),
        )
        .select_from(populations)
        .where(
            populations.c.demand_id == demands.c.id,
            populations.c.selected_obligation_id == obligations.c.id,
            populations.c.name == name,
            selection["role"].astext == role["name"].astext,
            selection["definition"].astext == definitions.c.definition_identity,
            selection["eligibility"].astext == definitions.c.eligibility_identity,
            selection["parameter_meaning"] == selected.c.value["parameter_meaning"],
            selection["choices"] == selected.c.value["choices"],
            selection["subject"].astext == obligations.c.subject,
            selection["original_source"].astext.is_not_distinct_from(obligations.c.original_source),
            selection["analyzed_scope"] == obligations.c.analyzed_scope,
            func.ops.ddo_read_visible(
                populations.c.created_at, populations.c.created_xid, reads.table_valued()
            ),
            func.ops.ddo_node_valid("population", populations.c.id, reads.table_valued()),
        )
        .correlate(demands, definitions, reads, obligations, roles, selected)
        .lateral("population_arm_decision")
    )
    header = _obj(
        product=rows.c.product,
        member=rows.c.member,
        subject=rows.c.subject,
        subject_definition=rows.c.subject_definition,
        original_source=rows.c.original_source,
        analyzed_scope=rows.c.analyzed_scope,
        support_references=rows.c.support_references,
        support_evidence=rows.c.support_evidence,
    )
    scalar = (
        select(and_(func.count() == 1, func.bool_and(rows.c.multiplicity == 1)))
        .select_from(rows)
        .where(
            _origin_role_matches(
                role,
                header,
                rows.c.kind_contract,
                rows.c.analyzed_scope,
                rows.c.support_references[0]["kind"].astext,
                obligations,
                allow_body_predicate=False,
                selection=demands.c.selection,
            ),
        )
        .correlate(roles, obligations, demands)
        .scalar_subquery()
    )
    resolved = or_(scoped.c.resolved, and_(_ordinary_scalar_role(role, kinds), scalar))
    decision = (
        select(
            func.coalesce(
                and_(func.count() > 0, func.bool_and(resolved), func.bool_or(scoped.c.unavailable)),
                False,
            )
        )
        .select_from(
            roles.outerjoin(kinds, kinds.c.kind_contract == role["kind_contract"].astext).join(
                scoped, literal(True)
            )
        )
        .where(~(role["name"].astext == any_(func.ops.ddo_binding_inactive(expression, context))))
    )
    decision = (
        decision.add_cte(rows, nest_here=True)
        .correlate(demands, definitions, reads, obligations, selected)
        .scalar_subquery()
    )
    return NativeRoutine(
        "ops",
        "ddo_population_binding_unavailable",
        (
            Parameter("p_obligation", pg_type("text")),
            Parameter("p_read", pg_type("text")),
        ),
        pg_type("bool"),
        select(
            case(
                (
                    and_(
                        scheduler_authorized(),
                        _population_shortfall_candidate(
                            model,
                            obligations.c.id,
                            obligations.c.operation_id,
                            demands.c.release_id,
                            reads.table_valued(),
                        ),
                    ),
                    decision,
                ),
                else_=False,
            )
        )
        .select_from(
            obligations.join(demands, demands.c.id == obligations.c.demand_id)
            .join(reads, reads.c.demand_id == demands.c.id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == obligations.c.operation_id,
                ),
            )
            .join(selected, selected.c.value["operation"].astext == definitions.c.operation_id)
        )
        .where(
            obligations.c.id == obligation,
            reads.c.id == read,
            func.ops.ddo_read_visible(
                obligations.c.created_at, obligations.c.created_xid, reads.table_valued()
            ),
            func.ops.ddo_demand_active(demands.c.id),
        ),
        security_definer=True,
        volatility="volatile",
        search_path=("pg_catalog", "pg_temp"),
    )


def _binding_matches_readiness(ready, binding):
    """Match the actual authored input/support incidence, independent of array order."""
    role = _items(ready["roles"], "cut_role")
    reference = _items(role.c.value["identity"]["support"], "cut_support")
    empty = cast(literal("[]"), JSONB())
    inputs = select(
        func.coalesce(func.jsonb_agg(role.c.value["identity"]["input"]), empty)
    ).scalar_subquery()
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


def _complete_unavailable(ready):
    arm = _items(ready["roles"], "settlement_arm")
    return and_(
        ready.is_not(None),
        select(1).select_from(arm).where(arm.c.value["state"].astext == "unavailable").exists(),
        ~select(1)
        .select_from(arm)
        .where(
            arm.c.value["state"].astext.not_in(("ready", "unavailable")),
        )
        .exists(),
    )


def _failed_current_use(model, current, ready, obligation, read_id):
    episodes = model.tables["ops.data_derivation"]
    return and_(
        current.c.fate == "failed",
        ready["ready"].astext == "true",
        _binding_matches_readiness(ready, current.c.selection),
        ~func.ops.ddo_obligation_wake_changed(
            obligation, current.c.selection["read_id"].astext, read_id
        ),
        select(1)
        .select_from(episodes)
        .where(
            episodes.c.id == current.c.derivation_id,
            episodes.c.request_id == current.c.request_id,
            episodes.c.generation == current.c.generation,
            episodes.c.outcome == "failed",
        )
        .correlate(current)
        .exists(),
    )


def _matching_binding_cut(
    model, history, current, boundary, ready, obligation, read_id, *, read_owner=None
):
    cuts = model.tables["ops.data_obligation_cut"]
    attached = model.tables["ops.demand_use"].alias("cut_attachment")
    return (
        select(cuts)
        .select_from(cuts.join(attached, attached.c.id == cuts.c.attachment_use_id))
        .where(
            cuts.c.project_id == history.c.project_id,
            cuts.c.name == history.c.name,
            cuts.c.selection_generation == history.c.generation,
            cuts.c.obligation_id == obligation,
            cuts.c.roles == ready["roles"],
            ready["ready"].astext == "true",
            func.ops.ddo_read_visible(cuts.c.created_at, cuts.c.created_xid, boundary),
            ~func.ops.ddo_obligation_wake_changed(obligation, cuts.c.read_id, read_id),
            attached.c.request_id == current.c.request_id,
            attached.c.generation == current.c.generation,
            _binding_matches_readiness(ready, current.c.selection),
        )
        .order_by(cuts.c.created_at.desc(), cuts.c.attachment_use_id.desc())
        .limit(1)
        .correlate(history, current, *((read_owner,) if read_owner is not None else ()))
    )


def _verified_fulfilled_binding(model, history, current, boundary, obligation, read_id):
    """Native attachment already checked complex role/predicate/population inputs.

    A real fulfilled use retains that actual binding cut. It remains a complete
    binding decision only while no scoped origin or authority changed, and only
    for a named generation that was already visible when it was authored.
    """
    reads = model.tables["ops.data_demand_read"].alias("fulfilled_binding_read")
    return and_(
        current.c.fate == "fulfilled",
        current.c.request_id.is_not(None),
        current.c.generation.is_not(None),
        current.c.derivation_id.is_not(None),
        ~func.ops.ddo_obligation_wake_changed(
            obligation, current.c.selection["read_id"].astext, read_id
        ),
        select(1)
        .select_from(reads)
        .where(
            reads.c.id == current.c.selection["read_id"].astext,
            reads.c.demand_id == history.c.demand_id,
            reads.c.trust_snapshot == core_variable("boundary", JSONB(), "trust_snapshot"),
            reads.c.kernel_digest == core_variable("boundary", Text(), "kernel_digest"),
            func.ops.ddo_read_visible(
                history.c.created_at, history.c.created_xid, reads.table_valued()
            ),
        )
        .correlate(history, current)
        .exists(),
    )


def _unchanged_input_free_use(model, current, ready, demand, trust, kernel, obligation, read_id):
    """A real fulfilled source has no input incidence to reauthor for a name."""
    original = model.tables["ops.data_demand_read"].alias("input_free_binding_read")
    return and_(
        current.c.fate == "fulfilled",
        ready["ready"].astext == "true",
        ready["roles"] == cast(literal("[]"), JSONB()),
        _binding_matches_readiness(ready, current.c.selection),
        ~func.ops.ddo_obligation_wake_changed(
            obligation, current.c.selection["read_id"].astext, read_id
        ),
        select(1)
        .select_from(original)
        .where(
            original.c.id == current.c.selection["read_id"].astext,
            original.c.demand_id == demand,
            original.c.trust_snapshot == trust,
            original.c.kernel_digest == kernel,
        )
        .correlate_except(original)
        .exists(),
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
            (
                "project_id",
                "name",
                "selection_generation",
                "obligation_id",
                "attachment_use_id",
                "read_id",
                "roles",
                "created_at",
                "created_xid",
            ),
            select(
                history.c.project_id,
                history.c.name,
                history.c.generation,
                attached("obligation_id"),
                attached("id"),
                boundary("id"),
                ready["roles"],
                func.clock_timestamp(),
                cast(func.pg_current_xact_id(), Text()),
            ).where(current_scope, func.ops.ddo_demand_active(attached("demand_id"))),
        )
        .on_conflict_do_nothing()
    )
    return NativeRoutine(
        "ops",
        "ddo_record_obligation_cut",
        parameters=(Parameter("p_use", pg_type("text")), Parameter("p_read", pg_type("text"))),
        returns=pg_type("bigint"),
        body=Block(
            (
                SelectInto(
                    select(core_relation_row(uses)).where(uses.c.id == use_id),
                    ("attached",),
                    strict=True,
                ),
                SelectInto(
                    select(core_relation_row(reads)).where(
                        reads.c.id == read_id,
                        reads.c.demand_id == attached("demand_id"),
                        attached("selection")["read_id"].astext == reads.c.id,
                    ),
                    ("boundary",),
                    strict=True,
                ),
                SelectInto(
                    select(core_relation_row(demands)).where(demands.c.id == attached("demand_id")),
                    ("demand",),
                    strict=True,
                ),
                If(
                    or_(
                        ~scheduler_authorized(),
                        func.current_setting("transaction_isolation").not_in(
                            ("read committed", "read uncommitted")
                        ),
                    ),
                    (Return(literal(0)),),
                ),
                Perform(
                    func.ops.ddo_require_read_current(
                        core_variable("boundary", NullType()), project
                    )
                ),
                Assign(
                    "ready", func.ops.ddo_obligation_readiness(attached("obligation_id"), read_id)
                ),
                If(
                    func.coalesce(
                        and_(
                            ready.is_not(None),
                            ready["ready"].astext == "true",
                            _binding_matches_readiness(ready, attached("selection")),
                        ),
                        False,
                    ).is_not(True),
                    (Return(literal(0)),),
                ),
                ForQuery(
                    ("scope",),
                    select(core_relation_row(history))
                    .where(
                        history.c.project_id == project,
                        history.c.demand_id == attached("demand_id"),
                        ~_superseded(history),
                    )
                    .order_by(history.c.project_id, history.c.name),
                    (
                        Perform(
                            func.pg_advisory_xact_lock(
                                func.hashtextextended(
                                    cast(
                                        func.jsonb_build_array(
                                            "ops.data_demand_selection",
                                            scope("project_id"),
                                            scope("name"),
                                        ),
                                        Text(),
                                    ),
                                    0,
                                )
                            )
                        ),
                        Sql(write),
                        GetRowCount("inserted"),
                        Assign("total", total + inserted),
                    ),
                ),
                Return(total),
            ),
            (
                Local("attached", uses),
                Local("boundary", reads),
                Local("demand", demands),
                Local("scope", history),
                Local("ready", pg_type("jsonb")),
                Local("inserted", pg_type("bigint")),
                Local("total", pg_type("bigint"), literal(0)),
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
    obligation = core_variable("p_obligation", Text())
    read_id = core_variable("p_read", Text())
    ready = core_variable("p_ready", JSONB())
    boundary = reads.table_valued()

    def visible(table):
        return func.ops.ddo_read_visible(table.c.created_at, table.c.created_xid, boundary)

    current = (
        select(uses)
        .where(uses.c.obligation_id == obligation, visible(uses))
        .order_by(uses.c.created_at.desc(), uses.c.id.desc())
        .limit(1)
        .correlate(reads)
        .lateral("cut_current_use")
    )
    unavailable = or_(
        core_variable("p_unavailable", Boolean()),
        _complete_unavailable(ready),
        _failed_current_use(model, current, ready, obligation, read_id),
    )
    retained = _matching_binding_cut(
        model, history, current, boundary, ready, obligation, read_id, read_owner=reads
    ).lateral("matching_binding_cut")
    input_free = _unchanged_input_free_use(
        model,
        current,
        ready,
        demands.c.id,
        reads.c.trust_snapshot,
        reads.c.kernel_digest,
        obligation,
        read_id,
    )
    settled = case(
        (
            and_(
                or_(retained.c.attachment_use_id.is_not(None), input_free),
                current.c.fate == "fulfilled",
            ),
            func.ops.ddo_node_valid("use", current.c.id, boundary),
        ),
        else_=False,
    )
    state = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        func.jsonb_build_object(
                            "selection_name",
                            history.c.name,
                            "selection_generation",
                            history.c.generation,
                            "state",
                            case(
                                (unavailable, "unavailable"), (settled, "settled"), else_="pending"
                            ),
                            "binding_read_id",
                            case(
                                (unavailable, read_id),
                                (
                                    and_(input_free, retained.c.attachment_use_id.is_(None)),
                                    current.c.selection["read_id"].astext,
                                ),
                                else_=retained.c.read_id,
                            ),
                            "attachment_use_id",
                            case(
                                (unavailable, None),
                                (
                                    and_(input_free, retained.c.attachment_use_id.is_(None)),
                                    current.c.id,
                                ),
                                else_=retained.c.attachment_use_id,
                            ),
                            "successor_use_id",
                            case((settled, current.c.id), else_=None),
                        ),
                        history.c.name,
                    )
                ),
                cast(literal("[]"), JSONB()),
            )
        )
        .select_from(history.outerjoin(current, literal(True)).outerjoin(retained, literal(True)))
        .where(
            history.c.project_id == demands.c.project_id,
            history.c.demand_id == demands.c.id,
            ~_superseded(history),
            visible(history),
            func.ops.ddo_demand_active(demands.c.id),
        )
        .correlate(demands, reads)
        .scalar_subquery()
    )
    return NativeRoutine(
        "ops",
        "ddo_obligation_settlement",
        parameters=(
            Parameter("p_obligation", pg_type("text")),
            Parameter("p_read", pg_type("text")),
            Parameter("p_ready", pg_type("jsonb")),
            Parameter("p_unavailable", pg_type("bool")),
        ),
        returns=pg_type("jsonb"),
        body=select(
            case(
                (
                    and_(
                        scheduler_authorized(),
                        or_(ready.is_not(None), core_variable("p_unavailable", Boolean())),
                    ),
                    state,
                ),
                else_=cast(literal(None), JSONB()),
            )
        )
        .select_from(
            obligations.join(demands, demands.c.id == obligations.c.demand_id).join(
                reads, reads.c.demand_id == demands.c.id
            )
        )
        .where(obligations.c.id == obligation, reads.c.id == read_id),
        security_definer=True,
        volatility="volatile",
        search_path=("pg_catalog", "pg_temp"),
    )


def demand_settlement(model):
    """Observe the selected scope once, sharing native validity across its uses.

    This is an explicit fresh/pinned observation, not a claim based on an empty
    executor queue. Unsupported binding shapes remain pending and are counted.
    Full named-demand coverage includes upstream decisions between delivery edges.
    """
    from .data_operation_projections import (
        _obj,
        _scoped_read_obligations,
        _set_valid,
        _validity_rows,
    )
    from .native_program import Raise

    demands = model.tables["ops.data_demand"]
    reads = model.tables["ops.data_demand_read"]
    uses = model.tables["ops.demand_use"]
    history = model.tables["ops.data_demand_selection"]
    populations = model.tables["ops.data_population"]
    outputs = model.tables["ops.data_derivation_output"]
    episodes = model.tables["ops.data_derivation"]
    payload = core_variable("p_payload", JSONB())
    boundary = core_variable("boundary", NullType())
    read_id = core_variable("boundary", reads.c.id.type, "id")
    demand_id = core_variable("d", demands.c.id.type, "id")
    project = core_variable("d", demands.c.project_id.type, "project_id")
    scope = core_variable("boundary", reads.c.scope.type, "scope")
    scoped = _scoped_read_obligations(model).cte("settlement_scope").prefix_with("MATERIALIZED")
    ready = (
        select(
            scoped.c.id,
            func.ops.ddo_obligation_readiness(
                scoped.c.id,
                read_id,
                type_=JSONB(),
            ).label("ready"),
            case(
                (
                    _population_shortfall_candidate(
                        model,
                        scoped.c.id,
                        scoped.c.operation_id,
                        core_variable("d", Text(), "release_id"),
                        boundary,
                    ),
                    func.ops.ddo_population_binding_unavailable(
                        scoped.c.id, read_id, type_=Boolean()
                    ),
                ),
                else_=False,
            ).label("binding_unavailable"),
        )
        .cte("settlement_readiness")
        .prefix_with("MATERIALIZED")
    )
    current = (
        select(uses)
        .where(
            uses.c.obligation_id == ready.c.id,
            func.ops.ddo_read_visible(uses.c.created_at, uses.c.created_xid, boundary),
        )
        .order_by(uses.c.created_at.desc(), uses.c.id.desc())
        .limit(1)
        .correlate(ready)
        .lateral("settlement_current")
    )
    states = (
        select(
            ready.c.id.label("obligation_id"),
            ready.c.ready,
            ready.c.binding_unavailable,
            current.c.id,
            current.c.fate,
            current.c.request_id,
            current.c.generation,
            current.c.derivation_id,
            current.c.selection,
        )
        .select_from(ready.outerjoin(current, literal(True)))
        .cte("settlement_current_states")
        .prefix_with("MATERIALIZED")
    )
    used_population = _items(states.c.selection["populations"], "settlement_binding_population")
    selected_witness = (
        select(1)
        .select_from(states.join(used_population, literal(True)))
        .where(
            used_population.c.value["population_id"].astext == populations.c.id,
        )
        .correlate(populations)
        .exists()
    )
    closed_origin = (
        select(1)
        .select_from(states)
        .where(
            populations.c.evidence["admission_use_id"].astext == states.c.id,
        )
        .correlate(populations)
        .exists()
    )
    population_seed = (
        select(func.array_agg(populations.c.id))
        .where(
            populations.c.demand_id == demand_id,
            or_(selected_witness, closed_origin),
            func.ops.ddo_read_visible(
                populations.c.created_at, populations.c.created_xid, boundary
            ),
        )
        .scalar_subquery()
    )
    validity = _validity_rows(
        select(func.array_agg(states.c.id))
        .where(
            states.c.fate == "fulfilled",
        )
        .scalar_subquery(),
        name="settlement_validity",
        boundary=boundary,
        seed_populations=population_seed,
    )
    heads = (
        select(history)
        .where(
            history.c.project_id == project,
            history.c.demand_id == demand_id,
            ~_superseded(history),
            func.ops.ddo_demand_active(demand_id),
        )
        .cte("settlement_heads")
    )
    matched = _matching_binding_cut(
        model, heads, states, boundary, states.c.ready, states.c.obligation_id, read_id
    ).lateral("settlement_matching_cut")
    # Narrow resource cuts do not silently become a statement about their unseen
    # upstream selection. Their wider freshness interpretation belongs to its owner.
    accounted = and_(
        scope == cast(literal("{}"), JSONB()),
        func.ops.ddo_read_visible(heads.c.created_at, heads.c.created_xid, boundary),
    )
    unavailable = and_(
        accounted,
        or_(
            states.c.binding_unavailable,
            _complete_unavailable(states.c.ready),
            _failed_current_use(model, states, states.c.ready, states.c.obligation_id, read_id),
        ),
    )
    generic_fulfilled = _verified_fulfilled_binding(
        model, heads, states, boundary, states.c.obligation_id, read_id
    )
    input_free = _unchanged_input_free_use(
        model,
        states,
        states.c.ready,
        demand_id,
        core_variable("boundary", JSONB(), "trust_snapshot"),
        core_variable("boundary", Text(), "kernel_digest"),
        states.c.obligation_id,
        read_id,
    )
    settled = and_(
        accounted,
        or_(matched.c.attachment_use_id.is_not(None), generic_fulfilled, input_free),
        states.c.fate == "fulfilled",
        _set_valid(validity, "use", states.c.id),
    )
    observed = (
        select(
            heads.c.name,
            heads.c.generation,
            states.c.obligation_id,
            and_(states.c.ready.is_(None), ~settled, ~unavailable).label("uncovered"),
            case((unavailable, "unavailable"), (settled, "settled"), else_="pending").label(
                "state"
            ),
        )
        .select_from(heads.outerjoin(states, literal(True)).outerjoin(matched, literal(True)))
        .cte("selection_observations")
    )
    discovery = _items(
        core_variable("d", JSONB(), "selection")["discovery"], "settlement_discovery"
    )
    producer = scoped.alias("settlement_discovery_producer")
    producing = states.alias("settlement_discovery_use")
    witness = (
        select(1)
        .select_from(populations)
        .where(
            populations.c.demand_id == demand_id,
            populations.c.name == discovery.c.value["population"].astext,
            populations.c.evidence["admission_use_id"].astext == producing.c.id,
            populations.c.evidence["product_id"].astext == outputs.c.product_id,
            populations.c.complete,
            _set_valid(validity, "population", populations.c.id),
            func.ops.ddo_read_visible(
                populations.c.created_at, populations.c.created_xid, boundary
            ),
        )
        .correlate(discovery, producing, outputs)
        .exists()
    )
    relevant_output = and_(
        outputs.c.derivation_id == producing.c.derivation_id,
        outputs.c.role == discovery.c.value["output_role"].astext,
    )
    terminal_empty = (
        select(1)
        .select_from(episodes)
        .where(
            episodes.c.id == producing.c.derivation_id,
            episodes.c.request_id == producing.c.request_id,
            episodes.c.generation == producing.c.generation,
            episodes.c.outcome == "empty",
            ~select(1)
            .select_from(outputs)
            .where(outputs.c.derivation_id == episodes.c.id)
            .correlate(episodes)
            .exists(),
            ~func.ops.ddo_obligation_wake_changed(
                producer.c.id, producing.c.selection["read_id"].astext, read_id
            ),
        )
        .correlate(producing, producer)
        .exists()
    )
    complete_producer = and_(
        producing.c.fate == "fulfilled",
        _set_valid(validity, "use", producing.c.id),
        or_(
            terminal_empty,
            and_(
                select(1)
                .select_from(outputs)
                .where(relevant_output)
                .correlate(producing, discovery)
                .exists(),
                ~select(1)
                .select_from(outputs)
                .where(relevant_output, ~witness)
                .correlate(producing, discovery)
                .exists(),
            ),
        ),
    )
    producer_decisions = producer.join(producing, producing.c.obligation_id == producer.c.id)
    discovery_complete = (
        ~select(1)
        .select_from(discovery)
        .where(
            or_(
                ~select(1)
                .select_from(producer_decisions)
                .where(
                    producer.c.operation_id == discovery.c.value["producer"].astext,
                )
                .correlate(discovery)
                .exists(),
                select(1)
                .select_from(producer_decisions)
                .where(
                    producer.c.operation_id == discovery.c.value["producer"].astext,
                    complete_producer.is_not(True),
                )
                .correlate(discovery)
                .exists(),
            )
        )
        .exists()
    )
    count = func.count(observed.c.obligation_id)
    summaries = (
        select(
            observed.c.name,
            _obj(
                selection_name=observed.c.name,
                selection_generation=observed.c.generation,
                state=case(
                    (
                        and_(
                            discovery_complete,
                            count > 0,
                            func.bool_and(observed.c.state == "settled"),
                        ),
                        "settled",
                    ),
                    (
                        and_(
                            discovery_complete,
                            count > 0,
                            func.bool_and(observed.c.state.in_(("settled", "unavailable"))),
                        ),
                        "unavailable",
                    ),
                    else_="pending",
                ),
                obligation_count=count,
                settled_count=func.count(observed.c.obligation_id).filter(
                    observed.c.state == "settled"
                ),
                unavailable_count=func.count(observed.c.obligation_id).filter(
                    observed.c.state == "unavailable"
                ),
                pending_count=func.count(observed.c.obligation_id).filter(
                    observed.c.state == "pending"
                ),
                uncovered_count=func.count(observed.c.obligation_id).filter(observed.c.uncovered),
                discovery_complete=discovery_complete,
            ).label("value"),
        )
        .group_by(observed.c.name, observed.c.generation)
        .cte("selection_settlement")
    )
    result = _obj(
        read_id=read_id,
        scope=scope,
        selections=select(
            func.coalesce(
                func.jsonb_agg(summaries.c.value).aggregate_order_by(summaries.c.name),
                cast(literal("[]"), JSONB()),
            )
        ).scalar_subquery(),
    )
    return NativeRoutine(
        "ops",
        "read_demand_settlement",
        (Parameter("p_payload", pg_type("jsonb")),),
        pg_type("jsonb"),
        Block(
            (
                If(
                    ~scheduler_authorized(),
                    (Raise("demand settlement requires writer or evaluator authority", "42501"),),
                ),
                SelectInto(
                    select(core_relation_row(reads)).where(reads.c.id == payload["read_id"].astext),
                    ("boundary",),
                    strict=True,
                ),
                SelectInto(
                    select(core_relation_row(demands)).where(
                        demands.c.id
                        == core_variable("boundary", reads.c.demand_id.type, "demand_id"),
                    ),
                    ("d",),
                    strict=True,
                ),
                Perform(func.ops.ddo_require_read_current(boundary, project)),
                Assign("p", func.jsonb_build_object("scope", scope)),
                Return(func.jsonb_build_object("payload", result)),
            ),
            (Local("boundary", reads), Local("d", demands), Local("p", pg_type("jsonb"))),
        ),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
