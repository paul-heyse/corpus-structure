"""Generate protected external execution custody from captured domain declarations."""

import yaml
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

from corpus_structure.schema.integrity import role_name

from .binding_recursive_native import _check, _elements, _json, _texts, _value
from .native_objects import INTERNAL_PROGRAM
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    PerformQuery,
    Return,
    SelectInto,
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _object(**fields):
    return func.jsonb_build_object(
        *(part for pair in fields.items() for part in pair), type_=JSONB()
    )


def external_execution_native_programs(model, protocol: bytes) -> tuple[ProgramDeclaration, ...]:
    """Emit one authoritative native packet, attempt and immutable receipt owner."""
    schema = yaml.safe_load(protocol)
    definitions = schema["definitions"]
    wire_requests = {operation["name"]: operation["request"] for operation in schema["operations"]}
    tables = {
        key: model.tables[name]
        for key, name in {
            "r": "ops.data_request",
            "t": "ops.task",
            "definition": "sem.data_operation_definition",
            "packet": "ops.data_external_packet",
            "old": "ops.data_external_packet",
            "receipt": "ops.data_external_receipt",
            "product": "kb.data_product",
            "member": "kb.data_product_member",
            "kind": "sem.data_kind_contract",
            "use": "ops.demand_use",
            "completion_intent": "ops.data_completion_intent",
            "revocation": "ops.data_revocation",
        }.items()
    }
    (
        requests,
        tasks,
        packets,
        receipts,
        operations,
        products,
        members,
        kinds,
        uses,
        intents,
        revoked,
    ) = (
        tables[key]
        for key in (
            "r",
            "t",
            "packet",
            "receipt",
            "definition",
            "product",
            "member",
            "kind",
            "use",
            "completion_intent",
            "revocation",
        )
    )

    def row(name, field):
        return core_variable(name, tables[name].c[field].type, field)

    def r(field):
        return row("r", field)

    def t(field):
        return row("t", field)

    def packet(field):
        return row("packet", field)

    def receipt(field):
        return row("receipt", field)

    def definition(field):
        return row("definition", field)

    p = _value("p", JSONB())
    request_row = _value("r")
    receipt_row = _value("receipt")
    completion, evidence, retained = (
        _value(name, JSONB()) for name in ("completion", "evidence", "retained")
    )
    key, digest, intent = (_value(name) for name in ("key", "digest_", "intent"))
    local_types = {
        "p": pg_type("jsonb"),
        "key": pg_type("text"),
        "digest_": pg_type("text"),
        "intent": pg_type("text"),
        **{
            name: pg_type("jsonb")
            for name in (
                "completion",
                "evidence",
                "retained",
                "inputs",
                "contracts",
                "snapshot",
                "result",
                "publication",
                "packet_value",
            )
        },
        "count_": pg_type("bigint"),
        "size_": pg_type("bigint"),
        "forbidden": pg_type("boolean"),
        "lim": pg_type("integer"),
        "state_": pg_type("text"),
    }

    def locals_for(names):
        return tuple(
            Local(
                name,
                tables[name] if name in tables else local_types[name],
                _value("p_payload", JSONB()) if name == "p" else None,
            )
            for name in names
        )

    def procedure(name, parameters, steps, locals_=(), *, returns="jsonb", volatility=None):
        return NativeRoutine(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type(returns),
            body=Block(tuple(steps), tuple(locals_)),
            volatility=volatility,
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )

    def wire(name, steps, names):
        contract = definitions[wire_requests[name]]
        required = tuple(contract["required"])
        optional = tuple(field for field in contract["properties"] if field not in required)
        guard = Perform(
            func.ops.ddo_fields(p, array(required, type_=Text()), array(optional, type_=Text()))
        )
        return procedure(
            name,
            (Parameter("p_payload", pg_type("jsonb")),),
            (guard, *steps),
            locals_for(("p", *names)),
        )

    def selected_row(table, condition, target, *, strict=True, lock=False):
        query = select(core_relation_row(table)).select_from(table).where(condition)
        return SelectInto(query.with_for_update() if lock else query, (target,), strict)

    request_select = selected_row(requests, requests.c.id == packet("request_id"), "r")
    packet_select = selected_row(
        packets,
        and_(
            packets.c.id == p["packet_id"].astext,
            packets.c.request_id == p["request_id"].astext,
            packets.c.generation == cast(p["generation"].astext, packets.c.generation.type),
        ),
        "packet",
    )
    receipt_select = selected_row(
        receipts, receipts.c.packet_id == packet("id"), "receipt", strict=False
    )
    definition_select = selected_row(
        operations,
        and_(
            operations.c.release_id == r("release_id"),
            operations.c.operation_id == r("operation_id"),
        ),
        "definition",
    )
    authorize = Perform(func.ops.ddo_authorize_request(request_row))
    lock_request = selected_row(requests, requests.c.id == r("id"), "r", lock=True)
    support = r("binding")["support"]
    lock_support = Perform(
        func.ops.ddo_lock_support(r("project_id"), r("original_source"), support)
    )
    assert_support = Perform(func.ops.ddo_assert_support(request_row, support))
    assert_active = Perform(func.ops.ddo_assert_external_active(request_row))
    claim = Assign("t", func.ops.ddo_claim(request_row, p))

    def result(**fields):
        return Return(_object(payload=_object(**fields)))

    packet_read_result = result(
        packet_id=packet("id"), packet_digest=packet("payload_digest"), packet=packet("payload")
    )
    request_fence = tuple_(
        r("id"),
        r("generation"),
        _value("producer_task", BigInteger()),
        _value("producer_attempt", BigInteger()),
        _value("producer_holder"),
    )
    receipt_fence = tuple_(
        *(receipt(name) for name in ("request_id", "generation", "task_id", "attempt", "holder"))
    )
    payload_fence = tuple_(
        p["request_id"].astext,
        cast(p["generation"].astext, BigInteger()),
        cast(p["task_id"].astext, BigInteger()),
        cast(p["attempt"].astext, BigInteger()),
        p["holder"].astext,
    )
    receipt_value = func.ops.ddo_external_receipt_value(receipt_row, type_=JSONB())
    intent_select = SelectInto(
        select(intents.c.id).where(
            intents.c.request_id == packet("request_id"),
            intents.c.generation == packet("generation"),
        ),
        ("intent",),
        True,
    )
    replay_result = result(receipt=receipt_value, intent_id=intent)
    replay = If(
        receipt("id").is_not(None),
        (
            _check(
                or_(
                    receipt("result_digest") != digest,
                    receipt("actor_assertion") != p["actor_assertion"].astext,
                    receipt("model_assertion").is_distinct_from(p["model_assertion"].astext),
                ),
                "external packet already retains a different immutable result/assertion",
            ),
            intent_select,
            replay_result,
        ),
    )
    input_items = (
        func.jsonb_array_elements(r("binding")["inputs"])
        .table_valued(column("item", JSONB()), with_ordinality="ordinal")
        .render_derived(name="inputs")
    )
    item = input_items.c.item
    product = products.alias("product")
    member = members.alias("member")
    input_fields = _object(
        role=item["role"].astext,
        position=item["position"],
        multiplicity=item["multiplicity"],
        product_id=product.c.id,
        member_id=item["member_id"],
        kind_contract=func.coalesce(member.c.kind_contract, product.c.kind_contract),
        subject=func.coalesce(member.c.subject, product.c.subject),
        subject_definition=func.coalesce(member.c.subject_definition, product.c.subject_definition),
        original_source=func.coalesce(member.c.original_source, product.c.original_source),
        analyzed_scope=case(
            (member.c.member_id.is_(None), product.c.analyzed_scope), else_=member.c.analyzed_scope
        ),
        meaning=func.coalesce(member.c.body, product.c.canonical_body),
    )
    input_result = pg_type("jsonb")
    input_result.setof = True
    inputs_sql = NativeRoutine(
        "ops",
        "ddo_external_input_rows",
        parameters=(Parameter("r", pg_type(str(requests.schema), requests.name)),),
        returns=input_result,
        body=select(input_fields)
        .select_from(
            input_items.join(product, product.c.id == item["product_id"].astext).outerjoin(
                member,
                and_(
                    member.c.product_id == product.c.id,
                    member.c.member_id == item["member_id"].astext,
                ),
            )
        )
        .where(or_(item["member_id"].astext.is_(None), member.c.member_id.is_not(None)))
        .order_by(input_items.c.ordinal),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )
    receipt_sql = NativeRoutine(
        "ops",
        "ddo_external_receipt_value",
        parameters=(Parameter("receipt", pg_type(str(receipts.schema), receipts.name)),),
        returns=pg_type("jsonb"),
        body=select(
            _object(
                version="external-execution-receipt-v1",
                receipt_id=receipt("id"),
                **{
                    name: receipt(name)
                    for name in (
                        "packet_id",
                        "packet_digest",
                        "request_id",
                        "generation",
                        "task_id",
                        "attempt",
                        "holder",
                        "runtime_id",
                        "admitting_principal",
                        "actor_assertion",
                        "model_assertion",
                        "result_digest",
                    )
                },
            )
        ),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    active_sql = procedure(
        "ddo_assert_external_active",
        (Parameter("r", pg_type(str(requests.schema), requests.name)),),
        (
            Perform(func.sem.require_runtime_binding(r("release_id"), r("runtime_id"))),
            _check(
                select(literal(1))
                .select_from(revoked)
                .where(
                    revoked.c.scope == func.ops.ddo_scope(r("project_id"), r("original_source")),
                    or_(
                        and_(
                            revoked.c.selector_kind == "runtime",
                            revoked.c.selector == r("runtime_id"),
                        ),
                        and_(
                            revoked.c.selector_kind == "recipe", revoked.c.selector == r("recipe")
                        ),
                    ),
                )
                .exists(),
                "external producing runtime or recipe was directly revoked",
            ),
        ),
        returns="void",
        volatility="stable",
    )
    inputs = (
        func.ops.ddo_external_input_rows(request_row)
        .table_valued(column("value", JSONB()))
        .render_derived(name="external_input")
    )
    input_value = inputs.c.value
    role_rows = _elements(definition("input_roles"), "input_role")
    selected_role = (
        select(role_rows.c.value)
        .where(role_rows.c.value["name"].astext == input_value["role"].astext)
        .lateral("role")
    )
    exposed_roles = _elements(
        definition("input_roles").op("||")(definition("output_roles")), "exposed_role"
    )
    exposed = select(exposed_roles.c.value["kind_contract"].astext.label("kind_contract")).cte(
        "exposed", recursive=True
    )
    parent_kind = kinds.alias("parent")
    child = _texts(parent_kind.c.member_contracts, "child").lateral("child")
    exposed = exposed.union(
        select(child.c.value).select_from(
            exposed.join(parent_kind, parent_kind.c.kind_contract == exposed.c.kind_contract).join(
                child, literal(True)
            )
        )
    )
    nested = (
        func.ops.ddo_body_kind_contracts(
            input_value["kind_contract"].astext, input_value["meaning"]
        )
        .table_valued(column("kind_contract", Text()))
        .render_derived(name="included")
        .lateral("included")
    )
    declared_protected = (
        select(exposed.c.kind_contract)
        .select_from(exposed.join(kinds, kinds.c.kind_contract == exposed.c.kind_contract))
        .where(kinds.c.universe == "evaluator")
        .exists()
    )
    selected_protected = (
        select(members.c.member_id)
        .select_from(
            input_items.join(members, members.c.product_id == item["product_id"].astext).join(
                kinds, kinds.c.kind_contract == members.c.kind_contract
            )
        )
        .where(item["member_id"].astext.is_(None), kinds.c.universe == "evaluator")
        .exists()
    )
    nested_protected = (
        select(nested.c.kind_contract)
        .select_from(
            inputs.join(nested, literal(True)).join(
                kinds, kinds.c.kind_contract == nested.c.kind_contract
            )
        )
        .where(kinds.c.universe == "evaluator")
        .exists()
    )
    output_roles = (
        func.jsonb_array_elements(definition("output_roles"))
        .table_valued(column("role", JSONB()), with_ordinality="ordinal")
        .render_derived(name="outputs")
    )
    output_role = output_roles.c.role
    output_contract = _object(
        role=output_role["name"].astext,
        kind_contract=output_role["kind_contract"].astext,
        schema=kinds.c.body_schema,
        minimum=output_role["minimum"],
        maximum=output_role["maximum"],
        collection=output_role["collection"],
    )
    old_id = row("old", "id")
    packet_value = _value("packet_value", JSONB())
    capacity = cast(p["max_bytes"].astext, Integer())

    def canonical_size(value):
        return func.octet_length(func.data.canonical_json(value))

    retain_sql = wire(
        "retain_external_data_packet",
        (
            selected_row(requests, requests.c.id == p["request_id"].astext, "r"),
            authorize,
            Assign(
                "key",
                literal("external-packet:")
                + func.ops.ddo_digest(
                    func.jsonb_build_array(r("id"), cast(p["generation"].astext, BigInteger()))
                ),
            ),
            selected_row(
                packets,
                and_(
                    packets.c.id == key,
                    packets.c.request_id == r("id"),
                    packets.c.generation == cast(p["generation"].astext, BigInteger()),
                ),
                "old",
                strict=False,
            ),
            If(
                old_id.is_not(None),
                (
                    result(
                        packet_id=old_id,
                        packet_digest=row("old", "payload_digest"),
                        state="awaiting-external",
                    ),
                ),
            ),
            lock_support,
            lock_request,
            claim,
            definition_select,
            _check(
                or_(
                    definition("support_contract")["external"].is_(None),
                    p["runtime_id"].astext != r("runtime_id"),
                ),
                "request has no matching admitted external protocol/runtime",
            ),
            assert_active,
            assert_support,
            _check(
                or_(declared_protected, selected_protected, nested_protected),
                "protected evaluator data cannot enter an external packet",
            ),
            SelectInto(
                select(
                    func.count(),
                    func.coalesce(func.sum(canonical_size(input_value)), 0),
                    func.coalesce(
                        func.bool_or(
                            or_(
                                kinds.c.universe == "evaluator",
                                selected_role.c.value.is_(None),
                                ~selected_role.c.value["accepted_kind_contracts"].bool_op("?")(
                                    input_value["kind_contract"].astext
                                ),
                            )
                        ),
                        False,
                    ),
                ).select_from(
                    inputs.join(
                        kinds, kinds.c.kind_contract == input_value["kind_contract"].astext
                    ).outerjoin(selected_role, literal(True))
                ),
                ("count_", "size_", "forbidden"),
            ),
            _check(
                or_(
                    _value("count_", BigInteger())
                    != func.jsonb_array_length(r("binding")["inputs"]),
                    _value("forbidden", Boolean()),
                ),
                "external packet input differs from exact admitted role/kind membership",
            ),
            SelectInto(
                select(
                    func.coalesce(
                        func.jsonb_agg(aggregate_order_by(output_contract, output_roles.c.ordinal)),
                        _json("[]"),
                    )
                ).select_from(
                    output_roles.join(
                        kinds, kinds.c.kind_contract == output_role["kind_contract"].astext
                    )
                ),
                ("contracts",),
            ),
            _check(
                _value("size_", BigInteger())
                + canonical_size(r("binding"))
                + canonical_size(_value("contracts", JSONB()))
                + canonical_size(definition("support_contract")["external"])
                > capacity,
                "external packet exceeds owned packet capacity",
            ),
            SelectInto(
                select(func.coalesce(func.jsonb_agg(input_value), _json("[]"))), ("inputs",)
            ),
            Assign(
                "packet_value",
                _object(
                    version="external-data-packet-v1",
                    packet_id=key,
                    request_id=r("id"),
                    request_key=r("request_key"),
                    generation=r("generation"),
                    task_id=t("id"),
                    project_id=r("project_id"),
                    release_id=r("release_id"),
                    runtime_id=r("runtime_id"),
                    operation_id=r("operation_id"),
                    recipe=r("recipe"),
                    implementation_revision=definition("implementation_revision"),
                    subject=r("subject"),
                    subject_definition=func.ops.ddo_operation_subject(
                        r("release_id"), r("operation_id")
                    ),
                    original_source=r("original_source"),
                    analyzed_scope=r("analyzed_scope"),
                    binding=r("binding"),
                    protocol=definition("support_contract")["external"],
                    inputs=_value("inputs", JSONB()),
                    result_contract=_value("contracts", JSONB()),
                    outcomes=definition("support_contract")["outcomes"],
                ),
            ),
            _check(
                canonical_size(packet_value) > capacity,
                "complete external packet exceeds owned packet capacity",
            ),
            Sql(
                insert(packets).values(
                    id=key,
                    request_id=r("id"),
                    generation=r("generation"),
                    task_id=t("id"),
                    producer_attempt=t("attempt"),
                    producer_holder=t("claimed_by"),
                    runtime_id=r("runtime_id"),
                    payload=packet_value,
                    payload_digest=func.ops.ddo_digest(packet_value),
                    created_at=func.clock_timestamp(),
                )
            ),
            Sql(
                update(tasks)
                .where(tasks.c.id == t("id"))
                .values(status="pending", lease_until=null())
            ),
            result(
                packet_id=key,
                packet_digest=func.ops.ddo_digest(packet_value),
                state="awaiting-external",
            ),
        ),
        (
            "r",
            "t",
            "definition",
            "old",
            "packet_value",
            "inputs",
            "contracts",
            "key",
            "count_",
            "size_",
            "forbidden",
        ),
    )
    current_use = (
        select(uses.c.id)
        .where(
            uses.c.demand_id == p["demand_id"].astext,
            tuple_(uses.c.request_id, uses.c.generation)
            == tuple_(packet("request_id"), packet("generation")),
            uses.c.fate == "attached",
            func.ops.ddo_demand_active(uses.c.demand_id, type_=Boolean()),
        )
        .exists()
    )
    queue_request = requests.alias("queue_request")
    queue_packet = packets.alias("queue_packet")
    queue_task = tasks.alias("queue_task")
    queue_use = uses.alias("queue_use")
    queue_receipt = receipts.alias("queue_receipt")
    queue_revoked = revoked.alias("queue_revoked")
    queue_scope = func.ops.ddo_scope(queue_request.c.project_id, queue_request.c.original_source)
    queue_projection = (
        select(
            queue_packet.c.id,
            queue_packet.c.payload_digest,
            queue_packet.c.request_id,
            queue_packet.c.generation,
            queue_packet.c.task_id,
            queue_request.c.operation_id,
            queue_request.c.subject,
        )
        .select_from(
            queue_packet.join(
                queue_request,
                tuple_(queue_request.c.id, queue_request.c.generation, queue_request.c.live_task_id)
                == tuple_(
                    queue_packet.c.request_id, queue_packet.c.generation, queue_packet.c.task_id
                ),
            ).join(queue_task, queue_task.c.id == queue_packet.c.task_id)
        )
        .where(
            queue_request.c.project_id == p["project_id"].astext,
            func.ops.ddo_request_useful(queue_request.table_valued(), type_=Boolean()),
            or_(
                queue_task.c.status == "pending",
                and_(
                    queue_task.c.status == "running",
                    queue_task.c.lease_until <= func.clock_timestamp(),
                ),
            ),
            ~select(queue_receipt.c.id)
            .where(queue_receipt.c.packet_id == queue_packet.c.id)
            .exists(),
            ~select(literal(1))
            .select_from(queue_revoked)
            .where(
                queue_revoked.c.scope == queue_scope,
                or_(
                    and_(
                        queue_revoked.c.selector_kind == "runtime",
                        queue_revoked.c.selector == queue_request.c.runtime_id,
                    ),
                    and_(
                        queue_revoked.c.selector_kind == "recipe",
                        queue_revoked.c.selector == queue_request.c.recipe,
                    ),
                ),
            )
            .exists(),
            or_(
                ~p.bool_op("?")("demand_id"),
                select(queue_use.c.id)
                .where(
                    queue_use.c.demand_id == p["demand_id"].astext,
                    tuple_(queue_use.c.request_id, queue_use.c.generation)
                    == tuple_(queue_packet.c.request_id, queue_packet.c.generation),
                    queue_use.c.fate == "attached",
                    func.ops.ddo_demand_active(queue_use.c.demand_id, type_=Boolean()),
                )
                .exists(),
            ),
        )
        .order_by(queue_packet.c.created_at, queue_packet.c.id)
        .limit(_value("lim", Integer()))
    )
    queue_fields = tuple(queue_projection.selected_columns)
    queue_targets = tuple("queue_" + column.name for column in queue_fields)
    queue_values = {
        column.name: _value(target, column.type)
        for column, target in zip(queue_fields, queue_targets, strict=True)
    }
    queue_steps = (
        Assign("lim", func.coalesce(cast(p["limit"].astext, Integer()), 1)),
        _check(~_value("lim", Integer()).between(1, 64), "invalid external queue bound"),
        Assign("result", _json("[]")),
        ForQuery(
            queue_targets,
            queue_projection,
            (
                PerformQuery(
                    select(func.ops.ddo_authorize_request(requests.table_valued())).where(
                        requests.c.id == queue_values["request_id"]
                    )
                ),
                Assign(
                    "result",
                    _value("result", JSONB()).op("||")(
                        func.jsonb_build_array(
                            _object(
                                packet_id=queue_values["id"],
                                packet_digest=queue_values["payload_digest"],
                                **{
                                    field: queue_values[field]
                                    for field in (
                                        "request_id",
                                        "generation",
                                        "task_id",
                                        "operation_id",
                                        "subject",
                                    )
                                },
                                state="awaiting-external",
                            )
                        )
                    ),
                ),
            ),
        ),
        result(packets=_value("result", JSONB())),
    )
    queue_contract = definitions[wire_requests["read_external_data_queue"]]
    queue_sql = procedure(
        "read_external_data_queue",
        (Parameter("p_payload", pg_type("jsonb")),),
        (
            Perform(
                func.ops.ddo_fields(
                    p,
                    array(queue_contract["required"], type_=Text()),
                    array(
                        [
                            field
                            for field in queue_contract["properties"]
                            if field not in queue_contract["required"]
                        ],
                        type_=Text(),
                    ),
                )
            ),
            *queue_steps,
        ),
        (
            *locals_for(("p", "lim", "result")),
            *(
                Local(
                    target,
                    column_type(
                        packets.c[column.name]
                        if column.name in packets.c
                        else requests.c[column.name]
                    ),
                )
                for column, target in zip(queue_fields, queue_targets, strict=True)
            ),
        ),
    )
    claim_sql = wire(
        "claim_external_data_packet",
        (
            selected_row(packets, packets.c.id == p["packet_id"].astext, "packet"),
            request_select,
            authorize,
            _check(
                or_(
                    r("project_id") != p["project_id"].astext,
                    and_(p.bool_op("?")("demand_id"), ~current_use),
                ),
                "external packet is outside the selected project/demand",
            ),
            If(
                tuple_(r("generation"), r("live_task_id")).is_distinct_from(
                    tuple_(packet("generation"), packet("task_id"))
                ),
                (result(state="no-work"),),
            ),
            Return(
                func.ops.ddo_claim_data_request(
                    _object(
                        request_id=r("id"),
                        generation=packet("generation"),
                        external_packet_id=packet("id"),
                        holder=p["holder"].astext,
                        lease_seconds=p["lease_seconds"],
                    )
                )
            ),
        ),
        ("packet", "r"),
    )
    read_sql = wire(
        "read_external_data_packet",
        (
            packet_select,
            request_select,
            authorize,
            receipt_select,
            If(
                and_(receipt("id").is_not(None), receipt_fence.is_not_distinct_from(payload_fence)),
                (
                    _check(
                        canonical_size(packet("payload")) > capacity,
                        "historical external packet exceeds transport capacity",
                    ),
                    packet_read_result,
                ),
            ),
            lock_support,
            lock_request,
            claim,
            assert_active,
            assert_support,
            _check(
                or_(
                    t("id") != packet("task_id"),
                    packet("payload")["binding"].is_distinct_from(r("binding")),
                    packet("payload")["recipe"].astext != r("recipe"),
                ),
                "external packet changed native request binding",
            ),
            _check(
                canonical_size(packet("payload")) > capacity,
                "external packet exceeds transport capacity",
            ),
            packet_read_result,
        ),
        ("r", "packet", "t", "receipt"),
    )
    external_receipts = func.coalesce(
        completion["execution_evidence"]["external_receipts"], _json("[]")
    )
    wire_receipt = _value("wire", JSONB())
    require_sql = procedure(
        "ddo_require_external_completion",
        (
            Parameter("completion", pg_type("jsonb")),
            Parameter("r", pg_type(str(requests.schema), requests.name)),
            Parameter("producer_task", pg_type("bigint")),
            Parameter("producer_attempt", pg_type("bigint")),
            Parameter("producer_holder", pg_type("text")),
        ),
        (
            definition_select,
            If(
                definition("support_contract")["external"].is_(None),
                (
                    _check(
                        external_receipts != _json("[]"),
                        "non-external operation cannot assert an external receipt",
                    ),
                    Return(),
                ),
            ),
            _check(
                or_(
                    func.jsonb_array_length(external_receipts) != 1,
                    *(
                        func.coalesce(completion["execution_evidence"][name], _json("[]"))
                        != _json("[]")
                        for name in (
                            "host_receipts",
                            "cpu_receipts",
                            "provider_receipts",
                            "pdf_receipts",
                            "pdf_observation_receipts",
                        )
                    ),
                ),
                "external completion requires exactly its genuine native admission receipt",
            ),
            Assign("wire", completion["execution_evidence"]["external_receipts"][0]),
            selected_row(receipts, receipts.c.id == wire_receipt["receipt_id"].astext, "receipt"),
            selected_row(packets, packets.c.id == receipt("packet_id"), "packet"),
            _check(
                or_(
                    wire_receipt.is_distinct_from(receipt_value),
                    receipt_fence.is_distinct_from(request_fence),
                    receipt("packet_digest") != packet("payload_digest"),
                    packet("payload")["binding"].is_distinct_from(r("binding")),
                    receipt("result_digest")
                    != func.ops.ddo_digest(completion.op("-")("execution_evidence")),
                ),
                "external receipt is not bound to this exact packet/result/native producer",
            ),
        ),
        (*locals_for(("definition", "receipt", "packet")), Local("wire", pg_type("jsonb"))),
        returns="void",
        volatility="volatile",
    )
    output_rows = _elements(completion["outputs"], "external_output")
    included = (
        func.ops.ddo_body_kind_contracts(
            output_rows.c.value["product"]["kind_contract"].astext,
            func.data.ddo_normalize(output_rows.c.value["product"]["body"]),
        )
        .table_valued(column("kind_contract", Text()))
        .render_derived(name="included")
        .lateral("included")
    )
    admitted_evidence = _object(
        version="native-execution-evidence-v1",
        request_id=r("id"),
        generation=r("generation"),
        task_id=t("id"),
        attempt=t("attempt"),
        holder=t("claimed_by"),
        runtime_id=packet("runtime_id"),
        host_receipts=_json("[]"),
        cpu_receipts=_json("[]"),
        pdf_receipts=_json("[]"),
        provider_receipts=_json("[]"),
        external_receipts=func.jsonb_build_array(receipt_value),
    )
    admit_sql = wire(
        "admit_external_data_result",
        (
            packet_select,
            request_select,
            authorize,
            Assign("completion", p["completion"]),
            _check(
                completion.bool_op("?")("execution_evidence"),
                "external callers cannot manufacture execution custody",
            ),
            Assign("digest_", func.ops.ddo_digest(completion)),
            receipt_select,
            replay,
            lock_support,
            lock_request,
            receipt_select,
            replay,
            claim,
            assert_active,
            assert_support,
            _check(
                or_(
                    packet("payload")["binding"].is_distinct_from(r("binding")),
                    packet("payload")["recipe"].astext != r("recipe"),
                    t("id") != packet("task_id"),
                    packet("payload")["protocol"]["requested_actor"].astext.is_distinct_from(
                        p["actor_assertion"].astext
                    ),
                    packet("payload")["protocol"]["requested_model"].astext.is_distinct_from(
                        p["model_assertion"].astext
                    ),
                ),
                "external result differs from exact packet/native claim/actor/model assertion contract",
            ),
            _check(
                or_(
                    completion["inputs"].is_distinct_from(r("binding")["inputs"]),
                    completion["support"].is_distinct_from(r("binding")["support"]),
                    completion["implementation_revision"].astext.is_distinct_from(
                        packet("payload")["implementation_revision"].astext
                    ),
                ),
                "external result changes its immutable input/implementation binding",
            ),
            _check(
                select(included.c.kind_contract)
                .select_from(
                    output_rows.join(included, literal(True)).join(
                        kinds, kinds.c.kind_contract == included.c.kind_contract
                    )
                )
                .where(kinds.c.universe == "evaluator")
                .exists(),
                "protected evaluator data cannot leave an external packet",
            ),
            Assign(
                "key",
                literal("external-result:")
                + func.ops.ddo_digest(func.jsonb_build_array(packet("id"), digest)),
            ),
            SelectInto(
                insert(receipts)
                .values(
                    id=key,
                    packet_id=packet("id"),
                    packet_digest=packet("payload_digest"),
                    request_id=r("id"),
                    generation=r("generation"),
                    task_id=t("id"),
                    attempt=t("attempt"),
                    holder=t("claimed_by"),
                    runtime_id=packet("runtime_id"),
                    admitting_principal=func.session_user(),
                    actor_assertion=p["actor_assertion"].astext,
                    model_assertion=p["model_assertion"].astext,
                    result_digest=digest,
                    created_at=func.clock_timestamp(),
                )
                .returning(*receipts.c),
                ("receipt",),
            ),
            Assign("evidence", admitted_evidence),
            Assign("completion", completion.op("||")(_object(execution_evidence=evidence))),
            Assign(
                "retained",
                func.ops.retain_data_completion_intent(
                    _object(
                        request_id=r("id"),
                        generation=r("generation"),
                        task_id=t("id"),
                        attempt=t("attempt"),
                        holder=t("claimed_by"),
                        runtime_id=packet("runtime_id"),
                        completion=completion,
                    )
                ),
            ),
            result(receipt=receipt_value, intent_id=retained["payload"]["intent_id"].astext),
        ),
        (
            "r",
            "t",
            "packet",
            "receipt",
            "completion",
            "evidence",
            "retained",
            "digest_",
            "key",
            "intent",
        ),
    )
    publication = _value("publication", JSONB())
    inspect_sql = wire(
        "inspect_external_data_result",
        (
            selected_row(packets, packets.c.id == p["packet_id"].astext, "packet"),
            request_select,
            authorize,
            receipt_select,
            SelectInto(
                select(intents.c.id).where(
                    intents.c.request_id == packet("request_id"),
                    intents.c.generation == packet("generation"),
                ),
                ("intent",),
            ),
            If(
                intent.is_not(None),
                (
                    Assign(
                        "publication",
                        func.ops.inspect_data_completion(
                            _object(
                                intent_id=intent,
                                request_id=packet("request_id"),
                                generation=packet("generation"),
                            ),
                            type_=JSONB(),
                        )["payload"],
                    ),
                ),
            ),
            Assign(
                "state_",
                case(
                    (publication["state"].astext == "committed", "committed"),
                    (r("generation") != packet("generation"), "superseded"),
                    (~func.ops.ddo_request_useful(request_row, type_=Boolean()), "cancelled"),
                    (receipt("id").is_not(None), "retained"),
                    else_="awaiting-external",
                ),
            ),
            result(
                packet_id=packet("id"),
                state=_value("state_"),
                receipt=case((receipt("id").is_(None), null()), else_=receipt_value),
                intent_id=intent,
                publication=publication,
            ),
        ),
        ("r", "packet", "receipt", "intent", "publication", "state_"),
    )
    release_sql = wire(
        "release_external_data_packet",
        (
            packet_select,
            selected_row(requests, requests.c.id == packet("request_id"), "r", lock=True),
            authorize,
            selected_row(tasks, tasks.c.id == packet("task_id"), "t", lock=True),
            _check(
                or_(
                    tuple_(
                        r("generation"), t("id"), t("attempt"), t("claimed_by")
                    ).is_distinct_from(
                        tuple_(
                            cast(p["generation"].astext, BigInteger()),
                            cast(p["task_id"].astext, BigInteger()),
                            cast(p["attempt"].astext, BigInteger()),
                            p["holder"].astext,
                        )
                    ),
                    ~t("status").in_(("running", "pending")),
                ),
                "external release lost its exact packet/attempt fence",
            ),
            _check(
                select(receipts.c.id).where(receipts.c.packet_id == packet("id")).exists(),
                "retained external result requires publication reconciliation, not release",
            ),
            Sql(
                update(tasks)
                .where(tasks.c.id == t("id"))
                .values(
                    status="pending",
                    lease_until=null(),
                    error=_object(
                        external_release=p["reason"].astext, physical_retirement="not-asserted"
                    ),
                )
            ),
            result(packet_id=packet("id"), state="awaiting-external", released=True),
        ),
        ("r", "t", "packet"),
    )
    routines = (
        inputs_sql,
        receipt_sql,
        active_sql,
        retain_sql,
        queue_sql,
        claim_sql,
        read_sql,
        require_sql,
        admit_sql,
        inspect_sql,
        release_sql,
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in routines
    )


def external_execution_native_sql(model, protocol: bytes) -> str:
    """Render the existing external execution capture before wire-name projection."""
    return "\n".join(
        declaration.routine.render() + ";\n"
        for declaration in external_execution_native_programs(model, protocol)
    )
