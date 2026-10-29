"""Native semantic databases: fresh extension-only clone, no legacy migration or sweeper.

The named principals are provisioned once with `just db-semantic-roles`; tests authenticate
as the restricted principals rather than SET ROLE from a database owner.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from corpus_structure.core.db import extensions
from corpus_structure.settings import Settings


@pytest.fixture
def semantic_db_engine() -> Iterator[Engine]:
    from corpus_structure.semantic.migrations import upgrade
    from corpus_structure.semantic.routines import deploy_routines

    settings = Settings()
    admin = create_engine(settings.database.sqlalchemy_url, poolclass=NullPool)
    url = admin.url
    server = create_engine(url.set(database="postgres"), poolclass=NullPool)
    name = f"cs_sem_test_{os.getpid()}_{uuid4().hex[:12]}"
    template = settings.database.template
    quote = server.dialect.identifier_preparer.quote
    engine = create_engine(url.set(database=name), poolclass=NullPool)
    try:
        with server.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            roles = set(conn.execute(text(
                "SELECT rolname FROM pg_roles WHERE rolname IN "
                "('corpus_sem_publisher','corpus_sem_writer','corpus_sem_reader')"
            )).scalars())
            if len(roles) != 3:
                pytest.fail("restricted semantic principals missing: run `just db-semantic-roles`")
            conn.exec_driver_sql(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(template)}")
        with engine.begin() as conn:
            extensions.check(conn.execute(text(extensions.FOUND)).all())
            # A template with application state is never an acceptable bootstrap.
            assert not conn.execute(text(
                "SELECT 1 FROM pg_namespace WHERE nspname IN ('sem','data','kb','meta')"
            )).first()
            upgrade(conn)
            deploy_routines(conn)
        yield engine
    finally:
        engine.dispose()
        admin.dispose()
        # libpq close can precede the server backend's final exit. An owner cannot terminate
        # another login's backend; wait briefly for its normal exit rather than widening roles.
        for attempt in range(40):
            try:
                with server.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    conn.exec_driver_sql(f"DROP DATABASE IF EXISTS {quote(name)}")
                break
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) != "55006" or attempt == 39:
                    raise
                time.sleep(0.05)
        server.dispose()


@pytest.fixture
def semantic_writer_engine(semantic_db_engine: Engine) -> Iterator[Engine]:
    engine = create_engine(
        semantic_db_engine.url.set(username="corpus_sem_writer"), poolclass=NullPool
    )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def semantic_reader_engine(semantic_db_engine: Engine) -> Iterator[Engine]:
    engine = create_engine(
        semantic_db_engine.url.set(username="corpus_sem_reader"), poolclass=NullPool
    )
    try:
        yield engine
    finally:
        engine.dispose()
