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

from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    Exit,
    ForQuery,
    If,
    Local,
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
    function,
    pg_type,
    sql_function,
)

# The captured program participates in the kernel digest. Its self-reference is
# bound by the existing captured-kernel realization after the source is frozen.
_KERNEL = "__DDO_SOURCE_DIGEST__"


def completion_settlement_native_sql(model: MetaData) -> str:
    output = []
    tables = model.tables
    request, definition, product, member = (
        tables[name] for name in ("ops.data_request", "sem.data_operation_definition", "kb.data_product", "kb.data_product_member"))

    def row(name, relation, field=None):
        return core_variable(name, JSONB() if field is None else relation.c[field].type, field)

    def rf(field=None):
        return row("r", request, field)

    def obj(**fields):
        return func.jsonb_build_object(*(part for key, value in fields.items() for part in (key, value)), type_=JSONB())

    def items(value, name):
        return func.jsonb_array_elements(value).table_valued(column("value", JSONB())).render_derived(name=name)

    empty, json_null = cast(literal("[]"), JSONB()), cast(literal("null"), JSONB())

    def reject(condition, message, state="P0001"):
        return If(condition, (Raise(message, state),))

    def lookup(name, relation, *conditions, lock=False):
        query = select(core_relation_row(relation)).select_from(relation).where(*conditions)
        return SelectInto(query.with_for_update() if lock else query, (name,), strict=True)

    def routine(schema, name, params, body, locals_=(), *, returns="void", stable=False, immutable=False, strict=False, definer=True, setof=False):
        result = pg_type(*returns.split("."))
        result.setof = setof
        output.append(function(schema, name,
            parameters=tuple(Parameter(key, pg_type(*kind.split("."))) for key, kind in params), returns=result,
            body=Block(tuple(body), tuple(locals_)), strict=strict,
            volatility="immutable" if immutable else "stable" if stable else None,
            security_definer=definer, search_path=("pg_catalog", "pg_temp")))

    pointer = core_variable("pointer", Text())
    path_items = func.unnest(func.string_to_array(case((func.left(pointer, 1) == "/", func.substr(pointer, 2)), else_=pointer), "/")).table_valued(
        column("value", Text()), with_ordinality="ordinality").render_derived(name="path_item")
    decoded = func.replace(func.replace(path_items.c.value, "~1", "/"), "~0", "~")
    paths = func.coalesce(func.array_agg(decoded).aggregate_order_by(path_items.c.ordinality), cast(array([]), ARRAY(Text())))
    # The ordered aggregate is the native ARRAY subquery's typed equivalent.
    path_type = pg_type("text")
    path_type.arrayBounds = (ast.Integer(ival=-1),)
    output.append(sql_function("data", "ddo_witness_path", parameters=(Parameter("pointer", pg_type("text")),), returns=path_type,
        body=select(case((pointer == "", cast(array([]), ARRAY(Text()))), else_=select(paths).select_from(path_items).scalar_subquery())),
        strict=True, volatility="immutable", search_path=("pg_catalog", "pg_temp")))
    body, current, following, item = (core_variable(name, JSONB()) for name in ("body", "current_values", "following", "item"))
    part = core_variable("part", Text())
    parts = func.unnest(func.data.ddo_witness_path(pointer)).table_valued(column("value", Text()), with_ordinality="ordinality").render_derived(name="part")
    values = items(current, "current_item")
    routine("data", "ddo_witness_records", (("body", "jsonb"), ("pointer", "text")), (
        ForQuery(("part",), select(parts.c.value).order_by(parts.c.ordinality), (
            Assign("following", empty),
            ForQuery(("item",), select(values.c.value), (
                If(part == "*", (
                    reject(func.jsonb_typeof(item) != "array", "output witness member step requires an array"), Assign("following", following.op("||")(item)),
                ), (
                    reject(func.jsonb_typeof(item) != "object", "output witness property step requires a record"),
                    If(and_(item.bool_op("?")(part), item[part] != json_null), (Assign("following", following.op("||")(func.jsonb_build_array(item[part]))),)),
                )),
            )), Assign("current_values", following),
        )), ReturnQuery(select(values.c.value)),
    ), (Local("current_values", pg_type("jsonb"), func.jsonb_build_array(body)), Local("following", pg_type("jsonb")), Local("part", pg_type("text")), Local("item", pg_type("jsonb"))),
        returns="jsonb", immutable=True, strict=True, definer=False, setof=True)

    completion, witness, selected_output, decoded_body, record_, candidate, candidates, comparison, actual, expected = (
        core_variable(name, JSONB()) for name in ("completion", "witness", "output", "body", "record", "candidate", "candidates", "comparison", "actual", "expected"))
    complete, matched = core_variable("complete", Boolean()), core_variable("matched", Boolean())
    contract = row("definition", definition, "support_contract")
    witnesses = items(func.coalesce(contract["output_witnesses"], empty), "witness_row")
    inputs = items(rf("binding")["inputs"], "input_row")
    candidate_value = obj(product=product.c.id, member=member.c.member_id, reference=func.jsonb_build_array(product.c.id, member.c.member_id),
        kind_contract=func.coalesce(member.c.kind_contract, product.c.kind_contract), project_id=product.c.project_id,
        **{name: func.coalesce(member.c[name], product.c[name]) for name in ("subject", "subject_definition", "original_source", "analyzed_scope")},
        body=func.data.ddo_json(func.coalesce(member.c.body, product.c.canonical_body)))
    candidate_query = select(func.coalesce(func.jsonb_agg(candidate_value), empty)).select_from(inputs.join(product, product.c.id == inputs.c.value["product_id"].astext).outerjoin(
        member, and_(member.c.product_id == product.c.id, member.c.member_id == inputs.c.value["member_id"].astext))).where(
            inputs.c.value["role"].astext == witness["input_role"].astext, or_(inputs.c.value["member_id"].astext.is_(None), member.c.member_id.is_not(None)))
    outputs, members = items(completion["outputs"], "output_row"), items(selected_output["product"]["members"], "member_row")
    records = func.data.ddo_witness_records(func.data.ddo_json(func.data.ddo_normalize(decoded_body)), witness["records"].astext).table_valued(column("value", JSONB())).render_derived(name="record_row")
    candidate_rows, comparisons = items(candidates, "candidate_row"), items(witness["comparisons"], "comparison_row")
    projection, field = comparison["input"]["projection"].astext, comparison["input"]["field"].astext
    incomplete = (Assign("complete", literal(False)), Exit())
    routine("ops", "ddo_assert_output_witnesses", (("r", "ops.data_request"), ("completion", "jsonb")), (
        lookup("definition", definition, definition.c.release_id == rf("release_id"), definition.c.operation_id == rf("operation_id")),
        If(func.jsonb_array_length(func.coalesce(contract["output_witnesses"], empty)) > 0, (Perform(func.ops.ddo_binding_body_access(rf("binding"), rf("project_id"))),)),
        ForQuery(("witness",), select(witnesses.c.value), (
            SelectInto(candidate_query, ("candidates",)),
            ForQuery(("output",), select(outputs.c.value).where(outputs.c.value["role"].astext == witness["output_role"].astext), (
                Assign("body", selected_output["product"]["body"]),
                If(selected_output["member_id"].astext.is_not(None), (SelectInto(select(members.c.value["body"]).where(members.c.value["member_id"].astext == selected_output["member_id"].astext), ("body",), strict=True),)),
                ForQuery(("record",), select(records.c.value), (
                    Assign("matched", literal(False)),
                    ForQuery(("candidate",), select(candidate_rows.c.value), (
                        Assign("complete", literal(True)),
                        ForQuery(("comparison",), select(comparisons.c.value), (
                            Assign("actual", func.coalesce(record_.op("#>", return_type=JSONB())(func.data.ddo_witness_path(comparison["output_field"].astext)), json_null)),
                            If(projection == "selected-input", (Assign("expected", candidate[field]),),
                                (Assign("expected", func.coalesce(candidate["body"].op("#>", return_type=JSONB())(func.data.ddo_witness_path(field)), json_null)),)),
                            If(and_(func.coalesce(expected, json_null) == json_null, comparison["encoding"].astext == "value",
                                ~and_(projection == "selected-input", field == "member")), incomplete),
                            If(comparison["encoding"].astext != "value", (
                                If(func.jsonb_typeof(actual) != "string", incomplete),
                                Assign("actual", cast(actual.op("#>>", return_type=Text())(array([], type_=Text())), JSONB())),
                            )),
                            If(comparison["encoding"].astext == "context-meaning-json", (Assign("expected", func.data.ddo_json_meaning(expected)),)),
                            If(actual.is_distinct_from(expected), incomplete),
                        )), If(complete, (Assign("matched", literal(True)), Exit())),
                    )), reject(~matched, literal("output witness has no complete selected input member: ") + func.coalesce(witness["output_role"].astext + witness["records"].astext, "<NULL>")),
                )),
            )),
        )),
    ), (Local("definition", definition), *(Local(name, pg_type("jsonb")) for name in ("witness", "output", "body", "record", "candidate", "candidates", "comparison", "actual", "expected")),
        Local("complete", pg_type("bool")), Local("matched", pg_type("bool"))))

    _completion_proofs(model, output, routine, row, rf, obj, items, reject, lookup)
    _intent_settlement(model, output, routine, row, rf, obj, items, reject, lookup)
    return native_sql_script(output) + "\n"


def _completion_proofs(model, output, routine, row, rf, obj, items, reject, lookup):
    tables = model.tables
    request, definition, producing_table, intent, receipt, reads = (tables[name] for name in (
        "ops.data_request", "sem.data_operation_definition", "ops.data_derivation", "ops.data_completion_intent", "ops.data_publication_receipt", "ops.data_demand_read"))
    completion, payload, snapshot = (core_variable(name, JSONB()) for name in ("completion", "payload", "snapshot"))
    runtime = core_variable("runtime", Text())
    output.append(sql_function("ops", "ddo_completion_seal", parameters=(Parameter("r", pg_type("ops", "data_request")),
        Parameter("payload", pg_type("jsonb")), Parameter("runtime", pg_type("text")), Parameter("snapshot", pg_type("jsonb"))),
        returns=pg_type("jsonb"), volatility="immutable", search_path=("pg_catalog", "pg_temp"), body=select(obj(
            kernel=_KERNEL, request=rf("id"), generation=rf("generation"), release=rf("release_id"), recipe=rf("recipe"),
            runtime=runtime, payload=func.ops.ddo_digest(payload), trust=snapshot))))
    r = rf()
    producer_task, producer_attempt = (core_variable(name, BigInteger()) for name in ("producer_task", "producer_attempt"))
    producer_holder = core_variable("producer_holder", Text())
    guards = (
        "ddo_require_external_completion", "ddo_require_record_grade_completion", "ddo_require_record_fit_completion",
        "ddo_require_operation_event_completion", "ddo_require_policy_authorization_completion", "ddo_require_structural_admission_completion",
        "ddo_require_structural_dossier_completion", "ddo_require_definition_completion", "ddo_require_artifact_completion",
        "ddo_require_contextual_completion", "ddo_require_rich_preparation_completion", "ddo_require_rich_admission_completion",
        "ddo_require_product_validations", "ddo_assert_output_witnesses",
    )
    checks: list[Statement] = [Perform(func.ops.ddo_require_pdf_completion(completion, producer_task, producer_attempt, producer_holder, rf("release_id"), rf("operation_id")))]
    for name in guards:
        if name == "ddo_require_operation_event_completion":
            checks.append(If(rf("operation_id").in_(("operation_event.frame", "operation_event.fit", "operation_event.authorize")), (Perform(func.ops.ddo_authorize("evaluator")),)))
        checks.append(Perform(getattr(func.ops, name)(completion, r, producer_task, producer_attempt, producer_holder) if name == "ddo_require_external_completion" else getattr(func.ops, name)(r, completion)))
    routine("ops", "ddo_require_completion_correspondence", (("r", "ops.data_request"), ("completion", "jsonb"), ("producer_task", "bigint"), ("producer_attempt", "bigint"), ("producer_holder", "text")), checks, stable=True)

    def pf(field=None):
        return row("producing", producing_table, field)

    def original(field=None):
        return row("original", intent, field)

    original_payload = original("payload")
    fields = ("request_id", "generation", "producer_task_id", "producer_attempt", "runtime_id")
    restored = func.jsonb_populate_record(r, obj(release_id=pf("release_id"), runtime_id=pf("runtime_id"), recipe=pf("recipe"), generation=pf("generation"),
        binding=rf("binding").op("||")(obj(inputs=original_payload["inputs"], support=original_payload["support"]))))
    routine("ops", "ddo_require_episode_correspondence", (("producing", "ops.data_derivation"), ("original", "ops.data_completion_intent")), (
        lookup("receipt", receipt, receipt.c.derivation_id == pf("id"), receipt.c.intent_id == original("id")),
        reject(or_(pf("intent_id").is_distinct_from(original("id")), tuple_(*(pf(key) for key in fields)).is_distinct_from(tuple_(*(original(key) for key in fields)))),
            "episode differs from its actual retained intent/producer", "23514"),
        lookup("r", request, request.c.id == pf("request_id")), Assign("r", restored),
        lookup("definition", definition, definition.c.release_id == rf("release_id"), definition.c.operation_id == rf("operation_id"), definition.c.recipe == rf("recipe")),
        reject(func.ops.ddo_completion_state(row("definition", definition), original_payload["outcome"].astext).is_distinct_from(pf("outcome")),
            "episode terminal state differs from admitted completion", "23514"),
        If(row("receipt", receipt, "validating_kernel_digest").is_distinct_from(_KERNEL), (
            reject(original("payload_digest").is_distinct_from(func.ops.ddo_digest(original_payload)), "historical intent payload digest differs", "23514"),
            Perform(func.ops.ddo_require_completion_correspondence(r, original_payload, original("producer_task_id"), original("producer_attempt"), original("producer_holder"))),
        )), Return(r),
    ), (Local("r", request), Local("receipt", receipt), Local("definition", definition)), returns="ops.data_request", stable=True)

    selected_output, cut = core_variable("output_", JSONB()), core_variable("cut", JSONB())
    outs = items(completion["outputs"], "output_row")
    grade_cuts = func.ops.ddo_record_grade_cuts(r).table_valued(column("cut_text", Text()), column("cut_id", Text()))
    fit_selections = func.ops.ddo_record_fit_selections(r).table_valued(column("role_name", Text()), column("selection", JSONB()))
    question = func.ops.ddo_record_grade_input(r, "question", type_=JSONB())["body"]
    contextual = select(1).select_from(outs).where(
        outs.c.value["product"]["body"].is_not(None), func.data.ddo_field(func.data.ddo_normalize(outs.c.value["product"]["body"]), "linguistic_observation").is_not_distinct_from(
            func.data.record_json_meaning(func.data.record_json_source(func.ops.ddo_contextual_linguistic_context())))).exists()
    routine("ops", "ddo_require_completion_live", (("r", "ops.data_request"), ("completion", "jsonb")), (
        Perform(func.ops.ddo_authorize_request(r)), Perform(func.ops.ddo_binding_body_access(rf("binding"), rf("project_id"))),
        ForQuery(("output_",), select(outs.c.value), (
            Perform(func.ops.ddo_kind_access(selected_output["product"]["kind_contract"].astext)),
            Perform(func.ops.ddo_body_access(selected_output["product"]["kind_contract"].astext, func.data.ddo_normalize(selected_output["product"]["body"]))),
        )),
        If(rf("operation_id") == "record_policy.grade", (
            ForQuery(("captured",), select(grade_cuts), (Perform(func.ops.ddo_record_grade_require_cut(rf("project_id"), core_variable("captured", Text(), "cut_text"), core_variable("captured", Text(), "cut_id"))),)),
        ), (If(rf("operation_id") == "record_policy.fit", (
            ForQuery(("selected",), select(fit_selections), (Perform(func.ops.ddo_record_fit_require_selection(r, core_variable("selected", Text(), "role_name"), core_variable("selected", JSONB(), "selection"), False)),)),
        ), (If(rf("operation_id") == "operation_event.frame", (
            ForQuery(("cut",), union(select(question["original_selection"]), select(question["prediction_selection"])), (
                Perform(func.ops.ddo_record_grade_require_cut(rf("project_id"), cut["cut_canonical_json"].astext, cut["cut_id"].astext)),)),
        ), (If(rf("operation_id") == "operation_event.fit", (
            Assign("cut", func.ops.ddo_record_grade_input(r, "specification", type_=JSONB())["body"]["frame"]["selection"]),
            Perform(func.ops.ddo_record_fit_cut_scopes(rf("project_id"), cut)),
            lookup("boundary", reads, reads.c.id == cut["read_id"].astext, reads.c.demand_id == cut["demand_id"].astext),
            Perform(func.ops.ddo_require_read_current(row("boundary", reads), rf("project_id"), True)),
        ), (If(and_(rf("operation_id") == "retrieve.contextual_scores/declared", completion["outcome"].astext == "success"), (
            reject(~contextual, "contextual linguistic premises changed", "23514"),
        )),)),)),)),)),
    ), (Local("captured", pg_type("record")), Local("selected", pg_type("record")), Local("output_", pg_type("jsonb")), Local("cut", pg_type("jsonb")), Local("boundary", reads)), stable=True)


def _intent_settlement(model, output, routine, row, rf, obj, items, reject, lookup):
    request, task, intent, receipt, adoption, runtime, definition = (model.tables[name] for name in (
        "ops.data_request", "ops.task", "ops.data_completion_intent", "ops.data_publication_receipt", "ops.data_intent_adoption", "sem.runtime_binding", "sem.data_operation_definition"))
    p = core_variable("p", JSONB())
    completion = p["completion"]
    snapshot, key = core_variable("snapshot", JSONB()), core_variable("key", Text())
    evidence = completion["execution_evidence"]
    private_fields = ("version", "host_receipts", "cpu_receipts", "cpu_replies", "pdf_receipts", "pdf_observation_receipts", "provider_receipts", "external_receipts", "product_validations")
    remaining = evidence
    for name in private_fields:
        remaining = remaining.op("-")(name)
    provider = items(func.coalesce(evidence["provider_receipts"], cast(literal("[]"), JSONB())), "provider_receipt")
    logical_members = items(provider.c.value["logical_members"], "logical_member")
    invalid_members = select(1).select_from(logical_members).where(or_(*(logical_members.c.value[name].is_distinct_from(p[name]) for name in ("request_id", "generation", "task_id", "attempt")))).correlate(provider).exists()
    invalid_provider = select(1).select_from(provider).where(or_(func.jsonb_array_length(provider.c.value["logical_members"]) == 0, invalid_members)).exists()
    def tf(field=None):
        return row("t", task, field)
    def old(field):
        return row("old", intent, field)
    valid_runtime = select(1).select_from(runtime).where(runtime.c.release_id == rf("release_id"), runtime.c.runtime_id == p["runtime_id"].astext,
        runtime.c.execution_profile == rf("binding")["execution_profile"].astext).exists()
    valid_implementation = select(1).select_from(definition).where(definition.c.release_id == rf("release_id"), definition.c.operation_id == rf("operation_id"),
        definition.c.implementation_revision == completion["implementation_revision"].astext).exists()
    routine("ops", "retain_data_completion_intent", (("p_payload", "jsonb"),), (
        Perform(func.ops.ddo_fields(p, array(["request_id", "generation", "task_id", "attempt", "holder", "runtime_id", "completion"]))),
        Perform(func.ops.ddo_fields(completion, array(["outcome", "outputs", "support", "inputs", "implementation_revision"]), array(["execution_evidence"]))),
        reject(and_(completion.bool_op("?")("execution_evidence"), remaining.is_distinct_from(p.op("-")("completion"))), "execution evidence differs from native producer fence/runtime"),
        reject(invalid_provider, "provider logical receipt differs from native attempt"),
        lookup("r", request, request.c.id == p["request_id"].astext), Assign("snapshot", func.ops.ddo_lock_completion_support(rf(), completion)),
        lookup("r", request, request.c.id == rf("id"), lock=True), Assign("t", func.ops.ddo_claim(rf(), p)),
        Perform(func.sem.require_runtime_binding(rf("release_id"), p["runtime_id"].astext)),
        Perform(func.ops.ddo_require_provider_profile(rf("release_id"), rf("operation_id"), p["runtime_id"].astext)),
        reject(~valid_runtime, "actual producer runtime execution profile differs from admitted request"),
        reject(or_(rf("generation") != cast(p["generation"].astext, request.c.generation.type), completion["inputs"].is_distinct_from(rf("binding")["inputs"]),
            completion["support"].is_distinct_from(rf("binding")["support"]), ~valid_implementation), "completion differs from admitted request/implementation"),
        Perform(func.ops.ddo_assert_support(rf(), completion["support"])),
        Perform(func.ops.ddo_require_completion_correspondence(rf(), completion, tf("id"), tf("attempt"), tf("claimed_by"))),
        Perform(func.ops.ddo_require_completion_live(rf(), completion)),
        Assign("key", literal("intent:") + func.ops.ddo_digest(func.jsonb_build_array(rf("id"), rf("generation"), tf("id"), tf("attempt"), tf("claimed_by"), p["runtime_id"].astext, completion))),
        Sql(insert(intent).values(id=key, request_id=rf("id"), generation=rf("generation"), producer_task_id=tf("id"), producer_attempt=tf("attempt"), producer_holder=tf("claimed_by"),
            runtime_id=p["runtime_id"].astext, payload=completion, payload_digest=func.ops.ddo_digest(completion), created_at=func.clock_timestamp(),
            validation_seal=func.ops.ddo_completion_seal(rf(), completion, p["runtime_id"].astext, snapshot)).on_conflict_do_nothing()),
        lookup("old", intent, intent.c.request_id == rf("id"), intent.c.generation == rf("generation")),
        reject(old("id") != key, "immutable retained intent must be adopted; a generation cannot replace its answer"),
        Return(obj(payload=obj(intent_id=key, payload_digest=old("payload_digest")))),
    ), (Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())), Local("r", request), Local("t", task), Local("snapshot", pg_type("jsonb")), Local("key", pg_type("text")), Local("old", intent)), returns="jsonb")

    def original(field=None):
        return row("i", intent, field)
    routine("ops", "adopt_data_completion_intent", (("p_payload", "jsonb"),), (
        Perform(func.ops.ddo_fields(p, array(["request_id", "generation", "task_id", "attempt", "holder", "intent_id"]))),
        lookup("i", intent, intent.c.id == p["intent_id"].astext), lookup("r", request, request.c.id == p["request_id"].astext),
        Assign("snapshot", func.ops.ddo_lock_completion_support(rf(), original("payload"))),
        lookup("r", request, request.c.id == rf("id"), lock=True), Assign("t", func.ops.ddo_claim(rf(), p)),
        reject(or_(original("request_id") != rf("id"), original("generation") != rf("generation"), original("generation") != cast(p["generation"].astext, intent.c.generation.type),
            select(1).select_from(receipt).where(receipt.c.intent_id == original("id")).exists()), "only unresolved exact generation intent can be adopted"),
        Perform(func.ops.ddo_assert_support(rf(), original("payload")["support"])),
        Sql(insert(adoption).values(intent_id=original("id"), task_id=tf("id"), attempt=tf("attempt"), holder=tf("claimed_by")).on_conflict_do_nothing()),
        Return(obj(payload=obj(intent_id=original("id"), producer_task_id=original("producer_task_id"), producer_attempt=original("producer_attempt")))),
    ), (Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())), Local("r", request), Local("t", task), Local("i", intent), Local("snapshot", pg_type("jsonb"))), returns="jsonb")
