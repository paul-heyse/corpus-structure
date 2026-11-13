"""Model-derived private PDF staging DDL and protected batch operations."""

from sqlalchemy.dialects.postgresql import dialect

from .metadata import metadata
from .pdf_staging import STAGE_FAMILIES


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


def stage_native_sql() -> str:
    from .pdf_domain_native import pdf_domain_native_sql

    sql = (
        pdf_domain_native_sql()
        + """
CREATE OR REPLACE FUNCTION ops.pdf_task_context(p_task bigint)
RETURNS TABLE(project_id text,release_id text,run_id bigint,request_id text,generation bigint,
 document_id bigint,source_digest text)
LANGUAGE plpgsql STABLE STRICT SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE job ops.task; legacy ops.run; request ops.data_request; document kb.document;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task;
 IF job.data_request_id IS NOT NULL THEN
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=job.data_request_id;
 SELECT * INTO STRICT document FROM kb.document d WHERE d.project_id=request.project_id
 AND d.key=request.original_source AND d.mime='application/pdf';
 RETURN QUERY SELECT request.project_id,job.release_id,NULL::bigint,request.id,
 job.data_generation::bigint,document.id,document.content_hash;
 ELSE
 SELECT * INTO STRICT legacy FROM ops.run WHERE id=job.run_id;
 IF job.unit_type='document' THEN
 SELECT * INTO STRICT document FROM kb.document d WHERE d.id=job.unit_id
 AND d.project_id=legacy.project_id;
 ELSIF job.unit_type='source_view' THEN
 SELECT d.* INTO STRICT document FROM kb.document d
 JOIN kb.source_view view ON view.document_id=d.id
 JOIN ops.run_source_view selected ON selected.source_view_id=view.id
 WHERE view.id=job.unit_id AND selected.run_id=legacy.id AND d.project_id=legacy.project_id;
 ELSE RAISE EXCEPTION 'PDF task has no original document context' USING ERRCODE='23514'; END IF;
 RETURN QUERY SELECT legacy.project_id,legacy.release_id,legacy.id,NULL::text,NULL::bigint,
 document.id,document.content_hash;
 END IF;
END $stage$;
REVOKE ALL ON FUNCTION ops.pdf_task_context(bigint) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.pdf_stage_owner_current(p_task bigint,p_attempt bigint,p_holder text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE job ops.task; request ops.data_request; legacy ops.run;
BEGIN
 SELECT * INTO job FROM ops.task WHERE id=p_task;
 IF NOT FOUND OR p_attempt IS NULL OR nullif(p_holder,'') IS NULL
 OR job.attempt IS DISTINCT FROM p_attempt OR job.claimed_by IS DISTINCT FROM p_holder
 OR job.status<>'running' OR job.lease_until IS NULL OR job.lease_until<=clock_timestamp() THEN
 RETURN false; END IF;
 IF job.data_request_id IS NULL THEN
 SELECT * INTO legacy FROM ops.run WHERE id=job.run_id;
 RETURN FOUND AND NOT legacy.sealed AND legacy.status IN ('created','running');
 END IF;
 SELECT * INTO request FROM ops.data_request WHERE id=job.data_request_id;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM ops.ddo_authorize_request(request);
 RETURN request.generation IS NOT DISTINCT FROM job.data_generation
 AND request.live_task_id IS NOT DISTINCT FROM job.id
 AND request.release_id IS NOT DISTINCT FROM job.release_id
 AND EXISTS(SELECT FROM sem.data_operation_definition definition
 WHERE definition.release_id=request.release_id AND definition.operation_id=request.operation_id
 AND definition.support_contract->'capabilities'->>'preparation'='pdf-native')
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
RETURNS TABLE(project_id text,release_id text,run_id bigint,request_id text,generation bigint,
 document_id bigint,source_digest text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE job ops.task; legacy ops.run; request ops.data_request; context record;
BEGIN
 IF p_task IS NULL OR p_attempt IS NULL OR p_holder IS NULL OR p_holder='' THEN
 RAISE EXCEPTION 'stale private PDF build owner' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT context FROM ops.pdf_task_context(p_task);
 IF context.request_id IS NOT NULL THEN
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=context.request_id;
 PERFORM ops.ddo_lock_support(request.project_id,request.original_source,
 request.binding->'support');
 PERFORM 1 FROM ops.data_demand demand WHERE EXISTS(SELECT FROM ops.demand_use use_
 WHERE use_.demand_id=demand.id AND use_.request_id=request.id
 AND use_.generation=request.generation
 AND use_.fate='attached') ORDER BY demand.id FOR SHARE;
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=context.request_id FOR UPDATE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task FOR UPDATE;
 ELSE
 SELECT * INTO STRICT legacy FROM ops.run WHERE id=context.run_id FOR SHARE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=legacy.id FOR UPDATE;
 END IF;
 IF NOT ops.pdf_stage_owner_current(p_task,p_attempt,p_holder) THEN
 RAISE EXCEPTION 'stale private PDF build owner/capability/support' USING ERRCODE='P0004'; END IF;
 RETURN QUERY SELECT context.project_id,context.release_id,context.run_id,context.request_id,
 context.generation,context.document_id,context.source_digest;
END $stage$;
REVOKE ALL ON FUNCTION ops.require_pdf_stage_owner(bigint,bigint,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.retain_pdf_original(p_task bigint,p_attempt bigint,p_holder text,
 p_original bytea,p_recipe bytea)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE owner record; original_digest text; recipe_digest text;
BEGIN
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(owner.release_id,'retain_pdf_original');
 IF p_original IS NULL OR substring(p_original FROM 1 FOR 5)<>convert_to('%PDF-','UTF8')
 OR p_recipe IS NULL OR octet_length(p_recipe)=0 THEN
 RAISE EXCEPTION 'original PDF or recipe bytes unavailable' USING ERRCODE='23514'; END IF;
 PERFORM convert_from(p_recipe,'UTF8')::jsonb;
 original_digest:=encode(sha256(p_original),'hex');
 recipe_digest:=encode(sha256(p_recipe),'hex');
 IF original_digest IS DISTINCT FROM owner.source_digest THEN
 RAISE EXCEPTION 'original PDF differs from exact document custody' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.source_artifact(artifact_digest,content) VALUES(original_digest,p_original),
 (recipe_digest,p_recipe) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.source_artifact
 WHERE artifact_digest=original_digest AND content=p_original)
 OR NOT EXISTS(SELECT FROM kb.source_artifact
 WHERE artifact_digest=recipe_digest AND content=p_recipe) THEN
 RAISE EXCEPTION 'original PDF or recipe artifact digest conflict' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.source_build(task_id,release_id,artifact_digest,recipe_digest)
 VALUES(p_task,owner.release_id,original_digest,recipe_digest) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.source_build source WHERE source.task_id=p_task
 AND source.release_id=owner.release_id AND source.artifact_digest=original_digest
 AND source.recipe_digest=recipe_digest) THEN
 RAISE EXCEPTION 'original PDF source build replay differs' USING ERRCODE='23514'; END IF;
 RETURN original_digest;
END $stage$;
REVOKE ALL ON FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea)
TO corpus_sem_writer;
CREATE OR REPLACE FUNCTION ops.begin_pdf_build(p_task bigint,p_attempt bigint,p_holder text,
 p_source text,p_recipe text,p_schema text,p_key text)
RETURNS SETOF ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,
 pg_temp AS $stage$
DECLARE owner record; build ops.pdf_stage_build; id text;
BEGIN
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
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
 INSERT INTO ops.pdf_stage_build VALUES(id,p_task,owner.run_id,owner.release_id,p_source,p_recipe,
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
CREATE OR REPLACE FUNCTION ops.require_pdf_build(p_build text,p_task bigint,p_attempt bigint,
 p_holder text)
RETURNS ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,
 pg_temp AS $stage$
DECLARE owner record; build ops.pdf_stage_build;
BEGIN
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 IF p_build IS NULL THEN RAISE EXCEPTION 'private PDF build is not owned/open'
 USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT build FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task
 FOR UPDATE;
 IF build.release_id IS DISTINCT FROM owner.release_id OR build.attempt IS DISTINCT FROM p_attempt
 OR build.holder IS DISTINCT FROM p_holder OR
 build.state<>'open' THEN
 RAISE EXCEPTION 'private PDF build is not owned/open' USING ERRCODE='P0004'; END IF;
 RETURN build;
END $stage$;
REVOKE ALL ON FUNCTION ops.require_pdf_build(text,bigint,bigint,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.require_pdf_stage_scratch(p_name text,p_relation regclass)
RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE scratch oid:=to_regclass('pg_temp.'||p_name);
BEGIN
 IF scratch IS NULL OR NOT EXISTS(SELECT FROM pg_class WHERE oid=scratch
 AND relowner='corpus_sem_publisher'::regrole AND relnamespace=pg_my_temp_schema()
 AND relkind='r' AND relpersistence='t' AND NOT relrowsecurity) OR
 EXISTS(SELECT FROM pg_trigger WHERE tgrelid=scratch) OR
 EXISTS(SELECT FROM pg_rewrite WHERE ev_class=scratch) OR
 EXISTS(SELECT FROM pg_inherits WHERE inhrelid=scratch OR inhparent=scratch) OR
 EXISTS(SELECT FROM pg_attrdef WHERE adrelid=scratch) OR
 EXISTS(SELECT FROM pg_index WHERE indrelid=scratch) OR
 EXISTS(SELECT FROM pg_constraint WHERE conrelid=scratch
 AND (contype NOT IN ('c','n') OR NOT convalidated)) THEN
 RAISE EXCEPTION 'untrusted private PDF scratch' USING ERRCODE='23514'; END IF;
 IF ARRAY(SELECT ROW(attnum,attname,atttypid,atttypmod,attnotnull,attgenerated,attidentity)::text
 FROM pg_attribute WHERE attrelid=scratch AND attnum>0 AND NOT attisdropped ORDER BY attnum)
 IS DISTINCT FROM
 ARRAY(SELECT ROW(attnum,attname,atttypid,atttypmod,attnotnull,attgenerated,attidentity)::text
 FROM pg_attribute WHERE attrelid=p_relation AND attnum>0 AND NOT attisdropped ORDER BY attnum)
 OR ARRAY(SELECT pg_get_constraintdef(oid,true) FROM pg_constraint
 WHERE conrelid=scratch AND contype='c' ORDER BY 1) IS DISTINCT FROM
 ARRAY(SELECT pg_get_constraintdef(oid,true) FROM pg_constraint
 WHERE conrelid=p_relation AND contype='c' ORDER BY 1) THEN
 RAISE EXCEPTION 'private PDF scratch schema differs' USING ERRCODE='23514'; END IF;
END $stage$;
REVOKE ALL ON FUNCTION ops.require_pdf_stage_scratch(text,regclass) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.prepare_pdf_stage(p_build text,p_task bigint,p_attempt bigint,
 p_holder text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE build ops.pdf_stage_build;
BEGIN
 build:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(build.release_id,'adopt_pdf_batch');
"""
    )
    relations = [metadata.tables[name] for name in STAGE_FAMILIES.values()]
    pg = dialect()
    for relation in relations:
        scratch = "ps_" + relation.name
        sql += (
            f"IF to_regclass('pg_temp.{scratch}') IS NULL THEN CREATE TEMP TABLE {scratch} "
            f"(LIKE {relation.fullname} INCLUDING CONSTRAINTS) ON COMMIT DROP; "
            f"ELSE PERFORM ops.require_pdf_stage_scratch('{scratch}',"
            f"'{relation.fullname}'::regclass); END IF; "
            f"TRUNCATE pg_temp.{scratch};\n"
        )
        # COPY is allowed only on the protected, exact session scratch.
        sql += f"GRANT SELECT,INSERT ON pg_temp.{scratch} TO corpus_sem_writer;\n"
    sql += "END $stage$;\n"
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
 PERFORM ops.require_pdf_stage_scratch('ps_{relation.name}','{relation.fullname}'::regclass);
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
    for relation in relations:
        columns = ",".join(pg.identifier_preparer.quote(c.name) for c in relation.columns)
        scratch = "pg_temp.ps_" + relation.name
        sql += (
            f"IF EXISTS(SELECT {columns} FROM {scratch} "
            f"EXCEPT SELECT {columns} FROM {relation.fullname}) THEN "
            "RAISE EXCEPTION 'private PDF batch replay content differs' "
            "USING ERRCODE='23514'; END IF;\n"
        )
    sql += "  RETURN NEXT receipt; RETURN;\n END IF;\n"
    for relation in relations:
        scratch = "pg_temp.ps_" + relation.name
        columns = ",".join(pg.identifier_preparer.quote(c.name) for c in relation.columns)
        sql += (
            f"INSERT INTO {relation.fullname}({columns}) SELECT {columns} "
            f"FROM {scratch} ON CONFLICT DO NOTHING;\n"
        )
        sql += (
            f"IF EXISTS(SELECT {columns} FROM {scratch} "
            f"EXCEPT SELECT {columns} FROM {relation.fullname}) THEN "
            "RAISE EXCEPTION 'changed private record duplicate' USING ERRCODE='23514'; END IF;\n"
        )
    sql += """
 INSERT INTO ops.pdf_stage_receipt VALUES(p_build,p_key,digest,total) RETURNING * INTO receipt;
 RETURN NEXT receipt;
END $stage$;
CREATE OR REPLACE FUNCTION ops.inspect_pdf_progress(p_build text,p_task bigint,p_attempt bigint,
 p_holder text)
RETURNS SETOF ops.pdf_stage_receipt LANGUAGE plpgsql SECURITY DEFINER SET
 search_path=pg_catalog,pg_temp AS $stage$
DECLARE build ops.pdf_stage_build;
BEGIN
 build:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(build.release_id,'inspect_pdf_progress');
 RETURN QUERY SELECT * FROM ops.pdf_stage_receipt WHERE build_id=p_build ORDER BY replay_key;
END $stage$;
CREATE OR REPLACE FUNCTION ops.resume_pdf_build(p_build text,p_task bigint,p_attempt bigint,
 p_holder text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE owner record; build ops.pdf_stage_build;
BEGIN
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(owner.release_id,'resume_pdf_build');
 IF p_build IS NULL THEN RAISE EXCEPTION 'private PDF resume binding differs'
 USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT build FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task
 FOR UPDATE;
 IF build.release_id IS DISTINCT FROM owner.release_id OR build.state NOT IN ('open','frozen')
 OR build.attempt>p_attempt OR (build.state='frozen' AND NOT EXISTS(
 SELECT FROM ops.pdf_frozen_build f WHERE f.build_id=build.build_id)) THEN
 RAISE EXCEPTION 'private PDF resume binding differs' USING ERRCODE='23514'; END IF;
 UPDATE ops.pdf_stage_build SET attempt=p_attempt,holder=p_holder WHERE build_id=p_build;
END $stage$;
CREATE OR REPLACE FUNCTION ops.abandon_pdf_build(p_build text,p_task bigint,p_attempt bigint,
 p_holder text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE build ops.pdf_stage_build;
BEGIN
 build:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(build.release_id,'abandon_pdf_build');
 IF NOT ops.execution_edge(build.release_id,'pdf_private_build','open','abandoned') THEN
 RAISE EXCEPTION 'private PDF abandonment transition unavailable' USING ERRCODE='23514'; END IF;
 UPDATE ops.pdf_stage_build SET state='abandoned' WHERE build_id=p_build;
END $stage$;
"""
    for signature in (
        "begin_pdf_build(bigint,bigint,text,text,text,text,text)",
        "prepare_pdf_stage(text,bigint,bigint,text)",
        "adopt_pdf_batch(text,bigint,bigint,text,text)",
        "inspect_pdf_progress(text,bigint,bigint,text)",
        "resume_pdf_build(text,bigint,bigint,text)",
        "abandon_pdf_build(text,bigint,bigint,text)",
    ):
        sql += (
            f"REVOKE ALL ON FUNCTION ops.{signature} FROM PUBLIC; "
            f"GRANT EXECUTE ON FUNCTION ops.{signature} TO corpus_sem_writer;\n"
        )
    from .pdf_staging import stage_upload_profile

    profile = stage_upload_profile()
    return (
        sql.replace("total>65536", "total>" + str(profile["max_rows"]))
        .replace("total_bytes>67108864", "total_bytes>" + str(profile["max_native_bytes"]))
        .replace(
            "octet_length(p_key)>1024",
            "octet_length(p_key)>" + str(profile["max_replay_key_bytes"]),
        )
    )
