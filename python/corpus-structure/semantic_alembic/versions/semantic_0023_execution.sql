-- Frozen finite edge projection of execution-model.yaml. Generated at development time.
-- Historical migration execution never imports installed model/compiler code.
CREATE FUNCTION ops.execution_edge(lifecycle text,prior text,result text) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT EXISTS(SELECT 1 FROM (VALUES
('analysis','candidate_open_borrowed','candidate_closed_invalidated'),
('analysis','candidate_open_detached','candidate_closed_detached'),
('analysis','candidate_open_none','candidate_closed_none'),
('analysis','captured_open_borrowed','captured_closed_invalidated'),
('analysis','captured_open_detached','captured_closed_detached'),
('analysis','captured_open_none','captured_closed_none'),
('evaluation_result','private','completed'),
('realization','writable','completed'),
('run','consolidating','cancelled_sealed'),
('run','consolidating','failed_sealed'),
('run','consolidating','finished'),
('run','created','cancelled_open'),
('run','created','consolidating'),
('run','created','failed_open'),
('run','created','running'),
('run','running','cancelled_open'),
('run','running','consolidating'),
('run','running','failed_open'),
('submission','held','accepted'),
('submission','held','refused'),
('submission','new','clean'),
('submission','new','context_refused'),
('submission','new','held'),
('task','awaiting_agent','cancelled'),
('task','awaiting_agent','running'),
('task','pending','cancelled'),
('task','pending','running'),
('task','running','cancelled'),
('task','running','done'),
('task','running','empty'),
('task','running','failed'),
('task','running','running'),
('task','running','running_held'),
('task','running_held','cancelled_held'),
('task','running_held','done_held'),
('task','running_held','empty_held'),
('task','running_held','failed_held'),
('task','running_held','running_held')) allowed(lifecycle,prior,result) WHERE allowed.lifecycle=$1 AND allowed.prior=$2 AND allowed.result=$3)
$fn$;
REVOKE ALL ON FUNCTION ops.execution_edge(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.execution_edge(text,text,text) TO corpus_sem_writer,corpus_sem_reader,corpus_sem_publisher;
CREATE TABLE sem.conditional_rule(
 release_id text NOT NULL REFERENCES sem.release(release_id),rule_id text NOT NULL,
 class_id text NOT NULL,scope text NOT NULL CHECK(scope IN ('shape','accepted_value')),
 PRIMARY KEY(release_id,rule_id),
 FOREIGN KEY(release_id,class_id) REFERENCES sem.class_definition(release_id,class_id)
);
CREATE TABLE sem.conditional_atom(
 release_id text NOT NULL,rule_id text NOT NULL,branch text NOT NULL CHECK(branch IN ('if','then','else')),
 position bigint NOT NULL CHECK(position>=0),property_name text NOT NULL,
 presence text NOT NULL CHECK(presence IN ('present','absent','optional')),choices jsonb,
 PRIMARY KEY(release_id,rule_id,branch,position),
 FOREIGN KEY(release_id,rule_id) REFERENCES sem.conditional_rule(release_id,rule_id),
 CHECK(choices IS NULL OR choices='null'::jsonb OR jsonb_typeof(choices)='array')
);
GRANT SELECT ON sem.conditional_rule,sem.conditional_atom TO corpus_sem_writer,corpus_sem_reader;
CREATE TABLE ops.completed_result(
 run_id bigint PRIMARY KEY REFERENCES ops.run(id),release_id text NOT NULL,
 output_realization_id text NOT NULL,cut_id bigint NOT NULL REFERENCES ops.input_cut(id),
 batch_id text NOT NULL,dependency_digest text NOT NULL,source_receipts jsonb NOT NULL,proof_receipts jsonb NOT NULL,
 UNIQUE(release_id,output_realization_id),
 FOREIGN KEY(release_id,output_realization_id) REFERENCES data.realization(release_id,realization_id),
 FOREIGN KEY(release_id,output_realization_id,batch_id) REFERENCES data.batch(release_id,realization_id,batch_id)
);
GRANT SELECT ON ops.completed_result TO corpus_sem_reader,corpus_sem_writer;
GRANT SELECT ON sem.conditional_rule,sem.conditional_atom TO corpus_sem_publisher;
GRANT SELECT,INSERT ON ops.completed_result TO corpus_sem_publisher;
CREATE FUNCTION data.validate_conditions(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE violation record;
BEGIN
 WITH RECURSIVE accepted(v) AS (
  SELECT roots.v FROM data.fact f JOIN data.selection s USING(release_id,realization_id,fact_id)
  CROSS JOIN LATERAL(VALUES(f.object_value_id),(f.qualification_value_id)) roots(v)
  WHERE f.release_id=r AND f.realization_id=z AND roots.v IS NOT NULL
  UNION SELECT vr.child_value_id FROM data.value_role vr JOIN accepted a ON a.v=vr.parent_value_id
  WHERE vr.release_id=r AND vr.realization_id=z
 ), subjects AS MATERIALIZED(
  SELECT rule.rule_id,rule.class_id,rule.scope,'record'::text AS kind,v.value_id AS subject
  FROM sem.conditional_rule rule JOIN data.typed_value v
   ON v.release_id=r AND v.realization_id=z AND v.datatype=rule.class_id
  WHERE rule.release_id=r AND (rule.scope='shape' OR EXISTS(SELECT 1 FROM accepted WHERE accepted.v=v.value_id))
  UNION ALL
  SELECT rule.rule_id,rule.class_id,rule.scope,'entity',m.entity_id
  FROM sem.conditional_rule rule JOIN data.membership m
   ON m.release_id=r AND m.realization_id=z AND m.class_id=rule.class_id
  WHERE rule.release_id=r
 ), members AS MATERIALIZED(
  SELECT s.rule_id,s.kind,s.subject,vr.role AS property_name,v.kind AS value_kind,v.text_value,
   data.canonical_json(data.value_meaning(r,z,v.value_id)) AS meaning
  FROM subjects s JOIN data.value_role vr ON s.kind='record' AND vr.release_id=r
   AND vr.realization_id=z AND vr.parent_value_id=s.subject
  JOIN data.typed_value v ON v.release_id=r AND v.realization_id=z AND v.value_id=vr.child_value_id
  UNION ALL
  SELECT s.rule_id,s.kind,s.subject,pa.constraints->>'name',v.kind,v.text_value,
   data.canonical_json(data.value_meaning(r,z,v.value_id))
  FROM subjects s JOIN sem.property_applicability pa ON s.kind='entity' AND pa.release_id=r AND pa.class_id=s.class_id
  JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.subject_id=s.subject AND f.property_id=pa.property_id
  JOIN data.typed_value v ON v.release_id=r AND v.realization_id=z AND v.value_id=f.object_value_id
  WHERE s.scope='shape' OR EXISTS(SELECT 1 FROM data.selection selected
   WHERE (selected.release_id,selected.realization_id,selected.fact_id)=(r,z,f.fact_id))
 ), atoms AS(
  SELECT s.rule_id,s.kind,s.subject,a.branch,a.position,count(DISTINCT m.meaning) AS cardinality,
   CASE a.presence WHEN 'present' THEN count(m.meaning)>0 WHEN 'absent' THEN count(m.meaning)=0 ELSE true END
    AND (a.choices IS NULL OR a.choices='null'::jsonb OR coalesce(bool_and(m.value_kind='string' AND a.choices ? m.text_value),true)) AS valid
  FROM subjects s JOIN sem.conditional_atom a ON a.release_id=r AND a.rule_id=s.rule_id
  LEFT JOIN members m ON (m.rule_id,m.kind,m.subject,m.property_name)=(s.rule_id,s.kind,s.subject,a.property_name)
  GROUP BY s.rule_id,s.kind,s.subject,a.branch,a.position,a.presence,a.choices
 ), branches AS(
  SELECT s.rule_id,s.kind,s.subject,
   coalesce(bool_and(a.valid) FILTER(WHERE a.branch='if'),true) AS antecedent,
   coalesce(bool_and(a.valid) FILTER(WHERE a.branch='then'),true) AS consequence,
   coalesce(bool_and(a.valid) FILTER(WHERE a.branch='else'),true) AS alternative,
   coalesce(bool_or(a.cardinality>1),false) AS ambiguous
  FROM subjects s LEFT JOIN atoms a USING(rule_id,kind,subject)
  GROUP BY s.rule_id,s.kind,s.subject
 ) SELECT * INTO violation FROM branches
 WHERE ambiguous OR NOT(CASE WHEN antecedent THEN consequence ELSE alternative END)
 ORDER BY rule_id,kind,subject LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'conditional rule violation' USING ERRCODE='23514',
  DETAIL=jsonb_build_object('rule_id',violation.rule_id,'subject_kind',violation.kind,
   'subject',violation.subject,'ambiguous',violation.ambiguous)::text;
 END IF;
END $fn$;
ALTER FUNCTION data.validate_conditions(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_conditions(text,text) FROM PUBLIC;
SET LOCAL ROLE corpus_sem_publisher;
ALTER FUNCTION data.validate_state(text,text) RENAME TO validate_pre_contract_state;
REVOKE ALL ON FUNCTION data.validate_pre_contract_state(text,text) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
CREATE FUNCTION data.validate_state(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 PERFORM data.validate_pre_contract_state(r,z);
 PERFORM data.validate_conditions(r,z);
END $fn$;
ALTER FUNCTION data.validate_state(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_state(text,text) FROM PUBLIC;

ALTER FUNCTION data.finish_evaluation(bigint,text,text) RENAME TO finish_pre_contract_evaluation;
REVOKE ALL ON FUNCTION data.finish_pre_contract_evaluation(bigint,text,text) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
CREATE FUNCTION data.finish_evaluation(p_cut bigint,p_output text,p_batch text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE job ops.run; completed ops.completed_result;
BEGIN
 SELECT jobrow.* INTO STRICT job FROM ops.run jobrow JOIN ops.input_cut cut ON cut.run_id=jobrow.id
  WHERE cut.id=p_cut FOR UPDATE OF jobrow;
 SELECT * INTO completed FROM ops.completed_result WHERE run_id=job.id;
 IF FOUND THEN
  IF (completed.cut_id,completed.output_realization_id,completed.batch_id)
    IS DISTINCT FROM(p_cut,p_output,p_batch) THEN
   RAISE EXCEPTION 'completed result identity conflict' USING ERRCODE='23505';
  END IF;
  RETURN;
 END IF;
 PERFORM data.finish_pre_contract_evaluation(p_cut,p_output,p_batch);
 INSERT INTO ops.completed_result(run_id,release_id,output_realization_id,cut_id,batch_id,
  dependency_digest,source_receipts,proof_receipts)
 VALUES(job.id,job.release_id,p_output,p_cut,p_batch,job.dependency_digest,
  coalesce((SELECT jsonb_agg(jsonb_build_object('task_id',ct.origin_task_id) ORDER BY ct.origin_task_id)
   FROM ops.cut_task ct WHERE ct.cut_id=p_cut),'[]'::jsonb),
  coalesce((SELECT jsonb_agg(jsonb_build_object('derivation_id',d.derivation_id) ORDER BY d.derivation_id)
   FROM data.derivation d WHERE d.release_id=job.release_id AND d.realization_id=p_output),'[]'::jsonb));
END $fn$;
ALTER FUNCTION data.finish_evaluation(bigint,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.finish_evaluation(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.finish_evaluation(bigint,text,text) TO corpus_sem_writer;

SET LOCAL ROLE __MIGRATION_OWNER__;
CREATE FUNCTION ops.execution_task_state(t ops.task) RETURNS text
LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT t.status || CASE WHEN coalesce(t.error ? 'semantic_proposal_first_result',false) THEN '_held' ELSE '' END
$fn$;
REVOKE ALL ON FUNCTION ops.execution_task_state(ops.task) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.execution_task_state(ops.task) TO corpus_sem_writer;
CREATE FUNCTION ops.guard_execution_task() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE prior text; result text; agent boolean;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RETURN NEW; END IF;
 result:=ops.execution_task_state(NEW);
 SELECT (m.tier='agent' OR m.family='agent') INTO STRICT agent FROM ops.method_config c JOIN ops.method m ON m.id=c.method_id WHERE c.id=NEW.method_config_id;
 IF TG_OP='INSERT' THEN
  IF NEW.status NOT IN ('pending','awaiting_agent','reused','skipped') OR NEW.attempt<>0 OR NEW.claimed_by IS NOT NULL OR NEW.lease_until IS NOT NULL
    OR result<>NEW.status THEN RAISE EXCEPTION 'invalid initial task combination' USING ERRCODE='23514'; END IF;
  IF NEW.status IN ('pending','awaiting_agent') AND (NEW.status='awaiting_agent')<>agent THEN
   RAISE EXCEPTION 'task channel differs from method contract' USING ERRCODE='23514'; END IF;
  IF NEW.status='skipped' AND nullif(NEW.reason,'') IS NULL THEN RAISE EXCEPTION 'skipped task requires reason' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 prior:=ops.execution_task_state(OLD);
 IF NEW.attempt IS DISTINCT FROM OLD.attempt THEN
  IF NEW.attempt<>OLD.attempt+1 OR NEW.status<>'running' OR nullif(NEW.claimed_by,'') IS NULL
    OR NEW.lease_until IS NULL OR NEW.lease_until<=clock_timestamp()
    OR (OLD.status='running' AND (OLD.lease_until IS NULL OR OLD.lease_until>=clock_timestamp()))
    OR NOT ops.execution_edge('task',prior,result) THEN
   RAISE EXCEPTION 'invalid claim or reclaim ownership' USING ERRCODE='23514'; END IF;
 ELSIF NEW.claimed_by IS DISTINCT FROM OLD.claimed_by THEN
  RAISE EXCEPTION 'holder mutation requires a new attempt' USING ERRCODE='23514';
 ELSIF prior<>result AND NOT ops.execution_edge('task',prior,result) THEN
  RAISE EXCEPTION 'undeclared task transition % -> %',prior,result USING ERRCODE='23514';
 END IF;
 IF OLD.error ? 'semantic_proposal_first_result' AND OLD.error->'semantic_proposal_first_result'
  IS DISTINCT FROM NEW.error->'semantic_proposal_first_result' THEN
  RAISE EXCEPTION 'held first result is immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.status<>'running' AND NEW.lease_until IS NOT NULL THEN
  RAISE EXCEPTION 'terminal task cannot retain a live lease' USING ERRCODE='23514'; END IF;
 IF NEW.status='running' AND (NEW.attempt<=0 OR nullif(NEW.claimed_by,'') IS NULL OR NEW.lease_until IS NULL) THEN
  RAISE EXCEPTION 'running task requires current attempt ownership' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_execution_task() FROM PUBLIC;
CREATE TRIGGER zz_execution_task BEFORE INSERT OR UPDATE ON ops.task FOR EACH ROW EXECUTE FUNCTION ops.guard_execution_task();
CREATE FUNCTION ops.guard_execution_run() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE prior text; result text;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RETURN NEW; END IF;
 prior:=OLD.status || CASE WHEN OLD.status IN ('failed','cancelled') THEN CASE WHEN OLD.sealed THEN '_sealed' ELSE '_open' END ELSE '' END;
 result:=NEW.status || CASE WHEN NEW.status IN ('failed','cancelled') THEN CASE WHEN NEW.sealed THEN '_sealed' ELSE '_open' END ELSE '' END;
 IF prior<>result AND NOT ops.execution_edge('run',prior,result) THEN
  RAISE EXCEPTION 'undeclared run transition % -> %',prior,result USING ERRCODE='23514'; END IF;
 IF NEW.sealed<>(NEW.status IN ('consolidating','finished') OR (NEW.status IN ('failed','cancelled') AND OLD.sealed)) THEN
  RAISE EXCEPTION 'invalid run sealing combination' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_execution_run() FROM PUBLIC;
CREATE TRIGGER zz_execution_run BEFORE UPDATE ON ops.run FOR EACH ROW EXECUTE FUNCTION ops.guard_execution_run();
CREATE FUNCTION ops.require_completed_result() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF NEW.status='finished' AND EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2')
 AND NOT EXISTS(SELECT 1 FROM ops.completed_result WHERE run_id=NEW.id AND release_id=NEW.release_id AND output_realization_id=NEW.result_realization_id) THEN
  RAISE EXCEPTION 'finished run requires completed EvaluationResult' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $fn$;
REVOKE ALL ON FUNCTION ops.require_completed_result() FROM PUBLIC;
CREATE CONSTRAINT TRIGGER completed_result_required AFTER UPDATE ON ops.run
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ops.require_completed_result();
CREATE TABLE data.publication_intent(
 release_id text NOT NULL,realization_id text NOT NULL,batch_id text NOT NULL,
 source_release_id text NOT NULL,source_realization_id text NOT NULL,source_revision bigint NOT NULL CHECK(source_revision>=0),
 source_capture_id text NOT NULL,operation_id text NOT NULL,projection_id text NOT NULL,
 PRIMARY KEY(release_id,realization_id,batch_id),
 FOREIGN KEY(release_id,realization_id,batch_id) REFERENCES data.batch(release_id,realization_id,batch_id),
 FOREIGN KEY(source_release_id,source_realization_id) REFERENCES data.realization(release_id,realization_id),
 CHECK(source_capture_id<>'' AND operation_id<>'' AND projection_id<>'')
);
GRANT SELECT ON data.publication_intent TO corpus_sem_reader,corpus_sem_writer;
GRANT SELECT,INSERT ON data.publication_intent TO corpus_sem_publisher;
SET LOCAL ROLE corpus_sem_publisher;
ALTER FUNCTION data.publish_batch(text,text,text,bytea) RENAME TO publish_contract_batch;
REVOKE ALL ON FUNCTION data.publish_contract_batch(text,text,text,bytea) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
CREATE FUNCTION data.publish_batch(r text,z text,b text,p_content bytea) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF EXISTS(SELECT 1 FROM data.publication_intent WHERE (release_id,realization_id,batch_id)=(r,z,b)) THEN
  RAISE EXCEPTION 'derived receipt requires its immutable source intent' USING ERRCODE='23505'; END IF;
 RETURN data.publish_contract_batch(r,z,b,p_content);
END $fn$;
ALTER FUNCTION data.publish_batch(text,text,text,bytea) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.publish_batch(text,text,text,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_batch(text,text,text,bytea) TO corpus_sem_writer;
CREATE FUNCTION data.publish_derived_batch(r text,z text,b text,p_content bytea,
 source_release text,source_realization text,source_revision bigint,source_capture text,
 operation text,projection text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE previous data.publication_intent; actual bigint; published bigint;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'derived publication requires SERIALIZABLE'; END IF;
 SELECT * INTO previous FROM data.publication_intent WHERE (release_id,realization_id,batch_id)=(r,z,b);
 IF FOUND THEN
  IF (previous.source_release_id,previous.source_realization_id,previous.source_revision,
   previous.source_capture_id,previous.operation_id,previous.projection_id)
  IS DISTINCT FROM(source_release,source_realization,source_revision,source_capture,operation,projection) THEN
   RAISE EXCEPTION 'derived publication intent conflict' USING ERRCODE='23505'; END IF;
  RETURN data.publish_contract_batch(r,z,b,p_content);
 END IF;
 IF EXISTS(SELECT 1 FROM data.batch WHERE (release_id,realization_id,batch_id)=(r,z,b)) THEN
  RAISE EXCEPTION 'append receipt cannot become snapshot-derived' USING ERRCODE='23505'; END IF;
 SELECT data_revision INTO actual FROM data.realization
 WHERE release_id=source_release AND realization_id=source_realization AND state='active' FOR SHARE;
 IF actual IS NULL OR source_revision IS NULL OR actual<>source_revision THEN
  RAISE EXCEPTION 'source snapshot changed; recompute required' USING ERRCODE='P0004'; END IF;
 IF source_capture IS NULL OR source_capture='' OR operation IS NULL OR operation='' OR projection IS NULL OR projection='' THEN
  RAISE EXCEPTION 'derived publication requires capture, operation and projection' USING ERRCODE='23514'; END IF;
 published:=data.publish_contract_batch(r,z,b,p_content);
 INSERT INTO data.publication_intent VALUES(r,z,b,source_release,source_realization,source_revision,source_capture,operation,projection);
 RETURN published;
END $fn$;
ALTER FUNCTION data.publish_derived_batch(text,text,text,bytea,text,text,bigint,text,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.publish_derived_batch(text,text,text,bytea,text,text,bigint,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_derived_batch(text,text,text,bytea,text,text,bigint,text,text,text) TO corpus_sem_writer;
