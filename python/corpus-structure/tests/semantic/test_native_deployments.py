"""Actual PostgreSQL custody controls and independent frozen-head reuse verification."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from uuid import uuid4

import pytest
from sqlalchemy import text

from corpus_structure.semantic import execution_admission, migrations
from native_test_support import database_name


@pytest.fixture
def private_keys(native_server):
    keys = []

    def new_key():
        key = uuid4().hex
        keys.append(key)
        return key

    yield new_key
    for key in keys:
        for name in native_server.names("cs_sem_head_" + key[:16]):
            native_server.drop(name)


@pytest.fixture
def tiny_construction(monkeypatch):
    import native_deployment_build

    calls = []

    def construct(connection):
        calls.append(connection.scalar(text("SELECT current_database()")))
        connection.exec_driver_sql("CREATE TABLE public.deployment_probe(value int)")
        connection.exec_driver_sql("INSERT INTO public.deployment_probe VALUES(71)")

    monkeypatch.setattr(native_deployment_build, "construct_deployment", construct)
    return calls


@pytest.mark.parametrize("kind", ["session", "test", "seed"])
def test_reused_head_checks_first_requested_clone_once_before_effects(
    native_server, private_keys, tiny_construction, monkeypatch, kind
):
    key, run = private_keys(), uuid4().hex
    with native_server.deployment(key=key, run_id=run) as built:
        assert built.built and built.verification == "fresh"
    checked = []

    def verify(connection, *, revision):
        checked.append(connection.scalar(text("SELECT current_database()")))
        assert connection.scalar(text("SELECT value FROM public.deployment_probe")) == 71

    monkeypatch.setattr(execution_admission, "verify_deployment_catalog", verify)
    monkeypatch.setattr(
        migrations, "current_revision", lambda connection: migrations.head_revision()
    )
    original_sessions = set(native_server.names("ci_test_"))
    requested = database_name(kind, pid=999999997).name
    with native_server.deployment(key=key, run_id=run) as reused:
        assert not reused.built and reused.verification == "pending"
        with reused.clone(requested) as engine:
            assert checked == [requested]
            assert reused.verification == "verified"
            with engine.begin() as connection:
                connection.exec_driver_sql("UPDATE public.deployment_probe SET value=93")
        with reused.clone(database_name("test").name) as engine:
            assert checked == [requested]
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT value FROM public.deployment_probe")) == 71
    assert len(tiny_construction) == 1
    assert set(native_server.names("ci_test_")) == original_sessions


def test_qualification_joiners_keep_fresh_in_run_exemption(
    native_server, private_keys, tiny_construction, monkeypatch
):
    key, run = private_keys(), uuid4().hex

    def forbidden(*args, **kwargs):
        pytest.fail("a freshly built run-private head must not be reverified")

    monkeypatch.setattr(execution_admission, "verify_deployment_catalog", forbidden)
    for _ in range(2):
        with native_server.deployment(key=key, run_id=run, run_private=True) as head:
            assert head.verification == "fresh"
            with head.clone(database_name("test").name) as engine, engine.connect() as connection:
                assert connection.scalar(text("SELECT value FROM public.deployment_probe")) == 71
    assert len(tiny_construction) == 1


def test_build_failure_leaves_no_head_or_build_residue(native_server, private_keys, monkeypatch):
    import native_deployment_build

    key = private_keys()
    before = set(native_server.names("cs_sem_build_"))

    def broken(connection):
        connection.exec_driver_sql("CREATE TABLE public.incomplete(value int)")
        raise RuntimeError("injected construction failure")

    monkeypatch.setattr(native_deployment_build, "construct_deployment", broken)
    with (
        pytest.raises(RuntimeError, match="injected construction"),
        native_server.deployment(key=key),
    ):
        pytest.fail("a failed build cannot be acquired")
    assert not native_server.exists(database_name("reusable_head", key=key).name)
    assert set(native_server.names("cs_sem_build_")) == before


def test_concurrent_acquisition_builds_once_and_build_lease_blocks_sweep(
    native_server, private_keys, tiny_construction, monkeypatch
):
    import native_deployment_build

    key = private_keys()
    entered, release = threading.Event(), threading.Event()
    construct = native_deployment_build.construct_deployment

    def blocked(connection):
        entered.set()
        assert release.wait(30), "control did not release construction"
        construct(connection)

    monkeypatch.setattr(native_deployment_build, "construct_deployment", blocked)

    def acquire():
        with native_server.deployment(key=key) as head:
            return head.name, head.built

    before = set(native_server.names("cs_sem_build_"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(acquire)
        try:
            assert entered.wait(30), "builder did not reach construction"
            second = pool.submit(acquire)
            builds = set(native_server.names("cs_sem_build_")) - before
            assert len(builds) == 1
            swept = native_server.sweep()
            assert builds <= set(swept.skipped)
            assert all(native_server.exists(name) for name in builds)
        finally:
            release.set()
        results = [first.result(timeout=30), second.result(timeout=30)]
    assert len(tiny_construction) == 1
    assert len({name for name, _ in results}) == 1
    assert sorted(built for _, built in results) == [False, True]
    assert set(native_server.names("cs_sem_build_")) == before


def test_ambiguous_publication_cleans_acknowledged_oid_and_preserves_replacement(
    native_server, private_keys, tiny_construction, monkeypatch
):
    key = private_keys()
    final = database_name("reusable_head", key=key).name
    moved = database_name("stale").name
    record = native_server._deployment_record

    def substituted(name):
        row = record(name)
        if name == final and row is not None:
            with native_server.connect() as connection:
                connection.exec_driver_sql(f'ALTER DATABASE "{final}" RENAME TO "{moved}"')
                connection.exec_driver_sql(f'CREATE DATABASE "{final}" TEMPLATE template0')
            return record(name)
        return row

    monkeypatch.setattr(native_server, "_deployment_record", substituted)
    try:
        with (
            pytest.raises(RuntimeError, match="acknowledged identity"),
            native_server.deployment(key=key),
        ):
            pytest.fail("substituted publication must refuse")
        assert native_server.exists(final)
        assert not native_server.exists(moved)
        assert record(final)[2] is None
    finally:
        with native_server.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{final}"')
        native_server.drop(moved)


def test_retention_keeps_three_and_preserves_leased_older_head(
    native_server, private_keys, tiny_construction
):
    with ExitStack() as usage:
        heads = [
            usage.enter_context(native_server.deployment(key=private_keys())) for _ in range(4)
        ]
        assert all(native_server.exists(head.name) for head in heads)
        heads[0].close()
        native_server._retain_deployments()
        assert not native_server.exists(heads[0].name)
        assert all(native_server.exists(head.name) for head in heads[1:])


def test_real_stale_head_is_replaced_before_requested_clone_is_exposed(
    native_server, private_keys, monkeypatch
):
    import native_deployment_build
    import qualification_plugin

    key, run = private_keys(), uuid4().hex
    construct = native_deployment_build.construct_deployment
    calls = []
    observed = []
    recorder = qualification_plugin.record_native_context

    def tamper_first(connection):
        construct(connection)
        calls.append(1)
        if len(calls) == 1:
            connection.exec_driver_sql(
                "CREATE OR REPLACE FUNCTION data.execution_contract_descriptor() RETURNS jsonb "
                "LANGUAGE sql IMMUTABLE AS $$ SELECT '{}'::jsonb $$"
            )

    def capture(context, **kwargs):
        observed.append(context)
        recorder(context, **kwargs)

    monkeypatch.setattr(native_deployment_build, "construct_deployment", tamper_first)
    with native_server.deployment(key=key, run_id=run) as initial:
        stale = initial.name
    monkeypatch.setattr(qualification_plugin, "record_native_context", capture)
    retired = None
    try:
        with native_server.deployment(key=key, run_id=run) as reused:
            requested = database_name("seed").name
            with reused.clone(requested) as engine, engine.connect() as connection:
                assert migrations.current_revision(connection) == migrations.head_revision()
                assert engine.url.database == requested
                assert reused.name == database_name("run_private_head", key=key, run=run).name
                assert reused.gap["stale_head"] == stale
                retired = reused.gap["retirement"]
                assert native_server.exists(retired)
            assert reused.name in native_server.sweep().skipped
        records = [
            context["native_test_deployment"]
            for context in observed
            if "native_test_deployment" in context
        ]
        assert len(records) == 1
        assert records[0]["deployment_key_gap"]["stale_head"] == stale
        assert records[0]["verification"] == "fresh"
        assert len(calls) == 2
    finally:
        if retired is not None:
            native_server.drop(retired)
