-- Located native projection addresses satisfy the same sealed occurrence-evidence obligation as legacy spans.
CREATE OR REPLACE FUNCTION data.finish_pre_context_evaluation(p_cut bigint,p_output text,p_batch text) RETURNS void
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
      AND (es.span_id IS NOT NULL OR (es.source_view_id IS NOT NULL AND es.native_address IS NOT NULL AND ops.native_source_address(es.source_view_id,es.native_address)=es.native_address)))) THEN
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
