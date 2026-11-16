"""Retained original-source premises beside an admitted current target kernel."""

from dataclasses import dataclass
from io import BytesIO
from hashlib import sha256
from typing import Any

from scenario_recipes import register_scenario_builder

from corpus_structure.core.evidence import document_key

from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
from corpus_structure.semantic.original_documents import (
    OriginalDocumentAcquisition,
    acquire_original_document_selection,
    read_original_document_bytes,
    register_original_document,
)
from semantic.data_operation_kernel_support import (
    Kernel,
    KernelRecipe,
    KernelSeedStage,
    admit_kernel,
    prepare_kernel,
)

PROJECT = "current-original-source"


@dataclass(frozen=True)
class OriginalSeedRecipe:
    target: KernelRecipe


@dataclass(frozen=True)
class OriginalSeedStage:
    original: OriginalDocumentAcquisition
    kernel: KernelSeedStage

    @property
    def seed_files(self):
        # The current read contract consumes retained native bytes, never the
        # registration path. Only the kernel's acquired files remain read inputs.
        return self.kernel.seed_files

    def validate_clone(self, admin):
        self.kernel.validate_clone(admin)
        with admin.connect() as connection:
            selected = acquire_original_document_selection(
                connection,
                project_id=self.original.reference.project_id,
                document_key=self.original.reference.document_key,
            )
            if selected != self.original:
                raise ValueError("original seed descriptor differs from its exact admission")
            read_original_document_bytes(
                connection, selected.reference, prepared=self.kernel.preparation.prepared
            )


@dataclass(frozen=True)
class OriginalSourceCase:
    original: OriginalDocumentAcquisition
    kernel: Kernel
    clone: Any

    @property
    def admin(self):
        return self.clone.admin

    @property
    def writer(self):
        return self.clone.writer


def build_original_seed(recipe, admin, writer, directory, *, purpose_engine=None):
    import pypdfium2 as pdfium

    if recipe.target.project_id is not None:
        raise ValueError("original seed initialization owns its explicit source project")
    kernel_directory = directory / "kernel"
    kernel_directory.mkdir()
    preparation = prepare_kernel(recipe.target, directory=kernel_directory)
    with admin.begin() as connection:
        admitted = admit_kernel(connection, recipe.target, engine=admin, preparation=preparation)

    document = pdfium.PdfDocument.new()
    page = document.new_page(200, 300)
    page.close()
    output = BytesIO()
    document.save(output)
    document.close()
    original = output.getvalue()
    path = directory / "independent-original.pdf"
    path.write_bytes(original)
    with writer.begin() as connection:
        DataOperationStorage(connection).initialize_source_project(
            {"project_id": ProjectId(PROJECT), "release_id": ReleaseId(preparation.prepared.release_id)}
        )
        register_original_document(
            connection,
            prepared=preparation.prepared,
            project_id=PROJECT,
            source_uri="independent-original.pdf",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        selected = acquire_original_document_selection(
            connection,
            project_id=PROJECT,
            document_key=document_key(PROJECT, "independent-original.pdf", sha256(original).hexdigest()),
        )
        if read_original_document_bytes(connection, selected.reference, prepared=preparation.prepared) != original:
            raise ValueError("original seed retained bytes differ from the registered source")
    return OriginalSeedStage(
        selected, KernelSeedStage(preparation, admitted.identities, recipe.target)
    )


register_scenario_builder(OriginalSeedRecipe, build_original_seed)


def original_source_clone(request, scenario_seeds):
    recipe = getattr(request, "param", None)
    if not isinstance(recipe, OriginalSeedRecipe):
        raise TypeError("ddo_original_source requires an explicit OriginalSeedRecipe")
    with scenario_seeds.commit_clone(recipe) as clone:
        stage = clone.stage
        if not isinstance(stage, OriginalSeedStage):
            raise TypeError("original recipe produced a different stage")
        kernel = Kernel(
            clone.admin, stage.kernel.preparation, stage.kernel.identities, recipe.target, clone
        )
        yield OriginalSourceCase(stage.original, kernel, clone)
