"""Compile the declared producer, episode, use and population validity graph."""

from pglast import ast
from sqlalchemy import (
    Boolean,
    Integer,
    MetaData,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
    union,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, array
from sqlalchemy.types import NullType

from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    While,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)
from .native_program import (
    literal as pg_literal,
)


def _json(value):
    return cast(literal(value), JSONB())


def _items(value, name):
    return (
        func.jsonb_array_elements(func.coalesce(value, _json("[]")))
        .table_valued(column("value", JSONB()))
        .alias(name)
    )


def _rows(relation, *predicates):
    return select(core_relation_row(relation)).select_from(relation).where(*predicates)


def _row(name, relation, *fields):
    return tuple(core_variable(name, relation.c[field].type, field) for field in fields)


def _exists(relation, *conditions):
    return select(1).select_from(relation).where(*conditions).exists()


def _program(name, inputs, returns, body, locals_=(), *, columns=()):
    result = pg_type(returns)
    result.setof = bool(columns)
    return function(
        "ops",
        name,
        parameters=inputs,
        returns=result,
        table_columns=columns,
        body=Block(tuple(body), tuple(locals_)),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        security_definer=True,
    )


def _reference_program(model):
    from .support_edges import declared_support_references

    reference = core_variable("reference", JSONB())
    choices = tuple(
        (
            reference[field].astext.in_(values)
            if values is not None
            else reference[field].astext.is_not(None),
            kind,
            identity,
        )
        for _, kind, field, values, identity in declared_support_references(model)
    )
    kind = case(*((condition, kind) for condition, kind, _ in choices), else_=None)
    identity = case(
        *((condition, reference[field].astext) for condition, _, field in choices), else_=None
    )
    identity_type = case(
        *((condition, func.jsonb_typeof(reference[field])) for condition, _, field in choices),
        else_=None,
    )
    return _program(
        "ddo_support_reference_node",
        (Parameter("reference", pg_type("jsonb")),),
        "jsonb",
        (
            If(
                or_(
                    func.jsonb_typeof(reference).is_distinct_from("object"),
                    identity_type.is_distinct_from("string"),
                    func.nullif(identity, "").is_(None),
                ),
                (Raise("unrecognized native support reference", "23514"),),
            ),
            Return(func.jsonb_build_object("kind", kind, "id", identity)),
        ),
    )


def _edge_program(model, parameters, kind, node_id):
    from .support_edges import support_edge_queries

    return _program(
        "ddo_validity_edges",
        parameters,
        "record",
        (ReturnQuery(union_all(*support_edge_queries(model, kind, node_id, "validity"))),),
        columns=(
            ("alternative", pg_type("int4")),
            ("child_kind", pg_type("text")),
            ("child_id", pg_type("text")),
        ),
    )


def _direct_program(model, parameters, kind, node_id):
    requests = model.tables["ops.data_request"]
    episodes = model.tables["ops.data_derivation"]
    definitions = model.tables["sem.data_operation_definition"]
    revoked = model.tables["ops.data_revocation"]
    outputs = model.tables["ops.data_derivation_output"]
    uses = model.tables["ops.demand_use"]
    support = model.tables["ops.data_derivation_support"]
    originals = model.tables["ops.original_source_admission"]
    populations = model.tables["ops.data_population"]
    boundary = core_variable("boundary", NullType())
    (boundary_id,) = _row("boundary", model.tables["ops.data_demand_read"], "id")
    use_fate, use_derivation, demand_id, selection = _row(
        "u",
        uses,
        "fate",
        "derivation_id",
        "demand_id",
        "selection",
    )
    population_id, population_demand, evidence, name, context, created = _row(
        "pop",
        populations,
        "id",
        "demand_id",
        "evidence",
        "name",
        "context_key",
        "created_at",
    )
    from .validity_programs import family_validity

    validity = family_validity(definitions, node_id)
    producing = episodes.join(requests, requests.c.id == episodes.c.request_id)
    admitted_producer = _exists(
        producing.join(
            definitions,
            and_(
                definitions.c.release_id == episodes.c.release_id,
                definitions.c.recipe == episodes.c.recipe,
                definitions.c.operation_id == requests.c.operation_id,
            ),
        ),
        episodes.c.id == node_id,
        episodes.c.outcome.in_(("success", "empty")),
        validity,
    )
    scope = func.ops.ddo_scope(requests.c.project_id, requests.c.original_source)
    hit = _exists(
        producing.join(revoked, revoked.c.scope == scope),
        episodes.c.id == node_id,
        or_(
            *(
                and_(revoked.c.selector_kind == field, revoked.c.selector == candidate)
                for field, candidate in (
                    ("derivation", episodes.c.id),
                    ("recipe", episodes.c.recipe),
                    ("runtime", episodes.c.runtime_id),
                )
            ),
            and_(
                revoked.c.selector_kind == "product",
                select(1)
                .select_from(outputs)
                .where(
                    outputs.c.derivation_id == episodes.c.id,
                    outputs.c.product_id == revoked.c.selector,
                )
                .correlate(episodes, revoked)
                .exists(),
            ),
        ),
    )
    support_use = uses.alias("selected_support_use")
    valid_episode = and_(
        _exists(episodes, episodes.c.id == node_id),
        ~_exists(
            support.outerjoin(
                support_use,
                and_(
                    support_use.c.id == support.c.admission_use_id,
                    support_use.c.derivation_id == support.c.support_derivation_id,
                ),
            ),
            support.c.derivation_id == node_id,
            support.c.admission_use_id.is_not(None),
            support_use.c.id.is_(None),
        ),
    )
    pop_refs = _items(selection["populations"], "selected_population")
    refs = _items(selection["support"], "support_ref")
    ref = refs.c.value
    use_valid = and_(
        func.coalesce(use_fate == "fulfilled", False),
        use_derivation.is_not(None),
        ~_exists(
            pop_refs.outerjoin(
                populations,
                and_(
                    populations.c.id == pop_refs.c.value["population_id"].astext,
                    populations.c.demand_id == demand_id,
                ),
            ),
            populations.c.id.is_(None),
        ),
        ~_exists(
            refs.outerjoin(
                support_use,
                and_(
                    support_use.c.id == ref["admission_use_id"].astext,
                    support_use.c.derivation_id == ref["derivation_id"].astext,
                ),
            ).outerjoin(
                originals,
                and_(
                    originals.c.id == ref["admission_id"].astext,
                    originals.c.source_reference == ref["source_reference"].astext,
                ),
            ),
            or_(
                and_(ref["admission_use_id"].astext.is_not(None), support_use.c.id.is_(None)),
                and_(
                    ref["kind"].astext.in_(("original-source", "authored")),
                    originals.c.id.is_(None),
                ),
            ),
        ),
    )
    valid_population = and_(
        population_id.is_not(None),
        _exists(
            uses,
            uses.c.id == evidence["admission_use_id"].astext,
            uses.c.demand_id == population_demand,
            uses.c.derivation_id == evidence["derivation_id"].astext,
        ),
        or_(
            ~evidence.has_key("selection"),
            _exists(
                populations,
                populations.c.id == evidence["selection"]["parent_population_id"].astext,
                populations.c.demand_id == population_demand,
                populations.c.id != population_id,
            ),
        ),
        ~_exists(
            populations,
            populations.c.demand_id == population_demand,
            populations.c.name == name,
            populations.c.context_key == context,
            tuple_(populations.c.created_at, populations.c.id) > tuple_(created, population_id),
            or_(
                boundary_id.is_(None),
                func.ops.ddo_read_visible(
                    populations.c.created_at, populations.c.created_xid, boundary
                ),
            ),
        ),
    )
    return _program(
        "ddo_validity_direct",
        parameters,
        "bool",
        (
            If(kind == "producer", (Return(and_(admitted_producer, ~hit)),)),
            If(kind == "episode", (Return(valid_episode),)),
            If(
                kind == "original",
                (
                    SelectInto(_rows(originals, originals.c.id == node_id), ("admission",)),
                    Return(
                        func.ops.ddo_original_admission_valid(
                            core_variable("admission", NullType()), boundary
                        )
                    ),
                ),
            ),
            If(
                kind == "use",
                (SelectInto(_rows(uses, uses.c.id == node_id), ("u",)), Return(use_valid)),
            ),
            If(
                kind == "population",
                (
                    SelectInto(_rows(populations, populations.c.id == node_id), ("pop",)),
                    Return(valid_population),
                ),
            ),
            Return(literal(False)),
        ),
        (Local("u", uses), Local("pop", populations), Local("admission", originals)),
    )


def _seed(name, kind):
    values = (
        func.unnest(core_variable(name, ARRAY(Text())))
        .table_valued(column("id", Text()))
        .render_derived()
    )
    return select(cast(literal(kind), Text()).label("kind"), values.c.id)


def _edges(kind, identity, name):
    return (
        func.ops.ddo_validity_edges(kind, identity)
        .table_valued(
            column("alternative", Integer()),
            column("child_kind", Text()),
            column("child_id", Text()),
        )
        .lateral(name)
    )


def _closure_program(boundary, array_type, empty):
    init = union(
        _seed("seed_uses", "use"),
        _seed("seed_episodes", "episode"),
        _seed("seed_populations", "population"),
    ).subquery("seeds")
    nodes = select(init).cte("nodes", recursive=True)
    edge = _edges(nodes.c.kind, nodes.c.id, "edge")
    nodes = nodes.union(
        select(edge.c.child_kind, edge.c.child_id)
        .select_from(nodes.join(edge, true()))
        .where(edge.c.child_id.is_not(None))
    )
    edge = _edges(nodes.c.kind, nodes.c.id, "adjacent")
    node_key = cast(func.jsonb_build_array(nodes.c.kind, nodes.c.id), Text())
    adjacency = (
        select(
            node_key.label("parent"),
            edge.c.alternative,
            case(
                (
                    edge.c.child_id.is_not(None),
                    cast(func.jsonb_build_array(edge.c.child_kind, edge.c.child_id), Text()),
                )
            ).label("child"),
        )
        .select_from(nodes.join(edge, true()))
        .cte("adjacency")
        .prefix_with("MATERIALIZED")
    )
    reach = (
        select(adjacency.c.parent, adjacency.c.child)
        .where(adjacency.c.child.is_not(None))
        .cte("reach", recursive=True)
    )
    reach = reach.union(
        select(reach.c.parent, adjacency.c.child)
        .select_from(
            reach.join(
                adjacency,
                adjacency.c.parent == reach.c.child,
            )
        )
        .where(adjacency.c.child.is_not(None))
    )
    cyclic = (
        select(1)
        .select_from(reach)
        .where(reach.c.parent == node_key, reach.c.child == reach.c.parent)
        .correlate(nodes)
        .exists()
    )
    direct = (
        select(
            nodes.c.kind,
            nodes.c.id,
            node_key.label("key"),
            and_(
                func.ops.ddo_validity_direct(
                    nodes.c.kind, nodes.c.id, core_variable("boundary", NullType())
                ),
                ~cyclic,
            ).label("valid"),
        )
        .select_from(nodes)
        .cte("direct")
        .prefix_with("MATERIALIZED")
    )
    facts = core_variable("facts", JSONB())
    edges = core_variable("edges", JSONB())
    good = core_variable("good", ARRAY(Text()))
    added = core_variable("added", ARRAY(Text()))
    facts_rows = _items(facts, "fact")
    edge_rows = _items(edges, "known_edge")
    seen = facts_rows.c.value
    node = seen["key"].astext
    proof = edge_rows.c.value
    ready = (
        select(1)
        .select_from(edge_rows)
        .where(proof["parent"].astext == node)
        .group_by(proof["alternative"].astext)
        .having(
            func.bool_and(or_(proof["child"].astext.is_(None), proof["child"].astext == any_(good)))
        )
        .correlate(facts_rows)
        .exists()
    )
    next_wave = (
        select(func.coalesce(func.array_agg(node), array((), type_=Text())))
        .select_from(facts_rows)
        .where(
            cast(seen["valid"].astext, Boolean()),
            ~(node == any_(good)),
            ready,
        )
    )
    from .native_program import Exit

    def pack(rows):
        return (
            select(func.coalesce(func.jsonb_agg(func.to_jsonb(rows.table_valued())), _json("[]")))
            .select_from(rows)
            .scalar_subquery()
        )

    return _program(
        "ddo_valid_closure",
        (
            Parameter("seed_uses", array_type),
            Parameter("seed_episodes", array_type),
            boundary,
            Parameter("seed_populations", array_type, empty),
        ),
        "record",
        (
            SelectInto(select(pack(direct), pack(adjacency)), ("facts", "edges")),
            While(
                literal(True),
                (
                    SelectInto(next_wave, ("added",)),
                    If(func.cardinality(added) == 0, (Exit(),)),
                    Assign("good", good.op("||")(added)),
                ),
            ),
            ReturnQuery(
                select(seen["kind"].astext, seen["id"].astext, node == any_(good)).select_from(
                    facts_rows
                )
            ),
        ),
        (
            Local("facts", pg_type("jsonb")),
            Local("edges", pg_type("jsonb")),
            Local("good", array_type, empty),
            Local("added", array_type),
        ),
        columns=(("kind", pg_type("text")), ("id", pg_type("text")), ("valid", pg_type("bool"))),
    )


def data_validity_sql(model: MetaData) -> str:
    parameters = (Parameter("p_kind", pg_type("text")), Parameter("p_id", pg_type("text")))
    demand_read = pg_type("ops", "data_demand_read")
    boundary = Parameter("boundary", demand_read, ast.A_Const(isnull=True))
    kind, identity = (core_variable(name, Text()) for name in ("p_kind", "p_id"))
    array_type = pg_type("text")
    array_type.arrayBounds = (ast.Integer(ival=-1),)
    empty = ast.TypeCast(arg=pg_literal("{}"), typeName=array_type)

    def selected(name):
        return case((kind == name, array([identity])), else_=array((), type_=Text()))

    closure = func.ops.ddo_valid_closure(
        selected("use"),
        selected("episode"),
        core_variable("boundary", NullType()),
        selected("population"),
    ).table_valued(column("kind", Text()), column("id", Text()), column("valid", Boolean()))
    found = (
        select(closure.c.valid)
        .where(closure.c.kind == kind, closure.c.id == identity)
        .scalar_subquery()
    )
    return native_sql_script(
        (
            _reference_program(model),
            _edge_program(model, parameters, kind, identity),
            _direct_program(
                model, (*parameters, Parameter("boundary", demand_read)), kind, identity
            ),
            _closure_program(boundary, array_type, empty),
            _program(
                "ddo_node_valid",
                (*parameters, boundary),
                "bool",
                (Return(func.coalesce(found, False)),),
            ),
        )
    )
