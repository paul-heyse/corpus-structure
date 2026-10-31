SET LOCAL ROLE corpus_sem_publisher;
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

-- PDF custody uses the existing run/task lease and never requires a text rendition.
CREATE OR REPLACE FUNCTION ops.publish_native_document(
 p_task bigint,p_attempt bigint,p_holder text,p_contract text,p_payload bytea,
 p_original bytea,p_schema bytea,p_recipe bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE job ops.task; run ops.run; previous ops.native_document_product;
 product jsonb; parsing_item jsonb; digest text; artifact text; parent ops.native_document_product; coverage jsonb;
BEGIN
 SELECT r.* INTO STRICT run FROM ops.run r JOIN ops.task t ON t.run_id=r.id WHERE t.id=p_task FOR SHARE OF r;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=run.id FOR UPDATE;
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN
  RAISE EXCEPTION 'stale native document attempt' USING ERRCODE='P0004'; END IF;
 product:=convert_from(p_payload,'UTF8')::jsonb; digest:=encode(sha256(p_payload),'hex');
 IF product ? 'document_json' THEN RAISE EXCEPTION 'internal PDF field supplied' USING ERRCODE='23514'; END IF;
parsing_item := (product - 'document') || jsonb_build_object('document_json', (product->'document')::text);
IF jsonb_typeof(parsing_item) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'parsing record must be an object: PdfNativeEnvelope' USING ERRCODE='23514'; END IF;
IF EXISTS(SELECT FROM jsonb_object_keys(parsing_item) key WHERE key<>ALL(ARRAY['recipe','source_scope','page_start','page_end','artifact_digest','product_key','schema_digest','recipe_digest','native_schema_version','document_json','health','parent_task_id','parent_product_key','parent_digest','items','regions','recognition_coverage','runtime_report','cell_reports','inline_candidate_pages','derivation_mappings'])) OR NOT (parsing_item ? 'recipe') OR (parsing_item ? 'recipe' AND (jsonb_typeof(parsing_item->'recipe') IS DISTINCT FROM 'string' OR parsing_item->>'recipe' NOT IN ('pdf-native-v1'))) OR NOT (parsing_item ? 'source_scope') OR (parsing_item ? 'source_scope' AND (jsonb_typeof(parsing_item->'source_scope') IS DISTINCT FROM 'string')) OR (parsing_item ? 'source_scope' AND parsing_item->>'source_scope' !~ '^(whole_document|page_range)$') OR (parsing_item ? 'page_start' AND (jsonb_typeof(parsing_item->'page_start') IS DISTINCT FROM 'number' OR parsing_item->>'page_start' !~ '^[0-9]+$')) OR (parsing_item ? 'page_start' AND (parsing_item->>'page_start')::numeric < 1) OR (parsing_item ? 'page_end' AND (jsonb_typeof(parsing_item->'page_end') IS DISTINCT FROM 'number' OR parsing_item->>'page_end' !~ '^[0-9]+$')) OR (parsing_item ? 'page_end' AND (parsing_item->>'page_end')::numeric < 1) OR NOT (parsing_item ? 'artifact_digest') OR (parsing_item ? 'artifact_digest' AND (jsonb_typeof(parsing_item->'artifact_digest') IS DISTINCT FROM 'string')) OR (parsing_item ? 'artifact_digest' AND parsing_item->>'artifact_digest' !~ '^[0-9a-f]{64}$') OR NOT (parsing_item ? 'product_key') OR (parsing_item ? 'product_key' AND (jsonb_typeof(parsing_item->'product_key') IS DISTINCT FROM 'string')) OR NOT (parsing_item ? 'schema_digest') OR (parsing_item ? 'schema_digest' AND (jsonb_typeof(parsing_item->'schema_digest') IS DISTINCT FROM 'string')) OR (parsing_item ? 'schema_digest' AND parsing_item->>'schema_digest' !~ '^[0-9a-f]{64}$') OR NOT (parsing_item ? 'recipe_digest') OR (parsing_item ? 'recipe_digest' AND (jsonb_typeof(parsing_item->'recipe_digest') IS DISTINCT FROM 'string')) OR (parsing_item ? 'recipe_digest' AND parsing_item->>'recipe_digest' !~ '^[0-9a-f]{64}$') OR NOT (parsing_item ? 'native_schema_version') OR (parsing_item ? 'native_schema_version' AND (jsonb_typeof(parsing_item->'native_schema_version') IS DISTINCT FROM 'string')) OR NOT (parsing_item ? 'document_json') OR (parsing_item ? 'document_json' AND (jsonb_typeof(parsing_item->'document_json') IS DISTINCT FROM 'string')) OR NOT (parsing_item ? 'health') OR (parsing_item ? 'health' AND (jsonb_typeof(parsing_item->'health') IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(parsing_item->'health') key WHERE key<>ALL(ARRAY['conversion','display_coverage','inline_coverage','cell_coverage','issues','formula_outcomes','candidate_policy','cells_policy','inline_scope','cell_scope','inline_membership','cell_membership'])) OR NOT (parsing_item->'health' ? 'conversion') OR (parsing_item->'health' ? 'conversion' AND (jsonb_typeof(parsing_item->'health'->'conversion') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'conversion' NOT IN ('failure','partial_success','success'))) OR NOT (parsing_item->'health' ? 'display_coverage') OR (parsing_item->'health' ? 'display_coverage' AND (jsonb_typeof(parsing_item->'health'->'display_coverage') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'display_coverage' NOT IN ('complete','partial','unknown','unsupported'))) OR NOT (parsing_item->'health' ? 'inline_coverage') OR (parsing_item->'health' ? 'inline_coverage' AND (jsonb_typeof(parsing_item->'health'->'inline_coverage') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'inline_coverage' NOT IN ('complete','partial','unknown','unsupported'))) OR NOT (parsing_item->'health' ? 'cell_coverage') OR (parsing_item->'health' ? 'cell_coverage' AND (jsonb_typeof(parsing_item->'health'->'cell_coverage') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'cell_coverage' NOT IN ('complete','partial','unknown','unsupported'))) OR (parsing_item->'health' ? 'issues' AND (jsonb_typeof(parsing_item->'health'->'issues') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'health'->'issues') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string'))) OR (parsing_item->'health' ? 'formula_outcomes' AND (jsonb_typeof(parsing_item->'health'->'formula_outcomes') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'health'->'formula_outcomes') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['pointer','outcome','error'])) OR NOT (nested_record ? 'pointer') OR (nested_record ? 'pointer' AND (jsonb_typeof(nested_record->'pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'pointer' AND nested_record->>'pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('failed','not_requested','succeeded','unknown'))) OR (nested_record ? 'error' AND (jsonb_typeof(nested_record->'error') IS DISTINCT FROM 'string')))))) OR (parsing_item->'health' ? 'candidate_policy' AND (jsonb_typeof(parsing_item->'health'->'candidate_policy') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'candidate_policy' NOT IN ('native-font-token-vector-ocr-word-v3','native-font-token-vector-v2','native-math-font-or-token-v1'))) OR (parsing_item->'health' ? 'cells_policy' AND (jsonb_typeof(parsing_item->'health'->'cells_policy') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'cells_policy' NOT IN ('all-nonempty-selected-cells-v1'))) OR (parsing_item->'health' ? 'inline_scope' AND (jsonb_typeof(parsing_item->'health'->'inline_scope') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'health'->'inline_scope') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string'))) OR (parsing_item->'health' ? 'inline_scope' AND EXISTS(SELECT FROM jsonb_array_elements_text(parsing_item->'health'->'inline_scope') element WHERE element !~ '^#(/[^/]+)+$')) OR (parsing_item->'health' ? 'cell_scope' AND (jsonb_typeof(parsing_item->'health'->'cell_scope') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'health'->'cell_scope') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string'))) OR (parsing_item->'health' ? 'cell_scope' AND EXISTS(SELECT FROM jsonb_array_elements_text(parsing_item->'health'->'cell_scope') element WHERE element !~ '^#(/[^/]+)+$')) OR (parsing_item->'health' ? 'inline_membership' AND (jsonb_typeof(parsing_item->'health'->'inline_membership') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'inline_membership' NOT IN ('descendants','direct'))) OR (parsing_item->'health' ? 'cell_membership' AND (jsonb_typeof(parsing_item->'health'->'cell_membership') IS DISTINCT FROM 'string' OR parsing_item->'health'->>'cell_membership' NOT IN ('descendants','direct')))))) OR (parsing_item ? 'parent_task_id' AND (jsonb_typeof(parsing_item->'parent_task_id') IS DISTINCT FROM 'number' OR parsing_item->>'parent_task_id' !~ '^[0-9]+$')) OR (parsing_item ? 'parent_task_id' AND (parsing_item->>'parent_task_id')::numeric < 1) OR (parsing_item ? 'parent_product_key' AND (jsonb_typeof(parsing_item->'parent_product_key') IS DISTINCT FROM 'string')) OR (parsing_item ? 'parent_digest' AND (jsonb_typeof(parsing_item->'parent_digest') IS DISTINCT FROM 'string')) OR (parsing_item ? 'parent_digest' AND parsing_item->>'parent_digest' !~ '^[0-9a-f]{64}$') OR NOT (parsing_item ? 'items') OR (parsing_item ? 'items' AND (jsonb_typeof(parsing_item->'items') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'items') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['pointer','ordinal','label','content_layer','parent_pointer','section_pointer','text'])) OR NOT (nested_record ? 'pointer') OR (nested_record ? 'pointer' AND (jsonb_typeof(nested_record->'pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'pointer' AND nested_record->>'pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'ordinal') OR (nested_record ? 'ordinal' AND (jsonb_typeof(nested_record->'ordinal') IS DISTINCT FROM 'number' OR nested_record->>'ordinal' !~ '^[0-9]+$')) OR (nested_record ? 'ordinal' AND (nested_record->>'ordinal')::numeric < 0) OR NOT (nested_record ? 'label') OR (nested_record ? 'label' AND (jsonb_typeof(nested_record->'label') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'content_layer') OR (nested_record ? 'content_layer' AND (jsonb_typeof(nested_record->'content_layer') IS DISTINCT FROM 'string')) OR (nested_record ? 'parent_pointer' AND (jsonb_typeof(nested_record->'parent_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'parent_pointer' AND nested_record->>'parent_pointer' !~ '^#(/[^/]+)+$') OR (nested_record ? 'section_pointer' AND (jsonb_typeof(nested_record->'section_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'section_pointer' AND nested_record->>'section_pointer' !~ '^#(/[^/]+)+$') OR (nested_record ? 'text' AND (jsonb_typeof(nested_record->'text') IS DISTINCT FROM 'string')))) OR jsonb_array_length(parsing_item->'items') < 1)) OR (parsing_item ? 'regions' AND (jsonb_typeof(parsing_item->'regions') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'regions') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['pointer','region_index','page_no','page_width','page_height','left','top','right','bottom','origin'])) OR NOT (nested_record ? 'pointer') OR (nested_record ? 'pointer' AND (jsonb_typeof(nested_record->'pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'pointer' AND nested_record->>'pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'region_index') OR (nested_record ? 'region_index' AND (jsonb_typeof(nested_record->'region_index') IS DISTINCT FROM 'number' OR nested_record->>'region_index' !~ '^[0-9]+$')) OR (nested_record ? 'region_index' AND (nested_record->>'region_index')::numeric < 0) OR NOT (nested_record ? 'page_no') OR (nested_record ? 'page_no' AND (jsonb_typeof(nested_record->'page_no') IS DISTINCT FROM 'number' OR nested_record->>'page_no' !~ '^[0-9]+$')) OR (nested_record ? 'page_no' AND (nested_record->>'page_no')::numeric < 1) OR NOT (nested_record ? 'page_width') OR (nested_record ? 'page_width' AND (jsonb_typeof(nested_record->'page_width') IS DISTINCT FROM 'number')) OR (nested_record ? 'page_width' AND (nested_record->>'page_width')::numeric < 0) OR NOT (nested_record ? 'page_height') OR (nested_record ? 'page_height' AND (jsonb_typeof(nested_record->'page_height') IS DISTINCT FROM 'number')) OR (nested_record ? 'page_height' AND (nested_record->>'page_height')::numeric < 0) OR NOT (nested_record ? 'left') OR (nested_record ? 'left' AND (jsonb_typeof(nested_record->'left') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'top') OR (nested_record ? 'top' AND (jsonb_typeof(nested_record->'top') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'right') OR (nested_record ? 'right' AND (jsonb_typeof(nested_record->'right') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'bottom') OR (nested_record ? 'bottom' AND (jsonb_typeof(nested_record->'bottom') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'origin') OR (nested_record ? 'origin' AND (jsonb_typeof(nested_record->'origin') IS DISTINCT FROM 'string' OR nested_record->>'origin' NOT IN ('bottom_left','top_left'))))))) OR (parsing_item ? 'recognition_coverage' AND (jsonb_typeof(parsing_item->'recognition_coverage') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'recognition_coverage') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (((EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['universe','policy','section_pointer','membership','outcome'])) OR NOT (nested_record ? 'universe') OR (nested_record ? 'universe' AND (jsonb_typeof(nested_record->'universe') IS DISTINCT FROM 'string')) OR nested_record->>'universe' IS DISTINCT FROM 'cell' OR NOT (nested_record ? 'policy') OR (nested_record ? 'policy' AND (jsonb_typeof(nested_record->'policy') IS DISTINCT FROM 'string')) OR nested_record->>'policy' IS DISTINCT FROM 'all-nonempty-selected-cells-v1' OR NOT (nested_record ? 'section_pointer') OR (nested_record ? 'section_pointer' AND (jsonb_typeof(nested_record->'section_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'section_pointer' AND nested_record->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'membership') OR (nested_record ? 'membership' AND (jsonb_typeof(nested_record->'membership') IS DISTINCT FROM 'string' OR nested_record->>'membership' NOT IN ('descendants','direct'))) OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('complete','partial','unknown','unsupported')))) AND (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['universe','policy','section_pointer','membership','outcome'])) OR NOT (nested_record ? 'universe') OR (nested_record ? 'universe' AND (jsonb_typeof(nested_record->'universe') IS DISTINCT FROM 'string')) OR nested_record->>'universe' IS DISTINCT FROM 'display' OR NOT (nested_record ? 'policy') OR (nested_record ? 'policy' AND (jsonb_typeof(nested_record->'policy') IS DISTINCT FROM 'string')) OR nested_record->>'policy' IS DISTINCT FROM 'detected-native-display-v1' OR NOT (nested_record ? 'section_pointer') OR (nested_record ? 'section_pointer' AND (jsonb_typeof(nested_record->'section_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'section_pointer' AND nested_record->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'membership') OR (nested_record ? 'membership' AND (jsonb_typeof(nested_record->'membership') IS DISTINCT FROM 'string' OR nested_record->>'membership' NOT IN ('descendants','direct'))) OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('complete','partial','unknown','unsupported')))) AND (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['universe','policy','section_pointer','membership','outcome'])) OR NOT (nested_record ? 'universe') OR (nested_record ? 'universe' AND (jsonb_typeof(nested_record->'universe') IS DISTINCT FROM 'string')) OR nested_record->>'universe' IS DISTINCT FROM 'inline' OR NOT (nested_record ? 'policy') OR (nested_record ? 'policy' AND (jsonb_typeof(nested_record->'policy') IS DISTINCT FROM 'string')) OR nested_record->>'policy' IS DISTINCT FROM 'native-font-token-vector-v2' OR NOT (nested_record ? 'section_pointer') OR (nested_record ? 'section_pointer' AND (jsonb_typeof(nested_record->'section_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'section_pointer' AND nested_record->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'membership') OR (nested_record ? 'membership' AND (jsonb_typeof(nested_record->'membership') IS DISTINCT FROM 'string' OR nested_record->>'membership' NOT IN ('descendants','direct'))) OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('complete','partial','unknown','unsupported')))) AND (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['universe','policy','section_pointer','membership','outcome'])) OR NOT (nested_record ? 'universe') OR (nested_record ? 'universe' AND (jsonb_typeof(nested_record->'universe') IS DISTINCT FROM 'string')) OR nested_record->>'universe' IS DISTINCT FROM 'inline' OR NOT (nested_record ? 'policy') OR (nested_record ? 'policy' AND (jsonb_typeof(nested_record->'policy') IS DISTINCT FROM 'string')) OR nested_record->>'policy' IS DISTINCT FROM 'native-font-token-vector-ocr-word-v3' OR NOT (nested_record ? 'section_pointer') OR (nested_record ? 'section_pointer' AND (jsonb_typeof(nested_record->'section_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'section_pointer' AND nested_record->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'membership') OR (nested_record ? 'membership' AND (jsonb_typeof(nested_record->'membership') IS DISTINCT FROM 'string' OR nested_record->>'membership' NOT IN ('descendants','direct'))) OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('complete','partial','unknown','unsupported'))))))))) OR (parsing_item ? 'runtime_report' AND (jsonb_typeof(parsing_item->'runtime_report') IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(parsing_item->'runtime_report') key WHERE key<>ALL(ARRAY['packages','bindings','effective_options','confidence'])) OR (parsing_item->'runtime_report' ? 'packages' AND (jsonb_typeof(parsing_item->'runtime_report'->'packages') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'runtime_report'->'packages') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['name','version'])) OR NOT (nested_record ? 'name') OR (nested_record ? 'name' AND (jsonb_typeof(nested_record->'name') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'version') OR (nested_record ? 'version' AND (jsonb_typeof(nested_record->'version') IS DISTINCT FROM 'string')))))) OR (parsing_item->'runtime_report' ? 'bindings' AND (jsonb_typeof(parsing_item->'runtime_report'->'bindings') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'runtime_report'->'bindings') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['name','value'])) OR NOT (nested_record ? 'name') OR (nested_record ? 'name' AND (jsonb_typeof(nested_record->'name') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'value') OR (nested_record ? 'value' AND (jsonb_typeof(nested_record->'value') IS DISTINCT FROM 'string')))))) OR NOT (parsing_item->'runtime_report' ? 'effective_options') OR (parsing_item->'runtime_report' ? 'effective_options' AND (jsonb_typeof(parsing_item->'runtime_report'->'effective_options') IS DISTINCT FROM 'string')) OR (parsing_item->'runtime_report' ? 'confidence' AND (jsonb_typeof(parsing_item->'runtime_report'->'confidence') IS DISTINCT FROM 'string'))))) OR (parsing_item ? 'cell_reports' AND (jsonb_typeof(parsing_item->'cell_reports') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'cell_reports') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['table_pointer','cell_index','page_no','classification','basis','outcome','formula_pointer','error'])) OR NOT (nested_record ? 'table_pointer') OR (nested_record ? 'table_pointer' AND (jsonb_typeof(nested_record->'table_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'table_pointer' AND nested_record->>'table_pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'cell_index') OR (nested_record ? 'cell_index' AND (jsonb_typeof(nested_record->'cell_index') IS DISTINCT FROM 'number' OR nested_record->>'cell_index' !~ '^[0-9]+$')) OR (nested_record ? 'cell_index' AND (nested_record->>'cell_index')::numeric < 0) OR NOT (nested_record ? 'page_no') OR (nested_record ? 'page_no' AND (jsonb_typeof(nested_record->'page_no') IS DISTINCT FROM 'number' OR nested_record->>'page_no' !~ '^[0-9]+$')) OR (nested_record ? 'page_no' AND (nested_record->>'page_no')::numeric < 1) OR NOT (nested_record ? 'classification') OR (nested_record ? 'classification' AND (jsonb_typeof(nested_record->'classification') IS DISTINCT FROM 'string' OR nested_record->>'classification' NOT IN ('math','prose','unknown'))) OR NOT (nested_record ? 'basis') OR (nested_record ? 'basis' AND (jsonb_typeof(nested_record->'basis') IS DISTINCT FROM 'string' OR nested_record->>'basis' NOT IN ('native-candidate-intersection','native-math-token','native-rich-reference','native-word-text','ocr-word-text','unresolved-native-evidence'))) OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('failed','not_requested','succeeded','unknown'))) OR (nested_record ? 'formula_pointer' AND (jsonb_typeof(nested_record->'formula_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'formula_pointer' AND nested_record->>'formula_pointer' !~ '^#(/[^/]+)+$') OR (nested_record ? 'error' AND (jsonb_typeof(nested_record->'error') IS DISTINCT FROM 'string')))))) OR (parsing_item ? 'inline_candidate_pages' AND (jsonb_typeof(parsing_item->'inline_candidate_pages') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'inline_candidate_pages') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['page_no','has_words','has_chars','has_vectors','candidates','native_text_quality','ocr_regions'])) OR NOT (nested_record ? 'page_no') OR (nested_record ? 'page_no' AND (jsonb_typeof(nested_record->'page_no') IS DISTINCT FROM 'number' OR nested_record->>'page_no' !~ '^[0-9]+$')) OR (nested_record ? 'page_no' AND (nested_record->>'page_no')::numeric < 1) OR NOT (nested_record ? 'has_words') OR (nested_record ? 'has_words' AND (jsonb_typeof(nested_record->'has_words') IS DISTINCT FROM 'boolean')) OR NOT (nested_record ? 'has_chars') OR (nested_record ? 'has_chars' AND (jsonb_typeof(nested_record->'has_chars') IS DISTINCT FROM 'boolean')) OR (nested_record ? 'has_vectors' AND (jsonb_typeof(nested_record->'has_vectors') IS DISTINCT FROM 'boolean')) OR (nested_record ? 'candidates' AND (jsonb_typeof(nested_record->'candidates') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(nested_record->'candidates') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['page_no','text','left','top','right','bottom','origin','font','basis','before','after','ocr_region_index','ocr_line_index','ocr_word_index'])) OR NOT (nested_record ? 'page_no') OR (nested_record ? 'page_no' AND (jsonb_typeof(nested_record->'page_no') IS DISTINCT FROM 'number' OR nested_record->>'page_no' !~ '^[0-9]+$')) OR (nested_record ? 'page_no' AND (nested_record->>'page_no')::numeric < 1) OR NOT (nested_record ? 'text') OR (nested_record ? 'text' AND (jsonb_typeof(nested_record->'text') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'left') OR (nested_record ? 'left' AND (jsonb_typeof(nested_record->'left') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'top') OR (nested_record ? 'top' AND (jsonb_typeof(nested_record->'top') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'right') OR (nested_record ? 'right' AND (jsonb_typeof(nested_record->'right') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'bottom') OR (nested_record ? 'bottom' AND (jsonb_typeof(nested_record->'bottom') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'origin') OR (nested_record ? 'origin' AND (jsonb_typeof(nested_record->'origin') IS DISTINCT FROM 'string')) OR (nested_record ? 'font' AND (jsonb_typeof(nested_record->'font') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'basis') OR (nested_record ? 'basis' AND (jsonb_typeof(nested_record->'basis') IS DISTINCT FROM 'string')) OR (nested_record ? 'before' AND (jsonb_typeof(nested_record->'before') IS DISTINCT FROM 'string')) OR (nested_record ? 'after' AND (jsonb_typeof(nested_record->'after') IS DISTINCT FROM 'string')) OR (nested_record ? 'ocr_region_index' AND (jsonb_typeof(nested_record->'ocr_region_index') IS DISTINCT FROM 'number' OR nested_record->>'ocr_region_index' !~ '^[0-9]+$')) OR (nested_record ? 'ocr_region_index' AND (nested_record->>'ocr_region_index')::numeric < 0) OR (nested_record ? 'ocr_line_index' AND (jsonb_typeof(nested_record->'ocr_line_index') IS DISTINCT FROM 'number' OR nested_record->>'ocr_line_index' !~ '^[0-9]+$')) OR (nested_record ? 'ocr_line_index' AND (nested_record->>'ocr_line_index')::numeric < 0) OR (nested_record ? 'ocr_word_index' AND (jsonb_typeof(nested_record->'ocr_word_index') IS DISTINCT FROM 'number' OR nested_record->>'ocr_word_index' !~ '^[0-9]+$')) OR (nested_record ? 'ocr_word_index' AND (nested_record->>'ocr_word_index')::numeric < 0))))) OR (nested_record ? 'native_text_quality' AND (jsonb_typeof(nested_record->'native_text_quality') IS DISTINCT FROM 'string' OR nested_record->>'native_text_quality' NOT IN ('broken','not_flagged','unassessed'))) OR (nested_record ? 'ocr_regions' AND (jsonb_typeof(nested_record->'ocr_regions') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(nested_record->'ocr_regions') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['region_index','engine','raster_width','raster_height','scale','orientation','outcome','lines','left','top','right','bottom'])) OR NOT (nested_record ? 'region_index') OR (nested_record ? 'region_index' AND (jsonb_typeof(nested_record->'region_index') IS DISTINCT FROM 'number' OR nested_record->>'region_index' !~ '^[0-9]+$')) OR (nested_record ? 'region_index' AND (nested_record->>'region_index')::numeric < 0) OR NOT (nested_record ? 'engine') OR (nested_record ? 'engine' AND (jsonb_typeof(nested_record->'engine') IS DISTINCT FROM 'string')) OR nested_record->>'engine' IS DISTINCT FROM 'rapidocr' OR NOT (nested_record ? 'raster_width') OR (nested_record ? 'raster_width' AND (jsonb_typeof(nested_record->'raster_width') IS DISTINCT FROM 'number' OR nested_record->>'raster_width' !~ '^[0-9]+$')) OR (nested_record ? 'raster_width' AND (nested_record->>'raster_width')::numeric < 1) OR NOT (nested_record ? 'raster_height') OR (nested_record ? 'raster_height' AND (jsonb_typeof(nested_record->'raster_height') IS DISTINCT FROM 'number' OR nested_record->>'raster_height' !~ '^[0-9]+$')) OR (nested_record ? 'raster_height' AND (nested_record->>'raster_height')::numeric < 1) OR NOT (nested_record ? 'scale') OR (nested_record ? 'scale' AND (jsonb_typeof(nested_record->'scale') IS DISTINCT FROM 'number')) OR (nested_record ? 'scale' AND (nested_record->>'scale')::numeric < 0) OR NOT (nested_record ? 'orientation') OR (nested_record ? 'orientation' AND (jsonb_typeof(nested_record->'orientation') IS DISTINCT FROM 'number' OR nested_record->>'orientation' !~ '^[0-9]+$')) OR (nested_record ? 'orientation' AND (nested_record->>'orientation')::numeric < 0) OR (nested_record ? 'orientation' AND (nested_record->>'orientation')::numeric > 0) OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('complete','partial','unknown'))) OR NOT (nested_record ? 'lines') OR (nested_record ? 'lines' AND (jsonb_typeof(nested_record->'lines') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(nested_record->'lines') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['line_index','text','words'])) OR NOT (nested_record ? 'line_index') OR (nested_record ? 'line_index' AND (jsonb_typeof(nested_record->'line_index') IS DISTINCT FROM 'number' OR nested_record->>'line_index' !~ '^[0-9]+$')) OR (nested_record ? 'line_index' AND (nested_record->>'line_index')::numeric < 0) OR NOT (nested_record ? 'text') OR (nested_record ? 'text' AND (jsonb_typeof(nested_record->'text') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'words') OR (nested_record ? 'words' AND (jsonb_typeof(nested_record->'words') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(nested_record->'words') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['word_index','text','confidence','start','end','raster_left','raster_top','raster_right','raster_bottom','left','top','right','bottom'])) OR NOT (nested_record ? 'word_index') OR (nested_record ? 'word_index' AND (jsonb_typeof(nested_record->'word_index') IS DISTINCT FROM 'number' OR nested_record->>'word_index' !~ '^[0-9]+$')) OR (nested_record ? 'word_index' AND (nested_record->>'word_index')::numeric < 0) OR NOT (nested_record ? 'text') OR (nested_record ? 'text' AND (jsonb_typeof(nested_record->'text') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'confidence') OR (nested_record ? 'confidence' AND (jsonb_typeof(nested_record->'confidence') IS DISTINCT FROM 'number')) OR (nested_record ? 'confidence' AND (nested_record->>'confidence')::numeric < 0) OR (nested_record ? 'confidence' AND (nested_record->>'confidence')::numeric > 1) OR NOT (nested_record ? 'start') OR (nested_record ? 'start' AND (jsonb_typeof(nested_record->'start') IS DISTINCT FROM 'number' OR nested_record->>'start' !~ '^[0-9]+$')) OR (nested_record ? 'start' AND (nested_record->>'start')::numeric < 0) OR NOT (nested_record ? 'end') OR (nested_record ? 'end' AND (jsonb_typeof(nested_record->'end') IS DISTINCT FROM 'number' OR nested_record->>'end' !~ '^[0-9]+$')) OR (nested_record ? 'end' AND (nested_record->>'end')::numeric < 1) OR NOT (nested_record ? 'raster_left') OR (nested_record ? 'raster_left' AND (jsonb_typeof(nested_record->'raster_left') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'raster_top') OR (nested_record ? 'raster_top' AND (jsonb_typeof(nested_record->'raster_top') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'raster_right') OR (nested_record ? 'raster_right' AND (jsonb_typeof(nested_record->'raster_right') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'raster_bottom') OR (nested_record ? 'raster_bottom' AND (jsonb_typeof(nested_record->'raster_bottom') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'left') OR (nested_record ? 'left' AND (jsonb_typeof(nested_record->'left') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'top') OR (nested_record ? 'top' AND (jsonb_typeof(nested_record->'top') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'right') OR (nested_record ? 'right' AND (jsonb_typeof(nested_record->'right') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'bottom') OR (nested_record ? 'bottom' AND (jsonb_typeof(nested_record->'bottom') IS DISTINCT FROM 'number')))) OR jsonb_array_length(nested_record->'words') < 1)))) OR jsonb_array_length(nested_record->'lines') < 1)) OR NOT (nested_record ? 'left') OR (nested_record ? 'left' AND (jsonb_typeof(nested_record->'left') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'top') OR (nested_record ? 'top' AND (jsonb_typeof(nested_record->'top') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'right') OR (nested_record ? 'right' AND (jsonb_typeof(nested_record->'right') IS DISTINCT FROM 'number')) OR NOT (nested_record ? 'bottom') OR (nested_record ? 'bottom' AND (jsonb_typeof(nested_record->'bottom') IS DISTINCT FROM 'number')))))))))) OR (parsing_item ? 'derivation_mappings' AND (jsonb_typeof(parsing_item->'derivation_mappings') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(parsing_item->'derivation_mappings') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['pointer','origin_pointer','source_field','start','end','cell_index','kind'])) OR NOT (nested_record ? 'pointer') OR (nested_record ? 'pointer' AND (jsonb_typeof(nested_record->'pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'pointer' AND nested_record->>'pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'origin_pointer') OR (nested_record ? 'origin_pointer' AND (jsonb_typeof(nested_record->'origin_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'origin_pointer' AND nested_record->>'origin_pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'source_field') OR (nested_record ? 'source_field' AND (jsonb_typeof(nested_record->'source_field') IS DISTINCT FROM 'string' OR nested_record->>'source_field' NOT IN ('cell_text','text'))) OR NOT (nested_record ? 'start') OR (nested_record ? 'start' AND (jsonb_typeof(nested_record->'start') IS DISTINCT FROM 'number' OR nested_record->>'start' !~ '^[0-9]+$')) OR (nested_record ? 'start' AND (nested_record->>'start')::numeric < 0) OR NOT (nested_record ? 'end') OR (nested_record ? 'end' AND (jsonb_typeof(nested_record->'end') IS DISTINCT FROM 'number' OR nested_record->>'end' !~ '^[0-9]+$')) OR (nested_record ? 'end' AND (nested_record->>'end')::numeric < 0) OR (nested_record ? 'cell_index' AND (jsonb_typeof(nested_record->'cell_index') IS DISTINCT FROM 'number' OR nested_record->>'cell_index' !~ '^[0-9]+$')) OR (nested_record ? 'cell_index' AND (nested_record->>'cell_index')::numeric < 0) OR NOT (nested_record ? 'kind') OR (nested_record ? 'kind' AND (jsonb_typeof(nested_record->'kind') IS DISTINCT FROM 'string' OR nested_record->>'kind' NOT IN ('native_text_range','table_cell','vector_region_anchor'))))))) THEN RAISE EXCEPTION 'parsing record shape differs: PdfNativeEnvelope' USING ERRCODE='23514'; END IF;

 IF (product->>'source_scope'='page_range' AND (product->>'page_start' IS NULL OR product->>'page_end' IS NULL OR (product->>'page_start')::bigint>(product->>'page_end')::bigint)) OR (product->>'source_scope'='whole_document' AND (product ? 'page_start' OR product ? 'page_end')) THEN
  RAISE EXCEPTION 'native source scope differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM unnest(ARRAY['inline','cell']) universe WHERE product->'health'->>(universe||'_coverage')='complete' AND
  (jsonb_array_length(COALESCE(product->'health'->(universe||'_scope'),'[]'))=0 OR product->'health'->>(universe||'_membership') IS NULL OR
   product->'health'->>(CASE universe WHEN 'inline' THEN 'candidate_policy' ELSE 'cells_policy' END) IS NULL)) THEN
  RAISE EXCEPTION 'complete recognition coverage requires a qualified scope/membership/policy' USING ERRCODE='23514'; END IF;
 IF product ? 'runtime_report' AND (jsonb_typeof((product->'runtime_report'->>'effective_options')::jsonb) IS DISTINCT FROM 'object'
  OR (product->'runtime_report' ? 'confidence' AND jsonb_typeof((product->'runtime_report'->>'confidence')::jsonb) IS DISTINCT FROM 'object')
  OR (SELECT count(*) FROM jsonb_array_elements(COALESCE(product->'runtime_report'->'packages','[]')))<>(SELECT count(DISTINCT value->>'name') FROM jsonb_array_elements(COALESCE(product->'runtime_report'->'packages','[]')))
  OR (SELECT count(*) FROM jsonb_array_elements(COALESCE(product->'runtime_report'->'bindings','[]')))<>(SELECT count(DISTINCT value->>'name') FROM jsonb_array_elements(COALESCE(product->'runtime_report'->'bindings','[]')))) THEN
  RAISE EXCEPTION 'native runtime report has invalid options or duplicate bindings' USING ERRCODE='23514'; END IF;
 IF p_original IS NULL THEN
  SELECT artifact_digest INTO STRICT artifact FROM ops.source_build WHERE task_id=p_task;
  IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=artifact) THEN RAISE EXCEPTION 'retained original is unavailable' USING ERRCODE='23514'; END IF;
 ELSE artifact:=encode(sha256(p_original),'hex'); END IF;
 IF product->>'artifact_digest' IS DISTINCT FROM artifact OR product->>'schema_digest' IS DISTINCT FROM encode(sha256(p_schema),'hex') OR product->>'recipe_digest' IS DISTINCT FROM encode(sha256(p_recipe),'hex') THEN
  RAISE EXCEPTION 'native artifact/schema/recipe identity differs' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/schema/pdf_products' AND encode(sha256(content),'hex')=p_contract) THEN
  RAISE EXCEPTION 'native contract not archived by task release' USING ERRCODE='23514'; END IF;
 IF encode(sha256(p_schema),'hex') IS DISTINCT FROM '3123788cfea7ddd282a4ec8fdeafee98d106ec2863d6722bbde4fc2f3f2e1bc1' OR NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/implementation/pdf/docling-validation.schema.json' AND encode(sha256(content),'hex')=product->>'schema_digest') THEN
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
 PERFORM ops.validate_pdf_ocr_pages(p_task,product);
 INSERT INTO kb.native_document_derivation(task_id,product_key,pointer,mapping_index,origin_pointer,source_field,start_offset,end_offset,cell_index,kind)
 SELECT p_task,product->>'product_key',m.value->>'pointer',m.n-1,m.value->>'origin_pointer',m.value->>'source_field',(m.value->>'start')::bigint,(m.value->>'end')::bigint,(m.value->>'cell_index')::bigint,m.value->>'kind'
 FROM jsonb_array_elements(COALESCE(product->'derivation_mappings','[]')) WITH ORDINALITY m(value,n);
 IF jsonb_array_length(COALESCE(product->'recognition_coverage','[]'))>0 AND (product->'health'->>'inline_coverage'<>'unknown' OR product->'health'->>'cell_coverage'<>'unknown') THEN
  RAISE EXCEPTION 'scoped recognition rows cannot imply global inline/cell coverage' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.native_document_coverage(task_id,product_key,section_pointer,membership,universe,outcome,policy)
 SELECT p_task,product->>'product_key',r.section_pointer,r.membership,r.universe,r.outcome,r.policy
 FROM jsonb_populate_recordset(NULL::kb.native_document_coverage,COALESCE(product->'recognition_coverage','[]')) r;
 FOR coverage IN SELECT value FROM jsonb_array_elements(COALESCE(product->'recognition_coverage','[]')) LOOP
  IF NOT EXISTS(SELECT FROM kb.native_document_item i WHERE i.task_id=p_task AND i.product_key=product->>'product_key' AND i.pointer=coverage->>'section_pointer' AND i.label IN ('section','chapter')) THEN
   RAISE EXCEPTION 'recognition coverage row is not a native organizational scope' USING ERRCODE='23514'; END IF;
  IF coverage->>'outcome'='complete' AND coverage->>'universe' IN ('display','inline') AND EXISTS(
   SELECT FROM kb.native_document_item i JOIN kb.native_document_item owner ON owner.task_id=i.task_id AND owner.product_key=i.product_key AND owner.pointer=i.parent_pointer
   WHERE i.task_id=p_task AND i.product_key=product->>'product_key' AND i.label='formula'
    AND i.pointer IN (SELECT ops.native_scope_items(p_task,product->>'product_key',coverage->>'section_pointer',coverage->>'membership'))
    AND ((coverage->>'universe'='display' AND owner.label NOT IN ('table','inline')) OR (coverage->>'universe'='inline' AND owner.label='inline'))
    AND NOT EXISTS(SELECT FROM jsonb_array_elements(product->'health'->'formula_outcomes') outcome WHERE outcome->>'pointer'=i.pointer AND outcome->>'outcome'='succeeded')) THEN
   RAISE EXCEPTION 'complete scoped formula coverage lacks attributable recognition' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(product->'cell_reports','[]')) report
 LEFT JOIN kb.native_document_item item ON item.task_id=p_task AND item.product_key=product->>'product_key' AND item.pointer=report->>'table_pointer'
 CROSS JOIN LATERAL (SELECT item.native_json->'data'->'table_cells'->((report->>'cell_index')::integer) value) cell
 WHERE item.pointer IS NULL OR item.label<>'table' OR cell.value IS NULL OR NOT EXISTS(SELECT FROM kb.native_document_region region WHERE region.task_id=p_task AND region.product_key=product->>'product_key' AND region.pointer=item.pointer AND region.page_no=(report->>'page_no')::bigint)
 OR (report->>'classification'='prose' AND (report->>'outcome'<>'not_requested' OR report->>'formula_pointer' IS NOT NULL))
 OR (report->>'classification'='math' AND report->>'outcome'='succeeded' AND (cell.value->'ref'->>'$ref' IS DISTINCT FROM report->>'formula_pointer' OR NOT EXISTS(SELECT FROM kb.native_document_item formula WHERE formula.task_id=p_task AND formula.product_key=product->>'product_key' AND formula.pointer=report->>'formula_pointer' AND formula.label='formula') OR NOT EXISTS(SELECT FROM jsonb_array_elements(product->'health'->'formula_outcomes') outcome WHERE outcome->>'pointer'=report->>'formula_pointer' AND outcome->>'outcome'='succeeded')))) THEN
 RAISE EXCEPTION 'native cell report is outside table/page/recognition custody' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.native_document_cell_report(task_id,product_key,table_pointer,cell_index,page_no,classification,basis,outcome,formula_pointer,error)
 SELECT p_task,product->>'product_key',r.table_pointer,r.cell_index,r.page_no,r.classification,r.basis,r.outcome,r.formula_pointer,r.error
 FROM jsonb_populate_recordset(NULL::kb.native_document_cell_report,COALESCE(product->'cell_reports','[]')) r;
 IF product ? 'runtime_report' THEN INSERT INTO kb.native_document_runtime VALUES(p_task,product->>'product_key',product->'runtime_report'); END IF;
 FOR coverage IN SELECT value FROM jsonb_array_elements(COALESCE(product->'recognition_coverage','[]')) WHERE value->>'universe'='cell' AND value->>'outcome'='complete' LOOP
  IF EXISTS(SELECT FROM kb.native_document_cell_report r WHERE r.task_id=p_task AND r.product_key=product->>'product_key'
   AND r.table_pointer IN (SELECT ops.native_scope_items(p_task,product->>'product_key',coverage->>'section_pointer',coverage->>'membership'))
   AND (r.classification='unknown' OR (r.classification='math' AND r.outcome<>'succeeded'))) THEN
   RAISE EXCEPTION 'complete scoped cell coverage contains unresolved recognition/classification' USING ERRCODE='23514'; END IF;
  IF EXISTS(WITH expected AS (
   SELECT item.pointer table_pointer,c.n-1 cell_index FROM kb.native_document_item item
   LEFT JOIN kb.native_document_item source ON source.task_id=parent.task_id AND source.product_key=parent.product_key AND source.pointer=item.pointer
   CROSS JOIN LATERAL jsonb_array_elements(COALESCE(source.native_json->'data'->'table_cells',item.native_json->'data'->'table_cells','[]')) WITH ORDINALITY c(value,n)
   WHERE item.task_id=p_task AND item.product_key=product->>'product_key' AND item.label='table'
    AND item.pointer IN (SELECT ops.native_scope_items(p_task,product->>'product_key',coverage->>'section_pointer',coverage->>'membership'))
    AND (length(trim(COALESCE(c.value->>'text','')))>0 OR c.value->'ref'->>'$ref' IS NOT NULL)
  ) SELECT FROM expected LEFT JOIN kb.native_document_cell_report actual ON actual.task_id=p_task AND actual.product_key=product->>'product_key' AND actual.table_pointer=expected.table_pointer AND actual.cell_index=expected.cell_index WHERE actual.table_pointer IS NULL) THEN
   RAISE EXCEPTION 'complete scoped cell coverage lacks its exact nonempty cell inventory' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM kb.native_document_cell_report report WHERE report.task_id=p_task AND report.product_key=product->>'product_key' AND NOT EXISTS(
  SELECT FROM kb.native_document_coverage c WHERE c.task_id=p_task AND c.product_key=product->>'product_key' AND c.universe='cell' AND report.table_pointer IN (SELECT ops.native_scope_items(p_task,product->>'product_key',c.section_pointer,c.membership)))) THEN
  RAISE EXCEPTION 'native cell report is outside declared recognition scope' USING ERRCODE='23514'; END IF;
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

-- One native containment projection serves membership validation and scoped recognition.
CREATE OR REPLACE FUNCTION ops.native_scope_items(p_task bigint,p_key text,p_section text,p_membership text)
RETURNS SETOF text LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $scope$
 WITH RECURSIVE subtree AS (
  SELECT pointer FROM kb.native_document_item WHERE task_id=p_task AND product_key=p_key AND pointer=p_section
  UNION ALL SELECT child.pointer FROM kb.native_document_item child JOIN subtree parent ON child.parent_pointer=parent.pointer
   WHERE child.task_id=p_task AND child.product_key=p_key AND p_membership='descendants'
 ) SELECT pointer FROM kb.native_document_item WHERE task_id=p_task AND product_key=p_key AND content_layer='body'
  AND ((p_membership='direct' AND section_pointer=p_section) OR (p_membership='descendants' AND pointer IN (SELECT pointer FROM subtree)))
$scope$;
REVOKE ALL ON FUNCTION ops.native_scope_items(bigint,text,text,text) FROM PUBLIC;

-- Immutable section views are instances, never fabricated document/rendition rows.
CREATE OR REPLACE FUNCTION ops.publish_source_view(p_run bigint,p_task bigint,p_attempt bigint,p_holder text,p_position bigint,p_payload bytea,p_recipe bytea) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $view$
DECLARE job ops.task; run ops.run; product jsonb; parsing_item jsonb; projection jsonb; piece jsonb;
 native ops.native_document_product; section kb.native_document_item; previous kb.source_view; result bigint;
 pos bigint:=0; stop bigint; node jsonb; spelling text; piece_pointer text; expected jsonb; coverage_universe text; local_coverage text; coverage_row kb.native_document_coverage;
BEGIN
 SELECT * INTO STRICT run FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=p_run FOR UPDATE;
 PERFORM sem.require_execution_operation(run.release_id,'publish_source_view');
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'source view attempt lost' USING ERRCODE='P0004'; END IF;
 product:=convert_from(p_payload,'UTF8')::jsonb;
 IF jsonb_typeof(product) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'parsing record must be an object: PdfSourceViewPublication' USING ERRCODE='23514'; END IF;
IF EXISTS(SELECT FROM jsonb_object_keys(product) key WHERE key<>ALL(ARRAY['key','document_id','native_task_id','native_product_key','native_content_digest','section_pointer','membership','projection_digest','recipe_digest','projection','replaces_source_view_id','analysis_eligible'])) OR NOT (product ? 'key') OR (product ? 'key' AND (jsonb_typeof(product->'key') IS DISTINCT FROM 'string')) OR NOT (product ? 'document_id') OR (product ? 'document_id' AND (jsonb_typeof(product->'document_id') IS DISTINCT FROM 'number' OR product->>'document_id' !~ '^[0-9]+$')) OR (product ? 'document_id' AND (product->>'document_id')::numeric < 1) OR NOT (product ? 'native_task_id') OR (product ? 'native_task_id' AND (jsonb_typeof(product->'native_task_id') IS DISTINCT FROM 'number' OR product->>'native_task_id' !~ '^[0-9]+$')) OR (product ? 'native_task_id' AND (product->>'native_task_id')::numeric < 1) OR NOT (product ? 'native_product_key') OR (product ? 'native_product_key' AND (jsonb_typeof(product->'native_product_key') IS DISTINCT FROM 'string')) OR NOT (product ? 'native_content_digest') OR (product ? 'native_content_digest' AND (jsonb_typeof(product->'native_content_digest') IS DISTINCT FROM 'string')) OR (product ? 'native_content_digest' AND product->>'native_content_digest' !~ '^[0-9a-f]{64}$') OR NOT (product ? 'section_pointer') OR (product ? 'section_pointer' AND (jsonb_typeof(product->'section_pointer') IS DISTINCT FROM 'string')) OR (product ? 'section_pointer' AND product->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (product ? 'membership') OR (product ? 'membership' AND (jsonb_typeof(product->'membership') IS DISTINCT FROM 'string' OR product->>'membership' NOT IN ('descendants','direct'))) OR NOT (product ? 'projection_digest') OR (product ? 'projection_digest' AND (jsonb_typeof(product->'projection_digest') IS DISTINCT FROM 'string')) OR (product ? 'projection_digest' AND product->>'projection_digest' !~ '^[0-9a-f]{64}$') OR NOT (product ? 'recipe_digest') OR (product ? 'recipe_digest' AND (jsonb_typeof(product->'recipe_digest') IS DISTINCT FROM 'string')) OR (product ? 'recipe_digest' AND product->>'recipe_digest' !~ '^[0-9a-f]{64}$') OR NOT (product ? 'projection') OR (product ? 'projection' AND (jsonb_typeof(product->'projection') IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(product->'projection') key WHERE key<>ALL(ARRAY['text','pieces','items','ancestors','health'])) OR NOT (product->'projection' ? 'text') OR (product->'projection' ? 'text' AND (jsonb_typeof(product->'projection'->'text') IS DISTINCT FROM 'string')) OR (product->'projection' ? 'pieces' AND (jsonb_typeof(product->'projection'->'pieces') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(product->'projection'->'pieces') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['item_ref','start','end','kind','cell_index','source_field'])) OR (nested_record ? 'item_ref' AND (jsonb_typeof(nested_record->'item_ref') IS DISTINCT FROM 'string')) OR (nested_record ? 'item_ref' AND nested_record->>'item_ref' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'start') OR (nested_record ? 'start' AND (jsonb_typeof(nested_record->'start') IS DISTINCT FROM 'number' OR nested_record->>'start' !~ '^[0-9]+$')) OR (nested_record ? 'start' AND (nested_record->>'start')::numeric < 0) OR NOT (nested_record ? 'end') OR (nested_record ? 'end' AND (jsonb_typeof(nested_record->'end') IS DISTINCT FROM 'number' OR nested_record->>'end' !~ '^[0-9]+$')) OR (nested_record ? 'end' AND (nested_record->>'end')::numeric < 0) OR NOT (nested_record ? 'kind') OR (nested_record ? 'kind' AND (jsonb_typeof(nested_record->'kind') IS DISTINCT FROM 'string')) OR (nested_record ? 'cell_index' AND (jsonb_typeof(nested_record->'cell_index') IS DISTINCT FROM 'number' OR nested_record->>'cell_index' !~ '^[0-9]+$')) OR (nested_record ? 'cell_index' AND (nested_record->>'cell_index')::numeric < 0) OR (nested_record ? 'source_field' AND (jsonb_typeof(nested_record->'source_field') IS DISTINCT FROM 'string')))))) OR NOT (product->'projection' ? 'items') OR (product->'projection' ? 'items' AND (jsonb_typeof(product->'projection'->'items') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(product->'projection'->'items') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string') OR jsonb_array_length(product->'projection'->'items') < 1)) OR (product->'projection' ? 'items' AND EXISTS(SELECT FROM jsonb_array_elements_text(product->'projection'->'items') element WHERE element !~ '^#(/[^/]+)+$')) OR (product->'projection' ? 'ancestors' AND (jsonb_typeof(product->'projection'->'ancestors') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(product->'projection'->'ancestors') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string'))) OR (product->'projection' ? 'ancestors' AND EXISTS(SELECT FROM jsonb_array_elements_text(product->'projection'->'ancestors') element WHERE element !~ '^#(/[^/]+)+$')) OR NOT (product->'projection' ? 'health') OR (product->'projection' ? 'health' AND (jsonb_typeof(product->'projection'->'health') IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(product->'projection'->'health') key WHERE key<>ALL(ARRAY['conversion','display_coverage','inline_coverage','cell_coverage','issues','formula_outcomes','candidate_policy','cells_policy','inline_scope','cell_scope','inline_membership','cell_membership'])) OR NOT (product->'projection'->'health' ? 'conversion') OR (product->'projection'->'health' ? 'conversion' AND (jsonb_typeof(product->'projection'->'health'->'conversion') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'conversion' NOT IN ('failure','partial_success','success'))) OR NOT (product->'projection'->'health' ? 'display_coverage') OR (product->'projection'->'health' ? 'display_coverage' AND (jsonb_typeof(product->'projection'->'health'->'display_coverage') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'display_coverage' NOT IN ('complete','partial','unknown','unsupported'))) OR NOT (product->'projection'->'health' ? 'inline_coverage') OR (product->'projection'->'health' ? 'inline_coverage' AND (jsonb_typeof(product->'projection'->'health'->'inline_coverage') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'inline_coverage' NOT IN ('complete','partial','unknown','unsupported'))) OR NOT (product->'projection'->'health' ? 'cell_coverage') OR (product->'projection'->'health' ? 'cell_coverage' AND (jsonb_typeof(product->'projection'->'health'->'cell_coverage') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'cell_coverage' NOT IN ('complete','partial','unknown','unsupported'))) OR (product->'projection'->'health' ? 'issues' AND (jsonb_typeof(product->'projection'->'health'->'issues') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(product->'projection'->'health'->'issues') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string'))) OR (product->'projection'->'health' ? 'formula_outcomes' AND (jsonb_typeof(product->'projection'->'health'->'formula_outcomes') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(product->'projection'->'health'->'formula_outcomes') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['pointer','outcome','error'])) OR NOT (nested_record ? 'pointer') OR (nested_record ? 'pointer' AND (jsonb_typeof(nested_record->'pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'pointer' AND nested_record->>'pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'outcome') OR (nested_record ? 'outcome' AND (jsonb_typeof(nested_record->'outcome') IS DISTINCT FROM 'string' OR nested_record->>'outcome' NOT IN ('failed','not_requested','succeeded','unknown'))) OR (nested_record ? 'error' AND (jsonb_typeof(nested_record->'error') IS DISTINCT FROM 'string')))))) OR (product->'projection'->'health' ? 'candidate_policy' AND (jsonb_typeof(product->'projection'->'health'->'candidate_policy') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'candidate_policy' NOT IN ('native-font-token-vector-ocr-word-v3','native-font-token-vector-v2','native-math-font-or-token-v1'))) OR (product->'projection'->'health' ? 'cells_policy' AND (jsonb_typeof(product->'projection'->'health'->'cells_policy') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'cells_policy' NOT IN ('all-nonempty-selected-cells-v1'))) OR (product->'projection'->'health' ? 'inline_scope' AND (jsonb_typeof(product->'projection'->'health'->'inline_scope') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(product->'projection'->'health'->'inline_scope') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string'))) OR (product->'projection'->'health' ? 'inline_scope' AND EXISTS(SELECT FROM jsonb_array_elements_text(product->'projection'->'health'->'inline_scope') element WHERE element !~ '^#(/[^/]+)+$')) OR (product->'projection'->'health' ? 'cell_scope' AND (jsonb_typeof(product->'projection'->'health'->'cell_scope') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(product->'projection'->'health'->'cell_scope') element WHERE jsonb_typeof(element) IS DISTINCT FROM 'string'))) OR (product->'projection'->'health' ? 'cell_scope' AND EXISTS(SELECT FROM jsonb_array_elements_text(product->'projection'->'health'->'cell_scope') element WHERE element !~ '^#(/[^/]+)+$')) OR (product->'projection'->'health' ? 'inline_membership' AND (jsonb_typeof(product->'projection'->'health'->'inline_membership') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'inline_membership' NOT IN ('descendants','direct'))) OR (product->'projection'->'health' ? 'cell_membership' AND (jsonb_typeof(product->'projection'->'health'->'cell_membership') IS DISTINCT FROM 'string' OR product->'projection'->'health'->>'cell_membership' NOT IN ('descendants','direct'))))))))) OR (product ? 'replaces_source_view_id' AND (jsonb_typeof(product->'replaces_source_view_id') IS DISTINCT FROM 'number' OR product->>'replaces_source_view_id' !~ '^[0-9]+$')) OR (product ? 'replaces_source_view_id' AND (product->>'replaces_source_view_id')::numeric < 1) OR NOT (product ? 'analysis_eligible') OR (product ? 'analysis_eligible' AND (jsonb_typeof(product->'analysis_eligible') IS DISTINCT FROM 'boolean')) THEN RAISE EXCEPTION 'parsing record shape differs: PdfSourceViewPublication' USING ERRCODE='23514'; END IF;

 projection:=product->'projection';
 IF product->>'recipe_digest' IS DISTINCT FROM encode(sha256(p_recipe),'hex') OR
 product->>'projection_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(projection),'UTF8')),'hex') THEN
 RAISE EXCEPTION 'source view recipe/projection identity differs' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT native FROM ops.native_document_product WHERE task_id=(product->>'native_task_id')::bigint AND product_key=product->>'native_product_key' AND content_digest=product->>'native_content_digest';
 -- Cross-release reuse is explicitly pinned to an archived native schema and producer contract.
 IF NOT EXISTS(SELECT FROM kb.document d JOIN ops.source_build b ON b.artifact_digest=d.content_hash JOIN ops.task t ON t.id=b.task_id JOIN ops.run r ON r.id=t.run_id
 WHERE d.id=(product->>'document_id')::bigint AND d.project_id=run.project_id AND b.task_id=native.task_id AND r.project_id=run.project_id AND EXISTS(SELECT FROM ops.source_build own WHERE own.task_id=p_task AND own.artifact_digest=b.artifact_digest)) THEN
 RAISE EXCEPTION 'native source view outside original/project custody' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.input WHERE release_id=native.release_id AND input_kind='dependency' AND input_name='execution/schema/pdf_products' AND encode(sha256(content),'hex')=native.contract_digest)
 OR NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/implementation/pdf/docling-validation.schema.json' AND encode(sha256(content),'hex')=native.schema_digest) THEN
 RAISE EXCEPTION 'native producer/consumer schema compatibility is unavailable' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT section FROM kb.native_document_item WHERE task_id=native.task_id AND product_key=native.product_key AND pointer=product->>'section_pointer';
 IF section.label NOT IN ('section','chapter') THEN RAISE EXCEPTION 'source view requires admitted section container' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements_text(projection->'items') ptr WHERE NOT EXISTS(SELECT FROM kb.native_document_item WHERE task_id=native.task_id AND product_key=native.product_key AND pointer=ptr))
 OR EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(projection->'ancestors','[]')) ptr WHERE NOT EXISTS(SELECT FROM kb.native_document_item WHERE task_id=native.task_id AND product_key=native.product_key AND pointer=ptr)) THEN
 RAISE EXCEPTION 'source view references an unqualified occurrence' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM jsonb_array_elements_text(projection->'items'))<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(projection->'items')) THEN
 RAISE EXCEPTION 'source view repeats an occurrence' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(pointer ORDER BY ordinal),'[]'::jsonb) INTO expected FROM kb.native_document_item
 WHERE task_id=native.task_id AND product_key=native.product_key AND pointer IN (SELECT ops.native_scope_items(native.task_id,native.product_key,section.pointer,product->>'membership'));
 IF projection->'items' IS DISTINCT FROM expected THEN RAISE EXCEPTION 'source view membership/order is incomplete or differs' USING ERRCODE='23514'; END IF;
 WITH RECURSIVE ancestry AS (
 SELECT p.*,0 depth FROM kb.native_document_item p WHERE p.task_id=native.task_id AND p.product_key=native.product_key AND p.pointer=section.parent_pointer
 UNION ALL SELECT p.*,a.depth+1 FROM kb.native_document_item p JOIN ancestry a ON p.pointer=a.parent_pointer WHERE p.task_id=native.task_id AND p.product_key=native.product_key
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
   SELECT native_json INTO STRICT node FROM kb.native_document_item WHERE task_id=native.task_id AND product_key=native.product_key AND pointer=piece_pointer;
   IF piece->>'source_field'='cell_text' THEN
    node:=node->'data'->'table_cells'->((piece->>'cell_index')::integer);
   END IF;
   IF spelling IS DISTINCT FROM (node->>(CASE WHEN piece->>'source_field'='cell_text' THEN 'text' ELSE COALESCE(piece->>'source_field','text') END)) OR COALESCE(piece->>'source_field','text') NOT IN ('text','orig','cell_text') THEN
    RAISE EXCEPTION 'projected source text differs from native occurrence' USING ERRCODE='23514'; END IF;
  ELSE RAISE EXCEPTION 'unadmitted source projection operation' USING ERRCODE='23514'; END IF;
  pos:=stop;
 END LOOP;
 SELECT (native.health - 'formula_outcomes') || jsonb_build_object('formula_outcomes',COALESCE(jsonb_agg(o.value ORDER BY o.n) FILTER(WHERE projection->'items' ? (o.value->>'pointer')),'[]')) INTO expected FROM jsonb_array_elements(COALESCE(native.health->'formula_outcomes','[]')) WITH ORDINALITY o(value,n);
 IF EXISTS(SELECT FROM kb.native_document_coverage WHERE task_id=native.task_id AND product_key=native.product_key) THEN
  expected:=expected-ARRAY['inline_scope','cell_scope','inline_membership','cell_membership','candidate_policy','cells_policy'];
  FOREACH coverage_universe IN ARRAY ARRAY['display','inline','cell'] LOOP
   SELECT * INTO coverage_row FROM kb.native_document_coverage c WHERE c.task_id=native.task_id AND c.product_key=native.product_key AND c.universe=coverage_universe AND
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
 FROM kb.native_document_item i LEFT JOIN kb.native_document_item parent ON parent.task_id=i.task_id AND parent.product_key=i.product_key AND parent.pointer=i.parent_pointer
 LEFT JOIN jsonb_array_elements(COALESCE(native.health->'formula_outcomes','[]')) o(value) ON o.value->>'pointer'=i.pointer
 WHERE i.task_id=native.task_id AND i.product_key=native.product_key AND projection->'items' ? i.pointer AND i.label='formula' AND COALESCE(parent.label,'') NOT IN ('table','inline');
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
 IF FOUND THEN
  IF previous.projection IS DISTINCT FROM projection OR previous.native_content_digest<>native.content_digest OR previous.recipe_digest<>product->>'recipe_digest' OR previous.analysis_eligible IS DISTINCT FROM (product->>'analysis_eligible')::boolean THEN
   RAISE EXCEPTION 'immutable source view replay differs' USING ERRCODE='23514'; END IF;
  result:=previous.id;
 ELSE
  IF run.sealed OR run.status NOT IN ('created','running') OR job.status<>'running' THEN RAISE EXCEPTION 'source view run is no longer writable' USING ERRCODE='P0004'; END IF;
  INSERT INTO kb.source_artifact(artifact_digest,content) VALUES(encode(sha256(p_recipe),'hex'),p_recipe) ON CONFLICT DO NOTHING;
  INSERT INTO kb.source_view(analysis_eligible,key,document_id,release_id,native_task_id,native_product_key,native_content_digest,section_pointer,membership,projection_digest,recipe_digest,projection)
  VALUES((product->>'analysis_eligible')::boolean,product->>'key',(product->>'document_id')::bigint,run.release_id,native.task_id,native.product_key,native.content_digest,section.pointer,product->>'membership',product->>'projection_digest',product->>'recipe_digest',projection) RETURNING id INTO result;
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
DECLARE job ops.task; run ops.run;
BEGIN
 SELECT * INTO STRICT run FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=p_run;
 PERFORM sem.require_execution_operation(run.release_id,'publish_source_view');
 IF job.status<>'reused' OR job.reused_task_id IS NULL OR NOT ops.valid_reuse(job) OR run.sealed THEN
 RAISE EXCEPTION 'source view reuse is not bound to successful source origin' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.run_source_view(run_id,source_view_id,position)
 SELECT p_run,v.id,s.position FROM kb.source_view v JOIN ops.run_source_view s ON s.source_view_id=v.id JOIN ops.task t ON t.run_id=s.run_id
 WHERE t.id=job.reused_task_id AND v.native_task_id=job.reused_task_id ON CONFLICT DO NOTHING;
END $reuse$;
REVOKE ALL ON FUNCTION ops.select_reused_source_views(bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.select_reused_source_views(bigint,bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.validate_native_frame_source(p_frame jsonb) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $source$
DECLARE view kb.source_view; context jsonb; expected jsonb; sentence jsonb; piece jsonb;
BEGIN
 IF jsonb_typeof(p_frame) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'parsing record must be an object: PdfFrameSource' USING ERRCODE='23514'; END IF;
IF EXISTS(SELECT FROM jsonb_object_keys(p_frame) key WHERE key<>ALL(ARRAY['unit_ref','text','sentences','source_view_id','native_product','section_pointer','membership','projection_digest','recipe_digest','native_context'])) OR NOT (p_frame ? 'unit_ref') OR (p_frame ? 'unit_ref' AND (jsonb_typeof(p_frame->'unit_ref') IS DISTINCT FROM 'string')) OR NOT (p_frame ? 'text') OR (p_frame ? 'text' AND (jsonb_typeof(p_frame->'text') IS DISTINCT FROM 'string')) OR NOT (p_frame ? 'sentences') OR (p_frame ? 'sentences' AND (jsonb_typeof(p_frame->'sentences') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'sentences') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['id','locator','start','end'])) OR NOT (nested_record ? 'id') OR (nested_record ? 'id' AND (jsonb_typeof(nested_record->'id') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'locator') OR (nested_record ? 'locator' AND (jsonb_typeof(nested_record->'locator') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'start') OR (nested_record ? 'start' AND (jsonb_typeof(nested_record->'start') IS DISTINCT FROM 'number' OR nested_record->>'start' !~ '^[0-9]+$')) OR (nested_record ? 'start' AND (nested_record->>'start')::numeric < 0) OR NOT (nested_record ? 'end') OR (nested_record ? 'end' AND (jsonb_typeof(nested_record->'end') IS DISTINCT FROM 'number' OR nested_record->>'end' !~ '^[0-9]+$')) OR (nested_record ? 'end' AND (nested_record->>'end')::numeric < 1))) OR jsonb_array_length(p_frame->'sentences') < 1)) OR NOT (p_frame ? 'source_view_id') OR (p_frame ? 'source_view_id' AND (jsonb_typeof(p_frame->'source_view_id') IS DISTINCT FROM 'number' OR p_frame->>'source_view_id' !~ '^[0-9]+$')) OR (p_frame ? 'source_view_id' AND (p_frame->>'source_view_id')::numeric < 1) OR NOT (p_frame ? 'native_product') OR (p_frame ? 'native_product' AND (jsonb_typeof(p_frame->'native_product') IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(p_frame->'native_product') key WHERE key<>ALL(ARRAY['task_id','product_key','content_digest'])) OR NOT (p_frame->'native_product' ? 'task_id') OR (p_frame->'native_product' ? 'task_id' AND (jsonb_typeof(p_frame->'native_product'->'task_id') IS DISTINCT FROM 'number' OR p_frame->'native_product'->>'task_id' !~ '^[0-9]+$')) OR (p_frame->'native_product' ? 'task_id' AND (p_frame->'native_product'->>'task_id')::numeric < 1) OR NOT (p_frame->'native_product' ? 'product_key') OR (p_frame->'native_product' ? 'product_key' AND (jsonb_typeof(p_frame->'native_product'->'product_key') IS DISTINCT FROM 'string')) OR NOT (p_frame->'native_product' ? 'content_digest') OR (p_frame->'native_product' ? 'content_digest' AND (jsonb_typeof(p_frame->'native_product'->'content_digest') IS DISTINCT FROM 'string')) OR (p_frame->'native_product' ? 'content_digest' AND p_frame->'native_product'->>'content_digest' !~ '^[0-9a-f]{64}$')))) OR NOT (p_frame ? 'section_pointer') OR (p_frame ? 'section_pointer' AND (jsonb_typeof(p_frame->'section_pointer') IS DISTINCT FROM 'string')) OR (p_frame ? 'section_pointer' AND p_frame->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (p_frame ? 'membership') OR (p_frame ? 'membership' AND (jsonb_typeof(p_frame->'membership') IS DISTINCT FROM 'string' OR p_frame->>'membership' NOT IN ('descendants','direct'))) OR NOT (p_frame ? 'projection_digest') OR (p_frame ? 'projection_digest' AND (jsonb_typeof(p_frame->'projection_digest') IS DISTINCT FROM 'string')) OR (p_frame ? 'projection_digest' AND p_frame->>'projection_digest' !~ '^[0-9a-f]{64}$') OR NOT (p_frame ? 'recipe_digest') OR (p_frame ? 'recipe_digest' AND (jsonb_typeof(p_frame->'recipe_digest') IS DISTINCT FROM 'string')) OR (p_frame ? 'recipe_digest' AND p_frame->>'recipe_digest' !~ '^[0-9a-f]{64}$') OR NOT (p_frame ? 'native_context') OR (p_frame ? 'native_context' AND (jsonb_typeof(p_frame->'native_context') IS DISTINCT FROM 'string')) THEN RAISE EXCEPTION 'parsing record shape differs: PdfFrameSource' USING ERRCODE='23514'; END IF;

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
 'items',(SELECT COALESCE(jsonb_agg(i.native_json ORDER BY ptr.n),'[]') FROM jsonb_array_elements_text(view.projection->'items') WITH ORDINALITY ptr(value,n) JOIN kb.native_document_item i ON i.task_id=view.native_task_id AND i.product_key=view.native_product_key AND i.pointer=ptr.value),
 'ancestors',(SELECT COALESCE(jsonb_agg(i.native_json ORDER BY ptr.n),'[]') FROM jsonb_array_elements_text(COALESCE(view.projection->'ancestors','[]')) WITH ORDINALITY ptr(value,n) JOIN kb.native_document_item i ON i.task_id=view.native_task_id AND i.product_key=view.native_product_key AND i.pointer=ptr.value)) INTO expected
 FROM ops.native_document_product p WHERE p.task_id=view.native_task_id AND p.product_key=view.native_product_key;
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
 IF jsonb_typeof(p_frame) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'parsing record must be an object: PdfNativeProposalFrame' USING ERRCODE='23514'; END IF;
IF EXISTS(SELECT FROM jsonb_object_keys(p_frame) key WHERE key<>ALL(ARRAY['context_sources','unit_ref','text','sentences','source_view_id','native_product','section_pointer','membership','projection_digest','recipe_digest','native_context'])) OR (p_frame ? 'context_sources' AND (jsonb_typeof(p_frame->'context_sources') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'context_sources') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['unit_ref','text','sentences','source_view_id','native_product','section_pointer','membership','projection_digest','recipe_digest','native_context'])) OR NOT (nested_record ? 'unit_ref') OR (nested_record ? 'unit_ref' AND (jsonb_typeof(nested_record->'unit_ref') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'text') OR (nested_record ? 'text' AND (jsonb_typeof(nested_record->'text') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'sentences') OR (nested_record ? 'sentences' AND (jsonb_typeof(nested_record->'sentences') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(nested_record->'sentences') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['id','locator','start','end'])) OR NOT (nested_record ? 'id') OR (nested_record ? 'id' AND (jsonb_typeof(nested_record->'id') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'locator') OR (nested_record ? 'locator' AND (jsonb_typeof(nested_record->'locator') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'start') OR (nested_record ? 'start' AND (jsonb_typeof(nested_record->'start') IS DISTINCT FROM 'number' OR nested_record->>'start' !~ '^[0-9]+$')) OR (nested_record ? 'start' AND (nested_record->>'start')::numeric < 0) OR NOT (nested_record ? 'end') OR (nested_record ? 'end' AND (jsonb_typeof(nested_record->'end') IS DISTINCT FROM 'number' OR nested_record->>'end' !~ '^[0-9]+$')) OR (nested_record ? 'end' AND (nested_record->>'end')::numeric < 1))) OR jsonb_array_length(nested_record->'sentences') < 1)) OR NOT (nested_record ? 'source_view_id') OR (nested_record ? 'source_view_id' AND (jsonb_typeof(nested_record->'source_view_id') IS DISTINCT FROM 'number' OR nested_record->>'source_view_id' !~ '^[0-9]+$')) OR (nested_record ? 'source_view_id' AND (nested_record->>'source_view_id')::numeric < 1) OR NOT (nested_record ? 'native_product') OR (nested_record ? 'native_product' AND (jsonb_typeof(nested_record->'native_product') IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record->'native_product') key WHERE key<>ALL(ARRAY['task_id','product_key','content_digest'])) OR NOT (nested_record->'native_product' ? 'task_id') OR (nested_record->'native_product' ? 'task_id' AND (jsonb_typeof(nested_record->'native_product'->'task_id') IS DISTINCT FROM 'number' OR nested_record->'native_product'->>'task_id' !~ '^[0-9]+$')) OR (nested_record->'native_product' ? 'task_id' AND (nested_record->'native_product'->>'task_id')::numeric < 1) OR NOT (nested_record->'native_product' ? 'product_key') OR (nested_record->'native_product' ? 'product_key' AND (jsonb_typeof(nested_record->'native_product'->'product_key') IS DISTINCT FROM 'string')) OR NOT (nested_record->'native_product' ? 'content_digest') OR (nested_record->'native_product' ? 'content_digest' AND (jsonb_typeof(nested_record->'native_product'->'content_digest') IS DISTINCT FROM 'string')) OR (nested_record->'native_product' ? 'content_digest' AND nested_record->'native_product'->>'content_digest' !~ '^[0-9a-f]{64}$')))) OR NOT (nested_record ? 'section_pointer') OR (nested_record ? 'section_pointer' AND (jsonb_typeof(nested_record->'section_pointer') IS DISTINCT FROM 'string')) OR (nested_record ? 'section_pointer' AND nested_record->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (nested_record ? 'membership') OR (nested_record ? 'membership' AND (jsonb_typeof(nested_record->'membership') IS DISTINCT FROM 'string' OR nested_record->>'membership' NOT IN ('descendants','direct'))) OR NOT (nested_record ? 'projection_digest') OR (nested_record ? 'projection_digest' AND (jsonb_typeof(nested_record->'projection_digest') IS DISTINCT FROM 'string')) OR (nested_record ? 'projection_digest' AND nested_record->>'projection_digest' !~ '^[0-9a-f]{64}$') OR NOT (nested_record ? 'recipe_digest') OR (nested_record ? 'recipe_digest' AND (jsonb_typeof(nested_record->'recipe_digest') IS DISTINCT FROM 'string')) OR (nested_record ? 'recipe_digest' AND nested_record->>'recipe_digest' !~ '^[0-9a-f]{64}$') OR NOT (nested_record ? 'native_context') OR (nested_record ? 'native_context' AND (jsonb_typeof(nested_record->'native_context') IS DISTINCT FROM 'string')))))) OR NOT (p_frame ? 'unit_ref') OR (p_frame ? 'unit_ref' AND (jsonb_typeof(p_frame->'unit_ref') IS DISTINCT FROM 'string')) OR NOT (p_frame ? 'text') OR (p_frame ? 'text' AND (jsonb_typeof(p_frame->'text') IS DISTINCT FROM 'string')) OR NOT (p_frame ? 'sentences') OR (p_frame ? 'sentences' AND (jsonb_typeof(p_frame->'sentences') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'sentences') nested_record WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(nested_record) key WHERE key<>ALL(ARRAY['id','locator','start','end'])) OR NOT (nested_record ? 'id') OR (nested_record ? 'id' AND (jsonb_typeof(nested_record->'id') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'locator') OR (nested_record ? 'locator' AND (jsonb_typeof(nested_record->'locator') IS DISTINCT FROM 'string')) OR NOT (nested_record ? 'start') OR (nested_record ? 'start' AND (jsonb_typeof(nested_record->'start') IS DISTINCT FROM 'number' OR nested_record->>'start' !~ '^[0-9]+$')) OR (nested_record ? 'start' AND (nested_record->>'start')::numeric < 0) OR NOT (nested_record ? 'end') OR (nested_record ? 'end' AND (jsonb_typeof(nested_record->'end') IS DISTINCT FROM 'number' OR nested_record->>'end' !~ '^[0-9]+$')) OR (nested_record ? 'end' AND (nested_record->>'end')::numeric < 1))) OR jsonb_array_length(p_frame->'sentences') < 1)) OR NOT (p_frame ? 'source_view_id') OR (p_frame ? 'source_view_id' AND (jsonb_typeof(p_frame->'source_view_id') IS DISTINCT FROM 'number' OR p_frame->>'source_view_id' !~ '^[0-9]+$')) OR (p_frame ? 'source_view_id' AND (p_frame->>'source_view_id')::numeric < 1) OR NOT (p_frame ? 'native_product') OR (p_frame ? 'native_product' AND (jsonb_typeof(p_frame->'native_product') IS DISTINCT FROM 'object' OR (EXISTS(SELECT FROM jsonb_object_keys(p_frame->'native_product') key WHERE key<>ALL(ARRAY['task_id','product_key','content_digest'])) OR NOT (p_frame->'native_product' ? 'task_id') OR (p_frame->'native_product' ? 'task_id' AND (jsonb_typeof(p_frame->'native_product'->'task_id') IS DISTINCT FROM 'number' OR p_frame->'native_product'->>'task_id' !~ '^[0-9]+$')) OR (p_frame->'native_product' ? 'task_id' AND (p_frame->'native_product'->>'task_id')::numeric < 1) OR NOT (p_frame->'native_product' ? 'product_key') OR (p_frame->'native_product' ? 'product_key' AND (jsonb_typeof(p_frame->'native_product'->'product_key') IS DISTINCT FROM 'string')) OR NOT (p_frame->'native_product' ? 'content_digest') OR (p_frame->'native_product' ? 'content_digest' AND (jsonb_typeof(p_frame->'native_product'->'content_digest') IS DISTINCT FROM 'string')) OR (p_frame->'native_product' ? 'content_digest' AND p_frame->'native_product'->>'content_digest' !~ '^[0-9a-f]{64}$')))) OR NOT (p_frame ? 'section_pointer') OR (p_frame ? 'section_pointer' AND (jsonb_typeof(p_frame->'section_pointer') IS DISTINCT FROM 'string')) OR (p_frame ? 'section_pointer' AND p_frame->>'section_pointer' !~ '^#(/[^/]+)+$') OR NOT (p_frame ? 'membership') OR (p_frame ? 'membership' AND (jsonb_typeof(p_frame->'membership') IS DISTINCT FROM 'string' OR p_frame->>'membership' NOT IN ('descendants','direct'))) OR NOT (p_frame ? 'projection_digest') OR (p_frame ? 'projection_digest' AND (jsonb_typeof(p_frame->'projection_digest') IS DISTINCT FROM 'string')) OR (p_frame ? 'projection_digest' AND p_frame->>'projection_digest' !~ '^[0-9a-f]{64}$') OR NOT (p_frame ? 'recipe_digest') OR (p_frame ? 'recipe_digest' AND (jsonb_typeof(p_frame->'recipe_digest') IS DISTINCT FROM 'string')) OR (p_frame ? 'recipe_digest' AND p_frame->>'recipe_digest' !~ '^[0-9a-f]{64}$') OR NOT (p_frame ? 'native_context') OR (p_frame ? 'native_context' AND (jsonb_typeof(p_frame->'native_context') IS DISTINCT FROM 'string')) THEN RAISE EXCEPTION 'parsing record shape differs: PdfNativeProposalFrame' USING ERRCODE='23514'; END IF;

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
DECLARE target ops.run; origin ops.run;
BEGIN
 SELECT * INTO STRICT target FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT origin FROM ops.run WHERE id=p_source_run;
 PERFORM sem.require_execution_operation(target.release_id,'publish_source_view');
 IF target.sealed OR target.project_id<>origin.project_id OR target.release_id<>origin.release_id OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=p_source_run AND source_view_id=p_view) THEN
 RAISE EXCEPTION 'source request selection differs from qualified origin' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.run_source_view(run_id,source_view_id,position) VALUES(p_run,p_view,0) ON CONFLICT DO NOTHING;
END $select$;
REVOKE ALL ON FUNCTION ops.select_source_view(bigint,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.select_source_view(bigint,bigint,bigint) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.publish_pdf_region_artifact(p_task bigint,p_attempt bigint,p_holder text,p_selection jsonb,p_recipe bytea,p_content bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $artifact$
DECLARE job ops.task; run ops.run; product ops.native_document_product; previous ops.native_region_artifact; digest text;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task FOR UPDATE;
 SELECT * INTO STRICT run FROM ops.run WHERE id=job.run_id FOR SHARE;
 PERFORM sem.require_execution_operation(run.release_id,'publish_pdf_region_artifact');
 IF run.sealed OR job.status<>'running' OR job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'region artifact attempt lost' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT product FROM ops.native_document_product WHERE task_id=(p_selection->>'task_id')::bigint AND product_key=p_selection->>'product_key' AND content_digest=p_selection->>'content_digest';
 IF NOT EXISTS(SELECT FROM ops.source_build b JOIN kb.document d ON d.content_hash=b.artifact_digest WHERE b.task_id=product.task_id AND d.project_id=run.project_id AND
 ((job.unit_type='document' AND job.unit_id=d.id) OR (job.unit_type='source_view' AND EXISTS(SELECT FROM kb.source_view v JOIN ops.run_source_view rs ON rs.source_view_id=v.id WHERE rs.run_id=run.id AND v.id=job.unit_id AND v.document_id=d.id))))
 OR NOT EXISTS(SELECT FROM kb.native_document_region WHERE task_id=product.task_id AND product_key=product.product_key AND pointer=p_selection->>'pointer' AND region_index=(p_selection->>'region_index')::bigint) THEN
 RAISE EXCEPTION 'render artifact is outside selected native original/region' USING ERRCODE='23514'; END IF;
 digest:=encode(sha256(p_content),'hex');
 SELECT * INTO previous FROM ops.native_region_artifact WHERE task_id=p_task;
 IF FOUND THEN
 IF previous.artifact_digest<>digest OR previous.recipe_digest<>encode(sha256(p_recipe),'hex') THEN RAISE EXCEPTION 'immutable region artifact replay differs' USING ERRCODE='23514'; END IF;
 RETURN digest; END IF;
 INSERT INTO kb.source_artifact SELECT encode(sha256(content),'hex'),content FROM unnest(ARRAY[p_recipe,p_content]) content ON CONFLICT DO NOTHING;
 INSERT INTO ops.native_region_artifact VALUES(p_task,product.task_id,product.product_key,product.content_digest,p_selection->>'pointer',(p_selection->>'region_index')::bigint,encode(sha256(p_recipe),'hex'),digest);
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
 ELSIF dependency='source_view_interpretation' THEN
  IF child.unit_id<>parent.unit_id OR NOT EXISTS(SELECT FROM ops.method_config consumer JOIN ops.method_config producer ON producer.id=parent.method_config_id JOIN ops.method method ON method.id=producer.method_id
    WHERE consumer.id=child.method_config_id AND consumer.params->>'source_dependency_method'=method.name) THEN
   RAISE EXCEPTION 'source prerequisite is not the declared same-view interpretation producer' USING ERRCODE='23514'; END IF;
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
 IF bound_release IS NOT NULL AND NEW.scope_type='segment' AND NOT EXISTS (SELECT FROM kb.segment s JOIN kb.rendition rd ON rd.id=s.rendition_id JOIN kb.document doc ON doc.id=rd.document_id JOIN ops.run producer ON producer.id=NEW.run_id WHERE doc.project_id=producer.project_id AND (NEW.scope_id IS NOT NULL OR NEW.scope_key IS NOT NULL) AND (NEW.scope_id IS NULL OR s.id=NEW.scope_id) AND (NEW.scope_key IS NULL OR s.segment_key=NEW.scope_key)) THEN
 RAISE EXCEPTION 'measurement segment subject is outside bound project' USING ERRCODE='23514'; END IF;
 IF bound_release IS NOT NULL AND NOT EXISTS (SELECT FROM sem.metric_definition d WHERE d.release_id=bound_release AND d.metric_id=NEW.metric AND d.subject_kind=NEW.scope_type) THEN
 RAISE EXCEPTION 'unresolved metric or incompatible measurement subject' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $fn$;

