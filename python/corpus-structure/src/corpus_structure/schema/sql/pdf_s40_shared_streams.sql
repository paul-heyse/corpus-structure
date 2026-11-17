DO $pdf_s40$
DECLARE descriptor record; part record; owner ops.pdf_stage_build; project text;
 state bytea; pending bytea; block bytea; block_ordinal bigint; offset_ bigint; next_ordinal bigint;
 retained ops.pdf_shared_stream_part;
BEGIN
 -- OPEN uploads are not admitted stages. Close their DB append capability;
 -- their original assets and durable producer spools remain for regeneration.
 UPDATE ops.pdf_stage_build SET state='abandoned' WHERE state='open';
 -- Explicit maintenance only: the two predecessor part relations must exist.
 -- Lock the finite source population before copying and retiring its stores.
 LOCK TABLE ops.pdf_artifact_part,ops.pdf_stage_artifact_part,
 ops.pdf_artifact_stream,ops.pdf_stage_artifact_stream IN ACCESS EXCLUSIVE MODE;
 ALTER TABLE ops.pdf_shared_stream_part DISABLE TRIGGER pdf_shared_content_mutation;
 FOR descriptor IN
 SELECT 'stage'::text source,s.* FROM ops.pdf_stage_artifact_stream s
 WHERE EXISTS(SELECT FROM ops.pdf_stage_build build WHERE build.build_id=s.product_id AND build.state IN ('frozen','published'))
 UNION ALL SELECT 'final'::text source,s.* FROM ops.pdf_artifact_stream s
 WHERE EXISTS(SELECT FROM ops.pdf_stage_build build WHERE build.build_id=s.product_id AND build.state IN ('frozen','published'))
 ORDER BY product_id,revision_id,stream_id,source LOOP
 IF descriptor.product_id IS DISTINCT FROM descriptor.revision_id THEN
 RAISE EXCEPTION 'S40 generated revision needs explicit regeneration' USING ERRCODE='23514'; END IF;
 SELECT * INTO owner FROM ops.pdf_stage_build WHERE build_id=descriptor.product_id;
 project:=ops.pdf_stream_project(descriptor.product_id);
 IF owner.build_id IS NULL OR project IS NULL THEN
 RAISE EXCEPTION 'S40 generated stream lacks actual declared build/project; regenerate it' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.pdf_shared_stream(project_id,encoding_profile,byte_length,byte_root,owner_build_id,owner_attempt,owner_holder)
 VALUES(project,descriptor.encoding_profile,descriptor.byte_length,descriptor.byte_root,owner.build_id,owner.attempt,owner.holder)
 ON CONFLICT DO NOTHING;
 state:=ops.pdf_identity_fold_start('bytes'); pending:=''::bytea;
 block_ordinal:=0; offset_:=0; next_ordinal:=0;
 FOR part IN EXECUTE CASE WHEN descriptor.source='stage' THEN
 'SELECT ordinal,byte_offset,byte_length,body,sha256_digest FROM ops.pdf_stage_artifact_part WHERE product_id=$1 AND revision_id=$2 AND stream_id=$3 ORDER BY ordinal'
 ELSE 'SELECT ordinal,byte_offset,byte_length,body,sha256_digest FROM ops.pdf_artifact_part WHERE product_id=$1 AND revision_id=$2 AND stream_id=$3 ORDER BY ordinal' END
 USING descriptor.product_id,descriptor.revision_id,descriptor.stream_id LOOP
 IF part.ordinal<>next_ordinal OR part.byte_offset<>offset_ OR part.byte_length NOT BETWEEN 1 AND 65536
 OR part.byte_length<>octet_length(part.body) OR part.sha256_digest<>encode(sha256(part.body),'hex') THEN
 RAISE EXCEPTION 'S40 historical actual part inventory differs; regenerate it' USING ERRCODE='23514'; END IF;
 pending:=pending||part.body; offset_:=offset_+part.byte_length; next_ordinal:=next_ordinal+1;
 -- Store the canonical byte-block partition, independent of predecessor chunking.
 WHILE octet_length(pending)>=65536 OR (offset_=descriptor.byte_length AND octet_length(pending)>0) LOOP
 block:=substr(pending,1,65536); pending:=substr(pending,65537);
 INSERT INTO ops.pdf_shared_stream_part(project_id,encoding_profile,stream_length,byte_root,ordinal,byte_offset,byte_length,body,sha256_digest)
 VALUES(project,descriptor.encoding_profile,descriptor.byte_length,descriptor.byte_root,block_ordinal,
 block_ordinal*65536,octet_length(block),block,encode(sha256(block),'hex')) ON CONFLICT DO NOTHING;
 SELECT stored.* INTO STRICT retained FROM ops.pdf_shared_stream_part stored WHERE stored.project_id=project
 AND stored.encoding_profile=descriptor.encoding_profile AND stored.stream_length=descriptor.byte_length
 AND stored.byte_root=descriptor.byte_root AND stored.ordinal=block_ordinal;
 IF (retained.byte_offset,retained.byte_length,retained.body,retained.sha256_digest) IS DISTINCT FROM
 (block_ordinal*65536,octet_length(block),block,encode(sha256(block),'hex')) THEN
 RAISE EXCEPTION 'S40 historical copies disagree on shared bytes; regenerate them' USING ERRCODE='23514'; END IF;
 state:=ops.pdf_identity_fold_step(state,block_ordinal,block); block_ordinal:=block_ordinal+1;
 END LOOP;
 END LOOP;
 IF offset_<>descriptor.byte_length OR octet_length(pending)<>0
 OR encode(ops.pdf_identity_fold_finish(state,block_ordinal,offset_),'hex')<>descriptor.byte_root THEN
 RAISE EXCEPTION 'S40 historical actual byte fold differs; regenerate it' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM ops.pdf_shared_stream_part stored WHERE stored.project_id=project
 AND stored.encoding_profile=descriptor.encoding_profile AND stored.stream_length=descriptor.byte_length
 AND stored.byte_root=descriptor.byte_root)<>block_ordinal THEN
 RAISE EXCEPTION 'S40 shared byte inventory has extra parts' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.pdf_shared_stream_verification(project_id,encoding_profile,byte_length,byte_root,part_count)
 VALUES(project,descriptor.encoding_profile,descriptor.byte_length,descriptor.byte_root,block_ordinal) ON CONFLICT DO NOTHING;
 END LOOP;
 ALTER TABLE ops.pdf_shared_stream_part ENABLE TRIGGER pdf_shared_content_mutation;
END $pdf_s40$;
