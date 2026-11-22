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
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.selected_support import ProducerOutputOccurrence
from semantic.test_contextual_workflow_preparation import prepared_workflow as prepared_workflow


@pytest.fixture(autouse=True)
def fresh_authority_worker(monkeypatch):
    from corpus_structure.semantic.data_operation_cpu import _load_descriptor

    # These in-process ingress controls stand in for distinct worker lifetimes.
    # Restore no acquired runtime across tests that install different projectors;
    # within each case the original authenticated descriptor cache remains active.
    # Depending on monkeypatch keeps this cleanup inside its fixture lifetime.
    _load_descriptor.cache_clear()
    yield
    _load_descriptor.cache_clear()


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
                    producer_output=ProducerOutputOccurrence(
                        member_id=None, role=f"emitted:{name}", position=position, multiplicity=1
                    ),
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

    sequences = ("syntax",) if variant == "declaration" else ()
    names = {
        "declaration": ("source", "syntax"),
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
    if variant == "named":
        arguments["annotations"] = {"header": arguments["annotations"], "partitions": []}
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
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
        prepared_parameter="prepared",
        prepared_release_id=prepared_workflow.release_id,
    )
    signature = inspect.signature(kernel, eval_str=True)

    def invoke(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        return json.loads(
            execute_python_call(
                descriptor.packet(bound.arguments, signature),
                lambda: None,
                prepared_releases={prepared_workflow.release_id: prepared_workflow},
            )
        )

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
    emitted = roles[0].members[0].producer_output
    assert emitted is not None
    altered_output = replace(
        roles[0],
        members=(
            replace(
                roles[0].members[0],
                producer_output=emitted.model_copy(update={"position": emitted.position + 1}),
            ),
        ),
    )
    with pytest.raises(ValueError, match="exact input basis"):
        invoke(
            arguments,
            (altered_output, *roles[1:]),
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


@pytest.mark.parametrize("variant", ["named", "learned"])
def test_component_cpu_retains_selected_source_member_and_requires_whole_primary_reports(
    prepared_workflow, monkeypatch, variant
):
    """Unadmitted source/empty-primary boundary, not provider or native evidence."""
    from corpus_structure.semantic import definition_component_products as components
    from corpus_structure.semantic.data_operation_cpu import (
        PythonCPUDescriptor,
        execute_python_call,
    )
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from semantic.test_contextual_workflow_preparation import unadmitted_frame

    frame, context = unadmitted_frame("12 means 12.")
    source = json.loads(frame.source_content)
    names = (
        ("annotations", "constructions") if variant == "named" else ("observation", "candidates")
    )
    _, raw_roles, _ = selected_roles(("source", *names))
    roles = tuple(
        replace(
            role,
            members=(
                replace(
                    role.members[0],
                    subject=context.subject,
                    original_source=context.original_source,
                    analyzed_scope=context.analyzed_scope,
                    subject_definition=context.subject_definition,
                    member="unadmitted:selected-source-view" if role.role == "source" else None,
                ),
            ),
        )
        for role in raw_roles
    )
    if variant == "named":
        from corpus_structure.semantic.producer_requirements import SelectedProducerContract
        from corpus_structure.semantic.reference_resolution import ProducingReferenceInput

        annotation = next(role.members[0] for role in roles if role.role == "annotations")
        construction = next(role.members[0] for role in roles if role.role == "constructions")
        # This unadmitted CPU control supplies the original role mapping explicitly;
        # false receipt fields confer no native publication or provider authority.
        contract = SelectedProducerContract(
            version="selected-producer-contract-v1",
            derivation_id=construction.support_episodes[0],
            release_id="unadmitted:release",
            runtime_id="unadmitted:runtime",
            publication_receipt=False,
            cpu_receipt=False,
            admitted_effects=(),
            validity_families=(),
            reference_inputs=(
                ProducingReferenceInput("sentences", annotation.product, annotation.kind_contract),
            ),
            reference_inputs_complete=True,
        )
        roles = tuple(
            replace(
                role,
                members=(
                    replace(
                        role.members[0],
                        support_evidence=canonical_bytes(
                            {"producer_contract": contract.model_dump(mode="json")}
                        ),
                    ),
                ),
            )
            if role.role == "constructions"
            else role
            for role in roles
        )
    # An explicitly empty, unadmitted primary inventory reaches the real domain
    # refusal after source custody. It cannot stand in for learned annotations.
    primary = {"source": source["source"], "selectors": source["selectors"], "blocks": []}
    if variant == "named":
        from corpus_structure.semantic.data_operation_partitions import partition_header

        header = {**primary, "rows": partition_header(()), "block_layouts": []}
        arguments = dict(
            source=source, annotations={"header": header, "partitions": []}, constructions=primary
        )
    else:
        from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource
        from corpus_structure.semantic.source_products import FrozenNativeSource

        pin = DeclaredRecordSource.from_bound(
            FrozenNativeSource.acquire(prepared_workflow, source),
            roles[0].members[0],
            project=context.project_id,
        ).pin()
        arguments = dict(
            source=source,
            observation=dict(source_pin=pin, outcome="partial", observations=[]),
            candidates=dict(source_pin=pin, members=[], operations=[]),
        )
    acquired = []
    original = DeclaredNativeFrameSource.acquire

    def observe_source(*args, **kwargs):
        result = original(*args, **kwargs)
        acquired.append(result.pin.values())
        return result

    monkeypatch.setattr(DeclaredNativeFrameSource, "acquire", observe_source)
    kernel = (
        components.named_definition_components_kernel
        if variant == "named"
        else components.definition_components_kernel
    )
    sources = components.definition_component_operation_sources(
        include_learned=variant == "learned"
    )
    descriptor = PythonCPUDescriptor(
        tuple((item.module, item.filename, item.content) for item in sources.sources),
        kernel.__module__ + "." + kernel.__qualname__,
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
        prepared_parameter="prepared",
        prepared_release_id=prepared_workflow.release_id,
    )
    signature = inspect.signature(kernel, eval_str=True)

    def invoke(selected_roles):
        basis = cpu_input_basis_from_roles(
            "unadmitted:named-source-boundary",
            context,
            selected_roles,
            {
                name: (body["header"] if name == "annotations" else body,)
                for name, body in arguments.items()
            },
            parameters=canonical_bytes(semantic_value({})),
            replicate=None,
        )
        bound = signature.bind(
            arguments=arguments,
            roles=selected_roles,
            context=context,
            input_basis=basis,
            prepared=prepared_workflow,
            check_active=lambda: None,
        )
        raw = execute_python_call(
            descriptor.packet(bound.arguments, signature),
            lambda: None,
            prepared_releases={prepared_workflow.release_id: prepared_workflow},
        )
        return cpu_authority_value(raw, expected_basis=basis)

    if variant == "named":
        with pytest.raises(ValueError, match="actual retained native source blocks"):
            invoke(roles)
    else:
        result = invoke(roles)
        assert [packet["body"] for packet in result["members"]] == []
        assert {stage["outcome"] for stage in result["definition_components"]["stages"]} == {
            "unavailable"
        }
        assert result["inputs"]["coverage_limits"]
        assert result["inputs"]["sources"][0]["source_member"] == "unadmitted:selected-source-view"
    assert acquired[0]["source_product"] == roles[0].members[0].product
    assert acquired[0]["source_member"] == "unadmitted:selected-source-view"
    assert acquired[0]["original_source"] == context.original_source
    assert (
        acquired[0]["source"]
        == canonical_bytes(
            [roles[0].members[0].product, "unadmitted:selected-source-view"]
        ).decode()
    )
    for name in names:
        changed = tuple(
            replace(role, members=(replace(role.members[0], member="unadmitted:primary-fragment"),))
            if role.role == name
            else role
            for role in roles
        )
        with pytest.raises(ValueError, match=r"exact whole (primary|retained) products"):
            invoke(changed)
    duplicated = (
        replace(roles[0], members=(replace(roles[0].members[0], multiplicity=2),)),
        *roles[1:],
    )
    with pytest.raises(ValueError, match=r"exact whole (primary|retained) products"):
        invoke(duplicated)
    foreign = (
        replace(
            roles[0],
            members=(replace(roles[0].members[0], original_source="unadmitted:foreign-original"),),
        ),
        *roles[1:],
    )
    with pytest.raises(ValueError, match="bound original document"):
        invoke(foreign)
