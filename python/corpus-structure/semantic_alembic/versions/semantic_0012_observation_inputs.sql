ALTER TABLE ops.task ADD COLUMN invocation_key text NOT NULL DEFAULT gen_random_uuid()::text;
ALTER TABLE ops.rendition_build DROP CONSTRAINT pk_rendition_build;
ALTER TABLE ops.rendition_build ADD CONSTRAINT pk_rendition_build PRIMARY KEY(task_id);
ALTER TABLE kb.observation ADD CONSTRAINT uq_observation_source_identity UNIQUE(release_id,observation_key);
CREATE TABLE kb.observation_input(
 release_id text NOT NULL,observation_id bigint NOT NULL,position bigint NOT NULL,
 source_observation_key text NOT NULL,role text NOT NULL,
 PRIMARY KEY(observation_id,position),
 FOREIGN KEY(release_id,observation_id) REFERENCES kb.observation(release_id,id),
 FOREIGN KEY(release_id,source_observation_key) REFERENCES kb.observation(release_id,observation_key),
 CHECK(position>=0),CHECK(role<>'')
);
GRANT SELECT ON kb.observation_input TO corpus_sem_reader,corpus_sem_writer;
GRANT SELECT,INSERT ON kb.observation_input TO corpus_sem_publisher;
CREATE FUNCTION kb.record_observation_inputs() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE ref jsonb; pos bigint:=0; target_run bigint;
BEGIN
 IF NEW.payload_definition<>'SourceObservation' THEN RETURN NEW; END IF;
 SELECT run_id INTO STRICT target_run FROM ops.task WHERE id=NEW.task_id;
 FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(NEW.payload->'inputs','[]'::jsonb)) LOOP
   IF NOT EXISTS(
     SELECT 1 FROM kb.observation source JOIN ops.task origin ON origin.id=source.task_id
     JOIN ops.task current ON current.run_id=target_run AND (current.id=origin.id OR current.reused_task_id=origin.id)
     WHERE source.observation_key=ref->>'observation_key' AND source.release_id=NEW.release_id
       AND origin.status IN ('done','empty')
   ) THEN RAISE EXCEPTION 'source input is outside the completed bound run'; END IF;
   INSERT INTO kb.observation_input(release_id,observation_id,position,source_observation_key,role)
   VALUES(NEW.release_id,NEW.id,pos,ref->>'observation_key',ref->>'role');
   pos:=pos+1;
 END LOOP;
 RETURN NEW;
END $fn$;
ALTER FUNCTION kb.record_observation_inputs() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION kb.record_observation_inputs() FROM PUBLIC;
CREATE TRIGGER observation_input_links AFTER INSERT ON kb.observation FOR EACH ROW EXECUTE FUNCTION kb.record_observation_inputs();

REVOKE UPDATE(sealed,result_realization_id) ON ops.run FROM corpus_sem_writer;
CREATE FUNCTION ops.guard_run_lifecycle() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF NEW.status='finished' AND current_user<>'corpus_sem_publisher' THEN RAISE EXCEPTION 'finished evaluation requires protected publication'; END IF;
 IF OLD.sealed AND NOT NEW.sealed THEN RAISE EXCEPTION 'sealed run cannot reopen'; END IF;
 IF OLD.status IN ('finished','failed','cancelled') AND NEW.status<>OLD.status THEN RAISE EXCEPTION 'terminal run cannot reopen'; END IF;
 IF NEW.sealed AND NOT OLD.sealed AND NOT EXISTS(SELECT 1 FROM ops.input_cut WHERE run_id=NEW.id AND final) THEN
   RAISE EXCEPTION 'sealing requires an immutable final input cut';
 END IF;
 IF (OLD.project_id,OLD.release_id,OLD.input_realization_id,OLD.input_revision,OLD.dependencies,OLD.dependency_digest,OLD.options,OLD.guideline,OLD.code_commit,OLD.kind,OLD.phase)
 IS DISTINCT FROM
 (NEW.project_id,NEW.release_id,NEW.input_realization_id,NEW.input_revision,NEW.dependencies,NEW.dependency_digest,NEW.options,NEW.guideline,NEW.code_commit,NEW.kind,NEW.phase) THEN
   RAISE EXCEPTION 'run interpretation and inputs are immutable';
 END IF;
 RETURN NEW;
END $fn$;
ALTER FUNCTION ops.guard_run_lifecycle() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_run_lifecycle() FROM PUBLIC;
CREATE TRIGGER guard_run_lifecycle BEFORE UPDATE ON ops.run FOR EACH ROW EXECUTE FUNCTION ops.guard_run_lifecycle();

CREATE FUNCTION ops.valid_reuse(t ops.task) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT t.reused_task_id IS NULL OR (
   t.status='reused' AND t.reused_task_id<>t.id AND EXISTS(
    SELECT 1 FROM ops.task origin JOIN ops.run previous ON previous.id=origin.run_id
    JOIN ops.run current_run ON current_run.id=t.run_id
    WHERE origin.id=t.reused_task_id AND origin.status IN ('done','empty') AND origin.reused_task_id IS NULL
      AND origin.method_config_id=t.method_config_id AND origin.input_hash=t.input_hash
      AND origin.unit_type=t.unit_type AND origin.unit_id IS NOT DISTINCT FROM t.unit_id
      AND origin.unit_key IS NOT DISTINCT FROM t.unit_key AND origin.packet_hash IS NOT DISTINCT FROM t.packet_hash
      AND previous.project_id=current_run.project_id AND previous.release_id=current_run.release_id
      AND previous.input_realization_id=current_run.input_realization_id AND previous.input_revision=current_run.input_revision
      AND previous.dependencies=current_run.dependencies AND previous.dependency_digest=current_run.dependency_digest
   )
 )
$fn$;
ALTER FUNCTION ops.valid_reuse(ops.task) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.valid_reuse(ops.task) FROM PUBLIC;

CREATE FUNCTION ops.guard_task_lifecycle() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE bound ops.run;
BEGIN
 SELECT * INTO STRICT bound FROM ops.run WHERE id=NEW.run_id FOR SHARE;
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
END $fn$;
-- The invoker identity above distinguishes direct application DML from protected completion.
GRANT EXECUTE ON FUNCTION ops.valid_reuse(ops.task) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.guard_task_lifecycle() FROM PUBLIC;
CREATE TRIGGER guard_task_lifecycle BEFORE INSERT OR UPDATE ON ops.task FOR EACH ROW EXECUTE FUNCTION ops.guard_task_lifecycle();

CREATE FUNCTION ops.guard_cut_task() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE t ops.task; cut ops.input_cut; origin ops.task;
BEGIN
 SELECT * INTO STRICT cut FROM ops.input_cut WHERE id=NEW.cut_id;
 SELECT * INTO STRICT t FROM ops.task WHERE id=NEW.task_id;
 SELECT * INTO STRICT origin FROM ops.task WHERE id=NEW.origin_task_id;
 IF t.run_id<>cut.run_id OR t.release_id<>cut.release_id OR NEW.origin_task_id<>coalesce(t.reused_task_id,t.id)
    OR origin.status NOT IN ('done','empty') OR NOT ops.valid_reuse(t) THEN
   RAISE EXCEPTION 'cut task is outside its immutable binding';
 END IF;
 RETURN NEW;
END $fn$;
ALTER FUNCTION ops.guard_cut_task() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_cut_task() FROM PUBLIC;
CREATE TRIGGER guard_cut_task BEFORE INSERT ON ops.cut_task FOR EACH ROW EXECUTE FUNCTION ops.guard_cut_task();

CREATE FUNCTION ops.end_source_run(p_run bigint,p_failure jsonb DEFAULT NULL) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE r ops.run; affected bigint;
BEGIN
 SELECT * INTO STRICT r FROM ops.run WHERE id=p_run FOR UPDATE;
 IF r.status IN ('finished','failed','cancelled') THEN RETURN 0; END IF;
 UPDATE ops.task SET status='cancelled',lease_until=NULL,finished_at=clock_timestamp(),error=p_failure
 WHERE run_id=r.id AND status IN ('pending','running','awaiting_agent');
 GET DIAGNOSTICS affected=ROW_COUNT;
 UPDATE ops.run SET status=CASE WHEN p_failure IS NULL THEN 'cancelled' ELSE 'failed' END WHERE id=r.id;
 RETURN affected;
END $fn$;
ALTER FUNCTION ops.end_source_run(bigint,jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.end_source_run(bigint,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.end_source_run(bigint,jsonb) TO corpus_sem_writer;
