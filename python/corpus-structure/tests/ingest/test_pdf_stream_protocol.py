"""Native stream protocol ordering with authored content and a scripted provider peer."""

import json
from contextlib import closing
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest
from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem, Size
from pdf_controlled_support import (
    ControlledPdfContent,
    controlled_native_child,
    controlled_pdf_stream,
    controlled_preparation_report,
)

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource, PdfStreamRequest
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, run_pdf_stream
from corpus_structure.ingest.pdf_worker import PdfWorker
from corpus_structure.semantic.pdf_certification import prepare_pdf_producer_contract
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context


@pytest.fixture
def stream_request(tmp_path):
    path = tmp_path / "original.pdf"
    path.write_bytes(b"%PDF-1.7\ncontrolled source")
    with OwnedPdfSource.acquire(path, tmp_path / "owned") as source:
        yield PdfStreamRequest(
            source,
            tmp_path / "pages",
            tmp_path / "records",
            "release",
            **asdict(prepare_pdf_producer_contract(trusted_pdf_context(), kind="native")),
        )


@pytest.fixture
def recipe():
    return PdfRecipe(
        "a" * 40,
        "b" * 40,
        device="cpu",
        ocr_device="cpu",
        recipe_id="docling-standard-pdf-stream-v1",
    )


def test_malformed_preparation_refuses_before_acknowledgement_or_conversion(stream_request):
    calls = []

    class Producer:
        def prepare(self, source, spool):
            calls.append("prepare")
            return b"{}"

        def convert(self, source, spool, *, page_range):
            pytest.fail("malformed preparation reached conversion")

    with pytest.raises(KeyError, match="_preparation"):
        run_pdf_stream(stream_request, Producer(), on_replay=lambda _reply: calls.append("ack"))
    assert calls == ["prepare"]


def test_changed_recovery_preparation_refuses_before_acknowledgement(
    stream_request, recipe, monkeypatch
):
    from corpus_structure.ingest import pdf_streaming

    spool = PdfStreamSpool(stream_request.spool_root)
    spool.preparation_identities.add("prior-preparation")
    report = controlled_preparation_report(recipe, None, spool)
    monkeypatch.setattr(pdf_streaming, "PdfStreamSpool", lambda *args, **kwargs: spool)
    acknowledged = []

    class Producer:
        def prepare(self, source, spool):
            return report

        def convert(self, source, spool, *, page_range):
            pytest.fail("changed preparation reached conversion")

    with pytest.raises(ValueError, match="resumed PDF native preparation differs"):
        run_pdf_stream(stream_request, Producer(), on_replay=acknowledged.append)
    assert acknowledged == []


def test_preparation_acknowledgement_cancellation_precedes_conversion(stream_request, recipe):
    checks = []

    class Producer:
        def prepare(self, source, spool):
            return controlled_preparation_report(recipe, None, spool)

        def convert(self, source, spool, *, page_range):
            pytest.fail("cancelled preparation reached conversion")

    def cancelled(replay):
        checks.append(replay.family)
        raise RuntimeError("cancelled after preparation")

    with pytest.raises(RuntimeError, match="cancelled after preparation"):
        run_pdf_stream(stream_request, Producer(), on_replay=cancelled)
    assert checks == ["native_preparation"]


def authored_content():
    document = DoclingDocument(name="scripted provider control")
    document.add_page(page_no=1, size=Size(width=10, height=10))
    document.add_text(
        label=DocItemLabel.TEXT,
        text="Private control Ω",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=1, t=1, r=9, b=3, coord_origin="TOPLEFT"),
            charspan=(0, 17),
        ),
    )
    return ControlledPdfContent.from_document(document)


class ScriptedWorker(PdfWorker):
    _child_target = staticmethod(controlled_native_child)


def test_controlled_content_and_real_peer_share_preparation_and_certified_document(
    stream_request, recipe
):
    from corpus_structure.ingest.pdf_build_spool import native_preparation_identity

    acknowledged = []
    with closing(ScriptedWorker(recipe)) as worker:
        actual = worker.stream(stream_request, on_replay=acknowledged.append)
    assert acknowledged[0].family == "native_preparation"
    assert acknowledged[-1].family == "producer_certification"
    assert actual.page_replays
    controlled_ack = []
    controlled = controlled_pdf_stream(
        SimpleNamespace(recipe=recipe, assets=None),
        replace(
            stream_request,
            spool_root=stream_request.spool_root.with_name("controlled-pages"),
            record_root=stream_request.record_root.with_name("controlled-records"),
        ),
        authored_content(),
        on_replay=controlled_ack.append,
    )
    assert controlled_ack[0].family == "native_preparation"
    assert controlled_ack[-1].family == "producer_certification"
    assert controlled.page_replays == ()
    assert native_preparation_identity(actual.effective_options) == native_preparation_identity(
        controlled.effective_options
    )
    assert actual.certification is not None and controlled.certification is not None
    assert (
        json.loads(actual.certification.path.read_bytes())["native_document_digest"]
        == json.loads(controlled.certification.path.read_bytes())["native_document_digest"]
    )
    for replay in (*acknowledged, *controlled_ack):
        replay.verify()


def test_request_payload_schema_reaches_controlled_candidate_encoding(stream_request, recipe):
    from corpus_structure.ingest.pdf_candidates import CandidatePage
    from corpus_structure.semantic.pdf_payloads import (
        PayloadContractError,
        prepare_payload_schema,
        schema_dump,
        schema_load,
    )

    original_family = prepare_payload_schema(schema_load(stream_request.payload_schema))
    schema = schema_load(stream_request.payload_schema)
    schema["title"] = "authored-candidate-schema"
    selected = replace(stream_request, payload_schema=schema_dump(schema))
    base = authored_content()
    document = DoclingDocument.model_validate_json(base.document_json)
    content = ControlledPdfContent.from_document(
        document, candidate_pages=(CandidatePage(1, False, False, ()),)
    )
    acknowledged = []
    # The request uses the new schema while its certificate contract deliberately stays old.
    with pytest.raises(PayloadContractError, match="payload schema binding differs"):
        controlled_pdf_stream(
            SimpleNamespace(recipe=recipe, assets=None),
            selected,
            content,
            on_replay=acknowledged.append,
        )
    (candidate,) = [replay for replay in acknowledged if replay.family == "candidate_payload"]
    assert candidate.page_no == 1
    assert candidate.schema_digest != original_family.schema_digest
    assert all(replay.family != "producer_certification" for replay in acknowledged)
