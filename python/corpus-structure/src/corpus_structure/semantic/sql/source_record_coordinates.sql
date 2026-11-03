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
  SELECT jsonb_object_agg(v.id::text,to_jsonb(v)) INTO source_views FROM kb.source_view v
   JOIN ops.run_source_view selected ON selected.source_view_id=v.id AND selected.run_id=p_run
   WHERE v.id IN (SELECT DISTINCT (a->'pin'->>'source_view_id')::bigint
    FROM jsonb_array_elements(record_anchors) a);
  FOR source_pin IN SELECT DISTINCT a->'pin' FROM jsonb_array_elements(record_anchors) a LOOP
    anchor_view:=jsonb_populate_record(NULL::kb.source_view,source_views->(source_pin->>'source_view_id'));
    IF anchor_view.id IS NULL OR anchor_view.native_build_id IS DISTINCT FROM record_placement.build_id
     OR anchor_view.native_revision_id IS DISTINCT FROM record_placement.build_id
     OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=p_run AND source_view_id=anchor_view.id)
     OR (anchor_view.native_task_id,anchor_view.native_product_key,anchor_view.native_content_digest)
      IS DISTINCT FROM (view.native_task_id,view.native_product_key,view.native_content_digest)
     OR source_pin IS DISTINCT FROM jsonb_build_object(
      'source',CASE WHEN anchor_view.id=view.id THEN p_source ELSE anchor_view.key END,
      'native_product_task_id',anchor_view.native_task_id,'product_key',anchor_view.native_product_key,
      'product_digest',anchor_view.native_content_digest,'projection_digest',anchor_view.projection_digest,
      'recipe_digest',anchor_view.recipe_digest,'source_view_id',anchor_view.id) THEN
     RAISE EXCEPTION 'private record related pin is stale, unselected or outside its native product' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF EXISTS(SELECT FROM jsonb_array_elements(record_anchors) a CROSS JOIN LATERAL (
   SELECT CASE WHEN a->>'pointer' ~ '^#/tables/(0|[1-9][0-9]*)/data/table_cells/(0|[1-9][0-9]*)$'
    THEN split_part(a->>'pointer','/data/table_cells/',1) ELSE a->>'pointer' END AS pointer) q
   WHERE NOT ((source_views->(a->'pin'->>'source_view_id')->'projection'->'items') ? q.pointer
    OR COALESCE(source_views->(a->'pin'->>'source_view_id')->'projection'->'ancestors','[]') ? q.pointer)) THEN
   RAISE EXCEPTION 'private record anchor is outside selected source view' USING ERRCODE='23514'; END IF;
  SELECT jsonb_object_agg(pointer,native_json) INTO native_nodes FROM ops.read_pdf_published_items(
   view.native_task_id,view.native_product_key,view.native_content_digest,ARRAY(
    SELECT DISTINCT CASE WHEN a->>'pointer' ~ '^#/tables/(0|[1-9][0-9]*)/data/table_cells/(0|[1-9][0-9]*)$'
     THEN split_part(a->>'pointer','/data/table_cells/',1) ELSE a->>'pointer' END
    FROM jsonb_array_elements(record_anchors) a));
  FOR record_anchor IN SELECT value FROM jsonb_array_elements(record_anchors) LOOP
    IF record_anchor->>'space'='model_context' THEN
     RAISE EXCEPTION 'model context is not admitted source evidence' USING ERRCODE='23514'; END IF;
    IF record_anchor ? 'binding' THEN
     IF record_anchor->'binding' NOT IN (
      '{"version":2,"relationship":"primary","policy":"attributed-selected-source-2"}'::jsonb,
      '{"version":2,"relationship":"selected_context","policy":"attributed-selected-source-2"}'::jsonb)
      OR (record_anchor->'binding'->>'relationship'='primary' AND record_anchor->'pin' IS DISTINCT FROM primary_pin) THEN
      RAISE EXCEPTION 'unsupported or contradictory source binding' USING ERRCODE='23514'; END IF;
    ELSIF record_anchor->'pin' IS DISTINCT FROM primary_pin OR record_anchor->>'space'='captured_recognition' THEN
     RAISE EXCEPTION 'private record anchor lacks attributed source binding' USING ERRCODE='23514'; END IF;
    anchor_view:=jsonb_populate_record(NULL::kb.source_view,
     source_views->(record_anchor->'pin'->>'source_view_id'));
    record_pointer:=record_anchor->>'pointer'; record_cell:=NULL;
    IF record_pointer ~ '^#/tables/(0|[1-9][0-9]*)/data/table_cells/(0|[1-9][0-9]*)$' THEN
     record_cell:=split_part(record_pointer,'/data/table_cells/',2)::integer;
     record_pointer:=split_part(record_pointer,'/data/table_cells/',1);
    END IF;
    IF NOT (anchor_view.projection->'items' ? record_pointer OR COALESCE(anchor_view.projection->'ancestors','[]'::jsonb) ? record_pointer) THEN
     RAISE EXCEPTION 'private record anchor is outside selected source view' USING ERRCODE='23514'; END IF;
    record_node:=native_nodes->record_pointer;
    IF record_node IS NULL THEN
     RAISE EXCEPTION 'private record native pointer has no published body' USING ERRCODE='23514'; END IF;
    IF record_cell IS NOT NULL THEN
     record_node:=record_node->'data'->'table_cells'->record_cell;
     IF jsonb_typeof(record_node) IS DISTINCT FROM 'object' THEN
      RAISE EXCEPTION 'private record cell is outside native table' USING ERRCODE='23514'; END IF;
    END IF;
    record_text:=record_node->>'text';
    IF record_anchor->>'space'='captured_recognition' THEN
     IF record_cell IS NOT NULL OR NOT record_anchor ? 'recognition' OR record_anchor->>'precision'<>'exact' THEN
      RAISE EXCEPTION 'unsupported captured recognition address' USING ERRCODE='23514'; END IF;
     recognition_key:=jsonb_build_array(record_pointer,record_anchor->'recognition')::text;
     IF NOT recognition_texts ? recognition_key THEN
      record_text:=ops.record_captured_recognition_text(anchor_view.native_task_id,
       anchor_view.native_product_key,anchor_view.native_content_digest,record_pointer,record_anchor->'recognition');
      recognition_texts:=recognition_texts||jsonb_build_object(recognition_key,record_text);
     END IF;
     record_text:=recognition_texts->>recognition_key;
    ELSIF record_anchor ? 'recognition' THEN
     RAISE EXCEPTION 'recognition address cannot reinterpret canonical text' USING ERRCODE='23514';
    ELSIF record_anchor->>'space'='selected_projection' THEN
     IF record_anchor->>'precision'='exact' AND NOT EXISTS(
      SELECT FROM jsonb_array_elements(anchor_view.projection->'pieces') piece WHERE piece->>'kind'='native_text'
       AND piece->>'item_ref'=record_pointer AND (piece->>'start')::bigint<=(record_anchor->>'start')::bigint
       AND (record_anchor->>'end')::bigint<=(piece->>'end')::bigint
       AND ((record_cell IS NOT NULL AND piece->>'source_field'='cell_text' AND (piece->>'cell_index')::integer=record_cell)
        OR (record_cell IS NULL AND COALESCE(piece->>'source_field','text') IN ('text','orig')))
     ) THEN RAISE EXCEPTION 'private projection anchor crosses synthetic or different source pieces' USING ERRCODE='23514'; END IF;
     record_text:=anchor_view.projection->>'text';
    END IF;
    IF record_anchor->>'precision'='exact' THEN
     IF record_text IS NULL OR record_anchor->>'start' IS NULL OR record_anchor->>'end' IS NULL
      OR NOT (0<=(record_anchor->>'start')::bigint AND (record_anchor->>'start')::bigint<(record_anchor->>'end')::bigint
       AND (record_anchor->>'end')::bigint<=char_length(record_text))
      OR record_anchor->>'source_piece' IS DISTINCT FROM substr(record_text,(record_anchor->>'start')::integer+1,
       ((record_anchor->>'end')::bigint-(record_anchor->>'start')::bigint)::integer) THEN
      RAISE EXCEPTION 'private record anchor does not reconstruct actual persisted source text' USING ERRCODE='23514'; END IF;
    ELSIF record_anchor ? 'start' OR record_anchor ? 'end' OR (record_anchor ? 'source_piece'
      AND (record_node->>'text' IS NULL OR position(record_anchor->>'source_piece' IN record_node->>'text')=0)) THEN
     RAISE EXCEPTION 'coarse private record anchor invents an exact extent or source spelling' USING ERRCODE='23514';
    END IF;
   END LOOP;
 EXCEPTION WHEN check_violation OR no_data_found OR too_many_rows THEN
  RAISE USING MESSAGE=SQLERRM,ERRCODE='23514',DETAIL='{"protocol":"corpus-invariant-1","guard":"native_source_address","version":"2","invariant":"published_document_address"}';
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_record_coordinates(bigint,bigint,text,jsonb) FROM PUBLIC;
