CREATE OR REPLACE FUNCTION ops.guard_execution_task() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE prior text; result text; agent boolean;
BEGIN
 IF NEW.data_request_id IS NOT NULL THEN
  IF current_user<>'corpus_sem_publisher' OR NOT EXISTS(SELECT FROM ops.data_request r
    WHERE r.id=NEW.data_request_id AND r.release_id=NEW.release_id AND r.generation=NEW.data_generation) THEN
   RAISE EXCEPTION 'data task requires protected admitted request generation' USING ERRCODE='23514'; END IF;
  IF TG_OP='INSERT' THEN
   IF NEW.status<>'pending' OR NEW.attempt<>0 OR NEW.claimed_by IS NOT NULL OR NEW.lease_until IS NOT NULL THEN RAISE EXCEPTION 'invalid initial data task'; END IF;
  ELSE
   IF (NEW.data_request_id,NEW.data_generation,NEW.release_id,NEW.invocation_key) IS DISTINCT FROM
      (OLD.data_request_id,OLD.data_generation,OLD.release_id,OLD.invocation_key) OR OLD.status IN ('done','empty','failed','cancelled') THEN RAISE EXCEPTION 'data task association/terminal state immutable'; END IF;
   IF NEW.attempt<>OLD.attempt THEN
    IF NEW.attempt<>OLD.attempt+1 OR NEW.status<>'running' OR nullif(NEW.claimed_by,'') IS NULL OR NEW.lease_until IS NULL OR NEW.lease_until<=clock_timestamp()
    OR OLD.status NOT IN ('pending','running') OR (OLD.status='running' AND (OLD.lease_until IS NULL OR OLD.lease_until>clock_timestamp())) THEN RAISE EXCEPTION 'invalid data claim fence'; END IF;
   ELSIF NEW.claimed_by IS DISTINCT FROM OLD.claimed_by THEN RAISE EXCEPTION 'data holder requires new attempt';
   ELSIF NEW.status<>OLD.status AND NOT (OLD.status='running' AND NEW.status IN ('done','empty','failed','cancelled')) THEN RAISE EXCEPTION 'invalid data task transition'; END IF;
  END IF;
  IF NEW.status='running' AND (NEW.attempt<=0 OR NEW.claimed_by IS NULL OR NEW.lease_until IS NULL) THEN RAISE EXCEPTION 'data running task requires exact fence'; END IF;
  IF NEW.status<>'running' AND NEW.lease_until IS NOT NULL THEN RAISE EXCEPTION 'data terminal task retains lease'; END IF;
  IF NEW.status IN ('done','empty','failed') AND NEW.result_digest IS NULL THEN RAISE EXCEPTION 'data completion requires receipt'; END IF;
  RETURN NEW;
 END IF;
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
DECLARE prior text; result text; nomination jsonb; demand jsonb; source jsonb; routes jsonb; expected jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  PERFORM sem.require_execution_operation(NEW.release_id,'start_run');
  IF NEW.runtime_id IS NULL THEN
   RAISE EXCEPTION 'new run requires an immutable runtime binding' USING ERRCODE='23514'; END IF;
  PERFORM sem.require_runtime_binding(NEW.release_id,NEW.runtime_id);
  IF NEW.options ? 'visual_nomination' THEN
   nomination:=NEW.options->'visual_nomination'; demand:=nomination->'demand';
   source:=demand->'source'; routes:=nomination->'routes';
   IF NEW.code_commit IS DISTINCT FROM 'chandra-visual-source-v1'
    OR NEW.options ?| ARRAY['visual_group','visual_request']
    OR nomination->>'version' IS DISTINCT FROM 'visual-nomination-v2'
    OR routes->>'policy' IS DISTINCT FROM 'chandra-dry-routing-v4'
    OR routes->'source' IS DISTINCT FROM source
    OR demand->>'release' IS DISTINCT FROM NEW.release_id
    OR demand->>'realization' IS DISTINCT FROM NEW.input_realization_id
    OR coalesce(demand->>'mode','') NOT IN ('selective','all-page')
    OR coalesce((demand->>'limit')::bigint,0) NOT BETWEEN 1 AND 64
    OR coalesce((demand->>'first')::bigint,0)<1
    OR jsonb_typeof(routes->'pages') IS DISTINCT FROM 'array'
    OR NOT EXISTS(SELECT FROM ops.input_cut cut JOIN ops.run origin ON origin.id=cut.run_id
     JOIN ops.cut_task member ON member.cut_id=cut.id JOIN ops.pdf_product p ON p.task_id=member.task_id
     WHERE cut.id=(demand->>'source_cut')::bigint AND origin.id=(source->>'run_id')::bigint
      AND origin.project_id=NEW.project_id AND cut.name='source-ready'
      AND member.origin_task_id=member.task_id AND p.task_id=(source->>'task_id')::bigint
      AND p.product_key=source->>'product_key' AND p.content_digest=source->>'content_digest'
      AND p.kind='integrated') THEN
    RAISE EXCEPTION 'visual nomination differs from its exact source-ready cut' USING ERRCODE='23514';
   END IF;
   IF jsonb_array_length(routes->'pages') IS DISTINCT FROM least((demand->>'limit')::bigint,
       (routes->>'page_count')::bigint-(demand->>'first')::bigint+1)
    OR EXISTS(SELECT FROM jsonb_array_elements(routes->'pages') WITH ORDINALITY q(page,n)
     WHERE page->>'page_no' IS DISTINCT FROM ((demand->>'first')::bigint+n-1)::text
      OR coalesce(page->>'action','') NOT IN ('recognize','repair','skip','unresolved')
      OR jsonb_typeof(page->'reasons') IS DISTINCT FROM 'array'
      OR jsonb_typeof(page->'cues') IS DISTINCT FROM 'array') THEN
    RAISE EXCEPTION 'visual nomination page coverage differs from its range' USING ERRCODE='23514';
   END IF;
   WITH proposed AS (
    SELECT jsonb_build_object('source',source,'page_no',page->'page_no') ||
       CASE WHEN demand->>'mode'='selective' THEN coalesce(nullif(reason->'crop','null'),'{}') ELSE '{}' END AS scope,
       page_pos,reason_pos
    FROM jsonb_array_elements(routes->'pages') WITH ORDINALITY q(page,page_pos)
    CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN demand->>'mode'='all-page' THEN '[{}]' ELSE page->'reasons' END)
     WITH ORDINALITY r(reason,reason_pos)
    WHERE demand->>'mode'='all-page' OR (page->>'action'='recognize' AND reason->>'code' IN
     ('missing_structure','incomplete_request','incomplete_ocr_region','located_disagreement','omitted_crop'))
   ), distinct_scopes AS (
    SELECT DISTINCT ON(scope) scope,page_pos,reason_pos FROM proposed ORDER BY scope,page_pos,reason_pos
   ) SELECT coalesce(jsonb_agg(scope ORDER BY page_pos,reason_pos),'[]') INTO expected FROM distinct_scopes;
   IF nomination->'selections' IS DISTINCT FROM expected THEN
    RAISE EXCEPTION 'visual nomination selections differ from its recorded routes' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.status<>'created' OR NEW.sealed OR NEW.result_realization_id IS NOT NULL THEN
   RAISE EXCEPTION 'invalid initial run combination' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.runtime_id IS DISTINCT FROM OLD.runtime_id THEN
  RAISE EXCEPTION 'run runtime binding is immutable' USING ERRCODE='23514'; END IF;
 IF NEW.result_realization_id IS NOT NULL AND OLD.options->'native_request'->>'demand'='render' THEN
  RAISE EXCEPTION 'native render runs have no evaluated realization' USING ERRCODE='23514'; END IF;
 IF NEW.result_realization_id IS NOT NULL AND OLD.code_commit='chandra-visual-source-v1'
   AND OLD.options ?| ARRAY['visual_request','visual_group','visual_nomination'] THEN
  RAISE EXCEPTION 'visual evidence runs have no evaluated realization' USING ERRCODE='23514'; END IF;
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
 IF TG_TABLE_NAME='task' AND to_jsonb(NEW)->>'data_request_id' IS NOT NULL THEN RETURN NEW; END IF;
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
 IF NEW.data_request_id IS NOT NULL THEN RETURN NEW; END IF;
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
 IF TG_OP='UPDATE' AND starts_with(OLD.unit_key,'chandra-mapping:')
  AND OLD.trigger->'visual_raw' IS DISTINCT FROM NEW.trigger->'visual_raw' THEN
   RAISE EXCEPTION 'visual mapping raw input is immutable' USING ERRCODE='23514';
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
