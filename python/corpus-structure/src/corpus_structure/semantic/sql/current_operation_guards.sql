-- Current composed operation guards; owning frozen predecessors are named below.

-- Forward source from semantic_0025_methods.sql; current-only execution admission.
CREATE OR REPLACE FUNCTION ops.guard_task_method_contract() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE declaration ops.method;
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RAISE EXCEPTION 'execution requires a current composed release' USING ERRCODE='23514'; END IF;
 SELECT m.* INTO STRICT declaration FROM ops.method m JOIN ops.method_config c ON c.method_id=m.id
 WHERE c.id=NEW.method_config_id;
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
