CREATE OR REPLACE FUNCTION sem.require_execution_projection(r text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $projection$
DECLARE document jsonb; model jsonb; actual jsonb; expected jsonb; target boolean;
BEGIN
 SELECT convert_from(prepared_bytes,'UTF8')::jsonb INTO STRICT document FROM sem.release WHERE release_id=r;
 IF (SELECT convert_from(manifest_bytes,'UTF8')::jsonb->'profile'->>'compiler_version' FROM sem.release WHERE release_id=r)IS DISTINCT FROM '22' THEN RAISE EXCEPTION 'execution projection requires current compiler ABI; regenerate' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('kind',kind,'name',name,'body_hex',encode(body,'hex')) ORDER BY kind,name),'[]'::jsonb) INTO actual FROM sem.registry_row WHERE release_id=r;
 SELECT COALESCE(jsonb_agg(value ORDER BY value->>'kind',value->>'name'),'[]'::jsonb) INTO expected FROM jsonb_array_elements(document->'products'->'registry_rows');
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived registry projection differs' USING ERRCODE='23514'; END IF;
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row WHERE release_id=r AND kind='execution_model';
 target:=EXISTS(SELECT FROM sem.release WHERE release_id=r AND convert_from(manifest_bytes,'UTF8')::jsonb ? 'data_operation_model');
 IF target AND model IS NOT NULL THEN
  RAISE EXCEPTION 'target archive contains legacy execution projection' USING ERRCODE='23514'; END IF;
 IF target THEN
  PERFORM sem.require_archive_bytes(r);
  IF NOT EXISTS(SELECT FROM sem.artifact WHERE release_id=r AND artifact_name='data_operations.json'
      AND convert_from(content,'UTF8')::jsonb->>'version' = 'data-operation-model-v4') THEN
   RAISE EXCEPTION 'unsupported target operation archive' USING ERRCODE='23514'; END IF;
 END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,o->>'id' operation_id,o->>'implementation' implementation_id,b->>'version' implementation_version FROM jsonb_array_elements(model->'operations') o JOIN jsonb_array_elements(model->'implementations') b ON b->>'id'=o->>'implementation') x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.execution_operation x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived execution_operation projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,t->>'id' transition_id,t->>'operation' operation_id,t->>'lifecycle' lifecycle FROM jsonb_array_elements(model->'transitions') t) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.execution_transition x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived execution_transition projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,t->>'id' transition_id,b.value prior_state,a.value result_state FROM jsonb_array_elements(model->'transitions') t CROSS JOIN LATERAL jsonb_array_elements_text(t->'from_states') b CROSS JOIN LATERAL jsonb_array_elements_text(t->'to_states') a) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.execution_edge x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived execution_edge projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,o->>'id' operation_id,e.value effect_id,(SELECT d->>'version' FROM jsonb_array_elements(model->'effect_definitions') d WHERE d->>'id'=e.value) effect_version FROM jsonb_array_elements(model->'operations') o CROSS JOIN LATERAL jsonb_array_elements_text(o->'effects') e) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.operation_effect x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived operation_effect projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,t->>'id' transition_id,e.value effect_id,(SELECT d->>'version' FROM jsonb_array_elements(model->'effect_definitions') d WHERE d->>'id'=e.value) effect_version FROM jsonb_array_elements(model->'transitions') t CROSS JOIN LATERAL jsonb_array_elements_text(t->'effects') e) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.transition_effect x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived transition_effect projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (SELECT r release_id,rule->>'policy_id' policy_id,rule->>'evidence_tier' evidence_tier,rule->>'agreement' agreement,rule->>'decision' decision,rule->>'decision_tier' decision_tier FROM sem.artifact a CROSS JOIN LATERAL jsonb_array_elements(convert_from(a.content,'UTF8')::jsonb->'decision_rules') rule WHERE a.release_id=r AND a.artifact_name='operation/scientific-policy.json') x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.scientific_decision_rule x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived scientific_decision_rule projection differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO expected FROM (WITH declarations AS (SELECT d FROM jsonb_array_elements(document->'products'->'definitions') d), props AS (
 SELECT d,p FROM declarations CROSS JOIN LATERAL jsonb_array_elements(d->'properties') p
 WHERE d->>'name'<>'SourceRecordProduct' AND NOT (d->'ancestors' ? 'SourceRecordProduct')
 ) SELECT DISTINCT r release_id,d->>'iri' class_id,p->>'iri' property_id,roles.role
 FROM props CROSS JOIN LATERAL (
 SELECT 'identity' role WHERE EXISTS(SELECT FROM jsonb_array_elements(d->'identity_groups') g CROSS JOIN LATERAL jsonb_array_elements_text(g) member WHERE member.value=p->>'name')
 UNION ALL SELECT 'required' WHERE (p->>'required')::boolean OR COALESCE((p->>'minimum_cardinality')::integer,0)>0
 UNION ALL SELECT 'display' WHERE EXISTS(SELECT FROM sem.registry_row reg WHERE reg.release_id=r AND reg.kind='operation_property' AND convert_from(reg.body,'UTF8')::jsonb->>'class'=d->>'name' AND convert_from(reg.body,'UTF8')::jsonb->>'property'=p->>'iri' AND convert_from(reg.body,'UTF8')::jsonb->>'cs:role'='display')
 ) roles) x;
 SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),'[]'::jsonb) INTO actual FROM sem.operation_property_role x WHERE release_id=r;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'archived operation_property_role projection differs' USING ERRCODE='23514'; END IF;
END $projection$;
REVOKE ALL ON FUNCTION sem.require_execution_projection(text) FROM PUBLIC;
