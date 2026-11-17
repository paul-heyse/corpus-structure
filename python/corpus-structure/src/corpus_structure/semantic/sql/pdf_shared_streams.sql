CREATE OR REPLACE FUNCTION ops.probe_pdf_shared_streams(p_build text,p_task bigint,p_attempt bigint,p_holder text,p_streams bytea)
RETURNS TABLE(stream_id text,verified boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE build ops.pdf_stage_build; packet jsonb; descriptor jsonb;
BEGIN
 build:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(build.release_id,'adopt_pdf_batch');
 IF p_streams IS NULL OR octet_length(p_streams)>67108864 THEN
 RAISE EXCEPTION 'shared stream probe exceeds its upload bound' USING ERRCODE='23514'; END IF;
 packet:=convert_from(p_streams,'UTF8')::jsonb;
 IF jsonb_typeof(packet) IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'shared stream probe requires an array' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(packet)>65536 THEN
 RAISE EXCEPTION 'shared stream probe requires a bounded descriptor set' USING ERRCODE='23514'; END IF;
 FOR descriptor IN SELECT value FROM jsonb_array_elements(packet) LOOP
 PERFORM ops.ddo_fields(descriptor,ARRAY['product_id','revision_id','stream_id','encoding_profile','byte_length','byte_root'],ARRAY['serialization_sha256']);
 IF EXISTS(SELECT FROM unnest(ARRAY['product_id','revision_id','stream_id','encoding_profile','byte_root']) name
 WHERE jsonb_typeof(descriptor->name) IS DISTINCT FROM 'string')
 OR descriptor->>'product_id' IS DISTINCT FROM p_build OR descriptor->>'revision_id' IS DISTINCT FROM p_build
 OR nullif(descriptor->>'stream_id','') IS NULL OR nullif(descriptor->>'encoding_profile','') IS NULL
 OR jsonb_typeof(descriptor->'byte_length') IS DISTINCT FROM 'number'
 OR NOT coalesce(descriptor->>'byte_length' ~ '^(0|[1-9][0-9]*)$',false)
 OR NOT coalesce(descriptor->>'byte_root' ~ '^[0-9a-f]{64}$',false)
 OR (descriptor ? 'serialization_sha256' AND descriptor->'serialization_sha256'<>'null'::jsonb
 AND (jsonb_typeof(descriptor->'serialization_sha256') IS DISTINCT FROM 'string'
 OR NOT coalesce(descriptor->>'serialization_sha256' ~ '^[0-9a-f]{64}$',false))) THEN
 RAISE EXCEPTION 'shared stream probe changes its owned build/key' USING ERRCODE='23514'; END IF;
 stream_id:=descriptor->>'stream_id';
 verified:=ops.pdf_shared_stream_ready(p_build,descriptor->>'encoding_profile',
 (descriptor->>'byte_length')::bigint,descriptor->>'byte_root'); RETURN NEXT;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.probe_pdf_shared_streams(text,bigint,bigint,text,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.probe_pdf_shared_streams(text,bigint,bigint,text,bytea) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.pdf_reclaim_pending_stream(p_project text,p_profile text,p_length bigint,p_root text)
RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE content ops.pdf_shared_stream; owner ops.pdf_stage_build; job ops.task;
BEGIN
 SELECT stored.* INTO STRICT content FROM ops.pdf_shared_stream stored WHERE stored.project_id=p_project
 AND stored.encoding_profile=p_profile AND stored.byte_length=p_length AND stored.byte_root=p_root FOR UPDATE;
 SELECT * INTO STRICT owner FROM ops.pdf_stage_build WHERE build_id=content.owner_build_id;
 SELECT * INTO STRICT job FROM ops.task WHERE id=owner.task_id;
 -- NOWAIT avoids waiting on an owner that is currently appending while holding
 -- its request/task locks. A caller retries its bounded admission transaction.
 PERFORM 1 FROM ops.data_request WHERE id=job.data_request_id FOR UPDATE NOWAIT;
 PERFORM 1 FROM ops.task WHERE id=job.id FOR UPDATE NOWAIT;
 PERFORM 1 FROM ops.pdf_stage_build WHERE build_id=owner.build_id FOR UPDATE NOWAIT;
 IF NOT ops.pdf_pending_stream_owner_dead(content) OR EXISTS(
 SELECT FROM ops.pdf_shared_stream_verification verified WHERE verified.project_id=p_project
 AND verified.encoding_profile=p_profile AND verified.byte_length=p_length AND verified.byte_root=p_root) THEN
 RAISE EXCEPTION 'shared stream is verified or still has a live append owner' USING ERRCODE='55P03'; END IF;
 IF EXISTS(SELECT FROM ops.pdf_stage_artifact_stream descriptor
 JOIN ops.pdf_stage_build dependent ON dependent.build_id=descriptor.product_id
 JOIN ops.task task ON task.id=dependent.task_id
 WHERE descriptor.encoding_profile=p_profile AND descriptor.byte_length=p_length AND descriptor.byte_root=p_root
 AND ops.pdf_stream_project(dependent.build_id)=p_project AND dependent.build_id<>owner.build_id
 AND dependent.state='open' AND task.status='running' AND task.lease_until>clock_timestamp()
 AND task.attempt=dependent.attempt AND task.claimed_by=dependent.holder) THEN
 RAISE EXCEPTION 'pending shared stream still has a live dependent build' USING ERRCODE='55P03'; END IF;
 DELETE FROM ops.pdf_shared_stream_part part WHERE part.project_id=p_project AND part.encoding_profile=p_profile
 AND part.stream_length=p_length AND part.byte_root=p_root;
 DELETE FROM ops.pdf_shared_stream stored WHERE stored.project_id=p_project AND stored.encoding_profile=p_profile
 AND stored.byte_length=p_length AND stored.byte_root=p_root;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_reclaim_pending_stream(text,text,bigint,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.pdf_cleanup_pending_build(p_build text) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE content ops.pdf_shared_stream;
BEGIN
 FOR content IN SELECT * FROM ops.pdf_shared_stream stored WHERE stored.owner_build_id=p_build
 AND NOT EXISTS(SELECT FROM ops.pdf_shared_stream_verification verified WHERE verified.project_id=stored.project_id
 AND verified.encoding_profile=stored.encoding_profile AND verified.byte_length=stored.byte_length AND verified.byte_root=stored.byte_root)
 ORDER BY stored.project_id,stored.encoding_profile,stored.byte_length,stored.byte_root LOOP
 PERFORM ops.pdf_reclaim_pending_stream(content.project_id,content.encoding_profile,content.byte_length,content.byte_root);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_cleanup_pending_build(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.pdf_shared_stream_mutation_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE row_ jsonb; content ops.pdf_shared_stream;
BEGIN
 IF TG_OP IN ('UPDATE','TRUNCATE') THEN RAISE EXCEPTION 'shared content cannot be updated or truncated' USING ERRCODE='23514'; END IF;
 row_:=CASE WHEN TG_OP='INSERT' THEN to_jsonb(NEW) ELSE to_jsonb(OLD) END;
 SELECT stored.* INTO STRICT content FROM ops.pdf_shared_stream stored WHERE stored.project_id=row_->>'project_id'
 AND stored.encoding_profile=row_->>'encoding_profile' AND stored.byte_root=row_->>'byte_root'
 AND stored.byte_length=coalesce((row_->>'stream_length')::bigint,(row_->>'byte_length')::bigint);
 IF EXISTS(SELECT FROM ops.pdf_shared_stream_verification verified WHERE verified.project_id=content.project_id
 AND verified.encoding_profile=content.encoding_profile AND verified.byte_length=content.byte_length AND verified.byte_root=content.byte_root) THEN
 RAISE EXCEPTION 'verified content is immutable' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
 IF ops.pdf_pending_stream_owner_dead(content) THEN RAISE EXCEPTION 'pending byte append fence is closed' USING ERRCODE='P0004'; END IF;
 RETURN NEW; END IF;
 IF NOT ops.pdf_pending_stream_owner_dead(content) THEN
 RAISE EXCEPTION 'verified content or live pending content is immutable' USING ERRCODE='23514'; END IF;
 RETURN OLD;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_shared_stream_mutation_guard() FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.pdf_adopt_shared_stream_descriptors(p_build text,p_streams regclass) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE stream ops.pdf_stage_artifact_stream%ROWTYPE; project text:=ops.pdf_stream_project(p_build); content ops.pdf_shared_stream; owner ops.pdf_stage_build;
BEGIN
 IF project IS NULL THEN RAISE EXCEPTION 'shared stream has no actual build project' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT owner FROM ops.pdf_stage_build WHERE build_id=p_build;
 FOR stream IN EXECUTE format('SELECT * FROM %s ORDER BY encoding_profile COLLATE "C",byte_length,byte_root COLLATE "C"',p_streams) LOOP
 -- The content row is the per-key lock; only one verifier can seal its actual fold.
 INSERT INTO ops.pdf_shared_stream VALUES(project,stream.encoding_profile,stream.byte_length,
 stream.byte_root,owner.build_id,owner.attempt,owner.holder) ON CONFLICT DO NOTHING;
 SELECT stored.* INTO STRICT content FROM ops.pdf_shared_stream stored
 WHERE stored.project_id=project AND stored.encoding_profile=stream.encoding_profile
 AND stored.byte_length=stream.byte_length AND stored.byte_root=stream.byte_root FOR UPDATE;
 IF NOT ops.pdf_shared_stream_ready(p_build,stream.encoding_profile,stream.byte_length,stream.byte_root)
 AND (content.owner_build_id,content.owner_attempt,content.owner_holder) IS DISTINCT FROM
 (owner.build_id,owner.attempt,owner.holder) THEN
 PERFORM ops.pdf_reclaim_pending_stream(project,stream.encoding_profile,stream.byte_length,stream.byte_root);
 INSERT INTO ops.pdf_shared_stream VALUES(project,stream.encoding_profile,stream.byte_length,stream.byte_root,
 owner.build_id,owner.attempt,owner.holder);
 END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_adopt_shared_stream_descriptors(text,regclass) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.pdf_adopt_shared_stream_parts(p_build text,p_parts regclass) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE part_product text; part_revision text; part_stream text; part_ordinal bigint;
 part_offset bigint; part_length bigint; part_body bytea; part_sha text;
 stream ops.pdf_stage_artifact_stream; project text:=ops.pdf_stream_project(p_build);
 retained ops.pdf_shared_stream_part; content ops.pdf_shared_stream; owner ops.pdf_stage_build;
BEGIN
 SELECT * INTO STRICT owner FROM ops.pdf_stage_build WHERE build_id=p_build;
 FOR part_product,part_revision,part_stream,part_ordinal,part_offset,part_length,part_body,part_sha
 IN EXECUTE format('SELECT product_id,revision_id,stream_id,ordinal,byte_offset,byte_length,body,sha256_digest FROM %s ORDER BY stream_id COLLATE "C",ordinal',p_parts) LOOP
 SELECT descriptor.* INTO stream FROM ops.pdf_stage_artifact_stream descriptor
 WHERE descriptor.product_id=p_build AND descriptor.revision_id=p_build AND descriptor.stream_id=part_stream;
 IF NOT FOUND THEN RAISE EXCEPTION 'shared parts require their descriptor before bytes' USING ERRCODE='23514'; END IF;
 IF part_product IS DISTINCT FROM p_build OR part_revision IS DISTINCT FROM p_build
 OR part_ordinal<0 OR part_offset<0 OR part_length NOT BETWEEN 1 AND 65536
 OR part_length<>octet_length(part_body) OR part_sha<>encode(sha256(part_body),'hex')
 OR part_offset+part_length>stream.byte_length THEN
 RAISE EXCEPTION 'shared stream incoming part differs from its descriptor/bytes' USING ERRCODE='23514'; END IF;
 SELECT stored.* INTO STRICT content FROM ops.pdf_shared_stream stored WHERE stored.project_id=project
 AND stored.encoding_profile=stream.encoding_profile AND stored.byte_length=stream.byte_length AND stored.byte_root=stream.byte_root FOR UPDATE;
 IF NOT ops.pdf_shared_stream_ready(p_build,stream.encoding_profile,stream.byte_length,stream.byte_root) THEN
 IF (content.owner_build_id,content.owner_attempt,content.owner_holder) IS DISTINCT FROM (owner.build_id,owner.attempt,owner.holder) THEN
 RAISE EXCEPTION 'pending shared parts belong to another append fence' USING ERRCODE='55P03'; END IF;
 INSERT INTO ops.pdf_shared_stream_part VALUES(project,stream.encoding_profile,stream.byte_length,stream.byte_root,
 part_ordinal,part_offset,part_length,part_body,part_sha) ON CONFLICT DO NOTHING;
 END IF;
 SELECT stored.* INTO retained FROM ops.pdf_shared_stream_part stored WHERE stored.project_id=project
 AND stored.encoding_profile=stream.encoding_profile AND stored.stream_length=stream.byte_length
 AND stored.byte_root=stream.byte_root AND stored.ordinal=part_ordinal;
 IF NOT FOUND OR (retained.byte_offset,retained.byte_length,retained.body,retained.sha256_digest) IS DISTINCT FROM
 (part_offset,part_length,part_body,part_sha) THEN
 RAISE EXCEPTION 'shared stream part replay differs' USING ERRCODE='23514'; END IF;
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_adopt_shared_stream_parts(text,regclass) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.pdf_verify_shared_stream(p_build text,p_stream text,p_complete boolean DEFAULT true)
RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE stream ops.pdf_stage_artifact_stream; project text:=ops.pdf_stream_project(p_build);
 part ops.pdf_shared_stream_part; state bytea; pending bytea:=''::bytea;
 next_ordinal bigint:=0; offset_ bigint:=0; block_ordinal bigint:=0; present bigint;
 content ops.pdf_shared_stream; owner ops.pdf_stage_build;
BEGIN
 SELECT descriptor.* INTO STRICT stream FROM ops.pdf_stage_artifact_stream descriptor
 WHERE descriptor.product_id=p_build AND descriptor.revision_id=p_build AND descriptor.stream_id=p_stream;
 SELECT stored.* INTO STRICT content FROM ops.pdf_shared_stream stored WHERE stored.project_id=project
 AND stored.encoding_profile=stream.encoding_profile AND stored.byte_length=stream.byte_length
 AND stored.byte_root=stream.byte_root FOR UPDATE;
 IF ops.pdf_shared_stream_ready(p_build,stream.encoding_profile,stream.byte_length,stream.byte_root) THEN RETURN; END IF;
 SELECT * INTO STRICT owner FROM ops.pdf_stage_build WHERE build_id=p_build;
 IF (content.owner_build_id,content.owner_attempt,content.owner_holder) IS DISTINCT FROM
 (owner.build_id,owner.attempt,owner.holder) THEN
 RAISE EXCEPTION 'pending fold belongs to another append fence' USING ERRCODE='55P03'; END IF;
 state:=ops.pdf_identity_fold_start('bytes');
 SELECT coalesce(sum(stored.byte_length),0) INTO present FROM ops.pdf_shared_stream_part stored
 WHERE stored.project_id=project AND stored.encoding_profile=stream.encoding_profile
 AND stored.stream_length=stream.byte_length AND stored.byte_root=stream.byte_root;
 IF NOT p_complete AND present<stream.byte_length THEN RETURN; END IF;
 FOR part IN SELECT * FROM ops.pdf_shared_stream_part stored WHERE stored.project_id=project
 AND stored.encoding_profile=stream.encoding_profile AND stored.stream_length=stream.byte_length
 AND stored.byte_root=stream.byte_root ORDER BY stored.ordinal LOOP
 IF part.ordinal<>next_ordinal OR part.byte_offset<>offset_ OR part.byte_length<>octet_length(part.body)
 OR part.byte_length NOT BETWEEN 1 AND 65536 OR part.sha256_digest<>encode(sha256(part.body),'hex') THEN
 RAISE EXCEPTION 'shared stream actual bytes/ordinal/offset/length/hash differs' USING ERRCODE='23514'; END IF;
 pending:=pending||part.body;
 WHILE octet_length(pending)>=65536 LOOP
 state:=ops.pdf_identity_fold_step(state,block_ordinal,substr(pending,1,65536));
 pending:=substr(pending,65537); block_ordinal:=block_ordinal+1;
 END LOOP;
 offset_:=offset_+part.byte_length; next_ordinal:=next_ordinal+1;
 END LOOP;
 IF octet_length(pending)>0 THEN state:=ops.pdf_identity_fold_step(state,block_ordinal,pending); block_ordinal:=block_ordinal+1; END IF;
 IF offset_<>stream.byte_length OR encode(ops.pdf_identity_fold_finish(state,block_ordinal,offset_),'hex')<>stream.byte_root THEN
 RAISE EXCEPTION 'shared stream actual fold differs from its content key' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.pdf_shared_stream_verification VALUES(project,stream.encoding_profile,stream.byte_length,
 stream.byte_root,next_ordinal) ON CONFLICT DO NOTHING;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_verify_shared_stream(text,text,boolean) FROM PUBLIC;
