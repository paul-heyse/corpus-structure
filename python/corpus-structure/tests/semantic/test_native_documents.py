"""Restricted PDF publication independent of HTML rendition custody."""

from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError, create_model
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_storage import read_native_items, read_native_regions

from .operation_scenario_support import prepare_operation_scenario


@pytest.mark.parametrize("captured_page", [False, pytest.param(True, marks=pytest.mark.corpus)])
def test_pdf_original_and_native_product_need_no_rendition(
    captured_page,
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        PageItem,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.semantic.pdf_contracts import (
        prepare_pdf_product,
        store_pdf_original,
    )

    prepared = prepare_operation_scenario(semantic_db_engine, observations=True, composed=True)
    original, recipe = b"%PDF-1.7\nindependent source fixture", b'{"recipe":"native-test"}'
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    doc = DoclingDocument(name="Independent")
    doc.pages[1] = PageItem(page_no=1, size=Size(width=200, height=300))
    doc.add_text(
        label=DocItemLabel.TEXT,
        text="Independent source.",
        orig="Independent source.",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=20, t=30, r=150, b=60, coord_origin="TOPLEFT"),
            charspan=(0, 19),
        ),
    )
    conversion = PdfConversion(
        sha256(original).hexdigest(), recipe, snapshot(doc), "success", (), (), (), None
    )
    source_path = tmp_path / "source.pdf"
    if captured_page:
        import json
        import os
        from pathlib import Path

        from corpus_structure.ingest.pdf_methods import _conversion_from_product

        repository = Path(__file__).resolve().parents[4]
        evidence = (
            repository / "docs/design_review/evidence/2026-10-31_pdf-serialization-retention/raw"
        )
        source = Path(
            os.environ.get(
                "CORPUS_PDF_QUALIFICATION_SOURCE",
                str(repository / "docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf"),
            )
        )
        if not source.exists() or not (evidence / "convert.payload.json").exists():
            pytest.skip("actual page85 native capture and retained original are required")
        source_path = source
        with source.open("rb") as stream:
            if stream.readline(128).strip() == b"version https://git-lfs.github.com/spec/v1":
                pytest.skip("retained page85 PDF requires Git LFS hydration")
            stream.seek(0)
            original = stream.read()
        recipe = (evidence / "convert.recipe.json").read_bytes()
        captured = json.loads((evidence / "convert.payload.json").read_bytes())
        assert captured["artifact_digest"] == sha256(original).hexdigest()
        assert (captured["page_start"], captured["page_end"]) == (85, 85)
        conversion = _conversion_from_product(SimpleNamespace(values=lambda: captured), recipe)
        # Prepare the older capture for a new publication before freezing its identity.
        doc = DoclingDocument.model_validate_json(conversion.native.payload)
        conversion = replace(conversion, native=snapshot(doc))
    probe = next(item for item in doc.texts if item.text and item.prov)
    expected_text = probe.text
    expected_box = probe.prov[0].bbox
    expected_origin = {"TOPLEFT": "top_left", "BOTTOMLEFT": "bottom_left"}[
        expected_box.coord_origin.value
    ]
    payload = publication_payload(
        conversion,
        product_key="native",
        schema_digest=sha256(schema).hexdigest(),
        include_application_metadata=False,
    )
    product = prepare_pdf_product(payload, original, schema, recipe)
    qualified_payload = publication_payload(
        conversion, product_key="qualified", schema_digest=sha256(schema).hexdigest()
    )
    qualified = prepare_pdf_product(qualified_payload, original, schema, recipe)
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="native-pdf-test",
        )
        method = SimpleNamespace(
            name="pdf.fixture",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("PdfFixture"),
        )
        config = record_method(conn, method, "default", {}, "pdf-fixture", prepared=prepared)
        if not captured_page:
            source_path.write_bytes(original)
        document_id = register_document(
            conn,
            project_id="p",
            source_uri="file:pdf-fixture",
            original_path=str(source_path),
            original=original,
            mime="application/pdf",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document_id,
            unit_key="pdf-source",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="pdf-fixture")[0]
        assert (
            store_pdf_original(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="pdf-fixture",
                original=original,
                recipe_bytes=recipe,
            )
            == sha256(original).hexdigest()
        )
    # Record publication settles before fallible application preparation or terminal completion.
    from .native_record_fixtures import publish_native_record_fixture

    published = publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "native-records",
        task_id=task,
        attempt=claim.attempt,
        holder="pdf-fixture",
        product=product,
        document=doc,
    )
    publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "qualified-records",
        task_id=task,
        attempt=claim.attempt,
        holder="pdf-fixture",
        product=qualified,
        document=doc,
    )
    digest = published.logical_digest
    # Optional application preparation can fail after exact native capture. Existing terminal
    # publication must retain that valid capture even when the task outcome is failed.
    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
    from corpus_structure.ingest.pdf_methods import _error_summary
    from corpus_structure.semantic.operations import complete_unit_result

    page_no = next(iter(doc.pages))
    application_conversion = replace(
        conversion,
        inline_candidates=(
            CandidatePage(
                page_no,
                True,
                False,
                (
                    InlineCandidate(
                        page_no, "", 20, 30, 40, 60, "TOPLEFT", None, "native-vector-gap-v1"
                    ),
                ),
                True,
            ),
        ),
    )
    application = publication_payload(
        application_conversion,
        product_key="organized",
        schema_digest=sha256(schema).hexdigest(),
        parent=(task, "native", digest),
    )
    # Omission succeeds; explicit null remains a contract violation (no widened slot).
    prepare_pdf_product(application, original, schema, recipe)
    application["inline_candidate_pages"][0]["candidates"][0]["font"] = None
    with pytest.raises(ValidationError) as invalid:
        prepare_pdf_product(application, original, schema, recipe)
    summary = _error_summary(invalid.value)
    assert "inline_candidate_pages.0.candidates.0.font" in summary
    legacy_arguments: dict[str, Any] = {"native_products": (product, qualified)}
    with pytest.raises(TypeError, match="native_products"):
        UnitResult(
            ref=UnitRef(TaskUnitType.DOCUMENT, document_id, "pdf-source"),
            outcome=ObservationOutcome.FAILED,
            error=summary,
            **legacy_arguments,
        )
    failed = UnitResult(
        ref=UnitRef(TaskUnitType.DOCUMENT, document_id, "pdf-source"),
        outcome=ObservationOutcome.FAILED,
        error=summary,
    )
    with semantic_writer_engine.begin() as conn:
        complete_unit_result(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="pdf-fixture",
            prepared=prepared,
            result=failed,
            method=method,
            configuration_hash="pdf-fixture",
            source="file:pdf-fixture",
        )
    with semantic_reader_engine.connect() as conn:
        state = conn.execute(
            text("SELECT status,error FROM ops.task WHERE id=:task"), {"task": task}
        ).one()
        assert state.status == "failed"
        assert len(str(state.error)) < 2000
        retained = conn.execute(
            text(
                "SELECT logical_digest FROM ops.read_pdf_published_revision(:task,'native',:digest)"
            ),
            {"task": task, "digest": digest},
        ).scalar_one()
        assert retained == digest
        rows = read_native_items(
            conn,
            task_id=task,
            product_key="native",
            content_digest=digest,
            pointer=probe.self_ref,
            projection_context=prepared,
        )
        assert rows[0]["text"] == expected_text
        regions = read_native_regions(
            conn,
            task_id=task,
            product_key="native",
            content_digest=digest,
            pointer=probe.self_ref,
            projection_context=prepared,
        )
        assert len(regions) == len(probe.prov)
        assert (
            regions[0]["left"] == Decimal(str(expected_box.l))
            and regions[0]["origin"] == expected_origin
        )
        with pytest.raises(ValueError, match="requires a published record"):
            read_native_items(conn, task_id=task, product_key="native", content_digest="0" * 64)
        assert conn.scalar(text("SELECT to_regclass('ops.rendition_build')")) is None

    if not captured_page:
        from corpus_structure.semantic.operations import end_source_run

        with semantic_writer_engine.begin() as conn:
            late = create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="ingest",
                unit_type="document",
                unit_id=document_id,
                unit_key="pdf-source",
                input_hash=sha256(original + b"late").hexdigest(),
            )
            late_claim = claim_tasks(conn, run_id=run, config_id=config, holder="late-native")[0]
            store_pdf_original(
                conn,
                task_id=late,
                attempt=late_claim.attempt,
                holder="late-native",
                original=original,
                recipe_bytes=recipe,
            )
            assert end_source_run(conn, run) == 1
        from corpus_structure.semantic.pdf_staging import begin_pdf_build

        with pytest.raises(DBAPIError), semantic_writer_engine.begin() as conn:
            begin_pdf_build(
                conn,
                task_id=late,
                attempt=late_claim.attempt,
                holder="late-native",
                source_digest=sha256(original).hexdigest(),
                recipe_digest=sha256(recipe).hexdigest(),
                schema_digest=sha256(schema).hexdigest(),
                replay_key="late-publication",
            )
        with semantic_reader_engine.connect() as conn:
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM "
                        "ops.read_pdf_published_revision(:task,'native',:digest)"
                    ),
                    {"task": late, "digest": digest},
                ).scalar_one()
                == 0
            )
