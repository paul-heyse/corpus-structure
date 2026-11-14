"""Native fixture definitions registered once by the package conftest.

The bare/revision/name routes retain actual bootstrap and historical upgrade obligations.
All acquisition, leases, policy replay and disposal use the shared PgAdmin lifecycle.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from contextlib import AbstractContextManager, contextmanager

import pytest
from sqlalchemy import Engine, text

from corpus_structure.core.db import extensions
from corpus_structure.semantic.migrations import upgrade
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, SemanticDeployment, database_name, principal_engine


@pytest.fixture
def commit_db_engine(
    native_server: PgAdmin, semantic_head_template: SemanticDeployment
) -> Iterator[Engine]:
    with semantic_head_template.clone(database_name("test").name) as engine:
        yield engine


@pytest.fixture
def semantic_bare_engine(native_server: PgAdmin) -> Iterator[Engine]:
    native_server.semantic_ready()
    with native_server.database(database_name("bare").name, native_server.template) as engine:
        with engine.begin() as conn:
            extensions.check(conn.execute(text(extensions.FOUND)).all())
            assert not conn.execute(
                text("SELECT 1 FROM pg_namespace WHERE nspname IN ('sem','data','kb','meta')")
            ).first()
        yield engine


@pytest.fixture
def semantic_database_at(native_server: PgAdmin) -> Callable[[str], AbstractContextManager[Engine]]:
    native_server.semantic_ready()

    @contextmanager
    def at(revision: str) -> Generator[Engine]:
        with native_server.database(
            database_name("revision").name, native_server.template
        ) as engine:
            with engine.begin() as conn:
                upgrade(conn, revision)
            yield engine

    return at


@pytest.fixture
def commit_writer_engine(native_settings: Settings, commit_db_engine: Engine) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "write", commit_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def commit_reader_engine(native_settings: Settings, commit_db_engine: Engine) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "read", commit_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def commit_evaluator_engine(
    native_settings: Settings, commit_db_engine: Engine
) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "evaluate", commit_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def commit_admitter_engine(native_settings: Settings, commit_db_engine: Engine) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "admit", commit_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()
