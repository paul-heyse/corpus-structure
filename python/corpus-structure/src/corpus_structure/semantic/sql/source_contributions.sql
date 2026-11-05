-- Independent source contributions share existing task/report and source custody.
CREATE OR REPLACE FUNCTION ops.source_contribution_occurrence(p_anchors jsonb)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT 'source-occurrence:'||encode(sha256(convert_to(data.canonical_json(COALESCE(
  jsonb_agg((a-'anchor_id'-'binding'-'pin')||jsonb_build_object('pin',jsonb_build_object('product_key',a->'pin'->'product_key','product_digest',a->'pin'->'product_digest')) ORDER BY n),'[]')),'UTF8')),'hex')
 FROM jsonb_array_elements(p_anchors) WITH ORDINALITY x(a,n)
$$;
REVOKE ALL ON FUNCTION ops.source_contribution_occurrence(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_source_contribution_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; v kb.source_view; shape json; op jsonb; contribution jsonb; anchor_ jsonb; ep jsonb;
 anchors jsonb; identities text[]; expected text; previous_ends jsonb; coordinate text; actual bigint;
 declaration json; role_definition jsonb; retained ops.task; binding jsonb; old_view kb.source_view; new_view kb.source_view; old_descriptor jsonb; new_descriptor jsonb; retained_body jsonb; retained_digests jsonb:='{}'; retained_sources jsonb:='{}';
 operation_map jsonb; identity_map jsonb; output_counts jsonb; schemas jsonb:='{}'; allowed_contracts jsonb;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 PERFORM sem.require_execution_operation(t.release_id,'bind_report');
 SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact
 WHERE release_id=t.release_id AND artifact_name='json_schema/SourceObservationBatch';
 IF shape IS NULL OR NOT public.json_matches_schema(shape,p_envelope::json)
  OR NOT p_envelope ? 'contribution_operations' OR NOT p_envelope ? 'contributions'
  OR jsonb_typeof(p_envelope->'contribution_operations') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_envelope->'contributions') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'contribution report differs from released explicit population shape' USING ERRCODE='23514'; END IF;
 IF t.unit_type<>'source_view' OR p_envelope->>'release_id' IS DISTINCT FROM t.release_id
  OR p_envelope->>'unit_key' IS DISTINCT FROM t.unit_key
  OR p_envelope->>'invocation_key' IS DISTINCT FROM t.invocation_key
  OR p_envelope->>'input_hash' IS DISTINCT FROM t.input_hash
  OR NOT EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
   WHERE cfg.id=t.method_config_id AND cfg.config_hash=p_envelope->>'configuration_hash'
    AND m.name=p_envelope->>'method' AND m.version=p_envelope->>'operation_version') THEN
  RAISE EXCEPTION 'contribution report differs from producing task binding' USING ERRCODE='23514'; END IF;
 IF t.status<>'running' AND NOT EXISTS(SELECT FROM ops.task_result WHERE task_id=t.id AND body=p_envelope) THEN
  RAISE EXCEPTION 'contribution report differs from immutable origin result' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=t.unit_id;
 IF p_envelope->>'source' IS NULL OR p_envelope->>'source' NOT IN (t.unit_key,v.key) THEN
  RAISE EXCEPTION 'contribution source differs from selected task/view' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*)<>count(DISTINCT o->>'operation_key') FROM jsonb_array_elements(p_envelope->'contribution_operations') o) THEN
  RAISE EXCEPTION 'duplicate contribution operation identity' USING ERRCODE='23514'; END IF;
 SELECT array_agg(x->>'contribution_id') INTO identities FROM jsonb_array_elements(p_envelope->'contributions') x;
 IF cardinality(identities) IS DISTINCT FROM (SELECT count(DISTINCT x) FROM unnest(identities) x)
  AND cardinality(identities)>0 THEN RAISE EXCEPTION 'duplicate contribution identity' USING ERRCODE='23514'; END IF;
 SELECT jsonb_object_agg(o->>'operation_key',o) INTO operation_map FROM jsonb_array_elements(p_envelope->'contribution_operations') o;
 SELECT COALESCE(jsonb_object_agg(c->>'contribution_id',true),'{}') INTO identity_map FROM jsonb_array_elements(p_envelope->'contributions') c;
 SELECT COALESCE(jsonb_object_agg(key,n),'{}') INTO output_counts FROM (
  SELECT c->>'operation_key' AS key,count(*) AS n FROM jsonb_array_elements(p_envelope->'contributions') c GROUP BY c->>'operation_key') counts;
 SELECT convert_from(content,'UTF8')::jsonb->'contracts' INTO allowed_contracts FROM sem.artifact
  WHERE release_id=t.release_id AND artifact_name='contribution_projection.json';
 FOR op IN SELECT DISTINCT jsonb_build_object('retained_task_id',o->'retained_task_id',
  'retained_result_digest',o->'retained_result_digest','retained_source_bindings',o->'retained_source_bindings')
  FROM jsonb_array_elements(p_envelope->'contribution_operations') o
  WHERE o ? 'retained_task_id' OR o ? 'retained_result_digest' OR o ? 'retained_source_bindings' LOOP
   IF NOT (op ? 'retained_task_id' AND op ? 'retained_result_digest' AND op ? 'retained_source_bindings')
    OR jsonb_array_length(op->'retained_source_bindings')=0 THEN
    RAISE EXCEPTION 'retained operation lacks complete immutable source lineage' USING ERRCODE='23514'; END IF;
   SELECT * INTO STRICT retained FROM ops.task WHERE id=(op->>'retained_task_id')::bigint;
   IF NOT retained_digests ? retained.id::text THEN
    SELECT body INTO STRICT retained_body FROM ops.task_result WHERE task_id=retained.id;
    retained_digests:=retained_digests||jsonb_build_object(retained.id::text,
     encode(sha256(convert_to(data.canonical_json(retained_body),'UTF8')),'hex'));
    retained_sources:=retained_sources||jsonb_build_object(retained.id::text,retained_body->>'source');
   END IF;
   IF retained.status NOT IN ('done','empty','failed') OR retained.reused_task_id IS NOT NULL
    OR NOT EXISTS(SELECT FROM ops.run a JOIN ops.run b ON a.project_id=b.project_id
     WHERE a.id=retained.run_id AND b.id=t.run_id)
    OR retained_digests->>retained.id::text IS DISTINCT FROM op->>'retained_result_digest' THEN
    RAISE EXCEPTION 'retained operation task/result identity differs from immutable source' USING ERRCODE='23514'; END IF;
   FOR binding IN SELECT value FROM jsonb_array_elements(op->'retained_source_bindings') LOOP
    SELECT * INTO STRICT old_view FROM kb.source_view WHERE id=(binding->>'original_source_view_id')::bigint;
    SELECT * INTO STRICT new_view FROM kb.source_view WHERE id=(binding->>'current_source_view_id')::bigint;
    old_descriptor:=jsonb_build_object('document_id',old_view.document_id,'native_task_id',old_view.native_task_id,'native_product_key',old_view.native_product_key,'native_content_digest',old_view.native_content_digest,'section_pointer',old_view.section_pointer,'membership',old_view.membership,'projection_digest',old_view.projection_digest,'recipe_digest',old_view.recipe_digest,'analysis_eligible',old_view.analysis_eligible,'projection',old_view.projection);
    new_descriptor:=jsonb_build_object('document_id',new_view.document_id,'native_task_id',new_view.native_task_id,'native_product_key',new_view.native_product_key,'native_content_digest',new_view.native_content_digest,'section_pointer',new_view.section_pointer,'membership',new_view.membership,'projection_digest',new_view.projection_digest,'recipe_digest',new_view.recipe_digest,'analysis_eligible',new_view.analysis_eligible,'projection',new_view.projection);
    IF old_descriptor IS DISTINCT FROM new_descriptor
     OR encode(sha256(convert_to(data.canonical_json(old_descriptor),'UTF8')),'hex') IS DISTINCT FROM binding->>'physical_digest'
     OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=retained.run_id AND source_view_id=old_view.id)
     OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=t.run_id AND source_view_id=new_view.id)
     OR binding->>'original_source' IS DISTINCT FROM (CASE WHEN old_view.id=retained.unit_id THEN retained_sources->>retained.id::text ELSE old_view.key END)
     OR binding->>'current_source' IS DISTINCT FROM (CASE WHEN new_view.id=t.unit_id THEN p_envelope->>'source' ELSE new_view.key END) THEN
     RAISE EXCEPTION 'retained operation source correspondence differs from selected physical custody' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(op->'retained_source_bindings') b
    WHERE (b->>'original_source_view_id')::bigint=retained.unit_id
     AND (b->>'current_source_view_id')::bigint=t.unit_id) THEN
    RAISE EXCEPTION 'retained operation lacks primary source correspondence' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR op IN SELECT value FROM jsonb_array_elements(p_envelope->'contribution_operations') LOOP
  actual:=COALESCE((output_counts->>(op->>'operation_key'))::bigint,0);
  IF actual<>(op->>'emitted_count')::bigint OR (actual>0 AND op->>'outcome' IN ('empty','failed','skipped','unsupported','not_run'))
   OR (op->>'outcome' IN ('failed','skipped','unsupported','limited','not_run') AND COALESCE(op->>'reason','')='') THEN
   RAISE EXCEPTION 'operation outcome or cardinality differs from actual contribution population' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR contribution IN SELECT value FROM jsonb_array_elements(p_envelope->'contributions') LOOP
  IF contribution->>'standing'<>'retained_private' OR NOT operation_map ? (contribution->>'operation_key') THEN
   RAISE EXCEPTION 'contribution lacks private standing or operation population' USING ERRCODE='23514'; END IF;
  IF NOT schemas ? (contribution->>'contract') THEN
   SELECT convert_from(content,'UTF8')::json INTO declaration FROM sem.artifact
    WHERE release_id=t.release_id AND artifact_name='json_schema/'||(contribution->>'contract');
   IF declaration IS NOT NULL THEN schemas:=schemas||jsonb_build_object(contribution->>'contract',declaration); END IF;
  END IF;
  declaration:=(schemas->(contribution->>'contract'))::json;
  -- Only released domain contracts with an implemented private effect may be named.
  IF declaration IS NULL OR NOT COALESCE(allowed_contracts ? (contribution->>'contract'),false) THEN
   RAISE EXCEPTION 'contribution semantic contract unavailable' USING ERRCODE='23514'; END IF;
  IF NOT public.json_matches_schema(declaration,jsonb_build_object('kind',contribution->'kind','semantic_type',contribution->'semantic_type',
    'effect','retain_private','assessment_event','local-contribution-1')::json) THEN
   RAISE EXCEPTION 'contribution semantics differ from released contract' USING ERRCODE='23514'; END IF;
  IF contribution->'pin' IS DISTINCT FROM jsonb_build_object('source',p_envelope->>'source',
    'native_product_task_id',v.native_task_id,'product_key',v.native_product_key,'product_digest',v.native_content_digest,
    'projection_digest',v.projection_digest,'recipe_digest',v.recipe_digest,'source_view_id',v.id) THEN
   RAISE EXCEPTION 'contribution pin differs from exact selected source view' USING ERRCODE='23514'; END IF;
  anchors:=COALESCE(contribution->'anchors','[]'); previous_ends:='{}';
  IF contribution->>'kind'='occurrence' AND jsonb_array_length(anchors)=0 THEN
   RAISE EXCEPTION 'located contribution occurrence requires source pieces' USING ERRCODE='23514'; END IF;
  IF jsonb_array_length(anchors)=0 AND contribution ? 'occurrence_id' THEN
   RAISE EXCEPTION 'unlocated contribution cannot claim an occurrence identity' USING ERRCODE='23514'; END IF;
  IF jsonb_array_length(anchors)>0 AND contribution->>'occurrence_id' IS DISTINCT FROM ops.source_contribution_occurrence(anchors) THEN
   RAISE EXCEPTION 'contribution occurrence identity differs from actual pieces' USING ERRCODE='23514'; END IF;
  FOR anchor_ IN SELECT value FROM jsonb_array_elements(anchors) LOOP
   IF anchor_->>'space'='selected_projection' THEN RAISE EXCEPTION 'physical occurrence requires canonical native coordinates' USING ERRCODE='23514'; END IF;
   expected:='record-anchor:'||encode(sha256(convert_to(data.canonical_json(
    (anchor_-'anchor_id')||jsonb_build_object('pin',anchor_->'pin'-'source_view_id')),'UTF8')),'hex');
   IF anchor_->>'anchor_id' IS DISTINCT FROM expected THEN
    RAISE EXCEPTION 'contribution source anchor identity differs from contents' USING ERRCODE='23514'; END IF;
   coordinate:=data.canonical_json(jsonb_build_array(anchor_->'pin'-'source_view_id',anchor_->'space',anchor_->'pointer',anchor_->'recognition'));
   IF anchor_->>'precision'='exact' THEN
    IF anchor_->>'start' IS NULL OR anchor_->>'end' IS NULL OR (anchor_->>'start')::bigint < COALESCE((previous_ends->>coordinate)::bigint,0) THEN
     RAISE EXCEPTION 'contribution source pieces overlap or reverse order' USING ERRCODE='23514'; END IF;
    previous_ends:=previous_ends||jsonb_build_object(coordinate,(anchor_->>'end')::bigint);
   END IF;
  END LOOP;
  IF (contribution->>'score_state'='native') IS DISTINCT FROM (c ? 'score') THEN
   RAISE EXCEPTION 'contribution score availability differs from actual score' USING ERRCODE='23514'; END IF;
  expected:='source-contribution:'||encode(sha256(convert_to(data.canonical_json(contribution-'contribution_id'),'UTF8')),'hex');
  IF contribution->>'contribution_id' IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'contribution identity differs from immutable contents' USING ERRCODE='23514'; END IF;
  FOR ep IN SELECT value FROM jsonb_array_elements(COALESCE(contribution->'endpoints','[]')) LOOP
   IF NOT identity_map ? (ep->>'contribution_id') OR ep->>'contribution_id'=contribution->>'contribution_id' THEN
    RAISE EXCEPTION 'contribution endpoint unavailable or self-referential' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(contribution->'members','[]')) x
    WHERE NOT identity_map ? x OR x=contribution->>'contribution_id') THEN
   RAISE EXCEPTION 'contribution member unavailable or self-referential' USING ERRCODE='23514'; END IF;
  IF (contribution->>'kind'='relation' AND jsonb_array_length(COALESCE(contribution->'endpoints','[]'))<2)
   OR (contribution->>'kind'='composite' AND jsonb_array_length(COALESCE(contribution->'members','[]'))=0) THEN
   RAISE EXCEPTION 'relation/composite contribution lacks endpoints/members' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT COALESCE(jsonb_agg(a),'[]') INTO anchors FROM (SELECT DISTINCT a
  FROM jsonb_array_elements(p_envelope->'contributions') c
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c->'anchors','[]')) a) pieces;
 PERFORM ops.validate_source_anchor_coordinates(t.run_id,t.unit_id,p_envelope->>'source',anchors);
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_contribution_report(bigint,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.project_source_contributions(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 INSERT INTO kb.source_contribution_operation(task_id,release_id,operation_key,position,question,operation_version,outcome,inspected_count,emitted_count,report_digest)
 SELECT p_task,p_envelope->>'release_id',o->>'operation_key',n-1,o->>'question',o->>'operation_version',o->>'outcome',
  (o->>'inspected_count')::bigint,(o->>'emitted_count')::bigint,o->>'report_digest'
 FROM jsonb_array_elements(p_envelope->'contribution_operations') WITH ORDINALITY x(o,n);
 INSERT INTO kb.source_contribution(task_id,release_id,contribution_id,position,operation_key,kind,semantic_type,source_view_id,occurrence_id,disposition,standing,score_state)
 SELECT p_task,p_envelope->>'release_id',c->>'contribution_id',n-1,c->>'operation_key',c->>'kind',c->>'semantic_type',
  (c->'pin'->>'source_view_id')::bigint,c->>'occurrence_id',c->>'disposition',c->>'standing',c->>'score_state'
 FROM jsonb_array_elements(p_envelope->'contributions') WITH ORDINALITY x(c,n);
 INSERT INTO kb.source_contribution_anchor(task_id,contribution_id,position,anchor_id,source_view_id,pointer,space,precision,"start","end")
 SELECT p_task,c->>'contribution_id',n-1,a->>'anchor_id',(a->'pin'->>'source_view_id')::bigint,
  a->>'pointer',a->>'space',a->>'precision',(a->>'start')::bigint,(a->>'end')::bigint
 FROM jsonb_array_elements(p_envelope->'contributions') c,
 LATERAL jsonb_array_elements(COALESCE(c->'anchors','[]')) WITH ORDINALITY x(a,n);
 INSERT INTO kb.source_contribution_endpoint(task_id,contribution_id,position,role,endpoint_id)
 SELECT p_task,c->>'contribution_id',n-1,e->>'role',e->>'contribution_id'
 FROM jsonb_array_elements(p_envelope->'contributions') c,
 LATERAL jsonb_array_elements(COALESCE(c->'endpoints','[]')) WITH ORDINALITY x(e,n);
END $$;
REVOKE ALL ON FUNCTION ops.project_source_contributions(bigint,jsonb) FROM PUBLIC;
