"""Compile authenticated binding admission over captured model and native facts."""

from typing import get_args, get_type_hints

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
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
)
from sqlalchemy.dialects.postgresql import JSONB, array

from .binding_recursive_native import (
    _binding_declarations,
    _check,
    _elements,
    _json,
    _render_binding_programs,
    _texts,
    _value,
    pg_type_array,
)
from .data_operation_model import BindingExpression
from .data_operation_projections import binding_columns
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    SelectInto,
    Statement,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program import literal as pg_literal
from .native_program_registry import ProgramDeclaration


def _binding_admission_native_routine(model):
    demands, requests, definitions, releases, boundaries, populations, derivations = (
        model.tables[name]
        for name in (
            "ops.data_demand",
            "ops.data_request",
            "sem.data_operation_definition",
            "sem.data_operation_release",
            "ops.data_demand_read",
            "ops.data_population",
            "ops.data_derivation",
        )
    )

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def demand(field):
        return row("demand", demands, field)

    def request(field):
        return row("request", requests, field)

    def population(field):
        return row("native_population", populations, field)

    p_demand, p_operation, p_subject = (
        _value(name) for name in ("p_demand", "p_operation", "p_subject")
    )
    p_meaning, p_binding, p_trust = (
        _value(name, JSONB()) for name in ("p_request_meaning", "p_binding", "p_trust")
    )
    p_read_checked = _value("p_read_checked", Boolean())
    local_names = (
        "binding_model",
        "operation",
        "compiled",
        "selection",
        "expression",
        "population_refs",
        "roles",
        "universe",
        "populations",
        "witnesses",
        "semantic_witnesses",
        "states",
        "context",
        "item",
        "roledef",
        "row_value",
        "chosen",
        "values",
        "raw",
        "role_meaning",
        "witness",
        "seen",
        "expected",
        "discovery_refs",
    )
    local = {name: _value(name, JSONB()) for name in local_names}
    binding_model, operation, compiled, selection, expression = (
        local[name]
        for name in ("binding_model", "operation", "compiled", "selection", "expression")
    )
    roledef, item, chosen, values, row_value = (
        local[name] for name in ("roledef", "item", "chosen", "values", "row_value")
    )
    role, state, projection_mode = (_value(name) for name in ("role", "state", "projection_mode"))
    count_selected, multiplicity, ordinal = (
        _value(name, BigInteger()) for name in ("count_selected", "multiplicity", "ordinal")
    )
    inactive = _value("inactive", ARRAY(Text()))
    selected_operations = _elements(demand("selection")["operations"], "selected_operation")
    roles = _elements(compiled["input_roles"], "compiled_role")
    input_items = _elements(p_binding["inputs"], "selected_input")
    native_values = _elements(local["universe"], "native_value")
    value = native_values.c.value
    supports = (
        func.ops.ddo_input_support_refs(p_binding, item)
        .table_valued(column("value", JSONB()))
        .render_derived(name="exact_support")
    )
    row_values = _elements(values, "selected_value")
    references = _elements(
        func.coalesce(row_value["support_references"], _json("[]")), "support_reference"
    )
    dimensions = _texts(roledef["identity_requirements"], "required_identity")
    population_refs = _elements(p_binding["populations"], "population_reference")
    selected_population = population_refs.c.value
    discovery = _elements(demand("selection")["discovery"], "discovery_relation")
    explicit = (
        func.jsonb_each_text(local["discovery_refs"])
        .table_valued(column("key", Text()), column("value", Text()))
        .render_derived(name="discovery_reference")
    )
    source_sets = func.coalesce(demand("selection")["source_sets"], _json("{}"))
    nodes = select(expression.label("n")).cte("nodes", recursive=True)
    descendants = _elements(
        func.coalesce(nodes.c.n["children"], _json("[]")), "descendant"
    ).lateral("descendant")
    nodes = nodes.union_all(
        select(descendants.c.value).select_from(nodes.join(descendants, literal(True)))
    )
    binding_rows = (
        func.ops.ddo_binding_rows(
            p_demand,
            p_operation,
            p_trust,
            p_binding["read_id"].astext,
            p_subject,
            func.coalesce(func.to_jsonb(request("original_source")), _json("null")),
            request("analyzed_scope"),
            False,
            case(
                (
                    select(nodes.c.n)
                    .where(
                        nodes.c.n["operator"].astext.in_(
                            ("forall", "absent", "membership", "covers")
                        )
                    )
                    .exists(),
                    null(),
                ),
                else_=p_binding["inputs"],
            ),
            p_read_checked,
        )
        .table_valued(*binding_columns())
        .alias("native_binding_row")
    )

    def check(condition, message, code="P0001"):
        return _check(condition, message, code)

    def selected_row(relation, condition, target):
        return SelectInto(
            select(core_relation_row(relation)).select_from(relation).where(condition),
            (target,),
            True,
        )

    steps: list[Statement] = [
        selected_row(demands, demands.c.id == p_demand, "demand"),
        selected_row(
            requests,
            requests.c.request_key == func.data.ddo_identity("semantic-request", p_meaning),
            "request",
        ),
        check(
            or_(
                request("operation_id") != p_operation,
                request("subject") != p_subject,
                request("project_id") != demand("project_id"),
                ~select(definitions.c.operation_id)
                .where(
                    definitions.c.release_id == demand("release_id"),
                    definitions.c.operation_id == p_operation,
                    definitions.c.recipe == request("recipe"),
                )
                .exists(),
            ),
            "native binding request custody differs",
        ),
        SelectInto(
            select(func.to_jsonb(definitions.table_valued())).where(
                definitions.c.release_id == demand("release_id"),
                definitions.c.operation_id == p_operation,
            ),
            ("compiled",),
            True,
        ),
        SelectInto(
            select(func.jsonb_build_object("kinds", releases.c.binding_types)).where(
                releases.c.release_id == demand("release_id"),
            ),
            ("binding_model",),
            True,
        ),
        Assign("expression", compiled["binding_expression"]),
        Assign(
            "operation",
            func.jsonb_build_object(
                "parameters", func.jsonb_build_object("json", compiled["parameter_definitions"])
            ),
        ),
        check(
            select(nodes.c.n)
            .where(
                or_(
                    nodes.c.n["operator"].astext.is_(None),
                    ~nodes.c.n["operator"].astext.in_(
                        get_args(get_type_hints(BindingExpression)["operator"])
                    ),
                )
            )
            .exists(),
            "authenticated native binding is outside the closed operator vocabulary",
        ),
        SelectInto(
            select(selected_operations.c.value).where(
                selected_operations.c.value["operation"].astext == p_operation
            ),
            ("selection",),
            True,
        ),
        Perform(func.ops.ddo_validate_parameters(operation, selection, binding_model)),
        check(
            or_(
                compiled["definition_identity"].astext.is_distinct_from(
                    selection["definition"].astext
                ),
                compiled["eligibility_identity"].astext.is_distinct_from(
                    selection["eligibility"].astext
                ),
            ),
            "binding differs from authenticated frozen definition",
        ),
        check(
            func.jsonb_array_length(compiled["input_roles"])
            != select(func.count(roles.c.value["name"].astext.distinct())).scalar_subquery(),
            "admitted input role inventory repeats a role",
        ),
        check(
            func.nullif(p_binding["read_id"].astext, "").is_(None),
            "native binding requires its authenticated read receipt",
            "23514",
        ),
        selected_row(
            boundaries,
            and_(
                boundaries.c.id == p_binding["read_id"].astext,
                boundaries.c.demand_id == demand("id"),
            ),
            "boundary",
        ),
        SelectInto(
            select(
                func.coalesce(
                    func.jsonb_agg(func.to_jsonb(binding_rows.table_valued())), _json("[]")
                )
            ),
            ("universe",),
        ),
        Assign("raw", func.data.ddo_json(p_binding["request_inputs"])),
    ]
    valid_row = and_(
        value["product"].astext == item["product_id"].astext,
        value["member"].astext.is_not_distinct_from(item["member_id"].astext),
        roledef["accepted_kind_contracts"].bool_op("?")(value["kind_contract"].astext),
        func.ops.ddo_binding_subject(
            roledef, value, p_subject, request("original_source"), type_=Boolean()
        ),
        func.ops.ddo_binding_source(
            roledef, value, request("original_source"), source_sets, type_=Boolean()
        ),
        value["position"].astext.is_not_distinct_from(item["position"].astext),
        value["multiplicity"].astext == item["multiplicity"].astext,
        value["support_evidence"]["producer_output"].is_not_distinct_from(
            func.nullif(item["producer_output"], _json("null"))
        ),
        func.coalesce(value["support_episodes"], _json("[]")) == item["support_derivation_ids"],
        select(supports.c.value)
        .where(func.ops.ddo_support_reference_matches(supports.c.value, value, type_=Boolean()))
        .correlate(native_values)
        .exists(),
    )
    steps.append(
        ForQuery(
            ("roledef",),
            select(roles.c.value),
            (
                Assign("role", roledef["name"].astext),
                Assign("values", _json("[]")),
                ForQuery(
                    ("item",),
                    select(input_items.c.value).where(input_items.c.value["role"].astext == role),
                    (
                        Perform(func.ops.ddo_input_support_selection(item)),
                        SelectInto(select(value).where(valid_row).limit(1), ("chosen",)),
                        check(
                            chosen.is_(None),
                            "selected input support set has no exact native binding row",
                            "23514",
                        ),
                        Assign("values", values.op("||")(func.jsonb_build_array(chosen))),
                    ),
                ),
                Assign("roles", func.jsonb_set(local["roles"], array([role]), values)),
                Assign("role_meaning", func.data.ddo_field(p_binding["request_inputs"], role)),
                Assign(
                    "state",
                    func.data.ddo_field(local["role_meaning"], "value", type_=JSONB())[0].astext,
                ),
                Assign(
                    "states", func.jsonb_set(local["states"], array([role]), func.to_jsonb(state))
                ),
                Assign("witness", local["raw"][role]["population_witness"]),
                If(
                    local["witness"].is_not(None) & (local["witness"] != _json("null")),
                    (
                        Assign(
                            "semantic_witnesses",
                            func.jsonb_set(
                                local["semantic_witnesses"], array([role]), local["witness"]
                            ),
                        ),
                    ),
                ),
                SelectInto(
                    select(
                        func.coalesce(
                            func.sum(cast(row_values.c.value["multiplicity"].astext, BigInteger())),
                            0,
                        )
                    ),
                    ("count_selected",),
                ),
                check(
                    (state == "present")
                    & or_(
                        count_selected < cast(roledef["minimum"].astext, BigInteger()),
                        roledef["maximum"].astext.is_not(None)
                        & (count_selected > cast(roledef["maximum"].astext, BigInteger())),
                    ),
                    "native binding role cardinality differs",
                    "23514",
                ),
                Assign("seen", _json("[]")),
                ForQuery(
                    ("row_value",),
                    select(row_values.c.value),
                    (
                        check(
                            select(references.c.value)
                            .where(
                                ~func.coalesce(
                                    roledef["support"]["origins"], _json('["computation"]')
                                ).bool_op("?")(references.c.value["kind"].astext)
                            )
                            .exists(),
                            "selected support origin is outside declared eligibility",
                            "23514",
                        ),
                        Assign(
                            "multiplicity", cast(row_value["multiplicity"].astext, BigInteger())
                        ),
                        Assign("ordinal", cast(row_value["position"].astext, BigInteger())),
                        check(
                            or_(
                                multiplicity.is_(None),
                                multiplicity < 1,
                                ordinal < 0,
                                (roledef["collection"].astext != "bag") & (multiplicity != 1),
                            ),
                            "native binding multiplicity or ordinal differs",
                            "23514",
                        ),
                        If(
                            roledef["collection"].astext == "sequence",
                            (
                                check(
                                    or_(
                                        ordinal.is_(None),
                                        local["seen"].bool_op("@>")(
                                            func.jsonb_build_array(ordinal)
                                        ),
                                    ),
                                    "native sequence has missing or repeated ordinal",
                                    "23514",
                                ),
                                Assign(
                                    "seen", local["seen"].op("||")(func.jsonb_build_array(ordinal))
                                ),
                            ),
                        ),
                        check(
                            select(dimensions.c.value)
                            .where(
                                dimensions.c.value.in_(("provider", "alternative")),
                                func.nullif(
                                    row_value[dimensions.c.value + "_identity"].astext, ""
                                ).is_(None),
                            )
                            .exists(),
                            "required native support identity is unavailable",
                            "23514",
                        ),
                    ),
                ),
            ),
        )
    )
    steps.append(
        check(
            select(literal(1))
            .select_from(population_refs)
            .group_by(selected_population["name"].astext)
            .having(func.count(selected_population["population_id"].astext.distinct()) != 1)
            .exists(),
            "one named population cannot select conflicting receipt scopes",
            "23514",
        )
    )
    producer = derivations.alias("producer")
    produced = requests.alias("produced")
    current_population = populations.alias("pop")
    pop = current_population.c
    population_evidence = pop.evidence
    original_episode = (
        select(producer.c.id)
        .select_from(producer.join(produced, produced.c.id == producer.c.request_id))
        .where(
            producer.c.id == population_evidence["derivation_id"].astext,
            produced.c.subject == p_subject,
            produced.c.original_source.is_not_distinct_from(request("original_source")),
            produced.c.analyzed_scope == request("analyzed_scope"),
        )
        .exists()
    )
    # A composite call takes the relation row itself, without expanding its fields.
    from pglast import ast
    from pglast.stream import RawStream
    from sqlalchemy import literal_column

    pop_row = literal_column(RawStream()(ast.ColumnRef(fields=(ast.String(sval="pop"),))))
    discovery_valid = (
        select(selected_population)
        .where(
            selected_population["population_id"].astext == pop.id,
            func.ops.ddo_discovery_role_population(
                core_variable("demand", JSONB()),
                pop_row,
                p_operation,
                selected_population["role"].astext,
                p_subject,
                request("original_source"),
                request("analyzed_scope"),
                core_variable("boundary", JSONB()),
                type_=Boolean(),
            ),
        )
        .correlate(current_population)
        .exists()
    )
    steps.append(
        ForQuery(
            ("native_population",),
            select(core_relation_row(current_population))
            .select_from(current_population)
            .where(
                pop.demand_id == p_demand,
                func.ops.ddo_node_valid("population", pop.id, type_=Boolean()),
                select(selected_population)
                .where(
                    selected_population["population_id"].astext == pop.id,
                    selected_population["name"].astext == pop.name,
                )
                .correlate(current_population)
                .exists(),
                or_(
                    discovery_valid,
                    ~population_evidence.bool_op("?")("selection") & original_episode,
                    and_(
                        population_evidence["selection"]["subject"].astext == p_subject,
                        population_evidence["selection"][
                            "original_source"
                        ].astext.is_not_distinct_from(request("original_source")),
                        population_evidence["selection"]["operation_id"].astext == p_operation,
                        population_evidence["selection"]["analyzed_scope"]
                        == request("analyzed_scope"),
                    ),
                ),
            ),
            (
                SelectInto(
                    select(
                        func.coalesce(
                            func.ops.ddo_binding_population_projection(
                                expression,
                                func.jsonb_build_object("choices", selection["choices"]),
                                selected_population["role"].astext,
                            ),
                            "member",
                        )
                    )
                    .where(selected_population["population_id"].astext == population("id"))
                    .limit(1),
                    ("projection_mode",),
                ),
                Assign(
                    "populations",
                    func.jsonb_set(
                        local["populations"],
                        array([population("name")]),
                        func.ops.ddo_project_population(
                            population("semantic_key"),
                            population("complete"),
                            population("members"),
                            population("evidence"),
                            demand("project_id"),
                            projection_mode,
                        ),
                    ),
                ),
            ),
        )
    )
    context_fields = {
        "project_id": demand("project_id"),
        "model": binding_model,
        "roledefs": compiled["input_roles"],
        "roles": local["roles"],
        "states": local["states"],
        "witnesses": local["witnesses"],
        "universe": local["universe"],
        "populations": local["populations"],
        "source_sets": source_sets,
        "parameters": selection["parameters"],
        "parameter_meaning": selection["parameter_meaning"],
        "parameterdefs": operation["parameters"]["json"],
        "choices": selection["choices"],
        "subject": p_subject,
        "original_source": request("original_source"),
    }
    steps.extend(
        (
            Assign(
                "context",
                func.jsonb_build_object(
                    *(entry for name, value in context_fields.items() for entry in (name, value))
                ),
            ),
            Assign("inactive", func.ops.ddo_binding_inactive(expression, local["context"])),
            Assign(
                "population_refs",
                func.ops.ddo_binding_population_refs(expression, local["context"]),
            ),
            SelectInto(
                select(
                    func.coalesce(
                        func.jsonb_object_agg(
                            discovery.c.value["target_role"].astext,
                            discovery.c.value["population"].astext,
                        ),
                        _json("{}"),
                    )
                ).where(
                    discovery.c.value["target"].astext == p_operation,
                    discovery.c.value.bool_op("?")("target_role"),
                ),
                ("discovery_refs",),
            ),
            check(
                select(explicit.c.key)
                .where(
                    local["population_refs"].bool_op("?")(explicit.c.key),
                    local["population_refs"][explicit.c.key].astext.is_distinct_from(
                        explicit.c.value
                    ),
                )
                .exists(),
                "discovery input conflicts with authored population scope",
                "23514",
            ),
            Assign("population_refs", local["population_refs"].op("||")(local["discovery_refs"])),
            ForQuery(
                ("item",),
                select(selected_population),
                (
                    Assign("role", item["role"].astext),
                    SelectInto(
                        select(roles.c.value).where(roles.c.value["name"].astext == role),
                        ("roledef",),
                        True,
                    ),
                    check(
                        local["witnesses"].bool_op("?")(role),
                        "one role cannot carry two population receipt scopes",
                        "23514",
                    ),
                    Assign("witness", local["populations"][item["name"].astext]),
                    check(
                        or_(
                            local["witness"].is_(None),
                            local["witness"]["evidence"]["population_id"].astext.is_distinct_from(
                                item["population_id"].astext
                            ),
                            item["name"].astext.is_distinct_from(
                                func.coalesce(local["population_refs"][role].astext, role)
                            ),
                        ),
                        "population receipt differs from exact current named closure",
                        "23514",
                    ),
                    Assign(
                        "expected",
                        case(
                            (
                                or_(
                                    local["states"][role].astext == "known-absent",
                                    func.ops.ddo_binding_population_refs(
                                        expression, local["context"]
                                    ).bool_op("?")(role),
                                ),
                                func.ops.ddo_binding_population_meaning(
                                    local["witness"],
                                    roledef["identity_requirements"].bool_op("?")("episode"),
                                ),
                            ),
                            else_=null(),
                        ),
                    ),
                    check(
                        local["semantic_witnesses"][role].is_distinct_from(local["expected"]),
                        "semantic population witness differs from native closure meaning",
                        "23514",
                    ),
                    Assign(
                        "witnesses",
                        func.jsonb_set(local["witnesses"], array([role]), local["witness"]),
                    ),
                ),
            ),
            ForQuery(
                ("roledef",),
                select(roles.c.value),
                (
                    Assign("role", roledef["name"].astext),
                    Assign("witness", local["semantic_witnesses"][role]),
                    If(
                        role == any_(inactive),
                        (
                            check(
                                or_(
                                    func.jsonb_array_length(local["roles"][role]) != 0,
                                    roledef["presence"].astext == "required",
                                    local["witness"]["reason"].astext.is_distinct_from(
                                        "unselected-declared-branch"
                                    ),
                                    local["witness"]["selection"].is_distinct_from(
                                        selection["choices"]
                                    ),
                                    local["witness"]["complete"].astext.is_distinct_from("true"),
                                ),
                                "unselected branch is not authenticated by frozen demand",
                                "23514",
                            ),
                            Assign(
                                "witnesses",
                                func.jsonb_set(local["witnesses"], array([role]), local["witness"]),
                            ),
                        ),
                        (
                            check(
                                local["witness"].is_not(None)
                                & ~local["witnesses"].bool_op("?")(role),
                                "population meaning lacks exact native receipt locator",
                                "23514",
                            ),
                        ),
                    ),
                ),
            ),
            Assign(
                "context",
                func.jsonb_set(local["context"], array(["witnesses"]), local["witnesses"]),
            ),
            check(
                ~func.ops.ddo_binding_test(expression, local["context"], type_=Boolean()),
                "selected native input bundles violate frozen binding",
                "23514",
            ),
        )
    )
    return NativeRoutine(
        "ops",
        "ddo_require_binding",
        parameters=(
            Parameter("p_demand", column_type(demands.c.id)),
            Parameter("p_operation", column_type(definitions.c.operation_id)),
            Parameter("p_subject", column_type(requests.c.subject)),
            Parameter("p_request_meaning", pg_type("jsonb")),
            Parameter("p_binding", pg_type("jsonb")),
            Parameter("p_trust", pg_type("jsonb")),
            Parameter("p_read_checked", pg_type("bool"), pg_literal(False)),
        ),
        returns=pg_type("void"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            tuple(steps),
            (
                Local("demand", demands),
                Local("request", requests),
                Local("native_population", populations),
                Local("boundary", boundaries),
                *(
                    Local(
                        name,
                        pg_type("jsonb"),
                        _json("{}")
                        if name
                        in {"roles", "populations", "witnesses", "semantic_witnesses", "states"}
                        else None,
                    )
                    for name in local_names
                ),
                *(Local(name, pg_type("text")) for name in ("role", "state", "projection_mode")),
                Local("inactive", pg_type_array()),
                *(
                    Local(name, pg_type("bigint"))
                    for name in ("count_selected", "multiplicity", "ordinal")
                ),
            ),
        ),
    )


def binding_admission_native_programs(model) -> tuple[ProgramDeclaration, ...]:
    return _binding_declarations((_binding_admission_native_routine(model),))


def binding_admission_native_sql(model) -> str:
    """Render this provider's captured statements from typed declarations."""
    return _render_binding_programs(binding_admission_native_programs(model), separator="")
