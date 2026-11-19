"""Exercise the exact reviewed statistical release on a private registered kernel."""

import os
from pathlib import Path

from corpus_structure.cli.managed import ResultStore
from corpus_structure.cli.model import _load_artifact, _read_runtime
from corpus_structure.schema.model_deployment import Candidate
from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
    inspect_data_operation_release,
)
from corpus_structure.semantic.data_operation_service import acquire_data_execution_basis
from corpus_structure.semantic.execution_admission import verify_native_execution_release
from corpus_structure.semantic.inspection_capsule import open_capsule_inputs
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.releases import persist_release, verify_release
from corpus_structure.semantic.runtime_binding_store import (
    persist_runtime_binding,
    runtime_binding_for_release,
)
from corpus_structure.semantic.storage_target import acquired_target


def test_exact_statistical_candidate_admits_under_registered_native_programs(
    commit_db_engine, commit_admitter_engine, commit_reader_engine
):
    candidate_id = os.environ["UDM_PRIVATE_CANDIDATE"]
    store = ResultStore(Path("build/ci"))
    with store.lease(candidate_id):
        binding = Candidate.model_validate_json(
            _load_artifact(store, candidate_id, "model.candidate", "deployment")
        )
        assert binding.revision and binding.release
        assert binding.inspection_sha256 and binding.release_manifest_sha256
        assert binding.release_artifacts_sha256
        bundle, deps, profile, prepared = open_capsule_inputs(
            store.read_artifact(candidate_id, "inspection"),
            digest=binding.inspection_sha256,
            release_id=binding.release,
            manifest_digest=binding.release_manifest_sha256,
            artifacts_digest=binding.release_artifacts_sha256,
        )
        runtime = _read_runtime(store, candidate_id, binding.runtime, prepared)
        assert runtime is not None
    with commit_db_engine.connect() as connection:
        actual = acquired_target(connection, purpose="maintenance")
        assert binding.target_identity is not None
        assert actual.database_oid != binding.target_identity.database_oid
        assert current_revision(connection) == binding.revision
    with commit_admitter_engine.begin() as connection:
        assert persist_release(connection, bundle, deps, profile, prepared) == binding.release
    assert (
        binding.preparation_request is not None and not binding.preparation_request.effect_approvals
    )
    with commit_admitter_engine.begin() as connection:
        admit_data_operation_release(connection, prepared)
        persist_runtime_binding(connection, prepared, runtime)
        assert verify_release(connection, prepared.release_id).release_id == prepared.release_id
        assert verify_native_execution_release(connection, prepared.release_id)
    with commit_reader_engine.begin() as connection:
        inspect_data_operation_release(connection, prepared)
        assert runtime_binding_for_release(connection, prepared, runtime.runtime_id) == runtime
        execution = acquire_data_execution_basis(
            connection,
            prepared.release_id,
            runtime.runtime_id,
            source_root=Path("python/corpus-structure/src"),
        )
        assert execution.runtime_locations
        for source in execution.sources.sources:
            assert execution.runtime_locations[source.module].read_bytes() == source.content
        assert any(asset.runtime_transport for asset in execution.sources.boundary_contracts)
