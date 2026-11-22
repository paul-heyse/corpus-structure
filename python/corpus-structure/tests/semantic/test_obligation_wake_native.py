"""Actual PostgreSQL snapshot controls for sparse work, not full scheduler qualification."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateIndex, CreateTable

from corpus_structure.semantic.data_read_boundary_native import read_boundary_native_programs
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.obligation_wake_native import obligation_wake_programs


@pytest.fixture
def wake_controls(infrastructure_commit_engine):
    engine = infrastructure_commit_engine
    model = get_metadata()
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA ops")
        for name in ("ops.data_demand_read", "ops.data_obligation_wake"):
            table = model.tables[name]
            connection.execute(CreateTable(table, include_foreign_key_constraints=[]))
            for index in table.indexes:
                connection.execute(CreateIndex(index))
        for routine in read_boundary_native_programs(model):
            if routine.name == "ddo_read_visible":
                connection.exec_driver_sql(routine.render())
        for declaration in obligation_wake_programs(model):
            if declaration.identity.name in {"ddo_read_xmin", "ddo_sparse_obligation_wake_changed"}:
                connection.exec_driver_sql(declaration.render())
    return engine


def _read(connection, name):
    connection.execute(
        text("""
        INSERT INTO ops.data_demand_read
          (id,demand_id,read_snapshot,frontier_at,owner_xid,trust_snapshot)
        VALUES (:name,'demand',pg_current_snapshot()::text,clock_timestamp(),
                pg_current_xact_id()::text,'{}'::jsonb)
    """),
        {"name": name},
    )


def _wake(connection, key="wake", obligation="obligation"):
    connection.execute(
        text("""
        INSERT INTO ops.data_obligation_wake
          (id,obligation_id,origin_kind,origin_id,input_role,occurrence,created_at,created_xid)
        VALUES (:key,:obligation,'fulfilled-use','origin','input','{}'::jsonb,
                clock_timestamp(),pg_current_xact_id()::text::numeric)
        ON CONFLICT DO NOTHING
    """),
        {"key": key, "obligation": obligation},
    )


def _changed(connection, before="before", after="after", obligation="obligation"):
    return connection.scalar(
        text("SELECT ops.ddo_sparse_obligation_wake_changed(:obligation,:before,:after)"),
        dict(obligation=obligation, before=before, after=after),
    )


@pytest.mark.parametrize(
    "origin_relation", ["demand_use", "original_source_admission", "data_population"]
)
@pytest.mark.parametrize("origin_first", [False, True])
def test_immediate_native_demand_fk_serializes_discovery_enrollment(
    wake_controls, origin_relation, origin_first
):
    """The existing FOR UPDATE discovery gate conflicts with origin FK key-share.

    This isolates PostgreSQL locking, not a full discovery execution. The model
    assertion binds the small two-column control to the actual immediate FK.
    """
    table = get_metadata().tables["ops." + origin_relation]
    demand_fk = next(
        fk
        for fk in table.foreign_key_constraints
        if fk.referred_table.fullname == "ops.data_demand"
    )
    assert not demand_fk.deferrable
    with wake_controls.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE ops.data_demand(id text PRIMARY KEY)")
        connection.exec_driver_sql("INSERT INTO ops.data_demand VALUES ('demand')")
        connection.exec_driver_sql(
            f"CREATE TABLE ops.{origin_relation}(id text PRIMARY KEY,demand_id text REFERENCES ops.data_demand(id))"
        )
    with wake_controls.connect() as first, wake_controls.connect() as second:
        first.begin()
        second.begin()
        second.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
        origin = f"INSERT INTO ops.{origin_relation} VALUES ('origin','demand')"
        enrollment = "SELECT 1 FROM ops.data_demand WHERE id='demand' FOR UPDATE"
        first.exec_driver_sql(origin if origin_first else enrollment)
        with pytest.raises(DBAPIError, match="lock timeout"):
            second.exec_driver_sql(enrollment if origin_first else origin)
        second.rollback()
        first.rollback()


@pytest.mark.parametrize("origin_started_first", [False, True])
def test_sparse_wake_observes_both_publication_wait_commit_orders(
    wake_controls, origin_started_first
):
    engine = wake_controls
    with engine.connect() as publisher:
        transaction = publisher.begin()
        if origin_started_first:
            publisher.scalar(text("SELECT pg_current_xact_id()"))
        with engine.begin() as reader:
            _read(reader, "before")
        _wake(publisher)
        transaction.commit()
    with engine.begin() as reader:
        _read(reader, "after")
        assert _changed(reader) is True
        assert _changed(reader, obligation="unrelated") is False
        assert _changed(reader, before="after") is False
        assert _changed(reader) is True


def test_sparse_wake_preserves_top_level_identity_and_same_transaction_retries(wake_controls):
    with wake_controls.begin() as connection:
        _read(connection, "before")
        top = connection.scalar(text("SELECT pg_current_xact_id()::text"))
        with connection.begin_nested():
            _wake(connection)
            assert (
                connection.scalar(text("SELECT created_xid::text FROM ops.data_obligation_wake"))
                == top
            )
        _wake(connection)
        _read(connection, "after")
        assert _changed(connection) is True
        assert connection.scalar(text("SELECT count(*) FROM ops.data_obligation_wake")) == 1
        assert _changed(connection, before="after") is False


def test_sparse_wake_rollbacks_do_not_create_work(wake_controls):
    with wake_controls.begin() as connection:
        _read(connection, "before")
        savepoint = connection.begin_nested()
        _wake(connection)
        savepoint.rollback()
        _read(connection, "after")
        assert _changed(connection) is False


def test_sparse_wake_retains_repeatable_read_visibility_until_a_fresh_cut(wake_controls):
    with (
        wake_controls.connect().execution_options(isolation_level="REPEATABLE READ") as reader,
        reader.begin(),
    ):
        _read(reader, "before")
        with wake_controls.begin() as publisher:
            _wake(publisher)
        _read(reader, "pinned-after")
        assert _changed(reader, after="pinned-after") is False
    with wake_controls.begin() as reader:
        _read(reader, "after")
        assert _changed(reader) is True
