"""Model-built relational readers for project-scoped PDF content."""

from __future__ import annotations

from pglast import ast, enums, parse_sql
from pglast.stream import RawStream
from sqlalchemy import (
    ARRAY,
    Boolean,
    MetaData,
    Table,
    Text,
    and_,
    any_,
    exists,
    func,
    not_,
    or_,
    select,
    union_all,
)

from .native_program import Parameter, column_type, core_variable, literal, pg_type, sql_function
from .pdf_record_model import artifact_part_upload_table


def _query_function(
    name: str,
    parameters: tuple[Parameter, ...],
    query,
    *,
    returns: ast.TypeName | Table,
    defaults: tuple[tuple[str, ast.Node], ...] = (),
    strict: bool = False,
    search_path: bool = True,
) -> str:
    """Decorate the shared routine compiler with SQL TABLE/default/strict nodes."""
    declaration = sql_function(
        "ops",
        name,
        parameters=parameters,
        returns=pg_type("record") if isinstance(returns, Table) else returns,
        body=query,
        volatility="stable",
        search_path=("pg_catalog", "pg_temp") if search_path else (),
    )
    statement = parse_sql(declaration)[0].stmt
    if not isinstance(statement, ast.CreateFunctionStmt):
        raise ValueError("shared-stream reader requires one typed function declaration")
    default_values = dict(defaults)
    inputs = tuple(statement.parameters or ())
    for parameter in inputs:
        if parameter.name in default_values:
            parameter.defexpr = default_values[parameter.name]
    if isinstance(returns, Table):
        if statement.returnType is None:
            raise ValueError("shared-stream reader requires its declared result type")
        outputs = tuple(
            ast.FunctionParameter(
                name=column.name,
                argType=column_type(column),
                mode=enums.FunctionParameterMode.FUNC_PARAM_TABLE,
            )
            for column in returns.columns
        )
        statement.parameters = (*inputs, *outputs)
        statement.returnType.setof = True
    if strict:
        statement.options = (
            *(statement.options or ()),
            ast.DefElem(
                defname="strict",
                arg=ast.Boolean(boolval=True),
            ),
        )
    revoke = ast.GrantStmt(
        is_grant=False,
        targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
        objtype=enums.ObjectType.OBJECT_FUNCTION,
        objects=(
            ast.ObjectWithArgs(
                objname=(ast.String(sval="ops"), ast.String(sval=name)),
                objargs=tuple(parameter.type_ for parameter in parameters),
                args_unspecified=False,
            ),
        ),
        grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
        grant_option=False,
        behavior=enums.DropBehavior.DROP_RESTRICT,
    )
    return RawStream()(statement) + ";\n" + RawStream()(revoke) + ";\n"


def shared_stream_queries_sql(model: MetaData) -> str:
    """Generate the four stable readers against the supplied physical model.

    The part reader remains invoker-only and has no function SET clause, so
    PostgreSQL can inline it and push a protected outer reader's keyset bounds
    into the qualified shared-content join.
    """
    build = model.tables["ops.pdf_stage_build"]
    job = model.tables["ops.task"]
    request = model.tables["ops.data_request"]
    content = model.tables["ops.pdf_shared_stream"]
    verified = model.tables["ops.pdf_shared_stream_verification"]
    parts = model.tables["ops.pdf_shared_stream_part"]
    stage = model.tables["ops.pdf_stage_artifact_stream"]
    final = model.tables["ops.pdf_artifact_stream"]
    p_build = core_variable("p_build", build.c.build_id.type)
    project = func.ops.pdf_stream_project(p_build)

    project_reader = _query_function(
        "pdf_stream_project",
        (Parameter("p_build", pg_type("text")),),
        select(request.c.project_id)
        .select_from(
            build.join(job, job.c.id == build.c.task_id).join(
                request, request.c.id == job.c.data_request_id
            )
        )
        .where(build.c.build_id == p_build),
        returns=pg_type("text"),
        strict=True,
    )

    p_product = core_variable("p_product", stage.c.product_id.type)
    p_revision = core_variable("p_revision", stage.c.revision_id.type)
    p_stage = core_variable("p_stage", Boolean())
    p_streams = core_variable("p_streams", ARRAY(Text()))
    descriptors = union_all(
        select(stage).where(
            p_stage, stage.c.product_id == p_product, stage.c.revision_id == p_revision
        ),
        select(final).where(
            not_(p_stage), final.c.product_id == p_product, final.c.revision_id == p_revision
        ),
    ).cte("descriptors")
    stream_project = func.ops.pdf_stream_project(p_product)
    selected = {
        "product_id": descriptors.c.product_id,
        "revision_id": descriptors.c.revision_id,
        "stream_id": descriptors.c.stream_id,
        **{
            name: parts.c[name]
            for name in ("ordinal", "byte_offset", "byte_length", "body", "sha256_digest")
        },
    }
    upload = artifact_part_upload_table(model)
    text_array = pg_type("text")
    text_array.arrayBounds = (ast.Integer(ival=-1),)
    part_reader = _query_function(
        "pdf_artifact_parts",
        (
            Parameter("p_product", pg_type("text")),
            Parameter("p_revision", pg_type("text")),
            Parameter("p_stage", pg_type("boolean")),
            Parameter("p_streams", text_array),
        ),
        select(*(selected[column.name] for column in upload.columns))
        .select_from(
            descriptors.join(
                parts,
                and_(
                    parts.c.project_id == stream_project,
                    parts.c.encoding_profile == descriptors.c.encoding_profile,
                    parts.c.stream_length == descriptors.c.byte_length,
                    parts.c.byte_root == descriptors.c.byte_root,
                ),
            )
        )
        .where(or_(p_streams.is_(None), descriptors.c.stream_id == any_(p_streams))),
        returns=upload,
        defaults=(("p_stage", literal(False)), ("p_streams", literal(None))),
        search_path=False,
    )

    p_profile = core_variable("p_profile", content.c.encoding_profile.type)
    p_length = core_variable("p_length", content.c.byte_length.type)
    p_root = core_variable("p_root", content.c.byte_root.type)
    verified_join = and_(
        *(
            verified.c[name] == content.c[name]
            for name in ("project_id", "encoding_profile", "byte_length", "byte_root")
        )
    )
    ready_reader = _query_function(
        "pdf_shared_stream_ready",
        (
            Parameter("p_build", pg_type("text")),
            Parameter("p_profile", pg_type("text")),
            Parameter("p_length", pg_type("bigint")),
            Parameter("p_root", pg_type("text")),
        ),
        select(
            exists(
                select(1)
                .select_from(content.join(verified, verified_join))
                .where(
                    content.c.project_id == project,
                    content.c.encoding_profile == p_profile,
                    content.c.byte_length == p_length,
                    content.c.byte_root == p_root,
                )
            )
        ),
        returns=pg_type("boolean"),
    )

    owner_build = core_variable("content", content.c.owner_build_id.type, "owner_build_id")
    owner_attempt = core_variable("content", content.c.owner_attempt.type, "owner_attempt")
    owner_holder = core_variable("content", content.c.owner_holder.type, "owner_holder")
    owner_reader = _query_function(
        "pdf_pending_stream_owner_dead",
        (Parameter("content", pg_type("ops", "pdf_shared_stream")),),
        select(
            not_(
                exists(
                    select(1)
                    .select_from(
                        build.join(job, job.c.id == build.c.task_id).join(
                            request, request.c.id == job.c.data_request_id
                        )
                    )
                    .where(
                        build.c.build_id == owner_build,
                        build.c.state == "open",
                        build.c.attempt == owner_attempt,
                        build.c.holder == owner_holder,
                        job.c.attempt == owner_attempt,
                        job.c.claimed_by == owner_holder,
                        job.c.status == "running",
                        job.c.lease_until > func.pg_catalog.clock_timestamp(),
                        request.c.live_task_id == job.c.id,
                        request.c.generation == job.c.data_generation,
                    )
                )
            )
        ),
        returns=pg_type("boolean"),
    )
    return project_reader + part_reader + ready_reader + owner_reader
