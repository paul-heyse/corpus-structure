"""Bounded COPY units do not create per-row adoption or rebuild payload families."""

from types import SimpleNamespace
from typing import Any, cast

import pyarrow as pa

from corpus_structure.semantic import arrow_transfer, pdf_contracts, pdf_payloads, pdf_publication


def setup_transfer(monkeypatch):
    events, copies = [], []
    monkeypatch.setattr(pdf_publication, "calls", SimpleNamespace(
        prepare_pdf_companions=lambda conn: events.append("prepare"),
        adopt_pdf_companions=lambda conn, **kwargs: events.append(("adopt", kwargs)),
    ))

    def copy(conn, profile, *, target, batches, **kwargs):
        for batch in batches:
            copies.append((target[1], batch.to_pylist()))

    monkeypatch.setattr(arrow_transfer, "copy_arrow_stream", copy)
    build = cast(Any, SimpleNamespace(build_id="build", release_id="release", task_id=1, attempt=1,
                                      holder="owner", _payload_family=None))
    return build, events, copies


def test_many_field_parts_copy_in_bounded_units_then_adopt_once(monkeypatch):
    build, events, copies = setup_transfer(monkeypatch)
    pdf_publication.adopt_pdf_companions(cast(Any, None), build, "native_metadata", [
        {"kind": "runtime_report", "ordinal": 0, "value": {"effective_options": "x" * (6 * 1024 * 1024)}},
    ], "large-field")
    assert events[0] == "prepare" and len(events) == 2 and events[1][0] == "adopt"
    assert len([name for name, _ in copies if name == "pc_pdf_stage_artifact_part"]) > 1
    assert sum(len(rows) for name, rows in copies if name == "pc_pdf_stage_companion") == 1
    assert sum(len(rows) for name, rows in copies if name == "pc_pdf_stage_companion_field") == 1
    assert all(len(rows) <= 64 for name, rows in copies if name == "pc_pdf_stage_artifact_part")


def test_payload_family_prepared_once_for_same_build_without_reencoding(monkeypatch):
    build, events, copies = setup_transfer(monkeypatch)
    prepared = []
    codec = SimpleNamespace(read_batch=lambda *a, **k: pa.record_batch({"page_no": [1]}))
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", lambda *args: "exact context")
    monkeypatch.setattr(pdf_payloads, "prepare_payload_family", lambda context: prepared.append(context) or codec)
    encoded = pdf_payloads.EncodedPagePayload(b"original-ipc", "a" * 64, "b" * 64, 1)
    for _ in range(2):
        pdf_publication.adopt_pdf_companions(cast(Any, None), build, "native_metadata", [
            {"kind": "inline_candidate_pages", "ordinal": 0, "value": encoded},
        ], "same-page")
    assert prepared == ["exact context"]
    assert len(events) == 4 and all(event[0] == "adopt" for event in (events[1], events[3]))
    assert [row["body"] for name, rows in copies if name == "pc_pdf_stage_artifact_part" for row in rows] == [b"original-ipc"] * 2


def test_dispatch_uses_producer_encoded_row_length_without_serializing_again(monkeypatch):
    from contextlib import nullcontext

    from corpus_structure.core.db.lifetime import BorrowerCancellation
    from corpus_structure.orchestrate import pdf_streaming
    from corpus_structure.semantic import identity

    rows = [pdf_publication.PdfCompanionRecord({"ordinal": i}, len(f'{{"ordinal":{i}}}'.encode())) for i in range(3)]
    adopted = []
    monkeypatch.setattr(pdf_streaming, "_pdf_transaction", lambda *_: nullcontext(None))
    monkeypatch.setattr(pdf_publication, "adopt_pdf_companions", lambda conn, build, family, records, **kwargs: adopted.extend(records))

    def forbidden(_):
        raise AssertionError("producer row was serialized again merely to size it")

    monkeypatch.setattr(identity, "canonical_bytes", forbidden)
    pdf_streaming.adopt_pdf_companions(cast(Any, None), cast(Any, None), "health", rows, "producer",
                                      check_active=lambda: None, cancellation=BorrowerCancellation())
    assert adopted == rows
