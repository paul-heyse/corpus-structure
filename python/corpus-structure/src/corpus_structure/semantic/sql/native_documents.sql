-- PDF custody uses the existing run/task lease and never requires a text rendition.
CREATE OR REPLACE FUNCTION ops.publish_native_document(
 p_task bigint,p_attempt bigint,p_holder text,p_contract text,p_payload bytea,
 p_original bytea,p_schema bytea,p_recipe bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE job ops.task; run ops.run; previous ops.native_document_product;
 product jsonb; parsing_item jsonb; digest text; artifact text; parent ops.native_document_product;
BEGIN
 SELECT r.* INTO STRICT run FROM ops.run r JOIN ops.task t ON t.run_id=r.id WHERE t.id=p_task FOR SHARE OF r;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=run.id FOR UPDATE;
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN
  RAISE EXCEPTION 'stale native document attempt' USING ERRCODE='P0004'; END IF;
 product:=convert_from(p_payload,'UTF8')::jsonb; digest:=encode(sha256(p_payload),'hex');
 -- {pdf_shape_guard}
 IF (product->>'source_scope'='page_range' AND (product->>'page_start' IS NULL OR product->>'page_end' IS NULL OR (product->>'page_start')::bigint>(product->>'page_end')::bigint)) OR (product->>'source_scope'='whole_document' AND (product ? 'page_start' OR product ? 'page_end')) THEN
  RAISE EXCEPTION 'native source scope differs' USING ERRCODE='23514'; END IF;
 IF p_original IS NULL THEN
  SELECT artifact_digest INTO STRICT artifact FROM ops.source_build WHERE task_id=p_task;
  IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=artifact) THEN RAISE EXCEPTION 'retained original is unavailable' USING ERRCODE='23514'; END IF;
 ELSE artifact:=encode(sha256(p_original),'hex'); END IF;
 IF product->>'artifact_digest' IS DISTINCT FROM artifact OR product->>'schema_digest' IS DISTINCT FROM encode(sha256(p_schema),'hex') OR product->>'recipe_digest' IS DISTINCT FROM encode(sha256(p_recipe),'hex') THEN
  RAISE EXCEPTION 'native artifact/schema/recipe identity differs' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/schema/pdf_products' AND encode(sha256(content),'hex')=p_contract) THEN
  RAISE EXCEPTION 'native contract not archived by task release' USING ERRCODE='23514'; END IF;
 IF encode(sha256(p_schema),'hex') IS DISTINCT FROM '{native_schema_digest}' OR NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/implementation/pdf/docling-validation.schema.json' AND encode(sha256(content),'hex')=product->>'schema_digest') THEN
  RAISE EXCEPTION 'native validation schema not admitted by release' USING ERRCODE='23514'; END IF;
 SELECT * INTO previous FROM ops.native_document_product WHERE task_id=p_task AND product_key=product->>'product_key';
 IF FOUND THEN
  IF previous.content_digest<>digest OR previous.payload<>p_payload OR previous.contract_digest<>p_contract THEN
   RAISE EXCEPTION 'immutable native replay differs' USING ERRCODE='23514'; END IF;
  RETURN digest;
 END IF;
 PERFORM sem.require_execution_operation(run.release_id,'publish_native_document');
 IF run.sealed OR run.status NOT IN ('created','running') OR job.status<>'running' THEN
  RAISE EXCEPTION 'run/attempt no longer accepts native products' USING ERRCODE='P0004'; END IF;
 IF num_nonnulls(product->>'parent_task_id',product->>'parent_product_key',product->>'parent_digest') NOT IN (0,3) THEN
  RAISE EXCEPTION 'incomplete native parent identity' USING ERRCODE='23514'; END IF;
 IF product ? 'parent_task_id' THEN
  SELECT * INTO STRICT parent FROM ops.native_document_product WHERE task_id=(product->>'parent_task_id')::bigint AND product_key=product->>'parent_product_key' AND content_digest=product->>'parent_digest';
  IF NOT EXISTS(SELECT FROM ops.source_build b JOIN ops.task t ON t.id=b.task_id JOIN ops.run r ON r.id=t.run_id WHERE b.task_id=parent.task_id AND b.artifact_digest=artifact AND r.project_id=run.project_id) THEN
   RAISE EXCEPTION 'native parent outside original/release/project custody' USING ERRCODE='23514'; END IF;
 END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(product->'derivation_mappings','[]')) m
 LEFT JOIN kb.native_document_item origin ON origin.task_id=parent.task_id AND origin.product_key=parent.product_key AND origin.pointer=m->>'origin_pointer'
 CROSS JOIN LATERAL (SELECT CASE WHEN m->>'source_field'='cell_text' THEN origin.native_json->'data'->'table_cells'->((m->>'cell_index')::integer)->>'text' ELSE origin.native_json->>'text' END spelling) source
 CROSS JOIN LATERAL (SELECT product->'document' #> string_to_array(substr(m->>'pointer',3),'/') node) target
 WHERE product->>'parent_task_id' IS NULL OR origin.pointer IS NULL OR target.node IS NULL
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(product->'items') i WHERE i->>'pointer'=m->>'pointer')
  OR source.spelling IS NULL OR (m->>'start')::bigint>(m->>'end')::bigint OR (m->>'start')::bigint<0 OR (m->>'end')::bigint>char_length(source.spelling)
  OR (m->>'source_field'='cell_text') IS DISTINCT FROM (m->>'cell_index' IS NOT NULL)
  OR (m->>'kind'='table_cell') IS DISTINCT FROM (m->>'source_field'='cell_text')
  OR (m->>'kind' IN ('native_text_range','table_cell') AND target.node->>'orig' IS DISTINCT FROM substr(source.spelling,(m->>'start')::integer+1,(m->>'end')::integer-(m->>'start')::integer))
  OR (m->>'kind'='vector_region_anchor' AND (target.node->>'orig' IS DISTINCT FROM '' OR substr(source.spelling,(m->>'start')::integer+1,(m->>'end')::integer-(m->>'start')::integer) ~ '[^[:space:]]'))) THEN
 RAISE EXCEPTION 'native derivation endpoints/range are unqualified' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.source_artifact(artifact_digest,content) SELECT encode(sha256(content),'hex'),content FROM unnest(ARRAY[p_original,p_schema,p_recipe]) content WHERE content IS NOT NULL ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.source_build WHERE task_id=p_task AND release_id=run.release_id AND artifact_digest=artifact) THEN
  RAISE EXCEPTION 'source build immutable identity differs' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.native_document_product(task_id,product_key,content_digest,release_id,contract_digest,schema_digest,recipe_digest,parent_task_id,parent_product_key,parent_digest,native_json,health,payload)
 VALUES(p_task,product->>'product_key',digest,run.release_id,p_contract,product->>'schema_digest',product->>'recipe_digest',(product->>'parent_task_id')::bigint,product->>'parent_product_key',product->>'parent_digest',product->'document',product->'health',p_payload);
 INSERT INTO kb.native_document_item(task_id,product_key,pointer,ordinal,label,parent_pointer,section_pointer,content_layer,text,native_json)
 SELECT p_task,product->>'product_key',i.pointer,i.ordinal,i.label,i.parent_pointer,i.section_pointer,i.content_layer,i.text,product->'document' #> string_to_array(substr(i.pointer,3),'/') FROM jsonb_populate_recordset(NULL::kb.native_document_item,product->'items') i;
 INSERT INTO kb.native_document_region(task_id,product_key,pointer,region_index,page_no,page_width,page_height,"left",top,"right",bottom,origin)
 SELECT p_task,product->>'product_key',i.pointer,i.region_index,i.page_no,i.page_width,i.page_height,i."left",i.top,i."right",i.bottom,i.origin FROM jsonb_populate_recordset(NULL::kb.native_document_region,product->'regions') i;
 INSERT INTO kb.native_document_derivation(task_id,product_key,pointer,mapping_index,origin_pointer,source_field,start_offset,end_offset,cell_index,kind)
 SELECT p_task,product->>'product_key',m.value->>'pointer',m.n-1,m.value->>'origin_pointer',m.value->>'source_field',(m.value->>'start')::bigint,(m.value->>'end')::bigint,(m.value->>'cell_index')::bigint,m.value->>'kind'
 FROM jsonb_array_elements(COALESCE(product->'derivation_mappings','[]')) WITH ORDINALITY m(value,n);
 -- Compare the complete access universe, not only whichever rows the caller supplied.
 IF EXISTS(
 WITH RECURSIVE nodes AS (
  SELECT '#/'||field.key||'/'||(entry.n-1)::text pointer,entry.value node FROM jsonb_each(product->'document') field
  CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN jsonb_typeof(field.value)='array' THEN field.value ELSE '[]'::jsonb END) WITH ORDINALITY entry(value,n)
  WHERE entry.value ? 'self_ref'
  UNION ALL SELECT product->'document'->'body'->>'self_ref',product->'document'->'body'
  UNION ALL SELECT product->'document'->'furniture'->>'self_ref',product->'document'->'furniture'
 ), walk(pointer,path,trail,scope) AS (
  SELECT pointer,ARRAY[CASE pointer WHEN '#/body' THEN 0 ELSE 1 END]::bigint[],ARRAY[pointer]::text[],NULL::text FROM nodes WHERE pointer IN ('#/body','#/furniture')
  UNION ALL
  SELECT child->>'$ref',w.path||n,w.trail||(child->>'$ref'),CASE WHEN target.node->>'label' IN ('section','chapter') THEN target.pointer ELSE w.scope END
  FROM walk w JOIN nodes parent_node ON parent_node.pointer=w.pointer
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(parent_node.node->'children','[]'::jsonb)) WITH ORDINALITY entry(child,n)
  JOIN nodes target ON target.pointer=child->>'$ref'
  WHERE NOT (child->>'$ref')=ANY(w.trail)
 ), ordered AS (
  SELECT pointer,path,scope FROM walk
  UNION ALL SELECT pointer,ARRAY[2]::bigint[],NULL::text FROM nodes WHERE NOT EXISTS(SELECT FROM walk WHERE walk.pointer=nodes.pointer)
 ), expected AS (
  SELECT nodes.*,row_number() OVER(ORDER BY ordered.path,nodes.pointer)-1 ordinal,ordered.scope
  FROM nodes JOIN ordered USING(pointer)
 )
 SELECT FROM expected e FULL JOIN (SELECT * FROM kb.native_document_item WHERE task_id=p_task AND product_key=product->>'product_key') actual USING(pointer)
 WHERE e.pointer IS NULL OR actual.pointer IS NULL OR actual.ordinal IS DISTINCT FROM e.ordinal
 OR actual.content_layer IS DISTINCT FROM e.node->>'content_layer'
 OR e.node->>'self_ref' IS DISTINCT FROM e.pointer
 OR actual.label IS DISTINCT FROM e.node->>'label'
 OR actual.text IS DISTINCT FROM e.node->>'text'
 OR actual.native_json IS DISTINCT FROM e.node
 OR actual.parent_pointer IS DISTINCT FROM e.node->'parent'->>'$ref'
 OR (actual.parent_pointer IS NOT NULL AND NOT EXISTS(SELECT FROM nodes p WHERE p.pointer=actual.parent_pointer))
 OR actual.section_pointer IS DISTINCT FROM e.scope
 OR EXISTS(SELECT FROM jsonb_array_elements(COALESCE(e.node->'children','[]'::jsonb)) child LEFT JOIN nodes target ON target.pointer=child->>'$ref' WHERE target.pointer IS NULL OR target.node->'parent'->>'$ref' IS DISTINCT FROM e.pointer)
 ) THEN RAISE EXCEPTION 'native access universe/order/membership differs' USING ERRCODE='23514'; END IF;
 -- One set-shaped provenance projection avoids repeated whole-document pointer lookup.
 IF EXISTS(
 WITH nodes AS (
  SELECT entry.value node FROM jsonb_each(product->'document') field
  CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN jsonb_typeof(field.value)='array' THEN field.value ELSE '[]'::jsonb END) entry(value)
  WHERE entry.value ? 'self_ref'
 ), expected AS (
  SELECT node->>'self_ref' pointer,n-1 region_index,prov,
   product->'document'->'pages'->(prov->>'page_no')->'size' page_size
  FROM nodes CROSS JOIN LATERAL jsonb_array_elements(COALESCE(node->'prov','[]'::jsonb)) WITH ORDINALITY regions(prov,n)
 )
 SELECT FROM expected e FULL JOIN (SELECT * FROM kb.native_document_region WHERE task_id=p_task AND product_key=product->>'product_key') r USING(pointer,region_index)
 WHERE e.pointer IS NULL OR r.pointer IS NULL
 OR (e.prov->>'page_no')::bigint IS DISTINCT FROM r.page_no
 OR (e.page_size->>'width')::numeric IS DISTINCT FROM r.page_width
 OR (e.page_size->>'height')::numeric IS DISTINCT FROM r.page_height
 OR (e.prov->'bbox'->>'l')::numeric IS DISTINCT FROM r."left"
 OR (e.prov->'bbox'->>'t')::numeric IS DISTINCT FROM r.top
 OR (e.prov->'bbox'->>'r')::numeric IS DISTINCT FROM r."right"
 OR (e.prov->'bbox'->>'b')::numeric IS DISTINCT FROM r.bottom
 OR CASE e.prov->'bbox'->>'coord_origin' WHEN 'TOPLEFT' THEN 'top_left' WHEN 'BOTTOMLEFT' THEN 'bottom_left' END IS DISTINCT FROM r.origin
 ) THEN RAISE EXCEPTION 'native region projection differs' USING ERRCODE='23514'; END IF;
 RETURN digest;
END $native$;
REVOKE ALL ON FUNCTION ops.publish_native_document(bigint,bigint,text,text,bytea,bytea,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.publish_native_document(bigint,bigint,text,text,bytea,bytea,bytea,bytea) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.retain_pdf_original(p_task bigint,p_attempt bigint,p_holder text,p_original bytea,p_recipe bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $original$
DECLARE job ops.task; run ops.run; artifact text:=encode(sha256(p_original),'hex'); recipe text:=encode(sha256(p_recipe),'hex');
BEGIN
 SELECT r.* INTO STRICT run FROM ops.run r JOIN ops.task t ON t.run_id=r.id WHERE t.id=p_task FOR SHARE OF r;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=run.id FOR UPDATE;
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder OR job.status<>'running' OR run.sealed OR run.status NOT IN ('created','running') THEN
  RAISE EXCEPTION 'stale PDF original attempt' USING ERRCODE='P0004'; END IF;
 PERFORM sem.require_execution_operation(run.release_id,'retain_pdf_original');
 IF substring(p_original FROM 1 FOR 5)<>convert_to('%PDF-','UTF8') THEN
  RAISE EXCEPTION 'PDF-only source requires PDF bytes' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM kb.document d WHERE d.project_id=run.project_id AND d.content_hash=artifact AND ((job.unit_type='document' AND d.id=job.unit_id) OR (job.unit_type='source_view' AND EXISTS(SELECT FROM kb.source_view v JOIN ops.run_source_view s ON s.source_view_id=v.id WHERE v.id=job.unit_id AND s.run_id=run.id AND v.document_id=d.id)))) THEN
  RAISE EXCEPTION 'PDF original differs from task document custody' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.source_artifact(artifact_digest,content) SELECT encode(sha256(content),'hex'),content FROM unnest(ARRAY[p_original,p_recipe]) content ON CONFLICT DO NOTHING;
 INSERT INTO ops.source_build(task_id,release_id,artifact_digest,recipe_digest) VALUES(p_task,run.release_id,artifact,recipe) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.source_build WHERE task_id=p_task AND release_id=run.release_id AND artifact_digest=artifact AND recipe_digest=recipe) THEN
  RAISE EXCEPTION 'immutable source build differs' USING ERRCODE='23514'; END IF;
 RETURN artifact;
END $original$;
REVOKE ALL ON FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea) TO corpus_sem_writer;
