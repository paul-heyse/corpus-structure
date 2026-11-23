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
from .data_operation_cpu import CPUArrowResult
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


def canonical_partition_values(inventory: dict, projection: dict) -> dict:
    """Build a tagged reference population for independent row and byte controls."""
    from .data_operation_values import decode_semantic_value
    from .data_product_reference import SemanticReference
    from .sentence_partitions import COLLECTION, SentenceBlock

    packets = []
    for part in inventory["collections"][COLLECTION]:
        key = part["partition_key"]
        rows = tuple(
            row
            | {
                "annotation": SemanticReference.item(
                    "inventory", COLLECTION, key, (row["record_type"], row["ordinal"])
                ).values()
            }
            for row in decode_semantic_value(part["body"])
        )
        packets.append(
            SentenceBlock(
                key, part["ordinal"], part["placement"]["start"], part["placement"]["end"], rows
            ).packet()
        )
    return {"header": _canonical_header(inventory, projection), "partitions": packets}


def _canonical_header(inventory, projection):
    header = inventory["header"]
    coverage = [row for row in header["coverage"] if row["family"] in projection["families"]]
    body = {
        **{key: header[key] for key in ("source", "selectors", "block_coverage")},
        "coverage": coverage,
        "outcome": "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in coverage)
        else "partial",
    }
    return append_manifest(body, projection["manifest_contract"])


_CANONICAL_REPLY = b"corpus.canonical_reply"


def _canonical_materialization(layout, rows, key):
    from .data_product_reference import SemanticReference
    from .sentence_partitions import COLLECTION

    return layout.from_rows(
        row
        | {
            "annotation": SemanticReference.item(
                "inventory", COLLECTION, key, (row["record_type"], row["ordinal"])
            ).values()
        }
        for row in rows
    ).table


@declare(
    "canonical-typed-partition-rows",
    "runtime_bytes",
    key=lambda basis, digest, layout, rows: (*basis, digest),
    weight=lambda table: table.get_total_buffer_size(),
)
def _memoized_canonical_materialization(basis, digest, layout, rows):
    return _canonical_materialization(layout, rows, "_")


def _place_canonical_materialization(table, key):
    import pyarrow as pa

    def replace_child(array, name, value):
        return pa.StructArray.from_arrays(
            [value if field.name == name else array.field(field.name) for field in array.type],
            fields=list(array.type),
        )

    column = table["annotation"]
    placed = []
    for chunk in column.chunks:
        address = chunk.field("partition_key")
        field_type = address.type.field("value").type
        address = replace_child(
            address, "value", pa.repeat(pa.scalar(key, type=field_type), len(chunk))
        )
        placed.append(replace_child(chunk, "partition_key", address))
    location = table.schema.get_field_index("annotation")
    return table.set_column(
        location, table.schema.field(location), pa.chunked_array(placed, type=column.type)
    )


def canonical_population_result(
    inventory: dict,
    projection: dict,
    output_kind: str,
    decimal_digits: int,
    memo_basis: tuple[str, ...] | None = None,
    *,
    populations: tuple[AcquiredPopulation, ...],
    prepared: object,
    check_active=lambda: None,
) -> CPUArrowResult:
    """Return normalized Arrow rows and compact placement, without a tagged partition reply."""
    from .data_operation_admission import bound_data_operation_model
    from .data_operation_population import population_layout
    from .sentence_partitions import COLLECTION
    from .types import PreparedRelease
    from .value_codec import decimal_digit_limit

    if decimal_digit_limit() != decimal_digits:
        raise ValueError("canonical worker codec differs from its acquired recipe")
    layout = None
    if inventory["collections"][COLLECTION]:
        if not isinstance(prepared, PreparedRelease):
            raise ValueError("canonical result lacks its acquired release layout")
        model = bound_data_operation_model(prepared)
        definition = next(kind for kind in model.kinds if kind.semantic_id == output_kind)
        layout = population_layout(prepared, definition, COLLECTION)
    return _canonical_population_table(
        inventory, projection, layout, populations, memo_basis=memo_basis, check_active=check_active
    )


def _canonical_population_table(
    inventory, projection, layout, populations, *, memo_basis=None, check_active=lambda: None
):
    import pyarrow as pa

    from .data_operation_values import decode_semantic_value
    from .native_source_view import thaw_native
    from .sentence_partitions import COLLECTION

    selected = inventory["collections"][COLLECTION]
    if populations and len(populations) != len(selected):
        raise ValueError("canonical population transfer differs from its selected metadata")
    placements = []
    if selected:
        if layout is None:
            raise ValueError("canonical population requires its nominal layout")
        if memo_basis is not None:
            memo_basis = (
                *memo_basis,
                *(layout.schema.metadata[name] for name in (b"release_id", b"kind")),
            )
        tables = []
        for index, part in enumerate(selected):
            check_active()
            key = part["partition_key"]
            if type(key) is not str or not key:
                raise ValueError("invalid canonical partition key")
            if populations:
                geometry = populations[index]
                count, block_rows = geometry.table.num_rows, geometry.rows()
                digest = part["geometry_digest"]
            else:
                block_rows = decode_semantic_value(thaw_native(part["body"]))
                count = len(block_rows)
                digest = sha256(canonical_bytes(part["body"])).hexdigest()
            placements.append(
                [key, part["ordinal"], part["placement"]["start"], part["placement"]["end"], count]
            )
            if memo_basis is None:
                table = _canonical_materialization(layout, block_rows, key)
            else:
                template = _memoized_canonical_materialization(
                    memo_basis, digest, layout, block_rows
                )
                table = _place_canonical_materialization(template, key)
            tables.append(table)
        table = pa.concat_tables(tables)
    else:
        table = pa.table({})
    metadata = dict(table.schema.metadata or {})
    metadata[_CANONICAL_REPLY] = canonical_bytes(
        {"header": _canonical_header(inventory, projection), "placements": placements}
    )
    return CPUArrowResult(table.replace_schema_metadata(metadata))


@dataclass(frozen=True)
class PreparedCanonicalProfile:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    operation: EffectiveOperation
    projection: bytes
    output_kind: str
    input_projection: InputReadProjection
    input_layouts: bytes

    def output(self, table, inventory, inputs):
        from corpus_structure.analytics import connection

        from .data_operation_partitions import partition_commitment_header
        from .data_operation_population import population_layout
        from .native_source_view import thaw_native
        from .sentence_partitions import COLLECTION, SentenceBlock, produce_sentence_partition

        metadata = dict(table.schema.metadata or {})
        control = json.loads(metadata.pop(_CANONICAL_REPLY, b"null"))
        projection = json.loads(self.projection)
        if (
            type(control) is not dict
            or set(control) != {"header", "placements"}
            or control["header"] != thaw_native(_canonical_header(inventory, projection))
        ):
            raise ValueError("canonical reply differs from its selected header")
        selected = inventory["collections"][COLLECTION]
        expected: list[tuple[str, int, int, int, int]] = [
            (
                part["partition_key"],
                part["ordinal"],
                part["placement"]["start"],
                part["placement"]["end"],
                inputs[index].table.num_rows if inputs else len(part["body"][1]),
            )
            for index, part in enumerate(selected)
        ]
        if (
            control["placements"] != [list(row) for row in expected]
            or sum(row[4] for row in expected) != table.num_rows
        ):
            raise ValueError("canonical reply differs from its selected partition extent")
        owned = []
        if expected:
            kind = next(kind for kind in self.model.kinds if kind.semantic_id == self.output_kind)
            layout = population_layout(self.prepared, kind, COLLECTION)
            table = table.replace_schema_metadata(metadata)
            if not table.schema.equals(layout.schema, check_metadata=True):
                raise ValueError("canonical reply differs from its nominal output layout")
            # The loaded kernel admitted the nominal rows before writing its bound reply.
            table.validate(full=True)
            with connection() as engine:
                offset = 0
                for key, ordinal, start, end, count in expected:
                    part = AcquiredPopulation._from_table(layout, table.slice(offset, count))
                    owned.append(
                        produce_sentence_partition(
                            SentenceBlock(key, ordinal, start, end, ()), part, engine=engine
                        )
                    )
                    offset += count
        elif table.num_columns or metadata:
            raise ValueError("empty canonical reply has undeclared columns")
        body = control["header"] | {
            COLLECTION: partition_commitment_header(item.commitment for item in owned)
        }
        return CanonicalProduct(
            canonical_bytes(body),
            self.prepared,
            self.model,
            self.output_kind,
            partitions=(),
            populations=tuple(owned),
        )

    def project(self, inventory, *, populations=()):
        from .data_operation_population import population_layout
        from .sentence_partitions import COLLECTION

        kind = next(kind for kind in self.model.kinds if kind.semantic_id == self.output_kind)
        result = _canonical_population_table(
            inventory,
            json.loads(self.projection),
            population_layout(self.prepared, kind, COLLECTION),
            populations,
        )
        return self.output(result.table, inventory, populations)


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
        "_canonical_materialization",
        "_canonical_population_table",
        "_place_canonical_materialization",
        "_canonical_header",
    ),
    "characterization_manifests": ("append_manifest", "compact_manifest"),
    "data_operation_identity": ("canonical_identity", "CanonicalIdentity.__post_init__"),
    "data_operation_json": ("json_bytes", "canonical_json_bytes"),
    "data_operation_partitions": ("partition_commitment_header",),
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
    "sentence_partitions": ("typed_sentence_role", "produce_sentence_partition"),
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

        entry = "corpus_structure.semantic.canonical_sentences.canonical_population_result"
        functions = (
            (self.operation.callable_surfaces[0].declaration, CanonicalSentenceProjection.run),
            (
                "corpus_structure.semantic.canonical_sentences.execute_canonical_projection",
                execute_canonical_projection,
            ),
            (entry, canonical_population_result),
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
            self, "_signature", inspect.signature(canonical_population_result, eval_str=True)
        )
        object.__setattr__(
            self,
            "_descriptor",
            prepared_cpu_descriptor(
                tuple(worker_sources),
                entry,
                self.profile.prepared.release_id,
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
        if binding is not None:
            if not isinstance(values[0], HydratedRoleValue) or partitioned.packets:
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
        import pyarrow as pa

        from .data_operation_cpu import plan_cpu_call
        from .native_source_view import thaw_native

        inputs = []
        inventory = self._input(values, binding, typed_inputs=inputs)
        from .sentence_partitions import COLLECTION

        populated = bool(inventory["collections"][COLLECTION])
        descriptor = (
            self._descriptor
            if populated
            else replace(self._descriptor, prepared_release_id=None, prepared_parameter=None)
        )
        populations = tuple(item.population for item in inputs)
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
            output_kind=self.profile.output_kind,
            decimal_digits=self._decimal_digits,
            memo_basis=memo_basis,
            populations=populations,
            prepared=self.profile.prepared if populated else None,
        )
        reply = yield from plan_cpu_call(
            descriptor,
            bound,
            self._signature,
            verify=self._verify,
            execution_owner=execution_owner,
            check_active=check_active,
            population_inputs={"populations": tuple(inputs)},
        )
        with pa.ipc.open_file(pa.BufferReader(reply.content)) as reader:
            result = self.profile.output(reader.read_all(), inventory, populations)
        check_active()
        self._verify()
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
