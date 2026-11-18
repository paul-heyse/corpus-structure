CREATE OR REPLACE FUNCTION ops.inspect_data_operation_release(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; projection jsonb; archived jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['release_id']);
 PERFORM data.require_execution_release(p->>'release_id');
 SELECT convert_from(content,'UTF8')::jsonb INTO projection FROM sem.artifact
 WHERE release_id=p->>'release_id' AND artifact_name='data_operation_native_definitions.json';
 SELECT convert_from(content,'UTF8')::jsonb INTO archived FROM sem.artifact
 WHERE release_id=p->>'release_id' AND artifact_name='data_operations.json'
 AND encode(sha256(content),'hex')=projection->>'model_digest';
 IF projection IS NULL OR archived IS NULL THEN
 RAISE EXCEPTION 'read-only inspection lacks its authenticated operation archive' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.data_operation_release facts WHERE facts.release_id=p->>'release_id'
 AND facts.lowering_digest='__DDO_LOWERING_DIGEST__' AND facts.native_kernel_digest=projection->>'native_digest'
 AND facts.model_digest=projection->>'model_digest') THEN
 RAISE EXCEPTION 'read-only inspection native source correspondence differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH expected AS (
 SELECT value->>'kind_contract' AS key,value AS body FROM jsonb_array_elements(projection->'kinds')),
 actual AS (SELECT kind.kind_contract AS key,to_jsonb(kind.*) AS body FROM sem.data_kind_contract kind
 JOIN sem.data_kind_release membership ON membership.kind_contract=kind.kind_contract WHERE membership.release_id=p->>'release_id')
 SELECT FROM expected FULL JOIN actual USING(key) WHERE expected.body IS DISTINCT FROM actual.body) THEN
 RAISE EXCEPTION 'read-only inspection admitted kind rowset differs from archived contracts' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH expected AS (
 SELECT value->>'operation_id' AS key,value-ARRAY['binding','definition','eligibility']::text[] AS body
 FROM jsonb_array_elements(projection->'operations')),
 actual AS (SELECT definition.operation_id AS key,to_jsonb(definition)-ARRAY['release_id','binding_expression','definition_identity','eligibility_identity','quantified','validity_family','command_class','dependencies']::text[] AS body
 FROM sem.data_operation_definition definition WHERE definition.release_id=p->>'release_id')
 SELECT FROM expected FULL JOIN actual USING(key) WHERE expected.body IS DISTINCT FROM actual.body) THEN
 RAISE EXCEPTION 'read-only inspection admitted operation rowset differs from archived contracts' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('release_id',p->>'release_id',
 'model_digest',projection->>'model_digest','native_digest',projection->>'native_digest'));
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_cpu_reply_value(completion jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE evidence jsonb:=completion->'execution_evidence'; reply text; value jsonb;
BEGIN
 IF jsonb_array_length(coalesce(evidence->'cpu_receipts','[]'))<>1
 OR jsonb_array_length(coalesce(evidence->'cpu_replies','[]'))<>1
 OR jsonb_typeof(evidence->'cpu_replies'->0) IS DISTINCT FROM 'string' THEN
 RAISE EXCEPTION 'authority completion requires its actual CPU reply and original receipt' USING ERRCODE='23514'; END IF;
 reply:=evidence->'cpu_replies'->>0;
 IF encode(sha256(convert_to(reply,'UTF8')),'hex') IS DISTINCT FROM evidence->'cpu_receipts'->0->>'result_digest' THEN
 RAISE EXCEPTION 'authority CPU reply differs from its original execution receipt' USING ERRCODE='23514'; END IF;
 value:=reply::jsonb;
 IF jsonb_typeof(value) IS DISTINCT FROM 'object' THEN
 RAISE EXCEPTION 'authority CPU reply lacks its declared object result' USING ERRCODE='23514'; END IF;
 RETURN value;
END $$;
REVOKE ALL ON FUNCTION ops.ddo_cpu_reply_value(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.inspect_data_execution(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; definition sem.data_operation_definition; runtime sem.runtime_binding; retained jsonb;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=p->>'release_id' AND operation_id=p->>'operation_id';
 IF p ? 'runtime_id' THEN
  SELECT * INTO STRICT runtime FROM sem.runtime_binding
  WHERE release_id=p->>'release_id' AND runtime_id=p->>'runtime_id';
  retained:=jsonb_build_object('manifest_sha256',encode(sha256(runtime.manifest_bytes),'hex'),
   'archive_sha256',encode(sha256(runtime.archive_bytes),'hex'));
 ELSE retained:='null'::jsonb; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('recipe',definition.recipe,
  'profile',definition.profile,'implementation_revision',definition.implementation_revision,
  'input_roles',definition.input_roles,'output_roles',definition.output_roles,'runtime',retained));
END $$;

__DDO_PRODUCT_ADMISSION_PROGRAMS__

CREATE OR REPLACE FUNCTION ops.ddo_kind_access(contract text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE universe text;
BEGIN
 SELECT kind.universe INTO STRICT universe FROM sem.data_kind_contract kind WHERE kind.kind_contract=contract;
 PERFORM ops.ddo_authorize(universe);
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_body_kind_contracts(p_kind text,p_body jsonb) RETURNS SETOF text
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE kind sem.data_kind_contract; child_kind sem.data_kind_contract; members jsonb; packet jsonb; child text; child_body jsonb;
BEGIN
 SELECT * INTO STRICT kind FROM sem.data_kind_contract WHERE kind_contract=p_kind;
 RETURN NEXT p_kind;
 IF kind.member_schema='{"not":{}}'::jsonb THEN RETURN; END IF;
 members:=data.ddo_field(p_body,'members');
 IF members IS NULL THEN RETURN; END IF;
 IF members->>0 IS DISTINCT FROM 'sequence' THEN RAISE EXCEPTION 'invalid nominal member body'; END IF;
 FOR packet IN SELECT value FROM jsonb_array_elements(members->1) LOOP
 child:=data.ddo_field(packet,'kind_contract')->>1;
 child_body:=data.ddo_field(packet,'body');
 IF child IS NULL OR child_body IS NULL OR NOT kind.member_contracts ? child THEN
 RAISE EXCEPTION 'body member kind is outside its captured nominal contract'; END IF;
 SELECT * INTO STRICT child_kind FROM sem.data_kind_contract WHERE kind_contract=child;
 IF NOT public.json_matches_schema(child_kind.meaning_schema::json,child_body::json)
 OR NOT public.json_matches_schema(child_kind.body_schema::json,data.ddo_json(child_body)::json) THEN
 RAISE EXCEPTION 'body member value differs from its captured nominal kind'; END IF;
 RETURN QUERY SELECT * FROM ops.ddo_body_kind_contracts(child,child_body);
 END LOOP;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_body_access(p_kind text,p_body jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE contract text;
BEGIN
 FOR contract IN SELECT * FROM ops.ddo_body_kind_contracts(p_kind,p_body) LOOP
 PERFORM ops.ddo_kind_access(contract);
 END LOOP;
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_binding_body_access(p_binding jsonb,p_project text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM ops.ddo_kind_access(product.kind_contract),
 ops.ddo_body_access(coalesce(member.kind_contract,product.kind_contract),coalesce(member.body,product.canonical_body))
 FROM jsonb_array_elements(p_binding->'inputs') input
 JOIN kb.data_product product ON product.id=input->>'product_id' AND product.project_id=p_project
 LEFT JOIN kb.data_product_member member ON member.product_id=product.id AND member.member_id=input->>'member_id'
 WHERE input->>'member_id' IS NULL OR member.member_id IS NOT NULL;
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_binding_rows(p_demand text,p_operation text,p_trust jsonb,p_read text DEFAULT NULL,p_subject text DEFAULT NULL,p_source jsonb DEFAULT NULL,p_scope jsonb DEFAULT NULL,p_decode_body boolean DEFAULT true,p_selected jsonb DEFAULT NULL,p_read_checked boolean DEFAULT false)
RETURNS TABLE(__DDO_CORE_BINDING_RETURNS__)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE d ops.data_demand; snapshot jsonb; boundary ops.data_demand_read;
BEGIN
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p_demand;
 IF p_read IS NULL THEN RAISE EXCEPTION 'binding requires exact native read acquisition'; END IF;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p_read AND demand_id=d.id;
 IF p_read_checked THEN snapshot:=p_trust; ELSE snapshot:=ops.ddo_require_read_current(boundary,d.project_id); END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') selected WHERE selected->>'operation'=p_operation) THEN RAISE EXCEPTION 'projection operation outside frozen demand'; END IF;
 IF p_source IS NOT NULL THEN
 IF jsonb_typeof(p_source) NOT IN ('string','null') THEN RAISE EXCEPTION 'source filter requires JSON string or explicit null' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_require_subject_source(ops.ddo_release_subject_scopes(d.release_id),ops.ddo_operation_subject(d.release_id,p_operation),p_source#>>'{}');
 END IF;
 IF ops.ddo_trust_snapshot_meaning(snapshot) IS DISTINCT FROM ops.ddo_trust_snapshot_meaning(p_trust) THEN RAISE EXCEPTION 'binding trust snapshot changed'; END IF;
 RETURN QUERY __DDO_CORE_BINDING_COMPUTED__;
 RETURN QUERY __DDO_CORE_BINDING_ORIGINAL__;
END $$;
CREATE OR REPLACE FUNCTION ops.data_binding_rows(p_demand text,p_operation text,p_trust jsonb,p_read text DEFAULT NULL,p_subject text DEFAULT NULL,p_source jsonb DEFAULT NULL,p_scope jsonb DEFAULT NULL)
RETURNS TABLE(__DDO_CORE_BINDING_RETURNS__)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 RETURN QUERY SELECT * FROM ops.ddo_binding_rows(p_demand,p_operation,p_trust,p_read,p_subject,p_source,p_scope,true,NULL);
END $$;
