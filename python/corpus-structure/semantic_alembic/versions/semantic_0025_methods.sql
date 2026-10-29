ALTER TABLE ops.method ADD COLUMN unit_type text;
ALTER TABLE ops.method ADD COLUMN configuration_schema_digest text;
ALTER TABLE ops.method ADD CONSTRAINT method_configuration_digest CHECK(configuration_schema_digest IS NULL OR configuration_schema_digest ~ '^[0-9a-f]{64}$');
GRANT INSERT(unit_type,configuration_schema_digest) ON ops.method TO corpus_sem_writer;
CREATE FUNCTION ops.guard_task_method_contract() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE declaration ops.method;
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=NEW.release_id AND profile='semantic-2') THEN RETURN NEW; END IF;
 SELECT m.* INTO STRICT declaration FROM ops.method m JOIN ops.method_config c ON c.method_id=m.id
 WHERE c.id=NEW.method_config_id;
 IF declaration.unit_type IS NULL OR declaration.configuration_schema_digest IS NULL
  OR declaration.unit_type IS DISTINCT FROM NEW.unit_type THEN
  RAISE EXCEPTION 'task unit/configuration contract is unresolved or incompatible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_task_method_contract() FROM PUBLIC;
CREATE TRIGGER task_method_contract BEFORE INSERT OR UPDATE ON ops.task
 FOR EACH ROW EXECUTE FUNCTION ops.guard_task_method_contract();
CREATE FUNCTION ops.guard_method_contract() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 RAISE EXCEPTION 'method version contract is immutable' USING ERRCODE='23514';
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_method_contract() FROM PUBLIC;
CREATE TRIGGER immutable_method_contract BEFORE UPDATE OR DELETE ON ops.method
 FOR EACH ROW EXECUTE FUNCTION ops.guard_method_contract();
