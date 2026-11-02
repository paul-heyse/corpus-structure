-- Operator guidance is recorded input provenance for one active run, not a model assertion.
CREATE OR REPLACE FUNCTION ops.record_direction(
 p_run bigint,p_actor text,p_session text,p_body jsonb
) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $body$
DECLARE selected_release text; result bigint;
BEGIN
 IF p_actor IS NULL OR p_actor='' OR p_session IS NULL OR p_session='' OR
    jsonb_typeof(p_body) IS DISTINCT FROM 'object' OR
    p_body->>'text' IS NULL OR p_body->>'scope' IS NULL THEN
  RAISE EXCEPTION 'direction run binding differs or run no longer active'
   USING ERRCODE='23514';
 END IF;
 SELECT release_id INTO selected_release FROM ops.run
  WHERE id=p_run AND project_id=p_body->>'project_id'
    AND status IN ('created','running') FOR SHARE;
 IF NOT FOUND THEN
  RAISE EXCEPTION 'direction run binding differs or run no longer active'
   USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(
  SELECT FROM sem.release r JOIN sem.execution_operation o ON o.release_id=r.release_id
  WHERE r.release_id=selected_release AND r.profile='semantic-2'
    AND o.operation_id='record_direction'
 ) THEN
  RAISE EXCEPTION 'direction requires a composed run release declaring record_direction'
   USING ERRCODE='23514';
 END IF;
 PERFORM sem.require_execution_operation(selected_release,'record_direction');
 INSERT INTO ops.intervention(run_id,actor,session_ref,kind,body)
  VALUES(p_run,p_actor,p_session,'direction',p_body) RETURNING id INTO result;
 RETURN result;
END $body$;
ALTER FUNCTION ops.record_direction(bigint,text,text,jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.record_direction(bigint,text,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.record_direction(bigint,text,text,jsonb) TO corpus_sem_writer;
