-- Current declared recognition observation publication over exact PDF support.
CREATE OR REPLACE FUNCTION ops.pdf_observation_meaning(p_payload bytea) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $meaning$
DECLARE value jsonb:=convert_from(p_payload,'UTF8')::jsonb;
 observed jsonb:=value->'observation'; binding jsonb:=observed->'binding'; decoding jsonb;
 observation jsonb; coverage jsonb;
BEGIN
 -- {observation_meaning_projection}
END $meaning$;

CREATE OR REPLACE FUNCTION ops.pdf_recognition_profile(p_release text,p_definition sem.data_operation_definition)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $profile$
DECLARE asset jsonb; profile jsonb;
BEGIN
 IF p_definition.release_id IS DISTINCT FROM p_release THEN
 RAISE EXCEPTION 'recognition policy belongs to another release' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT asset FROM jsonb_array_elements(p_definition.support_contract->'assets')
 WHERE value->>'reference'='frozen-native-recognition-policy'
 AND value->>'contract'='pdf-recognition/policy-v1'
 AND value->>'role'='recognition-models-and-recovery-policy';
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT profile FROM sem.input
 WHERE release_id=p_release AND input_kind='dependency' AND input_name=asset->>'contract'
 AND content_digest=asset->>'content_digest' AND encode(sha256(content),'hex')=content_digest;
 PERFORM ops.ddo_fields(profile,ARRAY['version','base_recipe_digest','recipes','recovery_policy','source_recovery']);
 IF profile->>'version' IS DISTINCT FROM 'pdf-recognition-profile-1' THEN
 RAISE EXCEPTION 'unsupported recognition policy' USING ERRCODE='23514'; END IF;
 RETURN profile;
END $profile$;

CREATE OR REPLACE FUNCTION ops.pdf_observation_projection_for_request(p_receipt jsonb,p_task bigint,p_attempt bigint,p_holder text,p_request ops.data_request)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $projection$
DECLARE job ops.task; request ops.data_request; definition sem.data_operation_definition;
 context record; profile jsonb; selected jsonb; capture jsonb; page jsonb; request_ref jsonb;
 report jsonb; result jsonb; request_row jsonb; payload jsonb; raw_payload bytea;
 product ops.pdf_product; origin jsonb; ordinal bigint; page_position bigint;
 requested jsonb; available jsonb; page_groups jsonb:='[]'; previous_page bigint; previous_outcome text;
 page_requests jsonb; pages jsonb:='[]'; report_content bytea; body_content bytea;
 recovery_count integer:=0;
BEGIN
 PERFORM ops.ddo_fields(p_receipt,ARRAY['version','request_id','generation','task_id','attempt','holder','runtime_id','source_digest','recipe_digest','pages']);
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT context FROM ops.pdf_task_context(p_task);
 request:=p_request;
 IF (request.id,request.generation,request.release_id) IS DISTINCT FROM
 (context.request_id,context.generation,context.release_id)
 OR request.project_id IS DISTINCT FROM context.project_id
 OR request.original_source IS DISTINCT FROM (SELECT document.key FROM kb.document document WHERE document.id=context.document_id) THEN
 RAISE EXCEPTION 'observation projection changes its actual task request basis' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_authorize_request(request);
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=context.release_id AND operation_id=request.operation_id;
 IF NOT coalesce(ops.ddo_pdf_command_eligible(definition),false)
 OR request.recipe IS DISTINCT FROM definition.recipe
 OR definition.support_contract->'effects'->0->>'name' IS DISTINCT FROM 'retain_pdf_observations'
 OR p_receipt->>'version' IS DISTINCT FROM 'pdf-observation-execution-1'
 OR p_receipt->>'request_id' IS DISTINCT FROM context.request_id
 OR (p_receipt->>'generation')::bigint IS DISTINCT FROM context.generation
 OR (p_receipt->>'task_id')::bigint IS DISTINCT FROM p_task
 OR (p_receipt->>'attempt')::bigint IS DISTINCT FROM p_attempt
 OR p_attempt IS NULL OR p_attempt<1 OR nullif(p_holder,'') IS NULL
 OR p_receipt->>'holder' IS DISTINCT FROM p_holder
 OR p_receipt->>'source_digest' IS DISTINCT FROM context.source_digest
 OR NOT EXISTS(SELECT FROM sem.runtime_binding runtime WHERE runtime.release_id=context.release_id
 AND runtime.runtime_id=p_receipt->>'runtime_id') THEN
 RAISE EXCEPTION 'observation receipt differs from actual native recognition owner' USING ERRCODE='23514'; END IF;
 profile:=ops.pdf_recognition_profile(context.release_id,definition);
 IF p_receipt->>'recipe_digest' IS DISTINCT FROM profile->>'base_recipe_digest' THEN
 RAISE EXCEPTION 'observation receipt changes configured recognition recipe' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT selected FROM jsonb_array_elements(request.binding->'inputs') WHERE value->>'role'='capture';
 capture:=ops.ddo_pdf_capture_source_for_request(request,request.project_id,selected->>'product_id',ops.ddo_single_input_support_episode(selected))->'publication';
 requested:=data.ddo_json(data.ddo_field(request.binding->'parameters','parameters'))->'pages';
 IF requested IS NULL OR jsonb_typeof(requested)<>'array' THEN
 RAISE EXCEPTION 'observation request lacks its exact physical page selection' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_agg((native.scalars_json->>'page_no')::bigint ORDER BY (native.scalars_json->>'page_no')::bigint),'[]')
 INTO available FROM ops.pdf_record_document document JOIN kb.pdf_record_membership member
 ON member.product_id=document.product_id AND member.revision_id=document.revision_id
 AND member.parent_id=document.root_id AND member.field_name='pages'
 JOIN kb.pdf_record_native native ON native.product_id=member.product_id AND native.revision_id=member.revision_id AND native.record_id=member.record_id
 WHERE document.product_id=capture->>'build_id' AND document.revision_id=capture->>'build_id';
 IF requested='[]'::jsonb THEN requested:=available;
 ELSIF EXISTS(SELECT FROM jsonb_array_elements(requested) page_number WHERE NOT available @> jsonb_build_array(page_number)) THEN
 RAISE EXCEPTION 'recognition page is outside the actual selected native inventory' USING ERRCODE='23514';
 END IF;
 IF jsonb_array_length(p_receipt->'pages')=0 THEN
 RAISE EXCEPTION 'observation receipt has no inspected page reports' USING ERRCODE='23514'; END IF;
 FOR page,page_position IN SELECT value,n FROM jsonb_array_elements(p_receipt->'pages') WITH ORDINALITY item(value,n) LOOP
 PERFORM ops.ddo_fields(page,ARRAY['page_no','recipe_digest','report_digest','adapter_reused','observations']);
 IF jsonb_typeof(page->'adapter_reused') IS DISTINCT FROM 'boolean'
 OR NOT requested @> jsonb_build_array((page->>'page_no')::bigint)
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(profile->'recipes') recipe WHERE recipe->>'digest'=page->>'recipe_digest') THEN
 RAISE EXCEPTION 'observation page/recipe differs from exact requested source' USING ERRCODE='23514'; END IF;
 IF previous_page IS DISTINCT FROM (page->>'page_no')::bigint THEN
 IF page_groups @> jsonb_build_array((page->>'page_no')::bigint)
 OR page->>'recipe_digest' IS DISTINCT FROM profile->>'base_recipe_digest' THEN
 RAISE EXCEPTION 'observation page ordering/base recipe differs' USING ERRCODE='23514'; END IF;
 page_groups:=page_groups||jsonb_build_array((page->>'page_no')::bigint); recovery_count:=0;
 ELSE
 recovery_count:=recovery_count+1;
 IF recovery_count<>1 OR profile->'recovery_policy'='null'::jsonb
 OR previous_outcome='succeeded' OR page->>'recipe_digest'=profile->>'base_recipe_digest' THEN
 RAISE EXCEPTION 'observation recovery differs from its finite admitted policy' USING ERRCODE='23514'; END IF;
 END IF;
 SELECT content INTO STRICT report_content FROM kb.source_artifact
 WHERE artifact_digest=page->>'report_digest' AND encode(sha256(content),'hex')=artifact_digest;
 report:=convert_from(report_content,'UTF8')::jsonb;
 -- {observation_report_shape}
 IF report->>'page_no' IS DISTINCT FROM page->>'page_no' OR report->>'recipe_digest' IS DISTINCT FROM page->>'recipe_digest'
 OR jsonb_array_length(report->'requests') IS DISTINCT FROM jsonb_array_length(page->'observations') THEN
 RAISE EXCEPTION 'observation report differs from exact retained request inventory' USING ERRCODE='23514'; END IF;
 SELECT content INTO STRICT body_content FROM kb.source_artifact WHERE artifact_digest=report->>'result_digest' AND encode(sha256(content),'hex')=artifact_digest;
 result:=convert_from(body_content,'UTF8')::jsonb;
 IF result->>'outcome' IS NULL OR result->>'outcome' NOT IN ('succeeded','partial','failed','unknown','unsupported') THEN
 RAISE EXCEPTION 'observation report lacks its actual reported page outcome' USING ERRCODE='23514'; END IF;
 page_requests:='[]';
 FOR request_ref,ordinal IN SELECT value,n-1 FROM jsonb_array_elements(page->'observations') WITH ORDINALITY item(value,n) LOOP
 PERFORM ops.ddo_fields(request_ref,ARRAY['ordinal','task_id','product_key','content_digest','publication_context']);
 SELECT * INTO STRICT product FROM ops.pdf_product WHERE task_id=(request_ref->>'task_id')::bigint
 AND product_key=request_ref->>'product_key' AND content_digest=request_ref->>'content_digest';
 origin:=product.publication_context;
 IF product.kind<>'recognition_observation' OR product.task_id<>p_task
 OR product.artifact_digest IS DISTINCT FROM context.source_digest
 OR origin IS NULL OR origin IS DISTINCT FROM request_ref->'publication_context'
 OR origin->>'version' IS DISTINCT FROM 'pdf-observation-publication-1'
 OR origin->>'request_id' IS DISTINCT FROM context.request_id OR (origin->>'generation')::bigint IS DISTINCT FROM context.generation
 OR (origin->>'task_id')::bigint IS DISTINCT FROM p_task OR origin->>'release_id' IS DISTINCT FROM context.release_id
 OR origin->>'source_digest' IS DISTINCT FROM context.source_digest
 OR (origin->>'attempt')::bigint NOT BETWEEN 1 AND p_attempt
 OR ((origin->>'attempt')::bigint=p_attempt AND (origin->>'holder' IS DISTINCT FROM p_holder OR origin->>'runtime_id' IS DISTINCT FROM p_receipt->>'runtime_id'))
 OR (request_ref->>'ordinal')::bigint IS DISTINCT FROM ordinal
 OR (report->'requests'->(ordinal::integer)->>'ordinal')::bigint IS DISTINCT FROM ordinal
 OR NOT EXISTS(SELECT FROM sem.runtime_binding runtime WHERE runtime.release_id=origin->>'release_id' AND runtime.runtime_id=origin->>'runtime_id')
 OR EXISTS(SELECT FROM ops.data_revocation revoked WHERE revoked.scope=ops.ddo_scope(request.project_id,request.original_source)
 AND revoked.selector_kind='runtime' AND revoked.selector=origin->>'runtime_id') THEN
 RAISE EXCEPTION 'observation publication/adoption loses original native attribution' USING ERRCODE='23514'; END IF;
 SELECT body.payload INTO STRICT raw_payload FROM ops.pdf_product_body body WHERE body.task_id=product.task_id AND body.product_key=product.product_key;
 payload:=convert_from(raw_payload,'UTF8')::jsonb;
 SELECT artifact.content INTO STRICT body_content FROM kb.source_artifact artifact
 WHERE artifact.artifact_digest=report->'requests'->(ordinal::integer)->>'request_digest' AND encode(sha256(artifact.content),'hex')=artifact.artifact_digest;
 request_row:=convert_from(body_content,'UTF8')::jsonb;
 IF encode(sha256(raw_payload),'hex') IS DISTINCT FROM product.content_digest
 OR payload->>'recipe_digest' IS DISTINCT FROM page->>'recipe_digest'
 OR payload->'observation'->'image'->>'page_no' IS DISTINCT FROM page->>'page_no'
 OR request_row->>'ordinal' IS DISTINCT FROM request_ref->>'ordinal'
 OR request_row->>'submitted_digest' IS DISTINCT FROM payload->'observation'->'image'->>'artifact_digest'
 OR request_row->>'outcome' IS DISTINCT FROM payload->'observation'->>'outcome'
 OR (CASE request_row->>'stage' WHEN 'fullpage' THEN 'A' WHEN 'detection' THEN 'B' WHEN 'crop' THEN 'C' END) IS DISTINCT FROM payload->'observation'->>'pass_role'
 OR (request_row ? 'raw_response') IS DISTINCT FROM (payload->'observation' ? 'raw_response_digest')
 OR (request_row ? 'raw_response' AND request_row->>'raw_digest' IS DISTINCT FROM payload->'observation'->>'raw_response_digest')
 OR EXISTS(SELECT FROM unnest(ARRAY[page->>'report_digest',report->>'result_digest',report->'requests'->(ordinal::integer)->>'request_digest']) digest
 WHERE NOT EXISTS(SELECT FROM ops.pdf_product_artifact owned WHERE owned.task_id=product.task_id AND owned.product_key=product.product_key AND owned.artifact_digest=digest)) THEN
 RAISE EXCEPTION 'observation report/request bytes differ from native retained evidence' USING ERRCODE='23514'; END IF;
 page_requests:=page_requests||jsonb_build_array(jsonb_build_object('ordinal',ordinal,
 'meaning_digest',ops.ddo_digest(data.ddo_json_meaning(ops.pdf_observation_meaning(raw_payload))),
 'pass_role',payload->'observation'->'pass_role','outcome',payload->'observation'->'outcome'));
 END LOOP;
 IF result->>'outcome'='succeeded' AND (jsonb_array_length(page_requests)<2
 OR page_requests->0->>'pass_role'<>'A' OR page_requests->1->>'pass_role'<>'B'
 OR EXISTS(SELECT FROM jsonb_array_elements(page_requests) reading WHERE reading->>'outcome'<>'succeeded')) THEN
 RAISE EXCEPTION 'successful page report differs from actual retained pass outcomes' USING ERRCODE='23514'; END IF;
 pages:=pages||jsonb_build_array(jsonb_build_object('page_no',page->'page_no','recipe_digest',page->'recipe_digest','outcome',result->'outcome','observations',page_requests));
 previous_page:=(page->>'page_no')::bigint; previous_outcome:=result->>'outcome';
 END LOOP;
 IF page_groups IS DISTINCT FROM requested THEN
 RAISE EXCEPTION 'observation reports do not cover the exact requested page inventory' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('document',request.original_source,'source_digest',context.source_digest,'recipe_digest',p_receipt->'recipe_digest','pages',pages);
END $projection$;

CREATE OR REPLACE FUNCTION ops.pdf_observation_projection(p_receipt jsonb,p_task bigint,p_attempt bigint,p_holder text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $projection$
DECLARE job ops.task; request ops.data_request;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=job.data_request_id;
 IF request.live_task_id IS DISTINCT FROM p_task OR request.generation IS DISTINCT FROM job.data_generation
 OR request.release_id IS DISTINCT FROM job.release_id THEN
 RAISE EXCEPTION 'active observation projection requires its current task request basis' USING ERRCODE='23514'; END IF;
 RETURN ops.pdf_observation_projection_for_request(p_receipt,p_task,p_attempt,p_holder,request);
END $projection$;

CREATE OR REPLACE FUNCTION ops.publish_pdf_observation(p_task bigint,p_attempt bigint,p_holder text,p_runtime text,p_contract text,p_payload bytea,p_artifacts bytea[]) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $observation$
DECLARE job ops.task; context record; definition sem.data_operation_definition; native_request ops.data_request; selected jsonb; publication jsonb; product jsonb:='{}'; digest text:=encode(sha256(p_payload),'hex');
 wire json; field_name text; field_value json; envelope_fields text[]:=ARRAY[]::text[];
 input_rows json; occurrence_rows json; relation_rows json; coverage_rows json; mapping_rows json;
 previous ops.pdf_product; input jsonb; occurrence jsonb; relation jsonb; endpoint jsonb; coverage jsonb; mapping_report jsonb; pin ops.pdf_product; idx bigint; eid bigint; original text; recognition_profile jsonb;
BEGIN
 -- Read identity without locking the task before the native support/demand/request
 -- locks. Exact immutable replay below needs only its original attempt fence.
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT context FROM ops.pdf_task_context(p_task);
  SELECT d.* INTO STRICT definition FROM sem.data_operation_definition d
  JOIN ops.data_request request ON request.release_id=d.release_id AND request.operation_id=d.operation_id
  WHERE request.id=context.request_id;
  IF NOT coalesce(ops.ddo_pdf_command_eligible(definition),false)
   OR definition.support_contract->'effects'->0->>'name' IS DISTINCT FROM 'retain_pdf_observations' THEN
   RAISE EXCEPTION 'native observations require the exact approved PDF recognition effect' USING ERRCODE='23514';
  END IF;
 IF job.attempt IS DISTINCT FROM p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'stale recognition observation attempt' USING ERRCODE='P0004'; END IF;
 PERFORM sem.require_runtime_binding(context.release_id,p_runtime);
 IF NOT EXISTS(SELECT FROM sem.runtime_binding runtime WHERE runtime.release_id=context.release_id
 AND runtime.runtime_id=p_runtime AND convert_from(runtime.manifest_bytes,'UTF8')::jsonb->>'execution_profile'=
 (SELECT request.binding->>'execution_profile' FROM ops.data_request request WHERE request.id=context.request_id))
 OR EXISTS(SELECT FROM ops.data_revocation revoked WHERE revoked.scope=ops.ddo_scope(context.project_id,
 (SELECT request.original_source FROM ops.data_request request WHERE request.id=context.request_id))
 AND revoked.selector_kind='runtime' AND revoked.selector=p_runtime) THEN
 RAISE EXCEPTION 'observation publisher runtime differs from admitted request profile/trust' USING ERRCODE='23514'; END IF;
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
 recognition_profile:=ops.pdf_recognition_profile(context.release_id,definition);
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(recognition_profile->'recipes') recipe
 WHERE recipe->>'digest'=product->>'recipe_digest'
 AND recipe->>'weights_digest'=product->'observation'->'binding'->>'weights_digest'
 AND recipe->>'tokenizer_digest'=product->'observation'->'binding'->>'tokenizer_digest') THEN
 RAISE EXCEPTION 'recognition recipe/model differs from exact admitted profile' USING ERRCODE='23514'; END IF;
 IF encode(sha256(ops.pdf_contract_input(context.release_id,'schema/pdf_products')),'hex') IS DISTINCT FROM p_contract THEN RAISE EXCEPTION 'PDF contract is not archived by task release' USING ERRCODE='23514'; END IF;
 IF product->'observation'->>'pass_role' IN ('chandra_page','chandra_crop') THEN
  RAISE EXCEPTION 'native integration cannot publish legacy Chandra observations' USING ERRCODE='23514'; END IF;
 SELECT artifact_digest INTO original FROM ops.source_build WHERE task_id=p_task AND release_id=context.release_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'owned PDF original was not retained' USING ERRCODE='23514'; END IF;
 IF product->>'artifact_digest' IS DISTINCT FROM original THEN RAISE EXCEPTION 'PDF original custody differs' USING ERRCODE='23514'; END IF;
 SELECT * INTO previous FROM ops.pdf_product WHERE task_id=p_task AND product_key=product->>'product_key';
 IF NOT FOUND THEN
  -- Acquire support -> demand -> request -> task before publication.
  SELECT * INTO STRICT context FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
  SELECT * INTO STRICT job FROM ops.task WHERE id=p_task;
  -- A concurrent exact publisher may have committed while ownership was acquired.
  SELECT * INTO previous FROM ops.pdf_product WHERE task_id=p_task AND product_key=product->>'product_key';
 ELSE
  SELECT * INTO STRICT job FROM ops.task WHERE id=p_task FOR UPDATE;
 END IF;
 IF job.attempt IS DISTINCT FROM p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN
  RAISE EXCEPTION 'stale recognition observation attempt' USING ERRCODE='P0004'; END IF;
 IF previous.task_id IS NOT NULL THEN
  IF previous.content_digest<>digest OR previous.contract_digest<>p_contract OR previous.kind<>product->>'kind' OR NOT EXISTS(SELECT FROM ops.pdf_product_body WHERE task_id=p_task AND product_key=product->>'product_key' AND payload=p_payload) THEN RAISE EXCEPTION 'immutable PDF bundle replay differs' USING ERRCODE='23514'; END IF;
  IF EXISTS((SELECT encode(sha256(supplied.content),'hex') FROM unnest(p_artifacts) supplied(content) EXCEPT SELECT a.artifact_digest FROM ops.pdf_product_artifact a WHERE a.task_id=p_task AND a.product_key=product->>'product_key') UNION ALL (SELECT a.artifact_digest FROM ops.pdf_product_artifact a WHERE a.task_id=p_task AND a.product_key=product->>'product_key' EXCEPT SELECT encode(sha256(supplied.content),'hex') FROM unnest(p_artifacts) supplied(content))) OR EXISTS(SELECT FROM unnest(p_artifacts) supplied(content) WHERE NOT EXISTS(SELECT FROM kb.source_artifact a WHERE a.artifact_digest=encode(sha256(supplied.content),'hex') AND a.content=supplied.content)) THEN RAISE EXCEPTION 'PDF replay artifacts differ' USING ERRCODE='23514'; END IF;
  RETURN digest;
 END IF;
 PERFORM ops.require_pdf_operation(context.release_id,'publish_pdf_observation');
  IF original IS DISTINCT FROM context.source_digest THEN
   RAISE EXCEPTION 'native recognition original differs from the owned request source' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT native_request FROM ops.data_request WHERE id=context.request_id;
  SELECT value INTO STRICT selected FROM jsonb_array_elements(native_request.binding->'inputs')
  WHERE value->>'role'='capture';
  IF selected->>'member_id' IS NOT NULL OR ops.ddo_single_input_support_episode(selected) IS NULL THEN
   RAISE EXCEPTION 'native recognition requires one whole selected PDF support' USING ERRCODE='23514'; END IF;
  publication:=ops.ddo_pdf_capture_source(native_request.id,context.project_id,
   selected->>'product_id',ops.ddo_single_input_support_episode(selected))->'publication';
  IF (SELECT count(*) FROM json_array_elements(input_rows) i WHERE i->>'role'='structural')<>1
   OR NOT EXISTS(SELECT FROM json_array_elements(input_rows) i WHERE i->>'role'='structural'
    AND i->>'task_id'=publication->>'task_id' AND i->>'product_key'=publication->>'product_key'
    AND i->>'content_digest'=publication->>'logical_digest') THEN
   RAISE EXCEPTION 'native recognition structural input differs from exact selected PDF publication'
   USING ERRCODE='23514'; END IF;
  -- Cross-task recognition may only reuse immutable predecessor observations of
  -- this exact selected publication. Same-task observations support successive passes.
  IF EXISTS(
   WITH RECURSIVE lineage(task_id,product_key,content_digest) AS (
    SELECT (publication->>'task_id')::bigint,publication->>'product_key',publication->>'logical_digest'
    UNION SELECT edge.input_task_id,edge.input_product_key,edge.input_content_digest
    FROM ops.pdf_product_input edge JOIN lineage parent
    ON edge.task_id=parent.task_id AND edge.product_key=parent.product_key
   )
   SELECT FROM json_array_elements(input_rows) i WHERE i->>'role'='recognition'
   AND (i->>'task_id')::bigint<>p_task AND NOT EXISTS(SELECT FROM lineage predecessor
    WHERE predecessor.task_id=(i->>'task_id')::bigint AND predecessor.product_key=i->>'product_key'
    AND predecessor.content_digest=i->>'content_digest')
  ) THEN RAISE EXCEPTION 'native recognition input is outside exact selected publication lineage'
   USING ERRCODE='23514'; END IF;
 -- Resolve EVERY input before inserting the new identity. Immutable edges to extant bodies
 -- make forward references, self references and cycles impossible without a path table.
 FOR input,idx IN SELECT value::jsonb,n-1 FROM json_array_elements(input_rows) WITH ORDINALITY i(value,n) LOOP
  -- {inputs_shape_guard}
  SELECT * INTO pin FROM ops.pdf_product WHERE task_id=(input->>'task_id')::bigint AND product_key=input->>'product_key' AND content_digest=input->>'content_digest';
  IF NOT FOUND THEN RAISE EXCEPTION 'PDF input pin has no exact admitted product' USING ERRCODE='23514'; END IF;
  IF pin.task_id=p_task AND pin.product_key=product->>'product_key' THEN RAISE EXCEPTION 'self PDF input' USING ERRCODE='23514'; END IF;
  IF pin.artifact_digest<>original OR NOT EXISTS(SELECT FROM ops.pdf_task_context(pin.task_id) input_context WHERE input_context.project_id=context.project_id AND input_context.source_digest=original) THEN RAISE EXCEPTION 'PDF input outside original/project custody' USING ERRCODE='23514'; END IF;
  IF (input->>'role'='recognition' AND pin.kind<>'recognition_observation') OR (input->>'role'='structural' AND pin.kind NOT IN ('native','integrated')) THEN RAISE EXCEPTION 'PDF input role/kind differs' USING ERRCODE='23514'; END IF;
  IF (pin.kind IN ('native','integrated') AND NOT EXISTS(
    SELECT FROM ops.pdf_published_revision b
    JOIN ops.pdf_build_validation v ON v.build_id=b.build_id AND v.frozen_digest=b.frozen_digest
      AND v.logical_digest=b.logical_digest AND v.native_callbacks
    WHERE b.task_id=pin.task_id AND b.product_key=pin.product_key
      AND b.release_id=pin.release_id AND b.kind=pin.kind AND b.source_digest=original
      AND b.logical_digest=pin.content_digest AND v.contract_digest=pin.contract_digest
      AND encode(sha256(ops.pdf_contract_input(b.release_id,'implementation/pdf/docling-validation.schema.json')),'hex')=b.schema_digest
   )) OR (pin.kind='recognition_observation' AND NOT EXISTS(
    SELECT FROM ops.pdf_product_body b
    WHERE b.task_id=pin.task_id AND b.product_key=pin.product_key
      AND encode(sha256(b.payload),'hex')=pin.content_digest
      AND encode(sha256(ops.pdf_contract_input(pin.release_id,'schema/pdf_products')),'hex')=pin.contract_digest
   )) THEN RAISE EXCEPTION 'PDF input has no admitted immutable body' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (SELECT count(*) FROM json_array_elements(input_rows))<>(SELECT count(DISTINCT (value->>'role',value->>'task_id',value->>'product_key')) FROM json_array_elements(input_rows)) THEN RAISE EXCEPTION 'duplicate PDF input role/pin' USING ERRCODE='23514'; END IF;
  IF NOT product ? 'observation' OR 'content'=ANY(envelope_fields) THEN RAISE EXCEPTION 'observation body differs' USING ERRCODE='23514'; END IF;
  IF (product->'observation'->>'pass_role' IN ('chandra_page','chandra_crop')) IS DISTINCT FROM
   (product->'observation'->'binding'->>'provider'='datalab-chandra-2') THEN
   RAISE EXCEPTION 'Chandra observation role differs from its provider' USING ERRCODE='23514';
  END IF;
  IF product->'observation' ? 'mapped_evidence_digest' THEN
   RAISE EXCEPTION 'mapped visual evidence requires a supported visual observation'
   USING ERRCODE='23514'; END IF;
  IF product->'observation'->'image'->>'precision' NOT IN ('unknown','coarse') OR (product->'observation'->'image'->'transform'->>'status') NOT IN ('unknown','coarse') OR jsonb_typeof((product->'observation'->'binding'->>'decoding_json')::jsonb) IS DISTINCT FROM 'object' OR (product->'observation' ? 'usage_json' AND jsonb_typeof((product->'observation'->>'usage_json')::jsonb) IS DISTINCT FROM 'object') THEN RAISE EXCEPTION 'unadmitted provider transform/precision/settings' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM unnest(p_artifacts) supplied(content) WHERE encode(sha256(supplied.content),'hex')=product->'observation'->'image'->>'artifact_digest' AND octet_length(supplied.content)>=24 AND substring(supplied.content FROM 1 FOR 8)=decode('89504e470d0a1a0a','hex') AND get_byte(supplied.content,16)::bigint*16777216+get_byte(supplied.content,17)::bigint*65536+get_byte(supplied.content,18)::bigint*256+get_byte(supplied.content,19)::bigint=(product->'observation'->'image'->>'width')::bigint AND get_byte(supplied.content,20)::bigint*16777216+get_byte(supplied.content,21)::bigint*65536+get_byte(supplied.content,22)::bigint*256+get_byte(supplied.content,23)::bigint=(product->'observation'->'image'->>'height')::bigint) THEN RAISE EXCEPTION 'submitted PNG dimensions/bytes differ' USING ERRCODE='23514'; END IF;
  IF (product->'observation'->>'outcome' IN ('succeeded','partial') AND NOT product->'observation' ? 'raw_response_digest') OR (product->'observation'->>'outcome' IN ('failed','unknown','unsupported') AND COALESCE(product->'observation'->>'diagnostic','')='') OR product->'health'->>'execution_outcome' IS DISTINCT FROM product->'observation'->>'outcome' OR (product->'observation'->>'usage_availability'='available') IS DISTINCT FROM (product->'observation' ? 'usage_json') THEN RAISE EXCEPTION 'observation response/diagnostic/usage availability differs' USING ERRCODE='23514'; END IF;
  IF product->'observation'->'image'->'transform'->>'status'='unknown' AND product->'observation'->'image'->'transform' ?| ARRAY['page_width','page_height','page_rotation','crop_left','crop_top','crop_right','crop_bottom','affine'] THEN RAISE EXCEPTION 'unknown transform carries fabricated parameters' USING ERRCODE='23514'; END IF;
  IF product->'observation'->'image'->'transform'->>'status'='coarse' AND (NOT product->'observation'->'image'->'transform' ?& ARRAY['page_width','page_height','page_rotation','crop_left','crop_top','crop_right','crop_bottom','affine'] OR jsonb_array_length(product->'observation'->'image'->'transform'->'affine')<>6 OR EXISTS(SELECT FROM jsonb_array_elements(product->'observation'->'image'->'transform'->'affine') WHERE jsonb_typeof(value)<>'number') OR (product->'observation'->'image'->'transform'->>'page_rotation')::bigint NOT IN (0,90,180,270) OR NOT (0<=(product->'observation'->'image'->'transform'->>'crop_left')::numeric AND (product->'observation'->'image'->'transform'->>'crop_left')::numeric<(product->'observation'->'image'->'transform'->>'crop_right')::numeric AND (product->'observation'->'image'->'transform'->>'crop_right')::numeric<=(product->'observation'->'image'->'transform'->>'page_width')::numeric AND 0<=(product->'observation'->'image'->'transform'->>'crop_top')::numeric AND (product->'observation'->'image'->'transform'->>'crop_top')::numeric<(product->'observation'->'image'->'transform'->>'crop_bottom')::numeric AND (product->'observation'->'image'->'transform'->>'crop_bottom')::numeric<=(product->'observation'->'image'->'transform'->>'page_height')::numeric)) THEN RAISE EXCEPTION 'coarse transform requires complete page/crop/rotation witness' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM unnest(ARRAY[product->'observation'->'image'->>'artifact_digest',product->'observation'->>'raw_response_digest',product->'observation'->>'mapped_evidence_digest']) d WHERE d IS NOT NULL AND NOT EXISTS(SELECT FROM unnest(p_artifacts) content WHERE encode(sha256(content),'hex')=d)) THEN RAISE EXCEPTION 'observation artifact bytes are missing' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM unnest(p_artifacts) content WHERE encode(sha256(content),'hex')=product->>'recipe_digest') THEN RAISE EXCEPTION 'PDF recipe bytes are missing' USING ERRCODE='23514'; END IF;
 -- Retain exact bytes and their immutable owning identity before dependent rows.
 -- The existing input-resolution pass above still refuses forward/self/cyclic pins.
 INSERT INTO kb.source_artifact(artifact_digest,content)
 SELECT encode(sha256(content),'hex'),content FROM unnest(p_artifacts) content
 ON CONFLICT DO NOTHING;
 INSERT INTO ops.pdf_product(task_id,product_key,content_digest,kind,artifact_digest,release_id,contract_digest,publication_context)
 VALUES(p_task,product->>'product_key',digest,product->>'kind',original,context.release_id,p_contract,
 jsonb_build_object('version','pdf-observation-publication-1','request_id',context.request_id,
 'generation',context.generation,'task_id',p_task,'attempt',p_attempt,'holder',p_holder,
 'runtime_id',p_runtime,'release_id',context.release_id,'source_digest',original));
 INSERT INTO ops.pdf_product_artifact(task_id,product_key,artifact_digest)
 SELECT p_task,product->>'product_key',encode(sha256(supplied.content),'hex')
 FROM unnest(p_artifacts) supplied(content) ON CONFLICT DO NOTHING;
 INSERT INTO ops.pdf_product_body(task_id,product_key,payload,recipe_digest,descriptor)
 VALUES(p_task,product->>'product_key',p_payload,product->>'recipe_digest',product);
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
REVOKE ALL ON FUNCTION ops.publish_pdf_observation(bigint,bigint,text,text,text,bytea,bytea[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.publish_pdf_observation(bigint,bigint,text,text,text,bytea,bytea[]) TO corpus_sem_writer;
