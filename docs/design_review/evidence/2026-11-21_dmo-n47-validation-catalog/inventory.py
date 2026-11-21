"""Compare direct schema validation calls in generated and installed native routines."""

import json
import re

from sqlalchemy import URL, create_engine, text

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.target_installation import (
    capture_target_installation,
    target_native_declarations,
)

SCHEMAS = ("app", "cp", "data", "eval", "kb", "ops", "sem")
CALL = re.compile(r"public[.]json_matches_schema\s*[(]", re.ASCII)

def source_inventory():
    installation = capture_target_installation(get_metadata())
    routines = {}
    for program in target_native_declarations(installation):
        identity = program.identity
        if identity.kind != "function" or identity.schema not in SCHEMAS:
            continue
        sites = len(CALL.findall(program.render()))
        if sites:
            key = (identity.schema, identity.name)
            assert key not in routines, key
            routines[key] = {
                "sites": sites,
                "source": program.source,
                "types": list(identity.arguments),
            }
    return routines

def catalog_inventory():
    engine = create_engine(URL.create(
        "postgresql+psycopg", username="paul", database="corpus_structure_ddo_stage",
        query={"host": "/var/run/postgresql", "port": "5434"},
    ))
    try:
        with engine.connect().execution_options(postgresql_readonly=True) as connection:
            target = connection.execute(text("""
                SELECT current_database(),
                       (SELECT oid FROM pg_database WHERE datname = current_database()),
                       (SELECT version_num FROM public.semantic_alembic_version)
            """)).one()
            assert tuple(target) == ("corpus_structure_ddo_stage", 130661481, "semantic_ddo_pe_n47")
            rows = connection.execute(
                text("""
                    SELECT n.nspname, p.proname, pg_get_function_identity_arguments(p.oid), p.prosrc
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname = ANY(:schemas)
                    ORDER BY n.nspname, p.proname, p.oid
                """),
                {"schemas": list(SCHEMAS)},
            ).all()
    finally:
        engine.dispose()
    routines = {}
    for schema, name, arguments, body in rows:
        sites = len(CALL.findall(body))
        if sites:
            assert (schema, name) not in routines, (schema, name)
            routines[schema, name] = {"sites": sites, "arguments": arguments}
    return routines

if __name__ == "__main__":
    declared, installed = source_inventory(), catalog_inventory()
    matched = sorted(set(declared) & set(installed))
    different = [key for key in matched if declared[key]["sites"] != installed[key]["sites"]]
    result = {
        "source_routines": len(declared), "installed_routines": len(installed),
        "source_only": sorted(set(declared) - set(installed)),
        "installed_only": sorted(set(installed) - set(declared)),
        "different_counts": different,
        "routines": [
            {"schema": schema, "routine": name, **declared[schema, name],
             "installed": installed[schema, name]}
            for schema, name in matched
        ],
    }
    print(json.dumps(result, indent=2))
