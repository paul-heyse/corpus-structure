-- Exact compact descriptor from canonical wire bytes, without a whole-envelope JSONB value.
CREATE OR REPLACE FUNCTION ops.pdf_product_descriptor(p_payload bytea) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $descriptor$
DECLARE result jsonb:='{}'; content_metadata jsonb:='{}'; field_name text; field_value json;
BEGIN
 FOR field_name,field_value IN SELECT key,value FROM json_each(convert_from(p_payload,'UTF8')::json) LOOP
  IF field_name='content' THEN
   SELECT COALESCE(jsonb_object_agg(key,value::jsonb),'{}'::jsonb) INTO content_metadata
    FROM json_each(field_value) WHERE key IN ('schema_digest','recipe_digest','health');
  ELSIF field_name<>ALL(ARRAY['occurrences','relations','coverage','inputs','mapping_reports']) THEN
   result:=result||jsonb_build_object(field_name,field_value::jsonb);
  END IF;
 END LOOP;
 IF result->>'kind'='integrated' THEN
  result:=result||jsonb_build_object('content_metadata',content_metadata);
 END IF;
 RETURN result;
END $descriptor$;
ALTER FUNCTION ops.pdf_product_descriptor(bytea) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.pdf_product_descriptor(bytea) FROM PUBLIC;
