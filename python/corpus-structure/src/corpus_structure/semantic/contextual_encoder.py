"""Explicit CPU encoder acquisition and source-native contextual query production."""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, dataclass
from hashlib import file_digest
from pathlib import Path
from typing import Any, TypedDict

from corpus_structure.methods.contextual_embeddings import (
    ENCODER_NUMERICS,
    EncoderNumericalPolicy,
    EncoderProfile,
)

from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import SourceArtifact

_ROOT = Path(__file__).parents[1]
_FILES = (
    "methods/contextual_encoding.py",
    "semantic/contextual_encoder.py",
    "methods/contextual_embeddings.py",
    "methods/contextual_candidates.py",
    "semantic/declared_record_sources.py",
    "semantic/declared_structural_references.py",
    "semantic/source_contexts.py",
    "methods/contextual_query.py",
    "methods/pm2_dipo_products.py",
    "semantic/declared_formal_readings.py",
    "semantic/contextual_target_products.py",
    "semantic/contextual_cpu.py",
    "semantic/characterization.py",
    "semantic/data_product_reference.py",
)


@dataclass(frozen=True)
class ContextualEncoderSelection:
    profile: EncoderProfile
    model_path: Path
    artifacts: tuple[tuple[str, str], ...]

    @classmethod
    def acquire(cls, profile, model_path):
        """Capture an existing local snapshot; no download, process or model allocation."""
        root = Path(model_path).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("contextual encoder requires its acquired local model directory")
        artifacts = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                with path.open("rb") as source:
                    artifacts.append(
                        (
                            path.relative_to(root).as_posix(),
                            file_digest(source, "sha256").hexdigest(),
                        )
                    )
        if not artifacts or not {"config.json", "modules.json"} <= {name for name, _ in artifacts}:
            raise ValueError("contextual encoder snapshot lacks actual model/module configuration")
        return cls(profile, root, tuple(artifacts))


def contextual_encoder_assets(selection):
    return SourceArtifact(
        "contextual/encoder-assets",
        canonical_bytes(
            {
                "version": "contextual-owned-cpu-encoder-2",
                "profile": asdict(selection.profile),
                "artifacts": selection.artifacts,
                "numerical_policy": ENCODER_NUMERICS.model_dump(mode="json"),
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/contextual_encoding.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _FILES
                ],
            }
        ),
    )


def contextual_encoder_custody(selection):
    return SourceArtifact(
        "contextual/encoder-custody",
        canonical_bytes(
            {
                "model_path": str(selection.model_path),
                "numerical_policy": ENCODER_NUMERICS.model_dump(mode="json"),
                "profile": asdict(selection.profile),
                "artifacts": selection.artifacts,
            }
        ),
    )


def contextual_encoder_declarations():
    from .data_operation_model import MODEL_VERSION
    from .nominal_schema_kinds import nominal_schema_kinds

    return SourceArtifact(
        "contextual/encoder-policy-kinds",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": nominal_schema_kinds(
                    EncoderNumericalPolicy.model_json_schema(),
                    namespace="urn:corpus:kind:contextual-encoder:",
                    root_name="NumericalPolicy",
                ),
            }
        ),
    )


def contextual_encoder_operation_sources(
    selection, *, include_dependencies=True, numerical_policy=None
):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    own = PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in _FILES[:2]
        ),
        boundary_contracts=(
            contextual_encoder_assets(selection),
            contextual_encoder_custody(selection),
        ),
    )
    if not include_dependencies:
        return own
    from .contextual_operations import contextual_operation_sources
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(contextual_operation_sources(numerical_policy), own)


def execute_contextual_encoder_profile(receiver, source, occurrence):
    return receiver.execute(source, occurrence)


def execute_selected_context_encoder_profile(
    receiver, source, occurrence, primary, context_selection
):
    return receiver.execute(source, occurrence, primary, context_selection)


def execute_target_encoder_profile(receiver, target):
    return receiver.execute(target)


def execute_target_encoder_kernel(target, profile_record, model_path, artifacts, *, check_active):
    from pydantic import TypeAdapter

    from corpus_structure.methods.contextual_embeddings import encode_contexts

    from .contextual_retrieval import TargetRepresentation
    from .contextual_target_products import target_encoding_input
    from .observations import source_python, source_value

    descriptor = TypeAdapter(TargetRepresentation).validate_python(
        source_python(target["descriptor"])
    )
    profile = TypeAdapter(EncoderProfile).validate_python(profile_record)
    result = encode_contexts(
        (target_encoding_input(descriptor),),
        profile,
        model_path=model_path,
        artifact_hashes=artifacts,
        check_active=check_active,
    )
    if result.limited_query_ids or len(result.vectors) != 1 or len(result.inputs) != 1:
        raise ValueError("target encoder did not produce its one exact target")
    return {
        "original_source": target.get("original_source"),
        "target": target,
        "profile": source_value(asdict(profile)),
        "vector": asdict(result.vectors[0]),
        "rendered": asdict(result.inputs[0]),
    }


def execute_target_encoder_authority_kernel(
    input_basis: list,
    profile_record: dict,
    model_path: str,
    artifacts: tuple[tuple[str, str], ...],
    *,
    check_active,
) -> dict:
    from .contextual_target_products import materialize_target
    from .data_operation_cpu_basis import cpu_authority_reply, cpu_basis_values

    roles, context = cpu_basis_values(input_basis, scalar_roles=("target",), set_roles=())
    rows = roles.get("target", ())
    target = materialize_target(rows[0].body, context=context)
    result = execute_target_encoder_kernel(
        target, profile_record, model_path, artifacts, check_active=check_active
    )
    return cpu_authority_reply(input_basis, result)


def execute_query_encoder_authority_kernel(
    input_basis: list,
    frame_record: dict,
    profile_record: dict,
    model_path: str,
    artifacts: tuple[tuple[str, str], ...],
    *,
    check_active,
) -> dict:
    from .data_operation_cpu_basis import cpu_authority_reply, cpu_basis_values
    from .data_operation_identity import decode_semantic_value
    from .data_operation_model import json_context_meaning

    roles, _ = cpu_basis_values(input_basis, scalar_roles=("source", "occurrence"), set_roles=(), sequence_roles=("primary",))
    source = roles["source"][0]
    from .contextual_cpu import checked_frame_source

    frame = checked_frame_source(frame_record, source)
    occurrence = roles["occurrence"][0].body
    parameters = decode_semantic_value(input_basis)["parameters"]
    selected = parameters.get("context_selection")
    query_context, context_inputs = None, ()
    if selected is not None:
        if not roles["primary"]:
            raise ValueError("selected query requires its complete processed primary population")
        query_context, context_inputs = prepare_primary_query_context(
            frame,
            occurrence,
            roles["primary"],
            recipe=selected["recipe"],
            evidence=selected["evidence"],
        )
    elif roles["primary"]:
        raise ValueError("lexical query cannot silently consume unrequested primary context")
    result = execute_contextual_encoder_kernel(
        frame_record,
        occurrence,
        profile_record,
        model_path,
        artifacts,
        check_active=check_active,
        query_context_record=query_context,
        context_inputs=context_inputs,
    )
    from .declared_structural_references import DeclaredContributionRef

    occurrence_input = roles["occurrence"][0]
    result["query"]["carrier"] = DeclaredContributionRef(
        product_id=occurrence_input.product_id,
        member_id=occurrence_input.member_id,
        kind_contract=occurrence_input.kind_contract,
        project_id=occurrence_input.context.project_id,
        subject=occurrence_input.context.subject,
        subject_definition=occurrence_input.context.subject_definition,
        original_source=occurrence_input.context.original_source,
        analyzed_scope_meaning=json_context_meaning(
            occurrence_input.context.analyzed_scope
        ).decode(),
        contribution_id=occurrence["contribution_id"],
    ).model_dump(mode="python", exclude_none=True)
    return cpu_authority_reply(input_basis, result)


def checked_primary_query_rows(primary, *, binding):
    """Validate native selection before sharing the actual typed primary inputs."""
    from .data_operation_cpu_basis import CPUInputRole
    from .data_operation_json import json_loads
    from .data_operation_model import SubjectContext

    roles = [role for role in binding.roles if role.role == "primary"]
    if (
        len(roles) != 1
        or roles[0].state != "present"
        or not roles[0].members
        or len(roles[0].members) != len(primary)
    ):
        raise ValueError("query context lacks its actual complete primary binding")
    entries = json_loads(binding.source_sets).get("query-context-primary", ())
    wanted = {(row["product"], row["member"]) for row in entries}
    actual = {(row.product, row.member) for row in roles[0].members}
    if (
        actual != wanted
        or len(actual) != len(primary)
        or any(member is not None for _, member in actual)
    ):
        raise ValueError("query context requires its exact frozen parent-product closure")
    rows = tuple(
        CPUInputRole(
            "primary",
            member.position,
            member.multiplicity,
            member.product,
            member.member,
            member.kind_contract,
            SubjectContext(
                binding.subject_context.project_id,
                member.subject,
                member.original_source,
                member.analyzed_scope,
                subject_definition=member.subject_definition,
            ),
            body,
            member.support_references,
        )
        for member, body in zip(roles[0].members, primary, strict=True)
    )
    return rows


def prepare_selected_query_context(frame, occurrence, primary, *, binding, recipe, evidence):
    return prepare_primary_query_context(
        frame,
        occurrence,
        checked_primary_query_rows(primary, binding=binding),
        recipe=recipe,
        evidence=evidence,
    )


def prepare_primary_query_context(frame, occurrence, rows, *, recipe, evidence):
    """Shared query12 projection over actual CPU/native primary role facts."""
    from corpus_structure.methods.contextual_query import (
        DeclaredQueryContextBinding,
        DeclaredQueryContextSelection,
        resolve_query_contexts,
    )

    from .data_operation_identity import semantic_value
    from .data_operation_json import json_bytes
    from .data_operation_model import json_context_meaning
    from .data_operation_support import ComputationalSupportReference
    from .data_product_reference import (
        DataProductMemberReference,
        DataProductReference,
        read_member_reference,
    )
    from .declared_formal_readings import SelectedCharacterizationInventories
    from .observations import source_value
    from .source_contexts import PreparedNativeSources

    selected = read_member_reference(evidence)
    if not isinstance(selected, DataProductMemberReference):
        raise ValueError("query context requires a genuine selected semantic member")
    selection = DeclaredQueryContextSelection(
        recipe, (DeclaredQueryContextBinding(occurrence["occurrence_id"], selected),)
    )
    products, inputs = {}, []
    for row in rows:
        if (
            row.role != "primary"
            or row.multiplicity != 1
            or row.member_id is not None
            or not any(
                isinstance(reference, ComputationalSupportReference) for reference in row.support
            )
        ):
            raise ValueError("query context primary lacks its genuine computational support")
        if (
            row.body.get("source") != frame.value["source"]
            or row.body.get("selectors") != frame.value["selectors"]
        ):
            raise ValueError("query context primary belongs to another original source/scope")
        products[row.product_id] = dict(canonical_body=semantic_value(row.body))
        inputs.append(
            dict(
                product_id=row.product_id,
                reference=json_bytes([row.product_id, None]).decode(),
                kind_contract=row.kind_contract,
                project_id=row.context.project_id,
                subject=row.context.subject,
                subject_definition=row.context.subject_definition,
                original_source=row.context.original_source,
                analyzed_scope_meaning=json_context_meaning(row.context.analyzed_scope).decode(),
            )
        )
    inventories = SelectedCharacterizationInventories(products)
    reachable, pending = set(), [selected.product]
    while pending:
        product = pending.pop()
        if product in reachable:
            continue
        if product not in inventories:
            raise ValueError("query context lacks its exact selected dependency closure")
        reachable.add(product)
        pending.extend(
            DataProductReference(row["product_id"])
            for row in inventories[product].payload.get("dependencies", ())
        )
    if reachable != {DataProductReference(product) for product in products}:
        raise ValueError("query context includes unrelated primary products")
    located = resolve_query_contexts(
        selection, inventories, (occurrence,), frame, preparation=PreparedNativeSources((frame,))
    )[occurrence["occurrence_id"]]
    if not located.signals or not located.rendered or not located.representation_digest:
        raise ValueError(
            "requested located query context is unavailable; lexical fallback is forbidden"
        )
    return dict(
        recipe=recipe,
        report=source_value(located.report()),
        rendered=located.rendered,
        representation_digest=located.representation_digest,
    ), tuple(inputs)


class EncodedQueryContext(TypedDict):
    recipe: str
    report: dict[str, Any]
    rendered: str
    representation_digest: str


def checked_encoded_query_context(context) -> EncodedQueryContext:
    """Preserve named context identity; absence is only the explicit lexical recipe."""
    from corpus_structure.methods.contextual_embeddings import identity

    from .observations import source_python, source_value

    if context is None:
        return dict(
            recipe="lexical-native-1",
            report=source_value(None),
            rendered="",
            representation_digest="",
        )
    report = source_python(context["report"])
    if (
        context["recipe"]
        not in {"located-frame-2", "located-referent-2", "located-discourse-neighbor-2"}
        or not isinstance(report, dict)
        or report.get("recipe") != context["recipe"]
        or not context["rendered"]
        or context["representation_digest"] != identity("located-query-context", report)
    ):
        raise ValueError("encoded query context differs from its exact selected representation")
    return dict(
        recipe=context["recipe"],
        report=context["report"],
        rendered=context["rendered"],
        representation_digest=context["representation_digest"],
    )


def execute_contextual_encoder_kernel(
    frame_record: dict,
    occurrence: dict,
    profile_record: dict,
    model_path: str,
    artifacts: tuple[tuple[str, str], ...],
    *,
    check_active,
    query_context_record: dict | None = None,
    context_inputs: tuple[dict, ...] = (),
) -> dict[str, dict]:
    from pydantic import TypeAdapter

    from corpus_structure.methods.contextual_candidates import retained_occurrences
    from corpus_structure.methods.contextual_embeddings import ContextInput, encode_contexts

    from .contributions import operation_identity
    from .declared_record_sources import DeclaredNativeFrameSource
    from .observations import source_value

    frame = DeclaredNativeFrameSource(**frame_record)
    pin = frame.pin.values()
    if occurrence["pin"] != pin:
        raise ValueError("contextual occurrence belongs to another selected native source")
    native = json.loads(frame.native_context)
    nodes = {node.get("self_ref", node.get("pointer")): node for node in native["items"]}
    for pointer, node in tuple(nodes.items()):
        for index, cell in enumerate(node.get("data", {}).get("table_cells", ())):
            nodes[f"{pointer}/data/table_cells/{index}"] = cell
    products, contexts, _ = retained_occurrences(
        {"contributions": (occurrence,)},
        nodes,
        pin,
        operation_identity("contextual-owned-cpu-encoder-1", occurrence["contribution_id"], pin),
        required_occurrence_ids=(occurrence["occurrence_id"],),
    )
    if len(products) != 1 or len(contexts) != 1:
        raise ValueError("contextual encoder requires exactly one retained native occurrence")
    text, start, end, mention = contexts[occurrence["occurrence_id"]]
    profile = TypeAdapter(EncoderProfile).validate_python(profile_record)
    query_context = checked_encoded_query_context(query_context_record)
    if (query_context_record is None) != (not context_inputs):
        raise ValueError("encoded query context differs from its retained primary inputs")
    inputs = [
        ContextInput(
            occurrence["occurrence_id"],
            pin["source"],
            "query",
            mention,
            text,
            start,
            end,
            representation_digest=query_context["representation_digest"],
            query_context=query_context["rendered"] if query_context_record is not None else None,
        )
    ]
    encoded = encode_contexts(
        inputs, profile, model_path=model_path, artifact_hashes=artifacts, check_active=check_active
    )
    query = next(
        value for value in encoded.vectors if value.object_id == occurrence["occurrence_id"]
    )
    if encoded.limited_query_ids or len(encoded.vectors) != len(inputs):
        raise ValueError("contextual encoder did not complete its selected vector population")
    return {
        "query": {
            "source_pin": pin,
            "occurrence_id": occurrence["occurrence_id"],
            "lexical_query": mention,
            "query_vector_id": query.vector_id,
            "anchors": products[0]["anchors"],
            "context": query_context,
            "context_inputs": list(context_inputs),
        },
        "vector": {
            "original_source": pin["original_source"],
            "profile": source_value(asdict(profile)),
            "vector": asdict(query),
            "rendered": asdict(encoded.inputs[0]),
        },
    }


@dataclass
class ContextualEncoderPlan:
    prepared: Any
    selection: ContextualEncoderSelection
    port: Any = None
    selected_context: bool = False

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult
        from .declared_record_sources import DeclaredNativeFrameSource

        if binding is None or binding.subject_context is None:
            raise ValueError("contextual encoder requires its acquired native source context")
        source = self.prepared.validate_json(
            "DdoSelectedNativeSource", json_bytes(arguments.arguments["source"])
        ).model_dump(mode="python", exclude_unset=True)
        occurrence = self.prepared.validate_json(
            "DdoCandidateSourceContribution", json_bytes(arguments.arguments["occurrence"])
        ).model_dump(mode="python", exclude_unset=True)
        members = next(role.members for role in binding.roles if role.role == "source")
        if len(members) != 1 or members[0].multiplicity != 1:
            raise ValueError("contextual encoder source differs from its one selected member")
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, source, members[0], project=binding.subject_context.project_id
        )
        from .data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_binding

        bodies = {"source": (source,), "occurrence": (occurrence,)}
        if self.selected_context:
            selection = arguments.arguments["context_selection"]
            prepare_selected_query_context(
                frame,
                occurrence,
                arguments.arguments["primary"],
                binding=binding,
                recipe=selection["recipe"],
                evidence=selection["evidence"],
            )
            bodies["primary"] = tuple(arguments.arguments["primary"])
        basis = cpu_input_basis_from_binding(self.port.identity.recipe, binding, bodies)
        kernel = execute_query_encoder_authority_kernel
        bound = inspect.signature(kernel).bind(
            input_basis=basis,
            frame_record=frame.record,
            profile_record=asdict(self.selection.profile),
            model_path=str(self.selection.model_path),
            artifacts=self.selection.artifacts,
            check_active=check_active,
        )
        captured = contextual_encoder_operation_sources(self.selection, include_dependencies=False)
        reply = yield from self.port.plan_cpu_reply(
            kernel,
            bound,
            captured,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        result = cpu_authority_value(reply.content, expected_basis=basis)
        products = {
            name: self.prepared.validate_json(class_name, json_bytes(result[name])).model_dump(
                mode="python", exclude_unset=True
            )
            for name, class_name in (
                ("query", "DdoContextualQuery"),
                ("vector", "DdoContextualQueryVector"),
            )
        }
        return PreparedCallResult(
            products,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


@dataclass
class ContextualTargetEncoderPlan:
    prepared: Any
    selection: ContextualEncoderSelection
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .contextual_target_products import materialize_target
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("target encoder requires its acquired target context")
        target = self.prepared.validate_json(
            "DdoContextualTarget", json_bytes(arguments.arguments["target"])
        ).model_dump(mode="python", exclude_unset=True)
        materialize_target(target, context=binding.subject_context)
        from .data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_binding

        basis = cpu_input_basis_from_binding(
            self.port.identity.recipe, binding, {"target": (target,)}
        )
        kernel = execute_target_encoder_authority_kernel
        bound = inspect.signature(kernel).bind(
            input_basis=basis,
            profile_record=asdict(self.selection.profile),
            model_path=str(self.selection.model_path),
            artifacts=self.selection.artifacts,
            check_active=check_active,
        )
        reply = yield from self.port.plan_cpu_reply(
            kernel,
            bound,
            contextual_encoder_operation_sources(self.selection, include_dependencies=False),
            execution_owner=execution_owner,
            check_active=check_active,
        )
        result = self.prepared.validate_json(
            "DdoContextualTargetVector",
            json_bytes(cpu_authority_value(reply.content, expected_basis=basis)),
        ).model_dump(mode="python", exclude_unset=True)
        return PreparedCallResult(
            result,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def resolve_contextual_encoder_port(
    prepared, model, operation, *, identity, authorize, custody, sources
):
    from corpus_structure.methods.contextual_encoding import (
        ContextualEncodingOperation,
        ContextualTargetEncodingOperation,
        SelectedContextEncodingOperation,
    )

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    acquired = {asset.name: asset for asset in custody}
    if "contextual/encoder-custody" not in acquired:
        raise PortRefusal("contextual encoder lacks its explicitly acquired CPU model")
    value = json.loads(acquired["contextual/encoder-custody"].content)
    if value["numerical_policy"] != ENCODER_NUMERICS.model_dump(mode="json"):
        raise PortRefusal("encoder numerical policy differs from acquired implementation")
    selection = ContextualEncoderSelection(
        EncoderProfile(**value["profile"]),
        Path(value["model_path"]),
        tuple((name, digest) for name, digest in value["artifacts"]),
    )
    selected = model.operation(operation)
    owners = {surface.exposed.rsplit(".", 1)[0] for surface in selected.callable_surfaces}
    classes = tuple(
        kind
        for kind in (
            ContextualEncodingOperation,
            SelectedContextEncodingOperation,
            ContextualTargetEncodingOperation,
        )
        if kind.__module__ + "." + kind.__qualname__ in owners
    )
    if len(classes) != 1 or not selection.artifacts:
        raise PortRefusal("contextual encoder factory differs from its acquired operation/model")
    receiver_type = classes[0]
    receiver = receiver_type(None)
    target_encoding = receiver_type is ContextualTargetEncodingOperation
    plan = (
        ContextualTargetEncoderPlan(prepared, selection)
        if target_encoding
        else ContextualEncoderPlan(
            prepared, selection, selected_context=receiver_type is SelectedContextEncodingOperation
        )
    )
    kernel = (
        execute_target_encoder_authority_kernel
        if target_encoding
        else execute_query_encoder_authority_kernel
    )
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.contextual_encoder." + type(plan).__name__ + ".plan",
        authorize,
        (contextual_encoder_assets(selection), contextual_encoder_custody(selection)),
        contextual_encoder_operation_sources(selection, include_dependencies=False),
        functions=(
            (
                "corpus_structure.semantic.contextual_encoder." + kernel.__name__,
                kernel,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port
