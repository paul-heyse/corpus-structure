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
REVOKE ALL ON FUNCTION ops.pdf_record_identity_frames(text,text,boolean) FROM PUBLIC;
