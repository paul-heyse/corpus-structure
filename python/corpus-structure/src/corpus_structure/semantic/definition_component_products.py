"""Declared generic definition components from exact retained model products."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .types import SourceArtifact

_ROOT = Path(__file__).parents[1]
_FILES = (
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
                "files": [(name, (_ROOT / name).read_bytes().hex()) for name in _FILES],
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
        DeclaredDefinitionComponentsReport,
        DeclaredLocatedDefinitionComponent,
        DeclaredStructuralInput,
        DeclaredStructuralInputPin,
        DefinitionRoleCandidate,
        DefinitionStage,
    )

    def member(name):
        (value,) = next(role.members for role in roles if role.role == name)
        if value.member is not None or value.multiplicity != 1:
            raise ValueError("definition components require exact whole retained products")
        return value

    check_active()
    frame = DeclaredNativeFrameSource.acquire(
        prepared, source, member("source"), project=context.project_id
    )
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
    report = DeclaredDefinitionComponentsReport(
        inputs=DeclaredStructuralInput(
            question="What terms and defining content are explicitly attached in these source blocks?",
            scope="selected-native-blocks",
            inventory_id="located-definition-components",
            policy_id="definition.located_gliner_v1",
            sources=tuple(sources),
            passages=tuple(passages),
            dependencies=(member("observation").product, member("candidates").product),
            coverage_limits=limits,
        ),
        definition_components=DeclaredDefinitionComponentsProduct(
            components=tuple(components[key] for key in sorted(components)),
            role_candidates=tuple(proposals),
            stages=tuple(stages),
        ),
        sources_input=(
            DeclaredStructuralInputPin.from_bound(member("source"), project=context.project_id),
        ),
        reports_input=(
            DeclaredStructuralInputPin.from_bound(member("candidates"), project=context.project_id),
        ),
    )
    check_active()
    return report.model_dump(mode="json", exclude_none=True)


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


def definition_components_kernel(
    arguments: dict, roles: tuple, context: Any, *, prepared: Any, check_active: Any
) -> dict:
    return project_definition_components(
        prepared, roles, context, **arguments, check_active=check_active
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
        signature = inspect.signature(self.kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        return (yield from self.port.plan_cpu(
            self.kernel,
            bound,
            definition_component_operation_sources(include_learned=self.kernel is definition_components_kernel),
            prepared_release_id=self.prepared.release_id,
            verify=self.verify,
            execution_owner=execution_owner,
            check_active=check_active,
        ))


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
    from .data_product_reference import DataProductMemberReference
    from .declared_record_sources import DeclaredNativeFrameSource
    from .declared_structural_calls import _passage
    from .declared_structural_references import DeclaredProductRef
    from .sentence_products import retained_source_annotation_products
    from .source_products import FrozenNativeSource
    from .structural_products import (
        DeclaredDefinitionBasisWitness,
        DeclaredDefinitionComponentsProduct,
        DeclaredDefinitionComponentsReport,
        DeclaredPrimaryReference,
        DeclaredStructuralInput,
        DeclaredStructuralInputPin,
        DefinitionStage,
        LocatedDefinitionSpan,
        declared_definition_component,
    )

    def member(name):
        (value,) = next(role.members for role in roles if role.role == name)
        if value.member is not None or value.multiplicity != 1:
            raise ValueError("named definition components require exact whole primary products")
        return value

    check_active()
    selected = FrozenNativeSource.acquire(prepared, source)
    frame = DeclaredNativeFrameSource.acquire(
        prepared, source, member("source"), project=context.project_id
    )
    for body in (annotations, constructions):
        if body["source"] != source["source"] or body["selectors"] != source["selectors"]:
            raise ValueError("named definition input differs from its exact original source/scope")
    native = CharacterizationSnapshot(member("annotations").product, canonical_bytes(annotations))
    primary = (
        CharacterizationSnapshot(member("constructions").product, canonical_bytes(constructions)),
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
                if not isinstance(ref, DataProductMemberReference):
                    raise ValueError(
                        "declared definition scope has a nonsemantic primary reference"
                    )
                primary_scope.append(
                    DeclaredPrimaryReference(
                        product_id=ref.product.product_id, member_id=ref.member_id
                    )
                )
            witnesses[match] = DeclaredDefinitionBasisWitness(
                annotation_product=DeclaredProductRef.from_bound(
                    member("annotations"), project=context.project_id
                ),
                block_id=product.block_id,
                dependency_digest=product.dependency_digest,
                rule=match.rule,
                variant=match.variant,
                nodes=match.nodes,
                primary_match=references[match],
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
                component_factory=declared_definition_component,
            ),
            *components_from_following_display(
                passage,
                result.matches,
                tuple(product.display_spans),
                scopes=scopes,
                term_role=term_role,
                witnesses=witnesses,
                component_factory=declared_definition_component,
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
    report = DeclaredDefinitionComponentsReport(
        inputs=DeclaredStructuralInput(
            question="Which retained named cues explicitly bind terms and defining text or native displays?",
            scope="selected-native-blocks",
            inventory_id="retained-named-definition-components",
            policy_id="definition-scope-1",
            sources=tuple(sources),
            passages=tuple(passages),
            dependencies=(member("annotations").product, member("constructions").product),
            coverage_limits=tuple(limits),
        ),
        definition_components=DeclaredDefinitionComponentsProduct(
            components=tuple(found[key] for key in sorted(found)), stages=tuple(stages)
        ),
        sources_input=(
            DeclaredStructuralInputPin.from_bound(member("source"), project=context.project_id),
        ),
        reports_input=(
            DeclaredStructuralInputPin.from_bound(
                member("constructions"), project=context.project_id
            ),
        ),
    )
    check_active()
    return report.model_dump(mode="json", exclude_none=True)


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
    arguments: dict, roles: tuple, context: Any, *, prepared: Any, check_active: Any
) -> dict:
    return project_named_definition_components(
        prepared, roles, context, **arguments, check_active=check_active
    )
