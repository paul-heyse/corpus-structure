-- Numeric product identity shares the native_float64 spelling used by PDF custody.
CREATE OR REPLACE FUNCTION ops.contextual_identity_value(p jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb;
BEGIN
 CASE jsonb_typeof(p)
 WHEN 'number' THEN RETURN jsonb_build_object('native_float64',encode(float8send((p#>>'{}')::double precision),'hex'));
 WHEN 'array' THEN SELECT COALESCE(jsonb_agg(ops.contextual_identity_value(value) ORDER BY n),'[]') INTO result
  FROM jsonb_array_elements(p) WITH ORDINALITY a(value,n); RETURN result;
 WHEN 'object' THEN SELECT COALESCE(jsonb_object_agg(key,ops.contextual_identity_value(value)),'{}') INTO result
  FROM jsonb_each(p); RETURN result;
 ELSE RETURN p;
 END CASE;
END $$;
REVOKE ALL ON FUNCTION ops.contextual_identity_value(jsonb) FROM PUBLIC;

-- Restore explicit optional nulls used by typed decision identity.
CREATE OR REPLACE FUNCTION ops.contextual_nullable_value(p jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb;
BEGIN
 IF jsonb_typeof(p)='array' THEN SELECT COALESCE(jsonb_agg(ops.contextual_nullable_value(value) ORDER BY n),'[]') INTO result FROM jsonb_array_elements(p) WITH ORDINALITY x(value,n); RETURN result;
 ELSIF jsonb_typeof(p)='object' THEN
  SELECT COALESCE(jsonb_object_agg(key,ops.contextual_nullable_value(value)),'{}') INTO result FROM jsonb_each(p);
  IF p ? 'witness_id' THEN result:=result||jsonb_build_object('effective_version',p->'effective_version'); END IF;
  RETURN result;
 END IF;
 RETURN p;
END $$;
REVOKE ALL ON FUNCTION ops.contextual_nullable_value(jsonb) FROM PUBLIC;

-- Replay question-relative selection from the complete witnessed input population.
CREATE OR REPLACE FUNCTION ops.validate_contextual_selection(d jsonb,candidates jsonb,inventory jsonb) RETURNS void
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE question jsonb; edges jsonb; edge jsonb; selected jsonb:='[]'; groups jsonb:='[]'; unresolved jsonb:='[]'; expected text; actual_pairs jsonb;
BEGIN
 IF jsonb_array_length(d->'constraints')=0 OR EXISTS(SELECT FROM jsonb_array_elements(d->'constraints') q GROUP BY q->>'constraint_id' HAVING count(*)>1)
 OR EXISTS(SELECT FROM jsonb_array_elements(d->'constraints') q,LATERAL jsonb_array_elements_text(q->'relation_kinds') k GROUP BY k HAVING count(*)>1)
 OR EXISTS(SELECT FROM jsonb_array_elements(d->'witnesses') w GROUP BY w->>'witness_id' HAVING count(*)>1)
 OR EXISTS(SELECT FROM jsonb_array_elements(d->'witnesses') w WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(d->'constraints') q WHERE q->'relation_kinds' ? (w->>'relation'))) THEN
  RAISE EXCEPTION 'relationship question ownership or witness population invalid' USING ERRCODE='23514'; END IF;
 FOR question IN SELECT value FROM jsonb_array_elements(d->'constraints') ORDER BY value->>'constraint_id' LOOP
  WITH eligible AS (
   SELECT w,g->>'target_id' semantic_target FROM jsonb_array_elements(d->'witnesses') w JOIN LATERAL jsonb_array_elements(inventory->'semantic_groups') g ON g->'member_target_ids' ? (w->>'target_id') WHERE question->'relation_kinds' ? (w->>'relation')
   AND w->>'support_state' NOT IN ('unsupported','ambiguous') AND w->>'occurrence_id'<>w->>'target_id'
   AND NOT (w->>'relation' IN ('denotes','alias-of') AND EXISTS(SELECT FROM jsonb_array_elements(d->'exclusions') ex WHERE
    (ex->>'left'=w->>'occurrence_id' AND ex->>'right'=w->>'target_id') OR (ex->>'right'=w->>'occurrence_id' AND ex->>'left'=w->>'target_id')))
   AND NOT (d->>'effective_version' IS NULL AND EXISTS(SELECT FROM jsonb_array_elements(inventory->'targets') target WHERE target->>'target_id'=w->>'target_id' AND target->>'effective_version' IS NOT NULL))
  ), pair AS (
   SELECT semantic_target target_id,w->>'relation' relation,jsonb_agg(w ORDER BY w->>'witness_id') witnesses,jsonb_agg(DISTINCT w->>'target_id' ORDER BY w->>'target_id') members FROM eligible GROUP BY semantic_target,w->>'relation'
  ), meanings AS (
   SELECT target_id,relation,jsonb_build_object('constraint_id',question->>'constraint_id','occurrence_id',d->>'occurrence_id','target_id',target_id,'relation',relation,'selection',CASE WHEN (question->>'exhaustive')::boolean THEN 'forced' ELSE 'preferred' END) meaning,witnesses,members FROM pair
  ) SELECT COALESCE(jsonb_agg(meaning||jsonb_build_object('witnesses',witnesses,'member_target_ids',members,'edge_id','scoped-edge:'||encode(sha256(convert_to(data.canonical_json(ops.contextual_nullable_value(meaning)),'UTF8')),'hex')) ORDER BY target_id,relation),'[]') INTO edges FROM meanings;
  IF jsonb_array_length(edges)=0 OR (question->>'multiplicity'='one' AND jsonb_array_length(edges)>1) THEN unresolved:=unresolved||jsonb_build_array(question->>'constraint_id'); END IF;
  IF question->>'multiplicity'='one' AND jsonb_array_length(edges)>1 THEN
   groups:=groups||jsonb_build_array(jsonb_build_object('constraint_id',question->>'constraint_id','edges',edges,'reason','competing senses under declared exclusive constraint'));
  ELSE selected:=selected||edges; END IF;
 END LOOP;
 IF d->'unresolved_constraints' IS DISTINCT FROM unresolved THEN RAISE EXCEPTION 'unresolved constraints differ from eligible edge population' USING ERRCODE='23514'; END IF;
 IF jsonb_strip_nulls(d->'selected_edges') IS DISTINCT FROM jsonb_strip_nulls(selected) OR jsonb_strip_nulls(d->'alternative_groups') IS DISTINCT FROM jsonb_strip_nulls(groups) THEN
  RAISE EXCEPTION 'selected edges or alternatives differ from exact question replay' USING ERRCODE='23514'; END IF;
 expected:=CASE WHEN jsonb_array_length(selected)>0 THEN CASE WHEN jsonb_array_length(unresolved)>0 THEN 'partial' ELSE 'selected' END WHEN jsonb_array_length(groups)>0 THEN 'ambiguous' WHEN d ? 'proposal' THEN d->'proposal'->>'kind' ELSE 'insufficient_evidence' END;
 IF d->>'outcome' IS DISTINCT FROM expected OR ((jsonb_array_length(selected)>0 OR jsonb_array_length(groups)>0) AND d ? 'proposal') THEN
  RAISE EXCEPTION 'decision outcome differs from question-relative selection' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION ops.validate_contextual_selection(jsonb,jsonb,jsonb) FROM PUBLIC;

-- Independent source contributions share existing task/report and source custody.
CREATE OR REPLACE FUNCTION ops.source_contribution_occurrence(p_anchors jsonb)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT 'source-occurrence:'||encode(sha256(convert_to(data.canonical_json(COALESCE(
  jsonb_agg((a-'anchor_id'-'binding'-'pin')||jsonb_build_object('pin',jsonb_build_object('product_key',a->'pin'->'product_key','product_digest',a->'pin'->'product_digest')) ORDER BY n),'[]')),'UTF8')),'hex')
 FROM jsonb_array_elements(p_anchors) WITH ORDINALITY x(a,n)
$$;
REVOKE ALL ON FUNCTION ops.source_contribution_occurrence(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_source_contribution_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; v kb.source_view; shape json; op jsonb; contribution jsonb; anchor_ jsonb; ep jsonb;
 anchors jsonb; identities text[]; expected text; previous_ends jsonb; coordinate text; actual bigint;
 declaration json; role_definition jsonb; retained ops.task; binding jsonb; old_view kb.source_view; new_view kb.source_view; old_descriptor jsonb; new_descriptor jsonb; retained_body jsonb; retained_digests jsonb:='{}'; retained_sources jsonb:='{}';
 operation_map jsonb; identity_map jsonb; output_counts jsonb; schemas jsonb:='{}'; allowed_contracts jsonb;
 local_ jsonb; local_request jsonb; local_result jsonb; selected_ids jsonb; local_inputs jsonb;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 PERFORM sem.require_execution_operation(t.release_id,'bind_report');
 SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact
 WHERE release_id=t.release_id AND artifact_name='json_schema/SourceObservationBatch';
 IF shape IS NULL OR NOT public.json_matches_schema(shape,p_envelope::json)
  OR NOT p_envelope ? 'contribution_operations' OR NOT p_envelope ? 'contributions'
  OR jsonb_typeof(p_envelope->'contribution_operations') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_envelope->'contributions') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'contribution report differs from released explicit population shape' USING ERRCODE='23514'; END IF;
 IF t.unit_type<>'source_view' OR p_envelope->>'release_id' IS DISTINCT FROM t.release_id
  OR p_envelope->>'unit_key' IS DISTINCT FROM t.unit_key
  OR p_envelope->>'invocation_key' IS DISTINCT FROM t.invocation_key
  OR p_envelope->>'input_hash' IS DISTINCT FROM t.input_hash
  OR NOT EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
   WHERE cfg.id=t.method_config_id AND cfg.config_hash=p_envelope->>'configuration_hash'
    AND m.name=p_envelope->>'method' AND m.version=p_envelope->>'operation_version') THEN
  RAISE EXCEPTION 'contribution report differs from producing task binding' USING ERRCODE='23514'; END IF;
 IF t.status<>'running' AND NOT EXISTS(SELECT FROM ops.task_result WHERE task_id=t.id AND body=p_envelope) THEN
  RAISE EXCEPTION 'contribution report differs from immutable origin result' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=t.unit_id;
 IF p_envelope->>'source' IS NULL OR p_envelope->>'source' NOT IN (t.unit_key,v.key) THEN
  RAISE EXCEPTION 'contribution source differs from selected task/view' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*)<>count(DISTINCT o->>'operation_key') FROM jsonb_array_elements(p_envelope->'contribution_operations') o) THEN
  RAISE EXCEPTION 'duplicate contribution operation identity' USING ERRCODE='23514'; END IF;
 SELECT array_agg(x->>'contribution_id') INTO identities FROM jsonb_array_elements(p_envelope->'contributions') x;
 IF cardinality(identities) IS DISTINCT FROM (SELECT count(DISTINCT x) FROM unnest(identities) x)
  AND cardinality(identities)>0 THEN RAISE EXCEPTION 'duplicate contribution identity' USING ERRCODE='23514'; END IF;
 SELECT jsonb_object_agg(o->>'operation_key',o) INTO operation_map FROM jsonb_array_elements(p_envelope->'contribution_operations') o;
 SELECT COALESCE(jsonb_object_agg(c->>'contribution_id',true),'{}') INTO identity_map FROM jsonb_array_elements(p_envelope->'contributions') c;
 SELECT COALESCE(jsonb_object_agg(key,n),'{}') INTO output_counts FROM (
  SELECT c->>'operation_key' AS key,count(*) AS n FROM jsonb_array_elements(p_envelope->'contributions') c GROUP BY c->>'operation_key') counts;
 SELECT convert_from(content,'UTF8')::jsonb->'contracts' INTO allowed_contracts FROM sem.artifact
  WHERE release_id=t.release_id AND artifact_name='contribution_projection.json';
 FOR op IN SELECT DISTINCT jsonb_build_object('retained_task_id',o->'retained_task_id',
  'retained_result_digest',o->'retained_result_digest','retained_source_bindings',o->'retained_source_bindings')
  FROM jsonb_array_elements(p_envelope->'contribution_operations') o
  WHERE o ? 'retained_task_id' OR o ? 'retained_result_digest' OR o ? 'retained_source_bindings' LOOP
   IF NOT (op ? 'retained_task_id' AND op ? 'retained_result_digest' AND op ? 'retained_source_bindings')
    OR jsonb_array_length(op->'retained_source_bindings')=0 THEN
    RAISE EXCEPTION 'retained operation lacks complete immutable source lineage' USING ERRCODE='23514'; END IF;
   SELECT * INTO STRICT retained FROM ops.task WHERE id=(op->>'retained_task_id')::bigint;
   IF NOT retained_digests ? retained.id::text THEN
    SELECT body INTO STRICT retained_body FROM ops.task_result WHERE task_id=retained.id;
    retained_digests:=retained_digests||jsonb_build_object(retained.id::text,
     encode(sha256(convert_to(data.canonical_json(retained_body),'UTF8')),'hex'));
    retained_sources:=retained_sources||jsonb_build_object(retained.id::text,retained_body->>'source');
   END IF;
   IF retained.status NOT IN ('done','empty','failed') OR retained.reused_task_id IS NOT NULL
    OR NOT EXISTS(SELECT FROM ops.run a JOIN ops.run b ON a.project_id=b.project_id
     WHERE a.id=retained.run_id AND b.id=t.run_id)
    OR retained_digests->>retained.id::text IS DISTINCT FROM op->>'retained_result_digest' THEN
    RAISE EXCEPTION 'retained operation task/result identity differs from immutable source' USING ERRCODE='23514'; END IF;
   FOR binding IN SELECT value FROM jsonb_array_elements(op->'retained_source_bindings') LOOP
    SELECT * INTO STRICT old_view FROM kb.source_view WHERE id=(binding->>'original_source_view_id')::bigint;
    SELECT * INTO STRICT new_view FROM kb.source_view WHERE id=(binding->>'current_source_view_id')::bigint;
    old_descriptor:=jsonb_build_object('document_id',old_view.document_id,'native_task_id',old_view.native_task_id,'native_product_key',old_view.native_product_key,'native_content_digest',old_view.native_content_digest,'section_pointer',old_view.section_pointer,'membership',old_view.membership,'projection_digest',old_view.projection_digest,'recipe_digest',old_view.recipe_digest,'analysis_eligible',old_view.analysis_eligible,'projection',old_view.projection);
    new_descriptor:=jsonb_build_object('document_id',new_view.document_id,'native_task_id',new_view.native_task_id,'native_product_key',new_view.native_product_key,'native_content_digest',new_view.native_content_digest,'section_pointer',new_view.section_pointer,'membership',new_view.membership,'projection_digest',new_view.projection_digest,'recipe_digest',new_view.recipe_digest,'analysis_eligible',new_view.analysis_eligible,'projection',new_view.projection);
    IF old_descriptor IS DISTINCT FROM new_descriptor
     OR encode(sha256(convert_to(data.canonical_json(old_descriptor),'UTF8')),'hex') IS DISTINCT FROM binding->>'physical_digest'
     OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=retained.run_id AND source_view_id=old_view.id)
     OR NOT EXISTS(SELECT FROM ops.run_source_view WHERE run_id=t.run_id AND source_view_id=new_view.id)
     OR binding->>'original_source' IS DISTINCT FROM (CASE WHEN old_view.id=retained.unit_id THEN retained_sources->>retained.id::text ELSE old_view.key END)
     OR binding->>'current_source' IS DISTINCT FROM (CASE WHEN new_view.id=t.unit_id THEN p_envelope->>'source' ELSE new_view.key END) THEN
     RAISE EXCEPTION 'retained operation source correspondence differs from selected physical custody' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(op->'retained_source_bindings') b
    WHERE (b->>'original_source_view_id')::bigint=retained.unit_id
     AND (b->>'current_source_view_id')::bigint=t.unit_id) THEN
    RAISE EXCEPTION 'retained operation lacks primary source correspondence' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR op IN SELECT value FROM jsonb_array_elements(p_envelope->'contribution_operations') LOOP
  IF op ? 'local_interpretation' THEN
   local_:=op->'local_interpretation'; selected_ids:=COALESCE(local_->'contribution_ids','[]');
   IF local_->>'seal' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(local_-'seal'),'UTF8')),'hex')
    OR local_->>'constraint_id' IS DISTINCT FROM op->>'operation_key'
    OR (local_->>'coupling_enabled')::boolean IS DISTINCT FROM false
    OR jsonb_array_length(selected_ids)<>(SELECT count(DISTINCT id) FROM jsonb_array_elements_text(selected_ids) x(id))
    OR EXISTS(SELECT FROM jsonb_array_elements_text(selected_ids) x(id) WHERE NOT identity_map ? id)
    OR jsonb_array_length(local_->'dependencies')=0
    OR EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') c,
     LATERAL jsonb_array_elements_text(COALESCE(c->'computation_dependencies','[]')) dep(id)
     WHERE selected_ids ? (c->>'contribution_id') AND NOT (local_->'dependencies') ? dep.id)
    OR (op->>'inspected_count')::bigint<>jsonb_array_length(selected_ids)
    OR (op->>'emitted_count')::bigint<>0
    OR jsonb_array_length(local_->'dependencies')<>(SELECT count(DISTINCT id) FROM jsonb_array_elements_text(local_->'dependencies') x(id))
    OR EXISTS(SELECT FROM jsonb_array_elements_text(local_->'dependencies') x(id)
     WHERE NOT COALESCE(op->'computation_dependencies','[]') ? id) THEN
    RAISE EXCEPTION 'local interpretation input/operation custody differs' USING ERRCODE='23514'; END IF;
   SELECT COALESCE(jsonb_agg(c ORDER BY c->>'contribution_id'),'[]') INTO local_inputs
    FROM jsonb_array_elements(p_envelope->'contributions') c WHERE selected_ids ? (c->>'contribution_id');
   IF local_->>'retained_input_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(local_inputs),'UTF8')),'hex') THEN
    RAISE EXCEPTION 'local interpretation input digest differs from retained contributions' USING ERRCODE='23514'; END IF;
   IF local_->>'outcome'='not_run' THEN
    IF op->>'outcome'<>'not_run' OR local_->>'probability_standing'<>'not_computed'
     OR local_ ?| ARRAY['request','result','request_digest','result_digest'] THEN
     RAISE EXCEPTION 'unrun local interpretation cannot carry computed probabilities' USING ERRCODE='23514'; END IF;
   ELSE
    IF NOT local_ ?& ARRAY['request','result','request_digest','result_digest']
     OR local_->>'request_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(local_->'request'),'UTF8')),'hex')
     OR local_->>'result_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(local_->'result'),'UTF8')),'hex') THEN
     RAISE EXCEPTION 'local interpretation request/result custody differs' USING ERRCODE='23514'; END IF;
    local_request:=data.record_source_json(local_->'request'); local_result:=data.record_source_json(local_->'result');
    IF local_request->'selection'->>'scope_id' IS DISTINCT FROM local_->>'constraint_id'
     OR EXISTS(SELECT FROM jsonb_array_elements_text(local_->'dependencies') x(id)
      WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(local_request->'dependencies') d WHERE d->>'key'=id))
     OR local_result->>'outcome' IS DISTINCT FROM local_->>'outcome'
     OR local_->>'probability_standing' IS DISTINCT FROM local_result->>'probability_standing'
     OR op->>'outcome' IS DISTINCT FROM (CASE local_->>'outcome' WHEN 'completed' THEN 'succeeded' WHEN 'resource_limit' THEN 'limited' ELSE 'failed' END)
     OR (local_->>'outcome'<>'completed' AND (
      jsonb_array_length(COALESCE(local_result->'marginals','[]'))>0
      OR jsonb_array_length(COALESCE(local_result->'event_probabilities','[]'))>0
      OR jsonb_array_length(COALESCE(local_result->'alternatives','[]'))>0
      OR COALESCE(local_result->'log_partition','null')<>'null')) THEN
     RAISE EXCEPTION 'local interpretation scope/outcome differs from actual result' USING ERRCODE='23514'; END IF;
   END IF;
  END IF;
  actual:=COALESCE((output_counts->>(op->>'operation_key'))::bigint,0);
  IF actual<>(op->>'emitted_count')::bigint OR (actual>0 AND op->>'outcome' IN ('empty','failed','skipped','unsupported','not_run'))
   OR (op->>'outcome' IN ('failed','skipped','unsupported','limited','not_run') AND COALESCE(op->>'reason','')='') THEN
   RAISE EXCEPTION 'operation outcome or cardinality differs from actual contribution population' USING ERRCODE='23514'; END IF;
 END LOOP;
 -- Projected definition terms retain exactly their authenticated component role/location.
 FOR contribution IN SELECT value FROM jsonb_array_elements(p_envelope->'contributions')
  WHERE value->>'semantic_type'='definition.term' AND (p_envelope->>'method'='locate.definition_terms'
   OR data.record_source_json(value->'value') ? 'component_reference') LOOP
  DECLARE meaning jsonb:=data.record_source_json(contribution->'value'); original jsonb; component jsonb; passage jsonb; expected_anchors jsonb; observed_anchors jsonb;
  BEGIN
   binding:=meaning->'component_reference'; original:=ops.resolve_retained_component(binding); component:=original->'component';
   SELECT p INTO STRICT passage FROM jsonb_array_elements(original->'report'->'inputs'->'passages') p WHERE p->>'passage_id'=component->'term'->>'passage_id';
   IF p_envelope->>'method'<>'locate.definition_terms' OR contribution->>'kind'<>'occurrence' OR meaning->>'role'<>'defined_term'
    OR meaning-ARRAY['role','component_reference']<>'{}' OR NOT EXISTS(SELECT FROM ops.method_config cfg WHERE cfg.id=t.method_config_id AND cfg.params->'component_refs' @> jsonb_build_array(binding)
     AND cfg.params->>'source_product_digest'=v.native_content_digest AND cfg.params->>'source_projection_digest'=v.projection_digest)
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(original->'report'->'inputs'->'sources') src WHERE (src->>'source_view_id')::bigint=v.id AND encode(sha256(convert_to(data.canonical_json(src),'UTF8')),'hex')=passage->>'source_ref')
    OR contribution->'computation_dependencies' IS DISTINCT FROM jsonb_build_array(binding->>'product_id',binding->>'component_id','retained-component:'||encode(sha256(convert_to(data.canonical_json(binding),'UTF8')),'hex')) THEN
    RAISE EXCEPTION 'definition term differs from retained component and producing configuration' USING ERRCODE='23514'; END IF;
   SELECT jsonb_agg(jsonb_build_object('pointer',p->>'item_ref'||CASE WHEN p->>'source_field'='cell_text' THEN '/data/table_cells/'||(p->>'cell_index') ELSE '' END,
    'start',greatest((component->'term'->>'start')::bigint,(p->>'start')::bigint)-(p->>'start')::bigint,
    'end',least((component->'term'->>'end')::bigint,(p->>'end')::bigint)-(p->>'start')::bigint,
    'source_piece',substring(v.projection->>'text' FROM greatest((component->'term'->>'start')::integer,(p->>'start')::integer)+1 FOR least((component->'term'->>'end')::integer,(p->>'end')::integer)-greatest((component->'term'->>'start')::integer,(p->>'start')::integer))) ORDER BY p->>'item_ref',greatest((component->'term'->>'start')::bigint,(p->>'start')::bigint)-(p->>'start')::bigint)
    INTO expected_anchors FROM jsonb_array_elements(v.projection->'pieces') p WHERE p->>'kind'='native_text' AND (p->>'start')::bigint<(component->'term'->>'end')::bigint AND (p->>'end')::bigint>(component->'term'->>'start')::bigint;
   SELECT jsonb_agg(jsonb_build_object('pointer',a->'pointer','start',a->'start','end',a->'end','source_piece',a->'source_piece') ORDER BY a->>'pointer',(a->>'start')::bigint,(a->>'end')::bigint)
    INTO observed_anchors FROM jsonb_array_elements(contribution->'anchors') a;
   IF expected_anchors IS NULL OR expected_anchors IS DISTINCT FROM observed_anchors THEN
    RAISE EXCEPTION 'definition term location differs from original component source pieces' USING ERRCODE='23514'; END IF;
  END;
 END LOOP;
 -- Located mentions preserve the selected producer's source anchors and semantic role.
 FOR contribution IN SELECT value FROM jsonb_array_elements(p_envelope->'contributions') WHERE value->>'semantic_type'='contextual.located_mention' LOOP
  SELECT cc INTO STRICT retained_body FROM ops.task producer JOIN ops.method_config cfg ON cfg.id=producer.method_config_id
   JOIN ops.method method ON method.id=cfg.method_id JOIN ops.task origin ON origin.id=COALESCE(producer.reused_task_id,producer.id)
   JOIN ops.task_result result ON result.task_id=origin.id
   CROSS JOIN LATERAL jsonb_array_elements(result.body->'contributions') cc
   WHERE producer.run_id=t.run_id AND producer.unit_id=t.unit_id AND producer.unit_type=t.unit_type AND producer.status IN ('done','reused')
   AND method.name=(SELECT params->>'source_dependency_method' FROM ops.method_config WHERE id=t.method_config_id)
   AND cc->>'contribution_id'=contribution->'computation_dependencies'->>0;
  IF contribution->'anchors' IS DISTINCT FROM retained_body->'anchors' OR contribution->'pin' IS DISTINCT FROM retained_body->'pin'
   OR contribution->>'occurrence_id' IS DISTINCT FROM retained_body->>'occurrence_id'
   OR contribution->'computation_dependencies'->>1 IS DISTINCT FROM retained_body->>'operation_key'
   OR data.record_source_json(contribution->'value') IS DISTINCT FROM jsonb_build_object('producer_semantic_type',retained_body->'semantic_type','producer_component',retained_body->'component','producer_value',retained_body->'value') THEN
   RAISE EXCEPTION 'located mention differs from selected producer source and role' USING ERRCODE='23514'; END IF;
 END LOOP;
 -- Contextual reports remain private, source-bound operation products.
 FOR op IN SELECT value FROM jsonb_array_elements(p_envelope->'contribution_operations') LOOP
  IF NOT op ? 'contextual_enrichment' THEN CONTINUE; END IF;
  DECLARE report jsonb:=op->'contextual_enrichment'; profile jsonb; vec jsonb; inv jsonb;
   candidate_list jsonb; candidate jsonb; decision jsonb; witness jsonb; target_product jsonb;
   profile_map jsonb; vector_map jsonb; inventory_map jsonb; list_map jsonb; expected text; expected_candidates jsonb; normalized_target jsonb; channel_report jsonb; expected_hits jsonb; registry_id text; registry_targets jsonb; reuse_row jsonb; reuse_task ops.task; reuse_run ops.run; current_runtime text;
   reuse_digests jsonb:='{}'; reuse_values jsonb:='{}'; origin_body jsonb; origin_vectors jsonb; meaning_group jsonb; member_id text; expected_meaning jsonb;
  BEGIN
   IF EXISTS(SELECT FROM jsonb_each(report->'product_counts') product_count
      WHERE (product_count.value#>>'{}')::integer<>jsonb_array_length(report->product_count.key)) THEN
    RAISE EXCEPTION 'contextual product counts differ from actual typed populations' USING ERRCODE='23514'; END IF;
   IF jsonb_array_length(COALESCE(report->'component_targets','[]'))>0 THEN
    PERFORM ops.validate_component_targets(report->'component_targets');
   END IF;
   IF p_envelope->>'method'='retrieve.contextual' AND jsonb_strip_nulls(report->'component_targets') IS DISTINCT FROM
    (SELECT jsonb_strip_nulls(params->'target_components') FROM ops.method_config WHERE id=t.method_config_id) THEN
    RAISE EXCEPTION 'contextual source targets differ from complete frozen input population' USING ERRCODE='23514'; END IF;
   registry_id:=NULL; registry_targets:='[]'::jsonb;
   IF (EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
        WHERE cfg.id=t.method_config_id AND (cfg.params ? 'registry_targets' OR m.name='retrieve.contextual'))
        OR jsonb_array_length(report->'inventories')>0) AND NOT report ? 'curated_registry_id' AND jsonb_array_length(COALESCE(report->'component_targets','[]'))=0 THEN
    RAISE EXCEPTION 'contextual target input requires its registered curated registry custody' USING ERRCODE='23514'; END IF;
   IF report ? 'curated_registry_id' THEN
    SELECT COALESCE(jsonb_agg(jsonb_build_object('target_id',x->'target_id','label',x->'label',
     'description',x->'description','aliases',COALESCE(x->'aliases','[]'),
     'type_name',x->'type_name','parent',x->'parent','scope',COALESCE(x->'scope','"global"'),
     'effective_version',x->'effective_version') ORDER BY x->>'target_id'),'[]') INTO registry_targets
    FROM ops.method_config cfg CROSS JOIN LATERAL jsonb_array_elements(cfg.params->'registry_targets') x
    WHERE cfg.id=t.method_config_id;
    registry_id:='curated-registry:'||encode(sha256(convert_to(data.canonical_json(registry_targets),'UTF8')),'hex');
    IF jsonb_array_length(registry_targets)=0 OR report->>'curated_registry_id' IS DISTINCT FROM registry_id
     OR (SELECT count(*)<>count(DISTINCT r->>'target_id') FROM jsonb_array_elements(registry_targets) r) THEN
     RAISE EXCEPTION 'curated registry differs from immutable producing configuration input' USING ERRCODE='23514'; END IF;
   END IF;
   SELECT COALESCE(jsonb_object_agg(p->>'profile_id',p),'{}') INTO profile_map
    FROM jsonb_array_elements(report->'profiles') p;
   SELECT COALESCE(jsonb_object_agg(x->>'vector_id',x),'{}') INTO vector_map
    FROM jsonb_array_elements(report->'vectors') x;
   SELECT COALESCE(jsonb_object_agg(x->>'inventory_id',x),'{}') INTO inventory_map
    FROM jsonb_array_elements(report->'inventories') x;
   SELECT COALESCE(jsonb_object_agg(x->>'list_id',x),'{}') INTO list_map
    FROM jsonb_array_elements(report->'candidate_lists') x;
   IF (SELECT count(*) FROM jsonb_object_keys(profile_map))<>jsonb_array_length(report->'profiles')
    OR (SELECT count(*) FROM jsonb_object_keys(vector_map))<>jsonb_array_length(report->'vectors')
    OR (SELECT count(*) FROM jsonb_object_keys(inventory_map))<>jsonb_array_length(report->'inventories')
    OR (SELECT count(*) FROM jsonb_object_keys(list_map))<>jsonb_array_length(report->'candidate_lists') THEN
    RAISE EXCEPTION 'duplicate contextual product identity' USING ERRCODE='23514'; END IF;
   FOR profile IN SELECT value FROM jsonb_array_elements(report->'profiles') LOOP
    expected:='encoder-profile:'||encode(sha256(convert_to(data.canonical_json(
     profile-'profile_id'-'max_items'-'max_input_bytes'-'timeout_seconds'),'UTF8')),'hex');
    IF profile->>'profile_id' IS DISTINCT FROM expected THEN
     RAISE EXCEPTION 'contextual profile identity differs from meaning' USING ERRCODE='23514'; END IF;
   END LOOP;
   FOR vec IN SELECT value FROM jsonb_array_elements(report->'vectors') LOOP
    profile:=profile_map->(vec->>'profile_id');
    expected:='context-vector:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
     vec->>'object_id',vec->>'source_binding',vec->>'profile_id',vec->>'input_digest',vec->>'representation_digest')),'UTF8')),'hex');
    IF profile IS NULL OR vec->>'vector_id' IS DISTINCT FROM expected
     OR (vec->>'source_binding' IS DISTINCT FROM p_envelope->>'source' AND NOT EXISTS(
      SELECT FROM jsonb_array_elements(registry_targets) rt WHERE rt->>'target_id'=vec->>'object_id'
       AND vec->>'source_binding'='curated-target:'||encode(sha256(convert_to(data.canonical_json(rt),'UTF8')),'hex')) AND NOT EXISTS(SELECT FROM jsonb_array_elements(COALESCE(report->'component_targets','[]')) ct WHERE ct->'reference'->>'component_id'=vec->>'object_id' AND vec->>'source_binding'='definition-component:'||encode(sha256(convert_to(data.canonical_json(ct->'reference'),'UTF8')),'hex')))
     OR public.vector_dims((vec->'values')::text::public.vector)<>(profile->>'dimension')::integer
     OR abs(public.vector_norm((vec->'values')::text::public.vector)-1)>0.00001 THEN
     RAISE EXCEPTION 'contextual vector profile/source/value binding differs' USING ERRCODE='23514'; END IF;
   END LOOP;
   SELECT runtime_id INTO current_runtime FROM ops.run WHERE id=t.run_id;
   IF (SELECT count(*)<>count(DISTINCT r->>'vector_id') FROM jsonb_array_elements(COALESCE(report->'vector_reuse','[]')) r) THEN
    RAISE EXCEPTION 'duplicate vector reuse identity' USING ERRCODE='23514'; END IF;
   FOR reuse_row IN SELECT value FROM jsonb_array_elements(COALESCE(report->'vector_reuse','[]')) LOOP
    SELECT * INTO reuse_task FROM ops.task WHERE id=(reuse_row->>'origin_task_id')::bigint;
    SELECT * INTO reuse_run FROM ops.run WHERE id=reuse_task.run_id;
    IF reuse_task.id IS NULL OR reuse_task.id>=t.id OR reuse_task.status NOT IN ('done','empty')
     OR reuse_task.reused_task_id IS NOT NULL OR reuse_task.release_id IS DISTINCT FROM t.release_id
     OR current_runtime IS NULL OR reuse_run.runtime_id IS DISTINCT FROM current_runtime
     OR reuse_row->>'origin_runtime_id' IS DISTINCT FROM current_runtime
     OR NOT EXISTS(SELECT FROM ops.run current_run WHERE current_run.id=t.run_id AND current_run.project_id=reuse_run.project_id)
     OR NOT vector_map ? (reuse_row->>'vector_id')
     OR vector_map->(reuse_row->>'vector_id')->>'source_binding'=p_envelope->>'source' THEN
     RAISE EXCEPTION 'vector reuse differs from original same-runtime/project target observation' USING ERRCODE='23514'; END IF;
    IF NOT reuse_digests ? reuse_task.id::text THEN
     SELECT body INTO STRICT origin_body FROM ops.task_result WHERE task_id=reuse_task.id;
     reuse_digests:=reuse_digests||jsonb_build_object(reuse_task.id::text,
      encode(sha256(convert_to(data.canonical_json(origin_body),'UTF8')),'hex'));
     SELECT COALESCE(jsonb_object_agg(vv->>'vector_id',vv),'{}') INTO origin_vectors
      FROM jsonb_array_elements(origin_body->'contribution_operations') oo,
       LATERAL jsonb_array_elements(oo->'contextual_enrichment'->'vectors') vv
      WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(COALESCE(oo->'contextual_enrichment'->'vector_reuse','[]')) rr
       WHERE rr->>'vector_id'=vv->>'vector_id');
     reuse_values:=reuse_values||jsonb_build_object(reuse_task.id::text,origin_vectors);
    END IF;
    IF reuse_digests->>reuse_task.id::text IS DISTINCT FROM reuse_row->>'result_digest'
     OR reuse_values->(reuse_task.id::text)->(reuse_row->>'vector_id') IS DISTINCT FROM vector_map->(reuse_row->>'vector_id') THEN
     RAISE EXCEPTION 'reused vector differs from immutable original report/result' USING ERRCODE='23514'; END IF;
   END LOOP;
   FOR inv IN SELECT value FROM jsonb_array_elements(report->'inventories') LOOP
    expected:='concept-inventory:'||encode(sha256(convert_to(data.canonical_json(
     jsonb_build_object('source_selection',inv->'source_selection','scope',inv->'scope',
      'effective_version',inv->'effective_version','reliable_type',inv->'reliable_type','parent',inv->'parent',
      'policy','eligible-concepts-2','semantic_groups',COALESCE((SELECT jsonb_agg(g ORDER BY g->>'target_id') FROM jsonb_array_elements(inv->'semantic_groups') g),'[]'),'targets',COALESCE((SELECT jsonb_agg(target ||
       jsonb_build_object('type_name',target->'type_name','parent',target->'parent',
        'effective_version',target->'effective_version','aliases',COALESCE(target->'aliases','[]'))
        ORDER BY target->>'target_id') FROM jsonb_array_elements(inv->'targets') target),'[]'))),'UTF8')),'hex');
    IF inv->>'inventory_id' IS DISTINCT FROM expected THEN
     RAISE EXCEPTION 'contextual inventory identity differs from eligible representations' USING ERRCODE='23514'; END IF;
    IF (SELECT count(*)<>count(DISTINCT x->>'target_id') FROM jsonb_array_elements(inv->'targets') x) THEN
     RAISE EXCEPTION 'duplicate contextual target' USING ERRCODE='23514'; END IF;
    FOR target_product IN SELECT value FROM jsonb_array_elements(inv->'targets') LOOP
     normalized_target:=target_product||jsonb_build_object('type_name',target_product->'type_name',
      'parent',target_product->'parent','effective_version',target_product->'effective_version',
      'aliases',COALESCE(target_product->'aliases','[]'));
     expected:='target-description:'||encode(sha256(convert_to(data.canonical_json(
      normalized_target-'representation_digest'),'UTF8')),'hex');
     IF target_product->>'representation_digest' IS DISTINCT FROM expected OR EXISTS(
      SELECT FROM jsonb_array_elements(report->'profiles') prof WHERE
       (SELECT count(*) FROM jsonb_array_elements(report->'vectors') v_
        WHERE v_->>'object_id'=target_product->>'target_id' AND v_->>'profile_id'=prof->>'profile_id'
         AND v_->>'representation_digest'=target_product->>'representation_digest')<>1) THEN
      RAISE EXCEPTION 'target representation differs or lacks its exact profile/vector' USING ERRCODE='23514'; END IF;
     IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(report->'component_targets','[]')) ct WHERE ct->'reference'->>'component_id'=target_product->>'target_id') THEN
      SELECT value INTO STRICT witness FROM jsonb_array_elements(report->'component_targets') ct(value) WHERE value->'reference'->>'component_id'=target_product->>'target_id';
      normalized_target:=ops.resolve_retained_component(witness->'reference')->'component';
      IF witness->>'label' IS DISTINCT FROM normalized_target->'term'->>'text' OR witness->>'description' IS DISTINCT FROM normalized_target->'content'->>'text'
       OR witness->>'scope' IS DISTINCT FROM normalized_target->>'scope' OR witness->>'effective_version' IS DISTINCT FROM normalized_target->>'effective_version'
       OR target_product->>'label' IS DISTINCT FROM witness->>'label' OR target_product->>'description' IS DISTINCT FROM witness->>'description'
       OR target_product->>'source_binding' IS DISTINCT FROM 'definition-component:'||encode(sha256(convert_to(data.canonical_json(witness->'reference'),'UTF8')),'hex') THEN
       RAISE EXCEPTION 'component target descriptor differs from authenticated located content' USING ERRCODE='23514'; END IF;
     ELSIF registry_id IS NULL OR NOT EXISTS(SELECT FROM jsonb_array_elements(registry_targets) registry_target
       WHERE registry_target=normalized_target-'source_binding'-'representation_digest'
        AND target_product->>'source_binding'='curated-target:'||encode(sha256(convert_to(data.canonical_json(registry_target),'UTF8')),'hex')) THEN
      RAISE EXCEPTION 'target lacks authenticated component custody' USING ERRCODE='23514'; END IF;
     IF (target_product->>'scope' NOT IN ('global',inv->>'scope'))
      OR (inv->>'effective_version' IS NOT NULL AND target_product->>'effective_version' IS NOT NULL
       AND target_product->>'effective_version' IS DISTINCT FROM inv->>'effective_version')
      OR (inv->>'reliable_type' IS NOT NULL AND target_product->>'type_name' IS NOT NULL
       AND target_product->>'type_name' IS DISTINCT FROM inv->>'reliable_type')
      OR (inv->>'parent' IS NOT NULL AND target_product->>'parent' IS NOT NULL
       AND target_product->>'parent' IS DISTINCT FROM inv->>'parent') THEN
      RAISE EXCEPTION 'contextual target source or eligibility differs' USING ERRCODE='23514'; END IF;
    END LOOP;
    IF (SELECT count(*)<>count(DISTINCT g->>'target_id') FROM jsonb_array_elements(inv->'semantic_groups') g)
     OR (SELECT count(*)<>count(DISTINCT m) FROM jsonb_array_elements(inv->'semantic_groups') g,LATERAL jsonb_array_elements_text(g->'member_target_ids') m)
     OR (SELECT count(*) FROM jsonb_array_elements(inv->'semantic_groups') g,LATERAL jsonb_array_elements_text(g->'member_target_ids') m)<>jsonb_array_length(inv->'targets') THEN
     RAISE EXCEPTION 'semantic target groups must partition the exact eligible population' USING ERRCODE='23514'; END IF;
    FOR meaning_group IN SELECT value FROM jsonb_array_elements(inv->'semantic_groups') LOOP
     IF meaning_group->>'target_id' IS DISTINCT FROM 'semantic-target:'||encode(sha256(convert_to(data.canonical_json(meaning_group->'meaning'),'UTF8')),'hex')
      OR jsonb_array_length(meaning_group->'member_target_ids')=0
      OR meaning_group->'member_target_ids' IS DISTINCT FROM (SELECT jsonb_agg(m ORDER BY m) FROM jsonb_array_elements(meaning_group->'member_target_ids') m) THEN
      RAISE EXCEPTION 'semantic group identity or ordered membership differs' USING ERRCODE='23514'; END IF;
     FOR member_id IN SELECT jsonb_array_elements_text(meaning_group->'member_target_ids') LOOP
      SELECT target INTO STRICT target_product FROM jsonb_array_elements(inv->'targets') target WHERE target->>'target_id'=member_id;
      IF starts_with(target_product->>'source_binding','definition-component:') THEN
       SELECT ct INTO STRICT witness FROM jsonb_array_elements(report->'component_targets') ct WHERE ct->'reference'->>'component_id'=member_id;
       expected_meaning:=ops.component_semantic_target(witness->'reference');
      ELSE expected_meaning:=jsonb_build_object('curated_target',jsonb_strip_nulls(target_product)); END IF;
      IF meaning_group->'meaning' IS DISTINCT FROM expected_meaning THEN
       RAISE EXCEPTION 'semantic target member differs from authenticated source meaning' USING ERRCODE='23514'; END IF;
     END LOOP;
    END LOOP;
   END LOOP;
   FOR candidate_list IN SELECT value FROM jsonb_array_elements(report->'candidate_lists') LOOP
    inv:=inventory_map->(candidate_list->>'inventory_id');
    vec:=vector_map->(candidate_list->>'query_vector_id');
    IF inv IS NULL OR vec IS NULL OR vec->>'profile_id' IS DISTINCT FROM candidate_list->>'profile_id'
     OR vec->>'object_id' IS DISTINCT FROM candidate_list->>'occurrence_id'
     OR vec->>'source_binding' IS DISTINCT FROM p_envelope->>'source'
     OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') c
      WHERE c->>'occurrence_id'=candidate_list->>'occurrence_id')
     OR jsonb_array_length(candidate_list->'candidates')>(candidate_list->>'unique_target_budget')::integer
     OR (candidate_list->>'eligible_target_count')::integer<>jsonb_array_length(inv->'targets')
     OR (SELECT count(*)<>count(DISTINCT x->>'target_id') FROM jsonb_array_elements(candidate_list->'candidates') x) THEN
     RAISE EXCEPTION 'candidate list differs from frozen source/inventory/vector' USING ERRCODE='23514'; END IF;
    IF candidate_list->>'policy_id'<>'exact-alias-postgresql-english-cosine-rrf60-1'
     OR (candidate_list->>'unique_target_budget')::integer>(candidate_list->>'channel_budget')::integer
     OR candidate_list->>'outcome' IS DISTINCT FROM
       (CASE jsonb_array_length(candidate_list->'candidates') WHEN 0 THEN 'empty' ELSE 'succeeded' END)
     OR (SELECT count(*)<>count(DISTINCT ch->>'channel')
      FROM jsonb_array_elements(candidate_list->'channel_results') ch)
     OR EXISTS(SELECT FROM jsonb_array_elements(candidate_list->'channel_results') ch WHERE
      jsonb_array_length(ch->'hits')>(candidate_list->>'channel_budget')::integer
      OR (SELECT count(*)<>count(DISTINCT h->>'target_id') FROM jsonb_array_elements(ch->'hits') h)
      OR EXISTS(SELECT FROM jsonb_array_elements(ch->'hits') h WHERE NOT EXISTS(
       SELECT FROM jsonb_array_elements(inv->'targets') tg WHERE tg->>'target_id'=h->>'target_id'))) THEN
     RAISE EXCEPTION 'candidate channel policy/budgets/eligible population differs' USING ERRCODE='23514'; END IF;
    FOR channel_report IN SELECT value FROM jsonb_array_elements(candidate_list->'channel_results') LOOP
     WITH target_rows AS (
      SELECT tg->>'target_id' AS id,
       concat_ws(' ',tg->>'label',tg->>'description',
        (SELECT string_agg(x,' ') FROM jsonb_array_elements_text(tg->'aliases') x)) AS search_text,
       ARRAY(SELECT lower(x) FROM (SELECT tg->>'label' AS x UNION ALL
        SELECT value FROM jsonb_array_elements_text(tg->'aliases')) forms) AS forms,
       (vv->'values')::text::public.vector AS vector
      FROM jsonb_array_elements(inv->'targets') tg,
       LATERAL jsonb_array_elements(report->'vectors') vv
      WHERE vv->>'object_id'=tg->>'target_id' AND vv->>'profile_id'=candidate_list->>'profile_id'
     ), scores AS (
      SELECT id,CASE channel_report->>'channel'
       WHEN 'dense' THEN 1-(vector OPERATOR(public.<=>) (vec->'values')::text::public.vector)
       WHEN 'alias' THEN 1::double precision
       ELSE ts_rank_cd(to_tsvector('english',search_text),
        websearch_to_tsquery('english',candidate_list->>'lexical_query'))::double precision END AS score
      FROM target_rows WHERE channel_report->>'channel'='dense'
       OR (channel_report->>'channel'='alias' AND lower(candidate_list->>'lexical_query')=ANY(forms))
       OR (channel_report->>'channel'='lexical' AND to_tsvector('english',search_text)@@
        websearch_to_tsquery('english',candidate_list->>'lexical_query'))
     ), ranked AS (SELECT id,score FROM scores ORDER BY score DESC,id
      LIMIT (candidate_list->>'channel_budget')::integer)
     SELECT COALESCE(jsonb_agg(jsonb_build_object('target_id',id,'score',score) ORDER BY score DESC,id),'[]')
      INTO expected_hits FROM ranked;
     IF jsonb_array_length(expected_hits)<>jsonb_array_length(channel_report->'hits')
      OR EXISTS(SELECT FROM jsonb_array_elements(expected_hits) WITH ORDINALITY e(value,n)
       JOIN jsonb_array_elements(channel_report->'hits') WITH ORDINALITY a(value,n) USING(n)
       WHERE e.value->>'target_id' IS DISTINCT FROM a.value->>'target_id'
        OR abs((e.value->>'score')::double precision-(a.value->>'score')::double precision)>1e-6) THEN
      RAISE EXCEPTION 'candidate channel differs from exact eligible source/vector scores' USING ERRCODE='23514'; END IF;
    END LOOP;
    WITH hits AS (
     SELECT ch->>'channel' AS channel,h,n FROM jsonb_array_elements(candidate_list->'channel_results') ch,
      LATERAL jsonb_array_elements(ch->'hits') WITH ORDINALITY x(h,n)
    ), sums AS (
     SELECT h->>'target_id' AS target_id,sum(1::double precision/(60+n) ORDER BY channel) AS score
      FROM hits GROUP BY h->>'target_id'
    ), selected AS (
     SELECT target_id,score,row_number() OVER (ORDER BY score DESC,target_id) AS rank FROM sums
      ORDER BY score DESC,target_id LIMIT (candidate_list->>'unique_target_budget')::integer
    ) SELECT COALESCE(jsonb_agg(jsonb_build_object('target_id',ss.target_id,'rank',ss.rank,
      'fusion_score',ss.score,'channels',(SELECT jsonb_agg(jsonb_build_object('channel',hits.channel,
       'rank',hits.n,'raw_score',hits.h->'score','evidence',COALESCE(hits.h->'evidence','[]')) ORDER BY hits.channel)
       FROM hits WHERE hits.h->>'target_id'=ss.target_id)) ORDER BY ss.rank),'[]')
      INTO expected_candidates FROM selected ss;
    IF jsonb_array_length(expected_candidates)<>jsonb_array_length(candidate_list->'candidates')
     OR EXISTS(SELECT FROM jsonb_array_elements(expected_candidates) WITH ORDINALITY e(value,n)
      JOIN jsonb_array_elements(candidate_list->'candidates') WITH ORDINALITY a(value,n) USING(n)
      WHERE e.value-'fusion_score' IS DISTINCT FROM a.value-'fusion_score'
       OR abs((e.value->>'fusion_score')::double precision-(a.value->>'fusion_score')::double precision)>1e-12) THEN
     RAISE EXCEPTION 'candidate ranks/fusion/channel witnesses differ from declared RRF' USING ERRCODE='23514'; END IF;
    expected:='concept-candidates:'||encode(sha256(convert_to(data.canonical_json(
     ops.contextual_identity_value(candidate_list-'list_id')),'UTF8')),'hex');
    IF candidate_list->>'list_id' IS DISTINCT FROM expected THEN
     RAISE EXCEPTION 'candidate list identity differs from full retained channels/query/policy' USING ERRCODE='23514'; END IF;
    FOR candidate IN SELECT value FROM jsonb_array_elements(candidate_list->'candidates') LOOP
     IF NOT EXISTS(SELECT FROM jsonb_array_elements(inv->'targets') target
       WHERE target->>'target_id'=candidate->>'target_id') THEN
      RAISE EXCEPTION 'candidate target outside frozen inventory' USING ERRCODE='23514'; END IF;
    END LOOP;
   END LOOP;
   FOR decision IN SELECT value FROM jsonb_array_elements(report->'relationship_decisions') LOOP
    expected:='scoped-exclusions:'||encode(sha256(convert_to(data.canonical_json(COALESCE(
     (SELECT jsonb_agg(jsonb_build_array(e->>'left',e->>'right') ORDER BY e->>'left',e->>'right')
      FROM jsonb_array_elements(decision->'exclusions') e),'[]')),'UTF8')),'hex');
    IF decision->>'exclusion_snapshot' IS DISTINCT FROM expected
     OR decision->>'source_binding' IS DISTINCT FROM p_envelope->>'source'
     OR decision->>'policy_id'<>'source-supported-scoped-links-2' THEN
     RAISE EXCEPTION 'relationship policy/source/exclusion snapshot differs' USING ERRCODE='23514'; END IF;
    expected:='scoped-relationship:'||encode(sha256(convert_to(data.canonical_json(ops.contextual_nullable_value(decision-'decision_id')||jsonb_build_object('effective_version',decision->'effective_version','proposal',CASE WHEN decision ? 'proposal' THEN ops.contextual_nullable_value(decision->'proposal') ELSE 'null'::jsonb END,'reason',decision->'reason')),'UTF8')),'hex');
    IF decision->>'decision_id' IS DISTINCT FROM expected THEN RAISE EXCEPTION 'relationship identity differs from complete question decision' USING ERRCODE='23514'; END IF;
    candidate_list:=list_map->(decision->>'candidate_list_id');
    inv:=inventory_map->(candidate_list->>'inventory_id');
    IF candidate_list IS NULL OR decision->>'occurrence_id' IS DISTINCT FROM candidate_list->>'occurrence_id'
     OR decision->>'scope' IS DISTINCT FROM inv->>'scope'
     OR decision->>'effective_version' IS DISTINCT FROM inv->>'effective_version' THEN
     RAISE EXCEPTION 'relationship differs from frozen question/scope' USING ERRCODE='23514'; END IF;
    PERFORM ops.validate_contextual_selection(decision,candidate_list,inv);
    IF decision->>'outcome' IN ('local_sense','new_concept') THEN
     witness:=decision->'proposal';
     IF witness IS NULL OR witness->>'kind' IS DISTINCT FROM decision->>'outcome'
      OR witness->>'source_binding' IS DISTINCT FROM p_envelope->>'source'
      OR witness->>'occurrence_id' IS DISTINCT FROM decision->>'occurrence_id'
      OR witness->>'inventory_id' IS DISTINCT FROM candidate_list->>'inventory_id'
      OR witness->>'scope' IS DISTINCT FROM decision->>'scope'
      OR witness->>'effective_version' IS DISTINCT FROM decision->>'effective_version'
      OR (SELECT array_agg(x ORDER BY x) FROM jsonb_array_elements_text(witness->'examined_targets') x)
       IS DISTINCT FROM (SELECT array_agg(c->>'target_id' ORDER BY c->>'target_id')
        FROM jsonb_array_elements(candidate_list->'candidates') c)
      OR EXISTS(SELECT FROM jsonb_array_elements_text(witness->'evidence_ids') e WHERE NOT identity_map ? e) THEN
      RAISE EXCEPTION 'local proposal differs from examined source/list/evidence' USING ERRCODE='23514'; END IF;
    END IF;
    FOR witness IN SELECT value FROM jsonb_array_elements(decision->'witnesses') LOOP
     IF witness->>'source_binding' IS DISTINCT FROM p_envelope->>'source'
      OR witness->>'occurrence_id' IS DISTINCT FROM decision->>'occurrence_id'
      OR witness->>'scope' IS DISTINCT FROM decision->>'scope'
      OR witness->>'effective_version' IS DISTINCT FROM decision->>'effective_version'
      OR NOT EXISTS(SELECT FROM jsonb_array_elements(candidate_list->'candidates') c
       WHERE c->>'target_id'=witness->>'target_id')
      OR witness->>'basis' NOT IN ('explicit_source_cue','producer_group','geometry','model_reading','admitted_derivation')
      OR EXISTS(SELECT FROM jsonb_array_elements_text(witness->'evidence_ids') e
       WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') cue
        WHERE cue->>'contribution_id'=e AND cue->>'kind' IN ('occurrence','proposal')
         AND jsonb_array_length(COALESCE(cue->'anchors','[]'))>0
         AND NOT EXISTS(SELECT FROM jsonb_array_elements(cue->'anchors') contextual_anchor
          WHERE contextual_anchor->>'precision'<>'exact'))) THEN
      RAISE EXCEPTION 'relationship witness differs from source/endpoints/evidence' USING ERRCODE='23514'; END IF;
    END LOOP;
   END LOOP;
  END;
 END LOOP;
 -- Scoped denotation statements are addressable products of the retained typed decision.
 FOR contribution IN SELECT value FROM jsonb_array_elements(p_envelope->'contributions')
   WHERE value->>'semantic_type'='contextual.relationship' LOOP
  DECLARE statement jsonb:=data.record_source_json(contribution->'value');
   denotation jsonb; selected_edge jsonb; denotation_report jsonb; denotation_list jsonb;
   source_cue jsonb; denotation_operation jsonb; matches bigint;
  BEGIN
   SELECT count(*) INTO matches FROM jsonb_array_elements(p_envelope->'contribution_operations') oo,
    LATERAL jsonb_array_elements(oo->'contextual_enrichment'->'relationship_decisions') dd
    WHERE dd->>'decision_id'=contribution->'computation_dependencies'->>2;
   IF matches<>1 THEN RAISE EXCEPTION 'denotation proposal lacks one retained decision' USING ERRCODE='23514'; END IF;
   SELECT oo->'contextual_enrichment',dd INTO denotation_report,denotation
    FROM jsonb_array_elements(p_envelope->'contribution_operations') oo,
     LATERAL jsonb_array_elements(oo->'contextual_enrichment'->'relationship_decisions') dd
    WHERE dd->>'decision_id'=contribution->'computation_dependencies'->>2;
   SELECT edge INTO STRICT selected_edge FROM jsonb_array_elements(denotation->'selected_edges') edge
    WHERE edge->>'edge_id'=contribution->'computation_dependencies'->>4 ;
   SELECT ll INTO denotation_list FROM jsonb_array_elements(denotation_report->'candidate_lists') ll
    WHERE ll->>'list_id'=denotation->>'candidate_list_id';
   SELECT cc INTO source_cue FROM jsonb_array_elements(p_envelope->'contributions') cc
    WHERE cc->>'contribution_id'=contribution->'members'->>0;
   denotation_operation:=operation_map->(contribution->>'operation_key');
   IF contribution->>'kind'<>'proposal' OR contribution->>'score_state'<>'missing'
    OR denotation->>'outcome' NOT IN ('selected','partial')
    OR jsonb_array_length(contribution->'members')<>1 OR source_cue IS NULL
    OR source_cue->>'kind'<>'occurrence'
    OR source_cue->>'occurrence_id' IS DISTINCT FROM denotation->>'occurrence_id'
    OR contribution->'anchors' IS DISTINCT FROM source_cue->'anchors'
    OR contribution->'pin' IS DISTINCT FROM source_cue->'pin'
    OR contribution->>'occurrence_id' IS DISTINCT FROM source_cue->>'occurrence_id'
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(selected_edge->'witnesses') w WHERE w->'evidence_ids' ? (source_cue->>'contribution_id'))
    OR statement IS DISTINCT FROM jsonb_build_object(
      'target',(SELECT sg->'meaning' FROM jsonb_array_elements(denotation_report->'inventories') ii,LATERAL jsonb_array_elements(ii->'semantic_groups') sg WHERE ii->>'inventory_id'=denotation_list->>'inventory_id' AND sg->>'target_id'=selected_edge->>'target_id'),
      'relation',selected_edge->>'relation','scope',denotation->'scope','effective_version',denotation->'effective_version')
    OR contribution->'computation_dependencies' IS DISTINCT FROM jsonb_build_array(
      source_cue->>'contribution_id',denotation->>'candidate_list_id',denotation->>'decision_id',
      (SELECT ii->>'source_selection' FROM jsonb_array_elements(denotation_report->'inventories') ii WHERE ii->>'inventory_id'=denotation_list->>'inventory_id'),selected_edge->>'edge_id')
    OR NOT ((denotation_operation->'computation_dependencies') @> (contribution->'computation_dependencies'))
    OR denotation_operation->>'report_digest' IS DISTINCT FROM split_part(denotation->>'decision_id',':',2)
    THEN RAISE EXCEPTION 'denotation proposal differs from selected source-bound scoped decision' USING ERRCODE='23514'; END IF;
  END;
 END LOOP;
 FOR contribution IN SELECT value FROM jsonb_array_elements(p_envelope->'contributions') LOOP
  IF contribution->>'standing'<>'retained_private' OR NOT operation_map ? (contribution->>'operation_key') THEN
   RAISE EXCEPTION 'contribution lacks private standing or operation population' USING ERRCODE='23514'; END IF;
  IF NOT schemas ? (contribution->>'contract') THEN
   SELECT convert_from(content,'UTF8')::json INTO declaration FROM sem.artifact
    WHERE release_id=t.release_id AND artifact_name='json_schema/'||(contribution->>'contract');
   IF declaration IS NOT NULL THEN schemas:=schemas||jsonb_build_object(contribution->>'contract',declaration); END IF;
  END IF;
  declaration:=(schemas->(contribution->>'contract'))::json;
  -- Only released domain contracts with an implemented private effect may be named.
  IF declaration IS NULL OR NOT COALESCE(allowed_contracts ? (contribution->>'contract'),false) THEN
   RAISE EXCEPTION 'contribution semantic contract unavailable' USING ERRCODE='23514'; END IF;
  IF NOT public.json_matches_schema(declaration,jsonb_build_object('kind',contribution->'kind','semantic_type',contribution->'semantic_type',
    'effect','retain_private','assessment_event','local-contribution-1')::json) THEN
   RAISE EXCEPTION 'contribution semantics differ from released contract' USING ERRCODE='23514'; END IF;
  IF contribution->'pin' IS DISTINCT FROM jsonb_build_object('source',p_envelope->>'source',
    'native_product_task_id',v.native_task_id,'product_key',v.native_product_key,'product_digest',v.native_content_digest,
    'projection_digest',v.projection_digest,'recipe_digest',v.recipe_digest,'source_view_id',v.id) THEN
   RAISE EXCEPTION 'contribution pin differs from exact selected source view' USING ERRCODE='23514'; END IF;
  anchors:=COALESCE(contribution->'anchors','[]'); previous_ends:='{}';
  IF contribution->>'kind'='occurrence' AND jsonb_array_length(anchors)=0 THEN
   RAISE EXCEPTION 'located contribution occurrence requires source pieces' USING ERRCODE='23514'; END IF;
  IF jsonb_array_length(anchors)=0 AND contribution ? 'occurrence_id' THEN
   RAISE EXCEPTION 'unlocated contribution cannot claim an occurrence identity' USING ERRCODE='23514'; END IF;
  IF jsonb_array_length(anchors)>0 AND contribution->>'occurrence_id' IS DISTINCT FROM ops.source_contribution_occurrence(anchors) THEN
   RAISE EXCEPTION 'contribution occurrence identity differs from actual pieces' USING ERRCODE='23514'; END IF;
  FOR anchor_ IN SELECT value FROM jsonb_array_elements(anchors) LOOP
   IF anchor_->>'space'='selected_projection' THEN RAISE EXCEPTION 'physical occurrence requires canonical native coordinates' USING ERRCODE='23514'; END IF;
   expected:='record-anchor:'||encode(sha256(convert_to(data.canonical_json(
    (anchor_-'anchor_id')||jsonb_build_object('pin',(anchor_->'pin')-'source_view_id')),'UTF8')),'hex');
   IF anchor_->>'anchor_id' IS DISTINCT FROM expected THEN
    RAISE EXCEPTION 'contribution source anchor identity differs from contents' USING ERRCODE='23514'; END IF;
   coordinate:=data.canonical_json(jsonb_build_array((anchor_->'pin')-'source_view_id',anchor_->'space',anchor_->'pointer',anchor_->'recognition'));
   IF anchor_->>'precision'='exact' THEN
    IF anchor_->>'start' IS NULL OR anchor_->>'end' IS NULL OR (anchor_->>'start')::bigint < COALESCE((previous_ends->>coordinate)::bigint,0) THEN
     RAISE EXCEPTION 'contribution source pieces overlap or reverse order' USING ERRCODE='23514'; END IF;
    previous_ends:=previous_ends||jsonb_build_object(coordinate,(anchor_->>'end')::bigint);
   END IF;
  END LOOP;
  IF (contribution->>'score_state'='native') IS DISTINCT FROM (contribution ? 'score') THEN
   RAISE EXCEPTION 'contribution score availability differs from actual score' USING ERRCODE='23514'; END IF;
  IF contribution->>'score_state'='native' THEN
   IF contribution->'score'->>'kind' NOT IN ('integer','float') THEN
    RAISE EXCEPTION 'native contribution score requires an actual numeric value' USING ERRCODE='23514'; END IF;
   IF contribution->'score'->>'kind'='float' THEN PERFORM data.record_source_float(contribution->'score'); END IF;
  END IF;
  expected:='source-contribution:'||encode(sha256(convert_to(data.canonical_json(contribution-'contribution_id'),'UTF8')),'hex');
  IF contribution->>'contribution_id' IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'contribution identity differs from immutable contents' USING ERRCODE='23514'; END IF;
  FOR ep IN SELECT value FROM jsonb_array_elements(COALESCE(contribution->'endpoints','[]')) LOOP
   IF NOT identity_map ? (ep->>'contribution_id') OR ep->>'contribution_id'=contribution->>'contribution_id' THEN
    RAISE EXCEPTION 'contribution endpoint unavailable or self-referential' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(contribution->'members','[]')) x
    WHERE NOT identity_map ? x OR x=contribution->>'contribution_id') THEN
   RAISE EXCEPTION 'contribution member unavailable or self-referential' USING ERRCODE='23514'; END IF;
  IF (contribution->>'kind'='relation' AND jsonb_array_length(COALESCE(contribution->'endpoints','[]'))<2)
   OR (contribution->>'kind'='composite' AND jsonb_array_length(COALESCE(contribution->'members','[]'))=0) THEN
   RAISE EXCEPTION 'relation/composite contribution lacks endpoints/members' USING ERRCODE='23514'; END IF;
  IF contribution ? 'component' THEN
   DECLARE component jsonb:=contribution->'component'; basis jsonb; role_ jsonb; participant jsonb;
    endpoint_roles jsonb; expected_endpoints jsonb; actual_endpoints jsonb; available_anchors jsonb;
   BEGIN
    op:=operation_map->(contribution->>'operation_key');
    IF component->>'question' IS DISTINCT FROM op->>'question'
     OR component->>'question_version' IS DISTINCT FROM op->>'operation_version'
     OR NOT(COALESCE(contribution->'computation_dependencies','[]') @> (component->'dependencies'))
     OR EXISTS(SELECT FROM jsonb_array_elements(component->'dependencies') d GROUP BY d HAVING count(*)>1) THEN
     RAISE EXCEPTION 'component differs from operation question/version/dependencies' USING ERRCODE='23514'; END IF;
    SELECT COALESCE(jsonb_agg(a->'anchor_id'),'[]') INTO available_anchors FROM (
     SELECT a FROM jsonb_array_elements(COALESCE(contribution->'anchors','[]')) a
     UNION ALL SELECT a FROM jsonb_array_elements(COALESCE(contribution->'endpoints','[]')) e
      JOIN LATERAL (SELECT c FROM jsonb_array_elements(p_envelope->'contributions') c WHERE c->>'contribution_id'=e->>'contribution_id') c ON true
      CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c.c->'anchors','[]')) a
    ) source_anchors;
    FOR basis IN SELECT value FROM jsonb_array_elements(component->'bases') LOOP
     IF NOT(component->'dependencies' @> (basis->'dependencies'))
      OR EXISTS(SELECT FROM jsonb_array_elements(basis->'dependencies') d GROUP BY d HAVING count(*)>1)
      OR NOT(available_anchors @> COALESCE(basis->'anchor_ids','[]')) THEN
      RAISE EXCEPTION 'component basis has unavailable dependency or source anchor' USING ERRCODE='23514'; END IF;
    END LOOP;
    IF component->>'kind'='located_role' THEN
     IF NOT contribution ? 'occurrence_id'
      OR EXISTS(SELECT FROM jsonb_array_elements(component->'roles') role_entry GROUP BY role_entry->>'role' HAVING count(*)>1) THEN
      RAISE EXCEPTION 'located component requires physical occurrence and distinct roles' USING ERRCODE='23514'; END IF;
     FOR role_ IN SELECT value FROM jsonb_array_elements(component->'roles') LOOP
      IF EXISTS(SELECT FROM jsonb_array_elements_text(role_->'anchor_ids') aid WHERE NOT EXISTS(
       SELECT FROM jsonb_array_elements(contribution->'anchors') a WHERE a->>'anchor_id'=aid)) THEN
       RAISE EXCEPTION 'located component role has unavailable source anchor' USING ERRCODE='23514'; END IF;
     END LOOP;
    ELSE
     SELECT convert_from(content,'UTF8')::jsonb->'component_endpoints'->(component->>'kind') INTO endpoint_roles
      FROM sem.artifact WHERE release_id=t.release_id AND artifact_name='contribution_projection.json';
     SELECT jsonb_object_agg(role,component->(role||'_contribution_id')) INTO expected_endpoints
      FROM jsonb_array_elements_text(COALESCE(endpoint_roles,'[]')) role;
     SELECT jsonb_object_agg(e->>'role',e->'contribution_id') INTO actual_endpoints
      FROM jsonb_array_elements(COALESCE(contribution->'endpoints','[]')) e;
     IF contribution->>'kind'<>'relation' OR endpoint_roles IS NULL OR jsonb_array_length(endpoint_roles)=0
      OR actual_endpoints IS DISTINCT FROM expected_endpoints
      OR jsonb_array_length(contribution->'endpoints')<>jsonb_array_length(endpoint_roles) THEN
      RAISE EXCEPTION 'component endpoints differ from released role signature' USING ERRCODE='23514'; END IF;
    END IF;
   END;
  END IF;
 END LOOP;
 SELECT COALESCE(jsonb_agg(a),'[]') INTO anchors FROM (SELECT DISTINCT a
  FROM jsonb_array_elements(p_envelope->'contributions') c
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c->'anchors','[]')) a) pieces;
 PERFORM ops.validate_source_anchor_coordinates(t.run_id,t.unit_id,p_envelope->>'source',anchors);
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_contribution_report(bigint,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.project_source_contributions(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 INSERT INTO kb.source_contribution_operation(task_id,release_id,operation_key,position,question,operation_version,outcome,inspected_count,emitted_count,report_digest)
 SELECT p_task,p_envelope->>'release_id',o->>'operation_key',n-1,o->>'question',o->>'operation_version',o->>'outcome',
  (o->>'inspected_count')::bigint,(o->>'emitted_count')::bigint,o->>'report_digest'
 FROM jsonb_array_elements(p_envelope->'contribution_operations') WITH ORDINALITY x(o,n);
 INSERT INTO kb.source_contribution(task_id,release_id,contribution_id,position,operation_key,kind,semantic_type,source_view_id,occurrence_id,disposition,standing,score_state)
 SELECT p_task,p_envelope->>'release_id',c->>'contribution_id',n-1,c->>'operation_key',c->>'kind',c->>'semantic_type',
  (c->'pin'->>'source_view_id')::bigint,c->>'occurrence_id',c->>'disposition',c->>'standing',c->>'score_state'
 FROM jsonb_array_elements(p_envelope->'contributions') WITH ORDINALITY x(c,n);
 INSERT INTO kb.source_contribution_anchor(task_id,contribution_id,position,anchor_id,source_view_id,pointer,space,precision,"start","end")
 SELECT p_task,c->>'contribution_id',n-1,a->>'anchor_id',(a->'pin'->>'source_view_id')::bigint,
  a->>'pointer',a->>'space',a->>'precision',(a->>'start')::bigint,(a->>'end')::bigint
 FROM jsonb_array_elements(p_envelope->'contributions') c,
 LATERAL jsonb_array_elements(COALESCE(c->'anchors','[]')) WITH ORDINALITY x(a,n);
 INSERT INTO kb.source_contribution_endpoint(task_id,contribution_id,position,role,endpoint_id)
 SELECT p_task,c->>'contribution_id',n-1,e->>'role',e->>'contribution_id'
 FROM jsonb_array_elements(p_envelope->'contributions') c,
 LATERAL jsonb_array_elements(COALESCE(c->'endpoints','[]')) WITH ORDINALITY x(e,n);
 -- Contextual derived indexes are projections of the already validated immutable report.
 INSERT INTO kb.contextual_profile(task_id,profile_id,dimension,detail)
 SELECT p_task,p->>'profile_id',(p->>'dimension')::integer,p
 FROM jsonb_array_elements(p_envelope->'contribution_operations') o,
 LATERAL jsonb_array_elements(o->'contextual_enrichment'->'profiles') p;
 INSERT INTO kb.contextual_vector(task_id,vector_id,object_id,source_binding,profile_id,input_digest,vector)
 SELECT p_task,v->>'vector_id',v->>'object_id',v->>'source_binding',v->>'profile_id',
  v->>'input_digest',(v->'values')::text::public.vector
 FROM jsonb_array_elements(p_envelope->'contribution_operations') o,
 LATERAL jsonb_array_elements(o->'contextual_enrichment'->'vectors') v;
 INSERT INTO kb.contextual_inventory(task_id,inventory_id,detail)
 SELECT p_task,i->>'inventory_id',i
 FROM jsonb_array_elements(p_envelope->'contribution_operations') o,
 LATERAL jsonb_array_elements(o->'contextual_enrichment'->'inventories') i;
 INSERT INTO kb.contextual_target_vector(task_id,inventory_id,profile_id,target_id,vector_id,search_text,exact_forms,vector)
 SELECT p_task,i->>'inventory_id',v->>'profile_id',target->>'target_id',v->>'vector_id',
  concat_ws(' ',target->>'label',target->>'description',(SELECT string_agg(x,' ') FROM jsonb_array_elements_text(target->'aliases') x)),
  ARRAY(SELECT lower(x) FROM (SELECT target->>'label' AS x UNION ALL SELECT value FROM jsonb_array_elements_text(target->'aliases')) forms),
  (v->'values')::text::public.vector
 FROM jsonb_array_elements(p_envelope->'contribution_operations') o,
 LATERAL jsonb_array_elements(o->'contextual_enrichment'->'inventories') i,
 LATERAL jsonb_array_elements(i->'targets') target,
 LATERAL jsonb_array_elements(o->'contextual_enrichment'->'vectors') v
 WHERE v->>'object_id'=target->>'target_id';
END $$;
REVOKE ALL ON FUNCTION ops.project_source_contributions(bigint,jsonb) FROM PUBLIC;
