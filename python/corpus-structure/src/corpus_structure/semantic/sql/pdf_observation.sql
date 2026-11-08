-- Current recognition-observation publication; selected documents use sealed records.
CREATE OR REPLACE FUNCTION ops.index_pdf_visual_mapping(p_task bigint,p_key text,p_digest text)
RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $locator$
DECLARE retained bytea; mapped jsonb; image jsonb; submitted jsonb; total bigint;
BEGIN
 IF EXISTS(SELECT FROM ops.pdf_visual_index WHERE task_id=p_task AND product_key=p_key AND artifact_digest=p_digest)
 THEN RETURN; END IF;
 SELECT a.content,b.descriptor->'observation'->'image' INTO STRICT retained,image
 FROM ops.pdf_product_body b JOIN ops.pdf_product_artifact c USING(task_id,product_key)
 JOIN kb.source_artifact a USING(artifact_digest)
 WHERE b.task_id=p_task AND b.product_key=p_key AND c.artifact_digest=p_digest
  AND b.descriptor->'observation'->>'mapped_evidence_digest'=p_digest;
 IF octet_length(retained)>8388608 OR encode(sha256(retained),'hex')<>p_digest THEN
  RAISE EXCEPTION 'mapped visual bytes differ from retained custody' USING ERRCODE='23514'; END IF;
 mapped:=convert_from(retained,'UTF8')::jsonb;
 -- {visual_mapping_shape_guard}
 submitted:=image->'transform';
 IF jsonb_typeof(mapped) IS DISTINCT FROM 'object' OR mapped-'version'-'page_no'-'rows'<>'{}'
  OR mapped->>'version' IS DISTINCT FROM '1' OR mapped->'page_no' IS DISTINCT FROM image->'page_no'
  OR jsonb_typeof(mapped->'rows') IS DISTINCT FROM 'array' OR jsonb_array_length(mapped->'rows')>10000 THEN
  RAISE EXCEPTION 'mapped visual artifact differs from the submitted page or format' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(mapped->'rows') r
  WHERE jsonb_typeof(r) IS DISTINCT FROM 'object'
   OR jsonb_typeof(r->'occurrence_id') IS DISTINCT FROM 'string' OR r->>'occurrence_id'=''
   OR coalesce(r->>'kind','') NOT IN ('picture','caption','caption_candidate','picture_text','picture_description',
      'formula','mermaid','cell_text','table','cell_group')
   OR (r->>'kind' IN ('caption','caption_candidate','picture_text','picture_description','formula','mermaid','cell_text')
     AND jsonb_typeof(r->'text') IS DISTINCT FROM 'string')
   OR (r ? 'parser_attachment_occurrence_ids' AND
     (r->>'kind' NOT IN ('caption','caption_candidate') OR jsonb_typeof(r->'parser_attachment_occurrence_ids')<>'array'))
   OR (r ? 'associated_picture_occurrence_ids' AND
     (r->>'kind'<>'caption_candidate' OR jsonb_typeof(r->'associated_picture_occurrence_ids')<>'array'))
   OR (r->>'kind'='table' AND jsonb_typeof(r->'cells') IS DISTINCT FROM 'array')
   OR (r ? 'source_region' AND (submitted->>'status' IS DISTINCT FROM 'coarse'
     OR jsonb_typeof(r->'source_region') IS DISTINCT FROM 'object'
     OR NOT (r->'source_region' ?& ARRAY['left','top','right','bottom'])
     OR (r->'source_region'->>'left')::numeric < (submitted->>'crop_left')::numeric-1e-5
     OR (r->'source_region'->>'top')::numeric < (submitted->>'crop_top')::numeric-1e-5
     OR (r->'source_region'->>'right')::numeric > (submitted->>'crop_right')::numeric+1e-5
     OR (r->'source_region'->>'bottom')::numeric > (submitted->>'crop_bottom')::numeric+1e-5
     OR (r->'source_region'->>'left')::numeric >= (r->'source_region'->>'right')::numeric
     OR (r->'source_region'->>'top')::numeric >= (r->'source_region'->>'bottom')::numeric))) THEN
  RAISE EXCEPTION 'mapped visual row differs from its submitted frame or kind' USING ERRCODE='23514'; END IF;
 SELECT count(*)+coalesce(sum(CASE WHEN r->>'kind'='table' THEN jsonb_array_length(r->'cells') ELSE 0 END),0)
 INTO total FROM jsonb_array_elements(mapped->'rows') r;
 IF total>10000 THEN RAISE EXCEPTION 'mapped visual artifact exceeds the aggregate row bound' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(mapped->'rows') r
  CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN r->>'kind'='table' THEN r->'cells' ELSE '[]' END) c
  WHERE (c->>'start_row_offset_idx')::bigint >= (c->>'end_row_offset_idx')::bigint
   OR (c->>'start_col_offset_idx')::bigint >= (c->>'end_col_offset_idx')::bigint
   OR (c->>'end_row_offset_idx')::bigint > (r->>'num_rows')::bigint
   OR (c->>'end_col_offset_idx')::bigint > (r->>'num_cols')::bigint
   OR EXISTS(SELECT FROM (VALUES ('row_header_path','row_header'),('column_header_path','column_header')) axis(path,flag)
    WHERE (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(c->axis.path))
     OR EXISTS(SELECT FROM jsonb_array_elements_text(c->axis.path) idx
       WHERE idx::integer<0 OR r->'cells'->(idx::integer)->axis.flag IS DISTINCT FROM 'true'::jsonb))) THEN
  RAISE EXCEPTION 'mapped visual cell differs from its table spans or header paths' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.pdf_visual_index VALUES(p_task,p_key,p_digest,total) ON CONFLICT DO NOTHING;
 IF NOT FOUND THEN RETURN; END IF;
 INSERT INTO kb.pdf_visual_locator(task_id,product_key,artifact_digest,occurrence_id,ordinal,kind,parent_id,body)
 SELECT p_task,p_key,p_digest,r->>'occurrence_id',n,r->>'kind',r->>'parent_occurrence_id',r
 FROM jsonb_array_elements(mapped->'rows') WITH ORDINALITY item(r,n);
 IF EXISTS(SELECT FROM kb.pdf_visual_locator r LEFT JOIN kb.pdf_visual_locator parent
  ON (parent.task_id,parent.product_key,parent.artifact_digest,parent.occurrence_id)=
     (r.task_id,r.product_key,r.artifact_digest,r.parent_id)
  WHERE (r.task_id,r.product_key,r.artifact_digest)=(p_task,p_key,p_digest) AND r.parent_id IS NOT NULL
   AND (parent.ordinal IS NULL OR parent.ordinal>=r.ordinal)) THEN
  RAISE EXCEPTION 'mapped visual parent must precede its child' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_visual_locator r LEFT JOIN kb.pdf_visual_locator parent
  ON (parent.task_id,parent.product_key,parent.artifact_digest,parent.occurrence_id)=
     (r.task_id,r.product_key,r.artifact_digest,r.parent_id)
  WHERE (r.task_id,r.product_key,r.artifact_digest)=(p_task,p_key,p_digest)
   AND r.body->'source_region' ? 'enclosing_occurrence_id' AND (
    NOT coalesce(parent.body ? 'source_region',false)
    OR r.body->'source_region'->>'enclosing_occurrence_id' IS DISTINCT FROM
       coalesce(parent.body->'source_region'->>'enclosing_occurrence_id',parent.occurrence_id)
    OR EXISTS(SELECT FROM unnest(ARRAY['left','top','right','bottom']) field
       WHERE r.body->'source_region'->field IS DISTINCT FROM parent.body->'source_region'->field))) THEN
  RAISE EXCEPTION 'mapped visual region differs from its enclosing parent' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_visual_locator r CROSS JOIN LATERAL (VALUES
   ('parser_attachment',r.body->'parser_attachment_occurrence_ids'),
   ('caption_association',r.body->'associated_picture_occurrence_ids')) links(role,targets)
  WHERE (r.task_id,r.product_key,r.artifact_digest)=(p_task,p_key,p_digest) AND (
   (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(links.targets))
   OR EXISTS(SELECT FROM jsonb_array_elements_text(links.targets) link(id)
    LEFT JOIN kb.pdf_visual_locator target ON
     (target.task_id,target.product_key,target.artifact_digest,target.occurrence_id)=(p_task,p_key,p_digest,link.id)
    WHERE target.occurrence_id IS NULL OR target.kind NOT IN ('picture','table')
     OR (links.role='caption_association' AND
      (target.kind<>'picture' OR NOT target.body ? 'source_region' OR NOT r.body ? 'source_region'))))) THEN
  RAISE EXCEPTION 'mapped visual caption links differ from qualified targets' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.pdf_visual_cell(task_id,product_key,artifact_digest,occurrence_id,cell_index,group_id)
 SELECT p_task,p_key,p_digest,r->>'occurrence_id',n-1,c->>'content_occurrence_id'
 FROM jsonb_array_elements(mapped->'rows') r CROSS JOIN LATERAL
  jsonb_array_elements(CASE WHEN r->>'kind'='table' THEN r->'cells' ELSE '[]' END) WITH ORDINALITY item(c,n);
 IF EXISTS(SELECT FROM kb.pdf_visual_cell c LEFT JOIN kb.pdf_visual_locator g
  ON (g.task_id,g.product_key,g.artifact_digest,g.occurrence_id)=
     (c.task_id,c.product_key,c.artifact_digest,c.group_id)
  WHERE (c.task_id,c.product_key,c.artifact_digest)=(p_task,p_key,p_digest) AND c.group_id IS NOT NULL
   AND (g.kind IS DISTINCT FROM 'cell_group' OR g.parent_id IS DISTINCT FROM c.occurrence_id)) THEN
  RAISE EXCEPTION 'mapped visual cell differs from its table-owned group' USING ERRCODE='23514'; END IF;
END $locator$;
REVOKE ALL ON FUNCTION ops.index_pdf_visual_mapping(bigint,text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.publish_pdf_observation(p_task bigint,p_attempt bigint,p_holder text,p_contract text,p_payload bytea,p_artifacts bytea[]) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $observation$
DECLARE job ops.task; run ops.run; product jsonb:='{}'; digest text:=encode(sha256(p_payload),'hex');
 wire json; field_name text; field_value json; envelope_fields text[]:=ARRAY[]::text[];
 input_rows json; occurrence_rows json; relation_rows json; coverage_rows json; mapping_rows json;
 visual_scope jsonb; visual_params jsonb; visual_recipe jsonb;
 previous ops.pdf_product; input jsonb; occurrence jsonb; relation jsonb; endpoint jsonb; coverage jsonb; mapping_report jsonb; pin ops.pdf_product; idx bigint; eid bigint; original text;
 bind_original boolean;
BEGIN
 SELECT r.* INTO STRICT run FROM ops.run r JOIN ops.task t ON t.run_id=r.id WHERE t.id=p_task FOR SHARE OF r;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=run.id FOR UPDATE;
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'stale recognition observation attempt' USING ERRCODE='P0004'; END IF;
 wire:=convert_from(p_payload,'UTF8')::json;
 IF json_typeof(wire) IS DISTINCT FROM 'object' OR wire->>'kind' IS DISTINCT FROM 'recognition_observation' THEN RAISE EXCEPTION 'parsing record must be an object: PdfIntegratedProduct' USING ERRCODE='23514'; END IF;
 FOR field_name,field_value IN SELECT key,value FROM json_each(wire) LOOP
  envelope_fields:=array_append(envelope_fields,field_name);
  CASE field_name
   WHEN 'inputs' THEN input_rows:=field_value;
   WHEN 'occurrences' THEN occurrence_rows:=field_value;
   WHEN 'relations' THEN relation_rows:=field_value;
   WHEN 'coverage' THEN coverage_rows:=field_value;
   WHEN 'mapping_reports' THEN mapping_rows:=field_value;
   WHEN 'content' THEN RAISE EXCEPTION 'document content is not an observation' USING ERRCODE='23514';
   ELSE product:=product||jsonb_build_object(field_name,field_value::jsonb);
  END CASE;
 END LOOP;
 -- {integrated_shape_guard}
 IF product->>'kind' IS DISTINCT FROM 'recognition_observation' OR product->>'product_key'=''  THEN
  RAISE EXCEPTION 'recognition observation kind/key/health differs' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/schema/pdf_products' AND encode(sha256(content),'hex')=p_contract) THEN RAISE EXCEPTION 'PDF contract is not archived by task release' USING ERRCODE='23514'; END IF;
 SELECT artifact_digest INTO original FROM ops.source_build WHERE task_id=p_task AND release_id=run.release_id;
 bind_original:=NOT FOUND;
 IF bind_original THEN
  original:=product->>'artifact_digest';
  IF coalesce(product->'observation'->>'pass_role','') NOT IN ('chandra_page','chandra_crop')
     OR NOT EXISTS(SELECT FROM kb.document d JOIN kb.source_artifact a ON a.artifact_digest=d.content_hash
       WHERE job.unit_type='document' AND d.id=job.unit_id AND d.project_id=run.project_id
         AND d.content_hash=original) THEN
   RAISE EXCEPTION 'PDF original is outside retained visual task custody' USING ERRCODE='23514'; END IF;
 END IF;
 IF product->>'artifact_digest' IS DISTINCT FROM original THEN RAISE EXCEPTION 'PDF original custody differs' USING ERRCODE='23514'; END IF;
 SELECT * INTO previous FROM ops.pdf_product WHERE task_id=p_task AND product_key=product->>'product_key';
 IF FOUND THEN
  IF previous.content_digest<>digest OR previous.contract_digest<>p_contract OR previous.kind<>product->>'kind' OR NOT EXISTS(SELECT FROM ops.pdf_product_body WHERE task_id=p_task AND product_key=product->>'product_key' AND payload=p_payload) THEN RAISE EXCEPTION 'immutable PDF bundle replay differs' USING ERRCODE='23514'; END IF;
  IF EXISTS((SELECT encode(sha256(supplied.content),'hex') FROM unnest(p_artifacts) supplied(content) EXCEPT SELECT a.artifact_digest FROM ops.pdf_product_artifact a WHERE a.task_id=p_task AND a.product_key=product->>'product_key') UNION ALL (SELECT a.artifact_digest FROM ops.pdf_product_artifact a WHERE a.task_id=p_task AND a.product_key=product->>'product_key' EXCEPT SELECT encode(sha256(supplied.content),'hex') FROM unnest(p_artifacts) supplied(content))) OR EXISTS(SELECT FROM unnest(p_artifacts) supplied(content) WHERE NOT EXISTS(SELECT FROM kb.source_artifact a WHERE a.artifact_digest=encode(sha256(supplied.content),'hex') AND a.content=supplied.content)) THEN RAISE EXCEPTION 'PDF replay artifacts differ' USING ERRCODE='23514'; END IF;
  RETURN digest;
 END IF;
 PERFORM sem.require_execution_operation(run.release_id,'publish_pdf_observation');
 IF run.sealed OR run.status NOT IN ('created','running') OR job.status<>'running'
 OR job.lease_until IS NULL OR job.lease_until<=clock_timestamp() THEN
  RAISE EXCEPTION 'run/attempt no longer accepts recognition observations' USING ERRCODE='P0004';
 END IF;
 -- Resolve EVERY input before inserting the new identity. Immutable edges to extant bodies
 -- make forward references, self references and cycles impossible without a path table.
 FOR input,idx IN SELECT value::jsonb,n-1 FROM json_array_elements(input_rows) WITH ORDINALITY i(value,n) LOOP
  -- {inputs_shape_guard}
  SELECT * INTO STRICT pin FROM ops.pdf_product WHERE task_id=(input->>'task_id')::bigint AND product_key=input->>'product_key' AND content_digest=input->>'content_digest';
  IF pin.task_id=p_task AND pin.product_key=product->>'product_key' THEN RAISE EXCEPTION 'self PDF input' USING ERRCODE='23514'; END IF;
  IF pin.artifact_digest<>original OR NOT EXISTS(SELECT FROM ops.task t JOIN ops.run r ON r.id=t.run_id WHERE t.id=pin.task_id AND r.project_id=run.project_id) THEN RAISE EXCEPTION 'PDF input outside original/project custody' USING ERRCODE='23514'; END IF;
  IF (input->>'role'='recognition' AND pin.kind<>'recognition_observation') OR (input->>'role'='structural' AND pin.kind NOT IN ('native','integrated')) THEN RAISE EXCEPTION 'PDF input role/kind differs' USING ERRCODE='23514'; END IF;
  IF (pin.kind IN ('native','integrated') AND NOT EXISTS(
    SELECT FROM ops.pdf_published_revision b
    JOIN ops.pdf_build_validation v ON v.build_id=b.build_id AND v.frozen_digest=b.frozen_digest
      AND v.logical_digest=b.logical_digest AND v.native_callbacks
    JOIN sem.input s ON s.release_id=b.release_id AND s.input_kind='dependency'
      AND s.input_name='execution/implementation/pdf/docling-validation.schema.json'
      AND s.content_digest=b.schema_digest
    WHERE b.task_id=pin.task_id AND b.product_key=pin.product_key
      AND b.release_id=pin.release_id AND b.kind=pin.kind AND b.source_digest=original
      AND b.logical_digest=pin.content_digest AND v.contract_digest=pin.contract_digest
   )) OR (pin.kind='recognition_observation' AND NOT EXISTS(
    SELECT FROM ops.pdf_product_body b JOIN sem.input s ON s.release_id=pin.release_id
      AND s.input_kind='dependency' AND s.input_name='execution/schema/pdf_products'
      AND encode(sha256(s.content),'hex')=pin.contract_digest
    WHERE b.task_id=pin.task_id AND b.product_key=pin.product_key
      AND encode(sha256(b.payload),'hex')=pin.content_digest
   )) THEN RAISE EXCEPTION 'PDF input has no admitted immutable body' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (SELECT count(*) FROM json_array_elements(input_rows))<>(SELECT count(DISTINCT (value->>'role',value->>'task_id',value->>'product_key')) FROM json_array_elements(input_rows)) THEN RAISE EXCEPTION 'duplicate PDF input role/pin' USING ERRCODE='23514'; END IF;
  IF NOT product ? 'observation' OR 'content'=ANY(envelope_fields) THEN RAISE EXCEPTION 'observation body differs' USING ERRCODE='23514'; END IF;
  IF (product->'observation'->>'pass_role' IN ('chandra_page','chandra_crop')) IS DISTINCT FROM
   (product->'observation'->'binding'->>'provider'='datalab-chandra-2') THEN
   RAISE EXCEPTION 'Chandra observation role differs from its provider' USING ERRCODE='23514';
  END IF;
  IF product->'observation'->>'pass_role' IN ('chandra_page','chandra_crop') THEN
   visual_scope:=run.options->'visual_request';
   IF run.options ? 'visual_group' THEN
    SELECT config.params INTO STRICT visual_params
     FROM ops.method_config config JOIN ops.method method ON method.id=config.method_id
     WHERE config.id=job.method_config_id AND method.name='native.source_request'
       AND method.version='5';
    visual_scope:=jsonb_strip_nulls(visual_params->'selection');
    SELECT convert_from(content,'UTF8')::jsonb INTO visual_recipe
     FROM unnest(p_artifacts) content WHERE encode(sha256(content),'hex')=product->>'recipe_digest';
    IF run.options ? 'visual_request'
       OR run.options->'visual_group'->>'version' IS DISTINCT FROM 'chandra-visual-group-v1'
       OR jsonb_typeof(run.options->'visual_group'->'selections') IS DISTINCT FROM 'array'
       OR jsonb_array_length(run.options->'visual_group'->'selections') NOT BETWEEN 1 AND 4
       OR (SELECT count(*) FROM jsonb_array_elements(run.options->'visual_group'->'selections') s
           WHERE s=visual_scope)<>1
       OR (run.options ? 'visual_nomination_run_id' AND NOT EXISTS(
        SELECT FROM ops.run nomination
        WHERE nomination.id=(run.options->>'visual_nomination_run_id')::bigint
         AND nomination.project_id=run.project_id AND nomination.release_id=run.release_id
         AND nomination.input_realization_id=run.input_realization_id AND nomination.sealed
         AND nomination.options->'visual_nomination'->>'version'='visual-nomination-v2'
         AND nomination.options->'visual_nomination'->'selections' @> jsonb_build_array(visual_scope)
       ))
       OR EXISTS(SELECT FROM jsonb_array_elements(run.options->'visual_group'->'selections') s
          WHERE s->'source' IS DISTINCT FROM visual_scope->'source')
       OR (visual_scope ? 'pointer')<>(visual_scope ? 'region_index')
       OR (visual_scope ? 'rotation' AND
           (NOT visual_scope ? 'pointer' OR visual_scope->>'rotation' NOT IN ('90','180','270')))
       OR visual_recipe->'selection' IS DISTINCT FROM visual_scope
       OR visual_params->>'recipe_digest' IS DISTINCT FROM product->>'recipe_digest'
       OR job.unit_key IS DISTINCT FROM 'chandra-'||(visual_params->>'step')||':'||(visual_params->>'recipe_digest')
       OR product->>'product_key' IS DISTINCT FROM job.unit_key
       OR job.unit_type IS DISTINCT FROM 'document'
       OR (visual_params->>'step'='mapping') IS DISTINCT FROM
          EXISTS (SELECT FROM json_array_elements(input_rows) i WHERE i->>'role'='recognition')
       OR (visual_params->>'step'='inference' AND
          (visual_recipe->'transform' IS DISTINCT FROM product->'observation'->'image'->'transform'
           OR visual_recipe->'submitted_png_digest' IS DISTINCT FROM product->'observation'->'image'->'artifact_digest'))
    THEN RAISE EXCEPTION 'Chandra observation differs from its grouped task and recipe' USING ERRCODE='23514'; END IF;
   END IF;
   IF (SELECT count(*) FROM json_array_elements(input_rows) i WHERE i->>'role'='structural')<>1 OR NOT EXISTS(
    SELECT FROM json_array_elements(input_rows) i JOIN ops.pdf_product parent
      ON parent.task_id=(i->>'task_id')::bigint AND parent.product_key=i->>'product_key'
      AND parent.content_digest=i->>'content_digest'
    JOIN ops.task source_task ON source_task.id=parent.task_id
    WHERE i->>'role'='structural' AND parent.kind='integrated'
      AND (i::jsonb - 'role')=((visual_scope->'source') - 'run_id')
      AND source_task.run_id=(visual_scope->'source'->>'run_id')::bigint
      AND source_task.unit_type='document' AND source_task.unit_id=job.unit_id AND EXISTS(
        SELECT FROM ops.read_pdf_published_revision(parent.task_id,parent.product_key,parent.content_digest) published
        WHERE published.source_digest=original AND published.kind='integrated'
        AND EXISTS(
         SELECT FROM kb.pdf_record_native page
         WHERE page.product_id=published.build_id AND page.revision_id=published.build_id
           AND page.family='page' AND page.scalars_json->'page_no'=visual_scope->'page_no'
        )
        AND (NOT visual_scope ? 'pointer' OR EXISTS(
         SELECT FROM kb.pdf_record_region region
         WHERE region.product_id=published.build_id AND region.revision_id=published.build_id
           AND region.pointer=visual_scope->>'pointer'
           AND region.region_index=(visual_scope->>'region_index')::bigint
           AND region.page_no=(visual_scope->>'page_no')::bigint
        ))
      )
      AND product->'observation'->'image'->'page_no'=visual_scope->'page_no'
      AND (product->'observation'->>'pass_role'='chandra_crop')=(visual_scope->>'pointer' IS NOT NULL)
   ) THEN RAISE EXCEPTION 'Chandra observation differs from requested source' USING ERRCODE='23514'; END IF;
   IF (product->'observation' ? 'mapped_evidence_digest'
      OR EXISTS (SELECT FROM json_array_elements(input_rows) i WHERE i->>'role'='recognition'))
      AND ((SELECT count(*) FROM json_array_elements(input_rows) i WHERE i->>'role'='recognition')<>1 OR NOT EXISTS(
    SELECT FROM json_array_elements(input_rows) i JOIN ops.pdf_product_body raw
      ON raw.task_id=(i->>'task_id')::bigint AND raw.product_key=i->>'product_key'
    JOIN ops.task raw_task ON raw_task.id=raw.task_id
    JOIN ops.run raw_run ON raw_run.id=raw_task.run_id
    JOIN ops.method_config raw_config ON raw_config.id=raw_task.method_config_id
    WHERE i->>'role'='recognition'
      AND COALESCE(raw_run.options->'visual_request',
       CASE WHEN raw_run.options->'visual_group'->>'version'='chandra-visual-group-v1'
         AND raw_run.options->'visual_group'->'selections' @>
           jsonb_build_array(jsonb_strip_nulls(raw_config.params->'selection'))
       THEN jsonb_strip_nulls(raw_config.params->'selection') END)=visual_scope
      AND (NOT run.options ? 'visual_group' OR (
       raw_task.status IN ('done','empty') AND raw_task.unit_key=raw.product_key
       AND starts_with(raw.product_key,'chandra-inference:')
       AND visual_recipe->'raw'=(i::jsonb-'role') || jsonb_build_object('run_id',raw_run.id)
       AND job.trigger->'visual_raw'=visual_recipe->'raw'
      ))
      AND raw.descriptor->'observation'=((product->'observation')-'mapped_evidence_digest')
      AND EXISTS (SELECT FROM ops.pdf_product_input upstream
       WHERE upstream.task_id=raw.task_id AND upstream.product_key=raw.product_key
         AND upstream.role='structural'
         AND upstream.input_task_id=(visual_scope->'source'->>'task_id')::bigint
         AND upstream.input_product_key=visual_scope->'source'->>'product_key'
         AND upstream.input_content_digest=visual_scope->'source'->>'content_digest')
   )) THEN RAISE EXCEPTION 'mapped Chandra observation differs from its raw input' USING ERRCODE='23514'; END IF;
  ELSIF product->'observation' ? 'mapped_evidence_digest' THEN
   RAISE EXCEPTION 'mapped visual evidence requires a Chandra observation' USING ERRCODE='23514';
  END IF;
  IF product->'observation'->'image'->>'precision' NOT IN ('unknown','coarse') OR (product->'observation'->'image'->'transform'->>'status') NOT IN ('unknown','coarse') OR jsonb_typeof((product->'observation'->'binding'->>'decoding_json')::jsonb) IS DISTINCT FROM 'object' OR (product->'observation' ? 'usage_json' AND jsonb_typeof((product->'observation'->>'usage_json')::jsonb) IS DISTINCT FROM 'object') THEN RAISE EXCEPTION 'unadmitted provider transform/precision/settings' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM unnest(p_artifacts) supplied(content) WHERE encode(sha256(supplied.content),'hex')=product->'observation'->'image'->>'artifact_digest' AND octet_length(supplied.content)>=24 AND substring(supplied.content FROM 1 FOR 8)=decode('89504e470d0a1a0a','hex') AND get_byte(supplied.content,16)::bigint*16777216+get_byte(supplied.content,17)::bigint*65536+get_byte(supplied.content,18)::bigint*256+get_byte(supplied.content,19)::bigint=(product->'observation'->'image'->>'width')::bigint AND get_byte(supplied.content,20)::bigint*16777216+get_byte(supplied.content,21)::bigint*65536+get_byte(supplied.content,22)::bigint*256+get_byte(supplied.content,23)::bigint=(product->'observation'->'image'->>'height')::bigint) THEN RAISE EXCEPTION 'submitted PNG dimensions/bytes differ' USING ERRCODE='23514'; END IF;
  IF (product->'observation'->>'outcome' IN ('succeeded','partial') AND NOT product->'observation' ? 'raw_response_digest') OR (product->'observation'->>'outcome' IN ('failed','unknown','unsupported') AND COALESCE(product->'observation'->>'diagnostic','')='') OR product->'health'->>'execution_outcome' IS DISTINCT FROM product->'observation'->>'outcome' OR (product->'observation'->>'usage_availability'='available') IS DISTINCT FROM (product->'observation' ? 'usage_json') THEN RAISE EXCEPTION 'observation response/diagnostic/usage availability differs' USING ERRCODE='23514'; END IF;
  IF product->'observation'->'image'->'transform'->>'status'='unknown' AND product->'observation'->'image'->'transform' ?| ARRAY['page_width','page_height','page_rotation','crop_left','crop_top','crop_right','crop_bottom','affine'] THEN RAISE EXCEPTION 'unknown transform carries fabricated parameters' USING ERRCODE='23514'; END IF;
  IF product->'observation'->'image'->'transform'->>'status'='coarse' AND (NOT product->'observation'->'image'->'transform' ?& ARRAY['page_width','page_height','page_rotation','crop_left','crop_top','crop_right','crop_bottom','affine'] OR jsonb_array_length(product->'observation'->'image'->'transform'->'affine')<>6 OR EXISTS(SELECT FROM jsonb_array_elements(product->'observation'->'image'->'transform'->'affine') WHERE jsonb_typeof(value)<>'number') OR (product->'observation'->'image'->'transform'->>'page_rotation')::bigint NOT IN (0,90,180,270) OR NOT (0<=(product->'observation'->'image'->'transform'->>'crop_left')::numeric AND (product->'observation'->'image'->'transform'->>'crop_left')::numeric<(product->'observation'->'image'->'transform'->>'crop_right')::numeric AND (product->'observation'->'image'->'transform'->>'crop_right')::numeric<=(product->'observation'->'image'->'transform'->>'page_width')::numeric AND 0<=(product->'observation'->'image'->'transform'->>'crop_top')::numeric AND (product->'observation'->'image'->'transform'->>'crop_top')::numeric<(product->'observation'->'image'->'transform'->>'crop_bottom')::numeric AND (product->'observation'->'image'->'transform'->>'crop_bottom')::numeric<=(product->'observation'->'image'->'transform'->>'page_height')::numeric)) THEN RAISE EXCEPTION 'coarse transform requires complete page/crop/rotation witness' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM unnest(ARRAY[product->'observation'->'image'->>'artifact_digest',product->'observation'->>'raw_response_digest',product->'observation'->>'mapped_evidence_digest']) d WHERE d IS NOT NULL AND NOT EXISTS(SELECT FROM unnest(p_artifacts) content WHERE encode(sha256(content),'hex')=d)) THEN RAISE EXCEPTION 'observation artifact bytes are missing' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM unnest(p_artifacts) content WHERE encode(sha256(content),'hex')=product->>'recipe_digest') THEN RAISE EXCEPTION 'PDF recipe bytes are missing' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.source_artifact(artifact_digest,content) SELECT encode(sha256(content),'hex'),content FROM unnest(p_artifacts) content ON CONFLICT DO NOTHING;
 IF bind_original THEN
  INSERT INTO ops.source_build(task_id,release_id,artifact_digest,recipe_digest)
  VALUES(p_task,run.release_id,original,product->>'recipe_digest');
 END IF;
 INSERT INTO ops.pdf_product(task_id,product_key,content_digest,kind,artifact_digest,release_id,contract_digest) VALUES(p_task,product->>'product_key',digest,product->>'kind',original,run.release_id,p_contract);
 INSERT INTO ops.pdf_product_artifact(task_id,product_key,artifact_digest) SELECT p_task,product->>'product_key',encode(sha256(supplied.content),'hex') FROM unnest(p_artifacts) supplied(content) ON CONFLICT DO NOTHING;
 INSERT INTO ops.pdf_product_body(task_id,product_key,payload,recipe_digest,descriptor) VALUES(p_task,product->>'product_key',p_payload,product->>'recipe_digest',product);
 IF product->'observation' ? 'mapped_evidence_digest' THEN
  PERFORM ops.index_pdf_visual_mapping(p_task,product->>'product_key',product->'observation'->>'mapped_evidence_digest');
 END IF;
 INSERT INTO ops.pdf_product_input(task_id,product_key,input_index,role,input_task_id,input_product_key,input_content_digest)
 SELECT p_task,product->>'product_key',n-1,value->>'role',(value->>'task_id')::bigint,value->>'product_key',value->>'content_digest' FROM json_array_elements(input_rows) WITH ORDINALITY i(value,n);
 FOR occurrence IN SELECT value::jsonb FROM json_array_elements(occurrence_rows) LOOP
  -- {occurrences_shape_guard}
  IF occurrence->>'occurrence_id'='' OR ((occurrence ? 'start')<>(occurrence ? 'end')) OR (occurrence ? 'start' AND ((occurrence->>'start')::bigint>(occurrence->>'end')::bigint OR occurrence->>'address_space' NOT IN ('native_item','recognized_text','selected_item','raw_response') OR occurrence->>'precision' IN ('unknown','coarse','block','inherited') OR (occurrence ? 'text' AND (occurrence->>'end')::bigint>char_length(occurrence->>'text')))) THEN RAISE EXCEPTION 'unqualified PDF occurrence address/range' USING ERRCODE='23514'; END IF;
  IF occurrence ? 'region' AND ((occurrence->'region'->>'left')::numeric>(occurrence->'region'->>'right')::numeric OR (occurrence->'region'->>'origin'='top_left' AND (occurrence->'region'->>'top')::numeric>(occurrence->'region'->>'bottom')::numeric) OR (occurrence->'region'->>'origin'='bottom_left' AND (occurrence->'region'->>'top')::numeric<(occurrence->'region'->>'bottom')::numeric)) THEN RAISE EXCEPTION 'region coordinate origin/bounds differ' USING ERRCODE='23514'; END IF;
  IF product->>'kind'='recognition_observation' AND occurrence ? 'region' AND (occurrence->'region'->>'precision' NOT IN ('unknown','coarse','block') OR occurrence->'region'->>'address_space' NOT IN ('submitted_pixels','normalized_raw') OR (occurrence->'region'->>'address_space'='submitted_pixels' AND (occurrence->'region'->>'origin'<>'top_left' OR (occurrence->'region'->>'left')::numeric<0 OR (occurrence->'region'->>'right')::numeric>(product->'observation'->'image'->>'width')::numeric OR (occurrence->'region'->>'top')::numeric<0 OR (occurrence->'region'->>'bottom')::numeric>(product->'observation'->'image'->>'height')::numeric)) OR (occurrence->'region'->>'address_space'='normalized_raw' AND EXISTS(SELECT FROM jsonb_each(occurrence->'region') entry WHERE entry.key IN ('left','top','right','bottom') AND ((entry.value::text)::numeric<0 OR (entry.value::text)::numeric>1)))) THEN RAISE EXCEPTION 'provider region precision/frame/bounds differs' USING ERRCODE='23514'; END IF;
  IF product->>'kind'='recognition_observation' AND occurrence ? 'page_no' AND occurrence->>'page_no' IS DISTINCT FROM product->'observation'->'image'->>'page_no' THEN RAISE EXCEPTION 'observation page differs from submitted image' USING ERRCODE='23514'; END IF;
  IF product->>'kind'='recognition_observation' AND occurrence->>'precision' NOT IN ('unknown','coarse','block') THEN RAISE EXCEPTION 'I10/I11 provider precision is unadmitted' USING ERRCODE='23514'; END IF;
  INSERT INTO kb.pdf_occurrence(task_id,product_key,occurrence_id,kind,address_space,precision,body,pointer) VALUES(p_task,product->>'product_key',occurrence->>'occurrence_id',occurrence->>'kind',occurrence->>'address_space',occurrence->>'precision',occurrence,occurrence->>'pointer');
 END LOOP;
 FOR relation IN SELECT value::jsonb FROM json_array_elements(relation_rows) LOOP
  -- {relations_shape_guard}
  IF relation->>'relation_id'='' OR relation->>'policy'='' OR relation->>'evidence'='' OR (relation->>'kind'='correspondence' AND relation->>'outcome' NOT IN ('matched','ambiguous','unmatched','unresolved')) OR (relation->>'kind'='decision' AND relation->>'outcome' NOT IN ('selected','added','replaced','retained_alternative','rejected','unresolved')) THEN RAISE EXCEPTION 'PDF relation kind/outcome/policy differs' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM jsonb_array_elements(relation->'endpoints') WHERE value ? 'input_index') OR (relation->>'kind'='correspondence' AND relation->>'outcome' IN ('matched','ambiguous') AND (SELECT count(DISTINCT (value->>'input_index',value->>'occurrence_id')) FROM jsonb_array_elements(relation->'endpoints'))<2) OR (relation->>'kind'='decision' AND relation->>'outcome' IN ('selected','added','replaced') AND NOT EXISTS(SELECT FROM jsonb_array_elements(relation->'endpoints') WHERE value->>'role'='output')) OR (relation->>'kind'='decision' AND relation->>'outcome'='rejected' AND EXISTS(SELECT FROM jsonb_array_elements(relation->'endpoints') WHERE value->>'role'='output')) THEN RAISE EXCEPTION 'PDF relation endpoint set differs' USING ERRCODE='23514'; END IF;
  IF (SELECT count(*) FROM jsonb_array_elements(relation->'endpoints'))<>(SELECT count(DISTINCT (value->>'input_index',value->>'occurrence_id',value->>'role')) FROM jsonb_array_elements(relation->'endpoints')) THEN RAISE EXCEPTION 'duplicate PDF relation endpoint' USING ERRCODE='23514'; END IF;
  INSERT INTO kb.pdf_relation(task_id,product_key,relation_id,kind,body) VALUES(p_task,product->>'product_key',relation->>'relation_id',relation->>'kind',relation-'endpoints');
  FOR endpoint,eid IN SELECT value,n-1 FROM jsonb_array_elements(relation->'endpoints') WITH ORDINALITY e(value,n) LOOP
   IF endpoint ? 'input_index' THEN
    SELECT p.* INTO pin FROM ops.pdf_product_input i JOIN ops.pdf_product p
      ON (p.task_id,p.product_key,p.content_digest)=(i.input_task_id,i.input_product_key,i.input_content_digest)
      WHERE i.task_id=p_task AND i.product_key=product->>'product_key' AND i.input_index=(endpoint->>'input_index')::bigint;
    IF NOT FOUND OR endpoint->>'role'='output' THEN RAISE EXCEPTION 'PDF endpoint input index/role differs' USING ERRCODE='23514'; END IF;
   ELSE
    IF endpoint->>'role'<>'output' THEN RAISE EXCEPTION 'local PDF endpoint must be output' USING ERRCODE='23514'; END IF;
    SELECT * INTO STRICT pin FROM ops.pdf_product WHERE task_id=p_task AND product_key=product->>'product_key';
   END IF;
   INSERT INTO kb.pdf_relation_endpoint(task_id,product_key,relation_id,endpoint_index,role,target_task_id,target_product_key,target_content_digest,occurrence_id) VALUES(p_task,product->>'product_key',relation->>'relation_id',eid,endpoint->>'role',pin.task_id,pin.product_key,pin.content_digest,endpoint->>'occurrence_id');
  END LOOP;
 END LOOP;
 IF EXISTS(SELECT FROM (SELECT value::jsonb AS r FROM json_array_elements(COALESCE(mapping_rows,'[]'::json))) reports LEFT JOIN ops.pdf_product_input i ON i.task_id=p_task AND i.product_key=product->>'product_key' AND i.input_index=(r->>'input_index')::bigint WHERE i.role IS DISTINCT FROM 'recognition' OR (r->>'outcome'<>'mapped' AND COALESCE(r->>'reason','')='') OR (r ? 'occurrence_id' AND NOT EXISTS(SELECT FROM kb.pdf_occurrence o WHERE o.task_id=i.input_task_id AND o.product_key=i.input_product_key AND o.occurrence_id=r->>'occurrence_id'))) THEN RAISE EXCEPTION 'mapping disposition differs from recognition custody' USING ERRCODE='23514'; END IF;
 FOR mapping_report,idx IN SELECT value::jsonb,n-1 FROM json_array_elements(COALESCE(mapping_rows,'[]'::json)) WITH ORDINALITY rows(value,n) LOOP
  -- {mapping_reports_shape_guard}
  INSERT INTO kb.pdf_mapping_report(task_id,product_key,report_index,input_index,body)
  VALUES(p_task,product->>'product_key',idx,(mapping_report->>'input_index')::bigint,mapping_report);
 END LOOP;
 IF json_array_length(coverage_rows)=0 THEN RAISE EXCEPTION 'PDF coverage is mandatory' USING ERRCODE='23514'; END IF;
 FOR coverage IN SELECT value::jsonb FROM json_array_elements(coverage_rows) LOOP
  -- {coverage_shape_guard}
  IF coverage->>'coverage_id'='' OR coverage->>'scope'='' OR coverage->>'family'='' OR coverage->>'discovery_policy'='' OR coverage->>'detail'='' OR (product->>'kind'='recognition_observation' AND coverage->>'outcome'='complete') THEN RAISE EXCEPTION 'PDF coverage scope/policy/outcome differs' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(coverage->'supports') support LEFT JOIN ops.pdf_product_input i ON i.task_id=p_task AND i.product_key=product->>'product_key' AND i.input_index=(support->>'input_index')::bigint LEFT JOIN kb.pdf_product_coverage c ON c.task_id=i.input_task_id AND c.product_key=i.input_product_key AND c.coverage_id=support->>'coverage_id' WHERE c.coverage_id IS NULL OR c.body->>'scope' IS DISTINCT FROM coverage->>'scope' OR c.body->>'family' IS DISTINCT FROM coverage->>'family') OR (coverage->>'outcome'='complete' AND NOT EXISTS(SELECT FROM jsonb_array_elements(coverage->'supports') support JOIN ops.pdf_product_input i ON i.task_id=p_task AND i.product_key=product->>'product_key' AND i.input_index=(support->>'input_index')::bigint JOIN kb.pdf_product_coverage c ON c.task_id=i.input_task_id AND c.product_key=i.input_product_key AND c.coverage_id=support->>'coverage_id' WHERE c.body->>'scope'=coverage->>'scope' AND c.body->>'family'=coverage->>'family' AND c.body->>'outcome'='complete')) THEN RAISE EXCEPTION 'complete coverage lacks qualified scope/family input attribution' USING ERRCODE='23514'; END IF;
  INSERT INTO kb.pdf_product_coverage(task_id,product_key,coverage_id,body) VALUES(p_task,product->>'product_key',coverage->>'coverage_id',coverage);
 END LOOP;
 RETURN digest;
END $observation$;
REVOKE ALL ON FUNCTION ops.publish_pdf_observation(bigint,bigint,text,text,bytea,bytea[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.publish_pdf_observation(bigint,bigint,text,text,bytea,bytea[]) TO corpus_sem_writer;
