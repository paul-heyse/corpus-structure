ALTER TABLE ops.task ADD COLUMN trigger jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE ops.task ADD CONSTRAINT uq_task_invocation_key UNIQUE(invocation_key);
ALTER TABLE ops.task ADD CONSTRAINT ck_task_invocation_key CHECK(invocation_key<>'');
GRANT INSERT(trigger) ON ops.task TO corpus_sem_writer;
CREATE FUNCTION ops.guard_source_selection() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE bound ops.run; document bigint;
BEGIN
 SELECT * INTO STRICT bound FROM ops.run WHERE id=NEW.run_id FOR SHARE;
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
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_source_selection() FROM PUBLIC;
CREATE TRIGGER guard_source_selection BEFORE INSERT OR UPDATE ON ops.task FOR EACH ROW EXECUTE FUNCTION ops.guard_source_selection();
CREATE TRIGGER guard_source_selection BEFORE INSERT OR UPDATE ON ops.run_rendition FOR EACH ROW EXECUTE FUNCTION ops.guard_source_selection();
CREATE FUNCTION ops.guard_final_cut() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF NEW.final AND EXISTS(SELECT 1 FROM ops.task WHERE run_id=NEW.run_id AND status IN ('pending','running','awaiting_agent')) THEN
   RAISE EXCEPTION 'final cut requires all automated tasks to finish';
 END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.guard_final_cut() FROM PUBLIC;
CREATE TRIGGER guard_final_cut BEFORE INSERT ON ops.input_cut FOR EACH ROW EXECUTE FUNCTION ops.guard_final_cut();
