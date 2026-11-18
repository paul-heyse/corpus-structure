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


def test_schema_wide_execute_effects_preserve_other_schemas():
    functions = {}
    update_function_inventory(
        functions,
        """
CREATE OR REPLACE FUNCTION eval.a() RETURNS bigint LANGUAGE sql AS $$SELECT 1$$;
CREATE OR REPLACE FUNCTION ops.b() RETURNS bigint LANGUAGE sql AS $$SELECT 2$$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA eval FROM PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA eval TO corpus_sem_evaluator;
""",
    )
    assert functions["eval.a()"]["execute_roles"] == ["corpus_sem_evaluator"]
    assert functions["ops.b()"]["execute_roles"] == ["PUBLIC"]


def test_function_rename_preserves_owner_acl_and_unrelated_overload_across_replacement():
    functions = {}
    update_function_inventory(
        functions,
        """SET LOCAL ROLE "owner X";
CREATE FUNCTION "odd S".before_name(a integer) RETURNS integer LANGUAGE sql AS $$SELECT a$$;
CREATE FUNCTION "odd S".before_name(a integer,b text) RETURNS integer LANGUAGE sql AS $$SELECT a$$;
REVOKE ALL ON FUNCTION "odd S".before_name(integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION "odd S".before_name(integer) TO "reader X";
""",
    )
    overload = dict(functions['"odd S".before_name(integer,text)'])
    update_function_inventory(
        functions,
        """SET LOCAL ROLE "migration X";
ALTER FUNCTION "odd S".before_name(int) RENAME TO "after :%";
CREATE OR REPLACE FUNCTION "odd S"."after :%"(a integer) RETURNS integer
LANGUAGE sql AS $$SELECT a+1$$;
""",
    )
    assert '"odd S".before_name(integer)' not in functions
    renamed = functions['"odd S"."after :%"(integer)']
    assert renamed["signature"] == '"odd S"."after :%"(integer)'
    assert renamed["owner"] == "owner X"
    assert renamed["execute_roles"] == ["reader X"]
    assert functions['"odd S".before_name(integer,text)'] == overload


def test_administration_nodes_preserve_quoted_identity_types_and_column_acl():
    from pglast import ast, enums, parse_sql

    from corpus_structure.semantic.native_objects import (
        NativeIdentity,
        native_owner_sql,
        native_privilege_sql,
        native_role_sql,
    )

    function = NativeIdentity("function", "odd S", "f :%", ("integer", "text[]"))
    grant = parse_sql(native_privilege_sql(function, "reader X", "EXECUTE", grant_option=True))[
        0
    ].stmt
    assert isinstance(grant, ast.GrantStmt)
    assert grant.grantees and grant.objects
    assert grant.grant_option and grant.grantees[0].rolename == "reader X"
    target = grant.objects[0]
    assert isinstance(target, ast.ObjectWithArgs) and target.objname and target.objargs
    assert [part.sval for part in target.objname] == ["odd S", "f :%"]
    assert target.objargs[1].arrayBounds
    owner = parse_sql(native_owner_sql(function, "owner X"))[0].stmt
    assert isinstance(owner, ast.AlterOwnerStmt) and owner.newowner is not None
    assert owner.newowner.rolename == "owner X"
    drop = parse_sql(function.drop_sql)[0].stmt
    assert isinstance(drop, ast.DropStmt) and drop.removeType == enums.ObjectType.OBJECT_FUNCTION
    table = NativeIdentity("table", "odd S", "t :%")
    revoke = parse_sql(
        native_privilege_sql(table, "PUBLIC", "REFERENCES", grant=False, column="x :%")
    )[0].stmt
    assert isinstance(revoke, ast.GrantStmt) and revoke.grantees and revoke.privileges
    assert not revoke.is_grant and revoke.behavior == enums.DropBehavior.DROP_RESTRICT
    assert revoke.grantees[0].roletype == enums.RoleSpecType.ROLESPEC_PUBLIC
    privilege = revoke.privileges[0]
    assert isinstance(privilege, ast.AccessPriv) and privilege.cols
    assert privilege.cols[0].sval == "x :%"
    role = parse_sql(native_role_sql("role's X"))[0].stmt
    assert isinstance(role, ast.VariableSetStmt) and role.is_local and role.args
    value = role.args[0]
    assert isinstance(value, ast.A_Const) and isinstance(value.val, ast.String)
    assert value.val.sval == "role's X"
