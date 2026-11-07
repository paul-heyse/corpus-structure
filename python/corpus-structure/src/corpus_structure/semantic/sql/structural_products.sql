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

-- Current deterministic source-field route replay. SQL token positions are character
-- positions, matching Python projected string offsets (never byte offsets).
CREATE OR REPLACE FUNCTION ops.structural_threshold_field(passage jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE pattern text:='>=|<=|>|<|=|≥|≤|[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[^\W\d][\w.-]*|[^\s]';
 raw text:=passage->>'text'; tokens jsonb:='[]'; item record; i integer; begin_ integer; end_ integer; field_ text; parts text[]; fields jsonb:='[]'; symbol text; op text; value_ text; unit_ text; basis_pattern text:='^Comparison basis:[ \t]*([^\n\r.]+?)[ \t]*\.?[ \t]*$'; basis_ text; witness jsonb;
BEGIN
 IF (SELECT count(*) FROM regexp_matches(raw,basis_pattern,'gn'))=1 THEN
  basis_:=nullif(btrim((regexp_match(raw,basis_pattern,'n'))[1],E' \t'),'');
  begin_:=regexp_instr(raw,basis_pattern,1,1,0,'n')-1;
  end_:=regexp_instr(raw,basis_pattern,1,1,1,'n')-1;
  IF basis_ IS NOT NULL THEN witness:=jsonb_build_object('passage_id',passage->>'passage_id','start',(passage->>'start')::integer+begin_,'end',(passage->>'start')::integer+end_,'text',substring(raw FROM begin_+1 FOR end_-begin_)); END IF;
 END IF;
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
   'grammar','threshold-lalr-1','state','parsed','value',value_,'comparator',op,'quantity',symbol,'unit',unit_,'basis',basis_,'basis_evidence',witness))));
 END LOOP;
 RETURN fields;
END $$;
REVOKE ALL ON FUNCTION ops.structural_threshold_field(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_compare_lexical(inputs jsonb,left_id text,right_id text,xf jsonb,yf jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE a jsonb;b jsonb;x jsonb;y jsonb;p jsonb;q jsonb;d text;dimensions jsonb:='[]';entry jsonb;typed text;reason text;removed jsonb;added jsonb;interval_ jsonb;lo jsonb;hi jsonb;av numeric;bv numeric;lower_side boolean;is_removed boolean;applicability text;why text;newer jsonb;older jsonb;w record;succession jsonb;witnesses integer:=0;start_ integer;end_ integer;pattern_ text:='^Revision ([A-Za-z0-9_-]+) supersedes revision ([A-Za-z0-9_-]+)\.[ \t]*$';
 old_pattern text:='^Revision ([A-Za-z0-9_-]+)\.[ \t]*$'; lineage_pattern text:='^Clause ([A-Za-z0-9_-]+)\.[ \t]*$'; old_start integer;old_end integer;
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
 IF a->>'scope'=b->>'scope' AND a->>'source_ref'=b->>'source_ref'
  AND ((a->>'end')::integer<=(b->>'start')::integer OR (b->>'end')::integer<=(a->>'start')::integer)
  AND nullif(a->>'parent','') IS NOT NULL AND a->>'parent'=b->>'parent'
  AND (SELECT array_agg(m[1]) FROM regexp_matches(a->>'text',lineage_pattern,'gn') m)=ARRAY[a->>'parent']
  AND (SELECT array_agg(m[1]) FROM regexp_matches(b->>'text',lineage_pattern,'gn') m)=ARRAY[a->>'parent']
  AND a->>'effective_version'<>b->>'effective_version' THEN
  FOR newer,older IN SELECT a,b UNION ALL SELECT b,a LOOP
   IF (SELECT array_agg(m[1]) FROM regexp_matches(older->>'text',old_pattern,'gn') m)
    IS DISTINCT FROM ARRAY[older->>'effective_version'] THEN CONTINUE; END IF;
   old_start:=regexp_instr(older->>'text',old_pattern,1,1,0,'n')-1;
   old_end:=regexp_instr(older->>'text',old_pattern,1,1,1,'n')-1;
   FOR w IN SELECT m,n::integer FROM regexp_matches(newer->>'text',pattern_,'gn') WITH ORDINALITY x(m,n) LOOP
    IF w.m[1]=newer->>'effective_version' AND w.m[2]=older->>'effective_version' THEN
     witnesses:=witnesses+1;
     start_:=regexp_instr(newer->>'text',pattern_,1,w.n,0,'n')-1;
     end_:=regexp_instr(newer->>'text',pattern_,1,w.n,1,'n')-1;
     succession:=jsonb_build_object('older_id',older->>'passage_id','newer_id',newer->>'passage_id',
      'evidence',jsonb_build_object('passage_id',newer->>'passage_id','start',(newer->>'start')::integer+start_,'end',(newer->>'start')::integer+end_,'text',substring(newer->>'text' FROM start_+1 FOR end_-start_)),
      'older_evidence',jsonb_build_object('passage_id',older->>'passage_id','start',(older->>'start')::integer+old_start,'end',(older->>'start')::integer+old_end,'text',substring(older->>'text' FROM old_start+1 FOR old_end-old_start)));
    END IF;
   END LOOP;
  END LOOP;
 END IF;
 IF a->>'scope' IS DISTINCT FROM b->>'scope' THEN applicability:='differently_scoped';why:='Original source scopes differ.';
 ELSIF witnesses=1 THEN applicability:='successive_revisions';why:='Exact source text establishes succession.';
 ELSIF a->>'effective_version' IS NULL OR b->>'effective_version' IS NULL THEN applicability:='unestablished';why:='Effective versions are not established.';
 ELSIF a->>'effective_version'<>b->>'effective_version' THEN applicability:='unestablished';why:='Different version labels do not establish succession or authority.';
 ELSIF NOT EXISTS(SELECT FROM unnest(ARRAY['actor','action','object','modality','condition','exception','order_dependency','parent','version']) dimension WHERE xf->dimension IS NULL OR yf->dimension IS NULL OR xf->dimension->>'lexical_value' IS DISTINCT FROM yf->dimension->>'lexical_value') THEN applicability:='co_applicable';why:='All non-threshold dimensions match under explicit scope/version.';
 ELSE applicability:='unestablished';why:='Missing or changed applicability dimensions remain material.';END IF;
 RETURN jsonb_build_object('left_id',left_id,'right_id',right_id,'dimensions',dimensions,'equivalence','not_asserted','identity_standing','not_asserted','applicability',applicability,'applicability_reason',why)||CASE WHEN witnesses=1 THEN jsonb_build_object('succession',succession) ELSE '{}'::jsonb END;
END $$;
REVOKE ALL ON FUNCTION ops.structural_compare_lexical(jsonb,text,text,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_literal(literal text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE m text[]; a numeric; b numeric; lower_closed boolean;upper_closed boolean;
 number_pattern text:='([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)';
 unit_pattern text:='([%$€£]|[A-Za-z][A-Za-z0-9_/-]*)';
BEGIN
 IF length(literal)>256 THEN RETURN NULL; END IF;
 m:=regexp_match(literal,'^\s*Date:\s*([0-9]{4})-([0-9]{2})-([0-9]{2})\s*$');
 IF m IS NOT NULL THEN
  IF m[1]='0000' THEN RETURN NULL;END IF;
  PERFORM make_date(m[1]::integer,m[2]::integer,m[3]::integer);
  RETURN jsonb_build_object('kind','date','value',m[1]||'-'||m[2]||'-'||m[3]);
 END IF;
 m:=regexp_match(literal,'^\s*Identifier:\s*([A-Za-z][A-Za-z0-9_.-]*)\s*$');
 IF m IS NOT NULL THEN RETURN jsonb_build_object('kind','identifier','value',m[1]);END IF;
 m:=regexp_match(literal,'^\s*Quantity:\s*'||number_pattern||'\s*'||unit_pattern||'\s*$');
 IF m IS NOT NULL THEN
  a:=m[1]::numeric;
  IF a<>0 AND (abs(a)<1e-100 OR abs(a)>=1e101) THEN RETURN NULL;END IF;
  RETURN jsonb_build_object('kind','quantity','value',data.decimal_canonical(a::text),'unit',m[2]);
 END IF;
 m:=regexp_match(literal,'^\s*Range:\s*([\[(])\s*'||number_pattern||'\s*,\s*'||number_pattern||'\s*([\])])\s*'||unit_pattern||'\s*$');
 IF m IS NULL THEN RETURN NULL;END IF;
 a:=m[2]::numeric;b:=m[3]::numeric;lower_closed:=m[1]='[';upper_closed:=m[4]=']';
 IF (a<>0 AND (abs(a)<1e-100 OR abs(a)>=1e101)) OR (b<>0 AND (abs(b)<1e-100 OR abs(b)>=1e101))
  OR a>b OR (a=b AND NOT (lower_closed AND upper_closed)) THEN RETURN NULL;END IF;
 RETURN jsonb_build_object('kind','range','lower',data.decimal_canonical(a::text),'upper',data.decimal_canonical(b::text),
  'lower_closed',lower_closed,'upper_closed',upper_closed,'unit',m[5]);
EXCEPTION WHEN datetime_field_overflow OR numeric_value_out_of_range OR invalid_text_representation THEN RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION ops.comparison_literal(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_member(passage jsonb,dimension text,extents jsonb,contribution text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
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
  'literal',CASE WHEN cardinality(literal)=1 THEN ops.comparison_literal(literal[1]) END));
END $$;
REVOKE ALL ON FUNCTION ops.comparison_member(jsonb,text,jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.comparison_groups(passage jsonb,source_ jsonb,ref jsonb,rows_ jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE reading jsonb;frame jsonb;component jsonb;pin jsonb;item jsonb;cue jsonb;dimension text;field_ jsonb;
 incomplete text[]:='{}';fields jsonb:='{}';controls jsonb:='[]';groups jsonb:='{}';members jsonb;state text;
 grouping text;witnesses jsonb;previous jsonb;lo integer;hi integer;gap text;marker text;word text;label text;focus jsonb;empty_ jsonb;
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
  field_:=ops.comparison_member(passage,dimension,item->'extents',item->>'contribution');
  IF field_ IS NOT NULL THEN fields:=jsonb_set(fields,ARRAY[dimension],COALESCE(fields->dimension,'[]')||jsonb_build_array(field_));END IF;
  IF field_ IS NULL OR item->>'outcome' IS DISTINCT FROM 'complete' THEN incomplete:=array_append(incomplete,dimension);END IF;
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
  field_:=ops.comparison_member(passage,dimension,cue->'component'->'extents',item->>'contribution_id');
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
 FOR field_ IN SELECT v FROM jsonb_array_elements(ops.structural_threshold_field(passage)) v LOOP
  IF EXISTS(SELECT FROM jsonb_array_elements(controls) c
   WHERE (c->>'start')::integer<=(field_->'typed'->'span'->>'start')::integer
    AND (c->>'end')::integer>=(field_->'typed'->'span'->>'end')::integer) THEN
   fields:=jsonb_set(fields,ARRAY['threshold_unit'],COALESCE(fields->'threshold_unit','[]')||jsonb_build_array(field_));
  END IF;
 END LOOP;
 FOREACH dimension IN ARRAY ARRAY['actor','action','object','modality','condition','threshold_unit','exception','order_dependency','parent','version'] LOOP
  SELECT COALESCE(jsonb_agg(m ORDER BY COALESCE(m->'spans'->0->>'start',m->'typed'->'span'->>'start')::integer,m->>'contribution_id'),'[]')
   INTO members FROM jsonb_array_elements(COALESCE(fields->dimension,'[]')) m;
  witnesses:='[]';grouping:=NULL;
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
     gap:=substring(passage->>'text' FROM lo-(passage->>'start')::integer+1 FOR hi-lo);
     word:=regexp_replace(gap,'^[[:space:]]+|[[:space:]]+$','','g');
     IF lower(word) NOT IN ('and','or') OR (marker IS NOT NULL AND marker<>lower(word)) THEN witnesses:='[]';EXIT;END IF;
     marker:=lower(word);lo:=lo+position(word in gap)-1;
     witnesses:=witnesses||jsonb_build_array(jsonb_build_object('passage_id',passage->>'passage_id','start',lo,'end',lo+length(word),'text',word));
    END IF;
    previous:=item;
   END LOOP;
   IF jsonb_array_length(witnesses)=jsonb_array_length(members)-1 THEN grouping:=CASE marker WHEN 'and' THEN 'conjunction' ELSE 'disjunction' END;END IF;
  END IF;
  groups:=jsonb_set(groups,ARRAY[dimension],jsonb_strip_nulls(jsonb_build_object('state',state,'grouping',grouping,'members',members,'witnesses',witnesses)));
 END LOOP;
 IF jsonb_array_length(groups->'exception'->'members')=0 OR
  (jsonb_array_length(groups->'exception'->'members')=1 AND jsonb_array_length(groups->'exception'->'members'->0->'spans')=1) THEN
  SELECT jsonb_agg(v) INTO empty_ FROM (
   SELECT v FROM jsonb_array_elements(COALESCE(groups->'exception'->'members'->0->'spans','[]')) v
   UNION ALL SELECT ops.comparison_member(passage,'exception',jsonb_build_array(focus),NULL)->'spans'->0 WHERE focus IS NOT NULL
  ) spans WHERE lower(rtrim(regexp_replace(v->>'text','^[[:space:]]+|[[:space:]]+$','','g'),'.')) IN ('no exceptions','exceptions: none');
  IF jsonb_array_length(empty_)=1 THEN
   groups:=jsonb_set(groups,ARRAY['exception'],jsonb_build_object('state','empty','members','[]'::jsonb,'witnesses',empty_));
  END IF;
 END IF;
 IF jsonb_array_length(groups->'threshold_unit'->'members')>0 AND
  'unresolved' IN (groups->'condition'->>'state',groups->'condition'->>'grouping') THEN
  groups:=jsonb_set(groups,ARRAY['threshold_unit'],(groups->'threshold_unit')||jsonb_build_object('state','unresolved','grouping','unresolved','witnesses','[]'::jsonb));
 END IF;
 RETURN groups;
END $$;
REVOKE ALL ON FUNCTION ops.comparison_groups(jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.structural_grouped_comparison(inputs jsonb,config jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE refs jsonb:=jsonb_build_array(config->'left_reading',config->'right_reading'); retained record;
 left_ jsonb;right_ jsonb;source_ jsonb;lg jsonb;rg jsonb;l jsonb;r jsonb;dim text;
 xf jsonb:='{}';yf jsonb:='{}';out_ jsonb;dims jsonb:='[]';entry jsonb;lexical text;
 compatible boolean;all_match boolean:=true;
BEGIN
 SELECT p INTO STRICT left_ FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'passage_id'=config->>'left_id';
 SELECT p INTO STRICT right_ FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'passage_id'=config->>'right_id';
 IF left_=right_ OR refs->0=refs->1 THEN RAISE EXCEPTION 'comparison requires distinct retained readings' USING ERRCODE='23514'; END IF;
 FOR retained IN SELECT * FROM ops.resolve_retained_source_contributions(refs) LOOP
  IF NOT inputs->'dependencies' ? (retained.reference->>'contribution_id') THEN
   RAISE EXCEPTION 'comparison lacks frozen retained reading dependency' USING ERRCODE='23514';END IF;
  IF retained.reference=refs->0 THEN
   SELECT s INTO STRICT source_ FROM jsonb_array_elements(inputs->'sources') s
    WHERE encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')=left_->>'source_ref';
   lg:=ops.comparison_groups(left_,source_,retained.reference,retained.contributions);
  ELSE
   SELECT s INTO STRICT source_ FROM jsonb_array_elements(inputs->'sources') s
    WHERE encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')=right_->>'source_ref';
   rg:=ops.comparison_groups(right_,source_,retained.reference,retained.contributions);
  END IF;
 END LOOP;
 IF lg IS NULL OR rg IS NULL THEN RAISE EXCEPTION 'comparison lacks both retained readings' USING ERRCODE='23514';END IF;
 FOR dim IN SELECT key FROM jsonb_each(lg) LOOP
  IF lg->dim->>'grouping'='singleton' THEN xf:=jsonb_set(xf,ARRAY[dim],lg->dim->'members'->0);END IF;
  IF rg->dim->>'grouping'='singleton' THEN yf:=jsonb_set(yf,ARRAY[dim],rg->dim->'members'->0);END IF;
 END LOOP;
 out_:=ops.structural_compare_lexical(inputs,config->>'left_id',config->>'right_id',xf,yf);
 compatible:=left_->>'scope'=right_->>'scope' AND (left_->>'effective_version' IS NOT DISTINCT FROM right_->>'effective_version' OR out_ ? 'succession');
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
  IF dim<>'threshold_unit' AND (lexical<>'same_lexical_value' OR l->>'grouping' IS DISTINCT FROM r->>'grouping' OR l->>'grouping'='unresolved') THEN all_match:=false;END IF;
  dims:=dims||jsonb_build_array((entry-ARRAY['left','right'])||jsonb_build_object('outcome',lexical,'left_group',l,'right_group',r));
 END LOOP;
 IF out_->>'applicability' NOT IN ('differently_scoped','successive_revisions')
  AND left_->>'effective_version' IS NOT NULL AND left_->>'effective_version'=right_->>'effective_version' THEN
  out_:=out_||CASE WHEN all_match THEN jsonb_build_object('applicability','co_applicable','applicability_reason','All non-threshold dimensions match under explicit scope/version.')
   ELSE jsonb_build_object('applicability','unestablished','applicability_reason','Missing or changed applicability dimensions remain material.') END;
 END IF;
 RETURN out_||jsonb_build_object('dimensions',dims,'left_reading',refs->0,'right_reading',refs->1);
END $$;
REVOKE ALL ON FUNCTION ops.structural_grouped_comparison(jsonb,jsonb) FROM PUBLIC;

-- Membership comes exclusively from authenticated current predecessor output roles.
-- Display selection has no authority to create a member or a supported facet.
CREATE OR REPLACE FUNCTION ops.dossier_comparison_roles(reference jsonb,report jsonb,selection_ jsonb,relationship jsonb,root_ref jsonb,root_ jsonb)
RETURNS SETOF jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE comparison jsonb:=jsonb_strip_nulls(report->'comparison');side_ text:=selection_->>'side';opposite_side text;
 passage jsonb;opposite jsonb;source_ jsonb;opposite_source jsonb;citation jsonb;opposite_citation jsonb;
 occurrence jsonb;binding jsonb;role_span jsonb;exception_group jsonb;
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
 SELECT jsonb_agg(span||jsonb_build_object('passage_id',passage->>'passage_id') ORDER BY n) INTO occurrence
 FROM jsonb_array_elements(relationship->'located_occurrence') WITH ORDINALITY spans(span,n);
 citation:=passage-ARRAY['source_ref','scope','effective_version','parent'];
 opposite_citation:=opposite-ARRAY['source_ref','scope','effective_version','parent'];
 binding:=jsonb_build_object('comparison_ref',reference,'side',side_,'relationship_ref',selection_->'relationship_ref',
  'relationship',relationship->'edge'->'relation','root',root_ref,'source',source_,'citation',citation,
  'occurrence',occurrence,'comparison',comparison,'opposite_source',opposite_source,'opposite_citation',opposite_citation);
 IF comparison->'succession'->'newer_id'=passage->'passage_id' THEN
  RETURN NEXT jsonb_build_object('role','revision','span',comparison->'succession'->'evidence','comparison_binding',binding); END IF;
 SELECT d->(side_||'_group') INTO exception_group FROM jsonb_array_elements(comparison->'dimensions') d WHERE d->>'dimension'='exception';
 IF relationship->'edge'->>'relation'='specializes' AND exception_group->>'state'='present' THEN
  FOR role_span IN SELECT span FROM jsonb_array_elements(exception_group->'members') field
   CROSS JOIN LATERAL jsonb_array_elements(field->'spans') span LOOP
   RETURN NEXT jsonb_build_object('role','exception','span',role_span,'comparison_binding',binding);
  END LOOP;
 END IF;
 IF comparison->>'applicability'='co_applicable' AND EXISTS(
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
     reference,report,binding_,relationships->relationship_key,root_ref,root_)bound_role;
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
   IF assessment IS NOT NULL AND (NOT role_ ? 'comparison_binding' OR role_->>'role'<>'relationship') THEN
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

CREATE OR REPLACE FUNCTION ops.artifact_alias_fields(raw text,artifact_end integer,pointer_ text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE alias_re text:='^\s*\((?:alias:|also called|also known as)\s*"([^"\r\n]+)"\s*\)';
 absent_re text:='^\s*\((aliases:\s*none)\s*\)';
 cursor_ integer:=artifact_end; start_ integer; end_ integer; matched text[];
 remaining text; aliases jsonb:='[]'; spans jsonb:='[]';
BEGIN
 LOOP
  remaining:=substring(raw FROM cursor_+1);
  matched:=regexp_match(remaining COLLATE pg_catalog.pg_c_utf8,alias_re,'i');
  EXIT WHEN matched IS NULL OR matched[1]~'^[[:space:]]*$';
  start_:=cursor_+regexp_instr(remaining COLLATE pg_catalog.pg_c_utf8,alias_re,1,1,0,'i',1)-1;
  end_:=start_+char_length(matched[1]);
  aliases:=aliases||jsonb_build_array(matched[1]);
  spans:=spans||jsonb_build_array(jsonb_build_object('source_pointer',pointer_,'start',start_,'end',end_,'text',matched[1]));
  cursor_:=cursor_+regexp_instr(remaining COLLATE pg_catalog.pg_c_utf8,alias_re,1,1,1,'i')-1;
 END LOOP;
 IF jsonb_array_length(spans)>0 THEN
  RETURN jsonb_build_object('aliases',aliases,'alias_state','observed','alias_occurrences',spans);END IF;
 remaining:=substring(raw FROM artifact_end+1);
 matched:=regexp_match(remaining COLLATE pg_catalog.pg_c_utf8,absent_re,'i');
 IF matched IS NOT NULL THEN
  start_:=artifact_end+regexp_instr(remaining COLLATE pg_catalog.pg_c_utf8,absent_re,1,1,0,'i',1)-1;
  RETURN jsonb_build_object('aliases','[]'::jsonb,'alias_state','known_empty','alias_occurrences','[]'::jsonb,
   'alias_absence',jsonb_build_object('source_pointer',pointer_,'start',start_,'end',start_+char_length(matched[1]),'text',matched[1]));
 END IF;
 RETURN jsonb_build_object('aliases','[]'::jsonb,'alias_state','unknown','alias_occurrences','[]'::jsonb);
END $$;
REVOKE ALL ON FUNCTION ops.artifact_alias_fields(text,integer,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_alias_span_source_value(span jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('kind','object','fields',jsonb_build_array(
  jsonb_build_object('name','source_pointer','position',0,'value',jsonb_build_object('kind','text','text',span->'source_pointer')),
  jsonb_build_object('name','start','position',1,'value',jsonb_build_object('kind','integer','integer',span->'start')),
  jsonb_build_object('name','end','position',2,'value',jsonb_build_object('kind','integer','integer',span->'end')),
  jsonb_build_object('name','text','position',3,'value',jsonb_build_object('kind','text','text',span->'text'))))
$$;
REVOKE ALL ON FUNCTION ops.artifact_alias_span_source_value(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_source_labels(raw text,artifact_end integer,pointer_ text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE label_re text:=E'^[[:space:]]*\\((numbering namespace|revision):[ \t]*([A-Za-z0-9][A-Za-z0-9_.-]*)\\)';
 cursor_ integer:=artifact_end;start_ integer;matched text[];remaining text;
 kind_ text;value_ text;label_count integer;evidence jsonb;
 numbering jsonb:='[]';revisions jsonb:='[]';result_ jsonb:='{}';span_ jsonb;
BEGIN
 LOOP
  remaining:=substring(raw FROM cursor_+1);
  matched:=regexp_match(remaining COLLATE "C",label_re);
  EXIT WHEN matched IS NULL;
  start_:=cursor_+regexp_instr(remaining COLLATE "C",label_re,1,1,0,'',2)-1;
  span_:=jsonb_build_object('source_pointer',pointer_,'start',start_,
   'end',start_+char_length(matched[2]),'text',matched[2]);
  IF matched[1]='revision' THEN revisions:=revisions||jsonb_build_array(span_);
  ELSE numbering:=numbering||jsonb_build_array(span_);END IF;
  cursor_:=cursor_+regexp_instr(remaining COLLATE "C",label_re,1,1,1)-1;
 END LOOP;
 FOR kind_,evidence IN SELECT 'numbering',numbering UNION ALL SELECT 'revision',revisions LOOP
  SELECT count(DISTINCT e->>'text'),min(e->>'text') INTO label_count,value_
  FROM jsonb_array_elements(evidence) e;
  result_:=result_||jsonb_build_object(kind_,jsonb_strip_nulls(jsonb_build_object(
   'state',CASE label_count WHEN 0 THEN 'unknown' WHEN 1 THEN 'observed' ELSE 'unresolved' END,
   'value',CASE WHEN label_count=1 THEN value_ END,'evidence',evidence)));
 END LOOP;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.artifact_source_labels(text,integer,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_explicit_reference(
 raw text,artifact_start integer,artifact_end integer,pointer_ text,kind_ text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE target_re text:=E'^[ \t]+\\((?:hereafter|also published as|also cited as)[ \t]+(Table|Figure)[ \t]+([A-Za-z]?[0-9]+(?:[.-][0-9]+)*[A-Za-z]?)[ \t]+in numbering namespace[ \t]+([A-Za-z0-9][A-Za-z0-9_.-]*)\\)(?=\\.|$)';
 remainder_ text;matched text[];end_ integer;
BEGIN
 IF left(raw,artifact_start) COLLATE "C" !~* E'^[ \t]*(?:See|Consult)[ \t]+$' THEN RETURN NULL; END IF;
 remainder_:=substring(raw FROM artifact_end+1);
 matched:=regexp_match(remainder_ COLLATE "C",target_re,'i');
 IF matched IS NULL OR lower(matched[1])<>kind_ THEN RETURN NULL; END IF;
 end_:=artifact_end+regexp_instr(remainder_ COLLATE "C",target_re,1,1,1,'i')-1;
 RETURN jsonb_build_object('target_code',matched[2],'target_numbering',matched[3],
  'cue',jsonb_build_object('source_pointer',pointer_,'start',0,'end',end_,'text',left(raw,end_)));
END $$;
REVOKE ALL ON FUNCTION ops.artifact_explicit_reference(text,integer,integer,text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.artifact_label_relation(a jsonb,b jsonb)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT CASE WHEN 'unresolved' IN (a->>'state',b->>'state') THEN 'unresolved'
 WHEN a->>'value' IS NULL OR b->>'value' IS NULL THEN 'unknown'
 WHEN a->>'value'=b->>'value' THEN 'same_observed' ELSE 'different_observed' END
$$;
REVOKE ALL ON FUNCTION ops.artifact_label_relation(jsonb,jsonb) FROM PUBLIC;

-- Reconstruct the source cohort rather than trusting duplicated fields or caller IDs.
-- A named source container and exact current projection remain the source authority.
CREATE OR REPLACE FUNCTION ops.artifact_source_records(inputs jsonb,config jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_ jsonb; binding jsonb; view_ kb.source_view; piece jsonb; node jsonb;
 pin jsonb; anchor_ jsonb; artifact jsonb; value_ jsonb; contribution jsonb; citations jsonb;
 candidates jsonb:='[]'; match_ record; raw text; quote_ text; pointer_ text; source_ref text;
 local_start integer; local_end integer; global_start integer; global_end integer; caption boolean;
 explicit_ jsonb;
 pattern text:=E'(?i)\\m(Table|Figure|Theorem|Section)\\s+([A-Z]?\\d[\\w./-]*)';
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
    IF right(match_.parts[2],1)='.' THEN
     match_.parts[2]:=left(match_.parts[2],-1);local_end:=local_end-1;END IF;
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
    explicit_:=CASE WHEN NOT caption THEN ops.artifact_explicit_reference(
     raw,local_start,local_end,pointer_,lower(match_.parts[1])) END;
    IF explicit_ IS NOT NULL AND NOT EXISTS(SELECT FROM jsonb_array_elements(inputs->'passages') p
     WHERE p->>'source_ref'=source_ref AND (p->>'start')::integer<=(piece->>'start')::integer
      AND (p->>'end')::integer>=(piece->>'start')::integer+(explicit_->'cue'->>'end')::integer) THEN
     explicit_:=NULL;
    END IF;
    artifact:=jsonb_strip_nulls(jsonb_build_object('protocol','source-artifact-occurrence-2',
     'artifact_kind',lower(match_.parts[1]),'source_work',binding->>'source_work',
     'controlled_code',match_.parts[2],
     'title',CASE WHEN caption THEN nullif(btrim(substring(raw FROM local_end+1),E' .:\n'),'') END,
     'revision_state','unknown',
     'occurrence_role',CASE WHEN caption THEN 'caption' ELSE 'reference' END,
     'scope',pointer_,'source_pointer',pointer_,
     'dependencies',jsonb_build_array('native:'||view_.native_task_id::text)))
     ||ops.artifact_alias_fields(raw,local_end,pointer_);
    -- SourceValue retains the producer's declared field ordering, independently of JSONB order.
    SELECT jsonb_build_object('kind','object','fields',jsonb_agg(jsonb_build_object(
     'name',key,'position',position,'value',CASE
      WHEN key='alias_absence' THEN ops.artifact_alias_span_source_value(artifact->key)
      WHEN jsonb_typeof(artifact->key)='array' THEN jsonb_build_object('kind','array','items',COALESCE((SELECT jsonb_agg(
       CASE WHEN key='alias_occurrences' THEN ops.artifact_alias_span_source_value(x)
        ELSE jsonb_build_object('kind','text','text',x) END ORDER BY n)
       FROM jsonb_array_elements(artifact->key) WITH ORDINALITY a(x,n)),'[]'))
      ELSE jsonb_build_object('kind','text','text',artifact->key) END) ORDER BY position)) INTO value_
    FROM (SELECT key,(row_number() OVER(ORDER BY n)-1)::integer position FROM unnest(ARRAY[
     'protocol','artifact_kind','source_work','controlled_code','title','aliases','alias_state','alias_occurrences','alias_absence','revision',
     'revision_state','occurrence_role','scope','source_pointer','dependencies']) WITH ORDINALITY f(key,n)
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
     'artifact',artifact,'source_contribution',contribution,'citations',citations)
     ||ops.artifact_source_labels(raw,local_end,pointer_)
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

CREATE OR REPLACE FUNCTION ops.artifact_external_nominations(inputs jsonb,config jsonb,records jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE held record; relation_ jsonb; endpoint jsonb; endpoint_row jsonb; src jsonb; pin_ jsonb;
 expected_role text; ids text[]; output jsonb:='[]'; directed jsonb; anchor_ jsonb; piece_ jsonb;
 occurrence_ jsonb; raw_ text; cue_ jsonb; cue_text text; cue_start integer;
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
    raw_:=substring(src->'projection'->>'text' FROM (piece_->>'start')::integer+1
     FOR (anchor_->>'start')::integer);
    cue_text:=(regexp_match(raw_, '\m(in|see|from)\s+$','i'))[1];
    IF cue_text IS NULL THEN
     RAISE EXCEPTION 'artifact reference lacks the exact local cross-reference cue' USING ERRCODE='23514';
    END IF;
    cue_start:=regexp_instr(raw_,'\m(in|see|from)\s+$',1,1,0,'i')-1;
    cue_:=jsonb_build_object('source_pointer',anchor_->>'pointer','start',cue_start,
     'end',cue_start+char_length(cue_text),'text',cue_text);
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
   'endpoints',directed,'origin_cue',cue_));
 END LOOP;
 RETURN output;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'artifact external nomination cannot resolve exact cohort endpoints' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.artifact_external_nominations(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_artifact_identity(inputs jsonb,config jsonb,product jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE expected_records jsonb; pair_ jsonb; a jsonb; b jsonb; routes jsonb; expected_pairs jsonb:='[]';
 code_a text; code_b text; title_a text; title_b text; compatible boolean; excluded boolean;
 lexical double precision; log_odds double precision; probability double precision; external_ boolean; policy jsonb;
 code_gamma integer; title_gamma integer; code_mw double precision; title_mw double precision;
 field_ jsonb; expected_value double precision; model_id text; expected_provenance jsonb; unbound jsonb; anchors jsonb;
 parameter_name text; parameter_value jsonb; parameter_text text; decoded_value double precision;
 alias_ boolean; expected_alias_pairs jsonb:='[]'; nominations jsonb; pair_nomination_ids jsonb;
 title_threshold double precision; config_policy jsonb:='{}'; numbering_ text; revision_ text;
 score_status text; expected_counts jsonb; explicit_references jsonb; explicit_ boolean;
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
  OR NOT policy ?& ARRAY['prior','code_m','code_u','title_m','title_u'] OR product->>'protocol'<>'artifact-identity-3' OR product->>'standing'<>'candidate_relative_private'
  OR policy IS DISTINCT FROM config_policy OR EXISTS(SELECT FROM jsonb_each(policy) p
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
 nominations:=ops.artifact_external_nominations(inputs,config,expected_records);
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
REVOKE ALL ON FUNCTION ops.validate_artifact_identity(jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.definition_role_candidates(detail jsonb,config_ jsonb,passage_map jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE window_ jsonb; passage_ jsonb; raw_ jsonb; candidate jsonb; role_ text; label_ text;
 lo integer; hi integer; start_ integer; end_ integer; index_ bigint; text_ text; result_ jsonb:='[]';
BEGIN
 IF detail->>'version' IS DISTINCT FROM 'located-definition-extraction-3'
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

CREATE OR REPLACE FUNCTION ops.validate_clause_classification(inputs jsonb,config_ jsonb,item jsonb,detail jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE reading_ jsonb; selection_ jsonb; passage_ jsonb; source_ jsonb; retained jsonb; frame_ jsonb; focus_ jsonb;
 annotation_ jsonb; sentence_ jsonb; before_ jsonb; after_ jsonb; window_ jsonb; raw_ jsonb;
 function_ jsonb; presentation_ jsonb; expected_ text; text_ text; digest_ text; policy_ text;
 lo integer; hi integer; position_ integer; neighbor_ integer; side_ text; visited text[]:=ARRAY[]::text[];
BEGIN
 policy_:=config_->>'context_policy';
 IF policy_ IS NULL OR policy_ NOT IN ('exact_focus','adjacent_sentences')
  OR item->>'context_policy' IS DISTINCT FROM policy_
  OR detail->>'version' IS DISTINCT FROM 'clause-model-observation-1'
  OR jsonb_typeof(detail->'raw_reports') IS DISTINCT FROM 'array'
  OR (detail->'profile')-'timeout_seconds' IS DISTINCT FROM (config_->'profile')-'timeout_seconds'
  OR (detail->'profile'->>'timeout_seconds')::numeric IS DISTINCT FROM (config_->'profile'->>'timeout_seconds')::numeric
  OR (SELECT jsonb_agg(r->'selection' ORDER BY i) FROM jsonb_array_elements(item->'readings') WITH ORDINALITY x(r,i))
    IS DISTINCT FROM config_->'focuses'
  OR EXISTS(SELECT FROM jsonb_array_elements(detail->'raw_reports') w GROUP BY w->>'computation' HAVING count(*)>1) THEN
  RAISE EXCEPTION 'clause model differs from exact configured focus selection' USING ERRCODE='23514'; END IF;
 FOR reading_ IN SELECT value FROM jsonb_array_elements(item->'readings') LOOP
  selection_:=reading_->'selection';
  SELECT p INTO STRICT passage_ FROM jsonb_array_elements(inputs->'passages') p WHERE p->>'passage_id'=selection_->>'passage_id';
  SELECT s INTO STRICT source_ FROM jsonb_array_elements(inputs->'sources') s
   WHERE encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')=passage_->>'source_ref';
  IF NOT inputs->'dependencies' ? (selection_->'frame'->>'contribution_id') THEN
   RAISE EXCEPTION 'clause focus missing declared retained dependency' USING ERRCODE='23514'; END IF;
  retained:=ops.resolve_retained_source_contribution(selection_->'frame');
  SELECT r INTO STRICT frame_ FROM jsonb_array_elements(retained->'contributions') r
   WHERE r->>'contribution_id'=selection_->'frame'->>'contribution_id';
  IF frame_->'component'->>'kind' IS DISTINCT FROM 'predicate_frame'
   OR frame_->'component'->>'focus_state' IS DISTINCT FROM 'exact'
   OR frame_->'component'->>'scope' IS DISTINCT FROM passage_->>'passage_id'
   OR frame_->'component'->>'effective_version' IS DISTINCT FROM passage_->>'effective_version'
   OR frame_->'pin'->>'source_view_id' IS DISTINCT FROM source_->>'source_view_id'
   OR frame_->'pin'->>'projection_digest' IS DISTINCT FROM source_->>'projection_digest' THEN
   RAISE EXCEPTION 'clause focus differs from exact retained frame and source' USING ERRCODE='23514'; END IF;
  SELECT m->'extents' INTO STRICT focus_ FROM jsonb_array_elements(frame_->'component'->'frame_members') m WHERE m->>'role'='focus';
  IF jsonb_array_length(focus_)<>1 THEN RAISE EXCEPTION 'clause focus is not contiguous' USING ERRCODE='23514'; END IF;
  lo:=(focus_->0->>'start')::integer; hi:=(focus_->0->>'end')::integer;
  IF NOT (lo>=(passage_->>'start')::integer AND hi>lo AND hi<=(passage_->>'end')::integer)
   OR reading_->'focus' IS DISTINCT FROM jsonb_build_object('passage_id',passage_->>'passage_id',
    'start',lo,'end',hi,'text',substring(passage_->>'text' FROM lo-(passage_->>'start')::integer+1 FOR hi-lo)) THEN
   RAISE EXCEPTION 'clause focus differs from original text extent' USING ERRCODE='23514'; END IF;
  before_:=NULL; after_:=NULL;
  IF policy_='adjacent_sentences' THEN
   SELECT a INTO STRICT annotation_ FROM ops.cut_task ct
   JOIN ops.task t ON t.id=ct.task_id JOIN ops.task_result result ON result.task_id=ct.origin_task_id
   JOIN ops.method_config config ON config.id=t.method_config_id JOIN ops.method method ON method.id=config.method_id
   CROSS JOIN LATERAL jsonb_array_elements(data.record_source_json(result.body->'parse_detail')->'annotations') a
   WHERE ct.cut_id=(source_->>'cut_id')::bigint AND t.unit_id=(source_->>'source_view_id')::bigint
    AND t.run_id=(source_->>'run_id')::bigint AND t.unit_type='source_view'
    AND method.name='extract.m1_annotations'
    AND 'annotation:'||(a->>'dependency_digest')=frame_->'component'->>'annotation'
    AND a->>'block_id'=frame_->'component'->>'block';
   SELECT (i-1)::integer INTO STRICT position_ FROM jsonb_array_elements(annotation_->'sentences') WITH ORDINALITY q(a,i)
    WHERE (a->>'start')::integer<=lo AND hi<=(a->>'end')::integer;
   FOREACH side_ IN ARRAY ARRAY['preceding','following'] LOOP
    neighbor_:=position_+CASE WHEN side_='preceding' THEN -1 ELSE 1 END;
    IF neighbor_<0 OR neighbor_>=jsonb_array_length(annotation_->'sentences') THEN CONTINUE; END IF;
    sentence_:=annotation_->'sentences'->neighbor_;
    lo:=(sentence_->>'start')::integer; hi:=(sentence_->>'end')::integer;
    IF lo<(passage_->>'start')::integer OR hi>(passage_->>'end')::integer THEN CONTINUE; END IF;
    sentence_:=jsonb_build_object('passage_id',passage_->>'passage_id',
      'start',lo,'end',hi,'text',substring(passage_->>'text' FROM lo-(passage_->>'start')::integer+1 FOR hi-lo));
    IF side_='preceding' THEN before_:=sentence_; ELSE after_:=sentence_; END IF;
   END LOOP;
  END IF;
  IF nullif(reading_->'preceding','null') IS DISTINCT FROM before_
   OR nullif(reading_->'following','null') IS DISTINCT FROM after_ THEN
   RAISE EXCEPTION 'clause model context differs from nearest retained sentences' USING ERRCODE='23514'; END IF;
  text_:=reading_->'focus'->>'text';
  IF policy_='adjacent_sentences' THEN
   text_:=COALESCE(before_->>'text'||chr(10),'')||'<focus>'||text_||'</focus>'||COALESCE(chr(10)||(after_->>'text'),'');
  END IF;
  digest_:=encode(sha256(convert_to(data.canonical_json(jsonb_build_array(policy_,selection_,text_)),'UTF8')),'hex');
  IF reading_->>'context_digest' IS DISTINCT FROM digest_ THEN
   RAISE EXCEPTION 'clause model context digest differs from exact input' USING ERRCODE='23514'; END IF;
  IF reading_->>'envelope' IS NULL THEN
   IF reading_->>'disposition'<>'failed' OR COALESCE(reading_->'function','[]')<>'[]' OR COALESCE(reading_->'presentation','[]')<>'[]' THEN
    RAISE EXCEPTION 'clause model outcome lacks provider envelope' USING ERRCODE='23514'; END IF;
   CONTINUE;
  END IF;
  SELECT w INTO STRICT window_ FROM jsonb_array_elements(detail->'raw_reports') w WHERE w->>'computation'=reading_->>'envelope';
  IF (reading_->>'envelope')=ANY(visited) OR window_->>'context_id' IS DISTINCT FROM 'clause-focus:'||digest_
   OR window_->>'context_digest' IS DISTINCT FROM digest_
   OR window_->>'profile' IS DISTINCT FROM detail->>'profile_fingerprint'
   OR window_->>'pack' IS DISTINCT FROM detail->>'pack_fingerprint'
   OR COALESCE(window_->'preparation'->>'synthetic_suffix','?') NOT IN ('','.')
   OR window_->'preparation'->>'consumed_text' IS DISTINCT FROM text_||(window_->'preparation'->>'synthetic_suffix') THEN
   RAISE EXCEPTION 'clause model envelope differs from bound focus input' USING ERRCODE='23514'; END IF;
  visited:=array_append(visited,reading_->>'envelope');
  raw_:=(window_->>'raw_json')::jsonb;
  function_:=ops.clause_model_axis(raw_->'clause_function',ARRAY['definition','explanation','assumption_restriction','prescribed_action','described_process','reference','unresolved']);
  presentation_:=ops.clause_model_axis(raw_->'presentation_context',ARRAY['example','attribution','historical','unresolved']);
  IF jsonb_typeof(raw_)<>'object' OR function_ IS NULL OR presentation_ IS NULL OR jsonb_array_length(function_)>1 THEN
   function_:='[]'; presentation_:='[]'; expected_:='failed';
  ELSE
   expected_:=CASE WHEN EXISTS(SELECT FROM jsonb_array_elements(function_||presentation_) v WHERE v->'accepted'='true')
      THEN 'observed' ELSE 'withheld' END;
  END IF;
  IF reading_->>'disposition' IS DISTINCT FROM expected_
   OR COALESCE(reading_->'function','[]') IS DISTINCT FROM function_
   OR COALESCE(reading_->'presentation','[]') IS DISTINCT FROM presentation_ THEN
   RAISE EXCEPTION 'clause model scores or withholding differ from retained output' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF cardinality(visited)<>jsonb_array_length(detail->'raw_reports') THEN
  RAISE EXCEPTION 'clause model report contains unbound provider envelopes' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION ops.validate_clause_classification(jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_structural_product_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; shape json; product jsonb; inputs jsonb; source_ jsonb; source_map jsonb:='{}'; passage jsonb; passage_map jsonb:='{}'; ref jsonb; v kb.source_view; identifier text; cited text; item jsonb; dimension jsonb; member jsonb; actual text[]; expected text[]; config_ jsonb; method_ text; introduction boolean; target_passage jsonb; premise jsonb; expected_state text; expected_outcome text; states text[]; model_detail jsonb; model_roles jsonb; model_components jsonb;
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
 SELECT jsonb_object_agg(p->>'passage_id',p) INTO passage_map FROM jsonb_array_elements(inputs->'passages') p;
 IF (CASE WHEN nullif(product->'definition','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'comparison','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'dossier','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'definition_components','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'artifact_identity','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END
  +CASE WHEN nullif(product->'clause_classification','null'::jsonb) IS NOT NULL THEN 1 ELSE 0 END)<>1 THEN
  RAISE EXCEPTION 'structural report must contain exactly one product variant' USING ERRCODE='23514'; END IF;
 CASE product->>'kind'
 WHEN 'clause_classification' THEN
  PERFORM ops.validate_clause_classification(inputs,config_,product->'clause_classification',
    data.record_source_json(p_envelope->'parse_detail'));
 WHEN 'definition_components' THEN
  item:=product->'definition_components';
  IF p_envelope->>'operation_version'='8' THEN
   model_detail:=data.record_source_json(p_envelope->'parse_detail');
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
    ops.structural_grouped_comparison(inputs,config_) THEN
   RAISE EXCEPTION 'comparison differs from exact retained predicate replay' USING ERRCODE='23514'; END IF;
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
