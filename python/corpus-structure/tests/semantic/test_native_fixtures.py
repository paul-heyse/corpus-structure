"""Independent native lifecycle, clone-policy and authenticated-principal controls (SP-I08)."""

from __future__ import annotations

import threading
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from native_test_support import principal_engine
from test_prerequisites import PrerequisiteUnavailable


def name(kind="test"):
    return f"cs_sem_{kind}_999999999_{uuid4().hex[:12]}"


def test_head_is_sealed_and_has_no_migration_backend(native_server, semantic_head_template):
    with native_server.connect() as conn:
        assert conn.execute(
            text("SELECT datallowconn,datistemplate FROM pg_database WHERE datname=:n"),
            {"n": semantic_head_template.name},
        ).one() == (False, False)
        assert (
            conn.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname=:n"),
                {"n": semantic_head_template.name},
            ).scalar_one()
            == 0
        )
    with (
        pytest.raises(DBAPIError, match="not currently accepting connections"),
        native_server.connect(semantic_head_template.name),
    ):
        pass


def test_fresh_committed_clones_are_isolated(native_server, semantic_head_template, monkeypatch):
    from corpus_structure.semantic import migrations

    def forbidden(*args, **kwargs):
        pytest.fail("a consumer clone must not rebuild migrations")

    monkeypatch.setattr(migrations, "upgrade", forbidden)
    left, right = name(), name()
    with (
        native_server.database(
            left, semantic_head_template.name, policy=semantic_head_template.policy
        ) as a,
        native_server.database(
            right, semantic_head_template.name, policy=semantic_head_template.policy
        ) as b,
    ):
        with a.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE public.isolation_probe(value int)")
            conn.exec_driver_sql("INSERT INTO public.isolation_probe VALUES(73)")
        with a.connect() as conn:
            assert (
                conn.exec_driver_sql("SELECT value FROM public.isolation_probe").scalar_one() == 73
            )
        with b.connect() as conn:
            assert (
                conn.exec_driver_sql("SELECT to_regclass('public.isolation_probe')").scalar_one()
                is None
            )
    assert not native_server.exists(left) and not native_server.exists(right)


def test_clone_replays_default_acl_grant_options_and_all_role_settings(native_server):
    source, target = name("bare"), name()
    with native_server.database(source, native_server.template):
        # NULL datacl must be interpreted as acldefault, including PUBLIC CONNECT/TEMP.
        initial = native_server.policy(source)
        assert any(g.grantee == "PUBLIC" and g.privilege == "TEMPORARY" for g in initial.grants)
        with native_server.connect() as conn:
            q = conn.dialect.identifier_preparer.quote
            conn.exec_driver_sql(
                f"GRANT CONNECT ON DATABASE {q(source)} TO corpus_sem_reader WITH GRANT OPTION"
            )
            conn.exec_driver_sql(f"ALTER DATABASE {q(source)} CONNECTION LIMIT 17")
            conn.exec_driver_sql(
                f"ALTER DATABASE {q(source)} SET application_name TO 'all-role=setting'"
            )
            conn.exec_driver_sql(
                f"ALTER DATABASE {q(source)} SET search_path TO public, pg_catalog"
            )
            conn.exec_driver_sql(
                f"ALTER DATABASE {q(source)} SET default_transaction_read_only TO on"
            )
            conn.exec_driver_sql(
                f"ALTER ROLE {q(initial.owner)} IN DATABASE {q(source)} "
                "SET search_path TO public, pg_catalog"
            )
            conn.exec_driver_sql(
                f"ALTER ROLE {q(initial.owner)} IN DATABASE {q(source)} "
                "SET statement_timeout TO '1s'"
            )
        expected = native_server.policy(source)
        assert any(g.grantee == "corpus_sem_reader" and g.grantable for g in expected.grants)
        assert {(s.role, s.key) for s in expected.settings} == {
            ("", "application_name"),
            ("", "search_path"),
            ("", "default_transaction_read_only"),
            (initial.owner, "search_path"),
            (initial.owner, "statement_timeout"),
        }
        with native_server.database(target, source) as clone:
            # PostgreSQL cloning loses database-level policy; independently require the loss.
            assert native_server.policy(target) != expected
            native_server.replay_policy(target, expected)
            actual = native_server.policy(target)
            assert actual == expected
            assert actual.connection_limit == 17
            with clone.connect() as conn:
                assert (
                    conn.exec_driver_sql("SHOW application_name").scalar_one() == "all-role=setting"
                )
                assert conn.exec_driver_sql("SHOW statement_timeout").scalar_one() == "1s"
                assert conn.exec_driver_sql("SHOW search_path").scalar_one() == "public, pg_catalog"
                assert (
                    conn.exec_driver_sql("SHOW default_transaction_read_only").scalar_one() == "on"
                )
            # Replaying acldefault removes explicit grants, settings and nondefault connlimit.
            native_server.replay_policy(target, initial)
            assert native_server.policy(target) == initial


def test_acl_replay_refuses_nonowner_grant_graph(native_server):
    source = name("bare")
    with native_server.database(source, native_server.template):
        policy = native_server.policy(source)
        first = policy.grants[0]
        unrepresentable = replace(policy, grants=(replace(first, grantor="corpus_sem_publisher"),))
        with pytest.raises(RuntimeError, match="owner-granted"):
            native_server.replay_policy(source, unrepresentable)
        assert native_server.policy(source) == policy


def test_missing_roles_are_one_typed_preflight(native_server, db_support):
    principals = db_support.semantic_principals()
    assert set(principals) == {"publisher", "write", "read", "evaluate", "fit", "admit"}
    missing = {purpose: f"missing_semantic_{purpose}" for purpose in principals}
    with pytest.raises(PrerequisiteUnavailable) as failure:
        native_server.check_roles(missing)
    assert failure.value.category == "postgres-roles"
    assert all(role in failure.value.reason for role in missing.values())


@pytest.mark.db
@pytest.mark.parametrize("purpose", ["write", "read", "evaluate", "admit"])
def test_actual_restricted_principals_deny_temp_dml_reference_and_escalation(request, purpose):
    engines = {
        "write": "semantic_writer_engine",
        "read": "semantic_reader_engine",
        "evaluate": "semantic_evaluator_engine",
        "admit": "semantic_admitter_engine",
    }
    engine = request.getfixturevalue(engines[purpose])
    with engine.begin() as conn:
        conn.execute(text("SELECT data.require_runtime_principal(:p)"), {"p": purpose})
        assert not conn.exec_driver_sql(
            "SELECT has_database_privilege(current_user,current_database(),'TEMP')"
        ).scalar_one()
        assert not conn.exec_driver_sql(
            "SELECT EXISTS(SELECT FROM pg_namespace "
            "WHERE nspname IN ('sem','data','ops','eval','kb') "
            "AND nspowner=current_user::regrole)"
        ).scalar_one()
        denied = [
            "CREATE TEMP TABLE counterfeit(value int)",
            "INSERT INTO data.fact DEFAULT VALUES",
            "INSERT INTO sem.release DEFAULT VALUES",
            "INSERT INTO eval.reference_pass DEFAULT VALUES",
            "SET LOCAL ROLE corpus_sem_publisher",
        ]
        if purpose != "evaluate":
            denied.append("SELECT * FROM eval.reference_set")
        for sql in denied:
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.exec_driver_sql(sql)


def test_owned_lease_blocks_sweep_and_untagged_residue_survives(native_server):
    owned, historical = name(), name()
    with native_server.database(owned, native_server.template):
        assert owned not in native_server.sweep()
        assert native_server.exists(owned)
        with native_server.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE "{historical}" TEMPLATE template0')
        try:
            assert historical not in native_server.sweep()
            with pytest.raises(RuntimeError, match="unauthenticated"):
                native_server.drop(historical)
        finally:
            with native_server.connect() as conn:
                conn.exec_driver_sql(f'DROP DATABASE "{historical}"')


def test_cancelled_body_still_drops_owned_database(native_server):
    database = name()
    with (
        pytest.raises(KeyboardInterrupt),
        native_server.database(database, native_server.template),
    ):
        raise KeyboardInterrupt("owned cancellation")
    assert not native_server.exists(database)


def test_cleanup_waits_for_authenticated_backend_normal_exit(native_server):
    database = name()
    timer = None
    try:
        with native_server.database(database, native_server.template) as engine:
            connection = engine.connect()
            connection.exec_driver_sql("SELECT 1")
            # A checked-out connection survives Engine.dispose(); normal exit releases it.
            timer = threading.Timer(0.2, connection.close)
            timer.start()
        assert not native_server.exists(database)
    finally:
        if timer is not None:
            timer.join()


def test_leaked_restricted_backend_refuses_drop_then_owner_can_finish_cleanup(
    native_server, native_settings
):
    database = name()
    reader = principal_engine(native_settings, "read", database)
    leaked = None
    # Keep the lease through recovery so a concurrent sweep cannot adopt the retained residue.
    with native_server.lease(database):
        try:
            with (
                pytest.raises(BaseExceptionGroup, match="cleanup failures") as failure,
                native_server.database(database, native_server.template),
            ):
                leaked = reader.connect()
                assert leaked.exec_driver_sql("SELECT current_user").scalar_one() == (
                    reader.url.username
                )
            assert any(
                isinstance(exc, DBAPIError) and getattr(exc.orig, "sqlstate", None) == "55006"
                for exc in failure.value.exceptions
            )
            assert native_server.exists(database)
        finally:
            if leaked is not None:
                leaked.close()
            reader.dispose()
            native_server.drop(database)
        assert not native_server.exists(database)


def test_dispose_failure_still_attempts_database_cleanup(native_server, monkeypatch):
    database = name()
    with (
        pytest.raises(BaseExceptionGroup, match="cleanup failures") as failures,
        native_server.database(database, native_server.template) as engine,
    ):
        dispose = engine.dispose

        def fail_dispose():
            dispose()
            raise RuntimeError("independent dispose failure")

        monkeypatch.setattr(engine, "dispose", fail_dispose)
    assert len(failures.value.exceptions) == 1
    assert not native_server.exists(database)


def test_principal_credentials_resolve_original_endpoint_before_clone_substitution():
    from corpus_structure.settings import Settings

    settings = Settings(
        database={
            "url": "postgresql://writer:write-secret@db.example:5434/original?sslmode=require",
            "maintenance_url": "postgresql://owner:admin-secret@db.example:5434/original",
            "reader_url": "postgresql://reader:read-secret@db.example:5434/original",
        }
    )
    reader = principal_engine(settings, "read", "clone")
    evaluator = principal_engine(settings, "evaluate", "clone")
    try:
        assert (reader.url.username, reader.url.password, reader.url.database) == (
            "reader",
            "read-secret",
            "clone",
        )
        assert reader.url.query["sslmode"] == "require"
        assert evaluator.url.username == "corpus_sem_evaluator"
        assert evaluator.url.password is None
        assert evaluator.url.database == "clone"
    finally:
        reader.dispose()
        evaluator.dispose()
    contradictory = settings.model_copy(
        update={
            "database": settings.database.model_copy(
                update={"reader_url": "postgresql://reader@db.example:5434/clone"}
            )
        }
    )
    with pytest.raises(ValueError, match="contradict target database"):
        principal_engine(contradictory, "read", "clone")


def test_create_stamp_failure_drops_just_created_unstamped_database(native_server, monkeypatch):
    database = name()
    original_tag = native_server.tag

    def fail_stamp(conn, target, owned):
        if target == database:
            raise RuntimeError("stamp failed after CREATE")
        original_tag(conn, target, owned)

    monkeypatch.setattr(native_server, "tag", fail_stamp)
    with (
        pytest.raises(RuntimeError, match="stamp failed"),
        native_server.database(database, native_server.template),
    ):
        pytest.fail("stamp failure must occur before yield")
    assert not native_server.exists(database)


@pytest.mark.parametrize("cancel", [False, True])
def test_engine_construction_failure_or_cancel_drops_created_database(
    native_server, monkeypatch, cancel
):
    from sqlalchemy.engine import make_url

    import native_test_support

    database = name()
    original_create_engine = native_test_support.create_engine
    error = KeyboardInterrupt if cancel else RuntimeError

    def fail_engine(url, **kwargs):
        if make_url(url).database == database:
            raise error("engine constructor failed after CREATE")
        return original_create_engine(url, **kwargs)

    monkeypatch.setattr(native_test_support, "create_engine", fail_engine)
    with (
        pytest.raises(error, match="engine constructor failed"),
        native_server.database(database, native_server.template),
    ):
        pytest.fail("engine construction must fail before yield")
    assert not native_server.exists(database)


def test_create_collision_never_disposes_the_other_database(native_server, monkeypatch):
    database = name()
    create = native_server.create

    def concurrent_create(target, source, **kwargs):
        # Simulate a noncooperating creator after our absent-name check.
        with native_server.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE "{target}" TEMPLATE template0')
        create(target, source, **kwargs)

    monkeypatch.setattr(native_server, "create", concurrent_create)
    try:
        with (
            pytest.raises(DBAPIError) as failure,
            native_server.database(database, native_server.template),
        ):
            pytest.fail("CREATE collision must occur before yield")
        assert getattr(failure.value.orig, "sqlstate", None) == "42P04"
        assert native_server.exists(database)
        with native_server.connect() as conn:
            assert (
                conn.execute(
                    text(
                        "SELECT shobj_description(oid,'pg_database') "
                        "FROM pg_database WHERE datname=:n"
                    ),
                    {"n": database},
                ).scalar_one()
                is None
            )
    finally:
        with native_server.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database}"')


def test_unknown_create_cancellation_never_disposes_an_intervening_database(
    native_server, monkeypatch
):
    database = name()

    def unknown_create(target, _source, **_kwargs):
        with native_server.connect() as actor:
            actor.exec_driver_sql(f'CREATE DATABASE "{target}" TEMPLATE template0')
        raise KeyboardInterrupt("CREATE outcome unavailable")

    monkeypatch.setattr(native_server, "create", unknown_create)
    try:
        with (
            pytest.raises(KeyboardInterrupt, match="outcome unavailable"),
            native_server.database(database, native_server.template),
        ):
            pytest.fail("unacknowledged CREATE must never expose an engine")
        assert native_server.exists(database)
    finally:
        with native_server.connect() as actor:
            actor.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database}"')


def test_clone_replays_and_removes_actual_restricted_reader_default(native_server, native_settings):
    source, target = name("bare"), name()
    with native_server.database(source, native_server.template):
        initial = native_server.policy(source)
        reader = principal_engine(native_settings, "read", "postgres")
        try:
            with reader.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                role, authenticated_role = conn.exec_driver_sql(
                    "SELECT current_user, session_user"
                ).one()
                assert role == authenticated_role
                assert not conn.exec_driver_sql(
                    "SELECT rolsuper FROM pg_roles WHERE rolname=current_user"
                ).scalar_one()
                q = conn.dialect.identifier_preparer.quote
                conn.exec_driver_sql(
                    f"ALTER ROLE {q(role)} IN DATABASE {q(source)} SET statement_timeout TO '2s'"
                )
                conn.exec_driver_sql(
                    f"ALTER ROLE {q(role)} IN DATABASE {q(source)} "
                    "SET search_path TO pg_catalog, public"
                )
                conn.exec_driver_sql(
                    f"ALTER ROLE {q(role)} IN DATABASE {q(source)} "
                    "SET default_transaction_read_only TO on"
                )
            expected = native_server.policy(source)
            assert [(s.role, s.key, s.value) for s in expected.settings] == [
                (role, "default_transaction_read_only", "on"),
                (role, "search_path", "pg_catalog, public"),
                (role, "statement_timeout", "2s"),
            ]
            with native_server.connect() as conn:
                assert conn.exec_driver_sql("SELECT current_user").scalar_one() != role
            with native_server.database(target, source, policy=expected):
                assert native_server.policy(target) == expected
                target_reader = principal_engine(native_settings, "read", target)
                try:
                    with target_reader.connect() as conn:
                        assert conn.exec_driver_sql("SHOW statement_timeout").scalar_one() == "2s"
                        assert (
                            conn.exec_driver_sql("SHOW search_path").scalar_one()
                            == "pg_catalog, public"
                        )
                        assert (
                            conn.exec_driver_sql("SHOW default_transaction_read_only").scalar_one()
                            == "on"
                        )
                finally:
                    target_reader.dispose()
                native_server.replay_policy(target, initial)
                assert native_server.policy(target) == initial
        finally:
            reader.dispose()


def test_receipt_observes_clone_deployment_and_authenticated_reader(
    semantic_db_engine, semantic_reader_engine, native_settings, monkeypatch
):
    from sqlalchemy.engine import make_url

    import qualification_plugin
    from corpus_structure.semantic.migrations import head_revision

    observed = []
    monkeypatch.setattr(
        qualification_plugin,
        "record_native_context",
        lambda context, **kwargs: observed.append(context),
    )
    with semantic_reader_engine.connect() as conn:
        oid = conn.exec_driver_sql(
            "SELECT oid FROM pg_database WHERE datname=current_database()"
        ).scalar_one()
    actual = next(event for event in observed if event["requested"]["purpose"] == "read")
    assert actual["acquired"]["database"] == semantic_db_engine.url.database
    assert actual["acquired"]["database"] != make_url(native_settings.database.url).database
    assert actual["acquired"]["database_oid"] == oid
    assert actual["acquired"]["current_user"] == "corpus_sem_reader"
    assert actual["acquired"]["session_user"] == "corpus_sem_reader"
    assert actual["acquired"]["revision"] == head_revision()
    assert actual["acquired"]["policy_ref"]
    assert actual["provenance"] == {"complete": True, "missing": []}
    assert set(actual["requested"]) == {"database", "host", "port", "principal", "purpose"}
