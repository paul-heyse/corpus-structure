"""Generate the ordered set claim boundary with exact per-item refusal semantics."""

from sqlalchemy import Text, column, exists, func, select
from sqlalchemy.dialects.postgresql import JSONB

from .native_program import (
    Assign,
    Block,
    CatchCheckViolation,
    Continue,
    ForQuery,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    core_variable,
    function,
    pg_type,
)


def claim_batch_native_sql(target):
    request = target.tables["ops.data_request"]
    p = core_variable("p", JSONB())
    item = core_variable("item", JSONB())
    result = core_variable("result", JSONB())
    results = core_variable("results", JSONB())
    cached = core_variable("cached", JSONB())
    cache_key = core_variable("cache_key", Text())
    object_ = func.pg_catalog.jsonb_build_object
    array_ = func.pg_catalog.jsonb_build_array

    def append(value, other):
        return value.op("||", return_type=JSONB())(other)

    items = func.pg_catalog.jsonb_array_elements(p["items"]).table_valued(column("value", JSONB())).render_derived(name="claim_item")
    return function(
        "ops", "claim_data_requests", parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"), security_definer=True, search_path=("pg_catalog", "pg_temp"),
        body=Block((
            ForQuery(("item",), select(items.c.value), (
                Assign("cache_key", func.ops.ddo_digest(item)),
                If(cached.has_key(cache_key), (
                    Assign("results", append(results, array_(cached[cache_key]))), Continue(),
                )),
                CatchCheckViolation((
                    If(~exists(select(1).select_from(request).where(request.c.id == item["request_id"].astext)), (Raise("claim item request is absent", "23514"),)),
                    Assign("result", func.ops.ddo_claim_data_request(append(item, object_("holder", p["holder"].astext, "lease_seconds", p["lease_seconds"])), type_=JSONB())["payload"]),
                    If(result["state"].astext == "claimed", (Assign("result", object_("state", "claimed", "result", result)),)),
                ), (
                    Assign("result", object_("state", "refused", "sqlstate", core_variable("sqlstate", Text()), "reason", core_variable("sqlerrm", Text()))),
                )),
                Assign("cached", append(cached, object_(cache_key, result))),
                Assign("results", append(results, array_(result))),
            )),
            Return(object_("payload", object_("items", results))),
        ), (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())), Local("item", pg_type("jsonb")),
            Local("result", pg_type("jsonb")), Local("results", pg_type("jsonb"), array_()),
            Local("cached", pg_type("jsonb"), object_()), Local("cache_key", pg_type("text")),
        )),
    ) + ";\n"
