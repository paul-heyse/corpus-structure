"""Observe role-wise binding plans on N35 with bounded authored relational inputs."""

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

ROOT = Path("/home/paul/corpus-structure")
sys.path[:0] = [
    str(ROOT / "python/corpus-structure/src"),
    str(ROOT / "python/corpus-structure/tests"),
    str(ROOT / "python/corpus-structure/tests/semantic"),
    str(ROOT / "scripts"),
]
from corpus_structure.semantic.data_operation_bindings import (
    binding_statement,
    compile_binding,
    execute_binding,
)
from corpus_structure.semantic.data_operation_model import BindingExpression
from semantic.test_data_operation_bindings import model, storage
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

folder = Path(__file__).resolve().parent
raw = folder / "raw"
engine = create_engine(
    URL.create(
        "postgresql+psycopg",
        username="paul",
        database="corpus_structure_ddo_stage",
        query={"host": "/var/run/postgresql", "port": "5434"},
    )
)
result = {
    "cases": [],
    "scope": "production binding compiler over authored independent row fixture; no whole-book composition or provider claim",
}
try:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            target = connection.execute(
                text(
                    "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),(SELECT version_num FROM public.semantic_alembic_version)"
                )
            ).one()
            assert (
                target[0] == "corpus_structure_ddo_stage"
                and target[1] == 130661481
                and target[2] == "semantic_ddo_pe_n35"
            )
            result["target"] = {
                "database": target[0],
                "oid": target[1],
                "revision": target[2],
            }
            connection.execute(text("SET LOCAL statement_timeout='30s'"))
            fixture = storage.__wrapped__(SimpleNamespace(connection=connection))
            connection, table, projection = next(fixture)
            prototype = dict(
                connection.execute(table.select().limit(1)).mappings().one()
            )
            for count in (2, 4, 8):
                connection.execute(table.delete())
                connection.execute(
                    table.insert(),
                    [
                        dict(
                            prototype,
                            product=f"p{index}",
                            member=f"m{index}",
                            position=index,
                            value=index,
                        )
                        for index in range(count)
                    ],
                )
                roles = tuple(f"role{index}" for index in range(8))
                schema = model(BindingExpression("scan", roles=roles), names=roles)
                compiled = compile_binding(
                    schema, "urn:op", (projection,), subject="doc"
                )
                statement = binding_statement(compiled)
                sql = str(
                    statement.compile(
                        dialect=connection.dialect,
                        compile_kwargs={"literal_binds": True},
                    )
                )
                (raw / f"role-binding-{count}.sql").write_text(sql + "\n")
                estimate = connection.exec_driver_sql(
                    "EXPLAIN (FORMAT JSON) " + sql
                ).scalar_one()
                plan = connection.exec_driver_sql(
                    "EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON) " + sql
                ).scalar_one()
                bound = execute_binding(connection, compiled)
                assert bound.sufficient and len(bound.roles) == 8
                assert all(len(role.members) == count for role in bound.roles)
                result["cases"].append(
                    {
                        "inputs": count,
                        "role_count": 8,
                        "selected_member_facts": sum(
                            len(role.members) for role in bound.roles
                        ),
                        "status": str(bound.status),
                        "estimate": estimate,
                        "observed": plan,
                    }
                )
                # A required role with no qualifying input must retain explicit unavailability.
                operation = schema.operations[0]
                missing = replace(
                    schema,
                    operations=(
                        replace(
                            operation,
                            roles=(
                                *operation.roles[:-1],
                                replace(operation.roles[-1], subject_field="base"),
                            ),
                        ),
                    ),
                )
                absent = execute_binding(
                    connection,
                    compile_binding(missing, "urn:op", (projection,), subject="doc"),
                )
                assert not absent.sufficient
                result["cases"][-1]["withheld_role"] = {
                    "status": str(absent.status),
                    "reasons": [reason.code for reason in absent.reasons],
                }
            try:
                next(fixture)
            except StopIteration:
                pass
            result["outcome"] = "passed"
        finally:
            transaction.rollback()
            result["rolled_back"] = True
finally:
    engine.dispose()
    (raw / "role-binding.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n"
    )
print(
    json.dumps(
        {
            **result,
            "cases": [
                {
                    key: value
                    for key, value in row.items()
                    if key not in ("estimate", "observed")
                }
                for row in result["cases"]
            ],
        }
    )
)
