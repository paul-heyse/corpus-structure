-- Current composed operation guards; owning frozen predecessors are named below.

-- Forward source from semantic_0025_methods.sql; current-only execution admission.
CREATE OR REPLACE FUNCTION ops.guard_task_method_contract() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE declaration ops.method; dimensions jsonb; model_product jsonb; dimension text; actual text;
BEGIN
 IF to_jsonb(NEW)->>'data_request_id' IS NOT NULL THEN RETURN NEW; END IF;
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 SELECT m.* INTO STRICT declaration FROM ops.method m JOIN ops.method_config c ON c.method_id=m.id
 WHERE c.id=NEW.method_config_id;
 SELECT convert_from(body,'UTF8')::jsonb INTO STRICT model_product FROM sem.registry_row
 WHERE release_id=NEW.release_id AND kind='execution_model';
 SELECT jsonb_object_agg(d->>'id',domain->'values') INTO dimensions
 FROM jsonb_array_elements(model_product->'operations') operation,
 LATERAL jsonb_array_elements(operation->'result_dimensions') d,
 jsonb_array_elements(model_product->'outcome_domains') domain
 WHERE operation->>'id'='configure_method' AND domain->>'id'=d->>'outcome_domain';
 FOR dimension,actual IN SELECT * FROM (VALUES
 ('family',declaration.family),('tier',declaration.tier),
 ('confidence_source',declaration.confidence_source)) fields(dimension,actual) LOOP
  IF (actual IS NULL AND dimensions ? (declaration.name||'/'||dimension)) OR
     (actual IS NOT NULL AND NOT coalesce(dimensions->(declaration.name||'/'||dimension) ? actual,false)) THEN
   RAISE EXCEPTION 'method % dimension % is not admitted by the task release',declaration.name,dimension USING ERRCODE='23514';
  END IF;
 END LOOP;
 IF declaration.unit_type IS NULL OR declaration.configuration_schema_digest IS NULL
  OR declaration.unit_type IS DISTINCT FROM NEW.unit_type THEN
  RAISE EXCEPTION 'task unit/configuration contract is unresolved or incompatible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $fn$;

-- Forward source from semantic_0023_execution.sql; current-only execution admission.
CREATE OR REPLACE FUNCTION ops.require_atomic_evaluation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE final_run ops.run;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT final_run FROM ops.run WHERE id=NEW.id;
 IF final_run.result_realization_id IS NOT NULL AND (
  final_run.status<>'finished' OR NOT EXISTS(SELECT 1 FROM ops.completed_result result
   WHERE result.run_id=final_run.id AND result.release_id=final_run.release_id
    AND result.output_realization_id=final_run.result_realization_id)) THEN
  RAISE EXCEPTION 'evaluation output must commit with its completed EvaluationResult' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $fn$;

-- Forward source from semantic_0018_packet_snapshot.sql; data tasks use the request fence.
CREATE OR REPLACE FUNCTION ops.guard_task_configuration() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE r ops.run; c ops.method_config; m ops.method;
BEGIN
 IF to_jsonb(NEW)->>'data_request_id' IS NOT NULL THEN RETURN NEW; END IF;
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
