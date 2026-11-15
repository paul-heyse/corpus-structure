"""Original source bytes and physical descriptors retain independent exact expectations."""

from hashlib import sha256
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from corpus_structure.semantic.data_operation_support import OriginalDocumentRef
from corpus_structure.semantic.original_documents import (
    OriginalDocumentConflict,
    OriginalDocumentReadRefused,
    read_original_document_bytes,
    register_original_document,
)
from corpus_structure.semantic.types import PreparedRelease
from semantic.original_document_support import prepared_source_admission


class Result:
    def __init__(self, row=None):
        self.row = row

    def one_or_none(self):
        return self.row

    def scalar_one(self):
        return None

    def one(self):
        return self.row


def test_registration_refuses_file_bytes_that_differ_before_database_effects(tmp_path):
    original = tmp_path / "book.pdf"
    original.write_bytes(b"%PDF-file")
    connection = MagicMock()
    with pytest.raises(OriginalDocumentConflict, match="bytes differ"):
        register_original_document(
            connection,
            prepared=cast(PreparedRelease, None),
            project_id="p",
            source_uri="book.pdf",
            original_path=str(original),
            original=b"%PDF-other",
            mime="application/pdf",
        )
    connection.execute.assert_not_called()


def test_registration_dispatches_descriptor_and_binary_in_one_admitted_native_call(tmp_path):
    from corpus_structure.core.evidence import document_key

    original = b"%PDF-independent\x00binary original"
    path = tmp_path / "book.pdf"
    path.write_bytes(original)
    prepared = prepared_source_admission()
    digest = sha256(original).hexdigest()
    key = document_key("project", "book.pdf", digest)
    connection = MagicMock()
    connection.execute.return_value = Result(
        (17, "project", key, "book.pdf", digest, str(path), "application/pdf", None, '{"x":null}')
    )
    assert (
        register_original_document(
            connection,
            prepared=prepared,
            project_id="project",
            source_uri="book.pdf",
            original_path=str(path),
            original=original,
            mime="application/pdf",
            metadata={"x": None},
        )
        == 17
    )
    connection.execute.assert_called_once()
    statement = connection.execute.call_args.args[0]
    assert statement.compile().params == {
        "release_id": prepared.release_id,
        "project_id": "project",
        "source_uri": "book.pdf",
        "content_hash": digest,
        "original_path": str(path),
        "mime": "application/pdf",
        "title": None,
        "meta": {"x": None},
        "original": original,
    }


@pytest.mark.parametrize("body, outcome", [(None, "missing"), (b"corrupt", "invalid")])
def test_missing_or_corrupt_retained_bytes_do_not_open_a_local_fallback(monkeypatch, body, outcome):
    expected = b"%PDF-retained-original"
    reference = OriginalDocumentRef(
        kind="original-document",
        project_id="project",
        document_key="book",
        content_hash=sha256(expected).hexdigest(),
        mime="application/pdf",
    )
    prepared = prepared_source_admission()
    connection = MagicMock()
    connection.execute.side_effect = [
        Result(),
        Result((17, "project", "book", reference.content_hash, "application/pdf")),
        Result(None if body is None else (body,)),
    ]
    from corpus_structure.semantic import original_documents

    source_root = Path(original_documents.__file__).resolve().parents[1]
    read_bytes = Path.read_bytes

    def source_bytes_only(path):
        # Current helper custody may authenticate installed code/schema sources.
        # A document/corpus path must never replace missing retained bytes.
        if not path.resolve().is_relative_to(source_root):
            raise AssertionError("original read must use its retained artifact")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", source_bytes_only)
    with pytest.raises(OriginalDocumentReadRefused) as refusal:
        read_original_document_bytes(connection, reference, prepared=prepared)
    assert refusal.value.outcome == outcome


def test_original_source_helper_facade_is_current():
    from corpus_structure.semantic import _source_admission_calls
    from corpus_structure.semantic.original_document_contracts import generated_source_calls

    assert Path(_source_admission_calls.__file__).read_text() == generated_source_calls()
