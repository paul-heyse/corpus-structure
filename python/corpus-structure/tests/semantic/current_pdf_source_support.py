"""Actual current source custody and DDO publication, with a controlled converter only.

The fixture creates no legacy run, method configuration, task alias or source-view row.
Native registration, task claims, publication receipts and semantic products remain real.
It requires the combined current native capture; the controlled converter is not provider evidence.
"""

from contextlib import contextmanager
from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from pdf_controlled_support import ControlledPdfContent
from scenario_recipes import register_scenario_builder

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.native_protocol_authoring import (
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
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    Kernel,
    KernelRecipe,
    KernelSeedStage,
    build_kernel,
)

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "current-source-catalog"


def compose_current_pdf_recipe(directory, *, name, bundle, operation_sources, declarations=()):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets

    recipe = PdfRecipe(
        "0" * 40,
        "1" * 40,
        device="cpu",
        ocr_device="cpu",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    assets = PreparedPdfAssets(directory, b"{}", ())
    capture = pdf_capture_operation_sources(recipe, assets, directory=directory / "owned")
    native = native_protocol_sources()
    pdf = pdf_domain_dependencies(ResolvedDependencies())
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*pdf.artifacts, *native)),
        (native_operation_declarations(native), *declarations),
        operation_sources(recipe, assets, capture),
    )
    return KernelRecipe(
        name,
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


def current_pdf_recipe(directory, *, math_context=False):
    from corpus_structure.semantic.native_requests import (
        pdf_region_inputs,
        pdf_region_operation_sources,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.visual_requests import (
        visual_external_declaration,
        visual_operation_sources,
    )

    def operation_sources(_recipe, _assets, capture):
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
        return sources

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
    return compose_current_pdf_recipe(
        directory,
        name="current-pdf-source",
        bundle=bundle,
        operation_sources=operation_sources,
        declarations=(visual_external_declaration(), source_profile_declarations()),
    )


@dataclass(frozen=True)
class CurrentPdfSource:
    kernel: Kernel
    demand_id: str
    document_key: str
    original: bytes
    sections: tuple[str, ...]
    published_only: bool = False

    def publication(self, connection):
        from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
        from corpus_structure.serve.selected_pdf import (
            SelectedPdfSourceReference,
            acquire_selected_pdf_source,
        )

        # This fixture owns one known capture. A general catalog's first bounded
        # page may instead contain discovery, and incomplete serving code cannot
        # grant the continuation needed to search its later pages. Acquire a new
        # exact capture/source cut rather than treating that unknown as absence.
        page = serve_demand_query(
            connection,
            DemandQueryRequest(
                project_id=PROJECT,
                demand_id=self.demand_id,
                operation_id="source.pdf/capture",
                original_source=self.document_key,
                containers_only=True,
                limit=1,
                max_bytes=8 * 1024 * 1024,
            ),
        )
        if len(page["items"]) != 1 or page["items"][0]["member_id"] is not None:
            raise AssertionError("exact capture/source cut did not select its one publication")
        row = page["items"][0]
        reference = SelectedPdfSourceReference(
            project_id=PROJECT,
            demand_id=self.demand_id,
            read_id=page["cut"]["read_id"],
            use_id=row["use_id"],
            product_id=row["product_id"],
            derivation_id=row["derivation_id"],
        )
        # The operation filter narrows selection; only the native publication
        # owner establishes the nominal kind, sealed receipt and exact source.
        selected = acquire_selected_pdf_source(connection, reference)
        assert selected.original_source == self.document_key
        return reference, page

    def register(self, connection, target, *, selections=()):
        if self.published_only:
            raise ValueError(
                "published capture cannot register a new demand; use a writable PDF source"
            )
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


def source_content():
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        ProvenanceItem,
        Size,
    )
    from pdf_controlled_support import ControlledPdfContent

    document = DoclingDocument(name="Independent current source")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    document.add_heading(text="1 Selected source", level=1)
    document.add_text(
        label=DocItemLabel.TEXT,
        text="Alice was running.",
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, 18)),
    )
    return ControlledPdfContent.from_document(document, formula_outcomes=())


@dataclass(frozen=True)
class PdfSourceScenario:
    content: ControlledPdfContent
    sections: tuple[str, ...] = ()
    math_context: bool = False

    def bind(self, directory: Path) -> KernelRecipe:
        return current_pdf_recipe(directory, math_context=self.math_context)


@dataclass(frozen=True)
class PublishedCaptureStage:
    kernel: KernelSeedStage
    demand_id: str
    document_key: str
    original: bytes
    sections: tuple[str, ...]

    @property
    def seed_files(self):
        return self.kernel.seed_files

    @property
    def seed_origin(self):
        return {"capture_producer": "controlled-recipe-content"}

    def validate_clone(self, admin):
        from sqlalchemy import select

        from corpus_structure.semantic.metadata import table

        self.kernel.validate_clone(admin)
        obligations = table("ops.data_obligation")
        uses = table("ops.demand_use")
        receipts = table("ops.data_publication_receipt")
        # Inspect the two selected frontier facts and their actual publication
        # receipts, without reconstructing products or re-executing a provider.
        frontier = (
            select(
                obligations.c.operation_id,
                obligations.c.original_source,
                uses.c.fate,
                receipts.c.id.label("publication_receipt"),
            )
            .select_from(
                obligations.join(uses, uses.c.obligation_id == obligations.c.id).outerjoin(
                    receipts, receipts.c.derivation_id == uses.c.derivation_id
                )
            )
            .where(obligations.c.demand_id == self.demand_id)
            .distinct(obligations.c.id)
            .order_by(obligations.c.id, uses.c.created_at.desc(), uses.c.id.desc())
        )
        with admin.connect() as connection:
            rows = connection.execute(frontier).mappings().all()
        if (
            len(rows) != 2
            or {row["operation_id"] for row in rows}
            != {"source.pdf/capture", "source.pdf_views/discovery"}
            or any(
                row["original_source"] != self.document_key
                or row["fate"] != "fulfilled"
                or row["publication_receipt"] is None
                for row in rows
            )
        ):
            raise ValueError(
                "published PDF seed lacks its exact completed capture frontier/publication"
            )

    def acquired(self, clone, *, published_only=False):
        stage = self.kernel
        kernel = Kernel(clone.admin, stage.preparation, stage.identities, stage.recipe, clone)
        return CurrentPdfSource(
            kernel, self.demand_id, self.document_key, self.original, self.sections, published_only
        )


def _capture_source(kernel, directory, sections, *, source_uri="independent-original.pdf"):
    from hashlib import sha256

    import pypdfium2 as pdfium

    from corpus_structure.core.evidence import document_key
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

    document = pdfium.PdfDocument.new()
    page = document.new_page(200, 300)
    page.close()
    output = BytesIO()
    document.save(output)
    document.close()
    original = output.getvalue()
    path = directory / "independent-original.pdf"
    path.write_bytes(original)
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
            source_uri=source_uri,
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        key = document_key(PROJECT, source_uri, sha256(original).hexdigest())
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
            execution_profile=kernel.recipe.execution_profile,
        )
        demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            intent, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
    path.unlink()  # The source owner must use retained custody, never a local fallback.
    result = execute_data_demand(
        kernel.purpose("write"),
        demand,
        source_root=ROOT / "python/corpus-structure/src",
        admission_engine=kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    assert result.receipt_count == 2
    return demand, key, original


def build_pdf_source(
    scenario, admin, writer, directory, *, purpose_engine, source_uri="independent-original.pdf"
):
    from pdf_controlled_support import controlled_pdf_converter

    recipe = scenario.bind(directory)
    stage = build_kernel(recipe, admin, writer, directory, purpose_engine=purpose_engine)
    kernel = Kernel(
        admin,
        stage.preparation,
        stage.identities,
        recipe,
        SimpleNamespace(purpose=purpose_engine),
    )
    with controlled_pdf_converter(scenario.content):
        demand, document, original = _capture_source(
            kernel, directory, scenario.sections, source_uri=source_uri
        )
    return PublishedCaptureStage(stage, demand, document, original, scenario.sections)


register_scenario_builder(PdfSourceScenario, build_pdf_source)


@contextmanager
def _current_pdf_source(scenario_seeds, tmp_path, *, content=None, sections=(), math_context=False):
    scenario = PdfSourceScenario(content or source_content(), tuple(sections), math_context)
    with scenario_seeds.build_for_consumer(scenario, tmp_path) as clone:
        yield clone.stage.acquired(clone)


@contextmanager
def current_pdf_process_source(scenario_seeds, directory):
    """Acquire a writable case that executes the actual PDF worker process."""
    recipe = current_pdf_recipe(directory)
    with scenario_seeds.build_for_consumer(recipe, directory) as clone:
        stage = clone.stage
        kernel = Kernel(clone.admin, stage.preparation, stage.identities, recipe, clone)
        demand, key, original = _capture_source(kernel, directory, ())
        yield CurrentPdfSource(kernel, demand, key, original, ())


@contextmanager
def _published_pdf_source(scenario_seeds, *, content=None, sections=(), math_context=False):
    """Clone a completed capture; every later converter entry is a classification error."""
    from unittest.mock import patch

    from corpus_structure.ingest.pdf_worker import PdfWorker

    scenario = PdfSourceScenario(content or source_content(), tuple(sections), math_context)
    with scenario_seeds.commit_clone(scenario) as clone:

        def unexpected_conversion(*_args, **_kwargs):
            raise AssertionError(
                "published PDF capture consumer reached converter; use a writable PDF source"
            )

        with patch.object(PdfWorker, "stream", unexpected_conversion):
            yield clone.stage.acquired(clone, published_only=True)


@pytest.fixture
def published_pdf_source(scenario_seeds):
    with _published_pdf_source(scenario_seeds) as source:
        yield source


@pytest.fixture(scope="module")
def published_pdf_source_factory(scenario_seeds):
    """Share recipe-described published section captures across post-capture consumers."""

    def acquire(rows, *, math_context=False):
        rows = tuple(rows)
        return _published_pdf_source(
            scenario_seeds,
            content=section_content(rows),
            sections=tuple("#/groups/" + str(i) for i in range(len(rows))),
            math_context=math_context,
        )

    return acquire


@pytest.fixture
def current_pdf_source(scenario_seeds, tmp_path):
    with _current_pdf_source(scenario_seeds, tmp_path) as source:
        yield source


@pytest.fixture
def current_pdf_source_factory(scenario_seeds, tmp_path):
    """Real current custody with independently selected converter section contents."""

    def acquire(rows, *, math_context=False):
        rows = tuple(rows)

        return _current_pdf_source(
            scenario_seeds,
            tmp_path,
            content=section_content(rows),
            sections=tuple("#/groups/" + str(i) for i in range(len(rows))),
            math_context=math_context,
        )

    return acquire


def section_content(rows, *, one_section=False):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        GroupLabel,
        ProvenanceItem,
        Size,
    )
    from pdf_controlled_support import ControlledPdfContent

    document = DoclingDocument(name="Independently selected current sections")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    from corpus_structure.ingest.pdf_health import FormulaOutcome

    outcomes = []
    group = None
    for i, (label, text, original, outcome) in enumerate(rows):
        if group is None or not one_section:
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
    return ControlledPdfContent.from_document(document, formula_outcomes=tuple(outcomes))


def admit_current_target(source, recipe, directory):
    """Admit a real separately captured consumer in the current source's clone."""
    from semantic.data_operation_kernel_support import admit_kernel, prepare_kernel

    directory.mkdir()
    if not isinstance(recipe, KernelRecipe):
        recipe = recipe.bind(directory)
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
    from corpus_structure.semantic.selected_support import SelectedReadReference

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
            read = SelectedReadReference.from_cut(page.cut)
            for row in page.members():
                if row["kind_contract"] in kinds:
                    selected.append(
                        (
                            dict(
                                row,
                                _selected_entry=SelectedSourceSetEntry.from_selected_header(
                                    row, read
                                ),
                            ),
                            row["body"],
                        )
                    )
        return tuple(selected)


def source_entry(row):
    """Retain the exact source packet's native cut and producing occurrence."""
    return row["_selected_entry"]


def current_consumer_request(source, kernel, targets, *, discover=False, discovered_entries=None):
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

    if discovered_entries is not None and not discover:
        raise ValueError("preselected discovered entries require source discovery")
    selections = _default_profile_selections(kernel.model, targets, {})
    original_sources, discovery, source_sets = {}, (), {}
    if discover:
        # This consumer discovers the fixture's explicitly pinned retained members.
        # The separately admitted consumer need not declare PDF recapture operations.
        producer = "source.selected_views/discovery"
        selections[producer] = DemandOperationSelection(
            operation=producer, parameters={"complete": True}
        )
        from corpus_structure.semantic.data_operation_source_sets import (
            FrozenSourceSet,
            source_sets_record,
        )

        source_sets = source_sets_record(
            (
                FrozenSourceSet.from_selected(
                    "selected-source-views",
                    tuple(source_entry(row) for row, _ in selected_current_sources(source))
                    if discovered_entries is None
                    else tuple(discovered_entries),
                ),
            )
        )
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
