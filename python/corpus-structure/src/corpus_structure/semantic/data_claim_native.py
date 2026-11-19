"""Generate the exact single-request claim and attempt-fence checks."""

import yaml
from sqlalchemy import (
    Boolean,
    Integer,
    Interval,
    Text,
    case,
    cast,
    exists,
    func,
    literal,
    or_,
    select,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, array

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
    core_variable,
    pg_type,
)


def claim_native_programs(target, protocol: bytes) -> tuple[NativeRoutine, ...]:
    contract = yaml.safe_load(protocol)["definitions"]["claim_data_request_request"]
    request = target.tables["ops.data_request"]
    task = target.tables["ops.task"]
    packet = target.tables["ops.data_external_packet"]
    use = target.tables["ops.demand_use"]
    intents = target.tables["ops.data_completion_intent"]
    consumptions = target.tables["ops.data_draft_consumption"]
    receipts = target.tables["ops.data_publication_receipt"]
    r = core_variable("r", Text())
    p = core_variable("p", JSONB())
    t = core_variable("t", Text())
    snapshot = core_variable("snapshot", JSONB())
    retained = core_variable("retained_id", intents.c.id.type)
    object_ = func.pg_catalog.jsonb_build_object

    def row(variable, relation, name):
        return core_variable(variable, relation.c[name].type, name)

    def rf(name):
        return row("r", request, name)

    def tf(name):
        return row("t", task, name)

    def pf(name):
        return row("packet", packet, name)

    task_fence = tuple_(
        tf("data_request_id"), tf("data_generation"), tf("id"), tf("attempt"), tf("claimed_by")
    )
    payload_fence = tuple_(
        rf("id"),
        rf("generation"),
        cast(p["task_id"].astext, task.c.id.type),
        cast(p["attempt"].astext, Integer()),
        p["holder"].astext,
    )
    stale = or_(
        task_fence.is_distinct_from(payload_fence),
        rf("generation").is_distinct_from(cast(p["generation"].astext, Integer())),
        tf("status").is_distinct_from("running"),
        tf("lease_until").is_(None),
        tf("lease_until") <= func.clock_timestamp(),
    )
    fence_guard = NativeRoutine(
        "ops",
        "ddo_claim",
        parameters=(
            Parameter("r", pg_type(str(request.schema), request.name)),
            Parameter("p", pg_type("jsonb")),
        ),
        returns=pg_type(str(task.schema), task.name),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                Perform(func.ops.ddo_authorize_request(r)),
                If(
                    ~func.ops.ddo_request_useful(r, type_=Boolean()),
                    (Raise("data request has no attached demand interest", "P0001"),),
                ),
                SelectInto(
                    select(task).where(task.c.id == rf("live_task_id")).with_for_update(),
                    ("t",),
                    strict=True,
                ),
                If(stale, (Raise("stale data task attempt fence", "23514"),)),
                Return(t),
            ),
            (Local("t", task),),
        ),
    )
    no_work = Return(object_("payload", object_("state", "no-work")))
    retained_query = select(intents.c.id).where(
        intents.c.request_id == rf("id"),
        or_(
            intents.c.generation == rf("generation"),
            select(1)
            .select_from(consumptions)
            .where(
                consumptions.c.intent_id == intents.c.id,
                consumptions.c.request_id == rf("id"),
                consumptions.c.generation == rf("generation"),
            )
            .exists(),
        ),
        ~exists(select(1).select_from(receipts).where(receipts.c.intent_id == intents.c.id)),
    )
    binding = rf("binding").op("-", return_type=JSONB())(literal("execution_profile"))
    lease = cast(p["lease_seconds"].astext, Integer())
    single_claim = NativeRoutine(
        "ops",
        "ddo_claim_data_request",
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
                If(
                    or_(
                        func.nullif(p["holder"].astext, "").is_(None),
                        ~lease.between(
                            contract["properties"]["lease_seconds"]["minimum"],
                            contract["properties"]["lease_seconds"]["maximum"],
                        ),
                    ),
                    (Raise("invalid holder/lease", "23514"),),
                ),
                SelectInto(
                    select(request).where(request.c.id == p["request_id"].astext),
                    ("r",),
                    strict=True,
                ),
                Perform(func.ops.ddo_authorize_request(r)),
                Assign(
                    "snapshot",
                    func.ops.ddo_lock_support(
                        rf("project_id"), rf("original_source"), rf("binding")["support"]
                    ),
                ),
                SelectInto(
                    select(request).where(request.c.id == rf("id")).with_for_update(),
                    ("r",),
                    strict=True,
                ),
                If(
                    rf("generation").is_distinct_from(cast(p["generation"].astext, Integer())),
                    (no_work,),
                ),
                If(~func.ops.ddo_request_useful(r, type_=Boolean()), (no_work,)),
                SelectInto(
                    select(task).where(task.c.id == rf("live_task_id")).with_for_update(),
                    ("t",),
                    strict=True,
                ),
                SelectInto(
                    select(packet).where(
                        packet.c.request_id == rf("id"), packet.c.generation == rf("generation")
                    ),
                    ("packet",),
                ),
                SelectInto(retained_query, ("retained_id",)),
                If(
                    p.has_key("external_packet_id")
                    & or_(
                        pf("id").is_(None),
                        pf("id") != p["external_packet_id"].astext,
                        pf("task_id") != tf("id"),
                    ),
                    (Raise("external claim differs from its exact current packet/task", "23514"),),
                ),
                If(
                    pf("id").is_not(None)
                    & retained.is_(None)
                    & p["external_packet_id"].astext.is_distinct_from(pf("id")),
                    (no_work,),
                ),
                If(
                    (tf("status") == "running") & tf("lease_until").is_(None),
                    (Raise("running task has no publication lease", "P0001"),),
                ),
                If(
                    or_(
                        ~tf("status").in_(("pending", "running")),
                        (tf("status") == "running") & (tf("lease_until") > func.clock_timestamp()),
                    ),
                    (no_work,),
                ),
                Perform(func.ops.ddo_assert_support(r, rf("binding")["support"])),
                If(pf("id").is_not(None), (Perform(func.ops.ddo_assert_external_active(r)),)),
                SelectInto(
                    select(use)
                    .where(
                        use.c.request_id == rf("id"),
                        use.c.generation == rf("generation"),
                        use.c.selection == binding,
                    )
                    .order_by(use.c.id)
                    .limit(1),
                    ("binding_use",),
                    strict=True,
                ),
                SelectInto(
                    update(task)
                    .where(task.c.id == tf("id"))
                    .values(
                        status="running",
                        attempt=task.c.attempt + 1,
                        claimed_by=p["holder"].astext,
                        lease_until=func.clock_timestamp()
                        + func.make_interval(0, 0, 0, 0, 0, 0, lease, type_=Interval()),
                        started_at=func.coalesce(task.c.started_at, func.clock_timestamp()),
                    )
                    .returning(*task.c),
                    ("t",),
                ),
                SelectInto(retained_query, ("retained_id",)),
                Return(
                    object_(
                        "payload",
                        object_(
                            "state",
                            "claimed",
                            "request_id",
                            rf("id"),
                            "release_id",
                            rf("release_id"),
                            "runtime_id",
                            rf("runtime_id"),
                            "binding",
                            binding,
                            "binding_demand_id",
                            row("binding_use", use, "demand_id"),
                            "binding_obligation_id",
                            row("binding_use", use, "obligation_id"),
                            "generation",
                            rf("generation"),
                            "task_id",
                            tf("id"),
                            "attempt",
                            tf("attempt"),
                            "holder",
                            tf("claimed_by"),
                            "lease_until",
                            tf("lease_until"),
                            "trust_snapshot",
                            snapshot,
                            "action",
                            case((retained.is_(None), "compute"), else_="reconcile"),
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
                Local("snapshot", pg_type("jsonb")),
                Local("retained_id", pg_type("text")),
                Local("packet", packet),
                Local("binding_use", use),
            ),
        ),
    )
    return (fence_guard, single_claim)


def claim_native_sql(target, protocol: bytes) -> str:
    from .native_objects import native_sql_script

    return (
        native_sql_script(routine.render() for routine in claim_native_programs(target, protocol))
        + "\n"
    )
