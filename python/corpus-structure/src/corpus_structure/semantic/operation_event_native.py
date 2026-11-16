"""Finite native custody for current selected operation-event frames and parameters."""


def operation_event_native_sql() -> str:
    import json
    from dataclasses import asdict
    from corpus_structure.evaluate.declared_operation_events import (
        AUTHORIZATION_EFFECT, AUTHORIZATION_FACTORY, AUTHORIZATION_OPERATION, NAMESPACE,
    )

    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_operation_event_command_eligible(definition sem.data_operation_definition)
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $event$
 SELECT definition.operation_id='__AUTHORIZE__' AND definition.profile='command'
 AND definition.support_contract->'capabilities'->>'preparation'='native-publication'
 AND definition.support_contract->'capabilities'->'forms'='["scalar"]'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint'='__AUTHORIZE_FACTORY__'
 AND definition.support_contract->'effects'='__EFFECT__'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND definition.implementation_revision LIKE 'implementation-slice:%'
$event$;

CREATE OR REPLACE FUNCTION ops.ddo_operation_event_completion_scopes(r ops.data_request)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $event$
DECLARE question jsonb; specification jsonb; selected jsonb;
BEGIN
 IF r.operation_id='operation_event.frame' THEN
 question:=ops.ddo_record_grade_input(r,'question')->'body';
 FOR selected IN SELECT question->'original_selection' UNION SELECT question->'prediction_selection' LOOP
 IF selected->>'project_id' IS DISTINCT FROM r.project_id THEN
 RAISE EXCEPTION 'event frame cut belongs to another project' USING ERRCODE='23514'; END IF;
 RETURN QUERY SELECT * FROM ops.ddo_record_grade_cut_scopes(r.project_id,selected->>'cut_canonical_json');
 END LOOP;
 ELSIF r.operation_id='operation_event.fit' THEN
 specification:=ops.ddo_record_grade_input(r,'specification')->'body';
 selected:=specification->'frame'->'selection';
 RETURN QUERY SELECT * FROM ops.ddo_record_fit_cut_scopes(r.project_id,selected);
 END IF;
END $event$;

CREATE OR REPLACE FUNCTION ops.ddo_operation_event_dependency_scopes(episode text)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $event$
DECLARE r ops.data_request;
BEGIN
 SELECT request.* INTO STRICT r FROM ops.data_request request JOIN ops.data_derivation producer
 ON producer.request_id=request.id WHERE producer.id=episode;
 RETURN QUERY SELECT * FROM ops.ddo_operation_event_completion_scopes(r);
END $event$;

CREATE OR REPLACE FUNCTION ops.ddo_operation_event_require_frame(r ops.data_request,body jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $event$
DECLARE question_product kb.data_product; question jsonb; frame jsonb:=body->'frame'; selected jsonb;
 original_census jsonb; prediction_census jsonb; report_pin jsonb; source_pin jsonb; bound jsonb; actual jsonb;
 report_product kb.data_product; producer ops.data_derivation; definition sem.data_operation_definition;
 cpu_roles jsonb:=data.ddo_field(ops.ddo_cpu_input_basis(r),'roles'); role_meaning jsonb; u jsonb;
 reports_ jsonb:='[]'; sources_ jsonb:='[]';
BEGIN
 SELECT product.* INTO STRICT question_product FROM jsonb_array_elements(r.binding->'inputs') chosen
 JOIN kb.data_product product ON product.id=chosen->>'product_id' AND product.project_id=r.project_id
 JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract
 WHERE chosen->>'role'='question' AND chosen->>'member_id' IS NULL AND (chosen->>'multiplicity')::integer=1
 AND kind.kind='__NAMESPACE__DdoOperationEventQuestion' AND kind.universe='evaluator';
 question:=data.ddo_json(question_product.canonical_body);
 IF body->>'version' IS DISTINCT FROM 'selected-operation-event-frame-product-1'
 OR body->>'frame_digest' IS DISTINCT FROM encode(sha256(convert_to(body->>'frame_canonical_json','UTF8')),'hex')
 OR (body->>'frame_canonical_json')::jsonb IS DISTINCT FROM frame
 OR frame->'question' IS DISTINCT FROM question
 OR frame->'question_reference' IS DISTINCT FROM ops.ddo_structural_product_reference(question_product)
 OR question->>'pass_kind' IS DISTINCT FROM 'C' OR question->>'exposure' IS DISTINCT FROM 'output_first'
 OR question->>'partition' NOT IN ('development','feature_fit') THEN
 RAISE EXCEPTION 'event frame changes actual protected question or exact canonical frame' USING ERRCODE='23514'; END IF;
 FOR selected IN SELECT question->'original_selection' UNION SELECT question->'prediction_selection' LOOP
 IF selected->>'project_id' IS DISTINCT FROM r.project_id
 OR (selected->>'cut_canonical_json')::jsonb->>'demand_id' IS DISTINCT FROM selected->>'demand_id'
 OR (selected->>'cut_canonical_json')::jsonb->>'read_id' IS DISTINCT FROM selected->>'read_id'
 OR (selected->>'cut_canonical_json')::jsonb->>'release_id' IS DISTINCT FROM selected->>'release_id'
 OR (selected->>'cut_canonical_json')::jsonb->>'runtime_id' IS DISTINCT FROM selected->>'runtime_id' THEN
 RAISE EXCEPTION 'event question changes exact native cut pins' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_record_grade_require_cut(r.project_id,selected->>'cut_canonical_json',selected->>'cut_id');
 END LOOP;
 original_census:=ops.ddo_record_grade_acquire_census(r.project_id,question->'original_selection'->>'cut_canonical_json',question->'original_selection'->>'cut_id');
 prediction_census:=ops.ddo_record_grade_acquire_census(r.project_id,question->'prediction_selection'->>'cut_canonical_json',question->'prediction_selection'->>'cut_id');
 FOR selected IN SELECT value->'selection' FROM jsonb_array_elements(question->'judgments') item(value) LOOP
 report_pin:=selected->'report'; source_pin:=selected->'source';
 IF selected->>'origin_group' IS DISTINCT FROM source_pin->>'original_source' THEN
 RAISE EXCEPTION 'event origin group differs from actual original source' USING ERRCODE='23514'; END IF;
 IF NOT reports_ ? (report_pin->>'product_id') THEN reports_:=reports_||jsonb_build_array(report_pin->>'product_id'); END IF;
 IF NOT sources_ @> jsonb_build_array(jsonb_build_array(source_pin->>'source_product',source_pin->>'source_member')) THEN
 sources_:=sources_||jsonb_build_array(jsonb_build_array(source_pin->>'source_product',source_pin->>'source_member')); END IF;
 SELECT value INTO STRICT bound FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'='reports' AND value->>'product_id'=report_pin->>'product_id'
 AND value->>'member_id' IS NULL AND (value->>'multiplicity')::integer=1;
 SELECT * INTO STRICT report_product FROM kb.data_product WHERE id=report_pin->>'product_id' AND project_id=r.project_id;
 IF report_pin IS DISTINCT FROM ops.ddo_structural_product_reference(report_product)
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(prediction_census->'outputs') output
 WHERE output->>'product_id'=report_product.id AND output->>'derivation_id'=selected->>'derivation_id')
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(r.binding->'support') support
 WHERE support->>'role'='reports' AND support->>'derivation_id'=selected->>'derivation_id') THEN
 RAISE EXCEPTION 'event report changes actual selected whole context/producer support' USING ERRCODE='23514'; END IF;
 u:=prediction_census->'uses'->(selected->>'use_id');
 IF u IS NULL OR u->>'derivation_id' IS DISTINCT FROM selected->>'derivation_id'
 OR u->>'completion_state' IS DISTINCT FROM 'success' OR u->>'fate' NOT IN ('fulfilled','attached') THEN
 RAISE EXCEPTION 'event report lacks its exact successful selected native use' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT producer FROM ops.data_derivation WHERE id=selected->>'derivation_id' AND outcome='success';
 SELECT operation.* INTO STRICT definition FROM sem.data_operation_definition operation
 JOIN ops.data_request request ON request.release_id=operation.release_id AND request.operation_id=operation.operation_id
 WHERE request.id=producer.request_id AND request.project_id=r.project_id;
 IF definition.operation_id IS DISTINCT FROM selected->>'producer_operation'
 OR definition.implementation_revision IS DISTINCT FROM selected->>'producer_revision'
 OR producer.release_id IS DISTINCT FROM question->'prediction_selection'->>'release_id' THEN
 RAISE EXCEPTION 'event report changes its actual admitted producer revision/release' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT role_meaning FROM jsonb_array_elements(cpu_roles->1) item(value)
 WHERE data.ddo_json(value)->>'role'='reports' AND data.ddo_json(value)->>'product_id'=report_product.id;
 -- Exact original CPU body custody is owned by the current component producer.
 -- A copied same-kind report, matching factory or unrelated receipt is insufficient.
 PERFORM ops.ddo_definition_component_basis(role_meaning);
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(data.ddo_json(report_product.canonical_body)->'definition_components'->'components') component
 WHERE component->>'component_id'=selected->>'component_id') THEN
 RAISE EXCEPTION 'event component is absent from its actual whole report' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT bound FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'='sources' AND value->>'product_id'=source_pin->>'source_product'
 AND value->>'member_id' IS NOT DISTINCT FROM source_pin->>'source_member' AND (value->>'multiplicity')::integer=1;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(original_census->'outputs') output
 WHERE output->>'product_id'=source_pin->>'source_product') THEN
 RAISE EXCEPTION 'event original source is outside exact original selected support' USING ERRCODE='23514'; END IF;
 actual:=ops.ddo_record_grade_input_value(r.project_id,bound->>'product_id',bound->>'member_id');
 IF (actual-'body'-'analyzed_scope_meaning') IS DISTINCT FROM jsonb_build_object(
 'product_id',source_pin->>'source_product','member_id',source_pin->>'source_member','project_id',source_pin->>'project_id',
 'kind_contract',source_pin->>'kind_contract','subject',source_pin->>'subject','subject_definition',source_pin->>'subject_definition','original_source',source_pin->>'original_source')
 OR actual->'analyzed_scope_meaning' IS DISTINCT FROM (source_pin->>'analyzed_scope_meaning')::jsonb
 OR actual->'body'->'source'->>'document' IS DISTINCT FROM source_pin->>'document'
 OR actual->'body'->'source'->>'projection' IS DISTINCT FROM source_pin->>'projection_digest'
 OR actual->'body'->'source'->>'section_pointer' IS DISTINCT FROM source_pin->>'section_pointer'
 OR actual->'body'->'source'->>'membership' IS DISTINCT FROM source_pin->>'membership' THEN
 RAISE EXCEPTION 'event source pin changes exact selected coordinate/context' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (SELECT count(*) FROM jsonb_array_elements(r.binding->'inputs') input WHERE input->>'role'='reports')<>jsonb_array_length(reports_)
 OR (SELECT count(*) FROM jsonb_array_elements(r.binding->'inputs') input WHERE input->>'role'='sources')<>jsonb_array_length(sources_) THEN
 RAISE EXCEPTION 'event frame changes the exact declared report/source population' USING ERRCODE='23514'; END IF;
END $event$;

CREATE OR REPLACE FUNCTION ops.ddo_operation_event_require_fit(r ops.data_request,body jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $event$
DECLARE specification jsonb:=ops.ddo_record_grade_input(r,'specification')->'body'; selected jsonb:=specification->'frame';
 selection_ jsonb:=selected->'selection'; d ops.data_demand; boundary ops.data_demand_read; p jsonb;
 p_use text:=selected->>'use_id'; p_product text:=selected->'reference'->>'product_id'; p_derivation text:=selected->>'derivation_id';
 admitted boolean; scope_key text; epoch bigint; current_trust jsonb:='{}'; chosen jsonb;
 producer ops.data_derivation; frame_request ops.data_request; intent ops.data_completion_intent; actual kb.data_product; definition sem.data_operation_definition;
BEGIN
 IF selection_->>'project_id' IS DISTINCT FROM r.project_id
 OR selected->'reference'->>'member_id' IS NOT NULL
 OR selection_->>'cut_id' IS DISTINCT FROM 'cut-selection:'||encode(sha256(convert_to(selection_->>'cut_canonical_json','UTF8')),'hex') THEN
 RAISE EXCEPTION 'event fit changes exact selected frame project/cut' USING ERRCODE='23514'; END IF;
 FOR scope_key IN SELECT * FROM ops.ddo_record_fit_cut_scopes(r.project_id,selection_) LOOP
 SELECT coalesce((SELECT scope.epoch FROM ops.data_trust_scope scope WHERE scope.scope=scope_key AND scope.project_id=r.project_id),0) INTO epoch;
 current_trust:=current_trust||jsonb_build_object(scope_key,epoch);
 END LOOP;
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=selection_->>'demand_id' AND project_id=r.project_id;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=selection_->>'read_id' AND demand_id=d.id;
 IF ops.ddo_trust_snapshot_meaning(current_trust) IS DISTINCT FROM ops.ddo_trust_snapshot_meaning(boundary.trust_snapshot) THEN
 RAISE EXCEPTION 'event frame current trust differs from original selected fit cut' USING ERRCODE='23514'; END IF;
 p:=jsonb_build_object('scope',boundary.scope);
 __DDO_CORE_SELECTED_SUPPORT_OUTPUT__ INTO admitted;
 IF NOT coalesce(admitted,false) THEN RAISE EXCEPTION 'event frame is outside exact native selected support' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT chosen FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'='frame' AND value->>'product_id'=p_product AND value->>'member_id' IS NULL AND (value->>'multiplicity')::integer=1;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(r.binding->'support') support WHERE support->>'role'='frame' AND support->>'derivation_id'=p_derivation) THEN
 RAISE EXCEPTION 'event fit changes exact frame producing support' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT producer FROM ops.data_derivation WHERE id=p_derivation AND outcome='success';
 SELECT * INTO STRICT frame_request FROM ops.data_request WHERE id=producer.request_id AND project_id=r.project_id;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=frame_request.release_id AND operation_id=frame_request.operation_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=producer.intent_id;
 SELECT * INTO STRICT actual FROM kb.data_product WHERE id=p_product AND project_id=r.project_id;
 IF selected->'reference' IS DISTINCT FROM ops.ddo_structural_product_reference(actual)
 OR data.ddo_json(actual.canonical_body)->>'frame_digest' IS DISTINCT FROM selected->>'frame_digest'
 OR definition.operation_id IS DISTINCT FROM 'operation_event.frame'
 OR NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt JOIN ops.data_derivation_output output ON output.derivation_id=receipt.derivation_id
 WHERE receipt.derivation_id=producer.id AND receipt.intent_id=intent.id AND output.product_id=p_product AND output.member_id IS NULL AND output.role='frame') THEN
 RAISE EXCEPTION 'event fit lacks actual selected current frame CPU/common receipt' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_require_operation_event_completion(frame_request,intent.payload);
 IF data.ddo_normalize(intent.payload->'outputs'->0->'product'->'body') IS DISTINCT FROM actual.canonical_body THEN
 RAISE EXCEPTION 'event frame differs from actual original CPU completion body' USING ERRCODE='23514'; END IF;
 IF body->'specification' IS DISTINCT FROM specification OR body->'result'->>'frame_digest' IS DISTINCT FROM selected->>'frame_digest'
 OR (body->'result'->'parameters' IS NOT NULL AND body->'result'->'parameters'<>'null'::jsonb AND
 (body->'result'->'parameters'->'algorithm' IS DISTINCT FROM specification->'algorithm'
 OR body->'result'->'parameters'->>'frame_digest' IS DISTINCT FROM selected->>'frame_digest')) THEN
 RAISE EXCEPTION 'event fit changes actual frame identity or declared algorithm' USING ERRCODE='23514'; END IF;
END $event$;

CREATE OR REPLACE FUNCTION ops.ddo_operation_event_require_parameters(r ops.data_request)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $event$
DECLARE chosen jsonb; issuing ops.data_derivation; issuer_request ops.data_request; intent ops.data_completion_intent;
BEGIN
 SELECT value INTO STRICT chosen FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'='parameters' AND value->>'member_id' IS NULL AND (value->>'multiplicity')::integer=1;
 IF NOT EXISTS(SELECT FROM kb.data_product product WHERE product.id=chosen->>'product_id' AND product.project_id=r.project_id
 AND product.subject=r.subject AND product.subject_definition=ops.ddo_operation_subject(r.release_id,r.operation_id)
 AND product.original_source IS NOT DISTINCT FROM r.original_source AND product.analyzed_scope=r.analyzed_scope) THEN
 RAISE EXCEPTION 'event score parameters change exact selected event context' USING ERRCODE='23514'; END IF;
 SELECT producer.* INTO STRICT issuing FROM ops.data_derivation producer
 JOIN ops.data_derivation_output output ON output.derivation_id=producer.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=producer.intent_id
 JOIN ops.data_request request ON request.id=producer.request_id AND request.project_id=r.project_id
 JOIN sem.data_operation_definition definition ON definition.release_id=request.release_id AND definition.operation_id=request.operation_id
 WHERE output.product_id=chosen->>'product_id' AND output.member_id IS NULL AND output.role='parameters'
 AND output.position=0 AND output.multiplicity=1 AND producer.outcome='success'
 AND ops.ddo_operation_event_command_eligible(definition)
 AND EXISTS(SELECT FROM jsonb_array_elements(r.binding->'support') support WHERE support->>'role'='parameters' AND support->>'derivation_id'=producer.id)
 AND (chosen->>'support_derivation_id' IS NULL OR chosen->>'support_derivation_id'=producer.id);
 SELECT * INTO STRICT issuer_request FROM ops.data_request WHERE id=issuing.request_id AND project_id=r.project_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=issuing.intent_id;
 PERFORM ops.ddo_require_operation_event_completion(issuer_request,intent.payload);
 IF data.ddo_normalize(intent.payload->'outputs'->0->'product'->'body') IS DISTINCT FROM
 (SELECT canonical_body FROM kb.data_product WHERE id=chosen->>'product_id' AND project_id=r.project_id) THEN
 RAISE EXCEPTION 'event score parameters differ from actual original native issuer' USING ERRCODE='23514'; END IF;
END $event$;

CREATE OR REPLACE FUNCTION ops.ddo_require_operation_event_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $event$
DECLARE definition sem.data_operation_definition; output jsonb; body jsonb; expected_factory text; output_role text; output_kind text;
 basis kb.data_product; producing ops.data_derivation; fit_request ops.data_request; fit_intent ops.data_completion_intent; selected jsonb; expected jsonb;
BEGIN
 IF r.operation_id NOT IN ('operation_event.frame','operation_event.fit','operation_event.authorize','urn:corpus:operation:score-operation-event') THEN RETURN; END IF;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF completion->>'outcome' IS DISTINCT FROM 'success' OR jsonb_array_length(completion->'outputs')<>1
 OR completion->'inputs' IS DISTINCT FROM r.binding->'inputs' OR completion->'support' IS DISTINCT FROM r.binding->'support'
 OR definition.implementation_revision IS DISTINCT FROM completion->>'implementation_revision' OR definition.recipe IS DISTINCT FROM r.recipe THEN
 RAISE EXCEPTION 'operation event completion changes exact current request/implementation' USING ERRCODE='23514'; END IF;
 output:=completion->'outputs'->0;
 IF r.operation_id='operation_event.authorize' THEN
 IF NOT coalesce(ops.ddo_operation_event_command_eligible(definition),false) OR jsonb_array_length(completion->'inputs')<>1 THEN
 RAISE EXCEPTION 'operation event issuer requires exact command/effect/factory and fit basis' USING ERRCODE='23514'; END IF;
 output_role:='parameters'; output_kind:='urn:corpus:kind:operation-event:parameters';
 selected:=completion->'inputs'->0;
 IF selected->>'role' IS DISTINCT FROM 'basis' OR selected->>'member_id' IS NOT NULL OR (selected->>'multiplicity')::integer<>1 THEN
 RAISE EXCEPTION 'event issuer requires actual whole protected fit basis' USING ERRCODE='23514'; END IF;
 SELECT product.* INTO STRICT basis FROM kb.data_product product JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract
 WHERE product.id=selected->>'product_id' AND product.project_id=r.project_id AND kind.kind='__NAMESPACE__DdoOperationEventFit' AND kind.universe='evaluator';
 SELECT producer.* INTO STRICT producing FROM ops.data_derivation producer JOIN ops.data_derivation_output produced ON produced.derivation_id=producer.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=producer.intent_id
 WHERE produced.product_id=basis.id AND produced.member_id IS NULL AND produced.role='fit' AND producer.outcome='success'
 AND EXISTS(SELECT FROM jsonb_array_elements(completion->'support') support WHERE support->>'role'='basis' AND support->>'derivation_id'=producer.id)
 AND (selected->>'support_derivation_id' IS NULL OR selected->>'support_derivation_id'=producer.id);
 SELECT * INTO STRICT fit_request FROM ops.data_request WHERE id=producing.request_id AND project_id=r.project_id AND operation_id='operation_event.fit';
 SELECT * INTO STRICT fit_intent FROM ops.data_completion_intent WHERE id=producing.intent_id;
 PERFORM ops.ddo_require_operation_event_completion(fit_request,fit_intent.payload);
 IF data.ddo_normalize(fit_intent.payload->'outputs'->0->'product'->'body') IS DISTINCT FROM basis.canonical_body
 OR data.ddo_json(basis.canonical_body)->'result'->>'status' IS DISTINCT FROM 'fitted' THEN
 RAISE EXCEPTION 'event issuer basis differs from actual successful protected CPU fit' USING ERRCODE='23514'; END IF;
 expected:=data.ddo_field(data.ddo_field(basis.canonical_body,'result'),'parameters');
 IF expected='["null"]'::jsonb OR data.ddo_normalize(output->'product'->'body') IS DISTINCT FROM expected THEN
 RAISE EXCEPTION 'event issuer may disclose only exact fitted strict parameters' USING ERRCODE='23514'; END IF;
 ELSE
 output_role:=CASE r.operation_id WHEN 'operation_event.frame' THEN 'frame' WHEN 'operation_event.fit' THEN 'fit' ELSE 'probability' END;
 output_kind:='__NAMESPACE__'||CASE r.operation_id WHEN 'operation_event.frame' THEN 'DdoOperationEventFrame' ELSE 'DdoOperationEventFit' END;
 expected_factory:=CASE r.operation_id WHEN 'urn:corpus:operation:score-operation-event' THEN 'corpus_structure.semantic.operation_policy.acquire_operation_event_score_port'
 ELSE 'corpus_structure.methods.operation_events.'||CASE r.operation_id WHEN 'operation_event.frame' THEN 'OperationEventFrame' ELSE 'OperationEventFit' END||'.acquire_port' END;
 IF definition.profile IS DISTINCT FROM 'derivation' OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM expected_factory
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR data.ddo_normalize(output->'product'->'body') IS DISTINCT FROM ops.ddo_cpu_reply_output(r,completion) THEN
 RAISE EXCEPTION 'event conclusion differs from actual admitted CPU body/factory/receipt' USING ERRCODE='23514'; END IF;
 body:=data.ddo_json(output->'product'->'body');
 IF r.operation_id='operation_event.frame' THEN PERFORM ops.ddo_operation_event_require_frame(r,body);
 ELSIF r.operation_id='operation_event.fit' THEN PERFORM ops.ddo_operation_event_require_fit(r,body);
 ELSE PERFORM ops.ddo_operation_event_require_parameters(r); END IF;
 END IF;
 IF output->>'role' IS DISTINCT FROM output_role OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND (CASE WHEN r.operation_id='urn:corpus:operation:score-operation-event' THEN kind.kind_contract=definition.output_roles->0->>'kind_contract' ELSE kind.kind=output_kind END)
 AND kind.universe=CASE WHEN r.operation_id IN ('operation_event.authorize','urn:corpus:operation:score-operation-event') THEN 'ordinary' ELSE 'evaluator' END) THEN
 RAISE EXCEPTION 'event output changes exact finite whole nominal contract' USING ERRCODE='23514'; END IF;
END $event$;

CREATE OR REPLACE FUNCTION ops.ddo_operation_event_dependencies_valid(episode text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $event$
DECLARE r ops.data_request; completion jsonb; selected jsonb; boundary ops.data_demand_read;
 scope_key text; epoch bigint; current_trust jsonb;
BEGIN
 SELECT request.* INTO STRICT r FROM ops.data_request request JOIN ops.data_derivation producer ON producer.request_id=request.id WHERE producer.id=episode;
 IF r.operation_id NOT IN ('operation_event.frame','operation_event.fit','operation_event.authorize','urn:corpus:operation:score-operation-event') THEN RETURN true; END IF;
 IF NOT EXISTS(SELECT FROM ops.data_derivation producer JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=producer.intent_id
 JOIN sem.artifact artifact ON artifact.release_id=producer.release_id AND artifact.artifact_name='data_operation_native_definitions.json'
 WHERE producer.id=episode AND convert_from(artifact.content,'UTF8')::jsonb->>'native_digest'='__DDO_SOURCE_DIGEST__') THEN RETURN false; END IF;
 SELECT intent.payload INTO STRICT completion FROM ops.data_derivation producer JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id WHERE producer.id=episode;
 IF r.operation_id='operation_event.frame' THEN
 FOR selected IN SELECT ops.ddo_record_grade_input(r,'question')->'body'->'original_selection'
 UNION SELECT ops.ddo_record_grade_input(r,'question')->'body'->'prediction_selection' LOOP
 PERFORM ops.ddo_record_grade_require_cut(r.project_id,selected->>'cut_canonical_json',selected->>'cut_id');
 END LOOP;
 ELSIF r.operation_id='operation_event.fit' THEN
 selected:=ops.ddo_record_grade_input(r,'specification')->'body'->'frame'->'selection';
 current_trust:='{}';
 FOR scope_key IN SELECT * FROM ops.ddo_record_fit_cut_scopes(r.project_id,selected) LOOP
 SELECT coalesce((SELECT scope.epoch FROM ops.data_trust_scope scope WHERE scope.scope=scope_key AND scope.project_id=r.project_id),0) INTO epoch;
 current_trust:=current_trust||jsonb_build_object(scope_key,epoch);
 END LOOP;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=selected->>'read_id' AND demand_id=selected->>'demand_id';
 IF ops.ddo_trust_snapshot_meaning(current_trust) IS DISTINCT FROM ops.ddo_trust_snapshot_meaning(boundary.trust_snapshot) THEN RETURN false; END IF;
 END IF;
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $event$;
""".replace("__AUTHORIZE__", AUTHORIZATION_OPERATION).replace("__AUTHORIZE_FACTORY__", AUTHORIZATION_FACTORY).replace(
        "__EFFECT__", json.dumps([asdict(AUTHORIZATION_EFFECT)], separators=(",", ":"))
    ).replace("__NAMESPACE__", NAMESPACE) + "\n".join(
        f"REVOKE ALL ON FUNCTION ops.{name}({arguments}) FROM PUBLIC;" for name, arguments in (
            ("ddo_operation_event_command_eligible", "sem.data_operation_definition"),
            ("ddo_operation_event_completion_scopes", "ops.data_request"),
            ("ddo_operation_event_dependency_scopes", "text"),
            ("ddo_operation_event_require_frame", "ops.data_request,jsonb"),
            ("ddo_operation_event_require_fit", "ops.data_request,jsonb"),
            ("ddo_operation_event_require_parameters", "ops.data_request"),
            ("ddo_require_operation_event_completion", "ops.data_request,jsonb"),
            ("ddo_operation_event_dependencies_valid", "text"),
        )
    )


def operation_event_native_sources():
    """Executable helper plus its actual source owners for the existing native cut."""
    from pathlib import Path
    from .types import SourceArtifact
    root=Path(__file__).parents[1]
    return (
        SourceArtifact("native/data-operation-operation-event.sql",operation_event_native_sql().encode()),
        SourceArtifact("native/data-operation-operation-event-native.py",Path(__file__).read_bytes()),
        SourceArtifact("native/data-operation-operation-event-producers.py",(root/"evaluate/declared_operation_events.py").read_bytes()),
        SourceArtifact("native/data-operation-operation-event-methods.py",(root/"methods/operation_events.py").read_bytes()),
    )
