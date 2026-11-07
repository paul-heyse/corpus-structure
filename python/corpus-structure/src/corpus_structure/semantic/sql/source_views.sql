-- Immutable section views are instances, never fabricated document/rendition rows.
CREATE OR REPLACE FUNCTION ops.validate_projected_table_captions(p_build text,p_root text,p_projection jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $captions$
BEGIN
 IF EXISTS (
  WITH RECURSIVE selected AS MATERIALIZED (
   SELECT r.pointer,r.parent_pointer,r.label,r.native_json
   FROM jsonb_array_elements_text(p_projection->'items') p(pointer)
   JOIN kb.pdf_record_access r ON r.pointer=p.pointer AND r.product_id=p_build
    AND r.revision_id=p_build AND r.content_layer='body'
   WHERE r.native_json->>'self_ref'=r.pointer
  ), walk(pointer,path,visited,in_cell,cell_index) AS (
   SELECT pointer,ARRAY[]::bigint[],ARRAY[pointer],false,NULL::bigint FROM selected WHERE pointer=p_root
   UNION ALL
   SELECT child.pointer,w.path||edge.n,w.visited||child.pointer,w.in_cell OR edge.in_cell,
    CASE WHEN edge.in_cell THEN edge.n-1 ELSE w.cell_index END
   FROM walk w JOIN selected parent USING(pointer)
   CROSS JOIN LATERAL (
    SELECT c->>'$ref' AS pointer,n,false AS in_cell
    FROM jsonb_array_elements(parent.native_json->'children') WITH ORDINALITY c(c,n)
    WHERE parent.native_json->'data'->'table_cells' IS NULL
    UNION ALL
    SELECT c->'ref'->>'$ref',n,true
    FROM jsonb_array_elements(parent.native_json->'data'->'table_cells') WITH ORDINALITY c(c,n)
    WHERE c->'ref'->>'$ref' IS NOT NULL
   ) edge JOIN selected child ON child.pointer=edge.pointer AND NOT child.pointer=ANY(w.visited)
  ), associations AS (
   SELECT DISTINCT ON (caption.pointer) caption.pointer,t.pointer AS owner,w.path,
    cardinality(w.path) AS depth,refs.family,refs.n
   FROM walk w JOIN selected t USING(pointer)
   CROSS JOIN LATERAL (
    SELECT 0 AS family,n,c->>'$ref' AS pointer FROM jsonb_array_elements(t.native_json->'children') WITH ORDINALITY c(c,n)
    UNION ALL
    SELECT 1,n,c->>'$ref' FROM jsonb_array_elements(t.native_json->'captions') WITH ORDINALITY c(c,n)
   ) refs JOIN selected caption ON caption.pointer=refs.pointer
   WHERE t.label='table' AND t.native_json->'data'->'table_cells' IS NOT NULL
    AND caption.label='caption' AND jsonb_typeof(caption.native_json->'text')='string'
    AND caption.native_json->>'text'<>''
    AND caption.parent_pointer=t.pointer
    AND NOT EXISTS(SELECT FROM walk reached WHERE reached.pointer=caption.pointer)
   ORDER BY caption.pointer,w.path,refs.family,refs.n
  ), pieces AS MATERIALIZED (
   SELECT piece,n FROM jsonb_array_elements(p_projection->'pieces') WITH ORDINALITY p(piece,n)
   WHERE piece->>'kind'='native_text'
  ), captions AS (
   SELECT a.*,false AS ordinary,p.n AS position
   FROM associations a LEFT JOIN pieces p ON p.piece->>'item_ref'=a.pointer
    AND p.piece->>'source_field'='text' AND NOT p.piece ? 'cell_index'
   UNION ALL
   SELECT w.pointer,NULL,w.path,cardinality(w.path),NULL,NULL,true,p.n
   FROM walk w JOIN selected c USING(pointer)
   LEFT JOIN pieces p ON p.piece->>'item_ref'=w.pointer
    AND p.piece->>'source_field'='text' AND NOT p.piece ? 'cell_index'
   WHERE NOT w.in_cell AND c.label='caption' AND c.native_json->>'text'<>''
  )
  SELECT FROM captions a WHERE a.position IS NULL
   OR (SELECT count(*) FROM pieces p WHERE p.piece->>'item_ref'=a.pointer)<>1
   OR (NOT a.ordinary AND EXISTS (
    SELECT FROM pieces p WHERE p.n>a.position AND (
     (p.piece->>'item_ref'=a.owner AND p.piece->>'source_field'='cell_text')
     OR (p.piece ? 'cell_index' AND EXISTS(
      SELECT FROM walk rich WHERE rich.pointer=p.piece->>'item_ref' AND rich.in_cell
       AND rich.path[1:a.depth]=a.path
     ))
    )
   ))
   OR EXISTS (
    SELECT FROM captions prior WHERE prior.owner=a.owner
     AND (prior.family,prior.n)<(a.family,a.n) AND prior.position>=a.position
   )
   OR EXISTS (
    SELECT FROM pieces p JOIN walk w ON w.pointer=p.piece->>'item_ref' AND NOT w.in_cell
    WHERE w.path<>a.path AND NOT p.piece ? 'cell_index'
     AND ((w.path<a.path AND p.n>a.position) OR (w.path>a.path AND p.n<a.position))
   )
  UNION ALL
  SELECT FROM pieces p JOIN selected c ON c.pointer=p.piece->>'item_ref'
  WHERE c.label='caption' AND (
   (NOT p.piece ? 'cell_index' AND NOT EXISTS(SELECT FROM captions a WHERE a.pointer=c.pointer))
   OR (p.piece ? 'cell_index' AND NOT EXISTS(
    SELECT FROM walk rich WHERE rich.pointer=c.pointer AND rich.in_cell
     AND rich.cell_index=(p.piece->>'cell_index')::bigint AND p.piece->>'source_field'='text'
   ))
  )
 ) THEN
  RAISE EXCEPTION 'source view table caption projection differs from selected native occurrences' USING ERRCODE='23514';
 END IF;
END $captions$;
REVOKE ALL ON FUNCTION ops.validate_projected_table_captions(text,text,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.publish_source_view(p_run bigint,p_task bigint,p_attempt bigint,p_holder text,p_position bigint,p_payload bytea,p_recipe bytea) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $view$
DECLARE job ops.task; run ops.run; product jsonb; parsing_item jsonb; projection jsonb; piece jsonb;
 native ops.pdf_selected_product; placement ops.pdf_published_revision; section kb.pdf_record_access; previous kb.source_view; result bigint;
 recipe_policy jsonb; recipe_owner jsonb; recipe_key text;
 pos bigint:=0; stop bigint; node jsonb; spelling text; piece_pointer text; expected jsonb; coverage_universe text; local_coverage text; coverage_row record; coverage_rows jsonb;
BEGIN
 SELECT * INTO STRICT run FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=p_run FOR UPDATE;
 PERFORM sem.require_execution_operation(run.release_id,'publish_source_view');
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'source view attempt lost' USING ERRCODE='P0004'; END IF;
 product:=convert_from(p_payload,'UTF8')::jsonb;
 -- {source_view_shape_guard}
 projection:=product->'projection';
 IF product->>'recipe_digest' IS DISTINCT FROM encode(sha256(p_recipe),'hex') OR
 product->>'projection_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(projection),'UTF8')),'hex') THEN
 RAISE EXCEPTION 'source view recipe/projection identity differs' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT native FROM ops.pdf_selected_product WHERE task_id=(product->>'native_task_id')::bigint AND product_key=product->>'native_product_key' AND content_digest=product->>'native_content_digest';
 SELECT * INTO STRICT placement FROM ops.read_pdf_published_revision(native.task_id,native.product_key,native.content_digest);
 PERFORM sem.require_execution_operation(placement.release_id,'read_native_source');
 -- Cross-release reuse is explicitly pinned to an archived native schema and producer contract.
 IF NOT EXISTS(SELECT FROM kb.document d JOIN ops.source_build b ON b.artifact_digest=d.content_hash JOIN ops.task t ON t.id=b.task_id JOIN ops.run r ON r.id=t.run_id
 WHERE d.id=(product->>'document_id')::bigint AND d.project_id=run.project_id AND b.task_id=native.task_id AND r.project_id=run.project_id AND EXISTS(SELECT FROM ops.source_build own WHERE own.task_id=p_task AND own.artifact_digest=b.artifact_digest)) THEN
 RAISE EXCEPTION 'native source view outside original/project custody' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.input WHERE release_id=native.release_id AND input_kind='dependency' AND input_name='execution/schema/pdf_products' AND encode(sha256(content),'hex')=native.contract_digest)
 OR NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/implementation/pdf/docling-validation.schema.json' AND encode(sha256(content),'hex')=native.schema_digest) THEN
 RAISE EXCEPTION 'native producer/consumer schema compatibility is unavailable' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT section FROM kb.pdf_record_access WHERE product_id=placement.build_id AND revision_id=placement.build_id AND pointer=product->>'section_pointer';
 IF section.label NOT IN ('section','chapter') AND NOT (
 section.pointer='#/body' AND product->>'membership'='direct'
 AND section.parent_pointer IS NULL AND section.content_layer='body'
 AND section.native_json->>'self_ref'='#/body') THEN
 RAISE EXCEPTION 'source view requires admitted section or direct residual body scope' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements_text(projection->'items') ptr WHERE NOT EXISTS(SELECT FROM kb.pdf_record_access WHERE product_id=placement.build_id AND revision_id=placement.build_id AND pointer=ptr))
 OR EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(projection->'ancestors','[]')) ptr WHERE NOT EXISTS(SELECT FROM kb.pdf_record_access WHERE product_id=placement.build_id AND revision_id=placement.build_id AND pointer=ptr)) THEN
 RAISE EXCEPTION 'source view references an unqualified occurrence' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM jsonb_array_elements_text(projection->'items'))<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(projection->'items')) THEN
 RAISE EXCEPTION 'source view repeats an occurrence' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(pointer ORDER BY ordinal),'[]'::jsonb) INTO expected FROM kb.pdf_record_access
 WHERE product_id=placement.build_id AND revision_id=placement.build_id AND pointer IN (SELECT pointer FROM ops.read_pdf_published_section_nodes(native.task_id,native.product_key,native.content_digest,section.pointer,product->>'membership') WHERE role='selected');
 IF projection->'items' IS DISTINCT FROM expected THEN RAISE EXCEPTION 'source view membership/order is incomplete or differs' USING ERRCODE='23514'; END IF;
 SELECT convert_from(content,'UTF8')::jsonb INTO recipe_policy FROM sem.input
 WHERE release_id=run.release_id AND input_kind='dependency'
 AND input_name='execution/implementation/pdf/section-text-recipe.json';
 IF recipe_policy IS NOT NULL THEN
  IF recipe_policy IS DISTINCT FROM '{"content_layers":["body"],"recipe":"native-section-text-v8"}'::jsonb
   OR job.unit_type<>'document' OR job.unit_id IS DISTINCT FROM (product->>'document_id')::bigint THEN
   RAISE EXCEPTION 'source view requires its selected PDF projection producer and recipe' USING ERRCODE='23514'; END IF;
  recipe_owner:=jsonb_build_object('task_id',native.task_id,'product_key',native.product_key,'content_digest',native.content_digest);
  IF p_recipe IS DISTINCT FROM convert_to(data.canonical_json(recipe_policy||jsonb_build_object(
   'analysis_eligible',product->'analysis_eligible','organization_owner',recipe_owner)),'UTF8') THEN
   RAISE EXCEPTION 'source view recipe differs from its selected release and native owner' USING ERRCODE='23514'; END IF;
  recipe_key:='source-view:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_object(
   'consumer_release',run.release_id,'native',recipe_owner,'section',section.pointer,
   'membership',product->>'membership','analysis_eligible',product->'analysis_eligible',
   'recipe',product->>'recipe_digest')),'UTF8')),'hex');
  IF product->>'key' IS DISTINCT FROM recipe_key THEN
   RAISE EXCEPTION 'source view key differs from its selected projection recipe' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_projected_table_captions(placement.build_id,section.pointer,projection);
 END IF;
 WITH RECURSIVE ancestry AS (
 SELECT p.*,0 depth FROM kb.pdf_record_access p WHERE p.product_id=placement.build_id AND p.revision_id=placement.build_id AND p.pointer=section.parent_pointer
 UNION ALL SELECT p.*,a.depth+1 FROM kb.pdf_record_access p JOIN ancestry a ON p.pointer=a.parent_pointer WHERE p.product_id=placement.build_id AND p.revision_id=placement.build_id
 ) SELECT COALESCE(jsonb_agg(pointer ORDER BY depth DESC),'[]'::jsonb) INTO expected FROM ancestry WHERE pointer NOT IN ('#/body','#/furniture');
 IF COALESCE(projection->'ancestors','[]') IS DISTINCT FROM expected THEN RAISE EXCEPTION 'source view ancestry differs' USING ERRCODE='23514'; END IF;
 FOR piece IN SELECT value FROM jsonb_array_elements(projection->'pieces') LOOP
  stop:=(piece->>'end')::bigint;
  IF (piece->>'start')::bigint<>pos OR stop<=pos OR stop>char_length(projection->>'text') THEN
   RAISE EXCEPTION 'source view pieces do not partition text' USING ERRCODE='23514'; END IF;
  spelling:=substr(projection->>'text',(pos+1)::integer,(stop-pos)::integer);
  IF piece->>'kind'='synthetic_separator' THEN
   IF piece->>'item_ref' IS NOT NULL OR spelling<>E'\n' THEN RAISE EXCEPTION 'unqualified synthetic source text' USING ERRCODE='23514'; END IF;
  ELSIF piece->>'kind'='native_text' THEN
   piece_pointer:=piece->>'item_ref';
   IF NOT (projection->'items' ? piece_pointer) THEN RAISE EXCEPTION 'piece outside selected source occurrences' USING ERRCODE='23514'; END IF;
   SELECT native_json INTO STRICT node FROM kb.pdf_record_access WHERE product_id=placement.build_id AND revision_id=placement.build_id AND pointer=piece_pointer;
   IF piece->>'source_field'='cell_text' THEN
    node:=node->'data'->'table_cells'->((piece->>'cell_index')::integer);
   ELSIF piece->>'source_field'='chart_cell_text' THEN
    IF node->>'label'<>'picture' OR NOT piece ? 'cell_index' THEN RAISE EXCEPTION 'chart cell requires picture/cell index' USING ERRCODE='23514'; END IF;
    node:=node->'meta'->'tabular_chart'->'chart_data'->'table_cells'->((piece->>'cell_index')::integer);
   ELSIF piece->>'source_field'='chart_title' THEN
    IF node->>'label'<>'picture' OR piece ? 'cell_index' THEN RAISE EXCEPTION 'chart title requires exact picture witness' USING ERRCODE='23514'; END IF;
    node:=jsonb_build_object('text',node->'meta'->'tabular_chart'->'title');
   END IF;
   IF spelling IS DISTINCT FROM (node->>(CASE WHEN piece->>'source_field' IN ('cell_text','chart_cell_text','chart_title') THEN 'text' ELSE COALESCE(piece->>'source_field','text') END)) OR COALESCE(piece->>'source_field','text') NOT IN ('text','orig','cell_text','chart_title','chart_cell_text') THEN
    RAISE EXCEPTION 'projected source text differs from native occurrence' USING ERRCODE='23514'; END IF;
  ELSE RAISE EXCEPTION 'unadmitted source projection operation' USING ERRCODE='23514'; END IF;
  pos:=stop;
 END LOOP;
 SELECT (native.health - 'formula_outcomes') || jsonb_build_object('formula_outcomes',COALESCE(jsonb_agg(o.value ORDER BY o.n) FILTER(WHERE projection->'items' ? (o.value->>'pointer')),'[]')) INTO expected FROM jsonb_array_elements(COALESCE(native.health->'formula_outcomes','[]')) WITH ORDINALITY o(value,n);
 SELECT COALESCE(jsonb_agg(r.body->'value' ORDER BY r.ordinal,r.local_id COLLATE "C"),'[]') INTO coverage_rows
 FROM ops.read_pdf_published_section_reports(native.task_id,native.product_key,native.content_digest,
 ARRAY(SELECT jsonb_array_elements_text(projection->'items')),ARRAY[section.pointer]||ARRAY(SELECT jsonb_array_elements_text(COALESCE(projection->'ancestors','[]')))) r
 WHERE r.body->>'kind'='recognition_coverage';
 IF EXISTS(SELECT FROM kb.pdf_record_companion c WHERE c.product_id=placement.build_id AND c.revision_id=placement.build_id AND c.family='native_metadata' AND c.body->>'kind'='recognition_coverage') THEN
  expected:=expected-ARRAY['inline_scope','cell_scope','inline_membership','cell_membership','candidate_policy','cells_policy'];
  FOREACH coverage_universe IN ARRAY ARRAY['display','inline','cell'] LOOP
   SELECT * INTO coverage_row FROM jsonb_to_recordset(coverage_rows) AS c(section_pointer text,membership text,universe text,outcome text,policy text) WHERE c.universe=coverage_universe AND
    ((c.section_pointer=section.pointer AND c.membership=product->>'membership') OR (c.outcome='complete' AND c.membership='descendants' AND (c.section_pointer=section.pointer OR projection->'ancestors' ? c.section_pointer)))
    ORDER BY (c.section_pointer=section.pointer AND c.membership=product->>'membership') DESC,c.section_pointer LIMIT 1;
   IF FOUND THEN
    expected:=jsonb_set(expected,ARRAY[coverage_universe||'_coverage'],to_jsonb(coverage_row.outcome));
    IF coverage_universe<>'display' THEN
     expected:=jsonb_set(expected,ARRAY[coverage_universe||'_scope'],jsonb_build_array(section.pointer));
     expected:=jsonb_set(expected,ARRAY[coverage_universe||'_membership'],to_jsonb(product->>'membership'));
     expected:=jsonb_set(expected,ARRAY[CASE coverage_universe WHEN 'inline' THEN 'candidate_policy' ELSE 'cells_policy' END],to_jsonb(coverage_row.policy));
    END IF;
   ELSE expected:=jsonb_set(expected,ARRAY[coverage_universe||'_coverage'],'"unknown"'::jsonb); END IF;
  END LOOP;
 ELSE
 SELECT CASE WHEN count(i.pointer)=0 OR bool_and(COALESCE(o.value->>'outcome'='succeeded',false)) THEN 'complete' WHEN count(o.value)>0 THEN 'partial' ELSE 'unknown' END INTO local_coverage
 FROM kb.pdf_record_access i LEFT JOIN kb.pdf_record_access parent ON parent.product_id=i.product_id AND parent.revision_id=i.revision_id AND parent.pointer=i.parent_pointer
 LEFT JOIN jsonb_array_elements(COALESCE(native.health->'formula_outcomes','[]')) o(value) ON o.value->>'pointer'=i.pointer
 WHERE i.product_id=placement.build_id AND i.revision_id=placement.build_id AND projection->'items' ? i.pointer AND i.label='formula' AND COALESCE(parent.label,'') NOT IN ('table','inline');
 expected:=jsonb_set(expected,'{display_coverage}',to_jsonb(local_coverage));
 FOREACH coverage_universe IN ARRAY ARRAY['inline','cell'] LOOP
  IF native.health->>(coverage_universe||'_coverage') IN ('complete','partial') AND NOT COALESCE((
   ((native.health->(coverage_universe||'_scope') ? section.pointer) AND native.health->>(coverage_universe||'_membership')=product->>'membership') OR
   (native.health->>(coverage_universe||'_membership')='descendants' AND ((native.health->(coverage_universe||'_scope') ? section.pointer) OR EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(projection->'ancestors','[]')) parent WHERE native.health->(coverage_universe||'_scope') ? parent)))),false) THEN
   expected:=jsonb_set(expected,ARRAY[coverage_universe||'_coverage'],'"unknown"'::jsonb);
  END IF;
 END LOOP;
 END IF;
 IF pos<>char_length(projection->>'text') OR projection->'health' IS DISTINCT FROM expected THEN
 RAISE EXCEPTION 'source view text extent/health differs' USING ERRCODE='23514'; END IF;
 SELECT * INTO previous FROM kb.source_view WHERE key=product->>'key' AND release_id=run.release_id;
 IF recipe_policy IS NULL AND NOT EXISTS(
  SELECT FROM ops.run_source_view WHERE run_id=p_run AND source_view_id=previous.id
   AND position=p_position AND supersedes_source_view_id IS NOT DISTINCT FROM (product->>'replaces_source_view_id')::bigint) THEN
  RAISE EXCEPTION 'fresh source view publication requires a release-bound projection recipe' USING ERRCODE='23514'; END IF;
 IF previous.id IS NOT NULL THEN
  IF previous.projection IS DISTINCT FROM projection OR previous.native_build_id IS DISTINCT FROM placement.build_id OR previous.native_revision_id IS DISTINCT FROM placement.build_id OR previous.native_content_digest<>native.content_digest OR previous.recipe_digest<>product->>'recipe_digest' OR previous.analysis_eligible IS DISTINCT FROM (product->>'analysis_eligible')::boolean THEN
   RAISE EXCEPTION 'immutable source view replay differs' USING ERRCODE='23514'; END IF;
  result:=previous.id;
 ELSE
  IF run.sealed OR run.status NOT IN ('created','running') OR job.status<>'running' THEN RAISE EXCEPTION 'source view run is no longer writable' USING ERRCODE='P0004'; END IF;
  INSERT INTO kb.source_artifact(artifact_digest,content) VALUES(encode(sha256(p_recipe),'hex'),p_recipe) ON CONFLICT DO NOTHING;
  INSERT INTO kb.source_view(analysis_eligible,key,document_id,release_id,native_task_id,native_product_key,native_content_digest,native_build_id,native_revision_id,section_pointer,membership,projection_digest,recipe_digest,projection)
  VALUES((product->>'analysis_eligible')::boolean,product->>'key',(product->>'document_id')::bigint,run.release_id,native.task_id,native.product_key,native.content_digest,placement.build_id,placement.build_id,section.pointer,product->>'membership',product->>'projection_digest',product->>'recipe_digest',projection) RETURNING id INTO result;
 END IF;
 IF product->>'replaces_source_view_id' IS NOT NULL AND NOT EXISTS(SELECT FROM ops.run_source_view rs JOIN kb.source_view old ON old.id=rs.source_view_id WHERE rs.run_id=p_run AND old.id=(product->>'replaces_source_view_id')::bigint AND old.document_id=(product->>'document_id')::bigint AND old.section_pointer=section.pointer AND old.membership=product->>'membership') THEN
 RAISE EXCEPTION 'source view replacement differs from selected original/section' USING ERRCODE='23514'; END IF;
 IF run.sealed OR run.status NOT IN ('created','running') OR job.status<>'running' THEN
  IF NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=p_run AND source_view_id=result AND position=p_position AND supersedes_source_view_id IS NOT DISTINCT FROM (product->>'replaces_source_view_id')::bigint) THEN
   RAISE EXCEPTION 'terminal source view replay cannot change selection' USING ERRCODE='P0004'; END IF;
  RETURN result;
 END IF;
 INSERT INTO ops.run_source_view(run_id,source_view_id,position,supersedes_source_view_id) VALUES(p_run,result,p_position,(product->>'replaces_source_view_id')::bigint) ON CONFLICT DO NOTHING;
 RETURN result;
END $view$;
REVOKE ALL ON FUNCTION ops.publish_source_view(bigint,bigint,bigint,text,bigint,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.publish_source_view(bigint,bigint,bigint,text,bigint,bytea,bytea) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.select_reused_source_views(p_run bigint,p_task bigint) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $reuse$
DECLARE job ops.task; run ops.run; parameters jsonb; retained_product jsonb;
BEGIN
 SELECT * INTO STRICT run FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=p_run;
 PERFORM sem.require_execution_operation(run.release_id,'publish_source_view');
 IF job.status<>'reused' OR job.reused_task_id IS NULL OR NOT ops.valid_reuse(job)
 OR run.sealed OR run.status NOT IN ('created','running') THEN
 RAISE EXCEPTION 'source view reuse is not bound to successful source origin' USING ERRCODE='23514'; END IF;
 SELECT params INTO STRICT parameters FROM ops.method_config WHERE id=job.method_config_id;
 IF NULLIF(parameters->'native_product','null'::jsonb) IS NOT NULL
 AND NULLIF(parameters->'integrated_product','null'::jsonb) IS NOT NULL THEN
 RAISE EXCEPTION 'source view reuse requires one declared retained product' USING ERRCODE='23514'; END IF;
 retained_product:=COALESCE(NULLIF(parameters->'integrated_product','null'::jsonb),
                            NULLIF(parameters->'native_product','null'::jsonb));
 INSERT INTO ops.run_source_view(run_id,source_view_id,position)
 SELECT p_run,v.id,s.position FROM ops.task origin
 JOIN ops.run origin_run ON origin_run.id=origin.run_id
 JOIN ops.run_source_view s ON s.run_id=origin.run_id
 JOIN kb.source_view v ON v.id=s.source_view_id
 JOIN kb.document d ON d.id=v.document_id AND d.id=job.unit_id
 JOIN ops.source_build own ON own.task_id=origin.id AND own.artifact_digest=d.content_hash
 JOIN ops.source_build native_build ON native_build.task_id=v.native_task_id AND native_build.artifact_digest=d.content_hash
 JOIN ops.task native_task ON native_task.id=v.native_task_id
 JOIN ops.run native_run ON native_run.id=native_task.run_id
 JOIN ops.pdf_selected_product native ON native.task_id=v.native_task_id
  AND native.product_key=v.native_product_key AND native.content_digest=v.native_content_digest
 WHERE origin.id=job.reused_task_id AND job.unit_type='document'
 AND origin_run.project_id=run.project_id AND origin_run.release_id=run.release_id
 AND v.release_id=run.release_id AND d.project_id=run.project_id AND native_run.project_id=run.project_id
 -- Producers may declare a retained input and publish their own organized output.
 -- Direct retention also admits the exact declared pin, without JSON numeric casts.
 AND (v.native_task_id=origin.id
  OR retained_product=jsonb_build_object('task_id',native.task_id,'product_key',native.product_key,'content_digest',native.content_digest))
 ON CONFLICT DO NOTHING;
END $reuse$;
REVOKE ALL ON FUNCTION ops.select_reused_source_views(bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.select_reused_source_views(bigint,bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.validate_native_frame_source(p_frame jsonb) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $source$
DECLARE view kb.source_view; context jsonb; expected jsonb; sentence jsonb; piece jsonb;
BEGIN
 -- {frame_source_shape_guard}
 SELECT * INTO STRICT view FROM kb.source_view WHERE id=(p_frame->>'source_view_id')::bigint;
 IF p_frame->>'unit_ref' IS DISTINCT FROM view.key OR p_frame->>'section_pointer' IS DISTINCT FROM view.section_pointer
 OR p_frame->>'membership' IS DISTINCT FROM view.membership OR p_frame->>'text' IS DISTINCT FROM view.projection->>'text'
 OR p_frame->>'projection_digest' IS DISTINCT FROM view.projection_digest OR p_frame->>'recipe_digest' IS DISTINCT FROM view.recipe_digest
 OR p_frame->'native_product' IS DISTINCT FROM jsonb_build_object('task_id',view.native_task_id,'product_key',view.native_product_key,'content_digest',view.native_content_digest) THEN
 RAISE EXCEPTION 'native frame source differs from immutable view' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM jsonb_array_elements(p_frame->'sentences'))<>(SELECT count(DISTINCT item->>'id') FROM jsonb_array_elements(p_frame->'sentences') item) THEN
 RAISE EXCEPTION 'native frame source sentence identifiers are not unique' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(view.projection->'pieces') WITH ORDINALITY piece(value,n)
  WHERE piece.value->>'kind'='native_text' AND piece.value->>'item_ref' IS NOT NULL AND (piece.value->>'end')::bigint>(piece.value->>'start')::bigint
  AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_frame->'sentences') supplied WHERE supplied->>'id'='native_evidence:'||(piece.n-1)::text)) THEN
 RAISE EXCEPTION 'native evidence alias inventory is incomplete' USING ERRCODE='23514'; END IF;
 FOR sentence IN SELECT value FROM jsonb_array_elements(p_frame->'sentences') WHERE starts_with(value->>'id','native_evidence:') LOOP
  IF substring(sentence->>'id' FROM length('native_evidence:')+1) !~ '^(0|[1-9][0-9]*)$' THEN
   RAISE EXCEPTION 'native evidence alias has an invalid piece ordinal' USING ERRCODE='23514'; END IF;
  piece:=view.projection->'pieces'->(substring(sentence->>'id' FROM length('native_evidence:')+1)::integer);
  IF piece IS NULL OR piece->>'kind'<>'native_text' OR piece->>'item_ref' IS NULL OR (sentence->>'start')::bigint IS DISTINCT FROM (piece->>'start')::bigint OR (sentence->>'end')::bigint IS DISTINCT FROM (piece->>'end')::bigint THEN
   RAISE EXCEPTION 'native evidence alias differs from its exact retained piece' USING ERRCODE='23514'; END IF;
 END LOOP;
 context:=(p_frame->>'native_context')::jsonb;
 SELECT jsonb_build_object('pieces',view.projection->'pieces','health',view.projection->'health',
 'items',(SELECT COALESCE(jsonb_agg(i.native_json ORDER BY ptr.n),'[]') FROM jsonb_array_elements_text(view.projection->'items') WITH ORDINALITY ptr(value,n) JOIN kb.pdf_record_access i ON i.product_id=view.native_build_id AND i.revision_id=view.native_revision_id AND i.pointer=ptr.value),
 'ancestors',(SELECT COALESCE(jsonb_agg(i.native_json ORDER BY ptr.n),'[]') FROM jsonb_array_elements_text(COALESCE(view.projection->'ancestors','[]')) WITH ORDINALITY ptr(value,n) JOIN kb.pdf_record_access i ON i.product_id=view.native_build_id AND i.revision_id=view.native_revision_id AND i.pointer=ptr.value)) INTO expected
 FROM ops.pdf_selected_product p WHERE p.task_id=view.native_task_id AND p.product_key=view.native_product_key AND p.content_digest=view.native_content_digest;
 IF EXISTS(SELECT FROM ops.pdf_product p WHERE p.task_id=view.native_task_id AND p.product_key=view.native_product_key AND p.kind='integrated') THEN
  IF COALESCE((p_frame->>'version')::integer,2)<>3 THEN RAISE EXCEPTION 'integrated source frame requires version 3' USING ERRCODE='23514'; END IF;
  IF NOT context ? 'integrated_context_json' OR (context->>'integrated_context_json')::jsonb IS DISTINCT FROM ops.integrated_source_context(view.native_task_id,view.native_product_key,view.native_content_digest,ARRAY(SELECT jsonb_array_elements_text(view.projection->'items')),view.section_pointer,view.membership) THEN RAISE EXCEPTION 'integrated source companion differs from selected occurrence scope' USING ERRCODE='23514'; END IF;
  context:=context-'integrated_context_json';
 END IF;
 IF context IS DISTINCT FROM expected THEN RAISE EXCEPTION 'native packet omitted or changed supplied source context' USING ERRCODE='23514'; END IF;
 FOR sentence IN SELECT value FROM jsonb_array_elements(p_frame->'sentences') LOOP
  IF starts_with(sentence->>'id','native_context:') OR sentence->>'id'='' OR (sentence->>'start')::bigint<0
   OR (sentence->>'end')::bigint<=(sentence->>'start')::bigint OR (sentence->>'end')::bigint>char_length(view.projection->>'text') THEN
   RAISE EXCEPTION 'native frame sentence lies outside source-local text' USING ERRCODE='23514'; END IF;
  PERFORM ops.native_source_address(view.id,sentence->>'locator',(sentence->>'start')::bigint,(sentence->>'end')::bigint);
 END LOOP;
END $source$;
REVOKE ALL ON FUNCTION ops.validate_native_frame_source(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_native_source_frame(p_run bigint,p_frame jsonb) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $sources$
DECLARE primary_view kb.source_view; source jsonb; ancestor kb.source_view;
BEGIN
 -- {native_frame_shape_guard}
 PERFORM ops.validate_native_frame_source(p_frame-'context_sources');
 SELECT * INTO STRICT primary_view FROM kb.source_view WHERE id=(p_frame->>'source_view_id')::bigint;
 IF NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=p_run AND source_view_id=primary_view.id) THEN
 RAISE EXCEPTION 'native frame primary view is not selected' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM jsonb_array_elements(COALESCE(p_frame->'context_sources','[]')))<>
 (SELECT count(DISTINCT item->>'source_view_id') FROM jsonb_array_elements(COALESCE(p_frame->'context_sources','[]')) item) THEN
 RAISE EXCEPTION 'native frame repeats a context source' USING ERRCODE='23514'; END IF;
 FOR source IN SELECT value FROM jsonb_array_elements(COALESCE(p_frame->'context_sources','[]')) LOOP
  PERFORM ops.validate_native_frame_source(source);
  SELECT * INTO STRICT ancestor FROM kb.source_view WHERE id=(source->>'source_view_id')::bigint;
  IF ancestor.id=primary_view.id OR ancestor.membership<>'direct' OR ancestor.native_task_id<>primary_view.native_task_id
   OR ancestor.native_product_key<>primary_view.native_product_key OR ancestor.native_content_digest<>primary_view.native_content_digest
   OR NOT(primary_view.projection->'ancestors' ? ancestor.section_pointer)
   OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=p_run AND source_view_id=ancestor.id) THEN
   RAISE EXCEPTION 'native frame context is not a selected same-product direct ancestor' USING ERRCODE='23514'; END IF;
 END LOOP;
END $sources$;
REVOKE ALL ON FUNCTION ops.validate_native_source_frame(bigint,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.capture_native_source_frame(p_task bigint,p_hash text,p_frame jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $frame$
DECLARE job ops.task; view kb.source_view; source jsonb; sentence jsonb; source_id bigint; handle text; ordinal integer:=0; previous jsonb;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task FOR UPDATE;
 PERFORM sem.require_execution_operation(job.release_id,'capture_native_source_frame');
 PERFORM ops.validate_native_source_frame(job.run_id,p_frame);
 SELECT * INTO STRICT view FROM kb.source_view WHERE id=(p_frame->>'source_view_id')::bigint;
 IF job.unit_type<>'source_view' OR job.unit_id<>view.id OR job.packet_hash IS DISTINCT FROM p_hash OR job.unit_key IS DISTINCT FROM p_frame->>'unit_ref' THEN
 RAISE EXCEPTION 'native packet frame differs from selected task' USING ERRCODE='23514'; END IF;
 SELECT source_frame INTO previous FROM ops.native_source_frame WHERE task_id=p_task;
 IF FOUND THEN
  IF previous IS DISTINCT FROM p_frame OR NOT EXISTS(SELECT FROM ops.native_source_frame WHERE task_id=p_task AND packet_hash=p_hash) THEN
   RAISE EXCEPTION 'immutable native frame replay differs' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 INSERT INTO ops.native_source_frame(task_id,packet_hash,unit_ref,source_view_id,product_task_id,product_key,product_digest,projection_digest,recipe_digest,context_json,source_frame)
 VALUES(p_task,p_hash,view.key,view.id,view.native_task_id,view.native_product_key,view.native_content_digest,view.projection_digest,view.recipe_digest,(p_frame->>'native_context')::jsonb,p_frame);
 FOR source IN SELECT p_frame-'context_sources' UNION ALL SELECT value FROM jsonb_array_elements(COALESCE(p_frame->'context_sources','[]')) LOOP
  source_id:=(source->>'source_view_id')::bigint;
  INSERT INTO ops.native_source_frame_source(task_id,unit_ref,source_view_id,product_task_id,product_key,product_digest,projection_digest,recipe_digest,section_pointer,membership,role,context_json)
  VALUES(p_task,source->>'unit_ref',source_id,(source->'native_product'->>'task_id')::bigint,source->'native_product'->>'product_key',source->'native_product'->>'content_digest',source->>'projection_digest',source->>'recipe_digest',source->>'section_pointer',source->>'membership',CASE WHEN source_id=view.id THEN 'primary' ELSE 'ancestor_context' END,(source->>'native_context')::jsonb);
  FOR sentence IN SELECT value FROM jsonb_array_elements(source->'sentences') LOOP
   handle:=CASE WHEN source_id=view.id THEN sentence->>'id' ELSE 'native_context:'||source_id::text||':'||(sentence->>'id') END;
   INSERT INTO ops.native_source_frame_sentence(task_id,sentence_id,locator,start_offset,end_offset,source_view_id)
   VALUES(p_task,handle,sentence->>'locator',(sentence->>'start')::bigint,(sentence->>'end')::bigint,source_id);
  END LOOP;
 END LOOP;
END $frame$;
REVOKE ALL ON FUNCTION ops.capture_native_source_frame(bigint,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.capture_native_source_frame(bigint,text,jsonb) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.select_source_view(p_run bigint,p_source_run bigint,p_view bigint) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $select$
DECLARE target ops.run; origin ops.run; source_ref jsonb;
BEGIN
 SELECT * INTO STRICT target FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT origin FROM ops.run WHERE id=p_source_run;
 PERFORM sem.require_execution_operation(target.release_id,'publish_source_view');
 IF target.sealed OR target.project_id<>origin.project_id OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=p_source_run AND source_view_id=p_view) THEN
 RAISE EXCEPTION 'source request selection differs from qualified origin' USING ERRCODE='23514'; END IF;
 IF target.release_id<>origin.release_id THEN
  SELECT jsonb_build_object('project_id',origin.project_id,'run_id',origin.id,'cut_id',completed.cut_id,'release_id',origin.release_id,
   'result_revision',batch.data_revision,'source_view_id',v.id,'native_task_id',v.native_task_id,'native_product_key',v.native_product_key,
   'native_content_digest',v.native_content_digest,'projection_digest',v.projection_digest,'recipe_digest',v.recipe_digest,
   'coordinate_version',CASE WHEN product.kind='integrated' THEN 3 ELSE 2 END) INTO STRICT source_ref
  FROM ops.completed_result completed JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id
  JOIN kb.source_view v ON v.id=p_view JOIN ops.pdf_product product ON product.task_id=v.native_task_id AND product.product_key=v.native_product_key AND product.content_digest=v.native_content_digest
  WHERE completed.run_id=origin.id;
  PERFORM ops.validate_structural_source(source_ref);
 END IF;
 INSERT INTO ops.run_source_view(run_id,source_view_id,position) VALUES(p_run,p_view,0) ON CONFLICT DO NOTHING;
END $select$;
REVOKE ALL ON FUNCTION ops.select_source_view(bigint,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.select_source_view(bigint,bigint,bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.publish_pdf_region_artifact(p_task bigint,p_attempt bigint,p_holder text,p_selection jsonb,p_recipe bytea,p_content bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $artifact$
DECLARE job ops.task; run ops.run; product ops.pdf_selected_product; placement ops.pdf_published_revision; previous ops.native_region_artifact; digest text;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task FOR UPDATE;
 SELECT * INTO STRICT run FROM ops.run WHERE id=job.run_id FOR SHARE;
 PERFORM sem.require_execution_operation(run.release_id,'publish_pdf_region_artifact');
 IF run.sealed OR job.status<>'running' OR job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'region artifact attempt lost' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT product FROM ops.pdf_selected_product WHERE task_id=(p_selection->>'task_id')::bigint AND product_key=p_selection->>'product_key' AND content_digest=p_selection->>'content_digest';
 SELECT * INTO STRICT placement FROM ops.read_pdf_published_revision(product.task_id,product.product_key,product.content_digest);
 PERFORM sem.require_execution_operation(placement.release_id,'read_native_source');
 IF NOT EXISTS(SELECT FROM ops.source_build b JOIN kb.document d ON d.content_hash=b.artifact_digest WHERE b.task_id=product.task_id AND d.project_id=run.project_id AND
 ((job.unit_type='document' AND job.unit_id=d.id) OR (job.unit_type='source_view' AND EXISTS(SELECT FROM kb.source_view v JOIN ops.run_source_view rs ON rs.source_view_id=v.id WHERE rs.run_id=run.id AND v.id=job.unit_id AND v.document_id=d.id))))
 OR NOT EXISTS(SELECT FROM kb.pdf_record_region WHERE product_id=placement.build_id AND revision_id=placement.build_id AND pointer=p_selection->>'pointer' AND region_index=(p_selection->>'region_index')::bigint) THEN
 RAISE EXCEPTION 'render artifact is outside selected native original/region' USING ERRCODE='23514'; END IF;
 digest:=encode(sha256(p_content),'hex');
 SELECT * INTO previous FROM ops.native_region_artifact WHERE task_id=p_task;
 IF FOUND THEN
 IF previous.native_build_id IS DISTINCT FROM placement.build_id OR previous.native_revision_id IS DISTINCT FROM placement.build_id OR previous.native_task_id IS DISTINCT FROM product.task_id OR previous.native_product_key IS DISTINCT FROM product.product_key OR previous.native_content_digest IS DISTINCT FROM product.content_digest OR previous.pointer IS DISTINCT FROM p_selection->>'pointer' OR previous.region_index IS DISTINCT FROM (p_selection->>'region_index')::bigint OR previous.artifact_digest<>digest OR previous.recipe_digest<>encode(sha256(p_recipe),'hex') THEN RAISE EXCEPTION 'immutable region artifact replay differs' USING ERRCODE='23514'; END IF;
 RETURN digest; END IF;
 INSERT INTO kb.source_artifact SELECT encode(sha256(content),'hex'),content FROM unnest(ARRAY[p_recipe,p_content]) content ON CONFLICT DO NOTHING;
 INSERT INTO ops.native_region_artifact(task_id,native_task_id,native_product_key,native_content_digest,native_build_id,native_revision_id,pointer,region_index,recipe_digest,artifact_digest) VALUES(p_task,product.task_id,product.product_key,product.content_digest,placement.build_id,placement.build_id,p_selection->>'pointer',(p_selection->>'region_index')::bigint,encode(sha256(p_recipe),'hex'),digest);
 RETURN digest;
END $artifact$;
REVOKE ALL ON FUNCTION ops.publish_pdf_region_artifact(bigint,bigint,text,jsonb,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.publish_pdf_region_artifact(bigint,bigint,text,jsonb,bytea,bytea) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.add_source_task_dependency(p_child bigint,p_parent bigint) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $dependency$
DECLARE child ops.task; parent ops.task; view kb.source_view; ancestor kb.source_view; dependency text;
BEGIN
 SELECT * INTO STRICT child FROM ops.task WHERE id=p_child;
 SELECT * INTO STRICT parent FROM ops.task WHERE id=p_parent;
 PERFORM sem.require_execution_operation(child.release_id,'schedule');
 SELECT * INTO STRICT view FROM kb.source_view WHERE id=child.unit_id;
 SELECT * INTO STRICT ancestor FROM kb.source_view WHERE id=parent.unit_id;
 SELECT params->>'source_dependencies' INTO dependency FROM ops.method_config WHERE id=child.method_config_id;
 IF child.run_id<>parent.run_id OR child.unit_type<>'source_view' OR parent.unit_type<>'source_view'
 OR view.native_task_id<>ancestor.native_task_id OR view.native_product_key<>ancestor.native_product_key OR view.native_content_digest<>ancestor.native_content_digest THEN
 RAISE EXCEPTION 'source prerequisite is outside bound run/product' USING ERRCODE='23514'; END IF;
 IF dependency='ancestor_source_view' THEN
  IF child.method_config_id<>parent.method_config_id OR NOT(view.projection->'ancestors' ? ancestor.section_pointer) THEN
   RAISE EXCEPTION 'source prerequisite is not a declared ancestor' USING ERRCODE='23514'; END IF;
 ELSIF dependency IN ('source_view_interpretation','source_view_product') THEN
  IF child.unit_id<>parent.unit_id OR NOT EXISTS(SELECT FROM ops.method_config consumer JOIN ops.method_config producer ON producer.id=parent.method_config_id JOIN ops.method method ON method.id=producer.method_id
    WHERE consumer.id=child.method_config_id AND consumer.params->>'source_dependency_method'=method.name) THEN
   RAISE EXCEPTION 'source prerequisite is not the declared same-view producer' USING ERRCODE='23514'; END IF;
 ELSE RAISE EXCEPTION 'source method has no admitted prerequisite declaration' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.task_dependency VALUES(p_child,p_parent,dependency) ON CONFLICT DO NOTHING;
END $dependency$;
REVOKE ALL ON FUNCTION ops.add_source_task_dependency(bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.add_source_task_dependency(bigint,bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.validate_measurement_definition() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE bound_release text; task_run bigint;
BEGIN
 SELECT r.release_id,t.run_id INTO bound_release,task_run FROM ops.task t JOIN ops.run r ON r.id=t.run_id WHERE t.id=NEW.task_id;
 IF task_run IS DISTINCT FROM NEW.run_id THEN RAISE EXCEPTION 'measurement producer run differs from task' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND jsonb_typeof(NEW.detail)<>'object' THEN
 RAISE EXCEPTION 'measurement detail requires source object' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NEW.value IS NOT NULL THEN
 IF NEW.value::text IN ('NaN','Infinity','-Infinity') THEN RAISE EXCEPTION 'measurement requires finite source value' USING ERRCODE='23514'; END IF;
 PERFORM NEW.value::double precision;
 END IF;
 IF bound_release IS NOT NULL AND NEW.scope_type='run' AND NEW.scope_id IS NOT NULL AND NOT EXISTS (SELECT FROM ops.run target JOIN ops.run producer ON producer.id=NEW.run_id WHERE target.id=NEW.scope_id AND target.release_id=bound_release AND target.project_id=producer.project_id) THEN
 RAISE EXCEPTION 'measurement run subject is outside bound project/release' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NEW.scope_type='source_view' AND NOT EXISTS(SELECT FROM kb.source_view v JOIN ops.run_source_view r ON r.source_view_id=v.id WHERE r.run_id=NEW.run_id AND (NEW.scope_id IS NULL OR v.id=NEW.scope_id) AND (NEW.scope_key IS NULL OR v.key=NEW.scope_key)) THEN RAISE EXCEPTION 'source-view metric outside selected run' USING ERRCODE='23514'; END IF;
 IF NEW.scope_type='segment' THEN RAISE EXCEPTION 'retired source measurement addressing requires current SourceView custody' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NOT EXISTS (SELECT FROM sem.metric_definition d WHERE d.release_id=bound_release AND d.metric_id=NEW.metric AND d.subject_kind=NEW.scope_type) THEN
 RAISE EXCEPTION 'unresolved metric or incompatible measurement subject' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;
