"""Native source initialization, immutable metadata, binary custody and actual purpose refusal."""

from collections.abc import Mapping
from hashlib import sha256
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.evidence import document_key
from corpus_structure.semantic import _source_admission_calls as calls
from corpus_structure.semantic._data_operation_wire import WireInitializeSourceProjectRequest
from corpus_structure.semantic.data_operation_admission import admit_data_operation_release
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
from corpus_structure.semantic.original_documents import (
    OriginalDocumentConflict,
    acquire_original_document_selection,
    read_original_document_bytes,
    register_original_document,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.types import PreparationProfile
from semantic.original_document_support import source_admission_inputs


@pytest.mark.parametrize("source_uri", ["book.pdf", 'cafe\u0301/quoted"\\book.pdf'])
def test_current_source_initialization_retains_exact_bytes_without_local_fallback(
    commit_db_engine, commit_writer_engine, commit_reader_engine, tmp_path, source_uri
):
    bundle, dependencies, _ = source_admission_inputs()
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with commit_db_engine.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
    original = b"%PDF-1.7\nindependently specified retained source\x00\xff\n"
    path = tmp_path / "book.pdf"
    path.write_bytes(original)
    payload: WireInitializeSourceProjectRequest = {
        "project_id": ProjectId("source-custody"),
        "release_id": ReleaseId(prepared.release_id),
    }

    def register(
        connection: Connection,
        *,
        title: str | None = "Original",
        mime: str = "application/pdf",
        metadata: Mapping[str, Any] | None = None,
        original_path: str = str(path),
    ):
        return register_original_document(
            connection,
            prepared=prepared,
            project_id="source-custody",
            source_uri=source_uri,
            original_path=original_path,
            original=original,
            mime=mime,
            title=title,
            metadata={"empty": [], "null": None} if metadata is None else metadata,
        )

    def native_register(
        connection: Connection,
        *,
        release_id: ReleaseId | None = None,
        content_hash: str = "0" * 64,
    ):
        return calls.source_document_registration(
            connection,
            release_id=ReleaseId(prepared.release_id) if release_id is None else release_id,
            project_id=ProjectId("source-custody"),
            source_uri="invalid-hash.pdf",
            content_hash=content_hash,
            original_path=str(path),
            original=b"another binary original",
            mime="application/pdf",
            title=None,
            meta={},
            projection_context=prepared,
        )

    with commit_writer_engine.begin() as connection:
        assert DataOperationStorage(connection).initialize_source_project(payload) == payload
        registered = register(connection)
        assert registered > 0
        assert register(connection) == registered
        copy = tmp_path / "same-bytes-at-another-path.pdf"
        copy.write_bytes(original)
        for changed in (
            lambda: register(connection, title="Changed"),
            lambda: register(connection, mime="another/type"),
            lambda: register(connection, metadata={"empty": []}),
            lambda: register(connection, original_path=str(copy)),
        ):
            with (
                pytest.raises(OriginalDocumentConflict, match="another source descriptor"),
                connection.begin_nested(),
            ):
                changed()
        with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
            connection.execute(text("INSERT INTO kb.document DEFAULT VALUES"))
        assert getattr(refusal.value.orig, "sqlstate", None) == "42501"

        for changed in (
            lambda: native_register(connection),
            lambda: native_register(
                connection,
                release_id=ReleaseId("unfinalized-source-release"),
                content_hash=sha256(b"another binary original").hexdigest(),
            ),
        ):
            with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
                changed()
            assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
        assert connection.scalar(text("SELECT count(*) FROM kb.document")) == 1
        assert connection.scalar(text("SELECT count(*) FROM kb.source_artifact")) == 1
        assert DataOperationStorage(connection).initialize_source_project(payload) == payload
        reference = acquire_original_document_selection(
            connection,
            project_id="source-custody",
            document_key=document_key("source-custody", source_uri, sha256(original).hexdigest()),
        ).reference
    path.unlink()
    with commit_reader_engine.connect() as connection:
        assert read_original_document_bytes(connection, reference, prepared=prepared) == original
        with pytest.raises(DBAPIError) as refusal:
            DataOperationStorage(connection).initialize_source_project(payload)
        assert getattr(refusal.value.orig, "sqlstate", None) == "42501"
    with commit_reader_engine.connect() as connection, pytest.raises(DBAPIError) as refusal:
        native_register(connection)
    assert getattr(refusal.value.orig, "sqlstate", None) == "42501"
