"""Compile exact request attachment, native binding validation and generation custody."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    null,
    or_,
    select,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array, insert
from sqlalchemy.sql.elements import Grouping

from .binding_recursive_native import _check, _each, _elements, _json, _value
from .native_program import (
    Assign,
    Block,
    CatchCheckViolation,
    Continue,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    PerformQuery,
    Raise,
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


def _selected(table, condition, target, *, strict=True, lock=False):
    query = select(core_relation_row(table)).select_from(table).where(condition)
    return SelectInto(query.with_for_update() if lock else query, (target,), strict)


def _procedure(name, parameters, steps, locals_=(), *, returns="jsonb", volatility=None):
    return (
        function(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type(returns),
            body=Block(tuple(steps), tuple(locals_)),
            volatility=volatility,
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )
        + ";\n"
    )


def binding_validation_native_sql(model):
    (
        demands,
        boundaries,
        definitions,
        populations,
        products,
        members,
        kinds,
        coverage,
        episodes,
        requests,
        outputs,
    ) = (
        model.tables[name]
        for name in (
            "ops.data_demand",
            "ops.data_demand_read",
            "sem.data_operation_definition",
            "ops.data_population",
            "kb.data_product",
            "kb.data_product_member",
            "sem.data_kind_contract",
            "kb.data_member_coverage",
            "ops.data_derivation",
            "ops.data_request",
            "ops.data_derivation_output",
        )
    )
    request_table, obligation_table = requests, model.tables["ops.data_obligation"]

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def r(field):
        return row("r", request_table, field)

    def o(field):
        return row("o", obligation_table, field)

    def d(field):
        return row("d", demands, field)

    def defn(field):
        return row("def", definitions, field)

    def pop(field):
        return row("pop", populations, field)

    def x(field):
        return row("x", products, field)

    def m(field):
        return row("native_member", members, field)

    (
        b,
        raw,
        roledef,
        rv,
        mv,
        item,
        expected,
        witness,
        role_meaning,
        population_reference,
        frozen_binding,
    ) = (
        _value(name, JSONB())
        for name in (
            "b",
            "raw",
            "roledef",
            "rv",
            "mv",
            "item",
            "expected",
            "witness",
            "role_meaning",
            "population_reference",
            "frozen_binding",
        )
    )
    replicate, state, lexical_alternative = (
        _value(name) for name in ("replicate", "state", "lexical_alternative")
    )
    selected_operations = _elements(d("selection")["operations"], "frozen_operation")
    roles = _elements(defn("input_roles"), "input_role")
    named_sources = _each(func.coalesce(d("selection")["source_sets"], _json("{}")), "named_source")
    names = (
        func.jsonb_object_keys(raw)
        .table_valued(column("name", Text()))
        .render_derived(name="role_name")
    )
    refs = _elements(b["populations"], "population_ref")
    supports = _elements(b["support"], "binding_support")
    discovery = _elements(d("selection")["discovery"], "discovery_relation")
    inputs = _elements(b["inputs"], "manifest_input")
    role_members = _elements(rv["value"], "semantic_member")
    population_members = _elements(pop("members"), "population_member")
    support_refs = (
        func.ops.ddo_input_support_refs(b, item)
        .table_valued(column("value", JSONB()))
        .render_derived(name="selected_reference")
    )
    discovery_support = (
        func.ops.ddo_input_support_refs(b, inputs.c.value)
        .table_valued(column("value", JSONB()))
        .render_derived(name="discovery_support")
    )
    wanted_role = roledef["name"].astext
    identity = roledef["identity_requirements"]
    episode_required = identity.bool_op("?")("episode")
    sequence = roledef["collection"].astext == "sequence"
    selected_choices = (
        select(selected_operations.c.value["choices"])
        .where(selected_operations.c.value["operation"].astext == o("operation_id"))
        .scalar_subquery()
    )
    projected_population = func.ops.ddo_project_population(
        pop("semantic_key"),
        pop("complete"),
        pop("members"),
        pop("evidence"),
        d("project_id"),
        func.coalesce(
            func.ops.ddo_binding_population_projection(
                frozen_binding, _object(choices=selected_choices), wanted_role
            ),
            "member",
        ),
    )
    witness_steps = (
        _check(
            population_reference.is_(None),
            "population witness lacks authenticated native receipt reference",
            "23514",
        ),
        _selected(
            populations,
            and_(
                populations.c.id == population_reference["population_id"].astext,
                populations.c.demand_id == d("id"),
                populations.c.name == population_reference["name"].astext,
            ),
            "pop",
        ),
        _check(
            ~func.ops.ddo_node_valid("population", pop("id"), type_=Boolean()),
            "population witness is historical or revoked",
            "23514",
        ),
        _check(
            and_(
                pop("evidence").bool_op("?")("selection"),
                tuple_(
                    *(
                        pop("evidence")["selection"][name].astext
                        for name in (
                            "obligation_id",
                            "operation_id",
                            "subject",
                            "subject_definition",
                            "original_source",
                        )
                    )
                ).is_distinct_from(
                    tuple_(
                        o("id"),
                        o("operation_id"),
                        o("subject"),
                        func.ops.ddo_operation_subject(d("release_id"), o("operation_id")),
                        o("original_source"),
                    )
                ),
            ),
            "selected population belongs to another binding context",
            "23514",
        ),
        Perform(func.ops.ddo_require_release_facts(d("release_id"))),
        SelectInto(
            select(definitions.c.binding_expression).where(
                definitions.c.release_id == d("release_id"),
                definitions.c.operation_id == o("operation_id"),
            ),
            ("frozen_binding",),
            True,
        ),
        Assign(
            "expected",
            func.ops.ddo_binding_population_meaning(projected_population, episode_required),
        ),
        _check(
            witness.is_distinct_from(expected),
            "population semantic witness differs from native closure value",
            "23514",
        ),
        _check(
            ~select(supports.c.value)
            .where(
                supports.c.value["role"].astext == literal("population:") + pop("name"),
                supports.c.value["derivation_id"].astext == pop("evidence")["derivation_id"].astext,
                supports.c.value["admission_use_id"].astext
                == pop("evidence")["admission_use_id"].astext,
            )
            .exists(),
            "population closure lacks authentic derivation support",
            "23514",
        ),
    )
    role_discovery = (
        select(discovery.c.value)
        .where(
            discovery.c.value["target"].astext == o("operation_id"),
            discovery.c.value["target_role"].astext == wanted_role,
        )
        .exists()
    )
    discovery_member = (
        select(population_members.c.value)
        .where(
            population_members.c.value["member_id"].astext == inputs.c.value["member_id"].astext,
            population_members.c.value["subject"].astext == o("subject"),
            population_members.c.value["subject_definition"].astext
            == func.ops.ddo_operation_subject(d("release_id"), o("operation_id")),
            population_members.c.value["original_source"].astext.is_not_distinct_from(
                o("original_source")
            ),
            population_members.c.value["analyzed_scope"] == o("analyzed_scope"),
        )
        .correlate(inputs)
        .exists()
    )
    discovery_reference = (
        select(discovery_support.c.value)
        .where(
            func.coalesce(discovery_support.c.value["kind"].astext, "computation") == "computation",
            discovery_support.c.value["derivation_id"].astext
            == pop("evidence")["derivation_id"].astext,
            discovery_support.c.value["admission_use_id"].astext
            == pop("evidence")["admission_use_id"].astext,
        )
        .correlate(inputs)
        .exists()
    )
    manifest_match = and_(
        inputs.c.value["role"].astext == wanted_role,
        inputs.c.value["product_id"].astext == mv["product"].astext,
        inputs.c.value["member_id"].astext.is_not_distinct_from(mv["member"].astext),
        inputs.c.value["multiplicity"].astext == mv["multiplicity"].astext,
        or_(
            ~sequence, inputs.c.value["position"].astext.is_not_distinct_from(mv["position"].astext)
        ),
        or_(
            ~episode_required,
            func.coalesce(mv["support_episodes"], _json("[]"))
            == func.ops.ddo_input_support_episodes(b, inputs.c.value),
        ),
    )
    candidate_rows = (
        select(inputs.c.value.label("candidate"))
        .where(
            inputs.c.value["role"].astext == wanted_role,
            inputs.c.value["product_id"].astext == mv["product"].astext,
            inputs.c.value["member_id"].astext.is_not_distinct_from(mv["member"].astext),
        )
        .limit(3)
        .subquery("candidates")
    )
    candidate = candidate_rows.c.candidate
    candidate_diagnostic = select(
        func.coalesce(
            func.jsonb_agg(
                _object(
                    multiplicity=candidate["multiplicity"],
                    position=candidate["position"],
                    episodes_match=func.coalesce(mv["support_episodes"], _json("[]"))
                    == func.ops.ddo_input_support_episodes(b, candidate),
                )
            ),
            _json("[]"),
        )
    ).scalar_subquery()
    same_semantic = tuple_(
        *(role_members.c.value[name].astext for name in ("product", "member", "multiplicity"))
    ).is_not_distinct_from(
        tuple_(*(mv[name].astext for name in ("product", "member", "multiplicity")))
    )
    semantic_count = (
        select(func.count())
        .where(
            same_semantic,
            or_(
                ~sequence,
                role_members.c.value["position"].astext.is_not_distinct_from(mv["position"].astext),
            ),
            or_(
                ~episode_required,
                role_members.c.value["support_episodes"].is_not_distinct_from(
                    mv["support_episodes"]
                ),
            ),
        )
        .scalar_subquery()
    )
    native_count = select(func.count()).where(manifest_match).scalar_subquery()
    actual_kind = func.coalesce(m("kind_contract"), x("kind_contract"))
    producing = episodes.alias("source_episode")
    producing_request = requests.alias("source_request")
    source_identity = (
        select(
            case(
                (
                    func.count(producing_request.c.operation_id.distinct()) == 1,
                    func.min(producing_request.c.operation_id),
                ),
                else_=null(),
            )
        )
        .select_from(
            support_refs.join(
                producing, producing.c.id == support_refs.c.value["derivation_id"].astext
            ).join(producing_request, producing_request.c.id == producing.c.request_id)
        )
        .where(
            support_refs.c.value["role"].astext == wanted_role,
            support_refs.c.value["position"].astext.is_not_distinct_from(item["position"].astext),
            select(outputs.c.product_id)
            .where(
                outputs.c.derivation_id == producing.c.id,
                outputs.c.product_id == item["product_id"].astext,
            )
            .correlate(producing)
            .exists(),
        )
    )
    originals = (
        select(support_refs.c.value["source_reference"].astext.label("identity"))
        .where(support_refs.c.value["kind"].astext.in_(("original-source", "authored")))
        .distinct()
        .subquery("original")
    )
    provider = (
        select(
            func.ops.ddo_episode_provider_identity(
                support_refs.c.value["derivation_id"].astext
            ).label("provider")
        )
        .where(func.coalesce(support_refs.c.value["kind"].astext, "computation") == "computation")
        .subquery("authenticated")
    )
    member_steps = (
        Perform(
            func.ops.ddo_fields(
                mv,
                array(
                    [
                        "product",
                        "kind",
                        "subject",
                        "subject_definition",
                        "member",
                        "original_source",
                        "analyzed_scope",
                        "coverage",
                        "position",
                        "multiplicity",
                    ]
                ),
                array(["support_episodes", "original_sources", "provider", "alternative"]),
            )
        ),
        _check(
            or_(
                and_(mv.bool_op("?")("support_episodes"), ~episode_required),
                and_(
                    mv.bool_op("?")("original_sources"), ~identity.bool_op("?")("original-source")
                ),
            ),
            "unrequested support identity cannot salt semantic input",
            "23514",
        ),
        _check(
            and_(~sequence, mv["position"].is_distinct_from(_json("null"))),
            "nonsequence position is not a semantic determinant",
            "23514",
        ),
        SelectInto(
            select(inputs.c.value)
            .where(manifest_match)
            .order_by(cast(inputs.c.value["position"].astext, Integer()))
            .limit(1),
            ("item",),
        ),
        If(
            item.is_(None),
            (
                Raise(
                    literal("semantic binding has no exact native manifest member for role ")
                    + wanted_role,
                    "23514",
                    cast(
                        _object(
                            collection=roledef["collection"].astext,
                            multiplicity=mv["multiplicity"],
                            position=mv["position"],
                            candidates=candidate_diagnostic,
                        ),
                        Text(),
                    ),
                ),
            ),
        ),
        _check(
            semantic_count != native_count,
            "semantic member occurrence counts differ from native manifest",
            "23514",
        ),
        _selected(products, products.c.id == item["product_id"].astext, "x"),
        PerformQuery(
            select(func.ops.ddo_authorize(kinds.c.universe)).where(
                kinds.c.kind_contract == x("kind_contract")
            )
        ),
        _selected(
            members,
            and_(members.c.product_id == x("id"), members.c.member_id == item["member_id"].astext),
            "native_member",
            strict=False,
        ),
        _check(
            or_(
                tuple_(
                    mv["kind"].astext,
                    mv["subject"].astext,
                    mv["subject_definition"].astext,
                    mv["original_source"].astext,
                    mv["multiplicity"].astext,
                ).is_distinct_from(
                    tuple_(
                        actual_kind,
                        func.coalesce(m("subject"), x("subject")),
                        func.coalesce(m("subject_definition"), x("subject_definition")),
                        x("original_source"),
                        item["multiplicity"].astext,
                    )
                ),
                mv["analyzed_scope"].is_distinct_from(
                    func.coalesce(m("analyzed_scope"), x("analyzed_scope"))
                ),
            ),
            "semantic request member differs from native product/member",
            "23514",
        ),
        SelectInto(
            select(
                func.coalesce(
                    func.jsonb_agg(
                        aggregate_order_by(
                            func.to_jsonb(coverage.table_valued())
                            .op("-")("product_id")
                            .op("-")("member_id"),
                            coverage.c.ordinal,
                        )
                    ),
                    _json("[]"),
                )
            ).where(
                coverage.c.product_id == x("id"), coverage.c.member_id == item["member_id"].astext
            ),
            ("expected",),
        ),
        _check(
            mv["coverage"].is_distinct_from(expected),
            "semantic input coverage differs from native projection",
            "23514",
        ),
        If(
            or_(roledef["presence"].astext == "alternative", identity.bool_op("?")("alternative")),
            (
                SelectInto(source_identity, ("lexical_alternative",)),
                _check(
                    or_(
                        lexical_alternative.is_(None),
                        and_(
                            roledef["presence"].astext == "alternative",
                            rv["selected_alternative"].astext.is_distinct_from(lexical_alternative),
                        ),
                        and_(
                            identity.bool_op("?")("alternative"),
                            mv["alternative"].astext.is_distinct_from(lexical_alternative),
                        ),
                    ),
                    "selected alternative differs from actual producing operation",
                    "23514",
                ),
            ),
        ),
        If(
            and_(
                identity.bool_op("?")("original-source"),
                select(support_refs.c.value)
                .where(support_refs.c.value["kind"].astext.in_(("original-source", "authored")))
                .exists(),
            ),
            (
                SelectInto(
                    select(
                        func.coalesce(
                            func.jsonb_agg(
                                aggregate_order_by(originals.c.identity, originals.c.identity)
                            ),
                            _json("[]"),
                        )
                    ),
                    ("expected",),
                ),
                _check(
                    mv["original_sources"].is_distinct_from(expected),
                    "original source identity differs from selected authentic facts",
                    "23514",
                ),
            ),
        ),
        If(
            identity.bool_op("?")("provider"),
            (
                SelectInto(
                    select(
                        case(
                            (
                                and_(
                                    func.count(provider.c.provider.distinct()) == 1,
                                    func.count() == func.count(provider.c.provider),
                                ),
                                func.min(provider.c.provider),
                            ),
                            else_=null(),
                        )
                    ),
                    ("lexical_alternative",),
                ),
                _check(
                    or_(
                        lexical_alternative.is_(None),
                        mv["provider"].astext.is_distinct_from(lexical_alternative),
                    ),
                    "provider identity differs from authentic producing custody",
                    "23514",
                ),
            ),
        ),
        If(
            and_(
                episode_required,
                select(support_refs.c.value)
                .where(
                    func.coalesce(support_refs.c.value["kind"].astext, "computation")
                    == "computation"
                )
                .exists(),
            ),
            (
                Assign("expected", func.ops.ddo_input_support_episodes(b, item)),
                _check(
                    or_(expected == _json("[]"), mv["support_episodes"].is_distinct_from(expected)),
                    "required episode identity differs from selected authentic support",
                    "23514",
                ),
            ),
        ),
    )
    steps = (
        Perform(func.ops.ddo_binding_body_access(b, r("project_id"))),
        _selected(demands, demands.c.id == o("demand_id"), "d"),
        _check(
            or_(
                b["inference"].astext.is_distinct_from(d("selection")["inference"].astext),
                ~select(selected_operations.c.value)
                .where(
                    selected_operations.c.value["operation"].astext == o("operation_id"),
                    selected_operations.c.value["parameter_meaning"]
                    == func.data.ddo_normalize(func.data.ddo_field(b["parameters"], "parameters")),
                )
                .exists(),
                func.data.ddo_field(b["parameters"], "replicate").is_distinct_from(
                    Grouping(
                        case(
                            (replicate.is_(None), func.jsonb_build_array("null")),
                            else_=func.jsonb_build_array("string", replicate),
                        )
                    )
                ),
                ~select(selected_operations.c.value)
                .where(
                    selected_operations.c.value["operation"].astext == o("operation_id"),
                    selected_operations.c.value["recipe"].astext == defn("recipe"),
                    selected_operations.c.value["replicate"].astext.is_not_distinct_from(replicate),
                )
                .exists(),
            ),
            "request differs from frozen inference/parameters/replicate/recipe",
            "23514",
        ),
        _check(
            ~select(boundaries.c.id)
            .where(boundaries.c.id == b["read_id"].astext, boundaries.c.demand_id == d("id"))
            .exists(),
            "binding lacks exact native read acquisition",
            "23514",
        ),
        _selected(
            boundaries,
            and_(boundaries.c.id == b["read_id"].astext, boundaries.c.demand_id == d("id")),
            "boundary",
        ),
        SelectInto(
            select(
                func.coalesce(
                    func.jsonb_object_agg(named_sources.c.key, named_sources.c.value), _json("{}")
                )
            ).where(
                select(roles.c.value)
                .where(roles.c.value["support"]["source_set"].astext == named_sources.c.key)
                .correlate(named_sources)
                .exists()
            ),
            ("expected",),
        ),
        If(
            expected != _json("{}"),
            (
                _check(
                    func.data.ddo_json(
                        func.data.ddo_field(b["parameters"], "source_sets")
                    ).is_distinct_from(func.ops.ddo_source_sets_meaning(expected)),
                    "request source-set meaning differs from exact frozen declaration",
                    "23514",
                ),
            ),
            (
                _check(
                    func.data.ddo_field(b["parameters"], "source_sets").is_not(None),
                    "undeclared request source-set meaning",
                    "23514",
                ),
            ),
        ),
        Assign("raw", func.data.ddo_json(b["request_inputs"])),
        _check(
            or_(
                func.jsonb_typeof(raw) != "object",
                select(names.c.name)
                .where(
                    ~select(roles.c.value)
                    .where(roles.c.value["name"].astext == names.c.name)
                    .correlate(names)
                    .exists()
                )
                .exists(),
            ),
            "request input roles differ from admitted definition",
            "23514",
        ),
        ForQuery(
            ("roledef",),
            select(roles.c.value),
            (
                Assign("role_meaning", func.data.ddo_field(b["request_inputs"], wanted_role)),
                Assign("rv", raw[wanted_role]),
                _check(rv.is_(None), "missing request role", "23514"),
                Assign(
                    "state", func.data.ddo_field(role_meaning, "value", type_=JSONB())[0].astext
                ),
                _check(
                    or_(
                        ~state.in_(("present", "known-absent")),
                        and_(state == "known-absent", roledef["presence"].astext == "required"),
                    ),
                    "incomplete input cannot attach runnable request",
                    "23514",
                ),
                Assign("witness", rv["population_witness"]),
                Assign("pop", null()),
                SelectInto(
                    select(refs.c.value).where(refs.c.value["role"].astext == wanted_role),
                    ("population_reference",),
                ),
                If(
                    and_(
                        witness.is_not(None),
                        witness != _json("null"),
                        witness.bool_op("?")("identity"),
                    ),
                    witness_steps,
                    (
                        _check(
                            population_reference.is_not(None),
                            "unexpected native population receipt for unwitnessed role",
                            "23514",
                        ),
                    ),
                ),
                If(
                    role_discovery,
                    (
                        _check(
                            or_(
                                pop("id").is_(None),
                                ~func.coalesce(
                                    func.ops.ddo_discovery_role_population(
                                        _value("d"),
                                        _value("pop"),
                                        o("operation_id"),
                                        wanted_role,
                                        o("subject"),
                                        o("original_source"),
                                        o("analyzed_scope"),
                                        _value("boundary"),
                                        type_=Boolean(),
                                    ),
                                    False,
                                ),
                                select(inputs.c.value)
                                .where(
                                    inputs.c.value["role"].astext == wanted_role,
                                    or_(
                                        inputs.c.value["product_id"].astext.is_distinct_from(
                                            pop("evidence")["product_id"].astext
                                        ),
                                        ~discovery_member,
                                    ),
                                )
                                .exists(),
                                select(inputs.c.value)
                                .where(
                                    inputs.c.value["role"].astext == wanted_role,
                                    ~discovery_reference,
                                )
                                .exists(),
                            ),
                            "discovery input differs from exact selected parent/member/context support",
                            "23514",
                        ),
                    ),
                ),
                _check(
                    and_(
                        state == "known-absent",
                        select(inputs.c.value)
                        .where(inputs.c.value["role"].astext == wanted_role)
                        .exists(),
                    ),
                    "absent role cannot carry native inputs",
                    "23514",
                ),
                _check(
                    and_(state == "known-absent", pop("id").is_not(None), ~pop("complete")),
                    "open population cannot establish absence",
                    "23514",
                ),
                _check(
                    and_(
                        roledef["presence"].astext == "alternative",
                        ~roledef["alternatives"].bool_op("?")(rv["selected_alternative"].astext),
                    ),
                    "selected alternative outside declared choice",
                    "23514",
                ),
                If(
                    state == "present",
                    (
                        _check(
                            func.jsonb_typeof(rv["value"]) != "array",
                            "present role has no member collection",
                            "23514",
                        ),
                        ForQuery(("mv",), select(role_members.c.value), member_steps),
                        _check(
                            func.jsonb_array_length(rv["value"])
                            != select(func.count())
                            .where(inputs.c.value["role"].astext == wanted_role)
                            .scalar_subquery(),
                            "native input manifest differs from semantic request members",
                            "23514",
                        ),
                    ),
                ),
            ),
        ),
    )
    parameters = tuple(
        Parameter(name, pg_type(*kind))
        for name, kind in (
            ("r", (str(request_table.schema), request_table.name)),
            ("o", (str(obligation_table.schema), obligation_table.name)),
            ("def", (str(definitions.schema), definitions.name)),
            ("b", ("jsonb",)),
            ("meaning", ("jsonb",)),
            ("replicate", ("text",)),
        )
    )
    locals_ = (
        *(
            Local(name, pg_type("jsonb"))
            for name in (
                "raw",
                "roledef",
                "rv",
                "mv",
                "item",
                "expected",
                "witness",
                "role_meaning",
                "population_reference",
                "frozen_binding",
            )
        ),
        *(
            Local(name, table)
            for name, table in (
                ("x", products),
                ("native_member", members),
                ("pop", populations),
                ("d", demands),
                ("boundary", boundaries),
            )
        ),
        Local("state", pg_type("text")),
        Local("lexical_alternative", pg_type("text")),
    )
    return _procedure(
        "ddo_validate_binding", parameters, steps, locals_, returns="void", volatility="stable"
    )


def attachment_native_sql(model, protocol: bytes):
    import yaml

    wire = yaml.safe_load(protocol)["definitions"]
    (
        obligations,
        demands,
        definitions,
        requests,
        tasks,
        boundaries,
        products,
        members,
        kinds,
        kind_releases,
        admissions,
        episodes,
        outputs,
        revocations,
        intents,
        receipts,
        generations,
        uses,
    ) = (
        model.tables[name]
        for name in (
            "ops.data_obligation",
            "ops.data_demand",
            "sem.data_operation_definition",
            "ops.data_request",
            "ops.task",
            "ops.data_demand_read",
            "kb.data_product",
            "kb.data_product_member",
            "sem.data_kind_contract",
            "sem.data_kind_release",
            "ops.original_source_admission",
            "ops.data_derivation",
            "ops.data_derivation_output",
            "ops.data_revocation",
            "ops.data_completion_intent",
            "ops.data_publication_receipt",
            "ops.data_request_generation",
            "ops.demand_use",
        )
    )

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def r(field):
        return row("r", requests, field)

    def o(field):
        return row("o", obligations, field)

    def d(field):
        return row("d", demands, field)

    def defn(field):
        return row("def", definitions, field)

    def current(field):
        return row("current_task", tasks, field)

    def retained(field):
        return row("retained", intents, field)

    def binding_use(field):
        return row("binding_use", uses, field)

    j = {
        name: _value(name, JSONB()) for name in ("p", "snapshot", "read_trust", "item", "declared")
    }
    p, item, declared = (j[name] for name in ("p", "item", "declared"))
    binding, meaning = p["binding"], p["request_meaning"]
    key, episode, usekey, retained_id = (
        _value(name) for name in ("key", "episode", "usekey", "retained_id")
    )
    cnt, task = _value("cnt", BigInteger()), _value("task", BigInteger())
    invalid_current, invalid_retained = (
        _value(name, Boolean()) for name in ("invalid_current", "invalid_retained")
    )
    lifecycle = wire["data_task_state"]["x-ddo-lifecycle"]
    pending, running, terminal = (lifecycle[name] for name in ("initial", "running", "terminal"))

    def fields(value, name):
        contract = wire[name]
        required = contract["required"]
        optional = tuple(field for field in contract["properties"] if field not in required)
        return Perform(
            func.ops.ddo_fields(value, array(required, type_=Text()), array(optional, type_=Text()))
        )

    roles = _elements(defn("input_roles").op("||")(defn("output_roles")), "operation_role")
    input_roles = _elements(defn("input_roles"), "input_role")
    input_rows = _elements(binding["inputs"], "manifest_input")
    effects = _elements(defn("support_contract")["effects"], "operation_effect")
    principal = func.coalesce(
        func.nullif(func.current_setting("role"), "none"), func.session_user()
    )

    def purpose(name):
        return func.pg_has_role(principal, name, "MEMBER", type_=Boolean())

    source_context = _object(
        project_id=d("project_id"),
        subject=o("subject"),
        subject_definition=func.ops.ddo_operation_subject(d("release_id"), o("operation_id")),
        original_source=o("original_source"),
        analyzed_scope=o("analyzed_scope"),
    )
    request_values = dict(
        id=key,
        request_key=key,
        project_id=d("project_id"),
        release_id=d("release_id"),
        runtime_id=d("runtime_id"),
        operation_id=o("operation_id"),
        recipe=defn("recipe"),
        subject=o("subject"),
        original_source=o("original_source"),
        analyzed_scope=o("analyzed_scope"),
        binding=binding.op("||")(_object(execution_profile=d("selection")["execution_profile"])),
        replicate=p["replicate"].astext,
        generation=1,
        live_task_id=null(),
    )
    request_updates = dict(
        binding=request_values["binding"], release_id=d("release_id"), runtime_id=d("runtime_id")
    )
    product = products.alias("input_product")
    member = members.alias("input_member")
    release_kind = kind_releases.alias("input_kind_release")
    support_refs = (
        func.ops.ddo_input_support_refs(binding, item)
        .table_valued(column("value", JSONB()))
        .render_derived(name="input_support")
    )
    reference = support_refs.c.value
    support_projections = select(
        func.coalesce(
            func.jsonb_agg(
                func.jsonb_strip_nulls(
                    _object(
                        kind=func.coalesce(reference["kind"].astext, "computation"),
                        derivation_id=reference["derivation_id"].astext,
                        admission_use_id=reference["admission_use_id"].astext,
                    )
                )
            ),
            _json("[]"),
        )
    ).scalar_subquery()
    fact = _object(
        product=product.c.id,
        member=item["member_id"].astext,
        subject=func.coalesce(member.c.subject, product.c.subject),
        subject_definition=func.coalesce(member.c.subject_definition, product.c.subject_definition),
        original_source=product.c.original_source,
        analyzed_scope=func.coalesce(member.c.analyzed_scope, product.c.analyzed_scope),
        meaning_body=func.coalesce(member.c.body, product.c.canonical_body),
        support_references=support_projections,
        support_evidence=_object(producer_output=item["producer_output"]),
    )
    kind = case(
        (item["member_id"].astext.is_(None), product.c.kind_contract), else_=member.c.kind_contract
    )
    admissible_product = (
        select(product.c.id)
        .select_from(
            product.outerjoin(
                member,
                and_(
                    member.c.product_id == product.c.id,
                    member.c.member_id == item["member_id"].astext,
                ),
            ).join(
                release_kind,
                and_(
                    release_kind.c.kind_contract == kind,
                    release_kind.c.release_id == d("release_id"),
                ),
            )
        )
        .where(
            product.c.id == item["product_id"].astext,
            product.c.project_id == d("project_id"),
            func.ops.ddo_binding_source(
                declared,
                fact,
                o("original_source"),
                func.coalesce(d("selection")["source_sets"], _json("{}")),
                type_=Boolean(),
            ),
            or_(
                and_(
                    item["member_id"].astext.is_(None),
                    declared["accepted_kind_contracts"].bool_op("?")(product.c.kind_contract),
                ),
                and_(
                    member.c.member_id.is_not(None),
                    declared["accepted_kind_contracts"].bool_op("?")(member.c.kind_contract),
                ),
            ),
        )
        .exists()
    )
    authenticated_original = (
        select(admissions.c.id)
        .where(
            admissions.c.id == reference["admission_id"].astext,
            func.ops.ddo_original_admission_valid(admissions.table_valued(), type_=Boolean()),
        )
        .correlate(support_refs)
        .exists()
    )
    source_request = requests.alias("source_request")
    producer = episodes.alias("producer")
    produced = outputs.alias("produced")
    direct_revocation = (
        select(literal(1))
        .select_from(revocations)
        .where(
            revocations.c.scope
            == func.ops.ddo_scope(source_request.c.project_id, source_request.c.original_source),
            or_(
                and_(
                    revocations.c.selector_kind == "derivation",
                    revocations.c.selector == producer.c.id,
                ),
                and_(
                    revocations.c.selector_kind == "recipe",
                    revocations.c.selector == producer.c.recipe,
                ),
                and_(
                    revocations.c.selector_kind == "runtime",
                    revocations.c.selector == producer.c.runtime_id,
                ),
                and_(
                    revocations.c.selector_kind == "product",
                    select(produced.c.product_id)
                    .where(
                        produced.c.derivation_id == producer.c.id,
                        produced.c.product_id == revocations.c.selector,
                    )
                    .correlate(producer, revocations)
                    .exists(),
                ),
            ),
        )
        .correlate(source_request, producer)
        .exists()
    )
    substitution = (
        select(producer.c.id)
        .select_from(producer.join(source_request, source_request.c.id == producer.c.request_id))
        .where(
            producer.c.id == episode,
            producer.c.outcome.in_(("success", "empty")),
            source_request.c.request_key == r("request_key"),
            ~direct_revocation,
        )
        .exists()
    )
    uncommitted_intent = (
        ~select(receipts.c.intent_id)
        .where(receipts.c.intent_id == intents.c.id)
        .correlate(intents)
        .exists()
    )
    old_supports = _elements(retained("payload")["support"], "old_support")
    old_support = old_supports.c.value
    old_original = (
        select(admissions.c.id)
        .where(
            admissions.c.id == old_support["admission_id"].astext,
            admissions.c.source_reference == old_support["source_reference"].astext,
            func.ops.ddo_original_admission_valid(admissions.table_valued(), type_=Boolean()),
        )
        .correlate(old_supports)
        .exists()
    )
    old_use = (
        select(uses.c.id)
        .where(
            uses.c.id == old_support["admission_use_id"].astext,
            uses.c.derivation_id == old_support["derivation_id"].astext,
            func.ops.ddo_node_valid("use", uses.c.id, type_=Boolean()),
        )
        .correlate(old_supports)
        .exists()
    )

    def distrust(project, source, runtime, recipe):
        return (
            select(literal(1))
            .select_from(revocations)
            .where(
                revocations.c.scope == func.ops.ddo_scope(project, source),
                or_(
                    and_(
                        revocations.c.selector_kind == "runtime", revocations.c.selector == runtime
                    ),
                    and_(revocations.c.selector_kind == "recipe", revocations.c.selector == recipe),
                ),
            )
            .exists()
        )

    invalid_old_support = (
        select(old_support)
        .where(
            case(
                (old_support["kind"].astext.in_(("original-source", "authored")), ~old_original),
                (
                    old_support["admission_use_id"].astext.is_(None),
                    ~func.ops.ddo_node_valid(
                        "episode", old_support["derivation_id"].astext, type_=Boolean()
                    ),
                ),
                else_=~old_use,
            )
        )
        .exists()
    )
    generation_steps = (
        If(
            r("live_task_id").is_not(None),
            (
                _selected(tasks, tasks.c.id == r("live_task_id"), "current_task", lock=True),
                _selected(
                    intents,
                    and_(
                        intents.c.request_id == r("id"),
                        intents.c.generation == r("generation"),
                        uncommitted_intent,
                    ),
                    "retained",
                    strict=False,
                ),
                Assign(
                    "invalid_current",
                    or_(
                        ~func.ops.ddo_support_available(
                            _value("r"), r("binding")["support"], type_=Boolean()
                        ),
                        distrust(
                            r("project_id"), r("original_source"), r("runtime_id"), r("recipe")
                        ),
                    ),
                ),
                Assign(
                    "invalid_retained",
                    and_(
                        retained("id").is_not(None),
                        or_(
                            invalid_old_support,
                            distrust(
                                r("project_id"),
                                r("original_source"),
                                retained("runtime_id"),
                                r("recipe"),
                            ),
                        ),
                    ),
                ),
                _check(
                    and_(
                        or_(invalid_current, invalid_retained),
                        current("status") == running,
                        or_(
                            current("lease_until").is_(None),
                            current("lease_until") > func.clock_timestamp(),
                        ),
                    ),
                    "invalid current generation still has an active producer lease",
                    "23514",
                ),
                If(
                    or_(
                        current("status").in_(terminal),
                        and_(
                            or_(invalid_current, invalid_retained),
                            or_(
                                current("status") == pending,
                                and_(
                                    current("status") == running,
                                    current("lease_until") <= func.clock_timestamp(),
                                ),
                            ),
                        ),
                    ),
                    (
                        _check(
                            distrust(
                                d("project_id"),
                                o("original_source"),
                                d("runtime_id"),
                                defn("recipe"),
                            ),
                            "replacement runtime or recipe was directly revoked",
                            "23514",
                        ),
                        SelectInto(
                            update(requests)
                            .where(requests.c.id == r("id"))
                            .values(
                                generation=requests.c.generation + 1,
                                live_task_id=null(),
                                **request_updates,
                            )
                            .returning(*requests.c),
                            ("r",),
                        ),
                    ),
                ),
            ),
        ),
        If(
            r("live_task_id").is_(None),
            (
                SelectInto(
                    update(requests)
                    .where(requests.c.id == r("id"))
                    .values(**request_updates)
                    .returning(*requests.c),
                    ("r",),
                ),
                SelectInto(
                    insert(tasks)
                    .values(
                        release_id=r("release_id"),
                        data_request_id=r("id"),
                        data_generation=r("generation"),
                        status=pending,
                        attempt=0,
                        cost=_json("{}"),
                        priority=0,
                        created_at=func.clock_timestamp(),
                    )
                    .returning(tasks.c.id),
                    ("task",),
                ),
                Sql(
                    insert(generations).values(
                        request_id=r("id"), generation=r("generation"), task_id=task
                    )
                ),
                SelectInto(
                    update(requests)
                    .where(requests.c.id == r("id"))
                    .values(live_task_id=task)
                    .returning(*requests.c),
                    ("r",),
                ),
            ),
        ),
    )
    state = case((episode.is_(None), "attached"), else_="fulfilled")
    existing_use = uses.alias("original_use")
    steps = (
        fields(p, "attach_data_request_request"),
        If(
            meaning[0].astext == "ddo",
            (
                _check(
                    or_(
                        meaning[1].astext != "semantic-request",
                        meaning[2].astext != "1",
                        func.jsonb_array_length(meaning) != 4,
                    ),
                    "invalid semantic request frame",
                    "23514",
                ),
                Assign("p", func.jsonb_set(p, array(["request_meaning"]), meaning[3])),
            ),
        ),
        _selected(obligations, obligations.c.id == p["obligation_id"].astext, "o"),
        _selected(demands, demands.c.id == o("demand_id"), "d"),
        _selected(
            definitions,
            and_(
                definitions.c.release_id == d("release_id"),
                definitions.c.operation_id == o("operation_id"),
            ),
            "def",
        ),
        Perform(
            func.ops.ddo_require_subject_source(
                func.ops.ddo_release_subject_scopes(d("release_id")),
                defn("subject_definition"),
                o("original_source"),
            )
        ),
        PerformQuery(
            select(func.ops.ddo_authorize(kinds.c.universe)).select_from(
                roles.join(kinds, kinds.c.kind_contract == roles.c.value["kind_contract"].astext)
            )
        ),
        If(
            func.coalesce(defn("command_class") == "pdf", False),
            (Perform(func.ops.require_pdf_operation(d("release_id"), "retain_pdf_original")),),
            (
                If(
                    func.coalesce(defn("command_class") == "rich", False),
                    (
                        _check(
                            ~purpose("corpus_sem_writer"),
                            "rich admission requires native write purpose",
                            "42501",
                        ),
                    ),
                    (
                        If(
                            or_(
                                *(
                                    func.coalesce(defn("command_class") == kind, False)
                                    for kind in ("policy", "structural", "operation_event")
                                )
                            ),
                            (
                                _check(
                                    ~purpose("corpus_sem_evaluator"),
                                    "policy authorization requires native evaluator purpose",
                                    "42501",
                                ),
                            ),
                            (
                                If(
                                    or_(
                                        ~defn("profile").in_(("derivation", "discovery")),
                                        func.coalesce(
                                            defn("support_contract")["effects"], _json("[]")
                                        )
                                        != _json("[]"),
                                    ),
                                    (
                                        _check(
                                            ~purpose("corpus_sem_writer"),
                                            "external command requires native write purpose",
                                            "42501",
                                        ),
                                        _check(
                                            or_(
                                                defn("profile") != "command",
                                                defn("support_contract")["external"].is_(None),
                                                func.coalesce(
                                                    defn("support_contract")["effects"], _json("[]")
                                                )
                                                == _json("[]"),
                                                select(effects.c.value)
                                                .where(
                                                    or_(
                                                        effects.c.value["authorization"]
                                                        != _json('["native-purpose:write"]'),
                                                        effects.c.value["idempotency"].astext
                                                        != "external-packet",
                                                        effects.c.value["fulfillment"].astext
                                                        != "native-publication-receipt",
                                                    )
                                                )
                                                .exists(),
                                            ),
                                            "operation profile requires its own declared command/read execution contract",
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
        _check(
            or_(
                p["replicate"].astext == "",
                func.ops.ddo_replicate_required(
                    defn("support_contract")["replicate_policy"].astext, type_=Boolean()
                ).is_distinct_from(p["replicate"].astext.is_not(None)),
            ),
            "replicate selection differs from declared operation policy",
            "23514",
        ),
        fields(binding, "binding"),
        _selected(
            boundaries,
            and_(boundaries.c.id == binding["read_id"].astext, boundaries.c.demand_id == d("id")),
            "boundary",
        ),
        Assign("read_trust", _value("p_read_trust", JSONB())),
        _check(
            or_(
                func.data.ddo_field(meaning, "recipe").is_distinct_from(
                    func.jsonb_build_array("string", defn("recipe"))
                ),
                func.data.ddo_field(meaning, "subject").is_distinct_from(
                    func.jsonb_build_array("string", o("subject"))
                ),
                func.data.ddo_field(meaning, "subject_context").is_distinct_from(
                    func.data.ddo_json_meaning(source_context)
                ),
                func.data.ddo_field(meaning, "inputs").is_distinct_from(
                    func.data.ddo_normalize(binding["request_inputs"])
                ),
                func.data.ddo_field(meaning, "parameters").is_distinct_from(
                    func.data.ddo_normalize(binding["parameters"])
                ),
                func.data.ddo_field(meaning, "inference").is_distinct_from(
                    func.jsonb_build_array("string", binding["inference"].astext)
                ),
            ),
            "request identity differs from compiled binding",
            "23514",
        ),
        Assign("key", func.data.ddo_identity("semantic-request", meaning)),
        _check(
            and_(p.bool_op("?")("request_key"), p["request_key"].astext != key),
            "request key differs from canonical meaning",
            "23514",
        ),
        Assign("snapshot", _value("p_snapshot", JSONB())),
        Perform(func.ops.ddo_require_active_demand(d("id"))),
        # Keep the insert and subsequent locking read as separate statements: a
        # concurrent winner may become visible only under the next RC snapshot.
        Sql(
            insert(requests)
            .values(**request_values)
            .on_conflict_do_nothing(index_elements=[requests.c.request_key])
        ),
        _selected(requests, requests.c.request_key == key, "r", lock=True),
        _check(
            or_(
                tuple_(
                    r("project_id"), r("recipe"), r("subject"), r("original_source"), r("replicate")
                ).is_distinct_from(
                    tuple_(
                        d("project_id"),
                        defn("recipe"),
                        o("subject"),
                        o("original_source"),
                        p["replicate"].astext,
                    )
                ),
                r("analyzed_scope").is_distinct_from(o("analyzed_scope")),
            ),
            "request custody or contract mismatch",
            "23514",
        ),
        _check(
            ~func.ops.ddo_bound_support_available(
                _value("r"), binding["support"], binding, type_=Boolean()
            ),
            "selected support is unavailable or revoked",
            "23514",
        ),
        Perform(
            func.ops.ddo_validate_binding(
                _value("r"), _value("o"), _value("def"), binding, meaning, p["replicate"].astext
            )
        ),
        _check(
            ~func.ops.ddo_trust_snapshot_meaning(j["read_trust"], type_=JSONB()).bool_op("@>")(
                func.ops.ddo_trust_snapshot_meaning(j["snapshot"])
            ),
            "binding trust snapshot changed after support locking",
            "23514",
        ),
        Perform(
            func.ops.ddo_require_binding(
                d("id"), o("operation_id"), o("subject"), meaning, binding, j["read_trust"], True
            )
        ),
        _check(
            func.jsonb_typeof(binding["inputs"]) != "array",
            "input manifest must be an array",
            "23514",
        ),
        ForQuery(
            ("item",),
            select(input_rows.c.value),
            (
                fields(item, "input_member"),
                SelectInto(
                    select(input_roles.c.value).where(
                        input_roles.c.value["name"].astext == item["role"].astext
                    ),
                    ("declared",),
                ),
                PerformQuery(
                    select(func.ops.ddo_authorize(kinds.c.universe)).where(
                        kinds.c.kind_contract == declared["kind_contract"].astext
                    )
                ),
                _check(
                    or_(
                        declared.is_(None),
                        ~admissible_product,
                        cast(item["position"].astext, Integer()) < 0,
                        cast(item["multiplicity"].astext, Integer()) < 1,
                    ),
                    "input role/member/kind/source mismatch",
                    "23514",
                ),
                _check(
                    ~select(reference)
                    .where(
                        or_(
                            func.coalesce(reference["kind"].astext, "computation") == "computation",
                            authenticated_original,
                        )
                    )
                    .exists(),
                    "input lacks selected authentic support",
                    "23514",
                ),
            ),
        ),
        ForQuery(
            ("declared",),
            select(input_roles.c.value),
            (
                SelectInto(
                    select(
                        func.coalesce(
                            func.sum(cast(input_rows.c.value["multiplicity"].astext, Integer())), 0
                        )
                    ).where(input_rows.c.value["role"].astext == declared["name"].astext),
                    ("cnt",),
                ),
                _check(
                    or_(
                        cnt < func.coalesce(cast(declared["minimum"].astext, Integer()), 0),
                        and_(
                            declared["maximum"].astext.is_not(None),
                            cnt > cast(declared["maximum"].astext, Integer()),
                        ),
                    ),
                    "input cardinality mismatch",
                    "23514",
                ),
            ),
        ),
        SelectInto(
            select(episodes.c.id)
            .where(
                episodes.c.request_id == r("id"),
                episodes.c.generation == r("generation"),
                func.ops.ddo_node_valid("episode", episodes.c.id, type_=Boolean()),
            )
            .order_by(episodes.c.id)
            .limit(1),
            ("episode",),
        ),
        If(
            p.bool_op("?")("rebind_derivation"),
            (
                Assign("episode", p["rebind_derivation"].astext),
                _check(
                    or_(
                        d("strength") != "value",
                        defn("support_contract")["provenance"].astext != "value_substitution",
                        ~substitution,
                        select(input_roles.c.value)
                        .where(
                            func.coalesce(input_roles.c.value["identity_requirements"], _json("[]"))
                            != _json("[]")
                        )
                        .exists(),
                    ),
                    "support substitution cannot rehabilitate this producer/contract",
                    "23514",
                ),
            ),
        ),
        If(episode.is_(None), generation_steps),
        SelectInto(
            select(intents.c.id).where(
                intents.c.request_id == r("id"),
                intents.c.generation == r("generation"),
                uncommitted_intent,
            ),
            ("retained_id",),
        ),
        Assign(
            "usekey",
            literal("use:")
            + func.ops.ddo_digest(
                func.jsonb_build_array(
                    o("id"), r("id"), r("generation"), episode, binding, j["snapshot"]
                )
            ),
        ),
        Sql(
            insert(uses)
            .values(
                id=usekey,
                demand_id=d("id"),
                obligation_id=o("id"),
                fate=state,
                request_id=r("id"),
                generation=r("generation"),
                derivation_id=episode,
                selection=binding,
                trust_snapshot=j["snapshot"],
                created_at=func.clock_timestamp(),
                created_xid=cast(func.pg_current_xact_id(), Text()),
            )
            .on_conflict_do_nothing()
        ),
        SelectInto(
            select(core_relation_row(existing_use))
            .select_from(existing_use)
            .where(
                existing_use.c.request_id == r("id"),
                existing_use.c.generation == r("generation"),
                existing_use.c.selection == r("binding").op("-")("execution_profile"),
            )
            .order_by(existing_use.c.id)
            .limit(1),
            ("binding_use",),
            True,
        ),
        Return(
            _object(
                payload=_object(
                    request_id=r("id"),
                    release_id=r("release_id"),
                    runtime_id=r("runtime_id"),
                    binding=r("binding").op("-")("execution_profile"),
                    binding_demand_id=binding_use("demand_id"),
                    binding_obligation_id=binding_use("obligation_id"),
                    generation=r("generation"),
                    task_id=r("live_task_id"),
                    fate=state,
                    derivation_id=episode,
                    use_id=usekey,
                    trust_snapshot=j["snapshot"],
                    action=case(
                        (episode.is_not(None), "reuse"),
                        (retained_id.is_not(None), "reconcile"),
                        else_="compute",
                    ),
                    retained_intent_id=retained_id,
                )
            )
        ),
    )
    parameters = tuple(
        Parameter(name, pg_type("jsonb")) for name in ("p_payload", "p_read_trust", "p_snapshot")
    )
    locals_ = (
        *(
            Local(name, table)
            for name, table in (
                ("o", obligations),
                ("d", demands),
                ("def", definitions),
                ("r", requests),
                ("retained", intents),
                ("current_task", tasks),
                ("binding_use", uses),
                ("boundary", boundaries),
            )
        ),
        *(
            Local(name, pg_type("jsonb"), _value("p_payload", JSONB()) if name == "p" else None)
            for name in j
        ),
        *(Local(name, pg_type("text")) for name in ("key", "episode", "usekey", "retained_id")),
        Local("task", pg_type("bigint")),
        Local("cnt", pg_type("bigint")),
        Local("invalid_current", pg_type("boolean")),
        Local("invalid_retained", pg_type("boolean")),
    )
    return _procedure("ddo_attach_data_request", parameters, steps, locals_)


def attachment_batch_native_sql(model):
    boundaries, demands, obligations, trust = (
        model.tables[name]
        for name in (
            "ops.data_demand_read",
            "ops.data_demand",
            "ops.data_obligation",
            "ops.data_trust_scope",
        )
    )

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def boundary(field):
        return row("boundary", boundaries, field)

    def demand(field):
        return row("demand", demands, field)

    def obligation(field):
        return row("obligation", obligations, field)

    p, item, result, results, cached, read_trust, snapshot = (
        _value(name, JSONB())
        for name in ("p", "item", "result", "results", "cached", "read_trust", "snapshot")
    )
    scope_key, cache_key = (_value(name) for name in ("scope_key", "cache_key"))
    entries = _elements(p["items"], "attach_entry")
    scopes = (
        func.ops.ddo_support_scopes(
            demand("project_id"),
            obligations.c.original_source,
            entries.c.value["binding"]["support"],
        )
        .table_valued(column("scope", Text()))
        .render_derived(name="scopes")
        .lateral("scopes")
    )
    lock_union = (
        select(scopes.c.scope)
        .select_from(
            entries.join(
                obligations,
                and_(
                    obligations.c.id == entries.c.value["obligation_id"].astext,
                    obligations.c.demand_id == demand("id"),
                ),
            ).join(scopes, literal(True))
        )
        .distinct()
        .order_by(scopes.c.scope)
    )
    item_scopes = (
        func.ops.ddo_support_scopes(
            demand("project_id"), obligation("original_source"), item["binding"]["support"]
        )
        .table_valued(column("scope", Text()))
        .render_derived(name="item_scope")
    )
    pairs = _each(snapshot, "support_epoch")
    steps = (
        _selected(boundaries, boundaries.c.id == p["read_id"].astext, "boundary"),
        _selected(demands, demands.c.id == boundary("demand_id"), "demand"),
        # Acquire the canonical union outside item savepoints so an item refusal
        # cannot release a lock retained by the read or another accepted item.
        ForQuery(
            ("scope_key",),
            lock_union,
            (
                Sql(
                    insert(trust)
                    .values(scope=scope_key, project_id=demand("project_id"), epoch=0)
                    .on_conflict_do_nothing()
                ),
                PerformQuery(
                    select(literal(1))
                    .select_from(trust)
                    .where(trust.c.scope == scope_key, trust.c.project_id == demand("project_id"))
                    .with_for_update(read=True)
                ),
            ),
        ),
        Assign(
            "read_trust",
            func.ops.ddo_require_read_current(_value("boundary"), demand("project_id")),
        ),
        Perform(
            func.ops.ddo_require_source_set_acquisitions(
                func.coalesce(demand("selection")["source_sets"], _json("{}")), demand("project_id")
            )
        ),
        ForQuery(
            ("item",),
            select(entries.c.value),
            (
                Assign("cache_key", func.ops.ddo_digest(item)),
                If(
                    cached.bool_op("?")(cache_key),
                    (
                        Assign(
                            "results", results.op("||")(func.jsonb_build_array(cached[cache_key]))
                        ),
                        Continue(),
                    ),
                ),
                CatchCheckViolation(
                    (
                        _selected(
                            obligations,
                            and_(
                                obligations.c.id == item["obligation_id"].astext,
                                obligations.c.demand_id == demand("id"),
                            ),
                            "obligation",
                            strict=False,
                        ),
                        _check(
                            or_(
                                obligation("id").is_(None),
                                item["binding"]["read_id"].astext.is_distinct_from(boundary("id")),
                            ),
                            "attach item differs from the admitted demand/read",
                            "23514",
                        ),
                        SelectInto(
                            select(
                                func.coalesce(
                                    func.jsonb_object_agg(
                                        item_scopes.c.scope, read_trust[item_scopes.c.scope]
                                    ),
                                    _json("{}"),
                                )
                            ),
                            ("snapshot",),
                        ),
                        _check(
                            select(pairs.c.value).where(pairs.c.value == _json("null")).exists(),
                            "attach support is outside the pinned read scopes",
                            "23514",
                        ),
                        Assign(
                            "result",
                            func.ops.ddo_attach_data_request(
                                item, read_trust, snapshot, type_=JSONB()
                            )["payload"],
                        ),
                        Assign("result", _object(state=result["fate"].astext, result=result)),
                    ),
                    (
                        Assign(
                            "result",
                            _object(
                                state="refused",
                                sqlstate=_value("sqlstate"),
                                reason=_value("sqlerrm"),
                            ),
                        ),
                    ),
                ),
                Assign("cached", cached.op("||")(func.jsonb_build_object(cache_key, result))),
                Assign("results", results.op("||")(func.jsonb_build_array(result))),
            ),
        ),
        Return(_object(payload=_object(items=results))),
    )
    locals_ = (
        Local("p", pg_type("jsonb"), _value("p_payload", JSONB())),
        *(
            Local(name, table)
            for name, table in (
                ("boundary", boundaries),
                ("demand", demands),
                ("obligation", obligations),
            )
        ),
        *(Local(name, pg_type("jsonb")) for name in ("item", "result", "read_trust", "snapshot")),
        Local("results", pg_type("jsonb"), _json("[]")),
        Local("cached", pg_type("jsonb"), _json("{}")),
        Local("cache_key", pg_type("text")),
        Local("scope_key", pg_type("text")),
    )
    return _procedure(
        "attach_data_requests", (Parameter("p_payload", pg_type("jsonb")),), steps, locals_
    )


def request_attachment_native_sql(model, protocol: bytes):
    return (
        binding_validation_native_sql(model)
        + attachment_native_sql(model, protocol)
        + attachment_batch_native_sql(model)
    )
