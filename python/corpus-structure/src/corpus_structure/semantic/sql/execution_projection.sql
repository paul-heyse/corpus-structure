-- Stable relational consumers. Candidate releases supply rows, never SQL identifiers or bodies.
CREATE OR REPLACE FUNCTION sem.require_execution_operation(r text,operation text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $operation$
DECLARE supported jsonb; actual jsonb; expected jsonb; archived_abi text;
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 SELECT convert_from(body,'UTF8')::jsonb->'inputs'->>'compiler_version' INTO archived_abi
 FROM sem.registry_row WHERE release_id=r AND kind='execution_model';
 IF archived_abi IS DISTINCT FROM data.execution_contract_descriptor()->>'execution_abi'
 AND operation NOT IN ('reload','open_read','query','explain','compile_projection',
  'capture_analytics','open_analysis','close_analysis','graph_project','graph_validate',
  'read_original','read_native_source','read_source_view','read_pdf_product') THEN
  RAISE EXCEPTION 'historical execution ABI is read-only: %',archived_abi USING ERRCODE='23514'; END IF;
 supported:=data.execution_contract_descriptor()->'supported_effects'->operation;
 IF supported IS NULL OR NOT EXISTS(SELECT FROM sem.execution_operation o WHERE o.release_id=r AND o.operation_id=operation
  AND o.implementation_id=supported->>'implementation' AND o.implementation_version=supported->>'version') THEN
  RAISE EXCEPTION 'unsupported execution operation % in release %',operation,r USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.operation_effect e WHERE e.release_id=r AND e.operation_id=operation
  AND e.effect_version IS DISTINCT FROM data.execution_contract_descriptor()->'supported_effect_versions'->>e.effect_id)
 OR EXISTS(SELECT FROM sem.transition_effect e JOIN sem.execution_transition t USING(release_id,transition_id)
  WHERE e.release_id=r AND t.operation_id=operation
  AND e.effect_version IS DISTINCT FROM data.execution_contract_descriptor()->'supported_effect_versions'->>e.effect_id) THEN
  RAISE EXCEPTION 'unsupported execution effect version for %',operation USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(effect_id ORDER BY effect_id),'[]'::jsonb) INTO actual
 FROM sem.operation_effect WHERE release_id=r AND operation_id=operation;
 IF actual IS DISTINCT FROM supported->'effects' THEN
  RAISE EXCEPTION 'unsupported execution effects for %',operation USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_object_agg(t.transition_id,COALESCE((SELECT jsonb_agg(e.effect_id ORDER BY e.effect_id)
  FROM sem.transition_effect e WHERE e.release_id=r AND e.transition_id=t.transition_id),'[]'::jsonb)),'{}'::jsonb) INTO actual
 FROM sem.execution_transition t WHERE t.release_id=r AND t.operation_id=operation;
 IF actual IS DISTINCT FROM supported->'transitions' THEN
  RAISE EXCEPTION 'unsupported transition effects for %',operation USING ERRCODE='23514'; END IF;
END $operation$;
REVOKE ALL ON FUNCTION sem.require_execution_operation(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sem.require_execution_operation(text,text) TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION ops.execution_edge(r text,lifecycle text,prior text,result text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $edge$
 SELECT EXISTS(SELECT FROM sem.execution_edge e JOIN sem.execution_transition t USING(release_id,transition_id)
 WHERE e.release_id=$1 AND t.lifecycle=$2 AND e.prior_state=$3 AND e.result_state=$4)
$edge$;
REVOKE ALL ON FUNCTION ops.execution_edge(text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.execution_edge(text,text,text,text) TO corpus_sem_writer,corpus_sem_reader;

CREATE OR REPLACE FUNCTION ops.require_transition(r text,operation text,prior text,result text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $transition$
BEGIN
 PERFORM sem.require_execution_operation(r,operation);
 IF EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') AND NOT EXISTS(
  SELECT FROM sem.execution_edge e JOIN sem.execution_transition t USING(release_id,transition_id)
  WHERE e.release_id=r AND t.operation_id=operation AND e.prior_state=prior AND e.result_state=result) THEN
  RAISE EXCEPTION 'undeclared operation transition %: % -> %',operation,prior,result USING ERRCODE='23514'; END IF;
END $transition$;
REVOKE ALL ON FUNCTION ops.require_transition(text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.require_transition(text,text,text,text) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.start_source_run(p_run bigint) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $start$
DECLARE job ops.run;
BEGIN
 SELECT * INTO STRICT job FROM ops.run WHERE id=p_run FOR UPDATE;
 PERFORM sem.require_execution_operation(job.release_id,'execute_source');
 IF job.status='running' AND NOT job.sealed THEN RETURN job.id; END IF;
 IF job.status<>'created' OR job.sealed THEN RAISE EXCEPTION 'run no longer accepts source execution' USING ERRCODE='P0004'; END IF;
 PERFORM ops.require_transition(job.release_id,'execute_source','created','running');
 UPDATE ops.run SET status='running' WHERE id=job.id;
 RETURN job.id;
END $start$;
REVOKE ALL ON FUNCTION ops.start_source_run(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.start_source_run(bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.claim_tasks(p_run bigint,p_config bigint,p_holder text,p_limit bigint,p_agent boolean) RETURNS SETOF ops.task
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $claim$
DECLARE job ops.run;
BEGIN
 IF p_limit<1 OR nullif(p_holder,'') IS NULL THEN RAISE EXCEPTION 'positive claim limit and nonempty holder required'; END IF;
 SELECT * INTO STRICT job FROM ops.run WHERE id=p_run FOR SHARE;
 PERFORM sem.require_execution_operation(job.release_id,'claim');
 IF job.sealed OR job.status NOT IN ('created','running') THEN RETURN; END IF;
 RETURN QUERY WITH candidates AS MATERIALIZED (
  SELECT id FROM ops.task WHERE run_id=p_run AND method_config_id=p_config
   AND (status=CASE WHEN p_agent THEN 'awaiting_agent' ELSE 'pending' END OR (status='running' AND lease_until<clock_timestamp()))
  AND NOT EXISTS(SELECT FROM ops.task_dependency d JOIN ops.task prerequisite ON prerequisite.id=d.dependency_task_id WHERE d.task_id=ops.task.id AND prerequisite.status NOT IN ('done','empty','reused'))
  ORDER BY priority DESC,id LIMIT p_limit FOR UPDATE SKIP LOCKED
 ) UPDATE ops.task t SET status='running',attempt=t.attempt+1,claimed_by=p_holder,
  lease_until=clock_timestamp()+interval '5 minutes',started_at=COALESCE(t.started_at,clock_timestamp())
 FROM candidates c WHERE t.id=c.id RETURNING t.*;
END $claim$;
REVOKE ALL ON FUNCTION ops.claim_tasks(bigint,bigint,text,bigint,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.claim_tasks(bigint,bigint,text,bigint,boolean) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.renew_claim(p_task bigint,p_attempt bigint,p_holder text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $renew$
DECLARE t ops.task; job ops.run;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT job FROM ops.run WHERE id=t.run_id FOR SHARE;
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task FOR UPDATE;
 IF job.sealed OR job.status NOT IN ('created','running') OR t.status<>'running'
  OR t.attempt<>p_attempt OR nullif(p_holder,'') IS NULL OR t.claimed_by IS DISTINCT FROM p_holder
  OR t.lease_until IS NULL OR t.lease_until<=clock_timestamp() THEN
  RAISE EXCEPTION 'claim ownership lost before renewal' USING ERRCODE='P0004'; END IF;
 UPDATE ops.task SET lease_until=clock_timestamp()+interval '5 minutes' WHERE id=p_task;
END $renew$;
REVOKE ALL ON FUNCTION ops.renew_claim(bigint,bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.renew_claim(bigint,bigint,text) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.lock_execution_run(p_run bigint,operation text) RETURNS ops.run
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $lock$
DECLARE job ops.run;
BEGIN
 SELECT * INTO STRICT job FROM ops.run WHERE id=p_run FOR SHARE;
 PERFORM sem.require_execution_operation(job.release_id,operation);
 RETURN job;
END $lock$;
REVOKE ALL ON FUNCTION ops.lock_execution_run(bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.lock_execution_run(bigint,text) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION sem.require_scientific_layout(r text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $layout$
DECLARE recipe jsonb; supported jsonb;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO recipe FROM sem.artifact
 WHERE release_id=r AND artifact_name='operation/scientific-policy.json';
 supported:=data.execution_contract_descriptor()->'scientific_report_layout';
 IF recipe IS NULL OR supported IS NULL
  OR jsonb_build_object('comparison_paths',recipe->'comparison_paths','array_rules',recipe->'array_rules')
     IS DISTINCT FROM supported THEN
  RAISE EXCEPTION 'unsupported scientific report layout in release %',r USING ERRCODE='23514'; END IF;
END $layout$;
REVOKE ALL ON FUNCTION sem.require_scientific_layout(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.guard_scientific_decisions() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $scientific$
DECLARE r text; recipe jsonb; rule jsonb; parent jsonb; reference_protocol text; operation_protocol text;
BEGIN
 SELECT release_id,sampling->>'record_protocol',sampling->>'operation_protocol'
 INTO STRICT r,reference_protocol,operation_protocol
  FROM eval.reference_set WHERE id=NEW.set_id;
 IF operation_protocol IS NOT NULL OR NEW.result->>'protocol'='source-operation-evaluation-1' THEN
  IF operation_protocol IS DISTINCT FROM 'source-operation-reference-1'
   OR reference_protocol IS NOT NULL OR NEW.result->>'family'='source_records'
   OR NEW.result->>'protocol' IS DISTINCT FROM 'source-operation-evaluation-1' THEN
   RAISE EXCEPTION 'reference family and trusted set protocol differ' USING ERRCODE='23514';
  END IF;
  PERFORM eval.validate_operation_reference_evaluation(
   NEW.project_id,NEW.run_id,NEW.set_id,NEW.reference_snapshot,NEW.result);
  RETURN NEW;
 END IF;
 IF reference_protocol='source-record-reference-1'
  OR NEW.result->>'family'='source_records'
  OR NEW.result->>'protocol'='source-record-evaluation-1' THEN
  IF reference_protocol IS DISTINCT FROM 'source-record-reference-1'
   OR NEW.result->>'family' IS DISTINCT FROM 'source_records'
   OR NEW.result->>'protocol' IS DISTINCT FROM 'source-record-evaluation-1' THEN
   RAISE EXCEPTION 'reference family and trusted set protocol differ' USING ERRCODE='23514';
  END IF;
  PERFORM eval.validate_source_record_reference_evaluation(
   NEW.project_id,NEW.run_id,NEW.set_id,NEW.reference_snapshot,NEW.result);
  RETURN NEW;
 END IF;
 PERFORM sem.require_execution_operation(r,'reference_grade');
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_scientific_layout(r);
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT recipe FROM sem.artifact
 WHERE release_id=r AND artifact_name='operation/scientific-policy.json';
 IF jsonb_typeof(recipe->'comparison_paths') IS DISTINCT FROM 'array'
  OR jsonb_typeof(recipe->'array_rules') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'scientific report recipe lacks supported paths and array rules' USING ERRCODE='23514'; END IF;
 BEGIN
  FOR rule IN SELECT value FROM jsonb_array_elements(recipe->'array_rules') LOOP
   FOR parent IN SELECT jsonb_path_query(NEW.result,('strict '||(rule->>'parent_path'))::jsonpath) LOOP
    IF jsonb_typeof(parent) IS DISTINCT FROM 'object'
     OR (((rule->>'required')::boolean OR parent ? (rule->>'field'))
         AND jsonb_typeof(parent->(rule->>'field')) IS DISTINCT FROM 'array') THEN
     RAISE EXCEPTION 'scientific report array differs at %.%',rule->>'parent_path',rule->>'field'
      USING ERRCODE='23514'; END IF;
   END LOOP;
  END LOOP;
 EXCEPTION WHEN data_exception THEN
  RAISE EXCEPTION 'scientific report structure differs from bound model' USING ERRCODE='23514';
 END;
 -- Container shape is established above; lax missing-member handling preserves optional leaves.
 IF EXISTS(
  SELECT FROM (
   SELECT comparison FROM jsonb_array_elements_text(recipe->'comparison_paths') path
   CROSS JOIN LATERAL jsonb_path_query(NEW.result,path.value::jsonpath) comparison
  ) reported LEFT JOIN sem.scientific_decision_rule decision
   ON decision.release_id=r AND decision.policy_id=reported.comparison->>'policy_id'
   AND decision.evidence_tier=reported.comparison->>'evidence_tier'
   AND decision.agreement=reported.comparison->>'agreement'
  WHERE decision.policy_id IS NULL OR decision.decision IS DISTINCT FROM reported.comparison->>'outcome'
   OR decision.decision_tier IS DISTINCT FROM reported.comparison->>'decision_tier'
 ) THEN RAISE EXCEPTION 'scientific decision differs from bound evidence policy' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $scientific$;
REVOKE ALL ON FUNCTION eval.guard_scientific_decisions() FROM PUBLIC;
CREATE TRIGGER scientific_decisions BEFORE INSERT ON eval.reference_evaluation FOR EACH ROW EXECUTE FUNCTION eval.guard_scientific_decisions();
SET LOCAL ROLE corpus_sem_publisher;

CREATE OR REPLACE FUNCTION ops.lock_finalization_run(p_run bigint) RETURNS ops.run
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $finalization$
DECLARE job ops.run;
BEGIN
 SELECT * INTO STRICT job FROM ops.run WHERE id=p_run FOR UPDATE;
 PERFORM sem.require_execution_operation(job.release_id,'evaluate');
 RETURN job;
END $finalization$;
REVOKE ALL ON FUNCTION ops.lock_finalization_run(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.lock_finalization_run(bigint) TO corpus_sem_writer;
