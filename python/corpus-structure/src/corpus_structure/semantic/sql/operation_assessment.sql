-- Operation-local references reuse protected eval tables and source closure validators.
CREATE OR REPLACE FUNCTION eval.create_operation_reference_set(p_project text,p_run bigint,p_label text,p_split text,p_guideline text,p_sampling jsonb,p_units jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint; source_release text; unit jsonb; metadata jsonb; group_snapshot jsonb; unit_id bigint; unit_snapshot jsonb; frozen_frame jsonb; source_cut bigint; membership_snapshot jsonb;
BEGIN
 SELECT release_id INTO STRICT source_release FROM ops.run WHERE id=p_run AND project_id=p_project FOR UPDATE;
 source_cut:=COALESCE((p_sampling->>'source_cut_id')::bigint,(SELECT cut_id FROM ops.completed_result WHERE run_id=p_run));
 IF NOT EXISTS(SELECT FROM ops.input_cut WHERE id=source_cut AND run_id=p_run AND release_id=source_release) THEN
  RAISE EXCEPTION 'record references require an explicitly sealed source-ready cut or completed source cut' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_execution_operation(source_release,'reference_operation_set');
 IF p_split NOT IN ('dev','test') OR p_split IS NULL OR p_guideline IS NULL OR btrim(p_guideline)=''
  OR jsonb_typeof(p_units) IS DISTINCT FROM 'array' OR jsonb_array_length(p_units)=0
  OR jsonb_typeof(p_sampling) IS DISTINCT FROM 'object'
  OR p_sampling->>'operation_protocol' IS DISTINCT FROM 'source-operation-reference-1'
  OR COALESCE(p_sampling->>'source_frame_abi','') NOT IN ('source-operation-frame-1','source-operation-frame-2')
  OR p_sampling->>'partition' NOT IN ('development','feature_fit','final_event_calibration','final_assessment')
  OR btrim(COALESCE(p_sampling->>'guideline_text',''))=''
  OR p_sampling->>'guideline_digest' IS DISTINCT FROM encode(sha256(convert_to(p_sampling->>'guideline_text','UTF8')),'hex')
  OR NOT(p_sampling ?& ARRAY['seed','strata','inclusion_probabilities','provenance','cohort','partition'])
  OR jsonb_typeof(p_sampling->'seed') IS DISTINCT FROM 'number' OR (p_sampling->>'seed') !~ '^-?(0|[1-9][0-9]*)$'
  OR jsonb_typeof(p_sampling->'strata') IS DISTINCT FROM 'object'
  OR jsonb_typeof(p_sampling->'inclusion_probabilities') IS DISTINCT FROM 'object'
  OR jsonb_typeof(p_sampling->'provenance') IS DISTINCT FROM 'object' OR p_sampling->'provenance'='{}'
  OR btrim(COALESCE(p_sampling->>'cohort',''))='' THEN
  RAISE EXCEPTION 'record sample requires frozen guideline, partition, seed, strata, inclusion and provenance' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(p_units)<>(SELECT count(DISTINCT u->>'unit_key') FROM jsonb_array_elements(p_units) u)
  OR (SELECT count(*) FROM jsonb_object_keys(p_sampling->'inclusion_probabilities'))<>jsonb_array_length(p_units) THEN
  RAISE EXCEPTION 'record sample repeats or omits eligible unit probabilities' USING ERRCODE='23514'; END IF;
 FOR unit IN SELECT value FROM jsonb_array_elements(p_units) LOOP
  IF NOT EXISTS(SELECT FROM kb.source_view v JOIN kb.document d ON d.id=v.document_id
   JOIN eval.document_split legacy ON legacy.project_id=p_project AND legacy.source_uri=d.source_uri AND legacy.split=p_split
   JOIN eval.reference_origin_source member ON member.project_id=p_project AND member.source_uri=d.source_uri
   JOIN eval.reference_origin_group origin ON origin.project_id=member.project_id AND origin.origin_group=member.origin_group
   WHERE v.id=(unit->>'source_view_id')::bigint AND v.key=unit->>'unit_key' AND d.project_id=p_project
    AND origin.partition=p_sampling->>'partition')
   OR jsonb_typeof(p_sampling->'inclusion_probabilities'->(unit->>'unit_key')) IS DISTINCT FROM 'number'
   OR NOT(0<(p_sampling->'inclusion_probabilities'->>(unit->>'unit_key'))::numeric
    AND (p_sampling->'inclusion_probabilities'->>(unit->>'unit_key'))::numeric<=1) THEN
   RAISE EXCEPTION 'sample unit is outside immutable origin partition/legacy split or lacks inclusion probability' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT jsonb_agg(to_jsonb(groups) ORDER BY groups.origin_group) INTO group_snapshot FROM (
  SELECT DISTINCT origin.* FROM jsonb_array_elements(p_units) u JOIN kb.source_view v ON v.id=(u->>'source_view_id')::bigint
  JOIN kb.document d ON d.id=v.document_id JOIN eval.reference_origin_source member ON member.project_id=p_project AND member.source_uri=d.source_uri
  JOIN eval.reference_origin_group origin ON origin.project_id=member.project_id AND origin.origin_group=member.origin_group) groups;
 SELECT jsonb_agg(u||jsonb_build_object('origin_group',member.origin_group,'source_uri',d.source_uri) ORDER BY u->>'unit_key')
 INTO unit_snapshot FROM jsonb_array_elements(p_units) u JOIN kb.source_view v ON v.id=(u->>'source_view_id')::bigint
 JOIN kb.document d ON d.id=v.document_id JOIN eval.reference_origin_source member ON member.project_id=p_project AND member.source_uri=d.source_uri;
 SELECT jsonb_agg(to_jsonb(member) ORDER BY source_view_id) INTO membership_snapshot FROM ops.run_source_view member WHERE run_id=p_run;
 metadata:=p_sampling||jsonb_build_object('origin_groups',group_snapshot,'eligible_units',unit_snapshot,
  'source_cut_id',source_cut,'source_membership',membership_snapshot,'membership_snapshot_kind','reference_set_creation');
 INSERT INTO eval.reference_set(project_id,release_id,source_run_id,label,split,guideline,sampling)
 VALUES(p_project,source_release,p_run,p_label,p_split,p_guideline,metadata) RETURNING id INTO result;
 FOR unit IN SELECT value FROM jsonb_array_elements(p_units) LOOP
  SELECT unit->'frame'||jsonb_build_object('source_views',jsonb_agg(to_jsonb(v) ORDER BY v.id)) INTO frozen_frame
  FROM kb.source_view v WHERE v.id IN (
   SELECT (unit->'frame'->'evaluation_frame'->'pin'->>'source_view_id')::bigint UNION ALL
   SELECT (pin->>'source_view_id')::bigint FROM jsonb_array_elements(unit->'frame'->'evaluation_frame'->'related_pins') pin);
  INSERT INTO eval.reference_unit(set_id,source_view_id,projection_digest,unit_key,context)
  SELECT result,v.id,v.projection_digest,unit->>'unit_key',jsonb_build_array(frozen_frame) FROM kb.source_view v
  WHERE v.id=(unit->>'source_view_id')::bigint AND v.key=unit->>'unit_key' AND EXISTS(
   SELECT FROM jsonb_array_elements(membership_snapshot) m WHERE (m->>'source_view_id')::bigint=v.id)
  RETURNING id INTO STRICT unit_id;
  PERFORM eval.validate_operation_reference_frame(unit_id,jsonb_build_object(
   'protocol','source-operation-reference-1','release_id',source_release,'unit_ref',unit->>'unit_key',
   'guideline',p_guideline,'rubric_version',frozen_frame->'evaluation_frame'->>'rubric_version',
   'context_policy',frozen_frame->'evaluation_frame'->>'context_policy','reason','source-only frame freeze','cases','[]'::jsonb)||
   ((frozen_frame->'evaluation_frame')-ARRAY['unit','release_id','guideline_version','pin','anchor_ids','related_pins','anchor_scopes','contribution_ids','source_group','partition','inspected_scope','opportunities','exposure_history']),frozen_frame);
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.create_operation_reference_set(text,bigint,text,text,text,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.create_operation_reference_set(text,bigint,text,text,text,jsonb,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.validate_operation_reference_frame(p_unit bigint,p_payload jsonb,p_frame jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE unit eval.reference_unit; reference_set eval.reference_set; selected kb.source_view;
 source_record jsonb; pin jsonb; bound jsonb; expected jsonb; related kb.source_view;
 captured jsonb; captured_view kb.source_view; source_snapshot jsonb; scope jsonb; scope_schema json; scope_pointer text; scope_node jsonb; scope_text text; capture_schema json;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=unit.set_id;
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=unit.source_view_id;
 bound:=p_frame->'evaluation_frame';
 IF unit.context IS DISTINCT FROM jsonb_build_array(p_frame)
  OR COALESCE(p_frame->>'protocol','') NOT IN ('source-operation-frame-1','source-operation-frame-2') OR p_frame-ARRAY['protocol','evaluation_frame','source_views','captured_coordinates','context_dependency_digest']<>'{}'
  OR jsonb_typeof(bound) IS DISTINCT FROM 'object'
  OR bound-ARRAY['unit','release_id','guideline_version','rubric_version','context_policy','pin','anchor_ids','related_pins','anchor_scopes','operation_question','operation_version','domain','direction','contribution_ids','source_group','partition','inspected_scope','opportunities','exposure_history']<>'{}'
  OR p_payload->>'protocol' IS DISTINCT FROM 'source-operation-reference-1'
  OR p_payload-ARRAY['protocol','release_id','unit_ref','guideline','rubric_version','context_policy',
    'operation_question','operation_version','domain','direction','reason','cases','adjudication_passes']<>'{}'
  OR reference_set.sampling->>'operation_protocol' IS DISTINCT FROM 'source-operation-reference-1'
  OR btrim(COALESCE(reference_set.sampling->>'guideline_text',''))=''
  OR reference_set.sampling->>'guideline_digest' IS DISTINCT FROM encode(sha256(convert_to(reference_set.sampling->>'guideline_text','UTF8')),'hex')
  OR reference_set.sampling->>'membership_snapshot_kind' IS DISTINCT FROM 'reference_set_creation'
  OR NOT EXISTS(SELECT FROM ops.input_cut WHERE id=(reference_set.sampling->>'source_cut_id')::bigint
    AND run_id=reference_set.source_run_id AND release_id=reference_set.release_id)
  OR p_payload->>'release_id' IS DISTINCT FROM reference_set.release_id
  OR p_payload->>'unit_ref' IS DISTINCT FROM unit.unit_key OR bound->>'unit' IS DISTINCT FROM unit.unit_key
  OR bound->>'release_id' IS DISTINCT FROM reference_set.release_id
  OR p_payload->>'guideline' IS DISTINCT FROM reference_set.guideline
  OR bound->>'guideline_version' IS DISTINCT FROM reference_set.guideline
  OR bound->>'rubric_version' IS DISTINCT FROM p_payload->>'rubric_version'
  OR bound->>'context_policy' IS DISTINCT FROM p_payload->>'context_policy'
  OR unit.projection_digest IS DISTINCT FROM selected.projection_digest
  OR jsonb_typeof(bound->'anchor_ids') IS DISTINCT FROM 'array'
  OR jsonb_typeof(bound->'related_pins') IS DISTINCT FROM 'array'
  OR jsonb_typeof(bound->'anchor_scopes') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_frame->'source_views') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_frame->'captured_coordinates') IS DISTINCT FROM 'array'
  OR (p_frame->>'context_dependency_digest' IS NOT NULL AND (p_frame->>'context_dependency_digest') !~ '^[a-f0-9]{64}$')
  OR btrim(COALESCE(p_payload->>'reason',''))=''
  OR bound->>'direction' NOT IN ('source_first','output_first')
  OR jsonb_typeof(bound->'contribution_ids') IS DISTINCT FROM 'array'
  OR (bound->>'direction'='source_first' AND bound->'contribution_ids'<>'[]')
  OR (bound->>'direction'='output_first' AND jsonb_array_length(bound->'contribution_ids')=0)
  OR EXISTS(SELECT FROM unnest(ARRAY['rubric_version','context_policy','operation_question','operation_version','domain','direction']) k
    WHERE btrim(COALESCE(bound->>k,''))='' OR p_payload->>k IS DISTINCT FROM bound->>k) THEN
  RAISE EXCEPTION 'record reference differs from frozen source/guideline/release protocol' USING ERRCODE='23514'; END IF;
 IF bound->>'direction'='output_first' AND EXISTS(
  SELECT FROM jsonb_array_elements_text(bound->'contribution_ids') identity WHERE NOT EXISTS(
   SELECT FROM kb.source_contribution contribution JOIN ops.task selected_task
    ON contribution.task_id=COALESCE(selected_task.reused_task_id,selected_task.id)
   JOIN kb.source_contribution_operation operation ON operation.task_id=contribution.task_id
    AND operation.operation_key=contribution.operation_key
   WHERE selected_task.run_id=reference_set.source_run_id AND contribution.source_view_id=unit.source_view_id
    AND contribution.contribution_id=identity AND contribution.release_id=reference_set.release_id
    AND operation.question=bound->>'operation_question' AND operation.operation_version=bound->>'operation_version')) THEN
  RAISE EXCEPTION 'output-first selection is outside retained operation contribution population' USING ERRCODE='23514'; END IF;
 expected:=eval.validate_reference_source_scope(p_unit,p_frame);
 IF jsonb_typeof(p_payload->'cases') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'operation cases must be an array' USING ERRCODE='23514'; END IF;
 IF p_frame->>'protocol' IS DISTINCT FROM reference_set.sampling->>'source_frame_abi' THEN
  RAISE EXCEPTION 'operation frame ABI differs from frozen set' USING ERRCODE='23514'; END IF;
 IF p_frame->>'protocol'='source-operation-frame-1' THEN
  IF bound ?| ARRAY['source_group','partition','inspected_scope','opportunities','exposure_history'] THEN
   RAISE EXCEPTION 'legacy frame cannot contain version two fields' USING ERRCODE='23514'; END IF;
 ELSE
  IF bound->>'partition' IS DISTINCT FROM reference_set.sampling->>'partition'
   OR btrim(COALESCE(bound->>'source_group',''))='' OR btrim(COALESCE(bound->>'inspected_scope',''))=''
   OR jsonb_typeof(bound->'opportunities') IS DISTINCT FROM 'array' OR jsonb_array_length(bound->'opportunities')=0
   OR jsonb_typeof(bound->'exposure_history') IS DISTINCT FROM 'array'
   OR (bound->>'partition' IN ('final_event_calibration','final_assessment') AND bound->'exposure_history'<>'[]')
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(reference_set.sampling->'eligible_units') u
    WHERE u->>'unit_key'=unit.unit_key AND u->>'origin_group'=bound->>'source_group')
   OR EXISTS(SELECT FROM jsonb_array_elements(bound->'opportunities') o GROUP BY o->>'opportunity_id' HAVING count(*)>1) THEN
   RAISE EXCEPTION 'operation source opportunities differ from frozen group/partition' USING ERRCODE='23514'; END IF;
  FOR source_record IN SELECT value FROM jsonb_array_elements(bound->'opportunities') LOOP
   IF source_record-ARRAY['opportunity_id','source_view_id','start','end','facet','source_state']<>'{}'
    OR jsonb_typeof(source_record->'source_view_id') IS DISTINCT FROM 'number'
    OR jsonb_typeof(source_record->'start') IS DISTINCT FROM 'number' OR jsonb_typeof(source_record->'end') IS DISTINCT FROM 'number'
    OR btrim(COALESCE(source_record->>'opportunity_id',''))='' OR btrim(COALESCE(source_record->>'facet',''))=''
    OR COALESCE(source_record->>'source_state','') NOT IN ('stated','unstated','inapplicable','unresolved','uninspected')
    OR COALESCE(source_record->>'start','') !~ '^[0-9]+$' OR COALESCE(source_record->>'end','') !~ '^[0-9]+$'
    OR (source_record->>'end')::bigint <= (source_record->>'start')::bigint
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_frame->'source_views') v WHERE v->>'id'=source_record->>'source_view_id'
     AND (source_record->>'end')::bigint<=length(v->'projection'->>'text')) THEN
    RAISE EXCEPTION 'invalid independent source opportunity' USING ERRCODE='23514'; END IF;
  END LOOP;
 END IF;
 FOR source_record IN SELECT value FROM jsonb_array_elements(p_payload->'cases') LOOP
  IF source_record-ARRAY['case_id','facet','anchor_ids','inspected_scope','source_state','judgment','alternatives','explanation',
    'assessor_provenance','contribution_kind','contribution_id','error_category','candidate_selector','permissible_anchor_sets','expectation_mode','anchor_endpoint_role']<>'{}'
   OR NOT(source_record ?& ARRAY['case_id','facet','anchor_ids','inspected_scope','source_state','judgment','alternatives','explanation','assessor_provenance'])
   OR EXISTS(SELECT FROM unnest(ARRAY['case_id','facet','inspected_scope','explanation']) k WHERE btrim(COALESCE(source_record->>k,''))='')
   OR COALESCE(source_record->>'judgment','') NOT IN ('supported','unsupported','ambiguous','unassessed')
   OR COALESCE(source_record->>'source_state','') NOT IN ('stated','unstated','uninspected','unresolved')
   OR jsonb_typeof(source_record->'anchor_ids') IS DISTINCT FROM 'array'
   OR jsonb_typeof(source_record->'alternatives') IS DISTINCT FROM 'array'
   OR jsonb_typeof(source_record->'assessor_provenance') IS DISTINCT FROM 'object' OR source_record->'assessor_provenance'='{}'
   OR (source_record ? 'candidate_selector' AND jsonb_typeof(source_record->'candidate_selector') IS DISTINCT FROM 'object')
   OR COALESCE(source_record->>'expectation_mode','structure') NOT IN ('structure','absence_detection')
   OR (source_record->>'anchor_endpoint_role' IS NOT NULL AND (
    COALESCE(source_record->>'contribution_kind','proposal') NOT IN ('proposal','relation')
    OR jsonb_typeof(source_record->'anchor_endpoint_role')<>'string'
    OR btrim(source_record->>'anchor_endpoint_role')=''))
   OR EXISTS(SELECT FROM jsonb_array_elements(source_record->'alternatives') a WHERE jsonb_typeof(a)<>'object' OR a='{}')
   OR (source_record->>'source_state'='uninspected' AND source_record->>'judgment'<>'unassessed')
   OR (source_record->>'source_state'='stated' AND source_record->>'judgment'='supported' AND source_record->'alternatives'='[]')
   OR NOT((bound->'anchor_ids') @> (source_record->'anchor_ids'))
   OR EXISTS(SELECT FROM jsonb_array_elements(source_record->'alternatives') expected_option
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(expected_option->'endpoint_semantics','[]')) endpoint
    WHERE endpoint-ARRAY['role','anchor_ids','fields']<>'{}' OR btrim(COALESCE(endpoint->>'role',''))=''
     OR jsonb_typeof(endpoint->'anchor_ids') IS DISTINCT FROM 'array'
     OR jsonb_typeof(endpoint->'fields') IS DISTINCT FROM 'object'
     OR NOT((bound->'anchor_ids') @> (endpoint->'anchor_ids')))
   OR (source_record ? 'permissible_anchor_sets' AND (jsonb_typeof(source_record->'permissible_anchor_sets') IS DISTINCT FROM 'array'
     OR EXISTS(SELECT FROM jsonb_array_elements(source_record->'permissible_anchor_sets') permitted
      WHERE jsonb_typeof(permitted)<>'array' OR NOT((bound->'anchor_ids') @> permitted))))
   OR (bound->>'direction'='source_first' AND source_record->>'contribution_id' IS NOT NULL)
   OR (bound->>'direction'='output_first' AND (source_record->>'contribution_id' IS NULL OR NOT(bound->'contribution_ids' ? (source_record->>'contribution_id')))) THEN
   RAISE EXCEPTION 'operation case differs from independent source/facet authority' USING ERRCODE='23514'; END IF;

 END LOOP;
 IF jsonb_array_length(p_payload->'cases')<>(SELECT count(DISTINCT r->>'case_id') FROM jsonb_array_elements(p_payload->'cases') r) THEN
  RAISE EXCEPTION 'operation reference duplicates case identities' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION eval.validate_operation_reference_frame(bigint,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_operation_reference_pass(p_unit bigint,p_kind text,p_actor text,p_authored bytea,p_frame jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint; unit eval.reference_unit; reference_set eval.reference_set;
 payload jsonb; schema json; pass_a eval.reference_pass; pass_b eval.reference_pass; source_record jsonb; frame_id bigint;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit FOR UPDATE;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=unit.set_id;
 PERFORM sem.require_execution_operation(reference_set.release_id,'reference_operation_pass');
 payload:=convert_from(p_authored,'UTF8')::jsonb;
 IF p_kind NOT IN ('A','B','C') OR p_kind IS NULL
  OR btrim(COALESCE(p_actor,''))='' THEN
  RAISE EXCEPTION 'record reference pass differs from released independent protocol' USING ERRCODE='23514'; END IF;
 PERFORM eval.validate_operation_reference_frame(p_unit,payload,p_frame);
 -- All independent authors and adjudication see the same frozen primary/related cut.
 IF EXISTS(SELECT FROM eval.reference_pass p JOIN eval.reference_frame f ON f.pass_id=p.id
  WHERE p.unit_id=p_unit AND f.source_frame IS DISTINCT FROM p_frame) THEN
  RAISE EXCEPTION 'record reference pass attempts silent frame relocation' USING ERRCODE='23514'; END IF;
 SELECT * INTO pass_a FROM eval.reference_pass WHERE unit_id=p_unit AND pass_kind='A' ORDER BY id DESC LIMIT 1;
 SELECT * INTO pass_b FROM eval.reference_pass WHERE unit_id=p_unit AND pass_kind='B' ORDER BY id DESC LIMIT 1;
 IF (p_kind='A' AND pass_b.actor=p_actor) OR (p_kind='B' AND pass_a.actor=p_actor) THEN
  RAISE EXCEPTION 'record A and B authors must be independent' USING ERRCODE='23514'; END IF;
 IF p_kind='C' THEN
  IF pass_a.id IS NULL OR pass_b.id IS NULL OR p_actor IN (pass_a.actor,pass_b.actor)
   OR payload->'adjudication_passes' IS DISTINCT FROM jsonb_build_array(pass_a.id,pass_b.id) THEN
   RAISE EXCEPTION 'record C requires independent retained A/B and explicit adjudication linkage' USING ERRCODE='23514'; END IF;
 ELSIF COALESCE(payload->'adjudication_passes','[]')<>'[]' THEN
  RAISE EXCEPTION 'only adjudication C may cite author passes' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_pass(unit_id,pass_kind,actor,authored,content_digest)
 VALUES(p_unit,p_kind,p_actor,p_authored,encode(sha256(p_authored),'hex')) RETURNING id INTO result;
 INSERT INTO eval.reference_frame(pass_id,version,source_view_id,projection_digest,frame,source_frame)
 VALUES(result,1,unit.source_view_id,unit.projection_digest,'[]',p_frame) RETURNING id INTO frame_id;
 FOR source_record IN SELECT value FROM jsonb_array_elements(payload->'cases') LOOP
  INSERT INTO eval.reference_item(pass_id,frame_id,item_kind,local_ref,payload)
  VALUES(result,frame_id,source_record->>'facet',source_record->>'case_id',source_record);
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_operation_reference_pass(bigint,text,text,bytea,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_operation_reference_pass(bigint,text,text,bytea,jsonb) TO corpus_sem_evaluator;


CREATE OR REPLACE FUNCTION eval.operation_author_packet(p_unit bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE unit eval.reference_unit; reference_set eval.reference_set; source_frame jsonb;
 selected kb.source_view; context jsonb; contexts jsonb:='[]'; schema jsonb;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=unit.set_id;
 PERFORM sem.require_execution_operation(reference_set.release_id,'reference_operation_pass');
 source_frame:=unit.context->0;
 PERFORM eval.validate_operation_reference_frame(p_unit,jsonb_build_object(
  'protocol','source-operation-reference-1','release_id',reference_set.release_id,'unit_ref',unit.unit_key,
  'guideline',reference_set.guideline,'rubric_version',source_frame->'evaluation_frame'->>'rubric_version',
  'context_policy',source_frame->'evaluation_frame'->>'context_policy',
  'reason','source-only author packet','cases','[]'::jsonb)||
   ((source_frame->'evaluation_frame')-ARRAY['unit','release_id','guideline_version','pin','anchor_ids','related_pins','anchor_scopes','contribution_ids','source_group','partition','inspected_scope','opportunities','exposure_history']),source_frame);
 FOR selected IN SELECT v.* FROM jsonb_array_elements(source_frame->'source_views') frozen
  JOIN kb.source_view v ON v.id=(frozen->>'id')::bigint ORDER BY v.id LOOP
  SELECT COALESCE(jsonb_object_agg(pointer,native_json),'{}') INTO context FROM ops.read_pdf_published_items(
   selected.native_task_id,selected.native_product_key,selected.native_content_digest,ARRAY(
    SELECT value FROM jsonb_array_elements_text(selected.projection->'items')
    UNION SELECT value FROM jsonb_array_elements_text(COALESCE(selected.projection->'ancestors','[]'))));
  contexts:=contexts||jsonb_build_array(jsonb_build_object('source_view_id',selected.id,'native_items',context));
 END LOOP;
 RETURN jsonb_build_object('protocol','source-operation-author-packet-1','unit_id',p_unit,
  'unit_ref',unit.unit_key,'release_id',reference_set.release_id,'guideline',reference_set.guideline,
  'guideline_text',reference_set.sampling->'guideline_text','guideline_digest',reference_set.sampling->'guideline_digest',
  'source_frame',jsonb_set(source_frame,'{evaluation_frame}',(source_frame->'evaluation_frame')-'contribution_ids'),'native_contexts',contexts);
END $$;
REVOKE ALL ON FUNCTION eval.operation_author_packet(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_author_packet(bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.validate_operation_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference_set eval.reference_set; completed ops.completed_result; snap jsonb;
 unit eval.reference_unit; source_frame jsonb; authored jsonb;
BEGIN
 PERFORM 1 FROM eval.reference_unit WHERE set_id=p_set FOR UPDATE;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 SELECT c.* INTO STRICT completed FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id
  JOIN ops.input_cut cut ON cut.id=c.cut_id AND cut.run_id=r.id AND cut.release_id=c.release_id
  WHERE c.run_id=p_run AND r.project_id=p_project AND r.sealed AND r.status='finished' AND cut.final;
 PERFORM sem.require_execution_operation(completed.release_id,'reference_operation_grade');
 IF reference_set.sampling->>'operation_protocol' IS DISTINCT FROM 'source-operation-reference-1'
  OR completed.release_id IS DISTINCT FROM reference_set.release_id
  OR p_snapshot IS DISTINCT FROM eval.native_reference_snapshot(p_set)
  OR jsonb_array_length(p_snapshot)=0
  OR jsonb_array_length(p_snapshot)<>(SELECT count(*) FROM eval.reference_unit WHERE set_id=p_set)
  OR p_result->>'protocol' IS DISTINCT FROM 'source-operation-evaluation-1'
  OR p_result->>'release_id' IS DISTINCT FROM completed.release_id
  OR (p_result->>'set_id')::bigint IS DISTINCT FROM p_set
  OR (p_result->>'run_id')::bigint IS DISTINCT FROM p_run
  OR p_result->'reference_snapshot' IS DISTINCT FROM p_snapshot
  OR p_result->>'partition' IS DISTINCT FROM reference_set.sampling->>'partition'
  OR p_result->>'quality_claim' IS DISTINCT FROM 'not_established'
  OR p_result->>'population_claim' IS DISTINCT FROM 'declared_cases_only'
  OR jsonb_typeof(p_result->'units') IS DISTINCT FROM 'array'
  OR jsonb_array_length(p_result->'units')<>jsonb_array_length(p_snapshot) THEN
  RAISE EXCEPTION 'operation evaluation source/release/snapshot differs or is stale' USING ERRCODE='23514'; END IF;
 FOR snap IN SELECT value FROM jsonb_array_elements(p_snapshot) LOOP
  SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=(snap->>'unit_id')::bigint AND set_id=p_set;
  SELECT f.source_frame,convert_from(p.authored,'UTF8')::jsonb INTO STRICT source_frame,authored
   FROM eval.reference_pass p JOIN eval.reference_frame f ON f.pass_id=p.id
   WHERE p.id=(snap->>'pass_id')::bigint AND f.id=(snap->>'frame_id')::bigint
    AND p.unit_id=unit.id AND p.pass_kind='C' AND p.content_digest=snap->>'content_digest';
  PERFORM eval.validate_operation_reference_frame(unit.id,authored,source_frame);
  IF NOT EXISTS(SELECT FROM ops.run_source_view v WHERE v.run_id=p_run AND v.source_view_id=unit.source_view_id)
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_result->'units') assessed
    WHERE (assessed->>'unit_id')::bigint=unit.id AND (assessed->>'source_view_id')::bigint=unit.source_view_id
     AND assessed->>'direction'=source_frame->'evaluation_frame'->>'direction'
     AND jsonb_array_length(assessed->'cases')=jsonb_array_length(authored->'cases')
     AND NOT EXISTS(SELECT FROM jsonb_array_elements(authored->'cases') expected WHERE NOT EXISTS(
       SELECT FROM jsonb_array_elements(assessed->'cases') actual WHERE actual->>'case_id'=expected->>'case_id'
        AND actual->>'facet'=expected->>'facet' AND actual->>'judgment' IN ('supported','unsupported','ambiguous','unassessed')))) THEN
   RAISE EXCEPTION 'operation evaluation misses selected source cases or changes their grain' USING ERRCODE='23514'; END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION eval.validate_operation_reference_evaluation(text,bigint,bigint,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_operation_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint;
BEGIN
 -- The table's trusted-set trigger dispatches to the same owned validator for every insert.
 INSERT INTO eval.reference_evaluation(project_id,run_id,set_id,reference_snapshot,result,content_digest)
 VALUES(p_project,p_run,p_set,p_snapshot,p_result,encode(sha256(convert_to(data.canonical_json(
  jsonb_build_object('snapshot',p_snapshot,'result',p_result)),'UTF8')),'hex')) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_operation_reference_evaluation(text,bigint,bigint,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_operation_reference_evaluation(text,bigint,bigint,jsonb,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.operation_review_export(p_project text,p_set bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference_set eval.reference_set; inventory jsonb; judgments jsonb;
BEGIN
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 IF reference_set.sampling->>'operation_protocol' IS DISTINCT FROM 'source-operation-reference-1' THEN
  RAISE EXCEPTION 'review export requires operation references' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('unit_id',u.id,'unit_ref',u.unit_key,
  'source_view_id',u.source_view_id,'direction',u.context->0->'evaluation_frame'->>'direction',
  'adjudicated',EXISTS(SELECT FROM eval.reference_pass p WHERE p.unit_id=u.id AND p.pass_kind='C')) ORDER BY u.id),'[]')
 INTO inventory FROM eval.reference_unit u WHERE u.set_id=p_set;
 IF reference_set.sampling->>'partition'='development' THEN
  SELECT COALESCE(jsonb_agg(jsonb_build_object('unit_id',u.id,'pass_id',p.id,'actor',p.actor,
   'content_digest',p.content_digest,'authored',convert_from(p.authored,'UTF8')::jsonb) ORDER BY u.id),'[]')
  INTO judgments FROM eval.reference_unit u JOIN LATERAL(
   SELECT * FROM eval.reference_pass WHERE unit_id=u.id AND pass_kind='C' ORDER BY id DESC LIMIT 1) p ON true WHERE u.set_id=p_set;
 ELSE judgments:='[]'; END IF;
 RETURN jsonb_build_object('protocol','source-operation-review-export-1','set_id',p_set,
  'partition',reference_set.sampling->>'partition','inventory',inventory,'judgments',judgments,
  'judgments_exposed',reference_set.sampling->>'partition'='development','quality_claim','not_established');
END $$;
REVOKE ALL ON FUNCTION eval.operation_review_export(text,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_review_export(text,bigint) TO corpus_sem_evaluator;
