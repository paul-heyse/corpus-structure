CREATE OR REPLACE FUNCTION data.require_execution_release(r text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $admission$
DECLARE expected jsonb; spec jsonb; owner_name text;
BEGIN
 -- generated physical catalog checks
 SELECT pg_get_userbyid(nspowner) INTO owner_name FROM pg_namespace WHERE nspname='sem';
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'functions') item
 LEFT JOIN pg_proc p ON p.oid=to_regprocedure(item.value->>'signature')
 LEFT JOIN pg_language l ON l.oid=p.prolang
 WHERE p.oid IS NULL OR encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') IS DISTINCT FROM item.value->>'body_sha256'
 OR p.prosecdef IS DISTINCT FROM (item.value->>'security')::boolean
 OR p.proisstrict IS DISTINCT FROM (item.value->>'strict')::boolean OR p.provolatile::text IS DISTINCT FROM item.value->>'volatility' OR p.proparallel::text IS DISTINCT FROM item.value->>'parallel' OR p.proleakproof IS DISTINCT FROM (item.value->>'leakproof')::boolean
 OR l.lanname IS DISTINCT FROM item.value->>'language'
 OR p.prorettype IS DISTINCT FROM to_regtype(item.value->>'result')
 OR p.proretset IS DISTINCT FROM (item.value->>'setof')::boolean
 OR COALESCE(to_jsonb(p.proconfig),'[]'::jsonb) IS DISTINCT FROM item.value->'config'
 OR pg_get_userbyid(p.proowner) IS DISTINCT FROM (CASE WHEN item.value->>'owner'='$migration_owner' THEN owner_name ELSE item.value->>'owner' END)
 OR has_function_privilege('corpus_sem_admitter',p.oid,'EXECUTE') IS DISTINCT FROM ((item.value->'execute_roles') ? 'corpus_sem_admitter') OR has_function_privilege('corpus_sem_evaluator',p.oid,'EXECUTE') IS DISTINCT FROM ((item.value->'execute_roles') ? 'corpus_sem_evaluator') OR has_function_privilege('corpus_sem_writer',p.oid,'EXECUTE') IS DISTINCT FROM ((item.value->'execute_roles') ? 'corpus_sem_writer') OR has_function_privilege('corpus_sem_reader',p.oid,'EXECUTE') IS DISTINCT FROM ((item.value->'execute_roles') ? 'corpus_sem_reader') OR EXISTS(SELECT FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0 AND a.privilege_type='EXECUTE')
 ORDER BY item.value->>'signature' LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native execution kernel differs: %',spec->>'signature' USING ERRCODE='23514'; END IF;
 -- generated trigger catalog checks
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'tables') item
 LEFT JOIN pg_class relation ON relation.oid=to_regclass(item.value->>'relation')
 WHERE relation.oid IS NULL OR relation.relkind<>'r' OR relation.relpersistence<>'p'
 OR relation.relrowsecurity OR relation.relforcerowsecurity
 OR pg_get_userbyid(relation.relowner) IS DISTINCT FROM item.value->>'owner'
 OR (SELECT jsonb_agg(jsonb_build_object('name',a.attname,'type',format_type(a.atttypid,a.atttypmod),'not_null',a.attnotnull,'identity',a.attidentity::text,'generated',a.attgenerated::text,'default',pg_get_expr(default_value.adbin,default_value.adrelid)) ORDER BY a.attname COLLATE "C")
     FROM pg_attribute a LEFT JOIN pg_attrdef default_value ON default_value.adrelid=a.attrelid AND default_value.adnum=a.attnum
     WHERE a.attrelid=relation.oid AND a.attnum>0 AND NOT a.attisdropped) IS DISTINCT FROM item.value->'columns'
 OR (SELECT to_jsonb(ARRAY(SELECT a.attname::text FROM unnest(c.conkey) WITH ORDINALITY cols(num,position) JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=cols.num ORDER BY cols.position)) FROM pg_constraint c WHERE c.conrelid=relation.oid AND c.contype='p') IS DISTINCT FROM item.value->'primary_key'
 OR (SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.conname,'columns',ARRAY(SELECT a.attname::text FROM unnest(c.conkey) WITH ORDINALITY cols(num,position) JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=cols.num ORDER BY cols.position),'target',remote_schema.nspname||'.'||remote.relname,'remote_columns',ARRAY(SELECT a.attname::text FROM unnest(c.confkey) WITH ORDINALITY cols(num,position) JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=cols.num ORDER BY cols.position),'on_update',c.confupdtype::text,'on_delete',c.confdeltype::text,'match',c.confmatchtype::text,'deferrable',c.condeferrable,'deferred',c.condeferred,'validated',c.convalidated) ORDER BY c.conname),'[]'::jsonb)
     FROM pg_constraint c JOIN pg_class remote ON remote.oid=c.confrelid JOIN pg_namespace remote_schema ON remote_schema.oid=remote.relnamespace WHERE c.conrelid=relation.oid AND c.contype='f') IS DISTINCT FROM item.value->'foreign_keys'
 OR EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader'),('corpus_sem_evaluator'),('corpus_sem_admitter')) actors(name) WHERE has_table_privilege(actors.name,relation.oid,'SELECT') IS DISTINCT FROM (COALESCE(item.value->'read_roles','["corpus_sem_writer","corpus_sem_reader","corpus_sem_admitter","corpus_sem_evaluator"]'::jsonb) ? actors.name) OR has_any_column_privilege(actors.name,relation.oid,'SELECT') IS DISTINCT FROM (COALESCE(item.value->'read_roles','["corpus_sem_writer","corpus_sem_reader","corpus_sem_admitter","corpus_sem_evaluator"]'::jsonb) ? actors.name) OR has_table_privilege(actors.name,relation.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_any_column_privilege(actors.name,relation.oid,'INSERT,UPDATE,REFERENCES'))
 OR EXISTS(SELECT FROM aclexplode(coalesce(relation.relacl,acldefault('r',relation.relowner))) acl WHERE acl.grantee=0)
 LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native source frame projection differs: %',spec->>'relation' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'readers') item
 CROSS JOIN LATERAL jsonb_array_elements_text(item.value->'roles') required_role(name)
 WHERE to_regclass(item.value->>'relation') IS NULL OR NOT has_table_privilege(required_role.name,to_regclass(item.value->>'relation'),'SELECT') LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'required native read capability is unavailable: %',spec->>'relation' USING ERRCODE='23514'; END IF;
 -- generated index catalog checks
 IF EXISTS(SELECT FROM pg_roles WHERE rolname='corpus_sem_evaluator' AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
 OR EXISTS(SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname='corpus_sem_evaluator') THEN RAISE EXCEPTION 'unrestricted evaluation principal' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('sem'),('data'),('ops'),('kb'),('eval')) schemas(name) WHERE coalesce(has_schema_privilege('corpus_sem_evaluator',to_regnamespace(schemas.name),'CREATE'),false)) THEN RAISE EXCEPTION 'evaluator schema mutation privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('sem','data','ops','kb','eval') AND c.relkind IN ('r','p') AND (has_table_privilege('corpus_sem_evaluator',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege('corpus_sem_evaluator',c.oid,'INSERT,UPDATE'))) THEN RAISE EXCEPTION 'evaluator direct write privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) WHERE coalesce(has_schema_privilege(roles.name,to_regnamespace('eval'),'USAGE,CREATE'),false))
 OR EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) WHERE n.nspname='eval' AND c.relkind IN ('r','p') AND (has_table_privilege(roles.name,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege(roles.name,c.oid,'SELECT,INSERT,UPDATE'))) THEN RAISE EXCEPTION 'reference data leaked to source principal' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_roles WHERE rolname IN ('corpus_sem_writer','corpus_sem_reader') AND (rolsuper OR rolcreaterole OR rolbypassrls)) OR pg_has_role('corpus_sem_writer','corpus_sem_publisher','MEMBER') OR pg_has_role('corpus_sem_reader','corpus_sem_publisher','MEMBER') OR pg_has_role('corpus_sem_writer',owner_name,'MEMBER') OR pg_has_role('corpus_sem_reader',owner_name,'MEMBER') THEN RAISE EXCEPTION 'unrestricted application principal' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) CROSS JOIN (VALUES('sem'),('data'),('ops'),('kb')) schemas(name) WHERE coalesce(has_schema_privilege(roles.name,to_regnamespace(schemas.name),'CREATE'),false)) THEN RAISE EXCEPTION 'application schema mutation privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) WHERE n.nspname IN ('sem','data') AND c.relkind IN ('r','p') AND (has_table_privilege(roles.name,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege(roles.name,c.oid,'INSERT,UPDATE'))) THEN RAISE EXCEPTION 'application direct semantic write privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) CROSS JOIN (VALUES('data.publish_contract_batch(text,text,text,bytea)'),('data.validate_state(text,text)'),('data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint)'),('data.finish_pre_contract_evaluation(bigint,text,text)')) kernels(signature) WHERE coalesce(has_function_privilege(roles.name,to_regprocedure(kernels.signature),'EXECUTE'),false)) THEN RAISE EXCEPTION 'application private kernel privilege' USING ERRCODE='23514'; END IF;
 -- generated native CHECK catalog checks
 IF EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='eval' AND c.relkind IN ('r','p') AND has_table_privilege('corpus_sem_admitter',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')) THEN RAISE EXCEPTION 'admission principal has reference access' USING ERRCODE='42501'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader'),('corpus_sem_admitter'),('corpus_sem_evaluator')) principal(name)
  WHERE has_database_privilege(principal.name,current_database(),'TEMP') OR pg_has_role(principal.name,'corpus_sem_publisher','MEMBER') OR pg_has_role(principal.name,owner_name,'MEMBER')) THEN
  RAISE EXCEPTION 'privileged runtime principal' USING ERRCODE='42501'; END IF;
END
$admission$;
ALTER FUNCTION data.require_execution_release(text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.require_execution_release(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;

GRANT EXECUTE ON FUNCTION data.require_execution_release(text),data.execution_contract_descriptor() TO corpus_sem_admitter;
