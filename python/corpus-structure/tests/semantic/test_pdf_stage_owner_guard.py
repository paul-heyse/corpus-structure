"""Actual source-authored PDF owner guard, with both lock paths statically checked."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.native_candidate import _pdf_payload_definitions
from corpus_structure.semantic.native_objects import (
    NativeIdentity,
    execute_native_sql,
    native_owner,
    prepare_native_authoring,
)
from corpus_structure.semantic.pdf_staging_native import stage_native_sql

from .pdf_staging_support import _private_build_factory


def test_current_pdf_stage_owner_static_check_and_actual_legacy_fence(
    semantic_db_engine, semantic_writer_engine, tmp_path, request,
):
    identity = NativeIdentity("function", "ops", "require_pdf_stage_owner", ("bigint", "bigint", "text"))
    with semantic_db_engine.begin() as connection:
        selected = next(
            item for item in _pdf_payload_definitions(
                connection, stage_native_sql(), source="current PDF owner guard", current_source=True,
            ) if item.identity == identity
        )
        # The authoring checker traverses both the legacy and request-backed branches
        # against the real installed row types and native dependencies.
        prepared = prepare_native_authoring(
            connection, (selected,), owned_authoring=True, check_plpgsql=frozenset({identity}),
        )
        assert prepared.desired[0].identity == identity
        with native_owner(connection, selected.owner):
            execute_native_sql(connection, selected.sql)
    build = _private_build_factory(
        semantic_db_engine, semantic_writer_engine, tmp_path, request,
    )()
    with semantic_db_engine.connect() as connection:
        parameters = {"task": build.task_id, "attempt": build.attempt, "holder": build.holder}
        query = text("SELECT * FROM ops.require_pdf_stage_owner(:task,:attempt,:holder)")
        context = connection.execute(query, parameters).mappings().one()
        assert context["project_id"] == "p"
        assert context["release_id"] == build.release_id
        assert context["run_id"] > 0
        assert context["request_id"] is None and context["generation"] is None
        assert context["document_id"] > 0
        assert context["source_digest"] == build.source_digest
        for change in ({"holder": "different-owner"}, {"attempt": build.attempt + 1}):
            with connection.begin_nested() as savepoint:
                with pytest.raises(DBAPIError, match="stale private PDF build owner"):
                    connection.execute(query, {**parameters, **change})
                savepoint.rollback()
