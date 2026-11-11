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
