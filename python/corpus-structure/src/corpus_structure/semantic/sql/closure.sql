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
 names constant text[]:=ARRAY[{intrinsic_relations}];
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
DECLARE bound text; model jsonb;
BEGIN
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row
 WHERE release_id=r AND kind='effective_bindings' AND name='effective-bindings-11';
 IF model IS NOT NULL THEN bound:=model->'statement'->>'class_iri';
 ELSE RAISE EXCEPTION 'missing current resolved statement binding' USING ERRCODE='23514';
 END IF;
 RETURN bound IS NOT NULL AND EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND class_id=bound)
  AND (c=bound OR EXISTS(SELECT FROM sem.class_hierarchy WHERE release_id=r AND class_id=c AND ancestor_id=bound));
END
$body$;

CREATE OR REPLACE FUNCTION data.check_evidence_source() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE observation kb.observation; ev data.evidence; method_name text;
 operation_version text; uri text; matched boolean;
 native_view kb.source_view; native_frame ops.native_source_frame; native_source ops.native_source_frame_source; address jsonb; first_offset bigint; last_offset bigint;
BEGIN
 SELECT * INTO STRICT observation FROM kb.observation WHERE id=NEW.observation_id;
 IF NEW.source_view_id IS NOT NULL OR observation.source_view_id IS NOT NULL THEN
  IF observation.release_id IS DISTINCT FROM NEW.release_id OR
   observation.source_view_id IS NULL OR
   NEW.rendition_id IS NOT NULL OR NEW.span_id IS NOT NULL OR observation.rendition_id IS NOT NULL OR
   observation.payload_definition<>'AgentStoredBatch' OR NEW.native_address IS NULL THEN
   RAISE EXCEPTION 'native evidence source differs from its bound observation' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT native_view FROM kb.source_view WHERE id=NEW.source_view_id;
  SELECT f.* INTO STRICT native_frame FROM ops.native_source_frame f JOIN ops.task t ON t.id=f.task_id
   AND t.packet_hash=f.packet_hash AND t.unit_key=f.unit_ref WHERE f.task_id=observation.task_id;
  SELECT * INTO STRICT native_source FROM ops.native_source_frame_source
   WHERE task_id=observation.task_id AND source_view_id=native_view.id;
  IF native_view.release_id IS DISTINCT FROM observation.release_id OR
   native_frame.source_view_id IS DISTINCT FROM observation.source_view_id OR
   native_source.product_task_id IS DISTINCT FROM native_view.native_task_id OR
   native_source.product_key IS DISTINCT FROM native_view.native_product_key OR
   native_source.product_digest IS DISTINCT FROM native_view.native_content_digest OR
   native_source.projection_digest IS DISTINCT FROM native_view.projection_digest OR
   native_source.recipe_digest IS DISTINCT FROM native_view.recipe_digest OR
   native_frame.unit_ref IS DISTINCT FROM observation.payload->>'unit_ref' THEN
   RAISE EXCEPTION 'native evidence frame differs from selected source custody' USING ERRCODE='23514'; END IF;
  SELECT m.name,m.version,d.source_uri INTO STRICT method_name,operation_version,uri
   FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id
   JOIN kb.document d ON d.id=native_view.document_id WHERE t.id=observation.task_id;
  SELECT * INTO STRICT ev FROM data.evidence WHERE evidence_id=NEW.evidence_id
   AND release_id=NEW.release_id AND realization_id=NEW.realization_id;
  IF (ev.source_uri,ev.provider,ev.operation_version) IS DISTINCT FROM (uri,method_name,operation_version) THEN
   RAISE EXCEPTION 'native evidence provider/source differs from bound observation' USING ERRCODE='23514'; END IF;
  address:=substring(ops.native_source_address(native_view.id,NEW.native_address) FROM 5)::jsonb;
  IF NOT(address ? 'source_view_id') THEN
   RAISE EXCEPTION 'native evidence requires an exact projected quote range' USING ERRCODE='23514'; END IF;
  first_offset:=(address->>'start')::bigint;last_offset:=(address->>'end')::bigint;
  SELECT EXISTS(SELECT FROM jsonb_array_elements(
    COALESCE(observation.payload->'claims','[]'::jsonb)||COALESCE(observation.payload->'unsupported','[]'::jsonb)||
    COALESCE(observation.payload->'identity_exclusions','[]'::jsonb)||
    COALESCE((SELECT jsonb_agg(attribute) FROM jsonb_array_elements(COALESCE(observation.payload->'entities','[]')) entity
      CROSS JOIN LATERAL jsonb_array_elements(COALESCE(entity->'attributes','[]')) attribute),'[]'::jsonb)) item
   CROSS JOIN LATERAL jsonb_array_elements(item->'evidence') citation
   JOIN ops.native_source_frame_sentence supplied ON supplied.task_id=observation.task_id
    AND supplied.source_view_id=native_view.id AND supplied.sentence_id=citation->>'sentence' AND supplied.locator=citation->>'locator'
   WHERE citation->>'outcome'='located' AND (citation->>'start')::bigint=first_offset
    AND (citation->>'end')::bigint=last_offset AND supplied.start_offset<=first_offset AND supplied.end_offset>=last_offset
    AND substring(native_view.projection->>'text' FROM first_offset::integer+1 FOR (last_offset-first_offset)::integer)
     =citation->>'quote'
    AND ev.locator::jsonb=jsonb_build_object('locator',citation->'locator','start',first_offset,'end',last_offset,'role',citation->'role'))
   INTO matched;
  IF NOT matched THEN RAISE EXCEPTION 'native evidence differs from a located supplied citation' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 RAISE EXCEPTION 'evidence requires current SourceView custody' USING ERRCODE='23514';
END $fn$;

CREATE OR REPLACE FUNCTION data.end_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
{transport_disposal}
END
$body$;

CREATE OR REPLACE FUNCTION data.validate_occurrence_context(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE o data.occurrence; context data.occurrence_context; observation kb.observation;
 edge data.occurrence_evidence; citation_role data.occurrence_evidence_role;
 source data.evidence_source; claim jsonb; statement jsonb; expected_statement text;
 expected_role text; source_rendition_key text; synthesis jsonb; attribute jsonb; declaration jsonb; attribute_index integer; src data.entity_source; establishment text;
BEGIN
 IF EXISTS(SELECT FROM data.occurrence_establishment e
  WHERE e.release_id=r AND e.realization_id=z
   AND EXISTS(SELECT FROM sem.vocabulary_member v WHERE v.release_id=r AND v.vocabulary_id='Establishment')
   AND NOT EXISTS(SELECT FROM sem.registry_row contract
    WHERE contract.release_id=r AND contract.kind='semantic_contract' AND contract.name='released-semantics-1'
     AND (convert_from(contract.body,'UTF8')::jsonb->'source_establishments') ? e.establishment)) THEN
  RAISE EXCEPTION 'source establishment is outside released source-admissible subset' USING ERRCODE='23514'; END IF;
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
    IF observation.source_view_id IS NOT NULL THEN
     IF NOT EXISTS(SELECT FROM ops.native_source_frame f WHERE f.task_id=observation.task_id
       AND f.source_view_id=observation.source_view_id AND f.unit_ref=observation.payload->>'unit_ref') THEN
      RAISE EXCEPTION 'native statement differs from its primary source frame' USING ERRCODE='23514'; END IF;
     source_rendition_key:=ops.native_source_statement_source_key(observation.task_id,statement->>'anchor');
     expected_statement:='entity:'||encode(sha256(convert_to(data.canonical_json(
      jsonb_build_array(r,z,'source-statement',source_rendition_key,
                       ops.native_source_statement_locator(observation.task_id,statement->>'anchor'))),'UTF8')),'hex');
    ELSE
     RAISE EXCEPTION 'statement requires current SourceView custody' USING ERRCODE='23514';
    END IF;
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
  ELSIF observation.payload_definition='AgentStoredBatch' AND o.item LIKE 'entities/%/attributes/%' THEN
   SELECT source.* INTO STRICT src FROM data.entity_source source
    JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.fact_id=o.fact_id AND f.subject_id=source.entity_id
    WHERE source.release_id=r AND source.realization_id=z AND source.observation_id=observation.id
     AND starts_with(o.item,'entities/'||source.local_id||'/attributes/');
   SELECT value INTO STRICT declaration FROM jsonb_array_elements(observation.payload->'entities') WHERE value->>'id'=src.local_id;
   attribute_index:=substring(o.item FROM length('entities/'||src.local_id||'/attributes/')+1)::integer;
   attribute:=declaration->'attributes'->attribute_index;
   SELECT e.establishment INTO establishment FROM data.occurrence_establishment e
    WHERE e.release_id=r AND e.realization_id=z AND e.occurrence_id=o.occurrence_id;
   IF attribute IS NULL OR attribute_index<0 OR context.occurrence_id IS NOT NULL OR
    attribute->>'establishment' IS DISTINCT FROM establishment OR
    NOT EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND f.fact_id=o.fact_id
      AND f.subject_id=src.entity_id AND f.property_id=attribute->>'predicate') THEN
    RAISE EXCEPTION 'attribute occurrence differs from its own source assertion' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM jsonb_array_elements(attribute->'evidence') WITH ORDINALITY citation(value,position)
     WHERE citation.value->>'outcome'='located' AND NOT EXISTS(
      SELECT FROM data.occurrence_evidence support
      WHERE support.release_id=r AND support.realization_id=z AND support.occurrence_id=o.occurrence_id
       AND support.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
         o.source,'entities',src.local_id,'attributes',attribute_index,citation.position-1,citation.value)),'UTF8')),'hex'))) THEN
    RAISE EXCEPTION 'attribute support differs from its own source evidence' USING ERRCODE='23514'; END IF;
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
   IF o.item LIKE 'entities/%/attributes/%' THEN
    SELECT citation.value->>'role' INTO expected_role
    FROM data.entity_source src
    JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.fact_id=o.fact_id AND f.subject_id=src.entity_id
    CROSS JOIN LATERAL jsonb_array_elements(observation.payload->'entities') entity
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(entity->'attributes','[]')) WITH ORDINALITY attr(value,position)
    CROSS JOIN LATERAL jsonb_array_elements(attr.value->'evidence') WITH ORDINALITY citation(value,position)
    WHERE src.release_id=r AND src.realization_id=z AND src.observation_id=observation.id
     AND entity->>'id'=src.local_id
     AND o.item='entities/'||src.local_id||'/attributes/'||(attr.position-1)::text
     AND f.property_id=attr.value->>'predicate' AND citation.value->>'outcome'='located'
     AND edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,'entities',src.local_id,'attributes',attr.position-1,citation.position-1,citation.value)),'UTF8')),'hex');
   ELSE
    SELECT citation.value->>'role' INTO expected_role
    FROM jsonb_array_elements(observation.payload->'claims') WITH ORDINALITY candidate(value,position)
    CROSS JOIN LATERAL jsonb_array_elements(candidate.value->'evidence') WITH ORDINALITY citation(value,position)
    WHERE citation.value->>'outcome'='located'
     AND (o.item !~ '^claims/[0-9]+$' OR candidate.position-1=split_part(o.item,'/',2)::integer)
     AND edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,'claims',candidate.position-1,citation.position-1,citation.value)),'UTF8')),'hex');
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
 IF archived.profile NOT IN ('semantic-1','semantic-2') OR document->>'format' IS DISTINCT FROM 'semantic-release-archive-3'
 OR COALESCE(manifest->'profile'->>'compiler_version','') NOT IN ('14','15','16')
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

-- {immutability_guards}

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
CREATE TRIGGER native_float_codec BEFORE INSERT ON data.typed_value FOR EACH ROW EXECUTE FUNCTION data.guard_float_codec();

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
  {typed_value_stage_verify}
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
 IF a.constraints->>'structural_identifier'='true' THEN
  IF EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND f.subject_id=a.entity_id
   AND f.property_id=a.property_id AND data.value_meaning(r,z,f.object_value_id)<>jsonb_build_array('string',a.entity_id)) THEN
   RAISE EXCEPTION 'structural identifier contradicts assigned entity identity' USING ERRCODE='23514'; END IF;
  CONTINUE;
 END IF;
 SELECT count(DISTINCT data.canonical_json(data.value_meaning(r,z,f.object_value_id))) INTO n FROM data.fact f
 WHERE f.release_id=r AND f.realization_id=z AND f.subject_id=a.entity_id AND f.property_id=a.property_id
 AND (a.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection s WHERE (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id)));
 IF n<COALESCE(a.minimum_cardinality,CASE WHEN a.required THEN 1 ELSE 0 END) OR n>COALESCE(a.maximum_cardinality,CASE WHEN a.multivalued THEN 9223372036854775807 ELSE 1 END) THEN RAISE EXCEPTION 'property cardinality %/%',a.entity_id,a.property_id USING ERRCODE='23514'; END IF;
 END LOOP;
 -- Identity groups use each declared member, with admitted case policy and complete scope.
 IF EXISTS(
 WITH key_parts AS (
 SELECT m.entity_id,m.class_id,i.group_id,i.position,
 count(DISTINCT data.canonical_json(CASE WHEN pa.constraints->>'structural_identifier'='true' THEN jsonb_build_array('string',m.entity_id) WHEN pa.constraints->>'case_policy'='casefold' AND tv.kind='string' THEN jsonb_build_array('string',casefold(tv.text_value COLLATE pg_catalog.pg_unicode_fast)) ELSE data.value_meaning(r,z,f.object_value_id) END)) AS count_values,
 min(data.canonical_json(CASE WHEN pa.constraints->>'structural_identifier'='true' THEN jsonb_build_array('string',m.entity_id) WHEN pa.constraints->>'case_policy'='casefold' AND tv.kind='string' THEN jsonb_build_array('string',casefold(tv.text_value COLLATE pg_catalog.pg_unicode_fast)) ELSE data.value_meaning(r,z,f.object_value_id) END)) AS part
 FROM data.membership m JOIN sem.identity_slot i ON i.release_id=r AND i.class_id=m.class_id
 JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=i.class_id AND pa.property_id=i.property_id
 LEFT JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.subject_id=m.entity_id AND f.property_id=i.property_id AND (pa.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection sel WHERE (sel.release_id,sel.realization_id,sel.fact_id)=(f.release_id,f.realization_id,f.fact_id)))
 LEFT JOIN data.typed_value tv ON (tv.release_id,tv.realization_id,tv.value_id)=(f.release_id,f.realization_id,f.object_value_id)
 WHERE m.release_id=r AND m.realization_id=z GROUP BY m.entity_id,m.class_id,i.group_id,i.position),
 keys AS(SELECT entity_id,class_id,group_id,string_agg(part,',' ORDER BY position) AS value,bool_and(count_values=1) AS complete FROM key_parts GROUP BY entity_id,class_id,group_id)
 SELECT FROM keys GROUP BY class_id,group_id,value HAVING count(*)>1 OR NOT bool_and(complete)
 ) THEN RAISE EXCEPTION 'missing, multivalued or nonunique entity identity' USING ERRCODE='23514'; END IF;
END $fn$;

CREATE OR REPLACE FUNCTION data.validate_entity_source(r text,z text) RETURNS void LANGUAGE plpgsql STABLE
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE source data.entity_source; observation kb.observation; declaration jsonb; decision data.entity_resolution; policy jsonb; provisional text; declaration_ordinal bigint;
BEGIN
 FOR source IN SELECT * FROM data.entity_source WHERE release_id=r AND realization_id=z LOOP
  SELECT * INTO STRICT observation FROM kb.observation WHERE id=source.observation_id;
  IF observation.payload_definition<>'AgentStoredBatch' THEN
   RAISE EXCEPTION 'entity source is not a released agent entity declaration' USING ERRCODE='23514'; END IF;
  SELECT value INTO declaration FROM jsonb_array_elements(observation.payload->'entities')
   WHERE value->>'id'=source.local_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'entity source local id is outside source declarations' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM data.membership existing WHERE existing.release_id=r AND existing.realization_id=z AND existing.entity_id=source.entity_id) AND NOT EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z
    AND m.entity_id=source.entity_id AND (m.class_id=declaration->>'class_iri' OR EXISTS(
      SELECT FROM sem.class_hierarchy h WHERE h.release_id=r AND h.class_id=m.class_id
       AND h.ancestor_id=declaration->>'class_iri'))) THEN
   RAISE EXCEPTION 'entity source class is incompatible with published membership' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM ops.run job JOIN ops.input_cut cut ON cut.run_id=job.id AND cut.final
    JOIN ops.cut_task task ON task.cut_id=cut.id AND task.origin_task_id=observation.task_id
    WHERE job.release_id=r AND job.result_realization_id=z AND job.sealed
     AND job.status IN ('consolidating','finished')) THEN
   RAISE EXCEPTION 'entity source is outside the bound final observation cut' USING ERRCODE='23514'; END IF;
  SELECT * INTO decision FROM data.entity_resolution d WHERE d.release_id=r AND d.realization_id=z
   AND d.observation_id=source.observation_id AND d.local_id=source.local_id;
  IF NOT FOUND OR decision.entity_id<>source.entity_id OR decision.operation_id<>'resolve_identity' THEN
   RAISE EXCEPTION 'entity source lacks its typed resolution decision' USING ERRCODE='23514'; END IF;
  SELECT operation.value INTO policy FROM sem.registry_row model
   CROSS JOIN LATERAL jsonb_array_elements(convert_from(model.body,'UTF8')::jsonb->'operations') operation(value)
   WHERE model.release_id=r AND model.kind='execution_model' AND operation.value->>'id'='resolve_identity';
  IF decision.operation_version IS DISTINCT FROM policy->>'policy_version' OR
   jsonb_typeof(decision.candidates::jsonb)<>'array' OR jsonb_typeof(decision.dependencies::jsonb)<>'array' OR
   jsonb_typeof(decision.key_policy::jsonb)<>'object' THEN
   RAISE EXCEPTION 'resolution decision differs from its released operation' USING ERRCODE='23514'; END IF;
  SELECT position-1 INTO STRICT declaration_ordinal
   FROM jsonb_array_elements(observation.payload->'entities') WITH ORDINALITY entity(value,position)
   WHERE value->>'id'=source.local_id;
  provisional:='entity:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
    r,z,observation.observation_key,'entities',declaration_ordinal,source.local_id)),'UTF8')),'hex');
  IF (decision.basis='source_local' OR decision.outcome<>'resolved') AND decision.entity_id<>provisional THEN
   RAISE EXCEPTION 'provisional identity falsely claims global resolution' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM data.entity_resolution decision WHERE decision.release_id=r AND decision.realization_id=z
   AND NOT EXISTS(SELECT FROM data.entity_source source WHERE source.release_id=r AND source.realization_id=z
    AND source.observation_id=decision.observation_id AND source.local_id=decision.local_id AND source.entity_id=decision.entity_id)) THEN
  RAISE EXCEPTION 'resolution decision lacks its source declaration' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.scientific_representative rep WHERE rep.release_id=r AND rep.realization_id=z
   AND (rep.policy_id<>'min-fact-id-1' OR NOT EXISTS(SELECT FROM data.selection selected WHERE
     selected.release_id=r AND selected.realization_id=z AND selected.fact_id=rep.fact_id) OR
    NOT EXISTS(SELECT FROM data.selection selected WHERE selected.release_id=r AND selected.realization_id=z
     AND selected.fact_id=rep.representative_fact_id) OR rep.representative_fact_id IS DISTINCT FROM
      (SELECT min(member.fact_id COLLATE "C") FROM data.scientific_representative member
       WHERE member.release_id=r AND member.realization_id=z AND member.component_id=rep.component_id))) THEN
  RAISE EXCEPTION 'scientific representative differs from accepted component minimum' USING ERRCODE='23514'; END IF;
END $fn$;

CREATE OR REPLACE FUNCTION eval.create_reference_set(p_project text,p_release text,p_run bigint,p_label text,p_split text,p_guideline text,p_sampling jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint;
BEGIN
 IF NOT EXISTS(SELECT FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id WHERE c.run_id=p_run AND r.project_id=p_project AND c.release_id=p_release) THEN RAISE EXCEPTION 'reference source result binding differs' USING ERRCODE='23514'; END IF;
 PERFORM data.require_execution_release(p_release);
 IF NOT EXISTS(SELECT FROM sem.registry_row contract WHERE contract.release_id=p_release
 AND contract.kind='semantic_contract' AND contract.name='released-semantics-1'
 AND (convert_from(contract.body,'UTF8')::jsonb->'executable_reference_splits') ? p_split) THEN
 RAISE EXCEPTION 'reference split unavailable for executable reference sets' USING ERRCODE='23514'; END IF;
 IF p_label='' OR p_guideline='' OR jsonb_typeof(p_sampling)<>'object' THEN RAISE EXCEPTION 'incomplete reference definition' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_set(project_id,release_id,source_run_id,label,split,guideline,sampling) VALUES(p_project,p_release,p_run,p_label,p_split,p_guideline,p_sampling) RETURNING id INTO result;
 RETURN result;
END $body$;
