CREATE OR REPLACE FUNCTION data.require_execution_release(r text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $admission$
DECLARE expected jsonb; spec jsonb; model jsonb; owner_name text; invalid_inference boolean;
BEGIN
 -- {finalized_release}
 PERFORM sem.require_execution_projection(r);
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r) THEN RAISE EXCEPTION 'unknown execution release' USING ERRCODE='23514'; END IF;
 expected:=data.execution_contract_descriptor();
 IF NOT EXISTS(SELECT FROM sem.physical_contract WHERE physical_id=expected->>'physical_id' AND source_digest=expected->>'physical_checks_source_digest') THEN
  RAISE EXCEPTION 'physical CHECK contract is unavailable' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM sem.physical_contract artifact CROSS JOIN LATERAL jsonb_array_elements(artifact.checks) item
 LEFT JOIN pg_constraint c ON c.conrelid=to_regclass(item.value->>'relation') AND c.conname=item.value->>'name' AND c.contype='c'
 WHERE artifact.physical_id=expected->>'physical_id' AND (c.oid IS NULL OR NOT c.convalidated OR pg_get_expr(c.conbin,c.conrelid) IS DISTINCT FROM item.value->>'expression') LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'physical CHECK expression differs: %.%',spec->>'relation',spec->>'name' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_constraint c JOIN pg_class rel ON rel.oid=c.conrelid JOIN pg_namespace ns ON ns.oid=rel.relnamespace
 WHERE c.contype='c' AND (expected->'physical_relations') ? (ns.nspname||'.'||rel.relname)
 AND NOT EXISTS(SELECT FROM sem.physical_contract artifact CROSS JOIN LATERAL jsonb_array_elements(artifact.checks) item
 WHERE artifact.physical_id=expected->>'physical_id' AND item.value->>'relation'=ns.nspname||'.'||rel.relname AND item.value->>'name'=c.conname)) THEN
 RAISE EXCEPTION 'unexpected physical CHECK' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'views') item
 WHERE to_regclass(item.value->>'relation') IS NULL
 OR regexp_replace(regexp_replace(pg_get_viewdef(to_regclass(item.value->>'relation'),true),'\mAS\M','','gi'),'[[:space:]();]','','g')
 IS DISTINCT FROM regexp_replace(regexp_replace(item.value->>'query','\mAS\M','','gi'),'[[:space:]();]','','g') LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native selected-fact view differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.release archived CROSS JOIN LATERAL
   jsonb_array_elements(convert_from(archived.prepared_bytes,'UTF8')::jsonb->'products'->'diagnostics') diagnostic
   WHERE archived.release_id=r AND (diagnostic->>'outcome' IN ('unsupported','unresolved')
    OR (diagnostic->>'outcome'='unchecked' AND NOT
      (diagnostic->>'code'='unchecked_term' AND diagnostic->>'message'='not4curation:unchecked')))) THEN
   RAISE EXCEPTION 'release contains unresolved or unchecked required semantics' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.input i LEFT JOIN sem.sql_admission a
   ON a.release_id=i.release_id AND a.input_kind=i.input_kind AND a.input_name=i.input_name
      AND a.physical_id=expected->>'physical_id'
   WHERE i.release_id=r AND i.input_kind='dependency' AND starts_with(i.input_name,'authored-sql/')
    AND (right(i.input_name,4)<>'.sql' OR length(i.input_name)<=length('authored-sql/.sql')
      OR encode(sha256(i.content),'hex') IS DISTINCT FROM i.content_digest
      OR a.release_id IS NULL OR encode(sha256(a.content),'hex') IS DISTINCT FROM a.content_digest
      OR convert_from(a.content,'UTF8')::jsonb->>'sql' IS DISTINCT FROM convert_from(i.content,'UTF8')
      OR convert_from(a.content,'UTF8')::jsonb->>'release_id' IS DISTINCT FROM r
      OR convert_from(a.content,'UTF8')::jsonb->>'physical_id' IS DISTINCT FROM expected->>'physical_id')) THEN
   RAISE EXCEPTION 'required authored SQL lacks exact current physical admission' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.property_applicability pa WHERE pa.release_id=r AND
    (pa.constraint_scope NOT IN ('shape','accepted_value') OR pa.constraints->>'pattern' IS NOT NULL
     OR COALESCE(pa.constraints->'patterns','[]'::jsonb) NOT IN ('[]'::jsonb,'null'::jsonb))) THEN
   RAISE EXCEPTION 'unsupported required native constraint scope or pattern' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN
  RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 WITH rules AS (
  SELECT convert_from(body,'UTF8')::jsonb rule FROM sem.registry_row WHERE release_id=r AND kind='inference_rule'
 ), signatures AS (
  SELECT rule->>'kind' kind,rule->>'predicate' predicate,COALESCE(NULLIF(rule->>'target',''),rule->>'predicate') target FROM rules
 ), invalid AS (
  SELECT 1 FROM signatures s WHERE s.kind IS NULL OR s.predicate IS NULL OR s.target IS NULL OR s.kind NOT IN ('inverse','symmetric','transitive','subproperty')
   OR NOT EXISTS(SELECT FROM sem.property_applicability a WHERE a.release_id=r AND a.property_id=s.predicate)
   OR NOT EXISTS(SELECT FROM sem.property_applicability a WHERE a.release_id=r AND a.property_id=s.target)
  UNION ALL
  SELECT 1 FROM signatures s JOIN sem.property_applicability a ON a.release_id=r AND a.property_id=s.predicate
  LEFT JOIN sem.class_definition source_range ON source_range.release_id=r AND source_range.name=a.range_name
  LEFT JOIN sem.property_applicability target ON target.release_id=r AND target.property_id=s.target
   AND target.class_id=CASE WHEN s.kind='subproperty' THEN a.class_id ELSE source_range.class_id END
  LEFT JOIN sem.class_definition target_range ON target_range.release_id=r AND target_range.name=target.range_name
  WHERE COALESCE((a.constraints->>'inlined')::boolean,false) OR source_range.class_id IS NULL
   OR target.property_id IS NULL OR COALESCE((target.constraints->>'inlined')::boolean,false) OR target_range.class_id IS NULL
   OR NOT (target_range.class_id=CASE WHEN s.kind IN ('subproperty','transitive') THEN source_range.class_id ELSE a.class_id END
    OR EXISTS(SELECT FROM sem.class_hierarchy h WHERE h.release_id=r AND h.ancestor_id=target_range.class_id
      AND h.class_id=CASE WHEN s.kind IN ('subproperty','transitive') THEN source_range.class_id ELSE a.class_id END))
  UNION ALL
  SELECT 1 FROM sem.property_applicability a CROSS JOIN (VALUES('symmetric'),('transitive')) flags(name)
   WHERE a.release_id=r AND COALESCE((a.constraints->>flags.name)::boolean,false)
    AND NOT EXISTS(SELECT FROM signatures s WHERE s.kind=flags.name AND s.predicate=a.property_id AND s.target=a.property_id)
  UNION ALL
  SELECT 1 FROM sem.property_applicability a LEFT JOIN LATERAL (
    SELECT count(DISTINCT t.property_id) AS count,min(t.property_id) AS target FROM sem.property_applicability t
    WHERE t.release_id=r AND (t.property_id=a.constraints->>'inverse' OR t.constraints->>'name'=a.constraints->>'inverse')
  ) inverse_target ON true
  WHERE a.release_id=r AND NULLIF(a.constraints->>'inverse','') IS NOT NULL
   AND (inverse_target.count<>1 OR NOT EXISTS(SELECT FROM signatures s WHERE s.kind='inverse' AND s.predicate=a.property_id AND s.target=inverse_target.target))
 ) SELECT EXISTS(SELECT FROM invalid) INTO invalid_inference;
 IF invalid_inference THEN RAISE EXCEPTION 'unsupported required native binary inference profile' USING ERRCODE='23514'; END IF;
 SELECT pg_get_userbyid(nspowner) INTO owner_name FROM pg_namespace WHERE nspname='sem';
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row
 WHERE release_id=r AND kind='execution_model';
 IF model IS NULL OR model->'inputs'->>'compiler_version' IS DISTINCT FROM expected->>'execution_abi' THEN
  RAISE EXCEPTION 'incompatible archived execution ABI' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.execution_operation WHERE release_id=r) THEN
  RAISE EXCEPTION 'release execution projection is unavailable' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.artifact WHERE release_id=r AND artifact_name='operation/scientific-policy.json') THEN
  PERFORM sem.require_scientific_layout(r);
 END IF;
 FOR spec IN SELECT jsonb_build_object('id',operation_id) FROM sem.execution_operation WHERE release_id=r LOOP
  PERFORM sem.require_execution_operation(r,spec->>'id');
 END LOOP;
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
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'triggers') item
 LEFT JOIN pg_trigger t ON t.tgrelid=to_regclass(item.value->>'relation') AND t.tgname=item.value->>'name' AND NOT t.tgisinternal
 WHERE t.oid IS NULL OR t.tgenabled NOT IN ('O','A') OR t.tgfoid IS DISTINCT FROM to_regprocedure(item.value->>'function') OR t.tgtype<>(item.value->>'type')::integer OR t.tgdeferrable IS DISTINCT FROM (item.value->>'deferrable')::boolean OR t.tginitdeferred IS DISTINCT FROM (item.value->>'deferred')::boolean OR to_jsonb(ARRAY(SELECT a.attname::text FROM unnest(t.tgattr::smallint[]) WITH ORDINALITY attrs(num,position) JOIN pg_attribute a ON a.attrelid=t.tgrelid AND a.attnum=attrs.num ORDER BY attrs.position)) IS DISTINCT FROM item.value->'columns' OR pg_get_expr(t.tgqual,t.tgrelid) IS DISTINCT FROM item.value->>'when' OR encode(t.tgargs,'hex') IS DISTINCT FROM item.value->>'args' LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native execution guard differs: %.%',spec->>'relation',spec->>'name' USING ERRCODE='23514'; END IF;
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
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'indexes') item
 LEFT JOIN pg_index i ON i.indexrelid=to_regclass(item.value->>'index')
 WHERE i.indexrelid IS NULL OR NOT i.indisvalid OR NOT i.indisready
 OR i.indrelid IS DISTINCT FROM to_regclass(item.value->>'relation')
 OR pg_get_indexdef(i.indexrelid) IS DISTINCT FROM item.value->>'definition' LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native source search index differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_roles WHERE rolname='corpus_sem_evaluator' AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
 OR EXISTS(SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname='corpus_sem_evaluator') THEN RAISE EXCEPTION 'unrestricted evaluation principal' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('sem'),('data'),('ops'),('kb'),('eval')) schemas(name) WHERE has_schema_privilege('corpus_sem_evaluator',schemas.name,'CREATE')) THEN RAISE EXCEPTION 'evaluator schema mutation privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('sem','data','ops','kb','eval') AND c.relkind IN ('r','p') AND (has_table_privilege('corpus_sem_evaluator',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege('corpus_sem_evaluator',c.oid,'INSERT,UPDATE'))) THEN RAISE EXCEPTION 'evaluator direct write privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) WHERE has_schema_privilege(roles.name,'eval','USAGE,CREATE'))
 OR EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) WHERE n.nspname='eval' AND c.relkind IN ('r','p') AND (has_table_privilege(roles.name,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege(roles.name,c.oid,'SELECT,INSERT,UPDATE'))) THEN RAISE EXCEPTION 'reference data leaked to source principal' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_roles WHERE rolname IN ('corpus_sem_writer','corpus_sem_reader') AND (rolsuper OR rolcreaterole OR rolbypassrls)) OR pg_has_role('corpus_sem_writer','corpus_sem_publisher','MEMBER') OR pg_has_role('corpus_sem_reader','corpus_sem_publisher','MEMBER') OR pg_has_role('corpus_sem_writer',owner_name,'MEMBER') OR pg_has_role('corpus_sem_reader',owner_name,'MEMBER') THEN RAISE EXCEPTION 'unrestricted application principal' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) CROSS JOIN (VALUES('sem'),('data'),('ops'),('kb')) schemas(name) WHERE has_schema_privilege(roles.name,schemas.name,'CREATE')) THEN RAISE EXCEPTION 'application schema mutation privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) WHERE n.nspname IN ('sem','data') AND c.relkind IN ('r','p') AND (has_table_privilege(roles.name,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege(roles.name,c.oid,'INSERT,UPDATE'))) THEN RAISE EXCEPTION 'application direct semantic write privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) CROSS JOIN (VALUES('data.publish_contract_batch(text,text,text,bytea)'),('data.validate_state(text,text)'),('data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint)'),('data.finish_pre_contract_evaluation(bigint,text,text)')) kernels(signature) WHERE has_function_privilege(roles.name,kernels.signature,'EXECUTE')) THEN RAISE EXCEPTION 'application private kernel privilege' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'checks') item
 LEFT JOIN pg_constraint c ON c.conrelid=to_regclass(item.value->>'relation') AND c.conname=item.value->>'name'
 WHERE c.oid IS NULL OR NOT c.convalidated OR pg_get_constraintdef(c.oid) IS DISTINCT FROM item.value->>'definition' LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native CHECK expression differs: %',spec->>'relation' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='eval' AND c.relkind IN ('r','p') AND has_table_privilege('corpus_sem_admitter',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')) THEN RAISE EXCEPTION 'admission principal has reference access' USING ERRCODE='42501'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader'),('corpus_sem_admitter'),('corpus_sem_evaluator')) principal(name)
  WHERE has_database_privilege(principal.name,current_database(),'TEMP') OR pg_has_role(principal.name,'corpus_sem_publisher','MEMBER') OR pg_has_role(principal.name,owner_name,'MEMBER')) THEN
  RAISE EXCEPTION 'privileged runtime principal' USING ERRCODE='42501'; END IF;
 -- {record_native_admission}
END
$admission$;
ALTER FUNCTION data.require_execution_release(text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.require_execution_release(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;

GRANT EXECUTE ON FUNCTION data.require_execution_release(text),data.execution_contract_descriptor() TO corpus_sem_admitter;
