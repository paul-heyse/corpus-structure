-- Standing-neutral source custody. Authority and completeness belong to callers.
CREATE OR REPLACE FUNCTION ops.validate_source_record_coordinates(
 p_run bigint,p_source_view bigint,p_source text,p_records jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE run_ ops.run; view kb.source_view; anchor_view kb.source_view;
 source_record jsonb; record_anchor jsonb; record_fields jsonb; record_schema json; source_schema json;
 record_pointer text; record_cell integer; record_node jsonb; record_text text;
 record_placement ops.pdf_published_revision; primary_pin jsonb; record_anchors jsonb;
 source_views jsonb; native_nodes jsonb; recognition_texts jsonb:='{}'; recognition_key text; source_pin jsonb;
BEGIN
 SELECT * INTO STRICT run_ FROM ops.run WHERE id=p_run;
 PERFORM sem.require_execution_operation(run_.release_id,'read_source_view');
 IF jsonb_typeof(p_records) IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'source coordinate custody requires an explicit record array' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT view FROM kb.source_view WHERE id=p_source_view;
  IF NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=p_run AND source_view_id=view.id)
   OR p_source IS NULL OR btrim(p_source)='' THEN
   RAISE EXCEPTION 'private record report logical source is not its selected task unit' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT record_placement FROM ops.read_pdf_published_revision(view.native_task_id,view.native_product_key,view.native_content_digest);
  IF view.native_build_id IS DISTINCT FROM record_placement.build_id OR view.native_revision_id IS DISTINCT FROM record_placement.build_id THEN
   RAISE EXCEPTION 'private record source placement differs from published product' USING ERRCODE='23514'; END IF;
  primary_pin:=jsonb_build_object('source',p_source,
   'native_product_task_id',view.native_task_id,'product_key',view.native_product_key,
   'product_digest',view.native_content_digest,'projection_digest',view.projection_digest,
   'recipe_digest',view.recipe_digest,'source_view_id',view.id);
  IF jsonb_array_length(p_records)=0 THEN RETURN; END IF;
  SELECT convert_from(content,'UTF8')::json INTO source_schema FROM sem.artifact
   WHERE release_id=run_.release_id AND artifact_name='json_schema/SourceRecord';
  FOR source_record IN SELECT value FROM jsonb_array_elements(p_records) LOOP
   IF source_schema IS NULL OR NOT public.json_matches_schema(source_schema,source_record::json) THEN
    RAISE EXCEPTION 'source record differs from released shape' USING ERRCODE='23514'; END IF;
   IF source_record->'pin' IS DISTINCT FROM jsonb_build_object(
    'source',p_source,'native_product_task_id',view.native_task_id,
    'product_key',view.native_product_key,'product_digest',view.native_content_digest,
    'projection_digest',view.projection_digest,'recipe_digest',view.recipe_digest,'source_view_id',view.id) THEN
    RAISE EXCEPTION 'private record pin differs from persisted selected source view' USING ERRCODE='23514'; END IF;
   SELECT convert_from(content,'UTF8')::json INTO record_schema FROM sem.artifact
    WHERE release_id=run_.release_id AND artifact_name='json_schema/'||(source_record->>'contract');
   SELECT jsonb_build_object('family',source_record->'family','occurrence_recipe',source_record->'occurrence_recipe')
    ||COALESCE(jsonb_object_agg(field->>'role',field),'{}'::jsonb) INTO record_fields
    FROM jsonb_array_elements(source_record->'fields') field;
   IF record_schema IS NULL OR NOT public.json_matches_schema(record_schema,record_fields::json) THEN
    RAISE EXCEPTION 'private record fields differ from released family shape' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM jsonb_array_elements(source_record->'anchors') a
    WHERE source_record->'occurrence_anchors' ? (a->>'anchor_id') AND
     (a->'pin' IS DISTINCT FROM source_record->'pin' OR a->>'space'='captured_recognition'
      OR COALESCE(a->'binding'->>'relationship','primary')<>'primary')) THEN
    RAISE EXCEPTION 'occurrence-defining anchors must remain primary' USING ERRCODE='23514'; END IF;

  END LOOP;
  SELECT COALESCE(jsonb_agg(a),'[]') INTO record_anchors FROM (
   SELECT DISTINCT a FROM jsonb_array_elements(p_records) r
   CROSS JOIN LATERAL jsonb_array_elements(r->'anchors') a) unique_anchors;
  PERFORM ops.validate_source_anchor_coordinates(p_run,p_source_view,p_source,record_anchors);
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_record_coordinates(bigint,bigint,text,jsonb) FROM PUBLIC;
