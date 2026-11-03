-- Private candidate custody only. Released shapes and actual source coordinates are
-- checked here; accepted whole-record publication has a separate admission owner.
IF p_envelope ? 'records' THEN
 BEGIN
  PERFORM sem.require_execution_operation(t.release_id,'bind_report');
  SELECT convert_from(content,'UTF8')::json INTO record_schema FROM sem.artifact
   WHERE release_id=t.release_id AND artifact_name='json_schema/SourceObservationBatch';
  IF record_schema IS NULL OR NOT public.json_matches_schema(record_schema,p_envelope::json) THEN
   RAISE EXCEPTION 'private record report differs from released shape' USING ERRCODE='23514'; END IF;
  IF t.unit_type<>'source_view' OR p_envelope->>'release_id' IS DISTINCT FROM t.release_id
   OR p_envelope->>'unit_key' IS DISTINCT FROM t.unit_key
   OR p_envelope->>'invocation_key' IS DISTINCT FROM t.invocation_key
   OR p_envelope->>'input_hash' IS DISTINCT FROM t.input_hash
   OR p_envelope->>'outcome' IS DISTINCT FROM (CASE p_outcome WHEN 'done' THEN 'produced' ELSE p_outcome END)
   OR NOT EXISTS(SELECT FROM ops.method_config c JOIN ops.method m ON m.id=c.method_id
    WHERE c.id=t.method_config_id AND c.config_hash=p_envelope->>'configuration_hash'
     AND m.name=p_envelope->>'method' AND m.version=p_envelope->>'operation_version') THEN
   RAISE EXCEPTION 'private record report differs from producing task binding' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT view FROM kb.source_view WHERE id=t.unit_id;
  IF NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=t.run_id AND source_view_id=view.id)
   OR p_envelope->>'source' NOT IN (t.unit_key,view.key) THEN
   RAISE EXCEPTION 'private record report logical source is not its selected task unit' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT record_placement FROM ops.read_pdf_published_revision(view.native_task_id,view.native_product_key,view.native_content_digest);
  IF view.native_build_id IS DISTINCT FROM record_placement.build_id OR view.native_revision_id IS DISTINCT FROM record_placement.build_id THEN
   RAISE EXCEPTION 'private record source placement differs from published product' USING ERRCODE='23514'; END IF;
  FOR source_record IN SELECT value FROM jsonb_array_elements(p_envelope->'records') LOOP
   IF source_record->>'standing'='accepted' THEN
    RAISE EXCEPTION 'private record custody does not admit accepted whole records' USING ERRCODE='23514'; END IF;
   IF source_record->'pin' IS DISTINCT FROM jsonb_build_object(
    'source',p_envelope->>'source','native_product_task_id',view.native_task_id,
    'product_key',view.native_product_key,'product_digest',view.native_content_digest,
    'projection_digest',view.projection_digest,'recipe_digest',view.recipe_digest,'source_view_id',view.id) THEN
    RAISE EXCEPTION 'private record pin differs from persisted selected source view' USING ERRCODE='23514'; END IF;
   SELECT convert_from(content,'UTF8')::json INTO record_schema FROM sem.artifact
    WHERE release_id=t.release_id AND artifact_name='json_schema/'||(source_record->>'contract');
   SELECT jsonb_build_object('family',source_record->'family','occurrence_recipe',source_record->'occurrence_recipe')
    ||COALESCE(jsonb_object_agg(field->>'role',field),'{}'::jsonb) INTO record_fields
    FROM jsonb_array_elements(source_record->'fields') field;
   IF record_schema IS NULL OR NOT public.json_matches_schema(record_schema,record_fields::json) THEN
    RAISE EXCEPTION 'private record fields differ from released family shape' USING ERRCODE='23514'; END IF;
   FOR record_anchor IN SELECT value FROM jsonb_array_elements(source_record->'anchors') LOOP
    IF record_anchor->'pin' IS DISTINCT FROM source_record->'pin' OR record_anchor->>'space'='model_context' THEN
     RAISE EXCEPTION 'private record anchor differs from qualified source pin' USING ERRCODE='23514'; END IF;
    record_pointer:=record_anchor->>'pointer'; record_cell:=NULL;
    IF record_pointer ~ '^#/tables/(0|[1-9][0-9]*)/data/table_cells/(0|[1-9][0-9]*)$' THEN
     record_cell:=split_part(record_pointer,'/data/table_cells/',2)::integer;
     record_pointer:=split_part(record_pointer,'/data/table_cells/',1);
    END IF;
    IF NOT (view.projection->'items' ? record_pointer OR COALESCE(view.projection->'ancestors','[]'::jsonb) ? record_pointer) THEN
     RAISE EXCEPTION 'private record anchor is outside selected source view' USING ERRCODE='23514'; END IF;
    SELECT native_json INTO STRICT record_node FROM kb.pdf_record_access
     WHERE product_id=view.native_build_id AND revision_id=view.native_revision_id AND pointer=record_pointer;
    IF record_cell IS NOT NULL THEN
     record_node:=record_node->'data'->'table_cells'->record_cell;
     IF jsonb_typeof(record_node) IS DISTINCT FROM 'object' THEN
      RAISE EXCEPTION 'private record cell is outside native table' USING ERRCODE='23514'; END IF;
    END IF;
    record_text:=record_node->>'text';
    IF record_anchor->>'space'='selected_projection' THEN
     IF record_anchor->>'precision'='exact' AND NOT EXISTS(
      SELECT FROM jsonb_array_elements(view.projection->'pieces') piece WHERE piece->>'kind'='native_text'
       AND piece->>'item_ref'=record_pointer AND (piece->>'start')::bigint<=(record_anchor->>'start')::bigint
       AND (record_anchor->>'end')::bigint<=(piece->>'end')::bigint
       AND ((record_cell IS NOT NULL AND piece->>'source_field'='cell_text' AND (piece->>'cell_index')::integer=record_cell)
        OR (record_cell IS NULL AND COALESCE(piece->>'source_field','text') IN ('text','orig')))
     ) THEN RAISE EXCEPTION 'private projection anchor crosses synthetic or different source pieces' USING ERRCODE='23514'; END IF;
     record_text:=view.projection->>'text';
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
  END LOOP;
 EXCEPTION WHEN check_violation THEN
  RAISE USING MESSAGE=SQLERRM,ERRCODE='23514',DETAIL='{"protocol":"corpus-invariant-1","guard":"native_source_address","version":"2","invariant":"published_document_address"}';
 END;
END IF;
