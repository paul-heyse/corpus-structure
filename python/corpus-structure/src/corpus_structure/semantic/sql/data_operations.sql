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

CREATE OR REPLACE FUNCTION ops.ddo_install_product_context(context jsonb,o jsonb,subject_scopes jsonb) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE k sem.data_kind_contract; key text; b jsonb; bd text; m jsonb; raw jsonb; family_value jsonb; n bigint; previous kb.data_product; packet jsonb; member_context jsonb; member_kind sem.data_kind_contract; inserted_product bigint;
BEGIN
 PERFORM ops.ddo_fields(context,ARRAY['project_id','release_id','subject','subject_definition','original_source','analyzed_scope']);
 PERFORM ops.ddo_require_subject_source(subject_scopes,context->>'subject_definition',context->>'original_source');
 PERFORM ops.ddo_fields(o,ARRAY['kind_contract','body','members'],ARRAY['artifact_digest']);
 SELECT * INTO STRICT k FROM sem.data_kind_contract WHERE kind_contract=o->>'kind_contract';
 PERFORM ops.ddo_authorize(k.universe);
 IF NOT EXISTS(SELECT FROM sem.data_kind_release WHERE release_id=(context->>'release_id') AND kind_contract=k.kind_contract) THEN RAISE EXCEPTION 'output kind is outside release'; END IF;
 IF o->>'artifact_digest' IS NOT NULL THEN RAISE EXCEPTION 'artifact publication requires an authenticated staged receipt profile'; END IF;
 b:=data.ddo_normalize(o->'body');
 PERFORM ops.ddo_body_access(k.kind_contract,b);
 IF NOT public.json_matches_schema(k.meaning_schema::json,b::json) OR NOT public.json_matches_schema(k.body_schema::json,data.ddo_json(b)::json) OR jsonb_typeof(o->'members')<>'array' THEN RAISE EXCEPTION 'body violates kind contract'; END IF;
 IF k.member_schema='{"not":{}}'::jsonb THEN
 IF o->'members'<>'[]'::jsonb THEN RAISE EXCEPTION 'noncontainer kind cannot publish projected members'; END IF;
 ELSE
 IF coalesce(data.ddo_field(b,'members')->>0,'')<>'sequence' OR jsonb_array_length(data.ddo_field(b,'members')->1)<>jsonb_array_length(o->'members') THEN RAISE EXCEPTION 'body/member projection count disagreement'; END IF;
 END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(o->'members') member GROUP BY member->>'member_id' HAVING count(*)<>1) THEN RAISE EXCEPTION 'duplicate member local identity'; END IF;
 bd:=data.ddo_identity('body',b);
 key:=data.ddo_identity('product',jsonb_build_array('mapping',jsonb_build_array(jsonb_build_array('body',jsonb_build_array('string',bd)),jsonb_build_array('kind',jsonb_build_array('string',k.kind_contract)),jsonb_build_array('subject',jsonb_build_array('string',(context->>'subject'))),jsonb_build_array('subject_context',data.ddo_json_meaning(jsonb_build_object('project_id',context->>'project_id','subject',context->>'subject','subject_definition',context->>'subject_definition','original_source',context->>'original_source','analyzed_scope',context->'analyzed_scope'))))));
 INSERT INTO kb.data_product (id,kind_contract,project_id,subject,subject_definition,original_source,analyzed_scope,canonical_body,body_digest,artifact_digest) VALUES(key,k.kind_contract,(context->>'project_id'),(context->>'subject'),(context->>'subject_definition'),(context->>'original_source'),(context->'analyzed_scope'),b,bd,o->>'artifact_digest') ON CONFLICT DO NOTHING;
 GET DIAGNOSTICS inserted_product=ROW_COUNT;
 SELECT * INTO STRICT previous FROM kb.data_product WHERE id=key;
 IF (previous.kind_contract,previous.project_id,previous.subject,previous.subject_definition,previous.original_source,previous.body_digest) IS DISTINCT FROM (k.kind_contract,(context->>'project_id'),(context->>'subject'),(context->>'subject_definition'),(context->>'original_source'),bd) OR previous.canonical_body IS DISTINCT FROM b OR previous.analyzed_scope IS DISTINCT FROM (context->'analyzed_scope') THEN RAISE EXCEPTION 'product identity/custody collision'; END IF;
 FOR m,n IN SELECT value,ord-1 FROM jsonb_array_elements(o->'members') WITH ORDINALITY entry(value,ord) LOOP
 PERFORM ops.ddo_fields(m,ARRAY['member_id','kind_contract','context','body'],ARRAY['coordinates','roles','endpoints','coverage','choices']);
 PERFORM ops.ddo_fields(m->'context',ARRAY['subject','subject_definition','original_source','analyzed_scope']);
 packet:=data.ddo_field(b,'members')->1->(n::integer);
 member_context:=m->'context';
 IF packet->>0<>'mapping' OR jsonb_array_length(packet->1)<>4
 OR data.ddo_field(packet,'member_id') IS DISTINCT FROM jsonb_build_array('string',m->>'member_id')
 OR data.ddo_field(packet,'kind_contract') IS DISTINCT FROM jsonb_build_array('string',m->>'kind_contract')
 OR data.ddo_field(packet,'body') IS DISTINCT FROM data.ddo_normalize(m->'body')
 OR data.ddo_json(data.ddo_field(packet,'context')) IS DISTINCT FROM member_context
 OR nullif(member_context->>'subject','') IS NULL OR nullif(member_context->>'subject_definition','') IS NULL
 OR member_context->>'original_source' IS DISTINCT FROM (context->>'original_source') THEN RAISE EXCEPTION 'member context/body differs from canonical container packet'; END IF;
 PERFORM ops.ddo_require_subject_source(subject_scopes,member_context->>'subject_definition',member_context->>'original_source');
 SELECT * INTO STRICT member_kind FROM sem.data_kind_contract WHERE kind_contract=m->>'kind_contract';
 PERFORM ops.ddo_authorize(member_kind.universe);
 IF NOT k.member_contracts ? member_kind.kind_contract
 OR NOT EXISTS(SELECT FROM sem.data_kind_release release_kind WHERE release_kind.release_id=(context->>'release_id') AND release_kind.kind_contract=member_kind.kind_contract)
 OR NOT public.json_matches_schema(member_kind.meaning_schema::json,data.ddo_normalize(m->'body')::json)
 OR NOT public.json_matches_schema(member_kind.body_schema::json,data.ddo_json(data.ddo_normalize(m->'body'))::json) THEN RAISE EXCEPTION 'member kind/body differs from declared nominal container member contract'; END IF;
 IF nullif(m->>'member_id','') IS NULL OR NOT public.json_matches_schema(k.member_schema::json,data.ddo_json(data.ddo_normalize(m->'body'))::json) THEN RAISE EXCEPTION 'invalid member contract'; END IF;
 raw:=data.ddo_json(data.ddo_normalize(m->'body'));
 IF EXISTS(SELECT FROM (VALUES('coordinates','coordinate'),('roles','role'),('endpoints','endpoint'),('coverage','coverage'),('choices','choice')) fields(field,family) WHERE (member_kind.families ? family AND coalesce(raw->field,'[]') IS DISTINCT FROM coalesce(m->field,'[]')) OR (NOT member_kind.families ? family AND coalesce(m->field,'[]')<>'[]'::jsonb)) THEN RAISE EXCEPTION 'member projection differs from semantic body'; END IF;
 END LOOP;
 INSERT INTO kb.data_product_member (product_id,member_id,kind_contract,subject,subject_definition,original_source,analyzed_scope,body)
 SELECT key,member->>'member_id',member->>'kind_contract',member->'context'->>'subject',
 member->'context'->>'subject_definition',member->'context'->>'original_source',member->'context'->'analyzed_scope',
 data.ddo_normalize(member->'body')
 FROM jsonb_array_elements(o->'members') WITH ORDINALITY entry(member,ordinal)
 WHERE inserted_product=1 ORDER BY ordinal ON CONFLICT DO NOTHING;
 -- All local endpoints exist before family insertion. Cross-product endpoints require exact custody.
 FOR m IN SELECT value FROM jsonb_array_elements(o->'members') LOOP
 SELECT * INTO STRICT member_kind FROM sem.data_kind_contract WHERE kind_contract=m->>'kind_contract';
 FOR family_value,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'coordinates','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(family_value,ARRAY['original_source','start','end'],ARRAY['page']);
 IF context->>'original_source' IS NULL OR family_value->>'original_source' IS DISTINCT FROM (context->>'original_source') OR NOT member_kind.families ? 'coordinate' THEN RAISE EXCEPTION 'coordinate source/family mismatch'; END IF;
 END LOOP;
 FOR family_value,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'roles','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(family_value,ARRAY['role','position','multiplicity']);
 IF NOT member_kind.families ? 'role' THEN RAISE EXCEPTION 'undeclared role family'; END IF;
 END LOOP;
 FOR family_value,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'endpoints','[]')) WITH ORDINALITY a(value,ord) LOOP
 IF family_value->>'scope'='local' THEN PERFORM ops.ddo_fields(family_value,ARRAY['scope','role','member_id']);
 ELSIF family_value->>'scope'='external' THEN PERFORM ops.ddo_fields(family_value,ARRAY['scope','role','product_id','member_id']);
 ELSE RAISE EXCEPTION 'endpoint requires explicit local/external scope'; END IF;
 IF NOT member_kind.families ? 'endpoint' OR NOT EXISTS(SELECT FROM kb.data_product x WHERE x.id=CASE WHEN family_value->>'scope'='local' THEN key ELSE family_value->>'product_id' END AND x.project_id=(context->>'project_id') AND x.original_source IS NOT DISTINCT FROM (context->>'original_source')) THEN RAISE EXCEPTION 'endpoint custody/family mismatch'; END IF;
 END LOOP;
 FOR family_value,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'coverage','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(family_value,ARRAY['scope','start','end','complete']);
 IF NOT member_kind.families ? 'coverage' THEN RAISE EXCEPTION 'undeclared coverage family'; END IF;
 END LOOP;
 FOR family_value,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'choices','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(family_value,ARRAY['choice_group','alternative','selected']);
 IF NOT member_kind.families ? 'choice' THEN RAISE EXCEPTION 'undeclared choice family'; END IF;
 END LOOP;
 END LOOP;
 INSERT INTO kb.data_member_coordinate
 SELECT key,member->>'member_id',ordinal-1,f->>'original_source',(f->>'start')::integer,(f->>'end')::integer,(f->>'page')::integer
 FROM jsonb_array_elements(o->'members') entry(member)
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'coordinates','[]')) WITH ORDINALITY item(f,ordinal)
 WHERE inserted_product=1 ORDER BY member->>'member_id',ordinal ON CONFLICT DO NOTHING;
 INSERT INTO kb.data_member_role
 SELECT key,member->>'member_id',ordinal-1,f->>'role',(f->>'position')::integer,(f->>'multiplicity')::integer
 FROM jsonb_array_elements(o->'members') entry(member)
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'roles','[]')) WITH ORDINALITY item(f,ordinal)
 WHERE inserted_product=1 ORDER BY member->>'member_id',ordinal ON CONFLICT DO NOTHING;
 INSERT INTO kb.data_member_endpoint
 SELECT key,member->>'member_id',ordinal-1,f->>'role',CASE WHEN f->>'scope'='local' THEN key ELSE f->>'product_id' END,f->>'member_id'
 FROM jsonb_array_elements(o->'members') entry(member)
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'endpoints','[]')) WITH ORDINALITY item(f,ordinal)
 WHERE inserted_product=1 ORDER BY member->>'member_id',ordinal ON CONFLICT DO NOTHING;
 INSERT INTO kb.data_member_coverage
 SELECT key,member->>'member_id',ordinal-1,f->>'scope',(f->>'start')::integer,(f->>'end')::integer,(f->>'complete')::boolean
 FROM jsonb_array_elements(o->'members') entry(member)
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'coverage','[]')) WITH ORDINALITY item(f,ordinal)
 WHERE inserted_product=1 ORDER BY member->>'member_id',ordinal ON CONFLICT DO NOTHING;
 INSERT INTO kb.data_member_choice
 SELECT key,member->>'member_id',ordinal-1,f->>'choice_group',f->>'alternative',(f->>'selected')::boolean
 FROM jsonb_array_elements(o->'members') entry(member)
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'choices','[]')) WITH ORDINALITY item(f,ordinal)
 WHERE inserted_product=1 ORDER BY member->>'member_id',ordinal ON CONFLICT DO NOTHING;
 -- Replays skip installation but still compare every projected ordinal. A native
 -- kernel change cannot silently reuse different members under the same product.
 WITH member_packets AS (SELECT member FROM jsonb_array_elements(o->'members') entry(member)),
 expected AS (SELECT 'member'::text family,member->>'member_id' member_id,-1::bigint ordinal,
 jsonb_build_array(member->>'kind_contract',member->'context'->>'subject',member->'context'->>'subject_definition',
 member->'context'->>'original_source',member->'context'->'analyzed_scope',data.ddo_normalize(member->'body')) value
 FROM member_packets UNION ALL SELECT 'coordinate'::text family,member->>'member_id' member_id,ordinal-1 ordinal,
 jsonb_build_array(f->>'original_source',(f->>'start')::integer,(f->>'end')::integer,(f->>'page')::integer) value FROM member_packets
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'coordinates','[]')) WITH ORDINALITY item(f,ordinal) UNION ALL SELECT 'role'::text family,member->>'member_id' member_id,ordinal-1 ordinal,
 jsonb_build_array(f->>'role',(f->>'position')::integer,(f->>'multiplicity')::integer) value FROM member_packets
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'roles','[]')) WITH ORDINALITY item(f,ordinal) UNION ALL SELECT 'endpoint'::text family,member->>'member_id' member_id,ordinal-1 ordinal,
 jsonb_build_array(f->>'role',CASE WHEN f->>'scope'='local' THEN key ELSE f->>'product_id' END,f->>'member_id') value FROM member_packets
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'endpoints','[]')) WITH ORDINALITY item(f,ordinal) UNION ALL SELECT 'coverage'::text family,member->>'member_id' member_id,ordinal-1 ordinal,
 jsonb_build_array(f->>'scope',(f->>'start')::integer,(f->>'end')::integer,(f->>'complete')::boolean) value FROM member_packets
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'coverage','[]')) WITH ORDINALITY item(f,ordinal) UNION ALL SELECT 'choice'::text family,member->>'member_id' member_id,ordinal-1 ordinal,
 jsonb_build_array(f->>'choice_group',f->>'alternative',(f->>'selected')::boolean) value FROM member_packets
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(member->'choices','[]')) WITH ORDINALITY item(f,ordinal)), actual AS (SELECT 'member'::text family,member_id,-1::bigint ordinal,
 jsonb_build_array(kind_contract,subject,subject_definition,original_source,analyzed_scope,body) value
 FROM kb.data_product_member WHERE product_id=key UNION ALL SELECT 'coordinate'::text family,member_id,ordinal,jsonb_build_array("original_source","start","end","page") value FROM kb.data_member_coordinate WHERE product_id=key UNION ALL SELECT 'role'::text family,member_id,ordinal,jsonb_build_array("role","position","multiplicity") value FROM kb.data_member_role WHERE product_id=key UNION ALL SELECT 'endpoint'::text family,member_id,ordinal,jsonb_build_array("role","endpoint_product","endpoint_member") value FROM kb.data_member_endpoint WHERE product_id=key UNION ALL SELECT 'coverage'::text family,member_id,ordinal,jsonb_build_array("scope","start","end","complete") value FROM kb.data_member_coverage WHERE product_id=key UNION ALL SELECT 'choice'::text family,member_id,ordinal,jsonb_build_array("choice_group","alternative","selected") value FROM kb.data_member_choice WHERE product_id=key)
 SELECT coalesce(expected.ordinal,actual.ordinal) INTO n
 FROM expected FULL JOIN actual USING(family,member_id,ordinal)
 WHERE expected.value IS DISTINCT FROM actual.value
 ORDER BY coalesce(expected.member_id,actual.member_id),coalesce(expected.ordinal,actual.ordinal),coalesce(expected.family,actual.family)
 LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'member projection identity collision at ordinal %',n USING ERRCODE='23514'; END IF;
 RETURN key;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_admit_original_source(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; d ops.data_demand; frozen jsonb; fact jsonb; kind text; product text; identity text;
 snapshot jsonb; kind_name text; kind_universe text; key text; admitted ops.original_source_admission; rooted boolean; subject_scopes jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['demand_id','selection_name','reference','selectors']);
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p->>'demand_id';
 frozen:=d.selection->'original_sources'->(p->>'selection_name');
 IF frozen IS NULL OR frozen IS DISTINCT FROM (p-'demand_id'-'selection_name')
 OR p->'reference'->>'project_id' IS DISTINCT FROM d.project_id THEN RAISE EXCEPTION 'original source selection differs from immutable demand'; END IF;
 IF p->'reference'->>'kind'='authored-fact' THEN
 IF p->'selectors' IS DISTINCT FROM '[{"scope":"authored-fact"}]'::jsonb THEN
 RAISE EXCEPTION 'authored input requires its explicit immutable selection scope'; END IF;
 SELECT contract.kind,contract.universe INTO STRICT kind_name,kind_universe FROM sem.data_kind_contract contract
 JOIN sem.data_kind_release release ON release.kind_contract=contract.kind_contract
 WHERE release.release_id=d.release_id AND contract.kind_contract=p->'reference'->>'kind_contract'
 AND contract.universe IN ('ordinary','evaluator');
 PERFORM ops.ddo_authorize(kind_universe);
 fact:=jsonb_build_object('subject',p->'reference'->>'subject','subject_definition',p->'reference'->>'subject_definition','original_source',p->'reference'->>'original_source',
 'analyzed_scope',p->'reference'->'analyzed_scope','meaning_body',data.ddo_normalize(p->'reference'->'meaning_body'),
 'evidence',jsonb_build_object('standing','authored','author_assertion',p->'reference'->>'author',
 'selection_id',p->'reference'->>'selection_id','submitted_by',coalesce(nullif(current_setting('role'),'none'),session_user)));
 ELSIF p->'reference'->>'kind'='original-document' THEN
 IF p->'selectors' IS DISTINCT FROM '[{"scope":"whole-document"}]'::jsonb THEN
 RAISE EXCEPTION 'original document scope differs from immutable whole document'; END IF;
 fact:=ops.ddo_original_document_view(p->'reference');
 kind_name:='https://corpus-structure.dev/semantic/data-operation-source/DdoOriginalDocument';
 ELSE
 RAISE EXCEPTION 'unknown original source admission reference';
 END IF;
 subject_scopes:=ops.ddo_release_subject_scopes(d.release_id);
 PERFORM ops.ddo_require_subject_source(subject_scopes,fact->>'subject_definition',fact->>'original_source');
 rooted:=EXISTS(SELECT FROM jsonb_array_elements(d.root) root WHERE
 (root->>'subject',root->>'original_source') IS NOT DISTINCT FROM (fact->>'subject',fact->>'original_source')
 AND root->'analyzed_scope'=fact->'analyzed_scope');
 IF NOT rooted THEN RAISE EXCEPTION 'authenticated source context is outside frozen roots'; END IF;
 snapshot:=ops.ddo_lock_support(d.project_id,fact->>'original_source','[]');
 PERFORM ops.ddo_require_active_demand(d.id);
 SELECT release.kind_contract INTO STRICT kind FROM sem.data_kind_release release
 JOIN sem.data_kind_contract contract ON contract.kind_contract=release.kind_contract
 WHERE release.release_id=d.release_id AND contract.kind=kind_name;
 product:=ops.ddo_install_product_context(jsonb_build_object('project_id',d.project_id,'release_id',d.release_id,
 'subject',fact->>'subject','subject_definition',fact->>'subject_definition','original_source',fact->>'original_source','analyzed_scope',fact->'analyzed_scope'),
 jsonb_build_object('kind_contract',kind,'body',fact->'meaning_body','members',
 (SELECT coalesce(jsonb_agg(jsonb_build_object('member_id',data.ddo_json(data.ddo_field(packet,'member_id')),
 'kind_contract',data.ddo_json(data.ddo_field(packet,'kind_contract')),
 'context',data.ddo_json(data.ddo_field(packet,'context')),'body',data.ddo_field(packet,'body'))
 || (SELECT coalesce(jsonb_object_agg(field,data.ddo_json(data.ddo_field(data.ddo_field(packet,'body'),field))),'{}')
 FROM unnest(ARRAY['coordinates','roles','endpoints','coverage','choices']) field
 WHERE data.ddo_field(data.ddo_field(packet,'body'),field) IS NOT NULL)), '[]')
 FROM jsonb_array_elements(CASE WHEN fact->'meaning_body'->>0='mapping'
 THEN coalesce(data.ddo_field(fact->'meaning_body','members')->1,'[]') ELSE '[]'::jsonb END) packet)),subject_scopes);
 identity:=ops.ddo_digest(p->'reference');
 key:='original-admission:'||ops.ddo_digest(jsonb_build_array(d.id,p->>'selection_name',identity,p->'selectors',product));
 INSERT INTO ops.original_source_admission VALUES(key,d.id,d.project_id,d.release_id,p->>'selection_name',identity,
 p->'reference',p->'selectors',product,fact->>'subject',fact->>'original_source',fact->'analyzed_scope',snapshot,
 fact->'evidence',clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT admitted FROM ops.original_source_admission WHERE demand_id=d.id AND selection_name=p->>'selection_name';
 IF admitted.id<>key THEN RAISE EXCEPTION 'immutable original source admission changed'; END IF;
 IF NOT ops.ddo_original_admission_valid(admitted) THEN RAISE EXCEPTION 'original source admission is revoked'; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('admission_id',admitted.id,'selection_name',admitted.selection_name,
 'product_id',product,'kind_contract',kind,'subject',admitted.subject,'subject_definition',fact->>'subject_definition','original_source',admitted.original_source,
 'analyzed_scope',admitted.analyzed_scope,'source_reference',identity,'trust_snapshot',snapshot,'evidence',admitted.evidence));
END $$;

CREATE OR REPLACE FUNCTION ops.admit_authored_data(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF p_payload->'reference'->>'kind' IS DISTINCT FROM 'authored-fact' THEN
 RAISE EXCEPTION 'authored admission requires its exact declared fact reference'; END IF;
 RETURN ops.ddo_admit_original_source(p_payload);
END $$;

CREATE OR REPLACE FUNCTION ops.admit_original_document_asset(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF p_payload->'reference'->>'kind' IS DISTINCT FROM 'original-document' THEN
 RAISE EXCEPTION 'original document reference discriminator differs'; END IF;
 RETURN ops.ddo_admit_original_source(p_payload);
END $$;

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
