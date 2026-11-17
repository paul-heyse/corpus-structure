-- SQL-language scope projection binds its domain provider functions at CREATE.
-- Compose this captured declaration after the grade, fit and event providers.
CREATE OR REPLACE FUNCTION ops.ddo_support_scopes(project text,source text,support jsonb) RETURNS TABLE(scope text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 __DDO_CORE_LOCK_SUPPORT_SCOPES__
$$;
