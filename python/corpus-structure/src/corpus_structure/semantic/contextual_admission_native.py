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
 'retrieve.contextual_target/declared','retrieve.contextual_inventory/declared',
 'retrieve.contextual_scores/declared','retrieve.contextual/declared',
 'retrieve.contextual_witnesses/declared','retrieve.contextual/with-witnesses') THEN RETURN; END IF;
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
 WHEN 'retrieve.contextual_inventory/declared' THEN 'corpus_structure.methods.contextual_declared.ContextualInventoryOperation.acquire_port'
 WHEN 'retrieve.contextual_scores/declared' THEN 'corpus_structure.methods.contextual_scoring.ContextualScoringOperation.acquire_port'
 WHEN 'retrieve.contextual/declared' THEN 'corpus_structure.methods.contextual_declared.ContextualRetrievalOperation.acquire_port'
 WHEN 'retrieve.contextual_witnesses/declared' THEN 'corpus_structure.methods.contextual_witnesses.ContextualWitnessOperation.acquire_port'
 WHEN 'retrieve.contextual/with-witnesses' THEN 'corpus_structure.methods.contextual_witnesses.ContextualWitnessedRetrievalOperation.acquire_port' END;
 IF operation.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM factory
 OR (operation.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (operation.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR operation.profile IS DISTINCT FROM (CASE WHEN r.operation_id IN
 ('retrieve.contextual_targets/curated','retrieve.contextual_targets/components') THEN 'discovery' ELSE 'derivation' END)
 OR operation.recipe IS DISTINCT FROM r.recipe
 OR operation.support_contract->'capabilities'->'forms' IS DISTINCT FROM '["scalar"]'::jsonb
 OR operation.support_contract->'capabilities'->>'preparation' IS DISTINCT FROM 'resource'
 OR operation.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>
 (CASE WHEN r.operation_id='retrieve.contextual_scores/declared' THEN 0 ELSE 1 END)
 OR completion->>'implementation_revision' IS DISTINCT FROM operation.implementation_revision THEN
 RAISE EXCEPTION 'contextual completion lacks its actual admitted captured producer' USING ERRCODE='23514'; END IF;
END $contextual$;

CREATE OR REPLACE FUNCTION ops.ddo_contextual_scoring_inputs(r ops.data_request,completion jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $contextual$
DECLARE original ops.data_request:=r; basis jsonb; item jsonb; role_name text; result jsonb:='{}';
 episode ops.data_derivation; producing ops.data_request; intent ops.data_completion_intent;
 producer_basis jsonb; scores_episode ops.data_derivation; scores_request ops.data_request;
 witness_episode ops.data_derivation; witness_request ops.data_request;
 vectors_episode ops.data_derivation; vectors_request ops.data_request; query_episode ops.data_derivation; vector_query jsonb; query_context jsonb;
 definition sem.data_operation_definition; score_definition sem.data_operation_definition;
BEGIN
 original.binding:=r.binding||jsonb_build_object('inputs',completion->'inputs','support',completion->'support');
 basis:=ops.ddo_cpu_input_basis(original);
 FOR item IN SELECT value FROM jsonb_array_elements(data.ddo_field(basis,'roles')->1) LOOP
 role_name:=data.ddo_field(item,'role')->>1;
 IF result ? role_name OR role_name NOT IN ('query','inventory','vectors','policy','scores','witnesses')
 OR data.ddo_field(item,'member_id') IS DISTINCT FROM '["null"]'::jsonb
 OR data.ddo_field(item,'multiplicity') IS DISTINCT FROM '["integer","1"]'::jsonb THEN
 RAISE EXCEPTION 'native contextual scoring requires exact distinct whole role products' USING ERRCODE='23514'; END IF;
 result:=result||jsonb_build_object(role_name,data.ddo_json(data.ddo_field(item,'body')));
 IF role_name='policy' THEN CONTINUE; END IF;
 SELECT d.* INTO STRICT episode FROM ops.data_derivation d
 JOIN ops.data_derivation_output output ON output.derivation_id=d.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=d.id AND receipt.intent_id=d.intent_id
 WHERE output.product_id=data.ddo_field(item,'product_id')->>1 AND output.member_id IS NULL AND output.multiplicity=1
 AND EXISTS(SELECT FROM jsonb_array_elements(data.ddo_json(data.ddo_field(item,'support'))) reference
 WHERE reference->>'kind'='computation' AND reference->>'derivation_id'=d.id);
 SELECT * INTO STRICT producing FROM ops.data_request WHERE id=episode.request_id AND project_id=r.project_id;
 IF (role_name='query' AND producing.operation_id NOT IN ('retrieve.contextual_query/declared','retrieve.contextual_query/selected-context'))
 OR (role_name='inventory' AND producing.operation_id<>'retrieve.contextual_inventory/declared')
 OR (role_name='vectors' AND producing.operation_id<>'retrieve.contextual_vectors/selection')
 OR (role_name='scores' AND producing.operation_id<>'retrieve.contextual_scores/declared')
 OR (role_name='witnesses' AND producing.operation_id<>'retrieve.contextual_witnesses/declared')
 OR NOT ops.ddo_contextual_dependencies_valid(episode.id) THEN
 RAISE EXCEPTION 'native contextual input lacks its actual declared producer/common receipt' USING ERRCODE='23514'; END IF;
 IF role_name='witnesses' THEN witness_episode:=episode; witness_request:=producing;
 ELSIF role_name='scores' THEN scores_episode:=episode; scores_request:=producing;
 ELSIF role_name='vectors' THEN vectors_episode:=episode; vectors_request:=producing;
 ELSIF role_name='query' THEN query_episode:=episode; query_context:=data.ddo_field(item,'context'); END IF;
 END LOOP;
 IF (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(result) key) IS DISTINCT FROM
 (CASE WHEN r.operation_id='retrieve.contextual_scores/declared' THEN ARRAY['inventory','policy','query','vectors']
 WHEN r.operation_id='retrieve.contextual/with-witnesses' THEN ARRAY['inventory','policy','query','scores','vectors','witnesses']
 ELSE ARRAY['inventory','policy','query','scores','vectors'] END) THEN
 RAISE EXCEPTION 'native contextual input population is incomplete or foreign' USING ERRCODE='23514'; END IF;
 IF query_context IS DISTINCT FROM data.ddo_field(basis,'context')
 OR result->'query'->'source_pin'->>'project_id' IS DISTINCT FROM r.project_id
 OR result->'query'->'source_pin'->>'original_source' IS DISTINCT FROM r.original_source THEN
 RAISE EXCEPTION 'native contextual query differs from selected product/original context' USING ERRCODE='23514'; END IF;
 -- The assembly's actual inventory and query-vector producer are custody,
 -- not merely matching labels/vector IDs in independently supplied bodies.
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=vectors_episode.intent_id;
 vectors_request.release_id:=vectors_episode.release_id; vectors_request.runtime_id:=vectors_episode.runtime_id;
 vectors_request.recipe:=vectors_episode.recipe; vectors_request.generation:=vectors_episode.generation;
 vectors_request.binding:=vectors_request.binding||jsonb_build_object('inputs',intent.payload->'inputs','support',intent.payload->'support');
 producer_basis:=ops.ddo_cpu_input_basis(vectors_request);
 IF ops.ddo_rich_role_population(basis,'inventory') IS DISTINCT FROM ops.ddo_rich_role_population(producer_basis,'inventory') THEN
 RAISE EXCEPTION 'native scoring inventory differs from actual selected vector assembly' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT vector_query FROM jsonb_array_elements(data.ddo_field(producer_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='query';
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(data.ddo_json(data.ddo_field(vector_query,'support'))) reference
 JOIN ops.data_derivation_output output ON output.derivation_id=reference->>'derivation_id'
 WHERE reference->>'kind'='computation' AND output.derivation_id=query_episode.id
 AND output.product_id=data.ddo_field(vector_query,'product_id')->>1
 AND output.member_id IS NULL AND output.role='vector' AND output.multiplicity=1) THEN
 RAISE EXCEPTION 'native scoring query and assembly vector have different original encoder episodes' USING ERRCODE='23514'; END IF;
 IF scores_episode.id IS NOT NULL THEN
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=scores_episode.intent_id;
 scores_request.release_id:=scores_episode.release_id; scores_request.runtime_id:=scores_episode.runtime_id;
 scores_request.recipe:=scores_episode.recipe; scores_request.generation:=scores_episode.generation;
 scores_request.binding:=scores_request.binding||jsonb_build_object('inputs',intent.payload->'inputs','support',intent.payload->'support');
 producer_basis:=ops.ddo_cpu_input_basis(scores_request);
 FOREACH role_name IN ARRAY ARRAY['query','inventory','vectors','policy'] LOOP
 IF ops.ddo_rich_role_population(basis,role_name) IS DISTINCT FROM ops.ddo_rich_role_population(producer_basis,role_name) THEN
 RAISE EXCEPTION 'native scores belong to another exact selected input/support population' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 SELECT * INTO STRICT score_definition FROM sem.data_operation_definition
 WHERE release_id=scores_episode.release_id AND operation_id=scores_request.operation_id;
 IF definition.support_contract->'numerical_policy' IS DISTINCT FROM score_definition.support_contract->'numerical_policy' THEN
 RAISE EXCEPTION 'native scores and CPU reduction have different captured numerical policies' USING ERRCODE='23514'; END IF;
 END IF;
 IF witness_episode.id IS NOT NULL THEN
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=witness_episode.intent_id;
 witness_request.release_id:=witness_episode.release_id; witness_request.runtime_id:=witness_episode.runtime_id;
 witness_request.recipe:=witness_episode.recipe; witness_request.generation:=witness_episode.generation;
 witness_request.binding:=witness_request.binding||jsonb_build_object('inputs',intent.payload->'inputs','support',intent.payload->'support');
 producer_basis:=ops.ddo_cpu_input_basis(witness_request);
 FOREACH role_name IN ARRAY ARRAY['query','inventory'] LOOP
 IF ops.ddo_rich_role_population(basis,role_name) IS DISTINCT FROM ops.ddo_rich_role_population(producer_basis,role_name) THEN
 RAISE EXCEPTION 'contextual witness binding belongs to another exact query/inventory support population' USING ERRCODE='23514'; END IF;
 END LOOP;
 END IF;
 RETURN result;
END $contextual$;

CREATE OR REPLACE FUNCTION ops.ddo_require_contextual_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $contextual$
DECLARE actual jsonb; expected jsonb; item jsonb; values_ jsonb; definition sem.data_operation_definition;
BEGIN
 IF r.operation_id NOT IN ('retrieve.contextual_query/declared','retrieve.contextual_query/selected-context',
 'retrieve.contextual_target_vector/declared','retrieve.contextual_vectors/selection',
 'retrieve.contextual_targets/curated','retrieve.contextual_targets/components',
 'retrieve.contextual_target/declared','retrieve.contextual_inventory/declared',
 'retrieve.contextual_scores/declared','retrieve.contextual/declared',
 'retrieve.contextual_witnesses/declared','retrieve.contextual/with-witnesses') THEN RETURN; END IF;
 PERFORM ops.ddo_require_contextual_producer(r,completion);
 IF r.operation_id IN ('retrieve.contextual_scores/declared','retrieve.contextual/declared','retrieve.contextual/with-witnesses') THEN
 values_:=ops.ddo_contextual_scoring_inputs(r,completion);
 ELSIF r.operation_id='retrieve.contextual_witnesses/declared' THEN
 PERFORM ops.ddo_contextual_witness_inputs(r,completion);
 ELSIF r.operation_id='retrieve.contextual_targets/components' THEN
 DECLARE original ops.data_request:=r; source_basis jsonb; report_row jsonb;
 BEGIN
 original.binding:=r.binding||jsonb_build_object('inputs',completion->'inputs','support',completion->'support');
 source_basis:=ops.ddo_cpu_input_basis(original);
 SELECT value INTO STRICT report_row FROM jsonb_array_elements(data.ddo_field(source_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='report';
 PERFORM ops.ddo_definition_component_basis(report_row);
 END;
 END IF;
 IF r.operation_id='retrieve.contextual_scores/declared' THEN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 actual:=ops.ddo_contextual_score_meaning(ops.ddo_contextual_native_scores(values_->'query',values_->'inventory',
 values_->'vectors',values_->'policy',definition.support_contract->'numerical_policy'->'body'));
 ELSE actual:=ops.ddo_cpu_reply_output(r,completion); END IF;
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
 'retrieve.contextual_target/declared','retrieve.contextual_inventory/declared',
 'retrieve.contextual_scores/declared','retrieve.contextual/declared',
 'retrieve.contextual_witnesses/declared','retrieve.contextual/with-witnesses') THEN RETURN true; END IF;
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
 (episode.producer_task_id,episode.producer_attempt,episode.runtime_id) THEN RETURN false; END IF;
 -- Native scoring is recomputed and sealed by the completion guard. Its actual
 -- task/runtime fences are the immutable intent columns, not a labelled thread
 -- result or a manufactured CPU execution envelope.
 IF r.operation_id<>'retrieve.contextual_scores/declared' AND (evidence->>'request_id' IS DISTINCT FROM episode.request_id
 OR (evidence->>'generation')::integer IS DISTINCT FROM episode.generation
 OR (evidence->>'task_id')::bigint IS DISTINCT FROM intent.producer_task_id
 OR (evidence->>'attempt')::integer IS DISTINCT FROM intent.producer_attempt
 OR evidence->>'holder' IS DISTINCT FROM intent.producer_holder
 OR evidence->>'runtime_id' IS DISTINCT FROM intent.runtime_id) THEN RETURN false; END IF;
 -- A later generation may rebind the request. Producer checking below uses the
 -- sealed episode's release/runtime/recipe and never today's input binding.
 r.release_id:=episode.release_id; r.runtime_id:=episode.runtime_id;
 r.recipe:=episode.recipe; r.generation:=episode.generation;
 PERFORM ops.ddo_require_contextual_producer(r,intent.payload);
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $contextual$;
REVOKE ALL ON FUNCTION ops.ddo_require_contextual_producer(ops.data_request,jsonb),
 ops.ddo_require_contextual_completion(ops.data_request,jsonb),ops.ddo_contextual_scoring_inputs(ops.data_request,jsonb),ops.ddo_contextual_dependencies_valid(text) FROM PUBLIC;
"""
