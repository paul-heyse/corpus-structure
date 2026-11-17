-- Current target helpers selected by target_installation.target_native_definitions.
-- Ownership and grants are declared there; this is not an installation script.

CREATE OR REPLACE FUNCTION sem.refuse_immutable_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 RAISE EXCEPTION 'immutable semantic content: %.% %',TG_TABLE_SCHEMA,TG_TABLE_NAME,TG_OP USING ERRCODE='23514';
END
$body$;

CREATE OR REPLACE FUNCTION sem.guard_finalized_insert() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 IF EXISTS(SELECT FROM sem.release_finalization WHERE release_id=NEW.release_id) THEN
  RAISE EXCEPTION 'finalized release cannot acquire intrinsic meaning: %',NEW.release_id USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END
$body$;

CREATE OR REPLACE FUNCTION sem.record_deployment_admission(r text,p text,d text,k text,c bytea) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 PERFORM sem.require_admission_caller();
 IF NOT EXISTS(SELECT FROM sem.release_finalization WHERE release_id=r) THEN RAISE EXCEPTION 'release is not finalized'; END IF;
 INSERT INTO sem.deployment_admission VALUES(r,p,d,k,c,encode(sha256(c),'hex')) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM sem.deployment_admission WHERE release_id=r AND physical_id=p AND deployment_id=d AND kind=k AND content=c AND content_digest=encode(sha256(c),'hex')) THEN
  RAISE EXCEPTION 'deployment admission replay differs' USING ERRCODE='23505'; END IF;
END
$body$;

CREATE OR REPLACE FUNCTION sem.record_sql_admission(r text,ik text,n text,p text,c bytea) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 PERFORM sem.require_admission_caller();
 IF NOT EXISTS(SELECT FROM sem.release_finalization WHERE release_id=r) THEN RAISE EXCEPTION 'release is not finalized'; END IF;
 INSERT INTO sem.sql_admission(release_id,input_kind,input_name,physical_id,content,content_digest)
 VALUES(r,ik,n,p,c,encode(sha256(c),'hex')) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM sem.sql_admission WHERE release_id=r AND input_kind=ik AND input_name=n AND physical_id=p AND content=c AND content_digest=encode(sha256(c),'hex')) THEN
  RAISE EXCEPTION 'SQL admission replay differs' USING ERRCODE='23505'; END IF;
END
$body$;

CREATE OR REPLACE FUNCTION sem.activate_release(p text,r text,parent text,g bigint) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint;
BEGIN
 PERFORM sem.require_admission_caller();
 IF NOT EXISTS(SELECT FROM sem.release_finalization WHERE release_id=r) THEN RAISE EXCEPTION 'release is not finalized'; END IF;
 PERFORM data.require_execution_release(r);
 UPDATE data.project SET active_release_id=r,generation=generation+1
 WHERE project_id=p AND active_release_id IS NOT DISTINCT FROM parent AND generation=g RETURNING generation INTO result;
 IF NOT FOUND THEN RAISE EXCEPTION 'stale activation token' USING ERRCODE='40001'; END IF;
 RETURN result;
END
$body$;

CREATE OR REPLACE FUNCTION data.require_runtime_principal(purpose text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE principal name:=session_user; required_role text; owner_oid oid;
BEGIN
 required_role:=CASE purpose WHEN 'read' THEN 'corpus_sem_reader' WHEN 'write' THEN 'corpus_sem_writer' WHEN 'evaluate' THEN 'corpus_sem_evaluator' WHEN 'admit' THEN 'corpus_sem_admitter' END;
 IF required_role IS NULL THEN RAISE EXCEPTION 'unknown runtime purpose'; END IF;
 SELECT nspowner INTO owner_oid FROM pg_namespace WHERE nspname='sem';
 IF NOT pg_has_role(principal,required_role,'USAGE') OR current_setting('role') NOT IN ('none',principal::text)
 OR EXISTS(SELECT FROM pg_roles WHERE oid=principal::regrole AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls OR rolreplication))
 OR pg_has_role(principal,'corpus_sem_publisher','MEMBER') OR pg_has_role(principal,owner_oid,'MEMBER')
 OR has_database_privilege(principal,current_database(),'TEMP')
 OR EXISTS(SELECT FROM pg_namespace WHERE nspname IN ('sem','data','ops','kb','eval') AND has_schema_privilege(principal,oid,'CREATE'))
 OR EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('sem','data') AND c.relkind IN ('r','p') AND (has_table_privilege(principal,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege(principal,c.oid,'INSERT,UPDATE'))) THEN
  RAISE EXCEPTION 'unrestricted or mismatched runtime principal for %',purpose USING ERRCODE='42501'; END IF;
 IF NOT has_table_privilege(principal,'sem.release','SELECT')
 OR NOT has_schema_privilege(principal,'ops','USAGE')
 OR (purpose IN ('read','write','evaluate') AND NOT coalesce(has_function_privilege(principal,to_regprocedure('ops.read_demand_result(jsonb)'),'EXECUTE'),false))
 OR (purpose='write' AND NOT coalesce(has_function_privilege(principal,to_regprocedure('ops.initialize_source_project(jsonb)'),'EXECUTE'),false))
 OR (purpose IN ('write','evaluate') AND NOT coalesce(has_function_privilege(principal,to_regprocedure('ops.register_data_demand(jsonb)'),'EXECUTE'),false))
 OR (purpose='evaluate' AND NOT coalesce(has_function_privilege(principal,to_regprocedure('ops.admit_authored_data(jsonb)'),'EXECUTE'),false))
 OR (purpose='admit' AND (NOT coalesce(has_function_privilege(principal,to_regprocedure('sem.publish_release_archive(text)'),'EXECUTE'),false)
 OR NOT coalesce(has_function_privilege(principal,to_regprocedure('ops.inspect_data_execution(jsonb)'),'EXECUTE'),false))) THEN
  RAISE EXCEPTION 'required runtime capability unavailable' USING ERRCODE='42501'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(data.execution_contract_descriptor()->'functions') contract
  LEFT JOIN pg_proc p ON p.oid=to_regprocedure(contract->>'signature')
  WHERE p.oid IS NULL OR has_function_privilege(principal,p.oid,'EXECUTE') IS DISTINCT FROM ((contract->'execute_roles') ? required_role)) THEN
  RAISE EXCEPTION 'runtime operation privileges differ from purpose contract' USING ERRCODE='42501'; END IF;
 IF purpose<>'evaluate'  AND EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='eval' AND c.relkind IN ('r','p') AND has_table_privilege(principal,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')) THEN
  RAISE EXCEPTION 'runtime principal has independent reference access' USING ERRCODE='42501'; END IF;
END
$body$;

CREATE OR REPLACE FUNCTION sem.require_archive_bytes(r text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE archived sem.release; document jsonb; manifest jsonb; expected jsonb; actual jsonb; kind text;
BEGIN
 SELECT * INTO STRICT archived FROM sem.release WHERE release_id=r;
 document:=convert_from(archived.prepared_bytes,'UTF8')::jsonb;
 manifest:=convert_from(archived.manifest_bytes,'UTF8')::jsonb;
 IF archived.profile NOT IN ('semantic-1','semantic-2') OR document->>'format' IS DISTINCT FROM 'semantic-release-archive-3'
 OR manifest->'profile'->>'compiler_version' IS DISTINCT FROM '24'
 OR archived.release_id<>'release:'||encode(sha256(archived.manifest_bytes),'hex')
 OR archived.content_digest<>encode(sha256(archived.prepared_bytes),'hex')
 OR document->'products'->>'release_id' IS DISTINCT FROM r
 OR manifest->'profile'->>'version' IS DISTINCT FROM archived.profile THEN
  RAISE EXCEPTION 'archive manifest identity differs' USING ERRCODE='23514'; END IF;
 FOREACH kind IN ARRAY ARRAY['source','dependency'] LOOP
  expected:=manifest->CASE kind WHEN 'source' THEN 'sources' ELSE 'dependencies' END;
  SELECT COALESCE(jsonb_agg(jsonb_build_array(input_name,content_digest) ORDER BY input_name),'[]'::jsonb) INTO actual
  FROM sem.input WHERE release_id=r AND input_kind=kind;
  IF expected IS DISTINCT FROM actual THEN RAISE EXCEPTION 'archive input manifest differs: %',kind USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT COALESCE(jsonb_agg(jsonb_build_array(artifact_name,content_digest) ORDER BY artifact_name),'[]'::jsonb) INTO actual FROM sem.artifact WHERE release_id=r;
 SELECT COALESCE(jsonb_agg(jsonb_build_array(value->>'kind',value->>'digest') ORDER BY value->>'kind'),'[]'::jsonb) INTO expected
 FROM jsonb_array_elements(document->'products'->'artifacts');
 IF actual IS DISTINCT FROM expected
 OR EXISTS(SELECT FROM sem.input WHERE release_id=r AND content_digest<>encode(sha256(content),'hex'))
 OR EXISTS(SELECT FROM sem.artifact WHERE release_id=r AND content_digest<>encode(sha256(content),'hex'))
 OR (SELECT count(*) FROM sem.input WHERE release_id=r)<>jsonb_array_length(manifest->'sources')+jsonb_array_length(manifest->'dependencies')+3
 OR (SELECT count(*) FROM sem.input WHERE release_id=r AND (input_kind,input_name) IN (('profile','profile'),('vocabulary','vocabulary'),('ontology_sources','ontology_sources')))<>3 THEN
  RAISE EXCEPTION 'archive product or input closure differs' USING ERRCODE='23514'; END IF;
 IF manifest ? 'data_operation_model' THEN
  IF manifest ? 'execution_model_id' OR document->'products' ? 'execution_model_id'
  OR NOT EXISTS(SELECT FROM sem.artifact WHERE release_id=r AND artifact_name='data_operations.json'
      AND content_digest=manifest->>'data_operation_model')
  OR NOT EXISTS(SELECT FROM sem.input WHERE release_id=r AND input_kind='dependency'
      AND input_name='data-operations/manifest.json')
  OR EXISTS(SELECT FROM sem.input WHERE release_id=r AND input_kind='dependency'
      AND input_name LIKE 'execution/%') THEN
   RAISE EXCEPTION 'target operation archive binding differs' USING ERRCODE='23514'; END IF;
 END IF;
END
$body$;

CREATE OR REPLACE FUNCTION data.require_float_lexical(value text) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $body$
DECLARE exponent integer;
BEGIN
 IF value IN ('0x0.0p+0','-0x0.0p+0') THEN RETURN value; END IF;
 IF value ~ '^-?0x0\.[0-9a-f]{13}p-1022$' AND split_part(value,'.',2) NOT LIKE '0000000000000p%' THEN RETURN value; END IF;
 IF value ~ '^-?0x1\.[0-9a-f]{13}p[+-](0|[1-9][0-9]{0,3})$' THEN
  exponent:=split_part(value,'p',2)::integer;
  IF exponent BETWEEN -1022 AND 1023 AND value NOT LIKE '%p-0' THEN RETURN value; END IF;
 END IF;
 RAISE EXCEPTION 'invalid finite float hexadecimal representation' USING ERRCODE='23514';
END
$body$;

CREATE OR REPLACE FUNCTION sem.require_admission_caller() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE principal name:=session_user; owner_oid oid;
BEGIN
 SELECT nspowner INTO owner_oid FROM pg_namespace WHERE nspname='sem';
 IF pg_has_role(principal,owner_oid,'MEMBER') THEN RETURN; END IF;
 IF NOT pg_has_role(principal,'corpus_sem_admitter','USAGE')
 OR pg_has_role(principal,'corpus_sem_publisher','MEMBER')
 OR EXISTS(SELECT FROM pg_roles WHERE oid=principal::regrole AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls OR rolreplication))
 OR has_database_privilege(principal,current_database(),'TEMP')
 OR EXISTS(SELECT FROM pg_namespace WHERE nspname IN ('sem','data','ops','kb','eval') AND has_schema_privilege(principal,oid,'CREATE'))
 OR EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('sem','data') AND c.relkind IN ('r','p') AND (has_table_privilege(principal,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege(principal,c.oid,'INSERT,UPDATE')))
 OR EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='eval' AND c.relkind IN ('r','p') AND has_table_privilege(principal,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')) OR EXISTS(SELECT FROM jsonb_array_elements(data.execution_contract_descriptor()->'functions') contract
 JOIN pg_proc p ON p.oid=to_regprocedure(contract->>'signature')
 WHERE has_function_privilege(principal,p.oid,'EXECUTE') IS DISTINCT FROM ((contract->'execute_roles') ? 'corpus_sem_admitter')) THEN
  RAISE EXCEPTION 'unrestricted admission caller' USING ERRCODE='42501'; END IF;
END
$body$;
