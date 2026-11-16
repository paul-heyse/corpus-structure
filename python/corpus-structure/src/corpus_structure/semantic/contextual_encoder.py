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
    "semantic/source_contexts.py",
    "methods/contextual_query.py",
    "methods/pm2_dipo_products.py",
    "semantic/declared_formal_readings.py",
    "semantic/contextual_target_products.py",
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


def prepare_selected_query_context(frame, occurrence, primary, *, binding, recipe, evidence):
    """Project actual bound primary products before any encoder/model allocation."""
    from corpus_structure.methods.contextual_query import (
        DeclaredQueryContextBinding,
        DeclaredQueryContextSelection,
        resolve_query_contexts,
    )

    from .data_operation_identity import semantic_value
    from .data_operation_json import json_bytes, json_loads
    from .data_operation_model import json_context_meaning
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
    roles = [role for role in binding.roles if role.role == "primary"]
    if (
        len(roles) != 1
        or roles[0].state != "present"
        or not roles[0].members
        or len(roles[0].members) != len(primary)
    ):
        raise ValueError("query context lacks its actual complete primary binding")
    source_sets = json_loads(binding.source_sets)
    entries = source_sets.get("query-context-primary", ())
    wanted = {(row["product"], row["member"]) for row in entries}
    actual = {(row.product, row.member) for row in roles[0].members}
    if (
        actual != wanted
        or len(actual) != len(primary)
        or any(member is not None for _, member in actual)
    ):
        raise ValueError("query context requires its exact frozen parent-product closure")
    products, inputs = {}, []
    for member, body in zip(roles[0].members, primary, strict=True):
        if member.multiplicity != 1 or not member.support_episodes:
            raise ValueError("query context primary lacks its genuine computational support")
        if (
            body.get("source") != frame.value["source"]
            or body.get("selectors") != frame.value["selectors"]
        ):
            raise ValueError("query context primary belongs to another original source/scope")
        products[member.product] = dict(canonical_body=semantic_value(body))
        inputs.append(
            dict(
                product_id=member.product,
                reference=json_bytes([member.product, None]).decode(),
                kind_contract=member.kind_contract,
                project_id=binding.subject_context.project_id,
                subject=member.subject,
                subject_definition=member.subject_definition,
                original_source=member.original_source,
                analyzed_scope_meaning=json_context_meaning(member.analyzed_scope).decode(),
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
        query_context, context_inputs = None, ()
        if self.selected_context:
            query_context, context_inputs = prepare_selected_query_context(
                frame,
                occurrence,
                arguments.arguments["primary"],
                binding=binding,
                recipe=arguments.arguments["context_selection"]["recipe"],
                evidence=arguments.arguments["context_selection"]["evidence"],
            )
        signature = inspect.signature(execute_contextual_encoder_kernel, eval_str=True)
        bound = signature.bind(
            frame_record=frame.record,
            occurrence=occurrence,
            profile_record=asdict(self.selection.profile),
            model_path=str(self.selection.model_path),
            artifacts=self.selection.artifacts,
            check_active=check_active,
            query_context_record=query_context,
            context_inputs=context_inputs,
        )
        captured = contextual_encoder_operation_sources(self.selection, include_dependencies=False)
        reply = yield from self.port.plan_cpu_reply(
            execute_contextual_encoder_kernel,
            bound,
            captured,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        result = json.loads(reply.content)
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
            products, cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record())
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
        signature = inspect.signature(execute_target_encoder_kernel, eval_str=True)
        bound = signature.bind(
            target=target,
            profile_record=asdict(self.selection.profile),
            model_path=str(self.selection.model_path),
            artifacts=self.selection.artifacts,
            check_active=check_active,
        )
        reply = yield from self.port.plan_cpu_reply(
            execute_target_encoder_kernel,
            bound,
            contextual_encoder_operation_sources(self.selection, include_dependencies=False),
            execution_owner=execution_owner,
            check_active=check_active,
        )
        result = self.prepared.validate_json("DdoContextualTargetVector", reply.content).model_dump(
            mode="python", exclude_unset=True
        )
        return PreparedCallResult(
            result, cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record())
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
    kernel = execute_target_encoder_kernel if target_encoding else execute_contextual_encoder_kernel
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
    )
    plan.port = port
    return port
