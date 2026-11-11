-- One coordinate rule for selection and family coverage, including empty results.
CREATE OR REPLACE FUNCTION ops.validate_characterization_selector(p_views jsonb,p_selector jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE v kb.source_view; pointer_ text:=p_selector->>'native_pointer';
BEGIN
 SELECT * INTO STRICT v FROM kb.source_view WHERE p_views @> jsonb_build_array(id) AND projection_digest=p_selector->>'projection';
 IF ((p_selector ? 'start')<>(p_selector ? 'end'))
 OR (p_selector ? 'start' AND ((p_selector->>'start')::bigint<0 OR (p_selector->>'end')::bigint<(p_selector->>'start')::bigint OR (p_selector->>'end')::bigint>char_length(v.projection->>'text')))
 OR (pointer_ IS NOT NULL AND NOT v.projection->'items' ? pointer_)
 OR (pointer_ IS NOT NULL AND p_selector ? 'start' AND NOT EXISTS(SELECT FROM jsonb_array_elements(v.projection->'pieces') piece
  WHERE piece->>'kind'='native_text' AND piece->>'item_ref'=pointer_
  AND (piece->>'start')::bigint<=(p_selector->>'start')::bigint AND (piece->>'end')::bigint>=(p_selector->>'end')::bigint))
 OR (p_selector ? 'page' AND NOT EXISTS(SELECT FROM kb.pdf_record_region region WHERE region.product_id=v.native_build_id
  AND region.revision_id=v.native_revision_id AND region.page_no=(p_selector->>'page')::bigint
  AND v.projection->'items' ? region.pointer AND (pointer_ IS NULL OR region.pointer=pointer_)
  AND (NOT p_selector ? 'start' OR EXISTS(SELECT FROM jsonb_array_elements(v.projection->'pieces') piece
   WHERE piece->>'kind'='native_text' AND piece->>'item_ref'=region.pointer
    AND (piece->>'start')::bigint<=(p_selector->>'start')::bigint AND (piece->>'end')::bigint>=(p_selector->>'end')::bigint)))) THEN
  RAISE EXCEPTION 'selector differs from exact projected piece and native page' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'selector cannot resolve exact qualified source projection' USING ERRCODE='23514';
END $$;

-- Private analysis products: immutable canonical payloads own every indexed projection.
CREATE OR REPLACE FUNCTION ops.validate_characterization_scope(p_task bigint,p_body jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; r ops.run; published ops.pdf_published_revision; pin jsonb; selector jsonb; v kb.source_view;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id;
 SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(
  (p_body->'base_document'->>'task_id')::bigint,p_body->'base_document'->>'product_key',p_body->'base_document'->>'content_digest');
 IF NOT EXISTS(SELECT FROM ops.task origin JOIN ops.run job ON job.id=origin.run_id
  WHERE origin.id=published.task_id AND job.project_id=r.project_id) THEN
  RAISE EXCEPTION 'characterization base belongs to another project' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(p_body->'source_scope'->'source_view_ids'))
 OR (SELECT count(*)<>count(DISTINCT value->>'source_view_id') FROM jsonb_array_elements(p_body->'source_scope'->'source_views'))
 OR EXISTS(SELECT jsonb_array_elements_text(p_body->'source_scope'->'source_view_ids') EXCEPT SELECT value->>'source_view_id' FROM jsonb_array_elements(p_body->'source_scope'->'source_views'))
 OR (SELECT count(*) FROM jsonb_array_elements(p_body->'source_scope'->'source_views'))
  <> jsonb_array_length(p_body->'source_scope'->'source_view_ids') THEN
  RAISE EXCEPTION 'characterization source scope repeats or omits a view' USING ERRCODE='23514'; END IF;
 FOR pin IN SELECT value FROM jsonb_array_elements(p_body->'source_scope'->'source_views') LOOP
  SELECT * INTO STRICT v FROM kb.source_view WHERE id=(pin->>'source_view_id')::bigint;
  IF pin->'base_document' IS DISTINCT FROM p_body->'base_document'
  OR (v.native_task_id,v.native_product_key,v.native_content_digest)
    IS DISTINCT FROM (published.task_id,published.product_key,published.logical_digest)
  OR (v.native_build_id,v.native_revision_id) IS DISTINCT FROM (published.build_id,published.build_id)
  OR NOT p_body->'source_scope'->'source_view_ids' @> jsonb_build_array(v.id)
  OR v.key IS DISTINCT FROM pin->>'key' OR v.section_pointer IS DISTINCT FROM pin->>'section_pointer'
  OR v.membership IS DISTINCT FROM pin->>'membership' OR v.projection_digest IS DISTINCT FROM pin->>'projection_digest'
  OR v.recipe_digest IS DISTINCT FROM pin->>'recipe_digest'
  OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=t.run_id AND source_view_id=v.id)
  OR (t.unit_type='source_view' AND t.unit_id IS DISTINCT FROM v.id)
  OR (t.unit_type='document' AND t.unit_id IS DISTINCT FROM v.document_id)
  OR t.unit_type NOT IN ('document','source_view') THEN
   RAISE EXCEPTION 'characterization source differs from exact producing scope' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR selector IN SELECT value FROM jsonb_array_elements(p_body->'source_scope'->'selectors')
  UNION ALL SELECT e.selector FROM jsonb_array_elements(coalesce(p_body->'coverage','[]')) coverage
   CROSS JOIN LATERAL jsonb_array_elements(coalesce(coverage->'eligible','[]')||coalesce(coverage->'examined','[]')||coalesce(coverage->'unexamined','[]')) e(selector) LOOP
  PERFORM ops.validate_characterization_selector(p_body->'source_scope'->'source_view_ids',selector);
 END LOOP;
END $$;

CREATE OR REPLACE FUNCTION ops.validate_characterization(p_task bigint,p_kind text,p_body jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; r ops.run; shape json; row_ jsonb; extent jsonb; ref jsonb; family text; item jsonb;
 ids text[]:='{}'; occurrences text[]:='{}'; terms text[]:='{}'; choices text[]:='{}'; group_ids text[]:='{}';
 seen text[]; checked_releases text[]:='{}'; cited text; v kb.source_view; dep ops.characterization_product; cfg ops.method_config; method_ ops.method; policies jsonb; policy jsonb;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id;
 PERFORM sem.require_execution_operation(t.release_id,'publish_characterization');
 SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact WHERE release_id=t.release_id
  AND artifact_name='json_schema/'||CASE p_kind WHEN 'layer' THEN 'AnnotationLayer' WHEN 'view' THEN 'EnrichedDocumentView' END;
 IF shape IS NULL OR NOT public.json_matches_schema(shape,p_body::json) OR p_body->>'release_id' IS DISTINCT FROM t.release_id
 OR p_body->>'format' IS DISTINCT FROM (CASE p_kind WHEN 'layer' THEN 'characterization-layer-v1' ELSE 'enriched-document-view-v1' END) THEN
  RAISE EXCEPTION 'characterization payload differs from released schema' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_characterization_scope(p_task,p_body);
 SELECT * INTO STRICT cfg FROM ops.method_config WHERE id=t.method_config_id;
 SELECT * INTO STRICT method_ FROM ops.method WHERE id=cfg.method_id;
 IF cfg.params->'characterization_base_document' IS DISTINCT FROM p_body->'base_document'
 OR cfg.params->'characterization_source_scope' IS DISTINCT FROM p_body->'source_scope' THEN
  RAISE EXCEPTION 'characterization source differs from frozen method configuration' USING ERRCODE='23514'; END IF;
 IF p_kind='view' THEN
  IF method_.name='text.compose_view' AND (coalesce(p_body->'layers','[]') IS DISTINCT FROM coalesce(cfg.params->'characterization_layers','[]') OR p_body->>'profile' IS DISTINCT FROM cfg.params->>'characterization_profile') THEN
   RAISE EXCEPTION 'view selection differs from producing configuration' USING ERRCODE='23514'; END IF;
  FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(p_body->'layers','[]')) LOOP
   SELECT * INTO STRICT dep FROM ops.characterization_product WHERE task_id=(ref->>'task_id')::bigint
    AND product_key=ref->>'product_key' AND content_digest=ref->>'content_digest' AND kind='layer';
   IF NOT dep.release_id=ANY(checked_releases) THEN
    PERFORM data.require_execution_release(dep.release_id);
    PERFORM sem.require_execution_operation(dep.release_id,'read_characterization');
    checked_releases:=array_append(checked_releases,dep.release_id);
   END IF;
   IF dep.payload->'base_document' IS DISTINCT FROM p_body->'base_document' OR dep.payload->>'format' IS DISTINCT FROM 'characterization-layer-v1' OR dep.payload->>'release_id' IS DISTINCT FROM dep.release_id
   OR NOT (p_body->'source_scope'->'source_views') @> (dep.payload->'source_scope'->'source_views')
   OR NOT (p_body->'source_scope'->'selectors') @> (dep.payload->'source_scope'->'selectors')
   OR NOT coalesce(p_body->'layers','[]') @> coalesce(dep.payload->'dependencies','[]')
   OR NOT EXISTS(SELECT FROM ops.task WHERE id=dep.task_id AND (status='done' OR id=p_task)) THEN
    RAISE EXCEPTION 'view mixes source or semantic releases' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(coalesce(p_body->'layers','[]')))
   OR (p_body->>'profile'='source_only' AND (jsonb_array_length(coalesce(p_body->'layers','[]'))>0 OR jsonb_array_length(coalesce(p_body->'coverage','[]'))>0)) THEN
   RAISE EXCEPTION 'view repeats layers or overstates source-only profile' USING ERRCODE='23514'; END IF;
  IF p_body->>'profile'<>'source_only' AND jsonb_array_length(coalesce(p_body->'layers','[]'))=0 THEN
   RAISE EXCEPTION 'view profile requires published layers' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(p_body->'coverage','[]')) c WHERE NOT EXISTS(
   SELECT FROM jsonb_array_elements(coalesce(p_body->'layers','[]')) l JOIN ops.characterization_product d
    ON d.task_id=(l->>'task_id')::bigint AND d.product_key=l->>'product_key' AND d.content_digest=l->>'content_digest'
   WHERE d.payload->'coverage' @> jsonb_build_array(c))) THEN
   RAISE EXCEPTION 'view coverage is not recorded by selected layers' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 IF p_body->>'outcome'='failed' THEN RAISE EXCEPTION 'failed analysis cannot publish a layer' USING ERRCODE='23514'; END IF;
 IF p_body->'operation'->>'key' IS DISTINCT FROM method_.name
 OR p_body->'operation'->>'version' IS DISTINCT FROM method_.version
 OR p_body->'operation'->>'runtime' IS DISTINCT FROM r.runtime_id
 OR p_body->'operation'->>'input' IS DISTINCT FROM t.input_hash
 OR p_body->'operation'->>'configuration' IS DISTINCT FROM cfg.config_hash
 OR EXISTS(SELECT FROM unnest(ARRAY['model','grammar','context']) key
  WHERE p_body->'operation'->>key IS DISTINCT FROM cfg.params->>key) THEN
  RAISE EXCEPTION 'layer differs from authenticated operation determinants' USING ERRCODE='23514'; END IF;
 FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(p_body->'dependencies','[]')) LOOP
  SELECT * INTO STRICT dep FROM ops.characterization_product WHERE task_id=(ref->>'task_id')::bigint
   AND product_key=ref->>'product_key' AND content_digest=ref->>'content_digest' AND kind='layer';
   IF NOT dep.release_id=ANY(checked_releases) THEN
    PERFORM data.require_execution_release(dep.release_id);
    PERFORM sem.require_execution_operation(dep.release_id,'read_characterization');
    checked_releases:=array_append(checked_releases,dep.release_id);
   END IF;
  IF dep.payload->'base_document' IS DISTINCT FROM p_body->'base_document' OR dep.payload->>'format' IS DISTINCT FROM 'characterization-layer-v1' OR dep.payload->>'release_id' IS DISTINCT FROM dep.release_id
  OR NOT EXISTS(SELECT FROM ops.task WHERE id=dep.task_id AND status='done') THEN
   RAISE EXCEPTION 'layer dependency mixes source/release or is unsealed' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF NOT coalesce(p_body->'dependencies','[]') @> coalesce(p_body->'operation'->'required_layers','[]') THEN
  RAISE EXCEPTION 'layer omits required dependencies' USING ERRCODE='23514'; END IF;
 FOREACH family IN ARRAY ARRAY['occurrences','annotations','memberships','roles','terms','choices'] LOOP
  seen:='{}';
  FOR row_ IN SELECT value FROM jsonb_array_elements(coalesce(p_body->family,'[]')) LOOP
   cited:=row_->>'local_id';
   IF cited=ANY(ids) THEN RAISE EXCEPTION 'duplicate layer inventory identity' USING ERRCODE='23514'; END IF;
   ids:=array_append(ids,cited); seen:=array_append(seen,cited);
   IF family='choices' THEN
    group_ids:=array_append(group_ids,cited);
    FOR item IN SELECT value FROM jsonb_array_elements(row_->'members') LOOP
     IF item->>'local_id'=ANY(ids) THEN RAISE EXCEPTION 'duplicate choice identity' USING ERRCODE='23514'; END IF;
     ids:=array_append(ids,item->>'local_id'); choices:=array_append(choices,item->>'local_id');
    END LOOP;
   END IF;
  END LOOP;
  IF family='occurrences' THEN occurrences:=seen; ELSIF family='terms' THEN terms:=seen; END IF;
 END LOOP;
 FOR row_ IN SELECT value FROM jsonb_array_elements(coalesce(p_body->'occurrences','[]')) LOOP
  IF row_->>'local_id' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(jsonb_build_object(
   'base_document',p_body->'base_document','extents',(SELECT jsonb_agg(value-'source_view_id' ORDER BY ord)
    FROM jsonb_array_elements(row_->'extents') WITH ORDINALITY e(value,ord)))),'UTF8')),'hex') THEN
   RAISE EXCEPTION 'source occurrence identity differs from original ordered extents' USING ERRCODE='23514'; END IF;
  FOR extent IN SELECT value FROM jsonb_array_elements(row_->'extents') LOOP
   SELECT * INTO STRICT v FROM kb.source_view WHERE id=(extent->>'source_view_id')::bigint;
   IF NOT p_body->'source_scope'->'source_view_ids' @> jsonb_build_array(v.id)
   OR extent->>'projection' IS DISTINCT FROM v.projection_digest
   OR NOT v.projection->'items' ? (extent->>'native_pointer')
   OR (extent ? 'page' AND NOT EXISTS(SELECT FROM kb.pdf_record_region region WHERE region.product_id=v.native_build_id
     AND region.revision_id=v.native_revision_id AND region.pointer=extent->>'native_pointer' AND region.page_no=(extent->>'page')::bigint))
   OR (extent->>'synthetic'='false' AND extent ? 'start' AND NOT EXISTS(SELECT FROM jsonb_array_elements(v.projection->'pieces') piece
    WHERE piece->>'kind'='native_text' AND piece->>'item_ref'=extent->>'native_pointer'
     AND (piece->>'start')::bigint<=(extent->>'start')::bigint AND (piece->>'end')::bigint>=(extent->>'end')::bigint))
   OR ((extent ? 'start')<>(extent ? 'end'))
   OR (extent ? 'start' AND ((extent->>'start')::bigint<0 OR ((extent->>'end')::bigint<(extent->>'start')::bigint OR (extent->>'end'=extent->>'start' AND extent->>'synthetic'='false'))
    OR (extent->>'end')::bigint>char_length(v.projection->>'text')
    OR (extent->>'synthetic'='false' AND extent ? 'text' AND extent->>'text' IS DISTINCT FROM substring(v.projection->>'text'
      FROM (extent->>'start')::integer+1 FOR (extent->>'end')::integer-(extent->>'start')::integer)))) THEN
    RAISE EXCEPTION 'occurrence differs from exact qualified source' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 SELECT convert_from(content,'UTF8')::jsonb INTO policies FROM sem.artifact
 WHERE release_id=t.release_id AND artifact_name='characterization/attachment-policies.json';
 FOREACH family IN ARRAY ARRAY['annotations','memberships','roles','terms','choices'] LOOP
  FOR row_ IN SELECT value FROM jsonb_array_elements(coalesce(p_body->family,'[]')) LOOP
   FOR cited IN SELECT jsonb_array_elements_text(coalesce(row_->'occurrences','[]')) LOOP
    IF NOT cited=ANY(occurrences) THEN RAISE EXCEPTION 'dangling occurrence reference' USING ERRCODE='23514'; END IF;
   END LOOP;
   FOR cited IN SELECT jsonb_array_elements_text(coalesce(row_->'premises','[]')) LOOP
    IF NOT cited=ANY(ids) THEN RAISE EXCEPTION 'dangling producing premise' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF family='memberships' AND (NOT row_->>'group'=ANY(ids) OR NOT row_->>'member'=ANY(ids)) THEN
    RAISE EXCEPTION 'dangling membership endpoint' USING ERRCODE='23514'; END IF;
   IF family='roles' THEN
    IF NOT row_->>'owner'=ANY(ids) OR NOT row_->>'member'=ANY(ids) THEN
     RAISE EXCEPTION 'dangling role endpoint' USING ERRCODE='23514'; END IF;
    policy:=policies->(row_->'basis'->>'kind');
    IF row_->'basis'->>'kind'='released_construction' THEN policy:=policy->'rules'->(row_->'basis'->>'rule_id'); END IF;
    SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact WHERE release_id=t.release_id
     AND artifact_name=policy->>'schema_kind';
    IF shape IS NULL OR NOT public.json_matches_schema(shape,(row_->'basis')::json) THEN
     RAISE EXCEPTION 'attachment basis differs from released support policy' USING ERRCODE='23514'; END IF;
    FOR cited IN SELECT jsonb_array_elements_text(coalesce(row_->'basis'->'premises','[]')) LOOP
     IF NOT cited=ANY(ids) THEN RAISE EXCEPTION 'dangling attachment premise' USING ERRCODE='23514'; END IF;
    END LOOP;
    FOR cited IN SELECT jsonb_array_elements_text(coalesce(row_->'basis'->'choice_refs','[]')) LOOP
     IF NOT cited=ANY(choices) THEN RAISE EXCEPTION 'dangling attachment choice' USING ERRCODE='23514'; END IF;
    END LOOP;
   END IF;
   FOR cited IN SELECT jsonb_array_elements_text(coalesce(row_->'required_choices','[]')) LOOP
    IF NOT cited=ANY(choices) THEN RAISE EXCEPTION 'dangling analytical choice' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF family='terms' THEN
    FOR item IN SELECT value FROM jsonb_array_elements(coalesce(row_->'children','[]')) LOOP
     IF item->>'structural' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'semantic term children must form a DAG' USING ERRCODE='23514'; END IF;
     IF NOT item->>'target'=ANY(terms) THEN RAISE EXCEPTION 'dangling term dependency' USING ERRCODE='23514'; END IF;
    END LOOP;
   ELSIF family='choices' THEN
    FOR item IN SELECT value FROM jsonb_array_elements(row_->'members') LOOP
     FOR cited IN SELECT jsonb_array_elements_text(coalesce(item->'premises','[]')) LOOP
      IF NOT cited=ANY(ids) THEN RAISE EXCEPTION 'dangling alternative premise' USING ERRCODE='23514'; END IF;
     END LOOP;
     IF NOT item->>'root'=ANY(terms) THEN RAISE EXCEPTION 'dangling alternative root' USING ERRCODE='23514'; END IF;
     FOR cited IN SELECT jsonb_array_elements_text(coalesce(item->'required_choices','[]')) LOOP
      IF NOT cited=ANY(choices) THEN RAISE EXCEPTION 'dangling alternative dependency' USING ERRCODE='23514'; END IF;
     END LOOP;
    END LOOP;
   END IF;
  END LOOP;
 END LOOP;
 FOR item IN
  SELECT value FROM jsonb_array_elements(coalesce(p_body->'annotations','[]')||coalesce(p_body->'memberships','[]')||coalesce(p_body->'terms','[]'))
  UNION ALL SELECT value->'basis' FROM jsonb_array_elements(coalesce(p_body->'roles','[]'))
  UNION ALL SELECT member FROM jsonb_array_elements(coalesce(p_body->'choices','[]')) g CROSS JOIN LATERAL jsonb_array_elements(g->'members') member
 LOOP
  FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(item->'external_premises','[]')) LOOP
   IF NOT coalesce(p_body->'dependencies','[]') @> jsonb_build_array(ref->'layer')
   OR NOT EXISTS(SELECT FROM ops.characterization_product d CROSS JOIN LATERAL jsonb_each(d.payload) f
    CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN f.key IN ('annotations','memberships','roles','terms','occurrences','choices') THEN f.value ELSE '[]'::jsonb END) node
    WHERE d.task_id=(ref->'layer'->>'task_id')::bigint AND d.product_key=ref->'layer'->>'product_key'
     AND d.content_digest=ref->'layer'->>'content_digest' AND (node->>'local_id'=ref->>'local_id' OR (f.key='choices' AND EXISTS(SELECT FROM jsonb_array_elements(node->'members') member WHERE member->>'local_id'=ref->>'local_id')))) THEN
    RAISE EXCEPTION 'qualified premise is outside declared layer closure' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(p_body->'annotations','[]')||coalesce(p_body->'roles','[]')||coalesce(p_body->'terms','[]'))
  UNION ALL SELECT member FROM jsonb_array_elements(coalesce(p_body->'choices','[]')) g CROSS JOIN LATERAL jsonb_array_elements(g->'members') member
 LOOP
  FOR row_ IN SELECT value->'value' FROM jsonb_array_elements(coalesce(item->'scores','[]')) LOOP
   IF row_->>'kind' NOT IN ('integer','float','null') OR (row_->>'kind'='float' AND (
    row_->>'hexadecimal' !~ '^-?0x(1\.[0-9a-f]{13}p[+-](0|[1-9][0-9]{0,3})|0\.[0-9a-f]{13}p-1022|0\.0p\+0)$'
    OR split_part(row_->>'hexadecimal','p',2)::integer NOT BETWEEN -1022 AND 1023
    OR row_->>'hexadecimal' IN ('0x0.0000000000000p-1022','-0x0.0000000000000p-1022'))) THEN
    RAISE EXCEPTION 'score differs from finite canonical numerical encoding' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 IF NOT p_body->'operation'->'outcomes' ? (p_body->>'outcome') THEN RAISE EXCEPTION 'undeclared layer outcome' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_body->'coverage') c WHERE
  (c->>'outcome' IN ('complete','empty') AND (c->>'availability'<>'available' OR jsonb_array_length(coalesce(c->'unexamined','[]'))>0
    OR jsonb_array_length(coalesce(c->'eligible','[]'))=0 OR c->'examined' IS DISTINCT FROM c->'eligible'))
  OR (c->>'outcome' NOT IN ('complete','empty') AND coalesce(c->>'reason','')=''))
 OR EXISTS(SELECT FROM jsonb_array_elements_text(p_body->'operation'->'produced_families') f WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(p_body->'coverage') c WHERE c->>'family'=f)) THEN
  RAISE EXCEPTION 'coverage omits examined scope or declared family' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH RECURSIVE members AS (SELECT member FROM jsonb_array_elements(coalesce(p_body->'choices','[]')) g CROSS JOIN LATERAL jsonb_array_elements(g->'members') member),
 edges AS (SELECT member->>'local_id' owner,value target FROM members CROSS JOIN LATERAL jsonb_array_elements_text(coalesce(member->'required_choices','[]'))),
 reach(owner,target) AS (SELECT owner,target FROM edges
 UNION SELECT reach_.owner,e.target FROM reach reach_ JOIN edges e ON e.owner=reach_.target)
 SELECT FROM reach WHERE owner=target) THEN RAISE EXCEPTION 'analytical choice dependency cycle' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(p_body->'terms','[]')) term WHERE term->>'kind'='binder'
  AND NOT (SELECT coalesce(jsonb_agg(edge->>'role'),'[]') FROM jsonb_array_elements(coalesce(term->'children','[]')) edge) @> '["variable","restrictor","body"]'::jsonb) THEN
  RAISE EXCEPTION 'binder lacks variable restrictor or body' USING ERRCODE='23514'; END IF;
 IF p_body->>'outcome'='complete' AND EXISTS(SELECT FROM jsonb_array_elements(p_body->'coverage') c WHERE c->>'outcome' NOT IN ('complete','empty')) THEN
  RAISE EXCEPTION 'complete layer claims incomplete families' USING ERRCODE='23514'; END IF;
 FOREACH family IN ARRAY ARRAY['annotations','memberships','roles','terms','choices'] LOOP
  IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(p_body->family,'[]')) n WHERE NOT EXISTS(
   SELECT FROM jsonb_array_elements(p_body->'coverage') c WHERE c->>'family'=n->>'family' AND c->>'outcome'<>'empty')) THEN
   RAISE EXCEPTION 'analytical node belongs to undeclared or empty family' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(WITH RECURSIVE edges AS (
  SELECT node->>'local_id' owner,child->>'target' target FROM jsonb_array_elements(coalesce(p_body->'terms','[]')) node
   CROSS JOIN LATERAL jsonb_array_elements(coalesce(node->'children','[]')) child WHERE child->>'structural'='true'
  UNION ALL SELECT m->>'group',m->>'member' FROM jsonb_array_elements(coalesce(p_body->'memberships','[]')) m WHERE m->>'structural'='true'
 ), reach(owner,target) AS (
  SELECT owner,target FROM edges
  UNION SELECT reach_.owner,e.target FROM reach reach_ JOIN edges e ON e.owner=reach_.target
 ) SELECT FROM reach WHERE owner=target) THEN
  RAISE EXCEPTION 'structural characterization dependency cycle' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_body->'coverage') c WHERE NOT p_body->'operation'->'produced_families' ? (c->>'family')
   OR c->>'operation' IS DISTINCT FROM p_body->'operation'->>'key')
 OR (SELECT count(*)<>count(DISTINCT c->>'family') FROM jsonb_array_elements(p_body->'coverage') c) THEN
  RAISE EXCEPTION 'coverage differs from declared produced families' USING ERRCODE='23514'; END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.publish_characterization(p_task bigint,p_attempt bigint,p_holder text,p_layer jsonb,p_view jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; r ops.run; body jsonb; kind_ text; digest_ text; key_ text; result_ jsonb:='{}'; terminal_digest text; family text;
BEGIN
 PERFORM data.require_runtime_principal('write');
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id FOR SHARE;
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task FOR UPDATE;
 terminal_digest:=encode(sha256(convert_to(data.canonical_json(jsonb_build_array(p_layer,p_view)),'UTF8')),'hex');
 IF t.status='done' AND t.attempt=p_attempt AND t.claimed_by=p_holder AND t.result_digest=terminal_digest THEN
  RETURN jsonb_build_object('transaction','replay','products',(SELECT jsonb_object_agg(kind,jsonb_build_object('task_id',task_id,'product_key',product_key,'content_digest',content_digest)) FROM ops.characterization_product WHERE task_id=p_task),'receipt',jsonb_build_object('task_id',t.id,'run_id',t.run_id,'release_id',t.release_id,'attempt',t.attempt,'protocol','done','result_digest',t.result_digest,'observation_ids','[]'::jsonb));
 END IF;
 IF r.sealed OR r.status NOT IN ('created','running') OR t.status<>'running' OR t.attempt<>p_attempt OR t.claimed_by IS DISTINCT FROM p_holder THEN
  RAISE EXCEPTION 'characterization task attempt lost or run sealed' USING ERRCODE='P0004'; END IF;
 IF octet_length(coalesce(data.canonical_json(p_layer),''))>8388608 OR octet_length(coalesce(data.canonical_json(p_view),''))>8388608 THEN
  RAISE EXCEPTION 'characterization report exceeds bounded payload contract' USING ERRCODE='54000'; END IF;
 IF p_layer IS NULL AND p_view IS NULL THEN RAISE EXCEPTION 'characterization publication is empty' USING ERRCODE='23514'; END IF;
 IF p_layer IS NULL AND NOT EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
  WHERE cfg.id=t.method_config_id AND m.name='text.compose_view') THEN
  RAISE EXCEPTION 'source-only composition requires its released producing method' USING ERRCODE='23514'; END IF;
 FOREACH kind_ IN ARRAY ARRAY['layer','view'] LOOP
  body:=CASE kind_ WHEN 'layer' THEN p_layer ELSE p_view END;
  IF body IS NULL THEN CONTINUE; END IF;
  PERFORM ops.validate_characterization(p_task,kind_,body);
  digest_:=encode(sha256(convert_to(data.canonical_json(body),'UTF8')),'hex'); key_:='characterization-'||kind_||':'||digest_;
  INSERT INTO ops.characterization_product(task_id,product_key,content_digest,kind,release_id,runtime_id,base_task_id,base_product_key,base_content_digest,payload)
  VALUES(t.id,key_,digest_,kind_,t.release_id,r.runtime_id,(body->'base_document'->>'task_id')::bigint,body->'base_document'->>'product_key',body->'base_document'->>'content_digest',body);
  result_:=result_||jsonb_build_object(kind_,jsonb_build_object('task_id',t.id,'product_key',key_,'content_digest',digest_));
  IF kind_='layer' THEN
   INSERT INTO kb.characterization_occurrence SELECT t.id,key_,digest_,v->>'local_id',v->>'local_id',v->'extents'->0->>'projection',(v->'extents'->0->>'source_view_id')::bigint,v FROM jsonb_array_elements(coalesce(body->'occurrences','[]')) v;
   INSERT INTO kb.characterization_annotation SELECT t.id,key_,digest_,v->>'local_id',v->>'kind',v->>'family',v FROM jsonb_array_elements(coalesce(body->'annotations','[]')) v;
   INSERT INTO kb.characterization_membership SELECT t.id,key_,digest_,v->>'local_id',v->>'group',v->>'member',v->>'role',(v->>'order')::bigint,v->>'family',v FROM jsonb_array_elements(coalesce(body->'memberships','[]')) v;
   INSERT INTO kb.characterization_role SELECT t.id,key_,digest_,v->>'local_id',v->>'owner',v->>'member',v->>'role',v->>'family',v FROM jsonb_array_elements(coalesce(body->'roles','[]')) v;
   INSERT INTO kb.characterization_term SELECT t.id,key_,digest_,v->>'local_id',v->>'kind',v->>'family',v FROM jsonb_array_elements(coalesce(body->'terms','[]')) v;
   INSERT INTO kb.characterization_choice SELECT t.id,key_,digest_,v->>'local_id',v->>'family',v FROM jsonb_array_elements(coalesce(body->'choices','[]')) v;
   INSERT INTO kb.characterization_extent SELECT t.id,key_,digest_,v->>'local_id',e.position-1,e.body->>'projection',(e.body->>'source_view_id')::bigint,e.body->>'native_pointer',(e.body->>'page')::bigint,(e.body->>'start')::bigint,(e.body->>'end')::bigint,e.body
    FROM jsonb_array_elements(coalesce(body->'occurrences','[]')) v CROSS JOIN LATERAL jsonb_array_elements(v->'extents') WITH ORDINALITY e(body,position);
   INSERT INTO kb.characterization_term_edge SELECT t.id,key_,digest_,v->>'local_id',e.position-1,e.body->>'target',e.body->>'role',(e.body->>'structural')::boolean,e.body
    FROM jsonb_array_elements(coalesce(body->'terms','[]')) v CROSS JOIN LATERAL jsonb_array_elements(coalesce(v->'children','[]')) WITH ORDINALITY e(body,position);
   INSERT INTO kb.characterization_choice_member SELECT t.id,key_,digest_,v->>'local_id',e->>'local_id',e->>'root',e
    FROM jsonb_array_elements(coalesce(body->'choices','[]')) v CROSS JOIN LATERAL jsonb_array_elements(v->'members') e;
   INSERT INTO kb.characterization_coverage SELECT t.id,key_,digest_,v->>'family',v->>'family',v->>'outcome',v FROM jsonb_array_elements(body->'coverage') v;
  END IF;
 END LOOP;
 INSERT INTO ops.task_result(task_id,release_id,body) VALUES(t.id,t.release_id,jsonb_build_object('characterization',result_,'outcome','produced'));
 UPDATE ops.task SET status='done',result_digest=terminal_digest,finished_at=clock_timestamp(),lease_until=NULL,error=NULL WHERE id=t.id;
 RETURN jsonb_build_object('transaction','applied','products',result_,'receipt',jsonb_build_object('task_id',t.id,'run_id',t.run_id,'release_id',t.release_id,'attempt',t.attempt,'protocol','done','result_digest',terminal_digest,'observation_ids','[]'::jsonb));
END $$;

CREATE OR REPLACE FUNCTION ops.read_characterization_product(p_task bigint,p_key text,p_digest text,p_kind text,p_run bigint DEFAULT NULL,p_max_bytes bigint DEFAULT 8388608)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE product ops.characterization_product; project_ text;
BEGIN
 IF pg_has_role(session_user,'corpus_sem_reader','USAGE') THEN PERFORM data.require_runtime_principal('read');
 ELSIF pg_has_role(session_user,'corpus_sem_writer','USAGE') THEN PERFORM data.require_runtime_principal('write');
 ELSE PERFORM data.require_runtime_principal('evaluate'); END IF;
 SELECT p.* INTO STRICT product FROM ops.characterization_product p JOIN ops.task t ON t.id=p.task_id
 WHERE p.task_id=p_task AND p.product_key=p_key AND p.content_digest=p_digest AND p.kind=p_kind AND t.status='done';
 PERFORM data.require_execution_release(product.release_id);
 PERFORM sem.require_execution_operation(product.release_id,'read_characterization');
 IF product.payload->>'release_id' IS DISTINCT FROM product.release_id
 OR product.payload->>'format' IS DISTINCT FROM (CASE product.kind WHEN 'layer' THEN 'characterization-layer-v1' ELSE 'enriched-document-view-v1' END) THEN
  RAISE EXCEPTION 'unsupported retained characterization format or release binding' USING ERRCODE='23514'; END IF;
 PERFORM ops.read_pdf_published_revision(product.base_task_id,product.base_product_key,product.base_content_digest);
 IF p_run IS NOT NULL AND NOT EXISTS(SELECT FROM ops.run requested JOIN ops.task origin ON origin.id=p_task
  JOIN ops.run producing ON producing.id=origin.run_id WHERE requested.id=p_run AND requested.project_id=producing.project_id) THEN
  RAISE EXCEPTION 'characterization product outside requested project' USING ERRCODE='23514'; END IF;
 IF p_max_bytes NOT BETWEEN 1 AND 8388608 OR octet_length(data.canonical_json(product.payload))>p_max_bytes THEN
  RAISE EXCEPTION 'characterization product exceeds read byte bound' USING ERRCODE='54000'; END IF;
 RETURN product.payload;
END $$;

CREATE OR REPLACE FUNCTION ops.read_characterization_memberships(p_task bigint,p_key text,p_digest text,p_groups jsonb,p_run bigint,p_after jsonb,p_layer_key text,p_limit bigint,p_max_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE view_ jsonb; answer jsonb;
BEGIN
 view_:=ops.read_characterization_product(p_task,p_key,p_digest,'view',p_run);
 IF (p_after IS NOT NULL AND (jsonb_typeof(p_after)<>'array' OR jsonb_array_length(p_after)<>3)) OR p_limit NOT BETWEEN 1 AND 1000 OR p_max_bytes NOT BETWEEN 1 AND 8388608
 OR jsonb_typeof(p_groups)<>'array' OR jsonb_array_length(p_groups)>256 THEN
  RAISE EXCEPTION 'invalid bounded membership selection' USING ERRCODE='22023'; END IF;
 WITH selected AS MATERIALIZED (
 SELECT pin,m.* FROM jsonb_array_elements(coalesce(view_->'layers','[]')) pin
 JOIN kb.characterization_membership m ON m.task_id=(pin->>'task_id')::bigint
  AND m.product_key=pin->>'product_key' AND m.content_digest=pin->>'content_digest'
 WHERE p_groups ? m.owner_id AND (p_layer_key IS NULL OR m.product_key=p_layer_key)
 AND (p_after IS NULL OR (m.task_id,m.product_key COLLATE "C",m.local_id COLLATE "C")>((p_after->>0)::bigint,(p_after->>1) COLLATE "C",(p_after->>2) COLLATE "C"))
 ORDER BY m.task_id,m.product_key COLLATE "C",m.local_id COLLATE "C" LIMIT p_limit+1
 ), positioned AS (SELECT *,row_number() OVER(ORDER BY task_id,product_key COLLATE "C",local_id COLLATE "C") page_position FROM selected),
 records AS (SELECT page_position,jsonb_build_object('layer',pin,'membership',m.body,'occurrences',
  (SELECT coalesce(jsonb_agg(o.body ORDER BY wanted.position),'[]')
   FROM jsonb_array_elements_text(m.body->'occurrences') WITH ORDINALITY wanted(id,position)
   JOIN kb.characterization_occurrence o ON o.task_id=m.task_id AND o.product_key=m.product_key
    AND o.content_digest=m.content_digest AND o.local_id=wanted.id)) body
 FROM positioned m WHERE page_position<=p_limit)
 SELECT jsonb_build_object('memberships',(SELECT coalesce(jsonb_agg(body ORDER BY page_position),'[]') FROM records),
  'next_after',CASE WHEN (SELECT count(*) FROM selected)>p_limit THEN (SELECT jsonb_build_array(task_id,product_key,local_id) FROM positioned WHERE page_position=p_limit) ELSE NULL END) INTO answer;
 IF octet_length(data.canonical_json(answer))>p_max_bytes THEN RAISE EXCEPTION 'membership response exceeds byte bound; reduce selected page' USING ERRCODE='54000'; END IF;
 RETURN answer;
END $$;

CREATE OR REPLACE FUNCTION ops.read_characterization_nodes(p_task bigint,p_key text,p_digest text,p_kind text,p_selectors jsonb,p_run bigint,p_after jsonb,p_limit bigint,p_max_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE view_ jsonb; answer jsonb;
BEGIN
 view_:=ops.read_characterization_product(p_task,p_key,p_digest,'view',p_run,8388608);
 IF p_kind NOT IN ('annotations','terms') OR p_limit NOT BETWEEN 1 AND 1000 OR p_max_bytes NOT BETWEEN 1 AND 8388608
 OR (p_after IS NOT NULL AND (jsonb_typeof(p_after)<>'array' OR jsonb_array_length(p_after)<>3))
 OR jsonb_typeof(p_selectors) IS DISTINCT FROM 'object'
 OR p_selectors-ARRAY['layer_key','family','annotation_kind','page','local_id']<>'{}'::jsonb THEN
  RAISE EXCEPTION 'invalid bounded characterization node selection' USING ERRCODE='22023'; END IF;
 WITH inventory AS (
  SELECT n.task_id,n.product_key,n.content_digest,n.local_id,n.family,n.kind,n.body FROM kb.characterization_annotation n WHERE p_kind='annotations'
  UNION ALL SELECT n.task_id,n.product_key,n.content_digest,n.local_id,n.family,n.kind,n.body FROM kb.characterization_term n WHERE p_kind='terms'
 ), selected AS MATERIALIZED (
  SELECT pin,n.* FROM jsonb_array_elements(coalesce(view_->'layers','[]')) pin JOIN inventory n
   ON n.task_id=(pin->>'task_id')::bigint AND n.product_key=pin->>'product_key' AND n.content_digest=pin->>'content_digest'
  WHERE (NOT p_selectors ? 'layer_key' OR n.product_key=p_selectors->>'layer_key')
   AND (NOT p_selectors ? 'family' OR n.family=p_selectors->>'family')
   AND (NOT p_selectors ? 'annotation_kind' OR n.kind=p_selectors->>'annotation_kind')
   AND (NOT p_selectors ? 'local_id' OR n.local_id=p_selectors->>'local_id')
   AND (NOT p_selectors ? 'page' OR EXISTS(SELECT FROM kb.characterization_extent e WHERE e.task_id=n.task_id
    AND e.product_key=n.product_key AND e.content_digest=n.content_digest AND n.body->'occurrences' ? e.occurrence_id AND e.page=(p_selectors->>'page')::bigint))
   AND (p_after IS NULL OR (n.task_id,n.product_key COLLATE "C",n.local_id COLLATE "C")>((p_after->>0)::bigint,(p_after->>1) COLLATE "C",(p_after->>2) COLLATE "C"))
  ORDER BY n.task_id,n.product_key COLLATE "C",n.local_id COLLATE "C" LIMIT p_limit+1
 ), positioned AS MATERIALIZED (SELECT *,row_number() OVER(ORDER BY task_id,product_key COLLATE "C",local_id COLLATE "C") position FROM selected),
 page_ AS MATERIALIZED (SELECT * FROM positioned WHERE position<=p_limit),
 occurrences AS MATERIALIZED (
  SELECT n.task_id,n.product_key,n.local_id node_id,o.body,w.position FROM page_ n
  CROSS JOIN LATERAL jsonb_array_elements_text(coalesce(n.body->'occurrences','[]')) WITH ORDINALITY w(id,position)
  JOIN kb.characterization_occurrence o ON o.task_id=n.task_id AND o.product_key=n.product_key AND o.content_digest=n.content_digest AND o.local_id=w.id
 ), roles AS MATERIALIZED (
  SELECT n.task_id,n.product_key,n.local_id node_id,r.body,r.local_id FROM page_ n JOIN kb.characterization_role r
   ON r.task_id=n.task_id AND r.product_key=n.product_key AND r.content_digest=n.content_digest
   AND (r.owner_id=n.local_id OR r.member_id=n.local_id)
 ), choices AS MATERIALIZED (
  SELECT DISTINCT n.task_id,n.product_key,n.local_id node_id,c.local_id,c.body FROM page_ n JOIN kb.characterization_choice_member m
   ON m.task_id=n.task_id AND m.product_key=n.product_key AND m.content_digest=n.content_digest
   AND (m.root_id=n.local_id OR n.body->'required_choices' ? m.local_id)
  JOIN kb.characterization_choice c ON c.task_id=m.task_id AND c.product_key=m.product_key AND c.content_digest=m.content_digest AND c.local_id=m.group_id
 ), sizes AS (SELECT coalesce(sum(octet_length(data.canonical_json(body))),0) bytes FROM (
  SELECT body FROM page_ UNION ALL SELECT body FROM occurrences UNION ALL SELECT body FROM roles UNION ALL SELECT body FROM choices) content)
 SELECT CASE WHEN (SELECT bytes FROM sizes)>p_max_bytes THEN NULL ELSE jsonb_build_object('nodes',
  (SELECT coalesce(jsonb_agg(jsonb_build_object('layer',n.pin,'node',n.body,
   'occurrences',(SELECT coalesce(jsonb_agg(o.body ORDER BY o.position),'[]') FROM occurrences o WHERE (o.task_id,o.product_key,o.node_id)=(n.task_id,n.product_key,n.local_id)),
   'roles',(SELECT coalesce(jsonb_agg(r.body ORDER BY r.local_id COLLATE "C"),'[]') FROM roles r WHERE (r.task_id,r.product_key,r.node_id)=(n.task_id,n.product_key,n.local_id)),
   'choices',(SELECT coalesce(jsonb_agg(c.body ORDER BY c.local_id COLLATE "C"),'[]') FROM choices c WHERE (c.task_id,c.product_key,c.node_id)=(n.task_id,n.product_key,n.local_id))) ORDER BY n.position),'[]') FROM page_ n),
  'next_after',CASE WHEN (SELECT count(*) FROM selected)>p_limit THEN (SELECT jsonb_build_array(task_id,product_key,local_id) FROM positioned WHERE position=p_limit) ELSE NULL END) END INTO answer;
 IF answer IS NULL OR octet_length(data.canonical_json(answer))>p_max_bytes THEN RAISE EXCEPTION 'characterization nodes exceed byte bound; reduce selected page' USING ERRCODE='54000'; END IF;
 RETURN answer;
END $$;
