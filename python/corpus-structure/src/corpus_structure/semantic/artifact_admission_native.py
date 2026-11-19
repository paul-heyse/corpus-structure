"""Compile artifact CPU result correspondence over captured physical contracts."""

from sqlalchemy import MetaData, Text, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name

from .metadata import get_metadata
from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration, ProgramValidity
from .validity_programs import selected_family


def artifact_admission_native_programs(
    *, target_metadata: MetaData | None = None
) -> tuple[ProgramDeclaration, ...]:
    model = get_metadata() if target_metadata is None else target_metadata
    definition = model.tables["sem.data_operation_definition"]
    request = model.tables["ops.data_request"]
    episode = model.tables["ops.data_derivation"]
    intent = model.tables["ops.data_completion_intent"]

    def row(name, table, field=None):
        return core_variable(
            name, table.table_valued().type if field is None else table.c[field].type, field
        )

    def lookup(name, table, *conditions):
        return SelectInto(
            select(core_relation_row(table)).select_from(table).where(*conditions),
            (name,),
            strict=True,
        )

    def json(value):
        return cast(literal(value), JSONB())

    def reject(condition, message):
        return If(condition, (Raise(message, "23514"),))

    def r(field=None):
        return row("r", request, field)

    def d(field):
        return row("definition", definition, field)

    def e(field=None):
        return row("episode", episode, field)

    completion = core_variable("completion", JSONB())
    actual = core_variable("actual", JSONB())
    expected = core_variable("expected", JSONB())
    output = core_variable("output", JSONB())
    result_field = core_variable("result_field", Text())
    support = d("support_contract")
    factory = support["capabilities"]["prepared_factory"]
    request_parameters = (
        Parameter("r", pg_type(str(request.schema), request.name)),
        Parameter("completion", pg_type("jsonb")),
    )
    definition_lookup = lookup(
        "definition",
        definition,
        definition.c.release_id == r("release_id"),
        definition.c.operation_id == r("operation_id"),
    )
    programs: list[ProgramDeclaration] = []

    def add(name, parameters, steps, locals_=(), *, returns="void", validity=()):
        programs.append(
            ProgramDeclaration(
                NativeRoutine(
                    "ops",
                    name,
                    parameters=parameters,
                    returns=pg_type(returns),
                    body=Block(tuple(steps), tuple(locals_)),
                    security_definer=True,
                    volatility="stable",
                    search_path=("pg_catalog", "pg_temp"),
                ),
                source="data-operations:forward",
                owner=role_name("publisher"),
                access=INTERNAL_PROGRAM,
                validity=validity,
            )
        )

    add(
        "ddo_require_artifact_producer",
        request_parameters,
        (
            definition_lookup,
            reject(
                or_(
                    ~selected_family(model, r("release_id"), r("operation_id"), "artifact"),
                    func.nullif(factory["entrypoint"].astext, "").is_(None),
                    factory["source_digest"].astext.op("~")("^[0-9a-f]{64}$").is_not(True),
                    d("implementation_revision").like("implementation-slice:%").is_not(True),
                    d("profile").is_distinct_from("derivation"),
                    d("recipe").is_distinct_from(r("recipe")),
                    support["capabilities"]["forms"].is_distinct_from(json('["scalar"]')),
                    support["capabilities"]["preparation"].astext.is_distinct_from("resource"),
                    support["effects"].is_distinct_from(json("[]")),
                    completion["implementation_revision"].astext.is_distinct_from(
                        d("implementation_revision")
                    ),
                    func.jsonb_array_length(
                        func.coalesce(completion["execution_evidence"]["cpu_receipts"], json("[]"))
                    )
                    != 1,
                ),
                "artifact completion lacks its actual captured scalar CPU producer",
            ),
        ),
        (Local("definition", definition),),
    )

    outputs = (
        func.jsonb_array_elements(completion["outputs"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="outputs_")
    )
    add(
        "ddo_require_artifact_completion",
        request_parameters,
        (
            If(
                ~selected_family(model, r("release_id"), r("operation_id"), "artifact"),
                (Return(),),
            ),
            Perform(func.ops.ddo_require_artifact_producer(r(), completion)),
            definition_lookup,
            Assign("actual", func.ops.ddo_cpu_reply_output(r(), completion, type_=JSONB())),
            reject(
                func.jsonb_typeof(support["result_fields"]).is_distinct_from("object"),
                "artifact output lacks its actual admitted result-field projection",
            ),
            ForQuery(
                ("output",),
                select(outputs.c.value),
                (
                    Assign("expected", actual),
                    If(
                        support["result_fields"] != json("{}"),
                        (
                            Assign(
                                "result_field",
                                support["result_fields"][output["role"].astext].astext,
                            ),
                            reject(
                                result_field.is_(None),
                                "artifact output lacks its exact admitted result field",
                            ),
                            Assign(
                                "expected", func.data.ddo_field(actual, result_field, type_=JSONB())
                            ),
                        ),
                        (
                            reject(
                                or_(
                                    func.jsonb_array_length(d("output_roles")) != 1,
                                    d("output_roles")[0]["name"].astext.is_distinct_from(
                                        output["role"].astext
                                    ),
                                ),
                                "artifact CPU reply requires its actual admitted single output contract",
                            ),
                        ),
                    ),
                    reject(
                        expected.is_distinct_from(
                            func.data.ddo_normalize(output["product"]["body"], type_=JSONB())
                        ),
                        "artifact publication differs from its actual exact-input CPU reply",
                    ),
                ),
            ),
        ),
        (
            Local("definition", definition),
            Local("output", pg_type("jsonb")),
            Local("actual", pg_type("jsonb")),
            Local("expected", pg_type("jsonb")),
            Local("result_field", pg_type("text")),
        ),
        validity=(ProgramValidity("artifact", "completion_guard"),),
    )

    episode_id = core_variable("episode_id", episode.c.id.type)
    add(
        "ddo_artifact_dependencies_valid",
        (Parameter("episode_id", column_type(episode.c.id)),),
        (
            CatchDependencyInvalidity(
                (
                    lookup("episode", episode, episode.c.id == episode_id),
                    lookup("r", request, request.c.id == e("request_id")),
                    If(
                        ~selected_family(model, r("release_id"), r("operation_id"), "artifact"),
                        (Return(literal(True)),),
                    ),
                    If(e("outcome") != "success", (Return(literal(False)),)),
                    lookup(
                        "intent",
                        intent,
                        intent.c.id == e("intent_id"),
                        intent.c.request_id == e("request_id"),
                        intent.c.generation == e("generation"),
                    ),
                    Assign(
                        "r", func.ops.ddo_require_episode_correspondence(e(), row("intent", intent))
                    ),
                    Return(literal(True)),
                ),
                (Return(literal(False)),),
            ),
        ),
        (Local("episode", episode), Local("r", request), Local("intent", intent)),
        returns="bool",
        validity=(ProgramValidity("artifact", "validator"),),
    )
    return tuple(programs)


def artifact_admission_native_sql(*, target_metadata: MetaData | None = None) -> str:
    """Render captured declarations and their existing private ACL projection."""
    return (
        native_sql_script(
            statement
            for declaration in artifact_admission_native_programs(target_metadata=target_metadata)
            for statement in (
                declaration.routine.render(),
                native_privilege_sql(declaration.identity, "PUBLIC", grant=False),
            )
        )
        + "\n"
    )
