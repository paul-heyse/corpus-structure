-- pdf-publication-records-v2 over the pdf-record-sha256-fold-v1 algorithm.
-- Only bounded per-record arrays are constructed; the ordered relation cursor spills normally.
CREATE OR REPLACE FUNCTION ops.pdf_identity_inline(p_value jsonb)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE kind_ text:=jsonb_typeof(p_value); payload_ bytea;
BEGIN
 CASE kind_
 WHEN 'null' THEN RETURN ops.pdf_identity_scalar('n',''::bytea);
 WHEN 'boolean' THEN RETURN ops.pdf_identity_scalar('b',CASE WHEN p_value='true'::jsonb THEN decode('01','hex') ELSE decode('00','hex') END);
 WHEN 'string' THEN RETURN ops.pdf_identity_scalar('s',convert_to(p_value#>>'{}','UTF8'));
 WHEN 'number' THEN RETURN ops.pdf_identity_scalar('i',convert_to(p_value::text,'UTF8'));
 WHEN 'object' THEN
  IF (SELECT count(*) FROM jsonb_object_keys(p_value))<>1 OR
     NOT p_value ? 'native_float64' OR (p_value->>'native_float64') !~ '^[0-9a-f]{16}$' THEN
   RAISE EXCEPTION 'invalid native binary64 inline representation' USING ERRCODE='23514';
  END IF;
  RETURN ops.pdf_identity_scalar('f',decode(p_value->>'native_float64','hex'));
 ELSE RAISE EXCEPTION 'unsupported inline scalar kind %',kind_ USING ERRCODE='23514';
 END CASE;
END $$;

-- Match Python ensure_ascii=True string spelling used by native membership keys.
CREATE OR REPLACE FUNCTION ops.pdf_identity_ascii_string(p_text text)
RETURNS text LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE out_ text:='"'; c_ text; n_ integer; i_ integer;
BEGIN
 -- PostgreSQL's JSON encoder already has exactly the required spelling for
 -- printable ASCII identifiers. Keep ensure_ascii handling below for all other text.
 IF p_text COLLATE "C" !~ '[^ -~]' THEN RETURN to_jsonb(p_text)::text; END IF;
 FOR i_ IN 1..char_length(p_text) LOOP
  c_:=substr(p_text,i_,1); n_:=ascii(c_);
  IF n_=34 THEN out_:=out_||chr(92)||'"';
  ELSIF n_=92 THEN out_:=out_||chr(92)||chr(92);
  ELSIF n_=8 THEN out_:=out_||chr(92)||'b';
  ELSIF n_=9 THEN out_:=out_||chr(92)||'t';
  ELSIF n_=10 THEN out_:=out_||chr(92)||'n';
  ELSIF n_=12 THEN out_:=out_||chr(92)||'f';
  ELSIF n_=13 THEN out_:=out_||chr(92)||'r';
  ELSIF n_<32 OR n_>126 THEN
   IF n_<=65535 THEN out_:=out_||chr(92)||'u'||lpad(to_hex(n_),4,'0');
   ELSE
    n_:=n_-65536;
    out_:=out_||chr(92)||'u'||to_hex(55296+n_/1024)||chr(92)||'u'||to_hex(56320+n_%1024);
   END IF;
  ELSE out_:=out_||c_;
  END IF;
 END LOOP;
 RETURN out_||'"';
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_stream_scalar(p_product text,p_revision text,p_stream text)
RETURNS bytea LANGUAGE plpgsql STABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE stream_ ops.pdf_artifact_stream; kind_ text;
BEGIN
 SELECT * INTO STRICT stream_ FROM ops.pdf_artifact_stream
 WHERE product_id=p_product AND revision_id=p_revision AND stream_id=p_stream;
 -- Descriptor algebra only: the complete identity entry verifies every immutable
 -- stream once before evaluating any record, including shared/unreferenced streams.
 IF stream_.encoding_profile IN ('pdf-record-native-json-v1','pdf-companion-json-field-v1') THEN kind_:='y';
 ELSIF stream_.encoding_profile ~ '^pdf-record-scalar-v1:[anbifsyd]$' THEN
  kind_:=right(stream_.encoding_profile,1);
 ELSE RAISE EXCEPTION 'stream is not a native scalar profile' USING ERRCODE='23514'; END IF;
 RETURN convert_to(kind_,'UTF8')||int8send(stream_.byte_length)||decode(stream_.byte_root,'hex');
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_companion_scalar(
 p_product text,p_revision text,p_family text,p_local text,p_field text,p_body jsonb)
RETURNS bytea LANGUAGE plpgsql STABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE field_ kb.pdf_record_companion_field; stream_ ops.pdf_artifact_stream;
BEGIN
 SELECT * INTO field_ FROM kb.pdf_record_companion_field WHERE product_id=p_product
 AND revision_id=p_revision AND family=p_family AND local_id=p_local AND field_name=p_field;
 IF FOUND THEN
  IF p_body ? p_field THEN RAISE EXCEPTION 'companion field has competing inline and external values' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT stream_ FROM ops.pdf_artifact_stream WHERE product_id=p_product
   AND revision_id=p_revision AND stream_id=field_.stream_id;
  IF p_field='value' AND p_family='native_metadata' AND
   p_body->>'kind'='{pdf_payload_family}' THEN
   IF field_.scalar_kind<>'y' OR stream_.encoding_profile<>'{pdf_payload_profile}'
    OR p_body->>'payload_codec' IS DISTINCT FROM stream_.encoding_profile
    OR COALESCE(p_body->>'payload_logical_digest','') !~ '^[0-9a-f]{64}$'
    OR COALESCE(p_body->>'payload_schema_digest','') !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'structured companion identity profile differs' USING ERRCODE='23514';
   END IF;
   -- Physical custody is frozen separately; this digest is trusted only after the
   -- released validation callback recomputes it from decoded typed page values.
   RETURN convert_to('y','UTF8')||int8send(32::bigint)||
    sha256(convert_to('pdf-ocr-candidate-logical-v1','UTF8')||
     decode(p_body->>'payload_logical_digest','hex'));
  END IF;
  IF (p_field='value' AND (p_family<>'native_metadata' OR field_.scalar_kind<>'y'
    OR stream_.encoding_profile<>'pdf-companion-json-field-v1'))
   OR (p_field='text' AND (p_family<>'occurrence' OR field_.scalar_kind<>'s'
    OR stream_.encoding_profile<>'pdf-record-scalar-v1:s')) THEN
   RAISE EXCEPTION 'companion field profile differs' USING ERRCODE='23514';
  END IF;
  RETURN ops.pdf_identity_stream_scalar(p_product,p_revision,field_.stream_id);
 END IF;
 IF p_family='native_metadata' THEN
  RAISE EXCEPTION 'metadata value requires its declared JSON byte stream' USING ERRCODE='23514';
 END IF;
 IF NOT p_body ? p_field THEN RETURN ops.pdf_identity_scalar('a',''::bytea); END IF;
 IF jsonb_typeof(p_body->p_field) NOT IN ('null','string') THEN
  RAISE EXCEPTION 'occurrence text must be string or null' USING ERRCODE='23514'; END IF;
 RETURN ops.pdf_identity_inline(p_body->p_field);
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_record_logical_identity(p_product text,p_revision text)
RETURNS text LANGUAGE plpgsql STABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE header_ ops.pdf_record_document; row_ record; node_ kb.pdf_record_native;
 member_ kb.pdf_record_membership; stream_ record; field_ text; descriptor_ jsonb;
 names_ text[]; values_ bytea[]; frame_ bytea; key_ text; key_scalar_ bytea;
 state_ bytea:=ops.pdf_identity_fold_start('records'); count_ bigint:=0; length_ bigint:=0;
BEGIN
 SELECT * INTO STRICT header_ FROM ops.pdf_record_document WHERE product_id=p_product AND revision_id=p_revision;
 -- This is the self-validating entry point. Private scalar helpers consume only
 -- the descriptors covered by this complete pass, never a caller-supplied bypass.
 FOR stream_ IN SELECT stream_id FROM ops.pdf_artifact_stream
 WHERE product_id=p_product AND revision_id=p_revision LOOP
  PERFORM ops.pdf_identity_verify_artifact(p_product,p_revision,stream_.stream_id);
 END LOOP;
 frame_:=ops.pdf_identity_record_frame(header_.native_schema_digest,'@context','@context',
 ARRAY['protocol','release','source'],ARRAY[
 ops.pdf_identity_scalar('s',convert_to('pdf-record-sha256-fold-v1','UTF8')),
 ops.pdf_identity_scalar('s',convert_to(header_.release_id,'UTF8')),
 ops.pdf_identity_scalar('s',convert_to(header_.source_digest,'UTF8'))]);
 state_:=ops.pdf_identity_fold_step(state_,count_,frame_); count_:=count_+1; length_:=length_+octet_length(frame_);
 FOR row_ IN
  SELECT * FROM (SELECT 'companion/'||c.family AS family,c.local_id AS key, NULL::text AS parent_key,NULL::text AS field_key,NULL::bigint AS ordinal_key FROM kb.pdf_record_companion c
   WHERE c.product_id=p_product AND c.revision_id=p_revision
  UNION ALL SELECT 'document','root',NULL,NULL,NULL
  UNION ALL SELECT 'endpoint','['||ops.pdf_identity_ascii_string(e.relation_id)||','||e.ordinal::text||']',e.relation_id,NULL,e.ordinal
   FROM kb.pdf_record_endpoint e WHERE e.product_id=p_product AND e.revision_id=p_revision
  UNION ALL SELECT 'membership','['||ops.pdf_identity_ascii_string(m.parent_id)||','||
   ops.pdf_identity_ascii_string(m.field_name)||','||CASE
    WHEN m.member_key IS NOT NULL THEN ops.pdf_identity_ascii_string(encode(ops.pdf_identity_scalar('s',convert_to(m.member_key,'UTF8')),'hex'))
    WHEN m.member_key_stream_id IS NOT NULL THEN ops.pdf_identity_ascii_string(encode(ops.pdf_identity_stream_scalar(p_product,p_revision,m.member_key_stream_id),'hex'))
    ELSE m.ordinal::text END||']',m.parent_id,m.field_name,m.ordinal
   FROM kb.pdf_record_membership m WHERE m.product_id=p_product AND m.revision_id=p_revision
  UNION ALL SELECT 'native',n.record_id,NULL,NULL,NULL FROM kb.pdf_record_native n WHERE n.product_id=p_product AND n.revision_id=p_revision
  UNION ALL SELECT 'publication','root',NULL,NULL,NULL
  ) ordered_ ORDER BY family COLLATE "C",key COLLATE "C"
 LOOP
  names_:=ARRAY[]::text[]; values_:=ARRAY[]::bytea[];
  IF row_.family='publication' THEN
   names_:=ARRAY['kind','recipe_digest'];
   SELECT ARRAY[ops.pdf_identity_scalar('s',convert_to(f.kind,'UTF8')),ops.pdf_identity_scalar('s',convert_to(b.recipe_digest,'UTF8'))] INTO STRICT values_
    FROM ops.pdf_frozen_build f JOIN ops.pdf_stage_build b USING(build_id) WHERE f.build_id=p_product;
  ELSIF row_.family='document' THEN
   names_:=ARRAY['mapping_profile','contract_version','native_schema_digest','root_id'];
   values_:=ARRAY[ops.pdf_identity_scalar('s',convert_to(header_.mapping_profile,'UTF8')),
    ops.pdf_identity_scalar('s',convert_to(header_.contract_version,'UTF8')),
    ops.pdf_identity_scalar('s',convert_to(header_.native_schema_digest,'UTF8')),
    ops.pdf_identity_scalar('s',convert_to(header_.root_id,'UTF8'))];
  ELSIF row_.family='native' THEN
   SELECT * INTO STRICT node_ FROM kb.pdf_record_native WHERE product_id=p_product AND revision_id=p_revision AND record_id=row_.key;
   names_:=ARRAY['native_type','family'];
   values_:=ARRAY[ops.pdf_identity_scalar('s',convert_to(node_.native_type,'UTF8')),ops.pdf_identity_scalar('s',convert_to(node_.family,'UTF8'))];
   FOR field_ IN SELECT k FROM (SELECT jsonb_object_keys(node_.scalars_json) k UNION SELECT jsonb_object_keys(node_.structure_json->'fields')) keys_ ORDER BY k COLLATE "C" LOOP
    IF node_.scalars_json ? field_ THEN
     names_:=array_append(names_,field_||'/value'); values_:=array_append(values_,ops.pdf_identity_inline(node_.scalars_json->field_));
    ELSE
     descriptor_:=node_.structure_json->'fields'->field_;
     IF descriptor_->>'kind'='parts' THEN
      names_:=array_append(names_,field_||'/value'); values_:=array_append(values_,ops.pdf_identity_stream_scalar(p_product,p_revision,descriptor_->>'stream_id'));
     ELSE
      names_:=array_append(names_,field_||'/kind'); values_:=array_append(values_,ops.pdf_identity_scalar('s',convert_to(descriptor_->>'kind','UTF8')));
      IF descriptor_->>'kind'='object' THEN
       names_:=array_append(names_,field_||'/target'); values_:=array_append(values_,ops.pdf_identity_scalar('s',convert_to(descriptor_->>'target','UTF8')));
      ELSE
       names_:=array_append(names_,field_||'/length'); values_:=array_append(values_,ops.pdf_identity_scalar('i',convert_to(descriptor_->>'length','UTF8')));
      END IF;
     END IF;
    END IF;
   END LOOP;
   IF node_.structure_json ? 'extensions' THEN
    names_:=array_append(names_,'@extensions'); values_:=array_append(values_,ops.pdf_identity_stream_scalar(p_product,p_revision,node_.structure_json->'extensions'->>'stream_id'));
   END IF;
  ELSIF row_.family='membership' THEN
   -- Key lookup derives from the already ordered cursor and uses the PK, never scans per parent.
   SELECT * INTO STRICT member_ FROM kb.pdf_record_membership m WHERE product_id=p_product AND revision_id=p_revision
    AND m.parent_id=row_.parent_key AND m.field_name=row_.field_key AND m.ordinal=row_.ordinal_key;
   names_:=ARRAY['parent_id','field_name']; values_:=ARRAY[ops.pdf_identity_scalar('s',convert_to(member_.parent_id,'UTF8')),ops.pdf_identity_scalar('s',convert_to(member_.field_name,'UTF8'))];
   IF member_.member_key IS NOT NULL OR member_.member_key_stream_id IS NOT NULL THEN
    names_:=array_append(names_,'member_key');
    key_scalar_:=CASE WHEN member_.member_key IS NOT NULL THEN ops.pdf_identity_scalar('s',convert_to(member_.member_key,'UTF8')) ELSE ops.pdf_identity_stream_scalar(p_product,p_revision,member_.member_key_stream_id) END;
    values_:=array_append(values_,key_scalar_);
   ELSE names_:=array_append(names_,'ordinal'); values_:=array_append(values_,ops.pdf_identity_scalar('i',convert_to(member_.ordinal::text,'UTF8'))); END IF;
   IF member_.value_kind='record' THEN
    names_:=array_append(names_,'target'); values_:=array_append(values_,ops.pdf_identity_scalar('s',convert_to(member_.record_id,'UTF8')));
   ELSE
    names_:=array_append(names_,'value'); values_:=array_append(values_,CASE WHEN member_.value_kind='scalar' THEN ops.pdf_identity_inline(member_.scalar_json) ELSE ops.pdf_identity_stream_scalar(p_product,p_revision,member_.stream_id) END);
   END IF;
  ELSIF left(row_.family,10)='companion/' THEN
   names_:=ARRAY['body','ordinal']; SELECT ARRAY[ops.pdf_identity_scalar('s',convert_to(data.canonical_json(CASE WHEN c.family='native_metadata' AND c.body->>'kind'='{pdf_payload_family}' THEN c.body-ARRAY['value','payload_codec','payload_schema_digest'] WHEN c.family='native_metadata' THEN c.body-'value' WHEN c.family='occurrence' THEN c.body-'text' ELSE c.body END),'UTF8')),ops.pdf_identity_scalar('i',convert_to(c.ordinal::text,'UTF8'))] INTO values_ FROM kb.pdf_record_companion c
    WHERE c.product_id=p_product AND c.revision_id=p_revision AND c.family=substr(row_.family,11) AND c.local_id=row_.key;
   IF row_.family IN ('companion/native_metadata','companion/occurrence') THEN
    field_:=CASE WHEN row_.family='companion/native_metadata' THEN 'value' ELSE 'text' END;
    names_:=array_append(names_,field_);
    SELECT array_append(values_,ops.pdf_identity_companion_scalar(p_product,p_revision,c.family,c.local_id,field_,c.body))
     INTO values_ FROM kb.pdf_record_companion c WHERE c.product_id=p_product AND c.revision_id=p_revision
     AND c.family=substr(row_.family,11) AND c.local_id=row_.key;
   END IF;

  ELSIF row_.family='endpoint' THEN
   names_:=ARRAY['relation_id','ordinal','target_task_id','target_product_key','target_content_digest','occurrence_id','role'];
   SELECT ARRAY[ops.pdf_identity_scalar('s',convert_to(e.relation_id,'UTF8')),ops.pdf_identity_scalar('i',convert_to(e.ordinal::text,'UTF8')),
    ops.pdf_identity_scalar('i',convert_to(e.target_task_id::text,'UTF8')),ops.pdf_identity_scalar('s',convert_to(e.target_product_key,'UTF8')),
    ops.pdf_identity_scalar('s',convert_to(e.target_content_digest,'UTF8')),ops.pdf_identity_scalar('s',convert_to(e.occurrence_id,'UTF8')),ops.pdf_identity_scalar('s',convert_to(e.role,'UTF8'))] INTO values_
    FROM kb.pdf_record_endpoint e WHERE e.product_id=p_product AND e.revision_id=p_revision AND e.relation_id=row_.parent_key AND e.ordinal=row_.ordinal_key;
  END IF;
  frame_:=ops.pdf_identity_record_frame(header_.native_schema_digest,row_.family,row_.key,names_,values_);
  state_:=ops.pdf_identity_fold_step(state_,count_,frame_); count_:=count_+1; length_:=length_+octet_length(frame_);
 END LOOP;
 RETURN encode(ops.pdf_identity_fold_finish(state_,count_,length_),'hex');
END $$;
REVOKE ALL ON FUNCTION ops.pdf_identity_inline(jsonb),ops.pdf_identity_ascii_string(text),
 ops.pdf_identity_stream_scalar(text,text,text),
 ops.pdf_identity_companion_scalar(text,text,text,text,text,jsonb),ops.pdf_record_logical_identity(text,text) FROM PUBLIC;
