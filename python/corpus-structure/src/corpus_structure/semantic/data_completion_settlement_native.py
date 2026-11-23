"""Domain-generated output witnesses, original-producer seals and intent settlement."""

from pglast import ast
from sqlalchemy import (
    BigInteger,
    Boolean,
    MetaData,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    tuple_,
    union,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, array, insert

from .data_operation_partition_native import population_upload_fence, population_upload_requested
from .data_operation_value_native import canonical_text_digest
from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    Exit,
    ForQuery,
    GetRowCount,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    Sql,
    Statement,
    core_relation_row,
    core_variable,
    pg_type,
)
from .validity_programs import family_programs, input_role, selected_family


def completion_settlement_native_programs(model: MetaData) -> tuple[NativeRoutine, ...]:
    output = []
    tables = model.tables
    request, definition, product, member = (
        tables[name]
        for name in (
            "ops.data_request",
            "sem.data_operation_definition",
            "kb.data_product",
            "kb.data_product_member",
        )
    )

    def row(name, relation, field=None):
        return core_variable(name, JSONB() if field is None else relation.c[field].type, field)

    def rf(field=None):
        return row("r", request, field)

    def obj(**fields):
        return func.jsonb_build_object(
            *(part for key, value in fields.items() for part in (key, value)), type_=JSONB()
        )

    def items(value, name):
        return (
            func.jsonb_array_elements(value)
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
        )

    empty, json_null = cast(literal("[]"), JSONB()), cast(literal("null"), JSONB())

    def reject(condition, message, state="P0001"):
        return If(condition, (Raise(message, state),))

    def lookup(name, relation, *conditions, lock=False):
        query = select(core_relation_row(relation)).select_from(relation).where(*conditions)
        return SelectInto(query.with_for_update() if lock else query, (name,), strict=True)

    def routine(
        schema,
        name,
        params,
        body,
        locals_=(),
        *,
        returns="void",
        stable=False,
        immutable=False,
        strict=False,
        definer=True,
        setof=False,
    ):
        result = pg_type(*returns.split("."))
        result.setof = setof
        output.append(
            NativeRoutine(
                schema,
                name,
                parameters=tuple(Parameter(key, pg_type(*kind.split("."))) for key, kind in params),
                returns=result,
                body=Block(tuple(body), tuple(locals_)),
                strict=strict,
                volatility="immutable" if immutable else "stable" if stable else None,
                security_definer=definer,
                search_path=("pg_catalog", "pg_temp"),
            )
        )

    pointer = core_variable("pointer", Text())
    path_items = (
        func.unnest(
            func.string_to_array(
                case((func.left(pointer, 1) == "/", func.substr(pointer, 2)), else_=pointer), "/"
            )
        )
        .table_valued(column("value", Text()), with_ordinality="ordinality")
        .render_derived(name="path_item")
    )
    decoded = func.replace(func.replace(path_items.c.value, "~1", "/"), "~0", "~")
    paths = func.coalesce(
        func.array_agg(decoded).aggregate_order_by(path_items.c.ordinality),
        cast(array([]), ARRAY(Text())),
    )
    # The ordered aggregate is the native ARRAY subquery's typed equivalent.
    path_type = pg_type("text")
    path_type.arrayBounds = (ast.Integer(ival=-1),)
    output.append(
        NativeRoutine(
            "data",
            "ddo_witness_path",
            parameters=(Parameter("pointer", pg_type("text")),),
            returns=path_type,
            body=select(
                case(
                    (pointer == "", cast(array([]), ARRAY(Text()))),
                    else_=select(paths).select_from(path_items).scalar_subquery(),
                )
            ),
            strict=True,
            volatility="immutable",
            search_path=("pg_catalog", "pg_temp"),
        )
    )
    body, current, following, item = (
        core_variable(name, JSONB()) for name in ("body", "current_values", "following", "item")
    )
    part = core_variable("part", Text())
    parts = (
        func.unnest(func.data.ddo_witness_path(pointer))
        .table_valued(column("value", Text()), with_ordinality="ordinality")
        .render_derived(name="part")
    )
    values = items(current, "current_item")
    routine(
        "data",
        "ddo_witness_records",
        (("body", "jsonb"), ("pointer", "text")),
        (
            ForQuery(
                ("part",),
                select(parts.c.value).order_by(parts.c.ordinality),
                (
                    Assign("following", empty),
                    ForQuery(
                        ("item",),
                        select(values.c.value),
                        (
                            If(
                                part == "*",
                                (
                                    reject(
                                        func.jsonb_typeof(item) != "array",
                                        "output witness member step requires an array",
                                    ),
                                    Assign("following", following.op("||")(item)),
                                ),
                                (
                                    reject(
                                        func.jsonb_typeof(item) != "object",
                                        "output witness property step requires a record",
                                    ),
                                    If(
                                        and_(item.bool_op("?")(part), item[part] != json_null),
                                        (
                                            Assign(
                                                "following",
                                                following.op("||")(
                                                    func.jsonb_build_array(item[part])
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    Assign("current_values", following),
                ),
            ),
            ReturnQuery(select(values.c.value)),
        ),
        (
            Local("current_values", pg_type("jsonb"), func.jsonb_build_array(body)),
            Local("following", pg_type("jsonb")),
            Local("part", pg_type("text")),
            Local("item", pg_type("jsonb")),
        ),
        returns="jsonb",
        immutable=True,
        strict=True,
        definer=False,
        setof=True,
    )

    (
        completion,
        witness,
        selected_output,
        decoded_body,
        record_,
        candidate,
        candidates,
        comparison,
        actual,
        expected,
    ) = (
        core_variable(name, JSONB())
        for name in (
            "completion",
            "witness",
            "output",
            "body",
            "record",
            "candidate",
            "candidates",
            "comparison",
            "actual",
            "expected",
        )
    )
    complete, matched = core_variable("complete", Boolean()), core_variable("matched", Boolean())
    contract = row("definition", definition, "support_contract")
    witnesses = items(func.coalesce(contract["output_witnesses"], empty), "witness_row")
    inputs = items(rf("binding")["inputs"], "input_row")
    candidate_value = obj(
        product=product.c.id,
        member=member.c.member_id,
        reference=func.jsonb_build_array(product.c.id, member.c.member_id),
        kind_contract=func.coalesce(member.c.kind_contract, product.c.kind_contract),
        project_id=product.c.project_id,
        **{
            name: func.coalesce(member.c[name], product.c[name])
            for name in ("subject", "subject_definition", "original_source", "analyzed_scope")
        },
        body=func.data.ddo_json(func.coalesce(member.c.body, product.c.canonical_body)),
    )
    candidate_query = (
        select(func.coalesce(func.jsonb_agg(candidate_value), empty))
        .select_from(
            inputs.join(product, product.c.id == inputs.c.value["product_id"].astext).outerjoin(
                member,
                and_(
                    member.c.product_id == product.c.id,
                    member.c.member_id == inputs.c.value["member_id"].astext,
                ),
            )
        )
        .where(
            inputs.c.value["role"].astext == witness["input_role"].astext,
            or_(inputs.c.value["member_id"].astext.is_(None), member.c.member_id.is_not(None)),
        )
    )
    outputs, members = (
        items(completion["outputs"], "output_row"),
        items(selected_output["product"]["members"], "member_row"),
    )
    records = (
        func.data.ddo_witness_records(
            func.data.ddo_json(func.data.ddo_normalize(decoded_body)), witness["records"].astext
        )
        .table_valued(column("value", JSONB()))
        .render_derived(name="record_row")
    )
    candidate_rows, comparisons = (
        items(candidates, "candidate_row"),
        items(witness["comparisons"], "comparison_row"),
    )
    projection, field = (
        comparison["input"]["projection"].astext,
        comparison["input"]["field"].astext,
    )
    incomplete = (Assign("complete", literal(False)), Exit())
    routine(
        "ops",
        "ddo_assert_output_witnesses",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            lookup(
                "definition",
                definition,
                definition.c.release_id == rf("release_id"),
                definition.c.operation_id == rf("operation_id"),
            ),
            If(
                func.jsonb_array_length(func.coalesce(contract["output_witnesses"], empty)) > 0,
                (Perform(func.ops.ddo_binding_body_access(rf("binding"), rf("project_id"))),),
            ),
            ForQuery(
                ("witness",),
                select(witnesses.c.value),
                (
                    SelectInto(candidate_query, ("candidates",)),
                    ForQuery(
                        ("output",),
                        select(outputs.c.value).where(
                            outputs.c.value["role"].astext == witness["output_role"].astext
                        ),
                        (
                            Assign("body", selected_output["product"]["body"]),
                            If(
                                selected_output["member_id"].astext.is_not(None),
                                (
                                    SelectInto(
                                        select(members.c.value["body"]).where(
                                            members.c.value["member_id"].astext
                                            == selected_output["member_id"].astext
                                        ),
                                        ("body",),
                                        strict=True,
                                    ),
                                ),
                            ),
                            ForQuery(
                                ("record",),
                                select(records.c.value),
                                (
                                    Assign("matched", literal(False)),
                                    ForQuery(
                                        ("candidate",),
                                        select(candidate_rows.c.value),
                                        (
                                            Assign("complete", literal(True)),
                                            ForQuery(
                                                ("comparison",),
                                                select(comparisons.c.value),
                                                (
                                                    Assign(
                                                        "actual",
                                                        func.coalesce(
                                                            record_.op("#>", return_type=JSONB())(
                                                                func.data.ddo_witness_path(
                                                                    comparison[
                                                                        "output_field"
                                                                    ].astext
                                                                )
                                                            ),
                                                            json_null,
                                                        ),
                                                    ),
                                                    If(
                                                        projection == "selected-input",
                                                        (Assign("expected", candidate[field]),),
                                                        (
                                                            Assign(
                                                                "expected",
                                                                func.coalesce(
                                                                    candidate["body"].op(
                                                                        "#>", return_type=JSONB()
                                                                    )(
                                                                        func.data.ddo_witness_path(
                                                                            field
                                                                        )
                                                                    ),
                                                                    json_null,
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                    If(
                                                        and_(
                                                            func.coalesce(expected, json_null)
                                                            == json_null,
                                                            comparison["encoding"].astext
                                                            == "value",
                                                            ~and_(
                                                                projection == "selected-input",
                                                                field == "member",
                                                            ),
                                                        ),
                                                        incomplete,
                                                    ),
                                                    If(
                                                        comparison["encoding"].astext != "value",
                                                        (
                                                            If(
                                                                func.jsonb_typeof(actual)
                                                                != "string",
                                                                incomplete,
                                                            ),
                                                            Assign(
                                                                "actual",
                                                                cast(
                                                                    actual.op(
                                                                        "#>>", return_type=Text()
                                                                    )(array([], type_=Text())),
                                                                    JSONB(),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                    If(
                                                        comparison["encoding"].astext
                                                        == "context-meaning-json",
                                                        (
                                                            Assign(
                                                                "expected",
                                                                func.data.ddo_json_meaning(
                                                                    expected
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                    If(
                                                        actual.is_distinct_from(expected),
                                                        incomplete,
                                                    ),
                                                ),
                                            ),
                                            If(
                                                complete, (Assign("matched", literal(True)), Exit())
                                            ),
                                        ),
                                    ),
                                    reject(
                                        ~matched,
                                        literal(
                                            "output witness has no complete selected input member: "
                                        )
                                        + func.coalesce(
                                            witness["output_role"].astext
                                            + witness["records"].astext,
                                            "<NULL>",
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
            Local("definition", definition),
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "witness",
                    "output",
                    "body",
                    "record",
                    "candidate",
                    "candidates",
                    "comparison",
                    "actual",
                    "expected",
                )
            ),
            Local("complete", pg_type("bool")),
            Local("matched", pg_type("bool")),
        ),
    )

    _completion_proofs(model, output, routine, row, rf, obj, items, reject, lookup)
    _intent_settlement(model, output, routine, row, rf, obj, items, reject, lookup)
    return tuple(output)


def _completion_seal_value(rf, obj, *, payload_digest, runtime, snapshot):
    return obj(
        validators=func.ops.ddo_current_validation_identities(
            rf("release_id"), rf("operation_id"), type_=JSONB()
        ),
        request=rf("id"),
        generation=rf("generation"),
        release=rf("release_id"),
        recipe=rf("recipe"),
        runtime=runtime,
        payload=payload_digest,
        trust=snapshot,
    )


def _completion_proofs(model, output, routine, row, rf, obj, items, reject, lookup):
    tables = model.tables
    request, definition, producing_table, intent, receipt, reads = (
        tables[name]
        for name in (
            "ops.data_request",
            "sem.data_operation_definition",
            "ops.data_derivation",
            "ops.data_completion_intent",
            "ops.data_publication_receipt",
            "ops.data_demand_read",
        )
    )
    completion, payload, snapshot = (
        core_variable(name, JSONB()) for name in ("completion", "payload", "snapshot")
    )
    runtime = core_variable("runtime", Text())
    output.append(
        NativeRoutine(
            "ops",
            "ddo_completion_seal",
            parameters=(
                Parameter("r", pg_type("ops", "data_request")),
                Parameter("payload", pg_type("jsonb")),
                Parameter("runtime", pg_type("text")),
                Parameter("snapshot", pg_type("jsonb")),
            ),
            returns=pg_type("jsonb"),
            volatility="stable",
            search_path=("pg_catalog", "pg_temp"),
            body=select(
                _completion_seal_value(
                    rf,
                    obj,
                    payload_digest=func.ops.ddo_digest(payload),
                    runtime=runtime,
                    snapshot=snapshot,
                )
            ),
        )
    )
    r = rf()
    producer_task, producer_attempt = (
        core_variable(name, BigInteger()) for name in ("producer_task", "producer_attempt")
    )
    producer_holder = core_variable("producer_holder", Text())
    family_guards = {
        guard: entry.family for entry in family_programs(model) for guard in entry.guards
    }
    guards = (
        "ddo_require_external_completion",
        "ddo_require_policy_authorization_completion",
        "ddo_require_structural_admission_completion",
        "ddo_require_structural_dossier_completion",
        "ddo_assert_output_witnesses",
    )
    checks: list[Statement] = [
        Perform(
            func.ops.ddo_require_pdf_completion(
                completion,
                producer_task,
                producer_attempt,
                producer_holder,
                rf("release_id"),
                rf("operation_id"),
            )
        )
    ]
    for name in guards:
        invocation = Perform(
            getattr(func.ops, name)(completion, r, producer_task, producer_attempt, producer_holder)
            if name == "ddo_require_external_completion"
            else getattr(func.ops, name)(r, completion)
        )
        checks.append(invocation)
    typed_populations = "ops.data_retained_population" in model.tables
    population_intent = core_variable("p_population_intent", Text())
    checks.append(
        If(
            select(1)
            .select_from(definition)
            .where(
                definition.c.release_id == rf("release_id"),
                definition.c.operation_id == rf("operation_id"),
                definition.c.support_contract.has_key("reference_targets"),
            )
            .exists(),
            (
                Perform(
                    func.ops.ddo_assert_output_references(
                        r, completion, *((population_intent,) if typed_populations else ())
                    )
                ),
            ),
        )
    )
    if "sem.data_rule" in model.tables:
        checks.append(Perform(func.ops.ddo_require_rule_assertion_shape(completion)))
    completion_parameters = (
        ("r", "ops.data_request"),
        ("completion", "jsonb"),
        ("producer_task", "bigint"),
        ("producer_attempt", "bigint"),
        ("producer_holder", "text"),
        *((("p_population_intent", "text"),) if typed_populations else ()),
    )
    routine(
        "ops",
        "ddo_require_completion_invariants",
        completion_parameters,
        checks,
        stable=True,
    )
    families = core_variable("families", JSONB())
    selective = tuple(
        If(
            families.has_key(family),
            (Perform(getattr(func.ops, guard)(r, completion)),),
        )
        for guard, family in family_guards.items()
    )
    routine(
        "ops",
        "ddo_require_completion_families",
        (("r", "ops.data_request"), ("completion", "jsonb"), ("families", "jsonb")),
        selective,
        stable=True,
    )
    routine(
        "ops",
        "ddo_require_completion_correspondence",
        completion_parameters,
        (
            Perform(
                func.ops.ddo_require_completion_invariants(
                    r,
                    completion,
                    producer_task,
                    producer_attempt,
                    producer_holder,
                    *((population_intent,) if typed_populations else ()),
                )
            ),
            Perform(
                func.ops.ddo_require_completion_families(
                    r,
                    completion,
                    func.ops.ddo_current_validation_identities(
                        rf("release_id"), rf("operation_id"), type_=JSONB()
                    ),
                )
            ),
        ),
        stable=True,
    )

    def pf(field=None):
        return row("producing", producing_table, field)

    def original(field=None):
        return row("original", intent, field)

    original_payload = original("payload")
    fields = ("request_id", "generation", "producer_task_id", "producer_attempt", "runtime_id")
    restored = func.jsonb_populate_record(
        r,
        obj(
            release_id=pf("release_id"),
            runtime_id=pf("runtime_id"),
            recipe=pf("recipe"),
            generation=pf("generation"),
            binding=rf("binding").op("||")(
                obj(inputs=original_payload["inputs"], support=original_payload["support"])
            ),
        ),
    )
    routine(
        "ops",
        "ddo_require_episode_identity",
        (("producing", "ops.data_derivation"), ("original", "ops.data_completion_intent")),
        (
            lookup(
                "receipt",
                receipt,
                receipt.c.derivation_id == pf("id"),
                receipt.c.intent_id == original("id"),
            ),
            reject(
                or_(
                    pf("intent_id").is_distinct_from(original("id")),
                    tuple_(*(pf(key) for key in fields)).is_distinct_from(
                        tuple_(*(original(key) for key in fields))
                    ),
                ),
                "episode differs from its actual retained intent/producer",
                "23514",
            ),
            lookup("r", request, request.c.id == pf("request_id")),
            Assign("r", restored),
            lookup(
                "definition",
                definition,
                definition.c.release_id == rf("release_id"),
                definition.c.operation_id == rf("operation_id"),
                definition.c.recipe == rf("recipe"),
            ),
            reject(
                func.ops.ddo_completion_state(
                    row("definition", definition), original_payload["outcome"].astext
                ).is_distinct_from(pf("outcome")),
                "episode terminal state differs from admitted completion",
                "23514",
            ),
            reject(
                original("payload_digest").is_distinct_from(func.ops.ddo_digest(original_payload)),
                "historical intent payload digest differs",
                "23514",
            ),
            Perform(
                func.ops.ddo_require_completion_invariants(
                    r,
                    original_payload,
                    original("producer_task_id"),
                    original("producer_attempt"),
                    original("producer_holder"),
                    *((original("id"),) if typed_populations else ()),
                )
            ),
            Return(r),
        ),
        (Local("r", request), Local("receipt", receipt), Local("definition", definition)),
        returns="ops.data_request",
        stable=True,
    )

    episode_parameters = (
        ("producing", "ops.data_derivation"),
        ("original", "ops.data_completion_intent"),
    )

    def episode_setup():
        return (
            Assign("r", func.ops.ddo_require_episode_identity(pf(), original())),
            lookup(
                "receipt",
                receipt,
                receipt.c.derivation_id == pf("id"),
                receipt.c.intent_id == original("id"),
            ),
            Assign(
                "missing",
                func.ops.ddo_missing_validation_identities(
                    row("receipt", receipt, "id"),
                    func.ops.ddo_current_validation_identities(
                        rf("release_id"), rf("operation_id"), type_=JSONB()
                    ),
                    type_=JSONB(),
                ),
            ),
        )

    episode_locals = (
        Local("r", request),
        Local("receipt", receipt),
        Local("missing", pg_type("jsonb")),
    )
    routine(
        "ops",
        "ddo_require_episode_correspondence",
        episode_parameters,
        (
            *episode_setup(),
            Perform(
                func.ops.ddo_require_completion_families(
                    r, original_payload, core_variable("missing", JSONB())
                )
            ),
            If(
                core_variable("missing", JSONB()).has_key("conservative"),
                (
                    reject(
                        ~func.ops.ddo_conservative_dependencies_valid(pf("id"), type_=Boolean()),
                        "conservative completion trust changed",
                        "23514",
                    ),
                ),
            ),
            Return(r),
        ),
        episode_locals,
        returns="ops.data_request",
        stable=True,
    )
    for family in family_programs(model):
        if not family.guards:
            continue
        routine(
            "ops",
            "ddo_require_episode_" + family.family.replace("-", "_") + "_correspondence",
            episode_parameters,
            (
                *episode_setup(),
                If(
                    core_variable("missing", JSONB()).has_key(family.family),
                    tuple(
                        Perform(getattr(func.ops, guard)(r, original_payload))
                        for guard in family.guards
                    ),
                ),
                Return(r),
            ),
            episode_locals,
            returns="ops.data_request",
            stable=True,
        )

    selected_output, cut = core_variable("output_", JSONB()), core_variable("cut", JSONB())
    outs = items(completion["outputs"], "output_row")
    grade_cuts = func.ops.ddo_record_grade_cuts(r).table_valued(
        column("cut_text", Text()), column("cut_id", Text())
    )
    fit_selections = func.ops.ddo_record_fit_selections(r).table_valued(
        column("role_name", Text()), column("selection", JSONB())
    )
    question = func.ops.ddo_record_grade_input(r, "question", type_=JSONB())["body"]
    contextual = (
        select(1)
        .select_from(outs)
        .where(
            outs.c.value["product"]["body"].is_not(None),
            func.data.ddo_field(
                func.data.ddo_normalize(outs.c.value["product"]["body"]), "linguistic_observation"
            ).is_not_distinct_from(
                func.data.record_json_meaning(
                    func.data.record_json_source(func.ops.ddo_contextual_linguistic_context())
                )
            ),
        )
        .exists()
    )
    routine(
        "ops",
        "ddo_require_completion_live",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            Perform(func.ops.ddo_authorize_request(r)),
            Perform(func.ops.ddo_require_completion_effect_authority(r)),
            Perform(func.ops.ddo_binding_body_access(rf("binding"), rf("project_id"))),
            ForQuery(
                ("output_",),
                select(outs.c.value),
                (
                    Perform(
                        func.ops.ddo_kind_access(selected_output["product"]["kind_contract"].astext)
                    ),
                    Perform(
                        func.ops.ddo_body_access(
                            selected_output["product"]["kind_contract"].astext,
                            func.data.ddo_normalize(selected_output["product"]["body"]),
                        )
                    ),
                ),
            ),
            If(
                selected_family(model, rf("release_id"), rf("operation_id"), "record-grade"),
                (
                    ForQuery(
                        ("captured",),
                        select(grade_cuts),
                        (
                            Perform(
                                func.ops.ddo_record_grade_require_cut(
                                    rf("project_id"),
                                    core_variable("captured", Text(), "cut_text"),
                                    core_variable("captured", Text(), "cut_id"),
                                )
                            ),
                        ),
                    ),
                ),
            ),
            If(
                selected_family(model, rf("release_id"), rf("operation_id"), "record-fit"),
                (
                    ForQuery(
                        ("selected",),
                        select(fit_selections),
                        (
                            Perform(
                                func.ops.ddo_record_fit_require_selection(
                                    r,
                                    core_variable("selected", Text(), "role_name"),
                                    core_variable("selected", JSONB(), "selection"),
                                    False,
                                )
                            ),
                            lookup(
                                "boundary",
                                reads,
                                reads.c.id
                                == core_variable("selected", JSONB(), "selection")[
                                    "read_id"
                                ].astext,
                                reads.c.demand_id
                                == core_variable("selected", JSONB(), "selection")[
                                    "demand_id"
                                ].astext,
                            ),
                            Perform(
                                func.ops.ddo_require_read_current(
                                    row("boundary", reads), rf("project_id"), True
                                )
                            ),
                        ),
                    ),
                ),
            ),
            If(
                selected_family(model, rf("release_id"), rf("operation_id"), "operation-event"),
                (
                    If(
                        input_role(model, rf("release_id"), rf("operation_id"), "question"),
                        (
                            ForQuery(
                                ("cut",),
                                union(
                                    select(question["original_selection"]),
                                    select(question["prediction_selection"]),
                                ),
                                (
                                    Perform(
                                        func.ops.ddo_record_grade_require_cut(
                                            rf("project_id"),
                                            cut["cut_canonical_json"].astext,
                                            cut["cut_id"].astext,
                                        )
                                    ),
                                ),
                            ),
                        ),
                        (
                            If(
                                input_role(
                                    model, rf("release_id"), rf("operation_id"), "specification"
                                ),
                                (
                                    Assign(
                                        "cut",
                                        func.ops.ddo_record_grade_input(
                                            r, "specification", type_=JSONB()
                                        )["body"]["frame"]["selection"],
                                    ),
                                    Perform(
                                        func.ops.ddo_record_fit_cut_scopes(rf("project_id"), cut)
                                    ),
                                    lookup(
                                        "boundary",
                                        reads,
                                        reads.c.id == cut["read_id"].astext,
                                        reads.c.demand_id == cut["demand_id"].astext,
                                    ),
                                    Perform(
                                        func.ops.ddo_require_read_current(
                                            row("boundary", reads), rf("project_id"), True
                                        )
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            If(
                and_(
                    selected_family(model, rf("release_id"), rf("operation_id"), "contextual"),
                    input_role(model, rf("release_id"), rf("operation_id"), "policy"),
                    ~input_role(model, rf("release_id"), rf("operation_id"), "scores"),
                    completion["outcome"].astext == "success",
                ),
                (reject(~contextual, "contextual linguistic premises changed", "23514"),),
            ),
        ),
        (
            Local("captured", pg_type("record")),
            Local("selected", pg_type("record")),
            Local("output_", pg_type("jsonb")),
            Local("cut", pg_type("jsonb")),
            Local("boundary", reads),
        ),
        stable=True,
    )


def execution_evidence_differs(payload):
    from .data_operation_execution_evidence import NativeExecutionEvidence

    completion = payload["completion"]
    evidence = completion["execution_evidence"]
    fence = ("request_id", "generation", "task_id", "attempt", "holder", "runtime_id")
    for name in NativeExecutionEvidence.model_fields:
        if name not in fence:
            evidence = evidence.op("-")(name)
    return and_(
        completion.has_key("execution_evidence"),
        evidence.is_distinct_from(payload.op("-")("completion")),
    )


def _intent_settlement(model, output, routine, row, rf, obj, items, reject, lookup):
    from .execution_origin_native import execution_origin_programs

    execution_origin_programs(model, routine, row, rf, obj, reject, lookup)
    request, task, intent, receipt, adoption, runtime, definition = (
        model.tables[name]
        for name in (
            "ops.data_request",
            "ops.task",
            "ops.data_completion_intent",
            "ops.data_publication_receipt",
            "ops.data_intent_adoption",
            "sem.runtime_binding",
            "sem.data_operation_definition",
        )
    )
    consumptions = model.tables["ops.data_draft_consumption"]
    p = core_variable("p", JSONB())
    completion = p["completion"]
    typed_populations = "ops.data_retained_population" in model.tables
    typed_upload = core_variable("typed_population_upload", Boolean())
    inserted = core_variable("inserted_intent", BigInteger())
    snapshot, key = core_variable("snapshot", JSONB()), core_variable("key", Text())
    payload_digest = core_variable("payload_digest_", Text())
    evidence = completion["execution_evidence"]
    provider = items(
        func.coalesce(evidence["provider_receipts"], cast(literal("[]"), JSONB())),
        "provider_receipt",
    )
    logical_members = items(provider.c.value["logical_members"], "logical_member")
    invalid_members = (
        select(1)
        .select_from(logical_members)
        .where(
            or_(
                *(
                    logical_members.c.value[name].is_distinct_from(p[name])
                    for name in ("request_id", "generation", "task_id", "attempt")
                )
            )
        )
        .correlate(provider)
        .exists()
    )
    invalid_provider = (
        select(1)
        .select_from(provider)
        .where(
            or_(func.jsonb_array_length(provider.c.value["logical_members"]) == 0, invalid_members)
        )
        .exists()
    )

    def tf(field=None):
        return row("t", task, field)

    def old(field):
        return row("old", intent, field)

    canonical_completion = core_variable("canonical_completion", Text())
    intent_prefix = func.data.canonical_json(
        func.jsonb_build_array(
            rf("id"),
            rf("generation"),
            tf("id"),
            tf("attempt"),
            tf("claimed_by"),
            p["runtime_id"].astext,
        )
    )
    valid_runtime = (
        select(1)
        .select_from(runtime)
        .where(
            runtime.c.release_id == rf("release_id"),
            runtime.c.runtime_id == p["runtime_id"].astext,
            runtime.c.execution_profile == rf("binding")["execution_profile"].astext,
        )
        .exists()
    )
    valid_implementation = (
        select(1)
        .select_from(definition)
        .where(
            definition.c.release_id == rf("release_id"),
            definition.c.operation_id == rf("operation_id"),
            definition.c.implementation_revision == completion["implementation_revision"].astext,
        )
        .exists()
    )
    routine(
        "ops",
        "retain_data_completion_intent",
        (("p_payload", "jsonb"),),
        (
            Perform(
                func.ops.ddo_fields(
                    p,
                    array(
                        [
                            "request_id",
                            "generation",
                            "task_id",
                            "attempt",
                            "holder",
                            "runtime_id",
                            "completion",
                        ]
                    ),
                )
            ),
            Perform(
                func.ops.ddo_fields(
                    completion,
                    array(["outcome", "outputs", "support", "inputs", "implementation_revision"]),
                    array(["execution_evidence"]),
                )
            ),
            reject(
                execution_evidence_differs(p),
                "execution evidence differs from native producer fence/runtime",
            ),
            reject(invalid_provider, "provider logical receipt differs from native attempt"),
            lookup("r", request, request.c.id == p["request_id"].astext),
            Assign("snapshot", func.ops.ddo_lock_completion_support(rf(), completion)),
            lookup("r", request, request.c.id == rf("id"), lock=True),
            Assign("t", func.ops.ddo_claim(rf(), p)),
            Perform(func.sem.require_runtime_binding(rf("release_id"), p["runtime_id"].astext)),
            Perform(
                func.ops.ddo_require_provider_profile(
                    rf("release_id"), rf("operation_id"), p["runtime_id"].astext
                )
            ),
            reject(
                ~valid_runtime,
                "actual producer runtime execution profile differs from admitted request",
            ),
            reject(
                or_(
                    rf("generation") != cast(p["generation"].astext, request.c.generation.type),
                    completion["inputs"].is_distinct_from(rf("binding")["inputs"]),
                    completion["support"].is_distinct_from(rf("binding")["support"]),
                    ~valid_implementation,
                ),
                "completion differs from admitted request/implementation",
            ),
            Perform(func.ops.ddo_assert_support(rf(), completion["support"])),
            Perform(func.ops.ddo_require_completion_live(rf(), completion)),
            Assign("canonical_completion", func.data.canonical_json(completion)),
            # Append the already canonical final element to the canonical frame.
            Assign(
                "key",
                literal("intent:")
                + canonical_text_digest(
                    func.left(intent_prefix, -1)
                    .concat(",")
                    .concat(canonical_completion)
                    .concat("]")
                ),
            ),
            reject(
                select(1)
                .select_from(consumptions)
                .where(
                    consumptions.c.request_id == rf("id"),
                    consumptions.c.generation == rf("generation"),
                    consumptions.c.intent_id != key,
                )
                .exists(),
                "immutable consumed draft must be adopted; a generation cannot replace its answer",
            ),
            Assign("payload_digest_", canonical_text_digest(canonical_completion)),
            Sql(
                insert(intent)
                .values(
                    id=key,
                    request_id=rf("id"),
                    generation=rf("generation"),
                    producer_task_id=tf("id"),
                    producer_attempt=tf("attempt"),
                    producer_holder=tf("claimed_by"),
                    runtime_id=p["runtime_id"].astext,
                    payload=completion,
                    payload_digest=payload_digest,
                    created_at=func.clock_timestamp(),
                    validation_seal=_completion_seal_value(
                        rf,
                        obj,
                        payload_digest=payload_digest,
                        runtime=p["runtime_id"].astext,
                        snapshot=snapshot,
                    ),
                )
                .on_conflict_do_nothing()
            ),
            *((GetRowCount("inserted_intent"),) if typed_populations else ()),
            lookup(
                "old",
                intent,
                intent.c.request_id == rf("id"),
                intent.c.generation == rf("generation"),
            ),
            reject(
                old("id") != key,
                "immutable retained intent must be adopted; a generation cannot replace its answer",
            ),
            *(
                (
                    Assign("typed_population_upload", population_upload_requested(completion)),
                    If(
                        typed_upload,
                        (
                            Perform(
                                func.ops.ddo_consume_population_upload(
                                    rf(),
                                    key,
                                    completion,
                                    population_upload_fence(p, rf("release_id")),
                                    inserted == 1,
                                )
                            ),
                        ),
                    ),
                )
                if typed_populations
                else ()
            ),
            Perform(
                func.ops.ddo_require_completion_correspondence(
                    rf(),
                    completion,
                    tf("id"),
                    tf("attempt"),
                    tf("claimed_by"),
                    *((key,) if typed_populations else ()),
                )
            ),
            Return(obj(payload=obj(intent_id=key, payload_digest=old("payload_digest")))),
        ),
        (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            Local("r", request),
            Local("t", task),
            Local("snapshot", pg_type("jsonb")),
            Local("key", pg_type("text")),
            Local("canonical_completion", pg_type("text")),
            Local("payload_digest_", pg_type("text")),
            Local("old", intent),
            *(
                (
                    Local("inserted_intent", pg_type("bigint")),
                    Local("typed_population_upload", pg_type("boolean")),
                )
                if typed_populations
                else ()
            ),
        ),
        returns="jsonb",
    )

    def original(field=None):
        return row("i", intent, field)

    routine(
        "ops",
        "adopt_data_completion_intent",
        (("p_payload", "jsonb"),),
        (
            Perform(
                func.ops.ddo_fields(
                    p,
                    array(
                        ["request_id", "generation", "task_id", "attempt", "holder", "intent_id"]
                    ),
                )
            ),
            lookup("i", intent, intent.c.id == p["intent_id"].astext),
            lookup("r", request, request.c.id == p["request_id"].astext),
            Assign("snapshot", func.ops.ddo_lock_completion_support(rf(), original("payload"))),
            lookup("r", request, request.c.id == rf("id"), lock=True),
            Assign("t", func.ops.ddo_claim(rf(), p)),
            reject(
                or_(
                    original("request_id") != rf("id"),
                    rf("generation") != cast(p["generation"].astext, intent.c.generation.type),
                    ~or_(
                        original("generation") == rf("generation"),
                        select(1)
                        .select_from(consumptions)
                        .where(
                            consumptions.c.intent_id == original("id"),
                            consumptions.c.request_id == rf("id"),
                            consumptions.c.generation == rf("generation"),
                        )
                        .exists(),
                    ),
                    select(1)
                    .select_from(receipt)
                    .where(receipt.c.intent_id == original("id"))
                    .exists(),
                ),
                "only unresolved exact or natively mapped generation intent can be adopted",
            ),
            Perform(func.ops.ddo_assert_support(rf(), original("payload")["support"])),
            Perform(func.ops.ddo_require_completion_live(rf(), original("payload"))),
            Sql(
                insert(adoption)
                .values(
                    intent_id=original("id"),
                    task_id=tf("id"),
                    attempt=tf("attempt"),
                    holder=tf("claimed_by"),
                )
                .on_conflict_do_nothing()
            ),
            Return(
                obj(
                    payload=obj(
                        intent_id=original("id"),
                        producer_task_id=original("producer_task_id"),
                        producer_attempt=original("producer_attempt"),
                    )
                )
            ),
        ),
        (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            Local("r", request),
            Local("t", task),
            Local("i", intent),
            Local("snapshot", pg_type("jsonb")),
        ),
        returns="jsonb",
    )


def completion_settlement_native_sql(model: MetaData) -> str:
    return (
        native_sql_script(item.render() for item in completion_settlement_native_programs(model))
        + "\n"
    )
