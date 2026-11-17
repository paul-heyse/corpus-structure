-- Current descriptors require an actual same-project shared-byte fold receipt.
-- Protected adoption verifies bytes once; guarded verified content is immutable.
-- Python replay separately checks each consumed part, stream root and optional SHA-256.
CREATE OR REPLACE FUNCTION ops.pdf_identity_verify_artifact(
 p_product text, p_revision text, p_stream text)
RETURNS TABLE(actual_length bigint, actual_byte_root bytea)
LANGUAGE plpgsql STABLE SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE stream_ ops.pdf_artifact_stream%ROWTYPE;
BEGIN
 SELECT * INTO STRICT stream_ FROM ops.pdf_artifact_stream
 WHERE product_id=p_product AND revision_id=p_revision AND stream_id=p_stream;
 IF NOT ops.pdf_shared_stream_ready(p_product,stream_.encoding_profile,stream_.byte_length,stream_.byte_root) THEN
 RAISE EXCEPTION 'artifact lacks its project-scoped actual fold receipt' USING ERRCODE='23514'; END IF;
 RETURN QUERY SELECT stream_.byte_length,decode(stream_.byte_root,'hex');
END $$;
REVOKE ALL ON FUNCTION ops.pdf_identity_verify_artifact(text,text,text) FROM PUBLIC;
