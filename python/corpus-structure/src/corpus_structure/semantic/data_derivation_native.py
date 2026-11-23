"""Typed publication and observation of exact declared derivations."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
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
)
from sqlalchemy.dialects.postgresql import JSONB, array, distinct_on, insert
from sqlalchemy.sql import update
from sqlalchemy.types import NullType

from .data_operation_native_identity import native_identity_field
from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    Continue,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Return,
    SelectInto,
    Sql,
    core_relation_row,
    core_variable,
    pg_type,
)
from .publication_delivery_native import record_publication_delivery


def _json(value):
    return cast(literal(value), JSONB())


def _clock():
    return func.clock_timestamp()


def _xid():
    return cast(func.pg_current_xact_id(), Text())


def _record(**fields):
    return func.jsonb_build_object(
        *(item for key, value in fields.items() for item in (key, value)), type_=JSONB()
    )


def _items(value, name, *, ordinality=False):
    call = func.jsonb_array_elements(value)
    field = column("value", JSONB())
    if ordinality:
        return call.table_valued(field, with_ordinality="ord").render_derived(name=name)
    return call.table_valued(field).alias(name)


def _owned_row(name, table):
    def field(column):
        return core_variable(name, table.c[column].type, column)

    return field


def _query(row):
    return select(core_relation_row(row)).select_from(row)


def _identifier(prefix, *coordinates):
    return literal(prefix).op("||")(func.ops.ddo_digest(func.jsonb_build_array(*coordinates)))


def _intent_lookup(intents, selection):
    return _query(intents).where(intents.c.id == selection)


def _field_check(payload, required, optional=()):
    return Perform(
        func.ops.ddo_fields(payload, array(required, type_=Text()), array(optional, type_=Text()))
    )


def _reject(when, message):
    from .native_program import Raise

    return If(when, (Raise(message, "P0001"),))


def _procedure(name, steps, locals_):
    return NativeRoutine(
        "ops",
        name,
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(tuple(steps), tuple(locals_)),
    )


def _publish_derivation(model: MetaData) -> NativeRoutine:
    requests = model.tables["ops.data_request"]
    tasks = model.tables["ops.task"]
    intents = model.tables["ops.data_completion_intent"]
    receipts = model.tables["ops.data_publication_receipt"]
    runtimes = model.tables["sem.runtime_binding"]
    definitions = model.tables["sem.data_operation_definition"]
    adoptions = model.tables["ops.data_intent_adoption"]
    origins = model.tables["ops.data_execution_origin"]
    consumptions = model.tables["ops.data_draft_consumption"]
    revocations = model.tables["ops.data_revocation"]
    episodes = model.tables["ops.data_derivation"]
    inputs = model.tables["ops.data_derivation_input"]
    outputs = model.tables["ops.data_derivation_output"]
    supporting = model.tables["ops.data_derivation_support"]
    original_support = model.tables["ops.data_derivation_original_support"]
    sources = model.tables["ops.original_source_admission"]
    members = model.tables["kb.data_product_member"]
    observations = model.tables["ops.demand_use"]
    payload = core_variable("p_payload", JSONB())
    request = _owned_row("r", requests)
    task = _owned_row("t", tasks)
    intent = _owned_row("i", intents)
    receipt = _owned_row("receipt", receipts)
    definition = _owned_row("def", definitions)
    composite = core_variable("r", NullType())
    snapshot, output, item, role, subject_scopes, output_context = (
        core_variable(name, JSONB())
        for name in ("snapshot", "o", "item", "roledef", "subject_scopes", "output_context")
    )
    episode, key, product, result = (
        core_variable(name, Text()) for name in ("episode", "key", "product", "result_state")
    )
    count, position = (core_variable(name, BigInteger()) for name in ("cnt", "n"))
    generation = cast(payload["generation"].astext, requests.c.generation.type)
    content = intent("payload")
    typed_populations = "ops.data_retained_population" in model.tables
    same_request = intent("request_id") == request("id")
    active_attempt = (task("id"), task("attempt"), task("claimed_by"))
    actual_producer = (
        intent("producer_task_id"),
        intent("producer_attempt"),
        intent("producer_holder"),
    )
    linked_attempt = (
        select(1)
        .select_from(adoptions)
        .where(
            adoptions.c.intent_id == intent("id"),
            tuple_(adoptions.c.task_id, adoptions.c.attempt, adoptions.c.holder)
            == tuple_(*active_attempt),
        )
        .exists()
    )

    consumed_draft = (
        select(1)
        .select_from(consumptions)
        .where(
            consumptions.c.intent_id == intent("id"),
            consumptions.c.request_id == payload["request_id"].astext,
            consumptions.c.generation == generation,
        )
        .exists()
    )

    def publication_response(receipt, derivation, replayed, snapshot):
        return _record(
            receipt_id=receipt, derivation_id=derivation, replayed=replayed, trust_snapshot=snapshot
        )

    replay = (
        SelectInto(_query(receipts).where(receipts.c.intent_id == intent("id")), ("receipt",)),
        If(
            and_(
                core_variable("found", Boolean()),
                same_request,
                or_(intent("generation") == generation, consumed_draft),
            ),
            (
                Perform(func.ops.ddo_require_completion_effect_authority(composite)),
                Perform(func.ops.ddo_reconfirm_completion_validity(receipt("id"))),
                Return(
                    _record(
                        payload=publication_response(
                            receipt("id"),
                            receipt("derivation_id"),
                            True,
                            receipt("trust_snapshot"),
                        )
                    )
                ),
            ),
        ),
    )
    active_runtime = (
        select(1)
        .select_from(runtimes)
        .where(
            runtimes.c.release_id == request("release_id"),
            runtimes.c.runtime_id == intent("runtime_id"),
            runtimes.c.execution_profile == request("binding")["execution_profile"].astext,
        )
        .exists()
    )
    scope = func.ops.ddo_scope(request("project_id"), request("original_source"))
    revoked = (
        select(1)
        .select_from(revocations)
        .where(
            revocations.c.scope == scope,
            or_(
                and_(
                    revocations.c.selector_kind == "runtime",
                    revocations.c.selector == intent("runtime_id"),
                ),
                and_(
                    revocations.c.selector_kind == "recipe",
                    revocations.c.selector == request("recipe"),
                ),
            ),
        )
        .exists()
    )
    positions = func.ops.ddo_derivation_input_positions(
        content["inputs"], definition("input_roles")
    ).table_valued(
        column("input_record", JSONB()), column("physical_position", inputs.c.position.type)
    )
    ordered_support = _items(content["support"], "ordered_support", ordinality=True)
    admission_scope = func.ops.ddo_scope(
        sources.c.project_id, sources.c.original_source, type_=Text()
    )
    supporting_scope = func.ops.ddo_scope(
        requests.c.project_id, requests.c.original_source, type_=Text()
    )
    outputs_rows = _items(content["outputs"], "output_rows")
    output_roles = _items(definition("output_roles"), "output_roles")
    out_role = output["role"].astext
    role_name = role["name"].astext
    role_kind = role["kind_contract"].astext
    out_member = output["member_id"].astext
    declared_outputs = (outputs.c.derivation_id == episode, outputs.c.role == role_name)
    produced = (
        select(1)
        .select_from(members)
        .where(
            members.c.product_id == product,
            members.c.member_id == out_member,
            members.c.kind_contract == role_kind,
        )
        .exists()
    )
    duplicate_outputs = (
        select(1)
        .select_from(outputs)
        .where(*declared_outputs)
        .group_by(
            outputs.c.product_id,
            outputs.c.member_id,
        )
        .having(func.count() != 1)
        .exists()
    )
    non_unit = (
        select(1)
        .select_from(outputs)
        .where(*declared_outputs, outputs.c.multiplicity != 1)
        .exists()
    )
    recent = (
        select(observations)
        .where(
            observations.c.request_id == request("id"),
            observations.c.generation == generation,
        )
        .ext(distinct_on(observations.c.obligation_id))
        .order_by(
            observations.c.obligation_id,
            observations.c.created_at.desc(),
            observations.c.id.desc(),
        )
        .subquery("latest_observations")
    )
    observe = (
        insert(observations)
        .from_select(
            (
                "id",
                "demand_id",
                "obligation_id",
                "fate",
                "request_id",
                "generation",
                "derivation_id",
                "selection",
                "trust_snapshot",
                "created_at",
                "created_xid",
            ),
            select(
                _identifier("use:", recent.c.obligation_id, key),
                recent.c.demand_id,
                recent.c.obligation_id,
                case((result == "failed", "failed"), else_="fulfilled"),
                request("id"),
                generation,
                episode,
                recent.c.selection,
                snapshot,
                _clock(),
                _xid(),
            )
            .select_from(recent)
            .where(recent.c.fate == "attached", func.ops.ddo_demand_active(recent.c.demand_id)),
        )
        .on_conflict_do_nothing()
    )
    return _procedure(
        "publish_data_derivation",
        (
            _field_check(
                payload,
                ("request_id", "generation", "task_id", "attempt", "holder", "intent_id"),
                ("trust_snapshot",),
            ),
            SelectInto(_intent_lookup(intents, payload["intent_id"].astext), ("i",), strict=True),
            SelectInto(
                _query(requests).where(requests.c.id == payload["request_id"].astext),
                ("r",),
                strict=True,
            ),
            Perform(func.ops.ddo_authorize_request(composite)),
            # Observe before and after waiting for the request. A successful replay needs no live claim.
            *replay,
            Assign("snapshot", func.ops.ddo_lock_completion_support(composite, content)),
            SelectInto(
                _query(requests).where(requests.c.id == request("id")).with_for_update(),
                ("r",),
                strict=True,
            ),
            *replay,
            Assign("t", func.ops.ddo_claim(composite, payload)),
            _reject(
                or_(
                    ~same_request,
                    and_(
                        ~consumed_draft,
                        or_(
                            intent("generation") != request("generation"),
                            intent("generation") != generation,
                        ),
                    ),
                    ~or_(tuple_(*actual_producer) == tuple_(*active_attempt), linked_attempt),
                ),
                "intent is not bound to current attempt",
            ),
            If(
                consumed_draft,
                (
                    Perform(func.ops.ddo_require_completion_live(composite, content)),
                    SelectInto(
                        select(origins.c.request_snapshot)
                        .select_from(
                            origins.join(consumptions, consumptions.c.origin_id == origins.c.id)
                        )
                        .where(
                            consumptions.c.intent_id == intent("id"),
                            consumptions.c.request_id == request("id"),
                            consumptions.c.generation == generation,
                        ),
                        ("original_request_",),
                        strict=True,
                    ),
                    Assign(
                        "r",
                        func.jsonb_populate_record(
                            composite, core_variable("original_request_", JSONB())
                        ),
                    ),
                ),
            ),
            Perform(func.ops.ddo_assert_support(composite, content["support"])),
            Perform(func.sem.require_runtime_binding(request("release_id"), intent("runtime_id"))),
            _reject(~active_runtime, "producing runtime execution profile differs"),
            Perform(
                func.ops.ddo_require_provider_profile(
                    request("release_id"), request("operation_id"), intent("runtime_id")
                )
            ),
            _reject(revoked, "producing runtime or recipe was directly revoked"),
            SelectInto(
                _query(definitions).where(
                    definitions.c.release_id == request("release_id"),
                    definitions.c.operation_id == request("operation_id"),
                ),
                ("def",),
                strict=True,
            ),
            Assign(
                "result_state",
                func.ops.ddo_completion_state(
                    core_variable("def", NullType()), content["outcome"].astext
                ),
            ),
            _reject(
                or_(
                    content["implementation_revision"].astext
                    != definition("implementation_revision"),
                    func.jsonb_typeof(content["outputs"]) != "array",
                ),
                "invalid completion attestation/outcome",
            ),
            _reject(
                and_(result.in_(("empty", "failed")), content["outputs"] != _json("[]")),
                "non-success completion cannot publish outputs",
            ),
            If(
                intent("validation_seal").is_distinct_from(
                    func.ops.ddo_completion_seal(
                        composite, content, intent("runtime_id"), snapshot
                    ),
                ),
                (
                    Perform(
                        func.ops.ddo_require_completion_correspondence(
                            composite,
                            content,
                            *actual_producer,
                            *((intent("id"),) if typed_populations else ()),
                        )
                    ),
                ),
            ),
            Perform(func.ops.ddo_require_completion_live(composite, content)),
            Assign("episode", _identifier("derivation:", intent("id"), intent("payload_digest"))),
            Sql(
                insert(episodes).values(
                    id=episode,
                    request_id=request("id"),
                    generation=request("generation"),
                    intent_id=intent("id"),
                    release_id=request("release_id"),
                    recipe=request("recipe"),
                    runtime_id=intent("runtime_id"),
                    producer_task_id=actual_producer[0],
                    producer_attempt=actual_producer[1],
                    outcome=result,
                    completed_at=_clock(),
                )
            ),
            ForQuery(
                ("item", "n"),
                select(positions.c.input_record, positions.c.physical_position),
                (
                    Sql(
                        insert(inputs).values(
                            derivation_id=episode,
                            role=item["role"].astext,
                            position=position,
                            multiplicity=cast(
                                item["multiplicity"].astext, inputs.c.multiplicity.type
                            ),
                            product_id=item["product_id"].astext,
                            member_id=item["member_id"].astext,
                            occurrence_label=item["occurrence_label"].astext,
                        )
                    ),
                ),
            ),
            ForQuery(
                ("item", "n"),
                select(ordered_support.c.value, ordered_support.c.ord - 1).select_from(
                    ordered_support
                ),
                (
                    If(
                        item["kind"].astext.in_(("original-source", "authored")),
                        (
                            Sql(
                                insert(original_support).from_select(
                                    (
                                        "derivation_id",
                                        "occurrence",
                                        "role",
                                        "position",
                                        "admission_id",
                                        "source_reference",
                                        "scope",
                                        "epoch",
                                    ),
                                    select(
                                        episode,
                                        position,
                                        item["role"].astext,
                                        cast(
                                            item["position"].astext,
                                            original_support.c.position.type,
                                        ),
                                        sources.c.id,
                                        sources.c.source_reference,
                                        admission_scope,
                                        cast(
                                            snapshot[admission_scope].astext,
                                            original_support.c.epoch.type,
                                        ),
                                    )
                                    .select_from(sources)
                                    .where(sources.c.id == item["admission_id"].astext),
                                )
                            ),
                            Continue(),
                        ),
                    ),
                    Sql(
                        insert(supporting).from_select(
                            (
                                "derivation_id",
                                "role",
                                "position",
                                "support_derivation_id",
                                "scope",
                                "epoch",
                                "admission_use_id",
                                "occurrence",
                            ),
                            select(
                                episode,
                                func.coalesce(item["role"].astext, "support"),
                                func.coalesce(
                                    cast(item["position"].astext, supporting.c.position.type),
                                    position,
                                ),
                                item["derivation_id"].astext,
                                supporting_scope,
                                cast(snapshot[supporting_scope].astext, supporting.c.epoch.type),
                                item["admission_use_id"].astext,
                                position,
                            )
                            .select_from(
                                episodes.join(requests, requests.c.id == episodes.c.request_id)
                            )
                            .where(episodes.c.id == item["derivation_id"].astext),
                        )
                    ),
                ),
            ),
            Assign("subject_scopes", func.ops.ddo_release_subject_scopes(request("release_id"))),
            Assign(
                "output_context",
                _record(
                    project_id=request("project_id"),
                    release_id=request("release_id"),
                    subject=request("subject"),
                    subject_definition=func.ops.ddo_operation_subject(
                        request("release_id"), request("operation_id")
                    ),
                    original_source=request("original_source"),
                    analyzed_scope=request("analyzed_scope"),
                ),
            ),
            ForQuery(
                ("o",),
                select(outputs_rows.c.value),
                (
                    _field_check(
                        output, ("role", "position", "multiplicity", "product"), ("member_id",)
                    ),
                    SelectInto(
                        select(output_roles.c.value).where(
                            output_roles.c.value["name"].astext == out_role
                        ),
                        ("roledef",),
                    ),
                    _reject(
                        or_(
                            role.is_(None),
                            and_(
                                out_member.is_(None),
                                role_kind.is_distinct_from(
                                    output["product"]["kind_contract"].astext
                                ),
                            ),
                        ),
                        "output role/kind mismatch",
                    ),
                    Assign(
                        "product",
                        func.ops.ddo_install_product_context(
                            output_context,
                            output["product"],
                            subject_scopes,
                            *(
                                (
                                    intent("id"),
                                    out_role,
                                    cast(output["position"].astext, BigInteger()),
                                )
                                if typed_populations
                                else ()
                            ),
                        ),
                    ),
                    _reject(
                        and_(out_member.is_not(None), ~produced),
                        "output member is outside its qualified product",
                    ),
                    Sql(
                        insert(outputs).values(
                            derivation_id=episode,
                            role=out_role,
                            position=cast(output["position"].astext, outputs.c.position.type),
                            multiplicity=cast(
                                output["multiplicity"].astext, outputs.c.multiplicity.type
                            ),
                            product_id=product,
                            member_id=out_member,
                        )
                    ),
                ),
            ),
            If(
                result == "success",
                (
                    ForQuery(
                        ("roledef",),
                        select(output_roles.c.value),
                        (
                            SelectInto(
                                select(func.coalesce(func.sum(outputs.c.multiplicity), 0)).where(
                                    *declared_outputs
                                ),
                                ("cnt",),
                            ),
                            _reject(
                                and_(
                                    role["collection"].astext == "set",
                                    or_(non_unit, duplicate_outputs),
                                ),
                                "set output requires unique values and unit multiplicity",
                            ),
                            _reject(
                                or_(
                                    count
                                    < func.coalesce(cast(role["minimum"].astext, Integer()), 0),
                                    and_(
                                        role["maximum"].astext.is_not(None),
                                        count > cast(role["maximum"].astext, Integer()),
                                    ),
                                ),
                                "output cardinality differs from contract",
                            ),
                        ),
                    ),
                ),
            ),
            *(
                (Perform(func.ops.ddo_settle_rule_attestations(composite, content, episode)),)
                if "sem.data_rule" in model.tables
                else ()
            ),
            Assign("key", _identifier("receipt:", intent("id"), episode)),
            Sql(
                insert(receipts).values(
                    id=key,
                    intent_id=intent("id"),
                    derivation_id=episode,
                    publishing_task_id=task("id"),
                    publishing_attempt=task("attempt"),
                    trust_snapshot=snapshot,
                    validating_kernel_digest=native_identity_field("source_digest"),
                    validation_identities=func.ops.ddo_current_validation_identities(
                        request("release_id"), request("operation_id"), type_=JSONB()
                    ),
                )
            ),
            Sql(
                update(tasks)
                .where(tasks.c.id == task("id"))
                .values(
                    status=case(
                        (result == "success", "done"), (result == "empty", "empty"), else_="failed"
                    ),
                    result_digest=intent("payload_digest"),
                    finished_at=_clock(),
                    lease_until=None,
                    error=case((result == "failed", _record(data_operation="failed"))),
                )
            ),
            Sql(record_publication_delivery(model, observe, key, request("project_id"))),
            Perform(
                func.ops.ddo_record_computation_wakes(
                    select(
                        func.coalesce(
                            func.jsonb_agg(observations.c.id),
                            _json("[]"),
                        )
                    )
                    .where(
                        observations.c.derivation_id == episode,
                        observations.c.request_id == request("id"),
                        observations.c.generation == generation,
                    )
                    .scalar_subquery()
                )
            ),
            Return(_record(payload=publication_response(key, episode, False, snapshot))),
        ),
        (
            Local("r", requests),
            Local("original_request_", pg_type("jsonb")),
            Local("t", tasks),
            Local("i", intents),
            Local("receipt", receipts),
            Local("snapshot", pg_type("jsonb")),
            Local("episode", pg_type("text")),
            Local("key", pg_type("text")),
            Local("o", pg_type("jsonb")),
            Local("item", pg_type("jsonb")),
            Local("roledef", pg_type("jsonb")),
            Local("def", definitions),
            Local("cnt", pg_type("int8")),
            Local("n", pg_type("int8")),
            Local("product", pg_type("text")),
            Local("result_state", pg_type("text")),
            Local("subject_scopes", pg_type("jsonb")),
            Local("output_context", pg_type("jsonb")),
        ),
    )


def _inspect_completion(model: MetaData) -> NativeRoutine:
    requests = model.tables["ops.data_request"]
    intents = model.tables["ops.data_completion_intent"]
    demands = model.tables["ops.data_demand"]
    observations = model.tables["ops.demand_use"]
    receipts = model.tables["ops.data_publication_receipt"]
    episodes = model.tables["ops.data_derivation"]
    consumptions = model.tables["ops.data_draft_consumption"]
    payload = core_variable("p_payload", JSONB())
    request = _owned_row("r", requests)
    intent = _owned_row("i", intents)
    receipt = _owned_row("receipt", receipts)
    has_demand, has_request, has_generation = (
        payload.has_key(name) for name in ("demand_id", "request_id", "generation")
    )
    demand = payload["demand_id"].astext
    request_id = payload["request_id"].astext
    generation = cast(payload["generation"].astext, requests.c.generation.type)
    adopted = (
        select(1)
        .select_from(consumptions)
        .where(
            consumptions.c.intent_id == intents.c.id,
            consumptions.c.request_id == request("id"),
            consumptions.c.generation == generation,
        )
        .correlate(intents)
        .exists()
    )
    selected = _intent_lookup(intents, payload["intent_id"].astext)
    full = _record(
        state="committed",
        intent_retained=True,
        receipt_id=receipt("id"),
        derivation_id=receipt("derivation_id"),
        producer_task_id=intent("producer_task_id"),
        producer_attempt=intent("producer_attempt"),
        runtime_id=intent("runtime_id"),
        semantic_outcome=intent("payload")["outcome"].astext,
        completion_state=select(episodes.c.outcome)
        .where(episodes.c.id == receipt("derivation_id"))
        .scalar_subquery(),
        trust_snapshot=receipt("trust_snapshot"),
    )
    return _procedure(
        "inspect_data_completion",
        (
            _field_check(payload, ("intent_id",), ("demand_id", "request_id", "generation")),
            _reject(
                or_(
                    ~or_(has_demand, and_(has_request, has_generation)),
                    has_request != has_generation,
                ),
                "inspection requires demand or exact request/generation binding",
            ),
            _reject(
                and_(
                    has_demand,
                    ~select(1).select_from(demands).where(demands.c.id == demand).exists(),
                ),
                "unknown inspection demand",
            ),
            If(
                has_request,
                (
                    SelectInto(
                        _query(requests)
                        .where(requests.c.id == request_id)
                        .with_for_update(read=True),
                        ("r",),
                        strict=True,
                    ),
                ),
                (
                    SelectInto(selected, ("i",)),
                    If(
                        ~core_variable("found", Boolean()),
                        (
                            Return(
                                _record(
                                    payload=_record(
                                        state="unavailable",
                                        intent_retained=False,
                                        reason="intent-request-binding-unavailable",
                                    )
                                )
                            ),
                        ),
                    ),
                    SelectInto(
                        _query(requests)
                        .where(requests.c.id == intent("request_id"))
                        .with_for_update(read=True),
                        ("r",),
                        strict=True,
                    ),
                ),
            ),
            Perform(func.ops.ddo_authorize_request(core_variable("r", NullType()))),
            # Observe row state after acquiring the request lock in the separate statement.
            SelectInto(
                selected.where(
                    intents.c.request_id == request("id"),
                    or_(~has_generation, intents.c.generation == generation, adopted),
                ),
                ("i",),
            ),
            _reject(
                and_(
                    has_demand,
                    ~select(1)
                    .select_from(observations)
                    .where(
                        observations.c.demand_id == demand,
                        observations.c.request_id == request("id"),
                        or_(~has_generation, observations.c.generation == generation),
                    )
                    .exists(),
                ),
                "intent request outside inspection demand",
            ),
            If(
                intent("id").is_(None),
                (
                    Return(
                        _record(
                            payload=_record(
                                state="known-uncommitted",
                                intent_retained=False,
                            )
                        )
                    ),
                ),
            ),
            SelectInto(_query(receipts).where(receipts.c.intent_id == intent("id")), ("receipt",)),
            Return(
                _record(
                    payload=case(
                        (core_variable("found", Boolean()), full),
                        else_=_record(
                            state="known-uncommitted",
                            intent_retained=True,
                            producer_task_id=intent("producer_task_id"),
                            producer_attempt=intent("producer_attempt"),
                        ),
                    )
                )
            ),
        ),
        (Local("i", intents), Local("r", requests), Local("receipt", receipts)),
    )


def data_derivation_programs(model: MetaData) -> tuple[NativeRoutine, ...]:
    return _publish_derivation(model), _inspect_completion(model)


def data_derivation_sql(model: MetaData) -> str:
    return native_sql_script(item.render() for item in data_derivation_programs(model))
