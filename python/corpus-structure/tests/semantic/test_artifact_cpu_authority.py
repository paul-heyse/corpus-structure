"""Current source capture and exact consumed-input wrapper, without native standing."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from pglast import ast

from corpus_structure.semantic.artifact_admission_native import artifact_admission_native_sql
from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_roles
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.current_artifact_support import ARTIFACT, artifact_recipe
from semantic.data_operation_kernel_support import prepare_kernel
from semantic.test_definition_cpu_authority import selected_roles


@pytest.fixture(scope="module")
def artifact_preparation(tmp_path_factory):
    return prepare_kernel(artifact_recipe(tmp_path_factory.mktemp("artifact-current-source")))


@pytest.fixture(scope="module")
def artifact_schema():
    from corpus_structure.semantic.artifact_products import artifact_inputs
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    # An explicitly empty current operation graph supplies real immutable DTOs,
    # with no operation admission or provider assertion at this unit boundary.
    return prepare_release(artifact_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))),
        data_operation_dependencies(ResolvedDependencies(), (structural_operation_declarations(),)),
        PreparationProfile(version="semantic-2"))


def test_actual_artifact_profile_has_complete_current_inputs_and_scalar_factory(artifact_preparation):
    operation = artifact_preparation.model.operation(ARTIFACT)
    assert operation.capabilities.forms == ("scalar",)
    assert {role.name for role in operation.roles if role.direction == "input"} == {"sources", "constructions", "nominations"}
    inputs = tuple(role for role in operation.roles if role.direction == "input")
    assert all(role.support is not None for role in inputs)
    assert {role.support.source_set for role in inputs if role.support is not None} == {
        "artifact-sources", "artifact-constructions", "artifact-nominations"}
    assert operation.result_fields == ()
    assert artifact_preparation.model.operation("text.constructions/source-native").recipe


def test_artifact_native_helper_declares_exact_private_completion_and_validity_signatures():
    sql = prepare_sql(artifact_admission_native_sql(), source="artifact-body-authority")
    names = set()
    for statement in sql.statements:
        if isinstance(statement.stmt, ast.CreateFunctionStmt):
            assert statement.stmt.funcname
            names.add(statement.stmt.funcname[-1].sval)
    assert names == {
            "ddo_require_artifact_producer", "ddo_require_artifact_completion", "ddo_artifact_dependencies_valid"}


def test_artifact_wrapper_binds_complete_role_values_support_and_typed_policy(monkeypatch, artifact_schema):
    from corpus_structure.methods import artifact_identity_declared
    from corpus_structure.semantic.artifact_products import artifact_kernel

    context, roles, bodies = selected_roles(("sources", "constructions", "nominations"))
    parameters = dict(selections=[], nomination_selections=[], policy=dict(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05),
        title_threshold=70.5, exclusions=[], known_anchor_ids=[])
    arguments: dict[str, Any] = {name: list(values) for name, values in bodies.items()} | parameters
    basis = cpu_input_basis_from_roles("unadmitted:artifact-wrapper-control", context, roles, bodies,
        parameters=canonical_bytes(semantic_value(parameters)), replicate="exact-cohort")
    observed = []

    def project(*args, **kwargs):
        observed.append(True)
        return dict(policy=deepcopy(kwargs["policy"]), controlled_projection="private")

    monkeypatch.setattr(artifact_identity_declared, "execute_artifact_identity", project)
    reply = artifact_kernel(arguments, roles, context, basis, prepared=artifact_schema, check_active=lambda: None)
    assert cpu_authority_value(canonical_bytes(reply), expected_basis=basis) == dict(policy=parameters["policy"], controlled_projection="private")
    assert observed == [True]
    changed = deepcopy(arguments)
    changed["policy"]["prior"] = 0.2
    with pytest.raises(ValueError, match="exact input basis"):
        artifact_kernel(changed, roles, context, basis, prepared=artifact_schema, check_active=lambda: None)
    changed = deepcopy(arguments)
    changed["sources"][0]["position"] = 99
    with pytest.raises(ValueError, match="exact input basis"):
        artifact_kernel(changed, roles, context, basis, prepared=artifact_schema, check_active=lambda: None)
    altered = replace(roles[0], members=(replace(roles[0].members[0], support_references=(), support_episodes=()),))
    with pytest.raises(ValueError, match="exact input basis"):
        artifact_kernel(arguments, (altered, *roles[1:]), context, basis, prepared=artifact_schema, check_active=lambda: None)
    assert observed == [True]
