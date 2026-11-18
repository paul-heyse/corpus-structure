"""PDF completion proof over sealed publication and the captured command model."""

import json
from dataclasses import asdict

from sqlalchemy import MetaData, Text, and_, case, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    SelectInto,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
)
from .pdf_effect_contract import (
    PDF_CAPTURE_EFFECT,
    PDF_CAPTURE_FACTORY,
    PDF_ENRICHMENT_EFFECT,
    PDF_ENRICHMENT_FACTORY,
    PDF_INTEGRATION_EFFECT,
    PDF_INTEGRATION_FACTORY,
    PDF_ORGANIZATION_EFFECT,
    PDF_ORGANIZATION_FACTORY,
    PDF_RECOGNITION_EFFECT,
    PDF_RECOGNITION_FACTORY,
)


def pdf_completion_native_sql(model: MetaData) -> str:
    definitions = model.tables["sem.data_operation_definition"]
    requests = model.tables["ops.data_request"]
    approved = [
        {"factory": factory, "effects": [asdict(effect)]}
        for factory, effect in (
            (PDF_CAPTURE_FACTORY, PDF_CAPTURE_EFFECT),
            (PDF_ENRICHMENT_FACTORY, PDF_ENRICHMENT_EFFECT),
            (PDF_INTEGRATION_FACTORY, PDF_INTEGRATION_EFFECT),
            (PDF_ORGANIZATION_FACTORY, PDF_ORGANIZATION_EFFECT),
            (PDF_RECOGNITION_FACTORY, PDF_RECOGNITION_EFFECT),
        )
    ]

    def definition(field):
        return core_variable("definition", definitions.c[field].type, field)

    def json_value(value):
        return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB())

    contract = definition("support_contract")
    capabilities = contract["capabilities"]
    pairs = func.jsonb_array_elements(json_value(approved)).table_valued(column("value", JSONB()))
    eligible = sql_function(
        "ops",
        "ddo_pdf_command_eligible",
        parameters=(Parameter("definition", pg_type("sem", "data_operation_definition")),),
        returns=pg_type("bool"),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
        body=select(
            and_(
                definition("profile") == "command",
                capabilities["preparation"].astext == "pdf-native",
                capabilities["forms"] == json_value(["scalar"]),
                select(1)
                .select_from(pairs)
                .where(
                    contract["effects"] == pairs.c.value["effects"],
                    capabilities["prepared_factory"]["entrypoint"].astext
                    == pairs.c.value["factory"].astext,
                )
                .exists(),
                capabilities["prepared_factory"]["source_digest"].astext.bool_op("~")(
                    "^[0-9a-f]{64}$"
                ),
                definition("implementation_revision").like("implementation-slice:%"),
            )
        ),
    )
    completion = core_variable("p_completion", JSONB())
    task, attempt = (
        core_variable(name, model.tables["ops.task"].c.id.type) for name in ("p_task", "p_attempt")
    )
    holder, release, operation = (
        core_variable(name, Text()) for name in ("p_holder", "p_release", "p_operation")
    )
    receipts, observations, output, expected = (
        core_variable(name, JSONB()) for name in ("receipts", "observations", "output", "expected")
    )
    context_release = core_variable("context", requests.c.release_id.type, "release_id")
    context_request = core_variable("context", requests.c.id.type, "request_id")
    context = func.ops.pdf_task_context(task).table_valued(
        column("release_id", requests.c.release_id.type),
        column("request_id", requests.c.id.type),
    )
    empty = json_value([])
    recognition = contract["effects"][0]["name"].astext == "retain_pdf_observations"

    def reject(condition, message):
        return If(condition, (Raise(message, "23514"),))

    require = function(
        "ops",
        "ddo_require_pdf_completion",
        parameters=(
            Parameter("p_completion", pg_type("jsonb")),
            Parameter("p_task", pg_type("bigint")),
            Parameter("p_attempt", pg_type("bigint")),
            Parameter("p_holder", pg_type("text")),
            Parameter("p_release", pg_type("text")),
            Parameter("p_operation", pg_type("text")),
        ),
        returns=pg_type("void"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                SelectInto(
                    select(core_relation_row(definitions)).where(
                        definitions.c.release_id == release,
                        definitions.c.operation_id == operation,
                    ),
                    ("definition",),
                    strict=True,
                ),
                If(
                    capabilities["preparation"].astext.is_distinct_from("pdf-native"),
                    (
                        reject(
                            or_(receipts != empty, observations != empty),
                            "non-PDF computation cannot acquire a PDF execution event",
                        ),
                        Return(),
                    ),
                ),
                reject(
                    ~func.coalesce(definition("command_class") == "pdf", False),
                    "PDF completion requires its exact approved command/effect/factory pair",
                ),
                SelectInto(select(context), ("context",), strict=True),
                reject(
                    or_(
                        context_release.is_distinct_from(release),
                        ~select(1)
                        .select_from(requests)
                        .where(
                            requests.c.id == context_request,
                            requests.c.operation_id == operation,
                            requests.c.release_id == release,
                        )
                        .exists(),
                    ),
                    "PDF completion differs from actual request owner",
                ),
                If(
                    func.ops.ddo_completion_state(
                        core_variable("definition", JSONB()), completion["outcome"].astext
                    ).in_(("failed", "empty")),
                    (
                        reject(
                            or_(
                                receipts != empty,
                                observations != empty,
                                completion["outputs"] != empty,
                            ),
                            "non-success PDF completion cannot publish receipts or outputs",
                        ),
                        Return(),
                    ),
                ),
                If(
                    recognition,
                    (
                        reject(
                            or_(
                                receipts != empty,
                                func.jsonb_array_length(observations).is_distinct_from(1),
                            ),
                            "recognition completion requires only its actual observation-set receipt",
                        ),
                        reject(
                            observations[0]["runtime_id"].astext.is_distinct_from(
                                completion["execution_evidence"]["runtime_id"].astext
                            ),
                            "observation adoption changes its actual completion runtime",
                        ),
                    ),
                    (
                        reject(
                            or_(
                                observations != empty,
                                func.jsonb_array_length(receipts).is_distinct_from(1),
                            ),
                            "sealed PDF completion requires only its actual publication receipt",
                        ),
                    ),
                ),
                reject(
                    func.jsonb_array_length(completion["outputs"]).is_distinct_from(1),
                    "PDF completion requires one whole-product output",
                ),
                Assign("output", completion["outputs"][0]),
                reject(
                    or_(
                        output["member_id"].astext.is_not(None),
                        output["position"].astext.is_distinct_from("0"),
                        output["multiplicity"].astext.is_distinct_from("1"),
                        output["product"]["members"].is_distinct_from(empty),
                    ),
                    "PDF completion must name its one whole product",
                ),
                Assign(
                    "expected",
                    case(
                        (
                            recognition,
                            func.ops.pdf_observation_projection(
                                observations[0], task, attempt, holder
                            ),
                        ),
                        else_=func.ops.pdf_publication_projection(
                            receipts[0], task, attempt, holder
                        ),
                    ),
                ),
                reject(
                    func.data.ddo_json(output["product"]["body"]).is_distinct_from(expected),
                    "PDF output differs from authentic native effect projection",
                ),
            ),
            (
                Local("definition", definitions),
                Local("context", pg_type("record")),
                Local("output", pg_type("jsonb")),
                Local("expected", pg_type("jsonb")),
                Local(
                    "receipts",
                    pg_type("jsonb"),
                    func.coalesce(completion["execution_evidence"]["pdf_receipts"], empty),
                ),
                Local(
                    "observations",
                    pg_type("jsonb"),
                    func.coalesce(
                        completion["execution_evidence"]["pdf_observation_receipts"], empty
                    ),
                ),
            ),
        ),
    )
    return (
        native_sql_script(
            (
                eligible,
                native_privilege_sql(
                    NativeIdentity(
                        "function",
                        "ops",
                        "ddo_pdf_command_eligible",
                        ("sem.data_operation_definition",),
                    ),
                    "PUBLIC",
                    grant=False,
                ),
                require,
                native_privilege_sql(
                    NativeIdentity(
                        "function",
                        "ops",
                        "ddo_require_pdf_completion",
                        ("jsonb", "bigint", "bigint", "text", "text", "text"),
                    ),
                    "PUBLIC",
                    grant=False,
                ),
            )
        )
        + "\n"
    )
