REVOKE UPDATE(error) ON ops.task FROM corpus_sem_writer;
CREATE FUNCTION ops.guard_initial_task_error() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF NEW.error IS NOT NULL AND current_user<>'corpus_sem_publisher' THEN
   RAISE EXCEPTION 'task diagnostics require a protected submission';
 END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_initial_task_error() FROM PUBLIC;
CREATE TRIGGER guard_initial_task_error BEFORE INSERT ON ops.task FOR EACH ROW EXECUTE FUNCTION ops.guard_initial_task_error();
CREATE FUNCTION ops.hold_agent_result(p_task bigint,p_attempt bigint,p_holder text,p_packet text,p_clean boolean,p_result jsonb)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE t ops.task; r ops.run;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id FOR SHARE;
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task FOR UPDATE;
 IF r.sealed OR r.status NOT IN ('created','running') OR t.status<>'running' OR t.attempt<>p_attempt OR t.claimed_by IS DISTINCT FROM p_holder THEN
   RAISE EXCEPTION 'agent submission attempt lost or run sealed' USING ERRCODE='P0004';
 END IF;
 IF p_packet IS NULL OR p_packet='' OR t.packet_hash IS DISTINCT FROM p_packet THEN
   RAISE EXCEPTION 'agent submission differs from recorded packet' USING ERRCODE='P0004';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM ops.method_config c JOIN ops.method m ON m.id=c.method_id WHERE c.id=t.method_config_id AND (m.tier='agent' OR m.family='agent')) THEN
   RAISE EXCEPTION 'uncertainty resubmission requires an agent task';
 END IF;
 IF p_clean IS NULL OR p_result IS NULL OR jsonb_typeof(p_result)<>'object' THEN
   RAISE EXCEPTION 'agent submission diagnostics must be a typed result object';
 END IF;
 IF NOT p_clean AND NOT coalesce(t.error ? 'semantic_proposal_first_result',false) THEN
   UPDATE ops.task SET error=coalesce(t.error,'{}'::jsonb)||jsonb_build_object(
     'semantic_proposal_first_result',jsonb_build_object('attempt',p_attempt,'holder',p_holder,'packet_hash',p_packet,'result',p_result)),
     lease_until=clock_timestamp()+interval '5 minutes' WHERE id=t.id;
   RETURN true;
 END IF;
 RETURN false;
END $fn$;
ALTER FUNCTION ops.hold_agent_result(bigint,bigint,text,text,boolean,jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.hold_agent_result(bigint,bigint,text,text,boolean,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.hold_agent_result(bigint,bigint,text,text,boolean,jsonb) TO corpus_sem_writer;

-- Publisher-owned replacement
CREATE OR REPLACE FUNCTION ops.end_source_run(p_run bigint,p_failure jsonb DEFAULT NULL) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE r ops.run; affected bigint;
BEGIN
 SELECT * INTO STRICT r FROM ops.run WHERE id=p_run FOR UPDATE;
 IF r.status IN ('finished','failed','cancelled') THEN RETURN 0; END IF;
 UPDATE ops.task SET status='cancelled',lease_until=NULL,finished_at=clock_timestamp(),
   error=CASE WHEN p_failure IS NULL THEN error ELSE coalesce(error,'{}'::jsonb)||p_failure END
 WHERE run_id=r.id AND status IN ('pending','running','awaiting_agent');
 GET DIAGNOSTICS affected=ROW_COUNT;
 UPDATE ops.run SET status=CASE WHEN p_failure IS NULL THEN 'cancelled' ELSE 'failed' END WHERE id=r.id;
 RETURN affected;
END $fn$;
REVOKE ALL ON FUNCTION ops.end_source_run(bigint,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.end_source_run(bigint,jsonb) TO corpus_sem_writer;
