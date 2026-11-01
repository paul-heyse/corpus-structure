-- pdf-record-sha256-fold-v1. This is not the historical content_digest contract.
-- No incremental-hash extension, whole-document bytea, or aggregate manifest.
CREATE OR REPLACE FUNCTION ops.pdf_identity_frame(p_tag bytea, p_payload bytea)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
BEGIN
 IF octet_length(p_tag) <> 1 OR octet_length(p_payload) > 65536 THEN
  RAISE EXCEPTION 'identity frame requires one-byte tag and bounded payload' USING ERRCODE='23514';
 END IF;
 RETURN p_tag || int8send(octet_length(p_payload)::bigint) || p_payload;
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_fold_start(p_domain text)
RETURNS bytea LANGUAGE sql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
 SELECT sha256(convert_to('corpus.pdf.fold.v1/start','UTF8') || decode('00','hex') ||
  ops.pdf_identity_frame(convert_to('D','UTF8'),convert_to(p_domain,'UTF8')))
$$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_fold_step(p_state bytea, p_ordinal bigint, p_payload bytea)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
BEGIN
 IF octet_length(p_state) <> 32 OR p_ordinal < 0 THEN
  RAISE EXCEPTION 'identity fold state/ordinal invalid' USING ERRCODE='23514';
 END IF;
 RETURN sha256(convert_to('corpus.pdf.fold.v1/step','UTF8') || decode('00','hex') ||
  p_state || int8send(p_ordinal) || ops.pdf_identity_frame(convert_to('F','UTF8'),p_payload));
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_fold_finish(p_state bytea, p_count bigint, p_length bigint)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
BEGIN
 IF octet_length(p_state) <> 32 OR p_count < 0 OR p_length < 0 THEN
  RAISE EXCEPTION 'identity fold final inventory invalid' USING ERRCODE='23514';
 END IF;
 RETURN sha256(convert_to('corpus.pdf.fold.v1/end','UTF8') || decode('00','hex') ||
  p_state || int8send(p_count) || int8send(p_length));
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_byte_root(p_payload bytea)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE state bytea := ops.pdf_identity_fold_start('bytes');
 ordinal bigint := 0; offset_ integer := 1; block_ bytea;
BEGIN
 WHILE offset_ <= octet_length(p_payload) LOOP
  block_ := substr(p_payload,offset_,65536);
  state := ops.pdf_identity_fold_step(state,ordinal,block_);
  offset_ := offset_ + octet_length(block_); ordinal := ordinal + 1;
 END LOOP;
 RETURN ops.pdf_identity_fold_finish(state,ordinal,octet_length(p_payload));
END $$;

-- Validate UTF-8 including U+0000, which PostgreSQL text itself cannot hold.
CREATE OR REPLACE FUNCTION ops.pdf_identity_utf8(p_payload bytea)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE i integer := 0; c integer; c2 integer; width_ integer; j integer;
BEGIN
 WHILE i < octet_length(p_payload) LOOP
  c := get_byte(p_payload,i);
  IF c < 128 THEN i := i+1; CONTINUE;
  ELSIF c BETWEEN 194 AND 223 THEN width_ := 2;
  ELSIF c BETWEEN 224 AND 239 THEN width_ := 3;
  ELSIF c BETWEEN 240 AND 244 THEN width_ := 4;
  ELSE RETURN false;
  END IF;
  IF i+width_ > octet_length(p_payload) THEN RETURN false; END IF;
  c2 := get_byte(p_payload,i+1);
  IF (c=224 AND c2<160) OR (c=237 AND c2>=160) OR
     (c=240 AND c2<144) OR (c=244 AND c2>=144) THEN RETURN false; END IF;
  FOR j IN 1..width_-1 LOOP
   IF get_byte(p_payload,i+j) NOT BETWEEN 128 AND 191 THEN RETURN false; END IF;
  END LOOP;
  i := i+width_;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION ops.pdf_identity_scalar(p_kind text, p_payload bytea)
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE valid_ boolean := false; text_ text;
BEGIN
 IF p_kind IN ('a','n') THEN valid_ := octet_length(p_payload)=0;
 ELSIF p_kind='b' THEN
  IF octet_length(p_payload)=1 THEN valid_ := get_byte(p_payload,0) IN (0,1); END IF;
 ELSIF p_kind='i' THEN
  text_ := convert_from(p_payload,'UTF8');
  valid_ := text_ ~ '^(0|-?[1-9][0-9]*)$';
 ELSIF p_kind='f' THEN
  IF octet_length(p_payload)=8 THEN
   valid_ := NOT ((get_byte(p_payload,0) & 127)=127 AND (get_byte(p_payload,1) & 240)=240);
  END IF;
 ELSIF p_kind='s' THEN valid_ := ops.pdf_identity_utf8(p_payload);
 ELSIF p_kind='y' THEN valid_ := true;
 ELSIF p_kind='d' THEN
  text_ := convert_from(p_payload,'UTF8');
  valid_ := text_ ~ '^[01]:(0|[1-9][0-9]*):(0|-?[1-9][0-9]*)$';
 END IF;
 IF NOT valid_ THEN
  RAISE EXCEPTION 'noncanonical PDF record scalar kind %',p_kind USING ERRCODE='23514';
 END IF;
 RETURN convert_to(p_kind,'UTF8') || int8send(octet_length(p_payload)::bigint) ||
  ops.pdf_identity_byte_root(p_payload);
END $$;

-- Inputs are schema-declared fields, never an unordered jsonb object or whole document.
CREATE OR REPLACE FUNCTION ops.pdf_identity_record_frame(
 p_schema text, p_family text, p_key text, p_names text[], p_scalars bytea[])
RETURNS bytea LANGUAGE plpgsql IMMUTABLE STRICT SET search_path TO 'pg_catalog', 'pg_temp' AS $$
DECLARE body_ bytea; i integer; n integer := cardinality(p_names); names_ text[] := ARRAY[]::text[];
BEGIN
 IF p_schema='' OR p_family='' OR p_key='' OR n<>cardinality(p_scalars) OR
    COALESCE(array_lower(p_names,1),1)<>1 OR COALESCE(array_lower(p_scalars,1),1)<>1 THEN
  RAISE EXCEPTION 'record schema/family/key/fields invalid' USING ERRCODE='23514';
 END IF;
 body_ := ops.pdf_identity_frame(convert_to('s','UTF8'),convert_to(p_schema,'UTF8')) ||
  ops.pdf_identity_frame(convert_to('f','UTF8'),convert_to(p_family,'UTF8')) ||
  ops.pdf_identity_frame(convert_to('k','UTF8'),convert_to(p_key,'UTF8'));
 IF n>0 THEN
  FOR i IN 1..n LOOP
   IF p_names[i] IS NULL OR p_names[i]='' OR p_names[i]=ANY(names_) OR
      p_scalars[i] IS NULL OR octet_length(p_scalars[i])<>41 OR
      get_byte(p_scalars[i],0) NOT IN (97,110,98,105,102,115,121,100) OR
      get_byte(p_scalars[i],1)>127 THEN
    RAISE EXCEPTION 'record field name/scalar invalid' USING ERRCODE='23514';
   END IF;
   body_ := body_ || ops.pdf_identity_frame(convert_to('n','UTF8'),convert_to(p_names[i],'UTF8')) || p_scalars[i];
   IF octet_length(body_)+8>65527 THEN
    RAISE EXCEPTION 'record frame exceeds 64 KiB; lower collections into rows' USING ERRCODE='23514';
   END IF;
   names_ := array_append(names_,p_names[i]);
  END LOOP;
 END IF;
 IF octet_length(body_)+17>65536 THEN
  RAISE EXCEPTION 'record frame exceeds 64 KiB' USING ERRCODE='23514';
 END IF;
 RETURN ops.pdf_identity_frame(convert_to('R','UTF8'),int8send(n::bigint) || body_);
END $$;


REVOKE ALL ON FUNCTION ops.pdf_identity_frame(bytea,bytea),
 ops.pdf_identity_fold_start(text), ops.pdf_identity_fold_step(bytea,bigint,bytea),
 ops.pdf_identity_fold_finish(bytea,bigint,bigint), ops.pdf_identity_byte_root(bytea),
 ops.pdf_identity_utf8(bytea), ops.pdf_identity_scalar(text,bytea),
 ops.pdf_identity_record_frame(text,text,text,text[],bytea[]) FROM PUBLIC;
