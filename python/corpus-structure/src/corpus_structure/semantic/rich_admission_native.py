"""Private rich-admission correspondence at the existing native completion fence.

Policy numerics and graph lowering belong to their captured CPU owners. Native
admission authenticates those owners, their exact declared inputs, and the actual
child reply rather than interpreting an ungrounded accepted flag.
"""

from __future__ import annotations


def rich_admission_native_sql() -> str:
    return _rich_input_correspondence_sql() + _rich_completion_sql()


def _rich_input_correspondence_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_rich_support_population(support jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $rich$
 SELECT coalesce(jsonb_agg(reference ORDER BY convert_to(data.canonical_json(reference),'UTF8')),'[]')
 FROM (SELECT DISTINCT jsonb_strip_nulls(value)-'admission_use_id' AS reference FROM jsonb_array_elements(support)) references_
$rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_role_headers(basis jsonb)
RETURNS SETOF jsonb LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $rich$
 SELECT data.ddo_json(jsonb_build_array('mapping',(
 SELECT coalesce(jsonb_agg(pair ORDER BY (pair->>0) COLLATE "C"),'[]')
 FROM jsonb_array_elements(role_meaning->1) pair WHERE pair->>0 NOT IN ('body','context'))))
 FROM jsonb_array_elements(data.ddo_field(basis,'roles')->1) role_meaning
$rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_role_population(basis jsonb,role_name text)
RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $rich$
 SELECT coalesce(jsonb_agg(item ORDER BY convert_to(data.canonical_json(item),'UTF8')),'[]') FROM (
 SELECT jsonb_build_object('product_id',row_value->'product_id','member_id',row_value->'member_id',
 'multiplicity',row_value->'multiplicity','support',ops.ddo_rich_support_population(row_value->'support')) AS item
 FROM ops.ddo_rich_role_headers(basis) row_value WHERE row_value->>'role'=role_name
 ) population
$rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_selected_value(project text,basis jsonb,role_name text,selected jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE bound jsonb; product kb.data_product; member kb.data_product_member;
BEGIN
 SELECT value INTO STRICT bound FROM jsonb_array_elements(data.ddo_field(basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1=role_name
 AND data.ddo_field(value,'product_id')->>1=selected->>'product_id'
 AND data.ddo_field(value,'member_id')='["null"]'::jsonb;
 IF data.ddo_field(bound,'support') IS DISTINCT FROM data.ddo_normalize(data.ddo_json_meaning(jsonb_strip_nulls(selected->'support_references'))) THEN
 RAISE EXCEPTION 'rich selection differs from actual whole-role support' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT product FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=project;
 IF selected->>'member_id' IS NULL THEN
 IF product.kind_contract IS DISTINCT FROM selected->>'kind_contract' THEN
 RAISE EXCEPTION 'rich whole selection differs from its actual kind' USING ERRCODE='23514'; END IF;
 RETURN product.canonical_body;
 END IF;
 SELECT * INTO STRICT member FROM kb.data_product_member WHERE product_id=product.id AND member_id=selected->>'member_id';
 IF member.kind_contract IS DISTINCT FROM selected->>'kind_contract' THEN
 RAISE EXCEPTION 'rich nominal member differs from its actual whole-report kind' USING ERRCODE='23514'; END IF;
 RETURN member.body;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_producing_request(project text,selected jsonb,operation_name text,factory_name text,output_role text,requires_cpu boolean)
RETURNS ops.data_request LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE request ops.data_request; producer ops.data_derivation; definition sem.data_operation_definition; intent ops.data_completion_intent;
BEGIN
 SELECT episode.* INTO STRICT producer FROM ops.data_derivation episode
 JOIN ops.data_derivation_output output ON output.derivation_id=episode.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 WHERE output.product_id=selected->>'product_id' AND output.member_id IS NULL
 AND (output_role IS NULL OR output.role=output_role) AND output.multiplicity=1 AND episode.outcome='success'
 AND EXISTS(SELECT FROM jsonb_array_elements(selected->'support_references') reference
 WHERE reference->>'kind'='computation' AND reference->>'derivation_id'=episode.id);
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=producer.request_id AND project_id=project;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=request.release_id AND operation_id=request.operation_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=producer.intent_id;
 IF (operation_name IS NOT NULL AND definition.operation_id IS DISTINCT FROM operation_name)
 OR (factory_name IS NOT NULL AND definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM factory_name)
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR intent.payload->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR producer.recipe IS DISTINCT FROM definition.recipe OR request.recipe IS DISTINCT FROM definition.recipe
 OR (requires_cpu AND (definition.profile IS DISTINCT FROM 'derivation'
 OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR jsonb_array_length(coalesce(intent.payload->'execution_evidence'->'cpu_receipts','[]'))<>1)) THEN
 RAISE EXCEPTION 'rich selection lacks its actual admitted producer and CPU/common receipt' USING ERRCODE='23514'; END IF;
 RETURN request;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_family_contract(p_release text,local_name text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE archive jsonb; result text;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT archive FROM sem.artifact
 WHERE release_id=p_release AND artifact_name='data_operations.json';
 SELECT identity->>'key' INTO STRICT result FROM jsonb_array_elements(archive->'kinds') kind
 JOIN jsonb_array_elements(archive->'identities') identity ON identity->>'owner'=kind->>'semantic_id'
 WHERE kind->>'name'=local_name AND kind->>'category'='class' AND kind->'complete'='true'::jsonb AND identity->>'domain'='kind';
 RETURN result;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_require_proposal_context(consolidation_basis jsonb,located_basis jsonb)
RETURNS void LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE consumed jsonb;
BEGIN
 SELECT value INTO STRICT consumed FROM ops.ddo_rich_role_headers(located_basis) value WHERE value->>'role'='packet';
 IF consumed->>'member_id' IS NOT NULL OR NOT EXISTS(
 SELECT FROM ops.ddo_rich_role_headers(consolidation_basis) context_input
 WHERE context_input->>'role'='proposal_contexts' AND context_input->>'product_id'=consumed->>'product_id'
 AND context_input->>'member_id' IS NULL
 AND ops.ddo_rich_support_population(context_input->'support')=ops.ddo_rich_support_population(consumed->'support')) THEN
 RAISE EXCEPTION 'rich located proposal differs from actual consumed whole packet/context support' USING ERRCODE='23514'; END IF;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_carried_reading(packet jsonb,known_packets jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $rich$
 SELECT coalesce(data.ddo_field(data.ddo_field(packet,'body'),'member_type')='["string","source-reading-assertion"]'::jsonb
 AND known_packets->ops.ddo_digest(data.ddo_normalize(packet))=data.ddo_normalize(packet),false)
$rich$;

REVOKE ALL ON FUNCTION ops.ddo_rich_role_population(jsonb,text),ops.ddo_rich_selected_value(text,jsonb,text,jsonb),
 ops.ddo_rich_producing_request(text,jsonb,text,text,text,boolean),ops.ddo_rich_family_contract(text,text),
 ops.ddo_rich_support_population(jsonb),ops.ddo_rich_require_proposal_context(jsonb,jsonb),ops.ddo_rich_role_headers(jsonb),
 ops.ddo_rich_carried_reading(jsonb,jsonb) FROM PUBLIC;
"""


def _rich_completion_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_rich_command_eligible(definition sem.data_operation_definition)
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $rich$
 SELECT definition.operation_id='rich.admit' AND definition.profile='command'
 AND definition.support_contract->'capabilities'->>'preparation'='native-publication'
 AND definition.support_contract->'capabilities'->'forms'='["scalar"]'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint'='corpus_structure.methods.rich_knowledge.RichKnowledgeAdmission.acquire_port'
 AND definition.support_contract->'effects'='[{"name":"native-rich-knowledge-admission","authorization":["exact-rich-consolidation-and-record-policy"],"idempotency":"request-generation/exact-input-population","fulfillment":"native-publication-receipt"}]'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND definition.implementation_revision LIKE 'implementation-slice:%'
$rich$;
REVOKE ALL ON FUNCTION ops.ddo_rich_command_eligible(sem.data_operation_definition) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_rich_require_preparation_producer(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE definition sem.data_operation_definition; output jsonb; factory text; output_role text; output_kind text;
BEGIN
 CASE r.operation_id
 WHEN 'prepare.external_extraction' THEN
 factory:='corpus_structure.methods.external_extraction.RichExtractionInputOperation.acquire_port';
 output_role:='result'; output_kind:='https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket';
 WHEN 'locate.external_extraction' THEN
 factory:='corpus_structure.methods.external_extraction.RichExtractionPlacementOperation.acquire_port';
 output_role:='result'; output_kind:='https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoLocatedExternalExtraction';
 WHEN 'rich.consolidate' THEN
 factory:='corpus_structure.methods.rich_knowledge.RichKnowledgeConsolidation.acquire_port';
 output_role:='consolidated'; output_kind:='https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichConsolidation';
 ELSE RAISE EXCEPTION 'rich preparation requires its actual operation owner' USING ERRCODE='23514';
 END CASE;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF definition.profile IS DISTINCT FROM 'derivation'
 OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM factory
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR completion->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR r.recipe IS DISTINCT FROM definition.recipe
 OR (r.operation_id='rich.consolidate' AND r.original_source IS NOT NULL)
 OR completion->'inputs' IS DISTINCT FROM r.binding->'inputs'
 OR completion->'support' IS DISTINCT FROM r.binding->'support'
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1 THEN
 RAISE EXCEPTION 'rich preparation requires actual derivation/factory/CPU and declared inputs' USING ERRCODE='23514'; END IF;
 IF completion->>'outcome' IS DISTINCT FROM 'success' OR jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'rich preparation requires one exact successful conclusion' USING ERRCODE='23514'; END IF;
 output:=completion->'outputs'->0;
 IF output->>'role' IS DISTINCT FROM output_role OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind=output_kind AND kind.universe='ordinary') THEN
 RAISE EXCEPTION 'rich preparation differs from its actual whole nominal output' USING ERRCODE='23514'; END IF;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_require_rich_preparation_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
BEGIN
 IF r.operation_id NOT IN ('prepare.external_extraction','locate.external_extraction','rich.consolidate') THEN RETURN; END IF;
 PERFORM ops.ddo_rich_require_preparation_producer(r,completion);
 IF ops.ddo_cpu_reply_output(r,completion) IS DISTINCT FROM data.ddo_normalize(completion->'outputs'->0->'product'->'body') THEN
 RAISE EXCEPTION 'rich preparation differs from actual original CPU reply and input basis' USING ERRCODE='23514'; END IF;
 IF r.operation_id='rich.consolidate' THEN PERFORM ops.ddo_rich_require_proposal_inputs(r.project_id,ops.ddo_cpu_input_basis(r)); END IF;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_require_proposal_inputs(project text,basis jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE selected jsonb; reference jsonb; item jsonb; located_request ops.data_request; packet_request ops.data_request;
BEGIN
 -- Located extraction drops macros; authenticate its actual immutable packet
 -- input rather than equating two packets that merely share source coordinates.
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(basis) header(value) WHERE value->>'role'='proposals' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 located_request:=ops.ddo_rich_producing_request(project,reference,'locate.external_extraction',
 'corpus_structure.methods.external_extraction.RichExtractionPlacementOperation.acquire_port','result',true);
 SELECT intent.payload INTO STRICT item FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=located_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 PERFORM ops.ddo_require_rich_preparation_completion(located_request,item);
 IF item->'outputs'->0->'product'->'body' IS DISTINCT FROM
 ops.ddo_rich_selected_value(project,basis,'proposals',reference) THEN
 RAISE EXCEPTION 'rich proposal differs from actual located CPU output' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_rich_require_proposal_context(basis,ops.ddo_cpu_input_basis(located_request));
 END LOOP;
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(basis) header(value) WHERE value->>'role'='proposal_contexts' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 packet_request:=ops.ddo_rich_producing_request(project,reference,'prepare.external_extraction',
 'corpus_structure.methods.external_extraction.RichExtractionInputOperation.acquire_port','result',true);
 SELECT intent.payload INTO STRICT item FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=packet_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 PERFORM ops.ddo_require_rich_preparation_completion(packet_request,item);
 IF item->'outputs'->0->'product'->'body' IS DISTINCT FROM
 ops.ddo_rich_selected_value(project,basis,'proposal_contexts',reference) THEN
 RAISE EXCEPTION 'rich proposal context differs from actual prepared CPU packet' USING ERRCODE='23514'; END IF;
 END LOOP;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_require_admission_producer(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE definition sem.data_operation_definition; output jsonb;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF NOT coalesce(ops.ddo_rich_command_eligible(definition),false)
 OR completion->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR r.recipe IS DISTINCT FROM definition.recipe OR r.original_source IS NOT NULL
 OR completion->'inputs' IS DISTINCT FROM r.binding->'inputs'
 OR completion->'support' IS DISTINCT FROM r.binding->'support'
 OR jsonb_array_length(coalesce(completion->'execution_evidence'->'cpu_receipts','[]'))<>1 THEN
 RAISE EXCEPTION 'rich admission requires actual command/effect/factory/CPU and whole declared inputs' USING ERRCODE='23514'; END IF;
 IF completion->>'outcome' IS DISTINCT FROM 'success' OR jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'rich admission requires one exact successful conclusion' USING ERRCODE='23514'; END IF;
 output:=completion->'outputs'->0;
 IF output->>'role' IS DISTINCT FROM 'admission' OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind='https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichAdmission' AND kind.universe='ordinary')
 OR (SELECT count(*) FROM jsonb_array_elements(r.binding->'inputs') input WHERE input->>'role'='consolidation')<>1
 OR EXISTS(SELECT FROM jsonb_array_elements(r.binding->'inputs') input WHERE input->>'member_id' IS NOT NULL
 OR (input->>'multiplicity')::integer IS DISTINCT FROM 1
 OR input->>'role' NOT IN ('consolidation','records','readings','policy_authorizations')) THEN
 RAISE EXCEPTION 'rich admission differs from its actual whole populations and nominal output' USING ERRCODE='23514'; END IF;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_require_rich_admission_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE basis jsonb; admission_meaning jsonb; admission jsonb; consolidated_meaning jsonb; consolidated jsonb;
 consolidation_request ops.data_request; consolidation_basis jsonb; selected jsonb; authorization_request ops.data_request;
 resolution_request ops.data_request; known_request ops.data_request;
 resolution_basis jsonb; reference jsonb; decision jsonb; raw_meaning jsonb; resolved_meaning jsonb; known_episode text;
 raw_record jsonb; resolved_record jsonb; resolution_meaning jsonb; report jsonb; policy_meaning jsonb; policy jsonb;
 events jsonb; event jsonb; reports jsonb:='{}'; raw_reports jsonb:='{}'; policies jsonb:='{}'; known_packets jsonb:='{}'; item jsonb; packet jsonb; raw_digest text;
 raw_comparison jsonb; resolved_comparison jsonb; assertion jsonb; family_contract text;
 known_meaning jsonb; known_graph jsonb;
BEGIN
 IF r.operation_id IS DISTINCT FROM 'rich.admit' THEN
 IF EXISTS(SELECT FROM sem.data_operation_definition definition CROSS JOIN LATERAL jsonb_array_elements(definition.support_contract->'effects') effect
 WHERE definition.release_id=r.release_id AND definition.operation_id=r.operation_id AND effect->>'name'='native-rich-knowledge-admission') THEN
 RAISE EXCEPTION 'rich admission effect requires its actual operation owner' USING ERRCODE='23514'; END IF;
 RETURN; END IF;
 PERFORM ops.ddo_rich_require_admission_producer(r,completion);
 basis:=ops.ddo_cpu_input_basis(r);
 admission_meaning:=data.ddo_normalize(completion->'outputs'->0->'product'->'body');
 -- The shared owner authenticates original bytes against result_digest and the
 -- child's independently reconstructed typed basis. No free accepted flag,
 -- regenerated reply text, or preserved receipt with another body is sufficient.
 IF ops.ddo_cpu_reply_output(r,completion) IS DISTINCT FROM admission_meaning THEN
 RAISE EXCEPTION 'rich admission differs from exact CPU decision and graph projection' USING ERRCODE='23514'; END IF;
 admission:=data.ddo_json(admission_meaning);
 consolidated_meaning:=ops.ddo_rich_selected_value(r.project_id,basis,'consolidation',admission->'consolidation');
 consolidated:=data.ddo_json(consolidated_meaning);
 consolidation_request:=ops.ddo_rich_producing_request(r.project_id,admission->'consolidation','rich.consolidate',
 'corpus_structure.methods.rich_knowledge.RichKnowledgeConsolidation.acquire_port','consolidated',true);
 SELECT intent.payload INTO STRICT item FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=consolidation_request.id AND EXISTS(SELECT FROM jsonb_array_elements(admission->'consolidation'->'support_references') support WHERE support->>'derivation_id'=producer.id);
 IF ops.ddo_cpu_reply_output(consolidation_request,item) IS DISTINCT FROM consolidated_meaning THEN
 RAISE EXCEPTION 'rich consolidation differs from actual original CPU graph reply' USING ERRCODE='23514'; END IF;
 consolidation_basis:=ops.ddo_cpu_input_basis(consolidation_request);
 IF consolidated->>'version' IS DISTINCT FROM 'rich-consolidation-1' OR consolidated->>'standing' IS DISTINCT FROM 'private-consolidated'
 OR admission->>'version' IS DISTINCT FROM 'rich-admission-1' OR admission->>'standing' IS DISTINCT FROM 'accepted'
 OR ops.ddo_rich_role_population(basis,'records') IS DISTINCT FROM ops.ddo_rich_role_population(consolidation_basis,'records')
 OR ops.ddo_rich_role_population(basis,'readings') IS DISTINCT FROM ops.ddo_rich_role_population(consolidation_basis,'readings') THEN
 RAISE EXCEPTION 'rich admission changes actual consolidated records/readings population or producer custody' USING ERRCODE='23514'; END IF;
 IF admission->>'eligibility_policy_digest' IS NULL
 OR admission->>'eligibility_policy_digest' !~ '^[0-9a-f]{64}$'
 OR admission->>'eligibility_policy_digest' IS DISTINCT FROM consolidated->'eligibility'->>'eligibility_policy_digest'
 OR admission->'selected_fact_ids' IS DISTINCT FROM consolidated->'eligibility'->'selected_fact_ids'
 OR admission->'selected_occurrence_ids' IS DISTINCT FROM consolidated->'eligibility'->'selected_occurrence_ids'
 OR admission->'scientific_representatives' IS DISTINCT FROM consolidated->'eligibility'->'scientific_representatives' THEN
 RAISE EXCEPTION 'rich admission changes actual rule eligibility or its checked policy basis' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_rich_require_proposal_inputs(r.project_id,consolidation_basis);
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(consolidation_basis) header(value) WHERE value->>'role'='known_universe' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 known_request:=ops.ddo_rich_producing_request(r.project_id,reference,'rich.admit',
 'corpus_structure.methods.rich_knowledge.RichKnowledgeAdmission.acquire_port','admission',false);
 SELECT producer.id INTO STRICT known_episode FROM ops.data_derivation producer
 WHERE producer.request_id=known_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 IF NOT ops.ddo_rich_admission_dependencies_valid(known_episode) THEN
 RAISE EXCEPTION 'rich known universe lacks actual sealed native admission authority' USING ERRCODE='23514'; END IF;
 SELECT canonical_body INTO STRICT known_meaning FROM kb.data_product
 WHERE id=reference->>'product_id' AND project_id=r.project_id;
 known_graph:=data.ddo_json(known_meaning);
 IF known_graph->>'eligibility_policy_digest' IS DISTINCT FROM admission->>'eligibility_policy_digest'
 OR jsonb_typeof(known_graph->'selected_reading_ids') IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'rich known eligibility requires its actual current policy basis and selection' USING ERRCODE='23514'; END IF;
 -- A previous accepted graph retains its own source/interpretation/support
 -- attribution. Index only exact reading packets after genuine native authority
 -- has been established; these are not new current raw/resolved decisions.
 FOR packet IN SELECT value FROM jsonb_array_elements(data.ddo_field(known_meaning,'members')->1)
 WHERE data.ddo_field(data.ddo_field(value,'body'),'member_type')='["string","source-reading-assertion"]'::jsonb
 AND known_graph->'selected_reading_ids' ? (data.ddo_field(value,'member_id')->>1) LOOP
 known_packets:=known_packets||jsonb_build_object(ops.ddo_digest(data.ddo_normalize(packet)),data.ddo_normalize(packet));
 END LOOP;
 END LOOP;
 -- Exact tagged packet membership preserves every retained field, evidence,
 -- alternative and context. The approved CPU graph owner selects closed
 -- dependencies; native does not implement a second lowering algorithm.
 IF EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(admission_meaning,'members')->1) member
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(consolidated_meaning,'members')->1) original
 WHERE data.ddo_normalize(original)=data.ddo_normalize(member)))
 OR EXISTS(SELECT FROM jsonb_array_elements(admission->'members') member GROUP BY member->>'member_id' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'rich admission changes actual consolidated graph members' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(admission->'policy_authorizations') IS DISTINCT FROM jsonb_array_length(ops.ddo_rich_role_population(basis,'policy_authorizations')) THEN
 RAISE EXCEPTION 'rich policy population differs from actual declared authorizations' USING ERRCODE='23514'; END IF;
 FOR reference IN SELECT value FROM jsonb_array_elements(admission->'policy_authorizations') LOOP
 IF reference->>'member_id' IS NOT NULL OR policies ? (reference->>'product_id') THEN
 RAISE EXCEPTION 'rich policy requires unique whole issued authorizations' USING ERRCODE='23514'; END IF;
 policy_meaning:=ops.ddo_rich_selected_value(r.project_id,basis,'policy_authorizations',reference);
 authorization_request:=ops.ddo_rich_producing_request(r.project_id,reference,'record_policy.authorize',
 'corpus_structure.methods.record_policy.RecordPolicyAuthorization.acquire_port','authorization',false);
 IF NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=reference->>'kind_contract'
 AND kind.kind='https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization' AND kind.universe='ordinary') THEN
 RAISE EXCEPTION 'rich policy is not the actual public authorization contract' USING ERRCODE='23514'; END IF;
 SELECT intent.payload INTO STRICT item FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=authorization_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 PERFORM ops.ddo_require_policy_authorization_completion(authorization_request,item);
 policies:=policies||jsonb_build_object(reference->>'product_id',jsonb_build_object('reference',reference,'body',data.ddo_json(policy_meaning)));
 END LOOP;
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(consolidation_basis) header(value) WHERE value->>'role'='records' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 PERFORM ops.ddo_rich_producing_request(r.project_id,reference,NULL,NULL,NULL,true);
 SELECT ops.ddo_digest(canonical_body) INTO STRICT raw_digest FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 raw_reports:=raw_reports||jsonb_build_object(selected->>'product_id',raw_digest);
 END LOOP;
 -- Prepare each distinct whole resolution report/event index once. All these
 -- dependencies are declared roles and enter the existing canonical lock union.
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(consolidation_basis) header(value) WHERE value->>'role'='readings' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 resolution_request:=ops.ddo_rich_producing_request(r.project_id,reference,'resolve.m1_readings/declared',
 'corpus_structure.methods.reading_resolution.ReadingResolutionOperation.acquire_port','result',true);
 resolution_basis:=ops.ddo_cpu_input_basis(resolution_request);
 resolution_meaning:=ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'readings',reference);
 SELECT intent.payload INTO STRICT item FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=resolution_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 IF ops.ddo_cpu_reply_output(resolution_request,item) IS DISTINCT FROM resolution_meaning THEN
 RAISE EXCEPTION 'rich final-event report differs from actual original reading CPU reply' USING ERRCODE='23514'; END IF;
 report:=data.ddo_json(resolution_meaning);
 events:=(report->>'diagnostics_json')::jsonb->'record_policy_events';
 IF jsonb_typeof(events) IS DISTINCT FROM 'array'
 OR EXISTS(SELECT FROM jsonb_array_elements(events) event_row GROUP BY event_row->>'record_id',event_row->>'interpretation_id' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'rich resolution requires unique actual final-event attribution' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_object_agg(data.canonical_json(jsonb_build_array(event_row->>'record_id',event_row->>'interpretation_id')),event_row),'{}') INTO events FROM jsonb_array_elements(events) event_row;
 reports:=reports||jsonb_build_object(reference->>'product_id',jsonb_build_object(
 'inputs',(SELECT coalesce(jsonb_agg(header),'[]') FROM ops.ddo_rich_role_headers(resolution_basis) header),'release_id',resolution_request.release_id,'recipe',resolution_request.recipe,'events',events));
 END LOOP;
 -- The decision census covers every actual raw record AND resolved record,
 -- including explicit unavailable resolutions and uncheckable/low-score events.
 -- An empty report has no fake record member.
 IF EXISTS(SELECT FROM ops.ddo_rich_role_headers(consolidation_basis) bound
 JOIN kb.data_product_member member ON member.product_id=bound->>'product_id'
 WHERE bound->>'role'='records' AND data.ddo_field(member.body,'candidate_type')='["string","record"]'::jsonb
 AND (SELECT count(*) FROM jsonb_array_elements(admission->'reading_decisions') judgment
 WHERE judgment->'original'->>'product_id'=member.product_id AND judgment->'original'->>'member_id'=member.member_id)<>1) THEN
 RAISE EXCEPTION 'rich decision census omits or duplicates actual raw records' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM ops.ddo_rich_role_headers(consolidation_basis) bound
 JOIN kb.data_product_member member ON member.product_id=bound->>'product_id'
 WHERE bound->>'role'='readings' AND data.ddo_field(member.body,'candidate_type')='["string","record"]'::jsonb
 AND (SELECT count(*) FROM jsonb_array_elements(admission->'reading_decisions') judgment
 WHERE judgment->'resolved'->>'product_id'=member.product_id AND judgment->'resolved'->>'member_id'=member.member_id)<>1) THEN
 RAISE EXCEPTION 'rich decision census omits or duplicates actual resolved records' USING ERRCODE='23514'; END IF;
 FOR decision IN SELECT value FROM jsonb_array_elements(admission->'reading_decisions') LOOP
 raw_meaning:=ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'records',decision->'original');
 raw_record:=data.ddo_json(raw_meaning);
 IF raw_record->>'candidate_type' IS DISTINCT FROM 'record' OR decision->'original'->>'member_id' IS NULL
 OR raw_record->>'record_id' IS DISTINCT FROM decision->>'record_id'
 OR raw_record->>'interpretation_id' IS DISTINCT FROM decision->>'source_interpretation_id' THEN
 RAISE EXCEPTION 'rich decision relabels actual original record attribution' USING ERRCODE='23514'; END IF;
 IF decision->'resolution'='null'::jsonb OR decision->'resolved'='null'::jsonb THEN
 IF decision->'resolution' IS DISTINCT FROM 'null'::jsonb OR decision->'resolved' IS DISTINCT FROM 'null'::jsonb
 OR decision->>'outcome' IS DISTINCT FROM 'not-checkable' OR decision->>'reason_code' IS DISTINCT FROM 'resolution-unavailable'
 OR decision->>'assertion_member_id' IS NOT NULL THEN
 RAISE EXCEPTION 'rich missing resolution must remain explicitly uncheckable' USING ERRCODE='23514'; END IF;
 CONTINUE; END IF;
 resolved_meaning:=ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'readings',decision->'resolved');
 PERFORM ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'readings',decision->'resolution');
 resolved_record:=data.ddo_json(resolved_meaning);
 report:=reports->(decision->'resolution'->>'product_id');
 IF report IS NULL OR decision->'resolved'->>'product_id' IS DISTINCT FROM decision->'resolution'->>'product_id'
 OR decision->'resolution'->>'member_id' IS NOT NULL OR decision->'original'->>'member_id' IS NULL OR decision->'resolved'->>'member_id' IS NULL
 OR raw_record->>'candidate_type' IS DISTINCT FROM 'record' OR resolved_record->>'candidate_type' IS DISTINCT FROM 'record'
 OR raw_record->>'record_id' IS DISTINCT FROM decision->>'record_id' OR resolved_record->>'record_id' IS DISTINCT FROM decision->>'record_id'
 OR raw_record->>'interpretation_id' IS DISTINCT FROM decision->>'source_interpretation_id'
 OR resolved_record->>'interpretation_id' IS DISTINCT FROM decision->>'interpretation_id'
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(report->'inputs') input
 WHERE input->>'role'='candidates' AND input->>'product_id'=decision->'original'->>'product_id'
 AND input->>'member_id' IS NULL
 AND ops.ddo_rich_support_population(input->'support')=ops.ddo_rich_support_population(decision->'original'->'support_references')) THEN
 RAISE EXCEPTION 'rich decision relabels actual raw/resolved member and producing report custody' USING ERRCODE='23514'; END IF;
 SELECT jsonb_build_array('mapping',jsonb_agg(pair ORDER BY (pair->>0) COLLATE "C")) INTO raw_comparison FROM jsonb_array_elements(raw_meaning->1) pair WHERE pair->>0 NOT IN ('interpretation_id','computation_dependencies');
 SELECT jsonb_build_array('mapping',jsonb_agg(pair ORDER BY (pair->>0) COLLATE "C")) INTO resolved_comparison FROM jsonb_array_elements(resolved_meaning->1) pair WHERE pair->>0 NOT IN ('interpretation_id','computation_dependencies');
 IF raw_comparison IS DISTINCT FROM resolved_comparison
 OR NOT (data.ddo_field(resolved_meaning,'computation_dependencies')->1 @>
 jsonb_build_array(jsonb_build_array('string','raw-candidate-result:'||(raw_reports->>(decision->'original'->>'product_id')))))
 OR EXISTS(
 SELECT FROM jsonb_array_elements(data.ddo_field(raw_meaning,'computation_dependencies')->1) dependency
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(resolved_meaning,'computation_dependencies')->1) retained WHERE retained=dependency)) THEN
 RAISE EXCEPTION 'rich resolved reading changes complete original fields/evidence/alternatives' USING ERRCODE='23514'; END IF;
 IF decision->'authorization'<>'null'::jsonb
 AND decision->'authorization' IS DISTINCT FROM policies->(decision->'authorization'->>'product_id')->'reference' THEN
 RAISE EXCEPTION 'rich decision references authority outside actual declared issuer population' USING ERRCODE='23514'; END IF;
 IF decision->>'outcome' IN ('accepted','below-threshold') THEN
 policy:=policies->(decision->'authorization'->>'product_id')->'body';
 event:=report->'events'->data.canonical_json(jsonb_build_array(decision->>'record_id',decision->>'interpretation_id'));
 family_contract:=ops.ddo_rich_family_contract(report->>'release_id',resolved_record->>'contract');
 IF policy IS NULL OR decision->'authorization' IS DISTINCT FROM policies->(decision->'authorization'->>'product_id')->'reference'
 OR event IS NULL OR event->>'outcome' IS DISTINCT FROM 'completed'
 OR event->>'feature_input_digest' IS DISTINCT FROM decision->>'feature_input_digest'
 OR event->>'feature_instance_digest' IS DISTINCT FROM decision->>'feature_instance_digest'
 OR event->>'event_procedure' IS DISTINCT FROM decision->>'event_procedure'
 OR policy->>'feature_instance_digest' IS DISTINCT FROM decision->>'feature_instance_digest'
 OR policy->>'event_procedure' IS DISTINCT FROM decision->>'event_procedure'
 OR policy->>'family' IS DISTINCT FROM resolved_record->>'family'
 OR policy->>'family_contract' IS DISTINCT FROM family_contract
 OR family_contract IS DISTINCT FROM ops.ddo_rich_family_contract(r.release_id,resolved_record->>'contract')
 OR policy->>'reading_recipe' IS DISTINCT FROM report->>'recipe'
 OR policy->'applicability'->>'project_id' IS DISTINCT FROM r.project_id
 OR encode(sha256(convert_to(event->>'feature_input_canonical_json','UTF8')),'hex') IS DISTINCT FROM event->>'feature_input_digest' THEN
 RAISE EXCEPTION 'rich decision lacks exact issued policy/current family/recipe and unique sealed feature event' USING ERRCODE='23514'; END IF;
 END IF;
 IF decision->>'outcome'='accepted' THEN
 SELECT member INTO STRICT assertion FROM jsonb_array_elements(admission->'members') member WHERE member->>'member_id'=decision->>'assertion_member_id';
 IF assertion->'body'->>'member_type' IS DISTINCT FROM 'source-reading-assertion'
 OR assertion->'body'->'original' IS DISTINCT FROM decision->'original'
 OR assertion->'body'->'resolution' IS DISTINCT FROM decision->'resolution'
 OR assertion->'body'->'resolved' IS DISTINCT FROM decision->'resolved'
 OR assertion->'body'->>'record_id' IS DISTINCT FROM decision->>'record_id'
 OR assertion->'body'->>'source_interpretation_id' IS DISTINCT FROM decision->>'source_interpretation_id'
 OR assertion->'body'->>'interpretation_id' IS DISTINCT FROM decision->>'interpretation_id' THEN
 RAISE EXCEPTION 'rich accepted assertion differs from actual complete reading decision' USING ERRCODE='23514'; END IF;
 ELSIF decision->>'assertion_member_id' IS NOT NULL THEN
 RAISE EXCEPTION 'rich rejected reading cannot retain an accepted assertion' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(admission_meaning,'members')->1) member_meaning
 WHERE data.ddo_field(data.ddo_field(member_meaning,'body'),'member_type')='["string","source-reading-assertion"]'::jsonb
 AND (SELECT count(*) FROM jsonb_array_elements(admission->'reading_decisions') judgment WHERE judgment->>'outcome'='accepted' AND judgment->>'assertion_member_id'=data.ddo_field(member_meaning,'member_id')->>1)<>1
 AND NOT ops.ddo_rich_carried_reading(member_meaning,known_packets)) THEN
 RAISE EXCEPTION 'rich accepted graph has no exact actual reading decision' USING ERRCODE='23514'; END IF;
 IF jsonb_typeof(admission->'selected_reading_ids') IS DISTINCT FROM 'array'
 OR (SELECT coalesce(jsonb_agg(member->>'member_id' ORDER BY (member->>'member_id') COLLATE "C"),'[]')
 FROM jsonb_array_elements(admission->'members') member
 WHERE member->'body'->>'member_type'='source-reading-assertion') IS DISTINCT FROM
 (SELECT coalesce(jsonb_agg(value ORDER BY value COLLATE "C"),'[]')
 FROM jsonb_array_elements_text(admission->'selected_reading_ids')) THEN
 RAISE EXCEPTION 'rich selected readings differ from actual retained assertion packets' USING ERRCODE='23514'; END IF;
END $rich$;

CREATE OR REPLACE FUNCTION ops.ddo_rich_admission_dependencies_valid(episode text)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE r ops.data_request; completion jsonb;
BEGIN
 SELECT request.* INTO STRICT r FROM ops.data_request request JOIN ops.data_derivation producer ON producer.request_id=request.id WHERE producer.id=episode;
 IF r.operation_id NOT IN ('rich.admit','rich.consolidate','prepare.external_extraction','locate.external_extraction') THEN RETURN true; END IF;
 -- The same captured native kernel sealed all immutable correspondence checks.
 -- Ordinary support closure still rechecks every declared dependency/current
 -- trust scope. Do not replay every immutable event/graph on every support read.
 IF NOT EXISTS(SELECT FROM ops.data_derivation producer JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=producer.intent_id
 JOIN sem.artifact artifact ON artifact.release_id=producer.release_id AND artifact.artifact_name='data_operation_native_definitions.json'
 WHERE producer.id=episode AND producer.outcome='success' AND convert_from(artifact.content,'UTF8')::jsonb->>'native_digest'='__DDO_SOURCE_DIGEST__') THEN RETURN false; END IF;
 SELECT intent.payload INTO STRICT completion FROM ops.data_derivation producer JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id WHERE producer.id=episode;
 IF r.operation_id='rich.admit' THEN PERFORM ops.ddo_rich_require_admission_producer(r,completion);
 ELSE PERFORM ops.ddo_rich_require_preparation_producer(r,completion); END IF;
 RETURN true;
 EXCEPTION WHEN data_exception OR integrity_constraint_violation OR no_data_found OR too_many_rows THEN RETURN false;
END $rich$;

REVOKE ALL ON FUNCTION ops.ddo_rich_require_admission_producer(ops.data_request,jsonb),
 ops.ddo_rich_require_preparation_producer(ops.data_request,jsonb),ops.ddo_require_rich_preparation_completion(ops.data_request,jsonb),
 ops.ddo_rich_require_proposal_inputs(text,jsonb),
 ops.ddo_require_rich_admission_completion(ops.data_request,jsonb),ops.ddo_rich_admission_dependencies_valid(text) FROM PUBLIC;
"""
