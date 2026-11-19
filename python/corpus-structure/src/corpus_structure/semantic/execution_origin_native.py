"""Native original execution custody and authorized private draft intake."""

from sqlalchemy import Text, and_, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array, insert
from sqlalchemy.types import NullType

from .native_program import Assign, If, Local, Perform, Return, Sql, core_variable, pg_type


def execution_origin_programs(model, routine, row, rf, obj, reject, lookup):
    request = model.tables["ops.data_request"]
    task = model.tables["ops.task"]
    definitions = model.tables["sem.data_operation_definition"]
    origins = model.tables["ops.data_execution_origin"]
    intents = model.tables["ops.data_completion_intent"]
    consumed = model.tables["ops.data_draft_consumption"]
    adoption = model.tables["ops.data_intent_adoption"]
    p = core_variable("p", JSONB())
    key = core_variable("key_", Text())
    original = core_variable("original_request_", NullType())
    completion = p["completion"]
    snapshot = core_variable("snapshot_", JSONB())

    def origin(field):
        return row("origin_", origins, field)

    def target_task(field):
        return row("t", task, field)

    def local_definition(field=None):
        return row("definition_", definitions, field)

    parameters = (("p_payload", "jsonb"),)
    common_locals = (
        Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
        Local("r", request),
        Local("t", task),
        Local("key_", pg_type("text")),
    )
    fence_fields = ["request_id", "generation", "task_id", "attempt", "holder"]
    candidates = (
        select(origins.c.id, origins.c.request_id, origins.c.generation, origins.c.created_at)
        .where(
            origins.c.request_id == rf("id"),
            origins.c.id != key,
        )
        .order_by(origins.c.created_at.desc(), origins.c.id)
        .limit(64)
        .subquery("prior_origin")
    )
    prior_origins = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        obj(
                            origin_id=candidates.c.id,
                            request_id=candidates.c.request_id,
                            generation=candidates.c.generation,
                        ),
                        candidates.c.created_at.desc(),
                        candidates.c.id,
                    )
                ),
                func.jsonb_build_array(),
            )
        )
        .select_from(candidates)
        .scalar_subquery()
    )
    routine(
        "ops",
        "register_data_execution_origin",
        parameters,
        (
            Perform(func.ops.ddo_fields(p, array([*fence_fields, "runtime_id"]))),
            lookup("r", request, request.c.id == p["request_id"].astext, lock=True),
            Assign("t", func.ops.ddo_claim(rf(), p)),
            Perform(func.sem.require_runtime_binding(rf("release_id"), p["runtime_id"].astext)),
            reject(
                p["runtime_id"].astext.is_distinct_from(rf("runtime_id")),
                "execution origin runtime differs from claimed request",
            ),
            lookup(
                "definition_",
                definitions,
                definitions.c.release_id == rf("release_id"),
                definitions.c.operation_id == rf("operation_id"),
            ),
            Assign(
                "key_",
                literal("execution-origin:").concat(
                    func.ops.ddo_digest(
                        func.jsonb_build_array(*(p[name] for name in (*fence_fields, "runtime_id")))
                    )
                ),
            ),
            Sql(
                insert(origins)
                .values(
                    id=key,
                    request_id=rf("id"),
                    generation=rf("generation"),
                    task_id=target_task("id"),
                    attempt=target_task("attempt"),
                    holder=target_task("claimed_by"),
                    runtime_id=p["runtime_id"].astext,
                    request_snapshot=func.to_jsonb(rf(), type_=JSONB()),
                    definition_snapshot=func.to_jsonb(local_definition(), type_=JSONB()),
                    created_at=func.clock_timestamp(),
                )
                .on_conflict_do_nothing()
            ),
            lookup("origin_", origins, origins.c.id == key),
            reject(
                or_(
                    origin("request_snapshot").is_distinct_from(func.to_jsonb(rf(), type_=JSONB())),
                    origin("definition_snapshot").is_distinct_from(
                        func.to_jsonb(local_definition(), type_=JSONB())
                    ),
                ),
                "execution origin replay differs from immutable native custody",
            ),
            Return(obj(payload=obj(origin_id=key, candidates=prior_origins))),
        ),
        (*common_locals, Local("definition_", definitions), Local("origin_", origins)),
        returns="jsonb",
    )
    # The semantic request key covers recipe, logical context, parameters and replicate.
    # Retain every admitted input and support binding until a narrower proof exists.
    same_material = and_(
        *(
            origin("request_snapshot")[name].is_not_distinct_from(
                func.to_jsonb(rf(), type_=JSONB())[name]
            )
            for name in (
                "request_key",
                "project_id",
                "operation_id",
                "recipe",
                "subject",
                "original_source",
                "analyzed_scope",
                "replicate",
            )
        ),
        *(
            origin("request_snapshot")["binding"][name].is_not_distinct_from(rf("binding")[name])
            for name in (
                "inputs",
                "support",
                "parameters",
                "request_inputs",
                "inference",
                "execution_profile",
                "populations",
            )
        ),
        *(
            origin("definition_snapshot")[name].is_not_distinct_from(
                func.to_jsonb(local_definition(), type_=JSONB())[name]
            )
            for name in ("implementation_revision", "profile", "output_roles", "support_contract")
        ),
    )
    from .validity_programs import family_programs, selected_family

    current_family_guards = tuple(
        If(
            selected_family(model, rf("release_id"), rf("operation_id"), family.family),
            tuple(Perform(getattr(func.ops, guard)(rf(), completion)) for guard in family.guards),
        )
        for family in family_programs(model)
    )
    original_completion = obj(
        **{
            name: origin(name)
            for name in ("request_id", "generation", "task_id", "attempt", "holder", "runtime_id")
        },
        completion=completion,
    )
    from .data_completion_settlement_native import execution_evidence_differs

    payload_digest = func.ops.ddo_digest(completion)
    origin_key = literal("intent:").concat(
        func.ops.ddo_digest(
            func.jsonb_build_array(
                origin("request_id"),
                origin("generation"),
                origin("task_id"),
                origin("attempt"),
                origin("holder"),
                origin("runtime_id"),
                completion,
            )
        )
    )
    routine(
        "ops",
        "consume_data_completion_draft",
        parameters,
        (
            Perform(
                func.ops.ddo_fields(
                    p, array([*fence_fields, "origin_id", "draft_id", "completion"])
                )
            ),
            lookup("r", request, request.c.id == p["request_id"].astext),
            Assign("snapshot_", func.ops.ddo_lock_completion_support(rf(), completion)),
            lookup("r", request, request.c.id == p["request_id"].astext, lock=True),
            Assign("t", func.ops.ddo_claim(rf(), p)),
            lookup("origin_", origins, origins.c.id == p["origin_id"].astext),
            lookup(
                "definition_",
                definitions,
                definitions.c.release_id == rf("release_id"),
                definitions.c.operation_id == rf("operation_id"),
            ),
            reject(
                ~same_material,
                "private completion material differs from the current request",
                "23514",
            ),
            reject(
                and_(
                    row("definition_", definitions, "support_contract")["reuse_eligible"].astext
                    == "false",
                    or_(
                        origin("request_id").is_distinct_from(rf("id")),
                        origin("generation").is_distinct_from(rf("generation")),
                        origin("task_id").is_distinct_from(target_task("id")),
                        origin("attempt").is_distinct_from(target_task("attempt")),
                        origin("holder").is_distinct_from(target_task("claimed_by")),
                    ),
                ),
                "attempt-only completion cannot be adopted by another producer attempt",
                "23514",
            ),
            reject(
                ~or_(
                    and_(
                        origin("task_id") == target_task("id"),
                        origin("attempt") == target_task("attempt"),
                        origin("holder") == target_task("claimed_by"),
                    ),
                    select(1)
                    .select_from(model.tables["ops.data_attempt_failure"])
                    .where(
                        *(
                            model.tables["ops.data_attempt_failure"].c[name] == origin(name)
                            for name in ("request_id", "generation", "task_id", "attempt", "holder")
                        )
                    )
                    .exists(),
                ),
                "private completion requires established original producer retirement",
                "23514",
            ),
            reject(
                func.coalesce(p["draft_id"].astext, "").bool_op("!~")("^[0-9a-f]{64}$"),
                "private completion lacks its acknowledged content identity",
            ),
            reject(
                and_(
                    origin("task_id") == target_task("id"),
                    origin("attempt") > target_task("attempt"),
                ),
                "private completion producer is newer than the consuming claim",
            ),
            Assign(
                "original_request_",
                func.jsonb_populate_record(original, origin("request_snapshot")),
            ),
            Perform(
                func.sem.require_runtime_binding(
                    origin("request_snapshot")["release_id"].astext, origin("runtime_id")
                )
            ),
            reject(
                execution_evidence_differs(original_completion),
                "private completion evidence differs from its original producer",
            ),
            reject(
                completion["implementation_revision"].astext.is_distinct_from(
                    origin("definition_snapshot")["implementation_revision"].astext
                ),
                "private completion implementation differs from original custody",
            ),
            Perform(func.ops.ddo_assert_support(rf(), completion["support"])),
            Perform(
                func.ops.ddo_require_completion_correspondence(
                    original, completion, origin("task_id"), origin("attempt"), origin("holder")
                )
            ),
            *current_family_guards,
            Perform(func.ops.ddo_require_completion_live(rf(), completion)),
            Assign("key_", origin_key),
            Sql(
                insert(intents)
                .values(
                    id=key,
                    request_id=origin("request_id"),
                    generation=origin("generation"),
                    producer_task_id=origin("task_id"),
                    producer_attempt=origin("attempt"),
                    producer_holder=origin("holder"),
                    runtime_id=origin("runtime_id"),
                    payload=completion,
                    payload_digest=payload_digest,
                    created_at=func.clock_timestamp(),
                    validation_seal=func.ops.ddo_completion_seal(
                        original, completion, origin("runtime_id"), snapshot
                    ),
                )
                .on_conflict_do_nothing()
            ),
            lookup(
                "intent_",
                intents,
                intents.c.request_id == origin("request_id"),
                intents.c.generation == origin("generation"),
            ),
            reject(
                row("intent_", intents, "id").is_distinct_from(key),
                "private completion differs from original retained answer",
            ),
            Sql(
                insert(consumed)
                .values(
                    origin_id=origin("id"),
                    draft_id=p["draft_id"].astext,
                    intent_id=key,
                    request_id=rf("id"),
                    generation=rf("generation"),
                    task_id=target_task("id"),
                    attempt=target_task("attempt"),
                    holder=target_task("claimed_by"),
                    created_at=func.clock_timestamp(),
                )
                .on_conflict_do_nothing()
            ),
            lookup("consumed_", consumed, consumed.c.origin_id == origin("id")),
            reject(
                or_(
                    row("consumed_", consumed, "intent_id").is_distinct_from(key),
                    row("consumed_", consumed, "draft_id").is_distinct_from(p["draft_id"].astext),
                    row("consumed_", consumed, "request_id").is_distinct_from(rf("id")),
                    row("consumed_", consumed, "generation").is_distinct_from(rf("generation")),
                ),
                "private completion already consumed under different custody",
            ),
            Sql(
                insert(adoption)
                .values(
                    intent_id=key,
                    task_id=target_task("id"),
                    attempt=target_task("attempt"),
                    holder=target_task("claimed_by"),
                )
                .on_conflict_do_nothing()
            ),
            Return(obj(payload=obj(intent_id=key, payload_digest=payload_digest))),
        ),
        (
            *common_locals,
            Local("origin_", origins),
            Local("definition_", definitions),
            Local("intent_", intents),
            Local("consumed_", consumed),
            Local("original_request_", request),
            Local("snapshot_", pg_type("jsonb")),
        ),
        returns="jsonb",
    )

    failures = model.tables["ops.data_attempt_failure"]
    receipts = model.tables["ops.data_publication_receipt"]
    derivations = model.tables["ops.data_derivation"]
    producer = p["producer"]
    inspection_completion = producer["completion"]
    inspection_key = literal("intent:").concat(
        func.ops.ddo_digest(
            func.jsonb_build_array(
                *(origin(name) for name in (*fence_fields, "runtime_id")),
                inspection_completion,
            )
        )
    )
    receipt_id = core_variable("receipt_id_", Text())
    failure_id = core_variable("failure_id_", Text())

    def inspection(state, reason, *, intent=None, receipt=None, failure=None):
        return Return(
            obj(
                payload=obj(
                    state=state,
                    reason=reason,
                    intent_id=intent,
                    receipt_id=receipt,
                    failure_id=failure,
                )
            )
        )

    routine(
        "ops",
        "inspect_data_completion_draft",
        parameters,
        (
            Perform(
                func.ops.ddo_fields(p, array(["project_id", "origin_id", "draft_id", "producer"]))
            ),
            Perform(
                func.ops.ddo_fields(producer, array([*fence_fields, "runtime_id", "completion"]))
            ),
            lookup("origin_", origins, origins.c.id == p["origin_id"].astext),
            reject(
                or_(
                    origin("request_snapshot")["project_id"].astext.is_distinct_from(
                        p["project_id"].astext
                    ),
                    *(
                        func.to_jsonb(origin(name)).is_distinct_from(producer[name])
                        for name in (*fence_fields, "runtime_id")
                    ),
                    func.coalesce(p["draft_id"].astext, "").bool_op("!~")("^[0-9a-f]{64}$"),
                ),
                "completion draft differs from original custody",
            ),
            Assign("key_", inspection_key),
            If(
                ~select(1).where(intents.c.id == key).exists(),
                (inspection("retained", "unpublished"),),
            ),
            lookup("intent_", intents, intents.c.id == key),
            reject(
                or_(
                    row("intent_", intents, "payload").is_distinct_from(inspection_completion),
                    row("intent_", intents, "payload_digest").is_distinct_from(
                        func.ops.ddo_digest(inspection_completion)
                    ),
                    select(1)
                    .where(
                        consumed.c.origin_id == origin("id"),
                        or_(
                            consumed.c.intent_id.is_distinct_from(key),
                            consumed.c.draft_id.is_distinct_from(p["draft_id"].astext),
                        ),
                    )
                    .exists(),
                ),
                "completion draft differs from native retained answer",
            ),
            Assign(
                "receipt_id_",
                select(receipts.c.id)
                .join(derivations, derivations.c.id == receipts.c.derivation_id)
                .where(
                    receipts.c.intent_id == key,
                    derivations.c.intent_id == key,
                    derivations.c.producer_task_id == origin("task_id"),
                    derivations.c.producer_attempt == origin("attempt"),
                )
                .scalar_subquery(),
            ),
            If(receipt_id.is_(None), (inspection("retained", "unpublished", intent=key),)),
            Assign(
                "failure_id_",
                select(failures.c.id)
                .where(*(failures.c[name] == origin(name) for name in fence_fields))
                .scalar_subquery(),
            ),
            If(
                failure_id.is_(None),
                (inspection("retained", "retirement-unconfirmed", intent=key, receipt=receipt_id),),
            ),
            inspection("eligible", "retired", intent=key, receipt=receipt_id, failure=failure_id),
        ),
        (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            Local("origin_", origins),
            Local("intent_", intents),
            Local("key_", pg_type("text")),
            Local("receipt_id_", pg_type("text")),
            Local("failure_id_", pg_type("text")),
        ),
        returns="jsonb",
        stable=True,
    )
