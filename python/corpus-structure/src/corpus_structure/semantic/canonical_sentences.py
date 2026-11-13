"""Acquired cheap canonical members projected from one retained spaCy inventory."""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .data_operation_model import SubjectContext
from .data_operation_outcomes import successful_return_outcome
from .identity import canonical_bytes
from .types import SourceArtifact

if TYPE_CHECKING:
    from .data_operation_admission import PreparedCapabilityIdentity
    from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
    from .types import PreparedRelease


@dataclass(frozen=True)
class CanonicalProduct:
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    kind: str
    subject_context: SubjectContext | None = None

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @property
    def value(self):
        name = next(
            definition.name
            for definition in self.prepared.definitions
            if definition.iri == self.kind
        )
        return self.prepared.validate_json(name, self.content)

    @property
    def reference(self):
        from .data_operation_identity import body_identity, contextual_product_identity
        from .data_product_reference import DataProductReference

        value = self.value.model_dump(mode="python", exclude_unset=True)
        kind = next(
            item.key
            for item in self.model.identities
            if item.owner == self.kind and item.domain == "kind"
        )
        return DataProductReference(
            contextual_product_identity(
                kind=kind, context=self._publication_context(), body=body_identity(value).key
            ).key
        )


def canonical_projection_spec(model, container_kind):
    """Derive constants and fields from the real nominal member graph, never user policy."""
    from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES

    from .data_operation_member_contracts import derive_member_kinds

    kinds = {kind.semantic_id: kind for kind in model.kinds}
    ids = {(item.owner, item.domain): item.key for item in model.identities}
    records = {}
    for owner in derive_member_kinds(model, container_kind):
        properties = [
            json.loads(kinds[edge.target].facts)
            for edge in model.edges
            if edge.source == owner and edge.relation == "property"
        ]
        tags = [
            prop["equals_string"]
            for prop in properties
            if prop["name"] == "record_type" and prop.get("equals_string")
        ]
        if len(tags) != 1 or tags[0] in records:
            raise ValueError("canonical members need distinct actual nominal record discriminators")
        records[tags[0]] = dict(
            kind_contract=ids[owner, "kind"], fields=sorted(prop["name"] for prop in properties)
        )
    if set(records) != {"token", "sentence"}:
        raise ValueError("canonical model must declare exactly sentence and token units")
    return dict(records=records, families=list(SPACY_FAMILIES[:2]))


def canonical_packet_values(inventory: dict, projection: dict) -> dict:
    """One flat typed projection, preserving actual original IDs/context and packet order."""
    packets = [
        {
            "member_id": packet["member_id"],
            "kind_contract": projection["records"][packet["body"]["record_type"]]["kind_contract"],
            "context": packet["context"],
            "body": {
                field: packet["body"][field]
                for field in projection["records"][packet["body"]["record_type"]]["fields"]
                if field in packet["body"]
            },
        }
        for packet in inventory["members"]
    ]
    coverage = [row for row in inventory["coverage"] if row["family"] in projection["families"]]
    return {
        **{key: inventory[key] for key in ("source", "selectors", "block_coverage")},
        "outcome": "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in coverage)
        else "partial",
        "coverage": coverage,
        "members": packets,
    }


@dataclass(frozen=True)
class PreparedCanonicalProfile:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    operation: EffectiveOperation
    projection: bytes
    input_name: str
    output_name: str

    def validate_input(self, value):
        return self.prepared.validate_json(self.input_name, canonical_bytes(value)).model_dump(
            mode="json", exclude_unset=True
        )

    def validate_output(self, value, *, subject_context=None):
        result = self.prepared.validate_json(self.output_name, canonical_bytes(value))
        rows = result.model_dump(mode="python", exclude_unset=True)["members"]
        by_id = {row["member_id"]: row["body"] for row in rows}
        if len(by_id) != len(rows):
            raise ValueError("canonical projection repeats a member")
        for body in by_id.values():
            if body["record_type"] == "sentence" and any(
                token not in by_id
                or by_id[token]["record_type"] != "token"
                or by_id[token].get("sentence_ref") != body["local_id"]
                for token in body["token_ids"]
            ):
                raise ValueError("canonical sentence has no exact retained token membership")
        return CanonicalProduct(
            canonical_bytes(result.model_dump(mode="json", exclude_unset=True)),
            self.prepared,
            self.model,
            next(role.kind for role in self.operation.roles if role.direction == "output"),
            subject_context,
        )

    def project(self, inventory, *, subject_context=None):
        actual = self.validate_input(inventory)
        return self.validate_output(
            canonical_packet_values(actual, json.loads(self.projection)),
            subject_context=subject_context,
        )


def execute_canonical_projection(receiver, inventory):
    return receiver.profile.project(inventory)


def canonical_profile_assets():
    from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES

    source = Path(__file__).read_bytes()
    module = ast.parse(source)
    names = {
        "canonical_packet_values",
        "canonical_projection_spec",
        "PreparedCanonicalProfile",
        "CanonicalProduct",
    }
    selected = [
        (node.name, ast.dump(node, include_attributes=False))
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
    ]
    return SourceArtifact(
        "canonical/profile-assets",
        canonical_bytes(dict(definitions=selected, families=SPACY_FAMILIES[:2])),
    )


def canonical_execution_custody():
    root = Path(__file__).parent
    paths = (
        Path(__file__),
        root / "data_operation_prepared_products.py",
        root / "data_operation_ports.py",
        root / "data_operation_cpu.py",
    )
    return SourceArtifact(
        "canonical/execution-custody",
        canonical_bytes(dict(files=[(path.name, path.read_bytes().hex()) for path in paths])),
    )


def canonical_sentence_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    path = Path(__file__).parents[1] / "methods/canonical_sentences.py"
    return PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.methods.canonical_sentences", path.read_bytes(), str(path)
            ),
        ),
        boundary_contracts=(canonical_profile_assets(), canonical_execution_custody()),
    )


@dataclass(frozen=True)
class PreparedCanonicalPort:
    identity: PreparedCapabilityIdentity
    profile: PreparedCanonicalProfile
    authorize: Any
    custody: tuple[SourceArtifact, ...]
    sources: Any

    @property
    def operation(self):
        return self.profile.operation

    @property
    def native_selections(self):
        return ()

    def _verify(self):
        from corpus_structure.methods.canonical_sentences import CanonicalSentenceProjection

        from .data_operation_ports import project_product_members
        from .data_operation_prepared_products import verify_prepared_product

        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(canonical_profile_assets(), canonical_execution_custody()),
            functions=(
                (self.operation.callable_surfaces[0].declaration, CanonicalSentenceProjection.run),
                (
                    "corpus_structure.semantic.canonical_sentences.execute_canonical_projection",
                    execute_canonical_projection,
                ),
                (
                    "corpus_structure.semantic.canonical_sentences.canonical_packet_values",
                    canonical_packet_values,
                ),
                (
                    "corpus_structure.semantic.canonical_sentences.canonical_projection_spec",
                    canonical_projection_spec,
                ),
                (
                    "corpus_structure.semantic.canonical_sentences.PreparedCanonicalProfile.project",
                    PreparedCanonicalProfile.project,
                ),
                (
                    "corpus_structure.semantic.data_operation_ports.project_product_members",
                    project_product_members,
                ),
            ),
            authorize=self.authorize,
            required_sources=canonical_sentence_operation_sources(),
        )

    def _input(self, values, binding):
        from .data_operation_identity import decode_semantic_value
        from .data_operation_ports import PortRefusal, PythonRoleValue, _untrusted_value
        from .source_products import source_subject

        inputs = [role for role in self.operation.roles if role.direction == "input"]
        kind = next(
            item.key
            for item in self.profile.model.identities
            if item.owner == inputs[0].kind and item.domain == "kind"
        )
        if (
            len(values) != 1
            or not isinstance(values[0], PythonRoleValue)
            or values[0].role != inputs[0].name
            or values[0].kind_contract != kind
        ):
            raise PortRefusal("canonical projection requires its actual nominal inventory role")
        value = self.profile.validate_input(_untrusted_value(values[0].value))
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or binding.definition != self.identity.definition
            or binding.eligibility != self.identity.eligibility
            or binding.subject != source_subject(value["source"])
            or decode_semantic_value(json.loads(binding.parameters)) != {}
        ):
            raise PortRefusal("canonical inventory differs from frozen selected binding")
        return value

    def _complete(self, value, binding=None):
        if binding is not None:
            value = replace(value, subject_context=binding.subject_context)
        from .data_operation_identity import semantic_value
        from .data_operation_ports import PortCompletion, RoleValue, project_product_members

        model_value = value.value
        typed = model_value.model_dump(mode="python", exclude_unset=True)
        output = next(role for role in self.operation.roles if role.direction == "output")
        kind = next(
            item.key
            for item in self.profile.model.identities
            if item.owner == output.kind and item.domain == "kind"
        )
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    kind,
                    value.content,
                    canonical_bytes(semantic_value(typed)),
                    project_product_members(self.profile.model, output.kind, typed),
                ),
            ),
            outcome=successful_return_outcome(self.operation),
        )

    def invoke_python(self, values, *, binding=None, check_active=lambda: None):
        from corpus_structure.methods.canonical_sentences import CanonicalSentenceProjection

        self._verify()
        inventory = self._input(values, binding)
        check_active()
        result = CanonicalSentenceProjection(self.profile).run(inventory)
        self._verify()
        return self._complete(result, binding)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call

        self._verify()
        inventory = self._input(values, binding)
        signature = inspect.signature(canonical_packet_values)
        bound = signature.bind(inventory=inventory, projection=json.loads(self.profile.projection))
        path = Path(__file__).resolve()
        descriptor = PythonCPUDescriptor(
            (("corpus_structure.semantic.canonical_sentences", str(path), path.read_bytes()),),
            "corpus_structure.semantic.canonical_sentences.canonical_packet_values",
            (),
            verification="prepared-kernel",
        )
        reply = yield from plan_cpu_call(
            descriptor,
            bound,
            signature,
            verify=self._verify,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        result = self.profile.validate_output(json.loads(reply.content))
        return replace(
            self._complete(result, binding),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )


def resolve_canonical_sentence_port(
    prepared, model, operation, *, identity, authorize, custody=(), sources=None
):
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    inputs = [role for role in selected.roles if role.direction == "input"]
    outputs = [role for role in selected.roles if role.direction == "output"]
    if (
        len(inputs) != 1
        or len(outputs) != 1
        or selected.effects
        or selected.capabilities.preparation != "resource"
    ):
        raise PortRefusal(
            "canonical projection requires its declared prepared scalar product profile"
        )
    by_iri = {definition.iri: definition.name for definition in prepared.definitions}
    profile = PreparedCanonicalProfile(
        prepared,
        model,
        selected,
        canonical_bytes(canonical_projection_spec(model, outputs[0].kind)),
        by_iri[inputs[0].kind],
        by_iri[outputs[0].kind],
    )
    port = PreparedCanonicalPort(
        identity, profile, authorize, custody, sources or canonical_sentence_operation_sources()
    )
    port._verify()
    return port
