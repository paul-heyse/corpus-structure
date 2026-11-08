"""SQL analysis and native admission authenticate sequentially without administrator writes."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.semantic.authored_sql import SQLAdmissionError, analyze_archived_sql
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import ActivationToken, activate_release

from .test_execution_release import _project, _stage_authored_sql


def test_sequential_restricted_sql_analysis_and_activation(
    semantic_db_engine,
    semantic_reader_engine,
    semantic_admitter_engine,
    semantic_application_settings,
):
    with semantic_db_engine.begin() as conn:
        prepared = _stage_authored_sql(conn)
        project = _project(conn)
        explicit_project = _project(conn)
    with semantic_reader_engine.connect() as reader:
        products = analyze_archived_sql(reader, prepared.release_id)
    assert len(products) == 1
    assert next(iter(products.values())).sql == "SELECT entity_id FROM data.entity"
    admission = semantic_admitter_engine
    with admission.begin() as conn:
        corrupted = {name: replace(value, sql="SELECT 'wrong'") for name, value in products.items()}
        with pytest.raises(SQLAdmissionError, match="binding differs"):
            activate_release(
                conn,
                project,
                prepared.release_id,
                expected_parent=None,
                expected_generation=0,
                sql_admissions=corrupted,
            )
        token = activate_release(
            conn,
            project,
            prepared.release_id,
            expected_parent=None,
            expected_generation=0,
            sql_admissions=products,
        )
        assert token == ActivationToken(prepared.release_id, 1)
        assert (
            conn.scalar(
                select(table("data.project").c.generation).where(
                    table("data.project").c.project_id == project
                )
            )
            == 1
        )

    invoked = CliRunner().invoke(
        app,
        [
            "release",
            "activate",
            prepared.release_id,
            "--project",
            explicit_project,
            "--target",
            "development",
            "--expected-generation",
            "0",
            "--json",
        ],
        obj=CliState(settings_factory=lambda: semantic_application_settings),
    )
    assert invoked.exit_code == 0, invoked.output
    assert json.loads(invoked.stdout)["generation"] == 1
    with semantic_db_engine.connect() as conn:
        selected = table("data.project")
        assert conn.execute(
            select(selected.c.active_release_id, selected.c.selected_result_run_id).where(
                selected.c.project_id == explicit_project
            )
        ).one() == (prepared.release_id, None)
