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

CREATE OR REPLACE FUNCTION ops.validate_structural_product_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; shape json; product jsonb; inputs jsonb; source_ jsonb; source_map jsonb:='{}'; passage jsonb; passage_map jsonb:='{}'; ref jsonb; v kb.source_view; identifier text; cited text; item jsonb; dimension jsonb; member jsonb; actual text[]; expected text[];
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
 OR product->>'version' IS DISTINCT FROM 'structural-product-1'
 OR product->>'standing' IS DISTINCT FROM 'private_proposal'
 OR NOT EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
  WHERE cfg.id=t.method_config_id AND cfg.config_hash=p_envelope->>'configuration_hash'
   AND m.name=p_envelope->>'method' AND m.version=p_envelope->>'operation_version'
   AND cfg.params->>'structural_input_digest'=encode(sha256(convert_to(data.canonical_json(inputs),'UTF8')),'hex')) THEN
  RAISE EXCEPTION 'structural report differs from exact producing RUN/input binding' USING ERRCODE='23514'; END IF;
 IF t.status<>'running' AND NOT EXISTS(SELECT FROM ops.task_result WHERE task_id=t.id AND body=p_envelope) THEN
  RAISE EXCEPTION 'structural report differs from immutable completed origin' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_structural_input(inputs);
 SELECT jsonb_object_agg(p->>'passage_id',p) INTO passage_map FROM jsonb_array_elements(inputs->'passages') p;
 IF (CASE WHEN nullif(product->'definition','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'comparison','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'dossier','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END)<>1 THEN
  RAISE EXCEPTION 'structural report must contain exactly one product variant' USING ERRCODE='23514'; END IF;
 CASE product->>'kind'
 WHEN 'definition_applicability' THEN
  item:=product->'definition';
  IF item IS NULL OR NOT passage_map ? (item->>'usage_id') OR item->>'retrieval_diagnosis' IS DISTINCT FROM 'not_independently_assessed' THEN
   RAISE EXCEPTION 'invalid definition usage or unsupported retrieval diagnosis' USING ERRCODE='23514'; END IF;
  FOR cited IN SELECT jsonb_array_elements_text(item->'eligible_targets') LOOP
   IF NOT passage_map ? cited THEN RAISE EXCEPTION 'definition target outside source closure' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF EXISTS(SELECT FROM jsonb_array_elements_text(item->'candidate_targets') c WHERE NOT item->'eligible_targets' ? c)
   OR EXISTS(SELECT FROM jsonb_array_elements(item->'readings') r WHERE NOT item->'candidate_targets' ? (r->>'target_id')) THEN
   RAISE EXCEPTION 'definition reading differs from fixed eligible candidate population' USING ERRCODE='23514'; END IF;
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
