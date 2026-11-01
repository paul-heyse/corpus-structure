from corpus_structure.semantic.native_inventory import update_function_inventory
from corpus_structure.semantic.native_products import function_bodies
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_shared_source_preserves_properties_quoted_identity_owner_and_execute():
    sql = """SET LOCAL ROLE "role X";
CREATE OR REPLACE FUNCTION "odd S"."F :%"(a integer,OUT b text)
RETURNS text LANGUAGE sql STABLE STRICT SECURITY DEFINER PARALLEL SAFE
SET search_path=pg_catalog,pg_temp SET work_mem='64MB' AS $$SELECT 'x:100%'$$;
REVOKE ALL ON FUNCTION "odd S"."F :%"(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION "odd S"."F :%"(integer) TO "reader X";
ALTER FUNCTION "odd S"."F :%"(int) OWNER TO "owner X";
"""
    prepared = prepare_sql(sql, source="properties.sql")
    functions = {}
    assert update_function_inventory(functions, prepared) is prepared
    spec = functions['"odd S"."F :%"(integer)']
    assert spec["parallel"] == "s" and spec["strict"] and spec["security"]
    assert spec["volatility"] == "s" and not spec["leakproof"]
    assert spec["owner"] == "owner X" and spec["execute_roles"] == ["reader X"]
    assert spec["config"] == ["search_path=pg_catalog, pg_temp", "work_mem=64MB"]
    assert function_bodies(prepared)["odd S.F :%"] == "SELECT 'x:100%'"
    assert prepared.sql == sql
