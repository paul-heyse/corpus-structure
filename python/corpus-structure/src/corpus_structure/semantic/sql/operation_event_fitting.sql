-- Independent operation correctness development fits; no whole-reading or truth authority.
CREATE OR REPLACE FUNCTION eval.operation_event_fit_frame(p_project text,p_evaluation bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE grade eval.reference_evaluation; reference_set eval.reference_set; completed ops.completed_result;
 unit_report jsonb; assessed jsonb; unit eval.reference_unit; authored jsonb; reference_case jsonb;
 selected ops.task; contribution kb.source_contribution; detail jsonb; operation kb.source_contribution_operation;
 observations jsonb:='[]'; event_ids jsonb:='[]'; versions jsonb:='[]'; identity text; head_exact integer; tail_exact integer;
 native_score numeric; frame jsonb; rubric jsonb:='[]'; option jsonb;
BEGIN
 SELECT * INTO STRICT grade FROM eval.reference_evaluation WHERE id=p_evaluation AND project_id=p_project;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=grade.set_id AND project_id=p_project;
 IF reference_set.sampling->>'partition' NOT IN ('development','feature_fit')
  OR grade.result->>'protocol' IS DISTINCT FROM 'source-operation-evaluation-1' THEN
  RAISE EXCEPTION 'operation fitting requires a protected development operation grade' USING ERRCODE='23514'; END IF;
 -- The immutable grade, selected final cut, and current independently authored C premises all agree.
 PERFORM eval.validate_operation_reference_evaluation(p_project,grade.run_id,grade.set_id,grade.reference_snapshot,grade.result);
 SELECT * INTO STRICT completed FROM ops.completed_result WHERE run_id=grade.run_id;
 PERFORM sem.require_execution_operation(completed.release_id,'reference_operation_fit');
 IF grade.content_digest IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(jsonb_build_object('snapshot',grade.reference_snapshot,'result',grade.result)),'UTF8')),'hex') THEN
  RAISE EXCEPTION 'operation grade digest differs' USING ERRCODE='23514'; END IF;
 FOR unit_report IN SELECT value FROM jsonb_array_elements(grade.result->'units') ORDER BY (value->>'unit_id')::bigint LOOP
  SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=(unit_report->>'unit_id')::bigint AND set_id=grade.set_id;
  IF unit.context->0->'evaluation_frame'->>'direction' IS DISTINCT FROM 'output_first' THEN CONTINUE; END IF;
  rubric:=rubric||jsonb_build_array(unit.context->0->'evaluation_frame'->'rubric_version');
  SELECT convert_from(p.authored,'UTF8')::jsonb INTO STRICT authored FROM eval.reference_pass p
   JOIN jsonb_array_elements(grade.reference_snapshot) s ON (s->>'pass_id')::bigint=p.id
   WHERE p.unit_id=unit.id AND p.pass_kind='C';
  FOR assessed IN SELECT value FROM jsonb_array_elements(unit_report->'cases') ORDER BY value->>'case_id' LOOP
   IF assessed->>'contribution_id' IS NULL OR assessed->>'facet' IS DISTINCT FROM 'defined_by_correctness' THEN CONTINUE; END IF;
   SELECT c.* INTO contribution FROM kb.source_contribution c JOIN ops.task t
    ON t.run_id=grade.run_id AND COALESCE(t.reused_task_id,t.id)=c.task_id
    JOIN ops.cut_task ct ON ct.task_id=t.id AND ct.cut_id=completed.cut_id
    WHERE c.contribution_id=assessed->>'contribution_id' AND c.source_view_id=unit.source_view_id
     AND c.kind='relation' AND c.semantic_type='relation.defined_by';
   IF NOT FOUND THEN CONTINUE; END IF;
   SELECT value INTO STRICT reference_case FROM jsonb_array_elements(authored->'cases')
    WHERE value->>'case_id'=assessed->>'case_id';
   IF reference_case->>'contribution_id' IS DISTINCT FROM contribution.contribution_id
    OR reference_case->>'contribution_kind' IS DISTINCT FROM 'relation'
    OR NOT (unit.context->0->'evaluation_frame'->'contribution_ids' ? contribution.contribution_id) THEN
    RAISE EXCEPTION 'correctness event must name its exact frozen emitted relation' USING ERRCODE='23514'; END IF;
   -- A supported event must constrain exact endpoint roles and native anchor scopes.
   IF reference_case->>'judgment'='supported' AND reference_case->>'source_state'='stated' THEN
    IF jsonb_array_length(reference_case->'alternatives')=0 THEN
     RAISE EXCEPTION 'defined_by support requires exact endpoint alternatives' USING ERRCODE='23514'; END IF;
    FOR option IN SELECT value FROM jsonb_array_elements(reference_case->'alternatives') LOOP
     IF option->>'semantic_type' IS DISTINCT FROM 'relation.defined_by'
      OR jsonb_typeof(option->'endpoint_semantics') IS DISTINCT FROM 'array'
      OR jsonb_array_length(option->'endpoint_semantics')<>2
      OR (SELECT count(DISTINCT e->>'role') FROM jsonb_array_elements(option->'endpoint_semantics') e
       WHERE e->>'role' IN ('head','tail') AND jsonb_typeof(e->'anchor_ids')='array'
        AND jsonb_array_length(e->'anchor_ids')>0)<>2 THEN
      RAISE EXCEPTION 'defined_by alternatives must bind both exact endpoint scopes' USING ERRCODE='23514'; END IF;
    END LOOP;
   END IF;
   identity:=contribution.task_id::text||':'||contribution.contribution_id;
   IF event_ids ? identity THEN RAISE EXCEPTION 'one emitted event cannot be weighted twice' USING ERRCODE='23514'; END IF;
   SELECT tr.body->'contributions'->contribution.position INTO STRICT detail FROM ops.task_result tr WHERE tr.task_id=contribution.task_id;
   SELECT * INTO STRICT operation FROM kb.source_contribution_operation WHERE task_id=contribution.task_id AND operation_key=contribution.operation_key;
   SELECT count(DISTINCT e.endpoint_id) FILTER(WHERE e.role='head' AND a.precision='exact'),
    count(DISTINCT e.endpoint_id) FILTER(WHERE e.role='tail' AND a.precision='exact') INTO head_exact,tail_exact
    FROM kb.source_contribution_endpoint e LEFT JOIN kb.source_contribution_anchor a
     ON a.task_id=e.task_id AND a.contribution_id=e.endpoint_id
    WHERE e.task_id=contribution.task_id AND e.contribution_id=contribution.contribution_id;
   native_score:=CASE WHEN detail->>'score_state'='native' THEN data.record_source_float(detail->'score')::numeric ELSE 0 END;
   IF native_score IS NULL OR native_score<0 OR native_score>1 THEN RAISE EXCEPTION 'invalid finite native relation score' USING ERRCODE='23514'; END IF;
   observations:=observations||jsonb_build_array(jsonb_build_object('event_id',identity,
    'contribution_id',contribution.contribution_id,'source_ref',unit.source_view_id::text||':'||contribution.contribution_id,
    'features',jsonb_build_array(native_score,CASE WHEN detail->>'score_state'='native' THEN 1 ELSE 0 END,head_exact,tail_exact),
    'judgment',assessed->>'judgment'));
   event_ids:=event_ids||jsonb_build_array(identity);
   versions:=versions||jsonb_build_array(jsonb_build_object('question',operation.question,'operation_version',operation.operation_version));
  END LOOP;
 END LOOP;
 SELECT COALESCE(jsonb_agg(v ORDER BY data.canonical_json(v)),'[]') INTO versions FROM (SELECT DISTINCT value v FROM jsonb_array_elements(versions)) unique_versions;
 frame:=jsonb_build_object('protocol','operation-event-development-1','event','defined_by_correctness',
  'event_version','defined-by-exact-endpoints-scope-1',
  'producer_version',encode(sha256(convert_to(data.canonical_json(versions),'UTF8')),'hex'),
  'rubric_digest',encode(sha256(convert_to(data.canonical_json(rubric),'UTF8')),'hex'),
  'reference_digest',grade.content_digest,'corpus_id',p_project||':'||grade.run_id::text||':'||completed.cut_id::text,
  'feature_names',jsonb_build_array('native_score','native_score_present','head_exact_endpoint_count','tail_exact_endpoint_count'),
  'event_ids',event_ids,'observations',observations,'assessment_mode','in_sample_development');
 RETURN jsonb_build_object('protocol','native-operation-event-frame-1','project_id',p_project,'evaluation_id',p_evaluation,
  'run_id',grade.run_id,'cut_id',completed.cut_id,'release_id',completed.release_id,'set_id',grade.set_id,
  'evaluation_digest',grade.content_digest,'reference_snapshot',grade.reference_snapshot,
  'source_frame_digest',grade.result->>'frame_digest','frame',frame);
END $$;
REVOKE ALL ON FUNCTION eval.operation_event_fit_frame(text,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_event_fit_frame(text,bigint) TO corpus_sem_evaluator,corpus_sem_fitter;

CREATE OR REPLACE FUNCTION eval.record_operation_event_fit(p_project text,p_evaluation bigint,p_frame jsonb,p_result jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE actual jsonb; result_id bigint; frame_digest text; parameters jsonb; item jsonb; n integer;
BEGIN
 actual:=eval.operation_event_fit_frame(p_project,p_evaluation);
 IF actual IS DISTINCT FROM p_frame THEN RAISE EXCEPTION 'operation fitting source/frame/C snapshot is stale or forged' USING ERRCODE='23514'; END IF;
 frame_digest:=encode(sha256(convert_to(data.canonical_json(ops.contextual_identity_value(p_frame->'frame')),'UTF8')),'hex');
 IF p_result->>'protocol' IS DISTINCT FROM 'operation-event-fit-result-1'
  OR p_result->>'assessment_mode' IS DISTINCT FROM 'in_sample_development'
  OR p_result->>'origin_requirement' IS DISTINCT FROM 'none'
  OR p_result->>'frame_digest' IS DISTINCT FROM frame_digest
  OR COALESCE(p_result->>'status','') NOT IN ('fitted','unavailable','failed')
  OR (p_result->>'observations')::integer IS DISTINCT FROM jsonb_array_length(p_frame->'frame'->'observations')
  OR (p_result->>'positive')::integer IS DISTINCT FROM (SELECT count(*) FROM jsonb_array_elements(p_frame->'frame'->'observations') o WHERE o->>'judgment'='supported')
  OR (p_result->>'negative')::integer IS DISTINCT FROM (SELECT count(*) FROM jsonb_array_elements(p_frame->'frame'->'observations') o WHERE o->>'judgment'='unsupported')
  OR (p_result->>'labeled')::integer IS DISTINCT FROM (p_result->>'positive')::integer+(p_result->>'negative')::integer THEN
  RAISE EXCEPTION 'operation fit result changes the declared event/label population' USING ERRCODE='23514'; END IF;
 parameters:=p_result->'parameters';
 IF p_result->>'status'='fitted' THEN
  IF (p_result->>'positive')::integer<1 OR (p_result->>'negative')::integer<1
   OR parameters->>'event' IS DISTINCT FROM 'defined_by_correctness'
   OR parameters->>'assessment_mode' IS DISTINCT FROM 'in_sample_development'
   OR parameters->>'frame_digest' IS DISTINCT FROM frame_digest
   OR parameters->>'producer_version' IS DISTINCT FROM p_frame->'frame'->>'producer_version'
   OR parameters->>'event_version' IS DISTINCT FROM p_frame->'frame'->>'event_version'
   OR parameters->>'corpus_id' IS DISTINCT FROM p_frame->'frame'->>'corpus_id'
   OR parameters->>'rubric_digest' IS DISTINCT FROM p_frame->'frame'->>'rubric_digest'
   OR parameters->>'reference_digest' IS DISTINCT FROM p_frame->'frame'->>'reference_digest'
   OR parameters->'feature_names' IS DISTINCT FROM p_frame->'frame'->'feature_names'
   OR parameters-ARRAY['algorithm','event','event_version','producer_version','feature_names','frame_digest','corpus_id','rubric_digest','reference_digest','assessment_mode','means','scales','coefficients','intercept']<>'{}'
   OR NOT (parameters->'algorithm' ?& ARRAY['algorithm','solver','weights','regularization_c','tolerance','max_iterations'])
   OR (parameters->'algorithm')-ARRAY['algorithm','solver','weights','regularization_c','tolerance','max_iterations']<>'{}'
   OR parameters->'algorithm'->>'algorithm' IS DISTINCT FROM 'scaled-logistic-operation-event-1'
   OR parameters->'algorithm'->>'solver' IS DISTINCT FROM 'lbfgs'
   OR parameters->'algorithm'->>'weights' IS DISTINCT FROM 'unit'
   OR (parameters->'algorithm'->>'regularization_c')::numeric<=0
   OR (parameters->'algorithm'->>'tolerance')::numeric<=0
   OR (parameters->'algorithm'->>'max_iterations')::integer<1 THEN
   RAISE EXCEPTION 'fitted parameters lack exact event applicability or finite algorithm' USING ERRCODE='23514'; END IF;
  n:=jsonb_array_length(parameters->'feature_names');
  IF jsonb_array_length(parameters->'means') IS DISTINCT FROM n OR jsonb_array_length(parameters->'scales') IS DISTINCT FROM n
   OR jsonb_array_length(parameters->'coefficients') IS DISTINCT FROM n OR jsonb_typeof(parameters->'intercept') IS DISTINCT FROM 'number'
   OR abs((parameters->>'intercept')::numeric)>1.7976931348623157e308
   OR EXISTS(SELECT FROM jsonb_array_elements(parameters->'scales') s WHERE jsonb_typeof(s)<>'number' OR (s#>>'{}')::numeric<=0 OR (s#>>'{}')::numeric>1.7976931348623157e308)
   OR EXISTS(SELECT FROM jsonb_array_elements((parameters->'means')||(parameters->'coefficients')) s WHERE jsonb_typeof(s)<>'number' OR abs((s#>>'{}')::numeric)>1.7976931348623157e308) THEN
   RAISE EXCEPTION 'operation fitted parameters must be finite and shape-complete' USING ERRCODE='23514'; END IF;
 ELSIF parameters IS DISTINCT FROM 'null'::jsonb THEN
  RAISE EXCEPTION 'failed/unavailable fitting cannot yield runtime parameters' USING ERRCODE='23514';
 END IF;
 IF jsonb_typeof(p_result->'predictions') IS DISTINCT FROM 'array'
  OR (p_result->>'status'='fitted' AND jsonb_array_length(p_result->'predictions')<>jsonb_array_length(p_frame->'frame'->'event_ids')) THEN
  RAISE EXCEPTION 'fitted event predictions require their complete declared population' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(p_result->'predictions')>0 THEN
  IF (SELECT jsonb_agg(x->>'event_id' ORDER BY ord) FROM jsonb_array_elements(p_result->'predictions') WITH ORDINALITY AS q(x,ord)) IS DISTINCT FROM p_frame->'frame'->'event_ids'
   OR EXISTS(SELECT FROM jsonb_array_elements(p_result->'predictions') x JOIN jsonb_array_elements(p_frame->'frame'->'observations') o ON x->>'event_id'=o->>'event_id' WHERE x->>'judgment' IS DISTINCT FROM o->>'judgment') THEN
   RAISE EXCEPTION 'operation predictions change exact event/label identity' USING ERRCODE='23514'; END IF;
 END IF;
 INSERT INTO eval.operation_event_fit(project_id,evaluation_id,run_id,cut_id,release_id,set_id,source_frame_digest,reference_snapshot,frame,result,content_digest)
 VALUES(p_project,p_evaluation,(p_frame->>'run_id')::bigint,(p_frame->>'cut_id')::bigint,p_frame->>'release_id',(p_frame->>'set_id')::bigint,
 p_frame->>'source_frame_digest',p_frame->'reference_snapshot',p_frame,p_result,
 encode(sha256(convert_to(data.canonical_json(jsonb_build_object('frame',p_frame,'result',p_result)),'UTF8')),'hex')) RETURNING id INTO result_id;
 RETURN result_id;
END $$;
REVOKE ALL ON FUNCTION eval.record_operation_event_fit(text,bigint,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_operation_event_fit(text,bigint,jsonb,jsonb) TO corpus_sem_evaluator,corpus_sem_fitter;

CREATE OR REPLACE FUNCTION eval.read_operation_event_fit(p_project text,p_fit bigint,p_protected boolean)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE fitted eval.operation_event_fit;
BEGIN
 SELECT * INTO STRICT fitted FROM eval.operation_event_fit WHERE id=p_fit AND project_id=p_project;
 IF p_protected AND NOT (pg_has_role(session_user,'corpus_sem_evaluator','MEMBER') OR pg_has_role(session_user,'corpus_sem_fitter','MEMBER')) THEN
  RAISE EXCEPTION 'operation labels require protected evaluator/fitter purpose' USING ERRCODE='42501'; END IF;
 IF fitted.content_digest IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(jsonb_build_object('frame',fitted.frame,'result',fitted.result)),'UTF8')),'hex') THEN
  RAISE EXCEPTION 'immutable operation fit digest differs' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_execution_operation(fitted.release_id,'reference_operation_fit');
 IF p_protected THEN RETURN to_jsonb(fitted); END IF;
 RETURN jsonb_build_object('id',fitted.id,'content_digest',fitted.content_digest,'status',fitted.result->>'status',
  'parameters',fitted.result->'parameters','quality_claim','not_established','assessment_mode','in_sample_development');
END $$;
REVOKE ALL ON FUNCTION eval.read_operation_event_fit(text,bigint,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.read_operation_event_fit(text,bigint,boolean) TO corpus_sem_reader,corpus_sem_evaluator,corpus_sem_fitter;
