"""Native custody of the explicit complete-record grading census.

Numerical features and whole-reading judgments belong to the captured evaluator
CPU implementation. This boundary authenticates its declared sources, original
reference passes and the retained native prediction opportunities, including
failed and empty opportunities which are not fulfilled computational support.
"""


def record_grade_native_sql() -> str:
    from .record_policy_authority import GRADE_FACTORY, GRADE_KIND, GRADE_OPERATION

    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_record_grade_input_value(project text,product text,member text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE value jsonb;
BEGIN
 SELECT jsonb_build_object('product_id',x.id,'member_id',member,'project_id',x.project_id,
 'kind_contract',CASE WHEN member IS NULL THEN x.kind_contract ELSE m.kind_contract END,
 'subject',CASE WHEN member IS NULL THEN x.subject ELSE m.subject END,
 'subject_definition',CASE WHEN member IS NULL THEN x.subject_definition ELSE m.subject_definition END,
 'original_source',CASE WHEN member IS NULL THEN x.original_source ELSE m.original_source END,
 'analyzed_scope_meaning',data.ddo_json_meaning(CASE WHEN member IS NULL THEN x.analyzed_scope ELSE m.analyzed_scope END),
 'body',data.ddo_json(CASE WHEN member IS NULL THEN x.canonical_body ELSE m.body END)) INTO STRICT value
 FROM kb.data_product x LEFT JOIN kb.data_product_member m ON m.product_id=x.id AND m.member_id=member
 WHERE x.id=product AND x.project_id=project AND (member IS NULL OR m.member_id IS NOT NULL);
 RETURN value;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_input(r ops.data_request,role_name text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE selected jsonb;
BEGIN
 SELECT value INTO STRICT selected FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'=role_name;
 IF selected->>'member_id' IS NOT NULL OR (selected->>'multiplicity')::integer<>1 THEN
 RAISE EXCEPTION 'record grade scalar role requires one whole actual product' USING ERRCODE='23514'; END IF;
 RETURN ops.ddo_record_grade_input_value(r.project_id,selected->>'product_id',NULL);
END $grade$;

-- This finite Core traversal deliberately has no validity callbacks. Refuse
-- protected judgments before any helper which could recursively validate a grade.
CREATE OR REPLACE FUNCTION ops.ddo_record_grade_require_finite_census(d ops.data_demand,boundary ops.data_demand_read)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE p jsonb:=jsonb_build_object('scope',boundary.scope); node record;
BEGIN
 IF EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') selected
 JOIN sem.data_operation_definition definition ON definition.release_id=d.release_id AND definition.operation_id=selected->>'operation'
 WHERE definition.operation_id IN ('__GRADE_OPERATION__','record_policy.fit','record_policy.authorize')
 OR EXISTS(SELECT FROM jsonb_array_elements(definition.input_roles||definition.output_roles) role
 JOIN sem.data_kind_contract kind ON kind.kind_contract=role->>'kind_contract'
 WHERE kind.universe='evaluator')) THEN
 RAISE EXCEPTION 'record census cannot consume a protected judgment demand' USING ERRCODE='23514'; END IF;
 FOR node IN __DDO_CORE_RECORD_GRADE_CENSUS_NODES__ LOOP
 IF node.kind='episode' AND EXISTS(SELECT FROM ops.data_derivation episode
 JOIN ops.data_request request ON request.id=episode.request_id
 JOIN sem.data_operation_definition definition ON definition.release_id=request.release_id AND definition.operation_id=request.operation_id
 WHERE episode.id=node.id AND (request.operation_id IN ('__GRADE_OPERATION__','record_policy.fit','record_policy.authorize')
 OR EXISTS(SELECT FROM jsonb_array_elements(definition.input_roles||definition.output_roles) role
 JOIN sem.data_kind_contract kind ON kind.kind_contract=role->>'kind_contract' WHERE kind.universe='evaluator'))) THEN
 RAISE EXCEPTION 'record census support reaches a protected judgment' USING ERRCODE='23514'; END IF;
 IF node.kind='original' AND EXISTS(SELECT FROM ops.original_source_admission admission
 JOIN kb.data_product product ON product.id=admission.product_id
 JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract
 WHERE admission.id=node.id AND kind.universe='evaluator') THEN
 RAISE EXCEPTION 'record census source reaches a protected judgment' USING ERRCODE='23514'; END IF;
 END LOOP;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_cut_scopes(project text,cut_text text)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE captured jsonb:=cut_text::jsonb; d ops.data_demand; boundary ops.data_demand_read; p jsonb; actual jsonb;
BEGIN
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=captured->>'demand_id' AND project_id=project;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=captured->>'read_id' AND demand_id=d.id;
 p:=jsonb_build_object('scope',boundary.scope);
 PERFORM ops.ddo_record_grade_require_finite_census(d,boundary);
 __DDO_CORE_CUT_SELECTION__ INTO actual;
 IF captured IS DISTINCT FROM actual THEN
 RAISE EXCEPTION 'record grade scope acquisition differs from actual project/cut' USING ERRCODE='23514'; END IF;
 RETURN QUERY __DDO_CORE_RECORD_GRADE_CENSUS_SCOPES__;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_require_cut(project text,cut_text text,cut_id text)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE captured jsonb:=cut_text::jsonb; d ops.data_demand; boundary ops.data_demand_read; p jsonb;
 actual jsonb; current_trust jsonb:='{}'; scope_key text; epoch bigint;
BEGIN
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=captured->>'demand_id' AND project_id=project;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=captured->>'read_id' AND demand_id=d.id;
 p:=jsonb_build_object('scope',boundary.scope);
 PERFORM ops.ddo_record_grade_require_finite_census(d,boundary);
 __DDO_CORE_CUT_SELECTION__ INTO actual;
 IF captured IS DISTINCT FROM actual OR cut_id IS DISTINCT FROM 'cut-selection:'||encode(sha256(convert_to(cut_text,'UTF8')),'hex') THEN
 RAISE EXCEPTION 'record grade differs from exact retained native cut' USING ERRCODE='23514'; END IF;
 -- The enclosing read/completion owns one canonical lock union. Zero epochs are
 -- omitted from the persisted meaning, but every structurally relevant scope is
 -- included in that union and compared here, including failed-use support.
 FOR scope_key IN __DDO_CORE_RECORD_GRADE_CENSUS_SCOPES__ LOOP
 SELECT coalesce((SELECT scope.epoch FROM ops.data_trust_scope scope WHERE scope.scope=scope_key AND scope.project_id=project),0) INTO epoch;
 current_trust:=current_trust||jsonb_build_object(scope_key,epoch);
 END LOOP;
 IF ops.ddo_trust_snapshot_meaning(current_trust) IS DISTINCT FROM ops.ddo_trust_snapshot_meaning(boundary.trust_snapshot) THEN
 RAISE EXCEPTION 'record census trust differs from its retained cut' USING ERRCODE='23514'; END IF;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_acquire_census(project text,cut_text text,cut_id text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE d ops.data_demand; boundary ops.data_demand_read; p jsonb; captured jsonb:=cut_text::jsonb; results jsonb;
 obligations jsonb:='{}'; uses_ jsonb:='{}'; outputs jsonb;
 lim bigint:=1000; after_key text:=''; selected_view text:='frontier'; selected_max_bytes bigint:=67108864;
BEGIN
 PERFORM ops.ddo_record_grade_require_cut(project,cut_text,cut_id);
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=captured->>'demand_id' AND project_id=project;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=captured->>'read_id' AND demand_id=d.id;
 p:=jsonb_build_object('scope',boundary.scope);
 -- One prepared, bounded frontier per distinct actual cut. Numerical/event
 -- comparisons below use these indexes rather than restarting the frontier.
 LOOP
 __DDO_CORE_READ_PAGE__ INTO results;
 SELECT obligations||coalesce(jsonb_object_agg(value->>'obligation_id',value),'{}') INTO obligations
 FROM jsonb_array_elements(results->'payload'->'obligations') item(value);
 SELECT uses_||coalesce(jsonb_object_agg(value->>'use_id',value),'{}') INTO uses_
 FROM jsonb_array_elements(results->'payload'->'uses') item(value);
 EXIT WHEN results->'payload'->'continuation' IS NULL OR results->'payload'->'continuation'='null'::jsonb;
 after_key:=results->'payload'->'continuation'->>'after';
 END LOOP;
 SELECT coalesce(jsonb_agg(to_jsonb(selected_output)),'[]') INTO outputs
 FROM (__DDO_CORE_RECORD_GRADE_SELECTED_OUTPUTS__) selected_output;
 RETURN jsonb_build_object('obligations',obligations,'uses',uses_,'outputs',outputs);
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_cuts(r ops.data_request)
RETURNS TABLE(cut_text text,cut_id text) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE specification jsonb; references_ jsonb; selection_ jsonb; question_ jsonb;
BEGIN
 IF r.operation_id IS DISTINCT FROM '__GRADE_OPERATION__' THEN RETURN; END IF;
 specification:=ops.ddo_record_grade_input(r,'specification')->'body';
 references_:=ops.ddo_record_grade_input(r,'adjudication')->'body';
 FOR selection_ IN SELECT value FROM jsonb_array_elements(specification->'prediction_selections') item(value) LOOP
 IF selection_->>'project_id' IS DISTINCT FROM r.project_id
 OR (selection_->>'cut_canonical_json')::jsonb->>'project_id' IS DISTINCT FROM selection_->>'project_id'
 OR (selection_->>'cut_canonical_json')::jsonb->>'demand_id' IS DISTINCT FROM selection_->>'demand_id'
 OR (selection_->>'cut_canonical_json')::jsonb->>'read_id' IS DISTINCT FROM selection_->>'read_id' THEN
 RAISE EXCEPTION 'record census selection differs from exact cut/project/read pins' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR question_ IN SELECT value->'question' FROM jsonb_array_elements(references_->'references') item(value) LOOP
 IF question_->>'project_id' IS DISTINCT FROM r.project_id
 OR (question_->>'source_cut_canonical_json')::jsonb->>'project_id' IS DISTINCT FROM r.project_id
 OR (question_->>'source_cut_canonical_json')::jsonb->>'release_id' IS DISTINCT FROM question_->>'source_release_id' THEN
 RAISE EXCEPTION 'record source question differs from original project/release cut' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN QUERY SELECT DISTINCT question->'question'->>'source_cut_canonical_json',question->'question'->>'source_cut_id'
 FROM jsonb_array_elements(references_->'references') question
 UNION SELECT selection->>'cut_canonical_json',selection->>'expected_cut'
 FROM jsonb_array_elements(specification->'prediction_selections') selection;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_completion_scopes(r ops.data_request)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE captured record;
BEGIN
 IF r.operation_id IS DISTINCT FROM '__GRADE_OPERATION__' THEN RETURN; END IF;
 FOR captured IN SELECT * FROM ops.ddo_record_grade_cuts(r) LOOP
 RETURN QUERY SELECT * FROM ops.ddo_record_grade_cut_scopes(r.project_id,captured.cut_text);
 END LOOP;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_dependency_scopes(episode text)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE r ops.data_request;
BEGIN
 SELECT request.* INTO STRICT r FROM ops.data_request request JOIN ops.data_derivation producer ON producer.request_id=request.id WHERE producer.id=episode;
 RETURN QUERY SELECT * FROM ops.ddo_record_grade_completion_scopes(r);
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_require_frame(r ops.data_request,grade jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE a jsonb:=ops.ddo_record_grade_input(r,'reference_a'); b jsonb:=ops.ddo_record_grade_input(r,'reference_b');
 c jsonb:=ops.ddo_record_grade_input(r,'adjudication'); specification jsonb:=ops.ddo_record_grade_input(r,'specification')->'body';
 frame jsonb:=grade->'frame'; question jsonb; selected jsonb; source_census jsonb; prediction_census jsonb; u jsonb; obligation jsonb;
 cuts jsonb:='{}'; captured record;
 predicted jsonb; carrier jsonb; candidate jsonb; event jsonb; actual_event jsonb; coverage jsonb; ref jsonb; pin jsonb; bound jsonb;
 pins jsonb:='[]'; sources_ jsonb:='[]'; event_count integer:=0; selected_count integer:=0; n bigint; pass_row record;
 producer ops.data_derivation; reading sem.data_operation_definition;
BEGIN
 IF grade->>'version' IS DISTINCT FROM 'record-grade-1'
 OR grade->>'frame_digest' IS DISTINCT FROM encode(sha256(convert_to(grade->>'frame_canonical_json','UTF8')),'hex')
 OR (grade->>'frame_canonical_json')::jsonb IS DISTINCT FROM frame OR frame->>'project_id' IS DISTINCT FROM r.project_id
 OR jsonb_array_length(c->'body'->'references')<>jsonb_array_length(specification->'prediction_selections')
 OR jsonb_array_length(c->'body'->'references')<>jsonb_array_length(frame->'coverage')
 OR jsonb_array_length(frame->'reference_passes')<>3*jsonb_array_length(c->'body'->'references')
 OR a->>'product_id'=b->>'product_id' OR a->>'product_id'=c->>'product_id' OR b->>'product_id'=c->>'product_id' THEN
 RAISE EXCEPTION 'record grade differs from canonical frame and genuine independent pass population' USING ERRCODE='23514'; END IF;
 FOR captured IN SELECT * FROM ops.ddo_record_grade_cuts(r) LOOP
 cuts:=cuts||jsonb_build_object(captured.cut_id,ops.ddo_record_grade_acquire_census(r.project_id,captured.cut_text,captured.cut_id));
 END LOOP;
 FOR ref,n IN SELECT value,ordinal FROM jsonb_array_elements(c->'body'->'references') WITH ORDINALITY items(value,ordinal) LOOP
 question:=ref->'question'; selected:=specification->'prediction_selections'->((n-1)::integer);
 sources_:=sources_||jsonb_build_array(question->'source');
 IF selected->'source' IS DISTINCT FROM question->'source'
 OR frame->'sources'->((n-1)::integer) IS DISTINCT FROM question->'source'
 OR frame->>'partition' IS DISTINCT FROM question->>'partition'
 OR frame->>'family' IS DISTINCT FROM question->>'family'
 OR frame->>'family_contract' IS DISTINCT FROM question->>'family_contract'
 OR frame->>'reading_recipe' IS DISTINCT FROM question->>'reading_recipe'
 OR frame->>'subset' IS DISTINCT FROM question->>'subset'
 OR frame->>'source_release_id' IS DISTINCT FROM question->>'source_release_id'
 OR frame->>'source_cut_id' IS DISTINCT FROM question->>'source_cut_id'
 OR frame->>'prediction_cut_id' IS DISTINCT FROM selected->>'expected_cut'
 OR frame->>'prediction_release_id' IS DISTINCT FROM (selected->>'cut_canonical_json')::jsonb->>'release_id'
 OR selected->>'project_id' IS DISTINCT FROM r.project_id
 OR (selected->>'cut_canonical_json')::jsonb->>'project_id' IS DISTINCT FROM selected->>'project_id'
 OR (selected->>'cut_canonical_json')::jsonb->>'demand_id' IS DISTINCT FROM selected->>'demand_id'
 OR (selected->>'cut_canonical_json')::jsonb->>'read_id' IS DISTINCT FROM selected->>'read_id' THEN
 RAISE EXCEPTION 'record question/source/prediction census changed' USING ERRCODE='23514'; END IF;
 source_census:=cuts->(question->>'source_cut_id');
 prediction_census:=cuts->(selected->>'expected_cut');
 FOR pass_row IN SELECT * FROM (VALUES ('A',a),('B',b),('C',c)) passes(pass_kind,pass_value) LOOP
 bound:=pass_row.pass_value;
 IF bound->'body'->>'pass_kind' IS DISTINCT FROM pass_row.pass_kind
 OR bound->'body'->'references'->((n-1)::integer)->>'pass_kind' IS DISTINCT FROM pass_row.pass_kind
 OR bound->'body'->'references'->((n-1)::integer)->'question' IS DISTINCT FROM question
 OR bound->'body'->'references'->((n-1)::integer)->'exposed_outputs' IS DISTINCT FROM '[]'::jsonb THEN
 RAISE EXCEPTION 'record reference pass differs from exact source-only question/exposure' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT event FROM jsonb_array_elements(frame->'reference_passes') item(value)
 WHERE value->>'pass_kind'=pass_row.pass_kind AND value->'source'=question->'source';
 IF event->'reference'->>'product_id' IS DISTINCT FROM bound->>'product_id'
 OR event->'reference'->>'member_id' IS NOT NULL
 OR event->>'author' IS DISTINCT FROM bound->'body'->'references'->((n-1)::integer)->>'author'
 OR event->'adjudicates' IS DISTINCT FROM bound->'body'->'references'->((n-1)::integer)->'adjudicates' THEN
 RAISE EXCEPTION 'record grade relabels actual reference pass' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR pin IN SELECT value FROM jsonb_array_elements(jsonb_build_array(question->'source')||coalesce((question->>'frame_canonical_json')::jsonb->'related_pins','[]')) item(value) LOOP
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(pins) previous WHERE previous->>'source_product'=pin->>'source_product' AND previous->>'source_member' IS NOT DISTINCT FROM pin->>'source_member') THEN pins:=pins||jsonb_build_array(pin); END IF;
 SELECT value INTO STRICT bound FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'='sources' AND value->>'product_id'=pin->>'source_product' AND value->>'member_id' IS NOT DISTINCT FROM pin->>'source_member';
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(source_census->'outputs') output WHERE output->>'product_id'=pin->>'source_product') THEN
 RAISE EXCEPTION 'record question source is outside actual selected cut support' USING ERRCODE='23514'; END IF;
 predicted:=ops.ddo_record_grade_input_value(r.project_id,bound->>'product_id',bound->>'member_id');
 IF (predicted-'body'-'analyzed_scope_meaning') IS DISTINCT FROM jsonb_build_object('product_id',pin->>'source_product','member_id',pin->>'source_member','project_id',pin->>'project_id',
 'kind_contract',pin->>'kind_contract','subject',pin->>'subject','subject_definition',pin->>'subject_definition','original_source',pin->>'original_source')
 OR predicted->'analyzed_scope_meaning' IS DISTINCT FROM (pin->>'analyzed_scope_meaning')::jsonb
 OR predicted->'body'->'source'->>'document' IS DISTINCT FROM pin->>'document'
 OR predicted->'body'->'source'->>'projection' IS DISTINCT FROM pin->>'projection_digest'
 OR predicted->'body'->'source'->>'section_pointer' IS DISTINCT FROM pin->>'section_pointer'
 OR predicted->'body'->'source'->>'membership' IS DISTINCT FROM pin->>'membership' THEN
 RAISE EXCEPTION 'record source pin differs from actual declared source product/member/context' USING ERRCODE='23514'; END IF;
 END LOOP;
 u:=prediction_census->'uses'->(selected->>'use_id');
 obligation:=prediction_census->'obligations'->(selected->>'obligation_id');
 IF u IS NULL OR obligation IS NULL OR u->>'obligation_id' IS DISTINCT FROM selected->>'obligation_id'
 OR u->>'request_id' IS DISTINCT FROM selected->>'request_id' THEN
 RAISE EXCEPTION 'record opportunity is outside its exact native selected census' USING ERRCODE='23514'; END IF;
 IF obligation->>'operation_id' IS DISTINCT FROM 'resolve.m1_readings/declared'
 OR obligation->>'subject' IS DISTINCT FROM question->'source'->>'subject'
 OR obligation->>'subject_definition' IS DISTINCT FROM question->'source'->>'subject_definition'
 OR obligation->>'original_source' IS DISTINCT FROM question->'source'->>'original_source'
 OR data.ddo_json_meaning(obligation->'analyzed_scope') IS DISTINCT FROM (question->'source'->>'analyzed_scope_meaning')::jsonb THEN
 RAISE EXCEPTION 'record opportunity differs from actual source context' USING ERRCODE='23514'; END IF;
 coverage:=frame->'coverage'->((n-1)::integer);
 IF coverage->'source' IS DISTINCT FROM question->'source' THEN RAISE EXCEPTION 'record coverage source changed' USING ERRCODE='23514'; END IF;
 IF selected->>'outcome' IN ('failed','no_output') THEN
 IF u->>'completion_state' IS DISTINCT FROM (CASE WHEN selected->>'outcome'='failed' THEN 'failed' ELSE 'empty' END)
 OR u->>'fate' IS DISTINCT FROM (CASE WHEN selected->>'outcome'='failed' THEN 'failed' ELSE 'known-absent' END)
 OR coverage->>'outcome' IS DISTINCT FROM selected->>'outcome'
 OR coverage->'outputs' IS DISTINCT FROM '[]'::jsonb OR coverage->'event_ids' IS DISTINCT FROM '[]'::jsonb
 OR (selected->>'outcome'='failed' AND (coverage->>'failure_request_id',coverage->>'failure_use_id') IS DISTINCT FROM (selected->>'request_id',selected->>'use_id')) THEN
 RAISE EXCEPTION 'failed or empty coverage differs from actual native completion' USING ERRCODE='23514'; END IF;
 CONTINUE;
 END IF;
 IF selected->>'outcome' IS DISTINCT FROM 'completed' OR u->>'completion_state' IS DISTINCT FROM 'success'
 OR u->>'fate' IS DISTINCT FROM 'fulfilled' OR u->>'derivation_id' IS DISTINCT FROM selected->>'derivation_id' THEN
 RAISE EXCEPTION 'record prediction is unavailable or differs from actual native success' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT bound FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'='prediction' AND value->>'product_id'=selected->>'product_id' AND value->>'member_id' IS NULL
 AND coalesce((value->>'multiplicity')::integer,0)=1;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(r.binding->'support') support WHERE support->>'derivation_id'=selected->>'derivation_id')
 OR NOT EXISTS(SELECT FROM ops.data_derivation_output output WHERE output.derivation_id=selected->>'derivation_id' AND output.product_id=selected->>'product_id' AND output.member_id IS NULL) THEN
 RAISE EXCEPTION 'record prediction lacks exact declared producer/output support' USING ERRCODE='23514'; END IF;
 selected_count:=selected_count+1;
 SELECT * INTO STRICT producer FROM ops.data_derivation WHERE id=selected->>'derivation_id' AND request_id=selected->>'request_id';
 SELECT * INTO STRICT reading FROM sem.data_operation_definition WHERE release_id=producer.release_id AND operation_id='resolve.m1_readings/declared';
 IF producer.recipe IS DISTINCT FROM reading.recipe OR reading.recipe IS DISTINCT FROM question->>'reading_recipe' THEN
 RAISE EXCEPTION 'record prediction changed its admitted reading recipe' USING ERRCODE='23514'; END IF;
 predicted:=ops.ddo_record_grade_input_value(r.project_id,selected->>'product_id',NULL); carrier:=predicted->'body';
 IF carrier->'source_pin' IS DISTINCT FROM jsonb_strip_nulls(question->'source') OR jsonb_array_length(coverage->'outputs')<>1
 OR coverage->'outputs'->0->>'product_id' IS DISTINCT FROM selected->>'product_id' THEN
 RAISE EXCEPTION 'record coverage differs from actual selected carrier/source' USING ERRCODE='23514'; END IF;
 FOR candidate IN SELECT value->'body' FROM jsonb_array_elements(carrier->'members') item(value)
 WHERE value->'body'->>'candidate_type'='record' AND value->'body'->>'family'=question->>'family' LOOP
 event_count:=event_count+1;
 SELECT value INTO STRICT event FROM jsonb_array_elements(frame->'events') item(value)
 WHERE value->>'interpretation_id'=candidate->>'interpretation_id';
 IF event->>'record_id' IS DISTINCT FROM candidate->>'record_id' OR event->'source' IS DISTINCT FROM question->'source'
 OR event->>'source_release_id' IS DISTINCT FROM producer.release_id OR event->>'derivation_id' IS DISTINCT FROM producer.id
 OR event->>'reading_recipe' IS DISTINCT FROM reading.recipe
 OR event->'reading'->>'product_id' IS DISTINCT FROM selected->>'product_id'
 OR event->'features'->>'record_id' IS DISTINCT FROM candidate->>'record_id'
 OR event->'features'->>'interpretation_id' IS DISTINCT FROM candidate->>'interpretation_id'
 OR event->'features'->>'release_id' IS DISTINCT FROM producer.release_id
 OR NOT coverage->'event_ids' ? (candidate->>'interpretation_id')
 OR (SELECT count(*) FROM sem.artifact artifact
 CROSS JOIN LATERAL jsonb_array_elements(convert_from(artifact.content,'UTF8')::jsonb->'kinds') owned
 CROSS JOIN LATERAL jsonb_array_elements(convert_from(artifact.content,'UTF8')::jsonb->'identities') identity_
 JOIN sem.data_kind_release admitted ON admitted.release_id=producer.release_id AND admitted.kind_contract=identity_->>'key'
 WHERE artifact.release_id=producer.release_id AND artifact.artifact_name='data_operations.json'
 AND owned->>'name'=candidate->>'contract' AND owned->>'category'='class' AND (owned->>'complete')::boolean
 AND identity_->>'domain'='kind' AND identity_->>'owner'=owned->>'semantic_id'
 AND identity_->>'key'=question->>'family_contract')<>1 THEN
 RAISE EXCEPTION 'grade event relabels actual eligible reading, family or producing context' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT actual_event FROM jsonb_array_elements((carrier->>'diagnostics_json')::jsonb->'record_policy_events') item(value)
 WHERE value->>'record_id'=candidate->>'record_id' AND value->>'interpretation_id'=candidate->>'interpretation_id';
 IF actual_event->>'outcome'='completed' THEN
 IF event->'final_event' IS DISTINCT FROM jsonb_build_object('outcome','completed','feature_instance_digest',actual_event->>'feature_instance_digest',
 'feature_input_digest',actual_event->>'feature_input_digest','event_procedure',actual_event->>'event_procedure','final_event_score',actual_event->'final_event_score') THEN
 RAISE EXCEPTION 'grade final event differs from actual sealed producer score' USING ERRCODE='23514'; END IF;
 ELSIF event->'final_event' IS DISTINCT FROM 'null'::jsonb OR frame->>'partition'='final_event_calibration' THEN
 RAISE EXCEPTION 'grade invents a completed final event' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF jsonb_array_length(coverage->'event_ids')<>(SELECT count(*) FROM jsonb_array_elements(carrier->'members') packet WHERE packet->'body'->>'candidate_type'='record' AND packet->'body'->>'family'=question->>'family')
 OR coverage->>'outcome' IS DISTINCT FROM (CASE WHEN jsonb_array_length(coverage->'event_ids')=0 THEN 'no_output' ELSE 'completed' END) THEN
 RAISE EXCEPTION 'grade coverage omits actual eligible reading events' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF sources_ IS DISTINCT FROM frame->'sources' OR jsonb_array_length(frame->'events')<>event_count
 OR jsonb_array_length(pins)<>(SELECT count(*) FROM jsonb_array_elements(r.binding->'inputs') item WHERE item->>'role'='sources')
 OR selected_count<>(SELECT count(*) FROM jsonb_array_elements(r.binding->'inputs') item WHERE item->>'role'='prediction') THEN
 RAISE EXCEPTION 'grade does not cover exact declared source and prediction populations' USING ERRCODE='23514'; END IF;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_require_producer(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE definition sem.data_operation_definition; output jsonb;
BEGIN
 IF r.operation_id IS DISTINCT FROM '__GRADE_OPERATION__' THEN RETURN; END IF;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF definition.profile IS DISTINCT FROM 'derivation' OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM '__GRADE_FACTORY__'
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR completion->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR completion->>'outcome' IS DISTINCT FROM 'success' OR completion->'inputs' IS DISTINCT FROM r.binding->'inputs'
 OR jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'record grade requires its actual admitted pure CPU implementation and complete inputs' USING ERRCODE='23514'; END IF;
 output:=completion->'outputs'->0;
 IF output->>'role' IS DISTINCT FROM 'grade' OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind='__GRADE_KIND__' AND kind.universe='evaluator') THEN
 RAISE EXCEPTION 'record grade output differs from protected whole scalar contract' USING ERRCODE='23514'; END IF;
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_require_record_grade_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
BEGIN
 IF r.operation_id IS DISTINCT FROM '__GRADE_OPERATION__' THEN RETURN; END IF;
 PERFORM ops.ddo_record_grade_require_producer(r,completion);
 PERFORM ops.ddo_record_grade_require_frame(r,data.ddo_json(completion->'outputs'->0->'product'->'body'));
END $grade$;

CREATE OR REPLACE FUNCTION ops.ddo_record_grade_dependencies_valid(episode text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $grade$
DECLARE r ops.data_request; completion jsonb; captured record;
BEGIN
 SELECT request.* INTO STRICT r FROM ops.data_request request JOIN ops.data_derivation producer ON producer.request_id=request.id WHERE producer.id=episode;
 IF r.operation_id IS DISTINCT FROM '__GRADE_OPERATION__' THEN RETURN true; END IF;
 SELECT intent.payload INTO STRICT completion FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=intent.id WHERE producer.id=episode;
 -- The original native receipt seals the complete immutable frame checks. A
 -- different kernel requires reassessment instead of trusting an old guard.
 IF NOT EXISTS(SELECT FROM sem.artifact artifact WHERE artifact.release_id=r.release_id
 AND artifact.artifact_name='data_operation_native_definitions.json'
 AND convert_from(artifact.content,'UTF8')::jsonb->>'native_digest'='__DDO_SOURCE_DIGEST__') THEN RETURN false; END IF;
 PERFORM ops.ddo_record_grade_require_producer(r,completion);
 FOR captured IN SELECT * FROM ops.ddo_record_grade_cuts(r) LOOP
 PERFORM ops.ddo_record_grade_require_cut(r.project_id,captured.cut_text,captured.cut_id);
 END LOOP;
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $grade$;
""".replace("__GRADE_OPERATION__", GRADE_OPERATION).replace("__GRADE_FACTORY__", GRADE_FACTORY).replace("__GRADE_KIND__", GRADE_KIND) + "\n".join(
        f"REVOKE ALL ON FUNCTION ops.{name}({arguments}) FROM PUBLIC;"
        for name, arguments in (
            ("ddo_record_grade_input_value", "text,text,text"),
            ("ddo_record_grade_input", "ops.data_request,text"),
            ("ddo_record_grade_require_finite_census", "ops.data_demand,ops.data_demand_read"),
            ("ddo_record_grade_cut_scopes", "text,text"),
            ("ddo_record_grade_require_cut", "text,text,text"),
            ("ddo_record_grade_acquire_census", "text,text,text"),
            ("ddo_record_grade_cuts", "ops.data_request"),
            ("ddo_record_grade_require_producer", "ops.data_request,jsonb"),
            ("ddo_record_grade_completion_scopes", "ops.data_request"),
            ("ddo_record_grade_dependency_scopes", "text"),
            ("ddo_record_grade_require_frame", "ops.data_request,jsonb"),
            ("ddo_require_record_grade_completion", "ops.data_request,jsonb"),
            ("ddo_record_grade_dependencies_valid", "text"),
        )
    )
