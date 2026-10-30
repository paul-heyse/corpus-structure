"""SQL analysis and native admission authenticate sequentially without administrator writes."""

from dataclasses import replace

import pytest
from sqlalchemy import select

from corpus_structure.semantic.authored_sql import SQLAdmissionError, analyze_archived_sql
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import ActivationToken, activate_release

from .test_execution_release import _project, _stage_authored_sql


def test_sequential_restricted_sql_analysis_and_activation(
    semantic_db_engine, semantic_reader_engine, semantic_admitter_engine
):
    with semantic_db_engine.begin() as conn:
        prepared = _stage_authored_sql(conn)
        project = _project(conn)
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
