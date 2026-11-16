"""Real source identities at the unadmitted plan boundary; no CPU/native execution claim."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_ports import python_port_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection


@pytest.fixture(scope="module")
def actual_nominal_identity():
    path = Path(__file__).parents[2] / "src/corpus_structure/semantic/identity.py"
    sources = PythonSourceCollection((PythonSource(
        "corpus_structure.semantic.identity", path.read_bytes(), str(path)),))
    model = compile_data_operations(python_sources=sources)
    operation = model.operations[0]
    identity = python_port_identity(model, sources, operation.semantic_id)
    assert isinstance(operation.recipe, bytes)
    assert isinstance(identity.recipe, str) and identity.recipe.startswith("recipe:")
    return model, operation, identity


@pytest.mark.parametrize("variant", ("declaration", "applicability", "learned", "named", "artifact", "fixture"))
def test_cpu_plans_use_actual_nominal_recipe_identity(actual_nominal_identity, variant):
    from corpus_structure.semantic.artifact_products import ArtifactCallPlan
    from corpus_structure.semantic.definition_applicability_products import ApplicabilityCallPlan
    from corpus_structure.semantic.definition_component_products import (
        DefinitionComponentsCallPlan,
        definition_components_kernel,
        named_definition_components_kernel,
    )
    from corpus_structure.semantic.definition_products import DefinitionCallPlan
    from semantic.contextual_native_fixture import FixtureCallPlan, execute_cue_kernel

    model, operation, identity = actual_nominal_identity
    context = SubjectContext("unadmitted:project", "unadmitted:source", None, b"{}", subject_definition="source")
    input_role = next(role for role in operation.roles if role.direction == "input")
    member = BoundRoleMember(
        "unadmitted:product", input_role.kind, context.subject, None, b"{}", b"{}", (), b"{}",
        subject_definition=context.subject_definition, support_references=(),
    )
    binding = BindingResult(
        operation.semantic_id, context.subject, (ResolvedRoleBinding(input_role.name, "present", (member,)),),
        "ready", (), canonical_bytes(semantic_value({})), b"{}", model.version,
        identity.definition, identity.eligibility, (), subject_context=context, replicate=None,
    )

    # Dispatch is deliberately stopped before the CPU boundary. The generic real operation
    # supplies nominal recipe/role metadata, without pretending to be a domain producer.
    class Port:
        def __init__(self):
            self.identity = identity
            self.operation = operation

        def plan_cpu(self, kernel, bound, sources, **options):
            yield bound.arguments["input_basis"]

    port = Port()
    prepared = cast(Any, SimpleNamespace(release_id="unadmitted:release"))
    if variant == "declaration":
        plan = DefinitionCallPlan(prepared)
    elif variant == "applicability":
        plan = ApplicabilityCallPlan(prepared)
    elif variant in {"learned", "named"}:
        plan = DefinitionComponentsCallPlan(prepared, kernel=(
            definition_components_kernel if variant == "learned" else named_definition_components_kernel))
    elif variant == "artifact":
        plan = ArtifactCallPlan(prepared)
    else:
        plan = FixtureCallPlan(prepared, execute_cue_kernel)
    plan.port = port
    value = [7] if variant == "artifact" else 7
    arguments = SimpleNamespace(arguments={input_role.name: value})
    if variant == "fixture":
        # The finite fixture's role is explicitly named source.
        binding = binding.__replace__(roles=(binding.roles[0].__replace__(role="source"),))
        arguments = SimpleNamespace(arguments={"source": 7})
    execution = plan.plan(arguments, binding=binding, check_active=lambda: None, execution_owner=None)
    basis = decode_semantic_value(next(execution))
    assert basis["recipe"] == identity.recipe
    assert basis["roles"][0]["body"] == 7
    assert basis["context"] == context.identity_record
    execution.close()
