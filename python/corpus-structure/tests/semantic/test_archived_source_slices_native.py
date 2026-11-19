"""T15 selects source sections from a persisted release after local inputs disappear."""

import json
from dataclasses import replace

from corpus_structure.orchestrate.source_operation import prepare_source_demand
from corpus_structure.orchestrate.source_request import SourceRunRequest
from corpus_structure.semantic.data_operation_admission import admit_data_operation_release
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
from corpus_structure.semantic.original_documents import register_original_document
from corpus_structure.semantic.releases import open_release_inputs, persist_release
from corpus_structure.semantic.source_pack_inputs import PACK_BINDINGS, source_slices
from corpus_structure.semantic.types import SourceArtifact


def test_native_archive_keeps_source_scope_after_working_pack_is_removed(
    tmp_path, commit_admitter_engine, commit_writer_engine, commit_reader_engine
):
    from semantic.data_operation_kernel_support import prepare_kernel
    from semantic.rich_domain_native_support import toy_recipe

    recipe = toy_recipe(tmp_path)
    captured = recipe.captured_inputs
    assert captured is not None
    pack = tmp_path / "operator-pack"
    pack.mkdir()
    path = pack / "slices.yaml"
    path.write_text(
        "default_scope: selected\nslices: {selected: [{native_sections: [Archived section]}]}\n"
    )
    dependencies = replace(
        captured.dependencies,
        artifacts=(
            *(
                a
                for a in captured.dependencies.artifacts
                if a.name not in {PACK_BINDINGS, "operation/slices.yaml"}
            ),
            SourceArtifact("operation/slices.yaml", path.read_bytes()),
            SourceArtifact(
                PACK_BINDINGS,
                json.dumps(
                    [dict(name="operator-pack", module=captured.bundle.root, prefix="")]
                ).encode(),
            ),
        ),
    )
    candidate = prepare_kernel(
        replace(recipe, captured_inputs=replace(captured, dependencies=dependencies))
    )
    project_id = "archived-source-scope:" + tmp_path.name
    original = tmp_path / "original.pdf"
    original.write_bytes(b"%PDF-1.7\nretained source scope selection\n")
    with commit_admitter_engine.begin() as connection:
        persist_release(
            connection,
            candidate.bundle,
            candidate.dependencies,
            candidate.profile,
            candidate.prepared,
        )
        admit_data_operation_release(connection, candidate.prepared)
    with commit_writer_engine.begin() as connection:
        DataOperationStorage(connection).initialize_source_project(
            {
                "project_id": ProjectId(project_id),
                "release_id": ReleaseId(candidate.prepared.release_id),
            }
        )
        register_original_document(
            connection,
            prepared=candidate.prepared,
            project_id=project_id,
            source_uri="original.pdf",
            original_path=str(original),
            original=original.read_bytes(),
            mime="application/pdf",
        )
    path.write_text("default_scope: altered\nslices: {altered: [{native_sections: [Changed]}]}\n")
    path.unlink()
    pack.rmdir()
    with commit_reader_engine.begin() as connection:
        dependencies = open_release_inputs(connection, candidate.prepared.release_id)[1]
        scopes = source_slices(dependencies, "operator-pack")
        request = prepare_source_demand(
            connection,
            SourceRunRequest(
                project_id=project_id,
                release_id=candidate.prepared.release_id,
                runtime_id="runtime:scope-selection",
                domain="operator-pack",
                workflow="capture",
                targets=("source.pdf_views/discovery",),
            ),
        )
    assert scopes["default_scope"] == "selected"
    producer = next(
        value for value in request.selections if value.operation == "source.pdf_views/discovery"
    )
    assert producer.parameters == {"sections": ["Archived section"], "membership": "descendants"}
