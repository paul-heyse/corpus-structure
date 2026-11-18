"""Reviewed deployment retains actual runtime bytes and explicit logical selection."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest
from model_change_support import model_checkout as model_checkout
from pydantic import ValidationError
from semantic.data_operation_kernel_support import STORAGE, prepare_kernel

from corpus_structure.cli import model as commands
from corpus_structure.cli.managed import ResultStore
from corpus_structure.schema.declarations import ModelError
from corpus_structure.schema.model_change import ChangeRequest, RuntimeCustody, prepare_preview
from corpus_structure.schema.model_deployment import Candidate
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime


@pytest.mark.parametrize("intent", [{"deployment": True}, {"native_revision": "next"}])
def test_application_intent_requires_explicit_logical_profile(intent):
    with pytest.raises(ValidationError, match="explicit execution_profile"):
        ChangeRequest(data_operations="target.yaml", **intent)
    with pytest.raises(ValidationError, match="explicit execution_profile"):
        ChangeRequest(data_operations="target.yaml", execution_profile=" ", **intent)
    selected = ChangeRequest(
        data_operations="target.yaml", execution_profile="execution:cpu", **intent
    )
    assert selected.execution_profile == "execution:cpu"


@pytest.mark.parametrize("intent", [{}, {"deployment": True}, {"native_revision": "next"}])
def test_non_application_intent_carries_no_runtime_claim(intent):
    assert ChangeRequest(**intent).execution_profile is None
    with pytest.raises(ValidationError, match="actual DDO application deployment"):
        ChangeRequest(execution_profile="execution:cpu", **intent)
    # An archival comparison is not an executable deployment.
    assert ChangeRequest(data_operations="target.yaml").execution_profile is None


def test_application_candidate_uses_retained_runtime_not_ambient_repreparation(model_checkout):
    root, _ = model_checkout
    prepared = prepare_kernel(STORAGE)
    (root / "schema.yaml").write_text(STORAGE.schema_text)
    assert STORAGE.declaration_content is not None
    (root / "operations.yaml").write_bytes(STORAGE.declaration_content)
    (root / "target.yaml").write_text(STORAGE.manifest_text)
    binding = prepare_data_operation_runtime(
        prepared.prepared,
        prepared.dependencies.artifacts,
        execution_profile="execution:cpu",
        observed={},
    )
    custody = RuntimeCustody.from_binding(binding)
    assert json.loads(binding.manifest)["observed"] == {}
    request = ChangeRequest(
        deployment=True, data_operations="target.yaml", execution_profile="execution:cpu"
    )
    preview = prepare_preview(
        root,
        request,
        target="target",
        local_release=prepared.prepared.release_id,
        release_manifest_sha256=sha256(prepared.prepared.manifest).hexdigest(),
        release_artifacts_sha256=prepared.prepared.artifacts_sha256,
    )
    with pytest.raises(ModelError, match="lacks exact reviewed runtime custody"):
        Candidate.from_preview(preview, None, prepared.prepared, {})
    preview = preview.model_copy(update={"runtime": custody})
    candidate = Candidate.from_preview(preview, None, prepared.prepared, {}, runtime=binding)
    assert candidate.runtime == custody
    store = ResultStore(root / "results")
    with store.operation("model.preview") as result:
        commands._publish_runtime(result, binding)
        result.settle()
    with store.lease(result.id):
        retained = commands._read_runtime(store, result.id, custody, prepared.prepared)
    assert retained == binding
    # A newly selected profile is a different runtime, even with identical inputs.
    another = prepare_data_operation_runtime(
        prepared.prepared,
        prepared.dependencies.artifacts,
        execution_profile="execution:other",
        observed={},
    )
    assert another.runtime_id != binding.runtime_id
    with pytest.raises(ModelError, match="exact reviewed custody"):
        Candidate.from_preview(preview, None, prepared.prepared, {}, runtime=another)
    with pytest.raises(ModelError, match="execution profile differs"):
        custody.model_copy(update={"execution_profile": "execution:other"}).verify(
            binding, prepared.prepared
        )
    for changed in (
        replace(binding, archive=binding.archive + b" "),
        replace(binding, manifest=binding.manifest + b" "),
        replace(binding, release_id="another"),
    ):
        with pytest.raises(ModelError, match="exact reviewed custody"):
            custody.verify(changed, prepared.prepared)
    with pytest.raises(ModelError, match="lack reviewed custody"):
        commands._read_runtime(store, result.id, None, prepared.prepared)

    store.artifact(result.id, "runtime_archive").write_bytes(binding.archive + b" ")
    with pytest.raises(ModelError, match="exact reviewed custody"):
        commands._read_runtime(store, result.id, custody, prepared.prepared)
