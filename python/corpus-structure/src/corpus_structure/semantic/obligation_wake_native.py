"""Sparse native origin delivery using the existing exact PostgreSQL read cuts.

Only top-level transaction IDs from pg_current_xact_id are persisted. A prior
snapshot's xmin bounds the indexed suffix that can become newly visible; both
actual read cuts still decide visibility, including same-transaction commands.
There is no insertion-order cursor, extra counter or wake lock.
"""

from pglast import ast, enums
from sqlalchemy import (
    BigInteger,
    Boolean,
    MetaData,
    Numeric,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, insert

from corpus_structure.schema.integrity import role_name

from .data_operation_projections import _fact_origin, _items, _obj, _origin_role_matches
from .native_objects import INTERNAL_PROGRAM
from .native_program import (
    Block,
    GetRowCount,
    Local,
    NativeRoutine,
    Parameter,
    Return,
    Sql,
    call,
    pg_type,
    variable,
)
from .native_program_registry import ProgramDeclaration


def _record_wakes(model, candidates):
    wakes = model.tables["ops.data_obligation_wake"]
    rows = candidates.cte("affected_binding_origins")
    key = literal("binding-wake:") + func.ops.ddo_digest(
        func.jsonb_build_array(
            rows.c.obligation_id,
            rows.c.origin_kind,
            rows.c.origin_id,
            rows.c.input_role,
            rows.c.occurrence,
        )
    )
    return (
        insert(wakes)
        .from_select(
            tuple(wakes.c.keys()),
            select(
                key,
                rows.c.obligation_id,
                rows.c.origin_kind,
                rows.c.origin_id,
                rows.c.input_role,
                rows.c.occurrence,
                func.clock_timestamp(),
                cast(cast(func.pg_current_xact_id(), Text), Numeric()),
            ).order_by(key),
        )
        .on_conflict_do_nothing()
    )


def _computation_candidates(model, requested, *, only_obligation=None):
    demands = model.tables["ops.data_demand"]
    obligations = model.tables["ops.data_obligation"]
    definitions = model.tables["sem.data_operation_definition"]
    uses = model.tables["ops.demand_use"]
    origins = uses.alias("wake_origin")
    source = obligations.alias("wake_producer")
    origin_demand = demands.alias("wake_origin_demand")
    prior = uses.alias("wake_previous")
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    outputs = model.tables["ops.data_derivation_output"]
    previous = (
        select(prior)
        .where(
            prior.c.obligation_id == origins.c.obligation_id,
            or_(
                prior.c.created_at < origins.c.created_at,
                and_(prior.c.created_at == origins.c.created_at, prior.c.id < origins.c.id),
            ),
        )
        .order_by(prior.c.created_at.desc(), prior.c.id.desc())
        .limit(1)
        .correlate(origins)
        .lateral("wake_prior")
    )
    fulfilled = origins.c.fate == "fulfilled"
    before_selection = previous.c.selection.op("-")("read_id")
    after_selection = origins.c.selection.op("-")("read_id")
    changed = or_(
        previous.c.id.is_(None),
        origins.c.fate.is_distinct_from(previous.c.fate),
        origins.c.request_id.is_distinct_from(previous.c.request_id),
        origins.c.generation.is_distinct_from(previous.c.generation),
        origins.c.derivation_id.is_distinct_from(previous.c.derivation_id),
        origins.c.trust_snapshot.is_distinct_from(previous.c.trust_snapshot),
        after_selection.is_distinct_from(before_selection),
    )
    producing_episode = case((fulfilled, origins.c.derivation_id), else_=previous.c.derivation_id)
    producing_use = case((fulfilled, origins.c.id), else_=previous.c.id)
    projected = union_all(
        select(
            cast(literal(None), Text).label("member_id"),
            products.c.kind_contract,
            products.c.subject,
            products.c.subject_definition,
            products.c.original_source,
            products.c.analyzed_scope,
        )
        .where(outputs.c.member_id.is_(None))
        .correlate(products, outputs),
        select(
            members.c.member_id,
            members.c.kind_contract,
            members.c.subject,
            members.c.subject_definition,
            members.c.original_source,
            members.c.analyzed_scope,
        )
        .where(
            members.c.product_id == products.c.id,
            or_(outputs.c.member_id.is_(None), members.c.member_id == outputs.c.member_id),
        )
        .correlate(products, outputs),
    ).lateral("wake_projection")
    emitted = (
        select(
            origins.c.id.label("origin_id"),
            origins.c.demand_id,
            origins.c.obligation_id.label("producer_obligation"),
            case((fulfilled, literal("fulfilled-use")), else_=literal("use-fate")).label(
                "origin_kind"
            ),
            origin_demand.c.project_id,
            source.c.operation_id.label("producer_operation"),
            producing_episode.label("episode"),
            producing_use.label("producing_use"),
            outputs.c.role.label("output_role"),
            outputs.c.position.label("output_position"),
            outputs.c.multiplicity,
            outputs.c.member_id.label("emitted_member"),
            products.c.id.label("product_id"),
            projected,
        )
        .select_from(
            requested.join(origins, origins.c.id == requested.c.value)
            .join(source, source.c.id == origins.c.obligation_id)
            .join(origin_demand, origin_demand.c.id == origins.c.demand_id)
            .outerjoin(previous, literal(True))
            .join(outputs, outputs.c.derivation_id == producing_episode)
            .join(products, products.c.id == outputs.c.product_id)
            .join(projected, literal(True))
        )
        .where(changed, or_(fulfilled, previous.c.fate == "fulfilled"))
        .cte("wake_emitted")
        .prefix_with("MATERIALIZED")
    )
    roles = _items(definitions.c.input_roles, "wake_input_role").lateral()
    role = roles.c.value
    selected = _items(demands.c.selection["operations"], "wake_operation").lateral()
    occurrence = _obj(
        output_role=emitted.c.output_role,
        output_position=emitted.c.output_position,
        product_id=emitted.c.product_id,
        member_id=emitted.c.emitted_member,
    )
    header = _obj(
        product=emitted.c.product_id,
        member=emitted.c.member_id,
        subject=emitted.c.subject,
        subject_definition=emitted.c.subject_definition,
        original_source=emitted.c.original_source,
        analyzed_scope=emitted.c.analyzed_scope,
        support_references=func.jsonb_build_array(
            _obj(
                kind=literal("computation"),
                derivation_id=emitted.c.episode,
                admission_use_id=emitted.c.producing_use,
            )
        ),
        support_evidence=_obj(
            producer_output=_obj(
                member_id=emitted.c.emitted_member,
                role=emitted.c.output_role,
                position=emitted.c.output_position,
                multiplicity=emitted.c.multiplicity,
            )
        ),
    )
    fields = (
        obligations.c.id.label("obligation_id"),
        emitted.c.origin_kind,
        emitted.c.origin_id,
        role["name"].astext.label("input_role"),
        occurrence.label("occurrence"),
    )
    precise = and_(
        obligations.c.id == only_obligation if only_obligation is not None else literal(True),
        emitted.c.producer_obligation != obligations.c.id,
        func.ops.ddo_demand_active(demands.c.id),
        _origin_role_matches(
            role,
            header,
            emitted.c.kind_contract,
            emitted.c.analyzed_scope,
            literal("computation"),
            obligations,
            allow_body_predicate=False,
            selection=demands.c.selection,
        ),
    )
    # A same-demand publication is a primary-key lookup. It never enumerates
    # another project's or another demand's roles to discover its local recipients.
    local = (
        select(*fields)
        .select_from(
            emitted.join(demands, demands.c.id == emitted.c.demand_id)
            .join(obligations, obligations.c.demand_id == demands.c.id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == obligations.c.operation_id,
                ),
            )
            .join(roles, literal(True))
            .join(selected, selected.c.value["operation"].astext == obligations.c.operation_id)
        )
        .where(
            precise,
            or_(
                func.jsonb_array_length(selected.c.value["dependencies"]) == 0,
                selected.c.value["dependencies"].bool_op("?")(emitted.c.producer_operation),
            ),
        )
    )
    # For cross-demand pins, acquire definitions by the indexed accepted kind,
    # then demands by the exact declared source-set name/product/member. JSON
    # expansion happens only after those containment selectors can narrow work.
    kind_selector = func.jsonb_build_array(
        _obj(accepted_kind_contracts=func.jsonb_build_array(emitted.c.kind_contract))
    )
    source_name = func.coalesce(role["support"]["source_set"].astext, "")
    pin_selector = _obj(
        source_sets=func.jsonb_build_object(
            source_name,
            _obj(
                entries=func.jsonb_build_array(
                    _obj(product=emitted.c.product_id, member=emitted.c.member_id)
                )
            ),
        )
    )
    pinned = (
        select(*fields)
        .select_from(
            emitted.join(definitions, definitions.c.input_roles.contains(kind_selector))
            .join(
                roles,
                and_(
                    role["support"]["source_set"].astext.is_not(None),
                    role["accepted_kind_contracts"].bool_op("?")(emitted.c.kind_contract),
                ),
            )
            .join(
                demands,
                and_(
                    demands.c.project_id == emitted.c.project_id,
                    demands.c.release_id == definitions.c.release_id,
                    demands.c.selection.contains(pin_selector),
                ),
            )
            .join(
                obligations,
                and_(
                    obligations.c.demand_id == demands.c.id,
                    obligations.c.operation_id == definitions.c.operation_id,
                ),
            )
        )
        .where(precise)
    )
    # A declared dependency also settles when it emits no matching product.
    # Preserve that pending/complete-empty/failure transition without inventing
    # a product address or requiring a pre-existing selected input.
    dependency = (
        select(
            obligations.c.id.label("obligation_id"),
            literal("dependency-state").label("origin_kind"),
            origins.c.id.label("origin_id"),
            role["name"].astext.label("input_role"),
            _obj(producer_operation=source.c.operation_id, fate=origins.c.fate).label("occurrence"),
        )
        .select_from(
            requested.join(origins, origins.c.id == requested.c.value)
            .join(source, source.c.id == origins.c.obligation_id)
            .outerjoin(previous, literal(True))
            .join(demands, demands.c.id == origins.c.demand_id)
            .join(obligations, obligations.c.demand_id == demands.c.id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == obligations.c.operation_id,
                ),
            )
            .join(roles, literal(True))
            .join(selected, selected.c.value["operation"].astext == obligations.c.operation_id)
        )
        .where(
            obligations.c.id == only_obligation if only_obligation is not None else literal(True),
            source.c.id != obligations.c.id,
            changed,
            func.ops.ddo_demand_active(demands.c.id),
            selected.c.value["dependencies"].bool_op("?")(source.c.operation_id),
            func.coalesce(
                role["support"]["origins"], cast(literal('["computation"]'), JSONB())
            ).bool_op("?")("computation"),
            or_(
                role["support"]["source_set"].astext.is_(None),
                and_(
                    role["support"]["source"].astext == "original-source",
                    ~func.coalesce(
                        demands.c.selection["source_sets"], cast(literal("{}"), JSONB())
                    ).has_key(role["support"]["source_set"].astext),
                ),
            ),
            source.c.original_source.is_not_distinct_from(obligations.c.original_source),
            source.c.subject == obligations.c.subject,
            source.c.analyzed_scope == obligations.c.analyzed_scope,
        )
    )
    return local.union(pinned, dependency)


def _computation_wakes(model):
    from .native_program import core_variable

    requested = (
        func.jsonb_array_elements_text(core_variable("p_uses", JSONB()))
        .table_valued(column("value", Text()))
        .render_derived(name="wake_uses")
    )
    return _writer(
        model,
        "ddo_record_computation_wakes",
        "p_uses",
        _computation_candidates(model, requested),
        _computation_origins(model, requested),
    )


def _original_candidates(model, requested, *, only_obligation=None):
    admissions = model.tables["ops.original_source_admission"]
    demands = model.tables["ops.data_demand"]
    obligations = model.tables["ops.data_obligation"]
    definitions = model.tables["sem.data_operation_definition"]
    products = model.tables["kb.data_product"]
    roles = _items(definitions.c.input_roles, "original_wake_role").lateral()
    header = _obj(
        product=admissions.c.product_id,
        member=cast(literal(None), Text),
        subject=admissions.c.subject,
        subject_definition=products.c.subject_definition,
        original_source=admissions.c.original_source,
        analyzed_scope=admissions.c.analyzed_scope,
    )
    candidates = (
        select(
            obligations.c.id.label("obligation_id"),
            _fact_origin(admissions).label("origin_kind"),
            admissions.c.id.label("origin_id"),
            roles.c.value["name"].astext.label("input_role"),
            _obj(product_id=admissions.c.product_id).label("occurrence"),
        )
        .select_from(
            requested.join(admissions, admissions.c.id == requested.c.value)
            .join(demands, demands.c.id == admissions.c.demand_id)
            .join(products, products.c.id == admissions.c.product_id)
            .join(obligations, obligations.c.demand_id == demands.c.id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == obligations.c.operation_id,
                ),
            )
            .join(roles, literal(True))
        )
        .where(
            obligations.c.id == only_obligation if only_obligation is not None else literal(True),
            func.ops.ddo_demand_active(demands.c.id),
            _origin_role_matches(
                roles.c.value,
                header,
                products.c.kind_contract,
                admissions.c.analyzed_scope,
                _fact_origin(admissions),
                obligations,
                allow_body_predicate=False,
                selection=demands.c.selection,
            ),
        )
        .distinct()
    )
    return candidates


def _original_wakes(model):
    from .native_program import core_variable

    requested = (
        func.jsonb_array_elements_text(core_variable("p_admissions", JSONB()))
        .table_valued(column("value", Text()))
        .render_derived(name="wake_admissions")
    )
    return _writer(
        model, "ddo_record_original_wakes", "p_admissions", _original_candidates(model, requested)
    )


def _population_candidates(model, requested, *, only_obligation=None):
    populations = model.tables["ops.data_population"]
    demands = model.tables["ops.data_demand"]
    obligations = model.tables["ops.data_obligation"]
    discovery = _items(demands.c.selection["discovery"], "population_wake_discovery").lateral()
    operations = _items(demands.c.selection["operations"], "population_wake_operation").lateral()
    selected = populations.c.selected_obligation_id.is_not(None)
    candidates = (
        select(
            obligations.c.id.label("obligation_id"),
            literal("population").label("origin_kind"),
            populations.c.id.label("origin_id"),
            func.coalesce(
                case(
                    (selected, populations.c.evidence["selection"]["role"].astext),
                    else_=discovery.c.value["target_role"].astext,
                ),
                "",
            ).label("input_role"),
            _obj(name=populations.c.name, complete=populations.c.complete).label("occurrence"),
        )
        .select_from(
            requested.join(populations, populations.c.id == requested.c.value)
            .join(demands, demands.c.id == populations.c.demand_id)
            .join(obligations, obligations.c.demand_id == demands.c.id)
            .join(operations, operations.c.value["operation"].astext == obligations.c.operation_id)
            .outerjoin(discovery, discovery.c.value["population"].astext == populations.c.name)
        )
        .where(
            obligations.c.id == only_obligation if only_obligation is not None else literal(True),
            func.ops.ddo_demand_active(demands.c.id),
            or_(
                and_(selected, populations.c.selected_obligation_id == obligations.c.id),
                and_(
                    ~selected,
                    or_(
                        discovery.c.value["target"].astext == obligations.c.operation_id,
                        operations.c.value["dependencies"].bool_op("?")(
                            discovery.c.value["target"].astext
                        ),
                    ),
                ),
            ),
        )
        .distinct()
    )
    return candidates


def _population_wakes(model):
    from .native_program import core_variable

    requested = (
        func.jsonb_array_elements_text(core_variable("p_populations", JSONB()))
        .table_valued(column("value", Text()))
        .render_derived(name="wake_populations")
    )
    return _writer(
        model,
        "ddo_record_population_wakes",
        "p_populations",
        _population_candidates(model, requested),
    )


def _computation_origins(model, requested):
    """Retain exact cause IDs even when cross-demand pin recipients are uncommitted."""
    demands = model.tables["ops.data_demand"]
    origin = model.tables["ops.demand_use"]
    obligations = model.tables["ops.data_obligation"]
    source = (
        requested.join(origin, origin.c.id == requested.c.value)
        .join(obligations, obligations.c.id == origin.c.obligation_id)
        .join(demands, demands.c.id == origin.c.demand_id)
    )
    return select(
        literal("computation").label("origin_kind"),
        origin.c.id.label("origin_id"),
        demands.c.project_id,
        demands.c.id.label("demand_id"),
        obligations.c.original_source,
    ).select_from(source)


def _record_origins(model, rows):
    origins = model.tables["ops.data_binding_origin"]
    source = rows.subquery("binding_origin_source")
    return (
        insert(origins)
        .from_select(
            tuple(origins.c.keys()),
            select(
                source,
                func.clock_timestamp(),
                cast(cast(func.pg_current_xact_id(), Text), Numeric()),
                cast(func.pg_current_snapshot(), Text),
            ),
        )
        .on_conflict_do_nothing()
    )


def _writer(model, name, parameter, candidates, origins=None):
    from .native_program import core_variable

    return NativeRoutine(
        "ops",
        name,
        (Parameter(parameter, pg_type("jsonb")),),
        pg_type("int8"),
        Block(
            (
                *((Sql(_record_origins(model, origins)),) if origins is not None else ()),
                Sql(_record_wakes(model, candidates)),
                GetRowCount("inserted"),
                Return(core_variable("inserted", BigInteger())),
            ),
            (Local("inserted", pg_type("int8")),),
        ),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def _scope_candidates(
    model, *, project=None, original=None, origin_kind=None, origin_id=None, only_obligation=None
):
    from .native_program import core_variable

    demands = model.tables["ops.data_demand"]
    obligations = model.tables["ops.data_obligation"]
    definitions = model.tables["sem.data_operation_definition"]
    roles = _items(definitions.c.input_roles, "scope_wake_role").lateral()
    role = roles.c.value
    original = core_variable("p_original", Text()) if original is None else original
    origin_kind = core_variable("p_kind", Text()) if origin_kind is None else origin_kind
    frozen = demands.c.selection["source_sets"][role["support"]["source_set"].astext]
    entries = _items(
        func.coalesce(frozen["entries"], cast(literal("[]"), JSONB())), "scope_wake_source"
    )
    from_source_set = (
        select(1)
        .select_from(entries)
        .where(
            entries.c.value["original_source"].astext.is_not_distinct_from(original),
        )
        .correlate_except(entries)
        .exists()
    )
    candidates = (
        select(
            obligations.c.id.label("obligation_id"),
            origin_kind.label("origin_kind"),
            (core_variable("p_origin", Text()) if origin_id is None else origin_id).label(
                "origin_id"
            ),
            role["name"].astext.label("input_role"),
            _obj(original_source=original).label("occurrence"),
        )
        .select_from(
            demands.join(obligations, obligations.c.demand_id == demands.c.id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == demands.c.release_id,
                    definitions.c.operation_id == obligations.c.operation_id,
                ),
            )
            .join(roles, literal(True))
        )
        .where(
            demands.c.project_id
            == (core_variable("p_project", Text()) if project is None else project),
            obligations.c.id == only_obligation if only_obligation is not None else literal(True),
            func.ops.ddo_demand_active(demands.c.id),
            or_(obligations.c.original_source.is_not_distinct_from(original), from_source_set),
            or_(
                origin_kind != "rule-establishment",
                func.jsonb_array_length(
                    func.coalesce(role["required_rules"], cast(literal("[]"), JSONB()))
                )
                > 0,
            ),
        )
        .distinct()
    )
    return candidates


def _scope_wakes(model):
    from .native_program import core_variable

    candidates = _scope_candidates(model)
    origins = select(
        core_variable("p_kind", Text()).label("origin_kind"),
        core_variable("p_origin", Text()).label("origin_id"),
        core_variable("p_project", Text()).label("project_id"),
        cast(literal(None), Text).label("demand_id"),
        core_variable("p_original", Text()).label("original_source"),
    )
    return NativeRoutine(
        "ops",
        "ddo_record_scope_wakes",
        (
            Parameter("p_project", pg_type("text")),
            Parameter("p_original", pg_type("text")),
            Parameter("p_kind", pg_type("text")),
            Parameter("p_origin", pg_type("text")),
        ),
        pg_type("int8"),
        Block(
            (
                Sql(_record_origins(model, origins)),
                Sql(_record_wakes(model, candidates)),
                GetRowCount("inserted"),
                Return(core_variable("inserted", BigInteger())),
            ),
            (Local("inserted", pg_type("int8")),),
        ),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def _sparse_wake_changed(model):
    wakes = model.tables["ops.data_obligation_wake"]
    reads = model.tables["ops.data_demand_read"]
    before, after = reads.alias("wake_before"), reads.alias("wake_after")
    from .native_program import core_variable

    def visible(boundary):
        return func.ops.ddo_read_visible(
            wakes.c.created_at, cast(wakes.c.created_xid, Text), boundary.table_valued()
        )

    changed = (
        select(1)
        .select_from(wakes)
        .where(
            wakes.c.obligation_id == core_variable("p_obligation", Text()),
            or_(
                wakes.c.created_xid >= func.ops.ddo_read_xmin(before.table_valued()),
                wakes.c.created_xid == cast(before.c.owner_xid, Numeric()),
            ),
            visible(after),
            ~visible(before),
        )
        .correlate(before, after)
        .exists()
    )
    return NativeRoutine(
        "ops",
        "ddo_sparse_obligation_wake_changed",
        (
            Parameter("p_obligation", pg_type("text")),
            Parameter("p_before", pg_type("text")),
            Parameter("p_after", pg_type("text")),
        ),
        pg_type("bool"),
        select(
            func.coalesce(
                select(changed)
                .select_from(before.join(after, before.c.demand_id == after.c.demand_id))
                .where(
                    before.c.id == core_variable("p_before", Text()),
                    after.c.id == core_variable("p_after", Text()),
                )
                .scalar_subquery(),
                literal(True),
            )
        ),
        security_definer=True,
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )


def _wake_changed(model):
    from .native_program import core_variable

    reads = model.tables["ops.data_demand_read"]
    before, after = reads.alias("wake_before"), reads.alias("wake_after")
    obligation = core_variable("p_obligation", Text())
    earlier, later = core_variable("p_before", Text()), core_variable("p_after", Text())
    answer = case(
        (func.ops.ddo_sparse_obligation_wake_changed(obligation, earlier, later), True),
        else_=func.ops.ddo_unseen_binding_origin(
            obligation, before.table_valued(), after.table_valued()
        ),
    )
    return NativeRoutine(
        "ops",
        "ddo_obligation_wake_changed",
        (
            Parameter("p_obligation", pg_type("text")),
            Parameter("p_before", pg_type("text")),
            Parameter("p_after", pg_type("text")),
        ),
        pg_type("bool"),
        select(
            func.coalesce(
                select(answer)
                .select_from(before.join(after, before.c.demand_id == after.c.demand_id))
                .where(before.c.id == earlier, after.c.id == later)
                .scalar_subquery(),
                literal(True),
            )
        ),
        security_definer=True,
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )


def _origin_saw_obligation():
    def op(symbol, left, right):
        return ast.A_Expr(
            kind=enums.A_Expr_Kind.AEXPR_OP,
            name=(ast.String(sval=symbol),),
            lexpr=left,
            rexpr=right,
        )

    value = ast.BoolExpr(
        boolop=enums.BoolExprType.AND_EXPR,
        args=(
            op("<=", variable("obligation", "created_at"), variable("origin", "created_at")),
            ast.BoolExpr(
                boolop=enums.BoolExprType.OR_EXPR,
                args=(
                    op(
                        "=",
                        variable("obligation", "created_xid"),
                        ast.TypeCast(
                            arg=variable("origin", "created_xid"), typeName=pg_type("text")
                        ),
                    ),
                    call(
                        "pg_catalog",
                        "pg_visible_in_snapshot",
                        ast.TypeCast(
                            arg=variable("obligation", "created_xid"),
                            typeName=pg_type("pg_catalog", "xid8"),
                        ),
                        ast.TypeCast(
                            arg=variable("origin", "read_snapshot"),
                            typeName=pg_type("pg_catalog", "pg_snapshot"),
                        ),
                    ),
                ),
            ),
        ),
    )
    return NativeRoutine(
        "ops",
        "ddo_binding_origin_saw_obligation",
        (
            Parameter("origin", pg_type("ops", "data_binding_origin")),
            Parameter("obligation", pg_type("ops", "data_obligation")),
        ),
        pg_type("bool"),
        ast.SelectStmt(targetList=(ast.ResTarget(val=value),)),
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
    )


def _unseen_origin(model):
    """Rejoin only new cause facts whose fanout could not see this recipient.

    Existing recipients use their sparse pointer. The recovery index starts at
    the wait cut's xmin, so an older uncommitted producer remains observable.
    Rejoining is an observation of authoritative facts, never evidence of closure.
    """
    from .native_program import core_variable

    origins = model.tables["ops.data_binding_origin"]
    obligations = model.tables["ops.data_obligation"]
    demands = model.tables["ops.data_demand"]
    before = core_variable("p_before", Boolean())
    after = core_variable("p_after", Boolean())
    obligation = core_variable("p_obligation", Text())
    minimum = func.ops.ddo_read_xmin(before)
    suffix = (
        select(origins)
        .select_from(
            origins.join(obligations, obligations.c.id == obligation).join(
                demands, demands.c.id == obligations.c.demand_id
            )
        )
        .where(
            origins.c.project_id == demands.c.project_id,
            or_(
                origins.c.demand_id == obligations.c.demand_id,
                origins.c.demand_id.is_(None),
                origins.c.origin_kind == "computation",
            ),
            or_(
                origins.c.created_xid >= minimum,
                origins.c.created_xid
                == cast(core_variable("p_before", Text(), "owner_xid"), Numeric()),
            ),
            func.ops.ddo_read_visible(
                origins.c.created_at, cast(origins.c.created_xid, Text), after
            ),
            ~func.ops.ddo_read_visible(
                origins.c.created_at, cast(origins.c.created_xid, Text), before
            ),
            ~func.ops.ddo_binding_origin_saw_obligation(
                origins.table_valued(), obligations.table_valued()
            ),
        )
        .cte("unseen_origin_suffix")
        .prefix_with("MATERIALIZED")
    )

    def requested(kind):
        return (
            select(suffix.c.origin_id.label("value"))
            .where(suffix.c.origin_kind == kind)
            .subquery("recover_" + kind)
        )

    checks = [
        select(1)
        .select_from(builder(model, requested(kind), only_obligation=obligation).subquery())
        .exists()
        for kind, builder in (("computation", _computation_candidates),)
    ]
    scope = (
        _scope_candidates(
            model,
            project=suffix.c.project_id,
            original=suffix.c.original_source,
            origin_kind=suffix.c.origin_kind,
            origin_id=suffix.c.origin_id,
            only_obligation=obligation,
        )
        .where(suffix.c.demand_id.is_(None))
        .subquery("recover_scope")
    )
    checks.append(select(1).select_from(scope).exists())
    return NativeRoutine(
        "ops",
        "ddo_unseen_binding_origin",
        (
            Parameter("p_obligation", pg_type("text")),
            Parameter("p_before", pg_type("ops", "data_demand_read")),
            Parameter("p_after", pg_type("ops", "data_demand_read")),
        ),
        pg_type("bool"),
        select(or_(*checks)).add_cte(suffix),
        security_definer=True,
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )


def obligation_wake_programs(model: MetaData):
    xmin = ast.TypeCast(
        arg=ast.TypeCast(
            arg=call(
                "pg_catalog",
                "pg_snapshot_xmin",
                ast.TypeCast(
                    arg=variable("boundary", "read_snapshot"),
                    typeName=pg_type("pg_catalog", "pg_snapshot"),
                ),
            ),
            typeName=pg_type("text"),
        ),
        typeName=pg_type("numeric"),
    )
    minimum = NativeRoutine(
        "ops",
        "ddo_read_xmin",
        (Parameter("boundary", pg_type("ops", "data_demand_read")),),
        pg_type("numeric"),
        ast.SelectStmt(targetList=(ast.ResTarget(val=xmin),)),
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:binding-wakes",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in (
            minimum,
            _origin_saw_obligation(),
            _unseen_origin(model),
            _sparse_wake_changed(model),
            _wake_changed(model),
            _computation_wakes(model),
            _original_wakes(model),
            _population_wakes(model),
            _scope_wakes(model),
        )
    )
