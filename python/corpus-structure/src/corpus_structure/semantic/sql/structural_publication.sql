-- Finite structural meaning projected separately from derivation identity.
CREATE OR REPLACE FUNCTION data.structural_citation(report jsonb,identifier text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE passage jsonb; source_ jsonb;
BEGIN
 SELECT value INTO STRICT passage FROM jsonb_array_elements(report->'inputs'->'passages') WHERE value->>'passage_id'=identifier;
 SELECT value INTO STRICT source_ FROM jsonb_array_elements(report->'inputs'->'sources')
 WHERE encode(sha256(convert_to(data.canonical_json(value),'UTF8')),'hex')=passage->>'source_ref';
 RETURN (passage-ARRAY['passage_id','source_ref'])||jsonb_build_object('source',source_-ARRAY[
  'run_id','cut_id','release_id','result_revision','source_view_id','native_task_id']);
END $$;
REVOKE ALL ON FUNCTION data.structural_citation(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.structural_citations(report jsonb,identifiers jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT COALESCE(jsonb_agg(c ORDER BY data.canonical_json(c)),'[]'::jsonb) FROM (
 SELECT DISTINCT data.structural_citation(report,value) c FROM jsonb_array_elements_text(identifiers)) selected
$$;
REVOKE ALL ON FUNCTION data.structural_citations(jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.structural_definition_component(report jsonb,component jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_strip_nulls(jsonb_build_object(
  'term',data.structural_citation(report,component->'term'->>'passage_id')||((component->'term')-'passage_id'),
  'content',data.structural_citation(report,component->'content'->>'passage_id')||((component->'content')-'passage_id'),
  'interpretation',component->'interpretation','scope',component->'scope','effective_version',component->'effective_version'))
$$;
REVOKE ALL ON FUNCTION data.structural_definition_component(jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.retained_definition_citations(reading jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb; component jsonb;
BEGIN
 retained:=ops.resolve_retained_component(reading->'component_ref');
 IF retained->'component' IS DISTINCT FROM reading->'component' THEN RAISE EXCEPTION 'dossier definition component differs from its actual origin' USING ERRCODE='23514'; END IF;
 component:=data.structural_definition_component(retained->'report',retained->'component');
 RETURN jsonb_build_array(component->'term',component->'content');
END $$;
REVOKE ALL ON FUNCTION data.retained_definition_citations(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.structural_public_clause_field(report jsonb,field_ jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb; witness jsonb;
BEGIN
 result:=jsonb_build_object('dimension',field_->>'dimension','lexical_value',field_->>'lexical_value',
  'evidence',data.structural_citations(report,field_->'evidence'));
 IF nullif(field_->'span','null') IS NOT NULL THEN
  result:=result||jsonb_build_object('span',data.structural_citation(report,field_->'span'->>'passage_id')||((field_->'span')-'passage_id'));
 END IF;
 IF nullif(field_->'spans','null') IS NOT NULL THEN
  result:=result||jsonb_build_object('spans',(SELECT jsonb_agg(data.structural_citation(report,v->>'passage_id')||(v-'passage_id') ORDER BY n)
   FROM jsonb_array_elements(field_->'spans') WITH ORDINALITY x(v,n)));
 END IF;
 IF nullif(field_->'literal','null') IS NOT NULL THEN
  result:=result||jsonb_build_object('literal',field_->'literal');
 END IF;
 IF nullif(field_->'condition','null') IS NOT NULL THEN
  result:=result||jsonb_build_object('condition',field_->'condition');
 END IF;
 IF nullif(field_->'typed','null') IS NOT NULL THEN
  result:=result||jsonb_build_object('typed',((field_->'typed')-ARRAY['span','basis_evidence'])||
   jsonb_build_object('span',data.structural_citation(report,field_->'typed'->'span'->>'passage_id')||((field_->'typed'->'span')-'passage_id')));
  witness:=nullif(field_->'typed'->'basis_evidence','null');
  IF witness IS NOT NULL THEN result:=jsonb_set(result,ARRAY['typed','basis_evidence'],data.structural_citation(report,witness->>'passage_id')||(witness-'passage_id'));END IF;
 END IF;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION data.structural_public_clause_field(jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.structural_public_statement(report jsonb,component_id text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb; value jsonb; items jsonb; item jsonb; side text; entry jsonb; witness jsonb; group_ jsonb;
BEGIN
 result:=jsonb_build_object('version','structural-public-statement-3','kind',report->>'kind',
  'scope',report->'inputs'->>'scope',
  'inventory_id',report->'inputs'->>'inventory_id','input_policy_id',report->'inputs'->>'policy_id',
  'coverage_limits',COALESCE((SELECT jsonb_agg(v ORDER BY v) FROM jsonb_array_elements(report->'inputs'->'coverage_limits') v),'[]'),
  'exclusions',COALESCE((SELECT jsonb_agg(v ORDER BY data.canonical_json(v)) FROM (
   SELECT jsonb_build_object('left',data.structural_citation(report,e->>'left'),'right',data.structural_citation(report,e->>'right')) v
   FROM jsonb_array_elements(report->'inputs'->'exclusions') e) x),'[]'));
 IF report->>'kind'='definition_components' THEN
  SELECT v INTO STRICT value FROM jsonb_array_elements(report->'definition_components'->'components') v WHERE v->>'component_id'=component_id;
  IF value->>'interpretation'='unresolved' THEN RAISE EXCEPTION 'unresolved attachment is not a supported public component' USING ERRCODE='23514'; END IF;
  result:=(result-'inventory_id'-'input_policy_id')||jsonb_build_object('definition_component',data.structural_definition_component(report,value));
 ELSIF component_id IS NOT NULL THEN RAISE EXCEPTION 'component selector requires component report' USING ERRCODE='23514';
 ELSIF report->>'kind'='definition_applicability' THEN
  result:=result-'inventory_id'-'input_policy_id';
  value:=report->'definition';
  SELECT COALESCE(jsonb_agg(v ORDER BY data.canonical_json(v)),'[]') INTO items FROM (
   SELECT jsonb_build_object('component',data.structural_definition_component(report,r->'component'),'outcome',r->'outcome',
    'premises',(SELECT COALESCE(jsonb_agg(jsonb_build_object('dimension',p->'dimension','state',p->'state','evidence',data.structural_citations(report,p->'evidence')) ORDER BY n),'[]') FROM jsonb_array_elements(r->'premises') WITH ORDINALITY premise(p,n)),'evidence',data.structural_citations(report,r->'evidence')) v FROM jsonb_array_elements(value->'readings') r) x;
  result:=result||jsonb_build_object('definition',jsonb_build_object('usage',data.structural_citation(report,value->>'usage_id'),
   'readings',items));
 ELSIF report->>'kind'='qualified_comparison' THEN
  value:=report->'comparison'; items:='[]';
  FOR item IN SELECT v FROM jsonb_array_elements(value->'dimensions') v LOOP
   entry:=jsonb_build_object('dimension',item->>'dimension','outcome',item->>'outcome','typed_outcome',item->>'typed_outcome','assumptions',item->'assumptions');
   IF nullif(item->'removed_interval','null') IS NOT NULL THEN entry:=entry||jsonb_build_object('removed_interval',item->'removed_interval');END IF;
   IF nullif(item->'added_interval','null') IS NOT NULL THEN entry:=entry||jsonb_build_object('added_interval',item->'added_interval');END IF;
   FOREACH side IN ARRAY ARRAY['left','right'] LOOP
    IF item->side IS NOT NULL AND item->side<>'null' THEN
     entry:=entry||jsonb_build_object(side,data.structural_public_clause_field(report,item->side));
    END IF;
    group_:=nullif(item->(side||'_group'),'null');
    IF group_ IS NOT NULL THEN
     entry:=entry||jsonb_build_object(side||'_group',jsonb_strip_nulls(jsonb_build_object(
      'state',group_->'state','grouping',group_->'grouping',
      'members',(SELECT COALESCE(jsonb_agg(data.structural_public_clause_field(report,v) ORDER BY n),'[]') FROM jsonb_array_elements(group_->'members') WITH ORDINALITY x(v,n)),
      'witnesses',(SELECT COALESCE(jsonb_agg(data.structural_citation(report,v->>'passage_id')||(v-'passage_id') ORDER BY n),'[]') FROM jsonb_array_elements(group_->'witnesses') WITH ORDINALITY x(v,n)))));
    END IF;
   END LOOP;
   items:=items||jsonb_build_array(entry);
  END LOOP;
  result:=result||jsonb_build_object('comparison',jsonb_build_object('left',data.structural_citation(report,value->>'left_id'),
   'right',data.structural_citation(report,value->>'right_id'),'dimensions',items,'equivalence',value->>'equivalence',
   'identity_standing',value->>'identity_standing','applicability',value->>'applicability'));
  IF nullif(value->'succession','null') IS NOT NULL THEN
   witness:=value->'succession'->'evidence';
   result:=jsonb_set(result,ARRAY['comparison','succession'],jsonb_build_object(
    'older',data.structural_citation(report,value->'succession'->>'older_id'),
    'newer',data.structural_citation(report,value->'succession'->>'newer_id'),
    'evidence',data.structural_citation(report,witness->>'passage_id')||(witness-'passage_id'),
    'older_evidence',data.structural_citation(report,value->'succession'->'older_evidence'->>'passage_id')||
     ((value->'succession'->'older_evidence')-'passage_id')));
  END IF;
 ELSIF report->>'kind'='dossier' THEN
  value:=report->'dossier';
  SELECT COALESCE(jsonb_agg(v ORDER BY data.canonical_json(v)),'[]') INTO items FROM (
   SELECT jsonb_strip_nulls(jsonb_build_object('passage',data.structural_citation(report,m->>'passage_id')||((m->'citation')-'passage_id'),'role',m->>'role',
    'sense',m->>'sense','scope',CASE WHEN nullif(m->'contribution_ref','null') IS NULL THEN m->>'scope' ELSE
     (SELECT string_agg(id,',' ORDER BY id) FROM (SELECT DISTINCT encode(sha256(convert_to(data.canonical_json(
       data.structural_citation(report,c->'span'->>'passage_id')->'source'),'UTF8')),'hex') id
       FROM jsonb_array_elements(m->'contribution_citations')c) physical_sources)
     ||':'||substring(m->>'scope' FROM strpos(m->>'scope',':')+1) END,
    'effective_version',m->'effective_version','qualification',m->>'qualification',
    'definition_interpretation',m->'definition_interpretation','applicability_outcome',m->'applicability_outcome',
    'endpoint_citations',CASE WHEN nullif(m->'contribution_ref','null') IS NOT NULL THEN
      (SELECT jsonb_agg(endpoint ORDER BY data.canonical_json(endpoint)) FROM
       (SELECT DISTINCT jsonb_build_object('source_pointer',c->'source_pointer',
       'passage',data.structural_citation(report,c->'span'->>'passage_id')||((c->'span')-'passage_id')) endpoint
       FROM jsonb_array_elements(m->'contribution_citations')c) endpoints) END)) v
   FROM jsonb_array_elements(value->'members') m) x;
  result:=result||jsonb_build_object('dossier',jsonb_build_object('root',value->>'root_id','members',items,
   'missing_sections',COALESCE((SELECT jsonb_agg(v ORDER BY v) FROM jsonb_array_elements(value->'missing_sections') v),'[]'),
   'membership_completeness',value->>'membership_completeness','admission_scope','membership_assembly_not_member_truth'));
 ELSE RAISE EXCEPTION 'unsupported public structural variant' USING ERRCODE='23514'; END IF;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION data.structural_public_statement(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.structural_publication_candidates(p_project text,p_release text,p_run bigint,p_cut bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE job ops.run; binding jsonb; selected record; report jsonb; group_ eval.structural_reference_set;
 c eval.structural_reference_pass; a eval.structural_reference_pass; b eval.structural_reference_pass;
 authored jsonb; case_ jsonb; statement jsonb; policy text; row_ jsonb; rows_ jsonb:='[]'; shape json;
 member jsonb; upstream record; statement_shape json;
BEGIN
 SELECT run.* INTO STRICT job FROM ops.run run JOIN ops.input_cut cut ON cut.run_id=run.id
 WHERE run.id=p_run AND run.project_id=p_project AND run.release_id=p_release AND run.sealed
 AND cut.id=p_cut AND cut.final AND cut.release_id=p_release;
 SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact
 WHERE release_id=p_release AND artifact_name='json_schema/StructuralPublicationPolicy';
 FOR binding IN SELECT value FROM jsonb_array_elements(COALESCE(convert_from(job.dependencies,'UTF8')::jsonb->'structural_admission','[]')) LOOP
  IF shape IS NULL OR binding-ARRAY['product_id','component_id','set_id','c_pass_id','c_content_digest','frame_digest','policy_id']<>'{}'
   OR NOT binding ?& ARRAY['product_id','set_id','c_pass_id','c_content_digest','frame_digest','policy_id'] THEN
   RAISE EXCEPTION 'structural admission requires released exact witness binding' USING ERRCODE='23514'; END IF;
  SELECT t.id selected_task_id,origin.id origin_task_id,result.body INTO STRICT selected
   FROM ops.cut_task member JOIN ops.task t ON t.id=member.task_id
   JOIN ops.task origin ON origin.id=COALESCE(t.reused_task_id,t.id)
   JOIN ops.task_result result ON result.task_id=origin.id
   WHERE member.cut_id=p_cut AND t.run_id=p_run AND t.release_id=p_release AND origin.release_id=p_release
   AND t.status IN ('done','reused') AND t.unit_type='run'
   AND 'structural:'||encode(sha256(convert_to(data.canonical_json((result.body->'structural_product')-'retrieval_report'),'UTF8')),'hex')=binding->>'product_id';
  report:=selected.body->'structural_product';
  policy:=CASE report->>'kind' WHEN 'definition_components' THEN 'independent-definition-component-1' WHEN 'definition_applicability' THEN 'independent-witnessed-applicability-1'
   WHEN 'qualified_comparison' THEN 'independent-structural-comparison-1' WHEN 'dossier' THEN 'independent-structural-dossier-1' END;
  IF policy IS NULL OR binding->>'policy_id' IS DISTINCT FROM policy OR NOT public.json_matches_schema(shape,
   jsonb_build_object('policy_id',policy,'policy_version','1','product_kind',report->>'kind','facet','public_statement')::json) THEN
   RAISE EXCEPTION 'structural publication policy is not released' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_structural_product_report(selected.origin_task_id,selected.body);
  SELECT * INTO STRICT group_ FROM eval.structural_reference_set WHERE id=(binding->>'set_id')::bigint
   AND project_id=p_project AND release_id=p_release;
  IF group_.frame_digest IS DISTINCT FROM binding->>'frame_digest' OR group_.frame->'inputs' IS DISTINCT FROM report->'inputs'
   OR group_.frame->>'operation' IS DISTINCT FROM report->>'kind'
   OR group_.frame->>'rubric_version' IS DISTINCT FROM policy
   OR (group_.frame->>'direction'='output_first' AND NOT(group_.frame->'product_ids' ? (binding->>'product_id'))) THEN
   RAISE EXCEPTION 'structural public frame differs from exact producer inputs' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT c FROM eval.structural_reference_pass WHERE set_id=group_.id AND pass_kind='C' ORDER BY id DESC LIMIT 1;
  SELECT * INTO STRICT a FROM eval.structural_reference_pass WHERE set_id=group_.id AND pass_kind='A' ORDER BY id DESC LIMIT 1;
  SELECT * INTO STRICT b FROM eval.structural_reference_pass WHERE set_id=group_.id AND pass_kind='B' ORDER BY id DESC LIMIT 1;
  IF c.id IS DISTINCT FROM (binding->>'c_pass_id')::bigint OR c.content_digest IS DISTINCT FROM binding->>'c_content_digest'
   OR c.parents IS DISTINCT FROM jsonb_build_array(a.id,b.id) OR a.actor=b.actor OR c.actor IN(a.actor,b.actor) THEN
   RAISE EXCEPTION 'structural public witness is stale or not independently adjudicated' USING ERRCODE='23514'; END IF;
  -- validate_structural_product_report replayed exact retained predecessor
  -- roles, protected member support and representation. Assembly admission remains
  -- separate from those independently established member assertions.
  statement:=data.structural_public_statement(report,binding->>'component_id');
  SELECT convert_from(content,'UTF8')::json INTO STRICT statement_shape FROM sem.artifact
   WHERE release_id=p_release AND artifact_name='json_schema/StructuralPublicStatement';
  IF NOT public.json_matches_schema(statement_shape,statement::json) THEN
   RAISE EXCEPTION 'structural public statement differs from released shape' USING ERRCODE='23514'; END IF;
  authored:=convert_from(c.authored,'UTF8')::jsonb;
  SELECT value INTO STRICT case_ FROM jsonb_array_elements(authored->'cases')
   WHERE value->>'facet'='public_statement' AND value->'path'='["public_statement"]'::jsonb
   AND value->>'judgment'='supported' AND value->'expected'=statement AND value->>'component_id' IS NOT DISTINCT FROM binding->>'component_id';
  IF NOT(case_->'source_passages' @> COALESCE((SELECT jsonb_agg(p->>'passage_id') FROM jsonb_array_elements(report->'inputs'->'passages') p),'[]')) THEN
   RAISE EXCEPTION 'public structural judgment omits selected source passages' USING ERRCODE='23514'; END IF;
  row_:=jsonb_build_object('claim_id','structural-claim:'||encode(sha256(convert_to(data.canonical_json(statement),'UTF8')),'hex'),
   'selected_task_id',selected.selected_task_id,'origin_task_id',selected.origin_task_id,'cut_id',p_cut,'product_id',binding->>'product_id',
   'product_kind',report->>'kind','policy_id',policy,'policy_version','1','set_id',group_.id,'c_pass_id',c.id,
   'c_content_digest',c.content_digest,'frame_digest',group_.frame_digest,'case_id',case_->>'case_id',
   'statement_json',data.canonical_json(statement),'sources_json',data.canonical_json(report->'inputs'->'sources'));
  row_:=row_||jsonb_build_object('assertion_id','structural-assertion:'||encode(sha256(convert_to(data.canonical_json(row_),'UTF8')),'hex'));
  rows_:=rows_||jsonb_build_array(row_);
 END LOOP;
 RETURN rows_;
EXCEPTION WHEN no_data_found OR too_many_rows OR invalid_text_representation THEN
 RAISE EXCEPTION 'structural public witness cannot resolve exact current custody' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION data.structural_publication_candidates(text,text,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.structural_publication_candidates(text,text,bigint,bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION data.validate_structural_assertions(r text,z text)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE job ops.run; cut bigint; expected jsonb; staged jsonb;
BEGIN
 IF to_regclass('pg_temp.sp_structural_assertion') IS NULL THEN RETURN; END IF;
 SELECT run.* INTO job FROM ops.run run WHERE run.result_realization_id=z AND run.release_id=r;
 IF NOT FOUND THEN
  IF EXISTS(SELECT FROM pg_temp.sp_structural_assertion) THEN RAISE EXCEPTION 'structural assertion has no producing run' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 SELECT id INTO STRICT cut FROM ops.input_cut WHERE run_id=job.id AND final AND release_id=r;
 expected:=data.structural_publication_candidates(job.project_id,r,job.id,cut);
 SELECT COALESCE(jsonb_agg(to_jsonb(s)-ARRAY['realization_id','release_id'] ORDER BY s.assertion_id),'[]') INTO staged
 FROM pg_temp.sp_structural_assertion s;
 IF staged IS DISTINCT FROM (SELECT COALESCE(jsonb_agg(v ORDER BY v->>'assertion_id'),'[]') FROM jsonb_array_elements(expected) v) THEN
  RAISE EXCEPTION 'staged structural assertions differ from native eligibility' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION data.validate_structural_assertions(text,text) FROM PUBLIC;
