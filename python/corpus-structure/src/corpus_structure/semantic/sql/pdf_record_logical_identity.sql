-- pdf-publication-records-v3 over the unchanged pdf-record-sha256-fold-v1 algorithm.
-- Only bounded per-record arrays are constructed; the ordered relation cursor spills normally.
CREATE OR REPLACE FUNCTION ops.pdf_identity_text(p_value text)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE payload_ bytea := convert_to(p_value,'UTF8');
BEGIN
 -- PostgreSQL text in a UTF8 database has already passed encoding validation.
 -- Keep the raw-byte validator for SQL_ASCII and every other database encoding.
 IF current_setting('server_encoding')<>'UTF8' THEN
  RETURN ops.pdf_identity_scalar('s',payload_);
 END IF;
 RETURN convert_to('s','UTF8')||int8send(octet_length(payload_)::bigint)||
  ops.pdf_identity_byte_root(payload_);
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_inline(p_value jsonb)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE kind_ text:=jsonb_typeof(p_value); payload_ bytea;
BEGIN
 CASE kind_
 WHEN 'null' THEN RETURN ops.pdf_identity_scalar('n',''::bytea);
 WHEN 'boolean' THEN RETURN ops.pdf_identity_scalar('b',CASE WHEN p_value='true'::jsonb THEN decode('01','hex') ELSE decode('00','hex') END);
 WHEN 'string' THEN RETURN ops.pdf_identity_text(p_value#>>'{}');
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

-- Physical pins select immutable, authenticated bodies; they do not salt logical
-- meaning. No DDO canonical product is needed: capture can publish raw and then
-- organized records in the same completion. The extant publication DAG is the
-- authority, not a caller-supplied logical hash.
CREATE OR REPLACE FUNCTION ops.pdf_identity_published_target(
 p_task bigint,p_key text,p_digest text)
RETURNS jsonb LANGUAGE plpgsql STABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE root_ ops.pdf_product; pin_ ops.pdf_product; revision_ ops.pdf_published_revision;
 body_ ops.pdf_product_body; item_ jsonb; pending_ jsonb; next_ jsonb; resolved_ jsonb:='{}';
 key_ text; root_key_ text; target_ jsonb; inputs_ jsonb; input_ record; selected_ jsonb;
 ready_ boolean; progress_ boolean; state_ bytea; frame_ bytea;
BEGIN
 SELECT * INTO STRICT root_ FROM ops.pdf_product
 WHERE task_id=p_task AND product_key=p_key AND content_digest=p_digest;
 root_key_:=data.canonical_json(jsonb_build_array(p_task,p_key,p_digest));
 -- UNION deduplicates shared A/B/C predecessors by exact physical identity;
 -- neither paths nor nested ancestor bodies are expanded. Sealed native/integrated
 -- digests terminate traversal: an endpoint never expands a whole-book input DAG.
 -- Only bounded target descriptors are carried forward; original ordered edges
 -- are folded once for each distinct observation.
 WITH RECURSIVE lineage(task_id,product_key,content_digest) AS (
  SELECT p_task,p_key,p_digest
  UNION
  SELECT edge.input_task_id,edge.input_product_key,edge.input_content_digest
  FROM ops.pdf_product_input edge JOIN lineage parent
  ON edge.task_id=parent.task_id AND edge.product_key=parent.product_key
  JOIN ops.pdf_product parent_product ON parent_product.task_id=parent.task_id
   AND parent_product.product_key=parent.product_key
   AND parent_product.content_digest=parent.content_digest
   AND parent_product.kind='recognition_observation'
 )
 SELECT jsonb_agg(to_jsonb(product) ORDER BY product.task_id,product.product_key COLLATE "C")
 INTO pending_ FROM lineage JOIN ops.pdf_product product USING(task_id,product_key,content_digest);
 WHILE jsonb_array_length(pending_)>0 LOOP
  next_:='[]'; progress_:=false;
  FOR item_ IN SELECT value FROM jsonb_array_elements(pending_) LOOP
   pin_:=jsonb_populate_record(NULL::ops.pdf_product,item_);
   key_:=data.canonical_json(jsonb_build_array(pin_.task_id,pin_.product_key,pin_.content_digest));
   IF pin_.artifact_digest IS DISTINCT FROM root_.artifact_digest THEN
    RAISE EXCEPTION 'logical PDF target changes original source' USING ERRCODE='23514'; END IF;
   -- This exact captured contract includes the current record profile. Older
   -- releases stay physically addressable but are never reinterpreted by v3.
   PERFORM ops.pdf_contract_input(pin_.release_id,'implementation/pdf/staging-model.yaml');
   IF pin_.kind IN ('native','integrated') THEN
    SELECT published.* INTO STRICT revision_
    FROM ops.pdf_published_revision published JOIN ops.pdf_build_validation validation
    ON validation.build_id=published.build_id AND validation.frozen_digest=published.frozen_digest
    AND validation.logical_digest=published.logical_digest AND validation.native_callbacks
    WHERE published.task_id=pin_.task_id AND published.product_key=pin_.product_key
    AND published.logical_digest=pin_.content_digest AND published.kind=pin_.kind
    AND published.release_id=pin_.release_id AND published.source_digest=pin_.artifact_digest
    AND validation.contract_digest=pin_.contract_digest
    AND encode(sha256(ops.pdf_contract_input(published.release_id,
     'implementation/pdf/docling-validation.schema.json')),'hex')=published.schema_digest;
    target_:=jsonb_build_object('version','pdf-published-target-v1','kind',revision_.kind,
     'source_digest',revision_.source_digest,'schema_digest',revision_.schema_digest,
     'recipe_digest',revision_.recipe_digest,'logical_digest',revision_.logical_digest);
   ELSIF pin_.kind='recognition_observation' THEN
    SELECT * INTO STRICT body_ FROM ops.pdf_product_body
    WHERE task_id=pin_.task_id AND product_key=pin_.product_key
    AND encode(sha256(payload),'hex')=pin_.content_digest
    AND encode(sha256(ops.pdf_contract_input(pin_.release_id,'schema/pdf_products')),'hex')=pin_.contract_digest;
    inputs_:='[]'; ready_:=true;
    FOR input_ IN SELECT * FROM ops.pdf_product_input
     WHERE task_id=pin_.task_id AND product_key=pin_.product_key ORDER BY input_index LOOP
     selected_:=resolved_->data.canonical_json(jsonb_build_array(
      input_.input_task_id,input_.input_product_key,input_.input_content_digest));
     IF selected_ IS NULL THEN ready_:=false; EXIT; END IF;
     IF input_.input_index<>jsonb_array_length(inputs_) THEN
      RAISE EXCEPTION 'logical PDF target input inventory is not contiguous' USING ERRCODE='23514'; END IF;
     inputs_:=inputs_||jsonb_build_array(jsonb_build_object(
      'ordinal',input_.input_index,'role',input_.role,'target_meaning',selected_));
    END LOOP;
    IF NOT ready_ THEN next_:=next_||jsonb_build_array(item_); CONTINUE; END IF;
    IF NOT EXISTS(SELECT FROM ops.pdf_product_input edge WHERE edge.task_id=pin_.task_id
     AND edge.product_key=pin_.product_key AND edge.role='structural') THEN
     RAISE EXCEPTION 'logical observation lacks authentic raw lineage' USING ERRCODE='23514'; END IF;
    state_:=ops.pdf_identity_fold_start('records');
    frame_:=ops.pdf_identity_record_frame(pin_.contract_digest,'observation','root',
     ARRAY['profile','source','recipe','meaning','inputs'],ARRAY[
      ops.pdf_identity_text('pdf-published-target-v1'),ops.pdf_identity_text(pin_.artifact_digest),
      ops.pdf_identity_text(body_.recipe_digest),ops.pdf_identity_text(data.canonical_json(
       data.ddo_json_meaning(ops.pdf_observation_meaning(body_.payload)))),
      ops.pdf_identity_text(data.canonical_json(inputs_))]);
    state_:=ops.pdf_identity_fold_step(state_,0,frame_);
    target_:=jsonb_build_object('version','pdf-published-target-v1','kind',pin_.kind,
     'source_digest',pin_.artifact_digest,'schema_digest',pin_.contract_digest,
     'recipe_digest',body_.recipe_digest,
     'logical_digest',encode(ops.pdf_identity_fold_finish(state_,1,octet_length(frame_)),'hex'));
   ELSE RAISE EXCEPTION 'unsupported logical PDF target kind %',pin_.kind USING ERRCODE='23514';
   END IF;
   resolved_:=jsonb_set(resolved_,ARRAY[key_],target_); progress_:=true;
  END LOOP;
  IF NOT progress_ THEN
   RAISE EXCEPTION 'logical PDF target has missing or cyclic input custody' USING ERRCODE='23514'; END IF;
  pending_:=next_;
 END LOOP;
 RETURN resolved_->root_key_;
END $$;

-- Published proof reads and admission fold the same ordered frame stream.
CREATE OR REPLACE FUNCTION ops.pdf_record_identity_frames(
 p_product text,p_revision text,p_fold boolean)
RETURNS SETOF bytea LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE header_ ops.pdf_record_document; row_ record; node_ kb.pdf_record_native;
 member_ kb.pdf_record_membership; companion_ kb.pdf_record_companion; endpoint_ kb.pdf_record_endpoint;
 field_ text; descriptor_ jsonb; body_ jsonb;
 names_ text[]; values_ bytea[]; frame_ bytea;
 state_ bytea:=ops.pdf_identity_fold_start('records'); count_ bigint:=0; length_ bigint:=0;
BEGIN
 SELECT * INTO STRICT header_ FROM ops.pdf_record_document WHERE product_id=p_product AND revision_id=p_revision;
 PERFORM ops.pdf_contract_input(header_.release_id,'implementation/pdf/staging-model.yaml');
 frame_:=ops.pdf_identity_record_frame(header_.native_schema_digest,'@context','@context',
 ARRAY['protocol','record_profile','source'],ARRAY[
 ops.pdf_identity_scalar('s',convert_to('pdf-record-sha256-fold-v1','UTF8')),
 ops.pdf_identity_scalar('s',convert_to('pdf-publication-records-v3','UTF8')),
 ops.pdf_identity_scalar('s',convert_to(header_.source_digest,'UTF8'))]);
 IF p_fold THEN
  state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
 ELSE RETURN NEXT frame_; END IF;
 count_:=count_+1; length_:=length_+octet_length(frame_);
 FOR row_ IN
  SELECT * FROM (
   SELECT 'companion/'||c.family AS family,c.local_id AS key,
    c AS companion,NULL::kb.pdf_record_endpoint AS endpoint,
    NULL::kb.pdf_record_membership AS member,NULL::kb.pdf_record_native AS node,
    NULL::bytea AS member_key, fields.local_id IS NOT NULL AS has_relation_fields
   FROM kb.pdf_record_companion c
   LEFT JOIN (
    SELECT DISTINCT f.local_id FROM kb.pdf_record_companion_field f
    WHERE f.product_id=p_product AND f.revision_id=p_revision AND f.family='relation'
   ) fields ON c.family='relation' AND fields.local_id=c.local_id
   WHERE c.product_id=p_product AND c.revision_id=p_revision
  UNION ALL SELECT 'document','root',NULL,NULL,NULL,NULL,NULL,false
  UNION ALL SELECT 'endpoint','['||ops.pdf_identity_ascii_string(e.relation_id)||','||e.ordinal::text||']',
   NULL,e,NULL,NULL,NULL,false
   FROM kb.pdf_record_endpoint e WHERE e.product_id=p_product AND e.revision_id=p_revision
  UNION ALL SELECT 'membership','['||ops.pdf_identity_ascii_string(m.parent_id)||','||
   ops.pdf_identity_ascii_string(m.field_name)||','||COALESCE(
    ops.pdf_identity_ascii_string(encode(member_key.scalar,'hex')),m.ordinal::text
   )||']',NULL,NULL,m,NULL,member_key.scalar,false
   FROM kb.pdf_record_membership m
   CROSS JOIN LATERAL (
    SELECT CASE WHEN m.member_key IS NOT NULL THEN ops.pdf_identity_text(m.member_key)
     ELSE ops.pdf_identity_stream_scalar(p_product,p_revision,m.member_key_stream_id)
    END AS scalar OFFSET 0
   ) member_key
   WHERE m.product_id=p_product AND m.revision_id=p_revision
  UNION ALL SELECT 'native',n.record_id,NULL,NULL,NULL,n,NULL,false
   FROM kb.pdf_record_native n WHERE n.product_id=p_product AND n.revision_id=p_revision
  UNION ALL SELECT 'publication','root',NULL,NULL,NULL,NULL,NULL,false
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
   node_:=row_.node;
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
   member_:=row_.member;
   names_:=ARRAY['parent_id','field_name']; values_:=ARRAY[ops.pdf_identity_scalar('s',convert_to(member_.parent_id,'UTF8')),ops.pdf_identity_scalar('s',convert_to(member_.field_name,'UTF8'))];
   IF member_.member_key IS NOT NULL OR member_.member_key_stream_id IS NOT NULL THEN
    names_:=array_append(names_,'member_key');
    values_:=array_append(values_,row_.member_key);
   ELSE names_:=array_append(names_,'ordinal'); values_:=array_append(values_,ops.pdf_identity_scalar('i',convert_to(member_.ordinal::text,'UTF8'))); END IF;
   IF member_.value_kind='record' THEN
    names_:=array_append(names_,'target'); values_:=array_append(values_,ops.pdf_identity_scalar('s',convert_to(member_.record_id,'UTF8')));
   ELSE
    names_:=array_append(names_,'value'); values_:=array_append(values_,CASE WHEN member_.value_kind='scalar' THEN ops.pdf_identity_inline(member_.scalar_json) ELSE ops.pdf_identity_stream_scalar(p_product,p_revision,member_.stream_id) END);
   END IF;
  ELSIF left(row_.family,10)='companion/' THEN
   companion_:=row_.companion;
   body_:=CASE
    WHEN companion_.family='native_metadata' AND companion_.body->>'kind'='{pdf_payload_family}'
     THEN companion_.body-ARRAY['value','payload_codec','payload_schema_digest']
    WHEN companion_.family='native_metadata' THEN companion_.body-'value'
    WHEN companion_.family='occurrence' THEN companion_.body-'text'
    WHEN row_.has_relation_fields THEN ops.pdf_companion_restore_fields(
     p_product,p_revision,companion_.family,companion_.local_id,companion_.body)
    ELSE companion_.body
   END;
   IF companion_.family='input' THEN
    body_:=jsonb_build_object('role',companion_.body->'role','target_meaning',
     ops.pdf_identity_published_target((companion_.body->>'task_id')::bigint,
      companion_.body->>'product_key',companion_.body->>'content_digest'));
   END IF;
   names_:=ARRAY['body','ordinal'];
   values_:=ARRAY[ops.pdf_identity_text(data.canonical_json(body_)),
    ops.pdf_identity_scalar('i',convert_to(companion_.ordinal::text,'UTF8'))];
   IF row_.family IN ('companion/native_metadata','companion/occurrence') THEN
    field_:=CASE WHEN row_.family='companion/native_metadata' THEN 'value' ELSE 'text' END;
    names_:=array_append(names_,field_);
    values_:=array_append(values_,ops.pdf_identity_companion_scalar(
     p_product,p_revision,companion_.family,companion_.local_id,field_,companion_.body));
   END IF;

  ELSIF row_.family='endpoint' THEN
   names_:=ARRAY['relation_id','ordinal','target_meaning','occurrence_id','role'];
   endpoint_:=row_.endpoint;
   IF endpoint_.target_task_id=0 AND
    ROW(endpoint_.target_product_key,endpoint_.target_content_digest) IS DISTINCT FROM ROW('@self'::text,'@self'::text) THEN
    RAISE EXCEPTION 'logical PDF self endpoint differs from canonical physical sentinel' USING ERRCODE='23514'; END IF;
   values_:=ARRAY[ops.pdf_identity_text(endpoint_.relation_id),
    ops.pdf_identity_scalar('i',convert_to(endpoint_.ordinal::text,'UTF8')),
    ops.pdf_identity_text(CASE WHEN endpoint_.target_task_id=0 THEN '@self' ELSE
     data.canonical_json(ops.pdf_identity_published_target(endpoint_.target_task_id,
      endpoint_.target_product_key,endpoint_.target_content_digest)) END),
    ops.pdf_identity_text(endpoint_.occurrence_id),ops.pdf_identity_text(endpoint_.role)];
  END IF;
  frame_:=ops.pdf_identity_record_frame(header_.native_schema_digest,row_.family,row_.key,names_,values_);
  IF p_fold THEN
   state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
  ELSE
   -- A PL/pgSQL set-returning result may spool on the server before fetch.
   -- Match the portable proof reader's frame, count and uncompressed byte bounds.
   IF octet_length(frame_)>65536 OR count_>=1000000 OR length_+octet_length(frame_)>402653184 THEN
    RAISE EXCEPTION 'review native proof exceeds frame budget' USING ERRCODE='54000';
   END IF;
   RETURN NEXT frame_;
  END IF;
  count_:=count_+1; length_:=length_+octet_length(frame_);
 END LOOP;
 IF p_fold THEN RETURN NEXT ops.pdf_identity_fold_finish(state_,count_,length_); END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.pdf_record_logical_identity(
 p_product text,p_revision text,p_verified_predecessor text)
RETURNS text LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE stream_ record; digest_ bytea;
BEGIN
 -- The protected validator resolves the optional predecessor from a compatible
 -- sealed receipt. A matching descriptor alone cannot prove its bytes unchanged.
 FOR stream_ IN
  SELECT current_.stream_id FROM ops.pdf_artifact_stream current_
  LEFT JOIN ops.pdf_artifact_stream prior ON prior.product_id=p_verified_predecessor
   AND prior.revision_id=p_verified_predecessor AND prior.stream_id=current_.stream_id
  WHERE current_.product_id=p_product AND current_.revision_id=p_revision
  AND (prior.stream_id IS NULL OR
   ROW(current_.byte_length,current_.serialization_sha256,current_.byte_root,current_.encoding_profile)
    IS DISTINCT FROM ROW(prior.byte_length,prior.serialization_sha256,prior.byte_root,prior.encoding_profile)
   OR EXISTS (
    SELECT FROM (
     SELECT ordinal,byte_offset,byte_length,body,sha256_digest FROM ops.pdf_artifact_part
     WHERE product_id=p_product AND revision_id=p_revision AND stream_id=current_.stream_id
    ) new_part FULL JOIN (
     SELECT ordinal,byte_offset,byte_length,body,sha256_digest FROM ops.pdf_artifact_part
     WHERE product_id=p_verified_predecessor AND revision_id=p_verified_predecessor
      AND stream_id=current_.stream_id
    ) old_part USING (ordinal)
    WHERE new_part IS DISTINCT FROM old_part
   ))
 LOOP
  PERFORM ops.pdf_identity_verify_artifact(p_product,p_revision,stream_.stream_id);
 END LOOP;
 SELECT f INTO STRICT digest_ FROM ops.pdf_record_identity_frames(p_product,p_revision,true) f;
 RETURN encode(digest_,'hex');
END $$;

-- Existing callers verify every immutable stream, including unreferenced streams.
CREATE OR REPLACE FUNCTION ops.pdf_record_logical_identity(p_product text,p_revision text)
RETURNS text LANGUAGE sql STABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT ops.pdf_record_logical_identity(p_product,p_revision,NULL)
$$;
REVOKE ALL ON FUNCTION ops.pdf_identity_text(text),ops.pdf_identity_inline(jsonb),ops.pdf_identity_ascii_string(text),
 ops.pdf_identity_stream_scalar(text,text,text),
 ops.pdf_identity_companion_scalar(text,text,text,text,text,jsonb),
 ops.pdf_identity_published_target(bigint,text,text),
 ops.pdf_record_identity_frames(text,text,boolean),ops.pdf_record_logical_identity(text,text,text),ops.pdf_record_logical_identity(text,text) FROM PUBLIC;
