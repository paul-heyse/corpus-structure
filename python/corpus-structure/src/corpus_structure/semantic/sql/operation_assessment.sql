CREATE OR REPLACE FUNCTION eval.validate_semantic_task_reference(p_reference jsonb,p_frame jsonb,p_opportunity jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE shape json := $task_schema${"$defs":{"JointQuery":{"additionalProperties":false,"properties":{"members":{"items":{"type":"string"},"maxItems":64,"minItems":1,"title":"Members","type":"array"},"expected":{"enum":["permitted","forbidden","unknown"],"title":"Expected","type":"string"}},"required":["members","expected"],"title":"JointQuery","type":"object"},"TaskAssertion":{"additionalProperties":false,"properties":{"subject":{"minLength":1,"title":"Subject","type":"string"},"relation":{"minLength":1,"title":"Relation","type":"string"},"object":{"minLength":1,"title":"Object","type":"string"},"requires":{"default":[],"items":{"type":"string"},"maxItems":64,"title":"Requires","type":"array"},"order":{"anyOf":[{"minimum":0,"type":"integer"},{"type":"null"}],"default":null,"title":"Order"},"standing":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"title":"Standing"}},"required":["subject","relation","object"],"title":"TaskAssertion","type":"object"},"TaskEntity":{"additionalProperties":false,"properties":{"id":{"minLength":1,"title":"Id","type":"string"},"kind":{"enum":["predicate","participant","operator","binder","variable","source","unknown","formal"],"title":"Kind","type":"string"},"extents":{"items":{"$ref":"#/$defs/TaskExtent"},"maxItems":64,"minItems":1,"title":"Extents","type":"array"},"value":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"title":"Value"},"support":{"default":"literal","enum":["literal","implicit_site"],"title":"Support","type":"string"}},"required":["id","kind","extents"],"title":"TaskEntity","type":"object"},"TaskExtent":{"additionalProperties":false,"properties":{"source_view_id":{"exclusiveMinimum":0,"title":"Source View Id","type":"integer"},"projection":{"pattern":"^[a-f0-9]{64}$","title":"Projection","type":"string"},"native_pointer":{"minLength":1,"title":"Native Pointer","type":"string"},"start":{"minimum":0,"title":"Start","type":"integer"},"end":{"minimum":0,"title":"End","type":"integer"}},"required":["source_view_id","projection","native_pointer","start","end"],"title":"TaskExtent","type":"object"},"TaskGroup":{"additionalProperties":false,"properties":{"id":{"minLength":1,"title":"Id","type":"string"},"compatibility":{"enum":["exclusive","compatible","unknown"],"title":"Compatibility","type":"string"},"members":{"items":{"$ref":"#/$defs/TaskMember"},"maxItems":64,"minItems":1,"title":"Members","type":"array"}},"required":["id","compatibility","members"],"title":"TaskGroup","type":"object"},"TaskMember":{"additionalProperties":false,"properties":{"id":{"minLength":1,"title":"Id","type":"string"},"root":{"minLength":1,"title":"Root","type":"string"},"requires":{"default":[],"items":{"type":"string"},"maxItems":64,"title":"Requires","type":"array"}},"required":["id","root"],"title":"TaskMember","type":"object"},"TaskSlot":{"additionalProperties":false,"properties":{"subject":{"minLength":1,"title":"Subject","type":"string"},"relation":{"minLength":1,"title":"Relation","type":"string"}},"required":["subject","relation"],"title":"TaskSlot","type":"object"}},"additionalProperties":false,"properties":{"version":{"const":"characterization-task-reference-v1","title":"Version","type":"string"},"task":{"enum":["roles","scope","binding","choices","modal_force","formal"],"title":"Task","type":"string"},"role_scheme":{"enum":["construction-children-v1","contextual-source-hypotheses-1","formal-children-v1"],"title":"Role Scheme","type":"string"},"mode":{"enum":["witness","complete_slots"],"title":"Mode","type":"string"},"focus":{"minLength":1,"title":"Focus","type":"string"},"entities":{"items":{"$ref":"#/$defs/TaskEntity"},"maxItems":128,"minItems":1,"title":"Entities","type":"array"},"assertions":{"default":[],"items":{"$ref":"#/$defs/TaskAssertion"},"maxItems":256,"title":"Assertions","type":"array"},"complete_slots":{"default":[],"items":{"$ref":"#/$defs/TaskSlot"},"maxItems":64,"title":"Complete Slots","type":"array"},"groups":{"default":[],"items":{"$ref":"#/$defs/TaskGroup"},"maxItems":32,"title":"Groups","type":"array"},"joint_queries":{"default":[],"items":{"$ref":"#/$defs/JointQuery"},"maxItems":64,"title":"Joint Queries","type":"array"}},"required":["version","task","role_scheme","mode","focus","entities"],"title":"SemanticTaskReference","type":"object"}$task_schema$::json;
 roles jsonb := $task_roles${"roles":["agent","agent_cue","antecedent","aspect","attachment_cue","auxiliary","body","complement","connective","copula","focus","governor","grammatical_object","grammatical_subject","head","left","modifier","predicate","right"],"scope":["aspect","auxiliary","body","cue","grammatical_object","grammatical_subject","negative_cue","negative_target","predicate","quantifier_cue","restrictor","target","variable"],"binding":["declared_binding_site","variable"],"choices":[],"modal_force":["cue","target"],"formal":["arguments","base","close","content","cue","denominator","exponent","function","left","lower","member","numerator","open","operand","right","separator","set","upper"]}$task_roles$::jsonb;
 entity jsonb; extent jsonb; assertion jsonb; group_ jsonb; member jsonb; query_ jsonb;
 entities jsonb; members jsonb; allowed jsonb;
BEGIN
 IF NOT public.json_matches_schema(shape,p_reference::json) THEN
  RAISE EXCEPTION 'invalid closed semantic task reference' USING ERRCODE='23514'; END IF;
 SELECT jsonb_agg(e->'id') INTO entities FROM jsonb_array_elements(p_reference->'entities') e;
 SELECT coalesce(jsonb_agg(m->'id'),'[]') INTO members FROM jsonb_array_elements(coalesce(p_reference->'groups','[]')) g CROSS JOIN LATERAL jsonb_array_elements(g->'members') m;
 allowed:=roles->(p_reference->>'task');
 IF jsonb_array_length(entities)<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(entities))
  OR jsonb_array_length(members)<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(members))
  OR (SELECT count(*)<>count(DISTINCT g->>'id') FROM jsonb_array_elements(coalesce(p_reference->'groups','[]')) g)
  OR NOT(entities @> jsonb_build_array(p_reference->'focus'))
  OR (p_reference->>'role_scheme'='contextual-source-hypotheses-1' AND p_reference->>'task'<>'binding')
  OR ((p_reference->>'role_scheme'='formal-children-v1') IS DISTINCT FROM (p_reference->>'task'='formal'))
  OR (p_reference->>'task'='choices' AND jsonb_array_length(coalesce(p_reference->'groups','[]'))=0)
  OR (p_reference->>'mode'='witness' AND (coalesce(p_reference->'complete_slots','[]')<>'[]' OR
   coalesce(p_reference->'assertions','[]')='[]' AND coalesce(p_reference->'groups','[]')='[]' AND coalesce(p_reference->'joint_queries','[]')='[]'))
  OR (p_reference->>'mode'='complete_slots' AND p_reference->>'task'<>'choices' AND coalesce(p_reference->'complete_slots','[]')='[]') THEN
  RAISE EXCEPTION 'semantic task identities or completeness are invalid' USING ERRCODE='23514'; END IF;
 FOR entity IN SELECT value FROM jsonb_array_elements(p_reference->'entities') LOOP
  IF (entity->>'value' IS NOT NULL AND entity->>'kind' NOT IN ('operator','binder','formal'))
   OR (entity->>'kind'='formal' AND coalesce(entity->>'value','')='') THEN
   RAISE EXCEPTION 'task semantic value requires an explicit operator/binder label' USING ERRCODE='23514'; END IF;
  FOR extent IN SELECT value FROM jsonb_array_elements(entity->'extents') LOOP
   IF (coalesce(entity->>'support','literal')='implicit_site' AND (entity->>'kind'<>'variable' OR extent->'start'<>extent->'end'))
    OR (coalesce(entity->>'support','literal')='literal' AND extent->'start'=extent->'end') THEN
    RAISE EXCEPTION 'task literal/implicit source support is invalid' USING ERRCODE='23514'; END IF;
   IF (extent->>'end')::bigint<(extent->>'start')::bigint OR NOT EXISTS(
    SELECT FROM kb.source_view v JOIN jsonb_array_elements(p_frame->'source_views') frozen ON (frozen->>'id')::bigint=v.id CROSS JOIN LATERAL jsonb_array_elements(v.projection->'pieces') piece
    WHERE v.id=(extent->>'source_view_id')::bigint AND v.projection_digest=extent->>'projection'
     AND piece->>'kind'='native_text' AND NOT coalesce((piece->>'synthetic')::boolean,false) AND piece->>'item_ref'=extent->>'native_pointer'
     AND (piece->>'start')::bigint<=(extent->>'start')::bigint AND (extent->>'end')::bigint<=(piece->>'end')::bigint) THEN
    RAISE EXCEPTION 'task entity differs from frozen original source coordinates' USING ERRCODE='23514'; END IF;
   IF entity->>'id'=p_reference->>'focus' AND NOT EXISTS(
    SELECT FROM jsonb_array_elements(p_opportunity->'extents') bound
    WHERE bound->'source_view_id'=extent->'source_view_id' AND bound->'projection'=extent->'projection' AND bound->'native_pointer'=extent->'native_pointer'
     AND (bound->>'start')::bigint<=(extent->>'start')::bigint AND (extent->>'end')::bigint<=(bound->>'end')::bigint) THEN
    RAISE EXCEPTION 'semantic task focus is outside its frozen opportunity' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 FOR assertion IN SELECT value FROM jsonb_array_elements(coalesce(p_reference->'assertions','[]')) LOOP
  IF (assertion->>'order' IS NOT NULL AND (jsonb_typeof(assertion->'order')<>'number' OR assertion->>'order' !~ '^[0-9]+$'))
   OR NOT(entities @> jsonb_build_array(assertion->'subject') AND entities @> jsonb_build_array(assertion->'object') AND allowed @> jsonb_build_array(assertion->'relation') AND members @> coalesce(assertion->'requires','[]'))
   OR (p_reference->>'mode'='complete_slots' AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_reference->'complete_slots') slot WHERE slot->'subject'=assertion->'subject' AND slot->'relation'=assertion->'relation')) THEN
   RAISE EXCEPTION 'semantic assertion changes declared endpoints, roles, choices or slots' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR assertion IN SELECT value FROM jsonb_array_elements(coalesce(p_reference->'complete_slots','[]')) LOOP
  IF NOT(entities @> jsonb_build_array(assertion->'subject') AND allowed @> jsonb_build_array(assertion->'relation')) THEN
   RAISE EXCEPTION 'invalid semantic complete slot' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR group_ IN SELECT value FROM jsonb_array_elements(coalesce(p_reference->'groups','[]')) LOOP
  FOR member IN SELECT value FROM jsonb_array_elements(group_->'members') LOOP
   IF NOT(entities @> jsonb_build_array(member->'root') AND members @> coalesce(member->'requires','[]')) THEN
    RAISE EXCEPTION 'invalid semantic choice roots or prerequisites' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 FOR query_ IN SELECT value FROM jsonb_array_elements(coalesce(p_reference->'joint_queries','[]')) LOOP
  IF NOT(members @> query_->'members') OR jsonb_array_length(query_->'members')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(query_->'members')) THEN
   RAISE EXCEPTION 'invalid semantic joint choice question' USING ERRCODE='23514'; END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION eval.validate_semantic_task_reference(jsonb,jsonb,jsonb) FROM PUBLIC;

-- Operation-local references reuse protected eval tables and source closure validators.
CREATE OR REPLACE FUNCTION eval.create_operation_reference_set(p_project text,p_run bigint,p_label text,p_split text,p_guideline text,p_sampling jsonb,p_units jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint; source_release text; unit jsonb; metadata jsonb; group_snapshot jsonb; unit_id bigint; unit_snapshot jsonb; frozen_frame jsonb; source_cut bigint; membership_snapshot jsonb;
 arms jsonb:=p_sampling->'comparison_arms'; arm_name text; arm jsonb; baseline jsonb; revised jsonb;
 arm_fields text[]:=ARRAY['method','method_version','operation_question','operation_version'];
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
  OR COALESCE(p_sampling->>'source_frame_abi','') NOT IN ('source-operation-frame-1','source-operation-frame-2','source-operation-frame-3')
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
 IF arms IS NOT NULL THEN
  IF jsonb_typeof(arms) IS DISTINCT FROM 'object' OR NOT(arms ?& ARRAY['baseline','revised'])
   OR arms-ARRAY['baseline','revised']<>'{}' OR p_sampling->>'source_frame_abi'<>'source-operation-frame-2' THEN
   RAISE EXCEPTION 'comparison requires baseline and revised arms on source-first V2 frames' USING ERRCODE='23514'; END IF;
  FOREACH arm_name IN ARRAY ARRAY['baseline','revised'] LOOP
   IF jsonb_typeof(arms->arm_name) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(arms->arm_name))<>jsonb_array_length(p_units) THEN
    RAISE EXCEPTION 'each comparison arm must bind every frozen source unit' USING ERRCODE='23514'; END IF;
  END LOOP;
 END IF;
 FOR unit IN SELECT value FROM jsonb_array_elements(p_units) LOOP
  IF arms IS NOT NULL THEN
   IF unit->'frame'->'evaluation_frame'->>'direction' IS DISTINCT FROM 'source_first' THEN
    RAISE EXCEPTION 'comparison requires source-first V2 frames' USING ERRCODE='23514'; END IF;
   baseline:=arms->'baseline'->(unit->>'unit_key'); revised:=arms->'revised'->(unit->>'unit_key');
   FOREACH arm IN ARRAY ARRAY[baseline,revised] LOOP
    IF jsonb_typeof(arm) IS DISTINCT FROM 'object' OR NOT(arm ?& arm_fields)
     OR arm-(arm_fields||ARRAY['configuration_hash'])<>'{}'
     OR EXISTS(SELECT FROM jsonb_each(arm) v WHERE jsonb_typeof(v.value)<>'string' OR btrim(v.value#>>'{}')='')
     OR (arm ? 'configuration_hash' AND arm->>'configuration_hash' !~ '^(cfg:[0-9a-f]{32}|[0-9a-f]{64})$') THEN
     RAISE EXCEPTION 'comparison requires exact method, operation and registered configuration bindings' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF (baseline ? 'configuration_hash') IS DISTINCT FROM (revised ? 'configuration_hash')
    OR (baseline-'configuration_hash'=revised-'configuration_hash'
     AND baseline->>'configuration_hash' IS NOT DISTINCT FROM revised->>'configuration_hash') THEN
    RAISE EXCEPTION 'same-operation comparison arms require distinct registered configuration hashes; configuration binding must cover both arms' USING ERRCODE='23514'; END IF;
  END IF;
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
   ((frozen_frame->'evaluation_frame')-ARRAY['unit','release_id','guideline_version','pin','anchor_ids','related_pins','anchor_scopes','contribution_ids','source_group','partition','inspected_scope','opportunities','exposure_history','characterization_view','selected_layers','outputs']),frozen_frame);
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
  OR COALESCE(p_frame->>'protocol','') NOT IN ('source-operation-frame-1','source-operation-frame-2','source-operation-frame-3') OR p_frame-ARRAY['protocol','evaluation_frame','source_views','captured_coordinates','context_dependency_digest']<>'{}'
  OR jsonb_typeof(bound) IS DISTINCT FROM 'object'
  OR bound-ARRAY['unit','release_id','guideline_version','rubric_version','context_policy','pin','anchor_ids','related_pins','anchor_scopes','operation_question','operation_version','domain','direction','contribution_ids','source_group','partition','inspected_scope','opportunities','exposure_history','characterization_view','selected_layers','outputs']<>'{}'
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
  OR (bound->>'direction'='output_first' AND p_frame->>'protocol'<>'source-operation-frame-3' AND jsonb_array_length(bound->'contribution_ids')=0)
  OR EXISTS(SELECT FROM unnest(ARRAY['rubric_version','context_policy','operation_question','operation_version','domain','direction']) k
    WHERE btrim(COALESCE(bound->>k,''))='' OR p_payload->>k IS DISTINCT FROM bound->>k) THEN
  RAISE EXCEPTION 'record reference differs from frozen source/guideline/release protocol' USING ERRCODE='23514'; END IF;
 IF p_frame->>'protocol'<>'source-operation-frame-3' AND bound->>'direction'='output_first' AND EXISTS(
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
  IF bound ?| ARRAY['source_group','partition','inspected_scope','opportunities','exposure_history','characterization_view','selected_layers','outputs'] THEN
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
  IF p_frame->>'protocol'='source-operation-frame-3' THEN
   PERFORM eval.validate_characterization_reference(p_unit,p_payload,p_frame);
  ELSE
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
 END IF;
 FOR source_record IN SELECT value FROM jsonb_array_elements(p_payload->'cases') LOOP
  IF source_record-ARRAY['case_id','facet','anchor_ids','inspected_scope','source_state','judgment','alternatives','explanation',
    'assessor_provenance','contribution_kind','contribution_id','error_category','candidate_selector','permissible_anchor_sets','expectation_mode','anchor_endpoint_role','opportunity_id','output_reference','required_family','graph_projection','native_reference','semantic_reference']<>'{}'
   OR NOT(source_record ?& ARRAY['case_id','facet','anchor_ids','inspected_scope','source_state','judgment','alternatives','explanation','assessor_provenance'])
   OR EXISTS(SELECT FROM unnest(ARRAY['case_id','facet','inspected_scope','explanation']) k WHERE btrim(COALESCE(source_record->>k,''))='')
   OR COALESCE(source_record->>'judgment','') NOT IN ('supported','unsupported','ambiguous','unassessed')
   OR COALESCE(source_record->>'source_state','') NOT IN ('stated','unstated','uninspected','unresolved','inapplicable')
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
   OR (bound->>'rubric_version' IN ('nce12-attachment-role-direction-scope-1','nce12-attachment-role-direction-scope-2')
    AND source_record->>'facet'='defining_text_attachment_correctness' AND EXISTS(
     SELECT FROM jsonb_array_elements(source_record->'alternatives') a
     WHERE a-ARRAY['semantic_type','endpoint_semantics']<>'{}'
      OR a->>'semantic_type' IS DISTINCT FROM 'definition.defining_text_attachment'
      OR jsonb_typeof(a->'endpoint_semantics') IS DISTINCT FROM 'array'
      OR EXISTS(SELECT FROM jsonb_array_elements(a->'endpoint_semantics') e
       WHERE e->'fields' IS DISTINCT FROM '{}'::jsonb)))
   OR (source_record->>'source_state'='uninspected' AND source_record->>'judgment'<>'unassessed')
   OR (source_record->>'source_state'='stated' AND source_record->>'judgment'='supported' AND source_record->'alternatives'='[]' AND (p_frame->>'protocol'<>'source-operation-frame-3' OR jsonb_typeof(source_record->'native_reference') IS DISTINCT FROM 'object' AND jsonb_typeof(source_record->'semantic_reference') IS DISTINCT FROM 'object'))
   OR (source_record->'semantic_reference' IS NOT NULL AND source_record->'semantic_reference'<>'null' AND p_frame->>'protocol'<>'source-operation-frame-3')
   OR (source_record->'native_reference' IS NOT NULL AND source_record->'native_reference'<>'null' AND p_frame->>'protocol'<>'source-operation-frame-3')
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
   OR (p_frame->>'protocol'<>'source-operation-frame-3' AND bound->>'direction'='output_first' AND (source_record->>'contribution_id' IS NULL OR NOT(bound->'contribution_ids' ? (source_record->>'contribution_id')))) THEN
   RAISE EXCEPTION 'operation case differs from independent source/facet authority' USING ERRCODE='23514'; END IF;

 END LOOP;
 IF bound->>'rubric_version'='nce12-attachment-role-direction-scope-2' THEN
  IF bound->>'direction'<>'output_first'
   OR EXISTS (SELECT FROM jsonb_array_elements(p_payload->'cases') c
    CROSS JOIN LATERAL jsonb_array_elements(c->'alternatives') a
    WHERE c->>'facet' IN ('attachment_head','attachment_tail','attachment_direction','attachment_scope')
     AND (a-ARRAY['semantic_type',c->>'facet']<>'{}'
       OR a->>'semantic_type' IS DISTINCT FROM 'definition.defining_text_attachment'
       OR NOT a ? (c->>'facet')
       OR CASE c->>'facet'
         WHEN 'attachment_scope' THEN jsonb_typeof(a->'attachment_scope') IS DISTINCT FROM 'object'
           OR (a->'attachment_scope')-ARRAY['kind','term','defining_text','declared_scope','effective_version']<>'{}'
           OR a->'attachment_scope'->>'kind' IS DISTINCT FROM 'native_section_scope'
           OR jsonb_typeof(a->'attachment_scope'->'term') IS DISTINCT FROM 'array'
           OR jsonb_typeof(a->'attachment_scope'->'defining_text') IS DISTINCT FROM 'array'
           OR EXISTS(SELECT FROM jsonb_array_elements_text(
            (a->'attachment_scope'->'term')||(a->'attachment_scope'->'defining_text')) p(pointer)
            WHERE NOT EXISTS(SELECT FROM kb.pdf_record_access n
             WHERE n.product_id=selected.native_build_id AND n.revision_id=selected.native_build_id
              AND n.pointer=p.pointer AND (n.label IN ('section','chapter') OR n.pointer='#/body')))
         WHEN 'attachment_direction' THEN a->'attachment_direction' NOT IN
           ('["term","defining_text"]'::jsonb,'["defining_text","term"]'::jsonb)
         ELSE jsonb_typeof(a->(c->>'facet')) IS DISTINCT FROM 'array'
           OR NOT ((bound->'anchor_ids') @> (a->(c->>'facet')))
       END)) THEN
   RAISE EXCEPTION 'attachment rubric requires independent exact head, tail, direction and scope cases' USING ERRCODE='23514';
  END IF;
 END IF;
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
 IF p_frame->'evaluation_frame'->>'rubric_version'='nce12-attachment-role-direction-scope-2'
  AND EXISTS (SELECT FROM jsonb_array_elements_text(p_frame->'evaluation_frame'->'contribution_ids') id
   CROSS JOIN unnest(ARRAY['defining_text_attachment_correctness','attachment_head',
     'attachment_tail','attachment_direction','attachment_scope']) f(facet)
   WHERE (SELECT count(*) FROM jsonb_array_elements(payload->'cases') c
     WHERE c->>'contribution_id'=id AND c->>'facet'=f.facet
      AND c->>'contribution_kind'='relation'
      AND COALESCE(c->>'expectation_mode','structure')='structure')<>1) THEN
  RAISE EXCEPTION 'attachment authoring requires all five independent cases per emitted relation'
   USING ERRCODE='23514';
 END IF;
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
 selected kb.source_view; context jsonb; contexts jsonb:='[]'; schema jsonb; packet jsonb;
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
   ((source_frame->'evaluation_frame')-ARRAY['unit','release_id','guideline_version','pin','anchor_ids','related_pins','anchor_scopes','contribution_ids','source_group','partition','inspected_scope','opportunities','exposure_history','characterization_view','selected_layers','outputs']),source_frame);
 FOR selected IN SELECT v.* FROM jsonb_array_elements(source_frame->'source_views') frozen
  JOIN kb.source_view v ON v.id=(frozen->>'id')::bigint ORDER BY v.id LOOP
  SELECT COALESCE(jsonb_object_agg(pointer,native_json),'{}') INTO context FROM ops.read_pdf_published_items(
   selected.native_task_id,selected.native_product_key,selected.native_content_digest,ARRAY(
    SELECT value FROM jsonb_array_elements_text(selected.projection->'items')
    UNION SELECT value FROM jsonb_array_elements_text(COALESCE(selected.projection->'ancestors','[]'))));
  IF octet_length(data.canonical_json(contexts))+octet_length(data.canonical_json(context))>1048576 THEN
   RAISE EXCEPTION 'operation author source context exceeds byte bound' USING ERRCODE='54000';
  END IF;
  contexts:=contexts||jsonb_build_array(jsonb_build_object('source_view_id',selected.id,'native_items',context));
 END LOOP;
 packet:=jsonb_build_object('protocol','source-operation-author-packet-1','unit_id',p_unit,
  'unit_ref',unit.unit_key,'release_id',reference_set.release_id,'guideline',reference_set.guideline,
  'guideline_text',reference_set.sampling->'guideline_text','guideline_digest',reference_set.sampling->'guideline_digest',
  'source_frame',jsonb_set(source_frame,'{evaluation_frame}',(source_frame->'evaluation_frame')-ARRAY['contribution_ids','characterization_view','selected_layers','outputs']),'native_contexts',contexts)||
  CASE WHEN source_frame->>'protocol'='source-operation-frame-3' AND source_frame->'evaluation_frame'->>'direction'='output_first' THEN
   jsonb_build_object('output_exposure','frozen_output_first_population','selected_outputs',(
    SELECT coalesce(jsonb_agg(jsonb_build_object('reference',o,'value',n) ORDER BY selection.ordinality),'[]')
    FROM jsonb_array_elements(source_frame->'evaluation_frame'->'outputs') WITH ORDINALITY selection(o,ordinality)
    JOIN ops.characterization_product product ON product.task_id=(o->'layer'->>'task_id')::bigint
     AND product.product_key=o->'layer'->>'product_key' AND product.content_digest=o->'layer'->>'content_digest'
    CROSS JOIN LATERAL jsonb_array_elements(product.payload->(o->>'collection')) n
    WHERE n->>(CASE o->>'collection' WHEN 'coverage' THEN 'family' ELSE 'local_id' END)=o->>'local_id'))
   ELSE '{}'::jsonb END;
 IF octet_length(data.canonical_json(packet))>1048576 THEN
  RAISE EXCEPTION 'operation author packet exceeds byte bound' USING ERRCODE='54000';
 END IF;
 RETURN packet;
END $$;
REVOKE ALL ON FUNCTION eval.operation_author_packet(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_author_packet(bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.validate_operation_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference_set eval.reference_set; completed ops.completed_result; snap jsonb;
 unit eval.reference_unit; source_frame jsonb; authored jsonb;
 arms jsonb; claimed_arm jsonb:=p_result->'comparison_arm'; arm_name text; binding jsonb;
 actual_reports jsonb; claimed_reports jsonb;
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
 arms:=reference_set.sampling->'comparison_arms'; arm_name:=claimed_arm->>'name';
 IF (arms IS NOT NULL OR claimed_arm IS NOT NULL) AND (
  jsonb_typeof(claimed_arm) IS DISTINCT FROM 'object' OR COALESCE(arm_name,'') NOT IN ('baseline','revised')
  OR NOT COALESCE(arms ? arm_name,false) OR claimed_arm->'producers' IS DISTINCT FROM arms->arm_name
  OR claimed_arm->>'binding_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(arms),'UTF8')),'hex')
  OR claimed_arm->'cut_id' IS DISTINCT FROM to_jsonb(completed.cut_id)) THEN
  RAISE EXCEPTION 'operation evaluation differs from its frozen comparison arm or cut' USING ERRCODE='23514'; END IF;
 FOR snap IN SELECT value FROM jsonb_array_elements(p_snapshot) LOOP
  SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=(snap->>'unit_id')::bigint AND set_id=p_set;
  binding:=arms->arm_name->unit.unit_key;
  IF binding ? 'configuration_hash' THEN
   -- The selected origin's registered configuration owns the hash, not the submitted grade.
   SELECT jsonb_agg(jsonb_build_array(task.id,origin.id,cfg.config_hash) ORDER BY task.id) INTO actual_reports
   FROM ops.cut_task member JOIN ops.task task ON task.id=member.task_id AND task.run_id=p_run
   JOIN ops.task origin ON origin.id=member.origin_task_id AND origin.id=COALESCE(task.reused_task_id,task.id)
   JOIN ops.method_config cfg ON cfg.id=origin.method_config_id JOIN ops.method method ON method.id=cfg.method_id
   JOIN ops.task_result report ON report.task_id=origin.id
   WHERE member.cut_id=completed.cut_id AND task.unit_type='source_view' AND task.unit_id=unit.source_view_id
    AND task.release_id=completed.release_id AND origin.release_id=completed.release_id
    AND method.name=binding->>'method' AND method.version=binding->>'method_version'
    AND EXISTS(SELECT FROM kb.source_contribution_operation operation WHERE operation.task_id=origin.id
     AND operation.release_id=completed.release_id AND operation.question=binding->>'operation_question'
     AND operation.operation_version=binding->>'operation_version');
   SELECT jsonb_agg(jsonb_build_array(report->'selected_task_id',report->'origin_task_id',report->'configuration_hash')
     ORDER BY (report->>'selected_task_id')::bigint) INTO claimed_reports
   FROM jsonb_array_elements(p_result->'units') assessed
   CROSS JOIN LATERAL jsonb_array_elements(assessed->'producer_reports') report
   WHERE assessed->'unit_id'=to_jsonb(unit.id);
   IF actual_reports IS NULL OR actual_reports IS DISTINCT FROM claimed_reports OR EXISTS(
    SELECT FROM jsonb_array_elements(actual_reports) report WHERE report->>2 IS DISTINCT FROM binding->>'configuration_hash') THEN
    RAISE EXCEPTION 'completed operation reports do not match the frozen arm configuration' USING ERRCODE='23514'; END IF;
  END IF;
  SELECT f.source_frame,convert_from(p.authored,'UTF8')::jsonb INTO STRICT source_frame,authored
   FROM eval.reference_pass p JOIN eval.reference_frame f ON f.pass_id=p.id
   WHERE p.id=(snap->>'pass_id')::bigint AND f.id=(snap->>'frame_id')::bigint
    AND p.unit_id=unit.id AND p.pass_kind='C' AND p.content_digest=snap->>'content_digest';
  PERFORM eval.validate_operation_reference_frame(unit.id,authored,source_frame);
  IF source_frame->>'protocol'='source-operation-frame-3' THEN
   PERFORM eval.validate_characterization_assessment_target(p_project,p_run,source_frame->'evaluation_frame',
    (SELECT assessed FROM jsonb_array_elements(p_result->'units') assessed WHERE (assessed->>'unit_id')::bigint=unit.id));
  END IF;
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

-- V3 shares reference custody; typed layer populations replace contribution membership.
CREATE OR REPLACE FUNCTION eval.validate_characterization_assessment_target(p_project text,p_run bigint,p_bound jsonb,p_assessed jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ref jsonb; view_ jsonb; layer_ jsonb; selected jsonb; output_ jsonb; collection_ text;
BEGIN
 ref:=p_assessed->'characterization_view';
 IF jsonb_typeof(ref) IS DISTINCT FROM 'object' OR ref-ARRAY['task_id','product_key','content_digest']<>'{}'
  OR NOT(ref ?& ARRAY['task_id','product_key','content_digest'])
  OR jsonb_typeof(ref->'task_id') IS DISTINCT FROM 'number' OR coalesce(ref->>'task_id','') !~ '^[1-9][0-9]*$'
  OR jsonb_typeof(ref->'product_key') IS DISTINCT FROM 'string' OR btrim(coalesce(ref->>'product_key',''))=''
  OR coalesce(ref->>'content_digest','') !~ '^[a-f0-9]{64}$' THEN
  RAISE EXCEPTION 'characterization assessment requires an exact view pin' USING ERRCODE='23514'; END IF;
 view_:=ops.read_characterization_product((ref->>'task_id')::bigint,ref->>'product_key',ref->>'content_digest','view',p_run,67108864);
 IF NOT EXISTS(SELECT FROM ops.run WHERE id=p_run AND project_id=p_project)
  OR EXISTS(SELECT FROM jsonb_array_elements(p_bound->'opportunities') o CROSS JOIN LATERAL jsonb_array_elements(o->'extents') e
   WHERE NOT(view_->'source_scope'->'source_view_ids' @> jsonb_build_array(e->'source_view_id')))
  OR (p_bound->>'direction'='output_first' AND ref IS DISTINCT FROM p_bound->'characterization_view')
  OR jsonb_typeof(p_assessed->'selected_layers') IS DISTINCT FROM 'array'
  OR jsonb_array_length(p_assessed->'selected_layers')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(p_assessed->'selected_layers'))
  OR (p_bound->>'direction'='output_first' AND p_assessed->'selected_layers' IS DISTINCT FROM p_bound->'selected_layers')
  OR EXISTS(SELECT FROM jsonb_array_elements(p_assessed->'selected_layers') l
   WHERE NOT(coalesce(view_->'active_layers',view_->'layers') @> jsonb_build_array(l))) THEN
  RAISE EXCEPTION 'characterization assessment changes source or active population' USING ERRCODE='23514'; END IF;
 FOR selected IN SELECT value FROM jsonb_array_elements(p_assessed->'selected_layers') LOOP
  layer_:=ops.read_characterization_product((selected->>'task_id')::bigint,selected->>'product_key',selected->>'content_digest','layer',p_run);
  IF layer_->'base_document' IS DISTINCT FROM view_->'base_document' THEN
   RAISE EXCEPTION 'characterization layer has wrong source document' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF p_bound->>'direction'='output_first' THEN
  IF jsonb_typeof(p_bound->'outputs') IS DISTINCT FROM 'array'
   OR jsonb_array_length(p_bound->'outputs')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(p_bound->'outputs')) THEN
   RAISE EXCEPTION 'output population is missing or duplicated' USING ERRCODE='23514'; END IF;
  FOR output_ IN SELECT value FROM jsonb_array_elements(p_bound->'outputs') LOOP
   collection_:=output_->>'collection'; selected:=output_->'layer';
   IF output_-ARRAY['layer','collection','local_id']<>'{}' OR NOT(output_ ?& ARRAY['layer','collection','local_id'])
    OR coalesce(collection_,'') NOT IN ('occurrences','annotations','memberships','roles','terms','choices','coverage')
    OR jsonb_typeof(output_->'collection') IS DISTINCT FROM 'string' OR jsonb_typeof(output_->'local_id') IS DISTINCT FROM 'string' OR btrim(coalesce(output_->>'local_id',''))='' OR NOT(p_bound->'selected_layers' @> jsonb_build_array(selected)) THEN
    RAISE EXCEPTION 'invalid typed characterization output identity' USING ERRCODE='23514'; END IF;
   layer_:=ops.read_characterization_product((selected->>'task_id')::bigint,selected->>'product_key',selected->>'content_digest','layer',p_run);
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(layer_->collection_) n
    WHERE n->>(CASE collection_ WHEN 'coverage' THEN 'family' ELSE 'local_id' END)=output_->>'local_id') THEN
    RAISE EXCEPTION 'frozen characterization output is absent' USING ERRCODE='23514'; END IF;
  END LOOP;
 END IF;
END $$;
REVOKE ALL ON FUNCTION eval.validate_characterization_assessment_target(text,bigint,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.validate_characterization_reference(p_unit bigint,p_payload jsonb,p_frame jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE bound jsonb:=p_frame->'evaluation_frame'; opportunity jsonb; extent_ jsonb; source_ kb.source_view;
 case_ jsonb; native_layer jsonb; native_block jsonb; native_extents jsonb; unit_ eval.reference_unit; set_ eval.reference_set;
BEGIN
 SELECT * INTO STRICT unit_ FROM eval.reference_unit WHERE id=p_unit;
 SELECT * INTO STRICT set_ FROM eval.reference_set WHERE id=unit_.set_id;
 IF bound->'contribution_ids'<>'[]' OR jsonb_typeof(bound->'selected_layers') IS DISTINCT FROM 'array'
  OR (bound->>'direction'='source_first' AND (bound->'characterization_view' IS DISTINCT FROM 'null'::jsonb OR bound->'selected_layers'<>'[]' OR bound->'outputs' IS DISTINCT FROM 'null'::jsonb))
  OR (bound->>'direction'='output_first' AND (jsonb_typeof(bound->'characterization_view') IS DISTINCT FROM 'object' OR jsonb_array_length(bound->'selected_layers')=0 OR jsonb_typeof(bound->'outputs') IS DISTINCT FROM 'array')) THEN
  RAISE EXCEPTION 'characterization frame confuses source and output authority' USING ERRCODE='23514'; END IF;
 FOR opportunity IN SELECT value FROM jsonb_array_elements(bound->'opportunities') LOOP
  IF opportunity-ARRAY['opportunity_id','extents','facet','source_state']<>'{}'
   OR btrim(coalesce(opportunity->>'opportunity_id',''))='' OR btrim(coalesce(opportunity->>'facet',''))=''
   OR coalesce(opportunity->>'source_state','') NOT IN ('stated','unstated','inapplicable','unresolved','uninspected')
   OR jsonb_typeof(opportunity->'extents') IS DISTINCT FROM 'array' OR jsonb_array_length(opportunity->'extents')=0 THEN
   RAISE EXCEPTION 'invalid independent characterization opportunity' USING ERRCODE='23514'; END IF;
  FOR extent_ IN SELECT value FROM jsonb_array_elements(opportunity->'extents') LOOP
   IF extent_-ARRAY['source_view_id','projection','native_pointer','start','end']<>'{}'
    OR NOT(extent_ ?& ARRAY['source_view_id','projection','native_pointer','start','end'])
    OR jsonb_typeof(extent_->'source_view_id') IS DISTINCT FROM 'number' OR jsonb_typeof(extent_->'start') IS DISTINCT FROM 'number' OR jsonb_typeof(extent_->'end') IS DISTINCT FROM 'number'
    OR coalesce(extent_->>'source_view_id','') !~ '^[1-9][0-9]*$'
    OR coalesce(extent_->>'start','') !~ '^[0-9]+$' OR coalesce(extent_->>'end','') !~ '^[0-9]+$'
    OR (extent_->>'start')::bigint >= (extent_->>'end')::bigint THEN
    RAISE EXCEPTION 'invalid ordered characterization extent' USING ERRCODE='23514'; END IF;
   SELECT v.* INTO STRICT source_ FROM kb.source_view v JOIN jsonb_array_elements(p_frame->'source_views') f ON (f->>'id')::bigint=v.id
    WHERE v.id=(extent_->>'source_view_id')::bigint;
   IF extent_->>'projection' IS DISTINCT FROM source_.projection_digest
    OR (extent_->>'end')::bigint > length(source_.projection->>'text')
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(source_.projection->'pieces') piece
     WHERE piece->>'kind'='native_text' AND piece->>'item_ref'=extent_->>'native_pointer' AND (piece->>'start')::bigint <= (extent_->>'start')::bigint
      AND (extent_->>'end')::bigint <= (piece->>'end')::bigint AND NOT coalesce((piece->>'synthetic')::boolean,false)) THEN
    RAISE EXCEPTION 'characterization extent is outside its frozen source pin' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 IF bound->>'direction'='output_first' THEN
  PERFORM eval.validate_characterization_assessment_target(set_.project_id,set_.source_run_id,bound,bound);
 END IF;
 FOR case_ IN SELECT value FROM jsonb_array_elements(p_payload->'cases') LOOP
  IF case_->'native_reference' IS NOT NULL AND case_->'native_reference'<>'null' THEN
   PERFORM eval.validate_native_scoring_reference(case_->'native_reference');
   SELECT o INTO opportunity FROM jsonb_array_elements(bound->'opportunities') o WHERE o->>'opportunity_id'=case_->>'opportunity_id';
   IF opportunity IS NULL OR (SELECT count(DISTINCT e->'source_view_id') FROM jsonb_array_elements(opportunity->'extents') e)<>1
    OR EXISTS(SELECT FROM (SELECT (e->>'start')::bigint AS first_,lag((e->>'end')::bigint) OVER(ORDER BY n) AS prior_end
      FROM jsonb_array_elements(opportunity->'extents') WITH ORDINALITY ext(e,n)) ordered WHERE first_<prior_end) THEN
    RAISE EXCEPTION 'native reference requires one exact ordered projection block' USING ERRCODE='23514'; END IF;
   SELECT * INTO STRICT source_ FROM kb.source_view WHERE id=(opportunity->'extents'->0->>'source_view_id')::bigint;
   IF case_->'native_reference'->>'text' IS DISTINCT FROM substring(source_.projection->>'text'
    FROM (opportunity->'extents'->0->>'start')::integer+1
    FOR (opportunity->'extents'->-1->>'end')::integer-(opportunity->'extents'->0->>'start')::integer) THEN
    RAISE EXCEPTION 'native reference text differs from its exact frozen source' USING ERRCODE='23514'; END IF;
   IF bound->>'direction'='output_first' THEN
    IF NOT coalesce(bound->'outputs' @> jsonb_build_array(case_->'output_reference'),false) THEN
     RAISE EXCEPTION 'native task output is outside its frozen population' USING ERRCODE='23514'; END IF;
    SELECT payload INTO native_layer FROM ops.characterization_product
     WHERE task_id=(case_->'output_reference'->'layer'->>'task_id')::bigint
      AND product_key=case_->'output_reference'->'layer'->>'product_key'
      AND content_digest=case_->'output_reference'->'layer'->>'content_digest' AND kind='layer';
    SELECT a INTO native_block FROM jsonb_array_elements(native_layer->'annotations') a
     WHERE a->>'local_id'=case_->'output_reference'->>'local_id' AND a->>'kind'='native.block';
    SELECT jsonb_agg(e.body-ARRAY['text','page','synthetic'] ORDER BY ref.n,e.n) INTO native_extents
     FROM jsonb_array_elements(native_block->'occurrences') WITH ORDINALITY ref(id,n)
     JOIN jsonb_array_elements(native_layer->'occurrences') o ON o->>'local_id'=ref.id#>>'{}'
     CROSS JOIN LATERAL jsonb_array_elements(o->'extents') WITH ORDINALITY e(body,n)
     WHERE NOT coalesce((e.body->>'synthetic')::boolean,false);
    IF case_->'output_reference'->>'collection' IS DISTINCT FROM 'annotations' OR native_block IS NULL
     OR native_extents IS DISTINCT FROM opportunity->'extents' THEN
     RAISE EXCEPTION 'native output reference must name its exact frozen native block' USING ERRCODE='23514'; END IF;
   END IF;
   IF case_->'alternatives'<>'[]' OR case_->>'graph_projection' IS NOT NULL
    OR coalesce(case_->'candidate_selector','{}')<>'{}' OR coalesce(case_->>'expectation_mode','structure')<>'structure'
    OR coalesce(case_->>'required_family','') NOT LIKE 'spacy.%' THEN
    RAISE EXCEPTION 'native task references cannot be graph alternatives or another scheme' USING ERRCODE='23514'; END IF;
  END IF;
  IF case_->'semantic_reference' IS NOT NULL AND case_->'semantic_reference'<>'null' THEN
   SELECT o INTO opportunity FROM jsonb_array_elements(bound->'opportunities') o WHERE o->>'opportunity_id'=case_->>'opportunity_id';
   PERFORM eval.validate_semantic_task_reference(case_->'semantic_reference',p_frame,opportunity);
   IF case_->'alternatives'<>'[]' OR case_->>'graph_projection' IS NOT NULL
    OR coalesce(case_->'native_reference','null')<>'null' OR coalesce(case_->'candidate_selector','{}')<>'{}'
    OR coalesce(case_->>'expectation_mode','structure')<>'structure' THEN
    RAISE EXCEPTION 'semantic task reference cannot mix graph/native/candidate expectations' USING ERRCODE='23514'; END IF;
  END IF;
  IF (case_->>'graph_projection' IS NOT NULL AND case_->>'graph_projection' NOT IN ('source_semantics','native_fidelity','retained_identity'))
   OR (EXISTS(SELECT FROM jsonb_array_elements(case_->'alternatives') a WHERE a ? 'graph') AND case_->>'graph_projection' IS NULL)
   OR btrim(coalesce(case_->>'required_family',''))='' OR jsonb_typeof(case_->'required_family') IS DISTINCT FROM 'string'
   OR case_->>'contribution_id' IS NOT NULL OR case_->>'anchor_endpoint_role' IS NOT NULL
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(bound->'opportunities') o WHERE o->>'opportunity_id'=case_->>'opportunity_id' AND o->>'facet'=case_->>'facet' AND (o->>'source_state'='uninspected' OR o->>'source_state'=case_->>'source_state'))
   OR (bound->>'direction'='source_first' AND coalesce(case_->'output_reference','null'::jsonb) IS DISTINCT FROM 'null'::jsonb)
   OR (bound->>'direction'='output_first' AND NOT(bound->'outputs' @> jsonb_build_array(case_->'output_reference'))) THEN
   RAISE EXCEPTION 'case changes frozen characterization scope or output identity' USING ERRCODE='23514'; END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION eval.validate_characterization_reference(bigint,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.operation_evaluation_page(p_project text,p_evaluation bigint,p_view text,p_facet text DEFAULT NULL,p_direction text DEFAULT NULL,p_cursor text DEFAULT NULL,p_limit bigint DEFAULT 100,p_max_bytes bigint DEFAULT 1048576)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected eval.reference_evaluation; selection text; position_ bigint:=0; current_ bigint:=0;
 row_ jsonb; items jsonb:='[]'; report jsonb; more_ boolean:=false; next_ text;
BEGIN
 PERFORM data.require_runtime_principal('evaluate');
 IF p_view IS NULL OR p_view NOT IN ('summary','coverage','cases','errors') OR (p_direction IS NOT NULL AND p_direction NOT IN ('source_first','output_first'))
  OR p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 1000 OR p_max_bytes IS NULL OR p_max_bytes NOT BETWEEN 1024 AND 8388608 THEN
  RAISE EXCEPTION 'invalid bounded assessment selection' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT selected FROM eval.reference_evaluation WHERE id=p_evaluation AND project_id=p_project;
 IF selected.result->>'protocol' IS DISTINCT FROM 'source-operation-evaluation-1' THEN
  RAISE EXCEPTION 'unknown operation evaluation' USING ERRCODE='23514'; END IF;
 selection:=encode(sha256(convert_to(data.canonical_json(jsonb_build_array(p_project,p_evaluation,selected.content_digest,p_view,p_facet,p_direction)),'UTF8')),'hex');
 IF p_cursor IS NOT NULL THEN
  IF split_part(p_cursor,':',1)<>selection OR split_part(p_cursor,':',2) !~ '^[0-9]+$' OR split_part(p_cursor,':',3)<>'' THEN
   RAISE EXCEPTION 'assessment cursor belongs to another selection' USING ERRCODE='23514'; END IF;
  position_:=split_part(p_cursor,':',2)::bigint;
 END IF;
 IF p_view='summary' THEN
  report:=jsonb_build_object('evaluation_id',p_evaluation,'run_id',selected.run_id,'set_id',selected.set_id,
   'release_id',selected.result->'release_id','partition',selected.result->'partition','population_claim',selected.result->'population_claim',
   'unit_count',jsonb_array_length(selected.result->'units'),'reference_snapshot_count',jsonb_array_length(selected.reference_snapshot),
   'quality_claim',selected.result->'quality_claim','next_cursor',NULL);
  IF octet_length(data.canonical_json(report))>p_max_bytes THEN RAISE EXCEPTION 'summary exceeds byte bound' USING ERRCODE='54000'; END IF;
  RETURN report;
 END IF;
 FOR row_ IN
  SELECT jsonb_build_object('unit_id',u.value->'unit_id','source_view_id',u.value->'source_view_id','direction',u.value->'direction','item',v.value)
  FROM jsonb_array_elements(selected.result->'units') WITH ORDINALITY u(value,n)
  CROSS JOIN LATERAL jsonb_array_elements(CASE p_view WHEN 'coverage' THEN coalesce(u.value->'source_coverage'->'opportunities','[]') ELSE coalesce(u.value->'cases','[]') END) WITH ORDINALITY v(value,n)
  WHERE (p_direction IS NULL OR u.value->>'direction'=p_direction)
   AND (p_facet IS NULL OR v.value->>'facet'=p_facet)
   AND (p_view<>'errors' OR v.value->>'judgment'<>'supported') ORDER BY u.n,v.n
 LOOP
  current_:=current_+1;
  IF current_<=position_ THEN CONTINUE; END IF;
  IF jsonb_array_length(items)>=p_limit OR octet_length(data.canonical_json(jsonb_build_object('evaluation_id',p_evaluation,'view',p_view,'facet',p_facet,'direction',p_direction,'items',items||jsonb_build_array(row_),'next_cursor',selection||':'||current_::text)))>p_max_bytes THEN
   IF items='[]' THEN RAISE EXCEPTION 'assessment item exceeds byte bound' USING ERRCODE='54000'; END IF;
   more_:=true; EXIT;
  END IF;
  items:=items||jsonb_build_array(row_);
 END LOOP;
 next_:=CASE WHEN more_ THEN selection||':'||(position_+jsonb_array_length(items))::text ELSE NULL END;
 report:=jsonb_build_object('evaluation_id',p_evaluation,'view',p_view,'facet',p_facet,'direction',p_direction,'items',items,'next_cursor',next_);
 IF octet_length(data.canonical_json(report))>p_max_bytes THEN RAISE EXCEPTION 'assessment page exceeds byte bound' USING ERRCODE='54000'; END IF;
 RETURN report;
END $$;
REVOKE ALL ON FUNCTION eval.operation_evaluation_page(text,bigint,text,text,text,text,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_evaluation_page(text,bigint,text,text,text,text,bigint,bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.validate_native_scoring_reference(p_reference jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE kind_ text; count_ bigint; text_ text; span_ jsonb; index_ integer; key_ text;
BEGIN
 IF jsonb_typeof(p_reference) IS DISTINCT FROM 'object'
  OR p_reference-ARRAY['version','kind','scheme','text','words','spaces','inspected','span_key','spans','labeled','allow_overlap','labels','cats','multi_label','threshold','positive_label','heads','deps']<>'{}'
  OR NOT(p_reference ?& ARRAY['version','kind','scheme','text','words','spaces'])
  OR p_reference->>'version' IS DISTINCT FROM 'spacy-native-reference-v1'
  OR p_reference->>'scheme' IS DISTINCT FROM 'spacy'
  OR coalesce(p_reference->>'kind','') NOT IN ('tokenization','spans','categories','dependencies')
  OR jsonb_typeof(p_reference->'text') IS DISTINCT FROM 'string'
  OR jsonb_typeof(p_reference->'words') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_reference->'spaces') IS DISTINCT FROM 'array'
  OR EXISTS(SELECT FROM jsonb_array_elements(p_reference->'words') w WHERE jsonb_typeof(w)<>'string' OR w='""')
  OR EXISTS(SELECT FROM jsonb_array_elements(p_reference->'spaces') s WHERE jsonb_typeof(s)<>'boolean')
  OR jsonb_array_length(p_reference->'words')<>jsonb_array_length(p_reference->'spaces')
  OR EXISTS(SELECT FROM unnest(ARRAY['inspected','labeled','allow_overlap']) flag WHERE p_reference ? flag AND jsonb_typeof(p_reference->flag)<>'boolean')
  OR (p_reference ? 'multi_label' AND p_reference->'multi_label'<>'null' AND jsonb_typeof(p_reference->'multi_label')<>'boolean') THEN
  RAISE EXCEPTION 'invalid closed native scoring reference' USING ERRCODE='23514'; END IF;
 kind_:=p_reference->>'kind'; count_:=jsonb_array_length(p_reference->'words');
 SELECT coalesce(string_agg((w.value#>>'{}')||CASE WHEN p_reference->'spaces'->(w.n-1)::integer='true'::jsonb THEN ' ' ELSE '' END,'' ORDER BY w.n),'') INTO text_
 FROM jsonb_array_elements(p_reference->'words') WITH ORDINALITY w(value,n);
 IF text_ IS DISTINCT FROM p_reference->>'text' THEN
  RAISE EXCEPTION 'native reference segmentation differs from exact text' USING ERRCODE='23514'; END IF;
 FOREACH key_ IN ARRAY ARRAY['spans','labels','heads','deps'] LOOP
  IF p_reference ? key_ AND jsonb_typeof(p_reference->key_) IS DISTINCT FROM 'array' THEN
   RAISE EXCEPTION 'native task field requires an array' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (kind_<>'spans' AND (coalesce(p_reference->'spans','[]')<>'[]' OR p_reference->>'span_key' IS NOT NULL))
  OR (kind_<>'dependencies' AND (coalesce(p_reference->'heads','[]')<>'[]' OR coalesce(p_reference->'deps','[]')<>'[]'))
  OR (kind_<>'categories' AND (coalesce(p_reference->'labels','[]')<>'[]' OR coalesce(p_reference->'cats','{}')<>'{}'
    OR p_reference->>'multi_label' IS NOT NULL OR p_reference->>'threshold' IS NOT NULL OR p_reference->>'positive_label' IS NOT NULL)) THEN
  RAISE EXCEPTION 'native fields differ from declared task' USING ERRCODE='23514'; END IF;
 IF kind_='spans' THEN
  IF jsonb_typeof(p_reference->'span_key') IS DISTINCT FROM 'string' OR btrim(coalesce(p_reference->>'span_key',''))=''
   OR (p_reference->>'span_key'='ents' AND coalesce((p_reference->>'allow_overlap')::boolean,false)) THEN
   RAISE EXCEPTION 'native spans require a compatible named population' USING ERRCODE='23514'; END IF;
  FOR span_ IN SELECT value FROM jsonb_array_elements(coalesce(p_reference->'spans','[]')) LOOP
   IF jsonb_typeof(span_) IS DISTINCT FROM 'object' OR span_-ARRAY['start','end','label','state']<>'{}'
    OR NOT(span_ ?& ARRAY['start','end']) OR jsonb_typeof(span_->'start') IS DISTINCT FROM 'number' OR jsonb_typeof(span_->'end') IS DISTINCT FROM 'number'
    OR coalesce(span_->>'start','') !~ '^[0-9]+$' OR coalesce(span_->>'end','') !~ '^[0-9]+$'
    OR (span_->>'start')::bigint >= (span_->>'end')::bigint OR (span_->>'end')::bigint>char_length(text_)
    OR (span_ ? 'label' AND jsonb_typeof(span_->'label')<>'string')
    OR (span_ ? 'state' AND jsonb_typeof(span_->'state') IS DISTINCT FROM 'string')
    OR coalesce(span_->>'state','inspected') NOT IN ('inspected','uninspected')
    OR (coalesce((p_reference->>'labeled')::boolean,true) AND coalesce(span_->>'state','inspected')='inspected' AND coalesce(span_->>'label','')='') THEN
    RAISE EXCEPTION 'native reference span has invalid source coordinates or label' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(p_reference->'spans','[]')) s GROUP BY s->'start',s->'end',coalesce(s->>'label','') HAVING count(*)>1)
   OR (NOT coalesce((p_reference->>'allow_overlap')::boolean,false) AND EXISTS(
    SELECT FROM jsonb_array_elements(coalesce(p_reference->'spans','[]')) WITH ORDINALITY a(s,n)
    JOIN jsonb_array_elements(coalesce(p_reference->'spans','[]')) WITH ORDINALITY b(s,n) ON a.n<b.n
    WHERE coalesce(a.s->>'state','inspected')='inspected' AND coalesce(b.s->>'state','inspected')='inspected'
     AND (a.s->>'start')::bigint<(b.s->>'end')::bigint AND (b.s->>'start')::bigint<(a.s->>'end')::bigint)) THEN
   RAISE EXCEPTION 'native reference span duplicates or violates overlap policy' USING ERRCODE='23514'; END IF;
 ELSIF kind_='categories' THEN
  IF jsonb_typeof(p_reference->'labels') IS DISTINCT FROM 'array' OR jsonb_array_length(p_reference->'labels')=0
   OR EXISTS(SELECT FROM jsonb_array_elements(p_reference->'labels') l WHERE jsonb_typeof(l)<>'string' OR l='""')
   OR jsonb_array_length(p_reference->'labels')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(p_reference->'labels'))
   OR jsonb_typeof(coalesce(p_reference->'cats','{}')) IS DISTINCT FROM 'object'
   OR jsonb_typeof(p_reference->'multi_label') IS DISTINCT FROM 'boolean'
   OR EXISTS(SELECT FROM jsonb_each(coalesce(p_reference->'cats','{}')) c WHERE NOT(p_reference->'labels' ? c.key)
    OR (c.value<>'null' AND (jsonb_typeof(c.value)<>'number' OR c.value NOT IN ('0'::jsonb,'1'::jsonb))))
   OR (p_reference->'multi_label'='true' AND (jsonb_typeof(p_reference->'threshold') IS DISTINCT FROM 'number'
     OR NOT ((p_reference->>'threshold')::numeric BETWEEN 0 AND 1)))
   OR (p_reference->'multi_label'='false' AND p_reference->>'threshold' IS NOT NULL AND p_reference->'threshold'<>'0')
   OR (p_reference->>'positive_label' IS NOT NULL AND (jsonb_typeof(p_reference->'positive_label')<>'string' OR p_reference->'multi_label'<>'false' OR jsonb_array_length(p_reference->'labels')<>2 OR NOT(p_reference->'labels' ? (p_reference->>'positive_label')))) THEN
   RAISE EXCEPTION 'native category reference violates declared label/masking policy' USING ERRCODE='23514'; END IF;
 ELSIF kind_='dependencies' THEN
  IF jsonb_typeof(p_reference->'heads') IS DISTINCT FROM 'array' OR jsonb_typeof(p_reference->'deps') IS DISTINCT FROM 'array'
   OR jsonb_array_length(p_reference->'heads')<>count_ OR jsonb_array_length(p_reference->'deps')<>count_ THEN
   RAISE EXCEPTION 'native dependency reference requires parallel heads and labels' USING ERRCODE='23514'; END IF;
  FOR index_ IN 0..count_::integer-1 LOOP
   IF (p_reference->'heads'->index_='null') IS DISTINCT FROM (p_reference->'deps'->index_='null')
    OR (p_reference->'heads'->index_<>'null' AND (jsonb_typeof(p_reference->'heads'->index_)<>'number'
      OR (p_reference->'heads'->>index_) !~ '^[0-9]+$' OR (p_reference->'heads'->>index_)::bigint>=count_
      OR jsonb_typeof(p_reference->'deps'->index_)<>'string' OR p_reference->'deps'->>index_='')) THEN
    RAISE EXCEPTION 'native dependency reference has invalid head, label or missing pair' USING ERRCODE='23514'; END IF;
  END LOOP;
 END IF;
END $$;
REVOKE ALL ON FUNCTION eval.validate_native_scoring_reference(jsonb) FROM PUBLIC;
