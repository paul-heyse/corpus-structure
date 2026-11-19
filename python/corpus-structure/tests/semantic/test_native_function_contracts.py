"""Generated catalog predicates reject changes to native function contracts."""

import json

from sqlalchemy import Text, cast, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic.native_admission import execution_descriptor_program
from corpus_structure.semantic.native_admission_functions import _normalized_function_checks
from corpus_structure.semantic.native_catalog import procedure
from corpus_structure.semantic.native_products import literal_json_descriptor


def test_generated_descriptor_preserves_json_and_sql_sensitive_literals():
    expected = {
        "literal": "'%; $$ $descriptor$ \\ text",
        "unicode": "測試",
        "items": [1, None, True],
    }
    assert (
        literal_json_descriptor(
            execution_descriptor_program(expected).render(), "data.execution_contract_descriptor"
        )
        == expected
    )


def test_generated_function_guards_compare_config_defaults_and_complete_acl(
    infrastructure_rollback,
):
    from sqlalchemy import func

    connection = infrastructure_rollback
    connection.exec_driver_sql("""
        CREATE FUNCTION public.guard_contract(x integer DEFAULT 1) RETURNS integer
        LANGUAGE sql COST 7 SET statement_timeout=0 SET search_path=pg_catalog
        AS 'SELECT x'
    """)
    owner = connection.scalar(select(func.current_user()))
    expected = {
        "result_definition": "integer",
        "argument_definition": "x integer DEFAULT 1",
        "argument_defaults": "1",
        "cost": 7,
        "rows": 0,
        "support": "-",
        "catalog_acl": [["$migration_owner", "EXECUTE", False], ["PUBLIC", "EXECUTE", False]],
        "config": ["search_path=pg_catalog", "statement_timeout=0"],
    }

    def mismatch(descriptor):
        item = cast(literal(json.dumps(descriptor), Text()), JSONB())
        p = procedure.alias("p")
        configuration, changed = _normalized_function_checks(item, p, literal(owner, Text()))
        return connection.execute(
            select(changed, configuration.is_distinct_from(item["config"]))
            .select_from(p)
            .where(p.c.oid == func.to_regprocedure("public.guard_contract(integer)"))
        ).one()

    assert mismatch(expected) == (False, False)
    for key, replacement in (
        ("result_definition", "bigint"),
        ("argument_definition", "x bigint"),
        ("argument_defaults", "2"),
        ("cost", 8),
        ("rows", 1),
        ("support", "pg_catalog.abs"),
    ):
        assert mismatch({**expected, key: replacement})[0] is True
    assert mismatch({**expected, "config": ["search_path=public"]}) == (False, True)
    connection.exec_driver_sql(
        "GRANT EXECUTE ON FUNCTION public.guard_contract(integer) TO corpus_sem_reader WITH GRANT OPTION"
    )
    assert mismatch(expected)[0] is True
    expected["catalog_acl"].append(["corpus_sem_reader", "EXECUTE", False])
    assert mismatch(expected)[0] is True
    expected["catalog_acl"].append(["corpus_sem_reader", "EXECUTE", True])
    assert mismatch(expected) == (False, False)
    connection.exec_driver_sql("ALTER FUNCTION public.guard_contract(integer) COST 9")
    assert mismatch(expected)[0] is True
