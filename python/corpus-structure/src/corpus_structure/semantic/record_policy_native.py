"""Native policy issuer recognition and bounded ordinary provenance disclosure."""


def record_policy_native_sql():
    import json
    from dataclasses import asdict
    from .record_policy_authority import (
        AUTHORIZATION_EFFECT, AUTHORIZATION_FACTORY, AUTHORIZATION_KIND, AUTHORIZATION_OPERATION,
    )

    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_policy_command_eligible(definition sem.data_operation_definition)
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $policy$
 SELECT definition.operation_id='__OPERATION__' AND definition.profile='command'
 AND definition.support_contract->'capabilities'->>'preparation'='native-publication'
 AND definition.support_contract->'capabilities'->'forms'='["scalar"]'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint'='__FACTORY__'
 AND definition.support_contract->'effects'='__EFFECTS__'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND definition.implementation_revision LIKE 'implementation-slice:%'
$policy$;
REVOKE ALL ON FUNCTION ops.ddo_policy_command_eligible(sem.data_operation_definition) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_policy_authority_leaf(episode text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $policy$
 SELECT NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_evaluator','MEMBER')
 AND EXISTS(SELECT FROM ops.data_derivation d JOIN ops.data_request request ON request.id=d.request_id
 JOIN sem.data_operation_definition definition ON definition.release_id=d.release_id AND definition.operation_id=request.operation_id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=d.id AND receipt.intent_id=d.intent_id
 JOIN ops.data_derivation_output output ON output.derivation_id=d.id
 JOIN sem.data_kind_contract kind ON kind.kind_contract=(SELECT product.kind_contract FROM kb.data_product product WHERE product.id=output.product_id)
 WHERE d.id=episode AND d.outcome='success' AND ops.ddo_policy_command_eligible(definition)
 AND output.role='authorization' AND output.position=0 AND output.multiplicity=1 AND output.member_id IS NULL
 AND kind.kind='__KIND__' AND kind.universe='ordinary'
 AND (SELECT count(*) FROM ops.data_derivation_output other WHERE other.derivation_id=d.id)=1)
$policy$;
REVOKE ALL ON FUNCTION ops.ddo_policy_authority_leaf(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_policy_authority_summary(episode text,selected_use text,read_id text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $policy$
DECLARE d ops.data_derivation; chosen ops.demand_use; boundary ops.data_demand_read;
 output ops.data_derivation_output; receipt ops.data_publication_receipt; standing text;
BEGIN
 IF NOT coalesce(ops.ddo_policy_authority_leaf(episode),false) THEN
 RAISE EXCEPTION 'ordinary policy authority summary requires an authenticated native issuer' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=read_id;
 SELECT * INTO STRICT d FROM ops.data_derivation WHERE id=episode;
 IF NOT ops.ddo_read_visible(d.created_at,d.created_xid,boundary) THEN
 RAISE EXCEPTION 'policy issuer is outside selected native visibility' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT output FROM ops.data_derivation_output WHERE derivation_id=episode;
 SELECT * INTO STRICT receipt FROM ops.data_publication_receipt WHERE derivation_id=episode AND intent_id=d.intent_id;
 IF selected_use IS NOT NULL THEN
 SELECT * INTO STRICT chosen FROM ops.demand_use WHERE id=selected_use AND derivation_id=episode;
 IF NOT ops.ddo_read_visible(chosen.created_at,chosen.created_xid,boundary) THEN
 RAISE EXCEPTION 'policy authority use is outside selected native visibility' USING ERRCODE='23514'; END IF;
 standing:=CASE WHEN ops.ddo_use_valid(chosen,boundary) THEN 'valid' ELSE 'unavailable' END;
 ELSE standing:=CASE WHEN ops.ddo_support_valid(episode,boundary) THEN 'valid' ELSE 'unavailable' END;
 END IF;
 RETURN jsonb_build_object('format','ddo-native-authority-leaf-v1','derivation_id',episode,
 'use_id',selected_use,'issuer_operation','__OPERATION__','release_id',d.release_id,'runtime_id',d.runtime_id,
 'recipe',d.recipe,'product_id',output.product_id,
 'kind_contract',(SELECT kind_contract FROM kb.data_product WHERE id=output.product_id),
 'intent_id',d.intent_id,'receipt_id',receipt.id,'standing',standing,'protected_dependencies','undisclosed');
END $policy$;
REVOKE ALL ON FUNCTION ops.ddo_policy_authority_summary(text,text,text) FROM PUBLIC;
""".replace("__OPERATION__", AUTHORIZATION_OPERATION).replace("__FACTORY__", AUTHORIZATION_FACTORY).replace(
        "__KIND__", AUTHORIZATION_KIND
    ).replace("__EFFECTS__", json.dumps([asdict(AUTHORIZATION_EFFECT)], separators=(",", ":")))
