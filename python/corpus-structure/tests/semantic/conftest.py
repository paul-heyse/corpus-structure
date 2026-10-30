"""Fresh committed native clones of one session-built frozen semantic deployment.

The bare/revision/name routes retain actual bootstrap and historical upgrade obligations.
All acquisition, leases, policy replay and disposal use the shared PgAdmin lifecycle.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Generator, Iterator
from contextlib import AbstractContextManager, contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text

from corpus_structure.core.db import extensions
from corpus_structure.semantic.migrations import upgrade
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, SemanticTemplate, principal_engine


def database_name(kind: str) -> str:
    return f"cs_sem_{kind}_{os.getpid()}_{uuid4().hex[:12]}"


@pytest.fixture
def semantic_db_engine(
    native_server: PgAdmin, semantic_head_template: SemanticTemplate
) -> Iterator[Engine]:
    with native_server.database(
        database_name("test"), semantic_head_template.name, policy=semantic_head_template.policy
    ) as engine:
        yield engine


@pytest.fixture
def semantic_bare_engine(native_server: PgAdmin) -> Iterator[Engine]:
    with native_server.database(database_name("bare"), native_server.template) as engine:
        with engine.begin() as conn:
            extensions.check(conn.execute(text(extensions.FOUND)).all())
            assert not conn.execute(
                text("SELECT 1 FROM pg_namespace WHERE nspname IN ('sem','data','kb','meta')")
            ).first()
        yield engine


@pytest.fixture
def semantic_database_at(native_server: PgAdmin) -> Callable[[str], AbstractContextManager[Engine]]:
    @contextmanager
    def at(revision: str) -> Generator[Engine]:
        with native_server.database(database_name("revision"), native_server.template) as engine:
            with engine.begin() as conn:
                upgrade(conn, revision)
            yield engine

    return at


@pytest.fixture
def semantic_writer_engine(
    native_settings: Settings, semantic_db_engine: Engine
) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "write", semantic_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def semantic_reader_engine(
    native_settings: Settings, semantic_db_engine: Engine
) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "read", semantic_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def semantic_evaluator_engine(
    native_settings: Settings, semantic_db_engine: Engine
) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "evaluate", semantic_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def semantic_admitter_engine(
    native_settings: Settings, semantic_db_engine: Engine
) -> Iterator[Engine]:
    engine = principal_engine(native_settings, "admit", semantic_db_engine.url.database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def admitter(semantic_admitter_engine: Engine) -> Engine:
    return semantic_admitter_engine
