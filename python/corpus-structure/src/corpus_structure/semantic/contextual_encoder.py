"""Explicit CPU encoder acquisition and source-native contextual query production."""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, dataclass
from hashlib import file_digest
from pathlib import Path
from typing import Any

from corpus_structure.methods.contextual_embeddings import EncoderProfile

from .identity import canonical_bytes
from .types import SourceArtifact

_ROOT = Path(__file__).parents[1]
_FILES = ("methods/contextual_encoding.py", "semantic/contextual_encoder.py", "methods/contextual_embeddings.py", "methods/contextual_candidates.py", "semantic/declared_record_sources.py", "semantic/source_contexts.py")


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
                    artifacts.append((path.relative_to(root).as_posix(), file_digest(source, "sha256").hexdigest()))
        if not artifacts or not {"config.json", "modules.json"} <= {name for name, _ in artifacts}:
            raise ValueError("contextual encoder snapshot lacks actual model/module configuration")
        return cls(profile, root, tuple(artifacts))


def contextual_encoder_assets(selection):
    return SourceArtifact("contextual/encoder-assets", canonical_bytes({"version": "contextual-owned-cpu-encoder-1", "profile": asdict(selection.profile), "artifacts": selection.artifacts, "device": "cpu", "dtype": "float32", "files": [(name, (_ROOT / name).read_bytes().hex()) for name in _FILES]}))


def contextual_encoder_custody(selection):
    return SourceArtifact("contextual/encoder-custody", canonical_bytes({"model_path": str(selection.model_path), "profile": asdict(selection.profile), "artifacts": selection.artifacts}))


def contextual_encoder_operation_sources(selection, *, include_dependencies=True):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    own = PythonSourceCollection(tuple(PythonSource("corpus_structure." + name.removesuffix(".py").replace("/", "."), (_ROOT / name).read_bytes(), str((_ROOT / name).resolve())) for name in _FILES[:2]), boundary_contracts=(contextual_encoder_assets(selection), contextual_encoder_custody(selection)))
    if not include_dependencies:
        return own
    from .contextual_operations import contextual_operation_sources
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(contextual_operation_sources(), own)


def execute_contextual_encoder_profile(receiver, source, occurrence, inventory):
    return receiver.execute(source, occurrence, inventory)


def execute_contextual_encoder_kernel(frame_record: dict, occurrence: dict, inventory: dict, profile_record: dict, model_path: str, artifacts: tuple[tuple[str, str], ...], *, check_active) -> dict[str, dict]:
    from pydantic import TypeAdapter

    from corpus_structure.methods.contextual_candidates import retained_occurrences
    from corpus_structure.methods.contextual_embeddings import ContextInput, encode_contexts

    from .contextual_operations import admitted_contextual_inventory
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
    products, contexts, _ = retained_occurrences({"contributions": (occurrence,)}, nodes, pin, operation_identity("contextual-owned-cpu-encoder-1", occurrence["contribution_id"], pin), required_occurrence_ids=(occurrence["occurrence_id"],))
    if len(products) != 1 or len(contexts) != 1:
        raise ValueError("contextual encoder requires exactly one retained native occurrence")
    text, start, end, mention = contexts[occurrence["occurrence_id"]]
    selected = admitted_contextual_inventory(inventory)
    profile = TypeAdapter(EncoderProfile).validate_python(profile_record)
    inputs = [ContextInput(occurrence["occurrence_id"], pin["source"], "query", mention, text, start, end)]
    for target in selected.targets:
        inputs.append(ContextInput(target.target_id, target.source_binding, "document", target.label, target.label + "\n" + target.description, 0, len(target.label), parent=target.parent or "", heading=("Aliases: " + ", ".join(target.aliases)) if target.aliases else "", type_name=target.type_name, representation_digest=target.representation_digest))
    encoded = encode_contexts(inputs, profile, model_path=model_path, artifact_hashes=artifacts, check_active=check_active)
    query = next(value for value in encoded.vectors if value.object_id == occurrence["occurrence_id"])
    if encoded.limited_query_ids or len(encoded.vectors) != len(inputs):
        raise ValueError("contextual encoder did not complete its selected vector population")
    return {"query": {"source_pin": pin, "occurrence_id": occurrence["occurrence_id"], "lexical_query": mention, "query_vector_id": query.vector_id, "anchors": products[0]["anchors"]}, "vectors": {"profile": source_value(asdict(profile)), "vectors": source_value([asdict(value) for value in encoded.vectors])}}


@dataclass
class ContextualEncoderPlan:
    prepared: Any
    selection: ContextualEncoderSelection
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult
        from .declared_record_sources import DeclaredNativeFrameSource

        if binding is None or binding.subject_context is None:
            raise ValueError("contextual encoder requires its acquired native source context")
        source = self.prepared.validate_json("DdoSelectedNativeSource", json_bytes(arguments.arguments["source"])).model_dump(mode="python", exclude_unset=True)
        occurrence = self.prepared.validate_json("DdoCandidateSourceContribution", json_bytes(arguments.arguments["occurrence"])).model_dump(mode="python", exclude_unset=True)
        inventory = self.prepared.validate_json("DdoContextualInventory", json_bytes(arguments.arguments["inventory"])).model_dump(mode="python", exclude_unset=True)
        members = next(role.members for role in binding.roles if role.role == "source")
        if len(members) != 1 or members[0].multiplicity != 1:
            raise ValueError("contextual encoder source differs from its one selected member")
        frame = DeclaredNativeFrameSource.acquire(self.prepared, source, members[0], project=binding.subject_context.project_id)
        signature = inspect.signature(execute_contextual_encoder_kernel, eval_str=True)
        bound = signature.bind(frame_record=frame.record, occurrence=occurrence, inventory=inventory, profile_record=asdict(self.selection.profile), model_path=str(self.selection.model_path), artifacts=self.selection.artifacts, check_active=check_active)
        captured = contextual_encoder_operation_sources(self.selection, include_dependencies=False)
        descriptor = PythonCPUDescriptor(tuple((source.module, source.filename, source.content) for source in captured.sources), "corpus_structure.semantic.contextual_encoder.execute_contextual_encoder_kernel", (), verification="prepared-kernel", control_parameter="check_active")
        reply = yield from plan_cpu_call(descriptor, bound, signature, verify=self.port._verify, execution_owner=execution_owner, check_active=check_active)
        result = json.loads(reply.content)
        products = {name: self.prepared.validate_json(class_name, json_bytes(result[name])).model_dump(mode="python", exclude_unset=True) for name, class_name in (("query", "DdoContextualQuery"), ("vectors", "DdoContextualVectors"))}
        return PreparedCallResult(products, cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()))


def resolve_contextual_encoder_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_encoding import ContextualEncodingOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    acquired = {asset.name: asset for asset in custody}
    if "contextual/encoder-custody" not in acquired:
        raise PortRefusal("contextual encoder lacks its explicitly acquired CPU model")
    value = json.loads(acquired["contextual/encoder-custody"].content)
    selection = ContextualEncoderSelection(EncoderProfile(**value["profile"]), Path(value["model_path"]), tuple(tuple(row) for row in value["artifacts"]))
    selected = model.operation(operation)
    if selected.semantic_id != ContextualEncodingOperation.__data_operation__["id"] or not selection.artifacts:
        raise PortRefusal("contextual encoder factory differs from its acquired operation/model")
    receiver = ContextualEncodingOperation(None)
    plan = ContextualEncoderPlan(prepared, selection)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody, receiver.run, plan.plan, "corpus_structure.semantic.contextual_encoder.ContextualEncoderPlan.plan", authorize, (contextual_encoder_assets(selection), contextual_encoder_custody(selection)), contextual_encoder_operation_sources(selection, include_dependencies=False), functions=(("corpus_structure.semantic.contextual_encoder.execute_contextual_encoder_kernel", execute_contextual_encoder_kernel),), requires_prepared_schema=True)
    plan.port = port
    return port
