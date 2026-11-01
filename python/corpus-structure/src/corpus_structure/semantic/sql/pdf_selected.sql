-- Selected Docling projections share PDF identity; the full companion remains mandatory.
CREATE OR REPLACE VIEW ops.pdf_selected_product AS
 SELECT task_id,product_key,content_digest,release_id,contract_digest,schema_digest,recipe_digest,parent_task_id,parent_product_key,parent_digest,native_json,health,payload
 FROM ops.native_document_product
 UNION ALL
 SELECT p.task_id,p.product_key,p.content_digest,p.release_id,p.contract_digest,
 body.descriptor->'content_metadata'->>'schema_digest',body.descriptor->'content_metadata'->>'recipe_digest',NULL::bigint,NULL::text,NULL::text,
 b.content->'document',body.descriptor->'content_metadata'->'health',body.payload
 FROM ops.pdf_product p JOIN ops.pdf_product_body body USING(task_id,product_key)
 CROSS JOIN LATERAL (SELECT (convert_from(body.payload,'UTF8')::json->'content')::jsonb content) b
 WHERE p.kind='integrated';
ALTER VIEW ops.pdf_selected_product OWNER TO corpus_sem_publisher;
GRANT SELECT ON ops.pdf_selected_product TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION ops.integrated_source_context(p_task bigint,p_key text,p_digest text,p_pointers text[],p_section text,p_membership text) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $context$
 WITH selected AS (
  SELECT o.* FROM kb.pdf_occurrence o WHERE o.task_id=p_task AND o.product_key=p_key AND o.pointer=ANY(p_pointers)
 ), relation_ids AS (
  SELECT DISTINCT e.relation_id FROM kb.pdf_relation_endpoint e JOIN selected o ON o.occurrence_id=e.occurrence_id
  WHERE e.task_id=p_task AND e.product_key=p_key AND e.target_task_id=p_task AND e.target_product_key=p_key
 ), related AS (
  SELECT r.* FROM kb.pdf_relation r JOIN relation_ids i USING(relation_id) WHERE r.task_id=p_task AND r.product_key=p_key
 ), endpoint_rows AS (
  SELECT e.* FROM kb.pdf_relation_endpoint e JOIN relation_ids i USING(relation_id) WHERE e.task_id=p_task AND e.product_key=p_key
 ), covered AS (
  SELECT c.* FROM kb.pdf_product_coverage c WHERE c.task_id=p_task AND c.product_key=p_key AND (
   c.body->>'scope' IN ('whole_document',p_section||':direct',p_section||':descendants') OR
   c.body->>'scope' IN (SELECT 'page:'||(o.body->>'page_no') FROM selected o UNION ALL SELECT 'pages:'||(o.body->>'page_no')||'-'||(o.body->>'page_no') FROM selected o)
  )
 ), input_rows AS (
  SELECT i.* FROM ops.pdf_product_input i WHERE i.task_id=p_task AND i.product_key=p_key AND (
   EXISTS(SELECT FROM endpoint_rows e WHERE e.role<>'output' AND (e.target_task_id,e.target_product_key,e.target_content_digest)=(i.input_task_id,i.input_product_key,i.input_content_digest)) OR
   i.input_index IN (SELECT (s->>'input_index')::bigint FROM covered c CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c.body->'supports','[]')) s)
  )
 ) SELECT jsonb_build_object(
  'selection',jsonb_build_object('task_id',p.task_id,'product_key',p.product_key,'content_digest',p.content_digest),
  'descriptor',b.descriptor,
  'occurrences',COALESCE((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.occurrence_id) FROM selected o),'[]'),
  'relations',COALESCE((SELECT jsonb_agg((to_jsonb(r)-'body')||jsonb_build_object('body',r.body-'endpoints','endpoints',COALESCE((SELECT jsonb_agg(to_jsonb(e) ORDER BY e.endpoint_index) FROM endpoint_rows e WHERE e.relation_id=r.relation_id),'[]')) ORDER BY r.relation_id) FROM related r),'[]'),
  'coverage',COALESCE((SELECT jsonb_agg(to_jsonb(c) ORDER BY c.coverage_id) FROM covered c),'[]'),
  'mapping_reports',COALESCE((SELECT jsonb_agg(to_jsonb(m) ORDER BY m.report_index) FROM kb.pdf_mapping_report m WHERE m.task_id=p_task AND m.product_key=p_key AND m.input_index IN (SELECT input_index FROM input_rows)),'[]'),
  'inputs',COALESCE((SELECT jsonb_agg(to_jsonb(i) ORDER BY i.input_index) FROM input_rows i),'[]')
 ) FROM ops.pdf_product p JOIN ops.pdf_product_body b USING(task_id,product_key)
 WHERE p.task_id=p_task AND p.product_key=p_key AND p.content_digest=p_digest AND p.kind='integrated'
$context$;
REVOKE ALL ON FUNCTION ops.integrated_source_context(bigint,text,text,text[],text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.integrated_source_context(bigint,text,text,text[],text,text) TO corpus_sem_writer,corpus_sem_reader;
