"""Generate fenced request renewal against the captured native domain and tables."""

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
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    core_variable,
    function,
    pg_type,
    sql_function,
)


def renewal_native_sql(target, protocol: bytes) -> str:
    definitions = yaml.safe_load(protocol)["definitions"]
    request_contract = definitions["renew_data_request_request"]
    request = target.tables["ops.data_request"]
    task = target.tables["ops.task"]
    revocation = target.tables["ops.data_revocation"]
    p = core_variable("p", JSONB())
    payload = core_variable("p_payload", JSONB())
    r = core_variable("r", Text())
    snapshot = core_variable("snapshot", JSONB())
    reason = core_variable("reason", Text())

    def request_field(name):
        return core_variable("r", request.c[name].type, name)

    def task_field(name):
        return core_variable("t", task.c[name].type, name)

    generation = cast(p["generation"].astext, request.c.generation.type)
    task_id = cast(p["task_id"].astext, task.c.id.type)
    attempt = cast(p["attempt"].astext, task.c.attempt.type)
    lease = cast(p["lease_seconds"].astext, Integer())
    holder = p["holder"].astext
    object_ = func.pg_catalog.jsonb_build_object
    lost = sql_function(
        "ops",
        "ddo_lost_attempt",
        parameters=(Parameter("p", pg_type("jsonb")), Parameter("reason", pg_type("text"))),
        returns=pg_type("jsonb"),
        body=select(
            object_(
                "payload",
                object_(
                    "state",
                    "lost",
                    "reason",
                    reason,
                    "request_id",
                    p["request_id"].astext,
                    "generation",
                    generation,
                    "task_id",
                    task_id,
                    "attempt",
                    attempt,
                    "holder",
                    holder,
                ),
            )
        ),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )

    def lost_result(value):
        return Return(func.ops.ddo_lost_attempt(p, value))

    stale_fence = or_(
        task_field("id").is_(None),
        request_field("generation").is_distinct_from(generation),
        tuple_(
            task_field("data_request_id"),
            task_field("data_generation"),
            task_field("id"),
            task_field("attempt"),
            task_field("claimed_by"),
        ).is_distinct_from(
            tuple_(request_field("id"), request_field("generation"), task_id, attempt, holder)
        ),
        task_field("status").is_distinct_from("running"),
        task_field("lease_until").is_(None),
        task_field("lease_until") <= func.clock_timestamp(),
    )
    revoked = exists(
        select(1)
        .select_from(revocation)
        .where(
            revocation.c.scope
            == func.ops.ddo_scope(request_field("project_id"), request_field("original_source")),
            or_(
                (revocation.c.selector_kind == "runtime")
                & (revocation.c.selector == request_field("runtime_id")),
                (revocation.c.selector_kind == "recipe")
                & (revocation.c.selector == request_field("recipe")),
            ),
        )
    )
    lease_contract = request_contract["properties"]["lease_seconds"]
    renew = function(
        "ops",
        "renew_data_request",
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                Perform(
                    func.ops.ddo_fields(
                        p, array(list(request_contract["properties"]), type_=Text())
                    )
                ),
                If(
                    or_(
                        func.nullif(holder, "").is_(None),
                        ~lease.between(lease_contract["minimum"], lease_contract["maximum"]),
                        generation < definitions["positive_integer"]["minimum"],
                        attempt < definitions["positive_integer"]["minimum"],
                        task_id < 1,
                    ),
                    (Raise("invalid request attempt/holder/lease", "P0001"),),
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
                        request_field("project_id"),
                        request_field("original_source"),
                        request_field("binding")["support"],
                    ),
                ),
                SelectInto(
                    select(request).where(request.c.id == request_field("id")).with_for_update(),
                    ("r",),
                    strict=True,
                ),
                SelectInto(
                    select(task)
                    .where(task.c.id == request_field("live_task_id"))
                    .with_for_update(),
                    ("t",),
                ),
                If(
                    ~func.ops.ddo_request_useful(r, type_=Boolean()),
                    (
                        lost_result(
                            case(
                                (task_field("status").in_(("done", "empty", "failed")), "fence"),
                                else_="cancelled",
                            )
                        ),
                    ),
                ),
                If(stale_fence, (lost_result("fence"),)),
                If(revoked, (lost_result("revoked"),)),
                If(
                    ~func.ops.ddo_support_available(
                        r, request_field("binding")["support"], type_=Boolean()
                    ),
                    (lost_result("support-unavailable"),),
                ),
                SelectInto(
                    update(task)
                    .where(task.c.id == task_field("id"))
                    .values(
                        lease_until=func.greatest(
                            task_field("lease_until"),
                            func.clock_timestamp()
                            + func.make_interval(0, 0, 0, 0, 0, 0, lease, type_=Interval()),
                        ),
                    )
                    .returning(*task.c),
                    ("t",),
                ),
                Return(
                    object_(
                        "payload",
                        object_(
                            "state",
                            "renewed",
                            "request_id",
                            request_field("id"),
                            "generation",
                            request_field("generation"),
                            "task_id",
                            task_field("id"),
                            "attempt",
                            task_field("attempt"),
                            "holder",
                            task_field("claimed_by"),
                            "lease_until",
                            task_field("lease_until"),
                            "trust_snapshot",
                            snapshot,
                        ),
                    )
                ),
            ),
            locals=(
                Local("p", pg_type("jsonb"), payload),
                Local("r", request),
                Local("t", task),
                Local("snapshot", pg_type("jsonb")),
            ),
        ),
    )
    return lost + ";\n" + renew + ";\n"
