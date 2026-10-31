"""Restricted PDF publication independent of HTML rendition custody."""

from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace

import pytest
from pydantic import create_model,ValidationError
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

from .test_operations import setup


def test_pdf_original_and_native_product_need_no_rendition(
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
        store_pdf_product,
    )

    prepared = setup(semantic_db_engine, observations=True, composed=True)
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
    payload = publication_payload(
        conversion, product_key="native", schema_digest=sha256(schema).hexdigest(),
        include_application_metadata=False,
    )
    product = prepare_pdf_product(payload, original, schema, recipe)
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="native-pdf-test",
        )
        method=SimpleNamespace(name="pdf.fixture",version="1",family="ingest",tier="deterministic",
            confidence_source=None,unit_type="document",Config=create_model("PdfFixture"))
        config = record_method(conn,method,"default",{},"pdf-fixture")
        source_path = tmp_path / "source.pdf"
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
    # A separate transaction models original retention before fallible inference.
    with semantic_writer_engine.begin() as conn:
        digest = store_pdf_product(
            conn, task_id=task, attempt=claim.attempt, holder="pdf-fixture", product=product
        )
        assert digest == product.digest
        assert (
            store_pdf_product(
                conn, task_id=task, attempt=claim.attempt, holder="pdf-fixture", product=product
            )
            == digest
        )
        with pytest.raises(DBAPIError), conn.begin_nested():
            store_pdf_product(
                conn, task_id=task, attempt=claim.attempt + 1, holder="pdf-fixture", product=product
            )
    from corpus_structure.semantic.identity import canonical_bytes

    mutations = [
        lambda value: value["items"].pop(),
        lambda value: value["regions"].clear(),
        lambda value: value["items"][0].update(ordinal=999),
        lambda value: value["items"][0].update(content_layer="forged-layer"),
    ]
    with semantic_writer_engine.begin() as conn:
        for index, mutate in enumerate(mutations):
            invalid = deepcopy(product.values())
            invalid["product_key"] = f"invalid-{index}"
            mutate(invalid)
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    text(
                        "SELECT ops.publish_native_document(:task,:attempt,:holder,:contract,"
                        ":payload,:original,:schema,:recipe)"
                    ),
                    dict(
                        task=task,
                        attempt=claim.attempt,
                        holder="pdf-fixture",
                        contract=product.contract_digest,
                        payload=canonical_bytes(invalid),
                        original=original,
                        schema=schema,
                        recipe=recipe,
                    ),
                )
    # Optional application preparation can fail after exact native capture. Existing terminal
    # publication must retain that valid capture even when the task outcome is failed.
    from corpus_structure.ingest.pdf_candidates import CandidatePage,InlineCandidate
    from dataclasses import replace
    from corpus_structure.ingest.pdf_methods import _error_summary
    from corpus_structure.core.method import UnitRef,UnitResult
    from corpus_structure.core.vocab import ObservationOutcome,TaskUnitType
    from corpus_structure.semantic.operations import complete_unit_result
    application_conversion=replace(conversion,inline_candidates=(CandidatePage(1,True,False,
        (InlineCandidate(1,'',20,30,40,60,'TOPLEFT',None,'native-vector-gap-v1'),),True),))
    application=publication_payload(application_conversion,product_key='organized',
        schema_digest=sha256(schema).hexdigest(),parent=(task,'native',product.digest))
    # Omission succeeds; explicit null remains a contract violation (no widened slot).
    prepare_pdf_product(application,original,schema,recipe)
    application['inline_candidate_pages'][0]['candidates'][0]['font']=None
    with pytest.raises(ValidationError) as invalid:
        prepare_pdf_product(application,original,schema,recipe)
    summary=_error_summary(invalid.value)
    assert 'inline_candidate_pages.0.candidates.0.font' in summary
    failed=UnitResult(ref=UnitRef(TaskUnitType.DOCUMENT,document_id,'pdf-source'),
        outcome=ObservationOutcome.FAILED,error=summary,native_products=(product,))
    with semantic_writer_engine.begin() as conn:
        complete_unit_result(conn,task_id=task,attempt=claim.attempt,holder='pdf-fixture',
            prepared=prepared,result=failed,method=method,configuration_hash='pdf-fixture',source='file:pdf-fixture')
    with semantic_reader_engine.connect() as conn:
        state=conn.execute(text('SELECT status,error FROM ops.task WHERE id=:task'),{'task':task}).one()
        assert state.status=='failed'
        assert len(str(state.error))<2000
        retained=conn.execute(text('SELECT content_digest FROM ops.native_document_product WHERE task_id=:task'),{'task':task}).scalar_one()
        assert retained==product.digest
        rows = read_native_items(
            conn, task_id=task, product_key="native", content_digest=digest, pointer="#/texts/0"
        )
        assert rows[0]["text"] == "Independent source."
        regions = read_native_regions(
            conn, task_id=task, product_key="native", content_digest=digest, pointer="#/texts/0"
        )
        assert len(regions) == 1 and regions[0]["left"] == 20 and regions[0]["origin"] == "top_left"
        with pytest.raises(ValueError, match="digest"):
            read_native_items(conn, task_id=task, product_key="native", content_digest="0" * 64)
        assert (
            conn.execute(
                text("SELECT count(*) FROM ops.rendition_build WHERE task_id=:task"), {"task": task}
            ).scalar_one()
            == 0
        )
