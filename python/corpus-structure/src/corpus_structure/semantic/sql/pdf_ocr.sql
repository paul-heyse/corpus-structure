-- Estimated OCR words retain their own recognized-line and raster/PDF crop frame.
CREATE OR REPLACE FUNCTION ops.validate_pdf_ocr_pages(p_task bigint,p_product jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $ocr$
DECLARE page jsonb; region jsonb; line jsonb; word jsonb; candidate jsonb; coverage jsonb;
 size jsonb; number bigint; scale double precision; width bigint; height bigint;
 l double precision; t double precision; r double precision; b double precision;
 rl double precision; rt double precision; rr double precision; rb double precision;
 first_offset bigint; last_offset bigint; previous_end bigint; required_page bigint;
BEGIN
 IF (SELECT count(*) FROM jsonb_array_elements(COALESCE(p_product->'inline_candidate_pages','[]'))) <>
    (SELECT count(DISTINCT value->>'page_no') FROM jsonb_array_elements(COALESCE(p_product->'inline_candidate_pages','[]'))) THEN
  RAISE EXCEPTION 'duplicate inline candidate page' USING ERRCODE='23514'; END IF;
 FOR page IN SELECT value FROM jsonb_array_elements(COALESCE(p_product->'inline_candidate_pages','[]')) LOOP
  number:=(page->>'page_no')::bigint;size:=p_product->'document'->'pages'->(number::text)->'size';
  IF size IS NULL THEN RAISE EXCEPTION 'inline candidate page is outside native scope' USING ERRCODE='23514'; END IF;
  IF (SELECT count(*) FROM jsonb_array_elements(COALESCE(page->'ocr_regions','[]'))) <>
     (SELECT count(DISTINCT value->>'region_index') FROM jsonb_array_elements(COALESCE(page->'ocr_regions','[]'))) THEN
   RAISE EXCEPTION 'duplicate OCR region index' USING ERRCODE='23514'; END IF;
  FOR region IN SELECT value FROM jsonb_array_elements(COALESCE(page->'ocr_regions','[]')) LOOP
   l:=(region->>'left')::double precision;t:=(region->>'top')::double precision;
   r:=(region->>'right')::double precision;b:=(region->>'bottom')::double precision;
   scale:=(region->>'scale')::double precision;width:=(region->>'raster_width')::bigint;height:=(region->>'raster_height')::bigint;
   IF NOT(scale>0 AND (region->>'orientation')::integer=0 AND 0<=l AND l<r AND r<=(size->>'width')::double precision
      AND 0<=t AND t<b AND b<=(size->>'height')::double precision
      AND abs((r-l)*scale-width)<=1 AND abs((b-t)*scale-height)<=1) THEN
    RAISE EXCEPTION 'OCR raster frame differs from its unrotated PDF crop' USING ERRCODE='23514'; END IF;
   IF (SELECT count(*) FROM jsonb_array_elements(region->'lines')) <>
      (SELECT count(DISTINCT value->>'line_index') FROM jsonb_array_elements(region->'lines')) THEN
    RAISE EXCEPTION 'duplicate OCR line index' USING ERRCODE='23514'; END IF;
   FOR line IN SELECT value FROM jsonb_array_elements(region->'lines') LOOP
    IF (SELECT count(*) FROM jsonb_array_elements(line->'words')) <>
       (SELECT count(DISTINCT value->>'word_index') FROM jsonb_array_elements(line->'words')) THEN
     RAISE EXCEPTION 'duplicate OCR word index' USING ERRCODE='23514'; END IF;
    previous_end:=0;
    FOR word IN SELECT value FROM jsonb_array_elements(line->'words') LOOP
     first_offset:=(word->>'start')::bigint;last_offset:=(word->>'end')::bigint;
     IF NOT(previous_end<=first_offset AND first_offset<last_offset AND last_offset<=char_length(line->>'text'))
       OR substring(line->>'text' FROM first_offset::integer+1 FOR (last_offset-first_offset)::integer) IS DISTINCT FROM word->>'text' THEN
      RAISE EXCEPTION 'OCR word differs from recognized line range' USING ERRCODE='23514'; END IF;
     IF region->>'outcome'='complete' AND substring(line->>'text' FROM previous_end::integer+1 FOR (first_offset-previous_end)::integer) ~ '[^[:space:]]' THEN
      RAISE EXCEPTION 'complete OCR inventory omits recognized line content' USING ERRCODE='23514'; END IF;
     previous_end:=last_offset;
     rl:=(word->>'raster_left')::double precision;rt:=(word->>'raster_top')::double precision;
     rr:=(word->>'raster_right')::double precision;rb:=(word->>'raster_bottom')::double precision;
     IF NOT(0<=rl AND rl<rr AND rr<=width AND 0<=rt AND rt<rb AND rb<=height
       AND abs((word->>'left')::double precision-(l+rl/scale))<=0.000001
       AND abs((word->>'top')::double precision-(t+rt/scale))<=0.000001
       AND abs((word->>'right')::double precision-(l+rr/scale))<=0.000001
       AND abs((word->>'bottom')::double precision-(t+rb/scale))<=0.000001) THEN
      RAISE EXCEPTION 'OCR word geometry differs from raster-to-PDF transform' USING ERRCODE='23514'; END IF;
    END LOOP;
    IF region->>'outcome'='complete' AND substring(line->>'text' FROM previous_end::integer+1) ~ '[^[:space:]]' THEN
     RAISE EXCEPTION 'complete OCR inventory omits recognized line content' USING ERRCODE='23514'; END IF;
   END LOOP;
  END LOOP;
  FOR candidate IN SELECT value FROM jsonb_array_elements(COALESCE(page->'candidates','[]')) LOOP
   IF (candidate->>'page_no')::bigint<>number OR candidate->>'origin' NOT IN ('TOPLEFT','BOTTOMLEFT')
     OR candidate->>'basis' NOT IN ('native-math-font-v1','native-math-token-v1','native-vector-gap-v1','ocr-word-token-v1')
     OR NOT(0<=(candidate->>'left')::double precision AND (candidate->>'left')::double precision<=(candidate->>'right')::double precision AND (candidate->>'right')::double precision<=(size->>'width')::double precision
     AND 0<=least((candidate->>'top')::double precision,(candidate->>'bottom')::double precision)
     AND greatest((candidate->>'top')::double precision,(candidate->>'bottom')::double precision)<=(size->>'height')::double precision) THEN
    RAISE EXCEPTION 'inline candidate has invalid page/origin/basis/geometry' USING ERRCODE='23514'; END IF;
   IF candidate->>'basis'='ocr-word-token-v1' THEN
    IF NOT(candidate ?& ARRAY['ocr_region_index','ocr_line_index','ocr_word_index']) OR candidate ? 'font' OR candidate->>'origin'<>'TOPLEFT' THEN
     RAISE EXCEPTION 'OCR candidate lacks complete estimated-word address' USING ERRCODE='23514'; END IF;
    SELECT w INTO word FROM jsonb_array_elements(COALESCE(page->'ocr_regions','[]')) regions
     CROSS JOIN LATERAL jsonb_array_elements(regions->'lines') lines
     CROSS JOIN LATERAL jsonb_array_elements(lines->'words') w
     WHERE regions->>'region_index'=candidate->>'ocr_region_index' AND lines->>'line_index'=candidate->>'ocr_line_index' AND w->>'word_index'=candidate->>'ocr_word_index';
    IF NOT FOUND OR word->>'text' IS DISTINCT FROM candidate->>'text'
     OR abs((word->>'left')::double precision-(candidate->>'left')::double precision)>0.000001
     OR abs((word->>'top')::double precision-(candidate->>'top')::double precision)>0.000001
     OR abs((word->>'right')::double precision-(candidate->>'right')::double precision)>0.000001
     OR abs((word->>'bottom')::double precision-(candidate->>'bottom')::double precision)>0.000001 THEN
     RAISE EXCEPTION 'OCR candidate differs from estimated word' USING ERRCODE='23514'; END IF;
   ELSIF candidate ?| ARRAY['ocr_region_index','ocr_line_index','ocr_word_index'] THEN
    RAISE EXCEPTION 'native candidate cannot relabel OCR word provenance' USING ERRCODE='23514';
   END IF;
  END LOOP;
 END LOOP;
 FOR coverage IN SELECT value FROM jsonb_array_elements(COALESCE(p_product->'recognition_coverage','[]'))
  WHERE value->>'universe'='inline' AND value->>'policy'='native-font-token-vector-ocr-word-v3' AND value->>'outcome'='complete'
  UNION ALL SELECT jsonb_build_object('section_pointer',pointer,'membership',p_product->'health'->>'inline_membership')
   FROM jsonb_array_elements_text(COALESCE(p_product->'health'->'inline_scope','[]')) pointer
   WHERE p_product->'health'->>'candidate_policy'='native-font-token-vector-ocr-word-v3' AND p_product->'health'->>'inline_coverage'='complete' LOOP
  FOR required_page IN SELECT DISTINCT region.page_no FROM kb.native_document_region region
   JOIN kb.native_document_item item ON item.task_id=region.task_id AND item.product_key=region.product_key AND item.pointer=region.pointer
   WHERE region.task_id=p_task AND region.product_key=p_product->>'product_key'
   AND item.label IN ('text','list_item','caption','footnote')
   AND ((jsonb_array_length(COALESCE(item.native_json->'children','[]'))=0 AND item.native_json->>'text' ~ '[^[:space:]]')
    OR (item.native_json->>'orig' ~ '[^[:space:]]' AND EXISTS(SELECT FROM jsonb_array_elements(COALESCE(item.native_json->'children','[]')) child_ref
     JOIN kb.native_document_item child ON child.task_id=item.task_id AND child.product_key=item.product_key AND child.pointer=child_ref->>'$ref'
     WHERE child.label='inline')))
   AND item.pointer IN (SELECT ops.native_scope_items(p_task,p_product->>'product_key',coverage->>'section_pointer',coverage->>'membership')) LOOP
   SELECT value INTO page FROM jsonb_array_elements(COALESCE(p_product->'inline_candidate_pages','[]')) WHERE (value->>'page_no')::bigint=required_page;
   IF NOT FOUND OR page->>'has_vectors' IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'complete OCR discovery policy lacks native vector inventory' USING ERRCODE='23514'; END IF;
   IF (jsonb_array_length(COALESCE(page->'ocr_regions','[]'))>0 AND EXISTS(SELECT FROM jsonb_array_elements(page->'ocr_regions') reg WHERE reg->>'outcome'<>'complete'))
    OR (jsonb_array_length(COALESCE(page->'ocr_regions','[]'))=0 AND (page->>'has_words'<>'true' OR page->>'native_text_quality'='broken')) THEN
    RAISE EXCEPTION 'complete OCR discovery policy lacks complete word inventory' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
END $ocr$;
REVOKE ALL ON FUNCTION ops.validate_pdf_ocr_pages(bigint,jsonb) FROM PUBLIC;
