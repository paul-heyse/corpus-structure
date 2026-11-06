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
 IF selected.report->>'version' IS DISTINCT FROM 'structural-product-2'
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
DECLARE selected record; operation jsonb; decision jsonb; edge jsonb; occurrence jsonb; target jsonb;
BEGIN
 SELECT result.body, task.unit_id, batch.data_revision, origin_job.runtime_id INTO STRICT selected
 FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id
 JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id
 JOIN ops.cut_task member ON member.cut_id=completed.cut_id JOIN ops.task task ON task.id=member.task_id
 JOIN ops.task origin ON origin.id=member.origin_task_id JOIN ops.run origin_job ON origin_job.id=origin.run_id
 JOIN ops.task_result result ON result.task_id=origin.id
 WHERE job.id=(ref->>'run_id')::bigint AND job.project_id=ref->>'project_id' AND job.release_id=ref->>'release_id'
 AND job.sealed AND job.status='finished' AND completed.cut_id=(ref->>'cut_id')::bigint
 AND task.id=(ref->>'selected_task_id')::bigint AND origin.id=(ref->>'origin_task_id')::bigint
 AND origin.id=COALESCE(task.reused_task_id,task.id) AND origin.release_id=ref->>'release_id' AND task.status IN ('done','reused');
 IF selected.data_revision IS DISTINCT FROM (ref->>'result_revision')::bigint OR selected.runtime_id IS DISTINCT FROM ref->>'runtime_fingerprint' THEN
  RAISE EXCEPTION 'retained relationship differs from original runtime/revision' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT operation FROM jsonb_array_elements(selected.body->'contribution_operations') WHERE value->>'operation_key'=ref->>'operation_key';
 IF operation->'contextual_enrichment'->>'version' IS DISTINCT FROM 'contextual-enrichment-2' THEN
  RAISE EXCEPTION 'retained relationship requires current contextual product' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT decision FROM jsonb_array_elements(operation->'contextual_enrichment'->'relationship_decisions') WHERE value->>'decision_id'=ref->>'decision_id';
 SELECT value INTO STRICT edge FROM jsonb_array_elements(decision->'selected_edges') WHERE value->>'edge_id'=ref->>'edge_id';
 SELECT value INTO STRICT occurrence FROM jsonb_array_elements(selected.body->'contributions') WHERE value->>'contribution_id'=ref->>'occurrence_contribution_id'
 AND value->>'semantic_type'='contextual.located_mention' AND value->>'occurrence_id'=decision->>'occurrence_id'
 AND EXISTS(SELECT FROM jsonb_array_elements(edge->'witnesses') w WHERE w->'evidence_ids' ? (value->>'contribution_id'));
 SELECT value INTO STRICT target FROM jsonb_array_elements(operation->'contextual_enrichment'->'component_targets') WHERE value->'reference'->>'component_id'=edge->>'target_id';
 PERFORM ops.resolve_retained_component(target->'reference');
 RETURN jsonb_build_object('decision',decision,'edge',edge,'occurrence',occurrence,'component_target',target,'source_view_id',selected.unit_id);
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'retained relationship cannot resolve exact original edge/source' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_relationship_decision(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_relationship_decision(jsonb) TO corpus_sem_reader,corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.validate_structural_product_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; shape json; product jsonb; inputs jsonb; source_ jsonb; source_map jsonb:='{}'; passage jsonb; passage_map jsonb:='{}'; ref jsonb; v kb.source_view; identifier text; cited text; item jsonb; dimension jsonb; member jsonb; actual text[]; expected text[]; config_ jsonb; method_ text;
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
 OR product->>'version' IS DISTINCT FROM 'structural-product-2'
 OR product->>'standing' IS DISTINCT FROM 'private_proposal'
 OR NOT EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
  WHERE cfg.id=t.method_config_id AND cfg.config_hash=p_envelope->>'configuration_hash'
   AND m.name=p_envelope->>'method' AND m.version=p_envelope->>'operation_version'
   AND cfg.params->>'structural_input_digest'=encode(sha256(convert_to(data.canonical_json(inputs),'UTF8')),'hex')) THEN
  RAISE EXCEPTION 'structural report differs from exact producing RUN/input binding' USING ERRCODE='23514'; END IF;
 SELECT cfg.params,m.name INTO STRICT config_,method_ FROM ops.method_config cfg
 JOIN ops.method m ON m.id=cfg.method_id WHERE cfg.id=t.method_config_id;
 IF method_='structure.products' THEN
  -- Registry configuration numbers use canonical decimal strings. Preserve exact
  -- semantic fields and all raw derivation values while accounting for that
  -- representation at numeric derivation leaves only.
  IF jsonb_strip_nulls(config_->'report')-'retrieval_report' IS DISTINCT FROM jsonb_strip_nulls(product)-'retrieval_report'
   OR EXISTS(WITH RECURSIVE nodes(expected,actual,path) AS (
    SELECT jsonb_strip_nulls(config_->'report')->'retrieval_report',jsonb_strip_nulls(product)->'retrieval_report',''::text
    UNION ALL
    SELECT child.expected,child.actual,n.path||child.suffix FROM nodes n CROSS JOIN LATERAL (
     SELECT n.expected->key expected,value actual,'.'||key suffix FROM jsonb_each(CASE WHEN jsonb_typeof(n.actual)='object' THEN n.actual ELSE '{}'::jsonb END)
     UNION ALL
     SELECT n.expected->(ord-1)::integer,value,'.*' FROM jsonb_array_elements(CASE WHEN jsonb_typeof(n.actual)='array' THEN n.actual ELSE '[]'::jsonb END) WITH ORDINALITY a(value,ord)
    ) child
   ) SELECT FROM nodes n WHERE CASE jsonb_typeof(n.actual)
    WHEN 'object' THEN jsonb_typeof(n.expected) IS DISTINCT FROM 'object'
      OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(n.actual) key)
        IS DISTINCT FROM (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(CASE WHEN jsonb_typeof(n.expected)='object' THEN n.expected ELSE '{}'::jsonb END) key)
    WHEN 'array' THEN jsonb_typeof(n.expected) IS DISTINCT FROM 'array'
      OR jsonb_array_length(n.actual)<>jsonb_array_length(CASE WHEN jsonb_typeof(n.expected)='array' THEN n.expected ELSE '[]'::jsonb END)
    WHEN 'number' THEN n.expected IS DISTINCT FROM n.actual AND (
      jsonb_typeof(n.expected) IS DISTINCT FROM 'string'
      OR n.path NOT IN ('.vectors.*.values.*','.profiles.*.timeout_seconds',
        '.candidate_lists.*.candidates.*.fusion_score',
        '.candidate_lists.*.candidates.*.channels.*.raw_score',
        '.candidate_lists.*.channel_results.*.hits.*.score')
      OR n.expected#>>'{}' IS DISTINCT FROM data.decimal_canonical(n.actual#>>'{}'))
    ELSE n.expected IS DISTINCT FROM n.actual END) THEN
   RAISE EXCEPTION 'supplied structural report differs from its frozen configuration' USING ERRCODE='23514'; END IF;
 ELSIF method_ IN ('structure.definitions','structure.definition_components') THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs)
    OR product->>'kind' NOT IN ('definition_components','definition_applicability') THEN
   RAISE EXCEPTION 'definition report differs from frozen source/question input' USING ERRCODE='23514'; END IF;
 ELSE
  RAISE EXCEPTION 'method does not declare a structural report producer' USING ERRCODE='23514';
 END IF;
 IF t.status<>'running' AND NOT EXISTS(SELECT FROM ops.task_result WHERE task_id=t.id AND body=p_envelope) THEN
  RAISE EXCEPTION 'structural report differs from immutable completed origin' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_structural_input(inputs);
 SELECT jsonb_object_agg(p->>'passage_id',p) INTO passage_map FROM jsonb_array_elements(inputs->'passages') p;
 IF (CASE WHEN nullif(product->'definition','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'comparison','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'dossier','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'definition_components','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END)<>1 THEN
  RAISE EXCEPTION 'structural report must contain exactly one product variant' USING ERRCODE='23514'; END IF;
 CASE product->>'kind'
 WHEN 'definition_components' THEN
  item:=product->'definition_components';
  IF (SELECT count(*)<>count(DISTINCT c->>'component_id') FROM jsonb_array_elements(item->'components') c) THEN
   RAISE EXCEPTION 'duplicate definition component identity' USING ERRCODE='23514'; END IF;
  FOR dimension IN SELECT value FROM jsonb_array_elements(item->'components') LOOP
   IF dimension->>'component_id' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(dimension-'component_id'),'UTF8')),'hex') THEN
    RAISE EXCEPTION 'definition component identity differs from complete meaning' USING ERRCODE='23514'; END IF;
   FOR ref IN SELECT dimension->'term' UNION ALL SELECT dimension->'content' LOOP
    passage:=passage_map->(ref->>'passage_id');
    IF passage IS NULL OR (ref->>'start')::bigint<(passage->>'start')::bigint OR (ref->>'end')::bigint>(passage->>'end')::bigint
     OR (ref->>'end')::bigint<=(ref->>'start')::bigint OR ref->>'text' IS DISTINCT FROM substring(passage->>'text' FROM (ref->>'start')::integer-(passage->>'start')::integer+1 FOR (ref->>'end')::integer-(ref->>'start')::integer)
     OR dimension->>'scope' IS DISTINCT FROM passage->>'scope' OR dimension->>'effective_version' IS DISTINCT FROM passage->>'effective_version' THEN
     RAISE EXCEPTION 'definition span or scope differs from exact source' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF EXISTS(SELECT FROM jsonb_array_elements_text(dimension->'evidence') e WHERE NOT passage_map ? e) THEN
    RAISE EXCEPTION 'definition evidence outside selected source' USING ERRCODE='23514'; END IF;
  END LOOP;
 WHEN 'definition_applicability' THEN
  item:=product->'definition';
  IF item IS NULL OR NOT passage_map ? (item->>'usage_id') OR item->>'retrieval_diagnosis' IS DISTINCT FROM 'not_independently_assessed' THEN
   RAISE EXCEPTION 'invalid definition usage or unsupported retrieval diagnosis' USING ERRCODE='23514'; END IF;
  IF method_='structure.definitions' AND (
   (SELECT jsonb_agg(v ORDER BY data.canonical_json(v)) FROM jsonb_array_elements(config_->'selection_refs') v)
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
   IF dimension->'component' IS DISTINCT FROM ref->'component' THEN RAISE EXCEPTION 'applicability component differs from authenticated origin' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM jsonb_array_elements(dimension->'premises') premise WHERE premise->>'dimension' IN ('parameterization','convention') AND premise->>'state'='inapplicable') THEN
    IF inputs->>'policy_id' IS DISTINCT FROM 'definition-introduction-1'
     OR source_->'edge'->>'relation' IS DISTINCT FROM 'defined-by'
     OR passage->>'start' IS DISTINCT FROM ref->'component'->'term'->>'start'
     OR passage->>'end' IS DISTINCT FROM ref->'component'->'term'->>'end'
     OR passage->>'text' IS DISTINCT FROM ref->'component'->'term'->>'text'
     OR passage->>'scope' IS DISTINCT FROM ref->'component'->>'scope'
     OR passage->>'effective_version' IS DISTINCT FROM ref->'component'->>'effective_version'
     OR passage->>'source_ref' IS DISTINCT FROM (SELECT p->>'source_ref' FROM jsonb_array_elements(ref->'report'->'inputs'->'passages') p WHERE p->>'passage_id'=ref->'component'->'term'->>'passage_id') THEN
     RAISE EXCEPTION 'inapplicable convention or parameterization requires exact defining occurrence policy' USING ERRCODE='23514'; END IF;
   END IF;
   IF NOT inputs->'dependencies' ? (dimension->'component_ref'->>'product_id') THEN
    RAISE EXCEPTION 'applicability lacks frozen component dependency' USING ERRCODE='23514'; END IF;
   IF dimension->>'outcome' LIKE 'applicable_%' AND EXISTS(SELECT FROM jsonb_array_elements(dimension->'premises') premise WHERE premise->>'state' IN ('unknown','incompatible')) THEN
    RAISE EXCEPTION 'applicability requires resolved compatible premises' USING ERRCODE='23514'; END IF;
  END LOOP;
 WHEN 'qualified_comparison' THEN
  item:=product->'comparison';
  IF item IS NULL OR item->>'left_id'=item->>'right_id' OR NOT passage_map ? (item->>'left_id') OR NOT passage_map ? (item->>'right_id')
   OR item->>'equivalence' IS DISTINCT FROM 'not_asserted' OR item->>'identity_standing' IS DISTINCT FROM 'not_asserted' THEN
   RAISE EXCEPTION 'comparison cannot manufacture equivalence or identity' USING ERRCODE='23514'; END IF;
  SELECT array_agg(value->>'dimension' ORDER BY n) INTO actual FROM jsonb_array_elements(item->'dimensions') WITH ORDINALITY d(value,n);
  expected:=ARRAY['actor','action','object','modality','condition','threshold_unit','exception','order_dependency','parent','version'];
  IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'comparison lacks ordered unknown-inclusive dimensions' USING ERRCODE='23514'; END IF;
  FOR dimension IN SELECT value FROM jsonb_array_elements(item->'dimensions') LOOP
   IF nullif(dimension->'left','null'::jsonb) IS NULL OR nullif(dimension->'right','null'::jsonb) IS NULL THEN
    IF dimension->>'outcome'<>'unknown' THEN RAISE EXCEPTION 'comparison infers absent dimension' USING ERRCODE='23514'; END IF;
   ELSIF dimension->'left'->>'dimension' IS DISTINCT FROM dimension->>'dimension' OR dimension->'right'->>'dimension' IS DISTINCT FROM dimension->>'dimension' THEN
    RAISE EXCEPTION 'comparison dimension does not match cited fields' USING ERRCODE='23514';
   ELSIF passage_map->(item->>'left_id')->>'scope' IS DISTINCT FROM passage_map->(item->>'right_id')->>'scope'
    OR passage_map->(item->>'left_id')->>'effective_version' IS DISTINCT FROM passage_map->(item->>'right_id')->>'effective_version' THEN
    IF dimension->>'outcome'<>'incompatible_applicability' THEN RAISE EXCEPTION 'comparison loses source applicability' USING ERRCODE='23514'; END IF;
   ELSIF dimension->>'outcome' IS DISTINCT FROM (CASE WHEN dimension->'left'->>'lexical_value'=dimension->'right'->>'lexical_value' THEN 'same_lexical_value' ELSE 'different_lexical_value' END) THEN
    RAISE EXCEPTION 'comparison lexical result differs from supplied attributed fields' USING ERRCODE='23514'; END IF;
  END LOOP;
 WHEN 'dossier' THEN
  item:=product->'dossier';
  IF item IS NULL OR item->>'membership_completeness' IS DISTINCT FROM 'declared_selection' THEN RAISE EXCEPTION 'invalid dossier membership claim' USING ERRCODE='23514'; END IF;
  FOR member IN SELECT value FROM jsonb_array_elements(item->'members') LOOP
   IF NOT passage_map ? (member->>'passage_id') OR (member->>'qualification'='independently_supported' AND nullif(member->>'assessment_id','') IS NULL) THEN
    RAISE EXCEPTION 'dossier member lacks source or declared qualification reference' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF (SELECT count(*)<>count(DISTINCT m->>'member_id') FROM jsonb_array_elements(item->'members') m)
  OR EXISTS(SELECT FROM jsonb_array_elements_text(item->'representatives') representative WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(item->'members') m WHERE m->>'member_id'=representative)) THEN
   RAISE EXCEPTION 'dossier membership/representative references differ' USING ERRCODE='23514'; END IF;
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
