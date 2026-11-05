CREATE OR REPLACE FUNCTION ops.complete_task(p_task bigint,p_attempt bigint,p_holder text,p_rows jsonb,p_outcome text,p_error jsonb,p_envelope jsonb DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; r ops.run; item jsonb; ids bigint[] := '{}'; oid bigint; digest text; native_input jsonb; origin kb.observation; view kb.source_view; ancestor kb.source_view;
 source_record jsonb; record_anchor jsonb; record_fields jsonb; record_schema json;
 record_pointer text; record_cell integer; record_node jsonb; record_text text; record_placement ops.pdf_published_revision;
 method ops.method; dimensions jsonb; model_product jsonb; observation_outcome text; provenance text;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id FOR SHARE;
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task FOR UPDATE;
 digest := encode(sha256(convert_to(jsonb_build_array(p_rows,p_outcome,p_error,p_envelope)::text,'UTF8')),'hex');
 IF t.status IN ('done','empty','failed') AND t.attempt=p_attempt AND t.claimed_by=p_holder AND t.result_digest=digest THEN
   RETURN jsonb_build_object('transaction','replay','receipt',jsonb_build_object('task_id',t.id,'run_id',t.run_id,'release_id',t.release_id,'attempt',t.attempt,'protocol',t.status,'result_digest',t.result_digest,'observation_ids',to_jsonb(ARRAY(SELECT id FROM kb.observation WHERE task_id=t.id ORDER BY ordinal))));
 END IF;
 IF r.sealed OR r.status NOT IN ('created','running') OR t.status<>'running' OR t.attempt<>p_attempt OR t.claimed_by IS DISTINCT FROM p_holder THEN
   RAISE EXCEPTION 'task attempt lost or run sealed' USING ERRCODE='P0004';
 END IF;
 IF p_outcome NOT IN ('done','empty','failed') OR (p_outcome='done')<>(jsonb_array_length(p_rows)>0 OR COALESCE(jsonb_array_length(NULLIF(p_envelope->'records','null'::jsonb)),0)>0 OR COALESCE(jsonb_array_length(NULLIF(p_envelope->'contributions','null'::jsonb)),0)>0 OR NULLIF(p_envelope->'structural_product','null'::jsonb) IS NOT NULL) OR (p_outcome='failed')<>(p_error<>'null'::jsonb) THEN
   RAISE EXCEPTION 'inconsistent terminal outcome';
 END IF;
 SELECT m.* INTO STRICT method FROM ops.method m JOIN ops.method_config config ON config.method_id=m.id WHERE config.id=t.method_config_id;
 SELECT convert_from(body,'UTF8')::jsonb INTO STRICT model_product FROM sem.registry_row
 WHERE release_id=t.release_id AND kind='execution_model';
 SELECT jsonb_object_agg(d->>'id',domain->'values') INTO dimensions
 FROM jsonb_array_elements(model_product->'operations') operation,
 LATERAL jsonb_array_elements(operation->'result_dimensions') d,
 jsonb_array_elements(model_product->'outcome_domains') domain
 WHERE operation->>'id'='configure_method' AND domain->>'id'=d->>'outcome_domain';
 IF p_envelope ? 'outcome' AND NOT coalesce(dimensions->(method.name||'/result.outcome') ? (p_envelope->>'outcome'),false) THEN
  RAISE EXCEPTION 'method result outcome is not admitted by its release' USING ERRCODE='23514'; END IF;
 IF NULLIF(p_envelope->'structural_product','null'::jsonb) IS NOT NULL THEN
  PERFORM ops.validate_structural_product_report(t.id,p_envelope);
 END IF;
 -- {source_record_guard}
 IF p_envelope ? 'contribution_operations' OR p_envelope ? 'contributions' THEN
  IF p_envelope->>'outcome' IS DISTINCT FROM (CASE p_outcome WHEN 'done' THEN 'produced' ELSE p_outcome END) THEN
   RAISE EXCEPTION 'contribution report differs from producing task outcome' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_source_contribution_report(t.id,p_envelope);
 END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p_rows) LOOP
   observation_outcome:=coalesce(item->>'outcome','produced');
   IF NOT coalesce(dimensions->(method.name||'/observation.family') ? (item->>'kind'),false)
      OR NOT coalesce(dimensions->(method.name||'/observation.outcome') ? observation_outcome,false) THEN
    RAISE EXCEPTION 'observation family/outcome is not admitted by its method release' USING ERRCODE='23514'; END IF;
   IF item->>'payload_definition'='SourceObservation' THEN
    IF item->'payload'->>'family' IS DISTINCT FROM item->>'kind'
       OR item->'payload'->>'outcome' IS DISTINCT FROM observation_outcome THEN
     RAISE EXCEPTION 'observation dimensions differ from its bound report' USING ERRCODE='23514'; END IF;
    provenance:=item->'payload'->>'confidence_source';
    IF provenance IS NOT NULL AND NOT coalesce(dimensions->(method.name||'/observation.confidence_source') ? provenance,false) THEN
     RAISE EXCEPTION 'observation confidence provenance is not admitted by its method release' USING ERRCODE='23514'; END IF;
   END IF;
   IF t.unit_type='source_view' AND (item->>'source_view_id')::bigint IS DISTINCT FROM t.unit_id THEN
    RAISE EXCEPTION 'native observation differs from producing source-view task unit' USING ERRCODE='23514'; END IF;
   IF item->>'rendition_id' IS NOT NULL OR item->>'segment_id' IS NOT NULL OR item->>'span_id' IS NOT NULL THEN
    RAISE EXCEPTION 'observation requires current SourceView custody' USING ERRCODE='23514'; END IF;
   IF item->>'source_view_id' IS NOT NULL THEN
    IF item->>'rendition_id' IS NOT NULL OR item->>'span_id' IS NOT NULL OR item->>'segment_id' IS NOT NULL OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=t.run_id AND source_view_id=(item->>'source_view_id')::bigint) THEN
     RAISE EXCEPTION 'native observation is outside run or aliases coordinates' USING ERRCODE='23514'; END IF;
    SELECT * INTO STRICT view FROM kb.source_view WHERE id=(item->>'source_view_id')::bigint;
    FOR native_input IN SELECT value FROM jsonb_array_elements(COALESCE(item->'payload'->'inputs','[]')) LOOP
     -- {native_input_shape_guard}
     SELECT * INTO STRICT origin FROM kb.observation WHERE release_id=t.release_id AND observation_key=native_input->>'observation_key';
     IF NOT EXISTS(SELECT FROM ops.task selected WHERE selected.run_id=t.run_id AND (selected.id=origin.task_id OR selected.reused_task_id=origin.task_id) AND selected.status IN ('done','empty','reused')) THEN
      RAISE EXCEPTION 'native observation input is not a selected completed source' USING ERRCODE='23514'; END IF;
     SELECT * INTO STRICT ancestor FROM kb.source_view WHERE id=origin.source_view_id;
     IF ancestor.native_task_id<>view.native_task_id OR ancestor.native_product_key<>view.native_product_key OR ancestor.native_content_digest<>view.native_content_digest
       OR ancestor.native_build_id IS DISTINCT FROM view.native_build_id
       OR ancestor.native_revision_id IS DISTINCT FROM view.native_revision_id
       OR (native_input->>'role'='native_parent_context' AND NOT(view.projection->'ancestors' ? ancestor.section_pointer))
       OR (native_input->>'role'<>'native_parent_context' AND ancestor.id<>view.id)
       OR (native_input->>'role'='native_analysis' AND origin.kind<>'record') THEN
      RAISE EXCEPTION 'native observation input differs from its declared source relation' USING ERRCODE='23514'; END IF;
    END LOOP;
    IF item->'payload'->>'native_pointer' IS NOT NULL AND NOT EXISTS(SELECT FROM kb.pdf_record_access n WHERE n.product_id=view.native_build_id AND n.revision_id=view.native_revision_id AND n.pointer=item->'payload'->>'native_pointer' AND view.projection->'items' ? n.pointer) THEN
     RAISE EXCEPTION 'native observation pointer outside selected view' USING ERRCODE='23514', DETAIL='{"protocol":"corpus-invariant-1","guard":"native_source_address","version":"2","invariant":"published_document_address"}'; END IF;
    IF num_nonnulls(item->'payload'->>'projected_start',item->'payload'->>'projected_end') NOT IN (0,2)
      OR num_nonnulls(item->'payload'->>'recognized_start',item->'payload'->>'recognized_end') NOT IN (0,2)
      OR (item->'payload'->>'recognized_start' IS NOT NULL AND NOT EXISTS(SELECT FROM kb.pdf_record_access n WHERE n.product_id=view.native_build_id AND n.revision_id=view.native_revision_id AND n.pointer=item->'payload'->>'native_pointer' AND 0<=(item->'payload'->>'recognized_start')::bigint AND (item->'payload'->>'recognized_start')::bigint<(item->'payload'->>'recognized_end')::bigint AND (item->'payload'->>'recognized_end')::bigint<=char_length(n.text))) THEN
     RAISE EXCEPTION 'native observation extent is not a qualified native/projected range' USING ERRCODE='23514', DETAIL='{"protocol":"corpus-invariant-1","guard":"native_source_address","version":"2","invariant":"published_document_address"}'; END IF;
    IF item->'payload'->>'projected_start' IS NOT NULL AND NOT EXISTS(SELECT FROM kb.source_view v WHERE v.id=(item->>'source_view_id')::bigint AND 0<=(item->'payload'->>'projected_start')::bigint AND (item->'payload'->>'projected_start')::bigint<(item->'payload'->>'projected_end')::bigint AND (item->'payload'->>'projected_end')::bigint<=char_length(v.projection->>'text')) THEN
     RAISE EXCEPTION 'native projected observation outside text' USING ERRCODE='23514'; END IF;
   END IF;
   INSERT INTO kb.observation(task_id,release_id,observation_key,ordinal,kind,payload_definition,payload,rendition_id,segment_id,span_id,score,outcome,source_view_id)
   VALUES(t.id,t.release_id,item->>'observation_key',(item->>'ordinal')::bigint,item->>'kind',item->>'payload_definition',item->'payload',(item->>'rendition_id')::bigint,(item->>'segment_id')::bigint,(item->>'span_id')::bigint,(item->>'score')::numeric,coalesce(item->>'outcome','produced'),(item->>'source_view_id')::bigint) RETURNING id INTO oid;
   ids:=array_append(ids,oid);
 END LOOP;
 IF p_envelope ? 'contributions' THEN PERFORM ops.project_source_contributions(t.id,p_envelope); END IF;
 IF p_envelope IS NOT NULL THEN INSERT INTO ops.task_result(task_id,release_id,body) VALUES(t.id,t.release_id,p_envelope); END IF;
 UPDATE ops.task SET status=p_outcome,result_digest=digest,error=CASE WHEN coalesce(t.error ? 'semantic_proposal_first_result',false) THEN coalesce(nullif(p_error,'null'::jsonb),'{}'::jsonb)||jsonb_build_object('semantic_proposal_first_result',t.error->'semantic_proposal_first_result') ELSE nullif(p_error,'null'::jsonb) END,finished_at=clock_timestamp(),lease_until=NULL WHERE id=t.id;
 RETURN jsonb_build_object('transaction','applied','receipt',jsonb_build_object('task_id',t.id,'run_id',t.run_id,'release_id',t.release_id,'attempt',t.attempt,'protocol',p_outcome,'result_digest',digest,'observation_ids',to_jsonb(ids)));
END $$;
ALTER FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) TO corpus_sem_writer;

