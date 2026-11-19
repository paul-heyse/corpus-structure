"""Compile recursive binding control over the frozen domain expression."""

from sqlalchemy import (
    Boolean,
    Integer,
    Numeric,
    Text,
    any_,
    cast,
    column,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by, array

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _binding_declarations(routines) -> tuple[ProgramDeclaration, ...]:
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operation-bindings:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in routines
    )


def _render_binding_programs(declarations, *, separator="") -> str:
    return separator.join(item.routine.render() + ";\n" for item in declarations)


def _elements(value, name="entry"):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _texts(value, name="entry"):
    return (
        func.jsonb_array_elements_text(value)
        .table_valued(column("value", Text()))
        .render_derived(name=name)
    )


def _each(value, name="entry"):
    return (
        func.jsonb_each(value)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .render_derived(name=name)
    )


def _value(name, type_=None):
    return core_variable(name, Text() if type_ is None else type_)


def _json(value):
    return cast(literal(value), JSONB())


def _check(condition, message, state="P0001"):
    return If(condition, (Raise(message, state),))


def _routine(
    name, steps, locals_=(), *, parameters=(("node", "jsonb"), ("context", "jsonb")), result="jsonb"
):
    return NativeRoutine(
        "ops",
        name,
        parameters=tuple(Parameter(name, pg_type(kind)) for name, kind in parameters),
        returns=pg_type(result),
        body=Block(tuple(steps), tuple(locals_)),
        strict=True,
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
    )


def _binding_exact_float_routine():
    value, digits, exact_text = (_value(name) for name in ("value", "digits", "exact_text"))
    result = _value("result", Numeric())
    fraction, exponent, shift, signum, index, digit = (
        _value(name, Integer())
        for name in ("fraction", "exponent", "shift", "signum", "i", "digit")
    )
    positions = (
        func.generate_series(1, func.length(digits))
        .table_valued(column("position", Integer()))
        .render_derived(name="hex_position")
    )
    integer_text = cast(func.trunc(result), Text())
    decimal_position = func.length(exact_text) + shift
    return _routine(
        "ddo_binding_float",
        (
            Perform(func.data.require_float_lexical(value)),
            If(
                func.left(value, 1) == "-",
                (Assign("signum", literal(-1)), Assign("value", func.substr(value, 2))),
            ),
            Assign("exponent", cast(func.split_part(value, "p", 2), Integer())),
            Assign("digits", func.substr(func.split_part(value, "p", 1), 3)),
            Assign("fraction", func.length(func.split_part(digits, ".", 2))),
            Assign("digits", func.replace(digits, ".", "")),
            ForQuery(
                ("i",),
                select(positions.c.position),
                (
                    Assign(
                        "digit", func.strpos("0123456789abcdef", func.substr(digits, index, 1)) - 1
                    ),
                    Assign("result", result * 16 + digit),
                ),
            ),
            Assign("shift", exponent - 4 * fraction),
            If(
                shift >= 0,
                (Return(signum * result * func.power(cast(literal(2), Numeric()), shift)),),
            ),
            Assign("result", result * func.power(cast(literal(5), Numeric()), -shift)),
            Assign("exact_text", func.lpad(integer_text, -shift + 1, "0")),
            If(func.length(integer_text) > -shift + 1, (Assign("exact_text", integer_text),)),
            Assign(
                "exact_text",
                func.substr(exact_text, 1, decimal_position)
                + "."
                + func.substr(exact_text, decimal_position + 1),
            ),
            Return(signum * cast(exact_text, Numeric())),
        ),
        tuple(Local(name, pg_type("text")) for name in ("digits", "exact_text"))
        + tuple(
            Local(name, pg_type("integer"))
            for name in ("fraction", "exponent", "shift", "i", "digit")
        )
        + (
            Local("result", pg_type("numeric"), literal(0)),
            Local("signum", pg_type("integer"), literal(1)),
        ),
        parameters=(("value", "text"),),
        result="numeric",
    )


def _binding_branch_native_routines():
    node, context, item, child, selected, definition, refs = (
        _value(name, JSONB())
        for name in ("node", "context", "item", "child", "selected", "definition", "refs")
    )
    result = _value("result", JSONB())
    role, name, choice = (_value(name) for name in ("role", "name", "choice"))
    names, active, inactive = (
        _value(name, ARRAY(Text())) for name in ("names", "active", "inactive")
    )
    matches = _value("matches", Integer())
    missing = _value("missing", Boolean())
    children = _elements(func.coalesce(node["children"], _json("[]")), "child_node")
    operands = _elements(func.coalesce(node["operands"], _json("[]")), "operand_node")
    name_rows = (
        func.unnest(names).table_valued(column("value", Text())).render_derived(name="role_name")
    )
    child_roles = (
        func.unnest(func.ops.ddo_binding_roles(child))
        .table_valued(column("value", Text()))
        .render_derived(name="child_role")
    )

    def scalar(value):
        return value.op("#>>", return_type=Text())(array([], type_=Text()))

    role_rows = _elements(node["roles"], "role_node")
    roledefs = _elements(context["roledefs"], "role_definition")
    choice_expr = func.coalesce(
        node["selected"].astext, context["choices"][node["choice_parameter"].astext].astext
    )
    selection = ForQuery(
        ("child",),
        select(children.c.value),
        (
            If(
                choice == any_(func.ops.ddo_binding_roles(child)),
                (
                    Assign("selected", child),
                    Assign("matches", matches + 1),
                ),
            ),
        ),
    )
    common = (
        Local("child", pg_type("jsonb")),
        Local("selected", pg_type("jsonb")),
        Local("choice", pg_type("text")),
        Local("matches", pg_type("integer"), literal(0)),
    )
    out = [
        _routine(
            "ddo_binding_missing",
            (
                ForQuery(
                    ("item",),
                    select(operands.c.value).where(operands.c.value["kind"].astext == "parameter"),
                    (
                        If(
                            ~context["parameters"].bool_op("?")(item["name"].astext),
                            (
                                Assign("definition", context["parameterdefs"][item["name"].astext]),
                                _check(
                                    or_(
                                        definition.is_(None),
                                        func.coalesce(definition["required"].astext, "true")
                                        != "false",
                                    ),
                                    "missing required frozen native parameter",
                                ),
                                Assign("missing", literal(True)),
                            ),
                        ),
                    ),
                ),
                ForQuery(
                    ("child",),
                    select(children.c.value),
                    (
                        Assign(
                            "missing",
                            func.ops.ddo_binding_missing(child, context, type_=Boolean()) | missing,
                        ),
                    ),
                ),
                Return(missing),
            ),
            (
                Local("item", pg_type("jsonb")),
                Local("child", pg_type("jsonb")),
                Local("definition", pg_type("jsonb")),
                Local("missing", pg_type("bool"), literal(False)),
            ),
            result="bool",
        )
    ]
    unique = (
        func.unnest(inactive)
        .table_valued(column("value", Text()))
        .render_derived(name="inactive_name")
    )
    # Array return types use the same PostgreSQL node as array locals.
    inactive_steps = (
        If(
            node["operator"].astext == "choice",
            (
                Assign("choice", choice_expr),
                selection,
                _check(matches != 1, "native branch choice is not uniquely frozen"),
                Assign("active", func.ops.ddo_binding_roles(selected)),
                ForQuery(
                    ("child",),
                    select(children.c.value),
                    (
                        If(
                            child != selected,
                            (
                                ForQuery(
                                    ("role",),
                                    select(child_roles.c.value),
                                    (
                                        If(
                                            ~(role == any_(active)),
                                            (
                                                Assign(
                                                    "inactive", func.array_append(inactive, role)
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                Return(inactive.concat(func.ops.ddo_binding_inactive(selected, context))),
            ),
        ),
        ForQuery(
            ("child",),
            select(children.c.value),
            (Assign("inactive", inactive.concat(func.ops.ddo_binding_inactive(child, context))),),
        ),
        Return(
            select(
                func.coalesce(
                    func.array_agg(aggregate_order_by(unique.c.value.distinct(), unique.c.value)),
                    array([], type_=Text()),
                )
            ).scalar_subquery()
        ),
    )
    out.append(
        NativeRoutine(
            "ops",
            "ddo_binding_inactive",
            parameters=(
                Parameter("node", pg_type("jsonb")),
                Parameter("context", pg_type("jsonb")),
            ),
            returns=pg_type_array(),
            body=Block(
                inactive_steps,
                (
                    *common,
                    Local("active", pg_type_array()),
                    Local("role", pg_type("text")),
                    Local("inactive", pg_type_array(), array([], type_=Text())),
                ),
            ),
            strict=True,
            volatility="immutable",
            search_path=("pg_catalog", "pg_temp"),
        )
    )
    entries = _each(refs, "population_reference")
    entry_key, entry_value = _value("entry_key"), _value("entry_value", JSONB())
    out.append(
        _routine(
            "ddo_binding_population_refs",
            (
                If(
                    node["operator"].astext == "choice",
                    (
                        Assign("choice", choice_expr),
                        ForQuery(
                            ("child",),
                            select(children.c.value),
                            (
                                If(
                                    choice == any_(func.ops.ddo_binding_roles(child)),
                                    (
                                        Assign(
                                            "result",
                                            func.ops.ddo_binding_population_refs(child, context),
                                        ),
                                        Assign("matches", matches + 1),
                                    ),
                                ),
                            ),
                        ),
                        _check(matches != 1, "population scope branch is not uniquely frozen"),
                        Return(result),
                    ),
                ),
                If(
                    node["operator"].astext.in_(("forall", "absent")),
                    (
                        SelectInto(
                            select(
                                func.coalesce(
                                    func.array_agg(scalar(role_rows.c.value)),
                                    array([], type_=Text()),
                                )
                            ),
                            ("names",),
                        ),
                        If(
                            func.cardinality(names) == 0,
                            (
                                SelectInto(
                                    select(
                                        func.coalesce(
                                            func.array_agg(roledefs.c.value["name"].astext),
                                            array([], type_=Text()),
                                        )
                                    ),
                                    ("names",),
                                ),
                            ),
                        ),
                        ForQuery(
                            ("name",),
                            select(name_rows.c.value),
                            (
                                Assign(
                                    "result",
                                    func.jsonb_set(result, array([name]), node["population"]),
                                ),
                            ),
                        ),
                    ),
                ),
                ForQuery(
                    ("item",),
                    select(operands.c.value).where(operands.c.value["kind"].astext == "population"),
                    (
                        _check(
                            ~node["operator"].astext.in_(("membership", "covers")),
                            "unsupported population operand scope",
                        ),
                        Assign(
                            "names",
                            func.ops.ddo_binding_roles(
                                func.jsonb_set(node, array(["children"]), _json("[]"))
                            ),
                        ),
                        _check(
                            func.cardinality(names) == 0,
                            "population operand lacks an identity-bearing role",
                        ),
                        ForQuery(
                            ("name",),
                            select(name_rows.c.value),
                            (
                                _check(
                                    result.bool_op("?")(name)
                                    & result[name].astext.is_distinct_from(item["name"].astext),
                                    "one role cannot carry two population scopes",
                                ),
                                Assign(
                                    "result", func.jsonb_set(result, array([name]), item["name"])
                                ),
                            ),
                        ),
                    ),
                ),
                ForQuery(
                    ("child",),
                    select(children.c.value),
                    (
                        Assign("refs", func.ops.ddo_binding_population_refs(child, context)),
                        ForQuery(
                            ("entry_key", "entry_value"),
                            select(entries.c.key, entries.c.value),
                            (
                                _check(
                                    result.bool_op("?")(entry_key)
                                    & result[entry_key].is_distinct_from(entry_value),
                                    "one role cannot carry two population scopes",
                                ),
                                Assign(
                                    "result",
                                    func.jsonb_set(result, array([entry_key]), entry_value),
                                ),
                            ),
                        ),
                    ),
                ),
                Return(result),
            ),
            (
                *common,
                Local("result", pg_type("jsonb"), _json("{}")),
                Local("names", pg_type_array()),
                Local("name", pg_type("text")),
                Local("item", pg_type("jsonb")),
                Local("refs", pg_type("jsonb")),
                Local("entry_key", pg_type("text")),
                Local("entry_value", pg_type("jsonb")),
            ),
        )
    )
    candidate = _value("candidate")
    population_projection = _routine(
        "ddo_binding_population_projection",
        (
            If(
                node["operator"].astext == "choice",
                (
                    Assign("choice", choice_expr),
                    ForQuery(
                        ("child",),
                        select(children.c.value),
                        (
                            If(
                                choice == any_(func.ops.ddo_binding_roles(child)),
                                (
                                    Return(
                                        func.ops.ddo_binding_population_projection(
                                            child, context, role
                                        )
                                    ),
                                ),
                            ),
                        ),
                    ),
                    Raise("population projection branch is not frozen", "P0001"),
                ),
            ),
            If(
                role == any_(func.ops.ddo_binding_roles(node.op("-")("children"))),
                (
                    If(
                        node["operator"].astext.in_(("forall", "absent")),
                        (Assign("projection", literal("member")),),
                    ),
                    ForQuery(
                        ("item",),
                        select(operands.c.value).where(
                            operands.c.value["kind"].astext == "population"
                        ),
                        (
                            Assign(
                                "candidate",
                                func.coalesce(item["population_projection"].astext, "member"),
                            ),
                            _check(
                                or_(
                                    ~candidate.in_(("member", "qualified-context")),
                                    (candidate == "qualified-context")
                                    & item["value_type"].astext.is_distinct_from("subject-context"),
                                ),
                                "invalid population projection",
                            ),
                            _check(
                                _value("projection").is_not(None)
                                & (_value("projection") != candidate),
                                "conflicting population projections",
                            ),
                            Assign("projection", candidate),
                        ),
                    ),
                ),
            ),
            ForQuery(
                ("child",),
                select(children.c.value),
                (
                    Assign(
                        "candidate",
                        func.ops.ddo_binding_population_projection(child, context, role),
                    ),
                    If(
                        candidate.is_not(None),
                        (
                            _check(
                                _value("projection").is_not(None)
                                & (_value("projection") != candidate),
                                "conflicting population projections",
                            ),
                            Assign("projection", candidate),
                        ),
                    ),
                ),
            ),
            Return(_value("projection")),
        ),
        (
            Local("child", pg_type("jsonb")),
            Local("item", pg_type("jsonb")),
            Local("projection", pg_type("text")),
            Local("candidate", pg_type("text")),
            Local("choice", pg_type("text")),
        ),
        parameters=(("node", "jsonb"), ("context", "jsonb"), ("role", "text")),
        result="text",
    )
    out.append(population_projection)
    return tuple(out)


def pg_type_array():
    from pglast import ast

    result = pg_type("text")
    result.arrayBounds = (ast.Integer(ival=-1),)
    return result


def _binding_population_native_routines():
    node, context = (_value(name, JSONB()) for name in ("node", "context"))
    names = _value("names", ARRAY(Text()))
    combinations = select(literal(0).label("n"), context["roles"].label("roles")).cte(
        "combinations", recursive=True
    )
    candidates = _elements(
        func.coalesce(context["roles"][names[combinations.c.n + 1]], _json("[]")), "candidate"
    )
    combinations = combinations.union_all(
        select(
            (combinations.c.n + 1).label("n"),
            func.jsonb_set(
                combinations.c.roles,
                array([names[combinations.c.n + 1]]),
                func.jsonb_build_array(candidates.c.value),
            ).label("roles"),
        )
        .select_from(combinations.join(candidates, literal(True)))
        .where(combinations.c.n < func.cardinality(names))
    )
    assignments_type = pg_type("jsonb")
    assignments_type.setof = True
    out = [
        NativeRoutine(
            "ops",
            "ddo_binding_assignments",
            parameters=(
                Parameter("node", pg_type("jsonb")),
                Parameter("context", pg_type("jsonb")),
            ),
            returns=assignments_type,
            body=Block(
                (
                    ReturnQuery(
                        select(
                            func.jsonb_set(context, array(["roles"]), combinations.c.roles)
                        ).where(combinations.c.n == func.cardinality(names))
                    ),
                ),
                (
                    Local(
                        "names",
                        pg_type_array(),
                        func.ops.ddo_binding_roles(
                            func.jsonb_set(node, array(["children"]), _json("[]"))
                        ),
                    ),
                ),
            ),
            strict=True,
            volatility="immutable",
            search_path=("pg_catalog", "pg_temp"),
        )
    ]
    members, evidence, result = (
        _value(name, JSONB()) for name in ("members", "evidence", "result")
    )
    identity, project, projection = (_value(name) for name in ("identity", "project", "projection"))
    complete = _value("complete", Boolean())
    entries = (
        func.jsonb_array_elements(members)
        .table_valued(column("value", JSONB()), with_ordinality="ordinal")
        .render_derived(name="member")
    )
    projected_context = func.jsonb_build_object(
        "project_id",
        project,
        "subject",
        entries.c.value["subject"],
        "subject_definition",
        entries.c.value["subject_definition"],
        "original_source",
        entries.c.value["original_source"],
        "analyzed_scope",
        entries.c.value["analyzed_scope"],
    )
    projected = _value("projected", JSONB())
    out.append(
        _routine(
            "ddo_project_population",
            (
                If(
                    projection == "qualified-context",
                    (
                        SelectInto(
                            select(
                                func.coalesce(
                                    func.jsonb_agg(
                                        aggregate_order_by(projected_context, entries.c.ordinal)
                                    ),
                                    _json("[]"),
                                )
                            ),
                            ("projected",),
                        ),
                    ),
                    (
                        If(
                            projection == "member",
                            (
                                SelectInto(
                                    select(
                                        func.coalesce(
                                            func.jsonb_agg(
                                                aggregate_order_by(
                                                    entries.c.value["member_id"], entries.c.ordinal
                                                )
                                            ),
                                            _json("[]"),
                                        )
                                    ),
                                    ("projected",),
                                ),
                            ),
                            (Raise("unknown population projection", "P0001"),),
                        ),
                    ),
                ),
                Assign(
                    "result",
                    func.jsonb_build_object(
                        "identity",
                        identity,
                        "complete",
                        complete,
                        "members",
                        projected,
                        "evidence",
                        evidence,
                    ),
                ),
                If(
                    projection == "qualified-context",
                    (
                        Assign(
                            "result",
                            result.op("||")(func.jsonb_build_object("projection", projection)),
                        ),
                    ),
                ),
                Return(result),
            ),
            (Local("projected", pg_type("jsonb")), Local("result", pg_type("jsonb"))),
            parameters=(
                ("identity", "text"),
                ("complete", "bool"),
                ("members", "jsonb"),
                ("evidence", "jsonb"),
                ("project", "text"),
                ("projection", "text"),
            ),
        )
    )
    witness = _value("witness", JSONB())
    episode = _value("episode")
    require_episode = _value("require_episode", Boolean())
    members_ = _elements(witness["members"], "population_member")
    member = members_.c.value
    keys = (
        func.jsonb_object_keys(member)
        .table_valued(column("key", Text()))
        .render_derived(name="member_key")
    )
    bad_plain = (
        select(member)
        .where(
            or_(
                func.jsonb_typeof(member).is_distinct_from("string"),
                member.op("#>>", return_type=Text())(array([], type_=Text())) == "",
            )
        )
        .exists()
    )
    bad_context = (
        select(member)
        .where(
            or_(
                func.jsonb_typeof(member) != "object",
                func.nullif(member["project_id"].astext, "").is_(None),
                func.nullif(member["subject"].astext, "").is_(None),
                func.nullif(member["subject_definition"].astext, "").is_(None),
                ~member.bool_op("?")("original_source"),
                ~func.jsonb_typeof(member["original_source"]).in_(("string", "null")),
                ~member.bool_op("?")("analyzed_scope"),
                select(func.count()).select_from(keys).correlate(members_).scalar_subquery() != 5,
            )
        )
        .exists()
    )
    invalid = or_(
        func.jsonb_typeof(witness).is_distinct_from("object"),
        func.jsonb_typeof(witness["identity"]).is_distinct_from("string"),
        func.nullif(witness["identity"].astext, "").is_(None),
        func.jsonb_typeof(witness["complete"]).is_distinct_from("boolean"),
        func.jsonb_typeof(witness["members"]).is_distinct_from("array"),
        func.jsonb_typeof(witness["evidence"]).is_distinct_from("object"),
        (func.coalesce(witness["projection"].astext, "member") == "member") & bad_plain,
        (witness["projection"].astext == "qualified-context") & bad_context,
        ~func.coalesce(witness["projection"].astext, "member").in_(("member", "qualified-context")),
        select(member).group_by(member).having(func.count() != 1).exists(),
    )
    out.append(
        _routine(
            "ddo_binding_population_meaning",
            (
                If(witness["reason"].astext == "unselected-declared-branch", (Return(witness),)),
                _check(invalid, "invalid structured native population witness"),
                Assign(
                    "result",
                    func.jsonb_build_object(
                        "identity",
                        witness["identity"],
                        "complete",
                        witness["complete"],
                        "members",
                        witness["members"],
                    ),
                ),
                If(
                    witness["projection"].astext == "qualified-context",
                    (
                        Assign(
                            "result",
                            result.op("||")(
                                func.jsonb_build_object("projection", "qualified-context")
                            ),
                        ),
                    ),
                ),
                If(
                    require_episode,
                    (
                        Assign(
                            "episode", func.nullif(witness["evidence"]["derivation_id"].astext, "")
                        ),
                        _check(episode.is_(None), "population episode identity is unavailable"),
                        Assign(
                            "result",
                            result.op("||")(
                                func.jsonb_build_object(
                                    "support_episodes", func.jsonb_build_array(episode)
                                )
                            ),
                        ),
                    ),
                ),
                Return(result),
            ),
            (Local("result", pg_type("jsonb")), Local("episode", pg_type("text"))),
            parameters=(("witness", "jsonb"), ("require_episode", "bool")),
        )
    )
    return tuple(out)


def _binding_consumed_producers_routine():
    selection = _value("selection", JSONB())
    operation = _value("operation")
    selected = _elements(selection["operations"], "selected")
    dependencies = _texts(selected.c.value["dependencies"], "dependency").lateral("dependency")
    discovery = _elements(selection["discovery"], "relation")
    dependency_rows = selected.join(dependencies, literal(True))
    direct = (
        select(dependencies.c.value.label("id"))
        .select_from(dependency_rows)
        .where(selected.c.value["operation"].astext == operation)
    )
    incoming = select(discovery.c.value["producer"].astext.label("id")).where(
        discovery.c.value["target"].astext == operation
    )
    seed = direct.union(incoming).subquery("seed")
    allowed = select(seed.c.id).cte("allowed", recursive=True)
    edge = (
        select(dependencies.c.value.label("id"))
        .select_from(dependency_rows)
        .where(selected.c.value["operation"].astext == allowed.c.id)
        .union(
            select(discovery.c.value["target"].astext.label("id")).where(
                discovery.c.value["producer"].astext == allowed.c.id
            )
        )
        .lateral("edge")
    )
    allowed = allowed.union(select(edge.c.id).select_from(allowed.join(edge, literal(True))))
    return NativeRoutine(
        "ops",
        "ddo_consumed_producers",
        parameters=(
            Parameter("selection", pg_type("jsonb")),
            Parameter("operation", pg_type("text")),
        ),
        returns=pg_type_array(),
        body=select(
            func.coalesce(
                func.array_agg(aggregate_order_by(allowed.c.id, allowed.c.id)),
                array([], type_=Text()),
            )
        ),
        strict=True,
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
    )


def binding_exact_float_programs() -> tuple[ProgramDeclaration, ...]:
    return _binding_declarations((_binding_exact_float_routine(),))


def binding_exact_float_sql() -> str:
    """Render this provider's captured statements from typed declarations."""
    return _render_binding_programs(binding_exact_float_programs(), separator="")


def binding_branch_native_programs() -> tuple[ProgramDeclaration, ...]:
    return _binding_declarations(_binding_branch_native_routines())


def binding_branch_native_sql() -> str:
    """Render this provider's captured statements from typed declarations."""
    return _render_binding_programs(binding_branch_native_programs(), separator="\n")


def binding_population_native_programs() -> tuple[ProgramDeclaration, ...]:
    return _binding_declarations(_binding_population_native_routines())


def binding_population_native_sql() -> str:
    """Render this provider's captured statements from typed declarations."""
    return _render_binding_programs(binding_population_native_programs(), separator="\n")


def binding_consumed_producers_programs() -> tuple[ProgramDeclaration, ...]:
    return _binding_declarations((_binding_consumed_producers_routine(),))


def binding_consumed_producers_sql() -> str:
    """Render this provider's captured statements from typed declarations."""
    return _render_binding_programs(binding_consumed_producers_programs(), separator="")
