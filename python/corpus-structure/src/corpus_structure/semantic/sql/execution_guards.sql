CREATE OR REPLACE FUNCTION ops.guard_execution_task() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE prior text; result text; agent boolean;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 result:=ops.execution_task_state(NEW);
 SELECT (m.tier='agent' OR m.family='agent') INTO STRICT agent FROM ops.method_config c JOIN ops.method m ON m.id=c.method_id WHERE c.id=NEW.method_config_id;
 IF TG_OP='INSERT' THEN
  PERFORM sem.require_execution_operation(NEW.release_id,'schedule');
  IF NEW.status NOT IN ('pending','awaiting_agent','reused','skipped') OR NEW.attempt<>0 OR NEW.claimed_by IS NOT NULL OR NEW.lease_until IS NOT NULL
    OR result<>NEW.status THEN RAISE EXCEPTION 'invalid initial task combination' USING ERRCODE='23514'; END IF;
  IF NEW.status IN ('pending','awaiting_agent') AND (NEW.status='awaiting_agent')<>agent THEN
   RAISE EXCEPTION 'task channel differs from method contract' USING ERRCODE='23514'; END IF;
  IF NEW.status='skipped' AND nullif(NEW.reason,'') IS NULL THEN RAISE EXCEPTION 'skipped task requires reason' USING ERRCODE='23514'; END IF;
  IF agent AND EXISTS (SELECT 1 FROM sem.operation_effect e WHERE e.release_id=NEW.release_id
    AND e.operation_id='schedule' AND e.effect_id='schedule_pending_or_reused_or_skipped' AND e.effect_version='2')
    AND ((NEW.status='skipped' AND NEW.packet_hash IS NOT NULL)
      OR (NEW.status<>'skipped' AND NEW.packet_hash IS NULL)) THEN
   RAISE EXCEPTION 'agent packet presence differs from invocation disposition' USING ERRCODE='23514'; END IF;
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
   RAISE EXCEPTION 'invalid claim or reclaim ownership' USING ERRCODE='23514',
    DETAIL='{"protocol":"corpus-invariant-1","guard":"execution_task","version":"2","invariant":"attempt_fence"}'; END IF;
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
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
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
 ELSIF NEW.unit_type='source_view' AND NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=NEW.run_id AND source_view_id=NEW.unit_id) THEN
   RAISE EXCEPTION 'task source view outside bound run';
 ELSIF NEW.unit_type IN ('rendition','segment','span') THEN
   RAISE EXCEPTION 'retired source task addressing requires current SourceView custody' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
