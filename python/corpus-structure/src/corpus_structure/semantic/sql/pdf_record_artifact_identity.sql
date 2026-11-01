-- Foundation verifier only: publication/frozen-union admission is a later package.
-- New serialization_sha256 is independently verified by the Python byte reader.
-- A retained old bytea additionally supplies direct native byte correspondence and
-- its standard SHA-256, without pretending SHA256(part hashes) is SHA256(content).
CREATE OR REPLACE FUNCTION ops.pdf_identity_verify_artifact(
 p_product text, p_revision text, p_stream text, p_admitted bytea DEFAULT NULL)
RETURNS TABLE(actual_length bigint, actual_byte_root bytea, retained_correspondence boolean)
LANGUAGE plpgsql STABLE SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE stream_ ops.pdf_artifact_stream%ROWTYPE; part_ ops.pdf_artifact_part%ROWTYPE;
 state_ bytea := ops.pdf_identity_fold_start('bytes'); pending_ bytea := ''::bytea;
 next_ordinal bigint := 0; offset_ bigint := 0; block_ordinal bigint := 0; root_ bytea;
BEGIN
 SELECT * INTO STRICT stream_ FROM ops.pdf_artifact_stream
 WHERE product_id=p_product AND revision_id=p_revision AND stream_id=p_stream;
 FOR part_ IN SELECT * FROM ops.pdf_artifact_part
  WHERE product_id=p_product AND revision_id=p_revision AND stream_id=p_stream ORDER BY ordinal LOOP
  IF part_.ordinal<>next_ordinal OR part_.byte_offset<>offset_ OR
     part_.byte_length<>octet_length(part_.body) OR part_.byte_length NOT BETWEEN 1 AND 65536 OR
     part_.sha256_digest<>encode(sha256(part_.body),'hex') THEN
   RAISE EXCEPTION 'artifact actual bytes/ordinal/offset/length/digest differs' USING ERRCODE='23514';
  END IF;
  IF p_admitted IS NOT NULL THEN
   IF offset_+part_.byte_length>octet_length(p_admitted) OR
      part_.body<>substr(p_admitted,offset_::integer+1,part_.byte_length::integer) THEN
    RAISE EXCEPTION 'artifact bytes differ from already-admitted retained bytes' USING ERRCODE='23514';
   END IF;
  END IF;
  pending_ := pending_ || part_.body;
  WHILE octet_length(pending_)>=65536 LOOP
   state_ := ops.pdf_identity_fold_step(state_,block_ordinal,substr(pending_,1,65536));
   pending_ := substr(pending_,65537); block_ordinal := block_ordinal+1;
  END LOOP;
  offset_ := offset_+part_.byte_length; next_ordinal := next_ordinal+1;
 END LOOP;
 IF octet_length(pending_)>0 THEN
  state_ := ops.pdf_identity_fold_step(state_,block_ordinal,pending_); block_ordinal := block_ordinal+1;
 END IF;
 root_ := ops.pdf_identity_fold_finish(state_,block_ordinal,offset_);
 IF offset_<>stream_.byte_length OR encode(root_,'hex')<>stream_.byte_root THEN
  RAISE EXCEPTION 'artifact verified inventory/root differs' USING ERRCODE='23514';
 END IF;
 IF p_admitted IS NOT NULL AND (octet_length(p_admitted)<>offset_ OR
  encode(sha256(p_admitted),'hex')<>stream_.serialization_sha256) THEN
  RAISE EXCEPTION 'artifact retained byte length/standard SHA-256 differs' USING ERRCODE='23514';
 END IF;
 RETURN QUERY SELECT offset_,root_,p_admitted IS NOT NULL;
END $$;


REVOKE ALL ON FUNCTION ops.pdf_identity_verify_artifact(text,text,text,bytea) FROM PUBLIC;
