"""Finite original target/vector custody for the actual applicability consumer."""


def contextual_definition_native_sql() -> str:
    return r'''
CREATE OR REPLACE FUNCTION ops.ddo_contextual_origin_basis(selected_input jsonb,operation_name text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $definition$
DECLARE episode ops.data_derivation; request ops.data_request; intent ops.data_completion_intent;
BEGIN
 IF operation_name NOT IN ('retrieve.contextual/with-witnesses','retrieve.contextual_vectors/selection',
 'retrieve.contextual_target_vector/declared','retrieve.contextual_target/declared','retrieve.contextual_targets/components') THEN
 RAISE EXCEPTION 'contextual definition lineage requires its finite declared producers' USING ERRCODE='23514'; END IF;
 SELECT d.* INTO STRICT episode FROM ops.data_derivation d
 JOIN ops.data_request r ON r.id=d.request_id AND r.operation_id=operation_name
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=d.id AND receipt.intent_id=d.intent_id
 JOIN ops.data_derivation_output output ON output.derivation_id=d.id
 WHERE output.product_id=data.ddo_field(selected_input,'product_id')->>1
 AND (output.member_id IS NULL OR output.member_id=data.ddo_field(selected_input,'member_id')->>1)
 AND output.multiplicity=1 AND d.outcome='success'
 AND d.id IN (SELECT reference->>'derivation_id' FROM jsonb_array_elements(
 data.ddo_json(data.ddo_field(selected_input,'support'))) reference WHERE reference->>'kind'='computation');
 IF NOT ops.ddo_contextual_dependencies_valid(episode.id) THEN
 RAISE EXCEPTION 'contextual definition lineage lacks its authentic sealed producer' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=episode.request_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id
 AND request_id=episode.request_id AND generation=episode.generation;
 request.release_id:=episode.release_id; request.runtime_id:=episode.runtime_id;
 request.recipe:=episode.recipe; request.generation:=episode.generation;
 request.binding:=request.binding||jsonb_build_object('inputs',intent.payload->'inputs','support',intent.payload->'support');
 RETURN ops.ddo_cpu_input_basis(request);
END $definition$;

CREATE OR REPLACE FUNCTION ops.ddo_require_contextual_definition_lineage(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $definition$
DECLARE original ops.data_request:=r; basis jsonb; producer_basis jsonb; selected_row jsonb;
 component_row jsonb; relationship_row jsonb; component_id text;
BEGIN
 original.binding:=r.binding||jsonb_build_object('inputs',completion->'inputs','support',completion->'support');
 basis:=ops.ddo_cpu_input_basis(original);
 component_id:=data.ddo_field(data.ddo_field(basis,'parameters'),'component_id')->>1;
 SELECT value INTO STRICT component_row FROM jsonb_array_elements(data.ddo_field(basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='components';
 SELECT value INTO STRICT relationship_row FROM jsonb_array_elements(data.ddo_field(basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='relationship';
 IF component_id IS NULL OR data.ddo_field(component_row,'member_id') IS DISTINCT FROM '["null"]'::jsonb
 OR data.ddo_field(relationship_row,'member_id') IS DISTINCT FROM '["null"]'::jsonb THEN
 RAISE EXCEPTION 'contextual applicability requires exact whole component and relationship inputs' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_definition_component_basis(component_row);
 producer_basis:=ops.ddo_contextual_origin_basis(relationship_row,'retrieve.contextual/with-witnesses');
 SELECT value INTO STRICT selected_row FROM jsonb_array_elements(data.ddo_field(producer_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='vectors';
 producer_basis:=ops.ddo_contextual_origin_basis(selected_row,'retrieve.contextual_vectors/selection');
 SELECT value INTO STRICT selected_row FROM jsonb_array_elements(data.ddo_field(producer_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='targets'
 AND data.ddo_field(data.ddo_field(data.ddo_field(value,'body'),'vector'),'object_id')->>1=component_id;
 producer_basis:=ops.ddo_contextual_origin_basis(selected_row,'retrieve.contextual_target_vector/declared');
 SELECT value INTO STRICT selected_row FROM jsonb_array_elements(data.ddo_field(producer_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='target';
 producer_basis:=ops.ddo_contextual_origin_basis(selected_row,'retrieve.contextual_target/declared');
 SELECT value INTO STRICT selected_row FROM jsonb_array_elements(data.ddo_field(producer_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='target';
 producer_basis:=ops.ddo_contextual_origin_basis(selected_row,'retrieve.contextual_targets/components');
 IF ops.ddo_rich_role_population(producer_basis,'report') IS DISTINCT FROM ops.ddo_rich_role_population(basis,'components') THEN
 RAISE EXCEPTION 'contextual applicability substitutes the original component report/member/producer support' USING ERRCODE='23514'; END IF;
END $definition$;
REVOKE ALL ON FUNCTION ops.ddo_contextual_origin_basis(jsonb,text),
 ops.ddo_require_contextual_definition_lineage(ops.data_request,jsonb) FROM PUBLIC;
'''
