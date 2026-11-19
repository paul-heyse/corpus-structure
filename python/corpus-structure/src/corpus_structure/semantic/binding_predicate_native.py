"""Compile the frozen binding expression's closed relational predicates."""

from typing import get_args, get_type_hints

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, array

from .binding_recursive_native import (
    _binding_declarations,
    _check,
    _elements,
    _json,
    _render_binding_programs,
    _routine,
    _texts,
    _value,
    pg_type_array,
)
from .data_operation_model import BindingExpression
from .native_program import (
    Assign,
    Continue,
    ForQuery,
    If,
    Local,
    Return,
    SelectInto,
    Statement,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _binding_predicate_native_routine():
    (
        node,
        context,
        child,
        selected,
        row,
        other,
        a,
        b,
        c,
        operands,
        operand,
        population,
        assignment,
        altered,
    ) = (
        _value(name, JSONB())
        for name in (
            "node",
            "context",
            "child",
            "selected",
            "row_value",
            "other_row",
            "a",
            "b",
            "c",
            "operands",
            "operand",
            "population",
            "assignment",
            "altered",
        )
    )
    operator, role, choice = (_value(name) for name in ("operator", "role", "choice"))
    names, active = (_value(name, ARRAY(Text())) for name in ("names", "active"))
    matching, i, j = (_value(name, Integer()) for name in ("matching", "i", "j"))
    total = _value("total", BigInteger())
    children = _elements(func.coalesce(node["children"], _json("[]")), "child_node")
    node_roles = _texts(func.coalesce(node["roles"], _json("[]")), "node_role")
    roledefs = _elements(context["roledefs"], "role_definition")
    roledef = (
        select(roledefs.c.value).where(roledefs.c.value["name"].astext == role).scalar_subquery()
    )
    selected_rows = _elements(func.coalesce(context["roles"][role], _json("[]")), "selected_row")
    members = _texts(population["members"], "population_member")
    universe = _elements(context["universe"], "candidate")
    candidate = universe.c.value
    role_names = (
        func.unnest(names).table_valued(column("value", Text())).render_derived(name="role_name")
    )
    child_roles = (
        func.unnest(func.ops.ddo_binding_roles(child))
        .table_valued(column("value", Text()))
        .render_derived(name="child_role")
    )

    def predicate(node_, context_):
        return func.ops.ddo_binding_test(node_, context_, type_=Boolean())

    def population_product(member):
        return func.ops.ddo_binding_population_product(population, member, type_=Boolean())

    def candidate_eligible(member):
        return and_(
            roledef["accepted_kind_contracts"].bool_op("?")(member["kind_contract"].astext),
            func.ops.ddo_binding_subject(
                roledef,
                member,
                context["subject"].astext,
                context["original_source"].astext,
                type_=Boolean(),
            ),
            func.ops.ddo_binding_source(
                roledef,
                member,
                context["original_source"].astext,
                context["source_sets"],
                type_=Boolean(),
            ),
            population_product(member),
        )

    descendants = select(children.c.value.label("n")).cte("descendants", recursive=True)
    descendant_children = _elements(
        func.coalesce(descendants.c.n["children"], _json("[]")), "descendant_child"
    ).lateral("descendant_child")
    descendants = descendants.union_all(
        select(descendant_children.c.value).select_from(
            descendants.join(descendant_children, literal(True))
        )
    )
    row_operators = (
        "all",
        "scan",
        "equal",
        "join",
        "literal",
        "range",
        "membership",
        "same",
        "distinct",
        "optional",
    )
    missing_candidates = (
        select(members.c.value)
        .where(
            ~select(candidate)
            .where(
                candidate["member"].astext == members.c.value,
                candidate_eligible(candidate),
            )
            .correlate(members)
            .exists()
        )
        .exists()
    )
    role_count = func.cardinality(names)

    def compare(left, right, kind):
        return func.ops.ddo_binding_compare(left, right, kind, type_=Boolean())

    steps: list[Statement] = [
        _check(
            or_(
                operator.is_(None),
                ~operator.in_(get_args(get_type_hints(BindingExpression)["operator"])),
            ),
            func.format("unsupported native binding operator %s", operator),
            "23514",
        ),
        If(
            operator == "choice",
            (
                _check(
                    node["selected"].astext.is_not(None)
                    & node["choice_parameter"].astext.is_not(None),
                    "ambiguous native branch selector",
                ),
                Assign(
                    "choice",
                    func.coalesce(
                        node["selected"].astext,
                        context["choices"][node["choice_parameter"].astext].astext,
                    ),
                ),
                _check(choice.is_(None), "missing frozen native branch selector"),
                ForQuery(
                    ("child",),
                    select(children.c.value),
                    (
                        If(
                            choice == any_(func.ops.ddo_binding_roles(child)),
                            (Assign("selected", child), Assign("matching", matching + 1)),
                        ),
                    ),
                ),
                _check(matching != 1, "native choice does not select exactly one declared branch"),
                Assign("active", func.ops.ddo_binding_roles(selected)),
                ForQuery(
                    ("child",),
                    select(children.c.value),
                    (
                        If(child == selected, (Continue(),)),
                        ForQuery(
                            ("role",),
                            select(child_roles.c.value),
                            (
                                If(
                                    ~(role == any_(active))
                                    & (
                                        func.jsonb_array_length(
                                            func.coalesce(context["roles"][role], _json("[]"))
                                        )
                                        != 0
                                    ),
                                    (Return(literal(False)),),
                                ),
                            ),
                        ),
                    ),
                ),
                Return(predicate(selected, context)),
            ),
        ),
        If(
            (operator == "optional") & func.ops.ddo_binding_missing(node, context, type_=Boolean()),
            (Return(literal(True)),),
        ),
        If(
            operator == "absent",
            (
                _check(
                    select(descendants.c.n)
                    .where(
                        or_(
                            descendants.c.n["operator"].astext.is_(None),
                            ~descendants.c.n["operator"].astext.in_(row_operators),
                        )
                    )
                    .exists(),
                    "absence children must be row predicates, not nested aggregate or branch scopes",
                ),
                SelectInto(
                    select(
                        func.coalesce(func.array_agg(node_roles.c.value), array([], type_=Text()))
                    ),
                    ("names",),
                ),
                _check(role_count != 1, "native absence requires one qualified role"),
                Assign("role", names[1]),
                Assign("population", context["populations"][node["population"].astext]),
                _check(
                    or_(
                        population.is_(None), population["complete"].astext.is_distinct_from("true")
                    ),
                    "native absence requires closed population",
                ),
                _check(
                    context["witnesses"][role].is_distinct_from(population),
                    "native absence witness differs from named population",
                ),
                If(
                    func.jsonb_array_length(func.coalesce(context["roles"][role], _json("[]")))
                    != 0,
                    (Return(literal(False)),),
                ),
                _check(missing_candidates, "negative population lacks admitted candidate facts"),
                ForQuery(
                    ("row_value",),
                    select(candidate).where(
                        candidate_eligible(candidate),
                        population["members"].bool_op("?")(candidate["member"].astext),
                    ),
                    (
                        Assign(
                            "altered",
                            func.jsonb_set(
                                context, array(["roles", role]), func.jsonb_build_array(row)
                            ),
                        ),
                        Assign("matching", literal(1)),
                        ForQuery(
                            ("child",),
                            select(children.c.value),
                            (If(~predicate(child, altered), (Assign("matching", literal(0)),)),),
                        ),
                        If(matching == 1, (Return(literal(False)),)),
                    ),
                ),
                Return(literal(True)),
            ),
        ),
        ForQuery(
            ("child",),
            select(children.c.value),
            (If(~predicate(child, context), (Return(literal(False)),)),),
        ),
        SelectInto(
            select(func.coalesce(func.array_agg(node_roles.c.value), array([], type_=Text()))),
            ("names",),
        ),
        If(
            operator.in_(("cardinality", "collection", "forall")) & (role_count == 0),
            (
                SelectInto(
                    select(
                        func.coalesce(
                            func.array_agg(roledefs.c.value["name"].astext), array([], type_=Text())
                        )
                    ),
                    ("names",),
                ),
            ),
        ),
        If(operator.in_(("scan", "all", "optional")), (Return(literal(True)),)),
        If(
            operator.in_(("cardinality", "collection", "forall")),
            (
                ForQuery(
                    ("role",),
                    select(role_names.c.value),
                    (
                        SelectInto(
                            select(
                                func.coalesce(
                                    func.sum(
                                        cast(
                                            selected_rows.c.value["multiplicity"].astext,
                                            BigInteger(),
                                        )
                                    ),
                                    0,
                                )
                            ),
                            ("total",),
                        ),
                        If(
                            operator == "cardinality",
                            (
                                If(
                                    node["minimum"].astext.is_not(None)
                                    & (total < cast(node["minimum"].astext, BigInteger())),
                                    (Return(literal(False)),),
                                ),
                                If(
                                    node["maximum"].astext.is_not(None)
                                    & (total > cast(node["maximum"].astext, BigInteger())),
                                    (Return(literal(False)),),
                                ),
                            ),
                        ),
                        If(
                            operator == "collection",
                            (
                                SelectInto(
                                    select(roledefs.c.value).where(
                                        roledefs.c.value["name"].astext == role
                                    ),
                                    ("selected",),
                                    True,
                                ),
                                _check(
                                    node["collection"].astext.is_distinct_from(
                                        selected["collection"].astext
                                    ),
                                    "native collection differs from role",
                                ),
                            ),
                        ),
                        If(
                            operator == "forall",
                            (
                                Assign(
                                    "population", context["populations"][node["population"].astext]
                                ),
                                _check(
                                    or_(
                                        population.is_(None),
                                        population["complete"].astext.is_distinct_from("true"),
                                    ),
                                    "native universal binding requires closed population",
                                ),
                                _check(
                                    context["witnesses"][role].is_distinct_from(population),
                                    "native universal witness differs from named population",
                                ),
                                If(
                                    or_(
                                        select(selected_rows.c.value)
                                        .where(
                                            or_(
                                                ~population["members"].bool_op("?")(
                                                    selected_rows.c.value["member"].astext
                                                ),
                                                ~population_product(selected_rows.c.value),
                                            )
                                        )
                                        .exists(),
                                        select(members.c.value)
                                        .where(
                                            ~select(selected_rows.c.value)
                                            .where(
                                                selected_rows.c.value["member"].astext
                                                == members.c.value,
                                                population_product(selected_rows.c.value),
                                            )
                                            .correlate(members)
                                            .exists()
                                        )
                                        .exists(),
                                    ),
                                    (Return(literal(False)),),
                                ),
                            ),
                        ),
                    ),
                ),
                Return(literal(True)),
            ),
        ),
    ]
    left_positions = (
        func.generate_series(1, role_count)
        .table_valued(column("position", Integer()))
        .render_derived(name="left_position")
    )
    right_positions = (
        func.generate_series(i + 1, role_count)
        .table_valued(column("position", Integer()))
        .render_derived(name="right_position")
    )
    left_rows = _elements(context["roles"][names[i]], "left_row")
    right_rows = _elements(context["roles"][names[j]], "right_row")
    left_identity = func.jsonb_build_array(row["product"], row["member"])
    right_identity = func.jsonb_build_array(other["product"], other["member"])
    steps.append(
        If(
            operator.in_(("same", "distinct")),
            (
                _check(role_count < 2, "native identity predicate requires two roles"),
                ForQuery(
                    ("i",),
                    select(left_positions.c.position),
                    (
                        ForQuery(
                            ("j",),
                            select(right_positions.c.position),
                            (
                                ForQuery(
                                    ("row_value",),
                                    select(left_rows.c.value),
                                    (
                                        ForQuery(
                                            ("other_row",),
                                            select(right_rows.c.value),
                                            (
                                                If(
                                                    or_(
                                                        (operator == "same")
                                                        & (left_identity != right_identity),
                                                        (operator == "distinct")
                                                        & (left_identity == right_identity),
                                                    ),
                                                    (Return(literal(False)),),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                Return(literal(True)),
            ),
        )
    )
    fields = _elements(func.coalesce(node["fields"], _json("[]")), "node_field")
    operand_rows = _elements(operands, "operand_row")
    actual = _elements(a, "actual_value")
    values_b = _elements(b, "expected_value")
    assignments = (
        func.ops.ddo_binding_assignments(node, context)
        .table_valued(column("value", JSONB()))
        .render_derived(name="assignment_row")
    )
    operand_positions = (
        func.generate_series(1, func.jsonb_array_length(operands) - 1)
        .table_valued(column("position", Integer()))
        .render_derived(name="operand_position")
    )
    steps.extend(
        (
            Assign("operands", func.coalesce(node["operands"], _json("[]"))),
            If(
                func.jsonb_array_length(operands) == 0,
                (
                    ForQuery(
                        ("operand",),
                        select(fields.c.value),
                        (
                            Assign(
                                "operands",
                                operands.op("||")(
                                    func.jsonb_build_array(
                                        func.jsonb_build_object("kind", "field", "field", operand)
                                    )
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            If(
                operator == "covers",
                (
                    _check(
                        or_(
                            func.jsonb_array_length(operands) != 2,
                            operands[0]["kind"].astext != "field",
                            ~operands[1]["kind"].astext.in_(("parameter", "literal", "population")),
                        ),
                        "invalid native coverage operands",
                    ),
                    Assign("a", func.ops.ddo_binding_values(operands[0], context)),
                    Assign("b", func.ops.ddo_binding_values(operands[1], context)),
                    ForQuery(
                        ("operand",),
                        select(values_b.c.value),
                        (
                            If(
                                ~select(actual.c.value)
                                .where(compare(actual.c.value, operand, "equal"))
                                .exists(),
                                (Return(literal(False)),),
                            ),
                        ),
                    ),
                    Return(literal(True)),
                ),
            ),
            If(
                operator == "literal",
                (
                    _check(
                        or_(
                            func.jsonb_array_length(operands) != 1, node["value"]["json"].is_(None)
                        ),
                        "invalid native literal predicate",
                    ),
                    Assign(
                        "operands",
                        operands.op("||")(
                            func.jsonb_build_array(
                                func.jsonb_build_object(
                                    "kind",
                                    "literal",
                                    "value_type",
                                    node["value"]["json"][0].astext,
                                    "value",
                                    node["value"],
                                )
                            )
                        ),
                    ),
                ),
            ),
            ForQuery(
                ("operand",),
                select(operand_rows.c.value).where(
                    operand_rows.c.value["kind"].astext == "population"
                ),
                (
                    _check(
                        ~operator.in_(("membership", "covers")),
                        "native population operands are membership/coverage universes",
                    ),
                    Assign("population", context["populations"][operand["name"].astext]),
                    Assign(
                        "names",
                        func.ops.ddo_binding_roles(
                            func.jsonb_set(node, array(["children"]), _json("[]"))
                        ),
                    ),
                    _check(
                        role_count == 0,
                        "population operand requires an identity-bearing input role",
                    ),
                    ForQuery(
                        ("role",),
                        select(role_names.c.value),
                        (
                            _check(
                                context["witnesses"][role].is_distinct_from(population),
                                "native membership witness differs from named population",
                            ),
                            If(
                                select(selected_rows.c.value)
                                .where(~population_product(selected_rows.c.value))
                                .exists(),
                                (Return(literal(False)),),
                            ),
                        ),
                    ),
                ),
            ),
            ForQuery(
                ("assignment",),
                select(assignments.c.value),
                (
                    Assign("a", func.ops.ddo_binding_values(operands[0], assignment)),
                    _check(
                        func.jsonb_array_length(a) != 1,
                        "native scalar predicate requires one operand value",
                    ),
                    If(
                        operator.in_(("equal", "join", "literal")),
                        (
                            _check(
                                func.jsonb_array_length(operands) < 2,
                                "invalid native equality predicate",
                            ),
                            ForQuery(
                                ("i",),
                                select(operand_positions.c.position),
                                (
                                    Assign(
                                        "b", func.ops.ddo_binding_values(operands[i], assignment)
                                    ),
                                    _check(
                                        func.jsonb_array_length(b) != 1,
                                        "native equality requires scalar operands",
                                    ),
                                    If(~compare(a[0], b[0], "equal"), (Return(literal(False)),)),
                                ),
                            ),
                        ),
                        (
                            If(
                                operator == "range",
                                (
                                    _check(
                                        func.jsonb_array_length(operands) != 3,
                                        "invalid native range",
                                    ),
                                    Assign(
                                        "b", func.ops.ddo_binding_values(operands[1], assignment)
                                    ),
                                    Assign(
                                        "c", func.ops.ddo_binding_values(operands[2], assignment)
                                    ),
                                    _check(
                                        or_(
                                            func.jsonb_array_length(b) != 1,
                                            func.jsonb_array_length(c) != 1,
                                        ),
                                        "native range requires scalar bounds",
                                    ),
                                    If(
                                        ~compare(a[0], b[0], "lower")
                                        | ~compare(a[0], c[0], "upper"),
                                        (Return(literal(False)),),
                                    ),
                                ),
                                (
                                    If(
                                        operator == "membership",
                                        (
                                            _check(
                                                or_(
                                                    func.jsonb_array_length(operands) != 2,
                                                    operands[1]["kind"].astext == "field",
                                                ),
                                                "invalid native membership universe",
                                            ),
                                            Assign(
                                                "b",
                                                func.ops.ddo_binding_values(
                                                    operands[1], assignment
                                                ),
                                            ),
                                            Assign("matching", literal(0)),
                                            ForQuery(
                                                ("c",),
                                                select(values_b.c.value),
                                                (
                                                    If(
                                                        compare(a[0], c, "equal"),
                                                        (Assign("matching", literal(1)),),
                                                    ),
                                                ),
                                            ),
                                            If(matching == 0, (Return(literal(False)),)),
                                        ),
                                        (
                                            _check(
                                                literal(True),
                                                "unsupported native predicate",
                                                "23514",
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            Return(literal(True)),
        )
    )
    return _routine(
        "ddo_binding_test",
        tuple(steps),
        (
            Local("operator", pg_type("text"), node["operator"].astext),
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "child",
                    "selected",
                    "row_value",
                    "other_row",
                    "a",
                    "b",
                    "c",
                    "operands",
                    "operand",
                    "population",
                    "assignment",
                    "altered",
                )
            ),
            *(Local(name, pg_type("text")) for name in ("role", "choice")),
            Local("names", pg_type_array()),
            Local("active", pg_type_array()),
            Local("matching", pg_type("integer"), literal(0)),
            Local("i", pg_type("integer")),
            Local("j", pg_type("integer")),
            Local("total", pg_type("bigint")),
        ),
        result="bool",
    )


def binding_predicate_native_programs() -> tuple[ProgramDeclaration, ...]:
    return _binding_declarations((_binding_predicate_native_routine(),))


def binding_predicate_native_sql() -> str:
    """Render this provider's captured statements from typed declarations."""
    return _render_binding_programs(binding_predicate_native_programs(), separator="")
