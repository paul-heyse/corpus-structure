"""Declared definition projections over authentic source and primary product inputs."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import PreparedRelease, SourceArtifact

_ROOT = Path(__file__).parents[1]
_PATHS = (
    "semantic/data_operation_cpu_basis.py",
    "semantic/definition_admission_native.py",
    "methods/definition_declared.py",
    "semantic/definition_products.py",
    "methods/definition_applicability.py",
    "methods/definition_declaration.py",
    "semantic/constructions/retained_declarations.py",
    "semantic/structural_products.py",
    "semantic/declared_structural_references.py",
    "semantic/declared_record_sources.py",
    "semantic/construction_products.py",
    "semantic/characterization_manifests.py",
    "semantic/hanlp_products.py",
    "semantic/source_contexts.py",
)


def definition_inputs(bundle):
    from .contextual_operations import contextual_inputs
    from .declaration_products import declaration_inputs
    from .declared_structural_calls import structural_inputs
    from .hanlp_products import hanlp_product_inputs

    if "data_operation_constructions" not in {source.name for source in bundle.sources}:
        bundle = declaration_inputs(bundle)
    if "data_operation_hanlp" not in {source.name for source in bundle.sources}:
        bundle = hanlp_product_inputs(bundle)
    return structural_inputs(contextual_inputs(bundle))


def definition_profile_assets():
    return SourceArtifact(
        "definitions/profile-assets",
        canonical_bytes(
            {
                "version": "declared-definition-projections-v1",
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/definition_declared.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _PATHS
                ],
            }
        ),
    )


def definition_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                "methods/definition_declared.py",
                "semantic/definition_products.py",
                "methods/definition_applicability.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(definition_profile_assets(),),
    )


@dataclass(frozen=True)
class PreparedDefinitionInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Callable[[], None]

    def members(self, role, *, whole=True):
        selected = next(value for value in self.roles if value.role == role)
        if any(
            (whole and member.member is not None) or member.multiplicity != 1
            for member in selected.members
        ):
            raise ValueError("definition inputs require their exact whole primary inventories")
        return selected.members

    def retained(self, role, values, name, model, source):
        from .construction_products import CharacterizationSnapshot
        from .enriched_document_products import RetainedCharacterizationProduct

        result = []
        for member, body in zip(self.members(role), values, strict=True):
            if (
                body["source"] != source.value["source"]
                or body["selectors"] != source.value["selectors"]
            ):
                raise ValueError(
                    "definition primary product differs from exact source and analyzed scope"
                )
            context = SubjectContext(
                self.context.project_id,
                member.subject,
                member.original_source,
                member.analyzed_scope,
                subject_definition=member.subject_definition,
            )
            product = RetainedCharacterizationProduct.acquire(
                self.prepared,
                model,
                self.prepared.index.definitions[name].iri,
                canonical_bytes(body),
                subject_context=context,
            )
            if product.semantic_id != member.product:
                raise ValueError("definition primary body differs from its exact selected product")
            result.append(CharacterizationSnapshot(product.semantic_id, product.content))
        return tuple(result)

    def declaration(
        self, source, syntax, hanlp, *, start, end, passage_id, scope, effective_version, parent
    ):
        from corpus_structure.methods.definition_declaration import (
            primary_declaration_component_products,
        )

        from .data_operation_admission import bound_data_operation_model
        from .declared_record_sources import DeclaredNativeFrameSource
        from .declared_structural_calls import _passage
        from .source_products import FrozenNativeSource
        from .structural_products import (
            DeclaredDefinitionComponentsProduct,
            DeclaredDefinitionComponentsReport,
            DeclaredStructuralInput,
            DeclaredStructuralInputPin,
            DefinitionStage,
        )

        self.check_active()
        model = bound_data_operation_model(self.prepared)
        selected = FrozenNativeSource.acquire(self.prepared, source)
        (source_member,) = self.members("source", whole=False)
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, source, source_member, project=self.context.project_id
        )
        reference, passage = _passage(
            frame,
            passage_id=passage_id,
            start=start,
            end=end,
            scope=scope,
            version=effective_version,
            parent=parent,
        )
        # Authored passage bounds select from the admitted analyzed source scope;
        # source text outside that scope never becomes a declaration premise.
        index = selected.selector_index()
        if not any(
            selector.get("start", 0) <= start
            and end <= selector.get("end", len(frame.text))
            and all(
                index.matches(selector, piece["item_ref"]) is True
                for piece in selected.value["pieces"]
                if piece["kind"] == "native_text" and start < piece["end"] and piece["start"] < end
            )
            for selector in selected.value["selectors"]
        ):
            raise ValueError("definition passage exceeds its analyzed original source scope")
        primary = self.retained("syntax", syntax, "DdoDeclarationSyntaxProduct", model, selected)
        support = self.retained("hanlp", hanlp, "DdoHanlpInventory", model, selected)
        component = primary_declaration_component_products(
            primary, selected, passage, supporting=support, source_pin=frame.pin.values()
        )
        source_pin = DeclaredStructuralInputPin.from_bound(
            source_member, project=self.context.project_id
        )
        primary_pins = tuple(
            DeclaredStructuralInputPin.from_bound(member, project=self.context.project_id)
            for member in self.members("syntax")
        )
        dependencies = tuple(
            member.product for role in ("syntax", "hanlp") for member in self.members(role)
        )
        report = DeclaredDefinitionComponentsReport(
            inputs=DeclaredStructuralInput(
                question="Read the exact retained local declaration chain.",
                scope=scope,
                inventory_id="explicit-native-definition",
                policy_id="retained-declaration-chain-v2",
                sources=(reference,),
                passages=(passage,),
                dependencies=dependencies,
            ),
            definition_components=DeclaredDefinitionComponentsProduct(
                components=(component,),
                stages=(
                    DefinitionStage(
                        passage_id=passage_id,
                        operation="attachment",
                        outcome="succeeded",
                        reason="Released declaration chain replayed from exact separately retained native syntax.",
                    ),
                ),
            ),
            sources_input=(source_pin,),
            reports_input=primary_pins,
        )
        self.check_active()
        return report.model_dump(mode="json", exclude_none=True)


def execute_definition_declaration(
    receiver, source, syntax, hanlp, start, end, passage_id, scope, effective_version, parent
):
    return receiver.inputs.declaration(
        source,
        syntax,
        hanlp,
        start=start,
        end=end,
        passage_id=passage_id,
        scope=scope,
        effective_version=effective_version,
        parent=parent,
    )


def definition_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    input_basis: list,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.definition_declared import DefinitionDeclarationOperation

    from .data_operation_cpu_basis import cpu_authority_reply, require_consumed_cpu_basis
    from .data_operation_values import semantic_value

    names = {role.role for role in roles}
    if names != {"source", "syntax", "hanlp"} or any(
        role.state != "present" or not role.members for role in roles
    ):
        raise ValueError("definition declaration requires its exact original input population")
    require_consumed_cpu_basis(
        input_basis,
        context,
        roles,
        {
            role.role: (arguments[role.role],)
            if role.role == "source"
            else tuple(arguments[role.role])
            for role in roles
        },
        parameters=canonical_bytes(
            semantic_value({name: value for name, value in arguments.items() if name not in names})
        ),
    )
    result = DefinitionDeclarationOperation(
        PreparedDefinitionInputs(prepared, roles, context, check_active)
    ).run(**arguments)
    return cpu_authority_reply(input_basis, result)


@dataclass
class DefinitionCallPlan:
    prepared: PreparedRelease
    kernel: Callable = definition_kernel
    port: Any = None

    def verify(self):
        if definition_profile_assets() != self.port.assets[0]:
            raise ValueError("definition source or semantic assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("definition call requires its exact qualified binding")
        signature = inspect.signature(self.kernel, eval_str=True)
        values: dict[str, Any] = dict(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        from .data_operation_cpu_basis import cpu_input_basis_from_binding

        collections = {role.name: role.collection for role in self.port.operation.roles}
        values["input_basis"] = cpu_input_basis_from_binding(
            self.port.identity.recipe,
            binding,
            {
                role.role: (arguments.arguments[role.role],)
                if collections[role.role] == "scalar"
                else tuple(arguments.arguments[role.role])
                for role in binding.roles
            },
        )
        bound = signature.bind(**values)
        captured = definition_operation_sources()
        return (
            yield from self.port.plan_cpu(
                self.kernel,
                bound,
                captured,
                prepared_release_id=self.prepared.release_id,
                verify=self.verify,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_definition_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.definition_declared import DefinitionDeclarationOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id == DefinitionDeclarationOperation.__data_operation__["id"]:
        receiver, kernel = DefinitionDeclarationOperation(None), definition_kernel
    else:
        raise PortRefusal("definition factory differs from its governing operation")
    plan = DefinitionCallPlan(prepared, kernel)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.definition_products.DefinitionCallPlan.plan",
        authorize,
        (definition_profile_assets(),),
        definition_operation_sources(),
        functions=(
            ("corpus_structure.semantic.definition_products." + kernel.__name__, kernel),
            (
                "corpus_structure.semantic.definition_products.execute_definition_declaration",
                execute_definition_declaration,
            ),
            (
                "corpus_structure.semantic.definition_products.PreparedDefinitionInputs.declaration",
                PreparedDefinitionInputs.declaration,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port
