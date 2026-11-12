-- Explicit foreign-source references preserve original project/release/run custody.
CREATE OR REPLACE FUNCTION ops.validate_structural_source(p_source jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE v kb.source_view; source_run ops.run; completed ops.completed_result; batch data.batch; field text;
BEGIN
 IF jsonb_typeof(p_source) IS DISTINCT FROM 'object'
 OR p_source-ARRAY['project_id','run_id','cut_id','release_id','result_revision','source_view_id','native_task_id','native_product_key','native_content_digest','projection_digest','recipe_digest','coordinate_version'] <> '{}'::jsonb
 OR NOT p_source ?& ARRAY['project_id','run_id','cut_id','release_id','result_revision','source_view_id','native_task_id','native_product_key','native_content_digest','projection_digest','recipe_digest','coordinate_version'] THEN
  RAISE EXCEPTION 'structural source reference has incomplete or extra fields' USING ERRCODE='23514'; END IF;
 FOREACH field IN ARRAY ARRAY['run_id','cut_id','source_view_id','native_task_id'] LOOP
  IF jsonb_typeof(p_source->field) IS DISTINCT FROM 'number' OR p_source->>field !~ '^[1-9][0-9]*$' THEN
   RAISE EXCEPTION 'structural source reference has invalid identifier' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF jsonb_typeof(p_source->'result_revision') IS DISTINCT FROM 'number' OR p_source->>'result_revision' !~ '^(0|[1-9][0-9]*)$'
 OR p_source->'coordinate_version' NOT IN ('2'::jsonb,'3'::jsonb) THEN
  RAISE EXCEPTION 'structural source reference has invalid revision/coordinates' USING ERRCODE='23514'; END IF;
 FOREACH field IN ARRAY ARRAY['project_id','release_id','native_product_key'] LOOP
  IF jsonb_typeof(p_source->field) IS DISTINCT FROM 'string' OR length(p_source->>field)=0 THEN
   RAISE EXCEPTION 'structural source reference has empty binding' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOREACH field IN ARRAY ARRAY['native_content_digest','projection_digest','recipe_digest'] LOOP
  IF jsonb_typeof(p_source->field) IS DISTINCT FROM 'string' OR p_source->>field !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'structural source reference has invalid digest' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT * INTO STRICT source_run FROM ops.run WHERE id=(p_source->>'run_id')::bigint;
 SELECT * INTO STRICT completed FROM ops.completed_result WHERE run_id=source_run.id;
 SELECT * INTO STRICT batch FROM data.batch WHERE release_id=completed.release_id AND realization_id=completed.output_realization_id AND batch_id=completed.batch_id;
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=(p_source->>'source_view_id')::bigint;
 IF NOT source_run.sealed OR source_run.status<>'finished'
 OR source_run.project_id IS DISTINCT FROM p_source->>'project_id'
 OR source_run.release_id IS DISTINCT FROM p_source->>'release_id'
 OR completed.cut_id IS DISTINCT FROM (p_source->>'cut_id')::bigint
 OR batch.data_revision IS DISTINCT FROM (p_source->>'result_revision')::bigint
 OR v.release_id IS DISTINCT FROM source_run.release_id
 OR NOT EXISTS(SELECT FROM ops.input_cut WHERE id=completed.cut_id AND run_id=source_run.id AND release_id=source_run.release_id AND final)
 OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=source_run.id AND source_view_id=v.id)
 OR NOT EXISTS(SELECT FROM kb.document WHERE id=v.document_id AND project_id=source_run.project_id)
 OR v.native_task_id IS DISTINCT FROM (p_source->>'native_task_id')::bigint
 OR v.native_product_key IS DISTINCT FROM p_source->>'native_product_key'
 OR v.native_content_digest IS DISTINCT FROM p_source->>'native_content_digest'
 OR v.projection_digest IS DISTINCT FROM p_source->>'projection_digest'
 OR v.recipe_digest IS DISTINCT FROM p_source->>'recipe_digest'
 OR (p_source->>'coordinate_version')::integer IS DISTINCT FROM (SELECT CASE WHEN kind='integrated' THEN 3 ELSE 2 END FROM ops.pdf_product WHERE task_id=v.native_task_id AND product_key=v.native_product_key AND content_digest=v.native_content_digest)
 OR NOT EXISTS(SELECT FROM ops.pdf_selected_product WHERE task_id=v.native_task_id AND product_key=v.native_product_key AND content_digest=v.native_content_digest) THEN
  RAISE EXCEPTION 'structural source differs from original completed source custody' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'structural source reference cannot resolve exact original custody' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_structural_source(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.validate_structural_source(jsonb) TO corpus_sem_reader,corpus_sem_writer;


CREATE OR REPLACE FUNCTION ops.validate_structural_input(p_inputs jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE inputs jsonb:=p_inputs; source_ jsonb; source_map jsonb:='{}'; passage jsonb; passage_map jsonb:='{}'; ref jsonb; v kb.source_view; identifier text;
BEGIN
 IF jsonb_typeof(inputs->'sources') IS DISTINCT FROM 'array' OR jsonb_typeof(inputs->'passages') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'structural input requires source/passage arrays' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(inputs->'sources')=0 OR jsonb_array_length(inputs->'passages')=0 THEN
  RAISE EXCEPTION 'structural report requires original source and passage closure' USING ERRCODE='23514'; END IF;
 FOR source_ IN SELECT value FROM jsonb_array_elements(inputs->'sources') LOOP
  PERFORM ops.validate_structural_source(source_);
  identifier:=encode(sha256(convert_to(data.canonical_json(source_),'UTF8')),'hex');
  IF source_map ? identifier THEN RAISE EXCEPTION 'duplicate structural source' USING ERRCODE='23514'; END IF;
  source_map:=source_map||jsonb_build_object(identifier,source_);
 END LOOP;
 FOR passage IN SELECT value FROM jsonb_array_elements(inputs->'passages') LOOP
  identifier:=passage->>'passage_id'; ref:=source_map->(passage->>'source_ref');
  IF passage_map ? identifier OR ref IS NULL THEN RAISE EXCEPTION 'duplicate passage or unknown original source' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT v FROM kb.source_view WHERE id=(ref->>'source_view_id')::bigint;
  IF (passage->>'end')::bigint<=(passage->>'start')::bigint OR (passage->>'end')::bigint>char_length(v.projection->>'text')
   OR passage->>'text' IS DISTINCT FROM substring(v.projection->>'text' FROM (passage->>'start')::integer+1 FOR (passage->>'end')::integer-(passage->>'start')::integer) THEN
   RAISE EXCEPTION 'structural passage differs from exact original source text' USING ERRCODE='23514'; END IF;
  passage_map:=passage_map||jsonb_build_object(identifier,passage);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.validate_structural_input(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.validate_structural_input(jsonb) TO corpus_sem_reader,corpus_sem_writer;

-- Resolve a component through its actual selected completed producer, never an alias.
CREATE OR REPLACE FUNCTION ops.resolve_retained_structural_report(ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected record; assertions jsonb;
BEGIN
 IF ref-ARRAY['product_id','project_id','run_id','cut_id','release_id','result_revision','selected_task_id','origin_task_id','runtime_fingerprint']<>'{}'::jsonb THEN
  RAISE EXCEPTION 'invalid retained structural reference fields' USING ERRCODE='23514'; END IF;
 SELECT origin.id, result.body->'structural_product' report, batch.data_revision,
  origin_job.runtime_id, completed.batch_id, completed.release_id, completed.output_realization_id
 INTO STRICT selected
 FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id
 JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id
 JOIN ops.cut_task member ON member.cut_id=completed.cut_id
 JOIN ops.task task ON task.id=member.task_id
 JOIN ops.task origin ON origin.id=COALESCE(task.reused_task_id,task.id)
 JOIN ops.run origin_job ON origin_job.id=origin.run_id
 JOIN ops.task_result result ON result.task_id=origin.id
 WHERE job.id=(ref->>'run_id')::bigint AND job.project_id=ref->>'project_id'
 AND job.release_id=ref->>'release_id' AND job.sealed AND job.status='finished'
 AND completed.cut_id=(ref->>'cut_id')::bigint AND task.id=(ref->>'selected_task_id')::bigint
 AND origin.id=(ref->>'origin_task_id')::bigint AND member.origin_task_id=origin.id
 AND origin.release_id=ref->>'release_id' AND task.status IN ('done','reused');
 IF selected.report->>'version' IS DISTINCT FROM 'structural-product-3'
 OR 'structural:'||encode(sha256(convert_to(data.canonical_json(selected.report-'retrieval_report'),'UTF8')),'hex') IS DISTINCT FROM ref->>'product_id'
 OR selected.data_revision IS DISTINCT FROM (ref->>'result_revision')::bigint
 OR selected.runtime_id IS DISTINCT FROM ref->>'runtime_fingerprint' THEN
  RAISE EXCEPTION 'retained report differs from exact original producer custody' USING ERRCODE='23514'; END IF;
 -- Public eligibility is obtained from the authoritative published rows below; the private
 -- report contains no self-declared support flag that a dossier may trust.
 SELECT COALESCE(jsonb_agg(jsonb_build_object('assessment_id',s.assertion_id,'statement',s.statement_json::jsonb)),'[]') INTO assertions
 FROM data.structural_assertion s WHERE s.release_id=selected.release_id
 AND s.realization_id=selected.output_realization_id AND s.cut_id=(ref->>'cut_id')::bigint
 AND s.selected_task_id=(ref->>'selected_task_id')::bigint AND s.origin_task_id=selected.id
 AND s.product_id=ref->>'product_id';
 RETURN jsonb_build_object('report',selected.report,'public_assertions',assertions);
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'retained report cannot resolve exact selected origin' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_structural_report(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_structural_report(jsonb) TO corpus_sem_reader,corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.resolve_retained_component(ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected record; component jsonb;
BEGIN
 SELECT origin.id, result.body->'structural_product' report, method.name, method.version,
  batch.data_revision, origin_job.runtime_id INTO STRICT selected
 FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id
 JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id
 JOIN ops.cut_task member ON member.cut_id=completed.cut_id
 JOIN ops.task task ON task.id=member.task_id
 JOIN ops.task origin ON origin.id=COALESCE(task.reused_task_id,task.id)
 JOIN ops.run origin_job ON origin_job.id=origin.run_id
 JOIN ops.task_result result ON result.task_id=origin.id
 JOIN ops.method_config config ON config.id=origin.method_config_id JOIN ops.method method ON method.id=config.method_id
 WHERE job.id=(ref->>'run_id')::bigint AND job.project_id=ref->>'project_id'
 AND job.release_id=ref->>'release_id' AND job.sealed AND job.status='finished'
 AND completed.cut_id=(ref->>'cut_id')::bigint AND task.id=(ref->>'selected_task_id')::bigint
 AND origin.id=(ref->>'origin_task_id')::bigint AND member.origin_task_id=origin.id AND origin.release_id=ref->>'release_id' AND task.status IN ('done','reused');
 IF selected.report->>'version' IS DISTINCT FROM 'structural-product-3'
 OR selected.report->>'kind' IS DISTINCT FROM 'definition_components'
 OR 'structural:'||encode(sha256(convert_to(data.canonical_json(selected.report-'retrieval_report'),'UTF8')),'hex') IS DISTINCT FROM ref->>'product_id'
 OR selected.name IS DISTINCT FROM ref->>'operation_id' OR selected.version IS DISTINCT FROM ref->>'operation_version'
 OR selected.data_revision IS DISTINCT FROM (ref->>'result_revision')::bigint
 OR selected.runtime_id IS DISTINCT FROM ref->>'runtime_fingerprint'
 OR selected.report->'inputs'->'dependencies' IS DISTINCT FROM ref->'dependencies' THEN
  RAISE EXCEPTION 'retained component differs from original producer custody' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT component FROM jsonb_array_elements(selected.report->'definition_components'->'components') WHERE value->>'component_id'=ref->>'component_id';
 RETURN jsonb_build_object('component',component,'report',selected.report);
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'retained component cannot resolve exact selected origin' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_component(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_component(jsonb) TO corpus_sem_reader,corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.component_semantic_target(ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb;
BEGIN
 retained:=ops.resolve_retained_component(ref);
 RETURN data.structural_definition_component(retained->'report',retained->'component');
END $$;
REVOKE ALL ON FUNCTION ops.component_semantic_target(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.component_semantic_target(jsonb) TO corpus_sem_reader,corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.validate_component_targets(targets jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE target jsonb; retained jsonb;
BEGIN
 IF jsonb_typeof(targets) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'component target population requires array' USING ERRCODE='23514'; END IF;
 FOR target IN SELECT value FROM jsonb_array_elements(targets) LOOP
  retained:=ops.resolve_retained_component(target->'reference')->'component';
  IF target->>'label' IS DISTINCT FROM retained->'term'->>'text' OR target->>'description' IS DISTINCT FROM retained->'content'->>'text'
   OR target->>'scope' IS DISTINCT FROM retained->>'scope' OR target->>'effective_version' IS DISTINCT FROM retained->>'effective_version'
   OR target->>'parent' IS NOT NULL THEN
   RAISE EXCEPTION 'component target descriptor differs from exact retained source' USING ERRCODE='23514'; END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.validate_component_targets(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.validate_component_targets(jsonb) TO corpus_sem_reader,corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.resolve_retained_relationship_decision(ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected record; operation jsonb; decision jsonb; edge jsonb; occurrence jsonb; target jsonb; semantic_group jsonb; targets jsonb; member jsonb; locations jsonb;
BEGIN
 SELECT result.body, task.unit_id, batch.data_revision, origin_job.runtime_id INTO STRICT selected
 FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id
 JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id
 JOIN ops.cut_task member ON member.cut_id=completed.cut_id JOIN ops.task task ON task.id=member.task_id
 JOIN ops.task origin ON origin.id=member.origin_task_id JOIN ops.run origin_job ON origin_job.id=origin.run_id
 JOIN ops.task_result result ON result.task_id=origin.id
 WHERE job.id=(ref->>'run_id')::bigint AND job.project_id=ref->>'project_id' AND job.release_id=ref->>'release_id'
 AND job.sealed AND job.status='finished' AND completed.cut_id=(ref->>'cut_id')::bigint
 AND task.id=(ref->>'selected_task_id')::bigint AND task.run_id=job.id AND task.unit_type='source_view' AND origin.id=(ref->>'origin_task_id')::bigint
 AND origin.id=COALESCE(task.reused_task_id,task.id) AND origin.release_id=ref->>'release_id' AND task.status IN ('done','reused');
 IF selected.data_revision IS DISTINCT FROM (ref->>'result_revision')::bigint OR selected.runtime_id IS DISTINCT FROM ref->>'runtime_fingerprint' THEN
  RAISE EXCEPTION 'retained relationship differs from original runtime/revision' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT operation FROM jsonb_array_elements(selected.body->'contribution_operations') WHERE value->>'operation_key'=ref->>'operation_key';
 IF operation->'contextual_enrichment'->>'version' IS DISTINCT FROM 'contextual-enrichment-2' THEN
  RAISE EXCEPTION 'retained relationship requires current contextual product' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT decision FROM jsonb_array_elements(operation->'contextual_enrichment'->'relationship_decisions') WHERE value->>'decision_id'=ref->>'decision_id';
 SELECT value INTO STRICT edge FROM jsonb_array_elements(decision->'selected_edges') WHERE value->>'edge_id'=ref->>'edge_id';
 SELECT cc INTO STRICT occurrence FROM jsonb_array_elements(selected.body->'contributions') cc WHERE cc->>'contribution_id'=ref->>'occurrence_contribution_id'
 AND cc->>'semantic_type'='contextual.located_mention' AND cc->>'occurrence_id'=decision->>'occurrence_id'
 AND EXISTS(SELECT FROM jsonb_array_elements(edge->'witnesses') w WHERE w->'evidence_ids' ? (cc->>'contribution_id'));
 SELECT sg INTO STRICT semantic_group FROM jsonb_array_elements(operation->'contextual_enrichment'->'candidate_lists') cl
 JOIN LATERAL jsonb_array_elements(operation->'contextual_enrichment'->'inventories') inv ON inv->>'inventory_id'=cl->>'inventory_id'
 CROSS JOIN LATERAL jsonb_array_elements(inv->'semantic_groups') sg
 WHERE cl->>'list_id'=decision->>'candidate_list_id' AND sg->>'target_id'=edge->>'target_id';
 SELECT jsonb_agg(ct ORDER BY data.canonical_json(ct->'reference')) INTO targets
 FROM jsonb_array_elements(operation->'contextual_enrichment'->'component_targets') ct WHERE semantic_group->'member_target_ids' ? (ct->'reference'->>'component_id');
 IF targets IS NULL OR jsonb_array_length(targets)<>jsonb_array_length(semantic_group->'member_target_ids') THEN RAISE EXCEPTION 'relationship group lacks every original component proof' USING ERRCODE='23514'; END IF;
 FOR member IN SELECT value FROM jsonb_array_elements(targets) LOOP
  IF ops.component_semantic_target(member->'reference') IS DISTINCT FROM semantic_group->'meaning' THEN RAISE EXCEPTION 'relationship group member changes source meaning' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT ct INTO STRICT target FROM jsonb_array_elements(targets) ct WHERE edge->'member_target_ids' ? (ct->'reference'->>'component_id') ORDER BY data.canonical_json(ct->'reference') LIMIT 1;
 SELECT jsonb_agg(jsonb_build_object('start',start_,'end',end_,'text',literal) ORDER BY start_,end_,literal)
 INTO locations
 FROM kb.source_view view_,jsonb_array_elements(occurrence->'anchors') anchor,
 LATERAL jsonb_array_elements(view_.projection->'pieces') piece,
 LATERAL (SELECT (piece->>'start')::integer+(anchor->>'start')::integer start_,
  (piece->>'start')::integer+(anchor->>'end')::integer end_,anchor->>'source_piece' literal) span
 WHERE view_.id=selected.unit_id AND piece->>'kind'='native_text'
  AND anchor->>'space'='native' AND anchor->>'precision'='exact'
  AND (anchor->'pin'->>'source_view_id')::bigint=view_.id
  AND anchor->'pin'->>'product_digest'=view_.native_content_digest
  AND anchor->'pin'->>'projection_digest'=view_.projection_digest
  AND anchor->>'pointer'=piece->>'item_ref'||CASE WHEN piece->>'cell_index' IS NOT NULL THEN '/data/table_cells/'||(piece->>'cell_index') ELSE '' END
  AND (piece->>'start')::integer<=start_ AND start_<end_ AND end_<=(piece->>'end')::integer
  AND literal=substring(view_.projection->>'text' FROM start_+1 FOR end_-start_);
 IF jsonb_array_length(locations) IS DISTINCT FROM jsonb_array_length(occurrence->'anchors') THEN locations:=NULL; END IF;
 RETURN jsonb_build_object('decision',decision,'edge',edge,'occurrence',occurrence,'component_target',target,'component_targets',targets,'semantic_target',semantic_group->'meaning','source_view_id',selected.unit_id,'located_occurrence',COALESCE(locations,'[]'));
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'retained relationship cannot resolve exact original edge/source' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_relationship_decision(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_relationship_decision(jsonb) TO corpus_sem_reader,corpus_sem_writer;

-- Comparison reads complete positioned source facts. Parsing and linguistic
-- classification are owned by the primary formal producer.
CREATE OR REPLACE FUNCTION ops.comparison_primary_extent(layers jsonb,ref jsonb,source_ jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE v kb.source_view; node jsonb; extents_ jsonb;
BEGIN
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
 node:=ops.primary_characterization_node(layers,ref);
 IF NOT ops.primary_characterization_in_view(layers,ref,node,v.id) THEN RETURN NULL; END IF;
 extents_:=ops.primary_characterization_extents(layers,ref,node,v);
 IF jsonb_array_length(extents_)<>1 OR coalesce((extents_->0->>'synthetic')::boolean,true) OR extents_->0->>'text' IS NULL THEN RETURN NULL; END IF;
 RETURN extents_->0;
END $$;
REVOKE ALL ON FUNCTION ops.comparison_primary_extent(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_primary_covered(layers jsonb,source_ jsonb,family_ text,lo bigint,hi bigint)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT EXISTS(SELECT FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'coverage') c
 WHERE c->>'family'=family_ AND c->>'availability'='available' AND c->>'outcome' IN ('complete','empty')
  AND coalesce(c->'unexamined','[]')='[]'::jsonb AND EXISTS(SELECT FROM jsonb_array_elements(c->'examined') s
   WHERE s->>'projection'=source_->>'projection_digest' AND coalesce((s->>'start')::bigint,0)<=lo AND coalesce((s->>'end')::bigint,0)>=hi))
$$;
REVOKE ALL ON FUNCTION ops.comparison_primary_covered(jsonb,jsonb,text,bigint,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_primary_fields(passage jsonb,source_ jsonb,layers jsonb,family_ text)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE l record; a jsonb; ref jsonb; root jsonb; extent_ jsonb; formal_ jsonb; input_ jsonb;
 results jsonb:='[]'; captured text[]:='{}'; complete_ boolean:=ops.comparison_primary_covered(layers,source_,family_,(passage->>'start')::bigint,(passage->>'end')::bigint); duplicates jsonb;
BEGIN
 FOR l IN SELECT * FROM jsonb_each(layers) LOOP
  captured:='{}';
  FOR a IN SELECT value FROM jsonb_array_elements(l.value->'annotations') WHERE value->>'kind'='formal.rule' AND value->>'family'=family_ AND value->'formal' ? 'normalized' LOOP
   formal_:=a->'formal';root:=ops.primary_characterization_node(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',formal_->>'input_id'));input_:=root->'formal_input';
   IF input_->>'representation' IS DISTINCT FROM 'source_text' OR input_->>'syntax_outcome' IS DISTINCT FROM 'complete'
    OR formal_->>'start' IS DISTINCT FROM '0' OR (formal_->>'end')::integer IS DISTINCT FROM char_length(input_->>'text') THEN CONTINUE; END IF;
   ref:=jsonb_build_object('layer',l.key::jsonb,'local_id',root->>'local_id');extent_:=ops.comparison_primary_extent(layers,ref,source_);
   IF extent_ IS NULL OR (extent_->>'start')::bigint<(passage->>'start')::bigint OR (extent_->>'end')::bigint>(passage->>'end')::bigint OR extent_->>'text' IS DISTINCT FROM input_->>'text' THEN CONTINUE; END IF;
   IF formal_->'normalized'->>'domain_status'='invalid' THEN complete_:=false;CONTINUE; END IF;
   captured:=array_append(captured,root->>'local_id');ref:=jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id');
   IF NOT ops.primary_characterization_choices(layers,ref,a,'[]') OR NOT ops.primary_characterization_choices(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',root->>'local_id'),root,'[]') THEN complete_:=false;CONTINUE; END IF;
   results:=results||jsonb_build_array(jsonb_build_object('reference',ref,'span',jsonb_build_object('passage_id',passage->>'passage_id','start',extent_->'start','end',extent_->'end','text',extent_->'text'),
    'grammar',input_->'grammar','start_symbol',input_->'start_symbol','rule',formal_->'rule','normalized',formal_->'normalized'));
  END LOOP;
  FOR a IN SELECT value FROM jsonb_array_elements(l.value->'annotations') WHERE value->>'family'=family_ AND value ? 'formal_input' LOOP
   extent_:=ops.comparison_primary_extent(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),source_);
   IF extent_ IS NOT NULL AND (extent_->>'start')::bigint>=(passage->>'start')::bigint AND (extent_->>'end')::bigint<=(passage->>'end')::bigint AND NOT (a->>'local_id'=ANY(captured)) THEN complete_:=false; END IF;
  END LOOP;
 END LOOP;
 SELECT coalesce(jsonb_agg(key),'[]') INTO duplicates FROM (SELECT jsonb_build_array(r->'span'->'start',r->'span'->'end') key FROM jsonb_array_elements(results) r GROUP BY r->'span'->'start',r->'span'->'end' HAVING count(*)<>1) d;
 IF jsonb_array_length(duplicates)>0 THEN complete_:=false; END IF;
 SELECT coalesce(jsonb_agg(r ORDER BY (r->'span'->>'start')::bigint,(r->'span'->>'end')::bigint),'[]') INTO results FROM jsonb_array_elements(results) r WHERE NOT duplicates @> jsonb_build_array(jsonb_build_array(r->'span'->'start',r->'span'->'end'));
 RETURN jsonb_build_object('fields',results,'complete',complete_);
END $$;
REVOKE ALL ON FUNCTION ops.comparison_primary_fields(jsonb,jsonb,jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_primary_lexical(passage jsonb,source_ jsonb,layers jsonb,kind_ text)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE l record; a jsonb; ref jsonb; extent_ jsonb; result_ jsonb:='[]'; bindings_ jsonb; member_ jsonb; member_ref jsonb; member_extent jsonb; m jsonb;
BEGIN
 FOR l IN SELECT * FROM jsonb_each(layers) LOOP
  FOR a IN SELECT value FROM jsonb_array_elements(l.value->'annotations') WHERE value->>'kind'=kind_ AND value->>'family'='formal.lexical' LOOP
   ref:=jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id');extent_:=ops.comparison_primary_extent(layers,ref,source_);
   IF extent_ IS NULL OR (extent_->>'start')::bigint<(passage->>'start')::bigint OR (extent_->>'end')::bigint>(passage->>'end')::bigint OR nullif(a->>'native_label','') IS NULL THEN CONTINUE; END IF;
   IF NOT ops.primary_characterization_choices(layers,ref,a,'[]') THEN CONTINUE; END IF;
   bindings_:='[]';
   FOR m IN SELECT value FROM jsonb_array_elements(l.value->'memberships') WHERE value->>'group'=a->>'local_id' LOOP
    member_ref:=jsonb_build_object('layer',l.key::jsonb,'local_id',m->>'member');member_:=ops.primary_characterization_node(layers,member_ref);member_extent:=ops.comparison_primary_extent(layers,member_ref,source_);
    IF member_extent IS NULL OR member_->>'native_label' IS DISTINCT FROM member_extent->>'text'
     OR (kind_='formal.revision_succession' AND member_->>'kind' IS DISTINCT FROM 'formal.version_identifier')
     OR (member_extent->>'start')::bigint<(extent_->>'start')::bigint OR (member_extent->>'end')::bigint>(extent_->>'end')::bigint
     OR NOT ops.primary_characterization_choices(layers,member_ref,member_,'[]') OR NOT ops.primary_characterization_choices(layers,ref,m,'[]') THEN RAISE EXCEPTION 'comparison lexical binding changes retained identifier membership' USING ERRCODE='23514'; END IF;
    bindings_:=bindings_||jsonb_build_array(jsonb_build_object('role',m->>'role','reference',member_ref,'value',member_->>'native_label'));
   END LOOP;
   result_:=result_||jsonb_build_array(jsonb_build_object('reference',ref,'span',jsonb_build_object('passage_id',passage->>'passage_id','start',extent_->'start','end',extent_->'end','text',extent_->'text'),'value',a->>'native_label','bindings',bindings_));
  END LOOP;
 END LOOP;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.comparison_primary_lexical(jsonb,jsonb,jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_threshold_field(passage jsonb,source_ jsonb,layers jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE inventory jsonb:=ops.comparison_primary_fields(passage,source_,layers,'formal.threshold'); fields jsonb:='[]'; f jsonb; n jsonb; bases jsonb:='[]'; basis_ jsonb; l record; a jsonb; extent_ jsonb; ref jsonb;
BEGIN
 FOR l IN SELECT * FROM jsonb_each(layers) LOOP
  FOR a IN SELECT value FROM jsonb_array_elements(l.value->'annotations') WHERE value->>'kind'='formal.comparison_basis' AND value->>'native_scheme'='source-comparison-basis-1' LOOP
   ref:=jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id');extent_:=ops.comparison_primary_extent(layers,ref,source_);
   IF extent_ IS NOT NULL AND (extent_->>'start')::bigint>=(passage->>'start')::bigint AND (extent_->>'end')::bigint<=(passage->>'end')::bigint AND nullif(a->>'native_label','') IS NOT NULL AND ops.primary_characterization_choices(layers,ref,a,'[]') THEN
    bases:=bases||jsonb_build_array(jsonb_build_object('reference',ref,'value',a->>'native_label','span',jsonb_build_object('passage_id',passage->>'passage_id','start',extent_->'start','end',extent_->'end','text',extent_->'text'))); END IF;
  END LOOP;
 END LOOP;
 IF jsonb_array_length(bases)=1 THEN basis_:=bases->0; END IF;
 FOR f IN SELECT value FROM jsonb_array_elements(inventory->'fields') LOOP
  n:=f->'normalized';
  IF n->>'kind' IS DISTINCT FROM 'threshold' OR NOT n ?& ARRAY['value','comparator'] THEN inventory:=jsonb_set(inventory,'{complete}','false');CONTINUE; END IF;
  fields:=fields||jsonb_build_array(jsonb_strip_nulls(jsonb_build_object('dimension','threshold_unit','lexical_value',f->'span'->>'text','evidence',jsonb_build_array(passage->>'passage_id'),
   'typed',jsonb_build_object('span',f->'span','grammar',f->'grammar','state','parsed','value',n->'value','comparator',n->'comparator','quantity',n->'quantity','unit',n->'unit','primary_formal',f->'reference','basis',basis_->'value','basis_evidence',basis_->'span','primary_basis',basis_->'reference'))));
 END LOOP;
 RETURN jsonb_build_object('fields',fields,'complete',inventory->'complete');
END $$;
REVOKE ALL ON FUNCTION ops.structural_threshold_field(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_literal(passage jsonb,source_ jsonb,layers jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE family_ text; candidates jsonb:='[]'; f jsonb; n jsonb; literal_ jsonb;
 field_ text; lexical_ text; parts_ text[]; coefficient_ text; digits_ text; exponent_ numeric;
BEGIN
 IF char_length(passage->>'text')>256 THEN RETURN '{}'; END IF;
 FOREACH family_ IN ARRAY ARRAY['formal.date','formal.identifier','formal.quantity','formal.interval'] LOOP
  FOR f IN SELECT value FROM jsonb_array_elements(ops.comparison_primary_fields(passage,source_,layers,family_)->'fields') LOOP
   IF f->'span'->'start'=passage->'start' AND f->'span'->'end'=passage->'end' AND f->>'start_symbol'='labeled' THEN candidates:=candidates||jsonb_build_array(f); END IF;
  END LOOP;
 END LOOP;
 IF jsonb_array_length(candidates)<>1 THEN RETURN '{}'; END IF;
 f:=candidates->0;n:=f->'normalized';
 IF n->>'kind' IN ('date','identifier') THEN literal_:=jsonb_build_object('kind',n->>'kind','value',n->'value');
 ELSIF f->>'rule'='quantity' AND n ? 'unit' THEN literal_:=jsonb_build_object('kind','quantity','value',n->'value','unit',n->'unit');
 ELSIF n->>'kind'='interval' AND n ? 'unit' THEN literal_:=jsonb_build_object('kind','range','lower',n->'lower','upper',n->'upper','lower_closed',n->'lower_closed','upper_closed',n->'upper_closed','unit',n->'unit');
 ELSE RETURN '{}'; END IF;
 IF literal_->>'kind' IN ('quantity','range') THEN
  FOREACH field_ IN ARRAY (CASE WHEN literal_->>'kind'='quantity' THEN ARRAY['value'] ELSE ARRAY['lower','upper'] END) LOOP
   lexical_:=literal_->>field_;
   IF lexical_ IS NULL OR lexical_ !~ '^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$' THEN RETURN '{}'; END IF;
   parts_:=regexp_split_to_array(ltrim(lexical_,'+-'),'[eE]');
   coefficient_:=parts_[1];digits_:=replace(coefficient_,'.','');
   IF ltrim(digits_,'0')<>'' THEN
    -- Read the retained exact decimal's adjusted exponent without expanding its value.
    exponent_:=CASE WHEN array_length(parts_,1)=2 THEN parts_[2]::numeric ELSE 0 END;
    exponent_:=exponent_+length(split_part(coefficient_,'.',1))-1
      -(length(digits_)-length(ltrim(digits_,'0')));
    IF abs(exponent_)>100 THEN RETURN '{}'; END IF;
   END IF;
  END LOOP;
 END IF;
 RETURN jsonb_build_object('literal',literal_,'primary_formal',f->'reference');
EXCEPTION WHEN numeric_value_out_of_range THEN RETURN '{}';
END $$;
REVOKE ALL ON FUNCTION ops.comparison_literal(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_primary_succession(inputs jsonb,a jsonb,b jsonb,primary_ jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_ jsonb; layers jsonb; older jsonb; newer jsonb; lineages jsonb:='{}'; facts jsonb; fact jsonb; declaration_ jsonb; bindings_ jsonb; witnesses jsonb:='[]'; passage_ jsonb;
BEGIN
 IF a->>'scope' IS DISTINCT FROM b->>'scope' OR a->>'source_ref' IS DISTINCT FROM b->>'source_ref' OR a->>'effective_version' IS NULL OR b->>'effective_version' IS NULL
  OR a->>'effective_version'=b->>'effective_version' OR nullif(a->>'parent','') IS NULL OR a->>'parent' IS DISTINCT FROM b->>'parent'
  OR NOT ((a->>'end')::bigint<=(b->>'start')::bigint OR (b->>'end')::bigint<=(a->>'start')::bigint) THEN RETURN NULL; END IF;
 SELECT s INTO STRICT source_ FROM jsonb_array_elements(inputs->'sources') s WHERE encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')=a->>'source_ref';
 layers:=primary_->(a->>'source_ref');
 FOR passage_ IN SELECT a UNION ALL SELECT b LOOP
  facts:=ops.comparison_primary_lexical(passage_,source_,layers,'formal.clause_lineage');
  IF jsonb_array_length(facts)<>1 OR facts->0->>'value' IS DISTINCT FROM a->>'parent' THEN RETURN NULL; END IF;
  lineages:=lineages||jsonb_build_object(passage_->>'passage_id',facts->0);
 END LOOP;
 FOR newer,older IN SELECT a,b UNION ALL SELECT b,a LOOP
  facts:=ops.comparison_primary_lexical(older,source_,layers,'formal.revision_declaration');
  IF jsonb_array_length(facts)<>1 OR facts->0->>'value' IS DISTINCT FROM older->>'effective_version' THEN CONTINUE; END IF;
  declaration_:=facts->0;
  FOR fact IN SELECT value FROM jsonb_array_elements(ops.comparison_primary_lexical(newer,source_,layers,'formal.revision_succession')) LOOP
   SELECT jsonb_object_agg(x->>'role',x->'value') INTO bindings_ FROM jsonb_array_elements(fact->'bindings') x;
   IF jsonb_array_length(fact->'bindings')<>2 OR bindings_ IS DISTINCT FROM jsonb_build_object('newer_revision',newer->>'effective_version','older_revision',older->>'effective_version') THEN CONTINUE; END IF;
   witnesses:=witnesses||jsonb_build_array(jsonb_build_object('older_id',older->>'passage_id','newer_id',newer->>'passage_id','evidence',fact->'span','older_evidence',declaration_->'span',
    'primary_witnesses',jsonb_build_array(declaration_->'reference',fact->'reference',lineages->(older->>'passage_id')->'reference',lineages->(newer->>'passage_id')->'reference')));
  END LOOP;
 END LOOP;
 RETURN CASE WHEN jsonb_array_length(witnesses)=1 THEN witnesses->0 END;
END $$;
REVOKE ALL ON FUNCTION ops.comparison_primary_succession(jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_compare_lexical(inputs jsonb,left_id text,right_id text,xf jsonb,yf jsonb,primary_ jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE a jsonb;b jsonb;x jsonb;y jsonb;p jsonb;q jsonb;d text;dimensions jsonb:='[]';entry jsonb;typed text;reason text;removed jsonb;added jsonb;interval_ jsonb;lo jsonb;hi jsonb;av numeric;bv numeric;lower_side boolean;is_removed boolean;applicability text;why text;newer jsonb;older jsonb;w record;succession jsonb;witnesses integer:=0;start_ integer;end_ integer;
BEGIN
 SELECT v INTO STRICT a FROM jsonb_array_elements(inputs->'passages')v WHERE v->>'passage_id'=left_id;
 SELECT v INTO STRICT b FROM jsonb_array_elements(inputs->'passages')v WHERE v->>'passage_id'=right_id;
 IF left_id=right_id THEN RAISE EXCEPTION 'comparison requires distinct passages' USING ERRCODE='23514';END IF;
 FOREACH d IN ARRAY ARRAY['actor','action','object','modality','condition','threshold_unit','exception','order_dependency','parent','version'] LOOP
  entry:=jsonb_build_object('dimension',d,'outcome','unknown','typed_outcome','unknown','assumptions','[]'::jsonb,'reason','No complete source-qualified typed premises.');
  x:=xf->d;y:=yf->d;
  IF x IS NOT NULL THEN entry:=entry||jsonb_build_object('left',x);END IF;IF y IS NOT NULL THEN entry:=entry||jsonb_build_object('right',y);END IF;
  IF x IS NOT NULL AND y IS NOT NULL THEN entry:=entry||jsonb_build_object('outcome',CASE WHEN x->>'lexical_value'=y->>'lexical_value' THEN 'same_lexical_value' ELSE 'different_lexical_value' END);END IF;
  IF d='threshold_unit' THEN
   IF x IS NOT NULL THEN entry:=entry||jsonb_build_object('left',x);END IF;IF y IS NOT NULL THEN entry:=entry||jsonb_build_object('right',y);END IF;
   IF x IS NOT NULL AND y IS NOT NULL THEN
    entry:=entry||jsonb_build_object('outcome',CASE WHEN x->>'lexical_value'=y->>'lexical_value' THEN 'same_lexical_value' ELSE 'different_lexical_value' END);
    p:=x->'typed';q:=y->'typed';typed:='unknown';removed:=NULL;added:=NULL;reason:='Unknown unit, quantity or basis withholds a stronger typed conclusion.';
    IF p->>'unit' IS NOT NULL AND q->>'unit' IS NOT NULL AND p->>'quantity' IS NOT NULL AND p->>'quantity'=q->>'quantity' AND p->>'unit'=q->>'unit' AND nullif(p->>'basis','') IS NOT NULL AND p->>'basis'=q->>'basis' THEN
     reason:='Exact threshold consequence only; other rule dimensions remain separate.';
     IF p->>'comparator' NOT IN ('>','>=','<','<=') OR q->>'comparator' NOT IN ('>','>=','<','<=') OR left(p->>'comparator',1)<>left(q->>'comparator',1) THEN typed:='unsupported';
     ELSE
      av:=(p->>'value')::numeric;bv:=(q->>'value')::numeric;typed:='different';lower_side:=left(p->>'comparator',1)='>';
      IF av=bv THEN
       IF p->>'comparator'=q->>'comparator' THEN typed:='equivalent';
       ELSE interval_:=jsonb_build_object('lower',p->>'value','upper',p->>'value','lower_closed',true,'upper_closed',true);IF position('=' in p->>'comparator')>0 THEN removed:=interval_;ELSE added:=interval_;END IF;END IF;
      ELSE
       lo:=CASE WHEN av<bv THEN p ELSE q END;hi:=CASE WHEN av<bv THEN q ELSE p END;
       interval_:=jsonb_build_object('lower',lo->>'value','upper',hi->>'value',
        'lower_closed',CASE WHEN lower_side THEN position('=' in lo->>'comparator')>0 ELSE position('=' in lo->>'comparator')=0 END,
        'upper_closed',CASE WHEN lower_side THEN position('=' in hi->>'comparator')=0 ELSE position('=' in hi->>'comparator')>0 END);
       is_removed:=CASE WHEN lower_side THEN av<bv ELSE av>bv END;IF is_removed THEN removed:=interval_;ELSE added:=interval_;END IF;
      END IF;
     END IF;
    END IF;
    entry:=entry||jsonb_build_object('typed_outcome',typed,'reason',reason,'assumptions',CASE WHEN typed IN ('equivalent','different') THEN '["same_quantity_unit_basis"]'::jsonb ELSE '[]'::jsonb END);
    IF removed IS NOT NULL THEN entry:=entry||jsonb_build_object('removed_interval',removed);END IF;IF added IS NOT NULL THEN entry:=entry||jsonb_build_object('added_interval',added);END IF;
   END IF;
  END IF;
  dimensions:=dimensions||jsonb_build_array(entry);
 END LOOP;
 succession:=ops.comparison_primary_succession(inputs,a,b,primary_);
 witnesses:=CASE WHEN succession IS NULL THEN 0 ELSE 1 END;
 IF a->>'scope' IS DISTINCT FROM b->>'scope' THEN applicability:='differently_scoped';why:='Original source scopes differ.';
 ELSIF witnesses=1 THEN applicability:='successive_revisions';why:='Exact source text establishes succession.';
 ELSIF a->>'effective_version' IS NULL OR b->>'effective_version' IS NULL THEN applicability:='unestablished';why:='Effective versions are not established.';
 ELSIF a->>'effective_version'<>b->>'effective_version' THEN applicability:='unestablished';why:='Different version labels do not establish succession or authority.';
 ELSIF NOT EXISTS(SELECT FROM unnest(ARRAY['actor','action','object','modality','condition','exception','order_dependency','parent','version']) dimension WHERE xf->dimension IS NULL OR yf->dimension IS NULL OR xf->dimension->>'lexical_value' IS DISTINCT FROM yf->dimension->>'lexical_value') THEN applicability:='co_applicable';why:='All non-threshold dimensions match under explicit scope/version.';
 ELSE applicability:='unestablished';why:='Missing or changed applicability dimensions remain material.';END IF;
 RETURN jsonb_build_object('left_id',left_id,'right_id',right_id,'dimensions',dimensions,'equivalence','not_asserted','identity_standing','not_asserted','applicability',applicability,'applicability_reason',why)||CASE WHEN witnesses=1 THEN jsonb_build_object('succession',succession) ELSE '{}'::jsonb END;
END $$;
REVOKE ALL ON FUNCTION ops.structural_compare_lexical(jsonb,text,text,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_member(passage jsonb,dimension text,extents jsonb,contribution text,source_ jsonb,layers jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE extent jsonb; lo integer; hi integer; value_ text; spans jsonb:='[]'; literal text[]:='{}';
BEGIN
 FOR extent IN SELECT e FROM jsonb_array_elements(extents) e LOOP
  lo:=(extent->>'start')::integer; hi:=(extent->>'end')::integer;
  IF lo<(passage->>'start')::integer OR hi>(passage->>'end')::integer OR hi<=lo THEN
   RAISE EXCEPTION 'comparison extent outside selected passage' USING ERRCODE='23514'; END IF;
  value_:=substring(passage->>'text' FROM lo-(passage->>'start')::integer+1 FOR hi-lo);
  spans:=spans||jsonb_build_array(jsonb_build_object('passage_id',passage->>'passage_id','start',lo,'end',hi,'text',value_));
  literal:=array_append(literal,value_);
 END LOOP;
 IF cardinality(literal)=0 THEN RETURN NULL;END IF;
 RETURN jsonb_strip_nulls(jsonb_build_object('dimension',dimension,'lexical_value',array_to_string(literal,' '),
  'spans',spans,'evidence',jsonb_build_array(passage->>'passage_id'),'contribution_id',contribution,
  'literal',NULL))||CASE WHEN cardinality(literal)=1 THEN ops.comparison_literal(passage||jsonb_build_object('start',spans->0->'start','end',spans->0->'end','text',literal[1]),source_,layers) ELSE '{}'::jsonb END;
END $$;
REVOKE ALL ON FUNCTION ops.comparison_member(jsonb,text,jsonb,text,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_groups(passage jsonb,source_ jsonb,ref jsonb,rows_ jsonb,layers jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE reading jsonb;frame jsonb;component jsonb;pin jsonb;item jsonb;cue jsonb;dimension text;field_ jsonb;
 incomplete text[]:='{}';fields jsonb:='{}';controls jsonb:='[]';groups jsonb:='{}';members jsonb;state text;
 grouping text;witnesses jsonb;previous jsonb;lo integer;hi integer;gap text;marker text;word text;label text;focus jsonb;empty_ jsonb;inventory_ jsonb;facts_ jsonb;fact_ jsonb; primary_ jsonb; tokens_ jsonb; l_ record; a_ jsonb; e_ jsonb; span_ jsonb; source_ref_ jsonb; prior_ jsonb;
BEGIN
 SELECT v INTO STRICT reading FROM jsonb_array_elements(rows_) v WHERE v->>'contribution_id'=ref->>'contribution_id';
 component:=reading->'component'; pin:=reading->'pin';
 SELECT v INTO STRICT frame FROM jsonb_array_elements(rows_) v WHERE v->>'contribution_id'=component->>'frame';
 IF component->>'kind' IS DISTINCT FROM 'predicate_reading' OR frame->'component'->>'kind' IS DISTINCT FROM 'predicate_frame'
  OR frame->'pin' IS DISTINCT FROM pin OR ref->>'project_id' IS DISTINCT FROM source_->>'project_id'
  OR pin->'source_view_id' IS DISTINCT FROM source_->'source_view_id' OR pin->'native_product_task_id' IS DISTINCT FROM source_->'native_task_id'
  OR pin->>'product_digest' IS DISTINCT FROM source_->>'native_content_digest' OR pin->>'projection_digest' IS DISTINCT FROM source_->>'projection_digest'
  OR pin->>'recipe_digest' IS DISTINCT FROM source_->>'recipe_digest'
  OR component->>'scope' IS DISTINCT FROM passage->>'passage_id' OR frame->'component'->>'scope' IS DISTINCT FROM passage->>'passage_id'
  OR component->>'effective_version' IS DISTINCT FROM passage->>'effective_version'
  OR frame->'component'->>'effective_version' IS DISTINCT FROM passage->>'effective_version' THEN
  RAISE EXCEPTION 'retained frame differs from exact selected passage' USING ERRCODE='23514';END IF;
 FOR item IN SELECT v FROM jsonb_array_elements(frame->'component'->'frame_members') v LOOP
  IF item->>'role'='focus' AND item->>'outcome'='complete' AND jsonb_array_length(item->'extents')=1 THEN focus:=item->'extents'->0;controls:=controls||(item->'extents');END IF;
  dimension:=CASE item->>'role' WHEN 'predicate' THEN 'action' WHEN 'actor' THEN 'actor' WHEN 'object' THEN 'object' END;
  IF dimension IS NULL THEN CONTINUE;END IF;
  field_:=ops.comparison_member(passage,dimension,item->'extents',item->>'contribution',source_,layers);
  IF field_ IS NOT NULL THEN fields:=jsonb_set(fields,ARRAY[dimension],COALESCE(fields->dimension,'[]')||jsonb_build_array(field_));END IF;
  IF field_ IS NULL OR item->>'outcome' IS DISTINCT FROM 'complete' THEN incomplete:=array_append(incomplete,dimension);END IF;
 END LOOP;
 FOR item IN SELECT v FROM jsonb_array_elements(frame->'component'->'unlocated_roles') v LOOP
  dimension:=CASE item->>'role' WHEN 'actor' THEN 'actor' WHEN 'object' THEN 'object' END;
  IF dimension IS NOT NULL THEN incomplete:=array_append(incomplete,dimension);END IF;
 END LOOP;
 FOR item IN SELECT v FROM jsonb_array_elements(rows_) v
  WHERE v->'component'->>'kind'='predicate_cue' AND v->'component'->>'host_state'='unresolved'
   AND v->'component'->>'scope'=frame->'component'->>'scope'
   AND v->'component'->>'annotation'=frame->'component'->>'annotation'
   AND v->'component'->'candidate_tokens' @> jsonb_build_array(frame->'component'->'predicate_token')
 LOOP
  dimension:=CASE item->'component'->>'cue_kind'
   WHEN 'condition' THEN 'condition' WHEN 'assumption' THEN 'condition' WHEN 'exception' THEN 'exception'
   WHEN 'modality' THEN 'modality' WHEN 'order' THEN 'order_dependency' WHEN 'dependency' THEN 'order_dependency' END;
  IF dimension IS NOT NULL THEN incomplete:=array_append(incomplete,dimension);END IF;
 END LOOP;
 FOR item IN SELECT v FROM jsonb_array_elements(rows_) v
  WHERE v->'component'->>'kind'='predicate_qualifier' AND v->'component'->>'host_contribution_id'=frame->>'contribution_id'
 LOOP
  dimension:=CASE item->'component'->>'qualifier_kind'
   WHEN 'condition' THEN 'condition' WHEN 'assumption' THEN 'condition' WHEN 'exception' THEN 'exception'
   WHEN 'modality' THEN 'modality' WHEN 'order' THEN 'order_dependency' WHEN 'dependency' THEN 'order_dependency' END;
  IF dimension IS NULL THEN CONTINUE;END IF;
  SELECT v INTO STRICT cue FROM jsonb_array_elements(rows_) v WHERE v->>'contribution_id'=item->'component'->>'qualifier_contribution_id';
  IF cue->'pin' IS DISTINCT FROM pin THEN RAISE EXCEPTION 'comparison qualifier differs from selected source' USING ERRCODE='23514';END IF;
  field_:=ops.comparison_member(passage,dimension,cue->'component'->'extents',item->>'contribution_id',source_,layers);
  IF field_ IS NOT NULL AND item->'component' ? 'condition' THEN
   field_:=field_||jsonb_build_object('condition',item->'component'->'condition');
  END IF;
  IF field_ IS NULL THEN incomplete:=array_append(incomplete,dimension);
  ELSE fields:=jsonb_set(fields,ARRAY[dimension],COALESCE(fields->dimension,'[]')||jsonb_build_array(field_));END IF;
  IF dimension='condition' THEN controls:=controls||(cue->'component'->'extents');END IF;
 END LOOP;
 FOREACH dimension IN ARRAY ARRAY['parent','version'] LOOP
  label:=passage->>CASE dimension WHEN 'parent' THEN 'parent' ELSE 'effective_version' END;
  IF label IS NOT NULL THEN
   fields:=jsonb_set(fields,ARRAY[dimension],jsonb_build_array(jsonb_build_object('dimension',dimension,'lexical_value',label,'evidence',jsonb_build_array(passage->>'passage_id'))));
  END IF;
 END LOOP;
 inventory_:=ops.structural_threshold_field(passage,source_,layers);
 IF inventory_->'complete' IS DISTINCT FROM 'true'::jsonb THEN incomplete:=array_append(incomplete,'threshold_unit'); END IF;
 FOR field_ IN SELECT v FROM jsonb_array_elements(inventory_->'fields') v LOOP
  IF EXISTS(SELECT FROM jsonb_array_elements(controls) c
   WHERE (c->>'start')::integer<=(field_->'typed'->'span'->>'start')::integer
    AND (c->>'end')::integer>=(field_->'typed'->'span'->>'end')::integer) THEN
   fields:=jsonb_set(fields,ARRAY['threshold_unit'],COALESCE(fields->'threshold_unit','[]')||jsonb_build_array(field_));
  END IF;
 END LOOP;
 FOREACH dimension IN ARRAY ARRAY['actor','action','object','modality','condition','threshold_unit','exception','order_dependency','parent','version'] LOOP
  SELECT COALESCE(jsonb_agg(m ORDER BY COALESCE(m->'spans'->0->>'start',m->'typed'->'span'->>'start')::integer,m->>'contribution_id'),'[]')
   INTO members FROM jsonb_array_elements(COALESCE(fields->dimension,'[]')) m;
  witnesses:='[]';primary_:='[]';grouping:=NULL;
  IF dimension=ANY(incomplete) THEN state:='unresolved';IF jsonb_array_length(members)>0 THEN grouping:='unresolved';END IF;
  ELSIF jsonb_array_length(members)=0 THEN state:='absent';
  ELSIF jsonb_array_length(members)=1 THEN state:='present';grouping:='singleton';
  ELSE
   state:='present';grouping:='unresolved';previous:=NULL;marker:=NULL;
   FOR item IN SELECT v FROM jsonb_array_elements(members) v LOOP
    IF previous IS NOT NULL THEN
     lo:=COALESCE(previous->'spans'->-1->>'end',previous->'typed'->'span'->>'end')::integer;
     hi:=COALESCE(item->'spans'->0->>'start',item->'typed'->'span'->>'start')::integer;
     IF hi<=lo THEN witnesses:='[]';EXIT;END IF;
     prior_:=passage||jsonb_build_object('start',lo,'end',hi);
     facts_:=ops.comparison_primary_lexical(prior_,source_,layers,'formal.coordination_cue');
     IF jsonb_array_length(facts_)<>1 OR NOT ops.comparison_primary_covered(layers,source_,'formal.lexical',lo,hi) THEN witnesses:='[]';primary_:='[]';EXIT; END IF;
     fact_:=facts_->0;tokens_:='[]';
     FOR l_ IN SELECT * FROM jsonb_each(layers) LOOP
      IF NOT ops.comparison_primary_covered(jsonb_build_object(l_.key,l_.value),source_,'formal.lexical',lo,hi) THEN CONTINUE; END IF;
      FOR a_ IN SELECT value FROM jsonb_array_elements(l_.value->'annotations') WHERE value->>'kind'='formal.token' AND value ? 'formal' LOOP
       source_ref_:=jsonb_build_object('layer',l_.key::jsonb,'local_id',a_->'formal'->>'input_id');
       IF ops.primary_characterization_node(layers,source_ref_)->'formal_input'->>'start_symbol' IS DISTINCT FROM 'lex' THEN CONTINUE; END IF;
       source_ref_:=jsonb_build_object('layer',l_.key::jsonb,'local_id',a_->>'local_id');e_:=ops.comparison_primary_extent(layers,source_ref_,source_);
       IF e_ IS NOT NULL AND (e_->>'start')::bigint<hi AND lo<(e_->>'end')::bigint THEN
        tokens_:=tokens_||jsonb_build_array(jsonb_build_array(source_ref_->'layer',e_->'start',e_->'end')); END IF;
      END LOOP;
     END LOOP;
     IF tokens_ IS DISTINCT FROM jsonb_build_array(jsonb_build_array(fact_->'reference'->'layer',fact_->'span'->'start',fact_->'span'->'end'))
      OR fact_->>'value' NOT IN ('and','or') OR (marker IS NOT NULL AND marker<>fact_->>'value') THEN witnesses:='[]';primary_:='[]';EXIT; END IF;
     marker:=fact_->>'value';witnesses:=witnesses||jsonb_build_array(fact_->'span');primary_:=primary_||jsonb_build_array(fact_->'reference');
    END IF;
    previous:=item;
   END LOOP;
   IF jsonb_array_length(witnesses)=jsonb_array_length(members)-1 THEN grouping:=CASE marker WHEN 'and' THEN 'conjunction' ELSE 'disjunction' END;END IF;
  END IF;
  groups:=jsonb_set(groups,ARRAY[dimension],jsonb_strip_nulls(jsonb_build_object('state',state,'grouping',grouping,'members',members,'witnesses',witnesses))||CASE WHEN primary_='[]'::jsonb THEN '{}'::jsonb ELSE jsonb_build_object('primary_witnesses',primary_) END);
 END LOOP;
 IF jsonb_array_length(groups->'exception'->'members')=0 OR
  (jsonb_array_length(groups->'exception'->'members')=1 AND jsonb_array_length(groups->'exception'->'members'->0->'spans')=1) THEN
  empty_:='[]';primary_:='[]';
  FOR span_ IN SELECT v FROM jsonb_array_elements(COALESCE(groups->'exception'->'members'->0->'spans','[]')) v
   UNION ALL SELECT ops.comparison_member(passage,'exception',jsonb_build_array(focus),NULL,source_,layers)->'spans'->0 WHERE focus IS NOT NULL LOOP
   facts_:=ops.comparison_primary_lexical(passage||jsonb_build_object('start',span_->'start','end',span_->'end'),source_,layers,'formal.exception_empty');
   IF jsonb_array_length(facts_)<>1 THEN CONTINUE; END IF;
   fact_:=facts_->0;
   IF fact_->>'value' IS DISTINCT FROM 'empty' THEN CONTINUE; END IF;
   IF substring(passage->>'text' FROM (span_->>'start')::integer-(passage->>'start')::integer+1 FOR (fact_->'span'->>'start')::integer-(span_->>'start')::integer) ~ '^\s*$'
    AND btrim(substring(passage->>'text' FROM (fact_->'span'->>'end')::integer-(passage->>'start')::integer+1 FOR (span_->>'end')::integer-(fact_->'span'->>'end')::integer),E' \t\n\r') IN ('','.') THEN
    empty_:=empty_||jsonb_build_array(fact_->'span');primary_:=primary_||jsonb_build_array(fact_->'reference'); END IF;
  END LOOP;
  IF jsonb_array_length(empty_)=1 THEN groups:=jsonb_set(groups,ARRAY['exception'],jsonb_build_object('state','empty','members','[]'::jsonb,'witnesses',empty_,'primary_witnesses',primary_)); END IF;
 END IF;
 IF jsonb_array_length(groups->'threshold_unit'->'members')>0 AND
  'unresolved' IN (groups->'condition'->>'state',groups->'condition'->>'grouping') THEN
  groups:=jsonb_set(groups,ARRAY['threshold_unit'],((groups->'threshold_unit')-'primary_witnesses')||jsonb_build_object('state','unresolved','grouping','unresolved','witnesses','[]'::jsonb));
 END IF;
 RETURN groups;
END $$;
REVOKE ALL ON FUNCTION ops.comparison_groups(jsonb,jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_typed_member(member jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH fields AS (
  SELECT member->'typed' AS threshold,member->'literal' AS literal,member->'condition' AS condition_
 ), normalized AS (
  SELECT *,CASE WHEN condition_->>'kind'='not' THEN condition_->'term' ELSE condition_ END AS comparison
  FROM fields
 )
 SELECT CASE
  WHEN threshold->>'state'='parsed' AND threshold->>'quantity' IS NOT NULL
   AND threshold->>'unit' IS NOT NULL AND threshold->>'basis' IS NOT NULL
  THEN jsonb_build_array(
   jsonb_build_array('threshold',threshold->'quantity',threshold->'unit',threshold->'basis'),
   jsonb_build_array(threshold->'comparator',threshold->'value'))
  WHEN literal->>'kind' IN ('date','identifier')
  THEN jsonb_build_array(jsonb_build_array(literal->'kind'),literal->'value')
  WHEN comparison->>'kind'='compare'
  THEN jsonb_build_array(jsonb_build_array('condition',condition_->>'kind'='not'),
   jsonb_build_array(comparison->'lhs',comparison->'relation',comparison->'rhs'))
 END FROM normalized
$$;
REVOKE ALL ON FUNCTION ops.comparison_typed_member(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_group_members(l jsonb,r jsonb,compatible boolean)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH members AS (
  SELECT side,n-1 AS i,typed->0 AS key,typed->1 AS value
  FROM (VALUES ('left',l),('right',r)) AS groups(side,g)
  CROSS JOIN LATERAL jsonb_array_elements(g->'members') WITH ORDINALITY x(member,n)
  CROSS JOIN LATERAL (SELECT ops.comparison_typed_member(member) AS typed) t
  WHERE typed IS NOT NULL
 ), grouped AS (
  SELECT side,key,count(*) AS size,min(i) AS i,(jsonb_agg(value ORDER BY i))->0 AS value
  FROM members GROUP BY side,key
 ), matches AS (
  SELECT a.i AS li,b.i AS ri,a.size<>1 OR b.size<>1 AS ambiguous,a.value=b.value AS equal_
  FROM grouped a JOIN grouped b USING(key) WHERE a.side='left' AND b.side='right'
 ), result AS (
  SELECT count(*) FILTER(WHERE NOT ambiguous) AS size,
   bool_or(ambiguous) AS ambiguous,bool_and(equal_) FILTER(WHERE NOT ambiguous) AS equal_,
   coalesce(jsonb_agg(jsonb_build_object('left_index',li,'right_index',ri,
    'outcome',CASE WHEN equal_ THEN 'equivalent' ELSE 'different' END)
    ORDER BY li) FILTER(WHERE NOT ambiguous),'[]') AS decisions FROM matches
 ), state AS (
  SELECT *,CASE
   WHEN NOT compatible OR 'unresolved' IN (l->>'state',r->>'state',l->>'grouping',r->>'grouping')
    OR 'absent' IN (l->>'state',r->>'state') THEN 'unresolved'
   WHEN l->>'grouping' IS NOT DISTINCT FROM r->>'grouping' THEN 'same'
   ELSE 'different' END AS grouping FROM result
 )
 SELECT jsonb_build_object('grouping_outcome',grouping,
  'member_comparisons',CASE WHEN grouping='unresolved' THEN '[]'::jsonb ELSE decisions END,
  'typed_outcome',CASE
   WHEN compatible AND 'unresolved' IN (l->>'state',r->>'state',l->>'grouping',r->>'grouping') THEN 'ambiguous'
   WHEN grouping='unresolved' THEN 'unknown'
   WHEN ambiguous THEN 'ambiguous'
   WHEN size=0 OR size<>jsonb_array_length(l->'members') OR size<>jsonb_array_length(r->'members') THEN 'unknown'
   WHEN grouping='different' OR NOT equal_ THEN 'different'
   ELSE 'equivalent' END) FROM state
$$;
REVOKE ALL ON FUNCTION ops.comparison_group_members(jsonb,jsonb,boolean) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_grouped_comparison(t ops.task,inputs jsonb,config jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE refs jsonb:=jsonb_build_array(config->'left_reading',config->'right_reading'); retained record;
 left_ jsonb;right_ jsonb;source_ jsonb;lg jsonb;rg jsonb;l jsonb;r jsonb;dim text;
 xf jsonb:='{}';yf jsonb:='{}';out_ jsonb;dims jsonb:='[]';entry jsonb;lexical text;
 compatible boolean;all_match boolean:=true; typed_compatible boolean; interval_applicable boolean;
 current_ boolean:=true; group_detail jsonb;
 focus_ jsonb; lf jsonb; rf jsonb; primary_ jsonb:='{}'; layers jsonb; view_ kb.source_view; source_id text;
BEGIN
 FOR source_ IN SELECT value FROM jsonb_array_elements(inputs->'sources') LOOP
  SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
  source_id:=encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(source_)),'UTF8')),'hex');
  primary_:=primary_||jsonb_build_object(source_id,ops.primary_characterization_layers(t,view_,config));
 END LOOP;
 SELECT p INTO STRICT left_ FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'passage_id'=config->>'left_id';
 SELECT p INTO STRICT right_ FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'passage_id'=config->>'right_id';
 IF left_=right_ OR refs->0=refs->1 THEN RAISE EXCEPTION 'comparison requires distinct retained readings' USING ERRCODE='23514'; END IF;
 FOR retained IN SELECT * FROM ops.resolve_retained_source_contributions(refs) LOOP
  IF NOT EXISTS(SELECT FROM jsonb_array_elements(retained.contributions) c
   WHERE c->>'contribution_id'=retained.reference->>'contribution_id'
    AND c->'component'->>'question_version'='6') THEN
   RAISE EXCEPTION 'typed comparison requires a current predicate reading' USING ERRCODE='23514'; END IF;
  IF NOT inputs->'dependencies' ? (retained.reference->>'contribution_id') THEN
   RAISE EXCEPTION 'comparison lacks frozen retained reading dependency' USING ERRCODE='23514';END IF;
  IF retained.reference=refs->0 THEN
   SELECT s INTO STRICT source_ FROM jsonb_array_elements(inputs->'sources') s
    WHERE encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')=left_->>'source_ref';
   lg:=ops.comparison_groups(left_,source_,retained.reference,retained.contributions,primary_->(left_->>'source_ref'));
  ELSE
   SELECT s INTO STRICT source_ FROM jsonb_array_elements(inputs->'sources') s
    WHERE encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')=right_->>'source_ref';
   rg:=ops.comparison_groups(right_,source_,retained.reference,retained.contributions,primary_->(right_->>'source_ref'));
  END IF;
  IF current_ THEN
   SELECT role->'extents'->0 INTO focus_ FROM jsonb_array_elements(retained.contributions) reading
   JOIN LATERAL jsonb_array_elements(retained.contributions) frame
    ON frame->>'contribution_id'=reading->'component'->>'frame'
   CROSS JOIN LATERAL jsonb_array_elements(frame->'component'->'frame_members') role
   WHERE reading->>'contribution_id'=retained.reference->>'contribution_id'
    AND role->>'role'='focus' AND role->>'outcome'='complete'
    AND jsonb_array_length(role->'extents')=1;
   IF focus_ IS NOT NULL THEN
    IF retained.reference=refs->0 THEN
     lf:=ops.comparison_member(left_,'action',jsonb_build_array(focus_),NULL,source_,primary_->(left_->>'source_ref'))->'spans'->0;
    ELSE
     rf:=ops.comparison_member(right_,'action',jsonb_build_array(focus_),NULL,source_,primary_->(right_->>'source_ref'))->'spans'->0;
    END IF;
   END IF;
  END IF;
 END LOOP;
 IF lg IS NULL OR rg IS NULL THEN RAISE EXCEPTION 'comparison lacks both retained readings' USING ERRCODE='23514';END IF;
 FOR dim IN SELECT key FROM jsonb_each(lg) LOOP
  IF lg->dim->>'grouping'='singleton' THEN xf:=jsonb_set(xf,ARRAY[dim],lg->dim->'members'->0);END IF;
  IF rg->dim->>'grouping'='singleton' THEN yf:=jsonb_set(yf,ARRAY[dim],rg->dim->'members'->0);END IF;
 END LOOP;
 out_:=ops.structural_compare_lexical(inputs,config->>'left_id',config->>'right_id',xf,yf,primary_);
 compatible:=left_->>'scope'=right_->>'scope' AND (left_->>'effective_version' IS NOT DISTINCT FROM right_->>'effective_version' OR out_ ? 'succession');
 typed_compatible:=compatible AND (left_->>'effective_version' IS NOT NULL OR out_ ? 'succession');
 interval_applicable:=typed_compatible AND NOT EXISTS(SELECT FROM
  (SELECT value FROM jsonb_each(lg) UNION ALL SELECT value FROM jsonb_each(rg)) g
  WHERE 'unresolved' IN (value->>'state',value->>'grouping'));
 FOR entry IN SELECT v FROM jsonb_array_elements(out_->'dimensions') v LOOP
  dim:=entry->>'dimension';l:=lg->dim;r:=rg->dim;
  lexical:='unknown';
  IF NOT compatible THEN lexical:='incompatible_applicability';
   entry:=(entry-ARRAY['added_interval','removed_interval'])||jsonb_build_object('typed_outcome','unknown','assumptions','[]'::jsonb,'reason','No complete source-qualified typed premises.');
  ELSE
   IF l->>'state' IN ('present','empty') AND r->>'state' IN ('present','empty') THEN
    lexical:=CASE WHEN jsonb_path_query_array(l,'$.members[*].lexical_value')=jsonb_path_query_array(r,'$.members[*].lexical_value')
     THEN 'same_lexical_value' ELSE 'different_lexical_value' END;
   END IF;
   IF 'unresolved' IN (l->>'state',r->>'state',l->>'grouping',r->>'grouping') THEN
    entry:=entry||jsonb_build_object('typed_outcome','ambiguous');
   END IF;
  END IF;
  IF current_ THEN
   group_detail:=ops.comparison_group_members(l,r,typed_compatible);
   IF dim<>'threshold_unit' OR NOT interval_applicable
    OR entry->>'reason'<>'Exact threshold consequence only; other rule dimensions remain separate.' THEN
    entry:=(entry-ARRAY['added_interval','removed_interval'])||group_detail||
     jsonb_build_object('assumptions','[]'::jsonb,'reason',CASE
      WHEN jsonb_array_length(group_detail->'member_comparisons')>0
       THEN 'Compared source-qualified members by their unique typed keys.'
      ELSE 'No complete source-qualified typed premises.' END);
   ELSE entry:=entry||(group_detail-'typed_outcome');
   END IF;
  END IF;
  IF dim<>'threshold_unit' AND (lexical<>'same_lexical_value' OR l->>'grouping' IS DISTINCT FROM r->>'grouping' OR l->>'grouping'='unresolved') THEN all_match:=false;END IF;
  dims:=dims||jsonb_build_array((entry-ARRAY['left','right'])||jsonb_build_object('outcome',lexical,'left_group',l,'right_group',r));
 END LOOP;
 IF out_->>'applicability' NOT IN ('differently_scoped','successive_revisions')
  AND left_->>'effective_version' IS NOT NULL AND left_->>'effective_version'=right_->>'effective_version' THEN
  out_:=out_||CASE WHEN all_match THEN jsonb_build_object('applicability','co_applicable','applicability_reason','All non-threshold dimensions match under explicit scope/version.')
   ELSE jsonb_build_object('applicability','unestablished','applicability_reason','Missing or changed applicability dimensions remain material.') END;
 END IF;
 RETURN out_||jsonb_strip_nulls(jsonb_build_object(
  'dimensions',dims,'left_reading',refs->0,'right_reading',refs->1,'left_focus',lf,'right_focus',rf));
END $$;
REVOKE ALL ON FUNCTION ops.structural_grouped_comparison(ops.task,jsonb,jsonb) FROM PUBLIC;

-- Membership comes exclusively from authenticated current predecessor output roles.
-- Display selection has no authority to create a member or a supported facet.
CREATE OR REPLACE FUNCTION ops.dossier_comparison_roles(reference jsonb,report jsonb,selection_ jsonb,relationship jsonb,root_ref jsonb,root_ jsonb)
RETURNS SETOF jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE comparison jsonb:=jsonb_strip_nulls(report->'comparison');side_ text:=selection_->>'side';opposite_side text;
 passage jsonb;opposite jsonb;source_ jsonb;opposite_source jsonb;citation jsonb;opposite_citation jsonb;
 occurrence jsonb;binding jsonb;role_span jsonb;exception_group jsonb;focus_ jsonb;
 premise jsonb:=selection_->'_applicability'; usage_ jsonb; applicable boolean;
 contradiction jsonb:=nullif(selection_->'_conflict_passage','null');
 left_text text:=comparison->'left_focus'->>'text'; right_text text:=comparison->'right_focus'->>'text';
BEGIN
 IF side_ IS NULL OR side_ NOT IN ('left','right') OR NOT comparison ?& ARRAY['left_reading','right_reading'] THEN
  RAISE EXCEPTION 'root binding requires a current retained grouped comparison' USING ERRCODE='23514'; END IF;
 opposite_side:=CASE side_ WHEN 'left' THEN 'right' ELSE 'left' END;
 SELECT p INTO STRICT passage FROM jsonb_array_elements(report->'inputs'->'passages') p WHERE p->>'passage_id'=comparison->>(side_||'_id');
 SELECT p INTO STRICT opposite FROM jsonb_array_elements(report->'inputs'->'passages') p WHERE p->>'passage_id'=comparison->>(opposite_side||'_id');
 SELECT s INTO STRICT source_ FROM jsonb_array_elements(report->'inputs'->'sources') s
  WHERE encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')=passage->>'source_ref';
 SELECT s INTO STRICT opposite_source FROM jsonb_array_elements(report->'inputs'->'sources') s
  WHERE encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')=opposite->>'source_ref';
 IF relationship->'edge'->>'relation' NOT IN ('denotes','defined-by','specializes')
  OR relationship->'decision'->>'scope' IS DISTINCT FROM passage->>'scope'
  OR root_->>'scope' IS DISTINCT FROM passage->>'scope' OR nullif(passage->>'effective_version','') IS NULL
  OR relationship->'decision'->>'effective_version' IS DISTINCT FROM passage->>'effective_version'
  OR root_->>'effective_version' IS DISTINCT FROM passage->>'effective_version'
  OR relationship->'source_view_id' IS DISTINCT FROM source_->'source_view_id'
  OR selection_->'relationship_ref'->'project_id' IS DISTINCT FROM source_->'project_id'
  OR selection_->'relationship_ref'->'release_id' IS DISTINCT FROM source_->'release_id'
  OR NOT relationship->'edge'->'member_target_ids' ? (root_->>'component_id')
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(relationship->'component_targets') target WHERE target->'reference'=root_ref) THEN
  RAISE EXCEPTION 'comparison side lacks the exact scoped root relationship' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(relationship->'located_occurrence')=0 OR EXISTS(
  SELECT FROM jsonb_array_elements(relationship->'located_occurrence') span
  WHERE (span->>'start')::integer<(passage->>'start')::integer OR (span->>'end')::integer>(passage->>'end')::integer
   OR span->>'text' IS DISTINCT FROM substring(passage->>'text' FROM (span->>'start')::integer-(passage->>'start')::integer+1 FOR (span->>'end')::integer-(span->>'start')::integer)) THEN
  RAISE EXCEPTION 'relationship occurrence is outside the exact comparison side' USING ERRCODE='23514'; END IF;
 focus_:=comparison->(side_||'_focus');
 IF (selection_->>'_require_focus')::boolean AND focus_ IS NULL THEN
  RAISE EXCEPTION 'comparison side has no exact retained reading focus' USING ERRCODE='23514'; END IF;
 IF focus_ IS NOT NULL AND EXISTS(
  SELECT FROM jsonb_array_elements(relationship->'located_occurrence') span
  WHERE (span->>'start')::integer<(focus_->>'start')::integer
   OR (span->>'end')::integer>(focus_->>'end')::integer) THEN
  RAISE EXCEPTION 'relationship occurrence is outside the exact comparison focus' USING ERRCODE='23514'; END IF;
 IF selection_ ? 'applicability_ref' THEN
  SELECT p INTO usage_ FROM jsonb_array_elements(premise->'inputs'->'passages') p
   WHERE p->>'passage_id'=premise->'definition'->>'usage_id';
  IF premise->>'kind' IS DISTINCT FROM 'definition_applicability' OR usage_ IS NULL OR focus_ IS NULL
   OR usage_->>'source_ref' IS DISTINCT FROM passage->>'source_ref'
   OR usage_->>'scope' IS DISTINCT FROM passage->>'scope'
   OR usage_->>'effective_version' IS DISTINCT FROM passage->>'effective_version'
   OR (usage_->>'start')::integer<(focus_->>'start')::integer
   OR (usage_->>'end')::integer>(focus_->>'end')::integer
   OR usage_->'start' IS DISTINCT FROM relationship->'located_occurrence'->0->'start'
   OR usage_->'end' IS DISTINCT FROM relationship->'located_occurrence'->(-1)->'end'
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(premise->'definition'->'readings') r
    WHERE r->'component_ref'=root_ref
    AND (r->'link_ref'=selection_->'relationship_ref' OR relationship->'edge'->>'relation'='specializes')
    AND r->>'outcome' IN ('applicable_definition','applicable_explanation')) THEN
   RAISE EXCEPTION 'comparison applicability differs from exact focus, root, or relationship' USING ERRCODE='23514'; END IF;
 END IF;
 applicable:=NOT coalesce((selection_->>'_require_focus')::boolean,false) OR selection_ ? 'applicability_ref';
 SELECT jsonb_agg(span||jsonb_build_object('passage_id',passage->>'passage_id') ORDER BY n) INTO occurrence
 FROM jsonb_array_elements(relationship->'located_occurrence') WITH ORDINALITY spans(span,n);
 citation:=passage-ARRAY['source_ref','scope','effective_version','parent'];
 opposite_citation:=opposite-ARRAY['source_ref','scope','effective_version','parent'];
 binding:=jsonb_build_object('comparison_ref',reference,'side',side_,'relationship_ref',selection_->'relationship_ref',
  'relationship',relationship->'edge'->'relation','root',root_ref,'source',source_,'citation',citation,
  'occurrence',occurrence,'comparison',comparison,'opposite_source',opposite_source,'opposite_citation',opposite_citation);
 IF selection_ ? 'applicability_ref' THEN
  binding:=binding||jsonb_build_object('applicability_ref',selection_->'applicability_ref'); END IF;
 IF selection_ ? 'conflict_passage_id' THEN
  IF contradiction IS NULL OR NOT selection_ ? 'applicability_ref'
   OR comparison->>'applicability' IS DISTINCT FROM 'co_applicable'
   OR contradiction->>'scope' IS DISTINCT FROM passage->>'scope'
   OR contradiction->>'effective_version' IS DISTINCT FROM passage->>'effective_version'
   OR left_text IS NULL OR right_text IS NULL OR left_text=right_text
   OR strpos(left_text,'"')>0 OR strpos(right_text,'"')>0
   OR contradiction->>'text' NOT IN (
    '"'||left_text||'" contradicts "'||right_text||'".',
    '"'||right_text||'" contradicts "'||left_text||'".') THEN
   RAISE EXCEPTION 'dossier conflict requires an exact explicit contradiction of both readings' USING ERRCODE='23514'; END IF;
  binding:=binding||jsonb_build_object('conflict_evidence',
   contradiction-ARRAY['source_ref','scope','effective_version','parent']);
  RETURN NEXT jsonb_build_object('role','conflict','span',citation,'comparison_binding',binding);
 END IF;
 IF comparison->'succession'->'newer_id'=passage->'passage_id' THEN
  RETURN NEXT jsonb_build_object('role','revision','span',comparison->'succession'->'evidence','comparison_binding',binding); END IF;
 SELECT d->(side_||'_group') INTO exception_group FROM jsonb_array_elements(comparison->'dimensions') d WHERE d->>'dimension'='exception';
 IF applicable AND relationship->'edge'->>'relation'='specializes' AND exception_group->>'state'='present' THEN
  FOR role_span IN SELECT span FROM jsonb_array_elements(exception_group->'members') field
   CROSS JOIN LATERAL jsonb_array_elements(field->'spans') span LOOP
   RETURN NEXT jsonb_build_object('role','exception','span',role_span,'comparison_binding',binding);
  END LOOP;
 END IF;
 IF contradiction IS NULL AND applicable AND comparison->>'applicability'='co_applicable' AND EXISTS(
  SELECT FROM jsonb_array_elements(comparison->'dimensions') d WHERE d->>'typed_outcome'='different') THEN
  RETURN NEXT jsonb_build_object('role','variant','span',citation,'comparison_binding',binding); END IF;
 RETURN NEXT jsonb_build_object('role','relationship','span',citation,'comparison_binding',binding);
END $$;
REVOKE ALL ON FUNCTION ops.dossier_comparison_roles(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_dossier(inputs jsonb,config jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference jsonb;retained jsonb;report jsonb;roles jsonb;role_ jsonb;c jsonb;r jsonb;span_ jsonb;p jsonb;assertion_ jsonb;expected_statement jsonb;assessment text;key_ text;member_ jsonb;members jsonb:='[]';facets jsonb:='[]';seen jsonb:='{}';selected jsonb:='[]';omitted jsonb;represented jsonb;missing jsonb;sections jsonb;budget integer:=(config->>'member_budget')::integer;mandatory integer;candidate record;membership_digest text;facet_digest text;representation jsonb; root_ref jsonb:=nullif(config->'root_component','null'); root_ jsonb; sense_ text;
 bindings jsonb:=COALESCE(config->'comparison_selections','[]'); binding_ jsonb; relationship_ref jsonb; relationships jsonb:='{}'; relationship_key text;
BEGIN
 IF root_ref IS NULL OR NOT COALESCE(config->'predecessors','[]') @> jsonb_build_array(root_ref-ARRAY['component_id','operation_id','operation_version','dependencies']) THEN
  RAISE EXCEPTION 'dossier requires exact root component predecessor' USING ERRCODE='23514';
 END IF;
 root_:=ops.resolve_retained_component(root_ref)->'component';sense_:=root_->>'component_id';
 IF budget<1 OR config->>'policy' NOT IN ('supported-facet-greedy-1','source-order-control-1') OR jsonb_array_length(COALESCE(config->'predecessors','[]'))+jsonb_array_length(COALESCE(config->'contribution_predecessors','[]'))=0 THEN RAISE EXCEPTION 'invalid current dossier selection policy' USING ERRCODE='23514';END IF;
 IF (SELECT count(*)<>count(DISTINCT v->>'product_id') FROM jsonb_array_elements(config->'predecessors')v) THEN RAISE EXCEPTION 'duplicate dossier predecessor' USING ERRCODE='23514';END IF;
 IF (SELECT count(*)<>count(DISTINCT b) FROM jsonb_array_elements(bindings)b) OR EXISTS(
  SELECT FROM jsonb_array_elements(bindings)b WHERE NOT inputs->'dependencies' ? (b->'relationship_ref'->>'edge_id')
  OR (b ? 'applicability_ref' AND NOT COALESCE(config->'predecessors','[]') @> jsonb_build_array(b->'applicability_ref'))
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(config->'predecessors') predecessor WHERE predecessor->'product_id'=b->'comparison_product_id')) THEN
  RAISE EXCEPTION 'dossier comparison binding requires exact declared dependencies' USING ERRCODE='23514'; END IF;
 FOR relationship_ref IN SELECT DISTINCT b->'relationship_ref' FROM jsonb_array_elements(bindings)b LOOP
  relationships:=relationships||jsonb_build_object(data.canonical_json(relationship_ref),ops.resolve_retained_relationship_decision(relationship_ref));
 END LOOP;
 FOR reference IN SELECT value FROM jsonb_array_elements(config->'predecessors') LOOP
  IF NOT inputs->'dependencies' ? (reference->>'product_id') THEN RAISE EXCEPTION 'dossier predecessor outside dependencies' USING ERRCODE='23514';END IF;
  retained:=ops.resolve_retained_structural_report(reference);report:=retained->'report';roles:='[]';
  IF report->>'kind'<>'qualified_comparison' AND EXISTS(SELECT FROM jsonb_array_elements(bindings)b WHERE b->'comparison_product_id'=reference->'product_id') THEN
   RAISE EXCEPTION 'comparison selection requires a qualified comparison predecessor' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(report->'inputs'->'passages') source_passage(value) WHERE NOT inputs->'passages' @> jsonb_build_array(source_passage.value)) THEN RAISE EXCEPTION 'dossier predecessor substitutes original passage' USING ERRCODE='23514';END IF;
  IF report->>'kind'='definition_components' THEN
   FOR c IN SELECT value FROM jsonb_array_elements(report->'definition_components'->'components') WHERE value->>'component_id'=sense_ LOOP
    roles:=roles||jsonb_build_array(jsonb_build_object('role','terminology','span',c->'term','component_id',c->>'component_id','definition_interpretation',c->>'interpretation'),jsonb_build_object('role',CASE c->>'interpretation' WHEN 'definition' THEN 'definition' WHEN 'explanation' THEN 'usage' ELSE 'unresolved_sense' END,'span',c->'content','component_id',c->>'component_id','definition_interpretation',c->>'interpretation'));
   END LOOP;
  ELSIF report->>'kind'='definition_applicability' THEN
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(report->'definition'->'readings') rr WHERE rr->'component'->>'component_id'=sense_) THEN CONTINUE;END IF;
   SELECT value INTO STRICT p FROM jsonb_array_elements(inputs->'passages') WHERE value->>'passage_id'=report->'definition'->>'usage_id';
   roles:=roles||jsonb_build_array(jsonb_build_object('role','usage','span',p-ARRAY['source_ref','scope','effective_version','parent']));
   FOR r IN SELECT value FROM jsonb_array_elements(report->'definition'->'readings') WHERE value->'component'->>'component_id'=sense_ LOOP roles:=roles||jsonb_build_array(jsonb_build_object('role',CASE WHEN r->>'outcome'='incompatible' THEN 'relationship' WHEN r->>'outcome' IN ('mention','example','applicable_explanation') THEN 'usage' WHEN r->>'outcome'='unresolved' OR r->'component'->>'interpretation'='unresolved' THEN 'unresolved_sense' WHEN r->'component'->>'interpretation'='explanation' THEN 'usage' ELSE 'definition' END,'span',r->'component'->'content','definition_interpretation',r->'component'->>'interpretation','applicability_outcome',r->>'outcome'));END LOOP;
  ELSIF report->>'kind'='qualified_comparison' THEN
   FOR binding_ IN SELECT b FROM jsonb_array_elements(bindings)b WHERE b->'comparison_product_id'=reference->'product_id' LOOP
    relationship_key:=data.canonical_json(binding_->'relationship_ref');
    SELECT roles||COALESCE(jsonb_agg(bound_role),'[]') INTO roles FROM ops.dossier_comparison_roles(
     reference,report,binding_||jsonb_build_object('_require_focus',config->'_require_focus',
      '_applicability',CASE WHEN binding_ ? 'applicability_ref'
       THEN ops.resolve_retained_structural_report(binding_->'applicability_ref')->'report' END,
      '_conflict_passage',(SELECT p FROM jsonb_array_elements(inputs->'passages') p
       WHERE p->>'passage_id'=binding_->>'conflict_passage_id')),
     relationships->relationship_key,root_ref,root_)bound_role;
   END LOOP;
  ELSE RAISE EXCEPTION 'dossier predecessors require finite current semantic products' USING ERRCODE='23514';END IF;
  FOR role_ IN SELECT value FROM jsonb_array_elements(roles) LOOP
   span_:=role_->'span';SELECT value INTO STRICT p FROM jsonb_array_elements(inputs->'passages') WHERE value->>'passage_id'=span_->>'passage_id';
   key_:=encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(jsonb_build_object('product',reference->>'product_id','role',role_->>'role','citation',span_,'sense',sense_,'definition_interpretation',role_->'definition_interpretation','applicability_outcome',role_->'applicability_outcome','comparison_binding',role_->'comparison_binding'))),'UTF8')),'hex');
   IF seen ? key_ THEN CONTINUE;END IF;seen:=seen||jsonb_build_object(key_,true);assessment:=NULL;
   IF jsonb_array_length(retained->'public_assertions')>0 AND NOT (report->>'kind'='definition_components' AND role_->>'definition_interpretation'='unresolved') THEN
    expected_statement:=data.structural_public_statement(report,role_->>'component_id');
    SELECT a->>'assessment_id' INTO assessment FROM jsonb_array_elements(retained->'public_assertions')a WHERE a->'statement'=expected_statement AND nullif(a->>'assessment_id','') IS NOT NULL LIMIT 1;
   END IF;
   member_:=jsonb_strip_nulls(jsonb_build_object('member_id',key_,'passage_id',p->>'passage_id','citation',span_,'role',role_->>'role','sense',sense_,'scope',p->>'scope','effective_version',p->'effective_version','relation_product_id',reference->>'product_id','definition_interpretation',role_->'definition_interpretation','applicability_outcome',role_->'applicability_outcome','comparison_binding',role_->'comparison_binding','qualification',CASE WHEN assessment IS NULL OR role_ ? 'comparison_binding' THEN 'proposed' ELSE 'independently_supported' END,'assessment_id',CASE WHEN NOT role_ ? 'comparison_binding' THEN assessment END));
   members:=members||jsonb_build_array(member_);
   IF assessment IS NOT NULL AND (NOT role_ ? 'comparison_binding' OR role_->>'role' NOT IN ('relationship','conflict')) THEN
    facets:=facets||jsonb_build_array(jsonb_strip_nulls(jsonb_build_object('facet_id',key_||':'||(role_->>'role'),'kind',concat_ws(':',role_->>'role',role_->>'definition_interpretation',role_->>'applicability_outcome',span_->>'text'),'definition_interpretation',role_->'definition_interpretation','applicability_outcome',role_->'applicability_outcome','scope',p->>'scope','member_id',key_,'assessment_id',assessment,
     'assessment_scope',CASE WHEN role_ ? 'comparison_binding' THEN 'comparison_statement' END,
     'evidence',CASE WHEN role_ ? 'comparison_binding' THEN jsonb_build_array(p->>'passage_id',role_->'comparison_binding'->'opposite_citation'->>'passage_id') ELSE jsonb_build_array(p->>'passage_id') END)));
   END IF;
  END LOOP;
 END LOOP;
 IF (SELECT count(*)<>count(DISTINCT v->>'contribution_id') FROM jsonb_array_elements(COALESCE(config->'contribution_predecessors','[]'))v) THEN RAISE EXCEPTION 'duplicate dossier contribution predecessor' USING ERRCODE='23514';END IF;
 -- Aggregate full source membership once; never append to the growing dossier per row.
 SELECT members||COALESCE(jsonb_agg(m||jsonb_build_object('sense',sense_,'member_id',
  encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(jsonb_build_object(
   'contribution_ref',m->'contribution_ref','role',m->'role','citations',m->'contribution_citations','scope',m->'scope','sense',sense_,'semantic_dependency',m->'semantic_dependency'))),'UTF8')),'hex'))),'[]') INTO members
 FROM ops.dossier_contribution_members(inputs,COALESCE(config->'contribution_predecessors','[]'),root_) AS source_member(m);
 SELECT COALESCE(jsonb_agg(m ORDER BY source_passage.value->>'source_ref',(m->'citation'->>'start')::bigint,(m->'citation'->>'end')::bigint,m->>'member_id'),'[]') INTO members FROM jsonb_array_elements(members)m JOIN jsonb_array_elements(inputs->'passages')source_passage(value) ON source_passage.value->>'passage_id'=m->>'passage_id';
 SELECT COALESCE(jsonb_agg(f ORDER BY f->>'facet_id'),'[]') INTO facets FROM jsonb_array_elements(facets)f;
 SELECT COALESCE(jsonb_agg(m->'member_id' ORDER BY n),'[]'),count(*) INTO selected,mandatory FROM jsonb_array_elements(members) WITH ORDINALITY row_(m,n) WHERE m->>'role' IN ('exception','revision','conflict');
 WHILE jsonb_array_length(selected)<budget LOOP
  SELECT m,n INTO candidate FROM jsonb_array_elements(members) WITH ORDINALITY row_(m,n) WHERE NOT selected ? (m->>'member_id')
   ORDER BY CASE WHEN config->>'policy'='source-order-control-1' THEN 0 ELSE (SELECT count(DISTINCT (f->>'kind',f->>'scope')) FROM jsonb_array_elements(facets)f WHERE f->>'member_id'=m->>'member_id' AND NOT EXISTS(SELECT FROM jsonb_array_elements(facets)represented_ WHERE selected ? (represented_->>'member_id') AND represented_->>'kind'=f->>'kind' AND represented_->>'scope'=f->>'scope')) END DESC,n LIMIT 1;
  EXIT WHEN NOT FOUND;selected:=selected||jsonb_build_array(candidate.m->'member_id');
 END LOOP;
 SELECT COALESCE(jsonb_agg(m->'member_id' ORDER BY n),'[]') INTO omitted FROM jsonb_array_elements(members) WITH ORDINALITY row_(m,n) WHERE NOT selected ? (m->>'member_id');
 SELECT COALESCE(jsonb_agg(f->'facet_id' ORDER BY f->>'facet_id') FILTER(WHERE selected ? (f->>'member_id')),'[]'),COALESCE(jsonb_agg(f->'facet_id' ORDER BY f->>'facet_id') FILTER(WHERE NOT selected ? (f->>'member_id')),'[]') INTO represented,missing FROM jsonb_array_elements(facets)f;
 SELECT COALESCE(jsonb_agg(role ORDER BY n),'[]') INTO sections FROM jsonb_array_elements('["definition","terminology","usage","relationship","variant","exception","revision","conflict","unresolved_sense","open_question"]') WITH ORDINALITY r(role,n) WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(members)m WHERE m->'role'=role);
 membership_digest:=encode(sha256(convert_to(data.canonical_json(members),'UTF8')),'hex');facet_digest:=encode(sha256(convert_to(data.canonical_json(facets),'UTF8')),'hex');
 representation:=jsonb_build_object('policy',config->>'policy','member_budget',budget,'selected',selected,'omitted',omitted,'represented_facets',represented,'missing_facets',missing,'mandatory_overflow',mandatory>budget,'membership_digest',membership_digest,'facet_digest',facet_digest);
 RETURN jsonb_build_object('root_id',sense_,'root_component',root_ref,'members',members,'predecessors',COALESCE(config->'predecessors','[]'),'contribution_predecessors',COALESCE(config->'contribution_predecessors','[]'),'representatives',selected,'missing_sections',sections,'supported_facets',facets,'representation',representation,'membership_completeness','declared_selection')
  || CASE WHEN bindings='[]'::jsonb THEN '{}'::jsonb ELSE jsonb_build_object('comparison_selections',bindings) END;
END $$;
REVOKE ALL ON FUNCTION ops.structural_dossier(jsonb,jsonb) FROM PUBLIC;

-- Artifact source fields are projected from exact retained navigation annotations.
CREATE OR REPLACE FUNCTION ops.artifact_primary_sources(t ops.task,inputs jsonb,config jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_ jsonb; view_ kb.source_view; layers jsonb; result_ jsonb:='{}'; source_id text; passage jsonb;
BEGIN
 FOR source_ IN SELECT value FROM jsonb_array_elements(inputs->'sources') LOOP
  SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
  layers:=ops.primary_characterization_layers(t,view_,config);source_id:=encode(sha256(convert_to(data.canonical_json(source_),'UTF8')),'hex');
  IF EXISTS(SELECT FROM jsonb_array_elements(config->'work_bindings') b WHERE b->>'native_content_digest'=source_->>'native_content_digest') THEN
   FOR passage IN SELECT value FROM jsonb_array_elements(inputs->'passages') WHERE value->>'source_ref'=source_id LOOP
    IF NOT EXISTS(SELECT FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'coverage') c
     WHERE c->>'family'='construction.navigation' AND c->>'availability'='available' AND c->>'outcome' IN ('complete','empty')
      AND EXISTS(SELECT FROM jsonb_array_elements(c->'examined') s WHERE s->>'projection'=view_.projection_digest
       AND coalesce((s->>'start')::bigint,0)<=(passage->>'start')::bigint AND (s->>'end')::bigint>=(passage->>'end')::bigint)) THEN
     RAISE EXCEPTION 'artifact cohort requires primary navigation coverage of every selected passage' USING ERRCODE='23514'; END IF;
   END LOOP;
  END IF;
  result_:=result_||jsonb_build_object(source_id,layers);
 END LOOP;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.artifact_primary_sources(ops.task,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_primary_span(layers jsonb,ref jsonb,node jsonb,role_ text,view_ kb.source_view,field_start bigint)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE extents_ jsonb:=ops.primary_navigation_role_extents(layers,ref,node,role_,view_); lo bigint; hi bigint; text_ text;
BEGIN
 SELECT min((e->>'start')::bigint),max((e->>'end')::bigint),string_agg(e->>'text','' ORDER BY n) INTO lo,hi,text_ FROM jsonb_array_elements(extents_) WITH ORDINALITY x(e,n);
 IF lo<field_start OR hi-lo<>char_length(text_) THEN RAISE EXCEPTION 'artifact field is not one literal native-item interval' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('source_pointer',node->'navigation'->>'pointer','start',lo-field_start,'end',hi-field_start,'text',text_);
END $$;
REVOKE ALL ON FUNCTION ops.artifact_primary_span(jsonb,jsonb,jsonb,text,kb.source_view,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_primary_reference_source_value(ref jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('kind','object','fields',jsonb_build_array(
  jsonb_build_object('name','layer','position',0,'value',jsonb_build_object('kind','object','fields',jsonb_build_array(
   jsonb_build_object('name','task_id','position',0,'value',jsonb_build_object('kind','integer','integer',ref->'layer'->'task_id')),
   jsonb_build_object('name','product_key','position',1,'value',jsonb_build_object('kind','text','text',ref->'layer'->'product_key')),
   jsonb_build_object('name','content_digest','position',2,'value',jsonb_build_object('kind','text','text',ref->'layer'->'content_digest'))))),
  jsonb_build_object('name','local_id','position',1,'value',jsonb_build_object('kind','text','text',ref->'local_id'))))
$$;
REVOKE ALL ON FUNCTION ops.artifact_primary_reference_source_value(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_alias_fields(layers jsonb,ref jsonb,node jsonb,view_ kb.source_view,field_start bigint)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE alias_role jsonb; span_ jsonb; aliases jsonb:='[]'; spans jsonb:='[]'; result_ jsonb;
BEGIN
 FOR alias_role IN SELECT value FROM jsonb_array_elements(node->'navigation'->'roles') WHERE value->>'role' LIKE 'alias/%' LOOP
  span_:=ops.artifact_primary_span(layers,ref,node,alias_role->>'role',view_,field_start);aliases:=aliases||jsonb_build_array(span_->'text');spans:=spans||jsonb_build_array(span_);
 END LOOP;
 result_:=jsonb_build_object('aliases',aliases,'alias_state',coalesce(node->'navigation'->>'alias_state','unknown'),'alias_occurrences',spans);
 IF EXISTS(SELECT FROM jsonb_array_elements(node->'navigation'->'roles') r WHERE r->>'role'='alias_absence') THEN result_:=result_||jsonb_build_object('alias_absence',ops.artifact_primary_span(layers,ref,node,'alias_absence',view_,field_start)); END IF;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.artifact_alias_fields(jsonb,jsonb,jsonb,kb.source_view,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_source_labels(layers jsonb,ref jsonb,node jsonb,view_ kb.source_view,field_start bigint)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE kind_ text; label_ jsonb; span_ jsonb; evidence jsonb; count_ integer; value_ text; result_ jsonb:='{}'; temporary_ jsonb;
BEGIN
 FOREACH kind_ IN ARRAY ARRAY['numbering_namespace','revision'] LOOP
  evidence:='[]';
  FOR label_ IN SELECT value FROM jsonb_array_elements(coalesce(node->'navigation'->'source_labels','[]')) WHERE value->>'kind'=kind_ LOOP
   temporary_:=jsonb_build_object('navigation',jsonb_build_object('pointer',node->'navigation'->>'pointer','roles',jsonb_build_array(jsonb_build_object('role','label','occurrences',label_->'occurrences'))));
   span_:=ops.artifact_primary_span(layers,ref,temporary_,'label',view_,field_start);
   IF span_->>'text' IS DISTINCT FROM label_->>'value' THEN RAISE EXCEPTION 'artifact source label differs from exact retained source span' USING ERRCODE='23514'; END IF;
   evidence:=evidence||jsonb_build_array(span_);
  END LOOP;
  SELECT count(DISTINCT e->>'text'),min(e->>'text') INTO count_,value_ FROM jsonb_array_elements(evidence) e;
  result_:=result_||jsonb_build_object(CASE kind_ WHEN 'numbering_namespace' THEN 'numbering' ELSE 'revision' END,
   jsonb_strip_nulls(jsonb_build_object('state',CASE count_ WHEN 0 THEN 'unknown' WHEN 1 THEN 'observed' ELSE 'unresolved' END,'value',CASE WHEN count_=1 THEN value_ END,'evidence',evidence)));
 END LOOP;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.artifact_source_labels(jsonb,jsonb,jsonb,kb.source_view,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_explicit_reference(layers jsonb,ref jsonb,node jsonb,view_ kb.source_view,field_start bigint)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF node->'navigation'->>'kind' IS DISTINCT FROM 'artifact_explicit_reference' OR node->'navigation'->>'designator' IS DISTINCT FROM ops.primary_navigation_role_text(layers,ref,node,'target_designator',view_)
  OR node->'navigation'->>'numbering_namespace' IS DISTINCT FROM ops.primary_navigation_role_text(layers,ref,node,'target_numbering',view_) THEN
  RAISE EXCEPTION 'artifact explicit reference changes retained target fields' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('target_code',node->'navigation'->>'designator','target_numbering',node->'navigation'->>'numbering_namespace','cue',ops.artifact_primary_span(layers,ref,node,'cue',view_,field_start),'primary_node',ref);
END $$;
REVOKE ALL ON FUNCTION ops.artifact_explicit_reference(jsonb,jsonb,jsonb,kb.source_view,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_alias_span_source_value(span jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('kind','object','fields',jsonb_build_array(
  jsonb_build_object('name','source_pointer','position',0,'value',jsonb_build_object('kind','text','text',span->'source_pointer')),
  jsonb_build_object('name','start','position',1,'value',jsonb_build_object('kind','integer','integer',span->'start')),
  jsonb_build_object('name','end','position',2,'value',jsonb_build_object('kind','integer','integer',span->'end')),
  jsonb_build_object('name','text','position',3,'value',jsonb_build_object('kind','text','text',span->'text'))))
$$;
REVOKE ALL ON FUNCTION ops.artifact_alias_span_source_value(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_label_relation(a jsonb,b jsonb)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT CASE WHEN 'unresolved' IN (a->>'state',b->>'state') THEN 'unresolved'
 WHEN a->>'value' IS NULL OR b->>'value' IS NULL THEN 'unknown'
 WHEN a->>'value'=b->>'value' THEN 'same_observed' ELSE 'different_observed' END
$$;
REVOKE ALL ON FUNCTION ops.artifact_label_relation(jsonb,jsonb) FROM PUBLIC;

-- Reconstruct the source cohort rather than trusting duplicated fields or caller IDs.
-- A named source container and exact current projection remain the source authority.
CREATE OR REPLACE FUNCTION ops.artifact_source_records(inputs jsonb,config jsonb,primary_sources jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_ jsonb; binding jsonb; view_ kb.source_view; piece jsonb; node jsonb; pin jsonb; anchor_ jsonb; artifact jsonb; value_ jsonb; contribution jsonb; citations jsonb;
 candidates jsonb:='[]'; raw text; quote_ text; pointer_ text; source_ref text; local_start integer;local_end integer;global_start integer;global_end integer;caption boolean;explicit_ jsonb;
 layers jsonb;l record; annotation_ jsonb; primary_ jsonb;ref_ jsonb;subject_ jsonb; explicit_ref jsonb;explicit_node jsonb; explicit_span jsonb;explicit_candidates jsonb;title_ text;
BEGIN
 IF (SELECT count(*)<>count(DISTINCT wb->>'native_content_digest') FROM jsonb_array_elements(config->'work_bindings') wb) THEN RAISE EXCEPTION 'artifact source-work bindings repeat' USING ERRCODE='23514'; END IF;
 FOR source_ IN SELECT value FROM jsonb_array_elements(inputs->'sources') LOOP
  SELECT wb INTO binding FROM jsonb_array_elements(config->'work_bindings') wb WHERE wb->>'native_content_digest'=source_->>'native_content_digest';
  IF binding IS NULL THEN CONTINUE; END IF;
  SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
  source_ref:=encode(sha256(convert_to(data.canonical_json(source_),'UTF8')),'hex');layers:=primary_sources->source_ref;
  pin:=jsonb_build_object('source',view_.key,'native_product_task_id',view_.native_task_id,'product_key',view_.native_product_key,'product_digest',view_.native_content_digest,'projection_digest',view_.projection_digest,'recipe_digest',view_.recipe_digest,'source_view_id',view_.id);
  FOR l IN SELECT * FROM jsonb_each(layers) LOOP
   FOR annotation_ IN SELECT value FROM jsonb_array_elements(l.value->'annotations') WHERE value->'navigation'->>'kind' IN ('artifact_mention','artifact_reference')
    AND ops.primary_characterization_in_view(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',value->>'local_id'),value,view_.id) LOOP
    ref_:=jsonb_build_object('layer',l.key::jsonb,'local_id',annotation_->>'local_id');primary_:=ops.primary_navigation_node(layers,ref_,'[]',view_);pointer_:=primary_->'navigation'->>'pointer';
    SELECT p INTO STRICT piece FROM jsonb_array_elements(view_.projection->'pieces') p WHERE p->>'kind'='native_text' AND p->>'cell_index' IS NULL AND p->>'item_ref'=pointer_;
    raw:=substring(view_.projection->>'text' FROM (piece->>'start')::integer+1 FOR (piece->>'end')::integer-(piece->>'start')::integer);
    SELECT native_json INTO STRICT node FROM ops.read_pdf_published_items(view_.native_task_id,view_.native_product_key,view_.native_content_digest,ARRAY[pointer_]);
    IF node->>'text' IS DISTINCT FROM raw THEN RAISE EXCEPTION 'artifact native field bridge differs from selected source' USING ERRCODE='23514'; END IF;
    caption:=node->>'label'='caption';subject_:=ops.artifact_primary_span(layers,ref_,primary_,'subject',view_,(piece->>'start')::bigint);
    local_start:=(subject_->>'start')::integer;local_end:=(subject_->>'end')::integer;quote_:=subject_->>'text';global_start:=(piece->>'start')::integer+local_start;global_end:=(piece->>'start')::integer+local_end;
    IF local_end>(piece->>'end')::integer-(piece->>'start')::integer OR primary_->'navigation'->>'designator' IS DISTINCT FROM ops.primary_navigation_role_text(layers,ref_,primary_,'designator',view_) THEN RAISE EXCEPTION 'artifact subject/designator differs from exact primary literal fields' USING ERRCODE='23514'; END IF;
    IF (SELECT count(*) FROM jsonb_each(layers) ll CROSS JOIN LATERAL jsonb_array_elements(ll.value->'annotations') aa WHERE aa->'navigation'->>'kind' IN ('artifact_mention','artifact_reference')
     AND CASE WHEN ops.primary_characterization_in_view(layers,jsonb_build_object('layer',ll.key::jsonb,'local_id',aa->>'local_id'),aa,view_.id) THEN
      ops.primary_navigation_role_extents(layers,jsonb_build_object('layer',ll.key::jsonb,'local_id',aa->>'local_id'),aa,'subject',view_)=ops.primary_navigation_role_extents(layers,ref_,primary_,'subject',view_) ELSE false END)<>1 THEN RAISE EXCEPTION 'artifact subject has competing primary navigation fields' USING ERRCODE='23514'; END IF;
    SELECT coalesce(jsonb_agg(jsonb_build_object('source_ref',source_ref,'passage_id',p->>'passage_id','source_pointer',pointer_,'start',global_start,'end',global_end,'text',quote_) ORDER BY ordinal),'[]') INTO citations
     FROM jsonb_array_elements(inputs->'passages') WITH ORDINALITY selected(p,ordinal) WHERE p->>'source_ref'=source_ref AND (p->>'start')::integer<=global_start AND (p->>'end')::integer>=global_end;
    IF jsonb_array_length(citations)=0 THEN CONTINUE; END IF;
    explicit_:=NULL;
    IF NOT caption THEN
     SELECT coalesce(jsonb_agg(jsonb_build_object('reference',jsonb_build_object('layer',ll.key::jsonb,'local_id',aa->>'local_id'),'node',aa)),'[]') INTO explicit_candidates
     FROM jsonb_each(layers) ll CROSS JOIN LATERAL jsonb_array_elements(ll.value->'annotations') aa
     WHERE aa->'navigation'->>'kind'='artifact_explicit_reference' AND aa->'navigation'->>'pointer'=pointer_ AND aa->'navigation'->>'artifact_kind'=primary_->'navigation'->>'artifact_kind'
      AND CASE WHEN ops.primary_characterization_in_view(layers,jsonb_build_object('layer',ll.key::jsonb,'local_id',aa->>'local_id'),aa,view_.id) THEN
       ops.primary_navigation_role_extents(layers,jsonb_build_object('layer',ll.key::jsonb,'local_id',aa->>'local_id'),aa,'subject',view_)=ops.primary_navigation_role_extents(layers,ref_,primary_,'subject',view_) ELSE false END;
     IF jsonb_array_length(explicit_candidates)>1 THEN RAISE EXCEPTION 'artifact explicit target has competing retained primary declarations' USING ERRCODE='23514'; END IF;
     IF jsonb_array_length(explicit_candidates)=1 THEN
      explicit_ref:=explicit_candidates->0->'reference';explicit_node:=explicit_candidates->0->'node';
      explicit_node:=ops.primary_navigation_node(layers,explicit_ref,'[]',view_);explicit_span:=ops.artifact_primary_span(layers,explicit_ref,explicit_node,'cue',view_,0);
      IF EXISTS(SELECT FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'source_ref'=source_ref AND (p->>'start')::integer<=(explicit_span->>'start')::integer AND (p->>'end')::integer>=(explicit_span->>'end')::integer) THEN explicit_:=ops.artifact_explicit_reference(layers,explicit_ref,explicit_node,view_,(piece->>'start')::bigint); END IF;
     END IF;
    END IF;
    title_:=NULL;
    IF caption AND EXISTS(SELECT FROM jsonb_array_elements(primary_->'navigation'->'roles') r WHERE r->>'role'='caption_title') THEN title_:=nullif(ops.primary_navigation_role_text(layers,ref_,primary_,'caption_title',view_),''); END IF;
    artifact:=jsonb_strip_nulls(jsonb_build_object('protocol','source-artifact-occurrence-2','artifact_kind',primary_->'navigation'->>'artifact_kind','source_work',binding->>'source_work','controlled_code',primary_->'navigation'->>'designator','title',title_,'revision_state','unknown','occurrence_role',CASE WHEN caption THEN 'caption' ELSE 'reference' END,'scope',pointer_,'source_pointer',pointer_,'dependencies',jsonb_build_array('native:'||view_.native_task_id::text),'primary_node',ref_))||ops.artifact_alias_fields(layers,ref_,primary_,view_,(piece->>'start')::bigint);
    -- SourceValue retains the producer's declared field ordering, independently of JSONB order.
    SELECT jsonb_build_object('kind','object','fields',jsonb_agg(jsonb_build_object(
     'name',key,'position',position,'value',CASE
      WHEN key='primary_node' THEN ops.artifact_primary_reference_source_value(artifact->key)
      WHEN key='alias_absence' THEN ops.artifact_alias_span_source_value(artifact->key)
      WHEN jsonb_typeof(artifact->key)='array' THEN jsonb_build_object('kind','array','items',COALESCE((SELECT jsonb_agg(
       CASE WHEN key='alias_occurrences' THEN ops.artifact_alias_span_source_value(x)
        ELSE jsonb_build_object('kind','text','text',x) END ORDER BY n)
       FROM jsonb_array_elements(artifact->key) WITH ORDINALITY a(x,n)),'[]'))
      ELSE jsonb_build_object('kind','text','text',artifact->key) END) ORDER BY position)) INTO value_
    FROM (SELECT key,(row_number() OVER(ORDER BY n)-1)::integer position FROM unnest(ARRAY[
     'protocol','artifact_kind','source_work','controlled_code','title','aliases','alias_state','alias_occurrences','alias_absence','revision',
     'revision_state','occurrence_role','scope','source_pointer','dependencies','primary_node']) WITH ORDINALITY f(key,n)
     WHERE artifact ? key) fields;
    anchor_:=jsonb_build_object('pin',pin,'space','native','pointer',pointer_,
     'precision','exact','start',local_start,'end',local_end,'source_piece',quote_);
    anchor_:=anchor_||jsonb_build_object('anchor_id','record-anchor:'||encode(sha256(convert_to(
     data.canonical_json(anchor_||jsonb_build_object('pin',pin-'source_view_id')),'UTF8')),'hex'));
    contribution:=jsonb_build_object('contract','RetainedContributionSemantics','kind','occurrence',
     'semantic_type','structural.artifact','operation_key','contribution-operation:'||encode(sha256(convert_to(
      data.canonical_json(jsonb_build_array(jsonb_build_array('structure.scoped_relations','3',pin),'{}'::jsonb)),'UTF8')),'hex'),
     'item_key',pointer_||':artifact_reference:'||global_start::text||':'||global_end::text,
     'pin',pin,'anchors',jsonb_build_array(anchor_),
     'occurrence_id',ops.source_contribution_occurrence(jsonb_build_array(anchor_)),
     'standing','retained_private','score_state','missing','disposition','located_proposal',
     'computation_dependencies',jsonb_build_array('native:'||view_.native_task_id::text),'value',value_);
    contribution:=contribution||jsonb_build_object('contribution_id','source-contribution:'||encode(sha256(
     convert_to(data.canonical_json(contribution),'UTF8')),'hex'));
    candidates:=candidates||jsonb_build_array(jsonb_build_object(
     'contribution_id',contribution->>'contribution_id','occurrence_id',contribution->>'occurrence_id',
     'artifact',artifact,'source_contribution',contribution,'citations',citations,'primary_node',ref_)
     ||ops.artifact_source_labels(layers,ref_,primary_,view_,(piece->>'start')::bigint)
     ||jsonb_strip_nulls(jsonb_build_object('explicit_reference',explicit_)));
   END LOOP;
  END LOOP;
 END LOOP;
 RETURN (WITH cohort AS (
  SELECT r,n,r->>'occurrence_id' occurrence_id,r->'artifact'->>'source_work' work_,
   r->'artifact'->>'artifact_kind' kind_ FROM jsonb_array_elements(candidates) WITH ORDINALITY c(r,n)
 ), selected AS (
  SELECT DISTINCT ON (occurrence_id,work_,kind_) * FROM cohort
  ORDER BY occurrence_id,work_,kind_,r->>'contribution_id',n
 ), selected_references AS (
  SELECT DISTINCT ON (occurrence_id,work_,kind_) occurrence_id,work_,kind_,
   r->'explicit_reference' explicit_reference FROM cohort WHERE r ? 'explicit_reference'
  ORDER BY occurrence_id,work_,kind_,r->>'contribution_id',n
 ), citations AS (
  SELECT occurrence_id,work_,kind_,jsonb_agg(c ORDER BY id,n,ordinal) citations
  FROM (SELECT DISTINCT ON (occurrence_id,work_,kind_,c) occurrence_id,work_,kind_,c,
    r->>'contribution_id' id,n,ordinal FROM cohort
   CROSS JOIN LATERAL jsonb_array_elements(r->'citations') WITH ORDINALITY cite(c,ordinal)
   ORDER BY occurrence_id,work_,kind_,c,r->>'contribution_id',n,ordinal) unique_citations
  GROUP BY occurrence_id,work_,kind_
 )
 SELECT COALESCE(jsonb_agg(jsonb_set(selected.r,'{citations}',citations.citations)
  ||jsonb_strip_nulls(jsonb_build_object('explicit_reference',selected_references.explicit_reference))
  ORDER BY selected.r->>'contribution_id'),'[]')
 FROM selected JOIN citations USING (occurrence_id,work_,kind_)
 LEFT JOIN selected_references USING (occurrence_id,work_,kind_));
END $$;
REVOKE ALL ON FUNCTION ops.artifact_source_records(jsonb,jsonb,jsonb) FROM PUBLIC;

-- RapidFuzz's normalized Indel similarity is twice the longest common subsequence
-- divided by the two codepoint lengths. This independent admission replay does not
-- replace the production RapidFuzz candidate generator.
CREATE OR REPLACE FUNCTION ops.artifact_lexical_score(a text,b text)
RETURNS double precision LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE previous integer[]; current_ integer[]; i integer; j integer; n integer; m integer;
BEGIN
 IF a IS NULL OR b IS NULL OR a='' OR b='' THEN RETURN 0; END IF;
 n:=char_length(a);m:=char_length(b);previous:=array_fill(0,ARRAY[m+1],ARRAY[0]);
 FOR i IN 1..n LOOP
  current_:=array_fill(0,ARRAY[m+1],ARRAY[0]);
  FOR j IN 1..m LOOP
   current_[j]:=CASE WHEN substring(a FROM i FOR 1)=substring(b FROM j FOR 1)
    THEN previous[j-1]+1 ELSE greatest(previous[j],current_[j-1]) END;
  END LOOP;
  previous:=current_;
 END LOOP;
 -- Match the library arithmetic as well as the mathematical ratio at exact thresholds.
 RETURN ((1.0-(n+m-2*previous[m])::double precision/(n+m)::double precision)*100.0)/100.0;
END $$;
REVOKE ALL ON FUNCTION ops.artifact_lexical_score(text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_external_nominations(t ops.task,inputs jsonb,config jsonb,records jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE held record; relation_ jsonb; endpoint jsonb; endpoint_row jsonb; src jsonb; pin_ jsonb;
 expected_role text; ids text[]; output jsonb:='[]'; directed jsonb; anchor_ jsonb; piece_ jsonb;
 occurrence_ jsonb; cue_ jsonb; primary_ref jsonb; primary_ jsonb; layers jsonb; view_ kb.source_view; literal_row jsonb;
BEGIN
 IF (SELECT count(*)<>count(DISTINCT r->>'contribution_id')
     FROM jsonb_array_elements(config->'external_nomination_refs') r) THEN
  RAISE EXCEPTION 'artifact external nomination references repeat' USING ERRCODE='23514';END IF;
 FOR held IN SELECT * FROM ops.resolve_retained_source_contributions(config->'external_nomination_refs')
  ORDER BY reference->>'contribution_id' LOOP
  IF NOT (inputs->'dependencies') ? (held.reference->>'contribution_id') THEN
   RAISE EXCEPTION 'artifact external nomination outside declared dependencies' USING ERRCODE='23514';END IF;
  SELECT r INTO STRICT relation_ FROM jsonb_array_elements(held.contributions) r
   WHERE r->>'contribution_id'=held.reference->>'contribution_id'
    AND r->>'semantic_type'='structural.scoped_attachment'
    AND data.record_source_json(r->'value')->>'relation'='artifact_reference_target';
  IF jsonb_array_length(relation_->'endpoints')<>2 OR
    NOT EXISTS(SELECT FROM jsonb_array_elements(relation_->'endpoints') e WHERE e->>'role'='attachment') OR
    NOT EXISTS(SELECT FROM jsonb_array_elements(relation_->'endpoints') e WHERE e->>'role'='target') THEN
   RAISE EXCEPTION 'artifact external nomination requires reference and caption endpoints' USING ERRCODE='23514';END IF;
  ids:='{}';directed:='[]';
  FOR endpoint IN SELECT e FROM jsonb_array_elements(relation_->'endpoints') e ORDER BY e->>'role' LOOP
   SELECT r INTO STRICT endpoint_row FROM jsonb_array_elements(held.contributions) r
    WHERE r->>'contribution_id'=endpoint->>'contribution_id'
     AND (r->>'semantic_type'='structural.artifact' OR
      (r->>'semantic_type'='structural.located_participant' AND data.record_source_json(r->'value')->>'role'='artifact_reference'));
   pin_:=endpoint_row->'pin';
   SELECT s INTO STRICT src FROM jsonb_array_elements(held.sources) s WHERE s->'pin'=pin_;
   anchor_:=endpoint_row->'anchors'->0;
   IF jsonb_array_length(endpoint_row->'anchors') IS DISTINCT FROM 1
    OR anchor_->'pin' IS DISTINCT FROM pin_ OR anchor_->>'space' IS DISTINCT FROM 'native'
    OR anchor_->>'precision' IS DISTINCT FROM 'exact'
    OR ops.source_contribution_occurrence(endpoint_row->'anchors') IS DISTINCT FROM endpoint_row->>'occurrence_id' THEN
    RAISE EXCEPTION 'artifact nomination endpoint lacks its exact origin source pin' USING ERRCODE='23514';END IF;
   SELECT p INTO STRICT piece_ FROM jsonb_array_elements(src->'projection'->'pieces') p
    WHERE p->>'kind'='native_text' AND p->>'item_ref'=anchor_->>'pointer'
     AND p->>'cell_index' IS NULL AND (anchor_->>'start')::integer>=0
     AND (anchor_->>'start')::integer<(anchor_->>'end')::integer
     AND (anchor_->>'end')::integer<=(p->>'end')::integer-(p->>'start')::integer
     AND substring(src->'projection'->>'text'
      FROM (p->>'start')::integer+(anchor_->>'start')::integer+1
      FOR (anchor_->>'end')::integer-(anchor_->>'start')::integer)=anchor_->>'source_piece';
   expected_role:=CASE endpoint->>'role' WHEN 'attachment' THEN 'reference' ELSE 'caption' END;
   SELECT r INTO STRICT occurrence_ FROM jsonb_array_elements(records) r
    WHERE r->>'occurrence_id'=endpoint_row->>'occurrence_id'
     AND r->'artifact'->>'occurrence_role'=expected_role;
   IF expected_role='reference' THEN
    SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(pin_->>'source_view_id')::bigint;
    layers:=ops.primary_characterization_layers(t,view_,config);primary_ref:=relation_->'component'->'primary_node';
    primary_:=ops.primary_navigation_node(layers,primary_ref,'[]',view_);
    literal_row:=endpoint_row;
    IF endpoint_row->>'semantic_type'='structural.artifact' THEN
     literal_row:=endpoint_row||jsonb_build_object('value',jsonb_build_object('kind','object','fields',jsonb_build_array(
      jsonb_build_object('name','text','position',0,'value',jsonb_build_object('kind','text','text',anchor_->'source_piece')),
      jsonb_build_object('name','source_pointer','position',1,'value',jsonb_build_object('kind','text','text',anchor_->'pointer')))));
    END IF;
    IF primary_->'navigation'->>'kind' IS DISTINCT FROM 'artifact_reference'
     OR NOT ops.primary_navigation_role_matches(layers,primary_ref,primary_,'subject',view_,literal_row) THEN
     RAISE EXCEPTION 'artifact nomination changes exact retained reference/cue source' USING ERRCODE='23514'; END IF;
    cue_:=ops.artifact_primary_span(layers,primary_ref,primary_,'cue',view_,(piece_->>'start')::bigint);
   END IF;
   ids:=array_append(ids,occurrence_->>'contribution_id');
   directed:=directed||jsonb_build_array(jsonb_build_object('role',endpoint->>'role',
    'record_id',occurrence_->>'contribution_id','contribution_id',endpoint_row->>'contribution_id',
    'origin_source_view_id',pin_->'source_view_id','origin_anchor_id',anchor_->>'anchor_id'));
  END LOOP;
  IF ids[1]=ids[2] THEN
   RAISE EXCEPTION 'artifact nomination requires distinct physical endpoints' USING ERRCODE='23514';END IF;
  output:=output||jsonb_build_array(jsonb_build_object('left',least(ids[1],ids[2]),
   'right',greatest(ids[1],ids[2]),'kind','artifact_reference_target','relationship',held.reference,
   'endpoints',directed,'origin_cue',cue_,'primary_node',primary_ref));
 END LOOP;
 RETURN output;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'artifact external nomination cannot resolve exact cohort endpoints' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.artifact_external_nominations(ops.task,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_declared_relationships(inputs jsonb,records jsonb,primary_sources jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE record_ jsonb;citation jsonb;view_ kb.source_view;passage jsonb;src jsonb;layers jsonb;l record;a jsonb;ref_ jsonb;node jsonb;nav jsonb;subject_ jsonb;cue_ jsonb;
 row_ jsonb;record_id text;work_ text;kind_ text;relation_ text;field_ text;role_ text;
 declarations jsonb:='[]';work_cues jsonb:='{}';targets jsonb;output jsonb:='[]';
BEGIN
 FOR record_ IN SELECT value FROM jsonb_array_elements(records) LOOP
  record_id:=record_->>'contribution_id';work_:=record_->'artifact'->>'source_work';kind_:=record_->'artifact'->>'artifact_kind';
  FOR citation IN SELECT value FROM jsonb_array_elements(record_->'citations') LOOP
   SELECT s INTO STRICT src FROM jsonb_array_elements(inputs->'sources') s WHERE encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')=citation->>'source_ref';
   SELECT p INTO STRICT passage FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'passage_id'=citation->>'passage_id' AND p->>'source_ref'=citation->>'source_ref';
   SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(src->>'source_view_id')::bigint;layers:=primary_sources->(citation->>'source_ref');
   FOR l IN SELECT * FROM jsonb_each(layers) LOOP
    FOR a IN SELECT value FROM jsonb_array_elements(l.value->'annotations') WHERE value->'navigation'->>'kind' IN ('artifact_work','artifact_relation') AND value->'navigation'->>'pointer'=citation->>'source_pointer'
     AND ops.primary_characterization_in_view(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',value->>'local_id'),value,view_.id) LOOP
     ref_:=jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id');node:=ops.primary_navigation_node(layers,ref_,'[]',view_);nav:=node->'navigation';
     subject_:=ops.artifact_primary_span(layers,ref_,node,'subject',view_,0);
     IF subject_->'start' IS DISTINCT FROM citation->'start' OR subject_->'end' IS DISTINCT FROM citation->'end' THEN CONTINUE; END IF;
     cue_:=ops.artifact_primary_span(layers,ref_,node,'cue',view_,0);
     IF (cue_->>'start')::bigint<(passage->>'start')::bigint OR (cue_->>'end')::bigint>(passage->>'end')::bigint THEN CONTINUE; END IF;
     cue_:=citation||cue_;
     IF nav->>'kind'='artifact_work' THEN
      IF nav->>'work' IS DISTINCT FROM ops.primary_navigation_role_text(layers,ref_,node,'work',view_) THEN RAISE EXCEPTION 'artifact work metadata changes exact retained work role' USING ERRCODE='23514'; END IF;
      IF nav->>'work'=work_ AND NOT work_cues ? record_id THEN work_cues:=work_cues||jsonb_build_object(record_id,jsonb_build_object('citation',citation,'cue',cue_,'primary',ref_)); END IF;
      CONTINUE;
     END IF;
     relation_:=nav->>'relation_kind';
     IF nav->>'artifact_kind' IS DISTINCT FROM kind_ OR (relation_='reference') IS DISTINCT FROM (record_->'artifact'->>'occurrence_role'='reference') THEN CONTINUE; END IF;
     FOR field_,role_ IN SELECT * FROM (VALUES('designator','target_designator'),('numbering_namespace','target_numbering'),('work','target_work'),('revision','target_revision')) names(field_,role_) LOOP
      IF nav ? field_ AND nav->>field_ IS DISTINCT FROM ops.primary_navigation_role_text(layers,ref_,node,role_,view_) THEN RAISE EXCEPTION 'artifact relationship metadata changes exact retained target field' USING ERRCODE='23514'; END IF;
     END LOOP;
     row_:=jsonb_build_object('kind',relation_,'source_id',record_id,'origin',cue_,'primary_node',ref_,
      'source_work',work_,'source_occurrence',record_->>'occurrence_id','source_revision',record_->'revision'->>'value',
      'target_work',coalesce(nav->>'work',work_),'target_kind',kind_,'target_namespace',nav->>'numbering_namespace','target_code',lower(nav->>'designator'),'target_revision',nav->>'revision');
     declarations:=declarations||jsonb_build_array(row_);
    END LOOP;
   END LOOP;
  END LOOP;
 END LOOP;
 FOR row_ IN SELECT value FROM jsonb_array_elements(declarations) LOOP
  SELECT coalesce(jsonb_agg(jsonb_strip_nulls(jsonb_build_object('record_id',r->>'contribution_id',
   'citation',CASE WHEN cross_work THEN work_cues->(r->>'contribution_id')->'citation' ELSE r->'citations'->0 END,
   'work_cue',CASE WHEN cross_work THEN work_cues->(r->>'contribution_id')->'cue' END,
   'work_primary_node',CASE WHEN cross_work THEN work_cues->(r->>'contribution_id')->'primary' END)) ORDER BY n),'[]') INTO targets
  FROM jsonb_array_elements(records) WITH ORDINALITY r(r,n),LATERAL (SELECT row_->>'source_work'<>row_->>'target_work' cross_work) c
  WHERE r->'artifact'->>'occurrence_role'='caption' AND r->'artifact'->>'source_work'=row_->>'target_work' AND r->'artifact'->>'artifact_kind'=row_->>'target_kind'
   AND r->'numbering'->>'value'=row_->>'target_namespace' AND lower(btrim(r->'artifact'->>'controlled_code'))=row_->>'target_code'
   AND r->>'occurrence_id'<>row_->>'source_occurrence' AND (NOT cross_work OR work_cues ? (r->>'contribution_id'))
   AND (row_->>'target_revision' IS NULL OR r->'revision'->>'value'=row_->>'target_revision')
   AND (row_->>'kind'<>'supersedes' OR (row_->>'source_revision' IS NOT NULL AND row_->>'target_revision' IS NOT NULL AND row_->>'source_revision'<>row_->>'target_revision'));
  row_:=jsonb_build_object('kind',row_->>'kind','source_id',row_->>'source_id','origin',row_->'origin','primary_node',row_->'primary_node','targets',targets,
   'outcome',CASE jsonb_array_length(targets) WHEN 0 THEN 'no_compatible_candidate' WHEN 1 THEN 'witnessed_candidate' ELSE 'ambiguous' END);
  IF NOT output @> jsonb_build_array(row_) THEN output:=output||jsonb_build_array(row_); END IF;
 END LOOP;
 RETURN output;
END $$;
REVOKE ALL ON FUNCTION ops.artifact_declared_relationships(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_artifact_identity(t ops.task,inputs jsonb,config jsonb,product jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE primary_sources jsonb:=ops.artifact_primary_sources(t,inputs,config);expected_records jsonb; pair_ jsonb; a jsonb; b jsonb; routes jsonb; expected_pairs jsonb:='[]';
 code_a text; code_b text; title_a text; title_b text; compatible boolean; excluded boolean;
 lexical double precision; log_odds double precision; probability double precision; external_ boolean; policy jsonb;
 code_gamma integer; title_gamma integer; code_mw double precision; title_mw double precision;
 field_ jsonb; expected_value double precision; model_id text; expected_provenance jsonb; unbound jsonb; anchors jsonb;
 parameter_name text; parameter_value jsonb; parameter_text text; decoded_value double precision;
 alias_ boolean; expected_alias_pairs jsonb:='[]'; nominations jsonb; pair_nomination_ids jsonb;
 title_threshold double precision; config_policy jsonb:='{}'; numbering_ text; revision_ text;
 score_status text; expected_counts jsonb; explicit_references jsonb; explicit_ boolean; declarations jsonb:='[]';
 python_space text:=chr(9)||chr(10)||chr(11)||chr(12)||chr(13)||chr(28)||chr(29)||chr(30)||chr(31)||chr(32)||chr(133)||chr(160)||chr(5760)||chr(8192)||chr(8193)||chr(8194)||chr(8195)||chr(8196)||chr(8197)||chr(8198)||chr(8199)||chr(8200)||chr(8201)||chr(8202)||chr(8232)||chr(8233)||chr(8239)||chr(8287)||chr(12288);
BEGIN
 policy:=product->'policy';
 -- MethodRegistry stores floats as canonical decimal strings; products keep typed numbers.
 -- Decode only these declared numeric configuration fields, without rewriting custody bytes.
 IF jsonb_typeof(config->'policy') IS DISTINCT FROM 'object'
  OR jsonb_typeof(policy) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 IF NOT ((config->'policy') ?& ARRAY['prior','code_m','code_u','title_m','title_u'])
  OR (SELECT count(*) FROM jsonb_each(config->'policy'))<>5 THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 FOR parameter_name,parameter_value IN
  SELECT key,value FROM jsonb_each(config->'policy')
  UNION ALL SELECT 'title_threshold',config->'title_threshold' LOOP
  IF COALESCE(jsonb_typeof(parameter_value),'null') NOT IN ('number','string') THEN
   RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514'; END IF;
  parameter_text:=parameter_value#>>'{}';
  IF jsonb_typeof(parameter_value)='string' THEN
   -- Canonical floats have no exponent; reject it before the decimal normalizer expands it.
   IF parameter_text ~ '[eE]' THEN
    RAISE EXCEPTION 'artifact numeric config requires canonical decimal strings' USING ERRCODE='23514'; END IF;
   IF parameter_text IS DISTINCT FROM data.decimal_canonical(parameter_text) THEN
    RAISE EXCEPTION 'artifact numeric config requires canonical decimal strings' USING ERRCODE='23514'; END IF;
  END IF;
  decoded_value:=parameter_text::double precision;
  IF NOT (decoded_value>'-Infinity'::double precision AND decoded_value<'Infinity'::double precision) THEN
   RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514'; END IF;
  IF parameter_name='title_threshold' THEN
   IF decoded_value<0 OR decoded_value>100 THEN
    RAISE EXCEPTION 'artifact title threshold must be between zero and one hundred' USING ERRCODE='23514'; END IF;
   title_threshold:=decoded_value;
  ELSE
   IF decoded_value<=0 OR decoded_value>=1 THEN
    RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
   config_policy:=config_policy||jsonb_build_object(parameter_name,decoded_value);
  END IF;
 END LOOP;
 IF product->>'identity_grain' IS DISTINCT FROM 'source_work_artifact_lineage'
  OR jsonb_typeof(config->'work_bindings') IS DISTINCT FROM 'array'
  OR jsonb_typeof(config->'external_nomination_refs') IS DISTINCT FROM 'array'
  OR jsonb_typeof(config->'exclusions') IS DISTINCT FROM 'array'
  OR NOT policy ?& ARRAY['prior','code_m','code_u','title_m','title_u']
  OR config->>'_operation_version' IS DISTINCT FROM '5' OR product->>'protocol' IS DISTINCT FROM 'artifact-identity-5'
  OR product->>'standing'<>'candidate_relative_private'
  OR policy IS DISTINCT FROM config_policy OR EXISTS(SELECT FROM jsonb_each(policy) p
   WHERE (p.value#>>'{}')::double precision<=0 OR (p.value#>>'{}')::double precision>=1)
  OR (SELECT count(*) FROM jsonb_each(policy))<>5 THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 expected_records:=ops.artifact_source_records(inputs,config,primary_sources);
 IF jsonb_strip_nulls(product->'records') IS DISTINCT FROM expected_records THEN
  RAISE EXCEPTION 'artifact cohort/fields/content identities differ from exact source replay' USING ERRCODE='23514'; END IF;
 declarations:=ops.artifact_declared_relationships(inputs,expected_records,primary_sources);
 IF product->'declared_relationships' IS DISTINCT FROM declarations THEN RAISE EXCEPTION 'artifact typed relationships differ from retained primary declarations' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(DISTINCT wb->>'provenance' ORDER BY wb->>'provenance'),'[]') INTO expected_provenance
 FROM jsonb_array_elements(inputs->'sources') src JOIN LATERAL jsonb_array_elements(config->'work_bindings') wb
  ON wb->>'native_content_digest'=src->>'native_content_digest';
 SELECT COALESCE(jsonb_agg(src->'source_view_id' ORDER BY n),'[]') INTO unbound
 FROM jsonb_array_elements(inputs->'sources') WITH ORDINALITY s(src,n)
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(config->'work_bindings') wb WHERE wb->>'native_content_digest'=src->>'native_content_digest');
 nominations:=ops.artifact_external_nominations(t,inputs,config,expected_records);
 IF COALESCE(product->'source_mapping_provenance','[]') IS DISTINCT FROM expected_provenance
  OR COALESCE(product->'unbound_source_ids','[]') IS DISTINCT FROM unbound
  OR product->'external_nominations' IS DISTINCT FROM nominations THEN
  RAISE EXCEPTION 'artifact source mapping/unavailable/alias population differs' USING ERRCODE='23514'; END IF;
 WITH cohort AS (SELECT r FROM jsonb_array_elements(expected_records) r), resolved AS (
  SELECT reference.r->>'contribution_id' attachment,
   COALESCE(jsonb_agg(caption.r->>'contribution_id' ORDER BY caption.r->>'contribution_id')
    FILTER (WHERE caption.r IS NOT NULL),'[]') targets
  FROM cohort reference LEFT JOIN cohort caption
   ON caption.r->'artifact'->>'occurrence_role'='caption'
    AND caption.r->'artifact'->>'source_work'=reference.r->'artifact'->>'source_work'
    AND caption.r->'artifact'->>'artifact_kind'=reference.r->'artifact'->>'artifact_kind'
    AND caption.r->'numbering'->>'value'=reference.r->'explicit_reference'->>'target_numbering'
    AND lower(btrim(caption.r->'artifact'->>'controlled_code',python_space))=
     lower(reference.r->'explicit_reference'->>'target_code')
  WHERE reference.r ? 'explicit_reference' GROUP BY reference.r->>'contribution_id'
 )
 SELECT COALESCE(jsonb_agg(jsonb_build_object('attachment',attachment,'targets',targets,
  'outcome',CASE jsonb_array_length(targets) WHEN 0 THEN 'no_compatible_candidate'
   WHEN 1 THEN 'witnessed_candidate' ELSE 'ambiguous' END) ORDER BY attachment),'[]')
 INTO explicit_references FROM resolved;
 IF product->'explicit_references' IS DISTINCT FROM explicit_references THEN
  RAISE EXCEPTION 'artifact explicit reference differs from selected source targets' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(id ORDER BY id),'[]') INTO anchors
 FROM jsonb_array_elements_text(COALESCE(config->'known_anchor_ids','[]')) selected(id);
 IF (SELECT count(*)<>count(DISTINCT id) FROM jsonb_array_elements_text(anchors) selected(id))
  OR COALESCE(product->'known_anchor_ids','[]') IS DISTINCT FROM anchors
  OR EXISTS(SELECT FROM jsonb_array_elements_text(anchors) selected(id)
   WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(expected_records) r WHERE r->>'contribution_id'=id)) THEN
  RAISE EXCEPTION 'artifact known anchors differ from exact selected immutable cohort inputs' USING ERRCODE='23514'; END IF;
 model_id:=encode(sha256(convert_to(data.canonical_json(policy),'UTF8')),'hex');
 IF (SELECT count(*)<>count(DISTINCT (p->>'left',p->>'right')) FROM jsonb_array_elements(product->'pairs') p) THEN
  RAISE EXCEPTION 'artifact pair population repeats' USING ERRCODE='23514'; END IF;
 FOR a,b,code_a,code_b IN
  WITH cohort AS (
   SELECT r,r->>'contribution_id' id,r->'artifact'->>'source_work' work_,
    r->'artifact'->>'artifact_kind' kind_,nullif(r->'artifact'->>'title','') title_,
    CASE WHEN btrim(r->'artifact'->>'controlled_code',python_space) COLLATE pg_catalog.pg_unicode_fast
     ~ '^[A-Za-z]?\d+([.\-]\d+)*[A-Za-z]?$'
     THEN lower(btrim(r->'artifact'->>'controlled_code',python_space)) END code_
   FROM jsonb_array_elements(expected_records) r
  ), aliases AS (
   SELECT DISTINCT id,work_,kind_,casefold(btrim(declared.literal,python_space) COLLATE pg_catalog.pg_unicode_fast) token
   FROM cohort CROSS JOIN LATERAL jsonb_array_elements_text(r->'artifact'->'aliases') declared(literal)
  ), keys(left_id,right_id) AS (
   SELECT l.id,r.id FROM cohort l JOIN cohort r USING (work_,kind_,code_) WHERE l.id<r.id
   UNION SELECT l.id,r.id FROM cohort l JOIN cohort r USING (work_,kind_)
    WHERE l.id<r.id AND l.title_ IS NOT NULL AND r.title_ IS NOT NULL
   UNION SELECT l.id,r.id FROM aliases l JOIN aliases r USING (work_,kind_,token) WHERE l.id<r.id
   UNION SELECT n->>'left',n->>'right' FROM jsonb_array_elements(nominations) n
   UNION SELECT least(d->>'source_id',endpoint->>'record_id'),greatest(d->>'source_id',endpoint->>'record_id')
    FROM jsonb_array_elements(declarations) d CROSS JOIN LATERAL jsonb_array_elements(d->'targets') endpoint
   UNION SELECT least(w->>'attachment',target.id),greatest(w->>'attachment',target.id)
    FROM jsonb_array_elements(explicit_references) w
    CROSS JOIN LATERAL jsonb_array_elements_text(w->'targets') target(id)
  )
  SELECT l.r,r.r,l.code_,r.code_ FROM keys JOIN cohort l ON l.id=keys.left_id
  JOIN cohort r ON r.id=keys.right_id
  WHERE l.r->>'occurrence_id'<>r.r->>'occurrence_id'
 LOOP
  numbering_:=ops.artifact_label_relation(a->'numbering',b->'numbering');
  revision_:=ops.artifact_label_relation(a->'revision',b->'revision');
  compatible:=(a->'artifact'->>'source_work'=b->'artifact'->>'source_work'
   AND a->'artifact'->>'artifact_kind'=b->'artifact'->>'artifact_kind'
   AND numbering_<>'different_observed');
  SELECT COALESCE(jsonb_agg(n->'relationship'->'contribution_id'),'[]') INTO pair_nomination_ids
   FROM jsonb_array_elements(nominations) n
   WHERE n->>'left'=a->>'contribution_id' AND n->>'right'=b->>'contribution_id';
  pair_nomination_ids:=pair_nomination_ids||COALESCE((
   SELECT jsonb_agg('artifact-declaration:'||encode(sha256(convert_to(data.canonical_json(d),'UTF8')),'hex'))
   FROM jsonb_array_elements(declarations) d CROSS JOIN LATERAL jsonb_array_elements(d->'targets') endpoint
   WHERE least(d->>'source_id',endpoint->>'record_id')=a->>'contribution_id'
    AND greatest(d->>'source_id',endpoint->>'record_id')=b->>'contribution_id'
  ),'[]');
  external_:=jsonb_array_length(pair_nomination_ids)>0;
  SELECT EXISTS(SELECT FROM jsonb_array_elements(explicit_references) w
   WHERE (w->>'attachment'=a->>'contribution_id' AND w->'targets' ? (b->>'contribution_id'))
    OR (w->>'attachment'=b->>'contribution_id' AND w->'targets' ? (a->>'contribution_id')))
   INTO explicit_;
  IF NOT compatible AND NOT external_ AND NOT explicit_ THEN CONTINUE; END IF;
  lexical:=CASE WHEN compatible THEN ops.artifact_lexical_score(a->'artifact'->>'title',b->'artifact'->>'title') ELSE 0 END;
  routes:='[]';
  IF compatible AND code_a IS NOT NULL AND code_a=code_b THEN
   routes:=routes||to_jsonb(CASE WHEN numbering_='same_observed' THEN 'exact_code' ELSE 'unscoped_code' END);
  END IF;
  IF compatible AND COALESCE(a->'artifact'->>'title','')<>'' AND COALESCE(b->'artifact'->>'title','')<>'' AND lexical*100 >=title_threshold THEN routes:=routes||'"lexical_title"'::jsonb; END IF;
  IF explicit_ THEN routes:=routes||'"explicit_reference"'::jsonb; END IF;
  IF external_ THEN routes:=routes||'"external_pairs"'::jsonb; END IF;
  alias_:=compatible AND EXISTS(SELECT FROM jsonb_array_elements_text(a->'artifact'->'aliases') x
   JOIN jsonb_array_elements_text(b->'artifact'->'aliases') y ON
    casefold(btrim(x,python_space) COLLATE pg_catalog.pg_unicode_fast)=
    casefold(btrim(y,python_space) COLLATE pg_catalog.pg_unicode_fast));
  IF alias_ THEN
   routes:=routes||'"native_alias_array"'::jsonb;
   expected_alias_pairs:=expected_alias_pairs||jsonb_build_array(jsonb_build_object('left',a->>'contribution_id','right',b->>'contribution_id'));
  END IF;
  IF routes='[]'::jsonb THEN CONTINUE; END IF;
  expected_pairs:=expected_pairs||jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id'));
  SELECT p INTO STRICT pair_ FROM jsonb_array_elements(product->'pairs') p WHERE p->>'left'=a->>'contribution_id' AND p->>'right'=b->>'contribution_id';
  excluded:=NOT compatible OR (anchors ? (a->>'contribution_id') AND anchors ? (b->>'contribution_id')) OR COALESCE(config->'exclusions','[]') @> jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')) OR COALESCE(config->'exclusions','[]') @> jsonb_build_array(jsonb_build_array(b->>'contribution_id',a->>'contribution_id'));
  score_status:=CASE WHEN excluded THEN 'excluded'
   WHEN 'reference' IN (a->'artifact'->>'occurrence_role',b->'artifact'->>'occurrence_role') THEN 'reference_only'
   WHEN code_a IS NOT NULL AND code_b IS NOT NULL AND numbering_<>'same_observed' THEN 'namespace_unavailable'
   WHEN (code_a IS NULL OR code_b IS NULL) AND
    (COALESCE(a->'artifact'->>'title','')='' OR COALESCE(b->'artifact'->>'title','')='') THEN 'no_comparable_features'
   ELSE 'scored' END;
  IF pair_->'candidate_routes' IS DISTINCT FROM routes OR pair_->>'standing'<>'candidate_relative_private'
   OR pair_->>'numbering_relation' IS DISTINCT FROM numbering_ OR pair_->>'revision_relation' IS DISTINCT FROM revision_
   OR pair_->>'score_status' IS DISTINCT FROM score_status
   OR pair_->>'scope_state' IS DISTINCT FROM (CASE WHEN excluded THEN 'excluded' ELSE 'compatible' END)
   OR pair_->>'lexical_score' IS NULL OR abs((pair_->>'lexical_score')::double precision-lexical)>1e-12
   OR pair_->'dependencies' IS DISTINCT FROM (SELECT jsonb_agg(value ORDER BY value) FROM (SELECT DISTINCT value FROM jsonb_array_elements_text(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')||(a->'artifact'->'dependencies')||(b->'artifact'->'dependencies')||pair_nomination_ids)) d) THEN
   RAISE EXCEPTION 'artifact candidate route/scope/dependencies differ from exact frozen cohort' USING ERRCODE='23514'; END IF;
  IF score_status<>'scored' THEN
   IF pair_->>'model_probability' IS NOT NULL OR pair_->>'model_id' IS NOT NULL OR COALESCE(pair_->'model_evidence','[]')<>'[]'::jsonb THEN RAISE EXCEPTION 'unavailable artifact pair carries a model score' USING ERRCODE='23514'; END IF;
   CONTINUE;
  END IF;
  code_gamma:=CASE WHEN code_a IS NULL OR code_b IS NULL THEN -1 WHEN code_a=code_b THEN 1 ELSE 0 END;
  title_a:=casefold(btrim(a->'artifact'->>'title',python_space) COLLATE pg_catalog.pg_unicode_fast);
  title_b:=casefold(btrim(b->'artifact'->>'title',python_space) COLLATE pg_catalog.pg_unicode_fast);
  title_gamma:=CASE WHEN title_a IS NULL OR title_b IS NULL THEN -1 WHEN title_a=title_b THEN 1 ELSE 0 END;
  code_mw:=CASE code_gamma WHEN -1 THEN 0 WHEN 1 THEN log(2::numeric,((policy->>'code_m')::numeric/(policy->>'code_u')::numeric))::double precision ELSE log(2::numeric,((1-(policy->>'code_m')::numeric)/(1-(policy->>'code_u')::numeric)))::double precision END;
  title_mw:=CASE title_gamma WHEN -1 THEN 0 WHEN 1 THEN log(2::numeric,((policy->>'title_m')::numeric/(policy->>'title_u')::numeric))::double precision ELSE log(2::numeric,((1-(policy->>'title_m')::numeric)/(1-(policy->>'title_u')::numeric)))::double precision END;
  log_odds:=ln((policy->>'prior')::double precision)-ln(1-(policy->>'prior')::double precision)+(code_mw+title_mw)*ln(2::double precision);
  probability:=CASE WHEN log_odds>745 THEN 1 WHEN log_odds < -745 THEN 0 WHEN log_odds>=0 THEN 1/(1+exp(-log_odds)) ELSE exp(log_odds)/(1+exp(log_odds)) END;
  IF pair_->>'model_id' IS DISTINCT FROM model_id OR pair_->>'model_probability' IS NULL OR abs((pair_->>'model_probability')::double precision-probability)>1e-10
   OR (SELECT count(*)<>4 OR count(DISTINCT f->>'name')<>4 FROM jsonb_array_elements(pair_->'model_evidence') f) THEN
   RAISE EXCEPTION 'artifact probability/model evidence differs from frozen exact-comparison likelihood' USING ERRCODE='23514'; END IF;
  FOR field_ IN SELECT value FROM jsonb_array_elements(pair_->'model_evidence') LOOP
   expected_value:=CASE field_->>'name' WHEN 'gamma_controlled_code' THEN code_gamma WHEN 'gamma_title' THEN title_gamma WHEN 'mw_controlled_code' THEN code_mw WHEN 'mw_title' THEN title_mw END;
   IF expected_value IS NULL OR field_->>'value' IS NULL OR abs((field_->>'value')::double precision-expected_value)>1e-10 THEN
    RAISE EXCEPTION 'artifact model comparison evidence differs from declared likelihood' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 IF jsonb_array_length(product->'pairs')<>jsonb_array_length(expected_pairs) THEN
  RAISE EXCEPTION 'artifact candidate population is incomplete or has extra pairs' USING ERRCODE='23514'; END IF;
 IF product->'native_alias_pairs' IS DISTINCT FROM (SELECT COALESCE(jsonb_agg(p ORDER BY p->>'left',p->>'right'),'[]') FROM jsonb_array_elements(expected_alias_pairs) p) THEN
  RAISE EXCEPTION 'artifact alias blocking differs from exact eligible observed aliases' USING ERRCODE='23514'; END IF;
 WITH routes AS (
  SELECT route,n FROM unnest(ARRAY['exact_code','unscoped_code','lexical_title','explicit_reference','external_pairs',
   'native_alias_array']) WITH ORDINALITY r(route,n)
 ), counts AS (
  SELECT route,n,count(p) nominated,count(p) FILTER (WHERE p->>'score_status'='scored') eligible,
   count(p) FILTER (WHERE p->'candidate_routes'->>0=route) marginal
  FROM routes LEFT JOIN LATERAL (
   SELECT p FROM jsonb_array_elements(product->'pairs') p WHERE p->'candidate_routes' ? route
  ) candidates(p) ON true GROUP BY route,n
 )
 SELECT jsonb_agg(to_jsonb(summary)-'n' ORDER BY n) INTO expected_counts
 FROM (SELECT *,sum(marginal) OVER (ORDER BY n) cumulative FROM counts) summary;
 IF product->'route_counts' IS DISTINCT FROM expected_counts THEN
  RAISE EXCEPTION 'artifact route counts differ from exact pair ledger' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(config->'exclusions','[]')) ep
  WHERE jsonb_array_length(ep)<>2 OR ep->>0=ep->>1 OR EXISTS(SELECT FROM jsonb_array_elements_text(ep) endpoint WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(expected_records) r WHERE r->>'contribution_id'=endpoint))) THEN
  RAISE EXCEPTION 'artifact configured pair endpoint lies outside source cohort' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'artifact candidate or source custody cannot resolve exact population' USING ERRCODE='23514';
WHEN invalid_text_representation OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_artifact_identity(ops.task,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.model_observation_policy(release_ text)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT convert_from(content,'UTF8')::jsonb FROM sem.input
 WHERE release_id=release_ AND input_kind='dependency'
 AND input_name='execution/implementation/operations/model-observation.json'
$$;
REVOKE ALL ON FUNCTION ops.model_observation_policy(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.model_definition_declaration(policy jsonb,config_ jsonb)
RETURNS text LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT string_agg(CASE WHEN jsonb_typeof(part)='object' THEN to_json(config_->>(part->>'field'))::text
                        ELSE part#>>'{}' END,'' ORDER BY i)
 FROM jsonb_array_elements(policy->'definition'->(config_->>'description_arm')) WITH ORDINALITY x(part,i)
$$;
REVOKE ALL ON FUNCTION ops.model_definition_declaration(jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.located_model_request(
 release_ text,method_ text,policy jsonb,config_ jsonb,context_id text,context_digest text,body text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 WITH definition AS (SELECT method_='structure.definition_components/10' enabled),
 profile AS (SELECT config_->'profile' p),
 schema_ AS (SELECT CASE WHEN enabled THEN ops.model_definition_declaration(policy,config_)
                        ELSE policy->>'clause' END declaration FROM definition),
 request_ AS (SELECT enabled,declaration,
  (p-ARRAY['snapshot','artifact_hashes','timeout_seconds'])||jsonb_build_object(
   'timeout_seconds',data.decimal_canonical(p->>'timeout_seconds'),
   'artifact_hashes',(SELECT jsonb_agg(a ORDER BY (a->>0) COLLATE "C",(a->>1) COLLATE "C")
                     FROM jsonb_array_elements(p->'artifact_hashes') a)) profile_,
  CASE WHEN enabled THEN data.decimal_canonical(config_->>'threshold') ELSE '0.5' END threshold_,
  CASE WHEN enabled THEN COALESCE(config_->>'evaluation_overlap','flat') ELSE 'flat' END overlap_,
  enabled AND (config_->>'evaluation_overlap') IS NOT NULL evaluation_
  FROM definition,profile,schema_),
 value_ AS (SELECT CASE policy->>'request_version'
  WHEN 'located-model-request-1' THEN jsonb_build_array(
   'located-model-request-1',release_,CASE WHEN enabled THEN 'native-local-v1' ELSE 'native-combined-v2' END,
   declaration,profile_,jsonb_build_array(jsonb_build_array(method_,context_id,context_digest,body)),
   threshold_,overlap_,evaluation_,policy->'inference')
  WHEN 'located-model-request-2' THEN jsonb_build_array(
   'located-model-request-2',jsonb_build_object(
    'release',release_,'version',CASE WHEN enabled THEN 'native-local-v1' ELSE 'native-combined-v2' END,
    'declaration',declaration,'profile',profile_,'threshold',threshold_,'overlap',overlap_,
    'evaluation',evaluation_,'inference',policy->'inference'),
   jsonb_build_array(encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
    'located-model-member-2',method_,context_id,context_digest,body)),'UTF8')),'hex')))
  ELSE NULL END payload FROM request_)
 SELECT encode(sha256(convert_to(data.canonical_json(payload),'UTF8')),'hex') FROM value_
$$;
REVOKE ALL ON FUNCTION ops.located_model_request(text,text,jsonb,jsonb,text,text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.located_model_observation_matches(report jsonb,request_ text)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE receipt jsonb; header_ jsonb; members_ jsonb; ordinal_ integer; expected_ text;
BEGIN
 IF request_ IS NULL OR jsonb_typeof(report) IS DISTINCT FROM 'object'
  OR report->>'request_digest' IS DISTINCT FROM request_
  OR report->>'computation' IS DISTINCT FROM request_
  OR jsonb_typeof(report->'raw_json') IS DISTINCT FROM 'string'
  OR jsonb_typeof(report->'effective_profile_json') IS DISTINCT FROM 'string' THEN RETURN false; END IF;
 IF report->>'batch_receipt_json' IS NULL THEN
  IF report->>'member_ordinal' IS NOT NULL THEN RETURN false; END IF;
  -- Historical receipts remain readable, but the caller must admit them under v1.
  expected_:=encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
   request_,report->>'raw_json',report->>'effective_profile_json')),'UTF8')),'hex');
 ELSE
  IF jsonb_typeof(report->'batch_receipt_json') IS DISTINCT FROM 'string'
   OR jsonb_typeof(report->'member_ordinal') IS DISTINCT FROM 'number'
   OR report->>'member_ordinal' !~ '^(0|[1-9][0-9]*)$' THEN RETURN false; END IF;
  receipt:=(report->>'batch_receipt_json')::jsonb;
  IF jsonb_typeof(receipt) IS DISTINCT FROM 'object'
   OR receipt-ARRAY['version','header','members','digest']<>'{}'::jsonb
   OR NOT (receipt ?& ARRAY['version','header','members','digest'])
   OR jsonb_typeof(receipt->'version') IS DISTINCT FROM 'number'
   OR receipt->>'version' IS DISTINCT FROM '2'
   OR jsonb_typeof(receipt->'header') IS DISTINCT FROM 'object'
   OR jsonb_typeof(receipt->'members') IS DISTINCT FROM 'array'
   OR jsonb_typeof(receipt->'digest') IS DISTINCT FROM 'string' THEN RETURN false; END IF;
  header_:=receipt->'header'; members_:=receipt->'members';
  IF header_-ARRAY['release','version','declaration','profile','threshold','overlap','evaluation','inference']<>'{}'::jsonb
   OR NOT (header_ ?& ARRAY['release','version','declaration','profile','threshold','overlap','evaluation','inference'])
   OR EXISTS(SELECT FROM unnest(ARRAY['release','version','declaration','threshold','overlap']) k
             WHERE jsonb_typeof(header_->k) IS DISTINCT FROM 'string')
   OR jsonb_typeof(header_->'profile') IS DISTINCT FROM 'object'
   OR jsonb_typeof(header_->'evaluation') IS DISTINCT FROM 'boolean'
   OR jsonb_typeof(header_->'inference') IS DISTINCT FROM 'object'
   OR jsonb_array_length(members_)=0
   OR EXISTS(SELECT FROM jsonb_array_elements(members_) m
             WHERE jsonb_typeof(m) IS DISTINCT FROM 'string' OR m#>>'{}' !~ '^[0-9a-f]{64}$')
   OR (SELECT count(*)<>count(DISTINCT m) FROM jsonb_array_elements(members_) m)
   OR receipt->>'digest' IS DISTINCT FROM request_
   OR encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       'located-model-request-2',header_,members_)),'UTF8')),'hex') IS DISTINCT FROM request_
   THEN RETURN false; END IF;
  ordinal_:=(report->>'member_ordinal')::integer;
  IF ordinal_>=jsonb_array_length(members_) THEN RETURN false; END IF;
  expected_:=encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
   'located-model-observation-2',request_,ordinal_,members_->>ordinal_,
   report->>'raw_json',report->>'effective_profile_json')),'UTF8')),'hex');
 END IF;
 RETURN report->>'observation_digest' IS NOT DISTINCT FROM expected_;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range OR invalid_parameter_value THEN
 RETURN false;
END $$;
REVOKE ALL ON FUNCTION ops.located_model_observation_matches(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_definition_window_requests(
 release_ text,detail jsonb,config_ jsonb,passage_map jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE policy jsonb:=ops.model_observation_policy(release_); passage_id text; passage jsonb;
 body text; snippet text; window_ jsonb; ledger jsonb; start_ integer; end_ integer; max_chars integer;
 overlap_ integer; windows integer; limit_ integer; boundary_ integer; cursor_ integer:=0; count_ integer:=0;
 offset_ integer; digest_ text; request_ text; envelope jsonb; code integer; status_ text;
BEGIN
 IF policy IS NULL OR COALESCE(policy->>'request_version','') NOT IN
  ('located-model-request-1','located-model-request-2')
  OR jsonb_typeof(detail->'window_outcomes') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'definition window outcomes lack the released model policy' USING ERRCODE='23514'; END IF;
 IF (config_->>'use_model')::boolean THEN
  IF detail->>'schema_declaration' IS DISTINCT FROM ops.model_definition_declaration(policy,config_) THEN
   RAISE EXCEPTION 'definition schema differs from exact released ordered declaration' USING ERRCODE='23514'; END IF;
  max_chars:=least((policy->'definition_windows'->>'chars')::integer,
   greatest(1,(config_->'profile'->>'max_input_bytes')::integer/4));
  overlap_:=least((policy->'definition_windows'->>'overlap')::integer,max_chars/4);
  limit_:=(policy->'definition_windows'->>'limit')::integer;
  FOR passage_id IN SELECT value FROM jsonb_array_elements_text(config_->'target_ids') LOOP
   passage:=passage_map->passage_id; body:=passage->>'text'; offset_:=(passage->>'start')::integer;
   start_:=0; end_:=0; windows:=0;
   WHILE start_<length(body) AND windows<limit_ LOOP
    end_:=least(length(body),start_+max_chars);
    IF end_<length(body) THEN
     boundary_:=end_-1;
     WHILE boundary_>=start_+max_chars/2 AND substr(body,boundary_+1,1)<>' ' LOOP boundary_:=boundary_-1; END LOOP;
     IF boundary_>start_ AND boundary_>=start_+max_chars/2 THEN end_:=boundary_; END IF;
    END IF;
    snippet:=substr(body,start_+1,end_-start_);
    window_:=passage||jsonb_build_object('start',offset_+start_,'end',offset_+end_,'text',snippet);
    digest_:=encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(window_)),'UTF8')),'hex');
    request_:=ops.located_model_request(release_,'structure.definition_components/10',policy,config_,
      'definition-target:'||digest_,digest_,snippet);
    ledger:=detail->'window_outcomes'->cursor_; cursor_:=cursor_+1;
    status_:=ledger->>'status';
    IF request_ IS NULL OR ledger IS NULL OR status_ IS NULL OR status_ NOT IN ('returned','failed','refused')
     OR ledger IS DISTINCT FROM jsonb_build_object('passage_id',passage_id,'start',offset_+start_,
       'end',offset_+end_,'request_digest',request_,'status',status_) THEN
     RAISE EXCEPTION 'definition window differs from exact configured population' USING ERRCODE='23514'; END IF;
    IF status_='returned' THEN
     envelope:=detail->'raw_reports'->count_; count_:=count_+1;
     IF (policy->>'request_version'='located-model-request-2' AND
          (envelope->>'batch_receipt_json' IS NULL OR envelope->>'member_ordinal' IS NULL))
      OR (policy->>'request_version'='located-model-request-1' AND
          (envelope->>'batch_receipt_json' IS NOT NULL OR envelope->>'member_ordinal' IS NOT NULL))
      OR ops.located_model_observation_matches(envelope,request_) IS DISTINCT FROM true
      OR envelope->>'context_digest' IS DISTINCT FROM digest_
      OR envelope->>'passage_id' IS DISTINCT FROM passage_id
      OR envelope->'window_start' IS DISTINCT FROM to_jsonb(offset_+start_)
      OR envelope->'window_end' IS DISTINCT FROM to_jsonb(offset_+end_) THEN
      RAISE EXCEPTION 'definition observation differs from the selected request' USING ERRCODE='23514'; END IF;
    END IF;
    windows:=windows+1;
    EXIT WHEN end_=length(body);
    start_:=greatest(start_+1,end_-overlap_);
    WHILE start_<end_ LOOP
     code:=ascii(substr(body,start_,1));
     EXIT WHEN code BETWEEN 9 AND 13 OR code BETWEEN 28 AND 32 OR code BETWEEN 8192 AND 8202
      OR code IN (133,160,5760,8232,8233,8239,8287,12288);
     start_:=start_+1;
    END LOOP;
   END LOOP;
   IF end_<length(body) THEN
    IF detail->'window_outcomes'->cursor_ IS DISTINCT FROM jsonb_build_object(
     'passage_id',passage_id,'start',offset_+end_,'end',offset_+length(body),'status','uninspected') THEN
     RAISE EXCEPTION 'definition outcome misses bounded uninspected tail' USING ERRCODE='23514'; END IF;
    cursor_:=cursor_+1;
   END IF;
  END LOOP;
 END IF;
 IF cursor_<>jsonb_array_length(detail->'window_outcomes') OR count_<>jsonb_array_length(detail->'raw_reports') THEN
  RAISE EXCEPTION 'definition report contains unbound window outcomes' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION ops.validate_definition_window_requests(text,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.definition_role_candidates(detail jsonb,config_ jsonb,passage_map jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE window_ jsonb; passage_ jsonb; raw_ jsonb; candidate jsonb; role_ text; label_ text;
 lo integer; hi integer; start_ integer; end_ integer; index_ bigint; text_ text; result_ jsonb:='[]';
BEGIN
 IF detail->>'version' IS DISTINCT FROM 'located-definition-extraction-5'
 OR detail->>'description_arm' IS DISTINCT FROM config_->>'description_arm'
 OR detail->>'overlap_policy' IS DISTINCT FROM COALESCE(config_->>'evaluation_overlap','flat')
 OR jsonb_typeof(detail->'raw_reports') IS DISTINCT FROM 'array'
 OR ((config_->>'use_model')::boolean AND (
  (detail->'profile')-'timeout_seconds' IS DISTINCT FROM (config_->'profile')-'timeout_seconds'
  OR (detail->'profile'->>'timeout_seconds')::numeric IS DISTINCT FROM (config_->'profile'->>'timeout_seconds')::numeric))
 OR (NOT (config_->>'use_model')::boolean AND detail->'raw_reports'<>'[]'::jsonb) THEN
  RAISE EXCEPTION 'definition roles lack their declared model operation' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements(detail->'raw_reports') w
    GROUP BY w->>'computation' HAVING count(*)>1) THEN
  RAISE EXCEPTION 'duplicate definition model envelope' USING ERRCODE='23514'; END IF;
 FOR window_ IN SELECT value FROM jsonb_array_elements(detail->'raw_reports') LOOP
  passage_:=passage_map->(window_->>'passage_id');
  lo:=(window_->>'window_start')::integer; hi:=(window_->>'window_end')::integer;
  IF passage_ IS NULL OR NOT config_->'target_ids' ? (window_->>'passage_id')
   OR lo IS NULL OR hi IS NULL OR lo<(passage_->>'start')::integer OR hi>(passage_->>'end')::integer OR hi<=lo
   OR window_->>'computation' IS NULL OR window_->>'profile' IS DISTINCT FROM detail->>'profile_fingerprint'
   OR window_->>'pack' IS DISTINCT FROM detail->>'pack_fingerprint'
   OR window_->>'context_id' IS DISTINCT FROM 'definition-target:'||(window_->>'context_digest')
   OR COALESCE(window_->'preparation'->>'synthetic_suffix','?') NOT IN ('','.')
   OR window_->'preparation'->>'consumed_text' IS DISTINCT FROM
      substring(passage_->>'text' FROM lo-(passage_->>'start')::integer+1 FOR hi-lo)
      ||(window_->'preparation'->>'synthetic_suffix') THEN
   RAISE EXCEPTION 'definition model envelope differs from its exact window' USING ERRCODE='23514'; END IF;
  raw_:=(window_->>'raw_json')::jsonb->'entities';
  IF jsonb_typeof(raw_) IS DISTINCT FROM 'object' THEN CONTINUE; END IF;
  IF EXISTS(SELECT FROM jsonb_each(raw_) e WHERE
     e.key NOT IN (config_->>'term_entity',config_->>'content_entity')
     OR jsonb_typeof(e.value)<>'array') THEN CONTINUE; END IF;
  FOREACH role_ IN ARRAY ARRAY['term','content'] LOOP
   label_:=config_->>(role_||'_entity');
   FOR candidate,index_ IN SELECT value,ordinality-1 FROM jsonb_array_elements(COALESCE(raw_->label_,'[]'::jsonb)) WITH ORDINALITY LOOP
    IF jsonb_typeof(candidate->'start') IS DISTINCT FROM 'number'
     OR jsonb_typeof(candidate->'end') IS DISTINCT FROM 'number'
     OR (candidate->>'start') !~ '^[0-9]{1,9}$' OR (candidate->>'end') !~ '^[0-9]{1,9}$'
     OR jsonb_typeof(candidate->'text') IS DISTINCT FROM 'string' THEN CONTINUE; END IF;
    start_:=(candidate->>'start')::integer; end_:=(candidate->>'end')::integer;
    text_:=candidate->>'text';
    IF start_>=end_ OR end_>hi-lo OR text_ IS DISTINCT FROM
     substring(passage_->>'text' FROM lo-(passage_->>'start')::integer+start_+1 FOR end_-start_) THEN CONTINUE; END IF;
    result_:=result_||jsonb_build_array(jsonb_build_object(
     'role',role_,'window_start',lo,'window_end',hi,'envelope',window_->>'computation','index',index_,
     'span',jsonb_build_object('passage_id',window_->>'passage_id','start',lo+start_,'end',lo+end_,'text',text_)));
   END LOOP;
  END LOOP;
 END LOOP;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.definition_role_candidates(jsonb,jsonb,jsonb) FROM PUBLIC;

-- Resolve each declared directed relation against the verified entity-channel indices.
-- Component identity deduplicates identical readings across overlapping windows.
CREATE OR REPLACE FUNCTION ops.definition_model_components(detail jsonb,config_ jsonb,passage_map jsonb,roles_ jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE window_ jsonb; passage_ jsonb; raw_ jsonb; relations_ jsonb; window_roles jsonb;
 relation_ jsonb; head_ jsonb; tail_ jsonb; term_ jsonb; content_ jsonb; interpretation_ text;
 meaning_ jsonb; key_ text; components_ jsonb:='{}'; lo integer;
BEGIN
 FOR window_ IN SELECT value FROM jsonb_array_elements(detail->'raw_reports') LOOP
  raw_:=(window_->>'raw_json')::jsonb;
  relations_:=raw_->'relation_extraction'->(config_->>'attachment_relation');
  IF jsonb_typeof(relations_) IS DISTINCT FROM 'array' THEN CONTINUE; END IF;
  SELECT COALESCE(jsonb_agg(r),'[]') INTO window_roles FROM jsonb_array_elements(roles_) r
   WHERE r->>'envelope'=window_->>'computation';
  passage_:=passage_map->(window_->>'passage_id');
  lo:=(window_->>'window_start')::integer;
  FOR relation_ IN SELECT value FROM jsonb_array_elements(relations_) LOOP
   head_:=relation_->'head'; tail_:=relation_->'tail';
   IF jsonb_typeof(head_->'start') IS DISTINCT FROM 'number' OR jsonb_typeof(head_->'end') IS DISTINCT FROM 'number'
    OR jsonb_typeof(tail_->'start') IS DISTINCT FROM 'number' OR jsonb_typeof(tail_->'end') IS DISTINCT FROM 'number'
    OR jsonb_typeof(head_->'text') IS DISTINCT FROM 'string' OR jsonb_typeof(tail_->'text') IS DISTINCT FROM 'string' THEN CONTINUE; END IF;
   -- The last valid term attribute at an exact offset is the decoder's selected reading.
   SELECT r->'span',attribute.label INTO term_,interpretation_ FROM jsonb_array_elements(window_roles) r
   CROSS JOIN LATERAL (SELECT raw_->'entities'->(config_->>'term_entity')->((r->>'index')::integer)->'interpretation' value) a
   CROSS JOIN LATERAL (SELECT CASE WHEN jsonb_typeof(a.value)='object' THEN a.value->>'label' ELSE a.value#>>'{}' END label) attribute
   WHERE r->>'role'='term' AND attribute.label IN ('definition','explanation','unresolved')
    AND head_->>'start'=((r->'span'->>'start')::integer-lo)::text
    AND head_->>'end'=((r->'span'->>'end')::integer-lo)::text
    AND head_->'text'=r->'span'->'text'
   ORDER BY (r->>'index')::integer DESC LIMIT 1;
   IF term_ IS NULL THEN CONTINUE; END IF;
   SELECT r->'span' INTO content_ FROM jsonb_array_elements(window_roles) r
   WHERE r->>'role'='content'
    AND tail_->>'start'=((r->'span'->>'start')::integer-lo)::text
    AND tail_->>'end'=((r->'span'->>'end')::integer-lo)::text
    AND tail_->'text'=r->'span'->'text' LIMIT 1;
   IF content_ IS NULL THEN CONTINUE; END IF;
   meaning_:=jsonb_strip_nulls(jsonb_build_object('term',term_,'content',content_,
    'interpretation',interpretation_,'basis','model_reading','scope',passage_->>'scope',
    'effective_version',passage_->>'effective_version','alternatives','[]'::jsonb,
    'evidence',jsonb_build_array(passage_->>'passage_id'),
    'reason','Target-local decoded span roles and directed attachment; independent support unassessed.'));
   key_:=encode(sha256(convert_to(data.canonical_json(meaning_),'UTF8')),'hex');
   components_:=components_||jsonb_build_object(key_,meaning_||jsonb_build_object('component_id',key_));
  END LOOP;
 END LOOP;
 RETURN (SELECT COALESCE(jsonb_agg(value ORDER BY key),'[]') FROM jsonb_each(components_));
END $$;
REVOKE ALL ON FUNCTION ops.definition_model_components(jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.clause_model_axis(raw_ jsonb,labels_ text[])
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE entry jsonb; name_ text; score_ jsonb; result_ jsonb:='[]'; seen text[]:=ARRAY[]::text[];
BEGIN
 IF nullif(raw_,'null') IS NULL THEN RETURN result_; END IF;
 IF jsonb_typeof(raw_)<>'array' THEN raw_:=jsonb_build_array(raw_); END IF;
 FOR entry IN SELECT value FROM jsonb_array_elements(raw_) LOOP
  name_:=CASE jsonb_typeof(entry) WHEN 'object' THEN entry->>'label' WHEN 'string' THEN entry#>>'{}' END;
  score_:=nullif(entry->'confidence','null');
  IF name_ IS NULL OR NOT name_=ANY(labels_) OR name_=ANY(seen)
   OR (score_ IS NOT NULL AND jsonb_typeof(score_)<>'number') THEN RETURN NULL; END IF;
  IF score_ IS NOT NULL AND NOT ((score_#>>'{}')::numeric BETWEEN 0 AND 1) THEN RETURN NULL; END IF;
  seen:=array_append(seen,name_);
  result_:=result_||jsonb_build_array(jsonb_strip_nulls(jsonb_build_object(
   'label',name_,'score',score_,'accepted',COALESCE(name_<>'unresolved' AND (score_#>>'{}')::numeric>=0.5,false))));
 END LOOP;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.clause_model_axis(jsonb,text[]) FROM PUBLIC;

-- A retained native token interval is a mechanical source projection, not a matcher.
CREATE OR REPLACE FUNCTION ops.primary_structural_token_span(layers jsonb,refs jsonb,p_view kb.source_view)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE ref jsonb; node jsonb; extents jsonb; first_ jsonb; prior_ bigint; lo bigint; hi bigint; population jsonb;
BEGIN
 IF jsonb_typeof(refs) IS DISTINCT FROM 'array' OR jsonb_array_length(refs)=0 THEN
  RAISE EXCEPTION 'primary token span requires explicit native members' USING ERRCODE='23514'; END IF;
 FOR ref IN SELECT value FROM jsonb_array_elements(refs) LOOP
  node:=ops.primary_characterization_node(layers,ref);
  IF node->>'kind' IS DISTINCT FROM 'native.token' OR node->'native_token' IS NULL THEN
   RAISE EXCEPTION 'primary role member is not a native token' USING ERRCODE='23514'; END IF;
  IF population IS NULL THEN
   population:=jsonb_build_array(ref->'layer',node->'native_token'->'native_run',node->'native_token'->'container');
  ELSIF population IS DISTINCT FROM jsonb_build_array(ref->'layer',node->'native_token'->'native_run',node->'native_token'->'container')
   OR (node->'native_token'->>'index')::bigint<>prior_+1 THEN
   RAISE EXCEPTION 'primary role has discontinuous or foreign token members' USING ERRCODE='23514'; END IF;
  prior_:=(node->'native_token'->>'index')::bigint;
  extents:=ops.primary_characterization_extents(layers,ref,node,p_view);
  IF jsonb_array_length(extents)<>1 THEN RAISE EXCEPTION 'primary token has no unique literal source extent' USING ERRCODE='23514'; END IF;
  first_:=extents->0;
  IF first_->>'synthetic' IS DISTINCT FROM 'false' OR node->'native_token'->>'text' IS DISTINCT FROM first_->>'text' OR (hi IS NOT NULL AND (first_->>'start')::bigint<hi) THEN
   RAISE EXCEPTION 'primary token order or literal text differs from source' USING ERRCODE='23514'; END IF;
  lo:=coalesce(lo,(first_->>'start')::bigint); hi:=(first_->>'end')::bigint;
 END LOOP;
 RETURN jsonb_build_array(lo,hi);
END $$;
REVOKE ALL ON FUNCTION ops.primary_structural_token_span(jsonb,jsonb,kb.source_view) FROM PUBLIC;

-- Adjacency follows retained sentence placement and native container membership.
CREATE OR REPLACE FUNCTION ops.primary_structural_sentence_context(layers jsonb,focus jsonb,passage jsonb,p_view kb.source_view)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE entry record; sentence jsonb; ref jsonb; extents jsonb; container_ jsonb; population jsonb; candidates jsonb:='[]';
 owner_ jsonb; before_ jsonb; after_ jsonb; lo bigint; hi bigint;
BEGIN
 FOR entry IN SELECT * FROM jsonb_each(layers) LOOP
  FOR sentence IN SELECT value FROM jsonb_array_elements(entry.value->'annotations') WHERE value->>'kind'='native.sentence' AND value->>'family'='spacy.sentences' LOOP
   ref:=jsonb_build_object('layer',entry.key::jsonb,'local_id',sentence->>'local_id');
   extents:=ops.primary_characterization_extents(layers,ref,sentence,p_view);
   SELECT min((e->>'start')::bigint),max((e->>'end')::bigint) INTO lo,hi FROM jsonb_array_elements(extents) e;
   SELECT DISTINCT jsonb_build_array(entry.key::jsonb,t->'native_token'->'native_run',t->'native_token'->'container') INTO STRICT container_
    FROM jsonb_array_elements(entry.value->'annotations') t WHERE t->'native_token'->>'sentence'=sentence->>'local_id';
   candidates:=candidates||jsonb_build_array(jsonb_build_object('population',container_,'start',lo,'end',hi));
  END LOOP;
 END LOOP;
 SELECT c INTO STRICT owner_ FROM jsonb_array_elements(candidates) c
  WHERE (c->>'start')::bigint<=(focus->>'start')::bigint AND (focus->>'end')::bigint<=(c->>'end')::bigint;
 SELECT c INTO before_ FROM jsonb_array_elements(candidates) c WHERE c->'population'=owner_->'population'
  AND (c->>'end')::bigint<=(owner_->>'start')::bigint ORDER BY (c->>'end')::bigint DESC LIMIT 1;
 SELECT c INTO after_ FROM jsonb_array_elements(candidates) c WHERE c->'population'=owner_->'population'
  AND (c->>'start')::bigint>=(owner_->>'end')::bigint ORDER BY (c->>'start')::bigint LIMIT 1;
 IF before_ IS NOT NULL AND (before_->>'start')::bigint>=(passage->>'start')::bigint THEN
  before_:=jsonb_build_object('passage_id',passage->>'passage_id','start',before_->'start','end',before_->'end',
   'text',substring(p_view.projection->>'text' FROM (before_->>'start')::integer+1 FOR (before_->>'end')::integer-(before_->>'start')::integer));
 ELSE before_:=NULL; END IF;
 IF after_ IS NOT NULL AND (after_->>'end')::bigint<=(passage->>'end')::bigint THEN
  after_:=jsonb_build_object('passage_id',passage->>'passage_id','start',after_->'start','end',after_->'end',
   'text',substring(p_view.projection->>'text' FROM (after_->>'start')::integer+1 FOR (after_->>'end')::integer-(after_->>'start')::integer));
 ELSE after_:=NULL; END IF;
 RETURN jsonb_build_object('preceding',before_,'following',after_);
END $$;
REVOKE ALL ON FUNCTION ops.primary_structural_sentence_context(jsonb,jsonb,jsonb,kb.source_view) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_clause_classification(inputs jsonb,config_ jsonb,item jsonb,detail jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reading_ jsonb; selection_ jsonb; passage_ jsonb; source_ jsonb; retained jsonb; frame_ jsonb; focus_ jsonb;
 layers jsonb; ref jsonb; node jsonb; answer jsonb; native_ jsonb; request_ jsonb; scope_ jsonb; declaration jsonb;
 expected_ jsonb; labels_ jsonb; offered jsonb; observed jsonb; selected_ jsonb; extents jsonb; v kb.source_view;
 before_ jsonb; after_ jsonb; examined jsonb; wanted_pin jsonb; disposition_ text; lo integer; hi integer; keys_ jsonb;
BEGIN
 IF config_->>'_operation_version' IS DISTINCT FROM '3' OR detail->>'version' IS DISTINCT FROM 'primary-clause-functions-1'
  OR item->>'context_policy' IS DISTINCT FROM config_->>'context_policy'
  OR (SELECT coalesce(jsonb_agg(r->'selection' ORDER BY i),'[]') FROM jsonb_array_elements(item->'readings') WITH ORDINALITY x(r,i)) IS DISTINCT FROM config_->'focuses'
  OR EXISTS(SELECT FROM jsonb_array_elements(coalesce(detail->'characterization_layers','[]')) pin WHERE NOT coalesce(config_->'characterization_layers','[]') @> jsonb_build_array(pin)) THEN
  RAISE EXCEPTION 'clause projection differs from frozen primary selection' USING ERRCODE='23514'; END IF;
 FOR reading_ IN SELECT value FROM jsonb_array_elements(item->'readings') LOOP
  selection_:=reading_->'selection';
  SELECT p INTO STRICT passage_ FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'passage_id'=selection_->>'passage_id';
  SELECT s INTO STRICT source_ FROM jsonb_array_elements(inputs->'sources') s WHERE encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')=passage_->>'source_ref';
  SELECT * INTO STRICT v FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
  layers:=config_->'_primary_layers'->(v.id::text);
  IF NOT inputs->'dependencies' ? (selection_->'frame'->>'contribution_id') THEN
   RAISE EXCEPTION 'clause focus missing declared retained dependency' USING ERRCODE='23514'; END IF;
  retained:=ops.resolve_retained_source_contribution(selection_->'frame');
  SELECT r INTO STRICT frame_ FROM jsonb_array_elements(retained->'contributions') r WHERE r->>'contribution_id'=selection_->'frame'->>'contribution_id';
  IF frame_->'component'->>'kind' IS DISTINCT FROM 'predicate_frame' OR frame_->'component'->>'focus_state' IS DISTINCT FROM 'exact'
   OR frame_->'component'->>'scope' IS DISTINCT FROM passage_->>'passage_id'
   OR frame_->'component'->>'effective_version' IS DISTINCT FROM passage_->>'effective_version'
   OR frame_->'pin'->>'source_view_id' IS DISTINCT FROM source_->>'source_view_id'
   OR frame_->'pin'->>'projection_digest' IS DISTINCT FROM source_->>'projection_digest' THEN
   RAISE EXCEPTION 'clause focus differs from exact retained frame and source' USING ERRCODE='23514'; END IF;
  SELECT m->'extents' INTO STRICT focus_ FROM jsonb_array_elements(frame_->'component'->'frame_members') m WHERE m->>'role'='focus';
  IF jsonb_array_length(focus_)<>1 THEN RAISE EXCEPTION 'clause focus is not contiguous' USING ERRCODE='23514'; END IF;
  lo:=(focus_->0->>'start')::integer; hi:=(focus_->0->>'end')::integer;
  IF NOT (lo>=(passage_->>'start')::integer AND hi>lo AND hi<=(passage_->>'end')::integer)
   OR reading_->'focus' IS DISTINCT FROM jsonb_build_object('passage_id',passage_->>'passage_id','start',lo,'end',hi,'text',substring(v.projection->>'text' FROM lo+1 FOR hi-lo)) THEN
   RAISE EXCEPTION 'clause focus differs from original text extent' USING ERRCODE='23514'; END IF;
  before_:=nullif(reading_->'preceding','null'); after_:=nullif(reading_->'following','null');
  IF config_->>'context_policy'='adjacent_sentences' THEN
   expected_:=ops.primary_structural_sentence_context(layers,reading_->'focus',passage_,v);
   IF jsonb_build_object('preceding',before_,'following',after_) IS DISTINCT FROM expected_ THEN
    RAISE EXCEPTION 'clause context differs from exact retained sentence adjacency' USING ERRCODE='23514'; END IF;
  END IF;
  IF config_->>'context_policy'='exact_focus' AND (before_ IS NOT NULL OR after_ IS NOT NULL) THEN
   RAISE EXCEPTION 'exact clause focus cannot claim adjacent context' USING ERRCODE='23514'; END IF;
  FOR expected_ IN SELECT before_ WHERE before_ IS NOT NULL UNION ALL SELECT after_ WHERE after_ IS NOT NULL LOOP
   IF expected_->>'passage_id' IS DISTINCT FROM passage_->>'passage_id'
    OR (expected_->>'start')::bigint<(passage_->>'start')::bigint OR (expected_->>'end')::bigint>(passage_->>'end')::bigint
    OR expected_->>'text' IS DISTINCT FROM substring(v.projection->>'text' FROM (expected_->>'start')::integer+1 FOR (expected_->>'end')::integer-(expected_->>'start')::integer) THEN
    RAISE EXCEPTION 'clause adjacent context differs from selected source' USING ERRCODE='23514'; END IF;
  END LOOP;
  examined:=jsonb_build_array(coalesce(before_->'start',to_jsonb(lo)),coalesce(after_->'end',to_jsonb(hi)));
  IF jsonb_array_length(coalesce(reading_->'primary_context','[]'))<>0 THEN
   RAISE EXCEPTION 'clause presentation has no selected primary context projection' USING ERRCODE='23514'; END IF;
  IF jsonb_array_length(coalesce(reading_->'primary_functions','[]'))=0 THEN
   IF reading_->>'disposition' IS DISTINCT FROM 'failed' OR coalesce(reading_->'function','[]')<>'[]'
    OR coalesce(reading_->'presentation','[]')<>'[]' OR nullif(reading_->'envelope','null') IS NOT NULL
    OR reading_->>'context_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(jsonb_build_array(config_->>'context_policy',selection_,examined)),'UTF8')),'hex') THEN
    RAISE EXCEPTION 'missing primary function cannot produce clause labels' USING ERRCODE='23514'; END IF;
   CONTINUE;
  END IF;
  IF jsonb_array_length(reading_->'primary_functions')<>1 THEN RAISE EXCEPTION 'clause function requires one exact primary question' USING ERRCODE='23514'; END IF;
  ref:=reading_->'primary_functions'->0; node:=ops.primary_characterization_node(layers,ref); answer:=node->'model_answer';
  IF node->>'kind' IS DISTINCT FROM 'model.question' OR answer->>'question_key' IS DISTINCT FROM 'functions'
   OR NOT coalesce(answer->>'family' IN ('character_gliner_function_v1','character_function_v1'),false)
   OR NOT ops.primary_characterization_choices(layers,ref,node,'[]') THEN
   RAISE EXCEPTION 'clause labels lack an exact compatible primary function question' USING ERRCODE='23514'; END IF;
  SELECT convert_from(body,'UTF8')::jsonb INTO STRICT declaration FROM sem.registry_row
   WHERE release_id=config_->>'_release' AND kind='interpretation_question_family' AND name=answer->>'family';
  IF answer->>'declaration_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(declaration),'UTF8')),'hex') THEN
   RAISE EXCEPTION 'clause function differs from its released question declaration' USING ERRCODE='23514'; END IF;
  extents:=ops.primary_characterization_extents(layers,ref,node,v);
  IF jsonb_array_length(extents)<>1 OR extents->0->>'synthetic' IS DISTINCT FROM 'false' OR extents->0->>'text' IS DISTINCT FROM reading_->'focus'->>'text' OR extents->0->'start' IS DISTINCT FROM to_jsonb(lo) OR extents->0->'end' IS DISTINCT FROM to_jsonb(hi) THEN
   RAISE EXCEPTION 'primary function does not describe the exact clause focus' USING ERRCODE='23514'; END IF;
  native_:=data.record_source_json(answer->'native_answer'); request_:=native_->'request';
  wanted_pin:=jsonb_build_object('source',v.key,'source_view_id',v.id,'native_product_task_id',v.native_task_id,'product_key',v.native_product_key,'product_digest',v.native_content_digest,'projection_digest',v.projection_digest,'recipe_digest',v.recipe_digest);
  IF answer->>'answer_kind'='gliner_classification' THEN
   scope_:=request_->'assessed_scope';
   IF examined IS DISTINCT FROM jsonb_build_array(lo,hi) OR request_->>'declaration_digest' IS DISTINCT FROM answer->>'declaration_digest'
    OR request_->'item'->>'text' IS DISTINCT FROM reading_->'focus'->>'text' THEN RAISE EXCEPTION 'primary classifier differs from exact focus input' USING ERRCODE='23514'; END IF;
  ELSIF answer->>'answer_kind'='choice' THEN
   scope_:=request_->'interpretation'->'assessed_scope';
   IF request_->'interpretation'->>'declaration_digest' IS DISTINCT FROM answer->>'declaration_digest'
    OR scope_->'focal_extent' IS DISTINCT FROM jsonb_build_array(lo,hi)
    OR request_->'state'->>'source' IS DISTINCT FROM substring(v.projection->>'text' FROM (examined->>0)::integer+1 FOR (examined->>1)::integer-(examined->>0)::integer)
    OR request_->'state'->'focal' IS DISTINCT FROM jsonb_build_object('start',lo-(examined->>0)::integer,'end',hi-(examined->>0)::integer) THEN
    RAISE EXCEPTION 'primary function context differs from selected focal source' USING ERRCODE='23514'; END IF;
  ELSE RAISE EXCEPTION 'unsupported primary clause function answer kind' USING ERRCODE='23514'; END IF;
  IF scope_->'pin' IS DISTINCT FROM wanted_pin OR scope_->'projection_extent' IS DISTINCT FROM examined
   OR reading_->>'context_digest' IS DISTINCT FROM answer->>'request_digest' OR reading_->>'envelope' IS DISTINCT FROM answer->>'request_digest' THEN
   RAISE EXCEPTION 'clause request provenance differs from retained primary input' USING ERRCODE='23514'; END IF;
  labels_:='[]'; observed:=coalesce(answer->'observed_keys','[]'); selected_:=coalesce(answer->'selected_keys','[]'); keys_:='[]';
  FOR offered IN SELECT value FROM jsonb_array_elements(observed) LOOP
   SELECT a INTO STRICT expected_ FROM jsonb_array_elements(answer->'alternatives') a WHERE a->'key'=offered;
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(declaration->'questions') q CROSS JOIN LATERAL jsonb_array_elements(q->'options') option_
    WHERE q->>'key'='functions' AND option_->'key'=offered) THEN
    RAISE EXCEPTION 'clause function label is outside its released vocabulary' USING ERRCODE='23514'; END IF;
   labels_:=labels_||jsonb_build_array(jsonb_build_object('label',offered,'score',CASE WHEN expected_ ? 'score' THEN data.record_source_json(expected_->'score'->'value') ELSE NULL END,'accepted',selected_ @> jsonb_build_array(offered)));
   keys_:=keys_||jsonb_build_array(offered);
  END LOOP;
  disposition_:=CASE WHEN jsonb_array_length(selected_)>0 THEN 'observed' WHEN answer->>'state' IN ('policy_withheld','unresolved','proposed') THEN 'withheld' ELSE 'failed' END;
  IF (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(observed)) OR NOT observed @> selected_
   OR reading_->'function' IS DISTINCT FROM labels_ OR coalesce(reading_->'presentation','[]')<>'[]'
   OR reading_->>'disposition' IS DISTINCT FROM disposition_ THEN
   RAISE EXCEPTION 'clause labels or withholding differ from retained primary answers' USING ERRCODE='23514'; END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.validate_clause_classification(jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

-- Named matches and predication/cue relations are authored upstream. This boundary
-- binds their exact retained nodes, source membership and choice requirements only.
CREATE OR REPLACE FUNCTION ops.validate_definition_basis(
 component jsonb,passage jsonb,source_ jsonb,config_ jsonb,policy jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE proof jsonb:=component->'witness'; basis text:=component->>'basis'; layers jsonb; primary_ jsonb; match_ jsonb;
 view_ kb.source_view; rule_ jsonb; body jsonb; detail jsonb; token jsonb; ref jsonb; part jsonb; binding jsonb; span_ jsonb;
 term_role text; cue_role text; cue_binding jsonb; content_binding jsonb; content_refs jsonb; content_span jsonb;
 scope_refs jsonb; scope_node jsonb; child jsonb; frame_ref jsonb; frame_node jsonb; predicate jsonb;
 expected_scope jsonb:='[]'; frames jsonb:='[]'; act_count integer:=0; act_ boolean; content_ boolean;
 entry record; relation_ jsonb; cue_ jsonb; cue_ref jsonb; cue_span jsonb; basis_node jsonb; covered jsonb;
 display_piece jsonb; cue_span_ jsonb; label_ jsonb;
BEGIN
 IF basis='model_reading' THEN
  IF nullif(proof,'null'::jsonb) IS NOT NULL THEN RAISE EXCEPTION 'model definition cannot claim a named annotation witness' USING ERRCODE='23514'; END IF;
  RETURN;
 ELSIF basis='unqualified' THEN
  IF component->>'interpretation' IS DISTINCT FROM 'unresolved' OR nullif(proof,'null'::jsonb) IS NOT NULL THEN
   RAISE EXCEPTION 'unqualified definition candidate claims unsupported interpretation' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 IF NOT coalesce(basis IN ('matched_cue','native_geometry'),false) OR proof->'primary_match' IS NULL
  OR jsonb_array_length(coalesce(proof->'primary_scope','[]'))=0 OR source_ IS NULL
  OR component->'term'->>'passage_id' IS DISTINCT FROM component->'content'->>'passage_id'
  OR config_->'use_named_candidates' IS DISTINCT FROM 'true'::jsonb THEN
  RAISE EXCEPTION 'definition basis lacks exact retained primary witness' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
 layers:=config_->'_primary_layers'->(view_.id::text);
 -- Keep the original cut/task witness: the adapter must have selected this primary match.
 SELECT result.body INTO STRICT body FROM ops.cut_task member JOIN ops.task task ON task.id=member.task_id
 JOIN ops.task origin ON origin.id=member.origin_task_id JOIN ops.task_result result ON result.task_id=origin.id AND result.release_id=origin.release_id
 JOIN ops.method_config cfg ON cfg.id=origin.method_config_id JOIN ops.method method ON method.id=cfg.method_id
 WHERE member.cut_id=(source_->>'cut_id')::bigint AND task.run_id=(source_->>'run_id')::bigint
  AND task.unit_type='source_view' AND task.unit_id=view_.id AND task.status IN ('done','reused')
  AND origin.id=coalesce(task.reused_task_id,task.id) AND origin.id=(proof->>'annotation_task_id')::bigint
  AND origin.release_id=source_->>'release_id' AND method.name='extract.m1_annotations' AND method.version='3'
  AND result.body->>'source'=view_.key AND result.body->>'input_hash'=origin.input_hash AND result.body->>'configuration_hash'=cfg.config_hash;
 detail:=data.record_source_json(body->'parse_detail');
 IF detail->>'recipe' IS DISTINCT FROM 'm1-owned-linguistic-product-1'
  OR NOT coalesce(detail->'characterization_layers','[]') @> jsonb_build_array(proof->'primary_match'->'layer') THEN
  RAISE EXCEPTION 'definition annotation adapter selected different primary evidence' USING ERRCODE='23514'; END IF;
 primary_:=ops.primary_characterization_node(layers,proof->'primary_match'); match_:=primary_->'named_match';
 SELECT r INTO STRICT rule_ FROM jsonb_array_elements(config_->'annotation_rules') r WHERE r->>'rule'=proof->>'rule' AND r->>'variant'=proof->>'variant';
 IF primary_->>'kind' IS DISTINCT FROM 'construction.named_binding' OR NOT coalesce(match_->>'status' IN ('matched','partial'),false)
  OR primary_->>'rule_id' IS DISTINCT FROM 'named-rule:'||encode(sha256(convert_to(data.canonical_json(rule_),'UTF8')),'hex')
  OR policy->'definition_witness'->'rules'->>((rule_->>'rule')||'/'||(rule_->>'variant')) IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(rule_),'UTF8')),'hex')
  OR config_->>'term_role' IS DISTINCT FROM policy#>>'{definition_witness,term_role}' OR config_->>'content_role' IS DISTINCT FROM policy#>>'{definition_witness,content_role}'
  OR match_->>'dependency_digest' IS DISTINCT FROM proof->>'dependency_digest' OR match_->>'rule' IS DISTINCT FROM proof->>'rule'
  OR match_->>'variant' IS DISTINCT FROM proof->>'variant' OR match_->>'mechanism' IS DISTINCT FROM rule_->>'mechanism'
  OR match_->'native_container'->>'local_id' IS DISTINCT FROM 'spacy/'||view_.id::text||'/'||(proof->>'block_id')||'/block'
  OR jsonb_array_length(match_->'nodes') IS DISTINCT FROM jsonb_array_length(proof->'nodes')
  OR EXISTS(SELECT FROM jsonb_array_elements(match_->'nodes') WITH ORDINALITY n(ref,i)
   WHERE ops.primary_characterization_node(layers,n.ref)->'native_token'->'index' IS DISTINCT FROM proof->'nodes'->((i-1)::integer)) THEN
  RAISE EXCEPTION 'definition cue differs from exact released primary match' USING ERRCODE='23514'; END IF;
 FOR ref IN SELECT value FROM jsonb_array_elements(match_->'nodes') LOOP
  token:=ops.primary_characterization_node(layers,ref); span_:=ops.primary_structural_token_span(layers,jsonb_build_array(ref),view_);
  IF ref->'layer' IS DISTINCT FROM match_->'native_container'->'layer' OR token->'native_token'->>'container' IS DISTINCT FROM match_->'native_container'->>'local_id'
   OR (span_->>0)::bigint<(passage->>'start')::bigint OR (span_->>1)::bigint>(passage->>'end')::bigint THEN
   RAISE EXCEPTION 'definition match node is outside its exact native passage/container' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR ref IN SELECT token_ FROM jsonb_array_elements(match_->'bindings') b CROSS JOIN LATERAL jsonb_array_elements(coalesce(b->'members','[]')||jsonb_build_array(b->'head')) token_ LOOP
  token:=ops.primary_characterization_node(layers,ref);
  IF ref->'layer' IS DISTINCT FROM match_->'native_container'->'layer' OR token->'native_token'->>'container' IS DISTINCT FROM match_->'native_container'->>'local_id' THEN
   RAISE EXCEPTION 'definition named role has a foreign native token endpoint' USING ERRCODE='23514'; END IF;
 END LOOP;
 scope_refs:=proof->'primary_scope'||jsonb_build_array(proof->'primary_match');
 FOR ref IN SELECT value FROM jsonb_array_elements(scope_refs) LOOP
  token:=ops.primary_characterization_node(layers,ref);
  IF NOT ops.primary_characterization_choices(layers,ref,token,'[]') THEN RAISE EXCEPTION 'definition witness loses required primary choices' USING ERRCODE='23514'; END IF;
 END LOOP;
 term_role:=CASE WHEN rule_->'bindings' ? 'definition_label_required' THEN 'nominal_subject' ELSE config_->>'term_role' END;
 cue_role:=CASE WHEN rule_->'bindings' ? 'definition_label_required' THEN 'copular_cue' ELSE 'defining_cue' END;
 SELECT b INTO STRICT binding FROM jsonb_array_elements(match_->'bindings') b WHERE b->>'role'=term_role AND b->>'status'='complete';
 span_:=ops.primary_structural_token_span(layers,binding->'members',view_);
 IF span_ IS DISTINCT FROM jsonb_build_array(component->'term'->'start',component->'term'->'end')
  OR component->>'interpretation' IS DISTINCT FROM (CASE WHEN rule_->>'rule' IN ('naming','explanation') THEN 'explanation' ELSE 'definition' END) THEN
  RAISE EXCEPTION 'definition term or interpretation differs from retained named role' USING ERRCODE='23514'; END IF;
 SELECT b INTO STRICT cue_binding FROM jsonb_array_elements(match_->'bindings') b WHERE b->>'role'=cue_role AND b->>'status'='complete';
 cue_span_:=ops.primary_structural_token_span(layers,cue_binding->'members',view_);
 SELECT b INTO content_binding FROM jsonb_array_elements(match_->'bindings') b WHERE b->>'role'=config_->>'content_role' AND b->>'status'='complete';
 content_refs:=coalesce(content_binding->'members','[]');
 FOR binding IN SELECT value FROM jsonb_array_elements(match_->'bindings') WHERE value->>'role' IN ('definition_scope_guard','defining_content_predicate') LOOP
  content_refs:=content_refs||CASE WHEN binding->>'role'='defining_content_predicate' THEN jsonb_build_array(binding->'head') ELSE coalesce(binding->'members','[]') END;
 END LOOP;
 content_span:=jsonb_build_array(component->'content'->'start',component->'content'->'end');
 IF basis='matched_cue' AND (content_binding IS NULL OR ops.primary_structural_token_span(layers,content_binding->'members',view_) IS DISTINCT FROM content_span
  OR coalesce((content_binding->>'demonstrative')::boolean,false) OR nullif(proof->'label_nodes','null') IS NOT NULL) THEN
  RAISE EXCEPTION 'definition content differs from exact retained named role' USING ERRCODE='23514'; END IF;
 -- Collect actual act/content predications from retained native-token relationships.
 FOR entry IN SELECT * FROM jsonb_each(layers) LOOP
  FOR frame_node IN SELECT value FROM jsonb_array_elements(entry.value->'terms') WHERE value->>'kind'='predicate' AND value->>'vocabulary'='source-linguistic-rules-1' LOOP
   frame_ref:=jsonb_build_object('layer',entry.key::jsonb,'local_id',frame_node->>'local_id');
   predicate:=ops.primary_characterization_child(layers,frame_ref,frame_node,'predicate');
   act_:=coalesce(predicate->'external_premises','[]') @> jsonb_build_array(cue_binding->'head');
   content_:=EXISTS(SELECT FROM jsonb_array_elements(content_refs) r WHERE coalesce(predicate->'external_premises','[]') @> jsonb_build_array(r));
   IF NOT act_ AND NOT content_ THEN CONTINUE; END IF;
   IF frame_node->>'status' IS DISTINCT FROM 'interpreted' OR NOT EXISTS(SELECT FROM jsonb_array_elements(entry.value->'coverage') c
    WHERE c->>'family'='construction.source_readings' AND c->>'availability'='available' AND c->>'outcome' IN ('complete','empty')
     AND NOT EXISTS(SELECT FROM jsonb_array_elements(ops.primary_characterization_extents(layers,frame_ref,frame_node,view_)) e WHERE NOT EXISTS(
      SELECT FROM jsonb_array_elements(c->'examined') selector WHERE selector->>'projection'=view_.projection_digest
       AND coalesce((selector->>'start')::bigint,0)<=(e->>'start')::bigint AND coalesce((selector->>'end')::bigint,char_length(view_.projection->>'text'))>=(e->>'end')::bigint))) THEN
    RAISE EXCEPTION 'definition primary predicate scope is incomplete' USING ERRCODE='23514'; END IF;
   IF act_ THEN
    act_count:=act_count+1; child:=ops.primary_characterization_child(layers,frame_ref,frame_node,'polarity');
    IF child->>'value' IS DISTINCT FROM 'positive' THEN RAISE EXCEPTION 'definition act is not a positive primary predication' USING ERRCODE='23514'; END IF;
   END IF;
   expected_scope:=expected_scope||jsonb_build_array(frame_ref); frames:=frames||jsonb_build_array(jsonb_build_object('reference',frame_ref,'act',act_));
  END LOOP;
 END LOOP;
 IF act_count<>1 THEN RAISE EXCEPTION 'definition lacks one exact primary act predicate' USING ERRCODE='23514'; END IF;
 FOR part IN SELECT value FROM jsonb_array_elements(frames) LOOP
  frame_ref:=part->'reference'; body:=layers->data.canonical_json(frame_ref->'layer');
  FOR relation_ IN SELECT value FROM jsonb_array_elements(body->'roles') WHERE value->>'role'='host' AND value->>'member'=frame_ref->>'local_id' LOOP
   cue_ref:=jsonb_build_object('layer',frame_ref->'layer','local_id',relation_->>'owner'); cue_:=ops.primary_characterization_node(layers,cue_ref);
   basis_node:=ops.primary_characterization_child(layers,cue_ref,cue_,'basis');
   cue_span:=ops.primary_characterization_extents(layers,cue_ref,cue_,view_);
   IF cue_->>'status' IS DISTINCT FROM 'interpreted' OR part->'act'='true'::jsonb OR NOT coalesce(cue_->>'value' IN ('condition','negation','quotation'),false)
    OR EXISTS(SELECT FROM jsonb_array_elements(cue_span) e WHERE e->>'synthetic' IS DISTINCT FROM 'false' OR (e->>'start')::bigint<(content_span->>0)::bigint OR (e->>'end')::bigint>(content_span->>1)::bigint) THEN
    RAISE EXCEPTION 'definition primary scope retains an uncarried qualification' USING ERRCODE='23514'; END IF;
   expected_scope:=expected_scope||jsonb_build_array(cue_ref,jsonb_build_object('layer',cue_ref->'layer','local_id',basis_node->>'local_id'));
  END LOOP;
 END LOOP;
 -- Unhosted primary cues retain unknown/qualified standing; they cannot disappear
 -- merely because the selected witness left their role relation out of its citation list.
 FOR entry IN SELECT * FROM jsonb_each(layers) LOOP
  FOR cue_ IN SELECT value FROM jsonb_array_elements(entry.value->'terms') WHERE value->>'kind'='operator' AND value->>'vocabulary'='source-linguistic-rules-1'
   AND EXISTS(SELECT FROM jsonb_array_elements(value->'children') e WHERE e->>'role'='cue') LOOP
   IF EXISTS(SELECT FROM jsonb_array_elements(entry.value->'roles') r WHERE r->>'role'='host' AND r->>'owner'=cue_->>'local_id') THEN CONTINUE; END IF;
   cue_ref:=jsonb_build_object('layer',entry.key::jsonb,'local_id',cue_->>'local_id'); basis_node:=ops.primary_characterization_child(layers,cue_ref,cue_,'basis');
   content_:=jsonb_array_length(coalesce(basis_node->'external_premises','[]'))>0 AND content_refs @> basis_node->'external_premises';
   IF EXISTS(SELECT FROM jsonb_array_elements(cue_->'children') e WHERE e->>'role'='origin') THEN
    child:=ops.primary_characterization_child(layers,cue_ref,cue_,'origin');
    IF coalesce(child->'external_premises','[]') @> jsonb_build_array(cue_binding->'head') THEN
     RAISE EXCEPTION 'definition act has an unresolved retained primary cue' USING ERRCODE='23514'; END IF;
   END IF;
   IF NOT content_ THEN CONTINUE; END IF;
   cue_span:=ops.primary_characterization_extents(layers,cue_ref,cue_,view_);
   IF cue_->>'status' IS DISTINCT FROM 'interpreted' OR NOT coalesce(cue_->>'value' IN ('condition','negation','quotation'),false)
    OR EXISTS(SELECT FROM jsonb_array_elements(cue_span) e WHERE e->>'synthetic' IS DISTINCT FROM 'false' OR (e->>'start')::bigint<(content_span->>0)::bigint OR (e->>'end')::bigint>(content_span->>1)::bigint) THEN
    RAISE EXCEPTION 'definition content has an uncarried retained primary qualification' USING ERRCODE='23514'; END IF;
   expected_scope:=expected_scope||jsonb_build_array(cue_ref,jsonb_build_object('layer',cue_ref->'layer','local_id',basis_node->>'local_id'));
  END LOOP;
 END LOOP;
 IF NOT proof->'primary_scope' @> expected_scope THEN RAISE EXCEPTION 'definition witness omits retained predicate or cue scope' USING ERRCODE='23514'; END IF;
 IF basis='native_geometry' THEN
  IF rule_->'bindings' ? 'definition_label_required' AND (proof->'label_nodes' IS NULL OR NOT EXISTS(
   SELECT FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'annotations') a
   WHERE a->>'kind'='construction.named_binding' AND a->'named_match'->'native_container'=match_->'native_container' AND EXISTS(SELECT FROM jsonb_array_elements(a->'named_match'->'bindings') b WHERE b->>'role'='definition_label' AND b->>'status'='complete')
    AND (SELECT jsonb_agg(ops.primary_characterization_node(layers,r)->'native_token'->'index' ORDER BY i) FROM jsonb_array_elements(a->'named_match'->'nodes') WITH ORDINALITY n(r,i))=proof->'label_nodes')) THEN
   RAISE EXCEPTION 'definition display lacks an exact retained primary numbered label' USING ERRCODE='23514'; END IF;
  IF NOT rule_->'bindings' ? 'definition_label_required' THEN
   SELECT b INTO STRICT binding FROM jsonb_array_elements(match_->'bindings') b WHERE b->>'role'='following_content_cue' AND b->>'status'='complete';
   cue_span_:=ops.primary_structural_token_span(layers,binding->'members',view_);
  END IF;
  SELECT piece INTO STRICT display_piece FROM jsonb_array_elements(view_.projection->'pieces') piece WHERE piece->>'kind'='native_text' AND piece->'start'=content_span->0 AND piece->'end'=content_span->1
   AND EXISTS(SELECT FROM ops.read_pdf_published_items(view_.native_task_id,view_.native_product_key,view_.native_content_digest,ARRAY[piece->>'item_ref']) item WHERE item.native_json->>'label'='formula' AND item.native_json->>'content_layer'='body');
  IF (cue_span_->>1)::bigint>(content_span->>0)::bigint OR substring(view_.projection->>'text' FROM (cue_span_->>1)::integer+1 FOR (content_span->>0)::integer-(cue_span_->>1)::integer) !~ '^[:[:space:]]*$' THEN
   RAISE EXCEPTION 'definition display differs from exact adjacent source geometry' USING ERRCODE='23514'; END IF;
 END IF;
EXCEPTION WHEN no_data_found OR too_many_rows OR invalid_text_representation OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'definition basis cannot resolve exact retained primary source support' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_definition_basis(jsonb,jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_declaration_fact_value(p_layers jsonb,p_ref jsonb,p_node jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE edge jsonb; child jsonb; result jsonb; n integer:=0; array_ boolean;
BEGIN
 IF p_node->>'family' IS DISTINCT FROM 'construction.declaration_syntax'
  OR p_node->>'vocabulary' IS DISTINCT FROM 'source-linguistic-rules-1'
  OR p_node->>'status' IS DISTINCT FROM 'interpreted'
  OR NOT ops.primary_characterization_choices(p_layers,p_ref,p_node,'[]') THEN
  RAISE EXCEPTION 'declaration fact is not a resolved primary source reading' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(coalesce(p_node->'children','[]'))=0 THEN
  RETURN (p_node->>'value')::jsonb;
 END IF;
 array_:=p_node->>'value'='[]'; result:=CASE WHEN array_ THEN '[]'::jsonb ELSE '{}'::jsonb END;
 FOR edge IN SELECT value FROM jsonb_array_elements(p_node->'children') ORDER BY (value->>'order')::integer NULLS FIRST LOOP
  IF edge->>'structural' IS DISTINCT FROM 'true' OR NOT edge ? 'target' OR edge ? 'choice_group'
   OR (array_ AND (edge->>'role'<>'item' OR (edge->>'order')::integer<>n))
   OR (NOT array_ AND result ? (edge->>'role')) THEN
   RAISE EXCEPTION 'declaration fact loses its exact structural children' USING ERRCODE='23514'; END IF;
  child:=ops.primary_characterization_node(p_layers,jsonb_build_object('layer',p_ref->'layer','local_id',edge->>'target'));
  child:=ops.primary_declaration_fact_value(p_layers,p_ref,child);
  result:=CASE WHEN array_ THEN result||jsonb_build_array(child) ELSE result||jsonb_build_object(edge->>'role',child) END;
  n:=n+1;
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION ops.primary_declaration_fact_value(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_declaration_role_members(p_layers jsonb,p_sentence jsonb,p_frame text,p_role text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE premise jsonb; group_ jsonb; body jsonb; role_ jsonb; member_ jsonb; token_ jsonb; indices jsonb:='[]'; found_ integer:=0;
BEGIN
 FOR premise IN SELECT value FROM jsonb_array_elements(p_sentence->'external_premises') LOOP
  IF 'annotation:'||encode(sha256(convert_to(data.canonical_json(premise),'UTF8')),'hex')<>p_frame THEN CONTINUE; END IF;
  group_:=ops.primary_characterization_node(p_layers,premise);
  IF group_->>'kind' IS DISTINCT FROM 'native.srl_group' THEN RAISE EXCEPTION 'declaration frame is not retained native SRL' USING ERRCODE='23514'; END IF;
  found_:=found_+1; body:=p_layers->data.canonical_json(premise->'layer');
  FOR role_ IN SELECT a FROM jsonb_array_elements(body->'annotations') a WHERE a->>'kind'='native.srl_role'
   AND a->>'native_label'=p_role AND EXISTS(SELECT FROM jsonb_array_elements(body->'memberships') m
    WHERE m->>'group'=group_->>'local_id' AND m->>'member'=a->>'local_id' AND m->>'role'=p_role) LOOP
   FOR member_ IN SELECT value FROM jsonb_array_elements(body->'memberships')
    WHERE value->>'group'=role_->>'local_id' AND value->>'role'='token' ORDER BY (value->>'order')::integer LOOP
    token_:=ops.primary_characterization_node(p_layers,jsonb_build_object('layer',premise->'layer','local_id',member_->>'member'));
    IF NOT p_sentence->'external_premises' @> jsonb_build_array(jsonb_build_object('layer',premise->'layer','local_id',member_->>'member'))
     OR token_->>'kind' IS DISTINCT FROM 'native.token' THEN RAISE EXCEPTION 'declaration SRL member is outside exact sentence support' USING ERRCODE='23514'; END IF;
    indices:=indices||jsonb_build_array(token_->'native_token'->'index');
   END LOOP;
  END LOOP;
 END LOOP;
 IF found_<>1 THEN RAISE EXCEPTION 'declaration native SRL frame is missing or ambiguous' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_agg(i ORDER BY (i #>> '{}')::integer),'[]') INTO indices FROM jsonb_array_elements(indices) i;
 RETURN indices;
END $$;
REVOKE ALL ON FUNCTION ops.primary_declaration_role_members(jsonb,jsonb,text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_primary_declaration_component(
 component jsonb,p_passage jsonb,p_source jsonb,p_config jsonb,p_release text)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE proof jsonb:=component->'declaration_chain'; layers jsonb; v kb.source_view; refs jsonb; ref jsonb;
 node jsonb; extents jsonb; body jsonb; premise jsonb; support jsonb; support_body jsonb; annotation jsonb;
 data_ jsonb; words_ jsonb; positions_ jsonb; rows_ jsonb:='[]'; row_ jsonb; native_pin jsonb; tokens_ jsonb; source_node jsonb; role_indices jsonb;
 first_ jsonb; construction jsonb; naming jsonb; intro jsonb; constructed jsonb; named jsonb;
 binding jsonb; intro_ jsonb; found_ integer; i integer; lo bigint; hi bigint; last_end bigint; label_span jsonb;
BEGIN
 IF component->>'basis' IS DISTINCT FROM 'declaration_chain' OR component->>'interpretation' IS DISTINCT FROM 'definition'
  OR nullif(component->'witness','null') IS NOT NULL OR nullif(proof->'parser','null') IS NOT NULL
  OR proof->>'version' IS DISTINCT FROM 'definition-declaration-chain-2' OR NOT ops.private_declaration_enabled(p_release)
  OR component->'evidence' IS DISTINCT FROM jsonb_build_array(p_passage->>'passage_id') OR component->'alternatives' IS DISTINCT FROM '[]'
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_config->'selections') s WHERE s->>'passage_id'=p_passage->>'passage_id' AND nullif(s->'parser','null') IS NULL) THEN
  RAISE EXCEPTION 'declaration differs from exact current primary source selection' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=(p_source->>'source_view_id')::bigint;
 layers:=p_config->'_primary_layers'->(v.id::text); refs:=proof->'primary_evidence';
 native_pin:=jsonb_build_object('source',v.key,'source_view_id',v.id,'native_product_task_id',v.native_task_id,'product_key',v.native_product_key,'product_digest',v.native_content_digest,'projection_digest',v.projection_digest,'recipe_digest',v.recipe_digest);
 IF proof->>'scope_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(jsonb_build_object('source',native_pin,'passage',jsonb_build_array(p_passage->'start',p_passage->'end'),'policy','primary-declaration-roles-1')),'UTF8')),'hex')
  OR jsonb_typeof(refs) IS DISTINCT FROM 'array' OR jsonb_array_length(refs)<>3
  OR (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(refs)) THEN
  RAISE EXCEPTION 'declaration requires three distinct exact primary sentence witnesses' USING ERRCODE='23514'; END IF;
 FOR ref IN SELECT value FROM jsonb_array_elements(refs) LOOP
  node:=ops.primary_characterization_node(layers,ref); body:=layers->data.canonical_json(ref->'layer');
  extents:=ops.primary_characterization_extents(layers,ref,node,v);
  IF node->>'value' IS DISTINCT FROM 'declaration_sentence' OR node->>'kind' IS DISTINCT FROM 'operator'
   OR body->'operation'->>'key' IS DISTINCT FROM 'text.constructions'
   OR jsonb_array_length(extents)=0 OR EXISTS(SELECT FROM jsonb_array_elements(extents) e WHERE e->>'synthetic' IS DISTINCT FROM 'false'
      OR (e->>'start')::bigint<(p_passage->>'start')::bigint OR (e->>'end')::bigint>(p_passage->>'end')::bigint)
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(body->'coverage') c WHERE c->>'family'='construction.declaration_syntax'
     AND c->>'availability'='available' AND c->>'outcome' IN ('complete','empty','partial')
     AND EXISTS(SELECT FROM jsonb_array_elements(c->'examined') e WHERE e->>'projection'=v.projection_digest
       AND (e->>'start')::bigint<=(extents->0->>'start')::bigint
       AND (e->>'end')::bigint>=(extents->(jsonb_array_length(extents)-1)->>'end')::bigint)
     AND NOT EXISTS(SELECT FROM jsonb_array_elements(c->'unexamined') e WHERE e->>'projection'=v.projection_digest
       AND (e->>'start')::bigint<(extents->(jsonb_array_length(extents)-1)->>'end')::bigint
       AND (e->>'end')::bigint>(extents->0->>'start')::bigint)) THEN
   RAISE EXCEPTION 'declaration requires complete located primary sentence characterization' USING ERRCODE='23514'; END IF;
  SELECT value INTO STRICT annotation FROM jsonb_array_elements(body->'annotations') a
   WHERE node->'premises' ? (a->>'local_id') AND a->>'rule_id'='tc.source.declaration_syntax.v1'
    AND a->>'native_scheme'='retained-hanlp-declaration-syntax-1' AND a->>'status'='interpreted';
  IF annotation->'external_premises' IS DISTINCT FROM node->'external_premises'
   OR annotation->'occurrences' IS DISTINCT FROM node->'occurrences'
   OR jsonb_array_length(coalesce(node->'external_premises','[]'))=0 THEN
   RAISE EXCEPTION 'declaration syntax lacks exact native witness closure' USING ERRCODE='23514'; END IF;
  data_:=ops.primary_declaration_fact_value(layers,ref,node); words_:=data_->'words'; positions_:=data_->'positions';
  IF jsonb_typeof(words_) IS DISTINCT FROM 'array' OR jsonb_array_length(words_)=0
   OR jsonb_array_length(words_) IS DISTINCT FROM jsonb_array_length(positions_) THEN
   RAISE EXCEPTION 'declaration sentence word/position population differs' USING ERRCODE='23514'; END IF;
  tokens_:='[]';
  FOR premise IN SELECT value FROM jsonb_array_elements(node->'external_premises') LOOP
   support:=ops.primary_characterization_node(layers,premise); support_body:=layers->data.canonical_json(premise->'layer');
   PERFORM ops.primary_characterization_extents(layers,premise,support,v);
   IF NOT body->'dependencies' @> jsonb_build_array(premise->'layer')
    OR support->>'kind' NOT IN ('native.token','native.srl_group','native.srl_role') THEN
    RAISE EXCEPTION 'declaration support is not an exact declared native dependency' USING ERRCODE='23514'; END IF;
   IF support->>'kind'='native.token' THEN
    IF support->'native_token'->>'head_index_base' IS DISTINCT FROM '1'
     OR NOT support->'native_token' ?& ARRAY['lemma','tag','dependency','native_head','sentence']
     OR EXISTS(SELECT family FROM unnest(ARRAY['hanlp.tokens','hanlp.lemma','hanlp.pos','hanlp.dependency','hanlp.srl']) family WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(support_body->'coverage') c WHERE c->>'family'=family AND c->>'availability'='available' AND c->>'outcome' IN ('complete','empty','partial')
      AND EXISTS(SELECT FROM jsonb_array_elements(c->'examined') e WHERE e->>'projection'=v.projection_digest
       AND (e->>'start')::bigint<=(extents->0->>'start')::bigint
       AND (e->>'end')::bigint>=(extents->(jsonb_array_length(extents)-1)->>'end')::bigint)
      AND NOT EXISTS(SELECT FROM jsonb_array_elements(c->'unexamined') e WHERE e->>'projection'=v.projection_digest
       AND (e->>'start')::bigint<(extents->(jsonb_array_length(extents)-1)->>'end')::bigint
       AND (e->>'end')::bigint>(extents->0->>'start')::bigint)))
     OR NOT EXISTS(SELECT FROM jsonb_array_elements(support_body->'native_runs') r
        WHERE r->>'local_id'=support->'native_token'->>'native_run' AND r->>'provider'='hanlp') THEN
     RAISE EXCEPTION 'declaration support loses its native role scheme' USING ERRCODE='23514'; END IF;
    tokens_:=tokens_||jsonb_build_array(jsonb_build_object('node',support,'reference',premise));
   END IF;
  END LOOP;
  SELECT jsonb_agg(t ORDER BY (t->'node'->'native_token'->>'index')::integer) INTO tokens_ FROM jsonb_array_elements(tokens_) t;
  IF jsonb_array_length(tokens_) IS DISTINCT FROM jsonb_array_length(words_) THEN
   RAISE EXCEPTION 'declaration syntax lacks complete native token support' USING ERRCODE='23514'; END IF;
  support_body:=layers->data.canonical_json(tokens_->0->'reference'->'layer');
  IF (SELECT count(*) FROM jsonb_array_elements(support_body->'annotations') t WHERE
      t->'native_token'->'native_run'=tokens_->0->'node'->'native_token'->'native_run'
      AND t->'native_token'->'container'=tokens_->0->'node'->'native_token'->'container')<>jsonb_array_length(tokens_) THEN
   RAISE EXCEPTION 'declaration primary sentence omits retained native tokens' USING ERRCODE='23514'; END IF;
  last_end:=-1;
  FOR i IN 0..jsonb_array_length(words_)-1 LOOP
   support:=tokens_->i->'node'; premise:=tokens_->i->'reference';
   lo:=(positions_->i->>0)::bigint; hi:=(positions_->i->>1)::bigint;
   IF support->'native_token'->'index' IS DISTINCT FROM to_jsonb(i)
    OR support->'native_token'->'text' IS DISTINCT FROM words_->i OR lo<last_end OR hi<=lo
    OR words_->>i IS DISTINCT FROM substring(v.projection->>'text' FROM lo::integer+1 FOR (hi-lo)::integer)
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(ops.primary_characterization_extents(layers,premise,support,v)) e
      WHERE e->'start'=to_jsonb(lo) AND e->'end'=to_jsonb(hi) AND e->>'synthetic'='false') THEN
    RAISE EXCEPTION 'declaration fact token differs from its exact native source' USING ERRCODE='23514'; END IF;
   last_end:=hi;
  END LOOP;
  rows_:=rows_||jsonb_build_array(jsonb_build_object('data',data_,'reference',ref,'node',node,'identity','annotation:'||encode(sha256(convert_to(data.canonical_json(ref),'UTF8')),'hex')));
 END LOOP;
 SELECT jsonb_agg(r ORDER BY (r->'data'->'positions'->0->>0)::bigint) INTO rows_ FROM jsonb_array_elements(rows_) r;
 first_:=rows_->0->'data'; construction:=rows_->1->'data'; naming:=rows_->2->'data';
 IF first_->'positions'->0->0 IS DISTINCT FROM p_passage->'start'
  OR naming->'positions'->(jsonb_array_length(naming->'positions')-1)->1 IS DISTINCT FROM p_passage->'end'
  OR proof->'construction_frame' IS DISTINCT FROM rows_->1->'identity' OR proof->'naming_frame' IS DISTINCT FROM rows_->2->'identity'
  OR jsonb_array_length(construction->'facts'->'intros')<>1 THEN
  RAISE EXCEPTION 'declaration chain differs from exact primary sentence ordering' USING ERRCODE='23514'; END IF;
 intro:=construction->'facts'->'intros'->0; named:=naming->'facts'->'naming';
 IF ops.primary_declaration_role_members(layers,rows_->1->'node',intro->>'frame','ARG1') IS DISTINCT FROM jsonb_build_array(intro->'subject') THEN
  RAISE EXCEPTION 'construction subject lacks its exact native SRL witness' USING ERRCODE='23514'; END IF;

 constructed:=construction->'words'->((proof->>'construction_subject_token')::integer);
 IF named='null' OR constructed IS NULL OR intro->'subject' IS DISTINCT FROM proof->'construction_subject_token'
  OR named->'antecedent' IS DISTINCT FROM proof->'naming_antecedent_token'
  OR constructed IS DISTINCT FROM naming->'words'->((named->>'antecedent')::integer)
  OR NOT ops.primary_declaration_role_members(layers,rows_->2->'node',named->>'frame','ARG1') @> jsonb_build_array(named->'antecedent')
  OR jsonb_array_length(proof->'bindings') IS DISTINCT FROM jsonb_array_length(first_->'facts'->'intros') THEN
  RAISE EXCEPTION 'declaration construction/naming binding differs from characterized roles' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*)<>count(DISTINCT value->'subject_token') OR count(*)<>count(DISTINCT value->'use_token') FROM jsonb_array_elements(proof->'bindings')) THEN
  RAISE EXCEPTION 'declaration repeats a subject/use binding' USING ERRCODE='23514'; END IF;
 FOR binding IN SELECT value FROM jsonb_array_elements(proof->'bindings') LOOP
  SELECT count(*),jsonb_agg(f)->0 INTO found_,intro_ FROM jsonb_array_elements(first_->'facts'->'intros') f
   WHERE f->'subject'=binding->'subject_token';
  IF found_<>1 OR ops.primary_declaration_role_members(layers,rows_->0->'node',intro_->>'frame','ARG1') IS DISTINCT FROM jsonb_build_array(binding->'subject_token')
   OR NOT ops.primary_declaration_role_members(layers,rows_->1->'node',intro->>'frame','ARG2') @> jsonb_build_array(binding->'use_token')
   OR binding->'frame' IS DISTINCT FROM rows_->0->'identity'
   OR first_->'words'->((binding->>'subject_token')::integer) IS DISTINCT FROM construction->'words'->((binding->>'use_token')::integer)
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(intro->'relative_uses') u WHERE u @> jsonb_build_array(binding->'use_token')) THEN
   RAISE EXCEPTION 'declaration subject/use binding differs from primary syntax' USING ERRCODE='23514'; END IF;
 END LOOP;
 role_indices:=ops.primary_declaration_role_members(layers,rows_->2->'node',named->>'frame','ARG2');
 IF jsonb_array_length(role_indices)=0 OR (named->>'term_end')::integer<>(role_indices->>(jsonb_array_length(role_indices)-1))::integer+1
  OR (named->>'term_start')::integer NOT BETWEEN (role_indices->>0)::integer AND (role_indices->>0)::integer+1 THEN
  RAISE EXCEPTION 'naming term loses its retained native role span' USING ERRCODE='23514'; END IF;
 IF (named->>'term_start')::integer=(role_indices->>0)::integer+1 AND NOT EXISTS(
   SELECT FROM jsonb_array_elements(rows_->2->'node'->'external_premises') r
   WHERE ops.primary_characterization_node(layers,r)->'native_token'->'index'=role_indices->0
    AND ops.primary_characterization_node(layers,r)->'native_token'->>'dependency'='det') THEN
  RAISE EXCEPTION 'naming term drops a non-determiner native member' USING ERRCODE='23514'; END IF;
 label_span:=proof->'label'; lo:=(naming->'positions'->((named->>'term_start')::integer)->>0)::bigint;
 hi:=(naming->'positions'->((named->>'term_end')::integer-1)->>1)::bigint;
 IF component->'term'->'start' IS DISTINCT FROM to_jsonb(lo) OR component->'term'->'end' IS DISTINCT FROM to_jsonb(hi)
  OR component->'content'->'start' IS DISTINCT FROM first_->'positions'->((first_->'facts'->'intros'->0->>'start')::integer)->0
  OR component->'content'->'end' IS DISTINCT FROM naming->'positions'->((named->>'subject_end')::integer-1)->1
  OR label_span->>'passage_id' IS DISTINCT FROM p_passage->>'passage_id' OR label_span->'start' IS DISTINCT FROM p_passage->'start'
  OR label_span->'end' IS DISTINCT FROM first_->'positions'->1->1
  OR label_span->>'text' IS DISTINCT FROM substring(v.projection->>'text' FROM (label_span->>'start')::integer+1 FOR (label_span->>'end')::integer-(label_span->>'start')::integer) THEN
  RAISE EXCEPTION 'declaration term/content/label differs from exact characterized boundaries' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows OR invalid_text_representation OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'declaration cannot resolve exact selected primary evidence' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_primary_declaration_component(jsonb,jsonb,jsonb,jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.condition_role_citations(inputs jsonb, retained jsonb, row_ jsonb, effective text)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE a jsonb; src jsonb; view_ jsonb; piece jsonb; passage jsonb; source_id text;
 lo integer; hi integer; result jsonb:='[]'; pin jsonb:=row_->'pin';
BEGIN
 SELECT s INTO STRICT src FROM jsonb_array_elements(inputs->'sources') s
 WHERE s->'source_view_id'=pin->'source_view_id'
 AND s->'native_task_id'=pin->'native_product_task_id'
 AND s->'native_product_key'=pin->'product_key'
 AND s->'native_content_digest'=pin->'product_digest'
 AND s->'projection_digest'=pin->'projection_digest'
 AND s->'recipe_digest'=pin->'recipe_digest';
 source_id:=encode(sha256(convert_to(data.canonical_json(src),'UTF8')),'hex');
 SELECT v INTO STRICT view_ FROM jsonb_array_elements(retained->'sources') v WHERE v->'pin'=pin;
 IF jsonb_typeof(row_->'anchors') IS DISTINCT FROM 'array' OR jsonb_array_length(row_->'anchors')=0 THEN
  RAISE EXCEPTION 'condition role requires exact source anchors' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT v FROM jsonb_array_elements(row_->'anchors') WITH ORDINALITY x(v,n) ORDER BY n LOOP
  IF a->'pin' IS DISTINCT FROM pin OR a->>'space' IS DISTINCT FROM 'native'
   OR a->>'precision' IS DISTINCT FROM 'exact' THEN
   RAISE EXCEPTION 'condition role requires exact source anchors' USING ERRCODE='23514'; END IF;
  SELECT p INTO STRICT piece FROM jsonb_array_elements(view_->'projection'->'pieces') p
  WHERE p->>'kind'='native_text' AND (p->>'item_ref')||
   CASE WHEN p->>'cell_index' IS NULL THEN '' ELSE '/data/table_cells/'||(p->>'cell_index') END=a->>'pointer';
  lo:=(piece->>'start')::integer+(a->>'start')::integer;
  hi:=(piece->>'start')::integer+(a->>'end')::integer;
  IF NOT ((piece->>'start')::integer<=lo AND lo<hi AND hi<=(piece->>'end')::integer)
   OR substring(view_->'projection'->>'text' FROM lo+1 FOR hi-lo) IS DISTINCT FROM a->>'source_piece' THEN
   RAISE EXCEPTION 'condition role differs from native source item' USING ERRCODE='23514'; END IF;
  SELECT p INTO STRICT passage FROM jsonb_array_elements(inputs->'passages') p
   WHERE p->>'source_ref'=source_id AND p->>'scope'=inputs->>'scope'
   AND p->>'effective_version' IS NOT DISTINCT FROM effective
   AND (p->>'start')::integer<=lo AND hi<=(p->>'end')::integer;
  IF substring(passage->>'text' FROM lo-(passage->>'start')::integer+1 FOR hi-lo) IS DISTINCT FROM a->>'source_piece' THEN
   RAISE EXCEPTION 'condition role differs from the exact source passage' USING ERRCODE='23514'; END IF;
  result:=result||jsonb_build_array(jsonb_build_object('source_pointer',a->>'pointer','span',
   jsonb_build_object('passage_id',passage->>'passage_id','start',lo,'end',hi,'text',a->>'source_piece')));
 END LOOP;
 IF (SELECT count(DISTINCT x) FROM jsonb_array_elements(result) x)<>jsonb_array_length(result) THEN
  RAISE EXCEPTION 'condition role repeats source evidence' USING ERRCODE='23514'; END IF;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION ops.condition_role_citations(jsonb,jsonb,jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_condition_qualification(inputs jsonb, ref jsonb, product jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb; relation_ jsonb; cue jsonb; host jsonb; predicate jsonb; member jsonb;
 component jsonb; cue_part jsonb; host_part jsonb; qualifier_id text; host_id text; version_ text;
 qualifier_citations jsonb; predicate_citations jsonb;
BEGIN
 retained:=ops.resolve_retained_source_contribution(ref);
 SELECT r INTO STRICT relation_ FROM jsonb_array_elements(retained->'contributions') r
 WHERE r->>'contribution_id'=ref->>'contribution_id';
 component:=relation_->'component';
 qualifier_id:=component->>'qualifier_contribution_id';
 host_id:=component->>'host_contribution_id';
 version_:=component->>'question_version';
 IF relation_->>'semantic_type' IS DISTINCT FROM 'structural.predicate_qualification'
  OR relation_->>'kind' IS DISTINCT FROM 'relation'
  OR component->>'kind' IS DISTINCT FROM 'predicate_qualifier'
  OR component->>'question' IS DISTINCT FROM 'source_predicate_interpretation'
  OR version_ IS DISTINCT FROM '6'
  OR component->>'scope' IS DISTINCT FROM inputs->>'scope'
  OR NOT COALESCE(component->>'qualifier_kind' IN ('condition','assumption'),false)
  OR relation_->'endpoints' IS DISTINCT FROM jsonb_build_array(
   jsonb_build_object('role','qualifier','contribution_id',qualifier_id),
   jsonb_build_object('role','host','contribution_id',host_id))
  OR NOT COALESCE(relation_->'members' ?& ARRAY[qualifier_id,host_id],false) THEN
  RAISE EXCEPTION 'condition statement requires the exact directed qualification' USING ERRCODE='23514'; END IF;
 SELECT r INTO STRICT cue FROM jsonb_array_elements(retained->'contributions') r WHERE r->>'contribution_id'=qualifier_id;
 SELECT r INTO STRICT host FROM jsonb_array_elements(retained->'contributions') r WHERE r->>'contribution_id'=host_id;
 cue_part:=cue->'component'; host_part:=host->'component';
 IF cue->>'semantic_type' IS DISTINCT FROM 'structural.predicate_cue'
  OR host->>'semantic_type' IS DISTINCT FROM 'structural.predicate_frame'
  OR cue_part->>'kind' IS DISTINCT FROM 'predicate_cue'
  OR host_part->>'kind' IS DISTINCT FROM 'predicate_frame'
  OR cue->'pin' IS DISTINCT FROM relation_->'pin' OR host->'pin' IS DISTINCT FROM relation_->'pin'
  OR cue_part->>'question' IS DISTINCT FROM 'source_predicate_frames'
  OR host_part->>'question' IS DISTINCT FROM 'source_predicate_frames'
  OR cue_part->>'question_version' IS DISTINCT FROM version_
  OR host_part->>'question_version' IS DISTINCT FROM version_
  OR cue_part->>'scope' IS DISTINCT FROM inputs->>'scope'
  OR host_part->>'scope' IS DISTINCT FROM inputs->>'scope'
  OR cue_part->>'effective_version' IS DISTINCT FROM component->>'effective_version'
  OR host_part->>'effective_version' IS DISTINCT FROM component->>'effective_version'
  OR cue_part->>'cue_kind' IS DISTINCT FROM component->>'qualifier_kind'
  OR cue_part->>'host_state' IS DISTINCT FROM 'located'
  OR NOT (CASE WHEN COALESCE(jsonb_array_length(cue_part->'cross_block_hosts'),0)>0
     THEN cue_part->'cross_block_hosts' IS NOT DISTINCT FROM jsonb_build_array(host_id)
     ELSE cue_part->'candidate_tokens' IS NOT DISTINCT FROM jsonb_build_array(host_part->'predicate_token')
      AND cue_part->>'block' IS NOT DISTINCT FROM host_part->>'block'
      AND cue_part->>'annotation' IS NOT DISTINCT FROM host_part->>'annotation' END) THEN
  RAISE EXCEPTION 'condition statement requires a uniquely located host in its source scope' USING ERRCODE='23514'; END IF;
 SELECT r INTO STRICT predicate FROM jsonb_array_elements(host_part->'frame_members') r WHERE r->>'role'='predicate';
 SELECT r INTO STRICT member FROM jsonb_array_elements(retained->'contributions') r
 WHERE r->>'contribution_id'=predicate->>'contribution';
 IF predicate->>'outcome' IS DISTINCT FROM 'complete'
  OR member->>'semantic_type' IS DISTINCT FROM 'structural.predicate_member'
  OR NOT COALESCE(host->'members' ? (predicate->>'contribution'),false)
  OR member->'pin' IS DISTINCT FROM relation_->'pin'
  OR data.record_source_json(member->'value')->>'role' IS DISTINCT FROM 'predicate' THEN
  RAISE EXCEPTION 'condition host requires its complete declared predicate member' USING ERRCODE='23514'; END IF;
 qualifier_citations:=ops.condition_role_citations(inputs,retained,cue,component->>'effective_version');
 predicate_citations:=ops.condition_role_citations(inputs,retained,member,component->>'effective_version');
 IF EXISTS(SELECT FROM jsonb_array_elements(qualifier_citations||predicate_citations) c
  JOIN LATERAL jsonb_array_elements(inputs->'passages') p ON p->>'passage_id'=c->'span'->>'passage_id'
  WHERE p->>'effective_version' IS DISTINCT FROM component->>'effective_version')
  OR product IS DISTINCT FROM jsonb_strip_nulls(jsonb_build_object(
   'relation',component->>'qualifier_kind','attachment',ref,'effective_version',component->>'effective_version',
   'qualifier',qualifier_citations,'host_predicate',predicate_citations)) THEN
  RAISE EXCEPTION 'condition role evidence differs from its exact retained source' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'condition statement cannot resolve exact role custody' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_condition_qualification(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_structural_product_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; shape json; product jsonb; inputs jsonb; source_ jsonb; source_map jsonb:='{}'; passage jsonb; passage_map jsonb:='{}'; ref jsonb; v kb.source_view; identifier text; cited text; item jsonb; dimension jsonb; member jsonb; actual text[]; expected text[]; config_ jsonb; method_ text; introduction boolean; target_passage jsonb; premise jsonb; expected_state text; expected_outcome text; states text[]; model_detail jsonb; model_roles jsonb; model_components jsonb; definition_policy jsonb;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 PERFORM sem.require_execution_operation(t.release_id,'bind_report');
 SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact WHERE release_id=t.release_id AND artifact_name='json_schema/SourceObservationBatch';
 IF shape IS NULL OR NOT public.json_matches_schema(shape,p_envelope::json) THEN
  RAISE EXCEPTION 'structural report differs from released shape' USING ERRCODE='23514'; END IF;
 product:=p_envelope->'structural_product'; inputs:=product->'inputs';
 IF t.unit_type<>'run' OR p_envelope->>'release_id' IS DISTINCT FROM t.release_id
 OR p_envelope->>'unit_key' IS DISTINCT FROM t.unit_key
 OR p_envelope->>'invocation_key' IS DISTINCT FROM t.invocation_key
 OR p_envelope->>'input_hash' IS DISTINCT FROM t.input_hash
 OR p_envelope->>'outcome' IS DISTINCT FROM 'produced'
 OR product->>'version' IS DISTINCT FROM 'structural-product-3'
 OR product->>'standing' IS DISTINCT FROM 'private_proposal'
 OR NOT EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
  WHERE cfg.id=t.method_config_id AND cfg.config_hash=p_envelope->>'configuration_hash'
   AND m.name=p_envelope->>'method' AND m.version=p_envelope->>'operation_version'
   AND cfg.params->>'structural_input_digest'=encode(sha256(convert_to(data.canonical_json(inputs),'UTF8')),'hex')) THEN
  RAISE EXCEPTION 'structural report differs from exact producing RUN/input binding' USING ERRCODE='23514'; END IF;
 SELECT cfg.params,m.name INTO STRICT config_,method_ FROM ops.method_config cfg
 JOIN ops.method m ON m.id=cfg.method_id WHERE cfg.id=t.method_config_id;
 IF method_ IN ('structure.compare','structure.dossier') THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs)
   OR product->>'kind' IS DISTINCT FROM (CASE method_ WHEN 'structure.compare' THEN 'qualified_comparison' ELSE 'dossier' END) THEN
   RAISE EXCEPTION 'structural producer differs from frozen original inputs' USING ERRCODE='23514'; END IF;
 ELSIF method_ IN ('structure.definitions','structure.definition_components','structure.definition_declaration_components') THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs)
    OR product->>'kind' IS DISTINCT FROM (CASE WHEN method_='structure.definitions' THEN 'definition_applicability' ELSE 'definition_components' END) THEN
   RAISE EXCEPTION 'definition report differs from frozen source/question input' USING ERRCODE='23514'; END IF;
 ELSIF method_='structure.condition_qualification' THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs)
   OR product->>'kind' IS DISTINCT FROM 'condition_qualification'
   OR p_envelope->>'operation_version' IS DISTINCT FROM '1'
   OR config_->'attachment'->>'release_id' IS DISTINCT FROM t.release_id
   OR config_->'attachment'->>'project_id' IS DISTINCT FROM (SELECT project_id FROM ops.run WHERE id=t.run_id) THEN
   RAISE EXCEPTION 'condition qualification differs from exact producing release and source input' USING ERRCODE='23514'; END IF;
 ELSIF method_='structure.clause_classification' THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs)
   OR product->>'kind' IS DISTINCT FROM 'clause_classification' THEN
   RAISE EXCEPTION 'clause model differs from frozen source inputs' USING ERRCODE='23514'; END IF;
 ELSIF method_='structure.artifact_identity' THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs) OR product->>'kind'<>'artifact_identity' THEN
   RAISE EXCEPTION 'artifact identity differs from exact selected source inputs' USING ERRCODE='23514'; END IF;
 ELSE
  RAISE EXCEPTION 'method does not declare a structural report producer' USING ERRCODE='23514';
 END IF;
 IF t.status<>'running' AND NOT EXISTS(SELECT FROM ops.task_result WHERE task_id=t.id AND body=p_envelope) THEN
  RAISE EXCEPTION 'structural report differs from immutable completed origin' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_structural_input(inputs);
 IF method_ IN ('structure.definition_components','structure.definition_declaration_components','structure.clause_classification') THEN
  source_map:='{}';
  FOR source_ IN SELECT value FROM jsonb_array_elements(inputs->'sources') LOOP
   SELECT * INTO STRICT v FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
   source_map:=source_map||jsonb_build_object(v.id::text,ops.primary_characterization_layers(t,v,config_));
  END LOOP;
  config_:=config_||jsonb_build_object('_primary_layers',source_map);
 END IF;
 SELECT jsonb_object_agg(p->>'passage_id',p) INTO passage_map FROM jsonb_array_elements(inputs->'passages') p;
 IF (CASE WHEN nullif(product->'definition','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'comparison','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'dossier','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'definition_components','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'artifact_identity','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'clause_classification','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'condition_qualification','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END)<>1 THEN
  RAISE EXCEPTION 'structural report must contain exactly one product variant' USING ERRCODE='23514'; END IF;
 CASE product->>'kind'
 WHEN 'condition_qualification' THEN
  PERFORM ops.validate_condition_qualification(inputs,config_->'attachment',product->'condition_qualification');
 WHEN 'clause_classification' THEN
  IF p_envelope->>'operation_version' IS DISTINCT FROM '3' THEN
   RAISE EXCEPTION 'clause observation version differs from released policy' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_clause_classification(inputs,config_||jsonb_build_object(
   '_release',t.release_id,'_operation_version',p_envelope->>'operation_version'),product->'clause_classification',
    data.record_source_json(p_envelope->'parse_detail'));
 WHEN 'definition_components' THEN
  item:=product->'definition_components';
  definition_policy:=ops.model_observation_policy(t.release_id);
  IF method_='structure.definition_declaration_components' THEN
   IF p_envelope->>'operation_version' IS DISTINCT FROM '2'
    OR NOT ops.private_declaration_enabled(t.release_id)
    OR data.record_source_json(p_envelope->'parse_detail') IS DISTINCT FROM
     '{"version":"definition-declaration-chain-2"}'::jsonb
    OR nullif(item->'role_candidates','null') IS NOT NULL
    OR jsonb_typeof(config_->'selections') IS DISTINCT FROM 'array'
    OR NOT COALESCE(jsonb_array_length(config_->'selections') BETWEEN 1 AND 64,false)
    OR jsonb_array_length(item->'components') IS DISTINCT FROM jsonb_array_length(config_->'selections')
    OR jsonb_array_length(item->'stages') IS DISTINCT FROM jsonb_array_length(config_->'selections')
    OR (SELECT count(DISTINCT x->>'passage_id') FROM jsonb_array_elements(config_->'selections') x)
     <>jsonb_array_length(config_->'selections')
    OR EXISTS(SELECT FROM jsonb_array_elements(config_->'selections') WITH ORDINALITY AS s(selection,n)
     WHERE nullif(selection->'parser','null') IS NOT NULL
      OR item->'components'->((n-1)::integer)#>>'{term,passage_id}' IS DISTINCT FROM selection->>'passage_id'
      OR item->'stages'->((n-1)::integer) IS DISTINCT FROM jsonb_build_object(
       'passage_id',selection->>'passage_id','operation','attachment','outcome','succeeded',
       'reason','Released declaration chain replayed from exact native parser roles.')) THEN
    RAISE EXCEPTION 'declaration report differs from its released exact configured population'
     USING ERRCODE='23514'; END IF;
  ELSIF (definition_policy IS NOT NULL) IS DISTINCT FROM
   (p_envelope->>'operation_version'='10') THEN
   RAISE EXCEPTION 'definition observation version differs from released policy' USING ERRCODE='23514'; END IF;
  IF p_envelope->>'operation_version'='10' THEN
   model_detail:=data.record_source_json(p_envelope->'parse_detail');
   IF p_envelope->>'operation_version'='10' THEN
    IF model_detail->>'version' IS DISTINCT FROM 'located-definition-extraction-5'
     OR jsonb_typeof(item->'role_candidates') IS DISTINCT FROM 'array' THEN
     RAISE EXCEPTION 'definition model requires located observation ABI 5' USING ERRCODE='23514'; END IF;
    PERFORM ops.validate_definition_window_requests(t.release_id,model_detail,config_,passage_map);
   END IF;
   model_roles:=ops.definition_role_candidates(model_detail,config_,passage_map);
   IF COALESCE(item->'role_candidates','[]'::jsonb) IS DISTINCT FROM model_roles THEN
    RAISE EXCEPTION 'definition role differs from exact indexed model envelope' USING ERRCODE='23514'; END IF;
   SELECT COALESCE(jsonb_agg(c ORDER BY c->>'component_id'),'[]') INTO model_components
    FROM jsonb_array_elements(item->'components') c WHERE c->>'basis'='model_reading';
   IF model_components IS DISTINCT FROM ops.definition_model_components(model_detail,config_,passage_map,model_roles) THEN
    RAISE EXCEPTION 'model definition components differ from retained directed attachments' USING ERRCODE='23514'; END IF;
  END IF;
  IF (SELECT count(*)<>count(DISTINCT c->>'component_id') FROM jsonb_array_elements(item->'components') c) THEN
   RAISE EXCEPTION 'duplicate definition component identity' USING ERRCODE='23514'; END IF;
  FOR dimension IN SELECT value FROM jsonb_array_elements(item->'components') LOOP
   IF dimension->>'component_id' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(dimension-'component_id'),'UTF8')),'hex') THEN
    RAISE EXCEPTION 'definition component identity differs from complete meaning' USING ERRCODE='23514'; END IF;
   FOR ref IN SELECT dimension->'term' UNION ALL SELECT dimension->'content' LOOP
    passage:=passage_map->(ref->>'passage_id');
    IF method_='structure.definition_components' AND NOT config_->'target_ids' ? (ref->>'passage_id') THEN RAISE EXCEPTION 'definition span is outside inspected target selection' USING ERRCODE='23514'; END IF;
    IF passage IS NULL OR (ref->>'start')::bigint<(passage->>'start')::bigint OR (ref->>'end')::bigint>(passage->>'end')::bigint
     OR (ref->>'end')::bigint<=(ref->>'start')::bigint OR ref->>'text' IS DISTINCT FROM substring(passage->>'text' FROM (ref->>'start')::integer-(passage->>'start')::integer+1 FOR (ref->>'end')::integer-(ref->>'start')::integer)
     OR dimension->>'scope' IS DISTINCT FROM passage->>'scope' OR dimension->>'effective_version' IS DISTINCT FROM passage->>'effective_version' THEN
     RAISE EXCEPTION 'definition span or scope differs from exact source' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF EXISTS(SELECT FROM jsonb_array_elements_text(dimension->'evidence') e WHERE NOT passage_map ? e) THEN
    RAISE EXCEPTION 'definition evidence outside selected source' USING ERRCODE='23514'; END IF;
   passage:=passage_map->(dimension->'term'->>'passage_id');
   SELECT s INTO source_ FROM jsonb_array_elements(inputs->'sources') s
   WHERE encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')=passage->>'source_ref';
   IF method_='structure.definition_declaration_components' THEN
    PERFORM ops.validate_primary_declaration_component(dimension,passage,source_,config_,t.release_id);
   ELSE
    IF nullif(dimension->'declaration_chain','null') IS NOT NULL THEN
     RAISE EXCEPTION 'incumbent definition extraction cannot carry a declaration chain'
      USING ERRCODE='23514'; END IF;
    PERFORM ops.validate_definition_basis(dimension,passage,source_,
     config_||jsonb_build_object('_release',t.release_id),definition_policy);
   END IF;
  END LOOP;
 WHEN 'definition_applicability' THEN
  item:=product->'definition';
  IF item IS NULL OR NOT passage_map ? (item->>'usage_id') OR item->>'retrieval_diagnosis' IS DISTINCT FROM 'not_independently_assessed' THEN
   RAISE EXCEPTION 'invalid definition usage or unsupported retrieval diagnosis' USING ERRCODE='23514'; END IF;
  IF method_='structure.definitions' AND (
   (SELECT jsonb_agg(selected_ref.value ORDER BY data.canonical_json(selected_ref.value)) FROM jsonb_array_elements(config_->'selection_refs') AS selected_ref(value))
   IS DISTINCT FROM (SELECT jsonb_agg(r->'link_ref' ORDER BY data.canonical_json(r->'link_ref')) FROM jsonb_array_elements(item->'readings') r)) THEN
   RAISE EXCEPTION 'applicability differs from frozen actual relationship selection' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements_text(item->'candidate_targets') c WHERE NOT item->'eligible_targets' ? c)
   OR EXISTS(SELECT FROM jsonb_array_elements(item->'readings') r WHERE NOT item->'candidate_targets' ? (r->>'target_id')) THEN
   RAISE EXCEPTION 'definition reading differs from fixed eligible candidate population' USING ERRCODE='23514'; END IF;
  FOR dimension IN SELECT value FROM jsonb_array_elements(item->'readings') LOOP
   source_:=ops.resolve_retained_relationship_decision(dimension->'link_ref');
   IF dimension->'component_ref' IS DISTINCT FROM source_->'component_target'->'reference'
    OR dimension->>'target_id' IS DISTINCT FROM source_->'edge'->>'target_id'
    OR item->>'candidate_list_id' IS DISTINCT FROM source_->'decision'->>'candidate_list_id' THEN
    RAISE EXCEPTION 'applicability loses actual selected edge and target binding' USING ERRCODE='23514'; END IF;
   passage:=passage_map->(item->>'usage_id');
   SELECT * INTO STRICT v FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(inputs->'sources') src WHERE (src->>'source_view_id')::bigint=v.id
    AND encode(sha256(convert_to(data.canonical_json(src),'UTF8')),'hex')=passage->>'source_ref')
    OR (SELECT jsonb_agg(jsonb_build_object('pointer',p->>'item_ref'||CASE WHEN p->>'source_field'='cell_text' THEN '/data/table_cells/'||(p->>'cell_index') ELSE '' END,
      'start',greatest((passage->>'start')::bigint,(p->>'start')::bigint)-(p->>'start')::bigint,
      'end',least((passage->>'end')::bigint,(p->>'end')::bigint)-(p->>'start')::bigint,
      'source_piece',substring(v.projection->>'text' FROM greatest((passage->>'start')::integer,(p->>'start')::integer)+1 FOR least((passage->>'end')::integer,(p->>'end')::integer)-greatest((passage->>'start')::integer,(p->>'start')::integer))) ORDER BY p->>'item_ref',greatest((passage->>'start')::bigint,(p->>'start')::bigint)-(p->>'start')::bigint)
      FROM jsonb_array_elements(v.projection->'pieces') p WHERE p->>'kind'='native_text' AND (p->>'start')::bigint<(passage->>'end')::bigint AND (p->>'end')::bigint>(passage->>'start')::bigint)
     IS DISTINCT FROM (SELECT jsonb_agg(jsonb_build_object('pointer',a->'pointer','start',a->'start','end',a->'end','source_piece',a->'source_piece') ORDER BY a->>'pointer',(a->>'start')::bigint,(a->>'end')::bigint)
      FROM jsonb_array_elements(source_->'occurrence'->'anchors') WITH ORDINALITY anchor(a,n)) THEN
     RAISE EXCEPTION 'usage differs from exact linked occurrence original source pieces' USING ERRCODE='23514'; END IF;
   ref:=ops.resolve_retained_component(dimension->'component_ref');
   IF data.structural_definition_component(ref->'report',ref->'component') IS DISTINCT FROM source_->'semantic_target' THEN RAISE EXCEPTION 'applicability component changes semantic target group meaning' USING ERRCODE='23514'; END IF;
   IF dimension->'component' IS DISTINCT FROM ref->'component' THEN RAISE EXCEPTION 'applicability component differs from authenticated origin' USING ERRCODE='23514'; END IF;
   IF source_->'edge'->>'relation' NOT IN ('denotes','defined-by')
    OR source_->'decision'->>'scope' IS DISTINCT FROM passage->>'scope'
    OR source_->'decision'->>'effective_version' IS DISTINCT FROM passage->>'effective_version' THEN
    RAISE EXCEPTION 'applicability requires actual usage-sense selection under the usage scope/version' USING ERRCODE='23514'; END IF;
   SELECT p INTO STRICT target_passage FROM jsonb_array_elements(ref->'report'->'inputs'->'passages') p WHERE p->>'passage_id'=ref->'component'->'term'->>'passage_id';
   introduction:=config_->>'applicability_scope'='defining_occurrence'
    AND inputs->>'policy_id'='definition-introduction-1'
    AND source_->'edge'->>'relation'='defined-by'
    AND passage->>'start'=ref->'component'->'term'->>'start' AND passage->>'end'=ref->'component'->'term'->>'end'
    AND passage->>'text'=ref->'component'->'term'->>'text' AND passage->>'scope'=ref->'component'->>'scope'
    AND passage->>'effective_version' IS NOT DISTINCT FROM ref->'component'->>'effective_version'
    AND passage->>'parent' IS NOT DISTINCT FROM target_passage->>'parent'
    AND passage->>'source_ref'=target_passage->>'source_ref';
   IF jsonb_array_length(dimension->'premises')<>6 OR
    (SELECT array_agg(p->>'dimension' ORDER BY p->>'dimension') FROM jsonb_array_elements(dimension->'premises') p)
     IS DISTINCT FROM ARRAY['convention','parameterization','parent','scope','sense','version'] THEN
    RAISE EXCEPTION 'applicability requires the exact six independent dimensions' USING ERRCODE='23514'; END IF;
   states:=ARRAY[]::text[];
   FOR premise IN SELECT value FROM jsonb_array_elements(dimension->'premises') LOOP
    expected_state:=CASE premise->>'dimension'
     WHEN 'sense' THEN 'compatible'
     WHEN 'parent' THEN CASE WHEN passage->>'parent' IS NOT NULL AND target_passage->>'parent' IS NOT NULL THEN CASE WHEN passage->>'parent'=target_passage->>'parent' THEN 'compatible' ELSE 'incompatible' END
      WHEN passage->>'parent' IS NULL AND target_passage->>'parent' IS NULL AND COALESCE(introduction,false) THEN 'inapplicable' ELSE 'unknown' END
     WHEN 'scope' THEN CASE WHEN passage->>'scope'=ref->'component'->>'scope' THEN 'compatible' ELSE 'incompatible' END
     WHEN 'version' THEN CASE WHEN passage->>'effective_version' IS NULL AND ref->'component'->>'effective_version' IS NOT NULL THEN 'unknown'
      WHEN passage->>'effective_version' IS NOT DISTINCT FROM ref->'component'->>'effective_version' THEN 'compatible' ELSE 'incompatible' END
     ELSE CASE WHEN COALESCE(introduction,false) THEN 'inapplicable' ELSE 'unknown' END END;
    IF premise->>'state' IS DISTINCT FROM expected_state OR premise->'evidence' IS DISTINCT FROM jsonb_build_array(item->>'usage_id',ref->'component'->'term'->>'passage_id') THEN
     RAISE EXCEPTION 'applicability premise differs from actual source-bound operation' USING ERRCODE='23514'; END IF;
    states:=array_append(states,expected_state);
   END LOOP;
   expected_outcome:=CASE WHEN 'incompatible'=ANY(states) THEN 'incompatible' WHEN 'unknown'=ANY(states) OR ref->'component'->>'interpretation'='unresolved' THEN 'unresolved'
    WHEN ref->'component'->>'interpretation'='definition' THEN 'applicable_definition' ELSE 'applicable_explanation' END;
   IF dimension->>'outcome' IS DISTINCT FROM expected_outcome THEN RAISE EXCEPTION 'applicability outcome differs from authenticated premises' USING ERRCODE='23514'; END IF;
   IF NOT inputs->'dependencies' ? (dimension->'component_ref'->>'product_id') THEN
    RAISE EXCEPTION 'applicability lacks frozen component dependency' USING ERRCODE='23514'; END IF;
   IF dimension->>'outcome' LIKE 'applicable_%' AND EXISTS(SELECT FROM jsonb_array_elements(dimension->'premises') AS declared_premise(value) WHERE declared_premise.value->>'state' IN ('unknown','incompatible')) THEN
    RAISE EXCEPTION 'applicability requires resolved compatible premises' USING ERRCODE='23514'; END IF;
  END LOOP;
 WHEN 'artifact_identity' THEN
  IF method_<>'structure.artifact_identity' THEN RAISE EXCEPTION 'artifact identity producer mismatch' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_artifact_identity(t,inputs,config_||jsonb_build_object(
   '_operation_version',p_envelope->>'operation_version'),product->'artifact_identity');
 WHEN 'qualified_comparison' THEN
  IF method_ IS DISTINCT FROM 'structure.compare' OR p_envelope->>'operation_version' IS DISTINCT FROM '6'
   OR jsonb_strip_nulls(product->'comparison') IS DISTINCT FROM ops.structural_grouped_comparison(t,inputs,config_) THEN
   RAISE EXCEPTION 'comparison differs from exact retained primary facts and predicate6' USING ERRCODE='23514'; END IF;
 WHEN 'dossier' THEN
  IF method_ IS DISTINCT FROM 'structure.dossier' OR jsonb_strip_nulls(product->'dossier') IS DISTINCT FROM
    ops.structural_dossier(inputs,config_||jsonb_build_object(
     '_require_focus',p_envelope->>'operation_version'='3')) THEN
   RAISE EXCEPTION 'dossier differs from authenticated predecessor membership/representation' USING ERRCODE='23514'; END IF;
 ELSE RAISE EXCEPTION 'unsupported structural product variant' USING ERRCODE='23514';
 END CASE;
 -- Every evidence member is a selected anchored passage, never an invented snippet.
 FOR cited IN SELECT jsonb_array_elements_text(r->'evidence') FROM jsonb_array_elements(COALESCE(product->'definition'->'readings','[]')) r
 UNION ALL SELECT jsonb_array_elements_text(s->'evidence') FROM jsonb_array_elements(COALESCE(product->'comparison'->'dimensions','[]')) d,
 LATERAL jsonb_array_elements(jsonb_build_array(d->'left',d->'right')) s WHERE s<>'null'::jsonb LOOP
  IF NOT passage_map ? cited THEN RAISE EXCEPTION 'structural evidence outside declared source closure' USING ERRCODE='23514'; END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'structural report cannot resolve declared original source closure' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_structural_product_report(bigint,jsonb) FROM PUBLIC;
