-- Immutable section views are instances, never fabricated document/rendition rows.

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
