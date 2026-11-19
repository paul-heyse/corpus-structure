"""Compile retired attempt retention with exact D1 source and provider custody."""

import json

import yaml
from sqlalchemy import (
    Boolean,
    Integer,
    Text,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, array, insert

from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    core_variable,
    pg_type,
)


def attempt_release_native_programs(
    target, protocol: bytes, evidence_schema: bytes
) -> tuple[NativeRoutine, ...]:
    definitions = yaml.safe_load(protocol)["definitions"]
    contract = definitions["release_data_attempt_request"]
    failure_contract = definitions["attempt_failure"]
    d1_contract = definitions["d1_known_limitation"]
    reply_contract = definitions["d1_limitation_reply"]["oneOf"]
    question_limit = next(
        item["properties"]["limit"]["enum"][0]
        for item in reply_contract
        if item["properties"]["reason"].get("const") == "question_count"
    )
    packed_questions = next(
        item["properties"]["row_tokens"]
        for item in reply_contract
        if item["properties"]["reason"].get("const") == "packed_row_tokens"
    )
    request = target.tables["ops.data_request"]
    task = target.tables["ops.task"]
    failures = target.tables["ops.data_attempt_failure"]
    intents = target.tables["ops.data_completion_intent"]
    consumptions = target.tables["ops.data_draft_consumption"]
    products = target.tables["kb.data_product"]
    members = target.tables["kb.data_product_member"]
    p = core_variable("p", JSONB())
    r = core_variable("r", Text())
    diagnostic = core_variable("diagnostic", JSONB())
    evidence = core_variable("evidence", JSONB())
    question_request = core_variable("question_request", JSONB())
    key = core_variable("key", failures.c.id.type)
    retained = core_variable("retained", intents.c.id.type)
    replayed = core_variable("replayed", Boolean())
    failure = p["failure"]
    source_pin = diagnostic["source_pin"]
    native_reply = diagnostic["native_reply"]
    batch = native_reply["batch_receipt"]
    object_ = func.pg_catalog.jsonb_build_object

    def field(variable, relation, name):
        return core_variable(variable, relation.c[name].type, name)

    def rf(name):
        return field("r", request, name)

    def tf(name):
        return field("t", task, name)

    def old(name):
        return field("old", failures, name)

    def rows(value, name):
        return (
            func.pg_catalog.jsonb_array_elements(value)
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
        )

    def omit(value, names):
        return value.op("-", return_type=JSONB())(array(list(names), type_=Text()))

    def refuse(condition, message, state="P0001"):
        return If(condition, (Raise(message, state),))

    inputs = rows(rf("binding")["inputs"], "source_input")
    input_ = inputs.c.value
    receipts = rows(evidence["provider_receipts"], "provider_receipt")
    receipt = receipts.c.value
    logical = rows(receipt["logical_members"], "logical_member")
    logical_member = logical.c.value
    physicals = rows(receipt["physical"], "physical_receipt")
    physical = physicals.c.value
    questions = (
        func.pg_catalog.jsonb_object_keys(question_request["questions"])
        .table_valued("key")
        .alias("question_key")
    )
    question_count = select(func.count()).select_from(questions).scalar_subquery()
    generation = cast(p["generation"].astext, Integer())
    attempt = cast(p["attempt"].astext, Integer())
    task_id = cast(p["task_id"].astext, task.c.id.type)
    holder = p["holder"].astext
    fence = tuple_(generation, task_id, attempt, holder)
    fence_fields = tuple(
        name for name in contract["properties"] if name not in {"physical_retirement", "failure"}
    )
    evidence_fields = tuple(
        name for name in json.loads(evidence_schema)["properties"] if name not in fence_fields
    )
    d1_mismatch = or_(
        ~rf("operation_id").in_(
            ("text.d1_source/source-native", "text.d1_candidates/source-native")
        ),
        failure["code"].astext.is_distinct_from("d1-known-limitation"),
        func.octet_length(diagnostic["request_json"].astext)
        > d1_contract["properties"]["request_json"]["maxLength"],
        func.pg_catalog.encode(
            func.pg_catalog.sha256(
                func.pg_catalog.convert_to(diagnostic["request_json"].astext, "UTF8")
            ),
            "hex",
        ).is_distinct_from(diagnostic["request_digest"].astext),
        question_request["interpretation"]["assessed_scope"]["pin"].is_distinct_from(source_pin),
        func.jsonb_typeof(question_request["questions"]).is_distinct_from("object"),
        (native_reply["reason"].astext == "question_count") & (question_count <= question_limit),
        (native_reply["reason"].astext == "packed_row_tokens")
        & ~question_count.between(packed_questions["minItems"], packed_questions["maxItems"]),
        tuple_(
            source_pin["project_id"].astext,
            source_pin["subject"].astext,
            source_pin["original_source"].astext,
        ).is_distinct_from(tuple_(rf("project_id"), rf("subject"), rf("original_source"))),
        source_pin["analyzed_scope_meaning"].astext.is_distinct_from(
            func.data.canonical_json(func.data.ddo_json_meaning(rf("analyzed_scope")))
        ),
        ~exists(
            select(1)
            .select_from(
                inputs.join(products, products.c.id == input_["product_id"].astext).outerjoin(
                    members,
                    (members.c.product_id == products.c.id)
                    & (members.c.member_id == input_["member_id"].astext),
                )
            )
            .where(
                input_["role"].astext == "source",
                products.c.id == source_pin["source_product"].astext,
                input_["member_id"].astext.is_not_distinct_from(source_pin["source_member"].astext),
                func.coalesce(members.c.kind_contract, products.c.kind_contract)
                == source_pin["kind_contract"].astext,
                func.coalesce(members.c.subject_definition, products.c.subject_definition)
                == source_pin["subject_definition"].astext,
            )
        ),
        omit(evidence, evidence_fields).is_distinct_from(
            omit(p, ("physical_retirement", "failure"))
        ),
        func.jsonb_array_length(evidence["provider_receipts"]) != 1,
        exists(
            select(1)
            .select_from(receipts)
            .where(
                or_(
                    func.jsonb_array_length(receipt["logical_members"]) == 0,
                    func.jsonb_array_length(receipt["physical"]) == 0,
                    receipt["cohort_members"].is_distinct_from(batch["members"]),
                    ~receipt["native_member_digests"].has_key(diagnostic["request_digest"].astext),
                    batch["members"]
                    .op("->>", return_type=Text())(cast(batch["member_ordinal"].astext, Integer()))
                    .is_distinct_from(diagnostic["request_digest"].astext),
                    exists(
                        select(1)
                        .select_from(logical)
                        .where(
                            tuple_(
                                *(
                                    logical_member[name]
                                    for name in ("request_id", "generation", "task_id", "attempt")
                                )
                            ).is_distinct_from(
                                tuple_(
                                    *(
                                        p[name]
                                        for name in (
                                            "request_id",
                                            "generation",
                                            "task_id",
                                            "attempt",
                                        )
                                    )
                                )
                            )
                        )
                    ),
                    exists(
                        select(1)
                        .select_from(physicals)
                        .where(
                            or_(
                                physical["provider"].astext != "d1",
                                physical["profile"].astext.is_distinct_from(
                                    diagnostic["profile_digest"].astext
                                ),
                                physical["runtime"].is_distinct_from(batch["header"]["runtime"]),
                            )
                        )
                    ),
                )
            )
        ),
    )
    retained_failure = case(
        (
            failure.has_key("d1_limitation"),
            omit(failure, ("d1_limitation",)).op("||", return_type=JSONB())(
                object_("d1_limitation_disclosure", "undisclosed")
            ),
        ),
        else_=failure,
    )
    new_failure = (
        If(
            ~func.ops.ddo_request_useful(r, type_=Boolean()),
            (Return(func.ops.ddo_lost_attempt(p, "cancelled")),),
        ),
        SelectInto(select(task).where(task.c.id == rf("live_task_id")).with_for_update(), ("t",)),
        If(
            or_(
                tf("id").is_(None),
                rf("generation").is_distinct_from(generation),
                tuple_(
                    tf("data_request_id"),
                    tf("data_generation"),
                    tf("id"),
                    tf("attempt"),
                    tf("claimed_by"),
                ).is_distinct_from(tuple_(rf("id"), rf("generation"), task_id, attempt, holder)),
                tf("status").is_distinct_from("running"),
            ),
            (Return(func.ops.ddo_lost_attempt(p, "fence")),),
        ),
        Assign("key", literal("attempt-failure:").concat(func.ops.ddo_digest(p))),
        Sql(
            insert(failures).values(
                id=key,
                request_id=rf("id"),
                generation=rf("generation"),
                task_id=tf("id"),
                attempt=tf("attempt"),
                holder=tf("claimed_by"),
                failure=failure,
                created_at=func.clock_timestamp(),
                created_xid=cast(func.pg_current_xact_id(), failures.c.created_xid.type),
            )
        ),
        Sql(
            update(task)
            .where(task.c.id == tf("id"))
            .values(
                status="pending",
                lease_until=None,
                finished_at=None,
                error=object_("data_attempt_failure", key, "failure", retained_failure),
            )
        ),
    )
    return (
        NativeRoutine(
            "ops",
            "release_data_attempt",
            parameters=(Parameter("p_payload", pg_type("jsonb")),),
            returns=pg_type("jsonb"),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                (
                    Perform(
                        func.ops.ddo_fields(
                            p,
                            array(contract["required"], type_=Text()),
                            array(
                                [
                                    name
                                    for name in contract["properties"]
                                    if name not in contract["required"]
                                ],
                                type_=Text(),
                            ),
                        )
                    ),
                    Perform(
                        func.ops.ddo_fields(
                            failure,
                            array(failure_contract["required"], type_=Text()),
                            array(
                                [
                                    name
                                    for name in failure_contract["properties"]
                                    if name not in failure_contract["required"]
                                ],
                                type_=Text(),
                            ),
                        )
                    ),
                    refuse(
                        or_(
                            p["physical_retirement"].astext.is_distinct_from("confirmed"),
                            func.nullif(holder, "").is_(None),
                            func.nullif(failure["code"].astext, "").is_(None),
                            func.nullif(failure["message"].astext, "").is_(None),
                            generation < 1,
                            attempt < 1,
                            task_id < 1,
                        ),
                        "attempt release requires exact known retirement/failure",
                    ),
                    SelectInto(
                        select(request).where(request.c.id == p["request_id"].astext),
                        ("r",),
                        strict=True,
                    ),
                    Perform(func.ops.ddo_authorize_request(r)),
                    If(
                        failure.has_key("d1_limitation"),
                        (
                            Assign("diagnostic", failure["d1_limitation"]),
                            Assign("evidence", diagnostic["execution_evidence"]),
                            Assign(
                                "question_request", cast(diagnostic["request_json"].astext, JSONB())
                            ),
                            refuse(
                                d1_mismatch,
                                "D1 limitation differs from its exact source/attempt/provider custody",
                                "23514",
                            ),
                            Perform(
                                func.sem.require_runtime_binding(
                                    rf("release_id"), evidence["runtime_id"].astext
                                )
                            ),
                            Perform(
                                func.ops.ddo_require_provider_profile(
                                    rf("release_id"),
                                    rf("operation_id"),
                                    evidence["runtime_id"].astext,
                                )
                            ),
                        ),
                    ),
                    Perform(
                        func.ops.ddo_lock_support(
                            rf("project_id"), rf("original_source"), rf("binding")["support"]
                        )
                    ),
                    SelectInto(
                        select(request).where(request.c.id == rf("id")).with_for_update(),
                        ("r",),
                        strict=True,
                    ),
                    SelectInto(
                        select(failures).where(
                            failures.c.request_id == rf("id"),
                            tuple_(
                                failures.c.generation,
                                failures.c.task_id,
                                failures.c.attempt,
                                failures.c.holder,
                            )
                            == fence,
                        ),
                        ("old",),
                    ),
                    If(
                        old("id").is_not(None),
                        (
                            refuse(
                                old("failure").is_distinct_from(failure),
                                "immutable attempt failure cannot change",
                            ),
                            Assign("key", old("id")),
                            Assign("replayed", literal(True)),
                        ),
                        new_failure,
                    ),
                    SelectInto(
                        select(intents.c.id).where(
                            intents.c.request_id == rf("id"),
                            or_(
                                intents.c.generation == generation,
                                select(1)
                                .select_from(consumptions)
                                .where(
                                    consumptions.c.intent_id == intents.c.id,
                                    consumptions.c.request_id == rf("id"),
                                    consumptions.c.generation == generation,
                                )
                                .exists(),
                            ),
                        ),
                        ("retained",),
                    ),
                    Return(
                        object_(
                            "payload",
                            object_(
                                "state",
                                "released",
                                "request_id",
                                rf("id"),
                                "generation",
                                generation,
                                "task_id",
                                task_id,
                                "attempt",
                                attempt,
                                "holder",
                                holder,
                                "failure_id",
                                key,
                                "replayed",
                                replayed,
                                "retained_intent_id",
                                retained,
                            ),
                        )
                    ),
                ),
                (
                    Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
                    Local("r", request),
                    Local("t", task),
                    Local("old", failures),
                    Local("key", pg_type("text")),
                    Local("retained", pg_type("text")),
                    Local("replayed", pg_type("bool"), literal(False)),
                    Local("diagnostic", pg_type("jsonb")),
                    Local("evidence", pg_type("jsonb")),
                    Local("question_request", pg_type("jsonb")),
                ),
            ),
        ),
    )


def attempt_release_native_sql(target, protocol: bytes, evidence_schema: bytes) -> str:
    from .native_objects import native_sql_script

    return (
        native_sql_script(
            routine.render()
            for routine in attempt_release_native_programs(target, protocol, evidence_schema)
        )
        + "\n"
    )
