"""Original exact component CPU-body proof and definition publication correspondence.

Component proof is shared by contextual applicability and other current consumers;
it does not depend on contextual numerical/source factory acquisition.
"""


def definition_admission_native_sql() -> str:
    return r'''
CREATE OR REPLACE FUNCTION ops.ddo_definition_source_reference(selected_input jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $definition$
 SELECT jsonb_build_object('product_id',data.ddo_field(selected_input,'product_id')->>1,
 'member_id',data.ddo_json(data.ddo_field(selected_input,'member_id')),
 'kind_contract',data.ddo_field(selected_input,'kind_contract')->>1,
 'project_id',data.ddo_field(data.ddo_field(selected_input,'context'),'project_id')->>1,
 'subject',data.ddo_field(data.ddo_field(selected_input,'context'),'subject')->>1,
 'subject_definition',data.ddo_field(data.ddo_field(selected_input,'context'),'subject_definition')->>1,
 'original_source',data.ddo_json(data.ddo_field(data.ddo_field(selected_input,'context'),'original_source')),
 'analyzed_scope_meaning',data.canonical_json(data.ddo_field(data.ddo_field(selected_input,'context'),'analyzed_scope')),
 'reference',data.canonical_json(jsonb_build_array(data.ddo_field(selected_input,'product_id')->>1,
 data.ddo_json(data.ddo_field(selected_input,'member_id')))))
$definition$;

CREATE OR REPLACE FUNCTION ops.ddo_definition_component_basis(selected_input jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $definition$
DECLARE episode ops.data_derivation; r ops.data_request; intent ops.data_completion_intent;
 definition sem.data_operation_definition; output_role text; result_field text; actual jsonb;
 basis jsonb; original_source_row jsonb; source_pins jsonb;
BEGIN
 IF data.ddo_field(selected_input,'member_id') IS DISTINCT FROM '["null"]'::jsonb
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=data.ddo_field(selected_input,'kind_contract')->>1
 AND kind.kind='urn:corpus:structural:DeclaredDefinitionComponentsReport') THEN
 RAISE EXCEPTION 'contextual component source requires its exact whole native report kind' USING ERRCODE='23514'; END IF;
 SELECT d.* INTO STRICT episode FROM ops.data_derivation d
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=d.id AND receipt.intent_id=d.intent_id
 JOIN ops.data_derivation_output output ON output.derivation_id=d.id
 WHERE output.product_id=data.ddo_field(selected_input,'product_id')->>1
 AND output.member_id IS NULL AND output.multiplicity=1 AND d.outcome='success'
 AND d.id IN (SELECT reference->>'derivation_id' FROM jsonb_array_elements(
 data.ddo_json(data.ddo_field(selected_input,'support'))) reference WHERE reference->>'kind'='computation');
 SELECT role INTO STRICT output_role FROM ops.data_derivation_output WHERE derivation_id=episode.id
 AND product_id=data.ddo_field(selected_input,'product_id')->>1 AND member_id IS NULL AND multiplicity=1;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=episode.request_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id
 AND request_id=episode.request_id AND generation=episode.generation;
 r.release_id:=episode.release_id; r.runtime_id:=episode.runtime_id;
 r.recipe:=episode.recipe; r.generation:=episode.generation;
 r.binding:=r.binding||jsonb_build_object('inputs',intent.payload->'inputs','support',intent.payload->'support');
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=episode.release_id AND operation_id=r.operation_id;
 IF definition.profile IS DISTINCT FROM 'derivation'
 OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'forms' IS DISTINCT FROM '["scalar"]'::jsonb
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE THEN
 RAISE EXCEPTION 'contextual component report lacks an actual captured scalar CPU producer' USING ERRCODE='23514'; END IF;
 actual:=ops.ddo_cpu_reply_output(r,intent.payload);
 IF jsonb_typeof(definition.support_contract->'result_fields') IS DISTINCT FROM 'object' THEN
 RAISE EXCEPTION 'component source lacks its admitted exact result-field projection' USING ERRCODE='23514'; END IF;
 IF definition.support_contract->'result_fields'<>'{}'::jsonb THEN
 result_field:=definition.support_contract->'result_fields'->>output_role;
 IF result_field IS NULL THEN RAISE EXCEPTION 'component CPU reply lacks its admitted output projection' USING ERRCODE='23514'; END IF;
 actual:=data.ddo_field(actual,result_field);
 ELSIF jsonb_array_length(definition.output_roles)<>1 OR definition.output_roles->0->>'name' IS DISTINCT FROM output_role THEN
 RAISE EXCEPTION 'component CPU reply requires its actual admitted single output contract' USING ERRCODE='23514'; END IF;
 IF actual IS DISTINCT FROM data.ddo_field(selected_input,'body') THEN
 RAISE EXCEPTION 'component source body differs from its actual original CPU reply' USING ERRCODE='23514'; END IF;
 basis:=ops.ddo_cpu_input_basis(r);
 SELECT value INTO STRICT original_source_row FROM jsonb_array_elements(data.ddo_field(basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='source';
 source_pins:=data.ddo_json(data.ddo_field(data.ddo_field(selected_input,'body'),'sources_input'));
 IF jsonb_typeof(source_pins) IS DISTINCT FROM 'array' OR jsonb_array_length(source_pins)<>1
 OR jsonb_strip_nulls(source_pins->0) IS DISTINCT FROM jsonb_strip_nulls(ops.ddo_definition_source_reference(original_source_row)) THEN
 RAISE EXCEPTION 'component source report differs from its exact original selected source/header' USING ERRCODE='23514'; END IF;
 RETURN basis;
END $definition$;

CREATE OR REPLACE FUNCTION ops.ddo_require_definition_producer(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $definition$
DECLARE definition sem.data_operation_definition;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF r.operation_id NOT IN ('structure.definition_applicability/declared','structure.definition_declaration_components/declared',
 'structure.definition_components/declared','structure.definition_named_components/declared')
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM
 (CASE WHEN r.operation_id='structure.definition_applicability/declared'
 THEN 'corpus_structure.methods.definition_applicability_declared.DefinitionApplicabilityOperation.acquire_port'
 WHEN r.operation_id='structure.definition_declaration_components/declared' THEN 'corpus_structure.methods.definition_declared.DefinitionDeclarationOperation.acquire_port'
 WHEN r.operation_id='structure.definition_components/declared' THEN 'corpus_structure.methods.definition_components_declared.DefinitionComponentsOperation.acquire_port'
 ELSE 'corpus_structure.methods.definition_named_declared.NamedDefinitionComponentsOperation.acquire_port' END)
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR definition.profile IS DISTINCT FROM 'derivation' OR definition.recipe IS DISTINCT FROM r.recipe
 OR definition.support_contract->'capabilities'->'forms' IS DISTINCT FROM '["scalar"]'::jsonb
 OR definition.support_contract->'capabilities'->>'preparation' IS DISTINCT FROM 'resource'
 OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR completion->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision THEN
 RAISE EXCEPTION 'contextual applicability lacks its actual captured scalar producer' USING ERRCODE='23514'; END IF;
END $definition$;

CREATE OR REPLACE FUNCTION ops.ddo_require_definition_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $definition$
DECLARE output jsonb; actual jsonb;
BEGIN
 IF r.operation_id NOT IN ('structure.definition_applicability/declared','structure.definition_declaration_components/declared',
 'structure.definition_components/declared','structure.definition_named_components/declared') THEN RETURN; END IF;
 PERFORM ops.ddo_require_definition_producer(r,completion);
 actual:=ops.ddo_cpu_reply_output(r,completion);
 FOR output IN SELECT value FROM jsonb_array_elements(completion->'outputs') LOOP
 IF actual IS DISTINCT FROM data.ddo_normalize(output->'product'->'body') THEN
 RAISE EXCEPTION 'definition publication differs from its actual exact-input CPU reply' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF r.operation_id='structure.definition_applicability/declared' THEN
 PERFORM ops.ddo_require_contextual_definition_lineage(r,completion); END IF;
END $definition$;

CREATE OR REPLACE FUNCTION ops.ddo_definition_dependencies_valid(episode_id text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $definition$
DECLARE episode ops.data_derivation; r ops.data_request; intent ops.data_completion_intent;
BEGIN
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=episode_id;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=episode.request_id;
 IF r.operation_id NOT IN ('structure.definition_applicability/declared','structure.definition_declaration_components/declared',
 'structure.definition_components/declared','structure.definition_named_components/declared') THEN RETURN true; END IF;
 IF episode.outcome<>'success' OR NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt
 JOIN sem.artifact artifact ON artifact.release_id=episode.release_id
 AND artifact.artifact_name='data_operation_native_definitions.json'
 WHERE receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 AND convert_from(artifact.content,'UTF8')::jsonb->>'native_digest'='__DDO_SOURCE_DIGEST__') THEN RETURN false; END IF;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id
 AND request_id=episode.request_id AND generation=episode.generation;
 IF (intent.producer_task_id,intent.producer_attempt,intent.runtime_id) IS DISTINCT FROM
 (episode.producer_task_id,episode.producer_attempt,episode.runtime_id) THEN RETURN false; END IF;
 r.release_id:=episode.release_id; r.runtime_id:=episode.runtime_id;
 r.recipe:=episode.recipe; r.generation:=episode.generation;
 PERFORM ops.ddo_require_definition_producer(r,intent.payload);
 -- First retention/publication checked the immutable finite custody chain.
 -- Ordinary support validity recurses over its actual mutable premises.
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $definition$;
REVOKE ALL ON FUNCTION ops.ddo_definition_source_reference(jsonb),ops.ddo_definition_component_basis(jsonb),
 ops.ddo_require_definition_producer(ops.data_request,jsonb),
 ops.ddo_require_definition_completion(ops.data_request,jsonb),ops.ddo_definition_dependencies_valid(text) FROM PUBLIC;
'''
