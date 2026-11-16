-- Current SourceValue operations, independent of record publication and predecessor history.
CREATE OR REPLACE FUNCTION data.report_field(value jsonb,member text) RETURNS jsonb LANGUAGE sql IMMUTABLE
RETURNS NULL ON NULL INPUT SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT (SELECT field->'value' FROM jsonb_array_elements(value->'fields') field
         WHERE field->>'name'=member) WHERE value->>'kind'='object'
$fn$;
REVOKE ALL ON FUNCTION data.report_field(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.record_source_float(p jsonb) RETURNS double precision
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE lexical text; digits text; exponent integer; result double precision;
BEGIN
 IF p->>'kind'='integer' THEN
  IF jsonb_typeof(p->'integer') IS DISTINCT FROM 'number' OR (p->>'integer') !~ '^-?(0|[1-9][0-9]*)$' THEN
   RAISE EXCEPTION 'source report integer must be an integer' USING ERRCODE='23514'; END IF;
  RETURN (p->>'integer')::double precision;
 END IF;
 IF p->>'kind' IS DISTINCT FROM 'float' OR jsonb_typeof(p->'hexadecimal') IS DISTINCT FROM 'string' THEN
  RAISE EXCEPTION 'record event score is not numeric' USING ERRCODE='23514'; END IF;
 lexical:=data.require_float_lexical(p->>'hexadecimal');
 digits:=replace(split_part(split_part(ltrim(lexical,'-'),'p',1),'x',2),'.','');
 exponent:=split_part(lexical,'p',2)::integer-52;
 -- The significand fits in 53 bits, and the binary scale is an exact finite
 -- power of two, including the smallest subnormal. Decimal numeric powers
 -- round negative exponents before multiplication and can alter the float.
 result:=(('x'||lpad(digits,16,'0'))::bit(64)::bigint)::double precision
  * power(2::double precision,exponent);
 IF left(lexical,1)='-' THEN result:=-result; END IF;
 RETURN result;
END $fn$;
REVOKE ALL ON FUNCTION data.record_source_float(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.record_source_json(p jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE result jsonb; kind text:=p->>'kind'; invalid_positions boolean; invalid_fields boolean; repeated_names boolean;
BEGIN
 IF p IS NULL THEN RETURN 'null'::jsonb; END IF;
 CASE kind
 WHEN 'null' THEN RETURN 'null'::jsonb;
 WHEN 'text','boolean','integer' THEN
  IF jsonb_typeof(p->kind) IS DISTINCT FROM (CASE kind WHEN 'text' THEN 'string' WHEN 'integer' THEN 'number' ELSE 'boolean' END)
   OR (kind='integer' AND (p->>'integer') !~ '^-?(0|[1-9][0-9]*)$') THEN
   RAISE EXCEPTION 'invalid source report % scalar',kind USING ERRCODE='23514'; END IF;
  RETURN p->kind;
 WHEN 'float' THEN RETURN to_jsonb(data.record_source_float(p));
 WHEN 'array' THEN
  IF p ? 'items' AND jsonb_typeof(p->'items') IS DISTINCT FROM 'array' THEN
   RAISE EXCEPTION 'source report items must be an array' USING ERRCODE='23514'; END IF;
  SELECT COALESCE(jsonb_agg(data.record_source_json(value) ORDER BY position),'[]') INTO result
   FROM jsonb_array_elements(COALESCE(p->'items','[]')) WITH ORDINALITY x(value,position);
  RETURN result;
 WHEN 'object' THEN
  IF p ? 'fields' AND jsonb_typeof(p->'fields') IS DISTINCT FROM 'array' THEN
   RAISE EXCEPTION 'source report fields must be an array' USING ERRCODE='23514'; END IF;
  SELECT bool_or(jsonb_typeof(value->'position') IS DISTINCT FROM 'number'
    OR value->>'position' IS DISTINCT FROM (position-1)::text),
   bool_or(jsonb_typeof(value->'name') IS DISTINCT FROM 'string' OR NOT value ? 'value'),
   count(*)<>count(DISTINCT (value->>'name') COLLATE "C")
   INTO invalid_positions,invalid_fields,repeated_names
   FROM jsonb_array_elements(COALESCE(p->'fields','[]')) WITH ORDINALITY x(value,position);
  IF invalid_positions THEN
   RAISE EXCEPTION 'source report fields are not contiguous and ordered' USING ERRCODE='23514'; END IF;
  IF invalid_fields THEN
   RAISE EXCEPTION 'source report field requires a string name and encoded value' USING ERRCODE='23514'; END IF;
  IF repeated_names THEN
   RAISE EXCEPTION 'source report contains a repeated field name' USING ERRCODE='23514'; END IF;
  SELECT COALESCE(jsonb_object_agg(value->>'name',data.record_source_json(value->'value')),'{}') INTO result
   FROM jsonb_array_elements(COALESCE(p->'fields','[]')) x(value);
  RETURN result;
 ELSE RAISE EXCEPTION 'unsupported sealed record event JSON' USING ERRCODE='23514';
 END CASE;
END $fn$;
REVOKE ALL ON FUNCTION data.record_source_json(jsonb) FROM PUBLIC;


-- Pure JSON meaning agrees with the fixed graph scalar/container ABI. No datatype
-- labels or source-product classes are introduced into graph values.
CREATE OR REPLACE FUNCTION data.record_json_meaning(p jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE result jsonb;
BEGIN
 CASE jsonb_typeof(p)
 WHEN 'null' THEN RETURN '["null"]'::jsonb;
 WHEN 'string' THEN RETURN jsonb_build_array('string',p);
 WHEN 'boolean' THEN RETURN jsonb_build_array('boolean',p);
 WHEN 'number' THEN RETURN jsonb_build_array('integer',p#>>'{}');
 WHEN 'array' THEN
  SELECT COALESCE(jsonb_agg(data.record_json_meaning(value) ORDER BY ord),'[]') INTO result
   FROM jsonb_array_elements(p) WITH ORDINALITY x(value,ord);
  RETURN jsonb_build_array('sequence',result);
 WHEN 'object' THEN
  SELECT COALESCE(jsonb_agg(jsonb_build_array(key,data.record_json_meaning(value)) ORDER BY key COLLATE "C"),'[]')
   INTO result FROM jsonb_each(p);
  RETURN jsonb_build_array('mapping',result);
 ELSE RAISE EXCEPTION 'unsupported record graph value' USING ERRCODE='23514';
 END CASE;
END $fn$;
REVOKE ALL ON FUNCTION data.record_json_meaning(jsonb) FROM PUBLIC;

