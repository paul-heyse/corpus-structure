-- Immutable section views are instances, never fabricated document/rendition rows.
CREATE OR REPLACE FUNCTION ops.publish_source_view(p_run bigint,p_task bigint,p_attempt bigint,p_holder text,p_position bigint,p_payload bytea,p_recipe bytea) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $view$
DECLARE job ops.task; run ops.run; product jsonb; parsing_item jsonb; projection jsonb; piece jsonb;
 native ops.native_document_product; section kb.native_document_item; previous kb.source_view; result bigint;
 pos bigint:=0; stop bigint; node jsonb; spelling text; piece_pointer text; expected jsonb;
BEGIN
 SELECT * INTO STRICT run FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=p_run FOR UPDATE;
 PERFORM sem.require_execution_operation(run.release_id,'publish_source_view');
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'source view attempt lost' USING ERRCODE='P0004'; END IF;
 product:=convert_from(p_payload,'UTF8')::jsonb;
 -- {source_view_shape_guard}
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
 WITH RECURSIVE selected AS (
 SELECT * FROM kb.native_document_item WHERE task_id=native.task_id AND product_key=native.product_key AND pointer=section.pointer
 UNION ALL SELECT child.* FROM kb.native_document_item child JOIN selected parent ON child.parent_pointer=parent.pointer
 WHERE child.task_id=native.task_id AND child.product_key=native.product_key
 ) SELECT COALESCE(jsonb_agg(pointer ORDER BY ordinal),'[]'::jsonb) INTO expected FROM selected
 WHERE content_layer='body' AND (product->>'membership'='descendants' OR section_pointer=section.pointer);
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

CREATE OR REPLACE FUNCTION ops.capture_native_source_frame(p_task bigint,p_hash text,p_frame jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $frame$
DECLARE job ops.task; view kb.source_view; context jsonb; expected jsonb; previous ops.native_source_frame; sentence jsonb;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task FOR UPDATE;
 PERFORM sem.require_execution_operation(job.release_id,'capture_native_source_frame');
 SELECT * INTO STRICT view FROM kb.source_view WHERE id=(p_frame->>'source_view_id')::bigint;
 IF job.unit_type<>'source_view' OR job.unit_id<>view.id OR job.packet_hash IS DISTINCT FROM p_hash OR job.unit_key IS DISTINCT FROM p_frame->>'unit_ref'
 OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=job.run_id AND source_view_id=view.id)
 OR p_frame->>'section_pointer' IS DISTINCT FROM view.section_pointer OR p_frame->>'membership' IS DISTINCT FROM view.membership
 OR p_frame->>'text' IS DISTINCT FROM view.projection->>'text'
 OR p_frame->>'projection_digest' IS DISTINCT FROM view.projection_digest OR p_frame->>'recipe_digest' IS DISTINCT FROM view.recipe_digest
 OR (p_frame->'native_product'->>'task_id')::bigint IS DISTINCT FROM view.native_task_id
 OR p_frame->'native_product'->>'product_key' IS DISTINCT FROM view.native_product_key
 OR p_frame->'native_product'->>'content_digest' IS DISTINCT FROM view.native_content_digest THEN
 RAISE EXCEPTION 'native packet frame differs from selected source view/task' USING ERRCODE='23514'; END IF;
 context:=(p_frame->>'native_context')::jsonb;
 SELECT jsonb_build_object('pieces',view.projection->'pieces','health',view.projection->'health',
 'items',(SELECT COALESCE(jsonb_agg(i.native_json ORDER BY ptr.n),'[]') FROM jsonb_array_elements_text(view.projection->'items') WITH ORDINALITY ptr(value,n) JOIN kb.native_document_item i ON i.task_id=view.native_task_id AND i.product_key=view.native_product_key AND i.pointer=ptr.value),
 'ancestors',(SELECT COALESCE(jsonb_agg(i.native_json ORDER BY ptr.n),'[]') FROM jsonb_array_elements_text(COALESCE(view.projection->'ancestors','[]')) WITH ORDINALITY ptr(value,n) JOIN kb.native_document_item i ON i.task_id=view.native_task_id AND i.product_key=view.native_product_key AND i.pointer=ptr.value)) INTO expected
 FROM ops.native_document_product p WHERE p.task_id=view.native_task_id AND p.product_key=view.native_product_key;
 IF context IS DISTINCT FROM expected THEN RAISE EXCEPTION 'native packet omitted or changed supplied source context' USING ERRCODE='23514'; END IF;
 SELECT * INTO previous FROM ops.native_source_frame WHERE task_id=p_task;
 IF FOUND THEN
  IF previous.packet_hash<>p_hash OR previous.context_json IS DISTINCT FROM context
   OR (SELECT count(*) FROM ops.native_source_frame_sentence WHERE task_id=p_task)<>jsonb_array_length(p_frame->'sentences')
   OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'sentences') item LEFT JOIN ops.native_source_frame_sentence saved ON saved.task_id=p_task AND saved.sentence_id=item->>'id'
    WHERE saved.task_id IS NULL OR saved.locator IS DISTINCT FROM item->>'locator' OR saved.start_offset IS DISTINCT FROM (item->>'start')::bigint OR saved.end_offset IS DISTINCT FROM (item->>'end')::bigint)
  THEN RAISE EXCEPTION 'immutable native frame replay differs' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 INSERT INTO ops.native_source_frame VALUES(p_task,p_hash,p_frame->>'unit_ref',view.id,view.native_task_id,view.native_product_key,view.native_content_digest,view.projection_digest,view.recipe_digest,context);
 FOR sentence IN SELECT value FROM jsonb_array_elements(p_frame->'sentences') LOOP
  IF (sentence->>'start')::bigint<0 OR (sentence->>'end')::bigint<=(sentence->>'start')::bigint OR (sentence->>'end')::bigint>char_length(view.projection->>'text') THEN
   RAISE EXCEPTION 'native frame sentence lies outside projected text' USING ERRCODE='23514'; END IF;
  PERFORM ops.native_source_address(view.id,sentence->>'locator',(sentence->>'start')::bigint,(sentence->>'end')::bigint);
  INSERT INTO ops.native_source_frame_sentence VALUES(p_task,sentence->>'id',sentence->>'locator',(sentence->>'start')::bigint,(sentence->>'end')::bigint);
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
