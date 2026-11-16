-- Only the exact persisted original-source read below grants custody. The pure
-- builder is shared semantic lowering; passing it caller JSON grants no admission.
CREATE OR REPLACE FUNCTION ops.ddo_native_source_body(p_document text,p_section text,p_membership text,p_projection jsonb,p_projection_digest text,p_items jsonb,p_selectors jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE atom jsonb; original jsonb; piece jsonb; selector jsonb; name text; cell jsonb; retained_cell jsonb; table_data jsonb; cells jsonb; pointers text[]:=ARRAY[]::text[];
 atoms jsonb:='[]'; ancestors jsonb:='[]'; all_atoms jsonb:='[]'; pieces jsonb:='[]'; recognition jsonb:='[]'; selected jsonb:='[]'; coordinate jsonb; projection text; text_value text:=p_projection->>'text'; previous bigint:=0;
BEGIN
 IF nullif(p_document,'') IS NULL OR nullif(p_section,'') IS NULL OR p_membership NOT IN ('direct','descendants')
 OR jsonb_typeof(p_items) IS DISTINCT FROM 'array' OR jsonb_typeof(p_selectors) IS DISTINCT FROM 'array' OR jsonb_array_length(p_selectors)=0
 OR jsonb_typeof(p_projection->'items') IS DISTINCT FROM 'array' OR jsonb_typeof(p_projection->'ancestors') IS DISTINCT FROM 'array'
 OR jsonb_typeof(p_projection->'text') IS DISTINCT FROM 'string' OR jsonb_typeof(p_projection->'pieces') IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'original source projection/request has invalid declared shape' USING ERRCODE='23514'; END IF;
 FOR original IN SELECT value FROM jsonb_array_elements(p_items) LOOP
 atom:='{}';
 FOREACH name IN ARRAY ARRAY['self_ref','label','text','orig','name','level','content_layer','marker','enumerated'] LOOP
 IF original ? name THEN atom:=atom||jsonb_build_object(name,original->name); END IF;
 END LOOP;
 IF jsonb_typeof(original->'parent'->'$ref')='string' THEN atom:=atom||jsonb_build_object('parent',original->'parent'->'$ref'); END IF;
 FOREACH name IN ARRAY ARRAY['children','captions','footnotes','references'] LOOP
 IF original ? name THEN atom:=atom||jsonb_build_object(name,(SELECT coalesce(jsonb_agg(value->'$ref' ORDER BY ordinal),'[]') FROM jsonb_array_elements(original->name) WITH ORDINALITY refs(value,ordinal))); END IF;
 END LOOP;
 IF original->'data' ? 'table_cells' THEN
 table_data:='{}'; cells:='[]';
 FOREACH name IN ARRAY ARRAY['num_rows','num_cols','orientation'] LOOP
 IF original->'data' ? name THEN table_data:=table_data||jsonb_build_object(name,original->'data'->name); END IF;
 END LOOP;
 FOR cell IN SELECT value FROM jsonb_array_elements(original->'data'->'table_cells') LOOP
 retained_cell:='{}';
 FOREACH name IN ARRAY ARRAY['text','row_span','col_span','start_row_offset_idx','end_row_offset_idx','start_col_offset_idx','end_col_offset_idx','column_header','row_header','row_section','fillable'] LOOP
 IF cell ? name THEN retained_cell:=retained_cell||jsonb_build_object(name,cell->name); END IF;
 END LOOP;
 IF cell->'ref'->>'$ref' IS NOT NULL THEN retained_cell:=retained_cell||jsonb_build_object('ref',cell->'ref'->'$ref'); END IF;
 cells:=cells||jsonb_build_array(retained_cell);
 END LOOP;
 atom:=atom||jsonb_build_object('data',table_data||jsonb_build_object('table_cells',cells));
 END IF;
 atom:=atom||jsonb_build_object('prov',(SELECT coalesce(jsonb_agg(jsonb_build_object('page_no',value->'page_no') ORDER BY ordinal),'[]') FROM jsonb_array_elements(coalesce(original->'prov','[]')) WITH ORDINALITY p(value,ordinal) WHERE value ? 'page_no'));
 IF nullif(atom->>'self_ref','') IS NULL OR atom->>'self_ref'=ANY(pointers) THEN RAISE EXCEPTION 'original source repeats or lacks an atom address'; END IF;
 pointers:=array_append(pointers,atom->>'self_ref'); atoms:=atoms||jsonb_build_array(atom);
 END LOOP;
 all_atoms:=atoms;
 SELECT coalesce(jsonb_agg(original_atom.value ORDER BY requested.ordinal),'[]') INTO atoms
 FROM jsonb_array_elements_text(p_projection->'items') WITH ORDINALITY requested(pointer,ordinal)
 JOIN jsonb_array_elements(all_atoms) original_atom ON original_atom.value->>'self_ref'=requested.pointer;
 SELECT coalesce(jsonb_agg(original_atom.value ORDER BY requested.ordinal),'[]') INTO ancestors
 FROM jsonb_array_elements_text(p_projection->'ancestors') WITH ORDINALITY requested(pointer,ordinal)
 JOIN jsonb_array_elements(all_atoms) original_atom ON original_atom.value->>'self_ref'=requested.pointer;
 IF jsonb_array_length(atoms)<>jsonb_array_length(p_projection->'items') OR jsonb_array_length(ancestors)<>jsonb_array_length(p_projection->'ancestors') THEN
 RAISE EXCEPTION 'original source selected/ancestor atom inventory is absent or ambiguous'; END IF;
 pointers:=ARRAY(SELECT value->>'self_ref' FROM jsonb_array_elements(atoms));
 FOR original IN SELECT value FROM jsonb_array_elements(p_projection->'pieces') LOOP
 piece:='{}';
 FOREACH name IN ARRAY ARRAY['kind','start','end','item_ref','source_field','cell_index'] LOOP
 IF original ? name THEN piece:=piece||jsonb_build_object(name,original->name); END IF;
 END LOOP;
 IF piece->>'start' !~ '^(0|[1-9][0-9]*)$' OR piece->>'end' !~ '^[1-9][0-9]*$'
 OR (piece->>'start')::bigint<>previous OR (piece->>'end')::bigint<=previous OR (piece->>'end')::bigint>char_length(text_value)
 OR piece->>'kind' NOT IN ('native_text','synthetic_separator')
 OR (piece->>'kind'='native_text' AND (NOT coalesce(piece->>'item_ref'=ANY(pointers),false) OR nullif(piece->>'source_field','') IS NULL)) THEN
 RAISE EXCEPTION 'original source pieces do not partition the actual projection' USING ERRCODE='23514'; END IF;
 previous:=(piece->>'end')::bigint; pieces:=pieces||jsonb_build_array(piece);
 END LOOP;
 IF previous<>char_length(text_value) THEN RAISE EXCEPTION 'original source pieces omit actual projected text'; END IF;
 FOR original IN SELECT value FROM jsonb_array_elements(coalesce(p_projection->'health'->'formula_outcomes','[]')) LOOP
 IF NOT coalesce(original->>'pointer'=ANY(pointers),false) OR EXISTS(SELECT FROM jsonb_array_elements(recognition) old WHERE old->>'pointer'=original->>'pointer') THEN RAISE EXCEPTION 'original recognition differs from unique source atom inventory'; END IF;
 recognition:=recognition||jsonb_build_array(jsonb_build_object('pointer',original->'pointer','outcome',original->'outcome'));
 END LOOP;
 projection:=ops.ddo_digest(jsonb_build_object('text',text_value,'pieces',pieces,'items',atoms,'ancestors',ancestors,'recognition',recognition));
 coordinate:=jsonb_build_object('document',p_document,'document_subject','original-document:'||ops.ddo_digest(jsonb_build_object('document',p_document)),'section_pointer',p_section,'membership',p_membership,'projection',projection);
 FOR selector IN SELECT value FROM jsonb_array_elements(p_selectors) LOOP
 PERFORM ops.ddo_fields(selector,ARRAY['projection'],ARRAY['native_pointer','page','start','end']);
 IF selector->>'projection' IS DISTINCT FROM p_projection_digest
 OR (selector ? 'native_pointer' AND (jsonb_typeof(selector->'native_pointer') IS DISTINCT FROM 'string' OR NOT EXISTS(
 WITH RECURSIVE ancestry AS (
  SELECT value->>'self_ref' pointer,value->>'parent' parent,ARRAY[value->>'self_ref'] path FROM jsonb_array_elements(atoms)
  UNION ALL
  SELECT original_atom.value->>'self_ref',original_atom.value->>'parent',ancestry.path||(original_atom.value->>'self_ref')
  FROM ancestry JOIN jsonb_array_elements(all_atoms) original_atom ON original_atom.value->>'self_ref'=ancestry.parent
  WHERE NOT (original_atom.value->>'self_ref')=ANY(ancestry.path)
 ) SELECT FROM ancestry WHERE pointer=selector->>'native_pointer'
 ))) THEN
 RAISE EXCEPTION 'original source selector differs from actual source projection/atom'; END IF;
 FOREACH name IN ARRAY ARRAY['page','start','end'] LOOP
 IF selector ? name AND (jsonb_typeof(selector->name) IS DISTINCT FROM 'number' OR selector->>name !~ '^(0|[1-9][0-9]*)$') THEN RAISE EXCEPTION 'original source selector requires exact integer bounds'; END IF;
 END LOOP;
 IF (selector ? 'page' AND (selector->>'page')::bigint<1) OR coalesce((selector->>'start')::bigint,0)>coalesce((selector->>'end')::bigint,char_length(text_value)) OR coalesce((selector->>'end')::bigint,char_length(text_value))>char_length(text_value) THEN
 RAISE EXCEPTION 'original source selector exceeds original coordinate bounds'; END IF;
 selected:=selected||jsonb_build_array(jsonb_set(selector,'{projection}',to_jsonb(projection)));
 END LOOP;
 RETURN jsonb_build_object('source',coordinate,'text',text_value,'pieces',pieces,'items',atoms,'ancestors',ancestors,'recognition',recognition,'selectors',selected);
END $$;

-- A selected historical publication is interpreted against its sealed producing
-- episode, never the binding/release/runtime currently stored on its request.
CREATE OR REPLACE FUNCTION ops.ddo_pdf_producing_request(p_derivation text)
RETURNS ops.data_request LANGUAGE plpgsql STABLE STRICT SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE episode ops.data_derivation; intent ops.data_completion_intent; request ops.data_request;
 publication ops.data_publication_receipt;
 job ops.task; definition sem.data_operation_definition; profile text; captured record;
 binding jsonb; candidate jsonb;
BEGIN
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=p_derivation AND outcome='success';
 SELECT * INTO STRICT publication FROM ops.data_publication_receipt
 WHERE intent_id=episode.intent_id AND derivation_id=episode.id;
 SELECT original.* INTO STRICT intent FROM ops.data_completion_intent original
 WHERE original.id=publication.intent_id AND original.request_id=episode.request_id
 AND original.generation=episode.generation;
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=episode.request_id;
 SELECT * INTO STRICT job FROM ops.task WHERE id=episode.producer_task_id;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=episode.release_id AND operation_id=request.operation_id;
 IF (intent.producer_task_id,intent.producer_attempt,intent.runtime_id) IS DISTINCT FROM
 (episode.producer_task_id,episode.producer_attempt,episode.runtime_id)
 OR publication.publishing_task_id IS DISTINCT FROM episode.producer_task_id
 OR publication.publishing_attempt NOT BETWEEN intent.producer_attempt AND job.attempt
 OR (job.data_request_id,job.data_generation,job.release_id) IS DISTINCT FROM
 (episode.request_id,episode.generation,episode.release_id)
 OR job.attempt<intent.producer_attempt OR nullif(intent.producer_holder,'') IS NULL
 OR NOT EXISTS(SELECT FROM ops.data_request_generation generation WHERE generation.request_id=episode.request_id
 AND generation.generation=episode.generation AND generation.task_id=episode.producer_task_id)
 OR episode.recipe IS DISTINCT FROM definition.recipe OR request.recipe IS DISTINCT FROM episode.recipe
 OR intent.payload->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR ops.ddo_completion_state(definition,intent.payload->>'outcome') IS DISTINCT FROM episode.outcome THEN
 RAISE EXCEPTION 'PDF original producer differs from sealed episode/intent/task fences' USING ERRCODE='23514'; END IF;
 SELECT convert_from(runtime.manifest_bytes,'UTF8')::jsonb->>'execution_profile' INTO STRICT profile
 FROM sem.runtime_binding runtime WHERE runtime.release_id=episode.release_id AND runtime.runtime_id=episode.runtime_id;
 IF nullif(profile,'') IS NULL THEN
 RAISE EXCEPTION 'PDF original producer lacks its admitted execution profile' USING ERRCODE='23514'; END IF;
 FOR captured IN
 SELECT selected.selection,demand.selection->'execution_profile' execution_profile
 FROM ops.demand_use selected JOIN ops.data_demand demand ON demand.id=selected.demand_id
 JOIN ops.data_obligation obligation ON obligation.id=selected.obligation_id AND obligation.demand_id=demand.id
 WHERE selected.request_id=episode.request_id AND selected.generation=episode.generation
 AND selected.fate IN ('attached','fulfilled') AND (selected.derivation_id IS NULL OR selected.derivation_id=episode.id)
 AND demand.project_id=request.project_id AND demand.release_id=episode.release_id
 AND demand.selection->>'execution_profile'=profile
 AND obligation.operation_id=request.operation_id AND obligation.subject=request.subject
 AND obligation.original_source IS NOT DISTINCT FROM request.original_source
 AND obligation.analyzed_scope=request.analyzed_scope
 AND selected.selection->'inputs' IS NOT DISTINCT FROM intent.payload->'inputs'
 AND selected.selection->'support' IS NOT DISTINCT FROM intent.payload->'support'
 ORDER BY selected.created_at,selected.id
 LOOP
 candidate:=captured.selection||jsonb_build_object('execution_profile',captured.execution_profile);
 IF binding IS NULL THEN binding:=candidate;
 ELSIF (binding-'read_id') IS DISTINCT FROM (candidate-'read_id') THEN
 RAISE EXCEPTION 'PDF original producer binding is ambiguous in immutable admitted uses' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF binding IS NULL THEN
 RAISE EXCEPTION 'PDF original producer lacks its full immutable admitted binding' USING ERRCODE='23514'; END IF;
 request.release_id:=episode.release_id; request.runtime_id:=episode.runtime_id;
 request.recipe:=episode.recipe; request.generation:=episode.generation;
 request.live_task_id:=episode.producer_task_id; request.binding:=binding;
 RETURN request;
END $$;

CREATE OR REPLACE FUNCTION ops.read_selected_pdf_observations(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; demand ops.data_demand; boundary ops.data_demand_read; receipt jsonb; cut jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['project_id','demand_id','read_id','use_id','product_id','derivation_id']);
 SELECT * INTO STRICT demand FROM ops.data_demand WHERE id=p->>'demand_id' AND project_id=p->>'project_id';
 cut:=ops.ddo_require_selected_output(p->>'demand_id',p->>'read_id',p->>'use_id',p->>'product_id',p->>'derivation_id');
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p->>'read_id' AND demand_id=demand.id;
 receipt:=ops.ddo_pdf_observation_derivation_receipt(demand.project_id,p->>'product_id',p->>'derivation_id',NULL,boundary);
 RETURN jsonb_build_object('payload',jsonb_build_object('receipt',receipt,'cut',cut,
 'original_source',(SELECT original_source FROM kb.data_product WHERE id=p->>'product_id')));
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_original_document_view(p_reference jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE document kb.document; original bytea; body jsonb; coordinate jsonb;
BEGIN
 PERFORM ops.ddo_fields(p_reference,ARRAY['kind','project_id','document_key','content_hash','mime']);
 IF p_reference->>'kind' IS DISTINCT FROM 'original-document' THEN
 RAISE EXCEPTION 'original document reference discriminator differs'; END IF;
 SELECT * INTO STRICT document FROM kb.document d WHERE d.project_id=p_reference->>'project_id'
 AND d.key=p_reference->>'document_key' AND d.content_hash=p_reference->>'content_hash'
 AND d.mime=p_reference->>'mime';
 SELECT content INTO STRICT original FROM kb.source_artifact WHERE artifact_digest=document.content_hash;
 IF encode(sha256(original),'hex') IS DISTINCT FROM document.content_hash THEN
 RAISE EXCEPTION 'original document retained byte digest differs'; END IF;
 body:=jsonb_build_object('document',document.key,'content_hash',document.content_hash,'mime',document.mime);
 coordinate:=jsonb_build_object('document',document.key);
 RETURN jsonb_build_object('body',body,'meaning_body',data.ddo_normalize(data.record_json_meaning(body)),
 'subject_definition','original-document','subject','original-document:'||ops.ddo_digest(coordinate),
 'original_source',document.key,'analyzed_scope',jsonb_build_object('document',document.key,'scope','whole-document'),
 'evidence',jsonb_build_object('reference',p_reference,'document_id',document.id,
 'document_content_hash',document.content_hash,'source_uri',document.source_uri,'original_path',document.original_path));
END $$;


-- One sealed publication/body proof for execution bindings and selected public reads.
CREATE OR REPLACE FUNCTION ops.ddo_pdf_derivation_receipt(p_project text,p_product text,
 p_derivation text,p_source text DEFAULT NULL,p_read ops.data_demand_read DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE producer ops.data_request; derivation ops.data_derivation; intent ops.data_completion_intent;
 product kb.data_product; receipts jsonb; receipt jsonb; expected jsonb;
BEGIN
 IF NOT ops.ddo_support_valid(p_derivation,p_read) THEN
 RAISE EXCEPTION 'PDF derivation support is not admitted at selected read' USING ERRCODE='23514'; END IF;
 SELECT der.* INTO STRICT derivation FROM ops.data_derivation der
 JOIN ops.data_derivation_output output ON output.derivation_id=der.id
 WHERE der.id=p_derivation AND output.product_id=p_product AND output.member_id IS NULL;
 producer:=ops.ddo_pdf_producing_request(derivation.id);
 IF producer.project_id IS DISTINCT FROM p_project OR (p_source IS NOT NULL AND producer.original_source IS DISTINCT FROM p_source) THEN
 RAISE EXCEPTION 'PDF producer is outside exact qualified selected source' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_authorize_request(producer);
 IF NOT EXISTS(SELECT FROM sem.data_operation_definition definition
 WHERE definition.release_id=derivation.release_id AND definition.operation_id=producer.operation_id
 AND coalesce(ops.ddo_pdf_command_eligible(definition),false)) THEN
 RAISE EXCEPTION 'selected source derivation is not an exact approved native PDF command' USING ERRCODE='23514'; END IF;
 PERFORM ops.require_pdf_operation(producer.release_id,'read_native_source');
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=derivation.intent_id;
 SELECT * INTO STRICT product FROM kb.data_product WHERE id=p_product
 AND project_id=p_project AND original_source=producer.original_source;
 receipts:=intent.payload->'execution_evidence'->'pdf_receipts';
 IF jsonb_typeof(receipts) IS DISTINCT FROM 'array' OR jsonb_array_length(receipts)<>1 THEN
 RAISE EXCEPTION 'selected PDF capture lacks one retained sealed publication' USING ERRCODE='23514'; END IF;
 receipt:=receipts->0;
 expected:=ops.pdf_publication_projection(receipt,intent.producer_task_id,
 intent.producer_attempt,intent.producer_holder);
 IF data.ddo_json(product.canonical_body) IS DISTINCT FROM expected
 OR expected->>'document' IS DISTINCT FROM producer.original_source THEN
 RAISE EXCEPTION 'selected PDF capture body differs from actual sealed publication' USING ERRCODE='23514'; END IF;
 RETURN receipt;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_pdf_capture_source(p_request text,p_project text,
 p_product text,p_derivation text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE consumer ops.data_request;
BEGIN
 SELECT * INTO STRICT consumer FROM ops.data_request WHERE id=p_request AND project_id=p_project;
 RETURN ops.ddo_pdf_capture_source_for_request(consumer,p_project,p_product,p_derivation);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_pdf_capture_source_for_request(consumer ops.data_request,p_project text,
 p_product text,p_derivation text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF consumer.project_id IS DISTINCT FROM p_project THEN
 RAISE EXCEPTION 'PDF source consumer changes its qualified project' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_authorize_request(consumer);
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(consumer.binding->'inputs') selected
 WHERE CASE WHEN selected->>'product_id'=p_product AND selected->>'member_id' IS NULL
 THEN ops.ddo_single_input_support_episode(selected)=p_derivation ELSE false END)
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(consumer.binding->'support') selected
 WHERE selected->>'derivation_id'=p_derivation) THEN
 RAISE EXCEPTION 'PDF source is outside exact selected computational support' USING ERRCODE='23514'; END IF;
 RETURN ops.ddo_pdf_derivation_receipt(p_project,p_product,p_derivation,consumer.original_source);
END $$;

CREATE OR REPLACE FUNCTION ops.read_selected_pdf_source(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; demand ops.data_demand; boundary ops.data_demand_read; receipt jsonb; cut jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['project_id','demand_id','read_id','use_id','product_id','derivation_id']);
 SELECT * INTO STRICT demand FROM ops.data_demand WHERE id=p->>'demand_id' AND project_id=p->>'project_id';
 cut:=ops.ddo_require_selected_output(p->>'demand_id',p->>'read_id',p->>'use_id',p->>'product_id',p->>'derivation_id');
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p->>'read_id' AND demand_id=demand.id;
 receipt:=ops.ddo_pdf_derivation_receipt(demand.project_id,p->>'product_id',p->>'derivation_id',NULL,boundary);
 RETURN jsonb_build_object('payload',jsonb_build_object('receipt',receipt,'cut',cut,'original_source',(SELECT original_source FROM kb.data_product WHERE id=p->>'product_id')));
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_pdf_observation_derivation_receipt(p_project text,p_product text,
 p_derivation text,p_source text DEFAULT NULL,p_read ops.data_demand_read DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE producer ops.data_request; derivation ops.data_derivation; intent ops.data_completion_intent;
 product kb.data_product; receipts jsonb; receipt jsonb; expected jsonb;
BEGIN
 IF NOT ops.ddo_support_valid(p_derivation,p_read) THEN
 RAISE EXCEPTION 'observation derivation support is not admitted at selected read' USING ERRCODE='23514'; END IF;
 SELECT der.* INTO STRICT derivation FROM ops.data_derivation der
 JOIN ops.data_derivation_output output ON output.derivation_id=der.id
 WHERE der.id=p_derivation AND output.product_id=p_product AND output.member_id IS NULL;
 producer:=ops.ddo_pdf_producing_request(derivation.id);
 IF producer.project_id IS DISTINCT FROM p_project OR (p_source IS NOT NULL AND producer.original_source IS DISTINCT FROM p_source) THEN
 RAISE EXCEPTION 'observation producer is outside exact qualified selected source' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_authorize_request(producer);
 IF NOT EXISTS(SELECT FROM sem.data_operation_definition definition
 WHERE definition.release_id=derivation.release_id AND definition.operation_id=producer.operation_id
 AND coalesce(ops.ddo_pdf_command_eligible(definition),false)
 AND definition.support_contract->'effects'->0->>'name'='retain_pdf_observations') THEN
 RAISE EXCEPTION 'selected observation derivation is not an approved recognition command' USING ERRCODE='23514'; END IF;
 PERFORM ops.require_pdf_operation(producer.release_id,'read_pdf_product');
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=derivation.intent_id;
 SELECT * INTO STRICT product FROM kb.data_product WHERE id=p_product
 AND project_id=p_project AND original_source=producer.original_source;
 receipts:=intent.payload->'execution_evidence'->'pdf_observation_receipts';
 IF jsonb_typeof(receipts) IS DISTINCT FROM 'array' OR jsonb_array_length(receipts)<>1 THEN
 RAISE EXCEPTION 'selected observations lack one actual native retention receipt' USING ERRCODE='23514'; END IF;
 receipt:=receipts->0;
 IF receipt->>'runtime_id' IS DISTINCT FROM intent.runtime_id THEN
 RAISE EXCEPTION 'selected observation receipt changes its original producing runtime' USING ERRCODE='23514'; END IF;
 expected:=ops.pdf_observation_projection_for_request(receipt,intent.producer_task_id,intent.producer_attempt,intent.producer_holder,producer);
 IF data.ddo_json(product.canonical_body) IS DISTINCT FROM expected
 OR expected->>'document' IS DISTINCT FROM producer.original_source THEN
 RAISE EXCEPTION 'selected observation meaning differs from native retained evidence' USING ERRCODE='23514'; END IF;
 RETURN receipt;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_pdf_observation_source(p_request text,p_project text,
 p_product text,p_derivation text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE consumer ops.data_request; derivation ops.data_derivation; producer ops.data_request;
 receipt jsonb; capture jsonb; raw_capture jsonb; raw_product kb.data_product;
BEGIN
 SELECT * INTO STRICT consumer FROM ops.data_request WHERE id=p_request AND project_id=p_project;
 PERFORM ops.ddo_authorize_request(consumer);
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(consumer.binding->'inputs') selected
 WHERE CASE WHEN selected->>'role'='observations' AND selected->>'product_id'=p_product
 AND selected->>'member_id' IS NULL THEN ops.ddo_single_input_support_episode(selected)=p_derivation ELSE false END)
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(consumer.binding->'support') selected
 WHERE selected->>'derivation_id'=p_derivation) THEN
 RAISE EXCEPTION 'observations are outside exact selected computational support' USING ERRCODE='23514'; END IF;
 receipt:=ops.ddo_pdf_observation_derivation_receipt(p_project,p_product,p_derivation,consumer.original_source);
 SELECT * INTO STRICT derivation FROM ops.data_derivation WHERE id=p_derivation;
 producer:=ops.ddo_pdf_producing_request(derivation.id);
 SELECT value INTO STRICT raw_capture FROM jsonb_array_elements(producer.binding->'inputs') WHERE value->>'role'='capture';
 PERFORM ops.ddo_pdf_capture_source_for_request(producer,p_project,raw_capture->>'product_id',ops.ddo_single_input_support_episode(raw_capture));
 IF NOT EXISTS(SELECT FROM ops.data_derivation raw_derivation JOIN ops.data_request raw_request ON raw_request.id=raw_derivation.request_id
 JOIN sem.data_operation_definition raw_definition ON raw_definition.release_id=raw_derivation.release_id AND raw_definition.operation_id=raw_request.operation_id
 WHERE raw_derivation.id=ops.ddo_single_input_support_episode(raw_capture)
 AND raw_definition.support_contract->'effects'->0->>'name'='publish_pdf_capture') THEN
 RAISE EXCEPTION 'recognition input is not the exact qualified raw capture kind' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT raw_product FROM kb.data_product WHERE id=raw_capture->>'product_id';
 SELECT value INTO STRICT capture FROM jsonb_array_elements(consumer.binding->'inputs') WHERE value->>'role'='capture';
 PERFORM ops.ddo_pdf_capture_source(consumer.id,p_project,capture->>'product_id',ops.ddo_single_input_support_episode(capture));
 -- Canonical product identity includes the complete qualified raw kind meaning;
 -- two actual producing episodes may support that same value. Preserve both
 -- independently valid chains rather than equating their physical publication pins.
 IF NOT EXISTS(
 WITH RECURSIVE lineage(id) AS (
 SELECT ops.ddo_single_input_support_episode(capture)
 UNION SELECT support.support_derivation_id FROM ops.data_derivation_support support JOIN lineage parent ON support.derivation_id=parent.id
 ) SELECT FROM lineage JOIN ops.data_derivation_output output ON output.derivation_id=lineage.id
 JOIN kb.data_product candidate ON candidate.id=output.product_id
 WHERE output.member_id IS NULL AND candidate.id=raw_product.id
 AND candidate.kind_contract=raw_product.kind_contract
 AND candidate.project_id=p_project AND candidate.original_source=consumer.original_source
 AND ops.ddo_support_valid(lineage.id)) THEN
 RAISE EXCEPTION 'observation raw capture differs from qualified selected source lineage' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('receipt',receipt,'value',(SELECT data.ddo_json(product.canonical_body) FROM kb.data_product product WHERE product.id=p_product));
END $$;
