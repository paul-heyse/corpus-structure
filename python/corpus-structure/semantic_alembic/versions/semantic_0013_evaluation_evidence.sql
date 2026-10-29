-- SourceObservation uses the declared lossless source-value shape. The scalar subquery refuses
-- duplicate members rather than silently choosing one; no heuristic JSON search locates evidence.
CREATE FUNCTION data.report_field(value jsonb,member text) RETURNS jsonb LANGUAGE sql IMMUTABLE
RETURNS NULL ON NULL INPUT SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT (SELECT field->'value' FROM jsonb_array_elements(value->'fields') field
         WHERE field->>'name'=member) WHERE value->>'kind'='object'
$fn$;
REVOKE ALL ON FUNCTION data.report_field(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.check_evidence_source() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE observation kb.observation; ev data.evidence; span kb.span; method_name text;
 operation_version text; uri text; matched boolean; synthesis jsonb;
BEGIN
 SELECT * INTO STRICT observation FROM kb.observation WHERE id=NEW.observation_id;
 IF observation.release_id<>NEW.release_id OR observation.rendition_id IS DISTINCT FROM NEW.rendition_id THEN
  RAISE EXCEPTION 'evidence source differs from bound observation'; END IF;
 SELECT m.name,m.version,d.source_uri INTO STRICT method_name,operation_version,uri
  FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id
  JOIN ops.method m ON m.id=c.method_id JOIN kb.rendition r ON r.id=NEW.rendition_id
  JOIN kb.document d ON d.id=r.document_id WHERE t.id=observation.task_id;
 SELECT * INTO STRICT ev FROM data.evidence WHERE evidence_id=NEW.evidence_id
  AND release_id=NEW.release_id AND realization_id=NEW.realization_id;
 IF ev.source_uri<>uri OR ev.provider<>method_name OR ev.operation_version<>operation_version THEN
  RAISE EXCEPTION 'evidence provider/source differs from bound observation'; END IF;
 IF NEW.span_id IS NULL THEN
  IF observation.span_id IS NOT NULL THEN RAISE EXCEPTION 'evidence omitted bound source span'; END IF;
  RETURN NEW;
 END IF;
 IF observation.span_id IS NOT NULL THEN
  IF observation.span_id<>NEW.span_id THEN RAISE EXCEPTION 'evidence span differs from bound observation'; END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO STRICT span FROM kb.span WHERE id=NEW.span_id AND rendition_id=NEW.rendition_id;
 matched:=false;
 IF observation.payload_definition='AgentStoredBatch' THEN
  SELECT EXISTS(SELECT FROM jsonb_array_elements(
      COALESCE(observation.payload->'claims','[]'::jsonb)||COALESCE(observation.payload->'unsupported','[]'::jsonb)) item
      CROSS JOIN LATERAL jsonb_array_elements(item->'evidence') citation
      WHERE citation->>'outcome'='located' AND (citation->>'start')::bigint=span.start_offset
       AND (citation->>'end')::bigint=span.end_offset) INTO matched;
 ELSIF observation.payload_definition='SourceObservation' AND observation.kind='author_markup' THEN
  synthesis:=data.report_field(observation.payload->'payload','synthesize');
  SELECT EXISTS(SELECT FROM jsonb_array_elements(data.report_field(synthesis,'evidence')->'items') citation
    WHERE (data.report_field(citation,'start')->>'integer')::bigint=span.start_offset
      AND (data.report_field(citation,'end')->>'integer')::bigint=span.end_offset) INTO matched;
 END IF;
 IF NOT matched THEN RAISE EXCEPTION 'evidence span is not a located citation in bound source report'; END IF;
 RETURN NEW;
END $fn$;
ALTER FUNCTION data.check_evidence_source() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.check_evidence_source() FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.finish_evaluation(p_cut bigint,p_output text,p_batch text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE cut ops.input_cut; job ops.run;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN
  RAISE EXCEPTION 'evaluation publication requires SERIALIZABLE'; END IF;
 SELECT * INTO STRICT cut FROM ops.input_cut WHERE id=p_cut;
 SELECT * INTO STRICT job FROM ops.run WHERE id=cut.run_id FOR UPDATE;
 IF NOT cut.final OR NOT job.sealed OR job.status NOT IN ('consolidating','finished') OR
    job.result_realization_id IS DISTINCT FROM p_output THEN
  RAISE EXCEPTION 'evaluation run fence changed'; END IF;
 IF NOT EXISTS(SELECT FROM data.realization WHERE realization_id=p_output AND release_id=job.release_id AND project_id=job.project_id AND realization_id<>job.input_realization_id AND state='active') THEN RAISE EXCEPTION 'output realization differs from bound run'; END IF;
 IF NOT EXISTS(SELECT FROM data.batch WHERE realization_id=p_output AND release_id=job.release_id
  AND batch_id=p_batch) THEN RAISE EXCEPTION 'evaluation result has no admitted receipt'; END IF;
 IF EXISTS(SELECT FROM data.occurrence o WHERE o.release_id=job.release_id AND o.realization_id=p_output
  AND NOT EXISTS(SELECT FROM data.occurrence_evidence oe JOIN data.evidence_source es
    ON (es.release_id,es.realization_id,es.evidence_id)=(oe.release_id,oe.realization_id,oe.evidence_id)
    JOIN kb.observation observation ON observation.id=es.observation_id
    JOIN ops.cut_task ct ON ct.origin_task_id=observation.task_id AND ct.cut_id=p_cut
    WHERE (oe.release_id,oe.realization_id,oe.occurrence_id)=(o.release_id,o.realization_id,o.occurrence_id)
      AND es.span_id IS NOT NULL)) THEN
  RAISE EXCEPTION 'source occurrence has no located evidence in sealed cut'; END IF;
 IF EXISTS(SELECT FROM data.occurrence o JOIN data.occurrence_evidence oe
   ON (oe.release_id,oe.realization_id,oe.occurrence_id)=(o.release_id,o.realization_id,o.occurrence_id)
   JOIN data.evidence_source es ON (es.release_id,es.realization_id,es.evidence_id)=
    (oe.release_id,oe.realization_id,oe.evidence_id)
   JOIN kb.observation observation ON observation.id=es.observation_id
   WHERE o.release_id=job.release_id AND o.realization_id=p_output AND
   NOT EXISTS(SELECT FROM ops.cut_task ct WHERE ct.cut_id=p_cut AND ct.origin_task_id=observation.task_id)) THEN
  RAISE EXCEPTION 'evaluation evidence is outside sealed observation cut'; END IF;
 UPDATE ops.run SET result_realization_id=p_output,status='finished' WHERE id=job.id;
END $fn$;

CREATE FUNCTION data.end_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_entity' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_entity'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_membership' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','establishment:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_membership'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_typed_value' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['value_id:text','kind:text','text_value:text','integer_value:numeric','numeric_value:numeric','decimal_lexical:text','boolean_value:boolean','entity_id:text','language:text','datatype:text','opaque_payload:jsonb']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_typed_value'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_value_role' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['parent_value_id:text','role:text','position:bigint','child_value_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_value_role'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_fact' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','subject_id:text','property_id:text','object_value_id:text','qualification_value_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_fact'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_occurrence' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','fact_id:text','source:text','item:text','report_object_value_id:text','report_qualification_value_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_occurrence'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_support' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','occurrence_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_support'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_selection' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','selected:boolean']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_selection'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_evidence' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','source_uri:text','locator:text','provider:text','operation_version:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_evidence'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_occurrence_evidence' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','evidence_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_occurrence_evidence'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_membership_support' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','evidence_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_membership_support'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_derivation' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','conclusion_fact_id:text','rule:text','rule_version:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_derivation'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_derivation_premise' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','position:bigint','premise_fact_id:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_derivation_premise'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_coverage' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['coverage_id:text','family:text','scope:text','outcome:text','reason:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_coverage'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_occurrence_establishment' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','establishment:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_occurrence_establishment'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_evidence_source' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','observation_id:bigint','rendition_id:bigint','span_id:bigint']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_evidence_source'; END IF;
 IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema()
   AND c.relname='sp_assessment' AND c.relkind='r' AND c.relpersistence='t'
   AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
   AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['assessment_id:text','operation_id:text','operation_version:text','outcome:text','fact_id:text','occurrence_id:text','confidence:numeric','reason:text','uncertainty:text']) THEN
  RAISE EXCEPTION 'untrusted staging relation sp_assessment'; END IF;
 DROP TABLE pg_temp.sp_entity;
 DROP TABLE pg_temp.sp_membership;
 DROP TABLE pg_temp.sp_typed_value;
 DROP TABLE pg_temp.sp_value_role;
 DROP TABLE pg_temp.sp_fact;
 DROP TABLE pg_temp.sp_occurrence;
 DROP TABLE pg_temp.sp_support;
 DROP TABLE pg_temp.sp_selection;
 DROP TABLE pg_temp.sp_evidence;
 DROP TABLE pg_temp.sp_occurrence_evidence;
 DROP TABLE pg_temp.sp_membership_support;
 DROP TABLE pg_temp.sp_derivation;
 DROP TABLE pg_temp.sp_derivation_premise;
 DROP TABLE pg_temp.sp_coverage;
 DROP TABLE pg_temp.sp_occurrence_establishment;
 DROP TABLE pg_temp.sp_evidence_source;
 DROP TABLE pg_temp.sp_assessment;
END $fn$;
ALTER FUNCTION data.end_stage() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.end_stage() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.end_stage() TO corpus_sem_writer;
