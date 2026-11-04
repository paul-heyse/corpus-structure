-- Independent record readings extend the existing evaluator/pass/grade store.
-- These functions never grant production acceptance or receive producer candidates.
CREATE OR REPLACE FUNCTION eval.assign_record_reference_origin(p_project text,p_group text,p_partition text,p_uris jsonb,p_provenance jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE existing record; uri text;
BEGIN
 IF p_group IS NULL OR btrim(p_group)='' OR p_partition NOT IN
  ('development','feature_fit','final_event_calibration','final_assessment') OR p_partition IS NULL
  OR jsonb_typeof(p_uris) IS DISTINCT FROM 'array' OR jsonb_array_length(p_uris)=0
  OR jsonb_typeof(p_provenance) IS DISTINCT FROM 'object' OR p_provenance='{}' THEN
  RAISE EXCEPTION 'explicit credible origins, partition and provenance are required' USING ERRCODE='23514'; END IF;
 -- One project lock serializes both absent groups and previously unseen copy URIs. It is
 -- held only for this bounded declaration transaction, not labeling or model execution.
 PERFORM 1 FROM data.project WHERE project_id=p_project FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown origin project' USING ERRCODE='23514'; END IF;
 SELECT * INTO existing FROM eval.reference_origin_group WHERE project_id=p_project AND origin_group=p_group;
 IF FOUND THEN
  IF existing.partition IS DISTINCT FROM p_partition OR existing.provenance IS DISTINCT FROM p_provenance THEN
   RAISE EXCEPTION 'immutable source-origin assignment differs' USING ERRCODE='23514'; END IF;
 ELSE
  INSERT INTO eval.reference_origin_group(project_id,origin_group,partition,provenance)
  VALUES(p_project,p_group,p_partition,p_provenance);
 END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_uris) value WHERE jsonb_typeof(value)<>'string' OR btrim(value#>>'{}')='')
  OR jsonb_array_length(p_uris)<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(p_uris) value) THEN
  RAISE EXCEPTION 'origin membership requires unique explicit source URIs' USING ERRCODE='23514'; END IF;
 FOR uri IN SELECT value FROM jsonb_array_elements_text(p_uris) LOOP
  IF EXISTS(SELECT FROM kb.document d JOIN kb.document copy ON copy.project_id=d.project_id AND copy.content_hash=d.content_hash
   JOIN eval.reference_origin_source member ON member.project_id=copy.project_id AND member.source_uri=copy.source_uri
   WHERE d.project_id=p_project AND d.source_uri=uri AND member.origin_group<>p_group) THEN
   RAISE EXCEPTION 'known byte-identical source copies require one credible origin group' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM eval.reference_origin_source WHERE project_id=p_project AND source_uri=uri AND origin_group<>p_group) THEN
   RAISE EXCEPTION 'copies and common origins cannot cross partition groups' USING ERRCODE='23514'; END IF;
  INSERT INTO eval.reference_origin_source(project_id,source_uri,origin_group)
  VALUES(p_project,uri,p_group) ON CONFLICT(project_id,source_uri) DO NOTHING;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION eval.assign_record_reference_origin(text,text,text,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.assign_record_reference_origin(text,text,text,jsonb,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_reference_source_binding(p_run bigint,p_view bigint,p_cut bigint DEFAULT NULL)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected kb.source_view; aliases text[]; source_cut bigint;
BEGIN
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=p_view;
 source_cut:=COALESCE(p_cut,(SELECT cut_id FROM ops.completed_result WHERE run_id=p_run));
 IF NOT EXISTS(SELECT FROM ops.input_cut c JOIN ops.run_source_view v ON v.run_id=c.run_id
  WHERE c.id=source_cut AND c.run_id=p_run AND v.source_view_id=p_view) THEN
  RAISE EXCEPTION 'record logical source is outside completed selected views' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM ops.input_cut c JOIN ops.cut_task ct ON ct.cut_id=c.id
  JOIN ops.task t ON t.id=ct.origin_task_id LEFT JOIN ops.task_result r ON r.task_id=t.id AND r.release_id=t.release_id
  WHERE c.id=source_cut AND c.run_id=p_run AND t.unit_type='source_view' AND t.unit_id=p_view
   AND r.body ? 'source' AND r.body->>'source' NOT IN (t.unit_key,selected.key)) THEN
  RAISE EXCEPTION 'source report metadata has an unauthenticated logical alias' USING ERRCODE='23514'; END IF;
 SELECT array_agg(DISTINCT COALESCE(NULLIF(r.body->>'source',''),t.unit_key)) INTO aliases
 FROM ops.input_cut c JOIN ops.cut_task ct ON ct.cut_id=c.id
 JOIN ops.task t ON t.id=ct.origin_task_id LEFT JOIN ops.task_result r ON r.task_id=t.id AND r.release_id=t.release_id
 WHERE c.id=source_cut AND c.run_id=p_run AND t.unit_type='source_view' AND t.unit_id=p_view;
 IF COALESCE(cardinality(aliases),0)>1 THEN
  RAISE EXCEPTION 'source cut contains ambiguous logical source aliases' USING ERRCODE='23514'; END IF;
 RETURN COALESCE(aliases[1],selected.key);
END $$;
REVOKE ALL ON FUNCTION eval.record_reference_source_binding(bigint,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_reference_source_binding(bigint,bigint,bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.create_source_record_reference_set(p_project text,p_run bigint,p_label text,p_split text,p_guideline text,p_sampling jsonb,p_units jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint; source_release text; unit jsonb; metadata jsonb; group_snapshot jsonb; unit_id bigint; unit_snapshot jsonb; frozen_frame jsonb; source_cut bigint; membership_snapshot jsonb;
BEGIN
 SELECT release_id INTO STRICT source_release FROM ops.run WHERE id=p_run AND project_id=p_project FOR UPDATE;
 source_cut:=COALESCE((p_sampling->>'source_cut_id')::bigint,(SELECT cut_id FROM ops.completed_result WHERE run_id=p_run));
 IF NOT EXISTS(SELECT FROM ops.input_cut WHERE id=source_cut AND run_id=p_run AND release_id=source_release) THEN
  RAISE EXCEPTION 'record references require an explicitly sealed source-ready cut or completed source cut' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_execution_operation(source_release,'reference_record_set');
 IF p_split NOT IN ('dev','test') OR p_split IS NULL OR p_guideline IS NULL OR btrim(p_guideline)=''
  OR jsonb_typeof(p_units) IS DISTINCT FROM 'array' OR jsonb_array_length(p_units)=0
  OR jsonb_typeof(p_sampling) IS DISTINCT FROM 'object'
  OR p_sampling->>'record_protocol' IS DISTINCT FROM 'source-record-reference-1'
  OR p_sampling->>'source_frame_abi' IS DISTINCT FROM 'source-record-frame-1'
  OR p_sampling->>'partition' NOT IN ('development','feature_fit','final_event_calibration','final_assessment')
  OR btrim(COALESCE(p_sampling->>'guideline_text',''))=''
  OR p_sampling->>'guideline_digest' IS DISTINCT FROM encode(sha256(convert_to(p_sampling->>'guideline_text','UTF8')),'hex')
  OR NOT(p_sampling ?& ARRAY['seed','strata','inclusion_probabilities','provenance','cohort','partition','reference_policy_version','prediction_policy_version'])
  OR jsonb_typeof(p_sampling->'seed') IS DISTINCT FROM 'number' OR (p_sampling->>'seed') !~ '^-?(0|[1-9][0-9]*)$'
  OR jsonb_typeof(p_sampling->'strata') IS DISTINCT FROM 'object'
  OR jsonb_typeof(p_sampling->'inclusion_probabilities') IS DISTINCT FROM 'object'
  OR jsonb_typeof(p_sampling->'provenance') IS DISTINCT FROM 'object' OR p_sampling->'provenance'='{}'
  OR btrim(COALESCE(p_sampling->>'cohort',''))='' OR btrim(COALESCE(p_sampling->>'reference_policy_version',''))=''
  OR btrim(COALESCE(p_sampling->>'prediction_policy_version',''))='' THEN
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
  PERFORM eval.validate_source_record_reference_frame(unit_id,jsonb_build_object(
   'protocol','source-record-reference-1','release_id',source_release,'unit_ref',unit->>'unit_key',
   'guideline',p_guideline,'reference_policy_version',p_sampling->>'reference_policy_version',
   'prediction_policy_version',p_sampling->>'prediction_policy_version','reason','source-only frame freeze','records','[]'::jsonb),frozen_frame);
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.create_source_record_reference_set(text,bigint,text,text,text,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.create_source_record_reference_set(text,bigint,text,text,text,jsonb,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.validate_source_record_reference_frame(p_unit bigint,p_payload jsonb,p_frame jsonb)
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
  OR p_frame->>'protocol' IS DISTINCT FROM 'source-record-frame-1' OR p_frame-ARRAY['protocol','evaluation_frame','source_views','captured_coordinates','context_dependency_digest']<>'{}'
  OR jsonb_typeof(bound) IS DISTINCT FROM 'object'
  OR bound-ARRAY['unit','release_id','guideline_version','reference_policy_version','prediction_policy_version','pin','anchor_ids','related_pins','anchor_scopes']<>'{}'
  OR p_payload->>'protocol' IS DISTINCT FROM 'source-record-reference-1'
  OR reference_set.sampling->>'record_protocol' IS DISTINCT FROM 'source-record-reference-1'
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
  OR p_payload->>'reference_policy_version' IS DISTINCT FROM reference_set.sampling->>'reference_policy_version'
  OR p_payload->>'prediction_policy_version' IS DISTINCT FROM reference_set.sampling->>'prediction_policy_version'
  OR bound->>'reference_policy_version' IS DISTINCT FROM p_payload->>'reference_policy_version'
  OR bound->>'prediction_policy_version' IS DISTINCT FROM p_payload->>'prediction_policy_version'
  OR unit.projection_digest IS DISTINCT FROM selected.projection_digest
  OR jsonb_typeof(bound->'anchor_ids') IS DISTINCT FROM 'array'
  OR jsonb_typeof(bound->'related_pins') IS DISTINCT FROM 'array'
  OR jsonb_typeof(bound->'anchor_scopes') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_frame->'source_views') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_frame->'captured_coordinates') IS DISTINCT FROM 'array'
  OR (p_frame->>'context_dependency_digest' IS NOT NULL AND (p_frame->>'context_dependency_digest') !~ '^[a-f0-9]{64}$')
  OR btrim(COALESCE(p_payload->>'reason',''))='' THEN
  RAISE EXCEPTION 'record reference differs from frozen source/guideline/release protocol' USING ERRCODE='23514'; END IF;
 -- Recheck partition authority even when the legacy generic set/unit entry points
 -- were used. Metadata strings alone never authorize feature-fit access.
 IF NOT EXISTS(SELECT FROM kb.document d
  JOIN eval.reference_origin_source member ON member.project_id=reference_set.project_id AND member.source_uri=d.source_uri
  JOIN eval.reference_origin_group origin ON origin.project_id=member.project_id AND origin.origin_group=member.origin_group
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(reference_set.sampling->'eligible_units','[]')) eligible
  WHERE d.id=selected.document_id AND d.project_id=reference_set.project_id
   AND origin.partition=reference_set.sampling->>'partition'
   AND reference_set.sampling->'origin_groups' @> jsonb_build_array(to_jsonb(origin))
   AND eligible->>'unit_key'=unit.unit_key AND (eligible->>'source_view_id')::bigint=selected.id
   AND eligible->>'origin_group'=origin.origin_group AND eligible->>'source_uri'=d.source_uri
   AND eligible->'frame'=p_frame-'source_views') THEN
  RAISE EXCEPTION 'record reference source has no immutable origin-partition/frame authority' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.document d JOIN kb.document copy ON copy.project_id=d.project_id AND copy.content_hash=d.content_hash
  JOIN eval.reference_origin_source original ON original.project_id=d.project_id AND original.source_uri=d.source_uri
  JOIN eval.reference_origin_source member ON member.project_id=copy.project_id AND member.source_uri=copy.source_uri
  WHERE d.id=selected.document_id AND original.origin_group<>member.origin_group) THEN
  RAISE EXCEPTION 'known source copies cannot supply separate partition origins' USING ERRCODE='23514'; END IF;
 expected:=jsonb_build_object('source',eval.record_reference_source_binding(reference_set.source_run_id,selected.id,(reference_set.sampling->>'source_cut_id')::bigint),'native_product_task_id',selected.native_task_id,
  'product_key',selected.native_product_key,'product_digest',selected.native_content_digest,
  'projection_digest',selected.projection_digest,'recipe_digest',selected.recipe_digest,'source_view_id',selected.id);
 IF bound->'pin' IS DISTINCT FROM expected THEN
  RAISE EXCEPTION 'record reference primary pin is stale' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(bound->'anchor_ids')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(bound->'anchor_ids'))
  OR EXISTS(SELECT FROM jsonb_array_elements(bound->'anchor_ids') a WHERE jsonb_typeof(a)<>'string') THEN
  RAISE EXCEPTION 'record reference anchor cut is malformed or duplicated' USING ERRCODE='23514'; END IF;
 FOR pin IN SELECT value FROM jsonb_array_elements(bound->'related_pins') LOOP
  SELECT * INTO STRICT related FROM kb.source_view WHERE id=(pin->>'source_view_id')::bigint;
  IF related.id=selected.id OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=reference_set.source_run_id AND source_view_id=related.id)
   OR related.native_build_id IS DISTINCT FROM selected.native_build_id
   OR related.native_revision_id IS DISTINCT FROM selected.native_revision_id
   OR (related.native_task_id,related.native_product_key,related.native_content_digest) IS DISTINCT FROM
    (selected.native_task_id,selected.native_product_key,selected.native_content_digest)
   OR pin IS DISTINCT FROM jsonb_build_object('source',related.key,'native_product_task_id',related.native_task_id,
    'product_key',related.native_product_key,'product_digest',related.native_content_digest,
    'projection_digest',related.projection_digest,'recipe_digest',related.recipe_digest,'source_view_id',related.id) THEN
   RAISE EXCEPTION 'record reference related source closure is stale or unselected' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF jsonb_array_length(bound->'related_pins')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(bound->'related_pins')) THEN
  RAISE EXCEPTION 'record reference repeats related pins' USING ERRCODE='23514'; END IF;
 SELECT convert_from(content,'UTF8')::json INTO STRICT scope_schema FROM sem.artifact
 WHERE release_id=reference_set.release_id AND artifact_name='json_schema/RecordReferenceAnchorScope';
 FOR scope IN SELECT value FROM jsonb_array_elements(bound->'anchor_scopes') LOOP
  IF NOT public.json_matches_schema(scope_schema,scope::json)
   OR (scope->'pin' IS DISTINCT FROM expected AND NOT EXISTS(SELECT FROM jsonb_array_elements(bound->'related_pins') p WHERE p=scope->'pin'))
   OR scope->>'space'='model_context'
   OR (scope->>'precision'='exact' AND (scope->>'start' IS NULL OR scope->>'end' IS NULL OR NOT(0<=(scope->>'start')::bigint AND (scope->>'start')::bigint<(scope->>'end')::bigint)))
   OR (scope->>'precision'<>'exact' AND (scope ? 'start' OR scope ? 'end'))
   OR ((scope->>'space'='captured_recognition') IS DISTINCT FROM (scope ? 'recognition')) THEN
   RAISE EXCEPTION 'record reference source scope is malformed, unbound or lossy' USING ERRCODE='23514'; END IF;
  scope_pointer:=CASE WHEN scope->>'pointer' ~ '^#/tables/(0|[1-9][0-9]*)/data/table_cells/(0|[1-9][0-9]*)$'
   THEN split_part(scope->>'pointer','/data/table_cells/',1) ELSE scope->>'pointer' END;
  IF NOT EXISTS(SELECT FROM kb.source_view scope_view WHERE scope_view.id=(scope->'pin'->>'source_view_id')::bigint
   AND (scope_view.projection->'items' ? scope_pointer OR COALESCE(scope_view.projection->'ancestors','[]') ? scope_pointer)) THEN
   RAISE EXCEPTION 'record reference scope pointer is outside its selected view' USING ERRCODE='23514'; END IF;
  IF scope->>'precision'='exact' AND scope->>'space'<>'captured_recognition' THEN
   IF scope->>'space'='selected_projection' THEN
    SELECT projection->>'text' INTO STRICT scope_text FROM kb.source_view WHERE id=(scope->'pin'->>'source_view_id')::bigint;
   ELSE
    SELECT native_json INTO STRICT scope_node FROM ops.read_pdf_published_items(
     (scope->'pin'->>'native_product_task_id')::bigint,scope->'pin'->>'product_key',scope->'pin'->>'product_digest',ARRAY[scope_pointer]);
    IF scope->>'pointer'<>scope_pointer THEN scope_node:=scope_node->'data'->'table_cells'->split_part(scope->>'pointer','/data/table_cells/',2)::integer; END IF;
    scope_text:=scope_node->>'text';
   END IF;
   IF scope_text IS NULL OR (scope->>'end')::bigint>length(scope_text) THEN
    RAISE EXCEPTION 'record reference scope exceeds its actual immutable source coordinate' USING ERRCODE='23514'; END IF;
  END IF;
  IF scope->>'space'='captured_recognition' AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_frame->'captured_coordinates') c
   WHERE c->'pin'=scope->'pin' AND c->>'pointer'=scope->>'pointer' AND c->'recognition'=scope->'recognition'
    AND (scope->>'end')::bigint<=length(c->>'text')) THEN
   RAISE EXCEPTION 'record scope is outside independently frozen capture coordinates' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT jsonb_agg(to_jsonb(v) ORDER BY v.id) INTO source_snapshot FROM kb.source_view v WHERE v.id IN (
  SELECT selected.id UNION ALL SELECT (p->>'source_view_id')::bigint FROM jsonb_array_elements(bound->'related_pins') p);
 IF EXISTS(SELECT FROM jsonb_array_elements(source_snapshot) v WHERE NOT EXISTS(
  SELECT FROM jsonb_array_elements(reference_set.sampling->'source_membership') m
  WHERE (m->>'source_view_id')::bigint=(v->>'id')::bigint AND (m->>'run_id')::bigint=reference_set.source_run_id))
  OR p_frame->'source_views' IS DISTINCT FROM source_snapshot THEN
  RAISE EXCEPTION 'immutable record source frames are stale or incomplete' USING ERRCODE='23514'; END IF;
 SELECT convert_from(content,'UTF8')::json INTO STRICT capture_schema FROM sem.artifact
 WHERE release_id=reference_set.release_id AND artifact_name='json_schema/RecordCoordinateText';
 FOR captured IN SELECT value FROM jsonb_array_elements(p_frame->'captured_coordinates') LOOP
  SELECT * INTO STRICT captured_view FROM kb.source_view WHERE id=(captured->'pin'->>'source_view_id')::bigint;
  IF NOT(captured_view.projection->'items' ? (captured->>'pointer')
   OR COALESCE(captured_view.projection->'ancestors','[]') ? (captured->>'pointer')) THEN
   RAISE EXCEPTION 'captured coordinate pointer is outside frozen selected view' USING ERRCODE='23514'; END IF;
  IF NOT public.json_matches_schema(capture_schema,captured::json) OR captured->>'space' IS DISTINCT FROM 'captured_recognition' OR NOT captured ? 'recognition'
   OR (captured->'pin' IS DISTINCT FROM expected AND NOT EXISTS(SELECT FROM jsonb_array_elements(bound->'related_pins') p WHERE p=captured->'pin'))
   OR captured->>'text' IS DISTINCT FROM ops.record_captured_recognition_text(captured_view.native_task_id,
    captured_view.native_product_key,captured_view.native_content_digest,captured->>'pointer',captured->'recognition') THEN
   RAISE EXCEPTION 'frozen captured coordinate differs from actual retained recognition' USING ERRCODE='23514'; END IF;
 END LOOP;
 PERFORM ops.validate_source_record_coordinates(reference_set.source_run_id,selected.id,expected->>'source',p_payload->'records');
 FOR source_record IN SELECT value FROM jsonb_array_elements(p_payload->'records') LOOP
  PERFORM data.validate_source_record_structure(reference_set.release_id,source_record);
  IF source_record->>'family' NOT IN ('definition','assertion','measurement','table','formula_context')
   OR source_record->>'standing' IS DISTINCT FROM 'accepted'
   OR source_record->>'policy_version' IS DISTINCT FROM bound->>'reference_policy_version'
   OR EXISTS(SELECT FROM jsonb_array_elements(source_record->'anchors') a
    WHERE (NOT(bound->'anchor_ids' ? (a->>'anchor_id')) AND NOT EXISTS(
      SELECT FROM jsonb_array_elements(bound->'anchor_scopes') bounded_scope(value) WHERE bounded_scope.value->'pin'=a->'pin'
       AND bounded_scope.value->>'space'=a->>'space' AND bounded_scope.value->>'pointer'=a->>'pointer' AND bounded_scope.value->>'precision'=a->>'precision'
       AND bounded_scope.value->'recognition' IS NOT DISTINCT FROM a->'recognition'
       AND (bounded_scope.value->>'precision'<>'exact' OR (
        (bounded_scope.value->>'start')::bigint<=(a->>'start')::bigint AND (a->>'end')::bigint<=(bounded_scope.value->>'end')::bigint))))
     OR (a->>'space'='captured_recognition' AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_frame->'captured_coordinates') c
      WHERE c->'pin'=a->'pin' AND c->>'pointer'=a->>'pointer' AND c->'recognition'=a->'recognition'))
     OR (a->'pin' IS DISTINCT FROM expected
     AND NOT EXISTS(SELECT FROM jsonb_array_elements(bound->'related_pins') p WHERE p=a->'pin'))) THEN
   RAISE EXCEPTION 'expected reading is outside frozen reference authority/anchor cut' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (SELECT count(*) FROM jsonb_array_elements(p_payload->'records'))<>
  (SELECT count(DISTINCT r->>'record_id') FROM jsonb_array_elements(p_payload->'records') r) THEN
  RAISE EXCEPTION 'reference duplicates source occurrences' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION eval.validate_source_record_reference_frame(bigint,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_source_record_reference_pass(p_unit bigint,p_kind text,p_actor text,p_authored bytea,p_frame jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint; unit eval.reference_unit; reference_set eval.reference_set;
 payload jsonb; schema json; pass_a eval.reference_pass; pass_b eval.reference_pass; source_record jsonb; frame_id bigint;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit FOR UPDATE;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=unit.set_id;
 PERFORM sem.require_execution_operation(reference_set.release_id,'reference_record_pass');
 payload:=convert_from(p_authored,'UTF8')::jsonb;
 SELECT convert_from(content,'UTF8')::json INTO STRICT schema FROM sem.artifact
 WHERE release_id=reference_set.release_id AND artifact_name='json_schema/ReferenceRecordBatch';
 IF NOT public.json_matches_schema(schema,payload::json) OR p_kind NOT IN ('A','B','C') OR p_kind IS NULL
  OR btrim(COALESCE(p_actor,''))='' THEN
  RAISE EXCEPTION 'record reference pass differs from released independent protocol' USING ERRCODE='23514'; END IF;
 PERFORM eval.validate_source_record_reference_frame(p_unit,payload,p_frame);
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
 FOR source_record IN SELECT value FROM jsonb_array_elements(payload->'records') LOOP
  INSERT INTO eval.reference_item(pass_id,frame_id,item_kind,local_ref,payload)
  VALUES(result,frame_id,source_record->>'family',source_record->>'record_id',source_record);
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_source_record_reference_pass(bigint,text,text,bytea,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_source_record_reference_pass(bigint,text,text,bytea,jsonb) TO corpus_sem_evaluator;

-- Strict reference compatibility is a derived projection, not a compatibility store.
CREATE OR REPLACE FUNCTION eval.record_reference_contract(p_release text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE projection jsonb; schemas jsonb; name text; schema jsonb; products jsonb; consumed text[]; ranges text[]; definitions jsonb; vocabularies jsonb; enums jsonb;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT projection FROM sem.artifact
  WHERE release_id=p_release AND artifact_name='record_projection.json';
 schemas:='{}';
 FOR name IN SELECT value FROM (
  SELECT unnest(ARRAY['SourceRecord','RecordSourcePin','RecordCoordinateText','ReferenceRecordBatch','RecordReferenceAnchorScope']) AS value
  UNION SELECT family->>'contract' FROM jsonb_array_elements(projection->'families') family) names ORDER BY value LOOP
  SELECT convert_from(content,'UTF8')::jsonb INTO STRICT schema FROM sem.artifact
   WHERE release_id=p_release AND artifact_name='json_schema/'||name;
  schemas:=schemas||jsonb_build_object(name,schema);
 END LOOP;
 SELECT convert_from(prepared_bytes,'UTF8')::jsonb->'products' INTO STRICT products FROM sem.release WHERE release_id=p_release;
 SELECT array_agg(DISTINCT value) INTO consumed FROM (
  SELECT jsonb_object_keys(schemas) AS value UNION ALL
  SELECT jsonb_object_keys(COALESCE(value->'$defs','{}')) FROM jsonb_each(schemas)) names;
 SELECT COALESCE(jsonb_agg(value ORDER BY value->>'name'),'[]'::jsonb) INTO definitions
  FROM jsonb_array_elements(products->'definitions') WHERE value->>'name'=ANY(consumed);
 SELECT array_agg(DISTINCT property->>'range') INTO ranges FROM jsonb_array_elements(definitions) definition
  CROSS JOIN LATERAL jsonb_array_elements(definition->'properties') property;
 SELECT COALESCE(jsonb_agg(value ORDER BY value->>'enum'),'[]'::jsonb) INTO vocabularies
  FROM jsonb_array_elements(products->'vocabularies') WHERE value->>'enum'=ANY(ranges);
 SELECT COALESCE(jsonb_agg(value ORDER BY value->>'name'),'[]'::jsonb) INTO enums
  FROM jsonb_array_elements(products->'registry_rows') WHERE value->>'kind'='enum' AND value->>'name'=ANY(ranges);
 RETURN jsonb_build_object('comparison_policy','strict-source-occurrence-1','families',projection->'families',
  'classification_kinds',projection->'classification_kinds','schemas',schemas,'definitions',definitions,
  'vocabularies',vocabularies,'enum_declarations',enums);
END $$;
REVOKE ALL ON FUNCTION eval.record_reference_contract(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_reference_physical_source(p_view bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE view kb.source_view; document kb.document; recipe bytea;
BEGIN
 SELECT * INTO STRICT view FROM kb.source_view WHERE id=p_view;
 SELECT * INTO STRICT document FROM kb.document WHERE id=view.document_id;
 SELECT content INTO STRICT recipe FROM kb.source_artifact WHERE artifact_digest=view.recipe_digest;
 IF view.projection_digest IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(view.projection),'UTF8')),'hex')
  OR view.recipe_digest IS DISTINCT FROM encode(sha256(recipe),'hex')
  OR document.content_hash IS NULL
  OR NOT EXISTS(SELECT FROM ops.pdf_selected_product WHERE task_id=view.native_task_id
   AND product_key=view.native_product_key AND content_digest=view.native_content_digest)
  OR NOT EXISTS(SELECT FROM ops.pdf_published_revision WHERE task_id=view.native_task_id
   AND product_key=view.native_product_key AND logical_digest=view.native_content_digest
   AND build_id=view.native_build_id AND build_id=view.native_revision_id) THEN
  RAISE EXCEPTION 'reference physical source custody/digests unavailable or changed' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('document_id',document.id,'document_key',document.key,
  'source_uri',document.source_uri,'content_hash',document.content_hash,
  'native_product_task_id',view.native_task_id,'product_key',view.native_product_key,'product_digest',view.native_content_digest,
  'native_build_id',view.native_build_id,'native_revision_id',view.native_revision_id,
  'section_pointer',view.section_pointer,'membership',view.membership,'analysis_eligible',view.analysis_eligible,
  'recipe_digest',view.recipe_digest,'recipe_bytes',encode(recipe,'hex'),
  'projection_digest',view.projection_digest,'projection',view.projection);
END $$;
REVOKE ALL ON FUNCTION eval.record_reference_physical_source(bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_reference_applicability(p_project text,p_run bigint,p_set bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference_set eval.reference_set; completed ops.completed_result; contract jsonb; physical jsonb;
 original kb.source_view; actual kb.source_view; candidates bigint[]; views jsonb:='[]';
BEGIN
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 SELECT c.* INTO STRICT completed FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id
  JOIN ops.input_cut cut ON cut.id=c.cut_id AND cut.run_id=r.id AND cut.release_id=c.release_id
  WHERE c.run_id=p_run AND r.project_id=p_project AND r.sealed AND r.status='finished' AND cut.final;
 PERFORM sem.require_execution_operation(completed.release_id,'reference_record_grade');
 contract:=eval.record_reference_contract(reference_set.release_id);
 IF contract IS DISTINCT FROM eval.record_reference_contract(completed.release_id)
  OR reference_set.sampling->>'record_protocol' IS DISTINCT FROM 'source-record-reference-1'
  OR reference_set.sampling->>'guideline_digest' IS DISTINCT FROM encode(sha256(convert_to(reference_set.sampling->>'guideline_text','UTF8')),'hex')
  OR btrim(COALESCE(reference_set.sampling->>'reference_policy_version',''))=''
  OR btrim(COALESCE(reference_set.sampling->>'prediction_policy_version',''))='' THEN
  RAISE EXCEPTION 'reference source/coordinate/family/guideline comparison contract differs' USING ERRCODE='23514'; END IF;
 FOR original IN SELECT DISTINCT v.* FROM eval.reference_unit u
  CROSS JOIN LATERAL jsonb_array_elements(u.context->0->'source_views') frozen
  JOIN kb.source_view v ON v.id=(frozen->>'id')::bigint WHERE u.set_id=p_set ORDER BY v.id LOOP
  IF NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=reference_set.source_run_id AND source_view_id=original.id) THEN
   RAISE EXCEPTION 'reference source closure is outside original run' USING ERRCODE='23514'; END IF;
  physical:=eval.record_reference_physical_source(original.id);
  SELECT array_agg(v.id ORDER BY v.id) INTO candidates FROM ops.run_source_view member
   JOIN kb.source_view v ON v.id=member.source_view_id
   WHERE member.run_id=p_run
    AND (v.document_id,v.native_task_id,v.native_product_key,v.native_content_digest,v.native_build_id,
     v.native_revision_id,v.section_pointer,v.membership,v.analysis_eligible,v.recipe_digest,v.projection_digest)
     IS NOT DISTINCT FROM (original.document_id,original.native_task_id,original.native_product_key,
      original.native_content_digest,original.native_build_id,original.native_revision_id,original.section_pointer,
      original.membership,original.analysis_eligible,original.recipe_digest,original.projection_digest)
    AND eval.record_reference_physical_source(v.id)=physical;
  IF COALESCE(cardinality(candidates),0)<>1 THEN
   RAISE EXCEPTION 'reference source correspondence missing or ambiguous for view %',original.id USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT actual FROM kb.source_view WHERE id=candidates[1];
  IF EXISTS(SELECT FROM jsonb_array_elements(views) pair WHERE (pair->>'prediction_view_id')::bigint=actual.id) THEN
   RAISE EXCEPTION 'reference source correspondence is not bijective' USING ERRCODE='23514'; END IF;
  views:=views||jsonb_build_array(jsonb_build_object('reference_view_id',original.id,'prediction_view_id',actual.id,
   'reference_key',original.key,'prediction_key',actual.key,
   'physical_digest',encode(sha256(convert_to(data.canonical_json(physical),'UTF8')),'hex')));
 END LOOP;
 IF views='[]' THEN RAISE EXCEPTION 'reference source closure is empty' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('protocol','source-record-reference-applicability-1',
  'comparison_policy','strict-source-occurrence-1','reference_release_id',reference_set.release_id,
  'prediction_release_id',completed.release_id,'source_run_id',reference_set.source_run_id,
  'source_cut_id',(reference_set.sampling->>'source_cut_id')::bigint,'run_id',p_run,'cut_id',completed.cut_id,
  'contract_digest',encode(sha256(convert_to(data.canonical_json(contract),'UTF8')),'hex'),
  'guideline_digest',reference_set.sampling->>'guideline_digest',
  'reference_policy_version',reference_set.sampling->>'reference_policy_version',
  'prediction_policy_version',reference_set.sampling->>'prediction_policy_version','views',views);
END $$;
REVOKE ALL ON FUNCTION eval.record_reference_applicability(text,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_reference_applicability(text,bigint,bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_reference_unit_binding(p_run bigint,p_unit bigint,p_pass bigint,p_frame bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE unit eval.reference_unit; reference_set eval.reference_set; payload jsonb; frozen jsonb; bound jsonb;
 applicability jsonb; pair jsonb; original_pin jsonb; actual_pin jsonb; pins jsonb:='[]'; related jsonb:='[]';
 scopes jsonb:='[]'; ids jsonb:='[]'; scope jsonb; actual kb.source_view;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=unit.set_id;
 SELECT convert_from(p.authored,'UTF8')::jsonb,f.source_frame INTO STRICT payload,frozen
  FROM eval.reference_pass p JOIN eval.reference_frame f ON f.pass_id=p.id
  WHERE p.id=p_pass AND p.unit_id=p_unit AND p.pass_kind='C' AND f.id=p_frame;
 PERFORM eval.validate_source_record_reference_frame(p_unit,payload,frozen);
 applicability:=eval.record_reference_applicability(reference_set.project_id,p_run,unit.set_id);
 bound:=frozen->'evaluation_frame';
 FOR original_pin IN SELECT bound->'pin' UNION ALL SELECT value FROM jsonb_array_elements(bound->'related_pins') LOOP
  SELECT value INTO STRICT pair FROM jsonb_array_elements(applicability->'views')
   WHERE (value->>'reference_view_id')::bigint=(original_pin->>'source_view_id')::bigint;
  SELECT * INTO STRICT actual FROM kb.source_view WHERE id=(pair->>'prediction_view_id')::bigint;
  actual_pin:=original_pin||jsonb_build_object('source_view_id',actual.id,'source',CASE
   WHEN original_pin=bound->'pin' THEN eval.record_reference_source_binding(p_run,actual.id,(applicability->>'cut_id')::bigint)
   ELSE actual.key END);
  IF applicability->>'reference_release_id'=applicability->>'prediction_release_id' AND actual_pin IS DISTINCT FROM original_pin THEN
   -- Missing/failed producers supply no authenticated report alias. Keep the
   -- original frame's logical coordinate so their source denominator survives;
   -- a genuine report with a different alias still refuses.
   IF (actual_pin-'source') IS NOT DISTINCT FROM (original_pin-'source') AND NOT EXISTS(
    SELECT FROM ops.cut_task ct JOIN ops.task t ON t.id=ct.origin_task_id
     JOIN ops.task_result r ON r.task_id=t.id AND r.release_id=t.release_id
    WHERE ct.cut_id=(applicability->>'cut_id')::bigint AND t.unit_type='source_view'
     AND t.unit_id=actual.id AND r.body ? 'source') THEN
    actual_pin:=original_pin;
   ELSE
    RAISE EXCEPTION 'record grade logical source binding changed from frozen source cut' USING ERRCODE='23514';
   END IF;
  END IF;
  pins:=pins||jsonb_build_array(jsonb_build_object('reference_pin',original_pin,'prediction_pin',actual_pin,
   'physical_digest',pair->>'physical_digest'));
  IF original_pin<>bound->'pin' THEN related:=related||jsonb_build_array(actual_pin); END IF;
 END LOOP;
 FOR scope IN SELECT value FROM jsonb_array_elements(bound->'anchor_scopes') LOOP
  SELECT value INTO STRICT pair FROM jsonb_array_elements(pins) WHERE value->'reference_pin'=scope->'pin';
  scopes:=scopes||jsonb_build_array(scope||jsonb_build_object('pin',pair->'prediction_pin'));
 END LOOP;
 -- Keep the original opaque allowlist. Actual anchors are checked by deriving their
 -- counterpart reference identity after authenticating the actual coordinate.
 ids:=bound->'anchor_ids';
 SELECT value->'prediction_pin' INTO STRICT actual_pin FROM jsonb_array_elements(pins) WHERE value->'reference_pin'=bound->'pin';
 RETURN jsonb_build_object('views',pins,'prediction_frame',jsonb_build_object('protocol','source-record-frame-1',
  'evaluation_frame',bound||jsonb_build_object('release_id',applicability->>'prediction_release_id',
   'pin',actual_pin,'related_pins',related,'anchor_scopes',scopes,'anchor_ids',ids)));
END $$;
REVOKE ALL ON FUNCTION eval.record_reference_unit_binding(bigint,bigint,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_reference_unit_binding(bigint,bigint,bigint,bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_reference_anchor_allowed(p_anchor jsonb,p_views jsonb,p_frame jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE pair jsonb; counterpart jsonb; identity text;
BEGIN
 SELECT value INTO STRICT pair FROM jsonb_array_elements(p_views) WHERE value->'prediction_pin'=p_anchor->'pin';
 counterpart:=(p_anchor-'anchor_id')||jsonb_build_object('pin',pair->'reference_pin');
 identity:='record-anchor:'||encode(sha256(convert_to(data.canonical_json(counterpart||jsonb_build_object(
  'pin',(pair->'reference_pin')-'source_view_id')),'UTF8')),'hex');
 RETURN p_frame->'anchor_ids' ? identity OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'anchor_scopes') scope
  WHERE scope->'pin'=counterpart->'pin' AND scope->'space'=counterpart->'space'
   AND scope->'pointer'=counterpart->'pointer' AND scope->'precision'=counterpart->'precision'
   AND scope->'recognition' IS NOT DISTINCT FROM counterpart->'recognition'
   AND (scope->>'precision'<>'exact' OR ((scope->>'start')::bigint<=(counterpart->>'start')::bigint
    AND (counterpart->>'start')::bigint<(counterpart->>'end')::bigint
    AND (counterpart->>'end')::bigint<=(scope->>'end')::bigint)));
END $$;
REVOKE ALL ON FUNCTION eval.record_reference_anchor_allowed(jsonb,jsonb,jsonb) FROM PUBLIC;

-- Comparison-only coordinates never rewrite persisted anchor/set/record identities.
CREATE OR REPLACE FUNCTION eval.record_reference_comparison_record(p_record jsonb,p_views jsonb,p_side text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE anchor jsonb; evidence jsonb; item jsonb; alternative jsonb; pair jsonb; physical text; identity text;
 anchors jsonb:='{}'; sets jsonb:='{}'; members jsonb; fields jsonb:='[]'; alternatives jsonb;
BEGIN
 IF p_side NOT IN ('reference','prediction') THEN RAISE EXCEPTION 'unknown reference comparison side' USING ERRCODE='23514'; END IF;
 FOR anchor IN SELECT value FROM jsonb_array_elements(p_record->'anchors') LOOP
  SELECT value INTO STRICT pair FROM jsonb_array_elements(p_views) WHERE value->(p_side||'_pin')=anchor->'pin';
  identity:=encode(sha256(convert_to(data.canonical_json((anchor-'anchor_id'-'pin')||jsonb_build_object('pin',pair->>'physical_digest')),'UTF8')),'hex');
  anchors:=anchors||jsonb_build_object(anchor->>'anchor_id',identity);
 END LOOP;
 FOR evidence IN SELECT value FROM jsonb_array_elements(COALESCE(p_record->'evidence_sets','[]')) LOOP
  SELECT COALESCE(jsonb_agg(anchors->value ORDER BY CASE WHEN evidence->>'ordering'='ordered' THEN ordinal END,
   CASE WHEN evidence->>'ordering'<>'ordered' THEN anchors->>value END COLLATE "C"),'[]'::jsonb)
   INTO members FROM jsonb_array_elements_text(evidence->'anchors') WITH ORDINALITY entry(value,ordinal);
  identity:=encode(sha256(convert_to(data.canonical_json((evidence-'set_id')||jsonb_build_object('anchors',members)),'UTF8')),'hex');
  sets:=sets||jsonb_build_object(evidence->>'set_id',identity);
 END LOOP;
 FOR item IN SELECT value FROM jsonb_array_elements(p_record->'fields') LOOP
  IF item ? 'evidence_sets' THEN
   SELECT COALESCE(jsonb_agg(sets->value ORDER BY ordinal),'[]'::jsonb) INTO members
    FROM jsonb_array_elements_text(item->'evidence_sets') WITH ORDINALITY entry(value,ordinal);
   item:=item||jsonb_build_object('evidence_sets',members);
  END IF;
  IF item ? 'alternatives' THEN
   alternatives:='[]';
   FOR alternative IN SELECT value FROM jsonb_array_elements(item->'alternatives') LOOP
    SELECT COALESCE(jsonb_agg(sets->value ORDER BY ordinal),'[]'::jsonb) INTO members
     FROM jsonb_array_elements_text(COALESCE(alternative->'evidence_sets','[]')) WITH ORDINALITY entry(value,ordinal);
    alternatives:=alternatives||jsonb_build_array(alternative||jsonb_build_object('evidence_sets',members));
   END LOOP;
   item:=item||jsonb_build_object('alternatives',alternatives);
  END IF;
  fields:=fields||jsonb_build_array(item);
 END LOOP;
 SELECT value->>'physical_digest' INTO STRICT physical FROM jsonb_array_elements(p_views) WHERE value->(p_side||'_pin')=p_record->'pin';
 SELECT COALESCE(jsonb_agg(anchors->value ORDER BY anchors->>value COLLATE "C"),'[]'::jsonb) INTO members
  FROM jsonb_array_elements_text(p_record->'occurrence_anchors');
 RETURN jsonb_build_object('occurrence',encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
  p_record->'family',p_record->'occurrence_recipe',physical,members)),'UTF8')),'hex'),'fields',fields);
END $$;
REVOKE ALL ON FUNCTION eval.record_reference_comparison_record(jsonb,jsonb,text) FROM PUBLIC;

-- Protected gap evidence is derived, never authored as free-form writer labels.
-- Keep expected values in C. These rows link source anchors and actual immutable
-- invocation diagnostics; missing diagnostics never establish a failed stage.
-- The completed final run also owns actual failed/skipped/cancelled terminal tasks.
-- They are immutable final-run diagnostics, explicitly outside successful cut custody;
-- publisher failures may occur after sealing, so this is not an as-of-cut claim.
CREATE OR REPLACE FUNCTION eval.source_record_gap_evidence(p_run bigint,p_unit bigint,p_pass bigint,p_frame bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE unit eval.reference_unit; reference_set eval.reference_set; completed ops.completed_result;
 payload jsonb; tasks jsonb; predictions jsonb; expected jsonb; actual jsonb;
 readings jsonb; reading_roles jsonb; evidence_roles jsonb; gaps jsonb:='[]'; kind text;
 binding jsonb; prediction_view bigint; reference_projection jsonb; prediction_projection jsonb; prediction_record jsonb; frozen jsonb;
 matched_bindings jsonb:='[]'; matched_tiers jsonb; family_contract jsonb; core_match boolean; full_match boolean;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=unit.set_id;
 SELECT * INTO STRICT completed FROM ops.completed_result WHERE run_id=p_run;
 PERFORM sem.require_execution_operation(completed.release_id,'reference_record_grade');
 binding:=eval.record_reference_unit_binding(p_run,p_unit,p_pass,p_frame);
 prediction_view:=(binding->'prediction_frame'->'evaluation_frame'->'pin'->>'source_view_id')::bigint;
 SELECT source_frame->'evaluation_frame' INTO STRICT frozen FROM eval.reference_frame WHERE id=p_frame AND pass_id=p_pass;
 IF NOT EXISTS(SELECT FROM ops.run job JOIN ops.input_cut cut ON cut.id=completed.cut_id
  AND cut.run_id=job.id AND cut.release_id=completed.release_id
  WHERE job.id=p_run AND job.project_id=reference_set.project_id AND job.sealed
   AND job.status='finished' AND cut.final) THEN
  RAISE EXCEPTION 'gap evidence requires the project immutable completed final run' USING ERRCODE='23514'; END IF;
 SELECT convert_from(p.authored,'UTF8')::jsonb INTO STRICT payload FROM eval.reference_pass p
 JOIN eval.reference_frame f ON f.pass_id=p.id WHERE p.id=p_pass AND p.unit_id=p_unit AND p.pass_kind='C' AND f.id=p_frame;
 SELECT COALESCE(jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
  'selected_task_id',selected.id,'origin_task_id',origin.id,'cut_member',ct.task_id IS NOT NULL,
  'method',method.name,'operation_version',method.version,
  'configuration_hash',config.config_hash,'input_hash',selected.input_hash,'outcome',selected.status,
  'result_present',result.task_id IS NOT NULL,'coverage_present',COALESCE(result.body ? 'coverage',false),
  'coverage',COALESCE(result.body->'coverage','[]'::jsonb),'parse_detail',result.body->'parse_detail',
  'error',COALESCE(result.body->>'error',origin.error::text,selected.error::text),
  'reason',selected.reason,
  'dependency_task_ids',COALESCE((SELECT jsonb_agg(dependency_task_id ORDER BY dependency_task_id)
    FROM ops.task_dependency WHERE task_id=selected.id),'[]'::jsonb),
  'dependent_task_ids',COALESCE((SELECT jsonb_agg(task_id ORDER BY task_id)
    FROM ops.task_dependency WHERE dependency_task_id=selected.id),'[]'::jsonb))) ORDER BY selected.id),'[]'::jsonb)
 INTO tasks FROM ops.task selected
 LEFT JOIN ops.cut_task ct ON ct.task_id=selected.id AND ct.cut_id=completed.cut_id
 JOIN ops.task origin ON origin.id=COALESCE(ct.origin_task_id,selected.id)
 JOIN ops.method_config config ON config.id=selected.method_config_id
 JOIN ops.method method ON method.id=config.method_id LEFT JOIN ops.task_result result ON result.task_id=origin.id
 WHERE selected.run_id=p_run AND selected.release_id=completed.release_id
  AND (ct.task_id IS NOT NULL OR selected.status IN ('failed','skipped','cancelled'))
  AND selected.unit_type='source_view' AND selected.unit_id=prediction_view;
 -- Use exactly the authoritative resolver/raw source selection used by grading.
 WITH selected AS (
  SELECT value FROM jsonb_array_elements(tasks) WHERE value->>'method'=CASE
   WHEN EXISTS(SELECT FROM jsonb_array_elements(tasks) t WHERE t->>'method'='resolve.m1_readings') THEN 'resolve.m1_readings'
   WHEN EXISTS(SELECT FROM jsonb_array_elements(tasks) t WHERE t->>'method'='extract.m1_candidates') THEN 'extract.m1_candidates'
   ELSE value->>'method' END),
 published AS (
  SELECT DISTINCT record,admission.decision FROM selected t
  JOIN data.record_report_member member ON member.selected_task_id=(t.value->>'selected_task_id')::bigint
   AND member.release_id=completed.release_id AND member.realization_id=completed.output_realization_id
  JOIN data.record_admission admission ON admission.release_id=member.release_id AND admission.realization_id=member.realization_id
   AND admission.record_id=member.record_id AND admission.interpretation_id=member.interpretation_id
  JOIN ops.task_result result ON result.task_id=(t.value->>'origin_task_id')::bigint
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(result.body->'records','[]')) record
  WHERE record->>'record_id'=member.record_id AND record->>'interpretation_id'=member.interpretation_id)
 SELECT COALESCE(jsonb_agg(record||jsonb_build_object('standing',decision)
  ORDER BY record->>'record_id',record->>'interpretation_id'),'[]'::jsonb) INTO predictions FROM published;
 PERFORM ops.validate_source_record_coordinates(p_run,prediction_view,
  binding->'prediction_frame'->'evaluation_frame'->'pin'->>'source',predictions);
 FOR prediction_record IN SELECT value FROM jsonb_array_elements(predictions) LOOP
  IF prediction_record->>'policy_version' IS DISTINCT FROM binding->'prediction_frame'->'evaluation_frame'->>'prediction_policy_version' THEN
   RAISE EXCEPTION 'prediction policy differs from frozen evaluation policy' USING ERRCODE='23514'; END IF;
  PERFORM data.validate_source_record_structure(completed.release_id,prediction_record);
  IF prediction_record->'pin' IS DISTINCT FROM binding->'prediction_frame'->'evaluation_frame'->'pin'
   OR EXISTS(SELECT FROM jsonb_array_elements(prediction_record->'anchors') anchor WHERE
    NOT eval.record_reference_anchor_allowed(anchor,binding->'views',frozen)) THEN
   RAISE EXCEPTION 'prediction differs from independently authenticated mapped reference cut' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR expected IN SELECT value FROM jsonb_array_elements(payload->'records') ORDER BY value->>'record_id' LOOP
  reference_projection:=eval.record_reference_comparison_record(expected,binding->'views','reference');
  SELECT COALESCE(jsonb_agg(jsonb_build_object('record_id',value->>'record_id','interpretation_id',value->>'interpretation_id','standing',value->>'standing')
   ORDER BY value->>'interpretation_id'),'[]'::jsonb) INTO readings
   FROM jsonb_array_elements(predictions) WHERE eval.record_reference_comparison_record(value,binding->'views','prediction')->'occurrence'=reference_projection->'occurrence';
  SELECT value INTO actual FROM jsonb_array_elements(predictions)
   WHERE eval.record_reference_comparison_record(value,binding->'views','prediction')->'occurrence'=reference_projection->'occurrence' AND value->>'standing'='accepted';
  reading_roles:='[]'; evidence_roles:='[]';
  IF actual IS NOT NULL THEN
   prediction_projection:=eval.record_reference_comparison_record(actual,binding->'views','prediction');
   SELECT COALESCE(jsonb_agg(ref->>'role' ORDER BY ref->>'role'),'[]'::jsonb) INTO reading_roles
    FROM jsonb_array_elements(reference_projection->'fields') ref LEFT JOIN LATERAL
     (SELECT value FROM jsonb_array_elements(prediction_projection->'fields') WHERE value->>'role'=ref->>'role') pred ON true
    WHERE eval.record_policy_field_meaning(ref) IS DISTINCT FROM eval.record_policy_field_meaning(pred.value);
   SELECT COALESCE(jsonb_agg(ref->>'role' ORDER BY ref->>'role'),'[]'::jsonb) INTO evidence_roles
    FROM jsonb_array_elements(reference_projection->'fields') ref LEFT JOIN LATERAL
     (SELECT value FROM jsonb_array_elements(prediction_projection->'fields') WHERE value->>'role'=ref->>'role') pred ON true
    WHERE eval.record_policy_field_evidence(ref) IS DISTINCT FROM eval.record_policy_field_evidence(pred.value);
   SELECT family INTO STRICT family_contract FROM sem.artifact artifact,
    LATERAL jsonb_array_elements(convert_from(artifact.content,'UTF8')::jsonb->'families') family
    WHERE artifact.release_id=completed.release_id AND artifact.artifact_name='record_projection.json'
     AND family->>'family'=expected->>'family';
   core_match:=NOT EXISTS(SELECT FROM jsonb_array_elements(family_contract->'roles') role
    WHERE role->'required'='true'::jsonb AND reading_roles ? (role->>'role'));
   full_match:=core_match AND reading_roles='[]' AND NOT EXISTS(
    SELECT FROM jsonb_array_elements(family_contract->'roles') role WHERE
     (role->'required'='true'::jsonb OR role->'meaning_changing'='true'::jsonb) AND evidence_roles ? (role->>'role'));
   matched_tiers:='[]';
   IF core_match THEN matched_tiers:=matched_tiers||'"core"'::jsonb; END IF;
   IF full_match THEN matched_tiers:=matched_tiers||'"full"'::jsonb; END IF;
   IF full_match AND evidence_roles='[]' THEN matched_tiers:=matched_tiers||'"evidence"'::jsonb; END IF;
   matched_bindings:=matched_bindings||jsonb_build_array(jsonb_build_object(
    'reference_record_id',expected->>'record_id','reference_interpretation_id',expected->>'interpretation_id',
    'prediction_record_id',actual->>'record_id','prediction_interpretation_id',actual->>'interpretation_id','tiers',matched_tiers));
   IF reading_roles='[]' AND evidence_roles='[]' THEN CONTINUE; END IF;
   kind:='mismatched';
  ELSIF readings<>'[]' THEN kind:='unaccepted';
  ELSIF predictions='[]' THEN kind:='no_output';
  ELSE kind:='missing'; END IF;
  gaps:=gaps||jsonb_build_array(jsonb_build_object('reference_record_id',expected->>'record_id','reference_interpretation_id',expected->>'interpretation_id','family',expected->>'family',
   'reference_anchor_ids',COALESCE((SELECT jsonb_agg(a->>'anchor_id' ORDER BY a->>'anchor_id')
     FROM jsonb_array_elements(expected->'anchors') a),'[]'::jsonb),
   'kind',kind,'earliest_failed_stage','unknown','reading_roles',reading_roles,'evidence_roles',evidence_roles,'predictions',readings));
 END LOOP;
 RETURN jsonb_build_object('unit_id',p_unit,'pass_id',p_pass,'frame_id',p_frame,'source_view_id',unit.source_view_id,
  'prediction_source_view_id',prediction_view,'reference_release_id',reference_set.release_id,'prediction_release_id',completed.release_id,
  'source_run_id',reference_set.source_run_id,'source_cut_id',(reference_set.sampling->>'source_cut_id')::bigint,
  'run_id',p_run,'cut_id',completed.cut_id,'cohort',reference_set.sampling->>'cohort','tasks',tasks,'gaps',gaps,'match_bindings',matched_bindings);
END $$;
REVOKE ALL ON FUNCTION eval.source_record_gap_evidence(bigint,bigint,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.source_record_gap_evidence(bigint,bigint,bigint,bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.validate_source_record_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_release text; reference_release text; item jsonb; payload jsonb; frozen jsonb; report_schema json; applicability jsonb;
BEGIN
 SELECT release_id INTO STRICT reference_release FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 SELECT c.release_id INTO STRICT source_release FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id WHERE c.run_id=p_run AND r.project_id=p_project;
 PERFORM sem.require_execution_operation(source_release,'reference_record_grade');
 applicability:=eval.record_reference_applicability(p_project,p_run,p_set);
 IF p_result->'applicability' IS DISTINCT FROM applicability OR p_result->>'reference_release_id' IS DISTINCT FROM reference_release THEN
  RAISE EXCEPTION 'record grade reference applicability differs from native authenticated correspondence' USING ERRCODE='23514'; END IF;
 SELECT convert_from(content,'UTF8')::json INTO STRICT report_schema FROM sem.artifact
 WHERE release_id=source_release AND artifact_name='json_schema/ReferenceRecordEvaluationReport';
 IF NOT public.json_matches_schema(report_schema,p_result::json)
  OR p_snapshot IS DISTINCT FROM eval.native_reference_snapshot(p_set)
  OR jsonb_array_length(p_snapshot)=0
  OR jsonb_array_length(p_snapshot)<>(SELECT count(*) FROM eval.reference_unit WHERE set_id=p_set)
  OR jsonb_array_length(p_result->'units')<>jsonb_array_length(p_snapshot)
  OR (p_result->>'reference_units_scored')::bigint<>jsonb_array_length(p_snapshot) THEN
  RAISE EXCEPTION 'record grade has a malformed report or incomplete frozen snapshot' USING ERRCODE='23514'; END IF;
 -- Bind each reported unit by identity, independently of array order. A same-length
 -- duplicate or foreign unit must not erase an empty/unrouted member of the population.
 IF jsonb_array_length(p_result->'units')<>(SELECT count(DISTINCT reported->>'unit') FROM jsonb_array_elements(p_result->'units') reported)
  OR EXISTS(SELECT FROM jsonb_array_elements(p_result->'units') reported WHERE NOT EXISTS(
   SELECT FROM jsonb_array_elements(p_snapshot) snap
   JOIN eval.reference_unit u ON u.id=(snap->>'unit_id')::bigint AND u.set_id=p_set
   JOIN eval.reference_frame f ON f.id=(snap->>'frame_id')::bigint AND f.pass_id=(snap->>'pass_id')::bigint
   JOIN eval.reference_set s ON s.id=u.set_id
   CROSS JOIN LATERAL jsonb_array_elements(s.sampling->'eligible_units') eligible
   WHERE reported->>'unit'=u.unit_key AND eligible->>'unit_key'=u.unit_key
    AND (eligible->>'source_view_id')::bigint=u.source_view_id
    AND reported->>'origin_group'=eligible->>'origin_group'
    AND reported->>'release_id'=source_release AND reported->>'reference_release_id'=s.release_id
    AND reported->>'guideline_version'=f.source_frame->'evaluation_frame'->>'guideline_version'
    AND reported->>'reference_policy_version'=f.source_frame->'evaluation_frame'->>'reference_policy_version'
    AND reported->>'prediction_policy_version'=f.source_frame->'evaluation_frame'->>'prediction_policy_version')) THEN
  RAISE EXCEPTION 'record grade unit population/origin/version binding differs from frozen snapshot' USING ERRCODE='23514'; END IF;
 IF p_result->>'protocol' IS DISTINCT FROM 'source-record-evaluation-1'
  OR p_result->>'family' IS DISTINCT FROM 'source_records'
  OR p_result->>'comparison_policy' IS DISTINCT FROM 'strict-source-occurrence-1'
  OR p_result->>'release_id' IS DISTINCT FROM source_release
  OR p_result->>'quality_claim' IS DISTINCT FROM 'not_established'
  OR p_result->>'output_realization_id' IS DISTINCT FROM
   (SELECT c.output_realization_id FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id
    WHERE c.run_id=p_run AND c.release_id=source_release AND r.project_id=p_project)
  OR p_result->>'partition' IS DISTINCT FROM (SELECT sampling->>'partition' FROM eval.reference_set WHERE id=p_set)
  OR p_result->>'sampling_digest' IS DISTINCT FROM (SELECT encode(sha256(convert_to(sampling::text,'UTF8')),'hex') FROM eval.reference_set WHERE id=p_set) THEN
  RAISE EXCEPTION 'record grade differs from frozen release/partition/completed publication' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p_snapshot) LOOP
  SELECT convert_from(authored,'UTF8')::jsonb INTO STRICT payload FROM eval.reference_pass WHERE id=(item->>'pass_id')::bigint;
  SELECT source_frame INTO STRICT frozen FROM eval.reference_frame WHERE id=(item->>'frame_id')::bigint AND pass_id=(item->>'pass_id')::bigint;
  PERFORM eval.validate_source_record_reference_frame((item->>'unit_id')::bigint,payload,frozen);
  IF (SELECT reported->'gap_evidence' FROM jsonb_array_elements(p_result->'units') reported
   JOIN eval.reference_unit u ON u.id=(item->>'unit_id')::bigint AND reported->>'unit'=u.unit_key)
   IS DISTINCT FROM eval.source_record_gap_evidence(p_run,(item->>'unit_id')::bigint,
    (item->>'pass_id')::bigint,(item->>'frame_id')::bigint) THEN
   RAISE EXCEPTION 'record gaps differ from complete independent C/native publication evidence' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(p_result->'units') reported JOIN eval.reference_unit u
    ON u.id=(item->>'unit_id')::bigint AND reported->>'unit'=u.unit_key
    WHERE reported->'match_bindings' IS DISTINCT FROM reported->'gap_evidence'->'match_bindings'
     OR EXISTS(SELECT FROM unnest(ARRAY['core','full','evidence']) tier WHERE reported->'matches'->tier IS DISTINCT FROM
      (SELECT COALESCE(jsonb_agg(binding->'reference_record_id' ORDER BY binding->>'reference_record_id'),'[]'::jsonb)
       FROM jsonb_array_elements(reported->'gap_evidence'->'match_bindings') binding WHERE binding->'tiers' ? tier))) THEN
   RAISE EXCEPTION 'record grade matches differ from authenticated original/prediction identities' USING ERRCODE='23514'; END IF;
  IF (SELECT reported->'correspondence' FROM jsonb_array_elements(p_result->'units') reported
   JOIN eval.reference_unit u ON u.id=(item->>'unit_id')::bigint AND reported->>'unit'=u.unit_key)
   IS DISTINCT FROM eval.record_reference_unit_binding(p_run,(item->>'unit_id')::bigint,
    (item->>'pass_id')::bigint,(item->>'frame_id')::bigint)->'views' THEN
   RAISE EXCEPTION 'record grade comparison closure differs from authenticated correspondence' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF p_result ? 'policy_fit' THEN
  PERFORM eval.validate_record_policy_product(p_project,p_run,p_set,p_result->'policy_fit');
 END IF;
 END $$;
REVOKE ALL ON FUNCTION eval.validate_source_record_reference_evaluation(text,bigint,bigint,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.record_source_record_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint;
BEGIN
 PERFORM 1 FROM eval.reference_unit WHERE set_id=p_set FOR UPDATE;
 PERFORM eval.validate_source_record_reference_evaluation(p_project,p_run,p_set,p_snapshot,p_result);
 INSERT INTO eval.reference_evaluation(project_id,run_id,set_id,reference_snapshot,result,content_digest)
 VALUES(p_project,p_run,p_set,p_snapshot,p_result,encode(sha256(convert_to(data.canonical_json(
  jsonb_build_object('snapshot',p_snapshot,'result',p_result)),'UTF8')),'hex')) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_source_record_reference_evaluation(text,bigint,bigint,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_source_record_reference_evaluation(text,bigint,bigint,jsonb,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.require_record_fitting_principal()
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE principal name:=session_user;
BEGIN
 -- Privileges alone are insufficient: refuse evaluator credentials, SET ROLE and role
 -- inheritance that could also reveal calibration/final labels through another route.
 IF NOT pg_has_role(principal,'corpus_sem_fitter','USAGE') OR current_setting('role') NOT IN ('none',principal::text)
  OR pg_has_role(principal,'corpus_sem_evaluator','MEMBER') OR pg_has_role(principal,'corpus_sem_publisher','MEMBER')
  OR EXISTS(SELECT FROM pg_namespace WHERE nspname='sem' AND pg_has_role(principal,nspowner,'MEMBER'))
  OR has_database_privilege(principal,current_database(),'TEMP')
  OR EXISTS(SELECT FROM pg_roles WHERE oid=principal::regrole AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls OR rolreplication))
  OR EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='eval'
   AND c.relkind IN ('r','p','v','m') AND (has_table_privilege(principal,c.oid,'SELECT')
    OR has_any_column_privilege(principal,c.oid,'SELECT')))
  OR EXISTS(SELECT FROM pg_namespace WHERE nspname IN ('sem','data','ops','kb','eval') AND has_schema_privilege(principal,oid,'CREATE')) THEN
  RAISE EXCEPTION 'fitting requires a restricted actual fitting principal' USING ERRCODE='42501'; END IF;
END $$;
REVOKE ALL ON FUNCTION eval.require_record_fitting_principal() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.require_record_fitting_principal() TO corpus_sem_fitter;

CREATE OR REPLACE FUNCTION eval.read_record_fitting_references(p_set bigint,p_prediction_run bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference_set eval.reference_set; result jsonb; snapshot jsonb; item jsonb; payload jsonb; applicability jsonb; target_release text;
BEGIN
 PERFORM eval.require_record_fitting_principal();
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=p_set;
 IF reference_set.sampling->>'record_protocol' IS DISTINCT FROM 'source-record-reference-1'
  OR reference_set.sampling->>'partition' IS DISTINCT FROM 'feature_fit' THEN
  RAISE EXCEPTION 'fitting capability exposes only isolated feature-fit references' USING ERRCODE='42501'; END IF;
 IF p_prediction_run IS NULL THEN
  PERFORM sem.require_execution_operation(reference_set.release_id,'reference_record_fit');
 ELSE
  SELECT c.release_id INTO STRICT target_release FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id
   WHERE c.run_id=p_prediction_run AND r.project_id=reference_set.project_id;
  PERFORM sem.require_execution_operation(target_release,'reference_record_fit');
  applicability:=eval.record_reference_applicability(reference_set.project_id,p_prediction_run,p_set);
 END IF;
 IF (SELECT jsonb_array_length(eval.native_reference_snapshot(p_set)))<>(SELECT count(*) FROM eval.reference_unit WHERE set_id=p_set)
  OR NOT EXISTS(SELECT FROM eval.reference_unit WHERE set_id=p_set) THEN
  RAISE EXCEPTION 'fitting requires every independently sampled unit adjudicated' USING ERRCODE='23514'; END IF;
 snapshot:=eval.native_reference_snapshot(p_set);
 FOR item IN SELECT value FROM jsonb_array_elements(snapshot) LOOP
  SELECT convert_from(authored,'UTF8')::jsonb INTO STRICT payload FROM eval.reference_pass WHERE id=(item->>'pass_id')::bigint;
  PERFORM eval.validate_source_record_reference_frame((item->>'unit_id')::bigint,payload,
   (SELECT source_frame FROM eval.reference_frame WHERE id=(item->>'frame_id')::bigint AND pass_id=(item->>'pass_id')::bigint));
 END LOOP;
 SELECT jsonb_agg(jsonb_build_object('unit_id',u.id,'unit_ref',u.unit_key,'pass_id',p.id,
  'authored',convert_from(p.authored,'UTF8')::jsonb,'content_digest',p.content_digest,
  'source_frame',f.source_frame,'guideline',reference_set.guideline,'sampling',reference_set.sampling)
  ||CASE WHEN p_prediction_run IS NULL THEN '{}'::jsonb ELSE jsonb_build_object('applicability',applicability,
   'prediction_binding',eval.record_reference_unit_binding(p_prediction_run,u.id,p.id,f.id)) END ORDER BY u.id)
 INTO result FROM jsonb_array_elements(snapshot) snap
 JOIN eval.reference_unit u ON u.id=(snap->>'unit_id')::bigint
 JOIN eval.reference_pass p ON p.id=(snap->>'pass_id')::bigint
 JOIN eval.reference_frame f ON f.id=(snap->>'frame_id')::bigint;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.read_record_fitting_references(bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.read_record_fitting_references(bigint,bigint) TO corpus_sem_fitter;

CREATE OR REPLACE FUNCTION eval.read_record_fitting_references(p_set bigint)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT eval.read_record_fitting_references(p_set,NULL::bigint)
$$;
REVOKE ALL ON FUNCTION eval.read_record_fitting_references(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.read_record_fitting_references(bigint) TO corpus_sem_fitter;

-- Source-only packets for independent A/B authors never include production records,
-- factors, public assertions, earlier passes or reference answers.
CREATE OR REPLACE FUNCTION eval.source_record_author_packet(p_unit bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE unit eval.reference_unit; reference_set eval.reference_set; source_frame jsonb;
 selected kb.source_view; context jsonb; contexts jsonb:='[]'; schema jsonb;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit;
 SELECT * INTO STRICT reference_set FROM eval.reference_set WHERE id=unit.set_id;
 PERFORM sem.require_execution_operation(reference_set.release_id,'reference_record_pass');
 source_frame:=unit.context->0;
 PERFORM eval.validate_source_record_reference_frame(p_unit,jsonb_build_object(
  'protocol','source-record-reference-1','release_id',reference_set.release_id,'unit_ref',unit.unit_key,
  'guideline',reference_set.guideline,'reference_policy_version',reference_set.sampling->>'reference_policy_version',
  'prediction_policy_version',reference_set.sampling->>'prediction_policy_version',
  'reason','source-only author packet','records','[]'::jsonb),source_frame);
 FOR selected IN SELECT v.* FROM jsonb_array_elements(source_frame->'source_views') frozen
  JOIN kb.source_view v ON v.id=(frozen->>'id')::bigint ORDER BY v.id LOOP
  SELECT COALESCE(jsonb_object_agg(pointer,native_json),'{}') INTO context FROM ops.read_pdf_published_items(
   selected.native_task_id,selected.native_product_key,selected.native_content_digest,ARRAY(
    SELECT value FROM jsonb_array_elements_text(selected.projection->'items')
    UNION SELECT value FROM jsonb_array_elements_text(COALESCE(selected.projection->'ancestors','[]'))));
  contexts:=contexts||jsonb_build_array(jsonb_build_object('source_view_id',selected.id,'native_items',context));
 END LOOP;
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT schema FROM sem.artifact
 WHERE release_id=reference_set.release_id AND artifact_name='json_schema/ReferenceRecordBatch';
 RETURN jsonb_build_object('protocol','source-record-author-packet-1','unit_id',p_unit,
  'unit_ref',unit.unit_key,'release_id',reference_set.release_id,'guideline',reference_set.guideline,
  'guideline_text',reference_set.sampling->'guideline_text','guideline_digest',reference_set.sampling->'guideline_digest',
  'source_frame',source_frame,'native_contexts',contexts,'authored_schema',schema);
END $$;
REVOKE ALL ON FUNCTION eval.source_record_author_packet(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.source_record_author_packet(bigint) TO corpus_sem_evaluator;
