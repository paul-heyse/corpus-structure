"""Captured CPU preparation for current rich operations and native completion effects."""

import inspect
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .types import SourceArtifact

_ROOT = Path(__file__).parents[1]
_FILES = (
    "analytics.py",
    "semantic/input_values.py",
    "methods/rich_knowledge.py",
    "semantic/rich_invocations.py",
    "semantic/rich_consolidation.py",
    "semantic/rich_reading_admission.py",
    "semantic/rich_reading_inputs.py",
    "semantic/rich_cpu_inputs.py",
    "semantic/rich_graph_subset.py",
    "semantic/rich_knowledge.py",
    "semantic/rich_proposal_lowering.py",
    "semantic/data_operation_cpu_basis.py",
    "semantic/rich_identity_exclusions.py",
    "semantic/rich_knowledge_contracts.py",
    "semantic/rich_decisions.py",
    "semantic/rich_graph_validation.py",
    "semantic/rich_value_graph.py",
    "semantic/rich_fact_graph.py",
    "semantic/rich_policy_binding.py",
    "semantic/rich_rules.py",
    "semantic/rich_rule_evaluation.py",
    "semantic/rich_scientific.py",
    "semantic/rich_relations.py",
    "semantic/qualification_meaning.py",
    "semantic/rich_record_readings.py",
    "semantic/record_contracts.py",
    "semantic/record_policy_authority.py",
    "semantic/record_policy.py",
    "semantic/reading_resolution_products.py",
    "semantic/analytical_kernels.py",
    "semantic/value_codec.py",
    "semantic/reference_positions.py",
    "semantic/expression_context.py",
    "semantic/rich_proposals.py",
    "semantic/proposals.py",
    "semantic/property_constraints.py",
    "semantic/identity_resolution.py",
    "semantic/alias_policy.py",
    "semantic/unicode_identity.py",
    "semantic/rule_views.py",
    "semantic/scientific_evidence.py",
    "semantic/math_context.py",
    "semantic/statement_types.py",
)


def rich_knowledge_assets():
    from .python_module_projection import admitted_operation_module_meaning

    return SourceArtifact(
        "rich-knowledge/algorithm-assets",
        canonical_bytes(
            {
                "version": "rich-knowledge-computation-1",
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes())
                            if name == "methods/rich_knowledge.py"
                            else (_ROOT / name).read_bytes()
                        ).hex(),
                    )
                    for name in _FILES
                ],
            }
        ),
    )


def rich_knowledge_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in _FILES
        ),
        boundary_contracts=(rich_knowledge_assets(),),
    )


def execute_consolidation_profile(
    receiver, proposals, proposal_contexts, authored, records, readings, known_universe, policy
):
    return receiver.execute(
        proposals=proposals,
        proposal_contexts=proposal_contexts,
        authored=authored,
        records=records,
        readings=readings,
        known_universe=known_universe,
        policy=policy,
    )


def execute_admission_profile(receiver, consolidation, records, readings, policy_authorizations):
    return receiver.execute(
        consolidation=consolidation,
        records=records,
        readings=readings,
        policy_authorizations=policy_authorizations,
    )


def _checked_kernel_inputs(action, input_basis, asset_content, prepared):
    from .data_operation_admission import bound_data_operation_model
    from .data_operation_model import validate_subject_context
    from .rich_cpu_inputs import RichKernelInputs

    model = bound_data_operation_model(prepared)
    operation = model.operation(action)
    recipe = next(
        item.key for item in model.identities if item.domain == "recipe" and item.owner == action
    )
    inputs = RichKernelInputs.from_basis(input_basis)
    if inputs.recipe != recipe:
        raise ValueError("rich child basis differs from its actual admitted operation recipe")
    assets = [
        item for item in operation.assets if item.contract == "rich-knowledge/algorithm-assets"
    ]
    if len(assets) != 1 or sha256(asset_content.encode()).hexdigest() != assets[0].content_digest:
        raise ValueError("rich child algorithm assets differ from their actual admitted owner")
    validate_subject_context(model, inputs.context, subject_definition=operation.subject)
    declarations = {role.name: role for role in operation.roles if role.direction == "input"}
    if {role.role for role in inputs.roles} - declarations.keys():
        raise ValueError("rich child basis contains an undeclared input role")
    kinds = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    for name, declaration in declarations.items():
        rows = inputs.selected(name)
        if (
            len(rows) < declaration.minimum
            or (declaration.maximum is not None and len(rows) > declaration.maximum)
            or any(
                row.multiplicity != 1
                or row.member_id is not None
                or row.kind_contract != kinds[declaration.kind]
                for row in rows
            )
        ):
            raise ValueError("rich child basis differs from its actual whole input population")
        for row in rows:
            validate_subject_context(model, row.context)
            if row.context.project_id != inputs.context.project_id:
                raise ValueError("rich child role belongs to another actual project")
    return model, inputs


def execute_rich_consolidation_kernel(
    input_basis: list, asset_content: str, *, prepared, check_active
) -> dict:
    from .data_operation_cpu_basis import cpu_authority_reply
    from .rich_consolidation import consolidate_rich_knowledge

    model, inputs = _checked_kernel_inputs("rich.consolidate", input_basis, asset_content, prepared)
    result = consolidate_rich_knowledge(prepared, model, inputs=inputs, check_active=check_active)
    return cpu_authority_reply(inputs.basis(), result.model_dump(mode="python"))


def execute_rich_admission_kernel(
    input_basis: list, asset_content: str, *, prepared, check_active
) -> dict:
    from .data_operation_cpu_basis import cpu_authority_reply
    from .rich_consolidation import admit_rich_knowledge

    model, inputs = _checked_kernel_inputs("rich.admit", input_basis, asset_content, prepared)
    result = admit_rich_knowledge(prepared, model, inputs=inputs, check_active=check_active)
    return cpu_authority_reply(inputs.basis(), result.model_dump(mode="python"))


@dataclass
class RichInvocationPlan:
    prepared: Any
    asset_content: str
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_cpu_basis import cpu_input_basis_from_binding
        from .data_operation_ports import PortRefusal

        check_active()
        if binding is None or not binding.sufficient or binding.subject_context is None:
            raise PortRefusal("rich computation requires its sufficient exact native binding")
        if binding.subject_context.original_source is not None:
            raise PortRefusal(
                "rich knowledge requires its actual source-free checked project subject"
            )
        operation = self.port.operation
        roles = {role.name: role for role in operation.roles if role.direction == "input"}
        values = arguments.arguments
        bodies = {
            name: (values[role.parameter or name],)
            if role.collection == "scalar"
            else tuple(values[role.parameter or name])
            for name, role in roles.items()
        }
        recipe = next(
            item.key
            for item in self.port.model.identities
            if item.domain == "recipe" and item.owner == operation.semantic_id
        )
        basis = cpu_input_basis_from_binding(recipe, binding, bodies)
        kernel = (
            execute_rich_consolidation_kernel
            if operation.semantic_id == "rich.consolidate"
            else execute_rich_admission_kernel
        )
        bound = inspect.signature(kernel, eval_str=True).bind(
            input_basis=basis,
            asset_content=self.asset_content,
            prepared=self.prepared,
            check_active=check_active,
        )
        return (
            yield from self.port.plan_cpu(
                kernel,
                bound,
                rich_knowledge_operation_sources(),
                prepared_release_id=self.prepared.release_id,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def acquire_rich_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.rich_knowledge import (
        RichKnowledgeAdmission,
        RichKnowledgeConsolidation,
    )

    from .data_operation_effects import PreparedNativePublicationEffect
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id == "rich.consolidate":
        receiver = RichKnowledgeConsolidation(None)
        kernel = execute_rich_consolidation_kernel
    elif selected.semantic_id == "rich.admit":
        receiver = RichKnowledgeAdmission(None)
        kernel = execute_rich_admission_kernel
    else:
        raise PortRefusal("rich preparation belongs to another declared operation")
    artifacts = [item for item in custody if item.name == "rich-knowledge/algorithm-assets"]
    if len(artifacts) != 1:
        raise PortRefusal("rich acquisition requires its actual captured algorithm assets")
    plan = RichInvocationPlan(prepared, artifacts[0].content.decode())
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.rich_invocations.RichInvocationPlan.plan",
        authorize,
        (rich_knowledge_assets(),),
        rich_knowledge_operation_sources(),
        functions=((kernel.__module__ + "." + kernel.__qualname__, kernel),),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return PreparedNativePublicationEffect(port) if selected.semantic_id == "rich.admit" else port
