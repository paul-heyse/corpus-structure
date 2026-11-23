"""Declared generic definition components from exact retained model products."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import SourceArtifact

_ROOT = Path(__file__).parents[1]
_FILES = (
    "semantic/data_operation_cpu_basis.py",
    "semantic/definition_admission_native.py",
    "methods/definition_components_declared.py",
    "semantic/definition_component_products.py",
    "semantic/definition_model_products.py",
    "methods/definition_applicability.py",
    "semantic/structural_products.py",
    "semantic/declared_structural_references.py",
    "semantic/declared_record_sources.py",
    "semantic/data_operation_prepared_call.py",
    "methods/definition_named_declared.py",
    "semantic/constructions/declared_named.py",
    "semantic/construction_products.py",
    "semantic/reference_resolution.py",
    "semantic/sentence_products.py",
    "methods/model_observation.json",
    "methods/predicate_frames.py",
)


def definition_component_inputs(bundle, *, include_learned=False):
    from .declared_structural_calls import structural_inputs
    from .learned_primary import learned_primary_inputs

    if include_learned and "data_operation_learned" not in {
        source.name for source in bundle.sources
    }:
        bundle = learned_primary_inputs(bundle)
    if "data_operation_constructions" not in {source.name for source in bundle.sources}:
        from .declaration_products import declaration_inputs

        bundle = declaration_inputs(bundle)
    return structural_inputs(bundle)


def definition_component_assets():
    return SourceArtifact(
        "definition-components/profile-assets",
        canonical_bytes(
            {
                "version": "declared-located-definition-components-v1",
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name
                            in (
                                "methods/definition_components_declared.py",
                                "methods/definition_named_declared.py",
                            )
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _FILES
                ],
            }
        ),
    )


def definition_component_operation_sources(*, include_learned=False):
    """Acquire deterministic named/display readers independently of model providers."""
    from .python_operation_sources import PythonSource, PythonSourceCollection

    modules = (
        "semantic/definition_component_products.py",
        "methods/definition_named_declared.py",
        "semantic/constructions/declared_named.py",
    )
    if include_learned:
        modules = (
            *modules,
            "methods/definition_components_declared.py",
            "semantic/definition_model_products.py",
        )
    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in modules
        ),
        boundary_contracts=(definition_component_assets(),),
    )


def project_definition_components(
    prepared, roles, context, source, observation, candidates, *, check_active
):
    from .declared_record_sources import DeclaredNativeFrameSource
    from .declared_structural_calls import _passage
    from .definition_model_products import retained_definition_windows
    from .sentence_products import _blocks
    from .source_products import FrozenNativeSource
    from .structural_products import (
        DeclaredDefinitionComponentsProduct,
        DeclaredLearnedDefinitionComponentsReport,
        DeclaredLocatedDefinitionComponent,
        DeclaredStructuralInput,
        DefinitionRoleCandidate,
        DefinitionStage,
        definition_component_packets,
        definition_component_report_values,
    )

    def member(name):
        (value,) = next(role.members for role in roles if role.role == name)
        # The source-view family publishes this exact source as a member;
        # observation/candidate reports must still be whole retained products.
        if value.multiplicity != 1 or (name != "source" and value.member is not None):
            raise ValueError("definition components require exact whole retained products")
        return value

    check_active()
    frame = DeclaredNativeFrameSource.acquire(
        prepared, source, member("source"), project=context.project_id
    )
    member("observation")
    member("candidates")
    selected = FrozenNativeSource.acquire(prepared, source)
    retained = retained_definition_windows(frame, observation, candidates)
    blocks, _ = _blocks(selected)
    if not blocks:
        raise ValueError(
            "generic definition components require an actual selected nonempty source block"
        )
    sources, passages = [], []
    for block in blocks:
        reference, passage = _passage(
            frame, passage_id=block.block_id, start=block.start, end=block.end, scope=block.block_id
        )
        if not sources:
            sources.append(reference)
        passages.append(passage)
    components, proposals, stages = {}, [], []
    for _, window, decoded in retained:
        if window.passage_id not in {passage.passage_id for passage in passages}:
            raise ValueError("definition window differs from the actual selected block inventory")
        for body in decoded["components"]:
            component = DeclaredLocatedDefinitionComponent.model_validate(body)
            components[component.component_id] = component
        proposals.extend(
            DefinitionRoleCandidate.model_validate(body) for body in decoded["role_candidates"]
        )
        for operation in ("located_extraction", "attachment"):
            failed = any(
                error["channel"]
                in (
                    {"term", "content", "roles"}
                    if operation == "located_extraction"
                    else {"attachment"}
                )
                for error in decoded["errors"]
            )
            stages.append(
                DefinitionStage(
                    passage_id=window.passage_id,
                    operation=operation,
                    outcome="failed"
                    if failed
                    else "succeeded"
                    if (
                        decoded["role_candidates"]
                        if operation == "located_extraction"
                        else decoded["components"]
                    )
                    else "empty",
                    reason="Exact retained located GLiNER window; independently located roles and directed attachments preserved.",
                )
            )
    observed_blocks = {window.passage_id for _, window, _ in retained}
    stages.extend(
        DefinitionStage(
            passage_id=passage.passage_id,
            operation="located_extraction",
            outcome="unavailable",
            reason="The retained provider pair did not inspect this selected original block; no absence is established.",
        )
        for passage in passages
        if passage.passage_id not in observed_blocks
    )
    limits = (
        ()
        if observation["outcome"] == "complete"
        else (
            "The actual retained provider inspection contains unavailable or unexamined source coverage; empty components establish no absence there.",
        )
    )
    from .data_product_reference import SemanticReference

    report = DeclaredLearnedDefinitionComponentsReport(
        inputs=DeclaredStructuralInput(
            question="What terms and defining content are explicitly attached in these source blocks?",
            scope="selected-native-blocks",
            inventory_id="located-definition-components",
            policy_id="definition.located_gliner_v1",
            sources=tuple(sources),
            passages=tuple(passages),
            dependencies=(),
            coverage_limits=limits,
        ),
        members=definition_component_packets(
            prepared, context, tuple(components[key] for key in sorted(components))
        ),
        definition_components=DeclaredDefinitionComponentsProduct(
            role_candidates=tuple(proposals),
            stages=tuple(stages),
        ),
        candidates_input=SemanticReference.whole("candidates").whole_value(),
    )
    check_active()
    return definition_component_report_values(report)


def execute_definition_components(receiver, source, observation, candidates):
    return project_definition_components(
        receiver.prepared,
        receiver.roles,
        receiver.context,
        source,
        observation,
        candidates,
        check_active=receiver.check_active,
    )


def _component_authority_kernel(
    arguments, roles, context, input_basis, *, prepared, check_active, named
):
    from .data_operation_cpu_basis import cpu_authority_reply, require_consumed_cpu_basis
    from .data_operation_values import semantic_value

    names = {role.role for role in roles}
    expected_names = (
        {"source", "annotations", "constructions"}
        if named
        else {"source", "observation", "candidates"}
    )
    if names != expected_names or any(
        role.state != "present" or len(role.members) != 1 for role in roles
    ):
        raise ValueError(
            "definition component authority requires its exact scalar input population"
        )
    body_values = {name: (arguments[name],) for name in names}
    if named:
        body_values["annotations"] = (arguments["annotations"]["header"],)
    require_consumed_cpu_basis(
        input_basis,
        context,
        roles,
        body_values,
        parameters=canonical_bytes(
            semantic_value({key: value for key, value in arguments.items() if key not in names})
        ),
    )
    kernel = project_named_definition_components if named else project_definition_components
    return cpu_authority_reply(
        input_basis, kernel(prepared, roles, context, **arguments, check_active=check_active)
    )


def definition_components_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    input_basis: list,
    *,
    prepared: Any,
    check_active: Any,
) -> dict:
    return _component_authority_kernel(
        arguments,
        roles,
        context,
        input_basis,
        prepared=prepared,
        check_active=check_active,
        named=False,
    )


@dataclass
class DefinitionComponentsCallPlan:
    prepared: Any
    kernel: Any = None
    port: Any = None

    def verify(self):
        if definition_component_assets() != self.port.assets[0]:
            raise ValueError("definition component source or policy changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("definition components require their exact qualified binding")
        from .data_operation_cpu_basis import cpu_input_basis_from_binding

        body_values = {role.role: (arguments.arguments[role.role],) for role in binding.roles}
        if self.kernel is named_definition_components_kernel:
            body_values["annotations"] = (arguments.arguments["annotations"]["header"],)
        signature = inspect.signature(self.kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            input_basis=cpu_input_basis_from_binding(
                self.port.identity.recipe,
                binding,
                body_values,
            ),
            prepared=self.prepared,
            check_active=check_active,
        )
        return (
            yield from self.port.plan_cpu(
                self.kernel,
                bound,
                definition_component_operation_sources(
                    include_learned=self.kernel is definition_components_kernel
                ),
                prepared_release_id=self.prepared.release_id,
                verify=self.verify,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_definition_components_port(
    prepared, model, operation, *, identity, authorize, custody, sources
):
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id == "structure.definition_components/declared":
        from corpus_structure.methods.definition_components_declared import (
            DefinitionComponentsOperation,
        )

        receiver, kernel = DefinitionComponentsOperation(None), definition_components_kernel
    elif selected.semantic_id == "structure.definition_named_components/declared":
        from corpus_structure.methods.definition_named_declared import (
            NamedDefinitionComponentsOperation,
        )

        receiver, kernel = (
            NamedDefinitionComponentsOperation(None),
            named_definition_components_kernel,
        )
    else:
        raise ValueError("definition component factory differs from its actual operation")
    plan = DefinitionComponentsCallPlan(prepared, kernel)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.definition_component_products.DefinitionComponentsCallPlan.plan",
        authorize,
        (definition_component_assets(),),
        definition_component_operation_sources(
            include_learned=kernel is definition_components_kernel
        ),
        functions=(
            (
                "corpus_structure.semantic.definition_component_products.execute_definition_components",
                execute_definition_components,
            ),
            (
                "corpus_structure.semantic.definition_component_products.project_definition_components",
                project_definition_components,
            ),
            ("corpus_structure.semantic.definition_component_products." + kernel.__name__, kernel),
            (
                "corpus_structure.semantic.definition_component_products.execute_named_definition_components",
                execute_named_definition_components,
            ),
            (
                "corpus_structure.semantic.definition_component_products.project_named_definition_components",
                project_named_definition_components,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port


def project_named_definition_components(
    prepared, roles, context, source, annotations, constructions, *, check_active
):
    """Read primary named roles and native display geometry using the original kernels."""
    from itertools import pairwise

    from corpus_structure.methods.definition_applicability import (
        _DEFINITION_SCOPE,
        _WITNESS_COLUMNS,
        components_from_following_display,
        components_from_named_matches,
        definition_scopes,
    )
    from corpus_structure.methods.model_observation import declared_policy
    from corpus_structure.methods.predicate_frames import (
        predicate_frames,
        prepare_predicate_readings,
    )

    from .construction_products import CharacterizationSnapshot
    from .constructions.declared_named import DeclaredNamedRules
    from .data_product_reference import DataProductMemberReference, SemanticReference
    from .declared_record_sources import DeclaredNativeFrameSource
    from .declared_structural_calls import _passage
    from .reference_resolution import require_selected_whole_reference
    from .sentence_products import retained_source_annotation_products
    from .source_products import FrozenNativeSource
    from .structural_products import (
        DeclaredDefinitionBasisWitness,
        DeclaredDefinitionComponentsProduct,
        DeclaredNamedDefinitionComponentsReport,
        DeclaredNamedDefinitionWitness,
        DeclaredStructuralInput,
        DefinitionStage,
        LocatedDefinitionSpan,
        definition_component_packets,
        definition_component_report_values,
    )

    def member(name):
        (value,) = next(role.members for role in roles if role.role == name)
        # A selected native source is genuinely a member of the source-view
        # family. Primary annotation/construction reports remain whole products.
        if value.multiplicity != 1 or (name != "source" and value.member is not None):
            raise ValueError("named definition components require exact whole primary products")
        return value

    check_active()
    selected = FrozenNativeSource.acquire(prepared, source)
    frame = DeclaredNativeFrameSource.acquire(
        prepared, selected, member("source"), project=context.project_id
    )
    annotation_header = annotations["header"]
    for body in (annotation_header, constructions):
        if body["source"] != source["source"] or tuple(body["selectors"]) != tuple(
            source["selectors"]
        ):
            raise ValueError("named definition input differs from its exact original source/scope")
    annotation_member = member("annotations")
    construction_member = member("constructions")
    require_selected_whole_reference(
        SemanticReference.whole("sentences"),
        role="sentences",
        producing=construction_member,
        selected=annotation_member,
    )
    native = CharacterizationSnapshot(
        annotation_member.product,
        canonical_bytes(annotation_header),
        tuple(canonical_bytes(packet) for packet in annotations["partitions"]),
    )
    primary = (
        CharacterizationSnapshot(construction_member.product, canonical_bytes(constructions)),
    )
    products = retained_source_annotation_products(selected, native)
    if not products:
        raise ValueError("named definition components require actual retained native source blocks")
    named = DeclaredNamedRules(primary, native)
    readings = prepare_predicate_readings(primary)
    policy = declared_policy(prepared)["definition_witness"]
    qualified = (
        policy.get("rules", {}) if policy.get("scope") == _DEFINITION_SCOPE["version"] else {}
    )
    term_role, content_role = policy["term_role"], policy["content_role"]
    sources, passages, stages, limits = [], [], [], []
    found: dict[str, Any] = {}
    recorded_witnesses = {}
    for product in products:
        check_active()
        reference, passage = _passage(
            frame,
            passage_id=product.block_id,
            start=product.block_start,
            end=product.block_end,
            scope=product.block_id,
        )
        if not sources:
            sources.append(reference)
        passages.append(passage)
        result, references, nominations, rule_ids = named.decode(product)
        scopes = (
            definition_scopes(
                result.matches,
                predicate_frames(frame.text, (product,), primary_products=readings),
                content_role=content_role,
            )
            if result.matches
            else {}
        )
        antecedents = {}
        for match in result.matches:
            nomination = nominations.get(match, {}).get(content_role)
            if (
                nomination is None
                or nomination.status != "resolved"
                or not nomination.antecedent_extents
            ):
                continue
            extents = nomination.antecedent_extents
            first, last = extents[0][0], extents[-1][1]
            if (
                nomination.context_start is not None
                and passage.start <= nomination.context_start <= first < last <= passage.end
                and all(left <= right for (_, left), (right, _) in pairwise(extents))
            ):
                antecedents[match] = LocatedDefinitionSpan(
                    passage_id=passage.passage_id,
                    start=first,
                    end=last,
                    text=frame.text[first:last],
                )
        complete_columns = {
            column.attribute for column in product.availability if column.status == "complete"
        } >= _WITNESS_COLUMNS
        witnesses: Any = {}
        for match in result.matches:
            scope = scopes.get(match)
            if (
                not complete_columns
                or scope is None
                or not scope.primary_scope
                or rule_ids[match.rule, match.variant]
                != "named-rule:" + qualified.get(f"{match.rule}/{match.variant}", "")
                or (
                    content_role in nominations.get(match, {})
                    and nominations[match][content_role].demonstrative is not False
                )
            ):
                continue
            primary_scope = []
            for ref in scope.primary_scope:
                if (
                    not isinstance(ref, DataProductMemberReference)
                    or ref.product.product_id != construction_member.product
                ):
                    raise ValueError(
                        "declared definition scope has a nonsemantic primary reference"
                    )
                primary_scope.append(
                    SemanticReference.member("constructions", ref.member_id).values()
                )
            match_ref = references[match]
            if match_ref.product.product_id != construction_member.product:
                raise ValueError("named definition match differs from its producing construction")
            witnesses[match] = DeclaredDefinitionBasisWitness(
                annotation_product=SemanticReference.whole("annotations").values(),
                block_id=product.block_id,
                dependency_digest=product.dependency_digest,
                rule=match.rule,
                variant=match.variant,
                nodes=match.nodes,
                primary_match=SemanticReference.member(
                    "constructions", match_ref.member_id
                ).values(),
                primary_scope=tuple(primary_scope),
            )
        components = (
            *components_from_named_matches(
                passage,
                result.matches,
                scopes=scopes,
                term_role=term_role,
                content_role=content_role,
                antecedents=antecedents,
                witnesses=witnesses,
                witnesses_by_component=recorded_witnesses,
            ),
            *components_from_following_display(
                passage,
                result.matches,
                tuple(product.display_spans),
                scopes=scopes,
                term_role=term_role,
                witnesses=witnesses,
                witnesses_by_component=recorded_witnesses,
            ),
        )
        found.update((component.component_id, component) for component in components)
        available = bool(result.availability) and all(
            state == "available" for _, _, state in result.availability
        )
        if not available:
            limits.append(
                "Named variants in native block "
                + product.block_id
                + " have unavailable or unperformed primary coverage; no absence is established."
            )
        stages.extend(
            (
                DefinitionStage(
                    passage_id=passage.passage_id,
                    operation="located_extraction",
                    outcome="succeeded"
                    if available and result.matches
                    else "empty"
                    if available
                    else "unavailable",
                    reason="Actual retained named availability and explicit native role bindings.",
                ),
                DefinitionStage(
                    passage_id=passage.passage_id,
                    operation="attachment",
                    outcome="succeeded" if components else "empty" if available else "unavailable",
                    reason="Original scope-qualified named and adjacent native display algorithms; no downstream language recognition.",
                ),
            )
        )
    from .data_product_reference import SemanticReference

    report = DeclaredNamedDefinitionComponentsReport(
        inputs=DeclaredStructuralInput(
            question="Which retained named cues explicitly bind terms and defining text or native displays?",
            scope="selected-native-blocks",
            inventory_id="retained-named-definition-components",
            policy_id="definition-scope-1",
            sources=tuple(sources),
            passages=tuple(passages),
            dependencies=(),
            coverage_limits=tuple(limits),
        ),
        members=definition_component_packets(
            prepared, context, tuple(found[key] for key in sorted(found))
        ),
        definition_components=DeclaredDefinitionComponentsProduct(
            stages=tuple(stages),
        ),
        witnesses=tuple(
            DeclaredNamedDefinitionWitness(
                component_id=identity, basis=recorded_witnesses[identity]
            )
            for identity in sorted(recorded_witnesses)
        ),
        constructions_input=SemanticReference.whole("constructions").whole_value(),
    )
    check_active()
    return definition_component_report_values(report)


def execute_named_definition_components(receiver, source, annotations, constructions):
    return project_named_definition_components(
        receiver.prepared,
        receiver.roles,
        receiver.context,
        source,
        annotations,
        constructions,
        check_active=receiver.check_active,
    )


def named_definition_components_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    input_basis: list,
    *,
    prepared: Any,
    check_active: Any,
) -> dict:
    return _component_authority_kernel(
        arguments,
        roles,
        context,
        input_basis,
        prepared=prepared,
        check_active=check_active,
        named=True,
    )
