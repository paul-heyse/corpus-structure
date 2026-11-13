-- DDO-02 rollback-only framing helper for already normalized typed semantic values.
-- Deliberately unregistered: no existing native key ABI or migration changes.
-- This establishes canonical framing parity, not body validation or admission.
-- data.canonical_json remains the existing native deterministic JSON owner.
CREATE OR REPLACE FUNCTION pg_temp.ddo_canonical_input(domain text, version text, value jsonb)
RETURNS bytea
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF domain='' OR version<>'1' THEN
  RAISE EXCEPTION 'unsupported DDO identity domain/version' USING ERRCODE='23514';
 END IF;
 -- Typed numeric lexical/hex values travel as strings; raw JSONB number spelling
 -- must never participate in a semantic identity. Null has the explicit ["null"] tag.
 IF jsonb_typeof(value)<>'array' OR EXISTS (
  WITH RECURSIVE parts(item) AS (
   SELECT value
   UNION ALL
   SELECT child FROM parts
   CROSS JOIN LATERAL jsonb_array_elements(
    CASE WHEN jsonb_typeof(item)='array' THEN item ELSE '[]'::jsonb END
   ) AS children(child)
  ) SELECT FROM parts WHERE jsonb_typeof(item) NOT IN ('array','string','boolean')
 ) THEN
  RAISE EXCEPTION 'DDO identity requires normalized tagged values with numeric strings'
   USING ERRCODE='23514';
 END IF;
 RETURN convert_to(data.canonical_json(jsonb_build_array('ddo',domain,version,value)),'UTF8');
END $fn$;

CREATE OR REPLACE FUNCTION pg_temp.ddo_identity_digest(domain text, version text, value jsonb)
RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT encode(sha256(pg_temp.ddo_canonical_input(domain,version,value)),'hex')
$fn$;
