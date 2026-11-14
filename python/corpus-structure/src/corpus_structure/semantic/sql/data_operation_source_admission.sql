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
 wanted:=ARRAY(SELECT DISTINCT value#>>'{}' FROM jsonb_array_elements((view_.projection->'items')||(view_.projection->'ancestors')) ORDER BY value#>>'{}');
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
 'subject','original-document:'||ops.ddo_digest(coordinate),
 'original_source',document.key,'analyzed_scope',jsonb_build_object('document',document.key,'scope','whole-document'),
 'evidence',jsonb_build_object('reference',p_reference,'document_id',document.id,
 'document_content_hash',document.content_hash,'source_uri',document.source_uri,'original_path',document.original_path));
END $$;
