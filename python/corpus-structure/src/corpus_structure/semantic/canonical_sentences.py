"""Project canonical sentence and token rows from the selected spaCy partitions."""

from __future__ import annotations

import inspect
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import cached_property
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from corpus_structure.caches import declare

from .characterization_manifests import append_manifest
from .data_operation_model import SubjectContext
from .data_operation_outcomes import successful_return_outcome
from .data_operation_population import AcquiredPopulation
from .data_operation_projection_values import _whole_input, materialize_whole_input_projection
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
    populations: tuple = field(default=(), kw_only=True)
    _payload: ClassVar[Any]

    def __post_init__(self):
        from .sentence_partitions import sentence_product_payload

        payload = sentence_product_payload(
            self.content,
            self.partitions,
            self.prepared,
            self.prepared.index.by_iri[self.kind].name,
            populations=self.populations,
        )
        object.__setattr__(self, "content", payload.content)
        object.__setattr__(self, "partitions", payload.partitions)
        object.__setattr__(self, "_payload", payload)

    def with_context(self, context):
        _ = self.value
        result = object.__new__(CanonicalProduct)
        for name in (
            "content",
            "prepared",
            "model",
            "kind",
            "partitions",
            "populations",
            "_payload",
        ):
            object.__setattr__(result, name, getattr(self, name))
        object.__setattr__(result, "subject_context", context)
        return result

    @property
    def value(self) -> Mapping[str, Any]:
        if (
            "_payload" not in vars(self)
            or self.content is not self._payload.content
            or self.partitions is not self._payload.partitions
            or self.populations is not self._payload.populations
        ):
            raise TypeError("canonical product lacks its validating acquisition")
        return self._payload.value

    @cached_property
    def partition_blocks(self):
        from .sentence_partitions import selected_sentence_blocks

        _ = self.value
        return selected_sentence_blocks(self._payload)

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

    @cached_property
    def reference(self):
        from .data_operation_identity import contextual_product_identity
        from .data_product_reference import DataProductReference

        kind = next(
            item.key
            for item in self.model.identities
            if item.owner == self.kind and item.domain == "kind"
        )
        return DataProductReference(
            contextual_product_identity(
                kind=kind, context=self._publication_context(), body=self._payload.body_identity
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


_ADDRESS_SLOT = canonical_bytes(("partition_key", None))
_OFFSET_BYTES = 8


def _canonical_local_rows(body: bytes) -> bytes:
    from .data_operation_values import decode_semantic_value

    return _canonical_rows_template(decode_semantic_value(json.loads(body)))


def _canonical_rows_template(geometry) -> bytes:
    """Prepare local rows and the exact address offsets in their canonical frame."""
    from .data_operation_identity import canonical_identity
    from .data_operation_value_codec import tagged_mapping_field
    from .data_operation_values import semantic_value
    from .data_product_reference import SemanticReference
    from .sentence_partitions import COLLECTION

    rows = tuple(
        row
        | {
            "annotation": SemanticReference.item(
                "inventory",
                COLLECTION,
                "_",
                (row["record_type"], row["ordinal"]),
                occurrence=None,
            ).values()
        }
        for row in geometry
    )
    frame = json.loads(canonical_identity("partition", None).canonical_input)
    body_value = semantic_value(rows)
    for row in body_value[1]:
        reference = tagged_mapping_field(row, "annotation")
        slot = next(field for field in reference[1] if field[0] == "partition_key")
        slot[1] = None
    frame[-1] = body_value

    # The semantic codec represents null as a tagged array. The only raw
    # nulls in this frame are the address fields inserted just above.
    encoded = canonical_bytes(frame)
    offsets = bytearray()
    stop = 0
    for _ in rows:
        offset = encoded.find(_ADDRESS_SLOT, stop)
        if offset < 0:
            raise ValueError("canonical partition has a missing annotation address slot")
        offsets.extend(offset.to_bytes(_OFFSET_BYTES))
        stop = offset + len(_ADDRESS_SLOT)
    if encoded.find(_ADDRESS_SLOT, stop) >= 0:
        raise ValueError("canonical partition has excess annotation address slots")
    return len(offsets).to_bytes(_OFFSET_BYTES) + bytes(offsets) + encoded


@declare(
    "canonical-partition-rows",
    "runtime_bytes",
    key=lambda basis, body, group_digest=None: (
        *basis,
        group_digest if group_digest is not None else sha256(body).digest(),
    ),
    weight=lambda result: len(result),
)
def _memoized_canonical_local_rows(
    basis: tuple[str, ...], body: bytes | AcquiredPopulation, group_digest: str | None = None
) -> bytes:
    if isinstance(body, AcquiredPopulation):
        return _canonical_rows_template(body.rows())
    return _canonical_local_rows(body)


def _address_canonical_local_rows(template: bytes, key: str) -> bytes:
    """Render this occurrence at precomputed slots, using the ordinary value codec."""
    from .data_operation_values import semantic_value

    if type(key) is not str or not key:
        raise ValueError("invalid canonical partition key")
    address = canonical_bytes(("partition_key", semantic_value(key)))
    view = memoryview(template)
    frame_start = _OFFSET_BYTES + int.from_bytes(view[:_OFFSET_BYTES])
    frame = view[frame_start:]
    fragments = []
    start = 0
    for slot in range(_OFFSET_BYTES, frame_start, _OFFSET_BYTES):
        offset = int.from_bytes(view[slot : slot + _OFFSET_BYTES])
        fragments.extend((frame[start:offset], address))
        start = offset + len(_ADDRESS_SLOT)
    fragments.append(frame[start:])
    return b"".join(fragments)


def canonical_partition_values(
    inventory: dict,
    projection: dict,
    memo_basis: tuple[str, ...] | None = None,
    decimal_digits: int | None = None,
    *,
    populations: tuple[AcquiredPopulation, ...] = (),
    check_active=lambda: None,
) -> dict:
    from .data_operation_identity import CanonicalIdentity
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
    partitions = inventory["collections"][COLLECTION]
    if populations and len(populations) != len(partitions):
        raise ValueError("canonical population transfer differs from its selected metadata")
    for index, part in enumerate(partitions):
        check_active()
        key = part["partition_key"]
        if populations:
            geometry = populations[index]
            template = (
                _canonical_rows_template(geometry.rows())
                if memo_basis is None
                else _memoized_canonical_local_rows(memo_basis, geometry, part["geometry_digest"])
            )
        else:
            meaning = canonical_bytes(part["body"])
            template = (
                _canonical_local_rows(meaning)
                if memo_basis is None
                else _memoized_canonical_local_rows(memo_basis, meaning)
            )
        frame = _address_canonical_local_rows(template, key)
        packets.append(
            {
                "collection": COLLECTION,
                "partition_key": key,
                "ordinal": part["ordinal"],
                "placement": part["placement"],
                "body": json.loads(frame)[-1],
                "partition_digest": CanonicalIdentity("partition", frame).key,
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

    def project(self, inventory, *, populations=()):
        return self.output(
            canonical_partition_values(
                inventory, json.loads(self.projection), populations=populations
            )
        )


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
        for item in acquire_codec_runtime(standard_json_io=True)
        if item.reference in {"datetime", "decimal", "hashlib", "json", "rapidjson"}
    )


_RESULT_HELPERS = {
    "canonical_sentences": (
        "_canonical_local_rows",
        "_canonical_rows_template",
        "_address_canonical_local_rows",
        "CanonicalProduct.from_projection",
    ),
    "characterization_manifests": ("append_manifest", "compact_manifest"),
    "data_operation_identity": ("canonical_identity", "CanonicalIdentity.__post_init__"),
    "data_operation_json": ("json_bytes", "canonical_json_bytes"),
    "data_operation_partitions": ("partition_header",),
    "data_operation_projection_values": ("_whole_input", "materialize_whole_input_projection"),
    "data_operation_value_codec": (
        "decode_semantic_value",
        "_decode_semantic_value",
        "native_semantic_value",
        "semantic_value",
        "tagged_mapping_field",
    ),
    "data_operation_values": ("decode_semantic_value", "semantic_value"),
    "data_product_reference": (
        "SemanticReference.item",
        "SemanticReference.__post_init__",
        "SemanticReference.values",
        "_write_reference_key_part",
    ),
    "identity": ("canonical_bytes",),
    "sentence_partitions": ("typed_sentence_role",),
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
        root / "data_operation_population.py",
        root / "population_canonical.py",
        root / "population_transfer.py",
        root / "population_canonical.py",
        root / "population_transfer.py",
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
    requires_prepared_schema: ClassVar[bool] = True

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

    def _input(self, values, binding, *, typed_inputs=None):
        from .data_operation_cpu import PopulationCPUInput
        from .data_operation_ports import HydratedRoleValue, PortRefusal, PythonRoleValue
        from .data_operation_values import decode_semantic_value
        from .sentence_partitions import COLLECTION, sentence_product_payload
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
        partitioned = values[0].partitioned
        if binding is not None and partitioned.populations:
            if not isinstance(values[0], HydratedRoleValue):
                raise PortRefusal("canonical geometry requires its authenticated selected role")
            HydratedRoleValue._require_selected(values[0], binding)
        retained = sentence_product_payload(
            partitioned.header,
            partitioned.packets,
            self.profile.prepared,
            self.profile.prepared.index.by_iri[inputs[0].kind].name,
            populations=partitioned.populations,
        )
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or binding.definition != self.identity.definition
            or binding.eligibility != self.identity.eligibility
            or binding.subject != source_subject(retained.value["source"])
            or decode_semantic_value(json.loads(binding.parameters)) != {}
        ):
            raise PortRefusal("canonical inventory differs from frozen selected binding")
        if retained.populations:
            projection = self.profile.input_projection
            selection = next(item for item in projection.collections if item.name == COLLECTION)
            if typed_inputs is None or selection.groups != ("geometry",):
                raise PortRefusal("canonical geometry differs from its compiled projection")
            facts = []
            for item in sorted(retained.populations, key=lambda value: value.commitment.ordinal):
                partition = item.commitment
                digest = item.group_digests["geometry"]
                facts.append(
                    dict(
                        collection=COLLECTION,
                        partition_key=partition.key,
                        ordinal=partition.ordinal,
                        placement={"start": partition.start, "end": partition.end},
                        geometry_digest=digest,
                    )
                )
                typed_inputs.append(
                    PopulationCPUInput(
                        item.population.project_groups(selection.groups),
                        projection.fingerprint,
                        digest,
                    )
                )
            return _whole_input(
                projection,
                retained.value,
                facts,
                lambda packet, _: {"geometry_digest": packet["geometry_digest"]},
            )
        return materialize_whole_input_projection(
            self.profile.input_projection,
            json.loads(self.profile.input_layouts),
            retained.value,
            retained.packets,
        )

    def _complete(self, value, binding=None):
        if binding is not None:
            value = value.with_context(binding.subject_context)
        from .data_operation_ports import PortCompletion
        from .sentence_partitions import typed_sentence_role

        output = next(role for role in self.operation.roles if role.direction == "output")
        kind = next(
            item.key
            for item in self.profile.model.identities
            if item.owner == output.kind and item.domain == "kind"
        )
        definition = next(
            kind for kind in self.profile.model.kinds if kind.semantic_id == output.kind
        )
        return PortCompletion(
            self.operation.semantic_id,
            (
                typed_sentence_role(
                    output.name,
                    kind,
                    value._payload,
                    self.profile.prepared,
                    definition,
                ),
            ),
            outcome=successful_return_outcome(self.operation),
        )

    def invoke_python(self, values, *, binding=None, check_active=lambda: None):
        from corpus_structure.methods.canonical_sentences import CanonicalSentenceProjection

        self._verify()
        inputs = []
        inventory = self._input(values, binding, typed_inputs=inputs)
        check_active()
        if inputs:
            result = self.profile.project(
                inventory, populations=tuple(item.population for item in inputs)
            )
        else:
            result = CanonicalSentenceProjection(self.profile).run(inventory)
        self._verify()
        return self._complete(result, binding)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from .data_operation_cpu import plan_cpu_call
        from .native_source_view import thaw_native

        inputs = []
        inventory = self._input(values, binding, typed_inputs=inputs)
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
            inventory=thaw_native(inventory),
            projection=json.loads(self.profile.projection),
            memo_basis=memo_basis,
            decimal_digits=self._decimal_digits,
            populations=tuple(item.population for item in inputs),
        )
        reply = yield from plan_cpu_call(
            self._descriptor,
            bound,
            self._signature,
            verify=self._verify,
            execution_owner=execution_owner,
            check_active=check_active,
            population_inputs={"populations": tuple(inputs)},
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
