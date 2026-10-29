CREATE SCHEMA ops;
CREATE SCHEMA kb;
GRANT USAGE,CREATE ON SCHEMA ops,kb TO corpus_sem_publisher;

CREATE TABLE ops.method (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	name TEXT NOT NULL,
	version TEXT NOT NULL,
	family TEXT NOT NULL,
	tier TEXT NOT NULL,
	confidence_source TEXT,
	CONSTRAINT pk_method PRIMARY KEY (id),
	CONSTRAINT uq_method_name_version UNIQUE (name, version)
)

;

CREATE TABLE ops.method_config (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	method_id BIGINT NOT NULL,
	name TEXT NOT NULL,
	params JSONB NOT NULL,
	config_hash TEXT NOT NULL,
	CONSTRAINT pk_method_config PRIMARY KEY (id),
	CONSTRAINT uq_method_config_method_id_config_hash UNIQUE (method_id, config_hash),
	CONSTRAINT fk_method_config_method_id FOREIGN KEY(method_id) REFERENCES ops.method (id)
)

;

CREATE TABLE kb.document (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	project_id TEXT NOT NULL,
	key TEXT NOT NULL,
	source_uri TEXT NOT NULL,
	content_hash TEXT NOT NULL,
	original_path TEXT NOT NULL,
	mime TEXT NOT NULL,
	title TEXT,
	meta JSONB NOT NULL,
	CONSTRAINT pk_document PRIMARY KEY (id),
	CONSTRAINT uq_document_project_id_key UNIQUE (project_id, key),
	CONSTRAINT uq_document_project_id_id UNIQUE (project_id, id),
	CONSTRAINT fk_document_project_id FOREIGN KEY(project_id) REFERENCES data.project (project_id)
)

;

CREATE TABLE kb.rendition (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	document_id BIGINT NOT NULL,
	key TEXT NOT NULL,
	content_digest TEXT NOT NULL,
	canonical_text TEXT NOT NULL,
	content JSONB NOT NULL,
	parse_status TEXT NOT NULL,
	CONSTRAINT pk_rendition PRIMARY KEY (id),
	CONSTRAINT uq_rendition_key UNIQUE (key),
	CONSTRAINT uq_rendition_document_id_id UNIQUE (document_id, id),
	CONSTRAINT fk_rendition_document_id FOREIGN KEY(document_id) REFERENCES kb.document (id)
)

;

CREATE TABLE ops.run (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	project_id TEXT NOT NULL,
	release_id TEXT NOT NULL,
	input_realization_id TEXT NOT NULL,
	input_revision BIGINT NOT NULL,
	dependency_digest TEXT NOT NULL,
	dependencies BYTEA NOT NULL,
	kind TEXT NOT NULL,
	phase BIGINT NOT NULL,
	options JSONB NOT NULL,
	guideline TEXT NOT NULL,
	status TEXT NOT NULL,
	code_commit TEXT NOT NULL,
	result_realization_id TEXT,
	sealed BOOLEAN NOT NULL,
	CONSTRAINT pk_run PRIMARY KEY (id),
	CONSTRAINT uq_run_id_release_id UNIQUE (id, release_id),
	CONSTRAINT fk_run_project_id FOREIGN KEY(project_id) REFERENCES data.project (project_id),
	CONSTRAINT fk_run_release_id_input_realization_id FOREIGN KEY(release_id, input_realization_id) REFERENCES data.realization (release_id, realization_id),
	CONSTRAINT ck_run_physical_cf2108479f CHECK (input_revision >= 0),
	CONSTRAINT ck_run_physical_18b3405cc1 CHECK (status IN ('created','running','consolidating','finished','failed','cancelled'))
)

;

CREATE TABLE kb.segment (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	rendition_id BIGINT NOT NULL,
	segment_key TEXT NOT NULL,
	parent_key TEXT,
	kind TEXT NOT NULL,
	ordinal BIGINT NOT NULL,
	start_offset BIGINT NOT NULL,
	end_offset BIGINT NOT NULL,
	attrs JSONB NOT NULL,
	parse_status TEXT NOT NULL,
	parse_reason TEXT,
	CONSTRAINT pk_segment PRIMARY KEY (id),
	CONSTRAINT uq_segment_rendition_id_segment_key UNIQUE (rendition_id, segment_key),
	CONSTRAINT uq_segment_rendition_id_id UNIQUE (rendition_id, id),
	CONSTRAINT fk_segment_rendition_id FOREIGN KEY(rendition_id) REFERENCES kb.rendition (id),
	CONSTRAINT ck_segment_physical_c8fe50ca90 CHECK (start_offset >= 0 AND end_offset >= start_offset)
)

;

CREATE TABLE ops.input_cut (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id BIGINT NOT NULL,
	name TEXT NOT NULL,
	final BOOLEAN NOT NULL,
	release_id TEXT NOT NULL,
	source_revision BIGINT NOT NULL,
	CONSTRAINT pk_input_cut PRIMARY KEY (id),
	CONSTRAINT uq_input_cut_run_id_name UNIQUE (run_id, name),
	CONSTRAINT fk_input_cut_run_id_release_id FOREIGN KEY(run_id, release_id) REFERENCES ops.run (id, release_id)
)

;

CREATE TABLE ops.run_rendition (
	run_id BIGINT NOT NULL,
	document_id BIGINT NOT NULL,
	rendition_id BIGINT NOT NULL,
	CONSTRAINT pk_run_rendition PRIMARY KEY (run_id, document_id),
	CONSTRAINT fk_run_rendition_run_id FOREIGN KEY(run_id) REFERENCES ops.run (id),
	CONSTRAINT fk_run_rendition_document_id_rendition_id FOREIGN KEY(document_id, rendition_id) REFERENCES kb.rendition (document_id, id)
)

;

CREATE TABLE ops.task (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id BIGINT NOT NULL,
	release_id TEXT NOT NULL,
	stage TEXT NOT NULL,
	unit_type TEXT NOT NULL,
	unit_id BIGINT,
	unit_key TEXT,
	method_config_id BIGINT NOT NULL,
	input_hash TEXT NOT NULL,
	packet_hash TEXT,
	reused_task_id BIGINT,
	status TEXT NOT NULL,
	attempt BIGINT NOT NULL,
	claimed_by TEXT,
	lease_until TIMESTAMP WITH TIME ZONE,
	result_digest TEXT,
	error JSONB,
	cost JSONB NOT NULL,
	reason TEXT,
	priority BIGINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE,
	finished_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_task PRIMARY KEY (id),
	CONSTRAINT uq_task_id_release_id UNIQUE (id, release_id),
	CONSTRAINT fk_task_run_id_release_id FOREIGN KEY(run_id, release_id) REFERENCES ops.run (id, release_id),
	CONSTRAINT fk_task_method_config_id FOREIGN KEY(method_config_id) REFERENCES ops.method_config (id),
	CONSTRAINT fk_task_reused_task_id FOREIGN KEY(reused_task_id) REFERENCES ops.task (id),
	CONSTRAINT ck_task_physical_3f232544ec CHECK (attempt >= 0),
	CONSTRAINT ck_task_physical_8cb2ac785d CHECK (status IN ('pending','running','awaiting_agent','done','empty','failed','reused','skipped','cancelled'))
)

;

CREATE TABLE kb.span (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	rendition_id BIGINT NOT NULL,
	segment_id BIGINT,
	start_offset BIGINT NOT NULL,
	end_offset BIGINT NOT NULL,
	CONSTRAINT pk_span PRIMARY KEY (id),
	CONSTRAINT uq_span_rendition_id_start_offset_end_offset UNIQUE (rendition_id, start_offset, end_offset),
	CONSTRAINT uq_span_rendition_id_id UNIQUE (rendition_id, id),
	CONSTRAINT fk_span_rendition_id FOREIGN KEY(rendition_id) REFERENCES kb.rendition (id),
	CONSTRAINT fk_span_rendition_id_segment_id FOREIGN KEY(rendition_id, segment_id) REFERENCES kb.segment (rendition_id, id),
	CONSTRAINT ck_span_physical_1612dc709c CHECK (start_offset >= 0 AND end_offset > start_offset)
)

;

CREATE TABLE ops.cut_task (
	cut_id BIGINT NOT NULL,
	task_id BIGINT NOT NULL,
	origin_task_id BIGINT NOT NULL,
	CONSTRAINT pk_cut_task PRIMARY KEY (cut_id, task_id),
	CONSTRAINT fk_cut_task_cut_id FOREIGN KEY(cut_id) REFERENCES ops.input_cut (id),
	CONSTRAINT fk_cut_task_task_id FOREIGN KEY(task_id) REFERENCES ops.task (id),
	CONSTRAINT fk_cut_task_origin_task_id FOREIGN KEY(origin_task_id) REFERENCES ops.task (id)
)

;

CREATE TABLE ops.intervention (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id BIGINT NOT NULL,
	task_id BIGINT,
	actor TEXT NOT NULL,
	session_ref TEXT NOT NULL,
	kind TEXT NOT NULL,
	body JSONB NOT NULL,
	rationale TEXT,
	CONSTRAINT pk_intervention PRIMARY KEY (id),
	CONSTRAINT fk_intervention_run_id FOREIGN KEY(run_id) REFERENCES ops.run (id),
	CONSTRAINT fk_intervention_task_id FOREIGN KEY(task_id) REFERENCES ops.task (id)
)

;

CREATE TABLE ops.measurement (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id BIGINT NOT NULL,
	task_id BIGINT NOT NULL,
	metric TEXT NOT NULL,
	scope_type TEXT NOT NULL,
	scope_id BIGINT,
	scope_key TEXT,
	value NUMERIC,
	detail JSONB NOT NULL,
	CONSTRAINT pk_measurement PRIMARY KEY (id),
	CONSTRAINT fk_measurement_run_id FOREIGN KEY(run_id) REFERENCES ops.run (id),
	CONSTRAINT fk_measurement_task_id FOREIGN KEY(task_id) REFERENCES ops.task (id)
)

;

CREATE TABLE ops.rendition_build (
	document_id BIGINT NOT NULL,
	method_config_id BIGINT NOT NULL,
	rendition_id BIGINT NOT NULL,
	task_id BIGINT NOT NULL,
	parse_detail JSONB NOT NULL,
	CONSTRAINT pk_rendition_build PRIMARY KEY (document_id, method_config_id),
	CONSTRAINT fk_rendition_build_document_id_rendition_id FOREIGN KEY(document_id, rendition_id) REFERENCES kb.rendition (document_id, id),
	CONSTRAINT fk_rendition_build_method_config_id FOREIGN KEY(method_config_id) REFERENCES ops.method_config (id),
	CONSTRAINT fk_rendition_build_task_id FOREIGN KEY(task_id) REFERENCES ops.task (id)
)

;

CREATE TABLE kb.observation (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	task_id BIGINT NOT NULL,
	release_id TEXT NOT NULL,
	observation_key TEXT NOT NULL,
	ordinal BIGINT NOT NULL,
	kind TEXT NOT NULL,
	payload_definition TEXT NOT NULL,
	payload JSONB NOT NULL,
	rendition_id BIGINT,
	segment_id BIGINT,
	span_id BIGINT,
	score NUMERIC,
	outcome TEXT NOT NULL,
	CONSTRAINT pk_observation PRIMARY KEY (id),
	CONSTRAINT uq_observation_observation_key UNIQUE (observation_key),
	CONSTRAINT uq_observation_task_id_ordinal UNIQUE (task_id, ordinal),
	CONSTRAINT fk_observation_task_id_release_id FOREIGN KEY(task_id, release_id) REFERENCES ops.task (id, release_id),
	CONSTRAINT fk_observation_rendition_id FOREIGN KEY(rendition_id) REFERENCES kb.rendition (id),
	CONSTRAINT fk_observation_rendition_id_segment_id FOREIGN KEY(rendition_id, segment_id) REFERENCES kb.segment (rendition_id, id),
	CONSTRAINT fk_observation_rendition_id_span_id FOREIGN KEY(rendition_id, span_id) REFERENCES kb.span (rendition_id, id),
	CONSTRAINT ck_observation_physical_ee668cd4ef CHECK (ordinal >= 0)
)

;

CREATE TABLE data.assessment (
	realization_id TEXT NOT NULL,
	release_id TEXT NOT NULL,
	assessment_id TEXT NOT NULL,
	fact_id TEXT,
	occurrence_id TEXT,
	operation_id TEXT NOT NULL,
	operation_version TEXT NOT NULL,
	outcome TEXT NOT NULL,
	confidence NUMERIC,
	reason TEXT,
	uncertainty TEXT,
	CONSTRAINT pk_assessment PRIMARY KEY (realization_id, release_id, assessment_id),
	CONSTRAINT fk_assessment_realization_id_release_id_fact_id FOREIGN KEY(realization_id, release_id, fact_id) REFERENCES data.fact (realization_id, release_id, fact_id),
	CONSTRAINT fk_assessment_realization_id_release_id_occurrence_id FOREIGN KEY(realization_id, release_id, occurrence_id) REFERENCES data.occurrence (realization_id, release_id, occurrence_id),
	CONSTRAINT ck_assessment_physical_a44e2bbc14 CHECK ((fact_id IS NULL) <> (occurrence_id IS NULL)),
	CONSTRAINT ck_assessment_physical_506af7cc40 CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
)

;

CREATE TABLE data.evidence_source (
	realization_id TEXT NOT NULL,
	release_id TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	observation_id BIGINT NOT NULL,
	rendition_id BIGINT NOT NULL,
	span_id BIGINT,
	CONSTRAINT pk_evidence_source PRIMARY KEY (realization_id, release_id, evidence_id),
	CONSTRAINT fk_evidence_source_realization_id_release_id_evidence_id FOREIGN KEY(realization_id, release_id, evidence_id) REFERENCES data.evidence (realization_id, release_id, evidence_id),
	CONSTRAINT fk_evidence_source_observation_id FOREIGN KEY(observation_id) REFERENCES kb.observation (id),
	CONSTRAINT fk_evidence_source_rendition_id FOREIGN KEY(rendition_id) REFERENCES kb.rendition (id),
	CONSTRAINT fk_evidence_source_rendition_id_span_id FOREIGN KEY(rendition_id, span_id) REFERENCES kb.span (rendition_id, id)
)

;

CREATE TABLE data.occurrence_establishment (
	realization_id TEXT NOT NULL,
	release_id TEXT NOT NULL,
	occurrence_id TEXT NOT NULL,
	establishment TEXT NOT NULL,
	CONSTRAINT pk_occurrence_establishment PRIMARY KEY (realization_id, release_id, occurrence_id),
	CONSTRAINT fk_occurrence_establishment_realization_id_release_id_o_03a1 FOREIGN KEY(realization_id, release_id, occurrence_id) REFERENCES data.occurrence (realization_id, release_id, occurrence_id),
	CONSTRAINT ck_occurrence_establishment_physical_ef563c839f CHECK (establishment IN ('stated','derived','agent_asserted'))
)

;
GRANT USAGE ON SCHEMA ops,kb TO corpus_sem_writer,corpus_sem_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA ops,kb TO corpus_sem_reader,corpus_sem_writer;
GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA ops,kb TO corpus_sem_publisher;
GRANT INSERT ON ALL TABLES IN SCHEMA ops,kb TO corpus_sem_writer;
REVOKE INSERT ON kb.observation,ops.cut_task,ops.input_cut FROM corpus_sem_writer;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ops,kb TO corpus_sem_writer;
GRANT UPDATE(status,result_realization_id,sealed) ON ops.run TO corpus_sem_writer;
GRANT UPDATE(status,attempt,claimed_by,lease_until,result_digest,error,cost,reason,priority,started_at,finished_at,reused_task_id) ON ops.task TO corpus_sem_writer;
GRANT SELECT ON data.evidence_source,data.occurrence_establishment TO corpus_sem_writer,corpus_sem_reader;
CREATE TABLE ops.task_result(task_id bigint PRIMARY KEY,release_id text NOT NULL,body jsonb NOT NULL,CONSTRAINT fk_task_result_scope FOREIGN KEY(task_id,release_id) REFERENCES ops.task(id,release_id));
GRANT SELECT ON ops.task_result TO corpus_sem_writer,corpus_sem_reader;
GRANT SELECT,INSERT ON ops.task_result TO corpus_sem_publisher;

CREATE FUNCTION ops.complete_task(p_task bigint,p_attempt bigint,p_holder text,p_rows jsonb,p_outcome text,p_error jsonb,p_envelope jsonb DEFAULT NULL)
RETURNS bigint[] LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; r ops.run; item jsonb; ids bigint[] := '{}'; oid bigint; digest text;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id FOR SHARE;
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task FOR UPDATE;
 digest := encode(sha256(convert_to(jsonb_build_array(p_rows,p_outcome,p_error,p_envelope)::text,'UTF8')),'hex');
 IF t.status IN ('done','empty','failed') AND t.attempt=p_attempt AND t.claimed_by=p_holder AND t.result_digest=digest THEN
   RETURN ARRAY(SELECT id FROM kb.observation WHERE task_id=t.id ORDER BY ordinal);
 END IF;
 IF r.sealed OR r.status NOT IN ('created','running') OR t.status<>'running' OR t.attempt<>p_attempt OR t.claimed_by IS DISTINCT FROM p_holder THEN
   RAISE EXCEPTION 'task attempt lost or run sealed' USING ERRCODE='P0004';
 END IF;
 IF p_outcome NOT IN ('done','empty','failed') OR (p_outcome='done')<>(jsonb_array_length(p_rows)>0) OR (p_outcome='failed')<>(p_error<>'null'::jsonb) THEN
   RAISE EXCEPTION 'inconsistent terminal outcome';
 END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p_rows) LOOP
   IF item->>'rendition_id' IS NOT NULL AND NOT EXISTS(SELECT 1 FROM ops.run_rendition rr WHERE rr.run_id=t.run_id AND rr.rendition_id=(item->>'rendition_id')::bigint) THEN
     RAISE EXCEPTION 'observation rendition outside run';
   END IF;
   INSERT INTO kb.observation(task_id,release_id,observation_key,ordinal,kind,payload_definition,payload,rendition_id,segment_id,span_id,score,outcome)
   VALUES(t.id,t.release_id,item->>'observation_key',(item->>'ordinal')::bigint,item->>'kind',item->>'payload_definition',item->'payload',(item->>'rendition_id')::bigint,(item->>'segment_id')::bigint,(item->>'span_id')::bigint,(item->>'score')::numeric,coalesce(item->>'outcome','produced')) RETURNING id INTO oid;
   ids:=array_append(ids,oid);
 END LOOP;
 IF p_envelope IS NOT NULL THEN INSERT INTO ops.task_result(task_id,release_id,body) VALUES(t.id,t.release_id,p_envelope); END IF;
 UPDATE ops.task SET status=p_outcome,result_digest=digest,error=nullif(p_error,'null'::jsonb),finished_at=clock_timestamp(),lease_until=NULL WHERE id=t.id;
 RETURN ids;
END $$;
ALTER FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) TO corpus_sem_writer;

CREATE FUNCTION ops.capture_cut(p_run bigint,p_name text,p_final boolean)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r ops.run; cut ops.input_cut; cut_id bigint;
BEGIN
 SELECT * INTO STRICT r FROM ops.run WHERE id=p_run FOR UPDATE;
 SELECT * INTO cut FROM ops.input_cut WHERE run_id=p_run AND name=p_name;
 IF FOUND THEN
  IF cut.final<>p_final THEN RAISE EXCEPTION 'cut name already has another meaning'; END IF;
  RETURN cut.id;
 END IF;
 IF r.sealed OR r.status NOT IN ('created','running','consolidating') THEN RAISE EXCEPTION 'run cannot create a cut'; END IF;
 INSERT INTO ops.input_cut(run_id,name,final,release_id,source_revision) VALUES(r.id,p_name,p_final,r.release_id,r.input_revision) RETURNING id INTO cut_id;
 INSERT INTO ops.cut_task(cut_id,task_id,origin_task_id)
 SELECT cut_id,t.id,coalesce(t.reused_task_id,t.id) FROM ops.task t LEFT JOIN ops.task origin ON origin.id=t.reused_task_id
 WHERE t.run_id=r.id AND coalesce(origin.status,t.status) IN ('done','empty');
 IF p_final THEN UPDATE ops.run SET sealed=true,status='consolidating' WHERE id=r.id; END IF;
 RETURN cut_id;
END $$;
ALTER FUNCTION ops.capture_cut(bigint,text,boolean) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.capture_cut(bigint,text,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.capture_cut(bigint,text,boolean) TO corpus_sem_writer;
CREATE FUNCTION ops.create_run(p text,r text,z text,v bigint,d bytea,k text,phase bigint,opts jsonb,g text,commit text)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source data.realization; result bigint;
BEGIN
 SELECT * INTO STRICT source FROM data.realization WHERE realization_id=z AND project_id=p FOR SHARE;
 IF source.release_id<>r OR source.data_revision<>v THEN RAISE EXCEPTION 'source snapshot changed' USING ERRCODE='P0004'; END IF;
 INSERT INTO ops.run(project_id,release_id,input_realization_id,input_revision,dependency_digest,dependencies,kind,phase,options,guideline,status,code_commit,sealed)
 VALUES(p,r,z,v,encode(sha256(d),'hex'),d,k,phase,opts,g,'created',commit,false) RETURNING id INTO result;
 RETURN result;
END $$;
ALTER FUNCTION ops.create_run(text,text,text,bigint,bytea,text,bigint,jsonb,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.create_run(text,text,text,bigint,bytea,text,bigint,jsonb,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.create_run(text,text,text,bigint,bytea,text,bigint,jsonb,text,text) TO corpus_sem_writer;
REVOKE INSERT ON ops.run FROM corpus_sem_writer;

GRANT SELECT,INSERT,UPDATE ON data.assessment,data.evidence_source,data.occurrence_establishment TO corpus_sem_publisher;
GRANT SELECT ON data.assessment,data.evidence_source,data.occurrence_establishment TO corpus_sem_reader,corpus_sem_writer;

CREATE FUNCTION ops.check_source_scope() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM ops.run r JOIN kb.document d ON d.project_id=r.project_id WHERE r.id=NEW.run_id AND d.id=NEW.document_id AND NOT r.sealed) THEN
  RAISE EXCEPTION 'source is outside run project or run is sealed';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER source_scope BEFORE INSERT ON ops.run_rendition FOR EACH ROW EXECUTE FUNCTION ops.check_source_scope();

CREATE FUNCTION kb.check_offsets() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE size bigint;
BEGIN
 SELECT char_length(canonical_text) INTO STRICT size FROM kb.rendition WHERE id=NEW.rendition_id;
 IF NEW.start_offset<0 OR NEW.end_offset>size THEN RAISE EXCEPTION 'source offsets outside canonical rendition'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER segment_offsets BEFORE INSERT ON kb.segment FOR EACH ROW EXECUTE FUNCTION kb.check_offsets();
CREATE TRIGGER span_offsets BEFORE INSERT ON kb.span FOR EACH ROW EXECUTE FUNCTION kb.check_offsets();
REVOKE ALL ON FUNCTION ops.check_source_scope(),kb.check_offsets() FROM PUBLIC;

ALTER TABLE kb.observation ADD CONSTRAINT uq_observation_bound UNIQUE(release_id,id);
ALTER TABLE data.evidence_source DROP CONSTRAINT fk_evidence_source_observation_id;
ALTER TABLE data.evidence_source ADD CONSTRAINT fk_evidence_source_observation_scope FOREIGN KEY(release_id,observation_id) REFERENCES kb.observation(release_id,id);
ALTER TABLE data.evidence_source ADD CONSTRAINT fk_evidence_source_realization FOREIGN KEY(realization_id,release_id) REFERENCES data.realization(realization_id,release_id);
ALTER TABLE data.occurrence_establishment ADD CONSTRAINT fk_occurrence_establishment_realization FOREIGN KEY(realization_id,release_id) REFERENCES data.realization(realization_id,release_id);
ALTER TABLE data.assessment ADD CONSTRAINT fk_assessment_realization FOREIGN KEY(realization_id,release_id) REFERENCES data.realization(realization_id,release_id);
CREATE FUNCTION data.check_evidence_source() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM kb.observation o WHERE o.id=NEW.observation_id AND o.release_id=NEW.release_id AND o.rendition_id=NEW.rendition_id AND o.span_id IS NOT DISTINCT FROM NEW.span_id) THEN
   RAISE EXCEPTION 'evidence source differs from bound observation';
 END IF;
 RETURN NEW;
END $$;
ALTER FUNCTION data.check_evidence_source() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.check_evidence_source() FROM PUBLIC;
CREATE TRIGGER evidence_source_scope BEFORE INSERT ON data.evidence_source FOR EACH ROW EXECUTE FUNCTION data.check_evidence_source();
