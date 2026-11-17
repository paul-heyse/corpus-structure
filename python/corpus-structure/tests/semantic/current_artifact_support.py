"""Actual current source/navigation custody with controlled literal PDF contents."""

from dataclasses import replace

from semantic.current_pdf_source_support import PROJECT, ROOT, CurrentPdfSource, current_pdf_recipe

ARTIFACT = "structure.artifact_identity/declared"
CONSTRUCTIONS = "text.constructions/source-native"


def artifact_recipe(directory):
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic.artifact_products import (
        artifact_inputs,
        artifact_operation_sources,
    )
    from corpus_structure.semantic.characterization_ports import construction_operation_sources
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
        read_data_operation_inputs,
    )
    from corpus_structure.semantic.construction_products import load_construction_options
    from corpus_structure.semantic.declared_structural_calls import (
        structural_operation_declarations,
    )
    from corpus_structure.semantic.predicate_products import predicate_operation_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.scoped_products import scoped_operation_sources
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact
    from semantic.data_operation_kernel_support import CapturedKernelInputs

    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    acquired = read_data_operation_inputs(captured.dependencies)
    assert acquired is not None and acquired[1] is not None
    declarations, sources = acquired
    assert sources is not None
    sources = combine_primary_sources(
        sources,
        construction_operation_sources(
            sentence_configuration=SentenceConfig(exclude=("ner",)),
            construction_options=load_construction_options(ROOT / "domains/statistics"),
        ),
        predicate_operation_sources(),
        scoped_operation_sources(),
        artifact_operation_sources(),
    )
    dependencies = data_operation_dependencies(
        ResolvedDependencies(
            (
                *(
                    item
                    for item in captured.dependencies.artifacts
                    if not item.name.startswith("data-operations/")
                ),
                SourceArtifact(
                    "operation/model-observation.json",
                    (
                        ROOT
                        / "python/corpus-structure/src/corpus_structure/methods/model_observation.json"
                    ).read_bytes(),
                ),
            ),
            captured.dependencies.vocabularies,
            captured.dependencies.ontology_sources,
        ),
        (*declarations, structural_operation_declarations()),
        sources,
    )
    return replace(
        original,
        name="current-artifact-cohort",
        captured_inputs=CapturedKernelInputs(
            artifact_inputs(captured.bundle), dependencies, captured.profile
        ),
    )


def artifact_stream(
    rows,
    self,
    source,
    *,
    spool_root,
    record_root,
    build_id,
    release_id,
    on_replay,
    check_active,
    page_size=(200, 300),
    **options,
):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        GroupLabel,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult

    check_active()
    document = DoclingDocument(name="Explicit controlled artifact passages")
    document.add_page(page_no=1, size=Size(width=page_size[0], height=page_size[1]))
    group = document.add_group(label=GroupLabel.SECTION, name="Selected artifact source")
    for label, literal in rows:
        document.add_text(
            label=DocItemLabel(label),
            text=literal,
            orig=literal,
            parent=group,
            prov=ProvenanceItem(
                page_no=1, bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, len(literal))
            ),
        )
    result = StreamingPdfResult(
        document,
        PdfStreamSpool(spool_root, check_active=check_active),
        "success",
        (),
        self.recipe.to_bytes(),
        (),
    )
    occurrences = result.write_native_occurrence_batches(
        record_root.with_name(record_root.name + "-occurrences"),
        build_id=build_id,
        on_batch=on_replay,
    )
    records = result.write_record_batches(
        record_root,
        build_id=build_id,
        release_id=release_id,
        source_digest=source.digest,
        on_batch=on_replay,
    )
    return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)


def companion_source(source, directory, monkeypatch, rows):
    """Register/capture an independent second original in the existing real project."""
    from hashlib import sha256
    from io import BytesIO

    import pypdfium2 as pdfium

    from corpus_structure.core.evidence import document_key
    from corpus_structure.ingest import pdf_worker
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        OperationSelection,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.original_documents import (
        acquire_original_document_selection,
        register_original_document,
    )

    document = pdfium.PdfDocument.new()
    page = document.new_page(210, 310)
    page.close()
    output = BytesIO()
    document.save(output)
    document.close()
    original = output.getvalue()
    assert original != source.original
    directory.mkdir()
    path = directory / "independent-other-book.pdf"
    path.write_bytes(original)
    kernel = source.kernel
    with kernel.purpose("write").begin() as connection:
        register_original_document(
            connection,
            prepared=kernel.prepared,
            project_id=PROJECT,
            source_uri="independent-other-book.pdf",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        key = document_key(PROJECT, "independent-other-book.pdf", sha256(original).hexdigest())
        selected = acquire_original_document_selection(
            connection, project_id=PROJECT, document_key=key
        )
        retained = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            freeze_demand(
                kernel.model,
                roots=(selected.root,),
                targets=("source.pdf_views/discovery",),
                original_sources=(selected.selection(),),
                selections=(
                    OperationSelection(
                        operation="source.pdf_views/discovery",
                        parameters=canonical_bytes(
                            {"sections": ["#/groups/0"], "membership": "descendants"}
                        ),
                    ),
                ),
                inference="independent-cross-work-original",
                execution_profile=kernel.recipe.execution_profile,
            ),
            project=PROJECT,
            release=kernel.prepared.release_id,
            runtime=kernel.runtime,
        )
    path.unlink()

    # Keep the actual worker receiver and original source execution owner.
    def stream(self, original_source, **options):
        return artifact_stream(rows, self, original_source, page_size=(210, 310), **options)

    monkeypatch.setattr(pdf_worker.PdfWorker, "stream", stream)
    result = execute_data_demand(
        kernel.purpose("write"),
        retained["demand_id"],
        source_root=ROOT,
        admission_engine=kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    assert result.receipt_count == 2
    return CurrentPdfSource(kernel, retained["demand_id"], key, original, ())
