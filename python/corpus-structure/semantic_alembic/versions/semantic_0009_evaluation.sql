CREATE FUNCTION data.begin_evaluation(p_cut bigint,p_output text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE cut ops.input_cut; job ops.run; revision bigint; existing data.realization;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN
  RAISE EXCEPTION 'evaluation publication requires SERIALIZABLE'; END IF;
 SELECT * INTO STRICT cut FROM ops.input_cut WHERE id=p_cut;
 SELECT * INTO STRICT job FROM ops.run WHERE id=cut.run_id FOR UPDATE;
 IF NOT cut.final OR NOT job.sealed OR job.status NOT IN ('consolidating','finished') THEN
  RAISE EXCEPTION 'evaluation requires sealed final observation cut'; END IF;
 IF p_output IS NULL OR p_output='' OR p_output=job.input_realization_id THEN
  RAISE EXCEPTION 'evaluation requires a fresh output realization'; END IF;
 SELECT * INTO existing FROM data.realization WHERE realization_id=p_output;
 IF FOUND THEN
  IF job.result_realization_id IS DISTINCT FROM p_output OR existing.release_id<>job.release_id
   OR existing.project_id<>job.project_id OR existing.state<>'active' THEN
   RAISE EXCEPTION 'output realization is not this run completed result' USING ERRCODE='23505';
  END IF;
  RETURN;
 END IF;
 IF job.result_realization_id IS NOT NULL OR job.status='finished' THEN
  RAISE EXCEPTION 'run already evaluated to another realization' USING ERRCODE='23505'; END IF;
 SELECT data_revision INTO STRICT revision FROM data.realization
  WHERE realization_id=job.input_realization_id AND release_id=job.release_id FOR UPDATE;
 IF revision<>cut.source_revision OR revision<>job.input_revision THEN
  RAISE EXCEPTION 'source revision changed before evaluation publication' USING ERRCODE='P0004'; END IF;
 INSERT INTO data.realization(realization_id,project_id,release_id,state,data_revision)
  VALUES(p_output,job.project_id,job.release_id,'active',0);
 UPDATE ops.run SET result_realization_id=p_output WHERE id=job.id;
END $fn$;
ALTER FUNCTION data.begin_evaluation(bigint,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.begin_evaluation(bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.begin_evaluation(bigint,text) TO corpus_sem_writer;

CREATE FUNCTION data.finish_evaluation(p_cut bigint,p_output text,p_batch text) RETURNS void
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
ALTER FUNCTION data.finish_evaluation(bigint,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.finish_evaluation(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.finish_evaluation(bigint,text,text) TO corpus_sem_writer;
