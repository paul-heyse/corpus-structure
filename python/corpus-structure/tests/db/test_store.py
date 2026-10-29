"""`open_store` (P0-F-4): the pool, the startup version check outside `configure`, error classes."""

from __future__ import annotations

import time
from typing import Any

import psycopg
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from corpus_structure.core.db import extensions, store
from corpus_structure.settings import Settings


def settings_for(engine: Engine) -> Settings:
    url = make_url(engine.url).set(drivername="postgresql")
    return Settings(database={"url": url.render_as_string(hide_password=False)})


def test_the_store_opens_and_lends_its_pool(db_engine: Engine) -> None:
    with store.open_store(settings_for(db_engine), "test-store") as opened:
        with opened.engine.connect() as conn:
            assert conn.execute(text("SELECT current_setting('application_name')")).scalar() == (
                "test-store"
            )
            value = conn.execute(text("SELECT CAST(:v AS jsonb)"), {"v": '{"a": "é"}'}).scalar()
            assert value == {"a": "é"}
        assert opened.pool.get_stats()["pool_size"] >= 1


def test_an_extension_at_another_version_fails_startup_with_the_typed_error(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    wrong = {**extensions.expected_extensions(), "pg_textsearch": "0.0.1"}
    monkeypatch.setattr(extensions, "expected_extensions", lambda path=None: wrong)
    started = time.monotonic()
    with pytest.raises(extensions.ExtensionVersionMismatch) as err:
        store.open_store(settings_for(db_engine), "test-store", timeout=20)
    assert time.monotonic() - started < 10  # refused at once, not after the pool's timeout
    assert err.value.wrong == {"pg_textsearch": ("0.0.1", "1.5.1")}
    assert "just db-provision" in str(err.value)


def test_errors_are_classified(db: Any) -> None:
    deadlock = psycopg.errors.DeadlockDetected("deadlock")
    assert store.classify_error(deadlock) is store.ErrorClass.RETRY
    with pytest.raises(DBAPIError) as err, db.begin_nested():
        db.execute(text("SELECT 1/0"))
    assert store.classify_error(err.value) is store.ErrorClass.DEFECT
    with pytest.raises(IntegrityError) as dup, db.begin_nested():
        db.execute(
            text("CREATE TEMP TABLE t (x int CONSTRAINT uq_observation_task_id_ordinal UNIQUE)")
        )
        db.execute(text("INSERT INTO t VALUES (1), (1)"))
    assert store.classify_error(dup.value) is store.ErrorClass.FENCING
