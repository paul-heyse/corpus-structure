"""Private staged PDF build fixture shared by native consumer tests."""

from hashlib import sha256
from types import SimpleNamespace

import pyarrow as pa
import pytest
from pydantic import create_model

from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_contracts import store_pdf_original
from corpus_structure.semantic.pdf_records import native_schema_bytes
from corpus_structure.semantic.pdf_staging import (
    begin_pdf_build,
    stage_schema,
)

from .operation_scenario_support import prepare_operation_scenario


@pytest.fixture
def private_build(semantic_db_engine, semantic_writer_engine, tmp_path, request):
    prepared = prepare_operation_scenario(
        semantic_db_engine, composed=True,
        observations=getattr(request, "param", None) == "renderable_pdf",
    )
    recipe = b'{"recipe":"stage-test"}'
    path = tmp_path / "source.pdf"
    if getattr(request, "param", None) == "renderable_pdf":
        from pdf_acceptance_support import write_controlled_pdf

        original = write_controlled_pdf(path, ("Region section", "evidence"))
    else:
        original = b"%PDF-1.7 private staging fixture"
        path.write_bytes(original)
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="stage-test",
        )
        method = SimpleNamespace(
            name="pdf.stage.fixture",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("PdfStageFixture"),
        )
        config = record_method(conn, method, "default", {}, "pdf-stage", prepared=prepared)
        document = register_document(
            conn,
            project_id="p",
            source_uri="file:pdf-stage",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="pdf-stage",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="stage-owner")[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="stage-owner",
            original=original,
            recipe_bytes=recipe,
        )
        build = begin_pdf_build(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="stage-owner",
            source_digest=sha256(original).hexdigest(),
            recipe_digest=sha256(recipe).hexdigest(),
            schema_digest=sha256(native_schema_bytes()).hexdigest(),
            replay_key="build-1",
        )
    return build


def native_batch(build, text_value="first"):
    return pa.RecordBatch.from_pylist(
        [
            dict(
                product_id=build.product_id,
                revision_id=build.revision_id,
                record_id="node-1",
                native_type="TextItem",
                family="node",
                native_address="#/texts/0",
                native_address_stream_id=None,
                scalars_json='{"text":"' + text_value + '"}',
                structure_json="{}",
            )
        ],
        schema=stage_schema("native"),
    )
