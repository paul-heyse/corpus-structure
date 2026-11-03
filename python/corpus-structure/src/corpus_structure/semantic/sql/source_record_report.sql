-- Shared private report/source custody for completion and sealed-cut publication.
CREATE OR REPLACE FUNCTION ops.validate_source_record_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; view kb.source_view; record_schema json; expected_outcome text;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 IF jsonb_typeof(p_envelope) IS DISTINCT FROM 'object' OR NOT p_envelope ? 'records' THEN
  RAISE EXCEPTION 'source record custody requires an explicit report' USING ERRCODE='23514'; END IF;
 IF t.status='running' THEN
  expected_outcome:=p_envelope->>'outcome';
  IF expected_outcome NOT IN ('produced','empty','failed') OR expected_outcome IS NULL THEN
   RAISE EXCEPTION 'source record report has unsupported task outcome' USING ERRCODE='23514'; END IF;
 ELSE
  IF t.status NOT IN ('done','empty','failed','reused') OR NOT EXISTS(
   SELECT FROM ops.task_result WHERE task_id=t.id AND release_id=t.release_id AND body=p_envelope) THEN
   RAISE EXCEPTION 'source record report differs from immutable origin task result' USING ERRCODE='23514'; END IF;
  expected_outcome:=CASE t.status WHEN 'done' THEN 'produced' ELSE t.status END;
 END IF;
  PERFORM sem.require_execution_operation(t.release_id,'bind_report');
  SELECT convert_from(content,'UTF8')::json INTO record_schema FROM sem.artifact
   WHERE release_id=t.release_id AND artifact_name='json_schema/SourceObservationBatch';
  IF record_schema IS NULL OR NOT public.json_matches_schema(record_schema,p_envelope::json) THEN
   RAISE EXCEPTION 'private record report differs from released shape' USING ERRCODE='23514'; END IF;
  IF t.unit_type<>'source_view' OR p_envelope->>'release_id' IS DISTINCT FROM t.release_id
   OR p_envelope->>'unit_key' IS DISTINCT FROM t.unit_key
   OR p_envelope->>'invocation_key' IS DISTINCT FROM t.invocation_key
   OR p_envelope->>'input_hash' IS DISTINCT FROM t.input_hash
   OR p_envelope->>'outcome' IS DISTINCT FROM expected_outcome
   OR NOT EXISTS(SELECT FROM ops.method_config c JOIN ops.method m ON m.id=c.method_id
    WHERE c.id=t.method_config_id AND c.config_hash=p_envelope->>'configuration_hash'
     AND m.name=p_envelope->>'method' AND m.version=p_envelope->>'operation_version') THEN
   RAISE EXCEPTION 'private record report differs from producing task binding' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT view FROM kb.source_view WHERE id=t.unit_id;
  IF p_envelope->>'source' NOT IN (t.unit_key,view.key) THEN
   RAISE EXCEPTION 'private report logical source differs from producing task/view' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'records') r WHERE r->>'standing'='accepted') THEN
   RAISE EXCEPTION 'private record custody does not admit accepted whole records' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_source_record_coordinates(t.run_id,t.unit_id,p_envelope->>'source',p_envelope->'records');
 EXCEPTION WHEN check_violation OR no_data_found OR too_many_rows THEN
  RAISE USING MESSAGE=SQLERRM,ERRCODE='23514',DETAIL='{"protocol":"corpus-invariant-1","guard":"native_source_address","version":"2","invariant":"published_document_address"}';
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_record_report(bigint,jsonb) FROM PUBLIC;
