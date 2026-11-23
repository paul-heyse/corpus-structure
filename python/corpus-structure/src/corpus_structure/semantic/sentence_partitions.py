"""The shared block-local view of sentence and token populations."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from corpus_structure.caches import declare

from ._data_operation_wire import WireProductPartition
from .data_operation_partitions import (
    PartitionCommitment,
    partition_commitment_header,
    partition_header,
    partition_packet,
)
from .data_operation_values import decode_semantic_value, semantic_value
from .data_product_reference import SemanticReference
from .identity import canonical_bytes

COLLECTION = "rows"


def construction_annotation_reference(block_key: str, row_type: str, ordinal: int):
    return SemanticReference.item("sentences", COLLECTION, block_key, (row_type, ordinal)).values()


@dataclass(frozen=True, slots=True)
class SentenceBlock:
    key: str
    ordinal: int
    start: int
    end: int
    rows: tuple[Mapping[str, Any], ...]

    def packet(self) -> WireProductPartition:
        return partition_packet(COLLECTION, self.key, self.ordinal, self.start, self.end, self.rows)


def blocks_from_packets(packets: Sequence[WireProductPartition]) -> tuple[SentenceBlock, ...]:
    if any(packet["collection"] != COLLECTION for packet in packets):
        raise ValueError("sentence populations require their declared rows collection")
    return tuple(
        SentenceBlock(
            packet["partition_key"],
            packet["ordinal"],
            packet["placement"]["start"],
            packet["placement"]["end"],
            tuple(decode_semantic_value(packet["body"])),
        )
        for packet in sorted(packets, key=lambda packet: packet["ordinal"])
    )


@dataclass(frozen=True)
class _SentenceProductHeader:
    content: bytes
    value: Mapping[str, Any]
    meaning: bytes
    tagged: tuple
    members: tuple[bytes, ...]
    member_packets: tuple[Mapping[str, Any], ...]
    body_identity: str


@dataclass(frozen=True)
class SentenceProductPayload(_SentenceProductHeader):
    """Invocation-owned assembly of immutable data, without occurrence authority."""

    partitions: tuple[bytes, ...]
    packets: tuple[Mapping[str, Any], ...]
    blocks: tuple[SentenceBlock, ...]
    populations: tuple = ()


@dataclass(frozen=True, slots=True)
class _SentencePartitionBody:
    digest: str
    tagged: tuple
    rows: tuple[Mapping[str, Any], ...]
    weight: int


@declare(
    "sentence-partition-bodies",
    "runtime_bytes",
    key=lambda meaning, tagged, decoder: (sha256(tagged).digest(), decoder),
    weight=lambda body: body.weight,
)
def _sentence_partition_body(meaning, tagged: bytes, decoder) -> _SentencePartitionBody:
    from .data_operation_consumers import _freeze_consumer
    from .data_operation_identity import canonical_identity
    from .native_source_view import freeze_native

    rows = decode_semantic_value(meaning)
    identity = canonical_identity("partition", rows)
    return _SentencePartitionBody(
        identity.key,
        freeze_native(meaning),
        tuple(_freeze_consumer(row) for row in rows),
        len(tagged) + len(identity.canonical_input),
    )


def sentence_product_payload(content, partitions, prepared, nominal_type, *, populations=()):
    from .data_operation_version import MODEL_VERSION
    from .value_codec import decimal_digit_limit

    if (
        type(content) is not bytes
        or type(partitions) is not tuple
        or any(type(packet) is not bytes for packet in partitions)
        or type(populations) is not tuple
        or (partitions and populations)
    ):
        raise TypeError("sentence products require owned immutable header and partition bytes")
    decoder = (MODEL_VERSION, decimal_digit_limit())
    header = _sentence_product_header(content, prepared, nominal_type, decoder)
    if populations:
        _verify_population_header(populations, header.value[COLLECTION])
        packets = ()
        blocks = ()
    else:
        packets, blocks = acquire_sentence_partitions(partitions, header.value[COLLECTION])
    return SentenceProductPayload(
        header.content,
        header.value,
        header.meaning,
        header.tagged,
        header.members,
        header.member_packets,
        header.body_identity,
        partitions,
        packets,
        blocks,
        populations,
    )


def selected_sentence_blocks(payload: SentenceProductPayload) -> tuple[SentenceBlock, ...]:
    """Enter the row API only for a consumer that actually needs working sentence records."""
    if not payload.populations:
        return payload.blocks
    return _blocks_from_populations(payload.populations)


def _verify_population_header(populations, header):
    if (
        any(
            item.commitment.collection != COLLECTION
            or item.commitment.item_count != item.population.table.num_rows
            for item in populations
        )
        or partition_commitment_header(item.commitment for item in populations) != header
    ):
        raise ValueError("sentence rows differ from their selected collection commitment")


def _blocks_from_populations(populations) -> tuple[SentenceBlock, ...]:
    from .data_operation_consumers import _freeze_consumer

    result = []
    for item in sorted(populations, key=lambda selected: selected.commitment.ordinal):
        partition = item.commitment
        result.append(
            SentenceBlock(
                partition.key,
                partition.ordinal,
                partition.start,
                partition.end,
                tuple(_freeze_consumer(row) for row in item.population.rows()),
            )
        )
    return tuple(result)


def acquire_sentence_blocks(partitions, commitment, *, populations=()) -> tuple[SentenceBlock, ...]:
    if populations:
        if partitions:
            raise ValueError("sentence rows have two admitted representations")
        _verify_population_header(populations, commitment)
        return _blocks_from_populations(populations)
    _, blocks = acquire_sentence_partitions(partitions, commitment)
    return blocks


def acquire_sentence_partitions(partitions, commitment):
    """Acquires committed partition packets at a product or sealed worker ingress."""
    from .data_operation_json import native_json_loads
    from .data_operation_version import MODEL_VERSION
    from .native_source_view import freeze_native
    from .value_codec import decimal_digit_limit

    decoder = (MODEL_VERSION, decimal_digit_limit())
    packets = tuple(native_json_loads(packet) for packet in partitions)
    if partition_header(packets) != commitment:
        raise ValueError("sentence rows differ from their selected collection commitment")
    blocks = []
    frozen_packets = []
    for packet in packets:
        if packet["collection"] != COLLECTION:
            raise ValueError("sentence populations require their declared rows collection")
        meaning = packet["body"]
        body = _sentence_partition_body(meaning, canonical_bytes(meaning), decoder)
        if body.digest != packet["partition_digest"]:
            raise ValueError("sentence partition digest differs from its actual rows")
        blocks.append(
            SentenceBlock(
                packet["partition_key"],
                packet["ordinal"],
                packet["placement"]["start"],
                packet["placement"]["end"],
                body.rows,
            )
        )
        metadata = {key: freeze_native(value) for key, value in packet.items() if key != "body"}
        frozen_packets.append(MappingProxyType({**metadata, "body": body.tagged}))
    return tuple(frozen_packets), tuple(sorted(blocks, key=lambda item: item.ordinal))


@declare(
    "sentence-product-headers",
    "runtime_bytes",
    key=lambda content, prepared, nominal_type, decoder: (
        sha256(content).digest(),
        prepared.release_id,
        nominal_type,
        decoder,
    ),
    weight=lambda header: len(header.content) + len(header.meaning) + sum(map(len, header.members)),
)
def _sentence_product_header(content, prepared, nominal_type, decoder):
    from .data_operation_identity import body_identity
    from .data_operation_json import native_json_loads
    from .native_source_view import freeze_native

    body = native_json_loads(content)
    if not isinstance(body, dict) or COLLECTION not in body:
        raise ValueError("sentence product requires its declared collection commitment")
    commitment = body.pop(COLLECTION)

    def fields(value):
        # Generated nominal models own dictionaries and tuple-valued collections.
        if isinstance(value, dict):
            return {key: fields(item) for key, item in value.items()}
        if isinstance(value, list):
            return tuple(fields(item) for item in value)
        return value

    checked = prepared.validate_python(nominal_type, fields(body)).model_dump(
        mode="json", exclude_unset=True
    )
    checked[COLLECTION] = commitment
    tagged = semantic_value(checked)
    members = tuple(
        dict(member, body=semantic_value(member["body"])) for member in checked["members"]
    )
    return _SentenceProductHeader(
        canonical_bytes(checked),
        freeze_native(checked),
        canonical_bytes(tagged),
        freeze_native(tagged),
        tuple(canonical_bytes(member) for member in members),
        tuple(freeze_native(member) for member in members),
        body_identity(checked).key,
    )


def partitioned_role(role, kind_contract, payload: SentenceProductPayload):
    """Publish the exact already acquired nominal header and partition data."""
    from .data_operation_ports import RoleValue

    return RoleValue(
        role, kind_contract, payload.content, payload.meaning, payload.members, payload.partitions
    )


def typed_sentence_role(role, kind_contract, payload: SentenceProductPayload, prepared, kind):
    """Publish compact sentence metadata with exact canonical upload items."""
    from corpus_structure.analytics import connection

    from .data_operation_population import population_layout
    from .data_operation_ports import RoleValue
    from .population_canonical import canonical_population
    from .population_transfer import PopulationUploadPartition

    layout = population_layout(prepared, kind, COLLECTION)
    blocks = selected_sentence_blocks(payload)
    populations = []
    if blocks:
        with connection() as engine:
            for block in blocks:
                items = canonical_population(layout.from_rows(block.rows), engine=engine)
                populations.append(
                    PopulationUploadPartition(
                        PartitionCommitment(
                            COLLECTION,
                            block.key,
                            block.ordinal,
                            block.start,
                            block.end,
                            items.partition_digest,
                            items.items.num_rows,
                        ),
                        items.group_digests,
                        items.items,
                    )
                )
    if (
        partition_commitment_header(item.commitment for item in populations)
        != payload.value[COLLECTION]
    ):
        raise ValueError("typed sentence rows differ from their admitted collection")
    return RoleValue(
        role,
        kind_contract,
        payload.content,
        payload.meaning,
        payload.members,
        populations=tuple(populations),
    )


def annotation_blocks(value: Mapping) -> tuple[SentenceBlock, ...]:
    """Project validated spaCy annotation in block-relative coordinates."""
    result = []
    for index, block in enumerate(value["blocks"]):
        annotation = block["annotation"]
        start, end = annotation["block_start"], annotation["block_end"]
        if len(annotation["tokens"]) != len(block["lexemes"]):
            raise ValueError("native lexical columns differ from their actual token population")
        rows = []
        for ordinal, (token, lexeme) in enumerate(
            zip(annotation["tokens"], block["lexemes"], strict=True)
        ):
            row = dict(token) | dict(lexeme)
            rows.append(
                row
                | dict(
                    record_type="token",
                    ordinal=ordinal,
                    start=token["start"] - start,
                    end=token["end"] - start,
                    extent=end - start,
                )
            )
        for ordinal, sentence in enumerate(annotation["sentences"]):
            rows.append(
                dict(
                    record_type="sentence",
                    ordinal=ordinal,
                    start=sentence["start"] - start,
                    end=sentence["end"] - start,
                    extent=end - start,
                )
            )
        rows.sort(key=lambda row: (row["record_type"], row["ordinal"]))
        result.append(SentenceBlock(annotation["block_id"], index, start, end, tuple(rows)))
    return tuple(result)


def partition_source_annotations(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[WireProductPartition, ...]]:
    """Separate original-source placement and layout from normalized annotation rows."""
    header = dict(value)
    header["block_layouts"] = [
        {
            "annotation": {
                key: field
                for key, field in block["annotation"].items()
                if key not in {"tokens", "sentences"}
            },
            "piece_offset": block["piece_offset"],
        }
        for block in header.pop("blocks")
    ]
    return header, tuple(block.packet() for block in annotation_blocks(value))
