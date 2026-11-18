"""Exact tagged structural statement lowering and protected native admission guards."""

from pglast.stream import RawStream
from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    Text,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array, distinct_on

from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchStrictLookup,
    ForQuery,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    SelectInto,
    Statement,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
)
from .native_program import (
    literal as native_literal,
)


def _json(value):
    return cast(literal(value), JSONB())


def _field(value, name):
    return func.data.ddo_field(value, name, type_=JSONB())


def _structural(name, *arguments):
    return getattr(func.ops, "ddo_structural_" + name)(*arguments, type_=JSONB())


def _pick(value, names=(), *, exclude=True):
    return _structural("pick", value, array(names, type_=Text()), literal(exclude))


def _pairs(*pairs):
    return func.jsonb_build_array(
        *(func.jsonb_build_array(key, value, type_=JSONB()) for key, value in pairs), type_=JSONB()
    )


def _map(*pairs):
    return _structural("map", _pairs(*pairs))


def _items(value, name, *, ordinal=False):
    return (
        func.jsonb_array_elements(value)
        .table_valued(
            column("value", JSONB()), **({"with_ordinality": "ordinal"} if ordinal else {})
        )
        .render_derived(name=name)
    )


def _sequence(value, *ordering):
    aggregate = func.jsonb_agg(aggregate_order_by(value, *ordering) if ordering else value)
    return func.jsonb_build_array("sequence", func.coalesce(aggregate, _json("[]")), type_=JSONB())


def _present(value):
    return func.coalesce(value, _json('["null"]')) != _json('["null"]')


def structural_statement_native_sql():
    """Compile tagged subtrees directly, preserving nulls and numeric meaning."""
    programs: list[str] = []

    def add(name, parameters, *, query=None, steps=(), locals_=(), strict=True):
        parameters = tuple(
            Parameter(label, pg_type(type_), *default) for label, type_, *default in parameters
        )
        if query is None:
            declaration = function(
                "ops",
                "ddo_structural_" + name,
                parameters=parameters,
                returns=pg_type("jsonb"),
                body=Block(
                    tuple(steps),
                    tuple(
                        Local(label, pg_type(type_), *initial) for label, type_, *initial in locals_
                    ),
                ),
                volatility="immutable",
                strict=strict,
                search_path=("pg_catalog", "pg_temp"),
            )
        else:
            declaration = sql_function(
                "ops",
                "ddo_structural_" + name,
                parameters=parameters,
                returns=pg_type("jsonb"),
                body=query,
                volatility="immutable",
                strict=strict,
                search_path=("pg_catalog", "pg_temp"),
            )
        programs.append(declaration)
        programs.append(
            native_privilege_sql(
                NativeIdentity(
                    "function",
                    "ops",
                    "ddo_structural_" + name,
                    tuple(RawStream()(item.type_) for item in parameters),
                ),
                "PUBLIC",
                grant=False,
            )
        )

    fields = core_variable("fields", JSONB())
    pairs = _items(fields, "pairs_")
    add(
        "map",
        (("fields", "jsonb"),),
        query=select(
            func.data.ddo_normalize(
                func.jsonb_build_array(
                    "mapping",
                    func.coalesce(func.jsonb_agg(pairs.c.value), _json("[]")),
                    type_=JSONB(),
                )
            )
        ).where(pairs.c.value[1].is_not(None)),
    )

    value = core_variable("value", JSONB())
    names_type = pg_type("text")
    from pglast import ast

    names_type.arrayBounds = (ast.Integer(ival=-1),)
    names = core_variable("names", array([], type_=Text()).type)
    exclude = core_variable("exclude_names", Boolean())
    pairs = _items(value[1], "pairs_")
    # The native declaration's text[] parameter remains the original call ABI.
    pick_parameters = (
        Parameter("value", pg_type("jsonb")),
        Parameter("names", names_type),
        Parameter("exclude_names", pg_type("bool"), native_literal(False)),
    )
    programs.append(
        sql_function(
            "ops",
            "ddo_structural_pick",
            parameters=pick_parameters,
            returns=pg_type("jsonb"),
            body=select(
                _structural("map", func.coalesce(func.jsonb_agg(pairs.c.value), _json("[]")))
            ).where(
                (pairs.c.value[0].astext == names.any_()) != exclude,
                pairs.c.value[1] != _json('["null"]'),
            ),
            volatility="immutable",
            strict=True,
            search_path=("pg_catalog", "pg_temp"),
        )
    )
    programs.append(
        native_privilege_sql(
            NativeIdentity(
                "function", "ops", "ddo_structural_pick", ("jsonb", "text[]", "boolean")
            ),
            "PUBLIC",
            grant=False,
        )
    )

    left = core_variable("left_value", JSONB())
    right = core_variable("right_value", JSONB())
    left_pairs, right_pairs = _items(left[1], "left_"), _items(right[1], "right_")
    merged = union_all(
        select(left_pairs.c.value.label("pair"), literal(0).label("priority")),
        select(right_pairs.c.value, literal(1)),
    ).subquery("fields_")
    chosen = (
        select(merged.c.pair)
        .ext(distinct_on(merged.c.pair[0].astext))
        .order_by(merged.c.pair[0].astext, merged.c.priority.desc())
        .subquery("chosen_")
    )
    add(
        "merge",
        (("left_value", "jsonb"), ("right_value", "jsonb")),
        query=select(_structural("map", func.coalesce(func.jsonb_agg(chosen.c.pair), _json("[]")))),
    )

    report = core_variable("report", JSONB())
    identifier = core_variable("identifier", Text())
    passage = core_variable("passage", JSONB())
    source_value = core_variable("source_value", JSONB())
    passages = _items(_field(_field(report, "inputs"), "passages")[1], "passages_")
    sources = _items(_field(_field(report, "inputs"), "sources")[1], "sources_")
    add(
        "citation",
        (("report", "jsonb"), ("identifier", "text")),
        steps=(
            SelectInto(
                select(passages.c.value).where(
                    _field(passages.c.value, "passage_id")[1].astext == identifier
                ),
                ("passage",),
                strict=True,
            ),
            SelectInto(
                select(sources.c.value).where(
                    func.ops.ddo_digest(func.data.ddo_json(_pick(sources.c.value)))
                    == _field(passage, "source_ref")[1].astext
                ),
                ("source_value",),
                strict=True,
            ),
            Return(
                _structural(
                    "merge",
                    _pick(passage, ("passage_id", "source_ref")),
                    _map(("source", _pick(source_value))),
                )
            ),
        ),
        locals_=(("passage", "jsonb"), ("source_value", "jsonb")),
    )

    span = core_variable("span_value", JSONB())
    add(
        "span",
        (("report", "jsonb"), ("span_value", "jsonb")),
        query=select(
            _structural(
                "merge",
                _structural("citation", report, _field(span, "passage_id")[1].astext),
                _pick(span, ("passage_id",)),
            )
        ),
    )
    identifiers = core_variable("identifiers", JSONB())
    selected = _items(identifiers[1], "identifiers_")
    citations = (
        select(_structural("citation", report, selected.c.value[1].astext).label("citation"))
        .distinct()
        .subquery("citations_")
    )
    add(
        "citations",
        (("report", "jsonb"), ("identifiers", "jsonb")),
        query=select(
            _sequence(
                citations.c.citation,
                func.data.canonical_json(func.data.ddo_json(citations.c.citation)).collate("C"),
            )
        ),
    )

    field_value = core_variable("field_value", JSONB())
    typed = core_variable("typed_value", JSONB())
    spans = core_variable("spans", JSONB())
    span_items = _items(_field(field_value, "spans")[1], "spans_", ordinal=True)
    field_steps: list[Statement] = [
        Assign(
            "fields",
            _pairs(
                ("dimension", _field(field_value, "dimension")),
                ("lexical_value", _field(field_value, "lexical_value")),
                ("evidence", _structural("citations", report, _field(field_value, "evidence"))),
            ),
        )
    ]
    field_steps.append(
        If(
            _present(_field(field_value, "span")),
            (
                Assign(
                    "fields",
                    fields.op("||")(
                        _pairs(("span", _structural("span", report, _field(field_value, "span"))))
                    ),
                ),
            ),
        )
    )
    field_steps.append(
        If(
            _present(_field(field_value, "spans")),
            (
                SelectInto(
                    select(
                        _sequence(
                            _structural("span", report, span_items.c.value), span_items.c.ordinal
                        )
                    ),
                    ("spans",),
                ),
                Assign("fields", fields.op("||")(_pairs(("spans", spans)))),
            ),
        )
    )
    field_steps.append(
        If(
            _present(_field(field_value, "literal")),
            (
                Assign(
                    "fields",
                    fields.op("||")(_pairs(("literal", _pick(_field(field_value, "literal"))))),
                ),
            ),
        )
    )
    # Free condition subtrees retain every tag and null without projection.
    field_steps.append(
        If(
            _present(_field(field_value, "condition")),
            (
                Assign(
                    "fields",
                    fields.op("||")(_pairs(("condition", _field(field_value, "condition")))),
                ),
            ),
        )
    )
    field_steps.extend(
        (
            Assign("typed_value", _field(field_value, "typed")),
            If(
                _present(typed),
                (
                    Assign(
                        "typed_value",
                        _structural(
                            "merge",
                            _pick(typed, ("span", "basis_evidence")),
                            _map(("span", _structural("span", report, _field(typed, "span")))),
                        ),
                    ),
                    If(
                        _present(_field(_field(field_value, "typed"), "basis_evidence")),
                        (
                            Assign(
                                "typed_value",
                                _structural(
                                    "merge",
                                    typed,
                                    _map(
                                        (
                                            "basis_evidence",
                                            _structural(
                                                "span",
                                                report,
                                                _field(
                                                    _field(field_value, "typed"), "basis_evidence"
                                                ),
                                            ),
                                        )
                                    ),
                                ),
                            ),
                        ),
                    ),
                    Assign("fields", fields.op("||")(_pairs(("typed", typed)))),
                ),
            ),
            Return(_structural("map", fields)),
        )
    )
    add(
        "clause_field",
        (("report", "jsonb"), ("field_value", "jsonb")),
        steps=field_steps,
        locals_=(("fields", "jsonb"), ("typed_value", "jsonb"), ("spans", "jsonb")),
    )

    inputs = core_variable("inputs", JSONB())
    comparison = core_variable("comparison", JSONB())
    dimensions = core_variable("dimensions", JSONB())
    dimension = core_variable("dimension", JSONB())
    entry = core_variable("entry", JSONB())
    group = core_variable("group_value", JSONB())
    members = core_variable("members", JSONB())
    witnesses = core_variable("witnesses", JSONB())
    coverage = core_variable("coverage", JSONB())
    exclusions = core_variable("exclusions", JSONB())
    succession = core_variable("succession", JSONB())

    def coverage_query():
        selected = _items(_field(inputs, "coverage_limits")[1], "coverage_")
        return select(_sequence(selected.c.value, selected.c.value[1].astext.collate("C")))

    def exclusions_query():
        selected = _items(_field(inputs, "exclusions")[1], "exclusions_")
        projection = select(
            _map(
                (
                    "left",
                    _structural("citation", report, _field(selected.c.value, "left")[1].astext),
                ),
                (
                    "right",
                    _structural("citation", report, _field(selected.c.value, "right")[1].astext),
                ),
            ).label("item")
        ).subquery("selected_")
        return select(
            _sequence(
                projection.c.item,
                func.data.canonical_json(func.data.ddo_json(projection.c.item)).collate("C"),
            )
        )

    dimension_items = _items(_field(comparison, "dimensions")[1], "dimensions_")
    dimension_steps: list[Statement] = [
        Assign(
            "entry",
            _pick(
                dimension,
                (
                    "dimension",
                    "outcome",
                    "typed_outcome",
                    "assumptions",
                    "grouping_outcome",
                    "member_comparisons",
                ),
                exclude=False,
            ),
        )
    ]
    for name in ("removed_interval", "added_interval"):
        dimension_steps.extend(
            (
                Assign("value", _field(dimension, name)),
                If(
                    _present(value),
                    (Assign("entry", _structural("merge", entry, _map((name, _pick(value))))),),
                ),
            )
        )
    group_members = _items(_field(group, "members")[1], "members_", ordinal=True)
    group_witnesses = _items(_field(group, "witnesses")[1], "witnesses_", ordinal=True)
    for name in ("left", "right"):
        dimension_steps.extend(
            (
                Assign("value", _field(dimension, name)),
                If(
                    _present(value),
                    (
                        Assign(
                            "entry",
                            _structural(
                                "merge",
                                entry,
                                _map((name, _structural("clause_field", report, value))),
                            ),
                        ),
                    ),
                ),
                Assign("group_value", _field(dimension, name + "_group")),
                If(
                    _present(group),
                    (
                        SelectInto(
                            select(
                                _sequence(
                                    _structural("clause_field", report, group_members.c.value),
                                    group_members.c.ordinal,
                                )
                            ),
                            ("members",),
                        ),
                        SelectInto(
                            select(
                                _sequence(
                                    _structural("span", report, group_witnesses.c.value),
                                    group_witnesses.c.ordinal,
                                )
                            ),
                            ("witnesses",),
                        ),
                        Assign(
                            "value",
                            _structural(
                                "merge",
                                _pick(group, ("state", "grouping"), exclude=False),
                                _map(("members", members), ("witnesses", witnesses)),
                            ),
                        ),
                        Assign(
                            "entry", _structural("merge", entry, _map((name + "_group", value)))
                        ),
                    ),
                ),
            )
        )
    dimension_steps.append(Assign("dimensions", dimensions.op("||")(func.jsonb_build_array(entry))))
    add(
        "comparison_statement",
        (("report", "jsonb"),),
        steps=(
            If(
                _field(report, "kind")[1].astext.is_distinct_from("qualified_comparison"),
                (
                    Raise(
                        "structural admission requires the exact qualified comparison variant",
                        "23514",
                    ),
                ),
            ),
            SelectInto(coverage_query(), ("coverage",)),
            SelectInto(exclusions_query(), ("exclusions",)),
            ForQuery(("dimension",), select(dimension_items.c.value), tuple(dimension_steps)),
            Assign(
                "fields",
                _pairs(
                    (
                        "left",
                        _structural("citation", report, _field(comparison, "left_id")[1].astext),
                    ),
                    (
                        "right",
                        _structural("citation", report, _field(comparison, "right_id")[1].astext),
                    ),
                    ("dimensions", func.jsonb_build_array("sequence", dimensions)),
                ),
            ),
            Assign(
                "value",
                _structural(
                    "merge",
                    _pick(
                        comparison,
                        ("equivalence", "identity_standing", "applicability"),
                        exclude=False,
                    ),
                    _structural("map", fields),
                ),
            ),
            Assign("succession", _field(comparison, "succession")),
            If(
                _present(succession),
                (
                    Assign(
                        "value",
                        _structural(
                            "merge",
                            value,
                            _map(
                                (
                                    "succession",
                                    _map(
                                        (
                                            "older",
                                            _structural(
                                                "citation",
                                                report,
                                                _field(succession, "older_id")[1].astext,
                                            ),
                                        ),
                                        (
                                            "newer",
                                            _structural(
                                                "citation",
                                                report,
                                                _field(succession, "newer_id")[1].astext,
                                            ),
                                        ),
                                        (
                                            "evidence",
                                            _structural(
                                                "span", report, _field(succession, "evidence")
                                            ),
                                        ),
                                        (
                                            "older_evidence",
                                            _structural(
                                                "span", report, _field(succession, "older_evidence")
                                            ),
                                        ),
                                    ),
                                )
                            ),
                        ),
                    ),
                ),
            ),
            Return(
                _structural(
                    "merge",
                    _pick(inputs, ("scope", "inventory_id"), exclude=False),
                    _map(
                        (
                            "version",
                            func.jsonb_build_array("string", "structural-public-statement-3"),
                        ),
                        ("kind", func.jsonb_build_array("string", "qualified_comparison")),
                        ("input_policy_id", _field(inputs, "policy_id")),
                        ("coverage_limits", coverage),
                        ("exclusions", exclusions),
                        ("comparison", value),
                    ),
                )
            ),
        ),
        locals_=(
            ("inputs", "jsonb", _field(report, "inputs")),
            ("comparison", "jsonb", _field(report, "comparison")),
            ("fields", "jsonb"),
            ("dimensions", "jsonb", _json("[]")),
            ("dimension", "jsonb"),
            ("entry", "jsonb"),
            ("value", "jsonb"),
            ("group_value", "jsonb"),
            ("members", "jsonb"),
            ("witnesses", "jsonb"),
            ("coverage", "jsonb"),
            ("exclusions", "jsonb"),
            ("succession", "jsonb"),
        ),
    )

    variant = core_variable("variant", Text())
    component_id = core_variable("component_id", Text())
    statement = core_variable("statement", JSONB())
    component = core_variable("component", JSONB())
    citations_value = core_variable("citations", JSONB())
    component_items = _items(
        _field(_field(report, "definition_components"), "components")[1], "components_"
    )
    condition_steps: list[Statement] = []
    for role in ("qualifier", "host_predicate"):
        role_items = _items(_field(component, role)[1], role + "_", ordinal=True)
        condition_steps.extend(
            (
                SelectInto(
                    select(
                        _sequence(
                            _map(
                                ("source_pointer", _field(role_items.c.value, "source_pointer")),
                                (
                                    "passage",
                                    _structural("span", report, _field(role_items.c.value, "span")),
                                ),
                            ),
                            role_items.c.ordinal,
                        )
                    ),
                    ("citations",),
                ),
                Assign("fields", fields.op("||")(_pairs((role, citations_value)))),
            )
        )
    add(
        "statement",
        (("report", "jsonb"), ("component_id", "text")),
        strict=False,
        steps=(
            If(
                variant == "qualified_comparison",
                (
                    If(
                        component_id.is_not(None),
                        (
                            Raise(
                                "comparison statement cannot select a definition component", "23514"
                            ),
                        ),
                    ),
                    Return(_structural("comparison_statement", report)),
                ),
            ),
            If(
                variant.not_in(("condition_qualification", "definition_components")),
                (
                    Raise(
                        "structural admission requires its exact released report variant", "23514"
                    ),
                ),
            ),
            If(
                (variant == "definition_components").is_distinct_from(component_id.is_not(None)),
                (
                    Raise(
                        "only definition publication requires one exact component selector", "23514"
                    ),
                ),
            ),
            SelectInto(coverage_query(), ("coverage",)),
            SelectInto(exclusions_query(), ("exclusions",)),
            Assign(
                "statement",
                _map(
                    ("version", func.jsonb_build_array("string", "structural-public-statement-3")),
                    ("kind", func.jsonb_build_array("string", variant)),
                    ("scope", _field(inputs, "scope")),
                    ("coverage_limits", coverage),
                    ("exclusions", exclusions),
                ),
            ),
            If(
                variant == "definition_components",
                (
                    SelectInto(
                        select(component_items.c.value).where(
                            _field(component_items.c.value, "component_id")[1].astext
                            == component_id
                        ),
                        ("component",),
                        strict=True,
                    ),
                    Assign(
                        "fields",
                        _pairs(
                            ("term", _structural("span", report, _field(component, "term"))),
                            ("content", _structural("span", report, _field(component, "content"))),
                            ("interpretation", _field(component, "interpretation")),
                            ("scope", _field(component, "scope")),
                        ),
                    ),
                    Assign("value", _field(component, "effective_version")),
                    If(
                        _present(value),
                        (Assign("fields", fields.op("||")(_pairs(("effective_version", value)))),),
                    ),
                    Return(
                        _structural(
                            "merge",
                            statement,
                            _map(("definition_component", _structural("map", fields))),
                        )
                    ),
                ),
            ),
            Assign("component", _field(report, "condition_qualification")),
            Assign("fields", _pairs(("relation", _field(component, "relation")))),
            Assign("value", _field(component, "effective_version")),
            If(
                func.coalesce(value[1].astext, "") != "",
                (Assign("fields", fields.op("||")(_pairs(("effective_version", value)))),),
            ),
            *condition_steps,
            Return(
                _structural(
                    "merge",
                    statement,
                    _map(("condition_qualification", _structural("map", fields))),
                )
            ),
        ),
        locals_=(
            ("inputs", "jsonb", _field(report, "inputs")),
            ("variant", "text", _field(report, "kind")[1].astext),
            ("coverage", "jsonb"),
            ("exclusions", "jsonb"),
            ("statement", "jsonb"),
            ("value", "jsonb"),
            ("component", "jsonb"),
            ("fields", "jsonb"),
            ("citations", "jsonb"),
        ),
    )
    return native_sql_script(programs) + "\n"


def _structural_command_helpers(model):
    import json
    from dataclasses import asdict

    from .declared_structural_admission import (
        ADMISSION_EFFECT,
        ADMISSION_FACTORY,
        ADMISSION_OPERATION,
    )

    definitions = model.tables["sem.data_operation_definition"]
    products = model.tables["kb.data_product"]

    def definition(field):
        return core_variable("definition", definitions.c[field].type, field)

    def product(field):
        return core_variable("product", products.c[field].type, field)

    support = definition("support_contract")
    factory = support["capabilities"]["prepared_factory"]
    return (
        native_sql_script(
            (
                sql_function(
                    "ops",
                    "ddo_structural_command_eligible",
                    parameters=(
                        Parameter("definition", pg_type(str(definitions.schema), definitions.name)),
                    ),
                    returns=pg_type("bool"),
                    volatility="immutable",
                    strict=True,
                    search_path=("pg_catalog", "pg_temp"),
                    body=select(
                        (definition("operation_id") == ADMISSION_OPERATION)
                        & (definition("profile") == "command")
                        & (support["capabilities"]["preparation"].astext == "native-publication")
                        & (support["capabilities"]["forms"] == _json('["scalar"]'))
                        & (factory["entrypoint"].astext == ADMISSION_FACTORY)
                        & (
                            support["effects"]
                            == _json(json.dumps([asdict(ADMISSION_EFFECT)], separators=(",", ":")))
                        )
                        & factory["source_digest"].astext.op("~")("^[0-9a-f]{64}$")
                        & definition("implementation_revision").like("implementation-slice:%")
                    ),
                ),
                sql_function(
                    "ops",
                    "ddo_structural_product_reference",
                    parameters=(
                        Parameter("product", pg_type(str(products.schema), products.name)),
                    ),
                    returns=pg_type("jsonb"),
                    volatility="immutable",
                    strict=True,
                    search_path=("pg_catalog", "pg_temp"),
                    body=select(
                        func.jsonb_build_object(
                            *(
                                part
                                for pair in (
                                    ("product_id", product("id")),
                                    ("member_id", None),
                                    *(
                                        (name, product(name))
                                        for name in (
                                            "kind_contract",
                                            "project_id",
                                            "subject",
                                            "subject_definition",
                                            "original_source",
                                        )
                                    ),
                                    (
                                        "analyzed_scope_meaning",
                                        func.data.canonical_json(
                                            func.data.ddo_json_meaning(product("analyzed_scope"))
                                        ),
                                    ),
                                )
                                for part in pair
                            ),
                            type_=JSONB(),
                        )
                    ),
                ),
            )
        )
        + "\n"
    )


def _completion_row(name, table, field=None):
    return core_variable(
        name, table.table_valued().type if field is None else table.c[field].type, field
    )


def _completion_lookup(name, table, *conditions, relation=None):
    return SelectInto(
        select(core_relation_row(table))
        .select_from(table if relation is None else relation)
        .where(*conditions),
        (name,),
        strict=True,
    )


def _completion_refusal(condition, message, sqlstate="23514"):
    return If(condition, (Raise(message, sqlstate),))


def _completion_program(name, requests, steps, locals_):
    parameters = (
        Parameter("r", pg_type(str(requests.schema), requests.name)),
        Parameter("completion", pg_type("jsonb")),
    )
    return (
        native_sql_script(
            (
                function(
                    "ops",
                    name,
                    parameters=parameters,
                    returns=pg_type("void"),
                    body=Block(
                        (
                            CatchStrictLookup(
                                tuple(steps),
                                (
                                    Raise(
                                        "dossier admission cannot resolve exact ordinary issuer/report custody"
                                        if name == "ddo_require_structural_dossier_completion"
                                        else "structural admission cannot resolve exact original custody",
                                        "23514",
                                    ),
                                ),
                            ),
                        ),
                        tuple(locals_),
                    ),
                    volatility="stable",
                    security_definer=True,
                    search_path=("pg_catalog", "pg_temp"),
                ),
                native_privilege_sql(
                    NativeIdentity(
                        "function", "ops", name, tuple(RawStream()(p.type_) for p in parameters)
                    ),
                    "PUBLIC",
                    grant=False,
                ),
            )
        )
        + "\n"
    )


def _structural_dossier_completion(model):
    from .declared_structural_admission import ADMISSION_KIND

    definitions, requests, products, kinds, episodes, outputs, receipts, intents = (
        model.tables[name]
        for name in (
            "sem.data_operation_definition",
            "ops.data_request",
            "kb.data_product",
            "sem.data_kind_contract",
            "ops.data_derivation",
            "ops.data_derivation_output",
            "ops.data_publication_receipt",
            "ops.data_completion_intent",
        )
    )

    def r(field=None):
        return _completion_row("r", requests, field)

    def d(field):
        return _completion_row("definition", definitions, field)

    def conclusion(field=None):
        return _completion_row("conclusion", products, field)

    def comparison(field=None):
        return _completion_row("comparison_product", products, field)

    completion = core_variable("completion", JSONB())
    selected = core_variable("selected", JSONB())
    admission = core_variable("admission_value", JSONB())
    count = core_variable("actual_count", BigInteger())
    support_contract = d("support_contract")
    factory = support_contract["capabilities"]["prepared_factory"]
    inputs = _items(completion["inputs"], "inputs_")
    supports = (
        func.ops.ddo_input_support_refs(r("binding"), selected)
        .table_valued(column("value", JSONB()))
        .render_derived(name="supports_")
    )
    issuer = definitions.alias("issuer")
    other = outputs.alias("other")
    issuer_join = (
        episodes.join(outputs, outputs.c.derivation_id == episodes.c.id)
        .join(
            receipts,
            (receipts.c.derivation_id == episodes.c.id)
            & (receipts.c.intent_id == episodes.c.intent_id),
        )
        .join(intents, intents.c.id == episodes.c.intent_id)
        .join(requests, requests.c.id == episodes.c.request_id)
        .join(
            issuer,
            (issuer.c.release_id == episodes.c.release_id)
            & (issuer.c.operation_id == requests.c.operation_id),
        )
    )
    issuer_count = (
        select(func.count())
        .select_from(issuer_join)
        .where(
            outputs.c.product_id == conclusion("id"),
            outputs.c.member_id.is_(None),
            outputs.c.role == "admission",
            outputs.c.position == 0,
            outputs.c.multiplicity == 1,
            episodes.c.outcome == "success",
            issuer.c.command_class == "structural",
            episodes.c.recipe == issuer.c.recipe,
            intents.c.payload["implementation_revision"].astext == issuer.c.implementation_revision,
            select(func.count())
            .select_from(other)
            .where(other.c.derivation_id == episodes.c.id)
            .correlate(episodes)
            .scalar_subquery()
            == 1,
            func.data.ddo_normalize(intents.c.payload["outputs"][0]["product"]["body"])
            == conclusion("canonical_body"),
            exists(
                select(1)
                .select_from(supports)
                .where(
                    supports.c.value["kind"].astext == "computation",
                    supports.c.value["derivation_id"].astext == episodes.c.id,
                )
            ),
        )
    )
    return _completion_program(
        "ddo_require_structural_dossier_completion",
        requests,
        (
            If(r("operation_id") != "structure.dossier/declared", (Return(),)),
            _completion_lookup(
                "definition",
                definitions,
                definitions.c.release_id == r("release_id"),
                definitions.c.operation_id == r("operation_id"),
            ),
            _completion_refusal(
                or_(
                    d("profile").is_distinct_from("derivation"),
                    support_contract["effects"].is_distinct_from(_json("[]")),
                    factory["entrypoint"].astext.is_distinct_from(
                        "corpus_structure.methods.dossier_declared.DossierOperation.acquire_port"
                    ),
                    factory["source_digest"].astext.op("~")("^[0-9a-f]{64}$").is_not(True),
                    d("implementation_revision").like("implementation-slice:%").is_not(True),
                ),
                "structural dossier requires its actual captured preparation factory",
            ),
            ForQuery(
                ("selected",),
                select(inputs.c.value).where(inputs.c.value["role"].astext == "admissions"),
                (
                    _completion_refusal(
                        or_(
                            selected["member_id"].astext.is_not(None),
                            cast(selected["multiplicity"].astext, Integer()).is_distinct_from(1),
                        ),
                        "dossier admission requires an exact whole conclusion",
                    ),
                    _completion_lookup(
                        "conclusion",
                        products,
                        products.c.id == selected["product_id"].astext,
                        products.c.project_id == r("project_id"),
                    ),
                    _completion_refusal(
                        ~exists(
                            select(1)
                            .select_from(kinds)
                            .where(
                                kinds.c.kind_contract == conclusion("kind_contract"),
                                kinds.c.kind == ADMISSION_KIND,
                                kinds.c.universe == "ordinary",
                            )
                        ),
                        "dossier admission differs from its actual ordinary structural kind",
                    ),
                    # Ordinary support authenticates visibility and full revocation closure.
                    # The dossier reads common issuer custody, never protected pass bodies.
                    SelectInto(issuer_count, ("actual_count",)),
                    _completion_refusal(
                        count != 1, "dossier admission lacks its exact actual native issuer receipt"
                    ),
                    Assign(
                        "admission_value",
                        func.data.ddo_json(conclusion("canonical_body"), type_=JSONB()),
                    ),
                    _completion_lookup(
                        "comparison_product",
                        products,
                        inputs.c.value["role"].astext == "comparisons",
                        inputs.c.value["member_id"].astext.is_(None),
                        products.c.id == admission["report"]["product_id"].astext,
                        products.c.project_id == r("project_id"),
                        relation=products.join(
                            inputs, inputs.c.value["product_id"].astext == products.c.id
                        ),
                    ),
                    _completion_refusal(
                        or_(
                            func.jsonb_strip_nulls(admission["report"]).is_distinct_from(
                                func.jsonb_strip_nulls(
                                    _structural("product_reference", comparison())
                                )
                            ),
                            admission["statement_encoding"].astext.is_distinct_from(
                                "ddo-semantic-value-v1"
                            ),
                            admission["statement_meaning_json"].astext.is_distinct_from(
                                func.data.canonical_json(
                                    _structural(
                                        "comparison_statement", comparison("canonical_body")
                                    )
                                )
                            ),
                        ),
                        "dossier admission differs from the actual retained comparison and exact statement",
                    ),
                ),
            ),
        ),
        (
            Local("definition", definitions),
            Local("selected", pg_type("jsonb")),
            Local("conclusion", products),
            Local("comparison_product", products),
            Local("admission_value", pg_type("jsonb")),
            Local("actual_count", pg_type("int8")),
        ),
    )


def structural_admission_native_sql(model):
    from .declared_structural_admission import (
        ADMISSION_KIND,
        ADMISSION_OPERATION,
        REFERENCE_KIND,
        STRUCTURAL_REPORT_PRODUCERS,
        DdoStructuralAdmission,
    )

    fields = {
        "version",
        "report",
        "component_id",
        "policy_id",
        "policy_version",
        "statement_encoding",
        "statement_meaning_json",
        "standing",
        "assessment_basis",
        "scientific_truth",
        "member_truth",
    }
    if fields != DdoStructuralAdmission.model_fields.keys():
        raise ValueError("native structural disclosure must cover its exact public contract")
    sql = r"""
CREATE OR REPLACE FUNCTION ops.ddo_require_structural_admission_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE definition sem.data_operation_definition; selected jsonb; output jsonb; report_product kb.data_product;
 pass_product kb.data_product; pass_kind sem.data_kind_contract; admitted ops.original_source_admission;
 pass_body jsonb; frame jsonb; passes jsonb:='{}'; actors jsonb:='[]'; parent_values jsonb:='[]'; c jsonb;
 report jsonb; statement jsonb; expected jsonb; selected_case jsonb; report_reference jsonb; producer_count bigint;
 report_kind text; variant text; report_role text; policy_id text; selected_component text;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF NOT coalesce((definition.command_class='structural'),false) THEN
 IF definition.operation_id='__OPERATION__' OR EXISTS(SELECT FROM jsonb_array_elements(definition.support_contract->'effects') effect
 WHERE effect->>'name'='native-evaluator-structural-admission') THEN
 RAISE EXCEPTION 'structural admission requires its exact command/effect/factory' USING ERRCODE='23514'; END IF;
 RETURN; END IF;
 IF NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_evaluator','MEMBER') THEN
 RAISE EXCEPTION 'structural admission requires native evaluator purpose' USING ERRCODE='42501'; END IF;
 IF completion->>'outcome' IS DISTINCT FROM 'success' OR jsonb_array_length(completion->'inputs')<>4
 OR jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'structural admission requires one report, three exact passes and one conclusion' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT selected FROM jsonb_array_elements(completion->'inputs') WHERE value->>'role' IN ('comparison','condition','definition');
 IF selected->>'member_id' IS NOT NULL OR (selected->>'position')::integer IS DISTINCT FROM 0
 OR (selected->>'multiplicity')::integer IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'structural report must be its exact whole scalar input' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT report_product FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 SELECT kind.kind INTO STRICT report_kind FROM sem.data_kind_contract kind WHERE kind.kind_contract=report_product.kind_contract AND kind.universe='ordinary';
 CASE report_kind
 WHEN 'urn:corpus:structural:DeclaredComparisonReport' THEN variant:='qualified_comparison'; report_role:='comparison'; policy_id:='independent-structural-comparison-1';
 WHEN 'urn:corpus:structural:DeclaredConditionReport' THEN variant:='condition_qualification'; report_role:='condition'; policy_id:='independent-condition-qualification-1';
 WHEN 'urn:corpus:structural:DeclaredDefinitionComponentsReport' THEN variant:='definition_components'; report_role:='definition'; policy_id:='independent-definition-component-1';
 ELSE RAISE EXCEPTION 'structural admission requires its actual released report kind' USING ERRCODE='23514'; END CASE;
 report:=data.ddo_json(report_product.canonical_body);
 IF report->>'kind' IS DISTINCT FROM variant OR selected->>'role' IS DISTINCT FROM report_role THEN
 RAISE EXCEPTION 'structural report differs from its exact choice-bound nominal variant' USING ERRCODE='23514'; END IF;
 SELECT count(*) INTO producer_count FROM ops.data_derivation episode
 JOIN ops.data_derivation_output produced ON produced.derivation_id=episode.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 JOIN ops.data_request request ON request.id=episode.request_id
 JOIN sem.data_operation_definition owner ON owner.release_id=episode.release_id AND owner.operation_id=request.operation_id
 JOIN ops.data_completion_intent intent ON intent.id=episode.intent_id
 WHERE produced.product_id=report_product.id AND produced.member_id IS NULL AND produced.role='result'
 AND produced.position=0 AND produced.multiplicity=1 AND episode.outcome='success'
 AND owner.profile='derivation'
 AND owner.support_contract->'effects'='[]'::jsonb
 AND (variant,owner.operation_id,owner.support_contract->'capabilities'->'prepared_factory'->>'entrypoint') IN (
 __REPORT_PRODUCERS__)
 AND owner.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND owner.implementation_revision LIKE 'implementation-slice:%' AND owner.recipe=episode.recipe
 AND intent.payload->>'implementation_revision'=owner.implementation_revision
 AND jsonb_array_length(coalesce(intent.payload->'execution_evidence'->'cpu_receipts','[]'))=1
 AND EXISTS(SELECT FROM ops.ddo_input_support_refs(r.binding,selected) support
 WHERE support->>'kind'='computation' AND support->>'derivation_id'=episode.id);
 IF producer_count<>1 THEN RAISE EXCEPTION 'structural report lacks its one actual captured producer for the selected variant' USING ERRCODE='23514'; END IF;
 report_reference:=ops.ddo_structural_product_reference(report_product);
 FOR selected IN SELECT value FROM jsonb_array_elements(completion->'inputs') WHERE value->>'role'='passes' LOOP
 IF selected->>'member_id' IS NOT NULL OR (selected->>'multiplicity')::integer IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'structural passes require distinct whole original authored products' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT pass_product FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 SELECT * INTO STRICT pass_kind FROM sem.data_kind_contract WHERE kind_contract=pass_product.kind_contract;
 IF pass_kind.kind IS DISTINCT FROM '__REFERENCE_KIND__' OR pass_kind.universe IS DISTINCT FROM 'evaluator' THEN
 RAISE EXCEPTION 'structural pass differs from its protected nominal kind' USING ERRCODE='23514'; END IF;
 SELECT admission.* INTO STRICT admitted FROM ops.original_source_admission admission
 JOIN ops.ddo_input_support_refs(r.binding,selected) support
 ON support->>'kind'='authored' AND support->>'admission_id'=admission.id AND support->>'source_reference'=admission.source_reference
 WHERE admission.product_id=pass_product.id AND admission.project_id=r.project_id
 AND admission.reference->>'kind'='authored-fact' AND ops.ddo_original_admission_valid(admission);
 pass_body:=data.ddo_json(pass_product.canonical_body);
 IF admitted.evidence->>'standing' IS DISTINCT FROM 'authored' OR nullif(admitted.evidence->>'submitted_by','') IS NULL
 OR admitted.reference->>'author' IS DISTINCT FROM pass_body->>'author_assertion'
 OR admitted.evidence->>'author_assertion' IS DISTINCT FROM pass_body->>'author_assertion'
 OR pass_body->'actor'->>'principal' IS DISTINCT FROM pass_body->>'author_assertion'
 OR pass_body->'actor'->>'basis' IS DISTINCT FROM 'authored_attribution'
 OR pass_body->>'version' IS DISTINCT FROM 'structural-reference-pass-1' OR pass_body->>'pass_kind' NOT IN ('A','B','C')
 OR passes ? (pass_body->>'pass_kind') THEN
 RAISE EXCEPTION 'structural pass lacks its exact original submitted author attribution' USING ERRCODE='23514'; END IF;
 IF frame IS NULL THEN frame:=pass_body->'frame'; END IF;
 IF frame IS DISTINCT FROM pass_body->'frame' OR jsonb_strip_nulls(frame->'report') IS DISTINCT FROM jsonb_strip_nulls(report_reference)
 OR jsonb_strip_nulls(frame->'inputs') IS DISTINCT FROM jsonb_strip_nulls(report->'inputs')
 OR frame->>'question' IS DISTINCT FROM report->'inputs'->>'question'
 OR jsonb_array_length(pass_body->'cases')<>1 OR pass_body->'cases'->0->>'case_id' IS DISTINCT FROM frame->>'case_id'
 OR frame->>'operation' IS DISTINCT FROM variant OR frame->>'rubric_version' IS DISTINCT FROM policy_id
 OR NOT frame ? 'component_id' OR ((frame->>'component_id' IS NOT NULL) IS DISTINCT FROM (variant='definition_components'))
 OR frame->>'direction' NOT IN ('source_first','output_first')
 OR (frame->>'direction'='source_first' AND frame->'exposed_outputs'<>'[]'::jsonb)
 OR (frame->>'direction'='output_first' AND NOT EXISTS(SELECT FROM jsonb_array_elements(frame->'exposed_outputs') exposed
 WHERE jsonb_strip_nulls(exposed)=jsonb_strip_nulls(report_reference))) THEN
 RAISE EXCEPTION 'structural passes differ from exact report/source/question/rubric/exposure frame' USING ERRCODE='23514'; END IF;
 IF actors @> jsonb_build_array(pass_body->'actor') THEN
 RAISE EXCEPTION 'structural passes repeat an attributed actor identity' USING ERRCODE='23514'; END IF;
 actors:=actors||jsonb_build_array(pass_body->'actor');
 IF pass_body->>'pass_kind' IN ('A','B') THEN
 IF pass_body->'parents'<>'[]'::jsonb THEN RAISE EXCEPTION 'A/B cannot adjudicate another pass' USING ERRCODE='23514'; END IF;
 parent_values:=parent_values||jsonb_build_array(jsonb_build_object('reference',ops.ddo_structural_product_reference(pass_product),'body_digest',pass_product.body_digest)); END IF;
 passes:=passes||jsonb_build_object(pass_body->>'pass_kind',pass_body);
 END LOOP;
 IF (SELECT count(*) FROM jsonb_object_keys(passes))<>3 OR NOT passes ?& ARRAY['A','B','C'] THEN
 RAISE EXCEPTION 'structural admission requires the exact A/B/C population' USING ERRCODE='23514'; END IF;
 c:=passes->'C';
 IF jsonb_array_length(c->'parents')<>2 OR jsonb_strip_nulls(c->'parents') @> jsonb_strip_nulls(parent_values) IS NOT TRUE
 OR jsonb_strip_nulls(parent_values) @> jsonb_strip_nulls(c->'parents') IS NOT TRUE THEN
 RAISE EXCEPTION 'C does not adjudicate exact original A/B product/body identities' USING ERRCODE='23514'; END IF;
 selected_component:=frame->>'component_id';
 statement:=ops.ddo_structural_statement(report_product.canonical_body,selected_component);
 SELECT value INTO STRICT selected_case FROM jsonb_array_elements(c->'cases')
 WHERE value->>'facet'='public_statement' AND value->'path'='["public_statement"]'::jsonb
 AND value->>'judgment'='supported' AND value->>'expected_meaning_json'=data.canonical_json(statement);
 IF NOT (selected_case->'source_passages' @> coalesce((SELECT jsonb_agg(value->>'passage_id') FROM jsonb_array_elements(report->'inputs'->'passages')),'[]')) THEN
 RAISE EXCEPTION 'structural supported statement omits selected source passages' USING ERRCODE='23514'; END IF;
 expected:=jsonb_build_object('version','structural-admission-1','report',report_reference,'component_id',selected_component,
 'policy_id',policy_id,'policy_version','1','statement_encoding','ddo-semantic-value-v1',
 'statement_meaning_json',data.canonical_json(statement),'standing','admitted_structural_statement',
 'assessment_basis','independently_attributed_authored_judgments','scientific_truth','not_established',
 'member_truth','not_established_by_assembly_admission');
 output:=completion->'outputs'->0;
 IF output->>'role' IS DISTINCT FROM 'admission' OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind='__KIND__' AND kind.universe='ordinary')
 OR data.ddo_normalize(output->'product'->'body') IS DISTINCT FROM data.ddo_normalize(data.ddo_json_meaning(expected)) THEN
 RAISE EXCEPTION 'structural ordinary conclusion differs from exact independently adjudicated statement' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'structural admission cannot resolve exact original custody' USING ERRCODE='23514';
END $structural$;

REVOKE ALL ON FUNCTION ops.ddo_structural_command_eligible(sem.data_operation_definition),
ops.ddo_structural_product_reference(kb.data_product),ops.ddo_require_structural_admission_completion(ops.data_request,jsonb) FROM PUBLIC;




"""
    sql = (
        sql.replace("__OPERATION__", ADMISSION_OPERATION)
        .replace("__KIND__", ADMISSION_KIND)
        .replace("__REFERENCE_KIND__", REFERENCE_KIND)
        .replace(
            "__REPORT_PRODUCERS__",
            ",".join(
                "(" + ",".join("'" + item + "'" for item in (variant, operation, factory)) + ")"
                for variant, producers in STRUCTURAL_REPORT_PRODUCERS.items()
                for operation, factory in producers
            ),
        )
    )
    from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script

    report_identity = NativeIdentity(
        "function",
        "ops",
        "ddo_structural_report_support",
        ("text", "ops.data_demand_read", "jsonb"),
    )
    return (
        structural_statement_native_sql()
        + _structural_command_helpers(model)
        + sql
        + _structural_dossier_completion(model)
        + native_sql_script(
            (
                _structural_report_support(model),
                native_privilege_sql(report_identity, "PUBLIC", grant=False),
            )
        )
    )


def _structural_report_support(model):
    """Authenticate the selectively disclosed report using the actual local cut."""
    from sqlalchemy import Boolean, Text, and_, case, cast, func, literal, select
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.types import NullType

    from .declared_structural_admission import ADMISSION_KIND
    from .native_program import (
        Assign,
        Block,
        CatchStrictLookup,
        If,
        Local,
        Parameter,
        Return,
        SelectInto,
        core_relation_row,
        core_variable,
        function,
        pg_type,
    )

    demand, uses, episodes, requests, definitions, outputs, products, kinds, inputs, supports = (
        model.tables[name]
        for name in (
            "ops.data_demand",
            "ops.demand_use",
            "ops.data_derivation",
            "ops.data_request",
            "sem.data_operation_definition",
            "ops.data_derivation_output",
            "kb.data_product",
            "sem.data_kind_contract",
            "ops.data_derivation_input",
            "ops.data_derivation_support",
        )
    )
    reads = model.tables["ops.data_demand_read"]
    boundary = core_variable("boundary", NullType())
    requested = core_variable("requested_products", JSONB())
    selected_use = core_variable("selected_use", Text())
    value = core_variable("value", JSONB())
    role_name = core_variable("role_name", Text())
    nominal = core_variable("nominal", Text())

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def b(field):
        return row("boundary", reads, field)

    def d(field):
        return row("demand", demand, field)

    def chosen(field):
        return row("chosen", uses, field)

    def episode(field):
        return row("episode", episodes, field)

    def input_(field):
        return row("input", inputs, field)

    def report(field):
        return row("report", products, field)

    def support(field):
        return row("support", supports, field)

    def selected(table, where, name, relation=None):
        return SelectInto(
            select(core_relation_row(table))
            .select_from(table if relation is None else relation)
            .where(where),
            (name,),
            strict=True,
        )

    def unavailable(condition):
        return If(condition, (Return(literal(None)),))

    newer = uses.alias("newer")
    report_use = uses.alias("used")
    producer = episodes.alias("producer")
    variants = (
        (
            "independent-structural-comparison-1",
            "comparison",
            "urn:corpus:structural:DeclaredComparisonReport",
        ),
        (
            "independent-condition-qualification-1",
            "condition",
            "urn:corpus:structural:DeclaredConditionReport",
        ),
        (
            "independent-definition-component-1",
            "definition",
            "urn:corpus:structural:DeclaredDefinitionComponentsReport",
        ),
    )
    policies = tuple(policy for policy, _, _ in variants)
    return function(
        "ops",
        "ddo_structural_report_support",
        parameters=(
            Parameter("selected_use", pg_type("text")),
            Parameter("boundary", pg_type("ops", "data_demand_read")),
            Parameter("requested_products", pg_type("jsonb")),
        ),
        returns=pg_type("jsonb"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                CatchStrictLookup(
                    (
                        unavailable(~b("public_disclosure")),
                        unavailable(func.jsonb_typeof(requested).is_distinct_from("array")),
                        selected(demand, demand.c.id == b("demand_id"), "demand"),
                        selected(
                            uses,
                            and_(uses.c.id == selected_use, uses.c.demand_id == b("demand_id")),
                            "chosen",
                        ),
                        unavailable(
                            or_(
                                chosen("fate").is_distinct_from("fulfilled"),
                                ~func.coalesce(
                                    func.ops.ddo_read_visible(
                                        chosen("created_at"),
                                        chosen("created_xid"),
                                        boundary,
                                        type_=Boolean(),
                                    ),
                                    False,
                                ),
                                select(1)
                                .select_from(newer)
                                .where(
                                    newer.c.obligation_id == chosen("obligation_id"),
                                    func.ops.ddo_read_visible(
                                        newer.c.created_at, newer.c.created_xid, boundary
                                    ),
                                    or_(
                                        newer.c.created_at > chosen("created_at"),
                                        and_(
                                            newer.c.created_at == chosen("created_at"),
                                            newer.c.id > chosen("id"),
                                        ),
                                    ),
                                )
                                .exists(),
                            )
                        ),
                        selected(
                            episodes,
                            and_(
                                episodes.c.id == chosen("derivation_id"),
                                episodes.c.outcome == "success",
                            ),
                            "episode",
                        ),
                        selected(
                            definitions,
                            and_(
                                requests.c.id == episode("request_id"),
                                requests.c.project_id == d("project_id"),
                            ),
                            "issuer",
                            definitions.join(
                                requests,
                                and_(
                                    requests.c.operation_id == definitions.c.operation_id,
                                    definitions.c.release_id == episode("release_id"),
                                ),
                            ),
                        ),
                        unavailable(
                            or_(
                                ~func.coalesce(
                                    row("issuer", definitions, "command_class") == "structural",
                                    False,
                                ),
                                ~func.coalesce(
                                    func.ops.ddo_policy_authority_leaf(
                                        episode("id"), type_=Boolean()
                                    ),
                                    False,
                                ),
                            )
                        ),
                        unavailable(
                            ~func.coalesce(
                                func.ops.ddo_node_valid(
                                    "use", chosen("id"), boundary, type_=Boolean()
                                ),
                                False,
                            )
                        ),
                        selected(
                            products,
                            and_(
                                outputs.c.derivation_id == episode("id"),
                                outputs.c.role == "admission",
                                outputs.c.position == 0,
                                outputs.c.multiplicity == 1,
                                outputs.c.member_id.is_(None),
                                products.c.project_id == d("project_id"),
                                kinds.c.kind == ADMISSION_KIND,
                                kinds.c.universe == "ordinary",
                                requested.has_key(products.c.id),
                            ),
                            "conclusion",
                            products.join(outputs, outputs.c.product_id == products.c.id).join(
                                kinds, kinds.c.kind_contract == products.c.kind_contract
                            ),
                        ),
                        Assign(
                            "value",
                            cast(
                                func.data.ddo_json(row("conclusion", products, "canonical_body")),
                                JSONB(),
                            ),
                        ),
                        unavailable(value["policy_id"].astext.not_in(policies)),
                        Assign(
                            "role_name",
                            case(
                                *(
                                    (value["policy_id"].astext == policy, literal(role))
                                    for policy, role, _ in variants
                                )
                            ),
                        ),
                        Assign(
                            "nominal",
                            case(
                                *(
                                    (value["policy_id"].astext == policy, literal(kind))
                                    for policy, _, kind in variants
                                )
                            ),
                        ),
                        selected(
                            inputs,
                            and_(
                                inputs.c.derivation_id == episode("id"),
                                inputs.c.role == role_name,
                                inputs.c.position == 0,
                                inputs.c.multiplicity == 1,
                                inputs.c.member_id.is_(None),
                            ),
                            "input",
                        ),
                        selected(
                            products,
                            and_(
                                products.c.id == input_("product_id"),
                                products.c.project_id == d("project_id"),
                                kinds.c.kind == nominal,
                                kinds.c.universe == "ordinary",
                                requested.has_key(products.c.id),
                                func.ops.ddo_body_access(
                                    products.c.kind_contract, products.c.canonical_body
                                ),
                            ),
                            "report",
                            products.join(kinds, kinds.c.kind_contract == products.c.kind_contract),
                        ),
                        unavailable(
                            func.jsonb_strip_nulls(value["report"]).is_distinct_from(
                                func.jsonb_strip_nulls(
                                    func.ops.ddo_structural_product_reference(
                                        core_variable("report", NullType())
                                    )
                                )
                            )
                        ),
                        selected(
                            supports,
                            and_(
                                supports.c.derivation_id == episode("id"),
                                supports.c.role == role_name,
                                supports.c.position == 0,
                            ),
                            "support",
                        ),
                        SelectInto(
                            select(*report_use.c)
                            .select_from(
                                report_use.join(
                                    producer, producer.c.id == report_use.c.derivation_id
                                )
                                .join(requests, requests.c.id == producer.c.request_id)
                                .join(outputs, outputs.c.derivation_id == producer.c.id)
                            )
                            .where(
                                report_use.c.id == support("admission_use_id"),
                                report_use.c.derivation_id == support("support_derivation_id"),
                                report_use.c.fate == "fulfilled",
                                producer.c.outcome == "success",
                                producer.c.completed_at <= b("frontier_at"),
                                requests.c.project_id == d("project_id"),
                                outputs.c.product_id == report("id"),
                                outputs.c.member_id.is_(None),
                                outputs.c.role == "result",
                                outputs.c.position == 0,
                                outputs.c.multiplicity == 1,
                                func.ops.ddo_read_visible(
                                    report_use.c.created_at, report_use.c.created_xid, boundary
                                ),
                                func.ops.ddo_node_valid("use", report_use.c.id, boundary),
                            ),
                            ("report_use",),
                            strict=True,
                        ),
                        Return(
                            func.jsonb_build_object(
                                "product_id",
                                report("id"),
                                "derivation_id",
                                row("report_use", uses, "derivation_id"),
                                "use_id",
                                row("report_use", uses, "id"),
                            )
                        ),
                    ),
                    (Return(literal(None)),),
                ),
            ),
            (
                *(
                    Local(name, table)
                    for name, table in (
                        ("demand", demand),
                        ("chosen", uses),
                        ("episode", episodes),
                        ("issuer", definitions),
                        ("conclusion", products),
                        ("report", products),
                        ("input", inputs),
                        ("report_use", uses),
                        ("support", supports),
                    )
                ),
                Local("value", pg_type("jsonb")),
                Local("role_name", pg_type("text")),
                Local("nominal", pg_type("text")),
            ),
        ),
    )
