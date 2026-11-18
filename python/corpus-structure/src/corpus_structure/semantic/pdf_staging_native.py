"""Model-derived private PDF staging DDL and protected batch operations."""

from sqlalchemy.dialects.postgresql import dialect

from .metadata import metadata


def native_payload_size_sql(relation, *, alias="s") -> str:
    """Size admitted native values from their declared types, never bytea's JSON hex.

    Arrow transfer buffers and native logical extents have separate declared budgets.
    Native extents include a row null bitmap and varlena headers, not TOAST compression.
    Canonical replay hashing remains independent of this resource bound.
    """
    from sqlalchemy import BigInteger, Boolean, Float, Integer, Numeric, String
    from sqlalchemy.dialects.postgresql import BYTEA, JSONB

    quote = dialect().identifier_preparer.quote
    sizes = [str((len(relation.columns) + 7) // 8)]
    for column in relation.columns:
        value = f"{alias}.{quote(column.name)}"
        kind = column.type
        if isinstance(kind, (BYTEA, String)):
            size = f"4+octet_length({value})"
        elif isinstance(kind, (JSONB, Numeric)):
            size = f"4+octet_length(convert_to({value}::text,'UTF8'))"
        elif isinstance(kind, Boolean):
            size = "1"
        elif isinstance(kind, BigInteger):
            size = "8"
        elif isinstance(kind, Integer):
            size = "4"
        elif isinstance(kind, Float):
            size = "8"
        else:
            raise ValueError(f"unsupported native upload type: {column}")
        sizes.append(f"CASE WHEN {value} IS NULL THEN 0 ELSE {size} END")
    return "(" + "+".join(sizes) + ")"


def stage_native_sql(*, target_metadata=None, pdf_sources=None) -> str:
    from .pdf_domain_native import pdf_domain_native_sql

    if target_metadata is not None and pdf_sources is None:
        from .pdf_domain import pdf_domain_sources

        pdf_sources = pdf_domain_sources(
            physical_sources=target_metadata.info["physical_sources"],
            linkml_types=target_metadata.info["physical_linkml_types"],
        )
    sql = (
        pdf_domain_native_sql(sources=pdf_sources)
        + """
CREATE OR REPLACE FUNCTION ops.pdf_task_context(p_task bigint)
RETURNS TABLE(project_id text,release_id text,request_id text,generation bigint,
 document_id bigint,source_digest text)
LANGUAGE plpgsql STABLE STRICT SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE job ops.task; request ops.data_request; document kb.document;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task;
 IF job.data_request_id IS NULL THEN RAISE EXCEPTION 'PDF task has no declared data request' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=job.data_request_id;
 SELECT * INTO STRICT document FROM kb.document d WHERE d.project_id=request.project_id
 AND d.key=request.original_source AND d.mime='application/pdf';
 RETURN QUERY SELECT request.project_id,job.release_id,request.id,
 job.data_generation::bigint,document.id,document.content_hash;

END $stage$;
REVOKE ALL ON FUNCTION ops.pdf_task_context(bigint) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.pdf_stage_owner_current(p_task bigint,p_attempt bigint,p_holder text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE job ops.task; request ops.data_request;
BEGIN
 SELECT * INTO job FROM ops.task WHERE id=p_task;
 IF NOT FOUND OR p_attempt IS NULL OR nullif(p_holder,'') IS NULL
 OR job.attempt IS DISTINCT FROM p_attempt OR job.claimed_by IS DISTINCT FROM p_holder
 OR job.status<>'running' OR job.lease_until IS NULL OR job.lease_until<=clock_timestamp() THEN
 RETURN false; END IF;
 IF job.data_request_id IS NULL THEN RETURN false; END IF;
 SELECT * INTO request FROM ops.data_request WHERE id=job.data_request_id;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM ops.ddo_authorize_request(request);
 RETURN request.generation IS NOT DISTINCT FROM job.data_generation
 AND request.live_task_id IS NOT DISTINCT FROM job.id
 AND request.release_id IS NOT DISTINCT FROM job.release_id
 AND EXISTS(SELECT FROM sem.data_operation_definition definition
 WHERE definition.release_id=request.release_id AND definition.operation_id=request.operation_id
 AND coalesce((definition.command_class='pdf'),false))
 AND EXISTS(SELECT FROM ops.demand_use use_ WHERE use_.request_id=request.id
 AND use_.generation=request.generation AND use_.fate='attached'
 AND ops.ddo_demand_active(use_.demand_id))
 AND ops.ddo_support_available(request,request.binding->'support')
 AND NOT EXISTS(SELECT FROM ops.data_revocation revoked
 WHERE revoked.scope=ops.ddo_scope(request.project_id,request.original_source)
 AND ((revoked.selector_kind='runtime' AND revoked.selector=request.runtime_id)
 OR (revoked.selector_kind='recipe' AND revoked.selector=request.recipe)));
END $stage$;
REVOKE ALL ON FUNCTION ops.pdf_stage_owner_current(bigint,bigint,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.require_pdf_stage_owner(p_task bigint,p_attempt bigint,p_holder text)
RETURNS TABLE(project_id text,release_id text,request_id text,generation bigint,
 document_id bigint,source_digest text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE job ops.task; request ops.data_request; context record;
BEGIN
 IF p_task IS NULL OR p_attempt IS NULL OR p_holder IS NULL OR p_holder='' THEN
 RAISE EXCEPTION 'stale private PDF build owner' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT context FROM ops.pdf_task_context(p_task);
 SELECT request_row.* INTO STRICT request FROM ops.data_request request_row
 WHERE request_row.id=context.request_id;
 PERFORM ops.ddo_lock_support(request.project_id,request.original_source,
 request.binding->'support');
 PERFORM 1 FROM ops.data_demand demand WHERE EXISTS(SELECT FROM ops.demand_use use_
 WHERE use_.demand_id=demand.id AND use_.request_id=request.id
 AND use_.generation=request.generation
 AND use_.fate='attached') ORDER BY demand.id FOR SHARE;
 SELECT request_row.* INTO STRICT request FROM ops.data_request request_row
 WHERE request_row.id=context.request_id FOR UPDATE;
 SELECT task_row.* INTO STRICT job FROM ops.task task_row WHERE task_row.id=p_task FOR UPDATE;
 IF NOT ops.pdf_stage_owner_current(p_task,p_attempt,p_holder) THEN
 RAISE EXCEPTION 'stale private PDF build owner/capability/support' USING ERRCODE='P0004'; END IF;
 RETURN QUERY SELECT context.project_id,context.release_id,context.request_id,
 context.generation,context.document_id,context.source_digest;
END $stage$;
REVOKE ALL ON FUNCTION ops.require_pdf_stage_owner(bigint,bigint,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.begin_pdf_build(p_task bigint,p_attempt bigint,p_holder text,
 p_source text,p_recipe text,p_schema text,p_key text)
RETURNS SETOF ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,
 pg_temp AS $stage$
DECLARE owner record; build ops.pdf_stage_build; id text;
BEGIN
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 IF EXISTS(SELECT FROM ops.data_request request JOIN sem.data_operation_definition definition
 ON definition.release_id=request.release_id AND definition.operation_id=request.operation_id
 WHERE request.id=owner.request_id AND definition.support_contract->'effects'->0->>'name'='retain_pdf_observations') THEN
 RAISE EXCEPTION 'recognition retention cannot stage a sealed PDF publication' USING ERRCODE='23514'; END IF;
 PERFORM ops.require_pdf_operation(owner.release_id,'begin_pdf_build');
 IF p_source IS NULL OR p_recipe IS NULL OR p_schema IS DISTINCT FROM
 encode(sha256(ops.pdf_contract_input(owner.release_id,
 'implementation/pdf/docling-validation.schema.json')),'hex')
 OR p_key IS NULL OR p_key=''
 OR octet_length(p_key)>1024 OR NOT
 EXISTS(SELECT FROM ops.source_build s WHERE s.task_id=p_task
 AND s.release_id=owner.release_id AND s.artifact_digest=p_source
 AND (s.recipe_digest=p_recipe OR EXISTS(SELECT FROM ops.pdf_stage_recipe sr
 WHERE sr.task_id=p_task AND sr.source_digest=p_source
 AND sr.root_recipe_digest=s.recipe_digest AND sr.stage_recipe_digest=p_recipe)))
 OR p_source IS DISTINCT FROM owner.source_digest
 OR NOT EXISTS(SELECT FROM kb.document d WHERE d.id=owner.document_id
 AND d.project_id=owner.project_id AND d.content_hash=p_source) THEN
 RAISE EXCEPTION 'private PDF build source custody differs' USING ERRCODE='23514'; END IF;
 id:=encode(sha256(convert_to(jsonb_build_array(p_task,p_source,p_recipe,p_schema,p_key)::text,
 'UTF8')),'hex');
 INSERT INTO ops.pdf_stage_build VALUES(id,p_task,owner.release_id,p_source,p_recipe,
 p_schema,p_key,p_attempt,p_holder,'open')
 ON CONFLICT(task_id,replay_key) DO NOTHING;
 SELECT * INTO STRICT build FROM ops.pdf_stage_build WHERE task_id=p_task AND replay_key=p_key;
 IF build.build_id IS DISTINCT FROM id OR build.attempt IS DISTINCT FROM p_attempt
 OR build.holder IS DISTINCT FROM p_holder OR
 build.state<>'open' THEN
 RAISE EXCEPTION 'private PDF build replay differs or requires explicit resume' USING
 ERRCODE='23514'; END IF;
 RETURN NEXT build;
END $stage$;
"""
    )
    selected = metadata if target_metadata is None else target_metadata
    from .native_program import (
        Assign,
        Block,
        Local,
        Parameter,
        Perform,
        call,
        function,
        literal,
        pg_type,
        variable,
    )
    from .pdf_shared_streams import (
        part_template,
        part_wire_contract_sql,
        pdf_scratch_prepare,
        pdf_stage_scratch_specs,
        shared_streams_sql,
    )

    sql += stage_scratch_authorization_sql()
    sql += part_wire_contract_sql(selected) + shared_streams_sql(selected)
    specs = pdf_stage_scratch_specs(selected)
    relations = [spec.source for spec in specs]
    pg = dialect()
    sql += (
        function(
            "ops",
            "prepare_pdf_stage",
            parameters=tuple(
                Parameter(name, pg_type(kind))
                for name, kind in (
                    ("p_build", "text"),
                    ("p_task", "bigint"),
                    ("p_attempt", "bigint"),
                    ("p_holder", "text"),
                )
            ),
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
    sql += """
CREATE OR REPLACE FUNCTION ops.adopt_pdf_batch(p_build text,p_task bigint,p_attempt bigint,
 p_holder text,p_key text)
RETURNS SETOF ops.pdf_stage_receipt LANGUAGE plpgsql SECURITY DEFINER SET
 search_path=pg_catalog,pg_temp AS $stage$
DECLARE build ops.pdf_stage_build; receipt ops.pdf_stage_receipt; n bigint; bytes bigint;
 total bigint:=0; total_bytes bigint:=0; hashes text:=''; digest text;
BEGIN
 build:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(build.release_id,'adopt_pdf_batch');
 IF p_key IS NULL OR p_key='' OR octet_length(p_key)>1024 THEN
 RAISE EXCEPTION 'invalid private replay key'
 USING ERRCODE='23514'; END IF;
"""
    for relation in sorted(relations, key=lambda r: r.fullname):
        scratch = "pg_temp.ps_" + relation.name
        keys = ",".join(pg.identifier_preparer.quote(c.name) for c in relation.primary_key)
        columns = ",".join(pg.identifier_preparer.quote(c.name) for c in relation.columns)
        sql += f"""
 PERFORM ops.require_pdf_stage_scratch('ps_{relation.name}',{part_template(relation)});
 SELECT count(*),COALESCE(sum({native_payload_size_sql(relation)}),0) INTO n,bytes FROM {scratch} s;
 total:=total+n; total_bytes:=total_bytes+bytes;
 IF total>65536 OR total_bytes>67108864 THEN RAISE EXCEPTION
 'private PDF upload profile exceeded' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM {scratch} WHERE product_id IS DISTINCT FROM p_build
 OR revision_id IS DISTINCT FROM p_build)
 OR EXISTS(SELECT FROM {scratch} GROUP BY {keys} HAVING count(*)>1) THEN
 RAISE EXCEPTION 'private PDF upload ownership or duplicate key differs' USING ERRCODE='23514';
 END IF;
 SELECT hashes||'{relation.fullname}:'||encode(sha256(convert_to(
 COALESCE(string_agg(to_jsonb(s)::text,E'\\n' ORDER BY {keys}),''),'UTF8')),'hex')
 INTO hashes FROM {scratch} s;
"""
    sql += """
 IF EXISTS(SELECT FROM pg_temp.ps_pdf_stage_document
 WHERE release_id IS DISTINCT FROM build.release_id
 OR source_digest IS DISTINCT FROM build.source_digest
 OR native_schema_digest IS DISTINCT FROM build.schema_digest) THEN
 RAISE EXCEPTION 'private PDF header binding differs' USING ERRCODE='23514'; END IF;
 digest:=encode(sha256(convert_to(hashes,'UTF8')),'hex');
 SELECT * INTO receipt FROM ops.pdf_stage_receipt WHERE build_id=p_build AND replay_key=p_key;
 IF FOUND THEN
  IF receipt.content_digest IS DISTINCT FROM digest OR receipt.row_count IS DISTINCT FROM total THEN
   RAISE EXCEPTION 'private PDF batch replay differs' USING ERRCODE='23514'; END IF;
"""
    sql += " END IF;\n"
    for relation in relations:
        scratch = "pg_temp.ps_" + relation.name
        if relation.name == "pdf_stage_artifact_part":
            sql += f"PERFORM ops.pdf_adopt_shared_stream_parts(p_build,'{scratch}'::regclass);\n"
            continue
        columns = ",".join(pg.identifier_preparer.quote(c.name) for c in relation.columns)
        if relation.name == "pdf_stage_artifact_stream":
            sql += (
                f"PERFORM ops.pdf_adopt_shared_stream_descriptors(p_build,'{scratch}'::regclass);\n"
            )
        sql += (
            f"INSERT INTO {relation.fullname}({columns}) SELECT {columns} "
            f"FROM {scratch} ON CONFLICT DO NOTHING;\n"
        )
        retained = (
            "ops.pdf_artifact_parts(p_build,p_build,true)"
            if relation.name == "pdf_stage_artifact_part"
            else relation.fullname
        )
        sql += (
            f"IF EXISTS(SELECT {columns} FROM {scratch} "
            f"EXCEPT SELECT {columns} FROM {retained}) THEN "
            "RAISE EXCEPTION 'changed private record duplicate' USING ERRCODE='23514'; END IF;\n"
        )
    sql += """
 PERFORM ops.pdf_verify_shared_stream(p_build,stream_id,false) FROM (
 SELECT stream_id FROM pg_temp.ps_pdf_stage_artifact_stream
 UNION SELECT stream_id FROM pg_temp.ps_pdf_stage_artifact_part) touched;
 IF receipt.build_id IS NULL THEN
 INSERT INTO ops.pdf_stage_receipt VALUES(p_build,p_key,digest,total) RETURNING * INTO receipt;
 END IF;
 RETURN NEXT receipt;
END $stage$;
"""
    sql += stage_lifecycle_sql(selected)
    for signature in (
        "begin_pdf_build(bigint,bigint,text,text,text,text,text)",
        "prepare_pdf_stage(text,bigint,bigint,text)",
        "adopt_pdf_batch(text,bigint,bigint,text,text)",
    ):
        sql += (
            f"REVOKE ALL ON FUNCTION ops.{signature} FROM PUBLIC; "
            f"GRANT EXECUTE ON FUNCTION ops.{signature} TO corpus_sem_writer;\n"
        )
    from .pdf_spool_native import pdf_spool_native_sql
    from .pdf_staging import stage_upload_profile

    sql += pdf_spool_native_sql()
    profile = stage_upload_profile()
    return (
        sql.replace("total>65536", "total>" + str(profile["max_rows"]))
        .replace("total_bytes>67108864", "total_bytes>" + str(profile["max_native_bytes"]))
        .replace(
            "octet_length(p_key)>1024",
            "octet_length(p_key)>" + str(profile["max_replay_key_bytes"]),
        )
    )


def stage_lifecycle_sql(model):
    """Generate original custody and private-build fences from the supplied model."""
    from typing import Any

    from pglast import ast, enums, parse_sql
    from pglast.stream import RawStream
    from sqlalchemy import (
        Boolean,
        Text,
        and_,
        cast,
        column,
        exists,
        func,
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

    def routine(name, parameters, returns, statements, locals_, *, output=(), writer=True):
        declaration = parse_sql(
            function(
                "ops",
                name,
                parameters=parameters,
                returns=returns,
                body=Block(tuple(statements), tuple(locals_)),
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
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
