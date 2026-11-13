-- The constant is a lowering of the captured trusted protocol's closed schemas.
CREATE OR REPLACE FUNCTION ops.ddo_require_wire(operation text,direction text,value jsonb)
RETURNS void LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $wire$
DECLARE contracts constant jsonb := '__DDO_WIRE_CONTRACTS__'::jsonb; schema jsonb;
BEGIN
 IF direction NOT IN ('input','output') OR NOT contracts ? operation THEN
  RAISE EXCEPTION 'unknown native wire operation/direction' USING ERRCODE='23514';
 END IF;
 schema:=contracts->operation->direction;
 IF schema IS NULL OR value IS NULL
  OR NOT public.json_matches_schema(schema::json,value::json) THEN
  RAISE EXCEPTION 'native wire violates % % schema',operation,direction USING ERRCODE='23514';
 END IF;
END $wire$;
