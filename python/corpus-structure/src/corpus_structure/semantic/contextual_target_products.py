"""Target-local canonical values and exact selected vector assembly.

Curated descriptions have project custody. Source-backed descriptions retain the
actual component report's original. Neither inherits the querying document.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from pydantic import TypeAdapter

from corpus_structure.methods.contextual_embeddings import (
    ContextInput,
    EncodedVector,
    EncoderProfile,
    RenderedInput,
    identity,
    validate_vector,
    verify_retained_rendering,
)

from .contextual_retrieval import TargetRepresentation, target_representation
from .data_operation_json import json_bytes
from .observations import source_python, source_value

TARGET_SUBJECT = "contextual-target"


def target_subject(target):
    return identity("contextual-target", [target.target_id, target.source_binding])


def target_context(target, original_source):
    return {
        "subject": target_subject(target),
        "subject_definition": TARGET_SUBJECT,
        "original_source": original_source,
        "analyzed_scope": {
            "target_id": target.target_id,
            "source_binding": target.source_binding,
        },
    }


def target_encoding_input(target):
    return ContextInput(
        target.target_id,
        target.source_binding,
        "document",
        target.label,
        target.label + "\n" + target.description,
        0,
        len(target.label),
        parent=target.parent or "",
        heading=("Aliases: " + ", ".join(target.aliases)) if target.aliases else "",
        type_name=target.type_name,
        representation_digest=target.representation_digest,
    )


def target_population(targets, *, original_source, kind_contract, semantic_targets=None):
    targets = tuple(sorted(targets, key=lambda value: value.target_id))
    if len({value.target_id for value in targets}) != len(targets):
        raise ValueError("target population repeats a target identity")
    return {
        "complete": True,
        "members": [
            {
                "member_id": target_subject(target),
                "kind_contract": kind_contract,
                "context": target_context(target, original_source),
                "body": {
                    "original_source": original_source,
                    "descriptor": source_value(asdict(target)),
                    "semantic_target": source_value(
                        semantic_targets[target.target_id]
                        if semantic_targets is not None
                        else {"curated_target": asdict(target)}
                    ),
                },
            }
            for target in targets
        ],
    }


def curated_target_population(selection, *, kind_contract):
    from .contextual_registry import RegistryTarget

    # Reconstruct the original registry descriptor binding, including all aliases,
    # rather than treating caller-supplied source strings as acquired provenance.
    raw = source_python(selection["targets"])
    values = TypeAdapter(tuple[RegistryTarget, ...]).validate_python(raw)
    if len({value.target_id for value in values}) != len(values):
        raise ValueError("curated population repeats a target identity")
    targets = tuple(
        target_representation(
            source_binding=identity("curated-target", value.model_dump(mode="json")),
            **value.model_dump(mode="python"),
        )
        for value in values
    )
    return target_population(targets, original_source=None, kind_contract=kind_contract)


def component_target_population(report, *, original_source, kind_contract):
    from .structural_products import DeclaredDefinitionComponentsReport

    selected = DeclaredDefinitionComponentsReport.model_validate(report)
    if not original_source or any(
        source.original_source != original_source for source in selected.sources_input
    ):
        raise ValueError("component targets require their actual original source")
    passages = {value.passage_id: value for value in selected.inputs.passages}
    targets, meanings = [], {}
    sources = {value.identity: value for value in selected.inputs.sources}
    for component in selected.definition_components.components:
        # Passage identities and exact located extents preserve independent source
        # occurrences. The enclosing report's membership is not target identity.
        term, content = component.term, component.content
        source = passages[term.passage_id].source_ref
        meanings[component.component_id] = {
            "term": {
                "source": sources[source].model_dump(mode="json"),
                "passage": passages[term.passage_id].model_dump(mode="json"),
                "span": term.model_dump(mode="json"),
            },
            "content": {
                "source": sources[passages[content.passage_id].source_ref].model_dump(mode="json"),
                "passage": passages[content.passage_id].model_dump(mode="json"),
                "span": content.model_dump(mode="json"),
            },
            "interpretation": component.interpretation,
            "scope": component.scope,
            "effective_version": component.effective_version,
        }
        binding = identity(
            "declared-definition-target-source",
            [
                original_source,
                source,
                term.model_dump(mode="json"),
                content.model_dump(mode="json"),
            ],
        )
        targets.append(
            target_representation(
                component.component_id,
                binding,
                term.text,
                content.text,
                type_name="definition",
                scope=component.scope,
                effective_version=component.effective_version,
            )
        )
    return target_population(
        targets,
        original_source=original_source,
        kind_contract=kind_contract,
        semantic_targets=meanings,
    )


def materialize_target(target, *, context):
    descriptor = TypeAdapter(TargetRepresentation).validate_python(
        source_python(target["descriptor"])
    )
    if target_context(descriptor, target.get("original_source")) != {
        key: value for key, value in context.record.items() if key != "project_id"
    }:
        raise ValueError("target descriptor differs from its exact discovered context")
    return {
        "original_source": target.get("original_source"),
        "descriptor": target["descriptor"],
        "semantic_target": target["semantic_target"],
    }


def selected_vector_frame(inventory, query, targets):
    """Exact assembly only; selected vector bytes retain their producing support."""
    from .contextual_operations import admitted_contextual_inventory

    selected = admitted_contextual_inventory(inventory)
    profile = TypeAdapter(EncoderProfile).validate_python(source_python(query["profile"]))
    query_vector = TypeAdapter(EncodedVector).validate_python(query["vector"])
    query_rendered = TypeAdapter(RenderedInput).validate_python(query["rendered"])
    if query_rendered.role != "query" or (
        query_vector.object_id,
        query_vector.source_binding,
        query_vector.input_digest,
        query_vector.representation_digest,
    ) != (
        query_rendered.object_id,
        query_rendered.source_binding,
        query_rendered.final_input_digest,
        query_rendered.representation_digest,
    ):
        raise ValueError("selected query vector requires its actual query rendering")
    expected = {value.target_id: value for value in selected.targets}
    vectors, seen = [query_vector], set()
    for product in targets:
        actual_profile = TypeAdapter(EncoderProfile).validate_python(
            source_python(product["profile"])
        )
        vector = TypeAdapter(EncodedVector).validate_python(product["vector"])
        target = expected.get(vector.object_id)
        if target is None or vector.object_id in seen:
            raise ValueError("selected target vectors contain duplicate or foreign membership")
        if actual_profile != profile:
            raise ValueError("selected target vector uses a different complete encoder profile")
        retained_target = product["target"]
        if source_python(retained_target["descriptor"]) != asdict(target):
            # Compare canonical source values below to preserve tuple/list meaning.
            from .identity import canonical_bytes

            if canonical_bytes(source_python(retained_target["descriptor"])) != canonical_bytes(
                asdict(target)
            ):
                raise ValueError(
                    "selected vector target differs from its exact inventory descriptor"
                )
        from .contextual_retrieval import _meaning

        meanings = [
            group.meaning
            for group in selected.semantic_groups
            if target.target_id in group.member_target_ids
        ]
        from .identity import canonical_bytes

        if len(meanings) != 1 or canonical_bytes(
            _meaning(source_python(retained_target["semantic_target"]))
        ) != canonical_bytes(meanings[0]):
            raise ValueError("selected target meaning differs from its authentic selected source")
        rendered = TypeAdapter(RenderedInput).validate_python(product["rendered"])
        verify_retained_rendering(target_encoding_input(target), profile, rendered)
        if (vector.input_digest, vector.source_binding, vector.representation_digest) != (
            rendered.final_input_digest,
            rendered.source_binding,
            rendered.representation_digest,
        ):
            raise ValueError("selected target vector differs from its actual rendered input")
        vectors.append(vector)
        seen.add(vector.object_id)
    if seen != expected.keys():
        raise ValueError("selected target vector population is missing required inventory members")
    if query_vector.object_id in seen:
        raise ValueError("query and target vector identities overlap")
    if len(vectors) > profile.max_items:
        raise ValueError("selected vector population exceeds the captured encoder bound")
    for vector in vectors:
        validate_vector(vector.values, profile.dimension)
        if vector.profile_id != profile.profile_id or vector.vector_id != identity(
            "context-vector",
            [
                vector.object_id,
                vector.source_binding,
                profile.profile_id,
                vector.input_digest,
                vector.representation_digest,
            ],
        ):
            raise ValueError("selected vector differs from its exact profile/input identity")
    return {
        "profile": query["profile"],
        "vectors": source_value(
            [asdict(value) for value in sorted(vectors, key=lambda value: value.object_id)]
        ),
    }


def execute_target_profile(receiver, value):
    return receiver.execute(value)


def execute_vector_selection_profile(receiver, inventory, query, targets):
    return receiver.execute(inventory, query, targets)


@dataclass
class ContextualTargetPlan:
    prepared: Any
    operation: str
    member_contract: str

    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        import inspect

        from .contextual_cpu import execute_contextual_projection_kernel
        from .contextual_operations import contextual_operation_sources
        from .data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_binding
        from .data_operation_prepared_call import PreparedCallResult
        from .identity import canonical_bytes

        if binding is None or binding.subject_context is None:
            raise ValueError("contextual target projection requires its actual native context")
        roles = {role.name: role for role in self.port.operation.roles if role.direction == "input"}
        bodies = {
            name: (arguments.arguments[role.parameter],)
            if role.collection == "scalar"
            else tuple(arguments.arguments[role.parameter])
            for name, role in roles.items()
        }
        basis = cpu_input_basis_from_binding(self.port.identity.recipe, binding, bodies)
        kernel = execute_contextual_projection_kernel
        bound = inspect.signature(kernel).bind(
            input_basis=basis,
            operation=self.operation,
            member_contract=self.member_contract,
            check_active=check_active,
        )
        reply = yield from self.port.plan_cpu_reply(
            kernel,
            bound,
            contextual_operation_sources(),
            check_active=check_active,
            execution_owner=execution_owner,
        )
        product = cpu_authority_value(reply.content, expected_basis=basis)
        kind = (
            "DdoContextualTargetPopulation"
            if self.operation
            in {"retrieve.contextual_targets/curated", "retrieve.contextual_targets/components"}
            else "DdoContextualTarget"
            if self.operation == "retrieve.contextual_target/declared"
            else "DdoContextualVectors"
        )
        checked = self.prepared.validate_json(kind, json_bytes(product)).model_dump(
            mode="python", exclude_unset=True
        )
        return PreparedCallResult(
            checked,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def resolve_target_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_targets import (
        ContextualTargetOperation,
        ContextualVectorSelectionOperation,
        CuratedContextualTargetsOperation,
        SourceContextualTargetsOperation,
    )

    from .contextual_cpu import execute_contextual_projection_kernel
    from .contextual_operations import contextual_operation_sources, contextual_retrieval_assets
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    classes = (
        ContextualTargetOperation,
        ContextualVectorSelectionOperation,
        CuratedContextualTargetsOperation,
        SourceContextualTargetsOperation,
    )
    selected = model.operation(operation)
    owners = {surface.exposed.rsplit(".", 1)[0] for surface in selected.callable_surfaces}
    found = [kind for kind in classes if kind.__module__ + "." + kind.__qualname__ in owners]
    if len(found) != 1:
        raise PortRefusal("contextual target factory differs from its actual operation")
    receiver = found[0](None)
    member_contract = next(
        item.key
        for item in model.identities
        if item.domain == "kind"
        and item.owner
        == "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetMember"
    )
    plan = ContextualTargetPlan(prepared, operation, member_contract)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.contextual_target_products.ContextualTargetPlan.plan",
        authorize,
        (contextual_retrieval_assets(),),
        contextual_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.contextual_cpu.execute_contextual_projection_kernel",
                execute_contextual_projection_kernel,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port
