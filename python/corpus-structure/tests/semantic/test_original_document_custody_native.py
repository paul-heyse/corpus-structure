"""Native source initialization, immutable metadata, binary custody and actual purpose refusal."""

from hashlib import sha256

import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.evidence import document_key
from corpus_structure.semantic.data_operation_admission import admit_data_operation_release
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic._data_operation_wire import WireInitializeSourceProjectRequest
from corpus_structure.semantic.identifiers import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.original_documents import acquire_original_document_selection, read_original_document_bytes, register_original_document
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.types import PreparationProfile
from semantic.original_document_support import source_admission_inputs


def test_current_source_initialization_retains_exact_bytes_without_local_fallback(commit_db_engine,commit_writer_engine,commit_reader_engine,tmp_path):
    bundle, dependencies, prepared = source_admission_inputs()
    with commit_db_engine.begin() as connection:
        persist_release(connection,bundle,dependencies,PreparationProfile(version="semantic-2"),prepared)
        admit_data_operation_release(connection,prepared)
    original = b"%PDF-1.7\nindependently specified retained source\n"
    path = tmp_path / "book.pdf"
    path.write_bytes(original)
    payload: WireInitializeSourceProjectRequest = {"project_id":ProjectId("source-custody"), "release_id":ReleaseId(prepared.release_id),"realization_id":RealizationId("source-custody-empty")}
    with commit_writer_engine.begin() as connection:
        assert DataOperationStorage(connection).initialize_source_project(payload) == payload
        registered = register_original_document(connection,prepared=prepared,project_id="source-custody",source_uri="book.pdf",original_path=str(path),original=original,mime="application/pdf",title="Original")
        assert registered > 0
        reference = acquire_original_document_selection(connection,project_id="source-custody",document_key=document_key("source-custody","book.pdf",sha256(original).hexdigest())).reference
    path.unlink()
    with commit_reader_engine.connect() as connection:
        assert read_original_document_bytes(connection,reference,prepared=prepared) == original
        with pytest.raises(DBAPIError) as refusal:
            DataOperationStorage(connection).initialize_source_project(payload)
        assert getattr(refusal.value.orig,"sqlstate",None) == "42501"
