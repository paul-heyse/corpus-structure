"""Independent production preparation refusal and retained archive boundaries."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event

from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.arrow_publication import AppendPublication
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.publication import EntityRow, PublicationBatch, _publish
from corpus_structure.semantic.query import ReadSession, SnapshotBinding, WrongRelease
from corpus_structure.semantic.types import PreparationError, PreparationProfile

from .test_archive_reader import archived
from .test_publication import fixture_model


@pytest.fixture(scope="module")
def current():
    return fixture_model(composed=True)[1]


def batch(prepared):
    return PublicationBatch(
        prepared.release_id, "realization:owned", "batch:one", entity=(EntityRow("entity:one"),)
    )


def test_append_consumes_actual_prepared_rows(current):
    original = batch(current).bind_preparation(current)
    assert AppendPublication.from_rows(original).content == original.content
    assert original._analysis_input.family == "publication"
    assert dict(original._analysis_input.dependencies)["content"] == canonical_bytes(
        sha256(original.content).hexdigest()
    )
    changed = replace(original, entity=(EntityRow("entity:changed"),))
    with pytest.raises(ValueError, match="preparation differs"):
        AppendPublication.from_rows(changed)
    # A deliberate rebuild after changing the rows restores correspondence.
    rebound = changed.bind_preparation(current)
    assert AppendPublication.from_rows(rebound).content == changed.content


def test_stale_rows_refuse_before_retry_acquires_database(current):
    stale = replace(batch(current).bind_preparation(current), entity=(EntityRow("entity:changed"),))
    engine = create_engine("sqlite://")
    acquisitions = []

    @event.listens_for(engine, "connect")
    def acquired(connection, record):
        acquisitions.append(connection)

    def publish(connection, rows):
        raise AssertionError("stale preparation reached publication")

    try:
        with pytest.raises(ValueError, match="preparation differs"):
            _publish(engine, stale, publish, attempts=2)
        assert acquisitions == []
    finally:
        engine.dispose()


def test_wrong_release_cannot_bind_rows_or_snapshot(current):
    other = replace(batch(current), release_id="release:other")
    with pytest.raises(PreparationError):
        other.bind_preparation(current)
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection, pytest.raises(WrongRelease):
            ReadSession(
                connection,
                SnapshotBinding("release:other", "realization:one", 1, "read:1"),
                current,
            )
    finally:
        engine.dispose()


def test_current_read_owner_retains_exact_snapshot_contract(current):
    binding = SnapshotBinding(current.release_id, "realization:one", 7, "read:one")
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            session = ReadSession(connection, binding, current)
            owned = session._analysis_input
            assert owned.family == "read"
            assert owned.release_id == current.release_id
            assert owned.model_id == current.execution_model_id
            assert dict(owned.dependencies) == {
                "release": canonical_bytes(current.release_id),
                "archive": canonical_bytes(current.release_id),
                "boundary": canonical_bytes(asdict(binding)),
            }
    finally:
        engine.dispose()


def test_genuine_historical_read_refuses_without_rewriting_retained_bytes():
    fixture = Path(__file__).parents[1] / "fixtures/semantic/reader-v10.json"
    original = fixture.read_bytes()
    data, bundle, artifacts = archived(fixture)
    manifest = bytes.fromhex(data["manifest"])
    assert json.loads(manifest)["profile"]["compiler_version"] == "10"
    with pytest.raises(ValueError, match=r"^unsupported archived compiler 10$"):
        reconstruct_release(
            data["products"],
            manifest,
            bundle,
            PreparationProfile(**data["profile"]),
            artifacts,
        )
    assert fixture.read_bytes() == original
