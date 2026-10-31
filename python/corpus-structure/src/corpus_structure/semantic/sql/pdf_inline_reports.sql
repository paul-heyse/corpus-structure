CREATE OR REPLACE FUNCTION ops.publish_pdf_inline_reports(p_task bigint,p_product jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $reports$
DECLARE report jsonb; page jsonb; candidate jsonb; target_pointer text; coverage jsonb;
 center_x double precision; center_y double precision; source_height double precision;
BEGIN
 IF (SELECT count(*) FROM jsonb_array_elements(COALESCE(p_product->'inline_alignment_reports','[]'))) <>
  (SELECT count(DISTINCT (value->>'page_no',value->>'candidate_index')) FROM jsonb_array_elements(COALESCE(p_product->'inline_alignment_reports','[]'))) THEN
  RAISE EXCEPTION 'duplicate inline alignment report candidate' USING ERRCODE='23514'; END IF;
 FOR report IN SELECT value FROM jsonb_array_elements(COALESCE(p_product->'inline_alignment_reports','[]')) LOOP
  IF NOT(p_product ?& ARRAY['parent_task_id','parent_product_key','parent_digest']) THEN
   RAISE EXCEPTION 'inline alignment report requires original parent product' USING ERRCODE='23514'; END IF;
  SELECT value INTO page FROM jsonb_array_elements(COALESCE(p_product->'inline_candidate_pages','[]')) WHERE value->>'page_no'=report->>'page_no';
  candidate:=page->'candidates'->((report->>'candidate_index')::integer);
  IF page IS NULL OR candidate IS NULL THEN RAISE EXCEPTION 'inline alignment report candidate is unavailable' USING ERRCODE='23514'; END IF;
  IF jsonb_array_length(report->'item_pointers')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(report->'item_pointers'))
   OR nullif(btrim(report->>'detail'),'') IS NULL
   OR (report->>'basis'='ambiguous-native-items' AND jsonb_array_length(report->'item_pointers')<2)
   OR (report->>'basis'='unmatched-native-text' AND jsonb_array_length(report->'item_pointers')<>1) THEN
   RAISE EXCEPTION 'inline alignment report basis/items/diagnostic differs' USING ERRCODE='23514'; END IF;
  center_x:=((candidate->>'left')::double precision+(candidate->>'right')::double precision)/2;
  center_y:=((candidate->>'top')::double precision+(candidate->>'bottom')::double precision)/2;
  source_height:=(p_product->'document'->'pages'->(report->>'page_no')->'size'->>'height')::double precision;
  IF candidate->>'origin'='BOTTOMLEFT' THEN center_y:=source_height-center_y; END IF;
  FOR target_pointer IN SELECT value FROM jsonb_array_elements_text(report->'item_pointers') LOOP
   IF NOT EXISTS(SELECT FROM kb.native_document_item item JOIN kb.native_document_item original
    ON original.task_id=(p_product->>'parent_task_id')::bigint AND original.product_key=p_product->>'parent_product_key' AND original.pointer=item.pointer
    WHERE item.task_id=p_task AND item.product_key=p_product->>'product_key' AND item.pointer=target_pointer
     AND item.label IN ('text','list_item','caption','footnote') AND original.label IN ('text','list_item','caption','footnote')
     AND item.content_layer='body' AND original.content_layer='body') THEN
    RAISE EXCEPTION 'inline alignment report item is not retained original body prose' USING ERRCODE='23514'; END IF;
   IF NOT EXISTS(SELECT FROM kb.native_document_region region WHERE region.task_id=p_task AND region.product_key=p_product->>'product_key'
    AND region.pointer=target_pointer AND region.page_no=(report->>'page_no')::bigint AND region.left<=center_x AND center_x<=region.right
    AND center_y BETWEEN least(CASE region.origin WHEN 'bottom_left' THEN source_height-region.top ELSE region.top END,CASE region.origin WHEN 'bottom_left' THEN source_height-region.bottom ELSE region.bottom END)
      AND greatest(CASE region.origin WHEN 'bottom_left' THEN source_height-region.top ELSE region.top END,CASE region.origin WHEN 'bottom_left' THEN source_height-region.bottom ELSE region.bottom END)) THEN
    RAISE EXCEPTION 'inline alignment report item differs from candidate page geometry' USING ERRCODE='23514'; END IF;
  END LOOP;
  INSERT INTO kb.native_document_inline_alignment_report(task_id,product_key,page_no,candidate_index,outcome,basis,detail,candidate_basis)
  VALUES(p_task,p_product->>'product_key',(report->>'page_no')::bigint,(report->>'candidate_index')::bigint,report->>'outcome',report->>'basis',report->>'detail',candidate->>'basis');
  INSERT INTO kb.native_document_inline_alignment_item(task_id,product_key,page_no,candidate_index,item_pointer)
  SELECT p_task,p_product->>'product_key',(report->>'page_no')::bigint,(report->>'candidate_index')::bigint,value FROM jsonb_array_elements_text(report->'item_pointers');
 END LOOP;
 FOR coverage IN SELECT value FROM jsonb_array_elements(COALESCE(p_product->'recognition_coverage','[]')) WHERE value->>'universe'='inline' AND value->>'outcome'='complete'
  UNION ALL SELECT jsonb_build_object('section_pointer',pointer,'membership',p_product->'health'->>'inline_membership') FROM jsonb_array_elements_text(COALESCE(p_product->'health'->'inline_scope','[]')) pointer WHERE p_product->'health'->>'inline_coverage'='complete' LOOP
  IF EXISTS(SELECT FROM kb.native_document_inline_alignment_item item WHERE item.task_id=p_task AND item.product_key=p_product->>'product_key'
   AND item.item_pointer IN (SELECT ops.native_scope_items(p_task,p_product->>'product_key',coverage->>'section_pointer',coverage->>'membership'))) THEN
   RAISE EXCEPTION 'complete inline coverage contains unresolved source correspondence' USING ERRCODE='23514'; END IF;
 END LOOP;
END $reports$;
REVOKE ALL ON FUNCTION ops.publish_pdf_inline_reports(bigint,jsonb) FROM PUBLIC;
