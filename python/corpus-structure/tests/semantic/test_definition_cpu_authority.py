"""Exact input/dispatch wrappers; controlled projections establish no scientific evidence."""

import inspect
import json
from copy import deepcopy
from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_cpu_basis import (
    cpu_authority_value,
    cpu_input_basis_from_roles,
)
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.identity import canonical_bytes
from semantic.test_contextual_workflow_preparation import prepared_workflow as prepared_workflow


def selected_roles(names, *, sequences=()):
    context = SubjectContext(
        "unadmitted:project",
        "unadmitted:source",
        "unadmitted:document",
        b"{}",
        subject_definition="original-source-view",
    )
    roles, bodies = [], {}
    for name in names:
        members, values = [], []
        for position in range(2 if name in sequences else 1):
            support = (
                ComputationalSupportReference(derivation_id=f"unadmitted:{name}:{position}"),
            )
            members.append(
                BoundRoleMember(
                    f"unadmitted:{name}:{position}",
                    "unadmitted:kind",
                    context.subject,
                    context.original_source,
                    context.analyzed_scope,
                    b"{}",
                    tuple(row.derivation_id for row in support),
                    b"{}",
                    position=position,
                    subject_definition=context.subject_definition,
                    support_references=support,
                )
            )
            values.append(dict(role=name, position=position))
        roles.append(ResolvedRoleBinding(name, "present", tuple(members)))
        bodies[name] = tuple(values)
    return context, tuple(roles), bodies


@pytest.mark.parametrize("variant", ["declaration", "applicability", "learned", "named"])
def test_definition_wrappers_bind_actual_values_parameters_and_support_before_dispatch(
    monkeypatch, variant, prepared_workflow
):
    from corpus_structure.methods import definition_applicability_declared
    from corpus_structure.semantic import definition_applicability_products as applicability
    from corpus_structure.semantic import definition_component_products as components
    from corpus_structure.semantic import definition_products as declaration

    sequences = ("syntax", "hanlp") if variant == "declaration" else ()
    names = {
        "declaration": ("source", "syntax", "hanlp"),
        "applicability": ("source", "components", "relationship"),
        "learned": ("source", "observation", "candidates"),
        "named": ("source", "annotations", "constructions"),
    }[variant]
    context, roles, bodies = selected_roles(names, sequences=sequences)
    arguments = {
        name: list(values) if name in sequences else values[0] for name, values in bodies.items()
    }
    parameters = (
        dict(
            start=0,
            end=1,
            passage_id="controlled",
            scope="selected",
            effective_version="",
            parent="",
        )
        if variant == "declaration"
        else (
            dict(
                component_id="controlled",
                decision_id="controlled",
                edge_id="controlled",
                usage_id="controlled",
                start=0,
                end=1,
                scope="selected",
                effective_version="",
                parent="",
                defining_occurrence=False,
            )
            if variant == "applicability"
            else {}
        )
    )
    arguments.update(parameters)
    basis = cpu_input_basis_from_roles(
        "unadmitted:definition-control",
        context,
        roles,
        bodies,
        parameters=canonical_bytes(semantic_value(parameters)),
        replicate="actual-logical-selection",
    )
    observed = []

    def project(*args, **kwargs):
        observed.append(True)
        return {"controlled_projection": "private", "source": deepcopy(arguments["source"])}

    if variant == "declaration":
        monkeypatch.setattr(declaration.PreparedDefinitionInputs, "declaration", project)
        kernel = declaration.definition_kernel
    elif variant == "applicability":
        monkeypatch.setattr(
            definition_applicability_declared, "execute_definition_applicability", project
        )
        kernel = applicability.applicability_kernel
    else:
        monkeypatch.setattr(
            components,
            "project_named_definition_components"
            if variant == "named"
            else "project_definition_components",
            project,
        )
        kernel = (
            components.named_definition_components_kernel
            if variant == "named"
            else components.definition_components_kernel
        )
    # Use the real prepared-kernel packet encoder and child ingress. Direct
    # Python calls cannot detect erased role/context types at the JSON boundary.
    from corpus_structure.semantic.data_operation_cpu import (
        PythonCPUDescriptor,
        execute_python_call,
    )

    sources = (
        declaration.definition_operation_sources()
        if variant == "declaration"
        else applicability.applicability_operation_sources()
        if variant == "applicability"
        else components.definition_component_operation_sources(include_learned=variant == "learned")
    )
    descriptor = PythonCPUDescriptor(
        tuple((source.module, source.filename, source.content) for source in sources.sources),
        kernel.__module__ + "." + kernel.__qualname__,
        (), verification="prepared-kernel", control_parameter="check_active",
        prepared_parameter="prepared", prepared_release_id=prepared_workflow.release_id,
    )
    signature = inspect.signature(kernel, eval_str=True)

    def invoke(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        return json.loads(execute_python_call(
            descriptor.packet(bound.arguments, signature), lambda: None,
            prepared_releases={prepared_workflow.release_id: prepared_workflow},
        ))

    reply = invoke(
        arguments, roles, context, basis, prepared=prepared_workflow, check_active=lambda: None
    )
    actual = cpu_authority_value(canonical_bytes(reply), expected_basis=basis)
    assert actual == {"controlled_projection": "private", "source": bodies["source"][0]}
    assert observed == [True]
    changed = deepcopy(arguments)
    source_body = changed["source"]
    assert isinstance(source_body, dict)
    source_body["position"] = 99
    with pytest.raises(ValueError, match="exact input basis"):
        invoke(
            changed, roles, context, basis, prepared=prepared_workflow, check_active=lambda: None
        )
    altered_role = replace(
        roles[0],
        members=(
            replace(
                roles[0].members[0],
                support_episodes=("unadmitted:other-producer",),
                support_references=(
                    ComputationalSupportReference(derivation_id="unadmitted:other-producer"),
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="exact input basis"):
        invoke(
            arguments,
            (altered_role, *roles[1:]),
            context,
            basis,
            prepared=prepared_workflow,
            check_active=lambda: None,
        )
    if parameters:
        changed = dict(arguments, start=1)
        with pytest.raises(ValueError, match="exact input basis"):
            invoke(
                changed,
                roles,
                context,
                basis,
                prepared=prepared_workflow,
                check_active=lambda: None,
            )
    assert observed == [True]
