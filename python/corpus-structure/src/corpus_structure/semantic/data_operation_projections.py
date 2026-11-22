"""Core-owned demand-scoped native read shapes and support closure.

Prepared SQL is captured alongside its explicit physical input closure. Runtime
reconstruction consumes those bytes rather than invoking current builders.
"""

from __future__ import annotations

from typing import Any

from pglast import ast
from sqlalchemy import (
    BigInteger,
    Boolean,
    Text,
    and_,
    case,
    cast,
    column,
    exists,
    false,
    func,
    literal,
    null,
    or_,
    select,
    union,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import NullType

from .data_operation_jsonb import ContextJSONB
from .native_program import core_cast_literal, core_reference, pg_type


def _pg_text_array():
    definition = pg_type("text")
    definition.arrayBounds = (ast.Integer(ival=-1),)
    return definition


def _json(value):
    import json

    return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB)


def _var[T](name: str, kind: type[TypeEngine[T]]) -> ColumnClause[T]:
    return core_reference(*name.split("."), type_=kind())


def _items(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _each(value, name):
    return (
        func.jsonb_each(value)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .render_derived(name=name)
    )


def _obj(**values):
    return func.jsonb_build_object(
        *(part for key, value in values.items() for part in (literal(key), value))
    )


def _aggregate(value, *order):
    expression = aggregate_order_by(value, *order) if order else value
    return func.coalesce(func.jsonb_agg(expression), _json([]))


def _requested_read_scope():
    # Optional JSON properties yield SQL NULL, rather than an empty object.
    # Normalize that omission before predicates such as NOT(scope ? 'key');
    # otherwise three-valued SQL logic filters the whole unscoped frontier.
    return func.coalesce(_var("p", JSONB)["scope"], _json({}))


def _public_read():
    """Disclosure is immutable acquisition custody, independent of the reopening role."""
    return _var("boundary.public_disclosure", Boolean)


def _public_authority_leaf(identity):
    return and_(_public_read(), func.ops.ddo_policy_authority_leaf(identity))


def _kind_disclosed(metadata, kind):
    kinds = metadata.tables["sem.data_kind_contract"]
    disclosed = exists(
        select(1)
        .select_from(kinds)
        .where(
            kinds.c.kind_contract == kind,
            kinds.c.universe.in_(("ordinary", "source")),
        )
    )
    return or_(~_public_read(), disclosed)


def _disclosed_kind_access(metadata, kind):
    # Authorization refuses with an exception. SQL AND order cannot protect it
    # from unrelated hidden rows, so establish immutable disclosure eligibility
    # before invoking the native capability check.
    return case(
        (_kind_disclosed(metadata, kind), func.ops.ddo_kind_access(kind)),
        else_=literal(False),
    )


def _disclosed_body_access(metadata, kind, body):
    return case(
        (_kind_disclosed(metadata, kind), func.ops.ddo_body_access(kind, body)),
        else_=literal(False),
    )


def _support_export_body_access(metadata, products, product_ids):
    # Hidden roots have no body in public support output. Keep their capability
    # checks out of the aggregate that governs the disclosed body records.
    access = case(
        (
            _kind_disclosed(metadata, products.c.kind_contract),
            func.ops.ddo_body_access(products.c.kind_contract, products.c.canonical_body),
        ),
        else_=literal(True),
    )
    return (
        select(func.coalesce(func.bool_and(access), literal(True)))
        .where(products.c.id.in_(select(product_ids.c.product_id)))
        .scalar_subquery()
    )


def _custody_body_eligible(metadata, kind, body):
    """Authenticate identity-only material within the original acquisition's universes."""
    kinds = metadata.tables["sem.data_kind_contract"]
    nested = (
        func.ops.ddo_body_kind_contracts(kind, body)
        .table_valued(column("kind_contract", Text))
        .render_derived(name="custody_body_kind")
    )
    outside_acquisition = exists(
        select(1)
        .select_from(nested.outerjoin(kinds, kinds.c.kind_contract == nested.c.kind_contract))
        .where(
            or_(
                kinds.c.kind_contract.is_(None),
                ~func.coalesce(
                    _var("boundary.access_universes", JSONB).bool_op("?")(kinds.c.universe),
                    False,
                ),
            )
        )
    )
    return and_(_kind_disclosed(metadata, kind), ~outside_acquisition)


def _visible(table):
    return func.ops.ddo_read_visible(
        table.c.created_at, table.c.created_xid, core_reference("boundary", type_=NullType())
    )


def _node(kind, identity):
    kind_value = literal(kind) if isinstance(kind, str) else kind
    return select(cast(kind_value, Text).label("kind"), cast(identity, Text).label("id"))


def _validity_rows(
    seed_uses, seed_episodes=None, *, name="validity", boundary=None, seed_populations=None
):
    from sqlalchemy.dialects.postgresql import ARRAY

    empty = cast(literal("{}"), ARRAY(Text))
    rows = (
        func.ops.ddo_valid_closure(
            empty if seed_uses is None else seed_uses,
            empty if seed_episodes is None else seed_episodes,
            core_reference("boundary", type_=NullType()) if boundary is None else boundary,
            empty if seed_populations is None else seed_populations,
        )
        .table_valued(column("kind", Text), column("id", Text), column("valid", Boolean))
        .alias(name + "_rows")
    )
    return select(rows).cte(name).prefix_with("MATERIALIZED")


def _set_valid(rows, kind, identity):
    return exists(
        select(1).select_from(rows).where(rows.c.kind == kind, rows.c.id == identity, rows.c.valid)
    )


def _support_walk(metadata, seed, *, public=False, name="support_closure"):
    """Visit declared finite edges through indexed per-node lookups."""
    from .support_edges import support_edge_queries

    closure = select(seed.c.kind, seed.c.id).where(seed.c.id.is_not(None)).cte(name, recursive=True)
    queries = support_edge_queries(
        metadata,
        closure.c.kind,
        closure.c.id,
        "public" if public else "scope",
        authority=_public_authority_leaf if public else None,
        boundary=core_reference("boundary", type_=NullType()),
        product_ids=_requested_read_scope()["product_ids"],
    )
    edges = union_all(*(query.correlate(closure) for query in queries)).lateral("support_edge")
    return closure.union(
        select(edges.c.child_kind.label("kind"), edges.c.child_id.label("id"))
        .select_from(closure.join(edges, literal(True)))
        .where(edges.c.child_id.is_not(None))
    )


def _scope_projection(
    metadata, nodes, project, direct_sources, *, domain_dependencies=True, domain_only=False
):
    episodes = metadata.tables["ops.data_derivation"]
    requests = metadata.tables["ops.data_request"]
    admissions = metadata.tables["ops.original_source_admission"]
    sources = union(
        direct_sources,
        select(requests.c.original_source.label("source"))
        .select_from(
            nodes.join(episodes, and_(nodes.c.kind == "episode", episodes.c.id == nodes.c.id)).join(
                requests, requests.c.id == episodes.c.request_id
            )
        )
        .where(requests.c.project_id == project),
        select(admissions.c.original_source.label("source"))
        .select_from(
            nodes.join(admissions, and_(nodes.c.kind == "original", admissions.c.id == nodes.c.id))
        )
        .where(admissions.c.project_id == project),
    ).cte("support_sources")
    scope = func.ops.ddo_scope(project, sources.c.source)
    ordinary = select(scope.label("scope"))
    if not domain_dependencies:
        return ordinary.order_by(scope)

    def domain_scopes(function, alias):
        scopes = (
            function(episodes.c.id).table_valued(column("scope", Text())).render_derived(name=alias)
        )
        return (
            select(scopes.c.scope)
            .select_from(
                nodes.join(episodes, and_(nodes.c.kind == "episode", episodes.c.id == nodes.c.id))
                .join(requests, requests.c.id == episodes.c.request_id)
                .join(scopes, literal(True))
            )
            .where(requests.c.project_id == project)
        )

    return union(
        *(() if domain_only else (ordinary,)),
        domain_scopes(func.ops.ddo_record_grade_dependency_scopes, "record_grade_scope"),
        domain_scopes(func.ops.ddo_record_fit_dependency_scopes, "record_fit_scope"),
        domain_scopes(func.ops.ddo_operation_event_dependency_scopes, "operation_event_scope"),
    ).order_by("scope")


def _demand_support_scope_inputs(metadata, *, include_unfulfilled=False):
    """One frozen demand seed and finite support walk for native read consumers."""
    demand, project = _var("d.id", Text), _var("d.project_id", Text)
    selection = _var("d.selection", JSONB)
    root = _items(_var("d.root", JSONB), "root")
    sets = _each(func.coalesce(selection["source_sets"], _json({})), "source_set")
    entry = _items(sets.c.value["entries"], "source_entry")
    source_entries = (
        select(entry.c.value.label("entry"), sets.c.value.label("source_set"))
        .select_from(sets.join(entry, literal(True)))
        .cte("source_entries")
    )
    uses = metadata.tables["ops.demand_use"]
    populations = metadata.tables["ops.data_population"]
    episodes = metadata.tables["ops.data_derivation"]
    outputs = metadata.tables["ops.data_derivation_output"]
    requests = metadata.tables["ops.data_request"]
    admissions = metadata.tables["ops.original_source_admission"]
    selected_uses = (
        select(uses.c.obligation_id, uses.c.id, uses.c.fate)
        .where(uses.c.demand_id == demand, _visible(uses))
        .distinct(uses.c.obligation_id)
        .order_by(uses.c.obligation_id, uses.c.created_at.desc(), uses.c.id.desc())
        .cte("selected_use_seeds")
    )
    selected_source = exists(
        select(1)
        .select_from(source_entries)
        .where(
            source_entries.c.entry["product"].astext == outputs.c.product_id,
            func.ops.ddo_source_set_proof_matches(
                source_entries.c.source_set,
                outputs.c.product_id,
                source_entries.c.entry["member"].astext,
                episodes.c.id,
                uses.c.id,
                _obj(
                    member_id=outputs.c.member_id,
                    role=outputs.c.role,
                    position=outputs.c.position,
                    multiplicity=outputs.c.multiplicity,
                ),
            ),
        )
    )
    seed = union(
        _node("use", selected_uses.c.id).where(
            literal(True) if include_unfulfilled else selected_uses.c.fate == "fulfilled"
        ),
        _node("population", populations.c.id).where(
            populations.c.demand_id == demand, _visible(populations)
        ),
        _node("use", uses.c.id)
        .select_from(
            episodes.join(outputs, outputs.c.derivation_id == episodes.c.id)
            .join(uses, uses.c.derivation_id == episodes.c.id)
            .join(requests, requests.c.id == episodes.c.request_id)
        )
        .where(
            requests.c.project_id == project,
            selected_source,
            uses.c.fate == "fulfilled",
            _visible(uses),
        ),
        _node("original", admissions.c.id).where(
            admissions.c.demand_id == demand, _visible(admissions)
        ),
    ).cte("support_seed")
    direct = union(
        select(root.c.value["original_source"].astext.label("source")),
        select(source_entries.c.entry["original_source"].astext),
    ).cte("direct_sources")
    return _support_walk(metadata, seed), select(direct.c.source)


def cancellation_scopes(metadata):
    """Current structural closure plus every actually recorded settlement scope.

    Recorded snapshots include domain cut scopes even when a historical cut now
    requires reacquisition. Cancellation withdraws interest; it need not validate
    or rehabilitate those historical products to acquire their trust barrier.
    """
    nodes, direct = _demand_support_scope_inputs(metadata, include_unfulfilled=True)
    ordinary = _scope_projection(
        metadata, nodes, _var("d.project_id", Text), direct, domain_dependencies=False
    )
    uses = metadata.tables["ops.demand_use"]
    retained = (
        func.jsonb_object_keys(uses.c.trust_snapshot)
        .table_valued(column("scope", Text))
        .render_derived(name="retained_settlement_scope")
    )
    return union(
        ordinary,
        select(retained.c.scope)
        .select_from(uses.join(retained, literal(True)))
        .where(uses.c.demand_id == _var("d.id", Text)),
    ).order_by("scope")


def read_scope_rows(metadata):
    """Retain each scope's exact ordinary/domain provenance at acquisition."""
    nodes, direct = _demand_support_scope_inputs(metadata, include_unfulfilled=True)
    args = (metadata, nodes, _var("d.project_id", Text), direct)
    ordinary = _scope_projection(*args, domain_dependencies=False).subquery("ordinary_read_scopes")
    domain = _scope_projection(*args, domain_only=True).subquery("domain_read_scopes")
    origins = union_all(
        select(ordinary.c.scope, literal(True).label("ordinary"), literal(False).label("domain")),
        select(domain.c.scope, literal(False).label("ordinary"), literal(True).label("domain")),
    ).subquery("read_scope_origins")
    return (
        select(
            origins.c.scope,
            func.bool_or(origins.c.ordinary).label("ordinary"),
            func.bool_or(origins.c.domain).label("domain"),
        )
        .group_by(origins.c.scope)
        .order_by(origins.c.scope)
    )


def read_access_universes(metadata):
    """Pin the universes of the exact disclosed support and unresolved roots.

    Authentication uses the same authority cut as support export. An evaluator
    still receives complete issuer provenance through that walk. Ordinary readers
    receive the authenticated conclusion and explicitly disclosed report edge.
    """
    obligations = _scoped_read_obligations(metadata).cte("access_scoped_obligations")
    latest = _latest_read_use(metadata, obligations)
    selected_uses = (
        select(latest)
        .select_from(obligations.join(latest, literal(True)))
        .cte("access_selected_uses")
    )
    products = metadata.tables["kb.data_product"]
    inputs = metadata.tables["ops.data_derivation_input"]
    outputs = metadata.tables["ops.data_derivation_output"]
    admissions = metadata.tables["ops.original_source_admission"]
    kinds = metadata.tables["sem.data_kind_contract"]
    in_scope = _original_in_read_context(admissions, obligations)
    seed = _read_support_seed(metadata, selected_uses, admissions, in_scope)
    nodes = _support_walk(metadata, seed, public=True)
    episode_ids = select(nodes.c.id).where(nodes.c.kind == "episode")
    authority_ids = select(nodes.c.id).where(nodes.c.kind == "authority")
    reached = union(
        select(inputs.c.product_id).where(inputs.c.derivation_id.in_(episode_ids)),
        select(outputs.c.product_id).where(outputs.c.derivation_id.in_(episode_ids)),
        select(outputs.c.product_id).where(outputs.c.derivation_id.in_(authority_ids)),
        select(admissions.c.product_id).select_from(
            nodes.join(admissions, and_(nodes.c.kind == "original", nodes.c.id == admissions.c.id))
        ),
    ).cte("access_products")
    nested = (
        func.ops.ddo_body_kind_contracts(products.c.kind_contract, products.c.canonical_body)
        .table_valued(column("kind_contract", Text))
        .render_derived(name="nested_access_kind")
    )
    observed = select(kinds.c.universe).select_from(
        reached.join(products, products.c.id == reached.c.product_id)
        .join(nested, literal(True))
        .join(kinds, kinds.c.kind_contract == nested.c.kind_contract)
    )
    definitions = metadata.tables["sem.data_operation_definition"]
    roles = _items(definitions.c.input_roles.op("||")(definitions.c.output_roles), "access_role")
    authenticated_conclusion = exists(
        select(1)
        .select_from(selected_uses)
        .where(
            selected_uses.c.obligation_id == obligations.c.id,
            selected_uses.c.fate == "fulfilled",
            _public_authority_leaf(selected_uses.c.derivation_id),
        )
        .correlate(obligations)
    )
    declared = (
        select(kinds.c.universe)
        .select_from(
            obligations.join(
                definitions,
                and_(
                    definitions.c.operation_id == obligations.c.operation_id,
                    definitions.c.release_id == _var("d.release_id", Text),
                ),
            )
            .join(roles, literal(True))
            .join(kinds, kinds.c.kind_contract == roles.c.value["kind_contract"].astext)
        )
        .where(~authenticated_conclusion)
    )
    universes = union(observed, declared).subquery("acquired_access_universes")
    return select(func.coalesce(func.jsonb_agg(universes.c.universe), _json([])))


def record_grade_census_nodes(metadata):
    """Inspect the actual frozen census graph without recursive validity calls."""
    nodes, _ = _demand_support_scope_inputs(metadata, include_unfulfilled=True)
    return select(nodes.c.kind, nodes.c.id)


def lock_support_scopes(metadata):
    reference = _items(_var("support", JSONB), "root_support_reference")
    from .support_edges import support_reference_node

    kind, identity = support_reference_node(reference.c.value)
    seed = _node(kind, identity).select_from(reference).cte("support_seed")
    return _scope_projection(
        metadata,
        _support_walk(metadata, seed),
        _var("project", Text),
        select(_var("source", Text).label("source")),
    )


def binding_row_contract():
    """The labeled result SELECT is the native/Python row-shape authority."""
    fields: tuple[tuple[str, TypeEngine[Any]], ...] = (
        ("product", Text()),
        ("kind_contract", Text()),
        ("subject", Text()),
        ("subject_definition", Text()),
        ("original_source", Text()),
        ("analyzed_scope", JSONB()),
        ("coverage", JSONB()),
        ("support_episodes", JSONB()),
        ("support_references", JSONB()),
        ("support_evidence", JSONB()),
        ("position", BigInteger()),
        ("multiplicity", BigInteger()),
        ("member", Text()),
        ("provider_identity", Text()),
        ("alternative_identity", Text()),
        ("body", JSONB()),
        ("meaning_body", JSONB()),
    )
    return select(*(column(name, kind).label(name) for name, kind in fields))


def binding_columns(*, decoder=False):
    return tuple(
        column(
            item.name,
            ContextJSONB()
            if decoder and item.name in {"analyzed_scope", "support_evidence"}
            else item.type,
        )
        for item in binding_row_contract().selected_columns
    )


def member_columns():
    return tuple(
        item.name for item in binding_columns() if item.name not in {"body", "meaning_body"}
    )


def binding_branches(metadata):
    demand, project, release = (
        _var("d.id", Text),
        _var("d.project_id", Text),
        _var("d.release_id", Text),
    )
    selection = _var("d.selection", JSONB)
    operation_id, subject = _var("p_operation", Text), _var("p_subject", Text)
    source_filter = _var("p_source", JSONB)
    source = cast(source_filter.op("#>>")(literal("{}")), Text)
    scope = _var("p_scope", JSONB)
    selected = _var("p_selected", JSONB)

    def source_matches(roledef, header):
        return or_(
            and_(source_filter.is_(None), roledef["support"]["source_set"].astext.is_(None)),
            func.ops.ddo_binding_source(
                roledef, header, source, func.coalesce(selection["source_sets"], _json({}))
            ),
        )

    def selected_key(product, member=None):
        requested = _items(selected, "selected_binding_key")
        predicates = [requested.c.value["product_id"].astext == product]
        if member is not None:
            predicates.append(requested.c.value["member_id"].astext.is_not_distinct_from(member))
        return or_(
            selected.is_(None),
            exists(select(1).select_from(requested).where(*predicates).correlate_except(requested)),
        )

    def decoded(value):
        return case((_var("p_decode_body", Boolean), func.data.ddo_json(value)), else_=null())

    boundary = core_reference("boundary", type_=NullType())
    definitions = metadata.tables["sem.data_operation_definition"]
    roles = _items(definitions.c.input_roles, "input_role")
    entries = _items(
        func.coalesce(
            selection["source_sets"][roles.c.value["support"]["source_set"].astext]["entries"],
            _json([]),
        ),
        "entry",
    )
    pins = (
        select(
            entries.c.value.label("entry"),
            selection["source_sets"][roles.c.value["support"]["source_set"].astext].label(
                "source_set"
            ),
        )
        .select_from(definitions.join(roles, literal(True)).join(entries, literal(True)))
        .where(
            definitions.c.release_id == release,
            definitions.c.operation_id == operation_id,
        )
        .cte("declared_pins")
        .prefix_with("MATERIALIZED")
    )
    uses = metadata.tables["ops.demand_use"].alias("u")
    episodes = metadata.tables["ops.data_derivation"].alias("episode")
    requests = metadata.tables["ops.data_request"].alias("producer")
    outputs = metadata.tables["ops.data_derivation_output"].alias("outp")
    products = metadata.tables["kb.data_product"].alias("x")
    members = metadata.tables["kb.data_product_member"].alias("m")
    later = metadata.tables["ops.demand_use"].alias("later")
    selected_operations = _items(selection["operations"], "selected_operation")
    exact_pin = exists(
        select(1)
        .select_from(pins)
        .where(
            pins.c.entry["product"].astext == products.c.id,
            func.ops.ddo_source_set_proof_matches(
                pins.c.source_set,
                products.c.id,
                pins.c.entry["member"].astext,
                episodes.c.id,
                uses.c.id,
                _obj(
                    member_id=outputs.c.member_id,
                    role=outputs.c.role,
                    position=outputs.c.position,
                    multiplicity=outputs.c.multiplicity,
                ),
            ),
            or_(
                and_(pins.c.entry["member"].astext.is_(None), outputs.c.member_id.is_(None)),
                and_(
                    pins.c.entry["member"].astext.is_not(None),
                    or_(
                        outputs.c.member_id.is_(None),
                        outputs.c.member_id == pins.c.entry["member"].astext,
                    ),
                ),
            ),
        )
    )
    allowed_producer = exists(
        select(1)
        .select_from(selected_operations)
        .where(
            selected_operations.c.value["operation"].astext == operation_id,
            or_(
                func.jsonb_array_length(selected_operations.c.value["dependencies"]) == 0,
                requests.c.operation_id
                == func.any(func.ops.ddo_consumed_producers(selection, operation_id)),
            ),
        )
    )
    later_exists = exists(
        select(1)
        .select_from(later)
        .where(
            later.c.obligation_id == uses.c.obligation_id,
            or_(
                later.c.created_at > uses.c.created_at,
                and_(later.c.created_at == uses.c.created_at, later.c.id > uses.c.id),
            ),
            _visible(later),
        )
    )
    admitted_base = (
        select(
            products.c.id.label("product_id"),
            products.c.kind_contract.label("parent_kind"),
            products.c.subject.label("parent_subject"),
            products.c.subject_definition.label("parent_subject_definition"),
            products.c.original_source.label("parent_source"),
            products.c.analyzed_scope.label("parent_scope"),
            products.c.canonical_body,
            outputs.c.member_id.label("output_member"),
            outputs.c.role.label("output_role"),
            outputs.c.position.label("output_position"),
            outputs.c.multiplicity.label("output_multiplicity"),
            episodes.c.id.label("episode_id"),
            uses.c.id.label("use_id"),
            requests.c.operation_id.label("producer_operation"),
        )
        .select_from(
            uses.join(episodes, episodes.c.id == uses.c.derivation_id)
            .join(requests, requests.c.id == episodes.c.request_id)
            .join(outputs, outputs.c.derivation_id == episodes.c.id)
            .join(products, products.c.id == outputs.c.product_id)
        )
        .where(
            uses.c.fate == "fulfilled",
            products.c.project_id == project,
            selected_key(products.c.id),
            _visible(uses),
            # A role-scoped explicit pin selects genuine input provenance;
            # production dependencies constrain default acquisition, not that
            # independent source workflow. Role/header/access checks below and
            # the selected read/support validity above still apply to both.
        )
    )
    # Preserve exact pins from other demands without an OR across the keyed
    # demand-use and product/member access paths. UNION removes a use reached
    # by both arms without discarding distinct emitting outputs.
    admitted = (
        union(
            admitted_base.where(uses.c.demand_id == demand, allowed_producer, ~later_exists),
            admitted_base.where(exact_pin),
        )
        .cte("admitted")
        .prefix_with("MATERIALIZED")
    )
    projected = union_all(
        select(
            cast(null(), Text).label("member_id"),
            admitted.c.parent_kind.label("projected_kind"),
            admitted.c.parent_subject.label("projected_subject"),
            admitted.c.parent_subject_definition.label("projected_subject_definition"),
            admitted.c.parent_source.label("projected_source"),
            admitted.c.parent_scope.label("projected_scope"),
            admitted.c.canonical_body.label("projected_body"),
        )
        .where(admitted.c.output_member.is_(None))
        .correlate(admitted),
        select(
            members.c.member_id,
            members.c.kind_contract,
            members.c.subject,
            members.c.subject_definition,
            members.c.original_source,
            members.c.analyzed_scope,
            members.c.body,
        )
        .where(
            members.c.product_id == admitted.c.product_id,
            or_(
                admitted.c.output_member.is_(None), admitted.c.output_member == members.c.member_id
            ),
        )
        .correlate(admitted),
    ).lateral("projected")
    header = _obj(subject=projected.c.projected_subject, meaning_body=projected.c.projected_body)
    full_header = _obj(
        product=admitted.c.product_id,
        member=projected.c.member_id,
        subject=projected.c.projected_subject,
        subject_definition=projected.c.projected_subject_definition,
        original_source=projected.c.projected_source,
        analyzed_scope=projected.c.projected_scope,
        meaning_body=projected.c.projected_body,
        support_references=func.jsonb_build_array(
            _obj(
                kind=literal("computation"),
                derivation_id=admitted.c.episode_id,
                admission_use_id=admitted.c.use_id,
            )
        ),
        support_evidence=_obj(
            member_body_identity=case(
                (
                    projected.c.member_id.is_not(None),
                    func.data.ddo_identity(
                        "body", func.data.ddo_normalize(projected.c.projected_body)
                    ),
                ),
                else_=null(),
            ),
            producer_output=_obj(
                member_id=admitted.c.output_member,
                role=admitted.c.output_role,
                position=admitted.c.output_position,
                multiplicity=admitted.c.output_multiplicity,
            ),
        ),
    )
    admitted_role = exists(
        select(1)
        .select_from(definitions.join(roles, literal(True)))
        .where(
            definitions.c.release_id == release,
            definitions.c.operation_id == operation_id,
            case(
                (
                    and_(
                        roles.c.value["accepted_kind_contracts"].op("?")(
                            projected.c.projected_kind
                        ),
                        func.coalesce(
                            roles.c.value["support"]["origins"], _json(["computation"])
                        ).op("?")(literal("computation")),
                        or_(
                            scope.is_(None),
                            roles.c.value["subject_field"].astext.is_not(None),
                            roles.c.value["subject_target"].astext == "source-set",
                            projected.c.projected_scope.is_not_distinct_from(scope),
                        ),
                    ),
                    case(
                        (
                            and_(
                                func.ops.ddo_kind_access(admitted.c.parent_kind),
                                func.ops.ddo_body_access(
                                    projected.c.projected_kind, projected.c.projected_body
                                ),
                            ),
                            and_(
                                or_(
                                    subject.is_(None),
                                    func.ops.ddo_binding_subject(
                                        roles.c.value, header, subject, source
                                    ),
                                ),
                                source_matches(roles.c.value, full_header),
                            ),
                        ),
                        else_=literal(False),
                    ),
                ),
                else_=literal(False),
            ),
        )
    )
    candidates = (
        select(
            *admitted.c,
            *projected.c,
        )
        .select_from(admitted.join(projected, literal(True)))
        .where(admitted_role, selected_key(admitted.c.product_id, projected.c.member_id))
        .cte("candidates")
        .prefix_with("MATERIALIZED")
    )
    candidate_validity = _validity_rows(
        select(
            func.coalesce(
                func.array_agg(candidates.c.use_id.distinct()), cast(literal("{}"), ARRAY(Text))
            )
        ).scalar_subquery(),
        name="candidate_validity",
    )
    from .producer_correspondence_native import selected_producer_contract

    evidence = _obj(
        member_body_identity=case(
            (
                candidates.c.member_id.is_not(None),
                func.data.ddo_identity(
                    "body", func.data.ddo_normalize(candidates.c.projected_body)
                ),
            ),
            else_=null(),
        ),
        product_validation=func.ops.ddo_product_validation(
            candidates.c.episode_id, candidates.c.product_id
        ),
        producer_output=_obj(
            member_id=candidates.c.output_member,
            role=candidates.c.output_role,
            position=candidates.c.output_position,
            multiplicity=candidates.c.output_multiplicity,
        ),
        producer_contract=selected_producer_contract(
            metadata,
            candidates,
            body_eligible=lambda kind, body: _custody_body_eligible(metadata, kind, body),
            body_access=lambda kind, body: _disclosed_body_access(metadata, kind, body),
        ),
        demand_id=demand,
        use_id=candidates.c.use_id,
        trust_snapshot=_var("snapshot", JSONB),
        read_id=_var("boundary.id", Text),
        read_snapshot=_var("boundary.read_snapshot", Text),
        frontier_at=core_reference("boundary", "frontier_at", type_=NullType()),
    )
    computed_values = (
        candidates.c.product_id,
        candidates.c.projected_kind,
        candidates.c.projected_subject,
        candidates.c.projected_subject_definition,
        candidates.c.projected_source,
        candidates.c.projected_scope,
        _json([]),
        func.jsonb_build_array(candidates.c.episode_id),
        func.jsonb_build_array(
            _obj(
                kind=literal("computation"),
                derivation_id=candidates.c.episode_id,
                admission_use_id=candidates.c.use_id,
            )
        ),
        evidence,
        cast(candidates.c.output_position, BigInteger),
        cast(candidates.c.output_multiplicity, BigInteger),
        candidates.c.member_id,
        func.ops.ddo_episode_provider_identity(candidates.c.episode_id),
        candidates.c.producer_operation,
        decoded(candidates.c.projected_body),
        candidates.c.projected_body,
    )
    computed = select(
        *(
            cast(value, field.type).label(field.name)
            for field, value in zip(binding_columns(), computed_values, strict=True)
        )
    ).where(
        _set_valid(candidate_validity, "use", candidates.c.use_id),
        func.ops.ddo_episode_current_valid(candidates.c.episode_id, release, type_=Boolean()),
        func.ops.ddo_kind_access(candidates.c.parent_kind),
        func.ops.ddo_body_access(candidates.c.projected_kind, candidates.c.projected_body),
    )
    admissions = metadata.tables["ops.original_source_admission"].alias("admission")
    fact_origin = case(
        (admissions.c.reference["kind"].astext == "authored-fact", literal("authored")),
        else_=literal("original-source"),
    )
    factual_header = _obj(
        product=admissions.c.product_id,
        member=cast(null(), Text),
        subject=admissions.c.subject,
        subject_definition=products.c.subject_definition,
        original_source=admissions.c.original_source,
        analyzed_scope=admissions.c.analyzed_scope,
        meaning_body=products.c.canonical_body,
    )
    factual_role = exists(
        select(1)
        .select_from(definitions.join(roles, literal(True)))
        .where(
            definitions.c.release_id == release,
            definitions.c.operation_id == operation_id,
            case(
                (
                    and_(
                        roles.c.value["accepted_kind_contracts"].op("?")(products.c.kind_contract),
                        func.coalesce(
                            roles.c.value["support"]["origins"], _json(["computation"])
                        ).op("?")(fact_origin),
                        or_(
                            scope.is_(None),
                            roles.c.value["subject_field"].astext.is_not(None),
                            roles.c.value["subject_target"].astext == "source-set",
                            admissions.c.analyzed_scope.is_not_distinct_from(scope),
                        ),
                        source_matches(roles.c.value, factual_header),
                    ),
                    case(
                        (
                            func.ops.ddo_body_access(
                                products.c.kind_contract, products.c.canonical_body
                            ),
                            or_(
                                subject.is_(None),
                                func.ops.ddo_binding_subject(
                                    roles.c.value, factual_header, subject, source
                                ),
                            ),
                        ),
                        else_=literal(False),
                    ),
                ),
                else_=literal(False),
            ),
        )
    )
    fact = (
        select(
            *admissions.c,
            products.c.kind_contract,
            products.c.subject_definition,
            products.c.canonical_body,
        )
        .select_from(admissions.join(products, products.c.id == admissions.c.product_id))
        .where(
            admissions.c.demand_id == demand,
            admissions.c.project_id == project,
            _visible(admissions),
            func.ops.ddo_original_admission_valid(admissions.table_valued(), boundary),
            factual_role,
            selected_key(admissions.c.product_id, cast(null(), Text)),
        )
        .cte("factual")
        .prefix_with("MATERIALIZED")
    )
    refs = _aggregate(
        _obj(
            kind=case(
                (fact.c.reference["kind"].astext == "authored-fact", literal("authored")),
                else_=literal("original-source"),
            ),
            admission_id=fact.c.id,
            source_reference=fact.c.source_reference,
        ),
        fact.c.id,
    )
    factual_evidence = _obj(
        demand_id=demand,
        original_admissions=_aggregate(fact.c.id, fact.c.id),
        trust_snapshot=_var("snapshot", JSONB),
        read_id=_var("boundary.id", Text),
        read_snapshot=_var("boundary.read_snapshot", Text),
        frontier_at=core_reference("boundary", "frontier_at", type_=NullType()),
    )
    original_values = (
        fact.c.product_id,
        fact.c.kind_contract,
        fact.c.subject,
        fact.c.subject_definition,
        fact.c.original_source,
        fact.c.analyzed_scope,
        _json([]),
        _json([]),
        refs,
        factual_evidence,
        literal(0),
        literal(1),
        null(),
        null(),
        null(),
        decoded(fact.c.canonical_body),
        fact.c.canonical_body,
    )
    original = (
        select(
            *(
                cast(value, field.type).label(field.name)
                for field, value in zip(binding_columns(), original_values, strict=True)
            )
        )
        .where(func.ops.ddo_body_access(fact.c.kind_contract, fact.c.canonical_body))
        .group_by(
            fact.c.product_id,
            fact.c.kind_contract,
            fact.c.subject,
            fact.c.subject_definition,
            fact.c.original_source,
            fact.c.analyzed_scope,
            fact.c.canonical_body,
        )
    )
    return computed, original


def _original_in_read_context(admissions, obligations):
    return or_(
        exists(
            select(1)
            .select_from(obligations)
            .where(
                obligations.c.subject == admissions.c.subject,
                obligations.c.original_source.is_not_distinct_from(admissions.c.original_source),
                obligations.c.analyzed_scope == admissions.c.analyzed_scope,
            )
        ),
        ~exists(select(1).select_from(obligations)),
    )


def _read_original_predicates(admissions, in_page):
    return (
        admissions.c.demand_id == _var("d.id", Text),
        in_page,
        _visible(admissions),
        *(
            or_(
                ~_requested_read_scope().op("?")(literal(name)),
                admissions.c[name].is_not_distinct_from(_requested_read_scope()[name].astext),
            )
            for name in ("subject", "original_source")
        ),
        or_(
            ~_requested_read_scope().op("?")(literal("product_ids")),
            exists(
                select(1)
                .select_from(
                    _items(_requested_read_scope()["product_ids"], "scope_original_product")
                )
                .where(
                    core_reference("scope_original_product", "value", type_=JSONB()).op("#>>")(
                        core_cast_literal("{}", _pg_text_array())
                    )
                    == admissions.c.product_id
                )
            ),
        ),
    )


def _read_support_seed(metadata, selected_uses, admissions, in_page):
    """Select exact uses and original facts before the public authority cut."""
    return union(
        _node("use", selected_uses.c.id),
        _node("original", admissions.c.id).where(*_read_original_predicates(admissions, in_page)),
    ).cte("export_support_seed")


def selected_support_export(metadata, selected_uses, admissions, in_page):
    """Export the finite selected witness closure, including nonreturned intermediates.

    Selection and current trust stay in the native acquisition owner. This is a
    derived projection over exact retained use/episode/population/original IDs.
    Body access checks apply to every product and member, including intermediates.
    """
    whole = _var("p", JSONB)["support_scope"].astext == "read"
    scoped = _scoped_read_obligations(metadata).cte("export_scoped_obligations")
    latest = _latest_read_use(metadata, scoped)
    seeds = union(
        select(selected_uses.c.id).where(~func.coalesce(whole, literal(False))),
        select(latest.c.id).select_from(scoped.join(latest, literal(True))).where(whole),
    ).cte("export_selected_use_ids")
    in_scope = exists(
        select(1)
        .select_from(scoped)
        .where(
            scoped.c.subject == admissions.c.subject,
            scoped.c.original_source.is_not_distinct_from(admissions.c.original_source),
            scoped.c.analyzed_scope == admissions.c.analyzed_scope,
        )
    )
    in_page = case((whole, or_(in_scope, ~exists(select(1).select_from(scoped)))), else_=in_page)
    seed = _read_support_seed(metadata, seeds, admissions, in_page)
    nodes = _support_walk(metadata, seed, public=True)
    episodes = metadata.tables["ops.data_derivation"]
    inputs = metadata.tables["ops.data_derivation_input"]
    outputs = metadata.tables["ops.data_derivation_output"]
    products = metadata.tables["kb.data_product"]
    members = metadata.tables["kb.data_product_member"]
    uses = metadata.tables["ops.demand_use"]
    populations = metadata.tables["ops.data_population"]
    requests = metadata.tables["ops.data_request"]
    definitions = metadata.tables["sem.data_operation_definition"]
    kinds = metadata.tables["sem.data_kind_contract"]

    def reached(kind, identity):
        return exists(
            select(1)
            .select_from(nodes)
            .where(nodes.c.kind == kind, nodes.c.id == identity)
            .correlate_except(nodes)
        )

    episode_ids = select(episodes.c.id).where(reached("episode", episodes.c.id))
    authority_ids = select(nodes.c.id).where(nodes.c.kind == "authority")
    request_ids = select(episodes.c.request_id).where(episodes.c.id.in_(episode_ids))
    product_ids = union(
        select(inputs.c.product_id).where(inputs.c.derivation_id.in_(episode_ids)),
        select(outputs.c.product_id).where(outputs.c.derivation_id.in_(episode_ids)),
        select(outputs.c.product_id).where(outputs.c.derivation_id.in_(authority_ids)),
        select(admissions.c.product_id).where(reached("original", admissions.c.id)),
    ).cte("export_products")

    def records(relation, predicate, *order):
        # Retain row context exactly; transaction visibility markers are not public
        # semantic addresses and are unnecessary for detached interpretation.
        value = func.to_jsonb(relation.table_valued())
        from .selected_support_contract import omitted_support_fields

        omitted = omitted_support_fields(relation.fullname)
        for name in sorted(omitted & set(relation.c.keys())):
            value = value.op("-")(literal(name))
        key = func.jsonb_build_array(
            *(relation.c[col.name] for col in relation.primary_key.columns)
        ).cast(Text)
        return select(
            (literal(relation.fullname + ":") + key).label("key"),
            literal(relation.fullname).label("relation"),
            value.label("record"),
        ).where(predicate)

    fields = dict(
        uses=records(
            uses,
            and_(reached("use", uses.c.id), ~_public_authority_leaf(uses.c.derivation_id)),
            uses.c.id,
        ),
        episodes=records(episodes, episodes.c.id.in_(episode_ids), episodes.c.id),
        requests=records(requests, requests.c.id.in_(request_ids), requests.c.id),
        original_admissions=records(
            admissions, reached("original", admissions.c.id), admissions.c.id
        ),
        populations=records(populations, reached("population", populations.c.id), populations.c.id),
        inputs=records(
            inputs,
            inputs.c.derivation_id.in_(episode_ids),
            inputs.c.derivation_id,
            inputs.c.role,
            inputs.c.position,
        ),
        outputs=records(
            outputs,
            outputs.c.derivation_id.in_(episode_ids),
            outputs.c.derivation_id,
            outputs.c.role,
            outputs.c.position,
        ),
        products=records(
            products,
            and_(
                products.c.id.in_(select(product_ids.c.product_id)),
                _disclosed_kind_access(metadata, products.c.kind_contract),
            ),
            products.c.id,
        ),
        members=records(
            members,
            and_(
                members.c.product_id.in_(select(product_ids.c.product_id)),
                _disclosed_kind_access(metadata, members.c.kind_contract),
            ),
            members.c.product_id,
            members.c.member_id,
        ),
        kinds=records(
            kinds,
            or_(
                kinds.c.kind_contract.in_(
                    select(products.c.kind_contract).where(
                        products.c.id.in_(select(product_ids.c.product_id))
                    )
                ),
                kinds.c.kind_contract.in_(
                    select(members.c.kind_contract).where(
                        members.c.product_id.in_(select(product_ids.c.product_id))
                    )
                ),
            ),
            kinds.c.kind_contract,
        ),
        definitions=records(
            definitions,
            exists(
                select(1)
                .select_from(episodes.join(requests, requests.c.id == episodes.c.request_id))
                .where(
                    or_(episodes.c.id.in_(episode_ids), episodes.c.id.in_(authority_ids)),
                    episodes.c.release_id == definitions.c.release_id,
                    requests.c.operation_id == definitions.c.operation_id,
                )
            ),
            definitions.c.release_id,
            definitions.c.operation_id,
        ),
    )
    if (partitions := metadata.tables.get("kb.data_product_partition")) is not None:
        visible_partition_parent = exists(
            select(1)
            .select_from(products.join(product_ids, product_ids.c.product_id == products.c.id))
            .where(
                products.c.id == partitions.c.product_id,
                _disclosed_body_access(
                    metadata, products.c.kind_contract, products.c.canonical_body
                ),
            )
        )
        fields["partitions"] = records(
            partitions, visible_partition_parent, *partitions.primary_key.columns
        )
    # This is an explicit bounded provenance form, not a second storage table.
    # In particular no issuer use/binding, request, intent, protected input, other
    # output or transitive protected support is exported as a normal episode.
    authority_use = uses.alias("authority_use")
    fields["authority_leaves"] = (
        select(
            (
                literal("ops.data_authority_leaf:")
                + func.jsonb_build_array(nodes.c.id, authority_use.c.id).cast(Text)
            ).label("key"),
            literal("ops.data_authority_leaf").label("relation"),
            func.ops.ddo_policy_authority_summary(
                nodes.c.id, authority_use.c.id, _var("boundary.id", Text)
            ).label("record"),
        )
        .select_from(
            nodes.outerjoin(
                authority_use,
                and_(
                    authority_use.c.derivation_id == nodes.c.id,
                    reached("use", authority_use.c.id),
                ),
            )
        )
        .where(nodes.c.kind == "authority")
    )
    # Revocation witnesses belong to the same authenticated, body-authorized
    # selected closure. Keep selector/epoch provenance; never infer cause merely
    # because a use is currently unavailable. No private table grant is added.
    revoked = metadata.tables["ops.data_revocation"]
    episode_match = exists(
        select(1)
        .select_from(episodes.join(requests, requests.c.id == episodes.c.request_id))
        .where(
            episodes.c.id.in_(episode_ids),
            revoked.c.scope
            == func.ops.ddo_scope(requests.c.project_id, requests.c.original_source),
            or_(
                and_(revoked.c.selector_kind == "derivation", revoked.c.selector == episodes.c.id),
                and_(revoked.c.selector_kind == "recipe", revoked.c.selector == episodes.c.recipe),
                and_(
                    revoked.c.selector_kind == "runtime",
                    revoked.c.selector == episodes.c.runtime_id,
                ),
                and_(
                    revoked.c.selector_kind == "product",
                    exists(
                        select(1)
                        .select_from(outputs)
                        .where(
                            outputs.c.derivation_id == episodes.c.id,
                            outputs.c.product_id == revoked.c.selector,
                        )
                    ),
                ),
            ),
        )
    )
    original_match = exists(
        select(1)
        .select_from(admissions)
        .where(
            reached("original", admissions.c.id),
            revoked.c.scope
            == func.ops.ddo_scope(admissions.c.project_id, admissions.c.original_source),
            or_(
                and_(
                    revoked.c.selector_kind == "original-admission",
                    revoked.c.selector == admissions.c.id,
                ),
                and_(
                    revoked.c.selector_kind == "original-source",
                    revoked.c.selector == admissions.c.source_reference,
                ),
                and_(
                    revoked.c.selector_kind == "product",
                    revoked.c.selector == admissions.c.product_id,
                ),
            ),
        )
    )
    selected_epoch = cast(
        _var("boundary.trust_snapshot", JSONB).op("->>")(revoked.c.scope), BigInteger
    )
    fields["revocations"] = records(
        revoked,
        and_(or_(episode_match, original_match), revoked.c.epoch <= selected_epoch),
        revoked.c.id,
    )
    intents = metadata.tables["ops.data_completion_intent"]
    receipts = metadata.tables["ops.data_publication_receipt"]
    batch_episodes = (
        select(episodes.c.id.label("derivation_id"), intents.c.id.label("intent_id"))
        .select_from(
            episodes.join(intents, intents.c.id == episodes.c.intent_id)
            .join(requests, requests.c.id == episodes.c.request_id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == episodes.c.release_id,
                    definitions.c.operation_id == requests.c.operation_id,
                ),
            )
        )
        .where(
            episodes.c.id.in_(episode_ids),
            definitions.c.support_contract["capabilities"]["forms"] == _json(["batch"]),
            func.jsonb_array_length(
                func.coalesce(intents.c.payload["execution_evidence"]["cpu_replies"], _json([]))
            )
            > 0,
        )
        .cte("export_batch_execution_episodes")
        .prefix_with("MATERIALIZED")
    )
    fields["completion_intents"] = records(
        intents,
        and_(
            intents.c.id.in_(select(episodes.c.intent_id).where(episodes.c.id.in_(episode_ids))),
            intents.c.id.not_in(select(batch_episodes.c.intent_id)),
        ),
        intents.c.id,
    )
    # Keep the selected operation's complete semantic support. Only the physical
    # cohort reply is private; this is a distinct native assertion, never a
    # rewritten completion-intent row with a misleading original payload digest.
    fields["execution_evidence_leaves"] = (
        select(
            (
                literal("ops.data_execution_evidence_leaf:")
                + func.jsonb_build_array(
                    episodes.c.id, outputs.c.product_id, outputs.c.role, outputs.c.position
                ).cast(Text)
            ).label("key"),
            literal("ops.data_execution_evidence_leaf").label("relation"),
            func.ops.ddo_cpu_execution_leaf(
                episodes.c.id,
                outputs.c.product_id,
                outputs.c.role,
                outputs.c.position,
                null().cast(Text),
            ).label("record"),
        )
        .select_from(
            episodes.join(batch_episodes, batch_episodes.c.derivation_id == episodes.c.id).join(
                outputs, outputs.c.derivation_id == episodes.c.id
            )
        )
        .where(outputs.c.member_id.is_(None))
    )
    fields["publication_receipts"] = records(
        receipts, receipts.c.derivation_id.in_(episode_ids), receipts.c.id
    )
    for name in ("data_derivation_support", "data_derivation_original_support"):
        relation = metadata.tables["ops." + name]
        visible_edge = relation.c.derivation_id.in_(episode_ids)
        if name == "data_derivation_support":
            issuer_use = uses.alias("structural_issuer_use")
            report_ref = cast(
                func.ops.ddo_structural_report_support(
                    issuer_use.c.id,
                    core_reference("boundary", type_=NullType()),
                    _requested_read_scope()["product_ids"],
                ),
                JSONB,
            )
            visible_edge = or_(
                visible_edge,
                exists(
                    select(1)
                    .select_from(issuer_use)
                    .where(
                        reached("use", issuer_use.c.id),
                        relation.c.derivation_id == issuer_use.c.derivation_id,
                        relation.c.role.in_(("comparison", "condition", "definition")),
                        relation.c.support_derivation_id == report_ref["derivation_id"].astext,
                        relation.c.admission_use_id == report_ref["use_id"].astext,
                    )
                ),
            )
        fields[name.removeprefix("data_derivation_")] = records(
            relation, visible_edge, *relation.primary_key.columns
        )
    from .support_edges import support_explanation_rows

    fields["validity_explanations"] = support_explanation_rows(
        metadata, seeds, core_reference("boundary", type_=NullType()), reached
    )
    rows = union(*fields.values()).cte("support_export_rows")
    bounded_rows = (
        select(rows)
        .where(rows.c.key > func.coalesce(_var("p", JSONB)["support_after"].astext, literal("")))
        .order_by(rows.c.key)
        .limit(_var("lim", BigInteger) + 1)
        .cte("support_export_bounded")
        .prefix_with("MATERIALIZED")
    )
    page = (
        select(bounded_rows)
        .order_by(bounded_rows.c.key)
        .limit(_var("lim", BigInteger))
        .cte("support_export_page")
    )
    last = select(func.max(page.c.key)).scalar_subquery()
    more = select(func.count()).select_from(bounded_rows).scalar_subquery() > _var(
        "lim", BigInteger
    )
    payload = _obj(
        records=select(
            _aggregate(
                _obj(key=page.c.key, relation=page.c.relation, record=page.c.record), page.c.key
            )
        ).scalar_subquery(),
        after=case((more, last), else_=null()),
        complete=~more,
    )
    body_bytes = select(
        func.coalesce(func.sum(func.octet_length(page.c.record.cast(Text))), 0)
    ).scalar_subquery()
    body_access = _support_export_body_access(metadata, products, product_ids)
    value = case(
        (
            body_access,
            case(
                (body_bytes <= _var("selected_max_bytes", BigInteger), payload),
                else_=func.ops.ddo_result_bytes_refusal(),
            ),
        ),
        else_=func.ops.ddo_result_bytes_refusal(),
    )
    return value, body_access


def read_selection():
    """Keep the acquired intent disclosure unchanged across authorized purposes."""
    selection = _var("d.selection", JSONB)
    public = _obj(
        version=literal("data-demand-public-selection-v1"),
        model=selection["model"],
        intent_digest=func.ops.ddo_digest(selection),
        **{name: selection[name] for name in ("roots", "targets", "root_operations", "discovery")},
    )
    return case(
        (and_(_public_read(), _var("boundary.scope", JSONB) != _json({})), public),
        else_=selection,
    )


def _cut_fields():
    return dict(
        demand_id=_var("d.id", Text),
        project_id=_var("d.project_id", Text),
        release_id=_var("d.release_id", Text),
        runtime_id=_var("d.runtime_id", Text),
        selection=read_selection(),
        trust_snapshot=_var("boundary.trust_snapshot", JSONB),
        read_id=_var("boundary.id", Text),
        read_snapshot=_var("boundary.read_snapshot", Text),
        frontier_at=core_reference("boundary", "frontier_at", type_=NullType()),
        scope=_var("boundary.scope", JSONB),
    )


def cut_selection_projection():
    """The same authenticated native cut metadata at every family read boundary."""
    return select(_obj(**_cut_fields()))


def _scoped_read_obligations(metadata, *, exact_obligation=None):
    """The exact declared read scope, independent of page size and continuation."""
    obligations = metadata.tables["ops.data_obligation"]
    uses = metadata.tables["ops.demand_use"]
    outputs = metadata.tables["ops.data_derivation_output"]
    admissions = metadata.tables["ops.original_source_admission"].alias("scope_original")
    read_scope = _requested_read_scope()
    scope_predicates = tuple(
        or_(
            ~read_scope.op("?")(literal(name)),
            obligations.c[name].is_not_distinct_from(read_scope[name].astext),
        )
        for name in ("operation_id", "subject", "original_source")
    )
    scoped_use = uses.alias("scope_use")
    later_scope_use = uses.alias("scope_later_use")
    selected_product = (
        func.jsonb_array_elements_text(read_scope["product_ids"])
        .table_valued(column("value", Text()))
        .render_derived(name="scope_product")
    )
    product_match = exists(
        select(1)
        .select_from(
            scoped_use.join(outputs, outputs.c.derivation_id == scoped_use.c.derivation_id).join(
                selected_product, selected_product.c.value == outputs.c.product_id
            )
        )
        .where(
            scoped_use.c.obligation_id == obligations.c.id,
            _visible(scoped_use),
            ~exists(
                select(1)
                .select_from(later_scope_use)
                .where(
                    later_scope_use.c.obligation_id == scoped_use.c.obligation_id,
                    _visible(later_scope_use),
                    or_(
                        later_scope_use.c.created_at > scoped_use.c.created_at,
                        and_(
                            later_scope_use.c.created_at == scoped_use.c.created_at,
                            later_scope_use.c.id > scoped_use.c.id,
                        ),
                    ),
                )
            ),
        )
    )
    original_match = exists(
        select(1)
        .select_from(
            admissions.join(selected_product, selected_product.c.value == admissions.c.product_id)
        )
        .where(
            admissions.c.demand_id == _var("d.id", Text),
            admissions.c.project_id == _var("d.project_id", Text),
            admissions.c.subject == obligations.c.subject,
            admissions.c.original_source.is_not_distinct_from(obligations.c.original_source),
            admissions.c.analyzed_scope == obligations.c.analyzed_scope,
            _visible(admissions),
        )
    )
    # Scope identifies retained evidence even after its trust is withdrawn. The
    # admission frontier checks current validity; support export retains raw custody.
    scope_predicates += (
        or_(~read_scope.op("?")(literal("product_ids")), product_match, original_match),
    )
    return select(obligations).where(
        obligations.c.demand_id == _var("d.id", Text),
        *([obligations.c.id == exact_obligation] if exact_obligation is not None else []),
        *scope_predicates,
        _visible(obligations),
    )


def _latest_read_use(metadata, obligations):
    uses = metadata.tables["ops.demand_use"]
    return (
        select(uses)
        .where(uses.c.obligation_id == obligations.c.id, _visible(uses))
        .order_by(uses.c.created_at.desc(), uses.c.id.desc())
        .limit(1)
        .correlate(obligations)
        .lateral("latest")
    )


def _selected_support_output_rows(
    metadata, *, purpose="read", one_use=True, member_aware=False, exact_obligation=None
):
    """Whole outputs reached by exact scoped selected current support."""
    obligations = _scoped_read_obligations(metadata, exact_obligation=exact_obligation).cte(
        "scoped_obligations"
    )
    latest = _latest_read_use(metadata, obligations)
    selected = (
        select(latest)
        .select_from(obligations.join(latest, literal(True)))
        .where(
            *([latest.c.id == _var("p_use", Text)] if one_use else []),
            latest.c.fate == "fulfilled",
        )
        .cte("selected_uses")
    )
    selected_validity = _validity_rows(
        select(func.array_agg(selected.c.id)).scalar_subquery(),
        name="selected_output_validity",
    )
    seed = (
        _node("use", selected.c.id)
        .where(_set_valid(selected_validity, "use", selected.c.id))
        .cte("selected_output_seed")
    )
    nodes = _support_walk(metadata, seed, public=purpose in {"read", "custody"})
    # A selected value use can remain valid without its historical episode.
    # Exact output authority still requires validity of the reached episode.
    reached_episodes = (
        select(func.array_agg(nodes.c.id))
        .where(nodes.c.kind.in_(("episode", "authority")))
        .scalar_subquery()
    )
    reached_uses = (
        select(func.array_agg(nodes.c.id)).where(nodes.c.kind == "use").scalar_subquery()
        if member_aware
        else None
    )
    reached_validity = _validity_rows(
        reached_uses, reached_episodes, name="reached_output_validity"
    )
    outputs = metadata.tables["ops.data_derivation_output"]
    episodes = metadata.tables["ops.data_derivation"]
    products = metadata.tables["kb.data_product"]
    if purpose == "read":
        access = _disclosed_body_access(
            metadata, products.c.kind_contract, products.c.canonical_body
        )
    elif purpose == "feature-fit":
        access = func.ops.ddo_feature_fit_body_access(
            products.c.kind_contract, products.c.canonical_body
        )
    elif purpose == "custody":
        access = _custody_body_eligible(
            metadata, products.c.kind_contract, products.c.canonical_body
        )
    else:
        raise ValueError("unknown selected output purpose")
    reached = exists(
        select(1)
        .select_from(nodes)
        .where(
            nodes.c.kind.in_(("episode", "authority")),
            nodes.c.id == episodes.c.id,
        )
    )
    relation = episodes.join(outputs, outputs.c.derivation_id == episodes.c.id).join(
        products, products.c.id == outputs.c.product_id
    )
    fields = [episodes.c.id.label("derivation_id"), outputs.c.product_id]
    producing_reached = literal(True)
    if member_aware:
        producing = metadata.tables["ops.demand_use"].alias("source_producing_use")
        relation = relation.join(producing, producing.c.derivation_id == episodes.c.id)
        fields.extend(
            (
                outputs.c.member_id.label("output_member_id"),
                outputs.c.role,
                outputs.c.position,
                outputs.c.multiplicity,
                producing.c.id.label("admission_use_id"),
            )
        )
        producing_reached = and_(
            producing.c.fate == "fulfilled",
            _visible(producing),
            _set_valid(reached_validity, "use", producing.c.id),
            exists(
                select(1)
                .select_from(nodes)
                .where(nodes.c.kind == "use", nodes.c.id == producing.c.id)
            ),
        )
    return (
        select(*fields)
        .select_from(relation)
        .where(
            case(
                (
                    and_(
                        reached,
                        producing_reached,
                        literal(True) if member_aware else outputs.c.member_id.is_(None),
                        products.c.project_id == _var("d.project_id", Text),
                        _set_valid(reached_validity, "episode", episodes.c.id),
                    ),
                    access,
                ),
                else_=literal(False),
            )
        )
        .distinct()
    )


def selected_support_output(metadata, *, purpose="read", exact_obligation=None):
    """Prove exact output membership; internal custody returns no body or caller capability."""
    rows = _selected_support_output_rows(
        metadata, purpose=purpose, exact_obligation=exact_obligation
    ).cte("selected_whole_outputs")
    return select(
        exists(
            select(1)
            .select_from(rows)
            .where(
                rows.c.derivation_id == _var("p_derivation", Text),
                rows.c.product_id == _var("p_product", Text),
            )
        )
    )


def selected_source_output_occurrences(metadata):
    """Identity-only actual use/output occurrences under one selected anchor."""
    return _selected_support_output_rows(metadata, member_aware=True)


def record_grade_selected_outputs(metadata):
    """Batch identity-only source-cut membership after the grade's finite guard."""
    return _selected_support_output_rows(metadata, one_use=False)


def _watermark_role_matches(role, header, projected_kind, projected_scope, bounded):
    """Use binding's immutable role, source and qualified-context association."""
    return case(
        (
            and_(
                role["accepted_kind_contracts"].bool_op("?")(projected_kind),
                func.coalesce(role["support"]["origins"], _json(["computation"])).bool_op("?")(
                    literal("computation")
                ),
                or_(
                    role["subject_field"].astext.is_not(None),
                    role["subject_target"].astext == "source-set",
                    projected_scope.is_not_distinct_from(bounded.c.analyzed_scope),
                ),
            ),
            and_(
                func.ops.ddo_binding_subject(
                    role, header, bounded.c.subject, bounded.c.original_source
                ),
                func.ops.ddo_binding_source(
                    role,
                    header,
                    bounded.c.original_source,
                    func.coalesce(_var("d.selection", JSONB)["source_sets"], _json({})),
                ),
            ),
        ),
        else_=literal(False),
    )


def _pinned_watermark_uses(metadata, bounded):
    """Visible exact-pin uses under the obligation's actual role/context policy."""
    selection = _var("d.selection", JSONB)
    definitions = metadata.tables["sem.data_operation_definition"].alias("watermark_definition")
    roles = _items(definitions.c.input_roles, "watermark_role")
    source_set = selection["source_sets"][roles.c.value["support"]["source_set"].astext]
    entries = _items(func.coalesce(source_set["entries"], _json([])), "watermark_pin")
    products = metadata.tables["kb.data_product"].alias("watermark_product")
    members = metadata.tables["kb.data_product_member"].alias("watermark_member")
    outputs = metadata.tables["ops.data_derivation_output"].alias("watermark_output")
    episodes = metadata.tables["ops.data_derivation"].alias("watermark_episode")
    uses = metadata.tables["ops.demand_use"].alias("watermark_use")
    selected_member = entries.c.value["member"].astext
    projected_kind = func.coalesce(members.c.kind_contract, products.c.kind_contract)
    projected_subject = func.coalesce(members.c.subject, products.c.subject)
    projected_scope = func.coalesce(members.c.analyzed_scope, products.c.analyzed_scope)
    projected_body = func.coalesce(members.c.body, products.c.canonical_body)
    emitting = _obj(
        member_id=outputs.c.member_id,
        role=outputs.c.role,
        position=outputs.c.position,
        multiplicity=outputs.c.multiplicity,
    )
    header = _obj(
        product=products.c.id,
        member=selected_member,
        subject=projected_subject,
        subject_definition=func.coalesce(
            members.c.subject_definition, products.c.subject_definition
        ),
        original_source=products.c.original_source,
        analyzed_scope=projected_scope,
        meaning_body=projected_body,
        support_references=func.jsonb_build_array(
            _obj(
                kind=literal("computation"),
                derivation_id=episodes.c.id,
                admission_use_id=uses.c.id,
            )
        ),
        support_evidence=_obj(producer_output=emitting),
    )
    # The same immutable subject/source/proof predicates own binding eligibility.
    # This records raw visible identities; live validity/authority remain with the
    # read acquisition and binding boundary rather than becoming a validity cache.
    role_matches = _watermark_role_matches(
        roles.c.value, header, projected_kind, projected_scope, bounded
    )
    return (
        select(
            bounded.c.id.label("obligation_id"),
            literal("use").label("kind"),
            uses.c.id.label("identity"),
            uses.c.created_at,
        )
        .select_from(
            bounded.join(
                definitions,
                and_(
                    definitions.c.release_id == _var("d.release_id", Text),
                    definitions.c.operation_id == bounded.c.operation_id,
                ),
            )
            .join(roles, literal(True))
            .join(entries, literal(True))
            .join(products, products.c.id == entries.c.value["product"].astext)
            .outerjoin(
                members,
                and_(members.c.product_id == products.c.id, members.c.member_id == selected_member),
            )
            .join(
                outputs,
                and_(
                    outputs.c.product_id == products.c.id,
                    or_(
                        and_(selected_member.is_(None), outputs.c.member_id.is_(None)),
                        and_(
                            selected_member.is_not(None),
                            or_(
                                outputs.c.member_id.is_(None),
                                outputs.c.member_id == selected_member,
                            ),
                        ),
                    ),
                ),
            )
            .join(episodes, episodes.c.id == outputs.c.derivation_id)
            .join(uses, uses.c.derivation_id == episodes.c.id)
        )
        .where(
            products.c.project_id == _var("d.project_id", Text),
            or_(selected_member.is_(None), members.c.member_id.is_not(None)),
            uses.c.fate == "fulfilled",
            _visible(uses),
            role_matches,
            func.ops.ddo_source_set_proof_matches(
                source_set,
                products.c.id,
                selected_member,
                episodes.c.id,
                uses.c.id,
                emitting,
            ),
        )
    )


def _unconstrained_watermark_uses(metadata, bounded):
    """Wake dependency-free consumers only for eligible same-demand role outputs."""
    selection = _var("d.selection", JSONB)
    selected = _items(selection["operations"], "watermark_unconstrained_operation")
    definitions = metadata.tables["sem.data_operation_definition"].alias(
        "watermark_local_definition"
    )
    roles = _items(definitions.c.input_roles, "watermark_local_role")
    uses = metadata.tables["ops.demand_use"].alias("watermark_local_use")
    later = metadata.tables["ops.demand_use"].alias("watermark_local_later")
    episodes = metadata.tables["ops.data_derivation"].alias("watermark_local_episode")
    outputs = metadata.tables["ops.data_derivation_output"].alias("watermark_local_output")
    products = metadata.tables["kb.data_product"].alias("watermark_local_product")
    members = metadata.tables["kb.data_product_member"].alias("watermark_local_member")
    projected = union_all(
        select(
            cast(null(), Text).label("member_id"),
            products.c.kind_contract.label("kind_contract"),
            products.c.subject.label("subject"),
            products.c.subject_definition.label("subject_definition"),
            products.c.original_source.label("original_source"),
            products.c.analyzed_scope.label("analyzed_scope"),
            products.c.canonical_body.label("meaning_body"),
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
            members.c.body,
        )
        .where(
            members.c.product_id == products.c.id,
            or_(outputs.c.member_id.is_(None), members.c.member_id == outputs.c.member_id),
        )
        .correlate(products, outputs),
    ).lateral("watermark_local_projection")
    emitting = _obj(
        member_id=outputs.c.member_id,
        role=outputs.c.role,
        position=outputs.c.position,
        multiplicity=outputs.c.multiplicity,
    )
    header = _obj(
        product=products.c.id,
        member=projected.c.member_id,
        subject=projected.c.subject,
        subject_definition=projected.c.subject_definition,
        original_source=projected.c.original_source,
        analyzed_scope=projected.c.analyzed_scope,
        meaning_body=projected.c.meaning_body,
        support_references=func.jsonb_build_array(
            _obj(
                kind=literal("computation"),
                derivation_id=episodes.c.id,
                admission_use_id=uses.c.id,
            )
        ),
        support_evidence=_obj(producer_output=emitting),
    )
    return (
        select(
            bounded.c.id.label("obligation_id"),
            literal("use").label("kind"),
            uses.c.id.label("identity"),
            uses.c.created_at,
        )
        .select_from(
            bounded.join(
                selected,
                and_(
                    selected.c.value["operation"].astext == bounded.c.operation_id,
                    func.jsonb_array_length(selected.c.value["dependencies"]) == 0,
                ),
            )
            .join(
                definitions,
                and_(
                    definitions.c.release_id == _var("d.release_id", Text),
                    definitions.c.operation_id == bounded.c.operation_id,
                ),
            )
            .join(roles, literal(True))
            .join(uses, uses.c.demand_id == _var("d.id", Text))
            .join(episodes, episodes.c.id == uses.c.derivation_id)
            .join(outputs, outputs.c.derivation_id == episodes.c.id)
            .join(products, products.c.id == outputs.c.product_id)
            .join(projected, literal(True))
        )
        .where(
            roles.c.value["support"]["source_set"].astext.is_(None),
            products.c.project_id == _var("d.project_id", Text),
            uses.c.fate == "fulfilled",
            _visible(uses),
            ~exists(
                select(1)
                .select_from(later)
                .where(
                    later.c.obligation_id == uses.c.obligation_id,
                    or_(
                        later.c.created_at > uses.c.created_at,
                        and_(later.c.created_at == uses.c.created_at, later.c.id > uses.c.id),
                    ),
                    _visible(later),
                )
            ),
            # Access checks raise on refusal, so unrelated kinds or qualified
            # contexts must be filtered before either authorization executes.
            case(
                (
                    _watermark_role_matches(
                        roles.c.value,
                        header,
                        projected.c.kind_contract,
                        projected.c.analyzed_scope,
                        bounded,
                    ),
                    case(
                        (
                            and_(
                                _kind_disclosed(metadata, products.c.kind_contract),
                                _kind_disclosed(metadata, projected.c.kind_contract),
                            ),
                            and_(
                                func.ops.ddo_kind_access(products.c.kind_contract),
                                func.ops.ddo_body_access(
                                    projected.c.kind_contract, projected.c.meaning_body
                                ),
                            ),
                        ),
                        else_=literal(False),
                    ),
                ),
                else_=literal(False),
            ),
        )
    )


def _inputs_watermarks(metadata, bounded):
    """A set-wise readiness fingerprint; waiting fates do not advance it."""
    uses = metadata.tables["ops.demand_use"]
    obligations = metadata.tables["ops.data_obligation"].alias("prerequisite_obligation")
    populations = metadata.tables["ops.data_population"]
    originals = metadata.tables["ops.original_source_admission"]
    selected = _items(_var("d.selection", JSONB)["operations"], "watermark_selected")
    dependencies = (
        func.jsonb_array_elements_text(selected.c.value["dependencies"])
        .table_valued(column("value", Text()))
        .render_derived(name="watermark_dependency")
    )
    prerequisites = (
        select(bounded.c.id.label("obligation_id"), dependencies.c.value.label("operation_id"))
        .select_from(
            bounded.join(
                selected, selected.c.value["operation"].astext == bounded.c.operation_id
            ).join(dependencies, literal(True))
        )
        .cte("watermark_prerequisites", recursive=True)
    )
    prerequisites = prerequisites.union(
        select(prerequisites.c.obligation_id, dependencies.c.value).select_from(
            prerequisites.join(
                selected, selected.c.value["operation"].astext == prerequisites.c.operation_id
            ).join(dependencies, literal(True))
        )
    )
    fulfilled = (
        select(
            bounded.c.id.label("obligation_id"),
            literal("use").label("kind"),
            uses.c.id.label("identity"),
            uses.c.created_at,
        )
        .select_from(
            bounded.join(prerequisites, prerequisites.c.obligation_id == bounded.c.id)
            .join(
                obligations,
                and_(
                    obligations.c.demand_id == _var("d.id", Text),
                    obligations.c.operation_id == prerequisites.c.operation_id,
                    obligations.c.original_source.is_not_distinct_from(bounded.c.original_source),
                ),
            )
            .join(uses, uses.c.obligation_id == obligations.c.id)
        )
        .where(uses.c.fate == "fulfilled", _visible(uses))
    )
    discovery = _items(_var("d.selection", JSONB)["discovery"], "watermark_discovery")
    relevant_population = or_(
        populations.c.selected_obligation_id == bounded.c.id,
        exists(
            select(1)
            .select_from(discovery)
            .where(
                discovery.c.value["population"].astext == populations.c.name,
                or_(
                    discovery.c.value["target"].astext == bounded.c.operation_id,
                    exists(
                        select(1)
                        .select_from(prerequisites)
                        .where(
                            prerequisites.c.obligation_id == bounded.c.id,
                            prerequisites.c.operation_id == discovery.c.value["target"].astext,
                        )
                    ),
                ),
            )
        ),
    )
    population_rows = (
        select(
            bounded.c.id.label("obligation_id"),
            literal("population").label("kind"),
            populations.c.id.label("identity"),
            populations.c.created_at,
        )
        .select_from(bounded.join(populations, populations.c.demand_id == _var("d.id", Text)))
        .where(relevant_population, _visible(populations))
    )
    # Original selections are exact frozen pins. Admission can occur after the
    # waiting fate, including an explicitly selected source from another context.
    original_rows = (
        select(
            bounded.c.id.label("obligation_id"),
            literal("original").label("kind"),
            originals.c.id.label("identity"),
            originals.c.created_at,
        )
        .select_from(bounded.join(originals, originals.c.demand_id == _var("d.id", Text)))
        .where(_visible(originals))
    )
    # A use can be both a local prerequisite and an explicit pin, or can emit
    # several selected outputs. Hash its actual identity once, independent of
    # output multiplicity and timestamp ties.
    visible = union(
        fulfilled,
        _pinned_watermark_uses(metadata, bounded),
        _unconstrained_watermark_uses(metadata, bounded),
        population_rows,
        original_rows,
    ).cte("watermark_visible")
    identities = (
        select(
            visible.c.obligation_id,
            _aggregate(
                _obj(kind=visible.c.kind, identity=visible.c.identity),
                visible.c.kind,
                visible.c.identity,
            ).label("identities"),
        )
        .group_by(visible.c.obligation_id)
        .cte("watermark_identities")
        .prefix_with("MATERIALIZED")
    )
    facts = (
        select(identities.c.identities)
        .where(identities.c.obligation_id == bounded.c.id)
        .correlate(bounded)
        .scalar_subquery()
    )
    return func.ops.ddo_digest(
        _obj(
            visible=func.coalesce(facts, _json([])),
            source_sets=_var("d.selection", JSONB)["source_sets"],
            original_sources=_var("d.selection", JSONB)["original_sources"],
            trust=_var("boundary.trust_snapshot", JSONB),
        )
    )


def read_page(metadata):
    """One pure atomic page under already acquired native pins."""
    from sqlalchemy import case

    demand = _var("d.id", Text)
    boundary = core_reference("boundary", type_=NullType())
    obligations = metadata.tables["ops.data_obligation"]
    episodes = metadata.tables["ops.data_derivation"]
    intents = metadata.tables["ops.data_completion_intent"]
    products = metadata.tables["kb.data_product"]
    outputs = metadata.tables["ops.data_derivation_output"]
    requests = metadata.tables["ops.data_request"]
    definitions = metadata.tables["sem.data_operation_definition"]
    read_scope = _requested_read_scope()
    bounded = (
        _scoped_read_obligations(metadata)
        .where(
            obligations.c.id > _var("after_key", Text),
            or_(
                ~_var("p", JSONB).op("?")(literal("obligation_id")),
                obligations.c.id == _var("p", JSONB)["obligation_id"].astext,
            ),
        )
        .order_by(obligations.c.id)
        .limit(_var("lim", BigInteger))
        .cte("bounded")
        .prefix_with("MATERIALIZED")
    )
    latest = _latest_read_use(metadata, bounded)
    selected_uses = (
        select(latest)
        .select_from(bounded.join(latest, literal(True)))
        .cte("selected_uses")
        .prefix_with("MATERIALIZED")
    )
    population_table = metadata.tables["ops.data_population"]
    public_seed = _node("use", selected_uses.c.id).cte("page_public_support_seed")
    public_nodes = _support_walk(metadata, public_seed, public=True, name="page_public_support")
    candidate_populations = (
        select(population_table)
        .where(
            population_table.c.demand_id == demand,
            or_(
                population_table.c.selected_obligation_id.is_(None),
                population_table.c.selected_obligation_id.in_(select(bounded.c.id)),
            ),
            _visible(population_table),
            or_(
                # The whole-demand execution frontier supplies closed discovery
                # populations before their consumers can bind them. A selected
                # cut still discloses only populations in its support walk.
                read_scope == _json({}),
                exists(
                    select(1)
                    .select_from(public_nodes)
                    .where(
                        public_nodes.c.kind == "population",
                        public_nodes.c.id == population_table.c.id,
                    )
                ),
            ),
        )
        .cte("candidate_populations")
        .prefix_with("MATERIALIZED")
    )
    validity = _validity_rows(
        select(func.array_agg(selected_uses.c.id)).scalar_subquery(),
        name="page_validity",
        seed_populations=select(func.array_agg(candidate_populations.c.id)).scalar_subquery(),
    )
    valid = _set_valid(validity, "use", selected_uses.c.id)
    fulfilled_invalid = and_(selected_uses.c.fate == "fulfilled", valid == false())
    input_roles = _items(definitions.c.input_roles, "required_identity_role")
    rebind_allowed = exists(
        select(1)
        .select_from(
            requests.join(
                definitions,
                and_(
                    definitions.c.release_id == _var("d.release_id", Text),
                    definitions.c.operation_id == requests.c.operation_id,
                ),
            )
        )
        .where(
            requests.c.id == selected_uses.c.request_id,
            definitions.c.support_contract["provenance"].astext == "value_substitution",
            ~exists(
                select(1)
                .select_from(input_roles)
                .where(
                    func.coalesce(input_roles.c.value["identity_requirements"], _json([]))
                    != _json([])
                )
            ),
        )
    )
    body_ids = (
        func.jsonb_array_elements_text(read_scope["product_ids"])
        .table_valued(column("value", Text()))
        .render_derived(name="selected_body_product")
    )
    product_body_selected = or_(
        ~read_scope.op("?")(literal("product_ids")),
        exists(select(1).select_from(body_ids).where(body_ids.c.value == products.c.id)),
    )
    product_value = _obj(
        role=outputs.c.role,
        position=outputs.c.position,
        multiplicity=outputs.c.multiplicity,
        product_id=outputs.c.product_id,
        member_id=outputs.c.member_id,
        kind_contract=products.c.kind_contract,
        subject=products.c.subject,
        subject_definition=products.c.subject_definition,
        original_source=products.c.original_source,
        analyzed_scope=products.c.analyzed_scope,
        body_state=case(
            (_var("selected_view", Text) == "products", literal("present")),
            else_=literal("not_requested"),
        ),
    ).op("||")(
        case(
            (_var("selected_view", Text) == "products", _obj(body=products.c.canonical_body)),
            else_=_json({}),
        )
    )
    selected_products = (
        select(_aggregate(product_value, outputs.c.role, outputs.c.position))
        .select_from(outputs.join(products, products.c.id == outputs.c.product_id))
        .where(
            outputs.c.derivation_id == selected_uses.c.derivation_id,
            case(
                (
                    or_(
                        _var("selected_view", Text) == "products",
                        func.coalesce(
                            _var("p", JSONB)["recheck_bodies"].as_boolean(), literal(False)
                        ),
                    ),
                    case(
                        (
                            product_body_selected,
                            func.ops.ddo_body_access(
                                products.c.kind_contract, products.c.canonical_body
                            ),
                        ),
                        else_=literal(False),
                    ),
                ),
                else_=literal(True),
            ),
        )
        .scalar_subquery()
    )
    semantic_outcome = (
        select(intents.c.payload["outcome"])
        .select_from(episodes.join(intents, intents.c.id == episodes.c.intent_id))
        .where(episodes.c.id == selected_uses.c.derivation_id)
        .scalar_subquery()
    )
    completion_state = (
        select(episodes.c.outcome)
        .where(episodes.c.id == selected_uses.c.derivation_id)
        .scalar_subquery()
    )
    external_packets = metadata.tables["ops.data_external_packet"]
    external_receipts = metadata.tables["ops.data_external_receipt"]

    def awaiting_external(use):
        return exists(
            select(1)
            .select_from(
                external_packets.join(
                    requests,
                    and_(
                        requests.c.id == external_packets.c.request_id,
                        requests.c.generation == external_packets.c.generation,
                        requests.c.live_task_id == external_packets.c.task_id,
                    ),
                )
            )
            .where(
                use.c.fate == "attached",
                external_packets.c.request_id == use.c.request_id,
                external_packets.c.generation == use.c.generation,
                func.ops.ddo_request_useful(requests.table_valued()),
                ~exists(select(1).where(external_receipts.c.packet_id == external_packets.c.id)),
            )
        )

    result_uses = select(
        _aggregate(
            _obj(
                use_id=selected_uses.c.id,
                obligation_id=selected_uses.c.obligation_id,
                fate=case(
                    (fulfilled_invalid, literal("unavailable")),
                    (awaiting_external(selected_uses), literal("awaiting-external")),
                    else_=selected_uses.c.fate,
                ),
                historical_fate=selected_uses.c.fate,
                semantic_outcome=semantic_outcome,
                completion_state=completion_state,
                request_id=case(
                    (_public_authority_leaf(selected_uses.c.derivation_id), null()),
                    else_=selected_uses.c.request_id,
                ),
                generation=case(
                    (_public_authority_leaf(selected_uses.c.derivation_id), null()),
                    else_=selected_uses.c.generation,
                ),
                derivation_id=selected_uses.c.derivation_id,
                rebind_derivation=case(
                    (
                        and_(
                            fulfilled_invalid,
                            _set_valid(validity, "producer", selected_uses.c.derivation_id),
                            _var("d.strength", Text) == "value",
                            rebind_allowed,
                        ),
                        selected_uses.c.derivation_id,
                    ),
                    else_=null(),
                ),
                selection=case(
                    (
                        _public_authority_leaf(selected_uses.c.derivation_id),
                        _obj(
                            kind=literal("native-authority"),
                            protected_dependencies=literal("undisclosed"),
                        ),
                    ),
                    else_=selected_uses.c.selection,
                ),
                trust_snapshot=selected_uses.c.trust_snapshot,
                products=selected_products,
            ),
            selected_uses.c.obligation_id,
        )
    ).scalar_subquery()
    latest_intent = (
        select(intents.c.id)
        .where(
            intents.c.request_id == latest.c.request_id, intents.c.generation == latest.c.generation
        )
        .order_by(intents.c.created_at.desc(), intents.c.id.desc())
        .limit(1)
        .correlate(latest)
        .scalar_subquery()
    )
    inputs_watermark = _inputs_watermarks(metadata, bounded)
    obligation_body = (
        func.to_jsonb(bounded.table_valued())
        .op("-")(literal("created_at"))
        .op("-")(literal("created_xid"))
        .op("||")(
            _obj(
                obligation_id=bounded.c.id,
                inputs_watermark=inputs_watermark,
                subject_definition=select(definitions.c.subject_definition)
                .where(
                    definitions.c.release_id == _var("d.release_id", Text),
                    definitions.c.operation_id == bounded.c.operation_id,
                )
                .scalar_subquery(),
                historical_fate=latest.c.fate,
                fate=case(
                    (
                        and_(
                            latest.c.fate == "fulfilled",
                            _set_valid(validity, "use", latest.c.id) == false(),
                        ),
                        literal("unavailable"),
                    ),
                    (awaiting_external(latest), literal("awaiting-external")),
                    else_=func.coalesce(latest.c.fate, literal("waiting")),
                ),
                request_id=latest.c.request_id,
                generation=latest.c.generation,
                intent_id=latest_intent,
            )
        )
    )
    result_obligations = (
        select(_aggregate(obligation_body, bounded.c.id))
        .select_from(bounded.outerjoin(latest, literal(True)))
        .scalar_subquery()
    )
    next_key = select(func.max(bounded.c.id)).scalar_subquery()
    more = and_(
        next_key.is_not(None),
        exists(
            _scoped_read_obligations(metadata).where(
                obligations.c.id > next_key,
                or_(
                    ~_var("p", JSONB).op("?")(literal("obligation_id")),
                    obligations.c.id == _var("p", JSONB)["obligation_id"].astext,
                ),
            )
        ),
    )
    admissions = metadata.tables["ops.original_source_admission"]
    admission_value = _obj(
        admission_id=admissions.c.id,
        selection_name=admissions.c.selection_name,
        product_id=admissions.c.product_id,
        kind_contract=products.c.kind_contract,
        subject=admissions.c.subject,
        subject_definition=products.c.subject_definition,
        original_source=admissions.c.original_source,
        analyzed_scope=admissions.c.analyzed_scope,
        source_reference=admissions.c.source_reference,
        trust_snapshot=admissions.c.trust_snapshot,
        evidence=admissions.c.evidence,
    )
    in_page = exists(
        select(1)
        .select_from(bounded)
        .where(
            bounded.c.subject == admissions.c.subject,
            bounded.c.original_source.is_not_distinct_from(admissions.c.original_source),
            bounded.c.analyzed_scope == admissions.c.analyzed_scope,
        )
    )
    result_admissions = (
        select(_aggregate(admission_value, admissions.c.id))
        .select_from(admissions.join(products, products.c.id == admissions.c.product_id))
        .where(
            *_read_original_predicates(admissions, in_page),
            func.ops.ddo_original_admission_valid(admissions.table_valued(), boundary),
            _disclosed_kind_access(metadata, products.c.kind_contract),
        )
        .scalar_subquery()
    )
    failures = metadata.tables["ops.data_attempt_failure"]
    failure_inputs = _items(requests.c.binding["inputs"], "failure_input")
    failure_members = metadata.tables["kb.data_product_member"].alias("failure_member")
    undisclosed_failure_input = exists(
        select(1)
        .select_from(
            requests.join(failure_inputs, literal(True))
            .join(products, products.c.id == failure_inputs.c.value["product_id"].astext)
            .outerjoin(
                failure_members,
                and_(
                    failure_members.c.product_id == products.c.id,
                    failure_members.c.member_id == failure_inputs.c.value["member_id"].astext,
                ),
            )
        )
        .where(
            requests.c.id == failures.c.request_id,
            ~_disclosed_kind_access(
                metadata, func.coalesce(failure_members.c.kind_contract, products.c.kind_contract)
            ),
        )
    )
    # The selected-use scope already authorizes generic failure metadata. Keep
    # that population complete while withholding exact native input material.
    disclosed_failure = case(
        (
            and_(failures.c.failure.has_key("d1_limitation"), undisclosed_failure_input),
            failures.c.failure.op("-")(literal("d1_limitation")).op("||")(
                _obj(d1_limitation_disclosure=literal("undisclosed"))
            ),
        ),
        else_=failures.c.failure,
    )
    failure_value = _obj(
        failure_id=failures.c.id,
        request_id=failures.c.request_id,
        generation=failures.c.generation,
        task_id=failures.c.task_id,
        attempt=failures.c.attempt,
        holder=failures.c.holder,
        failure=disclosed_failure,
    )
    result_failures = (
        select(
            _aggregate(
                failure_value, failures.c.request_id, failures.c.generation, failures.c.attempt
            )
        )
        .where(
            exists(
                select(1)
                .select_from(selected_uses)
                .where(
                    selected_uses.c.request_id == failures.c.request_id,
                    selected_uses.c.generation == failures.c.generation,
                )
            ),
            _visible(failures),
        )
        .scalar_subquery()
    )
    populations = population_table
    population_value = (
        func.to_jsonb(populations.table_valued())
        .op("-")(literal("created_at"))
        .op("-")(literal("created_xid"))
        .op("-")(literal("selected_obligation_id"))
        .op("-")(literal("context_key"))
        .op("||")(
            _obj(
                population_id=populations.c.id,
                evidence=populations.c.evidence.op("||")(
                    _obj(
                        producer_context=func.ops.ddo_population_producer_context(
                            populations.table_valued()
                        )
                    )
                ),
            )
        )
    )
    result_populations = (
        select(_aggregate(population_value, populations.c.name))
        .where(
            populations.c.id.in_(select(candidate_populations.c.id)),
            _set_valid(validity, "population", populations.c.id),
        )
        .scalar_subquery()
    )
    cancellations = metadata.tables["ops.data_demand_cancellation"]
    state = case(
        (
            exists(
                select(1)
                .select_from(cancellations)
                .where(cancellations.c.demand_id == demand, _visible(cancellations))
            ),
            literal("cancelled"),
        ),
        else_=literal("active"),
    )
    cut_fields = _cut_fields()
    pins = {
        name: cut_fields[name]
        for name in (
            "demand_id",
            "scope",
            "selection",
            "trust_snapshot",
            "read_id",
            "read_snapshot",
            "frontier_at",
        )
    }
    pins["view"] = _var("selected_view", Text)
    continuation = case(
        (
            more,
            _obj(
                **pins,
                after=next_key,
                limit=_var("lim", BigInteger),
                max_bytes=_var("selected_max_bytes", BigInteger),
            ),
        ),
        else_=null(),
    )
    body_bytes = (
        select(func.coalesce(func.sum(func.octet_length(products.c.canonical_body.cast(Text))), 0))
        .select_from(
            selected_uses.join(
                outputs, outputs.c.derivation_id == selected_uses.c.derivation_id
            ).join(products, products.c.id == outputs.c.product_id)
        )
        .where(product_body_selected)
        .scalar_subquery()
    )
    support_page, support_body_access = selected_support_export(
        metadata,
        selected_uses,
        admissions,
        or_(in_page, ~exists(select(1).select_from(bounded))),
    )
    payload = _obj(
        payload=_obj(
            **cut_fields,
            view=_var("selected_view", Text),
            intent=read_selection(),
            root=_var("d.root", JSONB),
            state=state,
            uses=result_uses,
            obligations=result_obligations,
            original_source_admissions=result_admissions,
            support_page=case(
                (
                    _var("selected_view", Text) == "support",
                    support_page,
                ),
                else_=null(),
            ),
            attempt_failures=result_failures,
            populations=result_populations,
            continuation=continuation,
        )
    )
    # Ordinary frontier reads omit bodies. An explicit cache recheck repeats
    # disclosure for the selected page and its hidden support without transfer.
    # Product pages count returned rows before building the body JSON aggregate.
    within_budget = case(
        (
            _var("selected_view", Text) == "products",
            body_bytes <= _var("selected_max_bytes", BigInteger),
        ),
        else_=literal(True),
    )
    within_budget = and_(
        within_budget,
        case(
            (
                func.coalesce(_var("p", JSONB)["recheck_bodies"].as_boolean(), literal(False)),
                support_body_access,
            ),
            else_=literal(True),
        ),
    )
    return select(
        case((within_budget, payload), else_=func.ops.ddo_result_bytes_refusal()).label("result")
    )


def capture_projection_sources(
    *,
    physical_sources=None,
    linkml_types=None,
    target_metadata=None,
    captured_module_sources=None,
):
    """Capture the physical and logical inputs consumed by the native read builders."""
    from pathlib import Path

    from corpus_structure.schema.physical import (
        compile_physical,
        linkml_types_source,
        physical_source_closure,
    )

    from .types import SourceArtifact

    if physical_sources is None:
        root = Path(__file__).resolve().parents[1] / "model/semantic"
        sources = physical_source_closure("physical.yaml", lambda name: (root / name).read_bytes())
        types = linkml_types_source() if linkml_types is None else linkml_types
    else:
        sources = dict(physical_sources)
        if not sources or not isinstance(linkml_types, bytes):
            raise ValueError(
                "explicit Core projection inputs require physical closure and captured LinkML types"
            )
        types = linkml_types
    if target_metadata is None:
        compile_physical(sources, linkml_types=types)
    elif sources != target_metadata.info.get(
        "physical_sources"
    ) or types != target_metadata.info.get("physical_linkml_types"):
        raise ValueError("Core projection metadata differs from captured physical inputs")
    return (
        SourceArtifact(
            "native/data-operation-projections.py",
            Path(__file__).read_bytes()
            if captured_module_sources is None
            else captured_module_sources["semantic/data_operation_projections.py"],
        ),
        SourceArtifact("native/projection-linkml-types.yaml", types),
        *(
            SourceArtifact("native/projection-physical/" + name, content)
            for name, content in sorted(sources.items())
        ),
    )
