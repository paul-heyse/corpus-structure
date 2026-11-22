"""Record pending receipt origins from the exact uses created by publication."""

from sqlalchemy import Column, Text, and_, any_, case, cast, column, func, or_, select, true
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, insert

from .data_operation_projections import _custody_body_eligible
from .native_program import (
    Block,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    ReturnQuery,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)


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


def fulfilled_use_recipients(model):
    """Find direct scalar-role candidates within a current exact named demand.

    The current named enrollment and fulfilled uses are the two durable facts.
    A NULL origin visits their intersection for this page, including uses
    attached by reuse and publication concurrent with enrollment.
    """
    history = model.tables["ops.data_demand_selection"]
    demands = model.tables["ops.data_demand"]
    reads = model.tables["ops.data_demand_read"]
    uses = model.tables["ops.demand_use"]
    obligations = model.tables["ops.data_obligation"]
    producer = obligations.alias("producer")
    recipient = obligations.alias("recipient")
    definitions = model.tables["sem.data_operation_definition"]
    producer_definition = definitions.alias("producer_definition")
    output = model.tables["ops.data_derivation_output"]
    derivations = model.tables["ops.data_derivation"]
    requests = model.tables["ops.data_request"]
    kind = model.tables["sem.data_kind_contract"].alias("output_kind")
    product = model.tables["kb.data_product"]
    fields = (
        ("p_project", history.c.project_id),
        ("p_name", history.c.name),
        ("p_generation", history.c.generation),
        ("p_read", reads.c.id),
        ("p_use", uses.c.id),
    )
    project, name, generation, read, use = (
        core_variable(parameter, field.type) for parameter, field in fields
    )
    page = core_variable("p_page", ARRAY(Text()))
    boundary = core_variable("boundary", JSONB())
    demand_id = core_variable("boundary", reads.c.demand_id.type, "demand_id")
    access_universes = core_variable("boundary", reads.c.access_universes.type, "access_universes")

    def occurrence(values, name):
        return (
            func.jsonb_array_elements(values)
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
            .lateral()
        )

    operations = occurrence(demands.c.selection["operations"], "selected_operation")
    input_role = occurrence(definitions.c.input_roles, "input_role")
    output_role = occurrence(producer_definition.c.output_roles, "output_role")
    selected = operations.c.value
    role = input_role.c.value
    emitted = output_role.c.value
    next_use = uses.alias("recipient_use")
    successor = (
        select(next_use.c.id, next_use.c.fate, next_use.c.selection)
        .where(
            next_use.c.obligation_id == recipient.c.id,
            func.ops.ddo_read_visible(next_use.c.created_at, next_use.c.created_xid, boundary),
        )
        .order_by(next_use.c.created_at.desc(), next_use.c.id.desc())
        .limit(1)
        .correlate(recipient)
        .lateral("recipient_current_use")
    )
    successor_input = occurrence(successor.c.selection["inputs"], "recipient_bound_input")
    successor_support = occurrence(successor.c.selection["support"], "recipient_bound_support")
    linked = (
        select(1)
        .select_from(successor_input.join(successor_support, true()))
        .where(
            successor_input.c.value["role"].astext == role["name"].astext,
            successor_input.c.value["product_id"].astext == output.c.product_id,
            successor_input.c.value["member_id"].astext.is_(None),
            successor_support.c.value["role"].astext == role["name"].astext,
            successor_support.c.value["position"].astext
            == successor_input.c.value["position"].astext,
            successor_support.c.value["admission_use_id"].astext == uses.c.id,
            successor_support.c.value["derivation_id"].astext == derivations.c.id,
        )
        .correlate(successor, input_role, output, uses, derivations)
        .exists()
    )
    successor_fate = case(
        (linked & (successor.c.fate == "attached"), "attached"),
        (
            linked & (successor.c.fate == "fulfilled"),
            case(
                (func.ops.ddo_node_valid("use", successor.c.id, boundary), "fulfilled"),
                else_="pending",
            ),
        ),
        else_="pending",
    )
    candidate = (
        select(
            history.c.name.label("selection_name"),
            history.c.generation.label("selection_generation"),
            uses.c.id.label("origin"),
            recipient.c.id.label("recipient"),
            role["name"].astext.label("input"),
            output.c.role.label("output"),
            output.c.position.label("position"),
            func.jsonb_build_object(
                "selection_name",
                history.c.name,
                "selection_generation",
                history.c.generation,
                "use_id",
                uses.c.id,
                "producer_operation",
                producer.c.operation_id,
                "output_role",
                output.c.role,
                "output_position",
                output.c.position,
                "recipient_obligation",
                recipient.c.id,
                "recipient_operation",
                recipient.c.operation_id,
                "input_role",
                role["name"].astext,
                "successor_use_id",
                case((linked, successor.c.id), else_=None),
                "successor_fate",
                successor_fate,
            ).label("reason"),
        )
        .select_from(
            history.join(demands, demands.c.id == history.c.demand_id)
            .join(uses, uses.c.demand_id == demands.c.id)
            .join(producer, producer.c.id == uses.c.obligation_id)
            .join(derivations, derivations.c.id == uses.c.derivation_id)
            .join(requests, requests.c.id == derivations.c.request_id)
            .join(output, output.c.derivation_id == derivations.c.id)
            .join(product, product.c.id == output.c.product_id)
            .join(kind, kind.c.kind_contract == product.c.kind_contract)
            .join(recipient, recipient.c.demand_id == demands.c.id)
            .join(
                producer_definition,
                and_(
                    producer_definition.c.release_id == derivations.c.release_id,
                    producer_definition.c.operation_id == requests.c.operation_id,
                    producer_definition.c.recipe == derivations.c.recipe,
                ),
            )
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == recipient.c.operation_id,
                ),
            )
            .join(operations, selected["operation"].astext == recipient.c.operation_id)
            .join(input_role, true())
            .join(output_role, emitted["name"].astext == output.c.role)
            .outerjoin(successor, true())
        )
        .where(
            history.c.project_id == project,
            or_(name.is_(None), history.c.name == name),
            or_(generation.is_(None), history.c.generation == generation),
            history.c.demand_id == demand_id,
            ~_superseded(history),
            func.ops.ddo_demand_active(demands.c.id),
            or_(use.is_(None), uses.c.id == use),
            uses.c.fate == "fulfilled",
            func.ops.ddo_read_visible(uses.c.created_at, uses.c.created_xid, boundary),
            recipient.c.id == any_(page),
            func.ops.ddo_read_visible(recipient.c.created_at, recipient.c.created_xid, boundary),
            producer.c.operation_id == requests.c.operation_id,
            selected["dependencies"].contains(func.jsonb_build_array(producer.c.operation_id)),
            product.c.project_id == project,
            kind.c.universe.in_(("ordinary", "source")),
            func.coalesce(access_universes.bool_op("?")(kind.c.universe), False),
            ~func.ops.ddo_policy_authority_leaf(derivations.c.id),
            _custody_body_eligible(model, product.c.kind_contract, product.c.canonical_body),
            producer.c.subject == recipient.c.subject,
            producer.c.original_source.is_not_distinct_from(recipient.c.original_source),
            producer.c.analyzed_scope == recipient.c.analyzed_scope,
            product.c.subject == recipient.c.subject,
            product.c.analyzed_scope == recipient.c.analyzed_scope,
            output.c.member_id.is_(None),
            output.c.position == 0,
            output.c.multiplicity == 1,
            emitted["collection"].astext == "scalar",
            emitted["kind_contract"].astext == product.c.kind_contract,
            role["collection"].astext == "scalar",
            role["presence"].astext == "required",
            func.coalesce(role["subject_target"].astext, "subject") == "subject",
            role["subject_field"].astext.is_(None),
            role["support"]["source_set"].astext.is_(None),
            func.coalesce(
                role["support"]["origins"], func.jsonb_build_array("computation")
            ).bool_op("?")("computation"),
            func.ops.ddo_binding_source_address(
                role,
                func.jsonb_build_object("original_source", product.c.original_source),
                recipient.c.original_source,
                func.jsonb_build_object(),
            ),
            role["accepted_kind_contracts"].contains(
                func.jsonb_build_array(product.c.kind_contract)
            ),
        )
        .distinct()
        .subquery("routed_occurrences")
    )
    returned = pg_type("jsonb")
    returned.setof = True
    return NativeRoutine(
        "ops",
        "ddo_fulfilled_use_recipients",
        parameters=(
            *(Parameter(parameter, column_type(field)) for parameter, field in fields),
            Parameter("p_page", column_type(Column("page", ARRAY(Text())))),
        ),
        returns=returned,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        volatility="volatile",
        body=Block(
            (
                SelectInto(
                    select(core_relation_row(reads))
                    .select_from(reads.join(demands, demands.c.id == reads.c.demand_id))
                    .where(reads.c.id == read, demands.c.project_id == project),
                    ("boundary",),
                    strict=True,
                ),
                Perform(func.ops.ddo_require_read_current(boundary, project)),
                ReturnQuery(
                    select(candidate.c.reason).order_by(
                        candidate.c.recipient,
                        candidate.c.input,
                        candidate.c.origin,
                        candidate.c.output,
                        candidate.c.position,
                        candidate.c.selection_name,
                        candidate.c.selection_generation,
                    )
                ),
            ),
            (Local("boundary", reads),),
        ),
    )
