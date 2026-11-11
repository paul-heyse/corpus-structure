CREATE OR REPLACE FUNCTION ops.require_source_interpretation(p_task bigint,c jsonb,p jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ref jsonb:=p->'source_record'; task_project text; body jsonb; member jsonb; d jsonb; candidate jsonb; focus jsonb; a data.record_anchor; field_name text; enum_name text; selected text; count_ integer;
BEGIN
 SELECT r.project_id INTO task_project FROM ops.task t JOIN ops.run r ON r.id=t.run_id WHERE t.id=p_task;
 IF NOT EXISTS(SELECT FROM ops.completed_result cr JOIN ops.run r ON r.id=cr.run_id
  JOIN ops.input_cut ic ON ic.id=cr.cut_id AND ic.run_id=r.id
  JOIN data.realization z ON z.release_id=cr.release_id AND z.realization_id=cr.output_realization_id
  JOIN data.source_record sr ON sr.release_id=cr.release_id AND sr.realization_id=cr.output_realization_id
  WHERE cr.run_id=(ref->>'run_id')::bigint AND cr.cut_id=(ref->>'cut_id')::bigint
   AND cr.release_id=ref->>'release_id' AND cr.output_realization_id=ref->>'realization_id'
   AND z.data_revision=(ref->>'data_revision')::bigint AND r.project_id=ref->>'project_id'
   AND r.project_id=task_project AND r.status='finished' AND r.sealed AND ic.final
   AND sr.record_id=ref->>'record_id' AND sr.interpretation_id=ref->>'interpretation_id'
   AND sr.source_view_id=(ref->>'source_view_id')::bigint
   AND sr.source_view_id=(c->'pin'->>'source_view_id')::bigint
   AND EXISTS(SELECT FROM data.record_report_member rm JOIN data.record_report rr
    ON rr.release_id=rm.release_id AND rr.realization_id=rm.realization_id AND rr.selected_task_id=rm.selected_task_id
    WHERE rm.release_id=sr.release_id AND rm.realization_id=sr.realization_id AND rm.record_id=sr.record_id
     AND rm.interpretation_id=sr.interpretation_id AND rr.cut_id=cr.cut_id))
 THEN RAISE EXCEPTION 'interpretation source record differs from completed pinned result' USING ERRCODE='23514'; END IF;
 SELECT convert_from(content,'UTF8')::jsonb INTO body FROM sem.artifact
  WHERE release_id=p->>'vocabulary_release' AND release_id=(SELECT release_id FROM ops.task WHERE id=p_task) AND artifact_name='vocabularies/metadata.json'
   AND encode(sha256(content),'hex')=p->>'metadata_digest';
 IF body IS NULL THEN RAISE EXCEPTION 'interpretation vocabulary metadata pins differ' USING ERRCODE='23514'; END IF;
 IF c->>'semantic_type'='terminology.interpretation' THEN
  SELECT count(DISTINCT value->>'field') INTO count_ FROM jsonb_array_elements(p->'decisions');
  IF count_<>jsonb_array_length(p->'decisions') THEN RAISE EXCEPTION 'duplicate terminology field decision' USING ERRCODE='23514'; END IF;
 END IF;
 FOR d IN SELECT value FROM jsonb_array_elements(CASE WHEN c->>'semantic_type'='terminology.interpretation' THEN p->'decisions' ELSE jsonb_build_array(p) END) LOOP
  focus:=d->'focus';
  SELECT ra.* INTO a FROM data.record_anchor ra
   JOIN data.record_evidence_member em ON em.release_id=ra.release_id AND em.realization_id=ra.realization_id AND em.record_id=ra.record_id AND em.interpretation_id=ra.interpretation_id AND em.anchor_id=ra.anchor_id
   JOIN data.record_field_evidence fe ON fe.release_id=em.release_id AND fe.realization_id=em.realization_id AND fe.record_id=em.record_id AND fe.interpretation_id=em.interpretation_id AND fe.set_id=em.set_id
   WHERE ra.release_id=ref->>'release_id' AND ra.realization_id=ref->>'realization_id'
    AND ra.record_id=ref->>'record_id' AND ra.interpretation_id=ref->>'interpretation_id'
    AND ra.anchor_id=focus->>'anchor_id' AND fe.role=focus->>'role' AND ra.precision='exact' LIMIT 1;
  IF a.anchor_id IS NULL OR (focus->>'start')::bigint<a.start OR (focus->>'end')::bigint>a."end"
   OR (focus->>'start')::bigint>=(focus->>'end')::bigint
   OR substring(a.source_piece FROM (focus->>'start')::integer-a.start::integer+1 FOR (focus->>'end')::integer-(focus->>'start')::integer) IS DISTINCT FROM focus->>'source_piece'
   OR a.source_view_id IS DISTINCT FROM (ref->>'source_view_id')::bigint
   OR a.native_product_task_id IS DISTINCT FROM (c->'pin'->>'native_product_task_id')::bigint
   OR a.product_key IS DISTINCT FROM c->'pin'->>'product_key' OR a.product_digest IS DISTINCT FROM c->'pin'->>'product_digest'
   OR a.projection_digest IS DISTINCT FROM c->'pin'->>'projection_digest' OR a.recipe_digest IS DISTINCT FROM c->'pin'->>'recipe_digest'
   OR (CASE WHEN jsonb_array_length(coalesce(c->'anchors','[]'))=0 THEN c->>'kind' IS DISTINCT FROM 'proposal' OR c ? 'occurrence_id'
    ELSE NOT EXISTS(SELECT FROM jsonb_array_elements(c->'anchors') ca WHERE ca->>'pointer'=a.pointer AND ca->>'space'=a.space AND ca->>'source_piece'=focus->>'source_piece' AND (ca->>'start')::bigint=(focus->>'start')::bigint AND (ca->>'end')::bigint=(focus->>'end')::bigint) END)
  THEN RAISE EXCEPTION 'interpretation focus does not authenticate record field source span' USING ERRCODE='23514'; END IF;
  IF c->>'semantic_type'='terminology.interpretation' THEN
   field_name:=d->>'field'; enum_name:=CASE field_name WHEN 'distribution_family' THEN 'StatisticalDistributionFamily' WHEN 'distribution_attribute' THEN 'StatisticalDistributionAttribute' END;
   IF enum_name IS NULL THEN RAISE EXCEPTION 'unsupported terminology field' USING ERRCODE='23514'; END IF;
   SELECT count(DISTINCT value->>'value') INTO count_ FROM jsonb_array_elements(d->'candidates');
   IF count_<>jsonb_array_length(d->'candidates') THEN RAISE EXCEPTION 'duplicate terminology candidate' USING ERRCODE='23514'; END IF;
   FOR candidate IN SELECT value FROM jsonb_array_elements(d->'candidates') LOOP
    SELECT m INTO member FROM jsonb_array_elements(body->'enums'->enum_name->'members') m WHERE m->>'value'=candidate->>'value';
    IF member IS NULL OR member->>'meaning' IS DISTINCT FROM candidate->>'meaning' OR coalesce(member->>'label',member->>'value') IS DISTINCT FROM candidate->>'label' THEN RAISE EXCEPTION 'candidate differs from released vocabulary' USING ERRCODE='23514'; END IF;
    IF NOT coalesce(candidate->>'matching_field'=ANY(ARRAY['value','label','synonym','browse']),false)
     OR (candidate->>'matching_field'='synonym' AND NOT EXISTS(SELECT FROM jsonb_array_elements(coalesce(member->'synonyms','[]')) sy WHERE sy->>'predicate'=candidate->>'matching_predicate'))
     OR (candidate->>'matching_field'<>'synonym' AND candidate->>'matching_predicate' IS DISTINCT FROM '')
    THEN RAISE EXCEPTION 'candidate matching field or predicate differs from source metadata' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF d->>'outcome'='selected' THEN
    IF NOT EXISTS(SELECT FROM jsonb_array_elements(d->'candidates') x WHERE x->>'value'=d->>'selected_value')
     OR d->>'mapping_direction' IS DISTINCT FROM 'source_to_term' OR NOT coalesce(d->>'mapping_predicate'=ANY(ARRAY['http://www.w3.org/2004/02/skos/core#exactMatch','http://www.w3.org/2004/02/skos/core#closeMatch','http://www.w3.org/2004/02/skos/core#broadMatch','http://www.w3.org/2004/02/skos/core#narrowMatch','http://www.w3.org/2004/02/skos/core#relatedMatch']),false)
    THEN RAISE EXCEPTION 'selected terminology mapping lacks examined candidate or predicate' USING ERRCODE='23514'; END IF;
   ELSIF d ? 'selected_value' OR d ? 'mapping_predicate' OR d ? 'mapping_direction' THEN RAISE EXCEPTION 'unresolved terminology claims selected mapping' USING ERRCODE='23514'; END IF;
   IF d->>'outcome'='no_match' AND jsonb_array_length(d->'candidates')<>0 THEN RAISE EXCEPTION 'no-match terminology has candidates' USING ERRCODE='23514'; END IF;
  ELSE
   IF d->>'outcome'='selected' THEN
    IF NOT EXISTS(SELECT FROM jsonb_array_elements(body->'enums'->'RecognizedTimeUnit'->'members') x WHERE x->>'value'=d->>'unit') OR NOT EXISTS(SELECT FROM jsonb_array_elements(body->'enums'->'RecognizedQuantityKind'->'members') x WHERE x->>'value'=d->>'quantity_kind') THEN RAISE EXCEPTION 'measurement unit or quantity is outside released vocabulary' USING ERRCODE='23514'; END IF;
   ELSIF d ? 'unit' OR d ? 'quantity_kind' THEN RAISE EXCEPTION 'unresolved measurement claims recognized identifiers' USING ERRCODE='23514'; END IF;
   IF (d->>'basis_status'='identified') IS DISTINCT FROM (coalesce(d->>'basis','')<>'') THEN RAISE EXCEPTION 'measurement basis status differs' USING ERRCODE='23514'; END IF;
  END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.require_source_interpretation(bigint,jsonb,jsonb) FROM PUBLIC;

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

-- One bounded immutable neighborhood per already authenticated inventory/profile.
CREATE OR REPLACE FUNCTION ops.contextual_mutual_neighbors(inv jsonb,profile jsonb,vectors jsonb)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH targets AS MATERIALIZED (
  SELECT t->>'target_id' AS id,t->>'representation_digest' AS digest,t->>'source_binding' AS source
  FROM jsonb_array_elements(inv->'targets') t
 ), eligible AS MATERIALIZED (
  SELECT t.id,t.digest,(v->'values')::text::public.vector AS vector
  FROM targets t JOIN jsonb_array_elements(vectors) v ON v->>'object_id'=t.id
  WHERE v->>'profile_id'=profile->>'profile_id' AND v->>'representation_digest'=t.digest
   AND v->>'source_binding'=t.source
   AND public.vector_dims((v->'values')::text::public.vector)=(profile->>'dimension')::integer
   AND abs(public.vector_norm((v->'values')::text::public.vector)-1)<=0.00001
 ), coverage AS (
  SELECT CASE WHEN NOT EXISTS(SELECT FROM targets) THEN 'completed'
   WHEN profile IS NULL THEN 'profile_unavailable'
   WHEN (SELECT count(*) FROM targets)<>(SELECT count(*) FROM eligible)
     OR (SELECT count(*) FROM eligible)<>(SELECT count(DISTINCT id) FROM eligible)
     OR (SELECT count(*) FROM targets t JOIN jsonb_array_elements(vectors) v
         ON v->>'object_id'=t.id AND v->>'profile_id'=profile->>'profile_id')
        <>(SELECT count(*) FROM eligible)
   THEN 'vector_coverage_unavailable' ELSE 'completed' END AS status
 ), representatives AS MATERIALIZED (
  SELECT e.*,g->>'target_id' AS group_id
  FROM coverage c,jsonb_array_elements(inv->'semantic_groups') g
  JOIN eligible e ON e.id=g->'member_target_ids'->>0
  WHERE c.status='completed'
 ), directed AS MATERIALIZED (
  SELECT a.id AS from_id,b.id AS to_id,
   row_number() OVER(PARTITION BY a.id ORDER BY b.distance,b.id COLLATE "C") AS rank_,b.distance
  FROM representatives a CROSS JOIN LATERAL (
   SELECT b.id,a.vector OPERATOR(public.<=>) b.vector AS distance
   FROM representatives b WHERE b.id<>a.id ORDER BY distance,b.id COLLATE "C" LIMIT 5
  ) b
 ), mutual AS (
  SELECT d.from_id,d.to_id,d.rank_ AS left_rank,r.rank_ AS right_rank,d.distance
  FROM directed d JOIN directed r ON r.from_id=d.to_id AND r.to_id=d.from_id
  WHERE d.from_id COLLATE "C"<d.to_id COLLATE "C"
 )
 SELECT jsonb_strip_nulls(jsonb_build_object(
  'policy','mutual-exact-cosine-top5-2','inventory_id',inv->>'inventory_id',
  'profile_id',profile->>'profile_id','status',c.status,
  'directed_ranks',COALESCE((
   SELECT jsonb_agg(jsonb_build_object('from_id',from_id,'to_id',to_id,'rank',rank_,'distance',distance)
    ORDER BY from_id COLLATE "C",rank_) FROM directed
  ),'[]'::jsonb),
  'edges',COALESCE((
   SELECT jsonb_agg(jsonb_build_object('left_id',m.from_id,'right_id',m.to_id,
    'left_group',a.group_id,'right_group',b.group_id,
    'left_digest',a.digest,'right_digest',b.digest,
    'left_rank',m.left_rank,'right_rank',m.right_rank,'distance',m.distance)
    ORDER BY m.from_id COLLATE "C",m.to_id COLLATE "C")
   FROM mutual m JOIN representatives a ON a.id=m.from_id JOIN representatives b ON b.id=m.to_id
  ),'[]'::jsonb)))
 FROM coverage c
$$;
REVOKE ALL ON FUNCTION ops.contextual_mutual_neighbors(jsonb,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.contextual_mutual_neighbors(jsonb,jsonb,jsonb) TO corpus_sem_reader,corpus_sem_writer;

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

CREATE OR REPLACE FUNCTION ops.validate_source_table_note_scope(p_view kb.source_view,p_rows jsonb,p_layers jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE link_ jsonb; subject_ jsonb; note_ jsonb; table_ jsonb; original_note jsonb; note_text text;
 cell_pointer text[]; cell_ jsonb; named text[]; eligible_count integer; matching_count integer; primary_ jsonb; ref_ jsonb; nav_ jsonb;
BEGIN
 FOR link_ IN
  SELECT value FROM jsonb_array_elements(p_rows) c(row_)
  CROSS JOIN LATERAL (SELECT data.record_source_json(c.row_->'value') value) meaning
  WHERE c.row_->>'semantic_type'='structural.scoped_attachment' AND value->>'relation'='note'
 LOOP
  SELECT row_ INTO STRICT subject_ FROM jsonb_array_elements(p_rows) row_
   WHERE row_->>'contribution_id'=link_->>'subject_id';
  SELECT row_ INTO STRICT note_ FROM jsonb_array_elements(p_rows) row_
   WHERE row_->>'contribution_id'=link_->>'target_id';
  cell_pointer:=regexp_match(subject_->'anchors'->0->>'pointer','^(.*)/data/table_cells/([0-9]+)$');
  IF cell_pointer IS NULL OR cell_pointer[1] IS DISTINCT FROM link_->>'region'
   OR jsonb_array_length(subject_->'anchors')<>1 OR jsonb_array_length(note_->'anchors')<>1
   OR data.record_source_json(subject_->'value')->>'role' IS DISTINCT FROM 'cell'
   OR data.record_source_json(note_->'value')->>'role' IS DISTINCT FROM 'note' THEN
   RAISE EXCEPTION 'table note lacks exact note and cell endpoints' USING ERRCODE='23514';
  END IF;
  SELECT native_json INTO STRICT table_ FROM ops.read_pdf_published_items(
   p_view.native_task_id,p_view.native_product_key,p_view.native_content_digest,ARRAY[cell_pointer[1]]);
  IF table_->>'label' IS DISTINCT FROM 'table' OR NOT EXISTS(
   SELECT FROM jsonb_array_elements(COALESCE(table_->'footnotes','[]')) n
    WHERE n->>'$ref'=note_->'anchors'->0->>'pointer'
  ) THEN
   RAISE EXCEPTION 'table note is outside its native table association' USING ERRCODE='23514';
  END IF;
  cell_:=table_->'data'->'table_cells'->(cell_pointer[2]::integer);
  IF cell_ IS NULL OR COALESCE((cell_->>'column_header')::boolean,false)
   OR COALESCE((cell_->>'row_header')::boolean,false) THEN
   RAISE EXCEPTION 'table note does not apply to a data cell' USING ERRCODE='23514';
  END IF;
  SELECT native_json INTO STRICT original_note FROM ops.read_pdf_published_items(
   p_view.native_task_id,p_view.native_product_key,p_view.native_content_digest,
   ARRAY[note_->'anchors'->0->>'pointer']);
  IF note_->'anchors'->0->>'source_piece' IS DISTINCT FROM original_note->>'text'
   OR note_->'anchors'->0->>'start' IS DISTINCT FROM '0'
   OR (note_->'anchors'->0->>'end')::integer IS DISTINCT FROM length(original_note->>'text') THEN
   RAISE EXCEPTION 'table note scope requires the whole original note' USING ERRCODE='23514';
  END IF;
  SELECT r->'component'->'primary_node',r->'component'->'primary_choices' INTO STRICT ref_,primary_
   FROM jsonb_array_elements(p_rows) r WHERE data.record_source_json(r->'value')=link_ AND r->>'semantic_type'='structural.scoped_attachment';
  primary_:=ops.primary_navigation_node(p_layers,ref_,primary_,p_view);
  nav_:=primary_->'navigation';
  IF nav_->>'kind' IS DISTINCT FROM 'note_scope' OR nav_->>'pointer' IS DISTINCT FROM note_->'anchors'->0->>'pointer' THEN
   RAISE EXCEPTION 'table note lacks its exact retained primary scope cue' USING ERRCODE='23514'; END IF;
  IF nav_->>'axis'='all' THEN CONTINUE; END IF;
  named:=ARRAY[nav_->>'label',nav_->>'axis'];
  IF named[1] IS NULL OR named[2] NOT IN ('row','column','band') THEN RAISE EXCEPTION 'table note has unresolved retained scope' USING ERRCODE='23514'; END IF;
  SELECT count(*),count(*) FILTER(WHERE CASE WHEN lower(named[2])='row' THEN
   (h->>'start_row_offset_idx')::integer<=(cell_->>'start_row_offset_idx')::integer AND
   (h->>'end_row_offset_idx')::integer>=(cell_->>'end_row_offset_idx')::integer AND
   (h->>'end_col_offset_idx')::integer<=(cell_->>'start_col_offset_idx')::integer
  ELSE
   (h->>'start_col_offset_idx')::integer<=(cell_->>'start_col_offset_idx')::integer AND
   (h->>'end_col_offset_idx')::integer>=(cell_->>'end_col_offset_idx')::integer AND
   (h->>'end_row_offset_idx')::integer<=(cell_->>'start_row_offset_idx')::integer
  END) INTO eligible_count,matching_count
  FROM jsonb_array_elements(table_->'data'->'table_cells') h
  WHERE lower(btrim(h->>'text'))=lower(named[1]) AND CASE WHEN lower(named[2])='row'
   THEN (h->>'row_header')::boolean ELSE (h->>'column_header')::boolean END;
  IF eligible_count<>1 OR matching_count<>1 THEN
   RAISE EXCEPTION 'table note does not establish the selected row or band' USING ERRCODE='23514';
  END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'table note cannot resolve original endpoints' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_table_note_scope(kb.source_view,jsonb,jsonb) FROM PUBLIC;



-- The selected policy derives finite requests here. The worker receives this
-- projection verbatim; admission derives it again from the selected source.
CREATE OR REPLACE FUNCTION ops.table_correspondence_band(
 p_edges jsonb,p_premises jsonb,p_dependencies jsonb,p_revision text,p_projection text,
 p_scope text,p_scale numeric)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH policy AS (
  SELECT 'table-policy:source-correspondence-1:correspondence:'||p_scale::text AS id,
   'table-model:'||p_revision AS model,'table-ontology:scoped-table-roles' AS ontology,
   'table-executor:exact-local-1' AS executor,
   p_scale::double precision*ln(2::double precision) AS weight
 ), hypotheses AS (
  SELECT m,m->>'identity' AS id,m->'bindings' AS bindings,n
  FROM jsonb_array_elements(p_premises) WITH ORDINALITY a(m,n)
 ), auxiliary AS (
  SELECT count(*)>0 AND NOT (count(*)=1 AND bool_and(m->>'standing'='fixed')) AS enabled
  FROM hypotheses
 ), axes AS (
  SELECT e->>'axis' AS axis,e->>'role' AS role,
   jsonb_build_array(jsonb_build_object('key','unresolved','kind','unresolved','reason','retained scope incomplete'))||
   CASE WHEN e->>'role' IN ('note','unit') THEN jsonb_build_array(
    jsonb_build_object('key','does_not_apply','kind','resolved','reason',NULL)) ELSE '[]' END||
   jsonb_agg(jsonb_build_object('key',e->>'id','kind','resolved','reason',NULL) ORDER BY (e->>'id') COLLATE "C") AS candidates,
   jsonb_agg(e ORDER BY (e->>'id') COLLATE "C") AS edges
  FROM jsonb_array_elements(p_edges) e GROUP BY e->>'axis',e->>'role'
 ), options AS (
  SELECT a.axis,a.role,a.edges,e,c->>'key' AS candidate,n
  FROM axes a CROSS JOIN LATERAL jsonb_array_elements(a.candidates) WITH ORDINALITY c(c,n)
  LEFT JOIN LATERAL jsonb_array_elements(a.edges) e ON e->>'id'=c->>'key'
 ), m_options AS (
  SELECT 0 AS n,'unresolved' AS id,NULL::jsonb AS bindings
  UNION ALL SELECT n,id,bindings FROM hypotheses
 ), role_factors AS (
  SELECT axis,jsonb_build_object('key','source-choice:'||axis,'scope',jsonb_build_array(axis),
   'values',jsonb_agg(CASE WHEN e->'direct'='true'::jsonb AND e->'disjoint'='false'::jsonb
     THEN p.weight ELSE 0 END ORDER BY n),
   'dependency_ids',(SELECT coalesce(jsonb_agg(d ORDER BY d COLLATE "C"),'[]')
    FROM (SELECT DISTINCT key AS d FROM jsonb_array_elements(o.edges) x
     CROSS JOIN LATERAL jsonb_array_elements_text(x->'evidence') k(key)) deps)||jsonb_build_array(p.id)
  ) AS factor
  FROM options o CROSS JOIN policy p GROUP BY axis,o.edges,p.id,p.weight
 ), compatibility AS (
  SELECT o.axis,jsonb_build_object('key','correspondence-role:'||o.axis,
   'scope',CASE WHEN a.enabled THEN jsonb_build_array('M',o.axis) ELSE jsonb_build_array(o.axis) END,
   'values',jsonb_agg(CASE WHEN m.bindings ? o.candidate THEN
    CASE WHEN m.bindings->o.candidate->>'alignment'='exact' THEN p.weight ELSE p.weight/2 END
    ELSE 0 END ORDER BY m.n,o.n),
   'dependency_ids',(SELECT jsonb_agg(d ORDER BY d COLLATE "C") FROM (
    SELECT DISTINCT dep AS d FROM hypotheses h
    CROSS JOIN LATERAL jsonb_each(h.bindings) b(edge,proof)
    JOIN options x ON x.axis=o.axis AND x.candidate=b.edge
    CROSS JOIN LATERAL jsonb_array_elements_text(b.proof->'dependencies') k(dep)
    UNION SELECT h.id FROM hypotheses h WHERE EXISTS(
     SELECT FROM options x WHERE x.axis=o.axis AND h.bindings ? x.candidate)
    UNION SELECT p.id
   ) deps)) AS factor
  FROM options o CROSS JOIN m_options m CROSS JOIN auxiliary a CROSS JOIN policy p
  WHERE (a.enabled OR m.n>0) AND EXISTS (
   SELECT FROM hypotheses h JOIN options x ON x.axis=o.axis AND h.bindings ? x.candidate)
  GROUP BY o.axis,a.enabled,p.id
 ), m_factor AS (
  SELECT jsonb_build_object('key','shared-correspondence-evidence','scope',jsonb_build_array('M'),
   'values',jsonb_agg(CASE WHEN m.n=0 THEN 0 ELSE p.weight END ORDER BY m.n),
   'dependency_ids',(SELECT jsonb_agg(d ORDER BY d COLLATE "C") FROM (
    SELECT DISTINCT h.id AS d FROM hypotheses h UNION SELECT p.id) deps)
  ) AS factor
  FROM m_options m CROSS JOIN policy p CROSS JOIN auxiliary a WHERE a.enabled GROUP BY p.id
 ), masks AS (
  SELECT axis,jsonb_build_object('key','source-disjoint:'||axis,'scope',jsonb_build_array(axis),
   'allowed',jsonb_agg(e->'disjoint' IS DISTINCT FROM 'true'::jsonb ORDER BY n),
   'dependency_ids',(SELECT jsonb_agg(d ORDER BY d COLLATE "C") FROM (
    SELECT DISTINCT key AS d FROM jsonb_array_elements(o.edges) x
    CROSS JOIN LATERAL jsonb_array_elements_text(x->'evidence') k(key)
    WHERE x->'disjoint'='true'::jsonb UNION SELECT p.ontology
   ) deps)
  ) AS mask
  FROM options o CROSS JOIN policy p GROUP BY axis,o.edges,p.ontology
  HAVING bool_or(e->'disjoint'='true'::jsonb)
 ), events AS (
  SELECT role,jsonb_build_object('key','any-'||role,
   'question','At least one retained '||role||' reading applies in this table row',
   'derivations',jsonb_agg(jsonb_build_array(jsonb_build_object('decision',axis,'candidate',candidate))
     ORDER BY axis COLLATE "C",n)) AS event
  FROM options WHERE e->'disjoint'='false'::jsonb GROUP BY role
 ), dependencies AS (
  SELECT 0 AS kind_order,key AS id,'observation' AS kind,p_revision AS revision
   FROM jsonb_array_elements_text(p_dependencies) d(key)
  UNION ALL SELECT 1,id,'context',p_projection FROM hypotheses
  UNION ALL SELECT 2,model,'model',p_revision FROM policy
  UNION ALL SELECT 3,ontology,'ontology','source-correspondence-1' FROM policy
  UNION ALL SELECT 4,executor,'context','exact-local-1' FROM policy
  UNION ALL SELECT 5,id,'policy','source-correspondence-1' FROM policy
 )
 SELECT jsonb_build_object(
  'decisions',(CASE WHEN a.enabled THEN jsonb_build_array(jsonb_build_object(
   'key','M','candidates',jsonb_build_array(jsonb_build_object('key','unresolved',
   'kind','unresolved','reason','shared correspondence unresolved within retained evidence'))||
   (SELECT jsonb_agg(jsonb_build_object('key',id,'kind','resolved','reason',NULL) ORDER BY n)
    FROM hypotheses))) ELSE '[]' END)||
   (SELECT jsonb_agg(jsonb_build_object('key',axis,'candidates',candidates) ORDER BY axis COLLATE "C") FROM axes),
  'constraints',
   (SELECT coalesce(jsonb_agg(mask ORDER BY axis COLLATE "C"),'[]') FROM masks),
  'dependencies',(SELECT jsonb_agg(jsonb_build_object('key',id,'kind',kind,'revision',revision)
   ORDER BY kind_order,id COLLATE "C") FROM dependencies),
  'selection',jsonb_build_object('scope_id',p_scope,'dependency_ids',p_dependencies,
   'retrieval_limit',NULL,'exclusions',(SELECT coalesce(jsonb_agg('source-disjoint:'||(e->>'id')
    ORDER BY (e->>'id') COLLATE "C"),'[]') FROM jsonb_array_elements(p_edges) e WHERE e->'disjoint'='true'::jsonb),
   'truncations','[]'::jsonb),
  'model_dependency_id',p.model,'ontology_dependency_id',p.ontology,'policy_dependency_id',p.id,
  'events',(SELECT coalesce(jsonb_agg(event ORDER BY role COLLATE "C"),'[]') FROM events),
  'marginal_decisions',NULL,'dependence_scopes',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'scope',factor->'scope','dependency_ids',factor->'dependency_ids',
   'reason','One source correspondence conditions this local role reading') ORDER BY axis COLLATE "C"),'[]')
   FROM compatibility WHERE a.enabled),
  'limits',jsonb_build_object('max_states',65536,'block_states',1024,'max_workspace_bytes',67108864,
   'max_seconds',10,'displayed_alternatives',5),
  'feasibility_control',false,'correspondence_premises',p_premises,
  'correspondence_status',CASE WHEN a.enabled THEN 'ambiguous'
   WHEN jsonb_array_length(p_premises)>0 THEN 'fixed' ELSE 'unavailable' END,
  'correspondence_reason',CASE WHEN jsonb_array_length(p_premises)=0 THEN
   'No exact observed-to-schematic declaration and eligible matched cells in this row.'
   WHEN a.enabled THEN 'Retained source permits competing or unresolved correspondence.' END
 )||jsonb_build_object('potentials',
  coalesce((SELECT jsonb_agg(factor) FROM m_factor),'[]')||
  (SELECT jsonb_agg(factor ORDER BY axis COLLATE "C") FROM role_factors)||
  (SELECT coalesce(jsonb_agg(factor ORDER BY axis COLLATE "C"),'[]') FROM compatibility))
 FROM auxiliary a CROSS JOIN policy p
$$;
REVOKE ALL ON FUNCTION ops.table_correspondence_band(jsonb,jsonb,jsonb,text,text,text,numeric) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.table_correspondence_requests(v kb.source_view,p_rows jsonb,p_scale numeric,p_layers jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE pointers text[]; nodes jsonb; captions jsonb; requests jsonb;
BEGIN
 IF p_scale IS NULL OR p_scale NOT IN (0.5,1,2) THEN
  RAISE EXCEPTION 'invalid registered table correspondence weight' USING ERRCODE='23514';
 END IF;
 p_scale:=trim_scale(p_scale);
 -- Read only native table cells, and prose referenced by retained role candidates.
 SELECT array_agg(DISTINCT pointer) INTO pointers FROM (
  SELECT (regexp_match(a->>'pointer','^(.*)/data/table_cells/[0-9]+$'))[1] AS pointer
  FROM jsonb_array_elements(p_rows) r CROSS JOIN LATERAL jsonb_array_elements(r->'anchors') a
  WHERE r->>'semantic_type'='structural.located_participant' AND a->>'pointer' LIKE '%/data/table_cells/%'
  UNION
  SELECT a->>'pointer' FROM jsonb_array_elements(p_rows) r
   CROSS JOIN LATERAL jsonb_array_elements(r->'anchors') a
  WHERE r->>'semantic_type'='structural.located_participant' AND a->>'pointer' NOT LIKE '%/data/table_cells/%'
   AND data.record_source_json(r->'value')->>'role'='table_role_declaration'
 ) candidates WHERE pointer IS NOT NULL;
 IF pointers IS NOT NULL THEN
  SELECT coalesce(jsonb_object_agg(pointer,native_json),'{}') INTO nodes
  FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,pointers);
  SELECT array_agg(DISTINCT c->>'$ref') INTO pointers FROM jsonb_each(nodes) n
  CROSS JOIN LATERAL jsonb_array_elements(n.value->'captions') c WHERE n.value->>'label'='table';
  IF pointers IS NOT NULL THEN
   SELECT coalesce(jsonb_object_agg(pointer,native_json->>'text'),'{}') INTO captions
   FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,pointers)
   WHERE native_json->>'label'='caption';
  END IF;
 END IF;
 WITH navigation AS MATERIALIZED (
  SELECT jsonb_build_object('layer',p.key::jsonb,'local_id',a->>'local_id') ref,a node,a->'navigation' nav
  FROM jsonb_each(p_layers) p CROSS JOIN LATERAL jsonb_array_elements(p.value->'annotations') a
  WHERE a->>'kind'='construction.navigation' AND a->'navigation'->>'codec'='source-navigation-v1'
 ), participants AS MATERIALIZED (
  SELECT r->>'contribution_id' AS id,r->'pin' AS pin,r->'anchors'->0 AS anchor,
   data.record_source_json(r->'value') AS meaning
  FROM jsonb_array_elements(p_rows) r
  WHERE r->>'semantic_type'='structural.located_participant' AND jsonb_array_length(r->'anchors')=1
 ), selected_cells AS MATERIALIZED (
  SELECT p.id,p.pin,p.anchor,p.meaning,x.coordinate[1] AS table_ref,c.cell,
   (c.cell->>'start_row_offset_idx')::integer AS r0,(c.cell->>'end_row_offset_idx')::integer AS r1,
   (c.cell->>'start_col_offset_idx')::integer AS c0,(c.cell->>'end_col_offset_idx')::integer AS c1
  FROM participants p CROSS JOIN LATERAL (
   SELECT regexp_match(p.anchor->>'pointer','^(.*)/data/table_cells/([0-9]+)$') AS coordinate
  ) x CROSS JOIN LATERAL (
   SELECT nodes->x.coordinate[1]->'data'->'table_cells'->(x.coordinate[2]::integer) AS cell
  ) c
  JOIN LATERAL jsonb_array_elements(v.projection->'pieces') piece
   ON piece->>'source_field'='cell_text' AND piece->>'item_ref'=x.coordinate[1] AND piece->>'cell_index'=x.coordinate[2]
  WHERE c.cell IS NOT NULL AND p.anchor->>'precision'='exact' AND p.anchor->>'space'='native'
   AND p.anchor->>'start'='0' AND (p.anchor->>'end')::integer=length(c.cell->>'text')
   AND p.anchor->>'source_piece'=c.cell->>'text' AND p.meaning->>'text'=c.cell->>'text'
   AND p.pin->>'source_view_id'=v.id::text AND p.pin->>'product_digest'=v.native_content_digest
 ), edges AS MATERIALIZED (
  SELECT r->>'contribution_id' AS id,r->'computation_dependencies' AS deps,s.id AS subject,t.id AS target,
   s.table_ref AS region,s.r0,s.r1,st.table_ref AS schematic,
   s.c0 AS sc0,s.c1 AS sc1,st.r0 AS tr0,st.r1 AS tr1,st.c0 AS tc0,st.c1 AS tc1,
   s.anchor AS source_anchor,t.anchor AS target_anchor,m.value->>'relation' AS role,m.value->>'basis' AS basis,
   (st.table_ref=s.table_ref AND t.meaning->>'role'='header' AND m.value->>'relation' IN ('header','unit','value_role')
    AND m.value->>'basis' IN ('native_geometry','matched_cue')) IS TRUE AS header,
   st.cell->>'text' AS symbol,t.meaning->>'role' AS target_role
  FROM jsonb_array_elements(p_rows) r
  CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') AS value) m
  JOIN selected_cells s ON s.id=m.value->>'subject_id'
  JOIN participants t ON t.id=m.value->>'target_id'
  LEFT JOIN selected_cells st ON st.id=t.id
  WHERE r->>'semantic_type'='structural.scoped_attachment' AND m.value->>'protocol'='scoped-attachment-1'
   AND m.value->>'relation' IN ('header','note','unit','value_role')
   AND m.value->>'region'=s.table_ref AND m.value->>'scope'=s.table_ref
   AND r->'pin'=s.pin AND t.pin=s.pin AND s.meaning->>'role'='cell'
   AND r->'component'->>'kind'='scoped_attachment'
   AND r->'component'->>'attachment_contribution_id'=s.id
   AND r->'component'->>'target_contribution_id'=t.id
   AND r->'component'->>'attachment_kind'=m.value->>'relation'
   AND r->'component'->>'scope'=s.table_ref
   AND m.value->'dependencies'=r->'computation_dependencies'
   AND EXISTS (SELECT FROM jsonb_array_elements(r->'component'->'bases') b
    WHERE b->>'kind'=m.value->>'basis')
   AND (st.id IS NOT NULL OR t.meaning->>'role' IN ('note','table_role_declaration'))
 ), role_edges AS MATERIALIZED (
  SELECT *,subject||'/'||role||'/'||CASE WHEN role='value_role' THEN role
   WHEN role='header' AND header THEN '('||tr0||', '||tr1||')' ELSE id END AS axis,
   (header AND (sc1<=tc0 OR tc1<=sc0)) IS TRUE AS disjoint,
   ((header AND tc0<=sc0 AND sc1<=tc1 AND tr1<=r0)
    OR (role IN ('note','unit') AND basis='matched_cue')) IS TRUE AS direct,
   jsonb_build_array(id,subject,target) AS evidence
  FROM edges
 ), declarations AS MATERIALIZED (
  SELECT d.id,d.anchor,d.meaning->>'region' AS region,
   ARRAY[ops.primary_navigation_role_text(p_layers,schematic.ref,schematic.node,'observed',v),ops.primary_navigation_role_text(p_layers,schematic.ref,schematic.node,'schematic',v)] AS parts,
   ARRAY(SELECT ops.primary_navigation_role_text(p_layers,role.ref,role.node,r->>'role',v)
    FROM jsonb_array_elements(role.nav->'roles') r WHERE r->>'role' LIKE 'symbol/%' ORDER BY r->>'role') AS symbols
  FROM participants d JOIN navigation role ON role.ref=d.meaning->'primary_node'
  JOIN navigation schematic ON schematic.nav->>'pointer'=role.nav->>'pointer' AND schematic.nav->>'kind'='table_schematic'
  WHERE d.meaning->>'role'='table_role_declaration' AND role.nav->>'kind'='table_role'
   AND d.meaning->>'measure_role'=role.nav->>'measure_role'
   AND ops.primary_navigation_role_matches(p_layers,role.ref,role.node,'cue',v,
    (SELECT r FROM jsonb_array_elements(p_rows) r WHERE r->>'contribution_id'=d.id))
 ), bindings AS (
  SELECT e.region,e.r0,e.r1,e.schematic,d.anchor->>'pointer' AS declaration_pointer,
   cap0.pointer AS observed_caption,cap1.pointer AS schematic_caption,
   e.id,e.subject,e.target,
   CASE WHEN (e.r0,e.r1,e.sc0,e.sc1)=(e.tr0,e.tr1,e.tc0,e.tc1) THEN 'exact' ELSE 'overlap' END AS alignment,
   jsonb_build_object('dependencies',e.evidence||jsonb_build_array(d.id),
    'observed_anchor',e.source_anchor->'anchor_id','schematic_anchor',e.target_anchor->'anchor_id',
    'declaration_anchor',d.anchor->'anchor_id') AS binding
  FROM role_edges e JOIN declarations d ON e.deps ? d.id AND d.region=e.region
  CROSS JOIN LATERAL (SELECT c->>'$ref' AS pointer FROM jsonb_array_elements(nodes->e.region->'captions') c
   WHERE EXISTS(SELECT FROM navigation a WHERE a.nav->>'pointer'=c->>'$ref'
    AND a.nav->>'kind' IN ('artifact_mention','artifact_reference') AND a.nav->>'artifact_kind'='table' AND a.nav->>'designator'=d.parts[1])) cap0
  CROSS JOIN LATERAL (SELECT c->>'$ref' AS pointer FROM jsonb_array_elements(nodes->e.schematic->'captions') c
   WHERE EXISTS(SELECT FROM navigation a WHERE a.nav->>'pointer'=c->>'$ref'
    AND a.nav->>'kind' IN ('artifact_mention','artifact_reference') AND a.nav->>'artifact_kind'='table' AND a.nav->>'designator'=d.parts[2])) cap1
  WHERE e.role='value_role' AND e.basis='matched_cue' AND e.region<>e.schematic
   AND e.source_anchor->>'source_piece' ~ '^\s*[0-9]+\s*$'
   AND CASE WHEN btrim(e.symbol) ~ '^s[0-9]+$' THEN 'sij' ELSE lower(btrim(e.symbol)) END
    =ANY(SELECT lower(s) FROM unnest(d.symbols) s)
   AND e.r0<e.tr1 AND e.tr0<e.r1 AND e.sc0<e.tc1 AND e.tc0<e.sc1
 ), alternatives AS (
  SELECT region,r0,r1,schematic,declaration_pointer,observed_caption,schematic_caption,
   count(*)=count(DISTINCT subject) AND count(*)=count(DISTINCT target) AND bool_and(alignment='exact')
    AND (nodes->region->'data'->'num_rows',nodes->region->'data'->'num_cols')
    =(nodes->schematic->'data'->'num_rows',nodes->schematic->'data'->'num_cols') AS exact,
   jsonb_object_agg(id,binding||jsonb_build_object('alignment',alignment) ORDER BY id COLLATE "C") AS proof
  FROM bindings GROUP BY region,r0,r1,schematic,declaration_pointer,observed_caption,schematic_caption
 ), band_premises AS (
  SELECT region,r0,r1,jsonb_agg(premise||jsonb_build_object('identity',
    'table-correspondence:'||encode(sha256(convert_to(data.canonical_json(premise),'UTF8')),'hex'),
    'standing',CASE WHEN alternative_count=1 AND exact THEN 'fixed' ELSE 'alternative' END)
    ORDER BY schematic COLLATE "C",declaration_pointer COLLATE "C",observed_caption COLLATE "C",
     schematic_caption COLLATE "C") AS premises
  FROM (SELECT *,count(*) OVER(PARTITION BY region,r0,r1) AS alternative_count,
   jsonb_build_object('source_revision',v.native_content_digest,'source_view_id',v.id,
    'source_projection',v.projection_digest,'source_recipe',v.recipe_digest,'observed_table',region,
    'schematic_table',schematic,'observed_caption',observed_caption,'schematic_caption',schematic_caption,
    'declaration_pointer',declaration_pointer,'bindings',proof) AS premise FROM alternatives) a
  GROUP BY region,r0,r1
 ), bands AS (
  SELECT region,r0,r1,count(*) AS edge_count,
   jsonb_agg(jsonb_build_object('id',id,'axis',axis,'role',role,'direct',direct,
    'disjoint',disjoint,'evidence',evidence) ORDER BY id COLLATE "C") AS edges,
   'source correspondence for '||region||' row ['||r0||', '||r1||')' AS question
  FROM role_edges GROUP BY region,r0,r1
 ), band_ids AS (
  SELECT b.*,coalesce(h.premises,'[]') AS premises,
   (SELECT jsonb_agg(id ORDER BY id COLLATE "C") FROM (
    SELECT DISTINCT k.id FROM role_edges e
    CROSS JOIN LATERAL jsonb_array_elements_text(e.evidence) k(id)
    WHERE (e.region,e.r0,e.r1)=(b.region,b.r0,b.r1)
    UNION SELECT DISTINCT x.id FROM bindings q
    CROSS JOIN LATERAL jsonb_array_elements_text(q.binding->'dependencies') x(id)
    WHERE (q.region,q.r0,q.r1)=(b.region,b.r0,b.r1)
   ) selected) AS ids
  FROM bands b LEFT JOIN band_premises h USING(region,r0,r1)
 ), prepared AS (
  SELECT b.*,(SELECT jsonb_agg(dep ORDER BY dep COLLATE "C") FROM (
   SELECT DISTINCT dep FROM jsonb_array_elements(p_rows) r
   CROSS JOIN LATERAL jsonb_array_elements_text(r->'computation_dependencies') d(dep)
   WHERE b.ids ? (r->>'contribution_id')
   UNION SELECT jsonb_array_elements_text(b.ids)) deps) AS dependencies
  FROM band_ids b
 ), questions AS (
  SELECT *,'contribution-operation:'||encode(sha256(convert_to(data.canonical_json(
    jsonb_build_array(jsonb_build_array('local-interpretation-2',question,ids,dependencies),'{}'::jsonb)),
    'UTF8')),'hex') AS scope_id FROM prepared
 )
 SELECT coalesce(jsonb_agg(jsonb_build_object('scope_id',scope_id,'question',question,
  'contribution_ids',ids,'dependencies',dependencies,'reason',
  CASE WHEN edge_count>16 THEN 'Exact correspondence policy permits at most 16 retained attachments per row.'
   ELSE NULL END,
  'request',CASE WHEN edge_count<=16 THEN ops.table_correspondence_band(edges,premises,dependencies,
   v.native_content_digest,v.projection_digest,scope_id,p_scale) ELSE NULL END)
  ORDER BY region COLLATE "C",r0,r1),'[]') INTO requests FROM questions;
 IF requests='[]'::jsonb THEN
  RETURN (SELECT jsonb_build_array(jsonb_build_object('scope_id',
   'contribution-operation:'||encode(sha256(convert_to(data.canonical_json(
    jsonb_build_array(jsonb_build_array('local-interpretation-2',question,'[]'::jsonb,deps),
     '{}'::jsonb)),'UTF8')),'hex'),
   'question',question,'contribution_ids','[]'::jsonb,'dependencies',deps,
   'reason','No eligible table correspondence band in the selected source view.',
   'request',NULL))
  FROM (SELECT 'source correspondence availability for view '||v.id AS question,
   jsonb_build_array('source-projection:'||v.projection_digest) AS deps) unavailable);
 END IF;
 RETURN requests;
END $$;
REVOKE ALL ON FUNCTION ops.table_correspondence_requests(kb.source_view,jsonb,numeric,jsonb) FROM PUBLIC;



CREATE OR REPLACE FUNCTION ops.prepare_table_correspondence(p_run bigint,p_view bigint,p_rows jsonb,p_scale numeric,p_layers jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE v kb.source_view; packet jsonb; layers jsonb:='{}'; item jsonb;
BEGIN
 SELECT s.* INTO STRICT v FROM kb.source_view s JOIN ops.run_source_view r ON r.source_view_id=s.id
 WHERE r.run_id=p_run AND s.id=p_view AND s.analysis_eligible;
 packet:=ops.read_primary_characterization(p_run,p_view,p_layers,8388608);
 FOR item IN SELECT value FROM jsonb_array_elements(packet->'layers') LOOP
  IF item->'payload'->'base_document' IS DISTINCT FROM jsonb_build_object('task_id',v.native_task_id,'product_key',v.native_product_key,'content_digest',v.native_content_digest)
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(item->'payload'->'source_scope'->'source_views') scope_ WHERE (scope_->>'source_view_id')::bigint=v.id AND scope_->>'projection_digest'=v.projection_digest) THEN
   RAISE EXCEPTION 'table correspondence primary layers differ from source base/projection' USING ERRCODE='23514'; END IF;
  layers:=layers||jsonb_build_object(data.canonical_json(item->'reference'),item->'payload');
 END LOOP;
 RETURN ops.table_correspondence_requests(v,p_rows,p_scale,layers);
EXCEPTION WHEN no_data_found THEN RAISE EXCEPTION 'table correspondence requires exact selected native source and primary layers' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.prepare_table_correspondence(bigint,bigint,jsonb,numeric,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.prepare_table_correspondence(bigint,bigint,jsonb,numeric,jsonb) TO corpus_sem_reader,corpus_sem_writer;



-- A projected extent must reconstruct the exact ordered physical anchors and
-- contain exactly the submitted retained tokens, apart from inter-token whitespace.
CREATE OR REPLACE FUNCTION ops.predicate_role_anchor_match(
 source_text text,source_pieces jsonb,extents jsonb,anchors jsonb,tokens jsonb,indices jsonb,
 lo bigint,hi bigint)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH extents_ AS (
  SELECT (e->>'start')::bigint AS a,(e->>'end')::bigint AS b,n,
   lag((e->>'end')::bigint) OVER(ORDER BY n) AS previous_end
  FROM jsonb_array_elements(extents) WITH ORDINALITY x(e,n)
 ), pieces AS (
  SELECT p,(p->>'start')::bigint AS a,(p->>'end')::bigint AS b,n
  FROM jsonb_array_elements(source_pieces) WITH ORDINALITY x(p,n)
 ), selected_tokens AS (
  SELECT (t->>'start')::bigint AS a,(t->>'end')::bigint AS b,n-1 AS i
  FROM jsonb_array_elements(tokens) WITH ORDINALITY x(t,n)
  WHERE indices @> jsonb_build_array(n-1)
 ), token_runs AS (
  SELECT e.n,t.a,t.b,lag(t.b) OVER(PARTITION BY e.n ORDER BY t.i) AS previous_end
  FROM extents_ e JOIN selected_tokens t ON e.a<=t.a AND t.b<=e.b
 ), physical AS (
  SELECT jsonb_agg(jsonb_build_array(
   p.p->>'item_ref'||CASE WHEN p.p->>'source_field'='cell_text'
    THEN '/data/table_cells/'||(p.p->>'cell_index') ELSE '' END,
   greatest(e.a,p.a)-p.a,least(e.b,p.b)-p.a
  ) ORDER BY e.n,p.n) AS anchors
  FROM extents_ e JOIN pieces p ON p.a<e.b AND p.b>e.a AND p.p->>'kind'='native_text'
 )
 SELECT jsonb_array_length(extents)>0 AND jsonb_array_length(indices)>0
 AND NOT EXISTS(SELECT FROM extents_ e WHERE e.a<lo OR e.b>hi OR e.a>=e.b OR e.previous_end>e.a)
 AND NOT EXISTS(SELECT FROM extents_ e JOIN pieces p ON p.a<e.b AND p.b>e.a
  WHERE p.p->>'kind'<>'native_text' OR coalesce(p.p->>'source_field','text') NOT IN ('text','orig','cell_text'))
 AND (SELECT jsonb_agg(i ORDER BY i) FROM selected_tokens) IS NOT DISTINCT FROM indices
 AND (SELECT count(*) FROM selected_tokens)=(SELECT count(*) FROM token_runs)
 AND NOT EXISTS(
  SELECT FROM extents_ e LEFT JOIN token_runs t USING(n)
  GROUP BY e.n,e.a,e.b HAVING min(t.a) IS DISTINCT FROM e.a OR max(t.b) IS DISTINCT FROM e.b
 )
 AND NOT EXISTS(
  SELECT FROM token_runs r WHERE r.previous_end IS NOT NULL AND
   substring(source_text FROM (r.previous_end+1)::integer FOR (r.a-r.previous_end)::integer)
    ~ '[^[:space:]]'
 )
 AND (SELECT physical.anchors FROM physical) IS NOT DISTINCT FROM (
  SELECT jsonb_agg(jsonb_build_array(a->>'pointer',a->'start',a->'end') ORDER BY n)
  FROM jsonb_array_elements(anchors) WITH ORDINALITY x(a,n)
  WHERE a->>'space'='native' AND a->>'precision'='exact'
 );
$$;
REVOKE ALL ON FUNCTION ops.predicate_role_anchor_match(text,jsonb,jsonb,jsonb,jsonb,jsonb,bigint,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.predicate_role_anchor_match(
 projection jsonb,extents jsonb,anchors jsonb,tokens jsonb,indices jsonb,lo bigint,hi bigint)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT ops.predicate_role_anchor_match(
  projection->>'text',projection->'pieces',extents,anchors,tokens,indices,lo,hi)
$$;
REVOKE ALL ON FUNCTION ops.predicate_role_anchor_match(jsonb,jsonb,jsonb,jsonb,jsonb,bigint,bigint) FROM PUBLIC;

-- Exact retained primary custody shared by current native consumer guards.
-- These helpers validate identities/relationships; none recognizes language.
CREATE OR REPLACE FUNCTION ops.primary_characterization_layers(p_run bigint,p_view kb.source_view,p_refs jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE packet jsonb; row_ jsonb; body jsonb; result jsonb:='{}';
BEGIN
 packet:=ops.read_primary_characterization(p_run,p_view.id,coalesce(p_refs,'[]'),8388608);
 FOR row_ IN SELECT value FROM jsonb_array_elements(packet->'layers') LOOP
  body:=row_->'payload';
  IF body->'base_document' IS DISTINCT FROM jsonb_build_object('task_id',p_view.native_task_id,'product_key',p_view.native_product_key,'content_digest',p_view.native_content_digest)
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(body->'source_scope'->'source_views') source_
    WHERE (source_->>'source_view_id')::bigint=p_view.id AND source_->>'projection_digest'=p_view.projection_digest) THEN
   RAISE EXCEPTION 'primary layer differs from exact selected source base/projection' USING ERRCODE='23514'; END IF;
  result:=result||jsonb_build_object(data.canonical_json(row_->'reference'),body);
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION ops.primary_characterization_layers(bigint,kb.source_view,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_characterization_layers(p_task ops.task,p_view kb.source_view,p_config jsonb)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT ops.primary_characterization_layers(p_task.run_id,p_view,coalesce(p_config->'characterization_layers','[]'))
$$;
REVOKE ALL ON FUNCTION ops.primary_characterization_layers(ops.task,kb.source_view,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_characterization_node(p_layers jsonb,p_ref jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE body jsonb:=p_layers->data.canonical_json(p_ref->'layer'); node jsonb;
BEGIN
 IF body IS NULL THEN RAISE EXCEPTION 'primary node layer is not an exact configured input' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT node FROM jsonb_array_elements(coalesce(body->'annotations','[]')||coalesce(body->'terms','[]')||coalesce(body->'roles','[]')||coalesce(body->'memberships','[]'))
 WHERE value->>'local_id'=p_ref->>'local_id';
 RETURN node;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'primary node does not resolve to one retained inventory member' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.primary_characterization_node(jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_characterization_in_view(p_layers jsonb,p_ref jsonb,p_node jsonb,p_view bigint)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT count(*)>0 AND bool_and((e->>'source_view_id')::bigint=p_view)
 FROM jsonb_array_elements(p_layers->data.canonical_json(p_ref->'layer')->'occurrences') o
 CROSS JOIN LATERAL jsonb_array_elements(o->'extents') e WHERE coalesce(p_node->'occurrences','[]') ? (o->>'local_id')
$$;
REVOKE ALL ON FUNCTION ops.primary_characterization_in_view(jsonb,jsonb,jsonb,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_characterization_child(p_layers jsonb,p_ref jsonb,p_node jsonb,p_role text)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE edge jsonb;
BEGIN
 SELECT value INTO STRICT edge FROM jsonb_array_elements(coalesce(p_node->'children','[]')) WHERE value->>'role'=p_role;
 IF NOT edge ? 'target' OR edge ? 'choice_group' THEN
  RAISE EXCEPTION 'primary child is an unresolved analytical site' USING ERRCODE='23514'; END IF;
 RETURN ops.primary_characterization_node(p_layers,jsonb_build_object('layer',p_ref->'layer','local_id',edge->>'target'));
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'primary child role is not one exact retained target' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.primary_characterization_child(jsonb,jsonb,jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_characterization_extents(p_layers jsonb,p_ref jsonb,p_node jsonb,p_view kb.source_view)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE body jsonb:=p_layers->data.canonical_json(p_ref->'layer'); oid text; occurrence jsonb; extent jsonb; result jsonb:='[]';
BEGIN
 IF body IS NULL THEN RAISE EXCEPTION 'primary extent layer is not selected' USING ERRCODE='23514'; END IF;
 FOR oid IN SELECT jsonb_array_elements_text(coalesce(p_node->'occurrences','[]')) LOOP
  SELECT value INTO STRICT occurrence FROM jsonb_array_elements(body->'occurrences') WHERE value->>'local_id'=oid;
  FOR extent IN SELECT value FROM jsonb_array_elements(occurrence->'extents') LOOP
   IF extent->>'projection' IS DISTINCT FROM p_view.projection_digest OR (extent->>'source_view_id')::bigint IS DISTINCT FROM p_view.id
    OR (extent ? 'start' AND ((extent->>'start')::bigint<0 OR (extent->>'end')::bigint>(char_length(p_view.projection->>'text'))))
    OR (extent->>'synthetic'='false' AND extent ? 'text' AND extent->>'text' IS DISTINCT FROM
     substring(p_view.projection->>'text' FROM (extent->>'start')::integer+1 FOR (extent->>'end')::integer-(extent->>'start')::integer)) THEN
    RAISE EXCEPTION 'primary extent differs from exact source projection' USING ERRCODE='23514'; END IF;
   result:=result||jsonb_build_array(extent);
  END LOOP;
 END LOOP;
 RETURN result;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'primary occurrence does not resolve within its retained layer' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.primary_characterization_extents(jsonb,jsonb,jsonb,kb.source_view) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_characterization_choices(p_layers jsonb,p_ref jsonb,p_node jsonb,p_selected jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE ref jsonb; member_ jsonb; group_ jsonb; body jsonb; required_ jsonb; local_ text; seen jsonb:='{}'; key_ text; count_ integer; site_ jsonb;
BEGIN
 IF jsonb_typeof(coalesce(p_selected,'[]'))<>'array' OR (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(coalesce(p_selected,'[]'))) THEN RETURN false; END IF;
 FOR local_ IN SELECT jsonb_array_elements_text(coalesce(p_node->'required_choices','[]')||coalesce(p_node->'choice_refs','[]')) LOOP
  IF NOT coalesce(p_selected,'[]') @> jsonb_build_array(jsonb_build_object('layer',p_ref->'layer','local_id',local_)) THEN RETURN false; END IF;
 END LOOP;
 IF NOT coalesce(p_selected,'[]') @> coalesce(p_node->'required_external_choices','[]') THEN RETURN false; END IF;
 FOR ref IN SELECT value FROM jsonb_array_elements(coalesce(p_selected,'[]')) LOOP
  body:=p_layers->data.canonical_json(ref->'layer');
  IF body IS NULL THEN RETURN false; END IF;
  SELECT g,m INTO STRICT group_,member_ FROM jsonb_array_elements(coalesce(body->'choices','[]')) g
   CROSS JOIN LATERAL jsonb_array_elements(g->'members') m WHERE m->>'local_id'=ref->>'local_id';
  key_:=data.canonical_json(jsonb_build_array(ref->'layer',group_->>'local_id'));
  count_:=coalesce((seen->>key_)::integer,0)+1;seen:=seen||jsonb_build_object(key_,count_);
  IF count_>1 AND group_->>'compatibility'<>'compatible' THEN RETURN false; END IF;
  required_:=coalesce(member_->'required_external_choices','[]');
  FOR local_ IN SELECT jsonb_array_elements_text(coalesce(member_->'required_choices','[]')) LOOP
   required_:=required_||jsonb_build_array(jsonb_build_object('layer',ref->'layer','local_id',local_));
  END LOOP;
  IF NOT coalesce(p_selected,'[]') @> required_ THEN RETURN false; END IF;
 END LOOP;
 FOR site_ IN SELECT value FROM jsonb_array_elements(coalesce(p_node->'children','[]')) WHERE value ? 'choice_group' LOOP
  body:=p_layers->data.canonical_json(p_ref->'layer');
  SELECT value INTO STRICT group_ FROM jsonb_array_elements(body->'choices') WHERE value->>'local_id'=site_->>'choice_group';
  IF (SELECT count(*) FROM jsonb_array_elements(group_->'members') m WHERE coalesce(p_selected,'[]') @>
   jsonb_build_array(jsonb_build_object('layer',p_ref->'layer','local_id',m->>'local_id')))<>1 THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
EXCEPTION WHEN no_data_found OR too_many_rows THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION ops.primary_characterization_choices(jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.predicate_primary_tokens(p_layers jsonb,p_ref jsonb,p_node jsonb,p_view kb.source_view)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE native_ref jsonb; first_ref jsonb; native_ jsonb; first_ jsonb; body jsonb; a jsonb; extents_ jsonb; result jsonb:='[]';
BEGIN
 FOR native_ref IN SELECT value FROM jsonb_array_elements(coalesce(p_node->'external_premises','[]')) LOOP
  native_:=ops.primary_characterization_node(p_layers,native_ref);
  IF native_->>'kind' IS DISTINCT FROM 'native.token' OR native_->>'native_scheme' IS DISTINCT FROM 'spacy-token-columns-1' THEN
   RAISE EXCEPTION 'predicate member requires exact native token premises' USING ERRCODE='23514'; END IF;
  IF first_ref IS NULL THEN first_ref:=native_ref;first_:=native_; END IF;
  IF native_ref->'layer' IS DISTINCT FROM first_ref->'layer'
   OR native_->'native_token'->>'container' IS DISTINCT FROM first_->'native_token'->>'container'
   OR native_->'native_token'->>'native_run' IS DISTINCT FROM first_->'native_token'->>'native_run' THEN
   RAISE EXCEPTION 'predicate member mixes native token containers' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF first_ref IS NULL THEN RAISE EXCEPTION 'predicate member has no native token support' USING ERRCODE='23514'; END IF;
 body:=p_layers->data.canonical_json(first_ref->'layer');
 FOR a IN SELECT value FROM jsonb_array_elements(body->'annotations')
  WHERE value->'native_token'->>'container'=first_->'native_token'->>'container'
   AND value->'native_token'->>'native_run'=first_->'native_token'->>'native_run'
  ORDER BY (value->'native_token'->>'index')::integer LOOP
  IF (a->'native_token'->>'index')::integer<>jsonb_array_length(result) THEN
   RAISE EXCEPTION 'predicate native container omits original token indices' USING ERRCODE='23514'; END IF;
  extents_:=ops.primary_characterization_extents(p_layers,jsonb_build_object('layer',first_ref->'layer','local_id',a->>'local_id'),a,p_view);
  result:=result||jsonb_build_array(a->'native_token'||jsonb_build_object(
   'start',(SELECT min((e->>'start')::bigint) FROM jsonb_array_elements(extents_) e),
   'end',(SELECT max((e->>'end')::bigint) FROM jsonb_array_elements(extents_) e)));
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION ops.predicate_primary_tokens(jsonb,jsonb,jsonb,kb.source_view) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.predicate_primary_member_matches(
 p_layers jsonb,p_ref jsonb,p_node jsonb,p_view kb.source_view,p_lo bigint,p_hi bigint,
 p_extents jsonb,p_anchors jsonb,p_indices jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE tokens jsonb; original_ jsonb; expected jsonb; mapped int8multirange; source_ int8multirange; actual_ int8multirange;
BEGIN
 tokens:=ops.predicate_primary_tokens(p_layers,p_ref,p_node,p_view);
 original_:=ops.primary_characterization_extents(p_layers,p_ref,p_node,p_view);
 SELECT coalesce(range_agg(int8range((piece->>'start')::bigint,(piece->>'end')::bigint,'[)')),'{}') INTO mapped
 FROM jsonb_array_elements(p_view.projection->'pieces') piece
 WHERE piece->>'kind'='native_text' AND coalesce(piece->>'source_field','text') IN ('text','orig','cell_text');
 SELECT coalesce(range_agg(int8range((e->>'start')::bigint,(e->>'end')::bigint,'[)')),'{}') INTO source_
 FROM jsonb_array_elements(original_) e;
 SELECT coalesce(range_agg(int8range((e->>'start')::bigint,(e->>'end')::bigint,'[)')),'{}') INTO actual_
 FROM jsonb_array_elements(p_extents) e;
 SELECT coalesce(jsonb_agg((native_->'native_token'->>'index')::integer ORDER BY (native_->'native_token'->>'index')::integer),'[]') INTO expected
 FROM jsonb_array_elements(coalesce(p_node->'external_premises','[]')) ref
 CROSS JOIN LATERAL (SELECT ops.primary_characterization_node(p_layers,ref) native_) n
 CROSS JOIN LATERAL (SELECT tokens->((native_->'native_token'->>'index')::integer) token_) t
 WHERE (token_->>'start')::bigint>=p_lo AND (token_->>'end')::bigint<=p_hi
  AND mapped @> int8range((token_->>'start')::bigint,(token_->>'end')::bigint,'[)');
 RETURN source_ @> actual_ AND p_indices IS NOT DISTINCT FROM expected
  AND ops.predicate_role_anchor_match(p_view.projection,p_extents,p_anchors,tokens,p_indices,p_lo,p_hi);
END $$;
REVOKE ALL ON FUNCTION ops.predicate_primary_member_matches(jsonb,jsonb,jsonb,kb.source_view,bigint,bigint,jsonb,jsonb,jsonb) FROM PUBLIC;

-- One exact role-to-source projection for primary navigation consumers.
CREATE OR REPLACE FUNCTION ops.primary_navigation_role_extents(p_layers jsonb,p_ref jsonb,p_node jsonb,p_role text,p_view kb.source_view)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE role_ jsonb; result jsonb;
BEGIN
 SELECT value INTO STRICT role_ FROM jsonb_array_elements(p_node->'navigation'->'roles') WHERE value->>'role'=p_role;
 result:=ops.primary_characterization_extents(p_layers,p_ref,jsonb_build_object('occurrences',role_->'occurrences'),p_view);
 IF jsonb_array_length(result)=0 OR EXISTS(SELECT FROM jsonb_array_elements(result) e WHERE coalesce((e->>'synthetic')::boolean,true) OR (e->>'start')::bigint>=(e->>'end')::bigint) THEN
  RAISE EXCEPTION 'navigation role has no exact literal source extent' USING ERRCODE='23514'; END IF;
 RETURN result;
EXCEPTION WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'navigation role is not one retained role binding' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.primary_navigation_role_extents(jsonb,jsonb,jsonb,text,kb.source_view) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_navigation_role_matches(p_layers jsonb,p_ref jsonb,p_node jsonb,p_role text,p_view kb.source_view,p_row jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE extents_ jsonb:=ops.primary_navigation_role_extents(p_layers,p_ref,p_node,p_role,p_view); expected_ jsonb; actual_ jsonb;
 value_ jsonb:=data.record_source_json(p_row->'value'); lo bigint; hi bigint; text_ text;
BEGIN
 SELECT min((e->>'start')::bigint),max((e->>'end')::bigint),string_agg(substring(p_view.projection->>'text' FROM (e->>'start')::integer+1 FOR (e->>'end')::integer-(e->>'start')::integer),'' ORDER BY n)
 INTO lo,hi,text_ FROM jsonb_array_elements(extents_) WITH ORDINALITY x(e,n);
 SELECT jsonb_agg(jsonb_build_array(p->>'item_ref'||CASE WHEN p->>'source_field'='cell_text' THEN '/data/table_cells/'||(p->>'cell_index') ELSE '' END,
  greatest((e->>'start')::bigint,(p->>'start')::bigint)-(p->>'start')::bigint,
  least((e->>'end')::bigint,(p->>'end')::bigint)-(p->>'start')::bigint) ORDER BY en,pn) INTO expected_
 FROM jsonb_array_elements(extents_) WITH ORDINALITY x(e,en)
 JOIN jsonb_array_elements(p_view.projection->'pieces') WITH ORDINALITY y(p,pn)
  ON (p->>'start')::bigint<(e->>'end')::bigint AND (p->>'end')::bigint>(e->>'start')::bigint
 WHERE p->>'kind'='native_text' AND coalesce(p->>'source_field','text') IN ('text','orig','cell_text');
 SELECT jsonb_agg(jsonb_build_array(a->>'pointer',a->'start',a->'end') ORDER BY n) INTO actual_
 FROM jsonb_array_elements(p_row->'anchors') WITH ORDINALITY x(a,n)
 WHERE a->>'space'='native' AND a->>'precision'='exact';
 RETURN expected_ IS NOT NULL AND expected_=actual_ AND jsonb_array_length(p_row->'anchors')=jsonb_array_length(expected_)
  AND value_->>'text' IS NOT DISTINCT FROM text_
  AND (NOT value_ ? 'start' OR value_->'start'=to_jsonb(lo)) AND (NOT value_ ? 'end' OR value_->'end'=to_jsonb(hi))
  AND (NOT value_ ? 'source_pointer' OR value_->>'source_pointer'=p_node->'navigation'->>'pointer' OR value_->>'source_pointer'=p_row->'anchors'->0->>'pointer');
END $$;
REVOKE ALL ON FUNCTION ops.primary_navigation_role_matches(jsonb,jsonb,jsonb,text,kb.source_view,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_navigation_node(p_layers jsonb,p_ref jsonb,p_choices jsonb,p_view kb.source_view)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE node jsonb:=ops.primary_characterization_node(p_layers,p_ref); binding jsonb; token_ jsonb; nav jsonb;
BEGIN
 nav:=node->'navigation';
 IF node->>'kind' IS DISTINCT FROM 'construction.navigation' OR node->>'family' IS DISTINCT FROM 'construction.navigation'
  OR nav->>'codec' IS DISTINCT FROM 'source-navigation-v1' OR NOT ops.primary_characterization_choices(p_layers,p_ref,node,p_choices) THEN
  RAISE EXCEPTION 'navigation witness is not an exact retained primary annotation with conserved choices' USING ERRCODE='23514'; END IF;
 PERFORM ops.primary_characterization_extents(p_layers,p_ref,node,p_view);
 FOR binding IN SELECT value FROM jsonb_array_elements(coalesce(nav->'native_tokens','[]')) LOOP
  token_:=ops.primary_characterization_node(p_layers,binding->'native_node');
  IF token_->>'kind' IS DISTINCT FROM 'native.token' OR token_->>'native_scheme' IS DISTINCT FROM 'spacy-token-columns-1'
   OR binding->'index' IS DISTINCT FROM token_->'native_token'->'index'
   OR token_->'native_token'->>'container' IS DISTINCT FROM 'spacy/'||p_view.id||'/'||(nav->>'block')||'/block' THEN
   RAISE EXCEPTION 'navigation named token differs from exact native endpoint' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN node;
END $$;
REVOKE ALL ON FUNCTION ops.primary_navigation_node(jsonb,jsonb,jsonb,kb.source_view) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_primary_named_links(t ops.task,v kb.source_view,config_ jsonb,population jsonb,operation_map jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE layers jsonb:=coalesce(config_->'_primary_layers',ops.primary_characterization_layers(t,v,config_));
 op jsonb; row_ jsonb; value_ jsonb; proof jsonb; ref jsonb; node jsonb; nav jsonb; selected_ jsonb; source_ jsonb; source_id text;
 extents_ jsonb; role_ text; field_ text; expected_ jsonb; tokens_ jsonb; expected_resolution text; lo bigint; hi bigint;
 subject_ jsonb; target_ jsonb; cue_ jsonb; relation_ jsonb; subject_value jsonb; target_value jsonb; cue_value jsonb;
 key_ text; candidate_ids text[]; actual_ids text[]; count_ integer; origin_body jsonb; layer_ record; primary_ jsonb; subject_span jsonb; cue_span jsonb; piece_ jsonb; inspected_ integer;
BEGIN
 IF NOT EXISTS(SELECT FROM jsonb_each(operation_map) o WHERE o.value->>'question'='source_named_links') THEN RETURN; END IF;
 PERFORM ops.validate_structural_input(config_->'inputs');
 SELECT s INTO STRICT source_ FROM jsonb_array_elements(config_->'inputs'->'sources') s WHERE (s->>'source_view_id')::bigint=v.id;
 source_id:=encode(sha256(convert_to(data.canonical_json(source_),'UTF8')),'hex');
 SELECT value INTO STRICT op FROM jsonb_each(operation_map) WHERE value->>'question'='source_named_links';
 IF NOT coalesce(config_->'characterization_layers','[]') @> coalesce(op->'primary_layers','[]') THEN RAISE EXCEPTION 'named operation uses unconfigured primary layers' USING ERRCODE='23514'; END IF;
 SELECT count(DISTINCT a->'navigation'->>'pointer') INTO inspected_ FROM jsonb_each(layers) l
 CROSS JOIN LATERAL jsonb_array_elements(l.value->'annotations') a
 WHERE a->'navigation'->>'kind'='named_availability' AND a->'navigation'->>'status'='complete'
 AND EXISTS(SELECT FROM jsonb_array_elements(config_->'inputs'->'passages') passage_
  CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN ops.primary_characterization_in_view(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a,v.id) THEN ops.primary_navigation_role_extents(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a,'source',v) ELSE '[]'::jsonb END) e
  WHERE passage_->>'source_ref'=source_id AND (e->>'start')::bigint<(passage_->>'end')::bigint AND (passage_->>'start')::bigint<(e->>'end')::bigint);
 IF op->'inspected_count' IS DISTINCT FROM to_jsonb(inspected_) THEN RAISE EXCEPTION 'named operation changes retained examined population' USING ERRCODE='23514'; END IF;
 FOR layer_ IN SELECT * FROM jsonb_each(layers) LOOP
  FOR primary_ IN SELECT value FROM jsonb_array_elements(layer_.value->'annotations') WHERE value->'navigation'->>'kind'='named_link' AND ops.primary_characterization_in_view(layers,jsonb_build_object('layer',layer_.key::jsonb,'local_id',value->>'local_id'),value,v.id) LOOP
   ref:=jsonb_build_object('layer',layer_.key::jsonb,'local_id',primary_->>'local_id');
   subject_span:=ops.primary_navigation_role_extents(layers,ref,primary_,'subject',v);cue_span:=ops.primary_navigation_role_extents(layers,ref,primary_,'cue',v);
   FOR selected_ IN SELECT value FROM jsonb_array_elements(config_->'inputs'->'passages') WHERE value->>'source_ref'=source_id LOOP
    IF NOT EXISTS(SELECT FROM jsonb_array_elements(subject_span||cue_span) e WHERE (e->>'start')::bigint<(selected_->>'start')::bigint OR (e->>'end')::bigint>(selected_->>'end')::bigint) THEN
     IF (SELECT count(*) FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
      WHERE r->>'operation_key'=op->>'operation_key' AND m->>'role'='named_link_subject' AND m->>'region'=selected_->>'passage_id'
       AND m->'named_cue'->'primary_node'=ref)<>1 THEN RAISE EXCEPTION 'named operation omits or repeats a retained selected construction' USING ERRCODE='23514'; END IF;
    END IF;
   END LOOP;
  END LOOP;
 END LOOP;
 IF op->>'outcome'='succeeded' AND EXISTS(SELECT FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
  WHERE r->>'operation_key'=op->>'operation_key' AND m->>'role'='named_link_subject' AND m->'named_cue'->>'resolution'<>'located') THEN
  RAISE EXCEPTION 'named outcome hides unresolved retained evidence' USING ERRCODE='23514'; END IF;
 IF op ? 'annotation_origin_task_id' THEN
  SELECT r.body INTO STRICT origin_body FROM ops.task selected JOIN ops.task_result r ON r.task_id=coalesce(selected.reused_task_id,selected.id)
   JOIN ops.method_config cfg ON cfg.id=selected.method_config_id JOIN ops.method method ON method.id=cfg.method_id
  WHERE r.task_id=(op->>'annotation_origin_task_id')::bigint AND selected.run_id=(source_->>'run_id')::bigint
   AND selected.unit_type='source_view' AND selected.unit_id=v.id AND selected.status IN ('done','reused','empty')
   AND method.name='extract.m1_annotations' AND method.version='3' AND r.body->>'source'=v.key
   AND EXISTS(SELECT FROM ops.cut_task cut WHERE cut.cut_id=(source_->>'cut_id')::bigint AND cut.task_id=selected.id AND cut.origin_task_id=r.task_id);
  IF NOT coalesce(data.record_source_json(origin_body->'parse_detail')->'characterization_layers','[]') @> coalesce(op->'primary_layers','[]') THEN RAISE EXCEPTION 'named origin summary changes primary pins' USING ERRCODE='23514'; END IF;
 END IF;
 FOR row_ IN SELECT value FROM jsonb_array_elements(population) WHERE value->>'operation_key'=op->>'operation_key' AND value->>'kind'='occurrence' LOOP
  value_:=data.record_source_json(row_->'value');proof:=value_->'named_cue';ref:=proof->'primary_node';
  node:=ops.primary_navigation_node(layers,ref,coalesce(proof->'primary_choices','[]'),v);nav:=node->'navigation';
  IF nav->>'kind' IS DISTINCT FROM 'named_link' OR NOT coalesce(op->'primary_layers','[]') @> jsonb_build_array(ref->'layer') THEN RAISE EXCEPTION 'named occurrence lacks its primary named-link witness' USING ERRCODE='23514'; END IF;
  SELECT p INTO STRICT selected_ FROM jsonb_array_elements(config_->'inputs'->'passages') p WHERE p->>'source_ref'=source_id
   AND p->>'passage_id'=value_->>'region' AND p->>'scope'=proof->>'scope' AND p->>'effective_version' IS NOT DISTINCT FROM proof->>'effective_version';
  lo:=(selected_->>'start')::bigint;hi:=(selected_->>'end')::bigint;expected_resolution:=nav->>'resolution';
  SELECT coalesce(jsonb_object_agg(b->>'name',b->'index'),'{}') INTO tokens_ FROM jsonb_array_elements(coalesce(nav->'native_tokens','[]')) b;
  FOREACH field_ IN ARRAY ARRAY['rule','variant','mechanism','annotation','block','designator'] LOOP
   IF nullif(proof->field_,'null') IS DISTINCT FROM nav->field_ THEN RAISE EXCEPTION 'named proof changes retained metadata %',field_ USING ERRCODE='23514'; END IF;
  END LOOP;
  IF proof->>'kind' IS DISTINCT FROM nav->>'relation_kind' OR proof->'tokens' IS DISTINCT FROM tokens_ THEN RAISE EXCEPTION 'named proof changes retained token bindings or relation kind' USING ERRCODE='23514'; END IF;
  FOREACH field_ IN ARRAY ARRAY['subject','cue','argument'] LOOP
   IF EXISTS(SELECT FROM jsonb_array_elements(nav->'roles') r WHERE r->>'role'=field_) THEN
    extents_:=ops.primary_navigation_role_extents(layers,ref,node,field_,v);
    SELECT jsonb_build_array(min((e->>'start')::bigint),max((e->>'end')::bigint)) INTO expected_ FROM jsonb_array_elements(extents_) e;
    IF (expected_->>0)::bigint<lo OR (expected_->>1)::bigint>hi THEN
     IF field_='argument' THEN expected_:=NULL;expected_resolution:='insufficient_evidence'; ELSE RAISE EXCEPTION 'named source roles are outside selected passage' USING ERRCODE='23514'; END IF;
    END IF;
   ELSE expected_:=NULL; END IF;
   IF nullif(proof->field_,'null') IS DISTINCT FROM expected_ THEN RAISE EXCEPTION 'named proof changes retained role extent %',field_ USING ERRCODE='23514'; END IF;
  END LOOP;
  IF proof->>'resolution' IS DISTINCT FROM expected_resolution THEN RAISE EXCEPTION 'named proof promotes or changes retained resolution' USING ERRCODE='23514'; END IF;
  role_:=CASE value_->>'role' WHEN 'named_link_subject' THEN 'subject' WHEN 'named_link_cue' THEN 'cue' WHEN 'named_link_target' THEN 'argument' WHEN 'named_link_definition_subject' THEN 'definition_subject' END;
  IF role_ IS NULL OR NOT ops.primary_navigation_role_matches(layers,ref,node,role_,v,row_)
   OR (role_='argument' AND proof->>'resolution'<>'located')
   OR (role_='definition_subject' AND value_->>'definition_subject_kind' IS DISTINCT FROM nav->>'definition_subject_kind') THEN RAISE EXCEPTION 'named occurrence changes retained role or exact source anchors' USING ERRCODE='23514'; END IF;
  IF NOT coalesce(row_->'computation_dependencies','[]') ? (nav->>'annotation') THEN RAISE EXCEPTION 'named occurrence loses original annotation dependency' USING ERRCODE='23514'; END IF;
  IF role_='subject' THEN
   SELECT count(*) INTO count_ FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
   WHERE r->>'operation_key'=op->>'operation_key' AND r->>'kind'='occurrence' AND m->>'region'=value_->>'region' AND m->'named_cue'=proof AND m->>'role'='named_link_cue';
   IF count_<>1 THEN RAISE EXCEPTION 'named subject loses its unique retained cue' USING ERRCODE='23514'; END IF;
   SELECT count(*) INTO count_ FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
   WHERE r->>'operation_key'=op->>'operation_key' AND r->>'kind'='occurrence' AND m->>'region'=value_->>'region' AND m->'named_cue'=proof AND m->>'role'='named_link_target';
   IF count_<>(CASE proof->>'resolution' WHEN 'located' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'named source group loses exact located/unknown target state' USING ERRCODE='23514'; END IF;
  END IF;
 END LOOP;
 FOR relation_ IN SELECT value FROM jsonb_array_elements(population) WHERE value->>'operation_key'=op->>'operation_key' AND value->>'kind'='relation' LOOP
  IF relation_->'component'->>'interpretation'='supported' THEN RAISE EXCEPTION 'private named proposal has no released host support codec' USING ERRCODE='23514'; END IF;
  SELECT r INTO STRICT subject_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=relation_->'members'->>0;
  SELECT r INTO STRICT target_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=relation_->'members'->>1;
  IF relation_->'component'->>'attachment_kind'='procedure_reference' THEN
   SELECT r INTO STRICT row_ FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
   WHERE r->>'operation_key'=op->>'operation_key' AND m->>'role'='named_link_subject' AND relation_->'computation_dependencies' ? (r->>'contribution_id');
   proof:=data.record_source_json(row_->'value')->'named_cue';ref:=proof->'primary_node';node:=ops.primary_navigation_node(layers,ref,relation_->'component'->'primary_choices',v);nav:=node->'navigation';
   SELECT b->'native_node' INTO STRICT expected_ FROM jsonb_array_elements(nav->'native_tokens') b WHERE b->>'name'='verb';
    IF NOT ops.primary_navigation_role_matches(layers,expected_,jsonb_build_object('navigation',jsonb_build_object('pointer',nav->>'pointer','roles',jsonb_build_array(jsonb_build_object('role','action','occurrences',ops.primary_characterization_node(layers,expected_)->'occurrences')))),'action',v,subject_) THEN
     RAISE EXCEPTION 'procedure named reference changes its exact action token' USING ERRCODE='23514'; END IF;
   SELECT r INTO STRICT row_ FROM jsonb_array_elements(population) r WHERE r->'component'->>'attachment_kind'='artifact_reference_target'
    AND r->'members'->>1=target_->>'contribution_id' AND relation_->'computation_dependencies' ? (r->>'contribution_id');
   SELECT r INTO STRICT cue_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=row_->'members'->>0;
   IF NOT ops.primary_navigation_role_matches(layers,ref,node,'subject',v,cue_) THEN RAISE EXCEPTION 'procedure named reference changes its retained artifact mention' USING ERRCODE='23514'; END IF;
  ELSE
   subject_value:=data.record_source_json(subject_->'value');target_value:=data.record_source_json(target_->'value');proof:=subject_value->'named_cue';ref:=proof->'primary_node';
   node:=ops.primary_navigation_node(layers,ref,relation_->'component'->'primary_choices',v);nav:=node->'navigation';
   IF subject_value->>'role' IS DISTINCT FROM 'named_link_subject' OR target_value->>'role' IS DISTINCT FROM 'named_link_target'
    OR proof IS DISTINCT FROM target_value->'named_cue' OR proof->>'resolution' IS DISTINCT FROM 'located'
    OR relation_->'component'->>'attachment_kind' IS DISTINCT FROM nav->>'relation_kind' THEN RAISE EXCEPTION 'named relation changes retained directed subject/target roles' USING ERRCODE='23514'; END IF;
  END IF;
  SELECT r INTO STRICT cue_ FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
   WHERE r->>'operation_key'=op->>'operation_key' AND relation_->'computation_dependencies' ? (r->>'contribution_id') AND m->>'role'='named_link_cue' AND m->'named_cue'=proof;
  IF relation_->'component'->'primary_node' IS DISTINCT FROM ref OR relation_->'component'->>'scope' IS DISTINCT FROM proof->>'scope'
   OR relation_->'component'->>'effective_version' IS DISTINCT FROM proof->>'effective_version'
   OR relation_->'endpoints' IS DISTINCT FROM jsonb_build_array(jsonb_build_object('role','attachment','contribution_id',subject_->'contribution_id'),jsonb_build_object('role','target','contribution_id',target_->'contribution_id')) THEN RAISE EXCEPTION 'named relation loses exact primary identity, direction or scope' USING ERRCODE='23514'; END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'named primary evidence does not resolve exact retained source roles' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_primary_named_links(ops.task,kb.source_view,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_navigation_role_text(p_layers jsonb,p_ref jsonb,p_node jsonb,p_role text,p_view kb.source_view)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT string_agg(substring(p_view.projection->>'text' FROM (e->>'start')::integer+1 FOR (e->>'end')::integer-(e->>'start')::integer),'' ORDER BY n)
 FROM jsonb_array_elements(ops.primary_navigation_role_extents(p_layers,p_ref,p_node,p_role,p_view)) WITH ORDINALITY x(e,n)
$$;
REVOKE ALL ON FUNCTION ops.primary_navigation_role_text(jsonb,jsonb,jsonb,text,kb.source_view) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.primary_formal_symbol_matches(p_layers jsonb,p_view kb.source_view,p_row jsonb,p_symbol text)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT EXISTS(SELECT FROM jsonb_each(p_layers) layer_ CROSS JOIN LATERAL jsonb_array_elements(layer_.value->'annotations') a
 WHERE a->'formal'->'normalized'->>'kind'='identifier' AND a->'formal'->'normalized'->>'value'=p_symbol
  AND a->'formal'->'normalized'->>'domain_status' IN ('valid','not_requested')
  AND CASE WHEN ops.primary_characterization_in_view(p_layers,jsonb_build_object('layer',layer_.key::jsonb,'local_id',a->>'local_id'),a,p_view.id) THEN ops.primary_navigation_role_matches(p_layers,jsonb_build_object('layer',layer_.key::jsonb,'local_id',a->>'local_id'),
   jsonb_build_object('navigation',jsonb_build_object('roles',jsonb_build_array(jsonb_build_object('role','symbol','occurrences',a->'occurrences')))), 'symbol',p_view,p_row) ELSE false END)
$$;
REVOKE ALL ON FUNCTION ops.primary_formal_symbol_matches(jsonb,kb.source_view,jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_primary_source_navigation(t ops.task,v kb.source_view,config_ jsonb,population jsonb,operation_map jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE layers jsonb:=ops.primary_characterization_layers(t,v,config_); row_ jsonb; c jsonb; node jsonb; nav jsonb; ref jsonb;
 subject_ jsonb; target_ jsonb; sv jsonb; tv jsonb; kind_ text; target_node jsonb; target_ref jsonb; target_nav jsonb;
 declaration_ jsonb; earlier_ jsonb; cue_ jsonb; symbol_ text; source_piece jsonb; target_piece jsonb; source_item jsonb; target_item jsonb;
 occurrence_ jsonb; value_ jsonb; role_ text; expected_ text; op jsonb; matched_ integer; prior_count integer;
BEGIN
 FOR op IN SELECT value FROM jsonb_each(operation_map) WHERE value->>'question' IN ('source_structural_relations','source_named_links','source_witnessed_links') LOOP
  IF NOT coalesce(config_->'characterization_layers','[]') @> coalesce(op->'primary_layers','[]') THEN RAISE EXCEPTION 'navigation operation changes configured primary input population' USING ERRCODE='23514'; END IF;
 END LOOP;
 PERFORM ops.validate_primary_named_links(t,v,config_||jsonb_build_object('_primary_layers',layers),population,operation_map);
 FOR row_ IN SELECT value FROM jsonb_array_elements(population) WHERE value->>'kind'='relation' AND value->'component'->>'kind'='scoped_attachment' LOOP
  c:=row_->'component';kind_:=c->>'attachment_kind';
  IF operation_map->(row_->>'operation_key')->>'question'='source_named_links' THEN CONTINUE; END IF;
  IF kind_ NOT IN ('declares','artifact_reference_target','value_role','unit','note') OR NOT EXISTS(SELECT FROM jsonb_array_elements(c->'bases') b WHERE b->>'kind'='matched_cue') THEN CONTINUE; END IF;
  ref:=c->'primary_node';node:=ops.primary_navigation_node(layers,ref,c->'primary_choices',v);nav:=node->'navigation';
  IF NOT coalesce(operation_map->(row_->>'operation_key')->'primary_layers','[]') @> jsonb_build_array(ref->'layer') THEN RAISE EXCEPTION 'navigation relation changes exact operation primary origin' USING ERRCODE='23514'; END IF;
  IF c->>'interpretation'='supported' THEN RAISE EXCEPTION 'private navigation proposal has no released host support codec' USING ERRCODE='23514'; END IF;
  SELECT r INTO STRICT subject_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=row_->'members'->>0;
  SELECT r INTO STRICT target_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=row_->'members'->>1;
  sv:=data.record_source_json(subject_->'value');tv:=data.record_source_json(target_->'value');
  IF row_->'endpoints' IS DISTINCT FROM jsonb_build_array(jsonb_build_object('role','attachment','contribution_id',subject_->'contribution_id'),jsonb_build_object('role','target','contribution_id',target_->'contribution_id'))
   OR subject_->'pin' IS DISTINCT FROM row_->'pin' OR target_->'pin' IS DISTINCT FROM row_->'pin'
   OR NOT c->'dependencies' @> row_->'members' THEN RAISE EXCEPTION 'navigation relation changes exact directed source endpoints' USING ERRCODE='23514'; END IF;
  IF kind_='note' THEN
   IF nav->>'kind' IS DISTINCT FROM 'note_scope' THEN RAISE EXCEPTION 'note relation lacks retained scope annotation' USING ERRCODE='23514'; END IF;
   -- Native table association, complete note and cell geometry are checked by
   -- validate_source_table_note_scope against this same exact primary node.
  ELSIF kind_ IN ('unit','value_role') THEN
   IF nav->>'kind' IS DISTINCT FROM 'table_role' OR (nav->>'measure_role' NOT IN ('row_sum','column_sum','sample_count','observed_count') AND nav->>'measure_role' IS DISTINCT FROM kind_) THEN RAISE EXCEPTION 'table language role changes retained primary classification' USING ERRCODE='23514'; END IF;
   IF tv->>'role'='table_role_declaration' THEN
    IF NOT ops.primary_navigation_role_matches(layers,ref,node,'cue',v,target_) OR tv->>'measure_role' IS DISTINCT FROM nav->>'measure_role' THEN RAISE EXCEPTION 'table declaration changes retained source role' USING ERRCODE='23514'; END IF;
   ELSIF nav->>'measure_role' IN ('unit','value_role') THEN
    SELECT native_json INTO STRICT source_item FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[nav->>'pointer']);
    target_item:=source_item->'data'->'table_cells'->((nav->>'cell_index')::integer);
    IF nav->>'cell_index' IS NULL OR target_item IS NULL OR NOT (coalesce((target_item->>'column_header')::boolean,false) OR coalesce((target_item->>'row_header')::boolean,false))
     OR tv->>'source_pointer' IS DISTINCT FROM (nav->>'pointer')||'/data/table_cells/'||(nav->>'cell_index')
     OR tv->>'text' IS DISTINCT FROM target_item->>'text' OR jsonb_array_length(target_->'anchors')<>1
     OR target_->'anchors'->0->>'start' IS DISTINCT FROM '0' OR (target_->'anchors'->0->>'end')::integer IS DISTINCT FROM char_length(target_item->>'text') THEN
     RAISE EXCEPTION 'table header classification changes retained native cell and cue' USING ERRCODE='23514'; END IF;
   ELSE
    SELECT r INTO STRICT declaration_ FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
     WHERE row_->'computation_dependencies' ? (r->>'contribution_id') AND m->>'role'='table_role_declaration' AND m->'primary_node'=ref;
    IF NOT ops.primary_navigation_role_matches(layers,ref,node,'cue',v,declaration_) THEN RAISE EXCEPTION 'table correspondence loses exact retained role declaration' USING ERRCODE='23514'; END IF;
   END IF;
  ELSIF kind_='artifact_reference_target' THEN
   IF nav->>'kind' IS DISTINCT FROM 'artifact_reference' OR NOT ops.primary_navigation_role_matches(layers,ref,node,'subject',v,subject_) THEN RAISE EXCEPTION 'artifact source changes retained cued mention' USING ERRCODE='23514'; END IF;
   target_ref:=tv->'primary_node';
   IF target_ref IS NULL THEN
    SELECT jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a INTO STRICT target_ref,target_node
    FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'annotations') a
    WHERE a->'navigation'->>'kind' IN ('artifact_mention','artifact_reference') AND a->'navigation'->>'artifact_kind'=nav->>'artifact_kind'
     AND a->'navigation'->>'designator'=nav->>'designator' AND ops.primary_navigation_role_matches(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a,'subject',v,target_);
   ELSE target_node:=ops.primary_navigation_node(layers,target_ref,c->'primary_choices',v); END IF;
   target_nav:=target_node->'navigation';
   IF target_nav->>'artifact_kind' IS DISTINCT FROM nav->>'artifact_kind' OR target_nav->>'designator' IS DISTINCT FROM nav->>'designator'
    OR NOT ops.primary_navigation_role_matches(layers,target_ref,target_node,'subject',v,target_) THEN RAISE EXCEPTION 'artifact target changes exact retained controlled code' USING ERRCODE='23514'; END IF;
   SELECT native_json INTO STRICT target_item FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[target_nav->>'pointer']);
   SELECT native_json INTO STRICT source_item FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[target_item->'parent'->>'$ref']);
   IF target_item->>'label' IS DISTINCT FROM 'caption' OR source_item->>'label' IS DISTINCT FROM (CASE nav->>'artifact_kind' WHEN 'table' THEN 'table' WHEN 'figure' THEN 'picture' END) THEN RAISE EXCEPTION 'artifact target lacks original native caption association' USING ERRCODE='23514'; END IF;
  ELSIF nav->>'kind'='symbol_declaration' THEN
   IF NOT ops.primary_navigation_role_matches(layers,ref,node,'description',v,target_) OR tv->>'role' IS DISTINCT FROM 'declaration' THEN RAISE EXCEPTION 'declaration changes retained description' USING ERRCODE='23514'; END IF;
   symbol_:=ops.primary_navigation_role_text(layers,ref,node,'symbol',v);
   IF sv->>'role'='symbol' THEN
    IF NOT ops.primary_navigation_role_matches(layers,ref,node,'symbol',v,subject_) THEN RAISE EXCEPTION 'declaration changes retained symbol site' USING ERRCODE='23514'; END IF;
   ELSIF sv->>'role'='formula_symbol' THEN
    IF NOT ops.primary_formal_symbol_matches(layers,v,subject_,symbol_) THEN RAISE EXCEPTION 'declaration changes retained formal symbol' USING ERRCODE='23514'; END IF;
    SELECT p INTO STRICT source_piece FROM jsonb_array_elements(v.projection->'pieces') p WHERE p->>'item_ref'=sv->>'source_pointer' AND p->>'kind'='native_text' AND NOT p ? 'cell_index';
    SELECT p INTO STRICT target_piece FROM jsonb_array_elements(v.projection->'pieces') p WHERE p->>'item_ref'=nav->>'pointer' AND p->>'kind'='native_text' AND NOT p ? 'cell_index';
    SELECT native_json INTO STRICT source_item FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[source_piece->>'item_ref']);
    SELECT native_json INTO STRICT target_item FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[target_piece->>'item_ref']);
    IF (nav->>'introducer'='where' AND substring(v.projection->>'text' FROM (target_piece->>'start')::integer+1
      FOR (SELECT min((e->>'start')::integer)-(target_piece->>'start')::integer FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,ref,node,'match',v)) e))!~ '^\s*$')
     OR source_item->>'label' IS DISTINCT FROM 'formula' OR source_item->'parent' IS NULL OR source_item->'parent' IS DISTINCT FROM target_item->'parent'
     OR NOT ((nav->>'introducer'='where' AND (source_piece->>'end')::bigint<=(target_piece->>'start')::bigint) OR (nav->>'introducer'='let' AND (target_piece->>'end')::bigint<=(source_piece->>'start')::bigint))
     OR EXISTS(SELECT FROM jsonb_array_elements(v.projection->'pieces') p WHERE p->>'kind'='native_text' AND (p->>'start')::bigint>=least((source_piece->>'end')::bigint,(target_piece->>'end')::bigint)
      AND (p->>'end')::bigint<=greatest((source_piece->>'start')::bigint,(target_piece->>'start')::bigint) AND (p->>'end')::bigint>(p->>'start')::bigint) THEN RAISE EXCEPTION 'declaration formal use changes native adjacent scope' USING ERRCODE='23514'; END IF;
   ELSE RAISE EXCEPTION 'declaration changes source symbol role' USING ERRCODE='23514'; END IF;
  ELSIF nav->>'kind'='recap' THEN
   IF tv->>'role' IS DISTINCT FROM 'declared_name' OR sv->>'role' IS DISTINCT FROM 'formula_symbol' THEN RAISE EXCEPTION 'recap changes exact source roles' USING ERRCODE='23514'; END IF;
   symbol_:=ops.primary_navigation_role_text(layers,ref,node,'symbol',v);
   IF NOT ops.primary_formal_symbol_matches(layers,v,subject_,symbol_)
    OR sv->>'source_pointer' IS DISTINCT FROM nav->>'pointer'
    OR (sv->>'start')::bigint IS NULL OR (sv->>'end')::bigint IS NULL
    OR (sv->>'start')::bigint<(SELECT min((e->>'start')::bigint) FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,ref,node,'equation',v)) e)
    OR (sv->>'end')::bigint>(SELECT max((e->>'end')::bigint) FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,ref,node,'equation',v)) e) THEN RAISE EXCEPTION 'recap changes retained equation symbol or equation extent' USING ERRCODE='23514'; END IF;
   SELECT jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a INTO STRICT target_ref,target_node
   FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'annotations') a
   WHERE a->'navigation'->>'kind'='declaration_template' AND ops.primary_navigation_role_matches(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a,'name',v,target_);
   IF ops.primary_navigation_role_text(layers,target_ref,target_node,'symbol',v) IS DISTINCT FROM symbol_
    OR ops.primary_navigation_role_text(layers,target_ref,target_node,'name',v) IS DISTINCT FROM ops.primary_navigation_role_text(layers,ref,node,'name',v) THEN RAISE EXCEPTION 'recap changes retained prior declaration identity' USING ERRCODE='23514'; END IF;
   SELECT r INTO STRICT cue_ FROM jsonb_array_elements(population) r CROSS JOIN LATERAL (SELECT data.record_source_json(r->'value') m) q
    WHERE row_->'computation_dependencies' ? (r->>'contribution_id') AND m->>'role'='declaration_recap';
   IF NOT ops.primary_navigation_role_matches(layers,ref,node,'cue',v,cue_) THEN RAISE EXCEPTION 'recap loses exact retained source cue' USING ERRCODE='23514'; END IF;
   SELECT r INTO STRICT earlier_ FROM jsonb_array_elements(population) r WHERE r->'component'->>'attachment_kind'='declares'
    AND r->>'operation_key'<>row_->>'operation_key' AND row_->'computation_dependencies' ? (r->>'contribution_id');
   SELECT r INTO STRICT declaration_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=earlier_->'members'->>1;
   IF NOT ops.primary_navigation_role_matches(layers,target_ref,target_node,'description',v,declaration_) THEN RAISE EXCEPTION 'recap loses exact original declared meaning' USING ERRCODE='23514'; END IF;
   -- Source ordering and same native parent are structural, independent of prose.
   SELECT native_json INTO STRICT source_item FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[nav->>'pointer']);
   SELECT native_json INTO STRICT target_item FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[target_node->'navigation'->>'pointer']);
   IF config_->>'ordered_formula_witness' IS NOT NULL AND target_item->>'label'='inline' THEN
    SELECT native_json INTO STRICT declaration_ FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[target_item->'parent'->>'$ref']);
    IF declaration_->>'label' IS DISTINCT FROM 'text' OR declaration_->'children' IS DISTINCT FROM jsonb_build_array(jsonb_build_object('$ref',target_node->'navigation'->>'pointer'))
     OR declaration_->'parent' IS DISTINCT FROM source_item->'parent' THEN RAISE EXCEPTION 'ordered recap changes retained native inline declaration owner' USING ERRCODE='23514'; END IF;
   ELSIF source_item->'parent' IS DISTINCT FROM target_item->'parent' THEN RAISE EXCEPTION 'recap changes retained native declaration owner' USING ERRCODE='23514'; END IF;
   IF source_item->'parent' IS NULL OR source_item->>'content_layer' IS DISTINCT FROM 'body' OR target_item->>'content_layer' IS DISTINCT FROM 'body'
    OR (SELECT max((e->>'end')::bigint) FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,target_ref,target_node,'name',v)) e)>
       (SELECT min((e->>'start')::bigint) FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,ref,node,'cue',v)) e) THEN RAISE EXCEPTION 'recap changes source ordering or native owner' USING ERRCODE='23514'; END IF;
   SELECT count(*) INTO prior_count FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'annotations') a
    CROSS JOIN LATERAL (SELECT jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id') r) q
   WHERE a->'navigation'->>'kind'='declaration_cue'
    AND ops.primary_navigation_role_text(layers,r,a,'symbol',v)=symbol_
    AND EXISTS(SELECT FROM jsonb_array_elements(config_->'inputs'->'passages') p
     CROSS JOIN LATERAL jsonb_array_elements(config_->'inputs'->'sources') source_
     WHERE (source_->>'source_view_id')::bigint=v.id AND p->>'source_ref'=encode(sha256(convert_to(data.canonical_json(source_),'UTF8')),'hex')
      AND p->>'passage_id'=tv->>'region'
      AND (SELECT min((e->>'start')::bigint) FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,r,a,'symbol',v)) e)>=(p->>'start')::bigint
      AND (SELECT max((e->>'end')::bigint) FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,r,a,'symbol',v)) e)<=
       (SELECT min((e->>'start')::bigint) FROM jsonb_array_elements(ops.primary_navigation_role_extents(layers,ref,node,'cue',v)) e));
   IF prior_count<>1 THEN RAISE EXCEPTION 'recap hides competing retained declaration sites' USING ERRCODE='23514'; END IF;
  ELSE RAISE EXCEPTION 'source relation has no matching retained navigation codec' USING ERRCODE='23514';
  END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'source navigation does not resolve exact retained primary custody' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_primary_source_navigation(ops.task,kb.source_view,jsonb,jsonb,jsonb) FROM PUBLIC;

-- Current predicate consumer: only retained identities, coordinate conservation and
-- normalized value codecs. Linguistic recognition belongs to text.constructions.
CREATE OR REPLACE FUNCTION ops.validate_source_predicates_primary(
 p_task ops.task,p_view kb.source_view,p_population jsonb,p_config jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE layers jsonb:=ops.primary_characterization_layers(p_task,p_view,p_config);
 operations jsonb:=p_config->'_predicate_operations'; original jsonb; original_id text; selected_run bigint:=p_task.run_id; selected_cut bigint;
 evidence jsonb; c jsonb; ref jsonb; node jsonb; body jsonb; construction jsonb; block_ref jsonb; block_ jsonb; extents_ jsonb;
 operation_ jsonb; origin_body jsonb;
 kind_ text; lo bigint; hi bigint; selection_ jsonb; edge jsonb; member_ jsonb; member_ref jsonb; part jsonb; child jsonb;
 rows_ jsonb; expected_ jsonb; tokens jsonb; indices_ jsonb; head_ jsonb; inherited_ jsonb; full_indices jsonb; count_ integer;
 host jsonb; cue jsonb; host_node jsonb; cue_node jsonb; reading_ jsonb; condition_ jsonb; qualified_ jsonb; normalized jsonb; parts_ jsonb;
 numeric_ jsonb; ranges_ jsonb; span_ jsonb; marker_ jsonb; comparison_ jsonb; cursor_ bigint; end_ bigint; text_ text; op_ text;
 condition_schema json; qualification_schema json; support_ jsonb; policies jsonb;
BEGIN
 IF p_config->'inputs' IS NOT NULL AND p_config->'inputs'<>'null'::jsonb THEN
  SELECT s INTO STRICT original FROM jsonb_array_elements(p_config->'inputs'->'sources') s WHERE (s->>'source_view_id')::bigint=p_view.id;
  PERFORM ops.validate_structural_source(original);
  original_id:=encode(sha256(convert_to(data.canonical_json(original),'UTF8')),'hex');
  selected_run:=(original->>'run_id')::bigint;selected_cut:=(original->>'cut_id')::bigint;
 END IF;
 FOR operation_ IN SELECT value FROM jsonb_each(operations) WHERE value->>'question' IN ('source_predicate_frames','source_predicate_interpretation') LOOP
  IF operation_->>'operation_version' IS DISTINCT FROM '6' OR NOT coalesce(p_config->'characterization_layers','[]') @> coalesce(operation_->'primary_layers','[]') THEN
   RAISE EXCEPTION 'predicate operation differs from exact configured primary inputs' USING ERRCODE='23514'; END IF;
  IF operation_ ? 'annotation_origin_task_id' THEN
   SELECT r.body INTO STRICT origin_body
   FROM ops.task t JOIN ops.task_result r ON r.task_id=coalesce(t.reused_task_id,t.id)
    JOIN ops.method_config cfg ON cfg.id=t.method_config_id JOIN ops.method method ON method.id=cfg.method_id
   WHERE r.task_id=(operation_->>'annotation_origin_task_id')::bigint AND t.run_id=selected_run
    AND t.unit_type='source_view' AND t.unit_id=p_view.id AND t.status IN ('done','reused','empty')
    AND method.name='extract.m1_annotations' AND method.version='3'
    AND r.body->>'source'=p_view.key AND (selected_cut IS NULL OR EXISTS(
     SELECT FROM ops.cut_task cut WHERE cut.cut_id=selected_cut AND cut.task_id=t.id AND cut.origin_task_id=r.task_id));
   IF NOT coalesce(data.record_source_json(origin_body->'parse_detail')->'characterization_layers','[]') @> coalesce(operation_->'primary_layers','[]') THEN
    RAISE EXCEPTION 'predicate summary origin differs from exact retained primary pins' USING ERRCODE='23514'; END IF;
  END IF;
 END LOOP;
 SELECT convert_from(content,'UTF8')::json INTO STRICT condition_schema FROM sem.artifact
  WHERE release_id=p_task.release_id AND artifact_name='json_schema/Condition';
 SELECT convert_from(content,'UTF8')::json INTO STRICT qualification_schema FROM sem.artifact
  WHERE release_id=p_task.release_id AND artifact_name='json_schema/Qualification';
 FOR evidence IN SELECT value FROM jsonb_each(p_population) WHERE value->'component'->>'kind' IN ('predicate_frame','predicate_reading','predicate_cue','predicate_qualifier') LOOP
  c:=evidence->'component';kind_:=c->>'kind';ref:=c->'primary_node';node:=ops.primary_characterization_node(layers,ref);
  operation_:=operations->(evidence->>'operation_key');body:=layers->data.canonical_json(ref->'layer');
  IF operation_ IS NULL OR c->>'question_version' IS DISTINCT FROM '6'
   OR c->>'question' IS DISTINCT FROM (CASE WHEN kind_ IN ('predicate_frame','predicate_cue') THEN 'source_predicate_frames' ELSE 'source_predicate_interpretation' END)
   OR operation_->>'question' IS DISTINCT FROM c->>'question'
   OR NOT coalesce(operation_->'primary_layers','[]') @> jsonb_build_array(ref->'layer')
   OR NOT ops.primary_characterization_choices(layers,ref,node,c->'primary_choices') THEN
   RAISE EXCEPTION 'predicate component loses primary origin or analytical choices' USING ERRCODE='23514'; END IF;
  IF c->>'interpretation'='supported' THEN
   IF node->'basis'->>'kind' IS DISTINCT FROM 'released_construction' OR node->'basis'->>'status' IS DISTINCT FROM 'witnessed' THEN
    RAISE EXCEPTION 'supported predicate requires a released mechanical witness' USING ERRCODE='23514'; END IF;
   SELECT convert_from(content,'UTF8')::jsonb INTO STRICT policies FROM sem.artifact WHERE release_id=p_task.release_id AND artifact_name='characterization/attachment-policies.json';
   support_:=policies->'released_construction'->'rules'->(node->'basis'->>'rule_id')->'support';
   IF support_ IS NULL THEN RAISE EXCEPTION 'predicate has no released support codec' USING ERRCODE='23514'; END IF;
   PERFORM ops.validate_characterization_support(body,node,support_);
  END IF;
  IF kind_ IN ('predicate_frame','predicate_cue') THEN
   IF node->>'family' IS DISTINCT FROM 'construction.source_readings' OR node->>'vocabulary' IS DISTINCT FROM 'source-linguistic-rules-1'
    OR node->>'kind' IS DISTINCT FROM (CASE kind_ WHEN 'predicate_frame' THEN 'predicate' ELSE 'operator' END) THEN
    RAISE EXCEPTION 'predicate component is not a retained source reading' USING ERRCODE='23514'; END IF;
   SELECT a INTO STRICT construction FROM jsonb_array_elements(body->'annotations') a
    WHERE node->'premises' ? (a->>'local_id') AND a->>'kind'='construction' AND a->>'family'='construction.source_readings';
   IF construction->>'native_label' IS DISTINCT FROM c->>'variant' THEN RAISE EXCEPTION 'predicate variant differs from retained construction' USING ERRCODE='23514'; END IF;
   SELECT value INTO STRICT block_ref FROM jsonb_array_elements(construction->'external_premises');
   block_:=ops.primary_characterization_node(layers,block_ref);
   IF block_->>'kind' IS DISTINCT FROM 'native.block' OR block_ref->>'local_id' IS DISTINCT FROM 'spacy/'||p_view.id||'/'||(c->>'block')||'/block'
    OR NOT coalesce(c->'dependencies','[]') ? (c->>'annotation') THEN
    RAISE EXCEPTION 'predicate block differs from its exact primary native container' USING ERRCODE='23514'; END IF;
   extents_:=ops.primary_characterization_extents(layers,block_ref,block_,p_view);
   SELECT min((e->>'start')::bigint),max((e->>'end')::bigint) INTO lo,hi FROM jsonb_array_elements(extents_) e;
   IF selected_cut IS NOT NULL THEN
    SELECT p INTO STRICT selection_ FROM jsonb_array_elements(p_config->'inputs'->'passages') p WHERE p->>'source_ref'=original_id
     AND p->>'passage_id'=c->>'scope' AND p->>'effective_version' IS NOT DISTINCT FROM c->>'effective_version';
    lo:=greatest(lo,(selection_->>'start')::bigint);hi:=least(hi,(selection_->>'end')::bigint);
   ELSIF c->>'scope' IS DISTINCT FROM c->>'block' OR c ? 'effective_version' THEN
    RAISE EXCEPTION 'predicate scope differs from retained block' USING ERRCODE='23514'; END IF;
  END IF;
  IF kind_='predicate_frame' THEN
   SELECT coalesce(jsonb_agg(m->'contribution' ORDER BY n),'[]') INTO rows_ FROM jsonb_array_elements(c->'frame_members') WITH ORDINALITY x(m,n);
   IF evidence->>'kind' IS DISTINCT FROM 'composite' OR evidence ? 'endpoints' OR evidence->'members' IS DISTINCT FROM rows_
    OR jsonb_array_length(rows_)<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(rows_)) OR NOT c->'dependencies' @> rows_
    OR c->>'grammatical_reading' IS DISTINCT FROM node->>'value' THEN
    RAISE EXCEPTION 'predicate frame differs from retained members or grammatical reading' USING ERRCODE='23514'; END IF;
   FOR member_ IN SELECT value FROM jsonb_array_elements(c->'frame_members') LOOP
    member_ref:=member_->'primary_node';child:=ops.primary_characterization_node(layers,member_ref);part:=p_population->(member_->>'contribution');
    IF member_ref->'layer' IS DISTINCT FROM ref->'layer' OR NOT EXISTS(SELECT FROM jsonb_array_elements(node->'children') e
      WHERE e->>'role'=member_->>'role' AND e->>'target'=member_ref->>'local_id')
     OR NOT ops.primary_characterization_choices(layers,member_ref,child,member_->'primary_choices')
     OR part->'pin' IS DISTINCT FROM evidence->'pin' OR part->>'operation_key' IS DISTINCT FROM evidence->>'operation_key'
     OR part->>'kind' IS DISTINCT FROM 'occurrence' OR part->>'semantic_type' IS DISTINCT FROM 'structural.predicate_member'
     OR NOT coalesce(part->'computation_dependencies','[]') ? (c->>'annotation')
     OR NOT ops.predicate_primary_member_matches(layers,member_ref,child,p_view,lo,hi,member_->'extents',part->'anchors',member_->'token_indices') THEN
     RAISE EXCEPTION 'predicate role differs from its retained child, choices or source tokens' USING ERRCODE='23514'; END IF;
    head_:=CASE WHEN member_->>'role'='focus' THEN ops.primary_characterization_child(layers,ref,node,'predicate') ELSE child END;
    IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(child->'children','[]')) e WHERE e->>'role'='head') THEN head_:=ops.primary_characterization_child(layers,member_ref,child,'head'); END IF;
    head_:=ops.primary_characterization_node(layers,head_->'external_premises'->0)->'native_token'->'index';
    inherited_:=NULL;
    IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(child->'children','[]')) e WHERE e->>'role'='inherited_from') THEN
     inherited_:=ops.primary_characterization_child(layers,member_ref,child,'inherited_from');
     inherited_:=ops.primary_characterization_node(layers,inherited_->'external_premises'->0)->'native_token'->'index'; END IF;
    IF member_->'head_token' IS DISTINCT FROM (CASE WHEN member_->'token_indices' @> jsonb_build_array(head_) THEN head_ END)
     OR member_->'inherited_from' IS DISTINCT FROM inherited_
     OR (member_->>'outcome'='complete' AND (child->>'status'<>'interpreted' OR
      (SELECT coalesce(range_agg(int8range((e->>'start')::bigint,(e->>'end')::bigint,'[)')),'{}') FROM jsonb_array_elements(member_->'extents') e)
       IS DISTINCT FROM (SELECT coalesce(range_agg(int8range((e->>'start')::bigint,(e->>'end')::bigint,'[)')),'{}') FROM jsonb_array_elements(ops.primary_characterization_extents(layers,member_ref,child,p_view)) e))) THEN
     RAISE EXCEPTION 'predicate role changes retained head, inheritance or completeness' USING ERRCODE='23514'; END IF;
    IF member_->>'role'='predicate' AND member_->'head_token' IS DISTINCT FROM c->'predicate_token' THEN
     RAISE EXCEPTION 'predicate head differs from retained predicate token' USING ERRCODE='23514'; END IF;
   END LOOP;
   FOR edge IN SELECT value FROM jsonb_array_elements(node->'children') WHERE value->>'role' IN ('predicate','focus','actor','subject','object','complement') LOOP
    child:=ops.primary_characterization_node(layers,jsonb_build_object('layer',ref->'layer','local_id',edge->>'target'));
    count_:=(SELECT count(*) FROM jsonb_array_elements(c->'frame_members') m WHERE m->>'role'=edge->>'role' AND m->'primary_node'->>'local_id'=edge->>'target');
    IF count_>1 THEN RAISE EXCEPTION 'predicate repeats a retained role child' USING ERRCODE='23514'; END IF;
    IF count_=0 THEN
     SELECT coalesce(jsonb_agg(ops.primary_characterization_node(layers,x)->'native_token'->'index' ORDER BY n),'[]') INTO full_indices
      FROM jsonb_array_elements(coalesce(child->'external_premises','[]')) WITH ORDINALITY a(x,n);
     member_ref:=jsonb_build_object('layer',ref->'layer','local_id',child->>'local_id');tokens:=ops.predicate_primary_tokens(layers,member_ref,child,p_view);
     IF EXISTS(SELECT FROM jsonb_array_elements(full_indices) i WHERE (tokens->(i::text::integer)->>'start')::bigint>=lo AND (tokens->(i::text::integer)->>'end')::bigint<=hi
       AND EXISTS(SELECT FROM jsonb_array_elements(p_view.projection->'pieces') p WHERE p->>'kind'='native_text' AND coalesce(p->>'source_field','text') IN ('text','orig','cell_text')
        AND (p->>'start')::bigint<=(tokens->(i::text::integer)->>'start')::bigint AND (p->>'end')::bigint>=(tokens->(i::text::integer)->>'end')::bigint))
      OR (edge->>'role'<>'focus' AND (SELECT count(*) FROM jsonb_array_elements(coalesce(c->'unlocated_roles','[]')) m
       WHERE m->>'role'=edge->>'role' AND m->'token_indices'=full_indices)<>1) THEN
      RAISE EXCEPTION 'predicate omits an eligible retained role child' USING ERRCODE='23514'; END IF;
    END IF;
   END LOOP;
   FOR member_ IN SELECT value FROM jsonb_array_elements(coalesce(c->'unlocated_roles','[]')) LOOP
    SELECT candidate INTO STRICT child FROM jsonb_array_elements(node->'children') e
     CROSS JOIN LATERAL (SELECT ops.primary_characterization_node(layers,jsonb_build_object('layer',ref->'layer','local_id',e->>'target')) candidate) q
    WHERE e->>'role'=member_->>'role' AND (SELECT jsonb_agg(ops.primary_characterization_node(layers,x)->'native_token'->'index' ORDER BY n)
     FROM jsonb_array_elements(candidate->'external_premises') WITH ORDINALITY a(x,n))=member_->'token_indices'
     AND NOT EXISTS(SELECT FROM jsonb_array_elements(c->'frame_members') m WHERE m->'primary_node'->>'local_id'=e->>'target');
    member_ref:=jsonb_build_object('layer',ref->'layer','local_id',child->>'local_id');head_:=child;inherited_:=NULL;
    IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(child->'children','[]')) e WHERE e->>'role'='head') THEN head_:=ops.primary_characterization_child(layers,member_ref,child,'head'); END IF;
    head_:=ops.primary_characterization_node(layers,head_->'external_premises'->0)->'native_token'->'index';
    IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(child->'children','[]')) e WHERE e->>'role'='inherited_from') THEN
     inherited_:=ops.primary_characterization_child(layers,member_ref,child,'inherited_from');inherited_:=ops.primary_characterization_node(layers,inherited_->'external_premises'->0)->'native_token'->'index'; END IF;
    IF member_->'head_token' IS DISTINCT FROM head_ OR member_->'inherited_from' IS DISTINCT FROM inherited_
     OR (SELECT count(*) FROM jsonb_array_elements(c->'unlocated_roles') m WHERE m->>'role'=member_->>'role' AND m->'token_indices'=member_->'token_indices')<>1 THEN
     RAISE EXCEPTION 'unlocated predicate role changes retained head, inheritance or membership' USING ERRCODE='23514'; END IF;
   END LOOP;
   SELECT m INTO STRICT member_ FROM jsonb_array_elements(c->'frame_members') m WHERE m->>'role'='predicate';
   SELECT m INTO member_ FROM jsonb_array_elements(c->'frame_members') m WHERE m->>'role'='focus';
   IF c->>'focus_state' IS DISTINCT FROM (CASE WHEN member_ IS NULL THEN 'unavailable' WHEN member_->>'outcome'='complete' AND jsonb_array_length(member_->'extents')=1 THEN 'exact' ELSE 'partial' END) THEN
    RAISE EXCEPTION 'predicate focus state differs from retained positioned focus' USING ERRCODE='23514'; END IF;
  ELSIF kind_='predicate_cue' THEN
   child:=ops.primary_characterization_child(layers,ref,node,'cue');member_ref:=jsonb_build_object('layer',ref->'layer','local_id',child->>'local_id');
   IF c->>'cue_kind' IS DISTINCT FROM (CASE node->>'value' WHEN 'temporal' THEN 'order' WHEN 'polarity' THEN 'negation' ELSE node->>'value' END)
    OR NOT ops.predicate_primary_member_matches(layers,member_ref,child,p_view,lo,hi,c->'extents',evidence->'anchors',c->'token_indices') THEN
    RAISE EXCEPTION 'predicate cue changes retained kind or source extent' USING ERRCODE='23514'; END IF;
   marker_:=ops.primary_characterization_child(layers,ref,node,'basis');member_ref:=jsonb_build_object('layer',ref->'layer','local_id',marker_->>'local_id');
   IF c->'primary_marker' IS DISTINCT FROM member_ref THEN RAISE EXCEPTION 'predicate marker is not the retained cue basis' USING ERRCODE='23514'; END IF;
   part:=p_population->(c->>'marker_member');
   IF c ? 'marker_member' AND (part->'pin' IS DISTINCT FROM evidence->'pin' OR part->>'operation_key' IS DISTINCT FROM evidence->>'operation_key'
    OR part->>'semantic_type' IS DISTINCT FROM 'structural.predicate_member' OR part->>'kind' IS DISTINCT FROM 'occurrence'
    OR NOT ops.predicate_primary_member_matches(layers,member_ref,marker_,p_view,lo,hi,c->'marker_extents',part->'anchors',c->'marker_token_indices')
    OR evidence->'members' IS DISTINCT FROM jsonb_build_array(c->'marker_member') OR NOT c->'dependencies' ? (c->>'marker_member')) THEN
    RAISE EXCEPTION 'predicate marker changes exact retained evidence' USING ERRCODE='23514'; END IF;
   IF NOT c ? 'marker_member' AND (evidence ? 'members' OR c->>'host_state'='located') THEN RAISE EXCEPTION 'located predicate cue lacks its marker' USING ERRCODE='23514'; END IF;
   FOR edge IN SELECT * FROM jsonb_array_elements(jsonb_build_array(jsonb_build_object('source','origin','field','governing_token'),jsonb_build_object('source','component','field','subordinate_token'))) LOOP
    expected_:=NULL;
    IF EXISTS(SELECT FROM jsonb_array_elements(node->'children') x WHERE x->>'role'=edge->>'source') THEN
     child:=ops.primary_characterization_child(layers,ref,node,edge->>'source');expected_:=ops.primary_characterization_node(layers,child->'external_premises'->0)->'native_token'->'index'; END IF;
    IF c->(edge->>'field') IS DISTINCT FROM expected_ THEN RAISE EXCEPTION 'predicate cue changes retained governing/component endpoint' USING ERRCODE='23514'; END IF;
   END LOOP;
   SELECT coalesce(jsonb_agg(i ORDER BY i),'[]') INTO expected_ FROM (
    SELECT DISTINCT ops.primary_characterization_node(layers,p->'external_premises'->0)->'native_token'->'index' i
    FROM jsonb_array_elements(body->'roles') r
    CROSS JOIN LATERAL (SELECT ops.primary_characterization_node(layers,jsonb_build_object('layer',ref->'layer','local_id',r->>'member')) h) h_
    CROSS JOIN LATERAL (SELECT ops.primary_characterization_child(layers,ref,h,'predicate') p) p_
    WHERE r->>'owner'=node->>'local_id' AND r->>'role'='host'
   ) hosts;
   IF NOT coalesce(c->'candidate_tokens','[]') @> expected_ OR NOT expected_ @> coalesce(c->'candidate_tokens','[]')
    OR jsonb_array_length(c->'candidate_tokens')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(c->'candidate_tokens')) THEN
    RAISE EXCEPTION 'predicate cue changes the complete retained candidate host population' USING ERRCODE='23514'; END IF;
   FOR indices_ IN SELECT value FROM jsonb_array_elements(coalesce(c->'cross_block_hosts','[]')) LOOP
    host:=p_population->(indices_#>>'{}');
    IF host->'component'->>'kind' IS DISTINCT FROM 'predicate_frame' OR host->'pin' IS DISTINCT FROM evidence->'pin'
     OR host->'component'->>'scope' IS DISTINCT FROM c->>'scope' OR host->'component'->>'effective_version' IS DISTINCT FROM c->>'effective_version'
     OR NOT c->'dependencies' ? (indices_#>>'{}') OR NOT EXISTS(SELECT FROM jsonb_array_elements(body->'roles') r
      WHERE r->>'owner'=node->>'local_id' AND r->>'role'='cross_block_host'
       AND host->'component'->'primary_node'=jsonb_build_object('layer',ref->'layer','local_id',r->>'member')) THEN
     RAISE EXCEPTION 'predicate cue changes retained cross-block host population' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF c->>'host_state'='located' AND (node->>'status'<>'interpreted' OR (jsonb_array_length(c->'candidate_tokens')=0 AND coalesce(jsonb_array_length(c->'cross_block_hosts'),0)=0)) THEN
    RAISE EXCEPTION 'predicate cue promotes an unresolved host' USING ERRCODE='23514'; END IF;
  ELSE
   host:=p_population->(CASE kind_ WHEN 'predicate_reading' THEN c->>'frame' ELSE c->>'host_contribution_id' END);
   IF host->'component'->>'kind' IS DISTINCT FROM 'predicate_frame' OR host->'pin' IS DISTINCT FROM evidence->'pin'
    OR host->'component'->>'scope' IS DISTINCT FROM c->>'scope' OR host->'component'->>'effective_version' IS DISTINCT FROM c->>'effective_version'
    OR NOT c->'dependencies' ? (host->>'contribution_id') THEN RAISE EXCEPTION 'predicate interpretation changes exact frame or scope' USING ERRCODE='23514'; END IF;
   host_node:=ops.primary_characterization_node(layers,host->'component'->'primary_node');
   IF kind_='predicate_reading' THEN
    IF ref IS DISTINCT FROM host->'component'->'primary_node' OR evidence->>'kind' IS DISTINCT FROM 'composite' OR evidence ? 'endpoints'
     OR evidence->'members' IS DISTINCT FROM jsonb_build_array(host->'contribution_id')
     OR c->>'reading' IS DISTINCT FROM ops.primary_characterization_child(layers,ref,node,'interpretation')->>'value'
     OR c->>'voice' IS DISTINCT FROM ops.primary_characterization_child(layers,ref,node,'voice')->>'value'
     OR c->>'polarity' IS DISTINCT FROM (CASE ops.primary_characterization_child(layers,ref,node,'polarity')->>'value' WHEN 'positive' THEN 'positive' WHEN 'negative' THEN 'negative' ELSE 'unresolved' END) THEN
     RAISE EXCEPTION 'predicate reading changes retained normalized fields' USING ERRCODE='23514'; END IF;
   ELSE
    cue:=p_population->(c->>'qualifier_contribution_id');cue_node:=ops.primary_characterization_node(layers,cue->'component'->'primary_node');
    IF cue->'component'->>'kind' IS DISTINCT FROM 'predicate_cue' OR cue->'component'->>'host_state' IS DISTINCT FROM 'located'
     OR cue->'pin' IS DISTINCT FROM evidence->'pin' OR cue->'component'->>'scope' IS DISTINCT FROM c->>'scope'
     OR cue->'component'->>'effective_version' IS DISTINCT FROM c->>'effective_version'
     OR ref->'layer' IS DISTINCT FROM cue->'component'->'primary_node'->'layer' OR ref->'layer' IS DISTINCT FROM host->'component'->'primary_node'->'layer'
     OR node->>'owner' IS DISTINCT FROM cue_node->>'local_id' OR node->>'member' IS DISTINCT FROM host_node->>'local_id'
     OR node->>'role' NOT IN ('host','cross_block_host') OR node->>'scheme' IS DISTINCT FROM 'source-linguistic-rules-1'
     OR c->>'qualifier_kind' IS DISTINCT FROM cue->'component'->>'cue_kind' OR NOT c->'dependencies' ? (cue->>'contribution_id')
     OR NOT ops.primary_characterization_choices(layers,cue->'component'->'primary_node',cue_node,c->'primary_choices')
     OR NOT ops.primary_characterization_choices(layers,host->'component'->'primary_node',host_node,c->'primary_choices')
     OR evidence->>'kind' IS DISTINCT FROM 'relation' OR evidence->'endpoints' IS DISTINCT FROM jsonb_build_array(jsonb_build_object('role','qualifier','contribution_id',cue->>'contribution_id'),jsonb_build_object('role','host','contribution_id',host->>'contribution_id')) THEN
     RAISE EXCEPTION 'predicate qualifier changes retained directed host relation' USING ERRCODE='23514'; END IF;
    IF node->>'role'='cross_block_host' THEN
     IF NOT cue->'component'->'cross_block_hosts' ? (host->>'contribution_id') OR NOT c ? 'host_witness' THEN RAISE EXCEPTION 'cross-block host loses retained witness' USING ERRCODE='23514'; END IF;
     IF c->'host_witness'->>'kind'='list_intro' THEN
      IF c->'host_witness'->>'list_group' IS DISTINCT FROM ops.primary_characterization_child(layers,cue->'component'->'primary_node',cue_node,'native_list_group')->>'value' THEN RAISE EXCEPTION 'cross-block list group differs from retained primary metadata' USING ERRCODE='23514'; END IF;
     ELSIF c->'host_witness'->>'kind'='parameter_note' THEN
      part:=p_population->(c->'host_witness'->>'parameterization');child:=ops.primary_characterization_child(layers,cue->'component'->'primary_node',cue_node,'prior_qualifier');
      IF part->'component'->'qualifier_contribution_id' IS NULL OR p_population->(part->'component'->>'qualifier_contribution_id')->'component'->'primary_node'
       IS DISTINCT FROM jsonb_build_object('layer',ref->'layer','local_id',child->>'local_id') OR NOT c->'dependencies' ? (c->'host_witness'->>'parameterization') THEN
       RAISE EXCEPTION 'parameter note changes retained predecessor' USING ERRCODE='23514'; END IF;
     ELSE RAISE EXCEPTION 'unknown cross-block witness codec' USING ERRCODE='23514'; END IF;
    ELSIF c ? 'host_witness' THEN RAISE EXCEPTION 'local primary host is not a cross-block witness' USING ERRCODE='23514'; END IF;
    condition_:=data.record_source_json(c->'condition');qualified_:=data.record_source_json(c->'qualification');reading_:=p_population->(c->>'interpretation_member');
    IF c ? 'condition' THEN
     IF c->>'qualifier_kind' NOT IN ('condition','assumption') OR NOT coalesce(public.json_matches_schema(condition_schema,condition_::json),false) THEN RAISE EXCEPTION 'predicate condition differs from its released codec' USING ERRCODE='23514'; END IF;
     text_:=(SELECT string_agg(substring(p_view.projection->>'text' FROM (e->>'start')::integer+1 FOR (e->>'end')::integer-(e->>'start')::integer),' ' ORDER BY n) FROM jsonb_array_elements(cue->'component'->'extents') WITH ORDINALITY x(e,n));
     IF condition_->>'kind'='escape' THEN
      IF condition_->>'text' IS DISTINCT FROM text_ OR c ? 'primary_condition_parts' THEN RAISE EXCEPTION 'escaped predicate condition changes located source' USING ERRCODE='23514'; END IF;
     ELSE
      op_:=ops.primary_characterization_child(layers,cue->'component'->'primary_node',cue_node,'formal_condition_operator')->>'value';
      IF op_ NOT IN ('compare','not_compare') OR jsonb_array_length(c->'primary_condition_parts') IS DISTINCT FROM 3 OR jsonb_array_length(cue->'component'->'extents')<>1 THEN RAISE EXCEPTION 'numeric condition lacks retained operator or positioned parts' USING ERRCODE='23514'; END IF;
      numeric_:='[]';ranges_:='[]';cursor_:=-1;
      FOR member_ref,count_ IN SELECT value,n::integer FROM jsonb_array_elements(c->'primary_condition_parts') WITH ORDINALITY x(value,n) LOOP
       child:=ops.primary_characterization_node(layers,member_ref);normalized:=child->'formal'->'normalized';span_:=ops.primary_characterization_extents(layers,member_ref,child,p_view);
       IF normalized->>'kind' IS DISTINCT FROM (CASE count_ WHEN 2 THEN 'comparator' ELSE 'decimal' END)
        OR normalized->>'domain_status' NOT IN ('valid','not_requested') OR jsonb_array_length(span_)<>1
        OR (span_->0->>'start')::bigint<cursor_
        OR NOT ops.primary_characterization_choices(layers,member_ref,child,c->'primary_choices') THEN RAISE EXCEPTION 'numeric condition part changes normalized formal evidence' USING ERRCODE='23514'; END IF;
       cursor_:=(span_->0->>'end')::bigint;
       IF EXISTS(SELECT FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'annotations') a
        WHERE a->'formal'->'normalized'->>'kind'=normalized->>'kind' AND a->'formal'->'normalized'->>'domain_status' IN ('valid','not_requested')
         AND a->'formal'->'normalized'->'value' IS DISTINCT FROM normalized->'value'
         AND CASE WHEN ops.primary_characterization_in_view(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a,p_view.id) THEN ops.primary_characterization_extents(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a,p_view)=span_ ELSE false END) THEN
        RAISE EXCEPTION 'numeric condition hides conflicting retained normalization' USING ERRCODE='23514'; END IF;
       numeric_:=numeric_||jsonb_build_array(normalized->'value');ranges_:=ranges_||span_;
      END LOOP;
      marker_:=ops.primary_characterization_child(layers,cue->'component'->'primary_node',cue_node,'basis');
      ranges_:=ranges_||ops.primary_characterization_extents(layers,cue->'component'->'primary_node',marker_,p_view);
      cursor_:=(cue->'component'->'extents'->0->>'start')::bigint;end_:=(cue->'component'->'extents'->0->>'end')::bigint;
      FOR span_ IN SELECT value FROM jsonb_array_elements(ranges_) ORDER BY (value->>'start')::bigint LOOP
       IF coalesce((span_->>'synthetic')::boolean,true) OR (span_->>'start')::bigint<cursor_ OR (span_->>'end')::bigint>end_
        OR substring(p_view.projection->>'text' FROM cursor_::integer+1 FOR ((span_->>'start')::bigint-cursor_)::integer)!~ '^\s*$' THEN RAISE EXCEPTION 'numeric condition parts do not exactly cover retained cue' USING ERRCODE='23514'; END IF;
       cursor_:=(span_->>'end')::bigint;
      END LOOP;
      IF substring(p_view.projection->>'text' FROM cursor_::integer+1 FOR (end_-cursor_)::integer)!~ '^\s*$' THEN RAISE EXCEPTION 'numeric condition leaves uninterpreted source content' USING ERRCODE='23514'; END IF;
      comparison_:=jsonb_build_object('kind','compare','relation',numeric_->1,'lhs',jsonb_build_object('kind','expression','language','text','expression',numeric_->0,'form','formula'),'rhs',jsonb_build_object('kind','expression','language','text','expression',numeric_->2,'form','formula'));
      expected_:=CASE op_ WHEN 'not_compare' THEN jsonb_build_object('kind','not','term',comparison_) ELSE comparison_ END;
      IF condition_ IS DISTINCT FROM expected_ THEN RAISE EXCEPTION 'numeric condition changes retained normalized comparison' USING ERRCODE='23514'; END IF;
     END IF;
    ELSIF c ? 'primary_condition_parts' THEN RAISE EXCEPTION 'formal parts without predicate condition' USING ERRCODE='23514'; END IF;
    expected_:=jsonb_build_array(cue->'contribution_id',host->'contribution_id');
    IF c ? 'interpretation_member' THEN expected_:=expected_||jsonb_build_array(c->'interpretation_member'); END IF;
    IF evidence->'members' IS DISTINCT FROM expected_ OR (c ? 'qualification') IS DISTINCT FROM (c ? 'interpretation_member') OR NOT c->'dependencies' @> expected_ THEN RAISE EXCEPTION 'predicate qualifier loses exact relation members' USING ERRCODE='23514'; END IF;
    IF c ? 'qualification' AND (NOT coalesce(public.json_matches_schema(qualification_schema,qualified_::json),false)
     OR qualified_->'condition' IS DISTINCT FROM condition_ OR reading_->'component'->>'kind' IS DISTINCT FROM 'predicate_reading'
     OR reading_->'component'->'frame' IS DISTINCT FROM host->'contribution_id'
     OR qualified_->'scope' IS DISTINCT FROM jsonb_build_object('extent','statement','locator',host->'contribution_id')
     OR qualified_->>'modality' IS DISTINCT FROM (CASE reading_->'component'->>'reading' WHEN 'definition' THEN 'defined' WHEN 'assumption_restriction' THEN 'supposed' WHEN 'described_process' THEN 'asserted' END)
     OR qualified_->'polarity' IS DISTINCT FROM (CASE reading_->'component'->>'polarity' WHEN 'positive' THEN 'true'::jsonb WHEN 'negative' THEN 'false'::jsonb END)) THEN RAISE EXCEPTION 'predicate qualification changes retained interpretation' USING ERRCODE='23514'; END IF;
   END IF;
  END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'predicate evidence does not resolve exact primary custody' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_predicates_primary(ops.task,kb.source_view,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_source_predicates(
 p_task ops.task,p_view kb.source_view,p_population jsonb,p_config jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF p_config->>'_predicate_version' IS DISTINCT FROM '6' THEN
  RAISE EXCEPTION 'obsolete predicate recognizer versions are not active consumer semantics' USING ERRCODE='23514';
 END IF;
 PERFORM ops.validate_source_predicates_primary(p_task,p_view,p_population,p_config);
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_predicates(ops.task,kb.source_view,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_scope_inheritance(population jsonb,operation_map jsonb)
RETURNS void LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE op jsonb; expected jsonb; actual jsonb; inspected integer;
BEGIN
 SELECT o INTO STRICT op FROM jsonb_each(operation_map) x(key,o)
 WHERE o->>'question'='source_scope_inheritance';
 WITH rows AS MATERIALIZED (
  SELECT c->>'contribution_id' AS id,c->'component' AS component
  FROM jsonb_array_elements(population) c WHERE c ? 'component'
 ), qualifiers AS (
  SELECT q.id,q.component, cue.component AS cue, host.component AS host
  FROM rows q
  JOIN rows cue ON cue.id=q.component->>'qualifier_contribution_id'
  JOIN rows host ON host.id=q.component->>'host_contribution_id'
  WHERE q.component->>'kind'='predicate_qualifier'
   AND q.component->>'qualifier_kind' IN ('condition','assumption')
 ), selected AS (
  SELECT id,component FROM qualifiers
  WHERE component->'host_witness'->>'kind'='list_intro'
   OR (NOT component ? 'host_witness' AND cue ? 'governing_token'
    AND cue->'governing_token'<>host->'predicate_token')
 )
 SELECT (SELECT count(*) FROM qualifiers),coalesce(jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
  'qualifier',id,'cue',component->>'qualifier_contribution_id','host',component->>'host_contribution_id',
  'scope',component->>'scope','effective_version',component->>'effective_version')) ORDER BY id),'[]')
 INTO inspected,expected FROM selected;
 SELECT coalesce(jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
  'qualifier',q->>'contribution_id','cue',r->'endpoints'->0->>'contribution_id',
  'host',r->'endpoints'->1->>'contribution_id','scope',r->'component'->>'scope',
  'effective_version',r->'component'->>'effective_version')) ORDER BY q->>'contribution_id'),'[]')
 INTO actual FROM jsonb_array_elements(population) r
 LEFT JOIN LATERAL (
  SELECT candidate FROM jsonb_array_elements(population) candidate
  WHERE candidate->'component'->>'kind'='predicate_qualifier'
   AND r->'computation_dependencies' ? (candidate->>'contribution_id')
 ) qualifying(q) ON true
 WHERE r->>'operation_key'=op->>'operation_key'
  AND r->>'kind'='relation' AND r->'component'->>'attachment_kind'='scope_inheritance';
 IF actual IS DISTINCT FROM expected OR (op->>'inspected_count')::integer IS DISTINCT FROM inspected
  OR (op->>'emitted_count')::integer IS DISTINCT FROM jsonb_array_length(expected)
  OR op->>'operation_version' IS DISTINCT FROM '1'
  OR EXISTS(SELECT FROM jsonb_array_elements(population) r
   WHERE r->>'operation_key'=op->>'operation_key' AND (
    r->>'kind' IS DISTINCT FROM 'relation' OR r->'component'->>'attachment_kind' IS DISTINCT FROM 'scope_inheritance'
    OR jsonb_array_length(r->'endpoints') IS DISTINCT FROM 2
    OR r->'endpoints'->0->>'role' IS DISTINCT FROM 'attachment'
    OR r->'endpoints'->1->>'role' IS DISTINCT FROM 'target')) THEN
  RAISE EXCEPTION 'scope inheritance differs from admitted qualifier and host population' USING ERRCODE='23514';
 END IF;
END $$;
REVOKE ALL ON FUNCTION ops.validate_scope_inheritance(jsonb,jsonb) FROM PUBLIC;

-- The original definition component and physical layout establish its section.
-- Authenticate a retained named source carrier before using any of its semantic
-- fields in contextual nominations. The source operation still owns recognition.
CREATE OR REPLACE FUNCTION ops.contextual_primary_named_cue(p_run bigint,p_view kb.source_view,p_layers jsonb,carrier jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE outer_ jsonb; original_ jsonb; proof jsonb; ref jsonb; layers jsonb; node jsonb; nav jsonb; role_ text; field_ text;
BEGIN
 IF carrier->>'semantic_type' IS DISTINCT FROM 'contextual.located_mention' THEN RETURN NULL; END IF;
 outer_:=data.record_source_json(carrier->'value');
 IF outer_->>'producer_semantic_type' IS DISTINCT FROM 'structural.located_participant' THEN RETURN NULL; END IF;
 IF jsonb_typeof(outer_->'producer_value') IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'contextual named source lacks an encoded producer value' USING ERRCODE='23514'; END IF;
 original_:=data.record_source_json(outer_->'producer_value');proof:=original_->'named_cue';ref:=proof->'primary_node';
 IF ref IS NULL OR coalesce(original_->>'role','') NOT IN ('named_link_subject','named_link_cue','named_link_target','named_link_definition_subject') THEN RETURN NULL; END IF;
 layers:=ops.primary_characterization_layers(p_run,p_view,p_layers);
 IF NOT layers ? data.canonical_json(ref->'layer') THEN RETURN NULL; END IF;
 node:=ops.primary_navigation_node(layers,ref,'[]',p_view);nav:=node->'navigation';
 IF nav->>'kind' IS DISTINCT FROM 'named_link' THEN RAISE EXCEPTION 'contextual source carrier lacks a primary named-link annotation' USING ERRCODE='23514'; END IF;
 FOREACH field_ IN ARRAY ARRAY['rule','variant','mechanism','annotation','block','designator'] LOOP
  IF nullif(proof->field_,'null'::jsonb) IS DISTINCT FROM nav->field_ THEN RAISE EXCEPTION 'contextual named source changes retained metadata' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF proof->>'kind' IS DISTINCT FROM nav->>'relation_kind'
  OR (proof->>'resolution' IS DISTINCT FROM nav->>'resolution' AND proof->>'resolution' IS DISTINCT FROM 'insufficient_evidence') THEN
  RAISE EXCEPTION 'contextual named source changes retained kind or resolution' USING ERRCODE='23514'; END IF;
 role_:=CASE original_->>'role' WHEN 'named_link_subject' THEN 'subject' WHEN 'named_link_cue' THEN 'cue' WHEN 'named_link_target' THEN 'argument' ELSE 'definition_subject' END;
 IF NOT ops.primary_navigation_role_matches(layers,ref,node,role_,p_view,carrier||jsonb_build_object('value',outer_->'producer_value'))
  OR (role_='definition_subject' AND original_->>'definition_subject_kind' IS DISTINCT FROM nav->>'definition_subject_kind') THEN
  RAISE EXCEPTION 'contextual named source changes retained role, source extent or subject kind' USING ERRCODE='23514'; END IF;
 RETURN nav||jsonb_build_object('primary_node',ref,'source_role',original_->>'role','selected_resolution',proof->>'resolution');
END $$;
REVOKE ALL ON FUNCTION ops.contextual_primary_named_cue(bigint,kb.source_view,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.contextual_component_section(ref jsonb,work_digest text,p_run bigint,p_layers jsonb)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb; term jsonb; passage jsonb; pin jsonb; v kb.source_view; piece jsonb;
 item_ jsonb; header_ jsonb; layers jsonb; primary_ jsonb; primary_ref jsonb; designator_ text;
BEGIN
 IF ref->>'project_id' IS DISTINCT FROM (SELECT project_id FROM ops.run WHERE id=p_run) THEN RETURN NULL; END IF;
 retained:=ops.resolve_retained_component(ref);
 term:=retained->'component'->'term';
 SELECT p INTO STRICT passage FROM jsonb_array_elements(retained->'report'->'inputs'->'passages') p
  WHERE p->>'passage_id'=term->>'passage_id';
 SELECT s INTO STRICT pin FROM jsonb_array_elements(retained->'report'->'inputs'->'sources') s
  WHERE encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')=passage->>'source_ref';
 IF pin->>'native_content_digest' IS DISTINCT FROM work_digest THEN RETURN NULL; END IF;
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=(pin->>'source_view_id')::bigint
  AND native_task_id=(pin->>'native_task_id')::bigint AND native_product_key=pin->>'native_product_key'
  AND native_content_digest=work_digest AND projection_digest=pin->>'projection_digest'
  AND recipe_digest=pin->>'recipe_digest';
 SELECT p INTO STRICT piece FROM jsonb_array_elements(v.projection->'pieces') p
  WHERE p->>'kind'='native_text' AND NOT p ? 'cell_index' AND coalesce(p->>'source_field','text')='text'
   AND (p->>'start')::bigint<=(term->>'start')::bigint AND (term->>'end')::bigint<=(p->>'end')::bigint;
 SELECT native_json INTO STRICT item_ FROM ops.read_pdf_published_items(
  v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[piece->>'item_ref']);
 IF item_->>'content_layer' IS DISTINCT FROM 'body' OR item_->'parent' IS NULL THEN RETURN NULL; END IF;
 SELECT n.native_json INTO header_ FROM jsonb_array_elements(v.projection->'pieces') p
  CROSS JOIN LATERAL ops.read_pdf_published_items(
   v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[p->>'item_ref']) n
  WHERE p->>'kind'='native_text' AND NOT p ? 'cell_index'
   AND (p->>'end')::bigint<=(piece->>'start')::bigint
   AND n.native_json->>'label'='section_header' AND n.native_json->>'content_layer'='body'
   AND n.native_json->'parent'=item_->'parent'
  ORDER BY (p->>'end')::bigint DESC LIMIT 1;
 IF header_ IS NULL THEN RETURN NULL; END IF;
 layers:=ops.primary_characterization_layers(p_run,v,p_layers);
 SELECT jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a INTO STRICT primary_ref,primary_
 FROM jsonb_each(layers) l CROSS JOIN LATERAL jsonb_array_elements(l.value->'annotations') a
 WHERE a->'navigation'->>'kind'='section_heading' AND a->'navigation'->>'pointer'=header_->>'self_ref'
  AND ops.primary_characterization_in_view(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id'),a,v.id);
 primary_:=ops.primary_navigation_node(layers,primary_ref,'[]',v);
 IF ops.primary_navigation_role_text(layers,primary_ref,primary_,'heading',v) IS DISTINCT FROM header_->>'text' THEN RETURN NULL; END IF;
 designator_:=ops.primary_navigation_role_text(layers,primary_ref,primary_,'designator',v);
 IF designator_ IS DISTINCT FROM primary_->'navigation'->>'designator' THEN RETURN NULL; END IF;
 RETURN designator_;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION ops.contextual_component_section(jsonb,text,bigint,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.contextual_component_section(jsonb,text,bigint,jsonb) TO corpus_sem_reader,corpus_sem_writer;

-- A heading is an exact source occurrence. The release packet map extends work
-- custody across independently published excerpts, without equating their pointers.
-- Return only an alias whose other endpoint is the component's exact original term.
CREATE OR REPLACE FUNCTION ops.contextual_definition_alias(ref jsonb,edge_ref jsonb,p_run bigint,p_layers jsonb)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb; component jsonb; term jsonb; passage jsonb; source_ jsonb;
 view_ kb.source_view; piece jsonb; rows_ jsonb; edge_ jsonb; member_ jsonb;
 endpoint_ jsonb; anchor_ jsonb; matching_index integer; alternate jsonb; edge_view kb.source_view; layers jsonb; primary_ jsonb; primary_ref jsonb; source_role text;
BEGIN
 IF ref->>'project_id' IS DISTINCT FROM edge_ref->>'project_id' OR ref->>'project_id' IS DISTINCT FROM (SELECT project_id FROM ops.run WHERE id=p_run) THEN RETURN NULL; END IF;
 rows_:=ops.resolve_retained_source_contribution(edge_ref)->'contributions';
 IF NOT EXISTS(SELECT FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id
  JOIN ops.method m ON m.id=c.method_id WHERE t.id=(edge_ref->>'origin_task_id')::bigint
   AND m.name='structure.scoped_relations' AND m.version='17') THEN RETURN NULL; END IF;
 SELECT r INTO STRICT edge_ FROM jsonb_array_elements(rows_) r
 WHERE r->>'contribution_id'=edge_ref->>'contribution_id';
 IF NOT coalesce(edge_->>'kind'='relation' AND edge_->>'semantic_type'='structural.scoped_attachment'
  AND edge_->'component'->>'question'='source_named_links'
  AND edge_->'component'->>'attachment_kind'='alias'
  AND edge_->'component'->>'question_version'='4'
  AND jsonb_array_length(edge_->'endpoints')=2,false) THEN RETURN NULL; END IF;
 SELECT * INTO STRICT edge_view FROM kb.source_view WHERE id=(edge_->'pin'->>'source_view_id')::bigint
  AND native_task_id=(edge_->'pin'->>'native_product_task_id')::bigint AND native_product_key=edge_->'pin'->>'product_key'
  AND native_content_digest=edge_->'pin'->>'product_digest' AND projection_digest=edge_->'pin'->>'projection_digest';
 layers:=ops.primary_characterization_layers(p_run,edge_view,p_layers);primary_ref:=edge_->'component'->'primary_node';
 IF primary_ref IS NULL OR NOT layers ? data.canonical_json(primary_ref->'layer') THEN RETURN NULL; END IF;
 primary_:=ops.primary_navigation_node(layers,primary_ref,'[]',edge_view);
 IF primary_->'navigation'->>'kind' IS DISTINCT FROM 'named_link' OR primary_->'navigation'->>'relation_kind' IS DISTINCT FROM 'alias'
  OR primary_->'navigation'->>'resolution' IS DISTINCT FROM 'located' THEN RETURN NULL; END IF;
 retained:=ops.resolve_retained_component(ref);
 component:=retained->'component';
 IF edge_->'component'->>'scope' IS DISTINCT FROM component->>'scope'
  OR edge_->'component'->>'effective_version' IS DISTINCT FROM component->>'effective_version'
  THEN RETURN NULL; END IF;
 term:=component->'term';
 SELECT p INTO STRICT passage FROM jsonb_array_elements(retained->'report'->'inputs'->'passages') p
 WHERE p->>'passage_id'=term->>'passage_id';
 SELECT x INTO STRICT source_ FROM jsonb_array_elements(retained->'report'->'inputs'->'sources') x
 WHERE encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(x)),'UTF8')),'hex')=passage->>'source_ref';
 SELECT * INTO STRICT view_ FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint
  AND native_task_id=(source_->>'native_task_id')::bigint AND native_product_key=source_->>'native_product_key'
  AND native_content_digest=source_->>'native_content_digest' AND projection_digest=source_->>'projection_digest'
  AND recipe_digest=source_->>'recipe_digest';
 SELECT p INTO STRICT piece FROM jsonb_array_elements(view_.projection->'pieces') p
 WHERE p->>'kind'='native_text' AND NOT p ? 'cell_index' AND coalesce(p->>'source_field','text')='text'
  AND (p->>'start')::bigint<=(term->>'start')::bigint AND (term->>'end')::bigint<=(p->>'end')::bigint;
 FOR member_ IN SELECT value FROM jsonb_array_elements(edge_->'endpoints') LOOP
  SELECT r INTO STRICT endpoint_ FROM jsonb_array_elements(rows_) r
  WHERE r->>'contribution_id'=member_->>'contribution_id';
  source_role:=CASE member_->>'role' WHEN 'attachment' THEN 'subject' WHEN 'target' THEN 'argument' END;
  IF source_role IS NULL OR NOT ops.primary_navigation_role_matches(layers,primary_ref,primary_,source_role,edge_view,endpoint_) THEN RETURN NULL; END IF;
  anchor_:=endpoint_->'anchors'->0;
  IF NOT coalesce(endpoint_->>'kind'='occurrence' AND jsonb_array_length(endpoint_->'anchors')=1
   AND anchor_->>'precision'='exact' AND anchor_->>'space'='native',false) THEN RETURN NULL; END IF;
  IF (anchor_->'pin'->>'native_product_task_id',anchor_->'pin'->>'product_key',
       anchor_->'pin'->>'product_digest',anchor_->>'pointer',anchor_->>'source_piece')
     IS NOT DISTINCT FROM
     (view_.native_task_id::text,view_.native_product_key,view_.native_content_digest,
      piece->>'item_ref',term->>'text')
   AND (anchor_->>'start')::bigint=(term->>'start')::bigint-(piece->>'start')::bigint
   AND (anchor_->>'end')::bigint=(term->>'end')::bigint-(piece->>'start')::bigint THEN
   IF matching_index IS NOT NULL THEN RETURN NULL; END IF;
   matching_index:=1;
  ELSE
   IF alternate IS NOT NULL THEN RETURN NULL; END IF;
   alternate:=anchor_;
  END IF;
 END LOOP;
 IF matching_index IS NULL THEN RETURN NULL; END IF;
 RETURN alternate->>'source_piece';
EXCEPTION WHEN no_data_found OR too_many_rows THEN RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION ops.contextual_definition_alias(jsonb,jsonb,bigint,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.contextual_definition_alias(jsonb,jsonb,bigint,jsonb) TO corpus_sem_reader,corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.contextual_section_headings(
 release_ text,sources jsonb,source_view bigint,scope_ text,effective_version text,p_run bigint,p_layers jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE packets jsonb; source_ jsonb; source_work text; source_digest text; selected_work text;
 targets jsonb; complete boolean:=true; v kb.source_view; layers jsonb; l record; a jsonb; primary_ref jsonb; primary_ jsonb;
 node_ jsonb; heading_ text; designator_ text; headings jsonb:='[]'; covered_ boolean;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT packets FROM sem.input WHERE release_id=release_ AND input_kind='dependency' AND input_name='execution/implementation/operations/section-packets.json';
 IF packets->'version' IS DISTINCT FROM '1'::jsonb OR jsonb_typeof(packets->'packets') IS DISTINCT FROM 'object'
  OR jsonb_typeof(packets->'native_products') IS DISTINCT FROM 'object' OR jsonb_typeof(sources) IS DISTINCT FROM 'array'
  OR jsonb_array_length(sources) NOT BETWEEN 1 AND 256 OR nullif(scope_,'') IS NULL
  OR (SELECT count(*)<>count(DISTINCT s) FROM jsonb_array_elements(sources) s)
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(sources) s WHERE (s->>'source_view_id')::bigint=source_view)
  OR EXISTS(SELECT FROM jsonb_array_elements(sources) s WHERE s->>'project_id' IS DISTINCT FROM (SELECT project_id FROM ops.run WHERE id=p_run)) THEN
  RAISE EXCEPTION 'invalid selected heading source inventory' USING ERRCODE='23514'; END IF;
 SELECT CASE WHEN packets->'native_products'->>sv.native_content_digest=d.content_hash THEN packets->'packets'->>d.content_hash END,sv.native_content_digest
 INTO STRICT source_work,source_digest FROM kb.source_view sv JOIN kb.document d ON d.id=sv.document_id WHERE sv.id=source_view;
 FOR source_ IN SELECT value FROM jsonb_array_elements(sources) LOOP
  PERFORM ops.validate_structural_source(source_);
  SELECT * INTO STRICT v FROM kb.source_view WHERE id=(source_->>'source_view_id')::bigint;
  SELECT CASE WHEN packets->'native_products'->>v.native_content_digest=d.content_hash THEN packets->'packets'->>d.content_hash END INTO selected_work FROM kb.document d WHERE d.id=v.document_id;
  IF v.native_content_digest<>source_digest AND (selected_work IS NULL OR source_work IS NULL) THEN complete:=false; END IF;
  IF v.native_content_digest<>source_digest AND (selected_work IS NULL OR selected_work IS DISTINCT FROM source_work) THEN CONTINUE; END IF;
  layers:=ops.primary_characterization_layers(p_run,v,p_layers);
  SELECT EXISTS(SELECT FROM jsonb_each(layers) layer_ CROSS JOIN LATERAL jsonb_array_elements(layer_.value->'coverage') c
   WHERE c->>'family'='construction.navigation' AND c->>'availability'='available' AND c->>'outcome' IN ('complete','empty')
    AND NOT EXISTS(SELECT FROM jsonb_array_elements(coalesce(c->'unexamined','[]')) u WHERE u->>'projection'=v.projection_digest)
    AND EXISTS(SELECT FROM jsonb_array_elements(c->'examined') e WHERE e->>'projection'=v.projection_digest
     AND coalesce((e->>'start')::bigint,0)=0 AND (e->>'end')::bigint>=char_length(v.projection->>'text'))) INTO covered_;
  IF NOT covered_ THEN complete:=false; END IF;
  FOR l IN SELECT * FROM jsonb_each(layers) LOOP
   FOR a IN SELECT value FROM jsonb_array_elements(l.value->'annotations') WHERE value->'navigation'->>'kind'='section_heading' AND ops.primary_characterization_in_view(layers,jsonb_build_object('layer',l.key::jsonb,'local_id',value->>'local_id'),value,v.id) LOOP
    primary_ref:=jsonb_build_object('layer',l.key::jsonb,'local_id',a->>'local_id');primary_:=ops.primary_navigation_node(layers,primary_ref,'[]',v);
    heading_:=ops.primary_navigation_role_text(layers,primary_ref,primary_,'heading',v);designator_:=ops.primary_navigation_role_text(layers,primary_ref,primary_,'designator',v);
    SELECT native_json INTO STRICT node_ FROM ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[primary_->'navigation'->>'pointer']);
    IF node_->>'label' IS DISTINCT FROM 'section_header' OR node_->>'content_layer' IS DISTINCT FROM 'body'
     OR heading_ IS DISTINCT FROM node_->>'text' OR designator_ IS DISTINCT FROM primary_->'navigation'->>'designator' THEN
     RAISE EXCEPTION 'heading primary fields differ from exact native heading' USING ERRCODE='23514'; END IF;
    headings:=headings||jsonb_build_array(jsonb_build_object('source',source_,'native_content_digest',v.native_content_digest,'native_product_key',v.native_product_key,
     'pointer',node_->>'self_ref','label',heading_,'designator',designator_,'primary',primary_ref));
   END LOOP;
  END LOOP;
 END LOOP;
 WITH grouped AS (
  SELECT h->>'native_content_digest' digest,h->>'native_product_key' product,h->>'pointer' pointer,h->>'label' label,h->>'designator' designator,
   (SELECT jsonb_agg(s ORDER BY encode(sha256(convert_to(data.canonical_json(s),'UTF8')),'hex')) FROM (SELECT DISTINCT x->'source' s FROM jsonb_array_elements(headings) x
    WHERE (x->>'native_content_digest',x->>'native_product_key',x->>'pointer',x->>'label',x->>'designator')=(h->>'native_content_digest',h->>'native_product_key',h->>'pointer',h->>'label',h->>'designator')) citations_) citations,
   jsonb_agg(DISTINCT h->'primary' ORDER BY h->'primary') primary_witnesses
  FROM jsonb_array_elements(headings) h GROUP BY h->>'native_content_digest',h->>'native_product_key',h->>'pointer',h->>'label',h->>'designator'
 ), represented AS (
  SELECT jsonb_build_object('target_id','section-heading:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(digest,product,pointer,0,char_length(label))),'UTF8')),'hex'),
   'designator',designator,'label',label,'pointer',pointer,'citations',citations,'primary_witnesses',primary_witnesses,
   'work_id',coalesce('parent-pdf:'||source_work,'native-packet:'||source_digest),'scope',scope_,'effective_version',effective_version) target FROM grouped
 ) SELECT coalesce(jsonb_agg(target ORDER BY target->>'target_id'),'[]') INTO targets FROM represented;
 RETURN jsonb_build_object('targets',targets,'complete',complete);
EXCEPTION WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'heading inventory cannot resolve exact primary source or release' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.contextual_section_headings(text,jsonb,bigint,text,text,bigint,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.contextual_section_headings(text,jsonb,bigint,text,text,bigint,jsonb) TO corpus_sem_reader,corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.clause_model_concordance(refs jsonb,source_view bigint,population jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE ref jsonb; report_ jsonb; observation_ jsonb; source_ jsonb; original_ jsonb;
 rows_ jsonb; old_frame_ jsonb; focus_ jsonb; current_ jsonb; predicted_ jsonb;
 result_ jsonb:='[]'; comparison_ text;
BEGIN
 FOR ref IN SELECT value FROM jsonb_array_elements(refs) LOOP
  report_:=ops.resolve_retained_structural_report(ref)->'report';
  IF report_->>'kind' IS DISTINCT FROM 'clause_classification' THEN
   RAISE EXCEPTION 'model concordance requires retained clause observation' USING ERRCODE='23514'; END IF;
  FOR observation_ IN SELECT value FROM jsonb_array_elements(report_->'clause_classification'->'readings') LOOP
   SELECT src INTO STRICT source_ FROM jsonb_array_elements(report_->'inputs'->'passages') p
   JOIN LATERAL jsonb_array_elements(report_->'inputs'->'sources') src
    ON encode(sha256(convert_to(data.canonical_json(src),'UTF8')),'hex')=p->>'source_ref'
   WHERE p->>'passage_id'=observation_->'selection'->>'passage_id';
   IF (source_->>'source_view_id')::bigint<>source_view THEN CONTINUE; END IF;
   original_:=observation_->'selection'->'frame';
   rows_:=ops.resolve_retained_source_contribution(original_)->'contributions';
   SELECT c INTO STRICT old_frame_ FROM jsonb_array_elements(rows_) c
    WHERE c->>'contribution_id'=original_->>'contribution_id';
   SELECT m->'extents' INTO STRICT focus_ FROM jsonb_array_elements(old_frame_->'component'->'frame_members') m
    WHERE m->>'role'='focus';
   SELECT reading->'component' INTO STRICT current_
   FROM jsonb_array_elements(population) reading JOIN LATERAL jsonb_array_elements(population) frame
     ON frame->>'contribution_id'=reading->'component'->>'frame'
   JOIN LATERAL jsonb_array_elements(frame->'component'->'frame_members') m ON m->>'role'='focus'
   WHERE reading->'component'->>'kind'='predicate_reading' AND frame->'component'->>'kind'='predicate_frame'
    AND frame->'component'->>'focus_state'='exact' AND frame->'pin'=old_frame_->'pin'
    AND m->'extents'=focus_
    AND (SELECT jsonb_object_agg(key,value) FROM jsonb_each(frame->'component') WHERE key IN
      ('annotation','block','predicate_token','variant','scope','effective_version'))
     IS NOT DISTINCT FROM (SELECT jsonb_object_agg(key,value) FROM jsonb_each(old_frame_->'component') WHERE key IN
      ('annotation','block','predicate_token','variant','scope','effective_version'));
   predicted_:=observation_->'function'->0;
   comparison_:=CASE WHEN predicted_->'accepted' IS DISTINCT FROM 'true'::jsonb THEN 'withheld'
    WHEN predicted_->>'label'=current_->>'reading' THEN 'agrees' ELSE 'disagrees' END;
   result_:=result_||jsonb_build_array(jsonb_build_object(
    'reference',ref,'observation',observation_,'deterministic_reading',current_->>'reading','comparison',comparison_));
  END LOOP;
 END LOOP;
 RETURN result_;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'retained classification differs from exact current deterministic frame' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.clause_model_concordance(jsonb,bigint,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_source_contribution_report(p_task bigint,p_envelope jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t ops.task; v kb.source_view; shape json; op jsonb; contribution jsonb; anchor_ jsonb; ep jsonb;
 anchors jsonb; identities text[]; expected text; previous_ends jsonb; coordinate text; actual bigint;
 declaration json; role_definition jsonb; retained ops.task; binding jsonb; old_view kb.source_view; new_view kb.source_view; old_descriptor jsonb; new_descriptor jsonb; retained_body jsonb; retained_digests jsonb:='{}'; retained_sources jsonb:='{}';
 operation_map jsonb; anchor_map jsonb; formula_relation_endpoints jsonb;
 output_counts jsonb; schemas jsonb:='{}'; contract_projection jsonb;
 allowed_contracts jsonb; payload_contract text; bound_semantics jsonb;
 local_ jsonb; local_request jsonb; local_result jsonb; selected_ids jsonb; local_inputs jsonb;
 predicate_population jsonb; table_config jsonb; table_mode text; table_policy_id text; formula_meaning jsonb;
 table_expected jsonb; table_actual jsonb;
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
 IF (p_envelope->>'method'='structure.scoped_relations' AND p_envelope->>'operation_version' IS DISTINCT FROM '17')
  OR (p_envelope->>'method'='retrieve.contextual' AND p_envelope->>'operation_version' IS DISTINCT FROM '11')
  OR (p_envelope->>'method'='locate.definition_terms' AND p_envelope->>'operation_version' IS DISTINCT FROM '2') THEN
  RAISE EXCEPTION 'obsolete contribution producer requires regeneration under its current contract' USING ERRCODE='23514'; END IF;
 IF p_envelope->>'method'='structure.scoped_relations' THEN
  SELECT params INTO STRICT table_config FROM ops.method_config WHERE id=t.method_config_id;
  PERFORM ops.validate_source_table_note_scope(v,p_envelope->'contributions',ops.primary_characterization_layers(t,v,table_config));
  table_mode:=table_config->>'interpretation_mode';
  IF table_mode IS NULL OR table_mode NOT IN ('feasibility','independent','coupled','correspondence')
   OR jsonb_typeof(table_config->'interpretation_weight_scale') IS DISTINCT FROM 'string'
   OR table_config->>'interpretation_weight_scale' NOT IN ('0.5','1','2') THEN
   RAISE EXCEPTION 'invalid registered table interpretation policy' USING ERRCODE='23514';
  END IF;
  IF table_mode<>'correspondence' THEN
   table_policy_id:='table-policy:shared-table-band-3:'||table_mode||':'||(table_config->>'interpretation_weight_scale');
  END IF;
 END IF;
 IF p_envelope->>'source' IS NULL OR p_envelope->>'source' NOT IN (t.unit_key,v.key) THEN
  RAISE EXCEPTION 'contribution source differs from selected task/view' USING ERRCODE='23514'; END IF;
 IF p_envelope->>'method'='extract.pm2_hanlp' AND p_envelope->>'operation_version'='2' THEN
  PERFORM ops.validate_hanlp_v2_report(t.id,p_envelope);
 END IF;
 IF (SELECT count(*)<>count(DISTINCT o->>'operation_key') FROM jsonb_array_elements(p_envelope->'contribution_operations') o) THEN
  RAISE EXCEPTION 'duplicate contribution operation identity' USING ERRCODE='23514'; END IF;
 SELECT array_agg(x->>'contribution_id') INTO identities FROM jsonb_array_elements(p_envelope->'contributions') x;
 IF cardinality(identities) IS DISTINCT FROM (SELECT count(DISTINCT x) FROM unnest(identities) x)
  AND cardinality(identities)>0 THEN RAISE EXCEPTION 'duplicate contribution identity' USING ERRCODE='23514'; END IF;
 SELECT jsonb_object_agg(o->>'operation_key',o) INTO operation_map FROM jsonb_array_elements(p_envelope->'contribution_operations') o;
 IF EXISTS(SELECT FROM jsonb_each(operation_map) o
  WHERE o.value->>'question'='source_formula_occurrences'
   AND (p_envelope->>'method' IS DISTINCT FROM 'structure.scoped_relations'
    OR p_envelope->>'operation_version' IS DISTINCT FROM '17'
    OR o.value->>'operation_version' IS DISTINCT FROM '1')) THEN
  RAISE EXCEPTION 'formula occurrence operation requires its released producer' USING ERRCODE='23514';
 END IF;
 -- Validate endpoint and member bases by exact identity without rescanning the report.
 SELECT COALESCE(jsonb_object_agg(c->>'contribution_id',COALESCE(c->'anchors','[]')),'{}')
 INTO anchor_map FROM jsonb_array_elements(p_envelope->'contributions') c;
 IF EXISTS(SELECT FROM jsonb_each(operation_map) o
  WHERE o.value->>'question'='source_formula_occurrences') THEN
  SELECT COALESCE(jsonb_object_agg(e->>'contribution_id',true),'{}') INTO formula_relation_endpoints
  FROM jsonb_array_elements(p_envelope->'contributions') c
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c->'endpoints','[]')) e
  WHERE c->>'kind'='relation'
   AND operation_map->(c->>'operation_key')->>'question' IS DISTINCT FROM 'source_witnessed_links';
 END IF;
 SELECT COALESCE(jsonb_object_agg(key,n),'{}') INTO output_counts FROM (
  SELECT c->>'operation_key' AS key,count(*) AS n FROM jsonb_array_elements(p_envelope->'contributions') c GROUP BY c->>'operation_key') counts;
 SELECT convert_from(content,'UTF8')::jsonb INTO contract_projection FROM sem.artifact
  WHERE release_id=t.release_id AND artifact_name='contribution_projection.json';
 allowed_contracts:=contract_projection->'contracts';
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
   IF (local_->>'policy_version'='source-correspondence-1') IS DISTINCT FROM
      COALESCE(table_mode='correspondence',false) THEN
    RAISE EXCEPTION 'table correspondence requires its registered producer and policy' USING ERRCODE='23514';
   END IF;
   IF local_->>'seal' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(local_-'seal'),'UTF8')),'hex')
    OR local_->>'constraint_id' IS DISTINCT FROM op->>'operation_key'
    OR op->>'operation_version' IS DISTINCT FROM 'local-interpretation-2'
    OR COALESCE(local_->>'policy_version','')=''
    OR jsonb_array_length(selected_ids)<>(SELECT count(DISTINCT id) FROM jsonb_array_elements_text(selected_ids) x(id))
    OR EXISTS(SELECT FROM jsonb_array_elements_text(selected_ids) x(id) WHERE NOT anchor_map ? id)
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
    IF local_->>'policy_mode'<>'not_run' OR (local_->>'coupling_enabled')::boolean IS DISTINCT FROM false
     OR op->>'outcome'<>'not_run' OR local_->>'probability_standing'<>'not_computed'
     OR local_ ?| ARRAY['request','result','request_digest','result_digest'] THEN
     RAISE EXCEPTION 'unrun local interpretation cannot carry computed probabilities' USING ERRCODE='23514'; END IF;
   ELSE
    IF NOT local_ ?& ARRAY['request','result','request_digest','result_digest']
     OR local_->>'request_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(local_->'request'),'UTF8')),'hex')
     OR local_->>'result_digest' IS DISTINCT FROM encode(sha256(convert_to(data.canonical_json(local_->'result'),'UTF8')),'hex') THEN
     RAISE EXCEPTION 'local interpretation request/result custody differs' USING ERRCODE='23514'; END IF;
    local_request:=data.record_source_json(local_->'request'); local_result:=data.record_source_json(local_->'result');
    IF table_policy_id IS NOT NULL AND (
     local_->>'policy_version' IS DISTINCT FROM 'shared-table-band-3'
     OR local_request->>'policy_dependency_id' IS DISTINCT FROM table_policy_id
     OR (local_->>'policy_mode' IS DISTINCT FROM table_mode AND NOT (
      table_mode='coupled' AND local_->>'policy_mode'='independent'))) THEN
     RAISE EXCEPTION 'table interpretation differs from registered mode or weight scale' USING ERRCODE='23514';
    END IF;
    IF (local_request ? 'feasibility_control' AND jsonb_typeof(local_request->'feasibility_control') IS DISTINCT FROM 'boolean')
     OR (local_request->'feasibility_control'='true'::jsonb AND (
      jsonb_array_length(local_request->'potentials')=0 OR EXISTS(
       SELECT FROM jsonb_array_elements(local_request->'potentials') factor
       WHERE jsonb_array_length(factor->'scope')<>1 OR EXISTS(
        SELECT FROM jsonb_array_elements(factor->'values') factor_value(value)
        WHERE factor_value.value<>'0'::jsonb)))) THEN
     RAISE EXCEPTION 'local interpretation feasibility control requires explicit zero unary potentials' USING ERRCODE='23514'; END IF;
    IF local_->>'probability_standing' IS DISTINCT FROM 'provisional_candidate_relative'
     OR (local_->>'coupling_enabled')::boolean IS DISTINCT FROM EXISTS(SELECT FROM jsonb_array_elements(local_request->'potentials') factor WHERE jsonb_array_length(factor->'scope')>1)
     OR local_->>'policy_mode' IS DISTINCT FROM (CASE WHEN local_request->'feasibility_control'='true'::jsonb THEN 'feasibility' WHEN EXISTS(SELECT FROM jsonb_array_elements(local_request->'potentials') factor WHERE jsonb_array_length(factor->'scope')>1) THEN 'coupled' WHEN jsonb_array_length(local_request->'potentials')>0 THEN 'independent' ELSE 'feasibility' END)
     OR NOT EXISTS(SELECT FROM jsonb_array_elements(local_request->'dependencies') dep WHERE dep->>'key'=local_request->>'policy_dependency_id' AND dep->>'revision'=local_->>'policy_version') THEN
     RAISE EXCEPTION 'local interpretation mode or policy differs from actual factors' USING ERRCODE='23514'; END IF;
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
    DECLARE axes_ jsonb:='{}'; d_ jsonb; c_ jsonb; t_ jsonb; v_ jsonb; key_ text; candidate_ text;
     scope_ jsonb; size_ numeric; retained_ numeric:=1; tables_ jsonb:='[]'; covered_ jsonb:='[]';
     selected_ jsonb; expected_ jsonb:='[]'; events_ jsonb:='[]'; choices_ jsonb; binding_ jsonb;
     seen_ jsonb:='[]'; index_ integer; position_ integer; table_index_ integer; mass_ numeric; positive_ numeric; displayed_ numeric;
     probability_tolerance_ CONSTANT numeric:=1e-9; undisplayed_mass_ numeric; inconsistent_ text;
    BEGIN
     IF local_result->>'outcome' NOT IN ('completed','invalid_input','infeasible','numerical_failure','resource_limit','cancelled')
      OR local_result->>'omitted_candidate_mass' IS DISTINCT FROM 'unknown'
      OR local_result->'dependencies' IS DISTINCT FROM local_request->'dependencies'
      OR local_result->'selection' IS DISTINCT FROM local_request->'selection'
      OR (local_result->>'outcome'<>'completed' AND local_result->'exact_retained_support' IS DISTINCT FROM 'false'::jsonb) THEN
      RAISE EXCEPTION 'local interpretation result claim/provenance invalid' USING ERRCODE='23514'; END IF;
     IF local_result->>'outcome'='completed' THEN
      IF NOT local_request ?& ARRAY['decisions','dependencies','selection','potentials','constraints','events','marginal_decisions','dependence_scopes','limits','model_dependency_id','ontology_dependency_id','policy_dependency_id']
       OR EXISTS(SELECT FROM unnest(ARRAY['decisions','dependencies','potentials','constraints','events','dependence_scopes']) k WHERE jsonb_typeof(local_request->k) IS DISTINCT FROM 'array')
       OR EXISTS(SELECT FROM unnest(ARRAY['marginals','event_probabilities','alternatives']) k WHERE jsonb_typeof(local_result->k) IS DISTINCT FROM 'array') THEN
       RAISE EXCEPTION 'local interpretation completed request/result shape invalid' USING ERRCODE='23514'; END IF;
      IF local_result->'exact_retained_support' IS DISTINCT FROM 'true'::jsonb
       OR jsonb_typeof(local_result->'log_partition') IS DISTINCT FROM 'number'
       OR abs((local_result->>'log_partition')::numeric)>1.7976931348623157e308
       OR jsonb_array_length(local_request->'decisions')=0 THEN
       RAISE EXCEPTION 'completed local interpretation requires finite exact support' USING ERRCODE='23514'; END IF;
      FOR d_ IN SELECT value FROM jsonb_array_elements(local_request->'decisions') LOOP
       key_:=d_->>'key';
       IF jsonb_typeof(d_->'key') IS DISTINCT FROM 'string' OR COALESCE(key_,'')='' OR axes_ ? key_ OR jsonb_array_length(d_->'candidates')=0
        OR jsonb_array_length(d_->'candidates')<>(SELECT count(DISTINCT c->>'key') FROM jsonb_array_elements(d_->'candidates') c)
        OR EXISTS(SELECT FROM jsonb_array_elements(d_->'candidates') c WHERE jsonb_typeof(c->'key') IS DISTINCT FROM 'string' OR COALESCE(c->>'key','')=''
         OR COALESCE(c->>'kind','') NOT IN ('resolved','unresolved','local_new')
         OR (c->>'kind'='unresolved' AND COALESCE(c->>'reason','')='')) THEN
        RAISE EXCEPTION 'local interpretation decision/candidate population invalid' USING ERRCODE='23514'; END IF;
       SELECT jsonb_agg(c->'key' ORDER BY n) INTO v_ FROM jsonb_array_elements(d_->'candidates') WITH ORDINALITY x(c,n);
       axes_:=axes_||jsonb_build_object(key_,v_);retained_:=retained_*jsonb_array_length(v_);
      END LOOP;
      IF jsonb_array_length(local_request->'dependencies')<>(SELECT count(DISTINCT d->>'key') FROM jsonb_array_elements(local_request->'dependencies') d)
       OR EXISTS(SELECT FROM jsonb_array_elements(local_request->'dependencies') d WHERE COALESCE(d->>'key','')='' OR COALESCE(d->>'revision','')=''
        OR COALESCE(d->>'kind','') NOT IN ('observation','counterevidence','rejected_alternative','retrieval','context','selection','model','ontology','policy')) THEN
       RAISE EXCEPTION 'local interpretation dependencies invalid' USING ERRCODE='23514'; END IF;
      FOREACH key_ IN ARRAY ARRAY['model','ontology','policy'] LOOP
       IF NOT EXISTS(SELECT FROM jsonb_array_elements(local_request->'dependencies') d
        WHERE d->>'key'=local_request->>(key_||'_dependency_id') AND d->>'kind'=key_) THEN
        RAISE EXCEPTION 'local interpretation required dependency kind differs' USING ERRCODE='23514'; END IF;
      END LOOP;
      IF jsonb_array_length(local_request->'selection'->'dependency_ids')=0
       OR jsonb_array_length(local_request->'selection'->'dependency_ids')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(local_request->'selection'->'dependency_ids'))
       OR EXISTS(SELECT FROM jsonb_array_elements_text(local_request->'selection'->'dependency_ids') id WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(local_request->'dependencies') d WHERE d->>'key'=id)) THEN
       RAISE EXCEPTION 'local interpretation selection dependency unavailable' USING ERRCODE='23514'; END IF;
      FOR d_ IN SELECT value FROM jsonb_array_elements(local_request->'dependence_scopes') LOOP
       IF jsonb_typeof(d_->'scope') IS DISTINCT FROM 'array' OR jsonb_array_length(d_->'scope')=0 OR btrim(COALESCE(d_->>'reason',''))=''
        OR jsonb_array_length(d_->'scope')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(d_->'scope'))
        OR EXISTS(SELECT FROM jsonb_array_elements_text(d_->'scope') k WHERE NOT axes_ ? k)
        OR jsonb_array_length(d_->'dependency_ids')=0
        OR jsonb_array_length(d_->'dependency_ids')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(d_->'dependency_ids'))
        OR EXISTS(SELECT FROM jsonb_array_elements_text(d_->'dependency_ids') id WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(local_request->'dependencies') d WHERE d->>'key'=id)) THEN
        RAISE EXCEPTION 'local interpretation dependence scope invalid' USING ERRCODE='23514'; END IF;
      END LOOP;
      FOR t_,table_index_ IN SELECT value,n::integer FROM jsonb_array_elements((local_request->'potentials')||(local_request->'constraints')) WITH ORDINALITY x(value,n) LOOP
       scope_:=t_->'scope';size_:=1;
       IF (table_index_<=jsonb_array_length(local_request->'potentials') AND (NOT t_ ? 'values' OR t_ ? 'allowed'))
        OR (table_index_>jsonb_array_length(local_request->'potentials') AND (NOT t_ ? 'allowed' OR t_ ? 'values'))
        OR jsonb_typeof(COALESCE(t_->'values',t_->'allowed')) IS DISTINCT FROM 'array' THEN
        RAISE EXCEPTION 'local interpretation factor kind/array invalid' USING ERRCODE='23514'; END IF;
       IF COALESCE(t_->>'key','')='' OR tables_ ? (t_->>'key') OR jsonb_typeof(scope_) IS DISTINCT FROM 'array' OR jsonb_array_length(scope_)=0
        OR jsonb_array_length(scope_)<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(scope_)) THEN
        RAISE EXCEPTION 'local interpretation factor scope/key invalid' USING ERRCODE='23514'; END IF;
       tables_:=tables_||jsonb_build_array(t_->>'key');
       FOR key_ IN SELECT value FROM jsonb_array_elements_text(scope_) LOOP
        IF NOT axes_ ? key_ THEN RAISE EXCEPTION 'local interpretation factor axis unavailable' USING ERRCODE='23514'; END IF;
        size_:=size_*jsonb_array_length(axes_->key_);
       END LOOP;
       IF jsonb_array_length(t_->'dependency_ids')=0
        OR jsonb_array_length(t_->'dependency_ids')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(t_->'dependency_ids'))
        OR EXISTS(SELECT FROM jsonb_array_elements_text(t_->'dependency_ids') id
        WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(local_request->'dependencies') d WHERE d->>'key'=id)) THEN
        RAISE EXCEPTION 'local interpretation factor dependency unavailable' USING ERRCODE='23514'; END IF;
       IF jsonb_array_length(COALESCE(t_->'values',t_->'allowed'))<>size_ THEN
        RAISE EXCEPTION 'local interpretation factor cardinality differs from axes' USING ERRCODE='23514'; END IF;
       IF t_ ? 'values' THEN
        covered_:=covered_||scope_;
        FOR v_ IN SELECT value FROM jsonb_array_elements(t_->'values') LOOP
         IF v_='{"nonfinite_float":"-inf"}'::jsonb THEN CONTINUE; END IF;
         IF jsonb_typeof(v_) IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'local interpretation log potential invalid' USING ERRCODE='23514'; END IF;
         IF abs((v_#>>'{}')::numeric)>1.7976931348623157e308 THEN RAISE EXCEPTION 'local interpretation log potential nonfinite' USING ERRCODE='23514'; END IF;
        END LOOP;
       ELSIF EXISTS(SELECT FROM jsonb_array_elements(t_->'allowed') mask_entry
        WHERE jsonb_typeof(mask_entry.value) IS DISTINCT FROM 'boolean') THEN
        RAISE EXCEPTION 'local interpretation constraint support must be boolean' USING ERRCODE='23514'; END IF;
      END LOOP;
      IF EXISTS(SELECT FROM jsonb_object_keys(axes_) k WHERE NOT covered_ ? k) THEN
       RAISE EXCEPTION 'completed local interpretation lacks explicit axis support' USING ERRCODE='23514'; END IF;
      selected_:=local_request->'marginal_decisions';
      IF selected_='null'::jsonb THEN SELECT jsonb_agg(k) INTO selected_ FROM jsonb_object_keys(axes_) k;END IF;
      IF jsonb_array_length(selected_)<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(selected_)) THEN
       RAISE EXCEPTION 'local interpretation marginal selection repeats' USING ERRCODE='23514'; END IF;
      FOR key_ IN SELECT value FROM jsonb_array_elements_text(selected_) LOOP
       IF NOT axes_ ? key_ THEN RAISE EXCEPTION 'local interpretation marginal axis unavailable' USING ERRCODE='23514'; END IF;
       FOR candidate_ IN SELECT value FROM jsonb_array_elements_text(axes_->key_) LOOP
        expected_:=expected_||jsonb_build_array(jsonb_build_array(key_,candidate_));
       END LOOP;
      END LOOP;
      IF jsonb_array_length(local_result->'marginals')<>jsonb_array_length(expected_)
       OR EXISTS(SELECT FROM jsonb_array_elements(local_result->'marginals') m GROUP BY m->>'decision',m->>'candidate' HAVING count(*)>1)
       OR EXISTS(SELECT FROM jsonb_array_elements(local_result->'marginals') m WHERE NOT expected_ @> jsonb_build_array(jsonb_build_array(m->>'decision',m->>'candidate'))) THEN
       RAISE EXCEPTION 'local interpretation marginal membership invalid' USING ERRCODE='23514'; END IF;
      FOR v_ IN SELECT value FROM jsonb_array_elements((local_result->'marginals')||(local_result->'event_probabilities')||(local_result->'alternatives')) LOOP
       IF jsonb_typeof(v_->'probability') IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'local interpretation probability invalid' USING ERRCODE='23514'; END IF;
       IF NOT(0<=(v_->>'probability')::numeric AND (v_->>'probability')::numeric<=1) THEN RAISE EXCEPTION 'local interpretation probability outside unit interval' USING ERRCODE='23514'; END IF;
      END LOOP;
      FOR key_ IN SELECT value FROM jsonb_array_elements_text(selected_) LOOP
       SELECT sum((m->>'probability')::numeric) INTO mass_ FROM jsonb_array_elements(local_result->'marginals') m WHERE m->>'decision'=key_;
       IF abs(mass_-1)>probability_tolerance_ THEN RAISE EXCEPTION 'local interpretation marginal normalization invalid' USING ERRCODE='23514'; END IF;
      END LOOP;
      FOR d_ IN SELECT value FROM jsonb_array_elements(local_request->'events') LOOP
       IF COALESCE(d_->>'key','')='' OR events_ ? (d_->>'key') OR btrim(COALESCE(d_->>'question',''))='' OR jsonb_array_length(d_->'derivations')=0 THEN
        RAISE EXCEPTION 'local interpretation event identity/question invalid' USING ERRCODE='23514'; END IF;
       events_:=events_||jsonb_build_array(d_->>'key');
       FOR choices_ IN SELECT value FROM jsonb_array_elements(d_->'derivations') LOOP
        IF jsonb_array_length(choices_)=0 OR jsonb_array_length(choices_)<>(SELECT count(DISTINCT c->>'decision') FROM jsonb_array_elements(choices_) c)
         OR EXISTS(SELECT FROM jsonb_array_elements(choices_) c WHERE NOT axes_ ? (c->>'decision') OR NOT (axes_->(c->>'decision')) ? (c->>'candidate')) THEN
         RAISE EXCEPTION 'local interpretation event assignment membership invalid' USING ERRCODE='23514'; END IF;
       END LOOP;
      END LOOP;
      IF (jsonb_array_length(selected_)=0 AND jsonb_array_length(events_)=0)
       OR jsonb_array_length(local_result->'event_probabilities')<>jsonb_array_length(events_)
       OR EXISTS(SELECT FROM jsonb_array_elements(local_result->'event_probabilities') e GROUP BY e->>'event' HAVING count(*)>1)
       OR EXISTS(SELECT FROM jsonb_array_elements(local_result->'event_probabilities') e WHERE NOT events_ ? (e->>'event')) THEN
       RAISE EXCEPTION 'local interpretation event membership invalid' USING ERRCODE='23514'; END IF;
      FOR d_ IN SELECT value FROM jsonb_array_elements(local_result->'alternatives') LOOP
       choices_:=d_->'choices';
       IF jsonb_array_length(choices_)<>(SELECT count(*) FROM jsonb_object_keys(axes_))
        OR jsonb_array_length(choices_)<>(SELECT count(DISTINCT c->>'decision') FROM jsonb_array_elements(choices_) c)
        OR EXISTS(SELECT FROM jsonb_array_elements(choices_) c WHERE NOT axes_ ? (c->>'decision') OR NOT (axes_->(c->>'decision')) ? (c->>'candidate')) THEN
        RAISE EXCEPTION 'local interpretation complete assignment membership invalid' USING ERRCODE='23514'; END IF;
       SELECT jsonb_object_agg(c->>'decision',c->>'candidate') INTO binding_ FROM jsonb_array_elements(choices_) c;
       IF seen_ @> jsonb_build_array(binding_) THEN RAISE EXCEPTION 'local interpretation repeats assignment' USING ERRCODE='23514'; END IF;
       seen_:=seen_||jsonb_build_array(binding_);
       FOR t_ IN SELECT value FROM jsonb_array_elements((local_request->'constraints')||(local_request->'potentials')) LOOP
        index_:=0;
        FOR key_ IN SELECT value FROM jsonb_array_elements_text(t_->'scope') LOOP
         SELECT n::integer-1 INTO STRICT position_ FROM jsonb_array_elements_text(axes_->key_) WITH ORDINALITY x(c,n) WHERE c=binding_->>key_;
         index_:=index_*jsonb_array_length(axes_->key_)+position_;
        END LOOP;
        IF (t_ ? 'allowed' AND t_->'allowed'->index_ IS DISTINCT FROM 'true'::jsonb)
         OR (t_ ? 'values' AND t_->'values'->index_='{"nonfinite_float":"-inf"}'::jsonb) THEN
         RAISE EXCEPTION 'local interpretation assignment violates hard support' USING ERRCODE='23514'; END IF;
       END LOOP;
      END LOOP;
      positive_:=(local_result->'search'->>'positive_states')::numeric;
      IF local_result->'search'->'limits' IS DISTINCT FROM local_request->'limits'
       OR EXISTS(SELECT FROM unnest(ARRAY['max_states','block_states','max_workspace_bytes']) k WHERE jsonb_typeof(local_request->'limits'->k) IS DISTINCT FROM 'number' OR COALESCE(local_request->'limits'->>k,'') !~ '^[1-9][0-9]*$')
       OR retained_>(local_request->'limits'->>'max_states')::numeric
       OR jsonb_typeof(local_request->'limits'->'max_seconds') IS DISTINCT FROM 'number'
       OR (local_request->'limits'->>'max_seconds')::numeric<0 OR (local_request->'limits'->>'max_seconds')::numeric>1.7976931348623157e308 THEN
       RAISE EXCEPTION 'local interpretation limits invalid or substituted' USING ERRCODE='23514'; END IF;
      IF EXISTS(SELECT FROM unnest(ARRAY['retained_states','examined_states','positive_states']) k WHERE jsonb_typeof(local_result->'search'->k) IS DISTINCT FROM 'number' OR COALESCE(local_result->'search'->>k,'') !~ '^[0-9]+$')
       OR (local_result->'search'->>'retained_states')::numeric<>retained_ OR (local_result->'search'->>'examined_states')::numeric<>retained_
       OR positive_<=0 OR positive_>retained_ OR jsonb_typeof(local_request->'limits'->'displayed_alternatives') IS DISTINCT FROM 'number'
       OR COALESCE(local_request->'limits'->>'displayed_alternatives','') !~ '^[0-9]+$' THEN
       RAISE EXCEPTION 'local interpretation completed support/count invalid' USING ERRCODE='23514'; END IF;
      displayed_:=(local_request->'limits'->>'displayed_alternatives')::numeric;
      IF jsonb_array_length(local_result->'alternatives')<>least(displayed_,positive_) THEN
       RAISE EXCEPTION 'local interpretation displayed support count invalid' USING ERRCODE='23514'; END IF;
      SELECT COALESCE(sum((a->>'probability')::numeric),0) INTO mass_ FROM jsonb_array_elements(local_result->'alternatives') a;
      IF mass_>1+probability_tolerance_ OR (jsonb_array_length(local_result->'alternatives')=positive_
       AND abs(mass_-1)>probability_tolerance_) THEN
       RAISE EXCEPTION 'local interpretation displayed support probability mass invalid' USING ERRCODE='23514'; END IF;
      undisplayed_mass_:=CASE WHEN jsonb_array_length(local_result->'alternatives')=positive_ THEN 0
       ELSE greatest(0,1-mass_) END;
      -- A marginal is a single choice. An event is a union of conjunctions.
      -- Test membership once per assignment even when several derivations match.
      WITH support AS MATERIALIZED (
       SELECT seen_->(n::integer-1) AS binding,(a->>'probability')::numeric AS mass
       FROM jsonb_array_elements(local_result->'alternatives') WITH ORDINALITY item(a,n)
      ), claims(kind,probability,derivations) AS (
       SELECT 'marginal',(m->>'probability')::numeric,jsonb_build_array(jsonb_build_array(m))
       FROM jsonb_array_elements(local_result->'marginals') m
       UNION ALL
       SELECT 'event',(e->>'probability')::numeric,d->'derivations'
       FROM jsonb_array_elements(local_result->'event_probabilities') e
       JOIN jsonb_array_elements(local_request->'events') d ON d->'key'=e->'event'
      )
      SELECT claim.kind INTO inconsistent_ FROM claims claim
      CROSS JOIN LATERAL (
       SELECT coalesce(sum(a.mass),0) AS mass FROM support a
       WHERE EXISTS(SELECT FROM jsonb_array_elements(claim.derivations) derivation(choices)
        WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(derivation.choices) choice(c)
         WHERE a.binding->>(c->>'decision') IS DISTINCT FROM c->>'candidate'))
      ) matched
      WHERE claim.probability NOT BETWEEN matched.mass-probability_tolerance_
       AND matched.mass+undisplayed_mass_+probability_tolerance_ LIMIT 1;
      IF inconsistent_ IS NOT NULL THEN
       RAISE EXCEPTION 'local interpretation % probability differs from displayed support',inconsistent_ USING ERRCODE='23514'; END IF;
     END IF;
    END;
   END IF;
  END IF;
  actual:=COALESCE((output_counts->>(op->>'operation_key'))::bigint,0);
  IF actual<>(op->>'emitted_count')::bigint OR (actual>0 AND op->>'outcome' IN ('empty','failed','skipped','unsupported','not_run'))
   OR (op->>'outcome' IN ('failed','skipped','unsupported','limited','not_run') AND COALESCE(op->>'reason','')='') THEN
   RAISE EXCEPTION 'operation outcome or cardinality differs from actual contribution population' USING ERRCODE='23514'; END IF;
 END LOOP;
 -- Projected definition terms retain exactly their authenticated component role/location.
 FOR contribution IN SELECT value FROM jsonb_array_elements(p_envelope->'contributions')
  WHERE (value->>'semantic_type'='definition.term' AND (p_envelope->>'method'='locate.definition_terms'
   OR data.record_source_json(value->'value') ? 'component_reference'))
   OR data.record_source_json(value->'value') ? 'role_reference' LOOP
  DECLARE meaning jsonb:=data.record_source_json(contribution->'value'); original jsonb; span_ jsonb; passage jsonb; expected_anchors jsonb; observed_anchors jsonb; key_ text; role_ text;
  BEGIN
   IF meaning ? 'role_reference' THEN
    binding:=meaning->'role_reference'; role_:=binding->>'role';
    original:=ops.resolve_retained_structural_report(binding->'report');
    SELECT c->'span' INTO STRICT span_ FROM jsonb_array_elements(original->'report'->'definition_components'->'role_candidates') c
     WHERE c->>'role'=role_ AND c->>'envelope'=binding->>'envelope' AND c->'index'=binding->'index';
    key_:='retained-definition-role:'||encode(sha256(convert_to(data.canonical_json(binding),'UTF8')),'hex');
    IF p_envelope->>'method'<>'locate.definition_terms' OR p_envelope->>'operation_version'<>'2'
     OR contribution->>'kind'<>'proposal' OR role_ NOT IN ('term','content')
     OR meaning->>'role' IS DISTINCT FROM role_
     OR meaning-ARRAY['role','role_reference']<>'{}' OR binding-ARRAY['role','report','envelope','index']<>'{}'
     OR contribution->>'item_key' IS DISTINCT FROM key_
     OR contribution->>'semantic_type' IS DISTINCT FROM (CASE role_ WHEN 'term' THEN 'definition.term' ELSE 'definition.defining_text' END)
     OR NOT EXISTS(SELECT FROM ops.task_result result WHERE result.task_id=(binding->'report'->>'origin_task_id')::bigint
      AND result.body->>'method'='structure.definition_components' AND result.body->>'operation_version'='10')
     OR NOT EXISTS(SELECT FROM ops.method_config cfg WHERE cfg.id=t.method_config_id AND cfg.params->'role_refs' @> jsonb_build_array(binding)
      AND cfg.params->>'source_product_digest'=v.native_content_digest AND cfg.params->>'source_projection_digest'=v.projection_digest)
     OR contribution->'computation_dependencies' IS DISTINCT FROM jsonb_build_array(binding->'report'->>'product_id',binding->>'envelope',key_) THEN
     RAISE EXCEPTION 'definition role differs from retained indexed observation or producing configuration' USING ERRCODE='23514'; END IF;
   ELSE
    binding:=meaning->'component_reference'; original:=ops.resolve_retained_component(binding); span_:=original->'component'->'term';
    IF p_envelope->>'method'<>'locate.definition_terms' OR contribution->>'kind'<>'occurrence' OR meaning->>'role'<>'defined_term'
    OR meaning-ARRAY['role','component_reference']<>'{}' OR NOT EXISTS(SELECT FROM ops.method_config cfg WHERE cfg.id=t.method_config_id AND cfg.params->'component_refs' @> jsonb_build_array(binding)
     AND cfg.params->>'source_product_digest'=v.native_content_digest AND cfg.params->>'source_projection_digest'=v.projection_digest)
    OR contribution->'computation_dependencies' IS DISTINCT FROM jsonb_build_array(binding->>'product_id',binding->>'component_id','retained-component:'||encode(sha256(convert_to(data.canonical_json(binding),'UTF8')),'hex')) THEN
    RAISE EXCEPTION 'definition term differs from retained component and producing configuration' USING ERRCODE='23514'; END IF;
   END IF;
   SELECT p INTO STRICT passage FROM jsonb_array_elements(original->'report'->'inputs'->'passages') p WHERE p->>'passage_id'=span_->>'passage_id';
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(original->'report'->'inputs'->'sources') src
    WHERE (src->>'source_view_id')::bigint=v.id AND encode(sha256(convert_to(data.canonical_json(src),'UTF8')),'hex')=passage->>'source_ref') THEN
    RAISE EXCEPTION 'definition role belongs to another exact source view' USING ERRCODE='23514'; END IF;
   SELECT jsonb_agg(jsonb_build_object('pointer',p->>'item_ref'||CASE WHEN p->>'source_field'='cell_text' THEN '/data/table_cells/'||(p->>'cell_index') ELSE '' END,
    'start',greatest((span_->>'start')::bigint,(p->>'start')::bigint)-(p->>'start')::bigint,
    'end',least((span_->>'end')::bigint,(p->>'end')::bigint)-(p->>'start')::bigint,
    'source_piece',substring(v.projection->>'text' FROM greatest((span_->>'start')::integer,(p->>'start')::integer)+1 FOR least((span_->>'end')::integer,(p->>'end')::integer)-greatest((span_->>'start')::integer,(p->>'start')::integer))) ORDER BY p->>'item_ref',greatest((span_->>'start')::bigint,(p->>'start')::bigint)-(p->>'start')::bigint)
    INTO expected_anchors FROM jsonb_array_elements(v.projection->'pieces') p WHERE p->>'kind'='native_text' AND (p->>'start')::bigint<(span_->>'end')::bigint AND (p->>'end')::bigint>(span_->>'start')::bigint;
   SELECT jsonb_agg(jsonb_build_object('pointer',a->'pointer','start',a->'start','end',a->'end','source_piece',a->'source_piece') ORDER BY a->>'pointer',(a->>'start')::bigint,(a->>'end')::bigint)
    INTO observed_anchors FROM jsonb_array_elements(contribution->'anchors') a;
   IF expected_anchors IS NULL OR expected_anchors IS DISTINCT FROM observed_anchors THEN
    RAISE EXCEPTION 'definition term location differs from original component source pieces' USING ERRCODE='23514'; END IF;
  END;
 END LOOP;
 IF p_envelope->>'method'='locate.definition_terms' AND p_envelope->>'operation_version'='2' AND EXISTS(
  SELECT FROM ops.method_config cfg,LATERAL jsonb_array_elements(cfg.params->'role_refs') ref
  WHERE cfg.id=t.method_config_id AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') c
   WHERE data.record_source_json(c->'value')->'role_reference'=ref)) THEN
  RAISE EXCEPTION 'projected definition role population misses a configured reference' USING ERRCODE='23514'; END IF;
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
 IF p_envelope->>'method'='retrieve.contextual'
  AND (SELECT count(*) FROM jsonb_array_elements(p_envelope->'contribution_operations') o
   WHERE o ? 'contextual_enrichment')<>1 THEN
  RAISE EXCEPTION 'heading selection requires its complete contextual operation report' USING ERRCODE='23514';
 END IF;
 FOR op IN SELECT value FROM jsonb_array_elements(p_envelope->'contribution_operations') LOOP
  IF NOT op ? 'contextual_enrichment' THEN CONTINUE; END IF;
  DECLARE report jsonb:=op->'contextual_enrichment'; profile jsonb; vec jsonb; inv jsonb;
   candidate_list jsonb; candidate jsonb; decision jsonb; witness jsonb; target_product jsonb;
   profile_map jsonb; vector_map jsonb; inventory_map jsonb; list_map jsonb; expected text; expected_candidates jsonb; normalized_target jsonb; channel_report jsonb; expected_hits jsonb; registry_id text; registry_targets jsonb; reuse_row jsonb; reuse_task ops.task; reuse_run ops.run; current_runtime text;
   reuse_digests jsonb:='{}'; reuse_values jsonb:='{}'; origin_body jsonb; origin_vectors jsonb; meaning_group jsonb; member_id text; expected_meaning jsonb;
   contextual_config jsonb; heading_inventory jsonb; heading_targets jsonb; heading_source text;
   heading_row jsonb; heading_ids jsonb; heading_full_hits jsonb; heading_outcome text;
   heading_origin bigint; heading_body jsonb; heading_constraints jsonb; heading_witnesses jsonb;
   heading_catalog jsonb; heading_catalog_sources jsonb;
  BEGIN
   SELECT params INTO STRICT contextual_config FROM ops.method_config WHERE id=t.method_config_id;
   IF p_envelope->>'method'='retrieve.contextual'
    AND jsonb_array_length(coalesce(contextual_config->'section_sources','[]'))>0 THEN
    IF contextual_config ?| ARRAY['query_context','required_occurrence_ids']
     OR data.record_source_json(p_envelope->'parse_detail') ? 'query_context' THEN
     RAISE EXCEPTION 'section contextual mode cannot combine component query controls' USING ERRCODE='23514'; END IF;
   ELSIF p_envelope->>'method'='retrieve.contextual' AND NOT contextual_config ? 'query_context' THEN
    IF jsonb_typeof(contextual_config->'required_occurrence_ids') IS DISTINCT FROM 'array'
     OR jsonb_array_length(contextual_config->'required_occurrence_ids') NOT BETWEEN 1 AND 256
     OR jsonb_array_length(coalesce(contextual_config->'section_sources','[]'))<>0
     OR data.record_source_json(p_envelope->'parse_detail') ? 'query_context' THEN
     RAISE EXCEPTION 'literal-only contextual control requires exact carriers and no parser signal' USING ERRCODE='23514';
    END IF;
   ELSIF p_envelope->>'method'='retrieve.contextual' THEN
    IF jsonb_typeof(contextual_config->'query_context') IS DISTINCT FROM 'object'
     OR jsonb_typeof(contextual_config->'query_context'->'bindings') IS DISTINCT FROM 'array'
     OR jsonb_array_length(contextual_config->'query_context'->'bindings') NOT BETWEEN 1 AND 32
     OR jsonb_array_length(coalesce(contextual_config->'section_sources','[]'))<>0
     OR EXISTS(SELECT FROM jsonb_array_elements(contextual_config->'query_context'->'bindings') b
      WHERE b->'evidence'->>'release_id' IS DISTINCT FROM t.release_id
       OR b->'evidence'->>'project_id' IS DISTINCT FROM (SELECT project_id FROM ops.run WHERE id=t.run_id)) THEN
     RAISE EXCEPTION 'enriched query context differs from registered source and release' USING ERRCODE='23514';
    END IF;
    IF EXISTS(
     SELECT FROM ops.resolve_retained_source_contributions(
      (SELECT jsonb_agg(b->'evidence') FROM jsonb_array_elements(contextual_config->'query_context'->'bindings') b)) held
     WHERE NOT EXISTS(
      SELECT FROM jsonb_array_elements(held.contributions) r
      WHERE r->>'contribution_id'=held.reference->>'contribution_id'
       AND r->'pin'->>'source_view_id'=v.id::text
       AND r->>'semantic_type'=CASE contextual_config->'query_context'->>'recipe'
        WHEN 'located-frame-1' THEN 'linguistic.predicate_frame'
        WHEN 'located-referent-1' THEN 'maverick.cluster'
        WHEN 'located-discourse-neighbor-1' THEN 'dipo.tree' END)
    ) OR EXISTS(
     SELECT FROM jsonb_array_elements(contextual_config->'query_context'->'bindings') b
     WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') c
      WHERE c->>'semantic_type'='contextual.located_mention'
       AND c->>'occurrence_id'=b->>'occurrence_id')
    ) THEN
     RAISE EXCEPTION 'enriched query context lacks its exact parser and focal source' USING ERRCODE='23514';
    END IF;
   END IF;
   IF contextual_config ? 'required_occurrence_ids' THEN
    IF p_envelope->>'method' IS DISTINCT FROM 'retrieve.contextual'
     OR p_envelope->>'operation_version' IS DISTINCT FROM '11'
     OR jsonb_typeof(contextual_config->'required_occurrence_ids') IS DISTINCT FROM 'array'
     OR jsonb_array_length(contextual_config->'required_occurrence_ids') NOT BETWEEN 1 AND 256
     OR EXISTS(SELECT FROM jsonb_array_elements_text(contextual_config->'required_occurrence_ids') r(id)
      GROUP BY r.id HAVING count(*)<>1 OR r.id !~ '^source-occurrence:[0-9a-f]{64}$')
     OR (SELECT array_agg(r.id ORDER BY r.id)
      FROM jsonb_array_elements_text(contextual_config->'required_occurrence_ids') r(id))
      IS DISTINCT FROM (SELECT array_agg(DISTINCT c->>'occurrence_id' ORDER BY c->>'occurrence_id')
       FROM jsonb_array_elements(p_envelope->'contributions') c
       WHERE c->>'semantic_type'='contextual.located_mention') THEN
     RAISE EXCEPTION 'contextual report differs from its exact configured carrier population' USING ERRCODE='23514';
    END IF;
   END IF;
   IF contextual_config ? 'definition_alias_refs' THEN
    IF p_envelope->>'method' IS DISTINCT FROM 'retrieve.contextual'
     OR p_envelope->>'operation_version' IS DISTINCT FROM '11'
     OR jsonb_array_length(contextual_config->'definition_alias_refs')>256
     OR jsonb_array_length(coalesce(contextual_config->'section_sources','[]'))>0
     OR EXISTS(SELECT FROM jsonb_array_elements(contextual_config->'definition_alias_refs') r
      GROUP BY r->>'contribution_id' HAVING count(*)>1)
     OR EXISTS(SELECT FROM jsonb_array_elements(contextual_config->'definition_alias_refs') r
      WHERE r->>'project_id' IS DISTINCT FROM (SELECT project_id FROM ops.run WHERE id=t.run_id)) THEN
     RAISE EXCEPTION 'definition alias selection differs from the exact contextual binding' USING ERRCODE='23514';
    END IF;
    PERFORM ops.resolve_retained_source_contributions(contextual_config->'definition_alias_refs');
   END IF;
   IF p_envelope->>'method'='retrieve.contextual'
    AND jsonb_array_length(coalesce(contextual_config->'section_sources','[]'))>0 THEN
    heading_inventory:=ops.contextual_section_headings(t.release_id,contextual_config->'section_sources',v.id,
     contextual_config->>'scope',contextual_config->>'effective_version',t.run_id,contextual_config->'characterization_layers');
    heading_targets:=heading_inventory->'targets';
    heading_catalog_sources:=coalesce(contextual_config->'section_catalog_sources','[]');
    IF jsonb_array_length(heading_catalog_sources)>0 THEN
     IF EXISTS(SELECT FROM jsonb_array_elements(contextual_config->'section_sources'||heading_catalog_sources) s
      GROUP BY s->>'source_view_id' HAVING count(*)>1) THEN
      RAISE EXCEPTION 'selected heading and outside catalog sources must be distinct' USING ERRCODE='23514';
     END IF;
     heading_catalog:=ops.contextual_section_headings(t.release_id,
      contextual_config->'section_sources'||heading_catalog_sources,v.id,
      contextual_config->>'scope',contextual_config->>'effective_version',t.run_id,contextual_config->'characterization_layers');
    END IF;
    heading_source:='section-heading-inventory:'||encode(sha256(convert_to(data.canonical_json(
     jsonb_build_array(contextual_config->'section_sources',heading_targets)),'UTF8')),'hex');
    SELECT upstream.task_id,upstream.body INTO STRICT heading_origin,heading_body
    FROM ops.task selected JOIN ops.task_result upstream ON upstream.task_id=coalesce(selected.reused_task_id,selected.id)
    JOIN ops.method_config cfg ON cfg.id=selected.method_config_id JOIN ops.method method ON method.id=cfg.method_id
    WHERE selected.run_id=t.run_id AND selected.unit_id=v.id AND selected.unit_type='source_view'
     AND selected.status IN ('done','empty','reused') AND method.name='structure.scoped_relations' AND method.version='17';
    heading_constraints:=jsonb_build_array(jsonb_build_object(
     'constraint_id','section-citation','relation_kinds',jsonb_build_array('cites-section'),
     'occurrence_role','citation','target_role','heading','multiplicity','one','exhaustive',false));
    IF jsonb_strip_nulls(heading_targets) IS DISTINCT FROM coalesce(report->'section_targets','[]')
     OR report->'section_sources' IS DISTINCT FROM contextual_config->'section_sources'
     OR coalesce(report->'section_catalog_sources','[]') IS DISTINCT FROM heading_catalog_sources
     OR report->'section_source_origin_task_id' IS DISTINCT FROM to_jsonb(heading_origin)
     OR report ? 'curated_registry_id' OR jsonb_array_length(coalesce(report->'component_targets','[]'))<>0
     OR jsonb_array_length(report->'inventories')<>1
     OR EXISTS(
      SELECT FROM jsonb_array_elements(heading_body->'contributions') c,
       LATERAL (SELECT data.record_source_json(c->'value') val) meaning
      WHERE c->>'semantic_type'='structural.located_participant'
       AND meaning.val->>'role'='named_link_subject'
       AND meaning.val->'named_cue'->>'resolution'='target_selection_required'
       AND meaning.val->'named_cue'->>'kind' IN ('section_citation','definition_reference')
       AND coalesce(contextual_config->'characterization_layers','[]') @> jsonb_build_array(meaning.val->'named_cue'->'primary_node'->'layer')
       AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') cc
        WHERE cc->>'semantic_type'='contextual.located_mention'
         AND cc->'computation_dependencies'->>0=c->>'contribution_id'))
     OR (SELECT count(*)<>count(DISTINCT r->>'occurrence_id')
      FROM jsonb_array_elements(report->'section_resolutions') r)
     OR (SELECT count(DISTINCT c->>'occurrence_id') FROM jsonb_array_elements(p_envelope->'contributions') c
      WHERE c->>'semantic_type'='contextual.located_mention')
        <>jsonb_array_length(coalesce(report->'section_resolutions','[]'))
     OR jsonb_array_length(coalesce(report->'section_resolutions','[]'))<>jsonb_array_length(report->'candidate_lists')
     OR jsonb_array_length(report->'candidate_lists')<>jsonb_array_length(report->'relationship_decisions') THEN
     RAISE EXCEPTION 'heading report differs from complete selected target inventory' USING ERRCODE='23514';
    END IF;
   ELSIF report ?| ARRAY['section_targets','section_resolutions','section_catalog_sources'] THEN
    RAISE EXCEPTION 'section heading report lacks its selected source configuration' USING ERRCODE='23514';
   END IF;
   IF EXISTS(SELECT FROM jsonb_each(report->'product_counts') product_count
      WHERE (product_count.value#>>'{}')::integer<>jsonb_array_length(report->product_count.key)) THEN
    RAISE EXCEPTION 'contextual product counts differ from actual typed populations' USING ERRCODE='23514'; END IF;
   IF jsonb_array_length(COALESCE(report->'component_targets','[]'))>0 THEN
    PERFORM ops.validate_component_targets(report->'component_targets');
   END IF;
   IF heading_inventory IS NULL AND p_envelope->>'method'='retrieve.contextual' AND jsonb_strip_nulls(report->'component_targets') IS DISTINCT FROM
    (SELECT jsonb_strip_nulls(params->'target_components') FROM ops.method_config WHERE id=t.method_config_id) THEN
    RAISE EXCEPTION 'contextual source targets differ from complete frozen input population' USING ERRCODE='23514'; END IF;
   registry_id:=NULL; registry_targets:='[]'::jsonb;
   IF (EXISTS(SELECT FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
        WHERE cfg.id=t.method_config_id AND (cfg.params ? 'registry_targets' OR m.name='retrieve.contextual'))
        OR jsonb_array_length(report->'inventories')>0) AND heading_inventory IS NULL AND NOT report ? 'curated_registry_id' AND jsonb_array_length(COALESCE(report->'component_targets','[]'))=0 THEN
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
    IF p_envelope->>'method'='retrieve.contextual' THEN
     expected:=CASE coalesce(contextual_config->>'profile','e5')
      WHEN 'e5' THEN 'encoder-profile:45a1807d2b4d6c8b2217aec6cd9dba7a5ed7b5c451f1e8800eaebc4a379a6397'
      WHEN 'qwen' THEN 'encoder-profile:4ff89ee3472c56c28d99545ddd6207cc0b6a82b9f9931a77b0fea8b86efb55eb' END;
     IF profile->>'profile_id' IS DISTINCT FROM expected THEN
      RAISE EXCEPTION 'contextual profile differs from released configured encoder' USING ERRCODE='23514'; END IF;
    END IF;
   END LOOP;
   FOR vec IN SELECT value FROM jsonb_array_elements(report->'vectors') LOOP
    profile:=profile_map->(vec->>'profile_id');
    expected:='context-vector:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
     vec->>'object_id',vec->>'source_binding',vec->>'profile_id',vec->>'input_digest',vec->>'representation_digest')),'UTF8')),'hex');
    IF profile IS NULL OR vec->>'vector_id' IS DISTINCT FROM expected
     OR (vec->>'source_binding' IS DISTINCT FROM p_envelope->>'source' AND NOT EXISTS(
      SELECT FROM jsonb_array_elements(registry_targets) rt WHERE rt->>'target_id'=vec->>'object_id'
       AND vec->>'source_binding'='curated-target:'||encode(sha256(convert_to(data.canonical_json(rt),'UTF8')),'hex')) AND NOT EXISTS(SELECT FROM jsonb_array_elements(COALESCE(report->'component_targets','[]')) ct WHERE ct->'reference'->>'component_id'=vec->>'object_id' AND vec->>'source_binding'='definition-component:'||encode(sha256(convert_to(data.canonical_json(ct->'reference'),'UTF8')),'hex'))
      AND NOT EXISTS(SELECT FROM jsonb_array_elements(coalesce(heading_targets,'[]')) h
       WHERE h->>'target_id'=vec->>'object_id' AND vec->>'source_binding'=h->>'target_id'))
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
    IF heading_inventory IS NOT NULL AND (inv->>'source_selection' IS DISTINCT FROM heading_source
     OR inv->>'scope' IS DISTINCT FROM contextual_config->>'scope'
     OR inv->>'effective_version' IS DISTINCT FROM contextual_config->>'effective_version'
     OR inv->>'reliable_type' IS DISTINCT FROM 'section-heading'
     OR jsonb_array_length(inv->'targets')<>jsonb_array_length(heading_targets)) THEN
     RAISE EXCEPTION 'heading inventory differs from declared representation scope' USING ERRCODE='23514';
    END IF;
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
     ELSIF heading_inventory IS NOT NULL THEN
      IF NOT EXISTS(SELECT FROM jsonb_array_elements(heading_targets) h
       WHERE h->>'target_id'=target_product->>'target_id'
        AND h->>'target_id'=target_product->>'source_binding'
        AND h->>'label'=target_product->>'label' AND h->>'label'=target_product->>'description'
        AND h->>'scope'=target_product->>'scope' AND target_product->>'type_name'='section-heading'
        AND (h->>'effective_version') IS NOT DISTINCT FROM target_product->>'effective_version'
        AND target_product->>'parent' IS NULL AND coalesce(target_product->'aliases','[]')='[]') THEN
       RAISE EXCEPTION 'heading representation lacks exact original source custody' USING ERRCODE='23514';
      END IF;
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
      ELSIF heading_inventory IS NOT NULL THEN
       SELECT jsonb_build_object('section_heading',jsonb_strip_nulls(h)) INTO STRICT expected_meaning
       FROM jsonb_array_elements(heading_targets) h WHERE h->>'target_id'=member_id;
      ELSE expected_meaning:=jsonb_build_object('curated_target',jsonb_strip_nulls(target_product)); END IF;
      IF meaning_group->'meaning' IS DISTINCT FROM expected_meaning THEN
       RAISE EXCEPTION 'semantic target member differs from authenticated source meaning' USING ERRCODE='23514'; END IF;
     END LOOP;
    END LOOP;
   END LOOP;
   IF p_envelope->>'method'='retrieve.contextual' THEN
    IF jsonb_array_length(report->'inventories') IS DISTINCT FROM 1
     OR jsonb_array_length(report->'profiles')>1 THEN
     RAISE EXCEPTION 'mutual neighborhood requires one inventory and at most one profile' USING ERRCODE='23514'; END IF;
    expected_meaning:=ops.contextual_mutual_neighbors(
      report->'inventories'->0,report->'profiles'->0,report->'vectors');
    IF report->'neighborhood' IS DISTINCT FROM expected_meaning THEN
     RAISE EXCEPTION 'mutual neighborhood differs from exact eligible vectors and ranks' USING ERRCODE='23514'; END IF;
   ELSIF report ? 'neighborhood' THEN
    RAISE EXCEPTION 'mutual neighborhood requires its released producer' USING ERRCODE='23514';
   END IF;
   FOR candidate_list IN SELECT value FROM jsonb_array_elements(report->'candidate_lists') LOOP
    inv:=inventory_map->(candidate_list->>'inventory_id');
    vec:=vector_map->(candidate_list->>'query_vector_id');
    IF inv IS NULL OR (
      candidate_list->>'policy_id'='exact-source-witness-only-1'
      AND (candidate_list ?| ARRAY['query_vector_id','profile_id']
       OR jsonb_array_length(candidate_list->'channel_results')<>1
       OR candidate_list->'channel_results'->0->>'channel' IS DISTINCT FROM 'witness')
     ) OR (
      candidate_list->>'policy_id'<>'exact-source-witness-only-1'
      AND (vec IS NULL OR vec->>'profile_id' IS DISTINCT FROM candidate_list->>'profile_id'
       OR vec->>'object_id' IS DISTINCT FROM candidate_list->>'occurrence_id'
       OR vec->>'source_binding' IS DISTINCT FROM p_envelope->>'source')
     )
     OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') c
      WHERE c->>'occurrence_id'=candidate_list->>'occurrence_id')
     OR jsonb_array_length(candidate_list->'candidates')>(candidate_list->>'unique_target_budget')::integer
     OR (candidate_list->>'eligible_target_count')::integer<>jsonb_array_length(inv->'targets')
     OR (SELECT count(*)<>count(DISTINCT x->>'target_id') FROM jsonb_array_elements(candidate_list->'candidates') x) THEN
     RAISE EXCEPTION 'candidate list differs from frozen source/inventory/vector' USING ERRCODE='23514'; END IF;
    IF candidate_list->>'policy_id' IS DISTINCT FROM (CASE
      WHEN NOT candidate_list ? 'query_vector_id' THEN 'exact-source-witness-only-1'
      WHEN EXISTS(
       SELECT FROM jsonb_array_elements(candidate_list->'channel_results') c WHERE c->>'channel'='witness'
      ) THEN 'exact-source-witness-then-rrf60-1' ELSE 'exact-alias-postgresql-english-cosine-rrf60-1' END)
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
    IF heading_inventory IS NOT NULL THEN
     SELECT r INTO STRICT heading_row FROM jsonb_array_elements(report->'section_resolutions') r
     WHERE r->>'occurrence_id'=candidate_list->>'occurrence_id';
     IF NOT EXISTS(
      SELECT FROM jsonb_array_elements(p_envelope->'contributions') c
      WHERE c->>'semantic_type'='contextual.located_mention'
       AND c->>'occurrence_id'=candidate_list->>'occurrence_id'
       AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'source_role'='named_link_subject'
       AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'relation_kind' IN ('section_citation','definition_reference')
       AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'selected_resolution'='target_selection_required'
       AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'designator'=heading_row->>'designator') THEN
      RAISE EXCEPTION 'section resolution lacks its original retained citation' USING ERRCODE='23514';
     END IF;
     SELECT coalesce(jsonb_agg(jsonb_build_object('target_id',id,'score',1,'evidence',evidence)
      ORDER BY id),'[]'),coalesce(jsonb_agg(id ORDER BY id),'[]')
     INTO heading_full_hits,heading_ids FROM (
      SELECT h->>'target_id' id,jsonb_agg(DISTINCT c->>'contribution_id' ORDER BY c->>'contribution_id') evidence
      FROM jsonb_array_elements(heading_targets) h,
       jsonb_array_elements(p_envelope->'contributions') c,
       LATERAL (SELECT CASE WHEN c->>'semantic_type'='contextual.located_mention'
        THEN data.record_source_json(c->'value') END val) occurrence,
       LATERAL (SELECT (CASE WHEN occurrence.val->>'producer_semantic_type'='structural.located_participant'
        THEN data.record_source_json(occurrence.val->'producer_value') END)->'named_cue' val) cue
      WHERE c->>'semantic_type'='contextual.located_mention'
       AND c->>'occurrence_id'=candidate_list->>'occurrence_id'
       AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'relation_kind' IN ('section_citation','definition_reference')
       AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'source_role'='named_link_subject'
       AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'selected_resolution'='target_selection_required'
       AND cue.val->>'scope'=contextual_config->>'scope'
       AND (cue.val->>'effective_version') IS NOT DISTINCT FROM contextual_config->>'effective_version'
       AND h->>'designator'=ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'designator' AND h->>'designator'=heading_row->>'designator'
      GROUP BY h->>'target_id'
     ) eligible;
     heading_outcome:=CASE
      WHEN NOT EXISTS(
       SELECT FROM jsonb_array_elements(p_envelope->'contributions') c,
        LATERAL (SELECT CASE WHEN c->>'semantic_type'='contextual.located_mention'
        THEN data.record_source_json(c->'value') END val) occurrence,
        LATERAL (SELECT (CASE WHEN occurrence.val->>'producer_semantic_type'='structural.located_participant'
        THEN data.record_source_json(occurrence.val->'producer_value') END)->'named_cue' val) cue
       WHERE c->>'semantic_type'='contextual.located_mention'
        AND c->>'occurrence_id'=candidate_list->>'occurrence_id'
        AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c) IS NOT NULL
        AND cue.val->>'scope'=contextual_config->>'scope'
        AND (cue.val->>'effective_version') IS NOT DISTINCT FROM contextual_config->>'effective_version'
      ) THEN 'insufficient_evidence'
      WHEN NOT (heading_inventory->>'complete')::boolean THEN 'unavailable_representation'
      WHEN jsonb_array_length(heading_ids)>(candidate_list->>'unique_target_budget')::integer THEN 'witness_budget_exceeded'
      WHEN heading_ids='[]' AND (heading_catalog->>'complete')::boolean AND EXISTS(
       SELECT FROM jsonb_array_elements(heading_catalog->'targets') h
       WHERE h->>'designator'=heading_row->>'designator'
        AND NOT EXISTS(SELECT FROM jsonb_array_elements(heading_targets) s
         WHERE s->>'target_id'=h->>'target_id')
      ) THEN 'outside_inventory'
      WHEN jsonb_array_length(heading_ids)=0 THEN 'no_compatible_candidate'
      WHEN jsonb_array_length(heading_ids)=1 THEN 'selected' ELSE 'ambiguous' END;
     IF heading_row->'eligible_target_ids' IS DISTINCT FROM heading_ids
      OR heading_row->>'outcome' IS DISTINCT FROM heading_outcome THEN
      RAISE EXCEPTION 'section resolution differs from complete exact heading population' USING ERRCODE='23514';
     END IF;
     SELECT coalesce(jsonb_agg(h ORDER BY n),'[]') INTO expected_hits
     FROM jsonb_array_elements(heading_full_hits) WITH ORDINALITY x(h,n)
     WHERE n<=(candidate_list->>'unique_target_budget')::integer;
    ELSIF p_envelope->>'method'='retrieve.contextual'
     AND EXISTS(SELECT FROM ops.method_config cfg,
      LATERAL jsonb_array_elements(cfg.params->'relationship_constraints') q
      WHERE cfg.id=t.method_config_id AND q->'relation_kinds' ? 'defined-by') THEN
      SELECT coalesce(jsonb_agg(jsonb_build_object('target_id',id,'score',1,'evidence',evidence)
       ORDER BY id),'[]') INTO expected_hits FROM (
       SELECT ct->'reference'->>'component_id' id,
        jsonb_agg(DISTINCT c->>'contribution_id' ORDER BY c->>'contribution_id') evidence
       FROM jsonb_array_elements(report->'component_targets') ct,
        jsonb_array_elements(p_envelope->'contributions') c,
        LATERAL (SELECT CASE WHEN c->>'semantic_type'='contextual.located_mention'
        THEN data.record_source_json(c->'value') END val) occurrence,
        LATERAL (SELECT CASE WHEN occurrence.val->>'producer_semantic_type' IN ('definition.term','structural.located_participant')
        THEN data.record_source_json(occurrence.val->'producer_value') END val) meaning
       WHERE c->>'semantic_type'='contextual.located_mention'
        AND c->>'occurrence_id'=candidate_list->>'occurrence_id'
        AND (
         (occurrence.val->>'producer_semantic_type'='definition.term'
          AND meaning.val->>'role'='defined_term' AND meaning.val->'component_reference'=ct->'reference')
         OR (occurrence.val->>'producer_semantic_type'='structural.located_participant'
          AND meaning.val->>'role' IN ('named_link_subject','named_link_definition_subject')
          AND jsonb_array_length(c->'anchors')=1
          AND (
           ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'relation_kind'='definition_reference'
           AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'selected_resolution'='target_selection_required'
           AND meaning.val->'named_cue'->>'scope'=contextual_config->>'scope'
           AND meaning.val->'named_cue'->>'effective_version' IS NOT DISTINCT FROM contextual_config->>'effective_version'
           AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',c)->>'designator'
            =ops.contextual_component_section(ct->'reference',v.native_content_digest,t.run_id,contextual_config->'characterization_layers')))
        )
        AND EXISTS(SELECT FROM jsonb_array_elements(inv->'targets') tg WHERE tg->>'target_id'=ct->'reference'->>'component_id')
       GROUP BY ct->'reference'->>'component_id'
      ) eligible;
    ELSE expected_hits:='[]'; END IF;
    SELECT value INTO channel_report FROM jsonb_array_elements(candidate_list->'channel_results')
     WHERE value->>'channel'='witness';
    IF (heading_inventory IS NOT NULL AND expected_hits IS DISTINCT FROM channel_report->'hits')
     OR (heading_inventory IS NULL AND expected_hits='[]' AND channel_report IS NOT NULL)
     OR (expected_hits<>'[]' AND expected_hits IS DISTINCT FROM channel_report->'hits')
     OR jsonb_array_length(expected_hits)>(candidate_list->>'unique_target_budget')::integer THEN
     RAISE EXCEPTION 'witness channel differs from complete exact source and target custody' USING ERRCODE='23514';
    END IF;
    FOR channel_report IN SELECT value FROM jsonb_array_elements(candidate_list->'channel_results') LOOP
     IF channel_report->>'channel'='witness' THEN CONTINUE; END IF;
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
     SELECT h->>'target_id' AS target_id,sum(1::double precision/(60+n) ORDER BY channel) AS score,
      bool_or(channel='witness') AS witnessed
      FROM hits GROUP BY h->>'target_id'
    ), selected AS (
     SELECT target_id,score,row_number() OVER (ORDER BY witnessed DESC,score DESC,target_id) AS rank FROM sums
      ORDER BY witnessed DESC,score DESC,target_id LIMIT (candidate_list->>'unique_target_budget')::integer
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
    IF heading_inventory IS NOT NULL THEN
     SELECT r INTO STRICT heading_row FROM jsonb_array_elements(report->'section_resolutions') r
     WHERE r->>'occurrence_id'=decision->>'occurrence_id';
     SELECT coalesce(jsonb_agg(w ORDER BY w->>'witness_id'),'[]') INTO heading_witnesses
     FROM jsonb_array_elements(candidate_list->'channel_results') ch,
      LATERAL jsonb_array_elements(ch->'hits') hit,
      LATERAL jsonb_array_elements_text(hit->'evidence') e,
      LATERAL (SELECT jsonb_strip_nulls(jsonb_build_object(
       'witness_id','section-citation:contribution-operation:'||encode(sha256(convert_to(data.canonical_json(
        jsonb_build_array(jsonb_build_array(e,hit->>'target_id',heading_row->>'designator'),'{}'::jsonb)),'UTF8')),'hex'),
       'occurrence_id',decision->>'occurrence_id','target_id',hit->>'target_id',
       'relation','cites-section','source_binding',decision->>'source_binding',
       'scope',decision->>'scope','effective_version',decision->>'effective_version',
       'evidence_ids',jsonb_build_array(e),'basis','explicit_source_cue',
       'support_state',CASE WHEN heading_row->>'outcome' IN ('selected','ambiguous') THEN 'unassessed' ELSE 'ambiguous' END
      )) w) expected_witness
     WHERE ch->>'channel'='witness';
     IF decision->'constraints' IS DISTINCT FROM heading_constraints
      OR decision ? 'proposal' OR coalesce(decision->'exclusions','[]')<>'[]'
      OR decision->'witnesses' IS DISTINCT FROM heading_witnesses
      OR decision->>'outcome' IS DISTINCT FROM (CASE WHEN heading_row->>'outcome' IN ('selected','ambiguous')
       THEN heading_row->>'outcome' ELSE 'insufficient_evidence' END) THEN
      RAISE EXCEPTION 'section decision differs from exact heading witnesses and coverage' USING ERRCODE='23514';
     END IF;
    END IF;
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
      OR EXISTS(SELECT FROM jsonb_array_elements_text(witness->'evidence_ids') e WHERE NOT anchor_map ? e) THEN
      RAISE EXCEPTION 'local proposal differs from examined source/list/evidence' USING ERRCODE='23514'; END IF;
    END IF;
    FOR witness IN SELECT value FROM jsonb_array_elements(decision->'witnesses') LOOP
     IF p_envelope->>'method'='retrieve.contextual' AND witness->>'relation'='defined-by'
      AND (starts_with(witness->>'witness_id','section-definition:') OR EXISTS(
       SELECT FROM jsonb_array_elements(p_envelope->'contributions') carrier
       CROSS JOIN LATERAL (SELECT CASE WHEN carrier->>'semantic_type'='contextual.located_mention'
        THEN CASE WHEN data.record_source_json(carrier->'value')->>'producer_semantic_type'='structural.located_participant'
         THEN data.record_source_json(data.record_source_json(
          carrier->'value')->'producer_value') END END AS original) extracted
       WHERE witness->'evidence_ids' ? (carrier->>'contribution_id')
        AND extracted.original->'named_cue'->>'kind'='definition_reference'
        AND extracted.original->>'role'='named_link_subject'
      )) THEN
      RAISE EXCEPTION 'section nomination cannot establish a definition endpoint' USING ERRCODE='23514';
     END IF;
     IF p_envelope->>'method'='retrieve.contextual' AND witness->>'relation'='defined-by'
      AND (starts_with(witness->>'witness_id','section-term-definition:') OR EXISTS(
       SELECT FROM jsonb_array_elements(p_envelope->'contributions') carrier
       CROSS JOIN LATERAL (SELECT CASE WHEN carrier->>'semantic_type'='contextual.located_mention'
        THEN CASE WHEN data.record_source_json(carrier->'value')->>'producer_semantic_type'='structural.located_participant'
         THEN data.record_source_json(data.record_source_json(
          carrier->'value')->'producer_value') END END AS original) extracted
       WHERE witness->'evidence_ids' ? (carrier->>'contribution_id')
        AND extracted.original->>'role'='named_link_definition_subject'
      )) AND NOT EXISTS(
       SELECT FROM jsonb_array_elements(p_envelope->'contributions') carrier
       CROSS JOIN LATERAL (SELECT CASE WHEN carrier->>'semantic_type'='contextual.located_mention'
        THEN CASE WHEN data.record_source_json(carrier->'value')->>'producer_semantic_type'='structural.located_participant'
         THEN data.record_source_json(data.record_source_json(
          carrier->'value')->'producer_value') END END AS original) extracted
       CROSS JOIN LATERAL (
        SELECT array_agg(ct->'reference'->>'component_id') AS ids
        FROM jsonb_array_elements(report->'component_targets') ct
        WHERE ops.contextual_component_section(ct->'reference',v.native_content_digest,t.run_id,contextual_config->'characterization_layers')
          =ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',carrier)->>'designator'
         AND (
          ops.component_semantic_target(ct->'reference')->'term'->>'text'
           =carrier->'anchors'->0->>'source_piece'
          OR (p_envelope->>'method'='retrieve.contextual' AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',carrier)->>'definition_subject_kind'='term'
           AND (SELECT count(*) FROM jsonb_array_elements(contextual_config->'definition_alias_refs') alias_ref
            WHERE ops.contextual_definition_alias(ct->'reference',alias_ref,t.run_id,contextual_config->'characterization_layers')=carrier->'anchors'->0->>'source_piece')=1)
         )
         AND EXISTS(SELECT FROM jsonb_array_elements(inv->'targets') it
          WHERE it->>'target_id'=ct->'reference'->>'component_id')
       ) matches
       WHERE witness->'evidence_ids'=jsonb_build_array(carrier->'contribution_id')
        AND carrier->>'occurrence_id'=decision->>'occurrence_id'
        AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',carrier)->>'source_role'='named_link_definition_subject'
        AND ops.contextual_primary_named_cue(t.run_id,v,contextual_config->'characterization_layers',carrier)->>'relation_kind'='definition_reference'
        AND extracted.original->'named_cue'->>'resolution'='target_selection_required'
        AND extracted.original->'named_cue'->>'scope'=witness->>'scope'
        AND extracted.original->'named_cue'->>'effective_version' IS NOT DISTINCT FROM witness->>'effective_version'
        AND witness->>'basis'='explicit_source_cue'
        AND cardinality(matches.ids)=1 AND matches.ids[1]=witness->>'target_id'
      ) THEN
      RAISE EXCEPTION 'named section definition differs from its unique exact source term' USING ERRCODE='23514';
     END IF;
     IF starts_with(witness->>'witness_id','section-definition:') AND (
      witness->>'basis' IS DISTINCT FROM 'explicit_source_cue'
      OR witness->>'relation' IS DISTINCT FROM 'defined-by'
      OR NOT EXISTS(SELECT FROM jsonb_array_elements(candidate_list->'channel_results') ch,
       LATERAL jsonb_array_elements(ch->'hits') hit WHERE ch->>'channel'='witness'
       AND hit->>'target_id'=witness->>'target_id' AND (hit->'evidence') @> (witness->'evidence_ids'))
     ) THEN RAISE EXCEPTION 'section relationship lacks its exact section witness nomination' USING ERRCODE='23514'; END IF;
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
  payload_contract:=contract_projection->'payload_contracts'->>(contribution->>'semantic_type');
  IF payload_contract IS NOT NULL AND payload_contract IS DISTINCT FROM contribution->>'contract' THEN
   RAISE EXCEPTION 'contribution does not use its released payload contract' USING ERRCODE='23514'; END IF;
  bound_semantics:=jsonb_build_object('kind',contribution->'kind','semantic_type',contribution->'semantic_type',
    'effect','retain_private','assessment_event','local-contribution-1');
  IF payload_contract IS NOT NULL THEN
   bound_semantics:=bound_semantics||jsonb_build_object(
    'question',operation_map->(contribution->>'operation_key')->'question',
    'value',data.record_source_json(contribution->'value'));
  END IF;
  IF NOT public.json_matches_schema(declaration,bound_semantics::json) THEN
   RAISE EXCEPTION 'contribution semantics differ from released contract' USING ERRCODE='23514'; END IF;
  IF contribution->'pin' IS DISTINCT FROM jsonb_build_object('source',p_envelope->>'source',
    'native_product_task_id',v.native_task_id,'product_key',v.native_product_key,'product_digest',v.native_content_digest,
    'projection_digest',v.projection_digest,'recipe_digest',v.recipe_digest,'source_view_id',v.id) THEN
   RAISE EXCEPTION 'contribution pin differs from exact selected source view' USING ERRCODE='23514'; END IF;
  IF contribution->>'semantic_type' IN ('terminology.interpretation','measurement.interpretation') THEN
   PERFORM ops.require_source_interpretation(t.id,contribution,data.record_source_json(contribution->'value'));
  END IF;
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
   PERFORM data.record_source_json(contribution->'score');
  END IF;
  expected:='source-contribution:'||encode(sha256(convert_to(data.canonical_json(contribution-'contribution_id'),'UTF8')),'hex');
  IF contribution->>'contribution_id' IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'contribution identity differs from immutable contents' USING ERRCODE='23514'; END IF;
  FOR ep IN SELECT value FROM jsonb_array_elements(COALESCE(contribution->'endpoints','[]')) LOOP
   IF NOT anchor_map ? (ep->>'contribution_id') OR ep->>'contribution_id'=contribution->>'contribution_id' THEN
    RAISE EXCEPTION 'contribution endpoint unavailable or self-referential' USING ERRCODE='23514'; END IF;
  END LOOP;
  IF EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(contribution->'members','[]')) x
    WHERE NOT anchor_map ? x OR x=contribution->>'contribution_id') THEN
   RAISE EXCEPTION 'contribution member unavailable or self-referential' USING ERRCODE='23514'; END IF;
  IF (contribution->>'kind'='relation' AND jsonb_array_length(COALESCE(contribution->'endpoints','[]'))<2)
   OR (contribution->>'kind'='composite' AND jsonb_array_length(COALESCE(contribution->'members','[]'))=0) THEN
   RAISE EXCEPTION 'relation/composite contribution lacks endpoints/members' USING ERRCODE='23514'; END IF;
  IF operation_map->(contribution->>'operation_key')->>'question'='source_formula_occurrences' THEN
   formula_meaning:=data.record_source_json(contribution->'value');
   anchor_:=contribution->'anchors'->0;
   IF contribution->>'semantic_type' IS DISTINCT FROM 'structural.located_participant'
    OR contribution->>'kind' IS DISTINCT FROM 'occurrence'
    OR contribution ?| ARRAY['component','endpoints','members']
    OR jsonb_array_length(contribution->'anchors') IS DISTINCT FROM 1
    OR contribution->'anchors'->0->>'space' IS DISTINCT FROM 'native'
    OR contribution->'anchors'->0->>'precision' IS DISTINCT FROM 'exact'
    OR formula_meaning->>'role' IS DISTINCT FROM 'formula_symbol'
    OR formula_meaning->>'syntax_standing' IS DISTINCT FROM 'syntax_only'
    OR formula_meaning->>'input_policy' IS DISTINCT FROM 'captured_inline_equation'
    OR formula_meaning->>'mapping' IS DISTINCT FROM 'exact_native_field'
    OR formula_meaning->>'text' IS DISTINCT FROM anchor_->>'source_piece'
    OR formula_meaning->>'source_pointer' IS DISTINCT FROM anchor_->>'pointer'
    OR formula_meaning->>'region' IS DISTINCT FROM anchor_->>'pointer'
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(v.projection->'pieces') p
      WHERE p->>'kind'='native_text' AND coalesce(p->>'source_field','text')='text' AND NOT p ? 'cell_index'
       AND p->>'item_ref'=anchor_->>'pointer'
       AND (p->>'start')::bigint+(anchor_->>'start')::bigint=(formula_meaning->>'start')::bigint
       AND (p->>'start')::bigint+(anchor_->>'end')::bigint=(formula_meaning->>'end')::bigint)
    OR formula_relation_endpoints ? (contribution->>'contribution_id')
   THEN RAISE EXCEPTION 'inline formula occurrence lacks exact syntax-only standing' USING ERRCODE='23514'; END IF;
  END IF;
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
      CROSS JOIN LATERAL jsonb_array_elements(anchor_map->(e->>'contribution_id')) a
     UNION ALL SELECT a FROM jsonb_array_elements_text(COALESCE(contribution->'members','[]')) m(id)
      CROSS JOIN LATERAL jsonb_array_elements(anchor_map->m.id) a
      WHERE component->>'kind' IN ('predicate_frame','predicate_reading','predicate_cue')
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
    ELSIF component->>'kind' NOT IN ('predicate_frame','predicate_reading','predicate_cue') THEN
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
 IF EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') c WHERE
  CASE c->'component'->>'kind'
   WHEN 'predicate_frame' THEN 'structural.predicate_frame'
   WHEN 'predicate_reading' THEN 'structural.predicate_reading'
   WHEN 'predicate_cue' THEN 'structural.predicate_cue'
   WHEN 'predicate_qualifier' THEN 'structural.predicate_qualification'
   ELSE 'other' END IS DISTINCT FROM
  CASE WHEN c->>'semantic_type' IN ('structural.predicate_frame','structural.predicate_reading',
   'structural.predicate_cue','structural.predicate_qualification') THEN c->>'semantic_type' ELSE 'other' END) THEN
  RAISE EXCEPTION 'predicate contribution differs from its released component type' USING ERRCODE='23514';
 END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') c
  WHERE c->'component'->>'kind' IN ('predicate_frame','predicate_reading','predicate_cue','predicate_qualifier')) THEN
  IF p_envelope->>'method'<>'structure.scoped_relations' OR p_envelope->>'operation_version' IS DISTINCT FROM '17' THEN
   RAISE EXCEPTION 'predicate evidence requires its released producer' USING ERRCODE='23514';
  END IF;
  SELECT jsonb_object_agg(c->>'contribution_id',c) INTO predicate_population
  FROM jsonb_array_elements(p_envelope->'contributions') c
  WHERE c->>'semantic_type' IN ('structural.predicate_member','structural.predicate_frame',
   'structural.predicate_cue','structural.predicate_reading','structural.predicate_qualification');
  PERFORM ops.validate_source_predicates(
   t,v,predicate_population,table_config||jsonb_build_object('_predicate_operations',operation_map,
    '_predicate_version','6'));
 END IF;
 IF p_envelope->>'method'='structure.scoped_relations' AND p_envelope->>'operation_version'='17' THEN
  PERFORM ops.validate_primary_source_navigation(t,v,table_config,p_envelope->'contributions',operation_map);
 END IF;
 IF p_envelope->>'method'='structure.scoped_relations'
  AND table_config->>'inputs' IS NOT NULL THEN
  PERFORM ops.validate_scope_inheritance(p_envelope->'contributions',operation_map);
 END IF;
 IF p_envelope->>'method'='structure.scoped_relations'
  AND (COALESCE(table_config->'classification_refs','[]')<>'[]'::jsonb
   OR data.record_source_json(p_envelope->'parse_detail') ? 'clause_model_concordance') THEN
  IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(table_config->'classification_refs','[]')) ref
    WHERE NOT table_config->'inputs'->'dependencies' ? (ref->>'product_id'))
   OR COALESCE(data.record_source_json(p_envelope->'parse_detail')->'clause_model_concordance','[]') IS DISTINCT FROM
    ops.clause_model_concordance(COALESCE(table_config->'classification_refs','[]'),v.id,p_envelope->'contributions') THEN
   RAISE EXCEPTION 'clause model concordance differs from authenticated exact focus' USING ERRCODE='23514'; END IF;
 END IF;
 PERFORM ops.validate_source_anchor_coordinates(t.run_id,t.unit_id,p_envelope->>'source',anchors);
 IF table_mode='correspondence' THEN
  table_expected:=ops.table_correspondence_requests(
   v,p_envelope->'contributions',(table_config->>'interpretation_weight_scale')::numeric,ops.primary_characterization_layers(t,v,table_config));
  SELECT coalesce(jsonb_agg(jsonb_build_object('scope_id',o->'operation_key','question',o->'question',
   'contribution_ids',local_report->'contribution_ids','dependencies',local_report->'dependencies',
   'reason',CASE WHEN local_report->>'outcome'='not_run' THEN local_report->'reason' END,
   'request',data.record_source_json(local_report->'request'))
   ORDER BY (o->>'operation_key') COLLATE "C"),'[]')
  INTO table_actual FROM jsonb_array_elements(p_envelope->'contribution_operations') o
  CROSS JOIN LATERAL (SELECT o->'local_interpretation' AS local_report) l WHERE o ? 'local_interpretation';
  IF table_actual IS DISTINCT FROM (SELECT coalesce(jsonb_agg(e ORDER BY (e->>'scope_id') COLLATE "C"),'[]')
    FROM jsonb_array_elements(table_expected) e) THEN
   RAISE EXCEPTION 'table correspondence differs from authoritative source-conditioned request'
    USING ERRCODE='23514';
  END IF;
 END IF;
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
 INSERT INTO kb.terminology_interpretation_field(task_id,contribution_id,source_run_id,source_cut_id,source_release_id,realization_id,data_revision,record_id,interpretation_id,vocabulary_release,metadata_digest,outcome,field,selected_value,meaning,mapping_predicate,mapping_direction)
 SELECT p_task,c->>'contribution_id',(p->'source_record'->>'run_id')::bigint,(p->'source_record'->>'cut_id')::bigint,p->'source_record'->>'release_id',p->'source_record'->>'realization_id',(p->'source_record'->>'data_revision')::bigint,p->'source_record'->>'record_id',p->'source_record'->>'interpretation_id',p->>'vocabulary_release',p->>'metadata_digest',d->>'outcome',d->>'field',d->>'selected_value',
 (SELECT m->>'meaning' FROM jsonb_array_elements(d->'candidates') m WHERE m->>'value'=d->>'selected_value'),d->>'mapping_predicate',d->>'mapping_direction'
 FROM jsonb_array_elements(p_envelope->'contributions') c,
 LATERAL (SELECT data.record_source_json(c->'value') AS p) pp,
 LATERAL jsonb_array_elements(p->'decisions') d WHERE c->>'semantic_type'='terminology.interpretation';
 INSERT INTO kb.measurement_interpretation(task_id,contribution_id,source_run_id,source_cut_id,source_release_id,realization_id,data_revision,record_id,interpretation_id,vocabulary_release,metadata_digest,outcome,unit,quantity_kind,basis_status,basis)
 SELECT p_task,c->>'contribution_id',(p->'source_record'->>'run_id')::bigint,(p->'source_record'->>'cut_id')::bigint,p->'source_record'->>'release_id',p->'source_record'->>'realization_id',(p->'source_record'->>'data_revision')::bigint,p->'source_record'->>'record_id',p->'source_record'->>'interpretation_id',p->>'vocabulary_release',p->>'metadata_digest',p->>'outcome',p->>'unit',p->>'quantity_kind',p->>'basis_status',p->>'basis'
 FROM jsonb_array_elements(p_envelope->'contributions') c,
 LATERAL (SELECT data.record_source_json(c->'value') AS p) pp WHERE c->>'semantic_type'='measurement.interpretation';
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
