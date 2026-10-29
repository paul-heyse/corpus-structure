"""New physical type boundaries; full release-bound streaming loaders belong to SP-05."""

from __future__ import annotations

from decimal import Decimal

import pyarrow as pa
from adbc_driver_postgresql import dbapi
from sqlalchemy import text

from corpus_structure.core.db.store import open_store
from corpus_structure.settings import DatabaseSettings, Settings


def test_adbc_exact_numeric_and_uncommitted_connection_boundary(
    semantic_db_engine, semantic_reader_engine
):
    uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    with semantic_db_engine.begin() as owner:
        owner.exec_driver_sql("CREATE TABLE public.semantic_interop (n numeric, lexical text, b bytea, flag boolean)")
        owner.exec_driver_sql("GRANT SELECT ON public.semantic_interop TO corpus_sem_reader")
        owner.execute(text("INSERT INTO public.semantic_interop VALUES (:n,:lexical,:b,:flag)"),
                      {"n": Decimal("123456789012345678901234567890.000001"),
                       "lexical": "1e200000", "b": b"\x00\xff", "flag": True})
    with dbapi.connect(uri) as conn, conn.cursor() as cursor:
        cursor.execute("SELECT n,lexical,b,flag FROM public.semantic_interop")
        with cursor.fetch_record_batch() as reader:
            result = reader.read_all()
        assert result.schema.field("n").type == pa.opaque(pa.string(), "numeric", "PostgreSQL")
        assert result.to_pylist() == [{"n": "123456789012345678901234567890.000001",
                                      "lexical": "1e200000", "b": b"\x00\xff", "flag": True}]
    # ADBC owns a different libpq session; it cannot participate in the COPY write transaction.
    with semantic_db_engine.begin() as owner:
        owner.exec_driver_sql("INSERT INTO public.semantic_interop(n) VALUES (2)")
        with dbapi.connect(uri) as conn, conn.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.semantic_interop")
            assert cursor.fetchone() == (1,)


def test_single_pool_returns_idle_connection_and_resets_isolation(semantic_writer_engine):
    uri = semantic_writer_engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    settings = Settings(database=DatabaseSettings(url=uri))
    with open_store(settings, "semantic-pool-test", min_size=1, max_size=1) as store:
        with store.engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn:
            with conn.begin():
                assert conn.exec_driver_sql("SHOW transaction_isolation").scalar_one() == "serializable"
                assert conn.exec_driver_sql("SELECT session_user").scalar_one() == "corpus_sem_writer"
        with store.engine.connect() as conn:
            assert conn.exec_driver_sql("SHOW transaction_isolation").scalar_one() == "read committed"
        assert store.pool.get_stats()["pool_available"] == 1
