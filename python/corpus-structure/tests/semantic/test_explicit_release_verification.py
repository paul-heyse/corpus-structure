"""Explicit proof reads current bytes and authenticates its native implementation."""

from collections import namedtuple
from types import SimpleNamespace
from typing import Any, cast

import pytest


def test_explicit_archive_read_bypasses_warm_entry(monkeypatch):
    from corpus_structure.semantic import archive_reader, determinants, storage_target

    header = namedtuple("Header", "finalized_digest content_digest")("digest", "digest")
    connection = SimpleNamespace()
    monkeypatch.setattr(archive_reader, "_archive_header", lambda *args: header)
    monkeypatch.setattr(determinants, "determinant_version", lambda name: "version")
    monkeypatch.setattr(storage_target, "acquired_database_identity", lambda conn: "database")
    retained = (
        SimpleNamespace(sources=()),
        SimpleNamespace(artifacts=()),
        None,
        SimpleNamespace(manifest=b"manifest", artifacts=()),
    )
    calls = []

    def current(conn, release_id, observed):
        calls.append((conn, release_id, observed))
        if len(calls) > 1:
            raise ValueError("current archive bytes are corrupt")
        return retained

    archive_reader._opened_archive.cache_clear()
    monkeypatch.setattr(archive_reader, "_read_archived_release_inputs", current)
    assert archive_reader.open_archived_release_inputs(connection, "release") is retained
    assert archive_reader.open_archived_release_inputs(connection, "release") is retained
    with pytest.raises(ValueError, match="current archive bytes"):
        archive_reader.open_archived_release_inputs(connection, "release", use_cache=False)
    assert calls == [(connection, "release", header)] * 2


def test_verify_release_requests_uncached_parts_and_compares_projections(monkeypatch):
    from corpus_structure.semantic import archive_reader, releases

    prepared = object()
    observed = []

    def parts(conn, release_id, *, use_cache=True):
        observed.append(("parts", use_cache))
        return "bundle", "dependencies", "profile", prepared

    monkeypatch.setattr(archive_reader, "open_archived_release_inputs", parts)
    monkeypatch.setattr(releases, "_projection_rows", lambda value: {"projection": ["expected"]})
    monkeypatch.setattr(
        releases,
        "_compare_rows",
        lambda conn, name, release, expected: observed.append((name, expected)),
    )
    assert releases.verify_release(cast(Any, object()), "release") is prepared
    assert observed == [("parts", False), ("projection", ["expected"])]


def test_native_proof_authenticates_frozen_functions_before_execution(monkeypatch):
    from corpus_structure.semantic import execution_admission

    observed = []

    def expectation(connection):
        observed.append("authenticated")
        return SimpleNamespace(named_catalog_proof=True, physical_id="physical")

    class Connection:
        def execute(self, statement):
            observed.append(str(statement))

    monkeypatch.setattr(execution_admission, "_deployment_expectation", expectation)
    assert (
        execution_admission.verify_native_execution_release(cast(Any, Connection()), "release")
        == "physical"
    )
    assert observed[0] == "authenticated"
    assert "data.prove_execution_release" in observed[1]


def test_native_proof_refuses_unauthenticated_implementation(monkeypatch):
    from corpus_structure.semantic import execution_admission

    def expectation(connection):
        raise execution_admission.ExecutionAdmissionError("native contract differs")

    monkeypatch.setattr(execution_admission, "_deployment_expectation", expectation)
    with pytest.raises(execution_admission.ExecutionAdmissionError, match="contract differs"):
        execution_admission.verify_native_execution_release(cast(Any, object()), "release")


def test_native_proof_cli_requires_an_explicit_release(cli):
    result = cli("release", "check", "--native-proof", "--json")
    assert result.exit_code == 1
    assert "--native-proof requires an explicit --release" in result.stdout
