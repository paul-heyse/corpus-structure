"""Actual current source custody and DDO publication, with a controlled converter only.

The fixture creates no legacy run, method configuration, task alias or source-view row.
Native registration, task claims, publication receipts and semantic products remain real.
It requires the combined current native capture; the controlled converter is not provider evidence.
"""

from contextlib import contextmanager
from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_storage import (
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.pdf_domain import pdf_domain_dependencies
from corpus_structure.semantic.pdf_views import pdf_views_operation_sources
from corpus_structure.semantic.source_discovery import (
    source_discovery_inputs,
    source_discovery_operation_sources,
)
from corpus_structure.semantic.source_profiles import (
    source_profile_declarations,
    source_profile_inputs,
    source_profile_operation_sources,
)
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, Kernel, KernelRecipe

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "current-source-catalog"


def current_pdf_recipe(directory, *, math_context=False):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets

    capture = pdf_capture_operation_sources(
        PdfRecipe(
            "0" * 40,
            "1" * 40,
            device="cpu",
            ocr_device="cpu",
            recipe_id="docling-standard-pdf-stream-v1",
        ),
        PreparedPdfAssets(directory, b"{}", ()),
        directory=directory / "owned",
    )
    from corpus_structure.semantic.native_requests import (
        pdf_region_inputs,
        pdf_region_operation_sources,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.visual_requests import (
        visual_external_declaration,
        visual_operation_sources,
    )

    sources = combine_primary_sources(
        pdf_views_operation_sources(capture),
        pdf_region_operation_sources(capture),
        visual_operation_sources(),
        source_discovery_operation_sources(),
        source_profile_operation_sources(),
    )
    if math_context:
        from corpus_structure.semantic.declared_math_products import (
            DeclaredMathOptions,
            math_profile_assets,
        )

        # Offline formula preparation consumes this actual captured profile;
        # a source-only recipe does not acquire an ambient mathematical context.
        sources = replace(
            sources,
            boundary_contracts=(
                *sources.boundary_contracts,
                math_profile_assets(DeclaredMathOptions()),
            ),
        )
    core = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
    bundle = source_profile_inputs(
        pdf_region_inputs(
            source_discovery_inputs(
                pdf_capture_inputs(
                    SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
                )
            )
        )
    )
    native = native_protocol_sources()
    pdf = pdf_domain_dependencies(ResolvedDependencies())
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*pdf.artifacts, *native, *capture_port_generator_sources())),
        (
            native_operation_declarations(native),
            visual_external_declaration(),
            source_profile_declarations(),
        ),
        sources,
    )
    return KernelRecipe(
        "current-pdf-source",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


@dataclass(frozen=True)
class CurrentPdfSource:
    kernel: Kernel
    demand_id: str
    document_key: str
    original: bytes
    sections: tuple[str, ...]

    def publication(self, connection):
        from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference
        from corpus_structure.serve.source_catalog import SourceCatalogRequest, read_source_catalog

        cursor = None
        for _ in range(100):
            page = read_source_catalog(
                connection,
                SourceCatalogRequest(
                    project_id=PROJECT,
                    demand_id=self.demand_id,
                    cursor=cursor,
                    limit=10,
                    max_bytes=8 * 1024 * 1024,
                ),
            )
            if page.rows:
                assert len(page.rows) == 1
                return SelectedPdfSourceReference.model_validate(page.rows[0]["selection"]), page
            if page.next_cursor is None:
                raise AssertionError("actual capture produced no selected publication")
            cursor = page.next_cursor
        raise AssertionError("bounded current source fixture did not reach its publication")

    def register(self, connection, target, *, selections=()):
        from corpus_structure.semantic.data_operation_json import json_loads
        from corpus_structure.semantic.data_operation_service import (
            DemandOriginalSelection,
            DemandRoot,
            NativeDemandRequest,
            create_native_demand,
        )
        from corpus_structure.semantic.original_documents import acquire_original_document_selection

        original = acquire_original_document_selection(
            connection, project_id=PROJECT, document_key=self.document_key
        )
        root = original.root
        request = NativeDemandRequest(
            project_id=PROJECT,
            release_id=self.kernel.prepared.release_id,
            runtime_id=self.kernel.runtime,
            roots=(
                DemandRoot(
                    subject=root.subject,
                    original_source=root.original_source,
                    analyzed_scope=json_loads(root.analyzed_scope),
                ),
            ),
            targets=(target,),
            selections=selections,
            original_sources={
                original.name: DemandOriginalSelection(
                    reference=original.reference.model_dump(mode="python"),
                    selectors=[{"scope": "whole-document"}],
                )
            },
            inference="current-source-journey",
            execution_profile="source-native",
        )
        return create_native_demand(connection, request)["demand_id"]


def _controlled_stream(
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
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult

    check_active()
    document = DoclingDocument(name="Independent current source")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    document.add_heading(text="1 Selected source", level=1)
    document.add_text(
        label=DocItemLabel.TEXT,
        text="Alice was running.",
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, 18)),
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


@contextmanager
def _current_pdf_source(
    scenario_seeds, tmp_path, monkeypatch, *, stream=None, sections=(), math_context=False
):
    from hashlib import sha256

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
    from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
    from corpus_structure.semantic.original_documents import (
        acquire_original_document_selection,
        register_original_document,
    )

    monkeypatch.setattr(pdf_worker.PdfWorker, "stream", stream or _controlled_stream)
    document = pdfium.PdfDocument.new()
    page = document.new_page(200, 300)
    page.close()
    output = BytesIO()
    document.save(output)
    document.close()
    original = output.getvalue()
    path = tmp_path / "independent-original.pdf"
    path.write_bytes(original)
    recipe = current_pdf_recipe(tmp_path, math_context=math_context)
    with scenario_seeds.commit_clone(recipe) as clone:
        stage = clone.stage
        kernel = Kernel(clone.admin, stage.preparation, stage.identities, recipe, clone)
        with kernel.purpose("write").begin() as connection:
            DataOperationStorage(connection).initialize_source_project(
                {
                    "project_id": ProjectId(PROJECT),
                    "release_id": ReleaseId(kernel.prepared.release_id),
                }
            )
            register_original_document(
                connection,
                prepared=kernel.prepared,
                project_id=PROJECT,
                source_uri="independent-original.pdf",
                original_path=str(path),
                original=original,
                mime="application/pdf",
            )
            key = document_key(PROJECT, "independent-original.pdf", sha256(original).hexdigest())
            selected = acquire_original_document_selection(
                connection, project_id=PROJECT, document_key=key
            )
            intent = freeze_demand(
                kernel.model,
                roots=(selected.root,),
                targets=("source.pdf_views/discovery",),
                original_sources=(selected.selection(),),
                selections=(
                    OperationSelection(
                        "source.pdf_views/discovery",
                        parameters=json_bytes(
                            {"sections": list(sections), "membership": "descendants"}
                        ),
                    ),
                )
                if sections
                else (),
                inference="current-source-journey",
                execution_profile=recipe.execution_profile,
            )
            demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
                intent, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
            )["demand_id"]
        path.unlink()  # The source owner must use retained custody, never a local fallback.
        result = execute_data_demand(
            kernel.purpose("write"),
            demand,
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
            project_id=PROJECT,
            database_capacity=6,
        )
        assert result.receipt_count == 2
        yield CurrentPdfSource(kernel, demand, key, original, tuple(sections))


@pytest.fixture
def current_pdf_source(scenario_seeds, tmp_path, monkeypatch):
    with _current_pdf_source(scenario_seeds, tmp_path, monkeypatch) as source:
        yield source


@pytest.fixture
def current_pdf_source_factory(scenario_seeds, tmp_path, monkeypatch):
    """Real current custody with independently selected converter section contents."""

    def acquire(rows, *, math_context=False):
        rows = tuple(rows)

        def stream(self, source, **options):
            return _section_stream(rows, self, source, **options)

        return _current_pdf_source(
            scenario_seeds,
            tmp_path,
            monkeypatch,
            stream=stream,
            sections=tuple("#/groups/" + str(i) for i in range(len(rows))),
            math_context=math_context,
        )

    return acquire


def _section_stream(
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
    document = DoclingDocument(name="Independently selected current sections")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    from corpus_structure.ingest.pdf_health import FormulaOutcome

    outcomes = []
    for i, (label, text, original, outcome) in enumerate(rows):
        group = document.add_group(label=GroupLabel.SECTION, name="Selected section " + str(i))
        if text or original:
            item = document.add_text(
                label=DocItemLabel(label),
                text=text,
                orig=original,
                parent=group,
                prov=ProvenanceItem(
                    page_no=1, bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, len(text))
                ),
            )
            if label == "formula":
                outcomes.append(FormulaOutcome(item.self_ref, outcome))
    result = StreamingPdfResult(
        document,
        PdfStreamSpool(spool_root, check_active=check_active),
        "success",
        (),
        self.recipe.to_bytes(),
        tuple(outcomes),
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


def admit_current_target(source, recipe, directory):
    """Admit a real separately captured consumer in the current source's clone."""
    from semantic.data_operation_kernel_support import admit_kernel, prepare_kernel

    directory.mkdir()
    preparation = prepare_kernel(recipe, directory=directory)
    with source.kernel.engine.begin() as connection:
        admitted = admit_kernel(
            connection, recipe, engine=source.kernel.engine, preparation=preparation
        )
    return Kernel(
        source.kernel.engine, preparation, admitted.identities, recipe, source.kernel.clone
    )


def selected_current_sources(source):
    """Read actual computational source members and their complete occurrence contexts."""
    from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry
    from corpus_structure.semantic.demand_results import stream_demand_result

    kinds = {
        item.key
        for item in source.kernel.model.identities
        if item.domain == "kind"
        and item.owner
        == "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource"
    }
    with source.kernel.purpose("read").begin() as connection:
        selected = []
        for page in stream_demand_result(connection, source.demand_id, project_id=PROJECT):
            for row in page.members():
                if row["kind_contract"] in kinds:
                    selected.append((dict(row, _selected_entry=SelectedSourceSetEntry.from_selected_header(row, page.cut)), row["body"]))
        return tuple(selected)


def source_entry(row):
    """Retain the exact source packet's native cut and producing occurrence."""
    return row["_selected_entry"]


def current_consumer_request(source, kernel, targets, *, discover=False):
    """Build explicit current intent over actual admitted computational contexts."""
    from corpus_structure.orchestrate.source_operation import _default_profile_selections
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import (
        DemandDiscoverySelection,
        DemandOperationSelection,
        DemandOriginalSelection,
        DemandRoot,
        NativeDemandRequest,
    )
    from corpus_structure.semantic.data_operation_source_discovery import source_discovery_relations
    from corpus_structure.semantic.original_documents import acquire_original_document_selection

    selections = _default_profile_selections(kernel.model, targets, {})
    original_sources, discovery, source_sets = {}, (), {}
    if discover:
        # This consumer discovers the fixture's explicitly pinned retained members.
        # The separately admitted consumer need not declare PDF recapture operations.
        producer = "source.selected_views/discovery"
        selections[producer] = DemandOperationSelection(
            operation=producer, parameters={"complete": True}
        )
        from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, source_sets_record

        source_sets = source_sets_record((FrozenSourceSet.from_selected(
            "selected-source-views", tuple(source_entry(row) for row, _ in selected_current_sources(source))
        ),))
        graph = kernel.model.projection_graph(
            "selected-dependencies",
            selected_dependencies=tuple(
                (name, value.selected_dependencies) for name, value in selections.items()
            ),
        )
        required = set(targets) | {producer}
        for target in tuple(required):
            required.update(graph.closure((target,)))
        relations = tuple(
            relation
            for target in sorted(required)
            for relation in source_discovery_relations(
                kernel.model,
                producer,
                "result",
                target,
                choices=selections[target].choices if target in selections else {},
            )
        )
        discovery = tuple(
            DemandDiscoverySelection(
                producer=relation.producer,
                output_role=relation.output_role,
                target=relation.target,
                population=relation.population,
                target_role=relation.target_role,
            )
            for relation in relations
        )
        root_targets = tuple(
            dict.fromkeys(
                (
                    producer,
                    *(
                        target
                        for target in targets
                        if target not in {row.target for row in relations}
                    ),
                )
            )
        )
        with kernel.purpose("write").begin() as connection:
            original = acquire_original_document_selection(
                connection, project_id=PROJECT, document_key=source.document_key
            )
        roots = (
            DemandRoot(
                subject=original.root.subject,
                original_source=original.root.original_source,
                analyzed_scope=json_loads(original.root.analyzed_scope),
            ),
        )
        original_sources = {original.name: DemandOriginalSelection(**original.selection().record())}
    else:
        root_targets = tuple(targets)
        roots = tuple(
            DemandRoot(
                subject=row["subject"],
                original_source=row["original_source"],
                analyzed_scope=row["analyzed_scope"],
            )
            for row, body in selected_current_sources(source)
        )
    return NativeDemandRequest(
        project_id=PROJECT,
        release_id=kernel.prepared.release_id,
        runtime_id=kernel.runtime,
        roots=roots,
        targets=root_targets,
        selections=tuple(selections.values()),
        discovery=discovery,
        original_sources=original_sources,
        source_sets=source_sets,
        execution_profile=kernel.recipe.execution_profile,
        inference="current-computational-source-test",
    )
