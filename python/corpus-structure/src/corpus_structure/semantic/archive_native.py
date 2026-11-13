"""Protected typed scratch and atomic publication for immutable release archives."""

from __future__ import annotations

from pglast import ast
from sqlalchemy.dialects.postgresql import dialect

from .archive_transport import archive_tables, scratch_name
from .native_objects import definition_from_sql
from .prepared_sql import prepare_sql

_GUARD = """
CREATE OR REPLACE FUNCTION sem.require_archive_scratch(p_name text,p_relation regclass)
RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $archive$
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
 RAISE EXCEPTION 'untrusted release archive scratch' USING ERRCODE='23514'; END IF;
 IF ARRAY(SELECT ROW(attnum,attname,atttypid,atttypmod,attnotnull,attgenerated,attidentity)::text
 FROM pg_attribute WHERE attrelid=scratch AND attnum>0 AND NOT attisdropped ORDER BY attnum)
 IS DISTINCT FROM
 ARRAY(SELECT ROW(attnum,attname,atttypid,atttypmod,attnotnull,attgenerated,attidentity)::text
 FROM pg_attribute WHERE attrelid=p_relation AND attnum>0 AND NOT attisdropped ORDER BY attnum)
 OR ARRAY(SELECT pg_get_constraintdef(oid,true) FROM pg_constraint
 WHERE conrelid=scratch AND contype='c' ORDER BY 1) IS DISTINCT FROM
 ARRAY(SELECT pg_get_constraintdef(oid,true) FROM pg_constraint
 WHERE conrelid=p_relation AND contype='c' ORDER BY 1) THEN
 RAISE EXCEPTION 'release archive scratch schema differs' USING ERRCODE='23514'; END IF;
END $archive$;
"""


def archive_native_sql() -> str:
    tables = archive_tables()
    quote = dialect().identifier_preparer.quote
    expected = ",".join("'" + scratch_name(t) + "'" for t in sorted(tables, key=lambda t: t.name))
    inventory = f"""
 IF ARRAY(SELECT relname::text FROM pg_class WHERE relnamespace=pg_my_temp_schema()
 AND left(relname,11)='cs_archive_' ORDER BY relname)
 IS DISTINCT FROM ARRAY[{expected}]::text[] THEN
 RAISE EXCEPTION 'archive scratch relation set differs' USING ERRCODE='23514'; END IF;
"""
    prepare = [
        """
CREATE OR REPLACE FUNCTION sem.prepare_release_archive(p_release_id text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $archive$
BEGIN
 PERFORM sem.require_admission_caller();
 IF nullif(p_release_id,'') IS NULL THEN
 RAISE EXCEPTION 'archive identity missing' USING ERRCODE='23514'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(p_release_id,0));
"""
    ]
    publish = [
        """
CREATE OR REPLACE FUNCTION sem.publish_release_archive(p_release_id text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $archive$
DECLARE replay boolean; archive_digest text;
BEGIN
 PERFORM sem.require_admission_caller();
 IF nullif(p_release_id,'') IS NULL THEN
 RAISE EXCEPTION 'archive identity missing' USING ERRCODE='23514'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(p_release_id,0));
""",
        inventory,
    ]
    for relation in tables:
        scratch = quote(scratch_name(relation))
        target = "sem." + quote(relation.name)
        guard = (
            f"PERFORM sem.require_archive_scratch('{scratch_name(relation)}',"
            f"'{relation.fullname}'::regclass);"
        )
        prepare.append(f"""
 IF to_regclass('pg_temp.{scratch}') IS NULL THEN
  CREATE TEMP TABLE {scratch} (LIKE {target} INCLUDING CONSTRAINTS) ON COMMIT DROP;
  REVOKE ALL ON TABLE pg_temp.{scratch} FROM PUBLIC;
  GRANT SELECT,INSERT ON TABLE pg_temp.{scratch} TO corpus_sem_admitter;
 ELSE {guard} TRUNCATE pg_temp.{scratch}; END IF;
""")
        keys = ",".join(quote(c.name) for c in relation.primary_key.columns)
        columns = ",".join(quote(c.name) for c in relation.columns)
        join = " AND ".join(
            f"s.{quote(c.name)}=a.{quote(c.name)}" for c in relation.primary_key.columns
        )
        left = ",".join(f"s.{quote(c.name)}" for c in relation.columns)
        right = ",".join(f"a.{quote(c.name)}" for c in relation.columns)
        publish.append(f"""
 {guard}
 IF EXISTS(SELECT FROM pg_temp.{scratch} WHERE release_id IS DISTINCT FROM p_release_id)
 OR EXISTS(SELECT FROM pg_temp.{scratch} GROUP BY {keys} HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'archive row scope/key differs: {relation.name}' USING ERRCODE='23514'; END IF;
""")
        if relation.info["archive_role"] == "header":
            publish.append(f"""
 IF (SELECT count(*) FROM pg_temp.{scratch})<>1 THEN
 RAISE EXCEPTION 'one complete release required' USING ERRCODE='23514'; END IF;
 SELECT content_digest INTO STRICT archive_digest FROM pg_temp.{scratch};
 replay:=EXISTS(SELECT FROM sem.release_finalization WHERE release_id=p_release_id);
""")
        publish.append(f"""
 IF NOT replay THEN INSERT INTO {target}({columns}) SELECT {columns} FROM pg_temp.{scratch}; END IF;
 IF EXISTS(SELECT FROM pg_temp.{scratch} s FULL JOIN
 (SELECT {columns} FROM {target} WHERE release_id=p_release_id) a ON {join}
 WHERE ROW({left}) IS DISTINCT FROM ROW({right})) THEN
 RAISE EXCEPTION 'archive replay differs: {relation.name}' USING ERRCODE='23505'; END IF;
""")
    prepare.extend([inventory, "END $archive$;"])
    publish.append("""
 IF EXISTS(SELECT FROM sem.release WHERE release_id=p_release_id
 AND encode(sha256(prepared_bytes),'hex')<>content_digest)
 OR EXISTS(SELECT FROM sem.input WHERE release_id=p_release_id
 AND encode(sha256(content),'hex')<>content_digest)
 OR EXISTS(SELECT FROM sem.artifact WHERE release_id=p_release_id
 AND encode(sha256(content),'hex')<>content_digest) THEN
  RAISE EXCEPTION 'archive content digest differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.release WHERE release_id=p_release_id AND
 (release_id<>'release:'||encode(sha256(manifest_bytes),'hex') OR
 convert_from(prepared_bytes,'UTF8')::jsonb->'products'->>'release_id'
 IS DISTINCT FROM release_id)) THEN
  RAISE EXCEPTION 'archive manifest identity differs' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_archive_bytes(p_release_id);
 PERFORM sem.require_execution_projection(p_release_id);
 IF NOT replay THEN INSERT INTO sem.release_finalization(release_id,content_digest)
 VALUES(p_release_id,archive_digest); END IF;
 RETURN p_release_id;
END $archive$;
""")
    return "\n".join([_GUARD, *prepare, *publish])


def archive_native_definitions(connection):
    source = "typed release archive:forward"
    prepared = prepare_sql(archive_native_sql(), source=source)
    return tuple(
        definition_from_sql(
            connection,
            prepared.excerpt(index),
            source=source,
            owner="corpus_sem_publisher",
            grants=()
            if statement.stmt.funcname[-1].sval == "require_archive_scratch"
            else (("corpus_sem_admitter", "EXECUTE", False),),
        )
        for index, statement in enumerate(prepared.statements)
        if isinstance(statement.stmt, ast.CreateFunctionStmt) and statement.stmt.funcname
    )
