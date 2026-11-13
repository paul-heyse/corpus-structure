-- Fixed trusted DDO kernel. JSON is a strict wire/archive envelope, not an EAV store.
CREATE OR REPLACE FUNCTION ops.ddo_fields(p jsonb, required text[], optional text[] DEFAULT ARRAY[]::text[])
RETURNS void LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR EXISTS(SELECT FROM unnest(required) k WHERE NOT p ? k)
 OR EXISTS(SELECT FROM jsonb_object_keys(p) k WHERE NOT k=ANY(required||optional)) THEN
 RAISE EXCEPTION 'DDO wire fields differ from the fixed operation contract' USING ERRCODE='23514'; END IF;
END $$;

CREATE OR REPLACE FUNCTION data.ddo_normalize(v jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE tag text; x jsonb; result jsonb; n integer; lexical text;
BEGIN
 IF jsonb_typeof(v)<>'array' OR jsonb_array_length(v)=0 OR jsonb_typeof(v->0)<>'string' THEN
 RAISE EXCEPTION 'DDO semantic value must be tagged' USING ERRCODE='23514'; END IF;
 tag:=v->>0; n:=jsonb_array_length(v);
 IF tag IN ('null','known-absent','unknown','unavailable') AND n=1 THEN RETURN v;
 ELSIF tag='boolean' AND n=2 AND jsonb_typeof(v->1)='boolean' THEN RETURN v;
 ELSIF tag IN ('string','date','datetime','float','integer','decimal') AND n=2 AND jsonb_typeof(v->1)='string' THEN
 lexical:=v->>1;
 IF tag='integer' THEN
  IF lexical !~ '^[+-]?[0-9]+$' THEN RAISE EXCEPTION 'invalid integer meaning'; END IF;
  lexical:=data.decimal_canonical(lexical);
 ELSIF tag='decimal' THEN
  IF lexical !~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' THEN RAISE EXCEPTION 'invalid decimal meaning'; END IF;
  lexical:=data.decimal_canonical(lexical);
 ELSIF tag='float' THEN lexical:=data.require_float_lexical(lexical);
 ELSIF tag='date' THEN
  IF lexical !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR lexical<>(lexical::date)::text THEN RAISE EXCEPTION 'date meaning requires canonical ISO date'; END IF;
 ELSIF tag='datetime' THEN
  IF lexical !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]{6})?[+]00:00$'
  OR lexical IS DISTINCT FROM (to_char(lexical::timestamptz AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS')||
    (CASE WHEN extract(microseconds FROM lexical::timestamptz)::bigint % 1000000<>0 THEN '.'||to_char(lexical::timestamptz AT TIME ZONE 'UTC','US') ELSE '' END)||'+00:00') THEN RAISE EXCEPTION 'datetime meaning requires canonical Python UTC ISO instant'; END IF;
 END IF;
 RETURN jsonb_build_array(tag,lexical);
 ELSIF tag='present' AND n=2 THEN RETURN jsonb_build_array(tag,data.ddo_normalize(v->1));
 ELSIF tag IN ('sequence','ordered-bag','bag','set') AND n=2 AND jsonb_typeof(v->1)='array' THEN
 SELECT coalesce(jsonb_agg(data.ddo_normalize(value) ORDER BY ord),'[]') INTO result FROM jsonb_array_elements(v->1) WITH ORDINALITY a(value,ord);
 IF tag IN ('bag','set') THEN
  IF tag='set' THEN SELECT coalesce(jsonb_agg(value ORDER BY convert_to(data.canonical_json(value),'UTF8')),'[]') INTO result FROM (SELECT DISTINCT value FROM jsonb_array_elements(result)) q;
  ELSE SELECT coalesce(jsonb_agg(value ORDER BY convert_to(data.canonical_json(value),'UTF8')),'[]') INTO result FROM jsonb_array_elements(result); END IF;
 END IF; RETURN jsonb_build_array(tag,result);
 ELSIF tag='mapping' AND n=2 AND jsonb_typeof(v->1)='array' THEN
 IF EXISTS(SELECT FROM jsonb_array_elements(v->1) e WHERE jsonb_typeof(e)<>'array' OR jsonb_array_length(e)<>2 OR jsonb_typeof(e->0)<>'string')
 OR EXISTS(SELECT FROM jsonb_array_elements(v->1) e GROUP BY e->>0 HAVING count(*)<>1) THEN RAISE EXCEPTION 'invalid mapping members'; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_array(e->0,data.ddo_normalize(e->1)) ORDER BY (e->>0) COLLATE "C"),'[]') INTO result FROM jsonb_array_elements(v->1) e;
 RETURN jsonb_build_array(tag,result);
 END IF;
 RAISE EXCEPTION 'invalid or unsupported DDO semantic tag %',tag USING ERRCODE='23514';
END $$;
CREATE OR REPLACE FUNCTION data.ddo_identity(domain text,v jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT domain||':'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array('ddo',domain,'1',data.ddo_normalize(v))),'UTF8')),'hex')
$$;
CREATE OR REPLACE FUNCTION ops.ddo_digest(v jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$ SELECT encode(sha256(convert_to(data.canonical_json(v),'UTF8')),'hex') $$;

CREATE OR REPLACE FUNCTION ops.ddo_authorize(universe text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF universe='evaluator' AND NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_evaluator','MEMBER') THEN
 RAISE EXCEPTION 'evaluator data requires evaluator purpose' USING ERRCODE='42501'; END IF;
 IF universe NOT IN ('ordinary','source','evaluator') THEN RAISE EXCEPTION 'unknown data universe'; END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_scope(project text,source text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$ SELECT 'source:'||ops.ddo_digest(jsonb_build_array(project,source)) $$;

CREATE OR REPLACE FUNCTION ops.ddo_lock_support(project text,source text,support jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE scope_key text; snapshot jsonb:='{}'; e bigint;
BEGIN
 -- A recursive closure includes every producing scope, not merely caller named epochs.
 FOR scope_key IN WITH RECURSIVE closure(id) AS (
 SELECT value->>'derivation_id' FROM jsonb_array_elements(support)
 UNION SELECT s.support_derivation_id FROM ops.data_derivation_support s JOIN closure c ON c.id=s.derivation_id
 ), scopes AS (
 SELECT ops.ddo_scope(project,source) AS scope UNION
 SELECT ops.ddo_scope(r.project_id,r.original_source) FROM closure c JOIN ops.data_derivation d ON d.id=c.id JOIN ops.data_request r ON r.id=d.request_id
 ) SELECT scope FROM scopes ORDER BY scope LOOP
 INSERT INTO ops.data_trust_scope(scope,project_id,epoch) VALUES(scope_key,project,0) ON CONFLICT DO NOTHING;
 SELECT epoch INTO e FROM ops.data_trust_scope WHERE scope=scope_key FOR UPDATE;
 snapshot:=snapshot||jsonb_build_object(scope_key,e);
 END LOOP;
 RETURN snapshot;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_read_visible(created_at timestamp with time zone,created_xid text,boundary ops.data_demand_read) RETURNS boolean
LANGUAGE sql STABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT created_at<=boundary.frontier_at AND (created_xid=boundary.owner_xid OR pg_visible_in_snapshot(created_xid::xid8,boundary.read_snapshot::pg_snapshot))
$$;

CREATE OR REPLACE FUNCTION ops.ddo_direct_support_valid(episode text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT EXISTS(SELECT FROM ops.data_derivation WHERE id=episode AND outcome IN ('success','empty')) AND NOT EXISTS(
 SELECT FROM ops.data_derivation d JOIN ops.data_request r ON r.id=d.request_id
 JOIN ops.data_revocation v ON v.scope=ops.ddo_scope(r.project_id,r.original_source)
 WHERE d.id=episode AND ((v.selector_kind='derivation' AND v.selector=d.id) OR (v.selector_kind='recipe' AND v.selector=d.recipe)
 OR (v.selector_kind='runtime' AND v.selector=d.runtime_id) OR (v.selector_kind='product' AND EXISTS(SELECT FROM ops.data_derivation_output o WHERE o.derivation_id=d.id AND o.product_id=v.selector))))
$$;
CREATE OR REPLACE FUNCTION ops.ddo_support_valid(episode text,boundary ops.data_demand_read DEFAULT NULL) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s ops.data_derivation_support; u ops.demand_use;
BEGIN
 IF NOT ops.ddo_direct_support_valid(episode) THEN RETURN false; END IF;
 FOR s IN SELECT * FROM ops.data_derivation_support WHERE derivation_id=episode LOOP
 IF s.admission_use_id IS NULL THEN
  IF NOT ops.ddo_support_valid(s.support_derivation_id,boundary) THEN RETURN false; END IF;
 ELSE
  SELECT * INTO u FROM ops.demand_use WHERE id=s.admission_use_id AND derivation_id=s.support_derivation_id;
  IF NOT FOUND OR NOT ops.ddo_use_valid(u,boundary) THEN RETURN false; END IF;
 END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_use_valid(u ops.demand_use,boundary ops.data_demand_read DEFAULT NULL) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE support jsonb; selected ops.demand_use;
BEGIN
 IF u.fate<>'fulfilled' OR NOT ops.ddo_direct_support_valid(u.derivation_id) THEN RETURN false; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(u.selection->'populations','[]')) ref LEFT JOIN ops.data_population pop ON pop.id=ref->>'population_id' AND pop.demand_id=u.demand_id WHERE pop.id IS NULL OR NOT ops.ddo_population_valid(pop,boundary)) THEN RETURN false; END IF;
 IF ops.ddo_support_valid(u.derivation_id,boundary) THEN RETURN true; END IF;
 IF NOT EXISTS(SELECT FROM ops.data_derivation d JOIN sem.data_operation_definition def ON (def.release_id,def.recipe)=(d.release_id,d.recipe)
 JOIN ops.data_demand demand ON demand.id=u.demand_id WHERE d.id=u.derivation_id AND def.support_contract->>'provenance'='value_substitution' AND demand.strength='value') THEN RETURN false; END IF;
 FOR support IN SELECT value FROM jsonb_array_elements(u.selection->'support') LOOP
 IF support->>'admission_use_id' IS NULL THEN
  IF NOT ops.ddo_support_valid(support->>'derivation_id',boundary) THEN RETURN false; END IF;
 ELSE
  SELECT * INTO selected FROM ops.demand_use WHERE id=support->>'admission_use_id' AND derivation_id=support->>'derivation_id';
  IF NOT FOUND OR NOT ops.ddo_use_valid(selected,boundary) THEN RETURN false; END IF;
 END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_population_producer_context(pop ops.data_population) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('operation_id',r.operation_id,'subject',r.subject,'original_source',r.original_source,'analyzed_scope',r.analyzed_scope)
 FROM ops.data_derivation episode JOIN ops.data_request r ON r.id=episode.request_id
 WHERE episode.id=pop.evidence->>'derivation_id'
$$;

CREATE OR REPLACE FUNCTION ops.ddo_population_scope(pop ops.data_population) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT CASE WHEN pop.evidence ? 'selection' THEN jsonb_build_object(
 'operation_id',pop.evidence->'selection'->'operation_id','subject',pop.evidence->'selection'->'subject',
 'original_source',pop.evidence->'selection'->'original_source','analyzed_scope',pop.evidence->'selection'->'analyzed_scope')
 ELSE ops.ddo_population_producer_context(pop) END
$$;

CREATE OR REPLACE FUNCTION ops.ddo_population_valid(pop ops.data_population,boundary ops.data_demand_read DEFAULT NULL) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_use ops.demand_use; parent ops.data_population;
BEGIN
 IF pop.id IS NULL OR EXISTS(SELECT FROM ops.data_population newer WHERE newer.demand_id=pop.demand_id AND newer.name=pop.name AND ops.ddo_population_scope(newer)=ops.ddo_population_scope(pop) AND (newer.created_at,newer.id)>(pop.created_at,pop.id) AND (boundary.id IS NULL OR ops.ddo_read_visible(newer.created_at,newer.created_xid,boundary))) THEN RETURN false; END IF;
 IF pop.evidence ? 'selection' THEN
 SELECT * INTO parent FROM ops.data_population WHERE id=pop.evidence->'selection'->>'parent_population_id' AND demand_id=pop.demand_id;
 IF parent.id IS NULL OR parent.id=pop.id OR NOT ops.ddo_population_valid(parent,boundary) THEN RETURN false; END IF;
 END IF;
 SELECT * INTO source_use FROM ops.demand_use u WHERE u.id=pop.evidence->>'admission_use_id' AND u.demand_id=pop.demand_id AND u.derivation_id=pop.evidence->>'derivation_id';
 RETURN FOUND AND ops.ddo_use_valid(source_use,boundary);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_support_available(r ops.data_request,support jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE item jsonb; episode ops.data_derivation; source_request ops.data_request; selected ops.demand_use;
BEGIN
 IF jsonb_typeof(support) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'support manifest must be array'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(support) LOOP
 PERFORM ops.ddo_fields(item,ARRAY['derivation_id','role','position'],ARRAY['admission_use_id']);
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=item->>'derivation_id';
 SELECT * INTO STRICT source_request FROM ops.data_request WHERE id=episode.request_id;
 IF source_request.project_id IS DISTINCT FROM r.project_id THEN RAISE EXCEPTION 'support outside project custody'; END IF;
 IF source_request.original_source IS DISTINCT FROM r.original_source AND NOT EXISTS(
 SELECT FROM sem.data_operation_definition def CROSS JOIN LATERAL jsonb_array_elements(def.input_roles) roledef
 CROSS JOIN LATERAL jsonb_array_elements(r.binding->'inputs') input
 JOIN kb.data_product product ON product.id=input->>'product_id'
 LEFT JOIN kb.data_product_member member ON member.product_id=product.id AND member.member_id=input->>'member_id'
 WHERE def.release_id=r.release_id AND def.operation_id=r.operation_id AND roledef->>'name'=input->>'role'
 AND (item->>'role'=input->>'role' OR EXISTS(SELECT FROM jsonb_array_elements(r.binding->'populations') reference JOIN ops.data_population pop ON pop.id=reference->>'population_id' WHERE reference->>'role'=input->>'role' AND item->>'role'='population:'||pop.name AND pop.evidence->>'derivation_id'=episode.id))
 AND EXISTS(SELECT FROM ops.data_derivation_output output WHERE output.derivation_id=episode.id AND output.product_id=product.id AND (output.member_id IS NULL OR output.member_id=input->>'member_id'))
 AND ops.ddo_binding_source(roledef,jsonb_build_object('product',product.id,'member',member.member_id,'subject',coalesce(member.subject,product.subject),'original_source',product.original_source,'analyzed_scope',coalesce(member.analyzed_scope,product.analyzed_scope),'meaning_body',coalesce(member.body,product.canonical_body)),r.original_source,coalesce(data.ddo_json(data.ddo_field(r.binding->'parameters','source_sets')),'{}'))
 ) THEN RAISE EXCEPTION 'foreign support outside exact frozen source-set custody'; END IF;
 IF item->>'admission_use_id' IS NULL THEN
 IF NOT ops.ddo_support_valid(episode.id) THEN RETURN false; END IF;
 ELSE
 SELECT * INTO selected FROM ops.demand_use WHERE id=item->>'admission_use_id' AND derivation_id=episode.id;
 IF NOT FOUND OR NOT ops.ddo_use_valid(selected) THEN RETURN false; END IF;
 END IF;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_assert_support(r ops.data_request,support jsonb) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT ops.ddo_support_available(r,support) THEN RAISE EXCEPTION 'support is unavailable or revoked'; END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_completion_state(def sem.data_operation_definition,outcome text) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE transitions jsonb; result text; n integer;
BEGIN
 IF NOT def.support_contract->'outcomes' ? outcome THEN RAISE EXCEPTION 'completion outcome is outside admitted operation contract'; END IF;
 SELECT count(*),min(t->>'after') INTO n,result FROM jsonb_array_elements(coalesce(def.support_contract->'transitions','[]')) t
 WHERE t->>'dimension'='completion' AND t->>'outcome'=outcome AND t->>'before'='pending'
 AND t->>'after' IN ('success','empty','failed') AND coalesce(t->'effects','[]')='[]'::jsonb;
 IF n=1 THEN RETURN result; END IF;
 IF n=0 AND outcome IN ('success','empty','failed') THEN RETURN outcome; END IF;
 RAISE EXCEPTION 'completion requires one declared terminal-state mapping';
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_authorize_request(r ops.data_request) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM ops.ddo_authorize(kind.universe) FROM sem.data_operation_definition operation
 CROSS JOIN LATERAL jsonb_array_elements(operation.input_roles||operation.output_roles) role
 JOIN sem.data_kind_contract kind ON kind.kind_contract=role->>'kind_contract'
 WHERE operation.release_id=r.release_id AND operation.operation_id=r.operation_id;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_demand_active(demand text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT NOT EXISTS(SELECT FROM ops.data_demand_cancellation c WHERE c.demand_id=demand)
$$;
CREATE OR REPLACE FUNCTION ops.ddo_require_active_demand(demand text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM 1 FROM ops.data_demand WHERE id=demand FOR SHARE;
 IF NOT ops.ddo_demand_active(demand) THEN RAISE EXCEPTION 'data demand is cancelled'; END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_request_useful(r ops.data_request) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT EXISTS(SELECT FROM ops.demand_use u WHERE u.request_id=r.id AND u.generation=r.generation
 AND u.fate='attached' AND ops.ddo_demand_active(u.demand_id)
 AND NOT EXISTS(SELECT FROM ops.demand_use later WHERE later.obligation_id=u.obligation_id
 AND (later.created_at,later.id)>(u.created_at,u.id)))
$$;

CREATE OR REPLACE FUNCTION ops.ddo_claim(r ops.data_request,p jsonb) RETURNS ops.task
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task;
BEGIN
 PERFORM ops.ddo_authorize_request(r);
 IF NOT ops.ddo_request_useful(r) THEN RAISE EXCEPTION 'data request has no attached demand interest'; END IF;
 SELECT * INTO STRICT t FROM ops.task WHERE id=r.live_task_id FOR UPDATE;
 IF (t.data_request_id,t.data_generation,t.id,t.attempt,t.claimed_by) IS DISTINCT FROM
 (r.id,r.generation,(p->>'task_id')::bigint,(p->>'attempt')::integer,p->>'holder')
 OR r.generation IS DISTINCT FROM (p->>'generation')::integer
 OR t.status IS DISTINCT FROM 'running' OR t.lease_until IS NULL OR t.lease_until<=clock_timestamp() THEN
 RAISE EXCEPTION 'stale data task attempt fence' USING ERRCODE='23514'; END IF;
 RETURN t;
END $$;

CREATE OR REPLACE FUNCTION ops.register_data_demand(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; key text; d ops.data_demand;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['project_id','release_id','runtime_id','root','selection','strength']);
 IF NOT EXISTS(SELECT FROM data.project WHERE project_id=p->>'project_id') OR
 NOT EXISTS(SELECT FROM sem.data_operation_definition WHERE release_id=p->>'release_id') OR
 p->>'strength' NOT IN ('value','episode','independent') THEN RAISE EXCEPTION 'unadmitted demand/project/strength'; END IF;
 IF p->'root' IS DISTINCT FROM p->'selection'->'roots'
 OR NOT EXISTS(SELECT FROM sem.artifact a WHERE a.release_id=p->>'release_id' AND a.artifact_name='data_operations.json' AND a.content_digest=p->'selection'->>'model')
 OR EXISTS(SELECT FROM jsonb_array_elements(p->'selection'->'operations') selected WHERE NOT EXISTS(
 SELECT FROM sem.artifact a CROSS JOIN LATERAL jsonb_array_elements(convert_from(a.content,'UTF8')::jsonb->'operations') op
 WHERE a.release_id=p->>'release_id' AND a.artifact_name='data_operation_native_definitions.json'
 AND op->>'operation_id'=selected->>'operation' AND op->>'recipe'=selected->>'recipe'
 AND op->>'definition'=selected->>'definition' AND op->>'eligibility'=selected->>'eligibility')) THEN RAISE EXCEPTION 'demand differs from authenticated effective model/selection'; END IF;
 PERFORM ops.ddo_authorize(kind.universe) FROM jsonb_array_elements(p->'selection'->'operations') selected JOIN sem.data_operation_definition operation ON operation.release_id=p->>'release_id' AND operation.operation_id=selected->>'operation' CROSS JOIN LATERAL jsonb_array_elements(operation.input_roles||operation.output_roles) role JOIN sem.data_kind_contract kind ON kind.kind_contract=role->>'kind_contract';
 IF p->>'strength'='independent' THEN RAISE EXCEPTION 'independent strength requires declared distinct-episode replicate obligations' USING ERRCODE='23514'; END IF;
 IF p->>'strength'='episode' AND EXISTS(SELECT FROM sem.data_operation_definition op
 CROSS JOIN LATERAL jsonb_array_elements(op.input_roles) role
 WHERE op.release_id=p->>'release_id' AND EXISTS(SELECT FROM jsonb_array_elements(p->'selection'->'operations') sel WHERE sel->>'operation'=op.operation_id)
 AND NOT (role->'identity_requirements' ? 'episode')) THEN RAISE EXCEPTION 'episode strength requires episode-qualified input contracts'; END IF;
 PERFORM ops.ddo_validate_source_sets(coalesce(p->'selection'->'source_sets','{}'),p->>'project_id');
 IF EXISTS(SELECT FROM jsonb_each(coalesce(p->'selection'->'source_sets','{}')) named WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(p->'selection'->'operations') selected JOIN sem.data_operation_definition def ON def.release_id=p->>'release_id' AND def.operation_id=selected->>'operation' CROSS JOIN LATERAL jsonb_array_elements(def.input_roles) roledef WHERE roledef->'support'->>'source_set'=named.key))
 OR EXISTS(SELECT FROM jsonb_array_elements(p->'selection'->'operations') selected JOIN sem.data_operation_definition def ON def.release_id=p->>'release_id' AND def.operation_id=selected->>'operation' CROSS JOIN LATERAL jsonb_array_elements(def.input_roles) roledef WHERE roledef->'support'->>'source_set' IS NOT NULL AND NOT coalesce(p->'selection'->'source_sets','{}') ? (roledef->'support'->>'source_set')) THEN RAISE EXCEPTION 'frozen source sets differ from admitted selected role policies'; END IF;
 PERFORM sem.require_runtime_binding(p->>'release_id',p->>'runtime_id');
 key:='demand:'||ops.ddo_digest(p);
 INSERT INTO ops.data_trust_scope(scope,project_id,epoch) SELECT DISTINCT ops.ddo_scope(p->>'project_id',root->>'original_source'),p->>'project_id',0 FROM (SELECT value FROM jsonb_array_elements(p->'root') UNION ALL SELECT entry FROM jsonb_each(coalesce(p->'selection'->'source_sets','{}')) named CROSS JOIN LATERAL jsonb_array_elements(named.value) entry) roots(root) ORDER BY 1 ON CONFLICT DO NOTHING;
 INSERT INTO ops.data_demand VALUES(key,p->>'project_id',p->>'release_id',p->>'runtime_id',p->'root',p->'selection',p->>'strength',clock_timestamp()) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=key;
 RETURN jsonb_build_object('payload',jsonb_build_object('demand_id',d.id,'selection',d.selection)||CASE WHEN ops.ddo_demand_active(d.id) THEN '{}'::jsonb ELSE jsonb_build_object('state','cancelled') END);
END $$;
CREATE OR REPLACE FUNCTION ops.cancel_data_demand(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; d ops.data_demand; r ops.data_request; o ops.data_obligation;
 old ops.demand_use; cancellation ops.data_demand_cancellation; scope_key text;
 requests jsonb:='[]'; key text; generation_row record;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['demand_id','reason']);
 IF nullif(p->>'reason','') IS NULL THEN RAISE EXCEPTION 'cancellation requires a reason'; END IF;
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p->>'demand_id';
 PERFORM ops.ddo_authorize(kind.universe) FROM jsonb_array_elements(d.selection->'operations') selected
 JOIN sem.data_operation_definition operation ON operation.release_id=d.release_id AND operation.operation_id=selected->>'operation'
 CROSS JOIN LATERAL jsonb_array_elements(operation.input_roles||operation.output_roles) role
 JOIN sem.data_kind_contract kind ON kind.kind_contract=role->>'kind_contract';
 -- Stable trust -> demand -> request -> task ordering. Demand SHARE guards all
 -- creation/attachment paths; no new request can enter this demand during cancellation.
 FOR scope_key IN SELECT DISTINCT ops.ddo_scope(d.project_id,root->>'original_source')
 FROM jsonb_array_elements(d.root) root ORDER BY 1 LOOP
 PERFORM 1 FROM ops.data_trust_scope WHERE scope=scope_key FOR UPDATE;
 END LOOP;
 PERFORM 1 FROM ops.data_demand WHERE id=d.id FOR UPDATE;
 PERFORM 1 FROM ops.data_request req WHERE EXISTS(SELECT FROM ops.demand_use u WHERE u.demand_id=d.id AND u.request_id=req.id) ORDER BY req.id FOR UPDATE;
 INSERT INTO ops.data_demand_cancellation VALUES(d.id,p->>'reason',clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT cancellation FROM ops.data_demand_cancellation WHERE demand_id=d.id;
 FOR o IN SELECT obligation.* FROM ops.data_obligation obligation WHERE obligation.demand_id=d.id ORDER BY obligation.id LOOP
 SELECT * INTO old FROM ops.demand_use u WHERE u.obligation_id=o.id ORDER BY u.created_at DESC,u.id DESC LIMIT 1;
 -- Settled evidence stays selected historical evidence. Cancellation detaches only unfinished work.
 IF old.id IS NULL OR old.fate NOT IN ('fulfilled','closed','cancelled','failed','not-applicable') THEN
 key:='use:'||ops.ddo_digest(jsonb_build_array('cancel-demand',d.id,o.id));
 INSERT INTO ops.demand_use VALUES(key,d.id,o.id,'cancelled',old.request_id,old.generation,NULL,
 coalesce(old.selection,'{}'::jsonb),coalesce(old.trust_snapshot,'{}'::jsonb),clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 END IF;
 END LOOP;
 -- Last-interest detachment permanently fences the old producer. Advancing the
 -- request does not claim the old task/process stopped; keep its history intact.
 FOR r IN SELECT req.* FROM ops.data_request req WHERE EXISTS(SELECT FROM ops.demand_use u WHERE u.demand_id=d.id AND u.request_id=req.id) ORDER BY req.id LOOP
 IF NOT ops.ddo_request_useful(r) AND r.live_task_id IS NOT NULL THEN
 PERFORM 1 FROM ops.task WHERE id=r.live_task_id FOR UPDATE;
 IF EXISTS(SELECT FROM ops.task WHERE id=r.live_task_id AND status IN ('pending','running')) THEN
 UPDATE ops.data_request SET generation=generation+1,live_task_id=NULL WHERE id=r.id;
 END IF;
 END IF;
 END LOOP;
 -- Report exact attached generations, never a newer generation belonging only
 -- to another demand. Physical owners correlate cancellation by this same fence.
 FOR generation_row IN SELECT DISTINCT u.request_id,u.generation,g.task_id
 FROM ops.demand_use u JOIN ops.data_request_generation g
 ON (g.request_id,g.generation)=(u.request_id,u.generation)
 WHERE u.demand_id=d.id ORDER BY u.request_id,u.generation LOOP
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=generation_row.request_id;
 r.generation:=generation_row.generation;
 r.live_task_id:=generation_row.task_id;
 requests:=requests||jsonb_build_array(jsonb_build_object('request_id',r.id,'generation',r.generation,'task_id',r.live_task_id,
 'interest',CASE WHEN ops.ddo_request_useful(r) THEN 'shared' ELSE 'orphaned' END,'physical_retirement','unconfirmed'));
 END LOOP;
 RETURN jsonb_build_object('payload',jsonb_build_object('demand_id',d.id,'state','cancelled','reason',cancellation.reason,'requests',requests));
END $$;

CREATE OR REPLACE FUNCTION ops.expand_data_obligation(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; d ops.data_demand; key text; population ops.data_population; allowed boolean;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['demand_id','operation_id','subject','original_source','analyzed_scope','parameters'],ARRAY['population_id']);
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p->>'demand_id';
 PERFORM ops.ddo_require_active_demand(d.id);
 IF NOT EXISTS(SELECT FROM sem.data_operation_definition WHERE release_id=d.release_id AND operation_id=p->>'operation_id')
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') s WHERE s->>'operation'=p->>'operation_id' AND s->'parameters'=p->'parameters')
 OR nullif(p->>'subject','') IS NULL OR nullif(p->>'original_source','') IS NULL THEN RAISE EXCEPTION 'obligation differs from frozen operation/parameters'; END IF;
 IF p ? 'population_id' THEN
 SELECT * INTO STRICT population FROM ops.data_population WHERE id=p->>'population_id' AND demand_id=d.id;
 IF NOT ops.ddo_population_valid(population) THEN RAISE EXCEPTION 'discovery population is not currently admitted'; END IF;
 SELECT EXISTS(WITH RECURSIVE allowed_operations(id) AS (
 SELECT rel->>'target' FROM jsonb_array_elements(d.selection->'discovery') rel WHERE rel->>'population'=population.name
 UNION SELECT dep.value FROM allowed_operations a JOIN LATERAL jsonb_array_elements(d.selection->'operations') op ON op->>'operation'=a.id CROSS JOIN LATERAL jsonb_array_elements_text(op->'dependencies') dep(value)) SELECT FROM allowed_operations WHERE id=p->>'operation_id') INTO allowed;
 allowed:=allowed AND EXISTS(SELECT FROM jsonb_array_elements(population.members) m WHERE (m->>'subject',m->>'original_source')=(p->>'subject',p->>'original_source') AND m->'analyzed_scope'=p->'analyzed_scope');
 ELSE
 allowed:=d.selection->'root_operations' ? (p->>'operation_id') AND EXISTS(SELECT FROM jsonb_array_elements(d.root) m WHERE (m->>'subject',m->>'original_source')=(p->>'subject',p->>'original_source') AND m->'analyzed_scope'=p->'analyzed_scope');
 END IF;
 IF NOT coalesce(allowed,false) THEN RAISE EXCEPTION 'obligation is outside native frozen root/discovery scope'; END IF;
 key:='obligation:'||ops.ddo_digest(p-'population_id');
 INSERT INTO ops.data_obligation VALUES(key,d.id,p->>'operation_id',p->>'subject',p->>'original_source',p->'analyzed_scope',p->'parameters',clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 RETURN jsonb_build_object('payload',jsonb_build_object('obligation_id',key));
END $$;
CREATE OR REPLACE FUNCTION ops.record_data_fate(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; o ops.data_obligation; key text;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['obligation_id','fate','selection'],ARRAY['request_id','generation','derivation_id','trust_snapshot']);
 SELECT * INTO STRICT o FROM ops.data_obligation WHERE id=p->>'obligation_id';
 PERFORM ops.ddo_require_active_demand(o.demand_id);
 IF p->>'fate' NOT IN ('known-absent','unknown','unavailable','invalid','closed','awaiting-discovery','awaiting-inputs','awaiting-population','not-applicable','failed','cancelled','partial') THEN RAISE EXCEPTION 'native ownership required for fulfillment/attachment'; END IF;
 key:='use:'||ops.ddo_digest(p);
 INSERT INTO ops.demand_use VALUES(key,o.demand_id,o.id,p->>'fate',NULL,NULL,NULL,p->'selection','{}',clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 RETURN jsonb_build_object('payload',jsonb_build_object('use_id',key,'fate',p->>'fate'));
END $$;
CREATE OR REPLACE FUNCTION ops.close_data_population(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; d ops.data_demand; x kb.data_product; producer ops.data_derivation; r ops.data_request; rel jsonb; members jsonb; complete boolean; evidence jsonb; key text; old ops.data_population; snapshot jsonb; semantic_key text; source_use ops.demand_use;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['demand_id','name','product_id','derivation_id','member_role']);
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p->>'demand_id';
 SELECT * INTO STRICT producer FROM ops.data_derivation WHERE id=p->>'derivation_id';
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=producer.request_id;
 SELECT * INTO STRICT x FROM kb.data_product WHERE id=p->>'product_id';
 snapshot:=ops.ddo_lock_support(r.project_id,r.original_source,jsonb_build_array(jsonb_build_object('derivation_id',producer.id)));
 PERFORM ops.ddo_require_active_demand(d.id);
 SELECT value INTO STRICT rel FROM jsonb_array_elements(d.selection->'discovery') value WHERE value->>'population'=p->>'name' AND value->>'producer'=r.operation_id AND value->>'output_role'=p->>'member_role';
 IF x.project_id<>d.project_id OR r.project_id<>d.project_id OR r.release_id<>d.release_id
 OR NOT EXISTS(SELECT FROM ops.demand_use u WHERE u.demand_id=d.id AND u.derivation_id=producer.id AND ops.ddo_use_valid(u)) OR NOT EXISTS(SELECT FROM sem.data_operation_definition op WHERE op.release_id=d.release_id AND op.operation_id=r.operation_id AND op.profile='discovery')
 OR NOT EXISTS(SELECT FROM ops.data_derivation_output outp WHERE outp.derivation_id=producer.id AND outp.product_id=x.id AND outp.role=p->>'member_role')
 OR NOT EXISTS(SELECT FROM ops.demand_use u WHERE u.demand_id=d.id AND u.derivation_id=producer.id AND u.fate='fulfilled') THEN RAISE EXCEPTION 'population lacks admitted declared discovery output'; END IF;
 PERFORM ops.ddo_authorize(k.universe) FROM sem.data_kind_contract k WHERE k.kind_contract=x.kind_contract;
 IF jsonb_typeof(data.ddo_json(data.ddo_field(x.canonical_body,'complete'))) IS DISTINCT FROM 'boolean' THEN RAISE EXCEPTION 'discovery closure must declare complete boolean'; END IF;
 complete:=(data.ddo_json(data.ddo_field(x.canonical_body,'complete')) #>> '{}')::boolean;
 IF EXISTS(SELECT FROM kb.data_product_member m WHERE m.product_id=x.id AND (nullif(m.subject,'') IS NULL OR m.original_source IS DISTINCT FROM x.original_source OR m.analyzed_scope IS NULL)) THEN RAISE EXCEPTION 'discovery member lacks qualified subject/source/scope'; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('member_id',m.member_id,'subject',m.subject,'original_source',m.original_source,'analyzed_scope',m.analyzed_scope) ORDER BY m.member_id),'[]') INTO members FROM kb.data_product_member m WHERE m.product_id=x.id;
 IF EXISTS(SELECT FROM jsonb_array_elements(members) m GROUP BY m->>'subject' HAVING count(*)<>1) THEN RAISE EXCEPTION 'discovery has ambiguous duplicate subjects'; END IF;
 SELECT * INTO STRICT source_use FROM ops.demand_use u WHERE u.demand_id=d.id AND u.derivation_id=producer.id AND ops.ddo_use_valid(u) ORDER BY u.created_at DESC,u.id DESC LIMIT 1;
 semantic_key:='population-value:'||ops.ddo_digest(jsonb_build_object('product',x.id,'member_role',p->>'member_role','members',members,'complete',complete));
 evidence:=jsonb_build_object('product_id',x.id,'derivation_id',producer.id,'member_role',p->>'member_role','admission_use_id',source_use.id,'trust_snapshot',snapshot,'producer_context',jsonb_build_object('operation_id',r.operation_id,'subject',r.subject,'original_source',r.original_source,'analyzed_scope',r.analyzed_scope));
 key:='population:'||ops.ddo_digest(jsonb_build_array(d.id,p->>'name',semantic_key,evidence));
 evidence:=evidence||jsonb_build_object('population_id',key);
 PERFORM 1 FROM ops.data_demand WHERE id=d.id FOR UPDATE;
 INSERT INTO ops.data_population (id,demand_id,semantic_key,name,members,complete,evidence,created_at,created_xid) VALUES(key,d.id,semantic_key,p->>'name',members,complete,evidence,clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT old FROM ops.data_population WHERE id=key;
 IF NOT ops.ddo_population_valid(old) THEN RAISE EXCEPTION 'population witness is historical or no longer admitted'; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('population_id',key,'semantic_key',semantic_key,'name',old.name,'complete',old.complete,'members',old.members,'evidence',old.evidence));
END $$;
CREATE OR REPLACE FUNCTION data.ddo_field(v jsonb,k text) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$ SELECT value->1 FROM jsonb_array_elements(v->1) WHERE value->>0=k $$;
CREATE OR REPLACE FUNCTION ops.ddo_validate_binding(r ops.data_request,o ops.data_obligation,def sem.data_operation_definition,b jsonb,meaning jsonb,replicate text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE raw jsonb; roledef jsonb; rv jsonb; mv jsonb; item jsonb; x kb.data_product; member_body jsonb; expected jsonb; pop ops.data_population; d ops.data_demand; witness jsonb; role_meaning jsonb; state text; reference jsonb; lexical_alternative text;
BEGIN
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=o.demand_id;
 IF b->>'inference' IS DISTINCT FROM d.selection->>'inference'
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') sel WHERE sel->>'operation'=o.operation_id AND sel->'parameter_meaning'=data.ddo_normalize(data.ddo_field(b->'parameters','parameters')))
 OR data.ddo_field(b->'parameters','replicate') IS DISTINCT FROM (CASE WHEN replicate IS NULL THEN jsonb_build_array('null') ELSE jsonb_build_array('string',replicate) END)
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') s WHERE s->>'operation'=o.operation_id AND s->>'recipe'=def.recipe AND s->>'replicate' IS NOT DISTINCT FROM replicate) THEN RAISE EXCEPTION 'request differs from frozen inference/parameters/replicate/recipe'; END IF;
 IF NOT EXISTS(SELECT FROM ops.data_demand_read acquired WHERE acquired.id=b->>'read_id' AND acquired.demand_id=d.id) THEN RAISE EXCEPTION 'binding lacks exact native read acquisition'; END IF;
 expected:=(SELECT coalesce(jsonb_object_agg(named.key,named.value),'{}') FROM jsonb_each(coalesce(d.selection->'source_sets','{}')) named WHERE EXISTS(SELECT FROM jsonb_array_elements(def.input_roles) AS role_record(value) WHERE role_record.value->'support'->>'source_set'=named.key));
 IF expected<>'{}'::jsonb THEN
 IF data.ddo_json(data.ddo_field(b->'parameters','source_sets')) IS DISTINCT FROM expected THEN RAISE EXCEPTION 'request source-set meaning differs from exact frozen declaration'; END IF;
 ELSIF data.ddo_field(b->'parameters','source_sets') IS NOT NULL THEN RAISE EXCEPTION 'undeclared request source-set meaning'; END IF;
 raw:=data.ddo_json(b->'request_inputs');
 IF jsonb_typeof(raw)<>'object' OR EXISTS(SELECT FROM jsonb_object_keys(raw) name WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(def.input_roles) f WHERE f->>'name'=name)) THEN RAISE EXCEPTION 'request input roles differ from admitted definition'; END IF;
 FOR roledef IN SELECT value FROM jsonb_array_elements(def.input_roles) LOOP
 IF roledef->'identity_requirements' ? 'provider' THEN RAISE EXCEPTION 'provider profile identity is not yet materialized for this native contract'; END IF;
 role_meaning:=data.ddo_field(b->'request_inputs',roledef->>'name');
 rv:=raw->(roledef->>'name');
 IF rv IS NULL THEN RAISE EXCEPTION 'missing request role'; END IF;
 state:=data.ddo_field(role_meaning,'value')->>0;
 IF state NOT IN ('present','known-absent') OR (state='known-absent' AND roledef->>'presence'='required') THEN RAISE EXCEPTION 'incomplete input cannot attach runnable request'; END IF;
 witness:=rv->'population_witness';
 pop:=NULL;
 SELECT value INTO reference FROM jsonb_array_elements(b->'populations') ref WHERE ref->>'role'=roledef->>'name';
 IF witness IS NOT NULL AND witness<>'null'::jsonb AND witness ? 'identity' THEN
 IF reference IS NULL THEN RAISE EXCEPTION 'population witness lacks authenticated native receipt reference'; END IF;
 SELECT * INTO STRICT pop FROM ops.data_population WHERE id=reference->>'population_id' AND demand_id=d.id AND name=reference->>'name';
 IF NOT ops.ddo_population_valid(pop) THEN RAISE EXCEPTION 'population witness is historical or revoked'; END IF;
 IF pop.evidence ? 'selection' AND (pop.evidence->'selection'->>'obligation_id',pop.evidence->'selection'->>'operation_id',pop.evidence->'selection'->>'subject',pop.evidence->'selection'->>'original_source') IS DISTINCT FROM (o.id,o.operation_id,o.subject,o.original_source) THEN RAISE EXCEPTION 'selected population belongs to another binding context'; END IF;
 expected:=ops.ddo_binding_population_meaning(jsonb_build_object('identity',pop.semantic_key,'complete',pop.complete,'members',(SELECT coalesce(jsonb_agg(value->'member_id' ORDER BY n),'[]') FROM jsonb_array_elements(pop.members) WITH ORDINALITY entry(value,n)),'evidence',pop.evidence),roledef->'identity_requirements' ? 'episode');
 IF witness IS DISTINCT FROM expected THEN RAISE EXCEPTION 'population semantic witness differs from native closure value'; END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(b->'support') selected WHERE selected->>'role'='population:'||pop.name AND selected->>'derivation_id'=pop.evidence->>'derivation_id' AND selected->>'admission_use_id'=pop.evidence->>'admission_use_id') THEN RAISE EXCEPTION 'population closure lacks authentic derivation support'; END IF;
 ELSIF reference IS NOT NULL THEN RAISE EXCEPTION 'unexpected native population receipt for unwitnessed role';
 END IF;
 IF state='known-absent' AND EXISTS(SELECT FROM jsonb_array_elements(b->'inputs') i WHERE i->>'role'=roledef->>'name') THEN RAISE EXCEPTION 'absent role cannot carry native inputs'; END IF;
 IF state='known-absent' AND pop.id IS NOT NULL AND NOT pop.complete THEN RAISE EXCEPTION 'open population cannot establish absence'; END IF;
 IF roledef->>'presence'='alternative' AND NOT (roledef->'alternatives' ? (rv->>'selected_alternative')) THEN RAISE EXCEPTION 'selected alternative outside declared choice'; END IF;
 IF state='present' THEN
 IF jsonb_typeof(rv->'value')<>'array' THEN RAISE EXCEPTION 'present role has no member collection'; END IF;
 FOR mv IN SELECT value FROM jsonb_array_elements(rv->'value') LOOP
 IF roledef->>'collection'<>'sequence' AND mv->'position' IS DISTINCT FROM 'null'::jsonb THEN RAISE EXCEPTION 'nonsequence position is not a semantic determinant'; END IF;
 SELECT value INTO STRICT item FROM jsonb_array_elements(b->'inputs') i WHERE i->>'role'=roledef->>'name' AND i->>'product_id'=mv->>'product' AND i->>'member_id' IS NOT DISTINCT FROM mv->>'member'
 AND i->>'multiplicity'=mv->>'multiplicity' AND (roledef->>'collection'<>'sequence' OR i->>'position' IS NOT DISTINCT FROM mv->>'position')
 AND (NOT roledef->'identity_requirements' ? 'episode' OR mv->'support_episodes'=(SELECT coalesce(jsonb_agg(episode ORDER BY episode),'[]') FROM (SELECT DISTINCT support->>'derivation_id' episode FROM jsonb_array_elements(b->'support') support WHERE support->>'role'=roledef->>'name' AND support->>'position' IS NOT DISTINCT FROM i->>'position') selected))
 ORDER BY (i->>'position')::integer LIMIT 1;
 IF (SELECT count(*) FROM jsonb_array_elements(rv->'value') other WHERE (other->>'product',other->>'member',other->>'multiplicity') IS NOT DISTINCT FROM (mv->>'product',mv->>'member',mv->>'multiplicity') AND (roledef->>'collection'<>'sequence' OR other->>'position' IS NOT DISTINCT FROM mv->>'position') AND (NOT roledef->'identity_requirements' ? 'episode' OR other->'support_episodes'=mv->'support_episodes')) <>
 (SELECT count(*) FROM jsonb_array_elements(b->'inputs') actual WHERE actual->>'role'=roledef->>'name' AND (actual->>'product_id',actual->>'member_id',actual->>'multiplicity') IS NOT DISTINCT FROM (mv->>'product',mv->>'member',mv->>'multiplicity') AND (roledef->>'collection'<>'sequence' OR actual->>'position' IS NOT DISTINCT FROM mv->>'position') AND (NOT roledef->'identity_requirements' ? 'episode' OR mv->'support_episodes'=(SELECT coalesce(jsonb_agg(episode ORDER BY episode),'[]') FROM (SELECT DISTINCT support->>'derivation_id' episode FROM jsonb_array_elements(b->'support') support WHERE support->>'role'=roledef->>'name' AND support->>'position' IS NOT DISTINCT FROM actual->>'position') selected))) THEN RAISE EXCEPTION 'semantic member occurrence counts differ from native manifest'; END IF;
 SELECT * INTO STRICT x FROM kb.data_product WHERE id=item->>'product_id';
 PERFORM ops.ddo_authorize(kind.universe) FROM sem.data_kind_contract kind WHERE kind.kind_contract=x.kind_contract;
 SELECT body INTO member_body FROM kb.data_product_member WHERE product_id=x.id AND member_id=item->>'member_id';
 IF (mv->>'kind',mv->>'subject',mv->>'original_source',mv->>'multiplicity') IS DISTINCT FROM (coalesce((SELECT member.kind_contract FROM kb.data_product_member member WHERE member.product_id=x.id AND member.member_id=item->>'member_id'),x.kind_contract),coalesce((SELECT member.subject FROM kb.data_product_member member WHERE member.product_id=x.id AND member.member_id=item->>'member_id'),x.subject),x.original_source,item->>'multiplicity') OR mv->'analyzed_scope' IS DISTINCT FROM coalesce((SELECT member.analyzed_scope FROM kb.data_product_member member WHERE member.product_id=x.id AND member.member_id=item->>'member_id'),x.analyzed_scope) THEN RAISE EXCEPTION 'semantic request member differs from native product/member'; END IF;
 SELECT coalesce(jsonb_agg(to_jsonb(c)-'product_id'-'member_id' ORDER BY c.ordinal),'[]') INTO expected FROM kb.data_member_coverage c WHERE c.product_id=x.id AND c.member_id=item->>'member_id';
 IF mv->'coverage' IS DISTINCT FROM expected THEN RAISE EXCEPTION 'semantic input coverage differs from native projection'; END IF;
 IF roledef->>'presence'='alternative' OR roledef->'identity_requirements' ? 'alternative' THEN
 SELECT CASE WHEN count(DISTINCT source_request.operation_id)=1 THEN min(source_request.operation_id) ELSE NULL END INTO lexical_alternative
 FROM jsonb_array_elements(b->'support') selected JOIN ops.data_derivation source_episode ON source_episode.id=selected->>'derivation_id' JOIN ops.data_request source_request ON source_request.id=source_episode.request_id
 WHERE selected->>'role'=roledef->>'name' AND selected->>'position' IS NOT DISTINCT FROM item->>'position'
 AND EXISTS(SELECT FROM ops.data_derivation_output produced WHERE produced.derivation_id=source_episode.id AND produced.product_id=item->>'product_id');
 IF lexical_alternative IS NULL OR (roledef->>'presence'='alternative' AND rv->>'selected_alternative' IS DISTINCT FROM lexical_alternative)
 OR (roledef->'identity_requirements' ? 'alternative' AND mv->>'alternative' IS DISTINCT FROM lexical_alternative) THEN RAISE EXCEPTION 'selected alternative differs from actual producing operation'; END IF;
 END IF;
 IF roledef->'identity_requirements' ? 'episode' THEN
 SELECT coalesce(jsonb_agg(id ORDER BY id),'[]') INTO expected FROM (SELECT DISTINCT z->>'derivation_id' id FROM jsonb_array_elements(b->'support') z WHERE z->>'role'=roledef->>'name' AND z->>'position' IS NOT DISTINCT FROM item->>'position') q;
 IF expected='[]'::jsonb OR mv->'support_episodes' IS DISTINCT FROM expected THEN RAISE EXCEPTION 'required episode identity differs from selected authentic support'; END IF;
 END IF;
 END LOOP;
 IF jsonb_array_length(rv->'value')<>(SELECT count(*) FROM jsonb_array_elements(b->'inputs') i WHERE i->>'role'=roledef->>'name') THEN RAISE EXCEPTION 'native input manifest differs from semantic request members'; END IF;
 END IF;
 END LOOP;
END $$;

CREATE OR REPLACE FUNCTION ops.attach_data_request(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; o ops.data_obligation; d ops.data_demand; def sem.data_operation_definition;
 r ops.data_request; key text; snapshot jsonb; episode text; task bigint; usekey text; item jsonb; declared jsonb; cnt bigint; retained_id text; retained ops.data_completion_intent; current_task ops.task; invalid_retained boolean;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['obligation_id','request_meaning','binding','replicate'],ARRAY['rebind_derivation','request_key']);
 IF p->'request_meaning'->>0='ddo' THEN
 IF p->'request_meaning'->>1<>'semantic-request' OR p->'request_meaning'->>2<>'1' OR jsonb_array_length(p->'request_meaning')<>4 THEN RAISE EXCEPTION 'invalid semantic request frame'; END IF;
 p:=jsonb_set(p,'{request_meaning}',p->'request_meaning'->3); END IF;
 SELECT * INTO STRICT o FROM ops.data_obligation WHERE id=p->>'obligation_id';
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=o.demand_id;
 SELECT * INTO STRICT def FROM sem.data_operation_definition WHERE release_id=d.release_id AND operation_id=o.operation_id;
 PERFORM ops.ddo_authorize(kind.universe) FROM jsonb_array_elements(def.input_roles||def.output_roles) role JOIN sem.data_kind_contract kind ON kind.kind_contract=role->>'kind_contract';
 IF def.profile NOT IN ('derivation','discovery') OR coalesce(def.support_contract->'effects','[]')<>'[]'::jsonb THEN RAISE EXCEPTION 'operation profile requires its own declared command/read execution contract'; END IF;
 PERFORM ops.ddo_fields(p->'binding',ARRAY['inputs','support','parameters','inference','request_inputs','populations','read_id']);
 IF data.ddo_field(p->'request_meaning','recipe') IS DISTINCT FROM jsonb_build_array('string',def.recipe)
 OR data.ddo_field(p->'request_meaning','subject') IS DISTINCT FROM jsonb_build_array('string',o.subject)
 OR data.ddo_field(p->'request_meaning','inputs') IS DISTINCT FROM data.ddo_normalize(p->'binding'->'request_inputs')
 OR data.ddo_field(p->'request_meaning','parameters') IS DISTINCT FROM data.ddo_normalize(p->'binding'->'parameters')
 OR data.ddo_field(p->'request_meaning','inference') IS DISTINCT FROM jsonb_build_array('string',p->'binding'->>'inference') THEN RAISE EXCEPTION 'request identity differs from compiled binding'; END IF;
 key:=data.ddo_identity('semantic-request',p->'request_meaning');
 IF p ? 'request_key' AND p->>'request_key'<>key THEN RAISE EXCEPTION 'request key differs from canonical meaning'; END IF;
 snapshot:=ops.ddo_lock_support(d.project_id,o.original_source,p->'binding'->'support');
 PERFORM ops.ddo_require_active_demand(d.id);
 -- INSERT waits for a concurrent winner. The following statement has a fresh READ COMMITTED
 -- snapshot before locking; a one-statement CTE would miss an uncommitted conflicting row.
 INSERT INTO ops.data_request VALUES(key,key,d.project_id,d.release_id,d.runtime_id,o.operation_id,def.recipe,o.subject,o.original_source,o.analyzed_scope,(p->'binding')||jsonb_build_object('execution_profile',d.selection->'execution_profile'),p->>'replicate',1,NULL) ON CONFLICT(request_key) DO NOTHING;
 SELECT * INTO STRICT r FROM ops.data_request WHERE request_key=key FOR UPDATE;
 IF (r.project_id,r.recipe,r.subject,r.original_source,r.replicate) IS DISTINCT FROM (d.project_id,def.recipe,o.subject,o.original_source,p->>'replicate')
 OR r.analyzed_scope IS DISTINCT FROM o.analyzed_scope THEN RAISE EXCEPTION 'request custody or contract mismatch'; END IF;
 PERFORM ops.ddo_assert_support(r,p->'binding'->'support');
 PERFORM ops.ddo_validate_binding(r,o,def,p->'binding',p->'request_meaning',p->>'replicate');
 PERFORM ops.ddo_require_binding(d.id,o.operation_id,o.subject,p->'request_meaning',p->'binding',snapshot);
 IF jsonb_typeof(p->'binding'->'inputs')<>'array' THEN RAISE EXCEPTION 'input manifest must be an array'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p->'binding'->'inputs') LOOP
 PERFORM ops.ddo_fields(item,ARRAY['role','position','multiplicity','product_id'],ARRAY['member_id','support_derivation_id']);
 SELECT value INTO declared FROM jsonb_array_elements(def.input_roles) WHERE value->>'name'=item->>'role';
 PERFORM ops.ddo_authorize(k.universe) FROM sem.data_kind_contract k WHERE k.kind_contract=declared->>'kind_contract';
 IF declared IS NULL OR NOT EXISTS(SELECT FROM kb.data_product x JOIN sem.data_kind_release kr ON kr.kind_contract=declared->>'kind_contract' AND kr.release_id=d.release_id
 WHERE x.id=item->>'product_id' AND x.project_id=d.project_id
 AND ops.ddo_binding_source(declared,jsonb_build_object('product',x.id,'member',item->>'member_id','subject',coalesce((SELECT member.subject FROM kb.data_product_member member WHERE member.product_id=x.id AND member.member_id=item->>'member_id'),x.subject),'original_source',x.original_source,'analyzed_scope',coalesce((SELECT member.analyzed_scope FROM kb.data_product_member member WHERE member.product_id=x.id AND member.member_id=item->>'member_id'),x.analyzed_scope),'meaning_body',coalesce((SELECT member.body FROM kb.data_product_member member WHERE member.product_id=x.id AND member.member_id=item->>'member_id'),x.canonical_body)),o.original_source,coalesce(d.selection->'source_sets','{}'))
 AND ((item->>'member_id' IS NULL AND x.kind_contract=declared->>'kind_contract') OR EXISTS(SELECT FROM kb.data_product_member m WHERE m.product_id=x.id AND m.member_id=item->>'member_id' AND m.kind_contract=declared->>'kind_contract')))
 OR (item->>'position')::integer<0 OR (item->>'multiplicity')::integer<1 THEN RAISE EXCEPTION 'input role/member/kind/source mismatch'; END IF;
 IF NOT EXISTS(SELECT FROM ops.data_derivation_output outp JOIN jsonb_array_elements(p->'binding'->'support') s ON s->>'derivation_id'=outp.derivation_id
 WHERE s->>'role'=item->>'role' AND s->>'position' IS NOT DISTINCT FROM item->>'position' AND (item->>'support_derivation_id' IS NULL OR item->>'support_derivation_id'=s->>'derivation_id') AND outp.product_id=item->>'product_id' AND ((item->>'member_id' IS NULL AND outp.member_id IS NULL) OR (item->>'member_id' IS NOT NULL AND (outp.member_id IS NULL OR outp.member_id=item->>'member_id')))) THEN RAISE EXCEPTION 'input lacks selected authentic producing support'; END IF;
 END LOOP;
 FOR declared IN SELECT value FROM jsonb_array_elements(def.input_roles) LOOP
 SELECT coalesce(sum((v->>'multiplicity')::integer),0) INTO cnt FROM jsonb_array_elements(p->'binding'->'inputs') v WHERE v->>'role'=declared->>'name';
 IF cnt<coalesce((declared->>'minimum')::integer,0) OR (declared->>'maximum' IS NOT NULL AND cnt>(declared->>'maximum')::integer) THEN RAISE EXCEPTION 'input cardinality mismatch'; END IF;
 END LOOP;
 SELECT x.id INTO episode FROM ops.data_derivation x WHERE x.request_id=r.id AND x.generation=r.generation AND ops.ddo_support_valid(x.id) ORDER BY x.id LIMIT 1;
 IF p ? 'rebind_derivation' THEN
 episode:=p->>'rebind_derivation';
 -- Substitution can replace upstream witnesses, never a directly distrusted producer.
 IF d.strength<>'value' OR def.support_contract->>'provenance'<>'value_substitution'
 OR NOT EXISTS(SELECT FROM ops.data_derivation x JOIN ops.data_request q ON q.id=x.request_id WHERE x.id=episode AND x.outcome IN ('success','empty') AND q.request_key=r.request_key
 AND NOT EXISTS(SELECT FROM ops.data_revocation v WHERE v.scope=ops.ddo_scope(q.project_id,q.original_source) AND ((v.selector_kind='derivation' AND v.selector=x.id) OR (v.selector_kind='recipe' AND v.selector=x.recipe) OR (v.selector_kind='runtime' AND v.selector=x.runtime_id)
 OR (v.selector_kind='product' AND EXISTS(SELECT FROM ops.data_derivation_output z WHERE z.derivation_id=x.id AND z.product_id=v.selector)))))
 OR EXISTS(SELECT FROM jsonb_array_elements(def.input_roles) z WHERE coalesce(z->'identity_requirements','[]')<>'[]'::jsonb) THEN RAISE EXCEPTION 'support substitution cannot rehabilitate this producer/contract'; END IF;
 END IF;
 IF episode IS NULL THEN
 IF r.live_task_id IS NOT NULL THEN
 SELECT * INTO STRICT current_task FROM ops.task WHERE id=r.live_task_id FOR UPDATE;
 SELECT * INTO retained FROM ops.data_completion_intent intent
 WHERE intent.request_id=r.id AND intent.generation=r.generation
 AND NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt WHERE receipt.intent_id=intent.id);
 invalid_retained:=retained.id IS NOT NULL AND (
 EXISTS(SELECT FROM jsonb_array_elements(retained.payload->'support') old_support
 WHERE CASE WHEN old_support->>'admission_use_id' IS NULL
 THEN NOT ops.ddo_support_valid(old_support->>'derivation_id')
 ELSE NOT EXISTS(SELECT FROM ops.demand_use selected
 WHERE selected.id=old_support->>'admission_use_id'
 AND selected.derivation_id=old_support->>'derivation_id' AND ops.ddo_use_valid(selected)) END)
 OR EXISTS(SELECT FROM ops.data_revocation v WHERE v.scope=ops.ddo_scope(r.project_id,r.original_source)
 AND ((v.selector_kind='runtime' AND v.selector=retained.runtime_id)
 OR (v.selector_kind='recipe' AND v.selector=r.recipe))));
 IF invalid_retained AND current_task.status='running'
 AND (current_task.lease_until IS NULL OR current_task.lease_until>clock_timestamp()) THEN
 RAISE EXCEPTION 'invalid retained intent still has an active producer lease'; END IF;
 IF current_task.status IN ('done','empty','failed','cancelled')
 OR (invalid_retained AND (current_task.status='pending'
 OR (current_task.status='running' AND current_task.lease_until<=clock_timestamp()))) THEN
 IF EXISTS(SELECT FROM ops.data_revocation v WHERE v.scope=ops.ddo_scope(d.project_id,o.original_source)
 AND ((v.selector_kind='runtime' AND v.selector=d.runtime_id)
 OR (v.selector_kind='recipe' AND v.selector=def.recipe))) THEN
 RAISE EXCEPTION 'replacement runtime or recipe was directly revoked'; END IF;
 -- The old intent/generation and task remain immutable history. Losing the
 -- publication fence does not assert that an old physical child has retired.
 UPDATE ops.data_request SET generation=generation+1,live_task_id=NULL,binding=(p->'binding')||jsonb_build_object('execution_profile',d.selection->'execution_profile'),release_id=d.release_id,runtime_id=d.runtime_id WHERE id=r.id RETURNING * INTO r;
 END IF; END IF;
 IF r.live_task_id IS NULL THEN
 UPDATE ops.data_request SET binding=(p->'binding')||jsonb_build_object('execution_profile',d.selection->'execution_profile'),release_id=d.release_id,runtime_id=d.runtime_id WHERE id=r.id RETURNING * INTO r;
 INSERT INTO ops.task(release_id,data_request_id,data_generation,status,attempt,cost,priority,created_at)
 VALUES(r.release_id,r.id,r.generation,'pending',0,'{}',0,clock_timestamp()) RETURNING id INTO task;
 INSERT INTO ops.data_request_generation VALUES(r.id,r.generation,task);
 UPDATE ops.data_request SET live_task_id=task WHERE id=r.id RETURNING * INTO r;
 END IF;
 END IF;
 SELECT intent.id INTO retained_id FROM ops.data_completion_intent intent WHERE intent.request_id=r.id AND intent.generation=r.generation AND NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt WHERE receipt.intent_id=intent.id);
 usekey:='use:'||ops.ddo_digest(jsonb_build_array(o.id,r.id,r.generation,episode,p->'binding',snapshot));
 INSERT INTO ops.demand_use VALUES(usekey,d.id,o.id,CASE WHEN episode IS NULL THEN 'attached' ELSE 'fulfilled' END,r.id,r.generation,episode,p->'binding',snapshot,clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 RETURN jsonb_build_object('payload',jsonb_build_object('request_id',r.id,'generation',r.generation,'task_id',r.live_task_id,'fate',CASE WHEN episode IS NULL THEN 'attached' ELSE 'fulfilled' END,'derivation_id',episode,'use_id',usekey,'trust_snapshot',snapshot,'action',CASE WHEN episode IS NOT NULL THEN 'reuse' WHEN retained_id IS NOT NULL THEN 'reconcile' ELSE 'compute' END,'retained_intent_id',retained_id));
END $$;

CREATE OR REPLACE FUNCTION ops.claim_data_request(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; snapshot jsonb; retained_id text;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['request_id','holder','lease_seconds']);
 IF nullif(p->>'holder','') IS NULL OR (p->>'lease_seconds')::integer NOT BETWEEN 1 AND 86400 THEN RAISE EXCEPTION 'invalid holder/lease'; END IF;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id';
 PERFORM ops.ddo_authorize_request(r);
 snapshot:=ops.ddo_lock_support(r.project_id,r.original_source,r.binding->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 IF NOT ops.ddo_request_useful(r) THEN RETURN jsonb_build_object('payload',jsonb_build_object('state','no-work')); END IF;
 SELECT * INTO STRICT t FROM ops.task WHERE id=r.live_task_id FOR UPDATE;
 IF t.status='running' AND t.lease_until IS NULL THEN RAISE EXCEPTION 'running task has no publication lease'; END IF;
 IF t.status NOT IN ('pending','running') OR (t.status='running' AND t.lease_until>clock_timestamp()) THEN RETURN jsonb_build_object('payload',jsonb_build_object('state','no-work')); END IF;
 PERFORM ops.ddo_assert_support(r,r.binding->'support');
 UPDATE ops.task SET status='running',attempt=attempt+1,claimed_by=p->>'holder',lease_until=clock_timestamp()+make_interval(secs=>(p->>'lease_seconds')::integer),started_at=coalesce(started_at,clock_timestamp()) WHERE id=t.id RETURNING * INTO t;
 SELECT intent.id INTO retained_id FROM ops.data_completion_intent intent WHERE intent.request_id=r.id AND intent.generation=r.generation AND NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt WHERE receipt.intent_id=intent.id);
 RETURN jsonb_build_object('payload',jsonb_build_object('state','claimed','request_id',r.id,'generation',r.generation,'task_id',t.id,'attempt',t.attempt,'holder',t.claimed_by,'lease_until',t.lease_until,'trust_snapshot',snapshot,'action',CASE WHEN retained_id IS NULL THEN 'compute' ELSE 'reconcile' END,'retained_intent_id',retained_id));
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_lost_attempt(p jsonb,reason text) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('payload',jsonb_build_object('state','lost','reason',reason,
 'request_id',p->>'request_id','generation',(p->>'generation')::integer,'task_id',(p->>'task_id')::bigint,
 'attempt',(p->>'attempt')::integer,'holder',p->>'holder'))
$$;

CREATE OR REPLACE FUNCTION ops.renew_data_request(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; snapshot jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['request_id','generation','task_id','attempt','holder','lease_seconds']);
 IF nullif(p->>'holder','') IS NULL OR (p->>'lease_seconds')::integer NOT BETWEEN 1 AND 86400
 OR (p->>'generation')::integer<1 OR (p->>'attempt')::integer<1 OR (p->>'task_id')::bigint<1 THEN RAISE EXCEPTION 'invalid request attempt/holder/lease'; END IF;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id';
 PERFORM ops.ddo_authorize_request(r);
 snapshot:=ops.ddo_lock_support(r.project_id,r.original_source,r.binding->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 SELECT * INTO t FROM ops.task WHERE id=r.live_task_id FOR UPDATE;
 IF NOT ops.ddo_request_useful(r) THEN RETURN ops.ddo_lost_attempt(p,CASE WHEN t.status IN ('done','empty','failed') THEN 'fence' ELSE 'cancelled' END); END IF;
 IF t.id IS NULL OR r.generation IS DISTINCT FROM (p->>'generation')::integer
 OR (t.data_request_id,t.data_generation,t.id,t.attempt,t.claimed_by) IS DISTINCT FROM
 (r.id,r.generation,(p->>'task_id')::bigint,(p->>'attempt')::integer,p->>'holder')
 OR t.status IS DISTINCT FROM 'running' OR t.lease_until IS NULL OR t.lease_until<=clock_timestamp() THEN
 RETURN ops.ddo_lost_attempt(p,'fence'); END IF;
 IF EXISTS(SELECT FROM ops.data_revocation v WHERE v.scope=ops.ddo_scope(r.project_id,r.original_source)
 AND ((v.selector_kind='runtime' AND v.selector=r.runtime_id)
 OR (v.selector_kind='recipe' AND v.selector=r.recipe))) THEN
 RETURN ops.ddo_lost_attempt(p,'revoked'); END IF;
 IF NOT ops.ddo_support_available(r,r.binding->'support') THEN RETURN ops.ddo_lost_attempt(p,'support-unavailable'); END IF;
 UPDATE ops.task SET lease_until=greatest(t.lease_until,clock_timestamp()+make_interval(secs=>(p->>'lease_seconds')::integer))
 WHERE id=t.id RETURNING * INTO t;
 RETURN jsonb_build_object('payload',jsonb_build_object('state','renewed','request_id',r.id,'generation',r.generation,
 'task_id',t.id,'attempt',t.attempt,'holder',t.claimed_by,'lease_until',t.lease_until,'trust_snapshot',snapshot));
END $$;

CREATE OR REPLACE FUNCTION ops.release_data_attempt(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; old ops.data_attempt_failure;
 key text; retained text; replayed boolean:=false;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['request_id','generation','task_id','attempt','holder','physical_retirement','failure']);
 PERFORM ops.ddo_fields(p->'failure',ARRAY['code','message']);
 IF p->>'physical_retirement' IS DISTINCT FROM 'confirmed' OR nullif(p->>'holder','') IS NULL
 OR nullif(p->'failure'->>'code','') IS NULL OR nullif(p->'failure'->>'message','') IS NULL
 OR (p->>'generation')::integer<1 OR (p->>'attempt')::integer<1 OR (p->>'task_id')::bigint<1 THEN
 RAISE EXCEPTION 'attempt release requires exact known retirement/failure'; END IF;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id';
 PERFORM ops.ddo_authorize_request(r);
 -- Request serialization also waits for uncertain retention/publication to settle.
 -- No inference work or transport wait is held under this transaction.
 PERFORM ops.ddo_lock_support(r.project_id,r.original_source,r.binding->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 SELECT * INTO old FROM ops.data_attempt_failure f WHERE f.request_id=r.id
 AND (f.generation,f.task_id,f.attempt,f.holder)=((p->>'generation')::integer,(p->>'task_id')::bigint,(p->>'attempt')::integer,p->>'holder');
 IF old.id IS NOT NULL THEN
 IF old.failure IS DISTINCT FROM p->'failure' THEN RAISE EXCEPTION 'immutable attempt failure cannot change'; END IF;
 key:=old.id; replayed:=true;
 ELSE
 IF NOT ops.ddo_request_useful(r) THEN RETURN ops.ddo_lost_attempt(p,'cancelled'); END IF;
 SELECT * INTO t FROM ops.task WHERE id=r.live_task_id FOR UPDATE;
 IF t.id IS NULL OR r.generation IS DISTINCT FROM (p->>'generation')::integer
 OR (t.data_request_id,t.data_generation,t.id,t.attempt,t.claimed_by) IS DISTINCT FROM
 (r.id,r.generation,(p->>'task_id')::bigint,(p->>'attempt')::integer,p->>'holder') OR t.status IS DISTINCT FROM 'running' THEN
 RETURN ops.ddo_lost_attempt(p,'fence'); END IF;
 key:='attempt-failure:'||ops.ddo_digest(p);
 INSERT INTO ops.data_attempt_failure VALUES(key,r.id,r.generation,t.id,t.attempt,t.claimed_by,p->'failure',clock_timestamp(),pg_current_xact_id()::text);
 UPDATE ops.task SET status='pending',claimed_by=NULL,lease_until=NULL,finished_at=NULL,
 error=jsonb_build_object('data_attempt_failure',key,'failure',p->'failure') WHERE id=t.id;
 END IF;
 SELECT id INTO retained FROM ops.data_completion_intent WHERE request_id=r.id AND generation=(p->>'generation')::integer;
 RETURN jsonb_build_object('payload',jsonb_build_object('state','released','request_id',r.id,
 'generation',(p->>'generation')::integer,'task_id',(p->>'task_id')::bigint,'attempt',(p->>'attempt')::integer,
 'holder',p->>'holder','failure_id',key,'replayed',replayed,'retained_intent_id',retained));
END $$;

CREATE OR REPLACE FUNCTION ops.retain_data_completion_intent(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; snapshot jsonb; key text; old ops.data_completion_intent;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['request_id','generation','task_id','attempt','holder','runtime_id','completion']);
 PERFORM ops.ddo_fields(p->'completion',ARRAY['outcome','outputs','support','inputs','implementation_revision'],ARRAY['execution_evidence']);
 IF p->'completion' ? 'execution_evidence' AND (p->'completion'->'execution_evidence' - 'version' - 'host_receipts' - 'cpu_receipts') IS DISTINCT FROM (p - 'completion') THEN RAISE EXCEPTION 'execution evidence differs from native producer fence/runtime'; END IF;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id';
 snapshot:=ops.ddo_lock_support(r.project_id,r.original_source,p->'completion'->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 t:=ops.ddo_claim(r,p);
 PERFORM sem.require_runtime_binding(r.release_id,p->>'runtime_id');
 IF NOT EXISTS(SELECT FROM sem.runtime_binding runtime WHERE runtime.release_id=r.release_id AND runtime.runtime_id=p->>'runtime_id'
 AND convert_from(runtime.manifest_bytes,'UTF8')::jsonb->>'execution_profile'=r.binding->>'execution_profile') THEN RAISE EXCEPTION 'actual producer runtime execution profile differs from admitted request'; END IF;
 IF r.generation<>(p->>'generation')::integer OR p->'completion'->'inputs' IS DISTINCT FROM r.binding->'inputs' OR p->'completion'->'support' IS DISTINCT FROM r.binding->'support'
 OR NOT EXISTS(SELECT FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id AND implementation_revision=p->'completion'->>'implementation_revision') THEN RAISE EXCEPTION 'completion differs from admitted request/implementation'; END IF;
 PERFORM ops.ddo_assert_support(r,p->'completion'->'support');
 key:='intent:'||ops.ddo_digest(jsonb_build_array(r.id,r.generation,t.id,t.attempt,t.claimed_by,p->>'runtime_id',p->'completion'));
 INSERT INTO ops.data_completion_intent VALUES(key,r.id,r.generation,t.id,t.attempt,t.claimed_by,p->>'runtime_id',p->'completion',ops.ddo_digest(p->'completion'),clock_timestamp()) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT old FROM ops.data_completion_intent WHERE request_id=r.id AND generation=r.generation;
 IF old.id<>key THEN RAISE EXCEPTION 'immutable retained intent must be adopted; a generation cannot replace its answer'; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('intent_id',key,'payload_digest',old.payload_digest));
END $$;
CREATE OR REPLACE FUNCTION ops.adopt_data_completion_intent(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; i ops.data_completion_intent; snapshot jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['request_id','generation','task_id','attempt','holder','intent_id']);
 SELECT * INTO STRICT i FROM ops.data_completion_intent WHERE id=p->>'intent_id';
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id';
 snapshot:=ops.ddo_lock_support(r.project_id,r.original_source,i.payload->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 t:=ops.ddo_claim(r,p);
 IF i.request_id<>r.id OR i.generation<>r.generation OR i.generation<>(p->>'generation')::integer OR EXISTS(SELECT FROM ops.data_publication_receipt WHERE intent_id=i.id) THEN RAISE EXCEPTION 'only unresolved exact generation intent can be adopted'; END IF;
 PERFORM ops.ddo_assert_support(r,i.payload->'support');
 INSERT INTO ops.data_intent_adoption VALUES(i.id,t.id,t.attempt,t.claimed_by) ON CONFLICT DO NOTHING;
 RETURN jsonb_build_object('payload',jsonb_build_object('intent_id',i.id,'producer_task_id',i.producer_task_id,'producer_attempt',i.producer_attempt));
END $$;
CREATE OR REPLACE FUNCTION data.ddo_json(v jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE tag text:=v->>0; result jsonb;
BEGIN
 IF tag IN ('null','known-absent','unknown','unavailable') THEN RETURN 'null';
 ELSIF tag IN ('boolean','string','date','datetime') THEN RETURN v->1;
 ELSIF tag='float' THEN RETURN to_jsonb(data.require_float_lexical(v->>1)::double precision);
 ELSIF tag IN ('integer','decimal') THEN RETURN to_jsonb((v->>1)::numeric);
 ELSIF tag='present' THEN RETURN data.ddo_json(v->1);
 ELSIF tag IN ('sequence','ordered-bag','bag','set') THEN SELECT coalesce(jsonb_agg(data.ddo_json(value) ORDER BY n),'[]') INTO result FROM jsonb_array_elements(v->1) WITH ORDINALITY a(value,n); RETURN result;
 ELSIF tag='mapping' THEN SELECT coalesce(jsonb_object_agg(e->>0,data.ddo_json(e->1)),'{}') INTO result FROM jsonb_array_elements(v->1) e; RETURN result;
 END IF; RAISE EXCEPTION 'unsupported semantic body';
END $$;
CREATE OR REPLACE FUNCTION ops.ddo_install_product(r ops.data_request,o jsonb) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE k sem.data_kind_contract; key text; b jsonb; bd text; m jsonb; raw jsonb; f jsonb; n bigint; previous kb.data_product; packet jsonb; member_context jsonb; member_kind sem.data_kind_contract;
BEGIN
 PERFORM ops.ddo_fields(o,ARRAY['kind_contract','body','members'],ARRAY['artifact_digest']);
 SELECT * INTO STRICT k FROM sem.data_kind_contract WHERE kind_contract=o->>'kind_contract';
 PERFORM ops.ddo_authorize(k.universe);
 IF NOT EXISTS(SELECT FROM sem.data_kind_release WHERE release_id=r.release_id AND kind_contract=k.kind_contract) THEN RAISE EXCEPTION 'output kind is outside release'; END IF;
 IF o->>'artifact_digest' IS NOT NULL THEN RAISE EXCEPTION 'artifact publication requires an authenticated staged receipt profile'; END IF;
 b:=data.ddo_normalize(o->'body');
 IF NOT public.json_matches_schema(k.meaning_schema::json,b::json) OR NOT public.json_matches_schema(k.body_schema::json,data.ddo_json(b)::json) OR jsonb_typeof(o->'members')<>'array' THEN RAISE EXCEPTION 'body violates kind contract'; END IF;
 IF k.member_schema='{"not":{}}'::jsonb THEN
 IF o->'members'<>'[]'::jsonb THEN RAISE EXCEPTION 'noncontainer kind cannot publish projected members'; END IF;
 ELSE
 IF coalesce(data.ddo_field(b,'members')->>0,'')<>'sequence' OR jsonb_array_length(data.ddo_field(b,'members')->1)<>jsonb_array_length(o->'members') THEN RAISE EXCEPTION 'body/member projection count disagreement'; END IF;
 END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(o->'members') member GROUP BY member->>'member_id' HAVING count(*)<>1) THEN RAISE EXCEPTION 'duplicate member local identity'; END IF;
 bd:=data.ddo_identity('body',b);
 key:=data.ddo_identity('product',jsonb_build_array('mapping',jsonb_build_array(jsonb_build_array('body',jsonb_build_array('string',bd)),jsonb_build_array('kind',jsonb_build_array('string',k.kind_contract)),jsonb_build_array('subject',jsonb_build_array('string',r.subject)))));
 INSERT INTO kb.data_product VALUES(key,k.kind_contract,r.project_id,r.subject,r.original_source,r.analyzed_scope,b,bd,o->>'artifact_digest') ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT previous FROM kb.data_product WHERE id=key;
 IF (previous.kind_contract,previous.project_id,previous.subject,previous.original_source,previous.body_digest) IS DISTINCT FROM (k.kind_contract,r.project_id,r.subject,r.original_source,bd) OR previous.canonical_body IS DISTINCT FROM b OR previous.analyzed_scope IS DISTINCT FROM r.analyzed_scope THEN RAISE EXCEPTION 'product identity/custody collision'; END IF;
 FOR m,n IN SELECT value,ord-1 FROM jsonb_array_elements(o->'members') WITH ORDINALITY entry(value,ord) LOOP
 PERFORM ops.ddo_fields(m,ARRAY['member_id','kind_contract','context','body'],ARRAY['coordinates','roles','endpoints','coverage','choices']);
 PERFORM ops.ddo_fields(m->'context',ARRAY['subject','original_source','analyzed_scope']);
 packet:=data.ddo_field(b,'members')->1->(n::integer);
 member_context:=m->'context';
 IF packet->>0<>'mapping' OR jsonb_array_length(packet->1)<>4
 OR data.ddo_field(packet,'member_id') IS DISTINCT FROM jsonb_build_array('string',m->>'member_id')
 OR data.ddo_field(packet,'kind_contract') IS DISTINCT FROM jsonb_build_array('string',m->>'kind_contract')
 OR data.ddo_field(packet,'body') IS DISTINCT FROM data.ddo_normalize(m->'body')
 OR data.ddo_json(data.ddo_field(packet,'context')) IS DISTINCT FROM member_context
 OR nullif(member_context->>'subject','') IS NULL OR member_context->>'original_source' IS DISTINCT FROM r.original_source THEN RAISE EXCEPTION 'member context/body differs from canonical container packet'; END IF;
 SELECT * INTO STRICT member_kind FROM sem.data_kind_contract WHERE kind_contract=m->>'kind_contract';
 PERFORM ops.ddo_authorize(member_kind.universe);
 IF NOT k.member_contracts ? member_kind.kind_contract
 OR NOT EXISTS(SELECT FROM sem.data_kind_release release_kind WHERE release_kind.release_id=r.release_id AND release_kind.kind_contract=member_kind.kind_contract)
 OR NOT public.json_matches_schema(member_kind.meaning_schema::json,data.ddo_normalize(m->'body')::json)
 OR NOT public.json_matches_schema(member_kind.body_schema::json,data.ddo_json(data.ddo_normalize(m->'body'))::json) THEN RAISE EXCEPTION 'member kind/body differs from declared nominal container member contract'; END IF;
 IF nullif(m->>'member_id','') IS NULL OR NOT public.json_matches_schema(k.member_schema::json,data.ddo_json(data.ddo_normalize(m->'body'))::json) THEN RAISE EXCEPTION 'invalid member contract'; END IF;
 raw:=data.ddo_json(data.ddo_normalize(m->'body'));
 IF EXISTS(SELECT FROM (VALUES('coordinates','coordinate'),('roles','role'),('endpoints','endpoint'),('coverage','coverage'),('choices','choice')) fields(field,family) WHERE (member_kind.families ? family AND coalesce(raw->field,'[]') IS DISTINCT FROM coalesce(m->field,'[]')) OR (NOT member_kind.families ? family AND coalesce(m->field,'[]')<>'[]'::jsonb)) THEN RAISE EXCEPTION 'member projection differs from semantic body'; END IF;
 INSERT INTO kb.data_product_member VALUES(key,m->>'member_id',member_kind.kind_contract,member_context->>'subject',member_context->>'original_source',member_context->'analyzed_scope',data.ddo_normalize(m->'body')) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.data_product_member WHERE product_id=key AND member_id=m->>'member_id' AND kind_contract=member_kind.kind_contract AND body=data.ddo_normalize(m->'body') AND subject=member_context->>'subject' AND original_source=member_context->>'original_source' AND analyzed_scope=member_context->'analyzed_scope') THEN RAISE EXCEPTION 'member local identity collision'; END IF;
 END LOOP;
 -- All local endpoints exist before family insertion. Cross-product endpoints require exact custody.
 FOR m IN SELECT value FROM jsonb_array_elements(o->'members') LOOP
 SELECT * INTO STRICT member_kind FROM sem.data_kind_contract WHERE kind_contract=m->>'kind_contract';
 FOR f,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'coordinates','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(f,ARRAY['original_source','start','end'],ARRAY['page']);
 IF f->>'original_source'<>r.original_source OR NOT member_kind.families ? 'coordinate' THEN RAISE EXCEPTION 'coordinate source/family mismatch'; END IF;
 INSERT INTO kb.data_member_coordinate VALUES(key,m->>'member_id',n,f->>'original_source',(f->>'start')::integer,(f->>'end')::integer,(f->>'page')::integer) ON CONFLICT DO NOTHING;
 END LOOP;
 FOR f,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'roles','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(f,ARRAY['role','position','multiplicity']);
 IF NOT member_kind.families ? 'role' THEN RAISE EXCEPTION 'undeclared role family'; END IF;
 INSERT INTO kb.data_member_role VALUES(key,m->>'member_id',n,f->>'role',(f->>'position')::integer,(f->>'multiplicity')::integer) ON CONFLICT DO NOTHING;
 END LOOP;
 FOR f,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'endpoints','[]')) WITH ORDINALITY a(value,ord) LOOP
 IF f->>'scope'='local' THEN PERFORM ops.ddo_fields(f,ARRAY['scope','role','member_id']);
 ELSIF f->>'scope'='external' THEN PERFORM ops.ddo_fields(f,ARRAY['scope','role','product_id','member_id']);
 ELSE RAISE EXCEPTION 'endpoint requires explicit local/external scope'; END IF;
 IF NOT member_kind.families ? 'endpoint' OR NOT EXISTS(SELECT FROM kb.data_product x WHERE x.id=CASE WHEN f->>'scope'='local' THEN key ELSE f->>'product_id' END AND x.project_id=r.project_id AND x.original_source=r.original_source) THEN RAISE EXCEPTION 'endpoint custody/family mismatch'; END IF;
 INSERT INTO kb.data_member_endpoint VALUES(key,m->>'member_id',n,f->>'role',CASE WHEN f->>'scope'='local' THEN key ELSE f->>'product_id' END,f->>'member_id') ON CONFLICT DO NOTHING;
 END LOOP;
 FOR f,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'coverage','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(f,ARRAY['scope','start','end','complete']);
 IF NOT member_kind.families ? 'coverage' THEN RAISE EXCEPTION 'undeclared coverage family'; END IF;
 INSERT INTO kb.data_member_coverage VALUES(key,m->>'member_id',n,f->>'scope',(f->>'start')::integer,(f->>'end')::integer,(f->>'complete')::boolean) ON CONFLICT DO NOTHING;
 END LOOP;
 FOR f,n IN SELECT value,ord-1 FROM jsonb_array_elements(coalesce(m->'choices','[]')) WITH ORDINALITY a(value,ord) LOOP
 PERFORM ops.ddo_fields(f,ARRAY['choice_group','alternative','selected']);
 IF NOT member_kind.families ? 'choice' THEN RAISE EXCEPTION 'undeclared choice family'; END IF;
 INSERT INTO kb.data_member_choice VALUES(key,m->>'member_id',n,f->>'choice_group',f->>'alternative',(f->>'selected')::boolean) ON CONFLICT DO NOTHING;
 END LOOP;
 END LOOP;
 RETURN key;
END $$;

CREATE OR REPLACE FUNCTION ops.publish_data_derivation(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; i ops.data_completion_intent; receipt ops.data_publication_receipt;
 snapshot jsonb; episode text; key text; o jsonb; item jsonb; roledef jsonb; def sem.data_operation_definition; cnt bigint; n bigint; product text; usekey text; result_state text;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['request_id','generation','task_id','attempt','holder','intent_id'],ARRAY['trust_snapshot']);
 SELECT * INTO STRICT i FROM ops.data_completion_intent WHERE id=p->>'intent_id';
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id';
 PERFORM ops.ddo_authorize_request(r);
 -- Receipt replay remains readable after terminal ownership and distrust. It creates no new admission.
 SELECT * INTO receipt FROM ops.data_publication_receipt WHERE intent_id=i.id;
 IF FOUND AND i.request_id=r.id AND i.generation=(p->>'generation')::integer THEN RETURN jsonb_build_object('payload',jsonb_build_object('receipt_id',receipt.id,'derivation_id',receipt.derivation_id,'replayed',true,'trust_snapshot',receipt.trust_snapshot)); END IF;
 snapshot:=ops.ddo_lock_support(r.project_id,r.original_source,i.payload->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 t:=ops.ddo_claim(r,p);
 IF i.request_id<>r.id OR i.generation<>r.generation OR i.generation<>(p->>'generation')::integer OR NOT ((i.producer_task_id,i.producer_attempt,i.producer_holder)=(t.id,t.attempt,t.claimed_by) OR EXISTS(SELECT FROM ops.data_intent_adoption a WHERE a.intent_id=i.id AND (a.task_id,a.attempt,a.holder)=(t.id,t.attempt,t.claimed_by))) THEN RAISE EXCEPTION 'intent is not bound to current attempt'; END IF;
 PERFORM ops.ddo_assert_support(r,i.payload->'support');
 PERFORM sem.require_runtime_binding(r.release_id,i.runtime_id);
 IF EXISTS(SELECT FROM ops.data_revocation v WHERE v.scope=ops.ddo_scope(r.project_id,r.original_source)
 AND ((v.selector_kind='runtime' AND v.selector=i.runtime_id) OR (v.selector_kind='recipe' AND v.selector=r.recipe))) THEN RAISE EXCEPTION 'producing runtime or recipe was directly revoked'; END IF;
 -- Expected epochs are advisory snapshots; a changed epoch is safely re-evaluated above under locks.
 SELECT * INTO STRICT def FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 result_state:=ops.ddo_completion_state(def,i.payload->>'outcome');
 IF i.payload->>'implementation_revision'<>def.implementation_revision OR jsonb_typeof(i.payload->'outputs')<>'array' THEN RAISE EXCEPTION 'invalid completion attestation/outcome'; END IF;
 IF result_state IN ('empty','failed') AND i.payload->'outputs'<>'[]'::jsonb THEN RAISE EXCEPTION 'non-success completion cannot publish outputs'; END IF;
 episode:='derivation:'||ops.ddo_digest(jsonb_build_array(i.id,i.payload_digest));
 INSERT INTO ops.data_derivation VALUES(episode,r.id,r.generation,i.id,r.release_id,r.recipe,i.runtime_id,i.producer_task_id,i.producer_attempt,result_state,clock_timestamp());
 FOR item IN SELECT value FROM jsonb_array_elements(i.payload->'inputs') LOOP
 INSERT INTO ops.data_derivation_input VALUES(episode,item->>'role',(item->>'position')::integer,(item->>'multiplicity')::integer,item->>'product_id',item->>'member_id');
 END LOOP;
 FOR item,n IN SELECT value,ord-1 FROM jsonb_array_elements(i.payload->'support') WITH ORDINALITY a(value,ord) LOOP
 INSERT INTO ops.data_derivation_support SELECT episode,coalesce(item->>'role','support'),coalesce((item->>'position')::integer,n),item->>'derivation_id',ops.ddo_scope(q.project_id,q.original_source),(snapshot->>ops.ddo_scope(q.project_id,q.original_source))::integer,item->>'admission_use_id',n FROM ops.data_derivation x JOIN ops.data_request q ON q.id=x.request_id WHERE x.id=item->>'derivation_id';
 END LOOP;
 FOR o IN SELECT value FROM jsonb_array_elements(i.payload->'outputs') LOOP
 PERFORM ops.ddo_fields(o,ARRAY['role','position','multiplicity','product'],ARRAY['member_id']);
 SELECT value INTO roledef FROM jsonb_array_elements(def.output_roles) WHERE value->>'name'=o->>'role';
 IF roledef IS NULL OR (o->>'member_id' IS NULL AND roledef->>'kind_contract' IS DISTINCT FROM o->'product'->>'kind_contract') THEN RAISE EXCEPTION 'output role/kind mismatch'; END IF;
 product:=ops.ddo_install_product(r,o->'product');
 IF o->>'member_id' IS NOT NULL AND NOT EXISTS(SELECT FROM kb.data_product_member member WHERE member.product_id=product AND member.member_id=o->>'member_id' AND member.kind_contract=roledef->>'kind_contract') THEN RAISE EXCEPTION 'output member is outside its qualified product'; END IF;
 INSERT INTO ops.data_derivation_output VALUES(episode,o->>'role',(o->>'position')::integer,(o->>'multiplicity')::integer,product,o->>'member_id');
 END LOOP;
 IF result_state='success' THEN
 FOR roledef IN SELECT value FROM jsonb_array_elements(def.output_roles) LOOP
 SELECT coalesce(sum(multiplicity),0) INTO cnt FROM ops.data_derivation_output WHERE derivation_id=episode AND role=roledef->>'name';
 IF roledef->>'collection'='set' AND (EXISTS(SELECT FROM ops.data_derivation_output output WHERE output.derivation_id=episode AND output.role=roledef->>'name' AND output.multiplicity<>1)
 OR EXISTS(SELECT FROM ops.data_derivation_output output WHERE output.derivation_id=episode AND output.role=roledef->>'name' GROUP BY output.product_id,output.member_id HAVING count(*)<>1)) THEN RAISE EXCEPTION 'set output requires unique values and unit multiplicity'; END IF;
 IF cnt<coalesce((roledef->>'minimum')::integer,0) OR (roledef->>'maximum' IS NOT NULL AND cnt>(roledef->>'maximum')::integer) THEN RAISE EXCEPTION 'output cardinality differs from contract'; END IF;
 END LOOP; END IF;
 key:='receipt:'||ops.ddo_digest(jsonb_build_array(i.id,episode));
 INSERT INTO ops.data_publication_receipt VALUES(key,i.id,episode,t.id,t.attempt,snapshot);
 UPDATE ops.task SET status=CASE result_state WHEN 'success' THEN 'done' WHEN 'empty' THEN 'empty' ELSE 'failed' END,result_digest=i.payload_digest,finished_at=clock_timestamp(),lease_until=NULL,error=CASE WHEN result_state='failed' THEN jsonb_build_object('data_operation','failed') ELSE NULL END WHERE id=t.id;
 -- Every already attached obligation is fulfilled without copying execution episodes or votes.
 IF result_state<>'failed' THEN
 INSERT INTO ops.demand_use SELECT 'use:'||ops.ddo_digest(jsonb_build_array(u.obligation_id,key)),u.demand_id,u.obligation_id,'fulfilled',r.id,r.generation,episode,u.selection,snapshot,clock_timestamp(),pg_current_xact_id()::text
 FROM (SELECT DISTINCT ON(obligation_id) * FROM ops.demand_use WHERE request_id=r.id AND generation=r.generation ORDER BY obligation_id,created_at DESC,id DESC) u WHERE u.fate='attached' AND ops.ddo_demand_active(u.demand_id) ON CONFLICT DO NOTHING;
 END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('receipt_id',key,'derivation_id',episode,'replayed',false,'trust_snapshot',snapshot));
END $$;

CREATE OR REPLACE FUNCTION ops.inspect_data_completion(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; i ops.data_completion_intent; r ops.data_request; receipt ops.data_publication_receipt;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['intent_id'],ARRAY['demand_id','request_id','generation']);
 IF NOT (p ? 'demand_id' OR (p ? 'request_id' AND p ? 'generation')) OR ((p ? 'request_id')<>(p ? 'generation')) THEN RAISE EXCEPTION 'inspection requires demand or exact request/generation binding'; END IF;
 IF p ? 'demand_id' AND NOT EXISTS(SELECT FROM ops.data_demand WHERE id=p->>'demand_id') THEN RAISE EXCEPTION 'unknown inspection demand'; END IF;
 IF p ? 'request_id' THEN
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id' FOR SHARE;
 ELSE
 SELECT * INTO i FROM ops.data_completion_intent WHERE id=p->>'intent_id';
 IF NOT FOUND THEN RETURN jsonb_build_object('payload',jsonb_build_object('state','unavailable','intent_retained',false,'reason','intent-request-binding-unavailable')); END IF;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=i.request_id FOR SHARE;
 END IF;
 PERFORM ops.ddo_authorize_request(r);
 -- The separate statement sees a publication/retention that committed while the
 -- row lock was acquired. No single-snapshot read is called proof of rollback.
 SELECT * INTO i FROM ops.data_completion_intent WHERE id=p->>'intent_id' AND request_id=r.id AND (NOT p ? 'generation' OR generation=(p->>'generation')::integer);
 IF p ? 'demand_id' AND NOT EXISTS(SELECT FROM ops.demand_use u WHERE u.demand_id=p->>'demand_id' AND u.request_id=r.id AND (NOT p ? 'generation' OR u.generation=(p->>'generation')::integer)) THEN RAISE EXCEPTION 'intent request outside inspection demand'; END IF;
 IF i.id IS NULL THEN RETURN jsonb_build_object('payload',jsonb_build_object('state','known-uncommitted','intent_retained',false)); END IF;
 SELECT * INTO receipt FROM ops.data_publication_receipt WHERE intent_id=i.id;
 RETURN jsonb_build_object('payload',CASE WHEN FOUND THEN jsonb_build_object('state','committed','intent_retained',true,'receipt_id',receipt.id,'derivation_id',receipt.derivation_id,'producer_task_id',i.producer_task_id,'producer_attempt',i.producer_attempt,'runtime_id',i.runtime_id,'semantic_outcome',i.payload->'outcome','completion_state',(SELECT der.outcome FROM ops.data_derivation der WHERE der.id=receipt.derivation_id),'trust_snapshot',receipt.trust_snapshot) ELSE jsonb_build_object('state','known-uncommitted','intent_retained',true,'producer_task_id',i.producer_task_id,'producer_attempt',i.producer_attempt) END);
END $$;

CREATE OR REPLACE FUNCTION ops.revoke_data_support(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; scope_key text; e bigint; key text;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['project_id','original_source','selector_kind','selector','reason']);
 IF nullif(p->>'reason','') IS NULL THEN RAISE EXCEPTION 'revocation requires reason'; END IF;
 IF NOT EXISTS(SELECT FROM ops.data_derivation x JOIN ops.data_request r ON r.id=x.request_id
 WHERE r.project_id=p->>'project_id' AND r.original_source=p->>'original_source' AND
 ((p->>'selector_kind'='derivation' AND p->>'selector'=x.id) OR
 (p->>'selector_kind'='recipe' AND p->>'selector'=x.recipe) OR
 (p->>'selector_kind'='runtime' AND p->>'selector'=x.runtime_id) OR
 (p->>'selector_kind'='product' AND EXISTS(SELECT FROM ops.data_derivation_output o WHERE o.derivation_id=x.id AND o.product_id=p->>'selector')))) THEN RAISE EXCEPTION 'revocation selector outside project/source scope'; END IF;
 scope_key:=ops.ddo_scope(p->>'project_id',p->>'original_source');
 INSERT INTO ops.data_trust_scope VALUES(scope_key,p->>'project_id',0) ON CONFLICT DO NOTHING;
 PERFORM 1 FROM ops.data_trust_scope WHERE scope=scope_key FOR UPDATE;
 UPDATE ops.data_trust_scope SET epoch=epoch+1 WHERE scope=scope_key RETURNING epoch INTO e;
 key:='revocation:'||ops.ddo_digest(jsonb_build_array(scope_key,e,p));
 INSERT INTO ops.data_revocation VALUES(key,scope_key,e,p->>'selector_kind',p->>'selector',p->>'reason',clock_timestamp());
 RETURN jsonb_build_object('payload',jsonb_build_object('revocation_id',key,'scope',scope_key,'epoch',e));
END $$;
CREATE OR REPLACE FUNCTION ops.read_demand_result(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; d ops.data_demand; snapshot jsonb:='{}'; results jsonb; obligations jsonb; lim integer; after_key text; next_key text; more boolean; selected_view text; boundary ops.data_demand_read; scope_key text; epoch bigint;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['demand_id'],ARRAY['selection','after','limit','trust_snapshot','read_id','read_snapshot','frontier_at','view']);
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p->>'demand_id';
 IF (p ? 'selection' AND p->'selection' IS DISTINCT FROM d.selection) OR (p ? 'after' AND NOT (p ? 'selection' AND p ? 'trust_snapshot' AND p ? 'read_id'))
 OR ((p ? 'read_snapshot' OR p ? 'frontier_at') AND NOT p ? 'read_id') THEN RAISE EXCEPTION 'demand read selection/snapshot pins are incomplete or differ'; END IF;
 selected_view:=coalesce(p->>'view','frontier');
 IF selected_view NOT IN ('frontier','products') THEN RAISE EXCEPTION 'unknown demand read view'; END IF;
 lim:=coalesce((p->>'limit')::integer,100); after_key:=coalesce(p->>'after','');
 IF lim NOT BETWEEN 1 AND 1000 THEN RAISE EXCEPTION 'invalid demand read bound'; END IF;
 -- Hold source epoch shares only for this short acquisition transaction, never inference.
 FOR scope_key IN SELECT s.scope FROM ops.data_trust_scope s WHERE s.project_id=d.project_id
 AND (EXISTS(SELECT FROM jsonb_array_elements(d.root) root WHERE s.scope=ops.ddo_scope(d.project_id,root->>'original_source'))
 OR EXISTS(SELECT FROM jsonb_each(coalesce(d.selection->'source_sets','{}')) source_set CROSS JOIN LATERAL jsonb_array_elements(source_set.value) entry WHERE s.scope=ops.ddo_scope(d.project_id,entry->>'original_source'))) ORDER BY s.scope LOOP
 SELECT s.epoch INTO epoch FROM ops.data_trust_scope s WHERE s.scope=scope_key FOR SHARE;
 snapshot:=snapshot||jsonb_build_object(scope_key,epoch);
 END LOOP;
 IF p ? 'read_id' THEN
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p->>'read_id' AND demand_id=d.id;
 IF boundary.trust_snapshot IS DISTINCT FROM snapshot
 OR (p ? 'read_snapshot' AND p->>'read_snapshot' IS DISTINCT FROM boundary.read_snapshot)
 OR (p ? 'frontier_at' AND (p->>'frontier_at')::timestamptz IS DISTINCT FROM boundary.frontier_at) THEN RAISE EXCEPTION 'read acquisition pins or current trust differ'; END IF;
 ELSE
 INSERT INTO ops.data_demand_read VALUES('read:'||gen_random_uuid()::text,d.id,pg_current_snapshot()::text,clock_timestamp(),pg_current_xact_id()::text,snapshot) RETURNING * INTO boundary;
 END IF;
 IF p ? 'trust_snapshot' AND p->'trust_snapshot' IS DISTINCT FROM snapshot THEN RAISE EXCEPTION 'trust snapshot changed; reacquire demand read'; END IF;
 PERFORM ops.ddo_authorize(k.universe) FROM ops.demand_use u JOIN ops.data_derivation_output outp ON outp.derivation_id=u.derivation_id JOIN kb.data_product x ON x.id=outp.product_id JOIN sem.data_kind_contract k ON k.kind_contract=x.kind_contract WHERE u.demand_id=d.id AND ops.ddo_read_visible(u.created_at,u.created_xid,boundary);
 WITH bounded AS MATERIALIZED (SELECT o.* FROM ops.data_obligation o WHERE o.demand_id=d.id AND o.id>after_key AND ops.ddo_read_visible(o.created_at,o.created_xid,boundary) ORDER BY o.id LIMIT lim),
 latest AS MATERIALIZED (SELECT u.* FROM bounded o CROSS JOIN LATERAL (SELECT x.* FROM ops.demand_use x WHERE x.obligation_id=o.id AND ops.ddo_read_visible(x.created_at,x.created_xid,boundary) ORDER BY x.created_at DESC,x.id DESC LIMIT 1) u)
 SELECT coalesce(jsonb_agg(jsonb_build_object('use_id',u.id,'obligation_id',u.obligation_id,'fate',CASE WHEN u.fate='fulfilled' AND NOT ops.ddo_use_valid(u,boundary) THEN 'unavailable' ELSE u.fate END,'historical_fate',u.fate,'semantic_outcome',(SELECT i.payload->'outcome' FROM ops.data_derivation der JOIN ops.data_completion_intent i ON i.id=der.intent_id WHERE der.id=u.derivation_id),'completion_state',(SELECT der.outcome FROM ops.data_derivation der WHERE der.id=u.derivation_id),'request_id',u.request_id,'generation',u.generation,'derivation_id',u.derivation_id,'selection',u.selection,'trust_snapshot',u.trust_snapshot,'products',(SELECT coalesce(jsonb_agg(jsonb_build_object('role',outp.role,'position',outp.position,'multiplicity',outp.multiplicity,'product_id',outp.product_id,'member_id',outp.member_id,'kind_contract',x.kind_contract,'subject',x.subject,'original_source',x.original_source,'analyzed_scope',x.analyzed_scope,'body_state',CASE WHEN selected_view='products' THEN 'present' ELSE 'not_requested' END)||CASE WHEN selected_view='products' THEN jsonb_build_object('body',x.canonical_body) ELSE '{}'::jsonb END ORDER BY outp.role,outp.position),'[]') FROM ops.data_derivation_output outp JOIN kb.data_product x ON x.id=outp.product_id WHERE outp.derivation_id=u.derivation_id)) ORDER BY u.obligation_id),'[]') INTO results FROM latest u;
 WITH bounded AS MATERIALIZED (SELECT o.* FROM ops.data_obligation o WHERE o.demand_id=d.id AND o.id>after_key AND ops.ddo_read_visible(o.created_at,o.created_xid,boundary) ORDER BY o.id LIMIT lim)
 SELECT coalesce(jsonb_agg((to_jsonb(o)-'created_at'-'created_xid')||jsonb_build_object('obligation_id',o.id,'historical_fate',u.fate,
 'fate',CASE WHEN u.fate='fulfilled' AND NOT ops.ddo_use_valid(u,boundary) THEN 'unavailable' ELSE coalesce(u.fate,'waiting') END,
 'request_id',u.request_id,'generation',u.generation,'intent_id',(SELECT i.id FROM ops.data_completion_intent i WHERE i.request_id=u.request_id AND i.generation=u.generation ORDER BY i.created_at DESC,i.id DESC LIMIT 1)) ORDER BY o.id),'[]'),max(o.id) INTO obligations,next_key
 FROM bounded o LEFT JOIN LATERAL (SELECT x.* FROM ops.demand_use x WHERE x.obligation_id=o.id AND ops.ddo_read_visible(x.created_at,x.created_xid,boundary) ORDER BY x.created_at DESC,x.id DESC LIMIT 1) u ON true;
 more:=next_key IS NOT NULL AND EXISTS(SELECT FROM ops.data_obligation o WHERE o.demand_id=d.id AND o.id>next_key AND ops.ddo_read_visible(o.created_at,o.created_xid,boundary));
 RETURN jsonb_build_object('payload',jsonb_build_object('demand_id',d.id,'selection',d.selection,'intent',d.selection,'root',d.root,'project_id',d.project_id,'release_id',d.release_id,'runtime_id',d.runtime_id,'state',CASE WHEN EXISTS(SELECT FROM ops.data_demand_cancellation c WHERE c.demand_id=d.id AND ops.ddo_read_visible(c.created_at,c.created_xid,boundary)) THEN 'cancelled' ELSE 'active' END,'view',selected_view,'trust_snapshot',snapshot,'read_id',boundary.id,'read_snapshot',boundary.read_snapshot,'frontier_at',boundary.frontier_at,'uses',results,'obligations',obligations, 'attempt_failures',(SELECT coalesce(jsonb_agg(jsonb_build_object('failure_id',failure.id,'request_id',failure.request_id,
 'generation',failure.generation,'task_id',failure.task_id,'attempt',failure.attempt,'holder',failure.holder,'failure',failure.failure)
 ORDER BY failure.request_id,failure.generation,failure.attempt),'[]') FROM ops.data_attempt_failure failure
 WHERE EXISTS(SELECT FROM jsonb_array_elements(results) selected WHERE selected->>'request_id'=failure.request_id AND (selected->>'generation')::integer=failure.generation)
 AND ops.ddo_read_visible(failure.created_at,failure.created_xid,boundary)),'populations',(SELECT coalesce(jsonb_agg((to_jsonb(pop)-'created_at'-'created_xid'-'selected_obligation_id')||jsonb_build_object('population_id',pop.id,'evidence',pop.evidence||jsonb_build_object('producer_context',ops.ddo_population_producer_context(pop))) ORDER BY pop.name),'[]') FROM ops.data_population pop WHERE pop.demand_id=d.id AND (pop.selected_obligation_id IS NULL OR pop.selected_obligation_id IN (SELECT value->>'obligation_id' FROM jsonb_array_elements(obligations))) AND ops.ddo_read_visible(pop.created_at,pop.created_xid,boundary) AND ops.ddo_population_valid(pop,boundary)),'continuation',CASE WHEN more THEN jsonb_build_object('demand_id',d.id,'selection',d.selection,'trust_snapshot',snapshot,'read_id',boundary.id,'read_snapshot',boundary.read_snapshot,'frontier_at',boundary.frontier_at,'view',selected_view,'after',next_key,'limit',lim) ELSE NULL END));
END $$;


-- Derive the row-local qualification portion of an owned binding. Aggregate and
-- cross-role checks remain in the original binding and are enforced on attachment.
CREATE OR REPLACE FUNCTION ops.ddo_population_filter(node jsonb,role text,choices jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE operator text:=node->>'operator'; child jsonb; projected jsonb; children jsonb:='[]'; names text[];
 selected jsonb; choice text; matches integer:=0;
BEGIN
 IF operator NOT IN ('scan','join','equal','literal','same','distinct','cardinality','collection','all','choice','optional','forall','absent','range','membership','covers') OR operator IS NULL THEN
 RAISE EXCEPTION 'unrepresentable selected-population filter operator'; END IF;
 IF operator='choice' THEN
 choice:=coalesce(node->>'selected',choices->>(node->>'choice_parameter'));
 FOR child IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP
 IF choice=ANY(ops.ddo_binding_roles(child)) THEN selected:=child; matches:=matches+1; END IF;
 END LOOP;
 IF matches<>1 THEN RAISE EXCEPTION 'population filter branch is not uniquely frozen'; END IF;
 RETURN ops.ddo_population_filter(selected,role,choices);
 END IF;
 names:=ops.ddo_binding_roles(node);
 IF NOT role=ANY(names) THEN RETURN jsonb_build_object('operator','all','children','[]'::jsonb); END IF;
 IF operator='absent' THEN RAISE EXCEPTION 'absence cannot define a positive selected population'; END IF;
 -- A wholly aggregate optional scope adds no row qualification. Defer the
 -- complete original scope, including its parameter-presence semantics.
 IF operator='optional' AND NOT EXISTS(
 WITH RECURSIVE descendants(n) AS (SELECT node UNION ALL SELECT value FROM descendants p CROSS JOIN LATERAL jsonb_array_elements(coalesce(p.n->'children','[]')))
 SELECT FROM descendants WHERE n->>'operator' IS NULL OR n->>'operator' NOT IN ('optional','all','scan','covers','cardinality','collection','forall','same','distinct')) THEN
 RETURN jsonb_build_object('operator','all','children','[]'::jsonb); END IF;
 IF operator='optional' AND (cardinality(names)<>1 OR EXISTS(
 WITH RECURSIVE descendants(n) AS (SELECT node UNION ALL SELECT value FROM descendants p CROSS JOIN LATERAL jsonb_array_elements(coalesce(p.n->'children','[]')))
 SELECT FROM descendants WHERE n->>'operator' NOT IN ('optional','all','scan','join','equal','literal','range','membership'))) THEN
 RAISE EXCEPTION 'optional population filter is not a closed row-local predicate'; END IF;
 -- Children are conjunctive even on aggregate and cross-role nodes. Preserve
 -- their row-local restrictions before projecting the node's own predicate.
 FOR child IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP
 projected:=ops.ddo_population_filter(child,role,choices);
 IF projected<>jsonb_build_object('operator','all','children','[]'::jsonb) THEN children:=children||jsonb_build_array(projected); END IF;
 END LOOP;
 names:=ops.ddo_binding_roles(node-'children');
 IF operator IN ('join','equal','literal','range','membership') AND cardinality(names)<=1 THEN
 IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(node->'operands','[]')) operand WHERE operand->>'kind'='population') THEN
 RAISE EXCEPTION 'selected population filter requires explicit non-circular membership operands'; END IF;
 children:=children||jsonb_build_array(node-'children');
 END IF;
 RETURN jsonb_build_object('operator',CASE WHEN operator='optional' THEN 'optional' ELSE 'all' END,'children',children);
END $$;

CREATE OR REPLACE FUNCTION ops.select_data_population(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; obligation ops.data_obligation; demand ops.data_demand; parent ops.data_population; boundary ops.data_demand_read;
 selected ops.data_population; source_request ops.data_request; archived jsonb; projection jsonb; operation jsonb;
 compiled jsonb; selection jsonb; expression jsonb; context jsonb; refs jsonb; role text; roledef jsonb; predicate jsonb;
 universe jsonb; row_value jsonb; expected jsonb; members jsonb:='[]'; evidence jsonb; meaning jsonb;
 scope jsonb; archive_digest text; value_key text; key text; count_roles integer;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['obligation_id','population_name','parent_population_id','read_id']);
 SELECT * INTO STRICT obligation FROM ops.data_obligation WHERE id=p->>'obligation_id';
 p:=p||jsonb_build_object('demand_id',obligation.demand_id,'operation_id',obligation.operation_id,'subject',obligation.subject,'original_source',obligation.original_source);
 SELECT * INTO STRICT demand FROM ops.data_demand WHERE id=p->>'demand_id';
 SELECT * INTO STRICT parent FROM ops.data_population WHERE id=p->>'parent_population_id' AND demand_id=demand.id;
 SELECT r.* INTO STRICT source_request FROM ops.data_request r JOIN ops.data_derivation episode ON episode.request_id=r.id WHERE episode.id=parent.evidence->>'derivation_id';
 -- The parent episode supplies authentic source support; this read-derived receipt
 -- introduces no producing task or inference episode.
 scope:=ops.ddo_lock_support(demand.project_id,p->>'original_source',jsonb_build_array(jsonb_build_object('derivation_id',parent.evidence->>'derivation_id')));
 PERFORM ops.ddo_require_active_demand(demand.id);
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p->>'read_id' AND demand_id=demand.id;
 IF NOT boundary.trust_snapshot @> scope OR NOT ops.ddo_read_visible(parent.created_at,parent.created_xid,boundary)
 OR NOT ops.ddo_population_valid(parent,boundary) OR source_request.project_id IS DISTINCT FROM demand.project_id
 OR parent.evidence ? 'selection' OR parent.name=p->>'population_name' THEN RAISE EXCEPTION 'selected population lacks its pinned admitted base parent'; END IF;
 scope:=boundary.trust_snapshot;
 PERFORM ops.ddo_authorize(kind.universe) FROM kb.data_product product JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract WHERE product.id=parent.evidence->>'product_id';
 SELECT value INTO STRICT selection FROM jsonb_array_elements(demand.selection->'operations') WHERE value->>'operation'=p->>'operation_id';
 SELECT convert_from(content,'UTF8')::jsonb,encode(sha256(content),'hex') INTO STRICT archived,archive_digest FROM sem.artifact WHERE release_id=demand.release_id AND artifact_name='data_operations.json';
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT projection FROM sem.artifact WHERE release_id=demand.release_id AND artifact_name='data_operation_native_definitions.json';
 IF projection->>'model_digest' IS DISTINCT FROM archive_digest THEN RAISE EXCEPTION 'population source model differs'; END IF;
 SELECT value INTO STRICT operation FROM jsonb_array_elements(archived->'operations') WHERE value->>'semantic_id'=p->>'operation_id';
 SELECT value INTO STRICT compiled FROM jsonb_array_elements(projection->'operations') WHERE value->>'operation_id'=p->>'operation_id';
 SELECT value->'expression' INTO STRICT expression FROM jsonb_array_elements(archived->'bindings') WHERE value->>'semantic_id'=operation->>'binding';
 IF compiled->'binding' IS DISTINCT FROM expression OR compiled->>'definition' IS DISTINCT FROM selection->>'definition'
 OR compiled->>'eligibility' IS DISTINCT FROM selection->>'eligibility' THEN RAISE EXCEPTION 'population filter differs from frozen definition'; END IF;
 context:=jsonb_build_object('model',archived,'roledefs',compiled->'input_roles','parameters',selection->'parameters',
 'parameter_meaning',selection->'parameter_meaning','parameterdefs',operation->'parameters'->'json','choices',selection->'choices',
 'subject',p->>'subject','original_source',p->>'original_source','roles','{}'::jsonb,'populations','{}'::jsonb,'witnesses','{}'::jsonb);
 refs:=ops.ddo_binding_population_refs(expression,context);
 SELECT count(*),min(e.key) INTO count_roles,role FROM jsonb_each_text(refs) e WHERE e.value=p->>'population_name';
 IF count_roles<>1 THEN RAISE EXCEPTION 'selected population name must identify one frozen active role'; END IF;
 SELECT value INTO STRICT roledef FROM jsonb_array_elements(compiled->'input_roles') WHERE value->>'name'=role;
 predicate:=ops.ddo_population_filter(expression,role,selection->'choices');
 IF NOT EXISTS(WITH RECURSIVE prerequisites(id) AS (
 SELECT value FROM jsonb_array_elements_text(selection->'dependencies')
 UNION SELECT dependency.value FROM prerequisites prerequisite JOIN LATERAL jsonb_array_elements(demand.selection->'operations') chosen ON chosen->>'operation'=prerequisite.id CROSS JOIN LATERAL jsonb_array_elements_text(chosen->'dependencies') dependency(value))
 SELECT FROM prerequisites WHERE id=source_request.operation_id) OR NOT EXISTS(
 SELECT FROM jsonb_array_elements(demand.selection->'discovery') relation WHERE relation->>'population'=parent.name
 AND relation->>'producer'=source_request.operation_id AND relation->>'output_role'=parent.evidence->>'member_role') THEN
 RAISE EXCEPTION 'selected parent is not a declared prerequisite discovery population'; END IF;
 IF NOT EXISTS(SELECT FROM kb.data_product product JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract
 WHERE product.id=parent.evidence->>'product_id' AND kind.member_contracts ? (roledef->>'kind_contract')) THEN
 RAISE EXCEPTION 'selected parent does not declare the role member kind'; END IF;
 IF (source_request.subject,source_request.original_source,source_request.analyzed_scope) IS DISTINCT FROM (obligation.subject,obligation.original_source,obligation.analyzed_scope) AND NOT EXISTS(
 SELECT FROM jsonb_array_elements(coalesce(demand.selection->'source_sets'->(roledef->'support'->>'source_set'),'[]')) entry
 WHERE entry->>'project_id'=demand.project_id AND entry->>'original_source'=source_request.original_source AND entry->>'product'=parent.evidence->>'product_id') THEN
 RAISE EXCEPTION 'selected parent source is outside the role frozen source set'; END IF;
 PERFORM ops.ddo_authorize(kind.universe) FROM sem.data_kind_contract kind WHERE kind.kind_contract=roledef->>'kind_contract';
 SELECT coalesce(jsonb_agg(to_jsonb(v)),'[]') INTO universe FROM ops.data_binding_rows(demand.id,p->>'operation_id',scope,boundary.id,p->>'subject',p->>'original_source') v
 WHERE v.product=parent.evidence->>'product_id' AND v.kind_contract=roledef->>'kind_contract'
 AND v.support_episodes ? (parent.evidence->>'derivation_id') AND v.support_evidence->>'use_id'=parent.evidence->>'admission_use_id';
 FOR expected IN SELECT value FROM jsonb_array_elements(parent.members) LOOP
 SELECT to_jsonb(m) INTO row_value FROM kb.data_product_member m WHERE m.product_id=parent.evidence->>'product_id' AND m.member_id=expected->>'member_id' AND m.kind_contract=roledef->>'kind_contract';
 IF row_value IS NULL THEN CONTINUE; END IF;
 IF NOT coalesce(ops.ddo_binding_source(roledef,jsonb_build_object('product',parent.evidence->>'product_id','member',row_value->>'member_id','subject',row_value->>'subject','original_source',row_value->>'original_source','analyzed_scope',row_value->'analyzed_scope','meaning_body',row_value->'body'),obligation.original_source,coalesce(demand.selection->'source_sets','{}')),false) THEN CONTINUE; END IF;
 IF ops.ddo_binding_subject(roledef,jsonb_build_object('subject',row_value->>'subject','meaning_body',row_value->'body'),p->>'subject') IS NULL THEN RAISE EXCEPTION 'population subject relationship is unknown'; END IF;
 IF NOT ops.ddo_binding_subject(roledef,jsonb_build_object('subject',row_value->>'subject','meaning_body',row_value->'body'),p->>'subject') THEN CONTINUE; END IF;
 SELECT value INTO row_value FROM jsonb_array_elements(universe) value WHERE value->>'member'=expected->>'member_id' LIMIT 1;
 IF row_value IS NULL THEN RAISE EXCEPTION 'parent population member facts unavailable in pinned read'; END IF;
 IF ops.ddo_binding_test(predicate,jsonb_set(context,ARRAY['roles',role],jsonb_build_array(row_value))) THEN members:=members||jsonb_build_array(expected); END IF;
 END LOOP;
 meaning:=jsonb_build_object('parent',parent.semantic_key,'operation',p->>'operation_id','kind_contract',roledef->>'kind_contract',
 'role',role,'subject',p->>'subject','original_source',p->>'original_source','analyzed_scope',obligation.analyzed_scope,'filter',predicate,'parameters',selection->'parameter_meaning',
 'members',members,'complete',parent.complete);
 value_key:='population-value:'||ops.ddo_digest(meaning);
 SELECT * INTO selected FROM ops.data_population old WHERE old.demand_id=demand.id AND old.name=p->>'population_name'
 AND old.selected_obligation_id=obligation.id AND old.semantic_key=value_key AND old.evidence->'selection'->>'parent_population_id'=parent.id AND ops.ddo_population_valid(old) ORDER BY old.created_at DESC,old.id DESC LIMIT 1;
 IF selected.id IS NULL THEN
 evidence:=(parent.evidence-'population_id')||jsonb_build_object('producer_context',ops.ddo_population_producer_context(parent),'selection',jsonb_build_object('parent_population_id',parent.id,
 'read_id',boundary.id,'obligation_id',obligation.id,'operation_id',p->>'operation_id','subject',p->>'subject','original_source',p->>'original_source','analyzed_scope',obligation.analyzed_scope,'role',role,
 'definition',selection->>'definition','eligibility',selection->>'eligibility','filter',predicate,'parameter_meaning',selection->'parameter_meaning','choices',selection->'choices'));
 key:='population:'||ops.ddo_digest(jsonb_build_array(demand.id,p->>'population_name',value_key,evidence));
 evidence:=evidence||jsonb_build_object('population_id',key);
 INSERT INTO ops.data_population (id,demand_id,selected_obligation_id,semantic_key,name,members,complete,evidence,created_at,created_xid) VALUES(key,demand.id,obligation.id,value_key,p->>'population_name',members,parent.complete,evidence,clock_timestamp(),pg_current_xact_id()::text) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT selected FROM ops.data_population WHERE id=key;
 END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('population_id',selected.id,'name',selected.name,'semantic_key',selected.semantic_key,
 'members',selected.members,'complete',selected.complete,'evidence',selected.evidence));
END $$;

CREATE OR REPLACE FUNCTION sem.data_operation_native_descriptor() RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('version','data-operation-native-v1','source_digest','__DDO_SOURCE_DIGEST__')
$$;
CREATE OR REPLACE FUNCTION sem.admit_data_operation_definitions(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; k jsonb; o jsonb; archived jsonb; old sem.data_kind_contract; operation jsonb; expected_inputs jsonb; expected_outputs jsonb; expected_support jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['release_id','model_digest','native_digest','kinds','operations']);
 IF p->>'native_digest' IS DISTINCT FROM sem.data_operation_native_descriptor()->>'source_digest' THEN RAISE EXCEPTION 'native source correspondence mismatch'; END IF;
 SELECT convert_from(content,'UTF8')::jsonb INTO archived FROM sem.artifact WHERE release_id=p->>'release_id' AND artifact_name='data_operations.json' AND encode(sha256(content),'hex')=p->>'model_digest';
 IF archived IS NULL THEN RAISE EXCEPTION 'effective operation archive is absent or differs'; END IF;
 IF NOT EXISTS(SELECT FROM sem.artifact a WHERE a.release_id=p->>'release_id'
 AND a.artifact_name='data_operation_native_definitions.json'
 AND convert_from(a.content,'UTF8')::jsonb=p-'release_id') THEN
 RAISE EXCEPTION 'native definition projection differs from authenticated release artifact'; END IF;
 FOR k IN SELECT value FROM jsonb_array_elements(p->'kinds') LOOP
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(archived->'kinds') kind WHERE kind->>'semantic_id'=k->>'kind' AND coalesce(kind->'facts'->'json'->>'universe','ordinary')=k->>'universe' AND coalesce(kind->'facts'->'json'->'projection_families','[]')=k->'families') THEN RAISE EXCEPTION 'kind purpose/projection policy differs from archived facts'; END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(archived->'identities') a WHERE a->>'owner'=k->>'kind' AND a->>'domain'='kind' AND a->>'key'=k->>'kind_contract') THEN RAISE EXCEPTION 'kind identity differs from archived effective model'; END IF;
 INSERT INTO sem.data_kind_contract VALUES(k->>'kind_contract',k->>'kind',k->'body_schema',k->'meaning_schema',k->'member_schema',k->'member_contracts',k->'families',k->>'universe') ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT old FROM sem.data_kind_contract WHERE kind_contract=k->>'kind_contract';
 IF (old.kind,old.universe) IS DISTINCT FROM (k->>'kind',k->>'universe') OR old.body_schema IS DISTINCT FROM k->'body_schema' OR old.meaning_schema IS DISTINCT FROM k->'meaning_schema' OR old.member_schema IS DISTINCT FROM k->'member_schema' OR old.member_contracts IS DISTINCT FROM k->'member_contracts' OR old.families IS DISTINCT FROM k->'families' THEN RAISE EXCEPTION 'kind contract changed under stable identity'; END IF;
 INSERT INTO sem.data_kind_release VALUES(p->>'release_id',old.kind_contract) ON CONFLICT DO NOTHING;
 END LOOP;
 FOR o IN SELECT value FROM jsonb_array_elements(p->'operations') LOOP
 SELECT value INTO STRICT operation FROM jsonb_array_elements(archived->'operations') op WHERE op->>'semantic_id'=o->>'operation_id';
 SELECT coalesce(jsonb_agg(role||jsonb_build_object('kind_contract',(SELECT id->>'key' FROM jsonb_array_elements(archived->'identities') id WHERE id->>'owner'=role->>'kind' AND id->>'domain'='kind'),'identity_requirements',coalesce(role->'support'->'identity_requirements','[]')) ORDER BY ord),'[]') INTO expected_inputs FROM jsonb_array_elements(operation->'roles') WITH ORDINALITY entry(role,ord) WHERE role->>'direction'='input';
 SELECT coalesce(jsonb_agg(role||jsonb_build_object('kind_contract',(SELECT id->>'key' FROM jsonb_array_elements(archived->'identities') id WHERE id->>'owner'=role->>'kind' AND id->>'domain'='kind'),'identity_requirements',coalesce(role->'support'->'identity_requirements','[]')) ORDER BY ord),'[]') INTO expected_outputs FROM jsonb_array_elements(operation->'roles') WITH ORDINALITY entry(role,ord) WHERE role->>'direction'='output';
 expected_support:=jsonb_build_object('policy',operation->'support_policy','outcomes',operation->'outcomes','replicate_policy',operation->'replicate_policy','state_dimensions',operation->'state_dimensions','transitions',operation->'transitions','effects',operation->'effects','provenance',CASE WHEN EXISTS(SELECT FROM jsonb_array_elements(operation->'roles') role WHERE role->'support'<>'null'::jsonb AND role->'support'->>'provenance'<>'value_substitution') THEN 'exact' ELSE 'value_substitution' END);
 IF o->'input_roles' IS DISTINCT FROM expected_inputs OR o->'output_roles' IS DISTINCT FROM expected_outputs
 OR o->'support_contract' IS DISTINCT FROM expected_support OR o->'profile' IS DISTINCT FROM operation->'profile'
 OR o->'binding' IS DISTINCT FROM (SELECT binding->'expression' FROM jsonb_array_elements(archived->'bindings') binding WHERE binding->>'semantic_id'=operation->>'binding')
 OR o->>'definition' IS DISTINCT FROM (SELECT id->>'key' FROM jsonb_array_elements(archived->'identities') id WHERE id->>'owner'=o->>'operation_id' AND id->>'domain'='definition')
 OR o->>'eligibility' IS DISTINCT FROM (SELECT id->>'key' FROM jsonb_array_elements(archived->'identities') id WHERE id->>'owner'=o->>'operation_id' AND id->>'domain'='eligibility')
 OR o->>'implementation_revision' IS DISTINCT FROM coalesce((SELECT id->>'key' FROM jsonb_array_elements(archived->'identities') id WHERE id->>'owner'=operation->>'implementation_root' AND id->>'domain'='implementation-slice'),operation->>'behavior') THEN RAISE EXCEPTION 'native definition projection disagrees with archived operation facts'; END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(archived->'identities') a WHERE a->>'owner'=o->>'operation_id' AND a->>'domain'='recipe' AND a->>'key'=o->>'recipe') THEN RAISE EXCEPTION 'recipe differs from archived effective model'; END IF;
 INSERT INTO sem.data_operation_definition VALUES(p->>'release_id',o->>'operation_id',o->>'recipe',o->>'profile',o->>'implementation_revision',o->'input_roles',o->'output_roles',o->'support_contract') ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM sem.data_operation_definition d WHERE d.release_id=p->>'release_id' AND d.operation_id=o->>'operation_id' AND d.recipe=o->>'recipe' AND d.profile=o->>'profile' AND d.implementation_revision=o->>'implementation_revision' AND d.input_roles=o->'input_roles' AND d.output_roles=o->'output_roles' AND d.support_contract=o->'support_contract') THEN RAISE EXCEPTION 'operation definition changed under admitted release'; END IF;
 END LOOP;
 RETURN jsonb_build_object('release_id',p->>'release_id','model_digest',p->>'model_digest');
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_kind_access(contract text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE universe text;
BEGIN
 SELECT kind.universe INTO STRICT universe FROM sem.data_kind_contract kind WHERE kind.kind_contract=contract;
 PERFORM ops.ddo_authorize(universe);
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION ops.data_binding_rows(p_demand text,p_operation text,p_trust jsonb,p_read text DEFAULT NULL,p_subject text DEFAULT NULL,p_source text DEFAULT NULL)
RETURNS TABLE(product text,kind_contract text,subject text,original_source text,analyzed_scope jsonb,coverage jsonb,support_episodes jsonb,support_evidence jsonb,"position" bigint,multiplicity bigint,member text,provider_identity text,alternative_identity text,body jsonb,meaning_body jsonb)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE d ops.data_demand; snapshot jsonb; boundary ops.data_demand_read;
BEGIN
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p_demand;
 IF p_read IS NOT NULL THEN SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p_read AND demand_id=d.id; END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') selected WHERE selected->>'operation'=p_operation) THEN RAISE EXCEPTION 'projection operation outside frozen demand'; END IF;
 SELECT coalesce(jsonb_object_agg(scope.scope,scope.epoch),'{}') INTO snapshot FROM ops.data_trust_scope scope WHERE scope.project_id=d.project_id AND EXISTS(SELECT FROM (SELECT value FROM jsonb_array_elements(d.root) UNION ALL SELECT entry FROM jsonb_each(coalesce(d.selection->'source_sets','{}')) named CROSS JOIN LATERAL jsonb_array_elements(named.value) entry) roots(root) WHERE scope.scope=ops.ddo_scope(d.project_id,root->>'original_source'));
 IF snapshot IS DISTINCT FROM p_trust OR (boundary.id IS NOT NULL AND boundary.trust_snapshot IS DISTINCT FROM snapshot) THEN RAISE EXCEPTION 'binding trust snapshot changed'; END IF;
 PERFORM ops.ddo_authorize(kind.universe) FROM sem.data_operation_definition operation CROSS JOIN LATERAL jsonb_array_elements(operation.input_roles) input_role(value) JOIN sem.data_kind_contract kind ON kind.kind_contract=input_role.value->>'kind_contract' WHERE operation.release_id=d.release_id AND operation.operation_id=p_operation;
 RETURN QUERY
 WITH admitted AS MATERIALIZED (
  SELECT x.id AS product_id,x.kind_contract AS parent_kind,x.subject AS parent_subject,x.original_source AS parent_source,x.analyzed_scope AS parent_scope,x.canonical_body,
   outp.member_id AS output_member,outp.position AS output_position,outp.multiplicity AS output_multiplicity,episode.id AS episode_id,u.id AS use_id,producer.operation_id AS producer_operation
  FROM ops.demand_use u JOIN ops.data_derivation episode ON episode.id=u.derivation_id
  JOIN ops.data_request producer ON producer.id=episode.request_id
  JOIN ops.data_derivation_output outp ON outp.derivation_id=episode.id JOIN kb.data_product x ON x.id=outp.product_id
  WHERE u.demand_id=d.id AND u.fate='fulfilled' AND x.project_id=d.project_id
   AND (boundary.id IS NULL OR ops.ddo_read_visible(u.created_at,u.created_xid,boundary))
   AND ops.ddo_use_valid(u,boundary)
   AND EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') selected WHERE selected->>'operation'=p_operation AND (jsonb_array_length(selected->'dependencies')=0 OR selected->'dependencies' ? producer.operation_id))
   AND NOT EXISTS(SELECT FROM ops.demand_use later WHERE later.obligation_id=u.obligation_id AND (later.created_at,later.id)>(u.created_at,u.id) AND (boundary.id IS NULL OR ops.ddo_read_visible(later.created_at,later.created_xid,boundary)))
 ), candidates AS MATERIALIZED (
  SELECT a.product_id,a.parent_kind,projected.*,a.episode_id,a.use_id,a.producer_operation,
   coalesce(member_role.position,a.output_position)::bigint AS occurrence_position,
   coalesce(member_role.multiplicity,a.output_multiplicity)::bigint AS occurrence_multiplicity
  FROM admitted a CROSS JOIN LATERAL (
   SELECT NULL::text AS member_id,a.parent_kind AS projected_kind,a.parent_subject AS projected_subject,a.parent_source AS projected_source,a.parent_scope AS projected_scope,a.canonical_body AS projected_body WHERE a.output_member IS NULL
   UNION ALL
   SELECT m.member_id,m.kind_contract,m.subject,m.original_source,m.analyzed_scope,m.body FROM kb.data_product_member m WHERE m.product_id=a.product_id AND (a.output_member IS NULL OR a.output_member=m.member_id)
  ) projected
  LEFT JOIN kb.data_member_role member_role ON member_role.product_id=a.product_id AND member_role.member_id=projected.member_id
  WHERE EXISTS(SELECT FROM sem.data_operation_definition operation
   CROSS JOIN LATERAL jsonb_array_elements(operation.input_roles) input_role(value)
   WHERE operation.release_id=d.release_id AND operation.operation_id=p_operation
   AND input_role.value->>'kind_contract'=projected.projected_kind
   AND (p_subject IS NULL OR ops.ddo_binding_subject(input_role.value,
    jsonb_build_object('subject',projected.projected_subject,'meaning_body',projected.projected_body),p_subject))
   AND ops.ddo_binding_source(input_role.value,jsonb_build_object('product',a.product_id,'member',projected.member_id,'subject',projected.projected_subject,'original_source',projected.projected_source,'analyzed_scope',projected.projected_scope,'meaning_body',projected.projected_body),p_source,coalesce(d.selection->'source_sets','{}')))
 )
 SELECT candidate.product_id,candidate.projected_kind,candidate.projected_subject,candidate.projected_source,candidate.projected_scope,
  coalesce((SELECT jsonb_agg(to_jsonb(coverage_row)-'product_id'-'member_id' ORDER BY coverage_row.ordinal) FROM kb.data_member_coverage coverage_row WHERE coverage_row.product_id=candidate.product_id AND coverage_row.member_id=candidate.member_id),'[]'),
  jsonb_build_array(candidate.episode_id),jsonb_build_object('demand_id',d.id,'use_id',candidate.use_id,'trust_snapshot',snapshot,'read_id',boundary.id,'read_snapshot',boundary.read_snapshot,'frontier_at',boundary.frontier_at),
  candidate.occurrence_position,candidate.occurrence_multiplicity,candidate.member_id,NULL::text,candidate.producer_operation,data.ddo_json(candidate.projected_body),candidate.projected_body
 FROM candidates candidate
 WHERE ops.ddo_kind_access(candidate.parent_kind) AND ops.ddo_kind_access(candidate.projected_kind);
END $$;
