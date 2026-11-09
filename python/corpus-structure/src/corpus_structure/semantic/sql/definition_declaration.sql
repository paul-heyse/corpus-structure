-- Replay the exact effective parser layout before accepting a v2 native envelope.
-- This verifier does not infer or normalize source text.
CREATE OR REPLACE FUNCTION ops.private_declaration_enabled(p_release text)
RETURNS boolean LANGUAGE sql STABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT count(*)=1 AND coalesce(bool_and(convert_from(content,'UTF8')=data.canonical_json(
  '{"scope":"private_development","hanlp_layout_policy":"source-seam-continuation-1",
    "definition_declaration_chain":"definition-declaration-chain-1"}'::jsonb)),false)
 FROM sem.input WHERE release_id=p_release AND input_kind='dependency'
  AND input_name ~ '^(pack/[^/]+/)?operation/pm2-definition-policy[.]json$'
$$;
REVOKE ALL ON FUNCTION ops.private_declaration_enabled(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_seam_source_tokens(
 p_report jsonb, p_projection jsonb, p_protected jsonb, p_startup jsonb
) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE
 map_ jsonb:=p_report->'source_map'; layout jsonb:=map_->'layout'; repair jsonb:=layout->'repair';
 tokens jsonb:=map_->'tokens'; slice_ jsonb:=map_->'context_pieces'->0;
 scope_start integer:=(slice_->>'start')::integer; scope_end integer:=(slice_->>'end')::integer;
 full_text text:=p_projection->>'text'; text_ text; tok jsonb; prior integer:=0;
 start_ integer; end_ integer; number_ integer; current_ integer:=0;
 sentences jsonb:='[]'; words jsonb:='[]'; sentence_tokens jsonb:='[]'; current_tokens jsonb:='[]';
 begin_ integer; stop_ integer; seam integer; coordinator_start integer; coordinator_end integer;
 previous_start integer; previous_end integer; token_count integer:=0;
 char_digest text; map_digest text; expected text; atoms jsonb; matched integer; competing integer;
BEGIN
 IF jsonb_typeof(map_) IS DISTINCT FROM 'object'
  OR jsonb_typeof(layout) IS DISTINCT FROM 'object'
  OR layout-ARRAY['policy','outcome','repair']<>'{}'::jsonb
  OR layout->>'policy' IS DISTINCT FROM 'source-seam-continuation-1'
  OR COALESCE(layout->>'outcome','') NOT IN ('repaired','unchanged','ambiguous')
  OR (layout->>'outcome'='repaired') IS DISTINCT FROM (jsonb_typeof(repair)='object')
  OR (layout->>'outcome'<>'repaired' AND repair IS DISTINCT FROM 'null'::jsonb)
  OR jsonb_typeof(tokens) IS DISTINCT FROM 'array' OR jsonb_array_length(tokens)=0
  OR jsonb_array_length(tokens)>4096
  OR jsonb_array_length(map_->'context_pieces') IS DISTINCT FROM 1
  OR slice_->>'coordinate_space' IS DISTINCT FROM 'native_projection'
  OR slice_->>'precision' IS DISTINCT FROM 'exact'
  OR NOT COALESCE(scope_start>=0 AND scope_start<scope_end AND scope_end<=char_length(full_text)
   AND scope_end-scope_start<=4096,false)
  OR COALESCE(p_report->>'scope_digest','') !~ '^[0-9a-f]{64}$'
  OR p_report->'authorized_source_path' IS DISTINCT FROM 'null'::jsonb
  OR map_->'segments' IS DISTINCT FROM jsonb_build_array(jsonb_build_object(
   'provider_start',0,'provider_end',scope_end-scope_start,'layout_start',0))
 THEN RAISE EXCEPTION 'HanLP v2 report lacks the exact bounded source layout' USING ERRCODE='23514'; END IF;
 text_:=substring(full_text FROM scope_start+1 FOR scope_end-scope_start);
 IF EXISTS(SELECT FROM jsonb_array_elements(p_protected) AS a(span)
  WHERE (span->>0)::integer<scope_end AND (span->>1)::integer>scope_start
  AND NOT ((span->>0)::integer>=scope_start AND (span->>1)::integer<=scope_end)) THEN
  RAISE EXCEPTION 'HanLP v2 scope cuts a protected source item' USING ERRCODE='23514';
 END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_array(a-scope_start,b-scope_start) ORDER BY a,b),'[]'::jsonb)
 INTO atoms FROM (
  SELECT (span->>0)::integer a,(span->>1)::integer b FROM jsonb_array_elements(p_protected) AS x(span)
 ) AS ranges WHERE a>=scope_start AND b<=scope_end;
 IF map_->'protected_atoms' IS DISTINCT FROM atoms THEN
  RAISE EXCEPTION 'HanLP v2 protected map differs from retained source atoms' USING ERRCODE='23514';
 END IF;
 FOR tok IN SELECT value FROM jsonb_array_elements(tokens) LOOP
  IF jsonb_typeof(tok) IS DISTINCT FROM 'object' OR tok-ARRAY['start','end','text','sentence']<>'{}'::jsonb
   OR NOT tok ?& ARRAY['start','end','text','sentence']
   OR jsonb_typeof(tok->'text') IS DISTINCT FROM 'string'
   OR COALESCE(tok->>'start','') !~ '^(0|[1-9][0-9]*)$'
   OR COALESCE(tok->>'end','') !~ '^[1-9][0-9]*$'
   OR COALESCE(tok->>'sentence','') !~ '^[0-7]$' THEN
   RAISE EXCEPTION 'HanLP v2 token is not one exact ordered source interval' USING ERRCODE='23514'; END IF;
  start_:=(tok->>'start')::integer; end_:=(tok->>'end')::integer; number_:=(tok->>'sentence')::integer;
  IF start_<prior OR end_<=start_ OR end_>char_length(text_)
   OR (token_count=0 AND (number_<>0 OR start_<>0))
   OR number_ NOT IN (current_,current_+1)
   OR substring(text_ FROM prior+1 FOR start_-prior) !~ '^[[:space:]]*$'
   OR tok->>'text' !~ '[^[:space:]]'
   OR tok->>'text' IS DISTINCT FROM substring(text_ FROM start_+1 FOR end_-start_)
   OR EXISTS(SELECT FROM jsonb_array_elements(atoms) AS x(span)
    WHERE (span->>0)::integer<end_ AND (span->>1)::integer>start_
    AND ((span->>0)::integer<>start_ OR (span->>1)::integer<>end_)) THEN
   RAISE EXCEPTION 'HanLP v2 token loses or changes selected source' USING ERRCODE='23514'; END IF;
  IF number_<>current_ THEN
   sentences:=sentences||jsonb_build_array(words);
   sentence_tokens:=sentence_tokens||jsonb_build_array(current_tokens);
   words:='[]'; current_tokens:='[]'; current_:=number_;
  END IF;
  words:=words||jsonb_build_array(tok->'text');
  current_tokens:=current_tokens||jsonb_build_array(tok);
  token_count:=token_count+1; prior:=end_;
 END LOOP;
 sentences:=sentences||jsonb_build_array(words);
 sentence_tokens:=sentence_tokens||jsonb_build_array(current_tokens);
 IF prior<>char_length(text_) OR p_report->'request' IS DISTINCT FROM jsonb_build_object('sentences',sentences)
  OR (p_report#>>'{native,outcome}'='succeeded'
   AND p_report#>'{native,native,tok}' IS DISTINCT FROM sentences) THEN
  RAISE EXCEPTION 'HanLP v2 request differs from the exact source token population' USING ERRCODE='23514';
 END IF;
 IF layout->>'outcome'='repaired' THEN
  IF repair-ARRAY['previous_sentence','orphan_sentence','punctuation_start','coordinator']<>'{}'::jsonb
   OR NOT repair ?& ARRAY['previous_sentence','orphan_sentence','punctuation_start','coordinator']
   OR jsonb_array_length(repair->'previous_sentence') IS DISTINCT FROM 2
   OR jsonb_array_length(repair->'orphan_sentence') IS DISTINCT FROM 2
   OR jsonb_array_length(repair->'coordinator') IS DISTINCT FROM 2 THEN
   RAISE EXCEPTION 'HanLP v2 seam repair has invalid exact coordinates' USING ERRCODE='23514'; END IF;
  previous_start:=(repair#>>'{previous_sentence,0}')::integer;
  previous_end:=(repair#>>'{previous_sentence,1}')::integer;
  begin_:=(repair#>>'{orphan_sentence,0}')::integer;
  stop_:=(repair#>>'{orphan_sentence,1}')::integer;
  seam:=(repair->>'punctuation_start')::integer;
  coordinator_start:=(repair#>>'{coordinator,0}')::integer;
  coordinator_end:=(repair#>>'{coordinator,1}')::integer;
  IF NOT COALESCE(scope_start<=previous_start AND previous_start<=coordinator_start
   AND coordinator_start<coordinator_end AND coordinator_end=previous_end
   AND previous_end+1=begin_ AND begin_+1=seam AND seam+1=stop_ AND stop_<=scope_end,false)
   OR lower(substring(full_text FROM coordinator_start+1 FOR coordinator_end-coordinator_start))
    NOT IN ('and','or')
   OR substring(full_text FROM previous_end+1 FOR 1)<>' '
   OR substring(full_text FROM begin_+1 FOR 1) !~ '^[[:alpha:]]$'
   OR substring(full_text FROM seam+1 FOR 1)<>'.'
   OR EXISTS(SELECT FROM jsonb_array_elements(p_protected) AS x(span)
    WHERE (span->>0)::integer<stop_ AND (span->>1)::integer>coordinator_start)
   OR NOT EXISTS(
    SELECT FROM jsonb_array_elements(p_projection->'pieces') AS q(p)
    CROSS JOIN jsonb_array_elements(p_projection->'pieces') AS l(p)
    CROSS JOIN jsonb_array_elements(p_projection->'pieces') AS r(p)
    WHERE q.p->>'kind'='native_text' AND q.p->>'source_field'='text'
     AND l.p->>'kind'='native_text' AND l.p->>'source_field'='text'
     AND r.p->>'kind'='native_text' AND r.p->>'source_field'='text'
     AND (q.p->>'start')::integer<=coordinator_start AND (q.p->>'end')::integer=begin_
     AND (l.p->>'start')::integer=begin_ AND (l.p->>'end')::integer=seam
     AND (r.p->>'start')::integer=seam AND r.p->>'item_ref'<>l.p->>'item_ref'
   ) THEN
   RAISE EXCEPTION 'HanLP v2 repair is not an exact unprotected source seam' USING ERRCODE='23514'; END IF;
  SELECT count(*) INTO matched FROM jsonb_array_elements(sentence_tokens) AS x(s)
  WHERE jsonb_array_length(s)>=3
   AND (s#>>'{0,start}')::integer=previous_start-scope_start
   AND (s->(-3)->>'start')::integer=coordinator_start-scope_start
   AND (s->(-3)->>'end')::integer=coordinator_end-scope_start
   AND (s->(-2)->>'start')::integer=begin_-scope_start
   AND (s->(-2)->>'end')::integer=seam-scope_start
   AND (s->(-1)->>'start')::integer=seam-scope_start
   AND (s->(-1)->>'end')::integer=stop_-scope_start;
  IF matched<>1 THEN
   RAISE EXCEPTION 'HanLP v2 effective sentence differs from its exact repaired seam'
    USING ERRCODE='23514'; END IF;
 END IF;
 -- Reversing the selected join would add an orphan that ends in a period.
 -- Test the remaining adjacent sentences for other competing exact seams.
 SELECT count(*) INTO competing
 FROM jsonb_array_elements(sentence_tokens) WITH ORDINALITY AS x(s,n)
 CROSS JOIN LATERAL (SELECT sentence_tokens->((n-2)::integer)->(-1) AS tail) AS prev
 CROSS JOIN LATERAL (SELECT
   scope_start+(s#>>'{0,start}')::integer AS orphan_start,
   scope_start+(s#>>'{0,end}')::integer AS orphan_end,
   scope_start+(tail->>'start')::integer AS head_start,
   scope_start+(tail->>'end')::integer AS head_end) AS bounds
 WHERE n>1 AND jsonb_array_length(s)=1 AND s#>>'{0,text}' ~ '^[[:alpha:]][.]$'
  AND lower(tail->>'text') IN ('and','or') AND head_end+1=orphan_start
  AND substring(full_text FROM head_end+1 FOR 1)=' '
  AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_protected) AS q(span)
   WHERE (span->>0)::integer<orphan_end AND (span->>1)::integer>head_start)
  AND EXISTS(
   SELECT FROM jsonb_array_elements(p_projection->'pieces') AS q(p)
   CROSS JOIN jsonb_array_elements(p_projection->'pieces') AS l(p)
   CROSS JOIN jsonb_array_elements(p_projection->'pieces') AS r(p)
   WHERE q.p->>'kind'='native_text' AND q.p->>'source_field'='text'
    AND l.p->>'kind'='native_text' AND l.p->>'source_field'='text'
    AND r.p->>'kind'='native_text' AND r.p->>'source_field'='text'
    AND (q.p->>'start')::integer<=head_start AND (q.p->>'end')::integer=orphan_start
    AND (l.p->>'start')::integer=orphan_start AND (l.p->>'end')::integer=orphan_end-1
    AND (r.p->>'start')::integer=orphan_end-1 AND r.p->>'item_ref'<>l.p->>'item_ref'
  );
 IF (layout->>'outcome'='ambiguous' AND competing<2)
  OR (layout->>'outcome'<>'ambiguous' AND competing<>0) THEN
  RAISE EXCEPTION 'HanLP v2 layout did not preserve competing source seams' USING ERRCODE='23514';
 END IF;
 char_digest:=encode(sha256(convert_to(data.canonical_json(jsonb_build_object(
  'coordinate_space','pm2-provider-character-map-1','scope_digest',p_report->>'scope_digest',
  'provider_text',text_,'segments',map_->'segments','protected_atoms',atoms)),'UTF8')),'hex');
 map_digest:=encode(sha256(convert_to(data.canonical_json(jsonb_build_object(
  'character_map',char_digest,'tokens',tokens,'layout',layout)),'UTF8')),'hex');
 expected:=encode(sha256(convert_to(data.canonical_json(jsonb_build_object(
  'source_map',map_digest,'profile',p_startup,'source_path',NULL,
  'operation',jsonb_build_array('pm2.hanlp.frames','2'),
  'request',data.canonical_json(p_report->'request'))),'UTF8')),'hex');
 IF p_report->>'source_map_digest' IS DISTINCT FROM char_digest
  OR p_report->>'input_digest' IS DISTINCT FROM expected
  OR p_report->>'effective_profile_digest' IS DISTINCT FROM
   encode(sha256(convert_to(data.canonical_json(p_startup),'UTF8')),'hex') THEN
  RAISE EXCEPTION 'HanLP v2 report differs from its source, layout or runtime input identity'
   USING ERRCODE='23514'; END IF;
 RETURN sentence_tokens;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range OR invalid_parameter_value THEN
 RAISE EXCEPTION 'HanLP v2 report has malformed layout or token coordinates' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.hanlp_seam_source_tokens(jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_unique_child(arcs jsonb, p_head integer, p_role text)
RETURNS integer LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT CASE WHEN count(*)=1 THEN min(ord)::integer-1 END
 FROM jsonb_array_elements(arcs) WITH ORDINALITY AS a(arc,ord)
 WHERE (arc->>0)::integer=p_head+1 AND arc->>1=p_role
$$;
REVOKE ALL ON FUNCTION ops.hanlp_unique_child(jsonb,integer,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_srl_group(groups jsonb, p_predicate integer)
RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT CASE WHEN count(*)=1 THEN jsonb_agg(g)->0 END
 FROM jsonb_array_elements(groups) AS frames(g)
 WHERE (SELECT jsonb_agg(role->1) FROM jsonb_array_elements(g) AS r(role)
   WHERE role->>1='PRED')='["PRED"]'::jsonb
  AND EXISTS(SELECT FROM jsonb_array_elements(g) AS r(role)
   WHERE role->>1='PRED' AND (role->>2)::integer=p_predicate
   AND (role->>3)::integer=p_predicate+1)
$$;
REVOKE ALL ON FUNCTION ops.hanlp_srl_group(jsonb,integer) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_srl_spans(frame jsonb, p_role text)
RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT COALESCE(jsonb_agg(jsonb_build_array(role->2,role->3) ORDER BY n),'[]'::jsonb)
 FROM jsonb_array_elements(frame) WITH ORDINALITY AS r(role,n) WHERE role->>1=p_role
$$;
REVOKE ALL ON FUNCTION ops.hanlp_srl_spans(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_act_is_local(
 words jsonb, arcs jsonb, first_ integer, last_ integer, admitted_content jsonb
) RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT NOT EXISTS(
  SELECT FROM generate_series(first_,last_-1) AS idx(i)
  WHERE words->>i IN ('"',U&'\201C',U&'\201D',U&'\2018',U&'\2019','``',repeat(chr(39),2))
  OR (NOT EXISTS(SELECT FROM jsonb_array_elements(admitted_content) AS spans(span)
   WHERE i>=(span->>0)::integer AND i<(span->>1)::integer)
   AND (lower(words->>i) IN ('if','unless','although','except','not','never','reportedly','allegedly')
    OR arcs->i->>1 IN ('advcl','neg')))
 )
$$;
REVOKE ALL ON FUNCTION ops.hanlp_act_is_local(jsonb,jsonb,integer,integer,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_native_role_is_exact(
 p_projection jsonb, p_tokens jsonb, p_base integer, p_span jsonb
) RETURNS boolean LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE
 a integer:=(p_span->>0)::integer; b integer:=(p_span->>1)::integer;
 lo integer; hi integer; pieces integer;
BEGIN
 IF NOT COALESCE(a>=0 AND b>a AND b<=jsonb_array_length(p_tokens),false) THEN RETURN false; END IF;
 lo:=p_base+(p_tokens->a->>'start')::integer;
 hi:=p_base+(p_tokens->(b-1)->>'end')::integer;
 SELECT COALESCE(sum(least((p->>'end')::integer,hi)-greatest((p->>'start')::integer,lo)),0)
 INTO pieces FROM jsonb_array_elements(p_projection->'pieces') AS parts(p)
 WHERE p->>'kind'='native_text' AND p ? 'item_ref'
  AND (p->>'end')::integer>lo AND (p->>'start')::integer<hi;
 RETURN pieces=hi-lo;
END $$;
REVOKE ALL ON FUNCTION ops.hanlp_native_role_is_exact(jsonb,jsonb,integer,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_chain_intro(
 p_native jsonb, p_tokens jsonb, p_projection jsonb, p_base integer,
 p_sentence integer, p_intro integer, p_terminal integer, p_coordinated boolean
) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE
 words jsonb:=p_native->'tok'->p_sentence; arcs jsonb:=p_native->'dep'->p_sentence;
 lemmas jsonb:=p_native->'lem'->p_sentence; tags jsonb:=p_native->'pos'->p_sentence;
 groups jsonb:=p_native->'srl'->p_sentence;
 head_ integer; copula integer; subject_ integer; frame jsonb; roles jsonb; subject_span jsonb;
 coverage integer[];
BEGIN
 IF lower(btrim(lemmas->>p_intro)) IS DISTINCT FROM 'let'
  OR NOT COALESCE(CASE WHEN p_coordinated THEN arcs->p_intro->>1='conj'
   ELSE arcs->p_intro->>1 IN ('root','dep','parataxis') END,false) THEN RETURN NULL; END IF;
 head_:=ops.hanlp_unique_child(arcs,p_intro,'ccomp');
 copula:=ops.hanlp_unique_child(arcs,head_,'cop');
 subject_:=ops.hanlp_unique_child(arcs,head_,'nsubj');
 frame:=ops.hanlp_srl_group(groups,copula);
 subject_span:=jsonb_build_array(subject_,subject_+1);
 roles:=ops.hanlp_srl_spans(frame,'ARG2');
 IF subject_ IS DISTINCT FROM p_intro+1 OR copula IS DISTINCT FROM subject_+1
  OR COALESCE(words->>subject_,'') !~ '^[[:alpha:]_][[:alnum:]_]*$'
  OR COALESCE(tags->>subject_,'') NOT IN ('NN','NNS','NNP','NNPS')
  OR ops.hanlp_srl_spans(frame,'ARG1') IS DISTINCT FROM jsonb_build_array(subject_span)
  OR COALESCE(jsonb_array_length(roles),0)=0
  OR NOT ops.hanlp_native_role_is_exact(p_projection,p_tokens,p_base,subject_span)
  OR NOT ops.hanlp_native_role_is_exact(p_projection,p_tokens,p_base,jsonb_build_array(copula,copula+1))
  OR EXISTS(SELECT FROM jsonb_array_elements(roles) AS parts(span)
   WHERE NOT ops.hanlp_native_role_is_exact(p_projection,p_tokens,p_base,span))
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(roles) AS parts(span)
   WHERE (span->>0)::integer<=head_ AND head_<(span->>1)::integer)
  OR NOT ops.hanlp_act_is_local(words,arcs,p_intro,p_terminal,roles) THEN RETURN NULL; END IF;
 SELECT array_agg(i ORDER BY i) INTO coverage FROM jsonb_array_elements(roles) AS parts(span)
 CROSS JOIN LATERAL generate_series((span->>0)::integer,(span->>1)::integer-1) AS idx(i);
 IF coverage IS DISTINCT FROM ARRAY(SELECT generate_series(copula+1,p_terminal-1)) THEN RETURN NULL; END IF;
 RETURN jsonb_build_object('head',head_,'copula',copula,'subject',subject_,'word',words->>subject_);
END $$;
REVOKE ALL ON FUNCTION ops.hanlp_chain_intro(jsonb,jsonb,jsonb,integer,integer,integer,integer,boolean) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_exact_chain(
 p_report jsonb, p_projection jsonb, p_sentences jsonb, p_passage jsonb, p_reference jsonb
) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE
 n jsonb:=p_report#>'{native,native}'; scope_ integer:=(p_report#>>'{source_map,context_pieces,0,start}')::integer;
 start_ integer:=(p_passage->>'start')::integer; end_ integer:=(p_passage->>'end')::integer;
 text_ text:=p_projection->>'text'; passage_ text:=p_passage->>'passage_id';
 numbers integer[]; decl integer; construction integer; naming integer; a integer; b integer;
 s integer; i integer; j integer; k integer; hop integer; head_ integer; root_ integer; num integer;
 first_ integer; length_ integer; words jsonb; arcs jsonb; roles jsonb; frame jsonb; role_ jsonb; rendered text;
 token_rows jsonb; prepared_words jsonb; intros integer[]; introduction integer; intro jsonb;
 subject_ integer; constructed text; construct integer; relative_ integer; relative_frame jsonb; obj integer;
 bindings jsonb:='[]'; uses integer[]:='{}'; declared text[]:='{}'; reference_use integer; use_head integer;
 predicate_ integer; nominal integer; term_head integer; antecedent integer; term_a integer; term_b integer;
 subj_a integer; subj_b integer; label_end integer; content_start integer; content_end integer;
 term_start integer; term_end integer; scope_digest text:=p_report->>'scope_digest';
BEGIN
 IF p_report#>>'{native,outcome}' IS DISTINCT FROM 'succeeded'
  OR p_report#>>'{source_map,layout,outcome}' IS DISTINCT FROM 'repaired'
  OR NOT COALESCE(start_>=scope_ AND start_<end_ AND
   end_<= (p_report#>>'{source_map,context_pieces,0,end}')::integer,false)
  OR p_passage->>'text' IS DISTINCT FROM substring(text_ FROM start_+1 FOR end_-start_)
 THEN RETURN NULL; END IF;
 SELECT array_agg(ord::integer-1 ORDER BY ord) INTO numbers
 FROM jsonb_array_elements(p_sentences) WITH ORDINALITY AS tokens(sen,ord)
 WHERE scope_+(sen#>>'{0,start}')::integer<end_
 AND scope_+(sen->(-1)->>'end')::integer>start_
 AND scope_+(sen->(-1)->>'end')::integer<=end_;
 IF cardinality(numbers) IS DISTINCT FROM 3 OR numbers[2]<>numbers[1]+1
  OR numbers[3]<>numbers[2]+1 THEN RETURN NULL; END IF;
 decl:=numbers[1]; construction:=numbers[2]; naming:=numbers[3];
 FOREACH s IN ARRAY numbers LOOP
  words:=n->'tok'->s; arcs:=n->'dep'->s; num:=jsonb_array_length(words);
  prepared_words:=p_report#>'{native,preparation}'->s->'prepared_words';
  IF COALESCE(words->>-1,'')<>'.' OR num<4 OR num>512
   OR jsonb_array_length(arcs) IS DISTINCT FROM num
   OR jsonb_array_length(n->'lem'->s) IS DISTINCT FROM num
   OR jsonb_array_length(n->'pos'->s) IS DISTINCT FROM num
   OR jsonb_array_length(prepared_words) IS DISTINCT FROM num
   OR jsonb_typeof(n->'srl'->s) IS DISTINCT FROM 'array' THEN RETURN NULL; END IF;
  SELECT CASE WHEN count(*)=1 THEN min(ord)::integer-1 END INTO root_
  FROM jsonb_array_elements(arcs) WITH ORDINALITY AS dep(arc,ord)
  WHERE arc->>0='0' AND arc->>1='root';
  IF root_ IS NULL THEN RETURN NULL; END IF;
  FOR i IN 0..num-1 LOOP
   IF jsonb_array_length(arcs->i) IS DISTINCT FROM 2
    OR COALESCE(arcs->i->>0,'') !~ '^(0|[1-9][0-9]*)$'
    OR COALESCE(arcs->i->>1,'')=''
    OR ((arcs->i->>1='root') IS DISTINCT FROM (i=root_)) THEN RETURN NULL; END IF;
   j:=i;
   FOR hop IN 0..num-1 LOOP
    EXIT WHEN j=root_;
    j:=(arcs->j->>0)::integer-1;
    IF NOT COALESCE(j>=0 AND j<num,false) THEN RETURN NULL; END IF;
   END LOOP;
   IF j<>root_ THEN RETURN NULL; END IF;
  END LOOP;
  FOR frame IN SELECT value FROM jsonb_array_elements(n->'srl'->s) LOOP
   IF (SELECT count(*) FROM jsonb_array_elements(frame) AS x(role)
    WHERE role->>1='PRED')<>1 THEN RETURN NULL; END IF;
   FOR role_ IN SELECT value FROM jsonb_array_elements(frame) LOOP
    a:=(role_->>2)::integer; b:=(role_->>3)::integer;
    IF jsonb_array_length(role_) IS DISTINCT FROM 4
     OR NOT COALESCE(a>=0 AND a<b AND b<=num,false)
     OR COALESCE(role_->>1,'')='' THEN RETURN NULL; END IF;
    SELECT string_agg(prepared_words->>w,' ' ORDER BY w) INTO rendered
    FROM generate_series(a,b-1) AS x(w);
    IF rendered IS DISTINCT FROM role_->>0 THEN RETURN NULL; END IF;
   END LOOP;
  END LOOP;
 END LOOP;

 token_rows:=p_sentences->decl; words:=n->'tok'->decl; arcs:=n->'dep'->decl;
 length_:=jsonb_array_length(words);
 SELECT ord::integer-1 INTO first_ FROM jsonb_array_elements(token_rows) WITH ORDINALITY AS x(tok,ord)
 WHERE scope_+(tok->>'start')::integer=start_;
 IF NOT COALESCE(first_>=0 AND first_<length_-3,false)
  OR lower(words->>first_) IS DISTINCT FROM 'definition'
  OR COALESCE(words->>(first_+1),'') !~ '^[0-9]+([.][0-9]+)*$' THEN RETURN NULL; END IF;
 SELECT array_agg(idx ORDER BY idx) INTO intros FROM generate_series(first_+2,length_-1) AS x(idx)
 WHERE lower(btrim(n->'lem'->decl->>idx))='let';
 IF NOT COALESCE(cardinality(intros) BETWEEN 1 AND 4 AND intros[1]=first_+2,false)
  OR NOT COALESCE((arcs->(intros[1])->>0)::integer IN (0,first_+1),false) THEN RETURN NULL; END IF;
 label_end:=scope_+(token_rows->(first_+1)->>'end')::integer;
 content_start:=scope_+(token_rows->(intros[1])->>'start')::integer;
 FOR j IN 1..cardinality(intros) LOOP
  i:=intros[j]; b:=COALESCE(intros[j+1],length_-1);
  IF j>1 AND ((arcs->i->>0)::integer IS DISTINCT FROM intros[1]+1
   OR lower(words->>(i-1)) IS DISTINCT FROM 'and'
   OR arcs->(i-1)->>1 IS DISTINCT FROM 'cc') THEN RETURN NULL; END IF;
  WHILE b>i AND lower(words->>(b-1)) IN (',',';','and') LOOP b:=b-1; END LOOP;
  intro:=ops.hanlp_chain_intro(n,token_rows,p_projection,scope_,decl,i,b,j>1);
  IF intro IS NULL OR intro->>'word'=ANY(declared) THEN RETURN NULL; END IF;
  declared:=array_append(declared,intro->>'word');
  bindings:=bindings||jsonb_build_array(jsonb_build_object(
   'frame',format('s%s/predicate/%s',decl,intro->>'copula'),'subject_token',intro->'subject'));
 END LOOP;

 token_rows:=p_sentences->construction; words:=n->'tok'->construction; arcs:=n->'dep'->construction;
 intro:=ops.hanlp_chain_intro(n,token_rows,p_projection,scope_,construction,0,jsonb_array_length(words)-1,false);
 IF intro IS NULL OR arcs#>>'{0,0}' IS DISTINCT FROM '0' OR intro->>'word'=ANY(declared) THEN RETURN NULL; END IF;
 construct:=(intro->>'copula')::integer; subject_:=(intro->>'subject')::integer; constructed:=intro->>'word';
 relative_:=ops.hanlp_unique_child(arcs,(intro->>'head')::integer,'acl:relcl');
 relative_frame:=ops.hanlp_srl_group(n->'srl'->construction,relative_);
 obj:=ops.hanlp_unique_child(arcs,relative_,'obj');
 IF relative_frame IS NULL OR n->'pos'->construction->>relative_ !~ '^VB'
  OR NOT ops.hanlp_native_role_is_exact(p_projection,token_rows,scope_,jsonb_build_array(relative_,relative_+1))
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(ops.hanlp_srl_spans(relative_frame,'ARG1')) AS roles(r)
   WHERE (r->>0)::integer<=obj AND obj<(r->>1)::integer)
  OR EXISTS(SELECT FROM jsonb_array_elements(ops.hanlp_srl_spans(relative_frame,'ARG1')) AS roles(r)
   WHERE NOT ops.hanlp_native_role_is_exact(p_projection,token_rows,scope_,r))
 THEN RETURN NULL; END IF;
 FOR j IN 1..cardinality(declared) LOOP
  SELECT CASE WHEN count(*)=1 THEN min(ord)::integer-1 END INTO reference_use
  FROM jsonb_array_elements_text(words) WITH ORDINALITY AS x(word,ord) WHERE word=declared[j];
  IF reference_use IS NULL THEN RETURN NULL; END IF;
  k:=reference_use;
  LOOP
   k:=(arcs->k->>0)::integer-1;
   EXIT WHEN k=relative_ OR k<0;
  END LOOP;
  IF k<>relative_ THEN RETURN NULL; END IF;
  uses:=array_append(uses,reference_use);
  bindings:=jsonb_set(bindings,ARRAY[(j-1)::text,'use_token'],to_jsonb(reference_use));
 END LOOP;
 SELECT min(idx) INTO reference_use FROM unnest(uses) AS q(idx);
 use_head:=(arcs->reference_use->>0)::integer-1;
 IF arcs->reference_use->>1 IS DISTINCT FROM 'nmod' OR use_head<0
  OR arcs->use_head->>1 IS DISTINCT FROM 'obl'
  OR EXISTS(SELECT FROM unnest(uses) AS q(idx) WHERE idx<>reference_use
   AND (arcs->idx->>1 IS DISTINCT FROM 'conj' OR (arcs->idx->>0)::integer IS DISTINCT FROM reference_use+1))
 THEN RETURN NULL; END IF;

 token_rows:=p_sentences->naming; words:=n->'tok'->naming; arcs:=n->'dep'->naming;
 SELECT ord::integer-1 INTO predicate_ FROM jsonb_array_elements(arcs) WITH ORDINALITY AS dep(arc,ord)
 WHERE arc->>0='0';
 IF COALESCE(lower(btrim(n->'lem'->naming->>predicate_)),'') NOT IN ('call','name') THEN RETURN NULL; END IF;
 frame:=ops.hanlp_srl_group(n->'srl'->naming,predicate_);
 nominal:=ops.hanlp_unique_child(arcs,predicate_,'nsubj:pass');
 term_head:=ops.hanlp_unique_child(arcs,predicate_,'xcomp');
 antecedent:=ops.hanlp_unique_child(arcs,nominal,'nmod');
 IF frame IS NULL OR ops.hanlp_unique_child(arcs,predicate_,'aux:pass') IS NULL
  OR words->>antecedent IS DISTINCT FROM constructed
  OR (SELECT count(*) FROM jsonb_array_elements_text(words) AS x(word) WHERE word=constructed)<>1
  OR lower(words->>ops.hanlp_unique_child(arcs,antecedent,'case')) IS DISTINCT FROM 'of'
  OR NOT ops.hanlp_native_role_is_exact(p_projection,token_rows,scope_,jsonb_build_array(predicate_,predicate_+1))
  OR jsonb_array_length(ops.hanlp_srl_spans(frame,'ARG1')) IS DISTINCT FROM 1
  OR jsonb_array_length(ops.hanlp_srl_spans(frame,'ARG2')) IS DISTINCT FROM 1
  OR EXISTS(SELECT FROM jsonb_array_elements(frame) AS x(role) WHERE role->>1 LIKE 'ARGM-%' AND role->>1<>'ARGM-DIS')
  OR NOT ops.hanlp_act_is_local(words,arcs,0,jsonb_array_length(words)-1,'[]') THEN RETURN NULL; END IF;
 roles:=ops.hanlp_srl_spans(frame,'ARG1')->0;
 IF NOT ops.hanlp_native_role_is_exact(p_projection,token_rows,scope_,roles) THEN RETURN NULL; END IF;
 subj_a:=(roles->>0)::integer; subj_b:=(roles->>1)::integer;
 roles:=ops.hanlp_srl_spans(frame,'ARG2')->0;
 IF NOT ops.hanlp_native_role_is_exact(p_projection,token_rows,scope_,roles) THEN RETURN NULL; END IF;
 term_a:=(roles->>0)::integer; term_b:=(roles->>1)::integer;
 IF NOT COALESCE(subj_a<=nominal AND nominal<antecedent AND antecedent<subj_b
  AND subj_b<=predicate_ AND predicate_<term_a AND term_a<=term_head AND term_head<term_b
  AND term_b=jsonb_array_length(words)-1,false)
  OR EXISTS(SELECT FROM generate_series(0,subj_a-1) AS q(idx)
   WHERE lower(words->>idx) IS DISTINCT FROM 'then')
  OR EXISTS(SELECT FROM generate_series(subj_b,predicate_-1) AS q(idx)
   WHERE arcs->idx->>1 IS DISTINCT FROM 'aux:pass') THEN RETURN NULL; END IF;
 IF arcs->term_a->>1='det' AND (arcs->term_a->>0)::integer=term_head+1 THEN term_a:=term_a+1; END IF;
 term_start:=scope_+(token_rows->term_a->>'start')::integer;
 term_end:=scope_+(token_rows->(term_b-1)->>'end')::integer;
 content_end:=scope_+(token_rows->(subj_b-1)->>'end')::integer;
 IF NOT COALESCE(start_<label_end AND label_end<content_start AND content_start<content_end
  AND content_end<term_start AND term_start<term_end AND term_end<=end_,false) THEN RETURN NULL; END IF;
 RETURN jsonb_build_object(
  'term',jsonb_build_object('passage_id',passage_,'start',term_start,'end',term_end,
   'text',substring(text_ FROM term_start+1 FOR term_end-term_start)),
  'content',jsonb_build_object('passage_id',passage_,'start',content_start,'end',content_end,
   'text',substring(text_ FROM content_start+1 FOR content_end-content_start)),
  'declaration_chain',jsonb_build_object('version','definition-declaration-chain-1','parser',p_reference,
   'scope_digest',scope_digest,'bindings',bindings,'construction_frame',format('s%s/predicate/%s',construction,construct),
   'construction_subject_token',subject_,'naming_frame',format('s%s/predicate/%s',naming,predicate_),
   'naming_antecedent_token',antecedent,'label',jsonb_build_object('passage_id',passage_,'start',start_,
    'end',label_end,'text',substring(text_ FROM start_+1 FOR label_end-start_))));
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range OR invalid_parameter_value THEN
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION ops.hanlp_exact_chain(jsonb,jsonb,jsonb,jsonb,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_hanlp_v2_report(p_task bigint,p_envelope jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE
 t ops.task; v kb.source_view; r ops.run; startup jsonb; config_ jsonb; report_ jsonb; operation_ jsonb;
 source_ jsonb; slice_ jsonb; extent_ jsonb; atoms jsonb; outcome_ text; expected text;
BEGIN
 SELECT * INTO STRICT t FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=t.unit_id;
 SELECT * INTO STRICT r FROM ops.run WHERE id=t.run_id;
 SELECT cfg.params INTO STRICT config_
 FROM ops.method_config cfg JOIN ops.method m ON m.id=cfg.method_id
 WHERE cfg.id=t.method_config_id AND m.name='extract.pm2_hanlp' AND m.version='2';
 startup:=config_->'startup';
 report_:=data.record_source_json(p_envelope->'parse_detail')->'pm2_native';
 slice_:=report_#>'{source_map,context_pieces,0}';
 extent_:=jsonb_build_array(slice_->'start',slice_->'end');
 operation_:=p_envelope->'contribution_operations'->0;
 outcome_:=report_#>>'{native,outcome}';
 IF NOT ops.private_declaration_enabled(t.release_id)
  OR config_->>'provider' IS DISTINCT FROM 'hanlp'
  OR config_->>'layout_policy' IS DISTINCT FROM 'source-seam-continuation-1'
  OR startup->>'provider' IS DISTINCT FROM 'hanlp'
  OR jsonb_typeof(startup) IS DISTINCT FROM 'object'
  OR p_envelope->>'method' IS DISTINCT FROM 'extract.pm2_hanlp'
  OR p_envelope->>'operation_version' IS DISTINCT FROM '2'
  OR p_envelope->>'source' IS DISTINCT FROM v.key
  OR p_envelope->>'release_id' IS DISTINCT FROM t.release_id
  OR p_envelope->>'input_hash' IS DISTINCT FROM t.input_hash
  OR report_->>'input_digest' IS DISTINCT FROM t.input_hash
  OR slice_->'source_view_id' IS DISTINCT FROM to_jsonb(v.id)
  OR jsonb_array_length(p_envelope->'contribution_operations') IS DISTINCT FROM 1
  OR operation_->>'question' IS DISTINCT FROM 'pm2.hanlp.frames'
  OR operation_->>'operation_version' IS DISTINCT FROM '2'
  OR operation_->>'outcome' IS DISTINCT FROM outcome_
  OR COALESCE(outcome_,'') NOT IN ('succeeded','empty','limited','failed')
  OR operation_->'computation_dependencies' IS DISTINCT FROM jsonb_build_array(t.input_hash)
  OR operation_->>'report_digest' IS DISTINCT FROM
   encode(sha256(convert_to(data.canonical_json(report_),'UTF8')),'hex') THEN
  RAISE EXCEPTION 'HanLP v2 report differs from its registered release, operation or input'
   USING ERRCODE='23514'; END IF;
 expected:='contribution-operation:'||encode(sha256(convert_to(data.canonical_json(
  jsonb_build_array(jsonb_build_array('pm2.hanlp.frames','2',t.unit_key,t.input_hash),
  '{}'::jsonb)),'UTF8')),'hex');
 IF operation_->>'operation_key' IS DISTINCT FROM expected OR NOT EXISTS(
  SELECT FROM jsonb_array_elements(r.options->'pm2_scope_intents') AS intents(x)
  WHERE x->'source_view_id'=to_jsonb(v.id) AND x->'extent'=extent_ AND x->>'disposition'='scheduled'
  AND x->>'question'='pm2.hanlp.frames' AND x->>'operation_version'='2'
  AND x->>'input_digest'=t.input_hash AND nullif(x->'parent_input_digest','null') IS NULL)
 THEN RAISE EXCEPTION 'HanLP v2 report lacks its exact admitted worklist item' USING ERRCODE='23514'; END IF;
 SELECT DISTINCT x->'source' INTO STRICT source_
 FROM jsonb_array_elements(r.options->'parser_scopes') AS scopes(x)
 WHERE x->'extent'=extent_ AND x#>'{source,source_view_id}'=to_jsonb(v.id)
  AND x->>'layout_policy'='source-seam-continuation-1' AND x->>'mode'='ordinary'
  AND x->'schedule'='true'::jsonb AND x->'supplied'='[]'::jsonb;
 PERFORM ops.validate_structural_source(source_);
 IF source_->>'project_id' IS DISTINCT FROM r.project_id THEN
  RAISE EXCEPTION 'HanLP v2 report source differs from its admitted project' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_array(p->'start',p->'end') ORDER BY (p->>'start')::integer),
  '[]'::jsonb) INTO atoms
 FROM jsonb_array_elements(v.projection->'pieces') AS pieces(p)
 JOIN kb.pdf_record_access a ON a.product_id=v.native_build_id AND a.revision_id=v.native_revision_id
  AND a.pointer=p->>'item_ref' AND a.label='formula'
 WHERE (p->>'end')::integer>(slice_->>'start')::integer
  AND (p->>'start')::integer<(slice_->>'end')::integer;
 RETURN ops.hanlp_seam_source_tokens(report_,v.projection,atoms,startup);
EXCEPTION WHEN no_data_found OR too_many_rows OR invalid_text_representation OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'HanLP v2 report cannot resolve its immutable source and profile' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_hanlp_v2_report(bigint,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.hanlp_cited_frame_matches(
 p_rows jsonb,p_report jsonb,p_frame text,p_operation text,p_pin jsonb
) RETURNS boolean LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE
 coordinates text[]; sentence_ integer; predicate_ integer; head_ integer; value_ jsonb; row_ jsonb;
 native_ jsonb:=p_report#>'{native,native}'; arcs jsonb; srl jsonb; expected jsonb; location_ text;
BEGIN
 coordinates:=regexp_match(p_frame,'^s([0-9]+)/predicate/([0-9]+)$');
 IF coordinates IS NULL THEN RETURN false; END IF;
 sentence_:=coordinates[1]::integer; predicate_:=coordinates[2]::integer;
 SELECT r INTO STRICT row_ FROM jsonb_array_elements(p_rows) AS rows(r)
 WHERE r->>'item_key'=p_frame AND r->>'operation_key'=p_operation AND r->'pin'=p_pin
  AND r->>'semantic_type'='linguistic.predicate_frame' AND r->>'contract'='PM2HanLPFrameContributionV1';
 value_:=data.record_source_json(row_->'value');
 arcs:=native_->'dep'->sentence_;
 head_:=CASE WHEN arcs->predicate_->>1='cop' THEN (arcs->predicate_->>0)::integer-1 ELSE predicate_ END;
 srl:=ops.hanlp_srl_group(native_->'srl'->sentence_,predicate_);
 location_:=format('s%s/span/%s-%s',sentence_,predicate_,predicate_+1);
 SELECT jsonb_build_array(jsonb_build_object('predicate',location_,'arguments',
  COALESCE(jsonb_agg(jsonb_build_object('role',role->>1,'location',
    format('s%s/span/%s-%s',sentence_,role->>2,role->>3)) ORDER BY ord),'[]')))
 INTO expected FROM jsonb_array_elements(srl) WITH ORDINALITY AS roles(role,ord)
 WHERE role->>1<>'PRED';
 RETURN (srl IS NOT NULL
  AND value_->'sentence'=to_jsonb(sentence_) AND value_->'predicate_token'=to_jsonb(predicate_)
  AND value_->'syntactic_head'=to_jsonb(head_) AND value_->>'predicate'=location_
  AND value_->>'scheme'='hanlp-ud-ptb-propbank-1'
  AND value_->>'voice'=(CASE WHEN head_<>predicate_ THEN 'copular' ELSE 'passive' END)
  AND value_->'srl_frames'=expected
  AND EXISTS(SELECT FROM jsonb_array_elements(p_rows) AS rows(r)
   WHERE r->>'item_key'=location_ AND r->>'kind'='occurrence' AND r->'pin'=p_pin
    AND r->>'operation_key'=p_operation AND row_->'members' ? (r->>'contribution_id'))
  AND NOT EXISTS(
   SELECT FROM jsonb_array_elements(expected#>'{0,arguments}') AS roles(arg)
   WHERE arg->>'role' IN ('ARG1','ARG2') AND NOT EXISTS(
    SELECT FROM jsonb_array_elements(p_rows) AS rows(r)
    WHERE r->>'item_key'=arg->>'location' AND r->>'kind'='occurrence' AND r->'pin'=p_pin
     AND r->>'operation_key'=p_operation AND row_->'members' ? (r->>'contribution_id')
   ))) IS TRUE;
EXCEPTION WHEN no_data_found OR too_many_rows OR invalid_text_representation OR numeric_value_out_of_range THEN
 RETURN false;
END $$;
REVOKE ALL ON FUNCTION ops.hanlp_cited_frame_matches(jsonb,jsonb,text,text,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.validate_declaration_chain_component(
 component jsonb, p_passage jsonb, p_source jsonb, p_config jsonb, p_release text
) RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE
 proof jsonb:=component->'declaration_chain'; ref jsonb:=proof->'parser'; retained jsonb; root_ jsonb;
 original jsonb; report_ jsonb; tokens jsonb; expected jsonb; item text; v kb.source_view;
 operation_ text; frame_pin jsonb;
BEGIN
 IF NOT ops.private_declaration_enabled(p_release)
  OR component->>'basis' IS DISTINCT FROM 'declaration_chain'
  OR component->>'interpretation' IS DISTINCT FROM 'definition'
  OR nullif(component->'witness','null') IS NOT NULL
  OR proof->>'version' IS DISTINCT FROM 'definition-declaration-chain-1'
  OR p_source->>'project_id' IS DISTINCT FROM ref->>'project_id'
  OR p_release IS DISTINCT FROM ref->>'release_id'
  OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_config->'selections') AS selections(x)
   WHERE x->>'passage_id'=p_passage->>'passage_id' AND x->'parser'=ref)
  OR component->'evidence' IS DISTINCT FROM jsonb_build_array(p_passage->>'passage_id')
  OR component->'alternatives' IS DISTINCT FROM '[]'::jsonb
  OR component->>'reason' IS DISTINCT FROM 'The definition joins exact introduced roles to their local uses and naming.'
 THEN RAISE EXCEPTION 'declaration chain differs from its exact released source and selection' USING ERRCODE='23514'; END IF;
 retained:=ops.resolve_retained_source_contribution(ref);
 SELECT r INTO STRICT root_ FROM jsonb_array_elements(retained->'contributions') AS rows(r)
 WHERE r->>'contribution_id'=ref->>'contribution_id' AND r->>'semantic_type'='linguistic.predicate_frame';
 SELECT * INTO STRICT v FROM kb.source_view WHERE id=(p_source->>'source_view_id')::bigint;
 IF root_#>'{pin,source_view_id}' IS DISTINCT FROM to_jsonb(v.id)
  OR root_->>'item_key' IS DISTINCT FROM proof->>'naming_frame' THEN
  RAISE EXCEPTION 'declaration witness names a different retained predicate' USING ERRCODE='23514'; END IF;
 SELECT body INTO STRICT original FROM ops.task_result WHERE task_id=(ref->>'origin_task_id')::bigint;
 tokens:=ops.validate_hanlp_v2_report((ref->>'origin_task_id')::bigint,original);
 report_:=data.record_source_json(original->'parse_detail')->'pm2_native';
 expected:=ops.hanlp_exact_chain(report_,v.projection,tokens,p_passage,ref);
 IF expected IS DISTINCT FROM jsonb_build_object('term',component->'term','content',component->'content',
  'declaration_chain',proof) THEN
  RAISE EXCEPTION 'declaration component differs from the exact native role chain' USING ERRCODE='23514'; END IF;
 operation_:=root_->>'operation_key'; frame_pin:=root_->'pin';
 FOR item IN SELECT proof->>'naming_frame' UNION ALL SELECT proof->>'construction_frame'
  UNION ALL SELECT binding->>'frame' FROM jsonb_array_elements(proof->'bindings') AS x(binding) LOOP
  IF NOT ops.hanlp_cited_frame_matches(original->'contributions',report_,item,operation_,frame_pin) THEN
   RAISE EXCEPTION 'declaration witness lacks its exact original typed parser frame' USING ERRCODE='23514'; END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows OR invalid_text_representation OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'declaration witness cannot resolve the exact retained parser origin' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.validate_declaration_chain_component(jsonb,jsonb,jsonb,jsonb,text) FROM PUBLIC;
