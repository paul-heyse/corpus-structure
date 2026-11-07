
-- Private batch assembly: authenticate each exact custody binding once; retain every root.
-- No caller-supplied raw rows, persistent cache, database writes or application EXECUTE grant.
CREATE OR REPLACE FUNCTION ops.retained_contribution_roots(row_map jsonb,root text)
RETURNS SETOF text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT root
 UNION ALL
 SELECT candidate.key FROM jsonb_each(row_map) candidate
 CROSS JOIN LATERAL (SELECT row_map->(row_map->root->'component'->>'frame')->'component' AS frame) host
 WHERE row_map->root->'component'->>'kind'='predicate_reading'
  AND (
   (candidate.value->'component'->>'kind'='predicate_qualifier'
    AND candidate.value->'component'->>'host_contribution_id'=row_map->root->'component'->>'frame')
   OR
   (candidate.value->'component'->>'kind'='predicate_cue'
    AND candidate.value->'component'->>'host_state'='unresolved'
    AND candidate.value->'component'->>'scope'=host.frame->>'scope'
    AND candidate.value->'component'->>'annotation'=host.frame->>'annotation'
    AND candidate.value->'component'->'candidate_tokens' @> jsonb_build_array(host.frame->'predicate_token'))
  )
$$;
REVOKE ALL ON FUNCTION ops.retained_contribution_roots(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.resolve_retained_source_contributions(refs jsonb)
RETURNS TABLE(reference jsonb,contributions jsonb,sources jsonb) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE binding record; selected record; ref jsonb; first_ref jsonb; field_ text;
 row_map jsonb; used_rows jsonb; rows_ jsonb; sources_ jsonb; row_ jsonb; pin_ jsonb;
 view_ kb.source_view;
BEGIN
 IF jsonb_typeof(refs) IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'invalid retained contribution reference list' USING ERRCODE='23514';END IF;
 -- Validate primitive fields before any cast or grouping. Exactly the single-reference ABI.
 FOR ref IN SELECT value FROM jsonb_array_elements(refs) LOOP
  IF jsonb_typeof(ref) IS DISTINCT FROM 'object' OR
   ref-ARRAY['contribution_id','project_id','run_id','cut_id','release_id','result_revision','selected_task_id','origin_task_id','runtime_fingerprint']<>'{}'::jsonb OR
   NOT ref ?& ARRAY['contribution_id','project_id','run_id','cut_id','release_id','result_revision','selected_task_id','origin_task_id','runtime_fingerprint'] THEN
   RAISE EXCEPTION 'invalid retained contribution reference fields' USING ERRCODE='23514';END IF;
  FOREACH field_ IN ARRAY ARRAY['run_id','cut_id','selected_task_id','origin_task_id'] LOOP
   IF jsonb_typeof(ref->field_) IS DISTINCT FROM 'number' OR ref->>field_ !~ '^[1-9][0-9]*$' THEN
    RAISE EXCEPTION 'invalid retained contribution identifier' USING ERRCODE='23514';END IF;END LOOP;
  IF jsonb_typeof(ref->'result_revision') IS DISTINCT FROM 'number' OR ref->>'result_revision' !~ '^(0|[1-9][0-9]*)$' OR ref->>'contribution_id' !~ '^source-contribution:[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'invalid retained contribution identity/revision' USING ERRCODE='23514';END IF;
  FOREACH field_ IN ARRAY ARRAY['project_id','release_id','runtime_fingerprint','contribution_id'] LOOP
   IF jsonb_typeof(ref->field_) IS DISTINCT FROM 'string' OR length(ref->>field_)=0 THEN
    RAISE EXCEPTION 'invalid retained contribution binding' USING ERRCODE='23514';END IF;END LOOP;
 END LOOP;
 FOR binding IN SELECT r-'contribution_id' custody,jsonb_agg(r) refs_
  FROM jsonb_array_elements(refs) r GROUP BY r-'contribution_id' LOOP
  first_ref:=binding.refs_->0;
  -- Same completed/final cut, selected/origin task and immutable producer checks as resolver.
  SELECT result.body,origin_job.runtime_id,batch.data_revision INTO STRICT selected
  FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id
  JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id
  JOIN ops.cut_task member ON member.cut_id=completed.cut_id JOIN ops.task task ON task.id=member.task_id
  JOIN ops.task origin ON origin.id=COALESCE(task.reused_task_id,task.id)
  JOIN ops.run origin_job ON origin_job.id=origin.run_id JOIN ops.task_result result ON result.task_id=origin.id
  WHERE job.id=(first_ref->>'run_id')::bigint AND job.project_id=first_ref->>'project_id' AND job.release_id=first_ref->>'release_id'
   AND job.sealed AND job.status='finished' AND completed.cut_id=(first_ref->>'cut_id')::bigint
   AND task.id=(first_ref->>'selected_task_id')::bigint AND origin.id=(first_ref->>'origin_task_id')::bigint
   AND member.origin_task_id=origin.id AND origin.release_id=first_ref->>'release_id' AND task.status IN ('done','reused')
   AND task.unit_type='source_view' AND origin.unit_type='source_view' AND task.unit_id=origin.unit_id
   AND result.body->>'release_id'=first_ref->>'release_id'
   AND EXISTS(SELECT FROM ops.input_cut cut WHERE cut.id=completed.cut_id AND cut.run_id=job.id AND cut.release_id=job.release_id AND cut.final);
  IF selected.runtime_id IS DISTINCT FROM first_ref->>'runtime_fingerprint' OR selected.data_revision IS DISTINCT FROM (first_ref->>'result_revision')::bigint THEN
   RAISE EXCEPTION 'retained contribution differs from original producer custody' USING ERRCODE='23514';END IF;
  -- Decode the large backing body once per exact binding. Refuse ambiguous identities.
  IF EXISTS(SELECT FROM jsonb_array_elements(selected.body->'contributions') c
    GROUP BY c->>'contribution_id' HAVING count(DISTINCT c)>1) THEN
   RAISE EXCEPTION 'retained contribution identity or endpoint closure differs' USING ERRCODE='23514';END IF;
  SELECT COALESCE(jsonb_object_agg(c->>'contribution_id',c),'{}') INTO row_map
   FROM jsonb_array_elements(selected.body->'contributions') c;
  IF EXISTS(SELECT FROM jsonb_array_elements(binding.refs_) r WHERE NOT row_map ? (r->>'contribution_id')) THEN
   RAISE EXCEPTION 'retained contribution unavailable' USING ERRCODE='23514';END IF;
  WITH RECURSIVE closure(id) AS (
   SELECT id FROM jsonb_array_elements(binding.refs_) r
    CROSS JOIN LATERAL ops.retained_contribution_roots(row_map,r->>'contribution_id') id
   UNION SELECT ep.id FROM closure r CROSS JOIN LATERAL (
    SELECT e->>'contribution_id' id FROM jsonb_array_elements(COALESCE(row_map->r.id->'endpoints','[]')) e
    UNION SELECT jsonb_array_elements_text(COALESCE(row_map->r.id->'members','[]'))) ep)
  SELECT jsonb_agg(row_map->id ORDER BY id) INTO used_rows FROM closure;
  IF EXISTS(SELECT FROM jsonb_array_elements(used_rows) r WHERE r='null'::jsonb OR
    r->>'contribution_id' IS DISTINCT FROM 'source-contribution:'||encode(sha256(convert_to(data.canonical_json(r-'contribution_id'),'UTF8')),'hex')) THEN
   RAISE EXCEPTION 'retained contribution identity or endpoint closure differs' USING ERRCODE='23514';END IF;
  sources_:='[]';
  -- Original physical source/projection custody is shared, not borrowed from inputs.
  FOR pin_ IN SELECT q.pin FROM (SELECT DISTINCT ON (r->'pin') r->'pin' pin,r->>'contribution_id' first_id
   FROM jsonb_array_elements(used_rows) r ORDER BY r->'pin',r->>'contribution_id')q ORDER BY q.first_id LOOP
   SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(pin_->>'source_view_id')::bigint;
   IF NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=(first_ref->>'run_id')::bigint AND source_view_id=view_.id)
    OR pin_ IS DISTINCT FROM jsonb_build_object('source',view_.key,'native_product_task_id',view_.native_task_id,'product_key',view_.native_product_key,'product_digest',view_.native_content_digest,'projection_digest',view_.projection_digest,'recipe_digest',view_.recipe_digest,'source_view_id',view_.id) THEN
    RAISE EXCEPTION 'retained contribution source pin differs' USING ERRCODE='23514';END IF;
   sources_:=sources_||jsonb_build_array(jsonb_build_object('source_view_id',view_.id,'pin',pin_,'projection',view_.projection));
  END LOOP;
  IF EXISTS(SELECT FROM jsonb_array_elements(used_rows) r CROSS JOIN LATERAL jsonb_array_elements(COALESCE(r->'anchors','[]')) a
    WHERE a->'pin' IS DISTINCT FROM r->'pin') THEN
   RAISE EXCEPTION 'retained contribution source pin differs' USING ERRCODE='23514';END IF;
  FOR ref IN SELECT value FROM jsonb_array_elements(binding.refs_) LOOP
   WITH RECURSIVE closure(id) AS (
    SELECT id FROM ops.retained_contribution_roots(row_map,ref->>'contribution_id') id UNION
    SELECT ep.id FROM closure r CROSS JOIN LATERAL (
     SELECT e->>'contribution_id' id FROM jsonb_array_elements(COALESCE(row_map->r.id->'endpoints','[]')) e
     UNION SELECT jsonb_array_elements_text(COALESCE(row_map->r.id->'members','[]'))) ep)
   SELECT jsonb_agg(row_map->id ORDER BY id) INTO rows_ FROM closure;
   reference:=ref;contributions:=rows_;sources:=sources_;RETURN NEXT;
  END LOOP;
 END LOOP;
 RETURN;
EXCEPTION WHEN no_data_found OR too_many_rows OR numeric_value_out_of_range OR invalid_text_representation THEN
 RAISE EXCEPTION 'retained contribution cannot resolve exact selected origin' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_source_contributions(jsonb) FROM PUBLIC;

-- Existing Reader API delegates to the single current custody-validation owner.
CREATE OR REPLACE FUNCTION ops.resolve_retained_source_contribution(ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result_ jsonb;
BEGIN
 SELECT jsonb_build_object('contributions',r.contributions,'sources',r.sources) INTO STRICT result_
 FROM ops.resolve_retained_source_contributions(jsonb_build_array(ref))r;
 RETURN result_;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'retained contribution cannot resolve exact selected origin' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_source_contribution(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_source_contribution(jsonb) TO corpus_sem_reader,corpus_sem_writer;
-- Private membership retains all original endpoint citations, with source-qualified scope.
CREATE OR REPLACE FUNCTION ops.dossier_contribution_member_from_retained(inputs jsonb,ref jsonb,retained_rows jsonb,retained_sources jsonb,dependency_index jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE root_ jsonb;row_ jsonb;a jsonb;s jsonb;v jsonb;piece jsonb;p jsonb;meaning jsonb;
 citations jsonb:='[]';deps jsonb:='[]';citation jsonb;span_ jsonb;source_id text;start_ integer;end_ integer;role_ text;raw_role text;scope_ text;key_ text;
BEGIN
 IF NOT dependency_index ? (ref->>'contribution_id') THEN RAISE EXCEPTION 'dossier contribution outside dependencies' USING ERRCODE='23514';END IF;
 SELECT r INTO STRICT root_ FROM jsonb_array_elements(retained_rows)r WHERE r->>'contribution_id'=ref->>'contribution_id';
 IF root_->>'semantic_type' NOT IN ('structural.located_participant','structural.scoped_attachment','structural.artifact') THEN RAISE EXCEPTION 'dossier requires current source structural product' USING ERRCODE='23514';END IF;
 FOR row_ IN SELECT r FROM jsonb_array_elements(retained_rows)r ORDER BY r->>'contribution_id' LOOP
 deps:=deps||jsonb_build_array(row_->'contribution_id')||COALESCE(row_->'computation_dependencies','[]');
 FOR a IN SELECT value FROM jsonb_array_elements(COALESCE(row_->'anchors','[]')) LOOP
 SELECT source_ INTO STRICT s FROM jsonb_array_elements(inputs->'sources')source_ WHERE source_->'source_view_id'=a->'pin'->'source_view_id'
 AND source_->'native_task_id'=a->'pin'->'native_product_task_id' AND source_->'native_product_key'=a->'pin'->'product_key'
 AND source_->'native_content_digest'=a->'pin'->'product_digest' AND source_->'projection_digest'=a->'pin'->'projection_digest' AND source_->'recipe_digest'=a->'pin'->'recipe_digest';
 SELECT source_ INTO STRICT v FROM jsonb_array_elements(retained_sources)source_ WHERE source_->'source_view_id'=s->'source_view_id';
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
 role_:=CASE WHEN raw_role IN ('exception','open_question') THEN raw_role WHEN root_->>'kind'='relation' THEN 'relationship' WHEN raw_role IN ('header','row_label','symbol','declaration') THEN 'terminology' WHEN starts_with(raw_role,'procedure_') THEN 'usage' ELSE 'unresolved_sense' END;
 SELECT string_agg(id,',' ORDER BY id) INTO scope_ FROM (SELECT DISTINCT c->>'source_ref' id FROM jsonb_array_elements(citations)c)q;
 scope_:=scope_||':'||COALESCE(meaning->>'region',meaning->>'scope',meaning->>'source_pointer','unknown');
 key_:=encode(sha256(convert_to(data.canonical_json(jsonb_build_object('contribution_ref',ref,'role',role_,'citations',citations,'scope',scope_)),'UTF8')),'hex');
 span_:=citations->0->'span';
 RETURN jsonb_build_object('member_id',key_,'passage_id',span_->>'passage_id','citation',span_,'role',role_,'sense','unresolved','scope',scope_,
 'relation_product_id',ref->>'contribution_id','contribution_ref',ref,'contribution_citations',citations,'computation_dependencies',deps,'qualification','proposed');
EXCEPTION WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'contribution cannot resolve exact original citation closure' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.dossier_contribution_member_from_retained(jsonb,jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

-- Ordinary one-reference membership keeps its authenticated resolver route.
CREATE OR REPLACE FUNCTION ops.dossier_contribution_member(inputs jsonb,ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb;
BEGIN
 retained:=ops.resolve_retained_source_contribution(ref);
 RETURN ops.dossier_contribution_member_from_retained(inputs,ref,
  retained->'contributions',retained->'sources',inputs->'dependencies');
END $$;
REVOKE ALL ON FUNCTION ops.dossier_contribution_member(jsonb,jsonb) FROM PUBLIC;

-- Dependency membership is indexed once; raw rows remain owned by the batch resolver.
CREATE OR REPLACE FUNCTION ops.dossier_contribution_members(inputs jsonb,refs jsonb,root_component jsonb)
RETURNS SETOF jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 RETURN QUERY
 WITH dependency_index AS MATERIALIZED (
  SELECT COALESCE(jsonb_object_agg(d,true),'{}') value FROM jsonb_array_elements_text(inputs->'dependencies')d)
 SELECT member||CASE WHEN attachment->'component'->>'attachment_kind'='depends_on' THEN
   jsonb_build_object('semantic_dependency',jsonb_build_object(
    'relation','depends_on',
    'dependent',(SELECT jsonb_agg(c ORDER BY n) FROM jsonb_array_elements(member->'contribution_citations') WITH ORDINALITY citations(c,n)
     WHERE c->>'contribution_id'=attachment->'component'->>'attachment_contribution_id'),
    'prerequisite',(SELECT jsonb_agg(c ORDER BY n) FROM jsonb_array_elements(member->'contribution_citations') WITH ORDINALITY citations(c,n)
     WHERE c->>'contribution_id'=attachment->'component'->>'target_contribution_id')))
   ELSE '{}'::jsonb END
 FROM ops.resolve_retained_source_contributions(refs)r CROSS JOIN dependency_index d
 CROSS JOIN LATERAL (SELECT ops.dossier_contribution_member_from_retained(
  inputs,r.reference,r.contributions,r.sources,d.value) AS member OFFSET 0) resolved
 JOIN LATERAL jsonb_array_elements(r.contributions) attachment
  ON attachment->>'contribution_id'=r.reference->>'contribution_id'
  AND attachment->>'semantic_type'='structural.scoped_attachment'
 WHERE EXISTS(
  SELECT FROM jsonb_array_elements(attachment->'endpoints') endpoint
  JOIN LATERAL jsonb_array_elements(member->'contribution_citations') citation
   ON citation->>'contribution_id'=endpoint->>'contribution_id'
  JOIN LATERAL jsonb_array_elements(inputs->'passages') p ON p->'passage_id'=citation->'span'->'passage_id'
  WHERE endpoint->>'role'='target'
   AND citation->'span' IN (root_component->'term',root_component->'content')
   AND p->>'scope'=root_component->>'scope'
   AND p->>'effective_version' IS NOT DISTINCT FROM root_component->>'effective_version')
 AND (attachment->'component'->>'attachment_kind' IS DISTINCT FROM 'depends_on' OR (
  data.record_source_json(attachment->'value')->>'relation'='depends_on'
  AND attachment->'component'->>'scope'=root_component->>'scope'
  AND attachment->'component'->>'effective_version' IS NOT DISTINCT FROM root_component->>'effective_version'
  AND EXISTS(SELECT FROM jsonb_array_elements(attachment->'component'->'bases') basis WHERE basis->>'kind'='matched_cue')));
END
$$;
REVOKE ALL ON FUNCTION ops.dossier_contribution_members(jsonb,jsonb,jsonb) FROM PUBLIC;
