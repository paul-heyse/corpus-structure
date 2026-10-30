-- Stable relational consumers. Candidate releases supply rows, never SQL identifiers or bodies.
CREATE OR REPLACE FUNCTION sem.require_execution_operation(r text,operation text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $operation$
DECLARE supported jsonb; actual jsonb; expected jsonb;
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RETURN; END IF;
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
  ORDER BY priority DESC,id LIMIT p_limit FOR UPDATE SKIP LOCKED
 ) UPDATE ops.task t SET status='running',attempt=t.attempt+1,claimed_by=p_holder,
  lease_until=clock_timestamp()+interval '5 minutes',started_at=COALESCE(t.started_at,clock_timestamp())
 FROM candidates c WHERE t.id=c.id RETURNING t.*;
END $claim$;
REVOKE ALL ON FUNCTION ops.claim_tasks(bigint,bigint,text,bigint,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.claim_tasks(bigint,bigint,text,bigint,boolean) TO corpus_sem_writer;

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

CREATE OR REPLACE FUNCTION eval.guard_scientific_decisions() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $scientific$
DECLARE r text;
BEGIN
 SELECT release_id INTO STRICT r FROM eval.reference_set WHERE id=NEW.set_id;
 PERFORM sem.require_execution_operation(r,'reference_grade');
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RETURN NEW; END IF;
 IF jsonb_typeof(NEW.result->'units') IS DISTINCT FROM 'array'
  OR jsonb_typeof(NEW.result->'undecided') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'scientific report requires typed units and undecided arrays' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements((NEW.result->'units')||(NEW.result->'undecided')) unit
  WHERE jsonb_typeof(unit) IS DISTINCT FROM 'object' OR jsonb_typeof(unit->'comparisons') IS DISTINCT FROM 'array') THEN
  RAISE EXCEPTION 'scientific report unit requires comparisons array' USING ERRCODE='23514'; END IF;

 IF EXISTS(
  SELECT FROM (
   SELECT comparison FROM jsonb_array_elements(COALESCE(NEW.result->'units','[]'::jsonb)||COALESCE(NEW.result->'undecided','[]'::jsonb)) unit
   CROSS JOIN LATERAL jsonb_array_elements(COALESCE(unit->'comparisons','[]'::jsonb)) comparison
  ) reported LEFT JOIN sem.scientific_decision_rule rule
   ON rule.release_id=r AND rule.policy_id=reported.comparison->>'policy_id'
   AND rule.evidence_tier=reported.comparison->>'evidence_tier' AND rule.agreement=reported.comparison->>'agreement'
  WHERE rule.policy_id IS NULL OR rule.decision IS DISTINCT FROM reported.comparison->>'outcome'
   OR rule.decision_tier IS DISTINCT FROM reported.comparison->>'decision_tier'
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
