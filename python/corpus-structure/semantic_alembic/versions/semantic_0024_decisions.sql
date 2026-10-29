-- Fixed fields; domain releases remain registry data.
ALTER TABLE data.coverage ADD COLUMN source_outcome text, ADD COLUMN required_capability text;
ALTER TABLE data.coverage ADD CONSTRAINT coverage_source_domain CHECK (source_outcome IS NULL OR source_outcome IN ('complete','partial','unknown','unsupported','failed'));
ALTER TABLE data.coverage ADD CONSTRAINT coverage_translation CHECK (source_outcome IS NULL OR outcome = CASE WHEN source_outcome IN ('unknown','unsupported') THEN 'unanalysed' ELSE source_outcome END);
ALTER TABLE data.assessment ADD COLUMN counterpart_fact_id text, ADD COLUMN counterpart_occurrence_id text, ADD COLUMN context_value_id text, ADD COLUMN comparison_tier text;
ALTER TABLE data.assessment ADD CONSTRAINT assessment_counterpart_fact FOREIGN KEY (realization_id,release_id,counterpart_fact_id) REFERENCES data.fact(realization_id,release_id,fact_id);
ALTER TABLE data.assessment ADD CONSTRAINT assessment_counterpart_occurrence FOREIGN KEY (realization_id,release_id,counterpart_occurrence_id) REFERENCES data.occurrence(realization_id,release_id,occurrence_id);
ALTER TABLE data.assessment ADD CONSTRAINT assessment_context FOREIGN KEY (realization_id,release_id,context_value_id) REFERENCES data.typed_value(realization_id,release_id,value_id);
ALTER TABLE data.assessment ADD CONSTRAINT assessment_counterpart_pair CHECK ((counterpart_fact_id IS NULL)=(counterpart_occurrence_id IS NULL));
CREATE FUNCTION data.validate_assessment_counterpart() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF NEW.counterpart_occurrence_id IS NOT NULL AND NOT EXISTS (SELECT FROM data.occurrence o WHERE (o.realization_id,o.release_id,o.occurrence_id,o.fact_id)=(NEW.realization_id,NEW.release_id,NEW.counterpart_occurrence_id,NEW.counterpart_fact_id)) THEN
 RAISE EXCEPTION 'assessment counterpart occurrence differs from fact' USING ERRCODE='23514'; END IF;
 IF NEW.context_value_id IS NOT NULL AND NEW.occurrence_id IS NOT NULL AND NOT EXISTS (SELECT FROM data.occurrence o WHERE (o.realization_id,o.release_id,o.occurrence_id,o.report_qualification_value_id)=(NEW.realization_id,NEW.release_id,NEW.occurrence_id,NEW.context_value_id)) THEN
 RAISE EXCEPTION 'assessment context differs from subject occurrence' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION data.validate_assessment_counterpart() FROM PUBLIC;
CREATE TRIGGER validate_assessment_counterpart BEFORE INSERT OR UPDATE ON data.assessment FOR EACH ROW EXECUTE FUNCTION data.validate_assessment_counterpart();

CREATE TABLE sem.metric_definition (
 release_id text NOT NULL REFERENCES sem.release(release_id), metric_id text NOT NULL,
 value_type text NOT NULL, subject_kind text NOT NULL, detail_schema text NOT NULL, description text NOT NULL,
 PRIMARY KEY(release_id,metric_id));
GRANT SELECT ON sem.metric_definition TO corpus_sem_publisher,corpus_sem_reader,corpus_sem_writer;
CREATE FUNCTION ops.validate_measurement_definition() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE bound_release text; task_run bigint;
BEGIN
 SELECT r.release_id,t.run_id INTO bound_release,task_run FROM ops.task t JOIN ops.run r ON r.id=t.run_id WHERE t.id=NEW.task_id;
 IF task_run IS DISTINCT FROM NEW.run_id THEN RAISE EXCEPTION 'measurement producer run differs from task' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NEW.value IS NOT NULL THEN
 IF NEW.value::text IN ('NaN','Infinity','-Infinity') THEN RAISE EXCEPTION 'measurement requires finite source value' USING ERRCODE='23514'; END IF;
 PERFORM NEW.value::double precision;
 END IF;
 IF bound_release IS NOT NULL AND NOT EXISTS (SELECT FROM sem.metric_definition d WHERE d.release_id=bound_release AND d.metric_id=NEW.metric AND d.subject_kind=NEW.scope_type) THEN
 RAISE EXCEPTION 'unresolved metric or incompatible measurement subject' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.validate_measurement_definition() FROM PUBLIC;
CREATE TRIGGER validate_measurement_definition BEFORE INSERT OR UPDATE ON ops.measurement FOR EACH ROW EXECUTE FUNCTION ops.validate_measurement_definition();

ALTER FUNCTION ops.validate_measurement_definition() OWNER TO corpus_sem_publisher;

GRANT SELECT ON data.occurrence_context,data.occurrence_evidence_role,data.membership_support TO corpus_sem_reader;
