-- Frozen selective reference storage, result selection and operator direction.
ALTER TABLE data.project ADD COLUMN selected_result_run_id bigint REFERENCES ops.completed_result(run_id);
CREATE INDEX ix_rendition_canonical_text_search ON kb.rendition USING gin (to_tsvector('english'::regconfig, canonical_text));
GRANT REFERENCES ON data.project,ops.completed_result,kb.rendition,sem.release TO corpus_sem_publisher;
GRANT USAGE ON SCHEMA sem,data,ops,kb TO corpus_sem_evaluator;
GRANT SELECT ON ALL TABLES IN SCHEMA sem,data,ops,kb TO corpus_sem_evaluator;
CREATE SCHEMA eval AUTHORIZATION corpus_sem_publisher;
SET LOCAL ROLE corpus_sem_publisher;
GRANT SELECT ON ALL TABLES IN SCHEMA sem,data,ops,kb TO corpus_sem_evaluator;

CREATE TABLE eval.document_split (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id TEXT NOT NULL, 
	source_uri TEXT NOT NULL, 
	split TEXT NOT NULL, 
	CONSTRAINT pk_document_split PRIMARY KEY (id), 
	CONSTRAINT uq_document_split_project_id_source_uri UNIQUE (project_id, source_uri), 
	CONSTRAINT fk_document_split_project_id FOREIGN KEY(project_id) REFERENCES data.project (project_id), 
	CONSTRAINT ck_document_split_physical_23de252598 CHECK (split IN ('dev','test','reserved'))
)

;
ALTER TABLE eval.document_split OWNER TO corpus_sem_publisher;

CREATE TABLE eval.reference_set (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id TEXT NOT NULL, 
	release_id TEXT NOT NULL, 
	source_run_id BIGINT NOT NULL, 
	label TEXT NOT NULL, 
	split TEXT NOT NULL, 
	guideline TEXT NOT NULL, 
	sampling JSONB NOT NULL, 
	CONSTRAINT pk_reference_set PRIMARY KEY (id), 
	CONSTRAINT uq_reference_set_project_id_label_split UNIQUE (project_id, label, split), 
	CONSTRAINT fk_reference_set_project_id FOREIGN KEY(project_id) REFERENCES data.project (project_id), 
	CONSTRAINT fk_reference_set_release_id FOREIGN KEY(release_id) REFERENCES sem.release (release_id), 
	CONSTRAINT fk_reference_set_source_run_id FOREIGN KEY(source_run_id) REFERENCES ops.completed_result (run_id), 
	CONSTRAINT ck_reference_set_physical_23de252598 CHECK (split IN ('dev','test'))
)

;
ALTER TABLE eval.reference_set OWNER TO corpus_sem_publisher;

CREATE TABLE eval.reference_evaluation (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id TEXT NOT NULL, 
	run_id BIGINT NOT NULL, 
	set_id BIGINT NOT NULL, 
	reference_snapshot JSONB NOT NULL, 
	result JSONB NOT NULL, 
	content_digest TEXT NOT NULL, 
	CONSTRAINT pk_reference_evaluation PRIMARY KEY (id), 
	CONSTRAINT fk_reference_evaluation_project_id FOREIGN KEY(project_id) REFERENCES data.project (project_id), 
	CONSTRAINT fk_reference_evaluation_run_id FOREIGN KEY(run_id) REFERENCES ops.completed_result (run_id), 
	CONSTRAINT fk_reference_evaluation_set_id FOREIGN KEY(set_id) REFERENCES eval.reference_set (id)
)

;
ALTER TABLE eval.reference_evaluation OWNER TO corpus_sem_publisher;

CREATE TABLE eval.reference_unit (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	set_id BIGINT NOT NULL, 
	rendition_id BIGINT NOT NULL, 
	unit_key TEXT NOT NULL, 
	context JSONB NOT NULL, 
	CONSTRAINT pk_reference_unit PRIMARY KEY (id), 
	CONSTRAINT uq_reference_unit_set_id_unit_key UNIQUE (set_id, unit_key), 
	CONSTRAINT fk_reference_unit_set_id FOREIGN KEY(set_id) REFERENCES eval.reference_set (id), 
	CONSTRAINT fk_reference_unit_rendition_id FOREIGN KEY(rendition_id) REFERENCES kb.rendition (id)
)

;
ALTER TABLE eval.reference_unit OWNER TO corpus_sem_publisher;

CREATE TABLE eval.reference_pass (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	unit_id BIGINT NOT NULL, 
	pass_kind TEXT NOT NULL, 
	actor TEXT NOT NULL, 
	authored BYTEA NOT NULL, 
	content_digest TEXT NOT NULL, 
	CONSTRAINT pk_reference_pass PRIMARY KEY (id), 
	CONSTRAINT fk_reference_pass_unit_id FOREIGN KEY(unit_id) REFERENCES eval.reference_unit (id), 
	CONSTRAINT ck_reference_pass_physical_7182d42311 CHECK (pass_kind IN ('A','B','C'))
)

;
ALTER TABLE eval.reference_pass OWNER TO corpus_sem_publisher;

CREATE TABLE eval.reference_frame (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	pass_id BIGINT NOT NULL, 
	version BIGINT NOT NULL, 
	rendition_id BIGINT NOT NULL, 
	rendition_digest TEXT NOT NULL, 
	frame JSONB NOT NULL, 
	parent_id BIGINT, 
	CONSTRAINT pk_reference_frame PRIMARY KEY (id), 
	CONSTRAINT uq_reference_frame_pass_id_version UNIQUE (pass_id, version), 
	CONSTRAINT fk_reference_frame_pass_id FOREIGN KEY(pass_id) REFERENCES eval.reference_pass (id), 
	CONSTRAINT fk_reference_frame_rendition_id FOREIGN KEY(rendition_id) REFERENCES kb.rendition (id), 
	CONSTRAINT fk_reference_frame_parent_id FOREIGN KEY(parent_id) REFERENCES eval.reference_frame (id), 
	CONSTRAINT ck_reference_frame_physical_429634fbaa CHECK (version > 0)
)

;
ALTER TABLE eval.reference_frame OWNER TO corpus_sem_publisher;

CREATE TABLE eval.reference_item (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	pass_id BIGINT NOT NULL, 
	frame_id BIGINT NOT NULL, 
	item_kind TEXT NOT NULL, 
	local_ref TEXT NOT NULL, 
	payload JSONB NOT NULL, 
	CONSTRAINT pk_reference_item PRIMARY KEY (id), 
	CONSTRAINT uq_reference_item_frame_id_item_kind_local_ref UNIQUE (frame_id, item_kind, local_ref), 
	CONSTRAINT fk_reference_item_pass_id FOREIGN KEY(pass_id) REFERENCES eval.reference_pass (id), 
	CONSTRAINT fk_reference_item_frame_id FOREIGN KEY(frame_id) REFERENCES eval.reference_frame (id)
)

;
ALTER TABLE eval.reference_item OWNER TO corpus_sem_publisher;
REVOKE ALL ON SCHEMA eval FROM PUBLIC,corpus_sem_reader,corpus_sem_writer;
GRANT USAGE ON SCHEMA eval TO corpus_sem_evaluator;
GRANT SELECT ON ALL TABLES IN SCHEMA eval TO corpus_sem_evaluator;
GRANT EXECUTE ON FUNCTION data.canonical_json(jsonb),data.decimal_canonical(text),data.value_meaning(text,text,text,text[],boolean) TO corpus_sem_evaluator;
CREATE FUNCTION eval.create_reference_set(p_project text,p_release text,p_run bigint,p_label text,p_split text,p_guideline text,p_sampling jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint;
BEGIN
 IF NOT EXISTS(SELECT FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id WHERE c.run_id=p_run AND r.project_id=p_project AND c.release_id=p_release) THEN RAISE EXCEPTION 'reference source result binding differs' USING ERRCODE='23514'; END IF;
 PERFORM data.require_execution_release(p_release);
 IF p_label='' OR p_guideline='' OR jsonb_typeof(p_sampling)<>'object' THEN RAISE EXCEPTION 'incomplete reference definition' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_set(project_id,release_id,source_run_id,label,split,guideline,sampling) VALUES(p_project,p_release,p_run,p_label,p_split,p_guideline,p_sampling) RETURNING id INTO result;
 RETURN result;
END $body$;
CREATE FUNCTION eval.add_reference_unit(p_set bigint,p_rendition bigint,p_key text,p_context jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint;
BEGIN
 IF p_key='' OR jsonb_typeof(p_context)<>'array' OR NOT EXISTS(
 SELECT FROM eval.reference_set s JOIN ops.completed_result c ON c.run_id=s.source_run_id
 JOIN ops.cut_task ct ON ct.cut_id=c.cut_id JOIN kb.observation o ON o.task_id=ct.origin_task_id
 JOIN kb.rendition r ON r.id=o.rendition_id JOIN kb.document d ON d.id=r.document_id AND d.project_id=s.project_id
 JOIN eval.document_split ds ON ds.project_id=s.project_id AND ds.source_uri=d.source_uri AND ds.split=s.split
 WHERE s.id=p_set AND r.id=p_rendition AND o.payload_definition='AgentStoredBatch' AND o.payload->>'unit_ref'=p_key) THEN RAISE EXCEPTION 'reference unit source binding differs' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_unit(set_id,rendition_id,unit_key,context) VALUES(p_set,p_rendition,p_key,p_context) RETURNING id INTO result;
 RETURN result;
END $body$;
CREATE FUNCTION eval.record_reference_pass(p_unit bigint,p_kind text,p_actor text,p_authored bytea,p_frame jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint; u eval.reference_unit; rendition kb.rendition; payload jsonb;
BEGIN
 SELECT * INTO STRICT u FROM eval.reference_unit WHERE id=p_unit FOR UPDATE;
 SELECT * INTO STRICT rendition FROM kb.rendition WHERE id=u.rendition_id;
 payload:=convert_from(p_authored,'UTF8')::jsonb;
 IF p_actor='' OR payload->>'unit_ref' IS DISTINCT FROM u.unit_key OR jsonb_typeof(p_frame)<>'array' THEN RAISE EXCEPTION 'reference pass shape or unit differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_frame) e WHERE NOT (e ?& ARRAY['start','end','quote']) OR (e->>'start')::bigint<0 OR (e->>'end')::bigint<(e->>'start')::bigint OR substring(rendition.canonical_text FROM (e->>'start')::integer+1 FOR (e->>'end')::integer-(e->>'start')::integer) IS DISTINCT FROM e->>'quote') THEN RAISE EXCEPTION 'reference citation frame differs from rendition' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_pass(unit_id,pass_kind,actor,authored,content_digest) VALUES(p_unit,p_kind,p_actor,p_authored,encode(sha256(p_authored),'hex')) RETURNING id INTO result;
 INSERT INTO eval.reference_frame(pass_id,version,rendition_id,rendition_digest,frame) VALUES(result,1,u.rendition_id,rendition.content_digest,p_frame);
 RETURN result;
END $body$;
CREATE FUNCTION eval.relocate_reference_frame(p_pass bigint,p_parent bigint,p_rendition bigint,p_frame jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint; previous eval.reference_frame; rendition kb.rendition;
BEGIN
 PERFORM 1 FROM eval.reference_pass WHERE id=p_pass FOR UPDATE;
 SELECT * INTO STRICT previous FROM eval.reference_frame WHERE id=p_parent AND pass_id=p_pass;
 IF previous.version<>(SELECT max(version) FROM eval.reference_frame WHERE pass_id=p_pass) THEN RAISE EXCEPTION 'reference frame parent is stale' USING ERRCODE='40001'; END IF;
 SELECT * INTO STRICT rendition FROM kb.rendition WHERE id=p_rendition;
 IF NOT EXISTS(SELECT FROM kb.rendition r WHERE r.id=previous.rendition_id AND r.document_id=rendition.document_id) OR jsonb_typeof(p_frame)<>'array' OR jsonb_array_length(p_frame)<>jsonb_array_length(previous.frame) THEN RAISE EXCEPTION 'reference frame relocation source differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_frame) WITH ORDINALITY e(value,n) JOIN jsonb_array_elements(previous.frame) WITH ORDINALITY old(value,n) USING(n) WHERE e.value->>'quote' IS DISTINCT FROM old.value->>'quote' OR (e.value->>'start')::bigint<0 OR (e.value->>'end')::bigint<(e.value->>'start')::bigint OR substring(rendition.canonical_text FROM (e.value->>'start')::integer+1 FOR (e.value->>'end')::integer-(e.value->>'start')::integer) IS DISTINCT FROM e.value->>'quote') THEN RAISE EXCEPTION 'reference frame relocation changes cited text' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_frame(pass_id,version,rendition_id,rendition_digest,frame,parent_id) VALUES(p_pass,previous.version+1,p_rendition,rendition.content_digest,p_frame,p_parent) RETURNING id INTO result;
 RETURN result;
END $body$;
CREATE FUNCTION eval.record_reference_items(p_pass bigint,p_frame bigint,p_items jsonb) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
 IF NOT EXISTS(SELECT FROM eval.reference_frame WHERE id=p_frame AND pass_id=p_pass) OR jsonb_typeof(p_items)<>'array' THEN RAISE EXCEPTION 'reference item frame differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM eval.reference_item WHERE frame_id=p_frame) THEN
  IF p_items IS DISTINCT FROM (SELECT jsonb_agg(jsonb_build_object('item_kind',item_kind,'local_ref',local_ref,'payload',payload) ORDER BY item_kind,local_ref) FROM eval.reference_item WHERE frame_id=p_frame) THEN RAISE EXCEPTION 'reference items are immutable' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 INSERT INTO eval.reference_item(pass_id,frame_id,item_kind,local_ref,payload) SELECT p_pass,p_frame,e->>'item_kind',e->>'local_ref',e->'payload' FROM jsonb_array_elements(p_items) e;
END $body$;
CREATE FUNCTION eval.reference_snapshot(p_set bigint) RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
 SELECT coalesce(jsonb_agg(jsonb_build_object('unit_id',u.id,'pass_id',p.id,'content_digest',p.content_digest,'frame_id',f.id,'rendition_id',f.rendition_id,'rendition_digest',f.rendition_digest) ORDER BY u.id),'[]'::jsonb)
 FROM eval.reference_unit u JOIN LATERAL(SELECT * FROM eval.reference_pass WHERE unit_id=u.id AND pass_kind='C' ORDER BY id DESC LIMIT 1) p ON true JOIN LATERAL(SELECT * FROM eval.reference_frame WHERE pass_id=p.id ORDER BY version DESC LIMIT 1) f ON true WHERE u.set_id=p_set
$body$;
CREATE FUNCTION eval.record_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint; source_release text; target_release text;
BEGIN
 PERFORM 1 FROM eval.reference_unit WHERE set_id=p_set FOR UPDATE;
 SELECT release_id INTO STRICT source_release FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 SELECT c.release_id INTO STRICT target_release FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id WHERE c.run_id=p_run AND r.project_id=p_project;
 IF source_release<>target_release OR p_snapshot IS DISTINCT FROM eval.reference_snapshot(p_set) OR jsonb_array_length(p_snapshot)=0 OR jsonb_array_length(p_snapshot)<>(SELECT count(*) FROM eval.reference_unit WHERE set_id=p_set) OR jsonb_typeof(p_result)<>'object' THEN RAISE EXCEPTION 'reference evaluation snapshot is incomplete or stale' USING ERRCODE='40001'; END IF;
 INSERT INTO eval.reference_evaluation(project_id,run_id,set_id,reference_snapshot,result,content_digest) VALUES(p_project,p_run,p_set,p_snapshot,p_result,encode(sha256(convert_to(data.canonical_json(jsonb_build_object('snapshot',p_snapshot,'result',p_result)),'UTF8')),'hex')) RETURNING id INTO result;
 RETURN result;
END $body$;
CREATE FUNCTION eval.assign_document_split(p_project text,p_source text,p_split text) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result text;
BEGIN
 INSERT INTO eval.document_split(project_id,source_uri,split) VALUES(p_project,p_source,p_split) ON CONFLICT(project_id,source_uri) DO NOTHING;
 SELECT split INTO STRICT result FROM eval.document_split WHERE project_id=p_project AND source_uri=p_source;
 IF result<>p_split THEN RAISE EXCEPTION 'document split is immutable' USING ERRCODE='23514'; END IF;
 RETURN result;
END $body$;
CREATE OR REPLACE FUNCTION data.guard_project_execution_admission() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $guard$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.generation<>0 OR NEW.selected_result_run_id IS NOT NULL THEN RAISE EXCEPTION 'project generation must start at zero without selected result' USING ERRCODE='23514'; END IF;
 ELSIF (NEW.active_release_id IS DISTINCT FROM OLD.active_release_id OR NEW.selected_result_run_id IS DISTINCT FROM OLD.selected_result_run_id OR NEW.generation IS DISTINCT FROM OLD.generation) AND NEW.generation IS DISTINCT FROM OLD.generation+1 THEN RAISE EXCEPTION 'project generation must advance exactly once' USING ERRCODE='23514'; END IF;
 IF NEW.active_release_id IS NOT NULL THEN PERFORM data.require_execution_release(NEW.active_release_id); END IF;
 IF NEW.selected_result_run_id IS NOT NULL AND NOT EXISTS(SELECT FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id AND r.project_id=NEW.project_id JOIN data.realization z ON z.realization_id=c.output_realization_id AND z.release_id=c.release_id WHERE c.run_id=NEW.selected_result_run_id AND r.result_realization_id=c.output_realization_id AND z.project_id=NEW.project_id) THEN RAISE EXCEPTION 'selected completed result binding differs' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $guard$;
CREATE FUNCTION data.select_project_result(p_project text,p_run bigint,p_generation bigint) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint;
BEGIN
 UPDATE data.project SET selected_result_run_id=p_run,generation=generation+1 WHERE project_id=p_project AND generation=p_generation RETURNING generation INTO result;
 IF result IS NULL THEN RAISE EXCEPTION 'project selection generation changed' USING ERRCODE='40001'; END IF;
 RETURN result;
END $body$;
CREATE FUNCTION ops.record_direction(p_run bigint,p_actor text,p_session text,p_body jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint;
BEGIN
 IF p_actor='' OR p_session='' OR jsonb_typeof(p_body)<>'object' OR p_body->>'text' IS NULL OR p_body->>'scope' IS NULL OR NOT EXISTS(SELECT FROM ops.run WHERE id=p_run AND project_id=p_body->>'project_id' AND status IN ('created','running')) THEN RAISE EXCEPTION 'direction run binding differs or run no longer active' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.intervention(run_id,actor,session_ref,kind,body) VALUES(p_run,p_actor,p_session,'direction',p_body) RETURNING id INTO result;
 RETURN result;
END $body$;
GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO corpus_sem_evaluator;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA eval FROM PUBLIC,corpus_sem_reader,corpus_sem_writer;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA eval TO corpus_sem_evaluator;
REVOKE ALL ON FUNCTION data.select_project_result(text,bigint,bigint),ops.record_direction(bigint,text,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.select_project_result(text,bigint,bigint),ops.record_direction(bigint,text,text,jsonb) TO corpus_sem_writer;
