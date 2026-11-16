"""Current contextual completion correspondence at the common native fence.

This helper adds no model, scoring implementation, receipt or validity owner.
The caller installs its hook alongside the authenticated CPU-basis helpers.
Retrieval requires a separately authenticated native scoring input; it is not
silently treated as a CPU result by this scalar encoder/selection guard.
"""


def contextual_admission_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_require_contextual_producer(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $contextual$
DECLARE operation sem.data_operation_definition; factory text;
BEGIN
 IF r.operation_id NOT IN ('retrieve.contextual_query/declared','retrieve.contextual_query/selected-context',
 'retrieve.contextual_target_vector/declared','retrieve.contextual_vectors/selection',
 'retrieve.contextual_targets/curated','retrieve.contextual_targets/components',
 'retrieve.contextual_target/declared','retrieve.contextual_inventory/declared') THEN RETURN; END IF;
 SELECT * INTO STRICT operation FROM sem.data_operation_definition
 WHERE release_id=r.release_id AND operation_id=r.operation_id;
 factory:=CASE r.operation_id
 WHEN 'retrieve.contextual_query/declared' THEN 'corpus_structure.methods.contextual_encoding.ContextualEncodingOperation.acquire_port'
 WHEN 'retrieve.contextual_query/selected-context' THEN 'corpus_structure.methods.contextual_encoding.SelectedContextEncodingOperation.acquire_port'
 WHEN 'retrieve.contextual_target_vector/declared' THEN 'corpus_structure.methods.contextual_encoding.ContextualTargetEncodingOperation.acquire_port'
 WHEN 'retrieve.contextual_vectors/selection' THEN 'corpus_structure.methods.contextual_targets.ContextualVectorSelectionOperation.acquire_port'
 WHEN 'retrieve.contextual_targets/curated' THEN 'corpus_structure.methods.contextual_targets.CuratedContextualTargetsOperation.acquire_port'
 WHEN 'retrieve.contextual_targets/components' THEN 'corpus_structure.methods.contextual_targets.SourceContextualTargetsOperation.acquire_port'
 WHEN 'retrieve.contextual_target/declared' THEN 'corpus_structure.methods.contextual_targets.ContextualTargetOperation.acquire_port'
 WHEN 'retrieve.contextual_inventory/declared' THEN 'corpus_structure.methods.contextual_declared.ContextualInventoryOperation.acquire_port' END;
 IF operation.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM factory
 OR (operation.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (operation.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR operation.recipe IS DISTINCT FROM r.recipe
 OR operation.support_contract->'capabilities'->'forms' IS DISTINCT FROM '["scalar"]'::jsonb
 OR operation.support_contract->'capabilities'->>'preparation' IS DISTINCT FROM 'resource'
 OR operation.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR completion->>'implementation_revision' IS DISTINCT FROM operation.implementation_revision THEN
 RAISE EXCEPTION 'contextual completion lacks its actual admitted captured producer' USING ERRCODE='23514'; END IF;
END $contextual$;

CREATE OR REPLACE FUNCTION ops.ddo_require_contextual_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $contextual$
DECLARE actual jsonb; expected jsonb; item jsonb;
BEGIN
 IF r.operation_id NOT IN ('retrieve.contextual_query/declared','retrieve.contextual_query/selected-context',
 'retrieve.contextual_target_vector/declared','retrieve.contextual_vectors/selection',
 'retrieve.contextual_targets/curated','retrieve.contextual_targets/components',
 'retrieve.contextual_target/declared','retrieve.contextual_inventory/declared') THEN RETURN; END IF;
 PERFORM ops.ddo_require_contextual_producer(r,completion);
 actual:=ops.ddo_cpu_reply_output(r,completion);
 FOR item IN SELECT value FROM jsonb_array_elements(completion->'outputs') LOOP
 expected:=CASE WHEN r.operation_id IN ('retrieve.contextual_query/declared','retrieve.contextual_query/selected-context')
 THEN data.ddo_field(actual,item->>'role') ELSE actual END;
 IF expected IS DISTINCT FROM data.ddo_normalize(item->'product'->'body') THEN
 RAISE EXCEPTION 'contextual publication differs from its actual processed CPU reply' USING ERRCODE='23514'; END IF;
 END LOOP;
END $contextual$;
CREATE OR REPLACE FUNCTION ops.ddo_contextual_dependencies_valid(episode_id text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $contextual$
DECLARE r ops.data_request; episode ops.data_derivation; intent ops.data_completion_intent; evidence jsonb;
BEGIN
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=episode_id;
 SELECT * INTO STRICT r FROM ops.data_request WHERE id=episode.request_id;
 IF r.operation_id NOT IN ('retrieve.contextual_query/declared','retrieve.contextual_query/selected-context',
 'retrieve.contextual_target_vector/declared','retrieve.contextual_vectors/selection',
 'retrieve.contextual_targets/curated','retrieve.contextual_targets/components',
 'retrieve.contextual_target/declared','retrieve.contextual_inventory/declared') THEN RETURN true; END IF;
 -- Immutable correspondence was checked at retention and publication by this
 -- captured native kernel. Ordinary support recursion rechecks mutable premises;
 -- do not replay the whole reply/model/scoring graph on every support read.
 IF episode.outcome<>'success' OR NOT EXISTS(SELECT FROM ops.data_publication_receipt receipt
 JOIN sem.artifact artifact ON artifact.release_id=episode.release_id
 AND artifact.artifact_name='data_operation_native_definitions.json'
 WHERE receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 AND convert_from(artifact.content,'UTF8')::jsonb->>'native_digest'='__DDO_SOURCE_DIGEST__') THEN RETURN false; END IF;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id
 AND request_id=episode.request_id AND generation=episode.generation;
 evidence:=intent.payload->'execution_evidence';
 IF (intent.producer_task_id,intent.producer_attempt,intent.runtime_id) IS DISTINCT FROM
 (episode.producer_task_id,episode.producer_attempt,episode.runtime_id)
 OR evidence->>'request_id' IS DISTINCT FROM episode.request_id
 OR (evidence->>'generation')::integer IS DISTINCT FROM episode.generation
 OR (evidence->>'task_id')::bigint IS DISTINCT FROM intent.producer_task_id
 OR (evidence->>'attempt')::integer IS DISTINCT FROM intent.producer_attempt
 OR evidence->>'holder' IS DISTINCT FROM intent.producer_holder
 OR evidence->>'runtime_id' IS DISTINCT FROM intent.runtime_id THEN RETURN false; END IF;
 -- A later generation may rebind the request. Producer checking below uses the
 -- sealed episode's release/runtime/recipe and never today's input binding.
 r.release_id:=episode.release_id; r.runtime_id:=episode.runtime_id;
 r.recipe:=episode.recipe; r.generation:=episode.generation;
 PERFORM ops.ddo_require_contextual_producer(r,intent.payload);
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $contextual$;
REVOKE ALL ON FUNCTION ops.ddo_require_contextual_producer(ops.data_request,jsonb),
 ops.ddo_require_contextual_completion(ops.data_request,jsonb),ops.ddo_contextual_dependencies_valid(text) FROM PUBLIC;
"""
