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
 IF bound_release IS NOT NULL AND jsonb_typeof(NEW.detail)<>'object' THEN
 RAISE EXCEPTION 'measurement detail requires source object' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NEW.value IS NOT NULL THEN
 IF NEW.value::text IN ('NaN','Infinity','-Infinity') THEN RAISE EXCEPTION 'measurement requires finite source value' USING ERRCODE='23514'; END IF;
 PERFORM NEW.value::double precision;
 END IF;
 IF bound_release IS NOT NULL AND NEW.scope_type='run' AND NEW.scope_id IS NOT NULL AND NOT EXISTS (SELECT FROM ops.run target JOIN ops.run producer ON producer.id=NEW.run_id WHERE target.id=NEW.scope_id AND target.release_id=bound_release AND target.project_id=producer.project_id) THEN
 RAISE EXCEPTION 'measurement run subject is outside bound project/release' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NEW.scope_type='segment' AND NOT EXISTS (SELECT FROM kb.segment s JOIN kb.rendition rd ON rd.id=s.rendition_id JOIN kb.document doc ON doc.id=rd.document_id JOIN ops.run producer ON producer.id=NEW.run_id WHERE doc.project_id=producer.project_id AND (NEW.scope_id IS NOT NULL OR NEW.scope_key IS NOT NULL) AND (NEW.scope_id IS NULL OR s.id=NEW.scope_id) AND (NEW.scope_key IS NULL OR s.segment_key=NEW.scope_key)) THEN
 RAISE EXCEPTION 'measurement segment subject is outside bound project' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NOT EXISTS (SELECT FROM sem.metric_definition d WHERE d.release_id=bound_release AND d.metric_id=NEW.metric AND d.subject_kind=NEW.scope_type) THEN
 RAISE EXCEPTION 'unresolved metric or incompatible measurement subject' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION ops.validate_measurement_definition() FROM PUBLIC;
CREATE TRIGGER validate_measurement_definition BEFORE INSERT OR UPDATE ON ops.measurement FOR EACH ROW EXECUTE FUNCTION ops.validate_measurement_definition();

ALTER FUNCTION ops.validate_measurement_definition() OWNER TO corpus_sem_publisher;

GRANT SELECT ON data.occurrence_context,data.occurrence_evidence_role,data.membership_support TO corpus_sem_reader,corpus_sem_writer;

-- Only protected source completion creates semantic measurement rows. Position preserves bags.
ALTER TABLE ops.measurement ADD COLUMN source_position bigint;
ALTER TABLE ops.measurement ADD CONSTRAINT measurement_source_position CHECK(source_position IS NULL OR source_position>=0);
ALTER TABLE ops.measurement ADD CONSTRAINT measurement_source_row UNIQUE(task_id,source_position);

CREATE FUNCTION ops.decode_source_value(v jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp SET extra_float_digits=3 AS $fn$
DECLARE kind text; converted jsonb; f double precision;
BEGIN
 IF v IS NULL OR jsonb_typeof(v)<>'object' OR jsonb_typeof(v->'kind') IS DISTINCT FROM 'string' THEN
  RAISE EXCEPTION 'source value requires typed object' USING ERRCODE='23514'; END IF;
 kind:=v->>'kind';
 CASE kind
 WHEN 'null' THEN
  IF v-'kind'<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid source null' USING ERRCODE='23514'; END IF;
  RETURN 'null'::jsonb;
 WHEN 'integer' THEN
  IF jsonb_typeof(v->'integer') IS DISTINCT FROM 'number' OR (v->>'integer')!~'^-?[0-9]+$' OR v-ARRAY['kind','integer']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid source integer' USING ERRCODE='23514'; END IF;
  RETURN v->'integer';
 WHEN 'boolean' THEN
  IF jsonb_typeof(v->'boolean') IS DISTINCT FROM 'boolean' OR v-ARRAY['kind','boolean']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid source boolean' USING ERRCODE='23514'; END IF;
  RETURN v->'boolean';
 WHEN 'text' THEN
  IF jsonb_typeof(v->'text') IS DISTINCT FROM 'string' OR v-ARRAY['kind','text']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid source text' USING ERRCODE='23514'; END IF;
  RETURN v->'text';
 WHEN 'float' THEN
  IF jsonb_typeof(v->'hexadecimal') IS DISTINCT FROM 'string' OR (v->>'hexadecimal')!~'^-?0x[0-9a-f]+(\.[0-9a-f]+)?p[+-]?[0-9]+$' OR v-ARRAY['kind','hexadecimal']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid source float' USING ERRCODE='23514'; END IF;
  f:=(v->>'hexadecimal')::double precision;
  IF f::text IN ('NaN','Infinity','-Infinity') THEN RAISE EXCEPTION 'source float must be finite' USING ERRCODE='23514'; END IF;
  RETURN to_jsonb(f);
 WHEN 'array' THEN
  IF (v?'items' AND jsonb_typeof(v->'items')<>'array') OR v-ARRAY['kind','items']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid source array' USING ERRCODE='23514'; END IF;
  SELECT coalesce(jsonb_agg(ops.decode_source_value(a.value) ORDER BY a.ordinality),'[]'::jsonb)
   INTO converted FROM jsonb_array_elements(coalesce(v->'items','[]'::jsonb)) WITH ORDINALITY a;
  RETURN converted;
 WHEN 'object' THEN
  IF (v?'fields' AND jsonb_typeof(v->'fields')<>'array') OR v-ARRAY['kind','fields']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid source object' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(v->'fields','[]'::jsonb)) WITH ORDINALITY a
   WHERE jsonb_typeof(a.value)<>'object' OR a.value-ARRAY['name','position','value']<>'{}'::jsonb
    OR jsonb_typeof(a.value->'name') IS DISTINCT FROM 'string'
    OR jsonb_typeof(a.value->'position') IS DISTINCT FROM 'number'
    OR CASE WHEN (a.value->>'position')~'^[0-9]+$' THEN (a.value->>'position')::numeric ELSE -1 END<>a.ordinality-1)
   OR EXISTS(SELECT a.value->>'name' FROM jsonb_array_elements(coalesce(v->'fields','[]'::jsonb)) a GROUP BY a.value->>'name' HAVING count(*)>1) THEN
   RAISE EXCEPTION 'source object fields require unique names and ordered positions' USING ERRCODE='23514'; END IF;
  SELECT coalesce(jsonb_object_agg(a.value->>'name',ops.decode_source_value(a.value->'value')),'{}'::jsonb)
   INTO converted FROM jsonb_array_elements(coalesce(v->'fields','[]'::jsonb)) a;
  RETURN converted;
 ELSE
  RAISE EXCEPTION 'unsupported source value kind' USING ERRCODE='23514';
 END CASE;
END $fn$;
ALTER FUNCTION ops.decode_source_value(jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.decode_source_value(jsonb) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;

CREATE FUNCTION ops.guard_measurement_custody() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE bound_release text;
BEGIN
 IF TG_OP<>'INSERT' THEN
  SELECT r.release_id INTO bound_release FROM ops.task t JOIN ops.run r ON r.id=t.run_id WHERE t.id=OLD.task_id;
  IF bound_release IS NOT NULL THEN RAISE EXCEPTION 'source measurements are immutable' USING ERRCODE='23514'; END IF;
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 END IF;
 SELECT r.release_id INTO bound_release FROM ops.task t JOIN ops.run r ON r.id=t.run_id WHERE t.id=NEW.task_id;
 IF bound_release IS NOT NULL AND (TG_OP<>'INSERT' OR current_user<>'corpus_sem_publisher' OR NEW.source_position IS NULL OR NOT EXISTS (SELECT FROM ops.task_result WHERE task_id=NEW.task_id)) THEN
  RAISE EXCEPTION 'semantic measurements require protected source materialization' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;
ALTER FUNCTION ops.guard_measurement_custody() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_measurement_custody() FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
CREATE TRIGGER guard_measurement_custody BEFORE INSERT OR UPDATE OR DELETE ON ops.measurement FOR EACH ROW EXECUTE FUNCTION ops.guard_measurement_custody();

CREATE FUNCTION ops.materialize_source_measurements() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE producer_run bigint; bound_release text;
BEGIN
 SELECT t.run_id,r.release_id INTO STRICT producer_run,bound_release FROM ops.task t JOIN ops.run r ON r.id=t.run_id WHERE t.id=NEW.task_id;
 IF bound_release IS NULL OR NOT NEW.body?'measurements' THEN RETURN NEW; END IF;
 IF jsonb_typeof(NEW.body)<>'object' OR jsonb_typeof(NEW.body->'measurements')<>'array' OR (NEW.body->>'outcome'='failed' AND jsonb_array_length(NEW.body->'measurements')>0) THEN RAISE EXCEPTION 'invalid source measurement batch' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(NEW.body->'measurements') a
  WHERE jsonb_typeof(a.value)<>'object' OR a.value-ARRAY['metric','scope_type','scope_id','scope_key','value','detail']<>'{}'::jsonb
   OR jsonb_typeof(a.value->'metric') IS DISTINCT FROM 'string'
   OR jsonb_typeof(a.value->'scope_type') IS DISTINCT FROM 'string'
   OR (a.value?'scope_key' AND jsonb_typeof(a.value->'scope_key')<>'string')
   OR (a.value?'scope_id' AND (jsonb_typeof(a.value->'scope_id')<>'number' OR (a.value->>'scope_id')!~'^[0-9]+$'))
   OR (a.value->'value'->>'kind') IS NULL OR (a.value->'value'->>'kind') NOT IN ('integer','float','null')
   OR (a.value->'detail'->>'kind') IS DISTINCT FROM 'object') THEN
  RAISE EXCEPTION 'invalid typed source measurement' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.measurement(run_id,task_id,metric,scope_type,scope_id,scope_key,value,detail,source_position)
 SELECT producer_run,NEW.task_id,a.value->>'metric',a.value->>'scope_type',
        (a.value->>'scope_id')::bigint,a.value->>'scope_key',
        (ops.decode_source_value(a.value->'value')#>>'{}')::numeric,
        ops.decode_source_value(a.value->'detail'),a.ordinality-1
 FROM jsonb_array_elements(NEW.body->'measurements') WITH ORDINALITY a;
 RETURN NEW;
END $fn$;
ALTER FUNCTION ops.materialize_source_measurements() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.materialize_source_measurements() FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
CREATE TRIGGER materialize_source_measurements AFTER INSERT ON ops.task_result FOR EACH ROW EXECUTE FUNCTION ops.materialize_source_measurements();

GRANT USAGE,SELECT ON SEQUENCE ops.measurement_id_seq TO corpus_sem_publisher;
