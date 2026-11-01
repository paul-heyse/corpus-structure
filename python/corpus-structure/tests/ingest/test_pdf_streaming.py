"""Independent source/spool/crop and lazy-native serialization controls for PDF22."""

import json
from hashlib import sha256
from types import SimpleNamespace

import pyarrow as pa
import pytest
from docling.datamodel.base_models import AssembledUnit, Page
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    Size,
    TableCell,
    TableData,
)
from PIL import Image

from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
from corpus_structure.ingest.pdf_streaming import (
    PdfStreamSpool,
    StreamingPdfResult,
    _json_view,
)


def test_owned_source_is_independent_of_operator_path_and_releases(tmp_path):
    path = tmp_path / "input.pdf"
    original = b"%PDF-1.7\n" + b"x" * 200000
    path.write_bytes(original)
    owner = OwnedPdfSource.acquire(
        path, tmp_path / "owned", expected_digest=sha256(original).hexdigest()
    )
    with owner as source:
        path.write_bytes(b"changed")
        source.verify()
        assert source.path.read_bytes() == original
        assert source.byte_length == len(original)
        retained = source.path
    assert not retained.exists()


def test_owned_source_refuses_digest_or_replacement(tmp_path):
    path = tmp_path / "input.pdf"
    path.write_bytes(b"%PDF-1.7\nhello")
    with pytest.raises(ValueError, match="digest differs"):
        OwnedPdfSource.acquire(path, tmp_path / "bad", expected_digest="0" * 64)
    assert list((tmp_path / "bad").iterdir()) == []
    owner = OwnedPdfSource.acquire(path, tmp_path / "owned")
    owner.reference.path.unlink()
    owner.reference.path.write_bytes(b"%PDF-1.7\nhello")
    with pytest.raises(ValueError, match=r"replaced or changed|writable"):
        owner.reference.verify()


def page_with_image():
    image = Image.new("RGB", (20, 20), (2, 3, 4))
    image.putpixel((3, 4), (100, 0, 0))
    page = Page(
        page_no=1,
        size=Size(width=10, height=10),
        assembled=AssembledUnit(elements=[], headers=[], body=[]),
    )
    assert page.__pydantic_private__ is not None
    page.__pydantic_private__["_backend"] = SimpleNamespace(unload=lambda: None)
    page._image_cache = {2.0: image}
    return page, image


def test_page_custody_precedes_release_and_restores_exact_crop(tmp_path):
    page, image = page_with_image()
    observed = []
    spool = PdfStreamSpool(tmp_path / "spool", on_page=observed.append)
    spool.capture_page(page, SimpleNamespace(retain_parsed_lines=lambda page: None), 2.0)
    assert len(observed) == 1
    assert page._backend is None and page.assembled is None and not page._image_cache
    result = SimpleNamespace(pages=[page])
    spool.restore_pages(result)
    restored = result.pages[0]
    box = BoundingBox(l=1, t=2, r=4, b=5, coord_origin=CoordOrigin.TOPLEFT)
    crop = restored.get_image(scale=2.0, cropbox=box)
    expected = image.crop((2, 4, 8, 10))
    assert crop.size == (6, 6)
    assert crop.tobytes() == expected.tobytes()
    crop.close()
    expected.close()
    image.close()
    with pytest.raises(ValueError, match="unrecorded"):
        restored.get_image(scale=1.0)


def test_failed_adoption_does_not_release_page(tmp_path):
    page, image = page_with_image()

    def refuse(_):
        raise RuntimeError("adoption refused")

    spool = PdfStreamSpool(tmp_path / "spool", on_page=refuse)
    with pytest.raises(RuntimeError, match="adoption refused"):
        spool.capture_page(page, SimpleNamespace(retain_parsed_lines=lambda page: None), 2.0)
    assert page._backend is not None and page.assembled is not None
    assert spool.pages == {}
    image.close()


def test_page_replay_refuses_corrupt_bytes(tmp_path):
    page, image = page_with_image()
    spool = PdfStreamSpool(tmp_path / "spool")
    spool.capture_page(page, SimpleNamespace(retain_parsed_lines=lambda page: None), 2.0)
    spool.pages[1].path.write_bytes(b"bad")
    with pytest.raises(ValueError, match="replay size changed"):
        spool.restore_pages(SimpleNamespace(pages=[page]))
    image.close()


def native_document():
    doc = DoclingDocument(name="native")
    doc.add_text(label=DocItemLabel.TEXT, text="Recognized Ω with repeated words words")
    doc.add_table(
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    text="42",
                    row_span=1,
                    col_span=1,
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                )
            ],
        )
    )
    return doc


def test_lazy_native_view_matches_pinned_export_without_whole_dump(monkeypatch):
    doc = native_document()
    expected = doc.export_to_dict()
    original = DoclingDocument.model_dump

    def guarded(self, *args, **kwargs):
        assert kwargs.get("exclude") or kwargs.get("include"), "whole document dump"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(DoclingDocument, "model_dump", guarded)
    assert json.loads(json.dumps(_json_view(doc, computed=True))) == expected


def test_record_replay_uses_exact_stage_schema_and_explicit_parts(tmp_path):
    from corpus_structure.semantic.pdf_staging import stage_schema

    doc = native_document()
    doc.texts[0].text = "x" * 100000
    spool = PdfStreamSpool(tmp_path / "spool")
    result = StreamingPdfResult(doc, spool, "success", (), b"qualified recipe", ())
    seen = []
    refs = result.write_record_batches(
        tmp_path / "records",
        build_id="build",
        release_id="release",
        source_digest="0" * 64,
        on_batch=seen.append,
    )
    assert tuple(seen) == refs
    assert {"header", "native", "membership", "reference", "artifact_part", "artifact_stream"} <= {
        ref.family for ref in refs
    }
    for ref in refs:
        ref.verify()
        with pa.memory_map(str(ref.path), "r") as source:
            reader = pa.ipc.open_file(source)
            assert reader.schema.equals(stage_schema(ref.family), check_metadata=True)
            batch = reader.get_batch(0)
            assert batch.num_rows == ref.rows
            assert batch.column("product_id").to_pylist() == ["build"] * ref.rows
            if ref.family == "artifact_part":
                assert max(batch.column("byte_length").to_pylist()) <= 65536


def test_logical_fields_do_not_depend_on_operational_build(tmp_path):
    from corpus_structure.semantic.pdf_records import native_record_identity_fields

    result = StreamingPdfResult(
        native_document(), PdfStreamSpool(tmp_path / "spool"), "success", (), b"", ()
    )

    def absent(*args):
        raise AssertionError("unexpected external scalar")

    def fields(build):
        return [
            (row.kind, native_record_identity_fields(row, scalar_descriptor=absent))
            for row in result.iter_records(
                product_id=build,
                revision_id=build,
                release_id="release",
                source_digest="0" * 64,
                write_scalar=absent,
            )
        ]

    assert fields("build-one") == fields("build-two")


def fake_stream_child(connection, recipe, assets):
    from corpus_structure.ingest.pdf_stream_types import (
        PdfReplayReady,
        PdfReplayRef,
        PdfStreamReply,
    )
    from corpus_structure.ingest.pdf_worker import NativeReply

    request = connection.recv()
    reference = PdfReplayRef(
        request.source.path, request.source.digest, request.source.byte_length, "page"
    )
    connection.send(PdfReplayReady(reference))
    if connection.recv() is True:
        connection.send(
            NativeReply(PdfStreamReply("success", (), recipe.to_bytes(), (reference,), ()))
        )
    connection.close()


def test_worker_adopts_replay_before_terminal_result(tmp_path):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_worker import PdfWorker

    source = tmp_path / "original.pdf"
    source.write_bytes(b"%PDF-1.7\nprotocol test")

    class Worker(PdfWorker):
        _child_target = staticmethod(fake_stream_child)

    recipe = PdfRecipe("a" * 40, "b" * 40, recipe_id="docling-standard-pdf-stream-v1")
    adopted = []
    with OwnedPdfSource.acquire(source, tmp_path / "sources") as ref:
        worker = Worker(recipe)
        try:
            result = worker.stream(
                ref,
                spool_root=tmp_path / "pages",
                record_root=tmp_path / "records",
                build_id="build",
                release_id="release",
                on_replay=adopted.append,
            )
            assert len(adopted) == 1 and result.page_replays == (adopted[0],)
            assert not hasattr(result, "document")
        finally:
            worker.close()


def test_lazy_view_preserves_native_origin_picture_and_typed_metadata(tmp_path):
    from docling_core.types.doc import DocumentOrigin, ImageRef, PictureMeta

    doc = native_document()
    doc.origin = DocumentOrigin(
        mimetype="application/pdf", binary_hash="a" * 64, filename="source.pdf"
    )
    picture = doc.add_picture()
    image = Image.new("RGB", (5, 5), "red")
    picture.image = ImageRef.from_pil(image, dpi=72)
    picture.meta = PictureMeta.model_validate(
        {"description": {"text": "An attributed description"}}
    )
    expected = doc.export_to_dict()
    assert json.loads(json.dumps(_json_view(doc, computed=True))) == expected
    stream = StreamingPdfResult(doc, PdfStreamSpool(tmp_path / "spool"), "success", (), b"{}", ())
    refs = stream.write_record_batches(
        tmp_path / "records", build_id="B", release_id="R", source_digest="0" * 64
    )
    assert any(ref.family == "artifact_part" for ref in refs)
    image.close()


def partial_stream_child(connection, recipe, assets):
    from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
    from corpus_structure.ingest.pdf_worker import NativeReply

    connection.recv()
    connection.send(
        NativeReply(
            PdfStreamReply("partial_success", ("native timeout",), recipe.to_bytes(), (), ())
        )
    )
    # Controller must kill/drain, rather than reuse this containing process.
    connection.recv()


def test_partial_stream_disposes_containing_worker(tmp_path):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_worker import PdfWorker

    class Worker(PdfWorker):
        _child_target = staticmethod(partial_stream_child)

    path = tmp_path / "input.pdf"
    path.write_bytes(b"%PDF-1.7\ncontrolled partial")
    with OwnedPdfSource.acquire(path, tmp_path / "source") as source:
        worker = Worker(PdfRecipe("a" * 40, "b" * 40, recipe_id="docling-standard-pdf-stream-v1"))
        try:
            result = worker.stream(
                source,
                spool_root=tmp_path / "pages",
                record_root=tmp_path / "records",
                build_id="build",
                release_id="release",
                on_replay=lambda _: None,
            )
            assert result.conversion_status == "partial_success"
            assert worker.closed and worker.pid is None
        finally:
            worker.close()
