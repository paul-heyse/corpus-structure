"""Core-owned demand-scoped native read shapes and support closure.

Prepared SQL is captured alongside its explicit physical input closure. Runtime
reconstruction consumes those bytes rather than invoking current builders.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    BigInteger,
    Text,
    and_,
    cast,
    column,
    exists,
    false,
    func,
    literal,
    literal_column,
    null,
    or_,
    select,
    union,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, dialect
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.type_api import TypeEngine

from .data_operation_json import ContextJSONB


def _json(value):
    import json

    return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB)


def _var[T](name: str, kind: type[TypeEngine[T]]) -> ColumnClause[T]:
    return literal_column(name, type_=kind())


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


def _visible(table):
    return func.ops.ddo_read_visible(
        table.c.created_at, table.c.created_xid, literal_column("boundary")
    )


def _node(kind, identity):
    kind_value = literal(kind) if isinstance(kind, str) else kind
    return select(cast(kind_value, Text).label("kind"), cast(identity, Text).label("id"))


def _reference_node(reference):
    from sqlalchemy import case

    original = reference["kind"].astext == "original-source"
    use = reference["admission_use_id"].astext.is_not(None)
    return (
        case((original, literal("original")), (use, literal("use")), else_=literal("episode")),
        case((original, reference["admission_id"].astext), (use, reference["admission_use_id"].astext), else_=reference["derivation_id"].astext),
    )


def _support_walk(metadata, seed):
    """Visit finite receipt nodes, including explicitly selected replacement support.

    Indexed per-node lateral lookups avoid materializing every historical edge.
    UNION deduplicates nodes; this is reachability, never all-path expansion.
    """
    support = metadata.tables["ops.data_derivation_support"]
    original_support = metadata.tables["ops.data_derivation_original_support"]
    uses = metadata.tables["ops.demand_use"]
    populations = metadata.tables["ops.data_population"]
    closure = select(seed.c.kind, seed.c.id).where(seed.c.id.is_not(None)).cte("support_closure", recursive=True)
    reference = _items(func.coalesce(uses.c.selection["support"], _json([])), "selected_support_reference")
    population_ref = _items(func.coalesce(uses.c.selection["populations"], _json([])), "selected_population_reference")
    reference_kind, reference_id = _reference_node(reference.c.value)
    from sqlalchemy import case

    edge_queries = (
        _node(case((support.c.admission_use_id.is_not(None), literal("use")), else_=literal("episode")), func.coalesce(support.c.admission_use_id, support.c.support_derivation_id)).where(closure.c.kind == "episode", support.c.derivation_id == closure.c.id),
        _node("original", original_support.c.admission_id).where(closure.c.kind == "episode", original_support.c.derivation_id == closure.c.id),
        _node("episode", uses.c.derivation_id).where(closure.c.kind == "use", uses.c.id == closure.c.id),
        _node(reference_kind, reference_id).select_from(uses.join(reference, literal(True))).where(closure.c.kind == "use", uses.c.id == closure.c.id),
        _node("population", populations.c.id).select_from(uses.join(population_ref, literal(True)).join(populations, and_(populations.c.id == population_ref.c.value["population_id"].astext, populations.c.demand_id == uses.c.demand_id))).where(closure.c.kind == "use", uses.c.id == closure.c.id),
        _node("use", uses.c.id).select_from(populations.join(uses, and_(uses.c.id == populations.c.evidence["admission_use_id"].astext, uses.c.derivation_id == populations.c.evidence["derivation_id"].astext, uses.c.demand_id == populations.c.demand_id))).where(closure.c.kind == "population", populations.c.id == closure.c.id),
        _node("population", populations.c.evidence["selection"]["parent_population_id"].astext).where(closure.c.kind == "population", populations.c.id == closure.c.id),
    )
    edges = union_all(*(query.correlate(closure) for query in edge_queries)).lateral("support_edge")
    return closure.union(select(edges.c.kind, edges.c.id).select_from(closure.join(edges, literal(True))).where(edges.c.id.is_not(None)))


def _scope_projection(metadata, nodes, project, direct_sources):
    episodes = metadata.tables["ops.data_derivation"]
    requests = metadata.tables["ops.data_request"]
    admissions = metadata.tables["ops.original_source_admission"]
    sources = union(
        direct_sources,
        select(requests.c.original_source.label("source")).select_from(nodes.join(episodes, and_(nodes.c.kind == "episode", episodes.c.id == nodes.c.id)).join(requests, requests.c.id == episodes.c.request_id)).where(requests.c.project_id == project),
        select(admissions.c.original_source.label("source")).select_from(nodes.join(admissions, and_(nodes.c.kind == "original", admissions.c.id == nodes.c.id))).where(admissions.c.project_id == project),
    ).cte("support_sources")
    scope = func.ops.ddo_scope(project, sources.c.source)
    return select(scope.label("scope")).where(sources.c.source.is_not(None)).order_by(scope)


def support_scopes(metadata):
    """Pinned reader validity and publication use the same selected-support walk."""
    demand, project = _var("d.id", Text), _var("d.project_id", Text)
    selection = _var("d.selection", JSONB)
    root = _items(_var("d.root", JSONB), "root")
    sets = _each(func.coalesce(selection["source_sets"], _json({})), "source_set")
    entry = _items(sets.c.value, "source_entry")
    source_entries = select(entry.c.value.label("entry")).select_from(sets.join(entry, literal(True))).cte("source_entries")
    uses = metadata.tables["ops.demand_use"]
    populations = metadata.tables["ops.data_population"]
    episodes = metadata.tables["ops.data_derivation"]
    outputs = metadata.tables["ops.data_derivation_output"]
    requests = metadata.tables["ops.data_request"]
    admissions = metadata.tables["ops.original_source_admission"]
    selected_uses = select(uses.c.obligation_id, uses.c.id, uses.c.fate).where(uses.c.demand_id == demand, _visible(uses)).distinct(uses.c.obligation_id).order_by(uses.c.obligation_id, uses.c.created_at.desc(), uses.c.id.desc()).cte("selected_use_seeds")
    external = exists(select(1).select_from(source_entries).where(func.ops.ddo_semantic_source_reference(source_entries.c.entry["reference"]), source_entries.c.entry["product"].astext == outputs.c.product_id))
    seed = union(
        _node("use", selected_uses.c.id).where(selected_uses.c.fate == "fulfilled"),
        _node("population", populations.c.id).where(populations.c.demand_id == demand, _visible(populations)),
        _node("use", uses.c.id).select_from(episodes.join(outputs, outputs.c.derivation_id == episodes.c.id).join(uses, uses.c.derivation_id == episodes.c.id).join(requests, requests.c.id == episodes.c.request_id)).where(requests.c.project_id == project, external, uses.c.fate == "fulfilled", _visible(uses)),
        _node("original", admissions.c.id).where(admissions.c.demand_id == demand, _visible(admissions)),
    ).cte("support_seed")
    direct = union(select(root.c.value["original_source"].astext.label("source")), select(source_entries.c.entry["original_source"].astext)).cte("direct_sources")
    return _scope_projection(metadata, _support_walk(metadata, seed), project, select(direct.c.source))


def lock_support_scopes(metadata):
    reference = _items(_var("support", JSONB), "root_support_reference")
    kind, identity = _reference_node(reference.c.value)
    seed = _node(kind, identity).select_from(reference).cte("support_seed")
    return _scope_projection(metadata, _support_walk(metadata, seed), _var("project", Text), select(_var("source", Text).label("source")))


def binding_row_contract():
    """The labeled result SELECT is the native/Python row-shape authority."""
    fields: tuple[tuple[str, TypeEngine[Any]], ...] = (
        ("product", Text()),
        ("kind_contract", Text()),
        ("subject", Text()),
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
        item.name
        for item in binding_columns()
        if item.name not in {"body", "meaning_body", "support_references"}
    )


def compiled(statement):
    return str(
        statement.compile(
            dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
    )


def native_return_shape():
    pg = dialect()
    return ",".join(
        pg.identifier_preparer.quote_identifier(item.name) + " " + item.type.compile(dialect=pg)
        for item in binding_columns()
    )


def binding_branches(metadata):
    demand, project, release = _var("d.id", Text), _var("d.project_id", Text), _var("d.release_id", Text)
    selection = _var("d.selection", JSONB)
    operation_id, subject, source = _var("p_operation", Text), _var("p_subject", Text), _var("p_source", Text)
    scope = _var("p_scope", JSONB)
    boundary = literal_column("boundary")
    definitions = metadata.tables["sem.data_operation_definition"]
    roles = _items(definitions.c.input_roles, "input_role")
    entries = _items(
        func.coalesce(
            selection["source_sets"][roles.c.value["support"]["source_set"].astext], _json([])
        ),
        "entry",
    )
    pins = (
        select(entries.c.value.label("entry"))
        .select_from(definitions.join(roles, literal(True)).join(entries, literal(True)))
        .where(
            definitions.c.release_id == release,
            definitions.c.operation_id == operation_id,
            func.ops.ddo_semantic_source_reference(entries.c.value["reference"]),
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
    member_roles = metadata.tables["kb.data_member_role"].alias("member_role")
    later = metadata.tables["ops.demand_use"].alias("later")
    selected_operations = _items(selection["operations"], "selected_operation")
    exact_pin = exists(
        select(1)
        .select_from(pins)
        .where(
            pins.c.entry["product"].astext == products.c.id,
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
    distinct = (
        episodes.c.id,
        outputs.c.role,
        outputs.c.position,
        products.c.id,
        outputs.c.member_id,
    )
    admitted = (
        select(
            products.c.id.label("product_id"),
            products.c.kind_contract.label("parent_kind"),
            products.c.subject.label("parent_subject"),
            products.c.original_source.label("parent_source"),
            products.c.analyzed_scope.label("parent_scope"),
            products.c.canonical_body,
            outputs.c.member_id.label("output_member"),
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
            or_(uses.c.demand_id == demand, exact_pin),
            uses.c.fate == "fulfilled",
            products.c.project_id == project,
            _visible(uses),
            func.ops.ddo_use_valid(uses.table_valued(), boundary),
            allowed_producer,
            or_(exact_pin, ~later_exists),
        )
        .distinct(*distinct)
        .order_by(*distinct, uses.c.id)
        .cte("admitted")
        .prefix_with("MATERIALIZED")
    )
    projected = union_all(
        select(
            cast(null(), Text).label("member_id"),
            admitted.c.parent_kind.label("projected_kind"),
            admitted.c.parent_subject.label("projected_subject"),
            admitted.c.parent_source.label("projected_source"),
            admitted.c.parent_scope.label("projected_scope"),
            admitted.c.canonical_body.label("projected_body"),
        ).where(admitted.c.output_member.is_(None)),
        select(
            members.c.member_id,
            members.c.kind_contract,
            members.c.subject,
            members.c.original_source,
            members.c.analyzed_scope,
            members.c.body,
        ).where(
            members.c.product_id == admitted.c.product_id,
            or_(
                admitted.c.output_member.is_(None), admitted.c.output_member == members.c.member_id
            ),
        ),
    ).lateral("projected")
    header = _obj(subject=projected.c.projected_subject, meaning_body=projected.c.projected_body)
    full_header = _obj(
        product=admitted.c.product_id,
        member=projected.c.member_id,
        subject=projected.c.projected_subject,
        original_source=projected.c.projected_source,
        analyzed_scope=projected.c.projected_scope,
        meaning_body=projected.c.projected_body,
    )
    admitted_role = exists(
        select(1)
        .select_from(definitions.join(roles, literal(True)))
        .where(
            definitions.c.release_id == release,
            definitions.c.operation_id == operation_id,
            roles.c.value["accepted_kind_contracts"].op("?")(projected.c.projected_kind),
            func.coalesce(roles.c.value["support"]["origins"], _json(["computation"])).op("?")(
                literal("computation")
            ),
            or_(
                subject.is_(None),
                func.ops.ddo_binding_subject(roles.c.value, header, subject, source),
            ),
            or_(
                roles.c.value["subject_field"].astext.is_not(None),
                roles.c.value["subject_target"].astext == "source-set",
                projected.c.projected_scope.is_not_distinct_from(scope),
            ),
            func.ops.ddo_binding_source(
                roles.c.value,
                full_header,
                source,
                func.coalesce(selection["source_sets"], _json({})),
            ),
        )
    )
    candidates = (
        select(
            *admitted.c,
            *projected.c,
            cast(
                func.coalesce(member_roles.c.position, admitted.c.output_position), BigInteger
            ).label("occurrence_position"),
            cast(
                func.coalesce(member_roles.c.multiplicity, admitted.c.output_multiplicity),
                BigInteger,
            ).label("occurrence_multiplicity"),
        )
        .select_from(
            admitted.join(projected, literal(True)).outerjoin(
                member_roles,
                and_(
                    member_roles.c.product_id == admitted.c.product_id,
                    member_roles.c.member_id == projected.c.member_id,
                ),
            )
        )
        .where(admitted_role)
        .cte("candidates")
        .prefix_with("MATERIALIZED")
    )
    coverage = metadata.tables["kb.data_member_coverage"].alias("coverage_row")
    coverage_query = (
        select(
            _aggregate(
                func.to_jsonb(coverage.table_valued())
                .op("-")(literal("product_id"))
                .op("-")(literal("member_id")),
                coverage.c.ordinal,
            )
        )
        .where(
            coverage.c.product_id == candidates.c.product_id,
            coverage.c.member_id == candidates.c.member_id,
        )
        .scalar_subquery()
    )
    evidence = _obj(
        demand_id=demand,
        use_id=candidates.c.use_id,
        trust_snapshot=_var("snapshot", JSONB),
        read_id=_var("boundary.id", Text),
        read_snapshot=_var("boundary.read_snapshot", Text),
        frontier_at=literal_column("boundary.frontier_at"),
    )
    computed_values = (
        candidates.c.product_id,
        candidates.c.projected_kind,
        candidates.c.projected_subject,
        candidates.c.projected_source,
        candidates.c.projected_scope,
        coverage_query,
        func.jsonb_build_array(candidates.c.episode_id),
        func.jsonb_build_array(
            _obj(
                kind=literal("computation"),
                derivation_id=candidates.c.episode_id,
                admission_use_id=candidates.c.use_id,
            )
        ),
        evidence,
        candidates.c.occurrence_position,
        candidates.c.occurrence_multiplicity,
        candidates.c.member_id,
        func.ops.ddo_episode_provider_identity(candidates.c.episode_id),
        candidates.c.producer_operation,
        func.data.ddo_json(candidates.c.projected_body),
        candidates.c.projected_body,
    )
    computed = select(
        *(
            cast(value, field.type).label(field.name)
            for field, value in zip(binding_columns(), computed_values, strict=True)
        )
    ).where(
        func.ops.ddo_kind_access(candidates.c.parent_kind),
        func.ops.ddo_kind_access(candidates.c.projected_kind),
    )
    admissions = metadata.tables["ops.original_source_admission"].alias("admission")
    factual_header = _obj(subject=admissions.c.subject, meaning_body=products.c.canonical_body)
    factual_role = exists(
        select(1)
        .select_from(definitions.join(roles, literal(True)))
        .where(
            definitions.c.release_id == release,
            definitions.c.operation_id == operation_id,
            roles.c.value["accepted_kind_contracts"].op("?")(products.c.kind_contract),
            func.coalesce(roles.c.value["support"]["origins"], _json(["computation"])).op("?")(
                literal("original-source")
            ),
            or_(
                subject.is_(None),
                func.ops.ddo_binding_subject(roles.c.value, factual_header, subject, source),
            ),
            or_(
                roles.c.value["subject_field"].astext.is_not(None),
                admissions.c.analyzed_scope.is_not_distinct_from(scope),
            ),
            or_(source.is_(None), admissions.c.original_source == source),
        )
    )
    fact = (
        select(*admissions.c, products.c.kind_contract, products.c.canonical_body)
        .select_from(admissions.join(products, products.c.id == admissions.c.product_id))
        .where(
            admissions.c.demand_id == demand,
            admissions.c.project_id == project,
            _visible(admissions),
            func.ops.ddo_original_admission_valid(admissions.table_valued(), boundary),
            factual_role,
        )
        .cte("factual")
        .prefix_with("MATERIALIZED")
    )
    refs = _aggregate(
        _obj(
            kind=literal("original-source"),
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
        frontier_at=literal_column("boundary.frontier_at"),
    )
    original_values = (
        fact.c.product_id,
        fact.c.kind_contract,
        fact.c.subject,
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
        func.data.ddo_json(fact.c.canonical_body),
        fact.c.canonical_body,
    )
    original = (
        select(
            *(
                cast(value, field.type).label(field.name)
                for field, value in zip(binding_columns(), original_values, strict=True)
            )
        )
        .where(func.ops.ddo_kind_access(fact.c.kind_contract))
        .group_by(
            fact.c.product_id,
            fact.c.kind_contract,
            fact.c.subject,
            fact.c.original_source,
            fact.c.analyzed_scope,
            fact.c.canonical_body,
        )
    )
    return computed, original


def read_page(metadata):
    """One pure atomic page under already acquired native pins."""
    from sqlalchemy import case

    demand, selection = _var("d.id", Text), _var("d.selection", JSONB)
    boundary = literal_column("boundary")
    obligations = metadata.tables["ops.data_obligation"]
    uses = metadata.tables["ops.demand_use"]
    episodes = metadata.tables["ops.data_derivation"]
    intents = metadata.tables["ops.data_completion_intent"]
    products = metadata.tables["kb.data_product"]
    outputs = metadata.tables["ops.data_derivation_output"]
    requests = metadata.tables["ops.data_request"]
    definitions = metadata.tables["sem.data_operation_definition"]
    bounded = (
        select(obligations)
        .where(
            obligations.c.demand_id == demand,
            obligations.c.id > _var("after_key", Text),
            _visible(obligations),
        )
        .order_by(obligations.c.id)
        .limit(_var("lim", BigInteger))
        .cte("bounded")
        .prefix_with("MATERIALIZED")
    )
    latest = (
        select(uses)
        .where(uses.c.obligation_id == bounded.c.id, _visible(uses))
        .order_by(uses.c.created_at.desc(), uses.c.id.desc())
        .limit(1)
        .correlate(bounded)
        .lateral("latest")
    )
    selected_uses = (
        select(latest)
        .select_from(bounded.join(latest, literal(True)))
        .cte("selected_uses")
        .prefix_with("MATERIALIZED")
    )
    valid = func.ops.ddo_use_valid(selected_uses.table_valued(), boundary)
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
    product_value = _obj(
        role=outputs.c.role,
        position=outputs.c.position,
        multiplicity=outputs.c.multiplicity,
        product_id=outputs.c.product_id,
        member_id=outputs.c.member_id,
        kind_contract=products.c.kind_contract,
        subject=products.c.subject,
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
        .where(outputs.c.derivation_id == selected_uses.c.derivation_id)
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
    result_uses = select(
        _aggregate(
            _obj(
                use_id=selected_uses.c.id,
                obligation_id=selected_uses.c.obligation_id,
                fate=case((fulfilled_invalid, literal("unavailable")), else_=selected_uses.c.fate),
                historical_fate=selected_uses.c.fate,
                semantic_outcome=semantic_outcome,
                completion_state=completion_state,
                request_id=selected_uses.c.request_id,
                generation=selected_uses.c.generation,
                derivation_id=selected_uses.c.derivation_id,
                rebind_derivation=case(
                    (
                        and_(
                            fulfilled_invalid,
                            func.ops.ddo_direct_support_valid(selected_uses.c.derivation_id),
                            _var("d.strength", Text) == "value",
                            rebind_allowed,
                        ),
                        selected_uses.c.derivation_id,
                    ),
                    else_=null(),
                ),
                selection=selected_uses.c.selection,
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
    obligation_body = (
        func.to_jsonb(bounded.table_valued())
        .op("-")(literal("created_at"))
        .op("-")(literal("created_xid"))
        .op("||")(
            _obj(
                obligation_id=bounded.c.id,
                historical_fate=latest.c.fate,
                fate=case(
                    (
                        and_(
                            latest.c.fate == "fulfilled",
                            func.ops.ddo_use_valid(latest.table_valued(), boundary) == false(),
                        ),
                        literal("unavailable"),
                    ),
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
            select(1)
            .select_from(obligations)
            .where(
                obligations.c.demand_id == demand,
                obligations.c.id > next_key,
                _visible(obligations),
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
            bounded.c.original_source == admissions.c.original_source,
            bounded.c.analyzed_scope == admissions.c.analyzed_scope,
        )
    )
    result_admissions = (
        select(_aggregate(admission_value, admissions.c.id))
        .select_from(admissions.join(products, products.c.id == admissions.c.product_id))
        .where(
            admissions.c.demand_id == demand,
            func.ops.ddo_original_admission_valid(admissions.table_valued(), boundary),
            func.ops.ddo_kind_access(products.c.kind_contract),
            in_page,
        )
        .scalar_subquery()
    )
    failures = metadata.tables["ops.data_attempt_failure"]
    failure_value = _obj(
        failure_id=failures.c.id,
        request_id=failures.c.request_id,
        generation=failures.c.generation,
        task_id=failures.c.task_id,
        attempt=failures.c.attempt,
        holder=failures.c.holder,
        failure=failures.c.failure,
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
    populations = metadata.tables["ops.data_population"]
    population_value = (
        func.to_jsonb(populations.table_valued())
        .op("-")(literal("created_at"))
        .op("-")(literal("created_xid"))
        .op("-")(literal("selected_obligation_id"))
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
            populations.c.demand_id == demand,
            or_(
                populations.c.selected_obligation_id.is_(None),
                populations.c.selected_obligation_id.in_(select(bounded.c.id)),
            ),
            _visible(populations),
            func.ops.ddo_population_valid(populations.table_valued(), boundary),
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
    pins = dict(
        demand_id=demand,
        selection=selection,
        trust_snapshot=_var("snapshot", JSONB),
        read_id=_var("boundary.id", Text),
        read_snapshot=_var("boundary.read_snapshot", Text),
        frontier_at=literal_column("boundary.frontier_at"),
        view=_var("selected_view", Text),
    )
    continuation = case(
        (more, _obj(**pins, after=next_key, limit=_var("lim", BigInteger))), else_=null()
    )
    return select(
        _obj(
            payload=_obj(
                **pins,
                intent=selection,
                root=_var("d.root", JSONB),
                project_id=_var("d.project_id", Text),
                release_id=_var("d.release_id", Text),
                runtime_id=_var("d.runtime_id", Text),
                state=state,
                uses=result_uses,
                obligations=result_obligations,
                original_source_admissions=result_admissions,
                attempt_failures=result_failures,
                populations=result_populations,
                continuation=continuation,
            )
        ).label("result")
    )


def capture_projection_sources(*, physical_sources=None, linkml_types=None):
    """Acquire explicit physical bytes and the generated native products together."""
    from pathlib import Path

    from corpus_structure.schema.physical import (
        compile_physical,
        linkml_types_source,
        physical_source_closure,
    )

    from .identity import canonical_bytes
    from .types import SourceArtifact

    if physical_sources is None:
        root = Path(__file__).resolve().parents[1] / "model/semantic"
        sources = physical_source_closure("physical.yaml", lambda name: (root / name).read_bytes())
        types = linkml_types_source() if linkml_types is None else linkml_types
    else:
        sources = dict(physical_sources)
        if not sources or not isinstance(linkml_types, bytes):
            raise ValueError("explicit Core projection inputs require physical closure and captured LinkML types")
        types = linkml_types
    metadata = compile_physical(sources, linkml_types=types)
    branches = binding_branches(metadata)
    products = {
        "support_scopes": compiled(support_scopes(metadata)),
        "lock_support_scopes": compiled(lock_support_scopes(metadata)),
        "binding_returns": native_return_shape(),
        "binding_computed": compiled(branches[0]),
        "binding_original": compiled(branches[1]),
        "read_page": compiled(read_page(metadata)),
    }
    return (
        SourceArtifact("native/data-operation-projections.py", Path(__file__).read_bytes()),
        SourceArtifact("native/data-operation-projections.json", canonical_bytes(products)),
        SourceArtifact("native/projection-linkml-types.yaml", types),
        *(
            SourceArtifact("native/projection-physical/" + name, content)
            for name, content in sorted(sources.items())
        ),
    )
