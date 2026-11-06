-- Exact selected task custody, immutable original contribution and its endpoint closure.
CREATE OR REPLACE FUNCTION ops.resolve_retained_source_contribution(ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected record; rows_ jsonb; sources_ jsonb; row_ jsonb; pin_ jsonb; view_ kb.source_view; field_ text;
BEGIN
 IF jsonb_typeof(ref) IS DISTINCT FROM 'object' OR
 ref-ARRAY['contribution_id','project_id','run_id','cut_id','release_id','result_revision','selected_task_id','origin_task_id','runtime_fingerprint']<>'{}'::jsonb OR
 NOT ref ?& ARRAY['contribution_id','project_id','run_id','cut_id','release_id','result_revision','selected_task_id','origin_task_id','runtime_fingerprint'] THEN
 RAISE EXCEPTION 'invalid retained contribution reference fields' USING ERRCODE='23514';END IF;
 FOREACH field_ IN ARRAY ARRAY['run_id','cut_id','selected_task_id','origin_task_id'] LOOP
 IF jsonb_typeof(ref->field_) IS DISTINCT FROM 'number' OR ref->>field_ !~ '^[1-9][0-9]*$' THEN RAISE EXCEPTION 'invalid retained contribution identifier' USING ERRCODE='23514';END IF;END LOOP;
 IF jsonb_typeof(ref->'result_revision') IS DISTINCT FROM 'number' OR ref->>'result_revision' !~ '^(0|[1-9][0-9]*)$' OR ref->>'contribution_id' !~ '^source-contribution:[0-9a-f]{64}$' THEN RAISE EXCEPTION 'invalid retained contribution identity/revision' USING ERRCODE='23514';END IF;
 FOREACH field_ IN ARRAY ARRAY['project_id','release_id','runtime_fingerprint','contribution_id'] LOOP
 IF jsonb_typeof(ref->field_) IS DISTINCT FROM 'string' OR length(ref->>field_)=0 THEN RAISE EXCEPTION 'invalid retained contribution binding' USING ERRCODE='23514';END IF;END LOOP;
 SELECT result.body,origin_job.runtime_id,batch.data_revision INTO STRICT selected
 FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id
 JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id
 JOIN ops.cut_task member ON member.cut_id=completed.cut_id JOIN ops.task task ON task.id=member.task_id
 JOIN ops.task origin ON origin.id=COALESCE(task.reused_task_id,task.id)
 JOIN ops.run origin_job ON origin_job.id=origin.run_id JOIN ops.task_result result ON result.task_id=origin.id
 WHERE job.id=(ref->>'run_id')::bigint AND job.project_id=ref->>'project_id' AND job.release_id=ref->>'release_id'
 AND job.sealed AND job.status='finished' AND completed.cut_id=(ref->>'cut_id')::bigint
 AND task.id=(ref->>'selected_task_id')::bigint AND origin.id=(ref->>'origin_task_id')::bigint
 AND member.origin_task_id=origin.id AND origin.release_id=ref->>'release_id' AND task.status IN ('done','reused')
 AND task.unit_type='source_view' AND origin.unit_type='source_view' AND task.unit_id=origin.unit_id
 AND result.body->>'release_id'=ref->>'release_id'
 AND EXISTS(SELECT FROM ops.input_cut cut WHERE cut.id=completed.cut_id AND cut.run_id=job.id AND cut.release_id=job.release_id AND cut.final);
 IF selected.runtime_id IS DISTINCT FROM ref->>'runtime_fingerprint' OR selected.data_revision IS DISTINCT FROM (ref->>'result_revision')::bigint THEN
 RAISE EXCEPTION 'retained contribution differs from original producer custody' USING ERRCODE='23514';END IF;
 WITH RECURSIVE available AS (SELECT c FROM jsonb_array_elements(selected.body->'contributions')c),
 closure(c) AS (SELECT c FROM available WHERE c->>'contribution_id'=ref->>'contribution_id' UNION
 SELECT a.c FROM closure r CROSS JOIN LATERAL (
 SELECT e->>'contribution_id' id FROM jsonb_array_elements(COALESCE(r.c->'endpoints','[]'))e
 UNION SELECT jsonb_array_elements_text(COALESCE(r.c->'members','[]')))ep JOIN available a ON a.c->>'contribution_id'=ep.id)
 SELECT COALESCE(jsonb_agg(c ORDER BY c->>'contribution_id'),'[]') INTO rows_ FROM closure;
 IF jsonb_array_length(rows_)=0 THEN RAISE EXCEPTION 'retained contribution unavailable' USING ERRCODE='23514';END IF;
 sources_:='[]';
 FOR row_ IN SELECT value FROM jsonb_array_elements(rows_) LOOP
 IF row_->>'contribution_id' IS DISTINCT FROM 'source-contribution:'||encode(sha256(convert_to(data.canonical_json(row_-'contribution_id'),'UTF8')),'hex') OR EXISTS(
 SELECT FROM (SELECT e->>'contribution_id' id FROM jsonb_array_elements(COALESCE(row_->'endpoints','[]'))e UNION SELECT jsonb_array_elements_text(COALESCE(row_->'members','[]')))ep
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(rows_)r WHERE r->>'contribution_id'=ep.id)) THEN
 RAISE EXCEPTION 'retained contribution identity or endpoint closure differs' USING ERRCODE='23514';END IF;
 pin_:=row_->'pin';SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(pin_->>'source_view_id')::bigint;
 IF NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=(ref->>'run_id')::bigint AND source_view_id=view_.id)
 OR pin_ IS DISTINCT FROM jsonb_build_object('source',view_.key,'native_product_task_id',view_.native_task_id,'product_key',view_.native_product_key,'product_digest',view_.native_content_digest,'projection_digest',view_.projection_digest,'recipe_digest',view_.recipe_digest,'source_view_id',view_.id)
 OR EXISTS(SELECT FROM jsonb_array_elements(COALESCE(row_->'anchors','[]'))a WHERE a->'pin' IS DISTINCT FROM pin_) THEN
 RAISE EXCEPTION 'retained contribution source pin differs' USING ERRCODE='23514';END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(sources_)s WHERE s->'source_view_id'=pin_->'source_view_id') THEN
 sources_:=sources_||jsonb_build_array(jsonb_build_object('source_view_id',view_.id,'pin',pin_,'projection',view_.projection));END IF;
 END LOOP;
 RETURN jsonb_build_object('contributions',rows_,'sources',sources_);
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range OR invalid_text_representation THEN
 RAISE EXCEPTION 'retained contribution cannot resolve exact selected origin' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_source_contribution(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_source_contribution(jsonb) TO corpus_sem_reader,corpus_sem_writer;

-- Private membership retains all original endpoint citations, with source-qualified scope.
CREATE OR REPLACE FUNCTION ops.dossier_contribution_member(inputs jsonb,ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb;root_ jsonb;row_ jsonb;a jsonb;s jsonb;v jsonb;piece jsonb;p jsonb;meaning jsonb;
 citations jsonb:='[]';deps jsonb:='[]';citation jsonb;span_ jsonb;source_id text;start_ integer;end_ integer;role_ text;raw_role text;scope_ text;key_ text;
BEGIN
 IF NOT inputs->'dependencies' ? (ref->>'contribution_id') THEN RAISE EXCEPTION 'dossier contribution outside dependencies' USING ERRCODE='23514';END IF;
 retained:=ops.resolve_retained_source_contribution(ref);
 SELECT r INTO STRICT root_ FROM jsonb_array_elements(retained->'contributions')r WHERE r->>'contribution_id'=ref->>'contribution_id';
 IF root_->>'semantic_type' NOT IN ('structural.located_participant','structural.scoped_attachment','structural.artifact') THEN RAISE EXCEPTION 'dossier requires current source structural product' USING ERRCODE='23514';END IF;
 FOR row_ IN SELECT r FROM jsonb_array_elements(retained->'contributions')r ORDER BY r->>'contribution_id' LOOP
 deps:=deps||jsonb_build_array(row_->'contribution_id')||COALESCE(row_->'computation_dependencies','[]');
 FOR a IN SELECT value FROM jsonb_array_elements(COALESCE(row_->'anchors','[]')) LOOP
 SELECT source_ INTO STRICT s FROM jsonb_array_elements(inputs->'sources')source_ WHERE source_->'source_view_id'=a->'pin'->'source_view_id'
 AND source_->'native_task_id'=a->'pin'->'native_product_task_id' AND source_->'native_product_key'=a->'pin'->'product_key'
 AND source_->'native_content_digest'=a->'pin'->'product_digest' AND source_->'projection_digest'=a->'pin'->'projection_digest' AND source_->'recipe_digest'=a->'pin'->'recipe_digest';
 SELECT source_ INTO STRICT v FROM jsonb_array_elements(retained->'sources')source_ WHERE source_->'source_view_id'=s->'source_view_id';
 IF a->>'space'<>'native' OR a->>'precision'<>'exact' OR a->'pin' IS DISTINCT FROM v->'pin' THEN RAISE EXCEPTION 'contribution lacks exact native bridge' USING ERRCODE='23514';END IF;
 SELECT item INTO STRICT piece FROM jsonb_array_elements(v->'projection'->'pieces')item WHERE item->>'kind'='native_text' AND
 (item->>'item_ref')||CASE WHEN item->>'cell_index' IS NULL THEN '' ELSE '/data/table_cells/'||(item->>'cell_index') END=a->>'pointer';
 start_:=(piece->>'start')::integer+(a->>'start')::integer;end_:=(piece->>'start')::integer+(a->>'end')::integer;
 IF NOT (piece->>'start')::integer<=start_ OR end_> (piece->>'end')::integer OR start_>=end_ OR
 substring(v->'projection'->>'text' FROM start_+1 FOR end_-start_) IS DISTINCT FROM a->>'source_piece' THEN RAISE EXCEPTION 'contribution citation differs from original source' USING ERRCODE='23514';END IF;
 source_id:=encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex');
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(inputs->'passages')passage WHERE passage->>'source_ref'=source_id AND (passage->>'start')::integer<=start_ AND (passage->>'end')::integer>=end_) THEN RAISE EXCEPTION 'endpoint outside dossier passage closure' USING ERRCODE='23514';END IF;
 FOR p IN SELECT passage FROM jsonb_array_elements(inputs->'passages')passage WHERE passage->>'source_ref'=source_id AND (passage->>'start')::integer<=start_ AND (passage->>'end')::integer>=end_ LOOP
 IF substring(p->>'text' FROM start_-(p->>'start')::integer+1 FOR end_-start_) IS DISTINCT FROM a->>'source_piece' THEN RAISE EXCEPTION 'contribution citation differs from dossier passage' USING ERRCODE='23514';END IF;
 span_:=jsonb_build_object('passage_id',p->>'passage_id','start',start_,'end',end_,'text',a->>'source_piece');
 citations:=citations||jsonb_build_array(jsonb_build_object('contribution_id',row_->>'contribution_id','source_ref',source_id,'source_pointer',a->>'pointer','span',span_));
 END LOOP;END LOOP;END LOOP;
 IF jsonb_array_length(citations)=0 THEN RAISE EXCEPTION 'dossier contribution lacks endpoint evidence' USING ERRCODE='23514';END IF;
 SELECT jsonb_agg(c ORDER BY c->>'source_ref',(c->'span'->>'start')::integer,(c->'span'->>'end')::integer,c->>'contribution_id',c->'span'->>'passage_id') INTO citations FROM (SELECT DISTINCT c FROM jsonb_array_elements(citations)c)q;
 SELECT jsonb_agg(d ORDER BY d) INTO deps FROM (SELECT DISTINCT d FROM jsonb_array_elements_text(deps)d)q;
 meaning:=data.record_source_json(root_->'value');raw_role:=COALESCE(meaning->>'role',meaning->>'relation','unresolved_sense');
 role_:=CASE WHEN raw_role IN ('exception','revision','conflict','open_question') THEN raw_role WHEN root_->>'kind'='relation' THEN 'relationship' WHEN raw_role IN ('header','row_label','symbol','declaration') THEN 'terminology' WHEN starts_with(raw_role,'procedure_') THEN 'usage' ELSE 'unresolved_sense' END;
 SELECT string_agg(id,',' ORDER BY id) INTO scope_ FROM (SELECT DISTINCT c->>'source_ref' id FROM jsonb_array_elements(citations)c)q;
 scope_:=scope_||':'||COALESCE(meaning->>'region',meaning->>'scope',meaning->>'source_pointer','unknown');
 key_:=encode(sha256(convert_to(data.canonical_json(jsonb_build_object('contribution_ref',ref,'role',role_,'citations',citations,'scope',scope_)),'UTF8')),'hex');
 span_:=citations->0->'span';
 RETURN jsonb_build_object('member_id',key_,'passage_id',span_->>'passage_id','citation',span_,'role',role_,'sense','unresolved','scope',scope_,
 'relation_product_id',ref->>'contribution_id','contribution_ref',ref,'contribution_citations',citations,'computation_dependencies',deps,'qualification','proposed');
EXCEPTION WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'contribution cannot resolve exact original citation closure' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.dossier_contribution_member(jsonb,jsonb) FROM PUBLIC;
