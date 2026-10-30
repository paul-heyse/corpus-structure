"""The source-frame native boundary attests routines, scoped relations and restricted ACLs."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .test_agent_resubmission import source_task


@pytest.mark.parametrize(
    "change,expected",
    [
        ("acl", "native source frame projection differs"),
        ("foreign_key", "native source frame projection differs"),
        ("helper", "native execution kernel differs: ops.source_statement_locator"),
    ],
)
def test_source_frame_deployment_drift_refuses_composed_admission(
    semantic_db_engine, semantic_writer_engine, tmp_path, change, expected
):
    prepared, _, task, _ = source_task(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )
    with semantic_writer_engine.begin() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.source_frame WHERE task_id=:task"), {"task": task}
            )
            == 1
        )
        conn.execute(
            text("SELECT data.require_execution_release(:release)"),
            {"release": prepared.release_id},
        )
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        if change == "acl":
            conn.exec_driver_sql("GRANT INSERT ON ops.source_frame TO corpus_sem_writer")
        elif change == "foreign_key":
            conn.exec_driver_sql(
                "ALTER TABLE ops.source_frame DROP CONSTRAINT fk_source_frame_task_id"
            )
        else:
            conn.exec_driver_sql(
                "CREATE OR REPLACE FUNCTION "
                "ops.source_statement_locator(p_task bigint,p_anchor text) RETURNS text "
                "LANGUAGE plpgsql STABLE SECURITY DEFINER "
                "SET search_path=pg_catalog,pg_temp "
                "AS $body$ BEGIN RETURN 'tampered'; END $body$"
            )
    with (
        semantic_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match=expected),
        conn.begin_nested(),
    ):
        conn.execute(
            text("SELECT data.require_execution_release(:release)"),
            {"release": prepared.release_id},
        )
