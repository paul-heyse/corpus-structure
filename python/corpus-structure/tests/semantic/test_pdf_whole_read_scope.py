"""Admitted bulk custody and narrow inventory preserve independent expected bytes."""

from contextlib import nullcontext
from hashlib import sha256
from unittest.mock import Mock

import pytest

from corpus_structure.semantic.pdf_record_identity import byte_root
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
from corpus_structure.semantic.refusals import ReadLimit
from semantic.pdf_record_reader_support import NativeRows, native


def bulk_reader(monkeypatch, content=b"independent retained bytes", *, parts=True, changed=False):
    reader = object.__new__(PublishedPdfReader)
    reader.read_budget = PublishedReadBudget(100, 100_000)
    reader.revision = {"release_id": "release", "source_digest": "a" * 64}
    reader.external_check_active = None
    calls = []
    length, root = byte_root((content,))
    descriptor = dict(
        stream_id="payload",
        byte_length=length,
        byte_root=root.hex(),
        serialization_sha256=sha256(content).hexdigest(),
        encoding_profile="pdf-record-scalar-v1:s",
    )

    def rows(family, filters=None, **kwargs):
        calls.append((family, filters))
        assert reader._whole_materialization
        if family == "artifact_stream":
            yield descriptor
        elif family == "artifact_part" and parts and content:
            yield dict(
                stream_id="payload",
                ordinal=0,
                byte_offset=0,
                byte_length=len(content),
                body=b"changed" if changed else content,
                sha256_digest=sha256(content).hexdigest(),
            )

    def events():
        calls.append(("native_events", None))
        yield {"kind": "literal", "value": "["}
        yield {"kind": "parts", "value": "payload"}
        yield {"kind": "literal", "value": ","}
        yield {"kind": "parts", "value": "payload"}
        yield {"kind": "literal", "value": "]"}

    monkeypatch.setattr(reader, "iter_rows", rows)
    monkeypatch.setattr(reader, "iter_native_events", events)
    monkeypatch.setattr(
        reader, "require_materialization_capacity", lambda: calls.append(("admission", None))
    )
    return reader, calls


def test_whole_read_fetches_and_verifies_each_stream_once_then_releases_cache(monkeypatch):
    reader, calls = bulk_reader(monkeypatch)
    assert reader.hydrate_document() == ["independent retained bytes"] * 2
    assert calls == [
        ("admission", None),
        ("artifact_stream", None),
        ("artifact_part", None),
        ("native_events", None),
    ]
    budget = reader.read_budget
    assert budget is not None and budget.bytes == len(b"independent retained bytes")
    assert reader._materialized_streams is None and not reader._whole_materialization


@pytest.mark.parametrize("defect", ["changed", "missing", "cumulative_bytes"])
def test_whole_read_refuses_invalid_parts_or_cumulative_budget_and_releases_custody(
    defect, monkeypatch
):
    reader, _ = bulk_reader(monkeypatch, parts=defect != "missing", changed=defect == "changed")
    if defect == "cumulative_bytes":
        reader.read_budget = PublishedReadBudget(100, 26, bytes=2)
    with pytest.raises((ValueError, ReadLimit)):
        reader.hydrate_document()
    assert reader._materialized_streams is None and not reader._whole_materialization


def test_whole_read_verifies_empty_stream_descriptor_with_no_parts(monkeypatch):
    reader, _ = bulk_reader(monkeypatch, b"")
    assert reader.hydrate_document() == ["", ""]


def test_admitted_pages_still_count_rows_without_preflight(monkeypatch):
    reader = object.__new__(PublishedPdfReader)
    reader.read_budget = PublishedReadBudget(1, 1000)
    reader._whole_materialization = True
    monkeypatch.setattr(reader, "_read_scope", nullcontext)

    class Result:
        def __enter__(self):
            return iter((("one",), ("two",)))

        def __exit__(self, *error):
            pass

    reader.conn = Mock()
    reader.conn.execute.return_value = Result()
    with pytest.raises(ReadLimit, match="row-work budget"):
        reader._raw_rows("bounded page")


def test_recognition_inventory_matches_page_keys_without_hydrating_page_bodies(monkeypatch):
    value = native()
    value["pages"] = {
        str(number): {"size": {"width": 100.0, "height": 100.0}, "page_no": number}
        for number in (3, 1)
    }
    reader = NativeRows(value)
    monkeypatch.setattr(
        reader,
        "iter_companions",
        lambda _: iter((dict(source_scope="whole_document", conversion="success"),)),
    )

    def forbidden():
        raise AssertionError("recognition must not hydrate the native document")

    monkeypatch.setattr(reader, "hydrate_document", forbidden)
    inventory = reader.recognition_inventory()
    assert inventory.page_nos == tuple(sorted(int(number) for number in value["pages"]))
    assert inventory.source_scope == "whole_document"
    assert inventory.health["conversion"] == "success"
    root = reader._one("header")["root_id"]
    reader.rows = [
        row
        for row in reader.rows
        if not (
            row.kind == "membership"
            and row.values["parent_id"] == root
            and row.values["field_name"] == "pages"
            and row.values["ordinal"] == 1
        )
    ]
    with pytest.raises(ValueError, match="membership inventory"):
        reader.recognition_inventory()
