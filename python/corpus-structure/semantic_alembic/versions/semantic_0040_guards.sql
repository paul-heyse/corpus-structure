CREATE OR REPLACE FUNCTION ops.guard_execution_task() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE prior text; result text; agent boolean;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RETURN NEW; END IF;
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
   RAISE EXCEPTION 'invalid claim or reclaim ownership' USING ERRCODE='23514'; END IF;
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
