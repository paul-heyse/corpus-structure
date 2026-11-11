CREATE OR REPLACE FUNCTION ops.validate_characterization_evidence(p_body jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE nodes jsonb; occurrences jsonb; runs jsonb; tokens jsonb; token_count bigint;
 a jsonb; detail jsonb; root jsonb; parent_ jsonb; correspondence jsonb; ref text; literal_ text;
 position_ bigint; normalized_ boolean; navigation_ jsonb; label_ jsonb; navigation_refs jsonb;
BEGIN
 SELECT coalesce(jsonb_object_agg(v->>'local_id',v),'{}') INTO nodes FROM jsonb_array_elements(coalesce(p_body->'annotations','[]')) v;
 SELECT coalesce(jsonb_object_agg(v->>'local_id',v),'{}') INTO occurrences FROM jsonb_array_elements(coalesce(p_body->'occurrences','[]')) v;
 SELECT coalesce(jsonb_object_agg(v->>'local_id',v),'{}') INTO runs FROM jsonb_array_elements(coalesce(p_body->'native_runs','[]')) v;
 IF (SELECT count(*) FROM jsonb_each(runs))<>jsonb_array_length(coalesce(p_body->'native_runs','[]')) THEN
  RAISE EXCEPTION 'duplicate native run identity' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_object_agg(jsonb_build_array(v->'native_token'->'native_run',v->'native_token'->'container',v->'native_token'->'index')::text,v->'native_token'),'{}'),count(*)
 INTO tokens,token_count FROM jsonb_array_elements(coalesce(p_body->'annotations','[]')) v WHERE v ? 'native_token';
 IF (SELECT count(*) FROM jsonb_each(tokens))<>token_count THEN
  RAISE EXCEPTION 'duplicate native token index within container' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT value FROM jsonb_each(nodes) LOOP
  navigation_:=a->'navigation';
  IF a->>'kind'='construction.navigation' AND navigation_ IS NULL THEN
   RAISE EXCEPTION 'navigation annotation requires typed source fields' USING ERRCODE='23514'; END IF;
  IF navigation_ IS NOT NULL THEN
   IF a->>'kind'<>'construction.navigation' OR a->>'family'<>'construction.navigation' THEN
    RAISE EXCEPTION 'navigation fields require their declared annotation family' USING ERRCODE='23514'; END IF;
   IF (SELECT count(*)<>count(DISTINCT role_->>'role') FROM jsonb_array_elements(coalesce(navigation_->'roles','[]')) role_) THEN
    RAISE EXCEPTION 'navigation role identity repeats' USING ERRCODE='23514'; END IF;
   SELECT coalesce(jsonb_agg(ref.id),'[]') INTO navigation_refs
    FROM jsonb_array_elements(coalesce(navigation_->'roles','[]')) role_
    CROSS JOIN LATERAL jsonb_array_elements_text(role_->'occurrences') ref(id);
   IF jsonb_array_length(navigation_refs)=0 OR EXISTS(SELECT FROM jsonb_array_elements_text(navigation_refs) ref WHERE NOT occurrences ? ref.value)
    OR NOT (navigation_refs @> coalesce(a->'occurrences','[]') AND coalesce(a->'occurrences','[]') @> navigation_refs) THEN
    RAISE EXCEPTION 'navigation roles must conserve their annotation source occurrences' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM jsonb_array_elements_text(navigation_refs) ref CROSS JOIN LATERAL jsonb_array_elements(occurrences->ref.value->'extents') e WHERE e->>'synthetic' IS DISTINCT FROM 'false' OR NOT e ? 'text') THEN
    RAISE EXCEPTION 'navigation fields require literal source evidence' USING ERRCODE='23514'; END IF;
   FOR label_ IN SELECT value FROM jsonb_array_elements(coalesce(navigation_->'source_labels','[]')) LOOP
    IF jsonb_array_length(label_->'occurrences')=0 OR NOT navigation_refs @> (label_->'occurrences') THEN
     RAISE EXCEPTION 'navigation source label differs from its literal source' USING ERRCODE='23514'; END IF;
    SELECT string_agg(e.body->>'text','' ORDER BY r.ord,e.ord) INTO literal_ FROM jsonb_array_elements_text(label_->'occurrences') WITH ORDINALITY r(id,ord)
     CROSS JOIN LATERAL jsonb_array_elements(occurrences->r.id->'extents') WITH ORDINALITY e(body,ord);
    IF literal_ IS DISTINCT FROM label_->>'value' THEN RAISE EXCEPTION 'navigation source label differs from its literal source' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(navigation_->'native_tokens','[]')) token_ WHERE NOT coalesce(a->'external_premises','[]') @> jsonb_build_array(token_->'native_node')) THEN
    RAISE EXCEPTION 'navigation native token requires its external premise' USING ERRCODE='23514'; END IF;
  END IF;
  detail:=a->'native_token';
  IF a->>'kind'='native.token' AND detail IS NULL THEN RAISE EXCEPTION 'native token requires typed columns' USING ERRCODE='23514'; END IF;
  IF detail IS NOT NULL AND (NOT runs ? (detail->>'native_run') OR NOT coalesce(nodes->(detail->>'container')->>'kind' IN ('native.block','native.sentence'),false)
   OR (detail ? 'sentence' AND nodes->(detail->>'sentence')->>'kind' IS DISTINCT FROM 'native.sentence')) THEN
   RAISE EXCEPTION 'native token population reference is missing' USING ERRCODE='23514'; END IF;
  IF detail IS NOT NULL THEN
   IF jsonb_array_length(coalesce(a->'occurrences','[]'))=0 OR EXISTS(SELECT FROM jsonb_array_elements_text(coalesce(a->'occurrences','[]')) ref WHERE NOT occurrences ? ref.value) THEN
    RAISE EXCEPTION 'native token requires its exact source occurrence' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM jsonb_array_elements_text(a->'occurrences') ref CROSS JOIN LATERAL jsonb_array_elements(occurrences->ref.value->'extents') e WHERE e->>'synthetic' IS DISTINCT FROM 'false' OR NOT e ? 'text') THEN
    RAISE EXCEPTION 'native token text differs from literal source' USING ERRCODE='23514'; END IF;
   SELECT string_agg(e.body->>'text','' ORDER BY r.ord,e.ord) INTO literal_ FROM jsonb_array_elements_text(a->'occurrences') WITH ORDINALITY r(id,ord)
    CROSS JOIN LATERAL jsonb_array_elements(occurrences->r.id->'extents') WITH ORDINALITY e(body,ord);
   IF literal_ IS DISTINCT FROM detail->>'text' THEN RAISE EXCEPTION 'native token text differs from literal source' USING ERRCODE='23514'; END IF;
  END IF;
  IF detail ? 'native_head' THEN
   IF NOT detail ? 'head_index_base' THEN RAISE EXCEPTION 'native head requires its index scheme' USING ERRCODE='23514'; END IF;
   IF NOT ((detail->>'head_index_base')::integer=1 AND (detail->>'native_head')::bigint=0)
    AND NOT tokens ? jsonb_build_array(detail->'native_run',detail->'container',to_jsonb((detail->>'native_head')::bigint-(detail->>'head_index_base')::bigint))::text THEN
    RAISE EXCEPTION 'native head is outside token population' USING ERRCODE='23514'; END IF;
  END IF;
  root:=a->'formal_input';
  IF a->>'kind'='formal.input' AND root IS NULL THEN RAISE EXCEPTION 'formal input requires typed input' USING ERRCODE='23514'; END IF;
  IF root IS NOT NULL THEN
   IF NOT occurrences ? (root->>'parent_occurrence') OR NOT coalesce(a->'occurrences' ? (root->>'parent_occurrence'),false) THEN
    RAISE EXCEPTION 'formal input parent is missing' USING ERRCODE='23514'; END IF;
   normalized_:=root->>'representation'='normalized_latex'; position_:=0;
   IF normalized_ AND coalesce(btrim(root->>'normalization_recipe'),'')='' THEN
    RAISE EXCEPTION 'normalized formal input requires its normalization recipe' USING ERRCODE='23514'; END IF;
   IF normalized_ THEN
    SELECT string_agg(e.body->>'text','' ORDER BY e.ord) INTO literal_ FROM jsonb_array_elements(occurrences->(root->>'parent_occurrence')->'extents') WITH ORDINALITY e(body,ord);
    IF root->>'original_text' IS DISTINCT FROM literal_ OR EXISTS(
     SELECT FROM jsonb_array_elements(occurrences->(root->>'parent_occurrence')->'extents') e WHERE e->>'synthetic'='true' OR NOT e ? 'text') THEN
     RAISE EXCEPTION 'normalized formal input requires its exact original source text' USING ERRCODE='23514'; END IF;
   END IF;
   FOR correspondence IN SELECT value FROM jsonb_array_elements(coalesce(root->'correspondence','[]')) LOOP
    IF normalized_ AND ((correspondence->>'input_start')::bigint<>position_ OR (correspondence->>'input_end')::bigint<=(correspondence->>'input_start')::bigint) THEN
     RAISE EXCEPTION 'normalized correspondence requires an ordered complete partition' USING ERRCODE='23514'; END IF;
    position_:=(correspondence->>'input_end')::bigint;
    IF (correspondence->>'input_end')::bigint<(correspondence->>'input_start')::bigint OR (correspondence->>'input_end')::bigint>char_length(root->>'text') THEN
     RAISE EXCEPTION 'formal correspondence exceeds input' USING ERRCODE='23514'; END IF;
    FOR ref IN SELECT jsonb_array_elements_text(coalesce(correspondence->'source_occurrences','[]')) LOOP
     IF NOT occurrences ? ref THEN RAISE EXCEPTION 'unknown formal correspondence source' USING ERRCODE='23514'; END IF;
    END LOOP;
    IF (correspondence->>'relation'='synthetic' AND (NOT correspondence ? 'boundary' OR jsonb_array_length(coalesce(correspondence->'source_occurrences','[]'))<>0))
    OR (correspondence->>'relation'<>'synthetic' AND jsonb_array_length(coalesce(correspondence->'source_occurrences','[]'))=0)
    OR (correspondence->>'relation'='contained_in_atom' AND correspondence->'source_occurrences' IS DISTINCT FROM jsonb_build_array(root->>'parent_occurrence')) THEN
     RAISE EXCEPTION 'formal correspondence invents literal support' USING ERRCODE='23514'; END IF;
    IF correspondence->>'relation'='synthetic' AND NOT EXISTS(
     SELECT FROM jsonb_array_elements(occurrences->(root->>'parent_occurrence')->'extents') e
     WHERE (e->>'start')::bigint<=(correspondence->>'boundary')::bigint AND (correspondence->>'boundary')::bigint<=(e->>'end')::bigint) THEN
     RAISE EXCEPTION 'synthetic correspondence boundary is outside parent source' USING ERRCODE='23514'; END IF;
    IF normalized_ AND (correspondence->>'relation'='contained_in_atom' OR EXISTS(
     SELECT FROM jsonb_array_elements_text(coalesce(correspondence->'source_occurrences','[]')) r
     CROSS JOIN LATERAL jsonb_array_elements(occurrences->r.value->'extents') e WHERE e->>'synthetic'='true' OR NOT e ? 'text')) THEN
     RAISE EXCEPTION 'normalized correspondence requires literal source support' USING ERRCODE='23514'; END IF;
    IF normalized_ AND EXISTS(
     SELECT FROM jsonb_array_elements_text(coalesce(correspondence->'source_occurrences','[]')) r
     CROSS JOIN LATERAL jsonb_array_elements(occurrences->r.value->'extents') e
     WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(occurrences->(root->>'parent_occurrence')->'extents') parent
      WHERE parent->'projection'=e->'projection' AND parent->'source_view_id'=e->'source_view_id' AND parent->'native_pointer'=e->'native_pointer'
       AND (parent->>'start')::bigint<=(e->>'start')::bigint AND (e->>'end')::bigint<=(parent->>'end')::bigint)) THEN
     RAISE EXCEPTION 'normalized correspondence source is outside its parent' USING ERRCODE='23514'; END IF;
    IF correspondence->>'relation'='exact' THEN
     IF EXISTS(SELECT FROM jsonb_array_elements_text(correspondence->'source_occurrences') r CROSS JOIN LATERAL jsonb_array_elements(occurrences->r.value->'extents') e WHERE e->>'synthetic'='true' OR NOT e ? 'text') THEN
      RAISE EXCEPTION 'exact correspondence requires literal text' USING ERRCODE='23514'; END IF;
     SELECT string_agg(e.body->>'text','' ORDER BY r.ord,e.ord) INTO literal_ FROM jsonb_array_elements_text(correspondence->'source_occurrences') WITH ORDINALITY r(id,ord)
      CROSS JOIN LATERAL jsonb_array_elements(occurrences->r.id->'extents') WITH ORDINALITY e(body,ord);
     IF literal_ IS DISTINCT FROM substring(root->>'text' FROM (correspondence->>'input_start')::integer+1 FOR (correspondence->>'input_end')::integer-(correspondence->>'input_start')::integer) THEN
      RAISE EXCEPTION 'formal correspondence differs from literal source' USING ERRCODE='23514'; END IF;
    END IF;
   END LOOP;
   IF normalized_ AND position_<>char_length(root->>'text') THEN
    RAISE EXCEPTION 'normalized correspondence requires an ordered complete partition' USING ERRCODE='23514'; END IF;
  END IF;
  detail:=a->'formal';
  IF a->>'kind' IN ('formal.token','formal.rule','formal.symbol') AND detail IS NULL THEN RAISE EXCEPTION 'formal node requires typed positions' USING ERRCODE='23514'; END IF;
  IF detail IS NOT NULL THEN
   IF detail ? 'symbol_parent' THEN
    parent_:=nodes->(detail->>'symbol_parent');
    IF parent_->>'kind' IS DISTINCT FROM 'formal.symbol' OR parent_->'formal'->>'input_id' IS DISTINCT FROM detail->>'input_id'
     OR NOT coalesce((parent_->'formal'->>'start')::bigint<=(detail->>'start')::bigint AND (detail->>'end')::bigint<=(parent_->'formal'->>'end')::bigint,false) THEN
     RAISE EXCEPTION 'formal symbol parent differs from positioned enclosing symbol' USING ERRCODE='23514'; END IF;
   END IF;
   IF detail->'normalized'->>'kind' IN ('decimal','threshold') AND detail->'normalized'->>'domain_status'='valid'
    AND coalesce(detail->'normalized'->>'value','') !~ '^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$' THEN
    RAISE EXCEPTION 'formal decimal requires exact finite decimal text' USING ERRCODE='23514'; END IF;
   root:=nodes->(detail->>'input_id')->'formal_input';
   IF root IS NULL OR (detail->>'start')::bigint>(detail->>'end')::bigint OR (detail->>'end')::bigint>char_length(root->>'text')
    OR (detail->>'start'=detail->>'end' AND NOT coalesce((detail->>'synthetic')::boolean,false))
    OR ((detail ? 'container_start')<>(detail ? 'container_end'))
    OR (detail ? 'container_start' AND ((detail->>'container_start')::bigint>(detail->>'start')::bigint OR (detail->>'container_end')::bigint<(detail->>'end')::bigint OR (detail->>'container_end')::bigint>char_length(root->>'text'))) THEN
     RAISE EXCEPTION 'formal node is outside represented input/container' USING ERRCODE='23514'; END IF;
  END IF;
 END LOOP;
 IF EXISTS(WITH RECURSIVE edges AS (
  SELECT annotation_.node->>'local_id' owner,annotation_.node->'formal'->>'symbol_parent' target
  FROM jsonb_array_elements(coalesce(p_body->'annotations','[]')) annotation_(node)
  WHERE annotation_.node->'formal' ? 'symbol_parent'
 ), reach(owner,target) AS (
  SELECT owner,target FROM edges UNION SELECT r.owner,e.target FROM reach r JOIN edges e ON e.owner=r.target
 ) SELECT FROM reach WHERE owner=target) THEN
  RAISE EXCEPTION 'formal symbol parent cycle' USING ERRCODE='23514'; END IF;
END $$;

-- Mechanical proof relationships; this does not run a linguistic recognizer.
CREATE OR REPLACE FUNCTION ops.validate_characterization_support(p_body jsonb,p_role jsonb,p_support jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE nodes jsonb; basis jsonb:=p_role->'basis'; construction jsonb; binding jsonb; production jsonb; member_ jsonb; witness jsonb;
BEGIN
 SELECT jsonb_object_agg(node->>'local_id',node) INTO nodes FROM jsonb_array_elements(
  coalesce(p_body->'annotations','[]')||coalesce(p_body->'memberships','[]')||coalesce(p_body->'terms','[]')) node;
 construction:=nodes->(basis->>'construction'); binding:=nodes->(basis->>'binding'); production:=nodes->(basis->>'production');
 member_:=nodes->(p_role->>'member');
 IF p_support->>'codec' IS DISTINCT FROM 'construction-membership-v1'
 OR NOT coalesce(basis->'premises' @> jsonb_build_array(basis->>'construction',basis->>'binding',basis->>'production'),false)
 OR construction->>'kind' IS DISTINCT FROM 'construction'
 OR construction->>'rule_id' IS DISTINCT FROM basis->>'rule_id'
 OR p_role->>'owner' IS DISTINCT FROM basis->>'construction'
 OR binding->>'group' IS DISTINCT FROM basis->>'construction'
 OR binding->>'member' IS DISTINCT FROM p_role->>'member'
 OR binding->>'role' IS DISTINCT FROM p_role->>'role'
 OR NOT coalesce(p_support->'roles' ? (p_role->>'role'),false)
 OR NOT coalesce(construction->'premises' ? (basis->>'production'),false)
 OR production->>'kind' IS DISTINCT FROM 'grammar.production'
 OR production->>'native_label' IS DISTINCT FROM p_support->>'production'
 OR coalesce(p_role->'occurrences','[]') IS DISTINCT FROM coalesce(binding->'occurrences','[]')
 OR NOT coalesce(member_->'occurrences','[]') @> coalesce(binding->'occurrences','[]')
 OR NOT coalesce(p_role->'required_choices','[]') @> coalesce(basis->'choice_refs','[]')
 OR NOT coalesce(basis->'choice_refs','[]') @> coalesce(p_role->'required_choices','[]') THEN
  RAISE EXCEPTION 'attachment endpoints differ from released construction witness' USING ERRCODE='23514'; END IF;
 FOR witness IN SELECT value FROM jsonb_array_elements(jsonb_build_array(construction,binding,production,member_,basis)) LOOP
  IF NOT coalesce(p_role->'required_choices','[]') @> coalesce(witness->'required_choices','[]')
   OR NOT coalesce(p_role->'required_external_choices','[]') @> coalesce(witness->'required_external_choices','[]') THEN
   RAISE EXCEPTION 'attachment loses required witness choices' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF NOT EXISTS(WITH RECURSIVE reach(id) AS (
  SELECT value FROM jsonb_array_elements_text(coalesce(production->'premises','[]'))
  UNION SELECT child FROM reach CROSS JOIN LATERAL jsonb_array_elements_text(coalesce(nodes->reach.id->'premises','[]')) child
 ) SELECT FROM reach WHERE id=p_role->>'member') THEN
  RAISE EXCEPTION 'attachment member is outside witnessed production' USING ERRCODE='23514'; END IF;
END $$;

-- One coordinate rule for selection and family coverage, including empty results.
CREATE OR REPLACE FUNCTION ops.validate_characterization_selector(p_views jsonb,p_selector jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE v kb.source_view; pointer_ text:=p_selector->>'native_pointer'; found_ boolean:=false;
BEGIN
 FOR v IN SELECT * FROM kb.source_view WHERE p_views @> jsonb_build_array(id) AND projection_digest=p_selector->>'projection' LOOP
 found_:=true;
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
 END LOOP;
 IF NOT found_ THEN RAISE EXCEPTION 'selector cannot resolve exact qualified source projection' USING ERRCODE='23514'; END IF;
END $$;

-- Reading an immutable historical product needs its original read contract,
-- not the ability to execute all of its former producers on today's layout.
CREATE OR REPLACE FUNCTION ops.require_characterization_read_release(p_release text)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release r JOIN sem.release_finalization f USING(release_id)
  WHERE r.release_id=p_release AND f.content_digest=r.content_digest) THEN
  RAISE EXCEPTION 'retained characterization requires a finalized original release' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_execution_projection(p_release);
 PERFORM sem.require_execution_operation(p_release,'read_characterization');
END $$;
REVOKE ALL ON FUNCTION ops.require_characterization_read_release(text) FROM PUBLIC;

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
  IF p_body->>'profile'='full_characterization' THEN
   SELECT convert_from(content,'UTF8')::jsonb INTO policies FROM sem.artifact WHERE release_id=t.release_id AND artifact_name='characterization/profiles.json';
   IF policies->'full_characterization' IS NULL OR EXISTS(
    SELECT FROM jsonb_array_elements_text(policies->'full_characterization') required(family)
    WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(coalesce(p_body->'coverage','[]')) c WHERE c->>'family'=required.family)) THEN
    RAISE EXCEPTION 'full characterization requires every released baseline family outcome' USING ERRCODE='23514'; END IF;
  END IF;
  IF method_.name='text.compose_view' AND (coalesce(p_body->'layers','[]') IS DISTINCT FROM coalesce(cfg.params->'characterization_layers','[]') OR p_body->>'profile' IS DISTINCT FROM cfg.params->>'characterization_profile' OR coalesce(p_body->'active_layers',p_body->'layers','[]') IS DISTINCT FROM coalesce(nullif(cfg.params->'characterization_active_layers','null'),cfg.params->'characterization_layers','[]')) THEN
   RAISE EXCEPTION 'view selection differs from producing configuration' USING ERRCODE='23514'; END IF;
  FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(p_body->'layers','[]')) LOOP
   SELECT * INTO STRICT dep FROM ops.characterization_product WHERE task_id=(ref->>'task_id')::bigint
    AND product_key=ref->>'product_key' AND content_digest=ref->>'content_digest' AND kind='layer';
   IF NOT dep.release_id=ANY(checked_releases) THEN
    PERFORM ops.require_characterization_read_release(dep.release_id);
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
  IF NOT coalesce(p_body->'layers','[]') @> coalesce(p_body->'active_layers',p_body->'layers','[]')
   OR (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(coalesce(p_body->'active_layers',p_body->'layers','[]')))
   OR (jsonb_array_length(coalesce(p_body->'layers','[]'))>0 AND jsonb_array_length(coalesce(p_body->'active_layers',p_body->'layers','[]'))=0) THEN
   RAISE EXCEPTION 'active layers must be a nonempty distinct subset of retained closure' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(p_body->'coverage','[]')) c WHERE NOT EXISTS(
   SELECT FROM jsonb_array_elements(coalesce(p_body->'active_layers',p_body->'layers','[]')) l JOIN ops.characterization_product d
    ON d.task_id=(l->>'task_id')::bigint AND d.product_key=l->>'product_key' AND d.content_digest=l->>'content_digest'
   WHERE d.payload->'coverage' @> jsonb_build_array(c))) THEN
   RAISE EXCEPTION 'view coverage is not recorded by selected layers' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 IF p_body->>'outcome'='failed' THEN RAISE EXCEPTION 'failed analysis cannot publish a layer' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_characterization_evidence(p_body);
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
    PERFORM ops.require_characterization_read_release(dep.release_id);
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
    IF policy ? 'support' THEN PERFORM ops.validate_characterization_support(p_body,row_,policy->'support'); END IF;
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
     IF (item ? 'target')=(item ? 'choice_group')
      OR (item ? 'target' AND NOT item->>'target'=ANY(terms))
      OR (item ? 'choice_group' AND NOT item->>'choice_group'=ANY(group_ids)) THEN
      RAISE EXCEPTION 'invalid term or packed choice site' USING ERRCODE='23514'; END IF;
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
  SELECT value FROM jsonb_array_elements(coalesce(p_body->'annotations','[]')||coalesce(p_body->'memberships','[]')||coalesce(p_body->'roles','[]')||coalesce(p_body->'terms','[]'))
  UNION ALL SELECT value->'basis' FROM jsonb_array_elements(coalesce(p_body->'roles','[]'))
  UNION ALL SELECT member FROM jsonb_array_elements(coalesce(p_body->'choices','[]')) g CROSS JOIN LATERAL jsonb_array_elements(g->'members') member
 LOOP
  FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(item->'external_premises','[]')||coalesce(item->'required_external_choices','[]')) LOOP
   IF NOT coalesce(p_body->'dependencies','[]') @> jsonb_build_array(ref->'layer')
   OR NOT EXISTS(SELECT FROM ops.characterization_product d CROSS JOIN LATERAL jsonb_each(d.payload) f
    CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN f.key IN ('annotations','memberships','roles','terms','occurrences','choices') THEN f.value ELSE '[]'::jsonb END) node
    WHERE d.task_id=(ref->'layer'->>'task_id')::bigint AND d.product_key=ref->'layer'->>'product_key'
     AND d.content_digest=ref->'layer'->>'content_digest' AND (node->>'local_id'=ref->>'local_id' OR (f.key='choices' AND EXISTS(SELECT FROM jsonb_array_elements(node->'members') member WHERE member->>'local_id'=ref->>'local_id')))) THEN
    RAISE EXCEPTION 'qualified premise is outside declared layer closure' USING ERRCODE='23514'; END IF;
  END LOOP;
  FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(item->'required_external_choices','[]')) LOOP
   IF NOT EXISTS(SELECT FROM ops.characterization_product d CROSS JOIN LATERAL jsonb_array_elements(coalesce(d.payload->'choices','[]')) g
     CROSS JOIN LATERAL jsonb_array_elements(g->'members') m
     WHERE d.task_id=(ref->'layer'->>'task_id')::bigint AND d.product_key=ref->'layer'->>'product_key'
     AND d.content_digest=ref->'layer'->>'content_digest' AND m->>'local_id'=ref->>'local_id') THEN
    RAISE EXCEPTION 'required external choice is not a choice member' USING ERRCODE='23514'; END IF;
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
  SELECT node->>'local_id' owner,coalesce(child->>'target',child->>'choice_group') target FROM jsonb_array_elements(coalesce(p_body->'terms','[]')) node
   CROSS JOIN LATERAL jsonb_array_elements(coalesce(node->'children','[]')) child WHERE child->>'structural'='true'
  UNION ALL SELECT g->>'local_id',m->>'root' FROM jsonb_array_elements(coalesce(p_body->'choices','[]')) g CROSS JOIN LATERAL jsonb_array_elements(g->'members') m
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

CREATE OR REPLACE FUNCTION ops.publish_characterization(p_task bigint,p_attempt bigint,p_holder text,p_layer jsonb,p_view jsonb,p_cost jsonb DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; r ops.run; body jsonb; kind_ text; digest_ text; key_ text; result_ jsonb:='{}'; terminal_digest text; family text;
BEGIN
 PERFORM data.require_runtime_principal('write');
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id FOR SHARE;
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task FOR UPDATE;
 terminal_digest:=encode(sha256(convert_to(data.canonical_json(jsonb_build_array(p_layer,p_view,p_cost)),'UTF8')),'hex');
 IF t.status='done' AND t.attempt=p_attempt AND t.claimed_by=p_holder AND t.result_digest=terminal_digest THEN
  RETURN jsonb_build_object('transaction','replay','products',(SELECT jsonb_object_agg(kind,jsonb_build_object('task_id',task_id,'product_key',product_key,'content_digest',content_digest)) FROM ops.characterization_product WHERE task_id=p_task),'receipt',jsonb_build_object('task_id',t.id,'run_id',t.run_id,'release_id',t.release_id,'attempt',t.attempt,'protocol','done','result_digest',t.result_digest,'observation_ids','[]'::jsonb));
 END IF;
 IF r.sealed OR r.status NOT IN ('created','running') OR t.status<>'running' OR t.attempt<>p_attempt OR t.claimed_by IS DISTINCT FROM p_holder THEN
  RAISE EXCEPTION 'characterization task attempt lost or run sealed' USING ERRCODE='P0004'; END IF;
 IF octet_length(coalesce(data.canonical_json(p_layer),''))>8388608 OR octet_length(coalesce(data.canonical_json(p_view),''))>8388608 THEN
  RAISE EXCEPTION 'characterization report exceeds bounded payload contract' USING ERRCODE='54000'; END IF;
 -- Fresh publication executes today's released producer; immutable upstream reads
 -- independently use their original read contracts.
 PERFORM data.require_execution_release(t.release_id);
 PERFORM data.record_source_json(p_cost);
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
  INSERT INTO kb.characterization_source_scope(task_id,product_key,content_digest,source_view_id,body)
   SELECT t.id,key_,digest_,(v->>'source_view_id')::bigint,v FROM jsonb_array_elements(body->'source_scope'->'source_views') v;
  IF kind_='layer' THEN
   INSERT INTO kb.characterization_occurrence SELECT t.id,key_,digest_,v->>'local_id',v->>'local_id',v->'extents'->0->>'projection',(v->'extents'->0->>'source_view_id')::bigint,v FROM jsonb_array_elements(coalesce(body->'occurrences','[]')) v;
   INSERT INTO kb.characterization_annotation SELECT t.id,key_,digest_,v->>'local_id',v->>'kind',v->>'family',v FROM jsonb_array_elements(coalesce(body->'annotations','[]')) v;
   INSERT INTO kb.characterization_membership SELECT t.id,key_,digest_,v->>'local_id',v->>'group',v->>'member',v->>'role',(v->>'order')::bigint,v->>'family',v FROM jsonb_array_elements(coalesce(body->'memberships','[]')) v;
   INSERT INTO kb.characterization_role SELECT t.id,key_,digest_,v->>'local_id',v->>'owner',v->>'member',v->>'role',v->>'family',v FROM jsonb_array_elements(coalesce(body->'roles','[]')) v;
   INSERT INTO kb.characterization_term SELECT t.id,key_,digest_,v->>'local_id',v->>'kind',v->>'family',v FROM jsonb_array_elements(coalesce(body->'terms','[]')) v;
   INSERT INTO kb.characterization_choice SELECT t.id,key_,digest_,v->>'local_id',v->>'family',v FROM jsonb_array_elements(coalesce(body->'choices','[]')) v;
   INSERT INTO kb.characterization_extent SELECT t.id,key_,digest_,v->>'local_id',e.position-1,e.body->>'projection',(e.body->>'source_view_id')::bigint,e.body->>'native_pointer',(e.body->>'page')::bigint,(e.body->>'start')::bigint,(e.body->>'end')::bigint,e.body
    FROM jsonb_array_elements(coalesce(body->'occurrences','[]')) v CROSS JOIN LATERAL jsonb_array_elements(v->'extents') WITH ORDINALITY e(body,position);
   INSERT INTO kb.characterization_term_edge SELECT t.id,key_,digest_,v->>'local_id',e.position-1,coalesce(e.body->>'target',e.body->>'choice_group'),e.body->>'role',(e.body->>'structural')::boolean,e.body
    FROM jsonb_array_elements(coalesce(body->'terms','[]')) v CROSS JOIN LATERAL jsonb_array_elements(coalesce(v->'children','[]')) WITH ORDINALITY e(body,position);
   INSERT INTO kb.characterization_choice_member SELECT t.id,key_,digest_,v->>'local_id',e->>'local_id',e->>'root',e
    FROM jsonb_array_elements(coalesce(body->'choices','[]')) v CROSS JOIN LATERAL jsonb_array_elements(v->'members') e;
   INSERT INTO kb.characterization_coverage SELECT t.id,key_,digest_,v->>'family',v->>'family',v->>'outcome',v FROM jsonb_array_elements(body->'coverage') v;
  END IF;
 END LOOP;
 INSERT INTO ops.task_result(task_id,release_id,body) VALUES(t.id,t.release_id,jsonb_build_object('characterization',result_,'outcome','produced','cost',p_cost));
 UPDATE ops.task SET status='done',result_digest=terminal_digest,finished_at=clock_timestamp(),lease_until=NULL,error=NULL WHERE id=t.id;
 RETURN jsonb_build_object('transaction','applied','products',result_,'receipt',jsonb_build_object('task_id',t.id,'run_id',t.run_id,'release_id',t.release_id,'attempt',t.attempt,'protocol','done','result_digest',terminal_digest,'observation_ids','[]'::jsonb));
END $$;

CREATE OR REPLACE FUNCTION ops.read_primary_characterization(p_run bigint,p_view bigint,p_refs jsonb,p_max_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ref jsonb; body jsonb; rows_ jsonb:='[]'; remaining bigint:=p_max_bytes; project_ text;
BEGIN
 IF pg_has_role(session_user,'corpus_sem_reader','USAGE') THEN PERFORM data.require_runtime_principal('read');
 ELSIF pg_has_role(session_user,'corpus_sem_writer','USAGE') THEN PERFORM data.require_runtime_principal('write');
 ELSE PERFORM data.require_runtime_principal('evaluate'); END IF;
 SELECT project_id INTO STRICT project_ FROM ops.run WHERE id=p_run;
 IF p_max_bytes NOT BETWEEN 1 AND 8388608 OR jsonb_typeof(p_refs)<>'array' OR jsonb_array_length(p_refs)>1000 THEN
  RAISE EXCEPTION 'invalid primary selection bounds' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(p_refs)) OR EXISTS(
  SELECT FROM jsonb_array_elements(p_refs) r WHERE NOT EXISTS(SELECT FROM ops.characterization_product p JOIN ops.task t ON t.id=p.task_id JOIN ops.run job ON job.id=t.run_id
   WHERE p.task_id=(r->>'task_id')::bigint AND p.product_key=r->>'product_key' AND p.content_digest=r->>'content_digest'
    AND p.kind='layer' AND t.status='done' AND job.project_id=project_)) THEN
  RAISE EXCEPTION 'primary selection includes an unavailable or foreign layer' USING ERRCODE='23514'; END IF;
 FOR ref IN SELECT r FROM jsonb_array_elements(p_refs) r JOIN kb.characterization_source_scope scope
  ON scope.task_id=(r->>'task_id')::bigint AND scope.product_key=r->>'product_key' AND scope.content_digest=r->>'content_digest'
  WHERE scope.source_view_id=p_view ORDER BY scope.task_id,scope.product_key LOOP
  IF remaining<=0 THEN RAISE EXCEPTION 'primary layers exceed source read budget' USING ERRCODE='54000'; END IF;
  body:=ops.read_characterization_product((ref->>'task_id')::bigint,ref->>'product_key',ref->>'content_digest','layer',p_run,remaining);
  remaining:=remaining-octet_length(data.canonical_json(body));
  rows_:=rows_||jsonb_build_array(jsonb_build_object('reference',ref,'payload',body));
 END LOOP;
 RETURN jsonb_build_object('layers',rows_);
END $$;

CREATE OR REPLACE FUNCTION ops.read_characterization_inventory(p_run bigint,p_after_task bigint,p_after_key text,p_limit bigint,p_max_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result_ jsonb; rows_ jsonb; last_ jsonb; requested ops.run; row_ jsonb;
BEGIN
 IF pg_has_role(session_user,'corpus_sem_reader','USAGE') THEN PERFORM data.require_runtime_principal('read');
 ELSIF pg_has_role(session_user,'corpus_sem_writer','USAGE') THEN PERFORM data.require_runtime_principal('write');
 ELSE PERFORM data.require_runtime_principal('evaluate'); END IF;
 SELECT * INTO STRICT requested FROM ops.run WHERE id=p_run;
 PERFORM sem.require_execution_operation(requested.release_id,'read_characterization_inventory');
 IF p_limit NOT BETWEEN 1 AND 1000 OR p_max_bytes NOT BETWEEN 1 AND 8388608 OR ((p_after_task IS NULL)<>(p_after_key IS NULL)) THEN
  RAISE EXCEPTION 'invalid characterization inventory bounds/cursor' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_agg(body ORDER BY task_id,product_key),'[]') INTO rows_ FROM (
  SELECT DISTINCT p.task_id,p.product_key,jsonb_build_object('reference',jsonb_build_object('task_id',p.task_id,'product_key',p.product_key,'content_digest',p.content_digest),
   'kind',p.kind,'release_id',p.release_id,'method',m.name,'configuration',cfg.config_hash,'source_view_ids',(SELECT jsonb_agg(s.source_view_id ORDER BY s.source_view_id) FROM kb.characterization_source_scope s WHERE (s.task_id,s.product_key,s.content_digest)=(p.task_id,p.product_key,p.content_digest))) body
  FROM ops.task selected JOIN ops.characterization_product p ON p.task_id=coalesce(selected.reused_task_id,selected.id)
   JOIN ops.task origin ON origin.id=p.task_id JOIN ops.run producer ON producer.id=origin.run_id
   JOIN ops.method_config cfg ON cfg.id=origin.method_config_id JOIN ops.method m ON m.id=cfg.method_id
  WHERE selected.run_id=p_run AND selected.status IN ('done','reused') AND origin.status='done'
   AND producer.project_id=requested.project_id
   AND (p_after_task IS NULL OR (p.task_id,p.product_key)>(p_after_task,p_after_key))
  ORDER BY p.task_id,p.product_key LIMIT p_limit+1
 ) bounded;
 last_:=CASE WHEN jsonb_array_length(rows_)>p_limit THEN rows_->(p_limit::integer-1)->'reference' ELSE NULL END;
 SELECT coalesce(jsonb_agg(value ORDER BY ord),'[]') INTO rows_ FROM jsonb_array_elements(rows_) WITH ORDINALITY e(value,ord) WHERE ord<=p_limit;
 FOR row_ IN SELECT value FROM jsonb_array_elements(rows_) LOOP
  PERFORM ops.require_characterization_read_release(row_->>'release_id');
 END LOOP;
 result_:=jsonb_build_object('products',rows_,'continuation',CASE WHEN last_ IS NULL THEN NULL ELSE jsonb_build_array(last_->'task_id',last_->'product_key') END);
 IF octet_length(data.canonical_json(result_))>p_max_bytes THEN RAISE EXCEPTION 'characterization inventory exceeds byte budget' USING ERRCODE='54000'; END IF;
 RETURN result_;
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
 PERFORM ops.require_characterization_read_release(product.release_id);
 IF product.payload->>'release_id' IS DISTINCT FROM product.release_id
 OR product.payload->>'format' IS DISTINCT FROM (CASE product.kind WHEN 'layer' THEN 'characterization-layer-v1' ELSE 'enriched-document-view-v1' END) THEN
  RAISE EXCEPTION 'unsupported retained characterization format or release binding' USING ERRCODE='23514'; END IF;
 PERFORM ops.read_pdf_published_revision(product.base_task_id,product.base_product_key,product.base_content_digest);
 IF p_run IS NOT NULL AND NOT EXISTS(SELECT FROM ops.run requested JOIN ops.task origin ON origin.id=p_task
  JOIN ops.run producing ON producing.id=origin.run_id WHERE requested.id=p_run AND requested.project_id=producing.project_id) THEN
  RAISE EXCEPTION 'characterization product outside requested project' USING ERRCODE='23514'; END IF;
 -- A document view contains the book's bounded source/family metadata, rather than
 -- annotation inventories. Keep natural-unit layer payloads under their smaller cap.
 IF p_max_bytes IS NULL OR p_max_bytes NOT BETWEEN 1 AND (CASE p_kind WHEN 'view' THEN 67108864 ELSE 8388608 END)
 OR octet_length(data.canonical_json(product.payload))>p_max_bytes THEN
  RAISE EXCEPTION 'characterization product exceeds read byte bound' USING ERRCODE='54000'; END IF;
 RETURN product.payload;
END $$;

CREATE OR REPLACE FUNCTION ops.read_characterization_layer_manifest(p_task bigint,p_key text,p_digest text,p_run bigint DEFAULT NULL,p_max_bytes bigint DEFAULT 8388608)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE product ops.characterization_product; result_ jsonb; header_ jsonb;
BEGIN
 IF pg_has_role(session_user,'corpus_sem_reader','USAGE') THEN PERFORM data.require_runtime_principal('read');
 ELSIF pg_has_role(session_user,'corpus_sem_writer','USAGE') THEN PERFORM data.require_runtime_principal('write');
 ELSE PERFORM data.require_runtime_principal('evaluate'); END IF;
 SELECT p.* INTO STRICT product FROM ops.characterization_product p JOIN ops.task t ON t.id=p.task_id
 WHERE p.task_id=p_task AND p.product_key=p_key AND p.content_digest=p_digest AND p.kind='layer' AND t.status='done';
 PERFORM ops.require_characterization_read_release(product.release_id);
 IF product.payload->>'release_id' IS DISTINCT FROM product.release_id
 OR product.payload->>'format' IS DISTINCT FROM 'characterization-layer-v1' THEN
  RAISE EXCEPTION 'unsupported retained characterization format or release binding' USING ERRCODE='23514'; END IF;
 PERFORM ops.read_pdf_published_revision(product.base_task_id,product.base_product_key,product.base_content_digest);
 IF p_run IS NOT NULL AND NOT EXISTS(SELECT FROM ops.run requested JOIN ops.task origin ON origin.id=p_task
  JOIN ops.run producing ON producing.id=origin.run_id WHERE requested.id=p_run AND requested.project_id=producing.project_id) THEN
  RAISE EXCEPTION 'characterization product outside requested project' USING ERRCODE='23514'; END IF;
 SELECT jsonb_object_agg(key,value) INTO header_ FROM jsonb_each(product.payload)
 WHERE key IN ('format','release_id','base_document','operation','source_scope','outcome','dependencies','coverage');
 result_:=jsonb_build_object('reference',jsonb_build_object('task_id',p_task,'product_key',p_key,'content_digest',p_digest),'kind','layer','payload',header_);
 IF p_max_bytes IS NULL OR p_max_bytes NOT BETWEEN 1 AND 8388608 OR octet_length(data.canonical_json(result_))>p_max_bytes THEN
  RAISE EXCEPTION 'characterization manifest exceeds read byte bound' USING ERRCODE='54000'; END IF;
 RETURN result_;
END $$;

CREATE OR REPLACE FUNCTION ops.read_characterization_memberships(p_task bigint,p_key text,p_digest text,p_groups jsonb,p_run bigint,p_after jsonb,p_layer_key text,p_limit bigint,p_max_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE view_ jsonb; answer jsonb;
BEGIN
 view_:=ops.read_characterization_product(p_task,p_key,p_digest,'view',p_run,67108864);
 IF (p_after IS NOT NULL AND (jsonb_typeof(p_after)<>'array' OR jsonb_array_length(p_after)<>3)) OR p_limit NOT BETWEEN 1 AND 1000 OR p_max_bytes NOT BETWEEN 1 AND 8388608
 OR jsonb_typeof(p_groups)<>'array' OR jsonb_array_length(p_groups)>256 THEN
  RAISE EXCEPTION 'invalid bounded membership selection' USING ERRCODE='22023'; END IF;
 WITH selected AS MATERIALIZED (
 SELECT pin,m.* FROM jsonb_array_elements(CASE WHEN p_layer_key IS NULL THEN coalesce(view_->'active_layers',view_->'layers','[]') ELSE coalesce(view_->'layers','[]') END) pin
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
 view_:=ops.read_characterization_product(p_task,p_key,p_digest,'view',p_run,67108864);
 IF p_kind NOT IN ('annotations','terms') OR p_limit NOT BETWEEN 1 AND 1000 OR p_max_bytes NOT BETWEEN 1 AND 8388608
 OR (p_after IS NOT NULL AND (jsonb_typeof(p_after)<>'array' OR jsonb_array_length(p_after)<>3))
 OR jsonb_typeof(p_selectors) IS DISTINCT FROM 'object'
 OR p_selectors-ARRAY['layer_key','family','annotation_kind','page','local_id']<>'{}'::jsonb THEN
  RAISE EXCEPTION 'invalid bounded characterization node selection' USING ERRCODE='22023'; END IF;
 WITH inventory AS (
  SELECT n.task_id,n.product_key,n.content_digest,n.local_id,n.family,n.kind,n.body FROM kb.characterization_annotation n WHERE p_kind='annotations'
  UNION ALL SELECT n.task_id,n.product_key,n.content_digest,n.local_id,n.family,n.kind,n.body FROM kb.characterization_term n WHERE p_kind='terms'
 ), selected AS MATERIALIZED (
  SELECT pin,n.* FROM jsonb_array_elements(CASE WHEN p_selectors ? 'layer_key' THEN coalesce(view_->'layers','[]') ELSE coalesce(view_->'active_layers',view_->'layers','[]') END) pin JOIN inventory n
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
