"""The generated `MetaData` with the overlay applies on PostgreSQL 18 (model and projections §3.4).

On a throwaway database cloned from `cs_template` on the test server (18/corpus by default), named
under this session's `ci_test_<pid>` lease and dropped afterwards: `create_all` runs the extension
assertion, creates the schemas, tables, indexes and views; the views equal D3 §8's as PostgreSQL
deparses them; the assertion refuses an extension at another version than the record.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from corpus_structure.core import db
from corpus_structure.core.db import overlay

DATA = Path(__file__).resolve().parent / "data"
VIEW = re.compile(r"CREATE VIEW (\w+)\.(\w+) AS\n(.*?);", re.S)


@pytest.fixture(scope="module")
def created(db_server: Any) -> Iterator[Engine]:
    name = f"ci_test_{os.getpid()}_9101"  # under the session's lease (conftest, DA-019)
    db_server.create(name, db_server.template)
    engine = create_engine(db_server.url_of(name), poolclass=NullPool)
    try:
        db.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        db_server.drop(name)
        assert not db_server.exists(name)


def test_create_all_applies_every_table_index_and_view(created: Engine) -> None:
    with created.connect() as conn:
        version = conn.execute(text("SHOW server_version")).scalar()
        tables = set(
            conn.execute(
                text(
                    "SELECT schemaname || '.' || tablename FROM pg_tables"
                    " WHERE schemaname IN ('meta', 'ops', 'kb', 'eval')"
                )
            ).scalars()
        )
        views = set(
            conn.execute(
                text(
                    "SELECT schemaname || '.' || viewname FROM pg_views"
                    " WHERE schemaname IN ('meta', 'ops', 'kb', 'eval')"
                )
            ).scalars()
        )
        indexes = set(
            conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes"
                    " WHERE schemaname IN ('meta', 'ops', 'kb', 'eval')"
                )
            ).scalars()
        )
        bm25 = conn.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'segment_bm25'")
        ).scalar()
        checks = conn.execute(
            text(
                "SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace"
                " WHERE c.contype = 'c' AND n.nspname IN ('meta', 'ops', 'kb', 'eval')"
            )
        ).scalar()
    assert str(version).startswith("18.")
    expected = {t.fullname for t in db.metadata.tables.values() if not t.is_view}
    assert tables == expected
    assert views == {v.fullname for v in db.OVERLAY.views}
    assert {str(i.name) for i in db.OVERLAY.indexes} <= indexes
    assert "USING bm25" in str(bm25) and "'english'::regconfig" in str(bm25)
    declared = sum(
        1
        for t in db.metadata.tables.values()
        for c in t.constraints
        if c.__class__.__name__ == "CheckConstraint"
    )
    assert checks == declared


def test_the_views_equal_d3s_as_postgresql_deparses_them(created: Engine) -> None:
    reference = VIEW.findall((DATA / "d3_ddl.sql").read_text(encoding="utf-8"))
    assert {f"{s}.{n}" for s, n, _ in reference} == {v.fullname for v in db.OVERLAY.views}
    with created.begin() as conn:
        conn.execute(text("CREATE SCHEMA d3_reference"))
        try:
            for schema, name, body in reference:
                conn.execute(text(f"CREATE VIEW d3_reference.{name} AS {body}"))
                ours, theirs = (
                    conn.execute(
                        text("SELECT pg_get_viewdef(CAST(:v AS regclass), true)"), {"v": v}
                    ).scalar()
                    for v in (f"{schema}.{name}", f"d3_reference.{name}")
                )
                assert ours == theirs, name
        finally:
            conn.execute(text("DROP SCHEMA d3_reference CASCADE"))


def test_the_extension_assertion_refuses_another_version(created: Engine) -> None:
    expected = overlay.expected_extensions()
    assert expected["pg_textsearch"]  # the record names it (DA-018)
    with created.connect() as conn:
        conn.execute(text(overlay.extension_assertion(expected)))  # the recorded versions pass
        wrong = {**expected, "pg_textsearch": "0.0.0"}
        with pytest.raises(DBAPIError, match=r"pg_textsearch is 1\.5\.1, expected 0\.0\.0") as err:
            conn.execute(text(overlay.extension_assertion(wrong)))
        assert getattr(err.value.orig, "sqlstate", None) == "P0001"
        conn.rollback()
        with pytest.raises(DBAPIError, match=r"absent, expected 1\.0: run just db-provision"):
            conn.execute(text(overlay.extension_assertion({"no_such_extension": "1.0"})))


@pytest.mark.parametrize("reason", ["", "   ", "\t\n"])
def test_an_empty_parse_reason_is_refused_by_validator_and_database(
    created: Engine, reason: str
) -> None:
    from types import SimpleNamespace

    from corpus_structure.core._model import validators

    row = SimpleNamespace(parse_status="failed", parse_reason=reason, start_offset=0, end_offset=1)
    with pytest.raises(ValueError, match="parse_reason"):
        validators.kb_segment(row)
    validators.kb_segment(SimpleNamespace(**{**vars(row), "parse_reason": "unclosed $"}))
    with created.connect() as conn:
        conn.execute(
            text(
                "WITH p AS (INSERT INTO meta.project (name, domain) VALUES ('p', 'd')"
                "  RETURNING id),"
                " d AS (INSERT INTO kb.document (project_id, key, source_uri, content_hash,"
                "  original_path, mime) SELECT id, 'doc:x', 'u', 'h', 'o', 'text/html' FROM p"
                "  RETURNING id)"
                " INSERT INTO kb.rendition (document_id, key, content_digest, canonical_text,"
                "  parse_status) SELECT id, 'ren:x', 'c', 'ab', 'failed' FROM d"
            )
        )
        insert = text(
            "INSERT INTO kb.segment (rendition_id, key, kind, ordinal, depth, start_offset,"
            " end_offset, text, parse_status, parse_reason)"
            " SELECT id, :key, 'paragraph', 0, 0, 0, 1, 'a', 'failed', :reason FROM kb.rendition"
        )
        conn.execute(insert, {"key": "seg:ok", "reason": "unclosed $"})
        with pytest.raises(DBAPIError, match="ck_segment_parse_reason_") as err:
            conn.execute(insert, {"key": "seg:empty", "reason": reason})
        assert getattr(err.value.orig, "sqlstate", None) == "23514"
        conn.rollback()
