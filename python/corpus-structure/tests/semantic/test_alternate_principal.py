"""Actual alternate reader authentication under the recoverable native lifecycle."""

from sqlalchemy import text

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from native_test_support import observe_engine


def test_alternate_reader_login_and_owner_base(semantic_db_engine, native_server):
    endpoint = semantic_db_engine.url
    database = endpoint.database
    assert database is not None
    base = endpoint.set(drivername="postgresql").render_as_string(hide_password=False)
    with native_server.alternate_reader(database) as role:
        settings = Settings(database={"url": base, "reader_url": f"postgresql://{role}@"})
        with open_runtime_engine(settings, purpose="read", timeout=5, max_size=1) as engine:
            observe_engine(engine, purpose="read")
            with engine.connect() as conn:
                assert conn.execute(text("SELECT current_user,session_user")).one() == (role, role)
        with open_runtime_engine(
            Settings(database={"url": base}), purpose="read", timeout=5, max_size=1
        ) as engine:
            observe_engine(engine, purpose="read")
            with engine.connect() as conn:
                assert conn.scalar(text("SELECT current_user")) == "corpus_sem_reader"
