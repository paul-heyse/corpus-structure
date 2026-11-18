"""Model-derived private PDF staging DDL and protected batch operations."""

from sqlalchemy.dialects.postgresql import dialect

from .metadata import metadata


def native_payload_size_expression(relation):
    """Declared logical extent, including null bitmap and varlena headers."""
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Float,
        Integer,
        Numeric,
        String,
        Text,
        case,
        cast,
        func,
        literal,
    )
    from sqlalchemy.dialects.postgresql import BYTEA, JSONB

    size = literal((len(relation.columns) + 7) // 8)
    for field in relation.c:
        kind = field.type
        if isinstance(kind, (BYTEA, String)):
            extent = 4 + func.octet_length(field)
        elif isinstance(kind, (JSONB, Numeric)):
            extent = 4 + func.octet_length(func.convert_to(cast(field, Text()), "UTF8"))
        elif isinstance(kind, Boolean):
            extent = literal(1)
        elif isinstance(kind, (BigInteger, Float)):
            extent = literal(8)
        elif isinstance(kind, Integer):
            extent = literal(4)
        else:
            raise ValueError(f"unsupported native upload type: {field}")
        size = size + case((field.is_(None), 0), else_=extent)
    return size


def native_payload_size_sql(relation, *, alias="s") -> str:
    """Render the shared extent expression for the remaining companion owner."""
    return str(native_payload_size_expression(relation.alias(alias)).compile(
        dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
    ))


def stage_native_sql(*, target_metadata=None, pdf_sources=None) -> str:
    from pglast import ast, enums
    from pglast.stream import RawStream

    from .pdf_domain_native import pdf_domain_native_sql

    if target_metadata is not None and pdf_sources is None:
        from .pdf_domain import pdf_domain_sources

        pdf_sources = pdf_domain_sources(
            physical_sources=target_metadata.info["physical_sources"],
            linkml_types=target_metadata.info["physical_linkml_types"],
        )
    sql = pdf_domain_native_sql(sources=pdf_sources)
    selected = metadata if target_metadata is None else target_metadata
    from .native_program import (
        Assign,
        Block,
        Local,
        Parameter,
        Perform,
        call,
        column_type,
        function,
        literal,
        pg_type,
        variable,
    )
    from .pdf_shared_streams import (
        part_wire_contract_sql,
        pdf_scratch_prepare,
        pdf_stage_scratch_specs,
        shared_streams_sql,
    )

    sql += stage_scratch_authorization_sql()
    sql += part_wire_contract_sql(selected) + shared_streams_sql(selected)
    specs = pdf_stage_scratch_specs(selected)
    build_relation = selected.tables["ops.pdf_stage_build"]
    prepare_parameters = tuple(Parameter(name, column_type(field)) for name, field in (
        ("p_build", build_relation.c.build_id), ("p_task", build_relation.c.task_id),
        ("p_attempt", build_relation.c.attempt), ("p_holder", build_relation.c.holder),
    ))
    sql += (
        function(
            "ops",
            "prepare_pdf_stage",
            parameters=prepare_parameters,
            returns=pg_type("void"),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                locals=(Local("build", selected.tables["ops.pdf_stage_build"]),),
                statements=(
                    Assign(
                        "build",
                        call(
                            "ops",
                            "require_pdf_build",
                            *(
                                variable(name)
                                for name in ("p_build", "p_task", "p_attempt", "p_holder")
                            ),
                        ),
                    ),
                    Perform(
                        call(
                            "ops",
                            "require_pdf_operation",
                            variable("build", "release_id"),
                            literal("adopt_pdf_batch"),
                        )
                    ),
                    *(statement for spec in specs for statement in pdf_scratch_prepare(spec)),
                ),
            ),
        )
        + ";\n"
    )
    sql += stage_batch_adoption_sql(selected)
    sql += stage_lifecycle_sql(selected)
    prepare_identity = ast.ObjectWithArgs(
        objname=(ast.String(sval="ops"), ast.String(sval="prepare_pdf_stage")),
        objargs=tuple(parameter.type_ for parameter in prepare_parameters), args_unspecified=False,
    )
    for allowed, grantee in (
        (False, ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC)),
        (True, ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename="corpus_sem_writer")),
    ):
        sql += RawStream()(ast.GrantStmt(
            is_grant=allowed, targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
            objtype=enums.ObjectType.OBJECT_FUNCTION, objects=(prepare_identity,),
            privileges=(ast.AccessPriv(priv_name="execute"),) if allowed else None,
            grantees=(grantee,), grant_option=False, behavior=enums.DropBehavior.DROP_RESTRICT,
        )) + ";\n"
    from .pdf_spool_native import pdf_spool_native_sql
    sql += pdf_spool_native_sql()
    return sql


def stage_lifecycle_sql(model):
    """Generate original custody and private-build fences from the supplied model."""
    from typing import Any

    from pglast import ast, enums, parse_sql
    from pglast.stream import RawStream
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Text,
        and_,
        cast,
        column,
        exists,
        func,
        literal,
        not_,
        or_,
        select,
        update,
    )
    from sqlalchemy.dialects.postgresql import BYTEA, JSONB, insert
    from sqlalchemy.types import TypeEngine

    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        Parameter,
        Perform,
        PerformQuery,
        Raise,
        Return,
        ReturnQuery,
        SelectInto,
        Sql,
        column_type,
        core_variable,
        function,
        pg_type,
    )

    document = model.tables["kb.document"]
    task = model.tables["ops.task"]
    request = model.tables["ops.data_request"]
    build = model.tables["ops.pdf_stage_build"]
    receipt = model.tables["ops.pdf_stage_receipt"]
    frozen = model.tables["ops.pdf_frozen_build"]
    artifacts = model.tables["kb.source_artifact"]
    sources = model.tables["ops.source_build"]
    definition = model.tables["sem.data_operation_definition"]
    runtime = model.tables["sem.runtime_binding"]
    inputs = model.tables["sem.input"]
    uses = model.tables["ops.demand_use"]
    demand = model.tables["ops.data_demand"]
    revoked = model.tables["ops.data_revocation"]
    stage_recipe = model.tables["ops.pdf_stage_recipe"]
    p_build = core_variable("p_build", build.c.build_id.type)
    p_task = core_variable("p_task", task.c.id.type)
    p_attempt = core_variable("p_attempt", task.c.attempt.type)
    p_holder = core_variable("p_holder", task.c.claimed_by.type)
    fence_parameters = (
        Parameter("p_task", column_type(task.c.id)),
        Parameter("p_attempt", column_type(task.c.attempt)),
        Parameter("p_holder", column_type(task.c.claimed_by)),
    )
    build_parameters = (Parameter("p_build", column_type(build.c.build_id)), *fence_parameters)
    owner_fields: dict[str, TypeEngine[Any]] = {
        "project_id": request.c.project_id.type,
        "release_id": task.c.release_id.type,
        "request_id": request.c.id.type,
        "generation": task.c.data_generation.type,
        "document_id": document.c.id.type,
        "source_digest": document.c.content_hash.type,
    }

    def owner_value(field):
        return core_variable("owner", owner_fields[field], field)

    def build_value(field):
        return core_variable("build", build.c[field].type, field)

    owner_rows = func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder).table_valued(
        *(column(name, type_) for name, type_ in owner_fields.items())
    )
    require_owner = SelectInto(select(owner_rows), ("owner",), True)
    require_build = Assign(
        "build", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder)
    )

    def require_operation(name, *, from_build=False):
        return Perform(
            func.ops.require_pdf_operation(
                build_value("release_id") if from_build else owner_value("release_id"), name
            )
        )

    def routine(name, parameters, returns, statements, locals_, *, output=(), writer=True, stable=False, strict=False):
        declaration = parse_sql(
            function(
                "ops",
                name,
                parameters=parameters,
                returns=returns,
                body=Block(tuple(statements), tuple(locals_)),
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
                volatility="stable" if stable else None,
                strict=strict,
            )
        )[0].stmt
        if not isinstance(declaration, ast.CreateFunctionStmt):
            raise ValueError("PDF lifecycle requires its typed native declaration")
        if output:
            declaration.parameters = (
                *(declaration.parameters or ()),
                *(
                    ast.FunctionParameter(
                        name=field,
                        argType=column_type(source),
                        mode=enums.FunctionParameterMode.FUNC_PARAM_TABLE,
                    )
                    for field, source in output
                ),
            )
        identity = ast.ObjectWithArgs(
            objname=(ast.String(sval="ops"), ast.String(sval=name)),
            objargs=tuple(p.type_ for p in parameters),
            args_unspecified=False,
        )
        revoke = ast.GrantStmt(
            is_grant=False,
            targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
            objtype=enums.ObjectType.OBJECT_FUNCTION,
            objects=(identity,),
            grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
            grant_option=False,
            behavior=enums.DropBehavior.DROP_RESTRICT,
        )
        statements_ = [declaration, revoke]
        if writer:
            statements_.append(
                ast.GrantStmt(
                    is_grant=True,
                    targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                    objtype=enums.ObjectType.OBJECT_FUNCTION,
                    objects=(identity,),
                    privileges=(ast.AccessPriv(priv_name="execute"),),
                    grantees=(
                        ast.RoleSpec(
                            roletype=enums.RoleSpecType.ROLESPEC_CSTRING,
                            rolename="corpus_sem_writer",
                        ),
                    ),
                    behavior=enums.DropBehavior.DROP_RESTRICT,
                )
            )
        return ";\n".join(RawStream()(value) for value in statements_) + ";\n"

    out = []
    owner_local = Local("owner", pg_type("record"))
    def physical_row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def job(field):
        return physical_row("job", task, field)

    def request_value(field):
        return physical_row("request", request, field)

    def context_value(field):
        return core_variable("context", owner_fields[field], field)

    context_outputs = (
        ("project_id", request.c.project_id), ("release_id", task.c.release_id),
        ("request_id", request.c.id), ("generation", task.c.data_generation),
        ("document_id", document.c.id), ("source_digest", document.c.content_hash),
    )
    context_type = pg_type("record")
    context_type.setof = True
    out.append(routine("pdf_task_context", (fence_parameters[0],), context_type, (
        SelectInto(select(task).where(task.c.id == p_task), ("job",), True),
        If(job("data_request_id").is_(None), (Raise("PDF task has no declared data request", "23514"),)),
        SelectInto(select(request).where(request.c.id == job("data_request_id")), ("request",), True),
        SelectInto(select(document).where(document.c.project_id == request_value("project_id"), document.c.key == request_value("original_source"), document.c.mime == "application/pdf"), ("document",), True),
        ReturnQuery(select(request_value("project_id"), job("release_id"), request_value("id"), cast(job("data_generation"), BigInteger()), physical_row("document", document, "id"), physical_row("document", document, "content_hash"))),
    ), (Local("job", task), Local("request", request), Local("document", document)), output=context_outputs, writer=False, stable=True, strict=True))
    current_conditions = and_(
        request_value("generation").is_not_distinct_from(job("data_generation")),
        request_value("live_task_id").is_not_distinct_from(job("id")),
        request_value("release_id").is_not_distinct_from(job("release_id")),
        exists(select(1).select_from(definition).where(definition.c.release_id == request_value("release_id"), definition.c.operation_id == request_value("operation_id"), func.coalesce(definition.c.command_class == "pdf", False))),
        exists(select(1).select_from(uses).where(uses.c.request_id == request_value("id"), uses.c.generation == request_value("generation"), uses.c.fate == "attached", func.ops.ddo_demand_active(uses.c.demand_id))),
        func.ops.ddo_support_available(core_variable("request", JSONB()), request_value("binding")["support"]),
        ~exists(select(1).select_from(revoked).where(revoked.c.scope == func.ops.ddo_scope(request_value("project_id"), request_value("original_source")), or_(
            and_(revoked.c.selector_kind == "runtime", revoked.c.selector == request_value("runtime_id")),
            and_(revoked.c.selector_kind == "recipe", revoked.c.selector == request_value("recipe")),
        ))),
    )
    out.append(routine("pdf_stage_owner_current", fence_parameters, pg_type("boolean"), (
        SelectInto(select(task).where(task.c.id == p_task), ("job",)),
        If(or_(not_(core_variable("found", Boolean())), p_attempt.is_(None), func.nullif(p_holder, "").is_(None),
            job("attempt").is_distinct_from(p_attempt), job("claimed_by").is_distinct_from(p_holder), job("status") != "running", job("lease_until").is_(None), job("lease_until") <= func.clock_timestamp()), (Return(literal(False)),)),
        If(job("data_request_id").is_(None), (Return(literal(False)),)),
        SelectInto(select(request).where(request.c.id == job("data_request_id")), ("request",)),
        If(not_(core_variable("found", Boolean())), (Return(literal(False)),)),
        Perform(func.ops.ddo_authorize_request(core_variable("request", JSONB()))), Return(current_conditions),
    ), (Local("job", task), Local("request", request)), writer=False, stable=True))
    context_rows = func.ops.pdf_task_context(p_task).table_valued(*(column(name, type_) for name, type_ in owner_fields.items()))
    demand_locks = select(literal(1)).select_from(demand).where(exists(select(1).select_from(uses).where(
        uses.c.demand_id == demand.c.id, uses.c.request_id == request_value("id"), uses.c.generation == request_value("generation"), uses.c.fate == "attached",
    ))).order_by(demand.c.id).with_for_update(read=True)
    out.append(routine("require_pdf_stage_owner", fence_parameters, context_type, (
        If(or_(p_task.is_(None), p_attempt.is_(None), p_holder.is_(None), p_holder == ""), (Raise("stale private PDF build owner", "P0004"),)),
        SelectInto(select(context_rows), ("context",), True),
        SelectInto(select(request).where(request.c.id == context_value("request_id")), ("request",), True),
        Perform(func.ops.ddo_lock_support(request_value("project_id"), request_value("original_source"), request_value("binding")["support"])),
        PerformQuery(demand_locks),
        SelectInto(select(request).where(request.c.id == context_value("request_id")).with_for_update(), ("request",), True),
        SelectInto(select(task).where(task.c.id == p_task).with_for_update(), ("job",), True),
        If(not_(func.ops.pdf_stage_owner_current(p_task, p_attempt, p_holder)), (Raise("stale private PDF build owner/capability/support", "P0004"),)),
        ReturnQuery(select(*(context_value(name) for name in owner_fields))),
    ), (Local("job", task), Local("request", request), Local("context", pg_type("record"))), output=context_outputs, writer=False))
    from .pdf_staging import stage_upload_profile

    profile = stage_upload_profile(physical_sources=model.info["physical_sources"])
    p_source, p_recipe, p_schema, p_key = (core_variable(name, Text()) for name in ("p_source", "p_recipe", "p_schema", "p_key"))
    accepted_source = exists(select(1).select_from(sources).where(sources.c.task_id == p_task, sources.c.release_id == owner_value("release_id"), sources.c.artifact_digest == p_source, or_(
        sources.c.recipe_digest == p_recipe, exists(select(1).select_from(stage_recipe).where(stage_recipe.c.task_id == p_task, stage_recipe.c.source_digest == p_source, stage_recipe.c.root_recipe_digest == sources.c.recipe_digest, stage_recipe.c.stage_recipe_digest == p_recipe)),
    )))
    build_type = pg_type(build.schema, build.name)
    build_type.setof = True
    out.append(routine("begin_pdf_build", (*fence_parameters, *(Parameter(name, pg_type("text")) for name in ("p_source", "p_recipe", "p_schema", "p_key"))), build_type, (
        require_owner,
        If(exists(select(1).select_from(request.join(definition, and_(definition.c.release_id == request.c.release_id, definition.c.operation_id == request.c.operation_id))).where(request.c.id == owner_value("request_id"), definition.c.support_contract["effects"][0]["name"].astext == "retain_pdf_observations")), (Raise("recognition retention cannot stage a sealed PDF publication", "23514"),)),
        require_operation("begin_pdf_build"),
        If(or_(p_source.is_(None), p_recipe.is_(None), p_schema.is_distinct_from(func.encode(func.sha256(func.ops.pdf_contract_input(owner_value("release_id"), "implementation/pdf/docling-validation.schema.json")), "hex")),
            p_key.is_(None), p_key == "", func.octet_length(p_key) > profile["max_replay_key_bytes"], ~accepted_source, p_source.is_distinct_from(owner_value("source_digest")),
            ~exists(select(1).select_from(document).where(document.c.id == owner_value("document_id"), document.c.project_id == owner_value("project_id"), document.c.content_hash == p_source))), (Raise("private PDF build source custody differs", "23514"),)),
        Assign("id", func.encode(func.sha256(func.convert_to(cast(func.jsonb_build_array(p_task, p_source, p_recipe, p_schema, p_key), Text()), "UTF8")), "hex")),
        Sql(insert(build).values({build.c.build_id: core_variable("id", build.c.build_id.type), build.c.task_id: p_task, build.c.release_id: owner_value("release_id"), build.c.source_digest: p_source, build.c.recipe_digest: p_recipe, build.c.schema_digest: p_schema, build.c.replay_key: p_key, build.c.attempt: p_attempt, build.c.holder: p_holder, build.c.state: "open"}).on_conflict_do_nothing(index_elements=(build.c.task_id, build.c.replay_key))),
        SelectInto(select(build).where(build.c.task_id == p_task, build.c.replay_key == p_key), ("build",), True),
        If(or_(build_value("build_id").is_distinct_from(core_variable("id", build.c.build_id.type)), build_value("attempt").is_distinct_from(p_attempt), build_value("holder").is_distinct_from(p_holder), build_value("state") != "open"), (Raise("private PDF build replay differs or requires explicit resume", "23514"),)),
        ReturnQuery(select(*(build_value(field.name) for field in build.c))),
    ), (owner_local, Local("build", build), Local("id", pg_type("text")))))

    build_local = Local("build", build)
    out.append(
        routine(
            "require_pdf_build",
            build_parameters,
            pg_type(build.schema, build.name),
            (
                require_owner,
                If(p_build.is_(None), (Raise("private PDF build is not owned/open", "P0004"),)),
                SelectInto(
                    select(build)
                    .where(build.c.build_id == p_build, build.c.task_id == p_task)
                    .with_for_update(),
                    ("build",),
                    True,
                ),
                If(
                    or_(
                        build_value("release_id").is_distinct_from(owner_value("release_id")),
                        build_value("attempt").is_distinct_from(p_attempt),
                        build_value("holder").is_distinct_from(p_holder),
                        build_value("state") != "open",
                    ),
                    (Raise("private PDF build is not owned/open", "P0004"),),
                ),
                Return(core_variable("build", JSONB())),
            ),
            (owner_local, build_local),
            writer=False,
        )
    )

    p_original = core_variable("p_original", BYTEA())
    p_recipe = core_variable("p_recipe", BYTEA())
    original_digest, recipe_digest = (
        core_variable(name, Text()) for name in ("original_digest", "recipe_digest_")
    )
    out.append(
        routine(
            "retain_pdf_original",
            (
                *fence_parameters,
                Parameter("p_original", pg_type("bytea")),
                Parameter("p_recipe", pg_type("bytea")),
            ),
            pg_type("text"),
            (
                require_owner,
                require_operation("retain_pdf_original"),
                If(
                    or_(
                        p_original.is_(None),
                        func.substr(p_original, 1, 5) != func.convert_to("%PDF-", "UTF8"),
                        p_recipe.is_(None),
                        func.octet_length(p_recipe) == 0,
                    ),
                    (Raise("original PDF or recipe bytes unavailable", "23514"),),
                ),
                Perform(cast(func.convert_from(p_recipe, "UTF8"), JSONB())),
                Assign("original_digest", func.encode(func.sha256(p_original), "hex")),
                Assign("recipe_digest_", func.encode(func.sha256(p_recipe), "hex")),
                If(
                    original_digest.is_distinct_from(owner_value("source_digest")),
                    (Raise("original PDF differs from exact document custody", "23514"),),
                ),
                Sql(
                    insert(artifacts)
                    .values(
                        [
                            {
                                artifacts.c.artifact_digest: original_digest,
                                artifacts.c.content: p_original,
                            },
                            {
                                artifacts.c.artifact_digest: recipe_digest,
                                artifacts.c.content: p_recipe,
                            },
                        ]
                    )
                    .on_conflict_do_nothing()
                ),
                If(
                    or_(
                        ~exists(
                            select(1)
                            .select_from(artifacts)
                            .where(
                                artifacts.c.artifact_digest == original_digest,
                                artifacts.c.content == p_original,
                            )
                        ),
                        ~exists(
                            select(1)
                            .select_from(artifacts)
                            .where(
                                artifacts.c.artifact_digest == recipe_digest,
                                artifacts.c.content == p_recipe,
                            )
                        ),
                    ),
                    (Raise("original PDF or recipe artifact digest conflict", "23514"),),
                ),
                Sql(
                    insert(sources)
                    .values(
                        {
                            sources.c.task_id: p_task,
                            sources.c.release_id: owner_value("release_id"),
                            sources.c.artifact_digest: original_digest,
                            sources.c.recipe_digest: recipe_digest,
                        }
                    )
                    .on_conflict_do_nothing()
                ),
                If(
                    ~exists(
                        select(1)
                        .select_from(sources)
                        .where(
                            sources.c.task_id == p_task,
                            sources.c.release_id == owner_value("release_id"),
                            sources.c.artifact_digest == original_digest,
                            sources.c.recipe_digest == recipe_digest,
                        )
                    ),
                    (Raise("original PDF source build replay differs", "23514"),),
                ),
                Return(original_digest),
            ),
            (
                owner_local,
                Local("original_digest", pg_type("text")),
                Local("recipe_digest_", pg_type("text")),
            ),
        )
    )

    p_runtime = core_variable("p_runtime", runtime.c.runtime_id.type)
    basis = (
        select(
            request.c.id,
            request.c.generation,
            request.c.release_id,
            request.c.operation_id,
            definition.c.definition_identity,
            definition.c.recipe,
            definition.c.implementation_revision,
            runtime.c.execution_profile,
            runtime.c.runtime_id,
            func.encode(func.sha256(runtime.c.manifest_bytes), "hex"),
            inputs.c.content_digest,
        )
        .select_from(
            request.join(
                definition,
                and_(
                    definition.c.release_id == request.c.release_id,
                    definition.c.operation_id == request.c.operation_id,
                ),
            )
            .join(
                runtime,
                and_(
                    runtime.c.release_id == request.c.release_id, runtime.c.runtime_id == p_runtime
                ),
            )
            .join(
                inputs,
                and_(
                    inputs.c.release_id == request.c.release_id,
                    inputs.c.input_kind == "dependency",
                    inputs.c.input_name == "pdf-domain/contract.json",
                    func.encode(func.sha256(inputs.c.content), "hex") == inputs.c.content_digest,
                ),
            )
        )
        .where(
            request.c.id == owner_value("request_id"),
            request.c.generation == owner_value("generation"),
            request.c.runtime_id == p_runtime,
        )
    )
    result_type = pg_type("record")
    result_type.setof = True
    out.append(
        routine(
            "read_pdf_producer_basis",
            (*fence_parameters, Parameter("p_runtime", column_type(runtime.c.runtime_id))),
            result_type,
            (
                require_owner,
                require_operation("retain_pdf_original"),
                Perform(func.sem.require_runtime_binding(owner_value("release_id"), p_runtime)),
                ReturnQuery(basis),
                If(
                    not_(core_variable("found", Boolean())),
                    (Raise("PDF producer runtime differs from current request fence", "P0004"),),
                ),
            ),
            (owner_local,),
            output=(
                ("request_id", request.c.id),
                ("generation", request.c.generation),
                ("release_id", request.c.release_id),
                ("operation", request.c.operation_id),
                ("definition", definition.c.definition_identity),
                ("recipe", definition.c.recipe),
                ("implementation", definition.c.implementation_revision),
                ("execution_profile", runtime.c.execution_profile),
                ("runtime_id", runtime.c.runtime_id),
                ("runtime_manifest_digest", inputs.c.content_digest),
                ("pdf_domain_digest", inputs.c.content_digest),
            ),
        )
    )

    receipt_type = pg_type(receipt.schema, receipt.name)
    receipt_type.setof = True
    out.append(
        routine(
            "inspect_pdf_progress",
            build_parameters,
            receipt_type,
            (
                require_build,
                require_operation("inspect_pdf_progress", from_build=True),
                ReturnQuery(
                    select(receipt)
                    .where(receipt.c.build_id == p_build)
                    .order_by(receipt.c.replay_key)
                ),
            ),
            (build_local,),
        )
    )
    out.append(
        routine(
            "resume_pdf_build",
            build_parameters,
            pg_type("void"),
            (
                require_owner,
                require_operation("resume_pdf_build"),
                If(p_build.is_(None), (Raise("private PDF resume binding differs", "23514"),)),
                SelectInto(
                    select(build)
                    .where(build.c.build_id == p_build, build.c.task_id == p_task)
                    .with_for_update(),
                    ("build",),
                    True,
                ),
                If(
                    or_(
                        build_value("release_id").is_distinct_from(owner_value("release_id")),
                        build_value("state").not_in(("open", "frozen")),
                        build_value("attempt") > p_attempt,
                        and_(
                            build_value("state") == "frozen",
                            ~exists(
                                select(1)
                                .select_from(frozen)
                                .where(frozen.c.build_id == build_value("build_id"))
                            ),
                        ),
                    ),
                    (Raise("private PDF resume binding differs", "23514"),),
                ),
                Sql(
                    update(build)
                    .values({build.c.attempt: p_attempt, build.c.holder: p_holder})
                    .where(build.c.build_id == p_build)
                ),
            ),
            (owner_local, build_local),
        )
    )
    out.append(
        routine(
            "abandon_pdf_build",
            build_parameters,
            pg_type("void"),
            (
                require_build,
                require_operation("abandon_pdf_build", from_build=True),
                Sql(
                    update(build)
                    .values({build.c.state: "abandoned"})
                    .where(build.c.build_id == p_build)
                ),
                Perform(func.ops.pdf_cleanup_pending_build(p_build)),
            ),
            (build_local,),
        )
    )
    return "\n".join(out)


def stage_scratch_authorization_sql():
    """Authorize actual scratch custody and compare declared native column/check shapes."""
    from pglast import ast, enums
    from pglast.stream import RawStream
    from sqlalchemy import (
        Boolean,
        Integer,
        Text,
        cast,
        exists,
        func,
        literal,
        not_,
        or_,
        select,
        tuple_,
    )
    from sqlalchemy.dialects.postgresql import OID, REGCLASS, array

    from .native_catalog import _catalog
    from .native_program import Block, If, Local, Parameter, Raise, core_variable, function, pg_type

    relation = _catalog(
        "pg_class",
        oid=OID,
        relowner=OID,
        relnamespace=OID,
        relkind=Text,
        relpersistence=Text,
        relrowsecurity=Boolean,
    )
    trigger = _catalog("pg_trigger", tgrelid=OID)
    rewrite = _catalog("pg_rewrite", ev_class=OID)
    inheritance = _catalog("pg_inherits", inhrelid=OID, inhparent=OID)
    defaults = _catalog("pg_attrdef", adrelid=OID)
    index = _catalog("pg_index", indrelid=OID)
    constraint = _catalog(
        "pg_constraint", oid=OID, conrelid=OID, contype=Text, convalidated=Boolean
    )
    attribute = _catalog(
        "pg_attribute",
        attrelid=OID,
        attnum=Integer,
        attname=Text,
        atttypid=OID,
        atttypmod=Integer,
        attnotnull=Boolean,
        attgenerated=Text,
        attidentity=Text,
        attisdropped=Boolean,
    )
    roles = _catalog("pg_roles", oid=OID, rolname=Text)
    scratch = core_variable("scratch", OID())
    expected = core_variable("p_relation", REGCLASS())
    owned_role = (
        select(roles.c.oid).where(roles.c.rolname == "corpus_sem_publisher").scalar_subquery()
    )
    safe_relation = exists(
        select(1)
        .select_from(relation)
        .where(
            relation.c.oid == scratch,
            relation.c.relowner == owned_role,
            relation.c.relnamespace == func.pg_my_temp_schema(),
            relation.c.relkind == "r",
            relation.c.relpersistence == "t",
            not_(relation.c.relrowsecurity),
        )
    )
    hostile = or_(
        scratch.is_(None),
        not_(safe_relation),
        exists(select(1).select_from(trigger).where(trigger.c.tgrelid == scratch)),
        exists(select(1).select_from(rewrite).where(rewrite.c.ev_class == scratch)),
        exists(
            select(1)
            .select_from(inheritance)
            .where(or_(inheritance.c.inhrelid == scratch, inheritance.c.inhparent == scratch))
        ),
        exists(select(1).select_from(defaults).where(defaults.c.adrelid == scratch)),
        exists(select(1).select_from(index).where(index.c.indrelid == scratch)),
        exists(
            select(1)
            .select_from(constraint)
            .where(
                constraint.c.conrelid == scratch,
                or_(constraint.c.contype.not_in(("c", "n")), not_(constraint.c.convalidated)),
            )
        ),
    )
    empty = array([], type_=Text())

    def column_shape(identity):
        fields = tuple_(
            attribute.c.attnum,
            attribute.c.attname,
            attribute.c.atttypid,
            attribute.c.atttypmod,
            attribute.c.attnotnull,
            attribute.c.attgenerated,
            attribute.c.attidentity,
        )
        return (
            select(
                func.coalesce(
                    func.array_agg(cast(fields, Text())).aggregate_order_by(attribute.c.attnum),
                    empty,
                )
            )
            .where(
                attribute.c.attrelid == identity,
                attribute.c.attnum > 0,
                not_(attribute.c.attisdropped),
            )
            .scalar_subquery()
        )

    def check_shape(identity):
        definition = func.pg_get_constraintdef(constraint.c.oid, True)
        return (
            select(func.coalesce(func.array_agg(definition).aggregate_order_by(definition), empty))
            .where(constraint.c.conrelid == identity, constraint.c.contype == "c")
            .scalar_subquery()
        )

    sql = function(
        "ops",
        "require_pdf_stage_scratch",
        parameters=(
            Parameter("p_name", pg_type("text")),
            Parameter("p_relation", pg_type("regclass")),
        ),
        returns=pg_type("void"),
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(hostile, (Raise("untrusted private PDF scratch", "23514"),)),
                If(
                    or_(
                        column_shape(scratch).is_distinct_from(column_shape(expected)),
                        check_shape(scratch).is_distinct_from(check_shape(expected)),
                    ),
                    (Raise("private PDF scratch schema differs", "23514"),),
                ),
            ),
            (
                Local(
                    "scratch",
                    pg_type("oid"),
                    func.to_regclass(literal("pg_temp.") + core_variable("p_name", Text())),
                ),
            ),
        ),
    )
    revoke = ast.GrantStmt(
        is_grant=False,
        targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
        objtype=enums.ObjectType.OBJECT_FUNCTION,
        objects=(
            ast.ObjectWithArgs(
                objname=(ast.String(sval="ops"), ast.String(sval="require_pdf_stage_scratch")),
                objargs=(pg_type("text"), pg_type("regclass")),
                args_unspecified=False,
            ),
        ),
        grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
        grant_option=False,
        behavior=enums.DropBehavior.DROP_RESTRICT,
    )
    return sql + ";\n" + RawStream()(revoke) + ";\n"


def stage_batch_adoption_sql(model):
    """Compile bounded, named-column scratch admission and exact replay once."""
    from pglast import ast, enums
    from pglast.stream import RawStream
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Column,
        MetaData,
        Table,
        Text,
        cast,
        exists,
        func,
        literal,
        or_,
        select,
    )
    from sqlalchemy.dialects.postgresql import REGCLASS, insert

    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        Parameter,
        Perform,
        PerformQuery,
        Raise,
        ReturnQuery,
        SelectInto,
        Sql,
        Statement,
        column_type,
        core_variable,
        function,
        pg_type,
    )
    from .pdf_shared_streams import pdf_stage_scratch_specs
    from .pdf_staging import stage_upload_profile

    profile = stage_upload_profile(physical_sources=model.info["physical_sources"])
    specs = pdf_stage_scratch_specs(model)
    build = model.tables["ops.pdf_stage_build"]
    receipt = model.tables["ops.pdf_stage_receipt"]
    p_build, p_task, p_attempt, p_holder, p_key = (
        core_variable(name, field.type) for name, field in (
            ("p_build", build.c.build_id), ("p_task", build.c.task_id), ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder), ("p_key", receipt.c.replay_key),
        )
    )
    n, size, total, total_bytes = (core_variable(name, BigInteger()) for name in ("n", "bytes", "total", "total_bytes"))
    hashes, digest = core_variable("hashes", Text()), core_variable("digest", Text())
    statements: list[Statement] = [
        Assign("build", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder)),
        Perform(func.ops.require_pdf_operation(core_variable("build", build.c.release_id.type, "release_id"), "adopt_pdf_batch")),
        If(or_(p_key.is_(None), p_key == "", func.octet_length(p_key) > profile["max_replay_key_bytes"]), (Raise("invalid private replay key", "23514"),)),
    ]
    scratch_tables = {
        spec.source.name: Table(spec.name, MetaData(), *(
            Column(field.name, field.type, nullable=field.nullable) for field in spec.source.c
        ), schema="pg_temp") for spec in specs
    }
    for spec in sorted(specs, key=lambda spec: spec.source.fullname):
        relation = spec.source
        scratch = scratch_tables[relation.name].alias("s")
        keys = tuple(scratch.c[field.name] for field in relation.primary_key)
        if not keys:
            raise ValueError("PDF incoming scratch requires its declared replay key")
        prototype = func.ops.pdf_part_upload_contract() if relation.name == "pdf_stage_artifact_part" else cast(literal(relation.fullname), REGCLASS())
        statements.extend((
            Perform(func.ops.require_pdf_stage_scratch(spec.name, prototype)),
            SelectInto(select(func.count(), func.coalesce(func.sum(native_payload_size_expression(scratch)), 0)).select_from(scratch), ("n", "bytes")),
            Assign("total", total + n), Assign("total_bytes", total_bytes + size),
            If(or_(total > profile["max_rows"], total_bytes > profile["max_native_bytes"]), (Raise("private PDF upload profile exceeded", "23514"),)),
            If(or_(exists(select(1).select_from(scratch).where(or_(scratch.c.product_id.is_distinct_from(p_build), scratch.c.revision_id.is_distinct_from(p_build)))),
                exists(select(1).select_from(scratch).group_by(*keys).having(func.count() > 1))),
                (Raise("private PDF upload ownership or duplicate key differs", "23514"),)),
            SelectInto(select(hashes + relation.fullname + ":" + func.encode(func.sha256(func.convert_to(
                func.coalesce(func.string_agg(cast(func.to_jsonb(scratch.table_valued()), Text()), literal("\n")).aggregate_order_by(*keys), ""), "UTF8")), "hex")).select_from(scratch), ("hashes",)),
        ))
    document = scratch_tables["pdf_stage_document"]
    statements.extend((
        If(exists(select(1).select_from(document).where(or_(
            document.c.release_id.is_distinct_from(core_variable("build", build.c.release_id.type, "release_id")),
            document.c.source_digest.is_distinct_from(core_variable("build", build.c.source_digest.type, "source_digest")),
            document.c.native_schema_digest.is_distinct_from(core_variable("build", build.c.schema_digest.type, "schema_digest")),
        ))), (Raise("private PDF header binding differs", "23514"),)),
        Assign("digest", func.encode(func.sha256(func.convert_to(hashes, "UTF8")), "hex")),
        SelectInto(select(receipt).where(receipt.c.build_id == p_build, receipt.c.replay_key == p_key), ("receipt",)),
        If(core_variable("found", Boolean()), (
            If(or_(core_variable("receipt", receipt.c.content_digest.type, "content_digest").is_distinct_from(digest),
                   core_variable("receipt", receipt.c.row_count.type, "row_count").is_distinct_from(total)),
               (Raise("private PDF batch replay differs", "23514"),)),
        )),
    ))
    for spec in specs:
        relation = spec.source
        scratch = scratch_tables[relation.name]
        if relation.name == "pdf_stage_artifact_part":
            statements.append(Perform(func.ops.pdf_adopt_shared_stream_parts(p_build, cast(literal(scratch.fullname), REGCLASS()))))
            continue
        if relation.name == "pdf_stage_artifact_stream":
            statements.append(Perform(func.ops.pdf_adopt_shared_stream_descriptors(p_build, cast(literal(scratch.fullname), REGCLASS()))))
        statements.extend((
            Sql(insert(relation).from_select(tuple(relation.c.keys()), select(*(scratch.c[field.name] for field in relation.c))).on_conflict_do_nothing()),
            If(exists(select(*(scratch.c[field.name] for field in relation.c)).except_(select(relation))), (Raise("changed private record duplicate", "23514"),)),
        ))
    touched = select(scratch_tables["pdf_stage_artifact_stream"].c.stream_id).union(
        select(scratch_tables["pdf_stage_artifact_part"].c.stream_id)
    ).subquery("touched")
    statements.extend((
        PerformQuery(select(func.ops.pdf_verify_shared_stream(p_build, touched.c.stream_id, False))),
        If(core_variable("receipt", receipt.c.build_id.type, "build_id").is_(None), (
            SelectInto(insert(receipt).values({receipt.c.build_id: p_build, receipt.c.replay_key: p_key, receipt.c.content_digest: digest, receipt.c.row_count: total}).returning(*receipt.c), ("receipt",)),
        )),
        ReturnQuery(select(*(core_variable("receipt", field.type, field.name) for field in receipt.c))),
    ))
    parameters = tuple(Parameter(name, column_type(field)) for name, field in (
        ("p_build", build.c.build_id), ("p_task", build.c.task_id), ("p_attempt", build.c.attempt), ("p_holder", build.c.holder), ("p_key", receipt.c.replay_key),
    ))
    returns = pg_type(receipt.schema, receipt.name)
    returns.setof = True
    declaration = function("ops", "adopt_pdf_batch", parameters=parameters, returns=returns, security_definer=True,
        search_path=("pg_catalog", "pg_temp"), body=Block(tuple(statements), (
            Local("build", build), Local("receipt", receipt), Local("n", pg_type("bigint")), Local("bytes", pg_type("bigint")),
            Local("total", pg_type("bigint"), literal(0)), Local("total_bytes", pg_type("bigint"), literal(0)),
            Local("hashes", pg_type("text"), literal("")), Local("digest", pg_type("text")),
        )))
    identity = ast.ObjectWithArgs(objname=(ast.String(sval="ops"), ast.String(sval="adopt_pdf_batch")), objargs=tuple(parameter.type_ for parameter in parameters), args_unspecified=False)
    revoke = ast.GrantStmt(is_grant=False, targtype=enums.GrantTargetType.ACL_TARGET_OBJECT, objtype=enums.ObjectType.OBJECT_FUNCTION,
        objects=(identity,), grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),), grant_option=False, behavior=enums.DropBehavior.DROP_RESTRICT)
    grant = ast.GrantStmt(is_grant=True, targtype=enums.GrantTargetType.ACL_TARGET_OBJECT, objtype=enums.ObjectType.OBJECT_FUNCTION,
        objects=(identity,), privileges=(ast.AccessPriv(priv_name="execute"),),
        grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename="corpus_sem_writer"),), behavior=enums.DropBehavior.DROP_RESTRICT)
    return declaration + ";\n" + RawStream()(revoke) + ";\n" + RawStream()(grant) + ";\n"
