"""Compile selected populations and exact source acquisition from domain metadata."""

from typing import get_args, get_type_hints

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Integer,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    func,
    literal,
    null,
    or_,
    select,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSONB, array, insert

from .binding_recursive_native import _check, _each, _elements, _json, _texts, _value, pg_type_array
from .data_operation_model import BindingExpression
from .data_operation_projections import (
    binding_columns,
    cut_selection_projection,
    selected_source_output_occurrences,
    selected_support_output,
)
from .native_program import (
    Assign,
    Block,
    Continue,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    PerformQuery,
    Return,
    SelectInto,
    Sql,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)


def _object(**fields):
    return func.jsonb_build_object(
        *(part for pair in fields.items() for part in pair), type_=JSONB()
    )


def _procedure(name, parameters, steps, locals_=(), *, returns="jsonb"):
    return (
        function(
            "ops",
            name,
            parameters=tuple(Parameter(name, pg_type(kind)) for name, kind in parameters),
            returns=pg_type(returns),
            body=Block(tuple(steps), tuple(locals_)),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )
        + ";\n"
    )


def population_filter_native_sql():
    """Project only frozen row-local restrictions; retain aggregate authority."""
    node, choices = (_value(name, JSONB()) for name in ("node", "choices"))
    role, operator, choice = (_value(name) for name in ("role", "operator", "choice"))
    child, projected, children, selected = (
        _value(name, JSONB()) for name in ("child", "projected", "children", "selected")
    )
    names, matches = _value("names", ARRAY(Text())), _value("matches", Integer())
    child_rows = _elements(func.coalesce(node["children"], _json("[]")), "filter_child")
    nodes = select(node.label("n")).cte("descendants", recursive=True)
    descendants = _elements(
        func.coalesce(nodes.c.n["children"], _json("[]")), "filter_descendant"
    ).lateral("filter_descendant")
    nodes = nodes.union_all(
        select(descendants.c.value).select_from(nodes.join(descendants, literal(True)))
    )
    operands = _elements(func.coalesce(node["operands"], _json("[]")), "filter_operand")
    operators = get_args(get_type_hints(BindingExpression)["operator"])
    empty = _object(operator="all", children=_json("[]"))
    return (
        function(
            "ops",
            "ddo_population_filter",
            parameters=(
                Parameter("node", pg_type("jsonb")),
                Parameter("role", pg_type("text")),
                Parameter("choices", pg_type("jsonb")),
            ),
            returns=pg_type("jsonb"),
            volatility="immutable",
            strict=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                (
                    _check(
                        or_(operator.is_(None), ~operator.in_(operators)),
                        "unrepresentable selected-population filter operator",
                    ),
                    If(
                        operator == "choice",
                        (
                            Assign(
                                "choice",
                                func.coalesce(
                                    node["selected"].astext,
                                    choices[node["choice_parameter"].astext].astext,
                                ),
                            ),
                            ForQuery(
                                ("child",),
                                select(child_rows.c.value),
                                (
                                    If(
                                        choice == any_(func.ops.ddo_binding_roles(child)),
                                        (
                                            Assign("selected", child),
                                            Assign("matches", matches + 1),
                                        ),
                                    ),
                                ),
                            ),
                            _check(matches != 1, "population filter branch is not uniquely frozen"),
                            Return(func.ops.ddo_population_filter(selected, role, choices)),
                        ),
                    ),
                    Assign("names", func.ops.ddo_binding_roles(node)),
                    If(~(role == any_(names)), (Return(empty),)),
                    _check(
                        operator == "absent", "absence cannot define a positive selected population"
                    ),
                    If(
                        and_(
                            operator == "optional",
                            ~select(nodes.c.n)
                            .where(
                                or_(
                                    nodes.c.n["operator"].astext.is_(None),
                                    ~nodes.c.n["operator"].astext.in_(
                                        (
                                            "optional",
                                            "all",
                                            "scan",
                                            "covers",
                                            "cardinality",
                                            "collection",
                                            "forall",
                                            "same",
                                            "distinct",
                                        )
                                    ),
                                )
                            )
                            .exists(),
                        ),
                        (Return(empty),),
                    ),
                    _check(
                        and_(
                            operator == "optional",
                            or_(
                                func.cardinality(names) != 1,
                                select(nodes.c.n)
                                .where(
                                    ~nodes.c.n["operator"].astext.in_(
                                        (
                                            "optional",
                                            "all",
                                            "scan",
                                            "join",
                                            "equal",
                                            "literal",
                                            "range",
                                            "membership",
                                        )
                                    )
                                )
                                .exists(),
                            ),
                        ),
                        "optional population filter is not a closed row-local predicate",
                    ),
                    ForQuery(
                        ("child",),
                        select(child_rows.c.value),
                        (
                            Assign(
                                "projected", func.ops.ddo_population_filter(child, role, choices)
                            ),
                            If(
                                projected != empty,
                                (
                                    Assign(
                                        "children",
                                        children.op("||")(func.jsonb_build_array(projected)),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    Assign("names", func.ops.ddo_binding_roles(node.op("-")("children"))),
                    If(
                        and_(
                            operator.in_(("join", "equal", "literal", "range", "membership")),
                            func.cardinality(names) <= 1,
                        ),
                        (
                            If(
                                select(operands.c.value)
                                .where(
                                    operands.c.value["kind"].astext == "population",
                                    operands.c.value["population_projection"].astext
                                    == "qualified-context",
                                )
                                .exists(),
                                (Return(_object(operator="all", children=children)),),
                            ),
                            _check(
                                select(operands.c.value)
                                .where(operands.c.value["kind"].astext == "population")
                                .exists(),
                                "selected population filter requires explicit non-circular membership operands",
                            ),
                            Assign(
                                "children",
                                children.op("||")(func.jsonb_build_array(node.op("-")("children"))),
                            ),
                        ),
                    ),
                    Return(
                        _object(
                            operator=case((operator == "optional", "optional"), else_="all"),
                            children=children,
                        )
                    ),
                ),
                (
                    Local("operator", pg_type("text"), node["operator"].astext),
                    *(Local(name, pg_type("jsonb")) for name in ("child", "projected", "selected")),
                    Local("children", pg_type("jsonb"), _json("[]")),
                    Local("names", pg_type_array()),
                    Local("choice", pg_type("text")),
                    Local("matches", pg_type("integer"), literal(0)),
                ),
            ),
        )
        + ";\n"
    )


def source_acquisition_native_sql(model):
    """Reacquire retained cuts once and prove exact output occurrences per use."""
    demands, boundaries, products, members, kinds = (
        model.tables[name]
        for name in (
            "ops.data_demand",
            "ops.data_demand_read",
            "kb.data_product",
            "kb.data_product_member",
            "sem.data_kind_contract",
        )
    )

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def d(field):
        return row("d", demands, field)

    def boundary(field):
        return row("boundary", boundaries, field)

    def product(field):
        return row("product_row", products, field)

    def member(field):
        return row("member_row", members, field)

    project = _value("project")
    j = {
        name: _value(name, JSONB())
        for name in (
            "source_sets",
            "scope",
            "acquired",
            "selected",
            "proof",
            "entry",
            "entries",
            "cut",
            "output_keys",
        )
    }
    selected, proof, entry, scope, acquired = (
        j[name] for name in ("selected", "proof", "entry", "scope", "acquired")
    )
    p_use, p_product, p_derivation = (
        _value(name) for name in ("p_use", "p_product", "p_derivation")
    )
    selected_read = _object(
        demand_id=d("id"),
        read_id=boundary("id"),
        scope=boundary("scope"),
        view="frontier",
        limit=1,
        trust_snapshot=boundary("trust_snapshot"),
        read_snapshot=boundary("read_snapshot"),
        frontier_at=boundary("frontier_at"),
    )
    acquire_rows = (
        SelectInto(
            select(core_relation_row(demands))
            .select_from(demands)
            .where(demands.c.id == selected["demand_id"].astext, demands.c.project_id == project),
            ("d",),
            True,
        ),
        SelectInto(
            select(core_relation_row(boundaries))
            .select_from(boundaries)
            .where(
                boundaries.c.id == selected["read_id"].astext, boundaries.c.demand_id == d("id")
            ),
            ("boundary",),
            True,
        ),
        Assign("p", selected_read),
        Perform(func.ops.ddo_require_read_current(_value("boundary"), d("project_id"))),
        SelectInto(cut_selection_projection(), ("cut",)),
    )
    selected_output = _procedure(
        "ddo_require_selected_output",
        (
            ("p_demand", "text"),
            ("p_read", "text"),
            ("p_use", "text"),
            ("p_product", "text"),
            ("p_derivation", "text"),
        ),
        (
            SelectInto(
                select(core_relation_row(demands))
                .select_from(demands)
                .where(demands.c.id == _value("p_demand")),
                ("d",),
                True,
            ),
            SelectInto(
                select(core_relation_row(boundaries))
                .select_from(boundaries)
                .where(boundaries.c.id == _value("p_read"), boundaries.c.demand_id == d("id")),
                ("boundary",),
                True,
            ),
            Assign("p", selected_read),
            Perform(func.ops.ddo_require_read_current(_value("boundary"), d("project_id"))),
            SelectInto(selected_support_output(model), ("admitted",)),
            _check(
                ~func.coalesce(_value("admitted", Boolean()), False),
                "output is outside current pinned selected support",
                "23514",
            ),
            SelectInto(cut_selection_projection(), ("cut",)),
            Return(j["cut"]),
        ),
        (
            Local("d", demands),
            Local("boundary", boundaries),
            Local("p", pg_type("jsonb")),
            Local("admitted", pg_type("boolean")),
            Local("cut", pg_type("jsonb")),
        ),
    )
    scope_rows = _each(j["source_sets"], "source_scope")
    entries = _elements(scope["entries"], "source_entry")
    reads = _elements(scope["acquisition"]["reads"], "source_read")
    proofs = _elements(acquired["proofs"], "source_proof")
    occurrences = selected_source_output_occurrences(model).subquery("occurrence")
    output_key = func.jsonb_build_array(
        *(
            occurrences.c[name]
            for name in (
                "admission_use_id",
                "derivation_id",
                "product_id",
                "output_member_id",
                "role",
                "position",
                "multiplicity",
            )
        )
    )
    proof_key = func.jsonb_build_array(
        proof["support"]["admission_use_id"].astext,
        p_derivation,
        p_product,
        proof["output"]["member_id"].astext,
        proof["output"]["role"].astext,
        cast(proof["output"]["position"].astext, BigInteger()),
        cast(proof["output"]["multiplicity"].astext, BigInteger()),
    )
    selected_kind = func.coalesce(member("kind_contract"), product("kind_contract"))
    grouped = _procedure(
        "ddo_require_source_set_acquisitions",
        (("source_sets", "jsonb"), ("project", "text")),
        (
            ForQuery(
                ("scope",),
                select(scope_rows.c.value),
                (
                    If(
                        scope["acquisition"]["kind"].astext == "all-admissible-support-v1",
                        (Continue(),),
                    ),
                    _check(
                        scope["acquisition"]["kind"].astext.is_distinct_from("selected-support-v1"),
                        "unsupported source acquisition kind",
                    ),
                    SelectInto(
                        select(
                            func.coalesce(
                                func.jsonb_object_agg(
                                    cast(
                                        func.jsonb_build_array(
                                            entries.c.value["product"].astext,
                                            entries.c.value["member"].astext,
                                        ),
                                        Text(),
                                    ),
                                    entries.c.value,
                                ),
                                _json("{}"),
                            )
                        ),
                        ("entries",),
                    ),
                    ForQuery(
                        ("acquired",),
                        select(reads.c.value),
                        (
                            Assign("selected", acquired["selection"]),
                            _check(
                                or_(
                                    selected["project_id"].astext.is_distinct_from(project),
                                    selected["cut_id"].astext.is_distinct_from(
                                        literal("cut-selection:")
                                        + func.encode(
                                            func.sha256(
                                                func.convert_to(
                                                    selected["cut_canonical_json"].astext, "UTF8"
                                                )
                                            ),
                                            "hex",
                                        )
                                    ),
                                ),
                                "source acquisition changes exact cut/project",
                            ),
                            *acquire_rows,
                            _check(
                                or_(
                                    j["cut"].is_distinct_from(
                                        cast(selected["cut_canonical_json"].astext, JSONB())
                                    ),
                                    tuple_(
                                        selected["release_id"].astext, selected["runtime_id"].astext
                                    ).is_distinct_from(tuple_(d("release_id"), d("runtime_id"))),
                                ),
                                "source acquisition differs from native retained cut bytes",
                            ),
                            ForQuery(
                                ("p_use",),
                                select(proofs.c.value["anchor_use_id"].astext).distinct(),
                                (
                                    SelectInto(
                                        select(
                                            func.coalesce(
                                                func.jsonb_object_agg(
                                                    cast(output_key, Text()), literal(True)
                                                ),
                                                _json("{}"),
                                            )
                                        ).select_from(occurrences),
                                        ("output_keys",),
                                    ),
                                    ForQuery(
                                        ("proof",),
                                        select(proofs.c.value).where(
                                            proofs.c.value["anchor_use_id"].astext == p_use
                                        ),
                                        (
                                            Assign("p_product", proof["product_id"].astext),
                                            Assign(
                                                "p_derivation",
                                                proof["support"]["derivation_id"].astext,
                                            ),
                                            _check(
                                                ~j["output_keys"].bool_op("?")(
                                                    cast(proof_key, Text())
                                                ),
                                                "source proof is outside exact selected use/output support",
                                                "23514",
                                            ),
                                            Assign(
                                                "entry",
                                                j["entries"][
                                                    cast(
                                                        func.jsonb_build_array(
                                                            p_product, proof["member_id"].astext
                                                        ),
                                                        Text(),
                                                    )
                                                ],
                                            ),
                                            _check(
                                                entry.is_(None),
                                                "source proof lacks its semantic entry",
                                            ),
                                            SelectInto(
                                                select(core_relation_row(products))
                                                .select_from(products)
                                                .where(
                                                    products.c.id == p_product,
                                                    products.c.project_id == project,
                                                ),
                                                ("product_row",),
                                                True,
                                            ),
                                            Assign("member_row", null()),
                                            If(
                                                proof["member_id"].astext.is_not(None),
                                                (
                                                    SelectInto(
                                                        select(core_relation_row(members))
                                                        .select_from(members)
                                                        .where(
                                                            members.c.product_id == p_product,
                                                            members.c.member_id
                                                            == proof["member_id"].astext,
                                                        ),
                                                        ("member_row",),
                                                        True,
                                                    ),
                                                ),
                                            ),
                                            PerformQuery(
                                                select(
                                                    func.ops.ddo_authorize(kinds.c.universe)
                                                ).where(kinds.c.kind_contract == selected_kind)
                                            ),
                                            _check(
                                                or_(
                                                    ~func.coalesce(
                                                        func.ops.ddo_kind_access(
                                                            selected_kind, type_=Boolean()
                                                        ),
                                                        False,
                                                    ),
                                                    ~func.coalesce(
                                                        func.ops.ddo_body_access(
                                                            selected_kind,
                                                            func.coalesce(
                                                                member("body"),
                                                                product("canonical_body"),
                                                            ),
                                                            type_=Boolean(),
                                                        ),
                                                        False,
                                                    ),
                                                ),
                                                "selected source member is outside current purpose access",
                                                "42501",
                                            ),
                                            _check(
                                                or_(
                                                    tuple_(
                                                        entry["subject"].astext,
                                                        entry["subject_definition"].astext,
                                                        entry["original_source"].astext,
                                                    ).is_distinct_from(
                                                        tuple_(
                                                            func.coalesce(
                                                                member("subject"),
                                                                product("subject"),
                                                            ),
                                                            func.coalesce(
                                                                member("subject_definition"),
                                                                product("subject_definition"),
                                                            ),
                                                            product("original_source"),
                                                        )
                                                    ),
                                                    entry["analyzed_scope"].is_distinct_from(
                                                        func.coalesce(
                                                            member("analyzed_scope"),
                                                            product("analyzed_scope"),
                                                        )
                                                    ),
                                                    and_(
                                                        proof["output"]["member_id"].astext.is_not(
                                                            None
                                                        ),
                                                        proof["output"][
                                                            "member_id"
                                                        ].astext.is_distinct_from(
                                                            proof["member_id"].astext
                                                        ),
                                                    ),
                                                ),
                                                "source acquisition changes selected member/context",
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            *(Local(name, pg_type("jsonb")) for name in j if name != "source_sets"),
            Local("d", demands),
            Local("boundary", boundaries),
            Local("p", pg_type("jsonb")),
            *(Local(name, pg_type("text")) for name in ("p_use", "p_product", "p_derivation")),
            Local("product_row", products),
            Local("member_row", members),
        ),
        returns="void",
    )
    return selected_output + grouped


def selected_population_native_sql(model):
    """Select an authenticated finite parent under the captured binding and read."""
    (
        obligations,
        demands,
        populations,
        requests,
        episodes,
        boundaries,
        artifacts,
        products,
        kinds,
        member_table,
    ) = (
        model.tables[name]
        for name in (
            "ops.data_obligation",
            "ops.data_demand",
            "ops.data_population",
            "ops.data_request",
            "ops.data_derivation",
            "ops.data_demand_read",
            "sem.artifact",
            "kb.data_product",
            "sem.data_kind_contract",
            "kb.data_product_member",
        )
    )

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def obligation(field):
        return row("obligation", obligations, field)

    def demand(field):
        return row("demand", demands, field)

    def parent(field):
        return row("parent", populations, field)

    def boundary(field):
        return row("boundary", boundaries, field)

    def source_request(field):
        return row("source_request", requests, field)

    def selected(field):
        return row("selected", populations, field)

    j = {
        name: _value(name, JSONB())
        for name in (
            "p",
            "archived",
            "projection",
            "operation",
            "compiled",
            "selection",
            "expression",
            "context",
            "refs",
            "roledef",
            "predicate",
            "universe",
            "row_value",
            "expected",
            "members",
            "evidence",
            "meaning",
            "scope",
            "candidates",
        )
    }
    (
        p,
        archived,
        projection,
        operation,
        compiled,
        selection,
        expression,
        context,
        roledef,
        row_value,
        expected,
    ) = (
        j[name]
        for name in (
            "p",
            "archived",
            "projection",
            "operation",
            "compiled",
            "selection",
            "expression",
            "context",
            "roledef",
            "row_value",
            "expected",
        )
    )
    role, archive_digest, value_key, key, projection_mode = (
        _value(name) for name in ("role", "archive_digest", "value_key", "key", "projection_mode")
    )

    def selected_row(table, condition, target):
        return SelectInto(
            select(core_relation_row(table)).select_from(table).where(condition), (target,), True
        )

    def artifact(name):
        return artifacts.c.release_id == demand("release_id"), artifacts.c.artifact_name == name

    selection_rows = _elements(demand("selection")["operations"], "selected_operation")
    authored_ops = _elements(archived["operations"], "authored_operation")
    compiled_ops = _elements(projection["operations"], "compiled_operation")
    bindings = _elements(archived["bindings"], "authored_binding")
    references = (
        func.jsonb_each_text(j["refs"])
        .table_valued(column("key", Text()), column("value", Text()))
        .render_derived(name="population_reference")
    )
    roles = _elements(compiled["input_roles"], "input_role")
    relations = _elements(demand("selection")["discovery"], "discovery_relation")
    accepted = _texts(roledef["accepted_kind_contracts"], "accepted_kind")
    source_entries = _elements(
        func.coalesce(
            demand("selection")["source_sets"][roledef["support"]["source_set"].astext]["entries"],
            _json("[]"),
        ),
        "source_entry",
    )
    rows = (
        func.ops.data_binding_rows(
            demand("id"),
            p["operation_id"].astext,
            j["scope"],
            boundary("id"),
            p["subject"].astext,
            p["original_source"],
            obligation("analyzed_scope"),
        )
        .table_valued(*binding_columns())
        .alias("binding_row")
    )
    expected_rows = _elements(parent("members"), "expected_member")
    universe_rows = _elements(j["universe"], "population_fact")
    source_sets = func.coalesce(demand("selection")["source_sets"], _json("{}"))
    source_subject = func.ops.ddo_operation_subject(
        source_request("release_id"), source_request("operation_id")
    )
    target_subject = func.ops.ddo_operation_subject(
        demand("release_id"), obligation("operation_id")
    )
    source_address = _object(
        product=parent("evidence")["product_id"].astext,
        member=row_value["member_id"].astext,
        subject=row_value["subject"].astext,
        subject_definition=row_value["subject_definition"].astext,
        original_source=row_value["original_source"].astext,
        analyzed_scope=row_value["analyzed_scope"],
        meaning_body=row_value["body"],
    )
    subject_matches = func.ops.ddo_binding_subject(
        roledef,
        _object(subject=row_value["subject"].astext, meaning_body=row_value["body"]),
        p["subject"].astext,
        obligation("original_source"),
        type_=Boolean(),
    )
    old = populations.alias("old")
    empty_filter = _object(operator="all", children=_json("[]"))
    new_selection = _object(
        parent_population_id=parent("id"),
        read_id=boundary("id"),
        obligation_id=obligation("id"),
        operation_id=p["operation_id"].astext,
        subject=p["subject"].astext,
        subject_definition=target_subject,
        original_source=p["original_source"].astext,
        analyzed_scope=obligation("analyzed_scope"),
        role=role,
        definition=selection["definition"].astext,
        eligibility=selection["eligibility"].astext,
        filter=j["predicate"],
        parameter_meaning=selection["parameter_meaning"],
        choices=selection["choices"],
    )
    steps = (
        Perform(
            func.ops.ddo_fields(
                p, array(["obligation_id", "population_name", "parent_population_id", "read_id"])
            )
        ),
        selected_row(obligations, obligations.c.id == p["obligation_id"].astext, "obligation"),
        Assign(
            "p",
            p.op("||")(
                _object(
                    demand_id=obligation("demand_id"),
                    operation_id=obligation("operation_id"),
                    subject=obligation("subject"),
                    original_source=obligation("original_source"),
                )
            ),
        ),
        selected_row(demands, demands.c.id == p["demand_id"].astext, "demand"),
        selected_row(
            populations,
            and_(
                populations.c.id == p["parent_population_id"].astext,
                populations.c.demand_id == demand("id"),
            ),
            "parent",
        ),
        SelectInto(
            select(core_relation_row(requests))
            .select_from(requests.join(episodes, episodes.c.request_id == requests.c.id))
            .where(episodes.c.id == parent("evidence")["derivation_id"].astext),
            ("source_request",),
            True,
        ),
        selected_row(
            boundaries,
            and_(boundaries.c.id == p["read_id"].astext, boundaries.c.demand_id == demand("id")),
            "boundary",
        ),
        Assign(
            "scope", func.ops.ddo_require_read_current(_value("boundary"), demand("project_id"))
        ),
        Perform(func.ops.ddo_require_active_demand(demand("id"))),
        _check(
            or_(
                ~func.ops.ddo_read_visible(
                    parent("created_at"), parent("created_xid"), _value("boundary"), type_=Boolean()
                ),
                ~func.ops.ddo_node_valid(
                    "population", parent("id"), _value("boundary"), type_=Boolean()
                ),
                source_request("project_id").is_distinct_from(demand("project_id")),
                parent("evidence").bool_op("?")("selection"),
                parent("name") == p["population_name"].astext,
            ),
            "selected population lacks its pinned admitted base parent",
        ),
        Assign("scope", boundary("trust_snapshot")),
        PerformQuery(
            select(func.ops.ddo_authorize(kinds.c.universe))
            .select_from(products.join(kinds, kinds.c.kind_contract == products.c.kind_contract))
            .where(products.c.id == parent("evidence")["product_id"].astext)
        ),
        SelectInto(
            select(selection_rows.c.value).where(
                selection_rows.c.value["operation"].astext == p["operation_id"].astext
            ),
            ("selection",),
            True,
        ),
        SelectInto(
            select(
                cast(func.convert_from(artifacts.c.content, "UTF8"), JSONB()),
                func.encode(func.sha256(artifacts.c.content), "hex"),
            ).where(*artifact("data_operations.json")),
            ("archived", "archive_digest"),
            True,
        ),
        SelectInto(
            select(cast(func.convert_from(artifacts.c.content, "UTF8"), JSONB())).where(
                *artifact("data_operation_native_definitions.json")
            ),
            ("projection",),
            True,
        ),
        _check(
            projection["model_digest"].astext.is_distinct_from(archive_digest),
            "population source model differs",
        ),
        SelectInto(
            select(authored_ops.c.value).where(
                authored_ops.c.value["semantic_id"].astext == p["operation_id"].astext
            ),
            ("operation",),
            True,
        ),
        SelectInto(
            select(compiled_ops.c.value).where(
                compiled_ops.c.value["operation_id"].astext == p["operation_id"].astext
            ),
            ("compiled",),
            True,
        ),
        SelectInto(
            select(bindings.c.value["expression"]).where(
                bindings.c.value["semantic_id"].astext == operation["binding"].astext
            ),
            ("expression",),
            True,
        ),
        _check(
            or_(
                compiled["binding"].is_distinct_from(expression),
                compiled["definition"].astext.is_distinct_from(selection["definition"].astext),
                compiled["eligibility"].astext.is_distinct_from(selection["eligibility"].astext),
            ),
            "population filter differs from frozen definition",
        ),
        Assign(
            "context",
            _object(
                model=archived,
                roledefs=compiled["input_roles"],
                parameters=selection["parameters"],
                parameter_meaning=selection["parameter_meaning"],
                parameterdefs=operation["parameters"]["json"],
                choices=selection["choices"],
                subject=p["subject"].astext,
                original_source=p["original_source"].astext,
                roles=_json("{}"),
                populations=_json("{}"),
                witnesses=_json("{}"),
            ),
        ),
        Assign("refs", func.ops.ddo_binding_population_refs(expression, context)),
        SelectInto(
            select(func.count(), func.min(references.c.key)).where(
                references.c.value == p["population_name"].astext
            ),
            ("count_roles", "role"),
        ),
        _check(
            _value("count_roles", Integer()) != 1,
            "selected population name must identify one frozen active role",
        ),
        SelectInto(
            select(roles.c.value).where(roles.c.value["name"].astext == role), ("roledef",), True
        ),
        Assign(
            "projection_mode",
            func.coalesce(
                func.ops.ddo_binding_population_projection(expression, context, role), "member"
            ),
        ),
        Assign("predicate", func.ops.ddo_population_filter(expression, role, selection["choices"])),
        _check(
            or_(
                ~(
                    source_request("operation_id")
                    == any_(
                        func.ops.ddo_consumed_producers(
                            demand("selection"), p["operation_id"].astext
                        )
                    )
                ),
                ~select(relations.c.value)
                .where(
                    relations.c.value["population"].astext == parent("name"),
                    relations.c.value["producer"].astext == source_request("operation_id"),
                    relations.c.value["output_role"].astext
                    == parent("evidence")["member_role"].astext,
                )
                .exists(),
            ),
            "selected parent is not a declared prerequisite discovery population",
        ),
        _check(
            and_(
                projection_mode != "qualified-context",
                ~select(products.c.id)
                .select_from(
                    products.join(kinds, kinds.c.kind_contract == products.c.kind_contract)
                )
                .where(
                    products.c.id == parent("evidence")["product_id"].astext,
                    select(accepted.c.value)
                    .where(kinds.c.member_contracts.bool_op("?")(accepted.c.value))
                    .correlate(kinds)
                    .exists(),
                )
                .exists(),
            ),
            "selected parent does not declare the role member kind",
        ),
        _check(
            and_(
                tuple_(
                    source_request("subject"),
                    source_subject,
                    source_request("original_source"),
                    source_request("analyzed_scope"),
                ).is_distinct_from(
                    tuple_(
                        obligation("subject"),
                        target_subject,
                        obligation("original_source"),
                        obligation("analyzed_scope"),
                    )
                ),
                ~select(source_entries.c.value)
                .where(
                    source_entries.c.value["project_id"].astext == demand("project_id"),
                    source_entries.c.value["original_source"].astext.is_not_distinct_from(
                        source_request("original_source")
                    ),
                    source_entries.c.value["product"].astext
                    == parent("evidence")["product_id"].astext,
                )
                .exists(),
            ),
            "selected parent source is outside the role frozen source set",
        ),
        PerformQuery(
            select(func.ops.ddo_authorize(kinds.c.universe)).where(
                kinds.c.kind_contract == roledef["kind_contract"].astext
            )
        ),
        SelectInto(
            select(
                func.coalesce(func.jsonb_agg(func.to_jsonb(rows.table_valued())), _json("[]"))
            ).where(
                rows.c.product == parent("evidence")["product_id"].astext,
                roledef["accepted_kind_contracts"].bool_op("?")(rows.c.kind_contract),
                rows.c.support_episodes.bool_op("?")(parent("evidence")["derivation_id"].astext),
                rows.c.support_evidence["use_id"].astext
                == parent("evidence")["admission_use_id"].astext,
                rows.c.support_evidence["producer_output"]["role"].astext
                == parent("evidence")["member_role"].astext,
            ),
            ("universe",),
        ),
        If(
            projection_mode == "qualified-context",
            (
                _check(
                    j["predicate"] != empty_filter,
                    "qualified-context closure cannot apply derived body filters to discovery members",
                ),
                Assign("members", parent("members")),
            ),
            (
                ForQuery(
                    ("expected",),
                    select(expected_rows.c.value),
                    (
                        SelectInto(
                            select(func.to_jsonb(member_table.table_valued())).where(
                                member_table.c.product_id
                                == parent("evidence")["product_id"].astext,
                                member_table.c.member_id == expected["member_id"].astext,
                                roledef["accepted_kind_contracts"].bool_op("?")(
                                    member_table.c.kind_contract
                                ),
                            ),
                            ("row_value",),
                        ),
                        If(row_value.is_(None), (Continue(),)),
                        If(
                            ~func.coalesce(
                                func.ops.ddo_binding_source_address(
                                    roledef,
                                    source_address,
                                    obligation("original_source"),
                                    source_sets,
                                    type_=Boolean(),
                                ),
                                False,
                            ),
                            (Continue(),),
                        ),
                        _check(
                            subject_matches.is_(None), "population subject relationship is unknown"
                        ),
                        If(~subject_matches, (Continue(),)),
                        SelectInto(
                            select(
                                func.coalesce(func.jsonb_agg(universe_rows.c.value), _json("[]"))
                            ).where(
                                universe_rows.c.value["member"].astext
                                == expected["member_id"].astext,
                                func.ops.ddo_binding_source(
                                    roledef,
                                    universe_rows.c.value,
                                    obligation("original_source"),
                                    source_sets,
                                    type_=Boolean(),
                                ),
                            ),
                            ("candidates",),
                        ),
                        _check(
                            func.jsonb_array_length(j["candidates"]) > 1,
                            "parent population member has ambiguous producing occurrences",
                        ),
                        _check(
                            func.jsonb_array_length(j["candidates"]) == 0,
                            "parent population member facts unavailable in pinned read",
                        ),
                        Assign("row_value", j["candidates"][0]),
                        If(
                            func.ops.ddo_binding_test(
                                j["predicate"],
                                func.jsonb_set(
                                    context,
                                    array(["roles", role]),
                                    func.jsonb_build_array(row_value),
                                ),
                                type_=Boolean(),
                            ),
                            (
                                Assign(
                                    "members",
                                    j["members"].op("||")(func.jsonb_build_array(expected)),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        Assign(
            "meaning",
            _object(
                parent=parent("semantic_key"),
                operation=p["operation_id"].astext,
                kind_contract=roledef["kind_contract"].astext,
                role=role,
                subject=p["subject"].astext,
                subject_definition=target_subject,
                original_source=p["original_source"].astext,
                analyzed_scope=obligation("analyzed_scope"),
                filter=j["predicate"],
                parameters=selection["parameter_meaning"],
                members=j["members"],
                complete=parent("complete"),
            ),
        ),
        If(
            projection_mode == "qualified-context",
            (Assign("meaning", j["meaning"].op("||")(_object(projection=projection_mode))),),
        ),
        Assign("value_key", literal("population-value:") + func.ops.ddo_digest(j["meaning"])),
        SelectInto(
            select(core_relation_row(old))
            .select_from(old)
            .where(
                old.c.demand_id == demand("id"),
                old.c.name == p["population_name"].astext,
                old.c.selected_obligation_id == obligation("id"),
                old.c.semantic_key == value_key,
                old.c.evidence["selection"]["parent_population_id"].astext == parent("id"),
                func.ops.ddo_node_valid("population", old.c.id, type_=Boolean()),
            )
            .order_by(old.c.created_at.desc(), old.c.id.desc())
            .limit(1),
            ("selected",),
        ),
        If(
            selected("id").is_(None),
            (
                Assign(
                    "evidence",
                    parent("evidence")
                    .op("-")("population_id")
                    .op("||")(
                        _object(
                            producer_context=func.ops.ddo_population_producer_context(
                                _value("parent")
                            ),
                            selection=new_selection,
                        )
                    ),
                ),
                Assign(
                    "key",
                    literal("population:")
                    + func.ops.ddo_digest(
                        func.jsonb_build_array(
                            demand("id"), p["population_name"].astext, value_key, j["evidence"]
                        )
                    ),
                ),
                Assign("evidence", j["evidence"].op("||")(_object(population_id=key))),
                Sql(
                    insert(populations)
                    .values(
                        id=key,
                        demand_id=demand("id"),
                        selected_obligation_id=obligation("id"),
                        semantic_key=value_key,
                        name=p["population_name"].astext,
                        context_key=func.ops.ddo_digest(
                            func.ops.ddo_population_evidence_scope(j["evidence"])
                        ),
                        members=j["members"],
                        complete=parent("complete"),
                        evidence=j["evidence"],
                        created_at=func.clock_timestamp(),
                        created_xid=cast(func.pg_current_xact_id(), Text()),
                    )
                    .on_conflict_do_nothing()
                ),
                selected_row(populations, populations.c.id == key, "selected"),
            ),
        ),
        Return(
            _object(
                payload=_object(
                    inserted_obligations=0,
                    population_id=selected("id"),
                    name=selected("name"),
                    semantic_key=selected("semantic_key"),
                    members=selected("members"),
                    complete=selected("complete"),
                    evidence=selected("evidence"),
                )
            )
        ),
    )
    locals_ = (
        *(
            Local(name, table)
            for name, table in (
                ("obligation", obligations),
                ("demand", demands),
                ("parent", populations),
                ("boundary", boundaries),
                ("selected", populations),
                ("source_request", requests),
            )
        ),
        *(
            Local(
                name,
                pg_type("jsonb"),
                _value("p_payload", JSONB())
                if name == "p"
                else _json("[]")
                if name == "members"
                else None,
            )
            for name in j
        ),
        *(
            Local(name, pg_type("text"))
            for name in ("role", "archive_digest", "value_key", "key", "projection_mode")
        ),
        Local("count_roles", pg_type("integer")),
    )
    return _procedure("select_data_population", (("p_payload", "jsonb"),), steps, locals_)


def population_acquisition_native_sql(model):
    return (
        population_filter_native_sql()
        + source_acquisition_native_sql(model)
        + selected_population_native_sql(model)
    )
