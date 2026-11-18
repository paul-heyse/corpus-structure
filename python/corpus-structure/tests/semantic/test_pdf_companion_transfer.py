"""Prepared Arrow COPY units preserve bounded parts and exact encoded payload bytes."""

from types import SimpleNamespace
from typing import Any, cast

import pyarrow as pa

from corpus_structure.semantic import arrow_transfer, pdf_payloads, pdf_publication


def setup_transfer(monkeypatch):
    events, copies = [], []
    monkeypatch.setattr(
        pdf_publication,
        "calls",
        SimpleNamespace(
            prepare_pdf_companions=lambda conn: events.append("prepare"),
            adopt_pdf_companions=lambda conn, **kwargs: events.append(("adopt", kwargs)),
        ),
    )

    def copy(conn, profile, *, target, batches, **kwargs):
        for batch in batches:
            copies.append((target[1], batch.to_pylist()))

    monkeypatch.setattr(arrow_transfer, "copy_arrow_stream", copy)
    from corpus_structure.semantic.pdf_shared_streams import PdfSharedStreamTransfer

    monkeypatch.setattr(PdfSharedStreamTransfer, "omit_verified_parts", lambda *args: False)
    build = cast(
        Any,
        SimpleNamespace(
            build_id="build",
            release_id="release",
            task_id=1,
            attempt=1,
            holder="owner",
        ),
    )
    return build, events, copies


def test_many_field_parts_copy_in_bounded_units_then_adopt_once(monkeypatch):
    build, events, copies = setup_transfer(monkeypatch)
    batches = []
    pdf_publication.prepare_pdf_companion_batches(
        build,
        "native_metadata",
        [
            {
                "kind": "runtime_report",
                "ordinal": 0,
                "value": {"effective_options": "x" * (6 * 1024 * 1024)},
            },
        ],
        on_batch=lambda name, batch, batches=batches: batches.append((name, batch)),
        payload_family=None,
    )
    assert events == []
    pdf_publication.adopt_prepared_pdf_companion_batches(
        cast(Any, None), build, batches, "large-field"
    )
    assert events[0] == "prepare" and len(events) == 2 and events[1][0] == "adopt"
    assert len([name for name, _ in copies if name == "pc_pdf_stage_artifact_part"]) > 1
    assert sum(len(rows) for name, rows in copies if name == "pc_pdf_stage_companion") == 1
    assert sum(len(rows) for name, rows in copies if name == "pc_pdf_stage_companion_field") == 1
    assert all(len(rows) <= 64 for name, rows in copies if name == "pc_pdf_stage_artifact_part")


def test_prepared_encoded_payload_retains_exact_bytes_across_adoptions(monkeypatch):
    build, events, copies = setup_transfer(monkeypatch)
    codec = SimpleNamespace(read_batch=lambda *a, **k: pa.record_batch({"page_no": [1]}))
    encoded = pdf_payloads.EncodedPagePayload(b"original-ipc", "a" * 64, "b" * 64, 1)
    for _ in range(2):
        batches = []
        pdf_publication.prepare_pdf_companion_batches(
            build,
            "native_metadata",
            [
                {"kind": "inline_candidate_pages", "ordinal": 0, "value": encoded},
            ],
            on_batch=lambda name, batch, batches=batches: batches.append((name, batch)),
            payload_family=codec,
        )
        pdf_publication.adopt_prepared_pdf_companion_batches(
            cast(Any, None), build, batches, "same-page"
        )
    assert len(events) == 4 and all(event[0] == "adopt" for event in (events[1], events[3]))
    assert [
        row["body"] for name, rows in copies if name == "pc_pdf_stage_artifact_part" for row in rows
    ] == [b"original-ipc"] * 2
