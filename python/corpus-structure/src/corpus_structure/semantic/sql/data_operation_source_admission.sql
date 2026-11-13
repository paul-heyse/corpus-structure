-- Only the exact persisted original-source read below grants custody. The pure
-- builder is shared semantic lowering; passing it caller JSON grants no admission.
CREATE OR REPLACE FUNCTION ops.ddo_native_source_body(p_document text,p_section text,p_membership text,p_projection jsonb,p_projection_digest text,p_items jsonb,p_selectors jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE atom jsonb; original jsonb; piece jsonb; selector jsonb; name text; pointers text[]:=ARRAY[]::text[];
 atoms jsonb:='[]'; pieces jsonb:='[]'; recognition jsonb:='[]'; selected jsonb:='[]'; coordinate jsonb; projection text; text_value text:=p_projection->>'text'; previous bigint:=0;
BEGIN
 IF nullif(p_document,'') IS NULL OR nullif(p_section,'') IS NULL OR p_membership NOT IN ('direct','descendants')
 OR jsonb_typeof(p_items) IS DISTINCT FROM 'array' OR jsonb_typeof(p_selectors) IS DISTINCT FROM 'array' OR jsonb_array_length(p_selectors)=0
 OR jsonb_typeof(p_projection->'text') IS DISTINCT FROM 'string' OR jsonb_typeof(p_projection->'pieces') IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'original source projection/request has invalid declared shape' USING ERRCODE='23514'; END IF;
 FOR original IN SELECT value FROM jsonb_array_elements(p_items) LOOP
 atom:='{}';
 FOREACH name IN ARRAY ARRAY['self_ref','label','text','orig'] LOOP
 IF original ? name THEN atom:=atom||jsonb_build_object(name,original->name); END IF;
 END LOOP;
 IF jsonb_typeof(original->'parent'->'$ref')='string' THEN atom:=atom||jsonb_build_object('parent',original->'parent'->'$ref'); END IF;
 atom:=atom||jsonb_build_object('prov',(SELECT coalesce(jsonb_agg(jsonb_build_object('page_no',value->'page_no') ORDER BY ordinal),'[]') FROM jsonb_array_elements(coalesce(original->'prov','[]')) WITH ORDINALITY p(value,ordinal) WHERE value ? 'page_no'));
 IF nullif(atom->>'self_ref','') IS NULL OR atom->>'self_ref'=ANY(pointers) THEN RAISE EXCEPTION 'original source repeats or lacks an atom address'; END IF;
 pointers:=array_append(pointers,atom->>'self_ref'); atoms:=atoms||jsonb_build_array(atom);
 END LOOP;
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
 projection:=ops.ddo_digest(jsonb_build_object('text',text_value,'pieces',pieces,'items',atoms,'recognition',recognition));
 coordinate:=jsonb_build_object('document',p_document,'section_pointer',p_section,'membership',p_membership,'projection',projection);
 FOR selector IN SELECT value FROM jsonb_array_elements(p_selectors) LOOP
 PERFORM ops.ddo_fields(selector,ARRAY['projection'],ARRAY['native_pointer','page','start','end']);
 IF selector->>'projection' IS DISTINCT FROM p_projection_digest
 OR (selector ? 'native_pointer' AND (jsonb_typeof(selector->'native_pointer') IS DISTINCT FROM 'string' OR NOT coalesce(selector->>'native_pointer'=ANY(pointers),false))) THEN
 RAISE EXCEPTION 'original source selector differs from actual source projection/atom'; END IF;
 FOREACH name IN ARRAY ARRAY['page','start','end'] LOOP
 IF selector ? name AND (jsonb_typeof(selector->name) IS DISTINCT FROM 'number' OR selector->>name !~ '^(0|[1-9][0-9]*)$') THEN RAISE EXCEPTION 'original source selector requires exact integer bounds'; END IF;
 END LOOP;
 IF (selector ? 'page' AND (selector->>'page')::bigint<1) OR coalesce((selector->>'start')::bigint,0)>coalesce((selector->>'end')::bigint,char_length(text_value)) OR coalesce((selector->>'end')::bigint,char_length(text_value))>char_length(text_value) THEN
 RAISE EXCEPTION 'original source selector exceeds original coordinate bounds'; END IF;
 selected:=selected||jsonb_build_array(jsonb_set(selector,'{projection}',to_jsonb(projection)));
 END LOOP;
 RETURN jsonb_build_object('source',coordinate,'text',text_value,'pieces',pieces,'items',atoms,'recognition',recognition,'selectors',selected);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_original_source_view(p_reference jsonb,p_selectors jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE view_ kb.source_view; document_ kb.document; placement record; wanted text[]; atoms jsonb; body jsonb;
BEGIN
 PERFORM ops.validate_structural_source(p_reference);
 SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(p_reference->>'source_view_id')::bigint;
 SELECT * INTO STRICT document_ FROM kb.document WHERE id=view_.document_id AND project_id=p_reference->>'project_id';
 PERFORM sem.require_execution_operation(p_reference->>'release_id','read_native_source');
 SELECT * INTO STRICT placement FROM ops.read_pdf_published_revision(view_.native_task_id,view_.native_product_key,view_.native_content_digest);
 IF (placement.task_id,placement.product_key,placement.logical_digest) IS DISTINCT FROM (view_.native_task_id,view_.native_product_key,view_.native_content_digest)
 OR view_.native_build_id IS DISTINCT FROM placement.build_id OR view_.native_revision_id IS DISTINCT FROM placement.build_id THEN RAISE EXCEPTION 'original source view escaped its published native placement'; END IF;
 wanted:=ARRAY(SELECT value#>>'{}' FROM jsonb_array_elements(view_.projection->'items'));
 SELECT coalesce(jsonb_agg(selected.native_json ORDER BY requested.ordinal),'[]') INTO atoms
 FROM unnest(wanted) WITH ORDINALITY requested(pointer,ordinal)
 JOIN ops.read_pdf_published_items(view_.native_task_id,view_.native_product_key,view_.native_content_digest,wanted) selected ON selected.pointer=requested.pointer
 WHERE selected.product_id=placement.build_id AND selected.revision_id=placement.build_id;
 IF jsonb_array_length(atoms)<>cardinality(wanted) THEN RAISE EXCEPTION 'original source native atom inventory is absent or ambiguous'; END IF;
 body:=ops.ddo_native_source_body(document_.key,view_.section_pointer,view_.membership,view_.projection,view_.projection_digest,atoms,p_selectors);
 RETURN jsonb_build_object('body',body,'meaning_body',data.ddo_normalize(data.record_json_meaning(body)),
 'subject','source-native:'||ops.ddo_digest(body->'source'),'original_source',document_.key,
 'analyzed_scope',jsonb_build_object('source',body->'source','selectors',body->'selectors'),
 'evidence',jsonb_build_object('reference',p_reference,'document_content_hash',document_.content_hash,'original_projection_digest',view_.projection_digest,
 'native_build_id',placement.build_id,'native_revision_id',placement.build_id,'producer_release_id',placement.release_id));
END $$;
