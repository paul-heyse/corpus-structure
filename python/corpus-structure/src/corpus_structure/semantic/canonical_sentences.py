"""Project canonical sentence and token rows from the selected spaCy partitions."""

from __future__ import annotations

import inspect
import json
import sys
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

from corpus_structure.caches import declare

from .characterization_manifests import append_manifest
from .data_operation_model import SubjectContext
from .data_operation_outcomes import successful_return_outcome
from .data_operation_projection_values import materialize_whole_input_projection
from .identity import canonical_bytes
from .types import SourceArtifact

if TYPE_CHECKING:
    from .data_operation_admission import PreparedCapabilityIdentity
    from .data_operation_cpu import PythonCPUDescriptor
    from .data_operation_model import (
        EffectiveDataOperationModel,
        EffectiveOperation,
        InputReadProjection,
    )
    from .runtime_slice import AuthenticatedSlice
    from .types import PreparedRelease


@dataclass(frozen=True)
class CanonicalProduct:
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    kind: str
    subject_context: SubjectContext | None = None
    partitions: tuple[bytes, ...] = field(kw_only=True)

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @classmethod
    def from_projection(cls, value, prepared, model, kind, *, subject_context=None):
        from .data_operation_partitions import partition_header
        from .sentence_partitions import COLLECTION

        packets = value["partitions"]
        body = dict(value["header"]) | {COLLECTION: partition_header(packets)}
        return cls(
            canonical_bytes(body),
            prepared,
            model,
            kind,
            subject_context,
            partitions=tuple(canonical_bytes(packet) for packet in packets),
        )

    @property
    def reference(self):
        from .data_operation_identity import body_identity, contextual_product_identity
        from .data_product_reference import DataProductReference

        value = json.loads(self.content)
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
    (owner,) = derive_member_kinds(model, container_kind)
    discriminator = kinds[owner + "/property/record_type"]
    if json.loads(discriminator.facts)["equals_string"] != "manifest":
        raise ValueError("canonical body must bind exactly its declared compact manifest")
    return dict(families=list(SPACY_FAMILIES[:2]), manifest_contract=ids[owner, "kind"])


def _canonical_local_rows(key: str, body: bytes) -> bytes:
    """Render the role-relative rows for one block, in local coordinates."""
    from .data_operation_partitions import partition_packet
    from .data_operation_values import decode_semantic_value
    from .data_product_reference import SemanticReference
    from .sentence_partitions import COLLECTION

    rows = tuple(
        row
        | {
            "annotation": SemanticReference.item(
                "inventory", COLLECTION, key, (row["record_type"], row["ordinal"])
            ).values()
        }
        for row in decode_semantic_value(json.loads(body))
    )
    packet = partition_packet(COLLECTION, key, 0, 0, 0, rows)
    return canonical_bytes({"body": packet["body"], "partition_digest": packet["partition_digest"]})


@declare(
    "canonical-partition-rows",
    "runtime_bytes",
    key=lambda basis, key, body: (*basis, key, sha256(body).digest()),
    weight=lambda result: len(result),
)
def _memoized_canonical_local_rows(basis: tuple[str, ...], key: str, body: bytes) -> bytes:
    return _canonical_local_rows(key, body)


def canonical_partition_values(
    inventory: dict,
    projection: dict,
    memo_basis: tuple[str, ...] | None = None,
    decimal_digits: int | None = None,
    *,
    check_active=lambda: None,
) -> dict:
    from .sentence_partitions import COLLECTION
    from .value_codec import decimal_digit_limit

    if decimal_digits is not None and decimal_digit_limit() != decimal_digits:
        raise ValueError("canonical worker codec differs from its acquired recipe")

    header = inventory["header"]
    coverage = [row for row in header["coverage"] if row["family"] in projection["families"]]
    body = {
        **{key: header[key] for key in ("source", "selectors", "block_coverage")},
        "coverage": coverage,
        "outcome": "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in coverage)
        else "partial",
    }
    packets = []
    for part in inventory["collections"][COLLECTION]:
        check_active()
        key = part["partition_key"]
        meaning = canonical_bytes(part["body"])
        rows = (
            _canonical_local_rows(key, meaning)
            if memo_basis is None
            else _memoized_canonical_local_rows(memo_basis, key, meaning)
        )
        packets.append(
            {
                "collection": COLLECTION,
                "partition_key": key,
                "ordinal": part["ordinal"],
                "placement": part["placement"],
                **json.loads(rows),
            }
        )
    return {"header": append_manifest(body, projection["manifest_contract"]), "partitions": packets}


@dataclass(frozen=True)
class PreparedCanonicalProfile:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    operation: EffectiveOperation
    projection: bytes
    output_kind: str
    input_projection: InputReadProjection
    input_layouts: bytes

    def output(self, value):
        return CanonicalProduct.from_projection(value, self.prepared, self.model, self.output_kind)

    def project(self, inventory):
        return self.output(canonical_partition_values(inventory, json.loads(self.projection)))


def execute_canonical_projection(receiver, inventory):
    return receiver.profile.project(inventory)


def _canonical_codec_contract(runtime):
    return [
        [
            item.reference,
            item.contract,
            sorted([file.path.name, file.digest] for file in item.files),
        ]
        for item in runtime
    ]


def _canonical_codec_runtime():
    from .external_runtime import acquire_codec_runtime

    return tuple(
        item
        for item in acquire_codec_runtime()
        if item.reference in {"datetime", "decimal", "hashlib", "rapidjson"}
    )


_RESULT_HELPERS = {
    "canonical_sentences": ("_canonical_local_rows", "CanonicalProduct.from_projection"),
    "characterization_manifests": ("append_manifest", "compact_manifest"),
    "data_operation_identity": ("canonical_identity", "CanonicalIdentity.__post_init__"),
    "data_operation_json": ("json_bytes",),
    "data_operation_partitions": ("partition_packet", "partition_header"),
    "data_operation_projection_values": ("_whole_input", "materialize_whole_input_projection"),
    "data_operation_value_codec": (
        "decode_semantic_value",
        "_decode_semantic_value",
        "native_semantic_value",
        "semantic_value",
    ),
    "data_operation_values": ("decode_semantic_value", "semantic_value"),
    "data_product_reference": (
        "SemanticReference.item",
        "SemanticReference.__post_init__",
        "SemanticReference.values",
        "_write_reference_key_part",
    ),
    "identity": ("canonical_bytes",),
    "sentence_partitions": ("partitioned_role",),
    "source_products": ("source_subject",),
    "value_codec": ("decimal_digit_limit", "decimal_text"),
    "value_codec_core": ("value_meaning", "decimal_text"),
}


def canonical_profile_assets():
    """Capture the deterministic canonical calculation and its exact codec inputs."""
    from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES

    from .characterization_manifests import _COVERAGE_FIELDS
    from .value_codec import decimal_digit_limit

    root = Path(__file__).parents[1]
    result_sources = (
        "methods/canonical_sentences.py",
        "semantic/data_operation_member_contracts.py",
        *(f"semantic/{name}.py" for name in _RESULT_HELPERS),
    )
    return SourceArtifact(
        "canonical/profile-assets",
        canonical_bytes(
            {
                "profile": "canonical-deterministic-projection-v1",
                "families": SPACY_FAMILIES[:2],
                "manifest_coverage_fields": _COVERAGE_FIELDS,
                "python": sys.version,
                "decimal_digits": decimal_digit_limit(),
                "codecs": _canonical_codec_contract(_canonical_codec_runtime()),
                "files": [
                    (name, sha256((root / name).read_bytes()).hexdigest())
                    for name in result_sources
                ],
            }
        ),
    )


def _canonical_execution_files():
    root = Path(__file__).parent
    return (
        Path(__file__),
        root / "characterization_manifests.py",
        root / "sentence_products.py",
        root / "sentence_partitions.py",
        root / "source_products.py",
        root / "data_operation_projection_values.py",
        root / "data_operation_prepared_products.py",
        root / "data_operation_ports.py",
        root / "data_operation_cpu.py",
    )


def canonical_execution_custody():
    return SourceArtifact(
        "canonical/execution-custody",
        canonical_bytes(
            dict(
                files=[
                    (path.name, path.read_bytes().hex()) for path in _canonical_execution_files()
                ]
            )
        ),
        runtime_transport=True,
    )


def canonical_sentence_operation_sources(*, sentence_configuration=None, include_dependencies=True):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    path = Path(__file__).parents[1] / "methods/canonical_sentences.py"
    own = PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.semantic.input_values",
                Path(__file__).with_name("input_values.py").read_bytes(),
                str(Path(__file__).with_name("input_values.py")),
            ),
            PythonSource(
                "corpus_structure.semantic.canonical_sentences",
                Path(__file__).read_bytes(),
                str(Path(__file__)),
            ),
            PythonSource(
                "corpus_structure.semantic.data_operation_ports",
                Path(__file__).with_name("data_operation_ports.py").read_bytes(),
                str(Path(__file__).with_name("data_operation_ports.py")),
            ),
            PythonSource(
                "corpus_structure.semantic.data_operation_projection_values",
                Path(__file__).with_name("data_operation_projection_values.py").read_bytes(),
                str(Path(__file__).with_name("data_operation_projection_values.py")),
            ),
            PythonSource(
                "corpus_structure.methods.canonical_sentences", path.read_bytes(), str(path)
            ),
            PythonSource(
                "corpus_structure.semantic.sentence_partitions",
                Path(__file__).with_name("sentence_partitions.py").read_bytes(),
                str(Path(__file__).with_name("sentence_partitions.py")),
            ),
        ),
        boundary_contracts=(canonical_profile_assets(), canonical_execution_custody()),
    )
    if not include_dependencies:
        return own
    from .primary_operations import combine_primary_sources
    from .sentence_products import sentence_operation_sources

    return combine_primary_sources(sentence_operation_sources(sentence_configuration), own)


@dataclass(frozen=True)
class PreparedCanonicalPort:
    identity: PreparedCapabilityIdentity
    profile: PreparedCanonicalProfile
    authorize: Any
    custody: tuple[SourceArtifact, ...]
    sources: Any
    _verification: AuthenticatedSlice = field(init=False, repr=False, compare=False)
    _descriptor: PythonCPUDescriptor = field(init=False, repr=False, compare=False)
    _signature: inspect.Signature = field(init=False, repr=False, compare=False)
    _decimal_digits: int = field(init=False, repr=False)
    _codec_runtime: tuple = field(init=False, repr=False, compare=False)

    @property
    def operation(self):
        return self.profile.operation

    @property
    def native_selections(self):
        return ()

    def __post_init__(self):
        from importlib import import_module
        from operator import attrgetter

        from corpus_structure.methods.canonical_sentences import CanonicalSentenceProjection

        from .data_operation_cpu import prepared_cpu_descriptor
        from .data_operation_prepared_products import (
            _verify_prepared_callable,
            authenticated_prepared_product,
            verify_prepared_product,
        )
        from .file_custody import verified_file
        from .python_operation_sources import PythonSource, PythonSourceCollection

        entry = "corpus_structure.semantic.canonical_sentences.canonical_partition_values"
        functions = (
            (self.operation.callable_surfaces[0].declaration, CanonicalSentenceProjection.run),
            (
                "corpus_structure.semantic.canonical_sentences.execute_canonical_projection",
                execute_canonical_projection,
            ),
            (entry, canonical_partition_values),
            (
                "corpus_structure.semantic.canonical_sentences.canonical_projection_spec",
                canonical_projection_spec,
            ),
            (
                "corpus_structure.semantic.canonical_sentences.PreparedCanonicalProfile.project",
                PreparedCanonicalProfile.project,
            ),
            (
                "corpus_structure.semantic.data_operation_projection_values.materialize_whole_input_projection",
                materialize_whole_input_projection,
            ),
        )
        required = canonical_sentence_operation_sources(include_dependencies=False)
        assets = required.boundary_contracts

        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            self.sources,
            self.custody,
            assets=assets,
            functions=functions,
            authorize=self.authorize,
            required_sources=required,
        )
        transport = next(asset for asset in assets if asset.name == "canonical/execution-custody")
        contents = dict(json.loads(transport.content)["files"])
        semantic = next(asset for asset in assets if asset.name == "canonical/profile-assets")
        determinants = json.loads(semantic.content)
        runtime = _canonical_codec_runtime()
        if _canonical_codec_contract(runtime) != determinants["codecs"]:
            raise ValueError("current canonical codecs differ from the acquired recipe")
        root = Path(__file__).parents[1]
        files = (
            tuple(
                verified_file(path, sha256(bytes.fromhex(contents[path.name])).hexdigest())
                for path in _canonical_execution_files()
            )
            + tuple(verified_file(root / name, digest) for name, digest in determinants["files"])
            + tuple(file for item in runtime for file in item.files)
        )
        sources = {source.module: source for source in required.sources}
        helpers = []
        worker_sources = []
        for name, definitions in _RESULT_HELPERS.items():
            module_name = f"corpus_structure.semantic.{name}"
            module = import_module(module_name)
            path = (root / "semantic" / f"{name}.py").resolve()
            content = path.read_bytes()
            sources.setdefault(module_name, PythonSource(module_name, content, str(path)))
            worker_sources.append((module_name, str(path), content))
            for definition in definitions:
                owner = module_name + "." + definition
                actual = attrgetter(definition)(module)
                _verify_prepared_callable(owner, actual)
                helpers.append((owner, actual))
        runtime_sources = PythonSourceCollection(tuple(sources.values()))
        verification = authenticated_prepared_product(
            runtime_sources, (*functions, *helpers), required_sources=runtime_sources
        )
        verification.files = tuple(
            {file.path: file for file in (*verification.files, *files)}.values()
        )
        object.__setattr__(self, "_verification", verification)
        object.__setattr__(self, "_decimal_digits", determinants["decimal_digits"])
        object.__setattr__(self, "_codec_runtime", runtime)
        object.__setattr__(
            self, "_signature", inspect.signature(canonical_partition_values, eval_str=True)
        )
        object.__setattr__(
            self,
            "_descriptor",
            prepared_cpu_descriptor(
                tuple(worker_sources),
                entry,
                None,
                tuple(file.receipt() for file in files),
                helpers=tuple(owner for owner, _ in helpers),
            ),
        )

    def _verify(self):
        from .data_operation_ports import PortRefusal
        from .value_codec import decimal_digit_limit

        self._verification.check()
        for codec in self._codec_runtime:
            codec.check()
        if decimal_digit_limit() != self._decimal_digits:
            raise PortRefusal("canonical value codec differs from the acquired computation recipe")
        self.authorize(self.identity)

    def _input(self, values, binding):
        from .data_operation_ports import PortRefusal, PythonRoleValue
        from .data_operation_values import decode_semantic_value
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
            or values[0].partitioned is None
        ):
            raise PortRefusal("canonical projection requires its actual nominal inventory role")
        inventory = values[0].partitioned.value()
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or binding.definition != self.identity.definition
            or binding.eligibility != self.identity.eligibility
            or binding.subject != source_subject(inventory["header"]["source"])
            or decode_semantic_value(json.loads(binding.parameters)) != {}
        ):
            raise PortRefusal("canonical inventory differs from frozen selected binding")
        return materialize_whole_input_projection(
            self.profile.input_projection,
            json.loads(self.profile.input_layouts),
            inventory["header"],
            inventory["partitions"],
        )

    def _complete(self, value, binding=None):
        if binding is not None:
            value = replace(value, subject_context=binding.subject_context)
        from .data_operation_ports import PortCompletion
        from .sentence_partitions import partitioned_role

        output = next(role for role in self.operation.roles if role.direction == "output")
        kind = next(
            item.key
            for item in self.profile.model.identities
            if item.owner == output.kind and item.domain == "kind"
        )
        return PortCompletion(
            self.operation.semantic_id,
            (
                partitioned_role(
                    output.name,
                    kind,
                    json.loads(value.content),
                    tuple(json.loads(packet) for packet in value.partitions),
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
        from .data_operation_cpu import plan_cpu_call

        inventory = self._input(values, binding)
        memo_basis = None
        if (
            binding is not None
            and binding.replicate is None
            and self.operation.replicate_policy == "deterministic-single-result"
        ):
            memo_basis = (
                binding.subject_context.project_id,
                self.identity.recipe,
                self.profile.input_projection.fingerprint,
                binding.parameters.decode(),
            )
        bound = self._signature.bind(
            inventory=inventory,
            projection=json.loads(self.profile.projection),
            memo_basis=memo_basis,
            decimal_digits=self._decimal_digits,
        )
        reply = yield from plan_cpu_call(
            self._descriptor,
            bound,
            self._signature,
            verify=self._verify,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        result = self.profile.output(json.loads(reply.content))
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
    input_projection = inputs[0].read_projection
    if input_projection is None or input_projection.scope != "whole":
        raise PortRefusal("canonical inventory requires its declared whole read projection")
    inventory_kind = next(kind for kind in model.kinds if kind.semantic_id == inputs[0].kind)
    profile = PreparedCanonicalProfile(
        prepared,
        model,
        selected,
        canonical_bytes(canonical_projection_spec(model, outputs[0].kind)),
        outputs[0].kind,
        input_projection,
        canonical_bytes(json.loads(inventory_kind.facts)["collections"]),
    )
    return PreparedCanonicalPort(
        identity, profile, authorize, custody, sources or canonical_sentence_operation_sources()
    )
