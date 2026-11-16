"""Original current source/cue custody for private authored witness bindings."""


def contextual_witness_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_contextual_input_reference(row_meaning jsonb,contribution boolean)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $witness$
DECLARE context_ jsonb:=data.ddo_field(row_meaning,'context'); result jsonb;
BEGIN
 result:=jsonb_build_object('product_id',data.ddo_field(row_meaning,'product_id')->>1,
 'member_id',data.ddo_json(data.ddo_field(row_meaning,'member_id')),
 'kind_contract',data.ddo_field(row_meaning,'kind_contract')->>1,
 'project_id',data.ddo_field(context_,'project_id')->>1,
 'subject',data.ddo_field(context_,'subject')->>1,
 'subject_definition',data.ddo_field(context_,'subject_definition')->>1,
 'original_source',data.ddo_json(data.ddo_field(context_,'original_source')),
 'analyzed_scope_meaning',data.canonical_json(data.ddo_field(context_,'analyzed_scope')));
 IF contribution THEN result:=result||jsonb_build_object('contribution_id',
 data.ddo_field(data.ddo_field(row_meaning,'body'),'contribution_id')->>1); END IF;
 RETURN jsonb_strip_nulls(result);
END $witness$;

CREATE OR REPLACE FUNCTION ops.ddo_contextual_witness_inputs(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $witness$
DECLARE original ops.data_request:=r; basis jsonb; row_ jsonb; query_row jsonb; inventory_row jsonb;
 source_row jsonb; hypothesis_row jsonb; cues jsonb:='[]'; query_ jsonb; hypotheses jsonb; inventory_ jsonb;
 query_episode ops.data_derivation; inventory_episode ops.data_derivation; query_request ops.data_request;
 query_intent ops.data_completion_intent; query_basis jsonb; original_occurrence jsonb; original_source jsonb;
 cue jsonb; reference_ jsonb; admission ops.original_source_admission; assertion_ jsonb;
 actual_refs jsonb; carrier_ jsonb; seen text[]:='{}'; name_ text;
BEGIN
 original.binding:=r.binding||jsonb_build_object('inputs',completion->'inputs','support',completion->'support');
 basis:=ops.ddo_cpu_input_basis(original);
 FOR row_ IN SELECT value FROM jsonb_array_elements(data.ddo_field(basis,'roles')->1) LOOP
 name_:=data.ddo_field(row_,'role')->>1;
 IF name_ NOT IN ('source','query','inventory','hypotheses','cues')
 OR data.ddo_field(row_,'multiplicity') IS DISTINCT FROM '["integer","1"]'::jsonb THEN
 RAISE EXCEPTION 'contextual witness input population is foreign or repeated' USING ERRCODE='23514'; END IF;
 IF name_='cues' THEN cues:=cues||jsonb_build_array(row_); CONTINUE; END IF;
 IF name_=ANY(seen) THEN RAISE EXCEPTION 'contextual witness requires exact scalar inputs' USING ERRCODE='23514'; END IF;
 seen:=array_append(seen,name_);
 CASE name_ WHEN 'source' THEN source_row:=row_; WHEN 'query' THEN query_row:=row_;
 WHEN 'inventory' THEN inventory_row:=row_; WHEN 'hypotheses' THEN hypothesis_row:=row_; END CASE;
 END LOOP;
 IF query_row IS NULL OR inventory_row IS NULL OR source_row IS NULL OR hypothesis_row IS NULL OR cues='[]'::jsonb
 OR data.ddo_field(query_row,'member_id') IS DISTINCT FROM '["null"]'::jsonb
 OR data.ddo_field(inventory_row,'member_id') IS DISTINCT FROM '["null"]'::jsonb
 OR data.ddo_field(hypothesis_row,'member_id') IS DISTINCT FROM '["null"]'::jsonb
 OR data.ddo_field(query_row,'context') IS DISTINCT FROM data.ddo_field(basis,'context')
 OR data.ddo_field(inventory_row,'context') IS DISTINCT FROM data.ddo_field(basis,'context') THEN
 RAISE EXCEPTION 'contextual witness lacks its exact selected input context/population' USING ERRCODE='23514'; END IF;
 query_:=data.ddo_json(data.ddo_field(query_row,'body'));
 hypotheses:=data.ddo_json(data.ddo_field(hypothesis_row,'body'));
 inventory_:=data.record_source_json(data.ddo_json(data.ddo_field(inventory_row,'body'))->'inventory');
 SELECT d.* INTO STRICT query_episode FROM ops.data_derivation d
 JOIN ops.data_derivation_output output ON output.derivation_id=d.id
 JOIN ops.data_request request ON request.id=d.request_id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=d.id AND receipt.intent_id=d.intent_id
 WHERE output.product_id=data.ddo_field(query_row,'product_id')->>1 AND output.member_id IS NULL AND output.role='query'
 AND request.operation_id IN ('retrieve.contextual_query/declared','retrieve.contextual_query/selected-context')
 AND EXISTS(SELECT FROM jsonb_array_elements(data.ddo_json(data.ddo_field(query_row,'support'))) reference
 WHERE reference->>'kind'='computation' AND reference->>'derivation_id'=d.id);
 IF NOT ops.ddo_contextual_dependencies_valid(query_episode.id) THEN
 RAISE EXCEPTION 'contextual witness query lacks original native/CPU publication' USING ERRCODE='23514'; END IF;
 SELECT d.* INTO STRICT inventory_episode FROM ops.data_derivation d
 JOIN ops.data_derivation_output output ON output.derivation_id=d.id
 JOIN ops.data_request request ON request.id=d.request_id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=d.id AND receipt.intent_id=d.intent_id
 WHERE output.product_id=data.ddo_field(inventory_row,'product_id')->>1 AND output.member_id IS NULL
 AND request.operation_id='retrieve.contextual_inventory/declared'
 AND EXISTS(SELECT FROM jsonb_array_elements(data.ddo_json(data.ddo_field(inventory_row,'support'))) reference
 WHERE reference->>'kind'='computation' AND reference->>'derivation_id'=d.id);
 IF NOT ops.ddo_contextual_dependencies_valid(inventory_episode.id) THEN
 RAISE EXCEPTION 'contextual witness inventory lacks its genuine native/CPU producer' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT query_request FROM ops.data_request WHERE id=query_episode.request_id;
 SELECT * INTO STRICT query_intent FROM ops.data_completion_intent WHERE id=query_episode.intent_id;
 query_request.release_id:=query_episode.release_id; query_request.runtime_id:=query_episode.runtime_id;
 query_request.recipe:=query_episode.recipe; query_request.generation:=query_episode.generation;
 query_request.binding:=query_request.binding||jsonb_build_object('inputs',query_intent.payload->'inputs','support',query_intent.payload->'support');
 query_basis:=ops.ddo_cpu_input_basis(query_request);
 SELECT value INTO STRICT original_occurrence FROM jsonb_array_elements(data.ddo_field(query_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='occurrence';
 SELECT value INTO STRICT original_source FROM jsonb_array_elements(data.ddo_field(query_basis,'roles')->1)
 WHERE data.ddo_field(value,'role')->>1='source';
 carrier_:=ops.ddo_contextual_input_reference(original_occurrence,true);
 IF carrier_ IS DISTINCT FROM query_->'carrier'
 OR ops.ddo_contextual_input_reference(source_row,false) IS DISTINCT FROM ops.ddo_contextual_input_reference(original_source,false)
 OR ops.ddo_rich_role_population(basis,'source') IS DISTINCT FROM ops.ddo_rich_role_population(query_basis,'source') THEN
 RAISE EXCEPTION 'contextual witness source/query carrier differs from original query custody' USING ERRCODE='23514'; END IF;
 actual_refs:='[]';
 FOR cue IN SELECT value FROM jsonb_array_elements(cues) LOOP
 IF jsonb_array_length(data.ddo_json(data.ddo_field(cue,'support')))=0
 OR data.ddo_field(data.ddo_field(cue,'body'),'pin') IS DISTINCT FROM data.ddo_field(data.ddo_field(query_row,'body'),'source_pin')
 OR data.ddo_field(data.ddo_field(cue,'body'),'occurrence_id') IS NULL
 OR jsonb_array_length(coalesce(data.ddo_json(data.ddo_field(data.ddo_field(cue,'body'),'anchors')),'[]'))=0
 OR EXISTS(SELECT FROM jsonb_array_elements(data.ddo_json(data.ddo_field(data.ddo_field(cue,'body'),'anchors'))) anchor
 WHERE anchor->>'precision' IS DISTINCT FROM 'exact' OR anchor->>'space' IS DISTINCT FROM 'native'
 OR anchor->'pin' IS DISTINCT FROM query_->'source_pin')
 OR (ops.ddo_contextual_input_reference(cue,true)=carrier_ AND
 ops.ddo_rich_support_population(data.ddo_json(data.ddo_field(cue,'support'))) IS DISTINCT FROM
 ops.ddo_rich_support_population(data.ddo_json(data.ddo_field(original_occurrence,'support')))) THEN
 RAISE EXCEPTION 'contextual witness cue differs from actual original parent/source/anchors' USING ERRCODE='23514'; END IF;
 FOR reference_ IN SELECT value FROM jsonb_array_elements(data.ddo_json(data.ddo_field(cue,'support'))) LOOP
 IF reference_->>'kind' IS DISTINCT FROM 'computation' OR NOT EXISTS(SELECT FROM ops.data_derivation producer
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=producer.id AND receipt.intent_id=producer.intent_id
 JOIN ops.data_derivation_output output ON output.derivation_id=producer.id
 WHERE producer.id=reference_->>'derivation_id' AND producer.outcome='success'
 AND output.product_id=data.ddo_field(cue,'product_id')->>1
 AND (output.member_id IS NULL OR output.member_id=data.ddo_field(cue,'member_id')->>1)) THEN
 RAISE EXCEPTION 'contextual witness cue lacks its actual original producer/common receipt' USING ERRCODE='23514'; END IF;
 END LOOP;
 actual_refs:=actual_refs||jsonb_build_array(ops.ddo_contextual_input_reference(cue,true));
 END LOOP;
 IF NOT actual_refs @> jsonb_build_array(carrier_) THEN
 RAISE EXCEPTION 'contextual witness omits its exact qualifying query carrier' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(data.ddo_json(data.ddo_field(hypothesis_row,'support'))) reference WHERE reference->>'kind'='authored') THEN
 RAISE EXCEPTION 'contextual witness lacks admitted authored hypotheses' USING ERRCODE='23514'; END IF;
 FOR reference_ IN SELECT value FROM jsonb_array_elements(data.ddo_json(data.ddo_field(hypothesis_row,'support'))) LOOP
 SELECT * INTO STRICT admission FROM ops.original_source_admission WHERE id=reference_->>'admission_id'
 AND source_reference=reference_->>'source_reference' AND product_id=data.ddo_field(hypothesis_row,'product_id')->>1;
 IF reference_->>'kind' IS DISTINCT FROM 'authored' OR admission.reference->>'kind' IS DISTINCT FROM 'authored-fact'
 OR admission.reference->>'author' IS DISTINCT FROM hypotheses->>'author_assertion'
 OR data.ddo_normalize(admission.reference->'meaning_body') IS DISTINCT FROM data.ddo_field(hypothesis_row,'body') THEN
 RAISE EXCEPTION 'contextual witness author assertion differs from original authored admission' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR assertion_ IN SELECT value FROM jsonb_array_elements(hypotheses->'hypotheses') LOOP
 IF NOT (assertion_->'cue_refs') @> jsonb_build_array(carrier_)
 OR EXISTS(SELECT FROM jsonb_array_elements(assertion_->'cue_refs') cited WHERE NOT actual_refs @> jsonb_build_array(cited))
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(inventory_->'targets') target
 WHERE (target->>'target_id') COLLATE "C"=(assertion_->>'target_id') COLLATE "C") THEN
 RAISE EXCEPTION 'contextual witness assertion differs from exact carrier/cues/selected target' USING ERRCODE='23514'; END IF;
 END LOOP;
END $witness$;
REVOKE ALL ON FUNCTION ops.ddo_contextual_input_reference(jsonb,boolean),
 ops.ddo_contextual_witness_inputs(ops.data_request,jsonb) FROM PUBLIC;
"""
