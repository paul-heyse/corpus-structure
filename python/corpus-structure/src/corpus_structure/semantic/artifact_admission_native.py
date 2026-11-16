"""Artifact CPU result correspondence, using the existing execution authority owner."""


def artifact_admission_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_require_artifact_producer(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $artifact$
DECLARE definition sem.data_operation_definition;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF r.operation_id IS DISTINCT FROM 'structure.artifact_identity/declared'
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM
 'corpus_structure.methods.artifact_identity_declared.ArtifactIdentityOperation.acquire_port'
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR definition.profile IS DISTINCT FROM 'derivation' OR definition.recipe IS DISTINCT FROM r.recipe
 OR definition.support_contract->'capabilities'->'forms' IS DISTINCT FROM '["scalar"]'::jsonb
 OR definition.support_contract->'capabilities'->>'preparation' IS DISTINCT FROM 'resource'
 OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR completion->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1 THEN
 RAISE EXCEPTION 'artifact completion lacks its actual captured scalar CPU producer' USING ERRCODE='23514'; END IF;
END $artifact$;

CREATE OR REPLACE FUNCTION ops.ddo_require_artifact_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $artifact$
DECLARE definition sem.data_operation_definition; output jsonb; actual jsonb; expected jsonb; result_field text;
BEGIN
 IF r.operation_id IS DISTINCT FROM 'structure.artifact_identity/declared' THEN RETURN; END IF;
 PERFORM ops.ddo_require_artifact_producer(r,completion);
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 actual:=ops.ddo_cpu_reply_output(r,completion);
 IF jsonb_typeof(definition.support_contract->'result_fields') IS DISTINCT FROM 'object' THEN
 RAISE EXCEPTION 'artifact output lacks its actual admitted result-field projection' USING ERRCODE='23514'; END IF;
 FOR output IN SELECT value FROM jsonb_array_elements(completion->'outputs') LOOP
 expected:=actual;
 IF definition.support_contract->'result_fields'<>'{}'::jsonb THEN
 result_field:=definition.support_contract->'result_fields'->> (output->>'role');
 IF result_field IS NULL THEN RAISE EXCEPTION 'artifact output lacks its exact admitted result field' USING ERRCODE='23514'; END IF;
 expected:=data.ddo_field(actual,result_field);
 ELSIF jsonb_array_length(definition.output_roles)<>1 OR definition.output_roles->0->>'name' IS DISTINCT FROM output->>'role' THEN
 RAISE EXCEPTION 'artifact CPU reply requires its actual admitted single output contract' USING ERRCODE='23514'; END IF;
 IF expected IS DISTINCT FROM data.ddo_normalize(output->'product'->'body') THEN
 RAISE EXCEPTION 'artifact publication differs from its actual exact-input CPU reply' USING ERRCODE='23514'; END IF;
 END LOOP;
END $artifact$;

CREATE OR REPLACE FUNCTION ops.ddo_artifact_dependencies_valid(episode_id text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $artifact$
DECLARE episode ops.data_derivation; r ops.data_request; intent ops.data_completion_intent;
BEGIN
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=episode_id;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=episode.request_id;
 IF r.operation_id IS DISTINCT FROM 'structure.artifact_identity/declared' THEN RETURN true; END IF;
 IF episode.outcome<>'success' OR NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt
 JOIN sem.artifact artifact ON artifact.release_id=episode.release_id
 AND artifact.artifact_name='data_operation_native_definitions.json'
 WHERE receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 AND convert_from(artifact.content,'UTF8')::jsonb->>'native_digest'='__DDO_SOURCE_DIGEST__') THEN RETURN false; END IF;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id
 AND request_id=episode.request_id AND generation=episode.generation;
 IF (intent.producer_task_id,intent.producer_attempt,intent.runtime_id) IS DISTINCT FROM
 (episode.producer_task_id,episode.producer_attempt,episode.runtime_id) THEN RETURN false; END IF;
 r.release_id:=episode.release_id; r.runtime_id:=episode.runtime_id; r.recipe:=episode.recipe; r.generation:=episode.generation;
 PERFORM ops.ddo_require_artifact_producer(r,intent.payload);
 -- Original body correspondence is immutable; common support recursion owns
 -- later validity of the exact source/navigation premises. No scoring replay.
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $artifact$;
REVOKE ALL ON FUNCTION ops.ddo_require_artifact_producer(ops.data_request,jsonb),
 ops.ddo_require_artifact_completion(ops.data_request,jsonb),ops.ddo_artifact_dependencies_valid(text) FROM PUBLIC;
"""
