"""Exact evaluator-policy issuance at the existing native completion boundary.

The scalar projection grants no authority. Its caller proves the selected protected
fit product's actual producing episode and commits through the common receipt.
"""

from __future__ import annotations

from .record_policy_authority import DdoRecordPolicyAuthorization


def record_policy_completion_native_sql() -> str:
    # This is the executable field correspondence, not another public schema.
    # Refuse an unhandled contract addition instead of silently disclosing it.
    projection = {
        "version": "to_jsonb('record-policy-authorization-1'::text)",
        "policy_instance_digest": "to_jsonb(encode(sha256(convert_to(basis->>'instance_canonical_json','UTF8')),'hex'))",
        "feature_instance_digest": "to_jsonb(encode(sha256(convert_to(basis->>'feature_canonical_json','UTF8')),'hex'))",
        "calibration_digest": "to_jsonb(encode(sha256(convert_to(basis->>'calibration_canonical_json','UTF8')),'hex'))",
        "algorithm": "basis->'instance'->'feature'->'algorithm'",
        "parameters": "basis->'instance'->'feature'->'parameters'",
        "family": "basis->'instance'->'feature'->'applicability'->'family'",
        "source_release_id": "basis->'instance'->'feature'->'applicability'->'release_id'",
        "subset": "basis->'instance'->'feature'->'applicability'->'subset'",
        "event_procedure": "basis->'instance'->'calibration'->'event_procedure'",
        "threshold_procedure": "basis->'instance'->'threshold_procedure'",
        "threshold": "basis->'instance'->'threshold'",
        "calibration_slope": "basis->'instance'->'calibration'->'slope'",
        "calibration_intercept": "basis->'instance'->'calibration'->'intercept'",
        **{
            name: f"basis->'{name}'"
            for name in (
                "family_contract",
                "reading_recipe",
                "numerical_policy",
                "judgment_basis_digest",
                "applicability",
            )
        },
    }
    if projection.keys() != DdoRecordPolicyAuthorization.model_fields.keys():
        raise ValueError("native policy projection must cover the exact public contract")
    fields = ",\n".join(f"'{name}',{value}" for name, value in sorted(projection.items()))

    def exact_field(name, expression):
        if name == "version" or (
            name.endswith("_digest")
            and name in {"policy_instance_digest", "feature_instance_digest", "calibration_digest"}
        ):
            return f"jsonb_build_array('string',projected->>'{name}')"
        # Every other public field copies one declared private semantic subtree.
        parts = expression.split("->")
        if parts[0] != "basis":
            raise ValueError("native policy field lacks its exact private correspondence")
        value = "basis"
        for part in parts[1:]:
            value = f"data.ddo_field({value},{part})"
        return value

    meaning_fields = ",\n".join(
        f"jsonb_build_array('{name}',{exact_field(name, value)})"
        for name, value in sorted(projection.items())
    )
    return (
        r"""
CREATE OR REPLACE FUNCTION ops.ddo_policy_authorization_value(basis jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $policy$
DECLARE instance jsonb:=basis->'instance'; feature jsonb:=instance->'feature'; calibration jsonb:=instance->'calibration';
BEGIN
 IF basis->>'version' IS DISTINCT FROM 'fitted-record-policy-1'
 OR jsonb_typeof(instance) IS DISTINCT FROM 'object'
 OR jsonb_typeof(feature) IS DISTINCT FROM 'object'
 OR jsonb_typeof(calibration) IS DISTINCT FROM 'object'
 OR jsonb_typeof(basis->'instance_canonical_json') IS DISTINCT FROM 'string'
 OR jsonb_typeof(basis->'feature_canonical_json') IS DISTINCT FROM 'string'
 OR jsonb_typeof(basis->'calibration_canonical_json') IS DISTINCT FROM 'string'
 OR (basis->>'instance_canonical_json')::jsonb IS DISTINCT FROM instance
 OR (basis->>'feature_canonical_json')::jsonb IS DISTINCT FROM feature
 OR (basis->>'calibration_canonical_json')::jsonb IS DISTINCT FROM calibration
 OR calibration->>'feature_instance_digest' IS DISTINCT FROM encode(sha256(convert_to(basis->>'feature_canonical_json','UTF8')),'hex')
 OR feature->'fit'->>'partition' IS DISTINCT FROM 'feature_fit'
 OR feature->'fit'->>'standing' IS DISTINCT FROM 'fitted'
 OR calibration->'fit'->>'partition' IS DISTINCT FROM 'final_event_calibration'
 OR calibration->'fit'->>'standing' IS DISTINCT FROM 'fitted'
 OR calibration->'fit'->>'frame_digest' IS NOT DISTINCT FROM feature->'fit'->>'frame_digest'
 OR calibration->'fit'->>'reference_digest' IS NOT DISTINCT FROM feature->'fit'->>'reference_digest' THEN
 RAISE EXCEPTION 'policy authorization differs from canonical fitted and held-out instance' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object(__PUBLIC_FIELDS__);
END $policy$;

CREATE OR REPLACE FUNCTION ops.ddo_policy_authorization_meaning(basis jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $policy$
DECLARE projected jsonb:=ops.ddo_policy_authorization_value(data.ddo_json(basis));
BEGIN
 RETURN data.ddo_normalize(jsonb_build_array('mapping',jsonb_build_array(__PUBLIC_MEANING_FIELDS__)));
END $policy$;

CREATE OR REPLACE FUNCTION ops.ddo_require_policy_authorization_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $policy$
DECLARE definition sem.data_operation_definition; selected jsonb; output jsonb;
 basis kb.data_product; basis_kind sem.data_kind_contract; producing ops.data_derivation;
 fit_definition sem.data_operation_definition; fit_intent ops.data_completion_intent; fit_request ops.data_request; expected jsonb;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF NOT coalesce(ops.ddo_policy_command_eligible(definition),false) THEN
 IF definition.operation_id='record_policy.authorize'
 OR EXISTS(SELECT FROM jsonb_array_elements(definition.support_contract->'effects') effect
 WHERE effect->>'name'='native-evaluator-policy-authorization') THEN
 RAISE EXCEPTION 'policy authorization requires its exact admitted command/effect/factory' USING ERRCODE='23514'; END IF;
 RETURN;
 END IF;
 IF NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_evaluator','MEMBER') THEN
 RAISE EXCEPTION 'policy authorization requires native evaluator purpose' USING ERRCODE='42501'; END IF;
 IF completion->>'outcome' IS DISTINCT FROM 'success'
 OR jsonb_array_length(completion->'inputs')<>1 OR jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'policy authorization requires one exact fitted basis and public conclusion' USING ERRCODE='23514'; END IF;
 selected:=completion->'inputs'->0; output:=completion->'outputs'->0;
 IF selected->>'role' IS DISTINCT FROM 'basis' OR selected->>'member_id' IS NOT NULL
 OR (selected->>'position')::integer IS DISTINCT FROM 0 OR (selected->>'multiplicity')::integer IS DISTINCT FROM 1
 OR output->>'role' IS DISTINCT FROM 'authorization' OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb THEN
 RAISE EXCEPTION 'policy authorization must consume and produce exact whole scalar products' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT basis FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 SELECT * INTO STRICT basis_kind FROM sem.data_kind_contract WHERE kind_contract=basis.kind_contract;
 IF basis_kind.kind IS DISTINCT FROM 'https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoFittedRecordPolicy'
 OR basis_kind.universe IS DISTINCT FROM 'evaluator' THEN
 RAISE EXCEPTION 'policy basis is not the protected fitted contract' USING ERRCODE='23514'; END IF;
 -- The exact selected producer must be part of this request's authenticated support;
 -- possessing a well-typed fitted body or an unrelated fit receipt is insufficient.
 IF (SELECT count(*) FROM ops.data_derivation producer
 JOIN ops.data_derivation_output produced ON produced.derivation_id=producer.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=producer.intent_id
 WHERE produced.product_id=basis.id AND produced.member_id IS NULL AND produced.role='fitted'
 AND produced.position=0 AND produced.multiplicity=1 AND producer.outcome='success'
 AND EXISTS(SELECT FROM jsonb_array_elements(completion->'support') support
 WHERE support->>'derivation_id'=producer.id)
 AND ops.ddo_input_support_selection(selected) ? producer.id)<>1 THEN
 RAISE EXCEPTION 'policy basis lacks one exact supported successful native fit receipt' USING ERRCODE='23514'; END IF;
 SELECT producer.* INTO STRICT producing FROM ops.data_derivation producer
 JOIN ops.data_derivation_output produced ON produced.derivation_id=producer.id
 WHERE produced.product_id=basis.id AND produced.member_id IS NULL AND produced.role='fitted'
 AND EXISTS(SELECT FROM jsonb_array_elements(completion->'support') support WHERE support->>'derivation_id'=producer.id)
 AND ops.ddo_input_support_selection(selected) ? producer.id;
 SELECT operation.* INTO STRICT fit_definition FROM sem.data_operation_definition operation
 JOIN ops.data_request request ON request.operation_id=operation.operation_id
 WHERE request.id=producing.request_id AND request.project_id=r.project_id AND operation.release_id=producing.release_id;
 SELECT * INTO STRICT fit_intent FROM ops.data_completion_intent WHERE id=producing.intent_id
 AND request_id=producing.request_id AND generation=producing.generation;
 IF (fit_intent.producer_task_id,fit_intent.producer_attempt,fit_intent.runtime_id) IS DISTINCT FROM
 (producing.producer_task_id,producing.producer_attempt,producing.runtime_id) THEN
 RAISE EXCEPTION 'policy fit basis differs from original producer fences' USING ERRCODE='23514'; END IF;
 IF fit_definition.operation_id IS DISTINCT FROM 'record_policy.fit' OR fit_definition.profile IS DISTINCT FROM 'derivation'
 OR fit_definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR fit_definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM 'corpus_structure.methods.declared_record_policy.RecordPolicyFit.acquire_port'
 OR (fit_definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (fit_definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR fit_intent.payload->>'implementation_revision' IS DISTINCT FROM fit_definition.implementation_revision
 OR jsonb_array_length(coalesce(fit_intent.payload->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR producing.recipe IS DISTINCT FROM fit_definition.recipe THEN
 RAISE EXCEPTION 'policy basis is not the actual admitted protected CPU fit implementation' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT fit_request FROM ops.data_request WHERE id=producing.request_id AND project_id=r.project_id;
 fit_request.release_id:=producing.release_id; fit_request.runtime_id:=producing.runtime_id;
 fit_request.recipe:=producing.recipe; fit_request.generation:=producing.generation;
 fit_request.binding:=fit_request.binding||jsonb_build_object('inputs',fit_intent.payload->'inputs','support',fit_intent.payload->'support');
 -- Issuance rechecks the actual original fit inputs, even for a receipt sealed
 -- before this guard existed. A same-kind/self-consistent body cannot substitute
 -- another legitimate request's grades or typed fitting specification.
 PERFORM ops.ddo_require_record_fit_completion(fit_request,fit_intent.payload);
 IF data.ddo_normalize(fit_intent.payload->'outputs'->0->'product'->'body') IS DISTINCT FROM basis.canonical_body THEN
 RAISE EXCEPTION 'policy basis differs from actual original fitted completion body' USING ERRCODE='23514'; END IF;
 expected:=ops.ddo_policy_authorization_value(data.ddo_json(basis.canonical_body));
 IF expected->'applicability'->>'project_id' IS DISTINCT FROM r.project_id
 OR NOT sem.ddo_model_class_contract(r.release_id,expected->>'family_contract')
 OR NOT EXISTS(SELECT FROM sem.data_operation_definition reading WHERE reading.release_id=r.release_id
 AND reading.operation_id='resolve.m1_readings/declared' AND reading.recipe=expected->>'reading_recipe')
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind='https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization' AND kind.universe='ordinary')
 OR data.ddo_normalize(output->'product'->'body') IS DISTINCT FROM ops.ddo_policy_authorization_meaning(basis.canonical_body) THEN
 RAISE EXCEPTION 'policy authorization public conclusion differs from exact fitted basis and current interpretation' USING ERRCODE='23514'; END IF;
END $policy$;
""".replace("__PUBLIC_FIELDS__", fields).replace("__PUBLIC_MEANING_FIELDS__", meaning_fields)
        + _fit_completion_sql()
    )


def _fit_completion_sql() -> str:
    """Actual selected grade/specification correspondence, with CPU-owned numerics."""
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_require_record_fit_correspondence(feature_meaning jsonb,calibration_meaning jsonb,specification_meaning jsonb,basis_meaning jsonb)
RETURNS void LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE feature_grade jsonb:=data.ddo_json(feature_meaning); calibration_grade jsonb:=data.ddo_json(calibration_meaning);
 specification jsonb:=data.ddo_json(specification_meaning); basis jsonb:=data.ddo_json(basis_meaning);
 first_ jsonb:=feature_grade->'frame'; second_ jsonb:=calibration_grade->'frame';
 instance_meaning jsonb:=data.ddo_field(basis_meaning,'instance'); instance jsonb:=basis->'instance';
 feature jsonb:=instance->'feature'; calibration jsonb:=instance->'calibration';
 feature_coverage text; calibration_coverage text; judgment_basis text;
 first_positive bigint; first_negative bigint; first_groups bigint; second_positive bigint; second_negative bigint; second_groups bigint; wrong_final boolean;
BEGIN
 feature_coverage:=ops.ddo_digest(first_->'coverage'); calibration_coverage:=ops.ddo_digest(second_->'coverage');
 judgment_basis:=ops.ddo_digest(data.ddo_normalize(jsonb_build_array('sequence',jsonb_build_array(
 jsonb_build_array('string',feature_grade->>'frame_digest'),jsonb_build_array('string',calibration_grade->>'frame_digest'),specification_meaning))));
 IF data.ddo_field(instance_meaning,'feature') IS DISTINCT FROM data.ddo_field(specification_meaning,'frozen_feature')
 OR data.ddo_field(instance_meaning,'threshold') IS DISTINCT FROM data.ddo_field(specification_meaning,'threshold')
 OR data.ddo_field(instance_meaning,'threshold_procedure') IS DISTINCT FROM data.ddo_field(specification_meaning,'threshold_procedure')
 OR data.ddo_field(instance_meaning,'conditioning_assumptions') IS DISTINCT FROM data.ddo_field(specification_meaning,'assumptions')
 OR data.ddo_field(basis_meaning,'applicability') IS DISTINCT FROM data.ddo_field(specification_meaning,'applicability')
 OR data.ddo_field(basis_meaning,'family_contract') IS DISTINCT FROM data.ddo_field(specification_meaning,'family_contract')
 OR data.ddo_field(basis_meaning,'reading_recipe') IS DISTINCT FROM data.ddo_field(specification_meaning,'reading_recipe')
 OR basis->>'judgment_basis_digest' IS DISTINCT FROM judgment_basis THEN
 RAISE EXCEPTION 'fitted policy differs from actual frozen feature, typed specification or judgment basis' USING ERRCODE='23514'; END IF;
 IF (first_->>'partition',second_->>'partition') IS DISTINCT FROM ('feature_fit','final_event_calibration')
 OR specification->'feature_selection'->>'frame_digest' IS DISTINCT FROM feature_grade->>'frame_digest'
 OR specification->'calibration_selection'->>'frame_digest' IS DISTINCT FROM calibration_grade->>'frame_digest'
 OR feature_grade->>'frame_digest' IS NOT DISTINCT FROM calibration_grade->>'frame_digest'
 OR first_->>'reference_digest' IS NOT DISTINCT FROM second_->>'reference_digest'
 OR NOT coalesce(second_->'held_out_from' ? (feature_grade->>'frame_digest'),false)
 OR (first_->>'project_id',first_->>'family_contract',first_->>'reading_recipe') IS DISTINCT FROM
 (specification->'applicability'->>'project_id',specification->>'family_contract',specification->>'reading_recipe')
 OR (second_->>'project_id',second_->>'family_contract',second_->>'reading_recipe') IS DISTINCT FROM
 (first_->>'project_id',first_->>'family_contract',first_->>'reading_recipe')
 OR (first_->>'family',first_->>'subset',first_->>'rubric_digest') IS DISTINCT FROM
 (second_->>'family',second_->>'subset',second_->>'rubric_digest') THEN
 RAISE EXCEPTION 'fit inputs differ from actual separate declared grade frames and interpretation' USING ERRCODE='23514'; END IF;
 IF (feature->'fit'->>'frame_digest',feature->'fit'->>'reference_digest',feature->'fit'->>'coverage_digest') IS DISTINCT FROM
 (feature_grade->>'frame_digest',first_->>'reference_digest',feature_coverage)
 OR (calibration->'fit'->>'frame_digest',calibration->'fit'->>'reference_digest',calibration->'fit'->>'coverage_digest') IS DISTINCT FROM
 (calibration_grade->>'frame_digest',second_->>'reference_digest',calibration_coverage)
 OR feature->'fit'->>'provenance' IS DISTINCT FROM 'declared-selected-complete-record-grade-1'
 OR calibration->'fit'->>'provenance' IS DISTINCT FROM 'declared-selected-complete-record-grade-1'
 OR feature->'fit'->>'conditioning_assumptions' IS DISTINCT FROM specification->>'assumptions'
 OR calibration->'fit'->>'conditioning_assumptions' IS DISTINCT FROM specification->>'assumptions'
 OR (feature->'applicability'->>'release_id',feature->'applicability'->>'family',feature->'applicability'->>'subset',feature->'applicability'->>'assumptions') IS DISTINCT FROM
 (first_->>'prediction_release_id',first_->>'family',first_->>'subset',specification->>'assumptions')
 OR calibration->>'coverage_digest' IS DISTINCT FROM calibration_coverage
 OR calibration->>'event_procedure' IS DISTINCT FROM specification->>'event_procedure'
 OR calibration->>'assumptions' IS DISTINCT FROM specification->>'assumptions'
 OR calibration->>'feature_instance_digest' IS DISTINCT FROM encode(sha256(convert_to(basis->>'feature_canonical_json','UTF8')),'hex') THEN
 RAISE EXCEPTION 'fitted feature/calibration provenance differs from actual input frames and procedure' USING ERRCODE='23514'; END IF;
 -- Population facts are conclusions about the exact retained grade, not free
 -- diagnostic labels. The numerical coefficients/convergence remain CPU-owned.
 SELECT count(*) FILTER(WHERE event->>'correct'='true'),count(*) FILTER(WHERE event->>'correct'='false'),count(DISTINCT event->>'origin_group')
 INTO first_positive,first_negative,first_groups FROM jsonb_array_elements(first_->'events') event;
 SELECT count(*) FILTER(WHERE event->>'correct'='true'),count(*) FILTER(WHERE event->>'correct'='false'),count(DISTINCT event->>'origin_group'),
 bool_or(event->'final_event'->>'feature_instance_digest' IS DISTINCT FROM calibration->>'feature_instance_digest'
 OR event->'final_event'->>'event_procedure' IS DISTINCT FROM specification->>'event_procedure')
 INTO second_positive,second_negative,second_groups,wrong_final FROM jsonb_array_elements(second_->'events') event;
 IF (feature->'fit'->>'positive_count')::bigint IS DISTINCT FROM first_positive
 OR (feature->'fit'->>'negative_count')::bigint IS DISTINCT FROM first_negative
 OR (calibration->'fit'->>'positive_count')::bigint IS DISTINCT FROM second_positive
 OR (calibration->'fit'->>'negative_count')::bigint IS DISTINCT FROM second_negative
 OR (feature->'fit'->>'declared_origin_group_count')::bigint IS DISTINCT FROM first_groups
 OR (calibration->'fit'->>'declared_origin_group_count')::bigint IS DISTINCT FROM second_groups
 OR coalesce(wrong_final,false) THEN
 RAISE EXCEPTION 'fitted diagnostics or final events differ from complete actual grade populations' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(first_->'origin_groups') a CROSS JOIN jsonb_array_elements(second_->'origin_groups') b
 WHERE a->>'origin_group'=b->>'origin_group')
 OR EXISTS(WITH a AS (SELECT value->'source'->>'original_source' id FROM jsonb_array_elements(first_->'origin_groups')
 UNION SELECT copy->>'original_source' FROM jsonb_array_elements(first_->'origin_groups') origin_ CROSS JOIN LATERAL jsonb_array_elements(origin_->'copied_from') copy),
 b AS (SELECT value->'source'->>'original_source' id FROM jsonb_array_elements(second_->'origin_groups')
 UNION SELECT copy->>'original_source' FROM jsonb_array_elements(second_->'origin_groups') origin_ CROSS JOIN LATERAL jsonb_array_elements(origin_->'copied_from') copy)
 SELECT FROM a JOIN b USING(id)) THEN
 RAISE EXCEPTION 'fit and calibration share an original, known copied source or origin group' USING ERRCODE='23514'; END IF;
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_require_finite_cut(d ops.data_demand,boundary ops.data_demand_read)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE p jsonb:=jsonb_build_object('scope',boundary.scope); node record;
BEGIN
 IF EXISTS(SELECT FROM jsonb_array_elements(d.selection->'operations') selected
 WHERE selected->>'operation' IN ('record_policy.fit','record_policy.authorize')) THEN
 RAISE EXCEPTION 'fit grade selection cannot select a fit or authorization census' USING ERRCODE='23514'; END IF;
 FOR node IN __DDO_CORE_RECORD_GRADE_CENSUS_NODES__ LOOP
 IF node.kind='episode' AND EXISTS(SELECT FROM ops.data_derivation producer JOIN ops.data_request request ON request.id=producer.request_id
 WHERE producer.id=node.id AND (request.operation_id IN ('record_policy.fit','record_policy.authorize')
 OR EXISTS(SELECT FROM ops.data_derivation_output output JOIN kb.data_product product ON product.id=output.product_id
 JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract WHERE output.derivation_id=producer.id
 AND kind.kind IN ('https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoFittedRecordPolicy','https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization')))) THEN
 RAISE EXCEPTION 'fit grade selection support reaches fitted policy authority' USING ERRCODE='23514'; END IF;
 END LOOP;
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_selections(r ops.data_request)
RETURNS TABLE(role_name text,selection jsonb) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE specification jsonb:=ops.ddo_record_grade_input(r,'specification')->'body'; selected jsonb; name_ text;
BEGIN
 FOR name_,selected IN SELECT 'feature_grade',specification->'feature_selection' UNION ALL SELECT 'calibration_grade',specification->'calibration_selection' LOOP
 IF selected->>'project_id' IS DISTINCT FROM r.project_id
 OR (selected->>'cut_canonical_json')::jsonb->>'project_id' IS DISTINCT FROM r.project_id
 OR (selected->>'cut_canonical_json')::jsonb->>'demand_id' IS DISTINCT FROM selected->>'demand_id'
 OR (selected->>'cut_canonical_json')::jsonb->>'read_id' IS DISTINCT FROM selected->>'read_id'
 OR selected->>'expected_cut' IS DISTINCT FROM 'cut-selection:'||encode(sha256(convert_to(selected->>'cut_canonical_json','UTF8')),'hex') THEN
 RAISE EXCEPTION 'fit selection differs from its actual original project/cut/read pins' USING ERRCODE='23514'; END IF;
 role_name:=name_; selection:=selected; RETURN NEXT;
 END LOOP;
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_cut_scopes(project text,selection jsonb)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE d ops.data_demand; boundary ops.data_demand_read; p jsonb; actual jsonb;
BEGIN
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=ddo_record_fit_cut_scopes.selection->>'demand_id'
 AND project_id=ddo_record_fit_cut_scopes.project;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=ddo_record_fit_cut_scopes.selection->>'read_id' AND demand_id=d.id;
 p:=jsonb_build_object('scope',boundary.scope);
 PERFORM ops.ddo_record_fit_require_finite_cut(d,boundary);
 __DDO_CORE_CUT_SELECTION__ INTO actual;
 IF actual IS DISTINCT FROM (selection->>'cut_canonical_json')::jsonb THEN
 RAISE EXCEPTION 'fit grade cut differs from exact native retained selection' USING ERRCODE='23514'; END IF;
 RETURN QUERY __DDO_CORE_SUPPORT_SCOPES__;
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_completion_scopes(r ops.data_request)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE selected record;
BEGIN
 IF r.operation_id IS DISTINCT FROM 'record_policy.fit' THEN RETURN; END IF;
 FOR selected IN SELECT DISTINCT selection FROM ops.ddo_record_fit_selections(r) LOOP
 RETURN QUERY SELECT * FROM ops.ddo_record_fit_cut_scopes(r.project_id,selected.selection);
 END LOOP;
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_dependency_scopes(episode text)
RETURNS SETOF text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE r ops.data_request; producing ops.data_derivation; intent ops.data_completion_intent;
BEGIN
 SELECT * INTO STRICT producing FROM ops.data_derivation WHERE id=episode;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=producing.request_id;
 IF r.operation_id IS DISTINCT FROM 'record_policy.fit' THEN RETURN; END IF;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=producing.intent_id
 AND request_id=producing.request_id AND generation=producing.generation;
 IF (intent.producer_task_id,intent.producer_attempt,intent.runtime_id) IS DISTINCT FROM
 (producing.producer_task_id,producing.producer_attempt,producing.runtime_id) THEN
 RAISE EXCEPTION 'fit dependency scopes differ from original producer fences' USING ERRCODE='23514'; END IF;
 r.release_id:=producing.release_id; r.runtime_id:=producing.runtime_id;
 r.recipe:=producing.recipe; r.generation:=producing.generation;
 r.binding:=r.binding||jsonb_build_object('inputs',intent.payload->'inputs','support',intent.payload->'support');
 RETURN QUERY SELECT * FROM ops.ddo_record_fit_completion_scopes(r);
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_require_selection(r ops.data_request,role_name text,selection jsonb,authenticate_output boolean)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE d ops.data_demand; boundary ops.data_demand_read; p jsonb; actual jsonb; scope_key text; current_trust jsonb:='{}'; epoch bigint;
 p_use text:=selection->>'use_id'; p_product text:=selection->>'product_id'; p_derivation text:=selection->>'derivation_id'; admitted boolean;
 chosen jsonb; grade jsonb; producer ops.data_derivation; definition sem.data_operation_definition; intent ops.data_completion_intent;
BEGIN
 -- scopes() authenticates the exact project/cut and refuses recursive fit graphs
 -- before invoking ordinary read validity. The enclosing owner locks this same
 -- scope union once in canonical order before request/task fences.
 FOR scope_key IN SELECT * FROM ops.ddo_record_fit_cut_scopes(r.project_id,selection) LOOP
 SELECT coalesce((SELECT scope.epoch FROM ops.data_trust_scope scope WHERE scope.scope=scope_key AND scope.project_id=r.project_id),0) INTO epoch;
 current_trust:=current_trust||jsonb_build_object(scope_key,epoch);
 END LOOP;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=selection->>'read_id' AND demand_id=selection->>'demand_id';
 IF ops.ddo_trust_snapshot_meaning(current_trust) IS DISTINCT FROM ops.ddo_trust_snapshot_meaning(boundary.trust_snapshot) THEN
 RAISE EXCEPTION 'fit grade current trust differs from original retained cut' USING ERRCODE='23514'; END IF;
 IF NOT authenticate_output THEN RETURN NULL; END IF;
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=boundary.demand_id AND project_id=r.project_id;
 p:=jsonb_build_object('scope',boundary.scope);
 __DDO_CORE_SELECTED_SUPPORT_OUTPUT__ INTO admitted;
 IF NOT coalesce(admitted,false) THEN RAISE EXCEPTION 'fit grade is outside exact current native selected support' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT chosen FROM jsonb_array_elements(r.binding->'inputs') item(value)
 WHERE value->>'role'=role_name AND value->>'product_id'=p_product AND value->>'member_id' IS NULL
 AND (value->>'multiplicity')::integer=1;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(r.binding->'support') support WHERE support->>'derivation_id'=p_derivation AND support->>'role'=role_name)
 OR NOT (ops.ddo_input_support_selection(chosen) ? p_derivation) THEN
 RAISE EXCEPTION 'fit grade selection differs from actual bound input product and producing episode' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT producer FROM ops.data_derivation WHERE id=p_derivation AND outcome='success';
 SELECT operation.* INTO STRICT definition FROM sem.data_operation_definition operation JOIN ops.data_request request ON request.operation_id=operation.operation_id
 WHERE request.id=producer.request_id AND request.project_id=r.project_id AND operation.release_id=producer.release_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=producer.intent_id
 AND request_id=producer.request_id AND generation=producer.generation;
 IF (intent.producer_task_id,intent.producer_attempt,intent.runtime_id) IS DISTINCT FROM
 (producer.producer_task_id,producer.producer_attempt,producer.runtime_id) THEN
 RAISE EXCEPTION 'fit grade differs from original producer fences' USING ERRCODE='23514'; END IF;
 IF definition.operation_id IS DISTINCT FROM 'record_policy.grade' OR definition.profile IS DISTINCT FROM 'derivation'
 OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM 'corpus_structure.methods.declared_record_policy.RecordPolicyGrade.acquire_port'
 OR intent.payload->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR producer.recipe IS DISTINCT FROM definition.recipe
 OR jsonb_array_length(coalesce(intent.payload->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt JOIN ops.data_derivation_output output ON output.derivation_id=receipt.derivation_id
 JOIN kb.data_product product ON product.id=output.product_id JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract
 WHERE receipt.derivation_id=producer.id AND receipt.intent_id=intent.id AND output.product_id=p_product AND output.member_id IS NULL
 AND output.role='grade' AND output.position=0 AND output.multiplicity=1 AND kind.kind='https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordGrade' AND kind.universe='evaluator') THEN
 RAISE EXCEPTION 'fit grade lacks actual protected grade CPU/common producer custody' USING ERRCODE='23514'; END IF;
 SELECT canonical_body INTO STRICT grade FROM kb.data_product WHERE id=p_product AND project_id=r.project_id;
 IF data.ddo_json(grade)->>'frame_digest' IS DISTINCT FROM selection->>'frame_digest'
 OR data.ddo_json(grade)->'frame'->>'partition' IS DISTINCT FROM (CASE WHEN role_name='feature_grade' THEN 'feature_fit' ELSE 'final_event_calibration' END) THEN
 RAISE EXCEPTION 'fit grade frame or partition differs from its actual selected input' USING ERRCODE='23514'; END IF;
 RETURN grade;
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_require_producer(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE definition sem.data_operation_definition; output jsonb;
BEGIN
 IF r.operation_id IS DISTINCT FROM 'record_policy.fit' THEN RETURN; END IF;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF definition.profile IS DISTINCT FROM 'derivation' OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM 'corpus_structure.methods.declared_record_policy.RecordPolicyFit.acquire_port'
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR completion->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR r.recipe IS DISTINCT FROM definition.recipe
 OR completion->'inputs' IS DISTINCT FROM r.binding->'inputs'
 OR completion->'support' IS DISTINCT FROM r.binding->'support'
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1 THEN
 RAISE EXCEPTION 'fit completion requires actual protected fit factory/CPU and exact declared inputs' USING ERRCODE='23514'; END IF;
 IF completion->>'outcome'='empty' AND completion->'outputs'='[]'::jsonb THEN RETURN; END IF;
 IF completion->>'outcome' IS DISTINCT FROM 'success' OR jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'fit completion requires one fitted scalar or a non-authoritative empty result' USING ERRCODE='23514'; END IF;
 output:=completion->'outputs'->0;
 IF output->>'role' IS DISTINCT FROM 'fitted' OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind='https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoFittedRecordPolicy' AND kind.universe='evaluator') THEN
 RAISE EXCEPTION 'fit output differs from exact protected fitted scalar contract' USING ERRCODE='23514'; END IF;
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_require_record_fit_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE selected record; feature jsonb; calibration jsonb; output jsonb; specification jsonb; cpu_output jsonb;
BEGIN
 IF r.operation_id IS DISTINCT FROM 'record_policy.fit' THEN RETURN; END IF;
 PERFORM ops.ddo_record_fit_require_producer(r,completion);
 cpu_output:=data.ddo_field(ops.ddo_cpu_reply_output(r,completion),'fitted');
 FOR selected IN SELECT * FROM ops.ddo_record_fit_selections(r) LOOP
 IF selected.role_name='feature_grade' THEN feature:=ops.ddo_record_fit_require_selection(r,selected.role_name,selected.selection,true);
 ELSE calibration:=ops.ddo_record_fit_require_selection(r,selected.role_name,selected.selection,true); END IF;
 END LOOP;
 IF completion->>'outcome'='empty' THEN
 IF cpu_output IS DISTINCT FROM '["null"]'::jsonb THEN
 RAISE EXCEPTION 'empty fit differs from its actual CPU result' USING ERRCODE='23514'; END IF;
 RETURN; END IF;
 output:=completion->'outputs'->0;
 IF cpu_output IS DISTINCT FROM data.ddo_normalize(output->'product'->'body') THEN
 RAISE EXCEPTION 'fitted policy differs from its actual CPU result' USING ERRCODE='23514'; END IF;
 SELECT product.canonical_body INTO STRICT specification FROM jsonb_array_elements(r.binding->'inputs') chosen
 JOIN kb.data_product product ON product.id=chosen->>'product_id' AND product.project_id=r.project_id
 WHERE chosen->>'role'='specification' AND chosen->>'member_id' IS NULL AND (chosen->>'multiplicity')::integer=1;
 PERFORM ops.ddo_require_record_fit_correspondence(feature,calibration,specification,data.ddo_normalize(output->'product'->'body'));
 -- Existing projection authenticates the three retained canonical instance texts.
 PERFORM ops.ddo_policy_authorization_value(data.ddo_json(output->'product'->'body'));
END $fit$;

CREATE OR REPLACE FUNCTION ops.ddo_record_fit_dependencies_valid(episode text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE r ops.data_request; selected record; producing ops.data_derivation; intent ops.data_completion_intent;
BEGIN
 SELECT * INTO STRICT producing FROM ops.data_derivation WHERE id=episode;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=producing.request_id;
 IF r.operation_id IS DISTINCT FROM 'record_policy.fit' THEN RETURN true; END IF;
 IF NOT EXISTS(SELECT FROM ops.data_derivation producer JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=producer.intent_id
 JOIN sem.artifact artifact ON artifact.release_id=producer.release_id AND artifact.artifact_name='data_operation_native_definitions.json'
 WHERE producer.id=episode AND convert_from(artifact.content,'UTF8')::jsonb->>'native_digest'='__DDO_SOURCE_DIGEST__') THEN RETURN false; END IF;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=producing.intent_id
 AND request_id=producing.request_id AND generation=producing.generation;
 IF intent.payload->>'outcome' IS DISTINCT FROM producing.outcome OR
 (intent.producer_task_id,intent.producer_attempt,intent.runtime_id) IS DISTINCT FROM
 (producing.producer_task_id,producing.producer_attempt,producing.runtime_id) THEN RETURN false; END IF;
 r.release_id:=producing.release_id; r.runtime_id:=producing.runtime_id;
 r.recipe:=producing.recipe; r.generation:=producing.generation;
 r.binding:=r.binding||jsonb_build_object('inputs',intent.payload->'inputs','support',intent.payload->'support');
 PERFORM ops.ddo_record_fit_require_producer(r,intent.payload);
 FOR selected IN SELECT * FROM ops.ddo_record_fit_selections(r) LOOP
 PERFORM ops.ddo_record_fit_require_selection(r,selected.role_name,selected.selection,false);
 END LOOP;
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $fit$;
""" + "\n".join(
        f"REVOKE ALL ON FUNCTION ops.{name}({arguments}) FROM PUBLIC;"
        for name, arguments in (
            ("ddo_require_record_fit_correspondence", "jsonb,jsonb,jsonb,jsonb"),
            ("ddo_record_fit_require_finite_cut", "ops.data_demand,ops.data_demand_read"),
            ("ddo_record_fit_selections", "ops.data_request"),
            ("ddo_record_fit_cut_scopes", "text,jsonb"),
            ("ddo_record_fit_completion_scopes", "ops.data_request"),
            ("ddo_record_fit_dependency_scopes", "text"),
            ("ddo_record_fit_require_selection", "ops.data_request,text,jsonb,boolean"),
            ("ddo_record_fit_require_producer", "ops.data_request,jsonb"),
            ("ddo_require_record_fit_completion", "ops.data_request,jsonb"),
            ("ddo_record_fit_dependencies_valid", "text"),
        )
    )
