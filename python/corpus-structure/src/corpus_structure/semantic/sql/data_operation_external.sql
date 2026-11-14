-- External computation shares the native request/task/attempt/publication owner.
-- These immutable rows retain custody; they do not schedule a second semantic queue.
CREATE OR REPLACE FUNCTION ops.ddo_external_input_rows(r ops.data_request) RETURNS SETOF jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('role',item->>'role','position',item->'position','multiplicity',item->'multiplicity',
 'product_id',product.id,'member_id',item->'member_id','kind_contract',coalesce(member.kind_contract,product.kind_contract),
 'subject',coalesce(member.subject,product.subject),'original_source',coalesce(member.original_source,product.original_source),
 'analyzed_scope',CASE WHEN member.member_id IS NULL THEN product.analyzed_scope ELSE member.analyzed_scope END,
 'meaning',coalesce(member.body,product.canonical_body))
 FROM jsonb_array_elements(r.binding->'inputs') WITH ORDINALITY inputs(item,ordinal)
 JOIN kb.data_product product ON product.id=item->>'product_id'
 LEFT JOIN kb.data_product_member member ON member.product_id=product.id AND member.member_id=item->>'member_id'
 WHERE item->>'member_id' IS NULL OR member.member_id IS NOT NULL
 ORDER BY ordinal
$$;

CREATE OR REPLACE FUNCTION ops.ddo_external_receipt_value(receipt ops.data_external_receipt) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('version','external-execution-receipt-v1','receipt_id',receipt.id,
 'packet_id',receipt.packet_id,'packet_digest',receipt.packet_digest,'request_id',receipt.request_id,
 'generation',receipt.generation,'task_id',receipt.task_id,'attempt',receipt.attempt,'holder',receipt.holder,
 'runtime_id',receipt.runtime_id,'admitting_principal',receipt.admitting_principal,
 'actor_assertion',receipt.actor_assertion,'model_assertion',receipt.model_assertion,'result_digest',receipt.result_digest)
$$;

CREATE OR REPLACE FUNCTION ops.ddo_assert_external_active(r ops.data_request) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM sem.require_runtime_binding(r.release_id,r.runtime_id);
 IF EXISTS(SELECT FROM ops.data_revocation v WHERE v.scope=ops.ddo_scope(r.project_id,r.original_source)
 AND ((v.selector_kind='runtime' AND v.selector=r.runtime_id) OR (v.selector_kind='recipe' AND v.selector=r.recipe))) THEN
 RAISE EXCEPTION 'external producing runtime or recipe was directly revoked'; END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.retain_external_data_packet(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; definition sem.data_operation_definition;
 old ops.data_external_packet; packet jsonb; inputs jsonb; contracts jsonb; key text; count_ bigint; size_ bigint; forbidden boolean; snapshot jsonb;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['request_id','generation','task_id','attempt','holder','runtime_id','max_bytes']);
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=p->>'request_id';
 PERFORM ops.ddo_authorize_request(r);
 key:='external-packet:'||ops.ddo_digest(jsonb_build_array(r.id,(p->>'generation')::bigint));
 -- Exact packet retention replay is historical custody, not new fulfillment.
 SELECT * INTO old FROM ops.data_external_packet WHERE id=key AND request_id=r.id AND generation=(p->>'generation')::bigint;
 IF FOUND THEN RETURN jsonb_build_object('payload',jsonb_build_object('packet_id',old.id,'packet_digest',old.payload_digest,'state','awaiting-external')); END IF;
 snapshot:=ops.ddo_lock_support(r.project_id,r.original_source,r.binding->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 t:=ops.ddo_claim(r,p);
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF definition.support_contract->'external' IS NULL OR p->>'runtime_id'<>r.runtime_id THEN RAISE EXCEPTION 'request has no matching admitted external protocol/runtime'; END IF;
 PERFORM ops.ddo_assert_external_active(r);
 PERFORM ops.ddo_assert_support(r,r.binding->'support');
 IF EXISTS(WITH RECURSIVE exposed(kind_contract) AS (
 SELECT role->>'kind_contract' FROM jsonb_array_elements(definition.input_roles||definition.output_roles) role
 UNION SELECT child.value FROM exposed JOIN sem.data_kind_contract parent USING(kind_contract)
 CROSS JOIN LATERAL jsonb_array_elements_text(parent.member_contracts) child(value)
 ) SELECT FROM exposed JOIN sem.data_kind_contract kind USING(kind_contract) WHERE kind.universe='evaluator')
 OR EXISTS(SELECT FROM jsonb_array_elements(r.binding->'inputs') item JOIN kb.data_product_member member ON member.product_id=item->>'product_id' JOIN sem.data_kind_contract kind ON kind.kind_contract=member.kind_contract WHERE item->>'member_id' IS NULL AND kind.universe='evaluator') THEN RAISE EXCEPTION 'protected evaluator data cannot enter an external packet'; END IF;
 SELECT count(*),coalesce(sum(octet_length(data.canonical_json(input))),0),coalesce(bool_or(kind.universe='evaluator' OR role.value IS NULL OR NOT (role.value->'accepted_kind_contracts' ? (input->>'kind_contract'))),false)
 INTO count_,size_,forbidden FROM ops.ddo_external_input_rows(r) input
 JOIN sem.data_kind_contract kind ON kind.kind_contract=input->>'kind_contract'
 LEFT JOIN LATERAL (SELECT value FROM jsonb_array_elements(definition.input_roles) WHERE value->>'name'=input->>'role') role ON true;
 IF count_<>jsonb_array_length(r.binding->'inputs') OR forbidden THEN RAISE EXCEPTION 'external packet input differs from exact admitted role/kind membership'; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('role',role->>'name','kind_contract',role->>'kind_contract','schema',kind.body_schema,'minimum',role->'minimum','maximum',role->'maximum','collection',role->'collection') ORDER BY ordinal),'[]') INTO contracts
 FROM jsonb_array_elements(definition.output_roles) WITH ORDINALITY outputs(role,ordinal) JOIN sem.data_kind_contract kind ON kind.kind_contract=role->>'kind_contract';
 IF size_+octet_length(data.canonical_json(r.binding))+octet_length(data.canonical_json(contracts))+octet_length(data.canonical_json(definition.support_contract->'external'))>(p->>'max_bytes')::integer THEN RAISE EXCEPTION 'external packet exceeds owned packet capacity'; END IF;
 SELECT coalesce(jsonb_agg(input),'[]') INTO inputs FROM ops.ddo_external_input_rows(r) input;
 packet:=jsonb_build_object('version','external-data-packet-v1','packet_id',key,'request_id',r.id,'request_key',r.request_key,'generation',r.generation,
 'task_id',t.id,'project_id',r.project_id,'release_id',r.release_id,'runtime_id',r.runtime_id,'operation_id',r.operation_id,'recipe',r.recipe,
 'implementation_revision',definition.implementation_revision,'subject',r.subject,'original_source',r.original_source,'analyzed_scope',r.analyzed_scope,
 'binding',r.binding,'protocol',definition.support_contract->'external','inputs',inputs,'result_contract',contracts,'outcomes',definition.support_contract->'outcomes');
 IF octet_length(data.canonical_json(packet))>(p->>'max_bytes')::integer THEN RAISE EXCEPTION 'complete external packet exceeds owned packet capacity'; END IF;
 INSERT INTO ops.data_external_packet VALUES(key,r.id,r.generation,t.id,t.attempt,t.claimed_by,r.runtime_id,packet,ops.ddo_digest(packet),clock_timestamp());
 -- Waiting for the external actor is derived from packet custody; the physical
 -- task reuses its ordinary released state and retains its exact attempt fence.
 UPDATE ops.task SET status='pending',lease_until=NULL WHERE id=t.id;
 RETURN jsonb_build_object('payload',jsonb_build_object('packet_id',key,'packet_digest',ops.ddo_digest(packet),'state','awaiting-external'));
END $$;

CREATE OR REPLACE FUNCTION ops.read_external_data_queue(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; lim integer:=coalesce((p_payload->>'limit')::integer,1); result jsonb; row_ record;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['project_id'],ARRAY['demand_id','limit']);
 IF lim NOT BETWEEN 1 AND 64 THEN RAISE EXCEPTION 'invalid external queue bound'; END IF;
 result:='[]';
 FOR row_ IN SELECT packet.id,packet.payload_digest,packet.request_id,packet.generation,packet.task_id,request.operation_id,request.subject FROM ops.data_external_packet packet
 JOIN ops.data_request request ON (request.id,request.generation,request.live_task_id)=(packet.request_id,packet.generation,packet.task_id)
 JOIN ops.task task ON task.id=packet.task_id
 WHERE request.project_id=p->>'project_id' AND ops.ddo_request_useful(request)
 AND (task.status='pending' OR (task.status='running' AND task.lease_until<=clock_timestamp()))
 AND NOT EXISTS(SELECT FROM ops.data_external_receipt receipt WHERE receipt.packet_id=packet.id)
 AND NOT EXISTS(SELECT FROM ops.data_revocation revoked WHERE revoked.scope=ops.ddo_scope(request.project_id,request.original_source)
 AND ((revoked.selector_kind='runtime' AND revoked.selector=request.runtime_id) OR (revoked.selector_kind='recipe' AND revoked.selector=request.recipe)))
 AND (NOT p ? 'demand_id' OR EXISTS(SELECT FROM ops.demand_use use_ WHERE use_.demand_id=p->>'demand_id' AND (use_.request_id,use_.generation)=(packet.request_id,packet.generation) AND use_.fate='attached' AND ops.ddo_demand_active(use_.demand_id)))
 ORDER BY packet.created_at,packet.id LIMIT lim LOOP
 PERFORM ops.ddo_authorize_request(request) FROM ops.data_request request WHERE request.id=row_.request_id;
 result:=result||jsonb_build_array(jsonb_build_object('packet_id',row_.id,'packet_digest',row_.payload_digest,'request_id',row_.request_id,'generation',row_.generation,'task_id',row_.task_id,'operation_id',row_.operation_id,'subject',row_.subject,'state','awaiting-external'));
 END LOOP;
 RETURN jsonb_build_object('payload',jsonb_build_object('packets',result));
END $$;


CREATE OR REPLACE FUNCTION ops.claim_external_data_packet(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; packet ops.data_external_packet; r ops.data_request;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['packet_id','project_id','holder','lease_seconds'],ARRAY['demand_id']);
 SELECT * INTO STRICT packet FROM ops.data_external_packet WHERE id=p->>'packet_id';
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=packet.request_id;
 PERFORM ops.ddo_authorize_request(r);
 IF r.project_id<>p->>'project_id' OR (p ? 'demand_id' AND NOT EXISTS(SELECT FROM ops.demand_use use_ WHERE use_.demand_id=p->>'demand_id' AND (use_.request_id,use_.generation)=(packet.request_id,packet.generation) AND use_.fate='attached' AND ops.ddo_demand_active(use_.demand_id))) THEN RAISE EXCEPTION 'external packet is outside the selected project/demand'; END IF;
 IF (r.generation,r.live_task_id) IS DISTINCT FROM (packet.generation,packet.task_id) THEN RETURN jsonb_build_object('payload',jsonb_build_object('state','no-work')); END IF;
 RETURN ops.claim_data_request(jsonb_build_object('request_id',r.id,'external_packet_id',packet.id,'holder',p->>'holder','lease_seconds',p->'lease_seconds'));
END $$;

CREATE OR REPLACE FUNCTION ops.read_external_data_packet(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; packet ops.data_external_packet; t ops.task; receipt ops.data_external_receipt;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['packet_id','request_id','generation','task_id','attempt','holder','max_bytes']);
 SELECT * INTO STRICT packet FROM ops.data_external_packet WHERE id=p->>'packet_id' AND request_id=p->>'request_id' AND generation=(p->>'generation')::bigint;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=packet.request_id;
 PERFORM ops.ddo_authorize_request(r);
 -- A producer may inspect/replay its already admitted exact result after a lost
 -- commit acknowledgement. This historical packet grants no new admission.
 SELECT * INTO receipt FROM ops.data_external_receipt WHERE packet_id=packet.id;
 IF receipt.id IS NOT NULL AND (receipt.request_id,receipt.generation,receipt.task_id,receipt.attempt,receipt.holder) IS NOT DISTINCT FROM (p->>'request_id',(p->>'generation')::bigint,(p->>'task_id')::bigint,(p->>'attempt')::bigint,p->>'holder') THEN
 IF octet_length(data.canonical_json(packet.payload))>(p->>'max_bytes')::integer THEN RAISE EXCEPTION 'historical external packet exceeds transport capacity'; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('packet_id',packet.id,'packet_digest',packet.payload_digest,'packet',packet.payload));
 END IF;
 PERFORM ops.ddo_lock_support(r.project_id,r.original_source,r.binding->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 t:=ops.ddo_claim(r,p);
 PERFORM ops.ddo_assert_external_active(r);
 PERFORM ops.ddo_assert_support(r,r.binding->'support');
 IF t.id<>packet.task_id OR packet.payload->'binding' IS DISTINCT FROM r.binding OR packet.payload->>'recipe'<>r.recipe THEN RAISE EXCEPTION 'external packet changed native request binding'; END IF;
 IF octet_length(data.canonical_json(packet.payload))>(p->>'max_bytes')::integer THEN RAISE EXCEPTION 'external packet exceeds transport capacity'; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('packet_id',packet.id,'packet_digest',packet.payload_digest,'packet',packet.payload));
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_require_external_completion(completion jsonb,r ops.data_request,producer_task bigint,producer_attempt bigint,producer_holder text) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE definition sem.data_operation_definition; receipt ops.data_external_receipt; wire jsonb; packet ops.data_external_packet;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF definition.support_contract->'external' IS NULL THEN
 IF coalesce(completion->'execution_evidence'->'external_receipts','[]')<>'[]'::jsonb THEN RAISE EXCEPTION 'non-external operation cannot assert an external receipt'; END IF;
 RETURN;
 END IF;
 IF jsonb_array_length(coalesce(completion->'execution_evidence'->'external_receipts','[]'))<>1
 OR coalesce(completion->'execution_evidence'->'host_receipts','[]')<>'[]'::jsonb
 OR coalesce(completion->'execution_evidence'->'cpu_receipts','[]')<>'[]'::jsonb
 OR coalesce(completion->'execution_evidence'->'provider_receipts','[]')<>'[]'::jsonb
 OR coalesce(completion->'execution_evidence'->'pdf_receipts','[]')<>'[]'::jsonb THEN RAISE EXCEPTION 'external completion requires exactly its genuine native admission receipt'; END IF;
 wire:=completion->'execution_evidence'->'external_receipts'->0;
 SELECT * INTO STRICT receipt FROM ops.data_external_receipt WHERE id=wire->>'receipt_id';
 SELECT * INTO STRICT packet FROM ops.data_external_packet WHERE id=receipt.packet_id;
 IF wire IS DISTINCT FROM ops.ddo_external_receipt_value(receipt)
 OR (receipt.request_id,receipt.generation,receipt.task_id,receipt.attempt,receipt.holder) IS DISTINCT FROM (r.id,r.generation,producer_task,producer_attempt,producer_holder)
 OR receipt.packet_digest<>packet.payload_digest OR packet.payload->'binding' IS DISTINCT FROM r.binding
 OR receipt.result_digest<>ops.ddo_digest(completion-'execution_evidence') THEN RAISE EXCEPTION 'external receipt is not bound to this exact packet/result/native producer'; END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.admit_external_data_result(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; packet ops.data_external_packet; receipt ops.data_external_receipt;
 completion jsonb; evidence jsonb; retained jsonb; digest_ text; key text; intent text;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['packet_id','request_id','generation','task_id','attempt','holder','actor_assertion','model_assertion','completion']);
 SELECT * INTO STRICT packet FROM ops.data_external_packet WHERE id=p->>'packet_id' AND request_id=p->>'request_id' AND generation=(p->>'generation')::bigint;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=packet.request_id;
 PERFORM ops.ddo_authorize_request(r);
 completion:=p->'completion';
 IF completion ? 'execution_evidence' THEN RAISE EXCEPTION 'external callers cannot manufacture execution custody'; END IF;
 digest_:=ops.ddo_digest(completion);
 SELECT * INTO receipt FROM ops.data_external_receipt WHERE packet_id=packet.id;
 IF FOUND THEN
 IF receipt.result_digest<>digest_ OR receipt.actor_assertion<>p->>'actor_assertion' OR receipt.model_assertion IS DISTINCT FROM p->>'model_assertion' THEN RAISE EXCEPTION 'external packet already retains a different immutable result/assertion'; END IF;
 SELECT id INTO STRICT intent FROM ops.data_completion_intent WHERE request_id=packet.request_id AND generation=packet.generation;
 RETURN jsonb_build_object('payload',jsonb_build_object('receipt',ops.ddo_external_receipt_value(receipt),'intent_id',intent));
 END IF;
 PERFORM ops.ddo_lock_support(r.project_id,r.original_source,r.binding->'support');
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=r.id FOR UPDATE;
 SELECT * INTO receipt FROM ops.data_external_receipt WHERE packet_id=packet.id;
 IF FOUND THEN
 IF receipt.result_digest<>digest_ OR receipt.actor_assertion<>p->>'actor_assertion' OR receipt.model_assertion IS DISTINCT FROM p->>'model_assertion' THEN RAISE EXCEPTION 'external packet already retains a different immutable result/assertion'; END IF;
 SELECT id INTO STRICT intent FROM ops.data_completion_intent WHERE request_id=packet.request_id AND generation=packet.generation;
 RETURN jsonb_build_object('payload',jsonb_build_object('receipt',ops.ddo_external_receipt_value(receipt),'intent_id',intent));
 END IF;
 t:=ops.ddo_claim(r,p);
 PERFORM ops.ddo_assert_external_active(r);
 PERFORM ops.ddo_assert_support(r,r.binding->'support');
 IF packet.payload->'binding' IS DISTINCT FROM r.binding OR packet.payload->>'recipe'<>r.recipe OR t.id<>packet.task_id
 OR packet.payload->'protocol'->>'requested_actor' IS DISTINCT FROM p->>'actor_assertion'
 OR packet.payload->'protocol'->>'requested_model' IS DISTINCT FROM p->>'model_assertion' THEN RAISE EXCEPTION 'external result differs from exact packet/native claim/actor/model assertion contract'; END IF;
 IF completion->'inputs' IS DISTINCT FROM r.binding->'inputs' OR completion->'support' IS DISTINCT FROM r.binding->'support'
 OR completion->>'implementation_revision' IS DISTINCT FROM packet.payload->>'implementation_revision' THEN RAISE EXCEPTION 'external result changes its immutable input/implementation binding'; END IF;
 key:='external-result:'||ops.ddo_digest(jsonb_build_array(packet.id,digest_));
 INSERT INTO ops.data_external_receipt VALUES(key,packet.id,packet.payload_digest,r.id,r.generation,t.id,t.attempt,t.claimed_by,packet.runtime_id,session_user,p->>'actor_assertion',p->>'model_assertion',digest_,clock_timestamp()) RETURNING * INTO receipt;
 evidence:=jsonb_build_object('version','native-execution-evidence-v1','request_id',r.id,'generation',r.generation,'task_id',t.id,'attempt',t.attempt,'holder',t.claimed_by,'runtime_id',packet.runtime_id,'host_receipts','[]'::jsonb,'cpu_receipts','[]'::jsonb,'pdf_receipts','[]'::jsonb,'provider_receipts','[]'::jsonb,'external_receipts',jsonb_build_array(ops.ddo_external_receipt_value(receipt)));
 completion:=completion||jsonb_build_object('execution_evidence',evidence);
 retained:=ops.retain_data_completion_intent(jsonb_build_object('request_id',r.id,'generation',r.generation,'task_id',t.id,'attempt',t.attempt,'holder',t.claimed_by,'runtime_id',packet.runtime_id,'completion',completion));
 RETURN jsonb_build_object('payload',jsonb_build_object('receipt',ops.ddo_external_receipt_value(receipt),'intent_id',retained->'payload'->>'intent_id'));
END $$;

CREATE OR REPLACE FUNCTION ops.inspect_external_data_result(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; packet ops.data_external_packet; receipt ops.data_external_receipt; intent text; publication jsonb; state_ text;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['packet_id']);
 SELECT * INTO STRICT packet FROM ops.data_external_packet WHERE id=p->>'packet_id';
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=packet.request_id;
 PERFORM ops.ddo_authorize_request(r);
 SELECT * INTO receipt FROM ops.data_external_receipt WHERE packet_id=packet.id;
 SELECT id INTO intent FROM ops.data_completion_intent WHERE request_id=packet.request_id AND generation=packet.generation;
 IF intent IS NOT NULL THEN publication:=ops.inspect_data_completion(jsonb_build_object('intent_id',intent,'request_id',packet.request_id,'generation',packet.generation))->'payload'; END IF;
 state_:=CASE WHEN publication->>'state'='committed' THEN 'committed' WHEN r.generation<>packet.generation THEN 'superseded' WHEN NOT ops.ddo_request_useful(r) THEN 'cancelled' WHEN receipt.id IS NOT NULL THEN 'retained' ELSE 'awaiting-external' END;
 RETURN jsonb_build_object('payload',jsonb_build_object('packet_id',packet.id,'state',state_,'receipt',CASE WHEN receipt.id IS NULL THEN NULL ELSE ops.ddo_external_receipt_value(receipt) END,'intent_id',intent,'publication',publication));
END $$;

CREATE OR REPLACE FUNCTION ops.release_external_data_packet(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; r ops.data_request; t ops.task; packet ops.data_external_packet;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['packet_id','request_id','generation','task_id','attempt','holder','reason']);
 SELECT * INTO STRICT packet FROM ops.data_external_packet WHERE id=p->>'packet_id' AND request_id=p->>'request_id' AND generation=(p->>'generation')::bigint;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=packet.request_id FOR UPDATE;
 PERFORM ops.ddo_authorize_request(r);
 SELECT * INTO STRICT t FROM ops.task WHERE id=packet.task_id FOR UPDATE;
 IF (r.generation,t.id,t.attempt,t.claimed_by) IS DISTINCT FROM ((p->>'generation')::bigint,(p->>'task_id')::bigint,(p->>'attempt')::bigint,p->>'holder') OR t.status NOT IN ('running','pending') THEN RAISE EXCEPTION 'external release lost its exact packet/attempt fence'; END IF;
 IF EXISTS(SELECT FROM ops.data_external_receipt WHERE packet_id=packet.id) THEN RAISE EXCEPTION 'retained external result requires publication reconciliation, not release'; END IF;
 -- Releasing logical permission does not assert an external actor/process stopped.
 UPDATE ops.task SET status='pending',lease_until=NULL,error=jsonb_build_object('external_release',p->>'reason','physical_retirement','not-asserted') WHERE id=t.id;
 RETURN jsonb_build_object('payload',jsonb_build_object('packet_id',packet.id,'state','awaiting-external','released',true));
END $$;
