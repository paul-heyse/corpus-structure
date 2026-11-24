"""Actual current PDF, formal, construction and composition test custody.

Only PDF record contents are controlled. Registration, declarations, requests,
native claims, sealed receipts, CPU execution and selected reads remain real.
This helper supplies no model/provider execution evidence.
"""

from dataclasses import dataclass, replace
from typing import Any

import pytest
from sqlalchemy import Engine

from corpus_structure.semantic.characterization_ports import (
    construction_operation_sources,
    document_view_operation_sources,
)
from corpus_structure.semantic.composed import (
    data_operation_dependencies,
)
from corpus_structure.semantic.construction_products import construction_product_inputs
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_service import execute_data_demand, read_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.original_documents import acquire_original_document_selection
from corpus_structure.semantic.pdf_publication import PublishedPdfDocumentRef
from corpus_structure.semantic.pdf_staging import PdfBuildRef
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.source_products import FrozenNativeSource
from semantic.current_pdf_source_support import ROOT, current_pdf_recipe
from semantic.data_operation_kernel_support import CapturedKernelInputs, split_captured_operations
from semantic.pdf_staging_support import _private_build_factory, _PrivatePdfBuildFactory
from semantic.selected_source_native_support import publish_selected


def characterization_recipe(directory, *, construction_options=None):
    """Extend the closed current source package with its actual analytical owners."""
    recipe = current_pdf_recipe(directory)
    captured = recipe.captured_inputs
    assert captured is not None
    base_dependencies, declarations, current = split_captured_operations(captured)
    from corpus_structure.ingest.sentences import SentenceConfig

    sources = combine_primary_sources(
        current,
        construction_operation_sources(
            construction_options=construction_options,
            sentence_configuration=SentenceConfig(exclude=("ner",)),
        ),
        document_view_operation_sources(),
    )
    # Recompose the decoded declaration package once. All independent native/PDF
    # inputs remain supplied, including their original registration authority.
    dependencies = base_dependencies
    return replace(
        recipe,
        name="current-characterization-controls",
        captured_inputs=CapturedKernelInputs(
            construction_product_inputs(captured.bundle),
            data_operation_dependencies(dependencies, declarations, sources),
            captured.profile,
        ),
    )


@pytest.fixture(scope="module")
def current_characterization_recipe(tmp_path_factory):
    return characterization_recipe(tmp_path_factory.mktemp("current-characterization"))


@dataclass(frozen=True)
class CurrentCharacterization:
    factory: _PrivatePdfBuildFactory
    build: PdfBuildRef
    publication: PublishedPdfDocumentRef
    source_row: dict[str, Any]
    reader: Engine

    @property
    def kernel(self):
        return self.factory.kernel

    @property
    def source(self):
        return FrozenNativeSource.acquire(self.kernel.prepared, self.source_row["body"])

    @property
    def context(self):
        row = self.source_row
        return SubjectContext(
            self.factory.project_id,
            row["subject"],
            row["original_source"],
            json_bytes(row["analyzed_scope"]),
            subject_definition=row["subject_definition"],
        )

    def register(self, target, *, profile=None, products=(), active=()):
        from corpus_structure.orchestrate.source_operation import _default_profile_selections
        from corpus_structure.semantic.data_operation_service import DemandOperationSelection
        from corpus_structure.semantic.data_operation_source_discovery import (
            source_discovery_relations,
        )
        from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
        from corpus_structure.semantic.enriched_document_products import (
            freeze_characterization_selection,
        )

        analytical_sources = ()
        if target == "text.compose_view/source-native":
            if profile is None:
                raise ValueError("retained composition requires an explicit profile")
            analytical_sources = freeze_characterization_selection(
                profile=profile, products=products, active=active
            )
        producer = "source.selected_views/discovery"
        supplied = (
            {target: DemandOperationSelection(operation=target, parameters={"profile": profile})}
            if profile is not None
            else {}
        )
        selections = _default_profile_selections(self.kernel.model, (target,), supplied)
        selections[producer] = DemandOperationSelection(
            operation=producer, parameters={"complete": True}
        )
        graph = self.kernel.model.projection_graph(
            "selected-dependencies",
            selected_dependencies=tuple(
                (name, value.selected_dependencies) for name, value in selections.items()
            ),
        )
        required = {target, producer, *graph.closure((target,))}
        relations = tuple(
            relation
            for operation in sorted(required)
            for relation in source_discovery_relations(
                self.kernel.model,
                producer,
                "result",
                operation,
                choices=selections[operation].choices if operation in selections else {},
            )
        )
        targets = (producer,) if target in {row.target for row in relations} else (producer, target)
        with self.factory.writer.begin() as connection:
            original = acquire_original_document_selection(
                connection, project_id=self.factory.project_id, document_key=self.factory.key
            )
            intent = freeze_demand(
                self.kernel.model,
                roots=(original.root,),
                targets=targets,
                selections=tuple(
                    OperationSelection(
                        name,
                        parameters=json_bytes(value.parameters),
                        choices=json_bytes(value.choices),
                        selected_dependencies=value.selected_dependencies,
                    )
                    for name, value in selections.items()
                ),
                discovery=relations,
                source_sets=(
                    FrozenSourceSet.from_selected(
                        "selected-source-views", (self.source_row["_selected_entry"],)
                    ),
                    *analytical_sources,
                ),
                original_sources=(original.selection(),),
                inference="controlled-pdf-records-v1",
                execution_profile=self.kernel.recipe.execution_profile,
            )
            return DemandPlanner(self.kernel.model, DataOperationStorage(connection)).register(
                intent,
                project=self.factory.project_id,
                release=self.kernel.prepared.release_id,
                runtime=self.kernel.runtime,
            )["demand_id"]

    def advance(self, demand, *, policy=None):
        from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

        result = execute_data_demand(
            self.factory.writer,
            demand,
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=self.factory.admitter,
            project_id=self.factory.project_id,
            database_capacity=6,
            policy=policy or CharacterizationExecutionPolicy(workers=1, max_submissions=1),
        )
        with self.reader.begin() as connection:
            snapshot = read_data_demand(connection, demand, view="products", max_bytes=64 * 1024**2)
        return result, snapshot

    def run(self, target, *, profile=None, products=(), active=()):
        demand = self.register(target, profile=profile, products=products, active=active)
        result, snapshot = self.advance(demand)
        return demand, result, snapshot

    def query(self, demand, **selection):
        selection.setdefault("max_bytes", 64 * 1024**2)
        with self.reader.begin() as connection:
            return serve_demand_query(
                connection,
                DemandQueryRequest(
                    project_id=self.factory.project_id,
                    demand_id=demand,
                    **selection,
                ),
            )

    def inspect(self, demand, **selection):
        from corpus_structure.serve.characterization import (
            DemandCharacterizationRequest,
            inspect_demand_characterization,
        )

        with self.reader.begin() as connection:
            return inspect_demand_characterization(
                connection,
                DemandCharacterizationRequest(
                    project_id=self.factory.project_id,
                    demand_id=demand,
                    **selection,
                ),
            )


def operation_use(snapshot, operation):
    obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
    (use,) = [
        row
        for row in snapshot["uses"]
        if obligations[row["obligation_id"]]["operation_id"] == operation
    ]
    return use


def operation_product(snapshot, operation):
    use = operation_use(snapshot, operation)
    products = use["products"]
    obligations = {row["obligation_id"]: row["operation_id"] for row in snapshot["obligations"]}
    producers = [
        (obligations[row["obligation_id"]], row["fate"], len(row["products"]))
        for row in snapshot["uses"]
    ]
    assert len(products) == 1, (
        f"{operation}: expected one product, observed {len(products)}; "
        f"fate={use.get('fate')}; continuation={snapshot.get('continuation') is not None}; "
        f"reasons={use['selection'].get('reasons', [])!r:.1500}; producers={producers}"
    )
    return products[0]


@pytest.fixture
def characterization_source(
    current_characterization_recipe,
    commit_db_engine,
    commit_writer_engine,
    commit_reader_engine,
    commit_admitter_engine,
    tmp_path,
    request,
):
    from docling_core.types.doc import DoclingDocument
    from pdf_controlled_support import ControlledPdfContent, controlled_pdf_converter

    from corpus_structure.ingest.pdf_health import FormulaOutcome
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
    from corpus_structure.semantic.product_reference import ProductReference

    factory = _private_build_factory(
        commit_db_engine,
        commit_writer_engine,
        tmp_path,
        request,
        admission_engine=commit_admitter_engine,
        kernel_recipe=current_characterization_recipe,
        source_kind="characterization_pdf",
    )
    build = factory()
    unprojected = getattr(request, "param", None) == "unprojected-formula"
    publication = publish_selected(
        commit_writer_engine,
        build,
        tmp_path / "source",
        characterization_pages=True,
        unprojected_formula=unprojected,
    )
    factory.complete(build, publication)
    # Later native demands may acquire another capture under their own exact
    # support. Keep the converter controlled for the complete fixture lifetime,
    # using the same authored document and outcomes from its sealed publication.
    with commit_writer_engine.begin() as connection:
        reader = PublishedPdfReader(
            connection,
            ProductReference(
                publication.task_id, publication.product_key, publication.logical_digest
            ),
            projection_context=factory.kernel.prepared,
            read_budget=PublishedReadBudget(1000, 8 * 1024**2),
        )
        content = ControlledPdfContent.from_document(
            DoclingDocument.model_validate(reader.reconstruct_document()),
            formula_outcomes=tuple(
                FormulaOutcome(item["pointer"], item["outcome"])
                for item in reader.native_metadata("formula_outcomes")
            ),
        )
    section = "Unprojected formula section" if unprojected else "Nested selected section"
    with controlled_pdf_converter(content):
        (source,) = factory.selected_sources(build, sections=(section,))
        yield CurrentCharacterization(factory, build, publication, source, commit_reader_engine)
