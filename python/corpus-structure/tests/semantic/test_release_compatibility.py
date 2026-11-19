"""Current reader, exact runtime and finalized archive cache controls."""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import AfterValidator, TypeAdapter, ValidationError

from corpus_structure.semantic import determinants
from corpus_structure.semantic.types import SEMANTIC_COMPILER_VERSION


@pytest.mark.parametrize("compiler", [SEMANTIC_COMPILER_VERSION])
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
        determinants,
        "determinant_version",
        lambda name: "changed" if name == changed else original(name),
    )
    assert not determinants.boundary_compatible(recorded, compiler)


@pytest.mark.parametrize(
    "compiler", ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "future"]
)
def test_retired_or_unknown_boundary_compilers_refuse_even_with_current_versions(compiler):
    recorded = {
        name: determinants.determinant_version(name) for name in determinants.BOUNDARY_LIBRARIES
    }
    assert not determinants.boundary_compatible(recorded, compiler)


def test_warm_cache_does_not_admit_changed_runtime_or_failed_source_verification(
    commit_db_engine, monkeypatch
):
    from sqlalchemy import insert

    from corpus_structure.semantic import archive_reader, releases
    from corpus_structure.semantic import prepare as compiler
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.release_identity import material_dependencies
    from semantic.releases_support import stage

    with commit_db_engine.begin() as conn:
        bundle, dependencies, profile, prepared = stage(conn)
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

        def unavailable_compiler(*args, **kwargs):
            pytest.fail("archived verification must not run the compiler")

        monkeypatch.setattr(compiler, "prepare_release", unavailable_compiler)
        assert releases.verify_release(conn, prepared.release_id).release_id == prepared.release_id

        def unreadable_archive(*args, **kwargs):
            raise releases.ReleaseConflict("independent archive verification failed")

        with monkeypatch.context() as changed:
            changed.setattr(archive_reader, "_read_archived_release_inputs", unreadable_archive)
            with pytest.raises(releases.ReleaseConflict, match="independent archive verification"):
                releases.verify_release(conn, prepared.release_id)
            with pytest.raises(releases.ReleaseConflict, match="independent archive verification"):
                releases.activate_release(
                    conn, "cached", prepared.release_id, expected_parent=None, expected_generation=0
                )
        # A read-cache hit is not an admission receipt. Original inputs can also
        # be opened while the compiler is unavailable, without re-derivation.
        assert releases.open_release(conn, prepared.release_id) is opened
        original, captured_dependencies, captured_profile, same = releases.open_release_inputs(
            conn, prepared.release_id
        )
        assert original == bundle
        assert [(item.name, item.content) for item in captured_dependencies.artifacts] == [
            (item.name, item.content) for item in material_dependencies(dependencies).artifacts
        ]
        assert captured_dependencies.vocabularies == dependencies.vocabularies
        assert captured_dependencies.ontology_sources == dependencies.ontology_sources
        assert captured_profile == profile
        assert same is opened


def test_cache_is_database_scoped_and_rechecks_current_archive_digest(
    commit_db_engine, commit_clone
):
    from sqlalchemy import update

    from corpus_structure.semantic import releases
    from corpus_structure.semantic.metadata import table
    from semantic.archive_faults import administrative_archive_edit
    from semantic.releases_support import stage

    with (
        commit_clone() as other,
        commit_db_engine.begin() as left,
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


def test_next_reader_snapshot_observes_an_activated_generation(
    commit_db_engine, commit_admitter_engine, commit_reader_engine
):
    from sqlalchemy import insert

    from corpus_structure.semantic import releases
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.read_snapshot import read_snapshot
    from semantic.releases_support import source_bundle, stage

    project = "archive-cache-generation"
    with commit_db_engine.begin() as conn:
        first_id = stage(conn)[3].release_id
        next_id = stage(conn, source_bundle(b"\n# New generation\n"))[3].release_id
        conn.execute(insert(table("data.project")).values(project_id=project))
    assert next_id != first_id

    def activate(release_id: str, *, parent: str | None, generation: int):
        with commit_admitter_engine.begin() as conn:
            return releases.activate_release(
                conn, project, release_id, expected_parent=parent, expected_generation=generation
            )

    previous = activate(first_id, parent=None, generation=0)
    with read_snapshot(commit_reader_engine) as conn:
        selected = releases.activation_token(conn, project)
        assert (selected.release_id, selected.generation) == (first_id, 1)
        first = releases.open_release(conn, first_id)

    activate(next_id, parent=previous.release_id, generation=previous.generation)
    with read_snapshot(commit_reader_engine) as conn:
        selected = releases.activation_token(conn, project)
        assert (selected.release_id, selected.generation) == (next_id, 2)
        assert releases.open_release(conn, next_id).release_id == selected.release_id
        assert releases.open_release(conn, first_id) is first


def test_shared_snapshot_restores_connection_state_after_failure(commit_reader_engine):
    from corpus_structure.semantic.read_snapshot import read_snapshot

    with (
        pytest.raises(RuntimeError, match="cancelled consumer"),
        read_snapshot(commit_reader_engine) as conn,
    ):
        assert conn.get_isolation_level() == "REPEATABLE READ"
        assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "on"
        raise RuntimeError("cancelled consumer")
    with commit_reader_engine.connect() as conn:
        assert conn.get_isolation_level() == "READ COMMITTED"
        assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "off"


def test_finalized_warm_open_selects_only_header_without_hashing(commit_db_engine, monkeypatch):
    from sqlalchemy import event

    from corpus_structure.semantic import releases
    from semantic.releases_support import stage

    with commit_db_engine.begin() as conn:
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


def test_cold_open_changed_header_refuses_without_publishing_cache(commit_db_engine, monkeypatch):
    from corpus_structure.semantic import archive_reader, releases
    from semantic.releases_support import stage

    with commit_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
        archive_reader._opened_archive.cache_clear()
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
        assert archive_reader._opened_archive.observe().entries == 0
        assert releases.open_release(conn, prepared.release_id).release_id == prepared.release_id


def test_unfinalized_archive_refuses_without_cache(commit_db_engine):
    from sqlalchemy import delete

    from corpus_structure.semantic import archive_reader, releases
    from corpus_structure.semantic.metadata import table
    from semantic.archive_faults import administrative_archive_edit
    from semantic.releases_support import stage

    with commit_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
        finalized = table("sem.release_finalization")
        with administrative_archive_edit(conn, finalized):
            conn.execute(delete(finalized).where(finalized.c.release_id == prepared.release_id))
        archive_reader._opened_archive.cache_clear()
        with pytest.raises(releases.ReleaseConflict, match="protected finalization"):
            releases.open_release(conn, prepared.release_id)
        assert archive_reader._opened_archive.observe().entries == 0


def test_overlapping_cold_archive_opens_publish_one_owner(commit_db_engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from corpus_structure.semantic import archive_reader, releases
    from semantic.releases_support import stage

    with commit_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
    archive_reader._opened_archive.cache_clear()
    started = Event()
    release_loader = Event()
    calls = 0
    original = archive_reader.reconstruct_release

    def reconstruct(*args, **kwargs):
        nonlocal calls
        calls += 1
        started.set()
        assert release_loader.wait(timeout=15)
        return original(*args, **kwargs)

    monkeypatch.setattr(archive_reader, "reconstruct_release", reconstruct)

    def open_one():
        with commit_db_engine.connect() as conn:
            return releases.open_release(conn, prepared.release_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(open_one)
        assert started.wait(timeout=15)
        second = executor.submit(open_one)
        release_loader.set()
        one, two = first.result(timeout=30), second.result(timeout=30)
    assert one is two
    assert calls == 1


def test_archive_cache_reuses_acquired_database_across_engines(commit_db_engine):
    from sqlalchemy import create_engine

    from corpus_structure.semantic import archive_reader, releases
    from semantic.releases_support import stage

    archive_reader._opened_archive.cache_clear()
    with commit_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
    with commit_db_engine.connect() as conn:
        opened = releases.open_release(conn, prepared.release_id)
    second = create_engine(commit_db_engine.url)
    try:
        with second.connect() as conn:
            assert releases.open_release(conn, prepared.release_id) is opened
    finally:
        second.dispose()
    assert archive_reader._opened_archive.observe().entries == 1
