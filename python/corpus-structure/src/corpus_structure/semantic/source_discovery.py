"""Mechanical discovery over exact admitted originals, with no inference or recapture."""

from __future__ import annotations

import ast
from collections.abc import Callable
from typing import TYPE_CHECKING
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import yaml

from .data_operation_outcomes import successful_return_outcome
from .identity import canonical_bytes
from .original_documents import original_document_subject
from .source_products import FrozenNativeSource, source_product_inputs, source_subject
from .types import SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from .data_operation_admission import PreparedCapabilityIdentity
    from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
    from .python_operation_sources import PythonSourceCollection
    from .types import PreparedRelease

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-source-discovery.yaml"


def source_discovery_inputs(bundle):
    bundle = source_product_inputs(bundle)
    name, root = "data_operation_source_discovery", "data_operation_source_discovery_root"
    if {name, root} & {item.name for item in bundle.sources}:
        raise ValueError("source discovery inputs use reserved schema names")
    return SourceBundle(root, (
        *bundle.sources, SourceArtifact(name, _MODEL.read_bytes()),
        SourceArtifact(root, yaml.safe_dump({"id": "urn:corpus:source-discovery-root", "name": root, "imports": [bundle.root, name]}).encode()),
    ))


def selected_source_population(original, views, *, complete, kind_contract):
    """Close only the supplied selection; preserve distinct scoped source members."""
    if type(complete) is not bool:
        raise TypeError("source discovery requires explicit complete/partial standing")
    document = original["document"]
    members, seen = [], set()
    for view in views:
        coordinate = view["source"]
        if coordinate["document"] != document:
            raise ValueError("source discovery cannot combine different original documents")
        identifier = source_subject(coordinate)
        context = {"subject": identifier, "original_source": document,
                   "analyzed_scope": {"source": coordinate, "selectors": view["selectors"]}}
        key = canonical_bytes(context)
        if key in seen:
            raise ValueError("source discovery repeats a complete selected source context")
        seen.add(key)
        members.append({"member_id": "selected-source-view:" + sha256(key).hexdigest(), "kind_contract": kind_contract,
                        "context": context, "body": view})
    members.sort(key=lambda value: canonical_bytes(value["context"]))
    return {"document": document, "complete": complete, "members": members}


@dataclass(frozen=True)
class SourceViewPopulation:
    content: bytes


@dataclass(frozen=True)
class PreparedSourceDiscovery:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel

    def project(self, original, views, complete):
        original = self.prepared.validate_python("DdoOriginalDocument", original).model_dump(mode="json")
        values = tuple(FrozenNativeSource.acquire(self.prepared, view).value for view in views)
        kind = self.prepared.index.definitions["DdoSelectedNativeSource"].iri
        kind_contract = next(item.key for item in self.model.identities if item.owner == kind and item.domain == "kind")
        value = selected_source_population(original, values, complete=complete, kind_contract=kind_contract)
        checked = self.prepared.validate_json("DdoSourceViewPopulation", canonical_bytes(value))
        return SourceViewPopulation(canonical_bytes(checked.model_dump(mode="json", exclude_unset=True)))


def execute_source_discovery(receiver, original, views, complete):
    return receiver.profile.project(original, views, complete)


def source_discovery_assets():
    module = ast.parse(Path(__file__).read_bytes())
    names = {"selected_source_population", "PreparedSourceDiscovery"}
    selected = tuple((node.name, ast.dump(node, include_attributes=False)) for node in module.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names)
    source = ast.parse(Path(__file__).with_name("source_products.py").read_bytes())
    source_names = {"source_subject", "FrozenNativeSource", "native_projection_identity", "_projection_body", "_native_atoms", "NativeSourceSelectorIndex", "_values"}
    algorithms = tuple((node.name, ast.dump(node, include_attributes=False)) for node in source.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in source_names)
    if {name for name, _ in algorithms} != source_names:
        raise ValueError("source discovery lacks its complete source interpretation")
    return SourceArtifact("source-discovery/profile-assets", canonical_bytes({"version": "source-discovery-assets-ast-v1", "projection": selected, "model": _MODEL.read_bytes().hex(), "source": algorithms, "document_address": Path(__file__).with_name("original_documents.py").read_bytes().hex()}))


def source_discovery_custody():
    return SourceArtifact("source-discovery/execution-custody", Path(__file__).read_bytes())


def source_discovery_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    path = Path(__file__).parents[1] / "methods/source_discovery.py"
    return PythonSourceCollection((PythonSource("corpus_structure.semantic.source_discovery", Path(__file__).read_bytes(), str(Path(__file__))), PythonSource("corpus_structure.methods.source_discovery", path.read_bytes(), str(path)),), boundary_contracts=(source_discovery_assets(), source_discovery_custody()))


@dataclass(frozen=True)
class PreparedSourceDiscoveryPort:
    identity: PreparedCapabilityIdentity
    operation: EffectiveOperation
    profile: PreparedSourceDiscovery
    authorize: Callable[[PreparedCapabilityIdentity], None]
    custody: tuple[SourceArtifact, ...]
    sources: PythonSourceCollection

    native_selections = ()

    @property
    def logical_signature(self):
        import inspect
        from corpus_structure.methods.source_discovery import SelectedSourceViewsOperation

        signature = inspect.signature(SelectedSourceViewsOperation.run, eval_str=True)
        return signature.replace(parameters=tuple(signature.parameters.values())[1:])

    def _verify(self):
        from corpus_structure.methods.source_discovery import SelectedSourceViewsOperation
        from .data_operation_prepared_products import verify_prepared_product

        verify_prepared_product(self.identity, self.profile.model, self.operation, self.sources, self.custody,
            assets=(source_discovery_assets(), source_discovery_custody()),
            functions=((self.operation.callable_surfaces[0].declaration, SelectedSourceViewsOperation.run),
                       ("corpus_structure.semantic.source_discovery.execute_source_discovery", execute_source_discovery),
                       ("corpus_structure.semantic.source_discovery.PreparedSourceDiscovery.project", PreparedSourceDiscovery.project),
                       ("corpus_structure.semantic.source_discovery.selected_source_population", selected_source_population)),
            authorize=self.authorize, required_sources=source_discovery_operation_sources())

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        # This bounded, read-only projection has no physical submission or provider wait.
        yield from ()
        return self.invoke_python(values, binding=binding, check_active=check_active)

    def invoke_python(self, values, *, binding=None, check_active=lambda: None):
        from .data_operation_identity import decode_semantic_value, semantic_value
        from .data_operation_ports import PortCompletion, PortRefusal, RoleValue, _untrusted_value, project_product_members

        self._verify()
        check_active()
        if binding is None or not binding.sufficient or binding.operation != self.operation.semantic_id:
            raise PortRefusal("source discovery requires an admitted sufficient binding")
        roles = {value.role: value for value in values}
        if len(roles) != len(values) or "original" not in roles or set(roles) - {"original", "views"}:
            raise PortRefusal("source discovery requires exactly its original and selected-view roles")
        ids = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        for role in self.operation.roles:
            if role.direction == "input" and role.name in roles and roles[role.name].kind_contract != ids[role.kind, "kind"]:
                raise PortRefusal("source discovery input has another nominal kind")
        original = _untrusted_value(roles["original"].value)
        if "views" in roles:
            views = _untrusted_value(roles["views"].value)
        else:
            absent = [role for role in binding.roles if role.role == "views"]
            if len(absent) != 1 or absent[0].state != "known-absent":
                raise PortRefusal("source discovery lacks its exact selected view population")
            views = ()
        parameters = decode_semantic_value(json.loads(binding.parameters))
        if set(parameters) != {"complete"} or binding.subject != original_document_subject(original["document"]):
            raise PortRefusal("source discovery lacks its frozen selection standing or document subject")
        product = self.profile.project(original, tuple(views), parameters["complete"])
        output = next(role for role in self.operation.roles if role.direction == "output")
        body = self.profile.prepared.validate_json("DdoSourceViewPopulation", product.content).model_dump(mode="python", exclude_unset=True)
        check_active()
        self._verify()
        return PortCompletion(self.operation.semantic_id,
            (RoleValue(output.name, ids[output.kind, "kind"], product.content, canonical_bytes(semantic_value(body)), project_product_members(self.profile.model, output.kind, body)),),
            outcome=successful_return_outcome(self.operation))


def resolve_source_discovery_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    if selected.profile != "discovery" or selected.effects or selected.capabilities.forms != ("scalar",):
        raise PortRefusal("source population requires its declared read-only scalar discovery profile")
    port = PreparedSourceDiscoveryPort(identity, selected, PreparedSourceDiscovery(prepared, model), authorize, custody, sources)
    port._verify()
    return port
