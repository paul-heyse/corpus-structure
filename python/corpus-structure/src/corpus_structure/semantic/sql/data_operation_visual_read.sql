CREATE OR REPLACE FUNCTION ops.ddo_visual_candidate_rows(mapped jsonb,p jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE rows_ jsonb; following integer; result jsonb;
BEGIN

 IF mapped IS NULL THEN
 IF (p->>'after')::integer<>0 THEN RAISE EXCEPTION 'visual evidence has no mapped continuation' USING ERRCODE='23514'; END IF;
 result:=jsonb_build_object('kind','rows','items','[]'::jsonb,'next_after',NULL);
 ELSE
 -- Parent-before-child identities and actual cell ownership remain unchanged.
 WITH RECURSIVE entries AS (
 SELECT value body,ordinality::integer ordinal FROM jsonb_array_elements(mapped->'rows') WITH ORDINALITY),
 anchor AS (SELECT body FROM entries WHERE body->>'occurrence_id'=p->>'occurrence_id'),
 cell_root AS (SELECT body->'cells'->((p->>'cell_index')::integer)->>'content_occurrence_id' id FROM anchor),
 subtree AS (
 SELECT body,ordinal FROM entries WHERE body->>'occurrence_id'=(SELECT id FROM cell_root)
 UNION ALL SELECT e.body,e.ordinal FROM entries e JOIN subtree parent ON e.body->>'parent_occurrence_id'=parent.body->>'occurrence_id'),
 text_matches AS (
 SELECT body FROM entries WHERE body->>'kind' IN ('picture_text','picture_description','caption','caption_candidate')
 AND strpos(btrim(regexp_replace(casefold((body->>'text') COLLATE pg_catalog.pg_unicode_fast),U&'[\0009-\000D\001C-\0020\0085\00A0\1680\2000-\200A\2028\2029\202F\205F\3000]+',' ','g'),' '),btrim(regexp_replace(casefold((p->>'query') COLLATE pg_catalog.pg_unicode_fast),U&'[\0009-\000D\001C-\0020\0085\00A0\1680\2000-\200A\2028\2029\202F\205F\3000]+',' ','g'),' '))>0),
 text_ancestors AS (
 SELECT body FROM text_matches UNION ALL SELECT e.body FROM entries e JOIN text_ancestors child
 ON e.body->>'occurrence_id'=child.body->>'parent_occurrence_id'),
 targets AS (
 SELECT body->>'occurrence_id' id FROM text_ancestors WHERE body->>'kind'='picture'
 UNION SELECT jsonb_array_elements_text(body->'parser_attachment_occurrence_ids') FROM text_matches
 UNION SELECT jsonb_array_elements_text(body->'associated_picture_occurrence_ids') FROM text_matches),
 candidates AS (
 SELECT * FROM entries e WHERE ordinal>(p->>'after')::integer
 AND (p->>'kind' IS NULL OR body->>'kind'=p->>'kind')
 AND (p->>'occurrence_id' IS NULL OR CASE WHEN p->>'cell_index' IS NULL
 THEN body->>'occurrence_id'=p->>'occurrence_id' ELSE ordinal IN (SELECT ordinal FROM subtree) END)
 AND (p->>'query' IS NULL OR (body->>'kind'='picture' AND body->>'occurrence_id' IN (SELECT id FROM targets)))
 AND (jsonb_array_length(p->'regions')=0 OR EXISTS(SELECT FROM jsonb_array_elements(p->'regions') region
 WHERE body->'source_region' IS NOT NULL AND body->'source_region'<>'null'::jsonb
 AND (body->'source_region'->>'left')::numeric<(region->>'right')::numeric
 AND (region->>'left')::numeric<(body->'source_region'->>'right')::numeric
 AND (body->'source_region'->>'top')::numeric<(region->>'bottom')::numeric
 AND (region->>'top')::numeric<(body->'source_region'->>'bottom')::numeric))
 ORDER BY ordinal LIMIT (p->>'limit')::integer+1)
 SELECT coalesce(jsonb_agg(body ORDER BY ordinal) FILTER(WHERE n<=(p->>'limit')::integer),'[]'::jsonb),
 CASE WHEN max(n)>(p->>'limit')::integer THEN max(ordinal) FILTER(WHERE n<=(p->>'limit')::integer) ELSE NULL END
 INTO rows_,following FROM (SELECT *,row_number() OVER(ORDER BY ordinal) n FROM candidates) ranked;
 IF p->>'occurrence_id' IS NOT NULL AND NOT EXISTS(SELECT FROM jsonb_array_elements(mapped->'rows') e WHERE e->>'occurrence_id'=p->>'occurrence_id') THEN
 RAISE EXCEPTION 'visual occurrence is outside candidate artifact' USING ERRCODE='23514'; END IF;
 IF p->>'cell_index' IS NOT NULL AND NOT EXISTS(SELECT FROM jsonb_array_elements(mapped->'rows') e
 WHERE e->>'occurrence_id'=p->>'occurrence_id' AND e->>'kind'='table'
 AND e->'cells'->((p->>'cell_index')::integer)->>'content_occurrence_id' IS NOT NULL) THEN
 RAISE EXCEPTION 'visual cell has no exact retained content group' USING ERRCODE='23514'; END IF;
 IF (p->>'after')::integer>0 AND jsonb_array_length(rows_)=0 THEN
 RAISE EXCEPTION 'visual continuation is outside selected scope' USING ERRCODE='23514'; END IF;
 result:=jsonb_build_object('kind','rows','items',rows_,'next_after',following);
 END IF;
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION ops.read_selected_visual_evidence(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload; source jsonb; cut jsonb; product kb.data_product;
 episode ops.data_derivation; raw_episode ops.data_derivation; intent ops.data_completion_intent;
 kind text; body jsonb; observation jsonb; image jsonb; mapping jsonb; raw_pin jsonb;
 raw_input jsonb; raw_product kb.data_product; artifact bytea; mapped jsonb;
 digest text; media text; total integer; offset_ integer; length_ integer; result jsonb;
 rows_ jsonb; following integer; selected jsonb; image_bytes bytea; response_bytes bytea;
BEGIN
 source:=ops.ddo_impl_read_selected_pdf_source(p->'source')->'payload';
 cut:=ops.ddo_require_selected_output(p->'source'->>'demand_id',p->'source'->>'read_id',
 p->'evidence'->>'use_id',p->'evidence'->>'product_id',p->'evidence'->>'derivation_id');
 IF cut IS DISTINCT FROM source->'cut' THEN RAISE EXCEPTION 'visual evidence differs from selected source cut' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT product FROM kb.data_product WHERE id=p->'evidence'->>'product_id'
 AND project_id=p->'source'->>'project_id';
 SELECT k.kind INTO STRICT kind FROM sem.data_kind_contract k WHERE k.kind_contract=product.kind_contract;
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=p->'evidence'->>'derivation_id';
 body:=data.ddo_json(product.canonical_body);
 raw_pin:=p->'evidence'; raw_episode:=episode;
 IF kind='https://corpus-structure.dev/semantic/data-operation-visual/DdoVisualMapping' THEN
 mapping:=body; observation:=body->'observation';
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id;
 SELECT value INTO STRICT raw_input FROM jsonb_array_elements(intent.payload->'inputs')
 WHERE value->>'role'='observation' AND value->>'member_id' IS NULL;
 IF NOT EXISTS(SELECT FROM ops.data_derivation_input input WHERE input.derivation_id=episode.id
 AND input.role='observation' AND input.product_id=raw_input->>'product_id' AND input.member_id IS NULL)
 OR NOT EXISTS(SELECT FROM ops.data_derivation_support support WHERE support.derivation_id=episode.id
 AND support.support_derivation_id=ops.ddo_single_input_support_episode(raw_input)) THEN
 RAISE EXCEPTION 'visual mapping lacks exact admitted raw input' USING ERRCODE='23514'; END IF;
 raw_pin:=jsonb_build_object('use_id',p->'evidence'->>'use_id','product_id',raw_input->>'product_id',
 'derivation_id',ops.ddo_single_input_support_episode(raw_input));
 PERFORM ops.ddo_require_selected_output(p->'source'->>'demand_id',p->'source'->>'read_id',
 raw_pin->>'use_id',raw_pin->>'product_id',raw_pin->>'derivation_id');
 SELECT * INTO STRICT raw_product FROM kb.data_product WHERE id=raw_pin->>'product_id'
 AND project_id=product.project_id AND original_source=product.original_source;
 IF NOT EXISTS(SELECT FROM sem.data_kind_contract k WHERE k.kind_contract=raw_product.kind_contract
 AND k.kind='https://corpus-structure.dev/semantic/data-operation-visual/DdoChandraObservation')
 OR data.ddo_json(raw_product.canonical_body) IS DISTINCT FROM observation THEN
 RAISE EXCEPTION 'visual mapping differs from its admitted raw observation' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT raw_episode FROM ops.data_derivation WHERE id=raw_pin->>'derivation_id';
 ELSIF kind='https://corpus-structure.dev/semantic/data-operation-visual/DdoChandraObservation' THEN
 observation:=body;
 ELSE RAISE EXCEPTION 'selected product is not visual evidence' USING ERRCODE='23514'; END IF;
 image:=observation->'image';
 IF product.original_source IS DISTINCT FROM image->>'document'
 OR product.original_source IS DISTINCT FROM source->>'original_source'
 OR image->>'source_digest' IS DISTINCT FROM source->'receipt'->'publication'->>'source_digest'
 OR image->>'logical_digest' IS DISTINCT FROM source->'receipt'->'publication'->>'logical_digest' THEN
 RAISE EXCEPTION 'visual image differs from selected original PDF source' USING ERRCODE='23514'; END IF;
 image_bytes:=decode(image->>'content_hex','hex'); response_bytes:=convert_to(observation->>'raw_response','UTF8');
 IF encode(sha256(image_bytes),'hex') IS DISTINCT FROM image->>'content_digest'
 OR substring(image_bytes,1,8) IS DISTINCT FROM decode('89504e470d0a1a0a','hex')
 OR octet_length(image_bytes)<24
 OR (get_byte(image_bytes,16)::bigint*16777216+get_byte(image_bytes,17)*65536+get_byte(image_bytes,18)*256+get_byte(image_bytes,19))<>(image->>'width')::integer
 OR (get_byte(image_bytes,20)::bigint*16777216+get_byte(image_bytes,21)*65536+get_byte(image_bytes,22)*256+get_byte(image_bytes,23))<>(image->>'height')::integer
 OR encode(sha256(response_bytes),'hex') IS DISTINCT FROM observation->>'response_digest' THEN
 RAISE EXCEPTION 'visual retained bytes differ from their exact digests' USING ERRCODE='23514'; END IF;
 IF mapping IS NOT NULL AND mapping->>'mapped_hex'<>'' THEN
 artifact:=decode(mapping->>'mapped_hex','hex');
 IF octet_length(artifact)>8388608 THEN RAISE EXCEPTION 'visual mapped artifact exceeds byte bound' USING ERRCODE='54000'; END IF;
 mapped:=convert_from(artifact,'UTF8')::jsonb;
 IF NOT public.json_matches_schema('__VISUAL_ARTIFACT_SCHEMA__'::json,mapped::json)
 OR (mapped->>'page_no')::integer<>(image->>'page_no')::integer THEN
 RAISE EXCEPTION 'visual mapped artifact violates current candidate schema' USING ERRCODE='23514'; END IF;
 END IF;
 IF p->>'mode'='header' THEN
 result:=jsonb_build_object('kind','header','header',jsonb_build_object(
 'evidence',p->'evidence','raw',raw_pin,'producer',to_jsonb(episode),'raw_producer',to_jsonb(raw_episode),
 'observation',(observation-'raw_response'-'image')||jsonb_build_object('image',
 (image-'content_hex'-'transform_json')||jsonb_build_object('transform',(image->>'transform_json')::jsonb)),
 'mapping_availability',CASE WHEN mapping IS NULL THEN 'not_selected' WHEN mapped IS NULL THEN 'unavailable' ELSE 'available' END,
 'mapping',CASE WHEN mapping IS NULL THEN NULL ELSE mapping-'observation'-'mapped_hex' END,
 'mapped_digest',CASE WHEN mapped IS NULL THEN NULL ELSE encode(sha256(artifact),'hex') END));
 ELSIF p->>'mode'='artifact' THEN
 digest:=p->>'artifact_digest';
 IF digest=image->>'content_digest' THEN artifact:=image_bytes; media:='image/png';
 ELSIF digest=observation->>'response_digest' THEN artifact:=response_bytes; media:='text/html; charset=utf-8';
 ELSIF mapped IS NOT NULL AND digest=encode(sha256(artifact),'hex') THEN media:='application/json';
 ELSE RAISE EXCEPTION 'visual artifact is outside exact selected evidence' USING ERRCODE='23514'; END IF;
 total:=octet_length(artifact); offset_:=(p->>'after')::integer;
 IF offset_>total OR (offset_=total AND offset_<>0) THEN RAISE EXCEPTION 'visual byte continuation is outside artifact' USING ERRCODE='23514'; END IF;
 length_:=least(65536,total-offset_);
 result:=jsonb_build_object('kind','artifact','digest',digest,'media_type',media,
 'content_hex',encode(substring(artifact,offset_+1,length_),'hex'),'offset',offset_,
 'total_bytes',total,'next_offset',CASE WHEN offset_+length_<total THEN offset_+length_ ELSE NULL END);
 ELSIF p->>'mode'='rows' THEN
 result:=ops.ddo_visual_candidate_rows(mapped,p);
 ELSE RAISE EXCEPTION 'unknown visual read mode' USING ERRCODE='23514'; END IF;
 IF octet_length(result::text)>(p->>'max_bytes')::integer THEN
 RAISE EXCEPTION 'visual result exceeds byte bound' USING ERRCODE='54000'; END IF;
 RETURN jsonb_build_object('payload',result);
END $$;
