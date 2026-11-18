"""Independent PDF staging and inventory values; no source-run setup or provider claim."""

from __future__ import annotations

import json

from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
)

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.orchestrate.pdf_streaming import ipc_replay_batches
from corpus_structure.semantic.pdf_certification import (
    PdfProducerPayloads,
    prepare_pdf_producer_contract,
    write_pdf_companion_sets,
)
from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
from corpus_structure.semantic.pdf_payloads import prepare_payload_family
from corpus_structure.semantic.pdf_publication import (
    adopt_prepared_pdf_companion_batches,
    prepared_pdf_companion_batches,
    record_pdf_producer_certification,
    stage_pdf_access_projection,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch


def stage_pdf_document(
    engine, build, directory, document, *, companions=None, cell_coverage="unknown"
):
    """Certify the exact authored bytes before their native COPY and attestation.

    Fixtures share production callbacks/interior/projection validation, while
    their expected native values and deliberate SQL tampering stay independent.
    The first publication runs the real reconstruction oracle in validate_pdf_build.
    """
    from corpus_structure.semantic import _pdf_native_calls as calls
    from corpus_structure.semantic.identifiers import TaskAttempt, TaskId

    directory.mkdir(parents=True, exist_ok=True)
    with engine.begin() as conn:
        context = pdf_context_for_task(conn, build.task_id)
    contract = prepare_pdf_producer_contract(context, kind="native")
    result = StreamingPdfResult(
        document, PdfStreamSpool(directory / "pages"), "success", (), b"{}", ()
    )
    replays = tuple(
        result.write_record_batches(
            directory / "records",
            build_id=build.build_id,
            release_id=build.release_id,
            source_digest=build.source_digest,
        )
    )
    families = dict(companions or {})
    families.setdefault(
        "health",
        [
            {
                "conversion": "success",
                "display_coverage": "unknown",
                "inline_coverage": "unknown",
                "cell_coverage": cell_coverage,
                "source_scope": "whole_document",
            }
        ],
    )
    prepared = write_pdf_companion_sets(
        directory / "companions",
        build,
        families,
        payload_family=prepare_payload_family(context),
        check_active=lambda: None,
    )
    projection = directory / "producer-access.jsonl"
    payloads = PdfProducerPayloads(
        directory / "producer-payloads.sqlite", json.loads(contract.validation_contract)
    )
    try:
        payloads.add_replays(replays)
        payloads.add_companion_replays(prepared)
        pins = payloads.target_pins()
        targets = {}
        for start in range(0, len(pins), 64):
            selected = pins[start : start + 64]
            with engine.begin() as conn:
                values = json.loads(
                    calls.read_pdf_certification_targets(
                        conn,
                        build_id=build.build_id,
                        task_id=TaskId(build.task_id),
                        attempt=TaskAttempt(build.attempt),
                        holder=build.holder,
                        targets=[list(pin) for pin in selected],
                    )
                )
            assert len(values) == len(selected) and {tuple(item["pin"]) for item in values} == set(
                selected
            )
            targets.update((tuple(item["pin"]), item["meaning"]) for item in values)
        certification = payloads.certify(
            document,
            projection,
            release_id=build.release_id,
            source_digest=build.source_digest,
            recipe_digest=build.recipe_digest,
            schema_digest=build.schema_digest,
            kind="native",
            lowering_identity=contract.lowering_identity,
            target_meanings=targets,
        )
    finally:
        payloads.close()
    for batch in ipc_replay_batches(replays, check_active=lambda: None):
        with engine.begin() as conn:
            adopt_pdf_batch(conn, build, batch.replay_key, batch.relations)
    for group in prepared:
        batches = prepared_pdf_companion_batches(group)
        try:
            with engine.begin() as conn:
                adopt_prepared_pdf_companion_batches(conn, build, batches, group.replay_key)
        finally:
            batches.close()
    stage_pdf_access_projection(
        engine, build, projection, cancellation=BorrowerCancellation(), check_active=lambda: None
    )
    with engine.begin() as conn:
        record_pdf_producer_certification(conn, build, certification)
    return document


def stage_complete_native(
    engine, build, directory, *, cell_coverage="unknown", region=False, companions=None
):
    document = DoclingDocument(name="frozen fixture")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    expected = "independent expected text"
    provenance = (
        ProvenanceItem(
            page_no=1, bbox=BoundingBox(l=1, t=10, r=100, b=20), charspan=(0, len(expected))
        )
        if region
        else None
    )
    document.add_text(label=DocItemLabel.TEXT, text=expected, prov=provenance)
    return stage_pdf_document(
        engine, build, directory, document, companions=companions, cell_coverage=cell_coverage
    )


def inventory():
    words = []
    for index, (spelling, start, left, right) in enumerate(
        (("x", 0, 3, 12), ("=", 2, 15, 24), ("2", 4, 27, 36))
    ):
        words.append(
            dict(
                word_index=index,
                text=spelling,
                confidence=0.9,
                start=start,
                end=start + 1,
                raster_left=left,
                raster_top=6,
                raster_right=right,
                raster_bottom=21,
                left=26 + left / 3,
                top=42,
                right=26 + right / 3,
                bottom=47,
            )
        )
    region = dict(
        region_index=0,
        engine="rapidocr",
        raster_width=120,
        raster_height=60,
        scale=3.0,
        orientation=0,
        left=26,
        top=40,
        right=66,
        bottom=60,
        outcome="complete",
        lines=[dict(line_index=0, text="x = 2", words=words)],
    )
    word = words[0]
    candidate = {key: word[key] for key in ("text", "left", "top", "right", "bottom")}
    candidate.update(
        page_no=1,
        origin="TOPLEFT",
        basis="ocr-word-token-v1",
        ocr_region_index=0,
        ocr_line_index=0,
        ocr_word_index=0,
    )
    return dict(
        page_no=1,
        has_words=False,
        has_chars=False,
        has_vectors=True,
        native_text_quality="broken",
        ocr_regions=[region],
        candidates=[candidate],
    )


def seed_pdf_shared_stream(
    conn,
    build,
    stream_id,
    body,
    *,
    profile="pdf-record-scalar-v1:s",
    parts=None,
    declared_root=None,
    verify=True,
):
    """Author independent byte-verifier vectors under real project/build ownership.

    Only administrative SQL fixtures use this raw constructor. Invalid vectors
    remain pending and directly challenge the owning native fold; it creates no
    fake verification receipt or passed producer/oracle record.
    """
    from hashlib import sha256

    from sqlalchemy import text

    from corpus_structure.semantic.pdf_record_identity import byte_root

    length, root = byte_root((body,))
    params = dict(
        build=build.build_id,
        attempt=build.attempt,
        holder=build.holder,
        stream=stream_id,
        profile=profile,
        length=length,
        root=root.hex() if declared_root is None else declared_root,
        sha=sha256(body).hexdigest(),
    )
    project = conn.scalar(text("SELECT ops.pdf_stream_project(:build)"), params)
    assert project is not None
    params["project"] = project
    for relation in ("ops.pdf_stage_artifact_stream", "ops.pdf_artifact_stream"):
        conn.execute(
            text(
                f"INSERT INTO {relation} VALUES(:build,:build,:stream,:length,:sha,:root,:profile)"
            ),
            params,
        )
    conn.execute(
        text(
            "INSERT INTO ops.pdf_shared_stream VALUES(:project,:profile,:length,:root,:build,:attempt,:holder) "
            "ON CONFLICT DO NOTHING"
        ),
        params,
    )
    if parts is None:
        parts = [
            dict(ordinal=index, byte_offset=start, body=body[start : start + 65536])
            for index, start in enumerate(range(0, len(body), 65536))
        ]
    for part in parts:
        part_body = part["body"]
        assert isinstance(part_body, bytes)
        conn.execute(
            text(
                "INSERT INTO ops.pdf_shared_stream_part VALUES(:project,:profile,:length,:root,"
                ":ordinal,:offset,:part_length,:body,:part_sha) ON CONFLICT DO NOTHING"
            ),
            params
            | dict(
                ordinal=part["ordinal"],
                offset=part["byte_offset"],
                body=part_body,
                part_length=len(part_body),
                part_sha=sha256(part_body).hexdigest(),
            ),
        )
    if verify:
        conn.execute(text("SELECT ops.pdf_verify_shared_stream(:build,:stream,true)"), params)
