"""Real private PostgreSQL/IPC composition with a scripted native provider.

This establishes custody and lifecycle integration, not actual OCR/model execution
or source fidelity. Only the provider is replaced inside the spawned child.
"""

from hashlib import file_digest, sha256
from types import SimpleNamespace

import pytest
from semantic import conftest as semantic_fixtures
from semantic import test_pdf_staging as staging_fixtures
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_stream_reconciliation import write_recognition_replay
from corpus_structure.ingest.pdf_stream_types import PdfReplayRef, PdfStreamReply
from corpus_structure.ingest.pdf_worker import PdfWorker
from corpus_structure.orchestrate.pdf_streaming import run_private_native_pdf_build
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import claim_tasks, create_task, register_document
from corpus_structure.semantic.pdf_contracts import store_pdf_original
from corpus_structure.semantic.pdf_staging import inspect_pdf_progress

semantic_db_engine = semantic_fixtures.semantic_db_engine
semantic_writer_engine = semantic_fixtures.semantic_writer_engine
semantic_reader_engine = semantic_fixtures.semantic_reader_engine
private_build = staging_fixtures.private_build


class _ScriptedDocumentConverter:
    """External Docling provider control; application preparation/hooks remain actual."""

    def __init__(self, *, allowed_formats, format_options):
        from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel

        option = format_options[allowed_formats[0]]
        self.pipeline = object.__new__(option.pipeline_cls)
        self.pipeline.pipeline_options = option.pipeline_options
        self.pipeline.heading_hierarchy_model = SimpleNamespace(
            retain_parsed_lines=lambda page: None
        )
        formula = object.__new__(CodeFormulaVlmModel)
        formula.elements_batch_size = 1
        self.pipeline.enrichment_pipe = [formula]
        self.pipeline.assemble_model = SimpleNamespace(options=None)
        self.initialized_pipelines = {"control": self.pipeline}

    def initialize_pipeline(self, input_format):
        pass

    def convert(self, source, *, raises_on_error, **options):
        from docling.datamodel.base_models import AssembledUnit, Page
        from docling_core.types.doc import (
            BoundingBox,
            DocItemLabel,
            DoclingDocument,
            PageItem,
            ProvenanceItem,
            Size,
        )
        from PIL import Image

        image = Image.new("RGB", (20, 20), (3, 5, 7))
        page = Page(
            page_no=1,
            size=Size(width=10, height=10),
            assembled=AssembledUnit(elements=[], headers=[], body=[]),
        )
        page._image_cache = {2.0: image}
        self.pipeline._release_page_resources(SimpleNamespace(payload=page))
        image.close()
        document = DoclingDocument(name="scripted provider control")
        document.pages[1] = PageItem(page_no=1, size=Size(width=10, height=10))
        document.add_text(
            label=DocItemLabel.TEXT,
            text="Private control Ω",
            prov=ProvenanceItem(
                page_no=1,
                bbox=BoundingBox(l=1, t=1, r=9, b=3, coord_origin="TOPLEFT"),
                charspan=(0, 17),
            ),
        )
        return SimpleNamespace(
            document=document,
            status=SimpleNamespace(value="success"),
            errors=(),
            input=SimpleNamespace(release=lambda: None),
        )


def _controlled_native_child(connection, recipe, assets):
    # Replace only the external library provider, preserving model-owned application bindings.
    from docling import document_converter

    from corpus_structure.ingest import pdf_worker

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(document_converter, "DocumentConverter", _ScriptedDocumentConverter)
        pdf_worker._native_child(connection, recipe, assets)


def test_real_private_native_pipeline_adopts_pages_records_and_companions(
    private_build,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
    monkeypatch,
):
    original = b"%PDF-1.7\nscripted-native-provider-control"
    original_path = tmp_path / "controlled.pdf"
    original_path.write_bytes(original)
    recipe = PdfRecipe("a" * 40, "b" * 40, recipe_id="docling-standard-pdf-stream-v1")
    with semantic_writer_engine.begin() as connection:
        task = table("ops.task")
        baseline = (
            connection.execute(select(task).where(task.c.id == private_build.task_id))
            .mappings()
            .one()
        )
        document_id = register_document(
            connection,
            project_id="p",
            source_uri="file:private-streaming-control",
            original_path=str(original_path),
            original=original,
            mime="application/pdf",
        )
        task_id = create_task(
            connection,
            run_id=baseline["run_id"],
            config_id=baseline["method_config_id"],
            stage="ingest",
            unit_type="document",
            unit_id=document_id,
            unit_key="private-streaming-control",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(
            connection,
            run_id=baseline["run_id"],
            config_id=baseline["method_config_id"],
            holder="stream-control",
        )[0]
        assert claim.task_id == task_id
        store_pdf_original(
            connection,
            task_id=task_id,
            attempt=claim.attempt,
            holder="stream-control",
            original=original,
            recipe_bytes=recipe.to_bytes(),
        )
    replay_path = tmp_path / "recognition.arrow"
    write_recognition_replay(replay_path, iter(()))
    with replay_path.open("rb") as source:
        digest = file_digest(source, "sha256").hexdigest()
    observation_replay = PdfReplayRef(
        replay_path, digest, replay_path.stat().st_size, "recognition"
    )
    monkeypatch.setattr(PdfWorker, "_child_target", staticmethod(_controlled_native_child))
    original_stream = PdfWorker.stream
    replies = []

    def inspect_reply(self, *args, **kwargs):
        result = original_stream(self, *args, **kwargs)
        assert isinstance(result, PdfStreamReply)
        assert not hasattr(result, "document")
        assert not hasattr(result, "native")
        assert result.record_replays and result.page_replays
        replies.append(result)
        return result

    monkeypatch.setattr(PdfWorker, "stream", inspect_reply)
    adopted = []
    directory = tmp_path / "run"
    build = run_private_native_pdf_build(
        semantic_writer_engine,
        claim,
        "stream-control",
        original=original_path,
        recipe=recipe,
        assets=None,
        directory=directory,
        source_digest=sha256(original).hexdigest(),
        schema_digest=private_build.schema_digest,
        replay_key="native-stream",
        observation_replay=observation_replay,
        structural_pin={
            "task_id": task_id,
            "product_key": "private-native",
            "content_digest": "0" * 64,
            "role": "structural",
        },
        integration_policy={},
        on_adopted=adopted.append,
    )
    assert len(replies) == 1 and adopted
    assert not list(directory.glob("pdf-source-*")), "source ends after child settlement"
    with semantic_writer_engine.begin() as connection:
        receipts = inspect_pdf_progress(connection, build)
    assert len(receipts) == len(adopted)
    assert sum(receipt.row_count for receipt in receipts) > 10
    # Page assembly and its raster were committed before the child's acknowledgement.
    assert any(receipt.replay_key.startswith("page:1:assembly:") for receipt in receipts)
    assert any(receipt.replay_key.startswith("page:1:raster:") for receipt in receipts)
    assert any(receipt.replay_key.startswith("ipc:native:") for receipt in receipts)
    assert any(receipt.replay_key.startswith("ipc:artifact_stream:") for receipt in receipts)
    for relation in ("ops.pdf_stage_native", "ops.pdf_stage_artifact_part"):
        with semantic_reader_engine.begin() as connection, pytest.raises(DBAPIError):
            connection.execute(text(f"SELECT * FROM {relation}"))
    assert not hasattr(build, "content_digest"), "private receipt is not a published product"
