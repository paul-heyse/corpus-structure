-- Remaining legacy field projections and binding guard. Current declared grading/fitting
-- use their own selected frames, CPU receipts and finite native authority owners.
CREATE OR REPLACE FUNCTION eval.record_policy_field_meaning(field jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT (field-'evidence_sets'-'evidence_status'-'reason'-'alternatives')||jsonb_build_object(
  'alternatives',COALESCE((SELECT jsonb_agg(value->'value' ORDER BY data.canonical_json(value->'value') COLLATE "C")
   FROM jsonb_array_elements(COALESCE(field->'alternatives','[]'))),'[]'::jsonb))
$$;
REVOKE ALL ON FUNCTION eval.record_policy_field_meaning(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_policy_field_evidence(field jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('status',field->'evidence_status','sets',
  COALESCE((SELECT jsonb_agg(value ORDER BY value COLLATE "C") FROM jsonb_array_elements_text(COALESCE(field->'evidence_sets','[]'))),'[]'::jsonb),
  'alternatives',COALESCE((SELECT jsonb_agg(pair ORDER BY data.canonical_json(pair) COLLATE "C") FROM (
   SELECT jsonb_build_array(alternative->'value',COALESCE((SELECT jsonb_agg(value ORDER BY value COLLATE "C")
    FROM jsonb_array_elements_text(COALESCE(alternative->'evidence_sets','[]'))),'[]'::jsonb)) AS pair
   FROM jsonb_array_elements(COALESCE(field->'alternatives','[]')) alternative) ordered),'[]'::jsonb))
$$;
REVOKE ALL ON FUNCTION eval.record_policy_field_evidence(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION sem.require_record_policy_binding(p_release text,p_binding jsonb,p_accept boolean)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE contract json; evaluation eval.reference_evaluation; product jsonb; instance jsonb; exact_bytes text;
BEGIN
 SELECT convert_from(content,'UTF8')::json INTO STRICT contract FROM sem.artifact
  WHERE release_id=p_release AND artifact_name='json_schema/RecordPolicyBinding';
 IF NOT public.json_matches_schema(contract,p_binding::json) THEN
  RAISE EXCEPTION 'record policy binding differs from released schema' USING ERRCODE='23514'; END IF;
 instance:=p_binding->'instance'; exact_bytes:=p_binding->>'instance_canonical_json';
 SELECT * INTO STRICT evaluation FROM eval.reference_evaluation WHERE id=(p_binding->>'evaluation_id')::bigint;
 product:=evaluation.result->'policy_fit';
 IF evaluation.content_digest IS DISTINCT FROM p_binding->>'evaluation_digest'
  OR evaluation.result->>'release_id' IS DISTINCT FROM p_release
  OR exact_bytes::jsonb IS DISTINCT FROM instance
  OR encode(sha256(convert_to(exact_bytes,'UTF8')),'hex') IS DISTINCT FROM p_binding->>'instance_digest'
  OR product->>'kind' IS DISTINCT FROM 'final_event_calibration'
  OR product->'acceptance_instance' IS DISTINCT FROM instance
  OR product->>'instance_digest' IS DISTINCT FROM p_binding->>'instance_digest'
  OR product->>'instance_canonical_json' IS DISTINCT FROM exact_bytes
  OR instance->'feature'->'applicability'->>'release_id' IS DISTINCT FROM p_release
  OR (p_accept AND (instance->'calibration' IS NULL OR instance->'calibration'='null'::jsonb)) THEN
  RAISE EXCEPTION 'record admission requires an exact protected evaluator-authorized instance' USING ERRCODE='23514'; END IF;
 -- Protected immutable insertion authenticated the complete numerical/reference frame.
 -- Later adjudication does not silently rebind or revoke this frozen instance.
 IF evaluation.content_digest IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(
   jsonb_build_object('snapshot',evaluation.reference_snapshot,'result',evaluation.result)),'UTF8')),'hex')
  OR NOT EXISTS(SELECT FROM eval.reference_set WHERE id=evaluation.set_id
   AND sampling->>'partition'='final_event_calibration'
   AND evaluation.result->>'reference_release_id'=release_id)
  OR evaluation.result->'applicability'->>'prediction_release_id' IS DISTINCT FROM p_release THEN
  RAISE EXCEPTION 'record policy evaluation custody differs from immutable protected bytes' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_execution_operation(p_release,'reference_record_calibrate');
END $$;
REVOKE ALL ON FUNCTION sem.require_record_policy_binding(text,jsonb,boolean) FROM PUBLIC;
