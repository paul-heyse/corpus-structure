-- Independent operation correctness development fits; no whole-reading or truth authority.
CREATE OR REPLACE FUNCTION eval.defining_text_event_features(
 p_task bigint,p_contribution text,p_view bigint
)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH view_projection AS MATERIALIZED (
  SELECT projection FROM kb.source_view WHERE id=p_view
 ), anchors AS (
  SELECT e.role,m.span
  FROM kb.source_contribution_endpoint e
  JOIN kb.source_contribution c ON c.task_id=e.task_id AND c.contribution_id=e.endpoint_id
    AND c.source_view_id=p_view AND c.kind='proposal'
    AND c.semantic_type='definition.'||e.role
  LEFT JOIN kb.source_contribution_anchor a ON a.task_id=c.task_id AND a.contribution_id=c.contribution_id
  LEFT JOIN LATERAL (
   SELECT CASE WHEN count(*)=1 THEN (array_agg(int8range(
    (x->>'start')::bigint+a."start",(x->>'start')::bigint+a."end")))[1] END AS span
   FROM view_projection v,LATERAL jsonb_array_elements(v.projection->'pieces') x
   WHERE a.source_view_id=p_view AND a.space='native' AND a.precision='exact'
    AND x->>'kind'='native_text'
    AND COALESCE(x->>'source_field','text')='text' AND NOT x ? 'cell_index'
    AND x->>'item_ref'=a.pointer
    AND a."end"<=(x->>'end')::bigint-(x->>'start')::bigint
  ) m ON true
  WHERE e.task_id=p_task AND e.contribution_id=p_contribution AND e.role IN ('term','defining_text')
 ), roles AS (
  SELECT role,range_agg(span) AS spans FROM anchors GROUP BY role HAVING bool_and(span IS NOT NULL)
 ), extents AS (
  SELECT role,min(lower(x)) AS start_,max(upper(x)) AS end_,
   sum(upper(x)-lower(x))::double precision AS length_
  FROM roles CROSS JOIN LATERAL unnest(spans) x GROUP BY role
 ), passage AS (
  SELECT projection->>'text' AS body FROM view_projection
 )
 SELECT COALESCE((
  SELECT jsonb_build_object('features',jsonb_build_array(
   ln(1.0+t.length_),ln(1.0+d.length_),
   CASE WHEN d.start_>=t.end_ THEN d.start_-t.end_
        WHEN t.start_>=d.end_ THEN d.end_-t.start_ ELSE 0 END::double precision/length(p.body),
   CASE WHEN regexp_replace(casefold(p.body COLLATE pg_catalog.pg_unicode_fast),
    U&'[\0009\000A\000B\000C\000D\0020\0085\00A0\1680\2000-\200A\2028\2029\202F\205F\3000]+',' ','g')
    ~ '\m(is defined as|is called|we call|denoted by)\M' THEN 1 ELSE 0 END))
  FROM passage p,extents t,extents d
  WHERE t.role='term' AND d.role='defining_text' AND length(p.body)>0
   AND t.end_<=length(p.body) AND d.end_<=length(p.body)
 ),jsonb_build_object('reason',CASE
   WHEN EXISTS(SELECT FROM passage WHERE length(body)>0) THEN 'incomparable_endpoint_anchors'
   ELSE 'missing_common_passage' END))
$$;
REVOKE ALL ON FUNCTION eval.defining_text_event_features(bigint,text,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.defining_text_event_scope(p_task bigint,p_contribution text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 WITH relation AS (
  SELECT c.task_id,c.contribution_id,v.native_build_id,
   r.body->'contributions'->c.position::integer AS retained
  FROM kb.source_contribution c JOIN kb.source_view v ON v.id=c.source_view_id
  JOIN ops.task_result r ON r.task_id=c.task_id
  JOIN kb.source_contribution_operation o ON o.task_id=c.task_id AND o.operation_key=c.operation_key
  WHERE c.task_id=p_task AND c.contribution_id=p_contribution AND c.kind='relation'
   AND c.semantic_type='definition.defining_text_attachment'
   AND o.question='propose_returned_role_attachments'
 ), owner AS (
  SELECT DISTINCT e.role,coalesce(n.section_pointer,'#/body') AS section_pointer
  FROM relation r JOIN kb.source_contribution_endpoint e
   ON e.task_id=r.task_id AND e.contribution_id=r.contribution_id
  JOIN kb.source_contribution_anchor a ON a.task_id=e.task_id AND a.contribution_id=e.endpoint_id
  JOIN kb.pdf_record_access n ON n.product_id=r.native_build_id AND n.revision_id=r.native_build_id
   AND n.pointer=regexp_replace(a.pointer,'/data/table_cells/[0-9]+$','') AND n.content_layer='body'
  WHERE e.role IN ('term','defining_text') AND a.space='native' AND a.precision='exact'
 ), scope_by_role AS (
  SELECT role,jsonb_agg(section_pointer ORDER BY section_pointer COLLATE "C") AS sections
  FROM owner GROUP BY role
 )
 SELECT jsonb_strip_nulls(jsonb_build_object('kind','native_section_scope',
   'term',t.sections,'defining_text',d.sections,
   'declared_scope',r.retained->'component'->'scope',
   'effective_version',r.retained->'component'->'effective_version'))
 FROM relation r CROSS JOIN scope_by_role t CROSS JOIN scope_by_role d
 WHERE t.role='term' AND d.role='defining_text'
$$;
REVOKE ALL ON FUNCTION eval.defining_text_event_scope(bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.defining_text_event_scope(bigint,text) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.defining_text_event_identity(p_task bigint,p_contribution text)
RETURNS text LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH relation AS (
  SELECT c.task_id,c.contribution_id,v.document_id,v.native_content_digest
  FROM kb.source_contribution c JOIN kb.source_view v ON v.id=c.source_view_id
  JOIN kb.source_contribution_operation o ON o.task_id=c.task_id AND o.operation_key=c.operation_key
  WHERE c.task_id=p_task AND c.contribution_id=p_contribution AND c.kind='relation'
   AND c.semantic_type='definition.defining_text_attachment'
   AND o.question='propose_returned_role_attachments'
 ), ranges AS (
  SELECT e.role,a.pointer,range_agg(int8range(a."start",a."end")) AS spans
  FROM relation r JOIN kb.source_contribution_endpoint e
   ON e.task_id=r.task_id AND e.contribution_id=r.contribution_id
  JOIN kb.source_contribution_anchor a ON a.task_id=e.task_id AND a.contribution_id=e.endpoint_id
  WHERE e.role IN ('term','defining_text') AND a.space='native' AND a.precision='exact'
  GROUP BY e.role,a.pointer
 ), endpoints AS (
  SELECT role,jsonb_agg(jsonb_build_array(pointer,lower(x),upper(x))
   ORDER BY pointer COLLATE "C",lower(x),upper(x)) AS anchors
  FROM ranges CROSS JOIN LATERAL unnest(spans) x GROUP BY role
 )
 SELECT 'defining-text-event:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
  'physical-defining-text-attachment-2',r.document_id,r.native_content_digest,
  t.anchors,d.anchors,scope.value)),
  'UTF8')),'hex')
 FROM relation r CROSS JOIN endpoints t CROSS JOIN endpoints d
 CROSS JOIN LATERAL (SELECT eval.defining_text_event_scope(r.task_id,r.contribution_id) AS value) scope
 WHERE t.role='term' AND d.role='defining_text' AND scope.value IS NOT NULL
$$;
REVOKE ALL ON FUNCTION eval.defining_text_event_identity(bigint,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.count_defining_text_events(p_project text,p_run bigint,p_cut bigint)
RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT count(DISTINCT eval.defining_text_event_identity(c.task_id,c.contribution_id))
 FROM ops.completed_result cr JOIN ops.run r ON r.id=cr.run_id
 JOIN ops.cut_task ct ON ct.cut_id=cr.cut_id
 JOIN kb.source_contribution c ON c.task_id=ct.origin_task_id
 WHERE cr.run_id=p_run AND cr.cut_id=p_cut AND r.project_id=p_project
  AND c.kind='relation' AND c.semantic_type='definition.defining_text_attachment'
$$;
REVOKE ALL ON FUNCTION ops.count_defining_text_events(text,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.count_defining_text_events(text,bigint,bigint) TO corpus_sem_reader;

CREATE OR REPLACE FUNCTION eval.operation_event_fit_frame(p_project text,p_evaluation bigint,p_event text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE grade eval.reference_evaluation; reference_set eval.reference_set; completed ops.completed_result;
 unit_report jsonb; assessed jsonb; unit eval.reference_unit; adjudication jsonb; reference_case jsonb;
 selected ops.task; contribution kb.source_contribution; detail jsonb; operation kb.source_contribution_operation;
 observations jsonb:='[]'; event_ids jsonb:='[]'; versions jsonb:='[]'; identity text; head_exact integer; tail_exact integer;
 native_score numeric; frame jsonb; rubric jsonb:='[]'; option jsonb; feature_result jsonb;
 semantic_type_ text; event_version_ text; head_role text; tail_role text; feature_names jsonb;
 unavailable jsonb:='[]'; observed_events jsonb:='[]'; defining_text boolean; origin_group_ text;
 actual_endpoints jsonb; authenticated_judgment text; sightings jsonb:='[]'; selected_sightings jsonb;
 actual_roles jsonb; actual_facets jsonb; facets jsonb; disagreements jsonb;
 facet_key text; facet_case jsonb; facet_grade text; pass_a jsonb; pass_b jsonb;

BEGIN
 IF p_event IS NULL OR p_event NOT IN ('defined_by_correctness','defining_text_attachment_correctness') THEN
  RAISE EXCEPTION 'unknown operation event' USING ERRCODE='23514'; END IF;
 defining_text:=p_event='defining_text_attachment_correctness';
 IF defining_text THEN
  semantic_type_:='definition.defining_text_attachment';
  event_version_:='defining-text-attachment-scope-features-2';
  head_role:='term'; tail_role:='defining_text';
  feature_names:='["term_log_length","content_log_length","signed_passage_separation","declared_cue"]';
 ELSE
  semantic_type_:='relation.defined_by'; event_version_:='defined-by-exact-endpoints-scope-1';
  head_role:='head'; tail_role:='tail';
  feature_names:='["native_score","native_score_present","head_exact_endpoint_count","tail_exact_endpoint_count"]';
 END IF;
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
  IF defining_text THEN
   IF unit.context->0->'evaluation_frame'->>'rubric_version'
      IS DISTINCT FROM 'nce12-attachment-role-direction-scope-2' THEN
    RAISE EXCEPTION 'attachment fitting requires the protected role/direction/scope v2 rubric'
     USING ERRCODE='23514';
   END IF;
   SELECT u->>'origin_group' INTO STRICT origin_group_
   FROM jsonb_array_elements(reference_set.sampling->'eligible_units') u
   WHERE u->>'unit_key'=unit.unit_key;
   IF nullif(origin_group_,'') IS NULL THEN
    RAISE EXCEPTION 'defining-text event requires frozen source origin' USING ERRCODE='23514'; END IF;
  END IF;
  rubric:=rubric||jsonb_build_array(unit.context->0->'evaluation_frame'->'rubric_version');
  SELECT convert_from(p.authored,'UTF8')::jsonb INTO STRICT adjudication FROM eval.reference_pass p
   JOIN jsonb_array_elements(grade.reference_snapshot) s ON (s->>'pass_id')::bigint=p.id
   WHERE p.unit_id=unit.id AND p.pass_kind='C';
  IF defining_text THEN
   SELECT convert_from(p.authored,'UTF8')::jsonb INTO STRICT pass_a FROM eval.reference_pass p
   WHERE p.id=(adjudication->'adjudication_passes'->>0)::bigint AND p.unit_id=unit.id AND p.pass_kind='A';
   SELECT convert_from(p.authored,'UTF8')::jsonb INTO STRICT pass_b FROM eval.reference_pass p
   WHERE p.id=(adjudication->'adjudication_passes'->>1)::bigint AND p.unit_id=unit.id AND p.pass_kind='B';
  END IF;
  FOR assessed IN SELECT value FROM jsonb_array_elements(unit_report->'cases') ORDER BY value->>'case_id' LOOP
   IF assessed->>'contribution_id' IS NULL OR assessed->>'facet' IS DISTINCT FROM p_event THEN CONTINUE; END IF;
   SELECT c.* INTO contribution FROM kb.source_contribution c JOIN ops.task t
    ON t.run_id=grade.run_id AND COALESCE(t.reused_task_id,t.id)=c.task_id
    JOIN ops.cut_task ct ON ct.task_id=t.id AND ct.cut_id=completed.cut_id
     AND ct.origin_task_id=c.task_id
    WHERE c.contribution_id=assessed->>'contribution_id' AND c.source_view_id=unit.source_view_id
     AND c.kind='relation' AND c.semantic_type=semantic_type_
     AND (NOT defining_text OR EXISTS(SELECT FROM kb.source_contribution_operation o
      WHERE o.task_id=c.task_id AND o.operation_key=c.operation_key
       AND o.question=unit.context->0->'evaluation_frame'->>'operation_question'
       AND o.operation_version=unit.context->0->'evaluation_frame'->>'operation_version'))
    ORDER BY c.task_id,t.id LIMIT 1;
   IF NOT FOUND THEN CONTINUE; END IF;
   SELECT value INTO STRICT reference_case FROM jsonb_array_elements(adjudication->'cases')
    WHERE value->>'case_id'=assessed->>'case_id';
   IF reference_case->>'contribution_id' IS DISTINCT FROM contribution.contribution_id
    OR reference_case->>'contribution_kind' IS DISTINCT FROM 'relation'
    OR NOT (unit.context->0->'evaluation_frame'->'contribution_ids' ? contribution.contribution_id) THEN
    RAISE EXCEPTION 'correctness event must name its exact frozen emitted relation' USING ERRCODE='23514'; END IF;
   -- A supported event must constrain exact endpoint roles and native anchor scopes.
   IF reference_case->>'judgment'='supported' AND reference_case->>'source_state'='stated' THEN
    IF jsonb_array_length(reference_case->'alternatives')=0 THEN
     RAISE EXCEPTION 'operation event support requires exact endpoint alternatives' USING ERRCODE='23514'; END IF;
    FOR option IN SELECT value FROM jsonb_array_elements(reference_case->'alternatives') LOOP
     IF option->>'semantic_type' IS DISTINCT FROM semantic_type_
      OR jsonb_typeof(option->'endpoint_semantics') IS DISTINCT FROM 'array'
      OR jsonb_array_length(option->'endpoint_semantics')<>2
      OR (SELECT count(DISTINCT e->>'role') FROM jsonb_array_elements(option->'endpoint_semantics') e
       WHERE e->>'role' IN (head_role,tail_role) AND jsonb_typeof(e->'anchor_ids')='array'
        AND jsonb_array_length(e->'anchor_ids')>0)<>2 THEN
      RAISE EXCEPTION 'operation event alternatives must bind both exact endpoint scopes' USING ERRCODE='23514'; END IF;
    END LOOP;
   END IF;
   identity:=contribution.task_id::text||':'||contribution.contribution_id;
   IF NOT defining_text THEN
    IF observed_events ? identity THEN RAISE EXCEPTION 'one emitted event cannot be weighted twice' USING ERRCODE='23514'; END IF;
    observed_events:=observed_events||jsonb_build_array(identity);
   END IF;
   SELECT tr.body->'contributions'->contribution.position::integer INTO STRICT detail FROM ops.task_result tr WHERE tr.task_id=contribution.task_id;
   SELECT * INTO STRICT operation FROM kb.source_contribution_operation WHERE task_id=contribution.task_id AND operation_key=contribution.operation_key;
   IF defining_text THEN
    IF operation.question<>'propose_returned_role_attachments' THEN
     RAISE EXCEPTION 'defining-text event requires its group-derived producer' USING ERRCODE='23514'; END IF;
    IF COALESCE(reference_case->>'expectation_mode','structure')<>'structure' THEN
     RAISE EXCEPTION 'defining-text fitting requires an emitted attachment judgment' USING ERRCODE='23514'; END IF;
    SELECT jsonb_agg(jsonb_build_object('role',e.role,'fields','{}'::jsonb,'anchor_ids',(
      SELECT jsonb_agg(a.anchor_id ORDER BY a.position)
      FROM kb.source_contribution_anchor a WHERE a.task_id=e.task_id
       AND a.contribution_id=e.endpoint_id AND a.source_view_id=contribution.source_view_id
       AND a.precision='exact' AND a.space='native')) ORDER BY e.position)
    INTO actual_endpoints
    FROM kb.source_contribution_endpoint e
    WHERE e.task_id=contribution.task_id AND e.contribution_id=contribution.contribution_id;
    authenticated_judgment:=CASE
     WHEN reference_case->>'judgment'='unassessed' OR reference_case->>'source_state'='uninspected'
      THEN 'unassessed'
     WHEN reference_case->>'judgment'='ambiguous' OR reference_case->>'source_state'='unresolved'
      THEN 'ambiguous'
     WHEN reference_case->>'judgment'='supported' AND reference_case->>'source_state'='stated'
      AND EXISTS(SELECT FROM jsonb_array_elements(reference_case->'alternatives') a
       WHERE a=jsonb_build_object('semantic_type',semantic_type_,'endpoint_semantics',actual_endpoints))
      THEN 'supported'
     ELSE 'unsupported' END;
    IF assessed->>'judgment' IS DISTINCT FROM authenticated_judgment THEN
     RAISE EXCEPTION 'defining-text grade differs from authored exact attachment evidence' USING ERRCODE='23514'; END IF;
    SELECT jsonb_object_agg(e->>'role',e->'anchor_ids') INTO actual_roles
    FROM jsonb_array_elements(actual_endpoints) e;
    actual_facets:=jsonb_build_object('attachment_head',actual_roles->'term',
     'attachment_tail',actual_roles->'defining_text','attachment_scope',
     eval.defining_text_event_scope(contribution.task_id,contribution.contribution_id),
     'attachment_direction',(SELECT jsonb_agg(e->'role' ORDER BY ord)
      FROM jsonb_array_elements(actual_endpoints) WITH ORDINALITY x(e,ord)));
    facets:='{}'; disagreements:='[]';
    FOREACH facet_key IN ARRAY ARRAY['attachment_head','attachment_tail','attachment_direction','attachment_scope'] LOOP
     SELECT value INTO STRICT facet_case FROM jsonb_array_elements(adjudication->'cases')
     WHERE value->>'contribution_id'=contribution.contribution_id AND value->>'facet'=facet_key;
     facet_grade:=CASE
      WHEN facet_case->>'judgment'='unassessed' OR facet_case->>'source_state'='uninspected' THEN 'unassessed'
      WHEN facet_case->>'judgment'='ambiguous' OR facet_case->>'source_state'='unresolved' THEN 'ambiguous'
      WHEN facet_case->>'judgment'='supported' AND facet_case->>'source_state'='stated'
       AND EXISTS(SELECT FROM jsonb_array_elements(facet_case->'alternatives') a
        WHERE a->facet_key=actual_facets->facet_key) THEN 'supported'
      ELSE 'unsupported' END;
     IF NOT EXISTS(SELECT FROM jsonb_array_elements(unit_report->'cases') c
      WHERE c->>'case_id'=facet_case->>'case_id' AND c->>'contribution_id'=contribution.contribution_id
       AND c->>'facet'=facet_key AND c->>'judgment'=facet_grade) THEN
      RAISE EXCEPTION 'attachment facet differs from exact authored alternatives' USING ERRCODE='23514';
     END IF;
     facets:=facets||jsonb_build_object(facet_key,facet_grade);
     IF EXISTS(SELECT FROM jsonb_array_elements(pass_a->'cases') a
      CROSS JOIN jsonb_array_elements(pass_b->'cases') b
      WHERE a->>'contribution_id'=contribution.contribution_id AND b->>'contribution_id'=a->>'contribution_id'
       AND a->>'facet'=facet_key AND b->>'facet'=facet_key
       AND ((a->>'judgment',a->>'source_state') IS DISTINCT FROM (b->>'judgment',b->>'source_state')
        OR NOT ((a->'alternatives') @> (b->'alternatives')
         AND (b->'alternatives') @> (a->'alternatives')))) THEN
      disagreements:=disagreements||jsonb_build_array(facet_key);
     END IF;
    END LOOP;
    IF authenticated_judgment IS DISTINCT FROM (CASE
     WHEN 'unsupported' IN (SELECT value FROM jsonb_each_text(facets)) THEN 'unsupported'
     WHEN 'ambiguous' IN (SELECT value FROM jsonb_each_text(facets)) THEN 'ambiguous'
     WHEN 'unassessed' IN (SELECT value FROM jsonb_each_text(facets)) THEN 'unassessed'
     ELSE 'supported' END) THEN
     RAISE EXCEPTION 'attachment label disagrees with adjudicated role/direction/scope facets' USING ERRCODE='23514';
    END IF;
    versions:=versions||jsonb_build_array(jsonb_build_object('question',operation.question,'operation_version',operation.operation_version));
    identity:=eval.defining_text_event_identity(contribution.task_id,contribution.contribution_id);
    IF identity IS NULL THEN
     RAISE EXCEPTION 'defining-text event lacks physical endpoint identity' USING ERRCODE='23514';
    END IF;
    feature_result:=eval.defining_text_event_features(contribution.task_id,contribution.contribution_id,contribution.source_view_id);
    sightings:=sightings||jsonb_build_array(jsonb_build_object('event_id',identity,
     'contribution_id',contribution.contribution_id,'origin_task_id',contribution.task_id,
     'source_view_id',unit.source_view_id,
     'source_key',(SELECT key FROM kb.source_view WHERE id=unit.source_view_id),
     'origin_group',origin_group_,
     'judgment',authenticated_judgment,'facets',facets,'disagreements',disagreements)||feature_result);
    CONTINUE;
   ELSE
   SELECT count(DISTINCT e.endpoint_id) FILTER(WHERE e.role='head' AND a.precision='exact'),
    count(DISTINCT e.endpoint_id) FILTER(WHERE e.role='tail' AND a.precision='exact') INTO head_exact,tail_exact
    FROM kb.source_contribution_endpoint e LEFT JOIN kb.source_contribution_anchor a
     ON a.task_id=e.task_id AND a.contribution_id=e.endpoint_id
    WHERE e.task_id=contribution.task_id AND e.contribution_id=contribution.contribution_id;
   native_score:=CASE WHEN detail->>'score_state'='native' THEN data.record_source_float(detail->'score')::numeric ELSE 0 END;
   IF native_score IS NULL OR native_score<0 OR native_score>1 THEN RAISE EXCEPTION 'invalid finite native relation score' USING ERRCODE='23514'; END IF;
    feature_result:=jsonb_build_object('features',jsonb_build_array(
      native_score,CASE WHEN detail->>'score_state'='native' THEN 1 ELSE 0 END,head_exact,tail_exact));
   END IF;
   observations:=observations||jsonb_build_array(jsonb_build_object('event_id',identity,
    'contribution_id',contribution.contribution_id,'source_ref',unit.source_view_id::text||':'||contribution.contribution_id,
    'features',feature_result->'features',
    'judgment',assessed->>'judgment'));
   event_ids:=event_ids||jsonb_build_array(identity);
   IF NOT defining_text THEN
    versions:=versions||jsonb_build_array(jsonb_build_object('question',operation.question,'operation_version',operation.operation_version));
   END IF;
  END LOOP;
 END LOOP;
 IF defining_text THEN
  WITH eligible AS (
   SELECT s->>'event_id' AS id,s FROM jsonb_array_elements(sightings) s
  ), representatives AS (
   SELECT DISTINCT ON (id) id,s FROM eligible
   ORDER BY id,(s ? 'features') DESC,(s->>'source_key') COLLATE "C",
    (s->>'origin_task_id')::bigint,s->>'contribution_id'
  ), grades AS (
   SELECT id,CASE
    WHEN bool_or(s->>'judgment'='ambiguous')
      OR (bool_or(s->>'judgment'='supported') AND bool_or(s->>'judgment'='unsupported')) THEN 'ambiguous'
    WHEN bool_or(s->>'judgment'='supported') THEN 'supported'
    WHEN bool_or(s->>'judgment'='unsupported') THEN 'unsupported'
    ELSE 'unassessed' END AS grade,
    jsonb_agg(DISTINCT (s-ARRAY['features','reason','event_id','origin_group','source_key'])
     ORDER BY (s-ARRAY['features','reason','event_id','origin_group','source_key'])) AS provenance
   FROM eligible GROUP BY id
  )
  SELECT coalesce(jsonb_agg(s||jsonb_build_object('judgment',g.grade,'sightings',g.provenance)
    ORDER BY r.id COLLATE "C"),'[]') INTO selected_sightings
  FROM representatives r JOIN grades g USING(id);
  SELECT coalesce(jsonb_agg(jsonb_build_object('event_id',s->'event_id',
   'contribution_id',s->'contribution_id',
   'source_ref',(s->>'source_view_id')||':'||(s->>'contribution_id'),
   'features',s->'features','judgment',s->'judgment','origin_group',s->'origin_group',
   'sightings',s->'sightings') ORDER BY s->>'event_id') FILTER(WHERE s ? 'features'),'[]'),
   coalesce(jsonb_agg(s->'event_id' ORDER BY s->>'event_id') FILTER(WHERE s ? 'features'),'[]'),
   coalesce(jsonb_agg(jsonb_build_object('event_id',s->'event_id','reason',s->'reason',
     'sightings',s->'sightings') ORDER BY s->>'event_id') FILTER(WHERE NOT s ? 'features'),'[]')
  INTO observations,event_ids,unavailable FROM jsonb_array_elements(selected_sightings) s;
 END IF;
 SELECT COALESCE(jsonb_agg(v ORDER BY data.canonical_json(v)),'[]') INTO versions FROM (SELECT DISTINCT value v FROM jsonb_array_elements(versions)) unique_versions;
 frame:=jsonb_build_object('protocol','operation-event-development-1','event',p_event,
  'event_version',event_version_,
  'producer_version',encode(sha256(convert_to(data.canonical_json(versions),'UTF8')),'hex'),
  'rubric_digest',encode(sha256(convert_to(data.canonical_json(rubric),'UTF8')),'hex'),
  'reference_digest',grade.content_digest,'corpus_id',p_project||':'||grade.run_id::text||':'||completed.cut_id::text,
  'feature_names',feature_names,
  'event_ids',event_ids,'observations',observations,'assessment_mode','in_sample_development');
 IF defining_text THEN frame:=frame||jsonb_build_object('feature_unavailable',unavailable); END IF;
 RETURN jsonb_build_object('protocol','native-operation-event-frame-1','project_id',p_project,'evaluation_id',p_evaluation,
  'run_id',grade.run_id,'cut_id',completed.cut_id,'release_id',completed.release_id,'set_id',grade.set_id,
  'evaluation_digest',grade.content_digest,'reference_snapshot',grade.reference_snapshot,
  'source_frame_digest',grade.result->>'frame_digest','frame',frame);
END $$;
REVOKE ALL ON FUNCTION eval.operation_event_fit_frame(text,bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_event_fit_frame(text,bigint,text) TO corpus_sem_evaluator,corpus_sem_fitter;

CREATE OR REPLACE FUNCTION eval.operation_event_fit_frame(p_project text,p_evaluation bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 RETURN eval.operation_event_fit_frame(p_project,p_evaluation,'defined_by_correctness');
END $$;
REVOKE ALL ON FUNCTION eval.operation_event_fit_frame(text,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_event_fit_frame(text,bigint) TO corpus_sem_evaluator,corpus_sem_fitter;

CREATE OR REPLACE FUNCTION eval.record_operation_event_fit(p_project text,p_evaluation bigint,p_frame jsonb,p_result jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE actual jsonb; result_id bigint; frame_digest text; parameters jsonb; item jsonb; n integer;
BEGIN
 actual:=eval.operation_event_fit_frame(p_project,p_evaluation,p_frame->'frame'->>'event');
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
  OR (p_result->>'labeled')::integer IS DISTINCT FROM (p_result->>'positive')::integer+(p_result->>'negative')::integer
  OR (p_frame->'frame'->>'event'='defining_text_attachment_correctness'
   AND (p_result->>'origin_groups')::integer IS DISTINCT FROM (SELECT count(DISTINCT o->>'origin_group')
    FROM jsonb_array_elements(p_frame->'frame'->'observations') o)) THEN
  RAISE EXCEPTION 'operation fit result changes the declared event/label population' USING ERRCODE='23514'; END IF;
 parameters:=p_result->'parameters';
 IF p_result->>'status'='fitted' THEN
  IF (p_result->>'positive')::integer<1 OR (p_result->>'negative')::integer<1
   OR parameters->>'event' IS DISTINCT FROM p_frame->'frame'->>'event'
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
   OR jsonb_typeof(parameters->'algorithm'->'regularization_c') IS DISTINCT FROM 'number'
   OR jsonb_typeof(parameters->'algorithm'->'tolerance') IS DISTINCT FROM 'number'
   OR jsonb_typeof(parameters->'algorithm'->'max_iterations') IS DISTINCT FROM 'number'
   OR COALESCE(parameters->'algorithm'->>'max_iterations','') !~ '^[1-9][0-9]*$'
   OR (parameters->'algorithm'->>'regularization_c')::numeric<=0
   OR (parameters->'algorithm'->>'regularization_c')::numeric>1.7976931348623157e308
   OR (parameters->'algorithm'->>'tolerance')::numeric<=0
   OR (parameters->'algorithm'->>'tolerance')::numeric>1.7976931348623157e308
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
  FOR item IN SELECT value FROM jsonb_array_elements(p_result->'predictions') LOOP
   IF NOT item ?& ARRAY['event_id','judgment','prior_probability','fitted_probability']
    OR item-ARRAY['event_id','judgment','prior_probability','fitted_probability']<>'{}'
    OR jsonb_typeof(item->'prior_probability') IS DISTINCT FROM 'number'
    OR NOT (0<=(item->>'prior_probability')::numeric AND (item->>'prior_probability')::numeric<=1)
    OR (p_result->>'status'='fitted' AND (
     jsonb_typeof(item->'fitted_probability') IS DISTINCT FROM 'number'
     OR NOT (0<=(item->>'fitted_probability')::numeric AND (item->>'fitted_probability')::numeric<=1)))
    OR (p_result->>'status'<>'fitted' AND item->'fitted_probability' IS DISTINCT FROM 'null'::jsonb) THEN
    RAISE EXCEPTION 'operation predictions require finite status-qualified probabilities' USING ERRCODE='23514'; END IF;
  END LOOP;
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
  'parameters',fitted.result->'parameters','event',fitted.frame->'frame'->>'event','quality_claim','not_established','assessment_mode','in_sample_development');
END $$;
REVOKE ALL ON FUNCTION eval.read_operation_event_fit(text,bigint,boolean) FROM PUBLIC,corpus_sem_reader;
GRANT EXECUTE ON FUNCTION eval.read_operation_event_fit(text,bigint,boolean) TO corpus_sem_evaluator,corpus_sem_fitter;

-- Ordinary consumers receive parameters through an owned operation in their
-- existing namespace; they never need visibility into the protected eval schema.
CREATE OR REPLACE FUNCTION ops.read_operation_event_parameters(p_project text,p_fit bigint)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT eval.read_operation_event_fit(p_project,p_fit,false)
$$;
REVOKE ALL ON FUNCTION ops.read_operation_event_parameters(text,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_operation_event_parameters(text,bigint) TO corpus_sem_reader,corpus_sem_evaluator,corpus_sem_fitter;
