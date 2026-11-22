"""Exact tagged structural statement lowering and protected native admission guards."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    Text,
    and_,
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

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchStrictLookup,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    SelectInto,
    Statement,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program import (
    literal as native_literal,
)
from .native_program_registry import ProgramDeclaration


def _structural_declaration(routine: NativeRoutine) -> ProgramDeclaration:
    return ProgramDeclaration(
        routine,
        source="data-operations:forward",
        owner=role_name("publisher"),
        access=INTERNAL_PROGRAM,
    )


def _structural_pairs(programs):
    return native_sql_script(
        statement
        for item in programs
        for statement in (
            item.routine.render(),
            native_privilege_sql(item.identity, "PUBLIC", grant=False),
        )
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


def _structural_statement_routines():
    """Compile tagged subtrees directly, preserving nulls and numeric meaning."""
    programs: list[NativeRoutine] = []

    def add(name, parameters, *, query=None, steps=(), locals_=(), strict=True):
        parameters = tuple(
            Parameter(label, pg_type(type_), *default) for label, type_, *default in parameters
        )
        if query is None:
            declaration = NativeRoutine(
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
            declaration = NativeRoutine(
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
        NativeRoutine(
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
    return tuple(programs)


def structural_statement_native_programs() -> tuple[ProgramDeclaration, ...]:
    return tuple(_structural_declaration(routine) for routine in _structural_statement_routines())


def structural_statement_native_sql() -> str:
    return _structural_pairs(structural_statement_native_programs()) + "\n"


def _structural_command_programs(model):
    definitions = model.tables["sem.data_operation_definition"]
    products = model.tables["kb.data_product"]

    def definition(field):
        return core_variable("definition", definitions.c[field].type, field)

    def product(field):
        return core_variable("product", products.c[field].type, field)

    support = definition("support_contract")
    factory = support["capabilities"]["prepared_factory"]
    return tuple(
        _structural_declaration(routine)
        for routine in (
            NativeRoutine(
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
                    (
                        func.ops.ddo_privileged_effect_eligible(
                            core_variable("definition", JSONB()),
                            "native-evaluator-structural-admission",
                        )
                    )
                    & (definition("profile") == "command")
                    & (support["capabilities"]["preparation"].astext == "native-publication")
                    & (support["capabilities"]["forms"] == _json('["scalar"]'))
                    & (func.nullif(factory["entrypoint"].astext, "").is_not(None))
                    & factory["source_digest"].astext.op("~")("^[0-9a-f]{64}$")
                    & definition("implementation_revision").like("implementation-slice:%")
                ),
            ),
            NativeRoutine(
                "ops",
                "ddo_structural_product_reference",
                parameters=(Parameter("product", pg_type(str(products.schema), products.name)),),
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
    return _structural_declaration(
        NativeRoutine(
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
        )
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
    declared_output = _items(definitions.c.output_roles, "dossier_output")
    is_dossier = (
        select(1)
        .select_from(
            definitions.join(declared_output, literal(True)).join(
                kinds, kinds.c.kind_contract == declared_output.c.value["kind_contract"].astext
            )
        )
        .where(
            definitions.c.release_id == r("release_id"),
            definitions.c.operation_id == r("operation_id"),
            kinds.c.kind == "urn:corpus:structural:DeclaredDossierReport",
        )
        .exists()
    )
    return _completion_program(
        "ddo_require_structural_dossier_completion",
        requests,
        (
            If(~is_dossier, (Return(),)),
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
                    func.nullif(factory["entrypoint"].astext, "").is_(None),
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


def _structural_issuance_completion(model):
    from .declared_structural_admission import (
        ADMISSION_KIND,
        REFERENCE_KIND,
    )

    definitions, requests, products, kinds, admissions, episodes, outputs, receipts, intents = (
        model.tables[name]
        for name in (
            "sem.data_operation_definition",
            "ops.data_request",
            "kb.data_product",
            "sem.data_kind_contract",
            "ops.original_source_admission",
            "ops.data_derivation",
            "ops.data_derivation_output",
            "ops.data_publication_receipt",
            "ops.data_completion_intent",
        )
    )

    def r(field=None):
        return _completion_row("r", requests, field)

    def definition(field):
        return _completion_row("definition", definitions, field)

    def report_product(field=None):
        return _completion_row("report_product", products, field)

    def pass_product(field=None):
        return _completion_row("pass_product", products, field)

    def pass_kind(field):
        return _completion_row("pass_kind", kinds, field)

    def admitted(field):
        return _completion_row("admitted", admissions, field)

    completion = core_variable("completion", JSONB())
    selected = core_variable("selected", JSONB())
    output = core_variable("output", JSONB())
    pass_body = core_variable("pass_body", JSONB())
    frame = core_variable("frame", JSONB())
    passes = core_variable("passes", JSONB())
    actors = core_variable("actors", JSONB())
    parents = core_variable("parent_values", JSONB())
    c = core_variable("c", JSONB())
    report = core_variable("report", JSONB())
    statement = core_variable("statement", JSONB())
    expected = core_variable("expected", JSONB())
    selected_case = core_variable("selected_case", JSONB())
    report_reference = core_variable("report_reference", JSONB())
    producer_count = core_variable("producer_count", BigInteger())
    report_kind = core_variable("report_kind", kinds.c.kind.type)
    variant = core_variable("variant", Text())
    report_role = core_variable("report_role", Text())
    policy_id = core_variable("policy_id", Text())
    selected_component = core_variable("selected_component", Text())
    inputs = _items(completion["inputs"], "inputs_")
    effects = _items(definition("support_contract")["effects"], "effects_")
    supports = (
        func.ops.ddo_input_support_refs(r("binding"), selected)
        .table_valued(column("value", JSONB()))
        .render_derived(name="supports_")
    )
    owner = definitions.alias("owner")
    producer_join = (
        episodes.join(outputs, outputs.c.derivation_id == episodes.c.id)
        .join(
            receipts,
            (receipts.c.derivation_id == episodes.c.id)
            & (receipts.c.intent_id == episodes.c.intent_id),
        )
        .join(requests, requests.c.id == episodes.c.request_id)
        .join(
            owner,
            (owner.c.release_id == episodes.c.release_id)
            & (owner.c.operation_id == requests.c.operation_id),
        )
        .join(intents, intents.c.id == episodes.c.intent_id)
    )
    producer_roles = _items(owner.c.output_roles, "admitted_report_output")
    consumer_roles = _items(definition("input_roles"), "admitted_report_input")
    admitted_report_shape = exists(
        select(1)
        .select_from(producer_roles.join(consumer_roles, literal(True)))
        .where(
            producer_roles.c.value["name"].astext == outputs.c.role,
            producer_roles.c.value["kind_contract"].astext == report_product("kind_contract"),
            consumer_roles.c.value["name"].astext == report_role,
            consumer_roles.c.value["accepted_kind_contracts"].contains(
                func.jsonb_build_array(report_product("kind_contract"))
            ),
        )
    )
    producer_factory = owner.c.support_contract["capabilities"]["prepared_factory"]
    producer_query = (
        select(func.count())
        .select_from(producer_join)
        .where(
            outputs.c.product_id == report_product("id"),
            outputs.c.member_id.is_(None),
            outputs.c.role == "result",
            outputs.c.position == 0,
            outputs.c.multiplicity == 1,
            episodes.c.outcome == "success",
            owner.c.profile == "derivation",
            owner.c.support_contract["effects"] == _json("[]"),
            admitted_report_shape,
            func.nullif(producer_factory["entrypoint"].astext, "").is_not(None),
            producer_factory["source_digest"].astext.op("~")("^[0-9a-f]{64}$"),
            owner.c.implementation_revision.like("implementation-slice:%"),
            owner.c.recipe == episodes.c.recipe,
            intents.c.payload["implementation_revision"].astext == owner.c.implementation_revision,
            func.jsonb_array_length(
                func.coalesce(intents.c.payload["execution_evidence"]["cpu_receipts"], _json("[]"))
            )
            == 1,
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
    exposed = _items(frame["exposed_outputs"], "exposed_")
    cases = _items(c["cases"], "cases_")
    source_passages = _items(report["inputs"]["passages"], "source_passages_")
    pass_names = (
        func.jsonb_object_keys(passes)
        .table_valued(column("name", Text()))
        .render_derived(name="pass_names_")
    )
    pass_steps = (
        _completion_refusal(
            or_(
                selected["member_id"].astext.is_not(None),
                cast(selected["multiplicity"].astext, Integer()).is_distinct_from(1),
            ),
            "structural passes require distinct whole original authored products",
        ),
        _completion_lookup(
            "pass_product",
            products,
            products.c.id == selected["product_id"].astext,
            products.c.project_id == r("project_id"),
        ),
        _completion_lookup(
            "pass_kind", kinds, kinds.c.kind_contract == pass_product("kind_contract")
        ),
        _completion_refusal(
            or_(
                pass_kind("kind").is_distinct_from(REFERENCE_KIND),
                pass_kind("universe").is_distinct_from("evaluator"),
            ),
            "structural pass differs from its protected nominal kind",
        ),
        _completion_lookup(
            "admitted",
            admissions,
            admissions.c.product_id == pass_product("id"),
            admissions.c.project_id == r("project_id"),
            admissions.c.reference["kind"].astext == "authored-fact",
            func.ops.ddo_original_admission_valid(core_relation_row(admissions)),
            relation=admissions.join(
                supports,
                (supports.c.value["kind"].astext == "authored")
                & (supports.c.value["admission_id"].astext == admissions.c.id)
                & (supports.c.value["source_reference"].astext == admissions.c.source_reference),
            ),
        ),
        Assign("pass_body", func.data.ddo_json(pass_product("canonical_body"), type_=JSONB())),
        _completion_refusal(
            or_(
                admitted("evidence")["standing"].astext.is_distinct_from("authored"),
                func.nullif(admitted("evidence")["submitted_by"].astext, "").is_(None),
                admitted("reference")["author"].astext.is_distinct_from(
                    pass_body["author_assertion"].astext
                ),
                admitted("evidence")["author_assertion"].astext.is_distinct_from(
                    pass_body["author_assertion"].astext
                ),
                pass_body["actor"]["principal"].astext.is_distinct_from(
                    pass_body["author_assertion"].astext
                ),
                pass_body["actor"]["basis"].astext.is_distinct_from("authored_attribution"),
                pass_body["version"].astext.is_distinct_from("structural-reference-pass-1"),
                pass_body["pass_kind"].astext.not_in(("A", "B", "C")),
                passes.has_key(pass_body["pass_kind"].astext),
            ),
            "structural pass lacks its exact original submitted author attribution",
        ),
        If(frame.is_(None), (Assign("frame", pass_body["frame"]),)),
        _completion_refusal(
            or_(
                frame.is_distinct_from(pass_body["frame"]),
                func.jsonb_strip_nulls(frame["report"]).is_distinct_from(
                    func.jsonb_strip_nulls(report_reference)
                ),
                func.jsonb_strip_nulls(frame["inputs"]).is_distinct_from(
                    func.jsonb_strip_nulls(report["inputs"])
                ),
                frame["question"].astext.is_distinct_from(report["inputs"]["question"].astext),
                func.jsonb_array_length(pass_body["cases"]) != 1,
                pass_body["cases"][0]["case_id"].astext.is_distinct_from(frame["case_id"].astext),
                frame["operation"].astext.is_distinct_from(variant),
                frame["rubric_version"].astext.is_distinct_from(policy_id),
                ~frame.has_key("component_id"),
                frame["component_id"]
                .astext.is_not(None)
                .is_distinct_from(variant == "definition_components"),
                frame["direction"].astext.not_in(("source_first", "output_first")),
                (frame["direction"].astext == "source_first")
                & (frame["exposed_outputs"] != _json("[]")),
                (frame["direction"].astext == "output_first")
                & ~exists(
                    select(1)
                    .select_from(exposed)
                    .where(
                        func.jsonb_strip_nulls(exposed.c.value)
                        == func.jsonb_strip_nulls(report_reference)
                    )
                ),
            ),
            "structural passes differ from exact report/source/question/rubric/exposure frame",
        ),
        _completion_refusal(
            actors.contains(func.jsonb_build_array(pass_body["actor"])),
            "structural passes repeat an attributed actor identity",
        ),
        Assign("actors", actors.op("||")(func.jsonb_build_array(pass_body["actor"]))),
        If(
            pass_body["pass_kind"].astext.in_(("A", "B")),
            (
                _completion_refusal(
                    pass_body["parents"] != _json("[]"), "A/B cannot adjudicate another pass"
                ),
                Assign(
                    "parent_values",
                    parents.op("||")(
                        func.jsonb_build_array(
                            func.jsonb_build_object(
                                "reference",
                                _structural("product_reference", pass_product()),
                                "body_digest",
                                pass_product("body_digest"),
                                type_=JSONB(),
                            )
                        )
                    ),
                ),
            ),
        ),
        Assign(
            "passes",
            passes.op("||")(
                func.jsonb_build_object(pass_body["pass_kind"].astext, pass_body, type_=JSONB())
            ),
        ),
    )
    variants = (
        (
            "urn:corpus:structural:DeclaredComparisonReport",
            "qualified_comparison",
            "comparison",
            "independent-structural-comparison-1",
        ),
        (
            "urn:corpus:structural:DeclaredConditionReport",
            "condition_qualification",
            "condition",
            "independent-condition-qualification-1",
        ),
        (
            "urn:corpus:structural:DeclaredDefinitionComponentsReport",
            "definition_components",
            "definition",
            "independent-definition-component-1",
        ),
    )
    select_variant: tuple[Statement, ...] = (
        Raise("structural admission requires its actual released report kind", "23514"),
    )
    for kind, tag, role, policy in reversed(variants):
        select_variant = (
            If(
                report_kind.in_(
                    (kind, "urn:corpus:structural:DeclaredNamedDefinitionComponentsReport")
                    if tag == "definition_components"
                    else (kind,)
                ),
                (
                    Assign("variant", literal(tag)),
                    Assign("report_role", literal(role)),
                    Assign("policy_id", literal(policy)),
                ),
                select_variant,
            ),
        )
    expected_fields = (
        ("version", "structural-admission-1"),
        ("report", report_reference),
        ("component_id", selected_component),
        ("policy_id", policy_id),
        ("policy_version", "1"),
        ("statement_encoding", "ddo-semantic-value-v1"),
        ("statement_meaning_json", func.data.canonical_json(statement)),
        ("standing", "admitted_structural_statement"),
        ("assessment_basis", "independently_attributed_authored_judgments"),
        ("scientific_truth", "not_established"),
        ("member_truth", "not_established_by_assembly_admission"),
    )
    return _completion_program(
        "ddo_require_structural_admission_completion",
        requests,
        (
            _completion_lookup(
                "definition",
                definitions,
                definitions.c.release_id == r("release_id"),
                definitions.c.operation_id == r("operation_id"),
            ),
            If(
                ~func.coalesce(definition("command_class") == "structural", literal(False)),
                (
                    _completion_refusal(
                        or_(
                            exists(
                                select(1)
                                .select_from(effects)
                                .where(
                                    effects.c.value["name"].astext
                                    == "native-evaluator-structural-admission"
                                )
                            ),
                        ),
                        "structural admission requires its exact command/effect/factory",
                    ),
                    Return(),
                ),
            ),
            _completion_refusal(
                ~func.ops.ddo_privileged_effect_admitted(
                    core_variable("definition", JSONB()), "native-evaluator-structural-admission"
                ),
                "structural admission lacks its independent release effect grant",
                "42501",
            ),
            _completion_refusal(
                or_(
                    completion["outcome"].astext.is_distinct_from("success"),
                    func.jsonb_array_length(completion["inputs"]) != 4,
                    func.jsonb_array_length(completion["outputs"]) != 1,
                ),
                "structural admission requires one report, three exact passes and one conclusion",
            ),
            SelectInto(
                select(inputs.c.value).where(
                    inputs.c.value["role"].astext.in_(("comparison", "condition", "definition"))
                ),
                ("selected",),
                strict=True,
            ),
            _completion_refusal(
                or_(
                    selected["member_id"].astext.is_not(None),
                    cast(selected["position"].astext, Integer()).is_distinct_from(0),
                    cast(selected["multiplicity"].astext, Integer()).is_distinct_from(1),
                ),
                "structural report must be its exact whole scalar input",
            ),
            _completion_lookup(
                "report_product",
                products,
                products.c.id == selected["product_id"].astext,
                products.c.project_id == r("project_id"),
            ),
            SelectInto(
                select(kinds.c.kind).where(
                    kinds.c.kind_contract == report_product("kind_contract"),
                    kinds.c.universe == "ordinary",
                ),
                ("report_kind",),
                strict=True,
            ),
            *select_variant,
            Assign("report", func.data.ddo_json(report_product("canonical_body"), type_=JSONB())),
            _completion_refusal(
                or_(
                    report["kind"].astext.is_distinct_from(variant),
                    selected["role"].astext.is_distinct_from(report_role),
                ),
                "structural report differs from its exact choice-bound nominal variant",
            ),
            SelectInto(producer_query, ("producer_count",)),
            _completion_refusal(
                producer_count != 1,
                "structural report lacks its one actual captured producer for the selected variant",
            ),
            Assign("report_reference", _structural("product_reference", report_product())),
            ForQuery(
                ("selected",),
                select(inputs.c.value).where(inputs.c.value["role"].astext == "passes"),
                pass_steps,
            ),
            _completion_refusal(
                or_(
                    select(func.count()).select_from(pass_names).scalar_subquery() != 3,
                    ~passes.has_all(array(("A", "B", "C"), type_=Text())),
                ),
                "structural admission requires the exact A/B/C population",
            ),
            Assign("c", passes["C"]),
            _completion_refusal(
                or_(
                    func.jsonb_array_length(c["parents"]) != 2,
                    func.jsonb_strip_nulls(c["parents"], type_=JSONB())
                    .contains(func.jsonb_strip_nulls(parents))
                    .is_not(True),
                    func.jsonb_strip_nulls(parents, type_=JSONB())
                    .contains(func.jsonb_strip_nulls(c["parents"]))
                    .is_not(True),
                ),
                "C does not adjudicate exact original A/B product/body identities",
            ),
            Assign("selected_component", frame["component_id"].astext),
            Assign(
                "statement",
                _structural("statement", report_product("canonical_body"), selected_component),
            ),
            SelectInto(
                select(cases.c.value).where(
                    cases.c.value["facet"].astext == "public_statement",
                    cases.c.value["path"] == _json('["public_statement"]'),
                    cases.c.value["judgment"].astext == "supported",
                    cases.c.value["expected_meaning_json"].astext
                    == func.data.canonical_json(statement),
                ),
                ("selected_case",),
                strict=True,
            ),
            _completion_refusal(
                ~selected_case["source_passages"].contains(
                    func.coalesce(
                        select(
                            func.jsonb_agg(source_passages.c.value["passage_id"].astext)
                        ).scalar_subquery(),
                        _json("[]"),
                    )
                ),
                "structural supported statement omits selected source passages",
            ),
            Assign(
                "expected",
                func.jsonb_build_object(
                    *(part for pair in expected_fields for part in pair), type_=JSONB()
                ),
            ),
            Assign("output", completion["outputs"][0]),
            _completion_refusal(
                or_(
                    output["role"].astext.is_distinct_from("admission"),
                    output["member_id"].astext.is_not(None),
                    cast(output["position"].astext, Integer()).is_distinct_from(0),
                    cast(output["multiplicity"].astext, Integer()).is_distinct_from(1),
                    output["product"]["members"].is_distinct_from(_json("[]")),
                    ~exists(
                        select(1)
                        .select_from(kinds)
                        .where(
                            kinds.c.kind_contract == output["product"]["kind_contract"].astext,
                            kinds.c.kind == ADMISSION_KIND,
                            kinds.c.universe == "ordinary",
                        )
                    ),
                    func.data.ddo_normalize(output["product"]["body"]).is_distinct_from(
                        func.data.ddo_normalize(func.data.ddo_json_meaning(expected))
                    ),
                ),
                "structural ordinary conclusion differs from exact independently adjudicated statement",
            ),
        ),
        (
            Local("definition", definitions),
            Local("selected", pg_type("jsonb")),
            Local("output", pg_type("jsonb")),
            Local("report_product", products),
            Local("pass_product", products),
            Local("pass_kind", kinds),
            Local("admitted", admissions),
            Local("pass_body", pg_type("jsonb")),
            Local("frame", pg_type("jsonb")),
            Local("passes", pg_type("jsonb"), _json("{}")),
            Local("actors", pg_type("jsonb"), _json("[]")),
            Local("parent_values", pg_type("jsonb"), _json("[]")),
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "c",
                    "report",
                    "statement",
                    "expected",
                    "selected_case",
                    "report_reference",
                )
            ),
            Local("producer_count", pg_type("int8")),
            Local("report_kind", column_type(kinds.c.kind)),
            *(
                Local(name, pg_type("text"))
                for name in ("variant", "report_role", "policy_id", "selected_component")
            ),
        ),
    )


def _structural_admission_groups(model):
    from .declared_structural_admission import DdoStructuralAdmission

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
    return (
        structural_statement_native_programs(),
        _structural_command_programs(model),
        (_structural_issuance_completion(model),),
        (_structural_dossier_completion(model),),
        (_structural_report_support(model),),
    )


def structural_admission_native_programs(model) -> tuple[ProgramDeclaration, ...]:
    return tuple(item for group in _structural_admission_groups(model) for item in group)


def structural_admission_native_sql(model) -> str:
    """Render the established statement, command and independent completion groups."""
    statements, commands, issuance, dossier, report = _structural_admission_groups(model)
    command_sql = native_sql_script(
        (
            *(item.routine.render() for item in commands),
            *(native_privilege_sql(item.identity, "PUBLIC", grant=False) for item in commands),
        )
    )
    return (
        _structural_pairs(statements)
        + "\n"
        + command_sql
        + "\n"
        + _structural_pairs(issuance)
        + "\n"
        + _structural_pairs(dossier)
        + "\n"
        + _structural_pairs(report)
    )


def _structural_report_support(model):
    """Authenticate the selectively disclosed report using the actual local cut."""
    from sqlalchemy import Boolean, Text, case, cast, func, literal, select
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.types import NullType

    from .declared_structural_admission import ADMISSION_KIND
    from .native_program import (
        Assign,
        Block,
        CatchStrictLookup,
        If,
        Local,
        NativeRoutine,
        Parameter,
        Return,
        SelectInto,
        core_relation_row,
        core_variable,
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
    routine = NativeRoutine(
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
                                or_(
                                    kinds.c.kind == nominal,
                                    and_(
                                        nominal
                                        == "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                                        kinds.c.kind
                                        == "urn:corpus:structural:DeclaredNamedDefinitionComponentsReport",
                                    ),
                                ),
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
    return _structural_declaration(routine)
