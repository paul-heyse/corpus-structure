SET LOCAL ROLE corpus_sem_publisher;

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

CREATE OR REPLACE FUNCTION sem.publish_release_archive(payload jsonb) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE r text; digest text; relation_name text; actual jsonb; expected jsonb; replay boolean;
 names constant text[]:=ARRAY['release','input','artifact','registry_row','class_definition','property_definition','vocabulary_member','metric_definition','execution_operation','scientific_decision_rule','class_hierarchy','property_applicability','identity_slot','conditional_rule','execution_transition','operation_effect','conditional_atom','execution_edge','transition_effect','operation_property_role'];
BEGIN
 PERFORM sem.require_admission_caller();
 IF jsonb_typeof(payload)<>'object' OR ARRAY(SELECT jsonb_object_keys(payload) ORDER BY 1)
   IS DISTINCT FROM ARRAY(SELECT unnest(names) ORDER BY 1) THEN
  RAISE EXCEPTION 'archive relation set differs' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(payload->'release')<>1 THEN RAISE EXCEPTION 'one complete release required'; END IF;
 r:=payload->'release'->0->>'release_id'; digest:=payload->'release'->0->>'content_digest';
 IF r IS NULL OR digest IS NULL THEN RAISE EXCEPTION 'archive identity missing'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(r,0));
 replay:=EXISTS(SELECT FROM sem.release_finalization WHERE release_id=r);
 FOREACH relation_name IN ARRAY names LOOP
  IF jsonb_typeof(payload->relation_name)<>'array' THEN RAISE EXCEPTION 'archive rows must be arrays'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(payload->relation_name) row WHERE row->>'release_id' IS DISTINCT FROM r) THEN
   RAISE EXCEPTION 'archive row has wrong release' USING ERRCODE='23514'; END IF;
  EXECUTE format('SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),''[]''::jsonb) FROM jsonb_populate_recordset(NULL::sem.%I,$1) t',relation_name)
   INTO expected USING payload->relation_name;
  IF NOT replay THEN
   EXECUTE format('INSERT INTO sem.%I SELECT * FROM jsonb_populate_recordset(NULL::sem.%I,$1)',relation_name,relation_name) USING payload->relation_name;
  END IF;
  EXECUTE format('SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),''[]''::jsonb) FROM sem.%I t WHERE release_id=$1',relation_name)
   INTO actual USING r;
  IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archive replay differs: %',relation_name USING ERRCODE='23505'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM sem.release WHERE release_id=r AND encode(sha256(prepared_bytes),'hex')<>content_digest)
 OR EXISTS(SELECT FROM sem.input WHERE release_id=r AND encode(sha256(content),'hex')<>content_digest)
 OR EXISTS(SELECT FROM sem.artifact WHERE release_id=r AND encode(sha256(content),'hex')<>content_digest) THEN
  RAISE EXCEPTION 'archive content digest differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.release WHERE release_id=r AND (release_id<>'release:'||encode(sha256(manifest_bytes),'hex') OR convert_from(prepared_bytes,'UTF8')::jsonb->'products'->>'release_id' IS DISTINCT FROM release_id)) THEN RAISE EXCEPTION 'archive manifest identity differs' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_archive_bytes(r);
 PERFORM sem.require_execution_projection(r);
 IF NOT replay THEN INSERT INTO sem.release_finalization VALUES(r,digest); END IF;
 RETURN r;
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

CREATE OR REPLACE FUNCTION data.begin_inference_workspace(r text,z text,revision bigint,snapshot text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 IF current_setting('transaction_isolation') NOT IN ('repeatable read','serializable') OR nullif(snapshot,'') IS NULL THEN
  RAISE EXCEPTION 'inference requires bound repeatable snapshot'; END IF;
 IF NOT EXISTS(SELECT FROM data.realization WHERE release_id=r AND realization_id=z AND data_revision=revision) THEN
  RAISE EXCEPTION 'inference source revision differs' USING ERRCODE='P0004'; END IF;
 IF to_regclass('pg_temp.semantic_inference_work') IS NOT NULL OR to_regclass('pg_temp.semantic_inference_binding') IS NOT NULL THEN
  RAISE EXCEPTION 'preexisting inference workspace'; END IF;
 CREATE TEMP TABLE semantic_inference_binding(release_id text,realization_id text,data_revision bigint,snapshot text) ON COMMIT DROP;
 INSERT INTO pg_temp.semantic_inference_binding VALUES(r,z,revision,snapshot);
 CREATE TEMP TABLE semantic_inference_work(subject text NOT NULL,predicate text NOT NULL,object text NOT NULL,context text,qualification text,context_key text NOT NULL,PRIMARY KEY(subject,predicate,object,context_key)) ON COMMIT DROP;
 GRANT SELECT,INSERT ON pg_temp.semantic_inference_work TO corpus_sem_writer;
 GRANT UPDATE(qualification) ON pg_temp.semantic_inference_work TO corpus_sem_writer;
END
$body$;

CREATE OR REPLACE FUNCTION data.end_inference_workspace(r text,z text,revision bigint,snapshot text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['semantic_inference_work','semantic_inference_binding'] LOOP
  IF NOT EXISTS(SELECT FROM pg_class WHERE relnamespace=pg_my_temp_schema() AND relname=name AND relkind='r' AND relpersistence='t' AND relowner=current_user::regrole) THEN
   RAISE EXCEPTION 'untrusted inference workspace'; END IF;
 END LOOP;
 IF (SELECT array_agg(attname||':'||format_type(atttypid,atttypmod) ORDER BY attnum) FROM pg_attribute
      WHERE attrelid='pg_temp.semantic_inference_work'::regclass AND attnum>0 AND NOT attisdropped)
    IS DISTINCT FROM ARRAY['subject:text','predicate:text','object:text','context:text','qualification:text','context_key:text']
 OR (SELECT array_agg(attname||':'||format_type(atttypid,atttypmod) ORDER BY attnum) FROM pg_attribute
      WHERE attrelid='pg_temp.semantic_inference_binding'::regclass AND attnum>0 AND NOT attisdropped)
    IS DISTINCT FROM ARRAY['release_id:text','realization_id:text','data_revision:bigint','snapshot:text'] THEN
  RAISE EXCEPTION 'inference workspace shape differs'; END IF;
 IF NOT EXISTS(SELECT FROM pg_temp.semantic_inference_binding b WHERE (b.release_id,b.realization_id,b.data_revision,b.snapshot)=(r,z,revision,$4)) THEN RAISE EXCEPTION 'inference binding differs'; END IF;
 DROP TABLE pg_temp.semantic_inference_work,pg_temp.semantic_inference_binding;
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
 OR (purpose='read' AND NOT has_table_privilege(principal,'data.realization','SELECT'))
 OR (purpose='write' AND NOT has_function_privilege(principal,'data.begin_stage()','EXECUTE'))
 OR (purpose='evaluate' AND NOT has_schema_privilege(principal,'eval','USAGE'))
 OR (purpose='admit' AND NOT has_function_privilege(principal,'sem.publish_release_archive(jsonb)','EXECUTE')) THEN
  RAISE EXCEPTION 'required runtime capability unavailable' USING ERRCODE='42501'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(data.execution_contract_descriptor()->'functions') contract
  JOIN pg_proc p ON p.oid=to_regprocedure(contract->>'signature')
  WHERE has_function_privilege(principal,p.oid,'EXECUTE') IS DISTINCT FROM ((contract->'execute_roles') ? required_role)) THEN
  RAISE EXCEPTION 'runtime operation privileges differ from purpose contract' USING ERRCODE='42501'; END IF;
 IF purpose<>'evaluate'  AND EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='eval' AND c.relkind IN ('r','p') AND has_table_privilege(principal,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')) THEN
  RAISE EXCEPTION 'runtime principal has independent reference access' USING ERRCODE='42501'; END IF;
END
$body$;

CREATE OR REPLACE FUNCTION data.is_bound_statement(r text,c text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE bound text; base text; model jsonb;
BEGIN
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row
 WHERE release_id=r AND kind='effective_bindings' AND name='effective-bindings-11';
 IF model IS NOT NULL THEN bound:=model->'statement'->>'class_iri';
 ELSE
  SELECT target.class_id INTO bound FROM sem.class_definition binding
  JOIN sem.property_applicability field ON field.release_id=binding.release_id AND field.class_id=binding.class_id
  JOIN sem.class_definition target ON target.release_id=field.release_id AND target.name=field.range_name
  WHERE binding.release_id=r AND binding.name='AgentStatementBinding' AND field.constraints->>'name'='statement'
   AND NOT field.multivalued AND NOT COALESCE((field.constraints->>'inlined')::boolean,false);
  IF bound IS NULL AND EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-1')
     AND NOT EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name='AgentStatementBinding') THEN
   SELECT class_id INTO bound FROM sem.class_definition WHERE release_id=r AND name='SourceStatement';
  END IF;
  IF bound IS NULL THEN RAISE EXCEPTION 'missing archived statement binding' USING ERRCODE='23514'; END IF;
  -- Historical archives have no v11 effective product. Validate their explicitly
  -- supported protocol instead of accepting any class named by a legacy binding.
  SELECT class_id INTO base FROM sem.class_definition WHERE release_id=r AND name='SourceStatement';
  IF base IS NULL OR NOT (bound=base OR EXISTS(SELECT FROM sem.class_hierarchy
      WHERE release_id=r AND class_id=bound AND ancestor_id=base))
     OR NOT EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND class_id=bound AND NOT abstract)
     OR NOT EXISTS(SELECT FROM sem.property_applicability p WHERE p.release_id=r AND p.class_id=bound
       AND p.constraints->>'name'='id' AND NOT p.multivalued
       AND NOT COALESCE((p.constraints->>'inlined')::boolean,false)
       AND p.constraints->>'native_range' IN ('string','uri','uriorcurie')
       AND EXISTS(SELECT FROM sem.identity_slot i WHERE i.release_id=r AND i.class_id=bound
           AND i.group_id='0' AND i.position=0 AND i.property_id=p.property_id)
       AND (SELECT count(*) FROM sem.identity_slot i WHERE i.release_id=r AND i.class_id=bound AND i.group_id='0')=1)
     OR NOT EXISTS(SELECT FROM sem.property_applicability p WHERE p.release_id=r AND p.class_id=bound
       AND p.constraints->>'name'='locator' AND p.required AND NOT p.multivalued
       AND NOT COALESCE((p.constraints->>'inlined')::boolean,false)
       AND p.constraints->>'native_range' IN ('string','uri','uriorcurie'))
     OR NOT EXISTS(SELECT FROM sem.property_applicability p WHERE p.release_id=r AND p.class_id=bound
       AND p.constraints->>'name'='statement_kind' AND NOT p.multivalued
       AND NOT COALESCE((p.constraints->>'inlined')::boolean,false)
       AND EXISTS(SELECT FROM sem.vocabulary_member v WHERE v.release_id=r AND v.vocabulary_id=p.range_name)) THEN
   RAISE EXCEPTION 'invalid archived source-statement protocol; derive a supported bound release' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN bound IS NOT NULL AND EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND class_id=bound)
  AND (c=bound OR EXISTS(SELECT FROM sem.class_hierarchy WHERE release_id=r AND class_id=c AND ancestor_id=bound));
END
$body$;

CREATE OR REPLACE FUNCTION data.check_evidence_source() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE observation kb.observation; ev data.evidence; span kb.span; method_name text;
 operation_version text; uri text; rendition_key text; matched boolean; locator_matched boolean; synthesis jsonb;
BEGIN
 SELECT * INTO STRICT observation FROM kb.observation WHERE id=NEW.observation_id;
 IF observation.release_id<>NEW.release_id OR observation.rendition_id IS DISTINCT FROM NEW.rendition_id THEN
  RAISE EXCEPTION 'evidence source differs from bound observation'; END IF;
 SELECT m.name,m.version,d.source_uri,r.key INTO STRICT method_name,operation_version,uri,rendition_key
  FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id
  JOIN ops.method m ON m.id=c.method_id JOIN kb.rendition r ON r.id=NEW.rendition_id
  JOIN kb.document d ON d.id=r.document_id WHERE t.id=observation.task_id;
 SELECT * INTO STRICT ev FROM data.evidence WHERE evidence_id=NEW.evidence_id
  AND release_id=NEW.release_id AND realization_id=NEW.realization_id;
 IF ev.source_uri<>uri OR ev.provider<>method_name OR ev.operation_version<>operation_version THEN
  RAISE EXCEPTION 'evidence provider/source differs from bound observation'; END IF;
 IF NEW.span_id IS NULL THEN
  IF observation.span_id IS NOT NULL THEN RAISE EXCEPTION 'evidence omitted bound source span'; END IF;
  IF ev.locator<>'observation:'||observation.observation_key THEN RAISE EXCEPTION 'evidence locator differs from bound observation'; END IF;
  RETURN NEW;
 END IF;
 IF observation.span_id IS NOT NULL THEN
  IF observation.span_id<>NEW.span_id THEN RAISE EXCEPTION 'evidence span differs from bound observation'; END IF;
  SELECT * INTO STRICT span FROM kb.span WHERE id=NEW.span_id;
  IF ev.locator<>'rendition:'||rendition_key||':span:'||span.start_offset||':'||span.end_offset THEN RAISE EXCEPTION 'evidence locator differs from bound span'; END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO STRICT span FROM kb.span WHERE id=NEW.span_id AND rendition_id=NEW.rendition_id;
 locator_matched:=ev.locator='rendition:'||rendition_key||':span:'||span.start_offset||':'||span.end_offset;
 matched:=false;
 IF observation.payload_definition='AgentStoredBatch' THEN
  SELECT EXISTS(SELECT FROM jsonb_array_elements(
      COALESCE(observation.payload->'claims','[]'::jsonb)||COALESCE(observation.payload->'unsupported','[]'::jsonb)||COALESCE(observation.payload->'identity_exclusions','[]'::jsonb)) item
      CROSS JOIN LATERAL jsonb_array_elements(item->'evidence') citation
      WHERE citation->>'outcome'='located' AND (citation->>'start')::bigint=span.start_offset
       AND (citation->>'end')::bigint=span.end_offset AND (CASE WHEN locator_matched THEN true ELSE ev.locator::jsonb=jsonb_build_object('locator',citation->'locator','start',span.start_offset,'end',span.end_offset,'role',citation->'role') END)) INTO matched;
 ELSIF observation.payload_definition='SourceObservation' AND observation.kind='author_markup' THEN
  synthesis:=data.report_field(observation.payload->'payload','synthesize');
  SELECT EXISTS(SELECT FROM jsonb_array_elements(data.report_field(synthesis,'evidence')->'items') citation
    WHERE (data.report_field(citation,'start')->>'integer')::bigint=span.start_offset
      AND (data.report_field(citation,'end')->>'integer')::bigint=span.end_offset AND locator_matched) INTO matched;
 END IF;
 IF NOT matched THEN RAISE EXCEPTION 'evidence span is not a located citation in bound source report'; END IF;
 RETURN NEW;
END $fn$;

CREATE OR REPLACE FUNCTION data.end_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity'; END IF; DROP TABLE pg_temp.sp_entity;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity_source' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','observation_id:bigint','local_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity_source'; END IF; DROP TABLE pg_temp.sp_entity_source;
IF to_regclass('pg_temp.sp_identity_exclusion') IS NOT NULL THEN IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_identity_exclusion' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['exclusion_id:text','observation_id:bigint','local_id:text','left_kind:text','left_ref:text','right_kind:text','right_ref:text','left_entity_id:text','right_entity_id:text','reason:text','operation_id:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_identity_exclusion'; END IF; DROP TABLE pg_temp.sp_identity_exclusion; END IF;
IF to_regclass('pg_temp.sp_identity_exclusion_evidence') IS NOT NULL THEN IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_identity_exclusion_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['exclusion_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_identity_exclusion_evidence'; END IF; DROP TABLE pg_temp.sp_identity_exclusion_evidence; END IF;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership'; END IF; DROP TABLE pg_temp.sp_membership;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_typed_value' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['value_id:text','kind:text','text_value:text','integer_value:numeric','numeric_value:numeric','decimal_lexical:text','boolean_value:boolean','entity_id:text','language:text','datatype:text','opaque_payload:jsonb']) THEN RAISE EXCEPTION 'untrusted staging relation sp_typed_value'; END IF; DROP TABLE pg_temp.sp_typed_value;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_value_role' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['parent_value_id:text','role:text','position:bigint','child_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_value_role'; END IF; DROP TABLE pg_temp.sp_value_role;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','subject_id:text','property_id:text','object_value_id:text','qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact'; END IF; DROP TABLE pg_temp.sp_fact;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','fact_id:text','source:text','item:text','report_object_value_id:text','report_qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence'; END IF; DROP TABLE pg_temp.sp_occurrence;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','occurrence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_support'; END IF; DROP TABLE pg_temp.sp_support;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_selection' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','selected:boolean']) THEN RAISE EXCEPTION 'untrusted staging relation sp_selection'; END IF; DROP TABLE pg_temp.sp_selection;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','source_uri:text','locator:text','provider:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence'; END IF; DROP TABLE pg_temp.sp_evidence;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_evidence'; END IF; DROP TABLE pg_temp.sp_occurrence_evidence;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_context' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','statement_entity_id:text','statement_role:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_context'; END IF; DROP TABLE pg_temp.sp_occurrence_context;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_evidence_role' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','evidence_id:text','role:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_evidence_role'; END IF; DROP TABLE pg_temp.sp_occurrence_evidence_role;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership_support'; END IF; DROP TABLE pg_temp.sp_membership_support;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','conclusion_fact_id:text','rule:text','rule_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation'; END IF; DROP TABLE pg_temp.sp_derivation;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation_premise' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','position:bigint','premise_fact_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation_premise'; END IF; DROP TABLE pg_temp.sp_derivation_premise;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_coverage' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['coverage_id:text','family:text','scope:text','outcome:text','reason:text','source_outcome:text','required_capability:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_coverage'; END IF; DROP TABLE pg_temp.sp_coverage;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_establishment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_establishment'; END IF; DROP TABLE pg_temp.sp_occurrence_establishment;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence_source' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','observation_id:bigint','rendition_id:bigint','span_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence_source'; END IF; DROP TABLE pg_temp.sp_evidence_source;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_assessment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['assessment_id:text','operation_id:text','operation_version:text','outcome:text','fact_id:text','occurrence_id:text','confidence:numeric','reason:text','uncertainty:text','counterpart_fact_id:text','counterpart_occurrence_id:text','context_value_id:text','comparison_tier:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_assessment'; END IF; DROP TABLE pg_temp.sp_assessment;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','input_realization_id:text','input_data_revision:bigint','input_entity_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity_input'; END IF; DROP TABLE pg_temp.sp_entity_input;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','input_realization_id:text','input_data_revision:bigint','input_fact_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact_input'; END IF; DROP TABLE pg_temp.sp_fact_input;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_alternative_group' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['group_id:text','reason:text','operation_id:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_alternative_group'; END IF; DROP TABLE pg_temp.sp_alternative_group;
IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_alternative_member' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['group_id:text','fact_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_alternative_member'; END IF; DROP TABLE pg_temp.sp_alternative_member;
END
$body$;

CREATE OR REPLACE FUNCTION data.validate_occurrence_context(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE o data.occurrence; context data.occurrence_context; observation kb.observation;
 edge data.occurrence_evidence; citation_role data.occurrence_evidence_role;
 source data.evidence_source; claim jsonb; statement jsonb; expected_statement text;
 expected_role text; source_rendition_key text; synthesis jsonb;
BEGIN
 IF EXISTS(SELECT FROM data.occurrence_context c WHERE c.release_id=r AND c.realization_id=z
   AND c.statement_role IS NOT NULL AND NOT EXISTS(SELECT FROM sem.vocabulary_member v
     WHERE v.release_id=r AND v.vocabulary_id='StatementRole' AND v.value=c.statement_role)) THEN
  RAISE EXCEPTION 'undeclared occurrence statement role' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.occurrence_evidence_role c WHERE c.release_id=r AND c.realization_id=z
   AND NOT EXISTS(SELECT FROM sem.vocabulary_member v WHERE v.release_id=r
    AND v.vocabulary_id='EvidenceRole' AND v.value=c.role)) THEN
  RAISE EXCEPTION 'undeclared occurrence evidence role' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.occurrence_context ctx WHERE ctx.release_id=r AND ctx.realization_id=z
   AND ctx.statement_entity_id IS NOT NULL AND NOT EXISTS(
    SELECT FROM data.membership m JOIN sem.class_definition c
     ON c.release_id=m.release_id AND c.class_id=m.class_id
    WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=ctx.statement_entity_id
     AND data.is_bound_statement(r,c.class_id))) THEN
  RAISE EXCEPTION 'occurrence statement lacks SourceStatement membership' USING ERRCODE='23514'; END IF;
 FOR o IN SELECT * FROM data.occurrence WHERE release_id=r AND realization_id=z LOOP
  SELECT * INTO context FROM data.occurrence_context c WHERE c.release_id=r AND c.realization_id=z
    AND c.occurrence_id=o.occurrence_id;
  SELECT * INTO observation FROM kb.observation ob WHERE ob.release_id=r AND ob.observation_key=o.source;
  IF NOT FOUND THEN CONTINUE; END IF;
  IF observation.payload_definition='AgentStoredBatch' AND o.item ~ '^claims/[0-9]+$' THEN
   claim:=observation.payload->'claims'->(split_part(o.item,'/',2)::integer);
   IF claim IS NULL THEN RAISE EXCEPTION 'occurrence claim is outside bound source report'; END IF;
   expected_statement:=NULL;
   expected_role:=claim->>'statement_role';
   IF claim->>'statement' IS NOT NULL THEN
    SELECT value INTO STRICT statement FROM jsonb_array_elements(observation.payload->'statements')
     WHERE value->>'id'=claim->>'statement';
    IF statement->>'kind'<>'outside' THEN
    IF EXISTS(SELECT FROM ops.source_frame WHERE task_id=observation.task_id) AND NOT EXISTS(
       SELECT FROM ops.source_frame f JOIN ops.task t ON t.id=f.task_id WHERE f.task_id=observation.task_id AND f.packet_hash=t.packet_hash
        AND f.unit_ref=observation.payload->>'unit_ref' AND f.rendition_id=observation.rendition_id) THEN
     RAISE EXCEPTION 'statement report differs from its immutable source frame' USING ERRCODE='23514'; END IF;
    SELECT key INTO STRICT source_rendition_key FROM kb.rendition WHERE id=observation.rendition_id;
    expected_statement:='entity:'||encode(sha256(convert_to(data.canonical_json(
     jsonb_build_array(r,z,'source-statement',source_rendition_key,ops.source_statement_locator(observation.task_id,statement->>'anchor'))),'UTF8')),'hex');
    END IF;
   END IF;
   IF (context.statement_entity_id,context.statement_role) IS DISTINCT FROM
      (expected_statement,expected_role) THEN
    RAISE EXCEPTION 'occurrence statement context differs from bound source claim' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM jsonb_array_elements(claim->'evidence') WITH ORDINALITY citation(value,position)
     WHERE citation.value->>'outcome'='located' AND citation.value->>'role' IS NOT NULL
      AND NOT EXISTS(SELECT FROM data.occurrence_evidence_role role
       WHERE role.release_id=r AND role.realization_id=z AND role.occurrence_id=o.occurrence_id
        AND role.role=citation.value->>'role'
        AND role.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
          o.source,'claims',split_part(o.item,'/',2)::bigint,citation.position-1,citation.value)),'UTF8')),'hex'))) THEN
    RAISE EXCEPTION 'occurrence citation role differs from bound source citation' USING ERRCODE='23514'; END IF;
  ELSIF context.occurrence_id IS NOT NULL THEN
   RAISE EXCEPTION 'occurrence context has no declared source claim' USING ERRCODE='23514';
  END IF;
 END LOOP;
 FOR edge IN SELECT * FROM data.occurrence_evidence WHERE release_id=r AND realization_id=z LOOP
  SELECT * INTO citation_role FROM data.occurrence_evidence_role c
   WHERE c.release_id=r AND c.realization_id=z AND c.occurrence_id=edge.occurrence_id
    AND c.evidence_id=edge.evidence_id;
  SELECT * INTO source FROM data.evidence_source es
   WHERE es.release_id=r AND es.realization_id=z AND es.evidence_id=edge.evidence_id;
  SELECT * INTO STRICT o FROM data.occurrence occurrence WHERE occurrence.release_id=r AND occurrence.realization_id=z
   AND occurrence.occurrence_id=edge.occurrence_id;
  SELECT * INTO observation FROM kb.observation ob WHERE ob.release_id=r AND ob.observation_key=o.source;
  IF NOT FOUND THEN CONTINUE; END IF;
  IF source.observation_id IS NOT NULL AND source.observation_id<>observation.id THEN
   RAISE EXCEPTION 'occurrence citation belongs to another source report' USING ERRCODE='23514'; END IF;
  expected_role:=NULL;
  IF observation.payload_definition='AgentStoredBatch' THEN
   SELECT citation.value->>'role' INTO expected_role
    FROM jsonb_array_elements(observation.payload->'claims') WITH ORDINALITY candidate(value,position)
    CROSS JOIN LATERAL jsonb_array_elements(candidate.value->'evidence') WITH ORDINALITY citation(value,position)
    WHERE citation.value->>'outcome'='located'
     AND (o.item !~ '^claims/[0-9]+$' OR candidate.position-1=split_part(o.item,'/',2)::integer)
     AND edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,'claims',candidate.position-1,citation.position-1,citation.value)),'UTF8')),'hex');
   IF NOT FOUND AND o.item LIKE 'entities/%/attributes/%' THEN
    SELECT citation.value->>'role' INTO expected_role
    FROM jsonb_array_elements(coalesce(observation.payload->'identity_exclusions','[]')) candidate
    CROSS JOIN LATERAL jsonb_array_elements(candidate->'evidence') WITH ORDINALITY citation(value,position)
    JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.fact_id=o.fact_id
    JOIN data.entity_source src ON src.release_id=r AND src.realization_id=z AND src.observation_id=observation.id AND src.entity_id=f.subject_id
    WHERE starts_with(o.item,'entities/'||src.local_id||'/attributes/')
     AND substring(o.item FROM length('entities/'||src.local_id||'/attributes/')+1) ~ '^[0-9]+$'
     AND ((candidate->'left'->>'kind'='local' AND candidate->'left'->>'target'=src.local_id)
       OR (candidate->'right'->>'kind'='local' AND candidate->'right'->>'target'=src.local_id))
     AND citation.value->>'outcome'='located'
     AND EXISTS(SELECT FROM jsonb_array_elements(candidate->'evidence') primary_citation WHERE primary_citation->>'outcome'='located' AND primary_citation->>'role'='primary')
     AND edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,'identity_exclusions',candidate->>'id',citation.position-1,citation.value)),'UTF8')),'hex');
   END IF;
   IF expected_role IS NULL THEN RAISE EXCEPTION 'occurrence citation is outside bound source claim' USING ERRCODE='23514'; END IF;
  ELSIF observation.payload_definition='SourceObservation' AND observation.kind='author_markup' THEN
   synthesis:=data.report_field(observation.payload->'payload','synthesize');
   SELECT data.report_field(citation.value,'role')->>'text' INTO expected_role
    FROM jsonb_array_elements(data.report_field(synthesis,'evidence')->'items') WITH ORDINALITY citation(value,position)
    WHERE edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,citation.position-1,
       (data.report_field(citation.value,'start')->>'integer')::bigint,
       (data.report_field(citation.value,'end')->>'integer')::bigint)),'UTF8')),'hex');
   IF NOT FOUND THEN RAISE EXCEPTION 'occurrence citation is outside bound source synthesis' USING ERRCODE='23514'; END IF;
  END IF;
  IF citation_role.role IS DISTINCT FROM expected_role THEN
   RAISE EXCEPTION 'occurrence citation role differs from bound source citation' USING ERRCODE='23514'; END IF;
 END LOOP;
END $fn$;

CREATE OR REPLACE FUNCTION sem.select_completed_result(p text,r bigint,g bigint) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 PERFORM sem.require_admission_caller(); RETURN data.select_project_result(p,r,g); END
$body$;

REVOKE ALL ON FUNCTION sem.refuse_immutable_mutation(),sem.guard_finalized_insert() FROM PUBLIC;
REVOKE ALL ON FUNCTION sem.publish_release_archive(jsonb),sem.record_deployment_admission(text,text,text,text,bytea),sem.record_sql_admission(text,text,text,text,bytea),sem.activate_release(text,text,text,bigint),sem.select_completed_result(text,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sem.publish_release_archive(jsonb),sem.record_deployment_admission(text,text,text,text,bytea),sem.record_sql_admission(text,text,text,text,bytea),sem.activate_release(text,text,text,bigint),sem.select_completed_result(text,bigint,bigint) TO corpus_sem_admitter;
REVOKE ALL ON FUNCTION data.begin_inference_workspace(text,text,bigint,text),data.end_inference_workspace(text,text,bigint,text),data.is_bound_statement(text,text),data.require_runtime_principal(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.begin_inference_workspace(text,text,bigint,text),data.end_inference_workspace(text,text,bigint,text) TO corpus_sem_writer;
GRANT EXECUTE ON FUNCTION data.require_runtime_principal(text) TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator,corpus_sem_admitter;
GRANT EXECUTE ON FUNCTION data.is_bound_statement(text,text) TO corpus_sem_writer,corpus_sem_reader;
GRANT USAGE ON SCHEMA sem,data,ops TO corpus_sem_admitter;
GRANT SELECT ON ALL TABLES IN SCHEMA sem TO corpus_sem_admitter;
GRANT SELECT ON data.project,data.realization TO corpus_sem_admitter;
GRANT SELECT ON ALL TABLES IN SCHEMA ops TO corpus_sem_admitter;
GRANT SELECT,INSERT ON ALL TABLES IN SCHEMA sem TO corpus_sem_publisher;
GRANT SELECT ON sem.release_finalization,sem.deployment_admission,sem.physical_contract TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION sem.require_archive_bytes(r text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE archived sem.release; document jsonb; manifest jsonb; expected jsonb; actual jsonb; kind text;
BEGIN
 SELECT * INTO STRICT archived FROM sem.release WHERE release_id=r;
 document:=convert_from(archived.prepared_bytes,'UTF8')::jsonb;
 manifest:=convert_from(archived.manifest_bytes,'UTF8')::jsonb;
 IF archived.profile NOT IN ('semantic-1','semantic-2') OR document->>'format' NOT IN ('semantic-release-archive-1','semantic-release-archive-2','semantic-release-archive-3')
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
END
$body$;
REVOKE ALL ON FUNCTION sem.require_archive_bytes(text) FROM PUBLIC;

DO $finalize$ DECLARE r text; BEGIN
 FOR r IN SELECT release_id FROM sem.release LOOP PERFORM sem.require_archive_bytes(r);
 PERFORM sem.require_execution_projection(r); END LOOP;
 INSERT INTO sem.release_finalization SELECT release_id,content_digest FROM sem.release
 ON CONFLICT(release_id) DO NOTHING;
 IF EXISTS(SELECT FROM sem.release_finalization f JOIN sem.release s USING(release_id)
           WHERE f.content_digest IS DISTINCT FROM s.content_digest) THEN
  RAISE EXCEPTION 'finalized release digest differs from archive' USING ERRCODE='23514';
 END IF;
END $finalize$;

CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON sem.execution_operation FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
CREATE TRIGGER release_finalized BEFORE INSERT ON sem.execution_operation FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();
CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON sem.execution_transition FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
CREATE TRIGGER release_finalized BEFORE INSERT ON sem.execution_transition FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();
CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON sem.execution_edge FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
CREATE TRIGGER release_finalized BEFORE INSERT ON sem.execution_edge FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();
CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON sem.operation_effect FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
CREATE TRIGGER release_finalized BEFORE INSERT ON sem.operation_effect FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();
CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON sem.transition_effect FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
CREATE TRIGGER release_finalized BEFORE INSERT ON sem.transition_effect FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();
CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON sem.operation_property_role FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
CREATE TRIGGER release_finalized BEFORE INSERT ON sem.operation_property_role FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();
CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON sem.scientific_decision_rule FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
CREATE TRIGGER release_finalized BEFORE INSERT ON sem.scientific_decision_rule FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();

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
CREATE OR REPLACE FUNCTION data.guard_float_codec() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 IF NEW.kind='float' THEN PERFORM data.require_float_lexical(NEW.text_value); END IF;
 RETURN NEW;
END
$body$;
REVOKE ALL ON FUNCTION data.require_float_lexical(text),data.guard_float_codec() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.require_float_lexical(text) TO corpus_sem_reader,corpus_sem_writer;

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
REVOKE ALL ON FUNCTION sem.require_admission_caller() FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.validate_pre_inference_state(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE a record; x record; n bigint; primitive text; lexical text; value_count bigint; accepted_values text[]; enforce boolean;
BEGIN

 -- Meaning of unstaged admitted graphs is established once: value rows/child closure and
 -- release definitions are immutable. Cumulative state checks below remain unchanged.
 IF to_regclass('pg_temp.sp_typed_value') IS NULL THEN
  FOR primitive IN SELECT value_id FROM data.typed_value WHERE release_id=r AND realization_id=z LOOP
   PERFORM data.value_meaning(r,z,primitive);
  END LOOP;
 ELSE
  IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_typed_value' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regrole AND (SELECT array_agg(stage_attr.attname||':'||format_type(stage_attr.atttypid,stage_attr.atttypmod) ORDER BY stage_attr.attnum) FROM pg_attribute stage_attr WHERE stage_attr.attrelid=c.oid AND stage_attr.attnum>0 AND NOT stage_attr.attisdropped)=ARRAY['value_id:text','kind:text','text_value:text','integer_value:numeric','numeric_value:numeric','decimal_lexical:text','boolean_value:boolean','entity_id:text','language:text','datatype:text','opaque_payload:jsonb']) THEN RAISE EXCEPTION 'untrusted typed-value staging'; END IF;
  FOR primitive IN SELECT DISTINCT value_id FROM pg_temp.sp_typed_value LOOP
   PERFORM data.value_meaning(r,z,primitive);
  END LOOP;
 END IF;
 IF EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z AND (m.establishment='' OR NOT EXISTS(SELECT FROM data.membership_support ms WHERE (ms.release_id,ms.realization_id,ms.entity_id,ms.class_id)=(m.release_id,m.realization_id,m.entity_id,m.class_id)))) THEN RAISE EXCEPTION 'membership requires establishment and support' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.derivation d LEFT JOIN data.derivation_premise dp ON (dp.release_id,dp.realization_id,dp.derivation_id)=(d.release_id,d.realization_id,d.derivation_id) WHERE d.release_id=r AND d.realization_id=z GROUP BY d.derivation_id HAVING count(dp.position)=0 OR min(dp.position)<>0 OR max(dp.position)<>count(dp.position)-1) THEN RAISE EXCEPTION 'derivation requires ordered premises' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND NOT EXISTS(SELECT FROM data.typed_value v JOIN sem.class_definition c ON c.release_id=r AND c.class_id=v.datatype AND (c.name='Qualification' OR EXISTS(SELECT FROM sem.class_hierarchy h JOIN sem.class_definition root ON root.release_id=h.release_id AND root.class_id=h.ancestor_id AND root.name='Qualification' WHERE h.release_id=r AND h.class_id=c.class_id)) WHERE v.release_id=r AND v.realization_id=z AND v.value_id=f.qualification_value_id)) THEN RAISE EXCEPTION 'fact requires typed qualification' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.membership m JOIN sem.class_definition c ON c.release_id=m.release_id AND c.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND c.abstract) THEN RAISE EXCEPTION 'direct membership of abstract class' USING ERRCODE='23514'; END IF;
 WITH RECURSIVE accepted(v) AS (SELECT root.v FROM data.fact f JOIN data.selection s ON (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id) CROSS JOIN LATERAL(VALUES (f.object_value_id),(f.qualification_value_id)) root(v) WHERE f.release_id=r AND f.realization_id=z AND root.v IS NOT NULL UNION SELECT vr.child_value_id FROM data.value_role vr JOIN accepted ac ON ac.v=vr.parent_value_id WHERE vr.release_id=r AND vr.realization_id=z) SELECT array_agg(v) INTO accepted_values FROM accepted;
 -- Every value is interpreted, including disconnected nested nodes. No caller digest is trusted.
 FOR x IN SELECT * FROM data.typed_value WHERE release_id=r AND realization_id=z LOOP
 IF x.kind IN ('interval','expression','missing') THEN RAISE EXCEPTION 'unsupported physical value alias; use a typed record' USING ERRCODE='23514'; END IF;
 IF x.datatype IS NOT NULL AND x.kind NOT IN ('record','mapping') THEN RAISE EXCEPTION 'datatype is supported only on typed records or mappings' USING ERRCODE='23514'; END IF;
 IF x.opaque_payload IS NOT NULL OR x.language IS NOT NULL THEN RAISE EXCEPTION 'unsupported opaque/language value' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('string','date','datetime','float') AND x.text_value IS NULL THEN RAISE EXCEPTION 'missing scalar text' USING ERRCODE='23514'; END IF;
 IF x.kind='integer' THEN
 lexical:=COALESCE(x.text_value,x.integer_value::text);
 IF lexical IS NULL OR lexical !~ '^[+-]?[0-9]+$' OR (x.integer_value IS NOT NULL AND data.decimal_canonical(lexical)<>data.decimal_canonical(x.integer_value::text)) THEN RAISE EXCEPTION 'invalid exact integer' USING ERRCODE='23514'; END IF;
 END IF;
 IF x.kind IN ('decimal','number') THEN
 lexical:=x.decimal_lexical;
 IF lexical IS NULL OR lexical !~ '^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$' OR (x.numeric_value IS NOT NULL AND lexical::numeric<>x.numeric_value) THEN RAISE EXCEPTION 'invalid exact decimal' USING ERRCODE='23514'; END IF;
 END IF;
 IF x.kind='boolean' AND x.boolean_value IS NULL THEN RAISE EXCEPTION 'missing boolean' USING ERRCODE='23514'; END IF;
 IF x.kind='float' AND (x.text_value !~ '^-?0x(0\.0p\+0|1\.[0-9a-f]{13}p([+]0|[+][1-9][0-9]*|-[1-9][0-9]*)|0\.[0-9a-f]{13}p-1022)$' OR (x.text_value ~ '0x1\.' AND split_part(x.text_value,'p',2)::integer NOT BETWEEN -1022 AND 1023) OR x.text_value ~ '0x0\.0000000000000p-1022') THEN RAISE EXCEPTION 'invalid finite float hex' USING ERRCODE='23514'; END IF;
 IF x.kind='date' AND (x.text_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR to_char(x.text_value::date,'YYYY-MM-DD')<>x.text_value) THEN RAISE EXCEPTION 'invalid canonical date' USING ERRCODE='23514'; END IF;
 IF x.kind='datetime' AND (x.text_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{6})?\+00:00$' OR extract(year FROM x.text_value::timestamptz) NOT BETWEEN 1 AND 9999 OR to_char(x.text_value::timestamptz AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS')||CASE WHEN extract(microseconds FROM x.text_value::timestamptz)::bigint % 1000000=0 THEN '' ELSE to_char(x.text_value::timestamptz AT TIME ZONE 'UTC','.US') END||'+00:00' <> x.text_value) THEN RAISE EXCEPTION 'invalid canonical UTC datetime' USING ERRCODE='23514'; END IF;
 IF x.kind NOT IN ('sequence','mapping','record','interval','expression','missing') AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id) THEN RAISE EXCEPTION 'scalar has child roles' USING ERRCODE='23514'; END IF;
 IF x.kind='sequence' AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id GROUP BY parent_value_id HAVING min(position)<>0 OR max(position)<>count(*)-1 OR count(DISTINCT position)<>count(*) OR bool_or(role<>'item')) THEN RAISE EXCEPTION 'invalid ordered sequence' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('mapping','record','interval','expression','missing') AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id GROUP BY role HAVING count(*)<>1 OR min(position)<>0) THEN RAISE EXCEPTION 'duplicate mapping role' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('record','interval','expression','missing') OR (x.kind='mapping' AND x.datatype IS NOT NULL) THEN
 IF x.datatype IS NULL OR NOT EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND class_id=x.datatype AND NOT abstract) THEN RAISE EXCEPTION 'undeclared record class' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.value_role vr WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=x.value_id AND NOT EXISTS(SELECT FROM sem.property_applicability pa WHERE pa.release_id=r AND pa.class_id=x.datatype AND pa.constraints->>'name'=vr.role)) THEN RAISE EXCEPTION 'undeclared record property' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT * FROM sem.property_applicability WHERE release_id=r AND class_id=x.datatype LOOP
 enforce:=a.constraint_scope='shape' OR COALESCE(x.value_id=ANY(accepted_values),false);
 SELECT count(*) INTO n FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id AND role=a.constraints->>'name';
 IF enforce AND n=0 AND (a.required OR COALESCE(a.minimum_cardinality,0)>0) THEN RAISE EXCEPTION 'missing required record property %',a.property_id USING ERRCODE='23514'; END IF;
 FOR primitive IN SELECT child_value_id FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id AND role=a.constraints->>'name' LOOP
 IF a.multivalued THEN
 IF NOT EXISTS(SELECT FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=primitive AND kind=CASE WHEN a.constraints->>'collection_key' IS NULL THEN 'sequence' ELSE 'mapping' END) THEN RAISE EXCEPTION 'multivalue collection representation differs for %/% (key %)',x.datatype,a.property_id,a.constraints->>'collection_key' USING ERRCODE='23514'; END IF;
 IF a.constraints->>'collection_key' IS NOT NULL AND EXISTS(SELECT FROM data.value_role member WHERE member.release_id=r AND member.realization_id=z AND member.parent_value_id=primitive AND NOT EXISTS(SELECT FROM data.value_role kr JOIN data.typed_value kv ON (kv.release_id,kv.realization_id,kv.value_id)=(kr.release_id,kr.realization_id,kr.child_value_id) WHERE kr.release_id=r AND kr.realization_id=z AND kr.parent_value_id=member.child_value_id AND kr.role=a.constraints->>'collection_key' AND kv.kind='string' AND kv.text_value=member.role)) THEN RAISE EXCEPTION 'inlined map key differs from member identifier for %/%',x.datatype,a.property_id USING ERRCODE='23514'; END IF;
 SELECT count(*) INTO value_count FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=primitive;
 IF enforce AND (value_count<COALESCE(a.minimum_cardinality,CASE WHEN a.required THEN 1 ELSE 0 END) OR (a.maximum_cardinality IS NOT NULL AND value_count>a.maximum_cardinality)) THEN RAISE EXCEPTION 'record cardinality' USING ERRCODE='23514'; END IF;
 FOR lexical IN SELECT child_value_id FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=primitive LOOP
 PERFORM data.validate_property(r,z,lexical,COALESCE(a.constraints->>'native_range',a.range_name),CASE WHEN enforce THEN a.constraints ELSE a.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum' END);
 END LOOP;
 ELSE PERFORM data.validate_property(r,z,primitive,COALESCE(a.constraints->>'native_range',a.range_name),CASE WHEN enforce THEN a.constraints ELSE a.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum' END);
 END IF;
 END LOOP;
 END LOOP;
 END IF;
 END LOOP;
 -- Range/applicability reads include the complete admitted state plus this candidate.
 IF EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND NOT EXISTS(SELECT FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id)) THEN RAISE EXCEPTION 'fact property is not applicable to subject class' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT f.object_value_id,COALESCE(pa.constraints->>'native_range',pa.range_name) AS range_name,CASE WHEN pa.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection s WHERE (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id)) THEN pa.constraints ELSE pa.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum'-'native_minimum'-'native_maximum' END AS constraints FROM data.fact f JOIN data.membership m ON (m.release_id,m.realization_id,m.entity_id)=(f.release_id,f.realization_id,f.subject_id) JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=m.class_id AND pa.property_id=f.property_id WHERE f.release_id=r AND f.realization_id=z LOOP
 PERFORM data.validate_property(r,z,a.object_value_id,a.range_name,a.constraints);
 END LOOP;
 -- Cardinality counts semantic values, never evidence occurrences.
 FOR a IN SELECT m.entity_id,pa.* FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z LOOP
 SELECT count(DISTINCT data.canonical_json(data.value_meaning(r,z,f.object_value_id))) INTO n FROM data.fact f
 WHERE f.release_id=r AND f.realization_id=z AND f.subject_id=a.entity_id AND f.property_id=a.property_id
 AND (a.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection s WHERE (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id)));
 IF n<COALESCE(a.minimum_cardinality,CASE WHEN a.required THEN 1 ELSE 0 END) OR n>COALESCE(a.maximum_cardinality,CASE WHEN a.multivalued THEN 9223372036854775807 ELSE 1 END) THEN RAISE EXCEPTION 'property cardinality %/%',a.entity_id,a.property_id USING ERRCODE='23514'; END IF;
 END LOOP;
 -- Identity groups use each declared member, with admitted case policy and complete scope.
 IF EXISTS(
 WITH key_parts AS (
 SELECT m.entity_id,m.class_id,i.group_id,i.position,
 count(DISTINCT data.canonical_json(CASE WHEN pa.constraints->>'case_policy'='casefold' AND tv.kind='string' THEN jsonb_build_array('string',casefold(tv.text_value COLLATE pg_catalog.pg_unicode_fast)) ELSE data.value_meaning(r,z,f.object_value_id) END)) AS count_values,
 min(data.canonical_json(CASE WHEN pa.constraints->>'case_policy'='casefold' AND tv.kind='string' THEN jsonb_build_array('string',casefold(tv.text_value COLLATE pg_catalog.pg_unicode_fast)) ELSE data.value_meaning(r,z,f.object_value_id) END)) AS part
 FROM data.membership m JOIN sem.identity_slot i ON i.release_id=r AND i.class_id=m.class_id
 JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=i.class_id AND pa.property_id=i.property_id
 LEFT JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.subject_id=m.entity_id AND f.property_id=i.property_id AND (pa.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection sel WHERE (sel.release_id,sel.realization_id,sel.fact_id)=(f.release_id,f.realization_id,f.fact_id)))
 LEFT JOIN data.typed_value tv ON (tv.release_id,tv.realization_id,tv.value_id)=(f.release_id,f.realization_id,f.object_value_id)
 WHERE m.release_id=r AND m.realization_id=z GROUP BY m.entity_id,m.class_id,i.group_id,i.position),
 keys AS(SELECT entity_id,class_id,group_id,string_agg(part,',' ORDER BY position) AS value,bool_and(count_values=1) AS complete FROM key_parts GROUP BY entity_id,class_id,group_id)
 SELECT FROM keys GROUP BY class_id,group_id,value HAVING count(*)>1 OR NOT bool_and(complete)
 ) THEN RAISE EXCEPTION 'missing, multivalued or nonunique entity identity' USING ERRCODE='23514'; END IF;
END $fn$;

GRANT SELECT ON sem.execution_edge TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON sem.execution_operation TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON sem.execution_transition TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON sem.operation_effect TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON sem.operation_property_role TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON sem.scientific_decision_rule TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON sem.transition_effect TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
-- Forward derived-publication ABI. Existing intent rows retain their original identity.
SET LOCAL ROLE corpus_sem_publisher;
CREATE OR REPLACE FUNCTION data.publish_derived_batch(r text,z text,b text,p_content bytea,
 source_release text,source_realization text,source_revision bigint,source_capture text,
 operation text,projection text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE previous data.publication_intent;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'derived publication requires SERIALIZABLE'; END IF;
 SELECT * INTO previous FROM data.publication_intent WHERE (release_id,realization_id,batch_id)=(r,z,b);
 IF NOT FOUND THEN RAISE EXCEPTION 'new derived publication requires the model-bound v2 ABI' USING ERRCODE='23514'; END IF;
 IF (previous.source_release_id,previous.source_realization_id,previous.source_revision,
 previous.source_capture_id,previous.operation_id,previous.projection_id)
 IS DISTINCT FROM(source_release,source_realization,source_revision,source_capture,operation,projection) THEN
 RAISE EXCEPTION 'derived publication intent conflict' USING ERRCODE='23505'; END IF;
 RETURN data.publish_contract_batch(r,z,b,p_content);
END $fn$;

CREATE OR REPLACE FUNCTION data.publish_derived_batch_v2(r text,z text,b text,p_content bytea,
 source_release text,source_realization text,source_revision bigint,source_capture text,
 operation text,projection text,contract_id text,cut_id bigint,profile_digest text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE previous data.publication_intent; actual bigint; published bigint; binding text;
 model jsonb; op jsonb; contract jsonb; policy jsonb; expected_policy jsonb;
 profile text; expected_projection text; cut ops.input_cut; job ops.run; base jsonb;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'derived publication requires SERIALIZABLE'; END IF;
 binding:=data.canonical_json(jsonb_build_object('abi','derived-2','contract_id',contract_id,
  'projection_id',projection,'cut_id',cut_id,'profile_digest',profile_digest));
 -- Replay precedes current model, source-revision and cut-state checks.
 SELECT * INTO previous FROM data.publication_intent WHERE (release_id,realization_id,batch_id)=(r,z,b);
 IF FOUND THEN
  IF (previous.source_release_id,previous.source_realization_id,previous.source_revision,
   previous.source_capture_id,previous.operation_id,previous.projection_id)
   IS DISTINCT FROM(source_release,source_realization,source_revision,source_capture,operation,binding) THEN
   RAISE EXCEPTION 'derived publication intent conflict' USING ERRCODE='23505'; END IF;
  RETURN data.publish_contract_batch(r,z,b,p_content);
 END IF;
 IF EXISTS(SELECT FROM data.batch WHERE (release_id,realization_id,batch_id)=(r,z,b)) THEN
  RAISE EXCEPTION 'append receipt cannot become snapshot-derived' USING ERRCODE='23505'; END IF;
 IF r IS DISTINCT FROM source_release OR source_capture IS NULL OR source_capture='' THEN
  RAISE EXCEPTION 'derived source release/capture differs' USING ERRCODE='23514'; END IF;
 PERFORM data.require_execution_release(r);
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row
  WHERE release_id=r AND kind='execution_model';
 IF model IS NULL THEN
  SELECT data.execution_contract_descriptor()->'base_derived_protocol' INTO base;
  IF NOT EXISTS(SELECT FROM sem.release released WHERE released.release_id=r AND released.profile='semantic-1') OR
   base IS DISTINCT FROM '{"operation":"publish_inference","projection":"accepted","universe":"eligible_positive_accepted","values":"exact","target":"same_realization"}'::jsonb OR
   operation IS DISTINCT FROM base->>'operation' OR contract_id IS DISTINCT FROM base->>'projection' THEN
   RAISE EXCEPTION 'release has no admitted derived operation/projection' USING ERRCODE='23514'; END IF;
 ELSE
  SELECT value INTO op FROM jsonb_array_elements(model->'operations') WHERE value->>'id'=operation;
  SELECT value INTO contract FROM jsonb_array_elements(model->'projections') WHERE value->>'id'=contract_id;
  IF op IS NULL OR contract IS NULL OR NOT (op->'projections' ? contract_id) THEN
   RAISE EXCEPTION 'operation does not permit derived projection' USING ERRCODE='23514'; END IF;
  policy:=contract->'analytical_policy';
  expected_policy:=jsonb_build_object('input_kind',contract_id,
   'universe',CASE contract_id WHEN 'candidate' THEN 'cut_candidates' WHEN 'accepted' THEN 'eligible_positive_accepted' END,
   'collections','positions_and_multiplicity','completeness','declared_universe',
   'values',CASE contract_id WHEN 'accepted' THEN 'exact' ELSE 'exact_with_separate_bounded_projection' END,
   'arithmetic_profile',CASE contract_id WHEN 'candidate' THEN 'analytical-profile.json' END);
  IF policy IS DISTINCT FROM expected_policy OR contract->'omissions' IS DISTINCT FROM
    (CASE contract_id WHEN 'candidate' THEN '[]'::jsonb ELSE '["negative_hypothetical_premises"]'::jsonb END) OR
    (contract->>'implementation',contract->>'lifetime') IS DISTINCT FROM
    (CASE contract_id WHEN 'candidate' THEN 'analysis' ELSE 'query' END,CASE contract_id WHEN 'candidate' THEN 'scope' ELSE 'snapshot' END) THEN
   RAISE EXCEPTION 'derived analytical projection policy is unsupported' USING ERRCODE='23514'; END IF;
 END IF;
 IF operation='evaluate' AND contract_id='candidate' THEN
  IF cut_id IS NULL OR cut_id<1 OR profile_digest IS NULL OR projection IS NULL THEN
   RAISE EXCEPTION 'candidate projection requires bound cut/profile' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT cut FROM ops.input_cut WHERE id=cut_id;
  SELECT * INTO STRICT job FROM ops.run WHERE id=cut.run_id FOR UPDATE;
  IF NOT cut.final OR NOT job.sealed OR job.status NOT IN ('consolidating','finished') OR
   (job.release_id,job.input_realization_id,job.input_revision,cut.source_revision,job.result_realization_id)
   IS DISTINCT FROM(r,source_realization,source_revision,source_revision,z) OR
   z=source_realization OR source_capture IS DISTINCT FROM 'cut:'||cut_id::text OR
   NOT EXISTS(SELECT FROM data.realization WHERE release_id=r AND realization_id=z AND project_id=job.project_id AND state='active') THEN
   RAISE EXCEPTION 'candidate source/target differs from sealed run cut' USING ERRCODE='23514'; END IF;
  SELECT content_digest INTO profile FROM sem.artifact WHERE release_id=r AND artifact_name='analytical-profile.json';
  IF profile IS NULL OR profile IS DISTINCT FROM profile_digest THEN
   RAISE EXCEPTION 'candidate arithmetic profile differs from release' USING ERRCODE='23514'; END IF;
  expected_projection:='projection:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
   r,data.execution_contract_descriptor()->>'physical_id','analytical-5',profile,contract)),'UTF8')),'hex');
  IF projection IS DISTINCT FROM expected_projection THEN RAISE EXCEPTION 'candidate compiled projection differs' USING ERRCODE='23514'; END IF;
 ELSIF operation='publish_inference' AND contract_id='accepted' THEN
  IF z IS DISTINCT FROM source_realization OR projection IS DISTINCT FROM 'accepted' OR cut_id IS NOT NULL OR profile_digest IS NOT NULL THEN
   RAISE EXCEPTION 'accepted inference requires exact same-realization input' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM pg_temp.sp_entity) OR EXISTS(SELECT FROM pg_temp.sp_entity_source) OR EXISTS(SELECT FROM pg_temp.sp_identity_exclusion) OR EXISTS(SELECT FROM pg_temp.sp_identity_exclusion_evidence) OR EXISTS(SELECT FROM pg_temp.sp_membership) OR EXISTS(SELECT FROM pg_temp.sp_value_role) OR EXISTS(SELECT FROM pg_temp.sp_occurrence) OR EXISTS(SELECT FROM pg_temp.sp_support) OR EXISTS(SELECT FROM pg_temp.sp_evidence) OR EXISTS(SELECT FROM pg_temp.sp_occurrence_evidence) OR EXISTS(SELECT FROM pg_temp.sp_occurrence_context) OR EXISTS(SELECT FROM pg_temp.sp_occurrence_evidence_role) OR EXISTS(SELECT FROM pg_temp.sp_membership_support) OR EXISTS(SELECT FROM pg_temp.sp_coverage) OR EXISTS(SELECT FROM pg_temp.sp_occurrence_establishment) OR EXISTS(SELECT FROM pg_temp.sp_evidence_source) OR EXISTS(SELECT FROM pg_temp.sp_assessment) OR EXISTS(SELECT FROM pg_temp.sp_entity_input) OR EXISTS(SELECT FROM pg_temp.sp_fact_input) OR EXISTS(SELECT FROM pg_temp.sp_alternative_group) OR EXISTS(SELECT FROM pg_temp.sp_alternative_member) THEN
   RAISE EXCEPTION 'inference publication contains source/assertion transport rows' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM pg_temp.sp_fact f WHERE NOT EXISTS(SELECT FROM pg_temp.sp_derivation d WHERE d.conclusion_fact_id=f.fact_id)
      OR NOT EXISTS(SELECT FROM pg_temp.sp_selection s WHERE s.fact_id=f.fact_id AND s.selected)) OR
     EXISTS(SELECT FROM pg_temp.sp_selection s WHERE NOT s.selected OR NOT EXISTS(SELECT FROM pg_temp.sp_fact f WHERE f.fact_id=s.fact_id)) THEN
   RAISE EXCEPTION 'inference output lacks its staged proof conclusion' USING ERRCODE='23514'; END IF;
 ELSE RAISE EXCEPTION 'unsupported derived operation/projection implementation' USING ERRCODE='23514';
 END IF;
 SELECT data_revision INTO actual FROM data.realization
 WHERE release_id=source_release AND realization_id=source_realization AND state='active' FOR SHARE;
 IF actual IS NULL OR source_revision IS NULL OR actual<>source_revision THEN
  RAISE EXCEPTION 'source snapshot changed; recompute required' USING ERRCODE='P0004'; END IF;
 published:=data.publish_contract_batch(r,z,b,p_content);
 INSERT INTO data.publication_intent VALUES(r,z,b,source_release,source_realization,source_revision,source_capture,operation,binding);
 RETURN published;
END $fn$;
REVOKE ALL ON FUNCTION data.publish_derived_batch_v2(text,text,text,bytea,text,text,bigint,text,text,text,text,bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_derived_batch_v2(text,text,text,bytea,text,text,bigint,text,text,text,text,bigint,text) TO corpus_sem_writer;

-- Forward identity exclusion validation bound to each archived operation policy.

CREATE OR REPLACE FUNCTION data.validate_identity_exclusions(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE expected_policy_version text;
BEGIN
 IF EXISTS(SELECT FROM data.identity_exclusion WHERE release_id=r AND realization_id=z)
 AND NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2')
 THEN RAISE EXCEPTION 'identity exclusions require composed execution capability' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x JOIN kb.observation o ON o.id=x.observation_id AND o.release_id=r
   WHERE x.release_id=r AND x.realization_id=z AND x.exclusion_id IS DISTINCT FROM
     'identity-exclusion:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,o.observation_key,x.local_id)),'UTF8')),'hex'))
 THEN RAISE EXCEPTION 'identity exclusion identity differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x JOIN kb.observation o ON o.release_id=x.release_id AND o.id=x.observation_id
  WHERE x.release_id=r AND x.realization_id=z AND NOT EXISTS(
   SELECT FROM jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
   WHERE d->>'id'=x.local_id AND d->>'reason'=x.reason
     AND d->'left'->>'kind'=x.left_kind AND d->'left'->>'target'=x.left_ref
     AND d->'right'->>'kind'=x.right_kind AND d->'right'->>'target'=x.right_ref
     AND EXISTS(SELECT FROM jsonb_array_elements(d->'evidence') e
                WHERE e->>'outcome'='located' AND e->>'role'='primary')
  )) THEN RAISE EXCEPTION 'identity exclusion source declaration differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion WHERE release_id=r AND realization_id=z) THEN
  SELECT operation.value->>'policy_version' INTO expected_policy_version
  FROM sem.registry_row model
  CROSS JOIN LATERAL jsonb_array_elements(convert_from(model.body,'UTF8')::jsonb->'operations') operation(value)
  WHERE model.release_id=r AND model.kind='execution_model' AND operation.value->>'id'='resolve_identity';
  IF expected_policy_version IS NULL OR expected_policy_version='' OR EXISTS(
    SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z
    AND (x.operation_id IS DISTINCT FROM 'resolve_identity'
         OR x.operation_version IS DISTINCT FROM expected_policy_version))
  THEN RAISE EXCEPTION 'identity exclusion operation version differs from release model' USING ERRCODE='23514'; END IF;
 END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z AND
   NOT EXISTS(SELECT FROM data.identity_exclusion_evidence xe JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
     JOIN kb.span span ON span.id=es.span_id JOIN kb.observation o ON o.id=x.observation_id AND o.release_id=r
     CROSS JOIN LATERAL jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
     CROSS JOIN LATERAL jsonb_array_elements(d->'evidence') e
     WHERE xe.release_id=r AND xe.realization_id=z AND xe.exclusion_id=x.exclusion_id
       AND es.observation_id=x.observation_id AND d->>'id'=x.local_id
       AND e->>'outcome'='located' AND e->>'role'='primary'
       AND (e->>'start')::bigint=span.start_offset AND (e->>'end')::bigint=span.end_offset))
 THEN RAISE EXCEPTION 'identity exclusion lacks located primary custody' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x
  CROSS JOIN LATERAL (VALUES(x.left_kind,x.left_ref,x.left_entity_id),(x.right_kind,x.right_ref,x.right_entity_id)) ep(kind,ref,entity)
  WHERE x.release_id=r AND x.realization_id=z AND NOT (
   (ep.kind='local' AND EXISTS(SELECT FROM data.entity_source src WHERE src.release_id=r AND src.realization_id=z
       AND src.observation_id=x.observation_id AND src.local_id=ep.ref AND src.entity_id=ep.entity)) OR
   (ep.kind='known' AND EXISTS(SELECT FROM data.entity_input i WHERE i.release_id=r AND i.realization_id=z
       AND i.input_entity_id=ep.ref AND i.entity_id=ep.entity)) OR
   EXISTS(SELECT FROM data.identity_exclusion prior
     JOIN data.entity_input l ON l.release_id=r AND l.realization_id=z AND l.input_realization_id=prior.realization_id
       AND l.input_entity_id=prior.left_entity_id AND l.entity_id=x.left_entity_id
     JOIN data.entity_input rr ON rr.release_id=r AND rr.realization_id=z AND rr.input_realization_id=prior.realization_id
       AND rr.input_entity_id=prior.right_entity_id AND rr.entity_id=x.right_entity_id
     WHERE prior.release_id=r AND prior.observation_id=x.observation_id AND prior.local_id=x.local_id)))
 THEN RAISE EXCEPTION 'identity exclusion endpoint assignment differs' USING ERRCODE='23514'; END IF;

 IF EXISTS(SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z AND NOT (
   EXISTS(SELECT FROM ops.run job JOIN ops.input_cut cut ON cut.run_id=job.id AND cut.final
     JOIN ops.cut_task ct ON ct.cut_id=cut.id JOIN kb.observation o ON o.task_id=ct.origin_task_id
     WHERE job.release_id=r AND job.result_realization_id=z AND o.id=x.observation_id) OR
   EXISTS(SELECT FROM data.identity_exclusion prior
     JOIN data.entity_input l ON l.release_id=r AND l.realization_id=z AND l.input_realization_id=prior.realization_id AND l.input_entity_id=prior.left_entity_id AND l.entity_id=x.left_entity_id
     JOIN data.entity_input rr ON rr.release_id=r AND rr.realization_id=z AND rr.input_realization_id=prior.realization_id AND rr.input_entity_id=prior.right_entity_id AND rr.entity_id=x.right_entity_id
     WHERE prior.release_id=r AND prior.observation_id=x.observation_id AND prior.local_id=x.local_id)))
 THEN RAISE EXCEPTION 'identity exclusion source outside effective cut or input binding' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH expected AS (
   SELECT x.exclusion_id,(e->>'start')::bigint start_offset,(e->>'end')::bigint end_offset,e->>'role' role,e->>'locator' locator,count(*) n
   FROM data.identity_exclusion x JOIN kb.observation o ON o.release_id=r AND o.id=x.observation_id
   CROSS JOIN LATERAL jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
   CROSS JOIN LATERAL jsonb_array_elements(d->'evidence') e
   WHERE x.release_id=r AND x.realization_id=z AND d->>'id'=x.local_id AND e->>'outcome'='located'
   GROUP BY x.exclusion_id,e->>'start',e->>'end',e->>'role',e->>'locator'
 ), actual AS (
   SELECT x.exclusion_id,span.start_offset,span.end_offset,ev.locator::jsonb->>'role' role,ev.locator::jsonb->>'locator' locator,count(*) n
   FROM data.identity_exclusion x JOIN data.identity_exclusion_evidence xe USING(release_id,realization_id,exclusion_id)
   JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
   JOIN data.evidence ev USING(release_id,realization_id,evidence_id) JOIN kb.span span ON span.id=es.span_id
   WHERE x.release_id=r AND x.realization_id=z AND es.observation_id=x.observation_id
   GROUP BY x.exclusion_id,span.start_offset,span.end_offset,ev.locator::jsonb->>'role',ev.locator::jsonb->>'locator'
 ) SELECT FROM ((SELECT * FROM expected EXCEPT SELECT * FROM actual)
   UNION ALL (SELECT * FROM actual EXCEPT SELECT * FROM expected)) mismatch)
 THEN RAISE EXCEPTION 'identity exclusion evidence differs from source citations' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion_evidence xe JOIN data.identity_exclusion x USING(release_id,realization_id,exclusion_id)
   LEFT JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
   WHERE xe.release_id=r AND xe.realization_id=z AND es.observation_id IS DISTINCT FROM x.observation_id)
 THEN RAISE EXCEPTION 'identity exclusion evidence outside source observation' USING ERRCODE='23514'; END IF;
END $fn$;
ALTER FUNCTION data.validate_identity_exclusions(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_identity_exclusions(text,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION data.begin_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $transport$
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 IF to_regclass('pg_temp.sp_entity') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_entity("entity_id" text) ON COMMIT DROP; GRANT INSERT ("entity_id") ON pg_temp.sp_entity TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_entity_source') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_entity_source("entity_id" text,"observation_id" bigint,"local_id" text) ON COMMIT DROP; GRANT INSERT ("entity_id","observation_id","local_id") ON pg_temp.sp_entity_source TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_identity_exclusion') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_identity_exclusion("exclusion_id" text,"observation_id" bigint,"local_id" text,"left_kind" text,"left_ref" text,"right_kind" text,"right_ref" text,"left_entity_id" text,"right_entity_id" text,"reason" text,"operation_id" text,"operation_version" text) ON COMMIT DROP; GRANT INSERT ("exclusion_id","observation_id","local_id","left_kind","left_ref","right_kind","right_ref","left_entity_id","right_entity_id","reason","operation_id","operation_version") ON pg_temp.sp_identity_exclusion TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_identity_exclusion_evidence') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_identity_exclusion_evidence("exclusion_id" text,"evidence_id" text) ON COMMIT DROP; GRANT INSERT ("exclusion_id","evidence_id") ON pg_temp.sp_identity_exclusion_evidence TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_membership') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_membership("entity_id" text,"class_id" text,"establishment" text) ON COMMIT DROP; GRANT INSERT ("entity_id","class_id","establishment") ON pg_temp.sp_membership TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_typed_value') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_typed_value("value_id" text,"kind" text,"text_value" text,"integer_value" numeric,"numeric_value" numeric,"decimal_lexical" text,"boolean_value" boolean,"entity_id" text,"language" text,"datatype" text,"opaque_payload" jsonb) ON COMMIT DROP; GRANT INSERT ("value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload") ON pg_temp.sp_typed_value TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_value_role') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_value_role("parent_value_id" text,"role" text,"position" bigint,"child_value_id" text) ON COMMIT DROP; GRANT INSERT ("parent_value_id","role","position","child_value_id") ON pg_temp.sp_value_role TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_fact') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_fact("fact_id" text,"subject_id" text,"property_id" text,"object_value_id" text,"qualification_value_id" text) ON COMMIT DROP; GRANT INSERT ("fact_id","subject_id","property_id","object_value_id","qualification_value_id") ON pg_temp.sp_fact TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence("occurrence_id" text,"fact_id" text,"source" text,"item" text,"report_object_value_id" text,"report_qualification_value_id" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id") ON pg_temp.sp_occurrence TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_support') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_support("fact_id" text,"occurrence_id" text) ON COMMIT DROP; GRANT INSERT ("fact_id","occurrence_id") ON pg_temp.sp_support TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_selection') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_selection("fact_id" text,"selected" boolean) ON COMMIT DROP; GRANT INSERT ("fact_id","selected") ON pg_temp.sp_selection TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_evidence') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_evidence("evidence_id" text,"source_uri" text,"locator" text,"provider" text,"operation_version" text) ON COMMIT DROP; GRANT INSERT ("evidence_id","source_uri","locator","provider","operation_version") ON pg_temp.sp_evidence TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence_evidence') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence_evidence("occurrence_id" text,"evidence_id" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","evidence_id") ON pg_temp.sp_occurrence_evidence TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence_context') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence_context("occurrence_id" text,"statement_entity_id" text,"statement_role" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","statement_entity_id","statement_role") ON pg_temp.sp_occurrence_context TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence_evidence_role') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence_evidence_role("occurrence_id" text,"evidence_id" text,"role" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","evidence_id","role") ON pg_temp.sp_occurrence_evidence_role TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_membership_support') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_membership_support("entity_id" text,"class_id" text,"evidence_id" text) ON COMMIT DROP; GRANT INSERT ("entity_id","class_id","evidence_id") ON pg_temp.sp_membership_support TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_derivation') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_derivation("derivation_id" text,"conclusion_fact_id" text,"rule" text,"rule_version" text) ON COMMIT DROP; GRANT INSERT ("derivation_id","conclusion_fact_id","rule","rule_version") ON pg_temp.sp_derivation TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_derivation_premise') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_derivation_premise("derivation_id" text,"position" bigint,"premise_fact_id" text) ON COMMIT DROP; GRANT INSERT ("derivation_id","position","premise_fact_id") ON pg_temp.sp_derivation_premise TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_coverage') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_coverage("coverage_id" text,"family" text,"scope" text,"outcome" text,"reason" text,"source_outcome" text,"required_capability" text) ON COMMIT DROP; GRANT INSERT ("coverage_id","family","scope","outcome","reason","source_outcome","required_capability") ON pg_temp.sp_coverage TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence_establishment') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence_establishment("occurrence_id" text,"establishment" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","establishment") ON pg_temp.sp_occurrence_establishment TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_evidence_source') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_evidence_source("evidence_id" text,"observation_id" bigint,"rendition_id" bigint,"span_id" bigint) ON COMMIT DROP; GRANT INSERT ("evidence_id","observation_id","rendition_id","span_id") ON pg_temp.sp_evidence_source TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_assessment') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_assessment("assessment_id" text,"operation_id" text,"operation_version" text,"outcome" text,"fact_id" text,"occurrence_id" text,"confidence" numeric,"reason" text,"uncertainty" text,"counterpart_fact_id" text,"counterpart_occurrence_id" text,"context_value_id" text,"comparison_tier" text) ON COMMIT DROP; GRANT INSERT ("assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty","counterpart_fact_id","counterpart_occurrence_id","context_value_id","comparison_tier") ON pg_temp.sp_assessment TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_entity_input') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_entity_input("entity_id" text,"input_realization_id" text,"input_data_revision" bigint,"input_entity_id" text,"run_id" bigint) ON COMMIT DROP; GRANT INSERT ("entity_id","input_realization_id","input_data_revision","input_entity_id","run_id") ON pg_temp.sp_entity_input TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_fact_input') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_fact_input("fact_id" text,"input_realization_id" text,"input_data_revision" bigint,"input_fact_id" text,"run_id" bigint) ON COMMIT DROP; GRANT INSERT ("fact_id","input_realization_id","input_data_revision","input_fact_id","run_id") ON pg_temp.sp_fact_input TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_alternative_group') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_alternative_group("group_id" text,"reason" text,"operation_id" text,"operation_version" text) ON COMMIT DROP; GRANT INSERT ("group_id","reason","operation_id","operation_version") ON pg_temp.sp_alternative_group TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_alternative_member') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_alternative_member("group_id" text,"fact_id" text) ON COMMIT DROP; GRANT INSERT ("group_id","fact_id") ON pg_temp.sp_alternative_member TO corpus_sem_writer;
END $transport$;
CREATE OR REPLACE FUNCTION data.publish_contract_batch(r text,z text,b text,p_content bytea) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $transport$

DECLARE actual bytea; old data.batch%ROWTYPE; rev bigint; f record; application record; expected text;
BEGIN
 PERFORM sem.require_execution_operation(r,'publish');
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity_source' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','observation_id:bigint','local_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity_source'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_identity_exclusion' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['exclusion_id:text','observation_id:bigint','local_id:text','left_kind:text','left_ref:text','right_kind:text','right_ref:text','left_entity_id:text','right_entity_id:text','reason:text','operation_id:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_identity_exclusion'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_identity_exclusion_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['exclusion_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_identity_exclusion_evidence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_typed_value' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['value_id:text','kind:text','text_value:text','integer_value:numeric','numeric_value:numeric','decimal_lexical:text','boolean_value:boolean','entity_id:text','language:text','datatype:text','opaque_payload:jsonb']) THEN RAISE EXCEPTION 'untrusted staging relation sp_typed_value'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_value_role' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['parent_value_id:text','role:text','position:bigint','child_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_value_role'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','subject_id:text','property_id:text','object_value_id:text','qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','fact_id:text','source:text','item:text','report_object_value_id:text','report_qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','occurrence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_support'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_selection' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','selected:boolean']) THEN RAISE EXCEPTION 'untrusted staging relation sp_selection'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','source_uri:text','locator:text','provider:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_evidence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_context' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','statement_entity_id:text','statement_role:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_context'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_evidence_role' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','evidence_id:text','role:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_evidence_role'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership_support'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','conclusion_fact_id:text','rule:text','rule_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation_premise' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','position:bigint','premise_fact_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation_premise'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_coverage' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['coverage_id:text','family:text','scope:text','outcome:text','reason:text','source_outcome:text','required_capability:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_coverage'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_establishment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_establishment'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence_source' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','observation_id:bigint','rendition_id:bigint','span_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence_source'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_assessment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['assessment_id:text','operation_id:text','operation_version:text','outcome:text','fact_id:text','occurrence_id:text','confidence:numeric','reason:text','uncertainty:text','counterpart_fact_id:text','counterpart_occurrence_id:text','context_value_id:text','comparison_tier:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_assessment'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','input_realization_id:text','input_data_revision:bigint','input_entity_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity_input'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','input_realization_id:text','input_data_revision:bigint','input_fact_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact_input'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_alternative_group' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['group_id:text','reason:text','operation_id:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_alternative_group'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_alternative_member' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['group_id:text','fact_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_alternative_member'; END IF;
 actual:=convert_to(data.canonical_json(jsonb_build_array(r,z,jsonb_build_object('entity',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id") j FROM pg_temp.sp_entity) q),'[]'::jsonb),
'entity_source',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","observation_id","local_id") j FROM pg_temp.sp_entity_source) q),'[]'::jsonb),
'identity_exclusion',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("exclusion_id","observation_id","local_id","left_kind","left_ref","right_kind","right_ref","left_entity_id","right_entity_id","reason","operation_id","operation_version") j FROM pg_temp.sp_identity_exclusion) q),'[]'::jsonb),
'identity_exclusion_evidence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("exclusion_id","evidence_id") j FROM pg_temp.sp_identity_exclusion_evidence) q),'[]'::jsonb),
'membership',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","class_id","establishment") j FROM pg_temp.sp_membership) q),'[]'::jsonb),
'typed_value',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("value_id","kind","text_value","integer_value"::text,"numeric_value"::text,"decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload") j FROM pg_temp.sp_typed_value) q),'[]'::jsonb),
'value_role',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("parent_value_id","role","position","child_value_id") j FROM pg_temp.sp_value_role) q),'[]'::jsonb),
'fact',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","subject_id","property_id","object_value_id","qualification_value_id") j FROM pg_temp.sp_fact) q),'[]'::jsonb),
'occurrence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id") j FROM pg_temp.sp_occurrence) q),'[]'::jsonb),
'support',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","occurrence_id") j FROM pg_temp.sp_support) q),'[]'::jsonb),
'selection',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","selected") j FROM pg_temp.sp_selection) q),'[]'::jsonb),
'evidence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("evidence_id","source_uri","locator","provider","operation_version") j FROM pg_temp.sp_evidence) q),'[]'::jsonb),
'occurrence_evidence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","evidence_id") j FROM pg_temp.sp_occurrence_evidence) q),'[]'::jsonb),
'occurrence_context',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","statement_entity_id","statement_role") j FROM pg_temp.sp_occurrence_context) q),'[]'::jsonb),
'occurrence_evidence_role',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","evidence_id","role") j FROM pg_temp.sp_occurrence_evidence_role) q),'[]'::jsonb),
'membership_support',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","class_id","evidence_id") j FROM pg_temp.sp_membership_support) q),'[]'::jsonb),
'derivation',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("derivation_id","conclusion_fact_id","rule","rule_version") j FROM pg_temp.sp_derivation) q),'[]'::jsonb),
'derivation_premise',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("derivation_id","position","premise_fact_id") j FROM pg_temp.sp_derivation_premise) q),'[]'::jsonb),
'coverage',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("coverage_id","family","scope","outcome","reason","source_outcome","required_capability") j FROM pg_temp.sp_coverage) q),'[]'::jsonb),
'occurrence_establishment',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","establishment") j FROM pg_temp.sp_occurrence_establishment) q),'[]'::jsonb),
'evidence_source',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("evidence_id","observation_id","rendition_id","span_id") j FROM pg_temp.sp_evidence_source) q),'[]'::jsonb),
'assessment',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence"::text,"reason","uncertainty","counterpart_fact_id","counterpart_occurrence_id","context_value_id","comparison_tier") j FROM pg_temp.sp_assessment) q),'[]'::jsonb),
'entity_input',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","input_realization_id","input_data_revision","input_entity_id","run_id") j FROM pg_temp.sp_entity_input) q),'[]'::jsonb),
'fact_input',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","input_realization_id","input_data_revision","input_fact_id","run_id") j FROM pg_temp.sp_fact_input) q),'[]'::jsonb),
'alternative_group',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("group_id","reason","operation_id","operation_version") j FROM pg_temp.sp_alternative_group) q),'[]'::jsonb),
'alternative_member',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("group_id","fact_id") j FROM pg_temp.sp_alternative_member) q),'[]'::jsonb)))),'UTF8');
 IF actual<>p_content THEN RAISE EXCEPTION 'batch bytes differ from staged content' USING ERRCODE='23514'; END IF;
 SELECT * INTO old FROM data.batch WHERE release_id=r AND realization_id=z AND batch_id=b;
 IF FOUND THEN
 IF old.content<>actual THEN RAISE EXCEPTION 'batch identity content conflict' USING ERRCODE='23505'; END IF;
 RETURN old.data_revision;
 END IF;
 IF EXISTS(SELECT FROM ops.run WHERE release_id=r AND result_realization_id=z AND status='finished') THEN RAISE EXCEPTION 'evaluated realization is immutable'; END IF;
 IF NOT EXISTS(SELECT FROM data.realization WHERE release_id=r AND realization_id=z AND state='active') THEN RAISE EXCEPTION 'realization not active in bound release' USING ERRCODE='23514'; END IF;
 -- The receipt exists in this transaction before occurrence FKs are checked.
 UPDATE data.realization SET data_revision=data_revision+1 WHERE release_id=r AND realization_id=z RETURNING data_revision INTO rev;
 INSERT INTO data.batch(release_id,realization_id,batch_id,content,content_digest,data_revision) VALUES(r,z,b,actual,encode(sha256(actual),'hex'),rev);
 IF EXISTS(SELECT FROM pg_temp.sp_value_role candidate JOIN data.typed_value parent ON parent.release_id=r AND parent.realization_id=z AND parent.value_id=candidate.parent_value_id WHERE NOT EXISTS(SELECT FROM data.value_role existing WHERE existing.release_id=r AND existing.realization_id=z AND (existing.parent_value_id,existing.role,existing.position,existing.child_value_id)=(candidate.parent_value_id,candidate.role,candidate.position,candidate.child_value_id))) THEN RAISE EXCEPTION 'existing typed value graph is immutable' USING ERRCODE='23514'; END IF;
 INSERT INTO data.entity(release_id,realization_id,"entity_id") SELECT r,z,"entity_id" FROM pg_temp.sp_entity ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id" FROM pg_temp.sp_entity EXCEPT SELECT "entity_id" FROM data.entity WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing entity' USING ERRCODE='23505'; END IF;
INSERT INTO data.entity_source(release_id,realization_id,"entity_id","observation_id","local_id") SELECT r,z,"entity_id","observation_id","local_id" FROM pg_temp.sp_entity_source ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id","observation_id","local_id" FROM pg_temp.sp_entity_source EXCEPT SELECT "entity_id","observation_id","local_id" FROM data.entity_source WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing entity_source' USING ERRCODE='23505'; END IF;
INSERT INTO data.identity_exclusion(release_id,realization_id,"exclusion_id","observation_id","local_id","left_kind","left_ref","right_kind","right_ref","left_entity_id","right_entity_id","reason","operation_id","operation_version") SELECT r,z,"exclusion_id","observation_id","local_id","left_kind","left_ref","right_kind","right_ref","left_entity_id","right_entity_id","reason","operation_id","operation_version" FROM pg_temp.sp_identity_exclusion ON CONFLICT DO NOTHING; IF EXISTS(SELECT "exclusion_id","observation_id","local_id","left_kind","left_ref","right_kind","right_ref","left_entity_id","right_entity_id","reason","operation_id","operation_version" FROM pg_temp.sp_identity_exclusion EXCEPT SELECT "exclusion_id","observation_id","local_id","left_kind","left_ref","right_kind","right_ref","left_entity_id","right_entity_id","reason","operation_id","operation_version" FROM data.identity_exclusion WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing identity_exclusion' USING ERRCODE='23505'; END IF;
INSERT INTO data.identity_exclusion_evidence(release_id,realization_id,"exclusion_id","evidence_id") SELECT r,z,"exclusion_id","evidence_id" FROM pg_temp.sp_identity_exclusion_evidence ON CONFLICT DO NOTHING; IF EXISTS(SELECT "exclusion_id","evidence_id" FROM pg_temp.sp_identity_exclusion_evidence EXCEPT SELECT "exclusion_id","evidence_id" FROM data.identity_exclusion_evidence WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing identity_exclusion_evidence' USING ERRCODE='23505'; END IF;
INSERT INTO data.membership(release_id,realization_id,"entity_id","class_id","establishment") SELECT r,z,"entity_id","class_id","establishment" FROM pg_temp.sp_membership ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id","class_id","establishment" FROM pg_temp.sp_membership EXCEPT SELECT "entity_id","class_id","establishment" FROM data.membership WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing membership' USING ERRCODE='23505'; END IF;
INSERT INTO data.typed_value(release_id,realization_id,"value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload") SELECT r,z,"value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload" FROM pg_temp.sp_typed_value ON CONFLICT DO NOTHING; IF EXISTS(SELECT "value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload" FROM pg_temp.sp_typed_value EXCEPT SELECT "value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload" FROM data.typed_value WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing typed_value' USING ERRCODE='23505'; END IF;
INSERT INTO data.value_role(release_id,realization_id,"parent_value_id","role","position","child_value_id") SELECT r,z,"parent_value_id","role","position","child_value_id" FROM pg_temp.sp_value_role ON CONFLICT DO NOTHING; IF EXISTS(SELECT "parent_value_id","role","position","child_value_id" FROM pg_temp.sp_value_role EXCEPT SELECT "parent_value_id","role","position","child_value_id" FROM data.value_role WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing value_role' USING ERRCODE='23505'; END IF;
INSERT INTO data.fact(release_id,realization_id,fact_id,subject_id,property_id,object_value_id,qualification_value_id)
SELECT r,z,fact_id,subject_id,property_id,object_value_id,qualification_value_id FROM pg_temp.sp_fact
ON CONFLICT DO NOTHING;
IF EXISTS(SELECT FROM pg_temp.sp_fact candidate JOIN data.fact actual
ON actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id
WHERE data.fact_identity(r,z,candidate.subject_id,candidate.property_id,candidate.object_value_id,candidate.qualification_value_id)
<>data.fact_identity(r,z,actual.subject_id,actual.property_id,actual.object_value_id,actual.qualification_value_id))
THEN RAISE EXCEPTION 'conflicting existing fact meaning' USING ERRCODE='23505'; END IF;

INSERT INTO data.occurrence(release_id,realization_id,"occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id",batch_id) SELECT r,z,"occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id",b FROM pg_temp.sp_occurrence ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id" FROM pg_temp.sp_occurrence EXCEPT SELECT "occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id" FROM data.occurrence WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence' USING ERRCODE='23505'; END IF;
INSERT INTO data.support(release_id,realization_id,"fact_id","occurrence_id") SELECT r,z,"fact_id","occurrence_id" FROM pg_temp.sp_support ON CONFLICT DO NOTHING; IF EXISTS(SELECT "fact_id","occurrence_id" FROM pg_temp.sp_support EXCEPT SELECT "fact_id","occurrence_id" FROM data.support WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing support' USING ERRCODE='23505'; END IF;
IF EXISTS(SELECT FROM pg_temp.sp_selection GROUP BY fact_id HAVING count(DISTINCT selected)>1 OR bool_or(selected IS NULL))
THEN RAISE EXCEPTION 'ambiguous selection product' USING ERRCODE='23514'; END IF;
IF EXISTS(SELECT FROM pg_temp.sp_selection candidate WHERE NOT EXISTS(SELECT FROM data.fact actual WHERE actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id))
THEN RAISE EXCEPTION 'selection fact is outside scope' USING ERRCODE='23503'; END IF;
DELETE FROM data.selection actual USING pg_temp.sp_selection candidate
WHERE actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id AND NOT candidate.selected;
INSERT INTO data.selection(release_id,realization_id,fact_id)
SELECT r,z,fact_id FROM pg_temp.sp_selection WHERE selected ON CONFLICT DO NOTHING;

INSERT INTO data.evidence(release_id,realization_id,"evidence_id","source_uri","locator","provider","operation_version") SELECT r,z,"evidence_id","source_uri","locator","provider","operation_version" FROM pg_temp.sp_evidence ON CONFLICT DO NOTHING; IF EXISTS(SELECT "evidence_id","source_uri","locator","provider","operation_version" FROM pg_temp.sp_evidence EXCEPT SELECT "evidence_id","source_uri","locator","provider","operation_version" FROM data.evidence WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing evidence' USING ERRCODE='23505'; END IF;
INSERT INTO data.occurrence_evidence(release_id,realization_id,"occurrence_id","evidence_id") SELECT r,z,"occurrence_id","evidence_id" FROM pg_temp.sp_occurrence_evidence ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","evidence_id" FROM pg_temp.sp_occurrence_evidence EXCEPT SELECT "occurrence_id","evidence_id" FROM data.occurrence_evidence WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence_evidence' USING ERRCODE='23505'; END IF;
INSERT INTO data.occurrence_context(release_id,realization_id,"occurrence_id","statement_entity_id","statement_role") SELECT r,z,"occurrence_id","statement_entity_id","statement_role" FROM pg_temp.sp_occurrence_context ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","statement_entity_id","statement_role" FROM pg_temp.sp_occurrence_context EXCEPT SELECT "occurrence_id","statement_entity_id","statement_role" FROM data.occurrence_context WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence_context' USING ERRCODE='23505'; END IF;
INSERT INTO data.occurrence_evidence_role(release_id,realization_id,"occurrence_id","evidence_id","role") SELECT r,z,"occurrence_id","evidence_id","role" FROM pg_temp.sp_occurrence_evidence_role ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","evidence_id","role" FROM pg_temp.sp_occurrence_evidence_role EXCEPT SELECT "occurrence_id","evidence_id","role" FROM data.occurrence_evidence_role WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence_evidence_role' USING ERRCODE='23505'; END IF;
INSERT INTO data.membership_support(release_id,realization_id,"entity_id","class_id","evidence_id") SELECT r,z,"entity_id","class_id","evidence_id" FROM pg_temp.sp_membership_support ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id","class_id","evidence_id" FROM pg_temp.sp_membership_support EXCEPT SELECT "entity_id","class_id","evidence_id" FROM data.membership_support WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing membership_support' USING ERRCODE='23505'; END IF;
INSERT INTO data.derivation(release_id,realization_id,"derivation_id","conclusion_fact_id","rule","rule_version") SELECT r,z,"derivation_id","conclusion_fact_id","rule","rule_version" FROM pg_temp.sp_derivation ON CONFLICT DO NOTHING; IF EXISTS(SELECT "derivation_id","conclusion_fact_id","rule","rule_version" FROM pg_temp.sp_derivation EXCEPT SELECT "derivation_id","conclusion_fact_id","rule","rule_version" FROM data.derivation WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing derivation' USING ERRCODE='23505'; END IF;
INSERT INTO data.derivation_premise(release_id,realization_id,"derivation_id","position","premise_fact_id") SELECT r,z,"derivation_id","position","premise_fact_id" FROM pg_temp.sp_derivation_premise ON CONFLICT DO NOTHING; IF EXISTS(SELECT "derivation_id","position","premise_fact_id" FROM pg_temp.sp_derivation_premise EXCEPT SELECT "derivation_id","position","premise_fact_id" FROM data.derivation_premise WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing derivation_premise' USING ERRCODE='23505'; END IF;
INSERT INTO data.coverage(release_id,realization_id,"coverage_id","family","scope","outcome","reason","source_outcome","required_capability") SELECT r,z,"coverage_id","family","scope","outcome","reason","source_outcome","required_capability" FROM pg_temp.sp_coverage ON CONFLICT DO NOTHING; IF EXISTS(SELECT "coverage_id","family","scope","outcome","reason","source_outcome","required_capability" FROM pg_temp.sp_coverage EXCEPT SELECT "coverage_id","family","scope","outcome","reason","source_outcome","required_capability" FROM data.coverage WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing coverage' USING ERRCODE='23505'; END IF;
INSERT INTO data.occurrence_establishment(release_id,realization_id,"occurrence_id","establishment") SELECT r,z,"occurrence_id","establishment" FROM pg_temp.sp_occurrence_establishment ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","establishment" FROM pg_temp.sp_occurrence_establishment EXCEPT SELECT "occurrence_id","establishment" FROM data.occurrence_establishment WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence_establishment' USING ERRCODE='23505'; END IF;
INSERT INTO data.evidence_source(release_id,realization_id,"evidence_id","observation_id","rendition_id","span_id") SELECT r,z,"evidence_id","observation_id","rendition_id","span_id" FROM pg_temp.sp_evidence_source ON CONFLICT DO NOTHING; IF EXISTS(SELECT "evidence_id","observation_id","rendition_id","span_id" FROM pg_temp.sp_evidence_source EXCEPT SELECT "evidence_id","observation_id","rendition_id","span_id" FROM data.evidence_source WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing evidence_source' USING ERRCODE='23505'; END IF;
INSERT INTO data.assessment(release_id,realization_id,"assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty","counterpart_fact_id","counterpart_occurrence_id","context_value_id","comparison_tier") SELECT r,z,"assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty","counterpart_fact_id","counterpart_occurrence_id","context_value_id","comparison_tier" FROM pg_temp.sp_assessment ON CONFLICT DO NOTHING; IF EXISTS(SELECT "assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty","counterpart_fact_id","counterpart_occurrence_id","context_value_id","comparison_tier" FROM pg_temp.sp_assessment EXCEPT SELECT "assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty","counterpart_fact_id","counterpart_occurrence_id","context_value_id","comparison_tier" FROM data.assessment WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing assessment' USING ERRCODE='23505'; END IF;
INSERT INTO data.entity_input(release_id,realization_id,"entity_id","input_realization_id","input_data_revision","input_entity_id","run_id") SELECT r,z,"entity_id","input_realization_id","input_data_revision","input_entity_id","run_id" FROM pg_temp.sp_entity_input ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id","input_realization_id","input_data_revision","input_entity_id","run_id" FROM pg_temp.sp_entity_input EXCEPT SELECT "entity_id","input_realization_id","input_data_revision","input_entity_id","run_id" FROM data.entity_input WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing entity_input' USING ERRCODE='23505'; END IF;
INSERT INTO data.fact_input(release_id,realization_id,"fact_id","input_realization_id","input_data_revision","input_fact_id","run_id") SELECT r,z,"fact_id","input_realization_id","input_data_revision","input_fact_id","run_id" FROM pg_temp.sp_fact_input ON CONFLICT DO NOTHING; IF EXISTS(SELECT "fact_id","input_realization_id","input_data_revision","input_fact_id","run_id" FROM pg_temp.sp_fact_input EXCEPT SELECT "fact_id","input_realization_id","input_data_revision","input_fact_id","run_id" FROM data.fact_input WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing fact_input' USING ERRCODE='23505'; END IF;
INSERT INTO data.alternative_group(release_id,realization_id,"group_id","reason","operation_id","operation_version") SELECT r,z,"group_id","reason","operation_id","operation_version" FROM pg_temp.sp_alternative_group ON CONFLICT DO NOTHING; IF EXISTS(SELECT "group_id","reason","operation_id","operation_version" FROM pg_temp.sp_alternative_group EXCEPT SELECT "group_id","reason","operation_id","operation_version" FROM data.alternative_group WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing alternative_group' USING ERRCODE='23505'; END IF;
INSERT INTO data.alternative_member(release_id,realization_id,"group_id","fact_id") SELECT r,z,"group_id","fact_id" FROM pg_temp.sp_alternative_member ON CONFLICT DO NOTHING; IF EXISTS(SELECT "group_id","fact_id" FROM pg_temp.sp_alternative_member EXCEPT SELECT "group_id","fact_id" FROM data.alternative_member WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing alternative_member' USING ERRCODE='23505'; END IF;
 PERFORM data.validate_state(r,z);
 PERFORM data.validate_occurrence_context(r,z);
 PERFORM data.validate_entity_source(r,z);
 PERFORM data.validate_alternatives(r,z);
 FOR f IN SELECT * FROM pg_temp.sp_occurrence LOOP
 expected:='occ:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,f.source,f.item)),'UTF8')),'hex');
 IF expected<>f.occurrence_id THEN RAISE EXCEPTION 'invalid occurrence identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM pg_temp.sp_fact LOOP
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.object_value_id,f.qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'invalid fact identity' USING ERRCODE='23514'; END IF;
 END LOOP;

 FOR f IN SELECT o.*,df.subject_id,df.property_id FROM data.occurrence o JOIN data.fact df ON (df.release_id,df.realization_id,df.fact_id)=(o.release_id,o.realization_id,o.fact_id) WHERE o.release_id=r AND o.realization_id=z LOOP
 IF NOT EXISTS(SELECT FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id) THEN RAISE EXCEPTION 'report property is not applicable to subject class' USING ERRCODE='23514'; END IF;
 FOR application IN SELECT pa.* FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id LOOP
 PERFORM data.validate_property(r,z,f.report_object_value_id,COALESCE(application.constraints->>'native_range',application.range_name),CASE WHEN application.constraint_scope='shape' THEN application.constraints ELSE application.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum' END);
 END LOOP;
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.report_object_value_id,f.report_qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'report meaning differs from fact' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND NOT EXISTS(SELECT FROM data.typed_value v JOIN sem.class_definition c ON c.release_id=r AND c.class_id=v.datatype AND (c.name='Qualification' OR EXISTS(SELECT FROM sem.class_hierarchy h JOIN sem.class_definition root ON root.release_id=h.release_id AND root.class_id=h.ancestor_id AND root.name='Qualification' WHERE h.release_id=r AND h.class_id=c.class_id)) WHERE v.release_id=r AND v.realization_id=z AND v.value_id=f.report_qualification_value_id) THEN RAISE EXCEPTION 'report requires typed qualification' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN rev;
END 
$transport$;
REVOKE ALL ON FUNCTION data.publish_contract_batch(text,text,text,bytea) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.begin_stage() TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION sem.require_execution_projection(r text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $projection$
DECLARE document jsonb; model jsonb; actual jsonb; expected jsonb;
BEGIN
 SELECT convert_from(prepared_bytes,'UTF8')::jsonb INTO STRICT document FROM sem.release WHERE release_id=r;
 -- Historical finalized archives retain their recorded projection ABI without backfill.
 IF (SELECT convert_from(manifest_bytes,'UTF8')::jsonb->'profile'->>'compiler_version' FROM sem.release WHERE release_id=r)<>'13' THEN RETURN; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('kind',kind,'name',name,'body_hex',encode(body,'hex')) ORDER BY kind,name),'[]'::jsonb) INTO actual FROM sem.registry_row WHERE release_id=r;
 SELECT COALESCE(jsonb_agg(value ORDER BY value->>'kind',value->>'name'),'[]'::jsonb) INTO expected FROM jsonb_array_elements(document->'products'->'registry_rows');
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived registry projection differs' USING ERRCODE='23514'; END IF;
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row WHERE release_id=r AND kind='execution_model';
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,o->>'id' operation_id,o->>'implementation' implementation_id,b->>'version' implementation_version FROM jsonb_array_elements(model->'operations') o JOIN jsonb_array_elements(model->'implementations') b ON b->>'id'=o->>'implementation') x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.execution_operation x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived execution_operation projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,t->>'id' transition_id,t->>'operation' operation_id,t->>'lifecycle' lifecycle FROM jsonb_array_elements(model->'transitions') t) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.execution_transition x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived execution_transition projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,t->>'id' transition_id,b.value prior_state,a.value result_state FROM jsonb_array_elements(model->'transitions') t CROSS JOIN LATERAL jsonb_array_elements_text(t->'from_states') b CROSS JOIN LATERAL jsonb_array_elements_text(t->'to_states') a) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.execution_edge x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived execution_edge projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,o->>'id' operation_id,e.value effect_id FROM jsonb_array_elements(model->'operations') o CROSS JOIN LATERAL jsonb_array_elements_text(o->'effects') e) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.operation_effect x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived operation_effect projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,t->>'id' transition_id,e.value effect_id FROM jsonb_array_elements(model->'transitions') t CROSS JOIN LATERAL jsonb_array_elements_text(t->'effects') e) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.transition_effect x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived transition_effect projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,rule->>'policy_id' policy_id,rule->>'evidence_tier' evidence_tier,rule->>'agreement' agreement,rule->>'decision' decision,rule->>'decision_tier' decision_tier FROM sem.artifact a CROSS JOIN LATERAL jsonb_array_elements(convert_from(a.content,'UTF8')::jsonb->'decision_rules') rule WHERE a.release_id=r AND a.artifact_name='operation/scientific-policy.json') x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.scientific_decision_rule x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived scientific_decision_rule projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (WITH declarations AS (SELECT d FROM jsonb_array_elements(document->'products'->'definitions') d), props AS (
 SELECT d,p FROM declarations CROSS JOIN LATERAL jsonb_array_elements(d->'properties') p
 ) SELECT DISTINCT r release_id,d->>'iri' class_id,p->>'iri' property_id,roles.role
 FROM props CROSS JOIN LATERAL (
 SELECT 'identity' role WHERE EXISTS(SELECT FROM jsonb_array_elements(d->'identity_groups') g CROSS JOIN LATERAL jsonb_array_elements_text(g) member WHERE member.value=p->>'name')
 UNION ALL SELECT 'required' WHERE (p->>'required')::boolean OR COALESCE((p->>'minimum_cardinality')::integer,0)>0
 UNION ALL SELECT 'display' WHERE EXISTS(SELECT FROM sem.registry_row reg WHERE reg.release_id=r AND reg.kind='operation_property' AND convert_from(reg.body,'UTF8')::jsonb->>'class'=d->>'name' AND convert_from(reg.body,'UTF8')::jsonb->>'property'=p->>'iri' AND convert_from(reg.body,'UTF8')::jsonb->>'cs:role'='display')
 ) roles) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.operation_property_role x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived operation_property_role projection differs' USING ERRCODE='23514'; END IF;
END $projection$;
REVOKE ALL ON FUNCTION sem.require_execution_projection(text) FROM PUBLIC;

-- Stable relational consumers. Candidate releases supply rows, never SQL identifiers or bodies.
CREATE OR REPLACE FUNCTION sem.require_execution_operation(r text,operation text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $operation$
DECLARE supported jsonb; actual jsonb; expected jsonb;
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RETURN; END IF;
 supported:=data.execution_contract_descriptor()->'supported_effects'->operation;
 IF supported IS NULL OR NOT EXISTS(SELECT FROM sem.execution_operation o WHERE o.release_id=r AND o.operation_id=operation
  AND o.implementation_id=supported->>'implementation' AND o.implementation_version=supported->>'version') THEN
  RAISE EXCEPTION 'unsupported execution operation % in release %',operation,r USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(effect_id ORDER BY effect_id),'[]'::jsonb) INTO actual
 FROM sem.operation_effect WHERE release_id=r AND operation_id=operation;
 IF actual IS DISTINCT FROM supported->'effects' THEN
  RAISE EXCEPTION 'unsupported execution effects for %',operation USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_object_agg(t.transition_id,COALESCE((SELECT jsonb_agg(e.effect_id ORDER BY e.effect_id)
  FROM sem.transition_effect e WHERE e.release_id=r AND e.transition_id=t.transition_id),'[]'::jsonb)),'{}'::jsonb) INTO actual
 FROM sem.execution_transition t WHERE t.release_id=r AND t.operation_id=operation;
 IF actual IS DISTINCT FROM supported->'transitions' THEN
  RAISE EXCEPTION 'unsupported transition effects for %',operation USING ERRCODE='23514'; END IF;
END $operation$;
REVOKE ALL ON FUNCTION sem.require_execution_operation(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sem.require_execution_operation(text,text) TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION ops.execution_edge(r text,lifecycle text,prior text,result text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $edge$
 SELECT EXISTS(SELECT FROM sem.execution_edge e JOIN sem.execution_transition t USING(release_id,transition_id)
 WHERE e.release_id=$1 AND t.lifecycle=$2 AND e.prior_state=$3 AND e.result_state=$4)
$edge$;
REVOKE ALL ON FUNCTION ops.execution_edge(text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.execution_edge(text,text,text,text) TO corpus_sem_writer,corpus_sem_reader;

CREATE OR REPLACE FUNCTION ops.require_transition(r text,operation text,prior text,result text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $transition$
BEGIN
 PERFORM sem.require_execution_operation(r,operation);
 IF EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') AND NOT EXISTS(
  SELECT FROM sem.execution_edge e JOIN sem.execution_transition t USING(release_id,transition_id)
  WHERE e.release_id=r AND t.operation_id=operation AND e.prior_state=prior AND e.result_state=result) THEN
  RAISE EXCEPTION 'undeclared operation transition %: % -> %',operation,prior,result USING ERRCODE='23514'; END IF;
END $transition$;
REVOKE ALL ON FUNCTION ops.require_transition(text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.require_transition(text,text,text,text) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.start_source_run(p_run bigint) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $start$
DECLARE job ops.run;
BEGIN
 SELECT * INTO STRICT job FROM ops.run WHERE id=p_run FOR UPDATE;
 PERFORM sem.require_execution_operation(job.release_id,'execute_source');
 IF job.status='running' AND NOT job.sealed THEN RETURN job.id; END IF;
 IF job.status<>'created' OR job.sealed THEN RAISE EXCEPTION 'run no longer accepts source execution' USING ERRCODE='P0004'; END IF;
 PERFORM ops.require_transition(job.release_id,'execute_source','created','running');
 UPDATE ops.run SET status='running' WHERE id=job.id;
 RETURN job.id;
END $start$;
REVOKE ALL ON FUNCTION ops.start_source_run(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.start_source_run(bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.claim_tasks(p_run bigint,p_config bigint,p_holder text,p_limit bigint,p_agent boolean) RETURNS SETOF ops.task
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $claim$
DECLARE job ops.run;
BEGIN
 IF p_limit<1 OR nullif(p_holder,'') IS NULL THEN RAISE EXCEPTION 'positive claim limit and nonempty holder required'; END IF;
 SELECT * INTO STRICT job FROM ops.run WHERE id=p_run FOR SHARE;
 PERFORM sem.require_execution_operation(job.release_id,'claim');
 IF job.sealed OR job.status NOT IN ('created','running') THEN RETURN; END IF;
 RETURN QUERY WITH candidates AS MATERIALIZED (
  SELECT id FROM ops.task WHERE run_id=p_run AND method_config_id=p_config
   AND (status=CASE WHEN p_agent THEN 'awaiting_agent' ELSE 'pending' END OR (status='running' AND lease_until<clock_timestamp()))
  ORDER BY priority DESC,id LIMIT p_limit FOR UPDATE SKIP LOCKED
 ) UPDATE ops.task t SET status='running',attempt=t.attempt+1,claimed_by=p_holder,
  lease_until=clock_timestamp()+interval '5 minutes',started_at=COALESCE(t.started_at,clock_timestamp())
 FROM candidates c WHERE t.id=c.id RETURNING t.*;
END $claim$;
REVOKE ALL ON FUNCTION ops.claim_tasks(bigint,bigint,text,bigint,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.claim_tasks(bigint,bigint,text,bigint,boolean) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.lock_execution_run(p_run bigint,operation text) RETURNS ops.run
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $lock$
DECLARE job ops.run;
BEGIN
 SELECT * INTO STRICT job FROM ops.run WHERE id=p_run FOR SHARE;
 PERFORM sem.require_execution_operation(job.release_id,operation);
 RETURN job;
END $lock$;
REVOKE ALL ON FUNCTION ops.lock_execution_run(bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.lock_execution_run(bigint,text) TO corpus_sem_writer;

SET LOCAL ROLE __MIGRATION_OWNER__;
CREATE OR REPLACE FUNCTION ops.guard_execution_task() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE prior text; result text; agent boolean;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RETURN NEW; END IF;
 result:=ops.execution_task_state(NEW);
 SELECT (m.tier='agent' OR m.family='agent') INTO STRICT agent FROM ops.method_config c JOIN ops.method m ON m.id=c.method_id WHERE c.id=NEW.method_config_id;
 IF TG_OP='INSERT' THEN
  PERFORM sem.require_execution_operation(NEW.release_id,'schedule');
  IF NEW.status NOT IN ('pending','awaiting_agent','reused','skipped') OR NEW.attempt<>0 OR NEW.claimed_by IS NOT NULL OR NEW.lease_until IS NOT NULL
    OR result<>NEW.status THEN RAISE EXCEPTION 'invalid initial task combination' USING ERRCODE='23514'; END IF;
  IF NEW.status IN ('pending','awaiting_agent') AND (NEW.status='awaiting_agent')<>agent THEN
   RAISE EXCEPTION 'task channel differs from method contract' USING ERRCODE='23514'; END IF;
  IF NEW.status='skipped' AND nullif(NEW.reason,'') IS NULL THEN RAISE EXCEPTION 'skipped task requires reason' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 prior:=ops.execution_task_state(OLD);
 IF NEW.attempt IS DISTINCT FROM OLD.attempt THEN
  PERFORM ops.require_transition(NEW.release_id,'claim',prior,result);
 ELSIF NEW.status='awaiting_agent' AND OLD.status='running' THEN
  PERFORM ops.require_transition(NEW.release_id,'release_claim',prior,result);
 ELSIF NEW.status IN ('done','empty','failed') AND OLD.status='running' THEN
  PERFORM ops.require_transition(NEW.release_id,'complete',prior,result);
 ELSIF NEW.status='cancelled' AND OLD.status<>'cancelled' THEN
  PERFORM ops.require_transition(NEW.release_id,'end_run',prior,result);
 ELSIF prior<>result THEN
  PERFORM ops.require_transition(NEW.release_id,'hold_submission',prior,result);
 ELSIF NEW.lease_until IS DISTINCT FROM OLD.lease_until THEN
  PERFORM sem.require_execution_operation(NEW.release_id,'renew_claim');
 END IF;

 IF NEW.attempt IS DISTINCT FROM OLD.attempt THEN
  IF NEW.attempt<>OLD.attempt+1 OR NEW.status<>'running' OR nullif(NEW.claimed_by,'') IS NULL
    OR NEW.lease_until IS NULL OR NEW.lease_until<=clock_timestamp()
    OR (OLD.status='running' AND (OLD.lease_until IS NULL OR OLD.lease_until>=clock_timestamp()))
    OR NOT ops.execution_edge(NEW.release_id,'task',prior,result) THEN
   RAISE EXCEPTION 'invalid claim or reclaim ownership' USING ERRCODE='23514'; END IF;
 ELSIF NEW.claimed_by IS DISTINCT FROM OLD.claimed_by
  AND NOT(current_user='corpus_sem_publisher' AND NEW.status='awaiting_agent'
   AND NEW.claimed_by IS NULL AND ops.execution_edge(NEW.release_id,'task',prior,result)) THEN
  RAISE EXCEPTION 'holder mutation requires a new attempt' USING ERRCODE='23514';
 ELSIF prior<>result AND NOT ops.execution_edge(NEW.release_id,'task',prior,result) THEN
  RAISE EXCEPTION 'undeclared task transition % -> %',prior,result USING ERRCODE='23514';
 END IF;
 IF NEW.attempt=OLD.attempt AND NEW.lease_until IS DISTINCT FROM OLD.lease_until
  AND NEW.status='running' AND current_user<>'corpus_sem_publisher' THEN
  RAISE EXCEPTION 'lease renewal requires protected current ownership' USING ERRCODE='23514'; END IF;
 IF NEW.status IN ('done','empty','failed','cancelled') AND current_user<>'corpus_sem_publisher' THEN
  RAISE EXCEPTION 'terminal task effects require protected publication' USING ERRCODE='23514'; END IF;
 IF NEW.status IN ('done','empty','failed') AND NEW.result_digest IS NULL THEN
  RAISE EXCEPTION 'completed task requires an immutable result receipt' USING ERRCODE='23514'; END IF;
 IF NEW.status='failed' AND (NEW.error IS NULL OR jsonb_typeof(NEW.error)<>'object') THEN
  RAISE EXCEPTION 'failed task requires typed failure diagnostics' USING ERRCODE='23514'; END IF;
 IF OLD.error ? 'semantic_proposal_first_result' AND OLD.error->'semantic_proposal_first_result'
  IS DISTINCT FROM NEW.error->'semantic_proposal_first_result' THEN
  RAISE EXCEPTION 'held first result is immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.status<>'running' AND NEW.lease_until IS NOT NULL THEN
  RAISE EXCEPTION 'terminal task cannot retain a live lease' USING ERRCODE='23514'; END IF;
 IF NEW.status='running' AND (NEW.attempt<=0 OR nullif(NEW.claimed_by,'') IS NULL OR NEW.lease_until IS NULL) THEN
  RAISE EXCEPTION 'running task requires current attempt ownership' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION ops.guard_execution_run() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE prior text; result text;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RETURN NEW; END IF;
 IF TG_OP='INSERT' THEN
  PERFORM sem.require_execution_operation(NEW.release_id,'start_run');
  IF NEW.status<>'created' OR NEW.sealed OR NEW.result_realization_id IS NOT NULL THEN
   RAISE EXCEPTION 'invalid initial run combination' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 prior:=OLD.status || CASE WHEN OLD.status IN ('failed','cancelled') THEN CASE WHEN OLD.sealed THEN '_sealed' ELSE '_open' END ELSE '' END;
 result:=NEW.status || CASE WHEN NEW.status IN ('failed','cancelled') THEN CASE WHEN NEW.sealed THEN '_sealed' ELSE '_open' END ELSE '' END;
 IF prior<>result THEN
  PERFORM ops.require_transition(NEW.release_id,CASE WHEN NEW.status='running' THEN 'execute_source'
   WHEN NEW.status='consolidating' THEN 'capture_cut' WHEN NEW.status='finished' THEN 'evaluate' ELSE 'end_run' END,prior,result);
 END IF;

 IF prior<>result AND NOT ops.execution_edge(NEW.release_id,'run',prior,result) THEN
  RAISE EXCEPTION 'undeclared run transition % -> %',prior,result USING ERRCODE='23514'; END IF;
 IF NEW.status IN ('finished','failed','cancelled') THEN
  IF current_user<>'corpus_sem_publisher' THEN
   RAISE EXCEPTION 'terminal run effects require protected publication' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT 1 FROM ops.task WHERE run_id=NEW.id AND status IN ('pending','awaiting_agent','running')) THEN
   RAISE EXCEPTION 'terminal run requires all source tasks to be terminal' USING ERRCODE='23514'; END IF;
 END IF;
 IF NEW.sealed<>(NEW.status IN ('consolidating','finished') OR (NEW.status IN ('failed','cancelled') AND OLD.sealed)) THEN
  RAISE EXCEPTION 'invalid run sealing combination' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

REVOKE UPDATE(status) ON ops.run FROM corpus_sem_writer;
REVOKE UPDATE(status,attempt,claimed_by,lease_until,started_at,finished_at) ON ops.task FROM corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.guard_source_selection() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE bound ops.run; document bigint;
BEGIN
 bound := ops.lock_execution_run(NEW.run_id,'schedule');
 IF TG_TABLE_NAME='task' THEN
   IF TG_OP='UPDATE' AND NEW.trigger IS DISTINCT FROM OLD.trigger THEN
     RAISE EXCEPTION 'task routing provenance is immutable';
   END IF;
   IF NEW.unit_type<>'document' THEN RETURN NEW; END IF;
   document:=NEW.unit_id;
 ELSE document:=NEW.document_id;
 END IF;
 IF bound.options ? 'corpus' AND NOT EXISTS(
   SELECT 1 FROM kb.document d WHERE d.id=document AND d.project_id=bound.project_id
     AND bound.options->'corpus'->'documents' ? d.key
 ) THEN RAISE EXCEPTION 'source document is outside immutable declared corpus'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION ops.guard_task_lifecycle() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE bound ops.run;
BEGIN
 bound := ops.lock_execution_run(NEW.run_id,'schedule');
 IF TG_OP='UPDATE' AND OLD.status IN ('done','empty','failed','reused','skipped','cancelled') AND NEW IS DISTINCT FROM OLD THEN
   RAISE EXCEPTION 'terminal source task is immutable';
 END IF;
 IF (TG_OP='INSERT' OR NEW.status IS DISTINCT FROM OLD.status) AND (bound.sealed OR bound.status IN ('finished','failed','cancelled'))
 AND NOT(TG_OP='UPDATE' AND current_user='corpus_sem_publisher' AND NEW.status IN ('failed','cancelled')) THEN
   RAISE EXCEPTION 'task run is closed';
 END IF;
 IF TG_OP='UPDATE' AND (OLD.run_id,OLD.release_id,OLD.method_config_id,OLD.input_hash,OLD.packet_hash,OLD.unit_type,OLD.unit_id,OLD.unit_key,OLD.invocation_key)
 IS DISTINCT FROM (NEW.run_id,NEW.release_id,NEW.method_config_id,NEW.input_hash,NEW.packet_hash,NEW.unit_type,NEW.unit_id,NEW.unit_key,NEW.invocation_key) THEN
   RAISE EXCEPTION 'task inputs are immutable';
 END IF;
 IF NEW.status IN ('done','empty') AND current_user<>'corpus_sem_publisher' THEN RAISE EXCEPTION 'successful source completion requires protected result publication'; END IF;
 IF NEW.status='reused' AND NEW.reused_task_id IS NULL THEN RAISE EXCEPTION 'reuse requires a completed origin'; END IF;
 IF NOT ops.valid_reuse(NEW) THEN RAISE EXCEPTION 'reuse origin has another bound source context'; END IF;
 IF NEW.unit_type='document' AND NOT EXISTS(SELECT 1 FROM kb.document WHERE id=NEW.unit_id AND project_id=bound.project_id) THEN
   RAISE EXCEPTION 'task document is outside bound project';
 ELSIF NEW.unit_type='rendition' AND NOT EXISTS(SELECT 1 FROM ops.run_rendition WHERE run_id=NEW.run_id AND rendition_id=NEW.unit_id) THEN
   RAISE EXCEPTION 'task rendition is outside bound run';
 ELSIF NEW.unit_type='segment' AND NOT EXISTS(SELECT 1 FROM kb.segment s JOIN ops.run_rendition rr ON rr.rendition_id=s.rendition_id WHERE rr.run_id=NEW.run_id AND s.id=NEW.unit_id) THEN
   RAISE EXCEPTION 'task segment is outside bound run';
 END IF;
 RETURN NEW;
END $$;

SET LOCAL ROLE corpus_sem_publisher;
