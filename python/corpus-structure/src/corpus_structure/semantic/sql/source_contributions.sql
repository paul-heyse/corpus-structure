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

CREATE OR REPLACE FUNCTION ops.validate_source_table_note_scope(p_view kb.source_view,p_rows jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE link_ jsonb; subject_ jsonb; note_ jsonb; table_ jsonb; original_note jsonb; note_text text;
 cell_pointer text[]; cell_ jsonb; named text[]; eligible_count integer; matching_count integer;
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
  note_text:=btrim(original_note->>'text',E' \t\n\r');
  IF note_text ~* '^(?:This note applies to )?all rows[.!]?$' THEN CONTINUE; END IF;
  named:=regexp_match(note_text,'^(?:Only )?the (.+?) (row|column|band)\y','i');
  IF named IS NULL THEN
   RAISE EXCEPTION 'table association alone does not establish cell note scope' USING ERRCODE='23514';
  END IF;
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
REVOKE ALL ON FUNCTION ops.validate_source_table_note_scope(kb.source_view,jsonb) FROM PUBLIC;

-- A projected extent must reconstruct the exact ordered physical anchors and
-- contain exactly the submitted retained tokens, apart from inter-token whitespace.
CREATE OR REPLACE FUNCTION ops.predicate_role_anchor_match(
 projection jsonb,extents jsonb,anchors jsonb,tokens jsonb,indices jsonb,lo bigint,hi bigint)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH extents_ AS (
  SELECT (e->>'start')::bigint AS a,(e->>'end')::bigint AS b,n,
   lag((e->>'end')::bigint) OVER(ORDER BY n) AS previous_end
  FROM jsonb_array_elements(extents) WITH ORDINALITY x(e,n)
 ), pieces AS (
  SELECT p,(p->>'start')::bigint AS a,(p->>'end')::bigint AS b,n
  FROM jsonb_array_elements(projection->'pieces') WITH ORDINALITY x(p,n)
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
   substring(projection->>'text' FROM (r.previous_end+1)::integer FOR (r.a-r.previous_end)::integer)
    ~ '[^[:space:]]'
 )
 AND (SELECT physical.anchors FROM physical) IS NOT DISTINCT FROM (
  SELECT jsonb_agg(jsonb_build_array(a->>'pointer',a->'start',a->'end') ORDER BY n)
  FROM jsonb_array_elements(anchors) WITH ORDINALITY x(a,n)
  WHERE a->>'space'='native' AND a->>'precision'='exact'
 );
$$;
REVOKE ALL ON FUNCTION ops.predicate_role_anchor_match(jsonb,jsonb,jsonb,jsonb,jsonb,bigint,bigint) FROM PUBLIC;

-- Independently check the declared marker/host relationship against the retained
-- dependency columns. Shared fronted conditions and modals have one direct source
-- owner and a compatible explicit conjunct.
CREATE OR REPLACE FUNCTION ops.predicate_cue_host_matches(
 projection jsonb,tokens jsonb,cue jsonb,host integer)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE origin integer:=(cue->>'governing_token')::integer;
 subordinate integer:=(cue->>'subordinate_token')::integer;
 marker_index integer:=(cue->'marker_token_indices'->>0)::integer;
 marker jsonb; root jsonb; child jsonb; target jsonb; kind_ text:=cue->>'cue_kind';
BEGIN
 marker:=tokens->marker_index; root:=tokens->origin; child:=tokens->subordinate; target:=tokens->host;
 IF marker IS NULL OR root IS NULL OR target IS NULL
  OR marker->>'sentence' IS NULL OR root->'sentence' IS DISTINCT FROM marker->'sentence'
  OR target->'sentence' IS DISTINCT FROM root->'sentence'
  OR (child IS NOT NULL AND child->'sentence' IS DISTINCT FROM root->'sentence') THEN
  RETURN false;
 END IF;
 IF kind_ IN ('condition','exception','order') THEN
  IF child IS NOT NULL THEN
   IF NOT COALESCE(
    (marker->>'dependency'='mark' AND marker->'head'=to_jsonb(subordinate)
     AND child->>'dependency'='advcl' AND child->'head'=to_jsonb(origin))
    OR (marker->>'dependency' IN ('prep','advmod') AND marker->'head'=to_jsonb(origin)
     AND child->>'dependency' IN ('pcomp','advcl') AND child->'head'=to_jsonb(marker_index)),
    false) THEN RETURN false; END IF;
  ELSIF NOT COALESCE(kind_='exception' AND left(cue->>'variant',8)='nominal_'
   AND marker->>'dependency'='prep' AND marker->'head'=to_jsonb(origin),false) THEN RETURN false;
  END IF;
 ELSIF kind_ IN ('modality','negation') THEN
  IF marker->'head' IS DISTINCT FROM to_jsonb(origin) OR NOT COALESCE(
   (kind_='negation' AND marker->>'dependency'='neg')
   OR (kind_='modality' AND marker->>'tag'='MD' AND marker->>'dependency' IN ('aux','auxpass','aux:pass','cop')),
   false) THEN RETURN false; END IF;
 ELSIF kind_ IN ('attribution','assumption') THEN
  IF cue->>'variant' IN ('reported_assumption','reported_complement') THEN
   RETURN COALESCE(marker_index=origin AND child->>'dependency'='ccomp'
    AND child->'head'=to_jsonb(origin) AND host=(CASE WHEN kind_='assumption' THEN origin ELSE subordinate END),false);
  END IF;
  RETURN COALESCE(kind_='attribution' AND cue->>'variant'='according_to'
   AND marker->>'dependency'='prep' AND marker->'head'=to_jsonb(origin) AND origin=host,false);
 ELSE
  RETURN false;
 END IF;
 IF host=origin THEN RETURN true; END IF;
 RETURN COALESCE(
  (kind_='modality' OR (kind_='condition' AND (cue->'token_indices'->>-1)::integer<origin))
  AND target->>'dependency'='conj' AND target->'head'=to_jsonb(origin)
  AND (SELECT array_agg(DISTINCT lower(substring(projection->>'text'
     FROM (t->>'start')::integer+1 FOR (t->>'end')::integer-(t->>'start')::integer)))
   FROM jsonb_array_elements(tokens) WITH ORDINALITY x(t,n)
   WHERE n-1>least(host,origin) AND n-1<greatest(host,origin)
    AND t->>'dependency'='cc' AND (t->>'head')::integer IN (host,origin))=ARRAY['and']::text[]
  AND NOT EXISTS(
   SELECT FROM jsonb_array_elements(tokens) t WHERE t->'head'=to_jsonb(host)
   AND t->>'dependency' IN ('nsubj','csubj','nsubjpass','csubjpass','nsubj:pass','csubj:pass',
    'aux','auxpass','aux:pass','cop')
  ),false);
END $$;
REVOKE ALL ON FUNCTION ops.predicate_cue_host_matches(jsonb,jsonb,jsonb,integer) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.predicate_token_texts(projection jsonb,tokens jsonb)
RETURNS text[] LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT array_agg(substring(projection->>'text' FROM (t->>'start')::integer+1
  FOR (t->>'end')::integer-(t->>'start')::integer) ORDER BY n)
 FROM jsonb_array_elements(tokens) WITH ORDINALITY x(t,n);
$$;
REVOKE ALL ON FUNCTION ops.predicate_token_texts(jsonb,jsonb) FROM PUBLIC;

-- Reconstruct the accepted bounded local recipes from the retained source columns.
-- The submitted candidate list alone is never a witness for one of these edges.
CREATE OR REPLACE FUNCTION ops.predicate_cue_recipe_matches(
 projection jsonb,annotation jsonb,cue jsonb,host integer)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE tokens jsonb:=annotation->'tokens'; words text[]; folded text[];
 marker integer:=(cue->'marker_token_indices'->>0)::integer;
 origin integer:=(cue->>'governing_token')::integer;
 subordinate integer:=(cue->>'subordinate_token')::integer;
 first_ integer:=(cue->'token_indices'->>0)::integer;
 last_ integer:=(cue->'token_indices'->>-1)::integer;
 kind_ text:=cue->>'cue_kind'; variant text:=cue->>'variant';
 target jsonb:=tokens->host; sentence jsonb:=target->'sentence';
 base integer:=marker; first_pred integer; conjunction integer; conjunction_head integer;
 start_sentence integer; then_ integer; lo integer; hi integer;
 edges integer[][]; labels text[];
BEGIN
 IF marker IS NULL OR origin IS NULL OR subordinate IS NULL OR first_ IS NULL OR last_ IS NULL
  OR least(marker,origin,subordinate,first_,host)<0 OR last_>=jsonb_array_length(tokens)
  OR target IS NULL OR sentence IS NULL OR sentence='null'
  OR cue->'marker_token_indices' IS DISTINCT FROM jsonb_build_array(marker)
  OR jsonb_array_length(cue->'extents')<>1
  OR cue->'token_indices' IS DISTINCT FROM (SELECT jsonb_agg(i ORDER BY i) FROM generate_series(first_,last_) i)
 THEN RETURN false; END IF;

 words:=ops.predicate_token_texts(projection,tokens);
 SELECT array_agg(lower(word) ORDER BY n) INTO folded FROM unnest(words) WITH ORDINALITY x(word,n);
 lo:=first_;
 hi:=greatest(last_,host);

 IF variant='event_compound_then' THEN
  first_pred:=(tokens->marker->>'head')::integer;
  then_:=last_+2;
  conjunction:=subordinate-2;
  conjunction_head:=(tokens->conjunction->>'head')::integer;
  SELECT min(n-1) INTO start_sentence FROM jsonb_array_elements(tokens) WITH ORDINALITY x(t,n)
   WHERE t->'sentence'=sentence;
  IF NOT coalesce(kind_='condition' AND host=origin AND target->>'dependency'='ROOT'
   AND first_=marker AND marker+2<=first_pred AND first_pred<conjunction AND conjunction<last_
   AND subordinate<=last_ AND then_<host AND folded[marker+1]='if' AND folded[conjunction+1]='and'
   AND tokens->first_pred->>'lemma'='be' AND tokens->subordinate->>'lemma'='be'
   AND words[marker+2]<>words[subordinate]
   AND (SELECT count(*) FROM jsonb_array_elements(tokens) WITH ORDINALITY x(t,n)
    WHERE t->'sentence'=sentence AND folded[n::integer]='then')=1
   AND folded[last_+2:last_+3]=ARRAY[',','then']
   AND (marker=start_sentence OR (marker=start_sentence+2 AND folded[start_sentence+1]='definition'
    AND words[start_sentence+2] ~ '^[[:digit:]]+([.][[:digit:]]+)*$'))
   AND (tokens->(subordinate-1)->>'dependency'='nsubj'
    AND tokens->(subordinate-1)->'head'=to_jsonb(subordinate)
    OR tokens->(subordinate-1)->>'dependency'='conj'
    AND tokens->(subordinate-1)->'head'=to_jsonb(conjunction_head)
    AND tokens->conjunction_head->>'dependency'='attr'
    AND tokens->conjunction_head->'head'=to_jsonb(first_pred))
   AND (conjunction_head IN (first_pred,subordinate) OR (tokens->conjunction_head->>'dependency'='attr'
    AND tokens->conjunction_head->'head'=to_jsonb(first_pred)))
   AND (SELECT count(*) FROM generate_series(first_pred+1,subordinate-1) i
    WHERE folded[i+1]='and' AND tokens->i->>'dependency'='cc')=1,false)
  THEN RETURN false; END IF;
  edges:=ARRAY[[0,first_pred-base],[1,first_pred-base],[first_pred-base,subordinate-base],
   [subordinate-base,host-base],[conjunction-base,conjunction_head-base],[then_-base,host-base]];
  labels:=ARRAY['mark','nsubj','advcl','ccomp','cc','advmod'];

 ELSIF variant='adjacent_variance_premise' THEN
  IF NOT coalesce(kind_='assumption' AND annotation->>'kind'='list_item' AND first_=marker
   AND last_=marker+9 AND origin=marker AND subordinate=marker+4 AND host=marker+18
   AND folded[marker+1:marker+20]=ARRAY['let',lower(words[marker+2]),'and',lower(words[marker+4]),
    'be','random','variables','with','positive','variance','.','the','correlation','of',
    lower(words[marker+2]),'and',lower(words[marker+4]),'is','defined','as'],false)
  THEN
   RETURN false;
  END IF;
  IF NOT coalesce(words[marker+2] ~ '^[[:alpha:]]$' AND words[marker+4] ~ '^[[:alpha:]]$'
   AND words[marker+2]<>words[marker+4]
   AND words[marker+2]=words[marker+15] AND words[marker+4]=words[marker+17]
   AND target->>'dependency'='ROOT' AND tokens->marker->>'dependency'='ROOT'
   AND (sentence#>>'{}')::integer=(tokens->marker->>'sentence')::integer+1
   AND (marker=0 OR tokens->(marker-1)->'sentence' IS DISTINCT FROM tokens->marker->'sentence'
    OR (rtrim(words[marker],'.') ~ '^[[:digit:]]+$' AND (marker=1 OR tokens->(marker-2)->'sentence'
     IS DISTINCT FROM tokens->marker->'sentence')))
   AND NOT EXISTS(SELECT FROM generate_series(marker,marker+10) i
    WHERE tokens->i->'sentence' IS DISTINCT FROM tokens->marker->'sentence')
   AND NOT EXISTS(SELECT FROM generate_series(marker+11,marker+19) i
    WHERE tokens->i->'sentence' IS DISTINCT FROM sentence),false)
  THEN RETURN false; END IF;
  hi:=marker+19;
  edges:=ARRAY[[4,0],[1,4],[3,1],[2,1],[6,4],[7,6],[9,7],[8,9],[12,18],[13,12],
   [14,13],[16,14],[15,14],[17,18]];
  labels:=ARRAY['ccomp','nsubj','conj','cc','attr','prep','pobj','amod','nsubjpass','prep',
   'pobj','conj','cc','auxpass'];

 ELSIF variant='nominal_parameter_pair' THEN
  IF NOT coalesce(kind_='parameterization' AND first_=marker AND marker>0 AND last_=marker+4
   AND origin=host AND host=marker+6 AND subordinate=marker-1
   AND tokens->subordinate->>'pos' IN ('NOUN','PROPN')
   AND folded[marker+1:marker+10]=ARRAY['with','parameters',lower(words[marker+3]),
    'and',lower(words[marker+5]),'is','defined','as','follows',':']
   AND words[marker+3] ~ '^[[:alpha:]]$' AND words[marker+5] ~ '^[[:alpha:]]$'
   AND words[marker+3]<>words[marker+5],false)
  THEN RETURN false; END IF;
  lo:=subordinate; hi:=marker+9;
  edges:=ARRAY[[0,-1],[5,6],[7,8],[8,6],[9,6]];
  labels:=ARRAY['prep','auxpass','mark','advcl','punct'];
  IF target->>'dependency'='conj' AND tokens->subordinate->>'dependency'='ROOT' THEN
   edges:=edges||ARRAY[[6,-1],[1,2],[2,0],[3,-1],[4,6]];
   labels:=labels||ARRAY['conj','compound','pobj','cc','nsubjpass'];
  ELSIF target->>'dependency'='ROOT' THEN
   edges:=edges||ARRAY[[-1,6],[1,0],[2,1],[3,2],[4,2]];
   labels:=labels||ARRAY['nsubjpass','pobj','appos','cc','conj'];
  ELSE RETURN false;
  END IF;

 ELSIF variant='customer_population_inclusion' THEN
  IF NOT coalesce(kind_='population_inclusion' AND origin=host AND marker=host+8
   AND first_=marker AND last_=host+17 AND subordinate=host+6
   AND folded[host+1:host+18]=ARRAY['counting','the','waiting','time','of','all','customers',',',
    'even','those','that','do','not','have','to','wait','at','all']
   AND (tokens->(last_+1)->'sentence' IS DISTINCT FROM sentence OR words[last_+2]='.')
   AND (tokens->(host+9)->>'dependency'='appos' AND (
    tokens->(host+9)->'head'=to_jsonb(subordinate)
    OR tokens->(host+9)->'head'=to_jsonb(host+3)
    OR (tokens->((tokens->(host+9)->>'head')::integer)->>'dependency'='nsubj'
     AND tokens->((tokens->(host+9)->>'head')::integer)->'head'=to_jsonb(host))
   )),false)
  THEN RETURN false; END IF;
  base:=host; lo:=host;
  edges:=ARRAY[[3,0],[4,3],[6,4],[5,6],[8,9],[10,13],[11,13],[12,13],[13,9],[14,15],[15,13]];
  labels:=ARRAY['dobj','prep','pobj','det','advmod','nsubj','aux','neg','relcl','aux','xcomp'];
 ELSE
  RETURN false;
 END IF;

 RETURN hi<jsonb_array_length(tokens)
  AND jsonb_array_length(tokens->marker->'piece_indices')=1
  AND NOT EXISTS(SELECT FROM generate_series(lo,hi) i
   WHERE tokens->i->'piece_indices' IS DISTINCT FROM tokens->marker->'piece_indices'
    OR (variant<>'adjacent_variance_premise' AND tokens->i->'sentence' IS DISTINCT FROM sentence))
  AND NOT EXISTS(SELECT FROM jsonb_array_elements(tokens) WITH ORDINALITY x(t,n)
   WHERE t->'sentence' IN (sentence,tokens->marker->'sentence')
    AND words[n::integer] IN ('"',chr(39),chr(96),'«','»','‘','’','‚','‛','“','”','„','‟',
     '‹','›','❮','❯',repeat(chr(39),2),repeat(chr(96),2)))
  AND NOT EXISTS(SELECT FROM generate_subscripts(labels,1) i
   WHERE tokens->(base+edges[i][1])->>'dependency' IS DISTINCT FROM labels[i]
    OR tokens->(base+edges[i][1])->'head' IS DISTINCT FROM to_jsonb(base+edges[i][2]));
END $$;
REVOKE ALL ON FUNCTION ops.predicate_cue_recipe_matches(jsonb,jsonb,jsonb,integer) FROM PUBLIC;

-- Cross-block witnesses use selected native tree membership and independently
-- located annotation endpoints. A matching text fragment cannot supply custody.
CREATE OR REPLACE FUNCTION ops.predicate_cross_block_host_matches(
 p_view kb.source_view,p_population jsonb,cue jsonb,host jsonb,rel jsonb,
 source_annotation jsonb,host_annotation jsonb,selection jsonb)
RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE projection jsonb:=p_view.projection; witness jsonb:=rel->'host_witness';
 scope_kind text:=witness->>'kind';
 source_node text:=source_annotation->>'block_id'; host_node text:=host_annotation->>'block_id';
 source_native jsonb; host_native jsonb; parent_native jsonb; group_native jsonb;
 shared_parent text; list_group text:=witness->>'list_group'; display_node text;
 source_pos integer; host_pos integer; between_ text;
 native_siblings text[]; sibling_pos integer;
 source_tokens jsonb:=source_annotation->'tokens'; host_tokens jsonb:=host_annotation->'tokens';
 source_words text[]; folded text[]; host_words text[];
 first_ integer:=(cue->'token_indices'->>0)::integer;
 last_ integer:=(cue->'token_indices'->>-1)::integer;
 marker integer:=(cue->'marker_token_indices'->>0)::integer;
 host_index integer:=(host->'component'->>'predicate_token')::integer;
 start_sentence integer; end_sentence integer; note_sentence jsonb; symbol text;
 parameterization jsonb; parameter_cue jsonb; parameter_token integer;
BEGIN
 IF NOT coalesce(
  selection IS NOT NULL AND source_node<>host_node AND source_node IS NOT NULL AND host_node IS NOT NULL
  AND cue->>'cue_kind'='assumption' AND cue->>'host_state'='located'
  AND NOT (cue ?| ARRAY['governing_token','subordinate_token'])
  AND coalesce(jsonb_array_length(cue->'candidate_tokens'),0)=0
  AND cue->'cross_block_hosts' ? (host->>'contribution_id')
  AND rel->'dependencies' ? (host->'component'->>'annotation')
  AND rel->'dependencies' ? (cue->>'annotation')
  AND projection->'items' ? source_node AND projection->'items' ? host_node
  AND cue->'marker_token_indices'=jsonb_build_array(marker)
  AND jsonb_array_length(cue->'extents')=1
  AND cue->'token_indices'=(SELECT jsonb_agg(i ORDER BY i) FROM generate_series(first_,last_) i),
  false) THEN RETURN false; END IF;

 WITH pieces AS (
  SELECT p,row_number() OVER(ORDER BY n) AS position
  FROM jsonb_array_elements(projection->'pieces') WITH ORDINALITY x(p,n)
  WHERE p->>'kind'='native_text'
 ), source_ AS (
  SELECT position FROM pieces WHERE p->>'item_ref'=source_node
   AND coalesce(p->>'source_field','text')='text' AND NOT p ? 'cell_index'
   AND p->'start'=source_annotation->'block_start' AND p->'end'=source_annotation->'block_end'
   AND (p->>'start')::bigint>=(selection->>'start')::bigint
   AND (p->>'end')::bigint<=(selection->>'end')::bigint
 ), host_ AS (
  SELECT position FROM pieces WHERE p->>'item_ref'=host_node
   AND coalesce(p->>'source_field','text')='text' AND NOT p ? 'cell_index'
   AND p->'start'=host_annotation->'block_start' AND p->'end'=host_annotation->'block_end'
   AND (p->>'start')::bigint>=(selection->>'start')::bigint
   AND (p->>'end')::bigint<=(selection->>'end')::bigint
 )
 SELECT source_.position,host_.position,pieces.p->>'item_ref' INTO STRICT source_pos,host_pos,between_
 FROM source_ CROSS JOIN host_ LEFT JOIN pieces ON pieces.position=host_.position+1;

 SELECT native_json INTO STRICT source_native FROM ops.read_pdf_published_items(
  p_view.native_task_id,p_view.native_product_key,p_view.native_content_digest,ARRAY[source_node]);
 SELECT native_json INTO STRICT host_native FROM ops.read_pdf_published_items(
  p_view.native_task_id,p_view.native_product_key,p_view.native_content_digest,ARRAY[host_node]);
 shared_parent:=source_native->'parent'->>'$ref';
 IF NOT coalesce(shared_parent IS NOT NULL AND source_native->>'label'='text'
  AND source_native->>'content_layer'='body' AND host_native->>'content_layer'='body'
  AND ((projection->'items' ? shared_parent) OR (projection->'ancestors' ? shared_parent)),false)
 THEN RETURN false; END IF;
 SELECT native_json INTO STRICT parent_native FROM ops.read_pdf_published_items(
  p_view.native_task_id,p_view.native_product_key,p_view.native_content_digest,ARRAY[shared_parent]);
 SELECT array_agg(child->>'$ref' ORDER BY n) INTO native_siblings
 FROM jsonb_array_elements(parent_native->'children') WITH ORDINALITY x(child,n);
 source_words:=ops.predicate_token_texts(projection,source_tokens);
 SELECT array_agg(lower(word) ORDER BY n) INTO folded
 FROM unnest(source_words) WITH ORDINALITY x(word,n);

 IF scope_kind='list_intro' THEN
  sibling_pos:=array_position(native_siblings,source_node);
  IF NOT coalesce(cue->>'variant'='list_assumption' AND witness=jsonb_build_object('kind',scope_kind,'list_group',list_group)
   AND projection->'items' ? list_group AND native_siblings[sibling_pos+1]=list_group AND source_pos<host_pos
   AND cardinality(array_positions(native_siblings,source_node))=1
   AND cardinality(array_positions(native_siblings,list_group))=1
   AND host_native->>'label'='list_item' AND host_native->'parent'->>'$ref'=list_group
   AND host_annotation->>'kind'='list_item' AND host_tokens->host_index->>'dependency'='ROOT'
   AND host_tokens->host_index->>'pos' IN ('VERB','AUX')
   AND (SELECT count(*) FROM jsonb_array_elements(host_tokens) t
    WHERE t->>'dependency'='ROOT' AND t->>'pos' IN ('VERB','AUX'))=1
   AND marker=6 AND first_=marker AND last_=jsonb_array_length(source_tokens)-2 AND last_>marker+1
   AND folded[1:8]=ARRAY['for','each','of','the','following',',','assume','that']
   AND source_words[last_+2]=':' AND source_tokens->marker->>'dependency'='ROOT'
   AND (SELECT count(*) FROM generate_series(marker+2,last_) i
    WHERE source_tokens->i->>'dependency'='ccomp' AND source_tokens->i->'head'=to_jsonb(marker))=1
   AND (SELECT count(DISTINCT t->'sentence') FROM jsonb_array_elements(source_tokens) t)=1,
   false) THEN RETURN false; END IF;
  SELECT native_json INTO STRICT group_native FROM ops.read_pdf_published_items(
   p_view.native_task_id,p_view.native_product_key,p_view.native_content_digest,ARRAY[list_group]);
  RETURN coalesce(group_native->>'label'='list' AND group_native->>'content_layer'='body'
   AND group_native->'parent'->>'$ref'=shared_parent
   AND (SELECT count(*) FROM jsonb_array_elements(group_native->'children') n WHERE n->>'$ref'=host_node)=1
   AND (SELECT p->>'item_ref' FROM jsonb_array_elements(projection->'pieces') WITH ORDINALITY x(p,n)
    WHERE p->>'kind'='native_text' ORDER BY n OFFSET source_pos LIMIT 1)
    =group_native->'children'->0->>'$ref',false);
 END IF;

 IF scope_kind<>'parameter_note' OR scope_kind IS NULL THEN RETURN false; END IF;
 sibling_pos:=array_position(native_siblings,host_node);
 display_node:=native_siblings[sibling_pos+1];
 IF NOT coalesce(cue->>'variant'='parameter_positive'
  AND witness=jsonb_build_object('kind',scope_kind,'parameterization',witness->>'parameterization')
  AND host_native->>'label'='text' AND host_native->'parent'->>'$ref'=shared_parent
  AND native_siblings[sibling_pos+2]=source_node AND host_pos+2=source_pos
  AND cardinality(array_positions(native_siblings,source_node))=1
  AND cardinality(array_positions(native_siblings,host_node))=1
  AND display_node=between_ AND projection->'items' ? display_node
  AND EXISTS(SELECT FROM ops.read_pdf_published_items(
   p_view.native_task_id,p_view.native_product_key,p_view.native_content_digest,ARRAY[display_node])
   WHERE native_json->>'label'='formula' AND native_json->>'content_layer'='body'
    AND native_json->'parent'->>'$ref'=shared_parent)
  AND marker=first_+2 AND last_=first_+5
  AND folded[first_-1:last_+2]=ARRAY['and','thus','it','is','assumed','to','be','positive','.']
  AND rel->'dependencies' ? (witness->>'parameterization'),false) THEN RETURN false; END IF;

 note_sentence:=source_tokens->marker->'sentence';
 SELECT min(n-1),max(n-1) INTO start_sentence,end_sentence
 FROM jsonb_array_elements(source_tokens) WITH ORDINALITY x(t,n) WHERE t->'sentence'=note_sentence;
 symbol:=source_words[start_sentence+3];
 IF NOT coalesce(start_sentence+2<first_-2 AND end_sentence=last_+1
  AND folded[start_sentence+1:start_sentence+2]=ARRAY['the','parameter']
  AND symbol ~ '^[[:alpha:]]$'
  AND source_tokens->first_->>'dependency'='nsubjpass' AND source_tokens->first_->'head'=to_jsonb(marker)
  AND source_tokens->(first_+1)->>'dependency'='auxpass' AND source_tokens->(first_+1)->'head'=to_jsonb(marker)
  AND source_tokens->(first_+3)->>'dependency'='aux' AND source_tokens->(first_+3)->'head'=to_jsonb(first_+4)
  AND source_tokens->(first_+4)->>'dependency'='xcomp' AND source_tokens->(first_+4)->'head'=to_jsonb(marker)
  AND source_tokens->last_->>'dependency'='acomp' AND source_tokens->last_->'head'=to_jsonb(first_+4)
  AND (SELECT count(*) FROM generate_series(start_sentence,end_sentence-2) i
    WHERE folded[i+1:i+2]=ARRAY['the','parameter'])=1,false)
 THEN RETURN false; END IF;

 parameterization:=p_population->(witness->>'parameterization')->'component';
 parameter_cue:=p_population->(parameterization->>'qualifier_contribution_id')->'component';
 parameter_token:=(parameter_cue->'token_indices'->>4)::integer;
 host_words:=ops.predicate_token_texts(projection,host_tokens);
 RETURN coalesce(parameterization->>'kind'='predicate_qualifier'
  AND parameterization->>'qualifier_kind'='parameterization'
  AND parameterization->>'host_contribution_id'=host->>'contribution_id'
  AND parameter_cue->>'variant'='nominal_parameter_pair'
  AND parameter_cue->>'annotation'=host->'component'->>'annotation'
  AND host_words[parameter_token+1]=symbol,false);
EXCEPTION WHEN no_data_found OR too_many_rows THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION ops.predicate_cross_block_host_matches(
 kb.source_view,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_source_predicates(
 p_task ops.task,p_view kb.source_view,p_population jsonb,p_config jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE original jsonb; original_id text; selected_run bigint:=p_task.run_id; selected_cut bigint;
 p_operations jsonb:=p_config->'_predicate_operations';
 predicate_version text:=p_config->>'_predicate_version';
 local_recipes constant text[]:=ARRAY['event_compound_then','adjacent_variance_premise',
  'nominal_parameter_pair','customer_population_inclusion'];
 cross_recipes constant text[]:=ARRAY['list_assumption','parameter_positive'];
 body jsonb; origin_task bigint; annotation_map jsonb; evidence jsonb; c jsonb; part jsonb; m jsonb;
 annotation jsonb; tokens jsonb; selection jsonb; members jsonb; predicate jsonb; focus jsonb;
 qualification_schema json; condition_schema json;
 cue jsonb; host jsonb; interpretation jsonb; qualified jsonb; condition_ jsonb; lo bigint; hi bigint; kind_ text;
 cue_component jsonb; host_component jsonb; host_annotation jsonb; recipe text; matches_host boolean;
BEGIN
 IF p_config->'inputs' IS NOT NULL AND p_config->'inputs'<>'null'::jsonb THEN
  SELECT s INTO STRICT original FROM jsonb_array_elements(p_config->'inputs'->'sources') s
   WHERE (s->>'source_view_id')::bigint=p_view.id;
  PERFORM ops.validate_structural_source(original);
  original_id:=encode(sha256(convert_to(data.canonical_json(original),'UTF8')),'hex');
  selected_run:=(original->>'run_id')::bigint;
  selected_cut:=(original->>'cut_id')::bigint;
 END IF;
 SELECT r.body,r.task_id INTO STRICT body,origin_task
 FROM ops.task selected
 JOIN ops.task_result r ON r.task_id=coalesce(selected.reused_task_id,selected.id)
 JOIN ops.method_config cfg ON cfg.id=selected.method_config_id
 JOIN ops.method method ON method.id=cfg.method_id
 WHERE selected.run_id=selected_run AND selected.unit_type='source_view' AND selected.unit_id=p_view.id
  AND selected.status IN ('done','reused','failed') AND method.name='extract.m1_annotations' AND method.version='2'
  AND r.body->>'source'=p_view.key
  AND (selected_cut IS NULL OR EXISTS(
   SELECT FROM ops.cut_task cut WHERE cut.cut_id=selected_cut AND cut.task_id=selected.id
    AND cut.origin_task_id=r.task_id
  ));
 IF EXISTS(SELECT FROM jsonb_each(p_operations) o WHERE
  o.value->>'question' IN ('source_predicate_frames','source_predicate_interpretation')
  AND ((o.value->>'annotation_origin_task_id')::bigint IS DISTINCT FROM origin_task
   OR o.value->>'operation_version' IS DISTINCT FROM predicate_version)) THEN
  RAISE EXCEPTION 'predicate operation differs from exact annotation producer' USING ERRCODE='23514';
 END IF;
 SELECT jsonb_object_agg('annotation:'||(a->>'dependency_digest'),a) INTO annotation_map
 FROM jsonb_array_elements(data.record_source_json(body->'parse_detail')->'annotations') a;
 SELECT convert_from(content,'UTF8')::json INTO qualification_schema
 FROM sem.artifact WHERE release_id=p_task.release_id AND artifact_name='json_schema/Qualification';
 SELECT convert_from(content,'UTF8')::json INTO condition_schema
 FROM sem.artifact WHERE release_id=p_task.release_id AND artifact_name='json_schema/Condition';
 FOR evidence IN SELECT value FROM jsonb_each(p_population)
  WHERE value->'component'->>'kind' IN ('predicate_frame','predicate_reading','predicate_cue','predicate_qualifier')
 LOOP
  c:=evidence->'component'; kind_:=c->>'kind';
  IF c->>'question_version' IS DISTINCT FROM predicate_version
   OR c->>'question' IS DISTINCT FROM (CASE WHEN kind_ IN ('predicate_frame','predicate_cue')
    THEN 'source_predicate_frames' ELSE 'source_predicate_interpretation' END)
   OR (predicate_version='2' AND (
    c ?| ARRAY['cross_block_hosts','host_witness']
    OR c->>'variant'=ANY(local_recipes||cross_recipes) OR c->>'cue_kind'='population_inclusion'))
  THEN RAISE EXCEPTION 'predicate evidence differs from its released recipe version' USING ERRCODE='23514'; END IF;
  IF kind_ IN ('predicate_frame','predicate_cue') THEN
   annotation:=annotation_map->(c->>'annotation');
   IF annotation IS NULL OR annotation->>'block_id' IS DISTINCT FROM c->>'block'
    OR NOT (c->'dependencies' ? (c->>'annotation')) THEN
    RAISE EXCEPTION 'predicate evidence lacks the exact retained annotation block' USING ERRCODE='23514';
   END IF;
   tokens:=annotation->'tokens';
   lo:=(annotation->>'block_start')::bigint; hi:=(annotation->>'block_end')::bigint;
   IF selected_cut IS NOT NULL THEN
    SELECT p INTO STRICT selection FROM jsonb_array_elements(p_config->'inputs'->'passages') p
     WHERE p->>'source_ref'=original_id AND p->>'passage_id'=c->>'scope'
      AND p->>'effective_version' IS NOT DISTINCT FROM c->>'effective_version';
    lo:=greatest(lo,(selection->>'start')::bigint); hi:=least(hi,(selection->>'end')::bigint);
   ELSIF c->>'scope' IS DISTINCT FROM c->>'block' OR c ? 'effective_version' THEN
    RAISE EXCEPTION 'predicate evidence is outside its retained block scope' USING ERRCODE='23514';
   END IF;
  END IF;
  IF kind_='predicate_frame' THEN
   SELECT jsonb_agg(m_->'contribution' ORDER BY n) INTO members
   FROM jsonb_array_elements(c->'frame_members') WITH ORDINALITY x(m_,n);
   SELECT m_ INTO STRICT predicate FROM jsonb_array_elements(c->'frame_members') m_ WHERE m_->>'role'='predicate';
   SELECT m_ INTO focus FROM jsonb_array_elements(c->'frame_members') m_ WHERE m_->>'role'='focus';
   IF evidence->>'kind'<>'composite' OR evidence ? 'endpoints' OR evidence->'members' IS DISTINCT FROM members
    OR jsonb_array_length(members)<>(SELECT count(DISTINCT m_) FROM jsonb_array_elements(members) m_)
    OR NOT c->'dependencies' @> members
    OR predicate->'head_token' IS DISTINCT FROM c->'predicate_token'
    OR (SELECT count(*) FROM jsonb_array_elements(c->'frame_members') m_ WHERE m_->>'role'='focus')>1
    OR (c->>'focus_state'='unavailable') IS DISTINCT FROM (focus IS NULL)
    OR (c->>'focus_state'='exact' AND (jsonb_array_length(focus->'extents')<>1 OR focus->>'outcome'<>'complete')) THEN
    RAISE EXCEPTION 'predicate frame differs from distinct role members and exact focus' USING ERRCODE='23514';
   END IF;
   FOR m IN SELECT value FROM jsonb_array_elements(c->'frame_members') LOOP
    part:=p_population->(m->>'contribution');
    IF part IS NULL OR part->'pin' IS DISTINCT FROM evidence->'pin'
     OR part->>'operation_key' IS DISTINCT FROM evidence->>'operation_key'
     OR part->>'kind'<>'occurrence' OR part->>'semantic_type'<>'structural.predicate_member'
     OR NOT part->'computation_dependencies' ? (c->>'annotation')
     OR (m ? 'head_token' AND NOT m->'token_indices' @> jsonb_build_array(m->'head_token'))
     OR (m ? 'inherited_from' AND (m->>'inherited_from')::bigint>=jsonb_array_length(tokens))
     OR NOT ops.predicate_role_anchor_match(p_view.projection,m->'extents',part->'anchors',tokens,m->'token_indices',lo,hi) THEN
     RAISE EXCEPTION 'predicate role differs from retained tokens and exact source extents' USING ERRCODE='23514';
    END IF;
   END LOOP;
  ELSIF kind_='predicate_cue' THEN
   part:=p_population->(c->>'marker_member');
   IF evidence->>'kind'<>'occurrence'
    OR NOT ops.predicate_role_anchor_match(p_view.projection,c->'extents',evidence->'anchors',tokens,c->'token_indices',lo,hi)
    OR EXISTS(SELECT FROM jsonb_array_elements_text(c->'candidate_tokens') token
     WHERE token::bigint>=jsonb_array_length(tokens))
    OR (c->>'host_state'='located' AND (part IS NULL OR (
     coalesce(jsonb_array_length(c->'candidate_tokens'),0)=0
     AND coalesce(jsonb_array_length(c->'cross_block_hosts'),0)=0)))
    OR (c ? 'cross_block_hosts' AND (
     NOT coalesce(c->>'variant'=ANY(cross_recipes) AND c->>'cue_kind'='assumption',false)
     OR coalesce(jsonb_array_length(c->'candidate_tokens'),0)<>0
     OR NOT ((c->'dependencies') @> (c->'cross_block_hosts'))
     OR EXISTS(SELECT FROM jsonb_array_elements_text(c->'cross_block_hosts') i GROUP BY i HAVING count(*)>1)
     OR EXISTS(SELECT FROM jsonb_array_elements_text(c->'cross_block_hosts') i
      WHERE p_population->i->'component'->>'kind' IS DISTINCT FROM 'predicate_frame'
       OR p_population->i->'pin' IS DISTINCT FROM evidence->'pin'
       OR p_population->i->'component'->>'scope' IS DISTINCT FROM c->>'scope'
       OR p_population->i->'component'->>'effective_version' IS DISTINCT FROM c->>'effective_version'
       OR p_population->i->'component'->>'annotation' IS NOT DISTINCT FROM c->>'annotation'
       OR (c->>'host_state'='located' AND (
        SELECT count(*) FROM jsonb_each(p_population) q
        WHERE q.value->'component'->>'host_contribution_id'=i
         AND q.value->'component'->>'qualifier_contribution_id'=evidence->>'contribution_id'
         AND q.value->'component' ? 'host_witness')<>1))
    ))
    OR (c ? 'marker_member' AND (
     part IS NULL OR part->'pin' IS DISTINCT FROM evidence->'pin'
     OR part->>'operation_key' IS DISTINCT FROM evidence->>'operation_key'
     OR part->>'semantic_type'<>'structural.predicate_member'
     OR NOT c->'dependencies' ? (c->>'marker_member')
     OR evidence->'members' IS DISTINCT FROM jsonb_build_array(c->'marker_member')
     OR NOT ops.predicate_role_anchor_match(
      p_view.projection,c->'marker_extents',part->'anchors',tokens,c->'marker_token_indices',lo,hi)))
    OR (NOT c ? 'marker_member' AND evidence ? 'members') THEN
    RAISE EXCEPTION 'predicate qualifier lacks exact retained evidence or candidate hosts' USING ERRCODE='23514';
   END IF;
  ELSE
   host:=p_population->(CASE kind_ WHEN 'predicate_reading' THEN c->>'frame' ELSE c->>'host_contribution_id' END);
   IF host->'component'->>'kind' IS DISTINCT FROM 'predicate_frame'
    OR host->'pin' IS DISTINCT FROM evidence->'pin'
    OR host->'component'->>'scope' IS DISTINCT FROM c->>'scope'
    OR host->'component'->>'effective_version' IS DISTINCT FROM c->>'effective_version'
    OR NOT c->'dependencies' ? (host->>'contribution_id') THEN
    RAISE EXCEPTION 'predicate interpretation differs from exact frame scope or version' USING ERRCODE='23514';
   END IF;
   IF kind_='predicate_reading' THEN
    IF evidence->>'kind'<>'composite' OR evidence ? 'endpoints'
     OR evidence->'members' IS DISTINCT FROM jsonb_build_array(host->'contribution_id') THEN
     RAISE EXCEPTION 'predicate reading must interpret one exact frame' USING ERRCODE='23514';
    END IF;
   ELSE
    cue:=p_population->(c->>'qualifier_contribution_id');
    cue_component:=cue->'component'; host_component:=host->'component';
    annotation:=annotation_map->(cue_component->>'annotation');
    recipe:=cue_component->>'variant';
    IF c ? 'host_witness' THEN
     host_annotation:=annotation_map->(host_component->>'annotation');
     SELECT p INTO STRICT selection FROM jsonb_array_elements(p_config->'inputs'->'passages') p
      WHERE p->>'source_ref'=original_id AND p->>'passage_id'=c->>'scope'
       AND p->>'effective_version' IS NOT DISTINCT FROM c->>'effective_version';
     matches_host:=predicate_version='3' AND recipe=ANY(cross_recipes)
      AND ops.predicate_cross_block_host_matches(p_view,p_population,cue_component,host,c,
       annotation,host_annotation,selection);
    ELSE
     matches_host:=NOT coalesce(recipe=ANY(cross_recipes),false)
      AND cue_component->>'annotation'=host_component->>'annotation'
      AND cue_component->>'block'=host_component->>'block'
      AND cue_component->'candidate_tokens' @> jsonb_build_array(host_component->'predicate_token')
      AND CASE WHEN recipe=ANY(local_recipes) THEN predicate_version='3'
       AND ops.predicate_cue_recipe_matches(p_view.projection,annotation,cue_component,
        (host_component->>'predicate_token')::integer)
       ELSE ops.predicate_cue_host_matches(p_view.projection,annotation->'tokens',cue_component,
        (host_component->>'predicate_token')::integer) END;
    END IF;
    interpretation:=p_population->(c->>'interpretation_member');
    qualified:=data.record_source_json(c->'qualification');
    condition_:=data.record_source_json(c->'condition');
    IF cue->'component'->>'kind' IS DISTINCT FROM 'predicate_cue'
     OR cue->'component'->>'host_state' IS DISTINCT FROM 'located'
     OR cue->'pin' IS DISTINCT FROM evidence->'pin'
     OR cue->'component'->>'scope' IS DISTINCT FROM c->>'scope'
     OR cue->'component'->>'effective_version' IS DISTINCT FROM c->>'effective_version'
     OR cue_component->>'cue_kind' IS DISTINCT FROM c->>'qualifier_kind'
     OR NOT c->'dependencies' ? (cue->>'contribution_id')
     OR matches_host IS DISTINCT FROM true
     OR (recipe=ANY(local_recipes||cross_recipes) AND c->>'qualifier_kind' IN ('condition','assumption')
      AND condition_->>'kind' IS DISTINCT FROM 'escape')
     OR (recipe IN ('nominal_parameter_pair','customer_population_inclusion') AND c ? 'qualification')
     OR evidence->'members' IS DISTINCT FROM (CASE WHEN c ? 'interpretation_member'
      THEN jsonb_build_array(cue->'contribution_id',host->'contribution_id',c->'interpretation_member')
      ELSE jsonb_build_array(cue->'contribution_id',host->'contribution_id') END)
     OR (c ? 'qualification') IS DISTINCT FROM (c ? 'interpretation_member')
     OR (condition_->>'kind'='escape' AND condition_->>'text' IS DISTINCT FROM
      (SELECT string_agg(substring(p_view.projection->>'text' FROM (e->>'start')::integer+1
         FOR (e->>'end')::integer-(e->>'start')::integer),' ' ORDER BY n)
       FROM jsonb_array_elements(cue->'component'->'extents') WITH ORDINALITY x(e,n)))
     OR (c ? 'condition' AND c->>'qualifier_kind' NOT IN ('condition','assumption'))
     OR (c ? 'condition' AND NOT coalesce(public.json_matches_schema(
      condition_schema,data.record_source_json(c->'condition')::json),false))
     OR (c ? 'qualification' AND (
      NOT coalesce(public.json_matches_schema(qualification_schema,data.record_source_json(c->'qualification')::json),false)
      OR qualified->'condition' IS DISTINCT FROM (CASE WHEN c ? 'condition' THEN condition_ END)
      OR NOT c->'dependencies' ? (c->>'interpretation_member')
      OR interpretation->'component'->>'kind' IS DISTINCT FROM 'predicate_reading'
      OR interpretation->'component'->'frame' IS DISTINCT FROM host->'contribution_id'
      OR qualified->'scope' IS DISTINCT FROM jsonb_build_object('extent','statement','locator',host->'contribution_id')
      OR qualified->>'modality' IS DISTINCT FROM (CASE interpretation->'component'->>'reading'
       WHEN 'definition' THEN 'defined' WHEN 'assumption_restriction' THEN 'supposed'
       WHEN 'described_process' THEN 'asserted' END)
      OR qualified->'polarity' IS DISTINCT FROM (CASE interpretation->'component'->>'polarity'
       WHEN 'positive' THEN 'true'::jsonb WHEN 'negative' THEN 'false'::jsonb END)
     )) THEN
     RAISE EXCEPTION 'predicate qualifier differs from its exact proposed host' USING ERRCODE='23514';
    END IF;
   END IF;
  END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'predicate evidence cannot resolve exact scope and annotation custody' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_source_predicates(ops.task,kb.source_view,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_witnessed_formula_links(
 v kb.source_view,config_ jsonb,population jsonb,operation_map jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE op jsonb; link_ jsonb; use_ jsonb; target_ jsonb; cue jsonb; earlier jsonb; declaration_ jsonb;
 up jsonb; tp jsonb; use_item jsonb; target_item jsonb; use_text text; target_text text;
 uv jsonb; tv jsonb; cv jsonb; dv jsonb; matched text[]; named text[]; scope_ text;
 declaration_count bigint; source_count bigint; ext jsonb; expected text; passage_lo bigint;
BEGIN
 FOR op IN SELECT value FROM jsonb_each(operation_map) WHERE value->>'question'='source_witnessed_links' LOOP
  IF op->>'operation_version' IS DISTINCT FROM '1' THEN
   RAISE EXCEPTION 'unsupported witnessed link version' USING ERRCODE='23514';
  END IF;
  SELECT count(*) INTO source_count FROM jsonb_array_elements(config_->'inputs'->'sources') s
   WHERE (s->>'source_view_id')::bigint=v.id;
  IF source_count<>1 THEN RAISE EXCEPTION 'witnessed links require one exact source selection' USING ERRCODE='23514'; END IF;
  SELECT coalesce(jsonb_agg(jsonb_build_array(p->'passage_id',p->'start',p->'end',p->'effective_version') ORDER BY n),'[]')
   INTO ext FROM jsonb_array_elements(config_->'inputs'->'passages') WITH ORDINALITY pp(p,n)
   WHERE p->>'source_ref'=(SELECT encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')
      FROM jsonb_array_elements(config_->'inputs'->'sources') s WHERE (s->>'source_view_id')::bigint=v.id);
  expected:='contribution-operation:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
   jsonb_build_array('source_witnessed_links','1',jsonb_build_object(
    'source',v.key,'native_product_task_id',v.native_task_id,'product_key',v.native_product_key,
    'product_digest',v.native_content_digest,'projection_digest',v.projection_digest,
    'recipe_digest',v.recipe_digest,'source_view_id',v.id),ext),'{}'::jsonb)),'UTF8')),'hex');
  IF op->>'operation_key' IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'witnessed links differ from exact selection identity' USING ERRCODE='23514'; END IF;
  FOR link_ IN SELECT r FROM jsonb_array_elements(population) r
   WHERE r->>'operation_key'=op->>'operation_key' AND r->>'kind'='relation'
  LOOP
   SELECT r INTO STRICT use_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=link_->'members'->>0;
   SELECT r INTO STRICT target_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=link_->'members'->>1;
   uv:=data.record_source_json(use_->'value'); tv:=data.record_source_json(target_->'value');
   IF link_->'component'->>'attachment_kind' IS DISTINCT FROM 'declares'
    OR operation_map->(use_->>'operation_key')->>'question' IS DISTINCT FROM 'source_formula_occurrences'
    OR uv->>'role' IS DISTINCT FROM 'formula_symbol'
    OR target_->>'operation_key' IS DISTINCT FROM op->>'operation_key'
    OR tv->>'role' IS DISTINCT FROM 'declared_name'
    OR link_->'endpoints' IS DISTINCT FROM jsonb_build_array(
     jsonb_build_object('role','attachment','contribution_id',use_->'contribution_id'),
     jsonb_build_object('role','target','contribution_id',target_->'contribution_id')) THEN
    RAISE EXCEPTION 'witnessed formula link has invalid roles or direction' USING ERRCODE='23514'; END IF;
   SELECT p INTO STRICT up FROM jsonb_array_elements(v.projection->'pieces') p
    WHERE p->>'item_ref'=uv->>'source_pointer' AND p->>'kind'='native_text' AND NOT p ? 'cell_index';
   SELECT p INTO STRICT tp FROM jsonb_array_elements(v.projection->'pieces') p
    WHERE p->>'item_ref'=tv->>'source_pointer' AND p->>'kind'='native_text' AND NOT p ? 'cell_index';
   SELECT native_json INTO STRICT use_item FROM ops.read_pdf_published_items(
    v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[up->>'item_ref']);
   SELECT native_json INTO STRICT target_item FROM ops.read_pdf_published_items(
    v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[tp->>'item_ref']);
   SELECT p->>'scope',(p->>'start')::bigint INTO STRICT scope_,passage_lo FROM jsonb_array_elements(config_->'inputs'->'passages') p
    WHERE p->>'passage_id'=tv->>'region'
    AND p->>'source_ref'=(SELECT encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')
      FROM jsonb_array_elements(config_->'inputs'->'sources') s WHERE (s->>'source_view_id')::bigint=v.id)
    AND (p->>'start')::bigint<=(tp->>'start')::bigint AND (up->>'end')::bigint<=(p->>'end')::bigint;
   use_text:=use_item->>'text'; target_text:=target_item->>'text';
   matched:=regexp_match(use_text,'^(We have seen above that it is possible to simulate a ([^.]+) ([A-Za-z]))\.[^.]*the simulated values for ([A-Za-z]) using the equation ([^.]+)\.');
   named:=regexp_match(target_text,'^Let ([A-Za-z]) be (a [^.]+)\. A ([^.]+?) with these parameters is said to be a ([^.]+)\.');
   IF (tp->>'end')::bigint>(up->>'start')::bigint
    OR use_item->'parent' IS NULL OR use_item->'parent' IS DISTINCT FROM target_item->'parent'
    OR use_item->>'content_layer' IS DISTINCT FROM 'body' OR target_item->>'content_layer' IS DISTINCT FROM 'body'
    OR matched IS NULL OR named IS NULL
    OR matched[3] IS DISTINCT FROM uv->>'text' OR matched[3] IS DISTINCT FROM matched[4]
    OR named[1] IS DISTINCT FROM matched[3] OR named[4] IS DISTINCT FROM matched[2]
    OR NOT starts_with(named[2],'a '||named[3]||' with parameters ')
    OR named[4] IS DISTINCT FROM tv->>'text'
    OR position(' using the equation '||matched[5]||'.' IN use_text)+length(' using the equation ')-1>(use_->'anchors'->0->>'start')::integer
    OR (use_->'anchors'->0->>'end')::integer>position(' using the equation '||matched[5]||'.' IN use_text)+length(' using the equation '||matched[5])-1
    OR (target_->'anchors'->0->>'start')::integer IS DISTINCT FROM position(' is said to be a '||named[4]||'.' IN target_text)+length(' is said to be a ')-1
    OR link_->'component'->>'scope' IS DISTINCT FROM scope_ THEN
    RAISE EXCEPTION 'witnessed formula link differs from the original declaration and recap' USING ERRCODE='23514'; END IF;
   SELECT count(*) INTO declaration_count FROM jsonb_array_elements(v.projection->'pieces') p
    CROSS JOIN LATERAL ops.read_pdf_published_items(v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[p->>'item_ref']) node
    CROSS JOIN LATERAL regexp_matches(node.native_json->>'text','\yLet '||matched[3]||' (?:be|denote|represent)\y','g') occurrences
    WHERE passage_lo<=(p->>'start')::bigint AND (p->>'end')::bigint<=(up->>'start')::bigint
    AND p->>'kind'='native_text' AND NOT p ? 'cell_index'
    AND node.native_json->'parent'=target_item->'parent';
   IF declaration_count<>1 THEN RAISE EXCEPTION 'witnessed formula declaration is ambiguous' USING ERRCODE='23514'; END IF;
   SELECT c INTO STRICT cue FROM jsonb_array_elements(population) c WHERE c->>'operation_key'=op->>'operation_key'
    AND link_->'computation_dependencies' ? (c->>'contribution_id')
    AND data.record_source_json(c->'value')->>'role'='declaration_recap';
   cv:=data.record_source_json(cue->'value');
   IF cv->>'source_pointer' IS DISTINCT FROM uv->>'source_pointer'
    OR cv->>'region' IS DISTINCT FROM tv->>'region'
    OR cue->'anchors'->0->>'start' IS DISTINCT FROM '0'
    OR cue->'anchors'->0->>'source_piece' IS DISTINCT FROM matched[1] THEN
    RAISE EXCEPTION 'witnessed formula link lacks exact recap cue' USING ERRCODE='23514'; END IF;
   SELECT e INTO STRICT earlier FROM jsonb_array_elements(population) e
    WHERE e->'component'->>'attachment_kind'='declares' AND e->>'operation_key'<>op->>'operation_key'
    AND link_->'computation_dependencies' ? (e->>'contribution_id');
   SELECT r INTO STRICT declaration_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=earlier->'members'->>1;
   dv:=data.record_source_json(declaration_->'value');
   IF dv->>'source_pointer' IS DISTINCT FROM tv->>'source_pointer'
    OR dv->>'role' IS DISTINCT FROM 'declaration' OR dv->>'text' IS DISTINCT FROM named[2] THEN
    RAISE EXCEPTION 'witnessed formula link lacks the original declared meaning' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'witnessed formula link lacks unambiguous exact custody' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_witnessed_formula_links(kb.source_view,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_named_source_links(
 v kb.source_view,config_ jsonb,population jsonb,operation_map jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE link_ jsonb; subject_ jsonb; target_ jsonb; cue jsonb; a jsonb; b jsonb; c jsonb; op jsonb;
 sp jsonb; tp jsonb; src jsonb; dst jsonb; passage jsonb; literal text; code text; kind_ text;
 pattern_ text; matched text[]; initials text; target_count integer; selected_source text;
BEGIN
 SELECT encode(sha256(convert_to(data.canonical_json(jsonb_strip_nulls(s)),'UTF8')),'hex')
  INTO STRICT selected_source FROM jsonb_array_elements(config_->'inputs'->'sources') s
  WHERE (s->>'source_view_id')::bigint=v.id;
 FOR subject_ IN SELECT r FROM jsonb_array_elements(population) r
  WHERE operation_map->(r->>'operation_key')->>'question'='source_named_links'
   AND data.record_source_json(r->'value')->>'resolution'='external_target_unavailable'
 LOOP
  a:=subject_->'anchors'->0;
  SELECT p INTO STRICT sp FROM jsonb_array_elements(v.projection->'pieces') p
   WHERE p->>'item_ref'=a->>'pointer' AND p->>'kind'='native_text' AND NOT p ? 'cell_index';
  SELECT p INTO STRICT passage FROM jsonb_array_elements(config_->'inputs'->'passages') p
   WHERE p->>'source_ref'=selected_source
    AND p->>'passage_id'=data.record_source_json(subject_->'value')->>'region'
    AND (p->>'start')::bigint<=(sp->>'start')::bigint
    AND (p->>'end')::bigint>=(sp->>'end')::bigint;
  SELECT native_json INTO STRICT src FROM ops.read_pdf_published_items(
   v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[sp->>'item_ref']);
  IF subject_->>'kind' IS DISTINCT FROM 'occurrence'
   OR data.record_source_json(subject_->'value')->>'role' IS DISTINCT FROM 'named_link_subject'
   OR jsonb_array_length(subject_->'anchors') IS DISTINCT FROM 1
   OR src->>'content_layer' IS DISTINCT FROM 'body' OR src->>'label' NOT IN ('text','paragraph','list_item')
   OR a->>'source_piece' !~ '^(?:ISO(?:/IEC)? [0-9]+(?::[0-9]{4})?|RFC [0-9]+|[A-Z][A-Za-z]+ and [A-Z][A-Za-z]+\.[0-9]+)$'
   OR substring(src->>'text' FROM 1 FOR (a->>'start')::integer) !~ '\y[Ss]ee $'
   OR NOT EXISTS(SELECT FROM jsonb_array_elements(population) r
    WHERE r->>'operation_key'=subject_->>'operation_key'
     AND data.record_source_json(r->'value')->>'role'='named_link_cue'
     AND data.record_source_json(r->'value')->>'region'=passage->>'passage_id'
     AND r->'anchors'->0->>'pointer'=a->>'pointer'
     AND r->'anchors'->0->>'source_piece'~'^[Ss]ee$'
     AND (r->'anchors'->0->>'end')::integer+1=(a->>'start')::integer)
   OR EXISTS(SELECT FROM jsonb_array_elements(population) r WHERE r->>'kind'='relation'
    AND r->'members' ? (subject_->>'contribution_id')) THEN
   RAISE EXCEPTION 'external citation lacks its exact unresolved source cue' USING ERRCODE='23514';
  END IF;
 END LOOP;
 FOR link_ IN SELECT r FROM jsonb_array_elements(population) r WHERE r->>'kind'='relation'
  AND operation_map->(r->>'operation_key')->>'question'='source_named_links'
 LOOP
  op:=operation_map->(link_->>'operation_key');
  SELECT r INTO STRICT subject_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=link_->'members'->>0;
  SELECT r INTO STRICT target_ FROM jsonb_array_elements(population) r WHERE r->>'contribution_id'=link_->'members'->>1;
  SELECT r INTO STRICT cue FROM jsonb_array_elements(population) r
   WHERE link_->'computation_dependencies' ? (r->>'contribution_id')
    AND r->>'operation_key'=link_->>'operation_key'
    AND data.record_source_json(r->'value')->>'role'='named_link_cue';
  a:=subject_->'anchors'->0; b:=target_->'anchors'->0; c:=cue->'anchors'->0;
  IF op->>'operation_version' IS DISTINCT FROM '1'
   OR data.record_source_json(subject_->'value')->>'role' IS DISTINCT FROM 'named_link_subject'
   OR data.record_source_json(target_->'value')->>'role' IS DISTINCT FROM 'named_link_target'
   OR subject_->>'operation_key' IS DISTINCT FROM link_->>'operation_key'
   OR target_->>'operation_key' IS DISTINCT FROM link_->>'operation_key'
   OR c->>'pointer' IS DISTINCT FROM a->>'pointer'
   OR link_->'endpoints' IS DISTINCT FROM jsonb_build_array(
     jsonb_build_object('role','attachment','contribution_id',subject_->'contribution_id'),
     jsonb_build_object('role','target','contribution_id',target_->'contribution_id')) THEN
   RAISE EXCEPTION 'named link differs from exact occurrence roles' USING ERRCODE='23514'; END IF;
  SELECT p INTO STRICT sp FROM jsonb_array_elements(v.projection->'pieces') p
   WHERE p->>'item_ref'=a->>'pointer' AND p->>'kind'='native_text' AND NOT p ? 'cell_index';
  SELECT p INTO STRICT tp FROM jsonb_array_elements(v.projection->'pieces') p
   WHERE p->>'item_ref'=b->>'pointer' AND p->>'kind'='native_text' AND NOT p ? 'cell_index';
  SELECT native_json INTO STRICT src FROM ops.read_pdf_published_items(
   v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[sp->>'item_ref']);
  SELECT native_json INTO STRICT dst FROM ops.read_pdf_published_items(
   v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[tp->>'item_ref']);
  SELECT p INTO STRICT passage FROM jsonb_array_elements(config_->'inputs'->'passages') p
   WHERE p->>'passage_id'=data.record_source_json(subject_->'value')->>'region'
    AND p->>'source_ref'=selected_source
    AND (p->>'start')::bigint<=least((sp->>'start')::bigint,(tp->>'start')::bigint)
    AND (p->>'end')::bigint>=greatest((sp->>'end')::bigint,(tp->>'end')::bigint);
  IF src->>'content_layer' IS DISTINCT FROM 'body' OR dst->>'content_layer' IS DISTINCT FROM 'body'
   OR src->>'label' NOT IN ('text','paragraph','list_item')
   OR link_->'component'->>'scope' IS DISTINCT FROM passage->>'scope' THEN
   RAISE EXCEPTION 'named link differs from selected source scope' USING ERRCODE='23514'; END IF;
  kind_:=link_->'component'->>'attachment_kind';
  literal:=src->>'text';
  IF kind_ IN ('section_citation','definition_reference') THEN
   code:=substring(a->>'source_piece' FROM '^Section ([0-9]+(?:\.[0-9]+)+)$');
   pattern_:=CASE kind_ WHEN 'section_citation' THEN '[Ss]ee' ELSE '[Aa]s defined in' END;
   IF code IS NULL OR c->>'source_piece' !~ ('^'||pattern_||'$')
    OR (c->>'end')::integer+1 IS DISTINCT FROM (a->>'start')::integer
    OR substring(literal FROM (c->>'end')::integer+1 FOR 1) IS DISTINCT FROM ' '
    OR dst->>'label' IS DISTINCT FROM 'section_header'
    OR (regexp_match(dst->>'text','^(?:Section )?([0-9]+(?:\.[0-9]+)+)(?:\s|$)'))[1] IS DISTINCT FROM code
    OR b->>'source_piece' IS DISTINCT FROM dst->>'text' OR b->>'start' IS DISTINCT FROM '0' THEN
    RAISE EXCEPTION 'section link differs from exact cue or structural identifier' USING ERRCODE='23514'; END IF;
   SELECT count(*) INTO target_count FROM jsonb_array_elements(v.projection->'pieces') p
    CROSS JOIN LATERAL ops.read_pdf_published_items(
     v.native_task_id,v.native_product_key,v.native_content_digest,ARRAY[p->>'item_ref']) n
    WHERE p->>'kind'='native_text' AND NOT p ? 'cell_index'
     AND (p->>'start')::bigint>=(passage->>'start')::bigint AND (p->>'end')::bigint<=(passage->>'end')::bigint
     AND n.native_json->>'content_layer'='body' AND n.native_json->>'label'='section_header'
     AND (regexp_match(n.native_json->>'text','^(?:Section )?([0-9]+(?:\.[0-9]+)+)(?:\s|$)'))[1]=code;
   IF target_count<>1 THEN RAISE EXCEPTION 'section link has competing targets' USING ERRCODE='23514'; END IF;
  ELSIF kind_='alias' AND c->>'source_piece'='(' THEN
   matched:=regexp_match(literal,'^([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+){1,7}) \(([A-Z]{2,8})\)\.$');
   SELECT string_agg(left(x,1),'' ORDER BY n) INTO initials FROM unnest(string_to_array(matched[1],' ')) WITH ORDINALITY s(x,n);
   IF matched IS NULL OR initials IS DISTINCT FROM matched[2] OR a->>'source_piece' IS DISTINCT FROM matched[1]
    OR b->>'source_piece' IS DISTINCT FROM matched[2] OR a->>'pointer' IS DISTINCT FROM b->>'pointer'
    OR a->>'start' IS DISTINCT FROM '0' OR (a->>'end')::integer+1 IS DISTINCT FROM (c->>'start')::integer
    OR c->>'end' IS DISTINCT FROM b->>'start' THEN
    RAISE EXCEPTION 'acronym does not match its exact full name and cue' USING ERRCODE='23514'; END IF;
  ELSE
   pattern_:=CASE kind_ WHEN 'alias' THEN 'is hereafter called' WHEN 'renames' THEN 'is renamed to'
    WHEN 'specializes' THEN 'specializes' WHEN 'supersedes' THEN 'supersedes' END;
   IF pattern_ IS NULL OR c->>'source_piece' IS DISTINCT FROM pattern_
    OR literal IS DISTINCT FROM (a->>'source_piece')||' '||pattern_||' '||(b->>'source_piece')||'.'
    OR a->>'pointer' IS DISTINCT FROM b->>'pointer' OR a->>'start' IS DISTINCT FROM '0'
    OR (a->>'end')::integer+1 IS DISTINCT FROM (c->>'start')::integer
    OR (c->>'end')::integer+1 IS DISTINCT FROM (b->>'start')::integer
    OR lower(a->>'source_piece')=lower(b->>'source_piece') THEN
    RAISE EXCEPTION 'named link differs from exact directed declaration' USING ERRCODE='23514'; END IF;
  END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'named link lacks its unique selected native source' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_named_source_links(kb.source_view,jsonb,jsonb,jsonb) FROM PUBLIC;

-- The original definition component and physical layout establish its section.
CREATE OR REPLACE FUNCTION ops.contextual_component_section(ref jsonb,work_digest text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb; term jsonb; passage jsonb; pin jsonb; v kb.source_view; piece jsonb;
 item_ jsonb; header_ jsonb;
BEGIN
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
 RETURN (regexp_match(header_->>'text','^(?:Section )?([0-9]+(?:\.[0-9]+)+)(?:\s|$)'))[1];
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION ops.contextual_component_section(jsonb,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.contextual_component_section(jsonb,text) TO corpus_sem_reader,corpus_sem_writer;

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
 operation_map jsonb; identity_map jsonb; output_counts jsonb; schemas jsonb:='{}'; allowed_contracts jsonb;
 local_ jsonb; local_request jsonb; local_result jsonb; selected_ids jsonb; local_inputs jsonb;
 predicate_population jsonb; table_config jsonb; table_mode text; table_policy_id text; formula_meaning jsonb;
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
 IF p_envelope->>'method'='structure.scoped_relations' AND p_envelope->>'operation_version' IN ('3','4','5','6') THEN
  PERFORM ops.validate_source_table_note_scope(v,p_envelope->'contributions');
  SELECT params INTO STRICT table_config FROM ops.method_config WHERE id=t.method_config_id;
  table_mode:=table_config->>'interpretation_mode';
  IF table_mode IS NULL OR table_mode NOT IN ('feasibility','independent','coupled')
   OR table_config->>'interpretation_weight_scale' IS NULL
   OR table_config->>'interpretation_weight_scale' NOT IN ('0.5','1','2') THEN
   RAISE EXCEPTION 'invalid registered table interpretation policy' USING ERRCODE='23514';
  END IF;
  table_policy_id:='table-policy:shared-table-band-3:'||table_mode||':'||(table_config->>'interpretation_weight_scale');
 END IF;
 IF p_envelope->>'source' IS NULL OR p_envelope->>'source' NOT IN (t.unit_key,v.key) THEN
  RAISE EXCEPTION 'contribution source differs from selected task/view' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*)<>count(DISTINCT o->>'operation_key') FROM jsonb_array_elements(p_envelope->'contribution_operations') o) THEN
  RAISE EXCEPTION 'duplicate contribution operation identity' USING ERRCODE='23514'; END IF;
 SELECT array_agg(x->>'contribution_id') INTO identities FROM jsonb_array_elements(p_envelope->'contributions') x;
 IF cardinality(identities) IS DISTINCT FROM (SELECT count(DISTINCT x) FROM unnest(identities) x)
  AND cardinality(identities)>0 THEN RAISE EXCEPTION 'duplicate contribution identity' USING ERRCODE='23514'; END IF;
 SELECT jsonb_object_agg(o->>'operation_key',o) INTO operation_map FROM jsonb_array_elements(p_envelope->'contribution_operations') o;
 IF EXISTS(SELECT FROM jsonb_each(operation_map) o
  WHERE o.value->>'question'='source_formula_occurrences'
   AND (p_envelope->>'method' IS DISTINCT FROM 'structure.scoped_relations'
    OR p_envelope->>'operation_version' NOT IN ('5','6')
    OR o.value->>'operation_version' IS DISTINCT FROM '1')) THEN
  RAISE EXCEPTION 'formula occurrence operation requires its released producer' USING ERRCODE='23514';
 END IF;
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
    OR op->>'operation_version' IS DISTINCT FROM 'local-interpretation-2'
    OR COALESCE(local_->>'policy_version','')=''
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
       ELSIF EXISTS(SELECT FROM jsonb_array_elements(t_->'allowed') v WHERE jsonb_typeof(v) IS DISTINCT FROM 'boolean') THEN
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
       IF abs(mass_-1)>1e-9 THEN RAISE EXCEPTION 'local interpretation marginal normalization invalid' USING ERRCODE='23514'; END IF;
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
      IF mass_>1+1e-9 OR (jsonb_array_length(local_result->'alternatives')=positive_ AND abs(mass_-1)>1e-9) THEN
       RAISE EXCEPTION 'local interpretation displayed support probability mass invalid' USING ERRCODE='23514'; END IF;
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
    IF p_envelope->>'method'='retrieve.contextual' AND p_envelope->>'operation_version'='6'
     AND EXISTS(SELECT FROM ops.method_config cfg,
      LATERAL jsonb_array_elements(cfg.params->'relationship_constraints') q
      WHERE cfg.id=t.method_config_id AND q->'relation_kinds' ? 'defined-by') THEN
      SELECT coalesce(jsonb_agg(jsonb_build_object('target_id',id,'score',1,'evidence',evidence)
       ORDER BY id),'[]') INTO expected_hits FROM (
       SELECT ct->'reference'->>'component_id' id,
        jsonb_agg(DISTINCT c->>'contribution_id' ORDER BY c->>'contribution_id') evidence
       FROM jsonb_array_elements(report->'component_targets') ct,
        jsonb_array_elements(p_envelope->'contributions') c,
        LATERAL (SELECT data.record_source_json(c->'value') val) occurrence,
        LATERAL (SELECT data.record_source_json(occurrence.val->'producer_value') val) meaning
       WHERE c->>'semantic_type'='contextual.located_mention'
        AND c->>'occurrence_id'=candidate_list->>'occurrence_id'
        AND (
         (occurrence.val->>'producer_semantic_type'='definition.term'
          AND meaning.val->>'role'='defined_term' AND meaning.val->'component_reference'=ct->'reference')
         OR (occurrence.val->>'producer_semantic_type'='structural.located_participant'
          AND meaning.val->>'role'='named_link_subject'
          AND jsonb_array_length(c->'anchors')=1
          AND substring(c->'anchors'->0->>'source_piece' FROM '^Section ([0-9]+(?:\.[0-9]+)+)$')
           =ops.contextual_component_section(ct->'reference',v.native_content_digest)
          AND EXISTS(SELECT FROM jsonb_array_elements(v.projection->'pieces') p
           WHERE p->>'kind'='native_text' AND NOT p ? 'cell_index'
            AND p->>'item_ref'=c->'anchors'->0->>'pointer'
            AND substring(v.projection->>'text' FROM (p->>'start')::integer+1 FOR
             (c->'anchors'->0->>'start')::integer)~'\y[Aa]s defined in $'))
        )
        AND EXISTS(SELECT FROM jsonb_array_elements(inv->'targets') tg WHERE tg->>'target_id'=ct->'reference'->>'component_id')
       GROUP BY ct->'reference'->>'component_id'
      ) eligible;
    ELSE expected_hits:='[]'; END IF;
    SELECT value INTO channel_report FROM jsonb_array_elements(candidate_list->'channel_results')
     WHERE value->>'channel'='witness';
    IF (expected_hits='[]' AND channel_report IS NOT NULL)
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
     IF starts_with(witness->>'witness_id','section-definition:') AND (
      witness->>'basis' IS DISTINCT FROM 'explicit_source_cue'
      OR witness->>'relation' IS DISTINCT FROM 'defined-by'
      OR NOT EXISTS(SELECT FROM jsonb_array_elements(candidate_list->'channel_results') ch,
       LATERAL jsonb_array_elements(ch->'hits') hit WHERE ch->>'channel'='witness'
       AND hit->>'target_id'=witness->>'target_id' AND hit->'evidence' @> witness->'evidence_ids')
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
    OR EXISTS(SELECT FROM jsonb_array_elements(p_envelope->'contributions') link_
      WHERE link_->>'kind'='relation'
       AND (p_envelope->>'operation_version'<>'6' OR
        operation_map->(link_->>'operation_key')->>'question' IS DISTINCT FROM 'source_witnessed_links')
       AND link_->'endpoints' @>
       jsonb_build_array(jsonb_build_object('contribution_id',contribution->>'contribution_id')))
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
      JOIN LATERAL (SELECT c FROM jsonb_array_elements(p_envelope->'contributions') c WHERE c->>'contribution_id'=e->>'contribution_id') c ON true
      CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c.c->'anchors','[]')) a
     UNION ALL SELECT a FROM jsonb_array_elements_text(COALESCE(contribution->'members','[]')) m(id)
      JOIN LATERAL (SELECT c FROM jsonb_array_elements(p_envelope->'contributions') c WHERE c->>'contribution_id'=m.id) c ON true
      CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c.c->'anchors','[]')) a
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
  IF p_envelope->>'method'<>'structure.scoped_relations' OR p_envelope->>'operation_version' NOT IN ('4','5','6') THEN
   RAISE EXCEPTION 'predicate evidence requires its released producer' USING ERRCODE='23514';
  END IF;
  SELECT jsonb_object_agg(c->>'contribution_id',c) INTO predicate_population
  FROM jsonb_array_elements(p_envelope->'contributions') c
  WHERE c->>'semantic_type' IN ('structural.predicate_member','structural.predicate_frame',
   'structural.predicate_cue','structural.predicate_reading','structural.predicate_qualification');
  PERFORM ops.validate_source_predicates(
   t,v,predicate_population,table_config||jsonb_build_object('_predicate_operations',operation_map,
    '_predicate_version',CASE WHEN p_envelope->>'operation_version' IN ('5','6') THEN '3' ELSE '2' END));
 END IF;
 IF EXISTS(SELECT FROM jsonb_each(operation_map) o WHERE o.value->>'question'='source_witnessed_links') THEN
  IF p_envelope->>'method' IS DISTINCT FROM 'structure.scoped_relations'
   OR p_envelope->>'operation_version' IS DISTINCT FROM '6' THEN
   RAISE EXCEPTION 'witnessed links require their released source producer' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_witnessed_formula_links(v,table_config,p_envelope->'contributions',operation_map);
 END IF;
 IF EXISTS(SELECT FROM jsonb_each(operation_map) o WHERE o.value->>'question'='source_named_links') THEN
  IF p_envelope->>'method' IS DISTINCT FROM 'structure.scoped_relations'
   OR p_envelope->>'operation_version' IS DISTINCT FROM '6' THEN
   RAISE EXCEPTION 'named links require their released source producer' USING ERRCODE='23514'; END IF;
  PERFORM ops.validate_named_source_links(v,table_config,p_envelope->'contributions',operation_map);
 END IF;
 IF p_envelope->>'method'='structure.scoped_relations' AND p_envelope->>'operation_version'='6'
  AND (COALESCE(table_config->'classification_refs','[]')<>'[]'::jsonb
   OR data.record_source_json(p_envelope->'parse_detail') ? 'clause_model_concordance') THEN
  IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(table_config->'classification_refs','[]')) ref
    WHERE NOT table_config->'inputs'->'dependencies' ? (ref->>'product_id'))
   OR COALESCE(data.record_source_json(p_envelope->'parse_detail')->'clause_model_concordance','[]') IS DISTINCT FROM
    ops.clause_model_concordance(COALESCE(table_config->'classification_refs','[]'),v.id,p_envelope->'contributions') THEN
   RAISE EXCEPTION 'clause model concordance differs from authenticated exact focus' USING ERRCODE='23514'; END IF;
 END IF;
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
