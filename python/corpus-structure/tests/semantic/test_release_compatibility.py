"""Versioned reader, runtime and cache controls with independent historical artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import AfterValidator, TypeAdapter, ValidationError

from corpus_structure.semantic import determinants
from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.types import PreparationProfile

from .test_archive_reader import archived


@pytest.mark.parametrize("compiler", ["14"])
@pytest.mark.parametrize("changed", ["pydantic", "pydantic-core", "python", "jsonschema", "cattrs"])
def test_runtime_compatibility_is_explicit_not_schema_equivalence(monkeypatch, compiler, changed):
    # These validators export exactly the same schema, but disagree on acceptance.
    def positive(value: int) -> int:
        if value <= 0:
            raise ValueError("positive required")
        return value

    old = TypeAdapter(int)
    changed_acceptance = TypeAdapter(Annotated[int, AfterValidator(positive)])
    assert old.json_schema() == changed_acceptance.json_schema()
    assert old.validate_python(0) == 0
    with pytest.raises(ValidationError):
        changed_acceptance.validate_python(0)
    recorded = {
        name: determinants.determinant_version(name)
        for name in (*determinants.BOUNDARY_LIBRARIES, "linkml-runtime")
    }
    assert determinants.boundary_compatible(recorded, compiler)
    original = determinants.determinant_version
    monkeypatch.setattr(
        determinants, "determinant_version",
        lambda name: "changed" if name == changed else original(name),
    )
    assert not determinants.boundary_compatible(recorded, compiler)


@pytest.mark.parametrize("compiler", ["10", "11", "12", "13", "future"])
def test_retired_or_unknown_boundary_compilers_refuse_even_with_current_versions(compiler):
    recorded = {name: determinants.determinant_version(name) for name in determinants.BOUNDARY_LIBRARIES}
    assert not determinants.boundary_compatible(recorded, compiler)


def test_warm_cache_does_not_admit_changed_runtime_or_failed_source_verification(
    semantic_db_engine, monkeypatch
):
    from sqlalchemy import insert

    from corpus_structure.semantic import releases
    from corpus_structure.semantic.metadata import table

    from .test_releases import stage

    with semantic_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
        conn.execute(insert(table("data.project")).values(project_id="cached"))
        opened = releases.open_release(conn, prepared.release_id)
        assert releases.open_release(conn, prepared.release_id) is opened
        actual = determinants.determinant_version
        with monkeypatch.context() as changed:
            changed.setattr(
                determinants,
                "determinant_version",
                lambda name: "changed-core" if name == "pydantic-core" else actual(name),
            )
            with pytest.raises(releases.ReleaseConflict, match="boundary library versions"):
                releases.open_release(conn, prepared.release_id)
        assert releases.open_release(conn, prepared.release_id) is opened

        def unavailable(*args, **kwargs):
            raise ValueError("independent exact-source verification failed")

        from corpus_structure.semantic import prepare as compiler

        monkeypatch.setattr(compiler, "prepare_release", unavailable)
        with pytest.raises(releases.ReleaseConflict):
            releases.verify_release(conn, prepared.release_id)
        with pytest.raises(releases.ReleaseConflict):
            releases.activate_release(
                conn, "cached", prepared.release_id, expected_parent=None, expected_generation=0
            )
        # A read-cache hit is not an admission receipt.
        assert releases.open_release(conn, prepared.release_id) is opened


def test_cache_is_database_scoped_and_rechecks_current_archive_digest(
    semantic_db_engine, semantic_database_at
):
    from sqlalchemy import update

    from corpus_structure.semantic import releases
    from corpus_structure.semantic.metadata import table

    from .archive_faults import administrative_archive_edit
    from .test_releases import stage

    with (
        semantic_database_at("head") as other,
        semantic_db_engine.begin() as left,
        other.begin() as right,
    ):
        _, _, _, first = stage(left)
        _, _, _, second = stage(right)
        assert first.release_id == second.release_id
        one = releases.open_release(left, first.release_id)
        two = releases.open_release(right, second.release_id)
        assert one is not two
        assert releases.open_release(left, first.release_id) is one
        release = table("sem.release")
        with administrative_archive_edit(left, release):
            left.execute(
                update(release)
                .where(release.c.release_id == first.release_id)
                .values(prepared_bytes=b"{}")
            )
        with pytest.raises(releases.ReleaseConflict, match="archive digest"):
            releases.open_release(left, first.release_id)
        assert releases.open_release(right, second.release_id) is two


def test_shared_snapshot_restores_connection_state_after_failure(semantic_reader_engine):
    from corpus_structure.semantic.query import read_snapshot

    with (
        pytest.raises(RuntimeError, match="cancelled consumer"),
        read_snapshot(semantic_reader_engine) as conn,
    ):
        assert conn.get_isolation_level() == "REPEATABLE READ"
        assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "on"
        raise RuntimeError("cancelled consumer")
    with semantic_reader_engine.connect() as conn:
        assert conn.get_isolation_level() == "READ COMMITTED"
        assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "off"


def test_finalized_warm_open_selects_only_header_without_hashing(semantic_db_engine, monkeypatch):
    from sqlalchemy import event

    from corpus_structure.semantic import releases

    from .test_releases import stage

    with semantic_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
        opened = releases.open_release(conn, prepared.release_id)
        statements = []

        def observe(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        def unexpected_hash(*args):
            raise AssertionError("a finalized warm hit must not hash payloads")

        event.listen(conn, "before_cursor_execute", observe)
        try:
            with monkeypatch.context() as guarded:
                guarded.setattr(releases, "_digest", unexpected_hash)
                assert releases.open_release(conn, prepared.release_id) is opened
        finally:
            event.remove(conn, "before_cursor_execute", observe)
        assert len(statements) == 1
        assert "release_finalization" in statements[0]
        assert "prepared_bytes" not in statements[0]
        assert "manifest_bytes" not in statements[0]


def test_cold_open_changed_header_refuses_without_publishing_cache(semantic_db_engine, monkeypatch):
    from corpus_structure.semantic import archive_reader, releases

    from .test_releases import stage

    with semantic_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
        with archive_reader._CACHE_LOCK:
            archive_reader._OPEN_CACHE.pop(conn.engine, None)
        original = archive_reader._archive_header
        calls = 0

        def changed_header(connection, release_id):
            nonlocal calls
            calls += 1
            row = original(connection, release_id)
            if calls == 2:
                return (*row[:-1], "changed physical tuple")
            return row

        with monkeypatch.context() as changed:
            changed.setattr(archive_reader, "_archive_header", changed_header)
            with pytest.raises(releases.ReleaseConflict, match="header changed"):
                releases.open_release(conn, prepared.release_id)
        with archive_reader._CACHE_LOCK:
            assert not archive_reader._OPEN_CACHE.get(conn.engine)
        assert releases.open_release(conn, prepared.release_id).release_id == prepared.release_id


def test_unfinalized_archive_keeps_full_checks_without_cache(semantic_db_engine, monkeypatch):
    from sqlalchemy import delete

    from corpus_structure.semantic import archive_reader, releases
    from corpus_structure.semantic.metadata import table

    from .archive_faults import administrative_archive_edit
    from .test_releases import stage

    with semantic_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
        finalized = table("sem.release_finalization")
        with administrative_archive_edit(conn, finalized):
            conn.execute(delete(finalized).where(finalized.c.release_id == prepared.release_id))
        with archive_reader._CACHE_LOCK:
            archive_reader._OPEN_CACHE.pop(conn.engine, None)
        compared = []
        original = releases._compare_rows

        def compare(connection, name, release_id, rows):
            compared.append(name)
            return original(connection, name, release_id, rows)

        monkeypatch.setattr(releases, "_compare_rows", compare)
        one = releases.open_release(conn, prepared.release_id)
        two = releases.open_release(conn, prepared.release_id)
        assert one is not two
        assert compared
        with archive_reader._CACHE_LOCK:
            assert not archive_reader._OPEN_CACHE.get(conn.engine)


def test_overlapping_cold_archive_opens_publish_one_owner(semantic_db_engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from corpus_structure.semantic import archive_reader, releases

    from .test_releases import stage

    with semantic_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
    with archive_reader._CACHE_LOCK:
        archive_reader._OPEN_CACHE.pop(semantic_db_engine, None)
    overlap = Barrier(2)
    original = archive_reader.reconstruct_release

    def reconstruct(*args, **kwargs):
        overlap.wait(timeout=15)
        return original(*args, **kwargs)

    monkeypatch.setattr(archive_reader, "reconstruct_release", reconstruct)

    def open_one():
        with semantic_db_engine.connect() as conn:
            return releases.open_release(conn, prepared.release_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(open_one) for _ in range(2)]
        one, two = [future.result(timeout=30) for future in futures]
    assert one is two


def test_archive_cache_retains_only_eight_recent_products(semantic_db_engine):
    from corpus_structure.semantic import archive_reader, releases

    from .test_releases import source_bundle, stage

    with semantic_db_engine.begin() as conn:
        prepared = [stage(conn, source_bundle(f"\n# release {i}\n".encode()))[3] for i in range(9)]
        opened = [releases.open_release(conn, item.release_id) for item in prepared[:8]]
        # Touch the oldest product, so eviction must select the second product.
        assert releases.open_release(conn, prepared[0].release_id) is opened[0]
        releases.open_release(conn, prepared[8].release_id)
        with archive_reader._CACHE_LOCK:
            assert len(archive_reader._OPEN_CACHE[conn.engine]) == 8
        assert releases.open_release(conn, prepared[0].release_id) is opened[0]
        assert releases.open_release(conn, prepared[1].release_id) is not opened[1]
