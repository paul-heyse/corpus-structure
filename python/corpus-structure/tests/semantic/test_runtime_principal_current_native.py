"""Current purpose admission requires real DDO capabilities on restricted principals."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


@pytest.mark.parametrize(
    ("purpose", "role", "capability"),
    [
        ("read", "reader", "ops.read_demand_result(jsonb)"),
        ("write", "writer", "ops.initialize_source_project(jsonb)"),
        ("evaluate", "evaluator", "ops.admit_authored_data(jsonb)"),
        ("admit", "admitter", "ops.inspect_data_execution(jsonb)"),
    ],
)
@pytest.mark.parametrize("missing_permission", ["function", "schema"])
def test_current_runtime_principal_requires_purpose_capability(
    request, commit_db_engine, purpose, role, capability, missing_permission
):
    engine = request.getfixturevalue("commit_" + role + "_engine")
    statement = text("SELECT data.require_runtime_principal(:purpose)")
    with engine.connect() as connection:
        connection.execute(statement, {"purpose": purpose})
    with commit_db_engine.connect() as connection, pytest.raises(DBAPIError) as refusal:
        connection.execute(statement, {"purpose": purpose})
    assert getattr(refusal.value.orig, "sqlstate", None) == "42501"

    with commit_db_engine.begin() as connection:
        if missing_permission == "function":
            connection.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        connection.execute(
            text(
                f"REVOKE EXECUTE ON FUNCTION {capability} FROM corpus_sem_{role}"
                if missing_permission == "function"
                else f"REVOKE USAGE ON SCHEMA ops FROM corpus_sem_{role}"
            )
        )
    with engine.connect() as connection, pytest.raises(DBAPIError) as refusal:
        connection.execute(statement, {"purpose": purpose})
    assert getattr(refusal.value.orig, "sqlstate", None) == "42501"
    assert "required runtime capability unavailable" in str(refusal.value)
