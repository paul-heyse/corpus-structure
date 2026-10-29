CREATE FUNCTION ops.lock_input_snapshot(p_run bigint) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE r ops.run; source data.realization;
BEGIN
 SELECT * INTO STRICT r FROM ops.run WHERE id=p_run;
 SELECT * INTO STRICT source FROM data.realization WHERE realization_id=r.input_realization_id FOR SHARE;
 IF source.release_id<>r.release_id OR source.project_id<>r.project_id OR source.data_revision<>r.input_revision THEN
   RAISE EXCEPTION 'packet input snapshot changed' USING ERRCODE='P0004';
 END IF;
END $fn$;
ALTER FUNCTION ops.lock_input_snapshot(bigint) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.lock_input_snapshot(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.lock_input_snapshot(bigint) TO corpus_sem_writer;
CREATE FUNCTION ops.guard_task_configuration() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE r ops.run; c ops.method_config; m ops.method;
BEGIN
 SELECT * INTO STRICT r FROM ops.run WHERE id=NEW.run_id;
 SELECT * INTO STRICT c FROM ops.method_config WHERE id=NEW.method_config_id;
 SELECT * INTO STRICT m FROM ops.method WHERE id=c.method_id;
 IF r.options ? 'operation_versions' AND r.options->'operation_versions'->>m.name IS DISTINCT FROM m.version THEN
   RAISE EXCEPTION 'task operation differs from immutable run snapshot';
 END IF;
 IF m.tier='agent' OR m.family='agent' THEN
   IF r.options ? 'agent_configs' AND NOT EXISTS(SELECT 1 FROM jsonb_each(r.options->'agent_configs') AS declared WHERE declared.value=c.params) THEN
     RAISE EXCEPTION 'agent task configuration differs from immutable run snapshot';
   END IF;
 ELSIF r.options ? 'configs' AND r.options->'configs'->>m.name IS DISTINCT FROM c.config_hash THEN
   RAISE EXCEPTION 'source task configuration differs from immutable run snapshot';
 END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_task_configuration() FROM PUBLIC;
CREATE TRIGGER guard_task_configuration BEFORE INSERT ON ops.task FOR EACH ROW EXECUTE FUNCTION ops.guard_task_configuration();
