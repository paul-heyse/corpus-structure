-- Private access projections are derived from the same frozen native records.
-- JSONB projection equality intentionally permits numeric lexical normalization and
-- signed-zero loss; the separately checked native record/byte identity retains both.
CREATE OR REPLACE FUNCTION ops.pdf_projection_scalar_matches(p_value jsonb,p_expected jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE actual_ bytea; expected_ bytea;
BEGIN
 IF p_value IS NULL OR p_expected IS NULL THEN RETURN false; END IF;
 IF jsonb_typeof(p_expected)='object' AND p_expected ? 'native_float64' THEN
  IF jsonb_typeof(p_value)<>'number' THEN RETURN false; END IF;
  actual_:=float8send((p_value#>>'{}')::double precision);
  expected_:=decode(p_expected->>'native_float64','hex');
  RETURN actual_=expected_ OR (expected_ IN (decode('0000000000000000','hex'),decode('8000000000000000','hex')) AND (p_value#>>'{}')::numeric=0);
 END IF;
 RETURN jsonb_typeof(p_value)=jsonb_typeof(p_expected) AND p_value=p_expected;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_projection_stream_value(p_build text,p_stream text)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE stream_ ops.pdf_artifact_stream; actual_length_ bigint; payload_ bytea;
BEGIN
 SELECT * INTO STRICT stream_ FROM ops.pdf_artifact_stream WHERE product_id=p_build AND revision_id=p_build AND stream_id=p_stream;
 -- A per-item projection is admitted through the existing 8MiB access-upload
 -- profile. Only its own opaque/key value is decoded here, never a book envelope.
 SELECT COALESCE(sum(octet_length(body)),0) INTO actual_length_ FROM ops.pdf_artifact_part
 WHERE product_id=p_build AND revision_id=p_build AND stream_id=p_stream;
 IF actual_length_>8388608 OR actual_length_<>stream_.byte_length THEN
  RAISE EXCEPTION 'native access scalar exceeds bounded projection or stream length' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(string_agg(body,''::bytea ORDER BY ordinal),''::bytea) INTO payload_ FROM ops.pdf_artifact_part
 WHERE product_id=p_build AND revision_id=p_build AND stream_id=p_stream;
 IF stream_.encoding_profile='pdf-record-native-json-v1' THEN RETURN convert_from(payload_,'UTF8')::jsonb;
 ELSIF stream_.encoding_profile='pdf-record-scalar-v1:s' THEN RETURN to_jsonb(convert_from(payload_,'UTF8'));
 ELSE RAISE EXCEPTION 'native access requires a JSON/string stream profile' USING ERRCODE='23514'; END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_projection_stream_matches(p_build text,p_stream text,p_value jsonb)
RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE stream_ ops.pdf_artifact_stream; payload_ bytea;
BEGIN
 IF p_value IS NULL THEN RETURN false; END IF;
 SELECT * INTO STRICT stream_ FROM ops.pdf_artifact_stream WHERE product_id=p_build AND revision_id=p_build AND stream_id=p_stream;
 IF stream_.encoding_profile='pdf-record-native-json-v1' THEN
  RETURN ops.pdf_projection_stream_value(p_build,p_stream)=p_value;
 ELSIF stream_.encoding_profile='pdf-record-scalar-v1:s' AND jsonb_typeof(p_value)='string' THEN
  payload_:=convert_to(p_value#>>'{}','UTF8');
 ELSIF stream_.encoding_profile='pdf-record-scalar-v1:i' AND jsonb_typeof(p_value)='number' THEN
  IF (p_value#>>'{}') !~ '^(0|-?[1-9][0-9]*)$' THEN RETURN false; END IF;
  payload_:=convert_to(p_value#>>'{}','UTF8');
 ELSIF stream_.encoding_profile='pdf-record-scalar-v1:f' AND jsonb_typeof(p_value)='number' THEN
  payload_:=float8send((p_value#>>'{}')::double precision);
  IF (p_value#>>'{}')::numeric=0 AND stream_.byte_length=8 AND stream_.byte_root IN
   (encode(ops.pdf_identity_byte_root(decode('0000000000000000','hex')),'hex'),encode(ops.pdf_identity_byte_root(decode('8000000000000000','hex')),'hex')) THEN RETURN true; END IF;
 ELSIF stream_.encoding_profile='pdf-record-scalar-v1:n' AND p_value='null'::jsonb THEN payload_:=''::bytea;
 ELSIF stream_.encoding_profile='pdf-record-scalar-v1:b' AND jsonb_typeof(p_value)='boolean' THEN
  payload_:=CASE WHEN p_value='true'::jsonb THEN decode('01','hex') ELSE decode('00','hex') END;
 ELSE RETURN false;
 END IF;
 RETURN octet_length(payload_)=stream_.byte_length AND encode(ops.pdf_identity_byte_root(payload_),'hex')=stream_.byte_root;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_check_access_correspondence(p_build text)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF EXISTS(SELECT FROM kb.pdf_record_access a LEFT JOIN kb.pdf_record_native n
 ON n.product_id=p_build AND n.revision_id=p_build AND n.native_address=a.pointer
 WHERE a.product_id=p_build AND (a.revision_id<>p_build OR n.record_id IS NULL OR
 a.native_json->>'self_ref' IS DISTINCT FROM a.pointer OR
 a.label IS DISTINCT FROM COALESCE(a.native_json->>'label','unspecified') OR
 a.content_layer IS DISTINCT FROM COALESCE(a.native_json->>'content_layer','body') OR
 a.text IS DISTINCT FROM a.native_json->>'text' OR
 a.parent_pointer IS DISTINCT FROM a.native_json#>>'{parent,$ref}')) THEN
 RAISE EXCEPTION 'native access fields do not correspond to frozen native item' USING ERRCODE='23514'; END IF;

 IF EXISTS(WITH RECURSIVE projected(record_id,value) AS (
  SELECT n.record_id,a.native_json FROM kb.pdf_record_access a JOIN kb.pdf_record_native n
  ON n.product_id=p_build AND n.revision_id=p_build AND n.native_address=a.pointer WHERE a.product_id=p_build AND a.revision_id=p_build
  UNION ALL
  SELECT child.record_id,child.value FROM projected w JOIN kb.pdf_record_native n
  ON n.product_id=p_build AND n.revision_id=p_build AND n.record_id=w.record_id
  CROSS JOIN LATERAL (
   SELECT f.value->>'target' AS record_id,w.value->f.key AS value
   FROM jsonb_each(n.structure_json->'fields') f WHERE f.value->>'kind'='object'
   UNION ALL
   SELECT m.record_id,CASE WHEN f.value->>'kind'='map' THEN container.value->COALESCE(m.member_key,ops.pdf_projection_stream_value(p_build,m.member_key_stream_id)#>>'{}') ELSE container.value->m.ordinal::integer END
   FROM jsonb_each(n.structure_json->'fields') f JOIN kb.pdf_record_membership m
   ON m.product_id=p_build AND m.revision_id=p_build AND m.parent_id=w.record_id AND m.field_name=f.key
   CROSS JOIN LATERAL (SELECT CASE WHEN n.native_type='NativeArray' AND f.key='items' THEN w.value ELSE w.value->f.key END value) container
   WHERE f.value->>'kind' IN ('array','map') AND m.value_kind='record'
  ) child
 ) CYCLE record_id SET cycle_ USING path_
 SELECT FROM projected w LEFT JOIN kb.pdf_record_native n
 ON n.product_id=p_build AND n.revision_id=p_build AND n.record_id=w.record_id
 WHERE w.cycle_ OR n.record_id IS NULL OR w.value IS NULL OR
 (n.native_type='NativeArray' AND jsonb_typeof(w.value)<>'array') OR
 (n.native_type<>'NativeArray' AND (jsonb_typeof(w.value)<>'object' OR
  CASE WHEN n.structure_json ? 'extensions' THEN
    ops.pdf_projection_stream_matches(p_build,n.structure_json->'extensions'->>'stream_id',
     w.value-ARRAY(SELECT jsonb_object_keys(n.scalars_json) UNION SELECT jsonb_object_keys(n.structure_json->'fields'))) IS NOT TRUE
  ELSE w.value-ARRAY(SELECT jsonb_object_keys(n.scalars_json) UNION SELECT jsonb_object_keys(n.structure_json->'fields'))<>'{}'::jsonb END)) OR
 EXISTS(SELECT FROM jsonb_each(n.scalars_json) s WHERE ops.pdf_projection_scalar_matches(w.value->s.key,s.value) IS NOT TRUE) OR
 EXISTS(SELECT FROM jsonb_each(n.structure_json->'fields') f
 CROSS JOIN LATERAL (SELECT CASE WHEN n.native_type='NativeArray' AND f.key='items' THEN w.value ELSE w.value->f.key END value) container
 WHERE container.value IS NULL OR
 (f.value->>'kind'='object' AND jsonb_typeof(container.value)<>'object') OR
 (f.value->>'kind'='parts' AND ops.pdf_projection_stream_matches(p_build,f.value->>'stream_id',container.value) IS NOT TRUE) OR
 (f.value->>'kind'='array' AND (jsonb_typeof(container.value)<>'array' OR jsonb_array_length(container.value)<>(f.value->>'length')::bigint)) OR
 (f.value->>'kind'='map' AND (jsonb_typeof(container.value)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(container.value))<>(f.value->>'length')::bigint)) OR
 EXISTS(SELECT FROM kb.pdf_record_membership m
 CROSS JOIN LATERAL (SELECT CASE WHEN f.value->>'kind'='map' THEN container.value->COALESCE(m.member_key,ops.pdf_projection_stream_value(p_build,m.member_key_stream_id)#>>'{}') ELSE container.value->m.ordinal::integer END value) actual
 WHERE m.product_id=p_build AND m.revision_id=p_build AND m.parent_id=w.record_id AND m.field_name=f.key AND
 (actual.value IS NULL OR (m.value_kind='scalar' AND ops.pdf_projection_scalar_matches(actual.value,m.scalar_json) IS NOT TRUE) OR
 (m.value_kind='parts' AND ops.pdf_projection_stream_matches(p_build,m.stream_id,actual.value) IS NOT TRUE))))) THEN
 RAISE EXCEPTION 'native access JSON differs from frozen record fields/members/scalars' USING ERRCODE='23514'; END IF;

 IF EXISTS(WITH RECURSIVE ancestry(pointer,owner,depth) AS (
  SELECT pointer,pointer,0 FROM kb.pdf_record_access WHERE product_id=p_build AND revision_id=p_build
  UNION ALL SELECT a.pointer,parent.pointer,a.depth+1 FROM ancestry a JOIN kb.pdf_record_access child
  ON child.product_id=p_build AND child.revision_id=p_build AND child.pointer=a.owner JOIN kb.pdf_record_access parent
  ON parent.product_id=p_build AND parent.revision_id=p_build AND parent.pointer=child.parent_pointer
 ) CYCLE owner SET cycle_ USING path_, nearest AS (
 SELECT DISTINCT ON (n.pointer) n.pointer,n.owner FROM ancestry n JOIN kb.pdf_record_access section
 ON section.product_id=p_build AND section.revision_id=p_build AND section.pointer=n.owner
 WHERE section.label IN ('section','chapter') ORDER BY n.pointer,n.depth
 ), cycles AS (SELECT DISTINCT pointer FROM ancestry WHERE cycle_)
 SELECT FROM kb.pdf_record_access a LEFT JOIN nearest n ON n.pointer=a.pointer
 LEFT JOIN cycles c ON c.pointer=a.pointer WHERE a.product_id=p_build AND a.revision_id=p_build AND
 (c.pointer IS NOT NULL OR a.section_pointer IS DISTINCT FROM n.owner)) THEN
 RAISE EXCEPTION 'native access section owner differs from native ancestry' USING ERRCODE='23514'; END IF;

 IF EXISTS(WITH RECURSIVE roots(pointer,path) AS (
  SELECT target.scalars_json->>'self_ref',ARRAY[CASE f.key WHEN 'body' THEN 0 ELSE 1 END]::bigint[]
  FROM ops.pdf_record_document h JOIN kb.pdf_record_native root ON root.product_id=p_build AND root.revision_id=p_build AND root.record_id=h.root_id
  CROSS JOIN LATERAL jsonb_each(root.structure_json->'fields') f JOIN kb.pdf_record_native target
  ON target.product_id=p_build AND target.revision_id=p_build AND target.record_id=f.value->>'target' WHERE h.product_id=p_build AND h.revision_id=p_build AND f.key IN ('body','furniture')
 ), traversal(pointer,path) AS (
 SELECT pointer,path FROM roots UNION ALL
 SELECT c.value->>'$ref',t.path||(c.ordinality-1) FROM traversal t JOIN kb.pdf_record_access a
 ON a.product_id=p_build AND a.revision_id=p_build AND a.pointer=t.pointer CROSS JOIN LATERAL jsonb_array_elements(COALESCE(a.native_json->'children','[]')) WITH ORDINALITY c
 ) CYCLE pointer SET cycle_ USING cycle_path_
 SELECT FROM (SELECT a.pointer,a.ordinal,row_number() OVER(ORDER BY CASE WHEN t.pointer IS NULL THEN 1 ELSE 0 END,t.path,a.pointer COLLATE "C")-1 expected,t.cycle_
 FROM kb.pdf_record_access a LEFT JOIN traversal t ON t.pointer=a.pointer WHERE a.product_id=p_build AND a.revision_id=p_build) ordered
 WHERE ordinal<>expected OR cycle_) THEN
 RAISE EXCEPTION 'native access order differs from native containment traversal' USING ERRCODE='23514'; END IF;

 IF EXISTS(WITH region_counts AS (
 SELECT pointer,count(*) count_ FROM kb.pdf_record_region
 WHERE product_id=p_build AND revision_id=p_build GROUP BY pointer
 ) SELECT FROM kb.pdf_record_access a LEFT JOIN region_counts counts ON counts.pointer=a.pointer
 WHERE a.product_id=p_build AND a.revision_id=p_build AND
 COALESCE(counts.count_,0)<>jsonb_array_length(COALESCE(a.native_json->'prov','[]'))) OR
 EXISTS(WITH page_sizes AS MATERIALIZED (
 SELECT pages.member_key,page_size.scalars_json AS dimensions
 FROM ops.pdf_record_document h JOIN kb.pdf_record_membership pages
 ON pages.product_id=p_build AND pages.revision_id=p_build
 AND pages.parent_id=h.root_id AND pages.field_name='pages'
 LEFT JOIN kb.pdf_record_native page ON page.product_id=p_build AND page.revision_id=p_build
 AND page.record_id=pages.record_id
 LEFT JOIN kb.pdf_record_native page_size ON page_size.product_id=p_build
 AND page_size.revision_id=p_build
 AND page_size.record_id=page.structure_json->'fields'->'size'->>'target'
 WHERE h.product_id=p_build AND h.revision_id=p_build
 ) SELECT FROM kb.pdf_record_region r LEFT JOIN kb.pdf_record_access a ON a.product_id=p_build AND a.revision_id=p_build AND a.pointer=r.pointer
 LEFT JOIN LATERAL (SELECT a.native_json->'prov'->r.region_index::integer value) prov ON true
 LEFT JOIN page_sizes size ON size.member_key=r.page_no::text
 WHERE r.product_id=p_build AND (r.revision_id<>p_build OR a.pointer IS NULL OR prov.value IS NULL OR
 (prov.value->>'page_no')::bigint IS DISTINCT FROM r.page_no OR
 ops.pdf_projection_scalar_matches(to_jsonb(r.page_width),size.dimensions->'width') IS NOT TRUE OR
 ops.pdf_projection_scalar_matches(to_jsonb(r.page_height),size.dimensions->'height') IS NOT TRUE OR
 to_jsonb(r.left) IS DISTINCT FROM prov.value->'bbox'->'l' OR to_jsonb(r.top) IS DISTINCT FROM prov.value->'bbox'->'t' OR
 to_jsonb(r.right) IS DISTINCT FROM prov.value->'bbox'->'r' OR to_jsonb(r.bottom) IS DISTINCT FROM prov.value->'bbox'->'b' OR
 r.origin IS DISTINCT FROM CASE prov.value->'bbox'->>'coord_origin' WHEN 'TOPLEFT' THEN 'top_left' WHEN 'BOTTOMLEFT' THEN 'bottom_left' END)) THEN
 RAISE EXCEPTION 'native access regions differ from native provenance/pages' USING ERRCODE='23514'; END IF;
END $$;

REVOKE ALL ON FUNCTION ops.pdf_projection_scalar_matches(jsonb,jsonb),ops.pdf_projection_stream_value(text,text),
 ops.pdf_projection_stream_matches(text,text,jsonb),ops.pdf_check_access_correspondence(text) FROM PUBLIC;
