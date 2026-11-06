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
DECLARE selected record; operation jsonb; decision jsonb; edge jsonb; occurrence jsonb; target jsonb; semantic_group jsonb; targets jsonb; member jsonb;
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
 RETURN jsonb_build_object('decision',decision,'edge',edge,'occurrence',occurrence,'component_target',target,'component_targets',targets,'semantic_target',semantic_group->'meaning','source_view_id',selected.unit_id);
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'retained relationship cannot resolve exact original edge/source' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_relationship_decision(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_relationship_decision(jsonb) TO corpus_sem_reader,corpus_sem_writer;

-- Current deterministic source-field route replay. SQL token positions are character
-- positions, matching Python projected string offsets (never byte offsets).
CREATE OR REPLACE FUNCTION ops.structural_threshold_field(passage jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE pattern text:='>=|<=|>|<|=|≥|≤|[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[^\W\d][\w.-]*|[^\s]';
 raw text:=passage->>'text'; tokens jsonb:='[]'; item record; i integer; begin_ integer; end_ integer; field_ text; parts text[]; fields jsonb:='[]'; symbol text; op text; value_ text; unit_ text;
BEGIN
 FOR item IN SELECT m[1] text,n::integer FROM regexp_matches(raw,'('||pattern||')','g') WITH ORDINALITY a(m,n) LOOP
  tokens:=tokens||jsonb_build_array(jsonb_build_object('text',item.text,'start',regexp_instr(raw,pattern,1,item.n)-1,'end',regexp_instr(raw,pattern,1,item.n,1)-1));
 END LOOP;
 FOR i IN 0..jsonb_array_length(tokens)-2 LOOP
  IF tokens->i->>'text' NOT IN ('>','>=','<','<=','=','≥','≤') OR tokens->(i+1)->>'text' !~ '^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$' THEN CONTINUE; END IF;
  begin_:=(tokens->i->>'start')::integer;end_:=(tokens->(i+1)->>'end')::integer;
  IF i>0 AND tokens->(i-1)->>'text' ~ '^[^\W\d][\w.-]*$' THEN begin_:=(tokens->(i-1)->>'start')::integer;END IF;
  IF tokens->(i+2)->>'text' IN ('%','$','€','£','USD','EUR','kg','m','s') THEN end_:=(tokens->(i+2)->>'end')::integer;END IF;
  field_:=substring(raw FROM begin_+1 FOR end_-begin_);
  parts:=regexp_match(field_,'^([A-Za-z][A-Za-z0-9_]*\s*)?(>=|<=|>|<|=|≥|≤)\s*([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\s*([%$€£]|[A-Za-z][A-Za-z0-9_/-]*)?$');
  IF parts IS NULL THEN CONTINUE;END IF;
  symbol:=nullif(btrim(parts[1]),'');op:=replace(replace(parts[2],'≥','>='),'≤','<=');value_:=data.decimal_canonical(parts[3]::numeric::text);unit_:=parts[4];
  fields:=fields||jsonb_build_array(jsonb_strip_nulls(jsonb_build_object('dimension','threshold_unit','lexical_value',field_,'evidence',jsonb_build_array(passage->>'passage_id'),
   'typed',jsonb_build_object('span',jsonb_build_object('passage_id',passage->>'passage_id','start',(passage->>'start')::integer+begin_,'end',(passage->>'start')::integer+end_,'text',field_),
   'grammar','threshold-lalr-1','state','parsed','value',value_,'comparator',op,'quantity',symbol,'unit',unit_))));
 END LOOP;
 RETURN CASE WHEN jsonb_array_length(fields)=1 THEN fields->0 ELSE NULL END;
END $$;
REVOKE ALL ON FUNCTION ops.structural_threshold_field(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_clause_fields(passage jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE raw text:=passage->>'text'; patterns text[]:=ARRAY['(?:^|[,;]\s*|\ythen\s+)(.+?)\s+(must|shall|should|may|can)\s+be\s+([A-Za-z]+)\s+by\s+([A-Za-z][A-Za-z0-9_-]*(?:\s+(?!(?:if|when|unless|except|before|after)\y)[A-Za-z][A-Za-z0-9_-]*){0,7})(?=\s+(?:if|when|unless|except|before|after)\y|\.(?=\s|$)|[;\n]|$)','(?:^|[,;]\s*|\ythen\s+)([A-Za-z][A-Za-z0-9_-]*(?:\s+(?!(?:if|when|unless|except|before|after)\y)[A-Za-z][A-Za-z0-9_-]*){0,7})\s+(must|shall|should|may|can)\s+((?!be\y)[A-Za-z]+)\s+((?:(?!\s+(?:if|when|unless|except|before|after)\y|\.(?=\s|$)|[;\n]).)+)(?=\s+(?:if|when|unless|except|before|after)\y|\.(?=\s|$)|[;\n]|$)'];
 pattern_ text; roles text[]; item record; n integer;g integer;a integer;b integer;d text;value_ jsonb;found jsonb:='{}';result jsonb:='{}';key_ text;threshold_ jsonb;
BEGIN
 FOR n IN 1..2 LOOP
  pattern_:=patterns[n];roles:=CASE n WHEN 1 THEN ARRAY['object','modality','action','actor'] ELSE ARRAY['actor','modality','action','object'] END;
  FOR item IN SELECT x.m,x.n::integer ordinal FROM regexp_matches(raw,pattern_,'gi') WITH ORDINALITY x(m,n) LOOP
   FOR g IN 1..4 LOOP
    d:=roles[g];a:=regexp_instr(raw,pattern_,1,item.ordinal,0,'i',g)-1;b:=regexp_instr(raw,pattern_,1,item.ordinal,1,'i',g)-1;
    WHILE a<b AND substring(raw FROM a+1 FOR 1)~'\s' LOOP a:=a+1;END LOOP;
    WHILE a<b AND substring(raw FROM b FOR 1)~'\s' LOOP b:=b-1;END LOOP;
    value_:=jsonb_build_object('dimension',d,'lexical_value',substring(raw FROM a+1 FOR b-a),'evidence',jsonb_build_array(passage->>'passage_id'),'span',jsonb_build_object('passage_id',passage->>'passage_id','start',(passage->>'start')::integer+a,'end',(passage->>'start')::integer+b,'text',substring(raw FROM a+1 FOR b-a)));
    found:=jsonb_set(found,ARRAY[d],COALESCE(found->d,'[]')||jsonb_build_array(value_));
   END LOOP;
  END LOOP;
 END LOOP;
 pattern_:='\y(if|when|provided(?:\s+that)?|unless|except(?:\s+(?:when|if))?|before|after)\s+((?:(?!,|\s+(?:unless|except|before|after)\y|\.(?=\s|$)|[;\n]).)+)';
 FOR item IN SELECT x.m,x.n::integer ordinal FROM regexp_matches(raw,pattern_,'gi') WITH ORDINALITY x(m,n) LOOP
  d:=CASE WHEN lower(item.m[1])~'^(unless|except)' THEN 'exception' WHEN lower(item.m[1]) IN ('before','after') THEN 'order_dependency' ELSE 'condition' END;
  a:=regexp_instr(raw,pattern_,1,item.ordinal,0,'i')-1;b:=regexp_instr(raw,pattern_,1,item.ordinal,1,'i')-1;
  WHILE a<b AND substring(raw FROM b FOR 1)~'\s' LOOP b:=b-1;END LOOP;
  value_:=jsonb_build_object('dimension',d,'lexical_value',substring(raw FROM a+1 FOR b-a),'evidence',jsonb_build_array(passage->>'passage_id'),'span',jsonb_build_object('passage_id',passage->>'passage_id','start',(passage->>'start')::integer+a,'end',(passage->>'start')::integer+b,'text',substring(raw FROM a+1 FOR b-a)));
  found:=jsonb_set(found,ARRAY[d],COALESCE(found->d,'[]')||jsonb_build_array(value_));
 END LOOP;
 FOR key_,value_ IN SELECT key,value FROM jsonb_each(found) LOOP IF jsonb_array_length(value_)=1 THEN result:=result||jsonb_build_object(key_,value_->0);END IF;END LOOP;
 FOREACH d IN ARRAY ARRAY['parent','version'] LOOP
  key_:=CASE d WHEN 'parent' THEN passage->>'parent' ELSE passage->>'effective_version' END;
  IF key_ IS NOT NULL AND key_<>'' THEN result:=result||jsonb_build_object(d,jsonb_build_object('dimension',d,'lexical_value',key_,'evidence',jsonb_build_array(passage->>'passage_id')));END IF;
 END LOOP;
 threshold_:=ops.structural_threshold_field(passage);IF threshold_ IS NOT NULL THEN result:=result||jsonb_build_object('threshold_unit',threshold_);END IF;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION ops.structural_clause_fields(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_comparison(inputs jsonb,left_id text,right_id text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE a jsonb;b jsonb;x jsonb;y jsonb;xf jsonb;yf jsonb;p jsonb;q jsonb;d text;dimensions jsonb:='[]';entry jsonb;typed text;reason text;removed jsonb;added jsonb;interval_ jsonb;lo jsonb;hi jsonb;av numeric;bv numeric;lower_side boolean;is_removed boolean;applicability text;why text;
BEGIN
 SELECT v INTO STRICT a FROM jsonb_array_elements(inputs->'passages')v WHERE v->>'passage_id'=left_id;
 SELECT v INTO STRICT b FROM jsonb_array_elements(inputs->'passages')v WHERE v->>'passage_id'=right_id;
 IF left_id=right_id THEN RAISE EXCEPTION 'comparison requires distinct passages' USING ERRCODE='23514';END IF;
 xf:=ops.structural_clause_fields(a);yf:=ops.structural_clause_fields(b);
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
    IF p->>'unit' IS NOT NULL AND q->>'unit' IS NOT NULL AND p->>'quantity' IS NOT NULL AND p->>'quantity'=q->>'quantity' AND p->>'unit'=q->>'unit' AND p->>'basis' IS NOT DISTINCT FROM q->>'basis' THEN
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
 IF a->>'scope' IS DISTINCT FROM b->>'scope' THEN applicability:='differently_scoped';why:='Original source scopes differ.';
 ELSIF a->>'effective_version' IS NULL OR b->>'effective_version' IS NULL THEN applicability:='unestablished';why:='Effective versions are not established.';
 ELSIF a->>'effective_version'<>b->>'effective_version' THEN applicability:='unestablished';why:='Different version labels do not establish succession or authority.';
 ELSIF NOT EXISTS(SELECT FROM unnest(ARRAY['actor','action','object','modality','condition','exception','order_dependency','parent','version']) dimension WHERE xf->dimension IS NULL OR yf->dimension IS NULL OR xf->dimension->>'lexical_value' IS DISTINCT FROM yf->dimension->>'lexical_value') THEN applicability:='co_applicable';why:='All non-threshold dimensions match under explicit scope/version.';
 ELSE applicability:='unestablished';why:='Missing or changed applicability dimensions remain material.';END IF;
 RETURN jsonb_build_object('left_id',left_id,'right_id',right_id,'dimensions',dimensions,'equivalence','not_asserted','identity_standing','not_asserted','applicability',applicability,'applicability_reason',why);
END $$;
REVOKE ALL ON FUNCTION ops.structural_comparison(jsonb,text,text) FROM PUBLIC;

-- Membership comes exclusively from authenticated current predecessor output roles.
-- Display selection has no authority to create a member or a supported facet.
CREATE OR REPLACE FUNCTION ops.structural_dossier(inputs jsonb,config jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE reference jsonb;retained jsonb;report jsonb;roles jsonb;role_ jsonb;c jsonb;r jsonb;d jsonb;side jsonb;span_ jsonb;p jsonb;assertion_ jsonb;expected_statement jsonb;assessment text;key_ text;member_ jsonb;members jsonb:='[]';facets jsonb:='[]';seen jsonb:='{}';selected jsonb:='[]';omitted jsonb;represented jsonb;missing jsonb;sections jsonb;budget integer:=(config->>'member_budget')::integer;mandatory integer;candidate record;membership_digest text;facet_digest text;representation jsonb;
BEGIN
 IF budget<1 OR config->>'policy' NOT IN ('supported-facet-greedy-1','source-order-control-1') OR jsonb_array_length(config->'predecessors')=0 THEN RAISE EXCEPTION 'invalid current dossier selection policy' USING ERRCODE='23514';END IF;
 IF (SELECT count(*)<>count(DISTINCT v->>'product_id') FROM jsonb_array_elements(config->'predecessors')v) THEN RAISE EXCEPTION 'duplicate dossier predecessor' USING ERRCODE='23514';END IF;
 FOR reference IN SELECT value FROM jsonb_array_elements(config->'predecessors') LOOP
  IF NOT inputs->'dependencies' ? (reference->>'product_id') THEN RAISE EXCEPTION 'dossier predecessor outside dependencies' USING ERRCODE='23514';END IF;
  retained:=ops.resolve_retained_structural_report(reference);report:=retained->'report';roles:='[]';
  IF EXISTS(SELECT FROM jsonb_array_elements(report->'inputs'->'passages') source_passage(value) WHERE NOT inputs->'passages' @> jsonb_build_array(source_passage.value)) THEN RAISE EXCEPTION 'dossier predecessor substitutes original passage' USING ERRCODE='23514';END IF;
  IF report->>'kind'='definition_components' THEN
   FOR c IN SELECT value FROM jsonb_array_elements(report->'definition_components'->'components') LOOP
    roles:=roles||jsonb_build_array(jsonb_build_object('role','terminology','span',c->'term','component_id',c->>'component_id'),jsonb_build_object('role','definition','span',c->'content','component_id',c->>'component_id'));
   END LOOP;
  ELSIF report->>'kind'='definition_applicability' THEN
   SELECT value INTO STRICT p FROM jsonb_array_elements(inputs->'passages') WHERE value->>'passage_id'=report->'definition'->>'usage_id';
   roles:=roles||jsonb_build_array(jsonb_build_object('role','usage','span',p-ARRAY['source_ref','scope','effective_version','parent']));
   FOR r IN SELECT value FROM jsonb_array_elements(report->'definition'->'readings') LOOP roles:=roles||jsonb_build_array(jsonb_build_object('role','definition','span',r->'component'->'content'));END LOOP;
  ELSIF report->>'kind'='qualified_comparison' THEN
   FOR d IN SELECT value FROM jsonb_array_elements(report->'comparison'->'dimensions') LOOP
    FOR side IN SELECT d->'left' UNION ALL SELECT d->'right' LOOP span_:=COALESCE(nullif(side->'span','null'),side->'typed'->'span');IF span_ IS NOT NULL AND span_<>'null' THEN roles:=roles||jsonb_build_array(jsonb_build_object('role',CASE WHEN d->>'dimension'='exception' THEN 'exception' ELSE 'variant' END,'span',span_));END IF;END LOOP;
   END LOOP;
  ELSE RAISE EXCEPTION 'dossier predecessors require finite current semantic products' USING ERRCODE='23514';END IF;
  FOR role_ IN SELECT value FROM jsonb_array_elements(roles) LOOP
   span_:=role_->'span';SELECT value INTO STRICT p FROM jsonb_array_elements(inputs->'passages') WHERE value->>'passage_id'=span_->>'passage_id';
   key_:=encode(sha256(convert_to(data.canonical_json(jsonb_build_object('product',reference->>'product_id','role',role_->>'role','citation',span_)),'UTF8')),'hex');
   IF seen ? key_ THEN CONTINUE;END IF;seen:=seen||jsonb_build_object(key_,true);assessment:=NULL;
   IF jsonb_array_length(retained->'public_assertions')>0 THEN
    expected_statement:=data.structural_public_statement(report,role_->>'component_id');
    SELECT a->>'assessment_id' INTO assessment FROM jsonb_array_elements(retained->'public_assertions')a WHERE a->'statement'=expected_statement AND nullif(a->>'assessment_id','') IS NOT NULL LIMIT 1;
   END IF;
   member_:=jsonb_strip_nulls(jsonb_build_object('member_id',key_,'passage_id',p->>'passage_id','citation',span_,'role',role_->>'role','sense','unresolved','scope',p->>'scope','effective_version',p->'effective_version','relation_product_id',reference->>'product_id','qualification',CASE WHEN assessment IS NULL THEN 'proposed' ELSE 'independently_supported' END,'assessment_id',assessment));
   members:=members||jsonb_build_array(member_);
   IF assessment IS NOT NULL THEN facets:=facets||jsonb_build_array(jsonb_build_object('facet_id',key_||':'||(role_->>'role'),'kind',(role_->>'role')||':'||(span_->>'text'),'scope',p->>'scope','member_id',key_,'assessment_id',assessment,'evidence',jsonb_build_array(p->>'passage_id')));END IF;
  END LOOP;
 END LOOP;
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
 RETURN jsonb_build_object('root_id',config->>'root_id','members',members,'predecessors',config->'predecessors','representatives',selected,'missing_sections',sections,'supported_facets',facets,'representation',representation,'membership_completeness','declared_selection');
END $$;
REVOKE ALL ON FUNCTION ops.structural_dossier(jsonb,jsonb) FROM PUBLIC;

-- Reconstruct the source cohort rather than trusting duplicated fields or caller IDs.
-- A named source container and exact current projection remain the source authority.
CREATE OR REPLACE FUNCTION ops.artifact_source_records(inputs jsonb,config jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_ jsonb; binding jsonb; view_ kb.source_view; piece jsonb; node jsonb;
 pin jsonb; anchor_ jsonb; artifact jsonb; value_ jsonb; contribution jsonb; citations jsonb;
 candidates jsonb:='[]'; match_ record; raw text; quote_ text; pointer_ text; source_ref text;
 local_start integer; local_end integer; global_start integer; global_end integer; caption boolean;
 pattern text:=E'(?i)\\m(Table|Figure|Theorem|Section)\\s+([A-Z]?\\d+(?:\\.\\d+)*[A-Za-z]?)';
BEGIN
 IF (SELECT count(*)<>count(DISTINCT wb->>'native_content_digest') FROM jsonb_array_elements(config->'work_bindings') wb) THEN
  RAISE EXCEPTION 'artifact source-work bindings repeat' USING ERRCODE='23514'; END IF;
 FOR source_ IN SELECT value FROM jsonb_array_elements(inputs->'sources') LOOP
  SELECT wb INTO binding FROM jsonb_array_elements(config->'work_bindings') wb
   WHERE wb->>'native_content_digest'=source_->>'native_content_digest';
  IF binding IS NULL THEN CONTINUE; END IF;
  SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
  source_ref:=encode(sha256(convert_to(data.canonical_json(source_),'UTF8')),'hex');
  pin:=jsonb_build_object('source',view_.key,'native_product_task_id',view_.native_task_id,
   'product_key',view_.native_product_key,'product_digest',view_.native_content_digest,
   'projection_digest',view_.projection_digest,'recipe_digest',view_.recipe_digest,'source_view_id',view_.id);
  FOR piece IN SELECT p FROM jsonb_array_elements(view_.projection->'pieces') p
   WHERE p->>'kind'='native_text' AND p->>'cell_index' IS NULL LOOP
   raw:=substring(view_.projection->>'text' FROM (piece->>'start')::integer+1
    FOR (piece->>'end')::integer-(piece->>'start')::integer);
   IF raw COLLATE pg_catalog.pg_unicode_fast !~ pattern THEN CONTINUE; END IF;
   pointer_:=piece->>'item_ref';
   SELECT native_json INTO STRICT node FROM ops.read_pdf_published_items(view_.native_task_id,
    view_.native_product_key,view_.native_content_digest,ARRAY[pointer_]);
   IF node->>'text' IS DISTINCT FROM raw THEN
    RAISE EXCEPTION 'artifact native field bridge differs from source projection' USING ERRCODE='23514'; END IF;
   caption:=node->>'label'='caption';
   FOR match_ IN SELECT parts,n::integer FROM regexp_matches(raw COLLATE pg_catalog.pg_unicode_fast,pattern,'g') WITH ORDINALITY m(parts,n) LOOP
    local_start:=regexp_instr(raw COLLATE pg_catalog.pg_unicode_fast,pattern,1,match_.n)-1;
    local_end:=regexp_instr(raw COLLATE pg_catalog.pg_unicode_fast,pattern,1,match_.n,1)-1;
    global_start:=(piece->>'start')::integer+local_start;
    global_end:=(piece->>'start')::integer+local_end;
    quote_:=substring(raw FROM local_start+1 FOR local_end-local_start);
    SELECT COALESCE(jsonb_agg(jsonb_build_object('source_ref',source_ref,
     'passage_id',p->>'passage_id','source_pointer',pointer_,'start',global_start,
     'end',global_end,'text',quote_) ORDER BY ordinal),'[]') INTO citations
    FROM jsonb_array_elements(inputs->'passages') WITH ORDINALITY selected(p,ordinal)
    WHERE p->>'source_ref'=source_ref AND (p->>'start')::integer<=global_start
     AND (p->>'end')::integer>=global_end;
    IF jsonb_array_length(citations)=0 THEN CONTINUE; END IF;
    artifact:=jsonb_strip_nulls(jsonb_build_object('protocol','source-artifact-occurrence-1',
     'artifact_kind',lower(match_.parts[1]),'source_work',binding->>'source_work',
     'controlled_code',match_.parts[2],
     'title',CASE WHEN caption THEN nullif(btrim(substring(raw FROM local_end+1),E' .:\n'),'') END,
     'aliases','[]'::jsonb,'revision_state','unknown',
     'occurrence_role',CASE WHEN caption THEN 'caption' ELSE 'reference' END,
     'scope',pointer_,'source_pointer',pointer_,
     'dependencies',jsonb_build_array('native:'||view_.native_task_id::text)));
    -- SourceValue retains the producer's declared field ordering, independently of JSONB order.
    SELECT jsonb_build_object('kind','object','fields',jsonb_agg(jsonb_build_object(
     'name',key,'position',position,'value',CASE WHEN jsonb_typeof(artifact->key)='array'
      THEN jsonb_build_object('kind','array','items',COALESCE((SELECT jsonb_agg(
       jsonb_build_object('kind','text','text',x) ORDER BY n)
       FROM jsonb_array_elements_text(artifact->key) WITH ORDINALITY a(x,n)),'[]'))
      ELSE jsonb_build_object('kind','text','text',artifact->key) END) ORDER BY position)) INTO value_
    FROM (SELECT key,(row_number() OVER(ORDER BY n)-1)::integer position FROM unnest(ARRAY[
     'protocol','artifact_kind','source_work','controlled_code','title','aliases','revision',
     'revision_state','occurrence_role','scope','source_pointer','dependencies']) WITH ORDINALITY f(key,n)
     WHERE artifact ? key) fields;
    anchor_:=jsonb_build_object('pin',pin,'space','native','pointer',pointer_,
     'precision','exact','start',local_start,'end',local_end,'source_piece',quote_);
    anchor_:=anchor_||jsonb_build_object('anchor_id','record-anchor:'||encode(sha256(convert_to(
     data.canonical_json(anchor_||jsonb_build_object('pin',pin-'source_view_id')),'UTF8')),'hex'));
    contribution:=jsonb_build_object('contract','RetainedContributionSemantics','kind','occurrence',
     'semantic_type','structural.artifact','operation_key','contribution-operation:'||encode(sha256(convert_to(
      data.canonical_json(jsonb_build_array(jsonb_build_array('structure.scoped_relations','1',pin),'{}'::jsonb)),'UTF8')),'hex'),
     'item_key',pointer_||':artifact_reference:'||global_start::text||':'||global_end::text,
     'pin',pin,'anchors',jsonb_build_array(anchor_),
     'occurrence_id',ops.source_contribution_occurrence(jsonb_build_array(anchor_)),
     'standing','retained_private','score_state','missing','disposition','located_proposal',
     'computation_dependencies',jsonb_build_array('native:'||view_.native_task_id::text),'value',value_);
    contribution:=contribution||jsonb_build_object('contribution_id','source-contribution:'||encode(sha256(
     convert_to(data.canonical_json(contribution),'UTF8')),'hex'));
    candidates:=candidates||jsonb_build_array(jsonb_build_object(
     'contribution_id',contribution->>'contribution_id','occurrence_id',contribution->>'occurrence_id',
     'artifact',artifact,'source_contribution',contribution,'citations',citations));
   END LOOP;
  END LOOP;
 END LOOP;
 RETURN (SELECT COALESCE(jsonb_agg(r ORDER BY r->>'contribution_id'),'[]') FROM (
  SELECT DISTINCT ON (r->>'occurrence_id',r->'artifact'->>'source_work',r->'artifact'->>'artifact_kind') r
  FROM jsonb_array_elements(candidates) r ORDER BY r->>'occurrence_id',r->'artifact'->>'source_work',
   r->'artifact'->>'artifact_kind',r->>'contribution_id') selected);
END $$;
REVOKE ALL ON FUNCTION ops.artifact_source_records(jsonb,jsonb) FROM PUBLIC;

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

CREATE OR REPLACE FUNCTION ops.validate_artifact_identity(inputs jsonb,config jsonb,product jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE expected_records jsonb; pair_ jsonb; a jsonb; b jsonb; routes jsonb; expected_pairs jsonb:='[]';
 code_a text; code_b text; title_a text; title_b text; compatible boolean; excluded boolean;
 lexical double precision; log_odds double precision; probability double precision; external_ boolean; policy jsonb;
 code_gamma integer; title_gamma integer; code_mw double precision; title_mw double precision;
 field_ jsonb; expected_value double precision; model_id text; expected_provenance jsonb; unbound jsonb; anchors jsonb;
 python_space text:=chr(9)||chr(10)||chr(11)||chr(12)||chr(13)||chr(28)||chr(29)||chr(30)||chr(31)||chr(32)||chr(133)||chr(160)||chr(5760)||chr(8192)||chr(8193)||chr(8194)||chr(8195)||chr(8196)||chr(8197)||chr(8198)||chr(8199)||chr(8200)||chr(8201)||chr(8202)||chr(8232)||chr(8233)||chr(8239)||chr(8287)||chr(12288);
BEGIN
 policy:=product->'policy';
 IF product->>'identity_grain' IS DISTINCT FROM 'source_work_artifact_lineage'
  OR jsonb_typeof(config->'title_threshold') IS DISTINCT FROM 'number'
  OR (config->>'title_threshold')::double precision<0 OR (config->>'title_threshold')::double precision>100
  OR jsonb_typeof(config->'work_bindings') IS DISTINCT FROM 'array'
  OR jsonb_typeof(config->'external_pairs') IS DISTINCT FROM 'array'
  OR jsonb_typeof(config->'exclusions') IS DISTINCT FROM 'array'
  OR NOT policy ?& ARRAY['prior','code_m','code_u','title_m','title_u'] OR product->>'protocol'<>'artifact-identity-1' OR product->>'standing'<>'candidate_relative_private'
  OR policy IS DISTINCT FROM config->'policy' OR EXISTS(SELECT FROM jsonb_each(policy) p
   WHERE (p.value#>>'{}')::double precision<=0 OR (p.value#>>'{}')::double precision>=1)
  OR (SELECT count(*) FROM jsonb_each(policy))<>5 THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 expected_records:=ops.artifact_source_records(inputs,config);
 IF jsonb_strip_nulls(product->'records') IS DISTINCT FROM expected_records THEN
  RAISE EXCEPTION 'artifact cohort/fields/content identities differ from exact source replay' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(DISTINCT wb->>'provenance' ORDER BY wb->>'provenance'),'[]') INTO expected_provenance
 FROM jsonb_array_elements(inputs->'sources') src JOIN LATERAL jsonb_array_elements(config->'work_bindings') wb
  ON wb->>'native_content_digest'=src->>'native_content_digest';
 SELECT COALESCE(jsonb_agg(src->'source_view_id' ORDER BY n),'[]') INTO unbound
 FROM jsonb_array_elements(inputs->'sources') WITH ORDINALITY s(src,n)
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(config->'work_bindings') wb WHERE wb->>'native_content_digest'=src->>'native_content_digest');
 IF COALESCE(product->'source_mapping_provenance','[]') IS DISTINCT FROM expected_provenance
  OR COALESCE(product->'unbound_source_ids','[]') IS DISTINCT FROM unbound
  OR COALESCE(product->'native_alias_pairs','[]')<>'[]'::jsonb THEN
  RAISE EXCEPTION 'artifact source mapping/unavailable/alias population differs' USING ERRCODE='23514'; END IF;
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
 FOR a,b IN SELECT left_,right_ FROM jsonb_array_elements(expected_records) left_,jsonb_array_elements(expected_records) right_
  WHERE left_->>'contribution_id'<right_->>'contribution_id' AND left_->>'occurrence_id'<>right_->>'occurrence_id' LOOP
  compatible:=(a->'artifact'->>'source_work'=b->'artifact'->>'source_work' AND a->'artifact'->>'artifact_kind'=b->'artifact'->>'artifact_kind');
  external_:=COALESCE(config->'external_pairs','[]') @> jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')) OR COALESCE(config->'external_pairs','[]') @> jsonb_build_array(jsonb_build_array(b->>'contribution_id',a->>'contribution_id'));
  IF NOT compatible AND NOT external_ THEN CONTINUE; END IF;
  code_a:=CASE WHEN btrim(a->'artifact'->>'controlled_code') COLLATE pg_catalog.pg_unicode_fast ~ '^[A-Za-z]?\d+([.\-]\d+)*[A-Za-z]?$' THEN lower(btrim(a->'artifact'->>'controlled_code')) END;
  code_b:=CASE WHEN btrim(b->'artifact'->>'controlled_code') COLLATE pg_catalog.pg_unicode_fast ~ '^[A-Za-z]?\d+([.\-]\d+)*[A-Za-z]?$' THEN lower(btrim(b->'artifact'->>'controlled_code')) END;
  lexical:=ops.artifact_lexical_score(a->'artifact'->>'title',b->'artifact'->>'title');routes:='[]';
  IF compatible AND code_a IS NOT NULL AND code_a=code_b THEN routes:=routes||'"exact_code"'::jsonb; END IF;
  IF compatible AND COALESCE(a->'artifact'->>'title','')<>'' AND COALESCE(b->'artifact'->>'title','')<>'' AND lexical*100 >=(config->>'title_threshold')::double precision THEN routes:=routes||'"lexical_title"'::jsonb; END IF;
  IF external_ THEN routes:=routes||'"external_pairs"'::jsonb; END IF;
  IF routes='[]'::jsonb THEN CONTINUE; END IF;
  expected_pairs:=expected_pairs||jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id'));
  SELECT p INTO STRICT pair_ FROM jsonb_array_elements(product->'pairs') p WHERE p->>'left'=a->>'contribution_id' AND p->>'right'=b->>'contribution_id';
  excluded:=NOT compatible OR (anchors ? (a->>'contribution_id') AND anchors ? (b->>'contribution_id')) OR COALESCE(config->'exclusions','[]') @> jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')) OR COALESCE(config->'exclusions','[]') @> jsonb_build_array(jsonb_build_array(b->>'contribution_id',a->>'contribution_id'));
  IF pair_->'candidate_routes' IS DISTINCT FROM routes OR pair_->>'standing'<>'candidate_relative_private'
   OR pair_->>'revision_relation'<>'unknown' OR pair_->>'scope_state' IS DISTINCT FROM (CASE WHEN excluded THEN 'excluded' ELSE 'compatible' END)
   OR abs((pair_->>'lexical_score')::double precision-lexical)>1e-12
   OR pair_->'dependencies' IS DISTINCT FROM (SELECT jsonb_agg(value ORDER BY value) FROM (SELECT DISTINCT value FROM jsonb_array_elements_text(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')||(a->'artifact'->'dependencies')||(b->'artifact'->'dependencies'))) d) THEN
   RAISE EXCEPTION 'artifact candidate route/scope/dependencies differ from exact frozen cohort' USING ERRCODE='23514'; END IF;
  IF excluded THEN
   IF pair_->>'model_probability' IS NOT NULL OR pair_->>'model_id' IS NOT NULL OR COALESCE(pair_->'model_evidence','[]')<>'[]'::jsonb THEN RAISE EXCEPTION 'excluded artifact pair carries a model score' USING ERRCODE='23514'; END IF;
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
 IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(config->'external_pairs','[]')||COALESCE(config->'exclusions','[]')) ep
  WHERE jsonb_array_length(ep)<>2 OR ep->>0=ep->>1 OR EXISTS(SELECT FROM jsonb_array_elements_text(ep) endpoint WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(expected_records) r WHERE r->>'contribution_id'=endpoint))) THEN
  RAISE EXCEPTION 'artifact configured pair endpoint lies outside source cohort' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'artifact candidate or source custody cannot resolve exact population' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_artifact_identity(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_structural_product_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; shape json; product jsonb; inputs jsonb; source_ jsonb; source_map jsonb:='{}'; passage jsonb; passage_map jsonb:='{}'; ref jsonb; v kb.source_view; identifier text; cited text; item jsonb; dimension jsonb; member jsonb; actual text[]; expected text[]; config_ jsonb; method_ text; introduction boolean; target_passage jsonb; premise jsonb; expected_state text; expected_outcome text; states text[];
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
 ELSIF method_ IN ('structure.definitions','structure.definition_components') THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs)
    OR product->>'kind' IS DISTINCT FROM (CASE method_ WHEN 'structure.definition_components' THEN 'definition_components' ELSE 'definition_applicability' END) THEN
   RAISE EXCEPTION 'definition report differs from frozen source/question input' USING ERRCODE='23514'; END IF;
 ELSIF method_='structure.artifact_identity' THEN
  IF jsonb_strip_nulls(config_->'inputs') IS DISTINCT FROM jsonb_strip_nulls(inputs) OR product->>'kind'<>'artifact_identity' THEN
   RAISE EXCEPTION 'artifact identity differs from exact selected source inputs' USING ERRCODE='23514'; END IF;
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
  +CASE WHEN nullif(product->'definition_components','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'artifact_identity','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END)<>1 THEN
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
    IF method_='structure.definition_components' AND NOT config_->'target_ids' ? (ref->>'passage_id') THEN RAISE EXCEPTION 'definition span is outside inspected target selection' USING ERRCODE='23514'; END IF;
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
  PERFORM ops.validate_artifact_identity(inputs,config_,product->'artifact_identity');
 WHEN 'qualified_comparison' THEN
  IF method_ IS DISTINCT FROM 'structure.compare' OR jsonb_strip_nulls(product->'comparison') IS DISTINCT FROM
    ops.structural_comparison(inputs,config_->>'left_id',config_->>'right_id') THEN
   RAISE EXCEPTION 'comparison differs from automatic exact source-field replay' USING ERRCODE='23514'; END IF;
 WHEN 'dossier' THEN
  IF method_ IS DISTINCT FROM 'structure.dossier' OR jsonb_strip_nulls(product->'dossier') IS DISTINCT FROM
    ops.structural_dossier(inputs,config_) THEN
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
