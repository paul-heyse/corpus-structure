-- One release-bound relational context selection shared by Python and frame guards.
CREATE OR REPLACE FUNCTION ops.pdf_record_context_rows(p_task bigint,p_key text,p_digest text,p_pointers text[],p_section text)
RETURNS TABLE(family text,local_id text,ordinal bigint,body jsonb)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 WITH published AS MATERIALIZED (
  SELECT * FROM ops.read_pdf_published_revision(p_task,p_key,p_digest)
 ), selected AS MATERIALIZED (
  SELECT c.* FROM kb.pdf_record_companion c JOIN published p ON c.product_id=p.build_id AND c.revision_id=p.build_id
  WHERE c.family='occurrence' AND c.body->>'pointer'=ANY(p_pointers)
 ), related AS MATERIALIZED (
  SELECT DISTINCT e.relation_id FROM kb.pdf_record_endpoint e JOIN published p ON e.product_id=p.build_id AND e.revision_id=p.build_id
  JOIN selected c ON c.local_id=e.occurrence_id
  WHERE (e.target_task_id=p_task AND e.target_product_key=p_key AND e.target_content_digest=p_digest)
   OR (e.target_task_id=0 AND e.target_product_key='@self' AND e.target_content_digest='@self')
 ), endpoints AS MATERIALIZED (
  SELECT e.* FROM kb.pdf_record_endpoint e JOIN published p ON e.product_id=p.build_id AND e.revision_id=p.build_id
  JOIN related r USING(relation_id)
 ), covered AS MATERIALIZED (
  SELECT c.* FROM kb.pdf_record_companion c JOIN published p ON c.product_id=p.build_id AND c.revision_id=p.build_id
  WHERE c.family='coverage' AND (c.body->>'scope' IN ('whole_document',p_section||':direct',p_section||':descendants')
   OR c.body->>'scope' IN (SELECT 'page:'||(o.body->>'page_no') FROM selected o UNION ALL
      SELECT 'pages:'||(o.body->>'page_no')||'-'||(o.body->>'page_no') FROM selected o))
 ), inputs AS MATERIALIZED (
  SELECT c.* FROM kb.pdf_record_companion c JOIN published p ON c.product_id=p.build_id AND c.revision_id=p.build_id
  WHERE c.family='input' AND (EXISTS(SELECT FROM endpoints e WHERE e.role<>'output' AND
   (e.target_task_id,e.target_product_key,e.target_content_digest)=
   ((c.body->>'task_id')::bigint,c.body->>'product_key',c.body->>'content_digest')) OR
   c.local_id IN (SELECT support->>'input_index' FROM covered x
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(x.body->'supports','[]')) support))
 ), chosen AS (
  SELECT * FROM selected UNION ALL SELECT * FROM covered UNION ALL SELECT * FROM inputs
  UNION ALL SELECT c.* FROM kb.pdf_record_companion c JOIN published p ON c.product_id=p.build_id AND c.revision_id=p.build_id
   WHERE c.family='relation' AND c.local_id IN (SELECT relation_id FROM related)
  UNION ALL SELECT c.* FROM kb.pdf_record_companion c JOIN published p ON c.product_id=p.build_id AND c.revision_id=p.build_id
   WHERE c.family='mapping_report' AND c.body->>'input_index' IN (SELECT local_id FROM inputs)
 ) SELECT c.family,c.local_id,c.ordinal,ops.pdf_companion_body(c.product_id,c.revision_id,c.family,c.local_id,c.body) FROM chosen c
$$;

CREATE OR REPLACE FUNCTION ops.record_integrated_source_context(p_task bigint,p_key text,p_digest text,
 p_pointers text[],p_section text,p_membership text,p_row_budget bigint DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE published ops.pdf_published_revision; actual_rows bigint; result_ jsonb;
BEGIN
 IF p_pointers IS NULL OR p_section IS NULL OR p_membership IS NULL OR p_membership NOT IN ('direct','descendants')
 OR (p_row_budget IS NOT NULL AND p_row_budget<1) THEN
 RAISE EXCEPTION 'invalid published source context selector' USING ERRCODE='22023'; END IF;
 SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(p_task,p_key,p_digest);
 -- Budgeted reads count before materialization. Ordinary section contexts use
 -- one set-shaped pass, without repeated scans for each continuation page.
 IF p_row_budget IS NOT NULL THEN
 SELECT count(*)+COALESCE(sum(CASE WHEN c.family='relation' THEN jsonb_array_length(c.body->'endpoints') ELSE 0 END),0)
 INTO actual_rows FROM ops.pdf_record_context_rows(p_task,p_key,p_digest,p_pointers,p_section) c;
 IF actual_rows>p_row_budget THEN
 RAISE EXCEPTION 'PDF mandatory companion exceeds requested row budget' USING ERRCODE='23514'; END IF;
 END IF;
 WITH chosen AS MATERIALIZED (
  SELECT * FROM ops.pdf_record_context_rows(p_task,p_key,p_digest,p_pointers,p_section)
 ), wrapped AS (
  SELECT c.family,c.ordinal,c.local_id,jsonb_build_object('task_id',p_task,'product_key',p_key)||
  CASE c.family
   WHEN 'input' THEN jsonb_build_object('input_index',c.local_id::bigint,'role',c.body->'role',
    'input_task_id',(c.body->>'task_id')::bigint,'input_product_key',c.body->'product_key','input_content_digest',c.body->'content_digest')
   WHEN 'occurrence' THEN jsonb_build_object('occurrence_id',c.local_id,'pointer',c.body->'pointer','kind',c.body->'kind',
    'precision',c.body->'precision','address_space',c.body->'address_space','body',c.body)
   WHEN 'coverage' THEN jsonb_build_object('coverage_id',c.local_id,'body',c.body)
   WHEN 'mapping_report' THEN jsonb_build_object('report_index',c.local_id::bigint,'input_index',(c.body->>'input_index')::bigint,'body',c.body)
   WHEN 'relation' THEN jsonb_build_object('relation_id',c.local_id,'kind',c.body->'kind','body',c.body-'endpoints',
    'endpoints',COALESCE((SELECT jsonb_agg(jsonb_build_object(
     'task_id',p_task,'product_key',p_key,'relation_id',e.relation_id,'endpoint_index',e.ordinal,'role',e.role,
     'target_task_id',CASE WHEN e.target_task_id=0 THEN p_task ELSE e.target_task_id END,
     'target_product_key',CASE WHEN e.target_task_id=0 THEN p_key ELSE e.target_product_key END,
     'target_content_digest',CASE WHEN e.target_task_id=0 THEN p_digest ELSE e.target_content_digest END,
     'occurrence_id',e.occurrence_id) ORDER BY e.ordinal) FROM kb.pdf_record_endpoint e
     WHERE e.product_id=published.build_id AND e.revision_id=published.build_id AND e.relation_id=c.local_id),'[]'))
   ELSE '{}'::jsonb END AS body FROM chosen c
 ), grouped AS (
  SELECT family,jsonb_agg(body ORDER BY ordinal,local_id) body FROM wrapped GROUP BY family
 ) SELECT jsonb_build_object('selection',jsonb_build_object('task_id',p_task,'product_key',p_key,'content_digest',p_digest),
  'descriptor',jsonb_build_object('version',2,'kind','integrated','revision',to_jsonb(published)),
  'inputs',COALESCE((SELECT body FROM grouped WHERE family='input'),'[]'),
  'occurrences',COALESCE((SELECT body FROM grouped WHERE family='occurrence'),'[]'),
  'relations',COALESCE((SELECT body FROM grouped WHERE family='relation'),'[]'),
  'coverage',COALESCE((SELECT body FROM grouped WHERE family='coverage'),'[]'),
  'mapping_reports',COALESCE((SELECT body FROM grouped WHERE family='mapping_report'),'[]')) INTO result_;
 RETURN result_;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_record_context_rows(bigint,text,text,text[],text),
 ops.record_integrated_source_context(bigint,text,text,text[],text,text,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.record_integrated_source_context(bigint,text,text,text[],text,text,bigint)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
