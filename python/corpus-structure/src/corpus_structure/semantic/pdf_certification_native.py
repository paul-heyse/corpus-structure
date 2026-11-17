"""Native producer attestation and per-lowering/kind reconstruction oracle custody."""


def pdf_certification_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.pdf_lowering_identity(p_release text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE content_ bytea; contract_ jsonb; item_ jsonb;
BEGIN
 content_:=ops.pdf_contract_input(p_release,'implementation/pdf/lowering-contract.json');
 contract_:=convert_from(content_,'UTF8')::jsonb;
 IF contract_->>'profile' IS DISTINCT FROM 'pdf-record-lowering-contract-v1' THEN
 RAISE EXCEPTION 'unsupported released PDF lowering contract' USING ERRCODE='23514'; END IF;
 FOR item_ IN SELECT value FROM jsonb_array_elements(contract_->'inputs') LOOP
 IF left(item_->>'name',11)<>'pdf-domain/' OR encode(sha256(ops.pdf_contract_input(p_release,
 substr(item_->>'name',12))),'hex') IS DISTINCT FROM item_->>'sha256' THEN
 RAISE EXCEPTION 'released PDF lowering source/codec/schema custody differs' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN encode(sha256(content_),'hex');
END $$;
CREATE OR REPLACE FUNCTION ops.pdf_producer_stream_identity(p_build text,p_schema text)
RETURNS text LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE row_ record; state_ bytea:=ops.pdf_identity_fold_start('pdf-producer-streams-v1');
 frame_ bytea; count_ bigint:=0; total_ bigint:=0;
BEGIN
 FOR row_ IN SELECT * FROM ops.pdf_artifact_stream WHERE product_id=p_build AND revision_id=p_build
 ORDER BY stream_id COLLATE "C" LOOP
 frame_:=ops.pdf_identity_record_frame(p_schema,'producer-stream',row_.stream_id,
 ARRAY['byte_length','byte_root','encoding_profile','serialization_sha256'], ARRAY[
 ops.pdf_identity_scalar('i',convert_to(row_.byte_length::text,'UTF8')),
 ops.pdf_identity_scalar('s',convert_to(row_.byte_root,'UTF8')),
 ops.pdf_identity_scalar('s',convert_to(row_.encoding_profile,'UTF8')),
 CASE WHEN row_.serialization_sha256 IS NULL THEN ops.pdf_identity_scalar('n',''::bytea)
 ELSE ops.pdf_identity_scalar('s',convert_to(row_.serialization_sha256,'UTF8')) END]);
 state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
 count_:=count_+1; total_:=total_+octet_length(frame_);
 END LOOP;
 RETURN encode(ops.pdf_identity_fold_finish(state_,count_,total_),'hex');
END $$;
REVOKE ALL ON FUNCTION ops.pdf_producer_stream_identity(text,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.record_pdf_producer_certification(p_build text,p_task bigint,
 p_attempt bigint,p_holder text,p_lowering text,p_kind text,p_logical text,p_native text,p_streams text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build;
BEGIN
 b:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(b.release_id,'stage_pdf_producer');
 IF p_lowering IS DISTINCT FROM ops.pdf_lowering_identity(b.release_id)
 OR p_kind IS NULL OR p_kind NOT IN ('native','integrated') OR COALESCE(p_logical,'') !~ '^[0-9a-f]{64}$'
 OR COALESCE(p_native,'') !~ '^[0-9a-f]{64}$' OR COALESCE(p_streams,'') !~ '^[0-9a-f]{64}$' THEN
 RAISE EXCEPTION 'PDF producer certification basis differs' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.pdf_producer_certification(build_id,attempt,holder,lowering_identity,kind,
 logical_digest,native_document_digest,stream_inventory_digest,source_digest,recipe_digest,schema_digest)
 VALUES(p_build,p_attempt,p_holder,p_lowering,p_kind,p_logical,p_native,p_streams,b.source_digest,b.recipe_digest,b.schema_digest)
 ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_producer_certification c WHERE c.build_id=p_build
 AND c.lowering_identity=p_lowering AND c.kind=p_kind AND c.logical_digest=p_logical
 AND c.native_document_digest=p_native AND c.stream_inventory_digest=p_streams AND c.source_digest=b.source_digest
 AND c.recipe_digest=b.recipe_digest AND c.schema_digest=b.schema_digest) THEN
 RAISE EXCEPTION 'changed PDF producer certification' USING ERRCODE='23514'; END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.read_pdf_certification_requirement(p_build text,p_task bigint,
 p_attempt bigint,p_holder text,p_frozen text)
RETURNS TABLE(lowering_identity text,kind text,logical_digest text,native_document_digest text,
 oracle_receipt_id text,certification_basis text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; c ops.pdf_producer_certification; oracle_ text; basis_ text;
BEGIN
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 SELECT * INTO STRICT c FROM ops.pdf_producer_certification WHERE build_id=p_build;
 IF c.lowering_identity IS DISTINCT FROM ops.pdf_lowering_identity(b.release_id)
 OR (c.source_digest,c.recipe_digest,c.schema_digest,c.kind) IS DISTINCT FROM
 (b.source_digest,b.recipe_digest,b.schema_digest,(SELECT f.kind FROM ops.pdf_frozen_build f WHERE f.build_id=p_build)) THEN
 RAISE EXCEPTION 'frozen PDF producer certification differs' USING ERRCODE='23514'; END IF;
 SELECT o.oracle_receipt_id INTO oracle_ FROM ops.pdf_roundtrip_oracle o
 WHERE o.build_id=p_build AND o.frozen_digest=p_frozen AND o.lowering_identity=c.lowering_identity
 AND o.kind=c.kind AND o.logical_digest=c.logical_digest AND o.native_document_digest=c.native_document_digest
 AND o.state='passed' ORDER BY o.oracle_receipt_id LIMIT 1;
 basis_:='round-trip-verified';
 IF oracle_ IS NULL THEN
 SELECT o.oracle_receipt_id INTO oracle_ FROM ops.pdf_roundtrip_oracle o
 JOIN ops.pdf_published_revision p ON p.build_id=o.build_id AND p.frozen_digest=o.frozen_digest
 AND p.logical_digest=o.logical_digest AND p.kind=o.kind
 JOIN ops.pdf_build_validation v ON v.build_id=p.build_id AND v.frozen_digest=p.frozen_digest
 AND v.logical_digest=p.logical_digest AND v.oracle_receipt_id=o.oracle_receipt_id
 WHERE o.lowering_identity=c.lowering_identity AND o.kind=c.kind AND o.state='passed'
 ORDER BY o.oracle_receipt_id LIMIT 1;
 basis_:='producer-certified';
 END IF;
 RETURN QUERY SELECT c.lowering_identity,c.kind,c.logical_digest,c.native_document_digest,oracle_,basis_;
END $$;
CREATE OR REPLACE FUNCTION ops.begin_pdf_roundtrip_oracle(p_build text,p_task bigint,p_attempt bigint,
 p_holder text,p_frozen text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; c record; index_ bigint; id_ text;
BEGIN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM 1 FROM ops.pdf_stage_build WHERE build_id=p_build FOR NO KEY UPDATE;
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 SELECT * INTO STRICT c FROM ops.read_pdf_certification_requirement(p_build,p_task,p_attempt,p_holder,p_frozen);
 SELECT count(*) INTO index_ FROM ops.pdf_roundtrip_oracle WHERE build_id=p_build;
 id_:=encode(sha256(convert_to(jsonb_build_array(p_build,p_frozen,c.lowering_identity,p_attempt,p_holder,index_)::text,'UTF8')),'hex');
 INSERT INTO ops.pdf_roundtrip_oracle(oracle_receipt_id,build_id,attempt,holder,frozen_digest,
 lowering_identity,kind,logical_digest,native_document_digest,state)
 VALUES(id_,p_build,p_attempt,p_holder,p_frozen,c.lowering_identity,c.kind,c.logical_digest,c.native_document_digest,'running');
 RETURN id_;
END $$;
CREATE OR REPLACE FUNCTION ops.finish_pdf_roundtrip_oracle(p_build text,p_task bigint,p_attempt bigint,
 p_holder text,p_frozen text,p_oracle text,p_state text,p_actual text,p_error text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; o ops.pdf_roundtrip_oracle;
BEGIN
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 SELECT * INTO STRICT o FROM ops.pdf_roundtrip_oracle WHERE oracle_receipt_id=p_oracle FOR UPDATE;
 IF (o.build_id,o.attempt,o.holder,o.frozen_digest) IS DISTINCT FROM (p_build,p_attempt,p_holder,p_frozen)
 OR p_state NOT IN ('passed','failed','interrupted') OR p_state IS NULL
 OR (p_state='passed' AND (p_actual IS DISTINCT FROM o.native_document_digest OR p_error IS NOT NULL))
 OR (p_state<>'passed' AND nullif(p_error,'') IS NULL) THEN
 RAISE EXCEPTION 'PDF round-trip oracle result differs from original producer' USING ERRCODE='23514'; END IF;
 IF o.state<>'running' THEN
 IF (o.state,o.actual_native_digest,o.error_message) IS NOT DISTINCT FROM (p_state,p_actual,p_error) THEN RETURN; END IF;
 RAISE EXCEPTION 'completed PDF oracle receipt is immutable' USING ERRCODE='23514'; END IF;
 UPDATE ops.pdf_roundtrip_oracle SET state=p_state,actual_native_digest=p_actual,error_message=p_error
 WHERE oracle_receipt_id=p_oracle;
END $$;
CREATE OR REPLACE FUNCTION ops.read_pdf_certification_targets(p_build text,p_task bigint,p_attempt bigint,
 p_holder text,p_targets jsonb)
RETURNS bytea LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; item_ jsonb; result_ jsonb:='[]'; meaning_ jsonb;
BEGIN
 b:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 IF jsonb_typeof(p_targets) IS DISTINCT FROM 'array' OR jsonb_array_length(p_targets)>512 THEN RAISE EXCEPTION 'PDF producer targets must be a bounded array'; END IF;
 FOR item_ IN SELECT value FROM jsonb_array_elements(p_targets) LOOP
 meaning_:=ops.pdf_identity_published_target((item_->>0)::bigint,item_->>1,item_->>2);
 IF meaning_->>'source_digest' IS DISTINCT FROM b.source_digest THEN
 RAISE EXCEPTION 'PDF producer target changes original source' USING ERRCODE='23514'; END IF;
 result_:=result_||jsonb_build_array(jsonb_build_object('pin',item_,'meaning',meaning_));
 END LOOP;
 RETURN convert_to(result_::text,'UTF8');
END $$;
REVOKE ALL ON FUNCTION ops.pdf_lowering_identity(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.record_pdf_producer_certification(text,bigint,bigint,text,text,text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.read_pdf_certification_requirement(text,bigint,bigint,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.begin_pdf_roundtrip_oracle(text,bigint,bigint,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.finish_pdf_roundtrip_oracle(text,bigint,bigint,text,text,text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.read_pdf_certification_targets(text,bigint,bigint,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.record_pdf_producer_certification(text,bigint,bigint,text,text,text,text,text,text),
 ops.read_pdf_certification_requirement(text,bigint,bigint,text,text),
 ops.begin_pdf_roundtrip_oracle(text,bigint,bigint,text,text),
 ops.finish_pdf_roundtrip_oracle(text,bigint,bigint,text,text,text,text,text,text),
 ops.read_pdf_certification_targets(text,bigint,bigint,text,jsonb) TO corpus_sem_writer;
"""
