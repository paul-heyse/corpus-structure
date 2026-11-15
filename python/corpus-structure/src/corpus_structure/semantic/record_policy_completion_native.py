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
        **{name: f"basis->'{name}'" for name in (
            "family_contract", "reading_recipe", "numerical_policy",
            "judgment_basis_digest", "applicability",
        )},
    }
    if projection.keys() != DdoRecordPolicyAuthorization.model_fields.keys():
        raise ValueError("native policy projection must cover the exact public contract")
    fields = ",\n".join(f"'{name}',{value}" for name, value in sorted(projection.items()))
    def exact_field(name, expression):
        if name == "version" or name.endswith("_digest") and name in {"policy_instance_digest", "feature_instance_digest", "calibration_digest"}:
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
    return r"""
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
 fit_definition sem.data_operation_definition; fit_intent ops.data_completion_intent; expected jsonb;
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
 AND (selected->>'support_derivation_id' IS NULL OR selected->>'support_derivation_id'=producer.id))<>1 THEN
 RAISE EXCEPTION 'policy basis lacks one exact supported successful native fit receipt' USING ERRCODE='23514'; END IF;
 SELECT producer.* INTO STRICT producing FROM ops.data_derivation producer
 JOIN ops.data_derivation_output produced ON produced.derivation_id=producer.id
 WHERE produced.product_id=basis.id AND produced.member_id IS NULL AND produced.role='fitted'
 AND EXISTS(SELECT FROM jsonb_array_elements(completion->'support') support WHERE support->>'derivation_id'=producer.id)
 AND (selected->>'support_derivation_id' IS NULL OR selected->>'support_derivation_id'=producer.id);
 SELECT operation.* INTO STRICT fit_definition FROM sem.data_operation_definition operation
 JOIN ops.data_request request ON request.release_id=operation.release_id AND request.operation_id=operation.operation_id
 WHERE request.id=producing.request_id AND request.project_id=r.project_id;
 SELECT * INTO STRICT fit_intent FROM ops.data_completion_intent WHERE id=producing.intent_id;
 IF fit_definition.operation_id IS DISTINCT FROM 'record_policy.fit' OR fit_definition.profile IS DISTINCT FROM 'derivation'
 OR fit_definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR fit_definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM 'corpus_structure.methods.declared_record_policy.RecordPolicyFit.acquire_port'
 OR (fit_definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (fit_definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR fit_intent.payload->>'implementation_revision' IS DISTINCT FROM fit_definition.implementation_revision
 OR jsonb_array_length(coalesce(fit_intent.payload->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR producing.recipe IS DISTINCT FROM fit_definition.recipe THEN
 RAISE EXCEPTION 'policy basis is not the actual admitted protected CPU fit implementation' USING ERRCODE='23514'; END IF;
 expected:=ops.ddo_policy_authorization_value(data.ddo_json(basis.canonical_body));
 IF expected->'applicability'->>'project_id' IS DISTINCT FROM r.project_id
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract family JOIN sem.data_kind_release admitted ON admitted.kind_contract=family.kind_contract
 WHERE admitted.release_id=r.release_id AND family.kind_contract=expected->>'family_contract')
 OR NOT EXISTS(SELECT FROM sem.data_operation_definition reading WHERE reading.release_id=r.release_id
 AND reading.operation_id='resolve.m1_readings' AND reading.recipe=expected->>'reading_recipe')
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind='https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization' AND kind.universe='ordinary')
 OR data.ddo_normalize(output->'product'->'body') IS DISTINCT FROM ops.ddo_policy_authorization_meaning(basis.canonical_body) THEN
 RAISE EXCEPTION 'policy authorization public conclusion differs from exact fitted basis and current interpretation' USING ERRCODE='23514'; END IF;
END $policy$;
""".replace("__PUBLIC_FIELDS__", fields).replace("__PUBLIC_MEANING_FIELDS__", meaning_fields)
