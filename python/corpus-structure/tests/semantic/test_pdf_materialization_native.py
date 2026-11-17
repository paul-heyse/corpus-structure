"""A native DDO PDF publication is bounded before whole-product detachment."""

import json

import pytest
from sqlalchemy import select

from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.original_documents import acquire_original_document_selection
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.refusals import ReadLimit
from semantic.current_pdf_integration_support import ROOT, current_pdf_recipe
from semantic.data_operation_kernel_support import Kernel
from semantic.data_operation_original_support import OriginalSeedRecipe


def test_exact_pdf_materialization_bound_admits_small_source_and_refuses_before_body(
    scenario_seeds, tmp_path, monkeypatch
):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest import pdf_worker

    def controlled_stream(
        self,
        source,
        *,
        spool_root,
        record_root,
        build_id,
        release_id,
        on_replay,
        check_active,
        **options,
    ):
        check_active()
        document = DoclingDocument(name="Independent materialization source")
        document.add_page(page_no=1, size=Size(width=200, height=300))
        document.add_text(
            label=DocItemLabel.TEXT,
            text="independent expected text",
            prov=ProvenanceItem(
                page_no=1,
                bbox=BoundingBox(l=10, t=20, r=150, b=40),
                charspan=(0, 25),
            ),
        )
        streamed = StreamingPdfResult(
            document,
            PdfStreamSpool(spool_root, check_active=check_active),
            "success",
            (),
            self.recipe.to_bytes(),
            (),
        )
        occurrences = streamed.write_native_occurrence_batches(
            record_root.with_name(record_root.name + "-occurrences"),
            build_id=build_id,
            on_batch=on_replay,
        )
        records = streamed.write_record_batches(
            record_root,
            build_id=build_id,
            release_id=release_id,
            source_digest=source.digest,
            on_batch=on_replay,
        )
        return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)

    monkeypatch.setattr(pdf_worker.PdfWorker, "stream", controlled_stream)
    recipe = OriginalSeedRecipe(current_pdf_recipe(tmp_path))
    with scenario_seeds.commit_clone(recipe) as clone:
        kernel = Kernel(
            clone.admin,
            clone.stage.kernel.preparation,
            clone.stage.kernel.identities,
            recipe.target,
            clone,
        )
        selected_original = clone.stage.original
        with kernel.purpose("write").begin() as connection:
            original = acquire_original_document_selection(
                connection,
                project_id=selected_original.reference.project_id,
                document_key=selected_original.reference.document_key,
            )
            intent = freeze_demand(
                kernel.model,
                roots=(original.root,),
                targets=("source.pdf/capture",),
                original_sources=(original.selection(),),
                inference="pdf-materialization-test",
                execution_profile=recipe.target.execution_profile,
            )
            demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
                intent,
                project=selected_original.reference.project_id,
                release=kernel.prepared.release_id,
                runtime=kernel.runtime,
            )["demand_id"]
        executed = execute_data_demand(
            kernel.purpose("write"),
            demand,
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert executed.receipt_count == 1
        intents, requests = table("ops.data_completion_intent"), table("ops.data_request")
        with clone.admin.connect() as connection:
            payload = connection.execute(
                select(intents.c.payload)
                .join_from(
                    intents,
                    requests,
                    requests.c.id == intents.c.request_id,
                )
                .where(requests.c.operation_id == "source.pdf/capture")
            ).scalar_one()
        assert isinstance(payload, dict)
        (receipt,) = payload["execution_evidence"]["pdf_receipts"]
        publication = receipt["publication"]
        pin = ProductReference(
            publication["task_id"],
            publication["product_key"],
            publication["logical_digest"],
        )
        with clone.admin.connect() as connection:
            from sqlalchemy import text

            context = (
                connection.execute(
                    text("SELECT * FROM ops.pdf_task_context(:task)"),
                    {"task": publication["task_id"]},
                )
                .mappings()
                .one()
            )
            assert "run_id" not in context
            assert context["request_id"] is not None
            documents = table("kb.document")
            actual_original = connection.execute(
                select(documents.c.project_id, documents.c.key, documents.c.content_hash).where(
                    documents.c.id == context["document_id"]
                )
            ).one()
            assert tuple(actual_original) == (
                selected_original.reference.project_id,
                selected_original.reference.document_key,
                selected_original.reference.content_hash,
            )
            request_demand = connection.scalar(
                text("SELECT demand_id FROM ops.demand_use WHERE request_id=:request LIMIT 1"),
                {"request": context["request_id"]},
            )
            assert request_demand == demand
        with kernel.purpose("read").connect() as connection:
            reader = PublishedPdfReader(
                connection,
                pin,
                projection_context=kernel.prepared,
                read_budget=PublishedReadBudget(100_000, 16 * 1024 * 1024),
            )
            bound = reader.require_materialization_capacity()
            # Independent content and real streamed serialization establish a lower
            # bound; the native scalar may conservatively include other custody.
            encoded = b"".join(reader.iter_native_json())
            assert b"independent expected text" in encoded
            assert bound >= len(encoded) > len(b"independent expected text")
            assert reader.hydrate_document() == json.loads(encoded)
            inventory = reader.recognition_inventory()
            assert inventory.page_nos == (1,)
            assert inventory.source_scope == "whole_document"
            assert inventory.health["conversion"] == "success"
            too_small = PublishedPdfReader(
                connection,
                pin,
                projection_context=kernel.prepared,
                read_budget=PublishedReadBudget(100_000, bound - 1),
            )

            def forbidden_body():
                raise AssertionError("source bytes fetched before aggregate input admission")

            monkeypatch.setattr(too_small, "iter_native_json", forbidden_body)
            with pytest.raises(ReadLimit, match="aggregate materialization"):
                too_small.hydrate_document()
