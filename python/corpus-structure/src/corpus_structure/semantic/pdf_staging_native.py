"""Model-derived private PDF staging DDL and protected batch operations."""

from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import AddConstraint, CreateTable

from .metadata import metadata
from .native_products import NativeProduct
from .pdf_staging import STAGE_FAMILIES
from .source_view_native import native_admission_sql


def stage_native_sql() -> str:
    sql = """
CREATE OR REPLACE FUNCTION ops.require_pdf_stage_owner(p_task bigint,p_attempt bigint,p_holder
 text)
RETURNS ops.run LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE job ops.task; run ops.run;
BEGIN
 IF p_task IS NULL OR p_attempt IS NULL OR p_holder IS NULL OR p_holder='' THEN
 RAISE EXCEPTION 'stale private PDF build owner' USING ERRCODE='P0004'; END IF;
 SELECT r.* INTO STRICT run FROM ops.run r JOIN ops.task t ON t.run_id=r.id WHERE t.id=p_task
 FOR SHARE OF r;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=run.id FOR UPDATE;
 IF job.attempt IS DISTINCT FROM p_attempt OR job.claimed_by IS DISTINCT FROM p_holder
 OR job.status<>'running'
 OR job.lease_until IS NULL OR job.lease_until<=clock_timestamp() OR run.sealed OR run.status
 NOT IN ('created','running') THEN
  RAISE EXCEPTION 'stale private PDF build owner' USING ERRCODE='P0004'; END IF;
 RETURN run;
END $stage$;
REVOKE ALL ON FUNCTION ops.require_pdf_stage_owner(bigint,bigint,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.begin_pdf_build(p_task bigint,p_attempt bigint,p_holder text,
 p_source text,p_recipe text,p_schema text,p_key text)
RETURNS SETOF ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,
 pg_temp AS $stage$
DECLARE run ops.run; build ops.pdf_stage_build; id text;
BEGIN
 run:=ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM sem.require_execution_operation(run.release_id,'begin_pdf_build');
 IF p_source IS NULL OR p_recipe IS NULL OR p_schema IS DISTINCT FROM '{native_schema_sha}'
 OR p_key IS NULL OR p_key=''
 OR octet_length(p_key)>1024 OR NOT
 EXISTS(SELECT FROM ops.source_build s WHERE s.task_id=p_task
 AND s.release_id=run.release_id AND s.artifact_digest=p_source AND s.recipe_digest=p_recipe)
 OR NOT EXISTS(SELECT FROM kb.document d JOIN ops.task t ON t.id=p_task WHERE
 d.project_id=run.project_id
 AND d.content_hash=p_source AND ((t.unit_type='document' AND d.id=t.unit_id) OR
 (t.unit_type='source_view' AND EXISTS(
 SELECT FROM kb.source_view v JOIN ops.run_source_view s ON s.source_view_id=v.id WHERE
 v.id=t.unit_id AND s.run_id=run.id AND v.document_id=d.id)))) THEN
 RAISE EXCEPTION 'private PDF build source custody differs' USING ERRCODE='23514'; END IF;
 id:=encode(sha256(convert_to(jsonb_build_array(p_task,p_source,p_recipe,p_schema,p_key)::text,
 'UTF8')),'hex');
 INSERT INTO ops.pdf_stage_build VALUES(id,p_task,run.id,run.release_id,p_source,p_recipe,
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
DECLARE run ops.run; build ops.pdf_stage_build;
BEGIN
 run:=ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 IF p_build IS NULL THEN RAISE EXCEPTION 'private PDF build is not owned/open'
 USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT build FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task
 FOR UPDATE;
 IF build.release_id IS DISTINCT FROM run.release_id OR build.attempt IS DISTINCT FROM p_attempt
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
 PERFORM sem.require_execution_operation(build.release_id,'adopt_pdf_batch');
"""
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
 PERFORM sem.require_execution_operation(build.release_id,'adopt_pdf_batch');
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
 SELECT count(*),COALESCE(sum(octet_length(to_jsonb(s)::text)),0) INTO n,bytes FROM {scratch} s;
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
 PERFORM sem.require_execution_operation(build.release_id,'inspect_pdf_progress');
 RETURN QUERY SELECT * FROM ops.pdf_stage_receipt WHERE build_id=p_build ORDER BY replay_key;
END $stage$;
CREATE OR REPLACE FUNCTION ops.resume_pdf_build(p_build text,p_task bigint,p_attempt bigint,
 p_holder text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE run ops.run; build ops.pdf_stage_build;
BEGIN
 run:=ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM sem.require_execution_operation(run.release_id,'resume_pdf_build');
 IF p_build IS NULL THEN RAISE EXCEPTION 'private PDF resume binding differs'
 USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT build FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task
 FOR UPDATE;
 IF build.release_id IS DISTINCT FROM run.release_id OR build.state<>'open'
 OR build.attempt>p_attempt THEN
 RAISE EXCEPTION 'private PDF resume binding differs' USING ERRCODE='23514'; END IF;
 UPDATE ops.pdf_stage_build SET attempt=p_attempt,holder=p_holder WHERE build_id=p_build;
END $stage$;
CREATE OR REPLACE FUNCTION ops.abandon_pdf_build(p_build text,p_task bigint,p_attempt bigint,
 p_holder text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $stage$
DECLARE build ops.pdf_stage_build;
BEGIN
 build:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM sem.require_execution_operation(build.release_id,'abandon_pdf_build');
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
    from hashlib import sha256

    from .pdf_records import native_schema_bytes
    from .pdf_staging import stage_upload_profile

    profile = stage_upload_profile()
    return (
        sql.replace("{native_schema_sha}", sha256(native_schema_bytes()).hexdigest())
        .replace("total>65536", "total>" + str(profile["max_rows"]))
        .replace("total_bytes>67108864", "total_bytes>" + str(profile["max_bytes"]))
        .replace(
            "octet_length(p_key)>1024",
            "octet_length(p_key)>" + str(profile["max_replay_key_bytes"]),
        )
    )


def pdf_staging_products(model=None, *, authoring_provenance=None):
    from .migrations import ALEMBIC_DIR
    from .pdf_record_native import pdf_record_products

    base_sql = pdf_record_products(model, authoring_provenance=authoring_provenance)[
        0
    ].content.decode()
    sql = (
        "SET LOCAL ROLE __MIGRATION_OWNER__;\n"
        "GRANT REFERENCES(id) ON ops.task TO corpus_sem_publisher;\n"
        "SET LOCAL ROLE corpus_sem_publisher;\n"
    )
    relations = {
        name: rel for name, rel in metadata.tables.items() if rel.name.startswith("pdf_stage_")
    }
    pg = dialect()
    for _name, relation in sorted(relations.items()):
        sql += (
            str(
                CreateTable(relation, include_foreign_key_constraints=[]).compile(dialect=pg)
            ).strip()
            + ";\n"
        )
    for name, relation in sorted(relations.items()):
        for constraint in sorted(relation.foreign_key_constraints, key=lambda item: str(item.name)):
            sql += (
                str(AddConstraint(constraint, isolate_from_table=False).compile(dialect=pg)).strip()
                + ";\n"
            )
        if relation.info["immutability"] == "immutable":
            sql += (
                "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE "
                f"ON {name} FOR EACH STATEMENT "
                "EXECUTE FUNCTION sem.refuse_immutable_mutation();\n"
            )
        sql += (
            f"REVOKE ALL ON {name} FROM PUBLIC,corpus_sem_writer,corpus_sem_reader,"
            "corpus_sem_admitter,corpus_sem_evaluator;\n"
        )
    sql += base_sql
    sql += stage_native_sql()
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0063_admission.sql").read_text()
    admission = native_admission_sql(
        sql,
        model,
        extra_relations=sorted(
            [
                *relations,
                *(
                    name
                    for name in metadata.tables
                    if ".pdf_record_" in name or ".pdf_artifact_" in name
                ),
            ]
        ),
        base_admission=previous,
        authoring_provenance=authoring_provenance,
    )
    return (
        NativeProduct("semantic_0064_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0064_admission.sql", admission.encode()),
    )
