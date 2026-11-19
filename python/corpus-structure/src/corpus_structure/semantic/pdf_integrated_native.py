"""Forward native realization of the model-owned PDF companion contract."""

from corpus_structure.schema.integrity import role_name

from .native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    native_owner_sql,
    native_privilege_sql,
    native_sql_script,
)
from .native_program_registry import ProgramDeclaration


def observation_publication_programs(context=None, *, target_metadata=None):
    """Compile protected observation definitions from current captured models."""
    from .metadata import get_metadata
    from .pdf_contracts import trusted_pdf_context
    from .pdf_observation_native import (
        observation_projection_routine,
        observation_publisher_routine,
    )

    context = trusted_pdf_context() if context is None else context
    model = get_metadata() if target_metadata is None else target_metadata
    meaning, policy, envelope = observation_value_routines(context, target_metadata=model)
    writer = NativeProgramAccess(purposes=("write",))
    return tuple(
        ProgramDeclaration(
            routine, "target-current:PDF publication", role_name("publisher"), access
        )
        for routine, access in (
            (meaning, INTERNAL_PROGRAM),
            (policy, INTERNAL_PROGRAM),
            (envelope, writer),
            (observation_projection_routine(context, model), INTERNAL_PROGRAM),
            (observation_publisher_routine(context, model), writer),
        )
    )


def observation_publication_sql(context=None, *, target_metadata=None) -> str:
    programs = observation_publication_programs(context, target_metadata=target_metadata)
    return (
        native_sql_script(
            (
                *(item.render() for item in programs),
                *(
                    statement
                    for item in programs
                    for statement in (
                        native_owner_sql(item.identity, item.owner),
                        native_privilege_sql(item.identity, "PUBLIC", grant=False),
                        *(
                            native_privilege_sql(
                                item.identity, role, privilege, grant_option=option
                            )
                            for role, privilege, option in item.access.grants(item.owner)
                        ),
                    )
                ),
            )
        )
        + "\n"
    )


def observation_value_routines(context, *, target_metadata=None):
    """Generate meaning, policy lookup and the current-request projection envelope."""
    from sqlalchemy import BigInteger, Text, cast, column, func, or_, select
    from sqlalchemy.dialects.postgresql import JSONB, array

    from .metadata import get_metadata
    from .native_program import (
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
    from .pdf_observations import (
        MEANING_SPEC,
        PROFILE_CONTRACT,
        PROFILE_REFERENCE,
        PROFILE_ROLE,
        observation_meaning_program,
    )

    model = get_metadata() if target_metadata is None else target_metadata
    task = model.tables["ops.task"]
    request = model.tables["ops.data_request"]
    definition = model.tables["sem.data_operation_definition"]
    inputs = model.tables["sem.input"]
    p_release = core_variable("p_release", Text())
    p_definition_release = core_variable("p_definition", definition.c.release_id.type, "release_id")
    support = core_variable("p_definition", JSONB(), "support_contract")
    asset, profile = (core_variable(name, JSONB()) for name in ("asset", "profile"))
    assets = func.jsonb_array_elements(support["assets"]).table_valued(column("value", JSONB()))
    policy = NativeRoutine(
        "ops",
        "pdf_recognition_profile",
        parameters=(
            Parameter("p_release", pg_type("text")),
            Parameter("p_definition", pg_type("sem", "data_operation_definition")),
        ),
        returns=pg_type("jsonb"),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    p_definition_release.is_distinct_from(p_release),
                    (Raise("recognition policy belongs to another release", "23514"),),
                ),
                SelectInto(
                    select(assets.c.value).where(
                        assets.c.value["reference"].astext == PROFILE_REFERENCE,
                        assets.c.value["contract"].astext == PROFILE_CONTRACT,
                        assets.c.value["role"].astext == PROFILE_ROLE,
                    ),
                    ("asset",),
                    True,
                ),
                SelectInto(
                    select(cast(func.convert_from(inputs.c.content, "UTF8"), JSONB())).where(
                        inputs.c.release_id == p_release,
                        inputs.c.input_kind == "dependency",
                        inputs.c.input_name
                        == ("data-operations/contracts/" + asset["contract"].astext),
                        inputs.c.content_digest == asset["content_digest"].astext,
                        func.encode(func.sha256(inputs.c.content), "hex")
                        == inputs.c.content_digest,
                    ),
                    ("profile",),
                    True,
                ),
                Perform(
                    func.ops.ddo_fields(
                        profile,
                        array(
                            [
                                "version",
                                "base_recipe_digest",
                                "recipes",
                                "recovery_policy",
                                "source_recovery",
                            ],
                            type_=Text(),
                        ),
                    )
                ),
                If(
                    profile["version"].astext.is_distinct_from("pdf-recognition-profile-1"),
                    (Raise("unsupported recognition policy", "23514"),),
                ),
                Return(profile),
            ),
            (Local("asset", pg_type("jsonb")), Local("profile", pg_type("jsonb"))),
        ),
    )
    parameters = (
        Parameter("p_receipt", pg_type("jsonb")),
        Parameter("p_task", pg_type("bigint")),
        Parameter("p_attempt", pg_type("bigint")),
        Parameter("p_holder", pg_type("text")),
    )
    job_request = core_variable("job", task.c.data_request_id.type, "data_request_id")
    conditions = tuple(
        core_variable("request", request.c[left].type, left).is_distinct_from(
            core_variable("job", task.c[right].type, right)
        )
        for left, right in (
            ("live_task_id", "id"),
            ("generation", "data_generation"),
            ("release_id", "release_id"),
        )
    )
    envelope = NativeRoutine(
        "ops",
        "pdf_observation_projection",
        parameters=parameters,
        returns=pg_type("jsonb"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                SelectInto(
                    select(task).where(task.c.id == core_variable("p_task", BigInteger())),
                    ("job",),
                    True,
                ),
                SelectInto(select(request).where(request.c.id == job_request), ("request",), True),
                If(
                    or_(*conditions),
                    (
                        Raise(
                            "active observation projection requires its current task request basis",
                            "23514",
                        ),
                    ),
                ),
                Return(
                    func.ops.pdf_observation_projection_for_request(
                        core_variable("p_receipt", JSONB()),
                        core_variable("p_task", BigInteger()),
                        core_variable("p_attempt", BigInteger()),
                        core_variable("p_holder", Text()),
                        core_variable("request", JSONB()),
                    )
                ),
            ),
            (Local("job", task), Local("request", request)),
        ),
    )
    specification = next(
        source.content for source in context.domain.sources if source.name == MEANING_SPEC
    )
    meaning = NativeRoutine(
        "ops",
        "pdf_observation_meaning",
        parameters=(Parameter("p_payload", pg_type("bytea")),),
        returns=pg_type("jsonb"),
        body=observation_meaning_program(specification),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    return meaning, policy, envelope
