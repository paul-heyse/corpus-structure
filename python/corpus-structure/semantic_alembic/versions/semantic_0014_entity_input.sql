
CREATE TABLE data.entity_input (
	realization_id TEXT NOT NULL, 
	release_id TEXT NOT NULL, 
	entity_id TEXT NOT NULL, 
	input_realization_id TEXT NOT NULL, 
	input_data_revision BIGINT NOT NULL, 
	input_entity_id TEXT NOT NULL, 
	run_id BIGINT NOT NULL, 
	CONSTRAINT fk_entity_input_realization_id_release_id FOREIGN KEY (realization_id, release_id) REFERENCES data.realization (realization_id, release_id),
	CONSTRAINT pk_entity_input PRIMARY KEY (realization_id, release_id, entity_id), 
	CONSTRAINT fk_entity_input_realization_id_release_id_entity_id FOREIGN KEY(realization_id, release_id, entity_id) REFERENCES data.entity (realization_id, release_id, entity_id), 
	CONSTRAINT fk_entity_input_input_realization_id_release_id_input_entity_id FOREIGN KEY(input_realization_id, release_id, input_entity_id) REFERENCES data.entity (realization_id, release_id, entity_id), 
	CONSTRAINT fk_entity_input_run_id FOREIGN KEY(run_id) REFERENCES ops.run (id), 
	CONSTRAINT ck_entity_input_physical_ed2a159c88 CHECK (input_data_revision >= 0), 
	CONSTRAINT ck_entity_input_physical_c3379ef8c3 CHECK (realization_id <> input_realization_id)
)

;
ALTER TABLE data.entity_input OWNER TO corpus_sem_publisher;

CREATE TABLE data.fact_input (
	realization_id TEXT NOT NULL, 
	release_id TEXT NOT NULL, 
	fact_id TEXT NOT NULL, 
	input_realization_id TEXT NOT NULL, 
	input_data_revision BIGINT NOT NULL, 
	input_fact_id TEXT NOT NULL, 
	run_id BIGINT NOT NULL, 
	CONSTRAINT fk_fact_input_realization_id_release_id FOREIGN KEY (realization_id, release_id) REFERENCES data.realization (realization_id, release_id),
	CONSTRAINT pk_fact_input PRIMARY KEY (realization_id, release_id, fact_id), 
	CONSTRAINT fk_fact_input_realization_id_release_id_fact_id FOREIGN KEY(realization_id, release_id, fact_id) REFERENCES data.fact (realization_id, release_id, fact_id), 
	CONSTRAINT fk_fact_input_input_realization_id_release_id_input_fact_id FOREIGN KEY(input_realization_id, release_id, input_fact_id) REFERENCES data.fact (realization_id, release_id, fact_id), 
	CONSTRAINT fk_fact_input_run_id FOREIGN KEY(run_id) REFERENCES ops.run (id), 
	CONSTRAINT ck_fact_input_physical_ed2a159c88 CHECK (input_data_revision >= 0), 
	CONSTRAINT ck_fact_input_physical_c3379ef8c3 CHECK (realization_id <> input_realization_id)
)

;
ALTER TABLE data.fact_input OWNER TO corpus_sem_publisher;
-- Publisher-owned routines
GRANT SELECT ON data.entity_input,data.fact_input TO corpus_sem_writer,corpus_sem_reader;
CREATE FUNCTION data.check_entity_input() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE job ops.run; source data.realization;
BEGIN
 SELECT * INTO STRICT job FROM ops.run WHERE id=NEW.run_id;
 SELECT * INTO STRICT source FROM data.realization WHERE realization_id=NEW.input_realization_id;
 IF job.release_id<>NEW.release_id OR job.result_realization_id IS DISTINCT FROM NEW.realization_id
  OR job.input_realization_id<>NEW.input_realization_id OR job.input_revision<>NEW.input_data_revision
  OR source.release_id<>NEW.release_id OR source.data_revision<>NEW.input_data_revision
  OR job.status NOT IN ('consolidating','finished') OR NOT job.sealed THEN
  RAISE EXCEPTION 'entity input differs from bound evaluation input'; END IF;
 RETURN NEW;
END $fn$;
CREATE TRIGGER entity_input_guard BEFORE INSERT OR UPDATE ON data.entity_input
FOR EACH ROW EXECUTE FUNCTION data.check_entity_input();
REVOKE ALL ON FUNCTION data.check_entity_input() FROM PUBLIC;
ALTER FUNCTION data.begin_stage() RENAME TO begin_pre_input_stage;
REVOKE ALL ON FUNCTION data.begin_pre_input_stage() FROM corpus_sem_writer;
CREATE FUNCTION data.begin_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 PERFORM data.begin_pre_input_stage();
 IF to_regclass('pg_temp.sp_fact_input') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF;
 CREATE TEMP TABLE sp_fact_input(fact_id text,input_realization_id text,input_data_revision bigint,input_fact_id text,run_id bigint) ON COMMIT DROP;
 GRANT INSERT(fact_id,input_realization_id,input_data_revision,input_fact_id,run_id) ON pg_temp.sp_fact_input TO corpus_sem_writer;
 IF to_regclass('pg_temp.sp_entity_input') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF;
 CREATE TEMP TABLE sp_entity_input(entity_id text,input_realization_id text,input_data_revision bigint,input_entity_id text,run_id bigint) ON COMMIT DROP;
 GRANT INSERT(entity_id,input_realization_id,input_data_revision,input_entity_id,run_id) ON pg_temp.sp_entity_input TO corpus_sem_writer;
END $fn$;
REVOKE ALL ON FUNCTION data.begin_stage() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.begin_stage() TO corpus_sem_writer;
ALTER FUNCTION data.end_stage() RENAME TO end_pre_input_stage;
REVOKE ALL ON FUNCTION data.end_pre_input_stage() FROM corpus_sem_writer;
CREATE FUNCTION data.end_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$ BEGIN
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','input_realization_id:text','input_data_revision:bigint','input_entity_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity_input'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','input_realization_id:text','input_data_revision:bigint','input_fact_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact_input'; END IF;
PERFORM data.end_pre_input_stage();
DROP TABLE pg_temp.sp_fact_input;
DROP TABLE pg_temp.sp_entity_input; END $fn$;
REVOKE ALL ON FUNCTION data.end_stage() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.end_stage() TO corpus_sem_writer;
CREATE OR REPLACE FUNCTION data.publish_batch(r text,z text,b text,p_content bytea) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE actual bytea; old data.batch%ROWTYPE; rev bigint; f record; application record; expected text;
BEGIN
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','input_realization_id:text','input_data_revision:bigint','input_fact_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact_input'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity_input' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','input_realization_id:text','input_data_revision:bigint','input_entity_id:text','run_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity_input'; END IF;
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_typed_value' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['value_id:text','kind:text','text_value:text','integer_value:numeric','numeric_value:numeric','decimal_lexical:text','boolean_value:boolean','entity_id:text','language:text','datatype:text','opaque_payload:jsonb']) THEN RAISE EXCEPTION 'untrusted staging relation sp_typed_value'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_value_role' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['parent_value_id:text','role:text','position:bigint','child_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_value_role'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','subject_id:text','property_id:text','object_value_id:text','qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','fact_id:text','source:text','item:text','report_object_value_id:text','report_qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','occurrence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_support'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_selection' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','selected:boolean']) THEN RAISE EXCEPTION 'untrusted staging relation sp_selection'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','source_uri:text','locator:text','provider:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_evidence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership_support'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','conclusion_fact_id:text','rule:text','rule_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation_premise' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','position:bigint','premise_fact_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation_premise'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_coverage' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['coverage_id:text','family:text','scope:text','outcome:text','reason:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_coverage'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_establishment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_establishment'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence_source' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','observation_id:bigint','rendition_id:bigint','span_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence_source'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_assessment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['assessment_id:text','operation_id:text','operation_version:text','outcome:text','fact_id:text','occurrence_id:text','confidence:numeric','reason:text','uncertainty:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_assessment'; END IF;
 actual:=convert_to(data.canonical_json(jsonb_build_array(r,z,jsonb_build_object('entity',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id") j FROM pg_temp.sp_entity) q),'[]'::jsonb),
'membership',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","class_id","establishment") j FROM pg_temp.sp_membership) q),'[]'::jsonb),
'typed_value',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("value_id","kind","text_value","integer_value"::text,"numeric_value"::text,"decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload") j FROM pg_temp.sp_typed_value) q),'[]'::jsonb),
'value_role',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("parent_value_id","role","position","child_value_id") j FROM pg_temp.sp_value_role) q),'[]'::jsonb),
'fact',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","subject_id","property_id","object_value_id","qualification_value_id") j FROM pg_temp.sp_fact) q),'[]'::jsonb),
'occurrence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id") j FROM pg_temp.sp_occurrence) q),'[]'::jsonb),
'support',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","occurrence_id") j FROM pg_temp.sp_support) q),'[]'::jsonb),
'selection',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","selected") j FROM pg_temp.sp_selection) q),'[]'::jsonb),
'evidence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("evidence_id","source_uri","locator","provider","operation_version") j FROM pg_temp.sp_evidence) q),'[]'::jsonb),
'occurrence_evidence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","evidence_id") j FROM pg_temp.sp_occurrence_evidence) q),'[]'::jsonb),
'membership_support',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","class_id","evidence_id") j FROM pg_temp.sp_membership_support) q),'[]'::jsonb),
'derivation',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("derivation_id","conclusion_fact_id","rule","rule_version") j FROM pg_temp.sp_derivation) q),'[]'::jsonb),
'derivation_premise',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("derivation_id","position","premise_fact_id") j FROM pg_temp.sp_derivation_premise) q),'[]'::jsonb),
'coverage',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("coverage_id","family","scope","outcome","reason") j FROM pg_temp.sp_coverage) q),'[]'::jsonb),
'occurrence_establishment',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","establishment") j FROM pg_temp.sp_occurrence_establishment) q),'[]'::jsonb),
'evidence_source',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("evidence_id","observation_id","rendition_id","span_id") j FROM pg_temp.sp_evidence_source) q),'[]'::jsonb),
'fact_input',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array(fact_id,input_realization_id,input_data_revision,input_fact_id,run_id) j FROM pg_temp.sp_fact_input) q),'[]'::jsonb),
'entity_input',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array(entity_id,input_realization_id,input_data_revision,input_entity_id,run_id) j FROM pg_temp.sp_entity_input) q),'[]'::jsonb),
'assessment',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence"::text,"reason","uncertainty") j FROM pg_temp.sp_assessment) q),'[]'::jsonb)))),'UTF8');
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
INSERT INTO data.membership_support(release_id,realization_id,"entity_id","class_id","evidence_id") SELECT r,z,"entity_id","class_id","evidence_id" FROM pg_temp.sp_membership_support ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id","class_id","evidence_id" FROM pg_temp.sp_membership_support EXCEPT SELECT "entity_id","class_id","evidence_id" FROM data.membership_support WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing membership_support' USING ERRCODE='23505'; END IF;
INSERT INTO data.derivation(release_id,realization_id,"derivation_id","conclusion_fact_id","rule","rule_version") SELECT r,z,"derivation_id","conclusion_fact_id","rule","rule_version" FROM pg_temp.sp_derivation ON CONFLICT DO NOTHING; IF EXISTS(SELECT "derivation_id","conclusion_fact_id","rule","rule_version" FROM pg_temp.sp_derivation EXCEPT SELECT "derivation_id","conclusion_fact_id","rule","rule_version" FROM data.derivation WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing derivation' USING ERRCODE='23505'; END IF;
INSERT INTO data.derivation_premise(release_id,realization_id,"derivation_id","position","premise_fact_id") SELECT r,z,"derivation_id","position","premise_fact_id" FROM pg_temp.sp_derivation_premise ON CONFLICT DO NOTHING; IF EXISTS(SELECT "derivation_id","position","premise_fact_id" FROM pg_temp.sp_derivation_premise EXCEPT SELECT "derivation_id","position","premise_fact_id" FROM data.derivation_premise WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing derivation_premise' USING ERRCODE='23505'; END IF;
INSERT INTO data.coverage(release_id,realization_id,"coverage_id","family","scope","outcome","reason") SELECT r,z,"coverage_id","family","scope","outcome","reason" FROM pg_temp.sp_coverage ON CONFLICT DO NOTHING; IF EXISTS(SELECT "coverage_id","family","scope","outcome","reason" FROM pg_temp.sp_coverage EXCEPT SELECT "coverage_id","family","scope","outcome","reason" FROM data.coverage WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing coverage' USING ERRCODE='23505'; END IF;
INSERT INTO data.occurrence_establishment(release_id,realization_id,"occurrence_id","establishment") SELECT r,z,"occurrence_id","establishment" FROM pg_temp.sp_occurrence_establishment ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","establishment" FROM pg_temp.sp_occurrence_establishment EXCEPT SELECT "occurrence_id","establishment" FROM data.occurrence_establishment WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence_establishment' USING ERRCODE='23505'; END IF;
INSERT INTO data.evidence_source(release_id,realization_id,"evidence_id","observation_id","rendition_id","span_id") SELECT r,z,"evidence_id","observation_id","rendition_id","span_id" FROM pg_temp.sp_evidence_source ON CONFLICT DO NOTHING; IF EXISTS(SELECT "evidence_id","observation_id","rendition_id","span_id" FROM pg_temp.sp_evidence_source EXCEPT SELECT "evidence_id","observation_id","rendition_id","span_id" FROM data.evidence_source WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing evidence_source' USING ERRCODE='23505'; END IF;
INSERT INTO data.assessment(release_id,realization_id,"assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty") SELECT r,z,"assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty" FROM pg_temp.sp_assessment ON CONFLICT DO NOTHING; IF EXISTS(SELECT "assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty" FROM pg_temp.sp_assessment EXCEPT SELECT "assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty" FROM data.assessment WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing assessment' USING ERRCODE='23505'; END IF;
 INSERT INTO data.entity_input(release_id,realization_id,entity_id,input_realization_id,input_data_revision,input_entity_id,run_id) SELECT r,z,entity_id,input_realization_id,input_data_revision,input_entity_id,run_id FROM pg_temp.sp_entity_input ON CONFLICT DO NOTHING; IF EXISTS(SELECT entity_id,input_realization_id,input_data_revision,input_entity_id,run_id FROM pg_temp.sp_entity_input EXCEPT SELECT entity_id,input_realization_id,input_data_revision,input_entity_id,run_id FROM data.entity_input WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing entity_input' USING ERRCODE='23505'; END IF;
INSERT INTO data.fact_input(release_id,realization_id,fact_id,input_realization_id,input_data_revision,input_fact_id,run_id) SELECT r,z,fact_id,input_realization_id,input_data_revision,input_fact_id,run_id FROM pg_temp.sp_fact_input ON CONFLICT DO NOTHING; IF EXISTS(SELECT fact_id,input_realization_id,input_data_revision,input_fact_id,run_id FROM pg_temp.sp_fact_input EXCEPT SELECT fact_id,input_realization_id,input_data_revision,input_fact_id,run_id FROM data.fact_input WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing fact_input' USING ERRCODE='23505'; END IF;
PERFORM data.validate_state(r,z);
 FOR f IN SELECT * FROM pg_temp.sp_occurrence LOOP
 expected:='occ:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,f.source,f.item)),'UTF8')),'hex');
 IF expected<>f.occurrence_id THEN RAISE EXCEPTION 'invalid occurrence identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM pg_temp.sp_fact LOOP
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.object_value_id,f.qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'invalid fact identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM data.fact WHERE release_id=r AND realization_id=z LOOP
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.object_value_id,f.qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'admitted fact meaning changed' USING ERRCODE='23514'; END IF;
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
END $fn$;

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
      COALESCE(observation.payload->'claims','[]'::jsonb)||COALESCE(observation.payload->'unsupported','[]'::jsonb)) item
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

CREATE OR REPLACE FUNCTION data.inference_seeds(r text,z text) RETURNS TABLE(fact_id text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT DISTINCT f.fact_id FROM data.fact f
 JOIN data.selection selected USING(release_id,realization_id,fact_id)
 JOIN data.support s USING(release_id,realization_id,fact_id)
 JOIN data.occurrence_establishment e ON (e.release_id,e.realization_id,e.occurrence_id)=
   (s.release_id,s.realization_id,s.occurrence_id) AND e.establishment='stated'
 WHERE f.release_id=r AND f.realization_id=z
 AND EXISTS(SELECT FROM data.occurrence_evidence oe JOIN data.evidence ev
  ON (ev.release_id,ev.realization_id,ev.evidence_id)=(oe.release_id,oe.realization_id,oe.evidence_id)
  WHERE (oe.release_id,oe.realization_id,oe.occurrence_id)=(s.release_id,s.realization_id,s.occurrence_id)
   AND ev.source_uri<>'' AND ev.locator<>'' AND ev.provider<>'' AND ev.operation_version<>'')
 AND NOT EXISTS(SELECT FROM data.value_role hedge WHERE (hedge.release_id,hedge.realization_id,hedge.parent_value_id)=(f.release_id,f.realization_id,f.qualification_value_id) AND hedge.role='hedge')
 AND EXISTS(SELECT FROM data.value_role vr JOIN data.typed_value v
  ON (v.release_id,v.realization_id,v.value_id)=(vr.release_id,vr.realization_id,vr.child_value_id)
  WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=f.qualification_value_id
   AND vr.role='modality' AND v.kind='string' AND v.text_value IN ('asserted','defined'))
 AND EXISTS(SELECT FROM data.value_role vr JOIN data.typed_value v
  ON (v.release_id,v.realization_id,v.value_id)=(vr.release_id,vr.realization_id,vr.child_value_id)
  WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=f.qualification_value_id
   AND vr.role='polarity' AND v.kind='boolean' AND v.boolean_value IS TRUE)
$fn$;

CREATE FUNCTION data.check_fact_input() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE source data.fact; target data.fact;
BEGIN
 SELECT * INTO STRICT source FROM data.fact WHERE release_id=NEW.release_id AND realization_id=NEW.input_realization_id AND fact_id=NEW.input_fact_id;
 SELECT * INTO STRICT target FROM data.fact WHERE release_id=NEW.release_id AND realization_id=NEW.realization_id AND fact_id=NEW.fact_id;
 IF NOT EXISTS(SELECT FROM data.entity_input ei WHERE ei.release_id=NEW.release_id AND ei.realization_id=NEW.realization_id AND ei.entity_id=target.subject_id AND ei.input_entity_id=source.subject_id AND ei.input_realization_id=NEW.input_realization_id AND ei.input_data_revision=NEW.input_data_revision AND ei.run_id=NEW.run_id)
 OR NOT EXISTS(SELECT FROM data.selection WHERE release_id=NEW.release_id AND realization_id=NEW.input_realization_id AND fact_id=NEW.input_fact_id)
 OR target.property_id<>source.property_id
 OR data.value_meaning(NEW.release_id,NEW.realization_id,target.object_value_id) IS DISTINCT FROM data.value_meaning(NEW.release_id,NEW.input_realization_id,source.object_value_id)
 OR data.value_meaning(NEW.release_id,NEW.realization_id,target.qualification_value_id) IS DISTINCT FROM data.value_meaning(NEW.release_id,NEW.input_realization_id,source.qualification_value_id) THEN
 RAISE EXCEPTION 'fact input differs from accepted bound input fact'; END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION data.check_fact_input() FROM PUBLIC;
CREATE TRIGGER fact_input_guard BEFORE INSERT OR UPDATE ON data.fact_input FOR EACH ROW EXECUTE FUNCTION data.check_fact_input();
