-- Finite policy products use the existing protected reference evaluation store.
-- Numerical fitting is trusted evaluator work; SQL authenticates its immutable inputs,
-- final-event membership, released contract and the exact exported parameter bytes.
CREATE OR REPLACE FUNCTION eval.record_policy_prediction_frame(p_project text,p_run bigint,p_set bigint,p_family text,p_kind text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference_set eval.reference_set; completed ops.completed_result; snapshot jsonb;
 units jsonb; method_name text; applicability jsonb; frame_unit jsonb; producer_report jsonb; prediction_record jsonb;
BEGIN
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 SELECT * INTO STRICT completed FROM ops.completed_result WHERE run_id=p_run;
 IF p_kind NOT IN ('feature_fit','final_event_calibration') OR p_kind IS NULL
  OR p_family NOT IN ('definition','assertion','measurement','table','formula_context') OR p_family IS NULL
  OR reference_set.sampling->>'record_protocol' IS DISTINCT FROM 'source-record-reference-1'
  OR reference_set.sampling->>'partition' IS DISTINCT FROM p_kind
  OR NOT EXISTS(SELECT FROM ops.run WHERE id=p_run AND project_id=p_project) THEN
  RAISE EXCEPTION 'policy fitting requires a completed compatible run and declared fit partition' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_execution_operation(completed.release_id,'reference_record_calibrate');
 applicability:=eval.record_reference_applicability(p_project,p_run,p_set);
 snapshot:=eval.native_reference_snapshot(p_set);
 IF jsonb_array_length(snapshot)=0 OR jsonb_array_length(snapshot)<>(SELECT count(*) FROM eval.reference_unit WHERE set_id=p_set) THEN
  RAISE EXCEPTION 'policy fitting needs every frozen source unit adjudicated, including empty units' USING ERRCODE='23514'; END IF;
 method_name:=CASE p_kind WHEN 'feature_fit' THEN 'extract.m1_candidates' ELSE 'resolve.m1_readings' END;
 -- LEFT LATERAL preserves each independently selected no-output unit in coverage.
 SELECT jsonb_agg(jsonb_build_object(
  'unit_id',u.id,'source_view_id',(binding.value->'prediction_frame'->'evaluation_frame'->'pin'->>'source_view_id')::bigint,
  'reference_source_view_id',u.source_view_id,'unit_key',u.unit_key,
  'prediction_frame',binding.value->'prediction_frame','correspondence',binding.value->'views',
  'origin_group',eligible->>'origin_group','source_frame',f.source_frame,
  'reference_records',COALESCE((SELECT jsonb_agg(rec ORDER BY ordinal) FROM
    jsonb_array_elements(convert_from(p.authored,'UTF8')::jsonb->'records') WITH ORDINALITY entry(rec,ordinal)
    WHERE rec->>'family'=p_family),'[]'::jsonb),
  'reports',COALESCE(reports.value,'[]'::jsonb)) ORDER BY u.id) INTO units
 FROM eval.reference_unit u
 JOIN LATERAL jsonb_array_elements(snapshot) frozen ON (frozen->>'unit_id')::bigint=u.id
 JOIN eval.reference_pass p ON p.id=(frozen->>'pass_id')::bigint AND p.unit_id=u.id AND p.pass_kind='C'
 JOIN eval.reference_frame f ON f.id=(frozen->>'frame_id')::bigint AND f.pass_id=p.id
 JOIN LATERAL jsonb_array_elements(reference_set.sampling->'eligible_units') eligible
  ON eligible->>'unit_key'=u.unit_key
 CROSS JOIN LATERAL (SELECT eval.record_reference_unit_binding(p_run,u.id,p.id,f.id) AS value) binding
 LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object('selected_task_id',selected.id,'origin_task_id',origin.id,
    'source',COALESCE(result.body->>'source',selected.unit_key),'outcome',selected.status,
    'records',COALESCE((SELECT jsonb_agg(rec ORDER BY ordinal) FROM
      jsonb_array_elements(COALESCE(result.body->'records','[]')) WITH ORDINALITY entry(rec,ordinal)
      WHERE rec->>'family'=p_family),'[]'::jsonb),
    'parse_detail',result.body->'parse_detail') ORDER BY selected.id) AS value
  FROM ops.cut_task ct JOIN ops.task selected ON selected.id=ct.task_id
  JOIN ops.task origin ON origin.id=ct.origin_task_id
  JOIN ops.method_config config ON config.id=selected.method_config_id
  JOIN ops.method method ON method.id=config.method_id
  LEFT JOIN ops.task_result result ON result.task_id=origin.id AND result.release_id=origin.release_id
  WHERE ct.cut_id=completed.cut_id AND selected.unit_type='source_view' AND selected.unit_id=(binding.value->'prediction_frame'->'evaluation_frame'->'pin'->>'source_view_id')::bigint
   AND method.name=method_name
   AND ct.origin_task_id=COALESCE(selected.reused_task_id,selected.id)
 ) reports ON true
 WHERE u.set_id=p_set;
 IF units IS NULL OR jsonb_array_length(units)<>jsonb_array_length(snapshot)
  OR EXISTS(SELECT FROM jsonb_array_elements(units) unit WHERE NOT EXISTS(
   SELECT FROM ops.run_source_view WHERE run_id=p_run AND source_view_id=(unit->>'source_view_id')::bigint)) THEN
  RAISE EXCEPTION 'policy fitting source frame is outside the completed source closure' USING ERRCODE='23514'; END IF;
 FOR frame_unit IN SELECT value FROM jsonb_array_elements(units) LOOP
  FOR producer_report IN SELECT value FROM jsonb_array_elements(frame_unit->'reports') LOOP
   PERFORM ops.validate_source_record_coordinates(p_run,(frame_unit->>'source_view_id')::bigint,
    frame_unit->'prediction_frame'->'evaluation_frame'->'pin'->>'source',producer_report->'records');
   FOR prediction_record IN SELECT value FROM jsonb_array_elements(producer_report->'records') LOOP
    IF prediction_record->>'policy_version' IS DISTINCT FROM frame_unit->'prediction_frame'->'evaluation_frame'->>'prediction_policy_version' THEN
     RAISE EXCEPTION 'policy candidate differs from frozen evaluation policy' USING ERRCODE='23514'; END IF;
    PERFORM data.validate_source_record_structure(completed.release_id,prediction_record);
    IF prediction_record->'pin' IS DISTINCT FROM frame_unit->'prediction_frame'->'evaluation_frame'->'pin' OR EXISTS(
     SELECT FROM jsonb_array_elements(prediction_record->'anchors') anchor WHERE NOT eval.record_reference_anchor_allowed(
      anchor,frame_unit->'correspondence',frame_unit->'source_frame'->'evaluation_frame')) THEN
     RAISE EXCEPTION 'policy candidate differs from authenticated mapped source cut' USING ERRCODE='23514'; END IF;
   END LOOP;
  END LOOP;
 END LOOP;
 RETURN jsonb_build_object('release_id',completed.release_id,'reference_release_id',reference_set.release_id,
  'applicability',applicability,'run_id',p_run,'set_id',p_set,
  'family',p_family,'kind',p_kind,'method',method_name,'units',units,
  'reference_digest',encode(sha256(convert_to(data.canonical_json(snapshot),'UTF8')),'hex'));
END $$;
REVOKE ALL ON FUNCTION eval.record_policy_prediction_frame(text,bigint,bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_policy_prediction_frame(text,bigint,bigint,text,text) TO corpus_sem_evaluator;

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

CREATE OR REPLACE FUNCTION eval.record_policy_full_correct(p_release text,candidate jsonb,p_references jsonb,p_views jsonb)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 WITH predicted AS (SELECT CASE WHEN p_views IS NULL THEN
  jsonb_build_object('occurrence',candidate->'record_id','fields',candidate->'fields')
  ELSE eval.record_reference_comparison_record(candidate,p_views,'prediction') END AS value),
 expected AS (SELECT reference,CASE WHEN p_views IS NULL THEN
  jsonb_build_object('occurrence',reference->'record_id','fields',reference->'fields')
  ELSE eval.record_reference_comparison_record(reference,p_views,'reference') END AS value
  FROM jsonb_array_elements(p_references) reference)
 SELECT EXISTS(SELECT FROM expected reference,predicted
  WHERE reference.value->'occurrence'=predicted.value->'occurrence'
   AND reference.reference->>'family'=candidate->>'family'
   AND NOT EXISTS(SELECT FROM jsonb_array_elements(predicted.value->'fields') prediction
    LEFT JOIN LATERAL (SELECT value FROM jsonb_array_elements(reference.value->'fields')
     WHERE value->>'role'=prediction->>'role') expected ON true
    WHERE expected.value IS NULL OR eval.record_policy_field_meaning(prediction) IS DISTINCT FROM eval.record_policy_field_meaning(expected.value)
     OR ((prediction->'meaning_changing'='true'::jsonb OR EXISTS(
       SELECT FROM sem.artifact artifact, LATERAL jsonb_array_elements(convert_from(artifact.content,'UTF8')::jsonb->'families') family,
        LATERAL jsonb_array_elements(family->'roles') role
       WHERE artifact.release_id=p_release AND artifact.artifact_name='record_projection.json'
        AND family->>'family'=candidate->>'family' AND role->>'role'=prediction->>'role' AND role->'required'='true'::jsonb)) AND
      eval.record_policy_field_evidence(prediction) IS DISTINCT FROM eval.record_policy_field_evidence(expected.value))))
$$;
REVOKE ALL ON FUNCTION eval.record_policy_full_correct(text,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_policy_full_correct(p_release text,candidate jsonb,p_references jsonb)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT eval.record_policy_full_correct(p_release,candidate,p_references,NULL::jsonb)
$$;
REVOKE ALL ON FUNCTION eval.record_policy_full_correct(text,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.validate_record_policy_product(p_project text,p_run bigint,p_set bigint,p_product jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_release text; contract json; input jsonb; unit jsonb; report jsonb; candidate jsonb; member jsonb; diagnostics jsonb;
 detail jsonb; event jsonb; events jsonb; feature jsonb; fit jsonb; calibration jsonb; acceptance jsonb;
 feature_eval eval.reference_evaluation; members jsonb:='[]'; coverage jsonb:='[]'; coverage_reports jsonb;
 positive bigint:=0; negative bigint:=0; origin_count bigint; exact_bytes text; count_members bigint:=0;
BEGIN
 SELECT c.release_id INTO STRICT source_release FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id
  JOIN eval.reference_set s ON s.id=p_set AND s.project_id=r.project_id WHERE c.run_id=p_run AND r.project_id=p_project;
 PERFORM sem.require_execution_operation(source_release,'reference_record_calibrate');
 SELECT convert_from(content,'UTF8')::json INTO STRICT contract FROM sem.artifact
  WHERE release_id=source_release AND artifact_name='json_schema/RecordPolicyCalibrationProduct';
 IF NOT public.json_matches_schema(contract,p_product::json)
  OR p_product->>'protocol' IS DISTINCT FROM 'source-record-policy-fit-1'
  OR p_product->>'event_procedure' IS DISTINCT FROM 'independent-complete-reading-logistic-1' THEN
  RAISE EXCEPTION 'policy fit differs from released product/procedure contract' USING ERRCODE='23514'; END IF;
 input:=eval.record_policy_prediction_frame(p_project,p_run,p_set,p_product->>'family',p_product->>'kind');
 feature:=p_product->'feature_instance';
 exact_bytes:=p_product->>'feature_canonical_json';
 IF exact_bytes::jsonb IS DISTINCT FROM feature
  OR encode(sha256(convert_to(exact_bytes,'UTF8')),'hex') IS DISTINCT FROM p_product->>'feature_instance_digest'
  OR feature->'applicability'->>'release_id' IS DISTINCT FROM source_release
  OR feature->'applicability'->>'family' IS DISTINCT FROM p_product->>'family'
  OR feature->'applicability'->>'subset' IS DISTINCT FROM p_product->>'subset'
  OR feature->'algorithm'->>'version' IS DISTINCT FROM 'm1-grouped-reading-logistic-1'
  OR feature->'algorithm'->>'feature_version' IS DISTINCT FROM 'sealed-record-groups-1'
  OR feature->'algorithm'->>'solver' IS DISTINCT FROM 'lbfgs'
  OR (feature->'algorithm'->>'l1_ratio')::numeric<>0
  OR (feature->'algorithm'->>'inverse_regularization')::numeric<=0
  OR (feature->'algorithm'->>'tolerance')::numeric<=0
  OR jsonb_array_length(feature->'algorithm'->'features')<>(SELECT count(DISTINCT value->>'name')
   FROM jsonb_array_elements(feature->'algorithm'->'features'))
  OR EXISTS(SELECT FROM jsonb_array_elements(feature->'algorithm'->'features') f WHERE f->>'group' IS DISTINCT FROM
   CASE f->>'name' WHEN 'present_fraction' THEN 'structure' WHEN 'located_fraction' THEN 'evidence'
    WHEN 'exact_anchor_fraction' THEN 'evidence' WHEN 'unresolved_fraction' THEN 'semantics'
    WHEN 'classified_fraction' THEN 'semantics' WHEN 'changed_fraction' THEN 'transformation'
    WHEN 'alternative_count' THEN 'structure' WHEN 'diagnostic_count' THEN 'diagnostics' ELSE 'unsupported' END)
  OR feature->'parameters'->'positive_class' IS DISTINCT FROM '1'::jsonb
  OR feature->'algorithm'->'positive_class' IS DISTINCT FROM '1'::jsonb
  OR feature->'parameters'->'feature_signature' IS DISTINCT FROM to_jsonb(encode(sha256(convert_to(data.canonical_json(
    jsonb_build_array(feature->'algorithm'->'feature_version',feature->'algorithm'->'features')),'UTF8')),'hex'))
  OR feature->'parameters'->'names' IS DISTINCT FROM (SELECT jsonb_agg(value->'name' ORDER BY ordinal)
   FROM jsonb_array_elements(feature->'algorithm'->'features') WITH ORDINALITY f(value,ordinal))
  OR jsonb_array_length(feature->'parameters'->'names')<>jsonb_array_length(feature->'parameters'->'coefficients')
  OR jsonb_array_length(feature->'parameters'->'names')<>jsonb_array_length(feature->'parameters'->'center')
  OR jsonb_array_length(feature->'parameters'->'names')<>jsonb_array_length(feature->'parameters'->'scale')
  OR EXISTS(SELECT FROM jsonb_array_elements_text(feature->'parameters'->'scale') value WHERE value::numeric<=0) THEN
  RAISE EXCEPTION 'policy feature instance differs from exported algorithm/parameter authority' USING ERRCODE='23514'; END IF;
 IF p_product->>'kind'='feature_fit' THEN
  IF p_product ? 'acceptance_instance' OR p_product ? 'feature_evaluation_id' THEN
   RAISE EXCEPTION 'feature fitting cannot claim final-event calibration authority' USING ERRCODE='23514'; END IF;
  fit:=feature->'fit';
 ELSE
  SELECT * INTO STRICT feature_eval FROM eval.reference_evaluation WHERE id=(p_product->>'feature_evaluation_id')::bigint;
  IF feature_eval.content_digest IS DISTINCT FROM p_product->>'feature_evaluation_digest'
   OR feature_eval.result->'policy_fit'->>'kind' IS DISTINCT FROM 'feature_fit'
   OR feature_eval.result->'policy_fit'->>'feature_instance_digest' IS DISTINCT FROM p_product->>'feature_instance_digest'
   OR feature_eval.result->'policy_fit'->'feature_instance' IS DISTINCT FROM feature
   OR feature_eval.result->'policy_fit'->>'feature_canonical_json' IS DISTINCT FROM p_product->>'feature_canonical_json' THEN
   RAISE EXCEPTION 'calibration must retain exact protected feature-fit instance' USING ERRCODE='23514'; END IF;
  -- Groups, URI copies and known identical bytes are compared across projects. Project
  -- separation alone is never evidence that held-out source origins are independent.
  IF EXISTS(SELECT FROM eval.reference_set train JOIN eval.reference_set held ON held.id=p_set
    CROSS JOIN LATERAL jsonb_array_elements(train.sampling->'eligible_units') a
    CROSS JOIN LATERAL jsonb_array_elements(held.sampling->'eligible_units') b
    WHERE train.id=feature_eval.set_id AND a->>'origin_group'=b->>'origin_group')
   OR EXISTS(SELECT FROM eval.reference_unit a JOIN kb.source_view av ON av.id=a.source_view_id
    JOIN kb.document ad ON ad.id=av.document_id, eval.reference_unit b JOIN kb.source_view bv ON bv.id=b.source_view_id
    JOIN kb.document bd ON bd.id=bv.document_id WHERE a.set_id=feature_eval.set_id AND b.set_id=p_set
     AND (ad.source_uri=bd.source_uri OR ad.content_hash=bd.content_hash)) THEN
   RAISE EXCEPTION 'calibration and feature fitting share declared or known source origins' USING ERRCODE='23514'; END IF;
  acceptance:=p_product->'acceptance_instance';
  exact_bytes:=p_product->>'instance_canonical_json';
  IF exact_bytes::jsonb IS DISTINCT FROM acceptance
   OR encode(sha256(convert_to(exact_bytes,'UTF8')),'hex') IS DISTINCT FROM p_product->>'instance_digest'
   OR acceptance->'feature' IS DISTINCT FROM feature OR acceptance->'calibration' IS NULL
   OR acceptance->'calibration'='null'::jsonb
   OR acceptance->'calibration'->>'feature_instance_digest' IS DISTINCT FROM p_product->>'feature_instance_digest'
   OR acceptance->'calibration'->>'event_procedure' IS DISTINCT FROM p_product->>'event_procedure'
   OR acceptance->'calibration'->>'method' IS DISTINCT FROM 'held-out-final-event-sigmoid-1'
   OR acceptance->'calibration'->>'frame_selection' IS DISTINCT FROM 'complete-predeclared-eligible-scored-events'
   OR (acceptance->>'threshold')::numeric<=0 OR (acceptance->>'threshold')::numeric>1 THEN
   RAISE EXCEPTION 'calibration export differs from exact instance/threshold contract' USING ERRCODE='23514'; END IF;
  calibration:=acceptance->'calibration'; fit:=calibration->'fit';
 END IF;
 FOR unit IN SELECT value FROM jsonb_array_elements(input->'units') LOOP
  coverage_reports:='[]';
  FOR report IN SELECT value FROM jsonb_array_elements(unit->'reports') LOOP
   coverage_reports:=coverage_reports||jsonb_build_array(jsonb_build_object('selected_task_id',report->'selected_task_id',
    'outcome',report->'outcome','records',jsonb_array_length(report->'records')));
   detail:=report->'parse_detail';
   FOR candidate IN SELECT value FROM jsonb_array_elements(report->'records') LOOP
    SELECT value INTO member FROM jsonb_array_elements(p_product->'event_members')
     WHERE value->>'record_id'=candidate->>'record_id' AND value->>'interpretation_id'=candidate->>'interpretation_id'
      AND value->'selected_task_id'=report->'selected_task_id';
    IF member IS NULL OR member->'source' IS DISTINCT FROM report->'source'
     OR member->'correct' IS DISTINCT FROM to_jsonb(eval.record_policy_full_correct(source_release,candidate,unit->'reference_records',unit->'correspondence')) THEN
     RAISE EXCEPTION 'policy event label differs from complete sealed candidate/adjudicated reading' USING ERRCODE='23514'; END IF;
    IF p_product->>'kind'='final_event_calibration' THEN
     SELECT COALESCE(jsonb_agg(value),'[]'::jsonb) INTO events FROM jsonb_array_elements(
       COALESCE(data.report_field(detail,'record_policy_events')->'items','[]'))
      WHERE data.report_field(value,'record_id')->>'text'=candidate->>'record_id'
       AND data.report_field(value,'interpretation_id')->>'text'=candidate->>'interpretation_id'
       AND data.report_field(value,'feature_instance_digest')->>'text'=p_product->>'feature_instance_digest';
     event:=events->0;
     IF jsonb_array_length(events)<>1 OR data.report_field(event,'outcome')->>'text' IS DISTINCT FROM 'completed'
      OR data.report_field(event,'event_procedure')->>'text' IS DISTINCT FROM p_product->>'event_procedure'
      OR data.report_field(event,'feature_input_digest')->>'text' IS DISTINCT FROM member->>'feature_input_digest'
      OR data.record_source_float(data.report_field(event,'final_event_score')) IS DISTINCT FROM (member->>'score')::double precision
      OR abs(data.record_source_float(data.report_field(event,'final_event_score'))-
       data.record_feature_score(candidate,data.record_source_json(data.report_field(event,'diagnostics')),feature))>
       greatest(1e-12,1e-12*abs(data.record_feature_score(candidate,
        data.record_source_json(data.report_field(event,'diagnostics')),feature)))
      OR (data.report_field(event,'feature_input_canonical_json')->>'text')::jsonb IS DISTINCT FROM
       jsonb_build_array(candidate,data.record_source_json(data.report_field(event,'diagnostics')))
      OR encode(sha256(convert_to(data.report_field(event,'feature_input_canonical_json')->>'text','UTF8')),'hex')
       IS DISTINCT FROM member->>'feature_input_digest' THEN
      RAISE EXCEPTION 'calibration must cover every sealed completed final event and its exact input' USING ERRCODE='23514'; END IF;
    ELSE
     SELECT COALESCE(jsonb_agg(diagnostic ORDER BY report_ordinal,diagnostic_ordinal),'[]'::jsonb) INTO diagnostics FROM (
      SELECT DISTINCT ON (data.canonical_json(diagnostic-'group')) diagnostic,report_ordinal,diagnostic_ordinal FROM (
       SELECT data.record_source_json(item) AS diagnostic,report_ordinal,diagnostic_ordinal
       FROM jsonb_array_elements(COALESCE(data.report_field(detail,'reports')->'items','[]')) WITH ORDINALITY reports(value,report_ordinal)
       CROSS JOIN LATERAL jsonb_array_elements(COALESCE(data.report_field(value,'diagnostics')->'items','[]')) WITH ORDINALITY items(item,diagnostic_ordinal)
      ) raw WHERE candidate->'computation_dependencies' ? (diagnostic->>'group_dependency')
       AND diagnostic->>'group_dependency' LIKE 'native-group:%'
      ORDER BY data.canonical_json(diagnostic-'group'),report_ordinal,diagnostic_ordinal) unique_diagnostics;
     IF (member->>'score')::numeric<>0 OR member->>'feature_input_digest' IS DISTINCT FROM
      encode(sha256(convert_to(data.canonical_json(jsonb_build_array(candidate,diagnostics)),'UTF8')),'hex') THEN
      RAISE EXCEPTION 'feature-fit frame differs from exact sealed candidate/diagnostics input' USING ERRCODE='23514'; END IF;
    END IF;
    members:=members||jsonb_build_array(member); count_members:=count_members+1;
    IF (member->>'correct')::boolean THEN positive:=positive+1; ELSE negative:=negative+1; END IF;
   END LOOP;
  END LOOP;
  coverage:=coverage||jsonb_build_array(jsonb_build_object('unit_id',unit->'unit_id',
   'source_view_id',unit->'source_view_id','reports',coverage_reports));
 END LOOP;
 SELECT count(DISTINCT source_unit.value->>'origin_group') INTO origin_count
  FROM jsonb_array_elements(input->'units') AS source_unit(value)
  WHERE EXISTS(SELECT FROM jsonb_array_elements(source_unit.value->'reports') AS selected_report(value)
   WHERE jsonb_array_length(selected_report.value->'records')>0);
 exact_bytes:=p_product->>'event_frame_canonical_json';
 IF count_members=0 OR members IS DISTINCT FROM p_product->'event_members'
  OR count_members<>(SELECT count(DISTINCT value->>'interpretation_id') FROM jsonb_array_elements(members))
  OR exact_bytes::jsonb IS DISTINCT FROM members
  OR encode(sha256(convert_to(exact_bytes,'UTF8')),'hex') IS DISTINCT FROM p_product->>'event_frame_digest'
  OR p_product->>'coverage_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(coverage),'UTF8')),'hex')
  OR fit->>'coverage_digest' IS DISTINCT FROM p_product->>'coverage_digest'
  OR fit->>'frame_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(input),'UTF8')),'hex')
  OR fit->>'reference_digest' IS DISTINCT FROM input->>'reference_digest'
  OR fit->>'partition' IS DISTINCT FROM p_product->>'kind'
  OR fit->>'standing' IS DISTINCT FROM 'fitted' OR fit->'converged' IS DISTINCT FROM 'true'::jsonb
  OR fit->>'library_version' IS DISTINCT FROM 'scikit-learn-1.9.1'
  OR (fit->>'positive_count')::bigint<>positive OR (fit->>'negative_count')::bigint<>negative
  OR (fit->>'declared_origin_group_count')::bigint<>origin_count
  OR least(positive,negative)<(feature->'algorithm'->>'minimum_per_class')::bigint
  OR origin_count<(feature->'algorithm'->>'minimum_origin_groups')::bigint
  OR (fit->>'iterations')::bigint<1 OR (fit->>'iterations')::bigint>=(feature->'algorithm'->>'max_iterations')::bigint
  OR (calibration IS NOT NULL AND (calibration->>'coverage_digest' IS DISTINCT FROM p_product->>'coverage_digest'
   OR calibration->'fit'->>'frame_digest'=feature->'fit'->>'frame_digest'
   OR calibration->'fit'->>'reference_digest'=feature->'fit'->>'reference_digest')) THEN
  RAISE EXCEPTION 'policy fit has incomplete membership, support, convergence or immutable frame custody' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION eval.validate_record_policy_product(text,bigint,bigint,jsonb) FROM PUBLIC;

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
